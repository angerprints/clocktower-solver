"""The experimental characters, added one at a time and without a script.

The first five (05.10.2026): Steward, Knight, Shugenja, Nightwatchman and
King. All of them give information and leave the night as it was, so
what is checked here is what each row *means* in a world — and the five
table decisions that went into that:

  * The Shugenja reads by **registration**, like the Chef and the Empath.
  * What the Nightwatchman says it did is kept and proves nothing; only
    the player it woke saying so does.
  * The King counts the dead at **its own turn**, after tonight's kills.
  * A Zombuul under its shroud is **alive** to the King.
  * The three characters the vendored night order does not know are
    slotted by hand.

A character has no home script, so two are made for them here, each
chosen to avoid what mixing is already known to break (see
`messung/README.md`): one with a Spy, a Recluse and a Zombuul, one with a
Vortox.
"""

import random
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking       # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

FIVE = ("Steward", "Knight", "Shugenja", "Nightwatchman", "King")

# Trouble Brewing's shape with the five in it, and a Zombuul for the King.
WITH_A_SPY = ["steward", "knight", "shugenja", "nightwatchman", "king",
              "washerwoman", "investigator", "chef", "empath", "undertaker",
              "monk", "ravenkeeper", "soldier",
              "recluse", "saint", "drunk", "butler",
              "poisoner", "spy", "scarletwoman", "baron",
              "imp", "zombuul"]
# Sects & Violets' shape, for what a Vortox does to each of them.
WITH_A_VORTOX = ["steward", "knight", "shugenja", "nightwatchman", "king",
                 "clockmaker", "dreamer", "flowergirl", "towncrier", "oracle",
                 "seamstress", "juggler", "sage",
                 "mutant", "sweetheart", "klutz", "saint",
                 "witch", "cerenovus", "eviltwin", "poisoner",
                 "vortox"]

SPY = scripts.from_ids("Experimental, with a Spy", WITH_A_SPY)
VORTOX = scripts.from_ids("Experimental, with a Vortox", WITH_A_VORTOX)


def cost(script, roles, infos=(), believes=None, **kw):
    """What the world costs on a board where everybody claims what they
    hold (or the token they were handed). None is a world thrown out."""
    n = len(roles)
    believes = tuple(believes or [None] * n)
    claims = {i: believes[i] or role for i, role in enumerate(roles)}
    state = GameState(n_players=n, script=script, claims=claims,
                      infos=list(infos), **kw)
    return S.explanation_cost(World(tuple(roles), believes), state)


#          0          1         2           3                4       5
SEVEN = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King", "Imp",
         "Spy"]                                               # 6


class TheyAreInTheCatalogue(SolverTest):

    def test_all_five_are_townsfolk_and_modelled(self):
        for key in FIVE:
            with self.subTest(character=key):
                self.assertEqual(CHARACTERS[key].team, "townsfolk")
                self.assertTrue(CHARACTERS[key].modelled)

    def test_three_of_them_have_a_slot_the_file_does_not_know(self):
        """The publisher's first night runs Seamstress, Steward, Knight,
        Noble, Balloonist, Shugenja, ..., Nightwatchman. The vendored
        file has no number for three of those, so each shares the slot
        of whatever follows it."""
        first = lambda key: CHARACTERS[key].first_night
        self.assertEqual(first("Steward"), first("Noble"))
        self.assertEqual(first("Knight"), first("Noble"))
        self.assertGreater(first("Shugenja"), first("Balloonist"))
        self.assertLess(first("Shugenja"), first("Nightwatchman"))
        for key in ("Steward", "Knight", "Shugenja"):
            self.assertEqual(CHARACTERS[key].other_night, 0)

    def test_they_read_before_an_ogre_picks_and_after_a_snake_charmer(self):
        for key in ("Steward", "Knight", "Shugenja"):
            with self.subTest(character=key):
                self.assertLess(CHARACTERS[key].first_night,
                                CHARACTERS["Ogre"].first_night)
                self.assertGreater(CHARACTERS[key].first_night,
                                   CHARACTERS["SnakeCharmer"].first_night)

    def test_the_king_reads_after_every_kill(self):
        late = CHARACTERS["King"].other_night
        for key in ("Imp", "Zombuul", "Pukka", "Po", "Shabaloth", "Assassin",
                    "Godfather", "Gossip", "Tinker", "Moonchild",
                    "Grandmother"):
            with self.subTest(killer=key):
                self.assertGreater(late, CHARACTERS[key].other_night)

    def test_the_nightwatchman_points_at_a_player(self):
        """Which is what a Goon reacts to."""
        self.assertTrue(CHARACTERS["Nightwatchman"].chooses)


