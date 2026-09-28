// Who was actually woken on a given night, for their own ability.
//
// Not the same question the wake table answers. That one is forgiving on
// purpose: it records what a holder could *honestly claim*, and a
// Courtier's honest answer depends on when they spent their ability. The
// Chambermaid needs the fact, and the fact depends on the board — a
// Ravenkeeper wakes only on the night it dies, an Undertaker only after
// an execution killed somebody, a Courtier only until it has named a
// character.
//
// Two things make the answer uncertain rather than merely unknown, and
// both are handled by returning the *set* of counts a reading could have
// taken rather than a single number:
//
//   * The Exorcist. A Demon it chose does not wake for its own ability
//     that night — it is woken to be told who the Exorcist is, which is
//     not the same thing. Nobody records who the Exorcist picked, so with
//     one in play the Demon's waking is genuinely open.
//   * Anybody impaired still wakes. Being drunk or poisoned does not let
//     you sleep through the night; the Storyteller wakes you and makes an
//     answer up. So impairment never changes this count.

import {CHARACTERS} from "./catalogue.mjs";

export const NEVER = "never";
export const FIRST = "first";
export const EVERY = "every";
export const OTHER = "other";
export const CONDITIONAL = "conditional";

export const CONDITION_RULES = {};

/** Register how to tell whether a character woke on a given night. */
const condition = (key, fn) => (CONDITION_RULES[key] = fn);

/** Only on the night it dies, and it does wake then. */
condition("Ravenkeeper", (world, state, seat, night) =>
  state.diedAt(seat).includes(`N${night}`));

/** Only when yesterday's execution actually killed somebody. */
condition("Undertaker", (world, state, seat, night) =>
  night >= 2 && state.executionDeath(night - 1) !== null);

/** Woken when she becomes the Demon, and not otherwise.
 *
 * The first night she is woken to be shown the Demon, which is not her
 * own ability and does not count.
 */
condition("ScarletWoman", (world, state, seat, night) =>
  world.demonAt(`N${night}`) === seat && world.demonAt("N1") !== seat);

/** Every night until it names a character, then never again. */
/** Every night, believing it is the Demon.
 *
 * Missing entirely, and `nights === "conditional"` is checked before the
 * night-one branch — so a character without a rule here silently never
 * wakes at all. Found by a Chambermaid counting two where the solver
 * could only reach one.
 */
condition("Lunatic", () => true);

/** The night it chooses, and thereafter on its gained schedule. */
condition("Philosopher", () => true);

/** Answered on the night after the day it guessed, and never again. */
condition("Juggler", (world, state, seat, night) => night === 2);

/** Once a game, and the simulator spends it on the first night. */
condition("Seamstress", (world, state, seat, night) => night === 1);

/** Only if the Demon killed it tonight. */
condition("Sage", (world, state, seat, night) =>
  state.diedAt(seat).includes(`N${night}`));

condition("Courtier", (world, state, seat, night) => {
  for (const info of state.infos)
    if (info.sourceRole === "Courtier" && info.player === seat)
      return night <= info.night;
  return true;                       // never spent, so still being woken
});

/** From the second night until it raises somebody. */
/** Once a game, so only on the night it spends it.
 *
 * Returning true every night had a Chambermaid counting a Professor that
 * had raised nobody. Nothing on the record says which night it used, so
 * this says no unless something else does — which keeps the count honest
 * rather than inventing a wake.
 */
condition("Professor", () => false);

/** Only on nights it can actually kill — which is nights after a day
 * when nobody died. */
condition("Zombuul", (world, state, seat, night) => {
  // Except the first night, when it wakes like every other Demon to
  // learn its Minions and its bluffs. The killing schedule is a separate
  // question from the waking one.
  if (night === 1) return true;
  if (night < 2) return false;
  for (const who of Object.keys(state.deaths || {}))
    if (state.diedAt(who).includes(`D${night - 1}`)) return false;
  return true;
});

/** Every night until it uses its one kill, then never again. */
condition("Assassin", (world, state, seat, night) => {
  for (const info of state.infos)
    if (info.sourceRole === "Assassin" && info.player === seat)
      return night <= info.night;
  return true;
});

