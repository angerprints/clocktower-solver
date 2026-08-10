// What killed somebody, not merely that they died.
//
// Trouble Brewing only ever kills at night one way, so "died at night"
// and "died by the Demon" were the same sentence. They are not the same
// sentence. A Soldier cannot be killed by the Demon and can be killed by
// a Gossip, an Assassin or a Godfather without any trouble at all. So a
// death is attributed to a *cause*, and what a character is safe from is
// a question about the cause rather than about the night.
//
// Protection is not a property of the night either. The Monk guards
// against the Demon; the Innkeeper guards against everything, so a
// Grandmother's grief and a Gambler's bad guess are stopped by one and
// not the other.

export const DEMON = "demon";     // the Demon's own kill
export const OTHER = "other";     // anything else that kills at night

/** Something that can kill on a given night.
 *
 * `kind` is what sort of death it is — the Soldier's protection reads
 * "safe from the Demon", so it turns on this and not on the character
 * doing the killing. `mustFire` is whether it happens whether or not
 * anybody wants it to: the Demon kills every night, so a night where
 * nobody died is a night something stopped it, while a Gossip only kills
 * when it said something true and a quiet night owes it nothing.
 */
export class Cause {
  constructor(name, kind, seats, {
    capacity = 1, cost = 1.0, mustFire = false, unstoppable = false,
    victimImpairedAt = null,
  } = {}) {
    this.name = name;
    this.kind = kind;
    this.seats = seats instanceof Set ? seats : new Set(seats);
    this.capacity = capacity;
    this.cost = cost;
    this.mustFire = mustFire;
    // Does anything stop it? An Assassin kills "even if they could not",
    // which overrides every shield there is. Nothing else in the game
    // does this, and a seat killed this way tells you nothing about
    // whether its protection was working.
    this.unstoppable = unstoppable;
    // Some kills are the far end of something that started earlier. A
    // Pukka poisons on one night and the poison kills on the next, so
    // the victim has to have been the one it poisoned — a demand on a
    // night that has already been explained.
    this.victimImpairedAt = victimImpairedAt;
  }
}

/** A reason somebody could not have died that way.
 *
 * `needs` is the seat whose ability had to be working — a Soldier
 * protects itself, a Monk protects somebody else. The plan is then asked
 * to leave that seat unimpaired, and if it cannot, the protection did not
 * happen and the death is back on the table.
 *
 * `chosen` marks a shield somebody had to aim. A Soldier is safe every
 * night whether anybody likes it or not, so a Soldier who died must have
 * been impaired. A Monk picks one player a night, so a death only ever
 * means it guarded somebody else — it implies nothing about the victim.
 */
export const shield = (by, {needs = null, cost = 1.0, chosen = false} = {}) =>
  ({by, needs, cost, chosen});

/** A death that follows from another one.
 *
 * `seat` is who else goes; `needs` is the seat whose ability makes it
 * happen, which has to have been working — a poisoned Grandmother
 * grieves nobody.
 *
 * What makes this awkward is that the thing linking them is usually a
 * marker rather than a character. The grandchild is not a character
 * anybody holds; it is a token the Storyteller put on a seat. So a rule
 * reads the board, including the ledger, rather than the roles.
 */
export const implication = (seat, needs) => ({seat, needs});

export const CAUSE_RULES = [];
export const IMMUNITY_RULES = [];
export const IMPLICATION_RULES = [];

export const causeRule = fn => (CAUSE_RULES.push(fn), fn);
export const immunityRule = fn => (IMMUNITY_RULES.push(fn), fn);
export const implicationRule = fn => (IMPLICATION_RULES.push(fn), fn);

export function causesOn(world, state, night) {
  const out = [];
  for (const rule of CAUSE_RULES) out.push(...rule(world, state, night));
  return out;
}

/** Every reason this seat could have survived that kind of death. */
export function shieldsOn(world, state, night, seat, kind) {
  const out = [];
  for (const rule of IMMUNITY_RULES) {
    const got = rule(world, state, night, seat, kind);
    if (got && got.length) out.push(...got);
  }
  return out;
}

export function implicationsOf(world, state, night, victim, kind) {
  const out = [];
  for (const rule of IMPLICATION_RULES)
    out.push(...rule(world, state, night, victim, kind));
  return out;
}

/** Every way of splitting the bodies into aimed-at and consequent. */
function subsets(items) {
  let out = [new Set()];
  for (const item of items)
    out = out.concat(out.map(chosen => new Set([...chosen, item])));
  return out;
}

const setKey = s => [...s].sort((a, b) => a - b).join(",");

/** How the night's deaths could have come about.
 *
 * Returns accounts of {cost, impaired, working, earlier} — what each
 * costs, which seats it needs impaired, which working, and any demand it
 * makes on a night already explained. Empty means no account fits and the
 * world is impossible.
 *
 * Not every body needs a cause of its own. A Grandmother dies because
 * her grandchild was killed, so one Demon kill can leave two bodies — and
 * the same link runs the other way, which is where the deduction is.
 */
