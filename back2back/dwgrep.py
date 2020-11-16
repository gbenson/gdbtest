#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import subprocess
import sys

def dwgrep(pattern, filename, check=False, debug=False):
    if debug:
        print("\x1B[31m%s\x1B[0m" % filename)
    cp = subprocess.run(["dwarfdump", filename],
                        check=check,
                        stdout=subprocess.PIPE,
                        encoding="utf-8")
    for line in cp.stdout.split("\n"):
        if not line:
            continue
        if pattern.search(line):
            print(filename+":", line)

def main():
    if len(sys.argv) < 3:
        print("\n".join((
            "usage: dwgrep PATTERN FILE_OR_DIR...",
            "(with PATTERN per https://docs.python.org/3/library/re.html)",
            "e.g. dwgrep 'DW_AT_count\s+<0x' "
            + "~/2020-11-12/with-{gcc,clang}/gdb/testsuite/outputs")),
              file=sys.stderr)
        sys.exit(1)
    pattern = re.compile(sys.argv[1], re.I)
    for filename in sys.argv[2:]:
        if not os.path.isdir(filename):
            dwgrep(pattern, filename)
            continue
        for dirpath, dirnames, filenames in os.walk(filename):
            for filename in filenames:
                filename = os.path.join(dirpath, filename)
                if not os.access(filename, os.X_OK):
                    continue
                dwgrep(pattern, filename)

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
