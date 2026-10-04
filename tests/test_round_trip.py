"""A saved game, reopened.

Every field the page can record is written to the browser's own storage
and read back on the next visit. A field that saves but does not load is
invisible until somebody reopens a game mid-session and finds half of it
gone — and by then the game is the thing they lost.

So this loads a game with something in *every* field, lets the page boot,
and compares what comes back out against what went in. Not a check on any
one feature: a check that adding a feature has not quietly broken the
save format for the others.

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
class AGameSurvivesBeingReopened(SolverTest):

    @classmethod
    def setUpClass(cls):
        import tools.build_site as build
        build.build()
        got = subprocess.run(
            [NODE, str(ROOT / "tests" / "harness" / "round_trip.mjs")],
            capture_output=True, text=True, timeout=300)
        if got.returncode:
            raise AssertionError(f"the round trip failed:\n{got.stderr}")
        cls.got = json.loads(got.stdout.strip().splitlines()[-1])

    def test_nothing_is_lost(self):
        self.assertEqual(self.got["lost"], [])

    def test_the_harness_looks_at_every_field(self):
        """A round trip that checked three fields would pass for ever.
        This one is only worth having if it covers what the page can
        actually record."""
        source = (ROOT / "tests" / "harness" / "round_trip.mjs").read_text()
        for field in ("name", "claim", "events", "certainty", "read",
                      "suspect", "voted", "nominated", "quiet", "done",
                      "over", "notes", "infos"):
            with self.subTest(field=field):
                self.assertIn(f'"{field}"', source)


class TheGameIsOverReachesTheSolver(SolverTest):
    """A switch that is saved and never sent does nothing.

    The solver takes a game to be going on, and with a Zombuul on the
    script reads two players alive as "the Demon is one of the dead". A
    board from after the end has to say so (04.10.2026). Solving and the
    guesswork check both send it; looking back does not, because it
    marks its own last morning.
    """

    def test_the_page_has_the_switch_and_sends_it(self):
        page = (ROOT / "ui" / "index.html").read_text()
        self.assertIn('tick.id="game-over"', page)
        self.assertEqual(page.count("game_over:!!S.over"), 2)

    def test_looking_back_marks_only_its_last_morning(self):
        source = (ROOT / "js" / "review.mjs").read_text()
        self.assertIn("game_over: night === last", source)


if __name__ == "__main__":
    unittest.main()
