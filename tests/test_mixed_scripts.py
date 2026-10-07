"""Mixed scripts: characters that have never shared one.

The three published scripts are three selections, and each character on
them has only ever met its own neighbours. `tools/play_games.py` draws
scripts that force the others to meet (`an_awkward_script`), and
`messung/tor.py` plays them by the thousand. On 05.10.2026 that sweep
lost the true world in 96 of 3,000 games; this file holds what was wrong
(07.10.2026), one class per test, and the sweep itself as the last one.

Three kinds of mistake, and they are worth telling apart:

  * **The simulator read the deal** where it meant the board as it
    stands tonight — a Washerwoman shown the character a seat held
    before a Snake Charmer swapped it away, a Drunk still drunk after a
    Fang Gu had jumped into it.
  * **The solver took a night for one moment.** A Gambler guesses tenth
    and an Exorcist names twenty-first; what moves a character comes
    later, and the question has to be asked of the board as it was.
  * **A rule knew one holder of an ability** where a Philosopher makes
    two.

What is still lost is listed in `STILL_LOST` with the reason, and the
reasons are in ROADMAP.md under the open items.
"""

import json
import pathlib
import random
import sys
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import impairment, info as I, scripts, waking  # noqa: E402
from botc.info import GameState                   # noqa: E402
from botc.worlds import World                     # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
import claims as claim_model                      # noqa: E402
import nightwalk                                  # noqa: E402
import play_games                                 # noqa: E402
import simulate                                   # noqa: E402

FIVE = ("Steward", "Knight", "Shugenja", "Nightwatchman", "King")
SIZES = [7, 8, 9, 10, 11]


def game(seed, nights=4, must_have=()):
    """One mixed game, as `messung/tor.py` plays it."""
    rng = random.Random(seed)
    script = play_games.an_awkward_script(rng, must_have=must_have)
    n = SIZES[seed % 5]
    deal, heard = simulate.play(n, rng, nights=nights, script=script)
    claims, wakes, _ = claim_model.claims_for(deal, rng, script=script)
    state = GameState(n_players=n, script=script, claims=claims, wakes=wakes,
                      infos=list(heard), votes=dict(deal.votes),
                      nominations=dict(deal.nominations), **deal.record())
    world = World(tuple(deal.roles), tuple(deal.believes))
    return deal, heard, state, world


def kept(seed, **kw):
    deal, heard, state, world = game(seed, **kw)
    return S.explanation_cost(world, state) is not None


def cost(script, roles, infos=(), believes=None, **kw):
    n = len(roles)
    believes = tuple(believes or [None] * n)
    claims = {i: believes[i] or role for i, role in enumerate(roles)}
    state = GameState(n_players=n, script=script, claims=claims,
                      infos=list(infos), **kw)
    return S.explanation_cost(World(tuple(roles), believes), state)


# --------------------------------------------------------------------------
# The simulator
# --------------------------------------------------------------------------

