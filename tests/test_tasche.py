"""How likely the bag was to be drawn (13.11.2026, Patrick's answers A to C
in claude/hauptziel-tasche-lesarten.md)."""
import json
import math
import pathlib
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TB = scripts.TROUBLE_BREWING


def world(roles):
    return World(tuple(roles), (None,) * len(roles))


def state(n=8, script=TB):
    return GameState(n_players=n, script=script, claims={}, infos=[],
                     days_done=set())


class TheBag(SolverTest):

    def test_a_barons_bag_is_likelier_world_for_world(self):
        # 8 players: 5 Townsfolk and 1 Outsider, or with the Baron 3 and 3.
        plain = world(["Chef", "Empath", "Monk", "Mayor", "Virgin", "Saint",
                       "Poisoner", "Imp"])
        baron = world(["Chef", "Empath", "Monk", "Butler", "Recluse", "Saint",
                       "Baron", "Imp"])
        ratio = S.bag_weight(baron, state()) / S.bag_weight(plain, state())
        self.assertAlmostEqual(ratio, (math.comb(13, 5) * math.comb(4, 1))
                               / (math.comb(13, 3) * math.comb(4, 3)))
        self.assertGreater(ratio, 4)

    def test_a_storytellers_choice_halves_it(self):
        bmr = scripts.BAD_MOON_RISING
        a = world(["Chef", "Empath", "Monk", "Mayor", "Virgin", "Saint",
                   "Godfather", "Imp"])
        b = world(["Chef", "Empath", "Monk", "Mayor", "Virgin", "Saint",
                   "Poisoner", "Imp"])
        # Not on the script, but the halving is the Godfather's alone.
        self.assertAlmostEqual(S.bag_weight(a, state(script=bmr)) * 2,
                               S.bag_weight(b, state(script=bmr)))

    def test_off_it_is_equal_weighting(self):
        was = S.BAG_PRIOR_POWER
        try:
            S.BAG_PRIOR_POWER = 0.0
            self.assertEqual(S.bag_weight(world(["Chef"] * 8), state()), 1.0)
        finally:
            S.BAG_PRIOR_POWER = was


class BothLanguagesAgree(SolverTest):

    def test_three_outsider_claims(self):
        import app
        claims = ["Chef", "Empath", "Saint", "Butler", "Recluse", "Monk",
                  "Mayor", "Virgin"]
        case = {"n_players": 8,
                "players": [{"claim": c, "events": []} for c in claims],
                "infos": [{"type": "Chef", "night": 1, "player": 0,
                           "count": 0}],
                "days_done": [1],
                "script": {"name": "Trouble Brewing",
                           "characters": [k.lower() for k in TB.keys]}}
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const r=solveBoard(JSON.parse(process.argv[1]));"
                  "console.log(JSON.stringify(r.error ? r.error : {"
                  " valid: r.valid,"
                  " rows: r.rows.map(x => [x.evil_pct, x.demon_pct])}));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(case)], cwd=ROOT,
                             capture_output=True, text=True, timeout=900)
        self.assertEqual(got.returncode, 0, got.stderr)
        js = json.loads(got.stdout)
        py = app.run_solve(case)
        self.assertNotIn("error", py)
        self.assertNotIsInstance(js, str, js)
        self.assertEqual(js["valid"], py["valid"])
        for (je, jd), row in zip(js["rows"], py["rows"]):
            self.assertAlmostEqual(je, row["evil_pct"], places=6)
            self.assertAlmostEqual(jd, row["demon_pct"], places=6)


if __name__ == "__main__":
    unittest.main()
