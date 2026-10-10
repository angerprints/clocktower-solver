// Who was not working on a given night, and what could have stopped them.
//
// Nothing here decides that anybody *was* impaired. The solver posits a
// poisoning only when a statement would otherwise be false, then comes
// here to ask whether the board could have produced it and what that
// would have cost. Drunk and poisoned are the same thing to everything
// downstream, which is why they share one registry.

/** One thing that can stop abilities working on a given night.
 *
 * `seats` is who it could have reached, `capacity` how many at once, and
 * `cost` what each hit is worth as a weight — how lucky it had to be to
 * land where the world needs it. A source that reaches everybody for
 * free, like being the Drunk, costs nothing.
 *
 * `cost` may be a number or a function of the seat, because some sources
 * are far likelier to land on one seat than another. The Sailor is the
 * case: whichever of two people it drunks is the Storyteller's call, and
 * a Storyteller treats it as a price the town pays rather than a weapon
 * to point at evil.
 */
import {phaseIndex} from "./phases.mjs";

/** Is this a dead Minion a living Vigormortis killed?
 *
 * "Minions you kill keep their ability": at night, while a Vigormortis was
 * the Demon, and only for as long as it stays alive. */
export function killedByAVigormortis(world, state, who, phase) {
  if (world.teamAt(who, phase) !== "minion") return false;
  const gone = state.diedAt(who)
    .filter(p => phaseIndex(p) <= phaseIndex(phase));
  if (!gone.length) return false;
  const first = gone.reduce((a, b) => phaseIndex(a) <= phaseIndex(b) ? a : b);
  if (first[0].toUpperCase() !== "N") return false;
  const killer = world.demonAt(first);
  if (killer === null || killer === undefined ||
      world.roleAt(killer, first) !== "Vigormortis") return false;
  const now = world.findAt("Vigormortis", phase);
  return now !== null && state.aliveSet(phase).has(now);
}

/** Alive — or dead at a Vigormortis's hand, which keeps its ability.
 *
 * A Witch it killed goes on cursing and a Cerenovus goes on maddening.
 * Only "alive" was asked, so a nominator dropping dead on the day after a
 * Vigormortis took its own Witch had nobody to have cursed them
 * (02.10.2026). */
export const minionStillActs = (world, state, seat, phase) =>
  state.aliveSet(phase).has(seat) ||
  killedByAVigormortis(world, state, seat, phase);

export class Source {
  constructor(name, seats, {capacity = 1, cost = 1.0, repeatCost = 1.0} = {}) {
    this.name = name;
    this.seats = seats instanceof Set ? seats : new Set(seats);
    this.capacity = capacity;
    this.cost = cost;
    // Hitting the same seat as last night is cheaper than a fresh guess,
    // because that is what people actually do.
    this.repeatCost = repeatCost;
  }

  price(seat, again = false) {
    const rate = again ? this.repeatCost : this.cost;
    return typeof rate === "function" ? rate(seat) : rate;
  }

  /** Nothing to be lucky about, whoever it lands on. */
  freeForEveryone() {
    return typeof this.cost !== "function" &&
           typeof this.repeatCost !== "function" &&
           this.cost >= 1.0 && this.repeatCost >= 1.0;
  }

  /** Free and it hits everything it reaches. A Sweetheart, Vigormortis or
   * Goon is free but picks one, so it is not — see impairment.py. */
  unavoidable() {
    return this.freeForEveryone() && this.capacity >= this.seats.size;
  }
}

export const SOURCE_RULES = [];

// An Organ Grinder drunk by its own choice, named so the Mathematician can
// leave it out — nobody else's doing (table ruling, 10.10.2026).
export const ORGAN_GRINDER_BY_CHOICE = "Organ Grinder, by choice";

/** Register something that can impair a seat.
 *
 * Called with (world, state, night) and returns the sources it offers
 * that night, or nothing.
 */
export function sourceRule(fn) {
  SOURCE_RULES.push(fn);
  return fn;
}

/** Everything that could impair somebody on this night of this world.
 * Kept on the view it was asked of — see impairment.py. */
export function sourcesOn(world, state, night) {
  let memo = world._sourcesMemo;
  if (!memo || memo.state !== state || memo.epoch !== state._epoch) {
    memo = {state, epoch: state._epoch, nights: new Map()};
    try { Object.defineProperty(world, "_sourcesMemo",
            {value: memo, writable: true, enumerable: false,
             configurable: true}); } catch (e) { /* frozen: no memo */ }
  }
  let got = memo.nights.get(night);
  if (!got) {
    got = [];
    for (const rule of SOURCE_RULES) got.push(...rule(world, state, night));
    memo.nights.set(night, got);
  }
  return got.slice();
}

