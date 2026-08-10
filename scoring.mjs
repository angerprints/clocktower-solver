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
import {planNight, sourcesOn} from "./impairment.mjs";
import {PRIORS} from "./priors.mjs";
import {phaseIndex} from "./phases.mjs";
import {ABSENT, ARBITRARY, TEAM, abilityState, isEvil} from "./roles.mjs";
import {Timeline, change} from "./worlds.mjs";
import {inBag, survivalsOf} from "./characters.rules.mjs";

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
export const transitionRule = fn => (TRANSITION_RULES.push(fn), fn);

export const HEIR_RULES = [];
export const heirRule = fn => (HEIR_RULES.push(fn), fn);

/** Every account of who was what, and when.
 *
 * Rules compose: each is offered the changes agreed so far and may add
 * its own. An empty result from any rule means nothing can explain this
 * world, which is how a Demon dead in daylight with nobody to inherit
 * gets ruled out.
 */
export function possibleTimelines(world, state, cap = 48) {
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

/** The Imp kills itself and a Minion takes over. */
heirRule(function aMinionCatchesTheStar(view, state, phase, character) {
  if (phase[0].toUpperCase() !== "N") return [];
  return starpassHeirs(view, state, phase)
    .map(seat => change(phase, seat, character));
});

/** The Demon killed in daylight, with her standing by. */
heirRule(function theScarletWomanStepsUp(view, state, phase, character) {
  if (phase[0].toUpperCase() === "N") return [];
  if (!scarletWomanTakesOver(view, state, phase)) return [];
  return [change(phase, view.findAt("ScarletWoman", phase), character)];
});

/** Could play have carried on with no Demon at all?
 *
 * Only with a Mastermind alive when the Demon went, only after a daylight
 * death, and only for one more day — so if the board runs on past that,
 * this is not what happened.
 */
function mastermindDay(world, state, phase) {
  if (!inBag(state, "Mastermind")) return false;
  const seat = world.findAt("Mastermind", phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return false;
  const day = parseInt(phase.slice(1), 10);
  return phaseIndex(state.finalPhase()) <= phaseIndex(`D${day + 1}`);
}

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

  const walk = (view, holder, soFar) => {
    if (found.length >= cap) return;
    // The first time they went down. A Demon raised afterwards is
    // somebody else's problem to model; the star passed when it fell.
    const phases = state.diedAt(holder);
    const phase = phases.length ? phases[0] : null;
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
    if (phase[0].toUpperCase() !== "N" && mastermindDay(view, state, phase))
      found.push(soFar);

    // No offers at all, and no Mastermind, means good won right there.
    for (const move of moves) {
      if (move.seat === null) continue;
      const grown = [...soFar, move];
      walk(new Timeline(world, grown), move.seat, grown);
    }
  };

  walk(world, start, []);
  return found;
}

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
  const fail = (night, seat) =>
    ((failures[night] = failures[night] || new Set()).add(seat));

  // Executing the Saint ends the game on the spot — while it is
  // *working*. A poisoned or drunk Saint is executed and the game carries
  // on, so an execution that killed somebody does not rule the Saint out;
  // it says something had to have stopped them.
  for (const day of Object.keys(state.executions || {}).map(Number)) {
    const seat = state.executionDeath(day);
    if (seat === null) continue;
    if (world.roleAt(seat, `D${day}`) === "Saint") fail(day, seat);
    // A Sailor cannot die, and that holds in daylight — so a working one
    // walks away from its own execution.
    if (world.roleAt(seat, `D${day}`) === "Sailor") fail(day, seat);
  }

  // Somebody standing again needs a reason, and the reason has to have
  // been working. A Professor only raises a Townsfolk, which is not the
  // same as raising somebody good: the Spy registers as one.
  let raisings = 0;
  for (const [seatKey, phases] of Object.entries(state.resurrections || {})) {
    const seat = Number(seatKey);
    for (const phase of phases) {
      raisings += 1;
      const night = parseInt(phase.slice(1), 10);
      if (!Number.isFinite(night)) continue;
      const prof = world.findAt("Professor", phase);
      if (prof === null || !inBag(state, "Professor")) return null;
      if (!state.aliveSet(phase).has(prof) || night < 2) return null;
      const raised = world.roleAt(seat, phase);
      if (TEAM[raised] !== "townsfolk" &&
          !CHARACTERS[raised].registers.includes("townsfolk")) return null;
      (working[night] = working[night] || new Set()).add(prof);
    }
  }
  if (raisings > 1) return null;          // once per game

  // An execution that killed nobody needs a reason, and the reason has to
  // have been working.
  for (const [dayKey, seat] of Object.entries(state.executions || {})) {
    const day = Number(dayKey);
    if (state.executionDeath(day) !== null) continue;
    const survivors = survivalsOf(world, state, day, seat);
    if (!survivors.length) return null;   // nothing here survives one
    working[day] = new Set(survivors);
  }

  const spent = spentNominations(state);
  const seats = sourceSeats(state);
  state.infos.forEach((info, idx) => {
    if (spent.has(idx)) { outcome[idx] = SPENT; return; }
    if (info.hard()) {
      if (!info.holds(world, state, null)) { invented = null; }
      else outcome[idx] = HELD;
      return;
    }
    const role = info.sourceRole;
    const phase = `N${info.night}`;
    let seat = seats[idx];
    if (seat === null) {
      seat = world.findAt(role, phase);
      if (seat === null) {
        const at = world.believes.indexOf(role);
        seat = at === -1 ? null : at;
      }
    }
    const held = seat === null ? ABSENT
                               : abilityState(world, seat, role, phase);
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
    if (info.type === "FortuneTeller") {
      // Whether it held depends on where the red herring was, which is
      // settled later. Left open until then.
      ftInfos.push([info, seat, idx]);
    } else if (!info.holds(world, state, null, seat)) {
      // Poison has to land on whoever the information came from —
      // poisoning the messenger changes nothing.
      fail(info.night, seat);
      outcome[idx] = EXCUSED;
    } else outcome[idx] = HELD;
  });
  if (invented === null) return null;     // a hard fact did not hold

  return {failures, ftInfos, invented, mustWork: working};
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
function nightAccounts(world, state) {
  const deaths = nightDeaths(state);
  const nights = new Set([...Object.keys(deaths).map(Number),
                          ...state.quietNights]);
  if (!nights.size) return [{cost: 1.0, impaired: {}, working: {}}];

  let accounts = [{cost: 1.0, impaired: {}, working: {}}];
  for (const night of [...nights].sort((a, b) => a - b)) {
    const died = new Set(deaths[night] || []);
    const options = explainNight(world, state, night, died);
    if (!options.length) return [];
    const grown = [];
    for (const acc of accounts) {
      for (const opt of options) {
        let clash = false;
        for (const s of opt.impaired) if (opt.working.has(s)) clash = true;
        if (clash) continue;              // asked to be both at once
        const merged = {};
        for (const [n, v] of Object.entries(acc.impaired)) merged[n] = new Set(v);
        merged[night] = new Set(opt.impaired);
        // A kill that started on an earlier night puts its demand back
        // where it belongs.
        for (const [when, seats] of Object.entries(opt.earlier || {})) {
          merged[when] = merged[when] || new Set();
          for (const s of seats) merged[when].add(s);
        }
        const work = {};
        for (const [n, v] of Object.entries(acc.working)) work[n] = new Set(v);
        work[night] = new Set(opt.working);
        grown.push({cost: acc.cost * opt.cost, impaired: merged,
                    working: work});
      }
    }
    accounts = grown.slice(0, 24);
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
  let total = 1.0;
  let previous = {};
  const nights = new Set([...Object.keys(failures), ...Object.keys(forbidden)]
    .map(Number));
  for (const night of [...nights].sort((a, b) => a - b)) {
    const wanted = failures[night] || new Set();
    const blocked = forbidden[night] || new Set();
    for (const s of wanted) if (blocked.has(s)) return null;
    const got = planNight(sourcesOn(world, state, night),
                          [...wanted].sort((a, b) => a - b),
                          [...blocked].sort((a, b) => a - b), previous);
    if (got === null) return null;
    total *= got.cost;
    previous = {...previous, ...got.hits};
  }
  return total;
}

/** The cost of one telling of this world, with the lineage settled. */
function explainOne(world, state, outcome = null) {
  const sorted = plainFailures(world, state, outcome || {});
  if (sorted === null) return null;
  const {failures, ftInfos, invented, mustWork} = sorted;

  // Every way the nights could have gone. Each brings its own demands on
  // who was impaired and who was working, so the plan is solved once per
  // account and the cheapest wins.
  const accounts = nightAccounts(world, state);
  if (!accounts.length) return null;

  const settle = readings => {
    let best = null;
    for (const acc of accounts) {
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

  const ceiling = settle(failures);
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
    for (const [info, src, idx] of ftInfos) {
      if (info.holds(world, state, rh, src)) marks[idx] = HELD;
      else {
        combined[info.night] = combined[info.night] || new Set();
        combined[info.night].add(src);
        marks[idx] = EXCUSED;
      }
    }
    const cost = settle(combined);
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
  const stories = possibleTimelines(world, state);
  if (!stories.length) return {cost: null, changes: []};
  if (stories.length === 1 && !stories[0][0].length)
    return {cost: explainOne(world, state, outcome), changes: []};

  let best = null, bestChanges = [], bestMarks = null;
  for (const [changes, weight] of stories) {
    const view = changes.length ? new Timeline(world, changes) : world;
    const marks = outcome ? {} : null;
    const cost = explainOne(view, state, marks);
    if (cost === null) continue;
    const got = cost * weight;
    if (best === null || got > best) {
      best = got; bestChanges = changes; bestMarks = marks;
    }
  }
  if (outcome && bestMarks) Object.assign(outcome, bestMarks);
  return {cost: best, changes: bestChanges};
}

/** How much explaining this world needs, as a multiplier, or null. */
export const explanationCost = (world, state) => bestStory(world, state).cost;

export const worldConsistent = (world, state) =>
  explanationCost(world, state) !== null;
