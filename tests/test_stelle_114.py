"""Stelle 114 (03.11.2026): an Innkeeper or a Sailor the Xaan poisoned.

"On night X, all Townsfolk are poisoned until dusk." The Innkeeper and
the Sailor are Townsfolk, and poisoned they drunk nobody. The simulator
asked whether they were droisoned before it added the Xaan's night, so
on night X their drunk still landed:

- Seed 2320 (line Innkeeper, Poisoner, Tea Lady, Sailor, Saint): the
  Innkeeper chose the Vortox on night 2, the Xaan's night, and the Vortox
  was drunk and killed nobody. The solver, which reads the Xaan first,
  found no reason for the quiet night.
- Seed 2509 (same line): the Sailor chose the Damsel on night 2, the
  Xaan's night; drunk, she survived a Harpy's right guess on day 2 and
  the game went on.

Both games now play as the rules have them, and the solver keeps them.
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

MUST = ("Innkeeper", "Poisoner", "TeaLady", "Sailor", "Saint")


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
    return deal, st


class TheXaansNight(SolverTest):

    def test_the_innkeeper_drunks_nobody(self):
        import simulate
        deal, st = game(2320)
        self.assertEqual(deal.roles[1], "Xaan")
        self.assertEqual(deal.roles[2], "Vortox")
        self.assertEqual(deal.roles[6], "Innkeeper")
        # Two Outsiders, so night 2 is the Xaan's.
        self.assertEqual(sum(simulate.TEAM[r] == "outsider"
                             for r in deal.roles), 2)
        self.assertEqual(deal.chose_by[("InnkeeperDrunk", 2)], {6: 2})
        self.assertNotIn(2, simulate.droisoned_at(deal, 2))
        self.assertIn(6, simulate.droisoned_at(deal, 2))
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_the_sailor_drunks_nobody(self):
        import simulate
        deal, st = game(2509)
        self.assertEqual((deal.roles[5], deal.roles[6], deal.roles[8]),
                         ("Damsel", "Xaan", "Sailor"))
        self.assertNotIn(5, simulate.droisoned_at(deal, 2, by_day=True))
        self.assertTrue(st.game_over)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))


if __name__ == "__main__":
    unittest.main()
