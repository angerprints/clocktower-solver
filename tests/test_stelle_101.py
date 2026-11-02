"""Stelle 101 (02.11.2026): a Philosopher somebody made later chooses.

Patrick: "ein Philo, welcher durch das Grubenweib erschaffen wurde, darf in
der nächsten Nacht aktiv werden" — the rule of Stelle 100: a character
made later in the night acts that night only if its place comes after;
the Philosopher's (100) comes before the Pit-Hag's (280), the Barber's
and the Huntsman's, so one made by them chooses the night after. In the
simulator it never chose at all.

Found on the way (seed 171): the simulator's Chambermaid did not count a
Philosopher waking to choose after the first night.
"""
import random
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc.info import GameState, PhilosopherChoice  # noqa: E402

# seed: the characters its gate line asks for. Each has a Philosopher made
# later that chose on a later night.
PLAYED = {171: ("PitHag", "Philosopher"),
          32: ("PitHag", "Philosopher"),
          54: ("Huntsman", "Damsel", "Philosopher"),
          152: ("Barber", "Philosopher")}


def game(seed, must):
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


class AMadePhilosopherChooses(SolverTest):

    def test_on_a_later_night_and_the_true_world_is_kept(self):
        for seed, must in PLAYED.items():
            deal, heard, st = game(seed, must)
            with self.subTest(seed=seed):
                late = [h for h in heard if isinstance(h, PhilosopherChoice)
                        and h.night > 1]
                self.assertTrue(late)
                for row in late:
                    # Made, not dealt — and on an earlier night.
                    self.assertNotEqual(deal.roles[row.player], "Philosopher")
                    self.assertTrue(any(
                        who == row.player and what == "Philosopher"
                        and int(when[1:]) < row.night
                        for when, who, what in deal.changes))
                self.assertIsNotNone(S.explanation_cost(deal.world(), st))


if __name__ == "__main__":
    unittest.main()
