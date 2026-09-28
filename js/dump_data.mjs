// Everything the data layer derives, printed as JSON so the Python side
// can be held against it. Run by `tests/test_js_data.py`.
//
//     node js/dump_data.mjs
//
// The point is not that these numbers are interesting. It is that a
// second implementation agreeing on every one of them means the tables,
// the lookups and the derived facts all match — which is most of what
// could quietly go wrong in a port of this layer.

import {CHARACTERS, SETUP, lookup, normalise} from "./catalogue.mjs";
import * as scripts from "./scripts.mjs";
import * as roles from "./roles.mjs";

const sorted = xs => [...xs].sort();

function scriptFacts(script) {
  return {
    keys: script.keys,
    townsfolk: script.townsfolk,
    outsiders: script.outsiders,
    minions: script.minions,
    demons: script.demons,
    seated: script.seatedKeys,
    fabled: script.fabled,
    modifiers: Object.fromEntries(
      Object.entries(script.setupModifiers).map(([k, v]) => [k, v])),
    unmodelled: scripts.unmodelled(script).map(c => c.key),
    playable: scripts.isPlayable(script),
    tooSmall: Object.fromEntries([5, 7, 9, 12, 15].map(n =>
      [n, scripts.tooSmallFor(script, n)])),
    believedTokens: Object.fromEntries(
      script.keys.filter(k => roles.believesAnother(k))
                 .map(k => [k, roles.believedTokens(k, script)])),
  };
}

// A handful of scripts: the published ones, one built from a file, and
// one narrow enough that the "too small" check has something to say.
const uploaded = scripts.fromJson(JSON.stringify([
  {id: "_meta", name: "Easter Trouble", author: "AnqeR und Shellynax"},
  "noble", "washerwoman", "librarian", "clockmaker", "grandmother", "slayer",
  "artist", "empath", "fortuneteller", "monk", "undertaker", "ravenkeeper",
  "virgin", "mayor", "ogre", "saint", "recluse", "drunk", "poisoner", "spy",
  "scarletwoman", "marionette", "baron", "imp"]));

const narrow = scripts.fromIds("A narrow script", [
  "washerwoman", "librarian", "investigator", "chef", "empath",
  "recluse", "saint", "poisoner", "spy", "imp"]);

const withUnknown = scripts.fromIds("With a stranger", [
  "washerwoman", "imp", "poisoner", "cabbagemerchant"]);

const out = {
  characters: Object.fromEntries(Object.entries(CHARACTERS).map(([key, c]) =>
    [key, {
      id: c.id, name: c.name, team: c.team, wake: sorted(c.wake),
      registers: sorted(c.registers), setup: c.setup,
      believes: c.believes, believesFrom: c.believes_from,
      modelled: c.modelled, chooses: c.chooses,
      alignmentOpen: c.alignment_open, nights: c.nights, seated: c.seated,
      show: roles.show(key),
      isEvil: roles.isEvil(key), alignment: roles.alignment(key),
      believesAnother: roles.believesAnother(key),
      knowsWhatItIs: roles.knowsWhatItIs(key),
      thinksItIsEvil: roles.thinksItIsEvil(key),
      evilRegistrations: roles.evilRegistrations(key),
    }])),
  setup: Object.fromEntries(Object.entries(SETUP).map(([n, c]) => [n, c])),
  lookups: Object.fromEntries(
    ["fortuneteller", "Fortune Teller", "FortuneTeller", "FORTUNE TELLER",
     "scarlet woman", "scarletwoman", "devils advocate", "DevilsAdvocate",
     "tealady", "Tea Lady", "cabbage merchant", ""]
      .map(name => [name, lookup(name)?.key ?? null])),
  normalise: Object.fromEntries(
    ["Fortune Teller", "  Scarlet_Woman ", "Devil's Advocate", "Po"]
      .map(name => [name, normalise(name)])),
  registersAsRole: Object.fromEntries(
    [["Recluse", "Imp"], ["Recluse", "Monk"], ["Recluse", "Recluse"],
     ["Spy", "Monk"], ["Spy", "Imp"], ["Chef", "Chef"], ["Chef", "Imp"],
     ["Goon", "Imp"], ["Imp", "Nonexistent"]]
      .map(([a, b]) => [`${a} as ${b}`, roles.registersAsRole(a, b)])),
  wakeFits: Object.fromEntries(
    [["Empath", null, "every"], ["Empath", null, "never"],
     ["Drunk", "Empath", "every"], ["Drunk", "Empath", "never"],
     ["Imp", null, "first"], ["Chef", null, ""]]
      // "-" rather than the language's own word for nothing: Python
      // writes None and JavaScript writes null, and the labels have to
      // match for the comparison to mean anything.
      .map(([a, b, s]) => [`${a}/${b || "-"}/${s || "-"}`,
                           roles.wakeFits(a, b, s)])),
  scripts: {
    "Trouble Brewing": scriptFacts(scripts.TROUBLE_BREWING),
    "Bad Moon Rising": scriptFacts(scripts.BAD_MOON_RISING),
    "Easter Trouble": scriptFacts(uploaded),
    "A narrow script": scriptFacts(narrow),
  },
  uploaded: {name: uploaded.name, author: uploaded.author,
             unknown: uploaded.unknown},
  withUnknown: {unknown: withUnknown.unknown},
  fabledInPlay: {
    "TB asked for Sentinel":
      scripts.fabledInPlay(scripts.TROUBLE_BREWING, ["Sentinel"]),
    "TB+Sentinel asked for Sentinel": scripts.fabledInPlay(
      scripts.fromIds("x", [...scripts.TROUBLE_BREWING.keys, "sentinel"]),
      ["Sentinel"]),
  },
};

process.stdout.write(JSON.stringify(out, null, 1) + "\n");
