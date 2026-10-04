"""Bad Moon Rising: twenty-five characters, and what each of them does.

Every lineup here is chosen rather than convenient, and says why. Seat
positions carry meaning on this script — a Tea Lady needs good players on
both sides, a Goon needs somebody able to choose it, a Grandmother needs a
grandchild — so each group names its seats and refers to them by name
instead of by index.

Two questions cannot be asked on this script at all and are tested on a
custom one: showing a Grandmother somebody evil who *registers* as good,
and the contrast that makes the Lunatic interesting — a believer who
thinks they are good. Bad Moon Rising has neither a Spy nor a Drunk.
"""

import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import deaths, scripts                  # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

BMR = scripts.BAD_MOON_RISING

# What the table says. Seven Townsfolk claims and two Outsider claims on a
# nine-seat board, so at least two seats are lying — which is ordinary.
CLAIMS = ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
          "Gambler", "Gossip", "Tinker", "Moonchild"]

TB_CLAIMS = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"]


def board(**kw):
    """A nine-seat Bad Moon Rising board."""
    return GameState(n_players=9, script=BMR,
                     claims={i: r for i, r in enumerate(CLAIMS)}, **kw)


def trouble_brewing(**kw):
    """The same size board on the other script, for the comparisons that
    ask what happens without these characters."""
    return GameState(n_players=9, script=scripts.TROUBLE_BREWING,
                     claims={i: r for i, r in enumerate(TB_CLAIMS)}, **kw)


def among(*roles):
    """A world of nine distinct characters, in seat order."""
    assert len(roles) == 9 and len(set(roles)) == 9, roles
    return World(tuple(roles), (None,) * 9)


# The lineup most groups start from. Seats 1–7 hold what they claim, seat
# 8 is the Minion and seat 9 the Demon — so the two Outsider claims are
# the lies, and every Townsfolk ability is genuinely in play.
HONEST = ("Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
          "Gambler", "Gossip", "Godfather", "Zombuul")


class TheScriptItself(SolverTest):

    def test_it_is_the_published_twenty_five(self):
        self.assertEqual(len(BMR.keys), 25)
        self.assertEqual(len(BMR.townsfolk), 13)
        self.assertEqual(len(BMR.outsiders), 4)
        self.assertEqual(len(BMR.minions), 4)
        self.assertEqual(len(BMR.demons), 4)

    def test_it_carries_nothing_from_trouble_brewing(self):
        """Worth pinning down: this was once built by appending the new
        characters to a Trouble Brewing list used as a placeholder, and
        the placeholder was never removed. Thirteen characters that do
        not belong, and a search five times larger than it should be.
        """
        self.assertEqual(set(BMR.keys) & set(scripts.TROUBLE_BREWING.keys),
                         set())

    def test_every_character_is_reasoned_about(self):
        # The Mastermind was the one left until 29.09.2026.
        self.assertEqual([c.name for c in BMR.unmodelled()], [])

    def test_a_claim_from_off_the_script_is_refused(self):
        """It used to be set aside as "no constraint", which leaves every
        seat unconstrained and the search with nothing to prune on. That
        does not fail, it hangs."""
        from botc.worlds import OffScript
        with self.assertRaises(OffScript):
            S.solve(GameState(n_players=7, script=BMR, claims={0: "Empath"}))


# --------------------------------------------------------------------------
# Townsfolk
# --------------------------------------------------------------------------

class TheGrandmother(SolverTest):
    """Shown a good player on the first night. If the Demon takes them,
    she goes too. Seat 1 is the Grandmother, seat 3 the grandchild."""

    GRANNY, CHILD = 0, 2

    def reading(self, role="Chambermaid"):
        from botc.info import GrandmotherInfo
        return GrandmotherInfo(1, self.GRANNY, target=self.CHILD, role=role)

    def test_her_reading_has_to_be_of_a_good_seat(self):
        evil_there = among("Grandmother", "Sailor", "Godfather", "Exorcist",
                           "Innkeeper", "Gambler", "Gossip", "Tinker",
                           "Zombuul")
        self.assertTrue(self.reading().holds(among(*HONEST), board(), None,
                                             self.GRANNY))
        self.assertFalse(self.reading("Godfather").holds(evil_there, board(),
                                                         None, self.GRANNY),
                         "a Godfather is not a good player")

    def test_the_demon_taking_the_grandchild_takes_her_too(self):
        state = board(deaths={self.CHILD: "N2", self.GRANNY: "N2"},
                      infos=[self.reading()])
        self.assertIsNotNone(S.explanation_cost(among(*HONEST), state),
                             "two bodies from one kill")

    def test_losing_only_the_grandchild_means_she_was_not_working(self):
        """Where nothing could have kept her alive, that is. A Courtier
        sits where the Innkeeper was: see the next one."""
        state = board(deaths={self.CHILD: "N2"}, infos=[self.reading()])
        nobody_to_guard_her = among(
            *(r if r != "Innkeeper" else "Courtier" for r in HONEST))
        cost = S.explanation_cost(nobody_to_guard_her, state)
        self.assertIsNotNone(cost)
        self.assertLess(cost, 1.0, "something had to have stopped her")

    def test_or_something_was_keeping_her_alive(self):
        """Grief is a death like any other, and what keeps a seat alive
        keeps it alive from this too. With an Innkeeper about she may
        simply have been one of its two; with a Tea Lady beside her and
        both neighbours good, she cannot die at all.

        The solver read "she lived" as "she was not working" and nothing
        else — so a Grandmother a Tea Lady was keeping, with nothing on
        the board able to impair her, had no world (03.10.2026)."""
        state = board(deaths={self.CHILD: "N2"}, infos=[self.reading()])
        self.assertEqual(S.explanation_cost(among(*HONEST), state), 1.0,
                         "the Innkeeper may have chosen her")
        # Tea Lady in the last seat: her neighbours are the Gossip and,
        # round the circle, the Grandmother — both good. Nothing here
        # drunks or poisons anybody.
        beside_her = among("Grandmother", "Zombuul", "Chambermaid", "Fool",
                           "Pacifist", "Gambler", "Mastermind", "Gossip",
                           "TeaLady")
        cost = S.explanation_cost(beside_her, state)
        self.assertEqual(cost, 1.0, "the Tea Lady kept her")
        # And had she died there, the Tea Lady was not working — which
        # nothing on that board can arrange.
        both = board(deaths={self.CHILD: "N2", self.GRANNY: "N2"},
                     infos=[self.reading()])
        self.assertIsNone(S.explanation_cost(beside_her, both))

    def test_the_token_sits_where_she_was_shown(self):
        """A marker the Storyteller put down, not a character anybody
        holds — so it stays put even if what she was told was invented."""
        was_the_demon = among("Grandmother", "Sailor", "Zombuul", "Exorcist",
                              "Innkeeper", "Gambler", "Gossip", "Tinker",
                              "Godfather")
        state = board(deaths={self.CHILD: "N2"}, infos=[self.reading()])
        hit = deaths.implications_of(was_the_demon, state, 2, self.CHILD,
                                     deaths.DEMON)
        self.assertEqual([h.seat for h in hit], [self.GRANNY])

    def test_a_grandchild_lost_to_anything_else_leaves_her_standing(self):
        state = board(deaths={self.CHILD: "N2"}, infos=[self.reading()])
        self.assertEqual(deaths.implications_of(among(*HONEST), state, 2,
                                                self.CHILD, deaths.OTHER), [])


class ShownSomebodyWhoRegistersAsGood(SolverTest):
    """The Grandmother question this script cannot ask.

    She is shown a good player, and the Spy is evil while registering as
    good — so it can be the one she is shown. Nothing on Bad Moon Rising
    misregisters, so the question needs a script where something does.
    """

    ROLES = ("Grandmother", "Spy", "Chambermaid", "Exorcist", "Innkeeper",
             "Gambler", "Tinker", "Moonchild", "Zombuul")

    def script(self):
        return scripts.from_ids("Grandmother and a Spy", [
            "grandmother", "chambermaid", "exorcist", "innkeeper", "gambler",
            "gossip", "tinker", "moonchild", "spy", "godfather", "zombuul"])

    def test_a_spy_can_be_shown_to_her_as_a_townsfolk(self):
        from botc.info import GrandmotherInfo
        state = GameState(n_players=9, script=self.script(),
                          claims={0: "Grandmother", 2: "Chambermaid"})
        spied = World(self.ROLES, (None,) * 9)
        self.assertTrue(
            GrandmotherInfo(1, 0, target=1, role="Chambermaid")
            .holds(spied, state, None, 0),
            "evil, shown as good — which is what the Spy is for")


class TheSailor(SolverTest):
    """Cannot die at all while working, and drunks one of two people a
    night without being told which. Seat 2."""

    SAILOR = 1

    def test_it_is_shielded_against_every_kind_of_death(self):
        for kind in (deaths.DEMON, deaths.OTHER):
            with self.subTest(kind=kind):
                got = S.a_sober_sailor_cannot_die(among(*HONEST), board(),
                                                  2, self.SAILOR, kind)
                self.assertTrue(got)
                self.assertFalse(got[0].chosen,
                                 "always on, so a dead Sailor means "
                                 "something stopped it")

    def test_a_dead_sailor_means_something_stopped_it(self):
        state = board(deaths={self.SAILOR: "N2"})
        cost = S.explanation_cost(among(*HONEST), state)
        self.assertIsNotNone(cost)
        self.assertLess(cost, 1.0)

    def test_drunking_itself_is_ordinary_and_drunking_evil_is_not(self):
        """A Storyteller treats it as the price the town pays for having
        somebody unkillable, not as a weapon to point at evil."""
        source = S.a_sailor_drunks_one_of_two(among(*HONEST), board(), 2)[0]
        self.assertGreater(source.price(self.SAILOR), source.price(8),
                           "itself, versus the Demon it happened to pick")
        self.assertPct(source.price(2), source.price(self.SAILOR), 1e-9,
                       "another good seat is the same coin flip")

    def test_it_can_only_reach_the_living(self):
        source = S.a_sailor_drunks_one_of_two(among(*HONEST),
                                              board(deaths={2: "N2"}), 3)[0]
        self.assertNotIn(2, source.seats)

    def test_a_dead_sailor_drunks_nobody(self):
        self.assertEqual(S.a_sailor_drunks_one_of_two(
            among(*HONEST), board(deaths={self.SAILOR: "N2"}), 3), [])


class WalkingAwayFromAnExecution(SolverTest):
    """Four reasons now, told apart by which seat had to be working."""

    def test_there_are_four_of_them(self):
        self.assertEqual(len(S.SURVIVES_EXECUTION_RULES), 5)

    def test_a_sailor_walks_away_from_its_own(self):
        self.assertIsNotNone(S.explanation_cost(among(*HONEST),
                                                board(executions={1: 1})))

    def test_a_seat_with_no_reason_cannot_have_survived(self):
        nobody_helps = among("Grandmother", "Minstrel", "Chambermaid",
                             "TeaLady", "Innkeeper", "Gambler", "Gossip",
                             "Godfather", "Zombuul")
        self.assertIsNone(S.explanation_cost(nobody_helps,
                                             board(executions={1: 1})))

    def test_a_fool_walks_away_once(self):
        with_fool = among("Grandmother", "Fool", "Chambermaid", "Exorcist",
                          "Innkeeper", "Gambler", "Gossip", "Godfather",
                          "Zombuul")
        self.assertIsNotNone(S.explanation_cost(with_fool,
                                                board(executions={1: 1})))

    def test_a_pacifist_spares_the_good_and_not_the_evil(self):
        with_pacifist = among("Pacifist", "Sailor", "Chambermaid", "Exorcist",
                              "Innkeeper", "Gambler", "Gossip", "Godfather",
                              "Zombuul")
        self.assertIsNotNone(S.explanation_cost(with_pacifist,
                                                board(executions={1: 2})))
        self.assertIsNone(S.explanation_cost(with_pacifist,
                                             board(executions={1: 7})),
                          "seat 8 is the Godfather")

    def test_a_devils_advocate_saves_from_the_gallows_only(self):
        advocate = among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                         "Innkeeper", "Gambler", "Gossip", "DevilsAdvocate",
                         "Zombuul")
        self.assertEqual(S.a_devils_advocate_saves_from_the_gallows(
            advocate, board(), 2, 1), [7])


class TheInnkeeperAndTheExorcist(SolverTest):
    """One guards two from everything; the other sends the Demon to bed."""

    def test_the_innkeeper_guards_against_every_kind(self):
        for kind in (deaths.DEMON, deaths.OTHER):
            with self.subTest(kind=kind):
                got = S.an_innkeeper_guards_two(among(*HONEST), board(),
                                                2, 0, kind)
                self.assertTrue(got)
                self.assertTrue(got[0].chosen,
                                "it picks who, so a death implies nothing")

    def test_the_exorcist_only_stops_the_demon(self):
        self.assertTrue(S.an_exorcist_sends_the_demon_to_bed(
            among(*HONEST), board(), 2, 8, deaths.DEMON))
        self.assertEqual(S.an_exorcist_sends_the_demon_to_bed(
            among(*HONEST), board(), 2, 8, deaths.OTHER), [])

    def test_neither_does_anything_on_the_first_night(self):
        self.assertEqual(S.an_innkeeper_guards_two(
            among(*HONEST), board(), 1, 0, deaths.DEMON), [])
        self.assertEqual(S.an_exorcist_sends_the_demon_to_bed(
            among(*HONEST), board(), 1, 8, deaths.DEMON), [])

    def test_the_innkeepers_drunkenness_covers_the_day_after(self):
        """Which needs no special handling: a night and the day that
        follows already share one key, because poison works that way."""
        from botc.info import SlayerShot, VirginNomination
        self.assertEqual(SlayerShot(3, 0, target=1).night,
                         VirginNomination(3, 0, nominator=1).night)


