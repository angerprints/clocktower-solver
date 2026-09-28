"""Random scripts, and the things that have to be true on all of them.

Every other test file states what one character does. This one states
what the machinery has to do *whatever* characters it is handed — so it
builds scripts nobody has played, deals boards on them, and walks a great
many worlds looking for something that does not hold.

The point is combinations. Trouble Brewing and Bad Moon Rising are two
selections out of an enormous number, and each of them exercises its own
characters against its own neighbours. A Tea Lady has never sat next to a
Recluse; a Goon has never been drunked by a Poisoner; a Pukka has never
had to explain a body beside a Soldier. Those pairings are where a rule
that quietly assumes its own script goes wrong.

Nothing here checks that an answer is *right* — that is what the oracle
and the per-character files are for. These check that the machinery stays
coherent: legal worlds, well-formed rules, sane numbers, and nothing that
crashes or hangs.
"""

import random
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import deaths, impairment, limits, scripts  # noqa: E402
from botc.catalogue import CHARACTERS             # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.roles import SETUP, believed_tokens, believes_another, TEAM  # noqa: E402
from botc.worlds import _bags, enumerate_worlds   # noqa: E402

# Everything the catalogue holds that can be dealt and is not refused
# outright. The Fabled are excluded because they take no seat; Legion and
# Riot because the solver declines them by name.
POOL = {team: sorted(k for k, c in CHARACTERS.items()
                     if c.team == team and c.seated
                     and k not in limits.UNSUPPORTED)
        for team in ("townsfolk", "outsider", "minion", "demon")}

SHAPE = {"townsfolk": 13, "outsider": 4, "minion": 4, "demon": 2}


def a_script(rng, name="Random"):
    """A script of the usual shape, drawn from everything known."""
    keys = []
    for team, count in SHAPE.items():
        keys.extend(rng.sample(POOL[team], count))
    return scripts.Script(name=name, keys=tuple(keys))


def a_board(rng, script, n_players):
    """A board of that size: everybody claims something on the script.

    Claims rather than silence, because an unclaimed table is both
    enormous and uninformative — the interesting behaviour is in how
    claims and readings cut it down.

    Enough Outsider claims to fill the bag, because otherwise most boards
    come back with no worlds at all: twelve seats all claiming Townsfolk
    cannot be a game, and a board that is not a game says nothing about
    whether the machinery works.
    """
    wanted = max(counts["outsider"] for _p, counts in _bags(n_players, script))
    seats = list(range(n_players))
    rng.shuffle(seats)
    claims = {}
    for seat in seats[:wanted]:
        claims[seat] = rng.choice(script.outsiders)
    for seat in seats[wanted:]:
        claims[seat] = rng.choice(script.townsfolk)
    return GameState(n_players=n_players, script=script, claims=claims)


class TheScriptsThemselves(SolverTest):

    def test_every_one_of_them_is_playable(self):
        rng = random.Random(1)
        for i in range(60):
            script = a_script(rng)
            with self.subTest(script=i):
                self.assertTrue(script.is_playable())
                self.assertEqual(len(script.keys), 23)
                self.assertEqual(len(set(script.keys)), 23,
                                 "no character twice")

    def test_every_bag_seats_the_whole_table(self):
        """The invariant that caught the Sentinel: a modifier that moves
        one number without moving another back deals a game of the wrong
        size, and produces worlds that look perfectly ordinary."""
        rng = random.Random(2)
        for i in range(30):
            script = a_script(rng)
            for n in range(5, 16):
                for _present, counts in _bags(n, script):
                    with self.subTest(script=i, players=n):
                        self.assertEqual(sum(counts.values()), n)

    def test_no_bag_asks_for_more_characters_than_exist(self):
        rng = random.Random(3)
        for i in range(30):
            script = a_script(rng)
            room = {t: len(script.by_team(t)) for t in SHAPE}
            for n in range(5, 16):
                for _present, counts in _bags(n, script):
                    for team, want in counts.items():
                        with self.subTest(script=i, players=n, team=team):
                            self.assertLessEqual(want, room[team])
                            self.assertGreaterEqual(want, 0)