class TheSteward(SolverTest):
    """One player, who is good."""

    def test_a_good_player_fits(self):
        self.assertEqual(cost(SPY, SEVEN, [I.StewardInfo(1, 0, target=1)]),
                         1.0)

    def test_the_demon_does_not(self):
        self.assertIsNone(cost(SPY, SEVEN, [I.StewardInfo(1, 0, target=5)]))

    def test_a_spy_may_be_the_one(self):
        """The wiki's own example: "Abdallah is the Spy, and is
        registering as good"."""
        self.assertEqual(cost(SPY, SEVEN, [I.StewardInfo(1, 0, target=6)]),
                         1.0)

    def test_and_then_the_spy_was_not_poisoned(self):
        """A droisoned character cannot misregister."""
        row = I.StewardInfo(1, 0, target=6)
        world = World(tuple(SEVEN), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)))
        self.assertEqual(row.leaned_on(world, state, 0), (6,))
        self.assertEqual(I.StewardInfo(1, 0, target=1)
                         .leaned_on(world, state, 0), ())

    def test_a_poisoned_steward_may_be_shown_anybody(self):
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Imp", "Poisoner"]
        self.assertIsNotNone(
            cost(SPY, roles, [I.StewardInfo(1, 0, target=5)]))

    def test_under_a_vortox_it_is_shown_somebody_evil(self):
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Vortox", "Witch"]
        self.assertIsNone(cost(VORTOX, roles,
                               [I.StewardInfo(1, 0, target=1)]))
        self.assertEqual(cost(VORTOX, roles,
                              [I.StewardInfo(1, 0, target=6)]), 1.0)


class TheKnight(SolverTest):
    """Two players, neither of whom is the Demon."""

    def test_two_who_are_not_the_demon_fit(self):
        self.assertEqual(cost(SPY, SEVEN, [I.KnightInfo(1, 1, a=0, b=2)]),
                         1.0)

    def test_a_minion_may_be_one_of_them(self):
        """"Townsfolk, Outsiders or even Minions"."""
        self.assertEqual(cost(SPY, SEVEN, [I.KnightInfo(1, 1, a=0, b=6)]),
                         1.0)

    def test_the_demon_may_not(self):
        self.assertIsNone(cost(SPY, SEVEN, [I.KnightInfo(1, 1, a=0, b=5)]))

    def test_it_is_two_players(self):
        self.assertIsNone(cost(SPY, SEVEN, [I.KnightInfo(1, 1, a=0, b=0)]))

    def test_a_recluse_is_not_the_demon_however_it_registers(self):
        roles = ["Steward", "Knight", "Shugenja", "Recluse", "King", "Imp",
                 "Spy"]
        self.assertEqual(cost(SPY, roles, [I.KnightInfo(1, 1, a=3, b=0)]),
                         1.0)

    def test_what_it_was_shown_can_become_the_demon_later(self):
        """A Scarlet Woman it was shown on night one takes over on day
        two. The reading was about that night, and still fits."""
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Imp", "ScarletWoman"]
        self.assertIsNotNone(cost(
            SPY, roles, [I.KnightInfo(1, 1, a=0, b=6)],
            deaths={5: "E1"}, days_done={1}))

    def test_under_a_vortox_the_two_include_the_demon(self):
        """The wiki's second example."""
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Vortox", "Witch"]
        self.assertIsNone(cost(VORTOX, roles,
                               [I.KnightInfo(1, 1, a=0, b=6)]))
        self.assertEqual(cost(VORTOX, roles,
                              [I.KnightInfo(1, 1, a=0, b=5)]), 1.0)