class TheGambler(SolverTest):
    """Guess wrong and you die; guess right and nobody learns anything.
    Seat 6 is the Gambler, seat 3 the Chambermaid it names."""

    GAMBLER, NAMED = 5, 2

    def guess(self, role):
        from botc.info import GamblerGuess
        return GamblerGuess(2, self.GAMBLER, target=self.NAMED, role=role)

    def test_dying_of_it_means_the_guess_was_wrong(self):
        """On a night nothing else kills. Somebody died in daylight, so
        the Zombuul stays in bed — and a Gambler dead by morning after
        a *correct* guess has to have gone some dearer way."""
        day = {"deaths": {self.GAMBLER: "N2", 0: "D1"}, "executions": {1: 0}}
        wrong = board(infos=[self.guess("Exorcist")], **day)
        right = board(infos=[self.guess("Chambermaid")], **day)
        self.assertIsNotNone(S.explanation_cost(among(*HONEST), wrong))
        got = S.explanation_cost(among(*HONEST), right)
        self.assertTrue(
            got is None
            or got < S.explanation_cost(among(*HONEST), wrong),
            "dying on a correct guess needs excusing")

    def test_but_the_demon_may_take_one_that_guessed_right(self):
        """It guesses before the Demon acts. This was impossible — "dead,
        so wrong" — and the true world went with it whenever a Demon
        killed the Gambler that had just named somebody correctly
        (02.10.2026)."""
        right = board(deaths={self.GAMBLER: "N2"},
                      infos=[self.guess("Chambermaid")])
        self.assertEqual(S.explanation_cost(among(*HONEST), right), 1.0)

    def test_a_right_guess_is_not_offered_as_what_killed_it(self):
        right = board(deaths={self.GAMBLER: "N2"},
                      infos=[self.guess("Chambermaid")])
        self.assertEqual(S.a_gambler_may_lose(among(*HONEST), right, 2), [])

    def test_living_through_it_means_the_guess_was_right(self):
        self.assertPct(S.explanation_cost(
            among(*HONEST), board(infos=[self.guess("Chambermaid")])),
            1.0, 1e-9)
        self.assertLess(S.explanation_cost(
            among(*HONEST), board(infos=[self.guess("Exorcist")])), 1.0)

    def test_its_death_reaches_nobody_else(self):
        state = board(deaths={self.GAMBLER: "N2"},
                      infos=[self.guess("Exorcist")])
        got = S.a_gambler_may_lose(among(*HONEST), state, 2)
        self.assertEqual(got[0].seats, frozenset({self.GAMBLER}))

    def test_with_no_guess_recorded_there_is_no_risk(self):
        self.assertEqual(S.a_gambler_may_lose(among(*HONEST), board(), 2), [])


class TheGossip(SolverTest):
    """A second way to die at night, and not the Demon's. Seat 7."""

    def test_it_is_not_a_demon_death_and_need_not_fire(self):
        got = S.a_gossip_may_kill(among(*HONEST), board(), 2)
        self.assertEqual(got[0].kind, deaths.OTHER)
        self.assertFalse(got[0].must_fire)

    def test_it_can_be_sunk_into_somebody_already_dead(self):
        got = S.a_gossip_may_kill(among(*HONEST), board(), 2)
        self.assertEqual(got[0].seats, frozenset(range(9)))

    def test_it_accounts_for_a_body_the_demon_did_not(self):
        """The Zombuul kills once, so a second body needs something."""
        two = board(deaths={2: "N2", 4: "N2"})
        no_gossip = among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                          "Innkeeper", "Gambler", "Minstrel", "Godfather",
                          "Zombuul")
        self.assertIsNotNone(S.explanation_cost(among(*HONEST), two))
        self.assertIsNone(S.explanation_cost(no_gossip, two),
                          "one kill a night, and nothing else that kills")

    def test_a_dead_gossip_says_nothing(self):
        self.assertEqual(S.a_gossip_may_kill(among(*HONEST),
                                             board(deaths={6: "N2"}), 3), [])


