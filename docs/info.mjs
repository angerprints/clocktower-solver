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
import {TEAM, evilRegistrations, isEvil, isReallyRole, registersAsRole} from "./roles.mjs";
import {sourcesOn} from "./impairment.mjs";
import {phaseIndex} from "./phases.mjs";
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
    // A Philosopher speaking a reading it gained is not relaying — it is
    // the source. Without this the row is handed to whoever claims that
    // character, and the Philosopher's own information ends up judged
    // against a seat that never said it.
    const took = state.philosophies()[this.player];
    if (took && took[0] === this.constructor.sourceRole &&
        phaseIndex(`N${this.night}`) >= phaseIndex(took[1]))
      return this.player;
    const holders = Object.entries(state.claims)
      .filter(([, role]) => role === this.constructor.sourceRole)
      .map(([seat]) => Number(seat));
    return holders.length === 1 ? holders[0] : null;
  }

  /** Is this row's content actually checked?
   *
   * Nearly always. The exceptions are rows that are *kept* rather than
   * solved — a Savant's pair, an Artist's question — and the
   * Mathematician on a script whose droison sources are not all built.
   *
   * It matters because those rows answer `holds` with true by default,
   * and under a Vortox "true" is a claim: it would mean the Vortox was
   * not working. A row that says nothing must go on saying nothing.
   */
  weighed() { return true; }

  /** Is this row a *choice* the seat made, rather than information?
   *
   * A Vortox makes Townsfolk abilities yield false information — and a
   * choice is not information. Nobody told a Philosopher what it took.
   * The consequences still land: a Philosopher that took the Town Crier
   * gets that ability and *that* reading is inverted.
   */
  get isAChoice() { return !!this.constructor.isAChoice; }

  /** Does a Vortox reach this row?
   *
   * **A Vortox falsifies information roles and nothing else.** Asking
   * that character by character got it wrong twice — a Philosopher's
   * choice was inverted when nothing had told it anything, and a Snake
   * Charmer's swap was flipped so a charmer claimed to have swapped with
   * a seat it never touched. So it is one question, answered here.
   */
  /** Seats this reading needed to *misregister* to hold.
   *
   * **A droisoned character cannot misregister.** A Storyteller chooses
   * freely what a droisoned *information* role yields, because the
   * information is arbitrary — but registration is a plain ability, and
   * a plain ability simply does not function. A poisoned Recluse is a
   * Recluse and shows as one.
   *
   * `holds` cannot decide this: whether a seat was droisoned is chosen
   * by the impairment plan, which settles afterwards. So a row says what
   * it leaned on, and those seats are forbidden from being droisoned
   * that night.
   */
  leanedOn() { return []; }

  isInformation(state) {
    return !this.isAChoice && this.weighed(state);
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

/** Did this seat have to misregister to match what it was shown as?
 *
 * True only when it is *not* that character and could show as one. A
 * seat that really is what it was called leaned on nothing.
 */
const misregistered = (w, seat, phase, claimed) => {
  if (seat === null || seat === undefined) return false;
  const actual = w.roleAt(seat, phase);
  return actual !== claimed && registersAsRole(actual, claimed);
};

/** Whether one of the pair really *is* that character.
 *
 * Legality allows registration; truth does not. A Spy shown as the
 * Slayer is still a Spy, so the reading is false — and a Vortox may
 * produce it freely, because falsifying is exactly its job.
 */
const pairIsTrue = function (w) {
  const phase = `N${this.night}`;
  return [this.a, this.b].some(
    who => who !== null && who !== undefined &&
           w.roleAt(who, phase) === this.role);
};

/** What a two-seat reading leaned on, shared by all three of them. */
const pairLeanedOn = function (w) {
  const phase = `N${this.night}`;
  for (const who of [this.a, this.b])
    if (who !== null && who !== undefined &&
        w.roleAt(who, phase) === this.role) return [];
  return [this.a, this.b].filter(
    who => misregistered(w, who, phase, this.role));
};

// --- the first night ------------------------------------------------

export const Washerwoman = define("Washerwoman", "Washerwoman",
  function (w) {
    return registersAsRole(w.roleAt(this.a, "N1"), this.role) ||
           registersAsRole(w.roleAt(this.b, "N1"), this.role);
  }, {leanedOn: pairLeanedOn, isTrue: pairIsTrue});

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
  }, {leanedOn: pairLeanedOn, isTrue: pairIsTrue});

