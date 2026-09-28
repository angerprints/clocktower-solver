// A board survives no world. What would have to give?
//
// Saying "nothing fits" and stopping is nearly useless mid-game: the
// board is somebody's hurried typing, and the useful answer is which
// entry to look at again. So one entry is removed at a time, and the
// removals that let a world through are the shortlist.
//
// The interesting case is *no* single culprit. That means the board is
// contradictory in a way no one entry accounts for — two readings
// disagreeing, a good player lying, or a character on the script that
// lets the Storyteller break the rules.

import {CHARACTERS, SETUP} from "./catalogue.mjs";
import {believedTokens, believesAnother} from "./roles.mjs";
import {explanationCost, forcedRoles} from "./scoring.mjs";
import {GameState} from "./state.mjs";
import {bags, eachWorld} from "./worlds.mjs";

/** Is there a single world that survives? Stops at the first one.
 *
 * Cheap when the answer is yes and expensive when it is no, which is
 * exactly the wrong way round for a diagnosis — hence the ceiling, and
 * the second answer saying whether the search finished or gave up.
 */
export function anythingFits(state, allowGoodLies = false,
                             ceiling = 120_000) {
  let seen = 0, found = false, complete = true;
  eachWorld(state.nPlayers, state.claims, {
    certainties: state.certainties,
    allowGoodLies,
    forced: forcedRoles(state),
    wakes: state.wakes,
    script: state.script,
    fabled: state.fabled,
  }, world => {
    seen += 1;
    if (seen > ceiling) { complete = false; return false; }
    if (explanationCost(world, state) !== null) { found = true; return false; }
    return true;
  });
  return {fits: found, complete: found ? true : complete};
}

/** The same board with one entry taken out.
 *
 * Dropping a death drops the execution that went with it, if any —
 * otherwise the board would claim the town executed somebody who never
 * died, which is a different situation and not the one being tested.
 */
function without(state, {dropInfo = null, dropDeath = null,
                         dropQuiet = null} = {}) {
  const executions = {};
  for (const [day, seat] of Object.entries(state.executions || {}))
    if (seat !== dropDeath) executions[day] = seat;

  const deaths = {};
  for (const [seat, phases] of Object.entries(state.deaths || {}))
    if (Number(seat) !== dropDeath) deaths[seat] = phases;

  return new GameState({
    nPlayers: state.nPlayers,
    claims: {...state.claims},
    certainties: {...state.certainties},
    reads: {...state.reads},
    wakes: {...state.wakes},
    suspects: {...state.suspects},
    deaths,
    resurrections: {...state.resurrections},
    executions,
    quietNights: [...state.quietNights].filter(n => n !== dropQuiet),
    infos: state.infos.filter((_x, i) => i !== dropInfo),
    names: [...(state.names || [])],
    script: state.script,
    fabled: state.fabled,
  });
}

/** Is the trouble the claims themselves rather than anything recorded?
 *
 * A common way to end up with no worlds at all, and one the entry-by-
 * entry search cannot see: twelve seats all claiming Townsfolk when every
 * bag for that table needs two Outsiders, and only the Drunk can sit
 * behind a Townsfolk claim. Removing a reading will never fix that.
 *
 * Returns a sentence, or null when the claims are not the problem.
 */
export function claimsCannotFillTheBag(state, allowGoodLies = false) {
  const n = state.nPlayers;
  if (!SETUP[n]) return null;

  // How many seats could hold an Outsider *at the same time*, which is
  // not the same as how many could individually. A Townsfolk claim can
  // hide the Drunk — but only one of them can, because there is only one
  // Drunk. Counting them one at a time made this never fire.
  let openSeats = 0, claimedOutsider = 0;
  const hidden = new Set();
  for (let seat = 0; seat < n; seat++) {
    const claim = state.claims[seat];
    const certainty = (state.certainties || {})[seat] || "";
    if (!claim || certainty === "hiding" || certainty === "unsure" ||
        allowGoodLies) {
      openSeats += 1;
    } else if (state.script.outsiders.includes(claim)) {
      claimedOutsider += 1;
    } else {
      for (const key of state.script.outsiders)
        if (believesAnother(key) &&
            believedTokens(key, state.script).includes(claim))
          hidden.add(key);              // one seat each, however many claim it
    }
  }
  const could = Math.min(claimedOutsider + openSeats + hidden.size,
                         state.script.outsiders.length);

  const wanted = Math.min(...bags(n, state.script, state.fabled)
    .map(([, counts]) => counts.outsider));
  if (could >= wanted) return null;

  return `${n} seats, and the smallest bag for that table still needs ` +
         `${wanted} Outsiders — but only ${could} of them could be one ` +
         `without lying about it. Somebody has to be an Outsider, so ` +
         `either a claim is wrong or a seat needs marking as ` +
         `\u201cmight be hiding\u201d.`;
}

/** Work out what would have to give.
 *
 * One culprit usually means a mis-entered reading or somebody lying. *No*
 * single culprit is the interesting case, and it is why `complete`
 * matters: a search that gave up rather than concluded has not shown
 * there is no culprit, only that it did not find one.
 */
export function diagnose(state, allowGoodLies = false, ceiling = 120_000) {
  const culprits = [];
  let complete = true;

  state.infos.forEach((info, i) => {
    const got = anythingFits(without(state, {dropInfo: i}), allowGoodLies,
                             ceiling);
    complete = complete && got.complete;
    if (got.fits)
      culprits.push({
        kind: "information",
        label: `${info.type} on night ${info.night}, seat ${info.player + 1}`,
      });
  });

  for (const seat of Object.keys(state.deaths || {}).map(Number)) {
    const got = anythingFits(without(state, {dropDeath: seat}), allowGoodLies,
                             ceiling);
    complete = complete && got.complete;
    if (got.fits)
      culprits.push({kind: "death", label: `seat ${seat + 1} dying`});
  }

  for (const night of [...state.quietNights]) {
    const got = anythingFits(without(state, {dropQuiet: night}),
                             allowGoodLies, ceiling);
    complete = complete && got.complete;
    if (got.fits)
      culprits.push({kind: "quiet night",
                     label: `the quiet night ${night}`});
  }

  return {culprits, complete};
}
