"""Die Engine des Einzelspieler-Spiels als unabhängiger Schiedsrichter.

Jede Partie der Engine kennt die volle Wahrheit und das öffentliche
Protokoll. Der Solver muss die wahre Welt behalten. Diese Prüfung bricht
den Zirkelschluss, dass Solver und Simulator zusammen geschrieben wurden.

Läuft nur, wenn die Engine da ist:

    set CLOCKTOWER_ENGINE=J:\\dev\\clocktower
    python run_tests.py engine_bridge

Gefunden beim ersten Lauf (28.09.2026):

  * Ein vergifteter Imp tötet niemanden, und der Solver kannte als
    Erklärung einer ruhigen Nacht nur einen Schild vor dem Opfer. Ein
    Giftmischer, der den eigenen Dämon trifft, machte das Brett
    unmöglich.
  * Der erste Fix dafür bot die neue Erklärung auch ohne Giftquelle an.
    `_night_accounts` behält nur die ersten 24 Kombinationen, und fünf
    ruhige Nächte voller Sackgassen verdrängten die echte Geschichte.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

ENGINE = os.environ.get("CLOCKTOWER_ENGINE")


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