class TheCourtier(SolverTest):
    """Names a character, not a player. Seat 1."""

    def world(self):
        return among("Courtier", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather", "Zombuul")

    def state(self, role, night=1):
        from botc.info import CourtierChoice
        return board(infos=[CourtierChoice(night, 0, role=role)])

    def test_it_reaches_whoever_holds_the_named_character(self):
        got = S.a_courtier_names_a_character(self.world(),
                                             self.state("Chambermaid"), 1)
        self.assertEqual(got[0].seats, frozenset({2}))

    def test_naming_somebody_nobody_is_does_nothing(self):
        """And spends the ability all the same. Nobody here is the Tea
        Lady, so there is nothing for it to land on."""
        self.assertEqual(S.a_courtier_names_a_character(
            self.world(), self.state("TeaLady"), 1), [])

    def test_it_lasts_three_days_and_nights(self):
        state = self.state("Chambermaid", night=2)
        for night, expected in ((1, False), (2, True), (3, True), (4, True),
                                (5, False)):
            with self.subTest(night=night):
                self.assertEqual(bool(S.a_courtier_names_a_character(
                    self.world(), state, night)), expected)

    def test_it_costs_nothing_because_it_is_not_luck(self):
        got = S.a_courtier_names_a_character(self.world(),
                                             self.state("Chambermaid"), 1)
        self.assertTrue(got[0].free_for_everyone())


class TheProfessor(SolverTest):
    """Raises one dead player, once, and only somebody registering as a
    Townsfolk. Seat 1."""

    def world(self):
        return among("Professor", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather", "Zombuul")

    def test_raising_needs_something_on_the_script_that_can(self):
        tb = trouble_brewing(deaths={2: "N2"}, resurrections={2: "N4"})
        self.assertEqual(len(S.solve(tb)[1]), 0)

    def test_the_raised_seat_has_to_register_as_a_townsfolk(self):
        good = board(deaths={2: "N2"}, resurrections={2: "N4"})
        minion = board(deaths={7: "N2"}, resurrections={7: "N4"})
        self.assertIsNotNone(S.explanation_cost(self.world(), good))
        self.assertIsNone(S.explanation_cost(self.world(), minion),
                          "a Godfather does not register as a Townsfolk")

    def test_registering_as_one_is_not_being_good(self):
        """Which is why it is evidence and not proof — and why it needs a
        script with something that misregisters."""
        script = scripts.from_ids("Professor and a Spy", [
            "professor", "chambermaid", "exorcist", "innkeeper", "gambler",
            "gossip", "tinker", "moonchild", "spy", "godfather", "zombuul"])
        state = GameState(n_players=9, script=script,
                          claims={0: "Professor", 2: "Chambermaid"},
                          deaths={1: "N2"}, resurrections={1: "N4"})
        spied = World(("Professor", "Spy", "Chambermaid", "Exorcist",
                       "Innkeeper", "Gambler", "Tinker", "Moonchild",
                       "Zombuul"), (None,) * 9)
        self.assertIsNotNone(S.explanation_cost(spied, state))

    def test_only_once(self):
        twice = board(deaths={2: "N2", 4: "N3"},
                      resurrections={2: "N4", 4: "N5"})
        self.assertIsNone(S.explanation_cost(self.world(), twice))


class TheMinstrel(SolverTest):
    """A Minion executed and the whole table goes quiet. Seat 1."""

    def world(self):
        return among("Minstrel", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather", "Zombuul")

    def test_a_minion_executed_silences_everybody_but_it(self):
        got = S.a_minstrel_silences_the_table(self.world(),
                                              board(deaths={7: "E1"}), 2)
        self.assertEqual(got[0].seats, frozenset(range(1, 9)))
        self.assertEqual(got[0].capacity, 8)
        self.assertTrue(got[0].free_for_everyone())

    def test_executing_somebody_good_does_nothing(self):
        self.assertEqual(S.a_minstrel_silences_the_table(
            self.world(), board(deaths={2: "E1"}), 2), [])

    def test_back_to_back_minions_give_two_silent_nights(self):
        """The check on the span arithmetic. Two Minions, not the Demon —
        executing that ends the game rather than silencing anybody."""
        two_minions = among("Minstrel", "Sailor", "Chambermaid", "Exorcist",
                            "Innkeeper", "Gambler", "Assassin", "Godfather",
                            "Zombuul")
        both = board(deaths={7: "E1", 6: "E2"})
        for night, expected in ((2, True), (3, True), (4, False)):
            with self.subTest(night=night):
                self.assertEqual(bool(S.a_minstrel_silences_the_table(
                    two_minions, both, night)), expected)

    def test_a_dead_minstrel_silences_nobody(self):
        self.assertEqual(S.a_minstrel_silences_the_table(
            self.world(), board(deaths={7: "E1", 0: "N2"}), 3), [])


class TheTeaLady(SolverTest):
    """Both her living neighbours good, and neither of them can die.

    Seat 3, so her neighbours are seats 2 and 4 — chosen because both are
    good here and the Demon is nowhere near her.
    """

    def world(self):
        return among("Grandmother", "Sailor", "TeaLady", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather", "Zombuul")

    def test_she_guards_the_seats_beside_her(self):
        got = S.a_tea_lady_keeps_her_neighbours(self.world(), board(), 2, 1,
                                                deaths.DEMON)
        self.assertTrue(got)
        self.assertFalse(got[0].chosen,
                         "she picks nobody, so a dead neighbour means she "
                         "was not working")

    def test_she_guards_against_everything(self):
        for kind in (deaths.DEMON, deaths.OTHER):
            with self.subTest(kind=kind):
                self.assertTrue(S.a_tea_lady_keeps_her_neighbours(
                    self.world(), board(), 2, 1, kind))

    def test_an_evil_neighbour_stops_it(self):
        beside_evil = among("Grandmother", "Godfather", "TeaLady", "Exorcist",
                            "Innkeeper", "Gambler", "Gossip", "Sailor",
                            "Zombuul")
        self.assertEqual(S.a_tea_lady_keeps_her_neighbours(
            beside_evil, board(), 2, 3, deaths.DEMON), [],
            "the Godfather is on her other side")

    def test_her_neighbours_change_as_people_die(self):
        self.assertTrue(S.a_tea_lady_keeps_her_neighbours(
            self.world(), board(deaths={1: "N2"}), 3, 0, deaths.DEMON),
            "seat 1 is beside her now that seat 2 is gone")


class TheFool(SolverTest):
    """Its first death does not take it, and that covers the gallows."""

    def world(self):
        return among("Fool", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
                     "Gambler", "Gossip", "Godfather", "Zombuul")

    def test_a_dead_fool_says_nothing(self):
        """Its first would-be death leaves no record, because nothing
        happened — so a Fool that is dead spent the free one out of
        sight. That is why the shield is marked as aimed rather than
        always on: it can explain a survival and implies nothing about a
        death."""
        got = S.a_fool_survives_once(self.world(), board(), 2, 0,
                                     deaths.DEMON)
        self.assertTrue(got[0].chosen)
        self.assertPct(S.explanation_cost(self.world(),
                                          board(deaths={0: "N2"})), 1.0, 1e-9)


# --------------------------------------------------------------------------
# Outsiders
# --------------------------------------------------------------------------

class TheGoon(SolverTest):
    """Really on whichever side chose it first, and it goes back and
    forth. Seat 2."""

    GOON = 1

    def world(self):
        return among("Grandmother", "Goon", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather", "Zombuul")

    def test_its_side_is_open_rather_than_misread(self):
        """Not the Recluse's problem. A Recluse is good and *reads* evil;
        a Goon that turned really is evil and counts for the team."""
        from botc.roles import evil_registrations
        self.assertTrue(CHARACTERS["Goon"].alignment_open)
        self.assertFalse(CHARACTERS["Recluse"].alignment_open)
        self.assertEqual(sorted(evil_registrations("Goon")), [False, True])

    def test_a_count_of_evil_beside_it_can_go_either_way(self):
        from botc.info import _possible_evil_counts
        self.assertEqual(
            _possible_evil_counts(self.world(), (self.GOON, 2), "N2"),
            {0, 1}, "the Chambermaid is not going to be evil; the Goon might")

    def test_it_drunks_whoever_pointed_at_it(self):
        got = S.a_goon_drunks_whoever_chose_it(self.world(), board(), 2)
        self.assertTrue(got)
        self.assertEqual(got[0].capacity, 1, "only the first one")
        self.assertNotIn(self.GOON, got[0].seats, "it cannot choose itself")
        self.assertNotIn(6, got[0].seats, "a Gossip chooses nobody")
        self.assertIn(3, got[0].seats, "an Exorcist does")
        self.assertIn(8, got[0].seats, "and so does the Demon")

    def test_naming_a_character_is_not_choosing_a_player(self):
        self.assertFalse(CHARACTERS["Courtier"].chooses)
        self.assertFalse(CHARACTERS["Grandmother"].chooses)
        self.assertTrue(CHARACTERS["Exorcist"].chooses)


class TheLunatic(SolverTest):
    """Thinks it is the Demon — the Drunk's machinery pointed somewhere
    new."""

    def test_it_is_handed_a_demon_rather_than_a_good_character(self):
        from botc.roles import believed_tokens
        self.assertEqual(sorted(believed_tokens("Lunatic", BMR)),
                         ["Po", "Pukka", "Shabaloth", "Zombuul"])

    def test_the_drunk_is_the_contrast(self):
        """Also handed the wrong token, and thinks it is good. Not on
        this script, which is why it is named rather than dealt."""
        from botc.roles import knows_what_it_is, thinks_it_is_evil
        self.assertFalse(knows_what_it_is("Lunatic"))
        self.assertFalse(knows_what_it_is("Drunk"))
        self.assertTrue(thinks_it_is_evil("Lunatic"))
        self.assertFalse(thinks_it_is_evil("Drunk"))

    def test_so_it_bluffs_the_way_the_demon_would(self):
        """The only good player that lies deliberately, because as far as
        it knows it has every reason to. Offered once per Demon it could
        think it is."""
        from botc.worlds import _candidates
        offered = _candidates("Chambermaid", False, "", None, None, BMR)
        self.assertEqual(sorted(t for r, t in offered if r == "Lunatic"),
                         ["Po", "Pukka", "Shabaloth", "Zombuul"])

    def test_it_is_still_good_and_still_an_outsider(self):
        from botc.roles import is_evil
        self.assertEqual(CHARACTERS["Lunatic"].team, "outsider")
        self.assertFalse(is_evil("Lunatic"))


class TheTinker(SolverTest):
    """May go at any time, at the Storyteller's whim. Seat 8."""

    TINKER = 7

    def world(self):
        return among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Tinker", "Zombuul")

    def test_it_can_go_on_any_night_with_no_trigger(self):
        got = S.a_tinker_may_go_at_any_time(self.world(), board(), 2)
        self.assertEqual(got[0].seats, frozenset({self.TINKER}))
        self.assertFalse(got[0].must_fire)

    def test_it_is_not_the_demons_doing(self):
        """Which is why a Monk would be no help: it guards against the
        Demon, and the Storyteller is not the Demon."""
        got = S.a_tinker_may_go_at_any_time(self.world(), board(), 2)
        self.assertEqual(got[0].kind, deaths.OTHER)

    def test_but_an_innkeeper_does_stop_it(self):
        self.assertTrue(S.an_innkeeper_guards_two(
            self.world(), board(), 2, self.TINKER, deaths.OTHER))

    def test_and_so_does_a_tea_lady_beside_it(self):
        beside = among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                       "Innkeeper", "Gambler", "TeaLady", "Tinker",
                       "Godfather")
        # Seat 7 is the Tea Lady; her neighbours are 6 and 8, both good.
        self.assertTrue(S.a_tea_lady_keeps_her_neighbours(
            beside, board(), 2, self.TINKER, deaths.OTHER))


class TheMoonchild(SolverTest):
    """Its pick lands the night after it learns it died. Seat 9."""

    CHILD = 8

    def world(self):
        return among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather",
                     "Moonchild")

    def test_its_pick_lands_the_night_after_it_learns(self):
        died = board(deaths={self.CHILD: "N2"})
        self.assertEqual(S.a_moonchild_takes_somebody_with_it(
            self.world(), died, 2), [], "not the same night")
        self.assertTrue(S.a_moonchild_takes_somebody_with_it(
            self.world(), died, 3), "the night after")
        self.assertEqual(S.a_moonchild_takes_somebody_with_it(
            self.world(), died, 4), [], "and not the one after that")

    def test_dying_in_daylight_works_the_same_way(self):
        self.assertTrue(S.a_moonchild_takes_somebody_with_it(
            self.world(), board(deaths={self.CHILD: "E2"}), 3))

    def test_only_a_good_target_dies(self):
        got = S.a_moonchild_takes_somebody_with_it(
            self.world(), board(deaths={self.CHILD: "N2"}), 3)
        self.assertNotIn(7, got[0].seats, "the Godfather is not good")
        self.assertIn(2, got[0].seats)

    def test_picking_an_evil_one_does_nothing_so_it_may_not_fire(self):
        got = S.a_moonchild_takes_somebody_with_it(
            self.world(), board(deaths={self.CHILD: "N2"}), 3)
        self.assertFalse(got[0].must_fire)


# --------------------------------------------------------------------------
# Minions
# --------------------------------------------------------------------------

class TheGodfather(SolverTest):
    """An Outsider lost in daylight, and it kills tonight. Seat 8."""

    OUTSIDER_AT = ("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                   "Innkeeper", "Gambler", "Tinker", "Godfather", "Zombuul")

    def test_it_is_the_first_setup_changer_with_a_choice(self):
        from botc.worlds import _bags
        shapes = {(c["townsfolk"], c["outsider"]) for _p, c in _bags(9, BMR)}
        self.assertIn((5, 2), shapes, "left alone")
        self.assertIn((6, 1), shapes, "one Outsider fewer")
        self.assertIn((4, 3), shapes, "one more")

    def test_an_outsider_lost_in_daylight_makes_it_kill(self):
        got = S.a_godfather_answers_an_outsider(
            among(*self.OUTSIDER_AT), board(deaths={6: "E2"}), 3)
        self.assertTrue(got)
        self.assertTrue(got[0].must_fire)
        self.assertEqual(got[0].kind, deaths.OTHER, "not the Demon's kill")

    def test_an_outsider_lost_at_night_does_not(self):
        """A clean piece of deduction for the table."""
        self.assertEqual(S.a_godfather_answers_an_outsider(
            among(*self.OUTSIDER_AT), board(deaths={6: "N2"}), 3), [])

    def test_whether_the_seat_was_an_outsider_depends_on_the_world(self):
        """Seat 7 holds the Gossip here, so nothing triggers."""
        self.assertEqual(S.a_godfather_answers_an_outsider(
            among(*HONEST), board(deaths={6: "E2"}), 3), [])


class TheAssassin(SolverTest):
    """Once per game, and nothing stops it."""

    def test_it_is_marked_as_unstoppable(self):
        with_assassin = among("Grandmother", "Sailor", "Chambermaid",
                              "Exorcist", "Innkeeper", "Gambler", "Gossip",
                              "Assassin", "Zombuul")
        got = S.an_assassin_kills_through_anything(with_assassin, board(), 2)
        self.assertTrue(got[0].unstoppable)
        self.assertEqual(got[0].kind, deaths.OTHER, "not the Demon's kill")

    def test_it_goes_through_a_shield_nothing_else_can(self):
        """A Tea Lady's neighbour cannot die while she is working, and
        with nothing here able to impair her that death is impossible —
        unless the Assassin did it.

        Chosen deliberately: a dead Sailor would *not* show this, because
        the Sailor drunking itself is a cheaper story than either.
        """
        # No Innkeeper, Sailor, Courtier or Goon anywhere in this
        # lineup, because every one of those could have stopped her —
        # which is the whole point of the comparison.
        seats = ("Grandmother", "TeaLady", "Chambermaid", "Minstrel",
                 "Pacifist", "Gambler", "Gossip", "{minion}", "Zombuul")
        with_one = among(*[s.format(minion="Assassin") for s in seats])
        without = among(*[s.format(minion="Mastermind") for s in seats])
        # Seat 2 is the Tea Lady; seats 1 and 3 are her good neighbours.
        state = board(deaths={2: "N2"})
        self.assertIsNone(S.explanation_cost(without, state))
        self.assertPct(S.explanation_cost(with_one, state),
                       S.ASSASSIN_STRIKE_PENALTY, 1e-9)


class TheMastermind(SolverTest):
    """The extra day it buys. See also `TheMastermindBuysOneDay`."""

    def world(self):
        # A Shabaloth rather than the Zombuul this used to be. A Zombuul
        # survives its first execution, so "the board runs on too far"
        # below was not too far at all once that was modelled — it was
        # the Zombuul carrying on, which is legal.
        return among("Grandmother", "Sailor", "Shabaloth", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Mastermind", "Tinker")

    def test_it_buys_one_more_day_after_the_demon_is_executed(self):
        """Nobody inherits — there is simply no Demon after this — so the
        lineage ends rather than continuing."""
        self.assertIsNotNone(S.explanation_cost(
            self.world(), board(deaths={2: "E2"}, quiet_nights={3})))

    def test_and_only_one(self):
        self.assertIsNone(S.explanation_cost(
            self.world(), board(deaths={2: "E2"}, quiet_nights={3, 4, 5})),
            "the board runs on too far for one extra day")

    def test_the_hint_asks_whether_they_were_the_demon_when_they_went(self):
        """Not who the Demon is now — in these worlds nobody is."""
        got = S.mastermind_days(board(deaths={2: "E2"}, quiet_nights={3},
                                      reads={2: 3}))
        self.assertTrue(got)
        self.assertEqual((got[0]["day"], got[0]["seat"]), (3, 2))

    def test_it_says_nothing_on_a_script_without_one(self):
        self.assertEqual(S.mastermind_days(trouble_brewing(deaths={2: "E2"})),
                         [])

    def test_an_execution_somebody_walked_away_from_is_not_one(self):
        self.assertEqual(S.mastermind_days(board(executions={2: 1})), [])


# --------------------------------------------------------------------------
# Demons
# --------------------------------------------------------------------------

class TheZombuul(SolverTest):
    """Kills only after a day when nobody died, and is dead on the board
    before it is dead in fact. Seat 9."""

    ZOMBUUL = 8

    def test_it_kills_after_a_quiet_day(self):
        self.assertTrue(S.a_zombuul_kills_on_a_quiet_day(
            among(*HONEST), board(), 2))

    def test_any_daylight_death_stops_it(self):
        """An execution, a Slayer shot, a Tinker going of its own accord
        — all the same to it."""
        for phase in ("E1", "D1"):
            with self.subTest(phase=phase):
                self.assertEqual(S.a_zombuul_kills_on_a_quiet_day(
                    among(*HONEST), board(deaths={2: phase}), 2), [])

    def test_a_death_in_the_night_does_not_stop_it(self):
        self.assertTrue(S.a_zombuul_kills_on_a_quiet_day(
            among(*HONEST), board(deaths={2: "N2"}), 3))

    def test_it_carries_on_after_its_first_death(self):
        """Recorded dead, still killing. Only really gone the second
        time."""
        once = board(deaths={self.ZOMBUUL: "N2"})
        twice = board(deaths={self.ZOMBUUL: ("N2", "N4")})
        self.assertTrue(S.a_zombuul_kills_on_a_quiet_day(
            among(*HONEST), once, 3))
        self.assertEqual(S.a_zombuul_kills_on_a_quiet_day(
            among(*HONEST), twice, 5), [])


class ThePukka(SolverTest):
    """Poisons on one night, and that poison kills on the next. Seat 9."""

    def world(self):
        return among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather", "Pukka")

    def test_it_does_not_kill_on_the_first_night(self):
        """It starts a night earlier than any other Demon, and that first
        night is only the poisoning."""
        self.assertEqual(S.a_pukka_kills_what_it_poisoned(
            self.world(), board(), 1), [])

    def test_its_victim_had_to_be_the_seat_it_poisoned(self):
        got = S.a_pukka_kills_what_it_poisoned(self.world(), board(), 2)
        self.assertEqual(got[0].victim_impaired_at, 1,
                         "a demand on the night before")

    def test_it_can_only_have_poisoned_somebody_alive_at_the_time(self):
        got = S.a_pukka_kills_what_it_poisoned(
            self.world(), board(deaths={2: "N2"}), 4)
        self.assertNotIn(2, got[0].seats)


class TheShabaloth(SolverTest):
    """Two a night, and it may bring one of them back. Seat 9."""

    def world(self):
        return among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather",
                     "Shabaloth")

    def test_it_kills_twice(self):
        self.assertEqual(
            S.a_shabaloth_kills_twice(self.world(), board(), 2)[0].capacity, 2)

    def test_so_two_bodies_in_a_night_are_its_own_doing(self):
        self.assertIsNotNone(S.explanation_cost(
            self.world(), board(deaths={2: "N2", 4: "N2"})))

    def test_either_kill_can_be_sunk_into_a_corpse(self):
        """So the table may only ever see one body."""
        got = S.a_shabaloth_kills_twice(self.world(), board(), 2)
        self.assertEqual(got[0].seats, frozenset(range(9)))


class ThePo(SolverTest):
    """May take nobody, and then takes three. Seat 9."""

    def world(self):
        return among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                     "Innkeeper", "Gambler", "Gossip", "Godfather", "Po")

    def test_it_may_decline(self):
        self.assertFalse(
            S.a_po_kills_none_or_three(self.world(), board(), 2)[0].must_fire)

    def test_it_offers_three_and_the_search_may_take_fewer(self):
        """A capacity is a ceiling, not a demand.

        This used to assert one after a night where somebody died, on the
        reasoning that a Po which killed cannot have been charging. The
        reasoning was right and the *test* was wrong: whether the **Po**
        killed cannot be read off whether anybody died. A Tinker that
        simply went, an Acrobat that fell, a Gambler that guessed wrong —
        all die with the Po charging quietly beside them.

        A board with one of those on the charging night offered a
        capacity of one against a record of three, and had no legal world
        at all. So the rule offers three either way and the search takes
        what it needs.
        """
        after_quiet = S.a_po_kills_none_or_three(
            self.world(), board(quiet_nights={2}), 3)
        after_a_kill = S.a_po_kills_none_or_three(
            self.world(), board(deaths={2: "N2"}), 3)
        self.assertEqual(after_quiet[0].capacity, 3)
        self.assertEqual(after_a_kill[0].capacity, 3)
        for got in (after_quiet, after_a_kill):
            with self.subTest(offers=len(got)):
                self.assertEqual(len(got), 1)   # one rule, one answer


class OnlyOneDemonAnswersPerWorld(SolverTest):
    """Four Demons on the script and each kills differently, so exactly
    one of the rules speaks for any given world."""

    def test_the_rules_do_not_overlap(self):
        for demon in ("Zombuul", "Pukka", "Shabaloth", "Po"):
            with self.subTest(demon=demon):
                w = among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                          "Innkeeper", "Gambler", "Gossip", "Godfather", demon)
                # The kill that is owed each night. A Pukka has a second
                # telling of the same kill — a night late, after a night
                # it was drunk — which shares the name and is never owed.
                firing = [c for c in deaths.causes_on(w, board(), 3)
                          if c.name == "Demon" and not c.also_impaired]
                self.assertEqual(len(firing), 1, f"{demon} gave {firing}")


if __name__ == "__main__":
    unittest.main()


class TheDemonsFirstNightIsOpen(SolverTest):
    """Told its Minions and its bluffs — and whether a Chambermaid counts
    that depends on whose table it is.

    Three readings in turn. A Demon's `nights` says "other", and reading
    that single word had every Demon asleep on night one: a Chambermaid
    who counted two beside a Demon and a Courtier made a board with no
    legal world. Reading the `wake` set instead had every Demon awake
    for certain, which does the same to a Chambermaid who counted *one*.

    The table's ruling (02.10.2026) is that it does not count — being
    told who your Minions are is not your ability, the same as a Baron —
    and that only the Pukka does, because it already chooses. Other
    Storytellers count it. So the solver calls it open and keeps both.
    """

    def board(self):
        from botc.info import GameState
        from botc import scripts
        claims = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        return GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                         claims={i: r for i, r in enumerate(claims)})

    def world(self, demon="Po", minion="Godfather", believes=None):
        from botc.worlds import World
        return World(("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                      "Innkeeper", "Gambler", "Gossip", minion, demon),
                     believes or (None,) * 9)

    def test_it_is_not_its_ability_and_not_settled_either(self):
        from botc import waking
        for demon in ("Po", "Zombuul", "Shabaloth"):
            with self.subTest(demon=demon):
                w = self.world(demon)
                self.assertFalse(waking.woke(w, self.board(), 8, 1))
                self.assertTrue(waking.uncertain(w, self.board(), 8, 1))

    def test_both_counts_are_legal_beside_one(self):
        """The Sailor woke; the Po may or may not be counted."""
        from botc import waking
        got = waking.possible_counts(self.world(), self.board(), [1, 8], 1)
        self.assertEqual(got, {1, 2})

    def test_the_pukka_chooses_on_night_one_and_counts_for_certain(self):
        from botc import waking
        w = self.world("Pukka")
        self.assertTrue(waking.woke(w, self.board(), 8, 1))
        self.assertFalse(waking.uncertain(w, self.board(), 8, 1))
        self.assertEqual(
            waking.possible_counts(w, self.board(), [1, 8], 1), {2})

    def test_from_the_second_night_a_demon_simply_wakes(self):
        from botc import waking
        self.assertTrue(waking.woke(self.world("Po"), self.board(), 8, 2))

    def test_but_an_exorcist_does_not_wake_on_the_first(self):
        """The one that actually means "not the first night", and the
        reason this cannot simply say everybody wakes."""
        from botc import waking
        self.assertFalse(waking.woke(self.world(), self.board(), 3, 1))
        self.assertTrue(waking.woke(self.world(), self.board(), 3, 2))
        self.assertFalse(waking.uncertain(self.world(), self.board(), 3, 1))

    def test_and_every_night_still_includes_the_first(self):
        """The first fix read the `wake` set alone, which does not list
        "first" for an every-night character — so every Empath and
        Poisoner slept through night one instead. A worse bug than the
        one being fixed."""
        from botc import waking
        for seat, role in ((1, "Sailor"), (2, "Chambermaid")):
            with self.subTest(role=role):
                self.assertTrue(
                    waking.woke(self.world(), self.board(), seat, 1))


class ALunaticCountsLikeTheDemonItThinksItIs(SolverTest):
    """Table ruling (02.10.2026): choosing who it thinks it kills is a
    Lunatic's ability, and a Chambermaid counts it.

    The rule said so and a list beside it said the opposite — `Lunatic`
    sat in `SHOWN_NOT_ACTING`, and the list is what `possible_counts`
    asks. So a Chambermaid beside one never counted it.
    """

    def setUp(self):
        from botc.info import GameState
        from botc import scripts
        from botc.worlds import World
        claims = ["Grandmother", "Sailor", "Chambermaid", "Minstrel",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        self.state = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                               claims={i: r for i, r in enumerate(claims)})
        self.World = World

    def world(self, thinks, demon="Po"):
        believes = [None] * 9
        believes[7] = thinks
        return self.World(("Grandmother", "Sailor", "Chambermaid",
                           "Minstrel", "Innkeeper", "Gambler", "Gossip",
                           "Lunatic", demon), tuple(believes))

    def test_it_counts_from_the_second_night(self):
        from botc import waking
        got = waking.possible_counts(self.world("Po"), self.state, [3, 7], 2)
        self.assertEqual(got, {1})

    def test_one_that_thinks_it_is_the_pukka_counts_on_the_first(self):
        from botc import waking
        got = waking.possible_counts(self.world("Pukka", "Pukka"),
                                     self.state, [3, 7], 1)
        self.assertEqual(got, {1})

    def test_one_that_thinks_it_is_the_po_is_open_on_the_first(self):
        from botc import waking
        got = waking.possible_counts(self.world("Po"), self.state, [3, 7], 1)
        self.assertEqual(got, {0, 1})

    def test_with_no_token_recorded_it_follows_the_real_demon(self):
        from botc import waking
        got = waking.possible_counts(self.world(None, "Pukka"), self.state,
                                     [3, 7], 1)
        self.assertEqual(got, {1})

    def test_a_zombuul_lunatic_sleeps_after_a_day_death(self):
        from botc.info import GameState
        from botc import scripts, waking
        state = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                          claims=dict(self.state.claims),
                          deaths={0: "D1"}, executions={1: 0})
        got = waking.possible_counts(self.world("Zombuul", "Zombuul"),
                                     state, [3, 7], 2)
        self.assertEqual(got, {0})


class AGodfatherWakesToKillAndNotOtherwise(SolverTest):
    """Night one for the Outsiders, then only after one died in daylight.

    The catalogue said "every", so a Chambermaid beside a Godfather on an
    ordinary night counted one too many.
    """

    def state(self, **more):
        from botc.info import GameState
        from botc import scripts
        claims = ["Grandmother", "Sailor", "Chambermaid", "Minstrel",
                  "Innkeeper", "Gambler", "Tinker", "Gossip", "Moonchild"]
        return GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                         claims={i: r for i, r in enumerate(claims)}, **more)

    def world(self):
        from botc.worlds import World
        return World(("Grandmother", "Sailor", "Chambermaid", "Minstrel",
                      "Innkeeper", "Gambler", "Tinker", "Godfather", "Po"),
                     (None,) * 9)

    def test_the_first_night(self):
        from botc import waking
        self.assertTrue(waking.woke(self.world(), self.state(), 7, 1))

    def test_not_on_an_ordinary_night(self):
        from botc import waking
        self.assertFalse(waking.woke(self.world(), self.state(), 7, 2))

    def test_after_an_outsider_was_executed(self):
        from botc import waking
        state = self.state(deaths={6: "D1"}, executions={1: 6})
        self.assertTrue(waking.woke(self.world(), state, 7, 2))
        self.assertFalse(waking.woke(self.world(), state, 7, 3))

    def test_not_after_a_townsfolk_was(self):
        from botc import waking
        state = self.state(deaths={5: "D1"}, executions={1: 5})
        self.assertFalse(waking.woke(self.world(), state, 7, 2))

    def test_an_outsider_lost_at_night_wakes_nobody(self):
        from botc import waking
        state = self.state(deaths={6: "N2"})
        self.assertFalse(waking.woke(self.world(), state, 7, 3))


