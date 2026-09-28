"""The three seams that have to exist before characters can change hands.

None of these change an answer today. They are here so that the parts of
the solver which depend on *when* they are asking say so out loud, and so
that the parts which depend on the shape of the bag read it from data
rather than from a hardcoded branch. Each test states what the seam has to
keep true once transitions land.
"""

import unittest

from helpers import SolverTest, spread              # sets up the import path
from botc.catalogue import CHARACTERS, Character  # noqa: E402
from botc.roles import ABSENT, ARBITRARY, GENUINE, SETUP, ability_state  # noqa: E402
from botc.scripts import TROUBLE_BREWING, Script  # noqa: E402
from botc.worlds import World, _bags, enumerate_worlds  # noqa: E402


class AskingAboutAMoment(SolverTest):
    """5a. Every question about a character now carries a phase."""

    WORLD = World(("Empath", "Drunk", "Imp", "Chef", "Poisoner"),
                  (None, "Chef", None, None, None))

    def test_a_world_answers_the_same_at_every_phase_for_now(self):
        for phase in ("N1", "E1", "N2", "D3", "N9"):
            with self.subTest(phase=phase):
                self.assertEqual(self.WORLD.role_at(2, phase), "Imp")
                self.assertEqual(self.WORLD.demon_at(phase), 2)
                self.assertEqual(self.WORLD.find_at("Poisoner", phase), 4)
                self.assertEqual(self.WORLD.team_at(4, phase), "minion")

    def test_the_demon_is_found_by_team_not_by_name(self):
        """So a script whose Demon is not the Imp needs no change here."""
        self.assertEqual(self.WORLD.demon_at("N1"), 2)
        no_demon = World(("Empath", "Chef", "Poisoner"), (None,) * 3)
        self.assertIsNone(no_demon.demon_at("N1"))

    def test_the_drunk_is_still_the_drunk_not_their_token(self):
        self.assertEqual(self.WORLD.role_at(1, "N1"), "Drunk")
        self.assertEqual(self.WORLD.believes[1], "Chef")


class HowMuchAnAbilityIsWorth(SolverTest):
    """5b. Three-valued, because "sober and healthy" stops being a
    yes-or-no question the moment a script can invert information."""

    WORLD = World(("Empath", "Drunk", "Imp", "Chef", "Poisoner"),
                  (None, "Chef", None, None, None))

    def test_holding_the_character_means_the_answer_has_to_be_true(self):
        self.assertIs(ability_state(self.WORLD, 0, "Empath", "N1"), GENUINE)
        self.assertIs(ability_state(self.WORLD, 3, "Chef", "N1"), GENUINE)

    def test_the_drunk_is_running_but_making_it_up(self):
        """Not ABSENT: the Storyteller woke them on the Chef's schedule
        and handed them a Chef-shaped answer. There is simply nothing to
        check against."""
        self.assertIs(ability_state(self.WORLD, 1, "Chef", "N1"), ARBITRARY)

    def test_somebody_else_entirely_is_absent(self):
        self.assertIs(ability_state(self.WORLD, 0, "Monk", "N1"), ABSENT)
        self.assertIs(ability_state(self.WORLD, 1, "Empath", "N1"), ABSENT)

    def test_arbitrary_and_absent_are_not_the_same_answer(self):
        """The solver treats them differently — one is a source that
        produced nothing checkable, the other is no source at all, and
        only the second means somebody invented the information."""
        self.assertIsNot(ARBITRARY, ABSENT)
        self.assertIsNot(ARBITRARY, GENUINE)


class WhatIsInTheBag(SolverTest):
    """5c. The distribution is read from data, not from an if-statement."""

    def test_trouble_brewing_has_exactly_two_bags(self):
        for n in (5, 9, 12, 15):
            with self.subTest(players=n):
                bags = _bags(n, TROUBLE_BREWING)
                self.assertEqual(len(bags), 2)
                plain = next(c for p, c in bags if not p)
                baron = next(c for p, c in bags if "Baron" in p)
                tf, out, mi, de = SETUP[n]
                self.assertEqual((plain["townsfolk"], plain["outsider"]), (tf, out))
                self.assertEqual((baron["townsfolk"], baron["outsider"]),
                                 (tf - 2, out + 2))

    def test_the_outsider_count_never_falls_below_the_base(self):
        for n in range(5, 16):
            base = SETUP[n][1]
            for _present, counts in _bags(n, TROUBLE_BREWING):
                self.assertGreaterEqual(counts["outsider"], base)

    def test_a_bag_that_cannot_exist_is_dropped(self):
        """Nine seats plus a Baron wants four Outsiders, which is every
        Outsider there is. A fifth would be impossible."""
        for _present, counts in _bags(9, TROUBLE_BREWING):
            self.assertLessEqual(counts["outsider"], 4)

    def test_a_modifier_is_only_dealt_in_its_own_bag(self):
        claims = spread(9)
        for world in enumerate_worlds(9, claims, max_worlds=5000):
            outsiders = sum(1 for r in world.roles
                            if r in ("Butler", "Drunk", "Recluse", "Saint"))
            self.assertEqual("Baron" in world.roles,
                             outsiders == SETUP[9][1] + 2)

    GODFATHER = Character(
        key="Godfather", id="godfather", name="Godfather", team="minion",
        wake=frozenset({"first", "every"}),
        setup=({"townsfolk": -1, "outsider": 1},
               {"townsfolk": 1, "outsider": -1}))

    def test_adding_a_modifier_grows_the_search_on_its_own(self):
        """The point of the seam: a new setup-changing character is a
        catalogue entry on a script, not a code change. The Godfather is
        +1 or -1 Outsider, so it doubles the bags it appears in — and the
        combination that would need five Outsiders is dropped."""
        # Put back exactly as found rather than deleted. This said
        # `del` once, written when no Godfather existed — and it has been
        # quietly removing the real one from the live catalogue ever
        # since Bad Moon Rising arrived. Nothing noticed until a script
        # that is built at import time went looking for a character a
        # later test had taken away.
        before = len(_bags(9, TROUBLE_BREWING))
        was = CHARACTERS.get("Godfather")
        CHARACTERS["Godfather"] = self.GODFATHER
        try:
            wider = Script("Trouble Brewing plus one",
                           TROUBLE_BREWING.keys + ("Godfather",))
            grown = _bags(9, wider)
            shapes = {(c["townsfolk"], c["outsider"]) for _p, c in grown}
            self.assertGreater(len(grown), before)
            self.assertIn((4, 3), shapes, "Baron and Godfather together")
            self.assertIn((6, 1), shapes, "the Godfather going the other way")
            self.assertNotIn((2, 5), shapes, "there is no fifth Outsider")
        finally:
            if was is None:
                del CHARACTERS["Godfather"]
            else:
                CHARACTERS["Godfather"] = was

    def test_a_script_without_it_is_unaffected(self):
        self.assertEqual(set(TROUBLE_BREWING.setup_modifiers), {"Baron"})
        self.assertEqual(len(_bags(9, TROUBLE_BREWING)), 2)


if __name__ == "__main__":
    unittest.main()
