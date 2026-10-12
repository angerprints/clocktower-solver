"""The ninth three experimental characters (12.10.2026).

High Priestess, General and Fisherman: each is told what the Storyteller
*believes*, so there is nothing to check. Every reading here is the
table's ruling of 12.10.2026, asked before anything was built — way 1 for
all six questions (A to F):

  A  the rows are kept and shown, not weighed (like the Artist's question)
  B  the High Priestess and the General wake every night, the first
     included; the Fisherman never
  C  the High Priestess shares the General's night slots (50, 69) until
     the whole order is gone through at the end
  D  a second Fisherman visit is kept, with a hint on the page
  E  the Mathematiker counts as it always has
  F  the simulator plays them at random
"""

import json
import pathlib
import random
import subprocess
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking      # noqa: E402
from botc.catalogue import CHARACTERS, EVERY, NEVER, PARTLY   # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

NINTH = ("HighPriestess", "General", "Fisherman")

# Trouble Brewing's shape, with a Mathematiker to count and a Vortox
# beside the Imp, under which every Townsfolk reading must be false — and
# these three say nothing, so must go on saying nothing.
LIKE_TB = ["washerwoman", "librarian", "investigator", "chef", "empath",
           "fortuneteller", "undertaker", "monk", "ravenkeeper",
           "mathematician", "highpriestess", "general", "fisherman",
           "butler", "drunk", "recluse", "saint",
           "poisoner", "spy", "scarletwoman", "baron",
           "imp", "vortox"]
# Bad Moon Rising's, with a Kammerzofe to count who woke and a Philosoph
# who may take the General or the High Priestess.
LIKE_BMR = ["grandmother", "sailor", "chambermaid", "exorcist", "innkeeper",
            "gambler", "gossip", "courtier", "professor", "philosopher",
            "highpriestess", "general", "fisherman",
            "goon", "lunatic", "tinker", "moonchild",
            "godfather", "devilsadvocate", "assassin", "mastermind",
            "zombuul", "pukka", "shabaloth", "po"]

NINE = scripts.from_ids("Ninth three, like Trouble Brewing", LIKE_TB)
NINE_BMR = scripts.from_ids("Ninth three, like Bad Moon Rising", LIKE_BMR)


def board(script, roles, infos=(), claims=None, believes=None, **kw):
    n = len(roles)
    world = World(tuple(roles), tuple(believes or (None,) * n))
    state = GameState(n_players=n, script=script,
                      claims=dict(claims if claims is not None
                                  else enumerate(roles)),
                      infos=list(infos), **kw)
    return world, state


def cost(script, roles, infos=(), **kw):
    world, state = board(script, roles, infos, **kw)
    return S.explanation_cost(world, state)


#        0          1               2          3            4        5
TB = ["Chef", "HighPriestess", "General", "Fisherman", "Empath", "Saint",
      "Poisoner", "Imp"]                                  # 6, 7
ROWS = [I.HighPriestessInfo(1, 1, target=7),
        I.HighPriestessInfo(2, 1, target=0),
        I.GeneralInfo(1, 2, says="evil"),
        I.GeneralInfo(2, 2, says="neither"),
        I.FishermanAdvice(1, 3, advice="Execute today."),
        I.FishermanAdvice(2, 3, advice="And again.")]


class TheyAreInTheCatalogue(SolverTest):

    def test_three_townsfolk_kept_but_not_weighed(self):
        for key in NINTH:
            with self.subTest(key=key):
                self.assertEqual(CHARACTERS[key].team, "townsfolk")
                self.assertEqual(CHARACTERS[key].handled, PARTLY)
                self.assertFalse(CHARACTERS[key].modelled)
                self.assertIn("not weighed", CHARACTERS[key].note)
                self.assertFalse(CHARACTERS[key].impairs)

    def test_two_wake_every_night_and_one_never(self):
        # B: the first night included.
        self.assertEqual(CHARACTERS["HighPriestess"].wake, {EVERY})
        self.assertEqual(CHARACTERS["General"].wake, {EVERY})
        self.assertEqual(CHARACTERS["Fisherman"].wake, {NEVER})
        self.assertEqual(CHARACTERS["HighPriestess"].nights, "every")
        self.assertEqual(CHARACTERS["General"].nights, "every")
        self.assertEqual(CHARACTERS["Fisherman"].nights, "never")

    def test_the_high_priestess_has_the_generals_slots_by_hand(self):
        # C: until the whole order is gone through at the end.
        self.assertEqual((CHARACTERS["General"].first_night,
                          CHARACTERS["General"].other_night), (50, 69))
        self.assertEqual((CHARACTERS["HighPriestess"].first_night,
                          CHARACTERS["HighPriestess"].other_night), (50, 69))
        # Before the Kammerzofe and the Mathematiker, which count them.
        for counter in ("Chambermaid", "Mathematician"):
            self.assertLess(CHARACTERS["HighPriestess"].other_night,
                            CHARACTERS[counter].other_night)

    def test_the_named_games_do_not_draw_them(self):
        import play_games
        for seed in range(200):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  as_named=True)
            with self.subTest(seed=seed):
                self.assertFalse(set(NINTH) & set(script.keys))

    def test_but_a_mixed_script_may_insist_on_them(self):
        import play_games
        for seed in range(20):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  must_have=NINTH)
            with self.subTest(seed=seed):
                self.assertLessEqual(set(NINTH), set(script.keys))

    def test_the_mathematiker_is_not_silenced_by_them(self):
        # They droison nobody, so a script with them is as countable as
        # one without.
        self.assertFalse(I._unbuilt_impairer(NINE))