class AProfessorIsWokenUntilItRaisesSomebody(SolverTest):
    """ "Once per game, at night*" — woken from the second night and free
    to decline, like the Assassin.

    It said never, because no row records the night it was used. What the
    board does record is somebody coming back to life.
    """

    def state(self, **more):
        from botc.info import GameState
        from botc import scripts
        claims = ["Grandmother", "Sailor", "Chambermaid", "Professor",
                  "Innkeeper", "Gambler", "Tinker", "Gossip", "Moonchild"]
        return GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                         claims={i: r for i, r in enumerate(claims)}, **more)

    def world(self, demon="Po"):
        from botc.worlds import World
        return World(("Grandmother", "Sailor", "Chambermaid", "Professor",
                      "Innkeeper", "Gambler", "Tinker", "Godfather", demon),
                     (None,) * 9)

    def test_not_the_first_night_and_every_one_after(self):
        from botc import waking
        got = [waking.woke(self.world(), self.state(), 3, n)
               for n in (1, 2, 3, 4)]
        self.assertEqual(got, [False, True, True, True])

    def test_it_sleeps_once_somebody_came_back(self):
        from botc import waking
        state = self.state(deaths={0: "N2"}, resurrections={0: "N3"})
        got = [waking.woke(self.world(), state, 3, n) for n in (2, 3, 4)]
        self.assertEqual(got, [True, True, False])
        self.assertFalse(waking.uncertain(self.world(), state, 3, 4))

    def test_unless_a_shabaloth_could_have_done_it(self):
        from botc import waking
        state = self.state(deaths={0: "N2"}, resurrections={0: "N3"})
        w = self.world("Shabaloth")
        self.assertTrue(waking.uncertain(w, state, 3, 4))
        self.assertEqual(waking.possible_counts(w, state, [1, 3], 4), {1, 2})


class APukkaPoisonsBeforeItKills(SolverTest):
    """And nothing provided that poison, so every Pukka board was
    impossible.

    The kill rule demands the victim was poisoned the night before —
    `victim_impaired_at=night - 1` — which was written when the Pukka
    went in and never paired with a source. It went unnoticed because a
    board only becomes impossible once a death is recorded on the right
    night, and no test or corpus board had one.

    Found by teaching the simulator to play Bad Moon Rising properly:
    once the Pukka killed the way it really does, the solver rejected the
    result.
    """

    def sources(self, night):
        from botc import impairment
        from botc.info import GameState
        from botc import scripts
        from botc.worlds import World
        claims = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        state = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                          claims={i: r for i, r in enumerate(claims)})
        world = World(("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                       "Innkeeper", "Gambler", "Gossip", "Godfather",
                       "Pukka"), (None,) * 9)
        return {s.name: sorted(s.seats)
                for s in impairment.sources_on(world, state, night)}

    def test_it_provides_the_poison_its_kill_demands(self):
        self.assertIn("Pukka", self.sources(1))

    def test_from_the_first_night(self):
        """It poisons before anybody else acts, which is why it is the
        one Demon that does something on night one."""
        self.assertIn("Pukka", self.sources(1))
        self.assertIn("Pukka", self.sources(2))

    def test_and_it_can_reach_anybody_alive(self):
        self.assertEqual(len(self.sources(1)["Pukka"]), 9)

    def test_which_is_why_it_has_to_be_priced(self):
        """The first version was free, and a free source reaching the
        whole table excuses *any* reading at no cost — which it duly did,
        quietly making a false Chambermaid reading cost nothing.

        Caught by an audit test written weeks earlier for a different
        reason: it asserts that explaining away something false costs
        something. The sources that are genuinely free — a Sweetheart, a
        No Dashii — are free because they reach one seat or two that
        nobody chose.
        """
        import botc.solver as S
        from botc import impairment
        from botc.info import GameState
        from botc import scripts
        from botc.worlds import World
        claims = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        state = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                          claims={i: r for i, r in enumerate(claims)})
        world = World(("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                       "Innkeeper", "Gambler", "Gossip", "Godfather",
                       "Pukka"), (None,) * 9)
        pukka = next(s for s in impairment.sources_on(world, state, 1)
                     if s.name == "Pukka")
        self.assertFalse(pukka.free_for_everyone(),
                         "a table-wide source must pay to land")
        # Nobody on this board dies the next night, so every seat is a
        # guess. The one that does die is another matter: see
        # `ThePukkasPoisonIsNotLuck`.
        for seat in range(8):
            self.assertPct(pukka.price(seat), S.POISON_HIT_PENALTY, 1e-9)

    def test_and_a_false_reading_still_costs_something(self):
        import botc.solver as S
        from botc.info import ChambermaidInfo, GameState
        from botc import scripts
        from botc.worlds import World
        claims = ["Grandmother", "Sailor", "Chambermaid", "Courtier",
                  "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"]
        world = World(("Grandmother", "Sailor", "Chambermaid", "Courtier",
                       "Innkeeper", "Gambler", "Gossip", "Tinker", "Pukka"),
                      (None,) * 9)

        def cost(count):
            state = GameState(
                n_players=9, script=scripts.BAD_MOON_RISING,
                claims={i: r for i, r in enumerate(claims)},
                infos=[ChambermaidInfo(1, 2, a=0, b=1, count=count)])
            return S.explanation_cost(world, state)

        self.assertPct(cost(2), 1.0, 1e-9)      # true: nothing to explain
        self.assertLess(cost(0), 1.0)           # false: somebody must have
    


