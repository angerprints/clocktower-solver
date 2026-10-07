// How much explaining a world needs, as a multiplier.
//
// Nothing is ruled out for being unlikely. A world survives if some story
// accounts for everything on the board, and the story's price is what
// separates a reading that simply holds from one that needs a Poisoner to
// have been clairvoyant. 1.0 means every statement stands on its own.
//
// The shape worth keeping in mind: nothing hidden is enumerated up front.
// Who was impaired, who the red herring was, who caught the star, what
// killed each body — each is posited only when something on the board
// would otherwise be false, and priced by how lucky it had to be.

import {CHARACTERS} from "./catalogue.mjs";
import {explainNight} from "./deaths.mjs";
import {minionStillActs, planNight, sourcesOn} from "./impairment.mjs";
import {PRIORS} from "./priors.mjs";
import {phaseIndex} from "./phases.mjs";
import {ABSENT, ARBITRARY, INVERTED, TEAM, abilityState, isEvil}
  from "./roles.mjs";
import {Timeline, change} from "./worlds.mjs";
import {inBag, survivalsOf, teaLadyFailedAtTheGallows}
  from "./characters.rules.mjs";

// What became of a recorded reading in one particular world. Four
// outcomes rather than true-or-false, because two of them are neither.
export const HELD = "held";        // genuine, and what they said was so
export const EXCUSED = "excused";  // genuine and false — something stopped them
export const MADE_UP = "made up";  // wrong token, so it was never theirs
export const INVENTED = "invented";  // nobody here could have produced it
export const SPENT = "spent";      // already used, so it says nothing

/** What a world pays for having made this reading up. */
export const inventionCost = info =>
  Math.min(1.0, PRIORS.FABRICATED_INFO_PENALTY /
                Math.pow(PRIORS.INFO_TRUST_STEP, info.trust || 0));

// --------------------------------------------------------------------
// Consistency
// --------------------------------------------------------------------

/** Does the Scarlet Woman become the Demon if it dies at this phase?
 *
 * Her condition is her own: alive, and five or more players still alive
 * when the Demon goes. She takes priority over any other Minion, so when
 * this is true there is no choice to be made.
 */
export function scarletWomanTakesOver(world, state, phase) {
  const seat = world.findAt("ScarletWoman", phase);
  if (seat === null) return false;
  const alive = state.aliveAt(phase);
  return alive.includes(seat) && alive.length >= 5;
}

/** Which Minions could take the star when the Imp kills itself.
 *
 * The Imp's ability hands the star to a Minion regardless of how many
 * players are left — that count is the Scarlet Woman's condition, not the
 * Imp's. But when she qualifies she takes it.
 */
export function starpassHeirs(world, state, phase) {
  const alive = state.aliveSet(phase);
  const minions = [];
  for (let m = 0; m < state.nPlayers; m++)
    if (world.teamAt(m, phase) === "minion" && alive.has(m)) minions.push(m);
  if (!minions.length) return [];
  if (scarletWomanTakesOver(world, state, phase))
    return [world.findAt("ScarletWoman", phase)];
  return minions;
}

// --------------------------------------------------------------------
// Characters that rewrite other characters
// --------------------------------------------------------------------
// A rule is handed a view of the world with the changes so far applied,
// and answers: what could this character have done, and what does each
// story cost? An empty changes list means "nothing happened", which is
// usually the only answer.
//
// Rules must be anchored to something on the record — a death, an
// execution, an event the table saw. A rule that could fire on any night
// for no reason would multiply the search by seats times nights, for
// stories nothing is asking for.

export const TRANSITION_RULES = [];

// The slot each rule's character acts at, so the rules run in the order
// the night ran.
//
// **Order matters.** Each rule sees the previous ones' work and appends
// its own changes, and `roleAt` takes the last change at a phase — so
// the sequence the rules run in *is* the sequence of the night.
//
// They ran Barber, Pit-Hag, Farmer, Snake Charmer — slots 40, 16, 48 and
// 11, almost exactly backwards.
const ACTS_AT = {
  aSnakeCharmerTakesTheStar: 11,
  aPitHagMakesSomebodyElse: 16,
  aBarberLetsTheDemonSwapTwo: 40,
  aFarmerHandsItOn: 48,
  anOgrePicksASide: 60,                  // late on night one
  demonHandovers: 99,                    // a death, so after everything
};

export const transitionRule = fn => (
  TRANSITION_RULES.push(fn),
  TRANSITION_RULES.sort((a, b) =>
    (ACTS_AT[a.name] ?? 50) - (ACTS_AT[b.name] ?? 50)),
  fn);

export const HEIR_RULES = [];
export const heirRule = fn => (HEIR_RULES.push(fn), fn);

/** Every account of who was what, and when.
 *
 * Rules compose: each is offered the changes agreed so far and may add
 * its own. An empty result from any rule means nothing can explain this
 * world, which is how a Demon dead in daylight with nobody to inherit
 * gets ruled out.
 */
// 128, not 48: a Barber's death offers every pair of seats. A night at a
// time when more than one rule can move anybody. See solver.py.
export function possibleTimelines(world, state, cap = 128) {
  // Counted in this world, not on the script. See solver.py.
  if (moversIn(world, state) < 2) return allNightsAtOnce(world, state, cap);
  const last = Math.max(1, parseInt(state.finalPhase().slice(1), 10));
  try {
    return nightByNight(world, state, cap, last)
      .map(([changes, weight]) => [changes, weight]);
  } finally {
    state._horizon = null;
  }
}

/** How many kinds of change could actually happen in this world. */
function moversIn(world, state) {
  const made = new Set();
  let swapped = false;
  for (const info of state.infos) {
    const source = info.sourceRole;
    if (source === "PitHag" && info.role) made.add(info.role);
    else if (source === "SnakeCharmer" && info.swapped) swapped = true;
  }
  const deaths = [...state.deathPhases()].filter(([, p]) => p);
  const phases = deaths.map(([, p]) => p);
  const atNight = phases.some(p => p[0].toUpperCase() === "N");
  // A Barber counts only once a seat that claimed it has died.
  const claimed = barberClaimants(state);
  const barberDied = deaths.some(([s]) => claimed.has(Number(s)));
  const roles = new Set([...world.roles, ...made]);
  let count = (swapped ? 1 : 0) + (made.size ? 1 : 0);
  for (const [key, needs] of [["Barber", barberDied], ["Farmer", atNight],
                              ["FangGu", atNight], ["Ogre", true]])
    if (needs && roles.has(key) && inBag(state, key)) count++;
  return count;
}

/** Every rule once, over the whole game, in night-slot order. */
function allNightsAtOnce(world, state, cap) {
  let stories = [[[], 1.0]];
  for (const rule of TRANSITION_RULES) {
    const grown = [];
    outer:
    for (const [changes, weight] of stories) {
      const view = changes.length ? new Timeline(world, changes) : world;
      for (const [extra, cost] of rule(view, state)) {
        grown.push([[...changes, ...extra], weight * cost]);
        if (grown.length >= cap) break outer;
      }
    }
    if (!grown.length) return [];
    stories = grown;
  }
  return stories;
}

const nightOf = c => parseInt(c.phase.slice(1), 10);
// Worked out once per change: the night passes ask for the same keys and
// moments of the same few changes hundreds of times per world.
const KEYS = new WeakMap(), MOMENTS = new WeakMap();
const sameChange = (a, b) => a === b || (a.phase === b.phase &&
  a.seat === b.seat && (a.role ?? null) === (b.role ?? null) &&
  (a.side ?? null) === (b.side ?? null));
const changeKey = c => {
  let k = KEYS.get(c);
  if (k === undefined) KEYS.set(c, k = `${c.phase}|${c.seat}|${c.role}|${c.side}`);
  return k;
};
const momentOf = c => {
  let m = MOMENTS.get(c);
  if (m === undefined) MOMENTS.set(c, m = phaseIndex(c.phase));
  return m;
};

/** A night at a time, each rule seeing everything but its own earlier
 * work. Stories are [changes, weight, owned] with owned = [[i, changes]].
 * Only the last pass may call a story impossible. See solver.py. */
/** The nights a transition rule could add anything, or null for all. The
 * last pass still asks every rule about the whole game. See solver.py. */
