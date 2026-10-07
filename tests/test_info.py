"""Each information type, checked against worlds built by hand.

These bypass the search entirely: build a world, ask the statement
whether it holds, and compare with what the rules say. When one of these
fails you know the rule is wrong, not the enumeration.
"""

import unittest

from helpers import SolverTest, game
from botc.info import (Washerwoman, Librarian, Investigator, Chef, Empath,
                       FortuneTeller, Undertaker, Ravenkeeper, SlayerShot,
                       VirginNomination, phase_index)
from botc.worlds import World


def world(roles, believes=None):
    return World(tuple(roles), tuple(believes or [None] * len(roles)))


# Seats:      0            1         2       3         4
BASIC = ["Washerwoman", "Empath", "Chef", "Imp", "Poisoner"]


class Phases(SolverTest):

    def test_nights_and_days_interleave(self):
        self.assertEqual(phase_index("N1"), 0)
        self.assertEqual(phase_index("E1"), 1)
        self.assertEqual(phase_index("D1"), 1)
        self.assertEqual(phase_index("N2"), 2)
        self.assertLess(phase_index("N2"), phase_index("N3"))


class RoleInformation(SolverTest):

    def setUp(self):
        self.s = game(5, claims={})

    def test_washerwoman_needs_the_role_in_one_of_the_pair(self):
        w = world(BASIC)
        self.assertTrue(Washerwoman(1, 0, a=1, b=2, role="Chef").holds(w, self.s, None))
        self.assertFalse(Washerwoman(1, 0, a=1, b=3, role="Monk").holds(w, self.s, None))

    def test_spy_can_show_up_as_any_townsfolk(self):
        w = world(["Washerwoman", "Spy", "Chef", "Imp", "Baron"])
        self.assertTrue(Washerwoman(1, 0, a=1, b=4, role="Monk").holds(w, self.s, None))

    def test_investigator_accepts_the_recluse_as_a_minion(self):
        w = world(["Investigator", "Recluse", "Chef", "Imp", "Poisoner"])
        self.assertTrue(Investigator(1, 0, a=1, b=2, role="Baron").holds(w, self.s, None))
        self.assertFalse(Investigator(1, 0, a=2, b=0, role="Baron").holds(w, self.s, None))

    def test_librarian_no_outsiders_means_none_in_play(self):
        none_said = Librarian(1, 0, a=None, b=None, role="")
        self.assertTrue(none_said.holds(world(BASIC), self.s, None))
        with_saint = world(["Washerwoman", "Saint", "Chef", "Imp", "Poisoner"])
        self.assertFalse(none_said.holds(with_saint, self.s, None))

    def test_undertaker_and_ravenkeeper_read_misregistration(self):
        w = world(["Undertaker", "Recluse", "Spy", "Imp", "Ravenkeeper"])
        # The Undertaker only has a reading if an execution killed
        # somebody, and it is about that seat.
        hanged = game(5, claims={}, deaths={1: "E1"})
        # The Recluse may read as a Demon
        self.assertTrue(Undertaker(2, 0, target=1, role="Imp").holds(w, hanged, None))
        # The Spy may read as a Townsfolk
        self.assertTrue(Ravenkeeper(2, 4, target=2, role="Monk").holds(w, self.s, None))
        # The Recluse reads evil or good, never as another Townsfolk
        self.assertFalse(Undertaker(2, 0, target=1, role="Monk").holds(w, hanged, None))

    def test_the_undertaker_needs_an_execution_to_read(self):
        w = world(["Undertaker", "Recluse", "Spy", "Imp", "Ravenkeeper"])
        quiet = game(5, claims={})
        survived = game(5, claims={}, executions={1: 1})
        self.assertFalse(Undertaker(2, 0, target=1, role="Recluse")
                         .holds(w, quiet, None), "nobody was executed")
        self.assertFalse(Undertaker(2, 0, target=1, role="Recluse")
                         .holds(w, survived, None), "nobody died of it")


