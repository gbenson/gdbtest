# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import glob
import nmdiff
import os
import subprocess

def is_elf(filename):
    return open(filename, "rb").read(4) == b"\177ELF"

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
                    gcc_symbols = nmdiff.elf_symbols(gcc_filename)
                    cfe_symbols = nmdiff.elf_symbols(cfe_filename)
                except subprocess.CalledProcessError:
                    continue
                in_gcc = dict((sym.name, sym) for sym in gcc_symbols)
                in_cfe = dict((sym.name, sym) for sym in cfe_symbols)
                for sym_name, sym in sorted(in_gcc.items()):
                    if sym_name in in_cfe:
                        continue
                    if sym.value is None:
                        continue
                    if "." in sym_name:
                        continue # XXX internal stuff?
                    if sym.type != sym.type.lower():
                        continue
                    #if (sym_name.startswith("_Z")
                    #    or sym_name.find("__Z") >= 0):
                    #    continue # XXX C++?
                    #print("%s: %s: %s" % (cfe_filename,
                    #                      sym.type,
                    #                      sym_name))
                    print(testname)
                    break
                else:
                    continue
                break

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
