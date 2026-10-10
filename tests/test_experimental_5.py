"""The fifth five experimental characters (10.10.2026).

Choirboy, Princess, Golem, Psychopath and Widow — the first of the
middling ones. Every reading here is the table's ruling of 10.10.2026,
asked before anything was built:

  * A **Choirboy** brings the King: one is never in play without the
    other. If the Demon's own kill takes the King, the Choirboy learns the
    Demon's player — a Recluse may register as it, a Vortox makes it
    false. A drunk or poisoned King is still the King; a dead Choirboy
    learns nothing, a drunk one anything. It wakes only on that night.
  * A **Princess** that nominated on her first day as the Princess, and
    had the nominee executed — dead of it or not — stops the Demon
    killing that night, if she has her ability then. The Demon still
    chooses; a Pukka's old poison kills nobody and comes off.
  * A **Golem** nominates once a game. A nominee who is not the Demon
    dies: one who lived registered as the Demon, could not die, or the
    Golem was not working — and a drunk Golem's nomination is spent too.
  * A **Psychopath** may kill in the open before nominations, and walks
    away from its execution if it wins roshambo. Only a Psychopath with
    its ability is offered roshambo, so whoever plays it is one.
  * A **Widow** poisons anybody on its first night, itself included, for
    as long as it lives and is not impaired itself, and one good player
    is told a Widow is in play. A Widow in play, ever, poisons the Damsel
    (their jinx). The Chambermaid counts it on its first night.

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
from botc.worlds import World, seated_legally     # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))

FIFTH = ("Choirboy", "Princess", "Golem", "Psychopath", "Widow")

# Trouble Brewing's shape, with the King the Choirboy brings and the
# Damsel the Widow poisons.
LIKE_TB = ["washerwoman", "librarian", "chef", "empath", "fortuneteller",
           "undertaker", "monk", "ravenkeeper", "king", "choirboy",
           "princess", "soldier", "mayor",
           "golem", "saint", "recluse", "drunk", "damsel",
           "psychopath", "widow", "poisoner", "scarletwoman",
           "imp"]
# Bad Moon Rising's, with a Chambermaid to count the Widow and a Pukka
# the Princess has to stop.
LIKE_BMR = ["grandmother", "sailor", "chambermaid", "exorcist", "innkeeper",
            "gambler", "gossip", "courtier", "professor", "king",
            "choirboy", "princess", "tealady",
            "golem", "goon", "lunatic", "tinker",
            "psychopath", "widow", "assassin", "devilsadvocate",
            "po", "pukka", "shabaloth", "zombuul"]

FIVE = scripts.from_ids("Fifth five, like Trouble Brewing", LIKE_TB)
FIVE_BMR = scripts.from_ids("Fifth five, like Bad Moon Rising", LIKE_BMR)


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
        teams = {key: CHARACTERS[key].team for key in FIFTH}
        self.assertEqual(teams, {"Choirboy": "townsfolk",
                                 "Princess": "townsfolk",
                                 "Golem": "outsider",
                                 "Psychopath": "minion",
                                 "Widow": "minion"})
        for key in FIFTH:
            self.assertTrue(CHARACTERS[key].modelled)

    def test_who_wakes(self):
        for key in ("Princess", "Golem", "Psychopath"):
            self.assertEqual(CHARACTERS[key].nights, "never")
        self.assertEqual(CHARACTERS["Choirboy"].nights, "conditional")
        self.assertEqual(CHARACTERS["Widow"].nights, "conditional")
        self.assertTrue(CHARACTERS["Widow"].chooses)
        self.assertIn("Choirboy", waking.CONDITION_RULES)
        self.assertIn("Widow", waking.CONDITION_RULES)

    def test_the_choirboy_brings_the_king(self):
        self.assertEqual(CHARACTERS["Choirboy"].brings, ("King",))
        roles = ["Chef", "Empath", "Mayor", "Choirboy", "Washerwoman",
                 "ScarletWoman", "Imp"]
        self.assertFalse(seated_legally(tuple(roles)))
        self.assertTrue(seated_legally(tuple(with_(roles, 2, "King"))))

    def test_the_named_games_do_not_draw_them(self):
        import play_games
        for seed in range(200):
            script = play_games.an_awkward_script(random.Random(seed),
                                                  as_named=True)
            with self.subTest(seed=seed):
                self.assertFalse(set(FIFTH) & set(script.keys))

    def test_a_mixed_script_with_a_choirboy_has_a_king(self):
        import play_games
        drawn = 0
        for seed in range(400):
            script = play_games.an_awkward_script(random.Random(seed))
            if "Choirboy" in script.keys:
                drawn += 1
                self.assertIn("King", script.keys)
        self.assertGreater(drawn, 10)


#           0       1         2       3           4
CHOIR = ["Chef", "Empath", "King", "Choirboy", "Washerwoman",
         "ScarletWoman", "Imp"]                             # 5, 6


class TheChoirboy(SolverTest):

    def test_shown_the_demon_when_the_king_fell(self):
        row = I.ChoirboyInfo(2, 3, target=6)
        self.assertEqual(cost(FIVE, CHOIR, [row], deaths={2: ("N2",)}), 1.0)

    def test_shown_anybody_else_it_was_not_working(self):
        row = I.ChoirboyInfo(2, 3, target=0)
        self.assertIsNone(cost(FIVE, CHOIR, [row], deaths={2: ("N2",)}))
        self.assertIsNotNone(cost(FIVE, with_(CHOIR, 5, "Poisoner"), [row],
                                  deaths={2: ("N2",)}))

    def test_a_recluse_may_register_as_the_demon(self):
        roles = with_(CHOIR, 1, "Recluse")
        row = I.ChoirboyInfo(2, 3, target=1)
        self.assertEqual(cost(FIVE, roles, [row], deaths={2: ("N2",)}), 1.0)

    def test_no_king_dead_no_answer(self):
        row = I.ChoirboyInfo(2, 3, target=6)
        self.assertIsNone(cost(FIVE, CHOIR, [row], deaths={0: ("N2",)}))

    def test_it_wakes_only_when_a_king_fell(self):
        world, state = board(FIVE, CHOIR, deaths={2: ("N2",)})
        self.assertEqual(waking.possible_counts(world, state, (3, 0), 2),
                         {0, 1})
        world, state = board(FIVE, CHOIR, deaths={0: ("N2",)})
        self.assertEqual(waking.possible_counts(world, state, (3, 0), 2),
                         {0})


#            0       1         2           3             4
PRINCE = ["Chef", "Empath", "Princess", "Undertaker", "Washerwoman",
          "ScarletWoman", "Imp"]                            # 5, 6


class ThePrincess(SolverTest):

    def nominated(self, day=1, target=0):
        return I.PrincessNominated(day, 2, target=target)

    def test_her_nominee_executed_and_nobody_dies(self):
        self.assertEqual(cost(FIVE, PRINCE, [self.nominated()],
                              deaths={0: ("E1",)}, quiet_nights={2},
                              days_done={1}), 1.0)

    def test_a_body_that_night_needs_her_impaired(self):
        dead = {0: ("E1",), 1: ("N2",)}
        self.assertIsNone(cost(FIVE, PRINCE, [self.nominated()],
                               deaths=dead, days_done={1}))
        self.assertIsNotNone(cost(FIVE, with_(PRINCE, 5, "Poisoner"),
                                  [self.nominated()], deaths=dead,
                                  days_done={1}))
        self.assertEqual(cost(FIVE, PRINCE, [], deaths=dead,
                              days_done={1}), 1.0)

    def test_executed_is_enough(self):
        self.assertIsNone(cost(FIVE, PRINCE, [self.nominated()],
                               executions={1: 0}, deaths={1: ("N2",)},
                               days_done={1}))

    def test_not_executed_stops_nothing(self):
        self.assertEqual(cost(FIVE, PRINCE, [self.nominated()],
                              deaths={1: ("N2",)}, days_done={1}), 1.0)

    def test_only_her_first_day(self):
        self.assertEqual(cost(FIVE, PRINCE, [self.nominated(day=2)],
                              deaths={4: ("N2",), 0: ("E2",),
                                      1: ("N3",)},
                              days_done={1, 2}), 1.0)

    def test_a_pukkas_old_poison_kills_nobody(self):
        roles = ["Chambermaid", "Gambler", "Princess", "Sailor",
                 "Professor", "DevilsAdvocate", "Pukka"]
        row = self.nominated(target=4)
        dead = {4: ("E1",), 0: ("N2",)}
        # Only if she was poisoned — by the Pukka itself, which costs.
        self.assertEqual(cost(FIVE_BMR, roles, [], deaths=dead,
                              days_done={1}), 1.0)
        self.assertLess(cost(FIVE_BMR, roles, [row], deaths=dead,
                             days_done={1}), 1.0)
        # And a quiet night beside her costs nothing.
        self.assertEqual(cost(FIVE_BMR, roles, [row], deaths={4: ("E1",)},
                              quiet_nights={2}, days_done={1}), 1.0)


#          0       1         2        3             4
GOLEM = ["Chef", "Empath", "Golem", "Undertaker", "Washerwoman",
         "ScarletWoman", "Imp"]                             # 5, 6


class TheGolem(SolverTest):

    def nominated(self, target, died, day=1):
        return I.GolemNomination(day, 2, target=target, died=died)

    def test_a_nominee_that_died(self):
        row = self.nominated(0, True)
        self.assertEqual(cost(FIVE, GOLEM, [row], deaths={0: ("D1",)}), 1.0)
        # Said by somebody who is no Golem, the body is not explained.
        self.assertIsNone(cost(FIVE, with_(GOLEM, 2, "Mayor"), [row],
                               deaths={0: ("D1",)}))

    def test_the_demon_does_not_die_of_it(self):
        self.assertIsNone(cost(FIVE, GOLEM, [self.nominated(6, True)],
                               deaths={6: ("D1",)}))
        self.assertEqual(cost(FIVE, GOLEM, [self.nominated(6, False)]), 1.0)

    def test_a_nominee_that_lived_needs_a_reason(self):
        row = self.nominated(0, False)
        self.assertIsNone(cost(FIVE, GOLEM, [row]))
        self.assertIsNotNone(cost(FIVE, with_(GOLEM, 5, "Poisoner"), [row]))
        self.assertEqual(cost(FIVE, with_(GOLEM, 0, "Recluse"), [row]), 1.0)

    def test_once_a_game_spent_or_not(self):
        first = self.nominated(6, False)
        self.assertEqual(cost(FIVE, GOLEM, [first, self.nominated(
            0, False, day=2)]), 1.0)
        self.assertIsNone(cost(FIVE, GOLEM, [first, self.nominated(
            0, True, day=2)], deaths={0: ("D2",)}))


#         0       1         2        3             4
PSYCHO = ["Chef", "Empath", "Mayor", "Undertaker", "Washerwoman",
          "Psychopath", "Imp"]                              # 5, 6


class ThePsychopath(SolverTest):

    def test_a_kill_in_the_open(self):
        row = I.PsychopathKill(1, 5, target=0, died=True)
        self.assertEqual(cost(FIVE, PSYCHO, [row], deaths={0: ("D1",)}), 1.0)
        row = I.PsychopathKill(1, 4, target=0, died=True)
        self.assertIsNone(cost(FIVE, PSYCHO, [row], deaths={0: ("D1",)}))

    def test_a_target_that_lived(self):
        row = I.PsychopathKill(1, 5, target=0, died=False)
        self.assertIsNone(cost(FIVE, PSYCHO, [row]))
        roles = ["Chambermaid", "Sailor", "Gambler", "Gossip", "Professor",
                 "Psychopath", "Po"]
        row = I.PsychopathKill(1, 5, target=1, died=False)
        self.assertEqual(cost(FIVE_BMR, roles, [row]), 1.0)

    def test_roshambo_is_only_ever_a_psychopath(self):
        self.assertEqual(cost(FIVE, PSYCHO, [I.PsychopathRoshambo(1, 5)],
                              executions={1: 5}), 1.0)
        self.assertEqual(cost(FIVE, PSYCHO, [I.PsychopathRoshambo(1, 5)],
                              deaths={5: ("E1",)}), 1.0)
        self.assertIsNone(cost(FIVE, PSYCHO, [I.PsychopathRoshambo(1, 4)],
                               executions={1: 4}))

    def test_it_walks_away_from_the_gallows(self):
        self.assertEqual(cost(FIVE, PSYCHO, executions={1: 5}), 1.0)
        world, state = board(FIVE, PSYCHO, executions={1: 5})
        self.assertEqual(S.survivals_of(world, state, 1, 5), [5])


#           0       1         2        3             4
WIDOWED = ["Chef", "Empath", "Mayor", "Undertaker", "Washerwoman",
           "Widow", "Imp"]                                  # 5, 6


class TheWidow(SolverTest):

    def test_a_good_player_was_told(self):
        self.assertEqual(cost(FIVE, WIDOWED, [I.WidowKnown(1, 0)]), 1.0)
        # Without a Widow on its first night the words were made up.
        self.assertLess(cost(FIVE, PSYCHO, [I.WidowKnown(1, 0)]), 1.0)
        self.assertLess(cost(FIVE, WIDOWED, [I.WidowKnown(2, 0)]), 1.0)

    def test_it_poisons_anybody_for_free(self):
        wrong = [I.Empath(1, 1, count=2)]
        self.assertEqual(cost(FIVE, WIDOWED, wrong), 1.0)
        self.assertIsNone(cost(FIVE, with_(WIDOWED, 5, "ScarletWoman"),
                               wrong))

    def test_it_poisons_the_damsel(self):
        roles = with_(WIDOWED, 2, "Damsel")
        guess = [I.DamselGuess(1, 5, target=2)]
        self.assertEqual(cost(FIVE, roles, guess, days_done={1}), 1.0)
        self.assertIsNone(cost(FIVE, with_(roles, 5, "ScarletWoman"),
                               guess, days_done={1}))

    def test_the_chambermaid_counts_it_on_its_first_night(self):
        world, state = board(FIVE, WIDOWED)
        self.assertEqual(waking.possible_counts(world, state, (5, 2), 1),
                         {1})
        self.assertEqual(waking.possible_counts(world, state, (5, 2), 2),
                         {0})

    def test_a_pukka_poisoning_it_after_its_turn_does_not_undo_it(self):
        """The Widow acts at 18 and the Pukka at 28: poisoned that night,
        and dead of it the next, it had still told somebody."""
        roles = ["Chambermaid", "Gambler", "Gossip", "Professor",
                 "Sailor", "Widow", "Pukka"]
        self.assertIsNotNone(cost(FIVE_BMR, roles, [I.WidowKnown(1, 0)],
                                  deaths={5: ("N2",)}))


class TheSimulatorPlaysThem(SolverTest):

    def played(self, script, games, nights=4):
        import claims as claim_model
        import simulate
        seen, lost = {}, []
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
            truth = World(tuple(deal.roles), tuple(deal.believes))
            if S.explanation_cost(truth, state) is None:
                lost.append(seed)
        return seen, lost

    def test_like_trouble_brewing(self):
        seen, lost = self.played(FIVE, 300)
        self.assertEqual(lost, [])
        for what in ("ChoirboyInfo", "PrincessNominated", "GolemNomination",
                     "PsychopathKill", "PsychopathRoshambo", "WidowKnown"):
            self.assertGreater(seen.get(what, 0), 5, what)

    def test_like_bad_moon_rising(self):
        seen, lost = self.played(FIVE_BMR, 300)
        self.assertEqual(lost, [])

    def games(self, script, how_many=300):
        import simulate
        for seed in range(how_many):
            n = [7, 8, 9, 10, 11][seed % 5]
            yield seed, simulate.play(n, random.Random(seed), nights=4,
                                      script=script)

    def test_a_choirboy_is_never_dealt_without_a_king(self):
        dealt = 0
        for script in (FIVE, FIVE_BMR):
            for seed, (deal, _heard) in self.games(script):
                if "Choirboy" in deal.roles:
                    dealt += 1
                    with self.subTest(script=script.name, seed=seed):
                        self.assertIn("King", deal.roles)
        self.assertGreater(dealt, 50)

    def test_the_princess_stops_every_demon_kill(self):
        import simulate
        stopped = 0
        for script in (FIVE, FIVE_BMR):
            for seed, (deal, _heard) in self.games(script):
                for night in deal.princess_stop:
                    if deal.nights_played < night:
                        continue
                    if not simulate._the_princess_stops(deal, night):
                        continue
                    stopped += 1
                    with self.subTest(script=script.name, seed=seed):
                        self.assertEqual(deal.demon_killed.get(night, []),
                                         [])
        self.assertGreater(stopped, 20)

    def test_a_golem_nominates_once(self):
        for script in (FIVE, FIVE_BMR):
            for seed, (deal, heard) in self.games(script):
                rows = [r for r in heard if isinstance(r, I.GolemNomination)]
                with self.subTest(script=script.name, seed=seed):
                    self.assertEqual(len(rows), len({r.player for r in rows}))

    def test_roshambo_only_for_a_working_psychopath(self):
        played = 0
        for seed, (deal, heard) in self.games(FIVE):
            for row in heard:
                if isinstance(row, I.PsychopathRoshambo):
                    played += 1
                    self.assertEqual(
                        deal.role_at(row.player, f"D{row.night}"),
                        "Psychopath")
                    self.assertTrue(deal.working(row.player, row.night,
                                                 by_day=True))
        self.assertGreater(played, 10)

    def test_one_good_player_is_told_once(self):
        for seed, (deal, heard) in self.games(FIVE):
            rows = [r for r in heard if isinstance(r, I.WidowKnown)]
            with self.subTest(seed=seed):
                self.assertLessEqual(len(rows), 1)
                for row in rows:
                    self.assertEqual(deal.side_at(row.player, "N1"), "good")

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
    """The Widow poisons at its slot, and a Princess's day silences the
    Demon — the Pukka's old poison included."""

    def test_the_deaths_come_out_the_same(self):
        import nightwalk
        import simulate
        nights = stopped = 0
        for script in (FIVE, FIVE_BMR):
            for seed in range(150):
                n = [7, 8, 9, 10, 11][seed % 5]
                deal, heard = simulate.play(n, random.Random(seed), nights=4,
                                            script=script)
                for night in range(2, deal.nights_played + 1):
                    hidden = nightwalk.hidden_from(deal, night, heard)
                    got = nightwalk.walk(deal, night, hidden)
                    nights += 1
                    stopped += ("princess", night) in hidden
                    with self.subTest(script=script.name, seed=seed,
                                      night=night):
                        self.assertEqual(got.died,
                                         deal.died_on(f"N{night}"))
                        self.assertEqual(got.untold, set())
        self.assertGreater(nights, 500)
        self.assertGreater(stopped, 10)


if __name__ == "__main__":
    unittest.main()
