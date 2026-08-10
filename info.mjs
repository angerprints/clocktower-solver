// Every kind of reading, and what makes each one true in a world.
//
// A reading knows which night it belongs to, who said it out loud, and
// which character produced it. `holds` answers the only question that
// matters: is this true in that world?
//
// Two things a reading does *not* decide. Whether the speaker actually
// held the character — that is the claim gate, and it lives in the
// solver. And whether they were impaired — poison is posited only when a
// statement would otherwise be false, which cannot be known until the
// statement has been checked.

import {CHARACTERS} from "./catalogue.mjs";
import {TEAM, evilRegistrations, registersAsRole} from "./roles.mjs";
import {possibleCounts} from "./waking.mjs";

const DEMONS = new Set(Object.entries(TEAM)
  .filter(([, team]) => team === "demon").map(([key]) => key));

const registersTownsfolk = role =>
  TEAM[role] === "townsfolk" || role === "Spy";

/** Every value "how many of these are evil" could take.
 *
 * Asked of a moment, because on scripts where somebody can change side
 * the answer is not the same all game.
 */
export function possibleEvilCounts(world, players, phase) {
  let sums = new Set([0]);
  for (const p of players) {
    const options = evilRegistrations(world.roleAt(p, phase),
                                      world.alignmentAt(p, phase));
    const grown = new Set();
    for (const so_far of sums)
      for (const evil of options) grown.add(so_far + (evil ? 1 : 0));
    sums = grown;
  }
  return sums;
}

/** The nearest living seat each way, as the Empath sees it.
 *
 * The Demon kills before the Empath wakes, so tonight's victim is
 * already gone and the count reads past them.
 */
export function livingNeighbours(state, night, p) {
  const phase = `N${night}`;
  const alive = state.aliveAt(phase)
    .filter(q => !state.diedAt(q).includes(phase));
  const at = alive.indexOf(p);
  if (at === -1 || alive.length < 3) return alive.filter(x => x !== p);
  return [alive[(at - 1 + alive.length) % alive.length],
          alive[(at + 1) % alive.length]];
}

class Info {
  constructor(fields) {
    this.night = 1;
    this.player = 0;
    // How far you believe the reading itself, separately from whoever
    // announced it. This is the piece that matters for readings
    // attributed to a character nobody has claimed.
    this.trust = 0;
    Object.assign(this, fields);
  }

  /** A fact about the world rather than a claim.
   *
   * A claim only binds when the speaker really holds that character. A
   * hard fact binds in every world and cannot be excused by poison.
   */
  hard() { return false; }

  /** Whose information this actually is.
   *
   * Usually the speaker — but handing your reading to somebody else to
   * share is ordinary play, so when the speaker claims a different
   * character and exactly one seat claims the matching one, it is
   * attributed there instead. With nobody to attribute it to, null means
   * "whoever turns out to hold this", so the solver fits the statement
   * onto the unclaimed seats rather than onto the speaker.
   */
  sourceSeat(state) {
    if (state.claims[this.player] === this.constructor.sourceRole)
      return this.player;
    const holders = Object.entries(state.claims)
      .filter(([, role]) => role === this.constructor.sourceRole)
      .map(([seat]) => Number(seat));
    return holders.length === 1 ? holders[0] : null;
  }

  get sourceRole() { return this.constructor.sourceRole; }

  holds() { throw new Error("not implemented"); }
}

const define = (name, sourceRole, holds, extra = {}) => {
  const cls = class extends Info {};
  Object.defineProperty(cls, "name", {value: name});
  cls.sourceRole = sourceRole;
  cls.prototype.type = name;
  cls.prototype.holds = holds;
  Object.assign(cls.prototype, extra);
  return cls;
};

// --- the first night ------------------------------------------------

export const Washerwoman = define("Washerwoman", "Washerwoman",
  function (w) {
    return registersAsRole(w.roleAt(this.a, "N1"), this.role) ||
           registersAsRole(w.roleAt(this.b, "N1"), this.role);
  });

