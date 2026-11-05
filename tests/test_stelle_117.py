"""Stelle 117 (05.11.2026, claude/stelle-117.md): the Boffin gives at the
setup, before anybody acts.

The Boffin gave the Demon the Snake Charmer's ability, and on the first
night a Huntsman found the Damsel, who became the Snake Charmer — not in
play then, as the Huntsman's ability asks. `solver.boffin_may_give` read
who held what at the end of that night, found the Damsel's Snake Charmer,
and refused the gift. With a swap later the true world was lost (seeds
414 and 909 of the Alchemist's gate line torAF).
"""

import json
import pathlib
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import Change, Timeline, World   # noqa: E402

IDS = ["huntsman", "damsel", "snakecharmer", "chef", "empath",
       "investigator", "undertaker", "washerwoman", "saint", "boffin",
       "poisoner", "imp"]
SC = scripts.from_ids("Stelle 117", IDS)

#    0           1       2         3        4      5         6
R = ["Huntsman", "Chef", "Empath", "Boffin", "Imp", "Damsel", "Washerwoman"]
C = ["Huntsman", "Chef", "Empath", "Investigator", "Undertaker",
     "SnakeCharmer", "Washerwoman"]
ROWS = [I.HuntsmanChoice(1, 0, target=5),
        I.BecameInfo(1, 5, role="SnakeCharmer", was="Damsel"),
        I.BoffinGave(1, 3, role="SnakeCharmer")]


def world():
    return World(roles=tuple(R), believes=(None,) * len(R))


def state(rows=ROWS, days=(1, 2)):
    return GameState(n_players=len(C), script=SC,
                     claims=dict(enumerate(C)), infos=list(rows),
                     days_done=set(days))


class TheBoffinGivesFirst(SolverTest):

    def test_a_huntsmans_damsel_does_not_take_the_gift_back(self):
        found = Timeline(world(), (Change("N1", 5, "SnakeCharmer", "good",
                                          480),))
        self.assertIn("SnakeCharmer",
                      S.boffin_may_give(found, state(), "N1", setup=True))
        # A new Demon later: whoever holds it then.
        self.assertNotIn("SnakeCharmer",
                         S.boffin_may_give(found, state(), "N2"))

    def test_the_damsel_charms_the_demon_with_its_gift(self):
        rows = ROWS + [I.SnakeCharmerChoice(2, 5, target=4, swapped=True)]
        self.assertIsNotNone(S.explanation_cost(world(), state(rows)))

    def test_both_languages_agree(self):
        import app
        root = pathlib.Path(__file__).resolve().parent.parent
        rows = [{"type": "HuntsmanChoice", "night": 1, "player": 0,
                 "target": 5},
                {"type": "BoffinGave", "night": 1, "player": 3,
                 "role": "SnakeCharmer"},
                {"type": "SnakeCharmerChoice", "night": 2, "player": 5,
                 "target": 4, "swapped": True}]
        # The board has no row for what the Damsel became: the Huntsman's
        # rule offers it.
        case = {"n_players": len(C),
                "players": [{"claim": c, "events": []} for c in C],
                "infos": rows, "days_done": [1, 2],
                "script": {"name": "Stelle 117", "characters": IDS}}
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const p=JSON.parse(process.argv[1]);"
                  "const r=solveBoard(p);"
                  "console.log(JSON.stringify(r.error ? r.error : {"
                  " valid: r.valid,"
                  " rows: r.rows.map(x => [x.evil_pct, x.demon_pct])}));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(case)], cwd=root,
                             capture_output=True, text=True, timeout=900)
        self.assertEqual(got.returncode, 0, got.stderr)
        js = json.loads(got.stdout)
        py = app.run_solve(case)
        self.assertNotIn("error", py)
        self.assertNotIsInstance(js, str, js)
        self.assertGreater(py["valid"], 0)
        self.assertEqual(js["valid"], py["valid"])
        for (je, jd), row in zip(js["rows"], py["rows"]):
            self.assertAlmostEqual(je, row["evil_pct"], places=6)
            self.assertAlmostEqual(jd, row["demon_pct"], places=6)
        # The Damsel that charmed the Demon holds it now.
        self.assertGreater(py["rows"][5]["demon_pct"], 0)


if __name__ == "__main__":
    unittest.main()