class TheSimulatorReadsTheBoardAsItStandsTonight(SolverTest):

    def test_a_falsified_undertaker_still_speaks_of_whoever_was_executed(self):
        """The false version was rebuilt from night, player and
        character, and `target` fell back to seat 0 — in Trouble Brewing
        too, where a poisoned Undertaker is told something false."""
        deal, _heard, _state, _world = game(3)
        rng = random.Random(1)
        for seat in range(1, deal.n):
            real = deal.role_at(seat, "E1")
            row = I.Undertaker(2, 0, target=seat, role=real)
            made = simulate._make_false(deal, row, 2, rng)
            with self.subTest(seat=seat):
                self.assertEqual(made.target, seat)
                self.assertNotEqual(made.role, real)

    def test_a_ravenkeeper_can_be_told_something_false(self):
        """It had no case at all, so a Vortox left it the truth."""
        deal, _heard, _state, _world = game(3)
        rng = random.Random(1)
        for seat in range(1, deal.n):
            real = deal.role_at(seat, "N2")
            row = I.Ravenkeeper(2, 0, target=seat, role=real)
            made = simulate._make_false(deal, row, 2, rng)
            with self.subTest(seat=seat):
                self.assertEqual(made.target, seat)
                self.assertNotEqual(made.role, real)

    def test_at_most_one_setup_changer_is_dealt(self):
        """A Baron chosen, the Demon was drawn from all of them — and a
        Fang Gu beside it sat in a bag counted for the Baron alone."""
        changers = {"Baron", "Godfather", "FangGu", "Vigormortis"}
        both = 0
        for seed in range(400):
            rng = random.Random(seed)
            script = play_games.an_awkward_script(rng)
            roles, _believes = simulate.deal(SIZES[seed % 5], rng, script)
            both += len(changers & set(script.keys)) > 1
            with self.subTest(seed=seed):
                self.assertLessEqual(len(changers & set(roles)), 1)
        self.assertGreater(both, 50, "no script here could have shown it")

    def test_a_wrong_token_ends_when_the_character_changes(self):
        """A Drunk a Fang Gu jumped into is the Fang Gu and kills."""
        for seed in range(200):
            deal, _heard, _state, _world = game(seed, nights=1)
            seat = next((p for p in range(deal.n) if deal.believes[p]), None)
            if seat is not None:
                break
        self.assertIsNotNone(seat)
        self.assertEqual(deal.token(seat, "N1"), deal.believes[seat])
        self.assertIn(seat, simulate.droisoned_at(deal, 1))
        deal.changes.append(("N2", seat, "FangGu"))
        self.assertEqual(deal.token(seat, "N1"), deal.believes[seat])
        self.assertIsNone(deal.token(seat, "N2"))

    def test_once_a_game_characters_woke_on_the_night_they_acted(self):
        """The comment said so and the code answered no for all of them."""
        deal, _heard, _state, _world = game(3)
        woke = simulate._conditionally_woke
        self.assertTrue(woke(deal, 0, "Seamstress", 1))
        self.assertFalse(woke(deal, 0, "Seamstress", 2))
        self.assertTrue(woke(deal, 0, "Juggler", 2))
        self.assertFalse(woke(deal, 0, "Juggler", 1))
        self.assertFalse(woke(deal, 0, "Artist", 1))

    def test_poison_goes_with_the_poisoner(self):
        """Made something else later the same night, its poison is gone."""
        tb = scripts.TROUBLE_BREWING
        for seed in range(300):
            deal, _heard = simulate.play(7, random.Random(seed), nights=1,
                                         script=tb)
            victim, by = deal.poisoned.get(1), deal.poisoned_by.get(1)
            if victim is not None and deal.believes[victim] is None \
                    and victim != by:
                break
        self.assertEqual(deal.roles[by], "Poisoner")
        self.assertIn(victim, simulate.droisoned_at(deal, 1))
        deal.changes.append(("N1", by, "Mayor"))
        self.assertNotIn(victim, simulate.droisoned_at(deal, 1))


# --------------------------------------------------------------------------
# The solver
# --------------------------------------------------------------------------

AWAKE = scripts.from_ids("Mixed, for waking", [
    "chambermaid", "philosopher", "clockmaker", "empath", "monk", "soldier",
    "saint", "lunatic", "mutant", "scarletwoman", "witch", "imp"])
#        0              1              2        3         4
BOARD = ["Chambermaid", "Philosopher", "Saint", "Empath", "Soldier",
         "ScarletWoman", "Imp"]                               # 5, 6


class APhilosopherWakesToChoose(SolverTest):

    def state(self, took):
        return GameState(n_players=7, script=AWAKE,
                         claims=dict(enumerate(BOARD)),
                         infos=[I.PhilosopherChoice(1, 1, role=took)])

    def test_on_the_night_it_chooses_whatever_it_took(self):
        """`<` where `<=` was meant: on the night it chose it was asked
        whether the *taken* character wakes, and a Saint does not."""
        world = World(tuple(BOARD), (None,) * 7)
        self.assertTrue(waking.woke(world, self.state("Saint"), 1, 1))
        self.assertFalse(waking.woke(world, self.state("Saint"), 1, 2))
        self.assertTrue(waking.woke(world, self.state("Empath"), 1, 2))

    def test_a_chambermaid_counts_it(self):
        row = lambda count: I.ChambermaidInfo(1, 0, a=1, b=2, count=count)
        took = I.PhilosopherChoice(1, 1, role="Saint")
        self.assertIsNotNone(cost(AWAKE, BOARD, [took, row(1)]))
        self.assertIsNone(cost(AWAKE, BOARD, [took, row(0)]))

    def test_one_that_took_the_lunatic_wakes_for_nothing_and_ends(self):
        """The Lunatic's rule asked whose night this seat was living,
        heard "a Philosopher's", and the two rules called each other
        until the stack ran out."""
        world = World(tuple(BOARD), (None,) * 7)
        self.assertFalse(waking.woke(world, self.state("Lunatic"), 1, 2))
        self.assertFalse(waking.woke(world, self.state("Philosopher"), 1, 2))