class Counting(SolverTest):

    def setUp(self):
        self.s = game(5, claims={})

    def test_chef_counts_adjacent_evil_around_the_circle(self):
        # Imp at 3 and Poisoner at 4 sit together: exactly one pair.
        w = world(BASIC)
        self.assertTrue(Chef(1, 2, count=1).holds(w, self.s, None))
        self.assertFalse(Chef(1, 2, count=0).holds(w, self.s, None))

    def test_chef_wraps_from_the_last_seat_to_the_first(self):
        w = world(["Imp", "Empath", "Chef", "Washerwoman", "Poisoner"])
        self.assertTrue(Chef(1, 2, count=1).holds(w, self.s, None))

    def test_chef_accepts_a_range_when_the_recluse_is_ambiguous(self):
        # The Recluse sits beside the Imp, so 1 or 2 pairs are both tellable.
        w = world(["Empath", "Chef", "Recluse", "Imp", "Poisoner"])
        for n in (1, 2):
            self.assertTrue(Chef(1, 1, count=n).holds(w, self.s, None), n)
        self.assertFalse(Chef(1, 1, count=0).holds(w, self.s, None))

    def test_empath_reads_its_two_living_neighbours(self):
        w = world(BASIC)
        s = game(5, claims={})
        self.assertTrue(Empath(1, 0, count=1).holds(w, s, None))   # seats 4 and 1
        self.assertFalse(Empath(1, 0, count=0).holds(w, s, None))

    def test_empath_looks_past_the_dead(self):
        w = world(BASIC)
        # Seat 4 (Poisoner) died, so seat 0 now reads seats 3 and 1
        s = game(5, claims={}, deaths={4: "N2"})
        self.assertTrue(Empath(3, 0, count=1).holds(w, s, None))
        alive = s.alive_at("N3")
        self.assertNotIn(4, alive)


class FortuneTellerReadings(SolverTest):

    def setUp(self):
        self.s = game(5, claims={})
        self.w = world(BASIC)

    def test_yes_on_the_demon(self):
        self.assertTrue(FortuneTeller(1, 1, a=3, b=0, yes=True).holds(self.w, self.s, None))

    def test_yes_on_the_red_herring_alone(self):
        info = FortuneTeller(1, 1, a=0, b=2, yes=True)
        self.assertFalse(info.holds(self.w, self.s, None))
        self.assertTrue(info.holds(self.w, self.s, 0))

    def test_yes_on_the_recluse(self):
        w = world(["Recluse", "Empath", "Chef", "Imp", "Poisoner"])
        self.assertTrue(FortuneTeller(1, 1, a=0, b=2, yes=True).holds(w, self.s, None))

    def test_no_rules_out_the_demon_and_the_herring(self):
        self.assertTrue(FortuneTeller(1, 1, a=0, b=2, yes=False).holds(self.w, self.s, None))
        self.assertFalse(FortuneTeller(1, 1, a=3, b=2, yes=False).holds(self.w, self.s, None))
        self.assertFalse(FortuneTeller(1, 1, a=0, b=2, yes=False).holds(self.w, self.s, 0))

    def test_no_still_allows_the_recluse_to_read_good(self):
        w = world(["Recluse", "Empath", "Chef", "Imp", "Poisoner"])
        self.assertTrue(FortuneTeller(1, 1, a=0, b=2, yes=False).holds(w, self.s, None))


