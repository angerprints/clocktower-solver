"""The sampler, checked against the exact answer wherever both fit.

Sampling is only worth having if its numbers mean something. Two claims
have to hold: the estimate must converge on what an exhaustive count
would have said, and the margin printed beside it must actually cover the
error most of the time. Both are testable here because these scenarios
are small enough to compute both ways.
"""

import random
import statistics
import unittest

from helpers import SolverTest, game, spread          # sets up the import path
from botc.info import Chef, Empath, Washerwoman       # noqa: E402
from botc.solver import analyze, estimate, pilot_size  # noqa: E402
from botc.worlds import enumerate_worlds, sample_worlds  # noqa: E402


def walk(n, claims, dives=6000, seed=0, **kw):
    """Total weight and dead-end rate over a batch of walks."""
    rng = random.Random(seed)
    total = 0.0
    dead = 0
    for world, stands_for in sample_worlds(n, claims, dives=dives, rng=rng, **kw):
        if world is None:
            dead += 1
        total += stands_for
    return total / dives, dead / dives


class CountsComeOutRight(SolverTest):
    """The estimator is unbiased, so with enough walks it lands on the
    number an exhaustive count would have produced."""

    CASES = {
        "7 seats, all claimed": (7, None),
        "9 seats, all claimed": (9, None),
        "12 seats, all claimed": (12, None),
        "9 seats, three silent": (9, {i: r for i, r in enumerate(
            ["Washerwoman", "Librarian", "Investigator",
             "Chef", "Empath", "FortuneTeller"])}),
    }

    def test_the_estimate_lands_on_the_exact_count(self):
        for name, (n, claims) in self.CASES.items():
            with self.subTest(scenario=name):
                claims = spread(n) if claims is None else claims
                exact = len(enumerate_worlds(n, claims, max_worlds=10 ** 7))
                runs = [walk(n, claims, seed=s)[0] for s in range(3)]
                got = statistics.mean(runs)
                self.assertPct(100 * (got - exact) / exact, 0.0, 6.0,
                               f"{name}: exact {exact}, estimated {got:.0f}")

    def test_the_error_shrinks_as_the_walks_pile_up(self):
        """Averaged absolute error, not a standard deviation.

        Estimating a spread from a handful of runs is itself so noisy
        that the test flakes — which it did, reporting a *smaller* spread
        from 500 walks than from 7000. Mean error over more seeds is
        steady enough to assert on.
        """
        n, claims = 12, spread(12)
        exact = len(enumerate_worlds(n, claims, max_worlds=10 ** 7))

        def typical_error(dives, seeds=8):
            runs = [walk(n, claims, dives=dives, seed=s)[0] for s in range(seeds)]
            return statistics.mean(abs(r - exact) for r in runs) / exact

        few = typical_error(300)
        many = typical_error(5000)
        self.assertLess(many, few * 0.7,
                        f"more walks should mean a closer answer: "
                        f"{few:.3%} at 300 walks, {many:.3%} at 5000")

    def test_walks_that_reach_nothing_still_count(self):
        """Dropping dead ends instead of scoring them zero would quietly
        inflate every estimate."""
        _est, dead = walk(9, {i: r for i, r in enumerate(
            ["Washerwoman", "Librarian", "Investigator",
             "Chef", "Empath", "FortuneTeller"])})
        self.assertGreater(dead, 0.0, "this scenario should hit dead ends")
        exact = len(enumerate_worlds(9, {i: r for i, r in enumerate(
            ["Washerwoman", "Librarian", "Investigator",
             "Chef", "Empath", "FortuneTeller"])}, max_worlds=10 ** 7))
        got = statistics.mean(
            walk(9, {i: r for i, r in enumerate(
                ["Washerwoman", "Librarian", "Investigator",
                 "Chef", "Empath", "FortuneTeller"])}, seed=s)[0]
            for s in range(3))
        self.assertPct(100 * (got - exact) / exact, 0.0, 6.0)