SEERS = scripts.from_ids("Mixed, a Fortune Teller under a Vortox", [
    "fortuneteller", "chambermaid", "clockmaker", "dreamer", "flowergirl",
    "oracle", "towncrier", "juggler", "sage", "mutant", "klutz",
    "witch", "eviltwin", "cerenovus", "vortox"])
#          0                1             2          3
SEEING = ["FortuneTeller", "Clockmaker", "Dreamer", "Flowergirl", "Oracle",
          "Witch", "Vortox"]                                  # 4, 5, 6


class AFortuneTellerUnderAVortox(SolverTest):
    """Nothing on this script can droison a Vortox, so a reading that
    came out true has no excuse at all."""

    def ft(self, a, b, yes):
        return I.FortuneTeller(1, 0, a=a, b=b, yes=yes)

    def test_a_no_on_two_good_players_is_the_herring_among_them(self):
        """Chosen with the herring in the pair the true answer is yes,
        and a Vortox makes it no. Read without a herring it looked true."""
        self.assertIsNotNone(cost(SEERS, SEEING, [self.ft(1, 2, False)]))

    def test_a_yes_on_two_good_players_is_false_and_fine(self):
        self.assertIsNotNone(cost(SEERS, SEEING, [self.ft(1, 2, True)]))

    def test_a_no_on_the_vortox_is_false_and_fine(self):
        self.assertIsNotNone(cost(SEERS, SEEING, [self.ft(6, 2, False)]))

    def test_a_yes_on_the_vortox_is_true_and_cannot_be(self):
        self.assertIsNone(cost(SEERS, SEEING, [self.ft(6, 2, True)]))

    def test_a_number_inside_a_range_may_still_be_the_wrong_one(self):
        """A Demon's first night may count or not, so a Chambermaid's
        answer about it is a range of two — and a Vortox needs only that
        the number *could* be wrong."""
        roles = ["Chambermaid"] + SEEING[1:]
        world = World(tuple(roles), (None,) * 7)
        state = GameState(n_players=7, script=SEERS,
                          claims=dict(enumerate(roles)))
        open_pair = I.ChambermaidInfo(1, 0, a=6, b=1, count=1)
        self.assertEqual(waking.possible_counts(world, state, (6, 1), 1),
                         {1, 2})
        self.assertTrue(open_pair.holds(world, state, None))
        self.assertFalse(open_pair.is_true(world, state))
        shut = I.ChambermaidInfo(1, 0, a=1, b=2, count=2)
        self.assertTrue(shut.is_true(world, state))
        self.assertIsNotNone(cost(SEERS, roles, [open_pair]))
        self.assertIsNone(cost(SEERS, roles, [shut]))


class ANightIsNotOneMoment(SolverTest):
    """Each of these is a game the sweep found, kept by name: the script
    is drawn from the seed, so the seed is the whole board."""

    def test_a_gambler_is_judged_as_it_guessed(self):
        """Tenth in the night, a moment before the Snake Charmer at
        eleven swapped with the Demon it had just named rightly."""
        deal, heard, state, world = game(1250)
        guess = next(r for r in heard if isinstance(r, I.GamblerGuess)
                     and r.night > 1
                     and deal.role_at(r.target, f"D{r.night - 1}") == r.role
                     and deal.role_at(r.target, f"N{r.night}") != r.role)
        self.assertNotEqual(deal.deaths.get(guess.player), f"N{guess.night}")
        self.assertIsNotNone(S.explanation_cost(world, state))

    def test_a_gambler_dead_of_its_guess_may_be_remade_the_same_night(self):
        """By a Pit-Hag at sixteen. The night then ends with no Gambler
        on the board, and the death still has to be its own."""
        deal, heard, state, world = game(140)
        guess = next(r for r in heard if isinstance(r, I.GamblerGuess)
                     and deal.deaths.get(r.player) == f"N{r.night}")
        self.assertNotEqual(deal.role_at(guess.player, f"N{guess.night}"),
                            "Gambler")
        self.assertIsNotNone(S.explanation_cost(world, state))

    def test_an_exorcist_names_the_demon_as_its_turn_came(self):
        """Twenty-first, before any Demon acts: the Outsider a Fang Gu
        was about to jump into is not the Demon it sent to bed."""
        deal, heard, state, world = game(1725)
        named = next(r for r in heard if isinstance(r, I.ExorcistChoice)
                     and (f"N{r.night}", r.target, "FangGu") in deal.changes)
        self.assertTrue(deal.died_on(f"N{named.night}"))
        self.assertIsNotNone(S.explanation_cost(world, state))


