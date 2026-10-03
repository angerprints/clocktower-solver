"""Can a night be replayed?

The experiment the night-order design asks for, before any of the
solver's three passes is touched. If a night that was just *played*
cannot be reproduced by walking it in slot order, one that has to be
*inferred* certainly cannot.
"""

import random
import unittest

import nightwalk
import simulate
from helpers import SolverTest


class AKnownNightCanBeReplayed(SolverTest):
    """Walk a night the simulator already played and compare.

    The hidden choices — where the Poisoner went, who the Demon took —
    are handed to the walk, because in the solver they would come from
    the impairment plan, which already searches over exactly those. The
    walk's job is to *check* an assignment, not to guess one.
    """

    def replay(self, games=40, nights=3):
        for seed in range(games):
            rng = random.Random(seed)
            deal, _heard = simulate.play(9, rng, nights=nights)
            for night in range(2, nights + 1):
                hidden = {}
                if deal.poisoned.get(night) is not None:
                    hidden[("poisoner", night)] = deal.poisoned[night]
                phase = f"N{night}"
                died = deal.died_on(phase)
                demon = deal.demon_at(phase)
                kills = [p for p in died if p != demon]
                if kills:
                    hidden[("demon", night)] = kills[0]
                yield deal, night, hidden, died

    def test_the_walk_reproduces_the_deaths(self):
        for deal, night, hidden, died in self.replay():
            got = nightwalk.walk(deal, night, hidden)
            with self.subTest(night=night, roles=deal.roles):
                self.assertEqual(got.died, died)

    def test_and_it_knows_who_acted_in_what_order(self):
        """A Poisoner goes before a Demon, and both before an Acrobat."""
        from botc.catalogue import CHARACTERS
        roles = {0: "Poisoner", 1: "Imp", 2: "Acrobat", 3: "Chef"}
        order = nightwalk.slots(roles, 2)
        self.assertEqual([roles[s] for s in order],
                         ["Poisoner", "Imp", "Acrobat"])
        self.assertEqual(roles[order[0]], "Poisoner")


class TheGoonTakesTheFirstAlignment(SolverTest):
    """The case that made the walk necessary.

    **The first player to choose the Goon tonight is drunk, and the Goon
    becomes their alignment.** A Sailor acts at slot 4 and a Poisoner at
    7, so if both choose the Goon it ends the night *good* — and if only
    the Poisoner does, it ends *evil*.

    Order decides an alignment here, not merely whether an ability
    worked, which is why no arrangement of "who was droisoned" could ever
    express it. That is the whole argument for walking a night.
    """

    class Board:
        n = 5

        def __init__(self, roles):
            self.roles = roles

        def role_at(self, seat, _phase):
            return self.roles[seat]

        def side_at(self, seat, _phase):
            from botc.roles import is_evil
            return "evil" if is_evil(self.roles[seat]) else "good"

        def alive_at(self, _phase):
            return set(range(self.n))

    def board(self):
        return self.Board(["Goon", "Sailor", "Poisoner", "Imp", "Chef"])

    def test_a_sailor_first_leaves_it_good(self):
        got = nightwalk.walk(self.board(), 2, {
            ("sailor", 2): 0, ("poisoner", 2): 0, ("demon", 2): 4})
        self.assertEqual(got.sides[0], "good")

    def test_a_poisoner_alone_turns_it_evil(self):
        got = nightwalk.walk(self.board(), 2, {
            ("poisoner", 2): 0, ("demon", 2): 4})
        self.assertEqual(got.sides[0], "evil")

    def test_whoever_chose_first_is_the_one_drunked(self):
        got = nightwalk.walk(self.board(), 2, {
            ("sailor", 2): 0, ("poisoner", 2): 0, ("demon", 2): 4})
        drunked = [entry[2] for entry in got.log if entry[1] == "droisoned"
                   and entry[3] == "Goon"]
        self.assertEqual(drunked, [1], "the Sailor, not the Poisoner")

    def test_and_the_order_is_what_decides_it(self):
        """Stated as a fact about the data rather than the walk, because
        if the slots ever changed the two tests above would still pass
        while meaning something else."""
        from botc.catalogue import CHARACTERS
        self.assertLess(CHARACTERS["Sailor"].other_night,
                        CHARACTERS["Poisoner"].other_night)


