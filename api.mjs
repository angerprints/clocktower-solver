// The same contract the server offered, answered on the device.
//
// The page has always talked to the solver over one JSON call — a board
// goes in, an answer comes out — which is what makes this swap possible
// without touching the grimoire itself. Every shape below is the shape
// `app.py` returns, because the page reads them and the page is not
// changing.
//
// `app.py` still works and is still the way to run this from a laptop
// with a phone borrowing it. What changes is that the phone no longer
// has to.

import "./characters.rules.mjs";        // registers every character rule
import {CHARACTERS, SETUP, WAKE_LABELS, WAKE_PATTERNS, lookup}
  from "./catalogue.mjs";
import {makeInfo} from "./info.mjs";
import {claimsCannotFillTheBag, diagnose} from "./diagnose.mjs";
import {couldExplainNothingFitting, refuses} from "./limits.mjs";
import {EXACT_LIMIT, analyze} from "./report.mjs";
import {sensitivity} from "./sensitivity.mjs";
import {TEAM, WAKE, show} from "./roles.mjs";
import * as scripts from "./scripts.mjs";
import {GameState} from "./state.mjs";
import {OffScript} from "./worlds.mjs";

// Above the exact limit the solver samples rather than walking every
// world, and says so — the page shows the margins. Truncating instead
// would be worse than either: a partial answer with no margins and no way
// to tell which worlds were dropped.

// Which reading each character produces. A row only makes sense on a
// script that has the character behind it.
const INFO_SOURCES = {
  Washerwoman: "Washerwoman", Librarian: "Librarian",
  Investigator: "Investigator", Chef: "Chef", Empath: "Empath",
  FortuneTeller: "FortuneTeller", Undertaker: "Undertaker",
  Ravenkeeper: "Ravenkeeper", SlayerShot: "Slayer",
  VirginNomination: "Virgin", GrandmotherInfo: "Grandmother",
  ChambermaidInfo: "Chambermaid", GamblerGuess: "Gambler",
  CourtierChoice: "Courtier",
};

// --------------------------------------------------------------------
// What the page needs to draw itself
// --------------------------------------------------------------------

export function scriptMeta(script, nPlayers = null) {
  const keys = script.seatedKeys;
  return {
    name: script.name,
    author: script.author,
    characters: keys.map(k => CHARACTERS[k].id),
    townsfolk: script.townsfolk,
    outsiders: script.outsiders,
    minions: script.minions,
    demons: script.demons,
    display: Object.fromEntries(keys.map(k => [k, show(k)])),
    wake_roles: Object.fromEntries(WAKE_PATTERNS.map(pat => [pat,
      [...script.townsfolk, ...script.outsiders].filter(
        k => !CHARACTERS[k].believes && WAKE[k].includes(pat))])),
    // A reading only exists if the character that produces it is in the
    // bag.
    info_types: Object.entries(INFO_SOURCES)
      .filter(([, source]) => keys.includes(source)).map(([name]) => name),
    complaints: complaintsAbout(script, nPlayers),
    playable: scripts.isPlayable(script),
    // Shown as checkboxes rather than dealt: the table knows which are in
    // play, so the solver is told rather than working it out.
    fabled: script.fabled.map(k => ({key: k, name: show(k)})),
    unmodelled: scripts.unmodelled(script)
      .map(c => ({key: c.key, name: c.name, note: c.note})),
  };
}

function complaintsAbout(script, nPlayers) {
  const out = [];
  if (!scripts.isPlayable(script))
    out.push("This script has no Townsfolk, no Minions or no Demon, so " +
             "there is no game to solve.");
  for (const short of scripts.tooSmallFor(script, nPlayers))
    out.push(`A ${nPlayers}-player game needs ${short.need} ` +
             `${short.team === "townsfolk" ? "Townsfolk"
                : short.team === "outsider" ? "Outsiders"
                : short.team === "minion" ? "Minions" : "Demons"}, ` +
             `and this script has ${short.have}.`);
  if (script.unknown.length)
    out.push(`Not recognised, and left out: ${script.unknown.join(", ")}.`);
  return out;
}

export function meta() {
  return {
    setup: Object.fromEntries(Object.entries(SETUP)),
    wake_patterns: WAKE_PATTERNS,
    wake_labels: WAKE_LABELS,
    catalogue: Object.values(CHARACTERS)
      .map(c => ({id: c.id, key: c.key, name: c.name, team: c.team,
                  modelled: c.modelled, note: c.note}))
      .sort((a, b) => a.team.localeCompare(b.team) ||
                      a.name.localeCompare(b.name)),
    built_in: Object.keys(scripts.BUILT_IN).sort(),
    script: scriptMeta(scripts.DEFAULT),
  };
}

