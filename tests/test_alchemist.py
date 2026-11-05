"""The Alchemist, group 1 (04.11.2026, claude/alchemist-lesarten.md and
claude/alchemist-gruppen.md).

"You have a Minion ability. When using this, the Storyteller may prompt
you to choose differently." Patrick's answers of 04.11.2026:

  * A Weg 1: in groups; group 1 is the scaffold and the Minions that
    choose at night (Poisoner, Witch, Devil's Advocate, Fearmonger,
    Cerenovus, Harpy, Assassin).
  * B Weg 1: a row "the Alchemist has the X ability"; without it every
    Minion of the script is tried.
  * C Weg 1: a Minion in play or not.
"""

import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking, worlds  # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import (AlchemistGift, Timeline, World,  # noqa: E402
                         alchemist_gift_change)

IDS = ["chef", "empath", "fortuneteller", "washerwoman", "investigator",
       "undertaker", "alchemist", "saint", "philosopher", "butler",
       "recluse", "godfather", "xaan", "vizier", "psychopath", "goblin",
       "boomdandy", "scarletwoman", "eviltwin", "mezepheles", "pithag",
       "dreamer",
       "poisoner", "witch", "assassin", "devilsadvocate", "cerenovus",
       "fearmonger", "spy", "baron", "imp"]
SC = scripts.from_ids("Alchemist", IDS)

#    0       1         2                3              4
R = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Alchemist",
     #  5     6
     "Spy", "Imp"]
# The same table with an Investigator where the Alchemist sits.
PLAIN = R[:4] + ["Investigator"] + R[5:]
C = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Alchemist",
     "Undertaker", "Chef"]


