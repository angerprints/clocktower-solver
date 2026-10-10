"""The fourth four experimental characters (10.10.2026).

Damsel, Fearmonger, Vizier and Organ Grinder — the last small ones. Each
leaves a row on the board or changes the vote, and every reading here is
the table's ruling of 10.10.2026, asked before anything was built:

  * A **Damsel** guessed by the Minions' first public guess loses her
    team the game. A Demon's or a good player's guess spends nothing. A
    drunk or poisoned Minion guessing right still wins; a drunk or
    poisoned Damsel ends nothing, and the guess is spent. A Spy in play,
    ever, poisons her (their jinx).
  * A **Fearmonger** chooses a player every night, and the table is told
    when the player is a new one — drunk or poisoned too. Its win needs
    the hidden choice, so only the simulator plays it.
  * A **Vizier** is announced on its first day if it has its ability
    then, and cannot die during the day — drunk or poisoned it can, but
    not when a Courtier made it drunk (their jinx). It wakes with a
    Fearmonger, for the Chambermaid.
  * An **Organ Grinder** has everybody vote with their eyes closed while
    it works. A day with votes on the board had no working one; being
    drunk by its own choice costs nothing, and a Mathematician does not
    count it.

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
from botc.worlds import World                     # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))

FOURTH = ("Damsel", "Fearmonger", "Vizier", "OrganGrinder")

# Trouble Brewing's shape, with the Magician the Vizier has a jinx with.
LIKE_TB = ["washerwoman", "librarian", "chef", "empath", "fortuneteller",
           "undertaker", "monk", "ravenkeeper", "virgin", "slayer",
           "soldier", "mayor", "magician",
           "damsel", "saint", "recluse", "drunk",
           "fearmonger", "vizier", "organgrinder", "poisoner",
           "imp"]
# Bad Moon Rising's, with a Chambermaid, a Flowergirl that asks about
# votes, and a Spy that poisons the Damsel.
LIKE_BMR = ["grandmother", "sailor", "chambermaid", "exorcist", "innkeeper",
            "gambler", "gossip", "courtier", "professor", "minstrel",
            "tealady", "pacifist", "flowergirl",
            "damsel", "goon", "lunatic", "tinker",
            "fearmonger", "vizier", "organgrinder", "spy",
            "po", "pukka"]

FOUR = scripts.from_ids("Fourth four, like Trouble Brewing", LIKE_TB)
FOUR_BMR = scripts.from_ids("Fourth four, like Bad Moon Rising", LIKE_BMR)


def board(script, roles, infos=(), **kw):
    n = len(roles)
    world = World(tuple(roles), (None,) * n)
    state = GameState(n_players=n, script=script,
                      claims=dict(enumerate(roles)), infos=list(infos), **kw)
    return world, state


def cost(script, roles, infos=(), **kw):
    world, state = board(script, roles, infos, **kw)
    return S.explanation_cost(world, state)


#        0       1         2             3         4
SEVEN = ["Chef", "Empath", "Undertaker", "Damsel", "Soldier",
         "Fearmonger", "Imp"]                                # 5, 6


class TheyAreInTheCatalogue(SolverTest):

    def test_an_outsider_and_three_minions(self):
        teams = {key: CHARACTERS[key].team for key in FOURTH}
        self.assertEqual(teams, {"Damsel": "outsider",
                                 "Fearmonger": "minion",
                                 "Vizier": "minion",
                                 "OrganGrinder": "minion"})
        for key in FOURTH:
            self.assertTrue(CHARACTERS[key].modelled)

    def test_who_wakes(self):
        self.assertEqual(CHARACTERS["Damsel"].nights, "never")
        self.assertEqual(CHARACTERS["Fearmonger"].nights, "every")
        self.assertTrue(CHARACTERS["Fearmonger"].chooses)
        self.assertEqual(CHARACTERS["OrganGrinder"].nights, "every")
        self.assertFalse(CHARACTERS["OrganGrinder"].chooses)
        self.assertEqual(CHARACTERS["Vizier"].nights, "conditional")
        self.assertIn("Vizier", waking.CONDITION_RULES)

    def test_the_named_games_do_not_draw_them(self):
        import play_games
        for seed in range(200):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  as_named=True)
            with self.subTest(seed=seed):
                self.assertFalse(set(FOURTH) & set(script.keys))


class AMinionGuessesTheDamsel(SolverTest):
    """Seat 5 holds the Fearmonger — a Minion — and seat 3 the Damsel."""

    def guess(self, by, at, day=1):
        return I.DamselGuess(day, by, target=at)

    def test_right_and_the_game_went_on_needs_her_off(self):
        rows = [self.guess(5, 3)]
        self.assertEqual(cost(FOUR, SEVEN, rows), 1.0)  # read that evening
        self.assertIsNone(cost(FOUR, SEVEN, rows, days_done={1}))

    def test_a_poisoner_can_be_the_reason(self):
        roles = SEVEN[:5] + ["Poisoner", "Imp"]
        self.assertIsNotNone(cost(FOUR, roles, [self.guess(5, 3)],
                                  days_done={1}))

    def test_wrong_says_nothing(self):
        self.assertEqual(cost(FOUR, SEVEN, [self.guess(5, 1)],
                              days_done={1}), 1.0)

    def test_only_a_minions_guess_counts(self):
        for by in (0, 6):                 # a Chef and the Imp
            with self.subTest(by=by):
                self.assertEqual(cost(FOUR, SEVEN, [self.guess(by, 3)],
                                      days_done={1}), 1.0)

    def test_only_the_minions_first(self):
        rows = [self.guess(5, 1), self.guess(5, 3, day=2)]
        self.assertEqual(cost(FOUR, SEVEN, rows, days_done={1, 2}), 1.0)
        # And a good player's guess before it spends nothing.
        rows = [self.guess(0, 1), self.guess(5, 3, day=2)]
        self.assertIsNone(cost(FOUR, SEVEN, rows, days_done={1, 2}))

    def test_a_dead_damsel_has_no_ability(self):
        self.assertIsNotNone(cost(FOUR, SEVEN, [self.guess(5, 3, day=2)],
                                  days_done={1, 2}, deaths={3: ("N2",)}))

    def test_a_spy_in_play_poisons_her(self):
        roles = SEVEN[:5] + ["Spy", "Imp"]
        self.assertEqual(cost(FOUR_BMR, roles, [self.guess(5, 3)],
                              days_done={1}), 1.0)


class TheFearmongerChose(SolverTest):

    def test_a_fact_that_one_was_alive_and_chose(self):
        row = I.FearmongerChose(1, 0)
        self.assertTrue(row.hard())
        self.assertEqual(cost(FOUR, SEVEN, [row]), 1.0)
        roles = SEVEN[:5] + ["Poisoner", "Imp"]
        self.assertIsNone(cost(FOUR, roles, [row]))

    def test_drunk_or_poisoned_it_is_announced_too(self):
        roles = ["Chef", "Empath", "Undertaker", "Damsel", "Soldier",
                 "Fearmonger", "Imp", "Monk", "Poisoner"]
        world, state = board(FOUR, roles, [I.FearmongerChose(2, 0)])
        _f, _ft, _c, working = S._plain_failures(world, state)
        self.assertFalse(any(5 in seats for seats in working.values()))

    def test_dead_it_chooses_nobody(self):
        self.assertIsNone(cost(FOUR, SEVEN, [I.FearmongerChose(2, 0)],
                               deaths={5: ("D1",)}))


class TheVizier(SolverTest):

    def roles(self):
        return SEVEN[:5] + ["Vizier", "Imp"]

    def test_announced_on_its_first_day_and_working(self):
        row = I.VizierAnnounced(1, 5)
        self.assertEqual(cost(FOUR, self.roles(), [row]), 1.0)
        world, state = board(FOUR, self.roles(), [row])
        _f, _ft, _c, working = S._plain_failures(world, state)
        self.assertIn(5, working.get(1, ()))
        # Nobody else is the Vizier.
        self.assertIsNone(cost(FOUR, self.roles(), [I.VizierAnnounced(1, 4)]))

    def test_not_on_a_later_day(self):
        self.assertIsNone(cost(FOUR, self.roles(),
                               [I.VizierAnnounced(2, 5)]))

    def test_it_walks_away_from_the_gallows(self):
        self.assertEqual(cost(FOUR, self.roles(), executions={1: 5}), 1.0)

    def test_executed_and_dead_it_was_not_working(self):
        self.assertIsNone(cost(FOUR, self.roles(), executions={1: 5},
                               deaths={5: ("D1",)}))
        roles = self.roles()[:4] + ["Poisoner"] + ["Vizier", "Imp"]
        roles = ["Chef", "Empath", "Undertaker", "Damsel", "Poisoner",
                 "Vizier", "Imp", "Monk", "Soldier"]
        self.assertIsNotNone(cost(FOUR, roles, executions={1: 5},
                                  deaths={5: ("D1",)}))

    def test_a_courtier_drunk_vizier_still_stands(self):
        """Their jinx: two ways to have walked away, so neither is
        demanded."""
        roles = ["Chambermaid", "Courtier", "Gambler", "Gossip", "Sailor",
                 "Vizier", "Po"]
        named = I.CourtierChoice(1, 1, role="Vizier")
        world, state = board(FOUR_BMR, roles, [named], executions={1: 5})
        self.assertEqual(sorted(S.survivals_of(world, state, 1, 5)), [1, 5])
        self.assertIsNotNone(S.explanation_cost(world, state))

    def test_it_wakes_beside_a_fearmonger(self):
        roles = ["Chambermaid", "Grandmother", "Gambler", "Gossip",
                 "Fearmonger", "Vizier", "Po", "Sailor", "Professor"]
        world, state = board(FOUR_BMR, roles)
        self.assertEqual(waking.possible_counts(world, state, (5, 3), 2),
                         {1})
        roles[4] = "Spy"
        world, state = board(FOUR_BMR, roles)
        self.assertEqual(waking.possible_counts(world, state, (5, 3), 2),
                         {0})


class TheOrganGrinder(SolverTest):

    def roles(self):
        return SEVEN[:5] + ["OrganGrinder", "Imp"]

    def test_eyes_closed_says_it_was_alive_and_working(self):
        row = I.BlindVote(1, 0)
        self.assertEqual(cost(FOUR, self.roles(), [row]), 1.0)
        self.assertIsNone(cost(FOUR, SEVEN, [row]))
        self.assertIsNone(cost(FOUR, self.roles(), [row],
                               deaths={5: ("N1",)}))

    def test_votes_on_the_board_need_it_drunk_which_is_free(self):
        voted = {1: {0, 1}}
        world, state = board(FOUR, self.roles(), votes=voted)
        failures, _ft, _c, _w = S._plain_failures(world, state)
        self.assertIn(5, failures.get(1, ()))
        self.assertEqual(S.explanation_cost(world, state), 1.0)

    def test_not_both(self):
        self.assertIsNone(cost(FOUR, self.roles(), [I.BlindVote(1, 0)],
                               votes={1: {0, 1}}))

    def test_a_mathematician_does_not_count_its_own_drink(self):
        roles = ["Mathematician", "Empath", "Undertaker", "Damsel",
                 "Soldier", "OrganGrinder", "Imp"]
        script = scripts.from_ids("Fourth four, with a Mathematician",
                                  LIKE_TB + ["mathematician"])
        self.assertEqual(cost(script, roles,
                              [I.MathematicianInfo(1, 0, count=0)]), 1.0)
        self.assertIsNone(cost(script, roles,
                               [I.MathematicianInfo(1, 0, count=1)]))

    def test_a_flowergirl_has_nothing_to_go_on(self):
        roles = ["Flowergirl", "Grandmother", "Gambler", "Gossip",
                 "Professor", "OrganGrinder", "Po"]
        said = I.FlowergirlInfo(2, 0, voted=True)
        self.assertIsNone(cost(FOUR_BMR, roles, [said]))
        self.assertEqual(cost(FOUR_BMR, roles,
                              [said, I.BlindVote(1, 1)]), 1.0)


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
        seen, lost, ends = self.played(FOUR, 300)
        self.assertEqual(lost, [])
        for what in ("DamselGuess", "FearmongerChose", "VizierAnnounced",
                     "BlindVote"):
            self.assertGreater(seen.get(what, 0), 20, what)
        for why in ("damsel", "fearmonger"):
            self.assertGreater(ends.get(why, 0), 5, why)

    def test_like_bad_moon_rising(self):
        seen, lost, _ends = self.played(FOUR_BMR, 300)
        self.assertEqual(lost, [])

    def games(self, script, how_many=300):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=4,
                                      script=script)

    def test_no_votes_are_written_down_on_a_blind_day(self):
        days = 0
        for script in (FOUR, FOUR_BMR):
            for seed, (deal, heard) in self.games(script):
                blind = {r.night for r in heard if isinstance(r, I.BlindVote)}
                self.assertEqual(blind, deal.blind_days)
                for day in blind:
                    days += 1
                    with self.subTest(script=script.name, seed=seed):
                        self.assertFalse(deal.votes.get(day))
        self.assertGreater(days, 50)

    def test_a_vizier_is_announced_once_on_its_first_day(self):
        said = 0
        for seed, (deal, heard) in self.games(FOUR):
            rows = [r for r in heard if isinstance(r, I.VizierAnnounced)]
            self.assertLessEqual(len(rows), 1)
            for row in rows:
                said += 1
                self.assertEqual(deal.role_at(row.player, f"D{row.night}"),
                                 "Vizier")
                self.assertTrue(deal.working(row.player, row.night,
                                             by_day=True))
        self.assertGreater(said, 20)

    def test_the_fearmonger_announces_only_a_new_player(self):
        for seed, (deal, heard) in self.games(FOUR):
            nights = {r.night for r in heard
                      if isinstance(r, I.FearmongerChose)}
            last = None
            for night in sorted(deal.fear_chose):
                with self.subTest(seed=seed, night=night):
                    self.assertEqual(night in nights,
                                     deal.fear_chose[night] != last)
                last = deal.fear_chose[night]

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


class TheNightWalkReplaysThem(SolverTest):
    """Only the Fearmonger points at anybody at night, and only a Goon
    notices — so the walk is told whom and nothing else changes."""

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = 0
        for script in (FOUR, FOUR_BMR):
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
