"""The eighth five experimental characters (11.10.2026).

Bounty Hunter, Cult Leader, Mezepheles, Leviathan and Yaggababble. Every
reading here is the table's ruling of 11.10.2026, asked before anything
was built (readings A to Z, with its corrections to C, F, O and T).
"""

import pathlib
import random
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking      # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import Timeline, World, enumerate_worlds   # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))

EIGHTH = ("BountyHunter", "CultLeader", "Mezepheles", "Leviathan",
          "Yaggababble")

# Trouble Brewing's shape: the Soldier and the Monk against a Yaggababble,
# the Recluse and the Spy beside a Cult Leader, the Scarlet Woman to take
# a Demon on, and the Leviathan's jinxes with the Banshee, the Farmer, the
# Ravenkeeper, the Sage, the Soldier and the King.
LIKE_TB = ["banshee", "sage", "chef", "empath", "farmer",
           "undertaker", "monk", "ravenkeeper", "slayer", "soldier",
           "bountyhunter", "cultleader", "king",
           "butler", "drunk", "recluse", "saint",
           "poisoner", "spy", "scarletwoman", "mezepheles",
           "imp", "leviathan", "yaggababble"]
# Bad Moon Rising's: its protectors, the Exorcist and the Innkeeper for
# their jinxes, the Grandmother for hers, the Chambermaid to count who
# woke, and a Pukka to poison a Mezepheles after its turn.
LIKE_BMR = ["grandmother", "sailor", "chambermaid", "exorcist", "innkeeper",
            "gambler", "gossip", "courtier", "professor", "tealady", "fool",
            "bountyhunter", "cultleader", "oracle",
            "goon", "lunatic", "tinker", "moonchild",
            "godfather", "devilsadvocate", "assassin", "mezepheles",
            "pukka", "po", "leviathan", "yaggababble"]

EIGHT = scripts.from_ids("Eighth five, like Trouble Brewing", LIKE_TB)
EIGHT_BMR = scripts.from_ids("Eighth five, like Bad Moon Rising", LIKE_BMR)


def board(script, roles, infos=(), claims=None, **kw):
    n = len(roles)
    world = World(tuple(roles), (None,) * n)
    state = GameState(n_players=n, script=script,
                      claims=dict(claims if claims is not None
                                  else enumerate(roles)),
                      infos=list(infos), **kw)
    return world, state


def cost(script, roles, infos=(), **kw):
    world, state = board(script, roles, infos, **kw)
    return S.explanation_cost(world, state)


class TheyAreInTheCatalogue(SolverTest):

    def test_two_townsfolk_a_minion_and_two_demons(self):
        teams = {key: CHARACTERS[key].team for key in EIGHTH}
        self.assertEqual(teams, {"BountyHunter": "townsfolk",
                                 "CultLeader": "townsfolk",
                                 "Mezepheles": "minion",
                                 "Leviathan": "demon",
                                 "Yaggababble": "demon"})
        for key in EIGHTH:
            self.assertTrue(CHARACTERS[key].modelled)

    def test_the_yaggababble_acts_where_the_publisher_puts_it(self):
        """Early on the first night, shown its phrase before the Minions
        learn each other; on the others after Lil' Monsta and before the
        Kazali (the night sheet, 23.10.2026)."""
        c = CHARACTERS
        self.assertLess(c["Yaggababble"].first_night, c["Snitch"].first_night)
        self.assertLess(c["Philosopher"].first_night,
                        c["Yaggababble"].first_night)
        self.assertLess(c["LilMonsta"].other_night,
                        c["Yaggababble"].other_night)
        self.assertLess(c["Yaggababble"].other_night,
                        c["Kazali"].other_night)

    def test_the_two_demons_kill_their_own_way(self):
        self.assertLessEqual({"Leviathan", "Yaggababble"},
                             S.KILLS_ITS_OWN_WAY)

    def test_the_named_games_do_not_draw_them(self):
        import play_games
        for seed in range(200):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  as_named=True)
            with self.subTest(seed=seed):
                self.assertFalse(set(EIGHTH) & set(script.keys))


def stories(script, roles, infos=(), **kw):
    """Every story that fits, as (cost, the seats turned evil in it)."""
    world, state = board(script, roles, infos, **kw)
    viable = []
    S.best_story(world, state, viable=viable)
    return [(got, sorted(c.seat for c in changes if c.side == "evil"))
            for got, changes in viable]


#        0       1        2        3              4            5        6
BH = ["Chef", "Empath", "Monk", "Soldier", "BountyHunter", "Saint", "Imp"]


