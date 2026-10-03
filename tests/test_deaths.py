"""What happens when the Demon dies, and what a quiet night proves."""

import unittest

from helpers import SolverTest, game, role_pct, solved  # sets up the import path
from botc.solver import (explanation_cost, scarlet_woman_takes_over,  # noqa: E402
                         starpass_heirs, in_play, world_weight,
                         _night_accounts)
from botc.worlds import World                      # noqa: E402
from botc.solver import (DEMON_POISONED_PENALTY,     # noqa: E402
                         POISON_HIT_PENALTY)

# What is left of a quiet night when nothing guards and nothing lies dead:
# a Poisoner that hit its own Demon, which a poisoned Imp's kill does not
# survive. Legal and rare — settled at the table. Before the engine found
# it this explanation did not exist, and every such board was impossible.
ONLY_POISON = POISON_HIT_PENALTY * DEMON_POISONED_PENALTY
# How sure a quiet night makes the table of its protector, now that the
# Demon may have been poisoned instead: near proof rather than proof.
NEAR_PROOF = 99.0

TWELVE = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
          "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Slayer",
          "Recluse", "Saint"]


def twelve(**kw):
    return game(12, claims={i: r for i, r in enumerate(TWELVE)}, **kw)


def share(state, role):
    """How much of the weight has this role on the board at all."""
    valid, _rows = solved(state)
    total = sum(world_weight(w, state) for w in valid)
    hit = sum(world_weight(w, state) for w in valid if in_play(w, role))
    return 100 * hit / total if total else 0.0


class WhoTakesTheStar(SolverTest):
    """Seats: 0 Empath, 1 Chef, 2 ScarletWoman, 3 Imp, 4 Poisoner,
    5 Washerwoman, 6 Monk."""

    ROLES = ["Empath", "Chef", "ScarletWoman", "Imp", "Poisoner",
             "Washerwoman", "Monk"]
    CLAIMS = {i: r for i, r in enumerate(ROLES)}

    def world(self, roles=None):
        roles = roles or self.ROLES
        return World(tuple(roles), (None,) * 7)

    def test_she_takes_priority_over_any_other_minion(self):
        state = game(7, claims=self.CLAIMS)
        heirs = starpass_heirs(self.world(), state, "N2")
        self.assertEqual(heirs, [2], "the Scarlet Woman leaves no choice")

    def test_below_five_alive_she_is_just_another_minion(self):
        state = game(7, claims=self.CLAIMS,
                     deaths={0: "N2", 1: "E1", 5: "N3"})
        self.assertFalse(scarlet_woman_takes_over(self.world(), state, "N4"))
        self.assertEqual(sorted(starpass_heirs(self.world(), state, "N4")), [2, 4])

    def test_without_her_the_storyteller_picks_any_living_minion(self):
        roles = list(self.ROLES)
        roles[2] = "Baron"
        state = game(7, claims={**self.CLAIMS, 2: "Baron"})
        self.assertEqual(sorted(starpass_heirs(self.world(roles), state, "N2")),
                         [2, 4])

    def test_a_starpass_needs_somebody_to_catch_it(self):
        alone = ["Empath", "Chef", "Undertaker", "Imp", "Slayer",
                 "Washerwoman", "Monk"]
        state = game(7, claims={i: r for i, r in enumerate(alone)},
                     deaths={3: "N2"})
        self.assertIsNone(explanation_cost(self.world(alone), state))


class DyingInDaylight(SolverTest):
    """A Demon killed in the day ends the game — unless she was there."""

    def test_an_executed_demon_needs_the_scarlet_woman(self):
        with_her = twelve(deaths={2: "E1"})
        valid, rows = solved(with_her)
        self.assertGreater(rows[2]["demon_pct"], 0.0)
        for world in valid:
            if world.roles[2] == "Imp":
                self.assertIn("ScarletWoman", world.roles,
                              "play carried on, so somebody took over")

    def test_with_too_few_alive_an_executed_seat_cannot_have_been_the_demon(self):
        """Her condition is five or more alive when the Demon goes. Below
        that nobody inherits, so good would have won there and then."""
        late = twelve(deaths={1: "E1", 0: "N2", 4: "E2", 3: "N3", 6: "E3",
                              5: "N4", 8: "E4", 7: "N5", 2: "E5"})
        self.assertEqual(len(late.alive_at("E5")), 4)
        _valid, rows = solved(late)
        self.assertPct(rows[2]["demon_pct"], 0.0, 0.01)

    def test_an_executed_demon_keeps_killing_through_its_heir(self):
        """The failure this replaces: the solver used to see the Demon's
        seat dead, decide nothing could have killed later, and throw the
        world away. The Scarlet Woman was doing the killing."""
        state = twelve(deaths={2: "E1", 5: "N2"})
        _valid, rows = solved(state)
        self.assertGreater(rows[2]["demon_pct"], 0.0,
                           "an executed seat can still have started as the Demon")

    def test_executing_somebody_ordinary_still_says_little(self):
        plain = solved(twelve())[1][2]["demon_pct"]
        executed = solved(twelve(deaths={2: "E1"}))[1][2]["demon_pct"]
        self.assertLess(executed, plain, "it narrows, but does not clear")
        self.assertGreater(executed, 0.0)