class WitnessedEvents(SolverTest):

    def setUp(self):
        self.s = game(5, claims={})

    def test_a_landed_slayer_shot_is_a_hard_fact(self):
        self.assertTrue(SlayerShot(2, 0, target=3, died=True).hard())
        self.assertFalse(SlayerShot(2, 0, target=3, died=False).hard())

    def test_a_landed_shot_needs_a_real_slayer_and_a_demon(self):
        w = world(["Slayer", "Empath", "Chef", "Imp", "Poisoner"])
        self.assertTrue(SlayerShot(2, 0, target=3, died=True).holds(w, self.s, None))
        self.assertFalse(SlayerShot(2, 0, target=4, died=True).holds(w, self.s, None))
        no_slayer = world(["Washerwoman", "Empath", "Chef", "Imp", "Poisoner"])
        self.assertFalse(SlayerShot(2, 0, target=3, died=True).holds(no_slayer, self.s, None))

    def test_a_landed_shot_may_have_hit_the_recluse(self):
        w = world(["Slayer", "Empath", "Recluse", "Imp", "Poisoner"])
        self.assertTrue(SlayerShot(2, 0, target=2, died=True).holds(w, self.s, None))

    def test_a_shot_that_did_nothing_only_clears_the_target(self):
        w = world(["Slayer", "Empath", "Chef", "Imp", "Poisoner"])
        self.assertTrue(SlayerShot(2, 0, target=2, died=False).holds(w, self.s, None))
        self.assertFalse(SlayerShot(2, 0, target=3, died=False).holds(w, self.s, None))

    def test_a_virgin_trigger_is_hard_and_names_both_seats(self):
        w = world(["Virgin", "Empath", "Chef", "Imp", "Poisoner"])
        fired = VirginNomination(1, 0, nominator=1, triggered=True)
        self.assertTrue(fired.hard())
        self.assertTrue(fired.holds(w, self.s, None))
        self.assertFalse(VirginNomination(1, 0, nominator=4, triggered=True)
                         .holds(w, self.s, None))

    def test_a_virgin_trigger_accepts_the_spy_as_a_townsfolk(self):
        w = world(["Virgin", "Spy", "Chef", "Imp", "Baron"])
        self.assertTrue(VirginNomination(1, 0, nominator=1, triggered=True)
                        .holds(w, self.s, None))

    def test_a_quiet_nomination_says_the_nominator_was_no_townsfolk(self):
        w = world(["Virgin", "Empath", "Chef", "Imp", "Poisoner"])
        quiet = VirginNomination(1, 0, nominator=1, triggered=False)
        self.assertFalse(quiet.hard())
        self.assertFalse(quiet.holds(w, self.s, None))
        self.assertTrue(VirginNomination(1, 0, nominator=4, triggered=False)
                        .holds(w, self.s, None))


class Attribution(SolverTest):

    def test_a_speaker_who_claims_the_role_owns_their_own_words(self):
        s = game(7)
        self.assertEqual(Empath(1, 4, count=1).source_seat(s), 4)

    def test_a_mismatch_is_read_as_relaying_the_one_claimant(self):
        s = game(7)
        self.assertEqual(Empath(1, 0, count=1).source_seat(s), 4)

    def test_with_nobody_claiming_it_the_statement_floats(self):
        s = game(7, claims={0: "Washerwoman"})
        self.assertIsNone(Empath(1, 0, count=1).source_seat(s))

    def test_witnessed_events_never_float(self):
        s = game(7, claims={0: "Washerwoman"})
        self.assertEqual(SlayerShot(2, 0, target=1, died=True).source_seat(s), 0)
        self.assertEqual(VirginNomination(1, 0, nominator=1).source_seat(s), 0)


if __name__ == "__main__":
    unittest.main()


