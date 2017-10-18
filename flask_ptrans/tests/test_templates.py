"""
    nose tests for flask_ptrans jinja2 extension

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

from pytest import raises
import jinja2
import json
from flask_ptrans.ptrans import _global_string_store as string_store


def fake_jinja(template_dict):
    """
    make a jinja2 environment with ptrans extension, that loads its templates
    from the provided dictionary
    """
    jinja_env = jinja2.Environment(loader=jinja2.DictLoader(template_dict))
    jinja_env.add_extension("flask_ptrans.ptrans.ptrans")
    jinja_env.filters['tojson'] = json.dumps
    return jinja_env


FAKE_TEMPLATES = {
    "trivial.html": "<html></html>",
    "simple.html": "<p>{% ptrans test-simple %}Unknown{% endptrans %}</p>",
    "broken.html": "<p>{% ptrans test-broken %}{% for i in [1,2,3] %}{% end %}{% endptrans %}</p>",
    "script.html": "<script> strings = {{ ptrans_subset(locale, 'prefix-')|tojson|safe }}; </script>"
}


def test_trivial_template():
    """
    jinja2 templates can be rendered in the fake environment
    """
    env = fake_jinja(FAKE_TEMPLATES)
    t = env.get_template("trivial.html")
    assert t.render() == FAKE_TEMPLATES["trivial.html"]


def test_simple_template():
    """
    can use ptrans syntax : unknown strings not replaced
    """
    env = fake_jinja(FAKE_TEMPLATES)
    t = env.get_template("simple.html")
    assert t.render() == "<p>Unknown</p>"


def test_broken_template():
    """
    ptrans syntax fails to parse if it has nested control structures
    """
    env = fake_jinja(FAKE_TEMPLATES)
    with raises(jinja2.TemplateSyntaxError):
        env.get_template("broken.html")


def test_script_template():
    """
    can call ptrans_subset() to insert JSON dict of strings
    """
    env = fake_jinja(FAKE_TEMPLATES)
    t = env.get_template("script.html")
    string_store.locales['en-GB'] = {
        "prefix-a": "A",
        "prefix-b": "B",
        "other-z": "Z"
    }
    script_with_strings = t.render(locale='en-GB')
    script_without_strings = t.render(locale='es-ES')
    assert script_without_strings == '<script> strings = {}; </script>'
    assert script_with_strings == '<script> strings = {"prefix-a": "A", "prefix-b": "B"}; </script>'


# stop "import *" from taking anything except test cases
__all__ = [name for name in dir() if name.startswith("test_")]
