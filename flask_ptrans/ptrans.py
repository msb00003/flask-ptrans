"""
    Flask/Jinja2 extension for pootle-based localisation

    Adds the following syntax to template files:

    {% ptrans STRID %}Fallback text{% endptrans %}

    This does 2 things:
    1. At runtime, it replaces its body with localised string whose ID is STRID, for the currently selected locale,
       or if the string ID is not defined for that locale, leaves it as the Fallback text provided.

    2. Marks the translatable string in the template, so the Fallback text can be extracted automatically as the
       en-gb text for that string ID. Our script to do this can then check for inconsistencies.

    Depends on {{locale}} being available in the template being rendered. IOW, pass it into render_template() as
    a keyword argument. You will want to do this anyway, so every page can begin with:
      <html lang="{{locale}}">
    thereby letting the browser know what language the page is being rendered in.

    String IDs start with a letter, and contain alphanumerics, underscores and hyphens.

Copyright 2015 Skyscanner Ltd

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.

"""
import logging
import glob
import os.path
import json

import flask
import jinja2.ext
import jinja2.nodes


class LazyLocalisedStringStore(object):
    """
    String store that looks up strings in a dictionary, chosen according to locale.
    The dictionaries are loaded from JSON files only as needed.

    If no file for an exactly matching locale is available, localisations for a
    partial match (same language but not same variant) will be used. This decision
    is made once when attempting to load a locale for the first time.
    """

    def __init__(self, localisation_directory=None):
        self.locales = {}               # {locale:dict_of_strings}
        self._known_locales = set()     # locales known to have a file that will match them
        self.localisation_dir = localisation_directory  # path to directory containing LOCALE.json files

    def lookup(self, locale, strid, fallback, **format_kwargs):
        """
        Localised version of a string
        :param locale: locale code, e.g. 'pt-BR'
        :param strid: string ID
        :param fallback: default string to return if localised version not found
        :param format_kwargs: if present, insert these into the string with str.format()
        :return: localised string or the fallback
        """
        if not isinstance(locale, (str, type(u''))):
            logging.error("locale is a %s for %s", locale.__class__.__name__, strid)
            translated = fallback
        else:
            if locale not in self.locales:
                self.load_locale(locale)
            # Invariant: self.locales[locale] is a dict (possibly empty, possibly alias to another
            #  loaded previously)
            translated = self.locales[locale].get(strid, fallback)
            if isinstance(translated, dict):
                translated = translated.get("value", fallback)
        if format_kwargs:
            if not isinstance(translated, type(u'')):   # ensure it's unicode, can't insert unicode into a bytestring
                translated = translated.decode('utf-8')
            try:
                translated = translated.format(**format_kwargs)
            except KeyError as err:
                logging.error("No {%s} in string %s, locale %s", err.args[0], strid, locale)
                pass
        return translated

    def lookup_cascade(self, locale, strid, fallback=None, fallback_locale="en-GB", **format_kwargs):
        """
        Localised version of a string, fallback to 1) fallback string, 2) other locale, 3) key
        """
        if not fallback:
            if fallback_locale not in self.locales:
                self.load_locale(fallback_locale)
            fallback = self.locales[fallback_locale].get(strid, strid)
        translated = self.lookup(locale, strid, fallback, **format_kwargs)
        return translated

    def subset(self, locale, *prefixes):
        """
        Return a subset of the string store for a specified locale, where the string IDs match any of the
        given prefixes.
        :param locale: locale code, e.g. 'pt-BR'
        :param prefixes: array of prefixes e.g. ['flights_payment_', 'shared_country_']
        :return: a dict containing keys and values
        """
        if not isinstance(locale, (str, type(u''))):
            logging.error("locale is a %s for subset %s", locale.__class__.__name__, prefixes)
            return {}
        if locale not in self.locales:
            self.load_locale(locale)
        trans = {k: v for (k, v) in self.locales[locale].items()
                 if any(k.startswith(p) for p in prefixes)}
        return trans

    def load_locale(self, locale):
        """
        Load best match for requested locale dict
        """
        filepath = self.best_file_for_locale(locale.lower())
        if not filepath:
            logging.warning("ptrans no translations for locale %s", locale)
            self.locales[locale] = {}  # give up, always fall back to untranslated text
        else:
            actual_locale_file = os.path.basename(filepath)
            actual_locale = os.path.splitext(actual_locale_file)[0]
            if actual_locale in self.locales:
                self.locales[locale] = self.locales[actual_locale]  # alias to already loaded locale
            else:
                logging.info("ptrans loading %s", filepath)
                with open(filepath, "r") as jsonfile:
                    try:
                        string_dict = json.load(jsonfile)
                        # in case files haven't been aggregated and simplified...
                        for k, v in string_dict.items():
                            # can cope with both of Pootle's JSON formats
                            if type(v) is dict:
                                # we only want the string value, not the comments
                                string_dict[k] = v.get("value")
                    except ValueError:
                        logging.error("ptrans invalid json in %s", filepath)
                        string_dict = {}    # give up, fall back to untranslated text
                self.locales[locale] = string_dict
                self.locales[actual_locale] = string_dict

    def best_file_for_locale(self, locale):
        """ first choice is exact match, second is any other locale with same language """
        if not self.localisation_dir:
            return None
        lang, hyphen, variant = locale.partition('-')
        candidates = [locale + ".json",     # exactly matching locale
                      lang + "-*.json"]     # set of locale files in same language group
        best_match = None
        for filename in candidates:
            file_list = glob.glob(os.path.join(self.localisation_dir, filename))
            if file_list:
                best_match = file_list[0]
                break
        return best_match

    @property
    def known_locales(self):
        """
        Set of the locales directly provided by localised files (including generic languages of specific locales)
        """
        if self._known_locales:     # memoize
            return self._known_locales
        if not self.localisation_dir:
            return set()
        file_list = glob.glob(os.path.join(self.localisation_dir, "*.json"))
        for filepath in file_list:
            locale = os.path.splitext(os.path.basename(filepath))[0]
            self._known_locales.add(locale)
            lang, hyphen, variant = locale.partition('-')
            if hyphen:
                self._known_locales.add(lang)
        return self._known_locales


