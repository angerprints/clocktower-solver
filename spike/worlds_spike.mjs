// A spike, not the port. It exists to answer one question before three
// thousand lines get translated: can JavaScript enumerate worlds fast
// enough for a phone to do this without a laptop in the room?
//
// So it carries only what the enumeration needs — the bag, the candidate
// lists, the backtracking search — with the character data hardcoded
// rather than read from a catalogue. Everything else is deliberately
// absent. If the numbers are good this becomes the seed of the real
// `worlds` module; if they are not, it is a day spent instead of a
// fortnight.
//
//     node spike/worlds_spike.mjs

const TEAM = {};
const put = (team, names) => names.forEach(n => (TEAM[n] = team));

// --- Trouble Brewing -------------------------------------------------
put("townsfolk", ["Washerwoman", "Librarian", "Investigator", "Chef",
  "Empath", "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin",
  "Slayer", "Soldier", "Mayor"]);
put("outsider", ["Butler", "Drunk", "Recluse", "Saint"]);
put("minion", ["Poisoner", "Spy", "ScarletWoman", "Baron"]);
put("demon", ["Imp"]);

// --- Bad Moon Rising -------------------------------------------------
put("townsfolk", ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
  "Innkeeper", "Gambler", "Gossip", "Courtier", "Professor", "Minstrel",
  "TeaLady", "Pacifist", "Fool"]);
put("outsider", ["Tinker", "Moonchild", "Goon", "Lunatic"]);
put("minion", ["Godfather", "DevilsAdvocate", "Assassin", "Mastermind"]);
put("demon", ["Zombuul", "Pukka", "Shabaloth", "Po"]);

// Characters whose holder was handed somebody else's token, and which
// teams that token can come from.
const BELIEVES = {Drunk: ["townsfolk"], Lunatic: ["demon"],
                  Marionette: ["townsfolk", "outsider"]};

// Characters that shift the bag, and how.
const SETUP_SHIFTS = {
  Baron: [{townsfolk: -2, outsider: 2}],
  Godfather: [{townsfolk: 1, outsider: -1}, {townsfolk: -1, outsider: 1}],
};

const SETUP = {
  5: [3, 0, 1, 1], 6: [3, 1, 1, 1], 7: [5, 0, 1, 1], 8: [5, 1, 1, 1],
  9: [5, 2, 1, 1], 10: [7, 0, 2, 1], 11: [7, 1, 2, 1], 12: [7, 2, 2, 1],
  13: [9, 0, 3, 1], 14: [9, 1, 3, 1], 15: [9, 2, 3, 1],
};

const TEAMS = ["townsfolk", "outsider", "minion", "demon"];

function makeScript(name, keys) {
  const by = t => keys.filter(k => TEAM[k] === t);
  return {
    name, keys,
    townsfolk: by("townsfolk"), outsiders: by("outsider"),
    minions: by("minion"), demons: by("demon"),
    modifiers: Object.fromEntries(
      keys.filter(k => SETUP_SHIFTS[k]).map(k => [k, SETUP_SHIFTS[k]])),
  };
}

const believesAnother = key => !!BELIEVES[key];

const LIST = {townsfolk: "townsfolk", outsider: "outsiders",
              minion: "minions", demon: "demons"};

function believedTokens(key, script) {
  const out = [];
  for (const team of BELIEVES[key] || [])
    for (const k of script[LIST[team]])
      if (!believesAnother(k) && !out.includes(k)) out.push(k);
  return out;
}

// Somebody who believes they are on the evil team bluffs the way the
// Demon would — a Lunatic is good, thinks it is the Demon, and lies
// accordingly. Leaving this out of the spike lost nine tenths of the
// Bad Moon Rising worlds, because a Lunatic claiming a Townsfolk is how
// an Outsider slot gets filled on a table where everybody claims one.
const thinksItIsEvil = key =>
  (BELIEVES[key] || []).some(t => t === "minion" || t === "demon");

