"""Stelle 58 (14.10.2026): whoever is handed a character says so.

Patrick's answers to A to F:

  A  A Farmer's heir always says it, as a "Claim changed" row (now the
     Farmer, before X), and claims the Farmer from then on.
  B  The search reads the row: a seat with one is searched as its first
     "was", not as what it claims now — for every such row.
  C  "Became the Farmer" is a Farmer that died that night, or a Pit-Hag
     whose choice nobody wrote down (free), besides the ways already there.
  D  An heir killed the same night hands it on at once: the next day two
     may say they became the Farmer, one of them alive.
  E  A Spy made the Farmer may say so or keep its bluff.
  F  A good player the Pit-Hag changes says so the same way.
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
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import Change, World             # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

IDS = ["farmer", "tealady", "chef", "empath", "monk", "washerwoman",
       "investigator", "pithag", "poisoner", "spy", "imp", "drunk",
       "recluse", "saint", "shabaloth"]
HEIRS = scripts.from_ids("Farmer heirs", IDS)
#      0       1         2         3       4              5         6
F7 = ["Chef", "Empath", "Farmer", "Monk", "Washerwoman", "PitHag", "Imp"]


def board(claims, rows=(), roles=F7, **kw):
    kw.setdefault("days_done", {1, 2})
    st = GameState(n_players=len(roles), script=HEIRS,
                   claims=dict(enumerate(claims)), infos=list(rows), **kw)
    return World(tuple(roles), (None,) * len(roles)), st


def became(night, seat, role, was):
    return I.BecameInfo(night, seat, role=role, was=was)


class TheSearchReadsTheRow(SolverTest):
    """B: the seat is searched as what it said before."""

    def test_the_heir_is_searched_as_what_it_was(self):
        claims = list(F7)
        claims[0] = "Farmer"
        _w, st = board(claims, [became(2, 0, "Farmer", "Chef")])
        self.assertEqual(st.dealt_claims()[0], "Chef")
        self.assertEqual(st.claims[0], "Farmer")
        _w, bare = board(claims)
        self.assertEqual(bare.dealt_claims()[0], "Farmer")

    def test_the_first_was_of_a_chain(self):
        claims = list(F7)
        claims[0] = "Farmer"
        rows = [became(3, 0, "Farmer", "TeaLady"),
                became(2, 0, "TeaLady", "Chef")]
        _w, st = board(claims, rows)
        self.assertEqual(st.dealt_claims()[0], "Chef")

    def test_a_seat_without_a_claim_stays_without(self):
        claims = dict(enumerate(F7))
        del claims[0]
        st = GameState(n_players=7, script=HEIRS, claims=claims,
                       infos=[became(2, 0, "Farmer", "Chef")])
        self.assertNotIn(0, st.dealt_claims())

    def test_the_heir_is_not_lying(self):
        claims = list(F7)
        claims[0] = "Farmer"
        world, st = board(claims, [became(2, 0, "Farmer", "Chef")],
                          deaths={2: ("N2",)})
        self.assertFalse(S.is_lying(world, st, 0))
        world, bare = board(claims, deaths={2: ("N2",)})
        self.assertTrue(S.is_lying(world, bare, 0))

    def test_the_true_world_is_found(self):
        claims = list(F7)
        claims[0] = "Farmer"
        world, st = board(claims, [became(2, 0, "Farmer", "Chef")],
                          deaths={2: ("N2",)})
        _all, valid = S.solve(st)
        self.assertIn(world.roles, [w.roles for w in valid])


class WhereTheFarmerCameFrom(SolverTest):
    """C and D."""

    def test_an_heir_killed_the_same_night_hands_it_on(self):
        world, st = board(F7, [became(2, 0, "Farmer", "Chef"),
                               became(2, 1, "Farmer", "Empath")],
                          deaths={2: ("N2",), 0: ("N2",)})
        stories = [c for c, _w in S.a_farmer_hands_it_on(world, st)]
        self.assertIn((Change("D2", 0, "Farmer", None),
                       Change("D2", 1, "Farmer", None)), stories)

    def test_an_unrecorded_pit_hag_may_have_made_it(self):
        # A Tea Lady nobody holds: the Pit-Hag, whose row is missing.
        world, st = board(F7, [became(2, 0, "TeaLady", "Chef")])
        stories = [c for c, _w in S.a_pit_hag_nobody_wrote_down(world, st)]
        self.assertIn((Change("N2", 0, "TeaLady", "good"),), stories)

    def test_not_a_character_in_play(self):
        # The Farmer that died that night is still in play: it was the
        # Farmer, not the Pit-Hag.
        world, st = board(F7, [became(2, 0, "Farmer", "Chef")],
                          deaths={2: ("N2",)})
        self.assertEqual(S.a_pit_hag_nobody_wrote_down(world, st),
                         [((), 1.0)])

    def test_not_without_a_living_pit_hag(self):
        world, st = board(F7, [became(2, 0, "TeaLady", "Chef")],
                          deaths={5: ("D1",)})
        self.assertEqual(S.a_pit_hag_nobody_wrote_down(world, st),
                         [((), 1.0)])

    def test_not_on_the_first_night(self):
        world, st = board(F7, [became(1, 0, "TeaLady", "Chef")],
                          days_done={1})
        self.assertEqual(S.a_pit_hag_nobody_wrote_down(world, st),
                         [((), 1.0)])


def _payloads():
    def pay(claims, rows, events, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players, "infos": rows,
                "script": {"name": HEIRS.name, "characters": IDS},
                "days_done": list(days)}

    def row(night, seat, role, was):
        return {"type": "Became", "night": night, "player": seat,
                "role": role, "was": was}
    heir = list(F7)
    heir[0] = "Farmer"
    two = list(heir)
    two[1] = "Farmer"
    two[6] = "Shabaloth"                 # two bodies on one night
    made = list(F7)
    made[0] = "TeaLady"
    chef = {"type": "Chef", "night": 1, "player": 0, "count": 1}
    wrong = {"type": "Chef", "night": 1, "player": 0, "count": 0}
    return [
        pay(heir, [row(2, 0, "Farmer", "Chef")], {2: ["N2"]}),
        pay(heir, [chef, row(2, 0, "Farmer", "Chef")], {2: ["N2"]}),
        pay(heir, [wrong, row(2, 0, "Farmer", "Chef")], {2: ["N2"]}),
        pay(heir, [chef], {2: ["N2"]}),
        pay(two, [row(2, 0, "Farmer", "Chef"), row(2, 1, "Farmer", "Empath")],
            {2: ["N2"], 0: ["N2"]}),
        pay(made, [row(2, 0, "TeaLady", "Chef")], {}),
        pay(made, [chef, row(2, 0, "TeaLady", "Chef")], {5: ["X1"]}),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_the_heirs(self):
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
        self.assertTrue(all(isinstance(v, int) for v in py), py)
        # With the row the Chef's reading is its own; without one, or
        # with a wrong one, nothing fits.
        self.assertEqual(py, [1, 1, 0, 0, 1, 1, 1])

    def test_the_page_takes_the_row_from_a_seat_killed_that_night(self):
        import app
        p = _payloads()[4]
        self.assertNotIn("error", app.run_solve(p))


class TheSimulatorSaysIt(SolverTest):
    """A, D, E, F in the simulator."""

    def games(self, must, how_many=300):
        import play_games
        import simulate
        for seed in range(how_many):
            rng = random.Random(seed)
            script = play_games.an_awkward_script(rng, must_have=must)
            deal, heard = simulate.play(7, rng, nights=4, script=script)
            yield seed, deal, heard

    def test_every_good_heir_says_it(self):
        heirs = told = chained = 0
        for _seed, deal, heard in self.games(("Farmer",)):
            rows = {(r.night, r.player) for r in heard
                    if isinstance(r, I.BecameInfo) and r.role == "Farmer"}
            for when, seat, what in deal.changes:
                if what != "Farmer" or deal.side_at(seat, when) != "good":
                    continue
                heirs += 1
                told += (int(when[1:]), seat) in rows
                chained += deal.deaths.get(seat) == f"N{when[1:]}"
        self.assertGreater(heirs, 10)
        self.assertEqual(told, heirs)
        self.assertGreater(chained, 0)

    def test_a_good_pit_hag_victim_says_it(self):
        victims = told = 0
        for _seed, deal, heard in self.games(("PitHag",)):
            rows = {(r.night, r.player) for r in heard
                    if isinstance(r, I.BecameInfo)}
            for row in heard:
                if not isinstance(row, I.PitHagChoice) or not row.role \
                        or deal.side_at(row.target, f"N{row.night}") != "good":
                    continue
                victims += 1
                told += (row.night, row.target) in rows
        self.assertGreater(victims, 5)
        self.assertEqual(told, victims)

    def test_one_row_a_night_for_a_seat(self):
        for seed, _deal, heard in self.games(("Farmer", "PitHag")):
            keys = [(r.night, r.player) for r in heard
                    if isinstance(r, I.BecameInfo)]
            with self.subTest(seed=seed):
                self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()