class NobodyDied(SolverTest):

    def test_a_quiet_night_proves_something_stopped_the_kill(self):
        before = share(twelve(), "Monk")
        after = share(twelve(quiet_nights={2}), "Monk")
        self.assertRises(before, after)
        self.assertGreater(after, NEAR_PROOF,
                           "with no Soldier claimed, only the Monk is left "
                           "— or a Poisoner that hit its own Demon")

    def test_it_clears_the_seat_that_claimed_the_protector(self):
        self.assertLess(solved(twelve(quiet_nights={2}))[1][7]["evil_pct"],
                        100.0 - NEAR_PROOF)

    def test_a_soldier_explains_it_just_as_well(self):
        claims = dict(enumerate(TWELVE))
        claims[7] = "Soldier"
        state = game(12, claims=claims, quiet_nights={2})
        self.assertGreater(share(state, "Soldier"), NEAR_PROOF)

    def test_a_dead_monk_is_no_guard_but_is_a_target(self):
        """Killing the Monk removes the guard and supplies a corpse at the
        same time, so the night is still explainable — just not for free."""
        roles = ["Empath", "Chef", "Poisoner", "Imp", "Monk",
                 "Washerwoman", "Undertaker"]
        claims = {i: r for i, r in enumerate(roles)}
        world = World(tuple(roles), (None,) * 7)

        guarded = explanation_cost(world, game(7, claims=claims, quiet_nights={2}))
        sunk = explanation_cost(world, game(7, claims=claims, quiet_nights={2},
                                            deaths={4: "E1"}))
        self.assertPct(guarded, 1.0, 1e-9, "a living Monk explains it outright")
        self.assertIsNotNone(sunk, "the Demon could aim at the corpse")
        self.assertLess(sunk, guarded, "but that is a deliberate play")

    def test_a_quiet_night_demands_the_guard_was_working(self):
        """It does not name who was impaired — it says who was not.

        The guard is one explanation, so that world is asking that nothing
        stopped it. The other is the Imp itself being poisoned, priced
        rare. That demand goes to the impairment plan,
        which has to satisfy every other night's failures around it.
        """
        roles = ["Empath", "Chef", "Poisoner", "Imp", "Monk",
                 "Washerwoman", "Undertaker"]
        world = World(tuple(roles), (None,) * 7)
        state = game(7, claims={i: r for i, r in enumerate(roles)},
                     quiet_nights={2})
        accounts = _night_accounts(world, state)
        # Two stories, not one. The Monk held — or the Poisoner in this
        # world hit its own Imp, which then killed nobody.
        self.assertEqual(len(accounts), 2)
        guarded = [a for a in accounts if a[2][2] == {4}]
        poisoned = [a for a in accounts if a[1][2] == {3}]
        self.assertEqual(len(guarded), 1, "the Monk, working that night")
        self.assertEqual(len(poisoned), 1, "the Imp, impaired that night")
        self.assertPct(guarded[0][0], 1.0, 1e-9)
        self.assertEqual(guarded[0][1][2], set())
        self.assertAlmostEqual(poisoned[0][0], DEMON_POISONED_PENALTY)

    def test_a_corpse_lets_the_guard_off_the_hook(self):
        """With something to aim at, the world has a free explanation and
        need not insist the guard was working at all."""
        roles = ["Empath", "Chef", "Poisoner", "Imp", "Monk",
                 "Washerwoman", "Undertaker"]
        world = World(tuple(roles), (None,) * 7)
        state = game(7, claims={i: r for i, r in enumerate(roles)},
                     quiet_nights={2}, deaths={5: "E1"})
        accounts = _night_accounts(world, state)
        costs = sorted(c for c, _i, _w in accounts)
        self.assertIn(1.0, costs, "the Monk was still guarding")
        self.assertTrue(any(w[2] == set() for _c, _i, w in accounts),
                        "or the Demon aimed at the corpse instead")

    def test_a_starpass_never_explains_a_quiet_night(self):
        """The Imp killing itself leaves a body. With no protector and no
        corpse to aim at, a starpass explains nothing however many Minions
        were standing by to catch the star — only the Poisoner hitting
        its own Demon is left."""
        roles = ["Empath", "Chef", "ScarletWoman", "Imp", "Poisoner",
                 "Washerwoman", "Undertaker"]
        state = game(7, claims={i: r for i, r in enumerate(roles)},
                     quiet_nights={2})
        self.assertAlmostEqual(
            explanation_cost(World(tuple(roles), (None,) * 7), state),
            ONLY_POISON)


