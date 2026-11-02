"""Stelle 104 (02.11.2026): a source of drunkenness that dies in the night.

"A character's ability always ends with death" — and the drunkenness or
poison it gave ends with it, not merely rests (table ruling, v3.1.4,
03.10.2026). The impairment plan kept a night and the day after it under
one key, so an Innkeeper killed in night 3 that had drunk the Tea Lady
kept her drunk at the gallows on day 3: the neighbour she saved there
asked her working, the death beside her asked her drunk, and the world
that really happened was thrown out (seed 2517 of the line Tea Lady,
Snake Charmer, Gambler, found 31.10.2026).

Now the days' demands are kept apart, and a source whose actor died in
the night covers that night and not the day.
"""
import json
import pathlib
import random
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
from helpers import SolverTest                    # sets up the import path

import botc.solver as S                           # noqa: E402
from botc import impairment                       # noqa: E402
from botc.impairment import Source                # noqa: E402
from botc.info import GameState                   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
MUST = ("TeaLady", "SnakeCharmer", "Gambler")


def game(seed, must=MUST):
    import claims as C
    import play_games
    import simulate
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    n = [7, 8, 9, 10, 11][seed % 5]
    deal, heard = simulate.play(n, rng, nights=4, script=script)
    cl, wk, _ = C.claims_for(deal, rng, script=script)
    st = GameState(n_players=n, script=script, claims=cl, wakes=wk,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, st


class TheInnkeeperDiesInTheNight(SolverTest):

    def test_the_true_world_is_kept(self):
        deal, st = game(2517)
        # The board as found: the Innkeeper (seat 0) dies in night 3,
        # and on day 3 the Tea Lady's neighbour walks from the gallows.
        self.assertEqual(deal.roles[0], "Innkeeper")
        self.assertEqual(deal.roles[1], "TeaLady")
        self.assertIn("N3", st.died_at(0))
        self.assertIsNone(st.execution_death(3))
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))


class ThePoisonerDiesInTheNight(SolverTest):
    """The simulator kept a Poisoner's poison through the day after the
    Demon killed it (seed 1800 of the gate line Innkeeper, Poisoner, Tea
    Lady, Sailor, Saint): the Tea Lady it poisoned in night 2 stood by
    while her neighbour, the Oracle, died at the gallows. The same rule
    now holds there for the Courtier, the Philosopher, the Xaan and the
    Minstrel too."""

    def test_the_tea_lady_is_sober_by_day(self):
        deal, st = game(1800, ("Innkeeper", "Poisoner", "TeaLady", "Sailor",
                               "Saint"))
        self.assertEqual((deal.roles[4], deal.roles[5]),
                         ("Poisoner", "TeaLady"))
        self.assertEqual(deal.poisoned_by.get(2), 4)
        self.assertEqual(deal.poisoned.get(2), 5)
        self.assertIn("N2", st.died_at(4))
        # The Oracle beside her is executed on day 2 and walks away.
        self.assertEqual(st.executions.get(2), 2)
        self.assertIsNone(st.execution_death(2))
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))


# One Innkeeper (actor 0) and one Poisoner (actor 5) on a night.
INN = Source("Innkeeper", frozenset({1, 6}), capacity=1, cost=0.5,
             repeat_cost=0.5, actor=0)
POI = Source("Poisoner", frozenset(range(7)), capacity=1, cost=0.3,
             repeat_cost=0.3, actor=5)

# (required, forbidden, day_required, day_forbidden, dying) -> result
CASES = [
    # Drunk at night, working by day: only a source that died will do.
    ([1], [], [], [1], [INN], (0.5, {"Innkeeper": 1})),
    ([1], [], [], [1], [], None),
    # Drunk by day: never by one that died in the night.
    ([1], [], [1], [], [INN], (0.3, {"Poisoner": 1})),
    # Both: the one that lives covers both.
    ([1], [], [1], [], [], (0.5, {"Innkeeper": 1})),
    # Nothing died: the night's and the day's together, as before.
    ([1], [1], [], [], [INN], None),
]


class ThePlanSplitsTheDay(SolverTest):

    def test_in_python(self):
        for req, forb, dreq, dforb, dying, want in CASES:
            with self.subTest(req=req, dreq=dreq, dforb=dforb,
                              dying=[s.name for s in dying]):
                required = sorted(set(req) | set(dreq))
                got = impairment.plan_night(
                    [INN, POI], required, forb, {},
                    (set(dreq), set(dforb), dying))
                if want is None:
                    self.assertIsNone(got)
                else:
                    self.assertAlmostEqual(got[0], want[0])
                    self.assertEqual(got[1], want[1])

    def test_in_javascript(self):
        script = (
            "import {Source, planNight} from './js/impairment.mjs';"
            "const inn = new Source('Innkeeper', new Set([1, 6]),"
            " {capacity: 1, cost: 0.5, repeatCost: 0.5, actor: 0});"
            "const poi = new Source('Poisoner', new Set([0,1,2,3,4,5,6]),"
            " {capacity: 1, cost: 0.3, repeatCost: 0.3, actor: 5});"
            "const by = {Innkeeper: inn, Poisoner: poi};"
            "const cases = JSON.parse(process.argv[1]);"
            "console.log(JSON.stringify(cases.map(([req, forb, dreq, dforb,"
            " dying]) => { const required = [...new Set([...req, ...dreq])]"
            ".sort((a, b) => a - b);"
            " const got = planNight([inn, poi], required, forb, {},"
            " [new Set(dreq), new Set(dforb), dying.map(n => by[n])]);"
            " return got === null ? null : [got.cost, got.hits]; })));")
        payload = [[r, f, dr, df, [s.name for s in dy]]
                   for r, f, dr, df, dy, _w in CASES]
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(payload)], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(got.returncode, 0, got.stderr)
        for out, (*_rest, want) in zip(json.loads(got.stdout), CASES):
            if want is None:
                self.assertIsNone(out)
            else:
                self.assertAlmostEqual(out[0], want[0])
                self.assertEqual(out[1], want[1])


class BothLanguagesAgree(SolverTest):

    def test_on_the_played_game(self):
        import app
        import play_games
        from make_fixtures import played
        rng = random.Random(2517)
        script = play_games.an_awkward_script(rng, must_have=MUST)
        payload = played("s2517", script, 2517, [7, 8, 9, 10, 11][2517 % 5],
                         4, rng=rng)["payload"]
        js = ("import {solveBoard} from './js/api.mjs';"
              "const p=JSON.parse(process.argv[1]);"
              "const r=solveBoard(p); console.log(JSON.stringify("
              "r.error || r.valid));")
        got = subprocess.run(["node", "--input-type=module", "-e", js,
                              json.dumps(payload)], cwd=ROOT,
                             capture_output=True, text=True, timeout=1800)
        self.assertEqual(got.returncode, 0, got.stderr)
        r = app.run_solve(payload)
        self.assertEqual(json.loads(got.stdout), r.get("error") or r["valid"])


if __name__ == "__main__":
    unittest.main()
