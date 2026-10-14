"""Stelle 59 (14.10.2026): the simulator plays the Slayer and the Virgin.

Neither was played at all, real or taken by a Philosopher, so no gate
asked the solver about a shot or a Virgin's nomination. Now a Slayer
shoots now and then before the nominations, and a Virgin's first
nomination executes a Townsfolk nominator on the spot.

Found on the way and fixed: under a Vortox both rows were read as
information and inverted, and a Philosopher that took the Professor was
held to wake every night when it may have spent it unseen.
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
from botc import info as I, scripts, waking       # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
TB = scripts.TROUBLE_BREWING

IDS = ["slayer", "virgin", "chef", "empath", "washerwoman", "investigator",
       "monk", "philosopher", "professor", "chambermaid", "drunk", "saint",
       "recluse", "poisoner", "scarletwoman", "spy", "vortox", "imp"]
OPEN = scripts.from_ids("In the open", IDS)
#      0       1         2         3           4              5         6
V7 = ["Chef", "Empath", "Slayer", "Virgin", "Washerwoman", "ScarletWoman",
      "Vortox"]                       # nothing to droison either of them


def cost(roles, rows=(), **kw):
    kw.setdefault("days_done", {1})
    # Somebody executed, or a Vortox would have won on day one.
    kw.setdefault("deaths", {4: ("E1",)})
    st = GameState(n_players=len(roles), script=OPEN,
                   claims=dict(enumerate(roles)), infos=list(rows), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)), st)


def games(script, how_many=300, nights=4, must=None):
    import play_games
    import simulate
    for seed in range(how_many):
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        sc = script or play_games.an_awkward_script(rng, must_have=must)
        deal, heard = simulate.play(n, rng, nights=nights, script=sc)
        yield seed, sc, rng, deal, heard


class AVortoxHasNothingToFalsify(SolverTest):

    def test_a_missed_shot_stays_a_miss(self):
        self.assertIsNotNone(cost(V7, [I.SlayerShot(1, 2, target=0)]))
        self.assertIsNone(cost(V7, [I.SlayerShot(1, 2, target=6)]))

    def test_a_quiet_nomination_stays_quiet(self):
        rows = [I.VirginNomination(1, 3, nominator=5, triggered=False)]
        self.assertIsNotNone(cost(V7, rows))
        rows = [I.VirginNomination(1, 3, nominator=0, triggered=False)]
        self.assertIsNone(cost(V7, rows))

    def test_neither_is_information(self):
        st = GameState(n_players=7, script=OPEN, claims=dict(enumerate(V7)))
        self.assertFalse(I.SlayerShot(1, 2).is_information(st))
        self.assertFalse(I.VirginNomination(1, 3).is_information(st))


class APhilosopherWakesLikeWhatItTook(SolverTest):

    def test_its_professor_may_have_been_spent_unseen(self):
        roles = ["Chef", "Empath", "Philosopher", "Chambermaid",
                 "Washerwoman", "Poisoner", "Imp"]
        st = GameState(n_players=7, script=OPEN,
                       claims=dict(enumerate(roles)),
                       infos=[I.PhilosopherChoice(1, 2, role="Professor")],
                       days_done={1, 2})
        world = World(tuple(roles), (None,) * 7)
        self.assertTrue(waking.uncertain(world, st, 2, 3))
        self.assertFalse(waking.uncertain(world, st, 2, 1))


def _payloads():
    def pay(rows, events=None, days=(1,)):
        # Somebody executed, or a Vortox would have won on day one.
        events = events or {4: ["X1"]}
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(V7)]
        return {"n_players": 7, "players": players, "infos": rows,
                "script": {"name": OPEN.name, "characters": IDS},
                "days_done": list(days)}
    return [
        pay([{"type": "SlayerShot", "night": 1, "player": 2, "target": 0,
              "died": False}]),
        pay([{"type": "SlayerShot", "night": 1, "player": 2, "target": 6,
              "died": False}]),
        pay([{"type": "VirginNomination", "night": 1, "player": 3,
              "nominator": 5, "triggered": False}]),
        pay([{"type": "VirginNomination", "night": 1, "player": 3,
              "nominator": 0, "triggered": True}], {0: ["X1"]}),
        pay([{"type": "VirginNomination", "night": 1, "player": 3,
              "nominator": 0, "triggered": False}]),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_shots_and_nominations(self):
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
        py = [app.run_solve(p).get("error") or app.run_solve(p)["valid"]
              for p in cases]
        self.assertEqual(json.loads(got.stdout), py)
        self.assertTrue(py[0] and py[2] and py[3], py)
        self.assertEqual([py[1], py[4]], [0, 0])


class TheSimulatorPlaysThem(SolverTest):

    def test_on_trouble_brewing(self):
        shots = landed = noms = triggered = ended = 0
        for _seed, _sc, _rng, deal, heard in games(TB):
            for row in heard:
                if isinstance(row, I.SlayerShot):
                    shots += 1
                    landed += row.died
                elif isinstance(row, I.VirginNomination):
                    noms += 1
                    triggered += row.triggered
            ended += deal.ended_why == "slayer"
        for got in (shots, landed, noms, triggered, ended):
            self.assertGreater(got, 5)

    def test_a_philosopher_shoots_and_is_nominated(self):
        took = {"SlayerShot": 0, "VirginNomination": 0}
        for _seed, _sc, _rng, deal, heard in games(
                None, 400, must=("Philosopher", "Slayer", "Virgin")):
            for row in heard:
                name = type(row).__name__
                if name in took and row.player in deal.philosophies:
                    took[name] += 1
        self.assertTrue(all(took.values()), took)

    def test_who_acted_in_the_open_claims_it(self):
        import claims as C
        for seed, sc, rng, deal, heard in games(TB):
            cl, _wk, _notes = C.claims_for(deal, rng, script=sc)
            for row in heard:
                shown = (isinstance(row, I.SlayerShot)
                         or (isinstance(row, I.VirginNomination)
                             and row.triggered))
                if shown and not deal.side_at(row.player, "N1") == "evil":
                    with self.subTest(seed=seed):
                        self.assertEqual(cl[row.player],
                                         deal.apparent(row.player))

    def test_the_true_world_is_kept(self):
        import claims as C
        lost = []
        for seed, sc, rng, deal, heard in games(TB):
            if not any(isinstance(r, (I.SlayerShot, I.VirginNomination))
                       for r in heard):
                continue
            cl, wk, _ = C.claims_for(deal, rng, script=sc)
            st = GameState(n_players=deal.n, script=sc, claims=cl, wakes=wk,
                           infos=list(heard), votes=dict(deal.votes),
                           nominations=dict(deal.nominations),
                           **deal.record())
            if S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        self.assertEqual(lost, [])


if __name__ == "__main__":
    unittest.main()
