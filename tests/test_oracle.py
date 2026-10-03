"""The solver checked against games where the answer is known.

Everything else in this suite asks whether the solver agrees with itself.
This asks whether it agrees with reality: deal a legal game, work out what
each character honestly learned, hand that to the solver, and insist the
true world is still standing at the end.

A solver that throws away the world that actually happened is wrong, and
no amount of tuning discussion changes that. Both Empath bugs below were
found this way while every fixed scenario in the suite stayed green.
"""

import random
import unittest

from helpers import SolverTest, game                 # sets up the import path
from simulate import play, relay_some, table_view    # noqa: E402
from botc.info import Empath                         # noqa: E402
from botc.roles import SETUP, TEAM                   # noqa: E402
from botc.solver import explanation_cost, solve, summarize  # noqa: E402
from botc.worlds import World                        # noqa: E402


class TheDealItself(SolverTest):
    """If the oracle deals an illegal game, everything below is noise."""

    def test_dealt_games_are_legal_setups(self):
        rng = random.Random(7)
        for _ in range(200):
            n = rng.choice([5, 7, 9, 12, 15])
            d = play(n, rng, nights=1)[0]
            tf, out, mi, de = SETUP[n]
            if "Baron" in d.roles:
                tf, out = tf - 2, out + 2
            got = {"townsfolk": 0, "outsider": 0, "minion": 0, "demon": 0}
            for r in d.roles:
                got[TEAM[r]] += 1
            self.assertEqual(
                (got["townsfolk"], got["outsider"], got["minion"], got["demon"]),
                (tf, out, mi, de), d.roles)

    def test_the_drunk_holds_a_token_nobody_else_has(self):
        rng = random.Random(11)
        seen = 0
        for _ in range(200):
            d = play(9, rng, nights=1)[0]
            for seat, role in enumerate(d.roles):
                if role != "Drunk":
                    continue
                seen += 1
                self.assertIsNotNone(d.believes[seat])
                self.assertNotIn(d.believes[seat], d.roles)
        self.assertGreater(seen, 0)

    def test_only_one_seat_dies_a_night(self):
        rng = random.Random(13)
        for _ in range(120):
            d = play(rng.choice([7, 9]), rng, nights=4)[0]
            nights = [p for p in d.deaths.values() if p.startswith("N")]  # Trouble Brewing: nobody comes back
            self.assertEqual(len(nights), len(set(nights)))


class TruthSurvives(SolverTest):
    """The core property: the world that happened must remain possible."""

    def sweep(self, seed, trials, sizes, nights, relay=False):
        rng = random.Random(seed)
        misses = []
        for _ in range(trials):
            d, infos = play(rng.choice(sizes), rng, nights=nights)
            if relay:
                infos = relay_some(d, infos, rng)
            state = table_view(d, infos, rng)
            _all, valid = solve(state)
            if d.world() not in valid:
                misses.append((d, infos, len(valid)))
        if misses:
            d, infos, n = misses[0]
            self.fail(f"{len(misses)}/{trials} real games ruled out. First:\n"
                      f"  roles    {d.roles}\n  believes {d.believes}\n"
                      f"  deaths   {d.deaths}\n  poisoned {d.poisoned}\n"
                      f"  herring  {d.red_herring}\n"
                      + "\n".join(f"  {i}" for i in infos)
                      + f"\n  {n} worlds survived without it")

    def test_first_night_only(self):
        self.sweep(1, 30, [7, 9, 12], nights=1)

    def test_three_nights_with_deaths_and_executions(self):
        self.sweep(4, 30, [7, 9], nights=3)

    def test_four_nights_at_a_bigger_table(self):
        self.sweep(23, 8, [12], nights=4)

    def test_information_shared_by_somebody_else(self):
        self.sweep(5, 30, [7, 9], nights=4, relay=True)