export const Investigator = define("Investigator", "Investigator",
  function (w) {
    return registersAsRole(w.roleAt(this.a, "N1"), this.role) ||
           registersAsRole(w.roleAt(this.b, "N1"), this.role);
  }, {leanedOn: pairLeanedOn, isTrue: pairIsTrue});

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
  }, {
    /** Whether the executed seat really was that character. */
    isTrue(w) {
      return w.roleAt(this.target, `D${this.night - 1}`) === this.role;
    },
    /** Read at the day of the execution, when the seat had to be showing
     * as what the Undertaker was told. */
    leanedOn(w) {
      return misregistered(w, this.target, `D${this.night - 1}`, this.role)
        ? [this.target] : [];
    },
  });

export const Ravenkeeper = define("Ravenkeeper", "Ravenkeeper",
  function (w) {
    return registersAsRole(w.roleAt(this.target, `N${this.night}`), this.role);
  }, {
    /** Whether that seat really was that character. */
    isTrue(w) {
      return w.roleAt(this.target, `N${this.night}`) === this.role;
    },
    leanedOn(w) {
      return misregistered(w, this.target, `N${this.night}`, this.role)
        ? [this.target] : [];
    },
  });

// --- Sects & Violets ---------------------------------------------------

/** Could this seat have shown as a Minion, if the Storyteller liked? */
const couldBeMinion = (w, seat, phase) =>
  w.teamAt(seat, phase) === "minion" ||
  CHARACTERS[w.roleAt(seat, phase)].registers.includes("minion");

/** Is there no way for this seat to have shown as anything else?
 *
 * A Spy is a Minion that registers as good, so it can nominate without
 * the Town Crier hearing a thing. Nobody else on these scripts can.
 */
const mustBeMinion = (w, seat, phase) =>
  w.teamAt(seat, phase) === "minion" &&
  !CHARACTERS[w.roleAt(seat, phase)].registers.some(t => t !== "minion");

/** Whether the Demon voted during the day just gone.
 *
 * Asked on the night after, so a reading on night three is about day
 * two. Read off the Demon at that day rather than off the deal, because
 * after a handover the question is about whoever held it then.
 */
export const FlowergirlInfo = define("FlowergirlInfo", "Flowergirl",
  function (w, s) {
    const day = this.night - 1;
    if (day < 1) return false;         // there was no day before the first
    const demon = w.demonAt(`D${day}`);
    if (demon === null) return !this.voted;
    const who = (s.votes || {})[day];
    const voted = !!who && (who.has ? who.has(demon) : who.includes(demon));
    return voted === !!this.voted;
  });

/** Whether a Minion nominated during the day just gone.
 *
 * A "yes" needs only one nominator who could have shown as a Minion —
 * the Storyteller chooses how anybody registers. A "no" is the harder
 * claim: every nominator has to have been able to show as something
 * else.
 */
export const TownCrierInfo = define("TownCrierInfo", "TownCrier",
  function (w, s) {
    const day = this.night - 1;
    if (day < 1) return false;
    const phase = `D${day}`;
    const raw = (s.nominations || {})[day];
    const who = !raw ? [] : (raw.has ? [...raw] : raw);
    if (this.nominated) return who.some(x => couldBeMinion(w, x, phase));
    return !who.some(x => mustBeMinion(w, x, phase));
  });

/** Whether a Minion really nominated, as against could have.
 *
 * `holds` allows for registration both ways — a Spy may be shown as a
 * Townsfolk, so "no Minion nominated" is a legal thing to say on a day
 * one did. Right for legality, wrong for truth, and a Vortox needs
 * truth: a reading made false by registration is already false.
 */
TownCrierInfo.prototype.isTrue = function (w, s) {
  const day = this.night - 1;
  if (day < 1) return false;
  const phase = `D${day}`;
  const raw = (s.nominations || {})[day];
  const who = !raw ? [] : (raw.has ? [...raw] : raw);
  const really = who.some(x => TEAM[w.roleAt(x, phase)] === "minion");
  return this.nominated ? really : !really;
};