def state(rows=(), claims=C, days=(1, 2), **kw):
    return GameState(n_players=len(claims), script=SC,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def offers(rows=()):
    """{ability: cost} the Alchemist in seat 4 may hold."""
    return {way[0].gift: cost
            for way, cost in S.alchemist_offers(world(), state(rows), 4)}


def explained(roles=R, rows=(), **kw):
    """(cost, the Alchemist's ability) of the best story, or (None, ())."""
    cost, changes = S.best_story(world(roles), state(rows, **kw))
    if cost is None:
        return None, ()
    return cost, tuple(c.gift for c in changes
                       if isinstance(c, AlchemistGift))


class WhatItMayHold(SolverTest):

    def test_each_seen_one_and_the_rest(self):
        got = offers()
        self.assertEqual(set(got), {"*", "Poisoner", "Witch", "Assassin",
                                    "DevilsAdvocate", "Cerenovus",
                                    "Fearmonger", "Xaan", "Vizier",
                                    "Psychopath", "Goblin", "Boomdandy",
                                    "ScarletWoman", "EvilTwin",
                                    "Mezepheles", "PitHag"})
        # One the town cannot see (the Spy): each seen one costs one, the
        # rest one. The Baron is not offered: the deal has no two Outsiders
        # more (group 2, 04.11.2026).
        self.assertEqual(got["*"], 1.0)
        self.assertAlmostEqual(got["Witch"], 1.0)
        self.assertNotIn("Baron", got)

    def test_a_row_names_it(self):
        self.assertEqual(offers([I.AlchemistHas(1, 4, role="Witch")]),
                         {"Witch": 1.0})
        # Not a Minion of the script: no world.
        self.assertEqual(offers([I.AlchemistHas(1, 4, role="Imp")]), {})
        self.assertIsNone(explained(rows=[I.AlchemistHas(1, 4,
                                                         role="Imp")])[0])

    def test_it_is_good(self):
        view = Timeline(world(), (alchemist_gift_change(4, "Poisoner"),))
        self.assertFalse(view.evil_at(4, "N2"))
        self.assertEqual(view.role_at(4, "N2"), "Alchemist")


class WhatItDoes(SolverTest):

    def test_a_witch_curse_without_a_witch(self):
        kw = dict(deaths={0: ("D2",)}, witch_deaths={2: 0})
        cost, gift = explained(**kw)
        self.assertIsNotNone(cost)
        self.assertEqual(gift, ("Witch",))
        self.assertIsNone(explained(PLAIN, **kw)[0])

    def test_a_devils_advocate_saves_from_the_gallows(self):
        kw = dict(executions={1: 0})
        cost, gift = explained(**kw)
        self.assertIsNotNone(cost)
        self.assertEqual(gift, ("DevilsAdvocate",))

    def test_a_second_body_in_the_night(self):
        kw = dict(deaths={0: ("N2",), 1: ("N2",)})
        cost, gift = explained(**kw)
        self.assertIsNotNone(cost)
        self.assertEqual(gift, ("Assassin",))
        self.assertIsNone(explained(PLAIN, **kw)[0])

    def test_madness_without_a_cerenovus(self):
        kw = dict(executions={2: 2}, deaths={2: ("D2",)},
                  madness_executions={2: 2})
        cost, gift = explained(**kw)
        self.assertIsNotNone(cost)
        self.assertEqual(gift, ("Cerenovus",))
        self.assertIsNone(explained(PLAIN, **kw)[0])

    def test_a_row_rules_the_others_out(self):
        kw = dict(deaths={0: ("D2",)}, witch_deaths={2: 0})
        row = I.AlchemistHas(1, 4, role="Poisoner")
        self.assertIsNone(explained(rows=[row], **kw)[0])


class APhilosopherThatTookIt(SolverTest):
    """Patrick, 04.11.2026: it has a Minion ability of its own, maybe
    another than the one the Alchemist it drunk was shown."""

    ROLES = R[:3] + ["Philosopher"] + R[4:]
    TOOK = I.PhilosopherChoice(1, 3, role="Alchemist")

    def test_it_is_offered_one_from_its_night(self):
        st = state([self.TOOK], claims=C[:3] + ["Philosopher"] + C[4:])
        self.assertIn((3, "N1"), S.alchemist_seats(world(self.ROLES), st))
        late = I.PhilosopherChoice(2, 3, role="Alchemist")
        st = state([late], claims=C[:3] + ["Philosopher"] + C[4:])
        self.assertIn((3, "N2"), S.alchemist_seats(world(self.ROLES), st))
        marks = [way[0] for way, _c in S.alchemist_offers(
            world(self.ROLES), st, 3, "N2")]
        self.assertTrue(all(m.phase == "N2" for m in marks))

    def test_its_curse_explains_a_death(self):
        kw = dict(deaths={0: ("D2",)}, witch_deaths={2: 0})
        # The dealt Alchemist shown the Poisoner: only the Philosopher's
        # own can be the Witch's.
        rows = [self.TOOK, I.AlchemistHas(1, 4, role="Poisoner")]
        claims = C[:3] + ["Philosopher"] + C[4:]
        cost, changes = S.best_story(world(self.ROLES),
                                     state(rows, claims=claims, **kw))
        self.assertIsNotNone(cost)
        self.assertIn((3, "Witch"), {(c.seat, c.gift) for c in changes
                                     if isinstance(c, AlchemistGift)})


class ItChangesTheSetup(SolverTest):
    """Group 2 (04.11.2026, claude/alchemist-gruppe-2-lesarten.md)."""

    # Eight seats: five Townsfolk and one Outsider dealt plainly.
    BARONS = ["Chef", "Empath", "Alchemist", "Saint", "Butler", "Recluse",
              "Spy", "Imp"]
    PLAIN = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Alchemist",
             "Butler", "Spy", "Imp"]

    def test_two_outsiders_more_are_its_baron(self):
        # Or its Xaan's "[X Outsiders]".
        self.assertEqual(worlds.alchemy_brackets(self.BARONS, SC),
                         (False, frozenset({"Baron", "Xaan"})))
        claims = dict(enumerate(self.BARONS))
        st = GameState(n_players=8, script=SC, claims=claims,
                       days_done={1})
        got = {way[0].gift for way, _c in S.alchemist_offers(
            world(self.BARONS), st, 2)}
        self.assertEqual(got, {"Baron", "Xaan"})
        # The bag is there to search.
        self.assertIn((frozenset({"Alchemist"}),
                       {"townsfolk": 3, "outsider": 3, "minion": 1,
                        "demon": 1}),
                      [(p, c) for p, c in worlds._bags(8, SC)])

    def test_a_plain_deal_has_no_baron_but_may_have_a_xaan(self):
        plain, keys = worlds.alchemy_brackets(self.PLAIN, SC)
        self.assertTrue(plain)
        self.assertIn("Xaan", keys)
        self.assertNotIn("Baron", keys)

    def test_its_godfather_kills_after_an_outsider_was_executed(self):
        # Its "[-1 or +1 Outsider]": two dealt, the Butler executed.
        roles = ["Chef", "Empath", "FortuneTeller", "Alchemist", "Butler",
                 "Recluse", "Spy", "Imp"]
        kw = dict(deaths={4: ("D1",), 0: ("N2",), 1: ("N2",)},
                  executions={1: 4})
        claims = dict(enumerate(roles))

        def best(rows):
            st = GameState(n_players=8, script=SC, claims=claims,
                           infos=list(rows), days_done={1, 2}, **kw)
            return S.best_story(world(roles), st)

        self.assertIn("Godfather", worlds.alchemy_brackets(roles, SC)[1])
        cost, changes = best([I.AlchemistHas(1, 3, role="Godfather")])
        self.assertIsNotNone(cost)
        self.assertIn("Godfather", [c.gift for c in changes
                                    if isinstance(c, AlchemistGift)])
        self.assertIsNone(best([I.AlchemistHas(1, 3, role="Witch")])[0])


