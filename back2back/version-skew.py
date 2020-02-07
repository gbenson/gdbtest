#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

class RPM(object):
    def __init__(self, rpm_nvra):
        #print("\x1B[33m%s\x1B[0m" % rpm_nvra)
        tmp = rpm_nvra.split(".")
        if len(tmp) > 1:
            self.arch = tmp.pop()
        else:
            self.arch = None
        tmp = ".".join(tmp).split("-")
        self.release = tmp.pop()
        self.version = tmp.pop()
        self.name = "-".join(tmp)
        assert str(self) == rpm_nvra

    @property
    def nvra(self):
        return self.name, self.version, self.release, self.arch

    def __str__(self):
        result = "-".join(self.nvra[:-1])
        if self.arch is not None:
            result = ".".join((result, self.arch))
        return result

def main(debug=False):
    packages = {}
    for line in open("rpm-qa.container-6ead8216858b").readlines():
        pkg = RPM(line.rstrip())
        assert pkg.name not in packages
        packages[pkg.name] = pkg

    for line in open("rpm-qa.vm-202002071318").readlines():
        pkg = RPM(line.rstrip())
        old = packages.pop(pkg.name, None)
        if old is None:
            if debug:
                print("V only:", pkg)
            continue
        elif str(pkg) == str(old):
            if debug:
                print("  Both:", pkg)
            continue
        else:
            print("\x1B[1;31mSKEW:\x1B[0m", old, pkg)

    if debug:
        for name, pkg in sorted(packages.items()):
            print("C only:", pkg)

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