class TheLibrarianBeingToldNobody(SolverTest):
    """"No Outsiders in play" is not a claim about the bag.

    It is a claim about what the Storyteller *showed*, and those are
    different things. A Recluse registers as a Minion or the Demon
    whenever the Storyteller likes, so a Librarian can honestly be told
    nobody with a Recluse sitting right there — which is the case the
    first version of this ruled out, and ruling out a game that happens is
    the wrong direction to be wrong in.
    """

    SEVEN = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker"]

    def reading(self):
        return Librarian(1, 1, a=None, b=None, role="")

    def board(self, claims=None):
        from botc.info import GameState
        from botc import scripts
        return GameState(n_players=len(claims or self.SEVEN),
                         script=scripts.TROUBLE_BREWING,
                         claims={i: r for i, r in
                                 enumerate(claims or self.SEVEN)})

    def world_with(self, outsider):
        roles = ["Washerwoman", "Librarian", "Investigator", "Chef",
                 outsider or "Empath", "Poisoner", "Imp"]
        believes = ["Empath" if r == "Drunk" else None for r in roles]
        return World(tuple(roles), tuple(believes))

    def test_with_no_outsider_at_all(self):
        self.assertTrue(self.reading().holds(self.world_with(None),
                                             self.board(), None))

    def test_a_recluse_can_hide_from_it(self):
        self.assertTrue(self.reading().holds(self.world_with("Recluse"),
                                             self.board(), None),
                        "it registered as a Minion, so nobody showed")

    def test_the_ones_that_cannot_hide(self):
        """The Saint, the Butler and the Drunk have no other team to
        register as, so one of those in play means somebody was shown."""
        for outsider in ("Saint", "Butler", "Drunk"):
            with self.subTest(outsider=outsider):
                self.assertFalse(self.reading().holds(
                    self.world_with(outsider), self.board(), None))

    def test_it_restores_worlds_a_table_could_actually_be_in(self):
        """Eight players wants one Outsider, so this is exactly the size
        where the two readings come apart."""
        from botc.info import GameState
        from botc import scripts
        import botc.solver as S
        claims = self.SEVEN + ["Recluse"]
        state = GameState(n_players=8, script=scripts.TROUBLE_BREWING,
                          claims={i: r for i, r in enumerate(claims)},
                          infos=[self.reading()])
        valid = S.solve(state)[1]
        self.assertTrue(valid)
        with_recluse = [w for w in valid if "Recluse" in w.roles]
        self.assertGreater(len(with_recluse), 100,
                           "a Recluse being shown as evil is ordinary play")
        # And none of those needs anybody impaired to explain it.
        self.assertTrue(any(S.explanation_cost(w, state) == 1.0
                            for w in with_recluse))


class ADayThatFinishedWithNoExecution(SolverTest):
    """Which is how most days end, and the board had no way to say so.

    Until this existed the only way to record that a day happened was for
    somebody to die in it. That left the page stuck: an execution on day
    two advanced nothing, so the statuses on offer stayed day two's and
    there was no way to reach day three without inventing a reading for
    night three first.

    It rules out no world by itself — the solver already assumes no
    execution unless one is recorded. What it does is say the game
    *reached* that day, which bounds how long a story can run.
    """

    SEATS = ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
             "Gambler", "Gossip", "Tinker", "Moonchild"]

    def board(self, **kw):
        from botc.info import GameState
        from botc import scripts
        return GameState(n_players=9, script=scripts.BAD_MOON_RISING,
                         claims={i: r for i, r in enumerate(self.SEATS)}, **kw)

    def test_it_moves_the_game_on(self):
        self.assertEqual(self.board().final_phase(), "N1")
        self.assertEqual(self.board(days_done={3}).final_phase(), "D3")

    def test_the_furthest_thing_recorded_still_wins(self):
        got = self.board(days_done={2}, deaths={4: "N5"})
        self.assertEqual(got.final_phase(), "N5")

    def test_it_rules_out_no_world_on_its_own(self):
        """The solver already assumes nobody was executed unless somebody
        was, so saying so adds no constraint — only a boundary."""
        import botc.solver as S
        plain = len(S.solve(self.board())[1])
        marked = len(S.solve(self.board(days_done={2, 3}))[1])
        self.assertEqual(plain, marked)

    def test_but_it_does_bound_how_long_a_story_can_run(self):
        """A Mastermind buys exactly one more day after the Demon is
        executed. Recording that a second day also finished is what says
        the game ran on too far for that."""
        import botc.solver as S
        from botc.worlds import World
        # A Shabaloth, not the Zombuul this was: a Zombuul survives its
        # first execution, so running on two more days would be legal.
        world = World(("Grandmother", "Sailor", "Shabaloth", "Exorcist",
                       "Innkeeper", "Gambler", "Gossip", "Mastermind",
                       "Tinker"), (None,) * 9)
        one_more = self.board(deaths={2: "E2"}, quiet_nights={3},
                              days_done={3})
        two_more = self.board(deaths={2: "E2"}, quiet_nights={3},
                              days_done={3, 4})
        self.assertIsNotNone(S.explanation_cost(world, one_more))
        self.assertIsNone(S.explanation_cost(world, two_more))


