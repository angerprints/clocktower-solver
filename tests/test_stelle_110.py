"""Stelle 110 (03.11.2026): the side a Pit-Hag's player keeps is read at
the Pit-Hag's turn.

"Each night*, choose a player & a character they become." The player
keeps their side. Which side that is was read as the night began. A Snake
Charmer acts before the Pit-Hag (220 before 280): "if you choose the
Demon, you swap characters and alignments". The seat the Demon left is
good by the Pit-Hag's turn.

Seed 1466 of the gate line Pit-Hag, Barber, Snake Charmer (Stelle 83, the
switch on): on night 3 the Snake Charmer (seat 3) swaps with the
Yaggababble (seat 1), and the Pit-Hag makes seat 1, now good, an Imp. The
solver kept the world but called the Imp evil.
"""
import json
import pathlib
import random
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc.info import GameState                   # noqa: E402

MUST = ("PitHag", "Barber", "SnakeCharmer")
ROOT = pathlib.Path(__file__).resolve().parent.parent


def game(seed=1466, must=MUST):
    import claims as C
    import play_games
    import simulate
    was = simulate.PIT_HAG_DEMONS
    simulate.PIT_HAG_DEMONS = 0.5
    try:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        n = [7, 8, 9, 10, 11][seed % 5]
        deal, heard = simulate.play(n, rng, nights=4, script=script)
        cl, wk, _ = C.claims_for(deal, rng, script=script)
    finally:
        simulate.PIT_HAG_DEMONS = was
    st = GameState(n_players=n, script=script, claims=cl, wakes=wk,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, st


def _imps(deal, st):
    """(side of the Imp on seat 1, did the Snake Charmer swap on night 3)
    for every story that makes it."""
    out = []
    for timeline, _cost in S.possible_timelines(deal.world(), st):
        changes = timeline
        imp = [c for c in changes if c.seat == 1 and c.role == "Imp"]
        if not imp:
            continue
        swapped = any(c.phase == "N3" and c.seat == 1
                      and c.role == "SnakeCharmer" for c in changes)
        out.append((imp[0].side, swapped))
    return out


class ThePitHagAfterTheSnakeCharmer(SolverTest):

    def test_the_game(self):
        deal, _st = game()
        self.assertEqual(deal.roles[1], "Yaggababble")
        self.assertEqual(deal.roles[3], "SnakeCharmer")
        self.assertEqual(deal.changes[:3],
                         [("N3", 3, "Yaggababble"), ("N3", 1, "SnakeCharmer"),
                          ("N3", 1, "Imp")])

    def test_the_imp_is_good_after_the_swap(self):
        deal, st = game()
        got = _imps(deal, st)
        self.assertTrue(any(swapped for _side, swapped in got))
        for side, swapped in got:
            if swapped:
                self.assertEqual(side, "good")

    def test_the_true_world_is_kept(self):
        deal, st = game()
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))



class BothLanguagesAgree(SolverTest):

    def test_on_the_game(self):
        import app
        import play_games
        import simulate
        from make_fixtures import played
        was = simulate.PIT_HAG_DEMONS
        simulate.PIT_HAG_DEMONS = 0.5
        try:
            rng = random.Random(1466)
            script = play_games.an_awkward_script(rng, must_have=MUST)
            payload = played("s1466", script, 1466,
                             [7, 8, 9, 10, 11][1466 % 5], 4,
                             rng=rng)["payload"]
        finally:
            simulate.PIT_HAG_DEMONS = was
        js = ("import {solveBoard} from './js/api.mjs';"
              "const p=JSON.parse(process.argv[1]);"
              "const r=solveBoard(p); console.log(JSON.stringify("
              "r.error || r.rows.map(x => x.evil_pct)));")
        got = subprocess.run(["node", "--input-type=module", "-e", js,
                              json.dumps(payload)], cwd=ROOT,
                             capture_output=True, text=True, timeout=1800)
        self.assertEqual(got.returncode, 0, got.stderr)
        from_js = json.loads(got.stdout)
        from_py = [row["evil_pct"] for row in app.run_solve(payload)["rows"]]
        for a, b in zip(from_js, from_py):
            self.assertAlmostEqual(a, b, places=6)
        # The seat the Demon left is good in most stories now (was 100 %).
        self.assertLess(from_py[1], 50)


if __name__ == "__main__":
    unittest.main()
