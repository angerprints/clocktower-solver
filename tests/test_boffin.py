"""The Boffin (26.10.2026, claude/laborratte-lesarten.md), stage 1.

"The Demon (even if drunk or poisoned) has a not-in-play good character's
ability. You both know which." Patrick's answers:

  * A Weg 3: without a row every ability is a story; those that change
    nothing the town sees are one story together, weighed by how many.
  * B Weg 1: good characters of the script nobody holds; not the Drunk,
    the Heretic, the Ogre or the Politician; a Village Idiot only with a
    spare token.
  * C Weg 1: a new Demon gets a new ability.
  * D Weg 2: a second living Demon — the Storyteller decides: both ways
    are stories.
  * E Weg 1: setup brackets only where the Demon has that ability (stage
    2).
  * F Weg 1: the Boffin wakes on night one; the Demon not then, and later
    whenever its ability wakes it.
  * G Weg 1: the Demon's readings weighed like the character's own.
  * H Weg 2: the Philosopher too (stage 2).
  * I Weg 1: a Boffin made in the middle of the game gives from then on.
  * J Weg 1: the simulator gives one at random; the row in about half.

Stage 1 reckons the abilities that change who dies, who is drunk and how
the game ends (`solver.BOFFIN_SEEN`). Its sobriety is the Boffin's.
"""

import json
import random
import subprocess
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc import waking                           # noqa: E402
from botc.catalogue import CHARACTERS, IMPAIRS, slot_of  # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import (BOFFIN_UNSEEN, BoffinGift, Change, Summoned,  # noqa
                         Timeline, World, boffin_gift_change)

import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

IDS = ["chef", "empath", "fortuneteller", "monk", "washerwoman",
       "investigator", "soldier", "undertaker", "fool", "virgin", "saint",
       "recluse", "sailor", "tealady", "innkeeper", "goon", "drunk",
       "boffin", "baron", "scarletwoman", "imp", "poisoner"]
SC = scripts.from_ids("Laborratte", IDS)

#    0       1         2                3              4        5         6
R = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Saint", "Boffin",
     "Imp"]
C = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Saint",
     "Investigator", "Undertaker"]