// --- the bag ---------------------------------------------------------

function bags(nPlayers, script) {
  const base = Object.fromEntries(
    TEAMS.map((t, i) => [t, SETUP[nPlayers][i]]));
  let out = [[new Set(), base]];
  for (const [role, shifts] of Object.entries(script.modifiers)) {
    const grown = [];
    for (const [present, counts] of out) {
      grown.push([present, counts]);                 // it stayed out
      for (const shift of shifts) {
        const moved = {...counts};
        for (const [t, d] of Object.entries(shift)) moved[t] += d;
        grown.push([new Set([...present, role]), moved]);
      }
    }
    out = grown;
  }
  const room = Object.fromEntries(TEAMS.map(t =>
    [t, script[t === "townsfolk" ? "townsfolk"
             : t === "outsider" ? "outsiders"
             : t === "minion" ? "minions" : "demons"].length]));
  const seen = new Set(), kept = [];
  for (const [present, counts] of out) {
    if (TEAMS.reduce((s, t) => s + counts[t], 0) !== nPlayers) continue;
    if (TEAMS.some(t => counts[t] < 0 || counts[t] > room[t])) continue;
    const key = [...present].sort().join(",") + "|" +
                TEAMS.map(t => counts[t]).join(",");
    if (seen.has(key)) continue;
    seen.add(key);
    kept.push([present, counts]);
  }
  return kept;
}

// --- what a seat could be --------------------------------------------

function itself(key, script) {
  return believesAnother(key)
    ? believedTokens(key, script).map(tok => [key, tok])
    : [[key, null]];
}

function anything(script) {
  const out = [];
  for (const key of script.keys) {
    if (believesAnother(key))
      believedTokens(key, script).forEach(tok => out.push([key, tok]));
    else out.push([key, null]);
  }
  return out;
}

function candidates(claim, script, allowGoodLies = false) {
  const evil = script.minions.concat(script.demons);
  const believers = script.keys.filter(believesAnother);
  if (claim === null || claim === undefined || claim === "")
    return anything(script);

  const evilBluffs = evil.filter(k => !believesAnother(k)).map(k => [k, null]);
  script.keys.filter(thinksItIsEvil).forEach(k =>
    believedTokens(k, script).forEach(tok => evilBluffs.push([k, tok])));

  if (script.townsfolk.includes(claim)) {
    const out = itself(claim, script);
    believers.forEach(b => {
      if (believedTokens(b, script).includes(claim)) out.push([b, claim]);
    });
    if (allowGoodLies)
      script.outsiders.filter(r => !believesAnother(r))
        .forEach(r => out.push([r, null]));
    return out.concat(evilBluffs);
  }
  if (script.outsiders.includes(claim)) {
    const out = itself(claim, script);
    believers.forEach(b => {
      if (believedTokens(b, script).includes(claim)) out.push([b, claim]);
    });
    if (allowGoodLies)
      script.outsiders.filter(r => r !== claim && !believesAnother(r))
        .forEach(r => out.push([r, null]));
    return out.concat(evilBluffs);
  }
  if (evil.includes(claim)) return itself(claim, script);
  throw new Error(`${claim} is not on ${script.name}`);
}

// --- the search ------------------------------------------------------

function branches(nPlayers, claims, script) {
  const out = [];
  for (const [present, target] of bags(nPlayers, script)) {
    const cands = [];
    for (let i = 0; i < nPlayers; i++) {
      let opts = candidates(claims[i] ?? null, script);
      opts = opts.filter(([role]) =>
        !script.modifiers[role] || present.has(role));
      cands.push(opts);
    }
    const order = [...Array(nPlayers).keys()]
      .sort((a, b) => cands[a].length - cands[b].length);
    out.push({target, cands, order, required: present});
  }
  return out;
}