function nightsItActs(rule, state) {
  const deaths = [];
  for (const [seat, phases] of Object.entries(state.deaths || {}))
    for (const p of phases) deaths.push([parseInt(p.slice(1), 10), p[0].toUpperCase()]);
  const rows = (role, field) => new Set(state.infos
    .filter(i => i.sourceRole === role && i[field]).map(i => i.night));
  switch (rule.name) {
    case "aBarberLetsTheDemonSwapTwo": {
      const claimed = barberClaimants(state);
      const out = new Set();
      for (const [seat, phases] of Object.entries(state.deaths || {}))
        if (claimed.has(Number(seat)))
          for (const p of phases) {
            const k = parseInt(p.slice(1), 10);
            out.add(p[0].toUpperCase() !== "N" ? k + 1 : k);
          }
      return out;
    }
    case "aPitHagMakesSomebodyElse": return rows("PitHag", "role");
    case "aSnakeCharmerTakesTheStar": return rows("SnakeCharmer", "swapped");
    case "aFarmerHandsItOn":
      return new Set(deaths.filter(([, kind]) => kind === "N").map(([k]) => k));
    case "anOgrePicksASide": return new Set([1]);
    case "demonHandovers": return new Set(deaths.map(([k]) => k));
    default: return null;
  }
}

function nightByNight(world, state, cap, last) {
  let stories = [[[], 1.0, []]];
  const acts = TRANSITION_RULES.map(rule => nightsItActs(rule, state));
  for (let night = 1; night <= last; night++) {
    const final = night === last;
    state._horizon = night;
    for (let i = 0; i < TRANSITION_RULES.length; i++) {
      const rule = TRANSITION_RULES[i];
      if (!final && acts[i] !== null && !acts[i].has(night)) continue;
      const grown = [];
      const seen = new Map();
      const keep = (changes, got, owned) => {
        const owner = new Map();
        for (const [k, mine] of owned) for (const c of mine) owner.set(changeKey(c), k);
        const ordered = changes.map((c, idx) => [c, idx, momentOf(c),
            owner.get(changeKey(c)) ?? TRANSITION_RULES.length])
          .sort((a, b) => a[2] - b[2] || a[3] - b[3] || a[1] - b[1])
          .map(([c]) => c);
        const key = ordered.map(changeKey).join(";");
        if (seen.has(key)) {
          const j = seen.get(key);
          if (got > grown[j][1]) grown[j] = [ordered, got, owned];
          return;
        }
        seen.set(key, grown.length);
        grown.push([ordered, got, owned]);
      };
      for (const [changes, weight, owned] of stories) {
        if (grown.length >= cap) break;
        const entry = owned.find(([k]) => k === i);
        const mine = entry ? entry[1] : [];
        const mineKeys = new Set(mine.map(changeKey));
        const others = mine.length
          ? changes.filter(c => !mineKeys.has(changeKey(c))) : changes;
        const earlier = mine.filter(c => nightOf(c) < night);
        const view = others.length ? new Timeline(world, others) : world;
        let fitted = false;
        for (const [extra, cost] of rule(view, state)) {
          // What this rule settled for earlier nights has to stand. Asked
          // first and without building keys: on the last pass a Barber
          // offers every pair again to each of its fifty-odd stories, and
          // all but one offer fail here.
          if (earlier.some(m => !extra.some(c => sameChange(c, m))))
            continue;                     // another story's earlier night
          const upto = extra.filter(c => nightOf(c) <= night);
          fitted = true;
          const added = upto.some(c => !mine.some(m => sameChange(m, c)));
          const again = owned.filter(([k]) => k !== i);
          keep([...others, ...upto], weight * (added ? cost : 1.0),
               [...again, [i, upto]]);
          if (grown.length >= cap) break;
        }
        if (!fitted && !final) keep(changes, weight, owned);
      }
      if (!grown.length) return [];
      stories = grown;
    }
  }
  return stories;
}

// The Demon may swap two players when a Barber dies, and mostly does
// not — a deliberate play with a cost, not the default.
export const BARBER_SWAP_PENALTY = 0.15;

/** The Barber died today, so tonight the Demon may swap two players.
 *
 * Characters only — a swapped player keeps their side, so a good player
 * can end up holding a Minion's character. Rare, legal, and the reason
 * `Change` keeps its two halves separate.
 *
 * Anchored to the Barber's death. A "may", so doing nothing comes first,
 * because it is what usually happened.
 */
const barberRule = transitionRule(function aBarberLetsTheDemonSwapTwo(world, state) {
  if (!inBag(state, "Barber")) return [[[], 1.0]];
  // Its offers depend only on the board it is shown, and a night-by-night
  // solve shows it the same board once per story it already made — fifty
  // times over. Kept per deal and per exact set of changes. See solver.py.
  const base = world instanceof Timeline ? world.world : world;
  const memo = memoFor(base, "_barberMemo", state);
  const key = (world.changes || []).map(changeKey).join(";");
  let got = memo.got.get(key);
  if (got === undefined) memo.got.set(key, got = barberOffers(world, state));
  return got;
});

/** Seats that said they were the Barber — as their claim, or in a row
 * saying they became it or had been it. A swap is only considered once
 * one of them has died (table ruling). See solver.py. */
export function barberClaimants(state) {
  const out = new Set();
  for (const [seat, role] of Object.entries(state.claims || {}))
    if (role === "Barber") out.add(Number(seat));
  for (const info of state.infos)
    if (info.type === "Became" && (info.role === "Barber" || info.was === "Barber"))
      out.add(Number(info.player));
  return out;
}

function barberOffers(world, state) {
  // Whoever was the Barber when they died, dealt or made — and claimed
  // it. See solver.py.
  const claimed = barberClaimants(state);
  const deaths = [];
  for (let seat = 0; seat < state.nPlayers; seat++)
    if (claimed.has(seat)) for (const phase of state.diedAt(seat))
      if (world.roleAt(seat, phase) === "Barber") deaths.push(phase);
  if (!deaths.length) return [[[], 1.0]];

  const stories = [[[], 1.0]];
  for (const phase of deaths) {
    const day = parseInt(phase.slice(1), 10);
    const night = "NDEX".indexOf(phase[0].toUpperCase()) > 0
      ? `N${day + 1}` : `N${day}`;
    if (phaseIndex(night) > phaseIndex(state.finalPhase())) continue;
    const demon = world.demonAt(night);
    for (let first = 0; first < state.nPlayers; first++)
      for (let second = first + 1; second < state.nPlayers; second++) {
        const a = world.roleAt(first, night), b = world.roleAt(second, night);
        if (a === b) continue;
        // Sides written out: a swap moves characters, never sides.
        const sideA = world.evilAt(first, night) ? "evil" : "good";
        const sideB = world.evilAt(second, night) ? "evil" : "good";
        // The Demon with one of its own Minions costs a world nothing;
        // any other pair is priced as a deliberate play (table habit).
        const ours = (first === demon && TEAM[b] === "minion") ||
                     (second === demon && TEAM[a] === "minion");
        const pair = [change(night, first, b, sideA),
                      change(night, second, a, sideB)];
        for (const c of pair)
          Object.defineProperty(c, "barber", {value: ours ? "ours" : "other"});
        stories.push([pair, ours ? 1.0 : BARBER_SWAP_PENALTY]);
      }
  }
  return stories;
}

// Demons that hand the star on when they kill themselves. The Imp is the
// only one in print, and saying so out loud matters: this used to be
// offered to *every* Demon dying at night, so a Zombuul or a Fang Gu
// that fell to a Slayer or an Assassin could quietly pass to a Minion
// and the game carried on. Good had actually won.
export const STARPASSES = new Set(["Imp"]);

/** The Imp kills itself and a Minion takes over.
 *
 * Only the Imp. Every other Demon dying at night is the end of it —
 * unless that Demon has a rule of its own, like the Fang Gu jumping into
 * an Outsider.
 */
heirRule(function aMinionCatchesTheStar(view, state, phase, character) {
  if (phase[0].toUpperCase() !== "N" || !STARPASSES.has(character)) return [];
  return starpassHeirs(view, state, phase)
    .map(seat => change(phase, seat, character));
});

/** The Fang Gu killed an Outsider, and they took its place.
 *
 * Not a death and a replacement: the Outsider *lives*, turns evil and
 * becomes the Fang Gu, and the old one dies instead. So the table sees
 * exactly one body — the Demon's own seat — which is why this belongs
 * with the handovers rather than with the kills.
 *
 * Once per game, so it is offered only while the star is still where it
 * was dealt.
 */
