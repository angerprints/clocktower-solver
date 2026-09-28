"""Drunk and poisoned are one thing, and the sources are a registry.

The effect is identical — an ability that does not work — so the solver
talks about a seat being *impaired* and leaves the cause to whatever is
registered. Trouble Brewing has two sources that look nothing alike: the
Drunk, impaired every night for free because that is simply what they
are, and the Poisoner, impairing one seat a night and having to have
guessed right.

Bad Moon Rising adds four more, and the point of these tests is that it
can, without the solver learning about any of them.
"""

import unittest

from helpers import SolverTest, game, solved      # sets up the import path
from botc import impairment                       # noqa: E402
import botc.solver as S                           # noqa: E402
from botc.impairment import Source, plan_night     # noqa: E402
from botc.info import Chef, Empath                # noqa: E402
from botc.worlds import World                     # noqa: E402

# 0 Empath, 1 Chef, 2 Poisoner, 3 Imp, 4 Monk, 5 Washerwoman, 6 Undertaker
ROLES = ["Empath", "Chef", "Poisoner", "Imp", "Monk", "Washerwoman",
         "Undertaker"]
CLAIMS = {i: r for i, r in enumerate(ROLES)}
WORLD = World(tuple(ROLES), (None,) * 7)


class PlanningOneNight(SolverTest):

    def poisoner(self, reach=range(7)):
        return Source("Poisoner", frozenset(reach), capacity=1,
                      cost=0.35, repeat_cost=0.7)

    def believer(self, seats):
        return Source("believer", frozenset(seats), capacity=len(seats))

    def test_nothing_to_explain_costs_nothing(self):
        self.assertEqual(plan_night([self.poisoner()], [], [], {}), (1.0, {}))

    def test_one_seat_is_the_poisoner_guessing_right(self):
        cost, hits = plan_night([self.poisoner()], [4], [], {})
        self.assertPct(cost, 0.35, 1e-9)
        self.assertEqual(hits, {"Poisoner": 4})

    def test_two_seats_are_beyond_one_source(self):
        self.assertIsNone(plan_night([self.poisoner()], [4, 5], [], {}))

    def test_two_seats_are_fine_with_two_sources(self):
        second = Source("Sailor", frozenset(range(7)), capacity=1, cost=0.5)
        got = plan_night([self.poisoner(), second], [4, 5], [], {})
        self.assertIsNotNone(got, "one each")
        self.assertPct(got[0], 0.35 * 0.5, 1e-9)

    def test_a_source_that_cannot_reach_is_no_help(self):
        short = self.poisoner(reach=[0, 1])
        self.assertIsNone(plan_night([short], [4], [], {}))

    def test_sticking_to_a_target_is_cheaper(self):
        fresh = plan_night([self.poisoner()], [4], [], {})[0]
        again = plan_night([self.poisoner()], [4], [], {"Poisoner": 4})[0]
        self.assertGreater(again, fresh)
        self.assertPct(again, 0.7, 1e-9)

    def test_a_free_source_covers_a_seat_for_nothing(self):
        """Being the Drunk is not a piece of luck."""
        cost, hits = plan_night([self.poisoner(), self.believer([4])],
                                [4], [], {})
        self.assertPct(cost, 1.0, 1e-9)
        self.assertEqual(hits, {}, "no guessing was needed")

    def test_a_free_source_it_cannot_avoid_blocks_a_demand(self):
        """A seat that is always impaired cannot also have been working."""
        self.assertIsNone(plan_night([self.believer([4])], [], [4], {}))

    def test_a_seat_cannot_be_working_and_impaired_at_once(self):
        self.assertIsNone(plan_night([self.poisoner()], [4], [4], {}))

    def test_a_demand_to_be_working_costs_nothing_by_itself(self):
        self.assertEqual(plan_night([self.poisoner()], [], [4], {}), (1.0, {}))


class AcrossNights(SolverTest):

    def test_the_same_seat_two_nights_running_is_the_cheaper_story(self):
        same = game(7, claims=CLAIMS, infos=[Empath(1, 0, count=2),
                                             Empath(2, 0, count=2)])
        apart = game(7, claims=CLAIMS, infos=[Empath(1, 0, count=2),
                                              Chef(2, 1, count=4)])
        self.assertGreater(S.explanation_cost(WORLD, same),
                           S.explanation_cost(WORLD, apart))

    def test_two_contradictions_in_one_night_still_needs_two_sources(self):
        both = game(7, claims=CLAIMS, infos=[Empath(1, 0, count=2),
                                             Chef(1, 1, count=4)])
        self.assertIsNone(S.explanation_cost(WORLD, both),
                          "one Poisoner cannot cover two seats")


