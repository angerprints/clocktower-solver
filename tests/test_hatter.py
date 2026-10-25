"""The Hatter (22.10.2026), the sixth of the big characters in the order
Patrick agreed on 20.10.2026 — its first stage (S Weg 1).

"If you died today or tonight, the Minion & Demon players may choose new
Minion & Demon characters to be."

Patrick's answers (claude/hutmacher-lesarten.md):

  A  Weg 1: every way the evil players can have chosen is a story.
  B  Weg 2: the optional rule too — the Demon and a Minion swap types.
  C  After a death by day, at the very start of the next night; after a
     death at night, straight after it (not reckoned in this stage).
  D  Every new ability works at once, as a new instance; a new Evil Twin
     gets a twin from the other side at once.
  E  Weg 1: the old character's poison ends with it.
  F  Weg 1: the simulator's Demon chooses in half the games, each Minion
     in a third, and they go on claiming their bluff.
  G  Weg 1: the Chambermaid does not count the waking for the party.
  H  Leviathan not after day 5; Legion not built.
  I  A Philosopher that took the Hatter is built.
  J  Weg 1: as many Demons after as before (a swap).
  K  Weg 2: two living Demons through the Summoner (a later stage).
  L  Weg 2: the night split at a death at night (stage 3c, 23.10.2026,
     tests/test_split_night.py).
  M–O, Q, R  Weg 1; P Weg 2: the Marionette chooses and may be chosen.
  S  Weg 1: in stages; what this one does not reckon, the page says so.
  T  As for the Barber: only a Hatter somebody claimed starts a party.
  U  Weg 2: the Lil' Monsta jinx is a later stage too.
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
from botc.worlds import TeaParty, Timeline, World  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ["hatter", "poisoner", "spy", "baron", "eviltwin", "imp", "po",
       "chef", "empath", "fortuneteller", "monk", "washerwoman",
       "investigator", "soldier", "gambler", "saint"]
HAT = scripts.from_ids("Hutmacher", IDS)
#    0       1         2               3       4              5
R = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman", "Hatter",
     "Poisoner", "Imp"]
C = ["Chef", "Empath", "FortuneTeller", "Monk", "Washerwoman", "Hatter",
     "Soldier", "Investigator"]
HANGED = dict(executions={1: 5}, deaths={5: ("D1",)})


def state(rows=(), roles=R, claims=C, script=HAT, days=(1, 2), **kw):
    st = GameState(n_players=len(roles), script=script,
                   claims=dict(enumerate(claims)), infos=list(rows),
                   days_done=set(days), **kw)
    return st


def cost(rows=(), roles=R, claims=C, script=HAT, days=(1, 2), **kw):
    st = state(rows, roles, claims, script, days, **kw)
    return S.explanation_cost(World(tuple(roles), (None,) * len(roles)), st)


def with_deaths(extra, base=HANGED):
    out = {k: (dict(v) if isinstance(v, dict) else v)
           for k, v in base.items()}
    out["deaths"] = {**base["deaths"], **extra}
    return out


class TheCharacter(SolverTest):

    def test_an_outsider_that_never_wakes(self):
        c = CHARACTERS["Hatter"]
        self.assertEqual(c.team, "outsider")
        self.assertEqual(c.wake, frozenset({"never"}))
        # Its party is the very first thing of the night (C).
        self.assertEqual(c.other_night, 1)


class TheChoices(SolverTest):

    def choices(self, night=2, **kw):
        st = state(**{**HANGED, **kw})
        st._final_phase_held = st.final_phase()
        return S.tea_party_choices(World(tuple(R), (None,) * len(R)), st,
                                   night)

    def test_nobody_first_then_every_way(self):
        got = self.choices()
        self.assertEqual(got[0], ())
        # The Poisoner keeps or takes the Spy, the Baron or the Evil Twin;
        # the Imp keeps or takes the Po: 4 x 2 ways — and the swap, the
        # Poisoner the Po and the Imp one of three Minions.
        self.assertEqual(len(got), 4 * 2 + 3)
        roles = {tuple((c.seat, c.role) for c in way) for way in got}
        self.assertIn(((6, "Spy"), (7, "Po")), roles)
        self.assertIn(((6, "Po"), (7, "Baron")), roles)

    def test_never_two_demons_or_none(self):
        for way in self.choices():
            view = Timeline(World(tuple(R), (None,) * len(R)), way)
            demons = [p for p in range(len(R))
                      if CHARACTERS[view.role_at(p, "N2")].team == "demon"]
            self.assertEqual(len(demons), 1, way)

    def test_the_dead_do_not_choose(self):
        got = self.choices(deaths={5: ("D1",), 6: ("N1",)})
        self.assertTrue(all(c.seat != 6 for way in got for c in way))

    def test_no_leviathan_after_day_five(self):
        script = scripts.from_ids("Hutmacher L", IDS + ["leviathan"])
        st = state(script=script, days=(1, 2, 3, 4, 5), **HANGED)
        world = World(tuple(R), (None,) * len(R))
        early = {c.role for way in S.tea_party_choices(world, st, 5)
                 for c in way}
        late = {c.role for way in S.tea_party_choices(world, st, 6)
                for c in way}
        self.assertIn("Leviathan", early)
        self.assertNotIn("Leviathan", late)


class OnlyAClaimedHatter(SolverTest):
    """T, 22.10.2026: as for the Barber."""

    def test_claimed_and_hanged(self):
        self.assertEqual(S.hatter_claimants(state(**HANGED)), {5})

    def test_a_hatter_hiding_starts_nothing(self):
        claims = list(C)
        claims[5] = "Saint"
        st = state(claims=claims, **HANGED)
        self.assertEqual(S.hatter_claimants(st), set())


class TheStartOfTheNight(SolverTest):
    """Everything that reads the board "as the night began" reads it after
    the tea party (worlds.moment)."""

    def test_a_gambler_that_named_the_old_demon_guessed_wrong(self):
        roles = list(R)
        roles[0] = "Gambler"
        claims = list(C)
        claims[0] = "Gambler"
        # The Imp became a Po at the party and killed the Empath; the
        # Gambler named seat 7 the Imp — wrong by then — and died of it.
        guess = I.GamblerGuess(2, 0, target=7, role="Imp")
        deaths = with_deaths({0: ("N2",), 1: ("N2",)})
        self.assertIsNotNone(cost([guess], roles=roles, claims=claims,
                                  **deaths))
        # With the Hatter standing nobody chose anything new: the Imp kills
        # one, and the right guess kills nobody.
        alive = dict(deaths={0: ("N2",), 1: ("N2",)})
        self.assertIsNone(cost([guess], roles=roles, claims=claims, **alive))

    def test_moment_b_is_after_the_party(self):
        world = World(tuple(R), (None,) * len(R))
        view = Timeline(world, (TeaParty("N2", 7, "Po", "evil"),))
        self.assertEqual(view.role_at(7, "D1"), "Imp")
        self.assertEqual(view.role_at(7, "B1"), "Po")
        self.assertEqual(view.role_at(7, "N2"), "Po")
        self.assertEqual(view.demon_at("B1"), 7)


class ANewEvilTwin(SolverTest):
    """M Weg 1: a twin from the other side at once."""

    def test_the_pair_is_told_on_the_night_it_was_taken(self):
        pair = I.EvilTwinPair(2, 2, a=6, b=2)
        self.assertEqual(cost([pair], **HANGED), 1.0)
        # With the Hatter standing there is no Evil Twin at all: the row
        # can only have been made up.
        self.assertLess(cost([pair]), 1.0)


class APhilosopherThatTookIt(SolverTest):
    """I: built — its death is a tea party, and a real Hatter beside it is
    drunk and starts none."""

    def test_its_death_lets_them_choose(self):
        roles = list(R)
        roles[5] = "Philosopher"
        claims = list(C)
        claims[5] = "Philosopher"
        script = scripts.from_ids("Hutmacher P", IDS + ["philosopher"])
        took = I.PhilosopherChoice(1, 5, role="Hatter")
        pair = I.EvilTwinPair(2, 2, a=6, b=2)
        self.assertEqual(cost([took, pair], roles=roles, claims=claims,
                              script=script, **HANGED), 1.0)
        self.assertLess(cost([took, pair], roles=roles, claims=claims,
                             script=script), 1.0)


class TheHatterWorking(SolverTest):

    def test_a_choice_needs_a_working_hatter(self):
        world = World(tuple(R), (None,) * len(R))
        st = state(**HANGED)
        st._final_phase_held = st.final_phase()
        view = Timeline(world, (TeaParty("N2", 6, "Spy", "evil"),))
        failures = S._plain_failures(view, st)
        self.assertIsNotNone(failures[0])


class NotReckonedYet(SolverTest):
    """S Weg 1, K and U: no figures, and the reason. (L, a Hatter dead at
    night, is reckoned since stage 3c.)"""

    def unreckoned(self, script=HAT, **kw):
        st = state(script=script, **kw)
        return S.analyze(st)["unreckoned"]

    def test_a_claimed_hatter_dead_at_night_is_reckoned_since_stage_3(self):
        """L Weg 2, built in stage 3c (23.10.2026)."""
        got = self.unreckoned(deaths={5: ("N2",)}, days=(1, 2))
        self.assertNotIn("hatter at night", got)

    def test_a_hanged_hatter_is_reckoned(self):
        self.assertEqual(self.unreckoned(**HANGED), {})

    def test_a_second_demon_through_the_summoner_is_reckoned(self):
        """K Weg 2, built in stage 2 (25.10.2026)."""
        script = scripts.from_ids("Hutmacher S", IDS + ["summoner"])
        self.assertEqual(self.unreckoned(script=script, days=(1, 2, 3),
                                         **HANGED), {})

    def test_lil_monsta_on_the_script(self):
        script = scripts.from_ids("Hutmacher M", IDS + ["lilmonsta"])
        self.assertIn("lil monsta", self.unreckoned(script=script, **HANGED))


class ThePrune(SolverTest):
    """A story nobody chose in that failed without looking past the party
    takes every choice with it — and changes no answer."""

    def test_same_answer_without_it(self):
        rows = [I.GamblerGuess(2, 0, target=7, role="Imp")]
        roles = list(R)
        roles[0] = "Gambler"
        claims = list(C)
        claims[0] = "Gambler"
        for deaths in (with_deaths({0: ("N2",), 1: ("N2",)}),
                       with_deaths({1: ("N2",)}), HANGED):
            st = state(rows, roles=roles, claims=claims, **deaths)
            on = S.analyze(st)
            S.TEA_PRUNE = False
            try:
                off = S.analyze(state(rows, roles=roles, claims=claims,
                                      **deaths))
            finally:
                S.TEA_PRUNE = True
            self.assertEqual(on["valid"], off["valid"])
            for a, b in zip(on["rows"], off["rows"]):
                self.assertAlmostEqual(a["evil_pct"], b["evil_pct"])
                self.assertAlmostEqual(a["demon_pct"], b["demon_pct"])


class TheSimulator(SolverTest):
    """Played games: the true world is kept wherever the Hatter was
    claimed, and the night-walk agrees on every night with a tea party."""

    def test_games_with_a_tea_party(self):
        import claims as Cl
        import nightwalk
        import play_games
        import simulate
        lost, walked, parties = [], [], 0
        for seed in range(400):
            rng = random.Random(seed)
            script = play_games.an_awkward_script(rng, must_have=("Hatter",))
            n = [7, 8, 9, 10, 11][seed % 5]
            deal, heard = simulate.play(n, rng, nights=4, script=script)
            if not deal.tea_made:
                continue
            parties += 1
            claims, wakes, _ = Cl.claims_for(deal, rng, script=script)
            st = GameState(n_players=n, script=script, claims=claims,
                           wakes=wakes, infos=list(heard),
                           votes=dict(deal.votes),
                           nominations=dict(deal.nominations),
                           **deal.record())
            for night in sorted({k for _s, k in deal.tea_made}):
                got = nightwalk.walk(deal, night,
                                     nightwalk.hidden_from(deal, night, heard))
                if got.died != deal.died_on(f"N{night}") or got.untold:
                    walked.append((seed, night))
            if S.hatter_unreckoned(deal.world(), st) is not None:
                continue
            said = S.hatter_claimants(st)
            hidden = not any(p in said for p in range(n)
                             if deal.roles[p] == "Hatter"
                             or deal.philosophies.get(p) == "Hatter")
            if not hidden and S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        self.assertGreater(parties, 20)
        self.assertEqual(walked, [])
        self.assertEqual(lost, [])


class TwoLivingDemons(SolverTest):
    """Stage 2 (25.10.2026): a Minion chose the Summoner at a tea party and
    summoned a second living Demon on the third night. Played games: the
    true world is kept, the night-walk agrees, and nothing is left
    unreckoned."""

    SEEDS = (48, 116, 157, 407, 466, 702)

    def test_played(self):
        import claims as Cl
        import nightwalk
        import play_games
        import simulate
        lost, walked, left = [], [], []
        for seed in self.SEEDS:
            rng = random.Random(seed)
            script = play_games.an_awkward_script(
                rng, must_have=("Hatter", "Summoner"))
            n = [7, 8, 9, 10, 11][seed % 5]
            deal, heard = simulate.play(n, rng, nights=4, script=script)
            self.assertTrue(deal.line2, seed)
            claims, wakes, _ = Cl.claims_for(deal, rng, script=script)
            st = GameState(n_players=n, script=script, claims=claims,
                           wakes=wakes, infos=list(heard),
                           votes=dict(deal.votes),
                           nominations=dict(deal.nominations),
                           **deal.record())
            if S.hatter_unreckoned(deal.world(), st) is not None:
                left.append(seed)
            for night in range(2, deal.nights_played + 1):
                got = nightwalk.walk(deal, night,
                                     nightwalk.hidden_from(deal, night, heard))
                if got.died != deal.died_on(f"N{night}") or got.untold:
                    walked.append((seed, night))
            if S.explanation_cost(deal.world(), st) is None:
                lost.append(seed)
        self.assertEqual((lost, walked, left), ([], [], []))

    def test_two_demons_at_once(self):
        """The board's Demons: both, from the summoning on."""
        from botc.worlds import Summoned, TeaParty, Timeline, World
        w = World(list(R), list(R))
        t = Timeline(w, (TeaParty("N2", 1, "Summoner", "evil"),
                         Summoned("N3", 0, "Po", "evil")))
        self.assertEqual(t.demons_at("D2"), (7,))
        self.assertEqual(t.demons_at("D3"), (7, 0))
        self.assertEqual(t.demon_at("D3"), 7)


