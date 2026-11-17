"""What a made-up row costs (17.11.2026, Patrick's answers A to C in
claude/hauptziel-bluff-preis-lesarten.md): 0.7 if it would be true were
every seat what it claims, 0.2 if not, and nothing for a choice."""
import json
import pathlib
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.info import (Chef, Empath, FortuneTeller, GameState,  # noqa: E402
                       Investigator, SailorChoice, Undertaker, Washerwoman)

ROOT = pathlib.Path(__file__).resolve().parent.parent
TB = scripts.TROUBLE_BREWING
BMR = scripts.BAD_MOON_RISING

TB_CLAIMS = ["Chef", "Empath", "FortuneTeller", "Investigator",
             "Undertaker", "Washerwoman", "Monk", "Soldier"]


def tb_state(claims=TB_CLAIMS, infos=()):
    return GameState(n_players=len(claims), script=TB,
                     claims=dict(enumerate(claims)), infos=list(infos),
                     days_done=set())


class TheWorldOfTheClaims(SolverTest):

    def test_every_seat_is_what_it_says(self):
        cw = S.claim_world(tb_state())
        self.assertEqual(list(cw.roles), TB_CLAIMS)

    def test_a_seat_with_no_claim_is_a_townsfolk_nobody_claims(self):
        claims = dict(enumerate(TB_CLAIMS))
        del claims[7]
        state = GameState(n_players=8, script=TB, claims=claims, infos=[],
                          days_done=set())
        cw = S.claim_world(state)
        self.assertEqual(cw.roles[7], "Librarian")   # first not claimed

    def test_what_fits_and_what_does_not(self):
        st = tb_state()
        self.assertTrue(S.fits_the_claims(Empath(night=1, player=1, count=0), st))
        self.assertFalse(S.fits_the_claims(Empath(night=1, player=1, count=1), st))
        self.assertTrue(S.fits_the_claims(Chef(night=1, player=0, count=0), st))
        self.assertFalse(S.fits_the_claims(Chef(night=1, player=0, count=1), st))
        self.assertTrue(S.fits_the_claims(
            Washerwoman(night=1, player=5, a=0, b=4, role="Chef"), st))
        self.assertFalse(S.fits_the_claims(
            Washerwoman(night=1, player=5, a=1, b=4, role="Chef"), st))
        # Nobody claims a Minion, so an Investigator never fits — the real
        # one no more than a bluffer.
        self.assertFalse(S.fits_the_claims(
            Investigator(night=1, player=3, a=6, b=7, role="Poisoner"), st))
        # Wherever the red herring is, a yes and a no can both be true.
        self.assertTrue(S.fits_the_claims(
            FortuneTeller(night=1, player=2, a=3, b=5, yes=True), st))
        self.assertTrue(S.fits_the_claims(
            FortuneTeller(night=1, player=2, a=3, b=5, yes=False), st))

    def test_the_undertaker_names_the_claim(self):
        st = tb_state()
        st.deaths = {6: ("D1",)}
        st.executions = {1: 6}
        self.assertTrue(S.fits_the_claims(
            Undertaker(night=2, player=4, target=6, role="Monk"), st))
        self.assertFalse(S.fits_the_claims(
            Undertaker(night=2, player=4, target=6, role="Imp"), st))

    def test_the_prices(self):
        st = tb_state()
        fit = Empath(night=1, player=1, count=0)
        misfit = Empath(night=1, player=1, count=1)
        self.assertAlmostEqual(S.invention_cost(fit, st), 0.7)
        self.assertAlmostEqual(S.invention_cost(misfit, st), 0.2)
        # A choice says nothing about the world: free (B Weg 1).
        self.assertEqual(S.invention_cost(
            SailorChoice(night=1, player=1, target=2), st), 1.0)
        # Trust still divides, as before.
        trusted = Empath(night=1, player=1, count=0, trust=1)
        self.assertAlmostEqual(S.invention_cost(trusted, st), 0.35)
        # Without a board, the old reading of "made up": the higher price.
        self.assertAlmostEqual(S.invention_cost(misfit), 0.2)

    def test_a_row_that_says_a_character_is_in_play_is_no_choice(self):
        from botc.info import BecameInfo, HarpyMadness, SlayerShot
        st = tb_state()
        self.assertLess(S.invention_cost(
            HarpyMadness(night=1, player=1, second=2), st), 1.0)
        self.assertLess(S.invention_cost(
            BecameInfo(night=2, player=1, role="Farmer"), st), 1.0)
        # A shot that did nothing is the claimed Slayer's own choice.
        self.assertEqual(S.invention_cost(
            SlayerShot(night=2, player=1, target=3, died=False), st), 1.0)

    def test_both_languages_name_the_same_three(self):
        script = ("import * as I from './js/info.mjs';"
                  "import {TOLD_NOT_CHOSEN} from './js/scoring.mjs';"
                  "const out = [];"
                  "for (const n of TOLD_NOT_CHOSEN) {"
                  "  if (!I[n] || !I[n].isAChoice) throw new Error(n);"
                  "  out.push(Object.create(I[n].prototype).type); }"
                  "console.log(JSON.stringify(out));")
        got = subprocess.run(["node", "--input-type=module", "-e", script],
                             cwd=ROOT, capture_output=True, text=True,
                             timeout=120)
        self.assertEqual(got.returncode, 0, got.stderr)
        # The board names BecameInfo "Became"; the corpus writer's table
        # says how.
        from make_fixtures import _KIND
        self.assertEqual(sorted(json.loads(got.stdout)),
                         sorted(_KIND.get(n, n) for n in S.TOLD_NOT_CHOSEN))

    def test_a_new_claim_builds_a_new_world(self):
        st = tb_state()
        row = Empath(night=1, player=1, count=1)
        self.assertFalse(S.fits_the_claims(row, st))
        st.claims[0] = "Recluse"      # who may register as evil beside her
        self.assertEqual(S.claim_world(st).roles[0], "Recluse")