heirRule(function anOutsiderBecomesTheFangGu(view, state, phase, character) {
  if (character !== "FangGu" || phase[0].toUpperCase() !== "N") return [];
  // Once per game, asked of the jump itself: an evil Fang Gu written onto
  // a seat dealt an Outsider. A Snake Charmer swap moves the star too.
  if ((view.changes || []).some(c => c.role === "FangGu" && c.side === "evil"
      && TEAM[view.roles[c.seat]] === "outsider"
      && phaseIndex(c.phase) < phaseIndex(phase))) return [];
  const alive = state.aliveSet(phase);
  const out = [];
  for (let seat = 0; seat < state.nPlayers; seat++)
    if (alive.has(seat) && view.teamAt(seat, phase) === "outsider")
      out.push(change(phase, seat, "FangGu", "evil"));
  return out;
});

/** The Demon killed in daylight, with her standing by. */
heirRule(function theScarletWomanStepsUp(view, state, phase, character) {
  if (phase[0].toUpperCase() === "N") return [];
  if (!scarletWomanTakesOver(view, state, phase)) return [];
  return [change(phase, view.findAt("ScarletWoman", phase), character)];
});

/** Was this seat executed on this day by any route the rules call an
 * execution: the vote, a Virgin's nominator, a Cerenovus's madness. Not a
 * Slayer's shot or a Witch's curse. See solver.py. */
function executed(state, day, seat) {
  if (state.executedOn(day) === seat) return true;
  if ((state.madnessExecutions || {})[day] === seat) return true;
  return state.infos.some(info =>
    info.type === "VirginNomination" && info.triggered &&
    info.night === day && info.nominator === seat);
}

/** Could play have carried on with no Demon at all? Only after an
 * execution, with the Mastermind alive, and for one more day. Whether it
 * was working, and whether a Scarlet Woman should have taken over, are
 * asked of the plan where the story's marker is found. */
