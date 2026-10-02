// Every reading checked against a spread of worlds, and every question a
// board can be asked about a moment, printed for the Python side to be
// held against.
//
//     node js/dump_info.mjs
//
// The shape matters here. A reading is a function of (world, board), so
// testing it against one world proves almost nothing — a wrong
// implementation agrees with a right one most of the time. So each
// reading is run against every world of a small board, and what gets
// compared is the whole pattern of trues and falses.

import {createHash} from "node:crypto";
import {GameState} from "./state.mjs";
import {KINDS, livingNeighbours, possibleEvilCounts} from "./info.mjs";
import * as scripts from "./scripts.mjs";
import {eachWorld} from "./worlds.mjs";
import {possibleCounts, uncertain, woke, wokeAs} from "./waking.mjs";

const TB = scripts.TROUBLE_BREWING;
const BMR = scripts.BAD_MOON_RISING;

const TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"];
// A board where somebody claims the character being tested. Checking a
// Virgin trigger on a table with no Virgin claim makes it false in every
// world, which tells one implementation apart from nothing.
const TB12 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
              "FortuneTeller", "Undertaker", "Virgin", "Slayer", "Monk",
              "Recluse", "Saint"];
// Seven players, because that is the only table size whose bag wants
// *no* Outsiders — so "none in play" is a thing the Librarian can
// truthfully say. At nine it is impossible whatever anybody claims.
//
// Two Outsider claims, because otherwise it is true in *every* world: a
// Baron's bag wants two Outsiders and seven Townsfolk claims cannot fill
// it, so only the plain bag survives and the answer never varies.
const TB7 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "Recluse", "Saint"];
const BMR9 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
              "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"];

const claimsOf = list => Object.fromEntries(list.map((r, i) => [i, r]));

function board(script, claims, opts = {}) {
  return new GameState({nPlayers: claims.length, script,
                        claims: claimsOf(claims), ...opts});
}

/** Run a reading against every world of a board and digest the answers.
 *
 * The digest is over the sequence of trues and falses in world order, so
 * it only matches if the two implementations agree on every world — not
 * merely on how many they agree about.
 */
function pattern(script, claims, row, opts = {}, herring = null) {
  const state = board(script, claims, opts);
  const Kind = KINDS[row.type];
  const {type, ...fields} = row;
  const info = new Kind(fields);
  const seat = info.sourceSeat(state);
  const answers = [];
  eachWorld(claims.length, state.claims, {script}, world => {
    answers.push(info.holds(world, state, herring, seat) ? "1" : "0");
    return answers.length < 60_000;
  });
  return {
    worlds: answers.length,
    trues: answers.filter(a => a === "1").length,
    digest: createHash("sha256").update(answers.join("")).digest("hex")
                                .slice(0, 16),
    sourceSeat: seat,
    hard: info.hard(),
  };
}

const readings = {};
const add = (name, script, claims, row, opts, herring) =>
  (readings[name] = pattern(script, claims, row, opts, herring));

add("washerwoman", TB, TB9,
    {type: "Washerwoman", night: 1, player: 0, a: 1, b: 5, role: "Librarian"});
add("librarian-somebody", TB, TB9,
    {type: "Librarian", night: 1, player: 1, a: 7, b: 8, role: "Recluse"});
add("librarian-nobody", TB, TB7,
    {type: "Librarian", night: 1, player: 1, a: null, b: null, role: ""});
add("investigator", TB, TB9,
    {type: "Investigator", night: 1, player: 2, a: 3, b: 8, role: "Poisoner"});
for (const count of [0, 1, 2])
  add(`chef-${count}`, TB, TB9, {type: "Chef", night: 1, player: 3, count});
for (const count of [0, 1, 2])
  add(`empath-${count}`, TB, TB9,
      {type: "Empath", night: 1, player: 4, count});
add("empath-after-a-death", TB, TB9,
    {type: "Empath", night: 2, player: 4, count: 1}, {deaths: {3: "N2"}});
