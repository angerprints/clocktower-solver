// How much of the answer is the evidence, and how much is my guesswork.
//
// Every figure the solver prints mixes two things. Some of it is the
// rulebook. The rest rests on a dozen constants picked by judgement, and
// they are printed in the same font as the parts that are checkable.
//
// This re-solves the same board with each of those constants moved to the
// edges of the range I would defend, and reports how far each seat's
// reading travels — and which constant moved it. A seat the evidence has
// pinned down barely shifts; a seat resting on a guess swings, and it is
// worth knowing which guess before trusting the number.
//
// Deliberately done by sampling, with the same seed every time. The walks
// are then identical across every setting and only the weights differ, so
// what comes back is the effect of the guess and nothing else — no
// sampling noise mixed in. It also keeps the cost the same whatever the
// table size, which re-solving exactly would not.
//
// One constant is moved at a time. Combinations would be more thorough
// and far slower, and the point is to find the load-bearing guess rather
// than to bound the worst case.

import {PRIOR_RANGES, withPrior} from "./priors.mjs";
import {estimate} from "./report.mjs";
import {Rng} from "./rng.mjs";

export function sensitivity(state, allowGoodLies = false, {
  ranges = PRIOR_RANGES, seed = 0, dives = 3500,
} = {}) {
  const solveNow = () =>
    estimate(state, allowGoodLies, dives, 1, new Rng(seed));

  const base = solveNow();
  const rows = base.rows.map((r, i) => ({
    player: i, evil_pct: r.evil_pct,
    low: r.evil_pct, high: r.evil_pct,
    driver: null, swing: 0.0,
  }));

  for (const [name, [low, high]] of Object.entries(ranges)) {
    const seen = [low, high].map(value =>
      withPrior(name, value, () => solveNow().rows));

    rows.forEach((row, i) => {
      const here = seen.map(got => got[i].evil_pct);
      row.low = Math.min(row.low, ...here);
      row.high = Math.max(row.high, ...here);
      const moved = Math.max(...here) - Math.min(...here);
      if (moved > row.swing) {
        row.swing = moved;
        row.driver = name;
      }
    });
  }

  return {base, rows};
}
