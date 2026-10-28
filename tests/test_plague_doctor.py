"""The Plague Doctor, stage 1 (28.10.2026, claude/pestdoktor-lesarten.md).

"If you die, the Storyteller gains a Minion ability." Patrick's answers of
28.10.2026:

  * A Weg 1: two stages. Stage 1 reckons what poisons, kills or changes
    an execution, and the five jinxed ones; stage 2 what changes
    characters or sides.
  * B Weg 3: each ability the town can see is a story of its own, the
    rest one story "nothing the town sees"; a row names it.
  * C Weg 1: any Minion of the script, one in play too.
  * D Weg 1: from its death on, the night it died too.
  * E Weg 1: the Spy's, the Scarlet Woman's, the Wraith's, the
    Fearmonger's and the Goblin's go to a living Minion, each a story.
  * G Weg 1: every death of a Plague Doctor gives one more.
  * H Weg 1: a Philosopher that took it gives one when it dies; the real
    one it drunk gives none.
  * I Weg 1: nobody wakes for the Storyteller; a Minion wakes for its
    second ability.
  * J Weg 1: the simulator plays it.
"""

import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import PlagueGift, Timeline, World  # noqa: E402

IDS = ["chef", "empath", "fortuneteller", "washerwoman", "investigator",
       "undertaker", "philosopher",
       "plaguedoctor", "saint", "butler",
       "poisoner", "godfather", "scarletwoman", "spy", "witch", "assassin",
       "devilsadvocate", "mastermind", "xaan", "goblin", "fearmonger",
       "baron", "imp"]
SC = scripts.from_ids("Pestdoktor", IDS)

#    0       1         2                3              4
R = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "PlagueDoctor",
     #  5          6
     "Poisoner", "Imp"]
C = ["Chef", "Empath", "FortuneTeller", "Washerwoman", "Investigator",
     "Undertaker", "Chef"]