class TheRowsAreKeptNotWeighed(SolverTest):
    """A: shown, never solved."""

    def test_none_of_them_is_weighed(self):
        world, state = board(NINE, TB, ROWS)
        for row in ROWS:
            with self.subTest(row=type(row).__name__):
                self.assertFalse(row.weighed(state))
                self.assertFalse(row.is_information(state))
                self.assertTrue(row.holds(world, state, None))

    def test_they_change_nothing_in_any_world(self):
        rng = random.Random(9)
        for _ in range(40):
            roles = list(TB)
            rng.shuffle(roles)
            seats = {r: i for i, r in enumerate(roles)}
            rows = [I.HighPriestessInfo(1, seats["HighPriestess"],
                                        target=rng.randrange(8)),
                    I.GeneralInfo(1, seats["General"],
                                  says=rng.choice(("good", "evil",
                                                   "neither"))),
                    I.FishermanAdvice(1, seats["Fisherman"], advice="x")]
            with self.subTest(roles=roles):
                self.assertEqual(cost(NINE, roles, rows), cost(NINE, roles))

    def test_and_under_a_vortox_they_stay_silent(self):
        # Their "true" must not be read as the Vortox not working.
        roles = ["Chef", "HighPriestess", "General", "Fisherman", "Empath",
                 "Saint", "Poisoner", "Vortox"]
        self.assertIsNotNone(cost(NINE, roles, ROWS))
        self.assertEqual(cost(NINE, roles, ROWS), cost(NINE, roles))

    def test_a_drunk_holding_one_says_nothing_either(self):
        roles = ["Chef", "Drunk", "General", "Fisherman", "Empath",
                 "Saint", "Poisoner", "Imp"]
        believes = [None, "HighPriestess"] + [None] * 6
        claims = {**dict(enumerate(roles)), 1: "HighPriestess"}
        world, state = board(NINE, roles, ROWS, claims=claims,
                             believes=believes)
        with_rows = S.explanation_cost(world, state)
        world, state = board(NINE, roles, claims=claims, believes=believes)
        self.assertEqual(with_rows, S.explanation_cost(world, state))

    def test_a_second_fisherman_visit_is_kept_and_costs_nothing(self):
        # D: the page says it asked already; the solver weighs neither.
        once = [I.FishermanAdvice(1, 3, advice="a")]
        twice = once + [I.FishermanAdvice(2, 3, advice="b")]
        self.assertEqual(cost(NINE, TB, once), cost(NINE, TB, twice))


