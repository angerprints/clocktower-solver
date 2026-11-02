"""Stelle 103 (02.11.2026): the Monk choosing the Goon.

"Each night, the 1st player to choose you with their ability is drunk
until dusk." The Monk chooses at 230, before every Demon — but in the
simulator it never told the Goon, so an Al-Hadikhia at 500 read as the
first to choose it, was made drunk, and its three lived; the night-walk,
which has the Monk choose, killed them (seed 2409 of the line Al-Hadikhia,
Monk, Innkeeper, Tea Lady, Goon). Patrick, 02.11.2026: a simulator error.
"""
import random
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
from helpers import SolverTest                    # sets up the import path

MUST = ("AlHadikhia", "Monk", "Innkeeper", "TeaLady", "Goon")


def game(seed, must=MUST):
    import play_games
    import simulate
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    return simulate.play([7, 8, 9, 10, 11][seed % 5], rng, nights=4,
                         script=script)


class TheGoonAnswersTheMonk(SolverTest):

    def test_the_monk_is_the_first_to_choose_it(self):
        deal, _heard = game(2409)
        chooser, goon = deal.goon_first[3]
        self.assertEqual((deal.roles[chooser], deal.roles[goon]),
                         ("Monk", "Goon"))

    def test_the_night_walk_agrees_every_night(self):
        import nightwalk
        deal, heard = game(2409)
        for night in range(2, deal.nights_played + 1):
            got = nightwalk.walk(deal, night,
                                 nightwalk.hidden_from(deal, night, heard))
            with self.subTest(night=night):
                self.assertEqual(sorted(got.died),
                                 sorted(deal.died_on(f"N{night}")))


if __name__ == "__main__":
    unittest.main()
