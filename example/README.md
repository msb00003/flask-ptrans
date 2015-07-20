# Example application

## Running

Make sure flask_ptrans is installed, then

    python example/example.py
    
Point your browser at `http://localhost:5000`

You should see the example web page in English, with links for English, Esperanto and Pseudo.
All these are are links back to the same page with `locale` set on the query string of the URL.

## Making the Pseudo-locale work

Run the `pseudolocalise` script thus:

    pseudolocalise example/localisation/en-gb.json > example/localisation/qps-ploc.json
    
It will mangle the English strings into weird but more-or-less readable unicode characters.

## Adding more languages

In `example/localisation` copy `en-gb.json` to a new file named for the locale you want, and translate the
strings in it.  You can add more links in `example/templates/index.html` if you like, but even if you don't,
the app will see the new locale next time it is run.

If you don't specify a locale on the URL, the app will guess it from your browser settings. For example,
if you set your browser's first choice of language to Esperanto, that's the variant of the page you will see.

## Checking you didn't miss any strings

Running `check_templates -n example` should display

    {}
    
meaning there are no new strings used under `example/templates` that don't exist in the 
`example/localisation/en-gb.json` file.

Running `list_untranslated_strings --dir=example/localisation --locale=eo-xx` will show you any
strings that have an English version but no translation in Esperanto.
