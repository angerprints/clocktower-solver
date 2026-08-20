// Weighing worlds, and turning a pile of them into a picture of the table.
//
// Worlds are not counted equally. Two things change a world's weight
// before any explaining is priced: a good player who lied, which is rare
// enough to push those worlds far down, and your own social read, which
// multiplies the odds a seat is evil without ever forcing anything.

import {CHARACTERS} from "./catalogue.mjs";
import {explainNight} from "./deaths.mjs";
import {TEAM, believesAnother, isEvil, show, wakeFits} from "./roles.mjs";
import {bestStory, explanationCost, forcedRoles, nightDeaths,
        worldConsistent} from "./scoring.mjs";
import {PRIORS} from "./priors.mjs";
import {Rng} from "./rng.mjs";
import {Timeline, eachWorld, sampleWorlds} from "./worlds.mjs";

// The tunable priors live in `priors.mjs` and are read from there at the
// moment they are used, so the guesswork sweep can move one and see what
// happens. Re-exported here because that is where they were, and because
// naming them at the point of use reads better than PRIORS.THIS every
// time.

// Above this, sample rather than walk every world.
export const EXACT_LIMIT = 40_000;
// The hard ceiling on enumeration, and much higher. Keeping the two apart
// matters: using one as the other made `solve` quietly return a truncated
// world set, which is worse than sampling — no margins, no warning worth
// the name, and no way to tell which worlds were dropped.
export const DEFAULT_MAX_WORLDS = 300_000;

// A floor rather than a threshold. Waiting until an executed seat looked
// like the Demon with any confidence fired on nothing: the town executing
// the actual Demon is rare enough that even with every other seat vouched
// for, the figure came to about eight percent.
export const MASTERMIND_HINT = 0.02;

/** Is this character on the grimoire at all?
 *
 * A Drunk's token counts: the Storyteller put it on the board, so the
 * Demon was never offered it as a bluff.
 */
export const inPlay = (world, role) =>
  world.roles.includes(role) || world.believes.includes(role);

/** Weight kept by a world in which an early night victim is evil.
 *
 * Counted from night two, the first night anybody can die.
 */
export const nightDeathFactor = night =>
  Math.min(1.0, PRIORS.NIGHT_DEATH_EVIL_PENALTY * Math.max(night - 1, 1));

/** Is this seat saying something they know to be false in this world?
 *
 * Covers both kinds of claim: the character they named, and anything
 * softer they said about waking. Somebody handed the wrong token is not
 * lying either way — they believe it, and they are woken on its schedule.
 * That holds however evil the character underneath turns out to be: a
 * Marionette believes what it says as sincerely as the Drunk does.
 */
export function isLying(world, state, p) {
  const role = world.roles[p];
  const believed = world.believes[p];
  const claim = state.claims[p];
  if (claim && !(role === claim ||
                 (believesAnother(role) && believed === claim))) return true;
  const said = (state.wakes || {})[p];
  return !!(said && !wakeFits(role, believed, said));
}

/** Everything that makes a world plausible except the poison story. */
/** What the table's confirmations are worth to a world.
 *
 * A reading the players later agreed was *right* is evidence that its
 * source really is that character. It multiplies rather than settling
 * anything: four confirmed rows from one seat compound, and no pile of
 * them reaches certainty, because a Spy reading the grimoire can feed a
 * Minion true information all game.
 */
export function confirmedBoost(world, state) {
  let got = 1.0;
  for (const info of state.infos) {
    if (!info.confirmed) continue;
    const seat = info.sourceSeat(state);
    if (seat === null || seat === undefined) continue;
    const source = info.sourceRole;
    if (source && world.roleAt(seat, `N${info.night}`) === source)
      got *= PRIORS.CONFIRMED_READING_STEP;
  }
  return got;
}

export function priorWeight(world, state) {
  let w = confirmedBoost(world, state);
  const reads = state.reads || {};
  const suspects = state.suspects || {};

  const bluffs = {};
  for (let p = 0; p < state.nPlayers; p++) {
    if (isEvil(world.roles[p]) && isLying(world, state, p)) {
      const claimed = state.claims[p];
      if (claimed) bluffs[claimed] = (bluffs[claimed] || 0) + 1;
    }
  }

  for (let p = 0; p < state.nPlayers; p++) {
    const evil = isEvil(world.roles[p]);
    if (isLying(world, state, p)) {
      if (!evil) {
        w *= TEAM[world.roles[p]] === "outsider" ? PRIORS.OUTSIDER_HIDING_PENALTY
                                                 : PRIORS.TOWNSFOLK_LIE_PENALTY;
      } else {
        const claim = state.claims[p];
        if (claim && (inPlay(world, claim) || (bluffs[claim] || 0) > 1))
          w *= PRIORS.BLUFF_COLLISION_PENALTY;
      }
    }
    const step = reads[p] || 0;
    if (step && evil) w *= Math.pow(PRIORS.READ_ODDS_STEP, step);
    if (suspects[p] && believesAnother(world.roles[p]))
      w *= PRIORS.DRUNK_SUSPICION_STEP;
  }

  for (const [p, phase] of state.deathPhases()) {
    if (!phase || phase[0].toUpperCase() !== "N") continue;  // executions say
    if (isEvil(world.roles[p]))                              // nothing alone
      w *= nightDeathFactor(parseInt(phase.slice(1), 10));
  }
  return w;
}

