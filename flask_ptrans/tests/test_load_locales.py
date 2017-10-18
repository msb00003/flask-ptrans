"""
 nose tests for loading and selecting locales

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

import os
import json
import tempfile

import pytest

from contextlib import contextmanager
from flask_ptrans import ptrans


FAKE_LOCALES = {
    "en-gb": {"hello": "hello"},
    "en-US": {"hello": {"value": "howdy"}},  # alt JSON style
    "es-ES": {"hello": "hola"},
    "en-XX": {"hello": 0},  # invalid string
    "bg-BG": {"hello": "Здравейте"}
}


@contextmanager
def temporary_string_store(fake_locales, broken=False):
    """
     with temporary_string_store(fake_locales) as store:
       string = store.lookup(locale, key, fallback)

    Make a LazyLocalisedStringStore initialised to work from a
    temporary directory of locale.json files, which will be
    emptied out and deleted after the with statement.

    :param fake_locales: dict of {locale:{key:value}}
    :param broken: true to generate invalid JSON
    :return: a ptrans.LazyLocalisedStringStore
    """
    dirpath = tempfile.mkdtemp()
    files_to_delete = []
    for locale in fake_locales:
        filename = os.path.join(dirpath, locale + ".json")
        files_to_delete.append(filename)
        with open(filename, "w", encoding="utf-8") as f:
            if broken:
                f.write("#this is not valid JSON#")
            else:
                json.dump(fake_locales[locale], f)
    store = ptrans.LazyLocalisedStringStore(dirpath)
    yield store
    for filename in files_to_delete:
        os.unlink(filename)
    os.rmdir(dirpath)


@pytest.mark.parametrize("locale", ["en-US", "bg-BG"])
def test_lazy_loading(locale):
    """
    before trying to fetch a string, no locales loaded
    afterwards, only the needed locale loaded
    """
    with temporary_string_store(FAKE_LOCALES) as store:
        assert not store.locales
        store.lookup(locale, "hello", "hello")
        assert locale in store.locales
        # store is allowed to cache other locales as same dict, but it definitely
        # shouldn't have loaded any others
        assert all(d is store.locales[locale] for d in store.locales.values())


def test_known_locales():
    """
    known locales are the specific ones in FAKE_LOCALES plus generic languages
    """
    expected = set()
    for locale in FAKE_LOCALES:
        expected.add(locale)
        lang, hyphen, variant = locale.partition('-')
        expected.add(lang)
    with temporary_string_store(FAKE_LOCALES) as store:
        known_locales = store.known_locales
        assert known_locales == expected
        assert store.known_locales is known_locales  # not scanned twice


def test_partial_match():
    """
    requesting es-XX loads es-ES file and caches it as es-XX
    """
    with temporary_string_store(FAKE_LOCALES) as store:
        assert store.lookup("es-XX", "hello", "FAIL") == "hola"
        assert "es-XX" in store.locales
        assert "es-ES" in store.locales  # cached actual locale
        # check that locale file is not reloaded for same language
        assert store.lookup("es-ES", "hello", "FAIL") == "hola"
        assert store.locales["es-XX"] is store.locales["es-ES"]
        # coverage for case where es-ES already loaded
        assert store.lookup("es-YY", "hello", "FAIL") == "hola"


def test_failed_match():
    """
    requesting a locale that has no match at all gets an empty dict
    """
    with temporary_string_store(FAKE_LOCALES) as store:
        store.lookup("jp-JP", "hello", "hello")
        assert set(store.locales) == {'jp-JP'}
        assert store.locales["jp-JP"] == {}


def test_broken_json():
    """
    when JSON files are broken in some way, always get empty dict
    """
    with temporary_string_store(FAKE_LOCALES, broken=True) as store:
        store.lookup("en-gb", "hello", "hello")
        assert "en-gb" in store.locales
        assert store.locales["en-gb"] == {}


def test_set_no_directory():
    """
    explicitly (for coverage) set no global localisation directory
    """
    ptrans.init_localisation(None)


def test_best_locale_no_request():
    """
    best_locale returns en-GB if flask has no request context or
    if no locales are known
    """
    assert ptrans.best_locale() == "en-GB"


# stop "import *" from taking anything except test cases
__all__ = [name for name in dir() if name.startswith("test_")]
