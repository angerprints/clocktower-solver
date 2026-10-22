// Step one of the solver: which role assignments are legal at all?
//
// A "world" is a complete mapping of seat to true character. Somebody
// handed the wrong token is the awkward case: their true character is the
// Drunk, but they also consume the Townsfolk token they think they hold,
// and nobody else can have it.
//
// Worlds are handed to a callback one at a time rather than collected,
// because a fifteen-seat Bad Moon Rising board has nine million of them
// and the caller only ever scores each one and drops it.

import {CHARACTERS, SETUP} from "./catalogue.mjs";
import {LISTENING, noteSideRead, phaseIndex} from "./phases.mjs";
import {EVIL, TEAM, alignment, believedTokens, believesAnother, isEvil,
        knowsWhatItIs, mustHide, thinksItIsEvil, wakeFits} from "./roles.mjs";
import {DEFAULT} from "./scripts.mjs";

const TEAMS = ["townsfolk", "outsider", "minion", "demon"];

/** A seat claimed a character that is not on this script. */
export class OffScript extends Error {
  constructor(claim, scriptName) {
    super(`${claim} is not on ${scriptName}, so nobody can be claiming ` +
          `it. Change the script, or change the claim.`);
    this.name = "OffScript";
    this.claim = claim;
    this.scriptName = scriptName;
  }
}

export class World {
  constructor(roles, believes) {
    this.roles = roles;
    this.believes = believes;
    this._index = null;
  }

  apparentRole(i) { return this.believes[i] || this.roles[i]; }

  /** Which seat holds this character, or null.
   *
   * Indexed on first use. Every character rule on a script asks this of
   * every world on every night, and with a full script that is twenty-odd
   * scans of the table — enough to cost more than the reasoning does.
   */
  find(role) {
    if (this._index === null) {
      this._index = new Map();
      this.roles.forEach((r, i) => {
        if (!this._index.has(r)) this._index.set(r, i);
      });
    }
    const at = this._index.get(role);
    return at === undefined ? null : at;
  }

  // Asking about a moment rather than about the game. A plain world is
  // one starting assignment, so these ignore the phase — they exist so
  // that every check which cares *when* it is asking says so, and a
  // timeline only has to override these.
  roleAt(seat, phase) {
    if (TEA_READS.now) teaRead(phase);
    return this.roles[seat];
  }
  findAt(role, phase) {
    if (TEA_READS.now) teaRead(phase);
    return this.find(role);
  }

  demonAt(phase) {
    if (TEA_READS.now) teaRead(phase);
    for (let i = 0; i < this.roles.length; i++)
      if (TEAM[this.roles[i]] === "demon") return i;
    return null;
  }

  teamAt(seat, phase) { return TEAM[this.roleAt(seat, phase)]; }
  alignmentAt(seat, phase) {
    if (LISTENING) noteSideRead(seat, phase);
    return alignment(this.roles[seat]);
  }
  evilAt(seat, phase) { return this.alignmentAt(seat, phase) === EVIL; }

  evilPlayers() {
    const out = [];
    this.roles.forEach((r, i) => { if (isEvil(r)) out.push(i); });
    return out;
  }
}

/** One seat becoming something else, from one phase onward.
 *
 * Either half may be left alone. No role keeps the character and moves
 * only the side, which is what an Ogre does; no side takes whichever the
 * new character normally sits on, which covers a Minion catching the
 * star. Both together cover a Pit-Hag rewriting somebody.
 */
export const change = (phase, seat, role = null, side = null) =>
  ({phase, seat, role, side});

/** A seat turned evil that knows it and keeps its character: the Bounty
 * Hunter's evil Townsfolk ("bountyhunter"), whoever a Mezepheles turned
 * ("mezepheles"). Told apart from an Ogre's turn because such a seat may
 * lie about what it learns from then on (info.mjs knowsItTurnedEvil).
 * `TurnedEvil` and `MezephelesTurn` in Python (11.10.2026). */
export const turnedEvil = (phase, seat, by) =>
  ({phase, seat, role: null, side: "evil", turned: by});

/** Who babysits Lil' Monsta from this night on, and "is the Demon"
 * (21.10.2026). Changes nothing about the seat. `Babysits` in Python. */
export const babysits = (phase, seat) =>
  ({phase, seat, role: null, side: null, babysits: true});

/** Was this world dealt with Lil' Monsta in the bag — nobody holding a
 * Demon? See worlds.py. */
export const BABYSAT_READS = {now: null};

export const lilMonstaWorld = world =>
  !world.roles.some(r => TEAM[r] === "demon")
  && !world.roles.includes("Summoner");

