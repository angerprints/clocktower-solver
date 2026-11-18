"""A good player lying for no reason keeps quiet about its own readings
(15.11.2026, Patrick's answer E in claude/hauptziel-ein-luegner-lesarten.md)."""
import random
import unittest

from helpers import SolverTest                    # sets up the import path
import claims as C                                # noqa: E402
import simulate                                   # noqa: E402
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.info import GameState                   # noqa: E402

TB = scripts.TROUBLE_BREWING


def game(seed):
    rng = random.Random(seed)
    n = [7, 8, 9, 10][seed % 4]
    deal, heard = simulate.play(n, rng, nights=4, script=TB)
    claims, wakes, notes = C.claims_for(deal, rng, script=TB)
    return n, deal, heard, claims, wakes, notes


class TheLiarKeepsQuiet(SolverTest):

    def test_its_readings_are_gone_and_nobody_elses(self):
        # The first game with a liar that had readings: until 18.11.2026
        # seed 6, a good Librarian claiming the Chef for no reason. Chaos
        # is rare since (claude/hauptziel-chaos-2-lesarten.md).
        for seed in range(400):
            n, deal, heard, claims, wakes, notes = game(seed)
            liars = [s for s, why in notes.items() if "for no reason" in why
                     and not C._claims_its_own(why)
                     and any(r.player == s for r in heard)]
            if liars:
                liar = liars[0]
                break
        told = C.heard_by_table(heard, notes)
        self.assertTrue(any(r.player == liar for r in heard))
        self.assertFalse(any(getattr(r, "player", None) == liar
                             and not r.hard() for r in told))
        self.assertEqual(
            [r for r in heard if getattr(r, "player", None) != liar],
            [r for r in told if getattr(r, "player", None) != liar])

    def test_the_true_world_still_fits(self):
        for seed in range(40):
            n, deal, heard, claims, wakes, notes = game(seed)
            if not any("for no reason" in why for why in notes.values()):
                continue
            with self.subTest(seed=seed):
                state = GameState(n_players=n, script=TB, claims=claims,
                                  wakes=wakes,
                                  infos=C.heard_by_table(heard, notes),
                                  votes=dict(deal.votes),
                                  nominations=dict(deal.nominations),
                                  **deal.record(told=False))
                self.assertIsNotNone(S.explanation_cost(deal.world(), state))

    def test_an_honest_table_hears_everything(self):
        n, deal, heard, claims, wakes, notes = game(0)
        self.assertFalse(any("for no reason" in w for w in notes.values()))
        self.assertEqual(C.heard_by_table(heard, notes), list(heard))


if __name__ == "__main__":
    unittest.main()