class TheMastermindBuysOneDay(SolverTest):
    """"If the Demon dies by execution (ending the game), play for 1 more
    day." Each half of that sentence is a condition the solver checks.

    Built with the wiki's page open (29.09.2026): execution only, the
    Mastermind alive, and only when the game would otherwise have ended —
    a Scarlet Woman who qualifies takes the Demon instead.
    """

    MIX = scripts.from_ids("A mixed bag", [
        "imp", "zombuul", "mastermind", "scarletwoman", "poisoner",
        "godfather", "grandmother", "sailor", "chambermaid", "exorcist",
        "innkeeper", "gambler", "gossip", "courtier", "tealady", "minstrel",
        "fool", "lunatic", "goon", "moonchild", "tinker"])
    TOWN = ("Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
            "Gambler", "Gossip")

    def world(self, *evil):
        return World(tuple(evil) + self.TOWN[:9 - len(evil)],
                     (None,) * 9)

    def board(self, **kw):
        base = dict(n_players=9, script=self.MIX, deaths={0: ("D2",)},
                    executions={2: 0}, days_done={1, 2}, quiet_nights={3})
        base.update(kw)
        return GameState(**base)

    def test_an_executed_demon_and_the_game_goes_on(self):
        cost, changes = S.best_story(self.world("Imp", "Mastermind"),
                                     self.board())
        self.assertIsNotNone(cost)
        self.assertTrue(any(S.is_mastermind_marker(c) for c in changes))

    def test_not_without_a_mastermind(self):
        self.assertIsNone(S.explanation_cost(
            self.world("Imp", "Poisoner"), self.board()))

    def test_only_one_more_day(self):
        self.assertIsNone(S.explanation_cost(
            self.world("Imp", "Mastermind"),
            self.board(quiet_nights={3, 4}, days_done={1, 2, 3})))

    def test_a_slayer_shot_is_not_an_execution(self):
        self.assertIsNone(S.explanation_cost(
            self.world("Imp", "Mastermind"), self.board(executions={})))

    def test_the_mastermind_has_to_be_alive(self):
        self.assertIsNone(S.explanation_cost(
            self.world("Imp", "Mastermind"),
            self.board(deaths={0: ("D2",), 1: ("D1",)},
                       executions={1: 1, 2: 0})))

    def test_a_scarlet_woman_comes_first(self):
        """She takes the Demon for free; the Mastermind's day is still
        possible, but only if she was not working, and that costs."""
        world = self.world("Imp", "Mastermind", "ScarletWoman")
        viable = []
        cost, changes = S.best_story(world, self.board(), viable=viable)
        self.assertEqual([c.role for c in changes], ["Imp"])
        marked = [c for c, ch in viable
                  if any(S.is_mastermind_marker(x) for x in ch)]
        self.assertTrue(marked)
        self.assertLess(max(marked), cost)


class AZombuulSurvivesItsFirstExecution(SolverTest):
    """The first time it dies it does not. Reading that death as final
    left nobody to inherit, and every board with an executed Zombuul was
    impossible."""

    def test_executed_and_still_killing(self):
        world = World(("Zombuul", "Godfather", "Grandmother", "Sailor",
                       "Chambermaid", "Exorcist", "Innkeeper", "Gambler",
                       "Gossip"), (None,) * 9)
        state = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                          deaths={0: ("D1",), 5: ("N3",)}, executions={1: 0},
                          days_done={1, 2}, quiet_nights={2})
        self.assertIsNotNone(S.explanation_cost(world, state))
        # The second execution is real, and with nobody to take over the
        # game is over — so a board that goes on is impossible.
        later = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                          deaths={0: ("D1", "D3"), 5: ("N3",)},
                          executions={1: 0, 3: 0}, days_done={1, 2, 3},
                          quiet_nights={2, 4})
        self.assertIsNone(S.explanation_cost(world, later))


class FoundByTheWiderSweep(SolverTest):
    """Pinned without the simulator: three solver faults the three
    hundred game sweep turned up (29.09.2026)."""

    def test_a_tea_lady_keeps_a_wrong_gambler_alive(self):
        from botc.info import GamblerGuess
        # Gambler at 0 beside the Tea Lady at 1, whose other neighbour is
        # good too. It names the Tea Lady as the Minstrel — wrong — and
        # lives, because she was working.
        world = World(("Gambler", "TeaLady", "Innkeeper", "Grandmother",
                       "Gossip", "Godfather", "Po", "Exorcist", "Sailor"),
                      (None,) * 9)
        guess = GamblerGuess(2, 0, 0, target=1, role="Minstrel")
        state = GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                          infos=[guess], days_done={1}, quiet_nights={2})
        self.assertTrue(guess.holds(world, state, None))
        # Not beside her, and nothing else could have kept it alive — no
        # Innkeeper either, which could have picked it.
        apart = World(("Grandmother", "TeaLady", "Chambermaid", "Gambler",
                       "Gossip", "Godfather", "Po", "Exorcist", "Sailor"),
                      (None,) * 9)
        far = GamblerGuess(2, 3, 0, target=1, role="Minstrel")
        self.assertFalse(far.holds(apart, state, None))

    def test_the_assassin_sleeps_through_night_one(self):
        """"At night*": on the first night it is only shown its team."""
        from botc.waking import woke
        world = World(("Assassin", "Grandmother", "Sailor", "Chambermaid",
                       "Exorcist", "Innkeeper", "Gambler", "Gossip",
                       "Zombuul"), (None,) * 9)
        state = GameState(n_players=9, script=scripts.BAD_MOON_RISING)
        self.assertFalse(woke(world, state, 0, 1))
        self.assertTrue(woke(world, state, 0, 2))


class ThePukkaTakesItsTurnByTheFlowchart(SolverTest):
    """The simulator's Pukka, step by step (table ruling, 02.10.2026:
    the flowchart by Not_Quite_Vertical is what counts).

    Three things were off. Its poison ended at dusk, so the player it
    killed was sober again on the night the poison came for them. It
    shared one table with the Poisoner's, and whichever was written
    second was lost. And an Exorcist that named it saved yesterday's
    victim while the Pukka went on to choose a new one — the wrong way
    round on both counts.
    """

    ROLES = ["Exorcist", "Sailor", "Chambermaid", "Gambler", "Innkeeper",
             "Fool", "Tinker", "Godfather", "Pukka"]

    def deal(self, marked=None):
        import simulate
        d = simulate.Deal(self.ROLES, [None] * 9, None, {}, {}, None)
        d.script = scripts.BAD_MOON_RISING
        d.pukka_owner = 8
        d.pukka_poisoned = marked
        return d

    def turn(self, d, night, seed=0):
        import random
        import simulate
        simulate._pukka_token_carries(d, night)
        return simulate._demon_kills(d, night, random.Random(seed))

    def test_the_marked_player_is_still_poisoned_when_it_comes_due(self):
        """A Sailor cannot die — unless it is the one that was poisoned."""
        import simulate
        for victim in (1, 5):                    # the Sailor, the Fool
            with self.subTest(victim=self.ROLES[victim]):
                d = self.deal(marked=victim)
                simulate._pukka_token_carries(d, 2)
                self.assertIn(victim, simulate.droisoned_at(d, 2))
                self.assertEqual(self.turn(d, 2), [victim])
                # What its death sets off is poisoned still.
                self.assertIn(victim, simulate.droisoned_at(d, 2))

    def test_the_new_poison_is_not_there_before_its_turn(self):
        import simulate
        d = self.deal()
        simulate._pukka_token_carries(d, 1)
        self.assertEqual(simulate.droisoned_at(d, 1), set())
        self.turn(d, 1)
        self.assertEqual(simulate.droisoned_at(d, 1), {d.pukka_marks[1]})

    def test_one_that_was_protected_is_healthy_again(self):
        """Guarded by a sober Innkeeper: alive, and the token is gone."""
        import simulate
        for seed in range(40):
            d = self.deal(marked=3)
            d.innkeeper_guarded[2] = (3, 6)
            got = self.turn(d, 2, seed)
            fresh = d.pukka_marks.get(2)
            with self.subTest(seed=seed, fresh=fresh):
                if fresh == 4:
                    # The Innkeeper was poisoned first — steps 2 and 4 —
                    # so it guards nobody.
                    self.assertEqual(got, [3])
                else:
                    self.assertEqual(got, [])
                    self.assertNotIn(3, simulate.droisoned_at(d, 2))
                self.assertEqual(d.pukka_poisoned, fresh)

    def test_an_exorcist_stops_the_choosing_not_the_dying(self):
        d = self.deal(marked=3)
        d.exorcised[2] = 8
        self.assertEqual(self.turn(d, 2), [3])
        self.assertEqual(d.pukka_history[2], (3, None))
        self.assertIsNone(d.pukka_poisoned)
        # And the night after is the quiet one: no token to come due.
        self.assertEqual(self.turn(d, 3), [])
        self.assertIsNotNone(d.pukka_poisoned)

    def test_a_poisoned_pukka_leaves_its_token_where_it_is(self):
        """No attack, no new poison — and the old one rests meanwhile."""
        import simulate
        d = self.deal(marked=3)
        d.poisoned[2] = 8                        # somebody got to the Pukka
        self.assertEqual(self.turn(d, 2), [])
        self.assertEqual(d.pukka_poisoned, 3)
        self.assertNotIn(3, simulate.droisoned_at(d, 2))
        # Sober again, it attacks the one it marked two nights ago.
        self.assertEqual(self.turn(d, 3), [3])

    def test_a_poisoner_beside_it_does_not_lose_its_own(self):
        import simulate
        d = self.deal()
        d.poisoned[1] = 0
        self.turn(d, 1)
        fresh = d.pukka_marks[1]
        self.assertEqual(simulate.droisoned_at(d, 1), {0, fresh})

    def test_the_token_goes_with_the_pukka(self):
        import simulate
        d = self.deal(marked=3)
        d.deaths[8] = "E1"
        simulate._pukka_token_carries(d, 2)
        self.assertIsNone(d.pukka_poisoned)
        self.assertEqual(simulate.droisoned_at(d, 2), set())


class ThePukkasPoisonIsNotLuck(SolverTest):
    """Whoever dies tomorrow night was the one it chose.

    The kill demands its victim was poisoned the night before, and the
    poison was priced like the Poisoner's — as though it had to get
    lucky. So every Pukka kill cost its world 0.35, and the true world of
    a Pukka game weighed a fifth of any other Demon's.
    """

    CLAIMS = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
              "Innkeeper", "Fool", "Gossip", "Tinker", "Moonchild"]

    def world(self):
        return World(("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                      "Innkeeper", "Fool", "Gossip", "Godfather", "Pukka"),
                     (None,) * 9)

    def state(self, deaths):
        return GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         deaths=deaths)

    def test_a_plain_kill_costs_nothing(self):
        got = S.explanation_cost(self.world(), self.state({6: "N2"}))
        self.assertEqual(got, 1.0)

    def test_nor_do_three_in_a_row(self):
        got = S.explanation_cost(
            self.world(), self.state({6: "N2", 3: "N3", 2: "N4"}))
        self.assertEqual(got, 1.0)

    def test_a_fool_it_poisoned_dies_and_that_is_free_too(self):
        """Still poisoned on the night the poison comes due, so the
        Fool's first death is a real one."""
        got = S.explanation_cost(self.world(), self.state({5: "N2"}))
        self.assertEqual(got, 1.0)

    def test_poison_on_anybody_else_is_still_a_guess(self):
        from botc import impairment
        state = self.state({6: "N2"})
        pukka = [s for s in impairment.sources_on(self.world(), state, 1)
                 if s.name == "Pukka"][0]
        self.assertEqual(pukka.price(6), 1.0)
        self.assertEqual(pukka.price(2), S.POISON_HIT_PENALTY)
        self.assertFalse(pukka.unavoidable())

    def test_the_token_is_free_on_tonights_dead_and_a_guess_on_the_rest(self):
        """It reached only the dead until 03.10.2026. Somebody kept alive
        carried it into the night all the same — see
        `test_an_innkeeper_under_the_token_and_kept_alive` below."""
        from botc import impairment
        state = self.state({6: "N2"})
        token = {s.name: s for s in
                 impairment.sources_on(self.world(), state, 2)}["Pukka's token"]
        self.assertEqual(token.price(6), 1.0)
        self.assertEqual(token.price(2), S.POISON_HIT_PENALTY)
        self.assertEqual(token.capacity, 1, "one token")
        self.assertFalse(token.unavoidable())
        quiet = {s.name: s for s in
                 impairment.sources_on(self.world(), state, 3)}["Pukka's token"]
        self.assertEqual(quiet.price(2), S.POISON_HIT_PENALTY)
        self.assertNotIn("Pukka's token", {
            s.name for s in impairment.sources_on(self.world(), state, 1)},
            "nothing is carried into the first night")