class ByDayAndOnTheGallows(SolverTest):
    """Group 3 (05.11.2026, claude/alchemist-gruppe-3-lesarten.md)."""

    def gifts(self, rows=(), **kw):
        cost, changes = S.best_story(world(), state(rows, **kw))
        return cost, {c.gift for c in changes
                      if isinstance(c, AlchemistGift)}

    def test_everybody_knows_its_vizier(self):
        cost, gifts = self.gifts([I.VizierAnnounced(1, 4)])
        self.assertIsNotNone(cost)
        self.assertEqual(gifts, {"Vizier"})
        self.assertIsNone(self.gifts([I.VizierAnnounced(1, 4),
                                      I.AlchemistHas(1, 4,
                                                     role="Witch")])[0])

    def test_its_vizier_walks_away_from_the_gallows(self):
        cost, gifts = self.gifts([I.VizierAnnounced(1, 4)],
                                 executions={1: 4})
        self.assertIsNotNone(cost)

    def test_its_psychopath_kills_in_the_open(self):
        cost, gifts = self.gifts([I.PsychopathKill(2, 4, target=0,
                                                   died=True)],
                                 deaths={0: ("D2",)})
        self.assertIsNotNone(cost)
        self.assertEqual(gifts, {"Psychopath"})

    def test_its_goblin_wins_for_good(self):
        rows = [I.GoblinClaim(1, 4), I.AlchemistHas(1, 4, role="Goblin")]
        # Executed after saying so, and the game ended: good won.
        cost, gifts = self.gifts(rows, executions={1: 4},
                                 deaths={4: ("E1",)}, days=(),
                                 game_over=True)
        self.assertIsNotNone(cost)
        self.assertEqual(gifts, {"Goblin"})
        # The game went on: its ability cannot have been working.
        self.assertIsNone(self.gifts(rows, executions={1: 4},
                                     deaths={4: ("E1",)})[0])

    def test_its_boomdandy_explodes(self):
        cost, gifts = self.gifts(
            [I.BoomdandyExploded(1, 4, pointed=0)], executions={1: 4},
            deaths={4: ("E1",), 0: ("D1",), 1: ("D1",), 2: ("D1",),
                    3: ("D1",)}, days=(), game_over=True)
        self.assertIsNotNone(cost)
        self.assertEqual(gifts, {"Boomdandy"})


