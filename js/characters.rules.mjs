// What each character actually does, registered into the registries.
//
// One rule per character, each answering a narrow question about a
// moment: can this kill tonight, can this seat be killed that way, could
// this have stopped somebody working. Nothing here decides that anything
// *happened* — the scoring does that, by asking these what was possible
// and paying for whichever story is cheapest.
//
// Adding a character is an entry in the catalogue and a rule here.

import {CHARACTERS} from "./catalogue.mjs";
import {DEMON, OTHER, PICKED, Cause, causeRule, immunityRule, implication,
        implicationRule, shield} from "./deaths.mjs";
import {ORGAN_GRINDER_BY_CHOICE, Source, makePoisonerRule, minionStillActs,
        sourceRule, sourcesOn} from "./impairment.mjs";
import {PRIORS} from "./priors.mjs";
import {phaseIndex} from "./phases.mjs";

// --------------------------------------------------------------------
// Constants. Every one is a judgement rather than a fact, which is what
// the sensitivity pass exists to make visible.
// --------------------------------------------------------------------

// The tunable prices live in `priors.mjs`, read at the moment they are
// used so the guesswork sweep can move one.

/** Is this character on the script at all?
 *
 * Every rule asks first. A Trouble Brewing board should not pay for
 * scanning the table for a Sailor on every night of every world.
 */
export function inBag(state, key) {
  if (!state._bagCache) state._bagCache = new Set(state.script.keys);
  return state._bagCache.has(key);
}

// One set per board: every Demon's kill and every Sweetheart asks for it
// on every night of every story. Nobody changes it.
const allSeats = state => state._allSeats ||
  (state._allSeats = new Set(Array.from({length: state.nPlayers}, (_, i) => i)));