export function worldWeight(world, state) {
  const cost = explanationCost(world, state);
  return cost === null ? 0.0 : priorWeight(world, state) * cost;
}

/** How the search should be set up for this board. */
const searchOptions = (state, allowGoodLies) => ({
  certainties: state.certainties,
  allowGoodLies,
  forced: forcedRoles(state),
  wakes: state.wakes,
  script: state.script,
  fabled: state.fabled,
});

/** Every legal world, and the ones that survive. */
export function solve(state, allowGoodLies = false,
                      maxWorlds = DEFAULT_MAX_WORLDS) {
  const all = [];
  eachWorld(state.nPlayers, state.claims,
            searchOptions(state, allowGoodLies), world => {
    all.push(world);
    return all.length < maxWorlds;
  });
  const valid = all.filter(w => worldConsistent(w, state));
  return {all, valid};
}

/** A weight as a percentage, kept inside nought and a hundred.
 *
 * Adding a few thousand floats and dividing lands on 100.00000000000001
 * often enough to matter, and a figure over a hundred is the kind of
 * thing somebody reasonably stops trusting the rest of the answer over.
 */
const share = (value, denom) =>
  Math.min(100.0, Math.max(0.0, 100 * value / denom));

/** Weighted per-seat picture. Percentages are shares of total weight. */
export function summarize(valid, state) {
  const n = state.nPlayers;
  const weights = valid.map(w => worldWeight(w, state));
  const total = weights.reduce((a, b) => a + b, 0) || 1.0;

  const rows = [];
  for (let p = 0; p < n; p++) {
    let evil = 0, demon = 0, drunk = 0, lying = 0;
    const roles = {};
    valid.forEach((w, i) => {
      const wt = weights[i];
      const role = w.roles[p];
      roles[role] = (roles[role] || 0) + wt;
      if (isEvil(role)) evil += wt;
      if (TEAM[role] === "demon") demon += wt;
      if (believesAnother(role)) drunk += wt;
      if (isLying(w, state, p)) lying += wt;
    });
    rows.push({
      player: p,
      claim: state.claims[p] ?? null,
      evil_pct: share(evil, total),
      demon_pct: share(demon, total),
      drunk_pct: share(drunk, total),
      lying_pct: share(lying, total),
      roles: Object.entries(roles)
        .map(([r, v]) => [r, share(v, total)])
        .sort((a, b) => b[1] - a[1]),
    });
  }
  return rows;
}

/** Blame counts turned into shares. */
function shareOut(blame) {
  const out = {};
  for (const [night, seats] of Object.entries(blame)) {
    out[night] = {};
    for (const [seat, causes] of Object.entries(seats)) {
      const sum = Object.values(causes).reduce((a, b) => a + b, 0) || 1.0;
      out[night][seat] = Object.fromEntries(
        Object.entries(causes).map(([k, v]) => [k, v / sum]));
    }
  }
  return out;
}

/** What became of each reading, as shares of the weight. */
function readingsFrom(state, told) {
  return state.infos.map((info, idx) => {
    const weight = Object.values(told[idx]).reduce((a, b) => a + b, 0);
    return {
      index: idx, type: info.type, night: info.night, player: info.player,
      shares: weight > 0
        ? Object.fromEntries(Object.entries(told[idx])
            .map(([mark, v]) => [mark, v / weight]))
        : {},
    };
  });
}

/** Add one world's account of each night death to the running totals. */
function tallyBlame(into, view, state, weight) {
  for (const [nightKey, victims] of Object.entries(nightDeaths(state))) {
    const night = Number(nightKey);
    const accounts = explainNight(view, state, night, new Set(victims), true);
    const total = accounts.reduce((a, b) => a + b.cost, 0);
    if (total <= 0) continue;
    for (const acc of accounts) {
      const slice = weight * acc.cost / total;
      for (const [seat, cause] of Object.entries(acc.who)) {
        into[night] = into[night] || {};
        into[night][seat] = into[night][seat] || {};
        into[night][seat][cause] = (into[night][seat][cause] || 0) + slice;
      }
    }
  }
}

