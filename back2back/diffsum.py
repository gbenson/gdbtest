#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import operator
import os
import re
import sys

from functools import reduce
from itertools import zip_longest

class Sumfile(object):
    def __init__(self, filename, testclass=None):
        self.filename = filename
        if testclass is None:
            testclass = SumfileTestcase
        self._testclass = testclass
        self._testcases = None

    @property
    def testcases(self):
        if self._testcases is None:
            self._read()
        return self._testcases

    def _read(self):
        assert self._testcases is None
        self._testcases = {}
        self.preamble = []
        testcase = None
        for line in open(self.filename).readlines():
            if self._testclass.is_runline(line):
                testcase = self._testclass(line)
                key = testcase.shortname
                assert key not in self._testcases
                self._testcases[key] = testcase
            elif testcase is not None:
                testcase._consume(line)
            else:
                self.preamble.append(line)
        if testcase is not None:
            self.summary = testcase._pop_summary()

    @property
    def keys(self):
        return self.testcases.keys

    _sentinel = object()

    def get(self, key, default=_sentinel):
        result = self.testcases.get(key, default)
        if result is self._sentinel:
            raise KeyError(key)
        return result

    def compare(self, other):
        return SumfileMatcher(self, other)

class SumfileTestcase(object):
    # Lines with this start and end separate the testcases in the file.
    # We can use this to process error messages with non-parallel runs.
    RUNLINE_PREFIX = "Running "
    RUNLINE_SUFFIX = " ...\n"

    # Lines matching this regular expression are the actual results.
    RESULTLINE_RE = re.compile("^([A-Z]+): ([^/]+/[^/]+\.exp): ")

    # The final testcase will have consumed the sumfile's summary.
    # A line with this start and end should separate it from the
    # testcase's output.
    SUMMARY_PREFIX = "\t\t=== "
    SUMMARY_SUFFIX = " Summary ===\n"

    @classmethod
    def is_runline(cls, line):
        return (line.startswith(cls.RUNLINE_PREFIX)
                and line.endswith(cls.RUNLINE_SUFFIX))

    def __init__(self, runline):
        assert self.is_runline(runline)
        self.lines = [runline]
        self._raw_counts = {}  # keys = *PASS, *FAIL, UN*
        self._counts = None    # keys = PASS, FAIL, SKIP only
        self.results = {}
        self._resultlines = {}

    @property
    def filename(self):
        return self.lines[0][len(self.RUNLINE_PREFIX)
                             :-len(self.RUNLINE_SUFFIX)]
    @property
    def shortname(self):
        dirname, basename = os.path.split(self.filename)
        return os.path.join(os.path.basename(dirname), basename)

    def _dedup(self, message):
        key, count = message, 0
        while True:
            if key not in self.results:
                return key
            count += 1
            key = "%s __diffsum_dedup_%08d" % (message, count)

    def _consume(self, line):
        assert self._counts is None
        m = self.RESULTLINE_RE.match(line)
        if m is not None:
            status, shortname = m.groups()
            assert shortname == self.shortname
            message = self._dedup(line[len(m.group(0)):].strip())
            assert message not in self.results
            self._raw_counts[status] = self._raw_counts.get(status, 0) + 1
            self.results[message] = status
            self._resultlines[message] = len(self.lines)
        self.lines.append(line)

    def _pop_summary(self):
        assert self._counts is None
        assert self.lines
        for index in range(-1, -1-len(self.lines), -1):
            line = self.lines[index]
            if (line.startswith(self.SUMMARY_PREFIX)
                  and line.endswith(self.SUMMARY_SUFFIX)):
                break
        else:
            assert False
        index -= 1 # Pop the leading blank line too.
        assert -index <= len(self.lines)
        result = self.lines[index:len(self.lines)]
        self.lines[index:len(self.lines)] = []
        return result

    @property
    def counts(self):
        if self._counts is None:
            self._counts = {}
            for raw_status, count in self._raw_counts.items():
                if raw_status.startswith("UN"):
                    status = "SKIP"
                else:
                    status = raw_status[-4:]
                    assert status in ("PASS", "FAIL")
                self._counts[status] = self._counts.get(status, 0) + count
        return self._counts

    @property
    def messages(self):
        tmp = ((line, msg) for msg, line in self._resultlines.items())
        return (msg for line, msg in sorted(tmp))

    # Canonical comparisons.
    def not_equivalent_to(self, other):
        return other is None or self._raw_counts != other._raw_counts

    # Derived comparisons.
    def is_equivalent_to(self, other):
        return not self.not_equivalent_to(other)

    # Queries.
    @property
    def has_results(self):
        return not (not self._raw_counts)

    @property
    def all_passed(self):
        return self._all_one_status("PASS")

    @property
    def all_failed(self):
        return self._all_one_status("FAIL")

    @property
    def all_skipped(self):
        return self._all_one_status("SKIP")

    def _all_one_status(self, status):
        return list(self.counts.keys()) == [status]

    @property
    def num_passed(self):
        return self._count("PASS")

    @property
    def num_failed(self):
        return self._count("FAIL")

    @property
    def num_skipped(self):
        return self._count("SKIP")

    def _count(self, status):
        return self.counts.get(status, 0)

    # Compiler failure message extraction.
    BUILDERROR_STARTLINE_PREFIX = "gdb compile failed,"

    @property
    def build_errors(self):
        hunting = True
        for line in self.lines:
            if hunting:
                start = line.find(self.BUILDERROR_STARTLINE_PREFIX)
                if start < 0:
                    continue
                hunting = False
                line = line[start:]
            elif self.RESULTLINE_RE.match(line) is not None:
                break
            if line.startswith(self.BUILDERROR_STARTLINE_PREFIX):
                line = line[len(self.BUILDERROR_STARTLINE_PREFIX):].lstrip()
            yield line

    @property
    def terse_build_errors(self):
        lines = list(self.build_errors)
        if not lines:
            return
        success = False

        for line in lines:
            if self.is_terse_build_error(line):
                yield line
                success = True
        if success:
            return

        print("\x1B[1;31m%s: error: can't tersify errors:\x1B[0m"
              % self.shortname)
        for lineno, line in enumerate(lines):
            print("%d:" % (lineno + 1), line.rstrip())
        raise SystemExit

    WARNING_ERROR_RE = re.compile(r":\s*(?:warning|(?:fatal\s+)?error):\s*")
    INFILE_LOCATION_RE = re.compile(r":\d+(?::\d+)?$")
    _compiler_prefixes = {"<unknown>:0": True}

    @classmethod
    def is_infile_location(cls, text):
        return cls.INFILE_LOCATION_RE.search(text) is not None

    @classmethod
    def is_terse_build_error(cls, line):
        parts = cls.WARNING_ERROR_RE.split(line)
        if len(parts) == 1:
            return False
        prefix, message = parts
        if prefix in cls._compiler_prefixes:
            # We've seen this prefix before, below.
            return True
        if message.find(" [-W") >= 0:
            # This message is twice verified. If the prefix isn't
            # a location in a file, then assume it's the name of
            # a tool and add it to our list.
            if not cls.is_infile_location(prefix):
                cls._compiler_prefixes[prefix] = True
            return True
        if cls.is_infile_location(prefix):
            # It's a location in a file, it's *probably* ok.
            return True
        return False

