#!/usr/bin/env python
"""
  list_untranslated_strings.py --dir DIRECTORY --locale LOCALE

  scan en-gb.json files, and see which strings in them haven't been translated to the specified locale yet
  default directory is ., default locale is it-IT

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
import argparse


def load_strings(directory, locale):
    filename = "{0}/{1}.json".format(directory, locale.lower())
    with open(filename) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add("dirs", default=[], nargs="*", help="directories to search for en-gb.json files [default .]")
    add("--locale", default="it-IT")
    args = ap.parse_args()
    if not args.dirs:
        args.dirs = ["."]
    for dirname in args.dirs:
        english_dict = load_strings(dirname, 'en-GB')
        other_dict = load_strings(dirname, args.locale)
        missing = sorted(k for k in english_dict
                         if english_dict[k].get("value") and not other_dict.get(k, {}).get("value"))
        for m in missing:
            print(m)

if __name__ == '__main__':
    main()