/** How many of the dead are evil.
 *
 * The Empath's question asked of the other half of the table. Counted by
 * how a seat *registers*, so a dead Recluse may be shown either way.
 */
export const OracleInfo = define("OracleInfo", "Oracle",
  function (w, s) {
    // Including whoever fell tonight. The Oracle reads at slot 59 and a
    // Demon kills at 24, so by the time it counts, tonight's victim is
    // dead — while `aliveSet` reports who was alive at the *start* of
    // the night, which is a different question.
    const phase = `N${this.night}`;
    const alive = s.aliveSet(phase);
    const dead = w.roles.map((_r, p) => p)
      .filter(p => !alive.has(p) || s.diedAt(p).includes(phase));
    return possibleEvilCounts(w, dead, phase).has(this.count);
  });

/** Whether two players are the same side.
 *
 * Once per game, and strong: it splits the table in one reading. By
 * registration, so a Recluse may read either way.
 */
export const SeamstressInfo = define("SeamstressInfo", "Seamstress",
  function (w) {
    const phase = `N${this.night}`;
    for (const first of evilRegistrations(w.roleAt(this.a, phase)))
      for (const second of evilRegistrations(w.roleAt(this.b, phase)))
        if ((first === second) === !!this.same) return true;
    return false;
  });

/** How many of the day's guesses were right.
 *
 * Guessed publicly during the day, answered that night, so the row sits
 * on the night the number arrived and carries the guesses with it.
 * Matched by registration, so guessing "Recluse" at a seat the
 * Storyteller was showing as a Minion can be wrong even though the seat
 * really is the Recluse.
 */
export const JugglerInfo = define("JugglerInfo", "Juggler",
  function (w) {
    const phase = `D${this.night - 1}`;
    let right = 0;
    // The page sends {player, role} and the tests hand over [seat, role].
    // Both are read here rather than normalised on the way in, so a row
    // loaded from an old save still means what it meant when it was
    // written.
    for (const guess of this.guesses || []) {
      const [who, role] = Array.isArray(guess)
        ? guess : [guess.player, guess.role];
      if (role && registersAsRole(w.roleAt(Number(who), phase), role))
        right += 1;
    }
    return right === this.count;
  });

/** Two statements, one true and one false — written down, not solved.
 *
 * A Savant's pair can be anything from "the Demon sits beside an
 * Outsider" to "no Minion has yet chosen a man", and checking arbitrary
 * claims about a board is a different program from this one.
 *
 * Not nothing, though: recording one is still somebody claiming to have
 * visited the Storyteller, so a world with no Savant pays for the claim.
 */
export const SavantInfo = define("SavantInfo", "Savant", () => true,
                                 {weighed: () => false});

/** A yes-or-no question — the question kept, the answer not solved. */
export const ArtistInfo = define("ArtistInfo", "Artist", () => true,
                                 {weighed: () => false});

/** Two seats that know each other, one good and one evil.
 *
 * Set on the first night, so that is where it is read. One of the pair
 * is the Evil Twin itself and the other is good.
 */
export const EvilTwinPair = define("EvilTwinPair", "EvilTwin",
  function (w) {
    const first = w.roleAt(this.a, "N1"), second = w.roleAt(this.b, "N1");
    if (first !== "EvilTwin" && second !== "EvilTwin") return false;
    return isEvil(first) !== isEvil(second);
  });

// Four declared choices whose value is entirely in what follows from
// them. None has an answer to be wrong about — the deduction is drawn by
// the death and impairment rules — but recording the choice is the only
// way those rules can know where it landed.
const declaredChoice = (name, role) => define(name, role, () => true);

/** Who the Moonchild pointed at on learning it died.
 *
 * Only a good target dies, so a seat that died the next day reads good
 * and one that did not reads evil.
 */
export const MoonchildChoice = declaredChoice("MoonchildChoice", "Moonchild");

/** Which seat the Exorcist named.
 *
 * Naming the Demon stops it waking, so a quiet night is explained by it
 * — and that makes the named seat likelier to be the Demon.
 */
