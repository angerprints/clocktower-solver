"""Real games stay explainable (real-games/).

A game from a real table, with the grimoire opened at the end, is the
one check that owes nothing to this repository's simulator. Whatever
the solver ranks first, the world that really happened must remain one
it allows — at every morning, cut back to what the table knew.

The ranking itself is not pinned here: it moves with every weight, and
for these boards it comes from sampling. See real-games/README.md.
"""

import json
import pathlib
import shutil
import subprocess
import unittest
from unittest import mock

from helpers import SolverTest                    # sets up the import path

import app
from botc import solver as S
from botc.worlds import World

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
KEY = {"Fortune Teller": "FortuneTeller", "Scarlet Woman": "ScarletWoman"}


class _Built(Exception):
    pass


def state_of(payload):
    """The board as the solver reads it, without solving it."""
    got = {}

    def keep(state, *args, **kwargs):
        got["state"] = state
        raise _Built

    with mock.patch.object(app, "analyze", keep):
        try:
            reply = app.run_solve(payload)
        except _Built:
            return got["state"]
    raise AssertionError(reply)


def mornings(doc):
    """Each morning's board, cut back by the page's own rule."""
    g = doc["game"]
    full = {"n_players": g["n"], "allow_good_lies": False,
            "players": g["players"], "infos": g["infos"],
            "quiet_nights": g["quiet"], "days_done": g["done"],
            "script": doc["script"], "fabled": []}
    out = subprocess.run(
        [NODE, "--input-type=module", "-e",
         'import {boardAt, lastNight} from "./js/review.mjs";'
         'const b = JSON.parse(process.argv[1]);'
         'const out = [];'
         'for (let k = 1; k <= lastNight(b); k++) out.push(boardAt(b, k));'
         'console.log(JSON.stringify(out));', json.dumps(full)],
        cwd=ROOT, capture_output=True, text=True, timeout=120, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(NODE, "Node is not installed")
class TheStreamedMarionetteGame(SolverTest):
    """Trouble Brewing with a Marionette, 12 players (01.10.2026)."""

    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(
            (ROOT / "real-games" / "2026-10-01-tb-marionette-stream.json")
            .read_text(encoding="utf-8"))
        g = cls.doc["game"]
        cls.truth = World(tuple(KEY.get(r, r) for r in g["truth"]),
                          tuple(g["believes"]))
        cls.boards = mornings(cls.doc)

    def test_six_mornings(self):
        self.assertEqual(len(self.boards), 6)

    def test_the_true_world_is_allowed_every_morning(self):
        for k, board in enumerate(self.boards, 1):
            with self.subTest(morning=k):
                cost = S.explanation_cost(self.truth, state_of(board))
                self.assertIsNotNone(cost)
                self.assertGreater(cost, 0)

    def test_only_the_poisoners_made_up_readings_cost_anything(self):
        """The Marionette's and the Drunk's readings are what they were
        shown, so they are free. Ekken invented two Undertaker readings,
        and those are all the true world pays for."""
        cost = S.explanation_cost(self.truth, state_of(self.boards[-1]))
        self.assertAlmostEqual(cost, S.FABRICATED_INFO_PENALTY ** 2)


if __name__ == "__main__":
    unittest.main()