class SinkingTheKill(SolverTest):
    """The Demon may choose a dead player. Nothing happens, the night
    passes empty, and a Demon bluffing Soldier or Monk gets to look
    protected for free."""

    NO_GUARD = ["Empath", "Chef", "Poisoner", "Imp", "Undertaker",
                "Washerwoman", "Librarian"]

    def cost(self, **kw):
        state = game(7, claims={i: r for i, r in enumerate(self.NO_GUARD)}, **kw)
        return explanation_cost(World(tuple(self.NO_GUARD), (None,) * 7), state)

    def test_with_a_corpse_on_the_board_a_quiet_night_is_possible(self):
        self.assertIsNotNone(self.cost(quiet_nights={2}, deaths={5: "E1"}))

    def test_without_one_it_is_not(self):
        self.assertAlmostEqual(self.cost(quiet_nights={2}), ONLY_POISON,
                               msg="nothing to guard with and nothing to "
                                   "aim at, so only the poisoned Demon")

    def test_the_corpse_has_to_predate_the_night(self):
        self.assertAlmostEqual(self.cost(quiet_nights={3}, deaths={5: "N4"}),
                               ONLY_POISON,
                               msg="a death two nights later helps nobody")

    def test_sinking_twice_costs_twice(self):
        once = self.cost(quiet_nights={2}, deaths={5: "E1"})
        twice = self.cost(quiet_nights={2, 3}, deaths={5: "E1"})
        self.assertPct(twice, once * once, 1e-9)

    def test_a_quiet_night_still_favours_a_real_protector(self):
        """It stops being proof once a corpse exists, but it should still
        lean that way — a guard explains the night for nothing."""
        claims = {i: r for i, r in enumerate(TWELVE)}
        with_corpse = game(12, claims=claims, quiet_nights={2},
                           deaths={0: "E1"})
        self.assertBetween(share(with_corpse, "Monk"), 80.0, 99.9)
        clean = game(12, claims=claims, quiet_nights={2})
        self.assertGreater(share(clean, "Monk"), NEAR_PROOF)


class TheMayorNeedsNoRuleOfItsOwn(SolverTest):
    """The bounce can leave a night empty — by landing on a corpse, or on
    the Soldier, or on somebody the Monk guarded. But every one of those
    needs a corpse or a protector that already explains the night by
    itself, so a separate Mayor rule would double-count rather than add
    anything. Written down because it looks as though it should.
    """

    PLAIN = ["Washerwoman", "Soldier", "Chef", "Empath", "Imp",
             "Poisoner", "Undertaker"]
    MAYOR = ["Washerwoman", "Soldier", "Chef", "Mayor", "Imp",
             "Poisoner", "Undertaker"]

    def cost(self, roles, **kw):
        state = game(7, claims={i: r for i, r in enumerate(roles)}, **kw)
        return explanation_cost(World(tuple(roles), (None,) * 7), state)

    def test_a_mayor_does_not_soften_a_dead_soldier(self):
        self.assertEqual(self.cost(self.PLAIN, deaths={1: "N2"}),
                         self.cost(self.MAYOR, deaths={1: "N2"}))

    def test_a_mayor_does_not_allow_two_deaths_in_one_night(self):
        self.assertIsNone(self.cost(self.MAYOR, deaths={0: "N2", 2: "N2"}))

    def test_a_mayor_does_not_explain_a_quiet_night(self):
        no_guard = ["Washerwoman", "Mayor", "Chef", "Empath", "Imp",
                    "Poisoner", "Undertaker"]
        self.assertAlmostEqual(self.cost(no_guard, quiet_nights={2}),
                               ONLY_POISON)


if __name__ == "__main__":
    unittest.main()


class TheLineage(SolverTest):
    """Handovers as an explanation, not as part of the world.

    A world stays one starting assignment. Who holds the Demon over time
    is searched lazily and only when a death forces it — the same shape
    the poison schedule and the red herring already use.
    """

    ROLES = ["Empath", "ScarletWoman", "Imp", "Chef", "Poisoner",
             "Washerwoman", "Monk"]
    CLAIMS = {i: r for i, r in enumerate(ROLES)}

    def world(self):
        return World(tuple(self.ROLES), (None,) * 7)

    def lineages(self, **kw):
        from botc.solver import demon_lineages
        return demon_lineages(self.world(), game(7, claims=self.CLAIMS, **kw))

    def test_a_demon_who_lived_needs_no_story(self):
        self.assertEqual(self.lineages(), [()])

    def test_an_execution_hands_it_to_her_and_nobody_else(self):
        got = self.lineages(deaths={2: "E1"})
        self.assertEqual(len(got), 1, "she takes priority, so no choice")
        [(change,)] = got
        self.assertEqual((change.phase, change.seat, change.role),
                         ("D1", 1, "Imp"),
                         "an execution death is a day death; that it was "
                         "an execution is recorded separately")

    def test_a_starpass_may_have_gone_to_any_living_minion(self):
        """Below five alive her own condition fails, so the Storyteller
        picks — and both stories have to be tried."""
        state = game(7, claims=self.CLAIMS,
                     deaths={3: "E1", 0: "N2", 5: "E3", 2: "N4"})
        self.assertEqual(len(state.alive_at("N4")), 4, "below her threshold")
        from botc.solver import demon_lineages
        heirs = {story[0][1] for story in demon_lineages(self.world(), state)}
        self.assertEqual(heirs, {1, 4}, "either Minion could have caught it")

    def test_the_star_can_move_twice(self):
        chain = self.lineages(deaths={2: "N2", 1: "N3"})
        self.assertTrue(any(len(story) == 2 for story in chain),
                        f"expected a chain, got {chain}")

    def test_a_demon_killed_in_daylight_with_no_heir_ends_the_game(self):
        alone = ["Empath", "Undertaker", "Imp", "Chef", "Slayer",
                 "Washerwoman", "Monk"]
        from botc.solver import demon_lineages
        state = game(7, claims={i: r for i, r in enumerate(alone)},
                     deaths={2: "E1"})
        self.assertEqual(demon_lineages(World(tuple(alone), (None,) * 7),
                                        state), [])

    def test_the_heir_reads_as_the_demon_afterwards(self):
        """What an Undertaker or a Ravenkeeper would learn about them."""
        from botc.worlds import Timeline
        from botc.worlds import Change
        view = Timeline(self.world(), (Change("D1", 1, "Imp"),))
        self.assertEqual(view.role_at(1, "N1"), "ScarletWoman")
        self.assertEqual(view.role_at(1, "N2"), "Imp")
        self.assertEqual(view.demon_at("N1"), 2)
        self.assertEqual(view.demon_at("N2"), 1)

    def test_the_world_underneath_is_untouched(self):
        from botc.worlds import Timeline
        from botc.worlds import Change
        view = Timeline(self.world(), (Change("D1", 1, "Imp"),))
        self.assertEqual(view.roles, tuple(self.ROLES))
        self.assertEqual(view.find("ScarletWoman"), 1)