class TheShugenja(SolverTest):
    """Which way round its closest evil player sits. Seats run clockwise."""

    def ways(self, script, roles, seat=2, **kw):
        """(clockwise fits, anticlockwise fits)."""
        return tuple(
            cost(script, roles,
                 [I.ShugenjaInfo(1, seat, clockwise=way)], **kw) is not None
            for way in (True, False))

    def test_closer_one_way_is_that_way(self):
        #  seat 2 looks: the Imp is one step clockwise, the Spy three back.
        roles = ["Steward", "Knight", "Shugenja", "Imp", "King",
                 "Nightwatchman", "Spy"]
        self.assertEqual(self.ways(SPY, roles), (True, False))

    def test_and_the_other_way_round(self):
        roles = ["Steward", "Imp", "Shugenja", "Knight", "King",
                 "Nightwatchman", "Spy"]
        self.assertEqual(self.ways(SPY, roles), (False, True))

    def test_a_tie_allows_either(self):
        """"If equidistant, this info is arbitrary." Three steps to the
        Imp one way and three to the Spy the other."""
        self.assertEqual(self.ways(SPY, SEVEN), (True, True))

    def test_so_does_the_seat_exactly_opposite(self):
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Empath", "Imp", "Monk"]              # the Imp is 4 of 8 away
        self.assertEqual(self.ways(SPY, roles), (True, True))

    def test_a_recluse_may_be_the_closest(self):
        """Table decision, 05.10.2026: by registration. The Imp is two
        steps anticlockwise; the Recluse, one step clockwise, may read as
        evil — or not."""
        roles = ["Imp", "Knight", "Shugenja", "Recluse", "King",
                 "Nightwatchman", "Steward"]
        self.assertEqual(self.ways(SPY, roles), (True, True))

    def test_and_a_spy_may_be_passed_over(self):
        """The Spy is one step clockwise and may read as good; then the
        Imp, two steps anticlockwise, is the closest."""
        roles = ["Imp", "Knight", "Shugenja", "Spy", "King",
                 "Nightwatchman", "Steward"]
        self.assertEqual(self.ways(SPY, roles), (True, True))

    def test_but_nothing_makes_a_plain_demon_read_good(self):
        roles = ["Recluse", "Knight", "Shugenja", "Imp", "King",
                 "Nightwatchman", "Steward"]
        # Imp one step clockwise; the Recluse two back can at best tie
        # nothing — it is further away.
        self.assertEqual(self.ways(SPY, roles), (True, False))

    def test_under_a_vortox_it_is_the_other_way(self):
        roles = ["Steward", "Knight", "Shugenja", "Vortox", "King",
                 "Nightwatchman", "Witch"]
        self.assertEqual(self.ways(VORTOX, roles), (False, True))

    def test_and_a_tie_under_a_vortox_still_allows_either(self):
        """Arbitrary is neither true nor false, so there is nothing for
        a Vortox to turn round."""
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Vortox", "Witch"]
        self.assertEqual(self.ways(VORTOX, roles), (True, True))


