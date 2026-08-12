// Facts about characters, derived from the catalogue.
//
// Team is a property of the character rather than of the script, so it
// covers everything the catalogue knows. Only the *lists* — which
// Townsfolk, which Outsiders — belong to a script.

import {CHARACTERS} from "./catalogue.mjs";

export const GOOD = "good";
export const EVIL = "evil";

export const TEAM = Object.fromEntries(
  Object.entries(CHARACTERS).map(([key, c]) => [key, c.team]));

export const WAKE = Object.fromEntries(
  Object.entries(CHARACTERS).map(([key, c]) => [key, c.wake]));

/** Human readable character name. */
export const show = role => (role ? CHARACTERS[role]?.name ?? role : "-");

/** Actual team membership — not how a character *registers*. */
export const isEvil = role =>
  TEAM[role] === "minion" || TEAM[role] === "demon";

/** Which side this character starts on.
 *
 * Kept apart from the character itself because the two come apart: an
 * Ogre turns evil without changing character.
 */
export const alignment = role => (isEvil(role) ? EVIL : GOOD);

/** Does whoever holds this think they are somebody else?
 *
 * The Drunk, and elsewhere the Marionette and the Lunatic. They are woken
 * on the schedule of the character they were handed and given answers to
 * match, so nothing they say is a lie.
 */
export const believesAnother = role => CHARACTERS[role].believes;

/** Can this seat's holder be relied on to know their own character?
 *
 * The distinction matters more than "is it evil". A knowing bluffer says
 * whatever suits them, so nothing they claim constrains anything.
 * Somebody handed the wrong token says what they honestly believe — and
 * that *does* constrain, against the token rather than against the truth.
 */
export const knowsWhatItIs = role => !CHARACTERS[role].believes;

/** Does the holder believe they are on the evil team?
 *
 * A Lunatic does, so it bluffs the way the Demon would — which makes it a
 * good player who lies deliberately, and the only one.
 */
export const thinksItIsEvil = role =>
  CHARACTERS[role].believes &&
  CHARACTERS[role].believes_from.some(t => t === "minion" || t === "demon");

/** Which characters this one could have been handed to believe in.
 *
 * Empty for everybody who knows what they are.
 */
export function believedTokens(role, script) {
  const c = CHARACTERS[role];
  if (!c.believes) return [];
  const out = [];
  for (const team of c.believes_from)
    for (const key of script.byTeam(team))
      if (!CHARACTERS[key].believes && !out.includes(key)) out.push(key);
  return out;
}

/** What can this character register as, for information purposes?
 *
 * Returns the possible values for "is evil". A character that may
 * register as a team on the other side is ambiguous, and the Storyteller
 * decides which — so both values stay possible.
 *
 * `side` overrides where the seat currently stands, for the characters
 * that can be turned. A turned Recluse is still ambiguous, because the
 * misregistration belongs to the character and not to the side.
 */
export function evilRegistrations(role, side = null) {
  const c = CHARACTERS[role];
  const mine = side !== null ? side === EVIL : isEvil(role);
  // A Goon really is on whichever side last claimed it, and nobody writes
  // down who chose it, so both are live. Not misregistration: it changes
  // which team they are on, not merely how they read.
  if (c.alignment_open) return [true, false];
  if (!c.registers.length) return [mine];
  const seen = new Set([mine]);
  for (const team of c.registers)
    seen.add(team === "minion" || team === "demon");
  return [...seen].sort((a, b) => Number(b) - Number(a));
}

/** Can `actual` show up as `claimed` in character information? */
export function registersAsRole(actual, claimed) {
  if (actual === claimed) return true;
  if (!TEAM[claimed]) return false;
  return CHARACTERS[actual].registers.includes(TEAM[claimed]);
}

/** Could a seat holding this character honestly describe waking so?
 *
 * Whoever believes they are somebody else experiences that character's
 * schedule, so that is what gets checked for them.
 */
export function wakeFits(actual, believed, said) {
  if (!said) return true;
  const apparent = believed || actual;
  return (WAKE[apparent] || []).includes(said);
}

// How much weight can be put on what a seat produced. Three-valued
// rather than a boolean, because "sober and healthy" stops being a
// yes-or-no question once a script can invert information.
export const GENUINE = "genuine";
export const ARBITRARY = "arbitrary";
export const INVERTED = "inverted";
export const ABSENT = "absent";

/** Poison is not decided here. The solver posits a poisoning only when a
 * statement would otherwise be false, which cannot be known until the
 * statement has been checked — so a poisoned seat looks GENUINE at this
 * point and is excused afterwards.
 */
export function abilityState(world, seat, role, phase, gained = null,
                             vortoxed = false) {
  if (world.roleAt(seat, phase) === role) {
    // A Vortox does not droison anybody: abilities work, and what they
    // *yield* is false. Not a weaker GENUINE but a stronger one — a
    // poisoned Empath may be told anything, a Vortox'd one must be told
    // something that is not so.
    //
    // Read off what the seat *is*: a Drunk holding a Townsfolk token is
    // an Outsider, so a Vortox leaves it alone.
    if (vortoxed && TEAM[role] === "townsfolk") return INVERTED;
    return GENUINE;
  }
  if (believesAnother(world.roleAt(seat, phase)) &&
      world.believes[seat] === role) return ARBITRARY;
  // A Philosopher keeps its own character and gains another's ability,
  // so a seat can be working two at once. `gained` is
  // (role, from, has-it-arrived) for that seat.
  if (gained !== null) {
    const [taken, , arrived] = gained;
    if (taken === role && arrived &&
        world.roleAt(seat, phase) === "Philosopher") return GENUINE;
  }
  return ABSENT;
}