/** The seat holding this character, if it is standing tonight. */
function acting(world, state, key, night) {
  const phase = `N${night}`;
  const seat = world.findAt(key, phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return null;
  return seat;
}

/** Who came back to life at this moment. */
/** Did this seat die after night `since` began and before `night` did?
 *
 * The lifetime of an ability: whatever a character set going on night
 * `since` is over by `night` if it has been dead in between, whether or
 * not it is standing again. */
function diedBetween(state, seat, since, night) {
  const from = phaseIndex(`N${since}`), to = phaseIndex(`N${night}`);
  return state.diedAt(seat).some(at => {
    const i = phaseIndex(at);
    return from <= i && i < to;
  });
}

function returnedAt(state, phase) {
  const out = new Set();
  for (const [seat, phases] of Object.entries(state.resurrections || {}))
    if (phases.includes(phase)) out.add(Number(seat));
  return out;
}

/** Who was alive at this moment — which, on a night somebody came back,
 * has two answers.
 *
 * A return is dated to a night, and a night is seventy-odd slots long. A
 * Shabaloth regurgitates just before it chooses; a Professor raises at
 * 43, after every Demon has been and gone. So whoever came back tonight
 * was dead for the first part of it and alive for the rest, and nothing
 * on the board says where the line fell. Anything that depends on who was
 * standing has to hold both ways before it may be demanded. */
function rosters(state, phase) {
  const alive = state.aliveSet(phase);
  const back = returnedAt(state, phase);
  if (!back.size) return [alive];
  return [alive, new Set([...alive].filter(seat => !back.has(seat)))];
}

const anyDiedAt = (state, phase) =>
  Object.keys(state.deaths || {}).some(who => state.diedAt(who).includes(phase));

/** The board as it stood when this night began — Python's `_before`. */
const beganAt = night => (night > 1 ? `E${night - 1}` : "N0");

/** What a declared choice named on this night, if it was recorded.
 *
 * Null when nothing was written down — which is not the same as an empty
 * answer: it means "nobody said", and the rule falls back to reaching
 * everybody rather than reaching nobody.
 */
function chosen(state, role, night, fields = ["target"], by = null) {
  // `by` is the seat that really holds the character in this world. A row
  // from anybody else is a bluff's story, and what the real one chose is
  // then as unrecorded as if nobody had spoken.
  for (const info of state.infos) {
    if (info.sourceRole !== role || info.night !== night) continue;
    if (by !== null && info.player !== by) continue;
    const got = fields.map(f => info[f])
                      .filter(v => v !== undefined && v !== null);
    if (got.length) return new Set(got);
  }
  return null;
}

/** The nearest Townsfolk each way round the circle.
 *
 * By *team*, not by side: a Townsfolk can be evil, and this skips
 * Outsiders and Minions rather than skipping the evil. The dead are not
 * skipped either — a dead Townsfolk is still the nearest one.
 */
function nearestTownsfolk(world, state, seat, phase) {
  const n = state.nPlayers;
  const out = new Set();
  for (const step of [1, -1])
    for (let gap = 1; gap < n; gap++) {
      const other = (seat + step * gap + n * n) % n;
      if (other === seat) break;
      if (world.teamAt(other, phase) === "townsfolk") { out.add(other); break; }
    }
  return out;
}

/** Whoever became the Snake Charmer by the swap, from then on.
 *
 * The new Demon is untouched; it is the *new Snake Charmer* — the old
 * Demon — that is poisoned, and permanently. Free, because nothing had
 * to go right for it.
 */
sourceRule(function aSwappedSnakeCharmerIsPoisonedForGood(world, state, night) {
  if (!inBag(state, "SnakeCharmer")) return [];
  const out = [];
  for (const info of state.infos) {
    if (info.sourceRole !== "SnakeCharmer" || !info.swapped) continue;
    // From the day after the swap, which is when it took effect.
    if (phaseIndex(`N${night}`) < phaseIndex(`D${info.night}`)) continue;
    // The old Demon it pointed at, not the first Snake Charmer found.
    // The player stays poisoned whatever they hold later, in a story where
    // the swap happened. See solver.py.
    const seat = info.target;
    if (!(world.changes || []).some(c => c.seat === seat &&
        c.role === "SnakeCharmer" && c.phase === `N${info.night}`)) continue;
    out.push(new Source("Snake Charmer", new Set([seat]),
                        {capacity: 1, cost: 1.0, repeatCost: 1.0}));
  }
  return out;
});

/** Its two nearest Townsfolk, all game.
 *
 * Nothing is chosen and nothing is lucky, so this costs nothing. It
 * moves as the table changes shape, and stops the moment the No Dashii
 * does.
 */
sourceRule(function aNoDashiiPoisonsItsTownsfolkNeighbours(world, state, night) {
  if (!inBag(state, "NoDashii")) return [];
  const phase = `N${night}`;
  const seat = world.findAt("NoDashii", phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return [];
  const hit = nearestTownsfolk(world, state, seat, phase);
  const out = [];
  if (hit.size)
    out.push(new Source("No Dashii", hit,
                        {capacity: hit.size, cost: 1.0, repeatCost: 1.0}));
  // Whoever was beside it as the night began, and no longer is: "the
  // players who are poisoned may change immediately". On a night a
  // Pit-Hag turns its Townsfolk neighbour into something else, that
  // neighbour was poisoned for the part of the night before it happened.
  // On offer, not forced.
  const began = beganAt(night);
  const then = world.findAt("NoDashii", began);
  if (then !== null) {
    const earlier = new Set([...nearestTownsfolk(world, state, then, began)]
      .filter(p => !hit.has(p)));
    if (earlier.size)
      out.push(new Source("No Dashii, as the night began", earlier,
                          {capacity: earlier.size, cost: () => 1.0,
                           repeatCost: () => 1.0}));
  }
  return out;
});

/** Every Minion it killed keeps its ability and drunks a neighbour.
 *
 * A Townsfolk beside the dead Minion, and the Storyteller chooses which
 * — so the reach is both neighbours and the capacity is one per corpse.
 * Stops when the Vigormortis does.
 */
sourceRule(function aVigormortisPoisonsBesideItsDeadMinions(world, state, night) {
  if (!inBag(state, "Vigormortis")) return [];
  const phase = `N${night}`;
  const seat = world.findAt("Vigormortis", phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return [];
  const out = [];
  for (let who = 0; who < state.nPlayers; who++) {
    if (world.teamAt(who, phase) !== "minion") continue;
    const gone = state.diedAt(who);
    if (!gone.length) continue;
    const first = gone.reduce((a, b) => phaseIndex(a) <= phaseIndex(b) ? a : b);
    if (phaseIndex(first) > phaseIndex(phase)) continue;
    // Only a Minion it killed: at night, with a Vigormortis as the Demon.
    if (first[0].toUpperCase() !== "N") continue;
    const killer = world.demonAt(first);
    if (killer === null || world.roleAt(killer, first) !== "Vigormortis")
      continue;
    const beside = nearestTownsfolk(world, state, who, phase);
    if (beside.size)
      out.push(new Source("Vigormortis", beside,
                          {capacity: 1, cost: 1.0, repeatCost: 1.0}));
  }
  return out;
});

/** Taking an ability drunks whoever already had it.
 *
 * Only while the Philosopher lives — unlike the Sweetheart, this one
 * switches off again. And only when somebody actually holds the chosen
 * character: it may take one nobody has, and then it drunks nobody.
 */
sourceRule(function aPhilosopherDrunksWhoeverHadIt(world, state, night) {
  if (!inBag(state, "Philosopher")) return [];
  const phase = `N${night}`;
  const out = [];
  for (const [who, [taken, since]]
       of Object.entries(state.philosophies())) {
    const seat = Number(who);
    if (phaseIndex(phase) < phaseIndex(since)) continue;
    if (!state.aliveSet(phase).has(seat)) continue;   // it stops with them
    // The span in which it stops being the Philosopher, or dies, is half
    // and half: whoever it drunk is drunk until that moment and sober
    // after it. There the drunkenness is on offer rather than forced, and
    // it is read off the board as the night began.
    const began = beganAt(night);
    const still = world.roleAt(seat, phase) === "Philosopher";
    if (!still && world.roleAt(seat, began) !== "Philosopher") continue;
    const died = state.diedAt(seat);
    const went = !still || died.includes(phase) || died.includes(`D${night}`);
    const had = world.findAt(taken, still ? phase : began);
    if (had === null || had === seat) continue;
    const free = went ? () => 1.0 : 1.0;
    out.push(new Source("Philosopher", new Set([had]),
                        {capacity: 1, cost: free, repeatCost: free}));
  }
  return out;
});

/** A Pukka poisons on one night and that poison kills on the next.
 *
 * The kill rule already demands the victim was poisoned the night before
 * and nothing provided that poison, so **every Pukka board was
 * impossible**. It went unnoticed because a board is only impossible
 * once a death is recorded on the right night, and no test or corpus
 * board had one.
 *
 * Two tokens can matter on one night, and they are priced differently.
 *
 * The one it places tonight: whoever goes on to die tomorrow night was
 * certainly the one it chose, so that costs nothing — the Pukka poisons
 * somebody every night and the body says who. This charged the
 * Poisoner's price for it, so every Pukka kill cost its world 0.35 and
 * the true world of a Pukka game weighed a fifth of any other Demon's
 * (02.10.2026). Anybody else is a guess and priced like one.
 *
 * The one it placed last night: that player stays poisoned until the
 * Pukka's turn comes round again, so a Sailor, a Fool or an Innkeeper
 * that dies tonight was still poisoned as the night began. Free for the
 * same reason, and it reaches only tonight's dead.
 *
 * Neither is forced on anybody: a seat that acted before the Pukka on
 * the night it was chosen was still sober when it did.
 */
function diedOn(state, night) {
  const phase = `N${night}`, out = new Set();
  for (const seat of Object.keys(state.deaths || {}))
    if (state.diedAt(+seat).includes(phase)) out.add(+seat);
  return out;
}

sourceRule(function aPukkaPoisonsWhoeverItWillKill(world, state, night) {
  if (!inBag(state, "Pukka")) return [];
  const phase = `N${night}`;
  const seat = world.findAt("Pukka", phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return [];
  const alive = state.aliveSet(phase);
  const dueTomorrow = diedOn(state, night + 1);
  const out = [new Source("Pukka", alive, {
    capacity: 1,
    cost: who => (dueTomorrow.has(who) ? 1.0 : PRIORS.POISON_HIT_PENALTY),
    repeatCost: who =>
      (dueTomorrow.has(who) ? 1.0 : PRIORS.POISON_REPEAT_PENALTY),
  })];
  const dueTonight = new Set(
    [...diedOn(state, night)].filter(who => alive.has(who)));
  // And somebody it did not kill — a Tea Lady's neighbour, an Innkeeper's
  // pick, a Fool. They carried the token into the night all the same, so
  // an Innkeeper among them chose with no ability. Nothing on the board
  // says who, so it is a guess and priced like one (03.10.2026).
  const carried = who =>
    (dueTonight.has(who) ? 1.0 : PRIORS.POISON_HIT_PENALTY);
  if (night >= 2)
    out.push(new Source("Pukka's token", alive,
                        {capacity: 1, cost: carried, repeatCost: carried}));
  return out;
});

/** From the night it dies, one player is drunk for good.
 *
 * Any death does it, and the Storyteller never says who — so the reach
 * is everybody and it never turns off again. That last part is what
 * makes it different from a Poisoner: a seat it landed on is impaired
 * for the rest of the game.
 *
 * Free rather than priced: the Storyteller picks, and picking somebody
 * is not a coincidence that needs paying for.
 */
sourceRule(function aSweetheartLeavesSomebodyDrunk(world, state, night) {
  if (!inBag(state, "Sweetheart")) return [];
  // Whoever was the Sweetheart when they died, dealt or made. See solver.py.
  const out = [];
  for (let seat = 0; seat < state.nPlayers; seat++) {
    const gone = state.diedAt(seat).filter(p => world.roleAt(seat, p) === "Sweetheart");
    if (!gone.length) continue;
    const first = gone.reduce((a, b) => phaseIndex(a) <= phaseIndex(b) ? a : b);
    if (phaseIndex(first) > phaseIndex(`N${night}`)) continue;
    out.push(new Source("Sweetheart", allSeats(state),
                        {capacity: 1, cost: 1.0, repeatCost: 1.0}));
  }
  return out;
});

// The Poisoner goes in first, before anything below it. Registration
// order decides which arrangement an impairment plan settles on when two
// cost the same, so it is part of the behaviour rather than a detail.
// Read late, through functions, so the sensitivity pass can move the
// constants above and have it mean something.
sourceRule(makePoisonerRule(() => PRIORS.POISON_HIT_PENALTY,
                            () => PRIORS.POISON_REPEAT_PENALTY));

// --------------------------------------------------------------------
// Ways of walking away from your own execution
// --------------------------------------------------------------------
// Trouble Brewing has none, so an execution recorded as survived there is
// not a world at all. The four here are told apart by which seat had to
// have been working.

export const SURVIVES_EXECUTION_RULES = [];
export const survivesExecutionRule = fn =>
  (SURVIVES_EXECUTION_RULES.push(fn), fn);

export function survivalsOf(world, state, day, seat, but = null) {
  const out = [];
  for (const rule of SURVIVES_EXECUTION_RULES)
    if (rule !== but) out.push(...rule(world, state, day, seat));
  return out;
}

/** Was this seat executed that day and left standing? */
const walkedAway = (state, day, seat) =>
  (state.executions || {})[day] === seat &&
  state.executionDeath(day) === null;

/** The gallows only. It chose somebody last night, and if the town
 * executes them today they walk away — but nothing else about their day
 * changes, so a Tinker it protected can still go of its own accord. */
const aDevilsAdvocateSavesFromTheGallows = survivesExecutionRule(
  function aDevilsAdvocateSavesFromTheGallows(world, state, day, seat) {
    if (!inBag(state, "DevilsAdvocate")) return [];
    const advocate = acting(world, state, "DevilsAdvocate", day);
    if (advocate === null) return [];
    // "Different to last night": it cannot keep the same player from the
    // gallows two days running. If they walked away yesterday too and
    // nothing but the Advocate could have managed that, it was spent on
    // them then.
    if (walkedAway(state, day - 1, seat) &&
        !survivalsOf(world, state, day - 1, seat,
                     aDevilsAdvocateSavesFromTheGallows).length) return [];
    return [advocate];
  });

/** "You cannot die during the day." Working, it walks away from the
 * gallows; drunk by a Courtier it does too (their jinx), so a Courtier
 * that named it lately is a second way and the plan demands neither
 * (10.10.2026). See solver.py. */
survivesExecutionRule(function aVizierCannotDieByDay(world, state, day, seat) {
  if (!inBag(state, "Vizier")) return [];
  if (world.roleAt(seat, `D${day}`) !== "Vizier") return [];
  const out = [seat];
  for (const info of state.infos)
    if (info.sourceRole === "Courtier" && info.role === "Vizier"
        && info.night <= day && day < info.night + 3) out.push(info.player);
  return out;
});

/** "If executed, you only die if you lose roshambo." Working, it may walk
 * away from the gallows, and that costs nothing (10.10.2026). */
survivesExecutionRule(function aPsychopathWinsAtRoshambo(
    world, state, day, seat) {
  if (!inBag(state, "Psychopath")) return [];
  if (world.roleAt(seat, `D${day}`) !== "Psychopath") return [];
  return [seat];
});

/** Some executed good players do not die — the Storyteller decides.
 *
 * A choice rather than a rule, so an executed good player who *did* die
 * proves nothing. It only ever explains a survival. */
survivesExecutionRule(function aPacifistMaySpareTheGood(
    world, state, day, seat) {
  if (!inBag(state, "Pacifist")) return [];
  const phase = `D${day}`;
  const pacifist = world.findAt("Pacifist", phase);
  if (pacifist === null || !state.aliveSet(phase).has(pacifist)) return [];
  if (world.evilAt(seat, phase)) return [];      // only the good are spared
  return [pacifist];
});

/** The Tea Lady whose protection covers this seat right now, or null.
 *
 * Both her living neighbours good, and this seat one of them. Asked of a
 * phase, because who is living beside her changes as people die — and it
 * is asked at night and in daylight alike. */
/** Who is standing when the town executes: the day's living, less anybody
 * who already died earlier that day — a Witch's curse, a Golem's nominee,
 * a Psychopath's pick (10.10.2026). The executed seat stays. */
function atTheGallows(state, day) {
  const phase = `D${day}`;
  const hanged = state.executedOn(day);
  return new Set([...state.aliveSet(phase)].filter(
    p => p === hanged || !state.diedAt(p).includes(phase)));
}

function teaLadyKeeping(world, state, seat, phase, alive = null) {
  if (alive === null) alive = state.aliveSet(phase);
  const lady = world.findAt("TeaLady", phase);
  if (lady === null || !alive.has(lady)) return null;
  const around = livingBeside(state, lady, phase, alive);
  // One other player left alive is her neighbour on both sides, and "both
  // your alive neighbours are good" is true of them (03.10.2026).
  if (!around.has(seat)) return null;
  for (const p of around) if (world.evilAt(p, phase)) return null;
  return lady;
}

/** "Cannot die" means cannot die: the gallows as much as the Demon.
 *
 * Her night-time protection has been here since she went in and the
 * daylight half never was, so a neighbour executed and left standing had
 * nothing to explain it (02.10.2026). */
survivesExecutionRule(function aTeaLadyKeepsHerNeighboursFromTheGallows(
    world, state, day, seat) {
  if (!inBag(state, "TeaLady")) return [];
  const lady = teaLadyKeeping(world, state, seat, `D${day}`,
                              atTheGallows(state, day));
  return lady === null ? [] : [lady];
});

/** Is one of her living neighbours on a side that can turn?
 *
 * A Goon is on whichever side last chose it, and nobody writes that down.
 * With one beside her she may be protecting and she may not — so her
 * protection can explain somebody living, and a death beside her proves
 * nothing about her (03.10.2026). */
function besideASideNobodyKnows(world, state, lady, phase, alive = null) {
  for (const p of livingBeside(state, lady, phase, alive))
    if (CHARACTERS[world.roleAt(p, phase)].alignment_open) return true;
  return false;
}

/** Executed and dead beside a Tea Lady: she was not working. */
export function teaLadyFailedAtTheGallows(world, state, day, seat) {
  if (!inBag(state, "TeaLady")) return null;
  const standing = atTheGallows(state, day);
  const lady = teaLadyKeeping(world, state, seat, `D${day}`, standing);
  if (lady !== null
      && besideASideNobodyKnows(world, state, lady, `D${day}`, standing))
    return null;
  return lady;
}

/** Its one free death covers the gallows as well as the night. */
const aFoolWalksAwayOnce = survivesExecutionRule(
  function aFoolWalksAwayOnce(world, state, day, seat) {
    if (!inBag(state, "Fool")) return [];
    if (world.roleAt(seat, `D${day}`) !== "Fool") return [];
    // Once. An earlier walk from the gallows that nothing else explains
    // was the Fool's one free death, and it is gone.
    //
    // Unless it has been dead and back since: "the regurgitated player
    // regains their ability, even a once per game ability already used",
    // and the same for a Professor's (03.10.2026).
    const back = ((state.resurrections || {})[seat] || [])
      .map(at => parseInt(String(at).slice(1), 10));
    for (let earlier = 1; earlier < day; earlier++) {
      if (back.some(night => earlier < night && night <= day)) continue;
      if (walkedAway(state, earlier, seat) &&
          !survivalsOf(world, state, earlier, seat, aFoolWalksAwayOnce).length)
        return [];
    }
    return [seat];
  });

/** It cannot die, and that holds in daylight.
 *
 * This is the deduction the table can make for itself: execute the
 * Sailor, watch it live, and you know it was working — which means the
 * person it chose the night before is carrying its drunkenness. */
survivesExecutionRule(function aSoberSailorWalksAway(world, state, day, seat) {
  if (!inBag(state, "Sailor")) return [];
  return world.roleAt(seat, `D${day}`) === "Sailor" ? [seat] : [];
});

// --------------------------------------------------------------------
// What kills
// --------------------------------------------------------------------

// Demons with a kill rule of their own. A Demon not named here kills the
// ordinary way, which is the right default: an unmodelled Demon that
// cannot kill would make every board it appears on impossible, while an
// unmodelled Demon that kills once a night is merely incomplete.
export const KILLS_ITS_OWN_WAY = new Set();

/** Say that these Demons are handled by a rule of their own. */
export const killsItsOwnWay = (...names) =>
  names.forEach(n => KILLS_ITS_OWN_WAY.add(n));

killsItsOwnWay("Zombuul", "Pukka", "Shabaloth", "Po");

/** The one cause Trouble Brewing has.
 *
 * Fires every night from the second, whether or not anybody wants it to,
 * and can aim anywhere — including at a corpse, which is how a Demon
 * bluffing protection buys itself a quiet night. */
causeRule(function theDemonKills(world, state, night) {
  if (night < 2) return [];              // nobody dies on the first night
  const phase = `N${night}`;
  const demon = world.demonAt(phase);
  if (demon === null) return [];
  // Each Demon that kills differently has its own rule below.
  // Each Demon that kills differently has its own rule below, and says
  // so by registering its name. Everything else kills the ordinary way.
  //
  // This used to name the Imp instead, which quietly meant "no Demon on
  // any script but Trouble Brewing and Bad Moon Rising can kill at all".
  // Recording a night death on a third script made every world
  // impossible — an ordinary board reading as a contradiction, which is
  // much worse than a Demon whose special trick is not modelled yet.
  if (KILLS_ITS_OWN_WAY.has(world.roleAt(demon, phase))) return [];
  if (!state.aliveSet(phase).has(demon)) return [];
  // Stopped at its source only when something tonight could reach it —
  // offered blindly it crowded the real story out of the first 24
  // accounts. See the_demon_kills in solver.py.
  let reachable = sourcesOn(world, state, night)
    .some(source => source.seats.has(demon));
  // Not on a night a Sweetheart dies: her drunkenness can land on the
  // Demon right after it kills her. See solver.py.
  for (let p = 0; p < state.nPlayers; p++)
    if (state.diedAt(p).includes(`N${night}`) &&
        world.roleAt(p, `N${night}`) === "Sweetheart") reachable = false;
  return [new Cause("Demon", DEMON, allSeats(state),
                    {capacity: 1, mustFire: true,
                     actor: reachable ? demon : null,
                     actorCost: PRIORS.DEMON_POISONED_PENALTY})];
});

/** Could anything have made this seat drunk or poisoned that night?
 *
 * A Demon that has to kill and killed nobody may have been stopped at its
 * source: it chose the Goon first, a Sailor or an Innkeeper made it
 * drunk, a Courtier named it, a Minstrel silenced the town. The four
 * Demons of Bad Moon Rising had no such explanation, and once played
 * games told their quiet nights, 83 in 60,000 lost the world that
 * happened (04.10.2026). Offered only where something could reach it.
 * See _could_be_stopped in solver.py. */
function couldBeStopped(world, state, seat, night) {
  return sourcesOn(world, state, night).some(source => source.seats.has(seat));
}

/** A Zombuul is dead on the board before it is dead in fact.
 *
 * The first time it would die it does not — but it registers as dead, so
 * the table crosses it off while it carries on killing. It is only really
 * gone the second time. */
function zombuulStillGoing(world, state, seat, phase) {
  const gone = state.diedAt(seat)
    .filter(p => phaseIndex(p) < phaseIndex(phase));
  return gone.length < 2;
}

/** Only if nobody died during the day before.
 *
 * Any death at all stops it — an execution, a Slayer shot, a Tinker going
 * of its own accord. And it kills while registered dead. */
causeRule(function aZombuulKillsOnAQuietDay(world, state, night) {
  if (!inBag(state, "Zombuul") || night < 2) return [];
  const phase = `N${night}`;
  const seat = world.findAt("Zombuul", phase);
  if (seat === null || !zombuulStillGoing(world, state, seat, phase)) return [];
  if (anyDiedAt(state, `D${night - 1}`)) return [];   // somebody went by day
  return [new Cause("Demon", DEMON, allSeats(state),
                    {capacity: 1, mustFire: true,
                     actor: couldBeStopped(world, state, seat, night) ? seat : null,
                     actorKillsWorking: false})];
});

/** Poisons on one night, and that poison kills on the next.
 *
 * It starts a night earlier than any other Demon: on the first night it
 * only poisons. So the victim has to be the seat its poison was on, which
 * is a demand on a night already accounted for. */
causeRule(function aPukkaKillsWhatItPoisoned(world, state, night) {
  if (!inBag(state, "Pukka") || night < 2) return [];
  const seat = acting(world, state, "Pukka", night);
  if (seat === null) return [];
  // Three ways a Pukka's night passes without a body besides "the one
  // it poisoned could not die". Drunk or poisoned tonight: no attack,
  // and that is the actor. Or it was last night: it poisoned nobody
  // then, so what comes due is the token from the night before that —
  // and that player could not die. Or there was no night before that.
  // See solver.py.
  const excuses = [];
  for (const back of [1, 2]) {
    const chose = night - 1 - back;
    const from = Math.max(chose, 0) + 1;
    let fits = true;
    for (let k = from; k < night; k++)
      if (acting(world, state, "Pukka", k) !== seat ||
          !couldBeStopped(world, state, seat, k)) fits = false;
    if (!fits) break;
    const demands = [];
    for (let k = from; k < night; k++) demands.push([k, seat]);
    if (chose < 1) { excuses.push([null, demands]); break; }
    if (acting(world, state, "Pukka", chose) !== seat) break;
    excuses.push([state.aliveSet(`N${chose}`), demands]);
  }
  const out = [new Cause("Demon", DEMON, state.aliveSet(`N${night - 1}`),
                         {capacity: 1, mustFire: true,
                          victimImpairedAt: night - 1,
                          actor: couldBeStopped(world, state, seat, night)
                            ? seat : null,
                          actorKillsWorking: false, excuses})];
  // A night late, or two. A drunk or poisoned Pukka does not attack and
  // its token stays where it is (the flowchart), and the poison rests
  // while it does (table ruling, 02.10.2026). So the one it poisoned on
  // night two was sober through night three and died on night four —
  // which, read the plain way, needs them poisoned on a night they were
  // demonstrably working. The same kill under the same name, so it
  // shares the one a night; and never owed, since the plain cause is.
  for (const late of [1, 2]) {
    const chose = night - 1 - late;
    if (chose < 1) break;
    let same = true;
    for (let k = chose; k < night; k++)
      if (acting(world, state, "Pukka", k) !== seat) same = false;
    if (!same) break;
    const also = [];
    for (let k = chose + 1; k < night; k++) also.push([k, seat]);
    out.push(new Cause("Demon", DEMON, state.aliveSet(`N${chose}`),
                       {capacity: 1, victimImpairedAt: chose,
                        alsoImpaired: also}));
  }
  return out;
});

/** Two a night, and either can be aimed at somebody already dead, so the
 * table may only ever see one body. */
causeRule(function aShabalothKillsTwice(world, state, night) {
  if (!inBag(state, "Shabaloth") || night < 2) return [];
  const seat = acting(world, state, "Shabaloth", night);
  if (seat === null) return [];
  return [new Cause("Demon", DEMON, allSeats(state),
                    {capacity: 2, mustFire: true,
                     actor: couldBeStopped(world, state, seat, night) ? seat : null,
                     actorKillsWorking: false})];
});

/** It may choose nobody — and then it takes three the next night.
 *
 * Whether it chose nobody is not written down, so a night with no bodies
 * is read as it possibly having declined. Permissive rather than exact,
 * which errs towards keeping worlds rather than throwing them away. */
causeRule(function aPoKillsNoneOrThree(world, state, night) {
  if (!inBag(state, "Po") || night < 2) return [];
  if (acting(world, state, "Po", night) === null) return [];
  // A Po charges by taking **nobody**, and then takes three.
  //
  // This asked whether *anybody* died last night, which is a different
  // question: a Tinker that simply went, an Acrobat that fell, a Gambler
  // that guessed wrong all die without the Po lifting a finger. One of
  // those on the charging night offered a capacity of one against a
  // record of three, and the board had no legal world.
  //
  // Whether the Po killed cannot be read off the deaths, because the
  // deaths are what is being explained. A capacity is a ceiling, so
  // three covers taking one and the search decides.
  //
  // Except on the second night: three is for the night after it chose
  // nobody, and the first night is not a choice.
  return [new Cause("Demon", DEMON, allSeats(state),
                    {capacity: night === 2 ? 1 : 3, mustFire: false})];
});

/** A Demon was created, so tonight's deaths are the Storyteller's.
 *
 * Nought to everybody, and no shield touches them — the same shape as
 * the Assassin, and for the same reason: the rule says deaths *are*
 * arbitrary rather than that somebody kills.
 *
 * These are the Pit-Hag's, not the Demon's, so a grandchild lost to one
 * leaves the Grandmother standing and a Soldier is no safer than anyone.
 */
causeRule(function aPitHagMakingADemonMakesDeathsArbitrary(world, state, night) {
  if (!inBag(state, "PitHag")) return [];
  const made = state.infos.some(
    i => i.sourceRole === "PitHag" && i.role && i.night === night &&
         CHARACTERS[i.role] && CHARACTERS[i.role].team === "demon");
  if (!made) return [];
  return [new Cause("Pit-Hag", OTHER, allSeats(state),
                    {capacity: state.nPlayers, cost: 1.0,
                     unstoppable: true})];
});

/** A second way to die at night, and not the Demon's.
 *
 * Which matters more than it sounds: a Soldier is safe from the Demon and
 * not from this, and a grandchild lost to it leaves the Grandmother
 * standing. */
causeRule(function aGossipMayKill(world, state, night) {
  if (!inBag(state, "Gossip") || night < 2) return [];
  if (acting(world, state, "Gossip", night) === null) return [];
  return [new Cause("Gossip", OTHER, allSeats(state),
                    {capacity: 1, cost: PRIORS.GOSSIP_KILL_PENALTY,
                     mustFire: false})];
});

/** An Outsider lost in *daylight*, and the Godfather kills tonight.
 *
 * Daylight specifically — an Outsider taken in the night triggers
 * nothing, which is a clean piece of deduction for the table. Whether the
 * seat that died was an Outsider is a question about the world rather
 * than about the board. */
causeRule(function aGodfatherAnswersAnOutsider(world, state, night) {
  if (!inBag(state, "Godfather") || night < 2) return [];
  const seat = acting(world, state, "Godfather", night);
  if (seat === null) return [];
  const day = `D${night - 1}`;
  const lost = Object.keys(state.deaths || {}).some(who =>
    state.diedAt(who).includes(day) &&
    world.teamAt(Number(who), day) === "outsider");
  if (!lost) return [];
  // Drunk or poisoned it kills nobody, and so does one that chose the
  // Goon first: a quiet night stopped at its source.
  return [new Cause("Godfather", OTHER, allSeats(state),
                    {capacity: 1, mustFire: true, actor: seat})];
});

/** Once per game, and nothing stops it.
 *
 * "Dies even if they could not" overrides every shield in the game, so a
 * seat killed this way tells you nothing about whether its protection was
 * working. Not the Demon's kill either. */
causeRule(function anAssassinKillsThroughAnything(world, state, night) {
  if (!inBag(state, "Assassin") || night < 2) return [];
  if (acting(world, state, "Assassin", night) === null) return [];
  const spent = state.infos.filter(i => i.sourceRole === "Assassin")
                           .map(i => i.night);
  if (spent.length && !spent.includes(night)) return [];
  return [new Cause("Assassin", OTHER, allSeats(state),
                    {capacity: 1, cost: PRIORS.ASSASSIN_STRIKE_PENALTY,
                     unstoppable: true})];
});

/** The Storyteller decides, and there is no trigger to wait for.
 *
 * Not the Demon's doing, which is why a Monk is no help. A Tea Lady or an
 * Innkeeper does stop it, because they guard against everything. */
causeRule(function aTinkerMayGoAtAnyTime(world, state, night) {
  if (!inBag(state, "Tinker")) return [];
  const seat = acting(world, state, "Tinker", night);
  if (seat === null) return [];
  return [new Cause("Tinker", OTHER, new Set([seat]),
                    {capacity: 1, cost: PRIORS.TINKER_DEATH_PENALTY})];
});

/** Its pick lands the night *after* it learns it died.
 *
 * Only a good target dies. Picking an evil one does nothing at all, which
 * is why this may fire rather than must. */
causeRule(function aMoonchildTakesSomebodyWithIt(world, state, night) {
  if (!inBag(state, "Moonchild") || night < 2) return [];
  const phase = `N${night}`;
  const child = world.findAt("Moonchild", phase);
  if (child === null) return [];
  const went = state.diedAt(child);
  if (!went.includes(`N${night - 1}`) && !went.includes(`D${night - 1}`))
    return [];
  const good = new Set([...state.aliveSet(phase)]
    .filter(seat => !world.evilAt(seat, phase)));
  // Recorded, it points somewhere in particular — and then a good player
  // it named *does* die. One still standing needs a reason: somebody
  // keeping them alive, or the Moonchild's ability not working that
  // night. Without that, "they lived, so they are evil" was never drawn
  // (02.10.2026).
  const picked = chosen(state, "Moonchild", night, ["target"], child);
  if (picked === null)
    return good.size ? [new Cause("Moonchild", OTHER, good, {capacity: 1})]
                     : [];
  const aimed = new Set([...good].filter(x => picked.has(x)));
  if (!aimed.size) return [];              // it named somebody evil
  // A Goon it named may have been turned by then, and nobody knows: the
  // pick may kill and need not.
  if ([...aimed].some(x => CHARACTERS[world.roleAt(x, phase)].alignment_open))
    return [new Cause("Moonchild", OTHER, aimed, {capacity: 1})];
  return [new Cause("Moonchild", PICKED, aimed,
                    {capacity: 1, mustFire: true})];
});

/** Guessing wrong kills you, and nothing else.
 *
 * It reaches exactly one seat — its own — so it can never account for
 * anybody else's death. */
/** Its pick was droisoned, so it dies — and nothing else does.
 *
 * Reaches exactly its own seat, like the Gambler's. Whether it *did*
 * fall is not decided here: that depends on whether the seat it picked
 * was impaired, which the impairment plan settles later.
 *
 * Not a Demon kill, so a Soldier or a Monk is no help. A Tea Lady is,
 * because her neighbours cannot die at all.
 */
causeRule(function anAcrobatMayFall(world, state, night) {
  if (!inBag(state, "Acrobat") || night < 2) return [];
  const phase = `N${night}`;
  const seat = world.findAt("Acrobat", phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return [];
  const picked = state.infos.some(
    i => i.sourceRole === "Acrobat" && i.night === night);
  if (!picked) return [];
  return [new Cause("Acrobat", OTHER, new Set([seat]), {capacity: 1,
                                                   mustFire: false})];
});

causeRule(function aGamblerMayLose(world, state, night) {
  if (!inBag(state, "Gambler") || night < 2) return [];
  // Whoever held it as the night began: it guesses tenth, and a Pit-Hag
  // at sixteen may have made the dead Gambler something else. And
  // everybody who has the ability — a Philosopher that took it stands
  // beside the real one, drunk and harmless (both 07.10.2026).
  const phase = `N${night}`, began = `D${night - 1}`;
  const holders = [];
  for (const at of [began, phase]) {
    const seat = world.findAt("Gambler", at);
    if (seat !== null && !holders.includes(seat)) holders.push(seat);
  }
  const took = state.philosophies() || {};
  for (const who of Object.keys(took).map(Number).sort((x, y) => x - y)) {
    const [taken, since] = took[who];
    if (taken === "Gambler" && !holders.includes(who)
        && world.roleAt(who, began) === "Philosopher"
        && phaseIndex(phase) >= phaseIndex(since)) holders.push(who);
  }
  const guesses = state.infos.filter(
    i => i.sourceRole === "Gambler" && i.night === night);
  const causes = [];
  for (const seat of holders) {
    if (!state.aliveSet(phase).has(seat)) continue;
    // Its own guess where the row says whose it was; a guess relayed by
    // somebody with no such ability could be anybody's.
    let mine = guesses.filter(g => g.player === seat);
    if (!mine.length) mine = guesses.filter(g => !holders.includes(g.player));
    if (!mine.length) continue;            // no guess recorded, no risk
    // A guess that was right kills nobody, judged as it was made.
    if (mine.every(g => world.roleAt(g.target, began) === g.role)) continue;
    causes.push(new Cause("Gambler", OTHER, new Set([seat]), {capacity: 1}));
  }
  return causes;
});

// --------------------------------------------------------------------
// What follows from a death
// --------------------------------------------------------------------

/** Her grandchild taken by the Demon takes her with it.
 *
 * Only the Demon. A grandchild lost to a Gossip or an Assassin leaves her
 * standing, which is why a death has to record what killed it.
 *
 * The grandchild is read off her reading rather than off the world: it is
 * a token the Storyteller put on the seat she was shown, and it sits
 * there whether what she was told was true or invented. */
implicationRule(function aGrandmotherGrieves(world, state, night, victim, kind) {
  if (!inBag(state, "Grandmother") || kind !== DEMON) return [];
  const out = [];
  for (const info of state.infos) {
    if (info.sourceRole !== "Grandmother" || info.target !== victim) continue;
    const seat = info.player;
    if (world.roleAt(seat, `N${night}`) !== "Grandmother") continue;
    // The grandchild she has *now*: her latest reading, from this life.
    // One who died and came back is a new Grandmother and is shown a new
    // grandchild (03.10.2026); the old one is nothing to her.
    const later = state.infos.some(
      other => other.sourceRole === "Grandmother" && other.player === seat &&
               info.night < other.night && other.night < night);
    if (later || (info.night >= night && night > 1) ||
        diedBetween(state, seat, info.night, night)) continue;
    // A Grandmother already dead cannot die again of grief.
    if (!state.aliveSet(`N${night}`).has(seat)) continue;
    // Nor one who only came back tonight and is standing at dawn: a
    // Professor raises at 43, after every Demon, so she was still dead
    // when her grandchild fell.
    if (returnedAt(state, `N${night}`).has(seat)) continue;
    out.push(implication(seat, seat));
  }
  return out;
});

// --------------------------------------------------------------------
// What stops a death
// --------------------------------------------------------------------

immunityRule(function theSoldierCannotBeDemonKilled(
    world, state, night, seat, kind) {
  if (!inBag(state, "Soldier") || kind !== DEMON) return [];
  if (world.roleAt(seat, `N${night}`) !== "Soldier") return [];
  // Only while working — a poisoned Soldier dies like anybody else.
  return [shield("Soldier", {needs: seat})];
});

immunityRule(function theMonkGuardsAgainstTheDemon(
    world, state, night, seat, kind) {
  if (!inBag(state, "Monk") || kind !== DEMON || night < 2) return [];
  const phase = `N${night}`;
  const monk = world.findAt("Monk", phase);
  if (monk === null || monk === seat) return [];
  if (!state.aliveSet(phase).has(monk)) return [];
  // Aimed: a death only ever means it guarded somebody else.
  return [shield("Monk", {needs: monk, chosen: true})];
});

/** The nearest living player on each side, going round the circle. */
function livingBeside(state, seat, phase, alive = null) {
  if (alive === null) alive = state.aliveSet(phase);
  const n = state.nPlayers;
  const out = new Set();
  for (const step of [1, -1])
    for (let gap = 1; gap < n; gap++) {
      const other = (seat + step * gap + n * n) % n;
      if (other === seat) break;
      if (alive.has(other)) { out.add(other); break; }
    }
  return out;
}

/** The pick did nothing because the Moonchild's ability did not.
 *
 * What counts is its state on the night the pick lands, and the dead can
 * be drunk or poisoned like anybody else. The plan does not reach the
 * dead, so this is priced like a poisoning rather than routed through
 * it. */
immunityRule(function aMoonchildThatWasNotWorking(
    world, state, night, seat, kind) {
  if (kind !== PICKED) return [];
  return [shield("Moonchild not working",
                 {cost: PRIORS.POISON_HIT_PENALTY, chosen: true})];
});

/** Both her living neighbours good, and neither of them can die.
 *
 * Whether they are good is exactly what is in question, so this depends
 * on the world being scored rather than on the board. Always on rather
 * than aimed: she picks nobody, so a neighbour who died means she was not
 * working. */
immunityRule(function aTeaLadyKeepsHerNeighbours(world, state, night, seat) {
  if (!inBag(state, "TeaLady")) return [];
  const phase = `N${night}`;
  // On a night somebody came back, who stood beside her has two answers.
  // She was raised at 43 and her neighbour was killed at 28: she was not
  // there to keep them. Or the one beside her came back late, and at 28
  // her neighbour was somebody else. Her protection is only *demanded*
  // when it held whichever way the night went (03.10.2026).
  const held = rosters(state, phase).map(
    alive => teaLadyKeeping(world, state, seat, phase, alive));
  const lady = held.find(who => who !== null);
  if (lady === undefined) return [];
  const eitherWay = held.every(who => who !== null);
  // A Tea Lady who died tonight herself stops protecting the moment she
  // goes. A Shabaloth that takes her first and her neighbour second kills
  // both, and the plan knows whole nights rather than the order within
  // one — so on such a night her protection may explain a survival but
  // demands nothing of a death.
  const fell = state.diedAt(lady).includes(phase);
  // And one living beside a Goon: its side is not on the board.
  const unsure = rosters(state, phase).some(
    alive => besideASideNobodyKnows(world, state, lady, phase, alive));
  return [shield("Tea Lady",
                 {needs: lady, chosen: fell || unsure || !eitherWay})];
});

/** The first death does not take it, whatever the death was.
 *
 * Marked as aimed rather than always on, and the reason is worth saying:
 * a Fool's first would-be death leaves no record at all, because nothing
 * happened. So a Fool that *is* dead says nothing — the free one was
 * spent out of sight. What it can do is explain a survival. */
immunityRule(function aFoolSurvivesOnce(world, state, night, seat) {
  if (!inBag(state, "Fool")) return [];
  if (world.roleAt(seat, `N${night}`) !== "Fool") return [];
  return [shield("Fool", {needs: seat, chosen: true})];
});

/** Not by the Demon, not by anything.
 *
 * Always on rather than aimed, so a Sailor who died must have been
 * impaired — including by its own ability, which is the price the town
 * pays for having one. */
immunityRule(function aSoberSailorCannotDie(world, state, night, seat) {
  if (!inBag(state, "Sailor")) return [];
  if (world.roleAt(seat, `N${night}`) !== "Sailor") return [];
  return [shield("Sailor", {needs: seat})];
});

/** From everything, not only the Demon — and it picks who. */
immunityRule(function anInnkeeperGuardsTwo(world, state, night, seat) {
  if (!inBag(state, "Innkeeper") || night < 2) return [];
  const keeper = acting(world, state, "Innkeeper", night);
  if (keeper === null) return [];
  if (returnedAt(state, `N${night}`).has(keeper)) return [];   // back tonight
  // Written down, the choice is no longer free. The two it named cannot
  // die tonight while it is working, so one of them dead means it was not
  // — and nobody else is covered at all. Unless the Innkeeper fell
  // tonight itself: its protection goes with it.
  const picked = chosen(state, "Innkeeper", night, ["a", "b"], keeper);
  if (picked === null)
    return [shield("Innkeeper", {needs: keeper, chosen: true})];
  if (!picked.has(seat)) return [];
  const fell = state.diedAt(keeper).includes(`N${night}`);
  return [shield("Innkeeper", {needs: keeper, chosen: fell})];
});

/** Choosing the Demon stops it waking at all, so nobody dies by it.
 *
 * Aimed rather than always on: it says nothing about a seat that did die,
 * only that it could have been the reason one did not. */
immunityRule(function anExorcistSendsTheDemonToBed(
    world, state, night, seat, kind) {
  if (!inBag(state, "Exorcist") || kind !== DEMON || night < 2) return [];
  const demon = world.demonAt(`N${night}`);
  if (demon !== null && demon !== undefined &&
      world.roleAt(demon, `N${night}`) === "Pukka") {
    // A Pukka is the exception: what dies tonight was chosen last night.
    // Naming it stops it *choosing*, so yesterday's victim still dies and
    // the quiet night is the one after (the flowchart; 02.10.2026).
    const then = night < 3 ? null
      : acting(world, state, "Exorcist", night - 1);
    if (then === null) return [];
    const before = chosen(state, "Exorcist", night - 1, ["target"], then);
    if (before !== null && !before.has(world.demonAt(`N${night - 1}`)))
      return [];
    // It had to be working *then*, which is not tonight's question.
    return [shield("Exorcist", {chosen: true})];
  }
  const exorcist = acting(world, state, "Exorcist", night);
  if (exorcist === null) return [];
  if (returnedAt(state, `N${night}`).has(exorcist)) return []; // back tonight
  // Recorded, it only stops the Demon if it named the seat holding it.
  const named = chosen(state, "Exorcist", night, ["target"], exorcist);
  // The Demon as the Exorcist's turn came, at 21. One that died tonight
  // handed the star on after that — a Fang Gu jumping, an Imp killing
  // itself (07.10.2026).
  let demonThen = world.demonAt(`N${night}`);
  const began = world.demonAt(`D${night - 1}`);
  // Only a Demon that died *as* one: a Snake Charmer swaps at 11, ahead
  // of the Exorcist, and the new Demon may then kill the old.
  if (began !== null && began !== demonThen
      && state.diedAt(began).includes(`N${night}`)
      && CHARACTERS[world.roleAt(began, `N${night}`)].team === "demon")
    demonThen = began;
  if (named !== null && !named.has(demonThen)) return [];
  // And it cuts the other way. Named and written down, the Demon does not
  // act tonight — so a Demon kill on that night says the Exorcist was not
  // working, or that this seat is not the Demon.
  return [shield("Exorcist", {needs: exorcist, chosen: named === null})];
});

/** The Banshee the table was told about died to the Demon and to nothing
 * else: the announcement comes only from a Demon's kill (table ruling,
 * 08.10.2026). A shield nothing had to be working for. */
immunityRule(function anAnnouncedBansheeFellToTheDemon(
    world, state, night, seat, kind) {
  if (kind === DEMON || !inBag(state, "Banshee")) return [];
  for (const info of state.infos)
    if (info.sourceRole === "Banshee" && info.night === night && info.hard()
        && info.leanedOn(world, state).includes(seat))
      return [shield("Banshee announced")];
  return [];
});

/** A working Choirboy was shown the Demon, so the King it died with fell
 * to the Demon and nothing else (10.10.2026). See solver.py. */
immunityRule(function aChoirboysKingFellToTheDemon(
    world, state, night, seat, kind) {
  if (kind === DEMON || !inBag(state, "Choirboy")) return [];
  const phase = `N${night}`;
  if (world.roleAt(seat, phase) !== "King") return [];
  for (const info of state.infos)
    if (info.type === "ChoirboyInfo" && info.night === night
        && world.roleAt(info.player, phase) === "Choirboy")
      return [shield("Choirboy", {needs: info.player})];
  return [];
});

/** "On your 1st day, if you nominated & executed a player, the Demon
 * doesn't kill tonight" (10.10.2026). See solver.py. */
immunityRule(function aPrincessStopsTheDemon(world, state, night, seat, kind) {
  if (kind !== DEMON || !inBag(state, "Princess")) return [];
  const day = night - 1;
  if (day < 1) return [];
  for (const info of state.infos) {
    if (info.type !== "PrincessNominated" || info.night !== day) continue;
    const princess = info.player;
    if (world.roleAt(princess, `D${day}`) !== "Princess") continue;
    if (day > 1 && world.roleAt(princess, `D${day - 1}`) === "Princess")
      continue;                        // not her first day
    if (state.executedOn(day) !== info.target) continue;
    if (!state.aliveSet(`N${night}`).has(princess)) continue;  // no ability
    return [shield("Princess", {needs: princess})];
  }
  return [];
});

/** The Demon went for the Mayor, and the Storyteller sent it elsewhere —
 * including into somebody already dead.
 *
 * Only the corpse case needs modelling. Bouncing onto a *living* player
 * is invisible: "the Demon attacked the Mayor and it landed on Cara" and
 * "the Demon attacked Cara" leave exactly the same board, and the solver
 * never tracked who was aimed at. Bouncing into a corpse is different —
 * a night where the Demon fired and nobody fell.
 *
 * Aimed rather than always on: the Storyteller chooses whether to move
 * the kill, so a Mayor that died at night proves nothing.
 */
immunityRule(function aMayorsDeathMayBeMoved(world, state, night, seat, kind) {
  if (!inBag(state, "Mayor") || kind !== DEMON) return [];
  const phase = `N${night}`;
  if (world.roleAt(seat, phase) !== "Mayor") return [];
  // Somebody has to already be dead for the kill to go nowhere.
  if (state.aliveAt(phase).length >= state.nPlayers) return [];
  return [shield("Mayor", {needs: seat, chosen: true})];
});

/** Aiming at a corpse kills nobody, whatever the aim.
 *
 * Nothing had to be working for that, so there is nobody to keep
 * unimpaired — but it is a deliberate play rather than the default, and a
 * Demon bluffing Soldier or Monk has every reason to make it. */
immunityRule(function theDeadCannotDieAgain(world, state, night, seat) {
  if (state.aliveSet(`N${night}`).has(seat)) {
    // Back tonight, so dead for the first part of it: a Pukka's poison
    // that came due at 26 found a corpse, and a Professor stood it up at
    // 43. The same sunk kill, except that from then on the seat can die
    // like anybody else — an excuse on offer, not a bar.
    if (returnedAt(state, `N${night}`).has(seat))
      return [shield("already dead", {needs: null,
                                      cost: PRIORS.SUNK_KILL_PENALTY,
                                      chosen: true})];
    return [];
  }
  return [shield("already dead", {needs: null, cost: PRIORS.SUNK_KILL_PENALTY})];
});

// --------------------------------------------------------------------
// What stops abilities working
// --------------------------------------------------------------------

/** Either the Sailor or whoever it chose, and it is not told which.
 *
 * Landing on the Sailor is the common case and priced as such; landing on
 * an evil seat is the one a Storyteller avoids. */
sourceRule(function aSailorDrunksOneOfTwo(world, state, night) {
  if (!inBag(state, "Sailor")) return [];
  const phase = `N${night}`;
  const seat = acting(world, state, "Sailor", night);
  if (seat === null) return [];
  // Whoever came back tonight was dead when its turn came — a Shabaloth
  // regurgitates at 27 and a Professor raises at 43, and the Sailor
  // chooses at 4. The same for the Innkeeper at 9 and the Exorcist at 21:
  // no choice, so nobody drunk and nobody guarded.
  if (returnedAt(state, phase).has(seat)) return [];
  const price = hit => {
    if (hit === seat) return 0.6;        // the usual half of the coin
    return world.evilAt(hit, phase) ? PRIORS.SAILOR_ON_EVIL_PENALTY : 0.6;
  };
  // It is one of two: the Sailor, or whoever it chose. Recorded, that is
  // a pair rather than the whole table.
  const picked = chosen(state, "Sailor", night);
  const reach = picked === null ? state.aliveSet(phase)
                                : new Set([seat, ...picked]);
  return [new Source("Sailor", reach,
                     {capacity: 1, cost: price, repeatCost: price})];
});

/** The first person to point at the Goon that night goes drunk.
 *
 * Only the first, and only somebody whose ability actually *chooses* a
 * player — a Courtier names a character and never triggers one. Nobody
 * records who chose whom, so the reach is everybody who could have. */
sourceRule(function aGoonDrunksWhoeverChoseIt(world, state, night) {
  if (!inBag(state, "Goon")) return [];
  const phase = `N${night}`;
  const goon = acting(world, state, "Goon", night);
  if (goon === null) return [];
  const pickers = new Set([...state.aliveSet(phase)].filter(
    seat => seat !== goon && CHARACTERS[world.roleAt(seat, phase)].chooses));
  // And a Courtier that named the Goon tonight: "The Courtier chooses the
  // Goon. The Goon turns good, and the Courtier becomes drunk" (the wiki;
  // table ruling, 08.10.2026).
  for (const info of state.infos)
    if (info.sourceRole === "Courtier" && info.night === night
        && info.role === "Goon" && info.player !== goon
        && world.roleAt(info.player, phase) === "Courtier"
        && state.aliveSet(phase).has(info.player)) pickers.add(info.player);
  if (!pickers.size) return [];
  // On offer, never forced. With one chooser left alive this was a free
  // source that could reach everybody it could reach — which the plan
  // reads as unavoidable, so the last Sailor standing was drunk every
  // night whether or not it had pointed at the Goon (03.10.2026).
  const free = () => 1.0;
  return [new Source("Goon", pickers, {capacity: 1, cost: free,
                                       repeatCost: free})];
});

/** Whoever holds the named character, drunk for three days and nights.
 *
 * The reach depends on the world being scored, not on the night: the
 * Courtier named a character, and which seat that lands on is different
 * in every world. Free rather than lucky — a declared action, not a
 * guess, so there is nothing to have got right. */
sourceRule(function aCourtierNamesACharacter(world, state, night) {
  if (!inBag(state, "Courtier")) return [];
  const out = [];
  for (const info of state.infos) {
    if (info.sourceRole !== "Courtier") continue;
    // Three days and nights: the span it was used in and the two after.
    if (!(info.night <= night && night <= info.night + 2)) continue;
    const phase = `N${night}`;
    const courtier = world.findAt("Courtier", phase);
    if (courtier === null || courtier !== info.player) continue;
    // Only while the Courtier lives: a drunkenness rests when the one
    // causing it dies (table ruling, 02.10.2026).
    if (!state.aliveSet(phase).has(courtier)) continue;
    // And it *ends* there: an ability ends with the death of whoever has
    // it, and a character that comes back is a new instance (table
    // ruling, 03.10.2026). What the old Courtier named is sober for good.
    if (diedBetween(state, courtier, info.night, night)) continue;
    const hit = world.findAt(info.role, phase);
    if (hit === null) continue;          // named somebody nobody is
    // In the span the Courtier dies, the named one is drunk for part of
    // it and sober for the rest. So there it is on offer rather than
    // forced: free to explain something that went wrong, and no bar to
    // something that worked.
    const died = state.diedAt(courtier);
    // Named the Goon, it may have been the first to choose it — then the
    // Courtier was drunk on the spot and nothing happened (08.10.2026).
    const went = died.includes(phase) || died.includes(`D${night}`)
      || info.role === "Goon";
    const free = went ? () => 1.0 : 1.0;
    out.push(new Source("Courtier", new Set([hit]),
                        {capacity: 1, cost: free, repeatCost: free}));
  }
  return out;
});

/** A Minion executed, and everybody else is drunk until dusk tomorrow.
 *
 * The whole table at once, for nothing — by far the largest lever on this
 * script. Two Minions executed on consecutive days gives two such nights
 * running, which is the thing to check if the span arithmetic is wrong. */
sourceRule(function aMinstrelSilencesTheTable(world, state, night) {
  if (!inBag(state, "Minstrel")) return [];
  const seat = acting(world, state, "Minstrel", night);
  if (seat === null) return [];
  // There to hear it: a Minstrel raised tonight was dead when the Minion
  // hanged, and its ability did nothing.
  if (!state.aliveSet(`D${night - 1}`).has(seat)) return [];
  // "If a Minion *died* by execution": one that walked away silences
  // nobody.
  const executed = state.executionDeath(night - 1);
  if (executed === null) return [];
  if (world.teamAt(executed, `D${night - 1}`) !== "minion") return [];
  const everyone = new Set(
    Array.from({length: state.nPlayers}, (_, i) => i).filter(p => p !== seat));
  return [new Source("Minstrel", everyone,
                     {capacity: everyone.size, cost: 1.0, repeatCost: 1.0})];
});

/** "Each night, choose if you are drunk until dusk." Itself and nobody
 * else, its own choice, free and never forced (10.10.2026). */
sourceRule(function anOrganGrinderMayDrink(world, state, night) {
  if (!inBag(state, "OrganGrinder")) return [];
  const phase = `N${night}`;
  const seat = world.findAt("OrganGrinder", phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return [];
  return [new Source(ORGAN_GRINDER_BY_CHOICE, new Set([seat]),
                     {capacity: 1, cost: () => 1.0, repeatCost: () => 1.0})];
});

/** "On your 1st night ... choose a player: they are poisoned." Anybody,
 * itself included, as long as it lives; free and never forced
 * (10.10.2026). See solver.py. */
sourceRule(function aWidowPoisonsOne(world, state, night) {
  if (!inBag(state, "Widow")) return [];
  const phase = `N${night}`;
  const seat = world.findAt("Widow", phase);
  if (seat === null || !minionStillActs(world, state, seat, phase)) return [];
  const everyone = new Set(Array.from({length: state.nPlayers}, (_, i) => i));
  return [new Source("Widow", everyone,
                     {capacity: 1, cost: () => 1.0, repeatCost: () => 1.0})];
});

/** One of the pair it protected, and it does not choose which.
 *
 * Lasts the night and the day after, which needs no special handling: a
 * night and the day that follows share one span already, because poison
 * works the same way. */
sourceRule(function anInnkeeperDrunksOneOfTheTwoItGuards(world, state, night) {
  if (!inBag(state, "Innkeeper") || night < 2) return [];
  const seat = acting(world, state, "Innkeeper", night);
  if (seat === null) return [];
  if (returnedAt(state, `N${night}`).has(seat)) return [];     // back tonight
  // One of the two it protected, and it does not choose which.
  const picked = chosen(state, "Innkeeper", night, ["a", "b"]);
  const reach = picked === null ? state.aliveSet(`N${night}`) : picked;
  return [new Source("Innkeeper", reach,
                     {capacity: 1, cost: 0.5, repeatCost: 0.5})];
});
