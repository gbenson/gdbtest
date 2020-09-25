#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import diffsum
import glob
import os
import sys

def filename_pairs():
    gcc_filenames = list(sorted(glob.glob("*gcc*.sum")))
    for gcc1_gcc2 in zip(gcc_filenames, gcc_filenames[1:] + [None]):
        g1, g2 = gcc1_gcc2
        c1 = g1.replace("gcc", "clang")
        #yield g1, c1      # Each baremetal-{gcc,clang}-* pair.
        if g2 is not None:
            yield g1, g2  # Each baremetal-gcc-{YYYYMMDD[N,N+1]} pair.
            c2 = g2.replace("gcc", "clang")
            yield c1, c2  # Each baremetal-clang-{YYYYMMDD[N,N+1]} pair.

def main():
    os.chdir(os.path.dirname(os.path.realpath(diffsum.__file__)))
    for filenames in filename_pairs():
        print(" <=> ".join(filenames), file=sys.stderr)
        for args in (#["--uncooked"],
                     #["--report-errors"],
                     #["--report-errors", "--verbose"],
                     [],
                     #["--verbose"],
                     #["--verbose", "--verbose"],
                    ):
            #print("  " + " ".join(args), file=sys.stderr)
            sys.argv[1:] = args + list(filenames)
            try:
                diffsum.main()
            except KeyboardInterrupt:
                raise
            except:
                print("FAIL!", file=sys.stderr)

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
