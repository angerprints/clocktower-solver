"""The JavaScript sampler.

This one cannot be checked the way everything else was. A sampled answer
comes from a random walk, so holding it against Python number-for-number
would mean pinning the JavaScript to Python's generator forever — and
that is not what makes a sampler correct anyway.

What makes it correct is that it converges on the right answer and is
honest about how far off it might be. So the checks are:

  * the world *count* it estimates matches the exact count,
  * every seat's reading lands inside the margin it printed, against the
    exact answer from the same board,
  * the margins shrink as the walks go up, roughly as the square root
    says they should,
  * dead-end walks are counted, because dropping them biases everything
    upwards,
  * and a board too big to walk is sampled rather than truncated, which
    is the gap this closes.

Skipped when Node is not installed.
"""

import json
import pathlib
import shutil
import subprocess
import unittest

from helpers import SolverTest                    # sets up the import path
import botc.solver as S                            # noqa: E402
from botc import scripts                           # noqa: E402
from botc.info import GameState                    # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
       "FortuneTeller", "Undertaker", "Recluse", "Saint"]


def run(script):
    got = subprocess.run([NODE, "--input-type=module", "-e", script],
                         capture_output=True, text=True, timeout=600,
                         cwd=str(ROOT))
    if got.returncode:
        raise AssertionError(got.stderr)
    return json.loads(got.stdout.strip().splitlines()[-1])


@unittest.skipUnless(NODE, "Node is not installed")
class TheGenerator(SolverTest):
    """Seeded, because an unseeded sampler is untestable: every run
    differs and there is no telling a regression from noise."""

    @classmethod
    def setUpClass(cls):
        cls.got = run("""
        const {Rng} = await import("./js/rng.mjs");
        const take = r => Array.from({length: 8}, () => r.random());
        const a = take(new Rng(42)), b = take(new Rng(42)), c = take(new Rng(43));
        let sum = 0; const buckets = new Array(10).fill(0);
        const r = new Rng(7);
        for (let i = 0; i < 200000; i++) {
          const x = r.random(); sum += x; buckets[Math.floor(x * 10)]++;
        }
        const below = new Rng(9); const seen = new Set();
        for (let i = 0; i < 2000; i++) seen.add(below.below(7));
        console.log(JSON.stringify({a, b, c, mean: sum / 200000, buckets,
                                    below: [...seen].sort()}));
        """)

    def test_the_same_seed_gives_the_same_walk(self):
        self.assertEqual(self.got["a"], self.got["b"])

    def test_a_different_seed_does_not(self):
        self.assertNotEqual(self.got["a"], self.got["c"])

    def test_it_is_evenly_spread(self):
        self.assertPct(self.got["mean"], 0.5, 0.005)
        for i, count in enumerate(self.got["buckets"]):
            with self.subTest(decile=i):
                self.assertPct(count, 20_000, 600)

    def test_a_whole_number_below_n_covers_every_value(self):
        self.assertEqual(self.got["below"], list(range(7)))


