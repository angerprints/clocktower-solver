"""The second five experimental characters (07.10.2026).

Banshee, Zealot, Heretic, Goblin and Ojo — chosen for being small. None
of them reads anything and only the Ojo acts at night, so what is checked
here is what each one *leaves on the board*:

  * A **Banshee** the Demon kills is announced to the table — that one
    died, not which seat. A fact, only for one whose ability worked, and
    only for a death by the Demon (table ruling, 08.10.2026).
  * A **Zealot** votes on every nomination while five are alive. One
    that did not is no Zealot (table ruling, 08.10.2026: the votes are
    to be entered correctly).
  * A **Heretic** turns the result round and nothing else. The game ends
    when it would have, so nothing here reads it.
  * A **Goblin** that says so when nominated and is executed has won —
    dead of it or not (table ruling, 08.10.2026). The town calling the
    bluff and the game going on says it was none.
  * An **Ojo** names a character and its holder dies. From the board that
    is a Demon killing one player a night.

They have no script, like the first five, so two are made for them here.
"""

import random
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking       # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

SECOND = ("Banshee", "Zealot", "Heretic", "Goblin", "Ojo")

# Trouble Brewing's shape, with an Imp beside the Ojo to tell them apart.
LIKE_TB = ["banshee", "washerwoman", "librarian", "investigator", "chef",
           "empath", "fortuneteller", "undertaker", "monk", "ravenkeeper",
           "slayer", "soldier", "mayor",
           "zealot", "heretic", "saint", "drunk",
           "goblin", "poisoner", "spy", "scarletwoman",
           "ojo", "imp"]
# Bad Moon Rising's, for everything that guards, raises and counts.
LIKE_BMR = ["banshee", "grandmother", "sailor", "chambermaid", "exorcist",
            "innkeeper", "gambler", "gossip", "courtier", "professor",
            "minstrel", "tealady", "fool",
            "zealot", "heretic", "goon", "tinker",
            "goblin", "godfather", "devilsadvocate", "assassin",
            "ojo", "po"]

OJO = scripts.from_ids("Second five, like Trouble Brewing", LIKE_TB)
OJO_BMR = scripts.from_ids("Second five, like Bad Moon Rising", LIKE_BMR)


def cost(script, roles, infos=(), believes=None, **kw):
    """What the world costs on a board where everybody claims what they
    hold (or the token they were handed). None is a world thrown out."""
    n = len(roles)
    believes = tuple(believes or [None] * n)
    claims = {i: believes[i] or role for i, role in enumerate(roles)}
    state = GameState(n_players=n, script=script, claims=claims,
                      infos=list(infos), **kw)
    return S.explanation_cost(World(tuple(roles), believes), state)


#        0          1        2         3         4             5
SEVEN = ["Banshee", "Chef", "Empath", "Zealot", "Undertaker", "Goblin",
         "Ojo"]                                               # 6
# Ten at the table: two Minions, so a Poisoner can sit beside the Goblin.
#      0          1       2         3             4       5
TEN = ["Banshee", "Chef", "Empath", "Undertaker", "Monk", "Soldier",
       "Mayor", "Goblin", "Poisoner", "Ojo"]             # 6, 7, 8, 9


