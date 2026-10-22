"""The Summoner (21.10.2026), the fifth of the big characters in the order
Patrick agreed on 20.10.2026.

"You get 3 bluffs. On the 3rd night, choose a player: they become an evil
Demon of your choice. [No Demon]"

Patrick's answers (claude/beschwoerer-lesarten.md):

  A  Weg 1: every player with every Demon, searched.
  B  Weg 1: anybody alive, itself and other Minions too; somebody dead
     only as a Zombuul, which has then died once (their jinx).
  C  Weg 1: every Demon of the script but Lil' Monsta, Legion and Riot;
     a Lord of Typhon beside a Minion, its other neighbour made one.
  D  Weg 1: dead before its turn, no Demon comes and good wins there.
  E  Weg 1: drunk or poisoned on its turn, the same at dawn — unless a
     Courtier or a Preacher took its ability (their jinxes).
  F  The Summoner registers as the Demon to the Clockmaker: the steps to
     the nearest other Minion, and 0 with none.
  G  Weg 1: the Chambermaid counts it on the first night and the third.
  H  The simulator makes a living good player the Demon — one whose
     character the table has seen confirmed, if there is one.
  I  A second living Demon is not built.
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
IDS = ["summoner", "poisoner", "spy", "scarletwoman", "imp", "nodashii",
       "vortox", "pukka", "zombuul",
       "chef", "empath", "fortuneteller", "monk", "washerwoman",
       "investigator", "soldier", "slayer", "clockmaker", "chambermaid",
       "undertaker", "snakecharmer", "sailor"]
SUM = scripts.from_ids("Beschwörer", IDS)
#    0       1         2               3       4              5
R = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman", "Soldier",
     "Summoner"]
C = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman", "Soldier",
     "Investigator"]


def cost(rows=(), deaths=None, days=(1, 2), roles=R, claims=C, **kw):
    st = GameState(n_players=len(roles), script=SUM,
                   claims=dict(enumerate(claims)), infos=list(rows),
                   deaths=deaths or {}, days_done=set(days), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)),
                              st)


class TheBag(SolverTest):

    def test_no_demon_and_a_townsfolk_more(self):
        self.assertEqual(CHARACTERS["Summoner"].setup,
                         ({"demon": -1, "townsfolk": 1},))
        worlds = enumerate_worlds(7, dict(enumerate(C)), script=SUM)
        evil = {tuple(sorted(r for r in w.roles
                             if CHARACTERS[r].team in ("minion", "demon")))
                for w in worlds}
        self.assertIn(("Summoner",), evil)
        self.assertIn(("Imp", "Poisoner"), evil)
        self.assertNotIn(("Imp", "Summoner"), evil)


class NoDemonYet(SolverTest):

    def test_nobody_dies_on_the_second_night(self):
        self.assertIsNotNone(cost(quiet_nights={2}))
        self.assertIsNone(cost(deaths={1: ("N2",)}))


class ItSummons(SolverTest):

    def test_the_demon_kills_from_the_third_night(self):
        self.assertIsNotNone(cost(deaths={1: ("N3",)}))
        # No Demon of this script kills twice.
        self.assertIsNone(cost(deaths={1: ("N3",), 2: ("N3",)}))

    def test_a_pukka_may_come_on_the_second_night(self):
        # Poisoned on the second night, dead on the third: only a Pukka
        # made on the second night does that, and so does one made on the
        # third — and then nobody dies until the fourth.
        self.assertIsNotNone(cost(deaths={1: ("N3",)}, quiet_nights={2}))

    def test_the_fortune_teller_finds_whoever_it_made(self):
        yes = I.FortuneTeller(4, 2, a=0, b=1, yes=True)
        self.assertIsNotNone(cost([yes], deaths={4: ("N3",)},
                                  days=(1, 2, 3)))
        # Before the third night there is nobody to find but the red
        # herring.
        self.assertIsNotNone(cost([I.FortuneTeller(1, 2, a=0, b=1,
                                                   yes=True)]))


class NoDemonComes(SolverTest):

    def test_dead_before_its_turn_ends_the_game(self):
        hanged = dict(executions={1: 6}, deaths={6: ("D1",)})
        self.assertIsNone(cost(days=(1, 2), **hanged))
        self.assertIsNotNone(cost(days=(1,), game_over=True, **hanged))

    def test_drunk_on_its_turn_ends_it_at_dawn(self):
        def ways(**kw):
            st = GameState(n_players=7, script=SUM, claims=dict(enumerate(C)),
                           infos=[], **kw)
            st._final_phase_held = st.final_phase()
            return [w for w in S.summon_options(World(tuple(R), (None,) * 7),
                                                st)
                    if any(type(c).__name__ == "NotSummoned" for c in w)]
        # Over at the third dawn: no Demon may have come.
        self.assertEqual(len(ways(days_done={1, 2}, quiet_nights={2, 3},
                                  game_over=True)), 1)
        # Going on, it came.
        self.assertEqual(ways(days_done={1, 2, 3}, quiet_nights={2, 3}), [])
        roles = list(R)
        roles[3] = "Sailor"
        claims = list(C)
        claims[3] = "Sailor"
        sailed = [I.SailorChoice(3, 3, target=6)]
        self.assertIsNotNone(cost(sailed, days=(1, 2), quiet_nights={2, 3},
                                  game_over=True, roles=roles,
                                  claims=claims))


class TheClockmaker(SolverTest):

    def test_counts_from_the_summoner_and_zero_alone(self):
        roles = ["Clockmaker"] + R[1:]
        claims = ["Clockmaker"] + C[1:]
        self.assertIsNotNone(cost([I.ClockmakerInfo(1, 0, count=0)],
                                  roles=roles, claims=claims))
        self.assertIsNone(cost([I.ClockmakerInfo(1, 0, count=1)],
                               roles=roles, claims=claims))


class TheChambermaid(SolverTest):

    def test_counts_it_on_the_first_night(self):
        roles = ["Chambermaid"] + R[1:]
        claims = ["Chambermaid"] + C[1:]
        # The Summoner (6) is shown its bluffs; the Washerwoman (4) is
        # shown hers too.
        woke = I.ChambermaidInfo(1, 0, a=4, b=6, count=2)
        slept = I.ChambermaidInfo(1, 0, a=4, b=6, count=1)
        self.assertEqual(cost([woke], roles=roles, claims=claims), 1.0)
        self.assertLess(cost([slept], roles=roles, claims=claims) or 0, 1.0)


class TheMarionette(SolverTest):
    """Nobody is the Marionette until the Demon comes; then it is a
    neighbour of the Demon, dead or alive, and the Summoner chose freely
    (Patrick, 22.10.2026)."""

    def world(self):
        roles = list(R)
        roles[5] = "Marionette"            # believes the Soldier
        believes = [None] * 7
        believes[5] = "Soldier"
        return World(tuple(roles), tuple(believes))

    def made(self, **kw):
        st = GameState(n_players=7, script=SUM, claims=dict(enumerate(C)),
                       infos=[], days_done={1, 2, 3}, **kw)
        st._final_phase_held = st.final_phase()
        out = {}
        for way in S.summon_options(self.world(), st):
            made = [c for c in way if type(c).__name__ == "Summoned"]
            if made:
                out.setdefault(made[0].seat, way)
        return out

    def test_beside_whoever_was_made(self):
        self.assertEqual(set(self.made()), {4, 6})

    def test_dead_or_alive(self):
        self.assertEqual(set(self.made(executions={1: 5},
                                       deaths={5: ("D1",)})), {4, 6})

    def test_the_seat_was_good_until_then(self):
        from botc.worlds import Timeline, dealt_roles
        self.assertEqual(dealt_roles(self.world())[5], "Soldier")
        way = self.made()[4]
        view = Timeline(self.world(), way)
        self.assertEqual(view.role_at(5, "N2"), "Soldier")
        self.assertFalse(view.evil_at(5, "N2"))
        self.assertEqual(view.role_at(5, "D3"), "Marionette")
        self.assertTrue(view.evil_at(5, "D3"))


def games(how_many=300, nights=4, must=("Summoner",)):
    import play_games
    import simulate
    for seed in range(how_many):
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        sc = play_games.an_awkward_script(rng, must_have=must)
        deal, heard = simulate.play(n, rng, nights=nights, script=sc)
        if deal.summoner is not None:
            yield seed, sc, rng, deal, heard


class TheSimulatorPlaysIt(SolverTest):

    def test_it_makes_a_good_player_the_demon(self):
        played = made = good = ended = 0
        for _seed, _sc, _rng, deal, _heard in games():
            played += 1
            self.assertFalse(any(CHARACTERS[r].team == "demon"
                                 for r in deal.roles))
            if deal.summoned is not None:
                made += 1
                night, seat, _demon = deal.summoned
                good += CHARACTERS[deal.roles[seat]].team in (
                    "townsfolk", "outsider")
                self.assertIn(night, (2, 3))
            elif deal.ended_why == "summoner":
                ended += 1
        self.assertGreater(played, 80)
        self.assertGreater(good, made * 0.8)
        self.assertGreater(ended, 0)

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
    def pay(rows, events, days=(1, 2), roles_claimed=C, over=False,
            ids=IDS):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(roles_claimed)]
        out = {"n_players": len(roles_claimed), "players": players,
               "infos": rows,
               "script": {"name": SUM.name, "characters": ids},
               "days_done": list(days)}
        if over:
            out["game_over"] = True
        return out

    clock = ["Clockmaker"] + C[1:]
    return [
        pay([], {1: ["N3"]}),
        pay([], {1: ["N3"], 2: ["N4"]}, days=(1, 2, 3)),
        pay([{"type": "FortuneTeller", "night": 4, "player": 2, "a": 0,
              "b": 1, "yes": True}], {4: ["N3"]}, days=(1, 2, 3)),
        pay([], {6: ["X1"]}, days=(1,), over=True),
        pay([{"type": "ClockmakerInfo", "night": 1, "player": 0,
              "count": 0}], {}, roles_claimed=clock),
        # A Marionette-to-be holding a Puzzlemaster until the Demon comes
        # (22.10.2026).
        pay([{"type": "FortuneTeller", "night": 2, "player": 2, "a": 5,
              "b": 6, "yes": True}], {1: ["N3"]}, days=(1, 2, 3),
            roles_claimed=C[:5] + ["Puzzlemaster", "Investigator"],
            ids=IDS + ["marionette", "puzzlemaster"]),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_a_summoner(self):
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