class TheyWake(SolverTest):
    """B and E: what a Kammerzofe and a Mathematiker see of them."""

    def test_every_night_while_alive(self):
        roles = ["Chambermaid", "HighPriestess", "General", "Fisherman",
                 "Gossip", "Assassin", "Po"]
        world, state = board(NINE_BMR, roles, deaths={2: ("N3",)})
        for night in (1, 2, 3, 4):
            with self.subTest(night=night):
                self.assertTrue(waking.woke(world, state, 1, night))
                self.assertFalse(waking.woke(world, state, 3, night))
                self.assertFalse(waking.uncertain(world, state, 1, night))
        self.assertTrue(waking.woke(world, state, 2, 2))
        # Dead before its slot on night three: the Po kills at 31.
        self.assertFalse(waking.woke(world, state, 2, 4))

    def test_the_kammerzofe_counts_them(self):
        roles = ["Chambermaid", "HighPriestess", "General", "Fisherman",
                 "Gossip", "Assassin", "Po"]
        bare = cost(NINE_BMR, roles)
        self.assertIsNotNone(bare)
        both = [I.ChambermaidInfo(1, 0, a=1, b=2, count=2)]
        self.assertEqual(cost(NINE_BMR, roles, both), bare)
        for wrong in (0, 1):
            said = [I.ChambermaidInfo(1, 0, a=1, b=2, count=wrong)]
            self.assertIsNone(cost(NINE_BMR, roles, said))
        fisher = [I.ChambermaidInfo(1, 0, a=3, b=4, count=0)]
        self.assertEqual(cost(NINE_BMR, roles, fisher), bare)

    def test_a_claim_is_judged_by_its_waking_pattern(self):
        # A softclaim of "every night" fits the two of them, and "never"
        # the Fisherman.
        roles = ["Chef", "HighPriestess", "General", "Fisherman", "Empath",
                 "Saint", "Poisoner", "Imp"]
        for seat, said in ((1, EVERY), (2, EVERY), (3, NEVER)):
            claims = dict(enumerate(roles))
            del claims[seat]
            world, state = board(NINE, roles, claims=claims,
                                 wakes={seat: said})
            with self.subTest(seat=seat):
                self.assertIsNotNone(S.explanation_cost(world, state))

    def test_the_mathematiker_counts_a_drunk_one_like_any_drunk(self):
        # E, as it always was.
        roles = ["Mathematician", "Drunk", "General", "Fisherman", "Empath",
                 "Saint", "Baron", "Imp"]
        believes = [None, "HighPriestess"] + [None] * 6
        claims = {**dict(enumerate(roles)), 1: "HighPriestess"}
        one = [I.MathematicianInfo(1, 0, count=1)]
        none = [I.MathematicianInfo(1, 0, count=0)]
        world, state = board(NINE, roles, one, claims=claims,
                             believes=believes)
        self.assertIsNotNone(S.explanation_cost(world, state))
        world, state = board(NINE, roles, none, claims=claims,
                             believes=believes)
        self.assertIsNone(S.explanation_cost(world, state))