def tb_case(infos):
    return {"n_players": 8,
            "players": [{"claim": c, "events": []} for c in TB_CLAIMS],
            "infos": infos, "days_done": [1],
            "script": {"name": "Trouble Brewing",
                       "characters": [k.lower() for k in TB.keys]}}


def bmr_case():
    claims = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
              "Innkeeper", "Gambler", "Courtier", "Fool"]
    return {"n_players": 8,
            "players": [{"claim": c, "events": []} for c in claims],
            "infos": [
                {"type": "SailorChoice", "night": 1, "player": 1, "target": 5},
                {"type": "SailorChoice", "night": 2, "player": 1, "target": 6},
                {"type": "ChambermaidInfo", "night": 1, "player": 2,
                 "a": 0, "b": 3, "count": 1},
                {"type": "ExorcistChoice", "night": 2, "player": 3,
                 "target": 4},
                {"type": "InnkeeperChoice", "night": 1, "player": 4,
                 "a": 0, "b": 1},
            ],
            "days_done": [1],
            "script": {"name": "Bad Moon Rising",
                       "characters": [k.lower() for k in BMR.keys]}}


class PythonAndJavaScriptAgree(SolverTest):

    def both(self, case):
        import app
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
        return py

    def test_trouble_brewing_with_rows_that_fit_and_rows_that_do_not(self):
        py = self.both(tb_case([
            {"type": "Chef", "night": 1, "player": 0, "count": 0},
            {"type": "Empath", "night": 1, "player": 1, "count": 1},
            {"type": "Empath", "night": 2, "player": 1, "count": 0},
            {"type": "FortuneTeller", "night": 1, "player": 2,
             "a": 3, "b": 5, "yes": True},
            {"type": "Investigator", "night": 1, "player": 3,
             "a": 6, "b": 7, "role": "Poisoner"},
            {"type": "Washerwoman", "night": 1, "player": 5,
             "a": 0, "b": 4, "role": "Chef"},
        ]))
        self.assertGreater(py["valid"], 0)

    def test_bad_moon_rising_with_choices(self):
        py = self.both(bmr_case())
        self.assertGreater(py["valid"], 0)


if __name__ == "__main__":
    unittest.main()
