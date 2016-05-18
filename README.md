Flask Extension for Template Localisation
=========================================

# Motivation

The string translation tool, [Pootle](https://github.com/translate/pootle), accepts translatable strings in the form of a JSON
file mapping keys to values (with associated comments to aid translation).

## Example

    {"flights_intro_welcome": {
        "value":"Welcome!",
        "comment":"appears as page heading"},
     ...}

Unlike `gettext` and other tools that are based on it (such as the existing Flask extension Babel,
and the built in `i18n` extension to `Jinja2` that comes with Flask), the string ID or key for 
each translatable string is an identifier, not the untranslated English text.

Therefore, if you are using Pootle in that way (as Skyscanner are), you need some way of inserting
localised strings into templates using the identifiers in the JSON files that Pootle produces, and
falling back to the untranslated string if no match is found.


# Installation

From the git repository, you can install directly using `pip install .` or build a .tar.gz or zip file
with `python setup.py sdist` (will appear in the `dist` directory) and install with `pip` from that.

The package depends on Flask, so pip will install the latest
versions of Flask and its dependencies if you don't already have them.

The tests require `nose`, so you might want to `pip install nose` if you want to run the tests.


# Activating the Extension

Within your Flask application, before you begin rendering pages, you need to import the `ptrans`
module, and tell it where to find the JSON files containing translations, and add the extension
to you app's `Jinja` environment:

    from flask_ptrans import ptrans
    
    ptrans.init_localisation(path_to_directory_of_json_files)
    app = Flask(...)
    app.jinja_env.add_extension('flask_ptrans.ptrans.ptrans')

The JSON files should be named using the locale of the strings they contain, in lower-case. For example,
`en-gb.json` or `pt-br.json`. They can be in the Pootle format as described above, or be a simple mapping from
string ID to translated string (since you don't need to include translator comments in a deployed application).

By default, empty translations are treated the same as missing translations (fall back to default string),
but you can override this if you are really sure by specifying ``init_localisation(path, allow_empty=True)``.

You can get fancy and provide your own way to find translations instead of looking for files in a directory:

    def find_translation(locale: str) -> dict:
        """
        accept a locale and return a dict {key: string} for that language
        """
        ...
        
    ptrans.init_localisation(locale_hook=find_translation)

This allows you to (for example) pull translations from a web service. Once the function returns a nonempty dict,
that will be cached indefinitely (same as it is when translations are found in a file), and the function won't be
called again for the same locale.

# The `ptrans_get` Function

Once the extension has been added, a function `ptrans_get(locale, string_id, fallback, **kwargs)` is available
in all templates, and can be used anywhere you could insert an expression inside {% %} or {{ }}.

If keyword arguments are given, then `str.format` is used to interpolate them into the resulting translated
string. For example:

    {{ ptrans_get(locale, STRID, 'Your reference is {ref}.', ref=booking_reference) }}

If any are missing, the string is returned as-is, with no placeholders filled in.


# Template Syntax

The extension adds one piece of template syntax.

    {% ptrans STRID %}Fallback text{% endptrans %}

This simply replaces the enclosed text with the translated string for the given string ID STRID, or leaves
it unchanged if no translation was found. It is roughly the same as inserting:

    {{ ptrans_get(locale, STRID, 'Fallback text') }}

If you need to do anything fancy (such as inserting values into placeholders in the string) you will
need to use the function, because the template syntax is limited to plain substitution.

You may need to insert a subset of the translated strings into the page for a script to use. In that case,
you can use `ptrans_subset` to insert a JSON object containing key,value pairs in the specified locale, for
all keys matching one or more prefixes.

    <script>
    strings = {{ ptrans_subset(locale, 'people-', 'dates-')|tojson|safe }};
    </script>
    
Always filter the result with `tojson|safe` unless you want Python dictionary syntax and HTML escaping. For most
uses you want proper JSON without any escaped characters inside your script.


# Choosing a Locale

Because `{% ptrans %}` expects `locale` to be in the environment, pass the variable `locale` into `render_template`
when you are rendering a page that uses the template syntax.

    render_template('index.html', locale=selected_locale)

How you decide what locale to use depends on your application. You could code it into the URLs and only provide
links to a specific set of translated pages, for example. Or you could select it based on the `Accept-Language` header
sent from the user's browser.

For doing that more conveniently, `ptrans` provides a function `best_locale()`. In a request context, this
returns the best match between the browser's language preference and the set of JSON files deployed with the
application. The set of supported locales is only created once and then cached, so there is no performance
problem if you want to call `best_locale()` for each request.


# Localisation files

There are two formats of localisation file, both JSON. The simple or output format is a single dictionary containing
string IDs as keys and strings as values.

The full or input format is a dictionary whose keys are string IDs, but whose values are dictionaries with "value"
and "comment" entries. The "value" is the string to be translated. The "comment" is for a human translator to read,
and should help explain the context enough to make the translation unambiguous.


# Utility Scripts

The following scripts will be installed by pip, to assist the localisation process:

## `ptrans_check`

    ptrans_check [options] directory

Looks in the directory for subdirectories `templates` and `localisation`. Scans the template directory recursively to
look for uses of `ptrans_get` or the `{% ptrans %}` directive, and scans the localisation directory for
`en-gb.json` files containing string IDs. Logs any new strings in the template that are not in the localisation file,
and strings that are there but differ from the default text used in the template.

With the `--new-strings` option, writes any new strings used in the templates but not defined in the JSON files to
standard output in the full JSON format. These can be checked and copied into the translation files.

## `ptrans_aggregate`

    ptrans_aggregate dest [source ...]

This collects JSON localisation files (in either format) from the source directories (by default, any subdirectories of
the destination) and aggregates all the strings that belong in the same locale from all the files that are found.
 
It produces one file per locale in the destination direction. These are in the simple format without comments.

## `ptrans_untranslated`

    ptrans_untranslated [--locale locale] [directory ...]

Looks in each specified directory for `en-gb.json` (the default is the current directory) and the translation file for
the specified locale (default is `it-IT`). Lists the IDs of strings that are nonempty in the en-GB locale but empty
or missing in the other locale.


## `ptrans_pseudolocalise`

    ptrans_pseudolocalise file

Reads a translation file in the simple output format, and produces a pseudo-localised version on standard output by
mangling the characters with unicode diacritics, so the text is kind of readable but recognisably altered.

It leaves alone any part of the translatable string that is in curly braces, because that is probably a named
placeholder for inserting values with Python's `format` syntax.


## `ptrans_resolve`

    ptrans_resolve [--update] [--interactive] filename

This is a utility for resolving git merge conflicts in a JSON file. It parses a file containing conflict markers,
and constructs dictionaries for the two versions of the file. Then it attempts to resolve the conflict by combining
the dictionaries at an object level rather than textually.

With the `--interactive` option it prompts the user to choose which of two different objects should be chosen when
an entry exists but is different in both versions.

With the `--update` option it will write the resolved file back in-place, provided that it is able to resolve the
conflicts without any problems.
