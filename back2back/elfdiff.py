#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

from elftools.elf import elffile

class ELFFile(elffile.ELFFile):
    def compare(self, other):
        if list(self.section_names) == list(other.section_names):
            print("section names are the same")

    @property
    def section_names(self):
        for section in self.iter_sections():
            yield section.name

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