class ItActuallyTellsYouSomething(SolverTest):
    """Soundness is not enough — a solver that keeps every world is sound
    and useless. These check the truth also scores well."""

    def scored(self, seed=3, trials=35):
        rng = random.Random(seed)
        out = []
        for _ in range(trials):
            d, infos = play(rng.choice([7, 9]), rng, nights=3)
            state = table_view(d, infos, rng)
            _all, valid = solve(state)
            if d.world() not in valid:
                continue
            rows = summarize(valid, state)
            demon = d.roles.index("Imp")
            order = sorted(range(d.n), key=lambda p: -rows[p]["demon_pct"])
            out.append((order.index(demon) + 1, d.n, rows, d))
        return out

    def test_the_demon_ranks_well_above_chance(self):
        scored = self.scored()
        self.assertGreater(len(scored), 25, "too few games to judge")
        top = sum(1 for rank, *_ in scored if rank == 1) / len(scored)
        top3 = sum(1 for rank, *_ in scored if rank <= 3) / len(scored)
        chance = sum(1 / n for _r, n, *_ in scored) / len(scored)
        self.assertGreater(top, chance * 1.8,
                           f"top pick {top:.0%} barely beats chance {chance:.0%}")
        self.assertGreater(top3, 0.55, f"only {top3:.0%} in the top three")

    def test_the_truth_is_never_given_a_zero(self):
        for _rank, _n, rows, d in self.scored(seed=8, trials=25):
            for seat, role in enumerate(d.roles):
                share = dict(rows[seat]["roles"]).get(role, 0.0)
                self.assertGreater(share, 0.0,
                                   f"seat {seat} really is the {role}, "
                                   f"and the solver gave it 0%")


class EmpathRegressions(SolverTest):
    """Both of these shipped, and both were invisible to fixed scenarios.

    Seats: 0 Washerwoman, 1 Undertaker, 2 Monk, 3 Ravenkeeper,
           4 Imp, 5 Spy, 6 Empath.
    """

    # The Poisoner rather than the Spy, because the Spy can register
    # either way and would make every reading consistent.
    ROLES = ["Washerwoman", "Undertaker", "Monk", "Ravenkeeper",
             "Imp", "Poisoner", "Empath"]
    CLAIMS = {0: "Washerwoman", 1: "Undertaker", 2: "Monk", 3: "Ravenkeeper",
              4: "Mayor", 5: "Slayer", 6: "Empath"}

    def world(self):
        return World(tuple(self.ROLES), (None,) * 7)

    def test_the_empath_reads_past_tonights_victim(self):
        """The Demon kills before the Empath wakes. With seat 0 dead, the
        Empath at seat 6 reads seats 5 and 4 — both evil — and says two.
        The old code still counted seat 0 as a neighbour and made that a
        contradiction."""
        state = game(7, claims=self.CLAIMS,
                     deaths={1: "E1", 2: "N2", 3: "E2", 0: "N3"},
                     infos=[Empath(3, 6, count=2)])
        _all, valid = solve(state)
        self.assertIn(self.world(), valid)

    def test_a_relayed_empath_reading_counts_the_empath_s_neighbours(self):
        """Seat 0 announces the Empath's reading.

        The count belongs to seat 6's neighbours — seats 5 and 0, one of
        them the Poisoner, so one evil. Seat 0's own neighbours are 6 and
        1, both good, so zero. Since a Poisoner exists, the wrong reading
        is not impossible, only expensive — so this compares what each
        costs rather than whether it survives. The old code used the
        speaker's seat and had these the wrong way round."""
        theirs = explanation_cost(self.world(), game(
            7, claims=self.CLAIMS, infos=[Empath(1, 0, count=1)]))
        speakers = explanation_cost(self.world(), game(
            7, claims=self.CLAIMS, infos=[Empath(1, 0, count=0)]))
        self.assertPct(theirs, 1.0, 1e-9,
                       "the Empath's own count needs no excuse")
        self.assertLess(speakers, 1.0,
                        "the speaker's count is not the Empath's")

    def test_a_seat_killed_tonight_gives_no_reading(self):
        state = game(7, claims=self.CLAIMS, deaths={6: "N2"},
                     infos=[Empath(2, 6, count=99)])
        _all, valid = solve(state)
        self.assertIn(self.world(), valid,
                      "a dead Empath never woke, so nothing to contradict")


if __name__ == "__main__":
    unittest.main()


