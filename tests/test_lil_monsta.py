"""Lil' Monsta (21.10.2026), the fourth of the big characters in the order
Patrick agreed on 20.10.2026.

"Each night, Minions choose who babysits Lil' Monsta & "is the Demon".
Each night*, a player might die. [+1 Minion]"

Patrick's answers (claude/lil-monsta-lesarten.md), all Weg 1:

  A  One babysitter a night, the same for every reading of that night and
     the day after, searched only where something asks.
  B  Anybody alive may babysit.
  C  A babysitter may say so: its own row, "hütet Lil' Monsta".
  D  At most one death a night, never the babysitter, a kill by the Demon
     (a Monk or a Soldier keeps a player from it, a Grandmother grieves),
     and nothing droisons it.
  E  A Snake Charmer that chooses the babysitter swaps with it like a
     Demon.
  F  An Exorcist that names last night's babysitter: nobody dies of Lil'
     Monsta tonight.
  G  The Chambermaid counts neither the Minions' choosing nor the
     babysitter being shown the token.
  H  In the simulator: a Minion mostly, the same one seven nights in ten,
     now and then somebody good; somebody dies most nights.
  I  A Pit-Hag making a second Demon beside it is not built.
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
from botc.worlds import World, enumerate_worlds   # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["lilmonsta", "poisoner", "spy", "scarletwoman", "vizier",
       "chef", "empath", "fortuneteller", "monk", "washerwoman",
       "investigator", "soldier", "slayer", "exorcist", "snakecharmer",
       "chambermaid", "clockmaker", "grandmother", "imp"]
LM = scripts.from_ids("Lil' Monsta", IDS)
#    0       1         2               3       4              5
R = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman", "Poisoner",
     "Spy"]
C = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman",
     "Investigator", "Soldier"]


def cost(rows=(), deaths=None, days=(1, 2), roles=R, claims=C, **kw):
    st = GameState(n_players=len(roles), script=LM,
                   claims=dict(enumerate(claims)), infos=list(rows),
                   deaths=deaths or {}, days_done=set(days), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)),
                              st)


def sat(night, seat):
    return I.LilMonstaBabysat(night, seat)


class TheBag(SolverTest):

    def test_nobody_holds_it_and_a_minion_comes_in(self):
        self.assertFalse(CHARACTERS["LilMonsta"].dealt)
        self.assertNotIn("LilMonsta", LM.seated_keys)
        worlds = enumerate_worlds(7, dict(enumerate(C)), script=LM)
        teams = {tuple(sorted(r for r in w.roles
                              if CHARACTERS[r].team in ("minion", "demon")))
                 for w in worlds}
        self.assertIn(("Poisoner", "Spy"), teams)        # Lil' Monsta's
        self.assertIn(("Imp", "Poisoner"), teams)        # the Imp's
        self.assertFalse(any(len(t) != 2 for t in teams))


class ItKills(SolverTest):

    def test_a_quiet_night_and_one_death_and_never_two(self):
        self.assertIsNotNone(cost(quiet_nights={2}))
        self.assertIsNotNone(cost(deaths={1: ("N2",)}))
        self.assertIsNone(cost(deaths={1: ("N2",), 3: ("N2",)}))

    def test_never_the_babysitter(self):
        # Killed, it was no babysitter: the row has to be made up.
        self.assertEqual(cost([sat(2, 0)], {1: ("N2",)}), 1.0)
        self.assertLess(cost([sat(2, 0)], {0: ("N2",)}), 1.0)

    def test_a_soldier_is_kept_from_it(self):
        roles = ["Chef", "Empath", "FortuneTeller", "Soldier",
                 "Washerwoman", "Poisoner", "Spy"]
        claims = list(roles[:5]) + ["Investigator", "Monk"]
        # Dead, so it was drunk or poisoned.
        self.assertLess(cost([], {3: ("N2",)}, roles=roles, claims=claims),
                        1.0)
        self.assertEqual(cost([], {1: ("N2",)}, roles=roles,
                              claims=claims), 1.0)

    def test_an_exorcist_naming_last_nights_babysitter_stops_it(self):
        roles = ["Chef", "Empath", "Exorcist", "Monk", "Washerwoman",
                 "Poisoner", "Spy"]
        claims = list(roles[:5]) + ["Investigator", "Soldier"]
        named = I.ExorcistChoice(2, 2, target=0)
        self.assertEqual(cost([sat(1, 0)], {1: ("N2",)}, roles=roles,
                              claims=claims), 1.0)
        self.assertLess(cost([sat(1, 0), named], {1: ("N2",)},
                             roles=roles, claims=claims), 1.0)


class TheBabysitter(SolverTest):

    def test_registers_as_the_demon_to_a_fortune_teller(self):
        # A yes on two good players: the babysitter, or the red herring.
        self.assertIsNotNone(cost([I.FortuneTeller(1, 2, a=0, b=1,
                                                   yes=True)]))

    def test_said_by_a_good_player_is_true_of_one_night(self):
        self.assertIsNotNone(cost([sat(1, 0), sat(2, 1)]))

    def test_killed_by_a_slayer_ends_the_game(self):
        roles = ["Chef", "Empath", "Slayer", "Monk", "Washerwoman",
                 "Poisoner", "Spy"]
        claims = list(roles[:5]) + ["Investigator", "Soldier"]
        shot = I.SlayerShot(1, 2, target=5, died=True)
        self.assertIsNotNone(cost([shot], {5: ("D1",)}, days=(1,),
                                  roles=roles, claims=claims,
                                  game_over=True))
        self.assertIsNone(cost([shot], {5: ("D1",)}, roles=roles,
                               claims=claims))

    def test_the_scarlet_woman_babysits_for_the_rest_of_the_game(self):
        roles = ["Chef", "Empath", "Slayer", "Monk", "Washerwoman",
                 "Poisoner", "ScarletWoman"]
        claims = list(roles[:5]) + ["Investigator", "Soldier"]
        shot = I.SlayerShot(1, 2, target=5, died=True)
        self.assertIsNotNone(cost([shot], {5: ("D1",)}, roles=roles,
                                  claims=claims))

    def test_a_babysitting_vizier_dies_when_executed(self):
        roles = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman",
                 "Vizier", "Spy"]
        claims = list(roles[:5]) + ["Vizier", "Soldier"]
        # Executed and alive: it was not babysitting that day.
        self.assertEqual(cost([], {}, roles=roles, claims=claims,
                              executions={1: 5}), 1.0)
        self.assertLess(cost([sat(1, 5)], {}, roles=roles, claims=claims,
                             executions={1: 5}), 1.0)

    def test_a_snake_charmer_swaps_with_it(self):
        roles = ["Chef", "Empath", "SnakeCharmer", "Monk", "Washerwoman",
                 "Poisoner", "Spy"]
        claims = list(roles[:5]) + ["Investigator", "Soldier"]
        swap = I.SnakeCharmerChoice(2, 2, target=5, swapped=True)
        self.assertIsNotNone(cost([swap], roles=roles, claims=claims))

    def test_a_chambermaid_does_not_count_it(self):
        roles = ["Chef", "Empath", "Chambermaid", "Monk", "Washerwoman",
                 "Poisoner", "Spy"]
        claims = list(roles[:5]) + ["Investigator", "Soldier"]
        # The Chef babysits and is woken to be shown it: that is no
        # waking of its own.
        maid = I.ChambermaidInfo(2, 2, a=0, b=4, count=0)
        self.assertIsNotNone(cost([sat(2, 0), maid], roles=roles,
                                  claims=claims))

    def test_a_clockmaker_counts_to_the_nearest_other_minion(self):
        roles = ["Chef", "Empath", "Clockmaker", "Monk", "Poisoner",
                 "Washerwoman", "Spy"]
        claims = ["Chef", "Empath", "Clockmaker", "Monk", "Investigator",
                  "Washerwoman", "Soldier"]
        # The Poisoner babysits: the Spy is two seats away.
        self.assertIsNotNone(cost([I.ClockmakerInfo(1, 2, count=2)],
                                  roles=roles, claims=claims))


def games(how_many=300, nights=4, must=("LilMonsta",)):
    import play_games
    import simulate
    for seed in range(how_many):
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        sc = play_games.an_awkward_script(rng, must_have=must)
        deal, heard = simulate.play(n, rng, nights=nights, script=sc)
        if getattr(deal, "lil_monsta", False):
            yield seed, sc, rng, deal, heard


class TheSimulatorPlaysIt(SolverTest):

    def test_minions_babysit_and_now_and_then_somebody_good(self):
        played = good = kills = 0
        for _seed, _sc, _rng, deal, heard in games():
            played += 1
            self.assertFalse(any(CHARACTERS[r].team == "demon"
                                 for r in deal.roles))
            good += sum(isinstance(r, I.LilMonstaBabysat) for r in heard)
            kills += len(getattr(deal, "lm_aimed", {}))
        self.assertGreater(played, 40)
        self.assertGreater(good, 0)
        self.assertGreater(kills, played)

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
    def pay(rows, events, days=(1, 2), roles_claimed=C, over=False):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(roles_claimed)]
        out = {"n_players": len(roles_claimed), "players": players,
               "infos": rows,
               "script": {"name": LM.name, "characters": IDS},
               "days_done": list(days)}
        if over:
            out["game_over"] = True
        return out

    slayer = ["Chef", "Empath", "Slayer", "Monk", "Washerwoman",
              "Investigator", "Soldier"]
    return [
        pay([], {1: ["N2"]}),
        pay([{"type": "FortuneTeller", "night": 1, "player": 2, "a": 0,
              "b": 1, "yes": True}], {}),
        pay([{"type": "LilMonstaBabysat", "night": 1, "player": 0},
             {"type": "LilMonstaBabysat", "night": 2, "player": 0}],
            {3: ["N2"]}),
        pay([{"type": "SlayerShot", "night": 1, "player": 2, "target": 5,
              "died": True}], {5: ["D1"]}, days=(1,), roles_claimed=slayer,
            over=True),
        # The babysitter shot and the game going on: the Scarlet Woman
        # babysits from then on.
        pay([{"type": "SlayerShot", "night": 1, "player": 2, "target": 5,
              "died": True}], {5: ["D1"], 1: ["N2"]}, roles_claimed=slayer),
        pay([{"type": "FortuneTeller", "night": 1, "player": 2, "a": 1,
              "b": 3, "yes": True},
             {"type": "FortuneTeller", "night": 2, "player": 2, "a": 3,
              "b": 4, "yes": True}], {1: ["N2"]}),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_lil_monsta(self):
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
