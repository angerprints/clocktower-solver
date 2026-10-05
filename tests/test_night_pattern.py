"""The nights of a game, counted against the day before each.

A Zombuul kills only after a day on which nobody died, and every other
Demon kills whatever the day did. The solver does not read that: every
quiet night has a legal account under the other Demons, and weighing
those accounts was measured to cost more than it finds (05.10.2026). So
the page counts the nights and says what it counted, where a Zombuul is
on the script. It changes no number.

The page is asked what it draws rather than trusted to draw it.

Skipped when Node is not installed.
"""

import json
import os
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
RULE = "A Zombuul kills only after a day with no death."


@unittest.skipUnless(NODE, "Node is not installed")
class TheNightsAreCounted(SolverTest):

    @classmethod
    def setUpClass(cls):
        import tools.build_site as build
        build.build()

    def drawn(self, game, script="Bad Moon Rising"):
        got = subprocess.run(
            [NODE, str(ROOT / "tests" / "harness" / "night_pattern.mjs")],
            capture_output=True, text=True, timeout=300,
            env=dict(os.environ, GAME=json.dumps(game), SCRIPT=script))
        if got.returncode:
            raise AssertionError(f"the page failed to draw:\n{got.stderr}")
        return json.loads(got.stdout.strip().splitlines()[-1])

    def test_quiet_after_every_execution_fits_a_zombuul(self):
        """Three executions, three quiet nights, then a day nobody went
        and a body the morning after."""
        lines = self.drawn({
            "events": {"Anna": ["X1"], "Ben": ["X2"], "Cara": ["X3"],
                       "Dan": ["N5"]},
            "quiet": [2, 3, 4], "done": [4]})
        self.assertEqual(lines, [
            "Night pattern",
            "After a day with a death: 3 nights quiet · 0 nights with deaths",
            "After a day with no death: 0 nights quiet · 1 night with deaths",
            RULE + " This pattern fits one.",
        ])

    def test_a_body_after_an_execution_was_somebody_elses(self):
        """It does not say the Demon is no Zombuul — an Assassin kills
        whenever it likes. It says what a Zombuul would need."""
        lines = self.drawn({
            "events": {"Anna": ["X1"], "Ben": ["N2"], "Cara": ["X2"]},
            "quiet": [3]})
        self.assertEqual(lines[1],
            "After a day with a death: 1 night quiet · 1 night with deaths")
        self.assertEqual(lines[-1], RULE + " If the Demon is a Zombuul, "
                         "something else killed on 1 night.")

    def test_every_death_by_day_counts(self):
        """Not only an execution: "any death at all stops it"."""
        lines = self.drawn({"events": {"Anna": ["D1"]}, "quiet": [2]})
        self.assertIn("After a day with a death: 1 night quiet", lines[1])

    def test_walking_away_from_the_gallows_is_no_death(self):
        lines = self.drawn({"events": {"Anna": ["S1"], "Ben": ["N2"]}})
        self.assertEqual(lines[1],
            "After a day with no death: 0 nights quiet · 1 night with deaths")
        self.assertEqual(lines[-1], RULE)

    def test_a_night_not_written_down_is_not_counted(self):
        """Night three has neither a body nor the tick."""
        lines = self.drawn({"events": {"Anna": ["X1"], "Ben": ["X2"],
                                       "Cara": ["X3"]}, "quiet": [2]})
        self.assertIn("1 night quiet", lines[1])

    def test_nothing_before_the_second_night(self):
        self.assertIsNone(self.drawn({"events": {"Anna": ["X1"]}}))

    def test_nothing_without_a_zombuul_on_the_script(self):
        game = {"events": {"Anna": ["X1"], "Ben": ["X2"]}, "quiet": [2, 3]}
        self.assertIsNone(self.drawn(game, "Trouble Brewing"))
        self.assertIsNone(self.drawn(game, "Sects & Violets"))


if __name__ == "__main__":
    unittest.main()
