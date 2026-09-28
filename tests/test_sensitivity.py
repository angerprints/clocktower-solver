"""How much of an answer is evidence, and how much is my guesswork.

Two related things live here. The sensitivity pass re-solves across the
plausible range of every judgement call, so a figure resting on one of
them can be told apart from one the evidence decided. The trust setting
is the other half: it takes the guess that turned out to matter most and
hands it to the person who actually knows.
"""

import unittest

from helpers import SolverTest, game, solved       # sets up the import path
import botc.solver as S                            # noqa: E402
from botc.info import Chef, Empath, Undertaker     # noqa: E402

TWELVE = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
          "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Slayer",
          "Recluse", "Saint"]


def busy():
    """A table with something for every prior to bite on."""
    return game(12, claims={i: r for i, r in enumerate(TWELVE)},
                deaths={0: "E1", 8: "N2"}, quiet_nights={3},
                infos=[Chef(1, 3, count=1), Empath(1, 4, count=1),
                       Empath(2, 4, count=2),
                       Undertaker(2, 6, target=0, role="Spy")])


class TheBands(SolverTest):

    @classmethod
    def setUpClass(cls):
        cls.got = S.sensitivity(busy(), dives=2500)

    def test_every_seat_gets_a_band_around_its_reading(self):
        for row in self.got["rows"]:
            self.assertLessEqual(row["low"], row["evil_pct"] + 0.01)
            self.assertGreaterEqual(row["high"], row["evil_pct"] - 0.01)
            self.assertBetween(row["low"], 0.0, 100.0)
            self.assertBetween(row["high"], 0.0, 100.0)

    def test_a_seat_that_moves_names_what_moved_it(self):
        movers = [r for r in self.got["rows"] if r["swing"] > 1.0]
        self.assertTrue(movers, "nothing moved at all — is anything wired up?")
        for row in movers:
            self.assertIn(row["driver"], S.PRIOR_RANGES)

    def test_the_bands_are_not_all_the_same_width(self):
        """The whole point: some seats the evidence has pinned down, and
        some are resting on a number I made up."""
        widths = sorted(r["high"] - r["low"] for r in self.got["rows"])
        self.assertGreater(widths[-1] - widths[0], 3.0)

    def test_the_widest_band_is_wider_than_the_sampling_error(self):
        """Modelling uncertainty was never shown, while statistical
        uncertainty was. On this table the hidden one is the larger."""
        widest = max(r["high"] - r["low"] for r in self.got["rows"])
        margin = max(r["margin"] for r in self.got["base"]["rows"])
        self.assertGreater(widest, margin)

    def test_the_same_walks_are_used_throughout(self):
        """Fixed seed, so the difference between settings is the setting
        and not sampling noise."""
        again = S.sensitivity(busy(), dives=2500)
        self.assertEqual([r["evil_pct"] for r in again["rows"]],
                         [r["evil_pct"] for r in self.got["rows"]])

    def test_every_prior_has_a_range_to_move_across(self):
        for name in ("OUTSIDER_HIDING_PENALTY", "BLUFF_COLLISION_PENALTY",
                     "POISON_HIT_PENALTY", "FABRICATED_INFO_PENALTY",
                     "NIGHT_DEATH_EVIL_PENALTY", "SUNK_KILL_PENALTY"):
            with self.subTest(prior=name):
                low, high = S.PRIOR_RANGES[name]
                self.assertLess(low, getattr(S, name))
                self.assertGreater(high, getattr(S, name))

    def test_the_constants_are_put_back_afterwards(self):
        self.assertPct(S.FABRICATED_INFO_PENALTY, 0.4, 1e-9)
        self.assertPct(S.POISON_HIT_PENALTY, 0.35, 1e-9)


class TrustingAReading(SolverTest):
    """The reading itself, separately from whoever announced it.

    This is what an unclaimed role needs: there is no seat to form an
    opinion about, so the opinion has to attach to the information.
    """

    CLAIMS = {0: "Washerwoman", 1: "Librarian", 2: "Investigator",
              3: "Chef", 4: "Slayer"}

    def empath_share(self, trust):
        state = game(7, claims=self.CLAIMS,
                     infos=[Empath(1, 0, trust, count=0),
                            Empath(2, 0, trust, count=0)])
        valid, _rows = solved(state)
        total = sum(S.world_weight(w, state) for w in valid)
        hit = sum(S.world_weight(w, state) for w in valid
                  if S.in_play(w, "Empath"))
        return 100 * hit / total if total else 0.0

    def test_believing_it_makes_the_role_more_likely_to_exist(self):
        self.assertRises(self.empath_share(0), self.empath_share(2))

    def test_disbelieving_it_takes_the_evidence_away(self):
        self.assertFalls(self.empath_share(0), self.empath_share(-2))

    def test_the_scale_runs_smoothly_between(self):
        curve = [self.empath_share(t) for t in range(-3, 4)]
        for a, b in zip(curve, curve[1:]):
            self.assertLess(a, b + 1e-9, f"not monotonic: {curve}")
        self.assertGreater(curve[-1] - curve[0], 40.0,
                           "the setting should be worth using")

    def test_disbelief_bottoms_out_rather_than_going_negative(self):
        """Not believing a reading means it costs nothing to have been
        invented. It cannot cost less than nothing."""
        self.assertPct(self.empath_share(-3), self.empath_share(-9), 0.01)

    def test_it_changes_what_a_silent_seat_is_guessed_as(self):
        believed = solved(game(7, claims=self.CLAIMS,
                               infos=[Empath(1, 0, 3, count=0),
                                      Empath(2, 0, 3, count=0)]))[1]
        doubted = solved(game(7, claims=self.CLAIMS,
                              infos=[Empath(1, 0, -3, count=0),
                                     Empath(2, 0, -3, count=0)]))[1]
        self.assertEqual(believed[5]["roles"][0][0], "Empath")
        self.assertNotEqual(doubted[5]["roles"][0][0], "Empath")

    def test_saying_nothing_leaves_the_old_behaviour(self):
        plain = game(7, claims=self.CLAIMS, infos=[Empath(1, 0, count=0)])
        zeroed = game(7, claims=self.CLAIMS, infos=[Empath(1, 0, 0, count=0)])
        self.assertEqual([r["evil_pct"] for r in solved(plain)[1]],
                         [r["evil_pct"] for r in solved(zeroed)[1]])


if __name__ == "__main__":
    unittest.main()
