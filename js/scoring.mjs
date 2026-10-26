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

import {CHARACTERS, slotOf} from "./catalogue.mjs";
import {explainNight} from "./deaths.mjs";
import {RESTING, minionStillActs, planNightResting, silencedOut, sourcesOn}
  from "./impairment.mjs";
import {PRIORS} from "./priors.mjs";
import {LISTENING, beginReads, differOnlyUnasked, endReads, listenForSides,
        phaseIndex, replayReads} from "./phases.mjs";
import {ABSENT, ARBITRARY, GENUINE, INVERTED, TEAM, abilityState, isEvil}
  from "./roles.mjs";
import {SETUP_SLOT, readingAt} from "./worlds.mjs";
import {BABYSAT_READS, SUMMON_READS, TEA_READS, Timeline, babysits, change,
        handedOn,
        changeAt, dealtRoles, lilMonstaWorld, notSummoned, summoned,
        summonerWorld, teaParty, turnedEvil, engineered, boffinGift}
  from "./worlds.mjs";
import {aLeviathanIsToldOf, demonHolding, summonedBeside, fauxPaw, inBag, leviathanAt, lleechHost, onBoard,
        pixieGain, survivalsOf, teaLadyFailedAtTheGallows}
  from "./characters.rules.mjs";
import {actsAsCultLeader, alHadikhiaChosen, besideAlive, cultSides, eachRealSide, fallsAs,
        fauxPawLycanthrope,
        holdingNow,
        knowsItTurnedEvil, sideOpen,
        livingNeighbours, takenByAPhilosopher, tookIt, wentOnAfter,
        babysitterAt, engineerChosen, boffinGiven, BOFFIN_NEVER_GIVES,
        BOFFIN_UNSEEN, boffinGiftOf, boffinHolders, boffinSeat, soberSeat}
  from "./info.mjs";

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
  aBountyHunterBringsAnEvilTownsfolk: 0, // the setup
  // Ahead of the Snake Charmer, which on night two points at night one's
  // babysitter (21.10.2026).
  theMinionsChooseABabysitter: 5,
  aSnakeCharmerTakesTheStar: 11,
  aPitHagMakesSomebodyElse: 16,
  // The Engineer (26.10.2026): after the Sailor, before the Preacher, the
  // Poisoner, the Snake Charmer and every Demon. See solver.py.
  anEngineerRebuildsTheEvil: 8,
  // After the Scarlet Woman, before the Lunatic, the Exorcist and every
  // Demon (21.10.2026).
  theSummonerSummons: 19,
  // And one a Minion became at a tea party (Hatter stage 2): the same
  // turn.
  aHattedSummonerSummons: 19,
  // At the very start of the night after the Hatter died by day (C).
  aHattersTeaParty: 1,
  // After a death at night, straight after it (C; Hatter stage 3c):
  // after the Summoner, before the Barber. See solver.py.
  aHattersTeaPartyAtNight: 30,
  aBarberLetsTheDemonSwapTwo: 40,
  aHuntsmanFindsTheDamsel: 45,
  aFarmerHandsItOn: 48,
  anOgrePicksASide: 60,                  // late on night one
  demonHandovers: 99,                    // a death, so after everything
  // The Boffin gives the Demon an ability at the setup — first, so every
  // rule after it sees it — and again to every new Demon, last
  // (26.10.2026). See solver.py.
  aBoffinGivesTheDemon: -1,
  aBoffinGivesANewDemon: 100,
};

export const transitionRule = fn => (
  TRANSITION_RULES.push(fn),
  TRANSITION_RULES.sort((a, b) =>
    (ACTS_AT[a.name] ?? 50) - (ACTS_AT[b.name] ?? 50)),
  fn);

export const HEIR_RULES = [];
export const heirRule = fn => (HEIR_RULES.push(fn), fn);

// Whose turn each rule is (Hatter stage 3b, 23.10.2026): the rule reads
// every night at that character's slot, and every change it makes on a
// night is stamped with it. See `_TURN_OF` in solver.py.
const TURN_OF = {
  aSnakeCharmerTakesTheStar: "SnakeCharmer",
  aPitHagMakesSomebodyElse: "PitHag",
  aPitHagNobodyWroteDown: "PitHag",
  theSummonerSummons: "Summoner",
  aHattedSummonerSummons: "Summoner",
  aBarberLetsTheDemonSwapTwo: "Barber",
  aHuntsmanFindsTheDamsel: "Huntsman",
  anEngineerRebuildsTheEvil: "Engineer",
  aFarmerHandsItOn: "Farmer",
  theMinionsChooseABabysitter: "LilMonsta",
  aBountyHunterBringsAnEvilTownsfolk: "Philosopher",
};

// One stamped copy per change: a rule's memo hands back the same change
// objects, and the night passes key changes by object.
const STAMPED = new WeakMap();

/** These changes, each made at this character's turn of its night —
 * unless it already says where it happened. See solver.py `stamped`. */
export function stamped(changes, key) {
  if (!key) return changes;
  let any = false;
  const out = changes.map(c => {
    if ((c.slot !== null && c.slot !== undefined) || c.phase[0] !== "N")
      return c;
    let got = STAMPED.get(c);
    if (got === undefined) {
      const slot = slotOf(key, parseInt(c.phase.slice(1), 10));
      // Every property kept, the hidden ones too: a Barber's swap says
      // which kind it is in one that is not enumerable (`barberOffers`),
      // and a spread copy lost it — the shares of a world's Barber stories
      // then came out unlike Python's (test_mixed_scripts).
      if (slot === null) got = c;
      else {
        got = Object.create(Object.getPrototypeOf(c),
                            Object.getOwnPropertyDescriptors(c));
        got.slot = slot;
      }
      STAMPED.set(c, got);
    }
    if (got !== c) any = true;
    return got;
  });
  return any ? out : changes;
}

/** Run `fn` with the board read at this row's turn (`rowTurn`). */
function atRowTurn(info, fn) {
  const got = rowTurn(info);
  return got ? readingAt(got.phase, got.first, got.other, fn) : fn();
}

/** A row's turn: {phase, first, other}, or null for the whole night. See
 * worlds.py `_row_slot`. */
export function rowTurn(info) {
  const role = info.constructor.sourceRole ?? info.sourceRole;
  const c = role ? CHARACTERS[role] : null;
  if (!c || !Number.isInteger(info.night)) return null;
  const first = c.first_night || 0, other = c.other_night || 0;
  if (!(info.night === 1 ? first : other)) return null;
  return {phase: `N${info.night}`, first, other};
}

/** Run `fn` reading the board at this character's turn of that night. */
function turnOf(key, night, fn) {
  return readingAt(`N${night}`, slotOf(key, 1) || 0, slotOf(key, night) || 0,
                   fn);
}

/** What a rule offers, asked at its turn and stamped with it. */
function offersOf(rule, view, state) {
  const key = TURN_OF[rule.name];
  if (!key) return rule(view, state);
  return readingAt(null, slotOf(key, 1) || 0, slotOf(key, 2) || 0,
    () => [...rule(view, state)].map(([extra, cost]) =>
      [stamped(extra, key), cost]));
}

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
  // One story for each Townsfolk a Bounty Hunter may have brought in
  // evil, beside everything else: room for all of them (11.10.2026).
  const dealt = dealtRoles(world);
  let hunted = 1;
  if (inBag(state, "BountyHunter") && dealt.includes("BountyHunter")) {
    hunted = Math.max(1, dealt.filter(r => TEAM[r] === "townsfolk").length);
    cap *= hunted;
  }
  // Room for every babysitter story Lil' Monsta offers (21.10.2026).
  if (inBag(state, "LilMonsta") && lilMonstaWorld(world))
    cap = Math.max(cap, LIL_MONSTA_STORIES);
  // And for every way a tea party went (22.10.2026), once for each
  // Townsfolk a Bounty Hunter may have turned. See solver.py.
  if (hatterOnBoard(state)) {
    // Once more for each slot a party at night may stand at. See solver.py.
    let slots = 1;
    const died = hatterDeaths(world, state);
    for (const [s, p] of died)
      if (p[0].toUpperCase() === "N")
        slots = Math.max(slots, teaSlots(state, parseInt(p.slice(1), 10), s).length);
    cap = Math.max(cap, HATTER_STORIES * hunted * slots * Math.max(1, died.length));
    // And for every way a Summoner chosen at a party before its third
    // night may have summoned (Hatter stage 2). See solver.py.
    if (state.script.keys.includes("Summoner") && died.length === 1
        && teaNight(died[0][1]) <= 3)
      cap *= 1 + summonable(state).length * state.nPlayers;
  }
  // And for every way the Engineer's choice went (26.10.2026), and a
  // Summoner it chose summoning beside the Demon. See solver.py.
  if (engineerOnBoard(state)) {
    cap = Math.max(cap, cap * (1 + Math.floor(ENGINEER_STORIES / 8)));
    if (state.script.keys.includes("Summoner"))
      cap *= 1 + summonable(state).length * state.nPlayers;
  }
  // And for every ability the Boffin may have given, at the setup and to a
  // new Demon (26.10.2026). See solver.py.
  if (boffinOnBoard(state)) {
    const seen = state.script.keys.filter(k => BOFFIN_SEEN.has(k)).length;
    cap *= 2 * (2 + seen);
  }
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
  let swapped = false, lastSwap = 0;
  for (const info of state.infos) {
    const source = info.sourceRole;
    if (source === "PitHag" && info.role) made.add(info.role);
    else if (source === "SnakeCharmer" && info.swapped) {
      swapped = true;
      lastSwap = Math.max(lastSwap, info.night);
    }
  }
  const deaths = [...state.deathPhases()].filter(([, p]) => p);
  const phases = deaths.map(([, p]) => p);
  const atNight = phases.some(p => p[0].toUpperCase() === "N");
  // A Barber counts only once a seat that claimed it has died.
  const claimed = barberClaimants(state);
  const barberDied = deaths.some(([s]) => claimed.has(Number(s)));
  const roles = new Set([...world.roles, ...made]);
  // And whatever a Philosopher took (13.10.2026). See solver.py.
  for (const [taken] of Object.values(state.philosophies() || {}))
    roles.add(taken);
  let count = (swapped ? 1 : 0) + (made.size ? 1 : 0);
  // The Demon handed on before a Snake Charmer chose it (Stelle 60,
  // 15.10.2026). See solver.py.
  if (swapped) {
    const dealt = new Set();
    world.roles.forEach((r, seat) => { if (TEAM[r] === "demon") dealt.add(seat); });
    const until = phaseIndex(`N${lastSwap}`);
    if (deaths.some(([s, p]) => dealt.has(Number(s)) && phaseIndex(p) < until))
      count++;
  }
  // A Huntsman that chose, and may have found the Damsel (10.10.2026).
  if (roles.has("Huntsman")
      && state.infos.some(i => i.type === "HuntsmanChoice")) count++;
  // The Summoner's Demon, once the board reaches it (21.10.2026).
  if (summonerWorld(world) && inBag(state, "Summoner")
      && phaseIndex(state.finalPhase()) >= phaseIndex("N2")) count++;
  // A claimed Hatter dead by day: night by night, always (22.10.2026).
  if (hatterOnBoard(state)) {
    const hatters = hatterClaimants(state);
    if (deaths.some(([s]) => hatters.has(Number(s)))) count += 2;
  }
  // The Engineer's choice: night by night, always (26.10.2026).
  if (engineerOnBoard(state)) count += 2;
  // A Boffin dealt: a new Demon's ability is given last, and a rule that
  // acts on a later night has to see it (26.10.2026).
  if (boffinOnBoard(state) && world.roles.includes("Boffin")) count += 1;
  for (const [key, needs] of [["Barber", barberDied], ["Farmer", atNight],
                              ["FangGu", atNight], ["Ogre", true]])
    if (needs && roles.has(key)
        && (key === "Barber" ? barberOnBoard(state) : onBoard(state, key)))
      count++;
  return count;
}

