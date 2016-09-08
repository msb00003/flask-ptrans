"""
Async version of LazyLocalisedStringStore, Python 3.5 and above only

For use with Tornado or asyncio.
"""

import logging
import glob
import os.path
import json


class AsyncLocalisedStringStore(object):
    """
    String store that looks up strings in a dictionary, chosen according to locale.
    The dictionaries are loaded from JSON files only as needed.

    If no file for an exactly matching locale is available, localisations for a
    partial match (same language but not same variant) will be used. This decision
    is made once when attempting to load a locale for the first time.
    """

    def __init__(self, localisation_directory=None, allow_empty=False, async_locale_hook=None):
        self.locales = {}               # {locale:dict_of_strings}
        self._known_locales = set()     # locales known to have a file that will match them
        self.localisation_dir = localisation_directory  # path to directory containing LOCALE.json files
        self.allow_empty = allow_empty  # accept empty translations? If not, they are treated as though missing
        self.locale_hook = async_locale_hook

    def install_locale_hook(self, async_locale_hook):
        self.locale_hook = async_locale_hook

    async def prepare_locale(self, locale):
        """ invoke this to ensure a locale is loaded, before using lookup """
        return self.locales.get(locale) or await self.load_locale(locale)

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
            locale_dict = self.locales.get(locale) or {}
            # Invariant: locale_dict is a dict (possibly empty, possibly alias to another
            #  loaded previously)
            translated = locale_dict.get(strid, fallback)
            if isinstance(translated, dict):
                translated = translated.get("value", fallback)
            if not translated and not self.allow_empty:
                translated = fallback
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
            fallback_dict = self.locales.get(fallback_locale) or {}
            fallback = fallback_dict.get(strid, strid)
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
        locale_dict = self.locales.get(locale) or {}
        trans = {k: v for (k, v) in locale_dict.items()
                 if any(k.startswith(p) for p in prefixes)}
        return trans

    async def load_locale(self, locale):  # -> dict
        """
        Load best match for requested locale dict
        """
        # first try the hook function if one was provided
        if self.locale_hook:
            lang, hyphen, variant = locale.partition("-")
            string_dict = await self.locale_hook(locale)
            if string_dict:
                self.locales[locale] = string_dict
                if lang not in self.locales:
                    self.locales[lang] = string_dict    # set this as the default locale for the base language too
            else:
                if hyphen and lang in self.locales:
                    self.locales[locale] = string_dict = self.locales[lang]    # make do with base language locale
            return string_dict

        # See if we have strings in a file
        filepath = self.best_file_for_locale(locale.lower())
        if not filepath:
            logging.warning("ptrans no translations for locale %s", locale)
            self.locales[locale] = {}  # give up, always fall back to untranslated text
            return {}
        else:
            actual_locale_file = os.path.basename(filepath)
            actual_locale = os.path.splitext(actual_locale_file)[0]
            if actual_locale in self.locales:
                string_dict = self.locales[locale] = self.locales[actual_locale]  # alias to already loaded locale
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
            return string_dict

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
_global_string_store = AsyncLocalisedStringStore()


def init_localisation(localisation_directory=None, allow_empty=False, locale_hook=None) -> AsyncLocalisedStringStore:
    _global_string_store.localisation_dir = localisation_directory
    if callable(locale_hook):
        _global_string_store.install_locale_hook(locale_hook)
    _global_string_store.allow_empty = allow_empty
    return _global_string_store
