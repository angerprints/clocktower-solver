// The two algorithms in the registries, run against synthetic rules.
//
//     node js/dump_rules.mjs
//
// The *character* rules live in the solver, which is the next phase, so
// the registries are empty at this point. What can be checked now is the
// machinery they feed: whether an impairment plan finds the same cheapest
// arrangement, and whether a night's deaths get the same accounts.
//
// So both implementations register the same made-up rules — a poisoner
// that reaches the living, a soldier that cannot be demon-killed, a monk
// that guards somebody else, a gossip that need not fire, an assassin
// nothing stops, a grandmother whose grandchild drags her along — and the
// answers are compared. Made up, but shaped exactly like the real ones,
// and between them they reach every branch.

import {DEMON, OTHER, Cause, IMMUNITY_RULES, IMPLICATION_RULES, CAUSE_RULES,
        causeRule, explainNight, implication, implicationRule, immunityRule,
        shield, shieldsOn} from "./deaths.mjs";
import {Source, planNight} from "./impairment.mjs";
import {GameState} from "./state.mjs";
import * as scripts from "./scripts.mjs";
import {World} from "./worlds.mjs";

const TB = scripts.TROUBLE_BREWING;
const TB9 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
             "FortuneTeller", "Undertaker", "Recluse", "Saint"];

// --- the plan --------------------------------------------------------
// A spread of sources: one free and unavoidable, one cheap, one dear, one
// that reaches two seats at once, one whose price depends on the seat.

const sources = {
  believer: new Source("believer", [3], {capacity: 1}),
  poisoner: new Source("Poisoner", [0, 1, 2, 3, 4],
                       {capacity: 1, cost: 0.35, repeatCost: 0.7}),
  sailor: new Source("Sailor", [1, 5],
                     {capacity: 1, cost: seat => (seat === 1 ? 0.5 : 0.15)}),
  innkeeper: new Source("Innkeeper", [6, 7], {capacity: 2, cost: 0.5}),
  courtier: new Source("Courtier", [8], {capacity: 1, cost: 1.0}),
};

const plans = {};
const tryPlan = (name, use, required, forbidden, previous = {}) => {
  const got = planNight(use.map(k => sources[k]), required, forbidden,
                        previous);
  plans[name] = got === null ? null
    : {cost: Number(got.cost.toFixed(9)), hits: got.hits};
};

tryPlan("nothing needed", ["poisoner"], [], []);
tryPlan("one seat, one source", ["poisoner"], [0], []);
tryPlan("one seat, out of reach", ["poisoner"], [7], []);
tryPlan("one seat, repeated", ["poisoner"], [0], [], {Poisoner: 0});
tryPlan("one seat, a different one", ["poisoner"], [0], [], {Poisoner: 1});
tryPlan("free source covers it", ["believer", "poisoner"], [3], []);
tryPlan("free source reaches a forbidden seat", ["believer"], [], [3]);
tryPlan("required and forbidden at once", ["poisoner"], [0], [0]);
tryPlan("two seats, two sources", ["poisoner", "sailor"], [0, 5], []);
tryPlan("two seats, one source", ["poisoner"], [0, 1], []);
tryPlan("two seats, one source with room", ["innkeeper"], [6, 7], []);
tryPlan("the cheaper arrangement wins", ["poisoner", "sailor"], [1], []);
tryPlan("price depends on the seat", ["sailor"], [5], []);
tryPlan("price depends on the seat, the other one", ["sailor"], [1], []);
tryPlan("three seats, three sources",
        ["poisoner", "sailor", "innkeeper"], [0, 5, 6], []);
tryPlan("three seats, not enough reach",
        ["poisoner", "sailor"], [0, 5, 8], []);
tryPlan("a forbidden seat blocks an arrangement",
        ["poisoner", "sailor"], [1], [0]);
tryPlan("a free source that costs nothing to use",
        ["courtier"], [8], []);

// --- the night accounting --------------------------------------------
// Rules shaped like the real ones, registered on both sides identically.

const board = (opts = {}) => new GameState({
  nPlayers: 9, script: TB,
  claims: Object.fromEntries(TB9.map((r, i) => [i, r])), ...opts});

const world = new World(
  ["Washerwoman", "Librarian", "Soldier", "Monk", "Empath", "Gossip",
   "Undertaker", "Poisoner", "Imp"], new Array(9).fill(null));

causeRule(function theDemonKills(w, s, night) {
  if (night < 2) return [];
  return [new Cause("Demon", DEMON, s.aliveSet(`N${night}`),
                    {capacity: 1, mustFire: true})];
});