class TheNightwatchman(SolverTest):
    """Points at a player once a game; that player learns who it is."""

    def test_the_player_it_woke_names_the_right_seat(self):
        self.assertEqual(
            cost(SPY, SEVEN, [I.NightwatchmanSeen(1, 0, shown=3)]), 1.0)

    def test_a_wrong_name_was_made_up_not_poisoned(self):
        """A droisoned Nightwatchman wakes nobody, so no poison explains
        somebody being shown the wrong seat. With a Poisoner in the world
        to blame, the row is still charged as invented."""
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Imp", "Poisoner"]
        wrong = cost(SPY, roles, [I.NightwatchmanSeen(1, 0, shown=1)])
        self.assertEqual(wrong, S.FABRICATED_INFO_PENALTY)

    def test_an_evil_player_can_say_anything(self):
        self.assertEqual(
            cost(SPY, SEVEN, [I.NightwatchmanSeen(1, 5, shown=1)]),
            S.FABRICATED_INFO_PENALTY)

    def test_a_drunk_with_the_token_wakes_nobody(self):
        """The wiki's second example. The Drunk has no ability, so the
        player it pointed at was never woken."""
        roles = ["Steward", "Knight", "Shugenja", "Drunk", "King", "Imp",
                 "Spy"]
        believes = [None, None, None, "Nightwatchman", None, None, None]
        self.assertEqual(
            cost(SPY, roles, [I.NightwatchmanSeen(1, 0, shown=3)],
                 believes=believes),
            S.FABRICATED_INFO_PENALTY)

    def test_it_was_working_that_night(self):
        """So the one seat a Poisoner cannot have hit is the
        Nightwatchman's — and a Steward shown the Demon then has nobody
        to blame."""
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Imp", "Poisoner"]
        seen = I.NightwatchmanSeen(1, 0, shown=3)
        self.assertIsNotNone(cost(SPY, roles, [seen]))
        # The Poisoner can explain a Knight shown the Demon...
        self.assertIsNotNone(cost(
            SPY, roles, [seen, I.KnightInfo(1, 1, a=5, b=0)]))
        world = World(tuple(roles), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(roles)), infos=[seen])
        # ...but the row itself says the Nightwatchman was not its mark.
        self.assertEqual(seen.leaned_on(world, state, 3), (3,))

    def test_it_is_never_attributed_to_a_claim(self):
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)))
        self.assertIsNone(I.NightwatchmanSeen(1, 0, shown=3)
                          .source_seat(state))

    def test_killed_before_its_turn_it_woke_nobody(self):
        """It acts late, after the kills."""
        row = I.NightwatchmanSeen(2, 0, shown=3)
        self.assertEqual(cost(SPY, SEVEN, [row], deaths={3: "N2"}),
                         S.FABRICATED_INFO_PENALTY)

    def test_a_player_killed_that_night_is_still_shown(self):
        """"Choose a player" means any player."""
        row = I.NightwatchmanSeen(2, 0, shown=3)
        self.assertEqual(cost(SPY, SEVEN, [row], deaths={0: "N2"}), 1.0)

    def test_under_a_vortox_the_wrong_player_is_shown(self):
        """The wiki's third example."""
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Vortox", "Witch"]
        self.assertIsNone(
            cost(VORTOX, roles, [I.NightwatchmanSeen(1, 0, shown=3)]))
        self.assertEqual(
            cost(VORTOX, roles, [I.NightwatchmanSeen(1, 0, shown=1)]), 1.0)

    def test_what_it_says_it_did_proves_nothing(self):
        """Table decision, 05.10.2026. Its own row holds whoever it
        names and whatever they are."""
        world = World(tuple(SEVEN), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)))
        for target in range(7):
            with self.subTest(target=target):
                self.assertTrue(I.NightwatchmanChoice(1, 3, target=target)
                                .holds(world, state, None, 3))
        self.assertFalse(I.NightwatchmanChoice(1, 3, target=0)
                         .is_information(state))

    def test_it_is_woken_until_it_points(self):
        world = World(tuple(SEVEN), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)),
                          infos=[I.NightwatchmanChoice(2, 3, target=0)])
        self.assertEqual([waking.woke(world, state, 3, n) for n in (1, 2, 3)],
                         [True, True, False])
        self.assertFalse(waking.uncertain(world, state, 3, 3))

    def test_with_nothing_said_only_the_first_night_is_certain(self):
        world = World(tuple(SEVEN), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)))
        self.assertFalse(waking.uncertain(world, state, 3, 1))
        self.assertTrue(waking.woke(world, state, 3, 1))
        self.assertTrue(waking.uncertain(world, state, 3, 2))

    def test_somebody_elses_row_does_not_date_its_choice(self):
        """The player it woke speaks a row with the same source."""
        world = World(tuple(SEVEN), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)),
                          infos=[I.NightwatchmanSeen(1, 0, shown=3)])
        self.assertTrue(waking.uncertain(world, state, 3, 2))