/** Score every legal world.
 *
 * Nothing is stored per world except running sums and a handful of the
 * most plausible examples, so this is limited by time rather than memory.
 *
 * Blame and the Mastermind hint are worked out in the same pass, because
 * each used to walk every world again and that trebled the cost.
 */
/** Roughly how far off a sampled percentage could be, in points.
 *
 * Two standard errors of a proportion, using the effective sample size
 * rather than the number of walks — importance weighting means a thousand
 * uneven samples can carry the weight of a hundred even ones, and
 * pretending otherwise would overstate the precision.
 */
export function margin(pct, ess) {
  if (ess === null || ess === undefined) return 0.0;
  if (ess <= 1) return 50.0;
  const p = Math.min(Math.max(pct / 100.0, 0.0), 1.0);
  return 100 * 2 * Math.sqrt(Math.max(p * (1 - p), 1e-9) / ess);
}

/** A rough count of how many legal worlds are out there.
 *
 * A few hundred random walks tell a search worth walking in full from one
 * that is hopeless, and they cost a fraction of a second — much better
 * than discovering it half a million worlds in.
 */
export function pilotSize(state, allowGoodLies = false, walks = 1500,
                          rng = null) {
  let total = 0.0, walked = 0;
  sampleWorlds(state.nPlayers, state.claims, {
    ...searchOptions(state, allowGoodLies),
    dives: walks, rng: rng || new Rng(0),
  }, (_world, standsFor) => { walked += 1; total += standsFor; });
  return walked ? total / walked : 0.0;
}

/** Probabilities from random walks instead of an exhaustive count.
 *
 * Each walk picks among whatever is open at every seat, so a world found
 * down a path stands for the product of how many ways there were to get
 * there. Carrying that weight is what makes the answer an estimate of the
 * real distribution rather than of whichever corner of the search the
 * walk happened to like.
 */
export function estimate(state, allowGoodLies = false, dives = 25000,
                         keepSamples = 8, rng = null) {
  const n = state.nPlayers;
  const now = state.finalPhase();
  rng = rng || new Rng((Math.random() * 2 ** 32) >>> 0);

  let total = 0.0, sq = 0.0, legalSum = 0.0, validSum = 0.0, walked = 0;
  const best = [];
  const blame = {};
  const told = state.infos.map(() => ({}));
  const perSeat = Array.from({length: n}, () => ({
    evil: 0, demon: 0, drunk: 0, lying: 0, roles: {},
  }));

  sampleWorlds(n, state.claims, {
    ...searchOptions(state, allowGoodLies), dives, rng,
  }, (world, standsFor) => {
    walked += 1;
    if (world === null) return;           // a dead end still counts as a walk
    legalSum += standsFor;

    const outcome = {};
    const {cost, changes} = bestStory(world, state, outcome);
    if (cost === null) return;
    const view = changes.length ? new Timeline(world, changes) : world;
    validSum += standsFor;

    const wt = standsFor * priorWeight(world, state) * cost;
    total += wt;
    sq += wt * wt;
    for (const [idx, mark] of Object.entries(outcome))
      told[idx][mark] = (told[idx][mark] || 0) + wt;

    const demon = view.demonAt(now);
    for (let p = 0; p < n; p++) {
      const seat = perSeat[p];
      const role = view.roleAt(p, now);
      seat.roles[role] = (seat.roles[role] || 0) + wt;
      if (view.evilAt(p, now)) seat.evil += wt;
      if (p === demon) seat.demon += wt;
      if (believesAnother(role)) seat.drunk += wt;
      if (isLying(world, state, p)) seat.lying += wt;
    }
    tallyBlame(blame, view, state, wt);

    if (best.length < keepSamples) {
      best.push([wt, world]);
      best.sort((a, b) => a[0] - b[0]);
    } else if (wt > best[0][0]) {
      best[0] = [wt, world];
      best.sort((a, b) => a[0] - b[0]);
    }
  });

  const ess = sq > 0 ? (total * total) / sq : 0.0;
  const denom = total > 0 ? total : 1.0;
  const rows = perSeat.map((seat, p) => {
    const evilPct = share(seat.evil, denom);
    return {
      player: p,
      claim: state.claims[p] ?? null,
      evil_pct: evilPct,
      demon_pct: share(seat.demon, denom),
      drunk_pct: share(seat.drunk, denom),
      lying_pct: share(seat.lying, denom),
      roles: Object.entries(seat.roles).map(([r, v]) => [r, share(v, denom)])
        .sort((a, b) => b[1] - a[1]),
      margin: margin(evilPct, ess),
    };
  });

  best.sort((a, b) => b[0] - a[0]);
  return {
    legal: walked ? Math.round(legalSum / walked) : 0,
    valid: walked ? Math.round(validSum / walked) : 0,
    truncated: false, sampled: true, dives: walked, ess,
    rows, samples: best.map(([, w]) => w),
    blame: shareOut(blame), mastermind: [],
    readings: readingsFrom(state, told),
  };
}