class ItBecomesTheDemon(SolverTest):
    """Group 3, D Weg 2 and H: with the Scarlet Woman's ability it becomes
    the Demon and stays good, and the game goes on."""

    def test_the_demon_executed_and_the_game_went_on(self):
        st = state(executions={1: 6}, deaths={6: ("E1",), 0: ("N2",)},
                   claims=C[:5] + ["Undertaker", "Chef"])
        cost, changes = S.best_story(world(), st)
        self.assertIsNotNone(cost)
        self.assertIn("ScarletWoman", {c.gift for c in changes
                                       if isinstance(c, AlchemistGift)})
        view = Timeline(world(), changes)
        self.assertEqual(view.demon_at("N2"), 4)
        self.assertFalse(view.evil_at(4, "N2"))
        # Shown something else, it cannot have.
        st = state([I.AlchemistHas(1, 4, role="Witch")], executions={1: 6},
                   deaths={6: ("E1",), 0: ("N2",)})
        self.assertIsNone(S.best_story(world(), st)[0])


class ItIsTheGoodTwin(SolverTest):
    """Group 3, I: its twin is an evil player; hanged, it hands evil the
    game."""

    def test_it_and_an_evil_player_know_each_other(self):
        st = state()
        view = Timeline(world(), (alchemist_gift_change(4, "EvilTwin"),))
        self.assertTrue(I.EvilTwinPair(1, 4, a=4, b=6).holds(view, st, None))
        self.assertFalse(I.EvilTwinPair(1, 4, a=4, b=0).holds(view, st, None))
        # Only on the night it has it from.
        self.assertFalse(I.EvilTwinPair(2, 4, a=4, b=6).holds(view, st, None))

    def test_hanged_and_the_game_went_on(self):
        rows = [I.EvilTwinPair(1, 4, a=4, b=6),
                I.AlchemistHas(1, 4, role="EvilTwin")]
        self.assertIsNotNone(S.best_story(world(), state(rows))[0])
        self.assertIsNone(S.best_story(world(), state(
            rows, executions={1: 4}, deaths={4: ("E1",)}))[0])


class ItTurnsSomebodyEvil(SolverTest):
    """Group 3, E Weg 1: with the Mezepheles's ability a good player turns
    evil; the Alchemist stays good."""

    def test_a_wrong_reading_from_a_player_it_turned(self):
        # The Empath's third-night reading is wrong, and nothing could
        # have poisoned it: turned evil, it may lie.
        def cost(key):
            rows = [I.AlchemistHas(1, 4, role=key), I.Empath(3, 1, count=2)]
            return S.best_story(world(), state(rows, days=(1, 2, 3)))[0]
        self.assertIsNotNone(cost("Mezepheles"))
        self.assertIsNone(cost("Witch"))


class ItRemakesSomebody(SolverTest):
    """Group 3: with the Pit-Hag's ability it makes a player a character not
    in play, and says so."""

    def test_the_chef_it_made_a_dreamer(self):
        rows = [I.AlchemistHas(1, 4, role="PitHag"),
                I.PitHagChoice(2, 4, target=0, role="Dreamer")]
        cost, changes = S.best_story(world(), state(rows))
        self.assertIsNotNone(cost)
        view = Timeline(world(), changes)
        self.assertEqual(view.role_at(0, "D2"), "Dreamer")
        self.assertFalse(view.evil_at(0, "D2"))


class BothSave(SolverTest):

    def test_a_devils_advocate_and_an_alchemist_with_its_ability(self):
        roles = R[:5] + ["DevilsAdvocate"] + R[6:]
        # Two walk away from the gallows on two days running: the dealt one
        # cannot keep the same player twice, but two players are two.
        kw = dict(executions={1: 0, 2: 1})
        cost, changes = S.best_story(world(roles), state(**kw))
        self.assertIsNotNone(cost)


