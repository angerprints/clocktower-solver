"""The Boffin, stage 2 (27.10.2026, claude/laborratte-stufe-2-lesarten.md).

Patrick's answers of 26.10.2026 (E, G, H) and 27.10.2026 (K to R):

  * E Weg 1: a gift's setup bracket holds exactly in the stories where the
    Demon has it.
  * G Weg 1 and K Weg 2: a reading of a good character X on a seat that is
    the Demon in a world makes X its gift there, and is weighed as X's.
  * H Weg 2 and M Weg 2: the Professor, the Huntsman and the Philosopher;
    every choice of a Philosopher-Demon is a story.
  * L Weg 1: the Barber and the Hatter only with the Boffin's row.
  * N Weg 1: the Engineer, the Nightwatchman, the Pixie, the Professor and
    the Huntsman are stories of their own.
  * O, Q Weg 1 and P Weg 2: the rest stays "nothing the town sees"; the
    Boffin may give the Atheist.
  * R Weg 1: the simulator plays stage 2.
"""

import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import (BOFFIN_UNSEEN, BoffinGift, Timeline, World,  # noqa
                         boffin_gift_change)

IDS = ["chef", "empath", "fortuneteller", "washerwoman", "investigator",
       "professor",
       "huntsman", "engineer", "nightwatchman", "pixie", "philosopher",
       "balloonist", "choirboy", "king", "bountyhunter", "villageidiot",
       "saint", "damsel", "recluse", "barber", "hatter", "atheist",
       "boffin", "baron", "scarletwoman", "imp", "poisoner"]
SC = scripts.from_ids("Laborratte 2", IDS)

#    0       1         2                3              4        5         6
R = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Investigator",
     "Boffin", "Imp"]
C = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Investigator",
     "Professor", "King"]


