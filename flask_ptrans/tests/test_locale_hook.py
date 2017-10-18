from flask_ptrans import ptrans

from pytest import raises


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
    elif locale == "fr-FR":
        return {
            "hello": "bonjour"
        }
    else:
        return {}


def explode(locale):
    raise ValueError(locale)


def test_locale_hook_works():

    string_store = ptrans.LazyLocalisedStringStore(locale_hook=locale_hook)

    assert string_store.lookup("en-gb", "hello", "FAIL") == "hello"
    assert string_store.lookup("es-MX", "hello", "FAIL") == "hola"
    assert string_store.lookup("fr-FR", "hello", "hello") == "bonjour"


def test_locale_hook_only_called_once():

    string_store = ptrans.LazyLocalisedStringStore(locale_hook=locale_hook)
    assert string_store.lookup("en-gb", "hello", "FAIL") == "hello"

    string_store.install_locale_hook(explode)
    assert string_store.lookup("en-gb", "goodbye", "goodbye") == "goodbye"   # didn't explode


def test_locale_hook_called_again_if_no_results():

    string_store = ptrans.LazyLocalisedStringStore(locale_hook=locale_hook)
    assert string_store.lookup("de-DE", "hello", "hello") == "hello"

    string_store.install_locale_hook(explode)
    with raises(ValueError):
        string_store.lookup("de-DE", "anything", "whatever")


def test_fallback_to_base_language():

    string_store = ptrans.LazyLocalisedStringStore(locale_hook=locale_hook)
    assert string_store.lookup("fr-CH", "hello", "FAIL") == "FAIL"       # no fr-CH locale
    assert string_store.lookup("fr-FR", "hello", "FAIL") == "bonjour"    # fr-FR is OK
    assert string_store.lookup("fr", "hello", "FAIL") == "bonjour"       # base fr language works now
    assert string_store.lookup("fr-CH", "hello", "FAIL") == "bonjour"    # so does fr-CH which falls back to it
