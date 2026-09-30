"""Sects & Violets, character by character.

The script where information stops being merely unreliable and starts
being wrong. Built a few characters at a time; what is not here yet says
so in the catalogue rather than pretending.

Lineups are chosen rather than convenient, and say why. One trap on this
script in particular: it has four Outsiders and the usual bag wants two,
so a board where two seats claim Outsiders **pins** them — there is
nowhere else for the Outsiders to be, and nothing about those seats can
vary. A reading aimed at one of them proves nothing.
"""

import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                           # noqa: E402
from botc import scripts                          # noqa: E402
from botc.info import ClockmakerInfo, DreamerInfo, GameState  # noqa: E402
from botc.worlds import World                     # noqa: E402

SV = scripts.SECTS_AND_VIOLETS

# Seven Townsfolk claims and two Outsider claims. The Outsider claimants
# are pinned by the bag, so anything being tested aims at a Townsfolk
# claimant, where a Minion or the Demon could be hiding.
CLAIMS = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
          "Flowergirl", "TownCrier", "Oracle", "Mutant", "Sweetheart"]


def board(**kw):
    return GameState(n_players=9, script=SV,
                     claims={i: r for i, r in enumerate(CLAIMS)}, **kw)


def among(*roles):
    assert len(roles) == 9 and len(set(roles)) == 9, roles
    return World(tuple(roles), (None,) * 9)


class TheClockmaker(SolverTest):
    """How many steps from the Demon to its nearest Minion.

    Around the circle, the shorter way, and the nearest when there is
    more than one. First night only, so the dead never come into it.
    """

    def spread(self, demon_at, minion_at):
        roles = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
                 "Flowergirl", "TownCrier", "Oracle", "Sage", "Juggler"]
        roles[demon_at] = "Vortox"
        roles[minion_at] = "Witch"
        world = World(tuple(roles), (None,) * 9)
        return next(n for n in range(9)
                    if ClockmakerInfo(1, 0, count=n).holds(world, board(),
                                                           None))

    def test_a_minion_beside_the_demon_is_one_step(self):
        self.assertEqual(self.spread(0, 1), 1)

    def test_it_counts_the_shorter_way_round(self):
        """Seat 9 is next door to seat 1, going backwards."""
        self.assertEqual(self.spread(0, 8), 1)
        self.assertEqual(self.spread(8, 0), 1)

    def test_four_along_is_four_either_way(self):
        self.assertEqual(self.spread(0, 4), 4)
        self.assertEqual(self.spread(0, 5), 4)

    def test_it_takes_the_nearest_of_several(self):
        world = among("Vortox", "Dreamer", "SnakeCharmer", "Witch",
                      "Flowergirl", "TownCrier", "Oracle", "Cerenovus",
                      "Juggler")
        self.assertTrue(ClockmakerInfo(1, 0, count=2).holds(world, board(),
                                                            None))
        self.assertFalse(ClockmakerInfo(1, 0, count=3).holds(world, board(),
                                                             None))

    def test_zero_steps_is_no_world_at_all(self):
        """It would mean the Demon is its own nearest Minion."""
        world = among("Vortox", "Dreamer", "SnakeCharmer", "Mathematician",
                      "Flowergirl", "TownCrier", "Oracle", "Witch",
                      "Juggler")
        self.assertFalse(ClockmakerInfo(1, 0, count=0).holds(world, board(),
                                                             None))

    def test_it_narrows_the_board(self):
        with_it = S.solve(board(infos=[ClockmakerInfo(1, 0, count=1)]))[1]
        without = S.solve(board())[1]
        self.assertGreater(len(without), len(with_it))
        self.assertGreater(len(with_it), 0)


class TheDreamer(SolverTest):
    """One good character and one evil one, and the target is one of them.

    Two constraints rather than one: the pair has to be one of each side,
    *and* the seat asked about has to be one of the two.
    """

    def reading(self, good="Oracle", evil="Witch", target=2):
        return DreamerInfo(1, 1, target=target, good_role=good,
                           evil_role=evil)

    def world(self, at_three="SnakeCharmer"):
        roles = ["Clockmaker", "Dreamer", at_three, "Mathematician",
                 "Flowergirl", "TownCrier", "Oracle", "Sage", "Vortox"]
        if at_three != "SnakeCharmer":
            roles[7] = "SnakeCharmer"
        return World(tuple(roles), (None,) * 9)

    def test_it_holds_when_the_target_is_the_evil_one(self):
        self.assertTrue(self.reading(good="Sage", evil="Witch")
                        .holds(self.world("Witch"), board(), None))

    def test_and_when_the_target_is_the_good_one(self):
        self.assertTrue(self.reading(good="SnakeCharmer", evil="Witch")
                        .holds(self.world(), board(), None))

    def test_but_not_when_the_target_is_neither(self):
        self.assertFalse(self.reading(good="Oracle", evil="Witch")
                         .holds(self.world(), board(), None))

    def test_two_characters_of_one_side_is_not_a_dreamer_reading(self):
        """The pair is always one of each. A row saying otherwise was
        mis-entered, and no world should be built around it."""
        for good, evil in (("Oracle", "Sage"), ("Witch", "Cerenovus")):
            with self.subTest(pair=(good, evil)):
                self.assertFalse(
                    DreamerInfo(1, 1, target=2, good_role=good,
                                evil_role=evil)
                    .holds(self.world(), board(), None))

    def test_naming_a_seats_own_claim_clears_it(self):
        """Less completely than it used to, and the Vortox is why.

        Under one, a Townsfolk reading has to come out *false* — so a
        Dreamer naming a seat's own claim is evidence the seat is not
        that, in the fifth or so of worlds where a Vortox is about. The
        reading still clears the seat; it no longer nearly settles it.
        """
        plain = S.summarize(*self._solved(board()))
        rows = S.summarize(*self._solved(board(infos=[
            self.reading(good="SnakeCharmer", evil="Witch")])))
        was = dict(plain[2]["roles"]).get("SnakeCharmer", 0)
        now = dict(rows[2]["roles"]).get("SnakeCharmer", 0)
        self.assertGreater(now, was)
        self.assertGreater(now, 60.0)

    def test_naming_something_else_raises_suspicion(self):
        plain = S.summarize(*self._solved(board()))
        named = S.summarize(*self._solved(board(infos=[
            self.reading(good="Oracle", evil="Witch")])))
        self.assertGreater(named[2]["evil_pct"], plain[2]["evil_pct"])

    def test_together_with_the_clockmaker_it_bites(self):
        plain = S.summarize(*self._solved(board()))
        rows = S.summarize(*self._solved(board(infos=[
            self.reading(good="Oracle", evil="Witch"),
            ClockmakerInfo(1, 0, count=1)])))
        # Each reading pushes, and together they push further than
        # either alone — which is what "it bites" means on a script where
        # a No Dashii can excuse a reading for nothing.
        one = S.summarize(*self._solved(board(infos=[
            self.reading(good="Oracle", evil="Witch")])))
        self.assertGreater(one[2]["evil_pct"], plain[2]["evil_pct"])
        self.assertGreater(rows[2]["evil_pct"], one[2]["evil_pct"])

    def _solved(self, state):
        return S.solve(state)[1], state


class TheOutsiderTrap(SolverTest):
    """Worth a test of its own, because it cost an hour once.

    Sects & Violets has four Outsiders and a nine-player bag wants two.
    Two Outsider claims fill it exactly, which pins those seats — nothing
    about them can vary, and a reading aimed at one proves nothing.
    """

    def test_two_outsider_claims_pin_those_seats(self):
        """All but one. Since the Mutant was modelled it can stand behind
        any Townsfolk claim, so the seat that says "Mutant" may be evil
        bluffing it while the real one hides. The Sweetheart has nobody
        to hide behind and stays pinned."""
        valid = S.solve(board())[1]
        self.assertTrue(valid)
        self.assertEqual({w.roles[8] for w in valid}, {"Sweetheart"})
        seven = {w.roles[7] for w in valid}
        self.assertIn("Mutant", seven)
        for role in seven - {"Mutant"}:
            with self.subTest(role=role):
                self.assertTrue(S.is_evil(role))
        for w in valid:
            if w.roles[7] != "Mutant":
                self.assertIn("Mutant", w.roles[:7])

    def test_while_a_townsfolk_claimant_can_be_anything(self):
        valid = S.solve(board())[1]
        self.assertGreater(len({w.roles[2] for w in valid}), 3)


if __name__ == "__main__":
    unittest.main()


class TheMathematician(SolverTest):
    """How many abilities went wrong tonight.

    A reading about the solver's own workings rather than about the
    table, and the only one of its kind. It counts the impaired, so what
    it can honestly say depends on what the script can break.
    """

    def full_script(self):
        """Trouble Brewing plus a Mathematician: something that droisons
        (a Poisoner, a Drunk) and nothing left unmodelled."""
        return scripts.from_ids(
            "Trouble Brewing and a Mathematician",
            [k.lower() for k in scripts.TROUBLE_BREWING.keys]
            + ["mathematician"])

    SEATS = ["Washerwoman", "Librarian", "Investigator", "Mathematician",
             "Empath", "FortuneTeller", "Undertaker", "Recluse", "Saint"]

    def solved(self, count):
        from botc.info import MathematicianInfo
        script = self.full_script()
        state = GameState(n_players=9, script=script,
                          claims={i: r for i, r in enumerate(self.SEATS)},
                          infos=[MathematicianInfo(2, 3, count=count)])
        return S.solve(state)[1]

    def test_the_range_is_what_could_have_gone_wrong(self):
        from botc.info import _possible_impairment_counts
        script = self.full_script()
        state = GameState(n_players=9, script=script,
                          claims={i: r for i, r in enumerate(self.SEATS)})
        nothing = World(("Washerwoman", "Librarian", "Investigator",
                         "Mathematician", "Empath", "FortuneTeller",
                         "Undertaker", "Baron", "Imp"), (None,) * 9)
        poisoner = World(("Washerwoman", "Librarian", "Investigator",
                          "Mathematician", "Empath", "FortuneTeller",
                          "Undertaker", "Poisoner", "Imp"), (None,) * 9)
        drunk = World(("Washerwoman", "Librarian", "Investigator",
                       "Mathematician", "Drunk", "FortuneTeller",
                       "Undertaker", "Poisoner", "Imp"),
                      (None,) * 4 + ("Empath",) + (None,) * 4)
        self.assertEqual(_possible_impairment_counts(nothing, state, 2),
                         (0, 0), "nothing here can go wrong")
        self.assertEqual(_possible_impairment_counts(poisoner, state, 2),
                         (0, 1), "the Poisoner has to land somewhere")
        self.assertEqual(_possible_impairment_counts(drunk, state, 2),
                         (1, 2), "the Drunk always, the Poisoner maybe "
                                 "on top")

    def test_a_number_it_could_not_have_reached_means_it_was_droisoned(self):
        """Not that the board is impossible — the Mathematician being
        wrong is itself something that goes wrong."""
        self.assertTrue(self.solved(4))

    def test_saying_nothing_went_wrong_argues_against_a_drunk(self):
        """Whoever holds somebody else's token is impaired every night,
        so zero sits badly with one being in play.

        It argues rather than proves, and the reason is worth keeping:
        a genuine Mathematician saying an impossible number is itself
        something going wrong, so those worlds survive with the
        Mathematician droisoned — at a price. Weight moves; nothing is
        ruled out.
        """
        from botc.info import MathematicianInfo
        script = self.full_script()

        def drunk_share(count):
            state = GameState(
                n_players=9, script=script,
                claims={i: r for i, r in enumerate(self.SEATS)},
                infos=[MathematicianInfo(2, 3, count=count)])
            valid = S.solve(state)[1]
            weights = [S.world_weight(w, state) for w in valid]
            total = sum(weights) or 1.0
            return sum(x for w, x in zip(valid, weights)
                       if "Drunk" in w.roles) / total

        self.assertLess(drunk_share(0), drunk_share(1),
                        "zero should argue against a Drunk being about")

    def test_it_bites_now_that_the_script_is_finished(self):
        """It used to say nothing here, and said so deliberately: Sects &
        Violets droisons four different ways and none of them was built,
        so the solver would have concluded nothing could go wrong and
        thrown away every world where something did.

        All four are built now, so the guard lets go — which is the
        moment this test was written to notice.
        """
        from botc.info import MathematicianInfo
        self.assertEqual(
            [c.name for c in SV.characters()
             if c.impairs and not c.modelled], [],
            "something that droisons is still unbuilt")
        counts = {count: len(S.solve(
            board(infos=[MathematicianInfo(2, 3, count=count)]))[1])
            for count in (0, 1, 2)}
        self.assertGreater(len(set(counts.values())), 1,
                           "the number it heard should matter now")

    def test_but_it_does_bite_once_everything_is_accounted_for(self):
        self.assertNotEqual(len(self.solved(0)), len(self.solved(1)))


