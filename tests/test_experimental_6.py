"""The sixth five experimental characters (10.10.2026).

Preacher, Huntsman, Puzzlemaster, Xaan and Boomdandy. Every reading here
is the table's ruling of 10.10.2026, asked before anything was built:

  * A **Preacher** chooses a player every night. A Minion it chooses
    while working has no ability for as long as the Preacher lives and
    works — forced, not on offer. That is not being drunk: an Acrobat
    picking one lives. A Mathematician counts it. A preached Vizier still
    cannot die by day (their jinx).
  * A **Huntsman** brings the Damsel in place of a Townsfolk. Once a game
    it chooses a living player; a Damsel it finds while working becomes a
    Townsfolk not in play, drunk or not. Anybody else, or a Huntsman off:
    nothing, and spent.
  * A **Puzzlemaster** keeps one player drunk all game, anybody, for
    free. Its one guess shown the Demon means it guessed the drunk one,
    or it was off itself.
  * A **Xaan** allows any number of Outsiders. On night X — the Outsiders
    dealt — every Townsfolk is poisoned until dusk, the Mathematician
    among them, if the Xaan lives and works.
  * A **Boomdandy** executed and working explodes: all but three die,
    never the Demon, and one more by pointing — the Demon, and good wins.

They have no script, like the rest, so two are made for them here.
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
from botc.worlds import World, enumerate_worlds, seated_legally  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))

SIXTH = ("Preacher", "Huntsman", "Puzzlemaster", "Xaan", "Boomdandy")

# Trouble Brewing's shape, with a Mathematician to count, an Acrobat to
# pick a preached Minion, the Damsel the Huntsman brings and a Vizier for
# the Preacher's jinx.
LIKE_TB = ["washerwoman", "librarian", "chef", "empath", "fortuneteller",
           "undertaker", "monk", "ravenkeeper", "preacher", "huntsman",
           "soldier", "mayor", "mathematician", "acrobat",
           "puzzlemaster", "damsel", "saint", "recluse", "drunk",
           "xaan", "boomdandy", "poisoner", "scarletwoman", "vizier",
           "imp"]
# Bad Moon Rising's, with a Chambermaid to count the Huntsman, a Minstrel
# and a Pukka.
LIKE_BMR = ["grandmother", "sailor", "chambermaid", "exorcist", "innkeeper",
            "gambler", "gossip", "courtier", "professor", "preacher",
            "huntsman", "tealady", "minstrel", "fool",
            "puzzlemaster", "damsel", "goon", "lunatic", "tinker",
            "xaan", "boomdandy", "widow", "assassin", "devilsadvocate",
            "po", "pukka", "shabaloth", "zombuul"]

SIX = scripts.from_ids("Sixth five, like Trouble Brewing", LIKE_TB)
SIX_BMR = scripts.from_ids("Sixth five, like Bad Moon Rising", LIKE_BMR)


def board(script, roles, infos=(), **kw):
    n = len(roles)
    world = World(tuple(roles), (None,) * n)
    state = GameState(n_players=n, script=script,
                      claims=dict(enumerate(roles)), infos=list(infos), **kw)
    return world, state


def cost(script, roles, infos=(), **kw):
    world, state = board(script, roles, infos, **kw)
    return S.explanation_cost(world, state)


def with_(roles, seat, role):
    out = list(roles)
    out[seat] = role
    return out


class TheyAreInTheCatalogue(SolverTest):

    def test_two_townsfolk_an_outsider_and_two_minions(self):
        teams = {key: CHARACTERS[key].team for key in SIXTH}
        self.assertEqual(teams, {"Preacher": "townsfolk",
                                 "Huntsman": "townsfolk",
                                 "Puzzlemaster": "outsider",
                                 "Xaan": "minion", "Boomdandy": "minion"})
        for key in SIXTH:
            self.assertTrue(CHARACTERS[key].modelled)

    def test_who_wakes(self):
        self.assertEqual(CHARACTERS["Preacher"].nights, "every")
        self.assertTrue(CHARACTERS["Preacher"].chooses)
        self.assertEqual(CHARACTERS["Huntsman"].nights, "conditional")
        self.assertIn("Huntsman", waking.CONDITION_RULES)
        for key in ("Puzzlemaster", "Xaan", "Boomdandy"):
            self.assertEqual(CHARACTERS[key].nights, "never")

    def test_the_named_games_do_not_draw_them(self):
        import play_games
        for seed in range(200):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  as_named=True)
            with self.subTest(seed=seed):
                self.assertFalse(set(SIXTH) & set(script.keys))

    def test_a_mixed_script_with_a_huntsman_has_the_damsel(self):
        import play_games
        drawn = 0
        for seed in range(400):
            script = play_games.an_awkward_script(random.Random(seed))
            if "Huntsman" in script.keys:
                drawn += 1
                self.assertIn("Damsel", script.keys)
        self.assertGreater(drawn, 10)


#            0       1         2           3             4
PREACH = ["Chef", "Empath", "Preacher", "Undertaker", "Washerwoman",
          "Poisoner", "Imp"]                                # 5, 6


class ThePreacher(SolverTest):

    def test_a_choice_alone_costs_nothing(self):
        self.assertEqual(cost(SIX, PREACH, [I.PreacherChoice(1, 2,
                                                             target=5)]), 1.0)

    def test_a_preached_poisoner_poisons_nobody(self):
        """Unless the Preacher was off when it chose, or now."""
        wrong = I.Empath(2, 1, count=2)
        preached = cost(SIX, PREACH, [I.PreacherChoice(1, 2, target=5),
                                      wrong])
        plain = cost(SIX, PREACH, [I.PreacherChoice(1, 2, target=0),
                                   wrong])
        self.assertEqual(plain, 0.35)
        self.assertLess(preached, plain)

    def test_a_preached_vizier_still_stands(self):
        roles = with_(PREACH, 5, "Vizier")
        world, state = board(SIX, roles, [I.PreacherChoice(1, 2, target=5)],
                             executions={1: 5})
        self.assertEqual(S.survivals_of(world, state, 1, 5), [5, 2])
        world, state = board(SIX, roles, executions={1: 5})
        self.assertEqual(S.survivals_of(world, state, 1, 5), [5])


#            0       1         2           3             4
HUNTED = ["Chef", "Empath", "Huntsman", "Undertaker", "Damsel",
          "ScarletWoman", "Imp"]                            # 5, 6


class TheHuntsman(SolverTest):

    def test_it_brings_the_damsel(self):
        self.assertEqual(CHARACTERS["Huntsman"].brings, ("Damsel",))
        self.assertFalse(seated_legally(tuple(with_(HUNTED, 4, "Mayor"))))
        # Seven players have no Outsider: the Damsel takes a Townsfolk's.
        self.assertEqual(cost(SIX, HUNTED), 1.0)
        worlds = enumerate_worlds(7, {0: "Chef", 1: "Empath",
                                      2: "Huntsman", 3: "Undertaker",
                                      4: "Damsel"}, script=SIX,
                                  max_worlds=50000)
        self.assertFalse(any("Huntsman" in w.roles
                             and "Damsel" not in w.roles for w in worlds))

    def test_a_damsel_found_is_a_townsfolk(self):
        roles = with_(HUNTED, 3, "Monk")
        rows = [I.HuntsmanChoice(2, 2, target=4),
                I.BecameInfo(2, 4, role="Undertaker", was="Damsel")]
        world, state = board(SIX, roles, rows)
        stories = S.possible_timelines(world, state)
        self.assertEqual(len(stories), 2)
        self.assertEqual(stories[1][0][0].role, "Undertaker")
        self.assertIsNotNone(S.explanation_cost(world, state))

    def test_nobody_found_or_the_damsel_turned(self):
        self.assertEqual(cost(SIX, HUNTED, [I.HuntsmanChoice(2, 2,
                                                             target=0)]), 1.0)
        self.assertEqual(cost(SIX, HUNTED, [I.HuntsmanChoice(2, 2,
                                                             target=4)]), 1.0)

    def test_a_minion_guessing_her_afterwards_wins_nothing(self):
        guess = I.DamselGuess(1, 5, target=4)
        self.assertIsNone(cost(SIX, HUNTED, [guess], days_done={1}))
        self.assertEqual(cost(SIX, HUNTED, [I.HuntsmanChoice(1, 2, target=4),
                                            guess], days_done={1}), 1.0)

    def test_it_wakes_until_it_chooses(self):
        world, state = board(SIX, HUNTED)
        self.assertEqual(waking.possible_counts(world, state, (2, 0), 1), {2})
        self.assertEqual(waking.possible_counts(world, state, (2, 0), 2),
                         {0, 1})
        world, state = board(SIX, HUNTED, [I.HuntsmanChoice(1, 2, target=0)])
        self.assertEqual(waking.possible_counts(world, state, (2, 3), 2), {0})


#            0       1         2               3             4
PUZZLED = ["Chef", "Empath", "Puzzlemaster", "Undertaker", "Washerwoman",
           "ScarletWoman", "Imp"]                           # 5, 6


class ThePuzzlemaster(SolverTest):

    def test_anybody_may_be_drunk_of_it_for_free(self):
        wrong = [I.Empath(1, 1, count=2)]
        self.assertEqual(cost(SIX, PUZZLED, wrong), 1.0)
        self.assertIsNone(cost(SIX, with_(PUZZLED, 2, "Saint"), wrong))

    def test_a_guess_shown_the_demon(self):
        guess = I.PuzzlemasterGuess(1, 2, guess=0, shown=6)
        self.assertEqual(guess.instead(*board(SIX, PUZZLED)),
                         (frozenset({0}), frozenset()))
        self.assertEqual(cost(SIX, PUZZLED, [guess]), 1.0)

    def test_a_guess_shown_anybody_else_says_nothing(self):
        guess = I.PuzzlemasterGuess(1, 2, guess=0, shown=3)
        self.assertIsNone(guess.instead(*board(SIX, PUZZLED)))
        self.assertEqual(cost(SIX, PUZZLED, [guess]), 1.0)


class TheXaan(SolverTest):

    def test_any_number_of_outsiders(self):
        worlds = enumerate_worlds(7, {0: "Chef", 1: "Empath", 2: "Saint",
                                      3: "Recluse", 4: "Puzzlemaster",
                                      5: "Monk", 6: "Mayor"},
                                  script=SIX, max_worlds=50000)
        self.assertTrue(worlds)
        self.assertTrue(all("Xaan" in w.roles for w in worlds))
        self.assertEqual(cost(SIX, ["Chef", "Empath", "Mayor", "Undertaker",
                                    "Washerwoman", "Xaan", "Imp"]), 1.0)

    def test_night_x_poisons_the_town(self):
        one = ["Chef", "Empath", "Saint", "Undertaker", "Washerwoman",
               "Xaan", "Imp"]
        wrong = [I.Empath(1, 1, count=2)]
        self.assertEqual(cost(SIX, one, wrong), 1.0)
        none = with_(one, 2, "Mayor")
        self.assertIsNone(cost(SIX, none, wrong))
        # Night two is not night X.
        self.assertIsNone(cost(SIX, one, [I.Empath(2, 1, count=2)]))

    def test_a_reading_true_that_night_needs_the_xaan_off(self):
        one = ["Chef", "Empath", "Saint", "Undertaker", "Washerwoman",
               "Xaan", "Imp", "Poisoner", "Monk"]
        world, state = board(SIX, one)
        self.assertEqual(S.explanation_cost(world, state), 1.0)

    def test_the_mathematician_is_poisoned_too(self):
        roles = ["Mathematician", "Empath", "Saint", "Undertaker",
                 "Washerwoman", "Xaan", "Imp"]
        said = [I.MathematicianInfo(1, 0, count=3)]
        self.assertEqual(cost(SIX, roles, said), 1.0)
        self.assertIsNone(cost(SIX, with_(roles, 2, "Mayor"), said))


#              0       1         2        3             4
BOOM = ["Chef", "Empath", "Mayor", "Undertaker", "Washerwoman",
        "Boomdandy", "Imp"]                                 # 5, 6


class TheBoomdandy(SolverTest):

    def test_executed_it_explodes(self):
        rows = [I.BoomdandyExploded(1, 5, pointed=0)]
        dead = {5: ("E1",), 1: ("D1",), 2: ("D1",), 0: ("D1",)}
        self.assertEqual(cost(SIX, BOOM, rows, deaths=dead,
                              game_over=True), 1.0)
        rows = [I.BoomdandyExploded(1, 4, pointed=0)]
        dead = {4: ("E1",), 1: ("D1",), 2: ("D1",), 0: ("D1",)}
        self.assertIsNone(cost(SIX, BOOM, rows, deaths=dead,
                               game_over=True))

    def test_never_the_demon_but_by_pointing(self):
        rows = [I.BoomdandyExploded(1, 5, pointed=0)]
        dead = {5: ("E1",), 6: ("D1",), 2: ("D1",), 0: ("D1",)}
        self.assertIsNone(cost(SIX, BOOM, rows, deaths=dead, game_over=True))

    def test_the_demon_pointed_at_and_good_wins(self):
        rows = [I.BoomdandyExploded(1, 5, pointed=6)]
        dead = {5: ("E1",), 1: ("D1",), 2: ("D1",), 6: ("D1",)}
        self.assertEqual(cost(SIX, BOOM, rows, deaths=dead,
                              game_over=True), 1.0)
        self.assertIsNone(cost(SIX, BOOM, rows, deaths=dead))


class TheSimulatorPlaysThem(SolverTest):

    def played(self, script, games, nights=4):
        import claims as claim_model
        import simulate
        seen, lost, ends = {}, [], {}
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
            for row in heard:
                seen[type(row).__name__] = seen.get(type(row).__name__, 0) + 1
            ends[deal.ended_why] = ends.get(deal.ended_why, 0) + 1
            truth = World(tuple(deal.roles), tuple(deal.believes))
            if S.explanation_cost(truth, state) is None:
                lost.append(seed)
        return seen, lost, ends

    def test_like_trouble_brewing(self):
        seen, lost, ends = self.played(SIX, 300)
        self.assertEqual(lost, [])
        for what in ("PreacherChoice", "HuntsmanChoice", "PuzzlemasterGuess",
                     "BoomdandyExploded"):
            self.assertGreater(seen.get(what, 0), 5, what)
        self.assertGreater(ends.get("boomdandy", 0), 5)

    def test_like_bad_moon_rising(self):
        seen, lost, _ends = self.played(SIX_BMR, 300)
        self.assertEqual(lost, [])

    def games(self, script, how_many=300):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=4,
                                      script=script)

    def test_a_huntsman_is_never_dealt_without_the_damsel(self):
        dealt = 0
        for script in (SIX, SIX_BMR):
            for seed, (deal, _heard) in self.games(script):
                if "Huntsman" in deal.roles:
                    dealt += 1
                    with self.subTest(script=script.name, seed=seed):
                        self.assertIn("Damsel", deal.roles)
        self.assertGreater(dealt, 50)

    def test_the_xaan_poisons_on_its_night_only(self):
        import simulate
        nights = 0
        for seed, (deal, _heard) in self.games(SIX):
            if "Xaan" not in deal.roles:
                continue
            x = sum(1 for r in deal.roles
                    if CHARACTERS[r].team == "outsider")
            town = [p for p in range(deal.n)
                    if CHARACTERS[deal.roles[p]].team == "townsfolk"
                    and deal.role_at(p, f"N{x}") == deal.roles[p]]
            if x < 1 or x > deal.nights_played or not town:
                continue
            xaan = deal.roles.index("Xaan")
            if xaan not in deal.alive_at(f"N{x}"):
                continue
            if xaan in simulate.droisoned_at(deal, x):
                continue
            nights += 1
            with self.subTest(seed=seed):
                self.assertLessEqual(set(town),
                                     simulate.droisoned_at(deal, x))
        self.assertGreater(nights, 10)

    def test_a_boomdandy_ends_the_game(self):
        for script in (SIX, SIX_BMR):
            for seed, (deal, heard) in self.games(script):
                rows = [r for r in heard if isinstance(r, I.BoomdandyExploded)]
                with self.subTest(script=script.name, seed=seed):
                    self.assertLessEqual(len(rows), 1)
                    if rows:
                        self.assertEqual(deal.ended_why, "boomdandy")
                        alive = [p for p in range(deal.n)
                                 if deal.deaths.get(p) is None]
                        self.assertLessEqual(len(alive), 4)

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


KNOWN_47 = {("Sixth five, like Bad Moon Rising", 44, 4)}


class TheNightWalkReplaysThem(SolverTest):
    """The Preacher and the Huntsman act at their slots; the rest are
    standing droisonings or daylight."""

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = 0
        for script in (SIX, SIX_BMR):
            for seed in range(150):
                n = [7, 8, 9, 10, 11][seed % 5]
                deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                            script=script)
                for night in range(2, deal.nights_played + 1):
                    # Open point 47: the Pukka's token from the night
                    # before, and the Pukka drunk by the Goon tonight.
                    if (script.name, seed, night) in KNOWN_47:
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