/** Woken on the schedule of whatever they think they are. */
const believer = (world, state, seat, night) => {
  const token = world.believes[seat];
  return token ? wokeAs(world, state, seat, night, token) : false;
};
condition("Drunk", believer);
condition("Marionette", believer);

/** Did somebody holding this character wake for it on this night?
 *
 * A Demon is the awkward case. Its `nights` says "other", because that
 * is when it *kills* — but it also wakes on the first night to learn its
 * Minions and its bluffs, and a Chambermaid sitting beside one counts
 * that. Reading the single word said every Demon slept through night
 * one, which made a Chambermaid who correctly counted two into a board
 * with no legal world at all.
 *
 * The `wake` set is the honest answer, except that "every" does not
 * bother to list "first" — so that is checked separately, or every
 * Empath and Poisoner sleeps through night one instead.
 */
export function wokeAs(world, state, seat, night, role) {
  const when = CHARACTERS[role].nights;
  if (when === CONDITIONAL) {
    const rule = CONDITION_RULES[role];
    return rule ? !!rule(world, state, seat, night) : false;
  }
  if (when === NEVER) return false;
  if (night === 1) {
    // Being shown the other evil players is not waking for your own
    // ability, so a Chambermaid does not count it. A Baron says "first
    // night" honestly — its `wake` set is what a player could truthfully
    // claim — and yet it has no night ability at all.
    if (when === NEVER) return false;
    return when === EVERY || (CHARACTERS[role].wake || []).includes(FIRST);
  }
  if (when === FIRST) return false;
  return true;                                   // "other" and "every"
}

/** Did this seat wake for its own ability on this night?
 *
 * The dead do not wake — except the Ravenkeeper, whose whole ability is
 * waking as it goes.
 */
export function woke(world, state, seat, night) {
  const phase = `N${night}`;
  const role = world.roleAt(seat, phase);
  if (!state.aliveSet(phase).has(seat) && role !== "Ravenkeeper") return false;
  return wokeAs(world, state, seat, night, role);
}

/** Could this seat's waking have gone either way?
 *
 * Only one thing does this: an Exorcist sending the Demon to bed. It is a
 * choice nobody writes down, so with one in play the Demon's waking is
 * genuinely open rather than merely unrecorded.
 */
export function uncertain(world, state, seat, night) {
  if (night < 2 || !state.script.keys.includes("Exorcist")) return false;
  const phase = `N${night}`;
  if (world.demonAt(phase) !== seat) return false;
  const exorcist = world.findAt("Exorcist", phase);
  return exorcist !== null && state.aliveSet(phase).has(exorcist);
}

/** Every value "how many of these woke" could have taken. */
// Woken to be *told* something rather than to do anything.
//
// A Lunatic is shown a Demon's night and made to choose victims who never
// die — it wakes, and none of it is its own ability working. A
// Chambermaid does not count it, for the same reason it does not count a
// Baron being shown the other evil players.
//
// `woke` answers two questions at once: *did this seat wake*, which
// decides what a player could honestly claim, and *did its own ability
// fire*, which is what a Chambermaid asks. They agree for almost every
// character, which is why the difference went unnoticed.
export const SHOWN_NOT_ACTING = new Set(
  ["Lunatic", "Spy", "EvilTwin", "Marionette"]);

/** What a Chambermaid counts — narrower than `woke`. */
export function wokeForOwnAbility(world, state, seat, night) {
  if (!woke(world, state, seat, night)) return false;
  return !SHOWN_NOT_ACTING.has(world.roleAt(seat, `N${night}`));
}

export function possibleCounts(world, state, seats, night) {
  let fixed = 0, openEnded = 0;
  for (const seat of seats) {
    if (uncertain(world, state, seat, night)) openEnded += 1;
    else if (wokeForOwnAbility(world, state, seat, night)) fixed += 1;
  }
  const out = new Set();
  for (let extra = 0; extra <= openEnded; extra++) out.add(fixed + extra);
  return out;
}