class TheBountyHunter(SolverTest):

    def test_one_townsfolk_is_evil_and_any_of_them_may_be(self):
        # Way 2 of C: the Bounty Hunter itself too.
        turned = sorted(seats[0] for _c, seats in stories(EIGHT, BH))
        self.assertEqual(turned, [0, 1, 2, 3, 4])

    def test_not_for_a_drunk_holding_the_token(self):
        roles = ["Chef", "Empath", "Monk", "Soldier", "Drunk", "Saint", "Imp"]
        world = World(tuple(roles), (None, None, None, None, "BountyHunter",
                                     None, None))
        state = GameState(n_players=7, script=EIGHT,
                          claims={**dict(enumerate(roles)), 4: "BountyHunter"})
        self.assertEqual(S.possible_timelines(world, state), [((), 1.0)])

    def test_shown_the_demon(self):
        self.assertEqual(cost(EIGHT, BH, [I.BountyHunterInfo(1, 4, target=6)]),
                         1.0)

    def test_shown_a_townsfolk_it_is_the_evil_one(self):
        # Or the Bounty Hunter is, and made it up — which costs.
        row = [I.BountyHunterInfo(1, 4, target=0)]
        self.assertEqual(stories(EIGHT, BH, row),
                         [(1.0, [0]), (S.FABRICATED_INFO_PENALTY, [4])])

    def test_shown_an_outsider_it_was_not_working_or_it_lies(self):
        # The Saint is good and registers as nothing else. Nothing here
        # can poison the Bounty Hunter, so it is the evil Townsfolk
        # itself, and made the reading up.
        row = [I.BountyHunterInfo(1, 4, target=5)]
        self.assertEqual(stories(EIGHT, BH, row),
                         [(S.FABRICATED_INFO_PENALTY, [4])])

    def test_the_recluse_may_be_shown(self):
        roles = ["Chef", "Empath", "Monk", "Soldier", "BountyHunter",
                 "Recluse", "Imp"]
        # Whichever Townsfolk is the evil one, the Recluse may be shown.
        got = stories(EIGHT, roles, [I.BountyHunterInfo(1, 4, target=5)])
        self.assertEqual(len([c for c, _s in got if c == 1.0]), 5)

    def test_the_evil_townsfolk_counts_for_the_chef(self):
        # The Imp at 6 sits beside the Chef at 0 and the Saint at 5: a
        # pair only if the Chef is the evil Townsfolk — who then may lie
        # anyway — or the count is made up.
        none = stories(EIGHT, BH, [I.Chef(1, 0, count=0)])
        self.assertEqual(sorted(s[0] for c, s in none if c == 1.0),
                         [1, 2, 3, 4])
        two = stories(EIGHT, BH, [I.Chef(1, 0, count=2)])
        self.assertEqual([(c, s) for c, s in two if c == 1.0], [])

    def test_a_second_one_only_once_the_first_has_died(self):
        first = I.BountyHunterInfo(1, 4, target=6)
        roles = ["Chef", "Empath", "Monk", "Soldier", "BountyHunter",
                 "Poisoner", "Imp", "ScarletWoman"]
        later = I.BountyHunterInfo(2, 4, target=7)
        alive = stories(EIGHT, roles, [first, later], days_done={1})
        dead = stories(EIGHT, roles, [first, later],
                       deaths={6: ("E1",), 0: ("N2",)})
        self.assertTrue(all(c < 1.0 for c, _s in alive))
        self.assertTrue(any(c == 1.0 for c, _s in dead))

    def test_never_the_same_player_twice(self):
        roles = ["Chef", "Empath", "Monk", "Soldier", "BountyHunter",
                 "Poisoner", "Imp", "ScarletWoman"]
        rows = [I.BountyHunterInfo(1, 4, target=5),
                I.BountyHunterInfo(2, 4, target=5)]
        got = stories(EIGHT, roles, rows, deaths={5: ("E1",), 0: ("N2",)})
        self.assertTrue(all(c < 1.0 for c, _s in got))

    def test_an_evil_townsfolk_may_lie_and_it_costs_a_made_up_reading(self):
        # Seat 1's neighbours are 0 and 2. Two evil there needs both to
        # be evil; one of them at most is, so the Empath is the liar.
        got = stories(EIGHT, BH, [I.Empath(1, 1, count=2)])
        self.assertEqual(got, [(S.FABRICATED_INFO_PENALTY, [1])])

    def test_under_a_vortox_the_shown_player_is_really_good(self):
        script = scripts.from_ids("with a Vortox", LIKE_TB + ["vortox"])
        roles = ["Chef", "Empath", "Monk", "Soldier", "BountyHunter",
                 "Saint", "Vortox"]
        good = stories(script, roles, [I.BountyHunterInfo(1, 4, target=5)])
        evil = stories(script, roles, [I.BountyHunterInfo(1, 4, target=6)])
        self.assertTrue(any(c == 1.0 for c, _s in good))
        self.assertEqual([s for c, s in evil if c == 1.0], [[4]])

    def test_one_townsfolks_false_claim_beside_it_costs_no_more_than_a_bluff(
            self):
        claims = dict(enumerate(BH))
        claims[2] = "Slayer"
        world, state = board(EIGHT, BH, claims=claims)
        with_one = S.prior_weight(world, state)
        without = ["Chef", "Empath", "Monk", "Soldier", "King", "Saint",
                   "Imp"]
        claims = dict(enumerate(without))
        claims[2] = "Slayer"
        world, state = board(EIGHT, without, claims=claims)
        self.assertGreater(with_one, S.prior_weight(world, state))

    def test_it_wakes_the_first_night_and_when_shown_another(self):
        world, state = board(EIGHT_BMR,
                             ["Chambermaid", "BountyHunter", "Sailor",
                              "Gossip", "Fool", "Assassin", "Po"],
                             [I.BountyHunterInfo(3, 1, target=5)],
                             deaths={6: ("E2",)})
        self.assertTrue(waking.woke(world, state, 1, 1))
        self.assertFalse(waking.woke(world, state, 1, 2))
        self.assertTrue(waking.woke(world, state, 1, 3))


def sides(script, roles, seat, phase, changes=(), **kw):
    world, state = board(script, roles, **kw)
    view = Timeline(world, tuple(changes)) if changes else world
    state._hidden = None
    return I.cult_sides(view, state, seat, phase)