function mastermindDay(world, state, phase, holder) {
  if (!inBag(state, "Mastermind") || phase[0].toUpperCase() !== "D")
    return false;
  const day = parseInt(phase.slice(1), 10);
  if (!executed(state, day, holder)) return false;
  const seat = world.findAt("Mastermind", phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return false;
  return phaseIndex(state.finalPhase()) <= phaseIndex(`D${day + 1}`);
}

/** The mark a Mastermind's extra day leaves in a story: a change that
 * changes nothing, on the executed Demon. Nothing else writes one. */
export const mastermindMarker = (phase, seat) => change(phase, seat, null, null);
export const isMastermindMarker = c =>
  (c.role === null || c.role === undefined) &&
  (c.side === null || c.side === undefined);

/** Every way the Demon could have changed hands in this world.
 *
 * The timing is not a free choice — it is pinned by the deaths already on
 * the record. A Demon dead at night killed itself, and the star has to
 * land on a living Minion. A Demon killed in daylight ends the game
 * outright unless the Scarlet Woman was standing by.
 *
 * Empty means no story fits, and the world is impossible.
 */
export function demonLineages(world, state, cap = 24) {
  const start = world.demonAt("N1");
  if (start === null) return [[]];

  const found = [];

  const walk = (view, holder, soFar, after = -1, held = new Set()) => {
    if (found.length >= cap) return;
    // The first time they went down. A Demon raised afterwards is
    // somebody else's problem to model; the star passed when it fell.
    // A seat that stopped being the Demon before it died hands nothing
    // on. A Snake Charmer swap moves the Demon to the charmer's seat and
    // leaves a *good* Snake Charmer behind — and when the new Demon
    // later kills that seat, this walk was still tracking it as the
    // holder, looked for an heir, found none, and declared the whole
    // world impossible.
    // A Zombuul's first death is not one: it registers dead and goes on
    // killing, so nobody inherits. Only the second is real. See solver.py.
    let phases = state.diedAt(holder);
    if (phases.length && view.roleAt(holder, phases[0]) === "Zombuul")
      phases = phases.slice(1);
    // Not yet, on a pass that only looks this far (possibleTimelines).
    const horizon = state._horizon ?? null;
    if (horizon !== null)
      phases = phases.filter(p => parseInt(p.slice(1), 10) <= horizon);
    const phase = phases.length ? phases[0] : null;
    // Moved sideways before it died, or before the board ends: follow the
    // star to whoever holds it now. See solver.py.
    const check = phase !== null ? phase
      : (horizon !== null ? `D${horizon}` : state.finalPhase());
    {
      const was = view.roleAt(holder, check);
      if (was && TEAM[was] !== "demon") {
        const successor = view.demonAt(check);
        if (successor !== null && successor !== holder && !held.has(successor)) {
          walk(view, successor, soFar, after, new Set([...held, holder]));
          return;
        }
        found.push(soFar);
        return;
      }
    }
    // A handover cannot happen *earlier* than the one before it, and no
    // seat can hold the star twice. Both were true by construction until
    // a Barber let the Demon swap characters around, and the walk went
    // round for ever. The same phase is fine: a Shabaloth kills twice, so
    // the Demon and its heir can fall together.
    if (phase !== null && (phaseIndex(phase) < after || held.has(holder))) {
      found.push(soFar);
      return;
    }
    if (phase === null) {
      found.push(soFar);                  // they held it to the end
      return;
    }
    const character = view.roleAt(holder, phase);
    const moves = [];
    for (const rule of HEIR_RULES)
      moves.push(...rule(view, state, phase, character));

    // A Mastermind buys one more day after the Demon is executed. Nobody
    // inherits — there simply is no Demon after this — so the lineage
    // ends here rather than continuing.
    if (mastermindDay(view, state, phase, holder))
      found.push([...soFar, mastermindMarker(phase, holder)]);

    // No offers at all, and no Mastermind, means good won right there.
    for (const move of moves) {
      if (move.seat === null) continue;
      const grown = [...soFar, move];
      walk(new Timeline(world, grown), move.seat, grown,
           phaseIndex(phase), new Set([...held, holder]));
    }
  };

  walk(world, start, []);
  return found;
}

/** Recorded creations, applied from the night they happened.
 *
 * The side is carried over rather than taken from the new character: a
 * Townsfolk turned into the Poisoner keeps its own side and gains the
 * ability, which is what makes a good Poisoner possible.
 */
transitionRule(function aPitHagMakesSomebodyElse(world, state) {
  const made = state.infos.filter(
    i => i.sourceRole === "PitHag" && i.role);
  if (!made.length) return [[[], 1.0]];
  const changes = made.map(info => {
    const phase = `N${info.night}`;
    // The side when the Pit-Hag acted, as the night began. See solver.py.
    const before = info.night > 1 ? `E${info.night - 1}` : "N0";  // the deal, as Python's `_before`
    const side = world.evilAt(info.target, before) ? "evil" : "good";
    return change(phase, info.target, info.role, side);
  });
  return [[changes, 1.0]];
});

/** Choosing the Demon swaps character and side, both ways.
 *
 * The only handover where the star moves *sideways* rather than on: the
 * Snake Charmer becomes the Demon, and the Demon becomes a good Snake
 * Charmer — poisoned from that moment for the rest of the game.
 *
 * Applied from the *day* after, not the night itself. The swap happens
 * because the ability worked, so it was still the Snake Charmer when it
 * did; writing the change at the night made the speaker stop holding
 * that character at the moment its row is attributed, and the row read
 * as invented.
 */
/** Could this seat have shown as good, if the Storyteller liked?
 *
 * Registration, not truth. A Spy is evil and registers as good, so the
 * Storyteller may hand it the Farmer on that basis — and it stays evil.
 */
function couldBeGood(world, seat, phase) {
  if (!world.evilAt(seat, phase)) return true;
  const regs = CHARACTERS[world.roleAt(seat, phase)].registers || [];
  return regs.includes("townsfolk") || regs.includes("outsider");
}

/** It died in the night, so somebody good becomes the Farmer.
 *
 * **Any** night death does it, not only the Demon's, and not an
 * execution. "Nothing happened" stays among the answers and is the
 * droisoned case — whether a seat was droisoned is chosen by the
 * impairment plan, which runs after transitions are settled.
 *
 * It chains, so every seat holding the character is considered rather
 * than the first: `findAt` returns the Farmer that was *dealt*, and that
 * seat goes on being a Farmer in the base world after it dies.
 */
transitionRule(function aFarmerHandsItOn(world, state) {
  if (!inBag(state, "Farmer")) return [[[], 1.0]];
  let stories = [[[], 1.0]];
  const latest = phaseIndex(state.finalPhase());
  for (let night = 1; phaseIndex(`N${night}`) <= latest; night++) {
    const phase = `N${night}`;
    const grown = [];
    for (const [changes, cost] of stories) {
      const view = changes.length ? new Timeline(world, changes) : world;
      const holders = [];
      for (let p = 0; p < state.nPlayers; p++)
        if (view.roleAt(p, phase) === "Farmer" &&
            state.diedAt(p).includes(phase)) holders.push(p);
      if (!holders.length) { grown.push([changes, cost]); continue; }
      const seat = holders[0];
      const heirs = [...state.aliveSet(phase)]
        .filter(p => p !== seat && couldBeGood(view, p, phase));
      grown.push([changes, cost]);
      for (const heir of heirs)
        grown.push([[...changes, change(`D${night}`, heir, "Farmer", null)],
                    cost]);
    }
    stories = grown.slice(0, 48);
  }
  return stories;
});

/** Would this seat hand an Ogre the evil side? Its true side, and the
 * jinx: the Spy and the Recluse register as evil to the Ogre. */
function evilToTheOgre(view, seat, phase) {
  if (view.evilAt(seat, phase)) return true;
  const regs = CHARACTERS[view.roleAt(seat, phase)].registers || [];
  return regs.includes("minion") || regs.includes("demon");
}

/** On its first night the Ogre takes the side of whoever it chose, even
 * if drunk or poisoned, and never learns which. Written from the first
 * day: it acts after the night's information roles. Unrecorded, turning
 * evil is weighed evil seats against good ones. See solver.py.
 */
transitionRule(function anOgrePicksASide(world, state) {
  if (!inBag(state, "Ogre")) return [[[], 1.0]];
  const ogre = world.findAt("Ogre", "N1");
  if (ogre === null || ogre === undefined) return [[[], 1.0]];
  const turn = [change("D1", ogre, null, "evil")];

  const picked = state.infos.filter(
    i => i.sourceRole === "Ogre" && i.player === ogre);
  if (picked.length) {
    const target = picked[0].target;
    if (target === ogre) return [];      // "not yourself"
    return evilToTheOgre(world, target, "N1") ? [[turn, 1.0]] : [[[], 1.0]];
  }

  let evil = 0, good = 0;
  for (let p = 0; p < state.nPlayers; p++) {
    if (p === ogre) continue;
    if (evilToTheOgre(world, p, "N1")) evil++; else good++;
  }
  if (good === 0) return [[turn, 1.0]];
  return [[[], 1.0], [turn, Math.min(1.0, evil / good)]];
});

/** Does this seat have that ability — held, or taken by a Philosopher? */
function hasAbility(world, state, seat, role, phase) {
  if (world.roleAt(seat, phase) === role) return true;
  const taken = state.philosophies()[seat];
  return !!(taken && taken[0] === role &&
            world.roleAt(seat, phase) === "Philosopher" &&
            phaseIndex(phase) >= phaseIndex(taken[1]));
}

/** Who has this ability — held, or gained by a Philosopher. */
function whoeverWorks(world, state, role, phase) {
  const seat = world.findAt(role, phase);
  if (seat !== null) return seat;
  for (const [who, [taken, since]] of Object.entries(state.philosophies()))
    if (taken === role && world.roleAt(+who, phase) === "Philosopher" &&
        phaseIndex(phase) >= phaseIndex(since)) return +who;
  return null;
}

transitionRule(function aSnakeCharmerTakesTheStar(world, state) {
  const swaps = state.infos.filter(
    i => i.sourceRole === "SnakeCharmer" && i.swapped);
  if (!swaps.length) return [[[], 1.0]];

  let stories = [[[], 1.0]];
  const base = world;
  for (const info of [...swaps].sort((a, b) => a.night - b.night)) {
    // Each swap sees the ones before it. See solver.py.
    const soFar = stories.length ? stories[0][0] : [];
    world = soFar.length ? new Timeline(base, soFar) : base;
    // Who *acted*, which is the board as it stood when the night began —
    // not after the swap this rule is about to write. The swap is dated
    // at the night now that it is immediate.
    const phase = `N${info.night}`;
    const began = info.night > 1 ? `E${info.night - 1}` : "N0";  // the deal, as Python's `_before`
    // The seat that said so, if it has the ability — held or taken by a
    // Philosopher — else whoever works it. See solver.py.
    const charmer = hasAbility(world, state, info.player, "SnakeCharmer", began)
      ? info.player : whoeverWorks(world, state, "SnakeCharmer", began);
    const demon = world.demonAt(began);
    if (charmer === null || demon === null || charmer === demon) continue;
    if (info.target !== demon) continue;   // they pointed at somebody else
    // From the night: the swap is immediate (settled at the table; the
    // attribution above reads the board as it began). Python has written
    // it at the night for a while and this still said the day after.
    const after = `N${info.night}`;
    stories = stories.map(([changes, cost]) => [
      [...changes,
       // The character the Demon held **when the swap happened**, at
       // slot 11 — not whatever it holds by the end of the night. Read
       // at `phase` this took the board after the rules that run first,
       // so on a night with a Pit-Hag the charmer was handed the
       // Pit-Hag's gift instead of the Demon's character and the Demon
       // vanished from the board.
       change(after, charmer, world.roleAt(demon, began), "evil"),
       change(after, demon, "SnakeCharmer", "good")],
      cost]);
  }
  return stories;
});

/** The Demon dying, as a transition rule.
 *
 * A starpass is not charged for: the Demon's own seat dying at night is
 * already discounted hard by the night-death prior, and billing it twice
 * would be double-counting.
 */
transitionRule(function demonHandovers(world, state) {
  return demonLineages(world, state).map(chain => [chain, 1.0]);
});

// --------------------------------------------------------------------
// Sorting the ledger
// --------------------------------------------------------------------

/** {night: [seats that died that night]} */
export function nightDeaths(state) {
  const out = {};
  for (const [seat, phase] of state.deathPhases())
    if (phase && phase[0].toUpperCase() === "N") {
      const night = parseInt(phase.slice(1), 10);
      (out[night] = out[night] || []).push(seat);
    }
  return out;
}

/** Roles pinned down by events the whole table watched.
 *
 * The same facts the hard checks enforce, handed to the search up front
 * so it never builds the worlds they rule out. Without this a Virgin
 * trigger still gives the right answer — it just has to generate and
 * discard millions of worlds to get there.
 */
export function forcedRoles(state) {
  const pinned = {};
  const pin = (seat, roles) => {
    const wanted = new Set(roles);
    pinned[seat] = pinned[seat]
      ? new Set([...pinned[seat]].filter(r => wanted.has(r)))
      : wanted;
  };
  for (const info of state.infos) {
    if (info.type === "VirginNomination" && info.triggered) {
      pin(info.player, ["Virgin"]);
      // The nomination only fires on a Townsfolk, or the Spy wearing one.
      // The Drunk is an Outsider, so a Drunk nominator is out.
      const spies = state.script.keys.filter(
        k => CHARACTERS[k].registers.includes("townsfolk"));
      pin(info.nominator, [...state.script.townsfolk, ...spies]);
    } else if (info.type === "SlayerShot" && info.died) {
      pin(info.player, ["Slayer"]);
      pin(info.target, ["Imp", "Recluse"]);
    }
  }
  return pinned;
}

/** Quiet Virgin nominations that carry nothing.
 *
 * The ability only fires the first time a Townsfolk nominates, so once
 * one nomination is on the record the later quiet ones say nothing.
 */
/** What it costs this world that its Zealot did not vote, on a day with
 * a nomination and five alive. Priced, not impossible: the likelier
 * story at a real table is a vote nobody wrote down. See solver.py. */
function aZealotKeptItsHandDown(world, state) {
  if (!inBag(state, "Zealot")) return 1.0;
  let cost = 1.0;
  for (const key of Object.keys(state.votes || {})) {
    const day = Number(key);
    const voted = new Set(state.votes[key] || []);
    const named = (state.nominations || {})[key];
    if (!voted.size || !named || !new Set(named).size) continue;
    const phase = `D${day}`;
    const alive = [...state.aliveSet(phase)];
    const hanged = state.executionDeath(day);
    const fell = alive.filter(p => state.diedAt(p).includes(phase)
                                   && hanged !== p).length;
    if (alive.length - fell < 5) continue;
    for (const seat of alive)
      if (!voted.has(seat) && !state.diedAt(seat).includes(phase)
          && world.roleAt(seat, phase) === "Zealot")
        cost *= PRIORS.ZEALOT_SILENT_PENALTY;
  }
  return cost;
}

function spentNominations(state) {
  if (state._spentNoms) return state._spentNoms;
  const spent = new Set(), seen = new Set();
  const order = state.infos.map((info, i) => [i, info])
    .filter(([, info]) => info.type === "VirginNomination")
    .sort((a, b) => a[1].night - b[1].night);
  for (const [i, info] of order) {
    if (seen.has(info.player) && !info.triggered) spent.add(i);
    seen.add(info.player);
  }
  state._spentNoms = spent;
  return spent;
}

function sourceSeats(state) {
  if (!state._sourceSeats)
    state._sourceSeats = state.infos.map(info => info.sourceSeat(state));
  return state._sourceSeats;
}

/** Sort every ledger row into: fits, contradicts, or was invented.
 *
 * Returns {failures, ftInfos, invented, mustWork}, or null if the world
 * is flatly impossible. The invention cost is a product rather than a
 * count, because how much a made-up reading costs depends on how far you
 * said you believed it.
 */
function plainFailures(world, state, outcome = {}) {
  const failures = {};
  const working = {};
  const ftInfos = [];
  let invented = 1.0;
  // A hard fact that did not hold. Kept apart from the cost: this was
  // `invented = null`, and the next made-up row multiplied it —
  // null times anything is nought in JavaScript, so the world came back
  // costing nothing instead of impossible, and was counted (found by
  // the first board with a Banshee announced, 07.10.2026).
  let impossible = false;
  const fail = (night, seat) =>
    ((failures[night] = failures[night] || new Set()).add(seat));
  // Nights where a reading came out true under a Vortox: either the
  // Vortox was off or the sources were droisoned. See solver.py.
  const vortoxOr = {};

  // Executing the Saint ends the game on the spot — while it is
  // *working*. A poisoned or drunk Saint is executed and the game carries
  // on, so an execution that killed somebody does not rule the Saint out;
  // it says something had to have stopped them.
  // A day that ended with nobody executed, and the game carried on.
  //
  // Evil wins on the spot if a Vortox is working when that happens, so
  // play continuing says there was not one — that day. Per day rather
  // than per game, because a Pit-Hag can bring one along later.
  for (const day of [...state.daysDone].sort((a, b) => a - b)) {
    if ((state.executions || {})[day] !== undefined) continue;
    const vortox = world.findAt("Vortox", `D${day}`);
    if (vortox === null || !state.aliveSet(`D${day}`).has(vortox)) continue;
    fail(day, vortox);
  }

  // Two deaths that name a character nobody chose to reveal, and the one
  // who did it has to have been working.
  for (const [day, ] of Object.entries(state.witchDeaths || {})) {
    const witch = world.findAt("Witch", `N${day}`);
    if (witch === null || !minionStillActs(world, state, witch, `N${day}`))
      return null;
    // "If just 3 players live, you lose this ability" — and the curse
    // goes with it.
    if (state.aliveSet(`D${day}`).size <= 3) return null;
    (working[day] = working[day] || new Set()).add(witch);
  }
  for (const [day, ] of Object.entries(state.madnessExecutions || {})) {
    const who = world.findAt("Cerenovus", `N${day}`);
    if (who === null || !minionStillActs(world, state, who, `N${day}`))
      return null;
    (working[day] = working[day] || new Set()).add(who);
  }

  // The good twin executed, and the game carried on. Evil wins on the
  // spot when that happens, so play continuing says the Evil Twin was not
  // working — or that the one who hanged was the evil one, which is the
  // deduction the table draws and this never did (02.10.2026).
  for (const info of state.infos) {
    if (info.type !== "EvilTwinPair") continue;
    for (const day of Object.keys(state.executions || {}).map(Number)) {
      const hanged = state.executionDeath(day);
      if (hanged !== info.a && hanged !== info.b) continue;
      const other = hanged === info.a ? info.b : info.a;
      const phase = `D${day}`;
      if (world.roleAt(other, phase) !== "EvilTwin" ||
          !state.aliveSet(phase).has(other) ||
          world.evilAt(hanged, phase)) continue;
      fail(day, other);
    }
  }

  // A Mastermind's extra day: it had to be working, and a Scarlet Woman
  // who qualified would have taken over instead, so she was not.
  for (const c of world.changes || []) {
    if (!isMastermindMarker(c)) continue;
    const day = parseInt(c.phase.slice(1), 10);
    const mastermind = world.findAt("Mastermind", c.phase);
    if (mastermind === null || !state.aliveSet(c.phase).has(mastermind))
      return null;
    (working[day] = working[day] || new Set()).add(mastermind);
    if (scarletWomanTakesOver(world, state, c.phase))
      fail(day, world.findAt("ScarletWoman", c.phase));
  }

  for (const day of Object.keys(state.executions || {}).map(Number)) {
    const seat = state.executionDeath(day);
    if (seat === null) continue;
    if (world.roleAt(seat, `D${day}`) === "Saint") fail(day, seat);
    // A Sailor cannot die, and that holds in daylight — so a working one
    // walks away from its own execution.
    if (world.roleAt(seat, `D${day}`) === "Sailor") fail(day, seat);
    // And the same for a Tea Lady's neighbour: executed and dead, so she
    // was not working. The mirror of her saving one.
    const lady = teaLadyFailedAtTheGallows(world, state, day, seat);
    if (lady !== null) fail(day, lady);
  }

  // Somebody standing again needs a reason, and the reason has to have
  // been working. Two characters do it.
  //
  // A Professor raises one Townsfolk, once — which is not the same as
  // raising somebody good: the Spy registers as one.
  //
  // A Shabaloth may regurgitate somebody it chose the night before,
  // whatever they are and as often as the Storyteller likes. That was
  // missing altogether: with no Professor in the world the board was
  // thrown out, and a second resurrection always was (02.10.2026).
  let byProfessor = 0;
  for (const [seatKey, phases] of Object.entries(state.resurrections || {})) {
    const seat = Number(seatKey);
    for (const phase of phases) {
      const night = parseInt(phase.slice(1), 10);
      if (!Number.isFinite(night)) continue;
      const shabaloth = inBag(state, "Shabaloth")
        ? world.findAt("Shabaloth", phase) : null;
      if (shabaloth !== null && night >= 3 &&
          state.aliveSet(phase).has(shabaloth)) continue;
      const prof = world.findAt("Professor", phase);
      if (prof === null || !inBag(state, "Professor")) return null;
      if (!state.aliveSet(phase).has(prof) || night < 2) return null;
      const raised = world.roleAt(seat, phase);
      if (TEAM[raised] !== "townsfolk" &&
          !CHARACTERS[raised].registers.includes("townsfolk")) return null;
      (working[night] = working[night] || new Set()).add(prof);
      byProfessor += 1;
    }
  }
  if (byProfessor > 1) return null;       // once per game

  // An execution that killed nobody needs a reason, and the reason has to
  // have been working.
  for (const [dayKey, seat] of Object.entries(state.executions || {})) {
    const day = Number(dayKey);
    if (state.executionDeath(day) !== null) continue;
    const survivors = new Set(survivalsOf(world, state, day, seat));
    if (!survivors.size) return null;     // nothing here survives one
    // One of them did it, and that one was working. With a single
    // candidate that is a demand; with several it is "one of these",
    // which the plan cannot hold. Demanding all of them threw out a
    // Devil's Advocate's rescue whenever a Pacifist on the same board was
    // drunk — and it replaced whatever else had to be working that day.
    if (survivors.size === 1) {
      const set = (working[day] = working[day] || new Set());
      for (const who of survivors) set.add(who);
    }
  }

  invented *= aZealotKeptItsHandDown(world, state);

  const spent = spentNominations(state);
  const seats = sourceSeats(state);
  state.infos.forEach((info, idx) => {
    if (spent.has(idx)) { outcome[idx] = SPENT; return; }
    if (info.hard()) {
      if (!info.holds(world, state, null)) { impossible = true; }
      else {
        outcome[idx] = HELD;
        // A fact can lean on somebody too: a Banshee announced was a
        // Banshee whose ability worked that night.
        for (const who of info.leanedOn(world, state)) {
          working[info.night] = working[info.night] || new Set();
          working[info.night].add(who);
        }
      }
      return;
    }
    // Something that happened in front of everybody and is judged by what
    // the day did with it — a claim to be the Goblin. Nobody is its
    // source, so there is nobody to have invented it.
    if (info.event) {
      const failed = info.mustHaveFailed(world, state);
      for (const who of failed) fail(info.night, who);
      outcome[idx] = failed.length ? EXCUSED : HELD;
      return;
    }
    const role = info.sourceRole;
    const phase = `N${info.night}`;
    let seat = seats[idx];
    if (seat === null) {
      // Who acted, not who holds the character now — a swap dated at
      // this night would otherwise find the seat it ended up at.
      const began = info.night > 1 ? `E${info.night - 1}` : "N0";  // the deal, as Python's `_before`
      seat = world.findAt(role, began);
      if (seat === null) seat = world.findAt(role, phase);
      if (seat === null)
        // Nobody holds it — but a Philosopher may be working it.
        for (const [who, [taken, since]]
             of Object.entries(state.philosophies()))
          if (taken === role && world.roleAt(+who, phase) === "Philosopher"
              && phaseIndex(phase) >= phaseIndex(since)) {
            seat = +who;
            break;
          }
      if (seat === null) {
        const at = world.believes.indexOf(role);
        seat = at === -1 ? null : at;
      }
    }
    // A Philosopher works two abilities at once, so a seat holding one
    // may be the source of the other's readings from the night it took
    // them.
    let gained = null;
    const took = state.philosophies()[seat];
    if (took) gained = [took[0], took[1],
                        phaseIndex(phase) >= phaseIndex(took[1])];
    // A Vortox in play makes every Townsfolk ability yield something
    // false. Alive, because a dead Demon does nothing; its own
    // droisoning is left to the plan rather than decided here.
    const vortox = world.findAt("Vortox", phase);
    const vortoxed = vortox !== null && state.aliveSet(phase).has(vortox);
    // Judged at the moment it acted. A Snake Charmer swap is dated at
    // the night, so at `phase` the charmer no longer holds the character
    // — and its own row was charged as invented, putting a world where
    // the swap really happened at 0.4 against 1.0 for one where it could
    // not.
    const acted = info.night > 1 ? `E${info.night - 1}` : "N0";  // the deal, as Python's `_before`
    let held;
    // Held then, or taken by a Philosopher then. See solver.py.
    if (seat !== null && world.roleAt(seat, phase) !== role
        && hasAbility(world, state, seat, role, acted)) {
      held = abilityState(world, seat, role, acted, gained, vortoxed);
    } else {
      held = seat === null ? ABSENT
                           : abilityState(world, seat, role, phase,
                                          gained, vortoxed);
    }
    // A row told to somebody other than the holder. A Drunk holding the
    // token has no ability, so nobody else is woken for it. See solver.py.
    const witnessed = !!info.witnessed;
    if (witnessed && held === ARBITRARY) held = ABSENT;
    if (held === ABSENT) {
      invented *= inventionCost(info);    // no such source in this world
      outcome[idx] = INVENTED;
      return;
    }
    if (held === ARBITRARY) { outcome[idx] = MADE_UP; return; }
    if (seat !== info.player && world.evilAt(info.player, phase)) {
      invented *= inventionCost(info);    // an evil messenger is none
      outcome[idx] = INVENTED;
      return;
    }
    // A Vortox falsifies information, not choices.
    // One question, asked in one place: does a Vortox reach this row?
    if (held === INVERTED && !info.isInformation(state)) {
      outcome[idx] = HELD;
      return;
    }

    if (held === INVERTED && info.type === "FortuneTeller") {
      // Whether it came out false depends on the red herring: chosen
      // with the herring in the pair the true answer is yes, and a
      // Vortox makes it no. Read without a herring that no looked true
      // (07.10.2026). Settled with the herring, below.
      ftInfos.push([info, seat, idx, vortox]);
      return;
    }

    if (held === INVERTED) {
      // It had to come out false. A reading that is *true* means the
      // Vortox itself was not working that night, which the plan can pay
      // for like any other droisoning.
      //
      // A false one is left alone rather than charged for — an
      // approximation worth naming: on a night mixing true and false
      // readings this takes the Vortox as droisoned and does not
      // additionally charge the false ones. Permissive, which keeps
      // worlds that happened rather than ruling them out.
      // Truth, not legality. Misregistration lets a Storyteller give
      // false information *legally* — a Spy shown as the Slayer is still
      // a Spy, so that reading is already false and a Vortox may produce
      // it freely. `holds` answers "could this have been said", which is
      // right nearly everywhere and wrong here.
      const wasTrue = info.isTrue
        ? info.isTrue(world, state, seat)
        : info.holds(world, state, null, seat);
      if (wasTrue) {
        // Then the Vortox was not working, and nothing else will do:
        // "even if they are drunk or poisoned, it must be false". For
        // three days this also accepted the seat itself being droisoned
        // (corrected 02.10.2026). The Mathematician keeps both ways out:
        // its number is checked against a range rather than a value.
        if (info.type === "MathematicianInfo") {
          const got = vortoxOr[info.night] =
            vortoxOr[info.night] || {vortox, sources: new Set()};
          got.sources.add(seat);
        } else fail(info.night, vortox);
        outcome[idx] = EXCUSED;
      } else outcome[idx] = HELD;
      return;
    }

    if (info.type === "FortuneTeller") {
      // Whether it held depends on where the red herring was, which is
      // settled later. Left open until then.
      ftInfos.push([info, seat, idx, null]);
    } else if (witnessed && !info.holds(world, state, null, seat)) {
      // Nothing excuses it: a droisoned source tells the other player
      // nothing at all, so the words did not come from the game.
      invented *= inventionCost(info);
      outcome[idx] = INVENTED;
    } else if (!info.holds(world, state, null, seat)) {
      // Poison has to land on whoever the information came from —
      // poisoning the messenger changes nothing.
      fail(info.night, seat);
      outcome[idx] = EXCUSED;
    } else {
      outcome[idx] = HELD;
      // **A droisoned character cannot misregister.** Registration is a
      // plain ability and a plain ability simply does not function, so a
      // row that held only by somebody misregistering forbids that seat
      // from having been droisoned that night.
      for (const who of (info.leanedOn ? info.leanedOn(world, state, seat) : []))
        (working[info.night] || (working[info.night] = new Set())).add(who);
    }
  });
  if (impossible) return null;            // a hard fact did not hold

  return {failures, ftInfos, invented, mustWork: working, vortoxOr};
}

// --------------------------------------------------------------------
// Putting a price on it
// --------------------------------------------------------------------

/** How every night of this game could have gone.
 *
 * A night that killed nobody is explained here rather than separately,
 * because "the Demon was stopped" and "the Demon killed somebody" are the
 * same question asked of the same cause.
 */
/** A memo on this deal, good for this state in this epoch only. */
function memoFor(base, name, state) {
  let memo = base[name];
  if (!memo || memo.state !== state || memo.epoch !== state._epoch) {
    memo = {state, epoch: state._epoch, got: new Map()};
    Object.defineProperty(base, name, {value: memo, writable: true,
                                       configurable: true});
  }
  return memo;
}

/** `explainNight`, kept per deal and per what had happened by then: a
 * night's deaths read only the changes up to it, so the stories of one
 * world share their early nights. See solver.py `_explained_night`. */
function explainedNight(world, state, night, died) {
  const base = world instanceof Timeline ? world.world : world;
  const here = phaseIndex(`N${night}`);
  const upto = (world.changes || []).filter(c => momentOf(c) <= here);
  const memo = memoFor(base, "_nightsMemo", state);
  const key = `${night}#${upto.map(changeKey).join(";")}`;
  let got = memo.got.get(key);
  if (got === undefined) {
    got = theOnesThatCanWin(explainNight(world, state, night, died()));
    memo.got.set(key, got);
  }
  return got;
}

/** A night's explanations, without those another one makes pointless.
 *
 * One that asks for everything another asks *and more*, and is no
 * cheaper, can never be the one that wins: any plan that grants it grants
 * the other, at a price at least as good. Dropping it loses nothing, and
 * the nights multiply — fewer ways per night is the only saving that is
 * not a guess (03.10.2026). See solver.py `_the_ones_that_can_win`. */
function theOnesThatCanWin(options) {
  const subset = (a, b) => { for (const x of a) if (!b.has(x)) return false;
                             return true; };
  const within = (a, b) => Object.entries(a || {}).every(
    ([night, seats]) => subset(seats, (b || {})[night] || new Set()));
  const kept = [];
  options.forEach((mine, i) => {
    let beaten = false;
    for (let j = 0; j < options.length && !beaten; j++) {
      const other = options[j];
      if (i === j || other.cost < mine.cost ||
          !subset(other.impaired, mine.impaired) ||
          !subset(other.working, mine.working) ||
          !within(other.earlier, mine.earlier)) continue;
      // Asking exactly the same at the same price: the first stays.
      const same = other.cost === mine.cost &&
        other.impaired.size === mine.impaired.size &&
        other.working.size === mine.working.size &&
        within(mine.earlier, other.earlier);
      if (same && j > i) continue;
      beaten = true;
    }
    if (!beaten) kept.push(mine);
  });
  return kept;
}

/** A night's explanations, without those the rest of the board refuses.
 *
 * The board asks before any night is explained: a reading that came out
 * false had an impaired source, and whoever walked away from an execution
 * was working. An explanation that needs one of those seats the other way
 * round is dead whatever else happens, but is not found out until the
 * plan is tried — after the cap has made its cut. Dropping them first
 * loses nothing. See _the_ones_the_board_allows in solver.py. */
function theOnesTheBoardAllows(night, options, impairedAlready, workingAlready) {
  const hits = (seats, other) => {
    if (!other) return false;
    for (const s of seats) if (other.has(s)) return true;
    return false;
  };
  const clash = (when, impaired, working) =>
    hits(impaired, workingAlready[when]) || hits(working, impairedAlready[when]);
  return options.filter(opt =>
    !clash(night, opt.impaired, opt.working) &&
    !Object.entries(opt.earlier || {})
      .some(([when, seats]) => clash(when, seats, [])));
}

const NOBODY = new Set();
const seatList = seats => [...seats].sort((a, b) => a - b).join(",");
const entryFor = (night, impaired, working) =>
  `${night}:${seatList(impaired)}/${seatList(working)};`;

export const ACCOUNTS_KEPT = 400;

/** How every night of this game could have gone.
 *
 * One account per set of demands, the cheapest excuses first. What an
 * account asks of the impairment plan is who had to be impaired and who
 * had to be working, night by night. Two that ask the same differ only
 * in what they cost, and the dearer can never win — so only the best of
 * each is kept, which loses nothing.
 *
 * Then a cap, because the nights multiply. It used to be the first
 * twenty-four as they came, unsorted and with every duplicate still in:
 * by the fourth night of a Bad Moon Rising game the account that really
 * happened was past the cut, and the world was thrown out with nothing
 * wrong with it (03.10.2026).
 *
 * Built without copying: the sets are shared and never changed, an
 * account's key grows by one night's entry, and an account that another
 * already beats is never built. Only those that put a demand on an
 * earlier night — a Pukka's — are made the long way (04.10.2026). See
 * _night_accounts in solver.py.
 */
function nightAccounts(world, state, impairedAlready = {}, workingAlready = {}) {
  const deaths = nightDeaths(state);
  const nights = new Set([...Object.keys(deaths).map(Number),
                          ...state.quietNights]);
  if (!nights.size) return [{cost: 1.0, impaired: {}, working: {}}];

  let accounts = [{cost: 1.0, impaired: {}, working: {}, key: ""}];
  const done = [];
  for (const night of [...nights].sort((a, b) => a - b)) {
    const options = [];
    for (const opt of theOnesTheBoardAllows(
        night, explainedNight(world, state, night,
                              () => new Set(deaths[night] || [])),
        impairedAlready, workingAlready)) {
      let clash = false;
      for (const s of opt.impaired) if (opt.working.has(s)) clash = true;
      if (clash) continue;              // asked to be both at once
      // A kill that started on an earlier night puts its demand back
      // where it belongs.
      const early = Object.entries(opt.earlier || {})
        .filter(([, seats]) => seats.size)
        .sort((a, b) => Number(a[0]) - Number(b[0]));
      options.push({opt, early,
                    entry: entryFor(night, opt.impaired, opt.working)});
    }
    if (!options.length) return [];
    done.push(night);
    const best = new Map();
    for (const acc of accounts) {
      for (const {opt, early, entry} of options) {
        const cost = acc.cost * opt.cost;
        let impaired = null, key;
        if (!early.length) {
          key = acc.key + entry;
        } else {
          impaired = {...acc.impaired};
          impaired[night] = opt.impaired;
          let clash = false;
          for (const [when, seats] of early) {
            const merged = new Set(impaired[when] || NOBODY);
            for (const s of seats) merged.add(s);
            impaired[when] = merged;
            const work = acc.working[when];
            if (work) for (const s of merged) if (work.has(s)) clash = true;
          }
          if (clash) continue;          // impaired and working at once
          const all = new Set([...done, ...Object.keys(impaired).map(Number)]);
          key = [...all].sort((a, b) => a - b)
            .map(n => entryFor(n, impaired[n] || NOBODY,
                               n === night ? opt.working
                                           : (acc.working[n] || NOBODY)))
            .join("");
        }
        const had = best.get(key);
        if (had !== undefined && cost <= had.cost) continue;
        if (impaired === null) {
          impaired = {...acc.impaired};
          impaired[night] = opt.impaired;
        }
        const working = {...acc.working};
        working[night] = opt.working;
        best.set(key, {cost, impaired, working, key});
      }
    }
    accounts = [...best.values()].sort((a, b) => b.cost - a.cost)
                                 .slice(0, ACCOUNTS_KEPT);
    if (!accounts.length) return [];
  }
  return accounts;
}

/** Who had to be impaired each night, and what that cost.
 *
 * `failures` is who must have been impaired — a reading that came out
 * false, an ability that did not fire. `forbidden` is who must not have
 * been: a Monk that is the only explanation for a quiet night was
 * working, so nothing can have stopped it.
 */
function impairmentPlan(world, state, failures, forbidden) {
  const got = planAsGiven(world, state, failures, forbidden);
  if (got !== null) return got;
  // A Courtier that was itself drunk or poisoned when it chose made
  // nobody drunk at all. Its drunkenness is unavoidable while it stands,
  // so a world that needs the named character *working* fails above — and
  // then the other story is tried: the Courtier impaired on the night it
  // chose, and its three days never happening.
  //
  // The same goes for a Philosopher: one that was drunk or poisoned when
  // it chose gained nothing and drunk nobody.
  for (const info of state.infos) {
    const source = info.sourceRole;
    if ((source !== "Courtier" && source !== "Philosopher") || !info.role)
      continue;
    const phase = `N${info.night}`;
    const began = info.night > 1 ? `E${info.night - 1}` : "N0";
    const holder = info.player;
    if (world.roleAt(holder, began) !== source &&
        world.roleAt(holder, phase) !== source) continue;
    const again = {};
    for (const [night, seats] of Object.entries(failures))
      again[night] = new Set(seats);
    (again[info.night] = again[info.night] || new Set()).add(holder);
    const other = planAsGiven(world, state, again, forbidden, [source]);
    if (other !== null) return other;
  }
  return null;
}

function planAsGiven(world, state, failures, forbidden, without = null) {
  let total = 1.0;
  let previous = {};
  const nights = new Set([...Object.keys(failures), ...Object.keys(forbidden)]
    .map(Number));
  for (const night of [...nights].sort((a, b) => a - b)) {
    const wanted = failures[night] || new Set();
    const blocked = forbidden[night] || new Set();
    for (const s of wanted) if (blocked.has(s)) return null;
    let sources = sourcesOn(world, state, night);
    if (without) sources = sources.filter(src => !without.includes(src.name));
    const got = planNight(sources,
                          [...wanted].sort((a, b) => a - b),
                          [...blocked].sort((a, b) => a - b), previous);
    if (got === null) return null;
    total *= got.cost;
    previous = {...previous, ...got.hits};
  }
  return total;
}

/** Every moment the game was going on with two or fewer on the board as
 * alive: the start of each night and day the board reaches, and the one
 * after the last, which is now — unless the board says the game is over.
 * Almost always none, and worked out once a board. */
function momentsWithTwoLeft(state) {
  if (state._twoLeft) return state._twoLeft;
  const final = phaseIndex(state.finalPhase());
  const out = [];
  for (let night = 1, beyond = false; !beyond; night++) {
    for (const phase of [`N${night}`, `D${night}`]) {
      if (phaseIndex(phase) > final) {
        beyond = true;
        if (state.gameOver) break;
      }
      if (state.aliveSet(phase).size <= 2) out.push(phase);
      if (beyond) break;
    }
  }
  return (state._twoLeft = out);
}

/** Evil wins with two players alive, so while the game goes on there are
 * three. With a Zombuul on the script, two on the board and no winner
 * means somebody crossed off is alive: a Zombuul that died once. Any
 * other Demon still standing has won, and the world goes. Only with a
 * Zombuul on the script (table decision, 04.10.2026). See
 * _the_game_went_on in solver.py. */
function theGameWentOn(world, state) {
  if (!inBag(state, "Zombuul")) return true;
  for (const phase of momentsWithTwoLeft(state)) {
    const board = state.aliveSet(phase);
    const demon = world.demonAt(phase);
    if (demon === null) continue;
    if (board.has(demon)) return false;   // it would have won there and then
    if (world.roleAt(demon, phase) === "Zombuul" && board.size < 2 &&
        state.diedAt(demon)
          .filter(p => phaseIndex(p) < phaseIndex(phase)).length < 2)
      return false;                       // it and one other: won as well
  }
  return true;
}

/** The cost of one telling of this world, with the lineage settled. */
function explainOne(world, state, outcome = null) {
  if (!theGameWentOn(world, state)) return null;
  const sorted = plainFailures(world, state, outcome || {});
  if (sorted === null) return null;
  const {failures, ftInfos, invented, mustWork, vortoxOr} = sorted;

  // Every way the nights could have gone. Each brings its own demands on
  // who was impaired and who was working, so the plan is solved once per
  // account and the cheapest wins.
  const accounts = nightAccounts(world, state, failures, mustWork || {});
  if (!accounts.length) return null;

  const settle = readings => {
    let best = null;
    for (const acc of accounts) {
      // Dearest last, and a plan never improves an account: once the
      // best this one could reach is no more than what is in hand,
      // nothing after it can win. See settle in solver.py.
      if (best !== null && acc.cost * invented <= best) break;
      const wanted = {};
      for (const [n, seats] of Object.entries(readings))
        wanted[n] = new Set(seats);
      for (const [n, seats] of Object.entries(acc.impaired)) {
        wanted[n] = wanted[n] || new Set();
        for (const s of seats) wanted[n].add(s);
      }
      // Whoever walked away from an execution had to be working across
      // that span — the same span as the night before it, so it lands in
      // the plan alongside everything else.
      const needed = {};
      for (const [n, seats] of Object.entries(acc.working))
        needed[n] = new Set(seats);
      for (const [day, seats] of Object.entries(mustWork || {})) {
        needed[day] = needed[day] || new Set();
        for (const s of seats) needed[day].add(s);
      }
      const planned = impairmentPlan(world, state, wanted, needed);
      if (planned === null) continue;
      const got = planned * acc.cost * invented;
      if (best === null || got > best) best = got;
    }
    return best;
  };

  // `settle`, trying each way a true reading under a Vortox can be
  // excused: per night, the Vortox off or every source droisoned.
  const nights = Object.keys(vortoxOr || {}).map(Number).sort((a, b) => a - b);
  const settleEither = readings => {
    if (!nights.length) return settle(readings);
    const k = Math.min(nights.length, 6);
    let best = null;
    for (let mask = 0; mask < (1 << k); mask++) {
      const trial = {};
      for (const [n, seats] of Object.entries(readings))
        trial[n] = new Set(seats);
      nights.forEach((night, i) => {
        // Bit clear means the Vortox was off, which is the first choice
        // tried, as in Python's `product((True, False))`.
        const off = i >= k || !((mask >> (k - 1 - i)) & 1);
        const {vortox, sources} = vortoxOr[night];
        trial[night] = trial[night] || new Set();
        if (off) trial[night].add(vortox);
        else for (const s of sources) trial[night].add(s);
      });
      const got = settle(trial);
      if (got !== null && (best === null || got > best)) best = got;
    }
    return best;
  };

  const ceiling = settleEither(failures);
  if (ceiling === null) return null;
  if (!ftInfos.length) return ceiling;

  // The herring only matters when it sits in one of the pairs the Fortune
  // Teller asked about, so those are the only seats worth trying — plus
  // one uninvolved seat to stand for "somewhere else".
  const asked = new Set();
  for (const [info] of ftInfos) { asked.add(info.a); asked.add(info.b); }
  const herrings = [...asked].filter(p => !isEvil(world.roles[p]));
  for (let p = 0; p < state.nPlayers; p++)
    if (!asked.has(p) && !isEvil(world.roles[p])) { herrings.push(p); break; }

  let best = null, bestMarks = null;
  for (const rh of herrings) {
    const combined = {};
    for (const [n, seats] of Object.entries(failures))
      combined[n] = new Set(seats);
    const marks = {};
    for (const [info, source, idx, vortox] of ftInfos) {
      let fits, src = source;
      // Under a Vortox the other way about: an answer that was true
      // means the Vortox was not working. True, not legal — a yes on a
      // Recluse is false.
      if (vortox !== null) { fits = !info.isTrueWith(world, rh); src = vortox; }
      else fits = info.holds(world, state, rh, source);
      if (fits) marks[idx] = HELD;
      else {
        combined[info.night] = combined[info.night] || new Set();
        combined[info.night].add(src);
        marks[idx] = EXCUSED;
      }
    }
    const cost = settleEither(combined);
    if (cost === null) continue;
    if (best === null || cost > best) { best = cost; bestMarks = marks; }
    if (best >= ceiling) break;           // cannot do better than this
  }
  if (outcome && bestMarks) Object.assign(outcome, bestMarks);
  return best;
}

/** What became of each recorded reading in this world. */
export function rowOutcomes(world, state) {
  const outcome = {};
  explainOne(world, state, outcome);
  return outcome;
}

/** The cheapest account of this world: {cost, changes}.
 *
 * The changes come back as well as the cost because the report needs
 * them — after a handover, "who is the Demon" has a different answer than
 * the deal gives.
 */
export function bestStory(world, state, outcome = null) {
  // A new epoch for the memos (sources, nights, Barber offers): they save
  // work between one world's stories, and kept past that a constant or a
  // rule changed between two solves would be answered from before it.
  state._epoch = (state._epoch || 0) + 1;
  const stories = possibleTimelines(world, state);
  if (!stories.length) return {cost: null, changes: [], viable: []};
  if (stories.length === 1 && !stories[0][0].length) {
    const cost = explainOne(world, state, outcome);
    return {cost, changes: [], viable: cost === null ? [] : [[cost, []]]};
  }

  let best = null, bestChanges = [], bestMarks = null;
  const viable = [];
  for (const [changes, weight] of stories) {
    const view = changes.length ? new Timeline(world, changes) : world;
    const marks = outcome ? {} : null;
    const cost = explainOne(view, state, marks);
    if (cost === null) continue;
    const got = cost * weight;
    viable.push([got, changes]);
    if (best === null || got > best) {
      best = got; bestChanges = changes; bestMarks = marks;
    }
  }
  if (outcome && bestMarks) Object.assign(outcome, bestMarks);
  return {cost: best, changes: bestChanges, viable};
}

/** Each fitting story as [view, share of the world's weight]. A world
 * weighs what its best story costs; the credit inside it is split across
 * its stories by what each costs, so an Ogre that may have turned evil
 * and a starpass with several heirs are counted as the odds say rather
 * than all-or-nothing. See solver.py. */
export function storyShares(world, viable, state = null) {
  // A Barber swap gets the share the table gives it, not its price.
  if (state && viable.length > 1 && inBag(state, "Barber") &&
      barberClaimants(state).size)
    viable = viable.map(([cost, changes]) =>
      [cost * barberShare(world, changes, state), changes]);
  const total = viable.reduce((sum, [cost]) => sum + cost, 0);
  if (total <= 0) return [];
  return viable.map(([cost, changes]) =>
    [changes.length ? new Timeline(world, changes) : world, cost / total]);
}

/** How much of a world's credit a story gets for its Barber swap: the
 * swap's price taken back out and the table's share put in — "no swap"
 * 1 − BARBER_SWAP_SHARE, Demon–Minion pairs BARBER_DEMON_MINION_SHARE of
 * the rest between them, every other pair what is left. See solver.py. */
function barberShare(world, changes, state) {
  const swaps = changes.filter(c => c.barber);
  const rest = changes.filter(c => !c.barber);
  const view = rest.length ? new Timeline(world, rest) : world;
  const counts = new Map();
  for (const [extra] of barberRule(view, state)) {
    if (!extra.length) continue;
    const got = counts.get(extra[0].phase) || [0, 0];
    got[extra[0].barber === "ours" ? 0 : 1] += 1;
    counts.set(extra[0].phase, got);
  }
  let factor = 1.0;
  for (const [night, [nOurs, nOther]] of counts) {
    const mine = swaps.filter(c => c.phase === night);
    if (!mine.length) { factor *= 1.0 - PRIORS.BARBER_SWAP_SHARE; continue; }
    const ours = mine[0].barber === "ours";
    const part = nOurs && nOther
      ? (ours ? PRIORS.BARBER_DEMON_MINION_SHARE
              : 1.0 - PRIORS.BARBER_DEMON_MINION_SHARE)
      : 1.0;
    factor *= PRIORS.BARBER_SWAP_SHARE * part / (ours ? nOurs : nOther) /
              (ours ? 1.0 : BARBER_SWAP_PENALTY);
  }
  return factor;
}

/** How much explaining this world needs, as a multiplier, or null. */
export const explanationCost = (world, state) => bestStory(world, state).cost;

export const worldConsistent = (world, state) =>
  explanationCost(world, state) !== null;
