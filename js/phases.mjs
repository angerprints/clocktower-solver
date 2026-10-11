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

// --------------------------------------------------------------------
// Whose side was asked about
// --------------------------------------------------------------------
// Two stories of one world often differ only in *which* seat turned evil:
// the Bounty Hunter's evil Townsfolk, the player a Mezepheles turned. If
// explaining one never asked which side either seat was on, the other is
// explained by the very same steps and costs the same, so it need not be
// explained again (scoring.mjs `explainOrRecall`, 11.10.2026).
//
// So the questions are written down: for each seat, the moments its side
// was asked about, as bits. Everything that reads a side goes through
// `alignmentAt` on a world or a timeline, or through `knowsItTurnedEvil`;
// both note it here. A stack, because the memos inside an explanation
// keep what was asked along with their answer and say it again when the
// answer is reused. See info.py.

const READS = [];
// Past this many moments a seat counts as asked about at every one.
const LAST_BIT = 30;
// Only on a script where somebody can turn evil that way: everywhere
// else there is nothing to recall, and nothing is written down.
export let LISTENING = false;
const NOTHING = new Map();

export function listenForSides(on) { LISTENING = !!on; READS.length = 0; }

export function noteSideRead(seat, phase) {
  if (!READS.length) return;
  const got = READS[READS.length - 1];
  const bit = phaseIndex(phase) + 2;
  got.set(seat, bit > LAST_BIT ? -1 : (got.get(seat) || 0) | (1 << bit));
}

export function beginReads() { if (LISTENING) READS.push(new Map()); }

/** What was asked since `beginReads`, handed on to whoever is listening
 * further out. */
export function endReads() {
  if (!LISTENING) return NOTHING;
  const got = READS.pop();
  replayReads(got);
  return got;
}

export function replayReads(reads) {
  if (!READS.length || !reads.size) return;
  const into = READS[READS.length - 1];
  for (const [seat, bits] of reads) into.set(seat, (into.get(seat) || 0) | bits);
}

/** Do two stories differ only where nobody looked? Each maps a seat to
 * the moment it is evil from. See `_differ_only_unasked` in solver.py. */
export function differOnlyUnasked(flips, others, reads) {
  const check = (seat, mine, theirs) => {
    if (mine === theirs) return true;
    const asked = reads.get(seat) || 0;
    if (!asked) return true;
    const none = x => x === undefined;
    const first = none(mine) ? theirs : none(theirs) ? mine : Math.min(mine, theirs);
    const last = none(mine) || none(theirs) ? null : Math.max(mine, theirs);
    if (asked === -1 || first + 2 > LAST_BIT) return false;
    let bits = asked >>> (first + 2);
    if (last !== null && last - first < 31) bits &= (2 ** (last - first)) - 1;
    return bits === 0;
  };
  for (const [seat, mine] of flips)
    if (!check(seat, mine, others.get(seat))) return false;
  for (const [seat, theirs] of others)
    if (!flips.has(seat) && !check(seat, undefined, theirs)) return false;
  return true;
}

export const isNight = phase => phase[0].toUpperCase() === "N";
export const nightOf = phase => parseInt(phase.slice(1), 10);
