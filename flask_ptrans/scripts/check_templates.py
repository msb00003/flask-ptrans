#!/usr/bin/env python
"""
  check_templates - check html templates for {% ptrans %} inserts, and extract strings from them for
  localisation. Check them against JSON files for Pootle translation, and report any inconsistencies and duplicates.

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

import re
import os
import json
import argparse
import logging
import glob
from collections import defaultdict, namedtuple


def strip_for_html(s1):
    """
    :param s1: a string with maybe arbitrary whitespace in it
    :return: trimmed string with all internal whitespace reduced to single spaces
    """
    return re.sub("\s+", " ", s1).strip()


class StringStore(object):
    """ Data structure for set of translatable strings

        These are in a set of dictionaries loaded from JSON files. Each is "owned" by the
        component with same name as the folder containing the file.
        The "shared" folder is special. Strings in shared can be used by any template,
        but strings in (for example) car_hire can only be used by a template inside
        the top level template directory with the same name.
        No overlap in string IDs is allowed between folders.

    """

    Problem = namedtuple("Problem", "desc strid filename body serious")

    def __init__(self):
        self.all_strings = {}       # {strid:value}
        self.owner_set = set()      # folder names that contain a json strings file
        self.string_owner = {}      # {strid:owner}
        self.new_strings = set()    # new strings found
        self.string_occurrences = defaultdict(set)  # {strid:{template_filename}}
        self.problems = []          # [Problem]

    @property
    def num_strings_in_json(self):
        return len(self.all_strings)

    @property
    def num_strings_in_templates(self):
        return len(self.string_occurrences)

    @property
    def serious_problems(self):
        return [prob for prob in self.problems if prob.serious]

    def add_problem(self, problem, strid, filename, string="", serious=True):
        """
        Record a problem
        :param problem: brief description of problem
        :param strid: translatable string ID
        :param filename: file where the problem was noticed
        :param string: associated translation string
        :param serious: whether problem is serious
        """
        self.problems.append(StringStore.Problem(problem, strid, filename, string, serious))

    def scan_json_files(self, directory, json_filename, nested=False):
        """
        Scan under top level directory for json files
        and incorporate the strings from them into all_strings.
        If nested is True, look only in subdirectories, which are then considered to be
        the owners of the strings.

        :param directory: localisation directory pathname
        :param json_filename: filename for JSON string files
        """
        if nested:
            json_files = glob.glob(os.path.join(directory, '*', json_filename))
        else:
            json_files = glob.glob(os.path.join(directory, json_filename))
        for filename in sorted(json_files):
            if nested:
                dir_name = os.path.split(filename)[0]
                owner = os.path.basename(dir_name)
            else:
                owner = "shared"
            self.owner_set.add(owner)
            with open(filename, "r") as f:
                string_dict = json.load(f)
                for k, v in string_dict.items():
                    if type(v) is dict and "value" in v:
                        value = v["value"]
                    elif isinstance(v, (str, type(u''))):
                        value = v
                    else:
                        self.add_problem("No value", k, filename)
                        continue
                    if k in self.all_strings:
                        other_owner = self.string_owner[k]
                        self.add_problem("Duplicate (from %s)" % other_owner, k, filename, value)
                        continue
                    self.all_strings[k] = value
                    self.string_owner[k] = owner

    def scan_templates(self, directory):
        """
        Scan under top level directory for HTML template files. Identify
        translated strings, check they are in the JSON files with the same
        value and are appropriate for the folder they were found under.
        :param directory: template directory pathname
        """

        ptrans_rx = re.compile(r"""
            # RegEx to extract {% ptrans (strid)%}(body){% endptrans %} groups
            \{% \s* ptrans \s+ (?P<strid>[A-Za-z0-9_-]*) \s* %} # ptrans tag with string ID
            (?P<body>   # group 'body' is made of
            (           # either...
            [^{]        # not a left brace
            |           # or...
            ( \{ (?! % ))   # left brace not followed by %
            )*      # repeated or empty
            )       # end of 'body' group - next will be end of string or '{%'
            {% \s* endptrans \s* %}  # expect a matching endptrans tag
            """, re.X)

        ptrans_get_rx = re.compile(r'''
            # RegEx to extract ptrans_get(locale, '(strid)', '(body)'...) groups
            ptrans_get\( \s* [a-zA-Z_0-9]+ \s* , \s* # identifier in locale arg
            (?P<qstrid> # quoted string ID is
              (         # either
              '[A-Za-z0-9_-]+'  # single-quoted ID
              |         # or
              "[A-Za-z0-9_-]+"  # double-quoted ID
              ))
              \s* , \s*
            (?P<qbody> # quoted body is
              (         # either
              '[^']*'  # single quoted string with no single quotes at all
              |         # or
              "[^"]+"  # double quoted string with no double quotes at all
              |
              """[^"]+""" # triple-dq string with no double quotes at all
              ))
              \s* [,)]
            ''', re.X)

        owner = "Unknown"
        for dirpath, dirnames, basenames in os.walk(directory):
            # When we walk into a dir named same as one of the 'owner' dirs found
            # when scanning for json files, set that as the 'owner' of the template
            dir_name = os.path.basename(dirpath)
            if dir_name in self.owner_set:
                owner = dir_name
            for basename in basenames:
                if not re.match(r".*\.(html|htm|json|j2|xml)$", basename):
                    continue    # probably not a template file
                filename = os.path.join(dirpath, basename)  # full path to file
                with open(filename, "r") as f:
                    logger.debug("Inspecting %s", filename)
                    html = f.read()
                    for match in ptrans_rx.finditer(html):
                        body = match.group('body')
                        strid = match.group('strid')
                        self.found_string(strid, body, filename, owner)
                    for match in ptrans_get_rx.finditer(html):
                        qbody = match.group('qbody')
                        qstrid = match.group('qstrid')
                        body = qbody.strip(qbody[0])      # take off whichever quotes
                        strid = qstrid.strip(qstrid[0])   # take off whichever quotes
                        self.found_string(strid, body, filename, owner)

    def found_string(self, strid, body, filename, owner):
        """ found a translatable string in a template file """
        body = strip_for_html(body)  # normalise white space for HTML
        if not strid:
            self.add_problem("String with no ID", "", filename, body)
            return
        strid_owner = self.string_owner.get(strid)
        if strid_owner is None:
            self.add_problem("New string", strid, filename, body, serious=False)
            self.new_strings.add(strid)     # new string found
            self.all_strings[strid] = body  # so we can check for same value if it occurs elsewhere
            self.string_owner[strid] = owner  # so we only report it as new once
        elif strid_owner not in (owner, "shared"):
            self.add_problem("Using %s in %s" % (strid_owner, owner), strid, filename, body)
        elif body.strip() == "":
            self.add_problem("Empty string", strid, filename, body)
        elif body != strip_for_html(self.all_strings[strid]):
            self.add_problem("Changed string?", strid, filename, body)
        self.string_occurrences[strid].add(filename)

    def new_strings_json(self):
        """ json representation of the new strings """
        new_string_dict = {k: {"value": self.all_strings[k]} for k in self.new_strings}
        return json.dumps(new_string_dict, sort_keys=True, indent=2)


def log_problems(string_store):
    logger.info("Strings in JSON: %d", string_store.num_strings_in_json)
    logger.info("Strings in templates: %d", string_store.num_strings_in_templates)
    logger.info("New Strings: %d", len(string_store.new_strings))

    for problem in string_store.problems:
        level = logging.WARNING if problem.serious else logging.INFO
        logger.log(level, "%s\t%s\t%s\t%r", problem.desc, problem.strid, problem.filename, problem.body)


def main():
    """
    parse arguments and run the correct checks
    """
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add("-f", "--json-file", help="filename for en-gb strings [%(default)s]", default="en-gb.json")
    add("directory", help="app directory. Should contain templates and localisation subdirectories")
    add("-v", "--verbose", default=False, action='store_true', help="Verbose output")
    add("-n", "--new-strings", default=False, action='store_true', help="output new strings as JSON")
    add("--nested", default=False, action="store_true", help="localisations are nested in subdirectories")
    args = ap.parse_args()
    global logger
    logger = logging.getLogger('transcheck')
    logging.basicConfig()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    string_store = StringStore()
    string_store.scan_json_files(os.path.join(args.directory, 'localisation'), args.json_file, nested=args.nested)
    string_store.scan_templates(os.path.join(args.directory, 'templates'))
    if args.new_strings and not string_store.serious_problems:
        print(string_store.new_strings_json())
    else:
        log_problems(string_store)


if __name__ == '__main__':
    main()
