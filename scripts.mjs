// A script is a name and a selection of characters. That is all.
//
// The published scripts are two such selections, and there is no
// mechanism behind them that a homebrew script does not also get. Custom
// scripts are the general case.

import {CHARACTERS, SETUP, lookup, normalise} from "./catalogue.mjs";
import {DATA} from "./characters.mjs";

const TEAM_LIST = {
  townsfolk: "townsfolk", outsider: "outsiders",
  minion: "minions", demon: "demons",
};

export function makeScript(name, keys, author = "", unknown = []) {
  const by = team => keys.filter(k => CHARACTERS[k].team === team);
  const script = {
    name: name || "Untitled script",
    keys: [...keys],
    author,
    unknown: [...unknown],
    townsfolk: by("townsfolk"),
    outsiders: by("outsider"),
    minions: by("minion"),
    demons: by("demon"),
    // The characters that can actually be dealt to a seat. A Fabled is
    // put on the table by the Storyteller and held by nobody.
    seatedKeys: keys.filter(k => CHARACTERS[k].seated),
    fabled: keys.filter(k => !CHARACTERS[k].seated),
  };
  // Only the *dealt* characters move the bag here. The Fabled move it
  // too, but whether one is in play is told to the solver rather than
  // discovered by it.
  script.setupModifiers = Object.fromEntries(
    keys.filter(k => CHARACTERS[k].setup.length && CHARACTERS[k].seated)
        .map(k => [k, CHARACTERS[k].setup]));
  script.byTeam = team => script[TEAM_LIST[team]] || [];
  return script;
}

/** Build a script from whatever a file called its characters. */
export function fromIds(name, ids, author = "") {
  const keys = [], unknown = [];
  for (const entry of ids) {
    const found = lookup(entry);
    if (!found) unknown.push(String(entry));
    else if (!keys.includes(found.key)) keys.push(found.key);
  }
  return makeScript(name, keys, author, unknown);
}

/** Read the format Storytellers actually pass around.
 *
 * A list whose entries are either character ids as plain strings, or
 * objects with an `id`. One of those may be `_meta`, carrying the
 * script's name and author.
 */
export function fromJson(text, fallbackName = "Uploaded script") {
  let data = typeof text === "string" ? JSON.parse(text) : text;
  if (!Array.isArray(data))
    data = data.characters || data.roles || [];

  let name = fallbackName, author = "";
  const ids = [];
  for (const entry of data) {
    if (entry && typeof entry === "object") {
      if (normalise(entry.id || "") === "meta") {
        name = entry.name || name;
        author = entry.author || author;
        continue;
      }
      ids.push(entry.id || entry.name || "");
    } else ids.push(entry);
  }
  return fromIds(name, ids, author);
}

/** Which teams run out of characters at this table size. */
export function tooSmallFor(script, nPlayers) {
  if (!SETUP[nPlayers]) return [];
  const teams = ["townsfolk", "outsider", "minion", "demon"];
  const wanted = Object.fromEntries(
    teams.map((t, i) => [t, SETUP[nPlayers][i]]));
  // A setup-changer can only ever ask for more, so take the worst case.
  for (const shifts of Object.values(script.setupModifiers))
    for (const shift of shifts)
      for (const [team, delta] of Object.entries(shift))
        wanted[team] = Math.max(wanted[team], wanted[team] + delta);
  const short = [];
  for (const team of teams) {
    const have = script.byTeam(team).length;
    if (have < wanted[team]) short.push({team, need: wanted[team], have});
  }
  return short;
}

export const unmodelled = script =>
  script.keys.map(k => CHARACTERS[k]).filter(c => !c.modelled);

export const isPlayable = script =>
  !!(script.townsfolk.length && script.minions.length && script.demons.length);

/** Which of the chosen Fabled are actually on this script. */
export const fabledInPlay = (script, chosen) =>
  (chosen || []).filter(k => script.fabled.includes(k));

export const BUILT_IN = Object.fromEntries(
  Object.entries(DATA.scripts).map(([name, keys]) =>
    [name, makeScript(name, keys)]));

export const TROUBLE_BREWING = BUILT_IN["Trouble Brewing"];
export const BAD_MOON_RISING = BUILT_IN["Bad Moon Rising"];
export const DEFAULT = TROUBLE_BREWING;
