"""Stelle 112 (03.11.2026): a drunk or poisoned Monk still chooses.

A droisoned ability does not work, but its holder still wakes and
chooses. Choosing the Goon first that night, the Monk is drunk until dusk
(it is already) and the Goon turns to its side (Patrick, 02.11.2026: "doch
nimm das bitte auf, genau für den fall mit dem schläger"). The simulator
let only a working Monk choose, so this never happened.

Seed 390 of the line Monk, Goon, Poisoner: the Goon (seat 6) turned evil
on night 2; on night 3 the droisoned Monk (seat 5) chooses it first, and
the Goon is good again. The Monk guards nobody.
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

MUST = ("Monk", "Goon", "Poisoner")


def game(seed=390, must=MUST):
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


class ADroisonedMonkChoosesTheGoon(SolverTest):

    def test_the_game(self):
        deal, _heard, _st = game()
        self.assertEqual(deal.roles[5], "Monk")
        self.assertEqual(deal.roles[6], "Goon")
        self.assertFalse(deal.working(5, 3))
        self.assertEqual(deal.goon_first[3], (5, 6))

    def test_the_goon_turns_good(self):
        deal, _heard, _st = game()
        self.assertIn(("N2", 6, "Goon", "evil"), deal.side_changes)
        self.assertIn(("N3", 6, "Goon", "good"), deal.side_changes)

    def test_both_walks_agree(self):
        import nightwalk
        deal, heard, _st = game()
        got = nightwalk.walk(deal, 3, nightwalk.hidden_from(deal, 3, heard))
        self.assertEqual(sorted(got.died), sorted(deal.died_on("N3")))

    def test_the_true_world_is_kept(self):
        deal, _heard, st = game()
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))


if __name__ == "__main__":
    unittest.main()
