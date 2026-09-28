// Putting the moments of a game in order.
//
// Only two kinds of moment: "N" for a night and "D" for a day. Whether a
// daytime death was an execution is recorded separately, because the two
// facts are independent — somebody can be executed and live, and somebody
// can die in the day without being executed.
//
// "E" is accepted for games saved before that separation existed, where
// it meant an execution death.

const CACHE = new Map();

/** "N1" -> 0, "D1" -> 1, "N2" -> 2, and so on.
 *
 * Memoised, because every character rule asks this of every world on
 * every night and it was the single hottest function in the Python
 * version before the same cache went in.
 */
export function phaseIndex(phase) {
  const got = CACHE.get(phase);
  if (got !== undefined) return got;
  const kind = phase[0].toUpperCase();
  const num = parseInt(phase.slice(1), 10);
  const at = (num - 1) * 2 + (kind === "N" ? 0 : 1);
  CACHE.set(phase, at);
  return at;
}

export const isNight = phase => phase[0].toUpperCase() === "N";
export const nightOf = phase => parseInt(phase.slice(1), 10);
