"""The parts that decide whether a world survives at all, and what it
costs to keep it alive.
"""

import unittest

from helpers import SolverTest, game, solved
from botc.info import Empath, Chef, VirginNomination, SlayerShot
from botc.solver import (POISON_HIT_PENALTY, POISON_REPEAT_PENALTY,
                         explanation_cost, forced_roles, night_death_factor,
                         _spent_nominations)
from botc.worlds import World, enumerate_worlds

# Seat 0 Empath, 1 Chef, 2 Poisoner, 3 Imp, 4 Washerwoman.
# The Empath's neighbours (4 and 1) are both good, so any count above 0 is
# false. The Poisoner and Imp sit together, so the Chef's honest answer is 1.
ROLES = ["Empath", "Chef", "Poisoner", "Imp", "Washerwoman"]
CLAIMS = {i: r for i, r in enumerate(ROLES)}
WORLD = World(tuple(ROLES), (None,) * 5)


def cost(infos, deaths=None, w=WORLD, claims=None):
    state = game(5, claims=CLAIMS if claims is None else claims,
                 deaths=deaths or {}, infos=infos)
    return explanation_cost(w, state)


class PoisonAccounting(SolverTest):

    def test_a_world_where_everything_holds_costs_nothing(self):
        self.assertEqual(cost([Empath(1, 0, count=0), Chef(1, 1, count=1)]), 1.0)

    def test_one_contradiction_a_night_is_the_poisoner(self):
        self.assertPct(cost([Empath(1, 0, count=2)]), POISON_HIT_PENALTY, 1e-9)

    def test_two_contradictions_in_one_night_is_impossible(self):
        self.assertIsNone(cost([Empath(1, 0, count=2), Chef(1, 1, count=0)]))

    def test_the_same_target_two_nights_running_is_cheaper(self):
        same = cost([Empath(1, 0, count=2), Empath(2, 0, count=2)])
        apart = cost([Empath(1, 0, count=2), Chef(2, 1, count=0)])
        self.assertPct(same, POISON_HIT_PENALTY * POISON_REPEAT_PENALTY, 1e-9)
        self.assertPct(apart, POISON_HIT_PENALTY ** 2, 1e-9)
        self.assertGreater(same, apart, "sticking to one target should cost less")

    def test_no_poisoner_means_no_excuse(self):
        clean = World(("Empath", "Chef", "Baron", "Imp", "Washerwoman"), (None,) * 5)
        self.assertIsNone(cost([Empath(1, 0, count=2)], w=clean))

    def test_a_dead_poisoner_cannot_poison(self):
        self.assertIsNone(cost([Empath(3, 0, count=2)], deaths={2: "E1"}))
        self.assertIsNotNone(cost([Empath(3, 0, count=2)], deaths={2: "E3"}))