class AReadingTheTableConfirmed(SolverTest):
    """"This checked out" is evidence, not proof.

    Different from `trust`, which says "I believe this row is real" and
    prices making it up. This says the *content* was right: an Undertaker
    whose reading matched what was later established, a Washerwoman whose
    pair turned out as described.

    It never settles anything, because a Spy reading the grimoire can
    feed a Minion true information all game — which is what separates it
    from the seat-level "confirmed" that pins a character outright.

    The players tick it between them. Nothing here can derive it: the
    solver does not know what the table later agreed.
    """

    CLAIMS = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
              "FortuneTeller", "Undertaker", "Recluse", "Saint"]

    def reading(self, confirmed, count=1):
        from botc.info import GameState, Undertaker
        rows = []
        for i in range(count):
            row = Undertaker(2 + i, 6, target=7 if i == 0 else 3,
                             role="Recluse" if i == 0 else "Chef")
            row.confirmed = confirmed
            rows.append(row)
        return GameState(n_players=9,
                         claims={i: r for i, r in enumerate(self.CLAIMS)},
                         deaths={7: "X1", 3: "X2"}, infos=rows)

    def share(self, state, seat=6, role="Undertaker"):
        import botc.solver as S
        rows = S.summarize(S.solve(state)[1], state)
        return dict(rows[seat]["roles"]).get(role, 0.0)

    def test_a_confirmed_reading_argues_for_its_source(self):
        plain = self.share(self.reading(False))
        marked = self.share(self.reading(True))
        self.assertGreater(marked, plain)

    def test_and_it_accumulates(self):
        one = self.share(self.reading(True, count=1))
        two = self.share(self.reading(True, count=2))
        three = self.share(self.reading(True, count=3))
        self.assertGreater(two, one)
        self.assertGreater(three, two)

    def test_but_never_reaches_certainty(self):
        """A Spy reading the grimoire can feed a Minion true information
        all game, so no pile of confirmations settles anything."""
        self.assertLess(self.share(self.reading(True, count=3)), 100.0)

    def test_the_boost_only_counts_where_the_seat_holds_the_role(self):
        """It is evidence that *this* reading came from who it says, so a
        world where somebody else is the Undertaker gains nothing."""
        import botc.solver as S
        from botc.worlds import World
        state = self.reading(True)
        elsewhere = World(("Undertaker", "Librarian", "Investigator",
                           "Chef", "Empath", "FortuneTeller", "Poisoner",
                           "Recluse", "Saint"), (None,) * 9)
        self.assertPct(S.confirmed_boost(elsewhere, state), 1.0, 1e-9)
        theirs = World(("Washerwoman", "Librarian", "Investigator", "Chef",
                        "Empath", "FortuneTeller", "Undertaker", "Recluse",
                        "Saint"), (None,) * 9)
        self.assertGreater(S.confirmed_boost(theirs, state), 1.0)

    def test_an_unmarked_board_is_unchanged(self):
        """Nobody who does not use it pays for it."""
        import botc.solver as S
        from botc.worlds import World
        state = self.reading(False)
        world = World(("Washerwoman", "Librarian", "Investigator", "Chef",
                       "Empath", "FortuneTeller", "Undertaker", "Recluse",
                       "Saint"), (None,) * 9)
        self.assertPct(S.confirmed_boost(world, state), 1.0, 1e-9)

    def test_proof_rows_are_not_offered_it(self):
        """A Virgin that triggered and a Slayer that fired establish a
        character outright. A softer nudge on top would say less than the
        board already says."""
        import pathlib
        page = (pathlib.Path(__file__).resolve().parent.parent
                / "ui" / "index.html").read_text()
        self.assertIn('PROOF_ROWS = ["VirginNomination", "SlayerShot"]', page)


