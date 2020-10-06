# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import difflib
import subprocess

class Symbol(object):
    def __init__(self, type, name, value=None):
        assert len(type) == 1
        self.type = type
        self.name = name
        self.value = value

    @property
    def type_and_name(self):
        if self.name is None:
            return self.type
        else:
            return " ".join((self.type, self.name))

def _elf_symbols(filename):
    cp = subprocess.run(["nm", filename],
                        check=True,
                        stdout=subprocess.PIPE,
                        encoding="utf-8")
    for line in cp.stdout.split("\n"):
        if not line:
            continue
        try:
            if line[0].isspace():
                yield Symbol(*line.lstrip().split(None, 1))
            else:
                vtn = line.split(None, 2)
                if len(vtn) == 2:
                    vtn.append(None)
                value, type, name = vtn
                yield Symbol(type, name, value)
        except ValueError as e:
            raise ValueError("%s: %s" % (line, e))

def elf_symbols(filename):
    return list(_elf_symbols(filename))

def main():
    a, b = sys.argv[1:]
    for line in difflib.unified_diff(
            [s.type_and_name for s in _elf_symbols(a)],
            [s.type_and_name for s in _elf_symbols(b)],
            fromfile=a,
            tofile=b):
        color = None
        if sys.stdout.isatty():
            if line[0] == "-" and line[:4] != "--- ":
                color = 31
            elif line[0] == "+" and line[:4] != "+++ ":
                color = 32
            elif line[:3] == "@@ ":
                color = 36
            elif line[0] != ' ':
                color = 1
        line = line.rstrip()
        if color is not None:
            line = "\x1B[%dm%s\x1B[0m" % (color, line)
        print(line)

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