/** The player the Summoner made an evil Demon of its choice
 * (21.10.2026). `Summoned` in Python. */
export const summoned = (phase, seat, role) =>
  ({phase, seat, role, side: "evil", summoned: true});

/** No Demon came, and good won there (D and E, Weg 1). A mark that
 * changes nothing. `NotSummoned` in Python. */
export const notSummoned = (phase, seat) =>
  ({phase, seat, role: null, side: null, notSummoned: true});

/** Whether anything from the summoning on was looked at while a story
 * was told (scoring.mjs bestSummonedStory). See worlds.py. */
export const SUMMON_READS = {now: null};

export const summonerWorld = world => world.roles.includes("Summoner");

/** A Minion or the Demon that chose a new character when the Hatter
 * died (22.10.2026). `TeaParty` in Python. */
export const teaParty = (phase, seat, role, side) =>
  ({phase, seat, role, side, tea: true});

/** Whether anything from the Hatter's night on was looked at while a
 * story was told: {at, read}. See worlds.py. */
export const TEA_READS = {now: null};

/** A phase as a number on one line with the changes: "B" — the board as
 * a night began, after a tea party at its very start — a little past the
 * day before it. See worlds.py. */
export const moment = phase =>
  phaseIndex(phase) + (phase[0] === "B" ? 0.75 : 0);

/** Where a change stands on that line: a tea party just before the night
 * it is stamped with. See worlds.py. */
export const changeAt = c => phaseIndex(c.phase) - (c.tea ? 0.5 : 0);

function teaRead(phase) {
  if (moment(phase) >= TEA_READS.now.at) TEA_READS.now.read = true;
}

/** Did this seat take its character at that night's tea party? Then that
 * night is its first with it (O Weg 1). See worlds.py. */
export const teaMade = (world, seat, night) =>
  (world.changes || []).some(c => c.tea && c.seat === seat
                             && c.phase === `N${night}`);

/** The characters the players really hold when the game starts: the deal,
 * but a Summoner's Marionette holds the good character it believes until
 * the Demon comes (22.10.2026). See worlds.py. */
export function dealtRoles(world) {
  const roles = world.roles;
  if (roles.includes("Summoner") && roles.includes("Marionette")) {
    const m = roles.indexOf("Marionette");
    const token = world.believes[m];
    if (token) {
      // The Lunatic, or the Townsfolk (perhaps the Drunk's). See worlds.py.
      const out = [...roles];
      out[m] = TEAM[token] === "demon" ? "Lunatic" : token;
      return out;
    }
  }
  return roles;
}

/** A world plus the times a character changed hands.
 *
 * The world underneath is still one starting assignment. What changes
 * with time is layered on top, posited only when something forces it.
 */
export class Timeline {
  constructor(world, changes = []) {
    // A timeline laid over a timeline is one timeline; nested, the
    // changes underneath were dropped. See worlds.py.
    if (world instanceof Timeline) {
      changes = [...world.changes, ...changes];
      world = world.world;
    }
    this.world = world;
    // In time order, stable: questions take the last change that applies,
    // front to back. See worlds.py.
    this.changes = changes.map((c, i) => [c, i, changeAt(c)])
      .sort((a, b) => a[2] - b[2] || a[1] - b[1])
      .map(([c]) => c);
    // Indexed by seat on first use, with each moment already a number:
    // most seats never change, and every question used to walk all the
    // changes and parse every phase again. Same answers. See worlds.py.
    this._index = null;
  }

  _indexed() {
    if (this._index) return this._index;
    const roles = new Map(), sides = new Map(), demons = [], held = new Set();
    let summonAt = null;
    for (const c of this.changes) {
      const at = changeAt(c);
      if (c.summoned && summonAt === null) summonAt = at;
      if (c.babysits) { demons.push([at, c.seat, c.phase]); continue; }
      if (!sides.has(c.seat)) sides.set(c.seat, []);
      sides.get(c.seat).push([at, c]);
      if (c.role !== null && c.role !== undefined) {
        if (!roles.has(c.seat)) roles.set(c.seat, []);
        roles.get(c.seat).push([at, c.role]);
        held.add(c.role);
        if (TEAM[c.role] === "demon") demons.push([at, c.seat, null]);
      }
    }
    return (this._index = {roles, sides, demons, held, summonAt});
  }

  /** Anything asked from the summoning on depends on it. */
  _summonRead(phase) {
    const at = this._indexed().summonAt;
    if (at !== null && SUMMON_READS.now && phaseIndex(phase) >= at)
      SUMMON_READS.now.read = true;
  }