add("empath-killed-tonight", TB, TB9,
    {type: "Empath", night: 2, player: 4, count: 2}, {deaths: {4: "N2"}});
add("fortune-teller-yes", TB, TB9,
    {type: "FortuneTeller", night: 1, player: 5, a: 0, b: 8, yes: true});
add("fortune-teller-no", TB, TB9,
    {type: "FortuneTeller", night: 1, player: 5, a: 0, b: 8, yes: false});
// The herring is outside the pair, so it neither forces a yes nor
// forbids a no — the answer still turns on the world.
add("fortune-teller-yes-herring", TB, TB9,
    {type: "FortuneTeller", night: 1, player: 5, a: 0, b: 8, yes: true},
    {}, 3);
add("fortune-teller-no-herring", TB, TB9,
    {type: "FortuneTeller", night: 1, player: 5, a: 0, b: 8, yes: false},
    {}, 3);
add("undertaker", TB, TB9,
    {type: "Undertaker", night: 2, player: 6, target: 7, role: "Spy"},
    {deaths: {7: "E1"}});
add("undertaker-no-execution", TB, TB9,
    {type: "Undertaker", night: 2, player: 6, target: 7, role: "Spy"});
add("undertaker-survived", TB, TB9,
    {type: "Undertaker", night: 2, player: 6, target: 7, role: "Spy"},
    {executions: {1: 7}});
add("ravenkeeper", TB, TB9,
    {type: "Ravenkeeper", night: 2, player: 8, target: 4, role: "Empath"},
    {deaths: {8: "N2"}});
add("virgin-triggered", TB, TB12,
    {type: "VirginNomination", night: 1, player: 7, nominator: 2,
     triggered: true});
add("virgin-quiet", TB, TB12,
    {type: "VirginNomination", night: 1, player: 7, nominator: 2,
     triggered: false});
add("slayer-landed", TB, TB12,
    {type: "SlayerShot", night: 2, player: 8, target: 11, died: true});
add("slayer-missed", TB, TB12,
    {type: "SlayerShot", night: 2, player: 8, target: 11, died: false});
add("grandmother", BMR, BMR9,
    {type: "GrandmotherInfo", night: 1, player: 0, target: 2,
     role: "Chambermaid"});
add("grandmother-evil-target", BMR, BMR9,
    {type: "GrandmotherInfo", night: 1, player: 0, target: 7,
     role: "Godfather"});
add("gambler-lived", BMR, BMR9,
    {type: "GamblerGuess", night: 2, player: 5, target: 2,
     role: "Chambermaid"});
add("gambler-died", BMR, BMR9,
    {type: "GamblerGuess", night: 2, player: 5, target: 2,
     role: "Chambermaid"}, {deaths: {5: "N2"}});
const SV = scripts.SECTS_AND_VIOLETS;
const SV9 = ["Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician",
             "Flowergirl", "TownCrier", "Oracle", "Mutant", "Sweetheart"];
for (const count of [0, 1, 2, 4])
  add(`clockmaker-${count}`, SV, SV9,
      {type: "ClockmakerInfo", night: 1, player: 0, count});
add("dreamer-own-claim", SV, SV9,
    {type: "DreamerInfo", night: 1, player: 1, target: 2,
     good_role: "SnakeCharmer", evil_role: "Witch"});
add("dreamer-something-else", SV, SV9,
    {type: "DreamerInfo", night: 1, player: 1, target: 2,
     good_role: "Oracle", evil_role: "Witch"});
add("dreamer-two-good", SV, SV9,
    {type: "DreamerInfo", night: 1, player: 1, target: 2,
     good_role: "Oracle", evil_role: "Sage"});

add("courtier", BMR, BMR9,
    {type: "CourtierChoice", night: 1, player: 7, role: "Chambermaid"});
for (const count of [0, 1, 2])
  add(`chambermaid-${count}`, BMR, BMR9,
      {type: "ChambermaidInfo", night: 2, player: 2, a: 4, b: 6, count});