class TheCultLeader(SolverTest):

    def test_between_two_good_players_it_stays_good(self):
        roles = ["Chef", "CultLeader", "Empath", "Soldier", "Monk", "Imp",
                 "ScarletWoman"]
        self.assertEqual(sides(EIGHT, roles, 1, "D1"), {False})
        self.assertEqual(sides(EIGHT, roles, 1, "N3", days_done={1, 2}),
                         {False})

    def test_between_two_evil_players_it_turns_evil(self):
        roles = ["Imp", "CultLeader", "ScarletWoman", "Soldier", "Monk",
                 "Chef", "Empath"]
        self.assertEqual(sides(EIGHT, roles, 1, "N1"), {False})  # not yet
        self.assertEqual(sides(EIGHT, roles, 1, "D1"), {True})

    def test_beside_one_of_each_it_may_be_either(self):
        roles = ["Imp", "CultLeader", "Chef", "Soldier", "Monk",
                 "ScarletWoman", "Empath"]
        self.assertEqual(sides(EIGHT, roles, 1, "D1"), {True, False})

    def test_a_neighbour_registering_evil_is_enough(self):
        # Table ruling, 11.10.2026: beside a Townsfolk and the Recluse it
        # may turn evil, though both are good.
        roles = ["Recluse", "CultLeader", "Chef", "Soldier", "Monk", "Imp",
                 "ScarletWoman"]
        self.assertEqual(sides(EIGHT, roles, 1, "D1"), {True, False})
        spy = ["Spy", "CultLeader", "Imp", "Soldier", "Monk", "Chef",
               "Empath"]
        self.assertEqual(sides(EIGHT, spy, 1, "D1"), {True, False})

    def test_a_zombuul_under_its_shroud_is_no_neighbour(self):
        # The same ruling: it registers as dead. So past it sits the
        # Chef, and both neighbours are good.
        script = scripts.from_ids("with a Zombuul", LIKE_BMR + ["zombuul"])
        roles = ["Zombuul", "CultLeader", "Grandmother", "Gossip", "Fool",
                 "Assassin", "Chambermaid"]
        # Beside the Zombuul and the Grandmother on the first night.
        self.assertEqual(sides(script, roles, 1, "D1"), {True, False})
        # Executed on day one it lives on under its shroud. On night two
        # the Cult Leader's neighbours are the Chambermaid, past it, and
        # the Grandmother: both good, and nothing here could have kept
        # it on the side it had.
        self.assertEqual(sides(script, roles, 1, "D2", deaths={0: ("E1",)},
                               days_done={1, 2}), {False})

    def test_dead_it_keeps_the_side_it_had(self):
        roles = ["Imp", "CultLeader", "ScarletWoman", "Soldier", "Monk",
                 "Chef", "Empath"]
        self.assertEqual(sides(EIGHT, roles, 1, "D2", deaths={
            1: ("E1",), 0: ("E1",)}, days_done={1, 2}), {True})

    def test_where_something_could_poison_it_the_old_side_stays_open(self):
        roles = ["Chef", "CultLeader", "Empath", "Soldier", "Monk",
                 "Poisoner", "Imp"]
        self.assertEqual(sides(EIGHT, roles, 1, "D1"), {False})
        turned = ["Imp", "CultLeader", "Poisoner", "Soldier", "Monk",
                  "Chef", "Empath"]
        # Evil neighbours, but a Poisoner may have kept it good.
        self.assertEqual(sides(EIGHT, turned, 1, "D1"), {True, False})

    def test_an_empath_beside_it_reads_what_its_neighbours_allow(self):
        # 0 Imp, 1 Cult Leader, 2 Scarlet Woman: evil from the first day.
        # The Empath at 6 sits between 5 and the Imp at 0: on night two
        # it reads the Imp only, and from 3 it would read nobody.
        roles = ["Imp", "CultLeader", "ScarletWoman", "Empath", "Monk",
                 "Chef", "Soldier"]
        # Seat 3's neighbours are 2 (evil) and 4: one.
        self.assertEqual(cost(EIGHT, roles, [I.Empath(2, 3, count=1)],
                              days_done={1}), 1.0)
        # After the Scarlet Woman is executed its neighbours are the Cult
        # Leader and the Monk: one evil, for a Cult Leader that turned.
        self.assertEqual(cost(EIGHT, roles, [I.Empath(2, 3, count=1)],
                              deaths={2: ("E1",)}), 1.0)
        self.assertIsNone(cost(EIGHT, roles, [I.Empath(2, 3, count=0)],
                               deaths={2: ("E1",)}))

    def test_a_cult_called_and_the_game_went_on(self):
        roles = ["Chef", "CultLeader", "Empath", "Soldier", "Monk", "Imp",
                 "ScarletWoman"]
        # Everybody good joined: it cannot have been working, and nothing
        # here could have stopped it.
        all_good = I.CultCalled(1, 1, joined=frozenset({0, 2, 3, 4}))
        self.assertIsNone(cost(EIGHT, roles, [all_good], days_done={1}))
        # One good player stayed out: nothing to explain.
        one_out = I.CultCalled(1, 1, joined=frozenset({0, 2, 3, 5, 6}))
        self.assertEqual(cost(EIGHT, roles, [one_out], days_done={1}), 1.0)
        # And nothing either on the day the board ends with.
        self.assertEqual(cost(EIGHT, roles, [all_good]), 1.0)

    def test_anybody_may_call_one(self):
        roles = ["Chef", "King", "Empath", "Soldier", "Monk", "Imp",
                 "ScarletWoman"]
        row = I.CultCalled(1, 1, joined=frozenset({0, 2, 3, 4}))
        self.assertEqual(cost(EIGHT, roles, [row], days_done={1}), 1.0)

    def test_an_evil_player_made_the_cult_leader_stays_evil(self):
        from botc.worlds import Change
        roles = ["Chef", "Poisoner", "Empath", "Soldier", "Monk", "Imp",
                 "ScarletWoman"]
        made = [Change("N2", 1, "CultLeader", "evil")]
        self.assertEqual(sides(EIGHT, roles, 1, "D3", changes=made,
                               days_done={1, 2, 3}), {True})

    def test_it_may_be_the_werewolfs_faux_paw(self):
        # Open item 55 (12.10.2026): its side comes from its neighbours,
        # and a good Cult Leader can still be the good player that reads
        # evil while a Lycanthrope lives. That was never asked.
        script = scripts.from_ids("Faux paw", [
            "villageidiot", "cultleader", "lycanthrope", "chef", "empath",
            "monk", "soldier", "saint", "recluse", "scarletwoman", "spy",
            "imp"])
        roles = ["VillageIdiot", "CultLeader", "Lycanthrope", "Chef",
                 "Empath", "ScarletWoman", "Imp"]
        evil = cost(script, roles, [I.VillageIdiotInfo(1, 0, target=1,
                                                       evil=True)])
        self.assertIsNotNone(evil)
        # As much as any other good player shown as the faux paw.
        self.assertEqual(evil, cost(script, roles, [
            I.VillageIdiotInfo(1, 0, target=3, evil=True)]))
        # And without a Lycanthrope it is good beside two good players.
        plain = ["VillageIdiot", "CultLeader", "Monk", "Chef", "Empath",
                 "ScarletWoman", "Imp"]
        self.assertIsNone(cost(script, plain, [
            I.VillageIdiotInfo(1, 0, target=1, evil=True)]))

    def test_it_shows_half_evil_where_both_sides_are_open(self):
        roles = ["Imp", "CultLeader", "Chef", "Soldier", "Monk",
                 "ScarletWoman", "Empath"]
        world, state = board(EIGHT, roles, days_done={1})
        acc = S._accumulator(7)
        S._tally(acc, world, world, state, 1.0, 7, "D1")
        self.assertEqual(acc["evil"][1], 0.5)

    def test_the_chambermaid_cannot_tell_whether_it_woke(self):
        roles = ["Chambermaid", "CultLeader", "Sailor", "Gossip", "Fool",
                 "Assassin", "Po"]
        world, state = board(EIGHT_BMR, roles, days_done={1})
        self.assertFalse(waking.uncertain(world, state, 1, 1))
        beside_evil = ["Chambermaid", "Sailor", "Gossip", "Fool",
                       "CultLeader", "Assassin", "Po"]
        world, state = board(EIGHT_BMR, beside_evil, days_done={1})
        self.assertTrue(waking.uncertain(world, state, 4, 1))


