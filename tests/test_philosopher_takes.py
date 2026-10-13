"""A Philosopher has the ability it took — step 1 (13.10.2026).

Open item 56: a Philosopher is that character, ability-wise (table ruling),
but solver, simulator and night-walk gave it only the abilities that read
and a few that act. Step 1 is the four on Sects & Violets that act, all
on dying: the Sweetheart, the Barber, the Klutz and the Mutant. The table's
answers, way 1 for all of them:

  A  a Philosopher that took the Sweetheart leaves somebody drunk when it
     dies, from then on
  B  a real Sweetheart drunk by that Philosopher when it dies leaves nobody
     drunk; dying after the Philosopher, it works again
  C  a Philosopher that wrote down taking the Barber counts as a Barber
     claim, and its death lets the Demon swap
  D  a real Barber drunk by that Philosopher when it dies swaps nothing
  E  a Philosopher that took the Klutz points on dying (the solver already
     knew; the simulator now plays it)
  F  a Philosopher that took the Mutant changes nothing for the solver
  G  a real Mutant drunk by that Philosopher still hides behind a
     Townsfolk: it does not know it is drunk
  H  the simulator plays all of it
"""

import json
import pathlib
import random
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SV = scripts.SECTS_AND_VIOLETS


def state(roles, rows=(), deaths=None, days=(1, 2), claims=None):
    return GameState(n_players=len(roles), script=SV,
                     claims=dict(claims if claims is not None
                                 else enumerate(roles)),
                     infos=list(rows), deaths=deaths or {},
                     days_done=set(days))


def cost(roles, rows=(), **kw):
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)),
                              state(roles, rows, **kw))


def stories(roles, rows=(), **kw):
    return S.possible_timelines(World(tuple(roles), (None,) * len(roles)),
                                state(roles, rows, **kw))


#         0              1           2            3          4
PHIL = ["Philosopher", "Oracle", "Clockmaker", "Dreamer", "Mutant",
        "Witch", "FangGu"]                                    # 5, 6
REAL = ["Philosopher", "Oracle", "Sweetheart", "Dreamer", "Mutant",
        "Witch", "FangGu"]


def took(role):
    return I.PhilosopherChoice(1, 0, role=role)


class TheSweetheart(SolverTest):

    def test_a_philosopher_that_took_it_leaves_somebody_drunk(self):
        # A: the Oracle counts a dead good Philosopher as evil on night 3.
        wrong = I.OracleInfo(3, 1, count=1)
        self.assertIsNotNone(cost(PHIL, [took("Sweetheart"), wrong],
                                  deaths={0: ("N2",)}))
        self.assertIsNone(cost(PHIL, [took("Dreamer"), wrong],
                               deaths={0: ("N2",)}))

    def test_the_real_one_drunk_by_it_leaves_nobody_drunk(self):
        # B: the Sweetheart dies while the Philosopher lives.
        self.assertIsNone(cost(REAL, [took("Sweetheart"),
                                      I.OracleInfo(3, 1, count=1)],
                               deaths={2: ("N2",)}))

    def test_after_the_philosopher_it_works_again(self):
        self.assertIsNotNone(cost(REAL, [took("Sweetheart"),
                                         I.OracleInfo(4, 1, count=2)],
                                  deaths={0: ("N2",), 2: ("N3",)},
                                  days=(1, 2, 3)))


class TheBarber(SolverTest):

    def test_a_philosopher_that_took_it_lets_the_demon_swap(self):
        # C: its row is as good as a claim.
        swaps = stories(PHIL, [took("Barber")], deaths={0: ("E1",)})
        self.assertGreater(len(swaps), 1)
        self.assertEqual(len(stories(PHIL, [took("Dreamer")],
                                     deaths={0: ("E1",)})), 1)

    def test_its_row_counts_as_a_barber_claim(self):
        got = S.barber_claimants(state(PHIL, [took("Barber")]))
        self.assertEqual(got, {0})

    def test_the_real_one_drunk_by_it_swaps_nothing(self):
        # D.
        roles = ["Philosopher", "Oracle", "Barber", "Dreamer", "Mutant",
                 "Witch", "FangGu"]
        self.assertEqual(len(stories(roles, [took("Barber")],
                                     deaths={2: ("E1",)})), 1)
        self.assertGreater(len(stories(roles, [took("Dreamer")],
                                       deaths={2: ("E1",)})), 1)


