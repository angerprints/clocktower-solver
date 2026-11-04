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
from botc import info as I, scripts, waking       # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import (AlchemistGift, Timeline, World,  # noqa: E402
                         alchemist_gift_change)

IDS = ["chef", "empath", "fortuneteller", "washerwoman", "investigator",
       "undertaker", "alchemist", "saint",
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
                                    "Fearmonger"})
        # Two the town cannot see (the Spy, the Baron): each seen one
        # costs one over two, the rest one.
        self.assertEqual(got["*"], 1.0)
        self.assertAlmostEqual(got["Witch"], 0.5)

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
        self.assertEqual(gift, ("Poisoner",))
        self.assertIsNone(explained(PLAIN, rows=[row])[0])


def _payloads():
    def pay(events, rows=(), claims=C, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players,
                "infos": list(rows),
                "script": {"name": "Alchemist", "characters": IDS},
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