class AddingASource(SolverTest):
    """A source the solver has never heard of, registered from outside.

    Shaped like the Sailor: every night, one of two seats is impaired and
    even the Sailor does not know which. Nothing in `botc/` changes.
    """

    def sailor_rule(self, seat):
        def sailor(world, state, night):
            reach = frozenset(state.alive_at(f"N{night}"))
            # Either the Sailor or whoever they chose, so hitting the seat
            # the world needs is a coin flip rather than a guess.
            return [Source("Sailor", reach, capacity=1, cost=0.5,
                           repeat_cost=0.5)]
        return sailor

    def setUp(self):
        self.rule = self.sailor_rule(4)
        impairment.SOURCE_RULES.append(self.rule)

    def tearDown(self):
        impairment.SOURCE_RULES.remove(self.rule)

    def test_it_covers_what_the_poisoner_could_not(self):
        """Two contradictions in one night is impossible on Trouble
        Brewing and ordinary once a second source is in play."""
        both = game(7, claims=CLAIMS, infos=[Empath(1, 0, count=2),
                                             Chef(1, 1, count=4)])
        self.assertIsNotNone(S.explanation_cost(WORLD, both))

    def test_the_solver_needed_no_changes_to_accept_it(self):
        self.assertIn(self.rule, impairment.SOURCE_RULES)

    def test_removing_it_puts_things_back(self):
        impairment.SOURCE_RULES.remove(self.rule)
        try:
            both = game(7, claims=CLAIMS, infos=[Empath(1, 0, count=2),
                                                 Chef(1, 1, count=4)])
            self.assertIsNone(S.explanation_cost(WORLD, both))
        finally:
            impairment.SOURCE_RULES.append(self.rule)


class TheCostsStillTune(SolverTest):
    """The Poisoner's source reads the solver's constants late, so the
    sensitivity pass still moves it."""

    def test_changing_the_constant_changes_the_plan(self):
        state = game(7, claims=CLAIMS, infos=[Empath(1, 0, count=2)])
        before = S.explanation_cost(WORLD, state)
        original = S.POISON_HIT_PENALTY
        S.POISON_HIT_PENALTY = 0.9
        try:
            after = S.explanation_cost(WORLD, state)
        finally:
            S.POISON_HIT_PENALTY = original
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()


class WhatKilledThem(SolverTest):
    """A death is attributed to a cause, not merely counted.

    Trouble Brewing kills at night one way, so "died at night" and "died
    by the Demon" were the same sentence and never had to be told apart.
    They are not the same sentence: a Soldier cannot be killed by the
    Demon and can be killed by a Gossip or an Assassin without trouble.
    """

    def board(self, **kw):
        roles = ["Empath", "Soldier", "Poisoner", "Imp", "Monk",
                 "Washerwoman", "Undertaker"]
        return (World(tuple(roles), (None,) * 7),
                game(7, claims={i: r for i, r in enumerate(roles)}, **kw))

    def gossip_rule(self, seat):
        """Shaped like a Gossip: kills once, and not as the Demon."""
        from botc import deaths

        def gossip(world, state, night):
            return [deaths.Cause(name="Gossip", kind=deaths.OTHER,
                                 seats=frozenset(state.alive_set(f"N{night}")),
                                 capacity=1, cost=0.5, must_fire=False)]
        return gossip

    # ------------------------------------------------------------------
    def test_a_soldier_killed_at_night_must_have_been_impaired(self):
        world, state = self.board(deaths={1: "N2"})
        self.assertPct(S.explanation_cost(world, state),
                       S.POISON_HIT_PENALTY, 1e-9,
                       "only the Demon can have done it, so it was poisoned")

    def test_a_second_cause_lets_the_soldier_die_intact(self):
        from botc import deaths
        rule = self.gossip_rule(0)
        deaths.CAUSE_RULES.append(rule)
        try:
            world, state = self.board(deaths={1: "N2"})
            self.assertGreater(S.explanation_cost(world, state),
                               S.POISON_HIT_PENALTY,
                               "a Gossip kills a Soldier without impairing it")
        finally:
            deaths.CAUSE_RULES.remove(rule)

    def test_two_deaths_in_one_night_need_two_causes(self):
        from botc import deaths
        world, state = self.board(deaths={0: "N2", 5: "N2"})
        self.assertIsNone(S.explanation_cost(world, state))
        rule = self.gossip_rule(0)
        deaths.CAUSE_RULES.append(rule)
        try:
            self.assertIsNotNone(S.explanation_cost(world, state))
        finally:
            deaths.CAUSE_RULES.remove(rule)

    def test_a_cause_that_need_not_fire_owes_a_quiet_night_nothing(self):
        """The Demon kills every night, so a quiet one means it was
        stopped. A Gossip only kills when it said something true."""
        from botc import deaths
        rule = self.gossip_rule(0)
        deaths.CAUSE_RULES.append(rule)
        try:
            world, state = self.board(quiet_nights={2})
            self.assertIsNotNone(S.explanation_cost(world, state),
                                 "the Monk explains it; the Gossip is silent")
        finally:
            deaths.CAUSE_RULES.remove(rule)

    def test_a_guard_that_has_to_be_aimed_implies_nothing_about_a_death(self):
        """The Monk picks one player a night, so somebody dying only ever
        means it guarded somebody else. Reading it otherwise made every
        death demand an impaired Monk."""
        world, state = self.board(deaths={5: "N2"})
        self.assertPct(S.explanation_cost(world, state), 1.0, 1e-9)

    def test_a_guard_that_is_always_there_does_imply_something(self):
        """Unlike the Soldier, which is safe whether anybody likes it."""
        world, state = self.board(deaths={1: "N2"})
        self.assertLess(S.explanation_cost(world, state), 1.0)


