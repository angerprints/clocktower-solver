"""Stelle 95 (30.10.2026): a Philosopher made in the night after its turn.

The Huntsman finds the Damsel late in the night and she becomes a
Philosopher. The Storyteller may wake her at once to choose, or leave it
for tomorrow (Patrick, A Weg 1): her waking that night is open, which a
Chambermaid beside her has to allow both ways. From the next night on she
is woken every night until she chooses.
"""
import unittest

from helpers import SolverTest                      # sets up the import path
from botc import waking                             # noqa: E402
from botc.info import GameState                     # noqa: E402
from botc.scripts import Script                     # noqa: E402
from botc.worlds import Change, Timeline, World     # noqa: E402

KEYS = ("Huntsman", "Damsel", "Philosopher", "Chambermaid", "Soldier",
        "Empath", "Imp", "Poisoner")


class ALatePhilosopher(SolverTest):

    def board(self):
        return GameState(n_players=6, script=Script(name="95", keys=KEYS),
                         claims={0: "Huntsman", 2: "Chambermaid",
                                 3: "Soldier", 4: "Empath"})

    def view(self, night=1):
        world = World(("Huntsman", "Damsel", "Chambermaid", "Soldier",
                       "Poisoner", "Imp"), (None,) * 6)
        return Timeline(world, (Change(f"N{night}", 1, "Philosopher",
                                       "good"),))

    def test_the_night_she_is_made_is_open(self):
        view, board = self.view(), self.board()
        self.assertFalse(waking.woke(view, board, 1, 1))
        self.assertTrue(waking.uncertain(view, board, 1, 1))

    def test_the_next_night_she_wakes(self):
        view, board = self.view(), self.board()
        self.assertTrue(waking.woke(view, board, 1, 2))
        self.assertFalse(waking.uncertain(view, board, 1, 2))

    def test_a_dealt_philosopher_is_not_open(self):
        world = World(("Huntsman", "Philosopher", "Chambermaid", "Soldier",
                       "Poisoner", "Imp"), (None,) * 6)
        self.assertFalse(waking.uncertain(world, self.board(), 1, 2))


if __name__ == "__main__":
    unittest.main()
