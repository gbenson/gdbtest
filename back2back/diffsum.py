#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import difflib
import operator
import os
import re
import sys
import weakref

from functools import reduce

class Sumfile(object):
    """A parsed summary (.sum) log file output from DejaGnu.

    DejaGnu's main output is a summary log file with a name derived
    from the name of the tool being tested.  For example, after
    running `runtest --tool gdb` a summary log file will be written
    to gdb.sum.

    https://www.gnu.org/software/dejagnu/manual/Summary-log-file.html
    """

    def __init__(self, filename, testclass=None):
        self.filename = filename
        if testclass is None:
            testclass = SumfileTestcase
        self._testclass = testclass
        self._testcases = None

    @property
    def testcases(self):
        """Dictionary of all testcases recorded in this file."""
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
                try:
                    testcase._consume(line)
                except:
                    print(repr(line))
                    raise
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

    @property
    def raw_counts(self):
        result = {}
        for testcase in self.testcases.values():
            for key, count in testcase.raw_counts.items():
                result[key] = result.get(key, 0) + count
        return result

class EquivalatableMixin(object):
    """Mixin for objects that can be equivalent to other objects.

    Equivalent is less strict than equal.  Two equal objects are by
    definition equivalent, but two objects that are equivalent are
    are not necessarily equal.
    """

    def not_equivalent_to(self, other):
        raise NotImplementedError

    def is_equivalent_to(self, other):
        return not self.not_equivalent_to(other)

class SumfileTestcase(EquivalatableMixin):
    """The complete summary log output of one DejaGnu testcase.

    The DejaGnu _testsuite_ for a tool is contained within a directory
    named `testsuite` in that tool's source directory.  For example,
    GDB's testsuite is contained within "/path/to/src/gdb/testsuite".

    Each DejaGnu _testcase_ goes in a subdirectory whose name begins
    with the tool name.  For example, `gdb.base/test1.exp` is one GDB
    testcase, `gdb.base/test2.exp` is a second GDB testcase, etc.

    https://www.gnu.org/software/dejagnu/manual/Adding-a-new-testsuite.html
    """

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
        self.results = []
        self._reset_counts()

    def _reset_counts(self):
        self._counts = self._raw_counts = None

    @property
    def filename(self):
        """This testcase's filename, as recorded by DejaGnu."""
        return self.lines[0][len(self.RUNLINE_PREFIX)
                             :-len(self.RUNLINE_SUFFIX)]
    @property
    def shortname(self):
        """This testcase's filename, relative to the testsuite."""
        dirname, basename = os.path.split(self.filename)
        return os.path.join(os.path.basename(dirname), basename)

    def _consume(self, line):
        m = self.RESULTLINE_RE.match(line)
        if m is not None:
            status, shortname = m.groups()
            assert shortname == self.shortname
            message = line[len(m.group(0)):].strip()
            result = SumfileTestcaseResult(
                weakref.proxy(self),
                len(self.lines),
                status,
                message)
            if status not in ("DUPLICATE", "PATH"):
                self._reset_counts()
                self.results.append(result)
        self.lines.append(line)

    def _pop_summary(self):
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

    def _replace_result(self, orig, repl):
        self.results[self.results.index(orig)] = repl
        self._reset_counts()

    @property
    def raw_counts(self):
        """Raw status code counts: *PASS, *FAIL, UN*.
        """
        if self._raw_counts is None:
            self._raw_counts = {}
            for result in self.results:
                self._raw_counts[result.raw_status] \
                    = self._raw_counts.get(result.raw_status, 0) + 1
        return self._raw_counts

    @property
    def counts(self):
        """Cooked status code counts: PASS, FAIL, SKIP.
        """
        if self._counts is None:
            self._counts = {}
            for result in self.results:
                self._counts[result.status] \
                    = self._counts.get(result.status, 0) + 1
        return self._counts

    # Comparisons.
    def not_equivalent_to(self, other):
        if other is None:
            return True
        if len(self.results) != len(other.results):
            return True
        for a, b in zip(self.results, other.results):
            if a.not_equivalent_to(b):
                return True
        return False

    # Queries.
    @property
    def has_results(self):
        return not (not self.results)

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
    def raw_build_errors(self):
        """This test's build errors, exactly as found."""
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

    NORMALIZE_FILENAME_RE = re.compile(
        r"%(sep)s[^%(sep)s]+%(sep)s%(pardir)s%(sep)s"
        % {"sep": os.sep,
           "pardir": os.pardir.replace(".", r"\.")})

    @property
    def build_errors(self):
        """This test's build errors, with filenames normalized."""
        for line in self.raw_build_errors:
            while True:
                line, numsubs = self.NORMALIZE_FILENAME_RE.subn(os.sep, line)
                if numsubs < 1:
                    break
            yield line

    @property
    def terse_build_errors(self):
        """Important lines (ideally one) from this test's build errors."""
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