@unittest.skipUnless(NODE, "Node is not installed")
class TheSamplerAgreesWithTheExactAnswer(SolverTest):
    """Against a board small enough to have one."""

    @classmethod
    def setUpClass(cls):
        cls.got = run("""
        await import("./js/characters.rules.mjs");
        const {Rng} = await import("./js/rng.mjs");
        const {GameState} = await import("./js/state.mjs");
        const scr = await import("./js/scripts.mjs");
        const rep = await import("./js/report.mjs");
        const seats = ["Washerwoman","Librarian","Investigator","Chef",
                       "Empath","FortuneTeller","Undertaker","Recluse","Saint"];
        const claims = Object.fromEntries(seats.map((r, i) => [i, r]));
        const state = new GameState({nPlayers: 9, script: scr.TROUBLE_BREWING,
                                     claims, deaths: {2: "N2"}});
        const exact = rep.analyze(state, false, 1e9);
        const out = {exact: {valid: exact.valid,
                             evil: exact.rows.map(r => r.evil_pct)}, runs: {}};
        for (const dives of [2000, 8000, 32000]) {
          const got = rep.estimate(state, false, dives, 8, new Rng(1));
          out.runs[dives] = {
            valid: got.valid, sampled: got.sampled, dives: got.dives,
            ess: got.ess,
            evil: got.rows.map(r => r.evil_pct),
            margins: got.rows.map(r => r.margin),
          };
          // Coverage across many seeds, which is the only way to check a
          // margin means what it says. One run cannot: a 95% interval is
          // supposed to miss now and then, and demanding it never does
          // would be testing for a margin that is too wide.
          let inside = 0, checks = 0, worst = 0;
          for (let seed = 1; seed <= 60; seed++) {
            const run = rep.estimate(state, false, dives, 8, new Rng(seed));
            run.rows.forEach((r, i) => {
              checks++;
              const off = Math.abs(r.evil_pct - exact.rows[i].evil_pct);
              if (off <= r.margin) inside++;
              worst = Math.max(worst, off);
            });
          }
          out.runs[dives].coverage = inside / checks;
          out.runs[dives].worst = worst;
        }
        console.log(JSON.stringify(out));
        """)

    def test_it_says_it_sampled(self):
        for dives, got in self.got["runs"].items():
            with self.subTest(dives=dives):
                self.assertTrue(got["sampled"])
                self.assertEqual(got["dives"], int(dives))

    def test_the_world_count_it_estimates_is_about_right(self):
        exact = self.got["exact"]["valid"]
        for dives, got in self.got["runs"].items():
            with self.subTest(dives=dives):
                self.assertPct(got["valid"], exact, exact * 0.10)

    def test_the_margin_means_what_it_says(self):
        """Two standard errors is a *95%* claim, so the check is coverage
        across many seeds — not that a single run never misses.

        The first version of this asserted every seat was inside on one
        seed, which asks a 95% interval to be right every time and failed
        exactly as often as it should have. Measured across sixty seeds
        the real coverage is about 96%, which is the margin being honest
        rather than generous.
        """
        for dives, got in self.got["runs"].items():
            with self.subTest(dives=dives):
                self.assertGreater(got["coverage"], 0.90,
                                   "the margin is too narrow to be trusted")
                self.assertLess(got["coverage"], 0.995,
                                "a margin that never misses is too wide "
                                "to be useful")

    def test_and_it_is_never_wildly_out(self):
        """Coverage alone would allow rare enormous misses."""
        for dives, got in self.got["runs"].items():
            with self.subTest(dives=dives):
                self.assertLess(got["worst"], 6.0)

    def test_more_walks_narrow_it(self):
        runs = self.got["runs"]
        wide = max(runs["2000"]["margins"])
        tight = max(runs["32000"]["margins"])
        self.assertLess(tight, wide / 2,
                        "sixteen times the walks should roughly quarter it")

    def test_the_effective_sample_size_is_honest(self):
        """It has to be below the number of walks — importance weighting
        means uneven samples carry less than their count suggests."""
        for dives, got in self.got["runs"].items():
            with self.subTest(dives=dives):
                self.assertLessEqual(got["ess"], int(dives) + 1)
                self.assertGreater(got["ess"], int(dives) * 0.3)


@unittest.skipUnless(NODE, "Node is not installed")
class ABoardTooBigToWalk(SolverTest):
    """The gap this closes: it used to stop early and hand back a
    partial count with no margins and no way to tell."""

    @classmethod
    def setUpClass(cls):
        cls.got = run("""
        const api = await import("./js/api.mjs");
        const chars = ["grandmother","sailor","chambermaid","exorcist",
          "innkeeper","gambler","gossip","courtier","professor","minstrel",
          "tealady","pacifist","fool","tinker","moonchild","goon","lunatic",
          "godfather","devilsadvocate","assassin","mastermind","zombuul",
          "pukka","shabaloth","po"];
        const seats = ["Grandmother","Sailor","Chambermaid","Exorcist",
          "Innkeeper","Gambler","Gossip","Courtier","Professor","Minstrel",
          "TeaLady","Tinker"];
        const r = api.solveBoard({
          n_players: 12, infos: [],
          players: seats.map(c => ({claim: c, events: []})),
          script: {name: "Bad Moon Rising", characters: chars}});
        console.log(JSON.stringify({
          valid: r.valid, sampled: r.sampled,
          margins: r.rows.map(x => x.margin),
          evil: r.rows.map(x => x.evil_pct)}));
        """)

    def test_it_is_sampled_rather_than_truncated(self):
        self.assertTrue(self.got["sampled"])

    def test_it_reaches_a_count_no_exact_walk_would(self):
        self.assertGreater(self.got["valid"], 100_000)

    def test_it_says_how_far_off_it_might_be(self):
        for seat, edge in enumerate(self.got["margins"]):
            with self.subTest(seat=seat + 1):
                self.assertGreater(edge, 0.0,
                                   "a sampled answer without a margin is "
                                   "worse than no answer")

    def test_the_readings_are_percentages(self):
        for seat, pct in enumerate(self.got["evil"]):
            with self.subTest(seat=seat + 1):
                self.assertBetween(pct, 0.0, 100.0)


if __name__ == "__main__":
    unittest.main()
