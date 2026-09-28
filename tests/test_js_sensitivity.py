"""The guesswork check, on both sides.

Every figure the solver prints mixes the rulebook with a dozen constants
picked by judgement. This re-solves the same board with each constant
moved to the edges of its plausible range and reports how far each seat
travels, and which constant moved it.

It cannot be compared number-for-number: both sides sample, and they use
different generators on purpose. What *can* be compared is the thing the
answer is for — **which guess is load-bearing for which seat**. If the two
disagree about that, one of them is wrong about the shape of the problem
rather than merely noisy.

Skipped when Node is not installed.
"""

import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                            # noqa: E402
from botc import scripts                           # noqa: E402
from botc.info import Empath, GameState            # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "FortuneTeller", "Undertaker", "Recluse", "Saint"]

PAYLOAD = {
    "n_players": 9,
    "players": [{"claim": c, "events": (["N2"] if i == 2 else []),
                 "read": (2 if i == 8 else 0)}
                for i, c in enumerate(TB9)],
    "infos": [{"type": "Empath", "night": 1, "player": 4, "count": 1}],
}


def board():
    return GameState(
        n_players=9, script=scripts.TROUBLE_BREWING,
        claims={i: r for i, r in enumerate(TB9)},
        deaths={2: "N2"}, reads={8: 2},
        infos=[Empath(1, 4, count=1)])


@unittest.skipUnless(NODE, "Node is not installed")
class TheGuessworkCheckAgrees(SolverTest):

    @classmethod
    def setUpClass(cls):
        script = """
        await import("./js/characters.rules.mjs");
        const api = await import("./js/api.mjs");
        console.log(JSON.stringify(api.guessworkFor(%s)));
        """ % json.dumps(PAYLOAD)
        got = subprocess.run([NODE, "--input-type=module", "-e", script],
                             capture_output=True, text=True, timeout=900,
                             cwd=str(ROOT))
        if got.returncode:
            raise AssertionError(got.stderr)
        cls.js = json.loads(got.stdout.strip().splitlines()[-1])
        cls.py = S.sensitivity(board())

    def test_it_reports_a_row_per_seat(self):
        self.assertEqual(len(self.js["rows"]), 9)
        self.assertEqual(len(self.py["rows"]), 9)

    def test_the_bands_contain_the_reading(self):
        for row in self.js["rows"]:
            with self.subTest(seat=row["player"] + 1):
                self.assertLessEqual(row["low"], row["evil_pct"] + 0.05)
                self.assertGreaterEqual(row["high"], row["evil_pct"] - 0.05)

    def test_both_find_the_same_load_bearing_guess(self):
        """The point of the whole thing. Two samplers with different
        generators will not agree on a percentage, but they have to agree
        about which constant a seat's reading rests on — that is a fact
        about the board, not about the walk."""
        looked = 0
        for mine, theirs in zip(self.js["rows"], self.py["rows"]):
            if theirs["swing"] < 3.0:
                continue        # too flat for the driver to mean anything
            looked += 1
            with self.subTest(seat=mine["player"] + 1):
                self.assertEqual(mine["driver"],
                                 (theirs["driver"] or "").replace("_", " ")
                                 .lower())
        self.assertGreater(looked, 2, "too few moving seats to prove much")

    def test_both_agree_roughly_how_far_it_moves(self):
        for mine, theirs in zip(self.js["rows"], self.py["rows"]):
            with self.subTest(seat=mine["player"] + 1):
                self.assertAlmostEqual(mine["swing"], theirs["swing"],
                                       delta=6.0)

    def test_a_seat_the_evidence_pinned_down_barely_moves(self):
        """Seat 3 died on night two, which the night-death prior settles
        hard whatever else is varied."""
        self.assertLess(self.js["rows"][2]["swing"], 5.0)

    def test_a_seat_resting_on_a_read_swings(self):
        """Seat 9 carries a +2 social read and nothing else, so what a
        read is worth is the only thing holding it up."""
        row = self.js["rows"][8]
        self.assertGreater(row["swing"], 10.0)
        self.assertEqual(row["driver"], "read odds step")

    def test_it_names_the_constant_in_words(self):
        for row in self.js["rows"]:
            with self.subTest(seat=row["player"] + 1):
                self.assertNotIn("_", row["driver"])


class ThePageAsksNobodyForAnything(SolverTest):
    """The last `fetch` is gone.

    Read off the page itself, so it cannot drift from what ships.
    """

    def test_there_are_no_calls_left(self):
        html = (ROOT / "ui" / "index.html").read_text()
        self.assertNotIn('fetch("/api', html)

    def test_the_guesswork_check_is_solved_locally(self):
        html = (ROOT / "ui" / "index.html").read_text()
        self.assertIn("solver.guessworkFor(", html)


if __name__ == "__main__":
    unittest.main()