export function explainNight(world, state, night, died, blame = false) {
  const causes = causesOn(world, state, night);
  const bodies = [...died].sort((a, b) => a - b);
  if (!causes.length)
    return bodies.length ? []
      : [{cost: 1.0, impaired: new Set(), working: new Set(), earlier: {}}];

  const out = [];
  // With nothing on the script that drags a second death along, every
  // body was aimed at and there is only the one split to try.
  const splits = IMPLICATION_RULES.length ? subsets(bodies)
                                          : [new Set(bodies)];
  for (const picked of splits) {
    const directly = bodies.filter(v => picked.has(v));
    const followed = bodies.filter(v => !picked.has(v));
    out.push(...accountFor(world, state, night, causes, directly, followed,
                           blame));
  }
  if (blame) return out;

  const seen = new Set(), unique = [];
  for (const got of out) {
    const key = [
      got.cost.toFixed(9), setKey(got.impaired), setKey(got.working),
      Object.keys(got.earlier).sort()
        .map(n => `${n}:${setKey(got.earlier[n])}`).join(";"),
    ].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(got);
  }
  unique.sort((a, b) => b.cost - a.cost);
  return unique;
}

/** One split: these were aimed at, those followed from them. */
function accountFor(world, state, night, causes, directly, followed, blame) {
  const zero = {};
  for (const c of causes) zero[c.name] = 0;
  let accounts = [{cost: 1.0, impaired: new Set(), working: new Set(),
                   used: zero, chain: [], earlier: {}}];

  for (const victim of directly) {
    const grown = [];
    for (const acc of accounts) {
      for (const cause of causes) {
        if (!cause.seats.has(victim)) continue;
        if (acc.used[cause.name] >= cause.capacity) continue;
        // A shield that was always there has to have failed, and that
        // means whatever provided it was impaired. A shield somebody had
        // to aim says nothing: they aimed elsewhere. Unless nothing could
        // have stopped this at all — in which case no shield has anything
        // to answer for, including the one saying you cannot kill a
        // corpse, which still holds because a corpse is not a kill.
        const blocked = shieldsOn(world, state, night, victim, cause.kind)
          .filter(s => !s.chosen && (!cause.unstoppable || s.needs === null));
        if (blocked.some(s => s.needs === null)) continue;

        const earlier = {};
        for (const [k, v] of Object.entries(acc.earlier)) earlier[k] = new Set(v);
        if (cause.victimImpairedAt !== null) {
          const at = cause.victimImpairedAt;
          if (!earlier[at]) earlier[at] = new Set();
          earlier[at].add(victim);
        }
        const impaired = new Set(acc.impaired);
        for (const s of blocked) impaired.add(s.needs);
        grown.push({
          cost: acc.cost * cause.cost,
          impaired,
          working: new Set(acc.working),
          used: {...acc.used, [cause.name]: acc.used[cause.name] + 1},
          chain: [...acc.chain, [victim, cause.kind, cause.name]],
          earlier,
        });
      }
    }
    accounts = grown;
    if (!accounts.length) return [];
  }

  // What follows from those deaths, and whether the board agrees.
  let settled = [];
  for (const acc of accounts) {
    const implied = [];
    for (const [victim, kind] of acc.chain)
      implied.push(...implicationsOf(world, state, night, victim, kind));

    let options = [{cost: acc.cost, impaired: new Set(acc.impaired),
                    working: new Set(acc.working)}];
    for (const hit of implied) {
      const grown = [];
      for (const o of options) {
        if (followed.includes(hit.seat) || o.impaired.has(hit.seat))
          // It happened, and whatever caused it was working.
          grown.push({cost: o.cost, impaired: o.impaired,
                      working: new Set([...o.working, hit.needs])});
        else
          // It did not happen, so whatever would have caused it was not.
          grown.push({cost: o.cost,
                      impaired: new Set([...o.impaired, hit.needs]),
                      working: new Set(o.working)});
      }
      options = grown;
    }

    for (const o of options) {
      const covered = new Set(implied.filter(h => !o.impaired.has(h.needs))
                                     .map(h => h.seat));
      if (followed.some(v => !covered.has(v))) continue;  // a body unaccounted
      if ([...o.impaired].some(s => o.working.has(s))) continue;  // both at once
      if (blame) {
        const who = {};
        for (const [victim, , name] of acc.chain) who[victim] = name;
        for (const v of followed) who[v] = "followed on";
        settled.push({...o, used: acc.used, who});
      } else {
        settled.push({...o, used: acc.used, earlier: acc.earlier});
      }
    }
  }

  if (blame)
    return settled.map(({cost, impaired, working, who}) =>
      ({cost, impaired, working, who}));

  // Anything that fires whether or not it is wanted, and killed nobody,
  // was stopped — and something had to do the stopping.
  for (const cause of causes) {
    if (!cause.mustFire) continue;
    const grown = [];
    for (const acc of settled) {
      if (acc.used[cause.name] > 0) {
        grown.push(acc);          // it did the killing; nothing to explain
        continue;
      }
      for (const target of [...cause.seats].sort((a, b) => a - b)) {
        for (const s of shieldsOn(world, state, night, target, cause.kind)) {
          if (s.needs !== null && acc.impaired.has(s.needs)) continue;
          grown.push({
            cost: acc.cost * s.cost,
            impaired: new Set(acc.impaired),
            working: s.needs === null ? new Set(acc.working)
                                      : new Set([...acc.working, s.needs]),
            used: acc.used,
            earlier: acc.earlier,
          });
        }
      }
    }
    settled = grown;
    if (!settled.length) return [];
  }

  return settled.map(({cost, impaired, working, earlier}) =>
    ({cost, impaired, working, earlier}));
}
