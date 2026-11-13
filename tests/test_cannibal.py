"""The Cannibal, stage 1 (12.11.2026, claude/kannibale-lesarten.md).

"You have the ability of the recently killed executee. If they are evil,
you are poisoned until a good player dies by execution." Patrick's
answers of 12.11.2026:

  A  A "you start knowing" ability works from the night after the
     execution, as the Philosopher's from the night it took it.
  B  Its own once-per-game use, once per character.
  C  A row that does not fit a good executee rules the world out; while
     an evil executee poisons it, any row fits.
  D  Philosopher, Hermit, Alchemist, Drunk and Lunatic executees come in
     stage 2.
"""
import json
import pathlib
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking       # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["cannibal", "chef", "empath", "washerwoman", "librarian", "monk",
       "professor", "soldier", "mayor", "philosopher",
       "saint", "recluse", "butler",
       "scarletwoman", "baron", "imp"]
CS = scripts.from_ids("Kannibale", IDS)
#    0       1         2        3            4       5
R = ["Chef", "Empath", "Saint", "Librarian", "Monk", "Cannibal",
     "ScarletWoman", "Imp"]
C = ["Chef", "Empath", "Saint", "Librarian", "Monk", "Cannibal",
     "Mayor", "Soldier"]


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def state(rows=(), days=(1, 2), claims=C, script=CS, **kw):
    return GameState(n_players=len(claims), script=script,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def cost(rows=(), roles=R, **kw):
    return S.explanation_cost(world(roles), state(rows, **kw))


def executed(seat, day=1):
    return dict(executions={day: seat}, deaths={seat: (f"E{day}",)})


class WhatItAte(SolverTest):

    def test_the_last_execution_death_by_then(self):
        st = state(**executed(1))
        self.assertIsNone(I.cannibal_meal(world(), st, 5, "D1"))
        self.assertEqual(I.cannibal_meal(world(), st, 5, "E1"),
                         (1, "Empath", "good"))
        self.assertEqual(I.cannibal_meal(world(), st, 5, "N2"),
                         (1, "Empath", "good"))
        self.assertEqual(I.cannibal_ate(world(), st, 5, "N2"), "Empath")
        self.assertFalse(I.cannibal_poisoned(world(), st, 5, "N2"))

    def test_a_night_and_a_day_count_the_day_before(self):
        self.assertEqual(I._days_eaten_by("N3"), 2)
        self.assertEqual(I._days_eaten_by("D3"), 2)
        self.assertEqual(I._days_eaten_by("E3"), 3)

    def test_an_evil_executee_poisons_it(self):
        st = state(**executed(6))
        self.assertIsNone(I.cannibal_ate(world(), st, 5, "N2"))
        self.assertTrue(I.cannibal_poisoned(world(), st, 5, "N2"))

    def test_a_good_one_after_an_evil_one_ends_the_poison(self):
        st = state(days=(1, 2, 3), executions={1: 6, 2: 1},
                   deaths={6: ("E1",), 1: ("E2",)})
        self.assertTrue(I.cannibal_poisoned(world(), st, 5, "N2"))
        self.assertFalse(I.cannibal_poisoned(world(), st, 5, "N3"))
        self.assertEqual(I.cannibal_ate(world(), st, 5, "N3"), "Empath")

    def test_a_dead_cannibal_keeps_what_it_had(self):
        st = state(days=(1, 2, 3), executions={1: 1, 2: 0},
                   deaths={1: ("E1",), 5: ("N2",), 0: ("E2",)})
        self.assertEqual(I.cannibal_ate(world(), st, 5, "N3"), "Empath")

    def test_executed_itself_it_has_eaten_nothing(self):
        st = state(**executed(5))
        self.assertIsNone(I.cannibal_ate(world(), st, 5, "N2"))

    def test_its_own_execution_is_no_meal(self):
        # What it had goes on, to fire at its death (13.11.2026).
        st = state(days=(1, 2, 3), executions={1: 1, 2: 5},
                   deaths={1: ("E1",), 5: ("E2",)})
        self.assertEqual(I.cannibal_meal(world(), st, 5, "E2"),
                         (1, "Empath", "good"))

    def test_the_alchemist_gives_nothing_yet(self):
        # Stage 2b (Patrick, 13.11.2026).
        roles = R[:3] + ["Alchemist"] + R[4:]
        st = state(**executed(3))
        self.assertIsNone(I.cannibal_ate(world(roles), st, 5, "N2"))
        self.assertIn("Alchemist", I.CANNIBAL_NOT_YET)
        self.assertNotIn("Philosopher", I.CANNIBAL_NOT_YET)
        self.assertNotIn("Hermit", I.CANNIBAL_NOT_YET)

    def test_held_as_a_philosopher_holds_what_it_took(self):
        st = state(**executed(1))
        self.assertTrue(I.took_it(world(), st, 5, "Empath", "N2"))
        self.assertFalse(I.took_it(world(), st, 5, "Empath", "N1"))
        self.assertEqual(I.cannibal_holders(world(), st, "Empath", "N2"),
                         [5])


class ItsRows(SolverTest):
    """C: its row as the executee's character."""

    def test_a_row_that_fits_the_good_executee(self):
        # Seat 5 sits between the Monk and the Scarlet Woman: one evil.
        self.assertIsNotNone(cost([I.Empath(2, 5, count=1)],
                                  **executed(1)))

    def test_a_wrong_count_rules_the_world_out(self):
        self.assertIsNone(cost([I.Empath(2, 5, count=0)], **executed(1)))

    def test_a_row_that_is_not_the_executees_rules_it_out(self):
        self.assertIsNone(cost([I.Empath(2, 5, count=1)], **executed(0)))

    def test_poisoned_any_row_fits(self):
        self.assertIsNotNone(cost([I.Empath(2, 5, count=0)],
                                  **executed(6)))


class ItWakes(SolverTest):

    def test_as_what_it_ate(self):
        self.assertTrue(waking.woke(world(), state(**executed(1)), 5, 2))

    def test_not_before_it_ate(self):
        self.assertFalse(waking.woke(world(), state(), 5, 2))


class TheProfessor(SolverTest):
    """Found with this stage: a Cannibal that ate the Professor raised it,
    and the solver asked the dead Professor, which then had used its
    raise when it raised somebody itself."""

    def test_it_raises_the_professor_it_ate(self):
        roles = R[:4] + ["Professor"] + R[5:]
        claims = C[:4] + ["Professor"] + C[5:]
        kw = dict(days=(1, 2, 3), claims=claims, executions={1: 4},
                  deaths={4: ("E1",), 0: ("N2",)},
                  resurrections={4: ("N2",), 0: ("N3",)})
        self.assertIsNotNone(cost(roles=roles, **kw))
        kw["claims"] = claims[:5] + ["Soldier"] + claims[6:]
        no = roles[:5] + ["Soldier"] + roles[6:]
        self.assertIsNone(cost(roles=no, **kw))


# Stage 2 (13.11.2026, claude/kannibale-2-lesarten.md).
IDS2 = IDS + ["hermit", "princess", "drunk", "lunatic", "klutz"]
CS2 = scripts.from_ids("Kannibale 2", IDS2)


def state2(rows=(), **kw):
    return state(rows, script=CS2, **kw)


def cost2(rows=(), roles=R, **kw):
    return S.explanation_cost(world(roles), state2(rows, **kw))


class TheDrunkAndTheLunatic(SolverTest):
    """A and B: what it is told is made up; it may have been woken."""

    def test_after_the_drunk_it_is_as_drunk(self):
        roles = R[:3] + ["Drunk"] + R[4:]
        st = state2(**executed(3))
        self.assertTrue(I.cannibal_poisoned(world(roles), st, 5, "N2"))
        self.assertTrue(I.cannibal_made_up(world(roles), st, 5, "N2"))
        self.assertIsNotNone(cost2([I.Empath(2, 5, count=0)], roles=roles,
                                   **executed(3)))
        self.assertTrue(waking.uncertain(world(roles), st, 5, 2))

    def test_after_the_lunatic_any_row_fits(self):
        roles = R[:3] + ["Lunatic"] + R[4:]
        st = state2(**executed(3))
        self.assertFalse(I.cannibal_poisoned(world(roles), st, 5, "N2"))
        self.assertTrue(I.cannibal_made_up(world(roles), st, 5, "N2"))
        self.assertIsNotNone(cost2([I.Empath(2, 5, count=0)], roles=roles,
                                   **executed(3)))
        self.assertTrue(waking.uncertain(world(roles), st, 5, 2))


class ThePhilosopher(SolverTest):
    """C: it chooses once, and has it until the next execution death."""

    ROLES = R[:3] + ["Philosopher"] + R[4:]

    def test_what_it_chose_is_its_own(self):
        rows = [I.PhilosopherChoice(2, 5, role="Chef")]
        st = state(rows, days=(1, 2), **executed(3))
        w = world(self.ROLES)
        self.assertTrue(I.took_it(w, st, 5, "Chef", "N2"))
        self.assertFalse(I.took_it(w, st, 5, "Chef", "N1"))

    def test_until_the_next_execution_death(self):
        rows = [I.PhilosopherChoice(2, 5, role="Chef")]
        st = state(rows, days=(1, 2, 3), executions={1: 3, 2: 1},
                   deaths={3: ("E1",), 1: ("E2",)})
        w = world(self.ROLES)
        self.assertTrue(I.took_it(w, st, 5, "Chef", "N2"))
        self.assertFalse(I.took_it(w, st, 5, "Chef", "N3"))

    def test_it_drunks_whoever_holds_it(self):
        rows = [I.PhilosopherChoice(2, 5, role="Empath")]
        st = state(rows, days=(1, 2), **executed(3))
        got = [src for src in S.a_cannibal_philosopher_drunks_whoever_had_it(
            world(self.ROLES), st, 2)]
        self.assertEqual([sorted(src.seats) for src in got], [[1]])

    def test_its_rows_as_what_it_chose(self):
        # Seat 5 between the Monk and the Scarlet Woman: one evil.
        rows = [I.PhilosopherChoice(2, 5, role="Empath"),
                I.Empath(3, 5, count=1)]
        self.assertIsNotNone(cost(rows, roles=self.ROLES,
                                  days=(1, 2, 3), **executed(3)))
        rows[1] = I.Empath(3, 5, count=0)
        self.assertIsNone(cost(rows, roles=self.ROLES,
                               days=(1, 2, 3), **executed(3)))


class TheHermit(SolverTest):
    """D: every Outsider's ability, as the Hermit has them."""

    def test_it_has_the_outsiders(self):
        roles = R[:3] + ["Hermit"] + R[4:]
        st = state2(**executed(3))
        w = world(roles)
        self.assertEqual(I.cannibal_ate(w, st, 5, "N2"), "Hermit")
        for role in ("Saint", "Klutz", "Butler"):
            self.assertTrue(I.has_cannibal_ability(w, st, 5, role, "N2"),
                            role)
        self.assertFalse(I.has_cannibal_ability(w, st, 5, "Empath", "N2"))
        self.assertIn(5, I.cannibal_holders(w, st, "Saint", "N2"))


class ThePrincess(SolverTest):
    """The jinx: it nominated, executed and killed her, and the Demon
    kills nobody that night."""

    ROLES = R[:3] + ["Princess"] + R[4:]

    def test_the_demon_does_not_kill(self):
        kw = dict(days=(1, 2), executions={1: 3},
                  deaths={3: ("E1",), 0: ("N2",)})
        self.assertIsNotNone(cost2(roles=self.ROLES, **kw))
        self.assertIsNone(cost2([I.PrincessNominated(1, 5, target=3)],
                                roles=self.ROLES, **kw))

    def test_not_if_she_was_somebody_else(self):
        kw = dict(days=(1, 2), executions={1: 3},
                  deaths={3: ("E1",), 0: ("N2",)})
        self.assertIsNotNone(cost2([I.PrincessNominated(1, 5, target=3)],
                                   **kw))


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


def board(infos=(), claims=C, events=None, **extra):
    """A page-shaped board. `events` per seat as the page writes them:
    "X1" executed and dead on day 1, "N2" dead in night 2. (The stage 1
    boards passed `deaths` and `executions`, which the page does not
    read, so they were quiet boards; 13.11.2026.)"""
    events = events or {}
    out = {"n_players": 8,
           "players": [{"claim": c, "events": list(events.get(i, ()))}
                       for i, c in enumerate(claims)],
           "infos": list(infos), "days_done": [1, 2],
           "script": {"name": "Kannibale", "characters": IDS}}
    out.update(extra)
    return out


class BothLanguagesAgree(SolverTest):

    def test_a_quiet_board(self):
        compare(self, board())

    def test_an_empath_eaten(self):
        compare(self, board(
            [{"type": "Empath", "night": 2, "player": 5, "count": 1}],
            events={1: ["X1"]}))

    def test_an_executee_that_may_be_evil(self):
        # The Mayor claim: good, and the row must fit; evil, and the
        # Cannibal was poisoned.
        compare(self, board(
            [{"type": "Empath", "night": 2, "player": 5, "count": 0}],
            events={6: ["X1"]}))


class BothLanguagesAgreeOnStageTwo(SolverTest):

    def test_a_philosopher_eaten(self):
        claims = C[:3] + ["Philosopher"] + C[4:]
        compare(self, board(
            [{"type": "PhilosopherChoice", "night": 2, "player": 5,
              "role": "Empath"},
             {"type": "Empath", "night": 3, "player": 5, "count": 1}],
            claims=claims, events={3: ["X1"]}, days_done=[1, 2, 3]))

    def test_a_princess_eaten(self):
        claims = C[:3] + ["Princess"] + C[4:]
        compare(self, board(
            [{"type": "PrincessNominated", "night": 1, "player": 5,
              "target": 3}],
            claims=claims, events={3: ["X1"], 0: ["N2"]},
            script={"name": "Kannibale 2", "characters": IDS2}))


if __name__ == "__main__":
    unittest.main()