class TheKing(SolverTest):
    """A living character each night, once the dead equal or outnumber
    the living."""

    #  after night 3: seats 0, 1, 2 and 6 are dead; 3, 4 and 5 stand.
    DEATHS = {6: "E1", 0: "N2", 1: "E2", 2: "N3"}

    def test_it_learns_a_character_somebody_alive_holds(self):
        self.assertEqual(cost(
            SPY, SEVEN, [I.KingInfo(3, 4, role="Nightwatchman")],
            deaths=self.DEATHS), 1.0)

    def test_not_one_only_the_dead_hold(self):
        self.assertIsNone(cost(
            SPY, SEVEN, [I.KingInfo(3, 4, role="Steward")],
            deaths=self.DEATHS))

    def test_it_counts_tonights_dead(self):
        """Table decision, 05.10.2026. Before night three there are
        three dead and four alive; the kill that night makes it four and
        three, and the King — acting after it — learns something."""
        world = World(tuple(SEVEN), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)), deaths=self.DEATHS)
        self.assertEqual(len(state.alive_at("N3")), 4)
        self.assertTrue(I.the_dead_outnumber_or_equal(world, state, 3))
        self.assertFalse(I.the_dead_outnumber_or_equal(world, state, 2))

    def test_before_that_it_learns_nothing(self):
        early = I.KingInfo(2, 4, role="Nightwatchman")
        self.assertIsNone(cost(SPY, SEVEN, [early], deaths=self.DEATHS))
        self.assertEqual(cost(SPY, SEVEN, [I.KingInfo(2, 4, role="")],
                              deaths=self.DEATHS), 1.0)

    def test_and_saying_nothing_when_it_should_have_learned_does_not_fit(self):
        self.assertIsNone(cost(SPY, SEVEN, [I.KingInfo(3, 4, role="")],
                               deaths=self.DEATHS))

    def test_a_spy_may_be_shown_as_a_townsfolk(self):
        """By registration, as for an Undertaker."""
        roles = ["Steward", "Knight", "Shugenja", "Spy", "King", "Imp",
                 "Nightwatchman"]
        self.assertEqual(cost(
            SPY, roles, [I.KingInfo(3, 4, role="Monk")],
            deaths=self.DEATHS), 1.0)

    def test_it_wakes_only_then(self):
        world = World(tuple(SEVEN), (None,) * 7)
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(SEVEN)), deaths=self.DEATHS)
        self.assertEqual([waking.woke(world, state, 4, n) for n in (1, 2, 3)],
                         [False, False, True])

    def test_under_a_vortox_it_is_shown_a_character_nobody_alive_holds(self):
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Vortox", "Witch"]
        self.assertIsNone(cost(
            VORTOX, roles, [I.KingInfo(3, 4, role="Nightwatchman")],
            deaths=self.DEATHS))
        self.assertEqual(cost(
            VORTOX, roles, [I.KingInfo(3, 4, role="Steward")],
            deaths=self.DEATHS), 1.0)


class TheKingAndAZombuulUnderItsShroud(SolverTest):
    """Table decision, 05.10.2026: the King counts by what is so."""

    #  Four executions, four quiet nights. The board shows four dead and
    #  three alive before night five.
    DEATHS = {5: "E1", 0: "E2", 1: "E3", 6: "E4"}
    QUIET = {2, 3, 4, 5}

    def board(self, roles, infos):
        return cost(SPY, roles, infos, deaths=self.DEATHS,
                    quiet_nights=self.QUIET)

    def test_the_zombuul_is_among_the_living(self):
        """So with it "dead" the count is four alive to three dead, and
        the King learns nothing."""
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Zombuul", "Spy"]
        self.assertEqual(self.board(roles, [I.KingInfo(5, 4, role="")]), 1.0)
        self.assertIsNone(
            self.board(roles, [I.KingInfo(5, 4, role="Shugenja")]))

    def test_whichever_of_the_dead_it_is(self):
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Poisoner", "Zombuul"]
        self.assertEqual(self.board(roles, [I.KingInfo(5, 4, role="")]), 1.0)

    def test_a_king_told_nothing_puts_the_demon_among_the_dead(self):
        """The whole point of entering it. As many crossed off as not,
        the King awake to say it learned nothing: one of the dead is not
        dead, and that is what a Zombuul is."""
        claims = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                  "Empath", "Chef"]
        events = {5: ("E1",), 0: ("E2",), 1: ("E3",), 6: ("E4",)}
        state = GameState(n_players=7, script=SPY,
                          claims=dict(enumerate(claims)), deaths=events,
                          quiet_nights=self.QUIET,
                          infos=[I.KingInfo(5, 4, role="")])
        _all, valid = S.solve(state)
        self.assertTrue(valid)
        rows = S.summarize(valid, state)
        on_the_dead = sum(rows[seat]["demon_pct"] for seat in events)
        self.assertGreater(on_the_dead, 80.0)

    def test_and_it_may_be_shown_the_zombuul_as_alive(self):
        #  Nine players and six crossed off: five really dead, four really
        #  alive with the Zombuul, so even counting it the dead have it.
        roles = ["Steward", "Knight", "Shugenja", "Nightwatchman", "King",
                 "Zombuul", "Spy", "Monk", "Soldier"]
        deaths = {5: "E1", 0: "E2", 1: "E3", 6: "E4", 7: "E5", 8: "E6"}
        quiet = {2, 3, 4, 5, 6, 7}
        shown = cost(SPY, roles, [I.KingInfo(7, 4, role="Zombuul")],
                     deaths=deaths, quiet_nights=quiet)
        self.assertEqual(shown, 1.0)
        #  The night before it was five alive to four dead: nothing.
        self.assertEqual(
            cost(SPY, roles, [I.KingInfo(6, 4, role="")],
                 deaths=deaths, quiet_nights=quiet), 1.0)