# This global string store is a singleton
_global_string_store = LazyLocalisedStringStore()


class PootleTranslationExtension(jinja2.ext.Extension):
    """
    Provide the {% ptrans %} tag
    """
    tags = {'ptrans'}

    def __init__(self, environment):
        """
        extend the environment so ptrans_lookup function is available
        """
        jinja2.ext.Extension.__init__(self, environment)
        environment.globals.update(
            ptrans_get=_global_string_store.lookup_cascade,
            ptrans_subset=_global_string_store.subset)

    def parse(self, parser):
        """
        :param parser: parser for HTML templates
        :return: a jinja2.nodes.Node defining how to render the contents of the tag at run-time
        """
        next(parser.stream)     # skip 'ptrans' token

        # expect a string ID (names and hyphens), then block_end
        name = parser.stream.expect('name')
        strid_buf = [name.value]
        while parser.stream.current.type in ('name', 'sub'):
            strid_buf.append(parser.stream.current.value)
            next(parser.stream)
        strid = ''.join(strid_buf)
        parser.stream.expect('block_end')   # %}

        # parse the block of fallback text
        body = []
        while parser.stream.current.type == 'data':
            body.append(parser.stream.current.value)
            next(parser.stream)
        fallback = u''.join(body)

        # expect {% endptrans %}
        parser.stream.expect('block_begin')
        name = parser.stream.expect('name')
        if name.value != 'endptrans':
            parser.fail('ptrans blocks can only contain text, not control structures', name.lineno)

        # make a Call node that calls ptrans_lookup with the locale, strid and fallback
        ptrans_node = jinja2.nodes.Call(jinja2.nodes.Name('ptrans_get', 'load'),
                                        [jinja2.nodes.Name('locale', 'load'),
                                         jinja2.nodes.Const(strid),
                                         jinja2.nodes.Const(fallback)],
                                        [], None, None)
        return jinja2.nodes.Output([ptrans_node])

ptrans = PootleTranslationExtension


def init_localisation(localisation_directory):
    _global_string_store.localisation_dir = localisation_directory


def best_locale():
    """
    Find best locale code for request's accept-language header, given the localisations available

    Prefers an exact match, otherwise it settles for first inexact match.
    Falls back to en-GB if nothing else will do.

    :return: locale code
    """
    locale = "en-GB"
    if flask.has_request_context():
        best = flask.request.accept_languages.best_match(_global_string_store.known_locales)
        if best:
            locale = best
    return locale