  // Questions about the whole game go straight through; only questions
  // about a moment consult the changes.
  get roles() { return this.world.roles; }
  get believes() { return this.world.believes; }
  find(role) { return this.world.find(role); }
  apparentRole(i) { return this.world.apparentRole(i); }
  evilPlayers() { return this.world.evilPlayers(); }

  roleAt(seat, phase) {
    this._summonRead(phase);
    if (TEA_READS.now) teaRead(phase);
    let role = this.world.roles[seat];
    const mine = this._indexed().roles.get(seat);
    if (mine) {
      const here = moment(phase);
      for (const [at, changed] of mine) if (at <= here) role = changed;
    }
    return role;
  }

  alignmentAt(seat, phase) {
    if (LISTENING) noteSideRead(seat, phase);
    this._summonRead(phase);
    let side = alignment(this.world.roles[seat]);
    const mine = this._indexed().sides.get(seat);
    if (mine) {
      const here = moment(phase);
      for (const [at, c] of mine) {
        if (at > here) continue;
        // An explicit side wins; otherwise take the new character's.
        side = c.side || (c.role ? alignment(c.role) : side);
      }
    }
    return side;
  }

  evilAt(seat, phase) { return this.alignmentAt(seat, phase) === EVIL; }

  findAt(role, phase) {
    if (TEA_READS.now) teaRead(phase);
    // Nobody dealt it and nobody changed into it: nobody holds it.
    if (!this._indexed().held.has(role) && !this.world.roles.includes(role))
      return null;
    for (let seat = 0; seat < this.world.roles.length; seat++)
      if (this.roleAt(seat, phase) === role) return seat;
    return null;
  }

  /** Which seat is the Demon now — the last to have become one.
   *
   * Tracked through the changes rather than read off the board, because
   * **holding a demon character is not the same as being the Demon**. A
   * handover leaves the old character where it was: an executed Imp
   * still holds the Imp when the Scarlet Woman inherits, so two seats
   * hold one and the board cannot say which is which.
   *
   * A Snake Charmer swap is tracked here too, because the swap grants
   * the charmer the Demon's *character* — a change with a demon role in
   * it. That only failed while the swap was copying the wrong character;
   * the tracking was never the fault.
   */
  demonAt(phase) {
    let seat = this.world.demonAt(phase);
    this._summonRead(phase);
    if (TEA_READS.now) teaRead(phase);
    const demons = this._indexed().demons;
    if (demons.length) {
      const here = moment(phase);
      let sat = null;
      for (const [at, changed, babysat] of demons)
        if (at <= here) { seat = changed; sat = babysat; }
      // Which nights' babysitters were looked at (bestBabysatStory).
      if (sat !== null && BABYSAT_READS.now) BABYSAT_READS.now.add(sat);
    }
    return seat;
  }

  teamAt(seat, phase) { return TEAM[this.roleAt(seat, phase)]; }

  /** A story with Lil' Monsta in it: somebody babysits. See worlds.py. */
  get lilMonsta() {
    return this._indexed().demons.some(([, , babysat]) => babysat !== null);
  }
}

// --------------------------------------------------------------------
// What a seat could be
// --------------------------------------------------------------------

/** Every character on this script, believers expanded. */
function anything(script) {
  const out = [];
  for (const key of script.seatedKeys) {
    if (believesAnother(key))
      for (const token of believedTokens(key, script)) out.push([key, token]);
    else out.push([key, null]);
  }
  return out;
}

/** This character as a candidate, with a token if it needs one.
 *
 * Claiming to *be* the Drunk is a legal thing to say, and dealing one
 * with no token behind it produces a world that is not a game.
 */
function itself(key, script) {
  return believesAnother(key)
    ? believedTokens(key, script).map(token => [key, token])
    : [[key, null]];
}

/** Evil characters that could be bluffing this claim.
 *
 * Believers are left out on purpose: somebody handed the wrong token says
 * what they believe, which the caller already covers. Letting them in
 * would offer a Marionette who thinks it is the Recluse while claiming
 * the Soldier — a deliberate lie from somebody who thinks they are good.
 */
function evilOptions(evil, script) {
  const out = evil.filter(k => knowsWhatItIs(k) && CHARACTERS[k].dealt)
    .map(key => [key, null]);
  // Somebody who thinks they are the Demon bluffs like the Demon. A
  // Lunatic is good and lies anyway, because as far as it knows it has
  // every reason to.
  for (const key of script.keys)
    if (thinksItIsEvil(key))
      for (const token of believedTokens(key, script)) out.push([key, token]);
  // A Lunatic beside the Summoner's Demon becomes its Marionette and goes
  // on thinking it is a Demon (22.10.2026). See worlds.py.
  if (["Summoner", "Marionette", "Lunatic"].every(k => script.keys.includes(k)))
    for (const token of believedTokens("Lunatic", script))
      out.push(["Marionette", token]);
  return out;
}