class FoundAtTheGate(SolverTest):
    """Games of the gate the first build lost, kept now (22.10.2026)."""

    def keeps(self, must, seed):
        import claims as Cl
        import play_games
        import simulate
        n = [7, 8, 9, 10, 11][seed % 5]
        rng = random.Random(seed)
        script = play_games.an_awkward_script(rng, must_have=must)
        deal, heard = simulate.play(n, rng, nights=4, script=script)
        claims, wakes, _ = Cl.claims_for(deal, rng, script=script)
        st = GameState(n_players=n, script=script, claims=claims,
                       wakes=wakes, infos=list(heard), votes=dict(deal.votes),
                       nominations=dict(deal.nominations), **deal.record())
        self.assertTrue(deal.tea_made)
        self.assertIsNotNone(S.explanation_cost(deal.world(), st))

    def test_room_for_every_bounty_hunter_story(self):
        # A Philosopher's Hatter hanged, the Yaggababble a Vortox: the
        # tea parties crowded the Bounty Hunter's Townsfolk out.
        self.keeps(("Hatter", "Marionette", "Lunatic", "Drunk",
                    "ScarletWoman"), 54)

    def test_a_demon_changed_after_a_jump_it_was_not_shown(self):
        # A Fang Gu that jumped, then chose the Po: the lineage, asked
        # without the jump, read the Po as the Demon all along.
        self.keeps(("Hatter", "Imp", "Po", "NoDashii"), 852)

    def test_the_star_goes_to_the_minion_that_swapped(self):
        # The optional rule's swap made a Minion the Fang Gu, which jumped
        # the same night: followed from the end, the jump was skipped.
        self.keeps(("Hatter", "Imp", "Po", "NoDashii"), 1511)


