"""The Kazali (20.10.2026), the second of the big characters.

"Each night*, choose a player: they die. [You choose which players are
which Minions. -? to +? Outsiders]"

Patrick's answers (claude/kazali-lesarten.md), Weg 1 for all four:

  A  Always the usual number of Minions.
  B  It wakes on the first night for its own ability; the players it
     makes Minions do not wake for theirs.
  C  Its Minions mostly claim the character they had before (as the Lord
     of Typhon's do).
  D  It picks any players, Townsfolk and Outsiders alike.

And Stelle 61, found at the Lord of Typhon's gate: an Innkeeper (or a
Sailor) killed later the same night leaves its drunk sober for the day.
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
from botc import scripts, waking                  # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.roles import SETUP, TEAM                # noqa: E402
from botc.worlds import World, _bags              # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["kazali", "poisoner", "spy", "scarletwoman", "marionette", "chef",
       "empath", "monk", "washerwoman", "investigator", "soldier",
       "chambermaid", "recluse", "saint", "drunk", "butler"]
KAZALI = scripts.from_ids("Kazali", IDS)


class TheBag(SolverTest):

    def test_the_usual_minions_and_any_outsiders(self):
        bags = [counts for present, counts in _bags(9, KAZALI)
                if "Kazali" in present and "Marionette" not in present]
        self.assertTrue(bags)
        self.assertTrue(all(c["minion"] == SETUP[9][2] for c in bags))
        self.assertTrue({0, 1, 2, 3, 4} <= {c["outsider"] for c in bags})

    def test_it_wakes_on_the_first_night_and_kills_after(self):
        c = CHARACTERS["Kazali"]
        self.assertEqual(c.nights, "every")
        self.assertGreater(c.first_night, 0)
        self.assertGreater(c.other_night, 0)
        self.assertNotIn("Kazali", S.STARPASSES)

    def test_a_chambermaid_sees_it_wake_on_the_first_night(self):
        roles = ["Chef", "Empath", "Chambermaid", "Monk", "Soldier",
                 "Poisoner", "Kazali"]
        st = GameState(n_players=7, script=KAZALI,
                       claims=dict(enumerate(roles)))
        world = World(tuple(roles), (None,) * 7)
        self.assertTrue(waking.woke_for_own_ability(world, st, 6, 1))
        roles[6] = "LordOfTyphon"
        world = World(tuple(roles), (None,) * 7)
        self.assertFalse(waking.woke_for_own_ability(world, st, 6, 1))


def games(how_many=300, nights=3, must=("Kazali",)):
    import play_games
    import simulate
    for seed in range(how_many):
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        sc = play_games.an_awkward_script(rng, must_have=must)
        deal, heard = simulate.play(n, rng, nights=nights, script=sc)
        if "Kazali" in deal.roles:
            yield seed, sc, rng, deal, heard


class TheSimulatorDealsIt(SolverTest):

    def test_the_usual_minions_out_of_good_tokens(self):
        seen, outsiders = 0, set()
        for seed, _sc, _rng, deal, _heard in games():
            seen += 1
            with self.subTest(seed=seed):
                minions = sum(TEAM[r] == "minion" for r in deal.roles)
                self.assertEqual(minions, SETUP[deal.n][2])
                for token in deal.first_tokens.values():
                    self.assertNotIn(token, deal.roles)
                    outsiders.add(TEAM[token])
        self.assertGreater(seen, 20)
        self.assertEqual(outsiders, {"townsfolk", "outsider"})

    def test_its_minions_mostly_claim_what_they_were(self):
        import claims as C
        said = told = 0
        for _seed, sc, rng, deal, _heard in games():
            cl, _wk, _ = C.claims_for(deal, rng, script=sc)
            for seat, token in deal.first_tokens.items():
                told += 1
                said += cl.get(seat) == token
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
            # Not a Barber's swap: that class is Stelle 4, kazali or not
            # (seed 193 swaps the Kazali with the Vizier).
            if S.explanation_cost(deal.world(), st) is None \
                    and "Barber" not in deal.roles:
                lost.append(seed)
        self.assertEqual(lost, [])


class AnInnkeeperKilledThatNight(SolverTest):
    """Stelle 61: its drunk is sober for the day."""

    def test_the_drunk_is_sober_by_day(self):
        import play_games
        import simulate
        found = 0
        for seed in range(400):
            n = [7, 8, 9, 10, 11][seed % 5]
            rng = random.Random(seed)
            sc = play_games.an_awkward_script(
                rng, must_have=("Innkeeper", "Psychopath"))
            d, _heard = simulate.play(n, rng, nights=4, script=sc)
            keeper = next((p for p in range(n)
                           if d.roles[p] == "Innkeeper"), None)
            for night, drunk in d.innkeeper_drunk.items():
                if keeper is None or d.deaths.get(keeper) != f"N{night}":
                    continue
                found += 1
                by_day = simulate.droisoned_at(d, night, by_day=True)
                d.innkeeper_drunk = {}
                without = simulate.droisoned_at(d, night, by_day=True)
                d.innkeeper_drunk = {night: drunk}
                with self.subTest(seed=seed, night=night):
                    self.assertEqual(drunk in by_day, drunk in without)
        self.assertGreater(found, 0)


def _payloads():
    def pay(claims, events, days=(1,)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players, "infos": [],
                "script": {"name": KAZALI.name, "characters": IDS},
                "days_done": list(days)}
    seven = ["Chef", "Empath", "Monk", "Washerwoman", "Investigator",
             "Soldier", "Saint"]
    return [pay(seven, {}),
            pay(seven, {3: ["N2"]}, days=(1, 2)),
            pay(seven[:5] + ["Butler", "Recluse"], {0: ["X1"]})]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_a_kazali(self):
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