if __name__ == "__main__":
    unittest.main()


class OrderDecidesTheOutcome(SolverTest):
    """Cases where *when* a character acts changes what happens.

    Each of these is a thing the three-pass design cannot express,
    because it needs one character to see what an earlier one did.
    """

    class Board:
        def __init__(self, roles):
            self.roles = roles
            self.n = len(roles)

        def role_at(self, seat, _phase):
            return self.roles[seat]

        def side_at(self, seat, _phase):
            from botc.roles import is_evil
            return "evil" if is_evil(self.roles[seat]) else "good"

        def alive_at(self, _phase):
            return set(range(self.n))

    def test_a_monk_guards_before_the_demon_kills(self):
        """The Monk acts at 12 and every Demon at 24 or later, which is
        what makes the guard mean anything: the Demon arrives and finds
        the seat already protected."""
        board = self.Board(["Monk", "Chef", "Poisoner", "Imp", "Empath"])
        guarded = nightwalk.walk(board, 2, {("monk", 2): 1,
                                            ("demon", 2): 1})
        self.assertEqual(guarded.died, set())
        elsewhere = nightwalk.walk(board, 2, {("monk", 2): 4,
                                              ("demon", 2): 1})
        self.assertEqual(elsewhere.died, {1})

    def test_a_snake_charmer_swaps_before_the_demon_kills(self):
        """It acts at 11, so the swap happens first — and the seat that
        kills afterwards is the charmer's, now holding the Demon."""
        board = self.Board(["SnakeCharmer", "Chef", "Poisoner", "Imp",
                            "Empath"])
        got = nightwalk.walk(board, 2, {("snakecharmer", 2): 3})
        self.assertEqual(got.roles[0], "Imp")
        self.assertEqual(got.sides[0], "evil")
        self.assertEqual(got.roles[3], "SnakeCharmer")
        self.assertEqual(got.sides[3], "good")

    def test_and_the_new_snake_charmer_is_poisoned(self):
        board = self.Board(["SnakeCharmer", "Chef", "Poisoner", "Imp",
                            "Empath"])
        got = nightwalk.walk(board, 2, {("snakecharmer", 2): 3})
        self.assertIn(3, got.droisoned)

    def test_a_philosopher_drunks_whoever_really_has_it(self):
        """It acts at 2, before almost everything — so the seat it
        drunks may still have to act tonight, and will not."""
        board = self.Board(["Philosopher", "Empath", "Poisoner", "Imp",
                            "Chef"])
        # Keyed by seat, because a table can hold more than one
        # Philosopher and one key per night could only ever name one.
        got = nightwalk.walk(board, 2, {("philosopher", 2): {0: "Empath"}})
        self.assertIn(1, got.droisoned)

    def test_a_soldier_survives_the_demon(self):
        board = self.Board(["Soldier", "Chef", "Poisoner", "Imp", "Empath"])
        got = nightwalk.walk(board, 2, {("demon", 2): 0})
        self.assertEqual(got.died, set())

    def test_but_not_a_droisoned_one(self):
        """Which the walk gets for free, because the Poisoner acts at 7
        and the Demon at 24."""
        board = self.Board(["Soldier", "Chef", "Poisoner", "Imp", "Empath"])
        got = nightwalk.walk(board, 2, {("poisoner", 2): 0,
                                        ("demon", 2): 0})
        self.assertEqual(got.died, {0})