class TheSimulatorPlaysThem(SolverTest):
    """Honestly, drunk, poisoned and under a Vortox — and the solver
    keeps the world that was played."""

    def played(self, script, games, nights=4):
        import claims as claim_model
        import simulate
        kinds, lost = set(), []
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
                kind = type(row).__name__
                if kind == "KingInfo" and not row.role:
                    kind = "KingInfo, nothing"
                kinds.add(kind)
            truth = World(tuple(deal.roles), tuple(deal.believes))
            if S.explanation_cost(truth, state) is None:
                lost.append(seed)
        return kinds, lost

    EVERY_ROW = {"StewardInfo", "KnightInfo", "ShugenjaInfo", "KingInfo",
                 "KingInfo, nothing", "NightwatchmanChoice",
                 "NightwatchmanSeen"}

    def test_with_a_spy_and_a_zombuul(self):
        kinds, lost = self.played(SPY, 300)
        self.assertEqual(lost, [])
        self.assertLessEqual(self.EVERY_ROW, kinds)

    def test_with_a_vortox(self):
        kinds, lost = self.played(VORTOX, 300)
        self.assertEqual(lost, [])
        self.assertLessEqual(self.EVERY_ROW, kinds)

    def test_a_drunk_nightwatchman_wakes_nobody(self):
        import simulate
        seen = 0
        for seed in range(400):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3, script=SPY)
            for row in heard:
                if type(row).__name__ != "NightwatchmanSeen":
                    continue
                seen += 1
                with self.subTest(seed=seed):
                    self.assertEqual(
                        deal.role_at(row.shown, f"N{row.night}"),
                        "Nightwatchman")
                    self.assertTrue(deal.working(row.shown, row.night))
        self.assertGreater(seen, 20)

    def test_a_king_under_a_zombuuls_shroud_learns_later(self):
        """Found rather than named: a game where the board shows as many
        dead as living, a Zombuul is up, and the King says it learned
        nothing."""
        import simulate
        for seed in range(400):
            rng = random.Random(seed)
            deal, heard = simulate.play(7, rng, nights=5, script=SPY)
            if deal.zombuul_up is None:
                continue
            if any(type(r).__name__ == "KingInfo" and not r.role
                   and r.night >= 4 for r in heard):
                return
        self.fail("no game in that range had a King told nothing beside "
                  "a Zombuul under its shroud")