class SumfileMatcher(object):
    def __init__(self, sumfile_a, sumfile_b):
        self._sfa = sumfile_a
        self._sfb = sumfile_b

    def __getitem__(self, key):
        a = self._sfa.get(key, None)
        b = self._sfb.get(key, None)
        if a is None and b is None:
            raise KeyError(key)
        return SumfileTestcasePair(self, a, b)

    def keys(self):
        result = set(self._sfa.keys())
        result.update(self._sfb.keys())
        return sorted(result)

    def values(self):
        return (self[key] for key in self.keys())

    def __iter__(self):
        return self.values()

class SumfileTestcasePair(object):
    class Category(object):
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def __str__(self):
            return self.name

    @classmethod
    def _cls_init(cls):
        for pri, cat in enumerate((
            ("IDENTICAL",
             """Identical status+message lines were emitted,
             in the same order.  These pairs should not
             require investigation."""),

            ("SKIPPED_EQUIVALENT",
             """Neither run reported passes or fails, but the
             reported status lines were not identical."""),

            ("TEST_APPEARED",
             """The test ran in the second run, but it was entirely
             absent in the first.  This should only occur when the
             .exp file was added between runs."""),

            ("PART_SKIPPED",
             """Some of the test ran without regressions, but it was
             partly skipped in the second run."""),

            ("TEST_SKIPPED",
             """The test ran in the first run, but it was entirely
             skipped in the second.  This usually represents the
             test reporting the lack of a required feature, or the
             test detecting that its testcases failed to compile."""),

            ("TEST_BOMBED",
             """The test emitted statuses in the first run, but not
             in the second.  This usually represents the test failing
             in some unhandled way."""),

            ("TEST_VANISHED",
             """The test ran in the first run, but it was entirely
              absent in the second.  This should only occur when the
             .exp file was removed between runs."""),

            ("EQUIVALENT",
             """Both runs emitted the same numbers of each status.
             These pairs could be trivial differences, or they could
             represent real regressions."""),

            ("REGRESSED",
             """The second run's result was worse than the first run's
             result in some way."""),

            ("IMPROVED",
             """The second run's result was better than the first run's
             result in some way."""),

                )):
            name, description = cat
            description = " ".join(description.split())
            setattr(cls, name, cls.Category(priority=pri,
                                            name=name,
                                            description=description))

    def __init__(self, matcher, a, b):
        if not hasattr(self, "IMPROVED"):
            self._cls_init()
        self._matcher = matcher
        self.a = a
        self.b = b
        self._category = None

    @property
    def shortname(self):
        result = self.a.shortname
        assert self.b.shortname == result
        return result

    @property
    def category(self):
        if self._category is None:
            self._category = self._categorize()
        return self._category

    def _categorize(self):
        if self.a is None:
            assert self.b is not None
            return self.TEST_APPEARED
        if self.b is None:
            return self.TEST_VANISHED
        if self.a.is_equivalent_to(self.b):
            return self._categorize_equivalent()
        if not self.b.has_results:
            if self.a.all_skipped:
                return self.SKIPPED_EQUIVALENT
            return self.TEST_BOMBED
        if self.b.all_skipped:
            if self.a.all_skipped:
                return self.SKIPPED_EQUIVALENT
            return self.TEST_SKIPPED
        return self._categorize_nonequivalent()

    def _categorize_equivalent(self):
        if self.a.results == self.b.results:
            sentinel = object()
            for a, b in zip_longest(self.a.messages,
                                    self.b.messages,
                                    fillvalue=sentinel):
                if a != b:
                    break
            else:
                return self.IDENTICAL
        return self.EQUIVALENT

    def _categorize_nonequivalent(self):
        if (self.b.num_passed < self.a.num_passed
              or self.b.num_failed > self.a.num_failed):
            return self.REGRESSED

        if self.b.num_skipped > self.a.num_skipped:
            return self.PART_SKIPPED

        if (self.b.num_passed > self.a.num_passed
              or self.b.num_failed < self.a.num_failed
              or self.b.num_skipped < self.a.num_skipped):
            return self.IMPROVED

        assert self.b.counts == self.a.counts
        return self.EQUIVALENT