class EveryWorldIsALegalGame(SolverTest):
    """The floor everything else stands on."""

    def worlds(self, seed, n_players=9, cap=1500):
        rng = random.Random(seed)
        script = a_script(rng)
        state = a_board(rng, script, n_players)
        got = enumerate_worlds(n_players, state.claims, script=script,
                               max_worlds=cap)
        return script, state, got

    def test_nobody_holds_two_characters_and_nothing_is_held_twice(self):
        for seed in range(25):
            script, _state, worlds = self.worlds(seed)
            for world in worlds:
                with self.subTest(seed=seed):
                    self.assertEqual(len(set(world.roles)), len(world.roles))
                    self.assertLessEqual(set(world.roles), set(script.keys))

    def test_the_team_counts_match_one_of_the_bags(self):
        for seed in range(25):
            script, state, worlds = self.worlds(seed)
            shapes = {tuple(sorted(c.items()))
                      for _p, c in _bags(state.n_players, script)}
            for world in worlds:
                got = {t: 0 for t in SHAPE}
                for role in world.roles:
                    got[TEAM[role]] += 1
                with self.subTest(seed=seed):
                    self.assertIn(tuple(sorted(got.items())), shapes)

    def test_a_believer_holds_a_token_nobody_else_has(self):
        """Somebody handed the wrong character consumes their own slot
        *and* the token they think they hold."""
        for seed in range(25):
            script, _state, worlds = self.worlds(seed)
            for world in worlds:
                for seat, role in enumerate(world.roles):
                    token = world.believes[seat]
                    with self.subTest(seed=seed, seat=seat):
                        if believes_another(role):
                            self.assertIsNotNone(token, f"{role} with none")
                            self.assertIn(token,
                                          believed_tokens(role, script))
                            self.assertNotIn(token, world.roles)
                        else:
                            self.assertIsNone(token)


class EveryRuleStaysWellFormed(SolverTest):
    """Each registered rule, against worlds from scripts it has never
    seen. A rule that quietly assumes its own script shows up here."""

    def sweep(self, seed=7, scripts_tried=60, worlds_each=120):
        rng = random.Random(seed)
        for _ in range(scripts_tried):
            script = a_script(rng)
            n = rng.choice((7, 9, 12))
            state = a_board(rng, script, n)
            worlds = enumerate_worlds(n, state.claims, script=script,
                                      max_worlds=worlds_each)
            for world in worlds:
                yield script, state, world, rng.choice((2, 3, 4))

    def test_causes_are_sane(self):
        seen = set()
        for _script, state, world, night in self.sweep():
            for cause in deaths.causes_on(world, state, night):
                seen.add(cause.name)
                self.assertIn(cause.kind, (deaths.DEMON, deaths.OTHER))
                self.assertGreaterEqual(cause.capacity, 1)
                self.assertGreater(cause.cost, 0.0)
                self.assertLessEqual(cause.cost, 1.0)
                self.assertLessEqual(set(cause.seats),
                                     set(range(state.n_players)))
        self.assertGreater(len(seen), 3, f"only {seen} ever fired")

    def test_shields_are_sane(self):
        for _script, state, world, night in self.sweep(seed=8):
            for seat in range(state.n_players):
                for kind in (deaths.DEMON, deaths.OTHER):
                    for shield in deaths.shields_on(world, state, night,
                                                    seat, kind):
                        self.assertTrue(shield.by)
                        self.assertGreater(shield.cost, 0.0)
                        self.assertLessEqual(shield.cost, 1.0)
                        if shield.needs is not None:
                            self.assertIn(shield.needs,
                                          range(state.n_players))

    def test_impairment_sources_are_sane(self):
        seen = set()
        for _script, state, world, night in self.sweep(seed=9):
            for source in impairment.sources_on(world, state, night):
                seen.add(source.name)
                self.assertGreaterEqual(source.capacity, 1)
                self.assertLessEqual(source.capacity, state.n_players)
                self.assertLessEqual(set(source.seats),
                                     set(range(state.n_players)))
                for seat in source.seats:
                    self.assertGreater(source.price(seat), 0.0)
                    self.assertLessEqual(source.price(seat), 1.0)
        self.assertGreater(len(seen), 2, f"only {seen} ever fired")

    def test_implications_point_at_real_seats(self):
        for _script, state, world, night in self.sweep(seed=10):
            for victim in range(state.n_players):
                for kind in (deaths.DEMON, deaths.OTHER):
                    for hit in deaths.implications_of(world, state, night,
                                                      victim, kind):
                        self.assertIn(hit.seat, range(state.n_players))
                        self.assertIn(hit.needs, range(state.n_players))

    def test_exactly_one_demon_rule_answers_for_any_world(self):
        """Four Demons kill four different ways, and two of them
        answering for the same world would double the kills."""
        for _script, state, world, night in self.sweep(seed=11):
            firing = [c for c in deaths.causes_on(world, state, night)
                      if c.name == "Demon"]
            self.assertLessEqual(len(firing), 1, f"{firing}")