/** Could this character avoid being counted as an Outsider?
 *
 * True for everybody who is not one, and for an Outsider that may
 * register as another team. The Butler, the Drunk and the Saint have no
 * such option, so one of those in play means the Librarian is shown
 * somebody.
 */
const canShowAsSomethingElse = role =>
  TEAM[role] !== "outsider" ||
  CHARACTERS[role].registers.some(team => team !== "outsider");

export const Librarian = define("Librarian", "Librarian",
  function (w) {
    if (this.a === null || this.a === undefined || this.a === "")
      // Not "there are no Outsiders" — "none of them showed as one". A
      // Recluse registers as a Minion or the Demon whenever the
      // Storyteller likes, so a Librarian can honestly be told nobody
      // with a Recluse sitting right there.
      return w.roles.every((_r, p) =>
        canShowAsSomethingElse(w.roleAt(p, "N1")));
    return registersAsRole(w.roleAt(this.a, "N1"), this.role) ||
           registersAsRole(w.roleAt(this.b, "N1"), this.role);
  });

export const Investigator = define("Investigator", "Investigator",
  function (w) {
    return registersAsRole(w.roleAt(this.a, "N1"), this.role) ||
           registersAsRole(w.roleAt(this.b, "N1"), this.role);
  });

export const Chef = define("Chef", "Chef",
  function (w) {
    const n = w.roles.length;
    const options = [];
    for (let p = 0; p < n; p++)
      options.push(evilRegistrations(w.roleAt(p, "N1"),
                                     w.alignmentAt(p, "N1")));
    // Every way the table could read, and how many neighbouring pairs
    // of evil each one gives.
    let combos = [[]];
    for (const opts of options) {
      const grown = [];
      for (const so_far of combos)
        for (const evil of opts) grown.push([...so_far, evil]);
      combos = grown;
    }
    for (const combo of combos) {
      let pairs = 0;
      for (let i = 0; i < n; i++)
        if (combo[i] && combo[(i + 1) % n]) pairs += 1;
      if (pairs === this.count) return true;
    }
    return false;
  });

// --- every night ------------------------------------------------------

export const Empath = define("Empath", "Empath",
  function (w, s, _rh, seat = null) {
    const who = seat === null ? this.player : seat;
    // Killed before they could wake: there is no reading to check.
    if (s.diedAt(who).includes(`N${this.night}`)) return true;
    const nb = livingNeighbours(s, this.night, who);
    return possibleEvilCounts(w, nb, `N${this.night}`).has(this.count);
  });

export const FortuneTeller = define("FortuneTeller", "FortuneTeller",
  function (w, _s, rh) {
    const pair = [this.a, this.b];
    const phase = `N${this.night}`;
    // Looking for the Demon specifically, not for evil — so a Goon that
    // has turned is nothing to it.
    const hardDemon = pair.includes(w.demonAt(phase));
    const recluse = pair.some(x => w.roleAt(x, phase) === "Recluse");
    const herring = pair.includes(rh);
    if (this.yes) return hardDemon || recluse || herring;
    // A "no" means no actual Demon and not the red herring. The Recluse
    // *may* register as good, so it does not interfere.
    return !hardDemon && !herring;
  });

export const Undertaker = define("Undertaker", "Undertaker",
  function (w, s) {
    // Only an execution that killed somebody gives the Undertaker
    // anything, and the character they held when it happened is not the
    // character they were dealt if the Demon changed hands.
    const day = this.night - 1;
    if (s.executionDeath(day) !== this.target) return false;
    return registersAsRole(w.roleAt(this.target, `D${day}`), this.role);
  });

export const Ravenkeeper = define("Ravenkeeper", "Ravenkeeper",
  function (w) {
    return registersAsRole(w.roleAt(this.target, `N${this.night}`), this.role);
  });

// --- Bad Moon Rising ---------------------------------------------------

/** Shown a good player and the character they hold.
 *
 * That seat is the grandchild from then on — a token the Storyteller puts
 * down, not a character anybody holds. Whether the reading was true or
 * invented, the token goes on the seat she was shown.
 */