class AnExorcistAndAPukka(SolverTest):
    """Naming the Pukka stops it choosing, not what it chose last night.

    So yesterday's victim still dies and the quiet night is the one
    *after* (the flowchart, steps 1 and 3 to 5). The shield sat on the
    night the Exorcist chose, as it does for every other Demon — which
    is a night late for a Pukka.

    No Sailor, Innkeeper, Fool or Tea Lady on this board, so nothing
    else is on hand to explain a quiet night.
    """

    CLAIMS = ["Grandmother", "Gambler", "Chambermaid", "Exorcist", "Gossip",
              "Courtier", "Professor", "Tinker", "Moonchild"]

    def cost(self, rows, demon="Pukka"):
        from botc.info import ExorcistChoice
        world = World(("Grandmother", "Gambler", "Chambermaid", "Exorcist",
                       "Gossip", "Courtier", "Professor", "Godfather",
                       demon), (None,) * 9)
        state = GameState(
            n_players=9, script=scripts.BAD_MOON_RISING,
            claims={i: r for i, r in enumerate(self.CLAIMS)},
            deaths={6: "N2", 2: "N4"}, quiet_nights={3},
            infos=[ExorcistChoice(night, 3, target=who)
                   for night, who in rows])
        return S.explanation_cost(world, state)

    def test_named_on_the_second_night_the_third_is_quiet(self):
        self.assertEqual(self.cost([(2, 8), (3, 0)]), 1.0)

    def test_named_on_the_quiet_night_itself_explains_nothing(self):
        got = self.cost([(2, 0), (3, 8)])
        self.assertTrue(got is None or got < 1.0)

    def test_for_any_other_demon_it_is_the_night_it_was_named(self):
        """A Zombuul rather than a Po, which may simply choose nobody."""
        self.assertEqual(self.cost([(2, 0), (3, 8)], demon="Zombuul"), 1.0)
        got = self.cost([(2, 8), (3, 0)], demon="Zombuul")
        self.assertTrue(got is None or got < 1.0)


class AMarionetteCountsAsTheTokenItHolds(SolverTest):
    """Table ruling (02.10.2026): the Chambermaid gets the number the
    Marionette's token gives.

    It thinks it is a good character and lives that character's nights,
    the same as the Drunk — which always counted, while the Marionette
    sat on the list of seats that are only shown something. The
    simulator counted it all along; no script on the sweep had both
    characters, so nothing showed the two disagreeing.
    """

    IDS = ["chambermaid", "empath", "chef", "undertaker", "monk",
           "washerwoman", "slayer", "saint", "drunk", "marionette",
           "poisoner", "imp"]

    def counts(self, token, night, **more):
        from botc import waking
        script = scripts.from_ids("Mixed", self.IDS)
        claims = ["Chambermaid", token, "Monk", "Washerwoman", "Slayer",
                  "Saint", "Chef"]
        state = GameState(n_players=7, script=script,
                          claims={i: r for i, r in enumerate(claims)}, **more)
        world = World(("Chambermaid", "Marionette", "Imp", "Washerwoman",
                       "Slayer", "Saint", "Chef"),
                      (None, token, None, None, None, None, None))
        return waking.possible_counts(world, state, [1, 4], night)

    def test_one_that_thinks_it_is_the_empath_wakes_every_night(self):
        self.assertEqual(self.counts("Empath", 1), {1})
        self.assertEqual(self.counts("Empath", 3), {1})

    def test_one_that_thinks_it_is_the_chef_only_on_the_first(self):
        self.assertEqual(self.counts("Chef", 1), {1})
        self.assertEqual(self.counts("Chef", 2), {0})

    def test_one_that_thinks_it_is_the_undertaker_after_an_execution(self):
        self.assertEqual(self.counts("Undertaker", 2), {0})
        hanged = {"deaths": {5: "D1"}, "executions": {1: 5}}
        self.assertEqual(self.counts("Undertaker", 2, **hanged), {1})

    def test_the_drunk_is_counted_the_same_way(self):
        from botc import waking
        script = scripts.from_ids("Mixed", self.IDS)
        claims = ["Chambermaid", "Empath", "Monk", "Washerwoman", "Slayer",
                  "Saint", "Chef"]
        state = GameState(n_players=7, script=script,
                          claims={i: r for i, r in enumerate(claims)})
        for holder in ("Drunk", "Marionette"):
            with self.subTest(holder=holder):
                world = World(("Chambermaid", holder, "Imp", "Washerwoman",
                               "Slayer", "Saint", "Chef"),
                              (None, "Empath") + (None,) * 5)
                self.assertEqual(
                    waking.possible_counts(world, state, [1, 4], 2), {1})


class TheRulebookReadAgainstTheCode(SolverTest):
    """Every character of Bad Moon Rising, read against the rulebook the
    single-player game is built from (02.10.2026).

    Each test is a small board with one true world. Where a rule was
    missing, that world was thrown out; where it was loose, a world that
    could not have happened cost nothing.
    """

    def cost(self, roles, bluffs, believes=None, **board):
        claims = list(roles)
        for seat, claim in bluffs.items():
            claims[seat] = claim
        state = GameState(n_players=len(roles),
                          script=scripts.BAD_MOON_RISING,
                          claims={i: c for i, c in enumerate(claims)},
                          **board)
        return S.explanation_cost(
            World(tuple(roles), tuple(believes or (None,) * len(roles))),
            state)

    TEA = ["Gambler", "TeaLady", "Gossip", "Chambermaid", "Professor",
           "Minstrel", "Tinker", "Godfather"]
    EVIL = {7: "Moonchild", 8: "Courtier"}

    # --- the Tea Lady ----------------------------------------------------

    def test_her_neighbour_walks_away_from_the_gallows(self):
        got = self.cost(self.TEA + ["Po"], self.EVIL, executions={1: 2})
        self.assertIsNotNone(got)

    def test_and_one_that_hangs_means_she_was_not_working(self):
        """Nothing on this board could have stopped her."""
        got = self.cost(self.TEA + ["Po"], self.EVIL,
                        executions={1: 2}, deaths={2: "D1"})
        self.assertIsNone(got)

    def test_a_shabaloth_takes_her_and_then_her_neighbour(self):
        got = self.cost(self.TEA + ["Shabaloth"], self.EVIL,
                        deaths={1: "N2", 2: "N2"})
        self.assertEqual(got, 1.0)

    def test_but_not_her_neighbour_while_she_stands(self):
        got = self.cost(self.TEA + ["Shabaloth"], self.EVIL,
                        deaths={2: "N2"})
        self.assertIsNone(got)

    # --- the Shabaloth ---------------------------------------------------

    BARE = ["Gambler", "Sailor", "Gossip", "Chambermaid", "Exorcist",
            "Minstrel", "Tinker", "Godfather"]

    def test_a_shabaloth_brings_somebody_back(self):
        got = self.cost(self.BARE + ["Shabaloth"], self.EVIL,
                        deaths={0: "N2", 2: "N2"}, resurrections={0: "N3"})
        self.assertIsNotNone(got)

    def test_and_may_do_it_twice(self):
        got = self.cost(self.BARE + ["Shabaloth"], self.EVIL,
                        deaths={0: "N2", 2: "N2", 3: "N3"},
                        resurrections={0: "N3", 3: "N4"})
        self.assertIsNotNone(got)

    def test_nobody_else_does(self):
        got = self.cost(self.BARE + ["Po"], self.EVIL,
                        deaths={0: "N2"}, resurrections={0: "N3"})
        self.assertIsNone(got)

    def test_a_professor_still_only_once(self):
        roles = ["Gambler", "Chambermaid", "Gossip", "Professor",
                 "Exorcist", "Minstrel", "Tinker", "Godfather", "Po"]
        self.assertEqual(self.cost(roles, self.EVIL, deaths={0: "N2"},
                                   resurrections={0: "N3"},
                                   quiet_nights={3}), 1.0)
        self.assertIsNone(self.cost(
            roles, self.EVIL, deaths={0: "N2", 1: "N3"},
            resurrections={0: "N3", 1: "N4"}))

    # --- the Courtier ----------------------------------------------------

    COURT = ["Courtier", "Fool", "Gossip", "Chambermaid", "Exorcist",
             "Minstrel", "Tinker", "Godfather", "Po"]
    COURT_EVIL = {7: "Moonchild", 8: "Professor"}

    def named(self):
        from botc.info import CourtierChoice
        return [CourtierChoice(1, 0, role="Fool")]

    def test_its_drunkenness_rests_once_it_is_dead(self):
        """Table ruling. The Fool it named walks away from the gallows
        the day after the Courtier died."""
        got = self.cost(self.COURT, self.COURT_EVIL, infos=self.named(),
                        deaths={0: "N2"}, executions={2: 1})
        self.assertIsNotNone(got)

    def test_while_it_lives_the_named_one_is_drunk(self):
        """Nothing here could have got at the Courtier on the first
        night, so the Fool was drunk and did not walk away."""
        got = self.cost(self.COURT, self.COURT_EVIL, infos=self.named(),
                        deaths={3: "N2"}, executions={2: 1})
        self.assertIsNone(got)

    def test_unless_the_courtier_was_itself_impaired_when_it_chose(self):
        """Then it made nobody drunk at all. A Sailor on the board could
        have chosen it first: priced, not free."""
        roles = self.COURT[:2] + ["Sailor"] + self.COURT[3:]
        got = self.cost(roles, self.COURT_EVIL, infos=self.named(),
                        deaths={3: "N2"}, executions={2: 1})
        self.assertIsNotNone(got)
        self.assertLess(got, 1.0)

    # --- the Minstrel ----------------------------------------------------

    MINSTREL = ["Gambler", "Sailor", "Gossip", "Chambermaid", "Exorcist",
                "Minstrel", "Tinker", "DevilsAdvocate", "Po"]

    def test_a_minion_that_walked_away_silences_nobody(self):
        got = self.cost(self.MINSTREL, self.COURT_EVIL,
                        executions={1: 7, 2: 1}, deaths={3: "N2"})
        self.assertIsNotNone(got)

    def test_one_that_died_silences_everybody(self):
        got = self.cost(self.MINSTREL, self.COURT_EVIL,
                        executions={1: 7, 2: 1}, deaths={7: "D1"})
        self.assertIsNone(got)

    # --- the Po ----------------------------------------------------------

    def test_a_po_takes_one_on_the_second_night(self):
        got = self.cost(self.BARE + ["Po"], self.EVIL,
                        deaths={0: "N2", 2: "N2", 3: "N2"})
        self.assertIsNone(got)

    def test_and_three_after_a_night_it_took_nobody(self):
        got = self.cost(self.BARE + ["Po"], self.EVIL,
                        deaths={0: "N3", 2: "N3", 3: "N3"}, quiet_nights={2})
        self.assertEqual(got, 1.0)

    # --- choices that were written down ----------------------------------

    def test_an_innkeepers_pair_cannot_die_while_it_works(self):
        from botc.info import InnkeeperChoice
        roles = ["Innkeeper", "Gambler", "Courtier", "Chambermaid",
                 "Exorcist", "Minstrel", "Pacifist", "Mastermind",
                 "Shabaloth"]
        got = self.cost(roles, {7: "Tinker", 8: "Professor"},
                        infos=[InnkeeperChoice(2, 0, a=1, b=2)],
                        deaths={1: "N2", 3: "N2"})
        self.assertTrue(got is None or got < 1.0)

    def test_an_exorcist_that_named_the_demon_and_a_body_anyway(self):
        from botc.info import ExorcistChoice
        roles = ["Exorcist", "Gambler", "Courtier", "Chambermaid", "Gossip",
                 "Minstrel", "Pacifist", "Mastermind", "Zombuul"]
        bluffs = {7: "Tinker", 8: "Professor"}
        named = [ExorcistChoice(2, 0, target=8)]
        self.assertEqual(self.cost(roles, bluffs, infos=named,
                                   quiet_nights={2}), 1.0)
        got = self.cost(roles, bluffs, infos=named, deaths={3: "N2"})
        self.assertTrue(got is None or got < 1.0)

    def test_a_fake_exorcists_row_binds_nobody(self):
        """The real one sits unclaimed elsewhere, and what it chose is as
        unrecorded as if nobody had spoken."""
        from botc.info import ExorcistChoice
        roles = ["Exorcist", "Gambler", "Courtier", "Chambermaid", "Gossip",
                 "Minstrel", "Pacifist", "Mastermind", "Zombuul"]
        bluffs = {0: "Tinker", 7: "Exorcist", 8: "Professor"}
        got = self.cost(roles, bluffs, quiet_nights={2},
                        infos=[ExorcistChoice(2, 7, target=3)])
        self.assertIsNotNone(got)

    # --- the Moonchild ---------------------------------------------------

    CHILD = ["Moonchild", "Gambler", "Gossip", "Chambermaid", "Exorcist",
             "Minstrel", "Tinker", "Mastermind", "Zombuul"]
    CHILD_EVIL = {7: "Fool", 8: "Courtier"}

    def picked(self, who):
        from botc.info import MoonchildChoice
        return {"executions": {1: 0}, "deaths": {0: "D1"},
                "infos": [MoonchildChoice(2, 0, target=who)]}

    def test_a_good_player_it_named_dies(self):
        board = self.picked(3)
        board["deaths"][3] = "N2"
        self.assertEqual(self.cost(self.CHILD, self.CHILD_EVIL, **board),
                         1.0)

    def test_one_still_standing_has_to_be_explained(self):
        got = self.cost(self.CHILD, self.CHILD_EVIL, quiet_nights={2},
                        **self.picked(3))
        self.assertIsNotNone(got)
        self.assertLess(got, 1.0)

    def test_an_evil_one_it_named_simply_lives(self):
        got = self.cost(self.CHILD, self.CHILD_EVIL, quiet_nights={2},
                        **self.picked(7))
        self.assertEqual(got, 1.0)

    # --- walking away from the gallows -----------------------------------

    def test_one_rescuer_working_is_enough(self):
        """A Devil's Advocate saved them, and the Pacifist on the same
        board was drunk the whole time: the Courtier named it. Both used
        to be demanded, and the rescue was thrown out."""
        from botc.info import CourtierChoice
        roles = ["Gambler", "Chambermaid", "Gossip", "Courtier", "Exorcist",
                 "Minstrel", "Pacifist", "DevilsAdvocate", "Po"]
        got = self.cost(roles, {7: "Moonchild", 8: "Professor"},
                        infos=[CourtierChoice(1, 3, role="Pacifist")],
                        executions={1: 0})
        self.assertIsNotNone(got)

    def test_a_devils_advocate_not_the_same_player_two_days_running(self):
        roles = ["Gambler", "Chambermaid", "Gossip", "Courtier", "Exorcist",
                 "Minstrel", "Tinker", "DevilsAdvocate", "Po"]
        bluffs = {7: "Moonchild", 8: "Professor"}
        self.assertIsNotNone(self.cost(roles, bluffs, executions={1: 0}))
        self.assertIsNone(self.cost(roles, bluffs,
                                    executions={1: 0, 2: 0},
                                    deaths={1: "N2"}))
        # Somebody else on the second day is another matter.
        self.assertIsNotNone(self.cost(roles, bluffs,
                                       executions={1: 0, 2: 2},
                                       deaths={1: "N2"}))

    def test_a_fool_walks_away_once(self):
        roles = ["Fool", "Chambermaid", "Gossip", "Courtier", "Exorcist",
                 "Minstrel", "Tinker", "Godfather", "Po"]
        bluffs = {7: "Moonchild", 8: "Professor"}
        self.assertIsNotNone(self.cost(roles, bluffs, executions={1: 0}))
        self.assertIsNone(self.cost(roles, bluffs,
                                    executions={1: 0, 2: 0},
                                    deaths={3: "N2"}))


