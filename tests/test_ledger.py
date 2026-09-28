"""The ledger reading as the game happened.

Each night's readings are framed by what actually occurred: the night's
deaths above them, and the day that followed beneath. Neither line is new
information — it is all on the seats already — but it is on the seats one
at a time, and a reading about night three means something different once
you can see who was not there to hear it.

The page is asked what it draws rather than trusted to draw it. The
harness loads the built page with a stub DOM, hands it a saved game with
something happening on most nights, and reports the framing lines it
produced.

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

# The game the harness loads: Cara dies on night 2 and comes back on
# night 4, Eve is executed on day 2, Gita dies on night 3, and days 1
# and 3 end with nobody executed.
EXPECTED = [
    ("day-foot", "day 1: nobody executed"),
    ("night-open", "Cara was found dead"),
    ("day-foot settled", "Day 2: Eve was executed"),
    ("night-open", "Gita was found dead"),
    ("day-foot", "day 3: nobody executed"),
    ("night-open", "Cara is back"),
    ("day-foot", "day 4: nobody executed"),
    ("day-foot", "day 5: nobody executed"),
]


@unittest.skipUnless(NODE, "Node is not installed")
class TheLedgerFramesEachDay(SolverTest):

    @classmethod
    def setUpClass(cls):
        import tools.build_site as build
        build.build()
        got = subprocess.run(
            [NODE, str(ROOT / "tests" / "harness" / "ledger_lines.mjs")],
            capture_output=True, text=True, timeout=300)
        if got.returncode:
            raise AssertionError(f"the ledger failed to draw:\n{got.stderr}")
        cls.lines = json.loads(got.stdout.strip().splitlines()[-1])

    def test_it_draws_what_the_game_did(self):
        self.assertEqual([(l["kind"], l["text"]) for l in self.lines],
                         EXPECTED)

    def test_a_night_death_is_named_above_that_night(self):
        opened = [l["text"] for l in self.lines if l["kind"] == "night-open"]
        self.assertIn("Cara was found dead", opened)
        self.assertIn("Gita was found dead", opened)

    def test_somebody_coming_back_is_named_too(self):
        opened = [l["text"] for l in self.lines if l["kind"] == "night-open"]
        self.assertIn("Cara is back", opened)

    def test_an_execution_closes_its_day(self):
        settled = [l for l in self.lines if l["kind"].endswith("settled")]
        self.assertEqual(len(settled), 1)
        self.assertIn("Eve was executed", settled[0]["text"])

    def test_a_day_nobody_was_executed_says_so(self):
        quiet = [l for l in self.lines
                 if l["kind"] == "day-foot" and "nobody" in l["text"]]
        self.assertGreaterEqual(len(quiet), 2)

    def test_the_execution_moved_the_game_on(self):
        """Day 5 only exists because day 3 ended and night 4 raised
        somebody — which is the counter working."""
        days = [l["text"] for l in self.lines if l["kind"] == "day-foot"]
        self.assertTrue(any("day 5" in d for d in days))

    def test_a_night_with_nothing_in_it_draws_no_line(self):
        """Night 1 had neither a death nor a return, and the header
        already carries the "nobody died" tick — a second line saying the
        same would be noise."""
        self.assertEqual(self.lines[0]["kind"], "day-foot")


if __name__ == "__main__":
    unittest.main()
