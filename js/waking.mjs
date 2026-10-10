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
  // `<` until 07.10.2026: on the night it chose it was asked whether the
  // *taken* character wakes, and one that took the Saint had not woken.
  if (phaseIndex(`N${night}`) <= phaseIndex(since)) return true;
  // Nothing to wake for, if what it took is no ability of its own: asked
  // anyway, the Lunatic's rule and this one called each other until the
  // stack ran out (07.10.2026).
  if (taken === "Philosopher" || CHARACTERS[taken].believes) return false;
  return wokeAs(world, state, seat, night, taken);
});

/** Answered on the night after the day it guessed, and never again. */
condition("Juggler", (world, state, seat, night) => night === 2);

/** Once a game, and the simulator spends it on the first night. */
condition("Seamstress", (world, state, seat, night) => night === 1);

/** Only if the Demon killed it tonight. */
condition("Sage", (world, state, seat, night) =>
  state.diedAt(seat).includes(`N${night}`));

// In this life: a Courtier that died and came back is a new one with the
// ability afresh (table ruling, 03.10.2026), so what counts is whether
// it has named anything since it last returned.
condition("Courtier", (world, state, seat, night) => {
  let born = 1;
  for (const at of (state.resurrections || {})[seat] || []) {
    const n = parseInt(String(at).slice(1), 10);
    if (n <= night && n > born) born = n;
  }
  for (const info of state.infos)
    if (info.sourceRole === "Courtier" && info.player === seat &&
        info.night >= born)
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
/** The night this seat said it used a once-a-game choice, or null.
 *
 * Its own row, not one somebody else filed about the same character: the
 * player a Nightwatchman woke speaks a row with that source too. */
function choseOn(state, seat, role) {
  for (const info of state.infos)
    if (info.sourceRole === role && info.player === seat && info.isAChoice)
      return info.night;
  return null;
}

/** Every night until it points at somebody, then never again. "Once per
 * game, at night" with no asterisk, so from the first. See waking.py. */
condition("Nightwatchman", (world, state, seat, night) => {
  const spent = choseOn(state, seat, "Nightwatchman");
  return spent === null || night <= spent;
});

/** Every night until it chooses, like the Nightwatchman (10.10.2026). */
condition("Huntsman", (world, state, seat, night) => {
  const spent = choseOn(state, seat, "Huntsman");
  return spent === null || night <= spent;
});

/** Who is alive when the King counts, which is late in the night.
 *
 * After tonight's deaths, and by what is so rather than by what the
 * board shows: a Zombuul that has died once is on the board as dead and
 * is not (table decisions, 05.10.2026). See info.py. */
export function reallyLiving(world, state, night) {
  const phase = `N${night}`;
  const living = new Set(state.aliveAt(phase)
    .filter(q => !state.diedAt(q).includes(phase)));
  if (state.script.keys.includes("Zombuul")) {
    const zombuul = world.findAt("Zombuul", phase);
    if (zombuul !== null && zombuul !== undefined && !living.has(zombuul)) {
      const now = phaseIndex(phase);
      const gone = state.diedAt(zombuul).filter(at => phaseIndex(at) <= now);
      if (gone.length === 1) living.add(zombuul);
    }
  }
  return living;
}

/** The King's condition, at the King's turn. */
export function theDeadOutnumberOrEqual(world, state, night) {
  const living = reallyLiving(world, state, night).size;
  return state.nPlayers - living >= living;
}

/** Only once the dead equal or outnumber the living. On the first night
 * the Demon is shown who the King is, which is not the King waking. */
condition("King", (world, state, seat, night) => {
  if (night < 2) return false;
  if (state.diedAt(seat).includes(`N${night}`)) return false;
  return theDeadOutnumberOrEqual(world, state, night);
});

/** Did another evil seat open its eyes tonight — [certain, maybe]?
 *
 * `certain` if one surely woke for its own ability, `maybe` if one's
 * waking is open (a Demon on the first night, an Exorcist's choice, an
 * Assassin that may have struck). Woken to be shown something counts
 * here, a Spy its grimoire: that is still somebody evil with their eyes
 * open, which is all a Wraith asks. */
function evilEyesOpen(world, state, seat, night) {
  const phase = `N${night}`;
  let certain = false, maybe = false;
  const poppy = world.findAt("PoppyGrower", phase);
  const poppyLives = poppy !== null && poppy !== undefined
    && state.aliveSet(phase).has(poppy);
  for (const other of state.aliveSet(phase)) {
    if (other === seat || !world.evilAt(other, phase)
        || world.roleAt(other, phase) === "Wraith") continue;
    // The Spy does not see the Grimoire while a Poppy Grower lives (their
    // jinx, as the table reads it: 08.10.2026), so it opens no eyes.
    if (poppyLives && world.roleAt(other, phase) === "Spy") continue;
    if (uncertain(world, state, other, night)) maybe = true;
    else if (woke(world, state, other, night)) certain = true;
  }
  return [certain, maybe];
}

/** Whenever another evil player wakes, the Wraith is woken first, and a
 * Chambermaid counts it (table ruling, 08.10.2026). Being shown your team
 * on the first night is nobody's ability. Drunk or poisoned it is *not*
 * woken (table ruling, 08.10.2026): this says what a sober one does, and
 * the Chambermaid's row asks the plan for the rest. */
condition("Wraith", (world, state, seat, night) =>
  evilEyesOpen(world, state, seat, night)[0]);

/** Only beside a Fearmonger: "the Vizier wakes with the Fearmonger"
 * (their jinx). Built for the Chambermaid; the rest is not (10.10.2026). */
condition("Vizier", (world, state, seat, night) => {
  const other = world.findAt("Fearmonger", `N${night}`);
  return other !== null && woke(world, state, other, night);
});

/** Woken only on a night the Demon killed the King; see `uncertain`. */
condition("Choirboy", () => false);

const aKingFell = (world, state, night) =>
  world.roles.some((_, seat) => state.diedAt(seat).includes(`N${night}`)
                   && world.roleAt(seat, `N${night}`) === "King");

/** On its first night as the Widow, to look and to choose. */
condition("Widow", (world, state, seat, night) =>
  night === 1 || world.roleAt(seat, `D${night - 1}`) !== "Widow");

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
  if (cameBackTonight(world, state, seat, night) === ASLEEP) return false;
  return wokeAs(world, state, seat, night, role);
}

const ASLEEP = "asleep", OPEN = "open";

/** A seat that returned to life this night: was its turn still to come?
 *
 * "They wake later tonight if they normally would." A Shabaloth
 * regurgitates just before its own turn and a Professor raises at its
 * own, so whoever came back was dead for every slot before that. An
 * Innkeeper at 9 slept through; a Chambermaid at 70 did not. Which of
 * the two did it is not written down: before both it was ASLEEP, after
 * both it woke as it normally would (null), between them OPEN. */
function cameBackTonight(world, state, seat, night) {
  const phase = `N${night}`;
  const back = (state.resurrections || {})[seat] || [];
  if (!back.includes(phase)) return null;
  const acting = actsAs(world, seat, phase);
  const slot = CHARACTERS[acting].other_night || 0;
  const raisers = ["Shabaloth", "Professor"]
    .filter(who => world.findAt(who, phase) !== null)
    .map(who => CHARACTERS[who].other_night || 0);
  if (!raisers.length || slot > Math.max(...raisers)) return null;
  return slot <= Math.min(...raisers) ? ASLEEP : OPEN;
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
  if (acting === "Choirboy")
    // Woken if the Demon killed the King tonight, and whose kill a King's
    // death was is not known here (10.10.2026).
    return state.aliveSet(phase).has(seat) && aKingFell(world, state, night);
  if (acting === "Wraith") {
    // Open exactly when no other evil seat surely woke and one may have —
    // a Demon on the first night is the usual one.
    if (!state.aliveSet(phase).has(seat)) return false;
    const [certain, maybe] = evilEyesOpen(world, state, seat, night);
    return maybe && !certain;
  }
  if (night === 1)
    return isDemon(acting) && CHARACTERS[acting].nights !== EVERY;
  if (cameBackTonight(world, state, seat, night) === OPEN) return true;
  if (acting === "Assassin") {
    // The same as the Professor below: woken until it strikes, and
    // nobody writes down when that was. Night two is certain — its first
    // chance — and after that either, unless the strike is on the record.
    if (night < 3 || !state.aliveSet(phase).has(seat)) return false;
    return !state.infos.some(
      info => info.sourceRole === "Assassin" && info.player === seat);
  }
  if (acting === "Huntsman") {
    // As the Nightwatchman. See waking.py.
    if (night < 2 || !state.aliveSet(phase).has(seat)) return false;
    return choseOn(state, seat, "Huntsman") === null;
  }
  if (acting === "Nightwatchman") {
    // The first night is certain. After that it may have chosen and
    // nobody wrote it down; its own row settles it either way.
    if (night < 2 || !state.aliveSet(phase).has(seat)) return false;
    return choseOn(state, seat, "Nightwatchman") === null;
  }
  if (acting === "Professor") {
    // Night two it is woken for certain: its first chance. After that it
    // may have chosen somebody who was no Townsfolk, or chosen while
    // drunk — nothing happens, the ability is gone, and nobody at the
    // table can see that it went. Only a return with no Shabaloth about
    // pins it: that was the Professor, awake until then and asleep after.
    if (night < 3 || !state.aliveSet(phase).has(seat)) return false;
    const raised = raisedOn(state);
    if (raised === null) return true;
    return world.findAt("Shabaloth", `N${raised}`) !== null;
  }
  if (!state.script.keys.includes("Exorcist")) return false;
  if (world.demonAt(phase) !== seat) return false;
  const exorcist = world.findAt("Exorcist", phase);
  return exorcist !== null && state.aliveSet(phase).has(exorcist);
}

/** Every value "how many of these woke" could have taken. */
// Woken to be *shown* something rather than to do anything.
//
// A Spy is shown the grimoire and an Evil Twin its twin. They wake, and
// none of it is their own ability working — the same reason a Baron being
// shown its team does not count.
//
// The Lunatic and the Marionette were on this list and came off it by
// table ruling (02.10.2026): both act, and only think they are somebody
// else while they do. A Marionette lives the nights of the token it was
// handed, so the Chambermaid gets the number that token gives — exactly
// as for the Drunk, which was never on the list.
export const SHOWN_NOT_ACTING = new Set(["Spy", "EvilTwin"]);

/** What a Chambermaid counts — narrower than `woke`. */
export function wokeForOwnAbility(world, state, seat, night) {
  if (!woke(world, state, seat, night)) return false;
  return !SHOWN_NOT_ACTING.has(world.roleAt(seat, `N${night}`));
}

/** `asleep` are seats taken as impaired tonight and so not woken — only
 * a Wraith changes by that (table ruling, 08.10.2026). */
export function possibleCounts(world, state, seats, night, asleep = null) {
  let fixed = 0, openEnded = 0;
  for (const seat of seats) {
    if (uncertain(world, state, seat, night)) openEnded += 1;
    else if (asleep && asleep.has(seat)) continue;
    else if (wokeForOwnAbility(world, state, seat, night)) fixed += 1;
  }
  const out = new Set();
  for (let extra = 0; extra <= openEnded; extra++) out.add(fixed + extra);
  return out;
}

/** The seats among these that are a Wraith a sober one would surely have
 * woken tonight — the ones whose impairment changes the count. */
export function wokenWraiths(world, state, seats, night) {
  const phase = `N${night}`;
  return new Set(seats.filter(seat =>
    actsAs(world, seat, phase) === "Wraith"
    && !uncertain(world, state, seat, night)
    && wokeForOwnAbility(world, state, seat, night)));
}