class WhatThePlayedGamesFound(SolverTest):
    """The simulator learned to play four things on 03.10.2026 — an
    execution somebody walks away from, the dead coming back, a Moonchild
    taken at night, a Witch's curse biting — and within the hour it had
    produced games the solver threw out. Each of these is one of them,
    cut down to a board with one true world.

    Most turn on one fact: **a return is dated to a night, and a night is
    seventy slots long.** A Shabaloth regurgitates at 27 and a Professor
    raises at 43, so whoever came back was dead for the first part of the
    night and alive for the rest.
    """

    TEA = TheRulebookReadAgainstTheCode.TEA
    EVIL = {7: "Moonchild", 8: "Courtier"}
    cost = TheRulebookReadAgainstTheCode.cost

    # --- a return in the middle of a night --------------------------------

    def test_a_tea_lady_raised_late_was_not_there_to_keep_her_neighbour(self):
        """She died on night two, her neighbour was killed on night three
        and the Professor raised her that same night — after the kill."""
        got = self.cost(self.TEA + ["Po"], self.EVIL,
                        deaths={1: "N2", 2: "N3"}, resurrections={1: "N3"})
        self.assertIsNotNone(got)

    def test_a_grandmother_raised_late_did_not_see_her_grandchild_fall(self):
        from botc.info import GrandmotherInfo
        roles = ["Grandmother", "Pacifist", "Gossip", "Chambermaid",
                 "Professor", "Minstrel", "Tinker", "Godfather", "Po"]
        shown = [GrandmotherInfo(1, 0, target=2, role="Gossip")]
        back = self.cost(roles, self.EVIL, infos=shown,
                         deaths={0: "D1", 2: "N2"}, executions={1: 0},
                         resurrections={0: "N2"})
        self.assertEqual(back, 1.0, "nothing to excuse")
        # Standing all along, with nothing on the board to impair her or
        # keep her alive, she would have gone with the grandchild — so
        # the only story left is that the reading was never hers.
        self.assertLess(self.cost(roles, self.EVIL, infos=shown,
                                  deaths={2: "N2"}), 1.0)

    def test_a_courtier_raised_by_the_professor_it_had_named(self):
        """Its drunkenness ended when it died, so the Professor was sober
        when it chose. (And stays sober: the Courtier that stands up is
        a new one — see `AnAbilityEndsWithItsOwner`.)"""
        from botc.info import CourtierChoice
        roles = ["Courtier", "Pacifist", "Gossip", "Chambermaid",
                 "Professor", "Minstrel", "Tinker", "Godfather", "Po"]
        got = self.cost(roles, self.EVIL,
                        infos=[CourtierChoice(1, 0, role="Professor")],
                        deaths={0: "D1"}, executions={1: 0},
                        resurrections={0: "N2"})
        self.assertIsNotNone(got)

    def test_a_minstrel_raised_since_was_not_there_to_hear_it(self):
        roles = ["Minstrel", "Pacifist", "Gossip", "Chambermaid",
                 "Professor", "Fool", "Tinker", "Godfather", "Po"]
        got = self.cost(roles, self.EVIL,
                        deaths={0: "N2", 7: "D2"}, executions={2: 7},
                        resurrections={0: "N3"})
        self.assertIsNotNone(got, "the Professor was sober when it chose")

    def test_a_pukkas_poison_came_due_on_somebody_not_yet_back(self):
        """Poisoned on the first night, executed that day, raised the next
        night — after the poison had found a corpse."""
        from botc.info import GrandmotherInfo
        roles = ["Grandmother", "Pacifist", "Gossip", "Chambermaid",
                 "Professor", "Minstrel", "Tinker", "Godfather", "Pukka"]
        got = self.cost(roles, self.EVIL,
                        infos=[GrandmotherInfo(1, 0, target=2, role="Fool")],
                        deaths={0: "D1"}, executions={1: 0},
                        resurrections={0: "N2"}, quiet_nights={2})
        self.assertIsNotNone(got)

    # --- the Chambermaid ---------------------------------------------------

    def chambermaid(self, roles, night, a, b, count, **board):
        from botc.info import ChambermaidInfo
        seat = roles.index("Chambermaid")
        return self.cost(roles, self.EVIL, infos=[
            ChambermaidInfo(night, seat, a=a, b=b, count=count)], **board)

    def test_a_professor_may_have_spent_it_where_nobody_could_see(self):
        """On somebody who was no Townsfolk, or while drunk: nothing
        happens and it is gone. Night two it is woken for certain; after
        that, either number."""
        roles = self.TEA + ["Po"]
        professor, gossip = 4, 2
        self.assertIsNotNone(self.chambermaid(roles, 2, professor, gossip, 1))
        self.assertIsNone(self.chambermaid(roles, 2, professor, gossip, 0))
        for count in (0, 1):
            with self.subTest(night=3, count=count):
                self.assertIsNotNone(
                    self.chambermaid(roles, 3, professor, gossip, count))

    def test_but_a_return_with_no_shabaloth_about_was_its_doing(self):
        roles = self.TEA + ["Po"]
        raised = {"deaths": {5: "N2"}, "resurrections": {5: "N3"}}
        self.assertIsNotNone(self.chambermaid(roles, 3, 4, 2, 1, **raised))
        self.assertIsNotNone(self.chambermaid(roles, 4, 4, 2, 0, **raised))
        self.assertIsNone(self.chambermaid(roles, 4, 4, 2, 1, **raised),
                          "spent, and seen to be")

    def test_whoever_came_back_tonight_slept_through_an_earlier_turn(self):
        """An Innkeeper acts at 9. Regurgitated at 27, it did not wake —
        and it guarded nobody and drunk nobody either."""
        roles = ["Gambler", "Innkeeper", "Gossip", "Chambermaid", "Fool",
                 "Minstrel", "Tinker", "Godfather", "Shabaloth"]
        back = {"deaths": {1: "N2"}, "resurrections": {1: "N3"}}
        self.assertIsNotNone(self.chambermaid(roles, 3, 1, 2, 0, **back))
        self.assertIsNone(self.chambermaid(roles, 3, 1, 2, 1, **back))

    # --- once per game, and then again --------------------------------------

    def test_a_fool_that_has_been_dead_and_back_walks_away_again(self):
        roles = ["Fool", "Chambermaid", "Gossip", "Courtier", "Exorcist",
                 "Minstrel", "Tinker", "Godfather", "Shabaloth"]
        bluffs = {7: "Moonchild", 8: "Professor"}
        again = self.cost(roles, bluffs, executions={1: 0, 3: 0},
                          deaths={0: "N2"}, resurrections={0: "N3"})
        self.assertIsNotNone(again)
        self.assertIsNone(self.cost(roles, bluffs, executions={1: 0, 3: 0}),
                          "not without having died in between")

    # --- a Pukka that was drunk for a night ---------------------------------

    def test_its_kill_comes_a_night_late(self):
        """The Tea Lady was poisoned on night two. On night three the
        Innkeeper made the Pukka drunk: no attack, the token stays, and
        the poison rests. So she kept her neighbour from the gallows that
        day — and died on night four."""
        from botc.info import InnkeeperChoice
        # A Grandmother beside her rather than a Gossip: nothing else on
        # this board can have killed the Tea Lady.
        roles = ["Gambler", "TeaLady", "Grandmother", "Chambermaid",
                 "Innkeeper", "Minstrel", "Tinker", "Godfather", "Pukka"]
        got = self.cost(roles, self.EVIL,
                        infos=[InnkeeperChoice(3, 4, a=8, b=5)],
                        deaths={6: "N2", 1: "N4"}, executions={3: 2},
                        quiet_nights={3})
        self.assertIsNotNone(got)

    # --- the Goon -------------------------------------------------------------

    def test_the_last_chooser_standing_need_not_have_chosen_the_goon(self):
        """With one chooser left alive the Goon's drunkenness was read as
        unavoidable, so that Sailor was drunk every night — and could not
        have walked away from the gallows."""
        roles = ["Sailor", "Fool", "Zombuul", "Minstrel", "Mastermind",
                 "Chambermaid", "Goon", "Tinker", "Grandmother"]
        got = self.cost(roles, {2: "Courtier", 4: "Gossip"},
                        deaths={2: "D1"}, executions={1: 2, 2: 0})
        self.assertIsNotNone(got)

    # --- how many tellings of the nights are kept -------------------------------

    def test_the_account_that_happened_is_not_past_the_cut(self):
        """Four nights, and on each a Demon, a Gossip, an Assassin and a
        Gambler able to explain the same body. The first twenty-four
        tellings, kept as they came, did not include the true one."""
        from botc.info import ChambermaidInfo, GamblerGuess
        roles = ["Chambermaid", "Pukka", "Innkeeper", "Assassin", "Gossip",
                 "Fool", "Professor", "Grandmother", "Gambler",
                 "DevilsAdvocate"]
        got = self.cost(
            roles, {1: "Pacifist", 3: "Goon", 9: "Courtier"},
            deaths={0: "E1", 8: "N2", 9: "N3", 4: "N4"},
            infos=[ChambermaidInfo(1, 0, a=1, b=7, count=7),
                   GamblerGuess(2, 8, target=4, role="Minstrel")])
        self.assertIsNotNone(got)



class AnAbilityEndsWithItsOwner(SolverTest):
    """Table ruling, 03.10.2026: an ability always ends with the death of
    whoever has it. Somebody raised or made anew is a **new instance** —
    it chooses again, and what the old one set going stays ended.

    Until then a Courtier's drunkenness *rested* while it was dead and
    took up again when it stood, and a Grandmother kept the grandchild
    of her first life.
    """

    cost = TheRulebookReadAgainstTheCode.cost
    COURT = ["Courtier", "Fool", "Gossip", "Chambermaid", "Professor",
             "Minstrel", "Tinker", "Godfather", "Po"]
    EVIL = {7: "Moonchild", 8: "Exorcist"}

    def named(self, *nights):
        from botc.info import CourtierChoice
        return [CourtierChoice(night, 0, role="Fool") for night in nights]

    def test_what_a_courtier_named_stays_sober_after_it_returns(self):
        """Named the Fool, died on night two, raised on night three. The
        Fool walks away from the gallows on day three: sober, though the
        three days are not up and the Courtier is standing again."""
        got = self.cost(self.COURT, self.EVIL, infos=self.named(1),
                        deaths={0: "N2"}, resurrections={0: "N3"},
                        executions={3: 1}, quiet_nights={3})
        self.assertIsNotNone(got)

    def test_and_is_drunk_again_only_if_it_names_them_again(self):
        got = self.cost(self.COURT, self.EVIL, infos=self.named(1, 4),
                        deaths={0: "N2"}, resurrections={0: "N3"},
                        executions={4: 1}, quiet_nights={3, 4})
        self.assertIsNone(got, "named on night four, drunk on day four")

    def test_one_that_never_died_still_has_its_three_days(self):
        got = self.cost(self.COURT, self.EVIL, infos=self.named(1),
                        deaths={3: "N2"}, executions={3: 1},
                        quiet_nights={3})
        self.assertIsNone(got)

    def test_a_courtier_back_from_the_dead_is_woken_to_choose(self):
        from botc import waking
        from botc.info import CourtierChoice
        world = World(tuple(self.COURT), (None,) * 9)

        def woken(infos):
            state = GameState(
                n_players=9, script=BMR,
                claims={i: r for i, r in enumerate(self.COURT)},
                infos=infos, deaths={0: "N2"}, resurrections={0: "N3"})
            return waking.woke(world, state, 0, 4)

        self.assertTrue(woken(self.named(1)),
                        "it chose in its first life, and this is its second")
        self.assertFalse(woken(self.named(1) + [CourtierChoice(3, 0,
                                                               role="Po")]))

    def test_a_grandmother_back_from_the_dead_has_let_go_of_the_first(self):
        """Shown the Gossip, executed, raised. The Gossip falls to the
        Demon two nights later and she stands: no grandchild of this
        life is on the board, and the old one is nothing to her."""
        from botc.info import GrandmotherInfo
        roles = ["Grandmother", "Pacifist", "Gossip", "Chambermaid",
                 "Professor", "Minstrel", "Tinker", "Godfather", "Po"]
        evil = {7: "Moonchild", 8: "Courtier"}
        shown = [GrandmotherInfo(1, 0, target=2, role="Gossip")]
        got = self.cost(roles, evil, infos=shown,
                        deaths={0: "D1", 2: "N3"}, executions={1: 0},
                        resurrections={0: "N2"}, quiet_nights={2})
        self.assertEqual(got, 1.0)

    def test_and_grieves_for_the_one_she_was_shown_on_her_return(self):
        from botc.info import GrandmotherInfo
        # No Gossip and no Assassin: only the Demon can have killed.
        roles = ["Grandmother", "Pacifist", "Minstrel", "Chambermaid",
                 "Professor", "Fool", "Tinker", "Mastermind", "Po"]
        evil = {7: "Moonchild", 8: "Courtier"}
        shown = [GrandmotherInfo(1, 0, target=2, role="Minstrel"),
                 GrandmotherInfo(2, 0, target=3, role="Chambermaid")]
        board = dict(infos=shown, executions={1: 0},
                     resurrections={0: "N2"}, quiet_nights={2})
        self.assertIsNone(self.cost(roles, evil, **board,
                                    deaths={0: "D1", 3: "N3"}),
                          "her new grandchild fell and she is standing")
        self.assertEqual(self.cost(roles, evil, **board,
                                   deaths={0: ("D1", "N3"), 3: "N3"}), 1.0)