class ItWakes(SolverTest):

    def woke(self, gift, night=2):
        view = Timeline(world(), (alchemist_gift_change(4, gift),))
        return waking.woke(view, state(), 4, night)

    def test_as_the_minion_would(self):
        self.assertTrue(self.woke("Poisoner"))
        self.assertTrue(self.woke("Poisoner", night=1))
        self.assertTrue(self.woke("Witch"))
        # The Devil's Advocate and the Assassin wake too; nothing the town
        # sees and nothing at all wake nobody.
        self.assertFalse(self.woke("*"))

    def test_an_unseen_one_may_have_woken(self):
        view = Timeline(world(), (alchemist_gift_change(4, "*"),))
        self.assertTrue(waking.uncertain(view, state(), 4, 2))
        view = Timeline(world(), (alchemist_gift_change(4, "Poisoner"),))
        self.assertFalse(waking.uncertain(view, state(), 4, 2))

    def test_without_a_gift_it_sleeps(self):
        self.assertFalse(waking.woke(Timeline(world(), ()), state(), 4, 2))


class APoisonedReading(SolverTest):

    def test_an_empath_wrong_without_a_poisoner(self):
        # The Empath beside the Alchemist and the Chef sees two evil:
        # wrong in every world here unless somebody poisoned it.
        row = I.Empath(2, 1, count=2)
        cost, gift = explained(rows=[row])
        self.assertIsNotNone(cost)
        # Poisoned — or, with a Mezepheles's ability, turned evil that
        # night before it read (group 3).
        self.assertIn(gift, (("Poisoner",), ("Mezepheles",)))
        self.assertIsNone(explained(PLAIN, rows=[row])[0])
        self.assertIsNotNone(explained(rows=[
            row, I.AlchemistHas(1, 4, role="Poisoner")])[0])


# Group 4 (05.11.2026, claude/alchemist-gruppe-4-lesarten.md): the jinxes.
IDS4 = IDS + ["widow", "wraith", "marionette", "mastermind", "organgrinder",
              "boffin", "soldier"]
SC4 = scripts.from_ids("Alchemist 4", IDS4)
# The Organ Grinder where the Spy sits.
OG = R[:5] + ["OrganGrinder", "Imp"]


