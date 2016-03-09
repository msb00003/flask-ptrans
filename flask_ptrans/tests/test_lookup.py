"""
  nose tests for string lookup in different locales

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

from nose.tools import assert_equals
from flask_ptrans import ptrans

FAKE_LOCALES = {
    "en-GB": {"hello": "hello",
              "hello-who": "Hello, {who}!",
              "other-water": "water",
              "only-english": "only english"},
    "es-ES": {"hello": "hola",
              "hello-who": "Hola, {who}!",
              "other-water": "agua"},
    "fr-FR": {"hello": {"value": "bonjour", "comment": "A greeting"}}  # longer format with comment
}


def fake_string_store(fake_locales):
    store = ptrans.LazyLocalisedStringStore()
    store.locales = fake_locales.copy()
    return store


def test_simple_lookup():
    """
    lookup return the correct string for the locale?
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup("es-ES", "hello", "FAIL"), "hola")
    assert_equals(store.lookup("en-GB", "hello", "FAIL"), "hello")
    assert_equals(store.lookup("fr-FR", "hello", "FAIL"), "bonjour")


def test_lookup_no_string():
    """
    lookup falls back to the default when string ID unknown
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup("en-GB", "goodbye", "FAIL-EN"), "FAIL-EN")


def test_lookup_no_locale():
    """
    lookup falls back to the default when locale is unknown
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup("jp-JP", "hello", "FAIL-JP"), "FAIL-JP")


def test_lookup_locale_wrong_type():
    """
    lookup falls back to the default when locale is wrong type (e.g. None)
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup(None, "hello", "FAIL-TYPE"), "FAIL-TYPE")


def test_lookup_with_substitution():
    """
    lookup can perform keyword substitutions
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup("en-GB", "hello-who", "FAIL", who="World"), "Hello, World!")


def test_lookup_substitution_fail():
    """
    if substitutions fail, string is in correct locale but no replacements
    """
    store = fake_string_store(FAKE_LOCALES)
    # mis-spelled keyword argument to make sub of {who} fail
    assert_equals(store.lookup("es-ES", "hello-who", "Hello, {who}!", woh="World"), "Hola, {who}!")


def test_lookup_substitution_wrong_type():
    """
    substitutions still done on fallback text even if locale is wrong type
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup(None, "hello-who", "Hello, {who}!", who="World"), "Hello, World!")


def test_lookup_cascade_simple():
    """
    lookup_cascade finds correct string for locale
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup_cascade("en-GB", "hello"), "hello")
    assert_equals(store.lookup_cascade("es-ES", "hello"), "hola")


def test_lookup_cascade_fallback_string():
    """
    fall back to fallback string
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup_cascade("en-GB", "goodbye", fallback="Goodbye"), "Goodbye")
    assert_equals(store.lookup_cascade("es-ES", "goodbye", fallback="Adios"), "Adios")


def test_lookup_cascade_fallback_locale():
    """
    fall back to other locale
    """
    store = fake_string_store(FAKE_LOCALES)

    # Fall back to en-GB by default
    assert_equals(store.lookup_cascade(None, "hello"), "hello")
    # Fall back to specified locale
    assert_equals(store.lookup_cascade(None, "hello", fallback_locale="es-ES"), "hola")


def test_lookup_cascade_no_fallback():
    """
    fall back to string key
    """
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.lookup_cascade("en-GB", "goodbye"), "goodbye")
    assert_equals(store.lookup_cascade("es-ES", "goodbye"), "goodbye")
    # If string does not exist in fallback locale, even if it does exist in en-GB,
    # fall back to key
    assert_equals(store.lookup_cascade("es-AR", "only-english", fallback_locale="es-ES"), "only-english")


def test_subset():
    store = fake_string_store(FAKE_LOCALES)
    assert_equals(store.subset('es-ES', 'hello'),
                  {"hello": "hola",
                   "hello-who": "Hola, {who}!"})
    assert_equals(store.subset('es-ES', 'hello-'),
                  {"hello-who": "Hola, {who}!"})
    assert_equals(store.subset('es-ES', 'nothing'), {})
    assert_equals(store.subset(None, 'hello'), {})


# stop "import *" from taking anything except test cases
__all__ = [name for name in dir() if name.startswith("test_")]
