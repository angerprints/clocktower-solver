"""The test runner itself.

A pattern matching no file used to report "Ran 0 tests — all good", and
that is not a pass: it is a typo being answered with a green light. It
happened for real — `run_tests.py waking`, when the file is `test_wakes`
— and for a whole session it hid the very tests being looked for, while
every run in between looked fine.

Cheap to prevent, and the sort of thing that only gets written down after
it has cost something.
"""

import pathlib
import subprocess
import sys
import unittest

from helpers import SolverTest                    # sets up the import path

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(*args):
    return subprocess.run([sys.executable, str(ROOT / "run_tests.py"), *args],
                          capture_output=True, text=True, timeout=300)


class APatternMatchingNothingIsAnError(SolverTest):

    def test_it_fails_rather_than_passing(self):
        got = run("thereisnosuchfile")
        self.assertEqual(got.returncode, 2)
        self.assertIn("nothing matches", got.stdout)

    def test_it_lists_the_files_that_do_exist(self):
        got = run("thereisnosuchfile")
        for name in ("wakes", "worlds", "claims"):
            with self.subTest(file=name):
                self.assertIn(name, got.stdout)

    def test_and_suggests_the_one_that_was_meant(self):
        """The case that prompted this. Compared by spelling, not by
        prefix — the first attempt matched on the first four letters,
        which is exactly wrong here: "waki" is not a substring of
        "wakes"."""
        got = run("waking")
        self.assertIn("did you mean", got.stdout)
        self.assertIn("wakes", got.stdout.split("did you mean")[1])

    def test_a_keyword_matching_nothing_fails_too(self):
        got = run("wakes", "-k", "zzzznosuchtest")
        self.assertEqual(got.returncode, 2)
        self.assertIn("no test matches", got.stdout)


class TheOrdinaryWaysStillWork(SolverTest):

    def test_a_whole_file_by_name(self):
        got = run("wakes")
        self.assertEqual(got.returncode, 0)
        self.assertIn("tests in", got.stdout)

    def test_a_prefix_matching_several(self):
        got = run("js_worlds")
        self.assertEqual(got.returncode, 0)

    def test_and_a_keyword_that_matches(self):
        got = run("wakes", "-k", "wake")
        self.assertEqual(got.returncode, 0)


if __name__ == "__main__":
    unittest.main()
