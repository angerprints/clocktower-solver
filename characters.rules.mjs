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
import {DEMON, OTHER, Cause, causeRule, immunityRule, implication,
        implicationRule, shield} from "./deaths.mjs";
import {Source, makePoisonerRule, sourceRule} from "./impairment.mjs";
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

const allSeats = state => new Set(
  Array.from({length: state.nPlayers}, (_, i) => i));

/** The seat holding this character, if it is standing tonight. */
function acting(world, state, key, night) {
  const phase = `N${night}`;
  const seat = world.findAt(key, phase);
  if (seat === null || !state.aliveSet(phase).has(seat)) return null;
  return seat;
}

const anyDiedAt = (state, phase) =>
  Object.keys(state.deaths || {}).some(who => state.diedAt(who).includes(phase));

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

export function survivalsOf(world, state, day, seat) {
  const out = [];
  for (const rule of SURVIVES_EXECUTION_RULES)
    out.push(...rule(world, state, day, seat));
  return out;
}

/** The gallows only. It chose somebody last night, and if the town
 * executes them today they walk away — but nothing else about their day
 * changes, so a Tinker it protected can still go of its own accord. */
survivesExecutionRule(function aDevilsAdvocateSavesFromTheGallows(
    world, state, day) {
  if (!inBag(state, "DevilsAdvocate")) return [];
  const advocate = acting(world, state, "DevilsAdvocate", day);
  return advocate === null ? [] : [advocate];
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

/** Its one free death covers the gallows as well as the night. */
survivesExecutionRule(function aFoolWalksAwayOnce(world, state, day, seat) {
  if (!inBag(state, "Fool")) return [];
  return world.roleAt(seat, `D${day}`) === "Fool" ? [seat] : [];
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
  return [new Cause("Demon", DEMON, allSeats(state),
                    {capacity: 1, mustFire: true})];
});

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
                    {capacity: 1, mustFire: true})];
});

/** Poisons on one night, and that poison kills on the next.
 *
 * It starts a night earlier than any other Demon: on the first night it
 * only poisons. So the victim has to be the seat its poison was on, which
 * is a demand on a night already accounted for. */
causeRule(function aPukkaKillsWhatItPoisoned(world, state, night) {
  if (!inBag(state, "Pukka") || night < 2) return [];
  if (acting(world, state, "Pukka", night) === null) return [];
  return [new Cause("Demon", DEMON, state.aliveSet(`N${night - 1}`),
                    {capacity: 1, mustFire: true,
                     victimImpairedAt: night - 1})];
});

/** Two a night, and either can be aimed at somebody already dead, so the
 * table may only ever see one body. */
causeRule(function aShabalothKillsTwice(world, state, night) {
  if (!inBag(state, "Shabaloth") || night < 2) return [];
  if (acting(world, state, "Shabaloth", night) === null) return [];
  return [new Cause("Demon", DEMON, allSeats(state),
                    {capacity: 2, mustFire: true})];
});

/** It may choose nobody — and then it takes three the next night.
 *
 * Whether it chose nobody is not written down, so a night with no bodies
 * is read as it possibly having declined. Permissive rather than exact,
 * which errs towards keeping worlds rather than throwing them away. */
causeRule(function aPoKillsNoneOrThree(world, state, night) {
  if (!inBag(state, "Po") || night < 2) return [];
  if (acting(world, state, "Po", night) === null) return [];
  const quiet = !anyDiedAt(state, `N${night - 1}`);
  return [new Cause("Demon", DEMON, allSeats(state),
                    {capacity: quiet ? 3 : 1, mustFire: false})];
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
  if (acting(world, state, "Godfather", night) === null) return [];
  const day = `D${night - 1}`;
  const lost = Object.keys(state.deaths || {}).some(who =>
    state.diedAt(who).includes(day) &&
    world.teamAt(Number(who), day) === "outsider");
  if (!lost) return [];
  return [new Cause("Godfather", OTHER, allSeats(state),
                    {capacity: 1, mustFire: true})];
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
  if (!good.size) return [];
  return [new Cause("Moonchild", OTHER, good, {capacity: 1})];
});

