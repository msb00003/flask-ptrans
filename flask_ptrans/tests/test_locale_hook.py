from flask_ptrans import ptrans

from nose.tools import assert_equals, assert_raises


def locale_hook(locale):
    """
    for this test, return english strings for any locale beginning "en", spanish
    for any locale beginning "es" and empty for any other locale
    :param locale: locale name e.g. "en-GB"
    :return: a dict of translations
    """
    if locale.startswith("en"):
        return {
            "hello": "hello"
        }
    elif locale.startswith("es"):
        return {
            "hello": "hola"
        }
    else:
        return {}


def explode(locale):
    raise ValueError(locale)


def test_locale_hook_works():

    string_store = ptrans.LazyLocalisedStringStore(locale_hook=locale_hook)

    assert_equals(string_store.lookup("en-gb", "hello", "FAIL"), "hello")
    assert_equals(string_store.lookup("es-MX", "hello", "FAIL"), "hola")
    assert_equals(string_store.lookup("fr-FR", "hello", "hello"), "hello")


def test_locale_hook_only_called_once():

    string_store = ptrans.LazyLocalisedStringStore(locale_hook=locale_hook)
    assert_equals(string_store.lookup("en-gb", "hello", "FAIL"), "hello")

    string_store.install_locale_hook(explode)
    assert_equals(string_store.lookup("en-gb", "goodbye", "goodbye"), "goodbye")   # didn't explode


def test_locale_hook_called_again_if_no_results():

    string_store = ptrans.LazyLocalisedStringStore(locale_hook=locale_hook)
    assert_equals(string_store.lookup("fr-FR", "hello", "hello"), "hello")

    string_store.install_locale_hook(explode)
    assert_raises(ValueError, string_store.lookup, "fr-FR", "anything", "whatever")