class Reporter(object):
    def __init__(self, pairs_by_category):
        self.pairs_by_category = pairs_by_category

    def __str__(self):
        return "\n".join(self.report_lines)

    @property
    def categories(self):
        for pri, cat in sorted(((cat.priority, cat)
                                for cat in self.pairs_by_category.keys()),
                               reverse=True):
            yield cat

class CountsReport(Reporter):
    @property
    def report_lines(self):
        total = reduce(operator.add,
                       (len(pairs)
                        for pairs in self.pairs_by_category.values()))
        for cat in self.categories:
            count = len(self.pairs_by_category[cat])
            yield "%20s %4d %5.1f%%" % (cat, count, 100*count/total)
        yield "  " + "=" * 32
        yield "%20s %4d %5.1f%%" % ("TOTAL", total, 100)

class FilesByCategoryReport(Reporter):
    @property
    def report_lines(self):
        is_first_line = True
        for cat in self.categories:
            if cat == SumfileTestcasePair.IDENTICAL:
                continue
            if is_first_line:
                is_first_line = False
            else:
                yield ""
            yield "%s:" % cat
            for pair in self.pairs_by_category[cat]:
                yield "  " + pair.shortname

class BuildErrorsReport(Reporter):
    @property
    def report_lines(self):
        for cat in self.categories:
            if cat == SumfileTestcasePair.IDENTICAL:
                continue
            for pair in self.pairs_by_category[cat]:
                is_first_line = True
                for line in pair.b.build_errors:
                    if is_first_line:
                        yield "\x1B[33m%s: %s: %s\x1B[0m" % (
                            pair.shortname,
                            cat,
                            pair.b.BUILDERROR_STARTLINE_PREFIX)
                        is_first_line = False
                    yield line.rstrip()