class TheFlowergirlAndTheTownCrier(SolverTest):
    """The two that ask about the day rather than the night.

    Both needed something the board did not record — who voted, and who
    nominated — so those are ticked per seat and gathered per day, and
    shown in the ledger beside the execution. A day is where the answer
    lives: "did the Demon vote today" is a question about a day.

    Both are asked on the night *after*, so a reading on night three is
    about day two.
    """

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(CLAIMS)}, **kw)

    def world(self):
        """Demon at seat 9, Minion at seat 8."""
        return among("Clockmaker", "Dreamer", "SnakeCharmer",
                     "Mathematician", "Flowergirl", "TownCrier", "Oracle",
                     "Witch", "Vortox")

    def test_the_flowergirl_reads_the_day_before(self):
        from botc.info import FlowergirlInfo
        yes = FlowergirlInfo(3, 4, voted=True)
        self.assertTrue(yes.holds(self.world(),
                                  self.board(votes={2: {8}}), None))
        self.assertFalse(yes.holds(self.world(),
                                   self.board(votes={2: {0, 1}}), None))

    def test_and_a_no_is_the_other_way_round(self):
        from botc.info import FlowergirlInfo
        no = FlowergirlInfo(3, 4, voted=False)
        self.assertTrue(no.holds(self.world(),
                                 self.board(votes={2: {0, 1}}), None))
        self.assertFalse(no.holds(self.world(),
                                  self.board(votes={2: {8}}), None))

    def test_there_is_no_day_before_the_first_night(self):
        from botc.info import FlowergirlInfo, TownCrierInfo
        self.assertFalse(FlowergirlInfo(1, 4, voted=False)
                         .holds(self.world(), self.board(), None))
        self.assertFalse(TownCrierInfo(1, 5, nominated=False)
                         .holds(self.world(), self.board(), None))

    def test_the_town_crier_hears_a_minion(self):
        from botc.info import TownCrierInfo
        yes = TownCrierInfo(3, 5, nominated=True)
        self.assertTrue(yes.holds(self.world(),
                                  self.board(nominations={2: {7}}), None))
        self.assertFalse(yes.holds(self.world(),
                                   self.board(nominations={2: {0, 1}}),
                                   None))

    def test_a_no_is_the_harder_claim(self):
        """A "yes" needs one nominator who *could* have shown as a
        Minion. A "no" needs every one of them to have been able to show
        as something else — which an ordinary Minion cannot."""
        from botc.info import TownCrierInfo
        no = TownCrierInfo(3, 5, nominated=False)
        self.assertFalse(no.holds(self.world(),
                                  self.board(nominations={2: {7}}), None))
        self.assertTrue(no.holds(self.world(),
                                 self.board(nominations={2: {0, 1}}), None))

    def test_a_spy_can_nominate_unheard(self):
        """It is a Minion that registers as good, so the Town Crier hears
        nothing — and that is the whole reason a "no" is checked against
        what a seat *must* be rather than what it is."""
        from botc.info import TownCrierInfo
        script = scripts.from_ids("Sects & Violets and a Spy",
                                  [k.lower() for k in SV.keys] + ["spy"])
        state = GameState(n_players=9, script=script,
                          claims={i: r for i, r in enumerate(CLAIMS)},
                          nominations={2: {7}})
        world = among("Clockmaker", "Dreamer", "SnakeCharmer",
                      "Mathematician", "Flowergirl", "TownCrier", "Oracle",
                      "Spy", "Vortox")
        self.assertTrue(TownCrierInfo(3, 5, nominated=False)
                        .holds(world, state, None))
        self.assertTrue(TownCrierInfo(3, 5, nominated=True)
                        .holds(world, state, None),
                        "the Storyteller could have shown it either way")

    def test_the_flowergirl_moves_suspicion_onto_the_voters(self):
        from botc.info import FlowergirlInfo
        voters = {2: {0, 1, 2}}
        yes = self.board(votes=voters, days_done={2},
                         infos=[FlowergirlInfo(3, 4, voted=True)])
        no = self.board(votes=voters, days_done={2},
                        infos=[FlowergirlInfo(3, 4, voted=False)])
        said_yes = S.summarize(S.solve(yes)[1], yes)
        said_no = S.summarize(S.solve(no)[1], no)
        for seat in (0, 1, 2):
            with self.subTest(voter=seat + 1):
                self.assertGreater(said_yes[seat]["evil_pct"],
                                   said_no[seat]["evil_pct"])
        for seat in (3, 5, 6):
            with self.subTest(abstained=seat + 1):
                self.assertLess(said_yes[seat]["evil_pct"],
                                said_no[seat]["evil_pct"])

    def test_the_town_crier_points_at_the_nominator(self):
        from botc.info import TownCrierInfo
        state = self.board(nominations={2: {2}}, days_done={2},
                           infos=[TownCrierInfo(3, 5, nominated=True)])
        rows = S.summarize(S.solve(state)[1], state)
        for seat in (0, 1, 3, 6):
            with self.subTest(other=seat + 1):
                self.assertLess(rows[seat]["evil_pct"],
                                rows[2]["evil_pct"])