export function analyze(state, allowGoodLies = false,
                        maxWorlds = EXACT_LIMIT, keepSamples = 8,
                        dives = 25000, rng = null) {
  // A few hundred walks say whether walking the whole thing is feasible,
  // which is much better than finding out half a million worlds in.
  if (pilotSize(state, allowGoodLies) > maxWorlds)
    return estimate(state, allowGoodLies, dives, keepSamples, rng);
  const n = state.nPlayers;
  const now = state.finalPhase();
  let legal = 0, valid = 0, total = 0.0, truncated = false;
  const best = [];
  const blame = {};

  const executed = Object.entries(state.executions || {})
    .map(([day, seat]) => [Number(day), seat])
    .filter(([day, seat]) => state.executionDeath(day) === seat)
    .sort((a, b) => a[0] - b[0]);
  const hanged = {};
  for (const [, seat] of executed) hanged[seat] = 0.0;

  // What became of each reading, weighed across every surviving world.
  // Worked out in the same pass, because the story that settles a world's
  // cost is the same story that says which rows held.
  const told = state.infos.map(() => ({}));

  const perSeat = Array.from({length: n}, () => ({
    evil: 0, demon: 0, drunk: 0, lying: 0, roles: {},
  }));

  eachWorld(n, state.claims, searchOptions(state, allowGoodLies), world => {
    legal += 1;
    if (legal > maxWorlds) {
      // Too big to walk. Stop, and throw the partial count away — it is
      // the first corner of the tree and nothing like a fair sample.
      truncated = true;
      return false;
    }
    const outcome = {};
    const {cost, changes} = bestStory(world, state, outcome);
    if (cost === null) return true;
    const view = changes.length ? new Timeline(world, changes) : world;

    valid += 1;
    const wt = priorWeight(world, state) * cost;
    total += wt;
    for (const [idx, mark] of Object.entries(outcome))
      told[idx][mark] = (told[idx][mark] || 0) + wt;

    // Character and side are read from the *timeline* at the moment the
    // game has reached, because after a handover the useful answer to
    // "who is the Demon" is who holds it now, not who was dealt it.
    // Lying is read from the deal, since a claim is about the whole game.
    const demon = view.demonAt(now);
    for (let p = 0; p < n; p++) {
      const seat = perSeat[p];
      const role = view.roleAt(p, now);
      seat.roles[role] = (seat.roles[role] || 0) + wt;
      if (view.evilAt(p, now)) seat.evil += wt;
      if (p === demon) seat.demon += wt;
      if (believesAnother(role)) seat.drunk += wt;
      if (isLying(world, state, p)) seat.lying += wt;
    }
    tallyBlame(blame, view, state, wt);
    for (const [day, seat] of executed)
      if (view.demonAt(`D${day}`) === seat) hanged[seat] += wt;

    if (best.length < keepSamples) {
      best.push([wt, world]);
      best.sort((a, b) => a[0] - b[0]);
    } else if (wt > best[0][0]) {
      best[0] = [wt, world];
      best.sort((a, b) => a[0] - b[0]);
    }
    return true;
  });

  const denom = total > 0 ? total : 1.0;
  const rows = perSeat.map((seat, p) => ({
    player: p,
    claim: state.claims[p] ?? null,
    evil_pct: share(seat.evil, denom),
    demon_pct: share(seat.demon, denom),
    drunk_pct: share(seat.drunk, denom),
    lying_pct: share(seat.lying, denom),
    roles: Object.entries(seat.roles).map(([r, v]) => [r, share(v, denom)])
      .sort((a, b) => b[1] - a[1]),
    margin: 0.0,
  }));

  if (truncated) return estimate(state, allowGoodLies, dives, keepSamples, rng);

  const shares = shareOut(blame);

  const hints = [];
  if (state.script.keys.includes("Mastermind") && total > 0)
    for (const [day, seat] of executed) {
      const odds = hanged[seat] / total;
      if (odds >= MASTERMIND_HINT)
        hints.push({day: day + 1, seat,
                    demon_pct: Math.round(1000 * odds) / 10});
    }

  const readings = readingsFrom(state, told);

  best.sort((a, b) => b[0] - a[0]);
  return {
    legal, valid, truncated, sampled: false, dives: 0, ess: null,
    rows, samples: best.map(([, w]) => w), blame: shares, mastermind: hints,
    readings,
  };
}

export {show};