class TheyAreInTheCatalogue(SolverTest):

    def test_one_townsfolk_two_outsiders_a_minion_and_a_demon(self):
        teams = {key: CHARACTERS[key].team for key in SECOND}
        self.assertEqual(teams, {"Banshee": "townsfolk", "Zealot": "outsider",
                                 "Heretic": "outsider", "Goblin": "minion",
                                 "Ojo": "demon"})
        for key in SECOND:
            self.assertTrue(CHARACTERS[key].modelled)

    def test_only_the_ojo_has_a_night(self):
        for key in ("Banshee", "Zealot", "Heretic", "Goblin"):
            with self.subTest(character=key):
                self.assertEqual(CHARACTERS[key].nights, "never")
                self.assertEqual(CHARACTERS[key].other_night, 0)
        self.assertEqual(CHARACTERS["Ojo"].nights, "other")

    def test_the_ojo_acts_where_the_publisher_puts_it(self):
        """After the Vigormortis and before anything the vendored file
        numbers later — the Assassin is next."""
        ojo = CHARACTERS["Ojo"].other_night
        self.assertEqual(ojo, CHARACTERS["Vigormortis"].other_night)
        self.assertGreater(ojo, CHARACTERS["Vortox"].other_night)
        self.assertLess(ojo, CHARACTERS["Assassin"].other_night)
        self.assertEqual(CHARACTERS["Ojo"].first_night, 0)

    def test_the_ojo_can_reach_a_goon(self):
        """It names the Goon's character, and that is choosing it — the
        wiki's Goon page has a Courtier doing exactly that."""
        self.assertTrue(CHARACTERS["Ojo"].chooses)

    def test_a_chambermaid_counts_only_the_ojo(self):
        roles = ["Chambermaid", "Banshee", "Zealot", "Goblin", "Ojo",
                 "Gambler", "Sailor"]
        world = World(tuple(roles), (None,) * 7)
        state = GameState(n_players=7, script=OJO_BMR,
                          claims=dict(enumerate(roles)))
        woke = {seat: waking.woke_for_own_ability(world, state, seat, 2)
                for seat in (1, 2, 3, 4)}
        self.assertEqual(woke, {1: False, 2: False, 3: False, 4: True})
        # And the first night the Goblin is only shown its team.
        self.assertFalse(waking.woke_for_own_ability(world, state, 3, 1))


class ABansheeTheDemonKilled(SolverTest):
    """Told to the whole table, so it is a fact — and it is told for a
    seat nobody names."""

    ROW = I.BansheeAnnounced(2, 4)        # whoever wrote it down

    def test_it_is_a_fact_and_no_vortox_reaches_it(self):
        self.assertTrue(self.ROW.hard())
        self.assertFalse(self.ROW.is_information(None))
        self.assertIsNone(self.ROW.source_seat(None))

    def test_the_banshee_is_whoever_died_that_night(self):
        self.assertEqual(cost(OJO, SEVEN, [self.ROW], deaths={0: "N2"}), 1.0)

    def test_no_banshee_among_the_dead_is_no_world(self):
        """Seat 1 fell, and seat 1 is the Chef here."""
        self.assertIsNone(cost(OJO, SEVEN, [self.ROW], deaths={1: "N2"}))

    def test_nor_one_that_died_another_night(self):
        self.assertIsNone(cost(OJO, SEVEN, [self.ROW],
                               deaths={1: "N2", 0: "N3"}))

    def test_only_for_a_death_by_the_demon(self):
        """Nothing but the Demon kills on this script, so the Banshee
        dying at all says the Demon did it. A Gossip could have — and
        then there would be no announcement."""
        gossiping = scripts.from_ids("with a Gossip", LIKE_BMR)
        roles = ["Banshee", "Gossip", "Chambermaid", "Sailor", "Gambler",
                 "Goblin", "Ojo"]
        world = World(tuple(roles), (None,) * 7)
        state = GameState(n_players=7, script=gossiping,
                          claims=dict(enumerate(roles)), infos=[self.ROW],
                          deaths={0: "N2"})
        from botc import deaths as D
        others = D.shields_on(world, state, 2, 0, D.OTHER)
        self.assertEqual([s.by for s in others], ["Banshee announced"])
        self.assertEqual(D.shields_on(world, state, 2, 0, D.DEMON), [])
        # Two bodies, the Banshee and the Chambermaid: one Demon kill, so
        # the other has to be the Gossip's — and it cannot be the
        # Banshee's. With the Gossip's words true, the board fits.
        kept = cost(gossiping, roles, [self.ROW],
                    deaths={0: "N2", 2: "N2"})
        self.assertIsNotNone(kept)

    def test_a_drunk_holding_the_token_is_never_announced(self):
        roles = ["Drunk"] + SEVEN[1:]
        believes = ["Banshee"] + [None] * 6
        self.assertIsNone(cost(OJO, roles, [self.ROW], believes=believes,
                               deaths={0: "N2"}))

    def test_a_philosopher_that_took_it_is(self):
        mixed = scripts.from_ids("with a Philosopher", LIKE_TB + ["philosopher"])
        roles = ["Philosopher"] + SEVEN[1:]
        took = I.PhilosopherChoice(1, 0, role="Banshee")
        self.assertIsNotNone(cost(mixed, roles, [took, self.ROW],
                                  deaths={0: "N2"}))
        self.assertIsNone(cost(mixed, roles, [self.ROW], deaths={0: "N2"}))

    def test_it_was_working_when_it_fell(self):
        """A poisoned Banshee goes quietly, so the one announced was not
        poisoned: the row leans on its seat."""
        world = World(tuple(TEN), (None,) * 10)
        state = GameState(n_players=10, script=OJO,
                          claims=dict(enumerate(TEN)), infos=[self.ROW],
                          deaths={0: "N2"})
        self.assertEqual(self.ROW.leaned_on(world, state), (0,))
        _fails, _ft, _cost, working = S._plain_failures(world, state)
        self.assertEqual(working, {2: {0}})

    def test_so_a_reading_it_would_have_to_be_poisoned_for_does_not_fit(self):
        """One Poisoner, one night: it cannot have been on the Banshee
        and is needed on the Empath, who heard something untrue — fine.
        But a Banshee that itself said something only poison explains is
        not."""
        false_empath = I.Empath(2, 2, count=2)      # between 1 and 3: none
        self.assertIsNotNone(cost(OJO, TEN, [self.ROW, false_empath],
                                  deaths={0: "N2"}))
        # Nothing the Banshee says is a reading, so pin it the other
        # way: the Poisoner's only target that night is the Empath, and
        # demanding the Banshee poisoned too has no plan.
        world = World(tuple(TEN), (None,) * 10)
        state = GameState(n_players=10, script=OJO,
                          claims=dict(enumerate(TEN)), infos=[self.ROW],
                          deaths={0: "N2"})
        self.assertIsNone(S._impairment_plan(world, state, {2: {0}},
                                             {2: {0}}))


