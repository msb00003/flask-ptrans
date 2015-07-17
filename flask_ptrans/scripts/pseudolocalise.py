#! /usr/bin/env python
"""
    pseudolocalise json_file

    read translatable strings in the json file, and emit a pseudo-localised version.

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
import argparse
import sys
import json
import unicodedata
import random
import re


THINGS_ABOVE = ["TILDE", "DIAERESIS", "RING ABOVE", "CIRCUMFLEX ACCENT", "CARON"]
THINGS_BELOW = ["TILDE", "PLUS SIGN", "DOWN TACK", "UP TACK", "BRIDGE", "RING"]
THINGS_THROUGH = ["TILDE", "LONG SOLIDUS", "LONG STROKE"]

MANGLING_CHARS = (
    [unicodedata.lookup("COMBINING {0}".format(name))
        for name in THINGS_ABOVE] +
    [unicodedata.lookup("COMBINING {0} BELOW".format(name))
        for name in THINGS_BELOW] +
    [unicodedata.lookup("COMBINING {0} OVERLAY".format(name)) for name in THINGS_THROUGH]
)


def mangle_char(c):
    """
    Mangled (pseudolocalised) version of a character
    :param c: single-char string
    :return: short unicode string visually similar to the character but with accents and stuff
    """
    return c + random.choice(MANGLING_CHARS)


def mangle_string(s):
    """
    pseudolocalise the characters of a string, but preserving any parts inside
    braces, which are placeholders for inserted values, and shouldn't be translated.
    """
    placeholder_rx = re.compile(
        r"""(     # group of
            \{    # opening brace
            [-a-zA-Z0-9 :!_.,+<>=^]+   # identifiers and numbers and limited Python formatting syntax
            \}    # closing brace
            )""", re.X)
    parts = placeholder_rx.split(s)
    for i, part in enumerate(parts):
        if not part.startswith("{"):    # mangle its contents
            parts[i] = ''.join(mangle_char(c) for c in part)
    return '[' + ''.join(parts) + ']'


def main():
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add("-v", "--verbose", default=False, action="store_true")
    add("filename")
    args = ap.parse_args()

    with open(args.filename) as json_file:
        string_dict = json.load(json_file)
    for key, trans in string_dict.items():
        if isinstance(trans, dict):
            before = trans.get("value", "")
            mangled = mangle_string(before)
            trans["value"] = mangled
        else:
            before = trans
            mangled = mangle_string(before)
            string_dict[key] = mangled
        if args.verbose:
            print(before.encode('utf-8'), "->", mangled.encode('utf-8'), file=sys.stderr)

    print(json.dumps(string_dict, sort_keys=True, indent=2))

if __name__ == '__main__':
    main()
