"""Stelle 83 (01.11.2026): a Pit-Hag makes a Demon beside the Demon in play.

Patrick's answers (claude/stelle-83-lesarten.md):

A Weg 1: the old Demon stays a Demon, so two live — with everything Hatter
    stage 2 built for a Summoner's second Demon.
B Weg 1: a good player made a Demon is a good Demon, and kills like one.
C Weg 2: the simulator makes a Demon only in runs that ask for it
    (`SIM_PIT_HAG_DEMONS`), so every other seed keeps its game.
D Weg 1: the Storyteller in the simulator as the wiki has it: a Demon
    made another Demon, nobody dies; a new evil Demon, the old one and one
    more (Patrick's note to A); a good Demon, half the time one of the two.

Found on the way (claude/stelle-83.md): arbitrary nights where nothing
has to fire, a Lleech the Storyteller may take, a Scarlet Woman stepping
up for a Leviathan before the night's readings, two Demon lines walked in
either order, a No Dashii made something else, the second Demon seen at
the Pit-Hag's turn; in the simulator the Flowergirl and the Choirboy
asking both Demons, and no Zombuul taken on the arbitrary night.
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
from botc.worlds import Change, PitHagDemon, Timeline, World  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
# seed: (characters the gate line asks for, what the Pit-Hag made) —
# found with SIM_PIT_HAG_DEMONS=0.5; every one was lost before. 207 is the
# Flowergirl that asked one Demon, 526 an Ojo that need not kill on its
# arbitrary night, 1593 a Leviathan whose Scarlet Woman steps up before a
# Fortune Teller, 2825 a No Dashii made something else after a Snake
# Charmer chose it.
PLAYED = {41: (("PitHag",), "good"),
          109: (("PitHag",), "evil"),
          207: (("PitHag",), "good"),
          526: (("PitHag", "Vortox", "Flowergirl"), "type"),
          1593: (("PitHag", "ScarletWoman", "FangGu"), "good"),
          2825: (("PitHag", "Barber", "SnakeCharmer"), "type")}


class asked:
    """The simulator with the switch on, for one block."""

    def __enter__(self):
        import simulate
        self.was = simulate.PIT_HAG_DEMONS
        simulate.PIT_HAG_DEMONS = 0.5
        return simulate

    def __exit__(self, *exc):
        import simulate
        simulate.PIT_HAG_DEMONS = self.was


def game(seed, must=("PitHag",)):
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
    return deal, st


class ThePlayedGamesAreKept(SolverTest):

    def test_every_one(self):
        with asked():
            for seed, (must, kind) in PLAYED.items():
                deal, st = game(seed, must)
                with self.subTest(seed=seed):
                    made = deal.pit_hag_demon
                    self.assertEqual([k for _t, k, _o in made.values()],
                                     [kind])
                    self.assertIsNotNone(
                        S.explanation_cost(deal.world(), st))

    def test_unasked_the_pit_hag_makes_no_demon(self):
        for seed, (must, _kind) in PLAYED.items():
            deal, _st = game(seed, must)
            with self.subTest(seed=seed):
                self.assertFalse(getattr(deal, "pit_hag_demon", None))


TB = scripts.TROUBLE_BREWING
#        0       1        2         3          4         5      6
ROLES = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Imp",
         "Poisoner"]


class TwoDemonsLive(SolverTest):

    def test_beside_the_demon_both_are_demons(self):
        world = World(tuple(ROLES), (None,) * 7)
        made = Timeline(world, (PitHagDemon("N2", 1, "NoDashii", "good"),))
        self.assertEqual(tuple(made.demons_at("N3")), (5, 1))
        # A good Demon (B Weg 1): its side stays.
        self.assertFalse(made.evil_at(1, "N3"))

    def test_the_demon_made_another_is_still_one(self):
        world = World(tuple(ROLES), (None,) * 7)
        made = Timeline(world, (Change("N2", 5, "NoDashii", "evil"),))
        self.assertEqual(tuple(made.demons_at("N3")), (5,))

    def test_a_row_beside_the_demon_tells_a_second(self):
        script = scripts.from_ids(
            "Trouble Brewing with a Pit-Hag",
            [c.lower() for c in TB.keys] + ["pithag", "nodashii"])
        roles = ["Chef", "Empath", "Monk", "Soldier", "Undertaker", "Imp",
                 "PitHag"]
        state = GameState(n_players=7, script=script,
                          claims={0: "Chef", 1: "Empath", 2: "Monk",
                                  3: "Soldier", 4: "Undertaker",
                                  5: "Chef", 6: "Empath"},
                          days_done={1},
                          infos=[I.PitHagChoice(2, 6, target=1,
                                                role="NoDashii")])
        world = World(tuple(roles), (None,) * 7)
        stories = S.a_pit_hag_makes_somebody_else(world, state)
        kinds = {type(c).__name__ for changes, _w in stories for c in changes}
        self.assertEqual(kinds, {"PitHagDemon"})


def _payloads():
    from make_fixtures import played
    import play_games
    out = []
    with asked():
        for seed, (must, _kind) in PLAYED.items():
            # Python and JavaScript part on this board already on main —
            # even its legal deals (a new open item, not this one's).
            if seed == 1593:
                continue
            rng = random.Random(seed)
            script = play_games.an_awkward_script(rng, must_have=must)
            n = [7, 8, 9, 10, 11][seed % 5]
            out.append(played(f"s{seed}", script, seed, n, 4,
                              rng=rng)["payload"])
    return out


class BothLanguagesAgree(SolverTest):

    def test_on_the_played_games(self):
        import app
        cases = _payloads()
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); return r.error || r.valid; })));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=1800)
        self.assertEqual(got.returncode, 0, got.stderr)
        py = []
        for p in cases:
            r = app.run_solve(p)
            py.append(r.get("error") or r["valid"])
        self.assertEqual(json.loads(got.stdout), py)
        self.assertTrue(all(isinstance(v, int) and v > 0 for v in py), py)


if __name__ == "__main__":
    unittest.main()
