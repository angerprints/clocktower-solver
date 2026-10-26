"""The Engineer (26.10.2026, claude/ingenieur-lesarten.md).

"Once per game, at night, choose which Minions or which Demon is in
play." Patrick's answers, all Weg 1 but the last:

  * A: only its row counts; without one nothing happened.
  * B: whoever holds a chosen character keeps it; the rest are handed to
    the other Minions, every way a story, each as likely.
  * C: drunk or poisoned, nothing changes and the choice is spent.
  * D: fewer chosen than Minions without one: that many change; more:
    every choice of the right number.
  * E: from its turn on — a later character acts that night, one that
    acts "at the start" acts at once (tea-party changes).
  * F: a Summoner chosen while a Demon lives summons a second one on the
    third night; a living Summoner it removes leaves its ability to the
    Storyteller (their jinx).
  * G: Lil' Monsta, Legion or Riot as the Demon stay "not reckoned".
  * H: the simulator's Engineer may choose on any night.
"""

import json
import random
import subprocess
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts               # noqa: E402
from botc.catalogue import CHARACTERS, slot_of    # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import Engineered, TeaParty, Timeline, World  # noqa: E402

import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

IDS = ["engineer", "chef", "empath", "fortuneteller", "monk",
       "washerwoman", "investigator", "soldier", "undertaker", "saint",
       "spy", "baron", "scarletwoman", "imp", "po", "summoner",
       "lilmonsta"]
ENG = scripts.from_ids("Ingenieur", IDS)
# The same with a Poisoner: something to make an Engineer drunk.
POISONED = scripts.from_ids("Ingenieur mit Giftmischer", IDS + ["poisoner"])

#    0           1       2         3        4              5
R = ["Engineer", "Chef", "Empath", "Monk", "Washerwoman", "Saint",
     "Spy", "Imp"]
C = ["Engineer", "Chef", "Empath", "Monk", "Washerwoman", "Saint",
     "Soldier", "Investigator"]


def state(rows=(), claims=C, script=ENG, days=(1, 2), **kw):
    return GameState(n_players=len(claims), script=script,
                     claims=dict(enumerate(claims)), infos=list(rows),
                     days_done=set(days), **kw)


def world(roles=R):
    return World(tuple(roles), (None,) * len(roles))


def chose(night, *roles, seat=0):
    return I.EngineerChoice(night, seat, roles=tuple(roles))


def told(roles=R, rows=(), **kw):
    """Every story the rules tell, as tuples of (seat, role)."""
    return [tuple((c.seat, c.role) for c in got)
            for got, _w in S.possible_timelines(world(roles),
                                                state(rows, **kw))]


class TheCharacter(SolverTest):

    def test_a_townsfolk_after_the_sailor(self):
        c = CHARACTERS["Engineer"]
        self.assertEqual(c.team, "townsfolk")
        self.assertTrue(c.chooses)
        # First night after the Marionette, other nights after the Sailor;
        # before the Preacher and the Poisoner either way.
        self.assertGreater(slot_of("Engineer", 1), slot_of("Marionette", 1))
        self.assertLess(slot_of("Engineer", 1), slot_of("Preacher", 1))
        self.assertGreater(slot_of("Engineer", 2), slot_of("Sailor", 2))
        self.assertLess(slot_of("Engineer", 2), slot_of("Poisoner", 2))

    def test_minions_or_one_demon(self):
        st = state()
        self.assertEqual(chose(2, "Spy", "Baron").chosen(st),
                         ("Spy", "Baron"))
        self.assertEqual(chose(2, "Po").chosen(st), ("Po",))
        self.assertIsNone(chose(2, "Spy", "Po").chosen(st))
        self.assertIsNone(chose(2, "Imp", "Po").chosen(st))
        self.assertIsNone(chose(2, "Poisoner").chosen(st))   # off script
        self.assertIsNone(chose(2).chosen(st))