class ProbabilitiesAgreeWithTheExactAnswer(SolverTest):

    SCENARIOS = {
        "quiet 9-seat table": lambda: game(9),
        "9 seats with information": lambda: game(9, infos=[
            Chef(1, 3, count=1), Empath(1, 4, count=1), Empath(2, 4, count=2)]),
        "9 seats, a death and a reading": lambda: game(9, deaths={3: "N2"}, infos=[
            Empath(1, 4, count=1), Washerwoman(1, 0, a=3, b=8, role="Monk")]),
    }

    def compare(self, build, dives=7000, seed=0):
        exact = analyze(build())
        sampled = estimate(build(), dives=dives, rng=random.Random(seed))
        return exact, sampled

    def test_every_seat_lands_close_to_the_truth(self):
        for name, build in self.SCENARIOS.items():
            with self.subTest(scenario=name):
                exact, sampled = self.compare(build)
                self.assertFalse(exact["sampled"], "this one should be exact")
                worst = max(abs(a["evil_pct"] - b["evil_pct"])
                            for a, b in zip(exact["rows"], sampled["rows"]))
                self.assertLess(worst, 5.0, f"{name}: worst error {worst:.1f} points")

    def test_the_margin_covers_the_error(self):
        covered = total = 0
        for build in self.SCENARIOS.values():
            for seed in range(2):
                exact, sampled = self.compare(build, seed=seed)
                for a, b in zip(exact["rows"], sampled["rows"]):
                    total += 1
                    covered += abs(a["evil_pct"] - b["evil_pct"]) <= b["margin"]
        self.assertGreater(covered / total, 0.85,
                           f"only {covered}/{total} figures fell inside their margin")

    def test_the_world_count_is_in_the_right_range(self):
        for name, build in self.SCENARIOS.items():
            with self.subTest(scenario=name):
                exact, sampled = self.compare(build)
                self.assertPct(100 * (sampled["valid"] - exact["valid"])
                               / max(exact["valid"], 1), 0.0, 10.0, name)


class HonestLabelling(SolverTest):

    def test_an_exact_answer_carries_no_margin_and_says_so(self):
        r = analyze(game(9))
        self.assertFalse(r["sampled"])
        self.assertIsNone(r["ess"])
        self.assertTrue(all(row["margin"] == 0.0 for row in r["rows"]))

    def test_a_sampled_answer_carries_a_margin_and_says_so(self):
        r = estimate(game(9), dives=4000, rng=random.Random(0))
        self.assertTrue(r["sampled"])
        self.assertGreater(r["ess"], 0)
        self.assertTrue(all(row["margin"] > 0.0 for row in r["rows"]))

    def test_fewer_walks_means_a_wider_margin(self):
        few = estimate(game(9), dives=1200, rng=random.Random(1))
        many = estimate(game(9), dives=12000, rng=random.Random(1))
        self.assertGreater(statistics.mean(r["margin"] for r in few["rows"]),
                           statistics.mean(r["margin"] for r in many["rows"]))

    def test_the_effective_sample_is_not_just_the_walk_count(self):
        """Importance weighting means uneven samples carry less than they
        appear to. Reporting the raw count would overstate the precision."""
        r = estimate(game(9), dives=6000, rng=random.Random(0))
        self.assertLess(r["ess"], 8000)


class ChoosingBetweenThem(SolverTest):

    def test_a_small_search_is_counted_exactly(self):
        self.assertFalse(analyze(game(9))["sampled"])

    def test_an_enormous_search_is_sampled_rather_than_refused(self):
        r = analyze(game(12, claims={}), rng=random.Random(0))
        self.assertTrue(r["sampled"])
        self.assertGreater(r["valid"], 10 ** 6)

    def test_the_pilot_spots_a_hopeless_search_quickly(self):
        small = pilot_size(game(9))
        huge = pilot_size(game(12, claims={}))
        self.assertLess(small, 10 ** 4)
        self.assertGreater(huge, 10 ** 6)

    def test_the_same_seed_gives_the_same_answer(self):
        a = estimate(game(9), dives=2500, rng=random.Random(42))
        b = estimate(game(9), dives=2500, rng=random.Random(42))
        self.assertEqual([r["evil_pct"] for r in a["rows"]],
                         [r["evil_pct"] for r in b["rows"]])


if __name__ == "__main__":
    unittest.main()