/** Every rule once, over the whole game, in night-slot order. */
function allNightsAtOnce(world, state, cap) {
  let stories = [[[], 1.0]];
  for (const rule of TRANSITION_RULES) {
    const grown = [];
    // What the rule offered a story that differs from this one only in
    // who turned evil, if it never asked which side they were on: a
    // Bounty Hunter's seven stories are then asked once, not seven times
    // (`explainOrRecall` has the reasoning).
    const askedBefore = new Map();
    outer:
    for (const [changes, weight] of stories) {
      if (!LISTENING) {                   // nobody turns evil that way here
        const view = changes.length ? new Timeline(world, changes) : world;
        for (const [extra, cost] of offersOf(rule, view, state)) {
          grown.push([[...changes, ...extra], weight * cost]);
          if (grown.length >= cap) break outer;
        }
        continue;
      }
      const {flips, restKey} = whoTurned(changes);
      let before = askedBefore.get(restKey);
      if (!before) askedBefore.set(restKey, before = []);
      let offers = null;
      for (const [theirs, reads, kept] of before)
        if (differOnlyUnasked(flips, theirs, reads)) { offers = kept; break; }
      if (offers === null) {
        const view = changes.length ? new Timeline(world, changes) : world;
        beginReads();
        let reads;
        try { offers = [...offersOf(rule, view, state)]; } finally { reads = endReads(); }
        before.push([flips, reads, offers]);
      }
      for (const [extra, cost] of offers) {
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

/** A story taken apart: which seat is evil from which moment (a Map),
 * the nights a Mezepheles turned somebody (as a key), and a key for
 * every other change. See `_who_turned` in solver.py. */
const NOBODY_TURNED = {flips: new Map(), turns: "", restKey: ""};
function whoTurned(changes) {
  if (!changes.length) return NOBODY_TURNED;
  const flips = new Map();
  let turns = "", restKey = "";
  for (const c of changes) {
    if (c.turned) {
      const at = momentOf(c);
      const had = flips.get(c.seat);
      flips.set(c.seat, had === undefined ? at : Math.min(at, had));
      if (c.turned === "mezepheles") turns += c.phase + ";";
    } else restKey += changeKey(c) + (c.barber ? "b" + c.barber : "") + ";";
  }
  return {flips, turns, restKey};
}
// Worked out once per change: the night passes ask for the same keys and
// moments of the same few changes hundreds of times per world.
const KEYS = new WeakMap(), MOMENTS = new WeakMap();
// With the slot (Hatter stage 3b): two changes alike but for where in the
// night they happened are two changes, as Python's tuples are.
// A Boffin's mark carries its ability apart from the side (26.10.2026),
// as Python keeps it in the side field: two marks that give different
// abilities are two stories.
const sameChange = (a, b) => a === b || (a.phase === b.phase &&
  a.seat === b.seat && (a.role ?? null) === (b.role ?? null) &&
  (a.side ?? null) === (b.side ?? null) &&
  (a.slot ?? null) === (b.slot ?? null) &&
  (a.boffin ? a.gift : undefined) === (b.boffin ? b.gift : undefined));
const changeKey = c => {
  let k = KEYS.get(c);
  if (k === undefined)
    KEYS.set(c, k = `${c.phase}|${c.seat}|${c.role}|${c.side}|${c.slot ?? null}`
                    + (c.boffin ? `|gift:${c.gift}` : ""));
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
    case "aBountyHunterBringsAnEvilTownsfolk":
      return new Set([1, ...rows("Philosopher", "role")]);
    case "aHuntsmanFindsTheDamsel":
      return new Set(state.infos.filter(i => i.type === "HuntsmanChoice")
        .map(i => i.night));
    case "demonHandovers": return new Set(deaths.map(([k]) => k));
    case "anEngineerRebuildsTheEvil":
      return new Set(engineerRows(state).map(i => i.night));
    case "theSummonerSummons":
    case "aHattedSummonerSummons": return new Set([1, 2, 3]);
    case "aHattersTeaParty": {
      const hatters = hatterClaimants(state);
      const out = new Set();
      for (const [seat, phases] of Object.entries(state.deaths || {}))
        if (hatters.has(Number(seat)))
          for (const p of phases)
            if (p[0].toUpperCase() !== "N") out.add(parseInt(p.slice(1), 10) + 1);
      return out;
    }
    case "aHattersTeaPartyAtNight": {
      const hatters = hatterClaimants(state);
      const out = new Set();
      for (const [seat, phases] of Object.entries(state.deaths || {}))
        if (hatters.has(Number(seat)))
          for (const p of phases)
            if (p[0].toUpperCase() === "N") out.add(parseInt(p.slice(1), 10));
      return out;
    }
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
        for (const [extra, cost] of offersOf(rule, view, state)) {
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
  if (!barberOnBoard(state)) return [[[], 1.0]];
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
  // A Philosopher that wrote down taking the Barber (13.10.2026).
  for (const [who, [taken]] of Object.entries(state.philosophies() || {}))
    if (taken === "Barber") out.add(Number(who));
  return out;
}

/** A Barber on the script, or a Philosopher that took one (13.10.2026). */
function barberOnBoard(state) {
  return inBag(state, "Barber") || takenByAPhilosopher(state, "Barber");
}

function barberOffers(world, state) {
  // Whoever was the Barber when they died, dealt or made — and claimed
  // it. See solver.py.
  const claimed = barberClaimants(state);
  const deaths = [];
  for (let seat = 0; seat < state.nPlayers; seat++)
    if (claimed.has(seat)) for (const phase of state.diedAt(seat))
      if (fallsAs(world, state, seat, "Barber", phase)) deaths.push(phase);
  if (!deaths.length) return [[[], 1.0]];

  const stories = [[[], 1.0]];
  for (const phase of deaths) {
    const day = parseInt(phase.slice(1), 10);
    const night = "NDEX".indexOf(phase[0].toUpperCase()) > 0
      ? `N${day + 1}` : `N${day}`;
    if (phaseIndex(night) > phaseIndex(state.finalPhase())) continue;
    const demons = world.demonsAt(night);
    for (let first = 0; first < state.nPlayers; first++)
      for (let second = first + 1; second < state.nPlayers; second++) {
        const a = world.roleAt(first, night), b = world.roleAt(second, night);
        if (a === b) continue;
        // Sides written out: a swap moves characters, never sides.
        const sideA = world.evilAt(first, night) ? "evil" : "good";
        const sideB = world.evilAt(second, night) ? "evil" : "good";
        // The Demon with one of its own Minions costs a world nothing;
        // any other pair is priced as a deliberate play (table habit).
        const ours = (demons.includes(first) && TEAM[b] === "minion") ||
                     (demons.includes(second) && TEAM[a] === "minion");
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

/** The Demon died, with her standing by: in daylight, or at night when it
 * was not the Imp's own starpass, which hands her the star first. A
 * Lleech going with its host was the first to show it (11.10.2026). */
heirRule(function theScarletWomanStepsUp(view, state, phase, character) {
  if (phase[0].toUpperCase() === "N" && STARPASSES.has(character)) return [];
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
  // Hanged itself, babysitting Lil' Monsta: it has no day to buy.
  if (seat === holder) return false;
  return phaseIndex(state.finalPhase()) <= phaseIndex(`D${day + 1}`);
}

/** The mark a Mastermind's extra day leaves in a story: a change that
 * changes nothing, on the executed Demon. Nothing else writes one. */
export const mastermindMarker = (phase, seat) => change(phase, seat, null, null);
export const isMastermindMarker = c =>
  (c.role === null || c.role === undefined) &&
  (c.side === null || c.side === undefined) && !c.babysits && !c.fell
  && !c.notSummoned && !c.handedOn && !c.boffin;

/** Every way the Demon could have changed hands in this world.
 *
 * The timing is not a free choice — it is pinned by the deaths already on
 * the record. A Demon dead at night killed itself, and the star has to
 * land on a living Minion. A Demon killed in daylight ends the game
 * outright unless the Scarlet Woman was standing by.
 *
 * Empty means no story fits, and the world is impossible.
 */
/** "If Lil' Monsta dies with 5 or more players alive, the Scarlet Woman
 * babysits Lil' Monsta for the rest of the game", from the moment after,
 * and she has to see it through. See solver.py. */
function theScarletWomanBabysits(world, state) {
  const fell = (world.changes || []).filter(c => c.fell);
  if (!fell.length) return [[]];
  const at = fell[0].phase, seat = fell[0].seat;
  const scarlet = world.findAt("ScarletWoman", at);
  if (scarlet === null || scarlet === seat
      || !scarletWomanTakesOver(world, state, at)) return [];
  const index = phaseIndex(at) + 1;
  const after = `${index % 2 ? "D" : "N"}${Math.floor(index / 2) + 1}`;
  const final = phaseIndex(state.finalPhase());
  if (state.diedAt(scarlet).some(gone => phaseIndex(gone) >= index
      && !(state.gameOver && phaseIndex(gone) >= final))) return [];
  return [[{...babysits(after, scarlet), slot: SETUP_SLOT}]];
}

export function demonLineages(world, state, cap = 24) {
  // Lil' Monsta's babysitters are the Minions' choice; what a
  // babysitter's death leads to is settled where they are chosen.
  if (inBag(state, "LilMonsta") && lilMonstaWorld(world))
    return theScarletWomanBabysits(world, state);
  let start = world.demonAt("N1");
  // The Summoner's Demon starts its line where it was made (21.10.2026).
  let since = null;
  if (start === null) {
    const made = summonedChange(world);
    if (!made) return [[]];
    start = made.seat;
    since = phaseIndex(made.phase);
  }

  // A second living Demon a Summoner made (Hatter stage 2, 25.10.2026):
  // each line walked on its own, the second on top of the first. See
  // solver.py.
  const beside = summonedBeside(world);
  if (!beside)
    return demonLine(world, state, world, start, since, 0, null, cap)
      .map(([line]) => line);
  const out = [];
  for (const [first, ends] of demonLine(world, state, world, start, since,
                                        0, beside, cap)) {
    const view = first.length ? new Timeline(world, first) : world;
    for (const [second, more] of demonLine(world, state, view, beside.seat,
                                           phaseIndex(beside.phase), 1,
                                           beside, cap)) {
      const story = [...first, ...second];
      if (aDemonLeft(story.length ? new Timeline(world, story) : world,
                     state, [...ends, ...more]))
        out.push(story);
      if (out.length >= cap) return out;
    }
  }
  return out;
}

/** Would a Scarlet Woman stepping up for this Demon make two living
 * Demons, with a Fang Gu or an Al-Hadikhia in play? See solver.py. */
function scarletWomanStays(view, state, phase, fallen) {
  const here = phaseIndex(phase);
  let jinxed = false;
  for (let p = 0; p < state.nPlayers; p++)
    if (["FangGu", "AlHadikhia"].includes(view.roleAt(p, phase))) jinxed = true;
  if (!jinxed) return false;
  return view.demonsAt(phase).some(d => d !== fallen
    && !state.diedAt(d).some(p => phaseIndex(p) <= here));
}

/** Every Demon that fell with nobody to take over, while the game went
 * on, left another standing (Hatter stage 2). See solver.py. */
function aDemonLeft(view, state, ends) {
  for (const [holder, phase] of ends) {
    const here = phaseIndex(phase);
    if (!view.demonsAt(phase).some(d => d !== holder
        && !state.diedAt(d).some(p => phaseIndex(p) <= here)))
      return false;
  }
  return true;
}

/** One Demon's line: [changes, ends] for each way. See solver.py. */
function demonLine(world, state, base, start, since, line, beside, cap) {
  const found = [];

  const walk = (view, holder, soFar, after = -1, held = new Set(),
                ends = []) => {
    if (found.length >= cap) return;
    const first = holder === start && since !== null && !soFar.length;
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
    // Made a Zombuul while dead, it "has already died once" (their jinx).
    let spent = false;
    if (first) {
      spent = phases.some(p => phaseIndex(p) < since);
      phases = phases.filter(p => phaseIndex(p) >= since);
    }
    if (phases.length && !spent && view.roleAt(holder, phases[0]) === "Zombuul")
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
        // Where a tea party took the Demon's character, the star went to
        // the Minion that swapped then. See solver.py.
        const gave = (view.changes || []).find(c => c.tea
          && c.seat === holder && TEAM[c.role] !== "demon"
          && phaseIndex(c.phase) > after
          && phaseIndex(c.phase) <= phaseIndex(check));
        const now = view.demonsAt(gave ? gave.phase : check);
        const successor = now.length > line ? now[line] : null;
        if (successor !== null && successor !== holder && !held.has(successor)) {
          walk(view, successor, soFar, after, new Set([...held, holder]), ends);
          return;
        }
        found.push([soFar, ends]);
        return;
      }
    }
    // A handover cannot happen *earlier* than the one before it, and no
    // seat can hold the star twice. Both were true by construction until
    // a Barber let the Demon swap characters around, and the walk went
    // round for ever. The same phase is fine: a Shabaloth kills twice, so
    // the Demon and its heir can fall together.
    if (phase !== null && (phaseIndex(phase) < after || held.has(holder))) {
      found.push([soFar, ends]);
      return;
    }
    if (phase === null) {
      found.push([soFar, ends]);          // they held it to the end
      return;
    }
    const character = view.roleAt(holder, phase);
    let moves = [];
    // At the turn of the Demon that fell (Hatter stage 3b). See solver.py.
    for (const rule of HEIR_RULES)
      moves.push(...stamped(rule(view, state, phase, character), character));
    // The Scarlet Woman stays herself where two Demons would live, with a
    // Fang Gu or an Al-Hadikhia in play (their jinxes; Hatter stage 2).
    // See solver.py.
    if (beside && scarletWomanStays(view, state, phase, holder))
      moves = moves.filter(m => m.seat === null
                           || view.roleAt(m.seat, phase) !== "ScarletWoman");

    // A Mastermind buys one more day after the Demon is executed. Nobody
    // inherits — there simply is no Demon after this — so the lineage
    // ends here rather than continuing.
    if (mastermindDay(view, state, phase, holder))
      found.push([[...soFar, mastermindMarker(phase, holder)], ends]);

    // No offers at all, and no Mastermind, means good won right there —
    // a story when the board says the game is over and this was its last
    // moment (10.10.2026). See solver.py.
    if (state.gameOver
        && phaseIndex(phase) >= phaseIndex(state.finalPhase()))
      found.push([soFar, ends]);
    // Beside a second Demon made by then the line may simply end — not
    // where the Scarlet Woman steps up (D Weg 1). See solver.py.
    else if (beside && phaseIndex(beside.phase) <= phaseIndex(phase)
             && !moves.some(m => m.seat !== null
                            && view.roleAt(m.seat, phase) === "ScarletWoman"))
      found.push([soFar, [...ends, [holder, phase]]]);
    for (const move of moves) {
      if (move.seat === null) continue;
      const mark = beside ? [handedOn(move.phase, holder, move.slot ?? null)]
        : [];
      const grown = [...soFar, ...mark, move];
      walk(new Timeline(base, grown), move.seat, grown,
           phaseIndex(phase), new Set([...held, holder]), ends);
    }
  };

  walk(base, start, [], since === null ? -1 : since);
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
    const before = info.night > 1 ? `B${info.night - 1}` : "N0";  // the deal, as Python's `_before`
    const side = world.evilAt(info.target, before) ? "evil" : "good";
    return change(phase, info.target, info.role, side);
  });
  return [[changes, 1.0]];
});

/** A seat said it became something, on a night a Pit-Hag could have made
 * it so, and no Pit-Hag row names it: that may have been the Pit-Hag,
 * whose choice evil does not say. Free. From the second night, with the
 * Pit-Hag alive, and only for a character nobody held as the night began
 * (Stelle 58, C, 14.10.2026). See solver.py. */
transitionRule(function aPitHagNobodyWroteDown(world, state) {
  if (!inBag(state, "PitHag")) return [[[], 1.0]];
  const recorded = new Set(state.infos
    .filter(i => i.sourceRole === "PitHag" && i.role)
    .map(i => `${i.night}|${i.target}`));
  let stories = [[[], 1.0]];
  for (const info of state.infos) {
    if (info.type !== "Became" || info.night < 2 || !CHARACTERS[info.role]
        || recorded.has(`${info.night}|${info.player}`)) continue;
    const phase = `N${info.night}`;
    const before = `B${info.night - 1}`;
    const hag = world.findAt("PitHag", phase);
    if (hag === null || !state.aliveSet(phase).has(hag)) continue;
    let held = false;
    for (let p = 0; p < state.nPlayers; p++)
      if (world.roleAt(p, before) === info.role) held = true;
    if (held) continue;
    const side = world.evilAt(info.player, before) ? "evil" : "good";
    const made = change(phase, info.player, info.role, side);
    stories = [...stories, ...stories.map(([c, w]) => [[...c, made], w])]
      .slice(0, 48);
  }
  return stories;
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
/** A Damsel the Huntsman chose becomes a Townsfolk not in play: the one
 * she said she became, or any. Or she stayed, and then the Huntsman was
 * not working, which its row asks for (10.10.2026). See solver.py. */
transitionRule(function aHuntsmanFindsTheDamsel(world, state) {
  if (!onBoard(state, "Huntsman")) return [[[], 1.0]];
  for (const info of state.infos) {
    if (info.type !== "HuntsmanChoice") continue;
    const night = info.night, phase = `N${night}`;
    if (!hasAbility(world, state, info.player, "Huntsman", phase)) continue;
    const mine = state.infos.indexOf(info);
    if (state.infos.some((o, idx) => idx < mine && o.type === "HuntsmanChoice"
        && o.player === info.player && o.night <= night)) continue;
    const began = night > 1 ? `B${night - 1}` : "N0";
    const target = info.target;
    // Or a Philosopher that took her (group 6, P, 14.10.2026).
    if (world.roleAt(target, began) !== "Damsel"
        && !tookIt(world, state, target, "Damsel", began)) continue;
    const said = state.infos.filter(b => b.type === "Became"
      && b.player === target && b.night >= night
      && state.script.townsfolk.includes(b.role)).map(b => b.role);
    const inPlay = new Set();
    for (let p = 0; p < state.nPlayers; p++) inPlay.add(world.roleAt(p, began));
    const options = said.length ? said.slice(0, 1)
      : state.script.townsfolk.filter(k => !inPlay.has(k));
    const side = world.evilAt(target, began) ? "evil" : "good";
    const out = [[[], 1.0]];
    for (const role of options.slice(0, 16))
      out.push([[change(phase, target, role, side)], 1.0]);
    return out;
  }
  return [[[], 1.0]];
});

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
  if (!onBoard(state, "Farmer")) return [[[], 1.0]];
  let stories = [[[], 1.0]];
  const latest = phaseIndex(state.finalPhase());
  for (let night = 1; phaseIndex(`N${night}`) <= latest; night++) {
    const phase = `N${night}`;
    const grown = [];
    for (const [changes, cost] of stories) {
      const view = changes.length ? new Timeline(world, changes) : world;
      const holders = [];
      for (let p = 0; p < state.nPlayers; p++)
        // And a Philosopher that took it (13.10.2026).
        if ((view.roleAt(p, phase) === "Farmer"
             || tookIt(view, state, p, "Farmer", phase)) &&
            state.diedAt(p).includes(phase)) holders.push(p);
      if (!holders.length) {
        grown.push([changes, cost]);
        // Its jinx with the Leviathan: a chosen Farmer uses its ability
        // and does not die (11.10.2026). Anchored to a seat saying it
        // became the Farmer that night. See solver.py.
        if (night >= 2 && inBag(state, "Leviathan")
            && leviathanAt(view, state, phase) !== null) {
          const alive = state.aliveSet(phase);
          const living = [...alive].filter(p =>
            view.roleAt(p, phase) === "Farmer" && !view.evilAt(p, phase));
          for (const info of state.infos) {
            if (info.type !== "Became" || info.role !== "Farmer"
                || info.night !== night || !living.length) continue;
            const heir = info.player;
            if (living.includes(heir) || !alive.has(heir)
                || !couldBeGood(view, heir, phase)) continue;
            grown.push([[...changes, change(`D${night}`, heir, "Farmer", null)],
                        cost]);
          }
        }
        continue;
      }
      const seat = holders[0];
      // Whoever said they became the Farmer that night first, so the cap
      // below keeps them (Stelle 58, 14.10.2026).
      const told = new Set(state.infos
        .filter(i => i.type === "Became" && i.role === "Farmer"
                && i.night === night).map(i => i.player));
      const heirs = [...state.aliveSet(phase)]
        .filter(p => p !== seat && couldBeGood(view, p, phase))
        .sort((a, b) => (told.has(a) ? 0 : 1) - (told.has(b) ? 0 : 1)
                        || a - b);
      grown.push([changes, cost]);
      // An heir killed the same night hands it on at once (Stelle 58, D).
      const handOn = (made, gone) => {
        for (const heir of heirs) {
          if (gone.has(heir)) continue;
          const more = [...made, change(`D${night}`, heir, "Farmer", null)];
          grown.push([more, cost]);
          if (state.diedAt(heir).includes(phase))
            handOn(more, new Set([...gone, heir]));
        }
      };
      handOn(changes, new Set([seat]));
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
  if (!onBoard(state, "Ogre")) return [[[], 1.0]];
  // The holder, and a Philosopher that took it (ruling G, 13.10.2026).
  const ogres = [world.findAt("Ogre", "N1")];
  for (const who of Object.keys(state.philosophies() || {}).map(Number)
         .sort((a, b) => a - b))
    if (tookIt(world, state, who, "Ogre", "N1")) ogres.push(who);
  let stories = [[[], 1.0]];
  for (const ogre of ogres) {
    if (ogre === null || ogre === undefined) continue;
    const mine = anOgresSide(world, state, ogre);
    const grown = [];
    for (const [changes, cost] of stories)
      for (const [more, price] of mine)
        grown.push([[...changes, ...more], cost * price]);
    stories = grown;
  }
  return stories;
});

function anOgresSide(world, state, ogre) {
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
}

/** "[1 Townsfolk is evil]": with a Bounty Hunter dealt, one Townsfolk is
 * evil from the setup, and it may be the Bounty Hunter itself (table
 * ruling, 11.10.2026). One story for each Townsfolk it could be, at no
 * cost. A Philosopher that takes the ability might turn one (their
 * jinx), so there both stories are told. See solver.py. */
transitionRule(function aBountyHunterBringsAnEvilTownsfolk(world, state) {
  if (!inBag(state, "BountyHunter")) return [[[], 1.0]];
  const town = [];
  const dealt = dealtRoles(world);
  dealt.forEach((role, p) => {
    if (TEAM[role] === "townsfolk") town.push(p);
  });
  if (dealt.includes("BountyHunter"))
    return town.map(p => [[turnedEvil("N0", p, "bountyhunter")], 1.0]);
  const stories = [[[], 1.0]];
  for (const info of state.infos) {
    if (info.sourceRole !== "Philosopher" || info.role !== "BountyHunter"
        || world.roles[info.player] !== "Philosopher") continue;
    const phase = `N${info.night}`;
    for (const p of town)
      if (!world.evilAt(p, phase))
        stories.push([[turnedEvil(phase, p, "bountyhunter")], 1.0]);
    break;
  }
  return stories;
});

// The fields of a row that name seats, by name: the same list in
// solver.py, so both sides tell the same stories.
const SEAT_FIELDS = ["a", "b", "c", "target", "guess", "shown", "second",
                     "nominator", "pointed"];
const SEAT_SETS = ["joined", "demons", "minions"];
const asSeat = value => {
  if (value === null || value === undefined || value === ""
      || typeof value === "boolean") return null;
  const got = Number(value);
  return Number.isInteger(got) ? got : null;
};

/** Seats whose side something on the board asks about from the second
 * night on. A Mezepheles may turn anybody, and only these stories change
 * anything the board can see. See solver.py. */
function seatsTheBoardLooksAt(world, state) {
  const n = state.nPlayers;
  if (!state._lookedAtCache) {
    const seats = new Set(), unclaimed = new Set();
    const add = value => {
      const got = asSeat(value);
      if (got !== null) seats.add(got);
    };
    const sources = sourceSeats(state);
    state.infos.forEach((info, idx) => {
      if (info.night < 2) return;
      seats.add(info.player);
      const role = info.sourceRole;
      const src = sources[idx];
      if (src !== null && src !== undefined) seats.add(src);
      else if (role) unclaimed.add(role);
      for (const name of SEAT_FIELDS) add(info[name]);
      for (const name of SEAT_SETS)
        for (const value of info[name] || []) add(value);
      for (const guess of info.guesses || [])
        add(Array.isArray(guess) ? guess[0] : guess.player);
      const kind = info.type;
      if (kind === "Empath" && src !== null && src !== undefined)
        for (const p of livingNeighbours(state, info.night, src)) seats.add(p);
      else if (kind === "Empath" || kind === "Chef" || kind === "SavantInfo")
        for (let p = 0; p < n; p++) seats.add(p);
      else if (kind === "OracleInfo") {
        const phase = `N${info.night}`;
        for (let p = 0; p < n; p++)
          if (!state.aliveSet(phase).has(p)
              || state.diedAt(p).includes(phase)) seats.add(p);
      }
    });
    for (const [seat] of state.deathPhases()) seats.add(seat);
    for (const seat of Object.values(state.executions || {})) seats.add(seat);
    state._lookedAtCache = [
      new Set([...seats].filter(p => p >= 0 && p < n)), unclaimed];
  }
  const [seats, unclaimed] = state._lookedAtCache;
  const out = new Set(seats);
  for (const role of unclaimed) {
    const holder = world.find(role);
    if (holder !== null && holder !== undefined) out.add(holder);
  }
  if (inBag(state, "CultLeader") && world.roles.includes("CultLeader")) {
    const leader = world.find("CultLeader");
    const last = parseInt(state.finalPhase().slice(1), 10);
    for (let day = 1; day <= last; day++)
      for (const p of besideAlive(state, leader, `D${day}`)) out.add(p);
    out.add(leader);
  }
  return out;
}

/** Could something later that night have reached a Mezepheles that had
 * already done its turning? A Pukka's poison, a Sweetheart dying in the
 * night. See solver.py. */
function actedBeforeTheDemonOnly(world, state, night) {
  const phase = `N${night}`;
  if (demonHolding(world, phase, "Pukka") !== null) return true;
  for (let p = 0; p < state.nPlayers; p++)
    if (state.diedAt(p).includes(phase)
        && fallsAs(world, state, p, "Sweetheart", phase)) return true;
  return false;
}

/** "The 1st good player to say this word becomes evil that night." One
 * good player on one night from the second, the Mezepheles holding its
 * character when that night began and still standing. Free, and told
 * only where a story needs it (`bestStory`). Returns the turns that
 * could be laid over this view, each a list of changes. See solver.py. */
export function aMezephelesMayHaveTurned(world, state) {
  const stories = [];
  if (!inBag(state, "Mezepheles")) return stories;
  const last = parseInt(state.finalPhase().slice(1), 10);
  let seats = null;
  for (let night = 2; night <= last; night++) {
    const phase = `N${night}`;
    const mez = world.findAt("Mezepheles", `B${night - 1}`);
    if (mez === null || mez === undefined
        || !minionStillActs(world, state, mez, phase)) continue;
    if (seats === null)
      seats = [...seatsTheBoardLooksAt(world, state)].sort((a, b) => a - b);
    for (const seat of seats) {
      if (seat === mez || world.evilAt(seat, phase)) continue;
      if (sideOpen(world, state, seat, phase)
          && !actsAsCultLeader(world, state, seat, phase)) continue;
      // At the Mezepheles's turn of that night (Hatter stage 3b).
      stories.push([{...turnedEvil(phase, seat, "mezepheles"),
                     slot: slotOf("Mezepheles", night)}]);
    }
  }
  return stories;
}

/** Does this seat have that ability — held, taken by a Philosopher, or
 * given the Demon by the Boffin (26.10.2026)? */
function hasAbility(world, state, seat, role, phase) {
  if (world.roleAt(seat, phase) === role) return true;
  return tookIt(world, state, seat, role, phase);
}

/** Who has this ability — held, gained by a Philosopher, or given the
 * Demon by the Boffin. */
function whoeverWorks(world, state, role, phase) {
  const seat = world.findAt(role, phase);
  if (seat !== null) return seat;
  for (const [who, [taken, since]] of Object.entries(state.philosophies()))
    if (taken === role && world.roleAt(+who, phase) === "Philosopher" &&
        phaseIndex(phase) >= phaseIndex(since)) return +who;
  const given = boffinHolders(world, state, role, phase);
  return given.length ? given[0] : null;
}

// --------------------------------------------------------------------
// Lil' Monsta (21.10.2026). See solver.py: each night the Minions choose
// a babysitter, who "is the Demon"; one babysitter a night, searched only
// where a reading asks (A, B, Weg 1).
// --------------------------------------------------------------------

export const LIL_MONSTA_STORIES = 256;
// Up to this many combinations of babysitters are all told; beyond it a
// night at a time (bestBabysatStory).
export const BABYSITTERS_TOLD_IN_FULL = 64;

/** Each night's babysitters worth trying, in order. See solver.py. */
export function babysitterOptions(world, state) {
  const last = Math.max(1, parseInt(state.finalPhase().slice(1), 10));
  const asked = babysitterAsked(state);
  const out = [];
  for (let night = 1; night <= last; night++)
    out.push(babysittersOn(world, state, night, asked));
  return out;
}

/** {night: [pointed at, ruled out, every seat]}. See solver.py. */
function babysitterAsked(state) {
  const asked = new Map();
  const at = night => {
    if (!asked.has(night)) asked.set(night, [new Set(), new Set(), [false]]);
    return asked.get(night);
  };
  for (const info of state.infos) {
    const k = info.night;
    switch (info.type) {
      case "FortuneTeller":
        [info.a, info.b].forEach(x => at(k)[info.yes ? 0 : 1].add(x)); break;
      case "SageInfo": at(k)[0].add(info.a); at(k)[0].add(info.b); break;
      case "ChoirboyInfo": at(k)[0].add(info.target); break;
      case "KnightInfo": at(k)[1].add(info.a); at(k)[1].add(info.b); break;
      case "ClockmakerInfo": at(k)[2][0] = true; break;
      case "LilMonstaBabysat": at(k)[0].add(info.player); break;
      case "SlayerShot": at(k)[info.died ? 0 : 1].add(info.target); break;
      case "GolemNomination": at(k)[info.died ? 1 : 0].add(info.target); break;
      case "PuzzlemasterGuess": at(k)[0].add(info.shown); break;
      case "SavantInfo":
        for (const says of [info.first_says, info.second_says])
          if (says && says.kind === "demon_among")
            for (const x of says.seats || []) at(k)[0].add(Number(x));
        break;
      case "FlowergirlInfo":
        if (k > 1)
          for (const v of (state.votes || {})[k - 1] || [])
            at(k - 1)[info.voted ? 0 : 1].add(v);
        break;
      case "SnakeCharmerChoice":
        at(k > 1 ? k - 1 : 1)[info.swapped ? 0 : 1].add(info.target); break;
      case "ExorcistChoice":
        // Naming last night's babysitter stops the kill and says nothing
        // else: it may well have.
        if (k > 1) at(k - 1)[0].add(info.target);
        break;
      default: break;
    }
  }
  return asked;
}

/** Seats the board says may have become a Minion: a Snake Charmer that
 * swapped, a Pit-Hag's Minion. */
function madeMinions(state) {
  const out = new Set();
  for (const info of state.infos) {
    if (info.type === "SnakeCharmerChoice" && info.swapped) out.add(info.player);
    else if (info.sourceRole === "PitHag" && info.role
             && TEAM[info.role] === "minion") out.add(info.target);
  }
  return out;
}

/** The seats worth trying as this night's babysitter, best first. */
function babysittersOn(world, state, night, asked) {
  const phase = `N${night}`;
  let alive = [...state.aliveSet(phase)].sort((a, b) => a - b);
  if (!alive.length) return [];
  // Read off the deal, not the story: asked again on later passes, what
  // it settled for an earlier night has to come out the same.
  const dealt = world.roles;
  // The Magician's jinx: the Storyteller picks among the Minions.
  const magician = world.find("Magician");
  if (magician !== null && state.aliveSet(phase).has(magician)
      && onBoard(state, "Magician")) {
    const made = madeMinions(state);
    alive = alive.filter(p => TEAM[dealt[p]] === "minion" || made.has(p));
  }
  // The Marionette's: it starts beside the first babysitter.
  if (night === 1) {
    const marionette = world.find("Marionette");
    if (marionette !== null) {
      const n = state.nPlayers;
      alive = alive.filter(p => p === (marionette + n - 1) % n
                           || p === (marionette + 1) % n);
    }
  }
  const [pointed, ruledOut, every] =
    asked.get(night) || [new Set(), new Set(), [false]];
  if (every[0]) return alive;
  const lo = phaseIndex(phase), hi = phaseIndex(`D${night}`);
  // Dead in the span, or on the gallows that day: tried, but never
  // standing in for the seats nothing asks about.
  const died = new Set(alive.filter(p => state.diedAt(p).some(at => {
    const i = phaseIndex(at);
    return lo <= i && i <= hi;
  }) || state.executedOn(night) === p));
  const out = alive.filter(p => pointed.has(p));
  for (const p of alive) if (died.has(p) && !out.includes(p)) out.push(p);
  const neutral = alive.filter(p => !pointed.has(p) && !ruledOut.has(p)
                               && !died.has(p));
  // First, the one standing for every seat nothing asks about: where it
  // will do, it is the story told (bestBabysatStory).
  if (neutral.length) {
    const minions = neutral.filter(p => TEAM[dealt[p]] === "minion");
    out.unshift((minions.length ? minions : neutral)[0]);
  } else {
    // Nobody nothing asks about: then anybody, the ruled out last.
    for (const p of alive) if (!out.includes(p) && !ruledOut.has(p)) out.push(p);
    for (const p of alive) if (!out.includes(p)) out.push(p);
  }
  return out;
}

/** What becomes of the babysitter chosen on this night, until the
 * Minions choose again. See solver.py. */
function babysitterFalls(world, state, seat, night) {
  const lo = phaseIndex(`N${night}`), hi = phaseIndex(`D${night}`);
  const gone = state.diedAt(seat).filter(at => {
    const i = phaseIndex(at);
    return lo <= i && i <= hi;
  }).sort((a, b) => phaseIndex(a) - phaseIndex(b));
  if (!gone.length) return [["go on", []]];
  const at = gone[0];
  const out = [];
  if (state.gameOver && phaseIndex(at) >= phaseIndex(state.finalPhase()))
    out.push(["over", []]);
  // The Scarlet Woman: who holds her by then is settled once the whole
  // story is in, so the fall is marked and the handovers settle it.
  if (onBoard(state, "ScarletWoman"))
    out.push(["scarlet", [{phase: at, seat, role: null, side: null,
                           fell: true}]]);
  if (mastermindDay(world, state, at, seat))
    out.push(["mastermind", [mastermindMarker(at, seat)]]);
  return out;
}

// --------------------------------------------------------------------
// The Summoner (21.10.2026, claude/beschwoerer-lesarten.md). See
// solver.py for the readings.
// --------------------------------------------------------------------
const NOT_SUMMONED = new Set(["LilMonsta", "Legion", "Riot"]);

const summonable = state => state.script.keys.filter(
  k => TEAM[k] === "demon" && !NOT_SUMMONED.has(k));

const neighboursOf = (n, seat) => [(seat - 1 + n) % n, (seat + 1) % n];

function summonedSeats(world, state, night, demon, puppet = true) {
  const n = state.nPlayers;
  const standing = state.aliveSet(`N${night}`);
  // Back tonight is back after the Summoner's turn. See solver.py.
  const back = new Set(Object.entries(state.resurrections || {})
    .filter(([, at]) => at.includes(`N${night}`)).map(([p]) => Number(p)));
  let seats = [];
  for (let p = 0; p < n; p++)
    if ((standing.has(p) && !back.has(p)) || demon === "Zombuul")
      seats.push(p);
  // The Marionette's jinx: it enters play after the Demon as its
  // neighbour, alive or dead (22.10.2026). See solver.py.
  // Not for a Summoner chosen at a tea party: the Marionette is in play
  // already (Hatter stage 2).
  if (puppet && world.roles.includes("Marionette")) {
    const near = neighboursOf(n, world.roles.indexOf("Marionette"));
    seats = seats.filter(p => near.includes(p));
  }
  return seats;
}

/** With a Summoner the Marionette holds its believed good character for
 * real until the Demon comes (22.10.2026). See solver.py. */
function marionetteEnters(world, state, made) {
  const m = world.roles.indexOf("Marionette");
  if (m < 0) return [[]];
  const token = world.believes[m];
  if (token === null || token === undefined) return [[]];
  // The Lunatic, or the Townsfolk, or the Drunk holding it (22.10.2026).
  // See solver.py.
  const held = [];
  if (TEAM[token] === "demon") held.push("Lunatic");
  else {
    held.push(token);
    if (TEAM[token] === "townsfolk" && !world.roles.includes("Drunk")
        && inBag(state, "Drunk"))
      held.push("Drunk");
  }
  const after = made ? [change(made.phase, m, "Marionette", "evil")] : [];
  return held.map(role => [change("N1", m, role, "good", SETUP_SLOT), ...after]);
}

function typhonNeighbours(world, state, night, seat, demon) {
  if (demon !== "LordOfTyphon") return [[]];
  const n = state.nPlayers;
  const before = night > 1 ? `B${night - 1}` : "N0";
  const phase = `N${night}`;
  const minion = p => TEAM[world.roleAt(p, before)] === "minion";
  const held = new Set();
  for (let p = 0; p < n; p++) held.add(world.roleAt(p, before));
  const spare = state.script.keys.filter(
    k => TEAM[k] === "minion" && !held.has(k) && k !== "Summoner");
  const out = [], seen = new Set();
  const [left, right] = neighboursOf(n, seat);
  for (const [mate, other] of [[left, right], [right, left]]) {
    if (mate === seat || !minion(mate)) continue;
    if (minion(other) || other === seat) {
      if (!seen.has("")) { seen.add(""); out.push([]); }
      continue;
    }
    for (const role of spare) {
      const key = `${other}|${role}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push([change(phase, other, role, "evil")]);
    }
  }
  return out;
}

/** Every way the Summoner's ability can have gone. See solver.py. */
export function summonOptions(world, state) {
  const summoner = world.roles.indexOf("Summoner");
  const final = state.finalPhase();
  const reached = night => phaseIndex(final) >= phaseIndex(`N${night}`);
  const died = [...state.diedAt(summoner)]
    .sort((a, b) => phaseIndex(a) - phaseIndex(b));
  const gone = died.length ? died[0] : null;
  const over = !!state.gameOver;
  const standing = night => gone === null
    || phaseIndex(gone) >= phaseIndex(`N${night}`);
  // An Engineer that may have taken its character: the Storyteller
  // summons then (their jinx, 26.10.2026). See solver.py.
  const jinxed = engineerOnBoard(state) && engineerMayTakeTheSummoner(state);
  const out = [];
  for (const demon of summonable(state))
    for (const night of (demon === "Pukka" ? [2, 3] : [3])) {
      if (!reached(night) || !(standing(night) || jinxed)) continue;
      for (const seat of summonedSeats(world, state, night, demon))
        for (const extra of typhonNeighbours(world, state, night, seat, demon))
          out.push([summoned(`N${night}`, seat, demon), ...extra]);
    }
  if (standing(3)) {
    if (!reached(3)) out.unshift([]);
    else if (over && phaseIndex(final) === phaseIndex("N3"))
      out.push([notSummoned("N3", summoner)]);
  } else if (over && phaseIndex(final) === phaseIndex(gone)) {
    out.push([notSummoned(gone, summoner)]);
  }
  return out.flatMap(way => marionetteEnters(
    world, state, way.find(c => c.summoned) || null).map(
      enters => [...way, ...enters]));
}

/** The night the Summoner made the Demon, as bestSummonedStory is trying
 * it; the first way where nobody is asking. */
transitionRule(function theSummonerSummons(world, state) {
  if (!inBag(state, "Summoner") || !summonerWorld(world)) return [[[], 1.0]];
  let fixed = state._summoned ?? null;
  if (fixed === null) {
    const options = summonOptions(world, state);
    if (!options.length) return [];
    fixed = options[0];
  }
  return [[[...fixed], 1.0]];
});

/** The Summoned change of this story, or null. */
export function summonedChange(world) {
  return (world.changes || []).find(c => c.summoned) || null;
}

// --------------------------------------------------------------------
// The Hatter (22.10.2026, claude/hutmacher-lesarten.md). See solver.py
// for the readings: every way the evil players can have chosen after a
// claimed Hatter died by day, at the very start of the next night; the
// optional rule as a swap that keeps the number of Demons; a death at
// night and a second living Demon are not reckoned yet (Stufe 1).
// --------------------------------------------------------------------
const NOT_HATTED = new Set(["Legion", "Riot", "LilMonsta"]);
export const HATTER_STORIES = 1024;
// How many stories with a tea party a solve may tell, and the fewest
// walks a sampled one takes whatever that says (V Weg 1). See solver.py.
export const TEA = {budget: 30000, exactBudget: 100000, minDives: 1000,
                    told: 0};
// Set by the tests: the prune in bestStoryTold off. See solver.py.
export const TEA_PRUNE = {on: true};
// And the one over a tea party's Summoner (stage 2). See solver.py.
export const SUMMON_TEA_PRUNE = {on: true};

export const hatterOnBoard = state =>
  inBag(state, "Hatter") || takenByAPhilosopher(state, "Hatter");

/** Seats that said they were the Hatter; only their deaths are a tea
 * party (T, 22.10.2026, as for the Barber). See solver.py. */
export function hatterClaimants(state) {
  const out = new Set();
  for (const [seat, role] of Object.entries(state.claims || {}))
    if (role === "Hatter") out.add(Number(seat));
  for (const info of state.infos)
    if (info.type === "Became" && (info.role === "Hatter" || info.was === "Hatter"))
      out.add(Number(info.player));
  for (const [who, [taken]] of Object.entries(state.philosophies() || {}))
    if (taken === "Hatter") out.add(Number(who));
  return out;
}

/** Every moment a claimed Hatter died as one: [[seat, phase]]. */
export function hatterDeaths(world, state) {
  const out = [];
  const claimed = hatterClaimants(state);
  for (let seat = 0; seat < state.nPlayers; seat++) {
    if (!claimed.has(seat)) continue;
    for (const phase of state.diedAt(seat))
      if (fallsAs(world, state, seat, "Hatter", phase)) out.push([seat, phase]);
  }
  return out.sort((a, b) => phaseIndex(a[1]) - phaseIndex(b[1]));
}

const teaNight = phase => ("DEX".includes(phase[0].toUpperCase())
  ? parseInt(phase.slice(1), 10) + 1 : parseInt(phase.slice(1), 10));

// Who may have killed a Hatter at night, and the slot after their turn:
// the Demons together, then each killer on the board. See solver.py
// `tea_slots`.
const TEA_KILLERS = ["Lycanthrope", "PitHag", "Assassin", "Godfather",
                     "Gossip", "Moonchild"];
const DEMONS_DONE = Math.max(...Object.values(CHARACTERS)
  .filter(c => c.team === "demon"
          && (c.other_night || 0) < CHARACTERS.Assassin.other_night)
  .map(c => c.other_night || 0)) + 5;

export function teaSlots(state, night, seat = null) {
  const out = new Set([DEMONS_DONE + 1]);
  const rows = type => state.infos.filter(i => i.type === type
                                          && i.night === night);
  for (const key of TEA_KILLERS) {
    const slot = slotOf(key, night);
    if (slot === null || !onBoard(state, key)) continue;
    if (seat !== null) {
      // As far as the board says, that killer did not. See solver.py.
      if (key === "Lycanthrope") {
        const said = rows("LycanthropeChose");
        if (said.length && said.every(i => i.target !== seat)) continue;
      }
      if (key === "PitHag") {
        const said = rows("PitHagChoice");
        if (said.length && !said.some(i => TEAM[i.role] === "demon")) continue;
      }
      if (key === "Godfather") {
        let any = false;
        for (let p = 0; p < state.nPlayers; p++)
          if (state.diedAt(p).includes(`D${night - 1}`)
              || state.diedAt(p).includes(`E${night - 1}`)) any = true;
        if (!any) continue;
      }
      if (key === "Moonchild"
          && !state.infos.some(i => i.type === "MoonchildChoice"
                               && i.target === seat)) continue;
    }
    out.add(slot + 1);
  }
  return [...out].sort((a, b) => a - b);
}

function hatted(state, team, night, held, demonAlive) {
  const out = [];
  for (const key of state.script.keys) {
    if (TEAM[key] !== team || held.has(key) || NOT_HATTED.has(key)) continue;
    if (key === "Leviathan" && night > 5) continue;
    // A Summoner taken before its third night summons beside the Demon:
    // reckoned since stage 2 (aHattedSummonerSummons).
    out.push(key);
  }
  return out;
}

/** Every way the evil players can have chosen at the start of this
 * night; the first is "nobody did". See solver.py. */
export function teaPartyChoices(view, state, night, slot = null) {
  if (slot !== null)
    return readingAt(`N${night}`, slot, slot,
                     () => teaPartyChoicesAt(view, state, night, slot));
  return teaPartyChoicesAt(view, state, night, null);
}

function teaPartyChoicesAt(view, state, night, slot) {
  const n = state.nPlayers;
  const phase = `N${night}`;
  const before = slot === null ? `D${night - 1}` : phase;
  const made = (p, key) => {
    const c = teaParty(phase, p, key, side(p));
    if (slot !== null) c.slot = slot;
    return c;
  };
  const alive = state.aliveSet(phase);
  const held = new Set();
  for (let p = 0; p < n; p++) held.add(view.roleAt(p, before));
  const side = p => (view.evilAt(p, before) ? "evil" : "good");
  const seats = [];
  for (let p = 0; p < n; p++)
    if (alive.has(p) && ["minion", "demon"].includes(TEAM[view.roleAt(p, before)]))
      seats.push(p);
  const demons = seats.filter(p => TEAM[view.roleAt(p, before)] === "demon");
  const demonAlive = demons.length > 0;
  const each = new Map();
  for (const p of seats)
    each.set(p, view.roleAt(p, before) === "Summoner" && night <= 3 ? []
      : hatted(state, TEAM[view.roleAt(p, before)], night, held, demonAlive));
  const out = [];
  const grow = (list, at, soFar, taken) => {
    if (at === list.length) {
      out.push([...soFar].sort((a, b) => a.seat - b.seat));
      return;
    }
    const p = list[at];
    grow(list, at + 1, soFar, taken);
    for (const key of each.get(p)) {
      if (taken.has(key)) continue;
      grow(list, at + 1, [...soFar, made(p, key)],
           new Set([...taken, key]));
    }
  };
  grow(seats, 0, [], new Set());
  // The optional rule: the Demon and one Minion swap types (B Weg 2,
  // J Weg 1).
  const spareDemons = hatted(state, "demon", night, held, true);
  const spareMinions = hatted(state, "minion", night, held, true);
  for (const demon of demons)
    for (const minion of seats) {
      if (demons.includes(minion)) continue;
      for (const dKey of spareDemons)
        for (const mKey of spareMinions) {
          const swap = [made(minion, dKey), made(demon, mKey)];
          const rest = seats.filter(p => p !== demon && p !== minion);
          grow(rest, 0, swap, new Set([dKey, mKey]));
        }
    }
  return out;
}

function teaStories(world, state, atNight) {
  if (!hatterOnBoard(state)) return [[[], 1.0]];
  const final = phaseIndex(state.finalPhase());
  let stories = [[[], 1.0]];
  for (const [hatter, phase] of hatterDeaths(world, state)) {
    const night = teaNight(phase);
    if ((phase[0].toUpperCase() === "N") !== atNight
        || final < phaseIndex(`N${night}`)) continue;
    // Not if the game ended with that death.
    if (atNight && state.gameOver && final === phaseIndex(phase)) continue;
    const slots = atNight ? teaSlots(state, night, hatter) : [null];
    const grown = [];
    for (const [changes, cost] of stories) {
      const view = changes.length ? new Timeline(world, changes) : world;
      for (const slot of slots)
        for (const choice of teaPartyChoices(view, state, night, slot)) {
          // "Nobody chose" is one story, whichever the slot.
          if (!choice.length && slot !== slots[0]) continue;
          grown.push([[...changes, ...choice], cost]);
        }
    }
    stories = grown;
  }
  return stories;
}

transitionRule(function aHattersTeaParty(world, state) {
  return teaStories(world, state, false);
});

// After a Hatter died at night, straight after its death (C; Hatter
// stage 3c). See solver.py.
transitionRule(function aHattersTeaPartyAtNight(world, state) {
  return teaStories(world, state, true);
});

/** The tea-party changes of this story, by night. */
export function teaParties(world) {
  const out = new Map();
  for (const c of world.changes || [])
    if (c.tea && !c.engineered) {
      if (!out.has(c.phase)) out.set(c.phase, []);
      out.get(c.phase).push(c);
    }
  return out;
}

/** What this story leaves out that the solver does not reckon yet, or
 * null: "two demons" or "lil monsta" ("hatter at night" is reckoned since
 * stage 3c). See solver.py. */
export function hatterUnreckoned(view, state) {
  if (!hatterOnBoard(state))
    return engineerUnreckoned(view, state) ?? boffinUnreckoned(view, state);
  const final = phaseIndex(state.finalPhase());
  for (const [, phase] of hatterDeaths(view, state)) {
    const night = teaNight(phase);
    const atNight = phase[0].toUpperCase() === "N";
    // A Hatter dead at night is reckoned since stage 3c.
    if (atNight && state.gameOver && final === phaseIndex(phase)) continue;
    if (final < phaseIndex(`N${night}`)) continue;
    const before = !atNight ? `D${night - 1}`
      : (night > 1 ? `B${night - 1}` : "N1");
    const alive = state.aliveSet(`N${night}`);
    const n = state.nPlayers;
    // The Demon may have chosen Lil' Monsta (their jinx): not reckoned
    // yet (U Weg 2). See solver.py.
    if (state.script.keys.includes("LilMonsta")) {
      let demonAlive = false;
      for (let p = 0; p < n; p++)
        if (alive.has(p) && TEAM[view.roleAt(p, before)] === "demon") demonAlive = true;
      if (demonAlive) return "lil monsta";
    }
  }
  return engineerUnreckoned(view, state) ?? boffinUnreckoned(view, state);
}

// --------------------------------------------------------------------
// The Engineer (26.10.2026, claude/ingenieur-lesarten.md). See solver.py.
// --------------------------------------------------------------------

const NOT_ENGINEERED = new Set(["LilMonsta", "Legion", "Riot"]);

// Room for every way the Engineer's choice went, beside everything else.
export const ENGINEER_STORIES = 512;

/** The Engineer rows that could have done anything: the first each seat
 * wrote, with a choice an Engineer can make. */
export function engineerRows(state) {
  if (state._engineerCache && state._engineerCache[0] === state.infos
      && state._engineerCache[1] === state.infos.length)
    return state._engineerCache[2];
  const out = [];
  state.infos.forEach((info, idx) => {
    if (info.type !== "EngineerChoice") return;
    if (state.infos.some((o, j) => j < idx && o.type === "EngineerChoice"
                         && o.player === info.player
                         && o.night <= info.night)) return;
    if (engineerChosen(info, state) === null) return;
    out.push(info);
  });
  state._engineerCache = [state.infos, state.infos.length, out];
  return out;
}

const engineerOnBoard = state =>
  onBoard(state, "Engineer") && engineerRows(state).length > 0;

/** A Hatter, or an Engineer that chose. */
export const teaOnBoard = state => hatterOnBoard(state) || engineerOnBoard(state);

/** Could this seat have used the Engineer's ability that night: alive and
 * holding it, at its turn? */
function engineerWorks(view, state, info) {
  const phase = `N${info.night}`;
  if (phaseIndex(state.finalPhase()) < phaseIndex(phase)) return false;
  if (!state.aliveSet(phase).has(info.player)) return false;
  return turnOf("Engineer", info.night,
                () => hasAbility(view, state, info.player, "Engineer", phase));
}

/** Every way a working Engineer's choice changed somebody; [] where it
 * changes nobody, or the solver does not reckon it. */
export function engineerOptions(view, state, info) {
  const chosen = engineerChosen(info, state);
  if (chosen === null) return [];
  const night = info.night;
  const phase = `N${night}`;
  const n = state.nPlayers;
  const [roles, side, demons] = turnOf("Engineer", night, () => {
    const r = [], sd = [];
    for (let p = 0; p < n; p++) {
      r.push(view.roleAt(p, phase));
      sd.push(view.evilAt(p, phase) ? "evil" : "good");
    }
    return [r, sd, [...view.demonsAt(phase)]];
  });
  if (TEAM[chosen[0]] === "demon") {
    const key = chosen[0];
    if (NOT_ENGINEERED.has(key) || demons.length !== 1) return [];
    const seat = demons[0];
    if (roles[seat] === key || TEAM[roles[seat]] !== "demon") return [];
    // A Zombuul that has died once stays what it is (Stelle 86). See
    // solver.py.
    if (!state.aliveSet(phase).has(seat)) return [];
    return [[engineered(phase, seat, key, side[seat])]];
  }
  const seats = [];
  for (let p = 0; p < n; p++) if (TEAM[roles[p]] === "minion") seats.push(p);
  const held = new Set(roles);
  const spare = chosen.filter(k => !held.has(k));
  const free = seats.filter(p => !chosen.includes(roles[p]));
  const k = Math.min(spare.length, free.length);
  if (!k) return [];
  const out = [];
  // Every k seats of the free ones, in order, each with every ordered
  // pick of k spare characters — as itertools does in Python.
  const combos = [];
  const pick = (from, got) => {
    if (got.length === k) { combos.push(got); return; }
    for (let i = from; i < free.length; i++) pick(i + 1, [...got, free[i]]);
  };
  pick(0, []);
  const perms = [];
  const arrange = (got, used) => {
    if (got.length === k) { perms.push(got); return; }
    for (let i = 0; i < spare.length; i++)
      if (!used.has(i)) arrange([...got, spare[i]], new Set([...used, i]));
  };
  arrange([], new Set());
  for (const who of combos)
    for (const what of perms) {
      out.push(who.map((p, i) => engineered(phase, p, what[i], side[p])));
      if (out.length >= ENGINEER_STORIES) return out;
    }
  return out;
}

/** Every way the Engineer's choice went: "nothing changed" first. */
transitionRule(function anEngineerRebuildsTheEvil(world, state) {
  if (!engineerOnBoard(state)) return [[[], 1.0]];
  let stories = [[[], 1.0]];
  for (const info of engineerRows(state)) {
    const grown = [];
    for (const [changes, cost] of stories) {
      grown.push([changes, cost]);
      const view = changes.length ? new Timeline(world, changes) : world;
      if (!engineerWorks(view, state, info)) continue;
      for (const way of engineerOptions(view, state, info))
        grown.push([[...changes, ...way], cost]);
    }
    stories = grown;
  }
  return stories;
});

const engineeredIn = view => (view.changes || []).filter(c => c.engineered);

/** What the Engineer's rows ask of the plan: {night: Set of seats} not
 * working, where its choice would have changed somebody and did not. A
 * change asks nothing, as the Huntsman's does. See solver.py. */
function engineerFailed(world, state) {
  const failures = {};
  const made = new Set(engineeredIn(world).map(c => c.phase));
  for (const info of engineerRows(state)) {
    if (!engineerWorks(world, state, info)) continue;
    const night = info.night;
    if (!made.has(`N${night}`) && engineerOptions(world, state, info).length)
      (failures[night] = failures[night] || new Set()).add(info.player);
  }
  return failures;
}

/** The night an Engineer's change took a living Summoner's character
 * before it summoned, or null (their jinx). */
function summonerEngineeredAway(world, state) {
  for (const c of engineeredIn(world)) {
    const night = parseInt(c.phase.slice(1), 10);
    if (night > 3 || c.role === "Summoner") continue;
    if (world.roleAt(c.seat, night > 1 ? `B${night - 1}` : "N0") === "Summoner"
        && state.aliveSet(c.phase).has(c.seat)) return night;
  }
  return null;
}

function engineerMayTakeTheSummoner(state) {
  return onBoard(state, "Engineer") && engineerRows(state).some(info => {
    const chosen = engineerChosen(info, state);
    return info.night <= 3 && TEAM[chosen[0]] === "minion"
      && !chosen.includes("Summoner");
  });
}

// --------------------------------------------------------------------
// The Boffin (26.10.2026, claude/laborratte-lesarten.md). See solver.py.
// --------------------------------------------------------------------

/** The abilities reckoned so far, each a story of its own (stage 1). */
export const BOFFIN_SEEN = new Set([
  "Fool", "Sailor", "TeaLady", "Soldier", "Monk", "Innkeeper", "Mayor",
  "Pacifist", "Princess", "Tinker", "Gambler", "Acrobat", "Grandmother",
  "Moonchild", "Gossip", "Lycanthrope", "Golem", "Banshee", "Farmer",
  "Virgin", "Saint", "Klutz", "Zealot",
  "Sweetheart", "Courtier", "Minstrel", "Preacher", "Goon",
  "Puzzlemaster",
]);

// Room for every ability, at every moment it is given.
export const BOFFIN_STORIES = 48;

const boffinOnBoard = state => state.script.keys.includes("Boffin");

/** The Boffin rows that name something it could give. */
export function boffinRows(state) {
  if (state._boffinCache && state._boffinCache[0] === state.infos
      && state._boffinCache[1] === state.infos.length)
    return state._boffinCache[2];
  const out = state.infos.filter(i => i.type === "BoffinGave"
                                 && boffinGiven(i, state) !== null);
  state._boffinCache = [state.infos, state.infos.length, out];
  return out;
}

/** Every good character the Boffin could give at that moment (B Weg 1). */
export function boffinMayGive(view, state, phase) {
  const held = Array.from({length: state.nPlayers},
                          (_, p) => view.roleAt(p, phase));
  const out = [];
  for (const key of state.script.keys) {
    if (TEAM[key] !== "townsfolk" && TEAM[key] !== "outsider") continue;
    if (BOFFIN_NEVER_GIVES.has(key)) continue;
    const count = held.filter(r => r === key).length;
    if (count && count >= (CHARACTERS[key].copies || 1)) continue;
    out.push(key);
  }
  return out;
}

/** What a Boffin row says it gave, for a moment of that night, or null:
 * a first-night row is about the Demon dealt, a later row about the
 * Demon made that night (seed 683). See solver.py. */
function boffinNamed(state, night, setup) {
  let named = null;
  for (const info of boffinRows(state))
    if (info.night === night && (night > 1 || setup))
      named = boffinGiven(info, state);
  return named;
}

/** Every ability the Boffin may have given this seat at that moment, as
 * [[mark], cost] — "nothing the town sees" first. */
export function boffinOffers(view, state, phase, seat, slot, setup = false) {
  const may = boffinMayGive(view, state, phase);
  const named = boffinNamed(state, parseInt(phase.slice(1), 10), setup);
  if (named !== null) {
    if (!may.includes(named)) return [];
    const gift = BOFFIN_SEEN.has(named) ? named : BOFFIN_UNSEEN;
    return [[[boffinGift(phase, seat, gift, slot)], 1.0]];
  }
  const seen = may.filter(k => BOFFIN_SEEN.has(k));
  const unseen = may.length - seen.length;
  const out = [];
  if (unseen) out.push([[boffinGift(phase, seat, BOFFIN_UNSEEN, slot)], 1.0]);
  const each = unseen ? 1.0 / unseen : 1.0;
  for (const k of seen) out.push([[boffinGift(phase, seat, k, slot)], each]);
  return out;
}

/** When the Boffin gives something in this story, and to whom. See
 * solver.py `_boffin_moments`. */
function boffinMoments(view, state, setup) {
  const base = view instanceof Timeline ? view.world : view;
  const out = [];
  if (setup) {
    if (base.roles.includes("Boffin")) {
      const start = base.demonAt("N1");
      if (start !== null) out.push(["N1", SETUP_SLOT, start, null]);
    }
    return out;
  }
  const changes = (view.changes || []).filter(c => !c.boffin)
    .map((c, i) => [c, i, changeAt(c)])
    .sort((a, b) => a[2] - b[2] || a[1] - b[1]).map(([c]) => c);
  changes.forEach((c, i) => {
    if (c.role === null || c.role === undefined) return;
    // The board just before this change, and just after it.
    const prior = i ? new Timeline(base, changes.slice(0, i)) : base;
    const after = new Timeline(base, changes.slice(0, i + 1));
    const was = prior.roleAt(c.seat, c.phase);
    if (TEAM[c.role] === "demon") {
      if (was === c.role) return;          // the same Demon as before
      const others = after.demonsAt(c.phase).filter(
        d => d !== c.seat && state.aliveSet(c.phase).has(d));
      const beside = c.summoned && others.length ? others[0] : null;
      out.push([c.phase, c.slot ?? null, c.seat, beside]);
    } else if (c.role === "Boffin" && was !== "Boffin"
               && boffinSeat(prior, state, c.phase) === null) {
      for (const d of after.demonsAt(c.phase))
        out.push([c.phase, c.slot ?? null, d, null]);
    }
  });
  return out;
}

function boffinStories(world, state, setup) {
  if (!boffinOnBoard(state)) return [[[], 1.0]];
  let stories = [[[], 1.0]];
  for (const [phase, slot, seat, beside] of boffinMoments(world, state, setup)) {
    if (boffinSeat(world, state, phase) === null && phase !== "N1") continue;
    const grown = [];
    for (const [changes, cost] of stories) {
      const view = changes.length ? new Timeline(world, changes) : world;
      let offers = boffinOffers(view, state, phase, seat, slot, setup);
      if (beside !== null) {
        // The Storyteller decides (D Weg 2): the first keeps it, or the
        // second gets one and the first's ends.
        grown.push([changes, cost]);
        const end = boffinGift(phase, beside, "", slot);
        offers = offers.map(([way, c]) => [[...way, end], c]);
      }
      for (const [way, c] of offers) {
        grown.push([[...changes, ...way], cost * c]);
        if (grown.length >= BOFFIN_STORIES * 64) break;
      }
    }
    stories = grown;
  }
  return stories;
}

transitionRule(function aBoffinGivesTheDemon(world, state) {
  return boffinStories(world, state, true);
});

transitionRule(function aBoffinGivesANewDemon(world, state) {
  return boffinStories(world, state, false);
});

/** What the Boffin leaves out that the solver does not reckon, or null:
 * Lil' Monsta, whose babysitter changes every night. */
export function boffinUnreckoned(view, state) {
  if (!boffinOnBoard(state) || !view.roles.includes("Boffin")) return null;
  if (inBag(state, "LilMonsta")
      && lilMonstaWorld(view instanceof Timeline ? view.world : view))
    return "boffin";
  return null;
}

/** What the Engineer's row leaves out that the solver does not reckon,
 * or null (G Weg 1). */
export function engineerUnreckoned(view, state) {
  if (!engineerOnBoard(state)) return null;
  for (const info of engineerRows(state)) {
    if (!engineerWorks(view, state, info)) continue;
    const chosen = engineerChosen(info, state);
    if (TEAM[chosen[0]] !== "demon") continue;
    if (NOT_ENGINEERED.has(chosen[0])) return "engineer";
    if (turnOf("Engineer", info.night,
               () => view.demonsAt(`N${info.night}`).length) > 1)
      return "engineer";
  }
  return null;
}

// --------------------------------------------------------------------
// Two living Demons (Hatter stage 2, 25.10.2026). See solver.py.
// --------------------------------------------------------------------

/** The tea-party changes that made somebody the Summoner. */
export const hattedSummoners = view =>
  (view.changes || []).filter(c => c.tea && c.role === "Summoner");

/** Could a Summoner chosen at this tea party act on this night? */
function summonsOn(c, night) {
  const at = parseInt(c.phase.slice(1), 10);
  if (night !== at) return night > at;
  return c.slot === null || c.slot === undefined
    || c.slot < slotOf("Summoner", night);
}

/** Every way a Summoner chosen at a tea party summoned: "nobody" first.
 * See solver.py. */
const hattedSummonerRule = transitionRule(
  function aHattedSummonerSummons(world, state) {
    const tea = hattedSummoners(world);
    if (!tea.length) return [[[], 1.0]];
    const final = phaseIndex(state.finalPhase());
    const n = state.nPlayers;
    const out = [[[], 1.0]];
    for (const c of tea) {
      const seat = c.seat;
      const ways = [];
      for (const night of [2, 3]) {
        const phase = `N${night}`;
        if (final < phaseIndex(phase) || !summonsOn(c, night)) continue;
        if (!state.aliveSet(phase).has(seat)
            || world.roleAt(seat, phase) !== "Summoner") continue;
        const held = new Set();
        for (let p = 0; p < n; p++) held.add(world.roleAt(p, phase));
        for (const demon of summonable(state)) {
          if (held.has(demon) || (night === 2 && demon !== "Pukka")) continue;
          for (const target of summonedSeats(world, state, night, demon,
                                             false))
            for (const extra of typhonNeighbours(world, state, night, target,
                                                 demon))
              ways.push([[summoned(phase, target, demon), ...extra], 1.0]);
        }
      }
      out.push(...sampledWays(world, c, ways));
    }
    return out;
  });

// While a solve estimates (Hatter stage 2, Weg 2): how many of a tea
// party's Summoner's ways each world tells, or null for all. See
// solver.py.
export const SUMMON_SAMPLE = {k: null, size: 8};

/** A number from a string, the same in Python and JavaScript. */
function stable(text) {
  let got = 0;
  for (let i = 0; i < text.length; i++)
    got = (got + (i + 1) * text.charCodeAt(i)) % 2147483647;
  return got;
}

/** Every way, or while estimating a fixed spread of k of them. */
function sampledWays(world, c, ways) {
  const k = SUMMON_SAMPLE.k;
  if (k === null || ways.length <= k) return ways;
  const step = Math.ceil(ways.length / k);
  const offset = stable(`${world.roles.join("|")}|${c.seat}|${c.phase}`) % step;
  return ways.filter((_w, i) => i >= offset && (i - offset) % step === 0);
}

/** One over the number of ways the tea party's Summoner could have
 * summoned, for a story where it did; 1 otherwise. See solver.py. */
function summonShare(world, changes, state) {
  if (!changes.some(c => c.summoned)) return 1.0;
  const tea = changes.filter(c => c.tea);
  if (!tea.some(c => c.role === "Summoner")) return 1.0;
  const ways = offersOf(hattedSummonerRule, new Timeline(world, tea),
                        state).length - 1;
  return ways > 0 ? 1.0 / ways : 1.0;
}

transitionRule(function theMinionsChooseABabysitter(world, state) {
  if (!inBag(state, "LilMonsta") || !lilMonstaWorld(world))
    return [[[], 1.0]];
  const last = Math.max(1, parseInt(state.finalPhase().slice(1), 10));
  // One babysitter a night, as bestBabysatStory is trying them; the first
  // of each night's options where nobody says.
  const fixed = state._babysitters
    || babysitterOptions(world, state).map(o => (o.length ? o[0] : null));
  const stories = [];
  const walk = (night, soFar) => {
    if (stories.length >= LIL_MONSTA_STORIES) return;
    if (night > last) { stories.push([soFar, 1.0]); return; }
    const one = night - 1 < fixed.length ? fixed[night - 1] : null;
    for (const seat of one === null ? [] : [one]) {
      const chosen = [...soFar, babysits(`N${night}`, seat)];
      for (const [how, extra] of babysitterFalls(world, state, seat, night)) {
        if (how === "go on") {
          walk(night + 1, chosen);
        } else {
          stories.push([[...chosen, ...extra], 1.0]);
        }
        if (stories.length >= LIL_MONSTA_STORIES) return;
      }
    }
  };
  walk(1, []);
  return stories;
});

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
    const began = info.night > 1 ? `B${info.night - 1}` : "N0";  // the deal, as Python's `_before`
    // The seat that said so, if it has the ability — held or taken by a
    // Philosopher — else whoever works it. See solver.py.
    const charmer = hasAbility(world, state, info.player, "SnakeCharmer", began)
      ? info.player : whoeverWorks(world, state, "SnakeCharmer", began);
    // The one it chose, of two living Demons (Hatter stage 2).
    const demons = world.demonsAt(began);
    let demon = demons.includes(info.target) ? info.target
      : (demons.length ? demons[0] : null);
    // Lil' Monsta's first babysitter is chosen at 15, before the charmer
    // at 20 (E, Weg 1, 21.10.2026).
    if (demon === null && info.night === 1) demon = babysitterAt(world, phase);
    if (charmer === null || demon === null || charmer === demon) continue;
    if (info.target !== demon) continue;   // they pointed at somebody else
    // A babysitter is swapped like a Demon: character and side, both ways.
    const sitter = babysitterAt(world, info.night > 1 ? began : phase);
    const sides = sitter !== demon ? ["evil", "good"]
      : [world.alignmentAt(demon, began), world.alignmentAt(charmer, began)];
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
       // Unless an Engineer made it another Demon earlier that night
       // (26.10.2026). See solver.py.
       change(after, charmer,
              ((world.changes || []).filter(c => c.engineered
                && c.seat === demon && c.phase === after).pop() || {}).role
                ?? world.roleAt(demon, began), sides[0]),
       change(after, demon, "SnakeCharmer", sides[1])],
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
  // Held for the length of one `bestStory`, like `finalPhase`.
  if (state._nightDeathsHeld) return state._nightDeathsHeld;
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
  // Pinned on the dealt character; where something can change characters
  // nothing is pinned, and the hard row does the work (Stelle 59). See
  // solver.py.
  const movers = ["PitHag", "Barber", "SnakeCharmer", "Farmer", "Huntsman",
                  "FangGu"];
  if (movers.some(key => onBoard(state, key))) return pinned;
  const changed = new Set(state.infos.filter(i => i.type === "Became")
    .map(i => i.player));
  const pin = (seat, roles) => {
    if (changed.has(seat)) return;      // it said it was handed another
    const wanted = new Set(roles);
    pinned[seat] = pinned[seat]
      ? new Set([...pinned[seat]].filter(r => wanted.has(r)))
      : wanted;
  };
  // A Philosopher that wrote down taking it may be the one (group 5).
  const orItsPhilosopher = (seat, role) => {
    const taken = (state.philosophies() || {})[seat];
    const out = taken && taken[0] === role ? [role, "Philosopher"] : [role];
    // Or a Demon the Boffin gave it (26.10.2026).
    if (state.script.keys.includes("Boffin"))
      out.push(...state.script.keys.filter(k => TEAM[k] === "demon"));
    return out;
  };
  for (const info of state.infos) {
    if (info.type === "VirginNomination" && info.triggered) {
      pin(info.player, orItsPhilosopher(info.player, "Virgin"));
      // The nomination only fires on a Townsfolk, or the Spy wearing one.
      // The Drunk is an Outsider, so a Drunk nominator is out.
      const spies = state.script.keys.filter(
        k => CHARACTERS[k].registers.includes("townsfolk"));
      pin(info.nominator, [...state.script.townsfolk, ...spies]);
    } else if (info.type === "SlayerShot" && info.died) {
      pin(info.player, orItsPhilosopher(info.player, "Slayer"));
      // Not the target: the Demon it hit may be a Minion that caught the
      // star (14.10.2026).
    }
  }
  return pinned;
}

/** Quiet Virgin nominations that carry nothing.
 *
 * The ability only fires the first time a Townsfolk nominates, so once
 * one nomination is on the record the later quiet ones say nothing.
 */
/** Did this world's Zealot sit out a vote it had to cast, on a day with a
 * nomination and five alive? A Zealot that did not vote is no Zealot
 * (table ruling, 08.10.2026). See solver.py. */
function aZealotKeptItsHandDown(world, state) {
  if (!inBag(state, "Zealot")) return false;
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
      // And a Philosopher that took it (group 5, 14.10.2026).
      if (!voted.has(seat) && !state.diedAt(seat).includes(phase)
          && (world.roleAt(seat, phase) === "Zealot"
              || tookIt(world, state, seat, "Zealot", phase)))
        return true;
  }
  return false;
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

/** The world with one seat read as the Recluse, for registration only: a
 * Philosopher that took it registers as it would, dead or alive (group 6,
 * N and F, 14.10.2026). Everything but these three is the world's own.
 * See solver.py. */
function asRecluse(world, who) {
  const roleAt = (seat, phase) =>
    seat === who ? "Recluse" : world.roleAt(seat, phase);
  const own = {
    roleAt,
    teamAt: (seat, phase) => TEAM[roleAt(seat, phase)],
    findAt: (role, phase) => {
      for (let seat = 0; seat < world.roles.length; seat++)
        if (roleAt(seat, phase) === role) return seat;
      return null;
    },
  };
  return new Proxy(world, {
    get(target, prop) {
      if (prop in own) return own[prop];
      const value = target[prop];
      return typeof value === "function" ? value.bind(target) : value;
    },
  });
}

/** Philosophers that took the Recluse, by then — alive or dead (F). */
function philosopherRecluses(world, state, phase) {
  return Object.keys(state.philosophies() || {}).map(Number)
    .sort((a, b) => a - b)
    .filter(who => tookIt(world, state, who, "Recluse", phase));
}

/** Sort every ledger row into: fits, contradicts, or was invented.
 *
 * Returns {failures, ftInfos, invented, mustWork}, or null if the world
 * is flatly impossible. The invention cost is a product rather than a
 * count, because how much a made-up reading costs depends on how far you
 * said you believed it.
 */
/** Their jinx: "If the Mastermind is alive and the Lleech's host dies by
 * execution, the Lleech lives but loses their ability" (11.10.2026). */
function aMastermindKeepsTheLleech(world, state, host, at) {
  if (at[0] !== "D" || !inBag(state, "Mastermind")) return false;
  if (state.executionDeath(Number(at.slice(1))) !== host) return false;
  const mastermind = world.findAt("Mastermind", at);
  return mastermind !== null && state.aliveSet(at).has(mastermind);
}

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
  // Rows that held only if somebody other than their source was impaired
  // or working: {night, source, impaired, working}. That or the source off
  // will do; `explainOne` tries both. So far only a Chambermaid whose count
  // turns on a Wraith (table ruling, 08.10.2026).
  const either = [];
  // Rows that held only with the faux paw reading evil, by night and
  // Lycanthrope: their sources. See below.
  const fauxWorking = {};

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
    const vortox = holdingNow(world, state, "Vortox", `D${day}`);
    if (vortox === null || !state.aliveSet(`D${day}`).has(vortox)) continue;
    fail(day, vortox);
  }

  // Two deaths that name a character nobody chose to reveal, and the one
  // who did it has to have been working.
  for (const [day, seat] of Object.entries(state.witchDeaths || {})
       .sort((a, b) => Number(a[0]) - Number(b[0]))) {
    const witch = world.findAt("Witch", `N${day}`);
    // "If just 3 players live, you lose this ability" — and the curse
    // goes with it.
    if (witch !== null && minionStillActs(world, state, witch, `N${day}`)
        && state.aliveSet(`D${day}`).size > 3) {
      (working[day] = working[day] || new Set()).add(witch);
      continue;
    }
    // Or a Yaggababble's kill by day, which is rare and costs (table
    // ruling, 11.10.2026). Never itself.
    const yagga = inBag(state, "Yaggababble")
      ? yaggababbleAt(world, state, `D${day}`) : null;
    if (yagga === null || yagga === Number(seat)) return null;
    invented *= PRIORS.YAGGABABBLE_BY_DAY_PENALTY;
    (working[day] = working[day] || new Set()).add(yagga);
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
    // Not when she is the one executed: a Scarlet Woman babysitting Lil'
    // Monsta (21.10.2026).
    if (scarletWomanTakesOver(world, state, c.phase)
        && world.findAt("ScarletWoman", c.phase) !== c.seat)
      fail(day, world.findAt("ScarletWoman", c.phase));
  }

  // The Summoner (21.10.2026): working when it made the Demon, unless a
  // Courtier or a Preacher took its ability (their jinxes); drunk or
  // poisoned on a turn that made none (E, Weg 1). See solver.py.
  if (inBag(state, "Summoner")) {
    const summoner = world.find("Summoner");
    // An Engineer that took a living Summoner's character left its
    // ability to the Storyteller (their jinx, 26.10.2026). See solver.py.
    const away = engineerOnBoard(state) ? summonerEngineeredAway(world, state)
      : null;
    const jinxed = away === null && engineerOnBoard(state)
      && engineerMayTakeTheSummoner(state);
    // Asked as a question about the board from its night on. See
    // solver.py.
    if (engineerOnBoard(state) && summoner !== null && summoner !== undefined
        && engineerMayTakeTheSummoner(state)) world.roleAt(summoner, "N3");
    if (summoner !== null && summoner !== undefined)
      for (const c of world.changes || []) {
        const night = parseInt(c.phase.slice(1), 10);
        if (c.notSummoned && away !== null) return null;
        if (c.summoned && jinxed) {
          const gone = [...state.diedAt(summoner)]
            .sort((a, b) => phaseIndex(a) - phaseIndex(b));
          if (gone.length && phaseIndex(gone[0]) < phaseIndex(c.phase))
            return null;
        }
        if (c.summoned) {
          if (away === null
              && !(onBoard(state, "Courtier") || onBoard(state, "Preacher")))
            (working[night] = working[night] || new Set()).add(summoner);
        } else if (c.notSummoned && c.phase === "N3"
                   && state.aliveSet("N3").has(summoner)) {
          fail(night, summoner);
        }
      }
  }

  // A Summoner chosen at a tea party (Hatter stage 2): working when it
  // made a Demon, drunk or poisoned on a third night it reached holding
  // it, alive, with none made. See solver.py.
  if (inBag(state, "Summoner") && teaOnBoard(state)) {
    const made = (world.changes || []).find(c => c.summoned) || null;
    const final = phaseIndex(state.finalPhase());
    for (const c of hattedSummoners(world)) {
      const seat = c.seat;
      if (made) {
        if (!(onBoard(state, "Courtier") || onBoard(state, "Preacher"))) {
          const night = parseInt(made.phase.slice(1), 10);
          (working[night] = working[night] || new Set()).add(seat);
        }
      } else if (final >= phaseIndex("D3") && summonsOn(c, 3)
                 && state.aliveSet("N3").has(seat)
                 && !state.diedAt(seat).includes("N3")
                 && world.roleAt(seat, "N3") === "Summoner") {
        fail(3, seat);
      }
    }
  }

  // The Engineer (26.10.2026): drunk or poisoned where its choice would
  // have changed somebody and did not.
  if (engineerOnBoard(state)) {
    for (const [night, seats] of Object.entries(engineerFailed(world, state)))
      for (const seat of seats) fail(Number(night), seat);
  }

  // The Hatter (22.10.2026): whoever chose a new character did so
  // because a Hatter died working. See solver.py.
  if (hatterOnBoard(state)) {
    const parties = teaParties(world);
    if (parties.size) {
      const died = hatterDeaths(world, state);
      for (const at of parties.keys()) {
        const night = parseInt(at.slice(1), 10);
        const why = died.filter(([, phase]) => teaNight(phase) === night);
        if (!why.length) return null;
        const [seat, phase] = why[why.length - 1];
        const day = parseInt(phase.slice(1), 10);
        (working[day] = working[day] || new Set()).add(seat);
      }
    }
  }

  for (const day of Object.keys(state.executions || {}).map(Number)) {
    const seat = state.executionDeath(day);
    if (seat === null) continue;
    // And a Philosopher that took her (group 6, D, 14.10.2026).
    if (hasAbility(world, state, seat, "Saint", `D${day}`))
      fail(day, soberSeat(world, state, seat, "Saint", `D${day}`));
    // A Sailor cannot die, and that holds in daylight — so a working one
    // walks away from its own execution.
    if (hasAbility(world, state, seat, "Sailor", `D${day}`))
      fail(day, soberSeat(world, state, seat, "Sailor", `D${day}`));
    // And the same for a Tea Lady's neighbour: executed and dead, so she
    // was not working. The mirror of her saving one.
    for (const lady of teaLadyFailedAtTheGallows(world, state, day, seat))
      fail(day, lady);
  }

  // A Vizier cannot die during the day. One that did was not working —
  // drunk or poisoned it dies like anybody (table ruling, 10.10.2026).
  if (inBag(state, "Vizier"))
    for (const [seat, phase] of state.deathPhases())
      if (phase[0] === "D" && world.roleAt(seat, phase) === "Vizier"
          && !(executed(state, Number(phase.slice(1)), seat)
               && babysitterAt(world, phase) === seat))
        fail(Number(phase.slice(1)), seat);

  // A Lleech dies when its host does and not before (11.10.2026). The
  // host is this telling's hidden choice. See solver.py.
  if (inBag(state, "Lleech")) {
    const lleech = world.find("Lleech");
    const host = lleechHost(state);
    if (lleech !== null && host !== null && host !== undefined) {
      const byPhase = (a, b) => phaseIndex(a) - phaseIndex(b);
      const mine = [...state.diedAt(lleech)].sort(byPhase);
      const gone = mine.length ? mine[0] : null;
      const theirs = host >= 0 ? [...state.diedAt(host)].sort(byPhase) : [];
      const at = theirs.length ? theirs[0] : null;
      if (at !== null && world.roleAt(lleech, at) === "Lleech"
          && state.aliveSet(at).has(lleech)
          && (gone === null || phaseIndex(gone) >= phaseIndex(at))) {
        const key = Number(at.slice(1));
        if (gone === at)
          (working[key] = working[key] || new Set()).add(lleech);
        else if (!aMastermindKeepsTheLleech(world, state, host, at))
          fail(key, lleech);
      }
      if (gone !== null && world.roleAt(lleech, gone) === "Lleech"
          && (at === null || phaseIndex(gone) < phaseIndex(at)))
        fail(Number(gone.slice(1)), lleech);
    }
  }

  // A day with votes on the board was voted with eyes open, so no Organ
  // Grinder was working then (10.10.2026).
  if (inBag(state, "OrganGrinder"))
    for (const [dayKey, voters] of Object.entries(state.votes || {})) {
      if (!voters || !(voters.length ?? voters.size)) continue;
      const phase = `D${dayKey}`;
      const grinder = world.findAt("OrganGrinder", phase);
      if (grinder !== null && state.aliveSet(phase).has(grinder))
        fail(Number(dayKey), grinder);
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
  // Once per game for each Professor, and again for one raised since, in
  // the order they happened (13.10.2026). See solver.py.
  const used = new Map();
  const raises = [];
  for (const [seatKey, phases] of Object.entries(state.resurrections || {}))
    for (const phase of phases) {
      const night = parseInt(phase.slice(1), 10);
      if (Number.isFinite(night)) raises.push([night, Number(seatKey), phase]);
    }
  raises.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  for (const [night, seat, phase] of raises) {
    // A dead player the Al-Hadikhia chose, who chose life (21.10.2026).
    if (inBag(state, "AlHadikhia")
        && alHadikhiaChosen(state, night).includes(seat)) {
      // Asked at its turn (Hatter stage 3c). See solver.py.
      const [ah, held] = turnOf("AlHadikhia", night, () => {
        const got = holdingNow(world, state, "AlHadikhia", phase);
        return [got, got !== null && got !== undefined
                     && world.roleAt(got, phase) === "AlHadikhia"];
      });
      if (held && state.aliveSet(phase).has(ah)) {
        (working[night] = working[night] || new Set()).add(ah);
        continue;
      }
    }
    {
      const shabaloth = inBag(state, "Shabaloth")
        ? turnOf("Shabaloth", night,
                 () => holdingNow(world, state, "Shabaloth", phase)) : null;
      if (shabaloth !== null && night >= 3 &&
          state.aliveSet(phase).has(shabaloth)) continue;
      // The holder, or a Philosopher that took it, ahead (13.10.2026).
      const back = returnedAtPhase(state, phase);
      const prof = turnOf("Professor", night, () => {
        let got = world.findAt("Professor", phase);
        for (const who of Object.keys(state.philosophies() || {}).map(Number)
               .sort((a, b) => b - a))
          if (state.aliveSet(phase).has(who) && who !== seat && !back.has(who)
              && tookIt(world, state, who, "Professor", phase)) got = who;
        return got;
      });
      if (prof === null || !onBoard(state, "Professor")) return null;
      if (!state.aliveSet(phase).has(prof) || night < 2) return null;
      const raised = world.roleAt(seat, phase);
      if (TEAM[raised] !== "townsfolk" &&
          !CHARACTERS[raised].registers.includes("townsfolk")) return null;
      (working[night] = working[night] || new Set()).add(prof);
      if (used.has(prof) && !((state.resurrections || {})[prof] || []).some(
            at => used.get(prof) < parseInt(String(at).slice(1), 10)
                  && parseInt(String(at).slice(1), 10) <= night))
        return null;                       // once per game
      used.set(prof, night);
    }
  }

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

  if (aZealotKeptItsHandDown(world, state)) return null;  // did not vote

  if (inBag(state, "Leviathan")) leviathanDemands(world, state, fail, either);

  // A player a Mezepheles turned: it was working that night — unless
  // something later that night may have reached it.
  for (const c of world.changes || []) {
    if (c.turned !== "mezepheles") continue;
    const night = parseInt(c.phase.slice(1), 10);
    const mez = world.findAt("Mezepheles", `B${night - 1}`);
    if (mez === null || mez === undefined) return null;
    if (!actedBeforeTheDemonOnly(world, state, night))
      (working[night] = working[night] || new Set()).add(mez);
  }

  const spent = spentNominations(state);
  const seats = sourceSeats(state);
  // Each row read at its character's turn of its night, attribution
  // included (Hatter stage 3b, E Weg 1). See solver.py.
  state.infos.forEach((info, idx) => atRowTurn(info, () => {
    // Once a hard fact did not hold nothing further is judged, as in
    // Python, which returns on the spot: the rows after it would only
    // ask about sides nobody needs any more (`explainOrRecall`).
    if (impossible) return;
    if (spent.has(idx)) { outcome[idx] = SPENT; return; }
    // Shown Lil' Monsta: true of whoever babysat that night, made up by
    // anybody else (21.10.2026, C).
    if (info.type === "LilMonstaBabysat") {
      if (info.holds(world, state, null)) outcome[idx] = HELD;
      else { invented *= inventionCost(info); outcome[idx] = INVENTED; }
      return;
    }
    if (info.hard()) {
      if (!info.holds(world, state, null)) { impossible = true; }
      else {
        outcome[idx] = HELD;
        // A fact can lean on somebody too: a Banshee announced was a
        // Banshee whose ability worked that night.
        // Or the Boffin behind a Demon it gave that ability (26.10.2026).
        for (let who of info.leanedOn(world, state)) {
          if (info.sourceRole)
            who = soberSeat(world, state, who, info.sourceRole,
                            `N${info.night}`);
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
      const began = info.night > 1 ? `B${info.night - 1}` : "N0";  // the deal, as Python's `_before`
      seat = world.findAt(role, began);
      if (seat === null) seat = world.findAt(role, phase);
      // Nobody holds it, and the one who said it believes it does: a
      // Drunk with that token (13.10.2026). See solver.py.
      if (seat === null && Number.isInteger(info.player)
          && world.believes[info.player] === role) seat = info.player;
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
        // Or a Demon the Boffin gave it (26.10.2026).
        const given = boffinHolders(world, state, role, phase);
        if (given.length) seat = given[0];
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
    const vortox = holdingNow(world, state, "Vortox", phase);
    const vortoxed = vortox !== null && state.aliveSet(phase).has(vortox);
    // Judged at the moment it acted. A Snake Charmer swap is dated at
    // the night, so at `phase` the charmer no longer holds the character
    // — and its own row was charged as invented, putting a world where
    // the swap really happened at 0.4 against 1.0 for one where it could
    // not.
    const acted = info.night > 1 ? `B${info.night - 1}` : "N0";  // the deal, as Python's `_before`
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
    // A Pixie mad about this character: made up until its holder dies,
    // at no cost, and its own from the night after (11.10.2026).
    if (held === ABSENT && seat !== null
        && (world.roleAt(seat, phase) === "Pixie"
            || tookIt(world, state, seat, "Pixie", phase))
        && onBoard(state, "Pixie")) {
      const got = pixieGain(world, state, seat);
      if (got !== null && got[0] === role) {
        if (got[1] !== null && info.night >= got[1])
          held = vortoxed && TEAM[role] === "townsfolk" ? INVERTED : GENUINE;
        else held = ARBITRARY;
      }
    }
    // A Demon the Boffin gave this ability (26.10.2026): its own, worked
    // through the Boffin, weighed like the character's own (G Weg 1).
    if (held === ABSENT && seat !== null && role !== null && role !== undefined
        && boffinGiftOf(world, state, seat, acted) === role)
      held = vortoxed && TEAM[role] === "townsfolk" ? INVERTED : GENUINE;
    const sober = seat === null ? seat
      : soberSeat(world, state, seat, role, acted);
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
    // A seat that was turned evil and knows it still has its ability and
    // is told the truth, and says what suits it: what holds is taken as
    // said, what does not was made up (11.10.2026). See solver.py.
    if (knowsItTurnedEvil(world, seat, phase)) {
      if (info.type === "FortuneTeller" || held === INVERTED
          || info.holds(world, state, null, seat)) outcome[idx] = HELD;
      else {
        invented *= inventionCost(info);
        outcome[idx] = INVENTED;
      }
      return;
    }
    // A Vortox falsifies information, not choices.
    // One question, asked in one place: does a Vortox reach this row?
    // A shot or a Virgin's nomination is still checked like any act
    // (Stelle 59, 14.10.2026). See solver.py.
    if (held === INVERTED && !info.isInformation(state) && info.inTheOpen)
      held = GENUINE;
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
      // True every way an open side could be (Stelle 72).
      let wasTrue;
      if (info.isTrue) {
        wasTrue = true;
        for (const view of eachRealSide(world, state, `N${info.night}`))
          if (!info.isTrue(view, state, seat)) { wasTrue = false; break; }
      } else wasTrue = info.holds(world, state, null, seat);
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

    // The Lycanthrope's faux paw registers evil while it works, and
    // whether it worked is the plan's: a row that asked about it is tried
    // both ways (11.10.2026). See solver.py.
    let ok = null, fauxNeed = null;
    if (info.type !== "FortuneTeller" && fauxPaw(state) !== null) {
      state._fauxMode = "on"; state._fauxHit = false;
      ok = info.holds(world, state, null, seat);
      if (state._fauxHit) {
        state._fauxMode = "off";
        const okOff = info.holds(world, state, null, seat);
        state._fauxMode = "on";
        const lyc = fauxPawLycanthrope(world, state, phase, false);
        if (ok && !okOff) fauxNeed = ["working", lyc];
        else if (okOff && !ok) fauxNeed = ["impaired", lyc];
      }
      state._fauxHit = false;
    }
    if (ok === null && info.type !== "FortuneTeller")
      ok = info.holds(world, state, null, seat);
    // Or it holds with a Philosopher that took the Recluse read as the
    // Recluse: then that Philosopher was working (group 6, N).
    let recluseNeed = null;
    if (ok === false && info.type !== "FortuneTeller")
      for (const who of philosopherRecluses(world, state, phase))
        if (info.holds(asRecluse(world, who), state, null, seat)) {
          recluseNeed = who; break;
        }
    // That, or its own source was off: either explains it.
    if (recluseNeed !== null && !witnessed) {
      either.push({night: info.night, source: [sober], impaired: [],
                   working: [recluseNeed]});
      outcome[idx] = EXCUSED;
      return;
    }
    if (recluseNeed !== null) ok = true;

    if (fauxNeed !== null && fauxNeed[0] === "impaired" && !witnessed) {
      either.push({night: info.night, source: [sober],
                   impaired: [fauxNeed[1]], working: []});
      outcome[idx] = EXCUSED;
      return;
    }

    if (info.type === "FortuneTeller") {
      // Whether it held depends on where the red herring was, which is
      // settled later. Left open until then.
      ftInfos.push([info, seat, idx, null]);
    } else if (witnessed && !ok) {
      // Nothing excuses it: a droisoned source tells the other player
      // nothing at all, so the words did not come from the game.
      invented *= inventionCost(info);
      outcome[idx] = INVENTED;
    } else if (!ok) {
      // Poison has to land on whoever the information came from —
      // poisoning the messenger changes nothing. Or on the Boffin behind
      // a Demon it gave the ability (26.10.2026).
      fail(info.night, sober);
      outcome[idx] = EXCUSED;
    } else {
      outcome[idx] = HELD;
      if (fauxNeed !== null && witnessed)
        (working[info.night] || (working[info.night] = new Set()))
          .add(fauxNeed[1]);
      else if (fauxNeed !== null) {
        // The Lycanthrope worked — or it did not, the reading was false
        // and its source droisoned. One choice a night covers every such
        // row (open item 57, 12.10.2026). See solver.py.
        const key = `${info.night}|${fauxNeed[1]}`;
        (fauxWorking[key] || (fauxWorking[key] = {night: info.night,
          lyc: fauxNeed[1], sources: new Set()})).sources.add(sober);
      }
      // **A droisoned character cannot misregister.** Registration is a
      // plain ability and a plain ability simply does not function, so a
      // row that held only by somebody misregistering forbids that seat
      // from having been droisoned that night.
      for (const who of (info.leanedOn ? info.leanedOn(world, state, seat) : []))
        (working[info.night] || (working[info.night] = new Set())).add(who);
      if (recluseNeed !== null)
        (working[info.night] || (working[info.night] = new Set()))
          .add(recluseNeed);
      // And one that held only if somebody else was impaired or working:
      // a Chambermaid's count that turns on a Wraith, which a drunk one
      // does not wake. Its own source being off explains it as well.
      const needs = info.instead ? info.instead(world, state, seat) : null;
      if (needs) {
        either.push({night: info.night, source: [sober],
                     impaired: needs[0], working: needs[1]});
        if (needs[0].length) outcome[idx] = EXCUSED;
      }
    }
  }));
  if (impossible) return null;            // a hard fact did not hold

  // In the order Python sorts its (night, Lycanthrope) keys.
  for (const group of Object.values(fauxWorking).sort(
         (a, b) => a.night - b.night || a.lyc - b.lyc))
    either.push({night: group.night, source: [...group.sources].sort((a, b) => a - b),
                 impaired: [], working: [group.lyc]});
  return {failures, ftInfos, invented, mustWork: working, vortoxOr, either};
}

/** The living Demon at this moment, if it is a Yaggababble. */
function yaggababbleAt(world, state, phase) {
  const demon = demonHolding(world, phase, "Yaggababble");
  if (demon === null || !state.aliveSet(phase).has(demon)) return null;
  return demon;
}

/** Every seat executed that day, by any route the rules call one. */
function allExecuted(state, day) {
  const out = [];
  const seat = state.executedOn(day);
  if (seat !== null) out.push(seat);
  const mad = (state.madnessExecutions || {})[day];
  if (mad !== null && mad !== undefined && !out.includes(mad)) out.push(mad);
  for (const info of state.infos)
    if (info.type === "VirginNomination" && info.triggered
        && info.night === day && !out.includes(info.nominator))
      out.push(info.nominator);
  return out;
}

/** Good, with nothing open about it. */
function surelyGood(world, state, seat, phase) {
  if (actsAsCultLeader(world, state, seat, phase)) {
    const sides = cultSides(world, state, seat, phase);
    return sides.size === 1 && sides.has(false);
  }
  if (sideOpen(world, state, seat, phase)) return false;
  return !world.evilAt(seat, phase);
}

/** The seat that nominated whoever the town executed that day, when the
 * board can say. */
function whoNominatedTheExecuted(state, day) {
  const hanged = state.executedOn(day);
  if (hanged === null) return null;
  for (const info of state.infos) {
    if (info.night !== day) continue;
    if (info.type === "ExecutionNomination") return info.player;
    if ((info.type === "PrincessNominated" || info.type === "GolemNomination")
        && info.target === hanged) return info.player;
  }
  const who = [...new Set((state.nominations || {})[day] || [])];
  return who.length === 1 ? Number(who[0]) : null;
}

/** What a game going on says about a Leviathan in this world: not
 * announced, a second good player executed, past day five, and its
 * jinxes with the Soldier, the Innkeeper, the Exorcist and the
 * Grandmother. See `_leviathan_demands` in solver.py (11.10.2026). */
function leviathanDemands(world, state, fail, either) {
  if (!aLeviathanIsToldOf(world)) return;
  const reached = Math.floor((phaseIndex(state.finalPhase()) + 1) / 2);
  let first = null;
  for (let day = 1; day <= reached; day++) {
    const seat = leviathanAt(world, state, `D${day}`);
    if (seat !== null) { first = [day, seat]; break; }
  }
  if (first === null) return;
  if (!state.infos.some(info => info.type === "LeviathanAnnounced"))
    fail(first[0], first[1]);

  let goodGone = 0;
  for (let day = first[0]; day <= reached; day++) {
    const phase = `D${day}`;
    const lev = leviathanAt(world, state, phase);
    if (lev === null) continue;
    const on = wentOnAfter(state, day);
    for (const seat of allExecuted(state, day)) {
      if (!surelyGood(world, state, seat, phase)) continue;
      goodGone += 1;
      if (goodGone >= 2 && on) fail(day, lev);
    }
    if (day >= 5 && on) fail(day, lev);
    if (!on) continue;

    const hanged = state.executedOn(day);
    if (hanged !== null && whoNominatedTheExecuted(state, day) === lev) {
      const behind = [];
      if (hasAbility(world, state, hanged, "Soldier", phase)) behind.push(hanged);
      const night = `N${day}`;
      for (const info of state.infos) {
        if (info.night !== day) continue;
        if (info.type === "InnkeeperChoice"
            && (info.a === hanged || info.b === hanged)
            && hasAbility(world, state, info.player, "Innkeeper", night))
          behind.push(info.player);
        else if (info.type === "ExorcistChoice" && info.target === hanged
                 && hasAbility(world, state, info.player, "Exorcist", night))
          behind.push(info.player);
      }
      for (const who of behind)
        either.push({night: day, source: [lev], impaired: [who], working: []});
    }

    const dead = state.executionDeath(day);
    if (dead !== null && inBag(state, "Grandmother"))
      for (const info of state.infos)
        if (info.type === "GrandmotherInfo" && info.target === dead
            && info.night <= day && state.aliveSet(phase).has(info.player)
            && hasAbility(world, state, info.player, "Grandmother", phase))
          either.push({night: day, source: [lev], impaired: [info.player],
                       working: []});
  }
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
  // And this telling's hidden choices (`hiddenChoices`).
  const hidden = state._hidden ? `|${state._hidden[0]}|${state._hidden[1]}` : "";
  if (!LISTENING) {                       // nobody turns evil that way here
    const key = `${night}#${upto.map(changeKey).join(";")}${hidden}`;
    let got = memo.got.get(key);
    if (got === undefined) {
      got = theOnesThatCanWin(explainNight(world, state, night, died()));
      memo.got.set(key, got);
    }
    return got;
  }
  // Kept per everything but who turned evil, and with whose side was
  // asked about on the way: a story that differs only in a seat nobody
  // asked about is handed the same answer (`explainOrRecall`).
  const {flips, restKey} = whoTurned(upto);
  const key = `${night}?${restKey}${hidden}`;
  let kept = memo.got.get(key);
  if (kept === undefined) memo.got.set(key, kept = []);
  for (const [theirs, reads, got] of kept)
    if (differOnlyUnasked(flips, theirs, reads)) {
      replayReads(reads);
      return got;
    }
  beginReads();
  let got, reads;
  try {
    got = theOnesThatCanWin(explainNight(world, state, night, died()));
  } finally {
    reads = endReads();
  }
  kept.push([flips, reads, got]);
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
// Sources a fallback of the plan may set aside whole. See solver.py.
const SET_ASIDE = ["Courtier", "Philosopher", "Preacher"];

/** Seats impaired tonight whatever the plan decides (13.10.2026). See
 * `_surely_impaired` in solver.py. */
function surelyImpaired(world, state, night) {
  const took = state.philosophies() || {};
  const out = new Set();
  for (const source of silencedOut(sourcesOn(world, state, night))) {
    if (!source.unavoidable() || RESTING.includes(source.name)
        || SET_ASIDE.includes(source.name)
        || (source.actor !== null && source.actor !== undefined
            && took[source.actor] !== undefined)) continue;
    for (const seat of source.seats) out.add(seat);
  }
  return out;
}

function nightAccounts(world, state, impairedAlready = {}, workingAlready = {}) {
  const deaths = nightDeaths(state);
  const nights = new Set([...Object.keys(deaths).map(Number),
                          ...state.quietNights]);
  if (!nights.size) return [{cost: 1.0, impaired: {}, working: {}}];

  let accounts = [{cost: 1.0, impaired: {}, working: {}, key: ""}];
  const done = [];
  for (const night of [...nights].sort((a, b) => a - b)) {
    const options = [];
    let sure = null;
    for (const opt of theOnesTheBoardAllows(
        night, explainedNight(world, state, night,
                              () => new Set(deaths[night] || [])),
        impairedAlready, workingAlready)) {
      let clash = false;
      for (const s of opt.impaired) if (opt.working.has(s)) clash = true;
      if (clash) continue;              // asked to be both at once
      if (opt.working.size) {
        if (sure === null) sure = surelyImpaired(world, state, night);
        let refused = false;
        for (const s of opt.working) if (sure.has(s)) refused = true;
        if (refused) continue;          // the plan would refuse it
      }
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
    const began = info.night > 1 ? `B${info.night - 1}` : "N0";
    const holder = info.player;
    if (world.roleAt(holder, began) !== source &&
        world.roleAt(holder, phase) !== source) continue;
    const again = {};
    for (const [night, seats] of Object.entries(failures))
      again[night] = new Set(seats);
    (again[info.night] = again[info.night] || new Set()).add(holder);
    // And a Philosopher that gained nothing has nothing of the character
    // it named to act with (13.10.2026). See solver.py.
    const mine = source === "Philosopher" ? [holder, info.role] : null;
    const other = planAsGiven(world, state, again, forbidden, [source], mine);
    if (other !== null) return other;
  }
  // And a Preacher that was off when it chose silenced nobody. See
  // solver.py.
  for (const info of state.infos) {
    if (info.type !== "PreacherChoice") continue;
    if (!hasAbility(world, state, info.player, "Preacher", `N${info.night}`))
      continue;
    const again = {};
    for (const [night, seats] of Object.entries(failures))
      again[night] = new Set(seats);
    (again[info.night] = again[info.night] || new Set()).add(info.player);
    const other = planAsGiven(world, state, again, forbidden, ["Preacher"]);
    if (other !== null) return other;
  }
  return null;
}

function planAsGiven(world, state, failures, forbidden, without = null,
                     mine = null) {
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
    if (mine) sources = sources.filter(
      src => src.actor !== mine[0] || src.name !== mine[1]);
    const got = planNightResting(sources,
                          [...wanted].sort((a, b) => a - b),
                          [...blocked].sort((a, b) => a - b), previous);
    if (got === null) return null;
    total *= got.cost;
    previous = {...previous, ...got.hits};
  }
  return total;
}

/** Who came back to life at this moment. */
function returnedAtPhase(state, phase) {
  const out = new Set();
  for (const [seat, phases] of Object.entries(state.resurrections || {}))
    if (phases.includes(phase)) out.add(Number(seat));
  return out;
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
    // A Zombuul on the board as dead stands all the same; of two living
    // Demons either wins (Hatter stage 2). See solver.py.
    const demons = world.demonsAt(phase);
    const up = demons.filter(d => !board.has(d)
      && world.roleAt(d, phase) === "Zombuul"
      && state.diedAt(d).filter(p => phaseIndex(p) < phaseIndex(phase))
        .length < 2);
    if ((up.length || demons.some(d => board.has(d)))
        && board.size + up.length <= 2)
      return false;                       // it would have won there and then
  }
  return true;
}

/** The good players worth trying as the faux paw: any seat a reading
 * looks at or the Lycanthrope could have hit, and one nobody looks at for
 * the rest. Good when the game began. See solver.py. */
function fauxPawCandidates(world, state) {
  const n = state.nPlayers;
  const good = [];
  for (let p = 0; p < n; p++) if (!world.evilAt(p, "N0")) good.push(p);
  if (!good.length) return [null];
  const looked = new Set();
  for (const info of state.infos) {
    if (["Chef", "Empath", "OracleInfo", "ShugenjaInfo"].includes(info.type))
      return good;
    // And the Bounty Hunter's evil player (Stelle 62). See solver.py.
    if (["SeamstressInfo", "Noble", "StewardInfo", "VillageIdiotInfo",
         "LycanthropeChose", "BountyHunterInfo"].includes(info.type))
      for (const field of ["a", "b", "c", "target"])
        if (Number.isInteger(info[field])) looked.add(info[field]);
  }
  for (const [seat, phase] of state.deathPhases())
    if (phase[0] === "N") looked.add(seat);
  const out = good.filter(p => looked.has(p));
  const rest = good.filter(p => !looked.has(p));
  return out.concat(rest.slice(0, 1));
}

/** Every [faux paw, Lleech host] worth trying, or null for neither. The
 * host is anybody who died, or -1 for somebody who never did. */
function hiddenChoices(world, state) {
  let faux = [null], host = [null];
  if ((inBag(state, "Lycanthrope") || takenByAPhilosopher(state, "Lycanthrope"))
      && (world.roles.includes("Lycanthrope")
          || takenByAPhilosopher(state, "Lycanthrope")))
    faux = fauxPawCandidates(world, state);
  if (inBag(state, "Lleech")) {
    const lleech = world.find("Lleech");
    if (lleech !== null) {
      const dead = new Set();
      for (const [seat] of state.deathPhases()) if (seat !== lleech) dead.add(seat);
      host = [...dead].sort((a, b) => a - b).concat([-1]);
    }
  }
  if (faux.length === 1 && faux[0] === null &&
      host.length === 1 && host[0] === null) return null;
  const out = [];
  for (const f of faux) for (const h of host) out.push([f, h]);
  return out;
}

/** The cost of one telling of this world, tried for each hidden choice it
 * leaves open — the faux paw, the Lleech's host — the best kept. */
function explainOne(world, state, outcome = null) {
  const choices = hiddenChoices(world, state);
  if (choices === null) {
    state._hidden = null;
    return explainOnce(world, state, outcome);
  }
  let best = null, bestMarks = null;
  for (const choice of choices) {
    state._hidden = choice;
    const marks = outcome ? {} : null;
    const cost = explainOnce(world, state, marks);
    if (cost !== null && (best === null || cost > best)) {
      best = cost; bestMarks = marks;
    }
  }
  state._hidden = null;
  if (outcome && bestMarks) Object.assign(outcome, bestMarks);
  return best;
}

/** The cost of one telling of this world, with the lineage settled. */
function explainOnce(world, state, outcome = null) {
  if (!theGameWentOn(world, state)) return null;
  // A night nothing at all explains settles it before any reading is
  // judged: the same answer, but a story that fails on its deaths has
  // then asked about nobody's side on the way. See solver.py.
  if (LISTENING) {
    const deaths = nightDeaths(state);
    const nights = new Set([...Object.keys(deaths).map(Number),
                            ...state.quietNights]);
    for (const night of [...nights].sort((a, b) => a - b))
      if (!explainedNight(world, state, night,
                          () => new Set(deaths[night] || [])).length)
        return null;
  }
  const sorted = plainFailures(world, state, outcome || {});
  if (sorted === null) return null;
  const {failures, ftInfos, invented, mustWork, vortoxOr, either} = sorted;

  // Every way the nights could have gone. Each brings its own demands on
  // who was impaired and who was working, so the plan is solved once per
  // account and the cheapest wins.
  const accounts = nightAccounts(world, state, failures, mustWork || {});
  if (!accounts.length) return null;

  const settle = (readings, extraWorking = {}) => {
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
      for (const [day, seats] of Object.entries(extraWorking)) {
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
  // excused: per night, the Vortox off or every source droisoned. And each
  // row that held only with somebody else impaired or working: that, or
  // its source off. Six choices at most are tried both ways; past that the
  // first.
  const nights = Object.keys(vortoxOr || {}).map(Number).sort((a, b) => a - b);
  const choices = [...nights.map(night => ({vortox: night})),
                   ...(either || []).map(row => ({row}))];
  const settleEither = readings => {
    if (!choices.length) return settle(readings);
    const k = Math.min(choices.length, 6);
    let best = null;
    for (let mask = 0; mask < (1 << k); mask++) {
      const trial = {}, working = {};
      for (const [n, seats] of Object.entries(readings))
        trial[n] = new Set(seats);
      choices.forEach((choice, i) => {
        // Bit clear means the first choice, which is tried first, as in
        // Python's `product((True, False))`.
        const first = i >= k || !((mask >> (k - 1 - i)) & 1);
        if (choice.row === undefined) {
          const night = choice.vortox;
          const {vortox, sources} = vortoxOr[night];
          trial[night] = trial[night] || new Set();
          if (first) trial[night].add(vortox);
          else for (const s of sources) trial[night].add(s);
        } else {
          const {night, source, impaired, working: needed} = choice.row;
          trial[night] = trial[night] || new Set();
          if (first) {
            for (const s of impaired) trial[night].add(s);
            working[night] = working[night] || new Set();
            for (const s of needed) working[night].add(s);
          } else for (const s of source) trial[night].add(s);
        }
      });
      const got = settle(trial, working);
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
  // Chosen at setup, among the good (22.10.2026). See solver.py.
  const dealt = dealtRoles(world);
  const herrings = [...asked].filter(p => !isEvil(dealt[p]));
  for (let p = 0; p < state.nPlayers; p++)
    if (!asked.has(p) && !isEvil(dealt[p])) { herrings.push(p); break; }

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
      else fits = info.holds(world, state, rh, source)
        || philosopherRecluses(world, state, `N${info.night}`).some(who =>
          info.holds(asRecluse(world, who), state, rh, source));
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
  // Whose side is asked about is only written down where a story can
  // differ in who turned evil (`explainOrRecall`).
  listenForSides(inBag(state, "BountyHunter") || inBag(state, "Mezepheles"));
  state._finalPhaseHeld = state._nightDeathsHeld = null;
  state._finalPhaseHeld = state.finalPhase();
  state._nightDeathsHeld = nightDeaths(state);
  try {
    return bestStoryNow(world, state, outcome);
  } finally {
    state._finalPhaseHeld = state._nightDeathsHeld = null;
  }
}

// Counted for the measurements: stories explained, recalled from one
// that differs only in who turned evil, and turns skipped.
export const STORIES = {explained: 0, recalled: 0, skipped: 0};

/** `explainOne`, unless a story told before settles this one: recalled
 * where the two differ only in seats whose side was never asked about,
 * skipped where a story that could not be explained gains a turn nobody
 * asked about. Neither changes an answer. See `_explain_or_recall` in
 * solver.py for the reasoning (11.10.2026, open item 52).
 * Returns [cost, marks, what was asked]. */
function explainOrRecall(world, changes, state, withMarks, toldBefore) {
  const {flips, turns, restKey} = whoTurned(changes);
  let before = toldBefore.get(restKey);
  if (!before) toldBefore.set(restKey, before = []);
  for (const [theirs, theirTurns, reads, cost, marks] of before) {
    if (theirTurns === turns) {
      if (differOnlyUnasked(flips, theirs, reads)) {
        STORIES.recalled += 1;
        return [cost, withMarks ? {...(marks || {})} : null, reads];
      }
    } else if (cost === null && theirTurns === "" && turns !== ""
               && turns.indexOf(";") === turns.length - 1
               && differOnlyUnasked(flips, theirs, reads)) {
      STORIES.skipped += 1;
      return [null, withMarks ? {} : null, reads];
    }
  }
  const marks = withMarks ? {} : null;
  const view = changes.length ? new Timeline(world, changes) : world;
  beginReads();
  let cost, reads;
  try { cost = explainOne(view, state, marks); } finally { reads = endReads(); }
  STORIES.explained += 1;
  before.push([flips, turns, reads, cost, marks]);
  return [cost, marks, reads];
}

function bestStoryNow(world, state, outcome) {
  if (inBag(state, "LilMonsta") && lilMonstaWorld(world))
    return bestBabysatStory(world, state, outcome);
  if (inBag(state, "Summoner") && summonerWorld(world))
    return bestSummonedStory(world, state, outcome);
  return bestStoryTold(world, state, outcome);
}

// Measured both ways on the gate. See solver.py.
export const SUMMON_PRUNE = {on: true};

/** The Summoner's Demon, told one way at a time (A, Weg 1, 21.10.2026):
 * every way that fits is kept for the report; a telling that failed
 * before anything from the summoning on was looked at fails for every
 * way. See `_best_summoned_story` in solver.py. */
function bestSummonedStory(world, state, outcome) {
  const options = summonOptions(world, state);
  if (!options.length) return {cost: null, changes: [], viable: []};
  let best = {cost: null, changes: [], marks: null};
  const viable = [];
  for (const fixed of options) {
    state._summoned = fixed;
    const reads = SUMMON_READS.now = {read: false};
    let got;
    try {
      const marks = outcome ? {} : null;
      got = {...bestStoryTold(world, state, marks), marks};
    } finally { state._summoned = null; SUMMON_READS.now = null; }
    viable.push(...got.viable);
    if (got.cost !== null && (best.cost === null || got.cost > best.cost))
      best = got;
    if (got.cost === null && SUMMON_PRUNE.on && !reads.read
        && fixed.some(c => c.summoned)) break;  // failed before it mattered
  }
  if (outcome && best.marks) Object.assign(outcome, best.marks);
  return {cost: best.cost, changes: best.changes, viable};
}

/** Lil' Monsta's babysitters, one a night: the stand-ins first, then one
 * night at a time with each of its other seats, keeping what explains
 * the board better, until nothing improves. See solver.py. */
function bestBabysatStory(world, state, outcome) {
  const options = babysitterOptions(world, state);
  if (!options.length || options.some(o => !o.length))
    return {cost: null, changes: [], viable: []};
  const tried = new Map();
  // Tellings that fitted nothing, with the nights they asked about; a
  // babysitter dead or on the gallows in its span is always asked about.
  // See solver.py.
  const failed = [];
  const marked = options.map((seats, night) => {
    const lo = phaseIndex(`N${night + 1}`), hi = phaseIndex(`D${night + 1}`);
    return new Set(seats.filter(p => state.executedOn(night + 1) === p
      || state.diedAt(p).some(at => {
        const i = phaseIndex(at);
        return lo <= i && i <= hi;
      })));
  });
  const tell = fixed => {
    const key = fixed.join(",");
    if (tried.has(key)) return tried.get(key);
    for (const [before, asked] of failed)
      if (fixed.every((seat, k) => (asked.has(k) ? seat === before[k]
                                                  : !marked[k].has(seat)))) {
        const none = {cost: null, changes: [], viable: [], marks: null};
        tried.set(key, none);
        return none;
      }
    state._babysitters = fixed;
    const reads = BABYSAT_READS.now = new Set();
    let got;
    try {
      const marks = outcome ? {} : null;
      const told = bestStoryTold(world, state, marks);
      got = {...told, marks};
    } finally { state._babysitters = null; BABYSAT_READS.now = null; }
    if (got.cost === null) {
      const asked = new Set();
      for (const at of reads)
        if (at[0] === "N") asked.add(parseInt(at.slice(1), 10) - 1);
      fixed.forEach((seat, k) => {
        if (k < marked.length && marked[k].has(seat)) asked.add(k);
      });
      failed.push([fixed, asked]);
    }
    tried.set(key, got);
    return got;
  };
  let fixed = options.map(o => o[0]);
  let best = tell(fixed);
  // Few enough to tell them all: then every one is (itertools.product's
  // order, the last night turning fastest).
  const size = options.reduce((n, o) => n * o.length, 1);
  let rest = options;
  if (size <= BABYSITTERS_TOLD_IN_FULL) {
    const at = options.map(() => 0);
    for (let i = 0; i < size; i++) {
      if (best.cost !== null && best.cost >= 1.0) break;
      const trial = at.map((j, night) => options[night][j]);
      const got = tell(trial);
      if (got.cost !== null && (best.cost === null || got.cost > best.cost)) {
        best = got; fixed = trial;
      }
      for (let night = at.length - 1; night >= 0; night--) {
        if (++at[night] < options[night].length) break;
        at[night] = 0;
      }
    }
    rest = [];                            // nothing left to try
  }
  // Where to start: the stand-ins, and — the Minions mostly keep it —
  // each seat babysitting every night it can.
  const seen = [];
  for (const o of rest) for (const p of o) if (!seen.includes(p)) seen.push(p);
  for (const seat of seen) {
    if (best.cost !== null && best.cost >= 1.0) break;
    const trial = rest.map(o => (o.includes(seat) ? seat : o[0]));
    const got = tell(trial);
    if (got.cost !== null && (best.cost === null || got.cost > best.cost)) {
      best = got; fixed = trial;
    }
  }
  // Nothing fitted yet: one night changed from any of the starts.
  if (best.cost === null) {
    for (const key of [...tried.keys()]) {
      const start = key.split(",").map(Number);
      for (let night = 0; night < rest.length; night++)
        for (const seat of rest[night]) {
          const trial = [...start];
          trial[night] = seat;
          const got = tell(trial);
          if (got.cost !== null && (best.cost === null || got.cost > best.cost)) {
            best = got; fixed = trial;
          }
        }
      if (best.cost !== null) break;
    }
  }
  for (let round = 0; round < 3; round++) {
    let better = false;
    for (let night = 0; night < rest.length; night++) {
      if (best.cost !== null && best.cost >= 1.0) break;
      for (const seat of rest[night]) {
        if (seat === fixed[night]) continue;
        const trial = [...fixed];
        trial[night] = seat;
        const got = tell(trial);
        if (got.cost !== null && (best.cost === null || got.cost > best.cost)) {
          best = got; fixed = trial; better = true;
        }
      }
    }
    if (!better) break;
  }
  const viable = [];
  for (const got of tried.values()) viable.push(...got.viable);
  if (outcome && best.marks) Object.assign(outcome, best.marks);
  return {cost: best.cost, changes: best.changes, viable};
}

function bestStoryTold(world, state, outcome) {
  const stories = possibleTimelines(world, state);
  if (!stories.length) return {cost: null, changes: [], viable: []};
  const turning = inBag(state, "Mezepheles");
  if (stories.length === 1 && !stories[0][0].length && !turning) {
    const cost = explainOne(world, state, outcome);
    return {cost, changes: [], viable: cost === null ? [] : [[cost, []]]};
  }

  let best = null, bestChanges = [], bestMarks = null;
  const viable = [];
  const toldBefore = new Map();
  // A tea party (22.10.2026): the stories where nobody chose anything new
  // go first, and one that could not be explained without looking at
  // anything from the earliest party on takes every choice made there
  // with it. See solver.py.
  let tea = null, order = stories;
  if (TEA_PRUNE.on && teaOnBoard(state)) {
    let at = null;
    for (const [got] of stories)
      for (const c of got)
        if (c.tea && (at === null || changeAt(c) < at)) at = changeAt(c);
    if (at !== null) {
      tea = {at, failed: new Set()};
      const has = (got, f) => got.some(f);
      // No party first, then a party with no summoning (stage 2).
      order = [...stories.filter(([got]) => !has(got, c => c.tea)),
               ...stories.filter(([got]) => has(got, c => c.tea)
                                 && !has(got, c => c.summoned)),
               ...stories.filter(([got]) => has(got, c => c.tea)
                                 && has(got, c => c.summoned))];
    }
  }
  // And a Summoner chosen at a party (Hatter stage 2): one that could not
  // be explained without looking at anything — sides too — from the
  // earliest summoning on takes every summoning sharing what came before
  // with it. See solver.py.
  let summ = null;
  if (SUMMON_TEA_PRUNE.on && tea && state.script.keys.includes("Summoner")) {
    let at = null;
    for (const [got] of stories)
      for (const c of got)
        if (c.summoned && (at === null || changeAt(c) < at)) at = changeAt(c);
    if (at !== null) summ = {at, failed: new Set()};
  }
  for (const [first, weight] of order) {
    let plain = null, before = null;
    if (tea) {
      const rest = first.filter(c => !c.tea);
      const key = rest.map(changeKey).join(";");
      if (rest.length !== first.length) {
        if (tea.failed.has(key)) { STORIES.skipped += 1; continue; }
        if (summ) {
          before = first.filter(c => changeAt(c) < summ.at)
            .map(changeKey).join(";");
          if (summ.failed.has(before)) { STORIES.skipped += 1; continue; }
        }
        TEA.told += 1;
      } else {
        plain = key;
      }
    }
    const watching = () => (plain !== null
      ? {at: tea.at, read: false} : {at: summ.at, read: false, sides: true});
    const fail = () => (plain !== null ? tea.failed.add(plain)
      : summ.failed.add(before));
    if (!LISTENING) {                     // nobody turns evil that way here
      const view = first.length ? new Timeline(world, first) : world;
      const marks = outcome ? {} : null;
      const watch = plain !== null || before !== null;
      if (watch) TEA_READS.now = watching();
      let cost;
      try {
        cost = explainOne(view, state, marks);
      } finally {
        if (watch) {
          if (cost === null && !TEA_READS.now.read) fail();
          TEA_READS.now = null;
        }
      }
      if (cost === null) continue;
      const got = cost * weight;
      viable.push([got, first]);
      if (best === null || got > best) {
        best = got; bestChanges = first; bestMarks = marks;
      }
      continue;
    }
    const told = [first];
    for (let at = 0; at < told.length;) {
      const changes = told[at++];
      const watch = (plain !== null || before !== null) && at === 1;
      const fresh = STORIES.explained;
      if (watch) TEA_READS.now = watching();
      let cost, marks, asked;
      try {
        [cost, marks, asked] = explainOrRecall(
          world, changes, state, !!outcome, toldBefore);
      } finally {
        if (watch) {
          // Only a story really told here says what it looked at.
          if (cost === null && !TEA_READS.now.read
              && STORIES.explained > fresh) fail();
          TEA_READS.now = null;
        }
      }
      // A story that leaves something to pay for, or does not fit at
      // all, is told again with each player a Mezepheles could have
      // turned (`aMezephelesMayHaveTurned`).
      if (turning && at === 1 && (cost === null || cost < 1.0)) {
        const view = changes.length ? new Timeline(world, changes) : world;
        for (const turn of aMezephelesMayHaveTurned(view, state)) {
          // Not if the story could not be explained and never asked
          // about that player's side from that night on: the second
          // shortcut of `explainOrRecall`, taken before the story is
          // even put together.
          if (cost === null) {
            const bits = asked.get(turn[0].seat) || 0;
            const from = momentOf(turn[0]) + 2;
            if (!bits || (bits !== -1 && from <= 30 && !(bits >>> from))) {
              STORIES.skipped += 1;
              continue;
            }
          }
          told.push([...changes, ...turn]);
        }
      }
      if (cost === null) continue;
      const got = cost * weight;
      viable.push([got, changes]);
      if (best === null || got > best) {
        best = got; bestChanges = changes; bestMarks = marks;
      }
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
  if (state && viable.length > 1 && barberOnBoard(state) &&
      barberClaimants(state).size)
    viable = viable.map(([cost, changes]) =>
      [cost * barberShare(world, changes, state), changes]);
  // A Summoner chosen at a tea party is one choice, however many ways it
  // then summoned (Hatter stage 2). See solver.py.
  if (state && viable.length > 1 && teaOnBoard(state)
      && state.script.keys.includes("Summoner"))
    viable = viable.map(([cost, changes]) =>
      [cost * summonShare(world, changes, state), changes]);
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
  // Asked at the Barber's turn, as the stories were told. See solver.py.
  for (const [extra] of offersOf(barberRule, view, state)) {
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
    // At least one of its kind, its own: counted over a view with the
    // later rules' work in it the pairs may come out as another kind, and
    // this divided by nought (11.10.2026). See solver.py.
    const among = Math.max(1, ours ? nOurs : nOther);
    factor *= PRIORS.BARBER_SWAP_SHARE * part / among /
              (ours ? 1.0 : BARBER_SWAP_PENALTY);
  }
  return factor;
}

/** How much explaining this world needs, as a multiplier, or null. */
export const explanationCost = (world, state) => bestStory(world, state).cost;

export const worldConsistent = (world, state) =>
  explanationCost(world, state) !== null;