export const ExorcistChoice = declaredChoice("ExorcistChoice", "Exorcist");

/** The two the Innkeeper protected: both safe, one of them drunk. */
export const InnkeeperChoice = declaredChoice("InnkeeperChoice", "Innkeeper");

/** Who the Sailor chose: one of the two of them is drunk. */
export const SailorChoice = declaredChoice("SailorChoice", "Sailor");

/** A seat that became a character it was not dealt.
 *
 * Recorded rather than searched for, and that is the whole design: a
 * Pit-Hag acts on any night, on any seat, for no reason the table sees.
 * But when it *is* known it is known loudly, and from then on that seat
 * answers as something else.
 *
 * The character has to have been **not in play**, read off the true
 * assignment rather than the tokens — a Drunk holding the Fortune Teller
 * token does not stop a real one being made. The **side does not move**:
 * a Townsfolk turned into the Poisoner is a good Poisoner. And the new
 * character starts **that night**, which is why the first-night readings
 * read their own night rather than night one.
 */
export const PitHagChoice = define("PitHagChoice", "PitHag",
  function (w) {
    const phase = `N${this.night}`;
    if (w.roleAt(this.target, phase) !== this.role) return false;
    if (this.night > 1) {
      const earlier = `N${this.night - 1}`;
      for (let p = 0; p < w.roles.length; p++)
        if (p !== this.target && w.roleAt(p, earlier) === this.role)
          return false;
    }
    return true;
  });

/** Who the Snake Charmer pointed at, and whether anything happened.
 *
 * Recorded rather than guessed, because the outcome is visible: choose
 * the Demon while working and you swap characters *and* sides with it,
 * which the table finds out about at once. Choose anybody else and
 * nothing happens — which is worth a lot, since it says that seat was
 * not the Demon.
 */
export const SnakeCharmerChoice = define("SnakeCharmerChoice", "SnakeCharmer",
  function (w) {
    const phase = `N${this.night}`;
    if (this.swapped)
      // Checked *after* the swap, and from the day it took effect: the
      // seat pointed at is now holding the Snake Charmer's character.
      return w.roleAt(this.target, `D${this.night}`) === "SnakeCharmer";
    // Nothing happened, so either they were not the Demon or the Snake
    // Charmer was not working — and the second is somebody else's excuse.
    return w.demonAt(phase) !== this.target;
  });

/** The night a Philosopher took somebody else's ability.
 *
 * It does not *become* that character — it keeps its own, and the chosen
 * one may be sitting elsewhere at the same time. So this is an overlay:
 * from this night on, that seat also acts as the chosen character.
 *
 * Choosing is the whole of it; there is no answer to be wrong about.
 * What it gained is checked wherever those readings are.
 */
export const PhilosopherChoice = define("PhilosopherChoice", "Philosopher",
  function () { return !isEvil(this.role); });

/** Killed by the Demon, it learns two players, one of them the killer.
 *
 * No misregistration here, unlike almost every other reading: it is
 * shown *the Demon that killed it*, so a Recluse being shown as the
 * Demon cannot fill the pair.
 */
export const SageInfo = define("SageInfo", "Sage",
  function (w) {
    const demon = w.demonAt(`N${this.night}`);
    return demon !== null && (demon === this.a || demon === this.b);
  });

/** Who the Klutz pointed at on dying.
 *
 * Good loses on the spot if that player is evil, so a board where the
 * game carried on says they were not — while it was working. Same shape
 * as the Saint being executed while poisoned.
 */
// The experimental four, named as the ledger names them.
//
// None of these existed here at all. Three of them shipped, and the
// moment anybody entered one and pressed Solve the whole solve died with
// "Unknown kind of reading" — the Python side had them, the JavaScript
// side did not, and the hosted page runs the JavaScript.
/** Three players, exactly one evil **by registration**. */
export const Noble = define("Noble", "Noble",
  function (w) {
    const phase = `N${this.night}`;
    const opts = [this.a, this.b, this.c].map(
      p => evilRegistrations(w.roleAt(p, phase)));
    for (const x of opts[0]) for (const y of opts[1]) for (const z of opts[2])
      if (Number(x) + Number(y) + Number(z) === 1) return true;
    return false;
  });

