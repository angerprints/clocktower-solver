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
import {phaseIndex} from "./phases.mjs";
import {EVIL, TEAM, alignment, believedTokens, believesAnother, isEvil,
        knowsWhatItIs, thinksItIsEvil, wakeFits} from "./roles.mjs";
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
  roleAt(seat, _phase) { return this.roles[seat]; }
  findAt(role, _phase) { return this.find(role); }

  demonAt(_phase) {
    for (let i = 0; i < this.roles.length; i++)
      if (TEAM[this.roles[i]] === "demon") return i;
    return null;
  }

  teamAt(seat, phase) { return TEAM[this.roleAt(seat, phase)]; }
  alignmentAt(seat, _phase) { return alignment(this.roles[seat]); }
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

/** A world plus the times a character changed hands.
 *
 * The world underneath is still one starting assignment. What changes
 * with time is layered on top, posited only when something forces it.
 */
export class Timeline {
  constructor(world, changes = []) {
    this.world = world;
    this.changes = changes;
  }

  // Questions about the whole game go straight through; only questions
  // about a moment consult the changes.
  get roles() { return this.world.roles; }
  get believes() { return this.world.believes; }
  find(role) { return this.world.find(role); }
  apparentRole(i) { return this.world.apparentRole(i); }
  evilPlayers() { return this.world.evilPlayers(); }

  roleAt(seat, phase) {
    const here = phaseIndex(phase);
    let role = this.world.roles[seat];
    for (const c of this.changes)
      if (c.seat === seat && c.role !== null && phaseIndex(c.phase) <= here)
        role = c.role;
    return role;
  }

  alignmentAt(seat, phase) {
    const here = phaseIndex(phase);
    let side = alignment(this.world.roles[seat]);
    for (const c of this.changes) {
      if (c.seat !== seat || phaseIndex(c.phase) > here) continue;
      // An explicit side wins; otherwise take the new character's.
      side = c.side || (c.role ? alignment(c.role) : side);
    }
    return side;
  }

  evilAt(seat, phase) { return this.alignmentAt(seat, phase) === EVIL; }

  findAt(role, phase) {
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
    const here = phaseIndex(phase);
    let seat = this.world.demonAt(phase);
    for (const c of this.changes)
      if (c.role && TEAM[c.role] === "demon" && phaseIndex(c.phase) <= here)
        seat = c.seat;
    return seat;
  }

  teamAt(seat, phase) { return TEAM[this.roleAt(seat, phase)]; }
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
  const out = evil.filter(knowsWhatItIs).map(key => [key, null]);
  // Somebody who thinks they are the Demon bluffs like the Demon. A
  // Lunatic is good and lies anyway, because as far as it knows it has
  // every reason to.
  for (const key of script.keys)
    if (thinksItIsEvil(key))
      for (const token of believedTokens(key, script)) out.push([key, token]);
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
    if (allowGoodLies)
      for (const r of script.outsiders)
        if (r !== claim && !believesAnother(r)) out.push([r, null]);
    return out;
  }

  // Openly claiming an evil character. Still needs its token if it is the
  // kind that holds one.
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
      (isEvil(role) && knowsWhatItIs(role)) || wakeFits(role, belief, wake));

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
      for (const shift of shifts) {
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

/** Which options are still open for this seat right now. */
function viable(options, used, count, target) {
  return options.filter(([role, belief]) =>
    !used.has(role) &&
    (belief === null || !used.has(belief)) &&
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
    let free = 0;
    for (const role of look.roles[k][t]) if (!used.has(role)) free += 1;
    if (free < want) return false;                  // not enough tokens left
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
    used.add(role);
    verdict[team] = fitsAhead(count, target, look, order, k, used);
    used.delete(role);
    count[team] -= 1;
  }
  return options.filter(([role]) => verdict[TEAM[role]]);
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
      cands.push(opts);
    }
    // Seats with fewest options first, so the search prunes earlier.
    const order = [...Array(nPlayers).keys()]
      .sort((a, b) => cands[a].length - cands[b].length);
    out.push({target, cands, order, required: present});
  }
  return out;
}

// --------------------------------------------------------------------
// The search
// --------------------------------------------------------------------

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
    const count = {townsfolk: 0, outsider: 0, minion: 0, demon: 0};

    const rec = k => {
      if (stop) return;
      if (k === order.length) {
        // This bag's characters have to have actually landed.
        for (const need of required) if (!used.has(need)) return;
        if (emit(new World([...roles], [...believes])) === false) stop = true;
        return;
      }
      const i = order[k];
      for (const [role, belief] of cands[i]) {
        const team = TEAM[role];
        if (used.has(role)) continue;
        if (belief !== null && used.has(belief)) continue;
        if (count[team] >= target[team]) continue;

        used.add(role);
        if (belief !== null) used.add(belief);
        count[team] += 1;
        roles[i] = role; believes[i] = belief;

        rec(k + 1);

        roles[i] = null; believes[i] = null;
        count[team] -= 1;
        used.delete(role);
        if (belief !== null) used.delete(belief);
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
  const count = {townsfolk: 0, outsider: 0, minion: 0, demon: 0};
  let standsFor = 1.0;

  for (let k = 0; k < order.length; k++) {
    const i = order[k];
    let options = prune(viable(cands[i], used, count, target),
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

    used.add(role);
    if (belief !== null) used.add(belief);
    count[TEAM[role]] += 1;
    roles[i] = role;
    believes[i] = belief;
  }

  for (const role of required) if (!used.has(role)) return null;
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
    if (got === null) emit(null, 0.0);
    else emit(got.world, got.standsFor * setups.length);
  }
}