def state(rows=(), claims=C, script=SC, days=(1, 2), **kw):
    return GameState(n_players=len(claims), script=script,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def gave(night, role, seat=5):
    return I.BoffinGave(night, seat, role=role)


def gifts(roles=R, rows=(), **kw):
    """Every story as {seat: gift}, with its cost."""
    out = []
    for got, cost in S.possible_timelines(world(roles), state(rows, **kw)):
        out.append(({c.seat: c.gift for c in got
                     if isinstance(c, BoffinGift)}, round(cost, 4)))
    return out


class TheCharacter(SolverTest):

    def test_a_minion_woken_on_the_first_night(self):
        c = CHARACTERS["Boffin"]
        self.assertEqual(c.team, "minion")
        self.assertTrue(slot_of("Boffin", 1))
        self.assertFalse(slot_of("Boffin", 2))
        # Before the Philosopher, so a Philosopher sees what it gave.
        self.assertLess(slot_of("Boffin", 1), slot_of("Philosopher", 1))
        self.assertIn("Boffin", IMPAIRS)

    def test_what_a_row_may_name(self):
        st = state()
        self.assertEqual(gave(1, "Fool").given(st), "Fool")
        self.assertIsNone(gave(1, "Drunk").given(st))     # their jinx
        self.assertIsNone(gave(1, "Imp").given(st))       # not good
        self.assertIsNone(gave(1, "Ravenkeeper").given(st))  # off the script


class TheStories(SolverTest):

    def test_nothing_seen_first_then_each_seen_one(self):
        got = gifts()
        # Investigator, Undertaker and Recluse are "nothing the town sees";
        # the Saint is in play, the Drunk forbidden.
        self.assertEqual(got[0], ({6: BOFFIN_UNSEEN}, 1.0))
        seen = {g[6] for g, _c in got[1:]}
        self.assertEqual(seen, {"Monk", "Soldier", "Fool", "Virgin",
                                "Sailor", "TeaLady", "Innkeeper", "Goon"})
        self.assertTrue(all(c == round(1 / 3, 4) for _g, c in got[1:]))
        self.assertNotIn("Saint", seen)

    def test_a_row_names_the_one(self):
        self.assertEqual(gifts(rows=[gave(1, "Fool")]), [({6: "Fool"}, 1.0)])
        self.assertEqual(gifts(rows=[gave(1, "Investigator")]),
                         [({6: BOFFIN_UNSEEN}, 1.0)])

    def test_no_boffin_no_story(self):
        roles = R[:5] + ["Baron", "Imp"]
        self.assertEqual(gifts(roles), [({}, 1.0)])

    def test_a_new_demon_gets_its_own(self):
        # The Imp kills itself on night two and the Scarlet Woman... here
        # the Boffin catches the star: a new Demon, a new ability (C).
        st = state(deaths={6: "N2"})
        got = S.possible_timelines(world(), st)
        moments = {(c.seat, c.phase) for changes, _ in got for c in changes
                   if isinstance(c, BoffinGift)}
        self.assertIn((6, "N1"), moments)

    def test_a_first_night_row_is_about_the_demon_dealt(self):
        # Seed 683 of the gate: a row of the first night does not name
        # what a Demon made later that night was given.
        self.assertIsNone(S._boffin_named(state([gave(1, "Fool")]), 1,
                                          False))
        self.assertEqual(S._boffin_named(state([gave(1, "Fool")]), 1,
                                         True), "Fool")


class WhatItDoes(SolverTest):

    def test_a_fool_demon_walks_from_the_gallows(self):
        st = state(executions={1: 6})
        self.assertIsNotNone(S.explanation_cost(world(), st))
        self.assertIsNone(S.explanation_cost(
            world(R[:5] + ["Baron", "Imp"]), st))

    def test_a_dead_boffin_gives_nothing(self):
        st = state(executions={1: 5, 2: 6}, deaths={5: "D1"},
                   days=(1, 2, 3))
        self.assertIsNone(S.explanation_cost(world(), st))

    def test_the_row_decides(self):
        self.assertIsNone(S.explanation_cost(
            world(), state([gave(1, "Monk")], executions={1: 6})))
        self.assertIsNotNone(S.explanation_cost(
            world(), state([gave(1, "Fool")], executions={1: 6})))

    def test_its_sobriety_is_the_boffins(self):
        view = Timeline(world(), (boffin_gift_change("N1", 6, "Fool", -1),))
        st = state()
        self.assertEqual(I.sober_seat(view, st, 6, "Fool", "N2"), 5)
        self.assertEqual(I.sober_seat(view, st, 6, "Imp", "N2"), 6)
        self.assertEqual(I.boffin_gift(view, st, 6, "N2"), "Fool")
        # Nothing the town sees answers nothing.
        view = Timeline(world(), (boffin_gift_change("N1", 6, BOFFIN_UNSEEN,
                                                     -1),))
        self.assertIsNone(I.boffin_gift(view, st, 6, "N2"))

    def test_a_goon_demon_stays_evil(self):
        view = Timeline(world(), (boffin_gift_change("N1", 6, "Goon", -1),))
        self.assertFalse(I.side_open(view, state(), 6, "N2"))

    def test_it_wakes_for_its_ability_after_the_first_night(self):
        view = Timeline(world(), (boffin_gift_change("N1", 6, "Monk", -1),))
        st = state(days=(1, 2, 3))
        self.assertTrue(waking.woke(view, st, 6, 2))
        # The Boffin itself on the first night (F Weg 1).
        self.assertTrue(waking.woke(view, st, 5, 1))
        self.assertFalse(waking.woke(view, st, 5, 2))


class TwoDemons(SolverTest):

    def test_the_storyteller_decides(self):
        # A Summoner's Demon beside the Imp: the first keeps its ability,
        # or the second gets one and the first's ends (D Weg 2).
        roles = R
        changes = (Summoned("N3", 1, "Imp", "evil", 190),)
        view = Timeline(world(roles), changes)
        st = state(days=(1, 2, 3))
        moments = S._boffin_moments(view, st, False)
        self.assertEqual(moments, [("N3", 190, 1, 6)])
        got = S._boffin_stories(view, st, False)
        self.assertEqual(got[0], ((), 1.0))           # the first keeps it
        ends = [c for way, _c in got[1:] for c in way
                if isinstance(c, BoffinGift) and c.seat == 6]
        self.assertTrue(ends and all(c.gift == "" for c in ends))


def _play(seed, must):
    import claims as Cl
    import play_games
    import simulate
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    n = [7, 8, 9, 10, 11][seed % 5]
    deal, heard = simulate.play(n, rng, nights=4, script=script)
    claims, wakes, _ = Cl.claims_for(deal, rng, script=script)
    st = GameState(n_players=n, script=script, claims=claims, wakes=wakes,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, heard, st


class TheSimulator(SolverTest):
    """Played games with a Boffin dealt: the true world is kept."""

    def test_games_with_a_boffin(self):
        given, rows, lost = 0, 0, []
        for seed in range(300):
            deal, heard, st = _play(seed, ("Boffin",))
            if getattr(deal, "boffin_gift", None) is None:
                continue
            given += 1
            rows += any(isinstance(r, I.BoffinGave) for r in heard)
            if S.hatter_unreckoned(deal.world(), st) is not None:
                continue
            if S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        self.assertGreater(given, 60)
        self.assertGreater(rows, 20)
        self.assertEqual(lost, [])

    def test_the_gossip_ends_with_the_boffin(self):
        # Seed 714 of the gate: the Boffin died to the Demon, so the
        # Demon's Gossip ability killed nobody after it.
        import nightwalk
        deal, heard, _st = _play(714, ("Boffin",))
        got = nightwalk.walk(deal, 3, nightwalk.hidden_from(deal, 3, heard))
        self.assertEqual(got.died, deal.died_on("N3"))


def _payloads():
    def pay(events, rows=(), claims=C, ids=IDS, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players,
                "infos": list(rows),
                "script": {"name": "Laborratte", "characters": ids},
                "days_done": list(days)}

    def b(night, role):
        return {"type": "BoffinGave", "night": night, "player": 5,
                "role": role}

    return [
        pay({}),
        pay({6: ["S1"]}),
        pay({1: ["N2"], 6: ["S1"]}),
        pay({6: ["S1"]}, [b(1, "Fool")]),
        pay({1: ["N2"], 2: ["X2"]}, days=(1, 2, 3)),
        pay({1: ["N2"]}, [b(1, "Sailor")]),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_a_boffin(self):
        import app
        cases = _payloads()
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); if (r.error) return r.error;"
                  " return {valid: r.valid, un: r.unreckoned || {},"
                  "  rows: r.rows.map(x => [x.evil_pct, x.demon_pct])};"
                  "})));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=900)
        self.assertEqual(got.returncode, 0, got.stderr)
        js = json.loads(got.stdout)
        for p, j in zip(cases, js):
            r = app.run_solve(p)
            self.assertNotIn("error", r)
            self.assertEqual(j["valid"], r["valid"])
            self.assertEqual(j["un"], r.get("unreckoned") or {})
            for (je, jd), row in zip(j["rows"], r["rows"]):
                self.assertAlmostEqual(je, row["evil_pct"], places=6)
                self.assertAlmostEqual(jd, row["demon_pct"], places=6)


if __name__ == "__main__":
    unittest.main()