class TheSecondBatch(SolverTest):
    """Oracle, Seamstress, Juggler — and the two that are kept, not solved.

    The lineup here claims Outsiders at seats 8 and 9 so the bag is
    filled without pinning anything being tested; the rest are Townsfolk
    claims, where a Minion or the Demon could be hiding.
    """

    CLAIMS = ["Clockmaker", "Dreamer", "Oracle", "Seamstress", "Juggler",
              "Savant", "Artist", "Mutant", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def world(self, at_two="Oracle"):
        roles = ["Clockmaker", "Dreamer", at_two, "Seamstress", "Juggler",
                 "Savant", "Artist", "Mutant", "Sweetheart"]
        if at_two != "Oracle":
            roles[6] = "Oracle"
        return World(tuple(roles), (None,) * 9)

    # --- Oracle ---------------------------------------------------------

    def test_the_oracle_counts_the_dead(self):
        from botc.info import OracleInfo
        world = among("Clockmaker", "Dreamer", "Oracle", "Seamstress",
                      "Juggler", "Savant", "Artist", "Witch", "Vortox")
        state = self.board(deaths={7: "N2", 0: "N3"})   # a Witch and a good
        self.assertTrue(OracleInfo(3, 2, count=1).holds(world, state, None))
        self.assertFalse(OracleInfo(3, 2, count=0).holds(world, state, None))
        self.assertFalse(OracleInfo(3, 2, count=2).holds(world, state, None))

    def test_nobody_dead_means_none_of_them_are_evil(self):
        from botc.info import OracleInfo
        world = among("Clockmaker", "Dreamer", "Oracle", "Seamstress",
                      "Juggler", "Savant", "Artist", "Witch", "Vortox")
        self.assertTrue(OracleInfo(2, 2, count=0).holds(world, self.board(),
                                                        None))
        self.assertFalse(OracleInfo(2, 2, count=1).holds(world, self.board(),
                                                         None))


    # A note that applies to several of the tests below.
    #
    # Sects & Violets got its Demons, and two of them poison for *free*:
    # a No Dashii always drunks its two nearest Townsfolk, and a
    # Vigormortis drunks beside every Minion it killed. Neither is a
    # choice and neither is lucky, so excusing a reading from one of
    # those seats costs nothing at all.
    #
    # That makes a single reading on this script much weaker than the
    # same reading on Trouble Brewing, where a Poisoner has to have got
    # lucky. It is not a regression — it is the script — so these check
    # the direction a reading pushes rather than demanding certainty.

    def test_it_pushes_suspicion_onto_the_dead_seat(self):
        from botc.info import OracleInfo
        plain = self.board(deaths={2: "N2"}, days_done={2})
        named = self.board(deaths={2: "N2"}, days_done={2},
                           infos=[OracleInfo(3, 2, count=1)])
        was = S.summarize(S.solve(plain)[1], plain)
        now = S.summarize(S.solve(named)[1], named)
        self.assertGreater(now[2]["evil_pct"], was[2]["evil_pct"])

    # --- Seamstress -----------------------------------------------------

    def test_the_seamstress_splits_the_table(self):
        from botc.info import SeamstressInfo
        world = among("Clockmaker", "Dreamer", "Oracle", "Seamstress",
                      "Juggler", "Savant", "Artist", "Witch", "Vortox")
        state = self.board()
        self.assertTrue(SeamstressInfo(2, 3, a=7, b=8, same=True)
                        .holds(world, state, None))
        self.assertFalse(SeamstressInfo(2, 3, a=7, b=8, same=False)
                         .holds(world, state, None))
        self.assertTrue(SeamstressInfo(2, 3, a=0, b=7, same=False)
                        .holds(world, state, None))

    def test_the_two_answers_pull_opposite_ways(self):
        from botc.info import SeamstressInfo
        same = self.board(infos=[SeamstressInfo(2, 3, a=0, b=1, same=True)])
        apart = self.board(infos=[SeamstressInfo(2, 3, a=0, b=1,
                                                 same=False)])
        said_same = S.summarize(S.solve(same)[1], same)
        said_apart = S.summarize(S.solve(apart)[1], apart)
        for seat in (0, 1):
            with self.subTest(seat=seat + 1):
                self.assertLess(said_same[seat]["evil_pct"],
                                said_apart[seat]["evil_pct"])

    # --- Juggler --------------------------------------------------------

    def test_the_juggler_counts_what_it_got_right(self):
        from botc.info import JugglerInfo
        world = among("Clockmaker", "Dreamer", "Oracle", "Seamstress",
                      "Juggler", "Savant", "Artist", "Witch", "Vortox")
        state = self.board()
        guesses = ((0, "Clockmaker"), (7, "Witch"), (1, "Oracle"))
        self.assertTrue(JugglerInfo(3, 4, guesses=guesses, count=2)
                        .holds(world, state, None))
        for wrong in (0, 1, 3):
            with self.subTest(count=wrong):
                self.assertFalse(
                    JugglerInfo(3, 4, guesses=guesses, count=wrong)
                    .holds(world, state, None))

    def test_getting_them_right_clears_those_seats(self):
        from botc.info import JugglerInfo
        state = self.board(days_done={2}, infos=[
            JugglerInfo(3, 4, guesses=((0, "Clockmaker"), (1, "Dreamer")),
                        count=2)])
        rows = S.summarize(S.solve(state)[1], state)
        for seat in (0, 1):
            with self.subTest(seat=seat + 1):
                self.assertLess(rows[seat]["evil_pct"], 15.0)

    # --- Savant and Artist ----------------------------------------------

    def test_the_savant_and_artist_are_kept_not_weighed(self):
        """Their content can be anything at all, and checking arbitrary
        claims about a board is a different program. Recording one is
        still somebody claiming to have visited the Storyteller, so it
        argues for that character existing — and nothing more."""
        from botc.info import ArtistInfo, SavantInfo
        world = self.world()
        state = self.board()
        for row in (SavantInfo(2, 5, first="anything", second="at all"),
                    ArtistInfo(2, 6, question="anything", answer=True)):
            with self.subTest(row=type(row).__name__):
                self.assertTrue(row.holds(world, state, None))

    def test_but_they_still_argue_for_their_own_claimant(self):
        from botc.info import SavantInfo
        plain = self.board()
        claimed = self.board(infos=[SavantInfo(2, 5, first="a", second="b")])
        was = S.summarize(S.solve(plain)[1], plain)
        now = S.summarize(S.solve(claimed)[1], claimed)
        self.assertLess(now[5]["evil_pct"], was[5]["evil_pct"])

    def test_they_say_in_the_script_panel_that_they_are_not_solved(self):
        from botc.catalogue import CHARACTERS
        # The Savant left this test when its statements got shapes the
        # board answers (see TheSavantIsWeighedWhenItCanBe).
        self.assertFalse(CHARACTERS["Artist"].modelled)
        self.assertIn("not weighed", CHARACTERS["Artist"].note)
        self.assertTrue(CHARACTERS["Savant"].modelled)


class WhatSilencesTheMathematician(SolverTest):
    """Only an unmodelled character that can *droison* should.

    The guard was written as "any unmodelled character at all", which was
    fine while everything unmodelled was temporary. The Savant and the
    Artist are permanent — their content will never be checked — so that
    guard would have silenced the Mathematician on Sects & Violets for
    good.
    """

    def test_the_flag_names_the_ones_that_matter(self):
        from botc.catalogue import CHARACTERS, IMPAIRS
        self.assertEqual(sorted(IMPAIRS - set(CHARACTERS)), [],
                         "the list names a character that does not exist")
        for key in ("Poisoner", "Drunk", "Sailor", "Courtier", "NoDashii",
                    "Philosopher", "PitHag"):
            with self.subTest(character=key):
                self.assertTrue(CHARACTERS[key].impairs)

    def test_and_not_the_ones_that_only_talk(self):
        from botc.catalogue import CHARACTERS
        for key in ("Savant", "Artist", "Oracle", "Juggler", "Clockmaker"):
            with self.subTest(character=key):
                self.assertFalse(CHARACTERS[key].impairs)

    def test_a_script_whose_only_gaps_are_talkers_is_not_silenced(self):
        from botc.catalogue import CHARACTERS
        # An Artist now; it was a Savant until the Savant was weighed.
        talkers = scripts.from_ids(
            "Trouble Brewing, a Mathematician and an Artist",
            [k.lower() for k in scripts.TROUBLE_BREWING.keys]
            + ["mathematician", "artist"])
        self.assertFalse(all(c.modelled for c in talkers.characters()))
        self.assertTrue(all(c.modelled for c in talkers.characters()
                            if c.impairs))


class TheThirdBatch(SolverTest):
    """Sage, Sweetheart, Barber, Klutz — and the Mutant, which is not
    modelled and says so."""

    CLAIMS = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
              "Klutz", "Barber", "Mutant", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def evil_at_nine(self):
        return among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                     "Klutz", "Recluse", "Witch", "Vortox")

    # --- Sage -----------------------------------------------------------

    def test_the_sage_is_shown_the_demon_that_killed_it(self):
        from botc.info import SageInfo
        world, state = self.evil_at_nine(), self.board(deaths={3: "N2"})
        self.assertTrue(SageInfo(2, 3, a=8, b=0).holds(world, state, None))
        self.assertFalse(SageInfo(2, 3, a=1, b=0).holds(world, state, None))

    def test_and_not_something_registering_as_one(self):
        """Unlike almost every other reading. It is shown the Demon that
        killed it, so a Recluse being shown as the Demon cannot fill the
        pair — and neither can a Minion."""
        from botc.info import SageInfo
        world, state = self.evil_at_nine(), self.board(deaths={3: "N2"})
        self.assertFalse(SageInfo(2, 3, a=6, b=0).holds(world, state, None),
                         "the Recluse is not the killer")
        self.assertFalse(SageInfo(2, 3, a=7, b=0).holds(world, state, None),
                         "nor is the Witch")

    def test_it_narrows_hard(self):
        """Onto the pair it named — though a Vortox blunts it, since
        under one the reading has to be false and the Demon is neither of
        the two."""
        from botc.info import SageInfo
        plain = self.board(deaths={3: "N2"})
        named = self.board(deaths={3: "N2"},
                           infos=[SageInfo(2, 3, a=0, b=8)])
        was = S.summarize(S.solve(plain)[1], plain)
        now = S.summarize(S.solve(named)[1], named)
        self.assertGreater(now[8]["evil_pct"] + now[0]["evil_pct"],
                           was[8]["evil_pct"] + was[0]["evil_pct"])
        self.assertGreater(now[8]["evil_pct"] + now[0]["evil_pct"], 60.0)

    # --- Klutz ----------------------------------------------------------

    def test_the_klutz_clears_who_it_pointed_at(self):
        from botc.info import KlutzChoice
        state = self.board(deaths={5: "N2"},
                           infos=[KlutzChoice(2, 5, target=0)])
        rows = S.summarize(S.solve(state)[1], state)
        self.assertLess(rows[0]["evil_pct"], 3.0)

    def test_but_a_droisoned_klutz_could_have_pointed_anywhere(self):
        """Good losing on the spot is the *working* ability. Pointing at
        somebody evil does not make the board impossible — it makes the
        Klutz wrong, which is a thing that happens."""
        from botc.info import KlutzChoice
        world = self.evil_at_nine()
        state = self.board(deaths={5: "N2"},
                           infos=[KlutzChoice(2, 5, target=8)])
        self.assertFalse(KlutzChoice(2, 5, target=8).holds(world, state,
                                                           None))
        self.assertTrue(S.solve(state)[1], "still explicable")

    # --- Sweetheart -----------------------------------------------------

    def test_the_sweetheart_starts_impairing_when_it_dies(self):
        from botc import impairment
        world = among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Sweetheart")
        alive = self.board()
        dead = self.board(deaths={8: "N2"})
        names = lambda st, night: [s.name for s in
                                   impairment.sources_on(world, st, night)]
        self.assertNotIn("Sweetheart", names(alive, 3))
        self.assertIn("Sweetheart", names(dead, 2))

    def test_and_never_stops(self):
        """Unlike a Poisoner. Whoever it landed on is impaired for the
        rest of the game, so every reading they give afterwards is
        arbitrary."""
        from botc import impairment
        world = among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Sweetheart")
        dead = self.board(deaths={8: "N2"})
        for night in (2, 3, 4, 8):
            with self.subTest(night=night):
                self.assertIn("Sweetheart",
                              [s.name for s in
                               impairment.sources_on(world, dead, night)])

    # --- Barber ---------------------------------------------------------

    def test_the_barber_offers_a_swap_only_after_it_dies(self):
        world = among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox")
        alive = S.possible_timelines(world, self.board())
        self.assertEqual(len(alive), 1)
        dead = S.possible_timelines(
            world, self.board(deaths={6: "D2", 0: "N3"}, days_done={3}))
        self.assertGreater(len(dead), 30, "every pair, plus doing nothing")

    def test_doing_nothing_comes_first(self):
        """It is a "may", and mostly it is not."""
        world = among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox")
        stories = S.possible_timelines(
            world, self.board(deaths={6: "D2", 0: "N3"}, days_done={3}))
        self.assertEqual(stories[0], ((), 1.0))

    def test_a_swap_keeps_each_side(self):
        """Characters only. A good player can end up holding a Minion's
        character, which is rare and legal."""
        world = among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox")
        state = self.board(deaths={6: "D2", 0: "N3"}, days_done={3})
        for changes, _cost in S.possible_timelines(world, state):
            for one in changes:
                with self.subTest(change=one):
                    # The swap writes each seat's side down (so a swapped
                    # Demon is not read as good), and it is the side the
                    # seat already had.
                    had = "evil" if world.evil_at(one.seat, one.phase) else "good"
                    self.assertIn(one.side, (None, had), "the side must not move")

    def test_the_lineage_walk_cannot_go_round_for_ever(self):
        """With two seats trading characters the star could be handed
        back to somebody who had already had it, and the walk recursed
        until the stack ran out. It solves now."""
        state = self.board(deaths={6: "D2", 0: "N3"}, days_done={3})
        self.assertTrue(S.solve(state)[1])

    # --- Mutant ---------------------------------------------------------

    def test_the_mutant_is_modelled_now(self):
        from botc.catalogue import CHARACTERS
        self.assertTrue(CHARACTERS["Mutant"].modelled)
        self.assertTrue(CHARACTERS["Mutant"].hides)


