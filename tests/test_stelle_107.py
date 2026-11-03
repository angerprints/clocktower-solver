"""Stelle 107 (03.11.2026): a Barber the Al-Hadikhia raised and killed again.

"If you died today or tonight, the Demon may choose 2 players (not
another Demon) to swap characters." The Al-Hadikhia chooses three, and a
corpse among them that chooses to live comes back; if all three chose
life, all three die. So a dead Barber it chose may die again tonight, and
the Demon swaps again. The record keeps who lay dead at dawn and nothing
of the return, so the solver offers that night's swap whenever a dead
Barber is in the row, and it never requires it.

And one swap a death, night after night: a story that swapped already
is told on, on the board its swap left. The solver offered one swap a
game, for the first death only.

Seed 2955 of the line Al-Hadikhia, Monk, Innkeeper, Tea Lady, Goon: the
Barber (seat 5) dies on night 2 and the Demon swaps itself with the Baron;
on nights 3 and 4 the Al-Hadikhia chooses the dead Barber, and the Demon
swaps the Monk and the Saint on night 3. The solver threw the true world
away.
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
MUST = ("AlHadikhia", "Monk", "Innkeeper", "TeaLady", "Goon")


def game(seed, must=MUST):
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


class ABarberRaisedAndKilledAgain(SolverTest):

    def test_the_game(self):
        deal, _heard, st = game(2955)
        self.assertEqual(deal.roles[5], "Barber")
        self.assertEqual(st.died_at(5), ("N2",))
        self.assertEqual(deal.changes[:4],
                         [("N2", 3, "Baron"), ("N2", 2, "AlHadikhia"),
                          ("N3", 1, "Saint"), ("N3", 6, "Monk")])

    def test_the_dead_barber_in_the_row_is_found(self):
        deal, _heard, st = game(2955)
        self.assertEqual(S.barber_raised_and_fell(deal.world(), st),
                         [(5, "N3"), (5, "N4")])

    def test_both_swaps_are_told_in_one_story(self):
        deal, _heard, st = game(2955)
        want = {("N2", 2, "AlHadikhia"), ("N2", 3, "Baron"),
                ("N3", 1, "Saint"), ("N3", 6, "Monk")}
        told = [{(c.phase, c.seat, c.role) for c in changes}
                for changes, _cost in
                S.a_barber_lets_the_demon_swap_two(deal.world(), st)]
        self.assertIn(want, told)

    def test_the_true_world_is_kept(self):
        deal, _heard, st = game(2955)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_no_row_no_second_swap(self):
        # Without the Al-Hadikhia's rows the Barber died once, and no story
        # swaps on a later night.
        deal, _heard, st = game(2955)
        from botc.info import AlHadikhiaChose
        st.infos = [i for i in st.infos if not isinstance(i, AlHadikhiaChose)]
        for changes, _cost in S.a_barber_lets_the_demon_swap_two(
                deal.world(), st):
            self.assertTrue(all(c.phase == "N2" for c in changes))


class BothLanguagesAgree(SolverTest):

    def test_on_the_barbers_game(self):
        import app
        import play_games
        from make_fixtures import played
        rng = random.Random(2955)
        script = play_games.an_awkward_script(rng, must_have=MUST)
        payload = played("s2955", script, 2955, [7, 8, 9, 10, 11][2955 % 5],
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