class SumfileTestcaseResult(EquivalatableMixin):
    """One single result (one status) from one DejaGnu testcase.

    Each SumfileTestcaseResult is the result of a call to one of the
    commands pass, fail, unresolved, unsupported, or untested.
    The raw status can be *PASS, *FAIL, or UN*.
    The cooked status will be one of PASS, FAIL or SKIP.
    """
    def __init__(self, testcase, rel_lineno, raw_status, message):
        self.testcase = testcase
        self.rel_lineno = rel_lineno
        self.raw_status = raw_status
        self.message = message

    @property
    def testname(self):
        return self.testcase.shortname

    @property
    def status(self):
        result = self.raw_status
        if result.startswith("UN"):
            result = "SKIP"
        else:
            result = result[-4:]
        if result not in ("PASS", "FAIL", "SKIP"):
            raise ValueError(self.raw_status)
        return result

    @property
    def as_tuple(self):
        return self.raw_status, self.testname, self.message

    def __str__(self):
        return ": ".join(self.as_tuple)

    def __eq__(self, other):
        return not (self != other)

    def __ne__(self, other):
        return other is None or self.as_tuple != other.as_tuple

    def not_equivalent_to(self, other):
        if other is None:
            return True
        if self == other:
            return False
        if self.is_failure_of(other):
            passer, failer = other, self
        elif other.is_failure_of(self):
            passer, failer = self, other
        else:
            return True
        if self.is_racy_failure(failer, passer):
            # XXX: hack: this mutates the failer's testcase.
            failer.testcase._replace_result(failer, passer)
            return False
        return True

    def is_failure_of(self, other):
        """Returns True if self is the FAILure to other's PASS."""
        return not self.not_failure_of(other)

    def not_failure_of(self, other):
        """Returns False if self is the FAILure to other's PASS."""
        return (other is None
                or self.testname != other.testname
                or self.status != "FAIL"
                or other.status != "PASS"
                or not self.message.startswith(other.message))

    RACYFAIL_REGEXPS_FILENAME = "racy.tests"
    RACYFAIL_REGEXPS = None

    @classmethod
    def _load_racy_failure_regexps(cls):
        if cls.RACYFAIL_REGEXPS is not None:
            return
        cls.RACYFAIL_REGEXPS = []
        topdir = os.path.dirname(os.path.realpath(__file__))
        filename = os.path.join(topdir, cls.RACYFAIL_REGEXPS_FILENAME)
        for line in open(filename).readlines():
            line = line.rstrip()
            if line:
                cls.RACYFAIL_REGEXPS.append(re.compile(line))

    @classmethod
    def is_known_racy_failure(cls, failer, passer):
        cls._load_racy_failure_regexps()
        failer_str = str(failer)
        for expr in cls.RACYFAIL_REGEXPS:
            if expr.search(failer_str) is not None:
                return True

    @classmethod
    def is_racy_failure(cls, failer, passer):
        assert failer.is_failure_of(passer)
        assert not passer.is_failure_of(failer)
        if cls.is_known_racy_failure(failer, passer):
            return True
        if (failer.raw_status in ("KFAIL", "XFAIL")
              and failer.testname.startswith("gdb.threads/")):
            print("warning: %s: ignored (racy)" % failer, file=sys.stderr)
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
        if self.a is None:
            return self.b.shortname
        result = self.a.shortname
        assert self.b is None or self.b.shortname == result
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
            return self.IDENTICAL
        return self.EQUIVALENT

    def _categorize_nonequivalent(self):
        # Less passes is unambiguously a regression.
        if self.b.num_passed < self.a.num_passed:
            return self.REGRESSED

        # Less skips without less passes is an improvement
        # regardless of whether we have more failures now.
        if self.b.num_skipped < self.a.num_skipped:
            return self.IMPROVED

        # More failures without less skips is a regression.
        if self.b.num_failed > self.a.num_failed:
            return self.REGRESSED

        # More skips without less passes is likely intentional.
        if self.b.num_skipped > self.a.num_skipped:
            return self.PART_SKIPPED

        # More passes without less skips or more failures is an
        # improvement.
        if self.b.num_passed > self.a.num_passed:
            return self.IMPROVED

        assert self.b.counts == self.a.counts
        return self.EQUIVALENT

    @property
    def delta(self):
        return difflib.unified_diff(self.a.lines,
                                    self.b.lines,
                                    fromfile=self.a.filename,
                                    tofile=self.b.filename)

    @property
    def prettydelta(self):
        for line in self.delta:
            color = None
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
            yield line