class DeathsConstrain(SolverTest):

    def test_the_demon_kills_once_a_night(self):
        self.assertIsNone(cost([], deaths={0: "N2", 1: "N2"}))
        self.assertIsNotNone(cost([], deaths={0: "N2", 1: "N3"}))

    def test_the_demon_must_still_be_alive_to_kill(self):
        self.assertIsNone(cost([], deaths={3: "E1", 0: "N2"}))

    def test_a_sober_soldier_cannot_be_the_victim(self):
        soldier = World(("Soldier", "Chef", "Poisoner", "Imp", "Washerwoman"),
                        (None,) * 5)
        claims = {**CLAIMS, 0: "Soldier"}
        # Only a poisoned Soldier dies here, so the world pays for the hit.
        self.assertPct(cost([], deaths={0: "N2"}, w=soldier, claims=claims),
                       POISON_HIT_PENALTY, 1e-9)

    def test_a_starpass_needs_a_minion_to_catch_it(self):
        self.assertIsNotNone(cost([], deaths={3: "N2"}))
        alone = World(("Empath", "Chef", "Undertaker", "Imp", "Washerwoman"),
                      (None,) * 5)
        self.assertIsNone(cost([], deaths={3: "N2"}, w=alone,
                               claims={0: "Empath", 3: "Imp"}))

    def test_an_executed_saint_needs_something_to_have_stopped_them(self):
        """It ends the game while it is *working*. There is a Poisoner in
        this world, so an executed Saint costs an excuse rather than being
        impossible — and a Saint that died in daylight without being
        executed costs nothing, because that was never their condition."""
        saint = World(("Saint", "Chef", "Poisoner", "Imp", "Washerwoman"),
                      (None,) * 5)
        claims = {**CLAIMS, 0: "Saint"}
        executed = cost([], deaths={0: "E1"}, w=saint, claims=claims)
        self.assertIsNotNone(executed)
        self.assertLess(executed, 1.0)
        self.assertPct(cost([], deaths={0: "D1"}, w=saint, claims=claims),
                       1.0, 1e-9)

    def test_with_nothing_able_to_stop_them_it_is_still_impossible(self):
        saint = World(("Saint", "Chef", "Baron", "Imp", "Washerwoman"),
                      (None,) * 5)
        claims = {**CLAIMS, 0: "Saint"}
        self.assertIsNone(cost([], deaths={0: "E1"}, w=saint, claims=claims))

    def test_the_night_discount_starts_at_night_two(self):
        self.assertPct(night_death_factor(2), 0.05, 1e-9)
        self.assertPct(night_death_factor(3), 0.10, 1e-9)
        self.assertGreater(night_death_factor(5), night_death_factor(3))
        self.assertEqual(night_death_factor(50), 1.0)


class WitnessedEventsPrune(SolverTest):

    def test_a_virgin_trigger_pins_both_seats_before_the_search(self):
        state = game(9, infos=[VirginNomination(1, 4, nominator=2, triggered=True)],
                     deaths={2: "E1"})
        pinned = forced_roles(state)
        self.assertEqual(pinned[4], frozenset({"Virgin"}))
        self.assertIn("Spy", pinned[2])
        self.assertNotIn("Imp", pinned[2])

    def test_a_landed_slayer_shot_pins_shooter_and_target(self):
        state = game(9, infos=[SlayerShot(2, 4, target=2, died=True)])
        pinned = forced_roles(state)
        self.assertEqual(pinned[4], frozenset({"Slayer"}))
        self.assertEqual(pinned[2], frozenset({"Imp", "Recluse"}))

    def test_a_shot_that_missed_pins_nothing(self):
        state = game(9, infos=[SlayerShot(2, 4, target=2, died=False)])
        self.assertEqual(forced_roles(state), {})

    def test_pinning_shrinks_the_search_rather_than_filtering_after(self):
        """The bug this guards: the event gave the right answer but only
        after generating every world it was going to throw away."""
        claims = {i: r for i, r in enumerate(
            ["Washerwoman", "Librarian", "Investigator", "Chef", "Virgin",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"])}
        state = game(9, claims=claims, deaths={2: "E1"},
                     infos=[VirginNomination(1, 4, nominator=2, triggered=True)])
        plain = len(enumerate_worlds(9, claims, max_worlds=10 ** 6))
        pinned = len(enumerate_worlds(9, claims, forced=forced_roles(state),
                                      max_worlds=10 ** 6))
        self.assertLess(pinned, plain)

    def test_the_virgin_only_fires_once(self):
        state = game(9, infos=[
            VirginNomination(1, 4, nominator=0, triggered=False),
            VirginNomination(2, 4, nominator=1, triggered=False),
        ])
        spent = _spent_nominations(state)
        self.assertEqual(spent, {1}, "the later quiet nomination says nothing")

    def test_a_quiet_nomination_moves_suspicion_onto_the_nominator(self):
        # Seat 0 claims Virgin so the row has somewhere to land.
        claims = {i: r for i, r in enumerate(
            ["Virgin", "Washerwoman", "Chef", "Empath", "Monk",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"])}
        base = solved(game(9, claims=claims))[1][2]["evil_pct"]
        after = solved(game(9, claims=claims, infos=[
            VirginNomination(1, 0, nominator=2, triggered=False)]))[1][2]["evil_pct"]
        self.assertRises(base, after)


if __name__ == "__main__":
    unittest.main()
