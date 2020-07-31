#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

from elftools.elf import elffile, sections
from itertools import zip_longest

class ELFFile(elffile.ELFFile):
    def compare(self, other):
        for ssec, osec in zip_longest(self.iter_sections(),
                                      other.iter_sections()):
            ssec.compare(osec)

def _compare_section(self, other):
    assert self.name == other.name
    assert type(self) == type(other)
    self_data = self.data()
    assert len(self_data) == self.data_size
    other_data = other.data()
    assert len(other_data) == other.data_size
    if self_data == other_data:
        print("\x1B[33m %s %s sh_size = %d\x1B[0m"
              % (self, repr(self.name), self["sh_size"]))
        return

    print("\x1B[31m-%s %s sh_size = %d\x1B[0m"
          % (self, repr(self.name), self["sh_size"]))
    print("\x1B[32m+%s %s sh_size = %d\x1B[0m"
          % (other, repr(other.name), other["sh_size"]))

sections.Section.compare = _compare_section

def main():
    assert len(sys.argv) == 3
    with open(sys.argv[1], "rb") as fa:
        with open(sys.argv[2], "rb") as fb:
            ELFFile(fa).compare(ELFFile(fb))

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