class EveryScriptReplays(SolverTest):
    """All three published scripts, every night, reproduced.

    The hidden choices are handed over the way the impairment plan would
    hand them over in the solver: where the Poisoner went, what the Demon
    aimed at, which seat's Pukka poison came due, what the Gambler
    guessed. The walk checks an assignment; it does not invent one.
    """

    def nights(self, script, games=30):
        """Every night of a played game, with what the walk must be told.

        The hidden inputs come from `nightwalk.hidden_from`, which is the
        single place that knows them. It used to be assembled here, and
        every ad-hoc comparison elsewhere assembled its own — three of
        which silently under-informed the walk and looked like walk bugs.

        A new character is added there once and every caller gets it.
        """
        for seed in range(games):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3, script=script)
            for night in (2, 3):
                hidden = nightwalk.hidden_from(deal, night, heard)
                died = deal.died_on(f"N{night}")
                yield deal, night, hidden, died

    def check(self, script, name):
        for deal, night, hidden, died in self.nights(script):
            got = nightwalk.walk(deal, night, hidden)
            with self.subTest(script=name, night=night, roles=deal.roles):
                self.assertEqual(got.died, died)

    def test_trouble_brewing(self):
        self.check(None, "Trouble Brewing")

    def test_bad_moon_rising(self):
        from botc import scripts
        self.check(scripts.BAD_MOON_RISING, "Bad Moon Rising")

    def test_sects_and_violets(self):
        from botc import scripts
        self.check(scripts.SECTS_AND_VIOLETS, "Sects & Violets")


class AnAbilityIsJudgedWhenItActs(SolverTest):
    """And for the Goon that is *after* it has answered back.

    The first player to choose the Goon is drunk on the spot, so that
    very choice already fails: a Demon that picks it first kills nobody
    (the rulebook of the single-player game, confirmed at the table
    03.10.2026). A Goon does protect itself from the first Demon that
    picks it — once a night.

    This class said the opposite until then: "the choice is already
    made, so the kill still lands". That was read off the card, the walk
    was built to it, and the simulator never played the Goon to say
    otherwise.
    """

    class Board:
        def __init__(self, roles):
            self.roles = roles
            self.n = len(roles)

        def role_at(self, seat, _phase):
            return self.roles[seat]

        def side_at(self, seat, _phase):
            from botc.roles import is_evil
            return "evil" if is_evil(self.roles[seat]) else "good"

        def alive_at(self, _phase):
            return set(range(self.n))

    def test_a_demon_that_picks_the_goon_first_does_not_kill_it(self):
        board = self.Board(["Goon", "Chef", "Empath", "Imp", "Saint"])
        got = nightwalk.walk(board, 2, {("demon", 2): [0]})
        self.assertEqual(got.died, set())

    def test_and_is_drunk_from_then_on(self):
        board = self.Board(["Goon", "Chef", "Empath", "Imp", "Saint"])
        got = nightwalk.walk(board, 2, {("demon", 2): [0]})
        self.assertIn(3, got.droisoned)

    def test_but_a_demon_droisoned_beforehand_kills_nobody(self):
        """The Poisoner acts at 7 and the Demon at 24, so this one is
        settled before the Demon ever chooses."""
        board = self.Board(["Goon", "Chef", "Poisoner", "Imp", "Saint"])
        got = nightwalk.walk(board, 2, {("poisoner", 2): 3,
                                        ("demon", 2): [1]})
        self.assertEqual(got.died, set())