export const GrandmotherInfo = define("GrandmotherInfo", "Grandmother",
  function (w) {
    const shown = w.roleAt(this.target, "N1");
    if (!registersAsRole(shown, this.role)) return false;
    // She is shown a *good* player, and the Spy can be one of those.
    return !w.evilAt(this.target, "N1") || shown === "Spy";
  });

/** Named a player and guessed their character. Wrong means they die.
 *
 * Which way this cuts depends on whether they are still standing, so the
 * row reads the deaths rather than carrying the answer. A Gambler who
 * died guessed wrong; one who lived guessed right — or was impaired,
 * which the plan can pay for.
 */
export const GamblerGuess = define("GamblerGuess", "Gambler",
  function (w, s, _rh, seat = null) {
    const who = seat === null ? this.player : seat;
    const right = registersAsRole(w.roleAt(this.target, `N${this.night}`),
                                  this.role);
    return s.diedAt(who).includes(`N${this.night}`) ? !right : right;
  });

/** Named a character, not a player. Once per game.
 *
 * Naming a character nobody holds still spends the ability and does
 * nothing at all, which is why this row constrains nothing by itself —
 * its whole effect is the drunkenness it licenses.
 */
export const CourtierChoice = define("CourtierChoice", "Courtier",
  function () { return true; });

// --- things the table watched -----------------------------------------

/** Somebody nominated the seat claiming Virgin. `night` is the day.
 *
 * Both outcomes carry information. A trigger is a death everyone saw: the
 * Virgin is real, sober and healthy, and the nominator registered as a
 * Townsfolk. A quiet nomination only bites in worlds where that seat
 * really is the Virgin — and then the nominator was no Townsfolk, or the
 * Virgin was poisoned.
 */
export const VirginNomination = define("VirginNomination", "Virgin",
  function (w) {
    const phase = `D${this.night}`;
    if (this.triggered)
      return w.roleAt(this.player, phase) === "Virgin" &&
             registersTownsfolk(w.roleAt(this.nominator, phase));
    return !registersTownsfolk(w.roleAt(this.nominator, phase));
  },
  {
    hard() { return this.triggered; },
    sourceSeat() { return this.player; },
  });

/** `night` is the day on which the shot was fired. */
export const SlayerShot = define("SlayerShot", "Slayer",
  function (w) {
    const phase = `D${this.night}`;
    const t = w.roleAt(this.target, phase);
    if (this.died)
      return w.roleAt(this.player, phase) === "Slayer" &&
             (DEMONS.has(t) || t === "Recluse");
    // A shot that did nothing is only evidence if a real Slayer fired it,
    // and that is the usual claim gate's business.
    return !DEMONS.has(t);
  },
  {
    // A shot that killed somebody is not a story anyone can tell — a body
    // hit the floor. Nothing but a real, sober, healthy Slayer hitting
    // the Demon can do that, so it binds in every world.
    hard() { return this.died; },
    // A shot happens in the open, so the shooter is never in doubt and
    // there is nothing to relay.
    sourceSeat() { return this.player; },
  });

/** Two living players, and how many of them woke tonight.
 *
 * For their *own* ability. A Demon woken because the Exorcist chose it
 * was woken to be told something, not to do anything, and does not count
 * — which is why the answer can be a range rather than a number.
 */
export const ChambermaidInfo = define("ChambermaidInfo", "Chambermaid",
  function (w, s) {
    return possibleCounts(w, s, [this.a, this.b], this.night).has(this.count);
  });

export const KINDS = {
  Washerwoman, Librarian, Investigator, Chef, Empath, FortuneTeller,
  Undertaker, Ravenkeeper, GrandmotherInfo, ChambermaidInfo, GamblerGuess,
  CourtierChoice, VirginNomination, SlayerShot,
};

/** Build a reading from the shape the page posts. */
export function makeInfo(row) {
  const Kind = KINDS[row.type];
  if (!Kind) throw new Error(`Unknown kind of reading: ${row.type}`);
  const {type, ...fields} = row;
  return new Kind(fields);
}