class TheNightWalkReplaysThem(SolverTest):
    """The second, independent telling of each night.

    Four of the five only read, so they cannot change who dies; the
    Nightwatchman points at a player, which a Goon answers. What the walk
    adds is the *moment*: a King counting after the kills, a Knight
    reading after a Snake Charmer has swapped.
    """

    def nights(self, script, games=150, nights=4):
        import nightwalk
        import simulate
        for seed in range(games):
            n = [7, 8, 9, 10, 11][seed % 5]
            rng = random.Random(seed)
            deal, heard = simulate.play(n, rng, nights=nights, script=script)
            for night in range(1, min(nights,
                                      deal.game_ends_after or nights) + 1):
                hidden = nightwalk.hidden_from(deal, night, heard)
                mine = [row for row in heard if row.night == night
                        and row.source_role in FIVE]
                asked = {}
                for row in mine:
                    if isinstance(row, I.StewardInfo):
                        asked[row.player] = row.target
                    elif isinstance(row, I.KnightInfo):
                        asked[row.player] = (row.a, row.b)
                hidden[("asked", night)] = asked
                yield seed, night, deal, mine, nightwalk.walk(deal, night,
                                                              hidden)

    def test_the_deaths_come_out_the_same(self):
        for script in (SPY, VORTOX):
            for seed, night, deal, _mine, got in self.nights(script):
                if night == 1:
                    continue
                with self.subTest(script=script.name, seed=seed, night=night):
                    self.assertEqual(got.died, deal.died_on(f"N{night}"))
                    self.assertEqual(got.untold, set())

    def test_whoever_says_they_were_woken_was(self):
        checked = 0
        for script in (SPY, VORTOX):
            for seed, night, deal, mine, got in self.nights(script):
                for row in mine:
                    if not isinstance(row, I.NightwatchmanSeen):
                        continue
                    checked += 1
                    with self.subTest(script=script.name, seed=seed,
                                      night=night):
                        self.assertIn(
                            row.player,
                            list(got.woken_by_nightwatchman.values()))
        self.assertGreater(checked, 20)

    def test_the_readings_agree(self):
        """Working seats only, and no Vortox: those are told something
        untrue on purpose."""
        checked = {key: 0 for key in ("Steward", "Knight", "Shugenja",
                                      "King")}
        for seed, night, deal, mine, got in self.nights(SPY, games=250):
            answers = {(r[1], r[2]): r[3] for r in got.readings}
            for row in mine:
                key = (row.player, row.source_role)
                if key not in answers or row.source_role not in checked:
                    continue
                if not deal.working(row.player, night):
                    continue
                answer = answers[key]
                checked[row.source_role] += 1
                with self.subTest(seed=seed, night=night, row=row):
                    if isinstance(row, (I.StewardInfo, I.KnightInfo)):
                        self.assertIs(answer, True)
                    elif isinstance(row, I.ShugenjaInfo):
                        self.assertIn(answer, (None, row.clockwise))
                    elif not row.role:
                        self.assertIs(answer, False)
                    else:
                        self.assertIn(row.role, answer or ())
        for key, count in checked.items():
            with self.subTest(character=key):
                self.assertGreater(count, 20)

    def test_a_philosopher_with_its_ability_points_too(self):
        import nightwalk

        class Board:
            n = 4
            roles = ["Philosopher", "Empath", "Imp", "Monk"]

            def role_at(self, seat, _phase):
                return self.roles[seat]

            def side_at(self, seat, _phase):
                return "evil" if seat == 2 else "good"

            def alive_at(self, _phase):
                return [0, 1, 2, 3]

        got = nightwalk.walk(Board(), 2, {
            "gained": {0: "Nightwatchman"}, ("nightwatchman", 2): {0: 3}})
        self.assertEqual(got.woken_by_nightwatchman, {0: 3})

    def test_a_poisoned_one_wakes_nobody(self):
        import nightwalk

        class Board:
            n = 4
            roles = ["Nightwatchman", "Poisoner", "Imp", "Monk"]

            def role_at(self, seat, _phase):
                return self.roles[seat]

            def side_at(self, seat, _phase):
                return "evil" if seat in (1, 2) else "good"

            def alive_at(self, _phase):
                return [0, 1, 2, 3]

        got = nightwalk.walk(Board(), 2, {
            ("poisoner", 2): 0, ("nightwatchman", 2): {0: 3}})
        self.assertEqual(got.woken_by_nightwatchman, {0: None})


if __name__ == "__main__":
    unittest.main()
