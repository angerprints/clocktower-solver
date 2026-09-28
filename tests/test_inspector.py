"""The seat inspector's checkboxes.

These are wired in one place and read back in another, and nothing about
the solver notices if only half of that happened: the box ticks, looks
right, and forgets the moment another seat is chosen.

That is exactly what shipped. Three checkboxes — "voted today",
"nominated today" and "their information might be wrong" — were added to
the panel and never bound to anything, because the edit that was meant to
attach the handlers anchored on text that did not exist and quietly did
nothing. The suspect box had been dead for a session before anybody tried
it.

So this drives the page: clicks a seat, ticks the boxes, clicks away and
back, and checks what survived — and what the ledger drew.

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


@unittest.skipUnless(NODE, "Node is not installed")
class TheSeatInspector(SolverTest):

    @classmethod
    def setUpClass(cls):
        import tools.build_site as build
        build.build()
        got = subprocess.run(
            [NODE, str(ROOT / "tests" / "harness" / "inspector_ticks.mjs")],
            capture_output=True, text=True, timeout=300)
        if got.returncode:
            raise AssertionError(f"the inspector failed to drive:\n"
                                 f"{got.stderr}")
        cls.got = json.loads(got.stdout.strip().splitlines()[-1])

    def test_every_checkbox_is_attached_to_something(self):
        """The whole bug in one line. A checkbox with no handler looks
        exactly like a working one until you click away."""
        self.assertEqual(sorted(self.got["wired"]),
                         ["f-nominated", "f-suspect", "f-voted"])

    def test_ticking_one_keeps_it_on_the_seat(self):
        self.assertEqual(self.got["kept"],
                         [{"seat": 3, "voted": [1], "nominated": [1]}])

    def test_it_belongs_to_that_seat_and_not_the_panel(self):
        """Clicking another seat shows that seat's answer, not the last
        one typed."""
        self.assertFalse(self.got["awayVoted"])

    def test_and_it_is_still_there_when_you_come_back(self):
        self.assertTrue(self.got["backVoted"])
        self.assertTrue(self.got["backNominated"])

    def test_the_ledger_gathers_the_day(self):
        """Ticked one seat at a time; the day is when it matters
        together."""
        self.assertEqual(self.got["ledger"], "Seat 3 nominated; Seat 3 voted")


if __name__ == "__main__":
    unittest.main()
