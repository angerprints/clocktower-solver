// What a board records, and how to ask it about a moment.
//
// The awkward part is that death is not permanent. A seat can die, be
// raised and die again, so "were they standing then" is a question about
// a moment rather than about a single death — and every check that cares
// when it is asking has to say so.

import {phaseIndex} from "./phases.mjs";
import {DEFAULT} from "./scripts.mjs";

/** A single phase is accepted wherever a list belongs, because one death
 * is what a seat usually has and writing `{2: "N3"}` is how anybody would
 * say it. */
export function asPhases(value) {
  if (value === null || value === undefined || value === "") return [];
  return typeof value === "string" ? [value] : [...value];
}

export class GameState {
  constructor(opts = {}) {
    this.nPlayers = opts.nPlayers;
    this.claims = opts.claims || {};
    this.script = opts.script || DEFAULT;
    // Public knowledge, so this is told to the solver rather than
    // discovered by it. What a Fabled *did* stays hidden, which is the
    // point of the Sentinel.
    this.fabled = opts.fabled || [];
    this.certainties = opts.certainties || {};
    this.reads = opts.reads || {};
    // Seats somebody thinks may have been handed the wrong token. A
    // suspicion about their *information*, not about their side.
    this.suspects = opts.suspects || {};
    this.wakes = opts.wakes || {};
    this.executions = {...(opts.executions || {})};
    this.quietNights = new Set(opts.quietNights || []);
    // Days the town got through without executing anybody. No world is
    // ruled out by it, but it says the game *reached* that day, which
    // bounds how long a lineage can run.
    this.daysDone = new Set(opts.daysDone || []);
    // Who voted, and who nominated, on each day. Only the Flowergirl and
    // the Town Crier ask, but a day is where the answer lives.
    this.votes = opts.votes || {};
    this.nominations = opts.nominations || {};
    // Two things the table sees plainly, each giving away a character
    // nobody chose to reveal: a seat dropping dead as it nominates is a
    // Witch, a seat executed for breaking madness is a Cerenovus.
    this.witchDeaths = opts.witchDeaths || {};
    this.madnessExecutions = opts.madnessExecutions || {};
    this.infos = opts.infos || [];
    this.names = opts.names || [];

    // "Executed on day n" written as a death gets split apart. It is how
    // most people describe it and how older saves recorded it, but the
    // two facts are separate — which is what lets a board say somebody
    // was executed and lived.
    const deaths = {};
    for (const [seat, phases] of Object.entries(opts.deaths || {})) {
      const out = [];
      for (const phase of asPhases(phases)) {
        if (phase && phase[0].toUpperCase() === "E") {
          const day = parseInt(phase.slice(1), 10);
          out.push(`D${day}`);
          if (this.executions[day] === undefined) this.executions[day] = +seat;
        } else out.push(phase);
      }
      deaths[seat] = out;
    }
    this.deaths = deaths;

    this.resurrections = Object.fromEntries(
      Object.entries(opts.resurrections || {})
            .map(([seat, phases]) => [seat, asPhases(phases)]));

    // One run of events per seat, in order.
    this._life = {};
    const seats = new Set([...Object.keys(this.deaths),
                           ...Object.keys(this.resurrections)]);
    for (const seat of seats) {
      const events = [];
      for (const p of this.deaths[seat] || []) events.push([phaseIndex(p), false]);
      for (const p of this.resurrections[seat] || []) events.push([phaseIndex(p), true]);
      // A death and a return at the same moment reads as the return,
      // since that is the only order in which both could be true.
      events.sort((a, b) => a[0] - b[0] || Number(a[1]) - Number(b[1]));
      this._life[seat] = events;
    }

    this._aliveCache = new Map();
    this._aliveSetCache = new Map();
  }

  /** Standing at this point, given everything that happened to them.
   *
   * A death takes effect *after* the moment it happened: somebody killed
   * on night two was alive during night two, which is what every check
   * asking "who was around then" means. A return takes effect *at* its
   * moment, because that is when they are back.
   */
  _alive(seat, index) {
    let standing = true;
    for (const [at, living] of this._life[seat] || []) {
      if (living) { if (at <= index) standing = true; }
      else if (at < index) standing = false;
    }
    return standing;
  }

  /** Who was still standing at this moment. Cached, because the
   * impairment plan asks for every night of every world. */
  aliveAt(phase) {
    const cached = this._aliveCache.get(phase);
    if (cached) return cached;
    const at = phaseIndex(phase);
    const out = [];
    for (let p = 0; p < this.nPlayers; p++) if (this._alive(p, at)) out.push(p);
    this._aliveCache.set(phase, out);
    return out;
  }

  /** Which character each Philosopher took, and from when. */
  philosophies() {
    if (!this._philosophies) {
      const got = {};
      for (const info of this.infos)
        if (info.sourceRole === "Philosopher" && info.role)
          got[info.player] = [info.role, `N${info.night}`];
      this._philosophies = got;
    }
    return this._philosophies;
  }

  aliveSet(phase) {
    let cached = this._aliveSetCache.get(phase);
    if (!cached) {
      cached = new Set(this.aliveAt(phase));
      this._aliveSetCache.set(phase, cached);
    }
    return cached;
  }

  /** Every moment this seat died. Usually one, sometimes none. */
  diedAt(seat) { return this.deaths[seat] || []; }

  /** (seat, phase) for every death on the record. */
  *deathPhases() {
    for (const [seat, phases] of Object.entries(this.deaths || {}))
      for (const phase of phases) yield [Number(seat), phase];
  }

  /** Who the town executed that day, alive or dead afterwards. */
  executedOn(day) {
    const seat = (this.executions || {})[day];
    return seat === undefined ? null : seat;
  }

  /** Who was executed that day *and* died of it.
   *
   * What the Undertaker learns from, and what the Saint's losing
   * condition keys off. An execution somebody walked away from gives
   * neither of them anything.
   */
  executionDeath(day) {
    const seat = this.executedOn(day);
    if (seat === null) return null;
    return this.diedAt(seat).includes(`D${day}`) ? seat : null;
  }

  /** The latest moment the game has reached.
   *
   * What "evil" means for a seat depends on when you ask, so the report
   * has to pick a moment. It picks now.
   */
  finalPhase() {
    let latest = "N1";
    const consider = phase => {
      if (phaseIndex(phase) > phaseIndex(latest)) latest = phase;
    };
    for (const [, phase] of this.deathPhases()) consider(phase);
    for (const phases of Object.values(this.resurrections || {}))
      phases.forEach(consider);
    for (const night of this.quietNights) consider(`N${night}`);
    for (const day of this.daysDone) consider(`D${day}`);
    for (const info of this.infos) consider(`N${info.night}`);
    return latest;
  }

  label(i) {
    return this.names && this.names[i] ? `${i}:${this.names[i]}` : String(i);
  }
}