add("chambermaid-night-1", BMR, BMR9,
    {type: "ChambermaidInfo", night: 1, player: 2, a: 0, b: 1, count: 1});
add("chambermaid-with-an-exorcist", BMR, BMR9,
    {type: "ChambermaidInfo", night: 2, player: 2, a: 3, b: 8, count: 1});

// --- who actually woke, rule by rule ---------------------------------
const waking = {};
{
  // Every conditional waker, on a board where it can actually be there.
  // A good character nobody claims is in no world at all, so each case
  // carries claims that leave room for the one it is testing.
  const TB_RK = ["Washerwoman", "Librarian", "Investigator", "Chef",
                 "Empath", "FortuneTeller", "Undertaker", "Recluse",
                 "Ravenkeeper"];
  const BMR_CP = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
                  "Innkeeper", "Gambler", "Gossip", "Courtier", "Professor"];
  const cases = {
    ravenkeeper: [TB, TB_RK, {deaths: {8: "N2"}}, "Ravenkeeper", 8],
    "ravenkeeper-alive": [TB, TB_RK, {}, "Ravenkeeper", 8],
    undertaker: [TB, TB9, {deaths: {7: "E1"}}, "Undertaker", 6],
    "undertaker-survived": [TB, TB9, {executions: {1: 7}}, "Undertaker", 6],
    "scarlet-woman": [TB, TB9, {deaths: {8: "E1"}}, "ScarletWoman", 7],
    courtier: [BMR, BMR_CP, {}, "Courtier", 7],
    "courtier-spent": [BMR, BMR_CP,
      {infos: [{sourceRole: "Courtier", player: 7, night: 2}]},
      "Courtier", 7],
    professor: [BMR, BMR_CP, {}, "Professor", 8],
    "professor-spent": [BMR, BMR_CP,
      {deaths: {2: "N2"}, resurrections: {2: "N3"}}, "Professor", 8],
    zombuul: [BMR, BMR9, {}, "Zombuul", 8],
    "zombuul-after-a-day-death": [BMR, BMR9, {deaths: {1: "D2"}},
      "Zombuul", 8],
    assassin: [BMR, BMR9, {}, "Assassin", 7],
    "assassin-spent": [BMR, BMR9,
      {infos: [{sourceRole: "Assassin", player: 7, night: 2}]},
      "Assassin", 7],
    drunk: [TB, TB9, {}, "Drunk", 4],
  };
  for (const [name, [script, claims, opts, role, seat]] of
       Object.entries(cases)) {
    const state = board(script, claims, opts);
    // A world is not needed for most of these, but the believer rule
    // reads its token, so one is built with the character in place.
    const roles = claims.map((_c, i) => (i === seat ? role : null));
    const worlds = [];
    eachWorld(claims.length, state.claims, {script}, w => {
      if (w.roles[seat] === role) worlds.push(w);
      return worlds.length < 1;
    });
    const w = worlds[0] || null;
    waking[name] = w === null ? "no such world" : {
      byNight: [1, 2, 3, 4, 5].map(n => woke(w, state, seat, n)),
      asRole: [1, 2, 3].map(n => wokeAs(w, state, seat, n, role)),
      believesToken: w.believes[seat],
    };
  }

  // The Exorcist is the only thing that makes a waking genuinely open.
  const withExorcist = board(BMR, BMR9);
  const first = [];
  eachWorld(9, withExorcist.claims, {script: BMR}, w => {
    if (w.roles[3] === "Exorcist" && w.roles[8] === "Zombuul") first.push(w);
    return first.length < 1;
  });
  if (first.length) {
    const w = first[0];
    waking["exorcist makes the demon open"] = {
      demon: [1, 2, 3].map(n => uncertain(w, withExorcist, 8, n)),
      somebodyElse: [2].map(n => uncertain(w, withExorcist, 4, n)),
      counts: [1, 2, 3].map(n =>
        [...possibleCounts(w, withExorcist, [8, 4], n)].sort()),
    };
  }
}

