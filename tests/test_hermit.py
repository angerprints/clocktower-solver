"""The Hermit, stage 1 (07.11.2026, claude/eremit-lesarten.md,
claude/eremit-1.md).

"You have all Outsider abilities. [-0 or -1 Outsider]" Patrick's answers
of 07.11.2026:

  A  The Outsider taken out may be the Hermit itself: then it is not in
     play, and there is one Outsider fewer.
  B  Believing it is a Townsfolk (the Drunk's), what it would have to
     choose itself does not happen (stage 2).
  C  Drunk and Lunatic both on the script: the Storyteller's (stage 2).
  D  A jinx poisons the whole Hermit (stage 2).

Stage 1: every Outsider ability of the script but the Drunk's and the
Lunatic's, held the way a Philosopher holds what it took.
"""
import json
import pathlib
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking       # noqa: E402
from botc.info import GameState, hermit_abilities  # noqa: E402
from botc.worlds import World, _bags, enumerate_worlds, HERMIT_GONE  # noqa

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["hermit", "saint", "recluse", "sweetheart", "butler", "klutz",
       "scarletwoman", "baron", "imp",
       "chef", "empath", "washerwoman", "librarian", "monk", "undertaker",
       "slayer", "soldier", "mayor", "chambermaid"]
HS = scripts.from_ids("Eremit", IDS)
#    0       1         2              3            4       5
R = ["Chef", "Empath", "Washerwoman", "Librarian", "Monk", "Hermit",
     "ScarletWoman", "Imp"]