function candidatesFromClaim(claim, allowGoodLies, certainty, script) {
  const evil = script.minions.concat(script.demons);
  const believers = script.keys.filter(believesAnother);

  if (claim && certainty === "confirmed") return itself(claim, script);

  if (claim && certainty === "self") {
    const out = itself(claim, script);
    for (const b of believers)
      if (believedTokens(b, script).includes(claim)) out.push([b, claim]);
    return out;
  }

  if (claim === null || claim === undefined || claim === "" ||
      certainty === "unsure") return anything(script);

  if (certainty === "hiding") allowGoodLies = true;

  const inTownsfolk = script.townsfolk.includes(claim);
  const inOutsiders = script.outsiders.includes(claim);

  if (inTownsfolk || inOutsiders) {
    const out = itself(claim, script);
    for (const b of believers)
      if (believedTokens(b, script).includes(claim)) out.push([b, claim]);
    out.push(...evilOptions(evil, script));
    if (allowGoodLies) {
      for (const r of script.outsiders)
        if (r !== claim && !believesAnother(r)) out.push([r, null]);
    } else if (inTownsfolk) {
      // A Mutant is behind a Townsfolk claim whether or not good lies are
      // allowed: it has no other claim it can safely make.
      for (const r of script.outsiders) if (mustHide(r)) out.push([r, null]);
    }
    // And a Pixie, mad about being the Townsfolk it was shown: its
    // ability asking it to lie (11.10.2026).
    if (inTownsfolk && script.keys.includes("Pixie") && claim !== "Pixie")
      out.push(["Pixie", null]);
    return out;
  }

  // Openly claiming an evil character. Still needs its token if it is the
  // kind that holds one.
  // Lil' Monsta is nobody's character: claiming it says nothing about
  // the seat (21.10.2026).
  if (evil.includes(claim) && !CHARACTERS[claim].dealt) return anything(script);
  if (evil.includes(claim)) return itself(claim, script);

  // Nobody can claim a character that is not in the bag. Treating this as
  // "no constraint" leaves every seat unconstrained and the search with
  // nothing to prune on — which does not fail, it hangs.
  throw new OffScript(claim, script.name);
}

/** Which (character, believes-it-is) options fit a given claim.
 *
 * Baseline: good players do not lie. `allowGoodLies` opens one more door
 * — an Outsider covering up behind somebody else's character — because
 * that is the good lie people actually tell.
 *
 * `certainty` overrides per seat: "self" (you can see your own token,
 * unless you were made the Drunk), "confirmed" (established by something
 * the table watched), "hiding" (may be covering up), "unsure" (not
 * trusted at all, and expensive).
 *
 * `wake` is what the seat said about waking, a softer claim that prunes
 * the same way. `allowed` narrows to characters some watched event pins
 * down; it never widens.
 */
export function candidates(claim, allowGoodLies = false, certainty = "",
                           allowed = null, wake = null, script = DEFAULT) {
  let opts = candidatesFromClaim(claim, allowGoodLies, certainty, script);

  // Held to a wake claim if the seat knows what it is. A knowing bluffer
  // is not, because they say whatever suits them; somebody handed the
  // wrong token is, because they answer honestly about the character they
  // think they have. Not the same question as "are they evil": a
  // Marionette is evil and still does not know.
  if (wake && certainty !== "hiding" && certainty !== "unsure")
    opts = opts.filter(([role, belief]) =>
      (isEvil(role) && knowsWhatItIs(role)) || mustHide(role) ||
      wakeFits(role, belief, wake));

  if (allowed !== null)
    opts = opts.filter(([role]) => allowed.has(role));
  return opts;
}

// --------------------------------------------------------------------
// The bag
// --------------------------------------------------------------------

/** Every distribution this table size could have been dealt.
 *
 * One entry per combination of setup-changing characters. The shape is
 * general because some scripts stack several, and some offer a choice of
 * shift rather than a fixed one.
 */
