"""Stellen 62 and 63 (20.10.2026).

62  A Bounty Hunter shown a good player as evil: that player may be the
    Lycanthrope's faux paw. The solver never tried it as one, so beside
    a lying evil Townsfolk the board had no telling at all.
63  Under a Vortox, a Mathematician's number inside the range of counts
    it could have been was read as certainly true, so the Vortox or the
    Mathematician had to be droisoned. A false number sits inside the
    range just as well; only a range of one is certainly true.
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
from botc import info as I                        # noqa: E402
from botc.info import GameState                   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
INN = ("Innkeeper", "Psychopath", "Sailor")
# name, seed, players, nights, must have
PLAYED = (
    ("bounty-hunter-faux-paw", 2255, 7, 4, ("Kazali", "BountyHunter")),
    ("mathematician-vortox-charmer", 2801, 8, 4, INN),
    ("mathematician-vortox-sailor", 1674, 11, 4, INN),
)


def game(seed, n, nights, must):
    import claims as C
    import play_games
    import simulate
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    cl, wk, _ = C.claims_for(deal, rng, script=script)
    st = GameState(n_players=n, script=script, claims=cl, wakes=wk,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, heard, st


class ThePlayedGamesAreKept(SolverTest):

    def test_every_one(self):
        for name, seed, n, nights, must in PLAYED:
            deal, _heard, st = game(seed, n, nights, must)
            with self.subTest(name=name):
                self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_the_bounty_hunters_player_is_tried_as_the_faux_paw(self):
        deal, heard, st = game(*PLAYED[0][1:])
        shown = next(r.target for r in heard
                     if isinstance(r, I.BountyHunterInfo))
        self.assertFalse(deal.side_at(shown, "N1") == "evil")
        self.assertIn(shown, S._faux_paw_candidates(deal.world(), st))


class AMathematicianUnderAVortox(SolverTest):

    def test_a_number_in_a_range_may_be_false(self):
        deal, heard, st = game(*PLAYED[1][1:])
        row = next(r for r in heard if isinstance(r, I.MathematicianInfo))
        low, high = I._possible_impairment_counts(deal.world(), st,
                                                  row.night)
        self.assertTrue(row.holds(deal.world(), st, None))
        self.assertEqual(row.is_true(deal.world(), st), low == high)


def _payloads():
    from make_fixtures import played
    import play_games
    out = []
    for name, seed, n, nights, must in PLAYED:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        out.append(played(name, script, seed, n, nights, rng=rng)["payload"])
    return out


class BothLanguagesAgree(SolverTest):

    def test_on_the_played_games(self):
        import app
        cases = _payloads()
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); return r.error || r.valid; })));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        py = []
        for p in cases:
            r = app.run_solve(p)
            py.append(r.get("error") or r["valid"])
        self.assertEqual(json.loads(got.stdout), py)


if __name__ == "__main__":
    unittest.main()