causeRule(function aGossipMayKill(w, s, night) {
  if (w.find("Gossip") === null || night < 2) return [];
  return [new Cause("Gossip", OTHER, new Set([...Array(9).keys()]),
                    {capacity: 1, cost: 0.4})];
});

causeRule(function anAssassinKillsThroughAnything(w, s, night) {
  if (!s.script.keys.includes("Assassin") || night < 3) return [];
  return [new Cause("Assassin", OTHER, new Set([...Array(9).keys()]),
                    {capacity: 1, cost: 0.25, unstoppable: true})];
});

immunityRule(function theSoldierCannotBeDemonKilled(w, s, night, seat, kind) {
  if (kind !== DEMON) return [];
  return w.roleAt(seat, `N${night}`) === "Soldier"
    ? [shield("Soldier", {needs: seat})] : [];
});

immunityRule(function theMonkGuardsAgainstTheDemon(w, s, night, seat, kind) {
  if (kind !== DEMON || night < 2) return [];
  const monk = w.findAt("Monk", `N${night}`);
  if (monk === null || monk === seat) return [];
  return [shield("Monk", {needs: monk, chosen: true})];
});

immunityRule(function theDeadCannotDieAgain(w, s, night, seat) {
  return s.aliveSet(`N${night}`).has(seat)
    ? [] : [shield("already dead", {cost: 0.45})];
});

implicationRule(function aGrandmotherGrieves(w, s, night, victim, kind) {
  if (kind !== DEMON) return [];
  for (const info of s.infos)
    if (info.sourceRole === "Grandmother" && info.target === victim)
      return [implication(info.player, info.player)];
  return [];
});

const rounded = accounts => accounts.map(a => ({
  cost: Number(a.cost.toFixed(9)),
  impaired: [...a.impaired].sort((x, y) => x - y),
  working: [...a.working].sort((x, y) => x - y),
  earlier: Object.fromEntries(Object.entries(a.earlier || {})
    .map(([n, v]) => [n, [...v].sort((x, y) => x - y)])),
}));

const nights = {};
const tryNight = (name, night, died, opts = {}) => {
  nights[name] = rounded(explainNight(world, board(opts), night, died));
};

tryNight("nobody died on night one", 1, []);
tryNight("one body", 2, [0]);
tryNight("the Soldier died", 2, [2]);
tryNight("the Monk died", 2, [3]);
tryNight("a quiet night", 2, []);
tryNight("two bodies", 2, [0, 1]);
tryNight("three bodies", 2, [0, 1, 4]);
tryNight("a body already dead", 3, [0], {deaths: {0: "N2"}});
tryNight("a quiet night with somebody already gone", 3, [],
         {deaths: {0: "N2"}});

// The grandchild link: one kill, two bodies — and the same link the
// other way, where she is still standing and something has to explain it.
const granny = {infos: [{sourceRole: "Grandmother", player: 4, target: 1,
                         night: 1}]};
tryNight("the grandchild alone", 2, [1], granny);
tryNight("the grandchild and the grandmother", 2, [1, 4], granny);
tryNight("the grandmother alone", 2, [4], granny);

// And the unstoppable cause, which goes through a shield nothing else can.
const withAssassin = scripts.fromIds("TB and an Assassin",
  [...TB.keys, "assassin"]);
const assassinBoard = new GameState({
  nPlayers: 9, script: withAssassin,
  claims: Object.fromEntries(TB9.map((r, i) => [i, r]))});
nights["the Soldier died with an Assassin about"] =
  rounded(explainNight(world, assassinBoard, 3, [2]));

// --- what the registries hold ----------------------------------------
const registry = {
  causes: CAUSE_RULES.map(f => f.name),
  shields: IMMUNITY_RULES.map(f => f.name),
  implications: IMPLICATION_RULES.map(f => f.name),
  shieldsOnASoldier: shieldsOn(world, board(), 2, 2, DEMON)
    .map(s => [s.by, s.needs, s.cost, s.chosen]),
  shieldsOnSomebodyElse: shieldsOn(world, board(), 2, 0, DEMON)
    .map(s => [s.by, s.needs, s.cost, s.chosen]),
  shieldsAgainstOther: shieldsOn(world, board(), 2, 2, OTHER)
    .map(s => [s.by, s.needs, s.cost, s.chosen]),
};

process.stdout.write(JSON.stringify({plans, nights, registry}, null, 1) + "\n");