/** Guessing wrong kills you, and nothing else.
 *
 * It reaches exactly one seat — its own — so it can never account for
 * anybody else's death. */
causeRule(function aGamblerMayLose(world, state, night) {
  if (!inBag(state, "Gambler") || night < 2) return [];
  const seat = acting(world, state, "Gambler", night);
  if (seat === null) return [];
  const guessed = state.infos.some(
    i => i.sourceRole === "Gambler" && i.night === night);
  if (!guessed) return [];               // no guess recorded, no risk
  return [new Cause("Gambler", OTHER, new Set([seat]), {capacity: 1})];
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
function livingBeside(state, seat, phase) {
  const alive = state.aliveSet(phase);
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

/** Both her living neighbours good, and neither of them can die.
 *
 * Whether they are good is exactly what is in question, so this depends
 * on the world being scored rather than on the board. Always on rather
 * than aimed: she picks nobody, so a neighbour who died means she was not
 * working. */
immunityRule(function aTeaLadyKeepsHerNeighbours(world, state, night, seat) {
  if (!inBag(state, "TeaLady")) return [];
  const phase = `N${night}`;
  const lady = world.findAt("TeaLady", phase);
  if (lady === null || !state.aliveSet(phase).has(lady)) return [];
  const around = livingBeside(state, lady, phase);
  if (!around.has(seat) || around.size < 2) return [];
  for (const p of around) if (world.evilAt(p, phase)) return [];
  return [shield("Tea Lady", {needs: lady})];
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
immunityRule(function anInnkeeperGuardsTwo(world, state, night) {
  if (!inBag(state, "Innkeeper") || night < 2) return [];
  const keeper = acting(world, state, "Innkeeper", night);
  if (keeper === null) return [];
  return [shield("Innkeeper", {needs: keeper, chosen: true})];
});

/** Choosing the Demon stops it waking at all, so nobody dies by it.
 *
 * Aimed rather than always on: it says nothing about a seat that did die,
 * only that it could have been the reason one did not. */
immunityRule(function anExorcistSendsTheDemonToBed(
    world, state, night, seat, kind) {
  if (!inBag(state, "Exorcist") || kind !== DEMON || night < 2) return [];
  const exorcist = acting(world, state, "Exorcist", night);
  if (exorcist === null) return [];
  return [shield("Exorcist", {needs: exorcist, chosen: true})];
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
  if (state.aliveSet(`N${night}`).has(seat)) return [];
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
  const price = hit => {
    if (hit === seat) return 0.6;        // the usual half of the coin
    return world.evilAt(hit, phase) ? PRIORS.SAILOR_ON_EVIL_PENALTY : 0.6;
  };
  return [new Source("Sailor", state.aliveSet(phase),
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
  if (!pickers.size) return [];
  return [new Source("Goon", pickers, {capacity: 1, cost: 1.0,
                                       repeatCost: 1.0})];
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
    const hit = world.findAt(info.role, phase);
    if (hit === null) continue;          // named somebody nobody is
    out.push(new Source("Courtier", new Set([hit]),
                        {capacity: 1, cost: 1.0, repeatCost: 1.0}));
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
  const executed = (state.executions || {})[night - 1];
  if (executed === undefined) return [];
  if (world.teamAt(executed, `D${night - 1}`) !== "minion") return [];
  const everyone = new Set(
    Array.from({length: state.nPlayers}, (_, i) => i).filter(p => p !== seat));
  return [new Source("Minstrel", everyone,
                     {capacity: everyone.size, cost: 1.0, repeatCost: 1.0})];
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
  return [new Source("Innkeeper", state.aliveSet(`N${night}`),
                     {capacity: 1, cost: 0.5, repeatCost: 0.5})];
});