class AZealotVotes(SolverTest):
    """"If there are 5 or more players alive, you must vote for every
    nomination." A Zealot that did not is no Zealot (table ruling,
    08.10.2026) — and drunk or poisoned is no excuse, the wiki says."""

    def board(self, voted, **kw):
        return cost(OJO, SEVEN, votes={1: set(voted)},
                    nominations={1: {1}}, **kw)

    def test_a_zealot_that_voted_costs_nothing(self):
        self.assertEqual(self.board({1, 3, 4}), 1.0)

    def test_one_that_did_not_is_no_zealot(self):
        self.assertIsNone(self.board({1, 4}))

    def test_on_any_such_day(self):
        got = cost(OJO, SEVEN, votes={1: {1, 3}, 2: {2}},
                   nominations={1: {1}, 2: {4}}, deaths={0: "N2"})
        self.assertIsNone(got)
        got = cost(OJO, SEVEN, votes={1: {1, 3}, 2: {2, 3}},
                   nominations={1: {1}, 2: {4}}, deaths={0: "N2"})
        self.assertEqual(got, 1.0)

    def test_poisoned_is_no_excuse(self):
        """Ten at the table and a Poisoner beside it: still ruled out."""
        roles = ["Zealot"] + TEN[1:]
        self.assertIsNone(cost(OJO, roles, votes={1: {1, 2}},
                               nominations={1: {1}}))

    def test_not_with_four_alive(self):
        deaths = {0: "N2", 1: "E1", 2: "E2"}
        got = cost(OJO, SEVEN, votes={3: {4}}, nominations={3: {4}},
                   deaths=deaths | {4: "N3"})
        self.assertEqual(got, 1.0)

    def test_not_on_a_day_nobody_wrote_votes_down_for(self):
        self.assertEqual(cost(OJO, SEVEN, nominations={1: {1}}), 1.0)

    def test_not_without_a_nomination(self):
        self.assertEqual(cost(OJO, SEVEN, votes={1: {1}}), 1.0)

    def test_nobody_else_is_held_to_it(self):
        """The Chef did not vote either, and is no Zealot."""
        self.assertEqual(self.board({3, 4}), 1.0)


class AHereticChangesNothingTheBoardShows(SolverTest):

    def test_a_world_with_one_costs_what_it_would_without(self):
        roles = SEVEN[:3] + ["Heretic"] + SEVEN[4:]
        for over in ({}, {"game_over": True}, {"days_done": {1}}):
            with self.subTest(board=over):
                self.assertEqual(cost(OJO, roles, **over), 1.0)