class ReadingsAreTakenAtTheirOwnSlot(SolverTest):
    """Information is read off the board *as it stands then*.

    An Undertaker at 55 sees who was executed; an Empath at 53 counts
    neighbours who may have died at 24; a Ravenkeeper at 52 learns a
    character a Pit-Hag may have changed at 16. None of those can be
    answered before the night has been walked to their slot, which is
    why the readings come in a second pass over the same order.
    """

    class Board:
        def __init__(self, roles):
            self.roles = roles
            self.n = len(roles)

        def role_at(self, seat, _phase):
            return self.roles[seat]

        def side_at(self, seat, _phase):
            from botc.roles import is_evil
            return "evil" if is_evil(self.roles[seat]) else "good"

        def alive_at(self, _phase):
            return set(range(self.n))

    def test_an_empath_counts_after_the_demon_has_killed(self):
        """The Demon acts at 24 and the Empath reads at 53, so a
        neighbour who died tonight is not a neighbour any more."""
        board = self.Board(["Empath", "Poisoner", "Imp", "Chef", "Saint"])
        got = nightwalk.walk(board, 2, {("demon", 2): [3]})
        reading = [r for r in got.readings if r[2] == "Empath"]
        self.assertTrue(reading)
        self.assertNotIn(3, got.alive)

    def test_and_a_droisoned_seat_reads_nothing(self):
        board = self.Board(["Empath", "Poisoner", "Imp", "Chef", "Saint"])
        got = nightwalk.walk(board, 2, {("poisoner", 2): 0})
        self.assertEqual([r for r in got.readings if r[2] == "Empath"], [])

    def test_the_walk_agrees_with_the_simulator(self):
        """Not just on who died — on what was learned."""
        agree = 0
        for seed in range(40):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3)
            for night in (2, 3):
                hidden = {}
                if deal.poisoned.get(night) is not None:
                    hidden[("poisoner", night)] = deal.poisoned[night]
                if deal.demon_aimed.get(night):
                    hidden[("demon", night)] = deal.demon_aimed[night]
                got = nightwalk.walk(deal, night, hidden)
                walked = {(r[1], r[2]): r[3] for r in got.readings}
                for row in heard:
                    if row.night != night:
                        continue
                    if type(row).__name__ != "Empath":
                        continue
                    mine = walked.get((row.player, "Empath"))
                    if mine is None:
                        continue
                    with self.subTest(seed=seed, night=night):
                        self.assertEqual(mine, row.count)
                    agree += 1
        self.assertGreater(agree, 10, "no Empath readings to compare")


class TheWalkAgreesWithTheSimulator(SolverTest):
    """Two independent derivations, compared on every reading.

    The strongest test here: the simulator works out what a character
    learns while playing, the walk works it out from the night as it
    stands at that character's slot, and neither knows about the other.

    **Three filters, and they matter.** A Vortox falsifies the reading,
    so the simulator records a lie. A droisoned seat is told whatever the
    Storyteller likes. Neither is a disagreement, and comparing them
    without excluding both is meaningless — the Oracle looked like 13 of
    25 until they were taken out.
    """

    def compare(self, kind, field, script=None, games=60, nights=(2, 3)):
        from botc import scripts as _s
        agree = 0
        for seed in range(games):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3, script=script)
            if "Vortox" in deal.roles:
                continue                  # the reading is a deliberate lie
            for night in nights:
                # Everything the walk has to be told, from the one place
                # that knows it — assembled by hand here, it missed a Fang
                # Gu's jump and counted the old Fang Gu alive (29.09.2026).
                hidden = nightwalk.hidden_from(deal, night, heard)
                got = nightwalk.walk(deal, night, hidden)
                walked = {(r[1], r[2]): r[3] for r in got.readings}
                for row in heard:
                    if row.night != night or type(row).__name__ != kind:
                        continue
                    if not deal.working(row.player, night):
                        continue          # told anything, so nothing to check
                    role = kind.replace("Info", "")
                    mine = walked.get((row.player, role))
                    if mine is None:
                        continue
                    with self.subTest(seed=seed, night=night, reading=kind):
                        self.assertEqual(mine, getattr(row, field))
                    agree += 1
        return agree

    def test_the_empath_counts_the_same(self):
        """It reads at 53 and the Demon kills at 24, so a neighbour who
        died tonight is not a neighbour any more."""
        self.assertGreater(self.compare("Empath", "count"), 10)

    def test_the_chef_counts_the_same(self):
        self.assertGreater(self.compare("Chef", "count", nights=(1,)), 10)

    def test_the_undertaker_sees_the_same_seat(self):
        self.assertGreater(self.compare("Undertaker", "target"), 10)

    def test_the_oracle_counts_the_same(self):
        """This one found a bug in the simulator: the Oracle reads at 59
        and the Demon kills at 24, so tonight's victim is dead when it
        counts. The simulator was using the state at the *start* of the
        night, which is a different question."""
        from botc import scripts
        self.assertGreater(
            self.compare("OracleInfo", "count", scripts.SECTS_AND_VIOLETS), 10)