class TheStories(SolverTest):

    def test_nothing_without_a_row(self):
        self.assertEqual(told(), [()])

    def test_a_minion_handed_out(self):
        self.assertEqual(told(rows=[chose(2, "Baron")]), [(), ((6, "Baron"),)])

    def test_who_holds_a_chosen_one_keeps_it(self):
        # The Spy is in play already: nothing to hand out.
        self.assertEqual(told(rows=[chose(2, "Spy")]), [()])

    def test_every_way_to_hand_them_out(self):
        roles = R[:5] + ["ScarletWoman", "Spy", "Imp"]
        got = told(roles, [chose(2, "Baron", "Summoner")])
        # Two seats, two characters: two ways — and "nothing".
        self.assertEqual(sorted(got), sorted([
            (), ((5, "Baron"), (6, "Summoner")),
            ((5, "Summoner"), (6, "Baron"))]))

    def test_fewer_chosen_than_minions(self):
        roles = R[:5] + ["ScarletWoman", "Spy", "Imp"]
        got = told(roles, [chose(2, "Baron")])
        self.assertEqual(sorted(got),
                         sorted([(), ((5, "Baron"),), ((6, "Baron"),)]))

    def test_more_chosen_than_minions(self):
        got = told(rows=[chose(2, "Baron", "ScarletWoman", "Summoner")])
        self.assertEqual(sorted(got), sorted([
            (), ((6, "Baron"),), ((6, "ScarletWoman"),),
            ((6, "Summoner"),)]))

    def test_the_demon(self):
        self.assertEqual(told(rows=[chose(2, "Po")]), [(), ((7, "Po"),)])
        self.assertEqual(told(rows=[chose(2, "Imp")]), [()])

    def test_at_its_turn_on_its_side(self):
        got = S.possible_timelines(world(), state([chose(3, "Baron")],
                                                  days=(1, 2, 3)))
        change = got[1][0][0]
        self.assertIsInstance(change, Engineered)
        self.assertIsInstance(change, TeaParty)   # its first night (E)
        self.assertEqual((change.phase, change.slot, change.side),
                         ("N3", slot_of("Engineer", 3), "evil"))

    def test_only_the_first_row_counts(self):
        rows = [chose(2, "Baron"), chose(3, "Po")]
        self.assertEqual(told(rows=rows, days=(1, 2, 3)),
                         [(), ((6, "Baron"),)])

    def test_an_engineer_that_is_not_one_does_nothing(self):
        roles = ["Chef"] + R[1:]
        self.assertEqual(told(roles, [chose(2, "Baron")]), [()])

    def test_dead_it_chooses_nothing(self):
        self.assertEqual(told(rows=[chose(2, "Baron")],
                              deaths={0: ("N1",)}, quiet_nights=set()),
                         [()])


class WorkingOrNot(SolverTest):
    """C Weg 1: a working Engineer whose choice would change somebody did;
    unchanged, it was drunk or poisoned."""

    def test_unchanged_needs_it_off(self):
        st = state([chose(2, "Baron")])
        self.assertIsNone(S._explain(world(), st))
        made = Timeline(world(), (Engineered("N2", 6, "Baron", "evil",
                                             slot_of("Engineer", 2)),))
        self.assertIsNotNone(S._explain(made, st))

    def test_a_poisoner_can_excuse_it(self):
        roles = R[:6] + ["Poisoner", "Imp"]
        st = state([chose(2, "Baron")], script=POISONED)
        self.assertIsNotNone(S._explain(world(roles), st))

    def test_the_board_keeps_both(self):
        roles = R[:6] + ["Poisoner", "Imp"]
        st = state([chose(2, "Baron")], script=POISONED)
        self.assertIsNotNone(S.explanation_cost(world(roles), st))


class NotReckoned(SolverTest):

    def test_lil_monsta_as_the_demon(self):
        st = state([chose(2, "LilMonsta")])
        self.assertEqual(S.hatter_unreckoned(world(), st), "engineer")
        st = state([chose(2, "Po")])
        self.assertIsNone(S.hatter_unreckoned(world(), st))


def _play(seed, must):
    import claims as Cl
    import play_games
    import simulate
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must)
    n = [7, 8, 9, 10, 11][seed % 5]
    deal, heard = simulate.play(n, rng, nights=4, script=script)
    claims, wakes, _ = Cl.claims_for(deal, rng, script=script)
    st = GameState(n_players=n, script=script, claims=claims, wakes=wakes,
                   infos=list(heard), votes=dict(deal.votes),
                   nominations=dict(deal.nominations), **deal.record())
    return deal, heard, st