// Every legal assignment, handed to `emit` one at a time. The shape is a
// callback rather than a generator on purpose: generators cost about a
// third of the run time here, and the caller only ever scores and drops
// each world.
function eachWorld(nPlayers, claims, script, emit) {
  for (const {target, cands, order, required} of
       branches(nPlayers, claims, script)) {
    const roles = new Array(nPlayers).fill(null);
    const believes = new Array(nPlayers).fill(null);
    const used = new Set();
    const count = {townsfolk: 0, outsider: 0, minion: 0, demon: 0};

    const rec = k => {
      if (k === order.length) {
        for (const need of required) if (!used.has(need)) return;
        emit(roles, believes);
        return;
      }
      const i = order[k];
      for (const [role, belief] of cands[i]) {
        const team = TEAM[role];
        if (used.has(role)) continue;
        if (belief !== null && used.has(belief)) continue;
        if (count[team] >= target[team]) continue;

        used.add(role);
        if (belief !== null) used.add(belief);
        count[team] += 1;
        roles[i] = role; believes[i] = belief;

        rec(k + 1);

        roles[i] = null; believes[i] = null;
        count[team] -= 1;
        used.delete(role);
        if (belief !== null) used.delete(belief);
      }
    };
    rec(0);
  }
}

// --- the measurement -------------------------------------------------

const TB = makeScript("Trouble Brewing", [
  "Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
  "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin", "Slayer",
  "Soldier", "Mayor", "Butler", "Drunk", "Recluse", "Saint",
  "Poisoner", "Spy", "ScarletWoman", "Baron", "Imp"]);

const BMR = makeScript("Bad Moon Rising", [
  "Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper", "Gambler",
  "Gossip", "Courtier", "Professor", "Minstrel", "TeaLady", "Pacifist",
  "Fool", "Tinker", "Moonchild", "Goon", "Lunatic",
  "Godfather", "DevilsAdvocate", "Assassin", "Mastermind",
  "Zombuul", "Pukka", "Shabaloth", "Po"]);

const TB15 = ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
  "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin", "Slayer",
  "Soldier", "Mayor", "Recluse", "Saint"];
const BMR15 = ["Grandmother", "Sailor", "Chambermaid", "Exorcist",
  "Innkeeper", "Gambler", "Gossip", "Courtier", "Professor", "Minstrel",
  "TeaLady", "Pacifist", "Fool", "Tinker", "Moonchild"];

function time(tag, script, seats, n, build) {
  const claims = {};
  seats.slice(0, n).forEach((r, i) => (claims[i] = r));
  let count = 0, checksum = 0;
  const started = process.hrtime.bigint();
  eachWorld(n, claims, script, (roles, believes) => {
    count += 1;
    // A world object per result, because the solver builds one to score
    // — counting alone would flatter the number. Not kept, because the
    // solver does not keep them either, and nine million of them is how
    // this spike first ran out of memory.
    if (build) {
      const world = {roles: roles.slice(), believes: believes.slice()};
      checksum += world.roles.length;      // so it cannot be optimised away
    }
  });
  const secs = Number(process.hrtime.bigint() - started) / 1e9;
  console.log(`${tag.padEnd(16)}${String(n).padStart(3)} seats  ` +
    `${count.toLocaleString().padStart(11)} worlds  ` +
    `${secs.toFixed(2).padStart(6)}s  ` +
    `${(count / secs / 1000).toFixed(0).padStart(7)}k/s`);
  return count;
}

console.log("building a world object for each result\n");
for (const [tag, script, seats] of [["Trouble Brewing", TB, TB15],
                                    ["Bad Moon Rising", BMR, BMR15]])
  for (const n of [9, 12, 15]) time(tag, script, seats, n, true);

console.log("\ncounting only, to show what the objects cost\n");
for (const [tag, script, seats] of [["Trouble Brewing", TB, TB15],
                                    ["Bad Moon Rising", BMR, BMR15]])
  for (const n of [9, 12, 15]) time(tag, script, seats, n, false);