class ExecutionAndDeathAreSeparate(SolverTest):
    """Two independent facts that used to share one field.

    A player can be executed and live — a Zombuul survives its first, a
    Devil's Advocate can save somebody from theirs. The day still ends.
    Nothing on Trouble Brewing does it, but the board has to be able to
    say it, and the things that key off an execution have to key off the
    right half.
    """

    def board(self, **kw):
        claims = {i: r for i, r in enumerate(TWELVE)}
        return game(12, claims=claims, **kw)

    def test_the_shorthand_still_works(self):
        """`deaths={2: "E1"}` is how most people write it, and how the
        older saved games recorded it."""
        state = self.board(deaths={2: "E1"})
        self.assertEqual(state.died_at(2), ("D1",),
                         "one death, but kept as a tuple — a seat can die "
                         "more than once now")
        self.assertEqual(state.executions[1], 2)
        self.assertEqual(state.execution_death(1), 2)

    def test_an_execution_somebody_walked_away_from(self):
        state = self.board(executions={1: 2})
        self.assertIsNone(state.deaths.get(2), "still standing")
        self.assertEqual(state.executed_on(1), 2)
        self.assertIsNone(state.execution_death(1),
                          "nothing died, so nothing to learn from")

    def test_a_day_death_that_was_not_an_execution(self):
        state = self.board(deaths={2: "D1"})
        self.assertIsNone(state.executed_on(1))
        self.assertIsNone(state.execution_death(1))

    def test_the_saint_only_loses_by_dying_of_it(self):
        """Surviving an execution proves nothing about the Saint, because
        the condition is dying of one.

        Tested on a script where surviving is possible at all: nothing on
        Trouble Brewing walks away from an execution, so a board saying
        somebody did is not a world there.
        """
        from botc.info import GameState
        # A Saint to execute and a Sailor to walk away — no published
        # script has both, so this one does.
        claims = {i: r for i, r in enumerate(
            ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "Undertaker", "Sailor", "Recluse", "Saint"])}
        died = GameState(n_players=9, script=mixed(), claims=claims,
                         deaths={8: "E1"})
        lived = GameState(n_players=9, script=mixed(), claims=claims,
                          executions={1: 6})
        # Not certain, and the reason is the point: a poisoned or drunk
        # Saint is executed and play carries on. It leans hard, because
        # a Poisoner landing on the Saint on exactly the day the town
        # executes them is luckier than the seat simply bluffing — but
        # "leans hard" and "proved" are different claims.
        self.assertGreater(solved(died)[1][8]["evil_pct"], 30.0)
        self.assertLess(solved(died)[1][8]["evil_pct"], 90.0)
        self.assertTrue(solved(lived)[0], "the Sailor explains surviving")
        self.assertLess(solved(lived)[1][8]["evil_pct"], 99.0,
                        "and says nothing about the Saint either way")

    def test_nothing_on_trouble_brewing_survives_an_execution(self):
        """So a board that says somebody did is not a world at all —
        rather than quietly producing numbers about an impossible game."""
        claims = {i: r for i, r in enumerate(TWELVE)}
        self.assertEqual(len(solved(game(12, claims=claims,
                                         executions={1: 11}))[0]), 0)

    def test_the_undertaker_learns_nothing_from_a_survivor(self):
        """Nobody died, so nobody could have learned anything.

        Checked as the mechanical fact rather than by comparing two
        probabilities. On a script with plenty of ways to be drunk, an
        impossible reading is cheap to excuse, and the seat claiming it
        can come out *more* likely on the board where the claim is
        hopeless — because that board constrains everything else less.
        The probability comparison stopped saying what it was written to
        say; this does not.
        """
        from botc.info import GameState, Undertaker
        from botc.worlds import World
        # An Undertaker to learn and a Sailor to survive the hanging.
        roles = ["Washerwoman", "Librarian", "Spy", "Chef", "Empath",
                 "Sailor", "Monk", "Recluse", "Undertaker"]
        claims = {i: r for i, r in enumerate(
            ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "Sailor", "Monk", "Recluse", "Undertaker"])}
        reading = Undertaker(2, 8, target=2, role="Spy")
        killed = GameState(n_players=9, script=mixed(), claims=claims,
                           deaths={2: "E1"})
        spared = GameState(n_players=9, script=mixed(), claims=claims,
                           executions={1: 5})
        world = World(tuple(roles), (None,) * 9)
        self.assertTrue(reading.holds(world, killed, None, 8))
        self.assertFalse(reading.holds(world, spared, None, 8),
                         "no execution death, so no reading to have")

    def test_the_board_refuses_a_reading_nobody_could_have_had(self):
        """The solver treats it as a false statement; the ledger will not
        let it be entered at all."""
        import app
        seats = [{"name": f"P{i+1}", "claim": TWELVE[i],
                  "death": "S1" if i == 2 else "", "certainty": "",
                  "read": 0, "wake": ""} for i in range(12)]
        reply = app.run_solve({"n_players": 12, "players": seats, "infos": [
            {"type": "Undertaker", "night": 2, "player": 6,
             "target": 2, "role": "Spy"}]})
        self.assertIn("error", reply)
        self.assertIn("executed", reply["error"])

    def test_the_undertaker_learns_from_the_one_who_died(self):
        from botc.info import Undertaker
        claims = {i: r for i, r in enumerate(TWELVE)}
        state = game(12, claims=claims, deaths={2: "E1"},
                     infos=[Undertaker(2, 6, target=2, role="Spy")])
        self.assertGreater(len(solved(state)[0]), 0)

    def test_pointing_the_undertaker_elsewhere_is_refused(self):
        """Who the town executed is public, so this is never a lie worth
        modelling — it is a mis-entry, and gets named as one."""
        import app
        seats = [{"name": f"P{i+1}", "claim": TWELVE[i],
                  "death": "X1" if i == 2 else "", "certainty": "",
                  "read": 0, "wake": ""} for i in range(12)]
        reply = app.run_solve({"n_players": 12, "players": seats, "infos": [
            {"type": "Undertaker", "night": 2, "player": 6,
             "target": 5, "role": "Spy"}]})
        self.assertIn("error", reply)
        self.assertIn("seat 3", reply["error"])


