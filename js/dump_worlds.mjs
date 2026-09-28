// Enumerate worlds for a set of boards and print what came out, so the
// Python side can be held against it.
//
//     node js/dump_worlds.mjs
//
// A count alone would not be enough: two implementations can produce the
// same number of worlds and disagree about which ones. So each board also
// gets a digest over the whole sorted set — every seat's character and
// every believer's token — which only matches if the sets are identical.

import {createHash} from "node:crypto";
import * as scripts from "./scripts.mjs";
import {Timeline, World, bags, candidates, change, eachWorld,
        OffScript} from "./worlds.mjs";

const TB = scripts.TROUBLE_BREWING;
const BMR = scripts.BAD_MOON_RISING;

const TB15 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
  "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin", "Slayer",
  "Soldier", "Mayor", "Recluse", "Saint"];
const BMR15 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
  "Innkeeper", "Gambler", "Gossip", "Courtier", "Professor", "Minstrel",
  "TeaLady", "Pacifist", "Fool", "Tinker", "Moonchild"];

const claimsFrom = list =>
  Object.fromEntries(list.map((role, i) => [i, role]));

/** Count, and a digest that only matches if the world sets are the same. */
function enumerated(nPlayers, claims, opts) {
  const lines = [];
  try {
    eachWorld(nPlayers, claims, opts, world => {
      lines.push(world.roles.map(
        (r, i) => world.believes[i] ? `${r}/${world.believes[i]}` : r).join(","));
      // No cap in practice: a truncated set would depend on the order
      // worlds came out in, and the digest is meant to depend only on
      // *which* worlds there are.
      return lines.length < 600_000;
    });
  } catch (err) {
    if (err instanceof OffScript) return {error: err.message};
    throw err;
  }
  lines.sort();
  return {
    count: lines.length,
    digest: createHash("sha256").update(lines.join("\n")).digest("hex")
                                .slice(0, 16),
  };
}

const boards = {};
const add = (name, n, claims, opts = {}) =>
  (boards[name] = enumerated(n, claimsFrom(claims), opts));

// --- plain boards, both scripts, several sizes ----------------------
for (const n of [5, 6, 7, 8, 9, 10, 12, 15])
  add(`tb-${n}`, n, TB15.slice(0, n), {script: TB});
// Bad Moon Rising stops at twelve: fifteen seats is nine million worlds,
// which is a fine thing to time and a poor thing to digest.
for (const n of [5, 6, 7, 8, 9, 10, 12])
  add(`bmr-${n}`, n, BMR15.slice(0, n), {script: BMR});

// --- claims of every kind -------------------------------------------
add("tb-9-outsider-claims", 9,
    ["Washerwoman", "Librarian", "Butler", "Drunk", "Empath",
     "FortuneTeller", "Undertaker", "Recluse", "Saint"], {script: TB});
add("tb-9-evil-claim", 9,
    ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
     "FortuneTeller", "Undertaker", "Recluse", "Imp"], {script: TB});
add("tb-9-some-unclaimed", 9,
    ["Washerwoman", "", "Investigator", "", "Empath", "", "Undertaker",
     "Recluse", "Saint"], {script: TB});
add("tb-9-off-script", 9,
    ["Grandmother", "Librarian", "Investigator", "Chef", "Empath",
     "FortuneTeller", "Undertaker", "Recluse", "Saint"], {script: TB});

// --- certainties -----------------------------------------------------
for (const kind of ["self", "confirmed", "hiding", "unsure"])
  add(`tb-9-certainty-${kind}`, 9, TB15.slice(0, 9),
      {script: TB, certainties: {0: kind, 4: kind}});

// --- good lies -------------------------------------------------------
add("tb-9-good-lies", 9, TB15.slice(0, 9),
    {script: TB, allowGoodLies: true});

// --- wake claims -----------------------------------------------------
for (const said of ["never", "first", "every", "other", "sometimes"])
  add(`tb-9-wake-${said}`, 9,
      ["", "Librarian", "Investigator", "Chef", "Empath", "FortuneTeller",
       "Undertaker", "Recluse", "Saint"],
      {script: TB, wakes: {0: said}});

// --- forced roles ----------------------------------------------------
add("tb-9-forced", 9, TB15.slice(0, 9),
    {script: TB, forced: {2: new Set(["Investigator", "Drunk"])}});