export function bags(nPlayers, script = DEFAULT, fabled = []) {
  const base = {};
  TEAMS.forEach((t, i) => (base[t] = SETUP[nPlayers][i]));
  let out = [[new Set(), base]];

  for (const [role, shifts] of Object.entries(script.setupModifiers)) {
    const grown = [];
    for (const [present, counts] of out) {
      grown.push([present, counts]);              // this one stayed out
      // A shift that would take a team below nought cannot be made. Where
      // there is another to choose, that one is taken; where there is
      // not, the character is in play and changes nothing — a Vigormortis
      // removes an Outsider "if there is one".
      let possible = shifts.filter(shift =>
        Object.entries(shift).every(([team, delta]) =>
          counts[team] + delta >= 0));
      if (!possible.length) possible = [{}];
      for (const shift of possible) {
        const moved = {...counts};
        for (const [team, delta] of Object.entries(shift)) moved[team] += delta;
        grown.push([new Set([...present, role]), moved]);
      }
    }
    out = grown;
  }

  // A Fabled is on the table, not in the bag. It is in play because the
  // Storyteller said so, so there is no "it stayed out" branch — only the
  // question of what it did, which nobody at the table knows.
  for (const key of fabled) {
    const shifts = CHARACTERS[key].setup.length ? CHARACTERS[key].setup : [{}];
    const grown = [];
    for (const [present, counts] of out)
      for (const shift of shifts) {
        const moved = {...counts};
        for (const [team, delta] of Object.entries(shift)) moved[team] += delta;
        grown.push([present, moved]);
      }
    out = grown;
  }

  out = out.concat(marionetteToBe(out, script));
  const room = Object.fromEntries(TEAMS.map(t => [t, script.byTeam(t).length]));
  const seen = new Set(), kept = [];
  for (const [present, counts] of out) {
    // Whatever the shifts did, the bag still has to seat everybody. A
    // modifier that moves one number without moving another back would
    // otherwise show up as a silently wrong world count.
    if (TEAMS.reduce((s, t) => s + counts[t], 0) !== nPlayers) continue;
    if (TEAMS.some(t => counts[t] < 0 || counts[t] > room[t])) continue;
    // Two Fabled answers can land on the same distribution. Searching it
    // twice would count every world in it twice.
    const key = [...present].sort().join(",") + "|" +
                TEAMS.map(t => counts[t]).join(",");
    if (seen.has(key)) continue;
    seen.add(key);
    kept.push([present, counts]);
  }
  return kept;
}

// Characters more than one seat may hold: the Village Idiot, up to three
// (11.10.2026). Everything else is one token in the bag.
const COPIES = Object.fromEntries(
  Object.values(CHARACTERS).filter(c => (c.copies || 1) > 1)
    .map(c => [c.key, c.copies]));

/** Is a token of this character still in the bag? */
const free = (role, used, taken) =>
  !used.has(role) || (role in COPIES && (taken[role] || 0) < COPIES[role]);

function take(role, used, taken) {
  used.add(role);
  taken[role] = (taken[role] || 0) + 1;
}

function giveBack(role, used, taken) {
  taken[role] -= 1;
  if (!taken[role]) { delete taken[role]; used.delete(role); }
}

/** Which options are still open for this seat right now. */
function viable(options, used, count, target, taken = {}) {
  return options.filter(([role, belief]) =>
    free(role, used, taken) &&
    (belief === null || free(belief, used, taken)) &&
    count[TEAM[role]] < target[TEAM[role]]);
}

/** Precomputed answers to "what can the seats after this one give me?"
 *
 * For each position and team: how many later seats could supply it, and
 * which characters of that team they could supply between them. The
 * second is what matters — a dozen seats can all offer to be the Drunk,
 * but there is only one Drunk token, so they cannot cover two Outsiders.
 */
function lookahead(cands, order) {
  const teams = cands.map(opts => new Set(opts.map(([r]) => TEAM[r])));
  const n = order.length;
  const seats = Array.from({length: n + 1},
    () => ({townsfolk: 0, outsider: 0, minion: 0, demon: 0}));
  const roles = Array.from({length: n + 1},
    () => ({townsfolk: new Set(), outsider: new Set(),
            minion: new Set(), demon: new Set()}));

  for (let k = n - 1; k >= 0; k--) {
    const i = order[k];
    seats[k] = {...seats[k + 1]};
    roles[k] = {};
    for (const t of TEAMS) roles[k][t] = new Set(roles[k + 1][t]);
    for (const t of teams[i]) seats[k][t] += 1;
    for (const [role] of cands[i]) roles[k][TEAM[role]].add(role);
  }
  return {teams, seats, roles};
}

/** Could the seats from position k onward fill what is still missing?
 *
 * Deliberately a relaxation: it never rules out a world that could
 * actually be reached, it only cuts walks already going nowhere.
 */
