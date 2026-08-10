// Every character the solver knows about, and what it knows about them.
//
// A character's team, its night schedule and how it misregisters belong
// to the character, not to the script it appears on. A *script* is only a
// selection. So the facts live here once, and `scripts.mjs` picks from
// them.
//
// The data comes from `characters.mjs`, generated out of the Python
// catalogue — see `tools/gen_characters.py`. Only the logic below is
// written twice.

import {DATA} from "./characters.mjs";

export const NEVER = "never";
export const FIRST = "first";
export const EVERY = "every";
export const OTHER = "other";
export const SOMETIMES = "sometimes";

export const WAKE_PATTERNS = DATA.wakePatterns;
export const WAKE_LABELS = DATA.wakeLabels;
export const SETUP = Object.fromEntries(
  Object.entries(DATA.setup).map(([n, counts]) => [Number(n), counts]));

// The same defaults the generator leaves out, put back. Keeping them in
// one place means a field added to the catalogue needs saying twice, not
// twelve times.
const DEFAULTS = {
  registers: [], setup: [], believes: false, believes_from: ["townsfolk"],
  modelled: true, note: "", chooses: false, alignment_open: false,
  nights: "never", seated: true,
};

export const CHARACTERS = Object.fromEntries(
  Object.entries(DATA.characters).map(([key, c]) =>
    [key, {key, ...DEFAULTS, ...c}]));

const BY_ID = Object.fromEntries(
  Object.values(CHARACTERS).map(c => [c.id, c]));

/** Turn anything a script might write into a catalogue id. */
export function normalise(name) {
  return String(name ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

/** Find a character by id, key or display name. Null if unknown. */
export function lookup(name) {
  const wanted = normalise(name);
  if (BY_ID[wanted]) return BY_ID[wanted];
  for (const c of Object.values(CHARACTERS))
    if (normalise(c.key) === wanted || normalise(c.name) === wanted) return c;
  return null;
}
