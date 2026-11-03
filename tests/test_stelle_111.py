"""Stelle 111 (03.11.2026): Pit-Hag nights with a second Demon, where the
night-walk and the simulator disagreed, and seed 729, which the solver
lost.

Found at the gate of Stelle 83, with the Pit-Hag making Demons on half its
turns (`SIM_PIT_HAG_DEMONS`):

- Seed 1506 (line Pit-Hag): the Pit-Hag chooses the Goon. "The 1st player
  to choose you with their ability is drunk until dusk." The simulator
  never asked the Goon, so the Pit-Hag made its change and stayed sober.
- Seed 2064 (line Pit-Hag, Scarlet Woman, Fang Gu): the Acrobat chooses
  the Vigormortis, whom a Snake Charmer swaps with that night: "if they
  are or become drunk or poisoned tonight, you die". The simulator
  counted the swap's poison from the night after.
- Seed 1341 (line Pit-Hag, Barber, Snake Charmer): the Pit-Hag makes the
  Demon a Lleech, which chooses its host at once. The night-walk gave it
  no host on a night whose deaths are the Storyteller's.
- Seed 729 (line Pit-Hag, Scarlet Woman, Fang Gu): a Snake Charmer swaps
  with the Pukka, and the next night the Pit-Hag makes the good Snake
  Charmer left behind a Lleech. The solver's Demon line stayed on that
  seat as if it had never stopped being the Demon, and the Scarlet Woman
  never took the Imp's star.
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
HB = ("PitHag", "Barber", "SnakeCharmer")
HS = ("PitHag", "ScarletWoman", "FangGu")
HP = ("PitHag",)


class asked:
    """The simulator with the switch on, for one block."""

    def __enter__(self):
        import simulate
        self.was = simulate.PIT_HAG_DEMONS
        simulate.PIT_HAG_DEMONS = 0.5
        return simulate

    def __exit__(self, *_exc):
        import simulate
        simulate.PIT_HAG_DEMONS = self.was
        return False


def game(seed, must):
    import claims as C
    import play_games
    with asked() as simulate:
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        n = [7, 8, 9, 10, 11][seed % 5]
        deal, heard = simulate.play(n, rng, nights=4, script=script)
        cl, wk, _ = C.claims_for(deal, rng, script=script)
    st = GameState(n_players=n, script=script, claims=cl, wakes=wk,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, heard, st


def walked(deal, heard, night):
    import nightwalk
    got = nightwalk.walk(deal, night, nightwalk.hidden_from(deal, night,
                                                            heard))
    return sorted(got.died), sorted(deal.died_on(f"N{night}"))


class ThePitHagChoosesTheGoon(SolverTest):

    def test_it_makes_nothing(self):
        deal, heard, _st = game(1506, HP)
        self.assertEqual(deal.goon_first.get(3, (None,))[0],
                         deal.roles.index("PitHag"))
        self.assertFalse([c for c in deal.changes if c[0] == "N3"])
        self.assertFalse([r for r in heard if r.night == 3
                          and type(r).__name__ == "PitHagChoice"])

    def test_both_walks_agree(self):
        deal, heard, _st = game(1506, HP)
        walk, sim = walked(deal, heard, 3)
        self.assertEqual(walk, sim)


class TheAcrobatAndTheSwappedDemon(SolverTest):

    def test_the_acrobat_dies(self):
        deal, heard, _st = game(2064, HS)
        walk, sim = walked(deal, heard, 4)
        self.assertEqual(walk, sim)
        self.assertEqual(deal.roles[sim[0]], "Acrobat")


class ALleechThePitHagMade(SolverTest):

    def test_both_walks_agree(self):
        deal, heard, _st = game(1341, HB)
        walk, sim = walked(deal, heard, 3)
        self.assertEqual(walk, sim)


class TheStarLeftBeforeThePitHagCame(SolverTest):

    def test_the_game(self):
        deal, _heard, _st = game(729, HS)
        self.assertEqual(deal.changes[:4],
                         [("N2", 5, "Pukka"), ("N2", 3, "SnakeCharmer"),
                          ("N2", 5, "Imp"), ("N3", 3, "Lleech")])
        self.assertIn(("N3", 8, "Imp"), deal.changes)

    def test_the_scarlet_woman_takes_the_star(self):
        deal, _heard, st = game(729, HS)
        told = [{(c.phase, c.seat, c.role) for c in changes}
                for changes, _cost in S.possible_timelines(deal.world(), st)]
        self.assertTrue(any(("N3", 8, "Imp") in t for t in told))

    def test_the_true_world_is_kept(self):
        deal, _heard, st = game(729, HS)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_both_languages_keep_it(self):
        # The whole board has 96,408 legal deals and takes Python twenty
        # minutes; the true world alone is asked in both.
        import play_games
        from make_fixtures import played
        deal, _heard, st = game(729, HS)
        with asked():
            rng = random.Random(729)
            script = play_games.an_awkward_script(rng, must_have=HS)
            payload = played("s729", script, 729, [7, 8, 9, 10, 11][729 % 5],
                             4, rng=rng)["payload"]
        js = ("import {readBoard} from './js/api.mjs';"
              "import {explanationCost} from './js/scoring.mjs';"
              "import {World} from './js/worlds.mjs';"
              "const [p, roles, believes]=JSON.parse(process.argv[1]);"
              "const {state}=readBoard(p);"
              "console.log(JSON.stringify(explanationCost("
              "new World(roles, believes), state)));")
        got = subprocess.run(
            ["node", "--input-type=module", "-e", js,
             json.dumps([payload, list(deal.roles),
                         list(deal.world().believes)])],
            cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        from_js = json.loads(got.stdout)
        from_py = S.explanation_cost(deal.world(), st)
        self.assertIsNotNone(from_js)
        self.assertAlmostEqual(from_js, from_py, places=6)

if __name__ == "__main__":
    unittest.main()
