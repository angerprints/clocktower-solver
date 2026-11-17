"""The last three (17.11.2026, Patrick's answers in
claude/hauptziel-final3-lesarten.md): the town may hang the real Saint and
lose the game on it (A), a good player lying for no reason makes up what
its claim would be told (B), and the solver reads a game that ended on a
working Saint's execution."""
import json
import pathlib
import random
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import claims as C                                # noqa: E402
import simulate                                   # noqa: E402
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.info import GameState                   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TB = scripts.TROUBLE_BREWING


def game(seed, script=TB, nights=4):
    rng = random.Random(seed)
    n = [7, 8, 9, 10][seed % 4]
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, notes = C.claims_for(deal, rng, script=script)
    return n, deal, heard, claims, wakes, notes


class TheTownMayHangTheSaint(SolverTest):

    def test_some_games_end_on_the_saint(self):
        ended = [seed for seed in range(200)
                 if game(seed)[1].ended_why == "saint"]
        self.assertGreater(len(ended), 3)
        for seed in ended[:5]:
            n, deal, *_ = game(seed)
            day = deal.game_ends_after
            hanged = next(p for p, at in deal.deaths.items()
                          if at == f"E{day}")
            self.assertEqual(deal.role_at(hanged, f"D{day}"), "Saint")

    def test_the_true_world_of_such_a_game_still_fits(self):
        for seed in range(200):
            n, deal, heard, claims, wakes, notes = game(seed)
            if deal.ended_why != "saint":
                continue
            last = deal.game_ends_after
            state = GameState(n_players=n, script=TB, claims=claims,
                              wakes=wakes,
                              infos=C.told_table(deal, heard, claims, notes,
                                                 last, seed),
                              votes=dict(deal.votes),
                              nominations=dict(deal.nominations),
                              **deal.record(told=False))
            self.assertTrue(state.game_over)
            self.assertIsNotNone(S.explanation_cost(deal.world(), state),
                                 seed)


class TheSaintEndsTheGame(SolverTest):
    CLAIMS = ["Saint", "Chef", "Washerwoman", "Librarian", "Slayer",
              "Ravenkeeper", "Undertaker", "Butler"]

    def state(self, **kw):
        return GameState(n_players=8, script=TB,
                         claims=dict(enumerate(self.CLAIMS)), infos=[], **kw)

    def test_only_at_the_end(self):
        over = self.state(deaths={0: ("E2",)}, game_over=True)
        self.assertTrue(S.the_saint_ended_it(over, 2))
        going_on = self.state(deaths={0: ("E2",)})
        self.assertFalse(S.the_saint_ended_it(going_on, 2))
        later = self.state(deaths={0: ("E2",), 3: ("N3",)}, game_over=True)
        self.assertFalse(S.the_saint_ended_it(later, 2))

    def test_both_languages_agree(self):
        import app
        case = {"n_players": 8,
                "players": [{"claim": c, "events": []} for c in self.CLAIMS],
                "infos": [{"type": "Chef", "night": 1, "player": 1,
                           "count": 0}],
                "days_done": [1], "game_over": True,
                "script": {"name": "Trouble Brewing",
                           "characters": [k.lower() for k in TB.keys]}}
        case["players"][0]["events"] = ["E2"]
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
        self.assertGreater(py["valid"], 0)
        for (je, jd), row in zip(js["rows"], py["rows"]):
            self.assertAlmostEqual(je, row["evil_pct"], places=6)
            self.assertAlmostEqual(jd, row["demon_pct"], places=6)


class TheChaosLiarMakesItUp(SolverTest):

    def test_a_liar_with_an_info_claim_reports(self):
        found = 0
        for seed in range(300):
            n, deal, heard, claims, wakes, notes = game(seed)
            # One the dice gave its own character tells the truth about
            # it and makes nothing up (933f915).
            liars = [s for s, why in notes.items() if "for no reason" in why
                     and not C._claims_its_own(why)]
            if not liars:
                continue
            last = min(4, deal.game_ends_after or 4)
            told = C.told_table(deal, heard, claims, notes, last, seed)
            for seat in liars:
                if claims[seat] in ("Empath", "FortuneTeller", "Chef") \
                        and deal.deaths.get(seat) is None:
                    found += 1
                    self.assertTrue(any(getattr(r, "player", None) == seat
                                        for r in told), (seed, seat))
        self.assertGreater(found, 3)


if __name__ == "__main__":
    unittest.main()