# A script for the questions that need characters from both published
# ones at the same time — a Saint that can be executed *and* a Sailor that
# walks away, or a Professor that raises *and* a Spy that registers as a
# Townsfolk while being evil. Neither published script has both halves.
MIXED = None


def mixed():
    global MIXED
    if MIXED is None:
        from botc import scripts
        MIXED = scripts.from_ids("Mixed", [
            "washerwoman", "librarian", "investigator", "chef", "empath",
            "undertaker", "monk", "soldier", "sailor", "professor",
            "recluse", "saint", "drunk", "poisoner", "spy", "baron", "imp"])
    return MIXED


class ComingBack(SolverTest):
    """Death stopped being permanent.

    A Professor raises a dead Townsfolk, and it is not the only character
    that can — nor are they all good. So a seat's life is a run of events
    rather than one death, and "were they standing then" is a question
    about a moment.
    """

    def board(self, **kw):
        claims = {i: r for i, r in enumerate(TWELVE)}
        return game(12, claims=claims, **kw)

    def test_a_seat_can_die_and_come_back(self):
        state = self.board(deaths={3: "N2"}, resurrections={3: "N4"})
        self.assertNotIn(3, state.alive_at("N3"))
        self.assertIn(3, state.alive_at("N4"))
        self.assertIn(3, state.alive_at("N5"))

    def test_and_can_be_killed_again_afterwards(self):
        state = self.board(deaths={3: ("N2", "N6")}, resurrections={3: "N4"})
        standing = [3 in state.alive_at(f"N{n}") for n in range(1, 8)]
        self.assertEqual(standing,
                         [True, True, False, True, True, True, False])

    def test_a_death_still_takes_effect_after_its_own_night(self):
        """Somebody killed on night two was around during night two,
        which is what every check asking "who was there" means."""
        state = self.board(deaths={3: "N2"})
        self.assertIn(3, state.alive_at("N2"))
        self.assertNotIn(3, state.alive_at("N3"))

    def test_a_return_takes_effect_during_its_own_night(self):
        state = self.board(deaths={3: "N2"}, resurrections={3: "N4"})
        self.assertIn(3, state.alive_at("N4"))

    def test_both_deaths_count_as_night_kills(self):
        """Each one needs a cause, so a seat killed twice needs two."""
        from botc.solver import _night_deaths
        state = self.board(deaths={3: ("N2", "N4")}, resurrections={3: "N3"})
        nights = _night_deaths(state)
        self.assertEqual(nights[2], [3])
        self.assertEqual(nights[4], [3])

    def test_coming_back_needs_something_that_can_do_it(self):
        """Nothing on Trouble Brewing raises the dead, so a board saying
        somebody came back is not a world there. The machinery is general;
        the script is what decides whether it can happen."""
        state = self.board(deaths={3: "N2"}, resurrections={3: "N4"})
        self.assertEqual(len(solved(state)[0]), 0)

    def test_and_nothing_assumes_whoever_comes_back_is_good(self):
        from botc.info import GameState
        # A Professor to do the raising and a Spy to be raised — again,
        # no published script has both.
        claims = {i: r for i, r in enumerate(
            ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "Undertaker", "Professor", "Recluse", "Saint"])}
        state = GameState(n_players=9, script=mixed(), claims=claims,
                          deaths={2: "N2"}, resurrections={2: "N4"})
        valid, rows = solved(state)
        self.assertTrue(valid)
        self.assertGreater(rows[2]["evil_pct"], 0.0,
                           "a Spy registers as a Townsfolk and gets raised "
                           "like anybody else")

    def test_the_game_reaches_the_later_moment(self):
        state = self.board(deaths={3: "N2"}, resurrections={3: "N5"})
        self.assertEqual(state.final_phase(), "N5")

    def test_a_board_with_nobody_raised_behaves_exactly_as_before(self):
        plain = self.board(deaths={3: "N2"})
        spelled = self.board(deaths={3: ("N2",)}, resurrections={})
        self.assertEqual([r["evil_pct"] for r in solved(plain)[1]],
                         [r["evil_pct"] for r in solved(spelled)[1]])