class TheKlutz(SolverTest):

    def test_its_pick_counts_as_the_klutzs(self):
        # E: already so in the solver; kept here so it stays so.
        self.assertIsNone(cost(PHIL, [took("Klutz"),
                                      I.KlutzChoice(2, 0, target=6)],
                               deaths={0: ("N2",)}))
        self.assertIsNotNone(cost(PHIL, [took("Klutz"),
                                         I.KlutzChoice(2, 0, target=1)],
                                  deaths={0: ("N2",)}))


class TheMutant(SolverTest):

    def test_a_drunk_mutant_still_hides(self):
        # G: it does not know it is drunk, so it claims a Townsfolk.
        from botc.roles import must_hide
        self.assertTrue(must_hide("Mutant"))


class TheSimulatorPlaysThem(SolverTest):
    """H."""

    def games(self, how_many=1500, nights=4):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=nights,
                                      script=SV)

    def test_a_philosopher_klutz_points_on_dying_at_night(self):
        pointed = 0
        for seed, (deal, heard) in self.games():
            for seat, role in deal.philosophies.items():
                if role != "Klutz" or not str(deal.deaths.get(seat, "")
                                              ).startswith("N"):
                    continue
                rows = [r for r in heard if isinstance(r, I.KlutzChoice)
                        and r.player == seat]
                with self.subTest(seed=seed):
                    self.assertEqual(len(rows), 1)
                pointed += 1
        self.assertGreater(pointed, 5)

    def test_a_philosopher_sweetheart_and_barber_act_on_dying(self):
        import simulate
        drunk = swapped = 0
        for seed, (deal, _heard) in self.games():
            for seat, role in deal.philosophies.items():
                gone = deal.deaths.get(seat)
                if not gone:
                    continue
                if role == "Sweetheart":
                    night = int(gone[1:]) + (0 if gone[0] == "N" else 1)
                    if night <= deal.nights_played:
                        later = simulate.droisoned_at(deal, night)
                        drunk += (seat + 1) % deal.n in later
                if role == "Barber":
                    swapped += bool(getattr(deal, "barber_swaps", {}))
        self.assertGreater(drunk, 10)
        self.assertGreater(swapped, 5)

    def test_the_true_world_is_kept(self):
        import claims as C
        import simulate
        lost = []
        for seed in range(600):
            n = [7, 8, 9, 10, 11][seed % 5]
            rng = random.Random(seed)
            deal, heard = simulate.play(n, rng, nights=4, script=SV)
            if not set(deal.philosophies.values()) & {
                    "Sweetheart", "Barber", "Klutz", "Mutant"}:
                continue
            cl, wk, _ = C.claims_for(deal, rng, script=SV)
            st = GameState(n_players=n, script=SV, claims=cl, wakes=wk,
                           infos=list(heard), votes=dict(deal.votes),
                           nominations=dict(deal.nominations),
                           **deal.record())
            if S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        # Seed 57 is one of the Sects & Violets games lost before this
        # step, for a reason of its own.
        self.assertLessEqual(set(lost), {57, 226, 572})


class BothLanguagesAgree(SolverTest):

    def test_on_the_boards_of_this_step(self):
        import app
        cases = []
        for rows, deaths in (
                ([{"type": "PhilosopherChoice", "night": 1, "player": 0,
                   "role": "Sweetheart"},
                  {"type": "OracleInfo", "night": 3, "player": 1,
                   "count": 1}], {0: ["N2"]}),
                ([{"type": "PhilosopherChoice", "night": 1, "player": 0,
                   "role": "Barber"}], {0: ["E1"]})):
            players = [{"claim": c, "events": deaths.get(i, [])}
                       for i, c in enumerate(["Philosopher", "Oracle",
                                              "Clockmaker", "Dreamer",
                                              "Savant", "Artist", "Juggler"])]
            payload = {"n_players": 7, "players": players, "infos": rows,
                       "script": {"name": SV.name,
                                  "characters": [c.lower() for c in SV.keys]},
                       "days_done": [1, 2]}
            cases.append(payload)
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); return r.error || r.valid; })));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=300)
        self.assertEqual(got.returncode, 0, got.stderr)
        js = json.loads(got.stdout)
        py = [app.run_solve(p).get("error") or app.run_solve(p)["valid"]
              for p in cases]
        self.assertEqual(js, py)


if __name__ == "__main__":
    unittest.main()
