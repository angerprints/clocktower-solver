"""Stelle 60 (15.10.2026): two small classes the Slayer brought out.

(a) The Scarlet Woman steps up in daylight, and on a later night a Snake
    Charmer chooses her. Run all at once, the charmer (slot 11) is asked
    before the Demon's lineage (last) and looks for the Demon where it
    was dealt, so the swap with her was never offered. A dealt Demon that
    died before the last swap now counts as a second mover, and the
    board is read a night at a time.
"""
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc.info import GameState                   # noqa: E402

GROUP_5 = ("Philosopher", "Slayer", "Virgin", "Golem", "Alsaahir", "Zealot",
           "Butler")
# seed, players, nights, must have
SWAPPED_THE_HEIR = ((127, 9, 4, GROUP_5),
                    (2001, 8, 6, ("Philosopher", "Slayer", "Virgin")))


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
    return deal, st


class ACharmerChoosesTheHeir(SolverTest):

    def test_the_played_games_are_kept(self):
        for seed, n, nights, must in SWAPPED_THE_HEIR:
            deal, st = game(seed, n, nights, must)
            with self.subTest(seed=seed):
                # The Scarlet Woman took over in daylight, and a charmer
                # later swapped with her.
                self.assertTrue(any(p[0] == "D" and r == "Vigormortis"
                                    for p, _s, r in deal.changes))
                self.assertEqual(S._movers_in(deal.world(), st), 2)
                self.assertIsNotNone(S.explanation_cost(deal.world(), st))


if __name__ == "__main__":
    unittest.main()