class TheMayorSendingAKillElsewhere(SolverTest):
    """A quiet night the Mayor can account for.

    Only the corpse case is modelled, and the reason is worth stating.
    Bouncing a kill onto a *living* player is invisible: "the Demon
    attacked the Mayor and it landed on Cara" and "the Demon attacked
    Cara" leave exactly the same board, and the solver never tracked who
    was aimed at. Bouncing into somebody already dead is different — the
    Demon fired and nobody fell.
    """

    SEATS = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Mayor", "Saint"]

    def board(self, **kw):
        from botc.info import GameState
        from botc import scripts
        return GameState(n_players=9, script=scripts.TROUBLE_BREWING,
                         claims={i: r for i, r in enumerate(self.SEATS)}, **kw)

    def world(self, at_eight="Mayor"):
        from botc.worlds import World
        return World(("Washerwoman", "Librarian", "Investigator", "Chef",
                      "Empath", "FortuneTeller", "Undertaker", at_eight,
                      "Imp"), (None,) * 9)

    def test_it_needs_a_corpse_to_bounce_into(self):
        import botc.solver as S
        from botc import deaths as D
        nobody_gone = self.board(quiet_nights={2})
        self.assertEqual(
            S.a_mayors_death_may_be_moved(self.world(), nobody_gone, 2, 7,
                                          D.DEMON), [])
        somebody_gone = self.board(deaths={4: "N2"}, quiet_nights={3})
        self.assertTrue(
            S.a_mayors_death_may_be_moved(self.world(), somebody_gone, 3, 7,
                                          D.DEMON))

    def test_it_is_offered_to_the_mayor_and_to_nobody_else(self):
        import botc.solver as S
        from botc import deaths as D
        state = self.board(deaths={4: "N2"}, quiet_nights={3})
        self.assertEqual(
            S.a_mayors_death_may_be_moved(self.world(), state, 3, 2,
                                          D.DEMON), [])

    def test_it_stops_the_demon_and_nothing_else(self):
        import botc.solver as S
        from botc import deaths as D
        state = self.board(deaths={4: "N2"}, quiet_nights={3})
        self.assertEqual(
            S.a_mayors_death_may_be_moved(self.world(), state, 3, 7,
                                          D.OTHER), [])

    def test_a_dead_mayor_proves_nothing(self):
        """Aimed rather than always on: the Storyteller chooses whether to
        move the kill, so a Mayor that died at night says nothing about
        whether it was working."""
        import botc.solver as S
        from botc import deaths as D
        state = self.board(deaths={4: "N2"}, quiet_nights={3})
        got = S.a_mayors_death_may_be_moved(self.world(), state, 3, 7,
                                            D.DEMON)
        self.assertTrue(got[0].chosen)

    def test_a_quiet_night_after_a_death_is_free_with_a_real_mayor(self):
        """Without one the Demon has to have aimed at a corpse itself,
        which is a deliberate play and is priced as such."""
        import botc.solver as S
        state = self.board(deaths={4: "N2"}, quiet_nights={3})
        self.assertPct(S.explanation_cost(self.world("Mayor"), state),
                       1.0, 1e-9)
        self.assertLess(S.explanation_cost(self.world("Saint"), state), 1.0)

    def test_so_a_quiet_night_is_evidence_the_mayor_is_real(self):
        import botc.solver as S
        state = self.board(deaths={4: "N2"}, quiet_nights={3})
        rows = S.summarize(S.solve(state)[1], state)
        self.assertEqual(rows[7]["roles"][0][0], "Mayor")
        self.assertGreater(rows[7]["roles"][0][1], 70.0)