// Worlds written out rather than searched for, because nobody claims to
// be a Lunatic or a Godfather. See test_js_info.py.
{
  const BMR = scripts.BAD_MOON_RISING;
  const GOOD = ["Grandmother", "Sailor", "Chambermaid", "Professor",
                "Innkeeper", "Gambler", "Tinker"];
  const LUNATIC = [...GOOD.slice(0, 6), "Lunatic"];
  const NOBODY = Array(9).fill(null);
  const thinks = token => [...Array(6).fill(null), token, null, null];
  const direct = {
    godfather: [[...GOOD, "Godfather", "Po"], NOBODY, {}],
    "godfather-outsider-executed": [[...GOOD, "Godfather", "Po"], NOBODY,
      {deaths: {6: "D1"}, executions: {1: 6}}],
    "godfather-townsfolk-executed": [[...GOOD, "Godfather", "Po"], NOBODY,
      {deaths: {5: "D1"}, executions: {1: 5}}],
    pukka: [[...GOOD, "Godfather", "Pukka"], NOBODY, {}],
    zombuul: [[...GOOD, "Godfather", "Zombuul"], NOBODY, {}],
    "shabaloth-and-a-raising": [[...GOOD, "Godfather", "Shabaloth"], NOBODY,
      {deaths: {0: "N2"}, resurrections: {0: "N3"}}],
    "po-and-a-raising": [[...GOOD, "Godfather", "Po"], NOBODY,
      {deaths: {0: "N2"}, resurrections: {0: "N3"}}],
    "lunatic-thinks-po": [[...LUNATIC, "Godfather", "Po"], thinks("Po"), {}],
    "lunatic-thinks-pukka": [[...LUNATIC, "Godfather", "Pukka"],
      thinks("Pukka"), {}],
    "lunatic-no-token": [[...LUNATIC, "Godfather", "Zombuul"], NOBODY,
      {deaths: {5: "D2"}, executions: {2: 5}}],
  };
  const {World} = await import("./worlds.mjs");
  for (const [name, [roles, believes, opts]] of Object.entries(direct)) {
    const state = board(BMR, [...roles.slice(0, 7), "Tinker", "Moonchild"],
                        opts);
    const w = new World(roles, believes);
    const nights = [1, 2, 3, 4];
    waking["direct " + name] = {
      woke: [3, 6, 7, 8].map(seat => nights.map(n => woke(w, state, seat, n))),
      open: [3, 6, 7, 8].map(seat =>
        nights.map(n => uncertain(w, state, seat, n))),
      counts: [[7, 8], [3, 6], [6, 8], [1, 7]].map(pair => nights.map(n =>
        [...possibleCounts(w, state, pair, n)].sort())),
    };
  }
}

// A Marionette beside a Chambermaid, which needs a mixed script: it counts
// as the token it holds (table ruling, 02.10.2026).
{
  const {World} = await import("./worlds.mjs");
  const mixed = scripts.fromIds("Mixed", [
    "chambermaid", "empath", "chef", "undertaker", "monk", "washerwoman",
    "slayer", "saint", "drunk", "marionette", "poisoner", "imp"]);
  for (const token of ["Empath", "Chef", "Undertaker"])
    for (const holder of ["Marionette", "Drunk"]) {
      const state = board(mixed, ["Chambermaid", token, "Monk",
                                  "Washerwoman", "Slayer", "Saint", "Chef"],
                          {deaths: {5: "D2"}, executions: {2: 5}});
      const w = new World(["Chambermaid", holder, "Imp", "Washerwoman",
                           "Slayer", "Saint", "Chef"],
                          [null, token, null, null, null, null, null]);
      waking[`token ${holder} thinks ${token}`] = [1, 2, 3, 4].map(n =>
        [...possibleCounts(w, state, [1, 4], n)].sort());
    }
}