class UncookedCountsReport(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b

    @property
    def pairs(self):
        result = {}
        for key, value in self.a.raw_counts.items():
            assert key not in result
            result[key] = [value, 0]
        for key, value in self.b.raw_counts.items():
            if key not in result:
                result[key] = [0, 0]
            assert result[key][1] == 0
            result[key][1] = value
        return result

    def __str__(self):
        result = []
        for key, values in self.pairs.items():
            result.append("%12s: %5d -> %d"
                          % ( (key,) + tuple(values) ))
        return "\n".join(result)

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
            generate_lines = (
                self.verbosity > int(cat == SumfileTestcasePair.IMPROVED)
                and self._diff_lines or self._list_lines)
            for line in generate_lines(cat):
                yield line

    def _list_lines(self, cat):
        yield "%s:" % cat
        for pair in self.pairs_by_category[cat]:
            yield "  " + pair.shortname

    def _diff_lines(self, cat):
        yield "\x1B[33m== \x1B[1m%s:\x1B[0m" % cat
        for pair in self.pairs_by_category[cat]:
            for line in pair.prettydelta:
                yield line

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
        testcases_by_msg = {}
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
                    for tmp, value in ((testcases_by_msg, pair.shortname),
                                        (filenames_by_msg, prefix)):
                        if msg not in tmp:
                            tmp[msg] = {}
                        tmp[msg][value] = True

        is_first_line = True
        for msg, filenames in sorted(filenames_by_msg.items()):
            if msg == "unsupported directive '.stabs'":
                continue  # I don't care about stabs.
            if is_first_line:
                is_first_line = False
            else:
                yield ""
            yield msg
            for filename in sorted(filenames):
                yield "  " + filename
            for index, testcase in enumerate(sorted(testcases_by_msg[msg])):
                yield ("\x1B[33m%8s %s\x1B[0m"
                       % (index == 0 and "affects:" or " ",
                          testcase))

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
        "--uncooked", action="store_true",
        help="report raw counts only rather than the standard report")
    parser.add_argument(
        "--report-errors", action="store_true",
        help="report build errors rather than the standard report")
    args = parser.parse_args()
    Reporter.verbosity = args.verbose
    a, b = map(Sumfile, args.filenames)

    if args.uncooked:
        print(UncookedCountsReport(a, b))
        return

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