class ThePoisonedSaint(SolverTest):
    """Executing the Saint ends the game — while it is *working*.

    A poisoned or drunk Saint is executed and play carries on, so an
    execution that killed somebody does not rule the Saint out. It says
    something had to have stopped them, which the impairment plan can pay
    for like anything else.

    This used to be a flat rejection, which is the wrong direction to be
    wrong in: a Poisoner going for the Saint on the day the town is minded
    to execute them is a real play, and the solver was insisting it never
    happened.
    """

    SEATS = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"]

    def board(self):
        from botc.info import GameState
        from botc import scripts
        return GameState(n_players=9, script=scripts.TROUBLE_BREWING,
                         claims={i: r for i, r in enumerate(self.SEATS)},
                         deaths={8: "E2"})

    def world(self, at_eight):
        from botc.worlds import World
        return World(("Washerwoman", "Librarian", "Investigator", "Chef",
                      "Empath", "FortuneTeller", "Undertaker", at_eight,
                      "Saint"), (None,) * 9)

    def test_a_poisoner_explains_it(self):
        import botc.solver as S
        cost = S.explanation_cost(self.world("Poisoner"), self.board())
        self.assertIsNotNone(cost, "a poisoned Saint can be executed")
        self.assertLess(cost, 1.0, "and it costs something to say so")

    def test_with_nothing_to_stop_them_it_is_still_impossible(self):
        import botc.solver as S
        self.assertIsNone(S.explanation_cost(self.world("Recluse"),
                                             self.board()))

    def test_the_worlds_it_restores_are_not_a_rounding_error(self):
        import botc.solver as S
        state = self.board()
        valid = S.solve(state)[1]
        really = [w for w in valid if w.roles[8] == "Saint"]
        self.assertGreater(len(really), 100)

    def test_but_it_is_still_evidence_they_were_lying(self):
        """Restoring the possibility is not the same as endorsing it. An
        executed seat that died is far likelier to have been bluffing."""
        import botc.solver as S
        state = self.board()
        rows = S.summarize(S.solve(state)[1], state)
        self.assertGreater(rows[8]["evil_pct"], 60.0)
        self.assertLess(rows[8]["evil_pct"], 95.0)

    def test_a_drunk_claiming_saint_was_never_the_question(self):
        """It is not the Saint, so this rule never looks at it — the
        claim is a lie only in the sense that the Storyteller told it."""
        import botc.solver as S
        from botc.worlds import World
        drunk = World(("Washerwoman", "Librarian", "Investigator", "Chef",
                       "Empath", "FortuneTeller", "Undertaker", "Poisoner",
                       "Drunk"), (None,) * 8 + ("Chef",))
        self.assertIsNotNone(S.explanation_cost(drunk, self.board()))


class ADemonWithNoRuleOfItsOwn(SolverTest):
    """Kills the ordinary way, rather than not at all.

    The generic kill used to name the Imp, which quietly meant "no Demon
    on any script but Trouble Brewing and Bad Moon Rising can kill". A
    night death on a third script made every world impossible — an
    ordinary board reading as a contradiction, which is far worse than a
    Demon whose special trick is not modelled yet.

    Found by adding Sects & Violets and recording one death on it.
    """

    SEATS = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
             "Flowergirl", "TownCrier", "Oracle", "Mutant", "Sweetheart"]

    def board(self, **kw):
        from botc.info import GameState
        from botc import scripts
        return GameState(n_players=9, script=scripts.SECTS_AND_VIOLETS,
                         claims={i: r for i, r in enumerate(self.SEATS)}, **kw)

    def test_a_night_death_is_explicable(self):
        import botc.solver as S
        bare = len(S.solve(self.board())[1])
        killed = len(S.solve(self.board(deaths={2: "N2"}))[1])
        self.assertGreater(bare, 0)
        self.assertGreater(killed, 0, "an ordinary board is not a paradox")

    def test_the_demons_with_their_own_rule_are_named(self):
        import botc.solver as S
        self.assertEqual(S.KILLS_ITS_OWN_WAY,
                         {"Zombuul", "Pukka", "Shabaloth", "Po"})

    def test_and_those_still_use_it(self):
        """The named ones are excluded from the generic rule, so each is
        answered by exactly one."""
        import botc.solver as S
        from botc import deaths as D, scripts
        from botc.info import GameState
        from botc.worlds import World
        claims = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        state = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                          claims={i: r for i, r in enumerate(claims)})
        for demon in ("Zombuul", "Pukka", "Shabaloth", "Po"):
            with self.subTest(demon=demon):
                world = World(("Grandmother", "Sailor", "Chambermaid",
                               "Exorcist", "Innkeeper", "Gambler", "Gossip",
                               "Godfather", demon), (None,) * 9)
                firing = [c for c in D.causes_on(world, state, 3)
                          if c.name == "Demon" and not c.also_impaired]
                self.assertEqual(len(firing), 1)

    def test_a_quiet_night_really_is_impossible_here(self):
        """Not a bug: Sects & Violets has no protective character at all,
        so with nobody yet dead the kill cannot be stopped and there is
        nowhere to sink it."""
        import botc.solver as S
        self.assertEqual(len(S.solve(self.board(quiet_nights={2}))[1]), 0)