def state(rows=(), claims=C, script=SC, days=(1, 2), **kw):
    return GameState(n_players=len(claims), script=script,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def gifts(roles=R, **kw):
    """{(seat, ability): cost} over every story."""
    out = {}
    for got, cost in S.possible_timelines(world(roles), state(**kw)):
        for c in got:
            if isinstance(c, PlagueGift):
                out[(c.seat, c.gift)] = cost
    return out


EXECUTED_D1 = dict(deaths={4: ("D1",)}, executions={1: 4})


class TheStories(SolverTest):

    def test_nothing_while_it_lives(self):
        self.assertEqual(gifts(), {})

    def test_each_seen_ability_is_a_story(self):
        got = gifts(**EXECUTED_D1)
        for key in ("Poisoner", "Godfather", "Witch", "Assassin",
                    "DevilsAdvocate", "Mastermind"):
            self.assertIn((None, key), got)
        # Their jinxes: the living Minion gains these (E Weg 1).
        for key in ("ScarletWoman", "Goblin", "Fearmonger"):
            self.assertIn((5, key), got)
            self.assertNotIn((None, key), got)
        # Nothing the town sees: the Spy, the Baron, a Xaan whose night
        # has passed (one Outsider dealt: night one).
        self.assertEqual(got[(None, "*")], 1.0)
        for key in ("Spy", "Baron", "Xaan"):
            self.assertNotIn((None, key), got)
            self.assertNotIn((5, key), got)
        # A random pick: each seen one costs one over the three unseen.
        self.assertAlmostEqual(got[(None, "Poisoner")], 1 / 3)

    def test_a_row_names_it(self):
        row = I.PlagueDoctorGave(1, 4, role="Witch")
        got = gifts(rows=[row], **EXECUTED_D1)
        self.assertEqual(set(got), {(None, "Witch")})
        # Not a Minion: no world fits.
        bad = I.PlagueDoctorGave(1, 4, role="Imp")
        self.assertIsNone(S.best_story(world(), state([bad],
                                                      **EXECUTED_D1))[0])

    def test_the_xaan_only_before_its_night(self):
        # Two Outsiders dealt: its night is the second, still to come.
        roles = R[:3] + ["Saint"] + R[4:]
        self.assertIn((None, "Xaan"), gifts(roles, **EXECUTED_D1))

    def test_every_death_gives_one_more(self):
        # G Weg 1: died, stood up, died again — two gifts in one story.
        stories = S.possible_timelines(world(), state(
            deaths={4: ("D1", "N3")}, resurrections={4: ("N2",)},
            days=(1, 2, 3)))
        most = max(sum(isinstance(c, PlagueGift) for c in got)
                   for got, _w in stories)
        self.assertEqual(most, 2)


class APhilosopherTookIt(SolverTest):
    """H Weg 1."""

    ROLES = ["Chef", "Empath", "FortuneTeller", "Philosopher",
             "PlagueDoctor", "Poisoner", "Imp"]
    TOOK = I.PhilosopherChoice(1, 3, role="PlagueDoctor")

    def test_the_real_one_it_drunk_gives_none(self):
        st = state([self.TOOK], deaths={4: ("D1",)}, executions={1: 4})
        self.assertEqual(S.plague_moments(world(self.ROLES), st), [])

    def test_its_own_death_gives_one(self):
        st = state([self.TOOK], deaths={3: ("D1",)}, executions={1: 3})
        self.assertEqual(S.plague_moments(world(self.ROLES), st),
                         [("D1", 3)])


class WhatTheyDo(SolverTest):

    def explained(self, roles=R, **kw):
        cost, changes = S.best_story(world(roles), state(**kw))
        return cost, [c for c in changes if isinstance(c, PlagueGift)]

    def test_a_godfather_kills_after_an_outsider_was_executed(self):
        # Two bodies on night two: the Imp's, and the Storyteller's
        # Godfather's — the Plague Doctor, an Outsider, went up today.
        kw = dict(deaths={4: ("D1",), 0: ("N2",), 1: ("N2",)},
                  executions={1: 4})
        cost, marks = self.explained(**kw)
        self.assertIsNotNone(cost)
        self.assertIn(marks[0].gift, ("Godfather", "Assassin"))
        # The same night with the Plague Doctor alive is no world.
        roles = R[:4] + ["Saint"] + R[5:]
        self.assertIsNone(self.explained(roles, **kw)[0])

    def test_a_witch_curse_without_a_witch(self):
        kw = dict(deaths={4: ("D1",), 0: ("D2",)}, executions={1: 4},
                  witch_deaths={2: 0})
        cost, marks = self.explained(**kw)
        self.assertIsNotNone(cost)
        self.assertEqual(marks[0].gift, "Witch")

    def test_a_devils_advocate_saves_from_the_gallows(self):
        kw = dict(deaths={4: ("D1",)}, executions={1: 4, 2: 0})
        cost, marks = self.explained(**kw)
        self.assertIsNotNone(cost)
        self.assertEqual(marks[0].gift, "DevilsAdvocate")

    def test_a_minion_given_the_scarlet_woman_takes_over(self):
        # The Imp executed on day two with six alive, and the game went
        # on: only a Minion given her ability (E Weg 1) explains it.
        kw = dict(deaths={4: ("D1",), 6: ("D2",)},
                  executions={1: 4, 2: 6}, days=(1, 2, 3))
        cost, marks = self.explained(**kw)
        self.assertIsNotNone(cost)
        self.assertEqual((marks[0].seat, marks[0].gift),
                         (5, "ScarletWoman"))


class NotReckonedYet(SolverTest):

    def test_a_stage_two_ability_on_the_script(self):
        sc = scripts.from_ids("Pestdoktor 2", IDS + ["pithag"])
        view = Timeline(world(), (S.plague_gift_change("D1", None, "*"),))
        st = state(script=sc, **EXECUTED_D1)
        self.assertEqual(S.plague_unreckoned(view, st), "plague doctor")
        self.assertIsNone(S.plague_unreckoned(view, state(**EXECUTED_D1)))


def _payloads():
    def pay(events, rows=(), claims=C, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players,
                "infos": list(rows),
                "script": {"name": "Pestdoktor", "characters": IDS},
                "days_done": list(days)}

    def gave(night, role):
        return {"type": "PlagueDoctorGave", "night": night, "player": 4,
                "role": role}

    pd = C[:4] + ["PlagueDoctor"] + C[5:]
    return [
        pay({4: ["X1"]}, claims=pd),
        pay({4: ["X1"], 0: ["N2"], 1: ["N2"]}, claims=pd),
        pay({4: ["X1"], 0: ["W2"]}, claims=pd),
        pay({4: ["X1"], 0: ["S2"]}, claims=pd),
        pay({4: ["X1"]}, [gave(1, "Poisoner")], claims=pd),
        pay({4: ["X1"], 6: ["X2"]}, claims=pd, days=(1, 2, 3)),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_plague_doctor_boards(self):
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