// --- the Fabled ------------------------------------------------------
const sentinel = scripts.fromIds("TB and a Sentinel",
  [...TB.keys, "sentinel"]);
add("tb-9-sentinel", 9, TB15.slice(0, 9),
    {script: sentinel, fabled: ["Sentinel"]});
add("tb-9-sentinel-not-asked", 9, TB15.slice(0, 9), {script: sentinel});

// --- custom scripts --------------------------------------------------
const easter = scripts.fromJson(JSON.stringify([
  {id: "_meta", name: "Easter Trouble"},
  "noble", "washerwoman", "librarian", "clockmaker", "grandmother", "slayer",
  "artist", "empath", "fortuneteller", "monk", "undertaker", "ravenkeeper",
  "virgin", "mayor", "ogre", "saint", "recluse", "drunk", "poisoner", "spy",
  "scarletwoman", "marionette", "baron", "imp"]));
add("easter-9", 9,
    ["Noble", "Washerwoman", "Clockmaker", "Grandmother", "Artist", "Empath",
     "Monk", "Ogre", "Saint"], {script: easter});
add("easter-12", 12,
    ["Noble", "Washerwoman", "Clockmaker", "Grandmother", "Artist", "Empath",
     "Monk", "Undertaker", "Virgin", "Mayor", "Ogre", "Saint"],
    {script: easter});

const narrow = scripts.fromIds("A narrow script", [
  "washerwoman", "librarian", "investigator", "chef", "empath",
  "recluse", "saint", "poisoner", "spy", "imp"]);
add("narrow-7", 7,
    ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
     "Recluse", "Saint"], {script: narrow});

// --- the bag itself --------------------------------------------------
const bagShapes = {};
for (const [tag, script, fabled] of [["tb", TB, []], ["bmr", BMR, []],
                                     ["tb-sentinel", sentinel, ["Sentinel"]],
                                     ["easter", easter, []]])
  for (const n of [5, 7, 9, 12, 15])
    bagShapes[`${tag}-${n}`] = bags(n, script, fabled)
      .map(([present, counts]) =>
        [[...present].sort(), ["townsfolk", "outsider", "minion", "demon"]
          .map(t => counts[t])]);

// --- candidate lists, spot-checked -----------------------------------
const candidateLists = {};
for (const [tag, claim, opts] of [
  ["tb-townsfolk", "Empath", {}],
  ["tb-outsider", "Recluse", {}],
  ["tb-drunk-claim", "Drunk", {}],
  ["tb-evil-claim", "Imp", {}],
  ["tb-unclaimed", null, {}],
  ["tb-good-lies", "Empath", {allowGoodLies: true}],
  ["tb-self", "Empath", {certainty: "self"}],
  ["tb-confirmed", "Empath", {certainty: "confirmed"}],
  ["bmr-townsfolk", "Chambermaid", {script: BMR}],
  ["bmr-lunatic-bluff", "Grandmother", {script: BMR}],
]) {
  const script = opts.script || TB;
  candidateLists[tag] = candidates(
    claim, opts.allowGoodLies || false, opts.certainty || "", null, null,
    script).map(([r, b]) => (b ? `${r}/${b}` : r)).sort();
}

// --- a timeline over a world -----------------------------------------
const base = new World(
  ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
   "FortuneTeller", "Undertaker", "ScarletWoman", "Imp"],
  new Array(9).fill(null));
const handover = new Timeline(base, [change("D2", 7, "Imp")]);
const timeline = {
  "before: demon": base.demonAt("N2"),
  "after: demon at N2": handover.demonAt("N2"),
  "after: demon at N3": handover.demonAt("N3"),
  "after: seat 8 at N2": handover.roleAt(7, "N2"),
  "after: seat 8 at N3": handover.roleAt(7, "N3"),
  "after: seat 8 evil at N1": handover.evilAt(7, "N1"),
  "after: find Imp at N2": handover.findAt("Imp", "N2"),
  "after: find Imp at N3": handover.findAt("Imp", "N3"),
  "after: team of seat 8 at N3": handover.teamAt(7, "N3"),
};

process.stdout.write(JSON.stringify(
  {boards, bagShapes, candidateLists, timeline}, null, 1) + "\n");
