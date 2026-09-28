"""Soft claims about waking at night: "I don't wake", "only the first
night". They narrow the good roles without naming one.
"""

import unittest

from helpers import SolverTest, game, solved      # sets up the import path
from botc.roles import (WAKE, WAKE_PATTERNS, TOWNSFOLK, OUTSIDERS,  # noqa: E402
                        is_evil, wake_fits)
from botc.worlds import _candidates               # noqa: E402

# What each statement should leave standing among the good roles. This is
# the table from the README; if it moves, the README moves with it.
EXPECTED = {
    "never": {"Ravenkeeper", "Virgin", "Slayer", "Soldier", "Mayor",
              "Recluse", "Saint"},
    "first": {"Washerwoman", "Librarian", "Investigator", "Chef"},
    "every": {"Empath", "FortuneTeller", "Undertaker", "Monk", "Butler"},
    "other": {"Undertaker", "Monk"},
    "sometimes": {"Undertaker", "Ravenkeeper"},
}


def good_roles_left(wake, claim=None, certainty=""):
    opts = _candidates(claim, False, certainty, None, wake)
    return {r for r, _b in opts if not is_evil(r) and r != "Drunk"}


class TheTable(SolverTest):

    def test_every_pattern_is_documented(self):
        self.assertEqual(set(EXPECTED), set(WAKE_PATTERNS))

    def test_each_statement_narrows_to_the_documented_roles(self):
        for pattern, expected in EXPECTED.items():
            with self.subTest(said=pattern):
                self.assertEqual(good_roles_left(pattern), expected)

    def test_every_good_role_can_say_something(self):
        for role in TOWNSFOLK + OUTSIDERS:
            if role == "Drunk":
                continue
            with self.subTest(role=role):
                self.assertTrue(WAKE[role], f"{role} has no honest answer")

    def test_the_loose_answer_is_forgiven_and_the_precise_one_is_sharper(self):
        """Monk and Undertaker wake every night after the first. Saying
        plainly "every night" is not a lie, so it must not rule them out."""
        self.assertIn("Monk", good_roles_left("every"))
        self.assertIn("Undertaker", good_roles_left("every"))
        self.assertLess(len(good_roles_left("other")), len(good_roles_left("every")))

    def test_the_ravenkeeper_may_honestly_say_never(self):
        self.assertIn("Ravenkeeper", good_roles_left("never"))
        self.assertIn("Ravenkeeper", good_roles_left("sometimes"))


class WhoIsHeldToIt(SolverTest):

    def test_evil_is_never_held_to_a_wake_claim(self):
        for pattern in WAKE_PATTERNS:
            with self.subTest(said=pattern):
                evil_left = {r for r, _b in _candidates(None, False, "", None, pattern)
                             if is_evil(r)}
                self.assertGreaterEqual(len(evil_left), 5,
                                        "evil says whatever suits the bluff")

    def test_the_drunk_is_judged_on_the_token_they_were_given(self):
        self.assertTrue(wake_fits("Drunk", "Empath", "every"))
        self.assertFalse(wake_fits("Drunk", "Empath", "never"))
        self.assertTrue(wake_fits("Drunk", "Soldier", "never"))

    def test_saying_nothing_constrains_nothing(self):
        self.assertTrue(wake_fits("Imp", None, ""))
        self.assertTrue(wake_fits("Soldier", None, None))

    def test_a_hiding_seat_may_lie_about_waking_too(self):
        """An Outsider covering up fakes the schedule as well as the role."""
        plain = good_roles_left("never", claim="Chef")
        hiding = good_roles_left("never", claim="Chef", certainty="hiding")
        self.assertNotIn("Recluse", plain)
        self.assertIn("Recluse", hiding)