/** A chosen or uploaded script, turned into what the page needs.
 *
 * Three ways in: a built-in by name, a list of characters somebody picked
 * themselves, or the contents of a `.json` a Storyteller handed round.
 * All three end up as the same thing.
 */
export function loadScript(payload) {
  try {
    let script;
    if (payload.json !== undefined && payload.json !== null)
      script = scripts.fromJson(payload.json);
    else if (payload.characters !== undefined && payload.characters !== null)
      script = scripts.fromIds(payload.name || "Custom script",
                               payload.characters, payload.author || "");
    else
      script = scripts.BUILT_IN[payload.name] || scripts.DEFAULT;
    return {script: scriptMeta(script, payload.n_players)};
  } catch (err) {
    return {error: `That script could not be read: ${err.message || err}`};
  }
}

// --------------------------------------------------------------------
// Turning the page's JSON into a board
// --------------------------------------------------------------------

const asList = value =>
  value === null || value === undefined || value === "" ? []
    : (typeof value === "string" ? [value] : [...value]);

function scriptFrom(payload) {
  const chosen = payload.script;
  if (!chosen) return scripts.DEFAULT;
  if (chosen.characters)
    return scripts.fromIds(chosen.name || "Custom script",
                           chosen.characters, chosen.author || "");
  return scripts.BUILT_IN[chosen.name] || scripts.DEFAULT;
}

/** Everything that can be wrong with a board before it is worth solving.
 *
 * The messages are the ones the page shows, so they say what to do about
 * it rather than what went wrong.
 */
function readBoard(payload) {
  const n = Number(payload.n_players);
  if (!SETUP[n]) return {error: "Table sizes from 5 to 15 players."};

  const script = scriptFrom(payload);
  if (!scripts.isPlayable(script))
    return {error: "This script has no Townsfolk, no Minions or no Demon, " +
                   "so there is no game to solve."};
  const short = scripts.tooSmallFor(script, n);
  if (short.length)
    return {error: complaintsAbout(script, n)[0]};

  const claims = {}, certainties = {}, reads = {}, wakes = {}, suspects = {};
  const deaths = {}, resurrections = {}, executions = {};

  const players = payload.players || [];
  for (let i = 0; i < n; i++) {
    const seat = players[i] || {};
    if (seat.claim) {
      const found = lookup(seat.claim);
      const key = found ? found.key : null;
      if (!key || !script.seatedKeys.includes(key))
        return {error: `Seat ${i + 1} claims ${seat.claim}, which is not ` +
                       `on ${script.name}. Change the script, or the claim.`};
      claims[i] = key;
    }
    if (seat.certainty) certainties[i] = seat.certainty;
    if (seat.read) reads[i] = Number(seat.read);
    if (seat.suspect) suspects[i] = true;
    if (seat.wake) wakes[i] = seat.wake;

    const events = [...asList(seat.events)];
    if (seat.death) events.push(seat.death);
    for (const raw of events) {
      const code = String(raw || "").trim();
      if (!code) continue;
      const kind = code[0].toUpperCase();
      const day = parseInt(code.slice(1), 10);
      if (!Number.isFinite(day))
        return {error: `Seat ${i + 1} has an unreadable status.`};
      if (kind === "X" || kind === "S") {
        if (executions[day] !== undefined && executions[day] !== i)
          return {error: `Seat ${i + 1} and seat ${executions[day] + 1} ` +
                         `are both marked as executed on day ${day}. The ` +
                         `town only executes once a day.`};
        executions[day] = i;
        if (kind === "X") (deaths[i] = deaths[i] || []).push(`D${day}`);
      } else if (kind === "R") {
        (resurrections[i] = resurrections[i] || []).push(`N${day}`);
      } else {
        (deaths[i] = deaths[i] || []).push(code);
      }
    }
    for (const p of asList(seat.died)) (deaths[i] = deaths[i] || []).push(p);
    for (const p of asList(seat.raised))
      (resurrections[i] = resurrections[i] || []).push(p);
  }

  const quiet = (payload.quiet_nights || []).map(Number);
  for (const night of quiet)
    for (const [seatKey, phases] of Object.entries(deaths))
      if (phases.includes(`N${night}`))
        return {error: `Night ${night} is marked as quiet, but seat ` +
                       `${Number(seatKey) + 1} is recorded as dying that ` +
                       `night.`};

  const infos = [];
  for (const row of payload.infos || []) {
    // The Demon kills before the Empath, Undertaker and Fortune Teller
    // wake, so a seat killed tonight hears nothing tonight. Three
    // exceptions: the Ravenkeeper is woken *by* dying, a Slayer shot and
    // a Virgin nomination happen in daylight, and a Gambler that guessed
    // wrong is dead *because* it acted.
    const actedAnyway = ["Ravenkeeper", "SlayerShot", "VirginNomination",
                         "GamblerGuess"];
    const speaker = Number(row.player || 0);
    const night = Number(row.night || 1);
    if ((deaths[speaker] || []).includes(`N${night}`) &&
        !actedAnyway.includes(row.type))
      return {error: `Seat ${speaker + 1} was killed on night ${night}, so ` +
                     `they never woke to learn this. Only the Ravenkeeper ` +
                     `learns anything as it goes.`};
    try {
      infos.push(makeInfo(row));
    } catch (err) {
      return {error: String(err.message || err)};
    }
  }

  return {
    state: new GameState({
      nPlayers: n, script, claims, certainties, reads, wakes, suspects,
      deaths, resurrections, executions, quietNights: quiet,
      fabled: scripts.fabledInPlay(script, payload.fabled || []),
      infos, names: (payload.players || []).map(s => s.name || ""),
    }),
  };
}