class GroupedBuildErrorsReport(Reporter):
    @property
    def report_lines(self):
        filenames_by_msg = {}
        for cat in self.categories:
            if cat == SumfileTestcasePair.IDENTICAL:
                continue
            for pair in self.pairs_by_category[cat]:
                for line in pair.b.terse_build_errors:
                    prefix, msg = pair.b.WARNING_ERROR_RE.split(line)
                    if prefix in pair.b._compiler_prefixes:
                        continue
                    msg = msg.rstrip()
                    if msg not in filenames_by_msg:
                        filenames_by_msg[msg] = {}
                    filenames_by_msg[msg][prefix] = True

        is_first_line = True
        for msg, filenames in sorted(filenames_by_msg.items()):
            if is_first_line:
                is_first_line = False
            else:
                yield ""
            yield msg
            for filename in sorted(filenames):
                yield "  " + filename

def main():
    parser = argparse.ArgumentParser(
        usage="diffsum [OPTION]... FILE1 FILE2",
        description="Compare two DejaGnu summary log (.sum) output files.",
        epilog="report bugs to: gbenson@redhat.com")
    parser.add_argument(
        "filenames", metavar="FILE1, FILE2", nargs=2,
        help="the two .sum files to compare")
    parser.add_argument(
        "--verbose", "-v", action="count", default=0,
        help="be more verbose")
    parser.add_argument(
        "--report-errors", action="store_true",
        help="report build errors rather than the standard report")
    args = parser.parse_args()
    a, b = map(Sumfile, args.filenames)

    # Group the testresult pairs by category.
    pairs_by_category = {}
    for pair in a.compare(b):
        cat = pair.category
        if cat not in pairs_by_category:
            pairs_by_category[cat] = []
        pairs_by_category[cat].append(pair)

    # Print some reports.
    if args.report_errors:
        if args.verbose > 0:
            print(BuildErrorsReport(pairs_by_category))
        else:
            print(GroupedBuildErrorsReport(pairs_by_category))
        return
    print()
    print(CountsReport(pairs_by_category))
    print()
    print(FilesByCategoryReport(pairs_by_category))
    print()

if __name__ == "__main__":
    if "sys" not in locals():
        import sys
    assert sys.version_info >= (3,)
    main()
