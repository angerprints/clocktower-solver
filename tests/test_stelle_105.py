"""Stelle 105 (03.11.2026): who holds an ability at its turn.

Two games the gate found on 31.10.2026, and both were the simulator.

Seed 1439 of the Plague Doctor's line (Plague Doctor, Pit-Hag,
Mezepheles, Summoner): the Pit-Hag made the Cult Leader an Innkeeper at
280 in night 4. The Innkeeper's place is 180, so by Lesart K it waits for
night 5. A sober seat did; this one sat beside the No Dashii and was
poisoned, and the simulator woke a droisoned seat on its new character
regardless — it chose at 180 and drunk the Empath. The solver had been
offering a late-made Innkeeper ever since to keep that world (Paket 5);
it now asks only who held it at its turn.

Seed 1107 of the line Philosopher, Grandmother, Snake Charmer: a
Philosopher with the Snake Charmer's ability chose the Goon at 220. The
simulator never asked the Goon about a Snake Charmer, so the Ojo at 490
counted as the first, went drunk, and the Goon it named lived. The
night-walk had it right.
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
from botc.info import GameState                   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLAGUE = ("PlagueDoctor", "PitHag", "Mezepheles", "Summoner")
CHARMER = ("Philosopher", "Grandmother", "SnakeCharmer")


def game(seed, must):
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
    return deal, heard, st


class AnInnkeeperMadeAfterItsPlace(SolverTest):

    def test_does_not_choose_that_night(self):
        deal, _heard, st = game(1439, PLAGUE)
        self.assertIn(("N4", 9, "Innkeeper"), deal.changes)
        self.assertEqual(deal.made_at[(4, 9)], 280)
        # Poisoned beside the No Dashii, and asleep all the same.
        self.assertEqual(deal.innkeeper_drunk, {})
        self.assertEqual(deal.innkeeper_guarded, {})

    def test_the_true_world_is_kept(self):
        deal, _heard, st = game(1439, PLAGUE)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_the_solver_offers_only_who_held_it_at_its_turn(self):
        deal, _heard, st = game(1439, PLAGUE)
        # The worlds the plan is asked about carry the Pit-Hag's change.
        seen = []
        given = S._plan_as_given

        def keep(world, *args, **kwargs):
            seen.append(world)
            return given(world, *args, **kwargs)
        S._plan_as_given = keep
        try:
            S.explanation_cost(deal.world(), st)
        finally:
            S._plan_as_given = given
        made = [w for w in seen
                if any(c.phase == "N4" and c.seat == 9
                       and c.role == "Innkeeper"
                       for c in getattr(w, "changes", ()))]
        self.assertTrue(made)
        for world in made:
            got = S.an_innkeeper_drunks_one_of_the_two_it_guards(world, st,
                                                                 4)
            self.assertNotIn(9, [s.actor for s in got])


class AGoonChosenByASnakeCharmer(SolverTest):

    def test_drunks_the_charmer_and_the_ojo_kills_it(self):
        import nightwalk
        deal, heard, _st = game(1107, CHARMER)
        self.assertEqual(deal.philosophies.get(4), "SnakeCharmer")
        self.assertEqual(deal.roles[5], "Goon")
        self.assertEqual(deal.goon_first[2], (4, 5))
        self.assertEqual(deal.deaths.get(5), "N2")
        for night in range(2, deal.nights_played + 1):
            with self.subTest(night=night):
                got = nightwalk.walk(deal, night,
                                     nightwalk.hidden_from(deal, night,
                                                           heard))
                self.assertEqual(got.died, deal.died_on(f"N{night}"))
                self.assertFalse(got.untold)

    def test_the_true_world_is_kept(self):
        deal, _heard, st = game(1107, CHARMER)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))


class BothLanguagesAgree(SolverTest):

    def test_on_the_innkeepers_game(self):
        import app
        import play_games
        from make_fixtures import played
        rng = random.Random(1439)
        script = play_games.an_awkward_script(rng, must_have=PLAGUE)
        payload = played("s1439", script, 1439, [7, 8, 9, 10, 11][1439 % 5],
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
