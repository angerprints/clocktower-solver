"""A Philosopher has the ability it took — step 2 (13.10.2026).

Open item 56, step 2: every other taken ability that acts, group by
group. The table's answers, way 1 for all of them (B to M):

  B  setup abilities in brackets do nothing when taken
  C  abilities that start on the first night work from the night of taking
  D  a Philosopher-Saint executed: good loses
  E  a taken Heretic works even dead
  G  a side changes for the Goon, the Cult Leader and the Ogre; the Ogre
     chooses on the night of taking
  H  both halves of the Mayor
  I  the Drunk, the Lunatic and characters with no ability do nothing, but
     the Philosopher is shown a token as if it held them
  J  two holders both choose and both rows are kept; only the
     Philosopher's works, because the real one is drunk
  K  only good characters from the script
  L  the simulator chooses at random on the first night
  M  group by group, each through the gate

Group 1, the ones that keep somebody alive: Monk, Soldier, Innkeeper,
Sailor, Tea Lady, Fool, Mayor, Pacifist, Exorcist, Princess.
"""

import json
import pathlib
import random
import subprocess
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

GROUP_1 = ("Monk", "Soldier", "Innkeeper", "Sailor", "TeaLady", "Fool",
           "Mayor", "Pacifist", "Exorcist", "Princess")

# Trouble Brewing's shape, with every character of group 1 to take.
IDS = ["philosopher", "monk", "soldier", "innkeeper", "sailor", "tealady",
       "fool", "mayor", "pacifist", "exorcist", "princess",
       "chef", "empath", "washerwoman", "investigator",
       "drunk", "saint", "recluse", "butler",
       "poisoner", "baron", "spy", "scarletwoman", "imp", "pukka"]
SHIELDS = scripts.from_ids("Philosopher shields", IDS)

#     0       1         2               3              4
R = ["Chef", "Empath", "Investigator", "Philosopher", "Washerwoman",
     "ScarletWoman", "Imp"]                                 # 5, 6


def cost(roles, rows=(), **kw):
    kw.setdefault("days_done", {1, 2})
    st = GameState(n_players=len(roles), script=SHIELDS,
                   claims=dict(enumerate(roles)), infos=list(rows), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)), st)


def took(role, seat=3):
    return I.PhilosopherChoice(1, seat, role=role)


class GroupOneInTheSolver(SolverTest):
    """Each with a Chef taken beside it, which keeps nobody alive."""

    def test_a_quiet_night_is_explained_by_what_it_took(self):
        for role in ("Monk", "Soldier", "Innkeeper", "Sailor", "TeaLady"):
            with self.subTest(role=role):
                self.assertIsNotNone(cost(R, [took(role)], quiet_nights={2}))
        self.assertIsNone(cost(R, [took("Chef")], quiet_nights={2}))

    def test_a_philosopher_soldier_cannot_die_by_the_demon(self):
        self.assertIsNone(cost(R, [took("Soldier")], deaths={3: ("N2",)}))
        self.assertIsNotNone(cost(R, [took("Chef")], deaths={3: ("N2",)}))

    def test_its_exorcist_has_to_name_the_demon(self):
        named = [took("Exorcist"), I.ExorcistChoice(2, 3, target=6)]
        other = [took("Exorcist"), I.ExorcistChoice(2, 3, target=2)]
        self.assertIsNotNone(cost(R, named, quiet_nights={2}))
        self.assertIsNone(cost(R, other, quiet_nights={2}))

    def test_its_fool_walks_away_from_the_gallows(self):
        self.assertIsNotNone(cost(R, [took("Fool")], executions={1: 3}))
        self.assertIsNone(cost(R, [took("Chef")], executions={1: 3}))

    def test_its_pacifist_may_spare_the_good(self):
        self.assertIsNotNone(cost(R, [took("Pacifist")], executions={1: 2}))
        self.assertIsNone(cost(R, [took("Chef")], executions={1: 2}))

    def test_its_mayor_may_send_the_kill_into_a_corpse(self):
        # H: a sunk kill explains the night anyway, at a price; the Mayor
        # explains it for free.
        dead = {1: ("E1",)}
        self.assertGreater(cost(R, [took("Mayor")], deaths=dead,
                                quiet_nights={2}),
                           cost(R, [took("Chef")], deaths=dead,
                                quiet_nights={2}))

    def test_its_princess_stops_the_demon(self):
        rows = [I.PrincessNominated(1, 3, target=0)]
        dead = {0: ("E1",), 1: ("N2",)}
        self.assertIsNone(cost(R, [took("Princess")] + rows, deaths=dead,
                               days_done={1}))
        self.assertIsNotNone(cost(R, [took("Chef")] + rows, deaths=dead,
                                  days_done={1}))

    def test_the_real_one_it_took_from_is_drunk(self):
        roles = list(R)
        roles[2] = "Soldier"
        self.assertIsNotNone(cost(roles, [took("Soldier")],
                                  deaths={2: ("N2",)}))
        self.assertIsNone(cost(roles, [took("Chef")], deaths={2: ("N2",)}))