class BelievingThatAReadingHappened(SolverTest):
    """`trust` prices a world in which the row was made up.

    A different question from "checked out": that one asks whether the
    reading was *right*, this asks whether it happened at all. It matters
    when somebody relays information second-hand — "the Empath said 2" —
    and no seat has claimed the character it came from.

    The control was written, the constant was tuned and the solver logic
    was tested, and nothing on the page ever called it. Every reading sat
    at neutral until it was finally wired up.
    """

    def weight_on_worlds_with(self, role, trust):
        import botc.solver as S
        from botc.info import Empath, GameState
        # Some seats unclaimed, so some worlds hold an Empath and others
        # do not. That is the only situation where trust can bite: when
        # *no* world can hold the character, every world pays the same
        # invention cost and it cancels out of the percentages.
        claims = {0: "Washerwoman", 1: "Librarian", 2: "Investigator",
                  3: "Chef", 7: "Recluse", 8: "Saint"}
        state = GameState(n_players=9, claims=claims,
                          infos=[Empath(1, 4, trust, count=2)])
        valid = S.solve(state, max_worlds=60_000)[1]
        total = sum(S.world_weight(w, state) for w in valid) or 1.0
        got = sum(S.world_weight(w, state) for w in valid
                  if role in w.roles)
        return 100.0 * got / total

    def test_believing_it_argues_the_character_is_there(self):
        low = self.weight_on_worlds_with("Empath", -3)
        mid = self.weight_on_worlds_with("Empath", 0)
        high = self.weight_on_worlds_with("Empath", 3)
        self.assertLess(low, mid)
        self.assertLess(mid, high)

    def test_it_is_a_separate_lever_from_checked_out(self):
        """One prices the row being invented, the other argues its source
        is who they say. Both can apply to the same reading."""
        import botc.solver as S
        from botc.info import Undertaker
        row = Undertaker(2, 6, 2, target=7, role="Recluse")
        row.confirmed = True
        self.assertEqual(row.trust, 2)
        self.assertTrue(row.confirmed)
        self.assertLess(S.invention_cost(row), 0.4)

    def test_the_page_actually_offers_it(self):
        """It did not, for the whole life of the project."""
        import pathlib
        page = (pathlib.Path(__file__).resolve().parent.parent
                / "ui" / "index.html").read_text()
        self.assertIn("body.appendChild(trustSel(rec));", page)