class TheMutantHides(SolverTest):
    """A Mutant cannot say it is an Outsider — it might be executed for
    it — so it always claims a Townsfolk.

    For every other good player a false claim is a choice and costs the
    world something. For this one it is the rules talking, and before
    the Mutant was modelled a world with one in it was never even built
    unless somebody claimed to be the Mutant: the one thing it never
    does.
    """

    CLAIMS = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
              "Klutz", "Barber", "Seamstress", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def test_any_townsfolk_claim_can_be_the_mutant(self):
        from botc.worlds import _candidates
        got = _candidates("Oracle", False, script=SV)
        self.assertIn(("Mutant", None), got)

    def test_but_not_an_outsider_claim(self):
        """Claiming another Outsider is being mad about being one."""
        from botc.worlds import _candidates
        self.assertNotIn(("Mutant", None),
                         _candidates("Sweetheart", False, script=SV))

    def test_nor_off_its_own_script(self):
        from botc.worlds import _candidates
        self.assertNotIn("Mutant", [r for r, _b in
                                    _candidates("Chef", False,
                                                script=scripts.TROUBLE_BREWING)])

    def test_what_it_says_about_waking_does_not_rule_it_out(self):
        """It says whatever suits the cover, like a bluffer."""
        from botc.worlds import _candidates
        got = _candidates("Oracle", False, wake="every", script=SV)
        self.assertIn(("Mutant", None), got)

    def test_its_cover_story_costs_nothing(self):
        state = self.board()
        honest = World(("Clockmaker", "Dreamer", "Oracle", "Sage",
                        "Juggler", "Klutz", "Barber", "Witch", "Vortox"),
                       (None,) * 9)
        hiding = World(("Clockmaker", "Dreamer", "Mutant", "Sage",
                        "Juggler", "Klutz", "Barber", "Witch", "Vortox"),
                       (None,) * 9)
        self.assertEqual(S.prior_weight(hiding, state),
                         S.prior_weight(honest, state))

    def test_a_board_holds_worlds_with_the_mutant_in_them(self):
        valid = S.solve(self.board())[1]
        self.assertTrue(any("Mutant" in w.roles for w in valid))

    def test_a_confirmed_mutant_is_still_one(self):
        """Executed for saying it: the table enters the seat as a
        confirmed Mutant, and that is a world like any other."""
        claims = dict(enumerate(self.CLAIMS))
        claims[6] = "Mutant"
        state = GameState(n_players=9, script=SV, claims=claims,
                          certainties={6: "confirmed"},
                          deaths={6: "D1"}, executions={1: 6})
        valid = S.solve(state)[1]
        self.assertTrue(valid)
        self.assertTrue(all(w.roles[6] == "Mutant" for w in valid))


class TheSavantIsWeighedWhenItCanBe(SolverTest):
    """Two statements, one true and one false.

    Words alone stay words. When both are entered in a shape the board can
    answer, the pair is weighed: exactly one held — both false under a
    Vortox, anything at all for a droisoned Savant.
    """

    W = World(("Clockmaker", "Dreamer", "Oracle", "Savant", "Juggler",
               "Klutz", "Barber", "Witch", "Vortox"),
              (None,) * 9)

    def row(self, one, two, night=1):
        from botc.info import SavantInfo
        return SavantInfo(night, 3, first_says=one, second_says=two)

    def state(self):
        return GameState(n_players=9, script=SV, claims={})

    def test_words_alone_are_not_weighed(self):
        from botc.info import SavantInfo
        self.assertFalse(SavantInfo(1, 3, first="a", second="b")
                         .weighed(self.state()))

    def test_one_shape_and_one_line_of_words_is_not_either(self):
        row = self.row({"kind": "evil", "seat": 7}, None)
        self.assertFalse(row.weighed(self.state()))

    def test_exactly_one_true_holds(self):
        row = self.row({"kind": "evil", "seat": 7},       # true
                       {"kind": "in_play", "role": "PitHag"})   # false
        self.assertTrue(row.holds(self.W, self.state(), None))

    def test_both_true_does_not(self):
        row = self.row({"kind": "evil", "seat": 7},
                       {"kind": "demon_among", "seats": [8, 0, 1]})
        self.assertFalse(row.holds(self.W, self.state(), None))

    def test_both_false_does_not_either(self):
        row = self.row({"kind": "good", "seat": 7},
                       {"kind": "outsiders", "count": 3})
        self.assertFalse(row.holds(self.W, self.state(), None))

    def test_every_shape_answers(self):
        from botc.info import SAVANT_KINDS, savant_truths
        shapes = {
            "evil": {"seat": 7}, "good": {"seat": 0},
            "same": {"a": 7, "b": 8}, "different": {"a": 0, "b": 8},
            "is": {"seat": 2, "role": "Oracle"},
            "in_play": {"role": "Barber"},
            "not_in_play": {"role": "Mutant"},
            "outsiders": {"count": 2},
            "demon_among": {"seats": [6, 7, 8]}}
        self.assertEqual(sorted(shapes), sorted(SAVANT_KINDS))
        for kind, args in shapes.items():
            with self.subTest(kind=kind):
                self.assertEqual(
                    savant_truths(dict(kind=kind, **args), self.W, "D1"),
                    {True})

    def test_a_recluse_can_read_either_way(self):
        from botc.info import savant_truths
        w = World(("Clockmaker", "Dreamer", "Oracle", "Savant", "Juggler",
                   "Recluse", "Barber", "Witch", "Vortox"), (None,) * 9)
        self.assertEqual(savant_truths({"kind": "evil", "seat": 5}, w, "D1"),
                         {True, False})
        self.assertEqual(
            savant_truths({"kind": "evil", "seat": 5}, w, "D1", real=True),
            {False})

    def test_under_a_vortox_both_were_false(self):
        """`is_true` is the Vortox's question: anything really true in
        it means the Vortox was not working."""
        s = self.state()
        both_false = self.row({"kind": "good", "seat": 7},
                              {"kind": "outsiders", "count": 3})
        one_true = self.row({"kind": "evil", "seat": 7},
                            {"kind": "outsiders", "count": 3})
        self.assertFalse(both_false.is_true(self.W, s))
        self.assertTrue(one_true.is_true(self.W, s))

    def test_a_vortox_board_takes_the_false_pair(self):
        claims = {0: "Clockmaker", 1: "Dreamer", 2: "Oracle", 3: "Savant",
                  4: "Juggler", 5: "Klutz", 6: "Barber"}
        row = self.row({"kind": "good", "seat": 7},
                       {"kind": "outsiders", "count": 3})
        state = GameState(n_players=9, script=SV, claims=claims, infos=[row])
        self.assertIsNotNone(S.explanation_cost(self.W, state))

    def test_it_narrows_the_board(self):
        """Told "seat 8 is evil" and "seat 1 is evil" on a board where
        the rest is quiet: one of the two, so each is about half."""
        claims = {i: r for i, r in enumerate(
            ["Clockmaker", "Dreamer", "Oracle", "Savant", "Juggler",
             "Klutz", "Barber", "Seamstress", "Sweetheart"])}
        plain = GameState(n_players=9, script=SV, claims=claims)
        told = GameState(n_players=9, script=SV, claims=claims, infos=[
            self.row({"kind": "evil", "seat": 7},
                     {"kind": "evil", "seat": 0})])
        before = S.summarize(S.solve(plain)[1], plain)
        after = S.summarize(S.solve(told)[1], told)
        self.assertGreater(after[7]["evil_pct"], before[7]["evil_pct"])
        self.assertGreater(after[0]["evil_pct"], before[0]["evil_pct"])


