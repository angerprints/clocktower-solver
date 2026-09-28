"""The priors are judgement calls, so these tests check direction and
shape rather than exact numbers — with one exception. The last class
pins every constant to a scenario where it must bite, so a prior that
quietly stops being applied fails loudly instead of drifting.
"""

import unittest

from helpers import SolverTest, game, solved, spread   # sets up the import path
import botc.solver as S                                # noqa: E402
from botc.info import Empath                           # noqa: E402


class RolePercentages(SolverTest):

    def test_each_seat_adds_up_to_a_whole(self):
        _v, rows = solved(game(7))
        for row in rows:
            total = sum(pc for _r, pc in row["roles"])
            self.assertPct(total, 100.0, 0.01, f"seat {row['player']}")

    def test_nothing_escapes_the_zero_to_hundred_range(self):
        _v, rows = solved(game(7))
        for row in rows:
            for key in ("evil_pct", "demon_pct", "drunk_pct", "lying_pct"):
                self.assertBetween(row[key], 0.0, 100.0, f"{key} out of range")

    def test_lying_is_never_less_likely_than_being_evil_when_all_seats_claim(self):
        """With every seat claiming, an evil seat is a bluffing seat."""
        _v, rows = solved(game(7))
        for row in rows:
            self.assertGreaterEqual(row["lying_pct"] + 0.01, row["evil_pct"])


class SocialReads(SolverTest):

    def read_curve(self, seat=3):
        out = []
        for r in range(-3, 4):
            state = game(7, reads={seat: r} if r else {})
            out.append(solved(state)[1][seat]["evil_pct"])
        return out

    def test_a_read_moves_the_odds_in_the_direction_you_read(self):
        curve = self.read_curve()
        self.assertFalls(curve[3], curve[0], "reading them good should lower it")
        self.assertRises(curve[3], curve[6], "reading them evil should raise it")

    def test_the_curve_is_monotonic(self):
        curve = self.read_curve()
        for a, b in zip(curve, curve[1:]):
            self.assertLess(a, b + 1e-9, f"not monotonic: {curve}")

    def test_a_read_is_a_nudge_and_never_a_verdict(self):
        curve = self.read_curve()
        self.assertGreater(curve[0], 0.5, "a good read must not clear anyone")
        self.assertLess(curve[6], 99.5, "an evil read must not convict anyone")


class DeathPriors(SolverTest):

    def test_dying_early_at_night_clears_a_seat_harder_than_dying_late(self):
        base = solved(game(9))[1][3]["evil_pct"]
        n2 = solved(game(9, deaths={3: "N2"}))[1][3]["evil_pct"]
        n5 = solved(game(9, deaths={3: "N5"}))[1][3]["evil_pct"]
        self.assertFalls(base, n5)
        self.assertFalls(n5, n2)

    def test_only_night_deaths_carry_the_discount(self):
        """Checked on the weight itself rather than the final figure.

        A daytime death now narrows things through hard rules — an
        executed seat was not the Saint, and could only have been the
        Demon if the Scarlet Woman took over — so comparing percentages
        would confuse the prior with those. This looks straight at the
        prior instead.
        """
        from botc.worlds import World
        roles = ["Washerwoman", "Librarian", "Investigator", "Poisoner",
                 "Empath", "FortuneTeller", "Undertaker", "Recluse", "Imp"]
        claims = dict(spread(9))
        world = World(tuple(roles), (None,) * 9)

        def prior(deaths):
            return S.prior_weight(world, game(9, claims=claims, deaths=deaths))

        self.assertPct(prior({}), prior({3: "E2"}), 1e-9,
                       "an execution is the town's choice, not the Demon's")
        self.assertPct(prior({}), prior({3: "D2"}), 1e-9,
                       "nor is a Slayer shot")
        self.assertLess(prior({3: "N2"}), prior({}),
                        "a night kill is the Demon's choice, and it tells")


class BluffCollisions(SolverTest):

    def double_claim(self):
        claims = dict(spread(9))
        claims[7] = "Empath"                      # seats 4 and 7 both claim it
        return game(9, claims=claims)

    def test_a_double_claim_favours_one_of_them_being_real(self):
        state = self.double_claim()
        valid, _rows = solved(state)
        with_penalty = self.in_play_share(valid, state, "Empath")
        S.BLUFF_COLLISION_PENALTY = 1.0
        try:
            without = self.in_play_share(valid, state, "Empath")
        finally:
            S.BLUFF_COLLISION_PENALTY = 0.3
        self.assertGreater(with_penalty, without)

    @staticmethod
    def in_play_share(valid, state, role):
        total = sum(S.world_weight(w, state) for w in valid)
        hit = sum(S.world_weight(w, state) for w in valid if S.in_play(w, role))
        return 100 * hit / total if total else 0.0