class TwoMayHoldOneAbility(SolverTest):

    def test_a_philosopher_with_the_gambler_dies_of_its_own_guess(self):
        """The rule looked at the seat holding the character, found the
        real Gambler — drunk and harmless — and stopped."""
        deal, heard, state, world = game(8725)
        seat = next(p for p, took in deal.philosophies.items()
                    if took == "Gambler")
        wrong = next(r for r in heard if isinstance(r, I.GamblerGuess)
                     and r.player == seat
                     and deal.deaths.get(seat) == f"N{r.night}")
        self.assertNotEqual(deal.role_at(wrong.target, f"D{wrong.night - 1}"),
                            wrong.role)
        self.assertIsNotNone(S.explanation_cost(world, state))
        # And the walk plays it: the Philosopher guesses, and falls.
        hidden = nightwalk.hidden_from(deal, wrong.night, heard)
        walked = nightwalk.walk(deal, wrong.night, hidden)
        self.assertEqual(walked.died, deal.died_on(f"N{wrong.night}"))


class AWrongTokenEndsWithTheCharacter(SolverTest):

    def test_a_drunk_the_fang_gu_jumped_into_kills(self):
        deal, _heard, state, world = game(3375)
        when, seat = next((at, who) for at, who, role in deal.changes
                          if role == "FangGu" and deal.believes[who])
        night = int(when[1:])
        self.assertTrue(any(deal.died_on(f"N{k}")
                            for k in range(night + 1, 5)))
        self.assertIsNotNone(S.explanation_cost(world, state))

    def test_the_source_stops_reaching_the_seat(self):
        roles = ["Clockmaker", "Drunk", "Dreamer", "Oracle", "Flowergirl",
                 "Witch", "FangGu"]
        believes = (None, "Sage", None, None, None, None, None)
        world = World(tuple(roles), believes)
        state = GameState(n_players=7, script=SEERS,
                          claims=dict(enumerate(roles)))
        jumped = S.Timeline(world, (S.Change("N2", 1, "FangGu", "evil"),))

        def believers(view, night):
            return set().union(*[s.seats for s in
                                 impairment.always_impaired(view, state,
                                                            night)] or [()])

        self.assertEqual(believers(world, 3), {1})
        self.assertEqual(believers(jumped, 1), {1})
        self.assertEqual(believers(jumped, 2), set())
        self.assertEqual(believers(jumped, 3), set())


# --------------------------------------------------------------------------
# The sweep
# --------------------------------------------------------------------------

# What six hundred games still lose, and why. A seed leaving this list is
# good news and the list should shrink; a seed joining it is a regression.
STILL_LOST = {
    (): {
        21: "a Barber's swap nobody announced, under a Vortox",
        55: "a Barber's swap and a Snake Charmer's on one board",
        146: "a Barber's swap nobody announced",
    },
    FIVE: {
        34: "a Vortox and a Seamstress shown somebody who misregisters",
        205: "an Innkeeper guarding a Fang Gu that jumps",
        461: "a Drunk Snake Charmer, a Philosopher's and a jump",
    },
}


class SixHundredMixedGames(SolverTest):

    def sweep(self, must_have):
        lost = []
        for seed in range(600):
            deal, heard, state, world = game(seed, must_have=must_have)
            if S.explanation_cost(world, state) is None:
                lost.append(seed)
        return lost

    def test_the_true_world_is_kept(self):
        for must_have, known in STILL_LOST.items():
            with self.subTest(must_have=must_have):
                lost = self.sweep(must_have)
                self.assertEqual([s for s in lost if s not in known], [])


class TheBoardsInTheCorpus(SolverTest):
    """One of each class, held in both languages by the conformance
    tests. Here only: they are boards the page accepts and can solve."""

    def test_every_mixed_board_was_solved(self):
        corpus = json.loads((HERE / "fixtures" / "conformance.json")
                            .read_text())
        mixed = [c for c in corpus["cases"]
                 if c["name"].startswith("mixed-")]
        self.assertGreaterEqual(len(mixed), 9)
        for case in mixed:
            with self.subTest(board=case["name"]):
                self.assertNotIn("error", case["expect"])
                self.assertGreater(case["expect"]["valid"], 0)


if __name__ == "__main__":
    unittest.main()