class WhatMadnessLeavesBehind(SolverTest):
    """The Cerenovus's madness leaves no mark of its own. Three things
    the table can see do: a seat executed for breaking ceremadness (the
    status), somebody saying they were made mad, and a good player
    claiming what they are not."""

    CLAIMS = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
              "Klutz", "Barber", "Seamstress", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def share(self, valid, role):
        return sum(1 for w in valid if role in w.roles) / max(len(valid), 1)

    def test_saying_so_makes_a_cerenovus_likelier(self):
        from botc.info import CerenovusMadness
        plain = self.board()
        told = self.board(infos=[CerenovusMadness(1, 2, role="Clockmaker")])
        def cerenovus(state):
            rows = S.analyze(state)
            return sum(dict(r["roles"]).get("Cerenovus", 0.0)
                       for r in rows["rows"])
        self.assertGreater(cerenovus(told), cerenovus(plain))

    def test_the_character_has_to_be_a_good_one(self):
        from botc.info import CerenovusMadness
        w = World(("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                   "Klutz", "Barber", "Cerenovus", "Vortox"), (None,) * 9)
        state = self.board()
        self.assertTrue(CerenovusMadness(1, 2, role="Oracle")
                        .holds(w, state, None, 7))
        self.assertFalse(CerenovusMadness(1, 2, role="Witch")
                         .holds(w, state, None, 7))

    def test_a_dead_cerenovus_maddens_nobody(self):
        from botc.info import CerenovusMadness
        w = World(("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                   "Klutz", "Barber", "Cerenovus", "Vortox"), (None,) * 9)
        state = self.board(deaths={7: "E1"}, executions={1: 7})
        self.assertTrue(CerenovusMadness(1, 2, role="Oracle")
                        .holds(w, state, None, 7))
        self.assertFalse(CerenovusMadness(2, 2, role="Oracle")
                         .holds(w, state, None, 7))

    def test_it_is_a_choice_so_a_vortox_leaves_it_alone(self):
        from botc.info import CerenovusMadness
        self.assertFalse(CerenovusMadness(1, 2, role="Oracle")
                         .is_information(self.board()))

    def test_with_a_cerenovus_a_good_lie_is_cheaper(self):
        """Seat 2 claims the Oracle and is really the Dreamer: madness in
        a world with a Cerenovus alive, chaos without one."""
        state = self.board(certainties={2: "unsure"}, days_done={1})
        mad = World(("Clockmaker", "Dreamer", "Dreamer", "Sage", "Juggler",
                     "Klutz", "Barber", "Cerenovus", "Vortox"), (None,) * 9)
        sane = World(("Clockmaker", "Dreamer", "Dreamer", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox"), (None,) * 9)
        self.assertAlmostEqual(
            S.prior_weight(mad, state) / S.prior_weight(sane, state),
            S.CERENOVUS_MADNESS_PENALTY / S.TOWNSFOLK_LIE_PENALTY)

    def test_one_madness_a_night(self):
        state = self.board(certainties={2: "unsure", 3: "unsure"})
        mad = World(("Clockmaker", "Dreamer", "Dreamer", "Juggler",
                     "Juggler", "Klutz", "Barber", "Cerenovus", "Vortox"),
                    (None,) * 9)
        self.assertEqual(S._madness_nights(mad, state), 1)
        self.assertAlmostEqual(
            S.prior_weight(mad, state),
            S.CERENOVUS_MADNESS_PENALTY * S.TOWNSFOLK_LIE_PENALTY)


class TheFourthBatch(SolverTest):
    """Evil Twin, Witch, Cerenovus, Philosopher.

    Two of these are got at from the other end. The Witch and the
    Cerenovus each make a hidden choice the board never records — but
    each leaves something the table sees plainly, and recording *that*
    says the character is in play. It is the only handle either offers.
    """

    CLAIMS = ["Philosopher", "Dreamer", "Oracle", "Sage", "Juggler",
              "Klutz", "Barber", "Mutant", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def share(self, valid, role):
        return sum(1 for w in valid if role in w.roles) / max(len(valid), 1)

    # --- Witch and Cerenovus -------------------------------------------

    def test_dying_while_nominating_means_a_witch(self):
        valid = S.solve(self.board(deaths={2: "D2"},
                                   witch_deaths={2: 2}))[1]
        self.assertTrue(valid)
        self.assertPct(self.share(valid, "Witch"), 1.0, 1e-9)

    def test_executed_for_madness_means_a_cerenovus(self):
        valid = S.solve(self.board(deaths={2: "D2"}, executions={2: 2},
                                   madness_executions={2: 2}))[1]
        self.assertTrue(valid)
        self.assertPct(self.share(valid, "Cerenovus"), 1.0, 1e-9)

    def test_at_nine_players_naming_one_fills_the_only_slot(self):
        """A fact about the *bag*, not about the characters. Nine players
        deals one Minion, so a Witch death leaves nowhere for anything
        else to be."""
        valid = S.solve(self.board(deaths={2: "D2"},
                                   witch_deaths={2: 2}))[1]
        self.assertPct(self.share(valid, "Cerenovus"), 0.0, 1e-9)

    def test_but_a_bigger_table_can_hold_both(self):
        """Twelve players deals two Minions, so a Witch death says
        nothing whatever about a Cerenovus — and both really can be in
        play at once. Written down because the opposite was claimed out
        loud once, from a nine-player board, as though it were a rule.
        """
        claims = self.CLAIMS + ["Seamstress", "Flowergirl", "TownCrier"]
        state = GameState(n_players=12, script=SV,
                          claims={i: r for i, r in enumerate(claims)},
                          deaths={2: "D2"}, witch_deaths={2: 2})
        valid = S.solve(state)[1]
        self.assertTrue(valid)
        self.assertPct(self.share(valid, "Witch"), 1.0, 1e-9)
        both = [w for w in valid
                if "Witch" in w.roles and "Cerenovus" in w.roles]
        self.assertGreater(len(both) / len(valid), 0.1,
                           "a witch death must not rule out a Cerenovus")

    def test_the_one_who_did_it_had_to_be_working(self):
        """Which is why it demands them rather than merely wanting them:
        a droisoned Witch curses nobody."""
        valid = S.solve(self.board(deaths={2: "D2"}, witch_deaths={2: 2}))[1]
        for world in valid:
            with self.subTest(world=world.roles):
                self.assertIn("Witch", world.roles)

    # --- Evil Twin ------------------------------------------------------

    def test_the_twins_are_one_of_each_side(self):
        from botc.info import EvilTwinPair
        world = among("Philosopher", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "EvilTwin", "Mutant", "Vortox")
        state = self.board()
        self.assertTrue(EvilTwinPair(1, 1, a=6, b=0).holds(world, state,
                                                           None))
        self.assertFalse(EvilTwinPair(1, 1, a=6, b=8).holds(world, state,
                                                            None),
                         "both evil is not a twin pair")
        self.assertFalse(EvilTwinPair(1, 1, a=0, b=1).holds(world, state,
                                                            None),
                         "neither is the Evil Twin")

    def test_naming_a_pair_moves_weight_onto_it(self):
        from botc.info import EvilTwinPair
        state = self.board(infos=[EvilTwinPair(1, 1, a=1, b=6)])
        rows = S.summarize(S.solve(state)[1], state)
        plain = S.summarize(*(lambda b: (S.solve(b)[1], b))(self.board()))
        self.assertGreater(rows[6]["evil_pct"], plain[6]["evil_pct"])

    # --- Philosopher ----------------------------------------------------

    def test_it_works_two_abilities_from_the_night_it_chose(self):
        from botc.roles import ABSENT, GENUINE, ability_state
        world = among("Philosopher", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox")
        self.assertEqual(ability_state(world, 0, "Philosopher", "N2"),
                         GENUINE)
        self.assertEqual(
            ability_state(world, 0, "Juggler", "N2", ("Juggler", "N3",
                                                      False)), ABSENT)
        self.assertEqual(
            ability_state(world, 0, "Juggler", "N3", ("Juggler", "N3",
                                                      True)), GENUINE)

    def test_a_gained_reading_belongs_to_the_philosopher(self):
        """Not to whoever claims that character. The relaying rule hands
        a row to the one seat claiming its source, which is right for
        somebody passing on information and wrong for a Philosopher
        speaking its own."""
        from botc.info import JugglerInfo, PhilosopherChoice
        state = self.board(infos=[PhilosopherChoice(3, 0, role="Juggler"),
                                  JugglerInfo(4, 0, guesses=((1, "Dreamer"),),
                                              count=1)])
        self.assertEqual(state.infos[1].source_seat(state), 0)

    def test_guesses_that_cannot_be_right_argue_against_the_claim(self):
        """Rather than making the board impossible. The cheaper story is
        that the seat is not the Philosopher at all."""
        from botc.info import JugglerInfo, PhilosopherChoice
        guesses = ((1, "Dreamer"), (2, "Oracle"))
        right = self.board(days_done={3}, infos=[
            PhilosopherChoice(3, 0, role="Juggler"),
            JugglerInfo(4, 0, guesses=guesses, count=2)])
        wrong = self.board(days_done={3}, infos=[
            PhilosopherChoice(3, 0, role="Juggler"),
            JugglerInfo(4, 0, guesses=guesses, count=0)])
        as_philosopher = lambda b: sum(
            1 for w in S.solve(b)[1] if w.roles[0] == "Philosopher")
        self.assertGreater(as_philosopher(right), as_philosopher(wrong))

    def test_it_drunks_whoever_already_had_it(self):
        from botc import impairment
        from botc.info import PhilosopherChoice
        world = among("Philosopher", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox")
        state = self.board(infos=[PhilosopherChoice(3, 0, role="Juggler")])
        names = lambda night: [s.name for s in
                               impairment.sources_on(world, state, night)]
        self.assertNotIn("Philosopher", names(2))
        self.assertIn("Philosopher", names(3))

    def test_but_only_while_it_lives(self):
        """Unlike a Sweetheart, this one switches off again."""
        from botc import impairment
        from botc.info import PhilosopherChoice
        world = among("Philosopher", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox")
        dead = self.board(deaths={0: "N4"},
                          infos=[PhilosopherChoice(3, 0, role="Juggler")])
        self.assertEqual(
            [s.name for s in impairment.sources_on(world, dead, 5)], [])

    def test_taking_a_character_nobody_holds_drunks_nobody(self):
        from botc import impairment
        from botc.info import PhilosopherChoice
        world = among("Philosopher", "Dreamer", "Oracle", "Sage", "Juggler",
                      "Klutz", "Barber", "Witch", "Vortox")
        state = self.board(infos=[PhilosopherChoice(3, 0,
                                                    role="TownCrier")])
        self.assertEqual(
            [s.name for s in impairment.sources_on(world, state, 3)], [])


class TheVortox(SolverTest):
    """Townsfolk abilities yield false information.

    Not a droisoning — it is the opposite kind of claim. A poisoned
    Empath may be told anything, including the truth by accident, so a
    poisoned reading constrains nothing. A Vortox'd Empath must be told
    something that is *not* so, which constrains the world in the other
    direction. That is why it needed a fourth ability state rather than a
    variation on poison.
    """

    CLAIMS = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz",
              "Barber", "Mutant", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def world(self):
        """A Vortox at seat 9 with the Witch beside it, so the true
        Clockmaker answer is 1."""
        return among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                     "Klutz", "Barber", "Witch", "Vortox")

    def test_it_touches_townsfolk_and_nobody_else(self):
        from botc.roles import GENUINE, INVERTED, ability_state
        world = self.world()
        self.assertEqual(
            ability_state(world, 0, "Clockmaker", "N2", None, True), INVERTED)
        for seat, role in ((5, "Klutz"), (7, "Witch"), (8, "Vortox")):
            with self.subTest(seat=seat + 1, role=role):
                self.assertEqual(
                    ability_state(world, seat, role, "N2", None, True),
                    GENUINE)

    def test_the_true_answer_is_the_one_that_cannot_be(self):
        from botc.info import ClockmakerInfo
        world = self.world()
        true_one = self.board(infos=[ClockmakerInfo(1, 0, count=1)])
        self.assertIsNone(S.explanation_cost(world, true_one))
        for wrong in (0, 2, 3):
            with self.subTest(count=wrong):
                state = self.board(infos=[ClockmakerInfo(1, 0, count=wrong)])
                self.assertPct(S.explanation_cost(world, state), 1.0, 1e-9)

    def test_it_does_not_protect_anybody_or_droison_anybody(self):
        """Its text is that abilities *yield false information*, not that
        they malfunction. A Monk still protects and a Soldier is still
        safe on a script that has them — and the Vortox itself adds no
        impairment source."""
        from botc import impairment
        world = self.world()
        self.assertEqual(
            [s.name for s in impairment.sources_on(world, self.board(), 2)],
            [])

    def test_a_day_with_no_execution_rules_a_working_vortox_out(self):
        """Evil wins on the spot, so play carrying on says there was not
        one."""
        world = self.world()
        self.assertPct(S.explanation_cost(world, self.board()), 1.0, 1e-9)
        self.assertIsNone(
            S.explanation_cost(world, self.board(days_done={2})))

    def test_but_a_day_that_had_one_says_nothing(self):
        world = self.world()
        state = self.board(days_done={2}, executions={2: 0},
                           deaths={0: "D2"})
        self.assertIsNotNone(S.explanation_cost(world, state))

    def test_it_is_asked_per_day_rather_than_per_game(self):
        """A Pit-Hag can bring one along later or replace one earlier, so
        a quiet day rules out a Vortox *that day* and no other."""
        import inspect
        source = inspect.getsource(S._plain_failures)
        self.assertIn("days_done", source)
        self.assertIn('f"D{day}"', source)

    def test_the_board_swings_both_ways(self):
        from botc.info import ClockmakerInfo
        plain = len(S.solve(self.board())[1])
        quiet = S.solve(self.board(days_done={2}))[1]
        self.assertLess(len(quiet), plain)
        self.assertEqual(sum(1 for w in quiet if "Vortox" in w.roles), 0)


class TheSnakeCharmer(SolverTest):
    """The only handover where the star moves sideways.

    Choosing the Demon while working swaps character *and* side both
    ways: the Snake Charmer becomes the Demon, and the Demon becomes a
    good Snake Charmer — poisoned from that moment for the rest of the
    game. The new Demon is untouched.

    Recorded rather than guessed, because the outcome is visible. A
    choice that did nothing is worth having too: it says that seat was
    not the Demon.
    """

    CLAIMS = ["Clockmaker", "SnakeCharmer", "Oracle", "Sage", "Juggler",
              "Klutz", "Barber", "Mutant", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def world(self):
        """Snake Charmer at seat 2, and the Demon at seat 9.

        Not a Vortox, deliberately: these boards mark a day as ended with
        nobody executed, which rules a working Vortox out on its own.
        The first draft used one and every world came back impossible for
        a reason that had nothing to do with the Snake Charmer.
        """
        return among("Clockmaker", "SnakeCharmer", "Oracle", "Sage",
                     "Juggler", "Klutz", "Barber", "Witch", "Vigormortis")

    def swap(self, target=8, swapped=True, night=2):
        from botc.info import SnakeCharmerChoice
        return SnakeCharmerChoice(night, 1, target=target, swapped=swapped)

    def test_both_seats_move_and_both_halves_with_them(self):
        from botc.worlds import Timeline
        world = self.world()
        state = self.board(infos=[self.swap()], days_done={2})
        chains = [c for c, _cost in S.possible_timelines(world, state) if c]
        self.assertTrue(chains)
        view = Timeline(world, chains[0])
        self.assertEqual(view.role_at(1, "D2"), "Vigormortis")
        self.assertTrue(view.evil_at(1, "D2"))
        self.assertEqual(view.role_at(8, "D2"), "SnakeCharmer")
        self.assertFalse(view.evil_at(8, "D2"))
        self.assertEqual(view.demon_at("D2"), 1)

    def test_the_new_snake_charmer_is_poisoned_and_the_demon_is_not(self):
        from botc import impairment
        from botc.worlds import Timeline
        world = self.world()
        state = self.board(infos=[self.swap()], days_done={2})
        chains = [c for c, _cost in S.possible_timelines(world, state) if c]
        view = Timeline(world, chains[0])
        hit = {s for src in impairment.sources_on(view, state, 3)
               if src.name == "Snake Charmer" for s in src.seats}
        self.assertEqual(hit, {8}, "the old Demon, not the new one")

    def test_it_is_applied_from_the_night_itself(self):
        """The swap is **immediate**.

        Settled at the table. A Snake Charmer acts at slot 11 and every
        Demon at 24 or later, so by the time the night's kill is made the
        charmer is holding the Demon — and it is the charmer's seat that
        kills. The old Demon is a poisoned good Snake Charmer and kills
        nobody.

        This asserted `D2` for a long time, for a reason worth keeping in
        view: writing the change at the night made the speaker stop
        holding the Snake Charmer at the very moment its own row is
        attributed, so the row read as invented and a world where the
        swap could really have happened scored 0.4 against 1.0 for one
        where it could not.

        That symptom was real and the cause was elsewhere. **A row belongs
        to whoever acted**, which is the board as it stood when the night
        began; the board afterwards is a different question. Dating the
        swap a whole phase late was paying for that confusion in the
        wrong place.
        """
        world = self.world()
        state = self.board(infos=[self.swap()], days_done={2})
        chains = [c for c, _cost in S.possible_timelines(world, state) if c]
        for change in chains[0]:
            with self.subTest(seat=change.seat + 1):
                self.assertEqual(change.phase, "N2")

    def test_a_world_where_it_could_happen_beats_one_where_it_could_not(self):
        state = self.board(infos=[self.swap()], days_done={2})
        could = self.world()
        could_not = among("Clockmaker", "SnakeCharmer", "Oracle", "Sage",
                          "Juggler", "Klutz", "Vigormortis", "Witch",
                          "Sweetheart")
        self.assertPct(S.explanation_cost(could, state), 1.0, 1e-9)
        # None is stronger still: no story at all fits.
        worse = S.explanation_cost(could_not, state)
        self.assertTrue(worse is None or worse < 1.0, worse)

    def test_a_recorded_swap_names_the_demon(self):
        """Read through `analyze` rather than `summarize`, because only
        one of them applies the changes: `summarize` reports the seat as
        it was *dealt*, and after a handover that is the wrong answer to
        "who is the Demon"."""
        state = self.board(infos=[self.swap(target=4)], days_done={2})
        rows = S.analyze(state)["rows"]
        self.assertGreater(rows[1]["demon_pct"], 60.0,
                           "whoever charmed now holds the star")
        self.assertLess(rows[4]["evil_pct"], 3.0,
                        "and the one they charmed is now a good "
                        "Snake Charmer")

    def test_a_choice_that_did_nothing_clears_that_seat(self):
        plain = self.board()
        nothing = self.board(infos=[self.swap(target=4, swapped=False)])
        was = S.summarize(S.solve(plain)[1], plain)
        now = S.summarize(S.solve(nothing)[1], nothing)
        self.assertLess(now[4]["evil_pct"], was[4]["evil_pct"])
        self.assertPct(now[4]["demon_pct"], 0.0, 0.01)

    def test_pointing_at_somebody_who_was_not_the_demon_offers_no_swap(self):
        world = self.world()
        state = self.board(infos=[self.swap(target=3)], days_done={2})
        self.assertEqual(
            [c for c, _cost in S.possible_timelines(world, state) if c], [])


class ThePitHag(SolverTest):
    """A seat that became something it was not dealt.

    Recorded rather than searched for, and that is the whole design. A
    Pit-Hag acts on any night, on any seat, for no reason the table sees
    — enumerating that would multiply the search by seats times
    characters times nights, almost all of it stories nothing is asking
    for. When it *is* known it is known loudly, and from then on that
    seat answers as something else.
    """

    CLAIMS = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz",
              "Barber", "Mutant", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def world(self):
        return among("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                     "Klutz", "Barber", "PitHag", "Vigormortis")

    def made(self, target, role, night=3):
        from botc.info import PitHagChoice
        return PitHagChoice(night, 7, target=target, role=role)

    def applied(self, info):
        from botc.worlds import Timeline
        world = self.world()
        state = self.board(infos=[info], days_done={3})
        for chain, _cost in S.possible_timelines(world, state):
            if chain:
                return Timeline(world, chain)
        return None

    def test_the_change_lands_on_the_night_it_happened(self):
        view = self.applied(self.made(0, "Philosopher"))
        self.assertIsNotNone(view)
        self.assertEqual(view.role_at(0, "N2"), "Clockmaker")
        self.assertEqual(view.role_at(0, "N3"), "Philosopher")

    def test_the_side_does_not_move(self):
        """A Townsfolk turned into a Minion's character keeps its own
        side — a good Poisoner is rare, legal, and the reason `Change`
        has kept its two halves apart since the Ogre."""
        good = self.applied(self.made(0, "SnakeCharmer"))
        self.assertFalse(good.evil_at(0, "N3"))
        evil = self.applied(self.made(7, "TownCrier"))
        self.assertTrue(evil.evil_at(7, "N3"),
                        "the Pit-Hag turning itself good would be a bargain")

    def test_it_can_only_make_what_nobody_is(self):
        world = self.world()
        state = self.board(infos=[self.made(0, "Dreamer")], days_done={3})
        # Seat 2 already holds the Dreamer, so this cannot have happened.
        self.assertFalse(state.infos[0].holds(world, state, None))

    def test_and_a_believed_token_does_not_block_it(self):
        """A Drunk holding the Fortune Teller token does not stop a real
        Fortune Teller being made: there is no Fortune Teller, only
        somebody who thinks so. Checked against the true assignment."""
        import inspect
        from botc.info import PitHagChoice
        source = inspect.getsource(PitHagChoice.holds)
        self.assertIn("role_at", source)
        self.assertNotIn("believes", source)

    def test_creating_something_in_play_argues_against_a_pit_hag(self):
        plain = S.solve(self.board())[1]
        odd = S.solve(self.board(infos=[self.made(0, "Dreamer")],
                                days_done={3}))[1]
        share = lambda v: sum(1 for w in v if "PitHag" in w.roles) / len(v)
        self.assertLess(share(odd), share(plain))

    def test_making_a_demon_makes_that_night_arbitrary(self):
        from botc import deaths as D
        world = self.world()
        quiet = [c.name for c in D.causes_on(
            world, self.board(infos=[self.made(0, "Philosopher")]), 3)]
        loud = [c.name for c in D.causes_on(
            world, self.board(infos=[self.made(0, "NoDashii")]), 3)]
        self.assertNotIn("Pit-Hag", quiet)
        self.assertIn("Pit-Hag", loud)

    def test_those_deaths_are_the_pit_hags_and_nothing_stops_them(self):
        from botc import deaths as D
        world = self.world()
        state = self.board(infos=[self.made(0, "NoDashii")])
        cause = next(c for c in D.causes_on(world, state, 3)
                     if c.name == "Pit-Hag")
        self.assertEqual(cause.kind, D.OTHER, "not the Demon's kill")
        self.assertTrue(cause.unstoppable)
        self.assertFalse(cause.must_fire, "nought is a legal number")


class TheFirstNightOfThisCharacter(SolverTest):
    """"Your first night" means the first night of *this* character.

    Every first-night reading used to read the board at night one, which
    is right for a character dealt at the start and wrong for one a
    Pit-Hag made on night four. They read their own night now — the same
    for an ordinary Washerwoman, and different for a created one.
    """

    def test_an_ordinary_first_night_reading_is_unchanged(self):
        from botc.info import Chef, GameState, Washerwoman
        claims = ["Washerwoman", "Librarian", "Investigator", "Chef",
                  "Empath", "FortuneTeller", "Undertaker", "Recluse",
                  "Saint"]
        state = GameState(n_players=9, script=scripts.TROUBLE_BREWING,
                          claims={i: r for i, r in enumerate(claims)})
        world = World(("Washerwoman", "Librarian", "Investigator", "Chef",
                       "Empath", "FortuneTeller", "Undertaker", "Poisoner",
                       "Imp"), (None,) * 9)
        self.assertTrue(Washerwoman(1, 0, a=1, b=5, role="Librarian")
                        .holds(world, state, None))
        self.assertTrue(Chef(1, 3, count=1).holds(world, state, None))

    def test_and_a_created_one_reads_the_night_it_arrived(self):
        import inspect
        from botc.info import Chef, Investigator, Librarian, Washerwoman
        for kind in (Washerwoman, Librarian, Investigator, Chef):
            with self.subTest(reading=kind.__name__):
                source = inspect.getsource(kind.holds)
                self.assertIn("self.night", source)
                self.assertNotIn('"N1"', source)


class CeremadnessNamesOneCharacter(SolverTest):
    """The status says "ceremadness" rather than "madness", and the
    difference is not cosmetic.

    Marking that death confirms a **Cerenovus** and nothing else. Other
    characters madden people — a Mutant is mad about being an Outsider
    all on its own — and a status called "executed for breaking madness"
    would quietly promise a deduction it cannot make. Naming the source
    keeps the promise the size of the rule.
    """

    def test_the_status_names_the_character(self):
        import pathlib
        page = (pathlib.Path(__file__).resolve().parent.parent
                / "ui" / "index.html").read_text()
        self.assertIn("Executed for breaking ceremadness", page)
        self.assertNotIn("Executed for breaking madness", page)

    def test_and_that_is_all_the_rule_confirms(self):
        """Read off the rule rather than the label: it looks for a
        Cerenovus by name."""
        import inspect
        source = inspect.getsource(S._plain_failures)
        self.assertIn('find_at("Cerenovus"', source)

    def test_marking_it_confirms_a_cerenovus(self):
        claims = ["Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                  "Klutz", "Barber", "Mutant", "Sweetheart"]
        state = GameState(n_players=9, script=SV,
                          claims={i: r for i, r in enumerate(claims)},
                          deaths={2: "D2"}, executions={2: 2},
                          madness_executions={2: 2})
        valid = S.solve(state)[1]
        self.assertTrue(valid)
        for world in valid:
            with self.subTest(world=world.roles):
                self.assertIn("Cerenovus", world.roles)

    def test_a_mutant_does_not_get_the_credit(self):
        """It is mad about being an Outsider without any Cerenovus, and
        an execution for that is an ordinary execution. Marking the
        ceremadness status would say something untrue, which is exactly
        what the rename prevents somebody doing by accident."""
        # A Mutant executed for claiming to be one is entered as a
        # confirmed Mutant claim, not as ceremadness; the status still
        # names only the Cerenovus (see the rule test above).
        import pathlib
        page = (pathlib.Path(__file__).resolve().parent.parent
                / "ui" / "index.html").read_text()
        self.assertNotIn("Mutant", page[page.index("function dayOptions"):
                                        page.index("const EVENT_WORDS")])


class AVortoxFalsifiesInformationNotChoices(SolverTest):
    """Nobody told a Philosopher what it took.

    The Vortox makes Townsfolk abilities yield false *information*, and
    several rows are not information at all — they are a choice the seat
    made and announced. A Philosopher decided to take the Oracle; a
    Courtier decided which character to name; a Klutz decided where to
    point; a Gambler decided what to guess.

    Treating those as readings made every board with a Philosopher on it
    impossible, which is how this was found: one Sects & Violets game in
    twenty-five, with the row rejected whatever the Philosopher chose.

    What follows from a choice is a different matter and still lands: a
    Philosopher that took the Town Crier gets that ability and **that**
    reading is inverted, a Gambler that guesses wrong still dies, and a
    Snake Charmer that chose the Vortox still swaps character and
    alignment with it — becoming a good Snake Charmer, poisoned for the
    rest of the game.
    """

    CLAIMS = ["Clockmaker", "Dreamer", "Philosopher", "Sage", "Juggler",
              "Klutz", "Barber", "Mutant", "Sweetheart"]

    def board(self, **kw):
        return GameState(n_players=9, script=SV,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         **kw)

    def world(self):
        """A Vortox at seat 9 and a real Philosopher at seat 3."""
        return among("Clockmaker", "Dreamer", "Philosopher", "Sage",
                     "Juggler", "Klutz", "Barber", "Witch", "Vortox")

    def test_a_philosophers_choice_survives_a_vortox(self):
        from botc.info import PhilosopherChoice
        for took in ("Oracle", "TownCrier", "Juggler", "SnakeCharmer"):
            with self.subTest(took=took):
                state = self.board(infos=[PhilosopherChoice(1, 2,
                                                            role=took)])
                self.assertIsNotNone(S.explanation_cost(self.world(), state))

    def test_the_choices_are_named_rather_than_guessed_at(self):
        """Anything not saying otherwise is treated as information, which
        is the safe direction: a reading wrongly inverted shows up as an
        impossible board, a choice wrongly inverted shows up as
        nothing."""
        from botc.info import (ArtistInfo, ClockmakerInfo, CourtierChoice,
                               Empath, GamblerGuess, KlutzChoice,
                               PhilosopherChoice, PitHagChoice,
                               SnakeCharmerChoice)
        for kind in (PhilosopherChoice, SnakeCharmerChoice, PitHagChoice,
                     CourtierChoice, KlutzChoice, GamblerGuess):
            with self.subTest(reading=kind.__name__):
                self.assertTrue(kind.is_a_choice)
        for kind in (Empath, ClockmakerInfo, ArtistInfo):
            with self.subTest(reading=kind.__name__):
                self.assertFalse(kind.is_a_choice)

    def test_but_what_the_choice_gained_is_still_inverted(self):
        """A Philosopher that took the Clockmaker gets that ability, and
        under a Vortox its answer has to be false — the choice is
        untouched, the reading it produced is not."""
        from botc.info import ClockmakerInfo, PhilosopherChoice
        world = self.world()
        # The Witch sits beside the Vortox, so the true answer is 1.
        took = PhilosopherChoice(1, 2, role="Clockmaker")
        true_one = self.board(infos=[took, ClockmakerInfo(1, 2, count=1)])
        false_one = self.board(infos=[took, ClockmakerInfo(1, 2, count=3)])
        self.assertIsNone(S.explanation_cost(world, true_one),
                          "under a Vortox the true answer cannot be given")
        self.assertIsNotNone(S.explanation_cost(world, false_one))


class TheBalloonist(SolverTest):
    """Shown a player each night of a different character type than the
    night before — and never told the type.

    The first reading here whose truth is not a property of one night.
    Every other row can be checked against a world on its own; this one
    means nothing without the row before it.
    """

    def board(self, rows):
        from botc import scripts
        from botc.info import GameState
        script = scripts.from_ids(
            "Trouble Brewing and a Balloonist",
            [k.lower() for k in scripts.TROUBLE_BREWING.keys] + ["balloonist"])
        claims = ["Balloonist", "Librarian", "Investigator", "Chef",
                  "Empath", "FortuneTeller", "Undertaker", "Recluse",
                  "Saint"]
        return GameState(n_players=9, script=script,
                         claims={i: r for i, r in enumerate(claims)},
                         infos=rows)

    def world(self):
        from botc.worlds import World
        return World(("Balloonist", "Librarian", "Investigator", "Chef",
                      "Empath", "FortuneTeller", "Undertaker", "Recluse",
                      "Imp"), (None,) * 9)

    def rows(self, *seats):
        from botc.info import BalloonistInfo
        return [BalloonistInfo(n + 1, 0, target=seat)
                for n, seat in enumerate(seats)]

    def test_two_townsfolk_running_needs_a_droisoned_night(self):
        """Possible, and only that way.

        A droisoned Balloonist may be shown the same type as last night —
        the wiki's own example. So a chain of two Townsfolk is not
        impossible, it is a Poisoner sitting on the Balloonist.

        This asserted flatly False, and wiring that into scoring threw
        out seven of forty mixed-script boards where the Balloonist had
        genuinely been poisoned. The chain function is kept and **not**
        wired in: it cannot price a droisoned night, and a check that
        cannot price something should not judge it.
        """
        self.assertFalse(S.a_balloonist_chain_fits(
            self.world(), self.board(self.rows(1, 2))))
        # ...and nothing acts on it: a board with that chain still
        # scores, because the Poisoner can pay for it.
        from botc.info import BalloonistInfo
        rows = self.rows(1, 2)
        self.assertIsNotNone(
            S.explanation_cost(self.world(), self.board(rows)))

    def test_a_townsfolk_then_the_demon_is_fine(self):
        self.assertTrue(S.a_balloonist_chain_fits(
            self.world(), self.board(self.rows(1, 8))))

    def test_the_recluse_may_be_shown_every_night(self):
        """Registration is what makes the chain a search rather than a
        comparison. A Recluse counts as Outsider, Minion or Demon, so one
        seat can satisfy several links — the wiki notes a devious
        Storyteller could show it every night."""
        self.assertTrue(S.a_balloonist_chain_fits(
            self.world(), self.board(self.rows(7, 7, 7))))

    def test_one_row_says_nothing(self):
        """It needs a pair. A single row that answered True would look
        verified while checking nothing."""
        self.assertTrue(S.a_balloonist_chain_fits(
            self.world(), self.board(self.rows(1))))

    def test_the_row_is_kept_rather_than_solved(self):
        """`weighed` is False, so the Vortox inversion leaves it alone
        and no per-row check pretends to judge the chain."""
        rows = self.rows(1, 2)
        state = self.board(rows)
        for row in rows:
            with self.subTest(night=row.night):
                self.assertFalse(row.weighed(state))


class AnHeirIsNotALiar(SolverTest):
    """A Farmer that dies at night hands the character to a living good
    player, who then says "I am the Farmer" — truthfully.

    `is_lying` compares against the character the seat was *dealt*, so it
    says yes, and a good seat that lies pays `TOWNSFOLK_LIE_PENALTY` at
    0.02. A Demon bluffing the same character pays
    `BLUFF_COLLISION_PENALTY` at 0.3.

    **The honest heir was fifteen times less likely than the demon.**

    Weighting, not legality — which is why three earlier attempts at
    widening the enumeration moved nothing. Both worlds were always
    legal and always generated; one was simply priced absurdly.
    """

    def board(self):
        from botc import scripts
        from botc.info import GameState
        ids = [k.lower() for k in scripts.TROUBLE_BREWING.keys] + ["farmer"]
        script = scripts.from_ids("Trouble Brewing and a Farmer", ids)
        return GameState(n_players=7, script=script,
                         claims={1: "Mayor", 2: "Farmer", 5: "Farmer"},
                         deaths={5: "N2"}, certainties={1: "self"})

    def worlds(self):
        from botc.worlds import World
        heir = World(("Butler", "Mayor", "Chef", "Soldier", "Monk",
                      "Farmer", "Imp"), (None,) * 7)
        liar = World(("Butler", "Mayor", "Imp", "Soldier", "Monk",
                      "Farmer", "Baron"), (None,) * 7)
        return heir, liar

    def test_the_honest_heir_is_not_priced_below_the_bluff(self):
        heir, liar = self.worlds()
        state = self.board()
        self.assertGreaterEqual(S.prior_weight(heir, state),
                                S.prior_weight(liar, state))

    def test_and_an_evil_seat_gets_no_such_excuse(self):
        """Exempting the seat outright made the demon's bluff cheaper
        too, and the answer got *worse* — 95.5 per cent to 98.6. Only a
        good seat can have been handed the character."""
        _heir, liar = self.worlds()
        state = self.board()
        self.assertIn(2, S._could_have_inherited(_heir, state))
        self.assertNotIn(2, S._could_have_inherited(liar, state))

    def test_the_seat_that_died_is_not_its_own_heir(self):
        heir, _liar = self.worlds()
        self.assertNotIn(5, S._could_have_inherited(heir, self.board()))


class FasterWithoutChangingAnAnswer(SolverTest):
    """Sects & Violets got slow when the Mutant multiplied the worlds.
    What made it quicker must not change a single answer — the corpus
    checks that board by board; these pin the pieces."""

    def test_the_indexed_timeline_answers_as_the_plain_walk_did(self):
        import random
        from botc.info import phase_index
        from botc.roles import alignment, TEAM
        from botc.worlds import Change, Timeline
        rng = random.Random(7)
        roles = ("Clockmaker", "Dreamer", "SnakeCharmer", "Oracle", "Barber",
                 "Mutant", "Witch", "FangGu")
        pool = list(roles) + ["Vortox", "Sage", "Philosopher"]
        phases = [f"{k}{n}" for n in range(1, 5) for k in "ND"]

        def plain_role(t, seat, phase):
            role = t.world.roles[seat]
            for c in t.changes:
                if c.seat == seat and c.role is not None \
                        and phase_index(c.phase) <= phase_index(phase):
                    role = c.role
            return role

        def plain_side(t, seat, phase):
            side = alignment(t.world.roles[seat])
            for c in t.changes:
                if c.seat != seat or phase_index(c.phase) > phase_index(phase):
                    continue
                side = c.side or (alignment(c.role) if c.role else side)
            return side

        def plain_demon(t, phase):
            seat = t.world.demon_at(phase)
            for c in t.changes:
                if c.role and TEAM[c.role] == "demon" \
                        and phase_index(c.phase) <= phase_index(phase):
                    seat = c.seat
            return seat

        world = World(roles, (None,) * 8)
        for _ in range(300):
            changes = tuple(
                Change(rng.choice(phases), rng.randrange(8),
                       rng.choice(pool + [None]),
                       rng.choice([None, "good", "evil"]))
                for _k in range(rng.randrange(5)))
            t = Timeline(world, changes)
            for phase in phases:
                self.assertEqual(t.demon_at(phase), plain_demon(t, phase))
                for seat in range(8):
                    self.assertEqual(t.role_at(seat, phase),
                                     plain_role(t, seat, phase))
                    self.assertEqual(t.alignment_at(seat, phase),
                                     plain_side(t, seat, phase))
                for role in pool:
                    want = next((p for p in range(8)
                                 if plain_role(t, p, phase) == role), None)
                    self.assertEqual(t.find_at(role, phase), want)

    def test_a_night_at_a_time_only_where_two_kinds_of_change_can_happen(self):
        from botc.info import SnakeCharmerChoice
        quiet = World(("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                       "Klutz", "Mutant", "Witch", "Vortox"), (None,) * 9)
        barber = World(("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler",
                        "Klutz", "Barber", "Witch", "FangGu"), (None,) * 9)
        plain = GameState(n_players=9, script=SV, claims={6: "Barber"},
                          deaths={6: "D1", 0: "N2"})
        self.assertEqual(S._movers_in(quiet, plain), 0)
        self.assertEqual(S._movers_in(barber, plain), 2)   # Barber, Fang Gu
        # A Barber nobody claimed is no swap to consider (table ruling).
        hidden = GameState(n_players=9, script=SV, claims={6: "Sage"},
                           deaths={6: "D1", 0: "N2"})
        self.assertEqual(S._movers_in(barber, hidden), 1)
        swapped = GameState(n_players=9, script=SV, claims={},
                            infos=[SnakeCharmerChoice(1, 2, target=8,
                                                      swapped=True)])
        self.assertEqual(S._movers_in(quiet, swapped), 1)

    def test_played_boards_put_the_votes_on_the_seats(self):
        """Where the page and both readers look for them. At the top of
        the payload they were dropped, and a Flowergirl who saw the Demon
        vote read as lying — the true world impossible."""
        import random
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import app
        import make_fixtures
        import simulate
        board = make_fixtures.played("x", SV, 8, 10, 3)
        self.assertNotIn("votes", board["payload"])
        self.assertTrue(any(p["voted"] for p in board["payload"]["players"]))
        deal, _heard = simulate.play(10, random.Random(8), nights=3,
                                     script=SV)
        seen = {}

        def keep(state, *a, **k):
            seen["state"] = state
            raise LookupError

        real = app.analyze
        app.analyze = keep
        try:
            app.run_solve(board["payload"])
        except LookupError:
            pass
        finally:
            app.analyze = real
        truth = World(tuple(deal.roles), tuple(deal.believes))
        self.assertIsNotNone(S.explanation_cost(truth, seen["state"]))


class ABarberSwapNeedsADeadBarberClaim(SolverTest):
    """Table ruling, 29.09.2026: a Barber swap is only considered once a
    seat that claimed the Barber has died. Its death offers every pair of
    seats, and a Barber nobody claimed is a death the table has no reason
    to read as one."""

    ROLES = ("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz",
             "Barber", "Witch", "Vortox")

    def stories(self, claim, **kw):
        state = GameState(n_players=9, script=SV, claims={6: claim},
                          deaths={6: "D1"}, quiet_nights={2}, **kw)
        return S.possible_timelines(World(self.ROLES, (None,) * 9), state)

    def test_a_claimed_barber_offers_the_swaps(self):
        self.assertGreater(len(self.stories("Barber")), 30)

    def test_a_hidden_one_offers_none(self):
        self.assertEqual(self.stories("Sage"), [((), 1.0)])

    def test_saying_so_later_counts_as_a_claim(self):
        from botc.info import BecameInfo
        got = self.stories("Sage", infos=[BecameInfo(1, 6, role="Sage",
                                                     was="Barber")])
        self.assertGreater(len(got), 30)


class ASwapThatIsReported(SolverTest):
    """Table rulings of 30.09.2026.

    A seat whose character changed and says so ("became X, was Y") was
    dealt Y: the search deals from Y and the new claim is no lie. A
    reported change nothing on the record explains opens the Barber's
    swap to every seat that died before it. And once a swap is open, the
    credit inside a world follows what the table does: the Demon usually
    swaps, half the time with one of its own Minions.
    """

    ROLES = ("Clockmaker", "Dreamer", "Oracle", "Sage", "Juggler", "Klutz",
             "Barber", "Witch", "Vortox")

    def test_the_search_deals_from_what_they_claimed_before(self):
        from botc.info import BecameInfo
        state = GameState(n_players=9, script=SV,
                          claims={2: "Dreamer"},
                          infos=[BecameInfo(2, 2, role="Dreamer",
                                            was="Oracle")])
        self.assertEqual(state.search_claims()[2], "Oracle")
        self.assertEqual(state.claims[2], "Dreamer")
        world = World(self.ROLES, (None,) * 9)
        self.assertFalse(S.is_lying(world, state, 2))

    def test_an_unexplained_change_opens_the_swap_to_the_dead(self):
        from botc.info import BecameInfo
        state = GameState(n_players=9, script=SV,
                          claims={6: "Sage", 2: "Dreamer"},
                          deaths={6: "D1"}, quiet_nights={2},
                          infos=[BecameInfo(2, 2, role="Dreamer",
                                            was="Oracle")])
        self.assertIn(6, S.barber_claimants(state))

    def test_a_recorded_creation_explains_it(self):
        from botc.info import BecameInfo, PitHagChoice
        state = GameState(n_players=9, script=SV,
                          claims={6: "Sage", 2: "Dreamer"},
                          deaths={6: "D1"}, quiet_nights={2},
                          infos=[BecameInfo(2, 2, role="Dreamer",
                                            was="Oracle"),
                                 PitHagChoice(2, 7, target=2,
                                              role="Dreamer")])
        self.assertNotIn(6, S.barber_claimants(state))

    def test_the_demon_and_its_minion_swap_for_free(self):
        state = GameState(n_players=9, script=SV, claims={6: "Barber"},
                          deaths={6: "D1"}, quiet_nights={2})
        offers = S._barber_offers(World(self.ROLES, (None,) * 9), state)
        ours = [cost for extra, cost in offers
                if extra and isinstance(extra[0], S.DemonMinionSwap)]
        other = [cost for extra, cost in offers
                 if extra and isinstance(extra[0], S.OtherSwap)]
        self.assertEqual(ours, [1.0])          # the Vortox and the Witch
        self.assertTrue(other and set(other) == {S.BARBER_SWAP_PENALTY})

    def test_the_credit_inside_a_world_follows_the_table(self):
        world = World(self.ROLES, (None,) * 9)
        state = GameState(n_players=9, script=SV, claims={6: "Barber"},
                          deaths={6: "D1"}, quiet_nights={2})
        offers = S._barber_offers(world, state)
        swaps = [extra for extra, _cost in offers if extra]
        n_other = sum(isinstance(e[0], S.OtherSwap) for e in swaps)
        ours = next(e for e in swaps if isinstance(e[0], S.DemonMinionSwap))
        other = next(e for e in swaps if isinstance(e[0], S.OtherSwap))
        self.assertAlmostEqual(S._barber_share(world, (), state),
                               1 - S.BARBER_SWAP_SHARE)
        self.assertAlmostEqual(
            S._barber_share(world, ours, state),
            S.BARBER_SWAP_SHARE * S.BARBER_DEMON_MINION_SHARE)
        # Every other pair, taken together, gets the other half — the
        # price each paid taken back out.
        self.assertAlmostEqual(
            S._barber_share(world, other, state) * S.BARBER_SWAP_PENALTY
            * n_other,
            S.BARBER_SWAP_SHARE * (1 - S.BARBER_DEMON_MINION_SHARE))


class FoundByTheWideSweep(SolverTest):
    """Pinned without the simulator (29.09.2026)."""

    def test_a_timeline_reads_its_changes_in_time_order(self):
        from botc.worlds import Change, Timeline, World
        w = World(("SnakeCharmer", "Sweetheart", "FangGu", "Oracle",
                   "Dreamer"), (None,) * 5)
        jump = Change("N2", 1, "FangGu", "evil")
        swap = (Change("N3", 0, "FangGu", "evil"),
                Change("N3", 1, "SnakeCharmer", "good"))
        # Written out of order, as a story assembled a night at a time is.
        view = Timeline(w, swap + (jump,))
        self.assertEqual(view.role_at(1, "N3"), "SnakeCharmer")
        self.assertEqual(view.demon_at("N3"), 0)
        # And a timeline over a timeline is one timeline.
        nested = Timeline(Timeline(w, (jump,)), swap)
        self.assertEqual(nested.role_at(1, "N2"), "FangGu")
        self.assertEqual(nested.role_at(1, "N3"), "SnakeCharmer")

    def test_the_mathematician_counts_only_the_living(self):
        from botc.info import GameState, _possible_impairment_counts
        from botc.worlds import World
        from botc import scripts
        # A Philosopher that took the Dreamer drunks the real Dreamer; dead,
        # that Dreamer has no ability left to go wrong.
        w = World(("Philosopher", "Dreamer", "Mathematician", "Oracle",
                   "Vortox"), (None,) * 5)
        from botc.info import PhilosopherChoice
        infos = [PhilosopherChoice(1, 0, 0, role="Dreamer")]
        alive = GameState(n_players=5, script=scripts.SECTS_AND_VIOLETS,
                          infos=infos)
        dead = GameState(n_players=5, script=scripts.SECTS_AND_VIOLETS,
                         infos=infos, deaths={1: ("D1",)})
        self.assertEqual(_possible_impairment_counts(w, alive, 2)[0], 1)
        self.assertEqual(_possible_impairment_counts(w, dead, 2)[0], 0)
