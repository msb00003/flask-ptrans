#! /usr/bin/env python
"""
    aggregate_json: find all xx-YY.json files (names are locales) in subdirectories,
    and aggregate all of the same locale into one file in the top-level directory.

    Aggregation is done thus:
    1. keys must not be duplicates unless their values are identical.
    2. value of key must be a string or a dict with a "value" that is a string.
    3. the keys of the output file are sorted

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

from __future__ import unicode_literals, print_function

import os
import argparse
import glob
import re
import logging
from collections import defaultdict
import json


def extract_all_locales(sources, pattern="*.json", encoding="utf-8"):
    """
    Aggregate all translated strings into one dict per locale
    :param sources: list of source directories
    :param pattern: glob pattern for files to consider
    :return: dict of dicts of all strings found, {locale:{key:value}}
    """
    all_locales = defaultdict(dict)
    total_errors = 0
    locale_rx = re.compile(r'(?P<locale>[a-z]+(-[a-z]+)?).json')
    for source in sources:
        filename_pattern = os.path.join(source, pattern)
        for filename in glob.glob(filename_pattern):
            basename = os.path.basename(filename)
            locale_match = locale_rx.match(basename)
            if not locale_match:
                continue
            locale = locale_match.group('locale')
            locale_dict = all_locales[locale]
            total_errors += extract_locale_strings(filename, locale_dict, encoding)
    # put count of errors in the dict if there were any
    if total_errors:
        all_locales["ERRORS"] = total_errors
    return all_locales


def extract_locale_strings(filename, locale_dict, encoding):
    """
    :param filename: JSON file containing strings
    :param locale_dict: dictionary to update with strings
    :returns number of errors found
    """
    errors = 0
    with open(filename, "rb") as f:
        logger.info("Scanning %s", filename)
        try:
            data = f.read()
            text = data.decode(encoding)
            strings_dict = json.loads(text)
        except ValueError:
            logger.error("Invalid JSON in %s", filename)
            return 1
        except UnicodeDecodeError:
            logger.error("Invalid %s in %s", encoding, filename)
            return 1
        for k, v in strings_dict.items():
            if type(v) is dict:
                value = v.get("value")
            else:
                value = v
            if not isinstance(value, (str, type(u''))):
                logger.error("Invalid value for %s in %s", k, filename)
                errors += 1
                continue
            if k in locale_dict and value != locale_dict[k]:
                logger.error("Duplicate key %s in %s", k, filename)
                errors += 1
                continue
            if not value:
                continue    # don't include empty strings
            locale_dict[k] = value
        return errors


def save_locale_files(destination, all_locales):
    """
    :param destination: destination directory
    :param all_locales: dict of all locales and their strings {locale:{key:value}}
    :return:
    """
    for locale, string_dict in all_locales.items():
        filename = os.path.join(destination, locale + ".json")
        with open(filename, "w") as f:
            json.dump(string_dict, f, sort_keys=True, indent=0)
            logger.info("Wrote %s strings in %s", len(string_dict), filename)


def main():
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add("-v", "--verbose", default=False, action='store_true', help="Verbose output")
    add("-e", "--encoding", default="utf-8", help="input encoding (default utf-8)")
    add("destination", help="directory to put aggregated files")
    add("sources", nargs="*", help="directory to look for json files [default is subdirs of destination]")
    args = ap.parse_args()
    if args.sources:
        file_pattern = "*.json"
        sources = args.sources
    else:
        sources = [args.destination]
        file_pattern = "*/*.json"
    global logger
    logger = logging.getLogger()
    logging.basicConfig()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    all_locales = extract_all_locales(sources, pattern=file_pattern, encoding=args.encoding)
    # only write output files if there were no errors, have failing exit code otherwise
    num_errors = all_locales.pop("ERRORS", 0)
    if num_errors == 0:
        save_locale_files(args.destination, all_locales)
    else:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