class TheNumbersStayCoherent(SolverTest):

    def boards(self, seed=13, count=20):
        rng = random.Random(seed)
        for _ in range(count):
            script = a_script(rng)
            yield a_board(rng, script, rng.choice((7, 9)))

    def test_a_board_with_nothing_recorded_rules_nothing_out(self):
        """No readings, no deaths — so every legal world is still live.
        A world going missing here means something is being ruled out by
        nothing at all."""
        for state in self.boards(seed=14, count=15):
            legal, valid = S.solve(state)
            with self.subTest(script=state.script.keys[:3]):
                self.assertEqual(len(valid), len(legal))

    def test_every_cost_is_a_weight_or_nothing(self):
        rng = random.Random(15)
        for state in self.boards(seed=15, count=12):
            worlds = enumerate_worlds(state.n_players, state.claims,
                                      script=state.script, max_worlds=40)
            for world in worlds:
                cost = S.explanation_cost(world, state)
                with self.subTest(script=state.script.name):
                    if cost is not None:
                        self.assertGreater(cost, 0.0)
                        self.assertLessEqual(cost, 1.0)

    def test_the_percentages_are_percentages(self):
        looked = 0
        for state in self.boards(seed=16, count=10):
            result = S.analyze(state)
            if not result["valid"]:
                continue                  # not a game; nothing to report on
            looked += 1
            for row in result["rows"]:
                with self.subTest(seat=row["player"]):
                    for key in ("evil_pct", "demon_pct", "drunk_pct",
                                "lying_pct"):
                        self.assertBetween(row[key], 0.0, 100.0)
                    self.assertPct(sum(p for _r, p in row["roles"]),
                                   100.0, 0.5)
                    self.assertLessEqual(row["demon_pct"],
                                         row["evil_pct"] + 0.001,
                                         "the Demon is on the evil team")
        self.assertGreater(looked, 5, "too few solvable boards to judge")

    def test_exactly_one_demon_between_them(self):
        """Every seat's chance of being the Demon, added up, is one
        Demon — whatever the script."""
        # Several seeds, for the same reason as the test below: pinned to
        # one, the count of solvable boards drifts every time a character
        # is added, and that is not what this is testing.
        looked = 0
        for seed in (17, 18, 19):
            for state in self.boards(seed=seed, count=10):
                result = S.analyze(state)
                if not result["valid"]:
                    continue
                looked += 1
                total = sum(r["demon_pct"] for r in result["rows"])
                with self.subTest(seed=seed, script=state.script.keys[:3]):
                    self.assertPct(total, 100.0, 1.0)
        self.assertGreater(looked, 5, "too few solvable boards to judge")

    def test_most_generated_boards_are_actually_games(self):
        """Guards the guards: if the generator mostly produced boards
        with no worlds, every property above would pass vacuously."""
        # Across several seeds rather than one.
        #
        # Pinned to seed 18 this asserted more than fifteen of twenty and
        # got exactly fifteen the day the Balloonist was added — not
        # because anything broke, but because a new Townsfolk appears in
        # half of all random scripts and every extra character makes the
        # bag maths a little tighter. A single seed cannot tell that from
        # a regression.
        #
        # Four seeds give eighty per cent, and the claim being made here
        # is "mostly", not "sixteen of twenty on this particular seed".
        solvable = total = 0
        for seed in (18, 19, 20, 21):
            for state in self.boards(seed=seed, count=20):
                total += 1
                solvable += bool(S.solve(state)[1])
        self.assertGreater(solvable / total, 0.7,
                           f"only {solvable}/{total} were games")