class TheSimulator(SolverTest):
    """Played games: the true world is kept, the night-walk agrees, and
    nothing is left unreckoned."""

    def run_games(self, seeds, must):
        import nightwalk
        lost, walked, left, chose_, made = [], [], [], 0, 0
        for seed in seeds:
            deal, heard, st = _play(seed, must)
            if not any(isinstance(r, I.EngineerChoice) for r in heard):
                continue
            chose_ += 1
            made += bool(deal.tea_made)
            for night in range(2, deal.nights_played + 1):
                got = nightwalk.walk(deal, night,
                                     nightwalk.hidden_from(deal, night, heard))
                if got.died != deal.died_on(f"N{night}") or got.untold:
                    walked.append((seed, night))
            if S.hatter_unreckoned(deal.world(), st) is not None:
                left.append(seed)
                continue
            if S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        return chose_, made, (lost, walked, left)

    def test_games_with_an_engineer(self):
        chose_, made, bad = self.run_games(range(300), ("Engineer",))
        self.assertGreater(chose_, 60)
        self.assertGreater(made, 30)
        self.assertEqual(bad, ([], [], []))

    def test_beside_a_summoner(self):
        _c, _m, bad = self.run_games(range(150), ("Engineer", "Summoner"))
        self.assertEqual(bad, ([], [], []))

    def keeps(self, seed, must):
        deal, _heard, st = _play(seed, must)
        self.assertTrue(deal.tea_made, seed)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st), seed)

    def test_the_charmer_takes_the_demon_it_made(self):
        # A Leviathan made the Imp at the Engineer's turn, and a Snake
        # Charmer swapped with it later that night: it took the Imp.
        self.keeps(1005, ("Engineer",))

    def test_the_storyteller_summons_for_a_summoner_it_took(self):
        # The living Summoner made a Wraith on night two and executed the
        # next day: the Storyteller still summons on the third night.
        self.keeps(738, ("Engineer", "Summoner"))

    def test_a_chambermaid_counts_the_night_it_chose(self):
        deal, heard, st = _play(770, ("Engineer",))
        self.assertTrue(any(isinstance(r, I.EngineerChoice) for r in heard))
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_a_pukka_made_tonight_only_poisons(self):
        # A Vortox made the Pukka on night two: nothing it chose is due
        # that night (found by the simulator, 26.10.2026).
        deal, _heard, st = _play(102, ("Engineer",))
        self.assertIn(("N2", 5, "Pukka"), deal.changes)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))


def _payloads():
    def pay(events, rows=(), claims=C, ids=IDS, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players,
                "infos": list(rows),
                "script": {"name": "Ingenieur", "characters": ids},
                "days_done": list(days)}

    def e(night, *roles):
        return {"type": "EngineerChoice", "night": night, "player": 0,
                "roles": list(roles)}

    return [
        pay({1: ["N2"]}, [e(2, "Baron")]),
        pay({1: ["N2"]}, [e(2, "Po")]),
        pay({1: ["N2"], 2: ["N3"]}, [e(2, "Baron", "ScarletWoman")],
            days=(1, 2, 3)),
        pay({1: ["N2"]}, [e(1, "Summoner")], days=(1, 2, 3)),
        pay({1: ["N2"], 4: ["X1"]}, [e(2, "Spy", "Baron", "Summoner")]),
        pay({1: ["N2"]}, [e(2, "LilMonsta")]),
        pay({1: ["N2"]}, [e(2, "Baron")], ids=IDS + ["poisoner"]),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_an_engineer(self):
        import app
        cases = _payloads()
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const ps=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(ps.map(p => {"
                  " const r = solveBoard(p); if (r.error) return r.error;"
                  " return {valid: r.valid, un: r.unreckoned || {},"
                  "  rows: r.rows.map(x => [x.evil_pct, x.demon_pct])};"
                  "})));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(cases)], cwd=ROOT,
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(got.returncode, 0, got.stderr)
        js = json.loads(got.stdout)
        for p, j in zip(cases, js):
            r = app.run_solve(p)
            self.assertNotIn("error", r)
            self.assertEqual(j["valid"], r["valid"])
            self.assertGreater(r["valid"], 0)
            self.assertEqual(j["un"], r.get("unreckoned") or {})
            for (je, jd), row in zip(j["rows"], r["rows"]):
                self.assertAlmostEqual(je, row["evil_pct"], places=6)
                self.assertAlmostEqual(jd, row["demon_pct"], places=6)


if __name__ == "__main__":
    unittest.main()
