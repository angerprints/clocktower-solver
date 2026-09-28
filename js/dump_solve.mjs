// The conformance corpus, answered by the JavaScript solver.
//
//     node js/dump_solve.mjs tests/fixtures/conformance.json
//
// This is the check the whole port has been building towards: the boards
// Python answered are answered again, and the numbers have to match to
// four figures.
//
// It goes through `api.solveBoard` — the same entry the page calls —
// rather than reading the payload itself. It used to have its own copy
// of that reader, which drifted the moment the board learned to record
// something new: votes were added, the page and the server both handled
// them, and this quietly did not, so the corpus reported a difference
// between the two implementations that did not exist.

import {readFileSync} from "node:fs";
import {solveBoard} from "./api.mjs";

const PLACES = 4;
const round = x => Number(x.toFixed(PLACES));
// Higher than app.py's ceiling, on purpose.
//
// Matching it exactly is not enough. Whether to sample is decided by
// `pilotSize`, a random walk of 1500 probes that *estimates* the world
// count before enumerating — so on a board near the threshold the two
// languages estimate differently and fall on opposite sides. One
// enumerates 51,516 worlds exactly, the other samples ~35,000 from a
// random walk, and the answers differ by three points of nothing.
//
// A sampled answer can never be compared against an exact one, so this
// side is given room to enumerate whatever Python enumerated.
const SERVER_MAX_WORLDS = 5_000_000;

function answer(payload) {
  let got;
  try {
    got = solveBoard(payload, {maxWorlds: SERVER_MAX_WORLDS});
  } catch (err) {
    return {error: String(err.message || err)};
  }
  if (got.error) return {error: got.error};

  const out = {
    valid: got.valid,
    sampled: got.sampled,
    rows: got.rows.map(row => ({
      evil_pct: round(row.evil_pct), demon_pct: round(row.demon_pct),
      drunk_pct: round(row.drunk_pct), lying_pct: round(row.lying_pct),
    })),
  };
  if (got.blame && Object.keys(got.blame).length)
    out.blame = Object.fromEntries(Object.entries(got.blame).map(
      ([night, seats]) => [night, Object.fromEntries(Object.entries(seats).map(
        ([seat, causes]) => [seat, Object.fromEntries(
          Object.entries(causes).map(([c, v]) => [c, round(v)]))]))]));
  return out;
}

const corpus = JSON.parse(readFileSync(process.argv[2], "utf8"));
const out = {};
for (const item of corpus.cases) out[item.name] = answer(item.payload);
process.stdout.write(JSON.stringify(out, null, 1) + "\n");
