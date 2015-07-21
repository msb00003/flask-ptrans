#! /usr/bin/env python
"""
    Parse a JSON file with VCS conflict markers (<<<<<, ======, >>>>>>) into two versions of the
    python dictionary it represents, and tries to merge changes in the object rather than textually.

    Interactive resolution may be needed where the different versions of the file have different
    values for the same key.

    It can save the corrected file back if all changes are resolved. Then you can git add and continue your merge.

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
import copy
import json
import pprint
import re

# Python3 compatibility fixes
if not hasattr(__builtins__, 'raw_input'):
    raw_input = input


class UnableToResolveError(ValueError):
    pass


def conflicting_file_texts(filename):
    """
    given a file with conflict markers, return the text of the two conflicting versions of the file
    """
    conflict_rx = re.compile(r"""
        (^      # a group at the beginning of a line, containing...
         (?:<<<<<<< \s \S*$)  # 7< then a commit label, EOL
         |       # or
         (?:=======$)  # 7= to end of line
         |       # or
         (?:>>>>>>> \s \S*$)  # 7> then a commit label, EOL
         )
        """, re.X | re.M)
    with open(filename, "r") as f:
        all_text = f.read()
        chunks = conflict_rx.split(all_text)
        our_chunks = []
        their_chunks = []
        ours = True
        theirs = True
        for chunk in chunks:
            if chunk.startswith("<<<<<<<"):
                ours = True
                theirs = False
            elif chunk.startswith("======="):
                ours = False
                theirs = True
            elif chunk.startswith(">>>>>>>"):
                ours = True
                theirs = True
            else:
                if ours:
                    our_chunks.append(chunk)
                if theirs:
                    their_chunks.append(chunk)
        return ''.join(our_chunks), ''.join(their_chunks)


def merge_objects(object_a, object_b, interactive=False):
    """
    Try to merge two dictionaries known to be from JSON files

    Can merge in any keys that are different between the two,
    but not any keys that are the same with different values.
    """
    if type(object_a) is not dict or type(object_b) is not dict:
        raise TypeError("both objects must be dict")
    result = copy.deepcopy(object_a)
    for k, v in object_b.items():
        if k not in result:
            result[k] = copy.deepcopy(v)
        elif v != result[k]:
            resolved = False
            if interactive:
                while not resolved:
                    print("Need to resolve value of key [{0}]".format(k))
                    print("<<<<<<< (1)")
                    pprint.pprint(result[k])
                    print("=======")
                    pprint.pprint(v)
                    print(">>>>>>> (2)")
                    answer = raw_input("Choose 1, 2, (A)bandon: ?")
                    if answer == "2":
                        result[k] = copy.deepcopy(v)
                    elif answer in ("a", "A"):
                        break
                    resolved = answer in ("1", "2")
            if not resolved:
                raise UnableToResolveError(k)
    return result


def resolve_json_file(filename, interactive=False, update=False):
    """
    Resolve conflicts in named JSON file
    """
    json_a, json_b = conflicting_file_texts(filename)
    object_a = json.loads(json_a)
    object_b = json.loads(json_b)
    try:
        merged = merge_objects(object_a, object_b, interactive=interactive)
        merged_json = json.dumps(merged, indent=0, sort_keys=True)
        if update:
            with open(filename, "w") as f:
                f.write(merged_json)
        print(merged_json)
    except UnableToResolveError as err:
        print("Unable to Resolve key", err.args[0], "in", filename)


def main():
    """
    parse arguments and perform JSON conflict resolution
    """
    ap = argparse.ArgumentParser()
    add = ap.add_argument
    add("filename", help="JSON file requiring conflict resolution", nargs='+')
    add("-i", "--interactive", default=False, action="store_true", help="prompt to resolve changed values")
    add("--update", default=False, action="store_true", help="overwrite file if resolved without errors")
    args = ap.parse_args()
    for filename in args.filename:
        resolve_json_file(filename, interactive=args.interactive, update=args.update)

if __name__ == '__main__':
    main()