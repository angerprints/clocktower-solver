"""Adding a character the solver has never heard of.

Trouble Brewing only ever moves the Demon between evil seats, so nothing
in it exercises the two things step 7 was for: a change that crosses
alignment, and a rule the core does not know about. This registers one
from outside and checks it works all the way through — into the world
search, into the Empath's arithmetic, and into the report.

The character is the **Fang Gu**, from Bad Moon Rising. When it attacks an
Outsider, the Outsider becomes the Fang Gu and the original dies instead.
It is a good test because it is almost the starpass — same trigger, a
Demon dead at night — but the star lands on a *good* seat, who turns evil
holding it. If the machinery only understood evil-to-evil handovers, this
would not fit.

Nothing here changes `botc/`. The rule is registered in setUp and removed
again afterwards.
"""

import unittest

from helpers import SolverTest, game                 # sets up the import path
import botc.solver as S                              # noqa: E402
from botc.info import Empath                         # noqa: E402
from botc.roles import EVIL, GOOD, TEAM              # noqa: E402
from botc.worlds import Change, Timeline, World      # noqa: E402


def fang_gu_conversion(view, state, phase, character):
    """An Outsider takes the Demon and turns evil doing it."""
    if phase[0].upper() != "N":
        return []
    alive = set(state.alive_at(phase))
    return [Change(phase, seat, character, EVIL)
            for seat in range(state.n_players)
            if seat in alive
            and view.team_at(seat, phase) == "outsider"
            and not view.evil_at(seat, phase)]


# Seats: 0 Empath, 1 Recluse, 2 Imp, 3 Chef, 4 Undertaker, 5 Slayer, 6 Monk.
# No Minion anywhere, so nothing in Trouble Brewing can catch the star.
ROLES = ["Empath", "Recluse", "Imp", "Chef", "Undertaker", "Slayer", "Monk"]
CLAIMS = {i: r for i, r in enumerate(ROLES)}


class AnUnknownCharacter(SolverTest):

    def setUp(self):
        S.HEIR_RULES.append(fang_gu_conversion)

    def tearDown(self):
        S.HEIR_RULES.remove(fang_gu_conversion)

    def world(self):
        return World(tuple(ROLES), (None,) * 7)

    def stories(self, **kw):
        return S.demon_lineages(self.world(), game(7, claims=CLAIMS, **kw))

    # ------------------------------------------------------------------
    def test_without_the_rule_there_is_nobody_to_take_it(self):
        S.HEIR_RULES.remove(fang_gu_conversion)
        try:
            self.assertEqual(self.stories(deaths={2: "N2"}), [],
                             "no Minion, so the game ended there")
        finally:
            S.HEIR_RULES.append(fang_gu_conversion)

    def test_with_it_the_outsider_inherits(self):
        got = self.stories(deaths={2: "N2"})
        self.assertEqual(len(got), 1)
        [(change,)] = got
        self.assertEqual((change.seat, change.role, change.side),
                         (1, "Imp", EVIL))

    def test_the_seat_changes_side_as_well_as_character(self):
        view = Timeline(self.world(), (Change("N2", 1, "Imp", EVIL),))
        self.assertEqual(view.alignment_at(1, "N1"), GOOD)
        self.assertEqual(view.alignment_at(1, "N2"), EVIL)
        self.assertEqual(view.role_at(1, "N1"), "Recluse")
        self.assertEqual(view.role_at(1, "N2"), "Imp")
        self.assertEqual(view.demon_at("N2"), 1)

    def test_a_change_can_move_the_side_without_the_character(self):
        """The other half of the record, which an Ogre or a Politician
        would use. Nothing in Trouble Brewing does, so it is checked
        here rather than left untested."""
        view = Timeline(self.world(), (Change("N2", 3, None, EVIL),))
        self.assertEqual(view.role_at(3, "N2"), "Chef", "same character")
        self.assertTrue(view.evil_at(3, "N2"), "other side")
        self.assertFalse(view.evil_at(3, "N1"))

    # ------------------------------------------------------------------
    def test_the_empath_counts_the_conversion(self):
        """The real test of the alignment seam: a change of side has to
        reach the arithmetic, not just the bookkeeping.

        Seat 0's neighbours are 1 and 6. Before the conversion seat 1 is
        the Recluse — good, though it may register either way. Afterwards
        it is an evil Demon, and no longer ambiguous.
        """
        plain = self.world()
        turned = Timeline(plain, (Change("N2", 1, "Imp", EVIL),))
        state = game(7, claims=CLAIMS, deaths={2: "N2"})

        before = Empath(1, 0, count=0).holds(plain, state, None, 0)
        after_zero = Empath(2, 0, count=0).holds(turned, state, None, 0)
        after_one = Empath(2, 0, count=1).holds(turned, state, None, 0)

        self.assertTrue(before, "a Recluse may read good")
        self.assertFalse(after_zero, "a Demon may not")
        self.assertTrue(after_one)

    def test_the_solver_finds_the_world_end_to_end(self):
        """With the conversion available, a table with no Minion at all
        can still have lost its Demon at night and carried on."""
        state = game(7, claims=CLAIMS, deaths={2: "N2"},
                     infos=[Empath(3, 0, count=1)])
        cost, changes = S.best_story(self.world(), state)
        self.assertIsNotNone(cost, "the conversion explains it")
        self.assertEqual(changes[0].seat, 1)
        self.assertEqual(changes[0].side, EVIL)

    def test_the_report_names_the_new_demon(self):
        """Who holds it now, not who was dealt it."""
        state = game(7, claims=CLAIMS, deaths={2: "N2"})
        _cost, changes = S.best_story(self.world(), state)
        view = Timeline(self.world(), changes)
        now = state.final_phase()
        self.assertEqual(view.demon_at(now), 1)
        self.assertTrue(view.evil_at(1, now))
        self.assertEqual(TEAM[view.role_at(1, now)], "demon")

    def test_the_core_is_unchanged_when_the_rule_goes_away(self):
        S.HEIR_RULES.remove(fang_gu_conversion)
        try:
            # Three built in now: a Minion catching the Imp's star, the
            # Scarlet Woman stepping up, and the Fang Gu jumping into an
            # Outsider.
            self.assertEqual(len(S.HEIR_RULES), 3, "the built-in ways")
            self.assertEqual(self.stories(deaths={2: "N2"}), [])
        finally:
            S.HEIR_RULES.append(fang_gu_conversion)


class TheRulesAreAnchored(SolverTest):
    """Why rules key off recorded events, and what that costs.

    A rule that could fire on any night for no reason would multiply the
    search by seats times nights, generating stories nothing is asking
    for. Every rule here hangs off something on the record — a death, an
    execution — so most worlds produce exactly one story and cost
    nothing extra.
    """

    def test_a_world_with_nothing_to_explain_has_one_story(self):
        plain = World(("Empath", "Chef", "Imp", "Poisoner", "Washerwoman"),
                      (None,) * 5)
        state = game(5, claims={i: r for i, r in enumerate(plain.roles)})
        self.assertEqual(S.possible_timelines(plain, state), [((), 1.0)])

    def test_the_search_is_capped(self):
        """Not a safety net that should ever fire on this script — but a
        script with several rules could otherwise run away."""
        plain = World(("Empath", "Chef", "Imp", "Poisoner", "Washerwoman"),
                      (None,) * 5)
        state = game(5, claims={i: r for i, r in enumerate(plain.roles)})
        self.assertLessEqual(len(S.possible_timelines(plain, state, cap=1)), 1)


if __name__ == "__main__":
    unittest.main()