class TheDeadStopHearingExceptOne(SolverTest):
    """A Ravenkeeper reads *because* it died.

    `working` requires being alive, so asking it before the exemption
    rejected the one character that has to be dead to read at all — and
    no Ravenkeeper reading was ever taken. Nothing failed; the comparison
    simply had nothing to compare, which is the quieter kind of wrong.
    """

    def test_a_ravenkeeper_that_died_tonight_still_reads(self):
        found = 0
        for seed in range(80):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3)
            for night in (2, 3):
                rows = [h for h in heard
                        if type(h).__name__ == "Ravenkeeper"
                        and h.night == night]
                if not rows:
                    continue
                hidden = {"red_herring": deal.red_herring,
                          ("asked", night): {rows[0].player: rows[0].target}}
                if deal.poisoned.get(night) is not None:
                    hidden[("poisoner", night)] = deal.poisoned[night]
                if deal.demon_aimed.get(night):
                    hidden[("demon", night)] = deal.demon_aimed[night]
                got = nightwalk.walk(deal, night, hidden)
                mine = {(r[1], r[2]): r[3] for r in got.readings}
                for row in rows:
                    if not deal.working(row.player, night):
                        continue
                    answer = mine.get((row.player, "Ravenkeeper"))
                    if answer is None:
                        continue
                    with self.subTest(seed=seed, night=night):
                        self.assertEqual(answer, row.role)
                    found += 1
        self.assertGreater(found, 0, "no Ravenkeeper read at all")

    def test_a_fortune_teller_reads_after_the_demon_kills(self):
        """It reads at 54 and a Demon kills at 24, so a seat taken
        tonight is dead when it asks — and a dead Demon still registers
        as one."""
        agree = 0
        for seed in range(60):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3)
            for night in (2, 3):
                rows = [h for h in heard
                        if type(h).__name__ == "FortuneTeller"
                        and h.night == night]
                if not rows:
                    continue
                hidden = {"red_herring": deal.red_herring,
                          ("asked", night): {rows[0].player: (rows[0].a,
                                                              rows[0].b)}}
                if deal.poisoned.get(night) is not None:
                    hidden[("poisoner", night)] = deal.poisoned[night]
                if deal.demon_aimed.get(night):
                    hidden[("demon", night)] = deal.demon_aimed[night]
                got = nightwalk.walk(deal, night, hidden)
                mine = {(r[1], r[2]): r[3] for r in got.readings}
                for row in rows:
                    if not deal.working(row.player, night):
                        continue
                    answer = mine.get((row.player, "FortuneTeller"))
                    if answer is None:
                        continue
                    with self.subTest(seed=seed, night=night):
                        self.assertEqual(answer, row.yes)
                    agree += 1
        self.assertGreater(agree, 10)