function fitsAhead(count, target, look, order, k, used) {
  const wanted = new Set();
  for (const t of TEAMS) if (target[t] - count[t] > 0) wanted.add(t);
  for (const t of TEAMS) {
    const want = target[t] - count[t];
    if (want <= 0) continue;
    if (look.seats[k][t] < want) return false;      // not enough seats left
    // A character more than one seat may hold is more than one token,
    // counted at its most — still a relaxation.
    let left = 0;
    for (const role of look.roles[k][t]) {
      if (!used.has(role)) left += 1;
      if (role in COPIES) left += COPIES[role] - 1;
    }
    if (left < want) return false;                  // not enough tokens left
  }
  for (let j = k; j < order.length; j++) {
    let useful = false;
    for (const t of look.teams[order[j]]) if (wanted.has(t)) useful = true;
    if (!useful) return false;            // this seat can fill nothing needed
  }
  return true;
}

/** Drop options whose team cannot be afforded later on. */
function prune(options, count, target, look, order, k, used) {
  if (k >= order.length) return options;
  const verdict = {};
  for (const [role] of options) {
    const team = TEAM[role];
    if (team in verdict) continue;
    count[team] += 1;
    const had = used.has(role);           // a second Village Idiot
    used.add(role);
    verdict[team] = fitsAhead(count, target, look, order, k, used);
    if (!had) used.delete(role);
    count[team] -= 1;
  }
  return options.filter(([role]) => verdict[TEAM[role]]);
}

// Stelle 73, A (22.10.2026): a Summoner's Marionette is nobody's at the
// deal; its Minion's place goes to a good character of either kind. The
// extra bags, marked with the kind the Marionette's player held. See
// worlds.py.
const MARIONETTE_HELD = {"Marionette@outsider": "outsider",
                         "Marionette@townsfolk": "townsfolk"};

function marionetteToBe(bags, script) {
  if (!script.keys.includes("Marionette")) return [];
  const out = [];
  for (const [present, counts] of bags) {
    if (!present.has("Summoner") || counts.minion < 2) continue;
    for (const [held, more, fewer] of [["outsider", "townsfolk", "outsider"],
                                       ["townsfolk", "outsider", "townsfolk"]]) {
      if (counts[fewer] < 1) continue;
      const moved = {...counts};
      moved[more] += 1;
      moved[fewer] -= 1;
      out.push([new Set([...present, "Marionette", `Marionette@${held}`]),
                moved]);
    }
  }
  return out;
}

function heldBefore(token, script) {
  const team = TEAM[token];
  if (team === "demon") return new Set(["outsider"]);
  if (team === "townsfolk" && script.keys.includes("Drunk"))
    return new Set(["townsfolk", "outsider"]);
  return new Set([team]);
}

function branches(nPlayers, claims, certainties, allowGoodLies, forced,
                  wakes, script, fabled) {
  if (!SETUP[nPlayers]) throw new Error("Table sizes from 5 to 15 players.");
  const movers = script.setupModifiers;
  const out = [];

  for (const [present, target] of bags(nPlayers, script, fabled)) {
    const cands = [];
    for (let i = 0; i < nPlayers; i++) {
      let opts = candidates(
        claims[i] ?? null, allowGoodLies, certainties[i] ?? "",
        forced[i] ?? null, wakes[i] ?? null, script);
      // A character that changes the bag can only be dealt in a bag that
      // was changed by it.
      opts = opts.filter(([role]) => !movers[role] || present.has(role));
      for (const [mark, held] of Object.entries(MARIONETTE_HELD))
        if (present.has(mark))
          opts = opts.filter(([role, token]) => role !== "Marionette"
                             || heldBefore(token, script).has(held));
      cands.push(opts);
    }
    // Seats with fewest options first, so the search prunes earlier.
    const order = [...Array(nPlayers).keys()]
      .sort((a, b) => cands[a].length - cands[b].length);
    // What has to land on a seat: not Lil' Monsta (21.10.2026).
    const required = new Set([...present].filter(
      k => CHARACTERS[k] && CHARACTERS[k].dealt));
    out.push({target, cands, order, required});
  }
  return out;
}

// --------------------------------------------------------------------
// The search
// --------------------------------------------------------------------

/** Does every character sit where the setup says it must? The Marionette
 * neighbours the Demon; the catalogue holds the rule (`beside`). See
 * worlds.py. */
/** A Marionette that thinks it is a Demon was a Lunatic until the
 * Summoner's Demon came (22.10.2026): only where a Summoner was dealt. */
export function believesLegally(roles, believes) {
  for (let i = 0; i < roles.length; i++)
    if (roles[i] === "Marionette" && believes[i]
        && TEAM[believes[i]] === "demon" && !roles.includes("Summoner"))
      return false;
  return true;
}