export const aliveThrough = (world, state, seat, night) =>
  state.aliveSet(`N${night}`).has(seat);

/** Whoever was handed the wrong token.
 *
 * Impaired every night of the game, and it costs nothing — being the
 * Drunk is not a piece of luck, it is what they are. Elsewhere the
 * Marionette and the Lunatic are the same story.
 */
sourceRule(function alwaysImpaired(world, state, night) {
  // Holding a token *is* being a believer, and the tokens are already on
  // the world — so this is a scan rather than a character lookup per
  // seat per night.
  const seats = new Set();
  world.believes.forEach((token, seat) => {
    // Until the seat's character changes: a Drunk a Fang Gu jumped into
    // is the Fang Gu and kills like one (07.10.2026).
    if (token !== null && token !== undefined
        && world.roleAt(seat, `N${night}`) === world.roles[seat])
      seats.add(seat);
  });
  if (!seats.size) return [];
  return [new Source("believer", seats,
                     {capacity: seats.size, cost: 1.0, repeatCost: 1.0})];
});

/** The Poisoner, as a source.
 *
 * The costs are read late, through functions, so the sensitivity pass can
 * still move the solver's constants and have it mean something.
 */
export function makePoisonerRule(hitCost, repeatCost) {
  return function poisoner(world, state, night) {
    // Looked up per night: a Poisoner who inherits the Demon has stopped
    // being the Poisoner.
    const seat = world.findAt("Poisoner", `N${night}`);
    if (seat === null || !aliveThrough(world, state, seat, night)) return [];
    return [new Source("Poisoner", state.aliveSet(`N${night}`),
                       {capacity: 1, cost: hitCost(),
                        repeatCost: repeatCost()})];
  };
}

/** Every ordered choice of `k` slots out of `n`, without repeats. */
function* arrangements(n, k, taken = [], used = new Set()) {
  if (taken.length === k) {
    yield taken;
    return;
  }
  for (let i = 0; i < n; i++) {
    if (used.has(i)) continue;
    used.add(i);
    yield* arrangements(n, k, [...taken, i], used);
    used.delete(i);
  }
}

/** Could these sources have impaired exactly who the world needs?
 *
 * `required` must be impaired, `forbidden` must not be. Returns the
 * cheapest arrangement as {cost, hits}, or null if there is none.
 *
 * Free sources are applied first: a seat covered by one needs nothing
 * else, and a seat a free source cannot avoid reaching makes a forbidden
 * seat impossible.
 */
export function planNight(sources, required, forbidden, previous) {
  const free = sources.filter(s => s.unavoidable());
  const paid = sources.filter(s => !s.unavoidable());

  const coveredFree = new Set();
  for (const source of free)
    for (const seat of source.seats) coveredFree.add(seat);

  const forbid = forbidden instanceof Set ? forbidden : new Set(forbidden);
  for (const seat of coveredFree)
    if (forbid.has(seat)) return null;   // something unavoidable reached them

  const need = required instanceof Set ? required : new Set(required);
  for (const seat of need)
    if (forbid.has(seat)) return null;   // asked to be working and not

  const outstanding = [...need].filter(seat => !coveredFree.has(seat));
  if (!outstanding.length) return {cost: 1.0, hits: {}};

  // One seat to cover and one source that can pay for it is what nearly
  // every night looks like, and it is worth not building the machinery
  // for it. Trouble Brewing never looks like anything else.
  if (outstanding.length === 1 && paid.length === 1) {
    const seat = outstanding[0], source = paid[0];
    if (source.capacity < 1 || !source.seats.has(seat) || forbid.has(seat))
      return null;
    const same = previous[source.name] === seat;
    return {cost: source.price(seat, same), hits: {[source.name]: seat}};
  }

  // Beyond that the numbers stay tiny, so trying the arrangements
  // outright is simpler than being clever and just as fast.
  const slots = [];
  for (const source of paid)
    for (let i = 0; i < source.capacity; i++) slots.push(source);
  if (outstanding.length > slots.length) return null;

  let best = null, bestHits = null;
  for (const arrangement of arrangements(slots.length, outstanding.length)) {
    let cost = 1.0, ok = true;
    const hits = {};
    for (let i = 0; i < outstanding.length; i++) {
      const seat = outstanding[i], source = slots[arrangement[i]];
      if (!source.seats.has(seat) || forbid.has(seat)) { ok = false; break; }
      const same = previous[source.name] === seat;
      cost *= source.price(seat, same);
      hits[source.name] = seat;
    }
    if (ok && (best === null || cost > best)) { best = cost; bestHits = hits; }
  }
  return best === null ? null : {cost: best, hits: bestHits};
}
