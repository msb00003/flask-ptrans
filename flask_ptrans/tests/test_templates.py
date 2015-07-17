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

from nose.tools import assert_equals, assert_raises
import jinja2


def fake_jinja(template_dict):
    """
    make a jinja2 environment with ptrans extension, that loads its templates
    from the provided dictionary
    """
    jinja_env = jinja2.Environment(loader=jinja2.DictLoader(template_dict))
    jinja_env.add_extension("flask_ptrans.ptrans.ptrans")
    return jinja_env


FAKE_TEMPLATES = {
    "trivial.html": "<html></html>",
    "simple.html": "<p>{% ptrans test-simple %}Unknown{% endptrans %}</p>",
    "broken.html": "<p>{% ptrans test-broken %}{% for i in [1,2,3] %}{% end %}{% endptrans %}</p>",
}


def test_trivial_template():
    """
    jinja2 templates can be rendered in the fake environment
    """
    env = fake_jinja(FAKE_TEMPLATES)
    t = env.get_template("trivial.html")
    assert_equals(t.render(), FAKE_TEMPLATES["trivial.html"])


def test_simple_template():
    """
    can use ptrans syntax : unknown strings not replaced
    """
    env = fake_jinja(FAKE_TEMPLATES)
    t = env.get_template("simple.html")
    assert_equals(t.render(), "<p>Unknown</p>")


def test_broken_template():
    """
    ptrans syntax fails to parse if it has nested control structures
    """
    env = fake_jinja(FAKE_TEMPLATES)
    assert_raises(jinja2.TemplateSyntaxError, env.get_template, "broken.html")

# stop "import *" from taking anything except test cases
__all__ = [name for name in dir() if name.startswith("test_")]
