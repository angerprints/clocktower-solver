// Every character rule, asked about every world of a board on every
// night, with the answers digested.
//
//     node js/dump_characters.mjs
//
// The rules are small and there are thirty-two of them, so spot-checking
// a few would leave most of the port unexamined. Instead each board is
// walked world by world and night by night, and what comes out — which
// causes were offered, which shields, which sources, what each one
// reaches and costs — is folded into one digest per board.
//
// A digest matches only if the two implementations agreed about every
// rule in every world. It says nothing about *where* they differ, so the
// per-rule tallies beside it are there to narrow a failure down.

import {createHash} from "node:crypto";
import "./characters.rules.mjs";        // registers everything
import {DEMON, OTHER, CAUSE_RULES, IMMUNITY_RULES, IMPLICATION_RULES,
        causesOn, implicationsOf, shieldsOn} from "./deaths.mjs";
import {SOURCE_RULES, sourcesOn} from "./impairment.mjs";
import {SURVIVES_EXECUTION_RULES, survivalsOf}
  from "./characters.rules.mjs";
import {makeInfo} from "./info.mjs";
import * as scripts from "./scripts.mjs";
import {GameState} from "./state.mjs";
import {eachWorld} from "./worlds.mjs";

const TB = scripts.TROUBLE_BREWING;
const BMR = scripts.BAD_MOON_RISING;

const TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"];
const TB12 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
              "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Slayer",
              "Soldier", "Saint"];
const BMR9 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
              "Innkeeper", "Gambler", "Gossip", "Tinker", "Moonchild"];
const BMR9B = ["Courtier", "Professor", "Minstrel", "TeaLady", "Pacifist",
               "Fool", "Sailor", "Goon", "Lunatic"];

const seats = list => Object.fromEntries(list.map((r, i) => [i, r]));

const sortNums = s => [...s].sort((a, b) => a - b);

/** Everything the rules say about one world, as text. */
function describe(world, state, nights) {
  const lines = [];
  for (const night of nights) {
    for (const c of causesOn(world, state, night))
      lines.push(`cause ${night} ${c.name} ${c.kind} ${c.capacity} ` +
                 `${c.cost.toFixed(6)} ${c.mustFire} ${c.unstoppable} ` +
                 `${c.victimImpairedAt} [${sortNums(c.seats)}]`);
    for (const s of sourcesOn(world, state, night)) {
      const prices = sortNums(s.seats)
        .map(seat => `${seat}:${s.price(seat).toFixed(6)}` +
                     `/${s.price(seat, true).toFixed(6)}`);
      lines.push(`source ${night} ${s.name} ${s.capacity} [${prices}]`);
    }
    for (let seat = 0; seat < state.nPlayers; seat++) {
      for (const kind of [DEMON, OTHER]) {
        for (const sh of shieldsOn(world, state, night, seat, kind))
          lines.push(`shield ${night} ${seat} ${kind} ${sh.by} ` +
                     `${sh.needs} ${sh.cost.toFixed(6)} ${sh.chosen}`);
        for (const hit of implicationsOf(world, state, night, seat, kind))
          lines.push(`implies ${night} ${seat} ${kind} ` +
                     `${hit.seat} ${hit.needs}`);
      }
      for (const day of nights)
        for (const who of survivalsOf(world, state, day, seat))
          lines.push(`survives ${day} ${seat} ${who}`);
    }
  }
  return lines;
}

const boards = {};

function run(name, script, claims, opts = {}, nights = [1, 2, 3, 4]) {
  const state = new GameState({
    nPlayers: claims.length, script, claims: seats(claims),
    ...opts,
    infos: (opts.infos || []).map(makeInfo),
  });
  const hash = createHash("sha256");
  const tally = {};
  let worlds = 0;
  eachWorld(claims.length, state.claims, {script}, world => {
    worlds += 1;
    const lines = describe(world, state, nights);
    hash.update(lines.join("\n"));
    hash.update("\u0000");
    for (const line of lines) {
      const key = line.split(" ").slice(0, 1)
        .concat(line.split(" ")[2] || "").join(" ");
      tally[key] = (tally[key] || 0) + 1;
    }
    return worlds < 4000;
  });
  boards[name] = {worlds, digest: hash.digest("hex").slice(0, 16), tally};
}