class AGoblinSaysSo(SolverTest):
    """`night` is the day. Seat 5 is the Goblin in SEVEN, seat 7 in TEN."""

    def test_the_words_alone_rule_nothing_out(self):
        self.assertEqual(cost(OJO, SEVEN, [I.GoblinClaim(1, 5)]), 1.0)
        self.assertEqual(cost(OJO, SEVEN, [I.GoblinClaim(1, 1)]), 1.0)

    def test_executed_and_the_game_went_on_it_was_no_goblin(self):
        """Nothing on a table of seven can have stopped it."""
        said = I.GoblinClaim(1, 5)
        self.assertIsNone(cost(OJO, SEVEN, [said], deaths={5: "E1"},
                               days_done={1}))
        # Went on, shown by a death the night after instead.
        self.assertIsNone(cost(OJO, SEVEN, [said],
                               deaths={5: "E1", 1: "N2"}))

    def test_executed_is_enough_dead_or_not(self):
        """"An ability that triggers on execution does not need the
        execution to kill" (table ruling, 08.10.2026). Executed and
        walked away — a Devil's Advocate, say — is still the win."""
        # Nobody here who could have made the Goblin drunk.
        roles = ["Banshee", "Grandmother", "Chambermaid", "Exorcist",
                 "TeaLady", "Gambler", "Gossip", "Goblin",
                 "DevilsAdvocate", "Ojo"]
        on = dict(executions={1: 7}, days_done={1})
        # Walked away, a Devil's Advocate beside it: legal on its own...
        self.assertIsNotNone(cost(OJO_BMR, roles, **on))
        # ...and not after saying it was the Goblin.
        self.assertIsNone(cost(OJO_BMR, roles, [I.GoblinClaim(1, 7)], **on))
        # The Gossip saying it and walking away is nothing.
        gossip = dict(executions={1: 6}, days_done={1})
        self.assertIsNotNone(cost(OJO_BMR, roles, [I.GoblinClaim(1, 6)],
                                  **gossip))

    def test_anybody_else_saying_it_and_hanging_is_fine(self):
        said = I.GoblinClaim(1, 1)
        self.assertEqual(cost(OJO, SEVEN, [said], deaths={1: "E1"},
                              days_done={1}), 1.0)

    def test_a_board_read_that_evening_says_nothing_yet(self):
        said = I.GoblinClaim(1, 5)
        self.assertEqual(cost(OJO, SEVEN, [said], deaths={5: "E1"}), 1.0)
        self.assertEqual(cost(OJO, SEVEN, [said], deaths={5: "E1"},
                              game_over=True), 1.0)

    def test_a_claim_on_another_day_does_not_count(self):
        """"The Goblin must have claimed to be the Goblin today.\""""
        said = I.GoblinClaim(1, 5)
        self.assertEqual(cost(OJO, SEVEN, [said], deaths={5: "E2"},
                              days_done={1, 2}), 1.0)

    def test_a_poisoned_goblin_is_the_one_excuse(self):
        said = I.GoblinClaim(1, 7)
        got = cost(OJO, TEN, [said], deaths={7: "E1"}, days_done={1})
        self.assertIsNotNone(got)
        self.assertLess(got, 1.0)

    def test_it_is_an_event_and_a_choice(self):
        said = I.GoblinClaim(1, 5)
        self.assertTrue(said.event)
        self.assertTrue(said.is_a_choice)
        self.assertEqual(said.source_seat(None), 5)


class AnOjoKillsLikeAnyDemon(SolverTest):

    def test_one_death_a_night(self):
        self.assertEqual(cost(OJO, SEVEN, deaths={1: "N2"}), 1.0)
        self.assertIsNone(cost(OJO, SEVEN, deaths={1: "N2", 2: "N2"}))

    def test_it_does_not_pass_the_star(self):
        """An Imp that kills itself hands on to its Minion. An Ojo that
        names itself is simply dead, and the game was over."""
        deaths = {6: "N2", 1: "N3"}
        self.assertIsNone(cost(OJO, SEVEN, deaths=deaths))
        imp = SEVEN[:6] + ["Imp"]
        self.assertIsNotNone(cost(OJO, imp, deaths=deaths))

    def test_a_soldier_and_a_monk_stop_it(self):
        """Nothing about naming a character gets round a guard."""
        from botc import deaths as D
        roles = ["Soldier"] + SEVEN[1:]
        world = World(tuple(roles), (None,) * 7)
        state = GameState(n_players=7, script=OJO,
                          claims=dict(enumerate(roles)))
        shields = D.shields_on(world, state, 2, 0, D.DEMON)
        self.assertEqual([s.by for s in shields], ["Soldier"])