// --- where a reading is attributed ------------------------------------
const relaying = {};
{
  const state = board(TB, TB9);
  const Kind = KINDS.Empath;
  relaying["spoken by the Empath"] =
    new Kind({night: 1, player: 4, count: 1}).sourceSeat(state);
  relaying["spoken by somebody else"] =
    new Kind({night: 1, player: 2, count: 1}).sourceSeat(state);
  const nobody = board(TB, ["Washerwoman", "Librarian", "Investigator",
    "Chef", "Monk", "FortuneTeller", "Undertaker", "Recluse", "Saint"]);
  relaying["nobody claims it"] =
    new Kind({night: 1, player: 2, count: 1}).sourceSeat(nobody);
  const twice = board(TB, ["Empath", "Librarian", "Investigator", "Chef",
    "Empath", "FortuneTeller", "Undertaker", "Recluse", "Saint"]);
  relaying["two seats claim it"] =
    new Kind({night: 1, player: 2, count: 1}).sourceSeat(twice);
  relaying["a shot is never relayed"] =
    new KINDS.SlayerShot({night: 2, player: 2, target: 8, died: true})
      .sourceSeat(state);
}

// --- what the board says about a moment -------------------------------
const lives = {};
{
  const cases = {
    "nothing recorded": {},
    "one night death": {deaths: {2: "N2"}},
    "an execution death": {deaths: {2: "E1"}},
    "executed and lived": {executions: {1: 2}},
    "died, raised": {deaths: {2: "N2"}, resurrections: {2: "N4"}},
    "died, raised, died": {deaths: {2: ["N2", "N6"]},
                           resurrections: {2: ["N4"]}},
    "raised the same night": {deaths: {2: "N2"}, resurrections: {2: "N2"}},
    "quiet nights": {quietNights: [2, 3]},
  };
  for (const [name, opts] of Object.entries(cases)) {
    const state = board(TB, TB9, opts);
    lives[name] = {
      alive: Object.fromEntries(
        ["N1", "D1", "N2", "D2", "N3", "N4", "N5", "N6", "N7"]
          .map(p => [p, state.aliveAt(p)])),
      diedAt: Object.fromEntries(
        [0, 2, 7].map(seat => [seat, state.diedAt(seat)])),
      deathPhases: [...state.deathPhases()],
      executions: state.executions,
      executedOn: Object.fromEntries(
        [1, 2].map(d => [d, state.executedOn(d)])),
      executionDeath: Object.fromEntries(
        [1, 2].map(d => [d, state.executionDeath(d)])),
      finalPhase: state.finalPhase(),
    };
  }
  // The final phase moves with the readings too.
  const withInfo = board(TB, TB9, {
    infos: [{night: 4}, {night: 2}]});
  lives["readings push the phase along"] = {finalPhase: withInfo.finalPhase()};
}

// --- the two helpers readings lean on ---------------------------------
const helpers = {neighbours: {}, evilCounts: {}};
{
  for (const [name, opts] of Object.entries({
    "everybody alive": {},
    "one gone": {deaths: {1: "N2"}},
    "two gone": {deaths: {1: "N2", 3: "N2"}},
    "the reader's own night death": {deaths: {2: "N2"}},
    "only two left": {deaths: {0: "N2", 1: "N2", 3: "N2", 4: "N2",
                               5: "N2", 6: "N2", 7: "N2"}},
  })) {
    const state = board(TB, TB9, opts);
    helpers.neighbours[name] = Object.fromEntries(
      [0, 2, 8].map(p => [p, livingNeighbours(state, 2, p)]));
  }
  const state = board(TB, TB9);
  const worlds = [];
  eachWorld(9, state.claims, {script: TB}, w => {
    worlds.push(w);
    return worlds.length < 3;
  });
  helpers.evilCounts = worlds.map(w => [
    [...possibleEvilCounts(w, [0, 1], "N1")].sort(),
    [...possibleEvilCounts(w, [7, 8], "N1")].sort(),
    [...possibleEvilCounts(w, [], "N1")].sort(),
  ]);
}

process.stdout.write(JSON.stringify(
  {readings, relaying, lives, helpers, waking}, null, 1) + "\n");