export const Acrobat = define("Acrobat", "Acrobat",
  function (w) { return true; });          // the walk judges the death

export const Balloonist = define("Balloonist", "Balloonist",
  function (w) { return true; });          // the chain is judged as a whole

export const Alsaahir = define("Alsaahir", "Alsaahir",
  function (w) {
    const phase = `D${this.night}`;
    const demons = new Set(), minions = new Set();
    for (let p = 0; p < w.roles.length; p++) {
      const team = TEAM[w.roleAt(p, phase)];
      if (team === "demon") demons.add(p);
      else if (team === "minion") minions.add(p);
    }
    const same = (a, b) => a.size === b.length
      && b.every(x => a.has(x));
    const exact = same(demons, this.demons || [])
               && same(minions, this.minions || []);
    if (this.won) return exact;
    if (w.roleAt(this.player, phase) !== "Alsaahir") return true;
    return !exact;
  });

/** A seat was handed a character it was not dealt, and says so. */
export const Became = define("Became", null,
  function (w) {
    const after = `D${this.night}`;
    return w.roleAt(this.player, after) === this.role
        && w.roles[this.player] !== this.role;
  });

export const KlutzChoice = define("KlutzChoice", "Klutz",
  function (w) {
    return !w.evilAt(this.target, `N${this.night}`);
  });

/** How many seats could have been impaired on this night.
 *
 * A range rather than a number, because the solver never decides where a
 * Poisoner went unless something forces it. What it does know is the
 * shape: whoever is *always* impaired — anybody holding somebody else's
 * token, or a whole table a Minstrel has silenced — plus at most one seat
 * per source that has to land somewhere.
 *
 * Every count between the two is reachable, since a source that can hit
 * a fresh seat can also hit one already taken.
 */
export function possibleImpairmentCounts(world, state, night) {
  const always = new Set();
  const movable = [];
  for (const source of sourcesOn(world, state, night)) {
    // Free *and* reaching everybody it touches — a Drunk holding
    // somebody else's token, a Minstrel silencing the table. A free
    // source that still has to *pick* is a different thing: a
    // Vigormortis poisons one of the two Townsfolk beside a dead Minion
    // and the Storyteller chooses which. Counting its whole reach as
    // certainly impaired said two where the answer was one.
    if (source.freeForEveryone() && source.capacity >= source.seats.size)
      for (const seat of source.seats) always.add(seat);
    else movable.push(source);
  }
  let most = always.size;
  for (const source of movable) {
    let fresh = 0;
    for (const seat of source.seats) if (!always.has(seat)) fresh += 1;
    most += Math.min(source.capacity, fresh);
  }
  return [always.size, Math.min(most, state.nPlayers)];
}

/** How many abilities went wrong tonight.
 *
 * A reading about the solver's own workings rather than about the table,
 * and the only one of its kind.
 *
 * Two approximations, both the permissive kind — they rule out numbers
 * that cannot happen and never rule out a world that could. It checks
 * the count is *reachable* rather than forcing the plan to produce it;
 * and it uses the night's own span, where "since dawn" straddles the day
 * before and tonight.
 */
export const MathematicianInfo = define("MathematicianInfo", "Mathematician",
  function (w, s) {
    // It can only count what the solver knows how to break. A script
    // with characters still to be built may have ways to go wrong that
    // nothing here has heard of, and ruling out a number on that basis
    // would throw away worlds that really happened.
    if (s.script.keys.some(k => CHARACTERS[k].impairs &&
                                !CHARACTERS[k].modelled)) return true;
    const [low, high] = possibleImpairmentCounts(w, s, this.night);
    return low <= this.count && this.count <= high;
  }, {
    // Silent on a script it cannot account for, and silence has to
    // survive a Vortox.
    weighed(state) {
      return !state.script.keys.some(k => CHARACTERS[k].impairs &&
                                          !CHARACTERS[k].modelled);
    },
  });

/** How many steps from the Demon to its nearest Minion.
 *
 * Around the circle, the shorter way, and the nearest Minion when there
 * is more than one — so a Minion sitting beside the Demon is 1.
 *
 * First night only, which is why the dead never come into it. Read off
 * the true Demon and the true Minions rather than off how anybody
 * registers: it is the Storyteller counting seats, not a character
 * reading anybody.
 */