class ACourtierNamingTheGoonChoosesIt(SolverTest):
    """"The Courtier chooses the Goon. The Goon turns good, and the
    Courtier becomes drunk" — the wiki's Goon page (table ruling,
    08.10.2026). Found while building the Ojo, which also names a
    character rather than pointing at a player."""

    ROLES = ["Courtier", "Goon", "Chambermaid", "Sailor", "Gambler",
             "Godfather", "Po"]

    def sources(self, row, night):
        from botc import impairment
        world = World(tuple(self.ROLES), (None,) * 7)
        state = GameState(n_players=7, script=scripts.BAD_MOON_RISING,
                          claims=dict(enumerate(self.ROLES)), infos=[row])
        return {s.name: s for s in impairment.sources_on(world, state,
                                                          night)}

    def test_the_courtier_may_be_the_goons_first_chooser(self):
        got = self.sources(I.CourtierChoice(1, 0, role="Goon"), 1)
        self.assertIn(0, got["Goon"].seats)

    def test_and_then_the_goon_is_not_drunk_for_certain(self):
        """Drunk on the spot, it made nobody drunk: the three days are
        on offer rather than forced."""
        got = self.sources(I.CourtierChoice(1, 0, role="Goon"), 1)
        self.assertFalse(got["Courtier"].unavoidable())
        other = self.sources(I.CourtierChoice(1, 0, role="Godfather"), 1)
        self.assertTrue(other["Courtier"].unavoidable())

    def test_only_on_the_night_it_named_the_goon(self):
        got = self.sources(I.CourtierChoice(1, 0, role="Goon"), 2)
        self.assertNotIn(0, got.get("Goon").seats if "Goon" in got else ())

    def test_the_simulator_plays_it(self):
        import simulate
        first = 0
        for seed in range(1500):
            deal, heard = simulate.play(9, random.Random(seed), nights=3,
                                        script=scripts.BAD_MOON_RISING)
            for row in heard:
                if not isinstance(row, I.CourtierChoice) or row.role != "Goon":
                    continue
                chose = deal.goon_first.get(row.night)
                if chose and chose[0] == row.player:
                    first += 1
                    with self.subTest(seed=seed):
                        self.assertFalse(deal.working(row.player, row.night))
                        self.assertNotIn(
                            (row.night, chose[1], row.player),
                            deal.courtier_drunks)
        self.assertGreater(first, 3)