class LegalIsNotTrue(SolverTest):
    """Misregistration makes information legal, not true.

    A Spy shown as the Slayer is still a Spy. The Storyteller is
    permitted to say it, and saying it does not make the seat a Slayer.

    Two questions, and the solver asked one of them for a long time.
    `holds` answers *could this have been said*, which is right nearly
    everywhere. A Vortox needs the other — it falsifies what an ability
    *yields*, and a misregistered reading is already false — so it asks
    `is_true` where a row has one.

    Asking the wrong one made a legal misregistered reading look true, so
    the Vortox had to be droisoned to explain it, and boards that really
    happened were priced as though something had gone wrong.
    """

    ROLES = ("Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Spy")

    def world(self):
        from botc.worlds import World
        return World(self.ROLES, (None,) * 9)

    def board(self, **kw):
        from botc.info import GameState
        return GameState(n_players=9, claims={}, **kw)

    def test_a_pair_reading_shown_a_misregistering_seat(self):
        from botc.info import Washerwoman
        row = Washerwoman(1, 4, a=8, b=1, role="Washerwoman")
        self.assertTrue(row.holds(self.world(), self.board(), None))
        self.assertFalse(row.is_true(self.world(), self.board()))

    def test_and_one_shown_the_real_thing(self):
        from botc.info import Washerwoman
        row = Washerwoman(1, 4, a=0, b=1, role="Washerwoman")
        self.assertTrue(row.holds(self.world(), self.board(), None))
        self.assertTrue(row.is_true(self.world(), self.board()))

    def test_the_single_target_readings_too(self):
        from botc.info import Ravenkeeper, Undertaker
        state = self.board(executions={1: 7}, deaths={7: "E1"})
        for row in (Undertaker(2, 6, target=7, role="Imp"),
                    Ravenkeeper(2, 0, target=8, role="Chef")):
            with self.subTest(reading=type(row).__name__):
                self.assertTrue(row.holds(self.world(), state, None))
                self.assertFalse(row.is_true(self.world(), state))

    def test_count_readings_have_one_too_and_lean_on_nobody(self):
        """What is so is a number, and a count can be held to it.

        This said the opposite until 07.10.2026: "there is no single fact
        that was the true one", and so a Chef told one at a table with no
        evil pair but a Recluse beside the Demon read as *true* under a
        Vortox. The table ruling that day: the truth is how many really
        are evil, whatever anybody could have registered as.

        What stays as it was is `leaned_on`. A Chef told one beside two
        Recluses leaned on *one of them*, and which is not a question the
        reading can answer — that still needs alternative explanations
        rather than one.
        """
        from botc.info import Chef, Empath, Info, OracleInfo
        for kind in (Chef, Empath, OracleInfo):
            with self.subTest(reading=kind.__name__):
                self.assertIn("is_true", vars(kind))
                self.assertIs(kind.leaned_on, Info.leaned_on)


class ADroisonedCharacterCannotMisregister(SolverTest):
    """Registration is a plain ability, and a plain ability does not work.

    A Storyteller chooses freely what a droisoned *information* role
    yields, because the information is arbitrary. A poisoned Recluse is a
    Recluse and shows as one.

    The check could not go in `registers_as_role`, and giving that a
    world would not have helped: **whether a seat was droisoned is not
    known when `holds` runs.** It is chosen, by the impairment plan,
    which settles afterwards. So a row says what it *leaned on* and those
    seats are forbidden from being droisoned that night.
    """

    ROLES = ("Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Poisoner")

    def world(self):
        from botc.worlds import World
        return World(self.ROLES, (None,) * 9)

    def test_a_reading_that_leaned_on_a_seat_says_so(self):
        from botc.info import GameState, Investigator
        row = Investigator(1, 2, a=7, b=0, role="Poisoner")
        self.assertEqual(row.leaned_on(self.world(), GameState(
            n_players=9, claims={})), (7,))

    def test_and_one_that_did_not_says_nothing(self):
        """The Poisoner really is the Poisoner, so either seat could have
        been droisoned and nothing was leaned on."""
        from botc.info import GameState, Investigator
        row = Investigator(1, 2, a=8, b=0, role="Poisoner")
        self.assertEqual(row.leaned_on(self.world(), GameState(
            n_players=9, claims={})), ())

    def test_the_board_still_fits(self):
        """Permissive, not restrictive: it rules out the combination —
        poisoning the Recluse *and* having it misregister — rather than
        the board."""
        import botc.solver as S
        from botc.info import Empath, GameState, Investigator
        claims = ["Washerwoman", "Librarian", "Investigator", "Chef",
                  "Empath", "FortuneTeller", "Undertaker", "Recluse",
                  "Saint"]
        state = GameState(
            n_players=9, claims={i: r for i, r in enumerate(claims)},
            infos=[Investigator(1, 2, a=7, b=0, role="Poisoner"),
                   Empath(1, 4, count=0)])
        self.assertIsNotNone(S.explanation_cost(self.world(), state))