#      0       1         2         3              4
TWO = ["Chef", "Empath", "Sailor", "Philosopher", "Washerwoman",
       "ScarletWoman", "Imp"]                                # 5, 6
WRONG = I.Empath(1, 1, count=2)                             # it is 0


def sails(seat, target):
    return I.SailorChoice(1, seat, target=target)


class TwoHoldersBothChoose(SolverTest):
    """J: both rows are kept, and only the Philosopher's lands."""

    def test_the_philosophers_sailor_drunks_whom_it_chose(self):
        rows = [took("Sailor"), sails(2, 4), sails(3, 1), WRONG]
        self.assertIsNotNone(cost(TWO, rows, days_done={1}))

    def test_the_real_sailors_choice_does_nothing(self):
        rows = [took("Sailor"), sails(2, 1), sails(3, 4), WRONG]
        self.assertIsNone(cost(TWO, rows, days_done={1}))
        # Without the Philosopher it is the real Sailor's to land.
        self.assertIsNotNone(cost(TWO, [took("Chef"), sails(2, 1), WRONG],
                                  days_done={1}))

    def test_a_drunk_philosopher_gained_nothing_to_drunk_itself_with(self):
        # Drunk when it chose, it took nothing — so not its own Sailor's
        # drunkenness either. The real Sailor then works, and chose 4.
        rows = [took("Sailor"), sails(3, 4), WRONG]
        self.assertIsNone(cost(TWO, rows, days_done={1}))


class ADrunksRowIsItsOwn(SolverTest):
    """A Drunk with the Knight's token says what it was shown, claiming
    something else. Nobody holds the Knight, but a Philosopher took it —
    and the row was read as the Philosopher's, which then had to have
    been off on a night nothing could reach it (a mixed game, 13.10.2026).
    """

    KNIGHT = scripts.from_ids("Knight and a Philosopher", [
        "philosopher", "knight", "chef", "empath", "washerwoman",
        "investigator", "drunk", "saint", "recluse", "butler", "poisoner",
        "scarletwoman", "imp"])

    def test_it_is_made_up_not_the_philosophers(self):
        roles = ("Drunk", "Chef", "Empath", "Philosopher", "Washerwoman",
                 "ScarletWoman", "Imp")
        world = World(roles, ("Knight",) + (None,) * 6)
        claims = {0: "Saint", 1: "Chef", 2: "Empath", 3: "Philosopher",
                  4: "Washerwoman", 5: "Chef", 6: "Empath"}
        rows = [took("Knight"), I.KnightInfo(1, 0, a=6, b=1)]   # 6 is it
        state = GameState(n_players=7, script=self.KNIGHT, claims=claims,
                          infos=rows, days_done={1})
        self.assertIsNotNone(S.explanation_cost(world, state))
        self.assertEqual(S.row_outcomes(world, state)[1], S.MADE_UP)


