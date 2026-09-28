// Characters this solver cannot honestly reason about.
//
// Everything else rests on two assumptions, and a handful of characters
// take one of them away: that the bag is known, and that the teams are
// the usual size. A character that breaks either does not make the solver
// slightly less accurate — it makes the whole world set wrong, quietly,
// while the output looks exactly as confident as ever.
//
// Two kinds, needing different handling. One breaks the *bag*, so no
// legal world exists to find — that has a visible signature, a board that
// fits nothing, and saying so is more use than saying nothing. The other
// breaks the *teams*, and has no signature at all: the board looks
// perfectly solvable and every number is wrong. There is nothing to
// detect, so the only honest thing is to refuse before starting.
//
// The table below is generated from `botc/limits.py` by
// `tools/gen_limits.py`, because the wording is the whole point of it and
// two copies would drift.

export const BREAKS_THE_BAG = "breaks the bag";
export const BREAKS_THE_TEAMS = "breaks the teams";

export const UNSUPPORTED = {
 "Atheist": {
  "kind": "breaks the bag",
  "short": "the Storyteller may have broken the rules",
  "why": "With an Atheist in play the Storyteller is allowed to break the rules, and there may be no evil players at all. Nothing the solver enumerates is a legal world, so there is no honest answer to give.",
  "signal": "A board that fits nothing is the signature. It is not proof — a mis-entered reading or a good player lying does the same thing — but it is worth raising."
 },
 "Legion": {
  "kind": "breaks the teams",
  "short": "most of the table is evil",
  "why": "Legion replaces the usual one-Demon-and-some-Minions split with most of the table being evil Demons. Every count the search prunes on is wrong, and nothing about the board would look unusual.",
  "signal": null
 },
 "Riot": {
  "kind": "breaks the teams",
  "short": "every Minion is a Demon",
  "why": "Riot turns every Minion into a Demon and rewrites how days work. The team counts and the death rules both stop holding.",
  "signal": null
 }
};

/** Which named characters on this script the solver cannot handle. */
export function unsupportedOn(script) {
  const keys = new Set(script.keys || script);
  const out = {};
  for (const [name, entry] of Object.entries(UNSUPPORTED))
    if (keys.has(name)) out[name] = entry;
  return out;
}

/** Characters that make solving dishonest before it even starts. */
export function refuses(script) {
  const out = {};
  for (const [name, entry] of Object.entries(unsupportedOn(script)))
    if (entry.kind === BREAKS_THE_TEAMS) out[name] = entry;
  return out;
}

/** Characters whose signature is a board that fits no world at all. */
export function couldExplainNothingFitting(script) {
  const out = {};
  for (const [name, entry] of Object.entries(unsupportedOn(script)))
    if (entry.kind === BREAKS_THE_BAG) out[name] = entry;
  return out;
}
