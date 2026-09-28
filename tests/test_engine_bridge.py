"""Die Engine des Einzelspieler-Spiels als unabhängiger Schiedsrichter.

Jede Partie der Engine kennt die volle Wahrheit und das öffentliche
Protokoll. Der Solver muss die wahre Welt behalten. Diese Prüfung bricht
den Zirkelschluss, dass Solver und Simulator zusammen geschrieben wurden.

Läuft nur, wenn die Engine da ist:

    set CLOCKTOWER_ENGINE=J:\\dev\\clocktower
    python run_tests.py engine_bridge

Gefunden beim ersten Lauf (28.09.2026), 400 Partien:

  * Ein vergifteter Imp tötet niemanden, und der Solver kannte als
    Erklärung einer ruhigen Nacht nur einen Schild vor dem Opfer. Ein
    Giftmischer, der den eigenen Dämon trifft, machte das Brett
    unmöglich.
  * Der erste Fix dafür bot die neue Erklärung auch ohne Giftquelle an.
    `_night_accounts` behält nur die ersten 24 Kombinationen, und fünf
    ruhige Nächte voller Sackgassen verdrängten die echte Geschichte.
  * Die Wahrsagerin bekommt auch für einen toten Dämon ein Nicken. Der
    Solver fragte, wer in dieser Nacht als Dämon handelt, und hielt ein
    wahres Ja auf den hingerichteten Imp für unmöglich.
  * Folgefehler, sichtbar erst durch den ersten Punkt: Die Planung der
    Störungen hielt jede kostenlose Quelle für eine, die jeden trifft,
    den sie erreicht. Eine tote Sweetheart machte so die ganze Stadt
    betrunken, und „der Dämon hat funktioniert" war unmöglich.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

ENGINE = os.environ.get("CLOCKTOWER_ENGINE")


class WhatTheEngineFound(unittest.TestCase):
    """Rule faults the engine exposed, pinned without needing the engine."""

    def test_a_poisoned_demon_explains_a_quiet_night(self):
        from botc import solver as S
        from botc.info import GameState
        from botc.worlds import World
        w = World(("Poisoner", "Undertaker", "Investigator",
                   "FortuneTeller", "Imp"), (None,) * 5)
        self.assertIsNotNone(S.explanation_cost(
            w, GameState(n_players=5, quiet_nights={2}, days_done={1, 2})))
        # And nothing else can: without a source the night stays owed.
        w2 = World(("Chef", "Undertaker", "Investigator",
                    "FortuneTeller", "Imp"), (None,) * 5)
        self.assertIsNone(S.explanation_cost(
            w2, GameState(n_players=5, quiet_nights={2}, days_done={1, 2})))

    def test_a_dead_demon_still_gets_the_fortune_tellers_nod(self):
        """Partie 115: The Imp is executed, the Scarlet Woman takes over,
        and on night three the Fortune Teller picks the dead Imp. "If they
        choose a dead Demon, then the Fortune Teller still receives a nod"
        (wiki). The solver asked who was acting as the Demon that night
        and called a true yes impossible."""
        from botc import info as I
        from botc import solver as S
        from botc.info import GameState
        from botc.worlds import World
        w = World(("ScarletWoman", "Imp", "FortuneTeller", "Ravenkeeper",
                   "Chef"), (None,) * 5)

        def board(yes):
            return GameState(n_players=5, deaths={1: ("D1",)},
                             executions={1: 1}, days_done={1, 2},
                             infos=[I.FortuneTeller(3, 2, 0, a=1, b=4,
                                                    yes=yes)])
        self.assertIsNotNone(S.explanation_cost(w, board(True)))
        # And a "no" on the dead Imp needs a droisoned Fortune Teller,
        # which nothing on this board can provide.
        self.assertIsNone(S.explanation_cost(w, board(False)))

    def test_a_sweetheart_drunks_one_player_not_the_town(self):
        """Free is not the same as unavoidable. A Sweetheart reaches the
        whole table and picks one; the planner put all nine in the
        impaired set, so a Demon that killed after her death — and so had
        to be working — could never be planned."""
        from botc import impairment
        sweetheart = impairment.Source("Sweetheart", frozenset(range(9)),
                                       capacity=1, cost=1.0, repeat_cost=1.0)
        self.assertFalse(sweetheart.unavoidable())
        self.assertIsNotNone(impairment.plan_night([sweetheart], [], [3], {}))
        # And one pick covers one seat, not two.
        self.assertIsNotNone(impairment.plan_night([sweetheart], [4], [3], {}))
        self.assertIsNone(impairment.plan_night([sweetheart], [4, 5], [], {}))
        # Being the Drunk still is unavoidable.
        drunk = impairment.Source("believer", frozenset({2}), capacity=1)
        self.assertTrue(drunk.unavoidable())
        self.assertIsNone(impairment.plan_night([drunk], [], [2], {}))



@unittest.skipUnless(ENGINE and os.path.isdir(os.path.join(ENGINE or "", "engine")),
                     "CLOCKTOWER_ENGINE zeigt nicht auf die Engine")
class TheEngineIsAnIndependentReferee(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, ENGINE)
        import engine_bridge
        cls.B = engine_bridge

    def sweep(self, games, mode, hirn=False, start=0):
        import botc.solver as S
        bad = []
        for i in range(start, start + games):
            n = [5, 6, 7, 8, 9][i % 5]
            state = self.B.play(i, n, 1 + i % 5, 1 + (i // 5) % 5, hirn)
            if S.explanation_cost(self.B.world_of(state),
                                  self.B.board_from(state, mode)) is None:
                bad.append(i)
        return bad

    def test_every_grimoire_board_keeps_the_truth(self):
        """Jeder Sitz ehrlich, auch gestörte Information: keine Lügen,
        nur Regeln."""
        self.assertEqual(self.sweep(120, "grimoire"), [])

    def test_five_quiet_nights_of_corpse_aims_survive(self):
        """Partie 42: Der Imp zielt fünf Nächte lang auf Tote. Ohne
        Giftquelle darf die Erklärung „vergiftet" keinen Platz in den
        ersten 24 Kombinationen belegen."""
        import botc.solver as S
        state = self.B.play(42, 7, 3, 4, False)
        self.assertIsNotNone(S.explanation_cost(
            self.B.world_of(state), self.B.board_from(state, "grimoire")))


if __name__ == "__main__":
    unittest.main()