#         0       1        2        3         4          5           6
MEZ = ["Chef", "Empath", "Monk", "Soldier", "King", "Mezepheles", "Imp"]


class TheMezepheles(SolverTest):

    def test_nobody_turned_is_always_a_story(self):
        self.assertEqual(stories(EIGHT, MEZ)[0], (1.0, []))

    def test_a_reading_only_a_turned_player_explains(self):
        # Seat 1's neighbours are 0 and 2, both good. One evil on night
        # three: one of them said the word.
        row = [I.Empath(3, 1, count=1)]
        got = stories(EIGHT, MEZ, row, days_done={1, 2})
        self.assertTrue(any(c == 1.0 and s in ([0], [2]) for c, s in got))
        without = ["Chef", "Empath", "Monk", "Soldier", "King", "Spy", "Imp"]
        self.assertIsNone(cost(EIGHT, without, row, days_done={1, 2}))

    def test_not_on_the_first_night(self):
        self.assertIsNone(cost(EIGHT, MEZ, [I.Empath(1, 1, count=1)]))

    def test_not_once_the_mezepheles_was_executed(self):
        row = [I.Empath(3, 1, count=1)]
        self.assertIsNone(cost(EIGHT, MEZ, row, deaths={5: ("E1",)},
                               days_done={1, 2}))
        # Executed after the night it turned somebody, it had.
        self.assertEqual(cost(EIGHT, MEZ, row, deaths={5: ("E2",)},
                              days_done={1, 2}), 1.0)

    def test_only_one_player_turns(self):
        # Two evil beside the Empath needs both its neighbours turned.
        # No story has that; the ones that fit have the Empath itself
        # turned and lying, which costs.
        got = stories(EIGHT, MEZ, [I.Empath(3, 1, count=2)],
                      days_done={1, 2})
        self.assertTrue(got)
        self.assertTrue(all(seats == [1] and c < 1.0 for c, seats in got))

    def test_the_turned_player_may_lie_from_that_night(self):
        # The Empath itself turned: what it says from then on may be
        # made up, at a price, and before that it was honest.
        late = stories(EIGHT, MEZ, [I.Empath(2, 1, count=0),
                                    I.Empath(3, 1, count=2)],
                       days_done={1, 2})
        # Turned on night two or on night three: either way the second
        # reading is the made-up one.
        self.assertEqual(late, [(S.FABRICATED_INFO_PENALTY, [1])] * 2)
        # A false reading from before anybody could have turned is not.
        self.assertIsNone(cost(EIGHT, MEZ, [I.Empath(1, 1, count=2)],
                               days_done={1, 2}))

    def test_it_had_to_be_working_that_night(self):
        roles = ["Chef", "Empath", "Monk", "Soldier", "King", "Mezepheles",
                 "Imp", "Poisoner"]
        world, state = board(EIGHT, roles, [I.Empath(3, 1, count=1)],
                             days_done={1, 2})
        state._epoch = -1
        turned = S.MezephelesTurn("N3", 0, None, "evil")
        failures, _ft, _inv, working = S._plain_failures(
            Timeline(world, (turned,)), state)
        self.assertIn(5, working[3])

    def test_a_turn_is_only_told_where_a_story_needs_it(self):
        # Everything on this board fits with nobody turned, and a turn
        # costs nothing, so it could not do better: it is not told, and
        # takes no share of the world.
        world, state = board(EIGHT, MEZ, deaths={0: ("N2",)},
                             days_done={1})
        viable = []
        S.best_story(world, state, viable=viable)
        self.assertEqual(viable, [(1.0, ())])
        # A reading that does not fit brings the turns in.
        world, state = board(EIGHT, MEZ, [I.Empath(3, 1, count=1)],
                             days_done={1, 2})
        viable = []
        S.best_story(world, state, viable=viable)
        self.assertTrue(viable)
        self.assertTrue(all(isinstance(changes[-1], S.MezephelesTurn)
                            for _cost, changes in viable))

    def test_only_seats_the_board_looks_at_are_tried(self):
        # The Empath at seat 1 looks at 0 and 2; nothing looks at 3.
        world, state = board(EIGHT, MEZ, [I.Empath(3, 1, count=1)],
                             days_done={1, 2})
        turned = {turn[0].seat
                  for turn in S.a_mezepheles_may_have_turned(world, state)}
        self.assertEqual(turned, {0, 1, 2})

    def test_it_wakes_the_first_night_only(self):
        world, state = board(EIGHT, MEZ)
        self.assertTrue(waking.woke_for_own_ability(world, state, 5, 1))
        self.assertFalse(waking.woke_for_own_ability(world, state, 5, 2))


