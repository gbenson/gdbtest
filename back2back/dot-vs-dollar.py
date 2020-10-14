# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import glob
import os
import re
import subprocess

def is_elf(filename):
    return open(filename, "rb").read(4) == b"\177ELF"

_DW2_STRING_RE = re.compile(r'^\s*\[\s*[0-9a-f]+\]\s+"(.*)"$')

def dw2_strings(filename):
    cp = subprocess.run(["eu-readelf",
                         "--debug-dump=str",
                         filename],
                        check=True,
                        stdout=subprocess.PIPE,
                        encoding="utf-8")
    for line in cp.stdout.split("\n"):
        m = _DW2_STRING_RE.match(line)
        if m is None:
            #print("\x1B[33m%s\x1B[0m" % repr(line))
            assert (not line
                    or line.lstrip() == "Offset  String"
                    or line.startswith("DWARF section ["))
            continue
        #print(m.group(1))
        yield m.group(1)

def main():
    for gcc_filename in sorted(glob.glob("/gdbtest/2020-10-12/with-gcc/"
                                         + "gdb/testsuite/outputs/gdb.*"
                                         + "/*/gdb.sum")):
        # Only examine directories where Clang FAILed a test
        # that GCC didn't fail.
        cfe_filename = gcc_filename.replace("/with-gcc/", "/with-clang/")
        gcc_sumfile = open(gcc_filename).read()
        for line in open(cfe_filename).readlines():
            if not line.startswith("FAIL:"):
                line = line[1:]
            if not line.startswith("FAIL:"):
                continue
            if gcc_sumfile.find(line) == -1:
                #print("CFE", line.rstrip())
                break
        else:
            continue

        gcc_test_topdir = os.path.dirname(gcc_filename)
        testname = os.sep.join(gcc_test_topdir.split(os.sep)[-2:])
        #if not gcc_test_topdir.endswith("/gdb.base/msym-lang"):
        #    continue
        #print("Examining", gcc_test_topdir)
        for dirpath, dirnames, filenames in os.walk(gcc_test_topdir):
            for gcc_filename in filenames:
                gcc_filename = os.path.join(dirpath, gcc_filename)
                if not is_elf(gcc_filename):
                    continue
                cfe_filename = gcc_filename.replace("/with-gcc/",
                                                    "/with-clang/")
                if not os.path.isfile(cfe_filename):
                    continue
                if not is_elf(cfe_filename):
                    continue
                try:
                    cfe_strings = \
                        [s for s in dw2_strings(cfe_filename) if "$" in s]
                except subprocess.CalledProcessError:
                    continue
                if not cfe_strings:
                    continue
                #print("%s.exp: CFE has %s"
                #      % (testname,
                #         ", ".join(map(repr, cfe_strings))))
                try:
                    gcc_strings = \
                        [s for s in dw2_strings(gcc_filename)
                         if s in [cs.replace("$", ".")
                                  for cs in cfe_strings]]
                except subprocess.CalledProcessError:
                    continue
                if not gcc_strings:
                    continue
                for gs in gcc_strings:
                    cs = gs.replace(".", "$")
                    assert cs in cfe_strings
                    print("%s.exp: %s => %s" % (testname, gs, cs))

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