def state(rows=(), claims=C, script=SC, days=(1, 2), **kw):
    return GameState(n_players=len(claims), script=script,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def seen_gifts(roles=R, rows=(), **kw):
    out = set()
    for got, _cost in S.possible_timelines(world(roles), state(rows, **kw)):
        out |= {c.gift for c in got if isinstance(c, BoffinGift)}
    return out


class TheNewStories(SolverTest):

    def test_stage_two_abilities_are_stories(self):
        got = seen_gifts()
        for key in ("Professor", "Engineer", "Nightwatchman", "Pixie",
                    "BountyHunter"):
            self.assertIn(key, got)
        # The Huntsman brings the Damsel (E Weg 1): only beside her.
        self.assertNotIn("Huntsman", got)
        self.assertIn("Huntsman", seen_gifts(R[:4] + ["Damsel"] + R[5:]))
        # Restrictions and knowledge stay "nothing the town sees" (O, Q).
        for key in ("Chef", "Recluse", "Damsel", "Atheist", "King"):
            self.assertNotIn(key, got)

    def test_the_atheist_may_be_given(self):
        # P Weg 2: given, nothing the town sees.
        st = state()
        self.assertEqual(I.BoffinGave(1, 5, role="Atheist").given(st),
                         "Atheist")


class TheBrackets(SolverTest):
    """E Weg 1: a gift's bracket holds exactly where the Demon has it."""

    def test_an_outsider_only_the_balloonist_explains(self):
        # Seven players deal no Outsider; the Saint is one. Only a
        # Balloonist's "[+1 Outsider]" holds that, so the Demon has it.
        roles = R[:4] + ["Saint"] + R[5:]
        self.assertEqual(seen_gifts(roles), {"Balloonist"})
        # A row naming something else cannot be.
        st = state([I.BoffinGave(1, 5, role="Professor")])
        self.assertEqual(S.possible_timelines(world(roles), st), [])

    def test_the_choirboy_needs_the_king(self):
        st = state()
        self.assertNotIn("Choirboy", S.boffin_may_give(world(), st, "N1",
                                                       setup=True))
        roles = R[:4] + ["King"] + R[5:]
        self.assertIn("Choirboy", S.boffin_may_give(world(roles), st, "N1",
                                                    setup=True))
        # Later, for a new Demon, no bracket.
        self.assertIn("Choirboy", S.boffin_may_give(world(), st, "N3"))

    def test_a_bounty_hunter_gift_turns_a_townsfolk(self):
        turned = set()
        for changes, _w in S.possible_timelines(world(), state()):
            gift = next((c.gift for c in changes
                         if isinstance(c, BoffinGift)), None)
            evil = {c.seat for c in changes
                    if type(c).__name__ == "TurnedEvil"}
            self.assertEqual(bool(evil), gift == "BountyHunter")
            turned |= evil
        self.assertEqual(turned, {0, 1, 2, 3, 4})


class WhatTheyDo(SolverTest):

    def test_a_professor_demon_raises_a_townsfolk(self):
        # The Chef died on night two and stood up on night three: nobody
        # holds the Professor, so only the Demon's gift explains it.
        st = state(deaths={0: ("N2",)}, resurrections={0: ("N3",)},
                   days=(1, 2, 3))
        self.assertIsNotNone(S.explanation_cost(world(), st))
        self.assertIsNone(S.explanation_cost(
            world(R[:5] + ["Baron", "Imp"]), st))

    def test_a_nightwatchman_demon_shows_itself(self):
        # "I was shown that 6 is the Nightwatchman": nobody holds it, so
        # the row is made up (0.4) — or the Demon has it, which needs
        # nothing else. That story costs only what the gift costs.
        rows = [I.NightwatchmanSeen(2, 1, shown=6)]
        viable = []
        S.best_story(world(), state(rows), viable=viable)
        by_gift = {}
        for cost, changes in viable:
            for c in changes:
                if isinstance(c, BoffinGift):
                    by_gift[c.gift] = cost
        shown = by_gift.pop("Nightwatchman")
        self.assertAlmostEqual(by_gift[BOFFIN_UNSEEN], 0.4)   # made up
        self.assertTrue(all(shown > c for g, c in by_gift.items()
                            if g != BOFFIN_UNSEEN))

    def test_an_engineer_demon_rebuilds_its_minions(self):
        rows = [I.EngineerChoice(2, 6, roles=("Poisoner",))]
        st = state(rows, days=(1, 2, 3))
        built = [changes for changes, _w in S.possible_timelines(world(), st)
                 if any(type(c).__name__ == "Engineered" for c in changes)]
        self.assertTrue(built)
        # Given the Engineer's ability, or the Philosopher's that took it.
        self.assertTrue(all(any(isinstance(c, BoffinGift)
                                and "Engineer" in I.boffin_abilities(
                                    c.gift, "N2") for c in changes)
                            for changes in built))


# The Empath's seat holds the Professor here, so the Boffin may give the
# Empath.
R_NO_EMPATH = ["Chef", "Professor", "FortuneTeller", "Washerwoman",
               "Investigator", "Boffin", "Imp"]


class APhilosopherDemon(SolverTest):
    """H and M Weg 2: every choice of a Demon with the Philosopher's
    ability is a story; one in play is drunk."""

    def choices(self, roles=R, rows=()):
        out = set()
        for got in seen_gifts(roles, rows):
            if got.startswith("Philosopher>"):
                out.add(got.split(">")[1])
        return out

    def test_every_choice(self):
        got = self.choices()
        self.assertIn(BOFFIN_UNSEEN, got)
        # In play: drunk, so seen. Not in play and seen: acts.
        for key in ("Chef", "Empath", "Professor", "Engineer"):
            self.assertIn(key, got)
        # Not in play and nothing the town sees: in "*".
        self.assertNotIn("Recluse", got)

    def test_its_row_decides(self):
        rows = [I.PhilosopherChoice(2, 6, role="Empath")]
        self.assertEqual(seen_gifts(rows=rows) & {
            g for g in seen_gifts(rows=rows) if g.startswith("Phil")},
            {"Philosopher>Empath>N2"})

    def test_it_drunks_whoever_holds_it(self):
        view = Timeline(world(), (boffin_gift_change(
            "N1", 6, I.boffin_philosophy("Empath", "N1"), -1),))
        got = S.a_boffin_philosopher_drunks_whoever_had_it(view, state(), 2)
        self.assertEqual([(g.seats, g.actor) for g in got],
                         [(frozenset({1}), 5)])
        self.assertTrue(I.took_it(view, state(), 6, "Empath", "N2"))
        self.assertTrue(I.took_it(view, state(), 6, "Philosopher", "N2"))


class ItsReadings(SolverTest):
    """K Weg 2: a reading of a good character on the Demon's seat makes that
    character a story of its own there, weighed as the character's."""

    def test_a_reading_makes_a_story(self):
        rows = [I.Empath(1, 6, count=1)]
        self.assertIn("Empath", seen_gifts(R_NO_EMPATH, rows))
        self.assertNotIn("Empath", seen_gifts(R_NO_EMPATH))

    def test_true_in_that_story_and_a_bluff_elsewhere(self):
        # Seat 6, claiming the Empath, neighbours the Boffin (evil) and
        # the Chef: one.
        claims = C[:6] + ["Empath"]
        for count, holds in ((1, True), (0, False)):
            viable = []
            S.best_story(world(R_NO_EMPATH),
                         state([I.Empath(1, 6, count=count)], claims=claims),
                         viable=viable)
            gifts = {c.gift for _cost, changes in viable for c in changes
                     if isinstance(c, BoffinGift)}
            self.assertEqual("Empath" in gifts, holds)
            self.assertIn(BOFFIN_UNSEEN, gifts)       # it may be a bluff

    def test_a_named_reading_ability_is_itself(self):
        rows = [I.BoffinGave(1, 5, role="Empath")]
        self.assertEqual(seen_gifts(R_NO_EMPATH, rows), {"Empath"})


class OnlyWithItsRow(SolverTest):
    """L Weg 1: the Barber and the Hatter only where the Boffin's row
    names them."""

    def test_not_without_a_row(self):
        self.assertNotIn("Barber", seen_gifts())
        self.assertNotIn("Hatter", seen_gifts())

    def test_with_a_row(self):
        rows = [I.BoffinGave(1, 5, role="Barber")]
        self.assertEqual(seen_gifts(rows=rows), {"Barber"})
        self.assertTrue(S._boffin_names(state(rows), "Barber"))
        self.assertEqual(S.barber_claimants(state(rows)), set(range(7)))


if __name__ == "__main__":
    unittest.main()
