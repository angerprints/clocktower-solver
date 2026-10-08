"""The third five experimental characters (08.10.2026).

Magician, Poppy Grower, Politician, Snitch and Wraith — the smallest that
were left. Four of them change only what the evil team knows or how the
game is scored, and no board shows either:

  * A **Magician** is shown to the Demon as a Minion and to the Minions
    as the Demon. It wakes for nothing.
  * A **Poppy Grower** keeps the evil team from learning each other until
    it dies. Being told is not anybody's ability.
  * A **Politician** may change side at the very end. Nothing reads it.
  * A **Snitch** hands every Minion three bluffs on the first night.

The fifth changes who is awake:

  * A **Wraith** is woken whenever another evil player opens their eyes
    for their own ability, and a Chambermaid counts it (my reading,
    08.10.2026). Being shown your team on the first night does not wake
    it; a Spy looking at the grimoire does, unless a Poppy Grower has its
    ability (their jinx).

They have no script, like the first ten, so two are made for them here.
"""

import pathlib
import random
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import info as I, scripts, waking       # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))

THIRD = ("Magician", "PoppyGrower", "Politician", "Snitch", "Wraith")

# Trouble Brewing's shape, with a Recluse and a Spy for registering.
LIKE_TB = ["magician", "poppygrower", "washerwoman", "librarian",
           "investigator", "chef", "empath", "fortuneteller", "undertaker",
           "monk", "ravenkeeper", "slayer", "soldier",
           "politician", "snitch", "recluse", "drunk",
           "wraith", "poisoner", "spy", "scarletwoman",
           "imp"]
# Bad Moon Rising's, with the Chambermaid that sees the Wraith, and a Spy
# so the Poppy Grower's jinx can come up.
LIKE_BMR = ["magician", "poppygrower", "grandmother", "sailor",
            "chambermaid", "exorcist", "innkeeper", "gambler", "gossip",
            "courtier", "professor", "minstrel", "tealady",
            "politician", "snitch", "goon", "lunatic",
            "wraith", "godfather", "assassin", "spy",
            "po", "pukka"]

WRAITH = scripts.from_ids("Third five, like Trouble Brewing", LIKE_TB)
WRAITH_BMR = scripts.from_ids("Third five, like Bad Moon Rising", LIKE_BMR)


def board(script, roles, infos=(), **kw):
    n = len(roles)
    world = World(tuple(roles), (None,) * n)
    state = GameState(n_players=n, script=script,
                      claims=dict(enumerate(roles)), infos=list(infos), **kw)
    return world, state


def cost(script, roles, infos=(), **kw):
    """What the world costs where everybody claims what they hold."""
    world, state = board(script, roles, infos, **kw)
    return S.explanation_cost(world, state)


def counts(roles, seats, night, script=WRAITH_BMR, **kw):
    world, state = board(script, roles, **kw)
    return waking.possible_counts(world, state, seats, night)


#        0              1              2          3         4
SEVEN = ["Chambermaid", "Grandmother", "Gambler", "Gossip", "Professor",
         "Wraith", "Po"]                                     # 5, 6


class TheyAreInTheCatalogue(SolverTest):

    def test_two_townsfolk_two_outsiders_and_a_minion(self):
        teams = {key: CHARACTERS[key].team for key in THIRD}
        self.assertEqual(teams, {"Magician": "townsfolk",
                                 "PoppyGrower": "townsfolk",
                                 "Politician": "outsider",
                                 "Snitch": "outsider", "Wraith": "minion"})
        for key in THIRD:
            self.assertTrue(CHARACTERS[key].modelled)

    def test_only_the_wraith_wakes_for_itself(self):
        for key in THIRD[:4]:
            with self.subTest(character=key):
                self.assertEqual(CHARACTERS[key].nights, "never")
        self.assertEqual(CHARACTERS["Wraith"].nights, "conditional")
        self.assertIn("Wraith", waking.CONDITION_RULES)

    def test_the_named_games_do_not_draw_them(self):
        """`as_named` keeps the pool of 07.10.2026, so "seed 1250" stays
        the game it was."""
        import play_games
        for seed in range(200):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  as_named=True)
            with self.subTest(seed=seed):
                self.assertFalse(set(THIRD) & set(script.keys))