def _payloads():
    def pay(events, rows=(), claims=C, ids=IDS, days=(1, 2)):
        players = [{"claim": c, "events": events.get(i, [])}
                   for i, c in enumerate(claims)]
        return {"n_players": len(claims), "players": players,
                "infos": list(rows),
                "script": {"name": "Hutmacher", "characters": ids},
                "days_done": list(days)}

    gambler = ["Gambler"] + C[1:]
    guess = {"type": "GamblerGuess", "night": 2, "player": 0, "target": 7,
             "role": "Imp"}
    return [
        pay({5: ["X1"]}),
        pay({5: ["X1"], 0: ["N2"], 1: ["N2"]}, [guess], claims=gambler),
        pay({5: ["X1"], 1: ["N2"]}, [{"type": "EvilTwinPair", "night": 2,
                                      "player": 2, "a": 6, "b": 2}]),
        pay({5: ["N2"]}),
        pay({5: ["X1"], 1: ["N2"]}, ids=IDS + ["summoner"]),
        pay({5: ["X1"], 1: ["N2"], 3: ["N3"]}, days=(1, 2, 3)),
        # Dead at night beside an Assassin: a party after the Demons' turn
        # and one after the Assassin's (stage 3c, 23.10.2026).
        pay({5: ["N2"], 1: ["N3"]}, ids=IDS + ["assassin"], days=(1, 2, 3)),
        # A Summoner chosen at the party summons a second living Demon on
        # the third night (stage 2, 25.10.2026): deaths that night are
        # arbitrary, and each Demon kills on the fourth.
        pay({5: ["X1"], 1: ["N2"]}, ids=IDS + ["summoner"], days=(1, 2, 3)),
        pay({5: ["X1"], 1: ["N2"], 2: ["N3"], 3: ["N3"], 4: ["N4"],
             0: ["N4"]}, ids=IDS + ["summoner"], days=(1, 2, 3)),
    ]


class BothLanguagesAgree(SolverTest):

    def test_on_boards_with_a_hatter(self):
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