class OnlyTheImpPassesTheStar(SolverTest):
    """Every other Demon dying at night is the end of it.

    The rule said "the Imp kills itself and a Minion takes over" in its
    own docstring and then checked nothing, so it was offered to *every*
    Demon. A Zombuul or a Fang Gu that fell to a Slayer or an Assassin
    could quietly pass to a Minion and the game carried on — when good
    had actually won.

    Found while building the Fang Gu, which needed to know why it was
    being offered a starpass it does not have.
    """

    def lineages(self, demon, script, claims):
        import botc.solver as S
        from botc.info import GameState
        from botc.worlds import World
        world = World(tuple(list(claims[:7]) + ["Godfather", demon]),
                      (None,) * 9)
        state = GameState(n_players=9, script=script,
                          claims={i: r for i, r in enumerate(claims)},
                          deaths={8: "N3"}, days_done={3})
        return S.demon_lineages(world, state)

    def test_the_imp_still_passes_it(self):
        import botc.solver as S
        from botc.info import GameState
        from botc import scripts
        from botc.worlds import World
        claims = ["Washerwoman", "Librarian", "Investigator", "Chef",
                  "Empath", "FortuneTeller", "Undertaker", "Recluse",
                  "Saint"]
        world = World(("Washerwoman", "Librarian", "Investigator", "Chef",
                       "Empath", "FortuneTeller", "Undertaker",
                       "ScarletWoman", "Imp"), (None,) * 9)
        state = GameState(n_players=9, script=scripts.TROUBLE_BREWING,
                          claims={i: r for i, r in enumerate(claims)},
                          deaths={8: "N3"}, days_done={3})
        self.assertTrue(S.demon_lineages(world, state))

    def test_and_nobody_else_does(self):
        from botc import scripts
        claims = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        for demon in ("Pukka", "Shabaloth", "Po"):
            with self.subTest(demon=demon):
                self.assertEqual(
                    self.lineages(demon, scripts.BAD_MOON_RISING, claims), [],
                    "good won there, and the board should say so")
        # The Zombuul stood in that list until its first death was
        # modelled as what it is: not a death. It goes on being the Demon,
        # so there is one story, and it hands nothing on.
        self.assertEqual(
            self.lineages("Zombuul", scripts.BAD_MOON_RISING, claims), [()])

    def test_the_list_is_named_rather_than_assumed(self):
        import botc.solver as S
        self.assertEqual(S.STARPASSES, {"Imp"})


class TheThreeDemonsOfSectsAndViolets(SolverTest):

    CLAIMS = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz",
              "Barber", "Mutant", "Sweetheart"]

    def board(self, **kw):
        from botc.info import GameState
        from botc import scripts
        return GameState(n_players=9, script=scripts.SECTS_AND_VIOLETS,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def world(self, demon_at_five):
        from botc.worlds import World
        return World(("Clockmaker", "Dreamer", "Oracle", "Sage",
                      demon_at_five, "Klutz", "Barber", "Witch",
                      "Sweetheart"), (None,) * 9)

    def sources(self, world, state, night):
        from botc import impairment
        return {s.name: sorted(s.seats)
                for s in impairment.sources_on(world, state, night)}

    def test_the_no_dashii_skips_outsiders_and_minions(self):
        """By team, not by side — a Townsfolk can be evil. Seats 6, 7 and
        9 are Outsiders and seat 8 is a Minion, so the nearest Townsfolk
        each way are seats 1 and 4."""
        got = self.sources(self.world("NoDashii"), self.board(), 2)
        self.assertEqual(got.get("No Dashii"), [0, 3])

    def test_and_stops_when_it_does(self):
        got = self.sources(self.world("NoDashii"),
                           self.board(deaths={4: "N3"}), 4)
        self.assertNotIn("No Dashii", got)

    def test_the_vigormortis_waits_for_a_dead_minion(self):
        alive = self.sources(self.world("Vigormortis"), self.board(), 2)
        self.assertNotIn("Vigormortis", alive)
        dead = self.sources(self.world("Vigormortis"),
                            self.board(deaths={7: "N2"}), 3)
        self.assertEqual(dead.get("Vigormortis"), [0, 3])

    def test_and_it_too_stops_when_the_demon_goes(self):
        got = self.sources(self.world("Vigormortis"),
                           self.board(deaths={7: "N2", 4: "N3"}), 4)
        self.assertNotIn("Vigormortis", got)

    def test_the_fang_gu_jumps_into_an_outsider(self):
        """The Outsider *lives*, turns evil and becomes the Fang Gu; the
        old one dies. One body, and it is the Demon's own seat."""
        import botc.solver as S
        world = self.world("FangGu")
        chains = S.demon_lineages(world, self.board(deaths={4: "N3"},
                                                    days_done={3}))
        moved = [c[0] for c in chains if c]
        self.assertTrue(moved)
        for change in moved:
            with self.subTest(seat=change.seat + 1):
                self.assertEqual(change.role, "FangGu")
                self.assertEqual(change.side, "evil")
                self.assertEqual(world.team_at(change.seat, "N3"), "outsider")

    def test_it_does_not_also_get_a_starpass(self):
        """Only the Imp has one, so a Minion is never among the heirs."""
        import botc.solver as S
        world = self.world("FangGu")
        for chain in S.demon_lineages(world, self.board(deaths={4: "N3"},
                                                        days_done={3})):
            for change in chain:
                with self.subTest(seat=change.seat + 1):
                    self.assertNotEqual(
                        world.team_at(change.seat, "N3"), "minion")