class FourThatLeaveNoMark(SolverTest):

    def test_a_world_with_one_costs_what_it_would_without(self):
        base = ["Chef", "Empath", "Undertaker", "Monk", "Soldier",
                "Poisoner", "Imp"]
        for key, at in (("Magician", 0), ("PoppyGrower", 1),
                        ("Politician", 2), ("Snitch", 3)):
            roles = list(base)
            roles[at] = key
            for over in ({}, {"game_over": True}, {"days_done": {1}}):
                with self.subTest(character=key, board=over):
                    self.assertEqual(cost(WRAITH, roles, **over), 1.0)

    def test_a_chambermaid_counts_none_of_them(self):
        roles = ["Chambermaid", "Magician", "PoppyGrower", "Politician",
                 "Snitch", "Godfather", "Po"]
        for night in (1, 2, 3):
            with self.subTest(night=night):
                self.assertEqual(counts(roles, (1, 2), night), {0})
                self.assertEqual(counts(roles, (3, 4), night), {0})


class AWraithWakesWithTheEvil(SolverTest):

    def test_beside_a_demon_that_kills(self):
        self.assertEqual(counts(SEVEN, (5, 3), 2), {1})
        self.assertEqual(counts(SEVEN, (5, 6), 2), {2})

    def test_the_first_night_follows_the_demon(self):
        """A Po is only shown its Minions on the first night, and whether
        that counts is open (table ruling, 02.10.2026: not here, at other
        tables yes). The Wraith inherits the doubt."""
        self.assertEqual(counts(SEVEN, (5, 3), 1), {0, 1})

    def test_a_minion_that_acts_on_the_first_night_settles_it(self):
        roles = SEVEN[:4] + ["Godfather", "Wraith", "Po"]
        self.assertEqual(counts(roles, (5, 3), 1), {1})

    def test_a_pukka_chooses_on_the_first_night(self):
        roles = SEVEN[:6] + ["Pukka"]
        self.assertEqual(counts(roles, (5, 3), 1), {1})

    def test_an_assassin_does_not_wake_it_on_the_first_night(self):
        """At night* — the first night it is only shown its team."""
        roles = SEVEN[:4] + ["Assassin", "Wraith", "Po"]
        self.assertEqual(counts(roles, (5, 3), 1), {0, 1})

    def test_a_dead_wraith_sleeps(self):
        self.assertEqual(counts(SEVEN, (5, 3), 2, deaths={5: "E1"}), {0})

    def test_a_spy_looking_wakes_it(self):
        roles = SEVEN[:4] + ["Spy", "Wraith", "Po"]
        self.assertEqual(counts(roles, (5, 3), 1), {1})

    def test_unless_a_poppy_grower_keeps_the_grimoire_shut(self):
        roles = ["Chambermaid", "PoppyGrower", "Gambler", "Gossip", "Spy",
                 "Wraith", "Po"]
        self.assertEqual(counts(roles, (5, 3), 1), {0, 1})
        # A dead Poppy Grower keeps nothing shut.
        self.assertEqual(counts(roles, (5, 3), 2, deaths={1: "E1"}), {1})

    def test_an_evil_twin_opens_its_eyes_on_the_first_night_only(self):
        """Shown its twin then, and never again — so it wakes a Wraith
        once. The simulator woke one beside it every night (08.10.2026)."""
        script = scripts.from_ids("Third five, with a twin",
                                  LIKE_BMR + ["eviltwin", "zombuul"])
        roles = SEVEN[:4] + ["EvilTwin", "Wraith", "Zombuul"]
        self.assertEqual(counts(roles, (5, 3), 1, script=script), {1})
        # A Zombuul sleeps after a day somebody died.
        self.assertEqual(counts(roles, (5, 3), 2, script=script,
                                deaths={1: "E1"}), {0})

    def test_the_lunatic_is_no_evil_player(self):
        """It thinks it is the Demon and wakes as one, but it is good."""
        roles = ["Chambermaid", "Lunatic", "Gambler", "Gossip", "Professor",
                 "Wraith", "Pukka"]
        world, state = board(WRAITH_BMR, roles)
        self.assertFalse(world.evil_at(1, "N2"))
        self.assertEqual(counts(roles, (5, 3), 2), {1})        # the Pukka

    def test_the_chambermaids_row_holds_it_to_that(self):
        right = I.ChambermaidInfo(2, 0, a=5, b=1, count=1)
        wrong = I.ChambermaidInfo(2, 0, a=5, b=1, count=0)
        self.assertEqual(cost(WRAITH_BMR, SEVEN, [right]), 1.0)
        self.assertIsNone(cost(WRAITH_BMR, SEVEN, [wrong]))


