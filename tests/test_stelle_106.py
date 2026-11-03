"""Stelle 106 (03.11.2026): the Farmer's heir and the Barber on one night.

On the night sheet the Barber's swap is at 590 and the Farmer at 690:
"If a Farmer died tonight, choose another good player and make them the
Farmer." So the heir is chosen from the board the swap left. The
simulator chose it first, before the swap, and then had to keep the
fresh heir out of the swap, or the swap would hand it a character the
dawn overwrote (Stelle 5, seed 1931). Now it chooses at the Farmer's
place, after the Barber and the Huntsman, and a seat the Demon swapped
may be made the Farmer. The solver stamps the heir at dawn already,
after every swap of the night, and needs nothing.
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
from botc.info import BecameInfo, GameState       # noqa: E402

MUST = ("Barber", "Farmer", "PitHag")


def game(seed, must=MUST):
    import claims as C
    import play_games
    import simulate
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    n = [7, 8, 9, 10, 11][seed % 5]
    deal, heard = simulate.play(n, rng, nights=4, script=script)
    cl, wk, _ = C.claims_for(deal, rng, script=script)
    st = GameState(n_players=n, script=script, claims=cl, wakes=wk,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, heard, st


class TheHeirIsChosenAfterTheSwap(SolverTest):

    def test_a_swapped_seat_may_be_made_the_farmer(self):
        deal, heard, st = game(2802)
        # The Barber (seat 6) hanged on day 2; in night 3 the Demon swaps
        # the Innkeeper (2) and the Seamstress (7), and the Farmer (8)
        # dies. At 690 the Seamstress' seat, an Innkeeper by then, is
        # made the Farmer.
        self.assertEqual(deal.roles[6], "Barber")
        self.assertEqual(deal.deaths.get(8), "N3")
        self.assertEqual(deal.changes,
                         [("N3", 7, "Innkeeper"), ("N3", 2, "Seamstress"),
                          ("D3", 7, "Farmer")])
        self.assertTrue(any(isinstance(r, BecameInfo) and r.player == 7
                            and r.role == "Farmer" and r.night == 3
                            for r in heard))
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_the_heir_comes_after_every_swap_of_its_night(self):
        for seed in (2802, 1931):
            deal, _heard, _st = game(seed, MUST if seed == 2802
                                     else ("PitHag", "Farmer",
                                           "Politician"))
            with self.subTest(seed=seed):
                for i, (when, _who, what) in enumerate(deal.changes):
                    if what != "Farmer" or when[0] != "D":
                        continue
                    later = deal.changes[i + 1:]
                    self.assertFalse(any(w == f"N{when[1:]}"
                                         for w, _s, _r in later))


if __name__ == "__main__":
    unittest.main()