class InPlay(SolverTest):

    CLAIMS = {0: "Washerwoman", 1: "Librarian", 2: "Investigator",
              3: "Chef", 4: "Empath"}

    def test_a_wake_claim_shrinks_the_world_count(self):
        open_ = len(solved(game(7, claims=self.CLAIMS))[0])
        said = len(solved(game(7, claims=self.CLAIMS, wakes={5: "never"}))[0])
        self.assertLess(said, open_)

    def test_the_narrowed_roles_are_what_the_seat_is_guessed_as(self):
        rows = solved(game(7, claims=self.CLAIMS, wakes={5: "every"}))[1]
        for role, pct in rows[5]["roles"]:
            if pct > 1 and not is_evil(role) and role != "Drunk":
                self.assertIn(role, EXPECTED["every"], f"{role} should not fit")

    def test_a_soft_claim_can_be_damning_when_the_honest_roles_are_taken(self):
        """Washerwoman, Librarian, Investigator and Chef are all claimed
        already, so a fifth seat saying "only the first night" has nothing
        honest left to be."""
        loose = solved(game(7, claims=self.CLAIMS, wakes={5: "never"}))[1][5]["evil_pct"]
        taken = solved(game(7, claims=self.CLAIMS, wakes={5: "first"}))[1][5]["evil_pct"]
        self.assertRises(loose, taken)
        self.assertGreater(taken, 40)

    def test_a_wake_claim_that_fights_the_role_claim_convicts_the_seat(self):
        """A Soldier does not wake every night. The seat is not impossible
        — it is evil, bluffing the role and the schedule together."""
        state = game(7, claims={**self.CLAIMS, 5: "Soldier"}, wakes={5: "every"})
        valid, rows = solved(state)
        self.assertTrue(valid, "evil can still tell this story")
        self.assertPct(rows[5]["evil_pct"], 100.0, 0.01)
        self.assertPct(rows[5]["lying_pct"], 100.0, 0.01)


if __name__ == "__main__":
    unittest.main()


class TheNightHasAnOrder(SolverTest):
    """Where each character acts, from `data/roles.json`.

    Two numbers, because the first night is a different order: a
    Washerwoman acts then and never again, and the Demon learning its
    Minions has a slot that later nights do not have.

    Kept un-renumbered on purpose. The gaps are what let a character
    added later drop into its true position without disturbing anything
    around it — and they keep the data checkable against its source.
    """

    def test_the_poisoner_goes_early(self):
        from botc.catalogue import CHARACTERS
        poisoner = CHARACTERS["Poisoner"].other_night
        for later in ("Imp", "Assassin", "Acrobat", "Farmer"):
            with self.subTest(after=later):
                self.assertLess(poisoner, CHARACTERS[later].other_night)

    def test_an_imp_acts_before_an_assassin(self):
        """Which is why a starpass can cost the Assassin its night.

        The Imp kills itself and hands the star to a Minion; if that
        Minion is the Assassin, then by the time the Assassin's slot
        arrives that seat is holding the Imp, and the ability is not
        there to use.
        """
        from botc.catalogue import CHARACTERS
        self.assertLess(CHARACTERS["Imp"].other_night,
                        CHARACTERS["Assassin"].other_night)

    def test_an_acrobat_sits_between_them(self):
        """It can be poisoned before it acts, and its pick can be
        poisoned after — which is what makes "are *or become* droisoned
        tonight" more than a turn of phrase."""
        from botc.catalogue import CHARACTERS
        self.assertLess(CHARACTERS["Poisoner"].other_night,
                        CHARACTERS["Acrobat"].other_night)

    def test_characters_that_act_in_daylight_have_no_slot(self):
        """A Virgin, a Slayer, a Soldier, a Saint: zero is right for
        them, and it is how "does not act at night" is said."""
        from botc.catalogue import CHARACTERS
        for key in ("Virgin", "Slayer", "Soldier", "Saint", "Mayor"):
            with self.subTest(character=key):
                self.assertEqual(CHARACTERS[key].first_night, 0)
                self.assertEqual(CHARACTERS[key].other_night, 0)

    def test_every_modelled_character_that_wakes_has_one(self):
        """If it wakes at night, it acts somewhere — and a character with
        no slot would be silently skipped once the night is ordered."""
        from botc.catalogue import CHARACTERS
        for c in CHARACTERS.values():
            if not c.modelled or c.nights in ("never", "conditional"):
                continue
            if not c.seated:
                continue                  # Fabled sit outside the circle
            with self.subTest(character=c.key):
                self.assertTrue(c.first_night or c.other_night)
