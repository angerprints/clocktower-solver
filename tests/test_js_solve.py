"""The whole JavaScript solver, answered against the corpus.

This is the check the port has been building towards. Every comparison
before it was of a part — the bag, one reading, one rule. Here the
ninety-two boards Python answered in `tests/fixtures/conformance.json`
are answered again by the JavaScript solver end to end, and the
percentages have to match to four figures.

The board is read from exactly the shape the page posts, so this is also
the first time the JavaScript side deals with a payload rather than with
objects handed to it.

Four of the boards are refused by Python for reasons that are *input
validation* rather than solving — two seats executed on one day, a night
marked quiet with somebody dying in it. That check lives in the server
and has not been ported, so those are counted separately rather than
quietly passed over.

Skipped when Node is not installed.
"""

import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
CORPUS = ROOT / "tests" / "fixtures" / "conformance.json"


@unittest.skipUnless(NODE, "Node is not installed")
class TheWholeSolverAgrees(SolverTest):

    @classmethod
    def setUpClass(cls):
        got = subprocess.run(
            [NODE, str(ROOT / "js" / "dump_solve.mjs"), str(CORPUS)],
            capture_output=True, text=True, timeout=1200)
        if got.returncode:
            raise AssertionError(f"js/dump_solve.mjs failed:\n{got.stderr}")
        cls.js = json.loads(got.stdout)
        cls.corpus = json.loads(CORPUS.read_text())
        cls.tol = 10 ** -cls.corpus["places"] * 20
        # The boards Python refused for input reasons rather than solving.
        cls.validation = {c["name"] for c in cls.corpus["cases"]
                          if "error" in c["expect"]}

    def solvable(self):
        return [c for c in self.corpus["cases"]
                if c["name"] not in self.validation]

    def test_every_board_was_answered(self):
        self.assertEqual(sorted(self.js),
                         sorted(c["name"] for c in self.corpus["cases"]))

    def test_the_same_worlds_survive(self):
        for case in self.solvable():
            with self.subTest(board=case["name"]):
                self.assertEqual(self.js[case["name"]]["valid"],
                                 case["expect"]["valid"])

    def test_nothing_was_sampled(self):
        """A sampled answer depends on a random walk and could never be
        reproduced across languages. The corpus has none, and this holds
        the JavaScript side to that too."""
        for case in self.solvable():
            with self.subTest(board=case["name"]):
                self.assertFalse(self.js[case["name"]]["sampled"])

    def test_every_seat_reads_the_same(self):
        for case in self.solvable():
            mine = self.js[case["name"]]["rows"]
            theirs = case["expect"]["rows"]
            self.assertEqual(len(mine), len(theirs))
            for i, (got, want) in enumerate(zip(mine, theirs)):
                for key, value in want.items():
                    with self.subTest(board=case["name"], seat=i + 1,
                                      figure=key):
                        self.assertAlmostEqual(got[key], value,
                                               delta=self.tol)

    def test_what_killed_each_body_agrees(self):
        for case in self.solvable():
            want = case["expect"].get("blame")
            if not want:
                continue
            with self.subTest(board=case["name"]):
                mine = self.js[case["name"]].get("blame", {})
                self.assertEqual(set(mine), set(want))
                for night, seats in want.items():
                    self.assertEqual(set(mine[night]), set(seats))
                    for seat, causes in seats.items():
                        self.assertEqual(set(mine[night][seat]), set(causes))
                        for cause, share in causes.items():
                            self.assertAlmostEqual(mine[night][seat][cause],
                                                   share, delta=self.tol)

    def test_the_boards_are_worth_comparing(self):
        """Percentages that are all nought and a hundred would match
        however wrong the port was."""
        interesting = 0
        for case in self.solvable():
            for row in case["expect"]["rows"]:
                if 1 < row["evil_pct"] < 99:
                    interesting += 1
        self.assertGreater(interesting, 200,
                           "too few in-between readings to prove anything")

    def test_a_refused_board_is_refused_the_same_way(self):
        """There used to be a gap here: input checking lived in the
        server and the JavaScript answered boards Python would not.

        It closed by accident, and the accident is the lesson. This
        comparison had its *own copy* of the board reader — so when the
        page's reader gained validation, nothing here noticed, and when
        the board learned to record votes, this quietly did not. Both
        now go through the same entry the page calls, and the refusals
        match word for word.
        """
        self.assertTrue(self.validation, "no refused boards to compare")
        for case in self.corpus["cases"]:
            if "error" not in case["expect"]:
                continue
            with self.subTest(board=case["name"]):
                self.assertEqual(self.js[case["name"]].get("error"),
                                 case["expect"]["error"])


if __name__ == "__main__":
    unittest.main()