class TheFirstNightPairs(SolverTest):
    """A Washerwoman, a Librarian, an Investigator.

    Two players and a character, one of whom is it. The *shown* character
    is the Storyteller's choice and misregistration is legal — a Spy
    shows as a Townsfolk, a Recluse as a Minion — so what the walk checks
    is which of the pair **could** have been shown, not which was.

    That is the honest limit of what a replay can say about these. The
    walk's contribution is *when*: the pair is drawn on the first night,
    from the board as it stood then.
    """

    def rows(self, kind, games=80):
        for seed in range(games):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3)
            found = [h for h in heard
                     if type(h).__name__ == kind and h.night == 1
                     and h.a is not None]
            if not found:
                continue
            hidden = {("asked", 1): {h.player: (h.a, h.b) for h in found}}
            if deal.poisoned.get(1) is not None:
                hidden[("poisoner", 1)] = deal.poisoned[1]
            got = nightwalk.walk(deal, 1, hidden)
            mine = {(r[1], r[2]): r[3] for r in got.readings}
            for row in found:
                if not deal.working(row.player, 1):
                    continue
                answer = mine.get((row.player, kind))
                if answer is None:
                    continue
                yield deal, row, answer

    def test_the_seat_really_shown_is_among_the_candidates(self):
        checked = 0
        for deal, row, answer in self.rows("Washerwoman"):
            shown = [p for p in (row.a, row.b)
                     if deal.role_at(p, "N1") == row.role]
            if not shown:
                continue
            with self.subTest(seat=row.player):
                self.assertIn(shown[0], answer)
            checked += 1
        self.assertGreater(checked, 5, "no washerwoman readings compared")

    def test_and_for_the_investigator(self):
        checked = 0
        for deal, row, answer in self.rows("Investigator"):
            shown = [p for p in (row.a, row.b)
                     if deal.role_at(p, "N1") == row.role]
            if not shown:
                continue
            with self.subTest(seat=row.player):
                self.assertIn(shown[0], answer)
            checked += 1
        self.assertGreater(checked, 5, "no investigator readings compared")

    def test_every_reading_has_at_least_one_candidate(self):
        """A pair where neither could show as the named team is not a
        legal reading, and the walk would say so by returning nothing."""
        checked = 0
        for _deal, row, answer in self.rows("Investigator"):
            with self.subTest(seat=row.player):
                self.assertTrue(answer, "no seat could show as a minion")
            checked += 1
        self.assertGreater(checked, 5)


class TheDreamerReadsWhatIsThereNow(SolverTest):
    """One good character and one evil, and one of them is true.

    It reads at 56, so a seat a Pit-Hag changed at 16 is read as what it
    holds *now* — which is the difference between a replay and a lookup.
    """

    def test_one_of_the_two_is_what_the_seat_holds(self):
        from botc import scripts
        checked = 0
        for seed in range(80):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3,
                                        script=scripts.SECTS_AND_VIOLETS)
            if "Vortox" in deal.roles:
                continue              # the reading is a deliberate lie
            for night in (2, 3):
                rows = [h for h in heard
                        if type(h).__name__ == "DreamerInfo"
                        and h.night == night]
                if not rows:
                    continue
                # Everything `hidden_from` knows, and who the Dreamer
                # asked about. Assembled by hand here it went stale three
                # times: no Fang Gu jump, no Pit-Hag, no Snake Charmer
                # swap — each found when a new deal happened to need it.
                hidden = nightwalk.hidden_from(deal, night, heard)
                hidden[("asked", night)] = {h.player: h.target
                                            for h in rows}
                got = nightwalk.walk(deal, night, hidden)
                mine = {(r[1], r[2]): r[3] for r in got.readings}
                for row in rows:
                    if not deal.working(row.player, night):
                        continue
                    answer = mine.get((row.player, "Dreamer"))
                    if answer is None:
                        continue
                    with self.subTest(seed=seed, night=night):
                        self.assertIn(answer,
                                      (row.good_role, row.evil_role))
                    checked += 1
        self.assertGreater(checked, 10, "no dreamer readings compared")


class TheJugglerCountsYesterdaysGuesses(SolverTest):
    """It guessed publicly in daylight and is answered at 61.

    What matters is what each seat held *then*, which is why the guesses
    come in with the hidden choices rather than being derived.
    """

    def test_it_counts_the_same_as_the_simulator(self):
        from botc import scripts
        checked = 0
        for seed in range(80):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3,
                                        script=scripts.SECTS_AND_VIOLETS)
            if "Vortox" in deal.roles:
                continue
            for night in (2, 3):
                rows = [h for h in heard
                        if type(h).__name__ == "JugglerInfo"
                        and h.night == night]
                if not rows:
                    continue
                hidden = {
                    ("asked", night): {
                        h.player: tuple((g["player"], g["role"])
                                        for g in h.guesses) for h in rows},
                    "gained": dict(deal.philosophies)}
                if deal.poisoned.get(night) is not None:
                    hidden[("poisoner", night)] = deal.poisoned[night]
                if deal.demon_aimed.get(night):
                    hidden[("demon", night)] = deal.demon_aimed[night]
                got = nightwalk.walk(deal, night, hidden)
                mine = {(r[1], r[2]): r[3] for r in got.readings}
                for row in rows:
                    if not deal.working(row.player, night):
                        continue
                    answer = mine.get((row.player, "Juggler"))
                    if answer is None:
                        continue
                    with self.subTest(seed=seed, night=night):
                        self.assertEqual(answer, row.count)
                    checked += 1
        self.assertGreater(checked, 5, "no juggler readings compared")


