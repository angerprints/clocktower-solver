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
//   * The Demon on the first night. It is woken to learn its Minions and
//     its bluffs, which is not its ability — the table's ruling
//     (02.10.2026); only the Pukka, which already chooses then, counts
//     for certain. Storytellers elsewhere do count it, so it is *open*:
//     both numbers stay legal and the true world survives either way.
//   * A Professor after somebody came back to life, when a Shabaloth is
//     about. Whichever of them did it is not written down.

import {CHARACTERS} from "./catalogue.mjs";
import {phaseIndex} from "./phases.mjs";

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

/** On the schedule of the Demon it thinks it is, and it counts.
 *
 * Being woken to choose who you think you kill is a Lunatic's ability
 * doing what it does (table ruling, 02.10.2026). So it wakes when that
 * Demon would; the first night is open the same way a real Demon's is.
 *
 * Missing entirely at first, and `nights === "conditional"` is checked
 * before the night-one branch — so a character without a rule here
 * silently never wakes at all.
 */
condition("Lunatic", (world, state, seat, night) =>
  wokeAs(world, state, seat, night, actsAs(world, seat, `N${night}`)));

/** The night it chooses, and thereafter on its gained schedule. */
//
// A Philosopher that took a character is that character, ability wise, so
// one that took the Clockmaker wakes on the first night and never again.
// This said "always" here while Python had the schedule — a Chambermaid
// beside one was read differently by the two (02.10.2026).
condition("Philosopher", (world, state, seat, night) => {
  const took = state.philosophies()[seat];
  if (!took) return true;
  const [taken, since] = took;
  if (phaseIndex(`N${night}`) < phaseIndex(since)) return true;
  return wokeAs(world, state, seat, night, taken);
});

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

/** The first night anybody came back to life, or null. */
function raisedOn(state) {
  let first = null;
  for (const phases of Object.values(state.resurrections || {}))
    for (const phase of phases) {
      if (String(phase)[0].toUpperCase() !== "N") continue;
      const n = parseInt(String(phase).slice(1), 10);
      if (first === null || n < first) first = n;
    }
  return first;
}

/** Every night but the first, until it has raised somebody.
 *
 * "Once per game, at night*": woken from the second night on and free
 * to decline, the same as an Assassin. This said *never*, which had a
 * Chambermaid beside an unspent Professor counting one where none was
 * allowed. With no Shabaloth about, somebody coming back to life was
 * the Professor, and it sleeps from then on; with one, see `uncertain`.
 */
condition("Professor", (world, state, seat, night) => {
  if (night === 1) return false;
  const raised = raisedOn(state);
  return raised === null || night <= raised;
});

/** The first night, and after a day an Outsider died.
 *
 * It learns the Outsiders on the first night, and after that is woken
 * only to kill — the same daylight condition the kill itself has.
 */
condition("Godfather", (world, state, seat, night) => {
  if (night === 1) return true;
  const day = `D${night - 1}`;
  for (const who of Object.keys(state.deaths || {}))
    if (state.diedAt(+who).includes(day) &&
        world.teamAt(+who, day) === "outsider") return true;
  return false;
});

/** Only on nights it can actually kill — which is nights after a day
 * when nobody died. */
condition("Zombuul", (world, state, seat, night) => {
  // On the first it is only told its Minions and its bluffs, like every
  // Demon but the Pukka. Whether that counts is open; see `uncertain`.
  if (night < 2) return false;
  for (const who of Object.keys(state.deaths || {}))
    if (state.diedAt(who).includes(`D${night - 1}`)) return false;
  return true;
});

/** Every night until it uses its one kill, then never again. */
// Every night but the first ("at night*") until it spends its kill.
condition("Assassin", (world, state, seat, night) => {
  if (night === 1) return false;
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

const isDemon = role => CHARACTERS[role].team === "demon";

/** Did somebody holding this character wake for it on this night?
 *
 * A Demon is the awkward case. Its `nights` says "other", because that
 * is when it *kills* — and on the first night it is woken to learn its
 * Minions and its bluffs. That is not its ability (table ruling,
 * 02.10.2026), so this says no; but it is not a settled no, and
 * `uncertain` keeps both counts legal. Only a Demon whose `nights` is
 * "every" — the Pukka — acts on the first night and counts outright.
 */
export function wokeAs(world, state, seat, night, role) {
  const when = CHARACTERS[role].nights;
  if (when === CONDITIONAL) {
    const rule = CONDITION_RULES[role];
    return rule ? !!rule(world, state, seat, night) : false;
  }
  if (when === NEVER) return false;
  if (night === 1) {
    // "every" includes the first night, and its wake set does not bother
    // to say so.
    if (when === EVERY) return true;
    // Being told who your Minions are is not your ability. A Baron says
    // "first night" honestly and has no night ability at all.
    if (isDemon(role)) return false;
    return (CHARACTERS[role].wake || []).includes(FIRST);
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

/** The character whose night this seat is living through. */
function actsAs(world, seat, phase) {
  const role = world.roleAt(seat, phase);
  if (role !== "Lunatic") return role;
  // The token it was shown — and when nobody recorded one, the Demon
  // that is really in play, which is what a Storyteller reaches for.
  if (world.believes[seat]) return world.believes[seat];
  const demon = world.demonAt(phase);
  return demon !== null && demon !== undefined
    ? world.roleAt(demon, phase) : "Imp";
}

/** Could this seat's waking have gone either way?
 *
 * Three things do this, and each is something nobody writes down: an
 * Exorcist sending the Demon to bed; the Demon on the first night, told
 * its Minions and bluffs (and a Lunatic that thinks it is that Demon);
 * and a Professor once somebody has come back to life with a Shabaloth
 * in play.
 */
export function uncertain(world, state, seat, night) {
  const phase = `N${night}`;
  const acting = actsAs(world, seat, phase);
  if (night === 1)
    return isDemon(acting) && CHARACTERS[acting].nights !== EVERY;
  if (acting === "Professor") {
    const raised = raisedOn(state);
    return raised !== null && night > raised &&
           state.aliveSet(phase).has(seat) &&
           world.findAt("Shabaloth", `N${raised}`) !== null;
  }
  if (!state.script.keys.includes("Exorcist")) return false;
  if (world.demonAt(phase) !== seat) return false;
  const exorcist = world.findAt("Exorcist", phase);
  return exorcist !== null && state.aliveSet(phase).has(exorcist);
}

/** Every value "how many of these woke" could have taken. */
// Woken to be *shown* something rather than to do anything.
//
// A Spy is shown the grimoire, an Evil Twin its twin, a Marionette a good
// character's night. They wake, and none of it is their own ability
// working — the same reason a Baron being shown its team does not count.
//
// The Lunatic was on this list while its rule said it counts, and the
// list won. The table ruled that it does count (02.10.2026).
export const SHOWN_NOT_ACTING = new Set(["Spy", "EvilTwin", "Marionette"]);

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
