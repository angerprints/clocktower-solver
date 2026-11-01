"""Stelle 53 (01.11.2026): the Barber after a handover by day.

The Imp is shot on day 2 and the Scarlet Woman steps up; the Barber is
executed that day, so on night 3 the new Imp may swap two players.

(a) Run all at once, the Barber (slot 40) was asked before the Demon's
    lineage (last): it offered the dead Imp as the Demon that swaps, and
    the new Imp's swap with the Poisoner as two of anybody. A dealt Demon
    dead by the night of a Barber's swap now counts as a second mover, and
    the board is read a night at a time — as for the Snake Charmer
    (Stelle 60).
(b) Patrick, Weg 1: "2 players (not another Demon)" — the dead Imp still
    holds the Imp's character and is never chosen.
"""
import unittest

from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

IDS = ["slayer", "chef", "empath", "monk", "washerwoman", "librarian",
       "investigator", "barber", "scarletwoman", "poisoner", "imp",
       "butler", "recluse", "baron", "spy"]
SCRIPT = scripts.from_ids("Stelle 53", IDS)
#       0         1       2         3       4              5
ROLES = ["Slayer", "Chef", "Empath", "Monk", "Washerwoman", "Librarian",
         #  6              7         8               9           10
         "Investigator", "Barber", "ScarletWoman", "Poisoner", "Imp"]
CLAIMS = ROLES[:8] + ["Butler", "Recluse", "Chef"]


def board(**kw):
    return GameState(n_players=11, script=SCRIPT,
                     claims=dict(enumerate(CLAIMS)),
                     deaths={10: ("D2",), 7: ("D2",)}, executions={2: 7},
                     days_done={1, 2, 3},
                     infos=[I.SlayerShot(2, 0, target=10, died=True)], **kw)


def swaps(stories):
    out = []
    for changes, cost in stories:
        pair = [c for c in changes
                if isinstance(c, (S.DemonMinionSwap, S.OtherSwap))]
        if pair:
            out.append((type(pair[0]).__name__,
                        frozenset((c.seat, c.role) for c in pair), cost))
    return out


class TheBarberAfterADayHandover(SolverTest):

    def setUp(self):
        self.state = board()
        self.world = World(tuple(ROLES), (None,) * 11)

    def test_read_night_by_night(self):
        self.assertEqual(S._movers_in(self.world, self.state), 2)

    def test_the_heir_swaps_with_its_minion_as_usual(self):
        got = swaps(S.possible_timelines(self.world, self.state))
        usual = [s for s in got if s[0] == "DemonMinionSwap"]
        self.assertEqual(usual, [("DemonMinionSwap",
                                  frozenset({(8, "Poisoner"), (9, "Imp")}),
                                  1.0)])

    def test_the_dead_imp_is_never_chosen(self):
        got = swaps(S.possible_timelines(self.world, self.state))
        self.assertFalse([s for s in got
                          if any(seat == 10 for seat, _r in s[1])])
        # Every other pair of the ten seats is still offered.
        self.assertEqual(len(got), 45)

    def test_the_true_world_after_the_swap_is_kept(self):
        # The new Imp gave the Poisoner its character on night 3.
        self.assertIsNotNone(S.explanation_cost(self.world, self.state))


if __name__ == "__main__":
    unittest.main()