export function seatedLegally(roles, believes = null) {
  const n = roles.length;
  // No Demon dealt is Lil' Monsta's bag: a Marionette sits beside the
  // first babysitter instead (scoring.mjs theMinionsChooseABabysitter).
  const noDemon = !roles.some(r => TEAM[r] === "demon");
  for (let seat = 0; seat < n; seat++) {
    const team = CHARACTERS[roles[seat]].beside;
    if (team === "demon" && noDemon) continue;
    if (team && TEAM[roles[(seat + n - 1) % n]] !== team &&
        TEAM[roles[(seat + 1) % n]] !== team) return false;
    // "[+the King]": a Choirboy dealt means a King dealt (10.10.2026).
    // A Summoner's Marionette-to-be may hold it (Stelle 73). See worlds.py.
    for (const other of CHARACTERS[roles[seat]].brings || [])
      if (!roles.includes(other) && !(believes && roles.includes("Summoner")
          && roles.includes("Marionette")
          && believes[roles.indexOf("Marionette")] === other)) return false;
    if (CHARACTERS[roles[seat]].lines_up && !inALine(roles, seat))
      return false;
  }
  return true;
}

/** Do the evil characters sit in one line, `lord` not at either end? The
 * Lord of Typhon's setup (19.10.2026). See worlds.py. */
export function inALine(roles, lord) {
  const n = roles.length;
  const evil = new Set();
  roles.forEach((r, s) => {
    if (TEAM[r] === "minion" || TEAM[r] === "demon") evil.add(s);
  });
  const bounty = roles.includes("BountyHunter");
  const kinds = roles.map((r, s) => {
    if (evil.has(s)) return "evil";
    if (CHARACTERS[r].registers.includes("minion")) return "registers";
    if (bounty && TEAM[r] === "townsfolk") return "townsfolk";
    return null;
  });
  if (kinds[(lord + n - 1) % n] === null || kinds[(lord + 1) % n] === null)
    return false;
  for (let start = 0; start < n; start++) {
    if (kinds[start] === null || start === lord) continue;
    let townsfolk = 0, covered = 0;
    for (let length = 1; length <= n; length++) {
      const seat = (start + length - 1) % n;
      if (kinds[seat] === null) break;
      if (kinds[seat] === "townsfolk") townsfolk++;
      if (townsfolk > 1) break;
      if (evil.has(seat)) covered++;
      if (covered === evil.size && seat !== lord && length >= 3) return true;
    }
  }
  return false;
}

/** Hand every legal assignment to `emit`, one at a time.
 *
 * A callback rather than a generator: generators cost about a third of
 * the run time here, and the caller only ever scores and drops each
 * world. Return `false` from `emit` to stop early.
 */
export function eachWorld(nPlayers, claims, opts = {}, emit) {
  const {
    certainties = {}, allowGoodLies = false, forced = {}, wakes = {},
    script = DEFAULT, fabled = [],
  } = opts;

  let stop = false;
  for (const {target, cands, order, required} of branches(
      nPlayers, claims, certainties, allowGoodLies, forced, wakes,
      script, fabled)) {
    if (stop) return;

    const roles = new Array(nPlayers).fill(null);
    const believes = new Array(nPlayers).fill(null);
    const used = new Set();
    const taken = {};
    const count = {townsfolk: 0, outsider: 0, minion: 0, demon: 0};

    const rec = k => {
      if (stop) return;
      if (k === order.length) {
        // This bag's characters have to have actually landed.
        for (const need of required) if (!used.has(need)) return;
        if (!seatedLegally(roles, believes) || !believesLegally(roles, believes))
          return;                            // dealt to seats it cannot sit in
        if (emit(new World([...roles], [...believes])) === false) stop = true;
        return;
      }
      const i = order[k];
      for (const [role, belief] of cands[i]) {
        const team = TEAM[role];
        if (!free(role, used, taken)) continue;
        if (belief !== null && !free(belief, used, taken)) continue;
        if (count[team] >= target[team]) continue;

        take(role, used, taken);
        if (belief !== null) take(belief, used, taken);
        count[team] += 1;
        roles[i] = role; believes[i] = belief;

        rec(k + 1);

        roles[i] = null; believes[i] = null;
        count[team] -= 1;
        giveBack(role, used, taken);
        if (belief !== null) giveBack(belief, used, taken);
        if (stop) return;
      }
    };
    rec(0);
  }
}

/** List form, stopping at `maxWorlds`. */
export function enumerateWorlds(nPlayers, claims, opts = {}) {
  const cap = opts.maxWorlds ?? 300_000;
  const out = [];
  eachWorld(nPlayers, claims, opts, world => {
    out.push(world);
    return out.length < cap;
  });
  return out;
}

