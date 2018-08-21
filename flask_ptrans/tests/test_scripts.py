# -*- encoding: utf-8 -*-   (for Python2, always the case in Python3)
"""
    nose tests for the utility scripts

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

from __future__ import print_function, unicode_literals

import json
import logging
import os
import tempfile
import textwrap
from contextlib import contextmanager

from flask_ptrans.scripts import aggregate_json, check_templates, resolve_json_conflicts, pseudolocalise


@contextmanager
def throwaway_dir():
    """
    yields path to a temporary directory which will be recursively deleted on exit from the 'with' block
    """
    dirpath = tempfile.mkdtemp()
    yield dirpath
    for path, dirnames, filenames in os.walk(dirpath, topdown=False):
        for f in filenames:
            os.unlink(os.path.join(path, f))
        for d in dirnames:
            os.rmdir(os.path.join(path, d))
    os.rmdir(dirpath)


def setup_module():
    check_templates.logger = logging.getLogger('chk')
    aggregate_json.logger = logging.getLogger('agg')
    logging.basicConfig()


def populate_with_fake_files(dirpath, data):
    """
    Populate a temp directory with small files constructed from a dict

    Dictionary keys ending in "/" create a sub-directory and recursively populate that using the
    corresponding value.

    Keys not ending in "/" represent file names.  If the entry is a string, it is written encoded in utf-8;
      otherwise it is dumped into the file as JSON.

    :param dirpath: directory path
    :param data: dict of {name:entry}
    """
    for key, value in data.items():
        if key.endswith("/"):
            subdirpath = os.path.join(dirpath, key.strip("/"))
            os.mkdir(subdirpath)
            populate_with_fake_files(subdirpath, value)
        else:
            filepath = os.path.join(dirpath, key)
            with open(filepath, "wb") as f:
                if isinstance(value, type(b"")):
                    f.write(value)
                elif isinstance(value, type("")):
                    f.write(value.encode('utf-8'))
                else:
                    f.write(json.dumps(value, indent=0, sort_keys=True).encode('utf-8'))


def test_populate_dir():
    """
    Confirm that temporary test files are actually removed
    """
    test_files = {
        "empty/": {},
        "notempty/": {"README": "Nothing to see here"}
    }
    with throwaway_dir() as dirpath:
        populate_with_fake_files(dirpath, test_files)
        gen = os.walk(dirpath)
        path, dirnames, filenames = next(gen)
        assert path == dirpath
        assert sorted(dirnames) == ["empty", "notempty"]
    # wiped
    assert not os.path.exists(dirpath)


def test_aggregate_json():
    """
        aggregate_json script combines files in subdirectories and omits empty strings
    """
    test_files = {
        "dir1/": {
            "fr-fr.json": {
                "key1": "bonjour",
                "key2": "",  # will be omitted
            },
            "en-us.json": {
                "key1": "hi",
                "key2": {"value": "howdy", "comment": "informal greeting"},  # only the value kept
                "key3": "see ya",
            },
        },
        "dir2/": {
            "fr-fr.json": {
                "key4": "ça va?"  # unicode will be preserved, key4 will be included
            },
            "qps-ploc.json": {  # pseudo-translation locale
                "key5": "pseudo"
            },
        },
    }
    expected = {
        "fr-fr": {
            "key1": "bonjour",
            "key4": "ça va?",
        },
        "en-us": {
            "key1": "hi",
            "key2": "howdy",
            "key3": "see ya",
        },
        "qps-ploc": {
            "key5": "pseudo",
        },
    }
    with throwaway_dir() as dirpath:
        populate_with_fake_files(dirpath, test_files)
        all_locales = aggregate_json.extract_all_locales([dirpath], pattern="*/*.json", encoding="utf-8")
        for locale in all_locales:
            assert all_locales[locale] == expected[locale]
        aggregate_json.save_locale_files(dirpath, all_locales)
        # check the round-trip via saved JSON
        with open(os.path.join(dirpath, "fr-fr.json"), "rb") as f:
            french = json.loads(f.read().decode("ascii"))  # strict JSON is ascii with \uXXXX escape codes
        assert french == expected['fr-fr']


def test_check_templates_find_strings():
    """
        check_templates finds translatable strings embedded in various ways
    """
    test_files = {
        "test/": {
            "syntax1.html": """
            <div>
              {% ptrans test-key1 %} body1 {% endptrans %}
              {% ptrans test-key--5 %} body5 {% endptrans %}
            </div>
            """,
            "quotes.html": '''
            <div>
              {{ ptrans_get(locale, 'test-key2', 'body2') }}
              {{ ptrans_get(locale, "test-key3", "body3") }}
              {{ ptrans_get(locale, "test-key4", """
                multi-line
                body4
                {insert}
                """, insert=0) }}
            </div>
            '''
        }
    }
    expected = {
        "test-key1": "body1",
        "test-key2": "body2",
        "test-key3": "body3",
        "test-key4": "multi-line body4 {insert}",
        "test-key--5": "body5",
    }
    with throwaway_dir() as dirpath:
        populate_with_fake_files(dirpath, test_files)
        string_store = check_templates.StringStore()
        string_store.scan_templates(dirpath)
        assert string_store.all_strings == expected
        assert string_store.new_strings == set(expected)  # all new


def test_check_templates_spot_changed_string():
    """
        check_templates can spot strings different in template and JSON file
    """
    test_files = {
        "templates/": {
            "test/": {
                "key1.html": """
                <div>{% ptrans key1 %}rhinoceros{% endptrans %}</div>
                """
            },
        },
        "localisation/": {
            "test/": {
                "en-gb.json": {"key1": {"value": "hippopotamus", "comment": "why not"}},
            }
        }
    }
    with throwaway_dir() as dirpath:
        populate_with_fake_files(dirpath, test_files)
        string_store = check_templates.StringStore()
        string_store.scan_json_files(os.path.join(dirpath, "localisation"), "en-gb.json", nested=True)
        assert string_store.all_strings == {"key1": "hippopotamus"}
        string_store.scan_templates(os.path.join(dirpath, "templates"))
        assert len(string_store.problems) == 1
        problem = string_store.problems[0]
        assert problem.strid == "key1"
        assert problem.body == "rhinoceros"
        assert problem.desc == "Changed string?"
        assert problem.serious is True


def test_check_templates_spot_duplicates():
    """
        check_templates spots duplicate keys in different subdirectories
    """
    test_files = {
        "dir1/": {
            "en-gb.json": {
                "key1": "hippopotamus",
                "key2": "giraffe"
            }
        },
        "dir2/": {
            "en-gb.json": {
                "key1": "hippopotamus",  # duplicate but equal string
                "key2": "camel"  # inconsistent string
            }
        }
    }
    expected = {
        "key1": "hippopotamus",
        "key2": "giraffe"
    }
    with throwaway_dir() as dirpath:
        populate_with_fake_files(dirpath, test_files)
        string_store = check_templates.StringStore()
        string_store.scan_json_files(dirpath, "en-gb.json", nested=True)
        assert string_store.all_strings == expected
        assert string_store.string_owner == {"key1": "dir1", "key2": "dir1"}
        assert len(string_store.problems) == 2
        for problem in string_store.problems:
            assert problem.desc == "Duplicate (from dir1)"


def test_resolve_json_conflicts():
    """
        can resolve a conflicted JSON file
    """
    test_files = {
        "conflicted.json": textwrap.dedent("""
        {
        "key1": "value1",
        <<<<<<< ours
        "key3": "",
        "key4": "value4"
        =======
        "key2": "value2"
        >>>>>>> theirs
        }""")
    }
    expected = {
        "key1": "value1",
        "key2": "value2",
        "key3": "",
        "key4": "value4",
    }
    with throwaway_dir() as dirpath:
        populate_with_fake_files(dirpath, test_files)
        filepath = os.path.join(dirpath, "conflicted.json")
        resolve_json_conflicts.resolve_json_file(filepath, interactive=False, update=True)
        with open(filepath, "r") as f:
            updated = json.load(f)
        assert updated == expected


def test_pseudolocalise_with_placeholders():
    """
    pseudolocalise.mangle_string preserves placeholders
    """
    translatable_string = "This {thing} {n: >+3,.7f} is {not} translatable"
    result = pseudolocalise.mangle_string(translatable_string)
    assert not (result == translatable_string)
    assert "{thing}" in result
    assert "{not}" in result
    assert "{n: >+3,.7f}" in result  # more extreme formatting than will ever be used, still survives mangling
    assert result.startswith("[") and result.endswith("]")