class UnattributedInformation(SolverTest):

    def test_calling_a_role_nobody_claimed_makes_that_role_more_likely(self):
        claims = {0: "Washerwoman", 1: "Librarian", 2: "Investigator",
                  3: "Chef", 4: "Slayer"}
        quiet = game(7, claims=claims)
        called = game(7, claims=claims, infos=[Empath(1, 0, count=0),
                                               Empath(2, 0, count=0)])
        self.assertRises(self.empath_share(quiet), self.empath_share(called))

    def test_it_lands_on_the_seats_that_have_said_nothing(self):
        claims = {0: "Washerwoman", 1: "Librarian", 2: "Investigator",
                  3: "Chef", 4: "Slayer"}
        rows = solved(game(7, claims=claims, infos=[Empath(1, 0, count=0),
                                                    Empath(2, 0, count=0)]))[1]
        self.assertEqual(rows[5]["roles"][0][0], "Empath")

    @staticmethod
    def empath_share(state):
        valid, _rows = solved(state)
        total = sum(S.world_weight(w, state) for w in valid)
        hit = sum(S.world_weight(w, state) for w in valid if S.in_play(w, "Empath"))
        return 100 * hit / total if total else 0.0


class PoisonLuck(SolverTest):

    def test_information_that_holds_up_beats_information_that_needs_luck(self):
        """Seat 4's two Empath readings contradict each other with nobody
        dead, so a real Empath needs the Poisoner twice."""
        steady = game(9, infos=[Empath(1, 4, count=1), Empath(2, 4, count=1)])
        shifting = game(9, infos=[Empath(1, 4, count=1), Empath(2, 4, count=3)])
        self.assertRises(solved(steady)[1][4]["evil_pct"],
                         solved(shifting)[1][4]["evil_pct"])


class EveryPriorIsWiredIn(SolverTest):
    """If a constant stops changing the answer, it stopped being applied.

    Each entry sets the constant to a neutral value and asserts that some
    seat's evil reading moves. This is the guard against a refactor that
    silently drops a factor.
    """

    CASES = {
        "READ_ODDS_STEP": (1.0, lambda: game(7, reads={3: 3})),
        "NIGHT_DEATH_EVIL_PENALTY": (1.0, lambda: game(9, deaths={3: "N2"})),
        "POISON_HIT_PENALTY": (1.0, lambda: game(9, infos=[
            Empath(1, 4, count=1), Empath(2, 4, count=3)])),
        "POISON_REPEAT_PENALTY": (1.0, lambda: game(9, infos=[
            Empath(1, 4, count=1), Empath(2, 4, count=3), Empath(3, 4, count=3)])),
        "FABRICATED_INFO_PENALTY": (1.0, lambda: game(
            7, claims={0: "Washerwoman", 1: "Librarian", 2: "Investigator",
                       3: "Chef", 4: "Slayer"},
            infos=[Empath(1, 0, count=0)])),
        "BLUFF_COLLISION_PENALTY": (1.0, lambda: game(
            9, claims={**spread(9), 7: "Empath"})),
        "OUTSIDER_HIDING_PENALTY": (1.0, lambda: game(
            9, certainties={4: "hiding"})),
        "TOWNSFOLK_LIE_PENALTY": (1.0, lambda: game(
            9, certainties={4: "unsure"})),
        # Needs a table where a protector is claimed, so that some worlds
        # explain the quiet night for free and others have to pay. Applied
        # to every world alike, the factor would cancel in the
        # normalisation and look unwired when it is working perfectly.
        "SUNK_KILL_PENALTY": (1.0, lambda: game(
            12, quiet_nights={2}, deaths={0: "E1"})),
    }

    def test_each_constant_changes_the_answer(self):
        for name, (neutral, build) in self.CASES.items():
            with self.subTest(constant=name):
                state = build()
                before = [r["evil_pct"] for r in solved(state)[1]]
                original = getattr(S, name)
                setattr(S, name, neutral)
                try:
                    after = [r["evil_pct"] for r in solved(build())[1]]
                finally:
                    setattr(S, name, original)
                moved = max(abs(a - b) for a, b in zip(before, after))
                self.assertGreater(moved, 0.5,
                                   f"{name} made no difference — is it still applied?")


if __name__ == "__main__":
    unittest.main()