def _payloads():
    """The boards above, as the page sends them, for both languages."""
    def pay(rows, events=None, quiet=None, roles=R, days=(1, 2)):
        players = [{"claim": c, "events": (events or {}).get(i, [])}
                   for i, c in enumerate(roles)]
        out = {"n_players": len(roles), "players": players, "infos": rows,
               "script": {"name": SHIELDS.name, "characters": IDS},
               "days_done": list(days)}
        if quiet:
            out["quiet_nights"] = quiet
        return out

    def take(role, seat=3):
        return {"type": "PhilosopherChoice", "night": 1, "player": seat,
                "role": role}

    def sail(seat, target):
        return {"type": "SailorChoice", "night": 1, "player": seat,
                "target": target}
    wrong = {"type": "Empath", "night": 1, "player": 1, "count": 2}
    out = []
    for role in GROUP_1[:5] + ("Exorcist", "Chef"):
        out.append(pay([take(role)], quiet=[2]))
    for target in (6, 2):
        out.append(pay([take("Exorcist"), {"type": "ExorcistChoice",
                                           "night": 2, "player": 3,
                                           "target": target}], quiet=[2]))
    for role in ("Soldier", "Fool", "Pacifist", "Mayor", "Princess", "Chef"):
        out.append(pay([take(role)], events={3: ["N2"]}))
        out.append(pay([take(role)], events={3: ["S1"]}))
        out.append(pay([take(role)], events={2: ["S1"]}))
        out.append(pay([take(role)], events={1: ["X1"]}, quiet=[2]))
        out.append(pay([take(role), {"type": "PrincessNominated", "night": 1,
                                     "player": 3, "target": 0}],
                       events={0: ["X1"], 1: ["N2"]}))
    for rows in ([take("Sailor"), sail(2, 4), sail(3, 1), wrong],
                 [take("Sailor"), sail(2, 1), sail(3, 4), wrong],
                 [take("Sailor"), sail(3, 4), wrong],
                 [take("Chef"), sail(2, 1), wrong]):
        out.append(pay(rows, roles=TWO, days=(1,)))
    return out


class BothLanguagesAgree(SolverTest):

    def test_on_the_boards_of_group_one(self):
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
        js = json.loads(got.stdout)
        py = []
        for p in cases:
            r = app.run_solve(p)
            py.append(r.get("error") or r["valid"])
        self.assertEqual(js, py)
        self.assertIn(0, py)                # some of them refused
        self.assertTrue(any(v for v in py))  # and some of them kept


class TheSimulatorPlaysThem(SolverTest):
    """L, and the gate in small: games that must hold a Philosopher and
    every character of group 1."""

    def games(self, how_many=400, nights=4):
        import play_games
        import simulate
        for seed in range(how_many):
            rng = random.Random(seed)
            script = play_games.an_awkward_script(
                rng, must_have=("Philosopher",) + GROUP_1)
            n = [7, 8, 9, 10, 11][seed % 5]
            deal, heard = simulate.play(n, rng, nights=nights, script=script)
            yield seed, script, rng, deal, heard

    def test_a_philosopher_chooses_with_what_it_took(self):
        chose = set()
        for _seed, _script, _rng, deal, heard in self.games():
            for row in heard:
                if row.player in deal.philosophies \
                        and row.source_role in GROUP_1:
                    chose.add(row.source_role)
            for (key, _night), seats in deal.chose_by.items():
                if any(p in deal.philosophies for p in seats):
                    chose.add(key)
        self.assertTrue({"Sailor", "Innkeeper", "Exorcist", "Monk",
                         "Princess"} <= chose, chose)

    def test_it_chooses_before_a_courtier_on_the_first_night(self):
        # The real Courtier it took from is drunk at its own turn, so what
        # it names stays sober (found at the gate, XNINEB seed 1525).
        import simulate
        from test_experimental_9 import NINE_BMR
        seen = 0
        for seed in range(400):
            n = [7, 8, 9, 10, 11][seed % 5]
            deal, heard = simulate.play(n, random.Random(seed), nights=2,
                                        script=NINE_BMR)
            if "Courtier" not in deal.philosophies.values():
                continue
            for row in heard:
                if type(row).__name__ != "CourtierChoice" or row.night != 1 \
                        or deal.roles[row.player] != "Courtier":
                    continue
                with self.subTest(seed=seed):
                    self.assertEqual([c for night, _holder, c
                                      in deal.courtier_drunks
                                      if c == row.player], [])
                seen += 1
        self.assertGreater(seen, 0)

    def test_the_true_world_is_kept(self):
        import claims as C
        lost = []
        for seed, script, rng, deal, heard in self.games():
            if not set(deal.philosophies.values()) & set(GROUP_1):
                continue
            cl, wk, _ = C.claims_for(deal, rng, script=script)
            st = GameState(n_players=deal.n, script=script, claims=cl,
                           wakes=wk, infos=list(heard),
                           votes=dict(deal.votes),
                           nominations=dict(deal.nominations),
                           **deal.record())
            if S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        self.assertEqual(lost, [])


if __name__ == "__main__":
    unittest.main()