class OneDeathDraggingAnother(SolverTest):
    """A death that follows from another one, and the deduction it gives.

    Shaped like the Grandmother, whose grandchild is not a character
    anybody holds but a token the Storyteller put on a seat. So the rule
    reads the board rather than the roles — here, a marker passed in
    directly — and only fires for a Demon kill, because a grandchild
    taken by a Gossip leaves her standing.

    Seats: 0 Grandmother-ish, 1 Chef, 2 Poisoner, 3 Imp, 4 Monk,
    5 Washerwoman, 6 Undertaker. The marker sits on seat 5.
    """

    ROLES = ["Empath", "Chef", "Poisoner", "Imp", "Monk", "Washerwoman",
             "Undertaker"]
    CLAIMS = {i: r for i, r in enumerate(ROLES)}
    GRIEVER, GRANDCHILD = 0, 5

    def world(self):
        return World(tuple(self.ROLES), (None,) * 7)

    def rule(self):
        from botc import deaths

        def grief(world, state, night, victim, kind):
            if kind != deaths.DEMON or victim != self.GRANDCHILD:
                return []
            if world.role_at(self.GRIEVER, f"N{night}") != "Empath":
                return []
            return [deaths.Implication(seat=self.GRIEVER,
                                       needs=self.GRIEVER)]
        return grief

    def setUp(self):
        from botc import deaths
        self.registered = self.rule()
        deaths.IMPLICATION_RULES.append(self.registered)

    def tearDown(self):
        from botc import deaths
        deaths.IMPLICATION_RULES.remove(self.registered)

    def board(self, **kw):
        return game(7, claims=self.CLAIMS, **kw)

    # ------------------------------------------------------------------
    def test_two_bodies_can_come_from_one_kill(self):
        """Without this they would need two causes, and Trouble Brewing
        has one — so the world would be thrown away."""
        state = self.board(deaths={self.GRANDCHILD: "N2", self.GRIEVER: "N2"})
        self.assertIsNotNone(S.explanation_cost(self.world(), state))

    def test_two_unrelated_bodies_still_need_two_causes(self):
        state = self.board(deaths={1: "N2", 6: "N2"})
        self.assertIsNone(S.explanation_cost(self.world(), state))

    def test_the_griever_left_standing_means_something(self):
        """This is the deduction, and it runs the other way: the
        grandchild died to the Demon and she did not, so she was not
        working — which costs, because somebody had to have impaired her."""
        alone = self.board(deaths={self.GRANDCHILD: "N2"})
        cost = S.explanation_cost(self.world(), alone)
        self.assertIsNotNone(cost)
        self.assertLess(cost, 1.0, "she had to have been poisoned")

    def test_with_nothing_to_impair_her_the_world_goes(self):
        no_poisoner = ["Empath", "Chef", "Undertaker", "Imp", "Monk",
                       "Washerwoman", "Slayer"]
        state = game(7, claims={i: r for i, r in enumerate(no_poisoner)},
                     deaths={self.GRANDCHILD: "N2"})
        self.assertIsNone(S.explanation_cost(World(tuple(no_poisoner),
                                                   (None,) * 7), state))

    def test_it_only_follows_a_demon_kill(self):
        """A grandchild taken by anything else leaves her standing, and
        that is exactly why the kind of death had to be recorded."""
        from botc import deaths
        def gossip(world, state, night):
            return [deaths.Cause(name="Gossip", kind=deaths.OTHER,
                                 seats=frozenset(state.alive_set(f"N{night}")),
                                 capacity=1, cost=0.5)]
        deaths.CAUSE_RULES.append(gossip)
        try:
            state = self.board(deaths={self.GRANDCHILD: "N2"})
            self.assertPct(S.explanation_cost(self.world(), state), 0.5, 1e-9,
                           "the Gossip did it, and she grieves nobody")
        finally:
            deaths.CAUSE_RULES.remove(gossip)

    def test_the_dragged_death_consumes_no_cause_of_its_own(self):
        """Which is the whole point: one aim, two bodies."""
        both = self.board(deaths={self.GRANDCHILD: "N2", self.GRIEVER: "N2"})
        one = self.board(deaths={self.GRANDCHILD: "N2", self.GRIEVER: "N3"})
        self.assertIsNotNone(S.explanation_cost(self.world(), both))
        self.assertIsNotNone(S.explanation_cost(self.world(), one),
                             "on separate nights each has its own")
