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
import {READ_AT, readingAt} from "./worlds.mjs";
import {slotOf} from "./catalogue.mjs";
import {LISTENING, beginReads, endReads, phaseIndex, replayReads}
  from "./phases.mjs";

/** The seat holding that character now: the Demon if it is that one, else
 * a living holder, else the first. A copy of info.mjs's `holdingNow`,
 * kept here so this module imports nothing above it (Stelle 59). */
function holdingNow(w, s, role, phase) {
  const demon = w.demonAt(phase);
  if (demon !== null && demon !== undefined && w.roleAt(demon, phase) === role)
    return demon;
  const alive = s.aliveSet(phase);
  let first = null;
  for (let seat = 0; seat < w.roles.length; seat++)
    if (w.roleAt(seat, phase) === role) {
      if (alive.has(seat)) return seat;
      if (first === null) first = seat;
    }
  return first;
}

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
  const now = holdingNow(world, state, "Vigormortis", phase);
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
  constructor(name, seats,
              {capacity = 1, cost = 1.0, repeatCost = 1.0, actor = null} = {}) {
    this.name = name;
    this.seats = seats instanceof Set ? seats : new Set(seats);
    this.capacity = capacity;
    this.cost = cost;
    // Hitting the same seat as last night is cheaper than a fresh guess,
    // because that is what people actually do.
    this.repeatCost = repeatCost;
    // The seat whose ability this is; see impairment.py.
    this.actor = actor;
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
  // Always of the whole night, whoever's turn is asking (Hatter stage
  // 3b). See impairment.py.
  if (READ_AT.now !== null) {
    const was = READ_AT.now;
    READ_AT.now = null;
    try { return sourcesOn(world, state, night); } finally { READ_AT.now = was; }
  }
  let memo = world._sourcesMemo;
  if (!memo || memo.state !== state || memo.epoch !== state._epoch) {
    memo = {state, epoch: state._epoch, nights: new Map()};
    try { Object.defineProperty(world, "_sourcesMemo",
            {value: memo, writable: true, enumerable: false,
             configurable: true}); } catch (e) { /* frozen: no memo */ }
  }
  // The hidden choices of this telling move a Lleech's poison, so they
  // are part of the key (scoring.mjs hiddenChoices).
  const hidden = state._hidden;
  const key = hidden ? `${night}|${hidden[0]}|${hidden[1]}` : `${night}`;
  let kept = memo.nights.get(key);
  if (!kept && !LISTENING) {
    const got = [];
    for (const rule of SOURCE_RULES) got.push(...rule(world, state, night));
    got.push(...beforeAParty(world, state, night, got));
    memo.nights.set(key, kept = [got, null]);
  } else if (!kept) {
    // With whose side the rules asked about, for the next story that is
    // handed this answer (phases.mjs `noteSideRead`).
    const got = [];
    beginReads();
    try {
      for (const rule of SOURCE_RULES) got.push(...rule(world, state, night));
      got.push(...beforeAParty(world, state, night, got));
    } finally {
      kept = [got, endReads()];
    }
    memo.nights.set(key, kept);
  } else if (kept[1]) replayReads(kept[1]);
  return kept[0].slice();
}

// Each source at its own turn of a night a tea party split (Hatter stage
// 3c): by rule name, the character whose turn it is. See impairment.py
// `SOURCE_TURNS`.
const SOURCE_TURNS = {
  poisoner: "Poisoner",
  aNoDashiiPoisonsItsTownsfolkNeighbours: "NoDashii",
  aVigormortisPoisonsBesideItsDeadMinions: "Vigormortis",
  aPhilosopherDrunksWhoeverHadIt: "Philosopher",
  aPukkaPoisonsWhoeverItWillKill: "Pukka",
  aSailorDrunksOneOfTwo: "Sailor",
  aCourtierNamesACharacter: "Courtier",
  anOrganGrinderMayDrink: "OrganGrinder",
  aWidowPoisonsOne: "Widow",
  aPreacherSilencesItsMinions: "Preacher",
  aLleechPoisonsItsHost: "Lleech",
  anInnkeeperDrunksOneOfTheTwoItGuards: "Innkeeper",
};

const sourceMark = s =>
  `${s.name}|${[...s.seats].sort((a, b) => a - b).join(",")}|${s.capacity}|${s.actor}`;

/** The sources only a turn before a tea party in the night saw. See
 * impairment.py `_before_a_party`. */
function beforeAParty(world, state, night, got) {
  const phase = `N${night}`;
  if (!(world.changes || []).some(c => c.tea && c.phase === phase
                                   && c.slot !== null && c.slot !== undefined))
    return [];
  const have = new Set(got.map(sourceMark));
  const out = [];
  for (const rule of SOURCE_RULES) {
    const key = SOURCE_TURNS[rule.name];
    const slot = key ? slotOf(key, night) : null;
    if (slot === null) continue;
    for (const source of readingAt(phase, slot, slot,
                                   () => rule(world, state, night))) {
      const mark = sourceMark(source);
      if (!have.has(mark)) { have.add(mark); out.push(source); }
    }
  }
  return out;
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
    // A Summoner's Marionette-to-be that was the Drunk or the Lunatic until
    // the Demon came is one all along (22.10.2026).
    const now = world.roleAt(seat, `N${night}`);
    if (token !== null && token !== undefined
        && (now === world.roles[seat]
            || (world.roles[seat] === "Marionette"
                && (now === "Drunk" || now === "Lunatic"))))
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
                        repeatCost: repeatCost(), actor: seat})];
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

// The two that take an ability away outright (10.10.2026), and a
// Philosopher's on whoever held what it took (13.10.2026). See
// impairment.py.
export const SILENCERS = ["Preacher", "Xaan", "Philosopher"];
// Sources that rest while their actor is drunk or poisoned: the two
// silencers, and a Lleech's poison on its host (11.10.2026).
export const RESTING = ["Preacher", "Xaan", "Lleech"];

/** Sources whose own actor a silencer reached tonight do nothing. */
export function silencedOut(sources) {
  const gone = new Set();
  for (const source of sources)
    if (SILENCERS.includes(source.name) && source.unavoidable())
      for (const seat of source.seats) gone.add(seat);
  if (!gone.size) return [...sources];
  return sources.filter(s => s.actor === null || s.actor === undefined
    || !gone.has(s.actor) || SILENCERS.includes(s.name));
}

/** `planNight`, and if nothing fits, the same night with one resting
 * silencer set aside and its actor impaired instead. See impairment.py. */
export function planNightResting(sources, required, forbidden, previous) {
  const working = silencedOut(sources);
  let got = planNight(working, required, forbidden, previous);
  if (got !== null) return got;
  const forbid = forbidden instanceof Set ? forbidden : new Set(forbidden);
  for (const source of working) {
    if (!RESTING.includes(source.name) || source.actor === null
        || source.actor === undefined || !source.unavoidable()
        || forbid.has(source.actor)) continue;
    const rest = silencedOut(sources.filter(s => s !== source));
    const wanted = [...new Set([...required, source.actor])]
      .sort((a, b) => a - b);
    got = planNight(rest, wanted, forbidden, previous);
    if (got !== null) return got;
  }
  return null;
}
