// Looking back on a game that really happened.
//
// Everything else here is measured against a simulator written in the
// same repository, which is circular. A real game is not: the table
// recorded what it heard, the grimoire was opened at the end, and the
// question is simply what this tool would have said each morning — and
// whether that would have found the Demon.
//
// That is the measure, because it is the table's (30.09.2026): if some
// characters come out wrong but the Demon is found, the job is done. So
// each morning is judged by where the true Demon stood among the seats,
// how sure the tool was of it, and whether it was the top suspect.
//
// The board is cut back to what the table knew at dawn after night k:
// every night event and night reading up to night k, and day events only
// up to the day before — the day itself had not happened yet.

import {lookup} from "./catalogue.mjs";
import {progressPart} from "./report.mjs";
import {TEAM} from "./roles.mjs";

// Rows that happen in daylight. They carry the number of the day, and a
// day comes after the night of the same number.
const DAY_ROWS = new Set(["SlayerShot", "VirginNomination", "SavantInfo",
                          "Alsaahir", "ArtistInfo"]);
const DAY_EVENTS = new Set(["X", "S", "D", "W", "M"]);

/** The last night this board reaches. */
export function lastNight(payload) {
  let last = 1;
  for (const row of payload.infos || []) last = Math.max(last, row.night || 1);
  for (const n of payload.quiet_nights || []) last = Math.max(last, +n);
  for (const seat of payload.players || [])
    for (const code of seat.events || []) {
      const k = parseInt(String(code).slice(1), 10);
      if (!Number.isFinite(k)) continue;
      // An execution on day k means the game went on to night k + 1.
      last = Math.max(last, DAY_EVENTS.has(String(code)[0].toUpperCase())
                            ? k + 1 : k);
    }
  for (const d of payload.days_done || []) last = Math.max(last, +d + 1);
  return last;
}

/** The board as the table knew it at dawn after night `night`. */
export function boardAt(payload, night) {
  const early = (kind, k) =>
    DAY_EVENTS.has(kind) ? k < night : k <= night;
  const players = (payload.players || []).map(seat => ({
    ...seat,
    events: (seat.events || []).filter(code => {
      const k = parseInt(String(code).slice(1), 10);
      return Number.isFinite(k) && early(String(code)[0].toUpperCase(), k);
    }),
    voted: (seat.voted || []).filter(day => +day < night),
    nominated: (seat.nominated || []).filter(day => +day < night),
  }));
  const infos = (payload.infos || []).filter(row =>
    DAY_ROWS.has(row.type) ? (row.night || 1) < night
                           : (row.night || 1) <= night);
  return {
    ...payload,
    players,
    infos,
    quiet_nights: (payload.quiet_nights || []).filter(n => +n <= night),
    days_done: (payload.days_done || []).filter(d => +d < night),
  };
}

/** Which seats really were the Demon, from what was revealed.
 *
 * `truth` is one entry per seat: the character they really held at the
 * end, or empty if not known. Every seat that held a Demon counts — a
 * starpass leaves two, and either being found is finding the Demon.
 */
export function trueDemons(truth) {
  const out = [];
  (truth || []).forEach((name, seat) => {
    const found = name ? lookup(name) : null;
    if (found && TEAM[found.key] === "demon") out.push(seat);
  });
  return out;
}

/** How one morning's answer did against the truth. */
export function judge(data, truth) {
  if (!data || data.error || !data.rows)
    return {error: (data && data.error) || "no answer"};
  const demons = trueDemons(truth);
  const rows = data.rows;
  const rankOf = seat => 1 + rows.filter(
    r => r.demon_pct > rows[seat].demon_pct + 1e-9).length;
  let best = null;
  for (const seat of demons) {
    const pct = rows[seat].demon_pct;
    // Seats level with it: first place shared with three others is a
    // quarter of an answer, and should read as one.
    const level = rows.filter(r => r.player !== seat &&
                                   Math.abs(r.demon_pct - pct) < 1e-9).length;
    const here = {seat, rank: rankOf(seat), pct, level};
    if (!best || here.rank < best.rank ||
        (here.rank === best.rank && here.pct > best.pct)) best = here;
  }
  const top = rows.reduce((a, r) => (r.demon_pct > a.demon_pct ? r : a),
                          rows[0]);
  const evil = [], good = [];
  (truth || []).forEach((name, seat) => {
    const found = name ? lookup(name) : null;
    if (!found || !rows[seat]) return;
    const team = TEAM[found.key];
    (team === "minion" || team === "demon" ? evil : good)
      .push(rows[seat].evil_pct);
  });
  const mean = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length
                               : null;
  return {
    valid: data.valid, sampled: !!data.sampled,
    demon: best,                                  // null if none revealed
    topSeat: top.player, topPct: top.demon_pct,
    found: !!best && best.rank === 1,
    evilMean: mean(evil), goodMean: mean(good),
  };
}

/** Every morning of the game, solved as it stood and judged.
 *
 * `solve` is the solver's own entry point (`api.solveBoard`), handed in
 * so this module needs nothing from the page's entry point. `onNight(k,
 * last)` is told before each morning is solved.
 */
export function review(payload, truth, {solve, onNight = null} = {}) {
  const last = lastNight(payload);
  const nights = [];
  for (let night = 1; night <= last; night++) {
    if (onNight) onNight(night, last);
    progressPart(night - 1, last);
    const data = solve(boardAt(payload, night));
    nights.push({night, ...judge(data, truth)});
  }
  return {nights, demons: trueDemons(truth), last};
}