#          0       1        2        3              4           5
LEV = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Poisoner",
       "Leviathan"]                                         # 6
SAID = I.LeviathanAnnounced(1, 0)


class TheLeviathan(SolverTest):

    def test_announced_there_is_one(self):
        self.assertEqual(cost(EIGHT, LEV, [SAID], days_done={1}), 1.0)
        imp = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Poisoner",
               "Imp"]
        self.assertIsNone(cost(EIGHT, imp, [SAID], days_done={1}))

    def test_not_announced_it_was_poisoned_on_its_first_day(self):
        # Way 2 of O, as for the Vizier.
        self.assertEqual(cost(EIGHT, LEV, days_done={1}),
                         S.POISON_HIT_PENALTY)
        nobody = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Spy",
                  "Leviathan"]
        self.assertIsNone(cost(EIGHT, nobody, days_done={1}))

    def test_nothing_is_asked_before_the_first_day(self):
        self.assertEqual(cost(EIGHT, LEV), 1.0)

    def test_it_kills_nobody(self):
        self.assertIsNone(cost(EIGHT, LEV, [SAID], deaths={0: ("N2",)}))
        self.assertEqual(cost(EIGHT, LEV, [SAID], quiet_nights={2, 3}), 1.0)

    def test_a_second_good_player_executed_and_the_game_went_on(self):
        two = cost(EIGHT, LEV, [SAID], deaths={0: ("E1",), 1: ("E2",)},
                   days_done={2})
        self.assertEqual(two, S.POISON_HIT_PENALTY)
        # One good and one evil is nothing.
        self.assertEqual(cost(EIGHT, LEV, [SAID],
                              deaths={0: ("E1",), 5: ("E2",)},
                              days_done={2}), 1.0)
        # And the second one on the day the board ends with says nothing.
        self.assertEqual(cost(EIGHT, LEV, [SAID],
                              deaths={0: ("E1",), 1: ("E2",)}), 1.0)

    def test_executed_is_enough(self):
        # A Fool walks away from its execution, and has been executed.
        roles = ["Grandmother", "Exorcist", "Chambermaid", "Fool", "Gossip",
                 "Assassin", "Leviathan"]
        got = cost(EIGHT_BMR, roles, [SAID], executions={1: 3},
                   deaths={4: ("E2",)}, days_done={2})
        self.assertIsNone(got)              # nothing here poisons it

    def test_after_day_five(self):
        self.assertEqual(cost(EIGHT, LEV, [SAID], days_done={1, 2, 3, 4}),
                         1.0)
        self.assertEqual(cost(EIGHT, LEV, [SAID],
                              days_done={1, 2, 3, 4, 5}),
                         S.POISON_HIT_PENALTY)

    def test_the_king_learns_from_the_first_death(self):
        roles = ["Chef", "Empath", "Monk", "Soldier", "King", "Poisoner",
                 "Leviathan"]
        row = I.KingInfo(2, 4, role="Monk")
        self.assertEqual(cost(EIGHT, roles, [SAID, row],
                              deaths={0: ("E1",)}), 1.0)
        self.assertLess(cost(EIGHT, roles, [SAID, row], days_done={1}), 1.0)

    def test_a_banshee_it_chose_dies_and_is_announced(self):
        roles = ["Chef", "Empath", "Monk", "Banshee", "King", "Spy",
                 "Leviathan"]
        self.assertEqual(cost(EIGHT, roles, [SAID, I.BansheeAnnounced(2, 0)],
                              deaths={3: ("N2",)}), 1.0)
        self.assertIsNone(cost(EIGHT, roles, [SAID], deaths={0: ("N2",)}))

    def test_a_farmer_it_chose_hands_the_character_on_and_lives(self):
        # Told by the seat that became it. Only beside a Leviathan is
        # there a story in which that happened with the Farmer alive.
        from botc.worlds import Change
        roles = ["Chef", "Empath", "Monk", "Farmer", "King", "Spy",
                 "Leviathan"]
        row = I.BecameInfo(2, 0, role="Farmer", was="Chef")
        handed = (Change("D2", 0, "Farmer", None),)
        world, state = board(EIGHT, roles, [SAID, row], quiet_nights={2})
        self.assertIn(handed, [c for c, _w in
                               S.possible_timelines(world, state)])
        imp = ["Chef", "Empath", "Monk", "Farmer", "King", "Spy", "Imp"]
        world, state = board(EIGHT, imp, [row], quiet_nights={2})
        self.assertEqual(S.possible_timelines(world, state), [((), 1.0)])

    def test_it_must_not_hang_the_soldier_itself(self):
        # One nominator that day, the Leviathan, and the Soldier went up:
        # good would have won. So it or the Soldier was not working.
        got = cost(EIGHT, LEV, [SAID], deaths={3: ("E1",)}, days_done={1},
                   nominations={1: {6}})
        self.assertEqual(got, S.POISON_HIT_PENALTY)
        other = cost(EIGHT, LEV, [SAID], deaths={3: ("E1",)}, days_done={1},
                     nominations={1: {0}})
        self.assertEqual(other, 1.0)
        # With two nominators the board has to say which.
        two = dict(deaths={3: ("E1",)}, days_done={1},
                   nominations={1: {0, 6}})
        self.assertEqual(cost(EIGHT, LEV, [SAID], **two), 1.0)
        self.assertEqual(cost(EIGHT, LEV, [
            SAID, I.ExecutionNomination(1, 6)], **two), S.POISON_HIT_PENALTY)

    def test_nor_the_exorcists_or_the_innkeepers(self):
        roles = ["Grandmother", "Gossip", "Chambermaid", "Exorcist",
                 "Innkeeper", "Assassin", "Leviathan"]
        base = dict(days_done={1, 2}, nominations={2: {6}})
        # Without an Innkeeper about, whose drunk could be the Exorcist.
        sober = ["Grandmother", "Gossip", "Chambermaid", "Exorcist",
                 "Tinker", "Assassin", "Leviathan"]
        named = cost(EIGHT_BMR, sober, [SAID, I.ExorcistChoice(2, 3,
                                                               target=0)],
                     deaths={0: ("E2",)}, **base)
        self.assertIsNone(named)
        guarded = cost(EIGHT_BMR, roles, [SAID, I.InnkeeperChoice(2, 4,
                                                                  a=0, b=1)],
                       deaths={0: ("E2",)}, **base)
        # One of the two it guards is drunk, never the Innkeeper itself
        # nor the Leviathan here. Nothing excuses it.
        self.assertIsNone(guarded)
        nobody = cost(EIGHT_BMR, roles, [SAID], deaths={0: ("E2",)}, **base)
        self.assertEqual(nobody, 1.0)

    def test_the_grandchild_on_the_gallows(self):
        roles = ["Grandmother", "Gossip", "Chambermaid", "Exorcist",
                 "Tinker", "Assassin", "Leviathan"]
        child = I.GrandmotherInfo(1, 0, target=2, role="Chambermaid")
        self.assertIsNone(cost(EIGHT_BMR, roles, [SAID, child],
                               deaths={2: ("E1",)}, days_done={1}))
        self.assertEqual(cost(EIGHT_BMR, roles, [SAID, child],
                              deaths={3: ("E1",)}, days_done={1}), 1.0)

    def test_choosing_the_goon_first_it_is_drunk_for_the_day(self):
        # Found at the gate: where its jinxes have it choose a good
        # player every night, the Goon may be the one, and the Leviathan
        # is drunk until dusk — so a sixth day says nothing against it.
        both = scripts.from_ids("Leviathan beside a Goon",
                                LIKE_BMR + ["sage"])
        roles = ["Grandmother", "Exorcist", "Chambermaid", "Goon", "Gossip",
                 "Assassin", "Leviathan"]
        late = dict(days_done={1, 2, 3, 4, 5})
        self.assertEqual(cost(both, roles, [SAID], **late), 1.0)
        # With nobody for it to choose among it never chooses at all.
        self.assertIsNone(cost(EIGHT_BMR, roles, [SAID], **late))
        # And not on the first night: unannounced, nothing excuses it.
        self.assertIsNone(cost(both, roles, days_done={1}))

    def test_it_wakes_only_for_its_jinxes(self):
        world, state = board(EIGHT_BMR,
                             ["Grandmother", "Sailor", "Chambermaid",
                              "Exorcist", "Innkeeper", "Assassin",
                              "Leviathan"])
        self.assertFalse(waking.woke(world, state, 6, 2))
        self.assertFalse(waking.uncertain(world, state, 6, 2))
        world, state = board(EIGHT, LEV)        # a Ravenkeeper on the script
        self.assertTrue(waking.woke(world, state, 6, 2))