def state4(rows=(), claims=C, days=(1, 2), **kw):
    return GameState(n_players=len(claims), script=SC4,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


class TheJinxes(SolverTest):
    """Group 4: J the Summoner later, K the Boffin as in the wiki, L the
    Demon attacks the one guessed."""

    def allowed(self, roles=R):
        return {k for k in ("Spy", "Widow", "Wraith", "Marionette",
                            "Mastermind", "OrganGrinder", "Boffin",
                            "Summoner", "Poisoner")
                if S._alchemy_jinx_allows(world(roles), k, "N1")}

    def test_beside_the_real_one_or_none(self):
        # The Spy is dealt: its own, none of the others that need theirs;
        # no Mastermind or Boffin dealt, so theirs; never the Summoner's.
        self.assertEqual(self.allowed(), {"Spy", "Mastermind", "Boffin",
                                          "Poisoner"})
        self.assertEqual(self.allowed(R[:5] + ["Mastermind", "Imp"]),
                         {"Boffin", "Poisoner"})
        self.assertEqual(self.allowed(OG), {"OrganGrinder", "Mastermind",
                                            "Boffin", "Poisoner"})

    def gifts(self, roles=R, rows=(), **kw):
        cost, changes = S.best_story(world(roles), state4(rows, **kw))
        return cost, {c.gift for c in changes
                      if isinstance(c, AlchemistGift)}

    SPY = I.AlchemistHas(1, 4, role="Spy")

    def test_a_right_guess_makes_the_demon_choose_them(self):
        rows = [self.SPY, I.AlchemistGuess(1, 4, target=5)]
        hanged = dict(executions={1: 0}, deaths={0: ("E1",)})
        # The Spy guessed, and the night was quiet: nothing kept it alive.
        self.assertIsNone(self.gifts(rows=rows, quiet_nights={2},
                                     **hanged)[0])
        # It died that night: as it must.
        cost, gifts = self.gifts(rows=rows, executions={1: 0},
                                 deaths={0: ("E1",), 5: ("N2",)})
        self.assertIsNotNone(cost)
        self.assertEqual(gifts, {"Spy"})
        # Somebody else died: the Demon did not choose the Spy.
        self.assertIsNone(self.gifts(rows=rows, executions={1: 0},
                                     deaths={0: ("E1",), 1: ("N2",)})[0])
        # A wrong guess changes nothing: a Demon aims at a corpse.
        self.assertIsNotNone(self.gifts(rows=[
            self.SPY, I.AlchemistGuess(1, 4, target=1)], quiet_nights={2},
            **hanged)[0])
        # Without the row it holds something else.
        cost, gifts = self.gifts(rows=rows[1:], quiet_nights={2}, **hanged)
        self.assertIsNotNone(cost)
        self.assertNotIn("Spy", gifts)

    def test_no_guess_without_an_execution(self):
        rows = [self.SPY, I.AlchemistGuess(1, 4, target=5)]
        self.assertIsNotNone(self.gifts(rows=rows, deaths={0: ("N2",)})[0])

    def test_its_organ_grinder_closes_the_eyes(self):
        rows = [I.BlindVote(2, 4)]
        hanged = dict(executions={1: 5}, deaths={5: ("E1",)})
        cost, gifts = self.gifts(OG, rows, **hanged)
        self.assertIsNotNone(cost)
        self.assertEqual(gifts, {"OrganGrinder"})
        self.assertIsNone(self.gifts(OG, rows + [I.AlchemistHas(
            1, 4, role="Witch")], **hanged)[0])

    def test_its_boffin_gives_the_demon_one(self):
        view = Timeline(world(), (alchemist_gift_change(4, "Boffin"),))
        st = state4()
        self.assertEqual(I.boffin_seat(view, st, "N2"), 4)
        stories = S.a_boffin_gives_the_demon(view, st)
        self.assertTrue(any(isinstance(c, worlds.BoffinGift)
                            and not isinstance(c, AlchemistGift)
                            and c.seat == 6
                            for changes, _ in stories for c in changes))
        plain = Timeline(world(), (alchemist_gift_change(4, "Poisoner"),))
        self.assertEqual(S.a_boffin_gives_the_demon(plain, st),
                         [((), 1.0)])

    def test_it_does_not_wake_for_what_it_has_not(self):
        for gift, woke in (("Spy", False), ("Widow", False),
                           ("Boffin", False), ("OrganGrinder", True)):
            view = Timeline(world(), (alchemist_gift_change(4, gift),))
            self.assertEqual(waking.woke(view, state4(), 4, 2), woke, gift)
        # And has none of their abilities.
        view = Timeline(world(), (alchemist_gift_change(4, "Spy"),))
        self.assertFalse(I.has_plague_ability(view, state4(), 4, "Spy",
                                              "N2"))


def _payloads():
    def pay(events, rows=(), claims=C, days=(1, 2), ids=IDS):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players,
                "infos": list(rows),
                "script": {"name": "Alchemist", "characters": ids},
                "days_done": list(days)}

    has = {"type": "AlchemistHas", "night": 1, "player": 4}
    return [
        pay({}),
        pay({0: ["N2"], 1: ["N2"]}),
        pay({0: ["W2"]}),
        pay({0: ["S1"]}),
        pay({2: ["M2"]}),
        pay({}, [{"type": "Empath", "night": 2, "player": 1, "count": 2}]),
        pay({0: ["W2"]}, [dict(has, role="Witch")]),
        pay({}, [dict(has, role="Poisoner"),
                 {"type": "Empath", "night": 2, "player": 1, "count": 2}]),
        # Group 2: its Baron moved the bag, its Godfather kills.
        pay({}, claims=["Chef", "Empath", "Alchemist", "Saint", "Butler",
                        "Recluse", "Chef", "Empath"]),
        pay({4: ["X1"], 0: ["N2"], 1: ["N2"]},
            [dict(has, player=3, role="Godfather")],
            claims=["Chef", "Empath", "FortuneTeller", "Alchemist",
                    "Butler", "Recluse", "Chef", "Empath"]),
        # Group 3: its Vizier, its Psychopath.
        pay({4: ["S1"]}, [{"type": "VizierAnnounced", "night": 1,
                           "player": 4}]),
        pay({0: ["D2"]}, [{"type": "PsychopathKill", "night": 2,
                           "player": 4, "target": 0, "died": True}]),
        # Its Scarlet Woman's: the Demon executed, the game went on.
        pay({6: ["X1"], 0: ["N2"]}),
        # Its Evil Twin's: an evil twin.
        pay({}, [{"type": "EvilTwinPair", "night": 1, "player": 4, "a": 4,
                  "b": 6}]),
        # Its Mezepheles's: a turned Empath lies.
        pay({}, [dict(has, role="Mezepheles"),
                 {"type": "Empath", "night": 3, "player": 1, "count": 2}],
            days=(1, 2, 3)),
        # A Philosopher that took the Alchemist (Patrick, 04.11.2026).
        pay({0: ["W2"]}, [{"type": "PhilosopherChoice", "night": 1,
                           "player": 3, "role": "Alchemist"},
                          dict(has, role="Poisoner")],
            claims=C[:3] + ["Philosopher"] + C[4:]),
        # Group 4: the jinxes, a guess, the Spy guessed dying, an Organ
        # Grinder's closed eyes.
        pay({}, ids=IDS4),
        pay({0: ["X1"]}, [{"type": "AlchemistGuess", "night": 1,
                           "player": 4, "target": 5}], ids=IDS4),
        pay({0: ["X1"], 5: ["N2"]},
            [{"type": "AlchemistGuess", "night": 1, "player": 4,
              "target": 5}, dict(has, role="Spy")], ids=IDS4),
        pay({5: ["X1"]}, [{"type": "BlindVote", "night": 2, "player": 4}],
            ids=IDS4),
        dict(pay({0: ["X1"]}, [{"type": "AlchemistGuess", "night": 1,
                                "player": 4, "target": 5},
                               dict(has, role="Spy")], ids=IDS4),
             quiet_nights=[2]),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_alchemist_boards(self):
        import json
        import pathlib
        import subprocess
        import app
        root = pathlib.Path(__file__).resolve().parent.parent
        cases = _payloads()
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); if (r.error) return r.error;"
                  " return {valid: r.valid, un: r.unreckoned || {},"
                  "  rows: r.rows.map(x => [x.evil_pct, x.demon_pct])};"
                  "})));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=root,
                             capture_output=True, text=True, timeout=900)
        self.assertEqual(got.returncode, 0, got.stderr)
        js = json.loads(got.stdout)
        for i, (p, j) in enumerate(zip(cases, js)):
            r = app.run_solve(p)
            self.assertNotIn("error", r, i)
            self.assertNotIsInstance(j, str, (i, j))
            self.assertGreater(r["valid"], 0, i)
            self.assertEqual(j["valid"], r["valid"], i)
            self.assertEqual(j["un"], r.get("unreckoned") or {}, i)
            for (je, jd), row in zip(j["rows"], r["rows"]):
                self.assertAlmostEqual(je, row["evil_pct"], places=6, msg=i)
                self.assertAlmostEqual(jd, row["demon_pct"], places=6,
                                       msg=i)


if __name__ == "__main__":
    unittest.main()