class WhatTheGoonAndTheOtherKillsFound(SolverTest):
    """The simulator learned the Goon and the three kills it had never
    played — the Assassin's, the Godfather's, a Gossip's — on 03.10.2026,
    and again it produced games the solver threw out.
    """

    cost = TheRulebookReadAgainstTheCode.cost
    EVIL = {7: "Moonchild", 8: "Courtier"}
    # Seat 2 is the Tea Lady, between a Gambler and whoever `beside` is.
    BESIDE = ["Gambler", "TeaLady", "{beside}", "Chambermaid", "Professor",
              "Minstrel", "Tinker", "Godfather", "Po"]

    def beside(self, who):
        return [role.format(beside=who) for role in self.BESIDE]

    # --- a side nobody wrote down --------------------------------------------

    def test_a_tea_lady_beside_a_goon_may_not_have_been_protecting(self):
        """The Goon turned evil in the night and her other neighbour was
        killed. Nothing here can have impaired her — and nothing had to."""
        died = dict(deaths={0: "N2"})
        self.assertIsNone(self.cost(self.beside("Gossip"), self.EVIL, **died),
                          "between two good players she keeps both")
        self.assertIsNotNone(self.cost(self.beside("Goon"), self.EVIL,
                                       **died))

    def test_nor_at_the_gallows(self):
        hanged = dict(deaths={0: "D1"}, executions={1: 0})
        self.assertIsNone(self.cost(self.beside("Gossip"), self.EVIL,
                                    **hanged))
        self.assertIsNotNone(self.cost(self.beside("Goon"), self.EVIL,
                                       **hanged))

    def test_but_she_still_may_have_been(self):
        """A Goon that stayed good: her neighbour walks away."""
        got = self.cost(self.beside("Goon"), self.EVIL, executions={1: 0})
        self.assertIsNotNone(got)

    def test_a_moonchild_that_named_a_goon_proves_nothing(self):
        """Named somebody good and they lived: that wants a reason, and
        costs. Named the Goon and it lived: it may have been evil by
        then."""
        from botc.info import MoonchildChoice
        roles = ["Gambler", "Pacifist", "Goon", "Chambermaid", "Professor",
                 "Minstrel", "Moonchild", "Godfather", "Po"]
        evil = {7: "Tinker", 8: "Courtier"}

        def named(seat):
            return self.cost(roles, evil,
                             infos=[MoonchildChoice(2, 6, target=seat)],
                             deaths={6: "D1"}, executions={1: 6},
                             quiet_nights={2})

        self.assertEqual(named(2), 1.0)
        self.assertLess(named(0), 1.0)

    # --- a kill stopped where it starts -------------------------------------------

    def test_a_godfather_is_the_one_who_kills(self):
        """So one made drunk — by the Goon it chose, among others —
        explains a night with no body."""
        world = among("Grandmother", "Sailor", "Chambermaid", "Exorcist",
                      "Innkeeper", "Gambler", "Tinker", "Godfather",
                      "Zombuul")
        got = S.a_godfather_answers_an_outsider(
            world, board(deaths={6: "E2"}), 3)
        self.assertEqual(got[0].actor, 7)

    # --- the Pukka's token on somebody who lived -------------------------------------

    def test_an_innkeeper_under_the_token_and_kept_alive(self):
        """Poisoned on the first night, and on the second a Tea Lady
        beside it keeps it alive. It chose its pair before the Pukka's
        turn, with the token still on it: nobody safe, nobody drunk. So
        the Gambler it named guessed wrong and died of it — which a
        working Innkeeper would not have allowed."""
        from botc.info import GamblerGuess, InnkeeperChoice
        roles = ["Chambermaid", "TeaLady", "Innkeeper", "Gambler",
                 "Professor", "Minstrel", "Tinker", "Godfather", "Pukka"]
        got = self.cost(
            roles, self.EVIL,
            infos=[InnkeeperChoice(2, 2, a=3, b=4),
                   GamblerGuess(2, 3, target=4, role="Fool")],
            deaths={3: "N2", 5: "N3"})
        self.assertIsNotNone(got)

    # --- how many tellings of a night are worth keeping ------------------------------

    def test_a_telling_that_asks_for_more_and_costs_no_less_is_dropped(self):
        none = frozenset()
        plain = (1.0, frozenset({3}), none, {})
        more = (1.0, frozenset({3, 4}), none, {})
        dearer = (0.5, frozenset({3}), none, {})
        cheaper_but_more = (1.0, frozenset({3}), frozenset({5}), {})
        earlier = (1.0, frozenset({3}), none, {2: {6}})
        other = (0.5, frozenset({7}), none, {})
        got = S._the_ones_that_can_win(
            [plain, more, dearer, cheaper_but_more, earlier, other, plain])
        self.assertEqual(got, [plain, other])

    def test_one_that_asks_for_more_but_costs_less_stays(self):
        none = frozenset()
        dear = (0.5, frozenset(), none, {})
        cheap = (1.0, frozenset({3}), none, {})
        self.assertEqual(S._the_ones_that_can_win([dear, cheap]),
                         [dear, cheap])


class ADemonStoppedAtItsSource(SolverTest):
    """A night without a body because the Demon itself was drunk.

    The Demons of Bad Moon Rising had one way to explain a quiet night:
    whoever they aimed at could not die. With no Sailor, Innkeeper, Fool,
    Tea Lady or Exorcist to lean on and nobody dead yet, a night like
    that had no explanation at all — and the commonest real reason, a
    Demon that pointed at the Goon first, was never on offer. Once played
    games told the solver their quiet nights, 83 in 60,000 lost the world
    that happened (04.10.2026).

    Nothing is taken away by this: a kill still says nothing about
    whether the Demon was sober (table decision, the same day).
    """

    GOOD = ["Gambler", "Gossip", "Chambermaid", "Professor", "Grandmother"]
    EVIL = {6: "Courtier", 7: "Minstrel"}

    def cost(self, demon, outsider="Goon", **board):
        roles = self.GOOD + [outsider, "Assassin", demon]
        claims = list(roles)
        for seat, claim in self.EVIL.items():
            claims[seat] = claim
        state = GameState(n_players=len(roles),
                          script=scripts.BAD_MOON_RISING,
                          claims={i: c for i, c in enumerate(claims)},
                          **board)
        return S.explanation_cost(
            World(tuple(roles), (None,) * len(roles)), state)

    def test_a_quiet_night_is_one_where_it_chose_the_goon_first(self):
        for demon in ("Shabaloth", "Zombuul", "Pukka"):
            with self.subTest(demon=demon):
                self.assertIsNotNone(self.cost(demon, quiet_nights={2}))

    def test_but_only_where_something_could_have_stopped_it(self):
        """A Tinker makes nobody drunk, and there is nothing else."""
        for demon in ("Shabaloth", "Zombuul"):
            with self.subTest(demon=demon):
                self.assertIsNone(
                    self.cost(demon, outsider="Tinker", quiet_nights={2}))

    def test_a_pukka_can_always_have_poisoned_itself_and_that_costs(self):
        """Its own poison reaches every seat, its own included. Legal,
        and nobody does it: free with a Goon to blame, dear without."""
        alone = self.cost("Pukka", outsider="Tinker", quiet_nights={2})
        self.assertIsNotNone(alone)
        self.assertLess(alone, 1.0)
        self.assertEqual(self.cost("Pukka", quiet_nights={2}), 1.0)

    def test_a_pukka_stopped_on_the_first_night_has_nothing_due(self):
        """It poisoned nobody, so nobody dies on the second — and it need
        not have been drunk on the second for that."""
        from botc import deaths as D
        roles = self.GOOD + ["Goon", "Assassin", "Pukka"]
        state = GameState(n_players=8, script=scripts.BAD_MOON_RISING,
                          claims={i: r for i, r in enumerate(roles)},
                          quiet_nights={2})
        world = World(tuple(roles), (None,) * 8)
        cause = [c for c in D.causes_on(world, state, 2) if c.must_fire][0]
        self.assertEqual(cause.excuses, ((None, ((1, 7),)),))

    def test_or_on_the_second_and_the_first_token_rests(self):
        """Stopped last night: what comes due is the token from the night
        before that, and that player has to have been unable to die."""
        from botc import deaths as D
        roles = self.GOOD + ["Goon", "Assassin", "Pukka"]
        state = GameState(n_players=8, script=scripts.BAD_MOON_RISING,
                          claims={i: r for i, r in enumerate(roles)},
                          quiet_nights={2, 3})
        world = World(tuple(roles), (None,) * 8)
        cause = [c for c in D.causes_on(world, state, 3) if c.must_fire][0]
        seats, demands = cause.excuses[0]
        self.assertEqual(seats, frozenset(range(8)))
        self.assertEqual(demands, ((2, 7),))
        self.assertEqual(cause.excuses[1], (None, ((1, 7), (2, 7))))

    def test_two_quiet_nights_running(self):
        for demon in ("Shabaloth", "Zombuul", "Pukka"):
            with self.subTest(demon=demon):
                self.assertIsNotNone(
                    self.cost(demon, quiet_nights={2, 3}))

    def test_a_kill_still_says_nothing_about_the_demon(self):
        """The same price with a Goon to be drunk by and without one."""
        for demon in ("Shabaloth", "Zombuul"):
            with self.subTest(demon=demon):
                self.assertEqual(self.cost(demon, deaths={0: "N2"}),
                                 self.cost(demon, outsider="Tinker",
                                           deaths={0: "N2"}))

    def test_a_po_owes_nothing_for_a_quiet_night_as_before(self):
        self.assertEqual(
            self.cost("Po", outsider="Tinker", quiet_nights={2}), 1.0)


class WhatTheBoardAlreadyAsksIsHeardFirst(SolverTest):
    """An explanation of a night that the readings rule out is dropped
    before the accounts are counted, not after.

    The accounts kept are capped at four hundred. Each one was only
    tested against the readings afterwards, so an account asking for a
    seat impaired on a night a reading needs it working — dead from the
    start — still held one of the four hundred places. Two games in
    24,000 over six nights had all four hundred taken that way
    (04.10.2026).
    """

    def test_one_that_needs_a_seat_the_other_way_round_is_dropped(self):
        none = frozenset()
        fine = (1.0, frozenset({1}), frozenset({2}), {})
        impaired_but_working = (1.0, frozenset({3}), none, {})
        working_but_impaired = (1.0, none, frozenset({5}), {})
        earlier_but_working = (1.0, none, none, {2: {4}})
        other_night = (1.0, frozenset({4}), none, {1: {3}})
        got = S._the_ones_the_board_allows(
            3, [fine, impaired_but_working, working_but_impaired,
                earlier_but_working, other_night],
            impaired_already={3: {5}}, working_already={3: {3}, 2: {4}})
        self.assertEqual(got, [fine, other_night])

    def test_with_nothing_asked_everything_stays(self):
        options = [(1.0, frozenset({1}), frozenset({2}), {1: {3}})]
        self.assertEqual(
            S._the_ones_the_board_allows(2, options, {}, {}), options)

    def test_the_answer_is_the_same_with_and_without_it(self):
        """On played games that never reach the cap, dropping them early
        changes no price."""
        import random
        import claims as C
        import simulate
        real = S._the_ones_the_board_allows
        for seed in range(40):
            n = [7, 8, 9, 10, 11][seed % 5]
            rng = random.Random(seed)
            deal, heard = simulate.play(n, rng, nights=4,
                                        script=scripts.BAD_MOON_RISING)
            claims, wakes, _ = C.claims_for(deal, rng,
                                            script=scripts.BAD_MOON_RISING)

            def price():
                state = GameState(
                    n_players=n, script=scripts.BAD_MOON_RISING,
                    claims=claims, wakes=wakes, infos=list(heard),
                    votes=dict(deal.votes),
                    nominations=dict(deal.nominations), **deal.record())
                return S.explanation_cost(
                    World(tuple(deal.roles), tuple(deal.believes)), state)

            with_it = price()
            S._the_ones_the_board_allows = \
                lambda night, options, a, b: options
            try:
                without = price()
            finally:
                S._the_ones_the_board_allows = real
            with self.subTest(seed=seed):
                self.assertEqual(with_it, without)