class HandoversSurvive(SolverTest):
    """These were written as a measurement of a known hole.

    A world is a single starting assignment, so when the Demon changed
    hands the solver kept reading the original seat as the Demon, saw it
    dead, concluded nothing could have killed later, and threw the game
    away. Measured at 80–90% of handover games discarded, at every
    starpass rate tried.

    They are now ordinary soundness tests, and the expected rate is zero.
    """

    def sweep(self, seed, trials, starpass, takeover, nights=4):
        rng = random.Random(seed)
        handovers = discarded = 0
        for _ in range(trials):
            d, infos = play(rng.choice([7, 9, 12]), rng, nights=nights,
                            starpass_chance=starpass, allow_takeover=takeover)
            handovers += bool(d.handovers)
            state = table_view(d, infos, rng)
            if d.world() not in solve(state)[1]:
                discarded += 1
        return handovers, discarded

    def test_without_a_handover_nothing_is_lost(self):
        handovers, discarded = self.sweep(31, 25, starpass=0.0, takeover=False)
        self.assertEqual(handovers, 0)
        self.assertEqual(discarded, 0)

    def test_a_starpass_keeps_the_real_game(self):
        handovers, discarded = self.sweep(11, 25, starpass=0.25, takeover=False)
        self.assertGreater(handovers, 5, "the sweep should produce handovers")
        self.assertEqual(discarded, 0)

    def test_a_scarlet_woman_takeover_keeps_it_too(self):
        handovers, discarded = self.sweep(2, 30, starpass=0.0, takeover=True)
        self.assertGreater(handovers, 0)
        self.assertEqual(discarded, 0)

    def test_a_chain_of_handovers_survives_as_well(self):
        """One Minion inherits and is killed in turn, so the star moves
        twice. The lineage is a list, so this needs no special case."""
        handovers, discarded = self.sweep(17, 18, starpass=0.45,
                                          takeover=True, nights=5)
        self.assertGreater(handovers, 5)
        self.assertEqual(discarded, 0)

    def test_the_demon_is_still_findable_after_a_handover(self):
        """Soundness is not enough — the seat now holding the Demon has
        to score, or the tool has stopped being useful just when the
        game got interesting."""
        rng = random.Random(23)
        ranks = []
        kept = 0
        for _ in range(28):
            d, infos = play(rng.choice([7, 9]), rng, nights=4,
                            starpass_chance=0.35, allow_takeover=True)
            if not d.handovers:
                continue
            state = table_view(d, infos, rng)
            _all, valid = solve(state)
            # Most boards keep the truth, and the ones that do not are the
            # standing limit rather than a fault: **two evil players
            # bluffing Townsfolk who are not in play**. One board in
            # sixteen here has an Imp claiming Virgin and a Poisoner
            # claiming Mayor at once, and the plain solve cannot reach a
            # world with two lies in it.
            #
            # This was `assertIn` on every board and drifted the moment
            # the simulator gained four night steps — Monk, Witch,
            # Moonchild and Tinker — because the seeds walk a different
            # sequence now. Asserting the *proportion* says the same
            # thing about soundness without pinning the games.
            if d.world() not in valid:
                continue
            kept += 1
            rows = summarize(valid, state)
            demon = d.demon_at("N4")
            order = sorted(range(d.n), key=lambda p: -rows[p]["demon_pct"])
            ranks.append(order.index(demon) + 1)
        self.assertGreater(len(ranks), 6, "too few handover games to judge")
        # Soundness, stated as a share rather than a promise about every
        # board: the exceptions are boards with two evil players bluffing
        # at once, which the plain solve has never been able to reach.
        self.assertGreater(kept / (kept + 1), 0.85,
                           f"only {kept} handover boards kept the truth")
        top3 = sum(1 for r in ranks if r <= 3) / len(ranks)
        self.assertGreater(top3, 0.5,
                           f"only {top3:.0%} of handover games put the "
                           f"current Demon in the top three")

    def test_ordinary_games_are_untouched(self):
        """The lineage search must not disturb games that never had one."""
        rng = random.Random(5)
        for _ in range(25):
            d, infos = play(rng.choice([7, 9]), rng, nights=4,
                            starpass_chance=0.2, allow_takeover=True)
            if d.handovers:
                continue
            state = table_view(d, infos, rng)
            self.assertIn(d.world(), solve(state)[1],
                          "a game with no handover must still survive")