// --- Trouble Brewing -------------------------------------------------
run("tb-9-bare", TB, TB9);
run("tb-9-a-death", TB, TB9, {deaths: {2: "N2"}});
run("tb-9-quiet", TB, TB9, {quietNights: [2]});
run("tb-9-execution", TB, TB9, {deaths: {7: "E1"}});
run("tb-12-protectors", TB, TB12, {deaths: {2: "N2"}});
run("tb-12-two-deaths", TB, TB12, {deaths: {2: "N2", 4: "N3"}});

// --- Bad Moon Rising, first half -------------------------------------
run("bmr-9-bare", BMR, BMR9);
run("bmr-9-a-death", BMR, BMR9, {deaths: {2: "N2"}});
run("bmr-9-day-death", BMR, BMR9, {deaths: {7: "D2"}});
run("bmr-9-execution", BMR, BMR9, {deaths: {7: "E2"}});
run("bmr-9-moonchild-gone", BMR, BMR9, {deaths: {8: "N2"}});
run("bmr-9-gambler-guessed", BMR, BMR9, {
  infos: [{type: "GamblerGuess", night: 2, player: 5, target: 2,
           role: "Chambermaid"}]});
run("bmr-9-grandmother", BMR, BMR9, {
  deaths: {2: "N2"},
  infos: [{type: "GrandmotherInfo", night: 1, player: 0, target: 2,
           role: "Chambermaid"}]});

// --- Bad Moon Rising, the other half ---------------------------------
run("bmr-9b-bare", BMR, BMR9B);
run("bmr-9b-courtier", BMR, BMR9B, {
  infos: [{type: "CourtierChoice", night: 1, player: 0,
           role: "Chambermaid"}]});
run("bmr-9b-minion-executed", BMR, BMR9B, {deaths: {7: "E1"}});
run("bmr-9b-survived-execution", BMR, BMR9B, {executions: {1: 6}});
run("bmr-9b-a-death", BMR, BMR9B, {deaths: {3: "N2"}});

// Two boards aimed at rules the ones above never reach. The Godfather is
// claimed outright, which pins it to a seat in every world — otherwise it
// sits past the four-thousand-world cap and the rule looks untested. And
// the Courtier names a character somebody actually holds, since naming
// one nobody holds correctly does nothing at all.
run("bmr-9-godfather-claimed", BMR,
    ["Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
     "Gambler", "Godfather", "Tinker", "Moonchild"],
    {deaths: {7: "D2"}});
run("bmr-9b-courtier-lands", BMR, BMR9B, {
  infos: [{type: "CourtierChoice", night: 1, player: 0, role: "Sailor"}]});
// And a Minion that owns up and hangs. The Minstrel sings only when the
// one executed *died* and was a Minion, and on the boards above the first
// four thousand worlds never put a Minion in that seat.
run("bmr-9b-assassin-hanged", BMR,
    [...BMR9B.slice(0, 6), "Assassin", ...BMR9B.slice(7)],
    {deaths: {6: "E1"}});

// --- what is registered ----------------------------------------------
const registry = {
  causes: CAUSE_RULES.map(f => f.name),
  shields: IMMUNITY_RULES.map(f => f.name),
  implications: IMPLICATION_RULES.map(f => f.name),
  sources: SOURCE_RULES.map(f => f.name),
  survivals: SURVIVES_EXECUTION_RULES.map(f => f.name),
};

process.stdout.write(JSON.stringify({boards, registry}, null, 1) + "\n");
