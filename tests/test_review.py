"""Looking back on a real game (js/review.mjs, tools/review_game.mjs).

Phase 4: a game played by real people, the grimoire opened at the end,
and every morning solved again as the table knew it. Judged the way the
table judges it (30.09.2026): was the Demon found?
"""

import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from helpers import SolverTest                    # sets up the import path

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


def node(script, *args):
    got = subprocess.run([NODE, "--input-type=module", "-e", script, *args],
                         cwd=ROOT, capture_output=True, text=True,
                         timeout=600)
    if got.returncode:
        raise AssertionError(got.stderr)
    return json.loads(got.stdout.strip().splitlines()[-1])


BOARD = {
    "n_players": 7,
    "players": [
        {"claim": "Washerwoman", "events": ["X1"]},
        {"claim": "Empath", "events": ["N2"], "voted": [1, 2]},
        {"claim": "Chef", "events": ["X2"]},
        {"claim": "Slayer"},
        {"claim": "Undertaker"},
        {"claim": "Monk"},
        {"claim": "Saint"},
    ],
    "infos": [
        {"type": "Empath", "night": 1, "player": 1, "count": 0},
        {"type": "Undertaker", "night": 2, "player": 4, "target": 0,
         "role": "Washerwoman"},
        {"type": "SlayerShot", "night": 2, "player": 3, "target": 5,
         "died": False},
    ],
    "quiet_nights": [], "days_done": [1, 2],
    "script": {"name": "Trouble Brewing", "characters": None},
}


@unittest.skipUnless(NODE, "Node is not installed")
class EachMorningAsTheTableKnewIt(SolverTest):

    @classmethod
    def setUpClass(cls):
        cls.got = node("""
            import {boardAt, lastNight} from "./js/review.mjs";
            const b = JSON.parse(process.argv[1]);
            const at = k => boardAt(b, k);
            console.log(JSON.stringify({
              last: lastNight(b),
              two: at(2), one: at(1), three: at(3)}));
        """, json.dumps(BOARD))

    def test_the_game_reaches_the_night_after_the_last_execution(self):
        self.assertEqual(self.got["last"], 3)

    def test_night_events_count_up_to_that_night(self):
        events = [p["events"] for p in self.got["two"]["players"]]
        self.assertIn("N2", events[1])

    def test_a_day_counts_only_once_it_is_over(self):
        """At dawn after night 2, day 1's execution is known and day 2's
        is not — it has not happened yet."""
        two = [p["events"] for p in self.got["two"]["players"]]
        self.assertEqual(two[0], ["X1"])
        self.assertEqual(two[2], [])
        three = [p["events"] for p in self.got["three"]["players"]]
        self.assertEqual(three[2], ["X2"])

    def test_readings_by_night_and_day_rows_by_day(self):
        kinds = [r["type"] for r in self.got["two"]["infos"]]
        self.assertEqual(kinds, ["Empath", "Undertaker"])
        kinds = [r["type"] for r in self.got["three"]["infos"]]
        self.assertIn("SlayerShot", kinds)

    def test_votes_and_finished_days_too(self):
        self.assertEqual(self.got["two"]["players"][1]["voted"], [1])
        self.assertEqual(self.got["two"]["days_done"], [1])
        self.assertEqual(self.got["one"]["days_done"], [])


@unittest.skipUnless(NODE, "Node is not installed")
class JudgedByTheDemon(SolverTest):

    def test_place_and_ties(self):
        got = node("""
            import {judge} from "./js/review.mjs";
            const rows = [10, 40, 40, 5].map((d, i) =>
              ({player: i, demon_pct: d, evil_pct: d}));
            const truth = ["Chef", "Imp", "Empath", "Poisoner"];
            const clear = ["Chef", "Empath", "Imp", "Poisoner"];
            console.log(JSON.stringify({
              level: judge({rows, valid: 1}, truth),
              behind: judge({rows, valid: 1},
                            ["Imp", "Chef", "Empath", "Poisoner"])}));
        """)
        self.assertEqual(got["level"]["demon"]["rank"], 1)
        self.assertEqual(got["level"]["demon"]["level"], 1)
        self.assertTrue(got["level"]["found"])
        self.assertEqual(got["behind"]["demon"]["rank"], 3)
        self.assertFalse(got["behind"]["found"])

    def test_a_starpass_counts_either_demon(self):
        got = node("""
            import {trueDemons} from "./js/review.mjs";
            console.log(JSON.stringify(
              trueDemons(["Imp", "Chef", "Imp", "Baron"])));
        """)
        self.assertEqual(got, [0, 2])


@unittest.skipUnless(NODE, "Node is not installed")
class ASavedGameCanBeSentOn(SolverTest):

    def test_the_tool_reads_what_the_page_saves(self):
        game = {
            "format": "clocktower-solver-game", "version": 1,
            "script": {"name": "Trouble Brewing", "author": "",
                       "characters": None, "fabled": []},
            "game": {"n": 7, "players": BOARD["players"],
                     "infos": BOARD["infos"], "quiet": [], "done": [1, 2],
                     "fabled": [],
                     "truth": ["Washerwoman", "Empath", "Chef", "Slayer",
                               "Poisoner", "Imp", "Saint"]}}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump(game, f)
        got = subprocess.run([NODE, str(ROOT / "tools" / "review_game.mjs"),
                              f.name, "--json"], cwd=ROOT,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        out = json.loads(got.stdout)
        self.assertEqual(out["demons"], [5])
        self.assertEqual([n["night"] for n in out["nights"]], [1, 2, 3])
        self.assertTrue(all("demon" in n for n in out["nights"]))

    def test_without_the_truth_it_says_what_to_do(self):
        game = {"format": "clocktower-solver-game", "version": 1,
                "game": {"n": 7, "players": BOARD["players"], "infos": []}}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            json.dump(game, f)
        got = subprocess.run([NODE, str(ROOT / "tools" / "review_game.mjs"),
                              f.name], cwd=ROOT, capture_output=True,
                             text=True, timeout=60)
        self.assertEqual(got.returncode, 2)
        self.assertIn("After the game", got.stderr)


if __name__ == "__main__":
    unittest.main()