class TheSimulatorPlaysThem(SolverTest):

    def played(self, script, games, nights=4):
        import claims as claim_model
        import simulate
        seen, lost = {}, []
        for seed in range(games):
            n = [7, 8, 9, 10, 11][seed % 5]
            rng = random.Random(seed)
            deal, heard = simulate.play(n, rng, nights=nights, script=script)
            claims, wakes, _ = claim_model.claims_for(deal, rng,
                                                      script=script)
            state = GameState(n_players=n, script=script, claims=claims,
                              wakes=wakes, infos=list(heard),
                              votes=dict(deal.votes),
                              nominations=dict(deal.nominations),
                              **deal.record())
            for row in heard:
                seen[type(row).__name__] = seen.get(type(row).__name__, 0) + 1
            if deal.ended_why == "goblin":
                seen["won by a Goblin"] = seen.get("won by a Goblin", 0) + 1
            truth = World(tuple(deal.roles), tuple(deal.believes))
            if S.explanation_cost(truth, state) is None:
                lost.append(seed)
        return seen, lost

    def test_like_trouble_brewing(self):
        seen, lost = self.played(OJO, 300)
        self.assertEqual(lost, [])
        for what in ("BansheeAnnounced", "GoblinClaim", "won by a Goblin"):
            self.assertGreater(seen.get(what, 0), 5, what)

    def test_like_bad_moon_rising(self):
        seen, lost = self.played(OJO_BMR, 300)
        self.assertEqual(lost, [])
        for what in ("BansheeAnnounced", "GoblinClaim", "won by a Goblin"):
            self.assertGreater(seen.get(what, 0), 5, what)

    def games(self, script, how_many=400, nights=4):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=nights,
                                      script=script)

    def test_a_banshee_is_announced_when_the_demon_takes_it_working(self):
        said = quiet = 0
        for script in (OJO, OJO_BMR):
            for seed, (deal, heard) in self.games(script):
                rows = {r.night: r for r in heard
                        if isinstance(r, I.BansheeAnnounced)}
                for night, killed in deal.demon_killed.items():
                    for seat in killed:
                        if deal.role_at(seat, f"N{night}") != "Banshee":
                            continue
                        working = deal.working(seat, night)
                        said += working
                        quiet += not working
                        with self.subTest(script=script.name, seed=seed):
                            self.assertEqual(night in rows, working)
                for night, row in rows.items():
                    with self.subTest(script=script.name, seed=seed):
                        self.assertIn(row.player,
                                      deal.demon_killed.get(night, ()))
        self.assertGreater(said, 20)
        self.assertGreater(quiet, 0, "no poisoned Banshee fell in range")

    def test_a_zealot_votes_while_five_are_alive(self):
        days = 0
        for script in (OJO, OJO_BMR):
            for seed, (deal, _heard) in self.games(script):
                for day, voted in deal.votes.items():
                    phase = f"E{day}"
                    living = deal.alive_at(phase)
                    # Five alive at the last nomination too: nobody but
                    # the executed went during the day.
                    if len(living) < 5 or deal.died_on(f"D{day}"):
                        continue
                    for seat in living:
                        if deal.role_at(seat, phase) != "Zealot":
                            continue
                        days += 1
                        with self.subTest(script=script.name, seed=seed,
                                          day=day):
                            self.assertIn(seat, voted)
        self.assertGreater(days, 100)

    def test_a_working_goblin_that_says_so_ends_the_game(self):
        ended = went_on = others = 0
        for script in (OJO, OJO_BMR):
            for seed, (deal, heard) in self.games(script):
                for row in heard:
                    if not isinstance(row, I.GoblinClaim):
                        continue
                    day = row.night
                    # Hanged that day: dead of it — perhaps raised and
                    # hanged again since, so every death is asked — or
                    # walked away and recorded as executed.
                    self.assertTrue(
                        f"E{day}" in deal.deaths_of(row.player)
                        or deal.executions.get(day) == row.player)
                    if deal.role_at(row.player, f"D{day}") != "Goblin":
                        others += 1
                        continue
                    working = deal.working(row.player, day, by_day=True)
                    with self.subTest(script=script.name, seed=seed):
                        self.assertEqual(deal.ended_at == f"E{day}"
                                         and deal.ended_why == "goblin",
                                         working)
                    ended += working
                    went_on += not working
        self.assertGreater(ended, 20)
        self.assertGreater(went_on, 0, "no drunk or poisoned Goblin hanged")
        self.assertGreater(others, 10)

    def test_no_other_script_plays_differently(self):
        """Nothing is drawn for a Goblin or a Zealot that is not there."""
        import hashlib
        import simulate
        digest = hashlib.sha256()
        for seed in range(60):
            deal, heard = simulate.play(9, random.Random(seed), nights=3,
                                        script=scripts.BAD_MOON_RISING)
            digest.update(repr((deal.roles, sorted(deal.deaths.items()),
                                [repr(r) for r in heard])).encode())
        self.assertEqual(digest.hexdigest()[:16], BMR_SIXTY)


class TheNightWalkReplaysThem(SolverTest):
    """Only the Ojo acts at night, and it kills the ordinary way — so
    the walk has nothing new to learn, and that is what is checked."""

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = 0
        for script in (OJO, OJO_BMR):
            for seed in range(150):
                # 410 on the second script is a Sailor choosing a Goon
                # the Innkeeper drunks later that night, which the walk
                # is told as drunk from the start. Not one of the five.
                if script is OJO_BMR and seed == 410:
                    continue
                n = [7, 8, 9, 10, 11][seed % 5]
                deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                            script=script)
                for night in range(2, deal.nights_played + 1):
                    hidden = nightwalk.hidden_from(deal, night, heard)
                    got = nightwalk.walk(deal, night, hidden)
                    nights += 1
                    with self.subTest(script=script.name, seed=seed,
                                      night=night):
                        self.assertEqual(got.died,
                                         deal.died_on(f"N{night}"))
                        self.assertEqual(got.untold, set())
        self.assertGreater(nights, 500)


# sixty Bad Moon Rising games as the simulator played them before the
# second five went in; see `test_no_other_script_plays_differently`.
BMR_SIXTY = "3dfeee8e079eff4a"


if __name__ == "__main__":
    unittest.main()
