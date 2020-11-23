#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import glob

NOT_PRESENT = "NOT_PRESENT"

def read_ds_a(filename):
    results = {}
    for line in open(filename).readlines():
        if ":" not in line:
            #print(repr(line))
            continue
        status, testname = line.split(":")
        testname = testname.strip()
        assert testname not in results
        results[testname] = status
    return results

class Tabulator(object):
    def __init__(self):
        self.transitions = {}

    def tabulate(self, testname, a_status, b_status):
        #print(testname, a_status, b_status)
        if a_status == b_status:
            t = "UNCHANGED"
        else:
            t = " -> ".join((a_status, b_status))
        if t not in self.transitions:
            self.transitions[t] = []
        self.transitions[t].append(testname)

def main():
    t = Tabulator()
    a, b = map(read_ds_a, sorted(glob.glob("diffsum-*-all")))
    for testname, a_status in a.items():
        b_status = b.pop(testname, NOT_PRESENT)
        t.tabulate(testname, a_status, b_status)
    a_status = NOT_PRESENT
    for testname, b_status in b.items():
        t.tabulate(testname, a_status, b_status)
    #print(len(t.transitions))
    for transition, tests in sorted(t.transitions.items()):
        print("%3d %s" % (len(tests), transition))

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