// --------------------------------------------------------------------
// Solving
// --------------------------------------------------------------------

/** How much of each seat's reading rests on a guess rather than on the
 * evidence. */
export function guessworkFor(payload) {
  const read = readBoard(payload);
  if (read.error) return {error: read.error};
  const got = sensitivity(read.state, !!payload.allow_good_lies);
  return {
    sensitivity: true,
    rows: got.rows.map(r => ({
      player: r.player,
      evil_pct: Math.round(r.evil_pct * 10) / 10,
      low: Math.round(r.low * 10) / 10,
      high: Math.round(r.high * 10) / 10,
      swing: Math.round(r.swing * 10) / 10,
      driver: (r.driver || "").replace(/_/g, " ").toLowerCase(),
    })),
  };
}

/** Nothing survived. Say what would have to give.
 *
 * One removable entry usually means a mis-entered reading or somebody
 * lying. No single entry accounting for it is the interesting case, and
 * on a script that lets the Storyteller break the rules it is worth
 * naming that possibility — without claiming it, since a board can be
 * contradictory in ordinary ways too.
 */
function whyNothingFits(state) {
  // The claims themselves are a common cause, and one the entry-by-entry
  // search cannot see, so it is asked first — but not instead of the
  // rest. A bag that cannot be filled is also exactly what an Atheist
  // game looks like, so both get said.
  const bag = claimsCannotFillTheBag(state);
  const out = bag
    ? {culprits: [], complete: true, bag}
    : diagnose(state);

  if (!out.culprits.length && out.complete) {
    const loose = couldExplainNothingFitting(state.script);
    out.unsupported = Object.entries(loose).map(([name, entry]) => ({
      name, short: entry.short, why: entry.why, signal: entry.signal,
    }));
  }
  return out;
}

/** Answer a board, in the shape the page has always been handed. */
export function solveBoard(payload) {
  const read = readBoard(payload);
  if (read.error) return {error: read.error};
  const state = read.state;

  // Characters that make solving dishonest before it even starts. The
  // board would look perfectly solvable and every number would be wrong,
  // so this is refused rather than attempted.
  const refused = refuses(state.script);
  if (Object.keys(refused).length) {
    const [name, entry] = Object.entries(refused)[0];
    return {error: `${name} is on this script, and ${entry.short}. ` +
                   `${entry.why}`};
  }

  let result;
  try {
    result = analyze(state, !!payload.allow_good_lies, EXACT_LIMIT);
  } catch (err) {
    if (err instanceof OffScript) return {error: err.message};
    throw err;
  }

  const samples = result.samples.map(w =>
    w.roles.map((r, p) => w.believes[p]
      ? `${show(r)} (thinks ${show(w.believes[p])})` : show(r)));

  const rows = result.rows.map(row => ({
    ...row,
    roles: row.roles.slice(0, 6)
      .map(([r, pc]) => [show(r), Math.round(pc * 10) / 10]),
    margin: Math.round((row.margin || 0) * 10) / 10,
  }));

  const reply = {
    legal: result.legal, valid: result.valid,
    sampled: result.sampled, ess: result.ess,
    rows, samples,
  };
  if (result.mastermind && result.mastermind.length)
    reply.mastermind = result.mastermind;
  if (result.blame && Object.keys(result.blame).length)
    reply.blame = result.blame;
  if (result.readings && result.readings.length)
    reply.readings = result.readings;
  if (!result.valid) reply.diagnosis = whyNothingFits(state);
  return reply;
}
