"""The Al-Hadikhia (21.10.2026), the first of the big characters in the
order Patrick agreed on 20.10.2026.

"Each night*, you may choose 3 players (all players learn who): each
silently chooses to live or die, but if all live, all die."

Patrick's answers (claude/al-hadikhia-lesarten.md):

  A  Weg 1: a row names the three, because the names are public.
  B  A player kept from dying tonight counts as choosing life whatever
     it chose; if all three lived, the others die and it stays.
  C  Weg 1: drunk or poisoned, it chooses and the names are announced,
     and nothing happens.
  D  Weg 2: the same player may be chosen more than once.
  E  In the simulator: evil chooses life; a good player whose ability is
     spent, or an Outsider that hurts the town while it lives, mostly
     death; anybody else mostly life.
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
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["alhadikhia", "poisoner", "spy", "scarletwoman", "chef", "empath",
       "monk", "washerwoman", "investigator", "soldier", "recluse", "saint",
       "butler", "professor", "imp"]
AH = scripts.from_ids("Al-Hadikhia", IDS)
#      0       1         2         3              4          5        6
R7 = ["Chef", "Empath", "Soldier", "Washerwoman", "Investigator", "Spy",
      "AlHadikhia"]


def chose(night, a, b, c):
    return I.AlHadikhiaChose(night, 0, a=a, b=b, c=c)


def cost(rows, deaths=None, resurrections=None, days=(1, 2), quiet=()):
    st = GameState(n_players=7, script=AH, claims=dict(enumerate(R7)),
                   infos=list(rows), deaths=deaths or {},
                   resurrections=resurrections or {}, days_done=set(days),
                   quiet_nights=set(quiet))
    return S.explanation_cost(World(tuple(R7), (None,) * 7), st)


class TheThreeChoose(SolverTest):

    def test_one_of_them_dies(self):
        self.assertIsNotNone(cost([chose(2, 0, 1, 3)], {1: ("N2",)}))

    def test_all_three_die(self):
        self.assertIsNotNone(cost([chose(2, 0, 1, 3)],
                                  {0: ("N2",), 1: ("N2",), 3: ("N2",)}))

    def test_nobody_else_dies(self):
        self.assertIsNone(cost([chose(2, 0, 1, 3)], {4: ("N2",)}))

    def test_nobody_dies_needs_a_reason(self):
        # No poisoner reaches it, nobody is protected, nobody was dead —
        # on a night the table marked as quiet.
        self.assertIsNone(cost([chose(2, 0, 1, 3)], quiet=(2,)))

    def test_a_soldier_among_them_keeps_the_night_quiet(self):
        # B: the Soldier counts as choosing life and stays; read
        # permissively, one shield among the three is enough.
        self.assertIsNotNone(cost([chose(2, 0, 2, 3)], quiet=(2,)))

    def test_a_corpse_that_chose_death(self):
        deaths = {1: ("E1",)}
        self.assertIsNotNone(cost([chose(2, 0, 1, 3)], deaths, quiet=(2,)))

    def test_a_dead_one_comes_back(self):
        deaths = {1: ("E1",)}
        back = {1: ("N2",)}
        self.assertIsNotNone(cost([chose(2, 0, 1, 3)], deaths, back))
        self.assertIsNone(cost([chose(2, 0, 4, 3)], deaths, back))

    def test_one_the_gambler_took_first(self):
        # The Gambler guessed wrong and died before its turn; a corpse by
        # then, it chose death, and nobody else need die (seed 1932).
        ids = IDS + ["gambler"]
        r = ["Chef", "Gambler"] + R7[2:]
        st = GameState(n_players=7, script=scripts.from_ids("G", ids),
                       claims=dict(enumerate(r)),
                       infos=[I.GamblerGuess(2, 1, target=0, role="Empath"),
                              chose(2, 0, 1, 3)],
                       deaths={1: ("N2",)}, days_done={1, 2})
        self.assertIsNotNone(S.explanation_cost(
            World(tuple(r), (None,) * 7), st))

    def test_the_same_player_twice(self):
        self.assertIsNotNone(cost([chose(2, 1, 1, 3)], {1: ("N2",)}))

    def test_without_a_row_nobody_dies_of_it(self):
        self.assertIsNone(cost([], {1: ("N2",)}))
        self.assertIsNotNone(cost([]))

    def test_it_kills_its_own_way_and_not_on_the_first_night(self):
        self.assertIn("AlHadikhia", S.KILLS_ITS_OWN_WAY)
        self.assertEqual(CHARACTERS["AlHadikhia"].first_night, 0)
        self.assertFalse(chose(1, 0, 1, 3).holds(
            World(tuple(R7), (None,) * 7),
            GameState(n_players=7, script=AH, claims={}), None))


# A Monk the town executed, chosen on night two, chooses life: it is back
# at the Al-Hadikhia's turn, after its own, so it slept through it.
CM_IDS = ["alhadikhia", "spy", "chambermaid", "monk", "chef", "empath",
          "washerwoman", "imp", "poisoner"]
CM = scripts.from_ids("Al-Hadikhia, Kammerzofe", CM_IDS)
#       0              1       2       3         4              5
R_CM = ["Chambermaid", "Monk", "Chef", "Empath", "Washerwoman", "Spy",
        "AlHadikhia"]


def chambermaid(count):
    st = GameState(n_players=7, script=CM, claims=dict(enumerate(R_CM)),
                   infos=[chose(2, 1, 2, 3),
                          I.ChambermaidInfo(2, 0, a=1, b=6, count=count)],
                   deaths={1: ("E1",), 2: ("N2",)},
                   resurrections={1: ("N2",)}, days_done={1, 2})
    return S.explanation_cost(World(tuple(R_CM), (None,) * 7), st)


class OneItBringsBack(SolverTest):

    def test_wakes_only_after_its_turn(self):
        self.assertIsNotNone(chambermaid(1))
        self.assertIsNone(chambermaid(2))


def games(how_many=300, nights=4, must=("AlHadikhia",)):
    import play_games
    import simulate
    for seed in range(how_many):
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        sc = play_games.an_awkward_script(rng, must_have=must)
        deal, heard = simulate.play(n, rng, nights=nights, script=sc)
        if "AlHadikhia" in deal.roles:
            yield seed, sc, rng, deal, heard


class TheSimulatorPlaysIt(SolverTest):

    def test_rows_deaths_and_returns(self):
        rows = back = twice = 0
        for _seed, _sc, _rng, deal, heard in games():
            for row in heard:
                if not isinstance(row, I.AlHadikhiaChose):
                    continue
                rows += 1
                picks = row.chosen()
                twice += len(set(picks)) < len(picks)
                died = deal.died_on(f"N{row.night}")
                self.assertTrue(died <= set(picks) | died)
            back += sum(1 for _w, _at, by in deal.resurrections
                        if by == "AlHadikhia")
        self.assertGreater(rows, 50)
        self.assertGreater(back, 0)
        self.assertGreater(twice, 0)

    def test_the_true_world_is_kept(self):
        import claims as C
        lost = []
        for seed, sc, rng, deal, heard in games():
            cl, wk, _ = C.claims_for(deal, rng, script=sc)
            st = GameState(n_players=deal.n, script=sc, claims=cl, wakes=wk,
                           infos=list(heard), votes=dict(deal.votes),
                           nominations=dict(deal.nominations),
                           **deal.record())
            # Not a Barber's swap: that class is Stelle 4.
            if S.explanation_cost(deal.world(), st) is None \
                    and "Barber" not in deal.roles:
                lost.append(seed)
        self.assertEqual(lost, [])


def _payloads():
    def pay(rows, events, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(R7)]
        return {"n_players": 7, "players": players, "infos": rows,
                "script": {"name": AH.name, "characters": IDS},
                "days_done": list(days)}

    def row(night, a, b, c):
        return {"type": "AlHadikhiaChose", "night": night, "player": 0,
                "a": a, "b": b, "c": c}
    return [
        pay([row(2, 0, 1, 3)], {1: ["N2"]}),
        pay([row(2, 0, 1, 3)], {0: ["N2"], 1: ["N2"], 3: ["N2"]}),
        pay([row(2, 0, 2, 3)], {}),
        pay([row(2, 1, 1, 3)], {1: ["N2"]}),
        pay([row(2, 0, 1, 3)], {1: ["X1", "R2"]}),
        {"n_players": 7, "days_done": [1, 2],
         "script": {"name": CM.name, "characters": CM_IDS},
         "infos": [row(2, 1, 2, 3),
                   {"type": "ChambermaidInfo", "night": 2, "player": 0,
                    "a": 1, "b": 6, "count": 1}],
         "players": [{"claim": c, "events": {1: ["X1", "R2"],
                                             2: ["N2"]}.get(i, [])}
                     for i, c in enumerate(R_CM)]},
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_an_al_hadikhia(self):
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
