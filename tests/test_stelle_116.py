"""Stelle 116 (05.11.2026, claude/stelle-116.md): the setup shifts add up
whatever order they are reckoned in.

`_bags` used to reckon the setup characters one after another and threw a
shift out as soon as the counts went below nought half way. With the Xaan
before the Baron, "Baron +2, Xaan -2" was lost at a table with one
Outsider — the plain split with both in play (seed 2704 of the
Alchemist's gate, 04.11.2026).
"""

import unittest

from helpers import SolverTest                    # sets up the import path
from botc import scripts, worlds                  # noqa: E402

IDS = ["chef", "empath", "fortuneteller", "washerwoman", "investigator",
       "undertaker", "monk", "huntsman", "saint", "recluse", "butler",
       "damsel", "baron", "xaan", "godfather", "spy", "imp", "fanggu",
       "vigormortis"]
SC = scripts.from_ids("Stelle 116", IDS)


def bags(n):
    return [(frozenset(p), tuple(c[t] for t in ("townsfolk", "outsider",
                                                "minion", "demon")))
            for p, c in worlds._bags(n, SC)]


class TheOrderDoesNotMatter(SolverTest):

    def test_a_baron_and_a_xaan_may_leave_the_split_plain(self):
        # Eight seats: five Townsfolk, one Outsider, one Minion, one Demon.
        # Baron +2 and Xaan -2 is that split again.
        self.assertIn((frozenset({"Baron", "Xaan"}), (5, 1, 1, 1)), bags(8))

    def test_a_xaan_may_take_back_what_a_godfather_gave(self):
        self.assertIn((frozenset({"Godfather", "Xaan"}), (5, 1, 1, 1)),
                      bags(8))

    def test_a_huntsmans_damsel_is_not_taken_away(self):
        # The Damsel he brings stays: no bag with a Huntsman and no
        # Outsider at all.
        for present, split in bags(8):
            if "Huntsman" in present:
                self.assertGreaterEqual(split[1], 1, present)

    def test_one_that_cannot_shift_changes_nothing(self):
        # Seven seats have no Outsider: a Vigormortis alone removes none.
        self.assertIn((frozenset({"Vigormortis"}), (5, 0, 1, 1)), bags(7))


if __name__ == "__main__":
    unittest.main()