C = ["Chef", "Empath", "Washerwoman", "Librarian", "Monk", "Hermit",
     "Mayor", "Soldier"]


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def state(rows=(), days=(1, 2), claims=C, script=HS, **kw):
    return GameState(n_players=len(claims), script=script,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def cost(rows=(), roles=R, **kw):
    return S.explanation_cost(world(roles), state(rows, **kw))


class ItsAbilities(SolverTest):

    def test_every_outsider_of_the_script_but_itself(self):
        self.assertEqual(hermit_abilities(HS),
                         {"Saint", "Recluse", "Sweetheart", "Butler",
                          "Klutz"})

    def test_not_yet_the_drunks_nor_the_lunatics(self):
        sc = scripts.from_ids("Eremit-Trunkenbold",
                              IDS + ["drunk", "lunatic"])
        got = hermit_abilities(sc)
        self.assertNotIn("Drunk", got)
        self.assertNotIn("Lunatic", got)
        self.assertIn("Saint", got)

    def test_nothing_without_a_hermit_on_the_script(self):
        sc = scripts.from_ids("Ohne", [k for k in IDS if k != "hermit"])
        self.assertEqual(hermit_abilities(sc), frozenset())

    def test_held_as_a_philosopher_holds_what_it_took(self):
        st = state()
        self.assertTrue(I.took_it(world(), st, 5, "Saint", "D1"))
        self.assertTrue(I.falls_as(world(), st, 5, "Sweetheart", "N2"))
        self.assertFalse(I.took_it(world(), st, 5, "Imp", "N2"))
        self.assertFalse(I.took_it(world(), st, 4, "Saint", "D1"))


class TheBag(SolverTest):
    """A: "[-0 or -1 Outsider]", and the one taken out may be itself."""

    def test_it_may_take_itself_out(self):
        bags = _bags(8, HS)
        gone = [(p, c) for p, c in bags if HERMIT_GONE in p]
        self.assertTrue(gone)
        # Without it and one Outsider fewer.
        self.assertTrue(any(c["outsider"] == 0 and "Hermit" not in p
                            for p, c in gone))

    def test_worlds_with_it_and_without(self):
        claims = dict(enumerate(C))
        got = {("Hermit" in w.roles,
                sum(1 for r in w.roles if r in HS.outsiders))
               for w in enumerate_worlds(8, claims, script=HS)}
        self.assertIn((True, 1), got)
        # The Hermit's claim a lie, nobody's an Outsider: it took itself
        # out, or no Hermit was in the bag.
        self.assertIn((False, 0), got)

    def test_no_bag_twice(self):
        bags = _bags(8, HS)
        keys = [(frozenset(p - {HERMIT_GONE}), tuple(sorted(c.items())))
                for p, c in bags]
        self.assertEqual(len(keys), len(set(keys)))


class WhatItDoes(SolverTest):

    def test_executed_with_the_saints_ability_good_loses(self):
        # Nothing on this script droisons it: a Hermit executed with the
        # Saint's ability ends the game, so a game that went on rules the
        # world out.
        sc = scripts.from_ids("Eremit-Heilige",
                              ["hermit", "saint", "scarletwoman", "imp",
                               "chef", "empath", "washerwoman", "librarian",
                               "monk", "soldier", "mayor"])
        kw = dict(executions={1: 5}, deaths={5: ("E1",)}, script=sc)
        self.assertIsNone(cost(**kw))
        plain = scripts.from_ids("Eremit-ohne", [
            "hermit", "recluse", "scarletwoman", "imp", "chef", "empath",
            "washerwoman", "librarian", "monk", "soldier", "mayor"])
        kw["script"] = plain
        self.assertIsNotNone(cost(**kw))

    def test_it_wakes_as_the_butler(self):
        st = state()
        self.assertTrue(waking.woke(world(), st, 5, 2))
        sc = scripts.from_ids("Ohne-Butler",
                              [k for k in IDS if k != "butler"])
        self.assertFalse(waking.woke(world(), state(script=sc), 5, 2))

    def test_the_recluses_ability_registers(self):
        # The Empath beside the Hermit (seat 5 is not beside 1; move it).
        roles = ["Chef", "Empath", "Hermit", "Librarian", "Monk",
                 "Washerwoman", "ScarletWoman", "Imp"]
        claims = ["Chef", "Empath", "Hermit", "Librarian", "Monk",
                  "Washerwoman", "Mayor", "Soldier"]
        row = I.Empath(1, 1, count=1)
        sc = scripts.from_ids("Eremit-Saint", [k for k in IDS
                                               if k != "recluse"]
                              + ["virgin"])
        st = GameState(n_players=8, script=HS, claims=dict(enumerate(claims)),
                       infos=[row], days_done={1})
        self.assertIsNotNone(S.explanation_cost(world(roles), st))
        st = GameState(n_players=8, script=sc, claims=dict(enumerate(claims)),
                       infos=[row], days_done={1})
        self.assertIsNone(S.explanation_cost(world(roles), st))

    def test_its_klutz_row_is_its_own(self):
        # It points at the Imp on dying in the night, and good loses: a
        # game that went on says it was not working, and nothing here
        # stops it.
        sc = scripts.from_ids("Eremit-Tollpatsch",
                              ["hermit", "klutz", "scarletwoman", "imp",
                               "chef", "empath", "washerwoman", "librarian",
                               "monk", "soldier", "mayor"])
        row = I.KlutzChoice(2, 5, target=7)
        kw = dict(deaths={5: ("N2",)}, script=sc)
        self.assertIsNone(cost([row], **kw))
        self.assertIsNotNone(cost([I.KlutzChoice(2, 5, target=0)], **kw))


class TwoPlagueDoctors(SolverTest):
    """Found with this stage: the real Plague Doctor's death and a
    Hermit's both gave the Storyteller the Marionette, and the same good
    neighbour was made it twice. It then believed it was the Marionette
    and woke on its own schedule without end."""

    def test_it_believes_what_it_was(self):
        from botc.worlds import PlagueMade, Timeline
        tl = Timeline(world(), (PlagueMade("N2", 0, "Marionette", "good", -1),
                                PlagueMade("D2", 0, "Marionette", "good")))
        self.assertEqual(tl.believes[0], "Chef")


# Stage 2 (07.11.2026): the Drunk's and the Lunatic's ability are what it
# believes (B, C), and the Damsel's jinxes poison it whole (D).
DS = scripts.from_ids("Eremit-Trunkenbold", IDS + ["drunk"])
LS = scripts.from_ids("Eremit-Verrückte", IDS + ["lunatic", "po"])


class WhatItBelieves(SolverTest):

    def test_with_the_drunks_a_townsfolk_with_the_lunatics_the_demon(self):
        from botc.roles import hermit_tokens
        self.assertEqual(hermit_tokens(HS), [])
        self.assertIn("Chef", hermit_tokens(DS))
        self.assertNotIn("Imp", hermit_tokens(DS))
        self.assertIn("Imp", hermit_tokens(LS))
        self.assertNotIn("Chef", hermit_tokens(LS))

    def test_a_townsfolk_claim_may_be_a_hermit_that_thinks_so(self):
        claims = dict(enumerate(C[:5] + ["Soldier", "Mayor", "Slayer"]))
        got = {(r, b) for w in enumerate_worlds(8, claims, script=DS)
               for r, b in zip(w.roles, w.believes) if r == "Hermit"}
        self.assertIn(("Hermit", "Chef"), got)
        # Never a Hermit that knows it: the Drunk's ability says it does not.
        self.assertNotIn(("Hermit", None), got)

    def test_it_chooses_nothing_believing_it_is_somebody_else(self):
        w = World(tuple(R), (None,) * 5 + ("Soldier",) + (None,) * 2)
        st = state(script=DS)
        self.assertFalse(I.has_hermit_ability(w, st, 5, "Klutz", "N2"))
        self.assertFalse(I.has_hermit_ability(w, st, 5, "Butler", "N2"))
        self.assertTrue(I.has_hermit_ability(w, st, 5, "Saint", "D1"))
        self.assertTrue(I.has_hermit_ability(world(), st, 5, "Klutz", "N2"))

    def test_thinking_it_is_the_demon_it_still_chooses(self):
        # Patrick, 12.11.2026: only the Townsfolk belief stops it.
        w = World(tuple(R), (None,) * 5 + ("Imp",) + (None,) * 2)
        st = state(script=LS)
        self.assertTrue(I.has_hermit_ability(w, st, 5, "Klutz", "N2"))
        self.assertTrue(I.has_hermit_ability(w, st, 5, "Butler", "N2"))
        # And wakes as its Butler on the first night, too.
        self.assertTrue(waking.woke(w, st, 5, 1))

    def test_the_mathematician_counts_it_where_the_drunk_is_on_the_script(self):
        w = World(tuple(R), (None,) * 5 + ("Chef",) + (None,) * 2)
        low, _high = I._possible_impairment_counts(w, state(script=DS), 2)
        self.assertEqual(low, 1)
        w = World(tuple(R), (None,) * 5 + ("Imp",) + (None,) * 2)
        low, _high = I._possible_impairment_counts(w, state(script=LS), 2)
        self.assertEqual(low, 0)

    def test_it_wakes_as_what_it_thinks_it_is(self):
        w = World(tuple(R), (None,) * 5 + ("Chef",) + (None,) * 2)
        self.assertTrue(waking.woke(w, state(script=DS), 5, 1))
        self.assertFalse(waking.woke(w, state(script=DS), 5, 2))

    def test_what_it_is_told_as_that_one_is_made_up(self):
        from botc.roles import ARBITRARY, ability_state
        w = World(tuple(R), (None,) * 5 + ("Chef",) + (None,) * 2)
        self.assertEqual(ability_state(w, 5, "Chef", "N1"), ARBITRARY)


class TheDamselsJinx(SolverTest):

    def test_a_spy_poisons_the_whole_hermit(self):
        sc = scripts.from_ids("Eremit-Unschuld",
                              ["hermit", "damsel", "spy", "imp", "chef",
                               "empath", "washerwoman", "librarian", "monk",
                               "soldier", "mayor"])
        roles = R[:6] + ["Spy", "Imp"]
        st = state(script=sc)
        got = S.a_spy_or_widow_poisons_the_hermit(world(roles), st, 2)
        self.assertEqual([sorted(x.seats) for x in got], [[5]])
        plain = R[:6] + ["ScarletWoman", "Imp"]
        sc2 = scripts.from_ids("Eremit-Unschuld-2",
                               ["hermit", "damsel", "scarletwoman", "imp",
                                "chef", "empath", "washerwoman", "librarian",
                                "monk", "soldier", "mayor"])
        self.assertEqual(S.a_spy_or_widow_poisons_the_hermit(
            world(plain), state(script=sc2), 2), [])


def compare(test, case):
    """Python and JavaScript give the same shares on this board."""
    import app
    script = ("import {solveBoard} from './js/api.mjs';"
              "const p=JSON.parse(process.argv[1]);"
              "const r=solveBoard(p);"
              "console.log(JSON.stringify(r.error ? r.error : {"
              " valid: r.valid,"
              " rows: r.rows.map(x => [x.evil_pct, x.demon_pct])}));")
    got = subprocess.run(["node", "--input-type=module", "-e", script,
                          json.dumps(case)], cwd=ROOT,
                         capture_output=True, text=True, timeout=900)
    test.assertEqual(got.returncode, 0, got.stderr)
    js = json.loads(got.stdout)
    py = app.run_solve(case)
    test.assertNotIn("error", py)
    test.assertNotIsInstance(js, str, js)
    test.assertGreater(py["valid"], 0)
    test.assertEqual(js["valid"], py["valid"])
    for (je, jd), row in zip(js["rows"], py["rows"]):
        test.assertAlmostEqual(je, row["evil_pct"], places=6)
        test.assertAlmostEqual(jd, row["demon_pct"], places=6)
    return py


class BothLanguagesAgree(SolverTest):

    def test_a_quiet_board(self):
        case = {"n_players": 8,
                "players": [{"claim": c, "events": []} for c in C],
                "infos": [], "days_done": [1],
                "script": {"name": "Eremit", "characters": IDS}}
        compare(self, case)

    def test_a_hermit_executed_and_a_chambermaid(self):
        claims = C[:4] + ["Chambermaid"] + C[5:]
        case = {"n_players": 8,
                "players": [{"claim": c, "events": []} for c in claims],
                "infos": [{"type": "ChambermaidInfo", "night": 2,
                           "player": 4, "a": 5, "b": 0, "count": 1}],
                "deaths": {"5": ["E2"]}, "executions": {"2": 5},
                "days_done": [1, 2],
                "script": {"name": "Eremit", "characters": IDS}}
        compare(self, case)

    def test_a_hermit_that_thinks_it_is_a_townsfolk(self):
        case = {"n_players": 8,
                "players": [{"claim": c, "events": []}
                            for c in C[:5] + ["Soldier", "Mayor", "Slayer"]],
                "infos": [], "days_done": [1],
                "script": {"name": "Eremit-Trunkenbold",
                           "characters": IDS + ["drunk"]}}
        compare(self, case)

    def test_its_klutz_row(self):
        case = {"n_players": 8,
                "players": [{"claim": c, "events": []} for c in C],
                "infos": [{"type": "KlutzChoice", "night": 2, "player": 5,
                           "target": 0}],
                "deaths": {"5": ["N2"]}, "days_done": [1, 2],
                "script": {"name": "Eremit", "characters": IDS}}
        compare(self, case)


if __name__ == "__main__":
    unittest.main()