class SomeReadingsCannotBeDerived(SolverTest):
    """A Savant and an Artist are told free text the Storyteller invents.

    There is nothing for a replay to work out — the walk can say *when*
    they were told and nothing about *what*. Listing them with a
    derivation that returns None would look like coverage and be none,
    which is the mistake the Ravenkeeper taught.

    The solver agrees: `weighed` is False for both, so they are kept
    rather than solved.
    """

    def test_the_walk_does_not_pretend_to_derive_them(self):
        import nightwalk as walk
        source = open(walk.__file__).read()
        self.assertIn("the Savant and the Artist are deliberately absent",
                      source)

    def test_and_the_solver_does_not_weigh_them(self):
        from botc.info import GameState, SavantInfo, ArtistInfo
        state = GameState(n_players=9, claims={})
        for row in (SavantInfo(1, 0, first="a", second="b"),
                    ArtistInfo(1, 0, question="q", answer=True)):
            with self.subTest(reading=type(row).__name__):
                self.assertFalse(row.weighed(state))


class TheWalkSaysWhenItWasNotTold(SolverTest):
    """Being under-informed used to look exactly like being wrong.

    Three comparisons failed because a probe forgot a hidden input — a
    Gambler's guess, a Pukka's poison coming due — and each time the walk
    refused a kill it had no way to know about, and the failure pointed
    at the walk.

    So the walk records `untold`: characters on the board that always
    act, are alive and working, and that it was told nothing about. A
    comparison can refuse to draw any conclusion until it is empty.
    """

    def test_a_fully_informed_night_says_nothing(self):
        """The standing gate. If this fires, either a character has
        started acting and `hidden_from` has not learned it, or a
        character is dealt and never acting at all."""
        from botc import scripts
        flagged = []
        for script in (None, scripts.BAD_MOON_RISING,
                       scripts.SECTS_AND_VIOLETS):
            for seed in range(30):
                rng = random.Random(seed)
                deal, heard = simulate.play(9, rng, nights=3, script=script)
                for night in (2, 3):
                    # A game a Mastermind's extra day finished has no
                    # night after it, and a night nobody played has
                    # nothing to be told about.
                    if deal.game_ends_after is not None \
                            and night > deal.game_ends_after:
                        continue
                    got = nightwalk.walk(
                        deal, night,
                        nightwalk.hidden_from(deal, night, heard))
                    if got.untold:
                        flagged.append((seed, night, sorted(got.untold)))
        self.assertEqual(flagged[:3], [], f"{len(flagged)} nights flagged")

    def test_and_an_empty_one_says_plenty(self):
        """The warning has to be capable of firing, or it says nothing.

        Needs a board that actually holds one of the characters the
        warning is about. This used a fixed seed and passed for the wrong
        reason: the check ran *before* the night, so every seat looked
        sober and even a board with nothing to warn about produced one.
        Moving the check to the end of the night — which was the right
        fix — left the fixture with no Poisoner and no Monk on it.
        """
        wanted = set(nightwalk.ALWAYS_ACTS)
        for seed in range(40):
            rng = random.Random(seed)
            deal, _heard = simulate.play(9, rng, nights=3)
            if not wanted & set(deal.roles):
                continue
            got = nightwalk.walk(deal, 2, {})
            if got.untold:
                return
        self.fail("the warning never fires on any board")

    def test_a_character_that_arrived_mid_game_is_not_counted(self):
        """A Snake Charmer swap leaves the old Demon holding the
        character from the day after, and it has no row for that night —
        it was not a Snake Charmer when the readings were taken. That
        silence is real rather than a missing input."""
        from botc import scripts
        for seed in range(40):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3,
                                        script=scripts.SECTS_AND_VIOLETS)
            swapped = [p for p in range(9)
                       if deal.role_at(p, "N3") == "SnakeCharmer"
                       and deal.roles[p] != "SnakeCharmer"]
            if not swapped:
                continue
            got = nightwalk.walk(deal, 3,
                                 nightwalk.hidden_from(deal, 3, heard))
            self.assertNotIn("SnakeCharmer", got.untold)
            return
        self.skipTest("no mid-game Snake Charmer in that range")