#          0       1        2        3              4           5
YAG = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Spy",
       "Yaggababble"]                                       # 6


class TheYaggababble(SolverTest):

    def test_one_body_costs_nothing(self):
        self.assertEqual(cost(EIGHT, YAG, deaths={0: ("N2",)}), 1.0)

    def test_each_one_more_costs(self):
        two = cost(EIGHT, YAG, deaths={0: ("N2",), 1: ("N2",)})
        three = cost(EIGHT, YAG, deaths={0: ("N2",), 1: ("N2",),
                                         4: ("N2",)})
        self.assertEqual(two, S.YAGGABABBLE_AGAIN_PENALTY)
        self.assertEqual(three, S.YAGGABABBLE_AGAIN_PENALTY ** 2)

    def test_an_imp_has_no_second_body(self):
        imp = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Spy",
               "Imp"]
        self.assertIsNone(cost(EIGHT, imp, deaths={0: ("N2",), 1: ("N2",)}))

    def test_a_quiet_night_costs_nothing(self):
        self.assertEqual(cost(EIGHT, YAG, quiet_nights={2, 3}), 1.0)

    def test_nobody_dies_on_the_first_night(self):
        self.assertIsNone(cost(EIGHT, YAG, deaths={0: ("N1",)}))

    def test_they_are_the_demons_kills(self):
        # A sober Soldier does not die of them; nothing here poisons it.
        self.assertIsNone(cost(EIGHT, YAG, deaths={3: ("N2",)}))
        # And a Sage it kills learns of it.
        roles = ["Chef", "Empath", "Monk", "Sage", "Undertaker", "Spy",
                 "Yaggababble"]
        self.assertEqual(cost(EIGHT, roles, [I.SageInfo(2, 3, a=0, b=6)],
                              deaths={3: ("N2",)}), 1.0)

    def test_never_itself(self):
        roles = YAG[:5] + ["ScarletWoman", "Yaggababble", "King"]
        self.assertIsNone(cost(EIGHT, roles, deaths={6: ("N2",)}))

    def test_poisoned_that_night_it_kills_nobody(self):
        roles = ["Chef", "Empath", "Monk", "Soldier", "Undertaker",
                 "Poisoner", "Yaggababble"]
        world, state = board(EIGHT, roles, deaths={0: ("N2",)})
        accounts = S._explained_night(world, state, 2)
        self.assertTrue(accounts)
        self.assertTrue(all(6 in working for _c, _i, working, _b in accounts))

    def test_the_exorcist_naming_it_stops_it(self):
        # Their jinx, and every Demon's rule. Nothing here could have
        # stopped the Exorcist, and nobody else kills.
        roles = ["Grandmother", "Professor", "Chambermaid", "Exorcist",
                 "Fool", "DevilsAdvocate", "Yaggababble"]
        named = [I.ExorcistChoice(2, 3, target=6)]
        self.assertIsNone(cost(EIGHT_BMR, roles, named,
                               deaths={0: ("N2",)}))
        other = [I.ExorcistChoice(2, 3, target=5)]
        self.assertIsNotNone(cost(EIGHT_BMR, roles, other,
                                  deaths={0: ("N2",)}))

    def test_somebody_dropping_dead_as_they_nominate(self):
        # Way 1 of X: a Witch, or a Yaggababble by day, which is rare.
        got = cost(EIGHT, YAG, deaths={0: ("D1",)}, witch_deaths={1: 0},
                   days_done={1})
        self.assertEqual(got, S.YAGGABABBLE_BY_DAY_PENALTY)
        imp = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Spy",
               "Imp"]
        self.assertIsNone(cost(EIGHT, imp, deaths={0: ("D1",)},
                               witch_deaths={1: 0}, days_done={1}))

    def test_it_is_shown_its_phrase_and_that_counts(self):
        world, state = board(EIGHT, YAG)
        self.assertTrue(waking.woke_for_own_ability(world, state, 6, 1))
        self.assertFalse(waking.uncertain(world, state, 6, 1))
        self.assertFalse(waking.woke_for_own_ability(world, state, 6, 2))
        # An Imp on its first night stays open, as it was.
        imp = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Spy",
               "Imp"]
        world, state = board(EIGHT, imp)
        self.assertTrue(waking.uncertain(world, state, 6, 1))


