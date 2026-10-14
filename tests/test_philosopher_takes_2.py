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

Group 2, the ones that kill: Gossip, Tinker, Moonchild, Lycanthrope,
Acrobat.

Group 3, the ones that disturb: Minstrel, Preacher, Goon, Puzzlemaster.
"""

import collections
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
        self.agree(_payloads())

    def test_on_the_boards_of_group_two(self):
        self.agree(_payloads_2())

    def test_on_the_boards_of_group_three(self):
        self.agree(_payloads_3())

    def test_on_the_boards_of_group_four(self):
        self.agree(_payloads_4())

    def test_on_the_boards_of_group_five(self):
        self.agree(_payloads_5())

    def test_on_the_boards_of_group_six(self):
        self.agree(_payloads_6())

    def agree(self, cases):
        import app
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


GROUP_2 = ("Gossip", "Tinker", "Moonchild", "Lycanthrope", "Acrobat")

KILL_IDS = ["philosopher", "gossip", "tinker", "moonchild", "lycanthrope",
            "acrobat", "chef", "empath", "washerwoman", "investigator",
            "monk", "drunk", "saint", "recluse", "poisoner", "scarletwoman",
            "spy", "imp"]
KILLERS = scripts.from_ids("Philosopher killers", KILL_IDS)
#     0       1         2               3              4
P7 = ["Chef", "Empath", "Investigator", "Philosopher", "Washerwoman",
      "Poisoner", "Imp"]                                     # 5, 6


def kcost(roles, rows=(), **kw):
    kw.setdefault("days_done", {1, 2})
    st = GameState(n_players=len(roles), script=KILLERS,
                   claims=dict(enumerate(roles)), infos=list(rows), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)), st)


class GroupTwoInTheSolver(SolverTest):
    """Two bodies on night 2 and an Imp that kills one: the other needs
    what the Philosopher took. With a Chef taken, nothing."""

    TWO = {"deaths": {3: ("N2",), 0: ("N2",)}}

    def test_its_tinker_may_simply_go(self):
        self.assertIsNotNone(kcost(R, [took("Tinker")], **self.TWO))
        self.assertIsNone(kcost(R, [took("Chef")], **self.TWO))

    def test_its_gossip_may_kill(self):
        dead = {"deaths": {1: ("N2",), 0: ("N2",)}}
        self.assertIsNotNone(kcost(R, [took("Gossip")], **dead))
        self.assertIsNone(kcost(R, [took("Chef")], **dead))

    def test_its_moonchild_takes_somebody_with_it(self):
        rows = [I.MoonchildChoice(2, 3, target=0)]
        dead = {"deaths": {3: ("E1",), 0: ("N2",), 1: ("N2",)},
                "executions": {1: 3}}
        self.assertIsNotNone(kcost(R, [took("Moonchild")] + rows, **dead))
        self.assertIsNone(kcost(R, [took("Chef")] + rows, **dead))

    def test_its_faux_paw_reads_evil(self):
        # An Empath between two good players told one.
        rows = [I.Empath(1, 1, count=1)]
        self.assertIsNotNone(kcost(R, [took("Lycanthrope")] + rows,
                                   days_done={1}))
        self.assertIsNone(kcost(R, [took("Chef")] + rows, days_done={1}))

    def test_its_acrobat_falls_with_a_poisoned_pick(self):
        rows = [I.AcrobatChoice(2, 3, target=1)]
        self.assertIsNotNone(kcost(P7, [took("Acrobat")] + rows,
                                   **self.TWO))
        self.assertIsNone(kcost(P7, [took("Chef")] + rows, **self.TWO))

    def test_two_lycanthropes_are_two_kills_by_name(self):
        # Beside the real one, the Philosopher's kill has its own name:
        # one name was one Lycanthrope firing twice.
        roles = list(R)
        roles[2] = "Lycanthrope"
        world = World(tuple(roles), (None,) * 7)
        st = GameState(n_players=7, script=KILLERS,
                       claims=dict(enumerate(roles)),
                       infos=[took("Lycanthrope")], days_done={1, 2})
        names = sorted(c.name for c in S.a_lycanthrope_may_kill(
            world, st, 2))
        self.assertEqual(names, ["Lycanthrope", "Lycanthrope (Philosopher)"])


def _payloads_2():
    def pay(rows, events, roles, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(roles)]
        return {"n_players": len(roles), "players": players, "infos": rows,
                "script": {"name": KILLERS.name, "characters": KILL_IDS},
                "days_done": list(days)}

    def take(role):
        return {"type": "PhilosopherChoice", "night": 1, "player": 3,
                "role": role}
    out = []
    for role in GROUP_2 + ("Chef",):
        out.append(pay([take(role)], {3: ["N2"], 0: ["N2"]}, R))
        out.append(pay([take(role), {"type": "MoonchildChoice", "night": 2,
                                     "player": 3, "target": 0}],
                       {3: ["X1"], 0: ["N2"], 1: ["N2"]}, R))
        out.append(pay([take(role), {"type": "Empath", "night": 1,
                                     "player": 1, "count": 1}], {}, R,
                       days=(1,)))
        out.append(pay([take(role), {"type": "Acrobat", "night": 2,
                                     "player": 3, "target": 1}],
                       {3: ["N2"], 0: ["N2"]}, P7))
    return out


GROUP_3 = ("Minstrel", "Preacher", "Goon", "Puzzlemaster")

DISTURB_IDS = ["philosopher", "minstrel", "preacher", "goon", "puzzlemaster",
               "chef", "empath", "washerwoman", "investigator", "monk",
               "drunk", "saint", "recluse", "poisoner", "scarletwoman",
               "spy", "imp"]
DISTURBERS = scripts.from_ids("Philosopher disturbers", DISTURB_IDS)
#      0       1         2              3              4
G7 = ["Chef", "Empath", "Philosopher", "Investigator", "Washerwoman",
      "ScarletWoman", "Imp"]                                 # 5, 6


def dcost(roles, rows=(), **kw):
    kw.setdefault("days_done", {1, 2})
    st = GameState(n_players=len(roles), script=DISTURBERS,
                   claims=dict(enumerate(roles)), infos=list(rows), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)), st)


class GroupThreeInTheSolver(SolverTest):
    """An Empath between two good players, told something else: what
    the Philosopher took has to explain it. With a Chef taken, nothing."""

    def test_its_minstrel_drunks_the_table(self):
        rows = [I.Empath(2, 1, count=2)]
        hanged = {"deaths": {5: ("D1",)}, "executions": {1: 5}}
        self.assertIsNotNone(dcost(R, [took("Minstrel")] + rows, **hanged))
        self.assertIsNone(dcost(R, [took("Chef")] + rows, **hanged))

    def test_its_preacher_silences_a_minion(self):
        rows = [took("Preacher"), I.PreacherChoice(1, 3, target=5)]
        st = GameState(n_players=7, script=DISTURBERS,
                       claims=dict(enumerate(P7)), infos=rows,
                       days_done={1, 2})
        got = S.a_preacher_silences_its_minions(
            World(tuple(P7), (None,) * 7), st, 2)
        self.assertEqual([(x.name, sorted(x.seats), x.actor) for x in got],
                         [("Preacher", [5], 3)])

    def test_its_goon_may_be_on_either_side(self):
        # Ruling G: the side changes. The Empath beside it may count it.
        rows = [I.Empath(2, 1, count=1)]
        self.assertIsNotNone(dcost(G7, [took("Goon", 2)] + rows))
        self.assertIsNone(dcost(G7, [took("Chef", 2)] + rows))

    def test_its_puzzlemaster_keeps_one_drunk(self):
        rows = [I.Empath(1, 1, count=2)]
        self.assertIsNotNone(dcost(R, [took("Puzzlemaster")] + rows,
                                   days_done={1}))
        self.assertIsNone(dcost(R, [took("Chef")] + rows, days_done={1}))


def _payloads_3():
    def pay(rows, events, roles, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(roles)]
        return {"n_players": len(roles), "players": players, "infos": rows,
                "script": {"name": DISTURBERS.name,
                           "characters": DISTURB_IDS},
                "days_done": list(days)}

    def take(role, seat=3):
        return {"type": "PhilosopherChoice", "night": 1, "player": seat,
                "role": role}

    def empath(night, count):
        return {"type": "Empath", "night": night, "player": 1,
                "count": count}
    out = []
    for role in GROUP_3 + ("Chef",):
        out.append(pay([take(role), empath(2, 2)], {5: ["X1"]}, R))
        out.append(pay([take(role), {"type": "PreacherChoice", "night": 1,
                                     "player": 3, "target": 5},
                        empath(2, 2)], {}, P7))
        out.append(pay([take(role, 2), empath(2, 1)], {}, G7))
        out.append(pay([take(role), empath(1, 2)], {}, R, days=(1,)))
    return out


GROUP_4 = ("Farmer", "Professor", "Huntsman", "Pixie", "CultLeader", "Ogre")

CHANGE_IDS = ["philosopher", "farmer", "professor", "huntsman", "pixie",
              "cultleader", "ogre", "damsel", "chef", "empath",
              "washerwoman", "investigator", "monk", "drunk", "saint",
              "recluse", "poisoner", "scarletwoman", "spy", "imp"]
CHANGERS = scripts.from_ids("Philosopher changers", CHANGE_IDS)
#      0       1         2              3                4
CL = ["Chef", "Empath", "Philosopher", "ScarletWoman", "Washerwoman",
      "Investigator", "Imp"]                                  # 5, 6


def cboard(roles, rows=(), **kw):
    kw.setdefault("days_done", {1, 2})
    st = GameState(n_players=len(roles), script=CHANGERS,
                   claims=dict(enumerate(roles)), infos=list(rows), **kw)
    return World(tuple(roles), (None,) * len(roles)), st


def ccost(roles, rows=(), **kw):
    return S.explanation_cost(*cboard(roles, rows, **kw))


class GroupFourInTheSolver(SolverTest):
    """What the Philosopher took changes a character or a side. With a
    Chef taken, nothing changes."""

    def test_its_professor_raises_the_dead(self):
        back = {"deaths": {0: ("N2",)}, "resurrections": {0: ("N3",)},
                "days_done": {1, 2, 3}}
        self.assertIsNotNone(ccost(R, [took("Professor")], **back))
        self.assertIsNone(ccost(R, [took("Chef")], **back))

    def test_the_real_professor_raises_its_philosopher(self):
        # Sober while it chose, drunk again once the Philosopher stood up
        # (gate seed 2478).
        roles = list(R)
        roles[2] = "Professor"
        back = {"deaths": {3: ("N2",)}, "resurrections": {3: ("N3",)},
                "days_done": {1, 2, 3}}
        self.assertIsNotNone(ccost(roles, [took("Professor")], **back))

    def test_whoever_its_professor_raised_slept_through_earlier_turns(self):
        # An Exorcist raised on night two was dead at its own turn, which
        # comes before the Professor's (XNINEB seed 881).
        from botc import waking
        roles = list(R)
        roles[0] = "Exorcist"
        back = {"deaths": {0: ("E1",)}, "resurrections": {0: ("N2",)}}
        world, st = cboard(roles, [took("Professor")], **back)
        self.assertEqual(waking._came_back_tonight(world, st, 0, 2),
                         waking.ASLEEP)
        world, st = cboard(roles, [took("Chef")], **back)
        self.assertIsNone(waking._came_back_tonight(world, st, 0, 2))

    def test_its_farmer_hands_the_character_on(self):
        from botc.worlds import Change
        world, st = cboard(R, [took("Farmer")], deaths={3: ("N2",)})
        stories = [c for c, _w in S.a_farmer_hands_it_on(world, st)]
        self.assertIn((Change("D2", 0, "Farmer", None),), stories)
        world, st = cboard(R, [took("Chef")], deaths={3: ("N2",)})
        self.assertEqual(S.a_farmer_hands_it_on(world, st), [((), 1.0)])

    def test_its_huntsman_finds_the_damsel(self):
        roles = list(R) + ["Damsel"]            # eight: one Outsider
        rows = [I.HuntsmanChoice(2, 3, target=7)]
        world, st = cboard(roles, [took("Huntsman")] + rows)
        found = S.a_huntsman_finds_the_damsel(world, st)
        self.assertTrue(any(c and c[0].seat == 7 for c, _w in found))
        self.assertIsNotNone(S.explanation_cost(world, st))
        world, st = cboard(roles, [took("Chef")] + rows)
        self.assertEqual(S.a_huntsman_finds_the_damsel(world, st),
                         [((), 1.0)])

    def test_its_pixie_learns_one_in_play(self):
        self.assertIsNotNone(ccost(R, [took("Pixie"), I.PixieLearned(
            1, 3, role="Empath")], days_done={1}))
        self.assertIsNone(ccost(R, [took("Pixie"), I.PixieLearned(
            1, 3, role="Monk")], days_done={1}))

    def test_its_ogre_takes_the_side_it_chose(self):
        # Ruling G: it chooses the night it took it. The Empath beside it
        # counts it.
        rows = [I.OgreChoice(1, 2, target=3), I.Empath(2, 1, count=1)]
        self.assertIsNotNone(ccost(CL, [took("Ogre", 2)] + rows))
        self.assertIsNone(ccost(CL, [took("Chef", 2)] + rows))

    def test_its_cult_leader_takes_a_neighbours_side(self):
        rows = [I.Empath(2, 1, count=1)]
        self.assertIsNotNone(ccost(CL, [took("CultLeader", 2)] + rows))
        self.assertIsNone(ccost(CL, [took("Chef", 2)] + rows))


def _payloads_4():
    def pay(rows, events, roles, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(roles)]
        return {"n_players": len(roles), "players": players, "infos": rows,
                "script": {"name": CHANGERS.name, "characters": CHANGE_IDS},
                "days_done": list(days)}

    def take(role, seat=3):
        return {"type": "PhilosopherChoice", "night": 1, "player": seat,
                "role": role}
    prof = list(R)
    prof[2] = "Professor"
    damsel = list(R) + ["Damsel"]        # eight players: one Outsider
    out = []
    for role in GROUP_4 + ("Chef",):
        out.append(pay([take(role)], {0: ["N2", "R3"]}, R, days=(1, 2, 3)))
        out.append(pay([take(role)], {3: ["N2", "R3"]}, prof,
                       days=(1, 2, 3)))
        out.append(pay([take(role)], {3: ["N2"]}, R))
        out.append(pay([take(role), {"type": "HuntsmanChoice", "night": 2,
                                     "player": 3, "target": 7}], {}, damsel))
        out.append(pay([take(role), {"type": "PixieLearned", "night": 1,
                                     "player": 3, "role": "Monk"}], {}, R,
                       days=(1,)))
        out.append(pay([take(role, 2), {"type": "OgreChoice", "night": 1,
                                        "player": 2, "target": 3},
                        {"type": "Empath", "night": 2, "player": 1,
                         "count": 1}], {}, CL))
    return out


GROUP_5 = ("Slayer", "Virgin", "Golem", "Alsaahir", "Zealot", "Butler")

DAY_IDS = ["philosopher", "slayer", "virgin", "golem", "alsaahir", "zealot",
           "butler", "chef", "empath", "washerwoman", "investigator", "monk",
           "drunk", "saint", "recluse", "poisoner", "scarletwoman", "spy",
           "imp", "po"]
BY_DAY = scripts.from_ids("Philosopher by day", DAY_IDS)


def dycost(roles, rows=(), **kw):
    kw.setdefault("days_done", {1})
    st = GameState(n_players=len(roles), script=BY_DAY,
                   claims=dict(enumerate(roles)), infos=list(rows), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)), st)


class GroupFiveInTheSolver(SolverTest):
    """What the town watched in daylight needs what the Philosopher took.
    With a Chef taken, nothing fits. The Butler is not modelled for
    anybody, so there is nothing for it to do."""

    def test_its_slayer_shot_lands(self):
        rows = [I.SlayerShot(1, 3, target=6, died=True)]
        dead = {"deaths": {6: ("D1",)}}
        self.assertIsNotNone(dycost(R, [took("Slayer")] + rows, **dead))
        self.assertIsNone(dycost(R, [took("Chef")] + rows, **dead))

    def test_the_real_slayer_it_drunk_misses(self):
        roles = list(R)
        roles[2] = "Slayer"
        rows = [I.SlayerShot(1, 2, target=6, died=True)]
        dead = {"deaths": {6: ("D1",)}}
        self.assertIsNone(dycost(roles, [took("Slayer")] + rows, **dead))
        self.assertIsNotNone(dycost(roles, [took("Chef")] + rows, **dead))

    def test_its_virgin_takes_the_nominator(self):
        rows = [I.VirginNomination(1, 3, nominator=0, triggered=True)]
        hanged = {"deaths": {0: ("E1",)}}
        self.assertIsNotNone(dycost(R, [took("Virgin")] + rows, **hanged))
        self.assertIsNone(dycost(R, [took("Chef")] + rows, **hanged))

    def test_its_golem_nominee_dies(self):
        rows = [I.GolemNomination(1, 3, target=0, died=True)]
        dead = {"deaths": {0: ("D1",)}}
        self.assertIsNotNone(dycost(R, [took("Golem")] + rows, **dead))
        self.assertIsNone(dycost(R, [took("Chef")] + rows, **dead))

    def test_its_alsaahir_wins(self):
        rows = [I.AlsaahirGuess(1, 3, demons=frozenset({6}),
                                minions=frozenset({5}), won=True)]
        self.assertIsNotNone(dycost(R, [took("Alsaahir")] + rows,
                                    game_over=True))
        self.assertIsNone(dycost(R, [took("Chef")] + rows, game_over=True))

    def test_its_zealot_must_vote(self):
        kept_down = {"votes": {1: {0, 1, 2}}, "nominations": {1: {0}}}
        self.assertIsNone(dycost(R, [took("Zealot")], **kept_down))
        self.assertIsNotNone(dycost(R, [took("Chef")], **kept_down))

    def test_a_landed_shot_pins_the_shooter_only(self):
        st = GameState(n_players=7, script=BY_DAY, claims=dict(enumerate(R)),
                       infos=[took("Slayer"),
                              I.SlayerShot(1, 3, target=6, died=True)],
                       deaths={6: ("D1",)}, days_done={1})
        pinned = S.forced_roles(st)
        self.assertEqual(pinned[3], {"Slayer", "Philosopher"})
        # The Demon it hit may be a Minion that caught the star.
        self.assertNotIn(6, pinned)


def _payloads_5():
    def pay(rows, events, roles=R, days=(1,), **more):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(roles)]
        return {"n_players": len(roles), "players": players, "infos": rows,
                "script": {"name": BY_DAY.name, "characters": DAY_IDS},
                "days_done": list(days), **more}

    def take(role, seat=3):
        return {"type": "PhilosopherChoice", "night": 1, "player": seat,
                "role": role}
    po = list(R)
    po[6] = "Po"
    out = []
    for role in GROUP_5 + ("Chef",):
        out.append(pay([take(role), {"type": "SlayerShot", "night": 1,
                                     "player": 3, "target": 6,
                                     "died": True}], {6: ["D1"]}))
        out.append(pay([take(role), {"type": "SlayerShot", "night": 1,
                                     "player": 3, "target": 6,
                                     "died": True}], {6: ["D1"]}, po))
        out.append(pay([take(role), {"type": "VirginNomination", "night": 1,
                                     "player": 3, "nominator": 0,
                                     "triggered": True}], {0: ["X1"]}))
        out.append(pay([take(role), {"type": "GolemNomination", "night": 1,
                                     "player": 3, "target": 0,
                                     "died": True}], {0: ["D1"]}))
    return out


GROUP_6 = ("Saint", "Recluse", "Damsel", "Grandmother", "King", "Choirboy")
TOKENS = ("Drunk", "Lunatic")

END_IDS = ["philosopher", "saint", "recluse", "damsel", "grandmother",
           "king", "choirboy", "huntsman", "drunk", "lunatic", "heretic",
           "politician", "chef", "empath", "washerwoman", "investigator",
           "librarian", "monk", "scarletwoman", "baron", "imp"]
AT_THE_END = scripts.from_ids("Philosopher at the end", END_IDS)


def ecost(roles, rows=(), claims=None, **kw):
    kw.setdefault("days_done", {1, 2})
    st = GameState(n_players=len(roles), script=AT_THE_END,
                   claims=dict(enumerate(claims or roles)),
                   infos=list(rows), **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)), st)


class GroupSixInTheSolver(SolverTest):
    """The end of the game and registering. With a Chef taken, the board
    reads the other way. Heretic and Politician are not modelled for
    anybody, so there is nothing for them to do."""

    def test_its_saint_executed_ends_the_game(self):
        # Ruling D: the game went on, so it cannot have been working.
        hanged = {"deaths": {3: ("E1",)}}
        self.assertIsNone(ecost(R, [took("Saint")], **hanged))
        self.assertIsNotNone(ecost(R, [took("Chef")], **hanged))

    def test_its_damsel_guessed_by_a_minion(self):
        # O: the Minion's first guess landed and the game went on.
        rows = [I.DamselGuess(1, 5, target=3)]
        self.assertIsNone(ecost(R, [took("Damsel")] + rows))
        self.assertIsNotNone(ecost(R, [took("Chef")] + rows))

    def test_its_damsel_is_found_by_the_huntsman(self):
        # P: it becomes a Townsfolk not in play.
        roles = list(R)
        roles[0] = "Huntsman"
        rows = [I.HuntsmanChoice(2, 0, target=3)]
        world = World(tuple(roles), (None,) * 7)
        st = GameState(n_players=7, script=AT_THE_END,
                       claims=dict(enumerate(roles)),
                       infos=[took("Damsel")] + rows, days_done={1, 2})
        found = S.a_huntsman_finds_the_damsel(world, st)
        self.assertTrue(any(c and c[0].seat == 3 for c, _w in found))

    def test_its_grandmother_grieves(self):
        rows = [I.GrandmotherInfo(1, 3, target=0, role="Chef")]
        both = {"deaths": {0: ("N2",), 3: ("N2",)}}
        self.assertIsNotNone(ecost(R, [took("Grandmother")] + rows, **both))
        self.assertIsNone(ecost(R, [took("Chef")] + rows, **both))

    def test_its_king_killed_tells_the_choirboy(self):
        # Q: the Choirboy learns the Demon when the Demon kills it.
        roles = list(R)
        roles[0] = "Choirboy"
        rows = [I.ChoirboyInfo(2, 0, target=6)]
        dead = {"deaths": {3: ("N2",)}}
        self.assertIsNotNone(ecost(roles, [took("King")] + rows, **dead))
        self.assertIsNone(ecost(roles, [took("Chef")] + rows, **dead))

    def test_its_recluse_may_read_evil(self):
        # N: the Empath beside it counts it.
        rows = [I.Empath(1, 1, count=1)]
        self.assertIsNotNone(ecost(G7, [took("Recluse", 2)] + rows,
                                   days_done={1}))
        self.assertIsNone(ecost(G7, [took("Chef", 2)] + rows,
                                days_done={1}))

    def test_its_drunk_lives_by_a_townsfolk(self):
        # I and S: it claims the Librarian it was shown, and what it was
        # told as one is made up.
        claims = list(R)
        claims[3] = "Librarian"
        rows = [I.Librarian(1, 3, a=0, b=1, role="Drunk")]
        st = GameState(n_players=7, script=AT_THE_END,
                       claims=dict(enumerate(claims)),
                       infos=[took("Drunk")] + rows, days_done={1})
        self.assertEqual(st.dealt_claims()[3], "Philosopher")
        world = World(tuple(R), (None,) * 7)
        self.assertEqual(S.explanation_cost(world, st), 1.0)

    def test_its_lunatic_may_have_woken(self):
        from botc import waking
        world = World(tuple(R), (None,) * 7)
        st = GameState(n_players=7, script=AT_THE_END,
                       claims=dict(enumerate(R)), infos=[took("Lunatic")],
                       days_done={1, 2})
        self.assertTrue(waking.uncertain(world, st, 3, 2))


def _payloads_6():
    def pay(rows, events, roles=R, days=(1, 2), claims=None):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims or roles)]
        return {"n_players": len(roles), "players": players, "infos": rows,
                "script": {"name": AT_THE_END.name, "characters": END_IDS},
                "days_done": list(days)}

    def take(role, seat=3):
        return {"type": "PhilosopherChoice", "night": 1, "player": seat,
                "role": role}
    choir = list(R)
    choir[0] = "Choirboy"
    librarian = list(R)
    librarian[3] = "Librarian"
    out = []
    for role in GROUP_6 + TOKENS + ("Chef",):
        out.append(pay([take(role)], {3: ["X1"]}))
        out.append(pay([take(role), {"type": "DamselGuess", "night": 1,
                                     "player": 5, "target": 3}], {}))
        out.append(pay([take(role), {"type": "GrandmotherInfo", "night": 1,
                                     "player": 3, "target": 0,
                                     "role": "Chef"}],
                       {0: ["N2"], 3: ["N2"]}))
        out.append(pay([take(role), {"type": "ChoirboyInfo", "night": 2,
                                     "player": 0, "target": 6}],
                       {3: ["N2"]}, choir))
        out.append(pay([take(role, 2), {"type": "Empath", "night": 1,
                                        "player": 1, "count": 1}], {}, G7,
                       days=(1,)))
        out.append(pay([take(role), {"type": "Librarian", "night": 1,
                                     "player": 3, "a": 0, "b": 1,
                                     "role": "Drunk"}], {}, R, days=(1,),
                       claims=librarian))
    return out


class TheSimulatorPlaysThem(SolverTest):
    """L, and the gate in small: games that must hold a Philosopher and
    every character of group 1."""

    def games(self, how_many=400, nights=4, group=GROUP_1):
        import play_games
        import simulate
        for seed in range(how_many):
            rng = random.Random(seed)
            script = play_games.an_awkward_script(
                rng, must_have=("Philosopher",) + group)
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

    def test_a_philosopher_kills_with_what_it_took(self):
        rows, tinkers = set(), 0
        for _seed, _script, _rng, deal, heard in self.games(group=GROUP_2):
            for row in heard:
                if row.player in deal.philosophies \
                        and row.source_role in GROUP_2:
                    rows.add(row.source_role)
            tinkers += sum(1 for p, took in deal.philosophies.items()
                           if took == "Tinker" and p in deal.deaths)
        self.assertTrue({"Acrobat", "Lycanthrope", "Moonchild"} <= rows,
                        rows)
        self.assertGreater(tinkers, 0)

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
        self.kept(GROUP_1)

    def test_the_true_world_is_kept_with_group_two(self):
        self.kept(GROUP_2)

    def test_the_true_world_is_kept_with_group_three(self):
        self.kept(GROUP_3)

    def test_a_philosopher_disturbs_with_what_it_took(self):
        sermons = guesses = turned = 0
        for _seed, _script, _rng, deal, heard in self.games(group=GROUP_3):
            for row in heard:
                if row.player in deal.philosophies:
                    sermons += type(row).__name__ == "PreacherChoice"
                    guesses += type(row).__name__ == "PuzzlemasterGuess"
            turned += sum(1 for _at, seat, _why, _side in deal.side_changes
                          if deal.philosophies.get(seat) == "Goon")
        self.assertGreater(sermons, 0)
        self.assertGreater(guesses, 0)
        self.assertGreater(turned, 0)

    def test_the_true_world_is_kept_with_group_four(self):
        self.kept(GROUP_4)

    def test_a_philosopher_changes_with_what_it_took(self):
        rows = collections.Counter()
        for _seed, _script, _rng, deal, heard in self.games(group=GROUP_4):
            for row in heard:
                if row.player in deal.philosophies:
                    rows[type(row).__name__] += 1
        for name in ("OgreChoice", "PixieLearned", "HuntsmanChoice"):
            self.assertGreater(rows[name], 0, rows)

    def test_the_true_world_is_kept_with_group_five(self):
        self.kept(GROUP_5)

    def test_a_philosopher_acts_by_day_with_what_it_took(self):
        rows = collections.Counter()
        for _seed, _script, _rng, deal, heard in self.games(group=GROUP_5):
            for row in list(heard) + list(getattr(deal, "day_heard", [])):
                if row.player in deal.philosophies:
                    rows[type(row).__name__] += 1
        for name in ("GolemNomination", "AlsaahirGuess"):
            self.assertGreater(rows[name], 0, rows)

    def test_the_true_world_is_kept_with_group_six(self):
        self.kept(GROUP_6)

    def test_the_true_world_is_kept_with_the_tokens(self):
        self.kept(TOKENS)

    def test_a_philosopher_ends_and_registers_with_what_it_took(self):
        rows = collections.Counter()
        for _seed, _script, _rng, deal, heard in self.games(group=GROUP_6):
            for row in heard:
                if row.player in deal.philosophies:
                    rows[type(row).__name__] += 1
        for name in ("GrandmotherInfo", "KingInfo"):
            self.assertGreater(rows[name], 0, rows)

    def test_a_philosopher_lives_by_the_token_it_was_shown(self):
        shown = 0
        for _seed, _script, _rng, deal, _heard in self.games(group=TOKENS):
            for seat, took_ in deal.philosophies.items():
                if took_ in TOKENS and deal.phil_token.get(seat):
                    shown += 1
                    if took_ == "Drunk":
                        self.assertEqual(deal.apparent(seat),
                                         deal.phil_token[seat])
        self.assertGreater(shown, 5)

    def kept(self, group):
        import claims as C
        lost = []
        for seed, script, rng, deal, heard in self.games(group=group):
            if not set(deal.philosophies.values()) & set(group):
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
