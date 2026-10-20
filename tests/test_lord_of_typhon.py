"""The Lord of Typhon (19.10.2026), the first of the big characters.

"Each night*, choose a player: they die. [Evil characters are in a line,
you are in the middle. +1 Minion. -? to +? Outsiders]"

Patrick's answers (claude/lord-of-typhon-lesarten.md):

  A  Weg 2: anywhere in the line but at an end. And a Recluse may stand
     at any place in the line, registering as a Minion at setup.
  B  Weg 1: an evil Townsfolk of the Bounty Hunter's may be part of the
     line, need not.
  C  Weg 1: only the deal. A Lord of Typhon made later seats nobody.
  D  Weg 1, not always: its Minions mostly claim the good token they were
     handed before they turned.
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
from botc import scripts                          # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.roles import TEAM                       # noqa: E402
from botc.worlds import (World, _bags, in_a_line,  # noqa: E402
                         seated_legally)

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["lordoftyphon", "poisoner", "spy", "scarletwoman", "chef", "empath",
       "monk", "washerwoman", "investigator", "soldier", "recluse", "saint",
       "drunk", "butler", "bountyhunter", "pithag", "imp"]
TYPHON = scripts.from_ids("Typhon", IDS)

# (roles, seat of the Lord, in a line?)
LINES = [
    (["Chef", "Spy", "LordOfTyphon", "Poisoner", "Empath"], 2, True),
    # At an end.
    (["Chef", "Spy", "Poisoner", "LordOfTyphon", "Empath"], 3, False),
    # A gap in the line.
    (["Spy", "Chef", "LordOfTyphon", "Poisoner", "Empath"], 2, False),
    # Round the table's edge.
    (["Poisoner", "Chef", "Empath", "Spy", "LordOfTyphon"], 4, True),
    # A Recluse standing in, at the end or beside the Lord (A).
    (["Recluse", "LordOfTyphon", "Poisoner", "Empath", "Chef"], 1, True),
    (["Recluse", "Spy", "LordOfTyphon", "Poisoner", "Chef"], 2, True),
    # Anywhere but an end (A, Weg 2): four evil, the Lord second.
    (["Spy", "LordOfTyphon", "Poisoner", "ScarletWoman", "Chef", "Empath",
      "Monk"], 1, True),
    # A Townsfolk in the line only with a Bounty Hunter (B), and one.
    (["Spy", "Chef", "LordOfTyphon", "Poisoner", "Empath"], 2, False),
    (["Spy", "BountyHunter", "Chef", "LordOfTyphon", "Poisoner"], 3, True),
    (["Spy", "Chef", "Empath", "LordOfTyphon", "Poisoner",
      "BountyHunter"], 3, False),
]


class TheLine(SolverTest):

    def test_every_case(self):
        for roles, lord, want in LINES:
            with self.subTest(roles=roles):
                self.assertEqual(in_a_line(roles, lord), want)
                self.assertEqual(seated_legally(roles), want)

    def test_the_same_in_javascript(self):
        script = ("import {inALine} from './js/worlds.mjs';"
                  "const cs=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(cs.map(([r, l]) =>"
                  " inALine(r, l))));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps([[r, l] for r, l, _ in LINES])],
                             cwd=ROOT, capture_output=True, text=True,
                             timeout=120)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(json.loads(got.stdout), [w for _r, _l, w in LINES])


class TheBag(SolverTest):

    def test_one_minion_more_and_any_outsiders(self):
        bags = [counts for present, counts in _bags(9, TYPHON)
                if "LordOfTyphon" in present]
        self.assertTrue(bags)
        self.assertTrue(all(c["minion"] == 2 for c in bags))
        self.assertTrue({0, 1, 2, 3, 4} <= {c["outsider"] for c in bags})

    def test_it_kills_and_hands_nothing_on(self):
        self.assertNotIn("LordOfTyphon", S.STARPASSES)
        self.assertNotIn("LordOfTyphon", S.KILLS_ITS_OWN_WAY)
        self.assertEqual(CHARACTERS["LordOfTyphon"].first_night, 0)
        self.assertGreater(CHARACTERS["LordOfTyphon"].other_night, 0)


def games(how_many=200, nights=3, must=("LordOfTyphon",)):
    import play_games
    import simulate
    for seed in range(how_many):
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        sc = play_games.an_awkward_script(rng, must_have=must)
        deal, heard = simulate.play(n, rng, nights=nights, script=sc)
        if "LordOfTyphon" in deal.roles:
            yield seed, sc, rng, deal, heard


class TheSimulatorDealsIt(SolverTest):

    def test_in_a_line_with_one_minion_more(self):
        from botc.roles import SETUP
        seen = 0
        for seed, _sc, _rng, deal, _heard in games():
            seen += 1
            lord = deal.roles.index("LordOfTyphon")
            with self.subTest(seed=seed):
                self.assertTrue(in_a_line(deal.roles, lord))
                minions = sum(TEAM[r] == "minion" for r in deal.roles)
                self.assertEqual(minions, SETUP[deal.n][2] + 1)
        self.assertGreater(seen, 20)

    def test_its_minions_mostly_claim_their_first_token(self):
        import claims as C
        said = told = 0
        for _seed, sc, rng, deal, _heard in games():
            cl, _wk, _ = C.claims_for(deal, rng, script=sc)
            for seat, token in deal.typhon_tokens.items():
                told += 1
                said += cl.get(seat) == token
                self.assertNotIn(token, deal.roles)
        self.assertGreater(said, told // 2)
        self.assertLess(said, told)

    def test_the_true_world_is_kept(self):
        import claims as C
        lost = []
        for seed, sc, rng, deal, heard in games():
            cl, wk, _ = C.claims_for(deal, rng, script=sc)
            st = GameState(n_players=deal.n, script=sc, claims=cl, wakes=wk,
                           infos=list(heard), votes=dict(deal.votes),
                           nominations=dict(deal.nominations),
                           **deal.record())
            if S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        self.assertEqual(lost, [])


def _payloads():
    def pay(claims, events, days=(1,)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players, "infos": [],
                "script": {"name": TYPHON.name, "characters": IDS},
                "days_done": list(days)}
    seven = ["Chef", "Empath", "Monk", "Washerwoman", "Investigator",
             "Soldier", "Saint"]
    return [pay(seven, {}),
            pay(seven, {3: ["N2"]}, days=(1, 2)),
            pay(seven[:5] + ["Butler", "Recluse"], {0: ["X1"]})]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_a_lord_of_typhon(self):
        import app
        cases = _payloads()
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); return r.error || r.valid; })));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        py = []
        for p in cases:
            r = app.run_solve(p)
            py.append(r.get("error") or r["valid"])
        self.assertEqual(json.loads(got.stdout), py)
        self.assertTrue(all(isinstance(v, int) and v > 0 for v in py), py)


if __name__ == "__main__":
    unittest.main()
