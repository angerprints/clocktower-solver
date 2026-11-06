"""The Alchemist with the Summoner's ability (05.11.2026,
claude/alchemist-beschwoerer-lesarten.md, claude/alchemist-5.md).

Their jinx: "The Alchemist-Summoner does not get bluffs, and chooses
which Demon but not which player. If they die before this happens, evil
wins. [No Demon]". Patrick's answers of 05.11.2026:

  M  "[No Demon]", a Townsfolk more, as for the real one: no Demon on the
     first two nights.
  N  The Storyteller makes any living player the Demon — a good one, a
     Minion, the Alchemist itself; somebody dead only as a Zombuul.
  O  Drunk or poisoned on the third night: no Demon, good wins, as for
     the real one.
"""
import json
import pathlib
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc import waking                           # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import (World, alchemist_summoner, enumerate_worlds,  # noqa
                         lil_monsta_world, summoner_seat, summoner_world)

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["alchemist", "summoner", "poisoner", "scarletwoman", "imp", "pukka",
       "zombuul", "chef", "empath", "fortuneteller", "monk", "washerwoman",
       "investigator", "soldier", "clockmaker", "chambermaid"]
AS = scripts.from_ids("Alchemist-Beschwörer", IDS)
#    0       1         2               3       4              5
R = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman", "Alchemist",
     "Poisoner"]
C = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman", "Alchemist",
     "Soldier"]


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def state(rows=(), days=(1, 2), claims=C, **kw):
    return GameState(n_players=len(claims), script=AS,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def cost(rows=(), roles=R, **kw):
    return S.explanation_cost(world(roles), state(rows, **kw))


class TheBag(SolverTest):

    def test_no_demon_and_a_townsfolk_more(self):
        worlds = enumerate_worlds(7, dict(enumerate(C)), script=AS)
        dealt = {(tuple(sorted(r for r in w.roles
                               if CHARACTERS[r].team in ("minion",
                                                         "demon"))),
                  "Alchemist" in w.roles)
                 for w in worlds}
        # One Minion, no Demon, the Alchemist dealt: its Summoner's.
        self.assertIn((("Poisoner",), True), dealt)
        # Never without an Alchemist and without a Summoner.
        self.assertNotIn((("Poisoner",), False), dealt)

    def test_told_apart_from_lil_monsta(self):
        self.assertEqual(alchemist_summoner(world()), 5)
        self.assertEqual(summoner_seat(world()), 5)
        self.assertTrue(summoner_world(world()))
        self.assertFalse(lil_monsta_world(world()))
        # Lil' Monsta's bag: a Minion more.
        monsta = ["Chef", "Empath", "FortuneTeller", "Monk", "Alchemist",
                  "ScarletWoman", "Poisoner"]
        self.assertIsNone(alchemist_summoner(world(monsta)))
        self.assertTrue(lil_monsta_world(world(monsta)))
        # And a world with a Demon is neither.
        imp = R[:4] + ["Imp", "Alchemist", "Poisoner"]
        self.assertIsNone(alchemist_summoner(world(imp)))
        self.assertFalse(summoner_world(world(imp)))

    def test_only_the_summoners_ability(self):
        got = {way[0].gift for way, _c in
               S.alchemist_offers(world(), state(), 5)}
        self.assertEqual(got, {"Summoner"})
        imp = R[:4] + ["Imp", "Alchemist", "Poisoner"]
        got = {way[0].gift for way, _c in
               S.alchemist_offers(world(imp), state(), 5)}
        self.assertNotIn("Summoner", got)


class BesideLilMonsta(SolverTest):
    """Found with this stage (05.11.2026): an Alchemist dealt beside Lil'
    Monsta had no ability at all — its bag was asked for a Lil' Monsta
    among the dealt characters, which nobody is dealt."""

    SCRIPT = scripts.from_ids("Alchemist-Monsta", IDS + ["lilmonsta"])
    MONSTA = ["Chef", "Empath", "FortuneTeller", "Monk", "Alchemist",
              "ScarletWoman", "Poisoner"]

    def test_it_has_an_ability(self):
        st = GameState(n_players=7, script=self.SCRIPT,
                       claims=dict(enumerate(C)), infos=[], days_done={1})
        got = {way[0].gift for way, _c in
               S.alchemist_offers(world(self.MONSTA), st, 4)}
        self.assertTrue(got)
        self.assertNotIn("Summoner", got)

    def test_both_languages_agree(self):
        case = {"n_players": 7,
                "players": [{"claim": c, "events": []} for c in C],
                "infos": [], "days_done": [1],
                "script": {"name": "Alchemist-Monsta",
                           "characters": IDS + ["lilmonsta"]}}
        compare(self, case)


class NoDemonYet(SolverTest):

    def test_nobody_dies_before_the_third_night(self):
        self.assertIsNotNone(cost(quiet_nights={2}))
        self.assertIsNone(cost(deaths={1: ("N2",)}))
        self.assertIsNotNone(cost(deaths={1: ("N3",)}, days=(1, 2, 3)))


class WhoBecomesIt(SolverTest):
    """N: any living player, the Alchemist and the Minion too."""

    def test_any_living_player(self):
        st = state(days=(1, 2, 3))
        st._final_phase_held = st.final_phase()
        made = {c.seat for way in S.summon_options(world(), st)
                for c in way if type(c).__name__ == "Summoned"}
        self.assertEqual(made, set(range(7)))

    def test_a_dead_one_only_as_a_zombuul(self):
        st = state(days=(1, 2, 3), executions={1: 0}, deaths={0: ("D1",)})
        st._final_phase_held = st.final_phase()
        kinds = {c.role for way in S.summon_options(world(), st)
                 for c in way if type(c).__name__ == "Summoned"
                 and c.seat == 0}
        self.assertEqual(kinds, {"Zombuul"})


class NoDemonComes(SolverTest):

    def test_dead_before_its_turn_ends_the_game(self):
        # Their jinx: evil wins there — and the game is over either way.
        hanged = dict(executions={1: 5}, deaths={5: ("D1",)})
        self.assertIsNone(cost(days=(1, 2), **hanged))
        self.assertIsNotNone(cost(days=(1,), game_over=True, **hanged))

    def test_drunk_on_its_turn_ends_it_at_dawn(self):
        # O: poisoned on the third night, no Demon, good wins at dawn.
        self.assertIsNotNone(cost(days=(1, 2), quiet_nights={2, 3},
                                  game_over=True))
        st = state(days=(1, 2), quiet_nights={2, 3}, game_over=True)
        st._final_phase_held = st.final_phase()
        ended = [w for w in S.summon_options(world(), st)
                 if any(type(c).__name__ == "NotSummoned" for c in w)]
        self.assertEqual(len(ended), 1)
        # Its failure is a demand: with nobody to poison it, that way
        # does not fit.
        sw = world(R[:6] + ["ScarletWoman"])
        st._summoned = ended[0]
        try:
            got, _ = S._best_story_told(sw, st, None, None)
        finally:
            st._summoned = None
        self.assertIsNone(got)
        st._summoned = ended[0]
        try:
            got, _ = S._best_story_told(world(), st, None, None)
        finally:
            st._summoned = None
        self.assertIsNotNone(got)


class ItWakes(SolverTest):
    """No bluffs on the first night (their jinx); woken on the night the
    Demon comes."""

    def test_not_on_the_first_night(self):
        rule = waking.CONDITION_RULES["Summoner"]
        self.assertFalse(rule(world(), state(), 5, 1))
        self.assertTrue(rule(world(), state(), 5, 3))
        real = R[:5] + ["Monk", "Summoner"]
        self.assertTrue(rule(world(real), state(), 6, 1))


class APhilosophersSecondDemon(SolverTest):
    """Patrick, 06.11.2026: a Philosopher that takes the Alchemist may get
    the Summoner's ability. A Demon is in play already: holding it on the
    third night, the Storyteller makes a living player a second Demon
    then. Taken later, it does nothing."""

    SCRIPT = scripts.from_ids("Philosoph-Beschwörer",
                              IDS + ["philosopher"])
    #        0       1         2               3       4
    ROLES = ["Chef", "Empath", "FortuneTeller", "Philosopher", "Imp",
             "Washerwoman", "Poisoner"]
    CLAIMS = ["Chef", "Empath", "FortuneTeller", "Philosopher", "Monk",
              "Washerwoman", "Soldier"]
    TOOK = I.PhilosopherChoice(1, 3, role="Alchemist")
    HAS = I.AlchemistHas(1, 3, role="Summoner")

    def state(self, rows=(), days=(1, 2, 3), **kw):
        return GameState(n_players=7, script=self.SCRIPT,
                         claims=dict(enumerate(self.CLAIMS)),
                         infos=[self.TOOK] + list(rows),
                         days_done=set(days), **kw)

    def test_it_may_have_it(self):
        got = {way[0].gift for way, _c in
               S.alchemist_offers(world(self.ROLES), self.state(), 3, "N1")}
        self.assertIn("Summoner", got)

    def test_a_second_demon_on_the_third_night(self):
        st = self.state([self.HAS])
        st._final_phase_held = st.final_phase()
        tl = S.Timeline(world(self.ROLES),
                        (S.alchemist_gift_change(3, "Summoner", "N1"),))
        made = {(c.phase, c.seat, c.role if c.phase == "N2" else None)
                for way, _c in S.a_hatted_summoner_summons(tl, st)
                for c in way if type(c).__name__ == "Summoned"}
        # Any living player, on the third night — a Pukka on the second:
        # the Demon and the Philosopher too.
        self.assertEqual(made, {(ph, p, demon) for p in range(7)
                                for ph, demon in (("N3", None),
                                                  ("N2", "Pukka"))})
        # Two deaths on the third night: the second Demon's night.
        two = dict(deaths={0: ("N3",), 1: ("N3",)})
        self.assertIsNotNone(S.explanation_cost(world(self.ROLES),
                                                self.state([self.HAS],
                                                           **two)))

    def test_taken_after_the_third_night_it_does_nothing(self):
        late = I.PhilosopherChoice(4, 3, role="Alchemist")
        st = GameState(n_players=7, script=self.SCRIPT,
                       claims=dict(enumerate(self.CLAIMS)),
                       infos=[late, I.AlchemistHas(4, 3, role="Summoner")],
                       days_done={1, 2, 3, 4})
        st._final_phase_held = st.final_phase()
        tl = S.Timeline(world(self.ROLES),
                        (S.alchemist_gift_change(3, "Summoner", "N4"),))
        ways = S.a_hatted_summoner_summons(tl, st)
        self.assertEqual(ways, [((), 1.0)])

    def test_both_languages_agree(self):
        case = {"n_players": 7,
                "players": [{"claim": c, "events": []}
                            for c in self.CLAIMS],
                "infos": [{"type": "PhilosopherChoice", "night": 1,
                           "player": 3, "role": "Alchemist"},
                          {"type": "AlchemistHas", "night": 1, "player": 3,
                           "role": "Summoner"}],
                "deaths": {"0": ["N3"], "1": ["N3"]},
                "days_done": [1, 2, 3],
                "script": {"name": "Philosoph-Beschwörer",
                           "characters": IDS + ["philosopher"]}}
        compare(self, case)


class TheClockmaker(SolverTest):
    """Patrick, 06.11.2026: the Alchemist is neither Minion nor Demon and
    registers as neither. No Demon on the first night: 0."""

    def test_learns_nothing_but_zero(self):
        roles = ["Clockmaker"] + R[1:6] + ["ScarletWoman"]
        claims = ["Clockmaker"] + C[1:]
        for count, fits in ((0, True), (1, False), (2, False)):
            got = cost([I.ClockmakerInfo(1, 0, count=count)],
                       roles=roles, claims=claims)
            self.assertEqual(got is not None, fits, count)

    def test_both_languages_agree(self):
        claims = ["Clockmaker"] + C[1:]
        case = {"n_players": 7,
                "players": [{"claim": c, "events": []} for c in claims],
                "infos": [{"type": "ClockmakerInfo", "night": 1,
                           "player": 0, "count": 0}],
                "days_done": [1],
                "script": {"name": "Alchemist-Beschwörer",
                           "characters": IDS}}
        compare(self, case)


def compare(test, case):
    """Python and JavaScript give the same shares on this board: the
    Python answer."""
    import app
    script = ("import {solveBoard} from './js/api.mjs';"
              "const p=JSON.parse(process.argv[1]);"
              "const r=solveBoard(p);"
              "console.log(JSON.stringify(r.error ? r.error : {"
              " valid: r.valid,"
              " rows: r.rows.map(x => [x.evil_pct, x.demon_pct])}));")
    got = subprocess.run(["node", "--input-type=module", "-e", script,
                          json.dumps(case)], cwd=ROOT,
                         capture_output=True, text=True, timeout=900)
    test.assertEqual(got.returncode, 0, got.stderr)
    js = json.loads(got.stdout)
    py = app.run_solve(case)
    test.assertNotIn("error", py)
    test.assertNotIsInstance(js, str, js)
    test.assertGreater(py["valid"], 0)
    test.assertEqual(js["valid"], py["valid"])
    for (je, jd), row in zip(js["rows"], py["rows"]):
        test.assertAlmostEqual(je, row["evil_pct"], places=6)
        test.assertAlmostEqual(jd, row["demon_pct"], places=6)
    return py


class BothLanguagesAgree(SolverTest):

    def test_a_board_with_the_third_nights_death(self):
        case = {"n_players": 7,
                "players": [{"claim": c, "events": []} for c in C],
                "infos": [{"type": "AlchemistHas", "night": 1, "player": 5,
                           "role": "Summoner"}],
                "deaths": {"2": ["N3"]}, "days_done": [1, 2, 3],
                "script": {"name": "Alchemist-Beschwörer",
                           "characters": IDS}}
        py = compare(self, case)
        # The Alchemist that summoned may be the Demon itself.
        self.assertGreater(py["rows"][5]["demon_pct"], 0)


if __name__ == "__main__":
    unittest.main()