class ThePageTakesThem(SolverTest):
    """The rows come in through app.py and js/api.mjs alike."""

    def payload(self, infos, deaths=None):
        claims = ["Chef", "HighPriestess", "General", "Fisherman", "Empath",
                  "Saint", "Savant"]
        players = [{"claim": c, "events": list((deaths or {}).get(i, ()))}
                   for i, c in enumerate(claims)]
        keys = LIKE_TB + ["savant"]
        return {"n_players": 7, "players": players, "infos": infos,
                "script": {"name": "B9",
                           "characters": [CHARACTERS[k].id if k in CHARACTERS
                                          else k for k in keys]},
                "days_done": [1, 2]}

    def answer(self, payload):
        import app
        return app.run_solve(payload)

    def js(self, payload):
        script = ("import {solveBoard} from './js/api.mjs';"
                  "const p=JSON.parse(process.argv[1]);"
                  "let r; try { r = solveBoard(p); } "
                  "catch (e) { r = {error: String(e.message||e)}; }"
                  "console.log(JSON.stringify(r.error ? {error: r.error}"
                  " : {valid: r.valid}));")
        got = subprocess.run(["node", "--input-type=module", "-e", script,
                              json.dumps(payload)], cwd=ROOT,
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(got.returncode, 0, got.stderr)
        return json.loads(got.stdout)

    def test_all_three_rows(self):
        rows = [{"type": "HighPriestessInfo", "night": 1, "player": 1,
                 "target": 4},
                {"type": "GeneralInfo", "night": 1, "player": 2,
                 "says": "good"},
                {"type": "FishermanAdvice", "night": 1, "player": 3,
                 "advice": "Trust the Empath."},
                {"type": "FishermanAdvice", "night": 2, "player": 3,
                 "advice": "again"}]
        py = self.answer(self.payload(rows))
        self.assertNotIn("error", py)
        self.assertEqual(self.js(self.payload(rows)), {"valid": py["valid"]})
        bare = self.answer(self.payload([]))
        self.assertEqual(py["valid"], bare["valid"])

    def test_a_general_is_told_one_of_three(self):
        rows = [{"type": "GeneralInfo", "night": 1, "player": 2,
                 "says": "maybe"}]
        self.assertIn("error", self.answer(self.payload(rows)))
        self.assertIn("error", self.js(self.payload(rows)))

    def test_advice_on_a_day_needs_the_fisherman_alive_that_day(self):
        # Day two comes after night two: killed that night, it asked
        # nothing on day two — as for a Savant. Killed on night three, it
        # did.
        row = {"type": "FishermanAdvice", "night": 2, "player": 3,
               "advice": "x"}
        dead = self.payload([row], deaths={3: ["N2"]})
        self.assertIn("error", self.answer(dead))
        self.assertIn("error", self.js(dead))
        later = self.payload([row], deaths={3: ["N3"]})
        self.assertNotIn("error", self.answer(later))
        self.assertNotIn("error", self.js(later))


class TheSimulatorPlaysThem(SolverTest):
    """F: at random, since nothing reads what they are told."""

    def games(self, script, how_many=200, nights=4):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=nights,
                                      script=script)

    def test_every_night_a_row_while_alive_and_one_advice_at_most(self):
        priestess = general = advice = 0
        for script in (NINE, NINE_BMR):
            for seed, (deal, heard) in self.games(script):
                for row in heard:
                    kind = type(row).__name__
                    priestess += kind == "HighPriestessInfo"
                    general += kind == "GeneralInfo"
                    advice += kind == "FishermanAdvice"
                    if kind == "GeneralInfo":
                        self.assertIn(row.says, ("good", "evil", "neither"))
                    if kind == "HighPriestessInfo":
                        self.assertNotEqual(row.target, row.player)
                visits = [row.player for row in heard
                          if isinstance(row, I.FishermanAdvice)]
                with self.subTest(script=script.name, seed=seed):
                    self.assertEqual(len(visits), len(set(visits)))
        self.assertGreater(priestess, 300)
        self.assertGreater(general, 300)
        self.assertGreater(advice, 60)

    def test_no_other_script_plays_differently(self):
        import hashlib
        import simulate
        digest = hashlib.sha256()
        for seed in range(60):
            deal, heard = simulate.play(9, random.Random(seed), nights=3,
                                        script=scripts.BAD_MOON_RISING)
            digest.update(repr((deal.roles, sorted(deal.deaths.items()),
                                [repr(r) for r in heard])).encode())
        from test_experimental_2 import BMR_SIXTY
        self.assertEqual(digest.hexdigest()[:16], BMR_SIXTY)

    def test_the_true_world_is_kept(self):
        import claims as C
        import simulate
        lost = []
        for script in (NINE, NINE_BMR):
            for seed in range(120):
                n = [7, 8, 9, 10, 11][seed % 5]
                rng = random.Random(seed)
                deal, heard = simulate.play(n, rng, nights=4, script=script)
                cl, wk, _ = C.claims_for(deal, rng, script=script)
                state = GameState(n_players=n, script=script, claims=cl,
                                  wakes=wk, infos=list(heard),
                                  votes=dict(deal.votes),
                                  nominations=dict(deal.nominations),
                                  **deal.record())
                if S.explanation_cost(deal.world(), state) is None:
                    lost.append((script.name, seed))
        self.assertEqual(lost, [])


# Nights the walk cannot replay for a reason that is not these three: a
# Philosoph that took the Segler earlier chooses the Schläger first, and
# the walk lets a taken Segler choose nobody (it runs the taken
# Schlangenbeschwörer, Nachtwächter and Glücksspieler only). So the
# Shabaloth is the second to choose the Schläger and kills; the walk
# makes it the first and drunk. Open item, ROADMAP (12.10.2026).
KNOWN = {("Ninth three, like Bad Moon Rising", 49, 4)}


class TheNightWalkReplaysThem(SolverTest):

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = 0
        for script in (NINE, NINE_BMR):
            for seed in range(150):
                n = [7, 8, 9, 10, 11][seed % 5]
                deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                            script=script)
                for night in range(2, deal.nights_played + 1):
                    if (script.name, seed, night) in KNOWN:
                        continue
                    hidden = nightwalk.hidden_from(deal, night, heard)
                    got = nightwalk.walk(deal, night, hidden)
                    nights += 1
                    with self.subTest(script=script.name, seed=seed,
                                      night=night):
                        self.assertEqual(got.died,
                                         deal.died_on(f"N{night}"))
                        self.assertEqual(got.untold, set())
        self.assertGreater(nights, 500)


if __name__ == "__main__":
    unittest.main()