class AddingWhatIsKnownNeverAddsWorlds(SolverTest):
    """Every fact narrows or leaves alone. Nothing widens."""

    def setup_board(self, seed):
        rng = random.Random(seed)
        script = a_script(rng)
        return rng, script, a_board(rng, script, 9)

    def test_a_death_never_makes_more_worlds_possible(self):
        for seed in range(20, 32):
            _rng, script, bare = self.setup_board(seed)
            with_death = GameState(n_players=9, script=script,
                                   claims=bare.claims, deaths={3: "N2"})
            with self.subTest(seed=seed):
                self.assertLessEqual(len(S.solve(with_death)[1]),
                                     len(S.solve(bare)[1]))

    def test_a_reading_never_makes_more_worlds_possible(self):
        from botc.info import Empath
        for seed in range(40, 52):
            _rng, script, bare = self.setup_board(seed)
            if "Empath" not in script.keys:
                continue
            speaker = next((s for s, c in bare.claims.items()
                            if c == "Empath"), 0)
            told = GameState(n_players=9, script=script, claims=bare.claims,
                             infos=[Empath(1, speaker, count=1)])
            with self.subTest(seed=seed):
                self.assertLessEqual(len(S.solve(told)[1]),
                                     len(S.solve(bare)[1]))

    def test_pinning_a_seat_never_makes_more_worlds_possible(self):
        for seed in range(60, 72):
            _rng, script, bare = self.setup_board(seed)
            sure = GameState(n_players=9, script=script, claims=bare.claims,
                             certainties={0: "confirmed"})
            with self.subTest(seed=seed):
                self.assertLessEqual(len(S.solve(sure)[1]),
                                     len(S.solve(bare)[1]))


class EveryRuleIsActuallyReached(SolverTest):
    """Guards the guards again. A sweep that never puts a Pukka on a
    script proves nothing about the Pukka, and would pass in silence."""

    def test_the_sweep_reaches_every_character_that_has_a_rule(self):
        rng = random.Random(77)
        seen = set()
        for _ in range(120):
            seen.update(a_script(rng).keys)
        has_a_rule = {
            "Soldier", "Monk", "Sailor", "Innkeeper", "Exorcist", "TeaLady",
            "Fool", "Pacifist", "DevilsAdvocate", "Godfather", "Assassin",
            "Mastermind", "Gossip", "Gambler", "Tinker", "Moonchild",
            "Courtier", "Minstrel", "Goon", "Professor", "Grandmother",
            "Chambermaid", "Poisoner", "Drunk", "Imp", "Zombuul", "Pukka",
            "Shabaloth", "Po",
        }
        missing = has_a_rule - seen
        self.assertEqual(missing, set(),
                         f"never put on any random script: {sorted(missing)}")


class NothingCrashesOrRunsAway(SolverTest):
    """Boards built out of whatever the generator felt like, solved end
    to end. No assertion beyond: it finishes, and it answers."""

    def test_a_spread_of_boards_all_solve(self):
        rng = random.Random(99)
        for i in range(25):
            script = a_script(rng)
            n = rng.choice((5, 6, 7, 8, 9))
            state = a_board(rng, script, n)
            # Some deaths, some quiet nights, some readings.
            deaths_ = {}
            for seat in rng.sample(range(n), rng.randint(0, 2)):
                deaths_[seat] = rng.choice(("N2", "N3", "E1", "D2"))
            state = GameState(n_players=n, script=script, claims=state.claims,
                              deaths=deaths_,
                              quiet_nights=set(rng.sample([2, 3],
                                                          rng.randint(0, 1))))
            with self.subTest(board=i):
                result = S.analyze(state)
                self.assertEqual(len(result["rows"]), n)
                self.assertGreaterEqual(result["valid"], 0)

    def test_a_script_the_solver_refuses_is_refused_whatever_else_is_on_it(self):
        rng = random.Random(100)
        for i in range(10):
            script = a_script(rng)
            with_legion = scripts.Script(name="With Legion",
                                         keys=script.keys + ("Legion",))
            with self.subTest(script=i):
                self.assertIn("Legion", limits.refuses(with_legion))


if __name__ == "__main__":
    unittest.main()