class TheSimulatorPlaysThem(SolverTest):

    def games(self, script, how_many=300, nights=4):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=nights,
                                      script=script)

    def test_a_bounty_hunter_brings_one_evil_townsfolk(self):
        dealt = itself = 0
        for script in (EIGHT, EIGHT_BMR):
            for seed, (deal, heard) in self.games(script):
                with self.subTest(script=script.name, seed=seed):
                    if "BountyHunter" not in deal.roles:
                        self.assertIsNone(deal.bh_evil)
                        continue
                    dealt += 1
                    self.assertEqual(
                        CHARACTERS[deal.roles[deal.bh_evil]].team,
                        "townsfolk")
                    self.assertEqual(deal.side_at(deal.bh_evil, "N1"),
                                     "evil")
                    itself += deal.roles[deal.bh_evil] == "BountyHunter"
        self.assertGreater(dealt, 150)
        self.assertGreater(itself, 5)          # way 2 of C

    def test_a_mezepheles_turns_one_good_player_at_most(self):
        turned = 0
        for script in (EIGHT, EIGHT_BMR):
            for seed, (deal, _heard) in self.games(script):
                if not deal.mez_turned:
                    continue
                turned += 1
                seat, night = deal.mez_turned
                with self.subTest(script=script.name, seed=seed):
                    self.assertGreaterEqual(night, 2)
                    self.assertEqual(deal.side_at(seat, f"D{night - 1}"),
                                     "good")
                    # That night: a Cult Leader it turned may be good
                    # again by the morning, and a Goon as soon as
                    # somebody good chooses it.
                    if deal.role_at(seat, f"N{night}") != "Goon":
                        self.assertEqual(deal.side_at(seat, f"N{night}"),
                                         "evil")
        self.assertGreater(turned, 40)

    def test_a_cult_leader_changes_sides_and_calls_its_cult(self):
        changes = calls = 0
        for seed, (deal, heard) in self.games(EIGHT):
            changes += len(deal.cult_woke)
            calls += sum(isinstance(row, I.CultCalled) for row in heard)
        self.assertGreater(changes, 50)
        self.assertGreater(calls, 30)

    def test_a_leviathan_kills_nobody_and_ends_the_game_its_own_way(self):
        ended = announced = quiet = 0
        for seed, (deal, heard) in self.games(EIGHT_BMR, nights=6):
            if "Leviathan" not in deal.roles:
                continue
            announced += any(isinstance(row, I.LeviathanAnnounced)
                             for row in heard)
            ended += deal.ended_why == "leviathan"
            # No Banshee on this script, so nobody dies of it at all.
            with self.subTest(seed=seed):
                for night, killed in deal.demon_killed.items():
                    self.assertEqual(killed, [])
                    quiet += 1
        self.assertGreater(announced, 60)
        self.assertGreater(ended, 20)
        self.assertGreater(quiet, 200)

    def test_a_cautious_village_hangs_fewer_beside_a_leviathan(self):
        # T of the readings: knowing a Leviathan is in play the village
        # executes carefully, and after one good player hardly at all.
        def hanged(with_it):
            days = executed = 0
            for seed, (deal, _heard) in self.games(EIGHT, nights=4):
                if (deal.lev_announced is not None) != with_it:
                    continue
                record = deal.record()
                gone = sum(any(str(at).startswith("E") for at in ats)
                           for ats in record["deaths"].values())
                days += max(1, deal.nights_played - 1)
                executed += gone + len(record["executions"])
            return executed / days
        self.assertLess(hanged(True), 0.75 * hanged(False))

    def test_a_yaggababble_kills_none_one_or_several(self):
        seen = set()
        for seed, (deal, _heard) in self.games(EIGHT):
            if "Yaggababble" not in deal.roles:
                continue
            for killed in deal.demon_killed.values():
                seen.add(min(len(killed), 2))
        self.assertEqual(seen, {0, 1, 2})

    def test_no_other_script_plays_differently(self):
        import hashlib
        import simulate
        digest = hashlib.sha256()
        for seed in range(60):
            deal, heard = simulate.play(9, random.Random(seed), nights=3,
                                        script=scripts.BAD_MOON_RISING)
            digest.update(repr((deal.roles, sorted(deal.deaths.items()),
                                [repr(r) for r in heard])).encode())
        from test_experimental_2 import BMR_SIXTY
        self.assertEqual(digest.hexdigest()[:16], BMR_SIXTY)

    def test_the_true_world_is_kept(self):
        import claims as C
        import simulate
        lost = []
        for script in (EIGHT, EIGHT_BMR):
            for seed in range(120):
                n = [7, 8, 9, 10, 11][seed % 5]
                rng = random.Random(seed)
                deal, heard = simulate.play(n, rng, nights=4, script=script)
                cl, wk, _ = C.claims_for(deal, rng, script=script)
                state = GameState(n_players=n, script=script, claims=cl,
                                  wakes=wk, infos=list(heard),
                                  votes=dict(deal.votes),
                                  nominations=dict(deal.nominations),
                                  **deal.record())
                if S.explanation_cost(deal.world(), state) is None:
                    lost.append((script.name, seed))
        self.assertEqual(lost, [])


KNOWN = set()


class TheNightWalkReplaysThem(SolverTest):
    """The Mezepheles turns at its slot, a Yaggababble's bodies are told
    to the walk, and a Leviathan kills only the Banshee it chose."""

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = 0
        for script in (EIGHT, EIGHT_BMR):
            for seed in range(150):
                n = [7, 8, 9, 10, 11][seed % 5]
                deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                            script=script)
                for night in range(2, deal.nights_played + 1):
                    if (script.name, seed, night) in KNOWN:
                        continue
                    hidden = nightwalk.hidden_from(deal, night, heard)
                    got = nightwalk.walk(deal, night, hidden)
                    nights += 1
                    with self.subTest(script=script.name, seed=seed,
                                      night=night):
                        self.assertEqual(got.died,
                                         deal.died_on(f"N{night}"))
                        self.assertEqual(got.untold, set())
        self.assertGreater(nights, 500)


if __name__ == "__main__":
    unittest.main()
