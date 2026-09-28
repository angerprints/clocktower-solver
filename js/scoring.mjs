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
import {ABSENT, ARBITRARY, INVERTED, TEAM, abilityState, isEvil}
  from "./roles.mjs";
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
transitionRule(function aBarberLetsTheDemonSwapTwo(world, state) {
  if (!inBag(state, "Barber")) return [[[], 1.0]];
  const barber = world.find("Barber");
  if (barber === null) return [[[], 1.0]];

  const stories = [[[], 1.0]];
  for (const phase of state.diedAt(barber)) {
    const day = parseInt(phase.slice(1), 10);
    const night = "NDEX".indexOf(phase[0].toUpperCase()) > 0
      ? `N${day + 1}` : `N${day}`;
    if (phaseIndex(night) > phaseIndex(state.finalPhase())) continue;
    for (let first = 0; first < state.nPlayers; first++)
      for (let second = first + 1; second < state.nPlayers; second++) {
        const a = world.roleAt(first, night), b = world.roleAt(second, night);
        if (a === b) continue;
        stories.push([[change(night, first, b), change(night, second, a)],
                      BARBER_SWAP_PENALTY]);
      }
  }
  return stories;
});

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
  if (view.demonAt(phase) !== view.demonAt("N1")) return [];
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
    const phases = state.diedAt(holder);
    const phase = phases.length ? phases[0] : null;
    if (phase !== null) {
      const held = view.roleAt(holder, phase);
      if (held && TEAM[held] !== "demon") { found.push(soFar); return; }
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
    if (phase[0].toUpperCase() !== "N" && mastermindDay(view, state, phase))
      found.push(soFar);

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
    const side = world.evilAt(info.target, phase) ? "evil" : "good";
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

transitionRule(function aSnakeCharmerTakesTheStar(world, state) {
  const swaps = state.infos.filter(
    i => i.sourceRole === "SnakeCharmer" && i.swapped);
  if (!swaps.length) return [[[], 1.0]];

  let stories = [[[], 1.0]];
  for (const info of swaps) {
    // Who *acted*, which is the board as it stood when the night began —
    // not after the swap this rule is about to write. The swap is dated
    // at the night now that it is immediate.
    const phase = `N${info.night}`;
    const began = info.night > 1 ? `E${info.night - 1}` : phase;
    const charmer = world.findAt("SnakeCharmer", began);
    const demon = world.demonAt(began);
    if (charmer === null || demon === null || charmer === demon) continue;
    if (info.target !== demon) continue;   // they pointed at somebody else
    const after = `D${info.night}`;
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
    if (witch === null || !state.aliveSet(`N${day}`).has(witch)) return null;
    (working[day] = working[day] || new Set()).add(witch);
  }
  for (const [day, ] of Object.entries(state.madnessExecutions || {})) {
    const who = world.findAt("Cerenovus", `N${day}`);
    if (who === null || !state.aliveSet(`N${day}`).has(who)) return null;
    (working[day] = working[day] || new Set()).add(who);
  }

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
      // Who acted, not who holds the character now — a swap dated at
      // this night would otherwise find the seat it ended up at.
      const began = info.night > 1 ? `E${info.night - 1}` : phase;
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
    const acted = info.night > 1 ? `E${info.night - 1}` : phase;
    let held;
    if (seat !== null && world.roleAt(seat, phase) !== role
        && world.roleAt(seat, acted) === role) {
      held = abilityState(world, seat, role, acted, gained, vortoxed);
    } else {
      held = seat === null ? ABSENT
                           : abilityState(world, seat, role, phase,
                                          gained, vortoxed);
    }
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
        fail(info.night, vortox);
        outcome[idx] = EXCUSED;
      } else outcome[idx] = HELD;
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
