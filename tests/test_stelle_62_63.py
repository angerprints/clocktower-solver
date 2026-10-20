"""Stellen 62 and 63 (20.10.2026).

62  A Bounty Hunter shown a good player as evil: that player may be the
    Lycanthrope's faux paw. The solver never tried it as one, so beside
    a lying evil Townsfolk the board had no telling at all.
63  Under a Vortox, a Mathematician's number inside the range of counts
    it could have been was read as certainly true, so the Vortox or the
    Mathematician had to be droisoned. A false number sits inside the
    range just as well; only a range of one is certainly true.
    And Patrick's J and K (20.10.2026), in the simulator: a Fang Gu that
    cannot die tonight does not jump (Weg 3); a first-night character
    the Huntsman makes on night one learns its information at once.
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
    ("fang-gu-guarded", 480, 7, 4, INN),
    ("fang-gu-guarded", 1259, 11, 4, INN),
    ("pixie-made-on-night-one", 1439, 11, 4, INN),
    ("philosopher-made-on-night-one", 229, 11, 4,
     ("Huntsman", "Damsel", "Pixie")),
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


class AGuardedFangGuDoesNotJump(SolverTest):
    """J, Weg 3: it cannot die instead, so the Outsider does not become
    it; the Outsider dies like anybody and the Fang Gu lives."""

    def test_the_outsider_dies_and_the_fang_gu_lives(self):
        deal, _heard, _st = game(*PLAYED[3][1:])
        self.assertIsNone(getattr(deal, "fanggu_jump", None))
        self.assertEqual(deal.deaths.get(2), "N2")       # the Damsel
        self.assertNotEqual(deal.deaths.get(4), "N2")    # the Fang Gu


class APixieMadeOnTheFirstNight(SolverTest):
    """K: a first-night character made tonight learns at once."""

    def test_it_is_shown_a_townsfolk_in_play(self):
        deal, heard, _st = game(*PLAYED[5][1:])
        row = next(r for r in heard if isinstance(r, I.PixieLearned))
        self.assertIn(row.role, [deal.role_at(p, "N1")
                                 for p in range(deal.n)])


class APhilosopherMadeOnTheFirstNight(SolverTest):
    """K, Weg 1: made after its place, it waits for its next night."""

    def test_it_does_not_choose_that_night(self):
        deal, heard, _st = game(*PLAYED[6][1:])
        made = [seat for (phase, seat, role) in deal.changes
                if phase == "N1" and role == "Philosopher"]
        self.assertTrue(made)
        self.assertFalse(any(isinstance(r, I.PhilosopherChoice)
                             and r.night == 1 and r.player in made
                             for r in heard))


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
                  " const r = solveBoard(p);"
                  " return [r.error || r.valid, !!r.sampled]; })));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        py, sampled = [], []
        for p in cases:
            r = app.run_solve(p)
            py.append(r.get("error") or r["valid"])
            sampled.append(bool(r.get("sampled")))
        # A board too big to count in time is sampled, and the two
        # languages draw different samples: only boards both counted must
        # agree.
        js = json.loads(got.stdout)
        both = [i for i, (v, s) in enumerate(js)
                if not s and not sampled[i]]
        self.assertEqual([js[i][0] for i in both], [py[i] for i in both])
        self.assertGreaterEqual(len(both), 4)


if __name__ == "__main__":
    unittest.main()