class TheWalkRunsOverASolverWorld(SolverTest):
    """The seam where the walk meets the solver.

    `best_story` asks `possible_timelines` for chains and scores each with
    `_explain`. The walk belongs there — as a *check* on a chain before it
    is scored, replaying the night to see whether the record comes out.

    This is the step none of the risk had been faced on: everything up to
    it was an experiment in `tests/` that nothing in `botc/` depended on.
    """

    def boards(self, script=None, games=30):
        import botc.solver as S
        from botc.info import GameState
        from botc.worlds import World, Timeline
        import claims as C
        for seed in range(games):
            rng = random.Random(seed)
            deal, heard = simulate.play(9, rng, nights=3, script=script)
            claims, wakes, _notes = C.claims_for(deal, rng, script=script)
            state = GameState(n_players=9, script=script, claims=claims,
                              wakes=wakes, **deal.record(),
                              infos=list(heard))
            world = World(tuple(deal.roles), tuple(deal.believes))
            # A Barber that hid and died: the swap is not looked for (a
            # table ruling, 29.09.2026), so the view the solver would
            # score is knowingly not the game that was played.
            claimed = S.barber_claimants(state)
            if any(deal.role_at(p, at) == "Barber" and p not in claimed
                   for p, at in deal.deaths.items()):
                continue
            chains = S.possible_timelines(world, state)
            # The telling that is the game played, where the solver has
            # it. Taking the first one was enough until a claimed Barber's
            # swap put several on offer: the first is the cheapest, and
            # the cheapest is the one with no swap in it.
            phases = [f"{half}{k}" for k in (1, 2, 3) for half in "NE"]
            def played(chain):
                view = Timeline(world, chain) if chain else world
                return all(view.role_at(p, at) == deal.role_at(p, at)
                           for p in range(deal.n) for at in phases)
            chain = next((c for c, _cost in chains if played(c)),
                         chains[0][0] if chains else ())
            view = Timeline(world, chain) if chain else world
            yield deal, heard, nightwalk.AsBoard(view, state)

    def test_the_adapter_needs_almost_nothing(self):
        """The walk asks a deal four things and a world answers two
        already. That the adapter is this small is the encouraging part —
        the walk was written against a simulated game and wants almost
        nothing a solver world cannot say."""
        for _deal, _heard, board in self.boards(games=1):
            for name in ("n", "role_at", "side_at", "alive_at"):
                with self.subTest(needs=name):
                    self.assertTrue(hasattr(board, name))

    def test_it_replays_the_night_the_same_way(self):
        """Over the *view* the solver would score, not the bare world.

        A `World` carries no changes — it says who was dealt what, and a
        swap lives in the `Timeline` wrapped around it. Handing the world
        underneath made the walk start every night from the deal and miss
        everything since: 174 of 180 rather than all of them.
        """
        from botc import scripts
        checked = 0
        for script in (None, scripts.BAD_MOON_RISING,
                       scripts.SECTS_AND_VIOLETS):
            for deal, heard, board in self.boards(script):
                for night in (2, 3):
                    got = nightwalk.walk(
                        board, night,
                        nightwalk.hidden_from(deal, night, heard))
                    died = deal.died_on(f"N{night}")
                    with self.subTest(night=night, roles=deal.roles):
                        self.assertEqual(got.died, died)
                    checked += 1
        self.assertGreater(checked, 100)