// --------------------------------------------------------------------
// Looking at a lot of worlds instead of counting all of them
// --------------------------------------------------------------------

/** Branches with the look-ahead tables attached, for the sampler.
 *
 * Bags that cannot produce a single world are dropped here rather than
 * wasting walks on them. With every seat claiming a Townsfolk, the
 * Baron's bag wants four Outsiders and the table can only reach one —
 * there is nothing down there to find.
 */
function samplingSetups(nPlayers, claims, opts) {
  const {certainties = {}, allowGoodLies = false, forced = {}, wakes = {},
         script = DEFAULT, fabled = []} = opts;
  const out = [];
  for (const branch of branches(nPlayers, claims, certainties, allowGoodLies,
                                forced, wakes, script, fabled)) {
    const look = lookahead(branch.cands, branch.order);
    const empty = {townsfolk: 0, outsider: 0, minion: 0, demon: 0};
    if (fitsAhead(empty, branch.target, look, branch.order, 0, new Set()))
      out.push({...branch, look});
  }
  return out;
}

/** One random walk from the top of the search to a finished world.
 *
 * Returns {world, standsFor} — how many worlds it stands for — or null
 * if the walk painted itself into a corner.
 *
 * The choice at each seat is deliberately not uniform. A seat claiming a
 * Townsfolk typically offers one honest option against five evil ones, so
 * tossing a fair coin over them makes a seat evil five times too often —
 * the walk lands in a thin corner of the tree and the weight needed to
 * correct it explodes. Instead each team is picked roughly in proportion
 * to how many of its slots are still unfilled, which is what the finished
 * world will actually look like. The weight then divides by the
 * probability the walk really used, so the estimate stays unbiased either
 * way; matching the shape only makes it steadier.
 */
export function dive(setup, nPlayers, rng) {
  const {target, cands, order, required, look} = setup;
  const roles = new Array(nPlayers).fill(null);
  const believes = new Array(nPlayers).fill(null);
  const used = new Set();
  const taken = {};
  const count = {townsfolk: 0, outsider: 0, minion: 0, demon: 0};
  let standsFor = 1.0;

  for (let k = 0; k < order.length; k++) {
    const i = order[k];
    let options = prune(viable(cands[i], used, count, target, taken),
                        count, target, look, order, k + 1, used);

    // A bag is only that bag if its characters actually land in it. When
    // this is the last seat that could take one, it must.
    for (const role of required) {
      if (used.has(role)) continue;
      let later = false;
      for (let j = k + 1; j < order.length && !later; j++)
        if (cands[order[j]].some(([r]) => r === role)) later = true;
      if (!later) options = options.filter(([r]) => r === role);
    }
    if (!options.length) return null;

    const perTeam = {};
    for (const [role] of options) {
      const t = TEAM[role];
      perTeam[t] = (perTeam[t] || 0) + 1;
    }
    const shares = options.map(([role]) => {
      const t = TEAM[role];
      return (target[t] - count[t]) / perTeam[t];
    });
    const pool = shares.reduce((a, b) => a + b, 0);

    const cut = rng.random() * pool;
    let running = 0.0, chosen = options.length - 1;
    for (let idx = 0; idx < shares.length; idx++) {
      running += shares[idx];
      if (running >= cut) { chosen = idx; break; }
    }
    const [role, belief] = options[chosen];
    standsFor *= pool / shares[chosen];

    take(role, used, taken);
    if (belief !== null) take(belief, used, taken);
    count[TEAM[role]] += 1;
    roles[i] = role;
    believes[i] = belief;
  }

  for (const role of required) if (!used.has(role)) return null;
  if (!seatedLegally(roles, believes) || !believesLegally(roles, believes))
    return null;                            // a dead end, like any other
  return {world: new World(roles, believes), standsFor};
}

/** Hand (world, weight) to `emit` for `dives` random walks.
 *
 * A walk that hits a dead end gives (null, 0). Those still count as
 * dives — dropping them would quietly bias everything upwards.
 */
export function sampleWorlds(nPlayers, claims, opts = {}, emit) {
  const {dives = 20000, rng} = opts;
  const setups = samplingSetups(nPlayers, claims, opts);
  if (!setups.length) return;
  for (let d = 0; d < dives; d++) {
    const setup = setups[rng.below(setups.length)];
    const got = dive(setup, nPlayers, rng);
    // A caller that has walked enough says so (the tea-party budget,
    // 22.10.2026).
    const more = got === null ? emit(null, 0.0)
      : emit(got.world, got.standsFor * setups.length);
    if (more === false) return;
  }
}