class TheSimulatorPlaysThem(SolverTest):

    def played(self, script, games, nights=4):
        import claims as claim_model
        import simulate
        dealt, lost, asked = {}, [], 0
        for seed in range(games):
            n = [7, 8, 9, 10, 11][seed % 5]
            rng = random.Random(seed)
            deal, heard = simulate.play(n, rng, nights=nights, script=script)
            claims, wakes, _ = claim_model.claims_for(deal, rng,
                                                      script=script)
            state = GameState(n_players=n, script=script, claims=claims,
                              wakes=wakes, infos=list(heard),
                              votes=dict(deal.votes),
                              nominations=dict(deal.nominations),
                              **deal.record())
            truth = World(tuple(deal.roles), tuple(deal.believes))
            for key in THIRD:
                dealt[key] = dealt.get(key, 0) + (key in deal.roles)
            for row in heard:
                if isinstance(row, I.ChambermaidInfo) and any(
                        deal.role_at(p, f"N{row.night}") == "Wraith"
                        for p in (row.a, row.b)):
                    asked += 1
            if S.explanation_cost(truth, state) is None:
                lost.append(seed)
        return dealt, lost, asked

    def test_like_trouble_brewing(self):
        dealt, lost, _ = self.played(WRAITH, 300)
        self.assertEqual(lost, [])
        for key in THIRD:
            self.assertGreater(dealt[key], 20, key)

    def test_like_bad_moon_rising(self):
        dealt, lost, asked = self.played(WRAITH_BMR, 400)
        self.assertEqual(lost, [])
        self.assertGreater(asked, 20, "no Chambermaid ever asked a Wraith")

    def test_its_count_is_one_the_solver_allows(self):
        """Read off the simulator's own rule, then asked of the solver's,
        seat by seat — a sober Chambermaid only."""
        import simulate
        checked = 0
        for seed in range(400):
            n = [7, 8, 9, 10, 11][seed % 5]
            deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                        script=WRAITH_BMR)
            # Only games where nobody changed character or side, so the
            # deal is the world all game.
            if deal.changes or deal.side_changes or deal.resurrections:
                continue
            for night in range(1, deal.nights_played + 1):
                phase = f"N{night}"
                wraith = next((p for p in deal.alive_at(phase)
                               if deal.role_at(p, phase) == "Wraith"), None)
                if wraith is None:
                    continue
                said = simulate._woke_for_own_ability(deal, wraith, night)
                state = GameState(n_players=n, script=WRAITH_BMR,
                                  claims={}, infos=list(heard),
                                  **deal.record())
                world = World(tuple(deal.roles), tuple(deal.believes))
                got = waking.possible_counts(world, state, (wraith,), night)
                checked += 1
                with self.subTest(seed=seed, night=night):
                    self.assertIn(int(said), got)
        self.assertGreater(checked, 100)

    def test_no_other_script_plays_differently(self):
        """Taking the Chambermaid's count out into a function moved no
        game on the published scripts."""
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


class TheNightWalkReplaysThem(SolverTest):
    """Nobody among the five acts at night, so the walk has nothing new
    to learn, and that is what is checked."""

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = 0
        for script in (WRAITH, WRAITH_BMR):
            for seed in range(150):
                n = [7, 8, 9, 10, 11][seed % 5]
                deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                            script=script)
                for night in range(2, deal.nights_played + 1):
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