export const ClockmakerInfo = define("ClockmakerInfo", "Clockmaker",
  function (w) {
    const phase = `N${this.night}`;
    const demon = w.demonAt(phase);
    if (demon === null) return false;
    const n = w.roles.length;
    let nearest = null;
    for (let m = 0; m < n; m++) {
      if (w.teamAt(m, phase) !== "minion") continue;
      const steps = Math.min((m - demon + n) % n, (demon - m + n) % n);
      if (nearest === null || steps < nearest) nearest = steps;
    }
    return nearest !== null && nearest === this.count;
  });

/** One good character and one evil one, and the target is one of them.
 *
 * Two constraints rather than one, which is what makes it strong: the
 * pair has to be one of each side, *and* the seat asked about has to be
 * one of the two. The Storyteller picks which is true and never says, so
 * this holds whichever way round it was.
 */
export const DreamerInfo = define("DreamerInfo", "Dreamer",
  function (w) {
    // One of each side, or the reading is not a Dreamer's at all.
    if (isEvil(this.good_role) || !isEvil(this.evil_role)) return false;
    const actual = w.roleAt(this.target, `N${this.night}`);
    return registersAsRole(actual, this.good_role) ||
           registersAsRole(actual, this.evil_role);
  });

/** Whether a Dreamer's reading was *true*, as against merely legal.
 *
 * A Vortox falsifies what an ability yields, and misregistration is the
 * mechanic that lets a Storyteller give false information legally — a
 * Spy shown as the Slayer is still a Spy, so that reading is already
 * false and a Vortox may produce it. `holds` answers "could this have
 * been said"; this answers "was it so".
 */
DreamerInfo.prototype.isTrue = function (w) {
  const actual = w.roleAt(this.target, `N${this.night}`);
  return isReallyRole(actual, this.good_role) ||
         isReallyRole(actual, this.evil_role);
};

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


// A Vortox falsifies information, not choices. Nobody told a Philosopher
// what it took, a Courtier which character to name, a Klutz where to
// point or a Gambler what to guess — so there is nothing about these
// rows for a Vortox to make false.
//
// The consequences still land: a Philosopher that took the Town Crier
// gets that ability and *that* reading is inverted, a Gambler that
// guesses wrong still dies, a Snake Charmer that chose the Vortox still
// swaps character and alignment with it.
PhilosopherChoice.isAChoice = true;
SnakeCharmerChoice.isAChoice = true;
PitHagChoice.isAChoice = true;
Became.isAChoice = true;
Acrobat.isAChoice = true;
Alsaahir.isAChoice = true;
CourtierChoice.isAChoice = true;
KlutzChoice.isAChoice = true;
GamblerGuess.isAChoice = true;
MoonchildChoice.isAChoice = true;
ExorcistChoice.isAChoice = true;
InnkeeperChoice.isAChoice = true;
SailorChoice.isAChoice = true;

export const KINDS = {
  Washerwoman, Librarian, Investigator, Chef, Empath, FortuneTeller,
  Undertaker, Ravenkeeper, GrandmotherInfo, ChambermaidInfo, GamblerGuess,
  CourtierChoice, VirginNomination, SlayerShot,
  ClockmakerInfo, DreamerInfo, MathematicianInfo,
  FlowergirlInfo, TownCrierInfo,
  OracleInfo, SeamstressInfo, JugglerInfo, SavantInfo, ArtistInfo,
  SageInfo, KlutzChoice, EvilTwinPair, PhilosopherChoice,
  SnakeCharmerChoice, PitHagChoice,
  Noble, Acrobat, Balloonist, Alsaahir, Became,
  MoonchildChoice, ExorcistChoice, InnkeeperChoice, SailorChoice,
};

/** Build a reading from the shape the page posts. */
export function makeInfo(row) {
  const Kind = KINDS[row.type];
  if (!Kind) throw new Error(`Unknown kind of reading: ${row.type}`);
  const {type, ...fields} = row;
  return new Kind(fields);
}
