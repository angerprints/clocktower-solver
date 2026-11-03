"""Stelle 108 (03.11.2026): a Choirboy, a King and a hidden Barber.

"If the Demon kills the King, you learn which player is the Demon." In
seed 1832 of the gate line Pit-Hag, Barber, Snake Charmer (Stelle 83, the
switch on), the Barber dies on day 1, and that night the Demon swaps the
King and the Mayor. On night 4 the Po kills the new King, and the
Choirboy is shown the Po.

Nobody claims the Barber. For a Barber nobody claims, the solver offers
only the swap of the Demon with its own Minion (Stelle 4, Weg 1), so it
never tells the swap of two good players, and the Choirboy's row has no
King to stand on. The true world is lost on purpose, like seed 1931 of
Stelle 106. With the Barber claimed, the swap is offered and the world
kept.
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

MUST = ("PitHag", "Barber", "SnakeCharmer")


def game(seed=1832, must=MUST):
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


class AChoirboyAfterAHiddenBarber(SolverTest):

    def test_the_game(self):
        deal, st = game()
        self.assertEqual(deal.roles[5], "Barber")
        self.assertNotIn(5, st.claims)
        self.assertIn(("N2", 3, "King"), deal.changes)
        self.assertIn(("N2", 1, "Mayor"), deal.changes)
        self.assertIn(("N3", 4, "Po"), deal.changes)
        self.assertEqual(st.died_at(3), ("N4",))

    def test_only_the_demons_swap_is_offered(self):
        deal, st = game()
        told = [{(c.phase, c.seat, c.role) for c in changes}
                for changes, _cost in
                S.a_barber_lets_the_demon_swap_two(deal.world(), st)]
        self.assertEqual(told, [set(), {("N2", 4, "PitHag"),
                                        ("N2", 8, "Yaggababble")}])

    def test_the_true_world_is_lost_on_purpose(self):
        deal, st = game()
        self.assertIsNone(S.explanation_cost(deal.world(), st))

    def test_a_claimed_barber_keeps_it(self):
        deal, st = game()
        st.claims = dict(st.claims)
        st.claims[5] = "Barber"
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))


if __name__ == "__main__":
    unittest.main()
