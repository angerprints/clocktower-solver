// The numbers that are judgement rather than rules.
//
// Every figure the solver prints mixes two things. Some of it is the
// rulebook — a landed Slayer shot means the target was the Demon or the
// Recluse, and that is checkable. The rest rests on the constants below,
// which were picked by judgement and are printed in the same font.
//
// They live here, in one mutable object, for a reason that only shows up
// when you try to measure them: the guesswork sweep re-solves the same
// board with each one moved to the edges of its plausible range, and a
// value frozen into a `const` in three separate modules cannot be moved.
// Everything that uses one reads it from here at the moment it is needed.

export const PRIORS = {
  // Good players lie far less than evil ones, but not all good lies are
  // the same. An Outsider covering their character is close to routine —
  // a Recluse or a Saint claiming a Townsfolk is a normal way to stay
  // alive. A Townsfolk claiming a *different* Townsfolk poisons its own
  // team's information for no gain.
  OUTSIDER_HIDING_PENALTY: 0.35,
  TOWNSFOLK_LIE_PENALTY: 0.02,

  // Evil is handed bluffs drawn from characters that are NOT in play, and
  // the team knows each other, so a clean bluff collides with nothing.
  BLUFF_COLLISION_PENALTY: 0.3,

  // Each point of social read multiplies the odds of that seat being evil.
  READ_ODDS_STEP: 2.0,

  // Marking a seat as possibly unreliable multiplies the odds they were
  // handed somebody else's token.
  DRUNK_SUSPICION_STEP: 3.0,

  // The Demon kills good players. Killing your own Minion wastes a night,
  // and the one real reason to do it happens late.
  NIGHT_DEATH_EVIL_PENALTY: 0.05,

  // A world that only survives because the Poisoner hit exactly the right
  // seat on exactly the right night is not as good a story as one where
  // the information is simply true.
  POISON_HIT_PENALTY: 0.35,
  POISON_REPEAT_PENALTY: 0.7,

  // Information with no genuine source anywhere in a world had to be
  // invented. That happens — people bluff detailed readings — but it is a
  // deliberate risk.
  FABRICATED_INFO_PENALTY: 0.4,
  INFO_TRUST_STEP: 2.0,
  // What one confirmed reading is worth, as an odds multiplier on its
  // source really being that character. Evidence, not proof — a Spy
  // reading the grimoire can feed a Minion true information all game.
  CONFIRMED_READING_STEP: 2.5,

  // Sinking a kill into a corpse fakes protection, which is exactly what
  // a Demon bluffing Soldier or Monk wants.
  SUNK_KILL_PENALTY: 0.45,

  // A Gossip only kills when what it said that day was true.
  GOSSIP_KILL_PENALTY: 0.4,
  // A Tinker goes when the Storyteller feels like it.
  TINKER_DEATH_PENALTY: 0.3,
  // One strike for the whole game.
  ASSASSIN_STRIKE_PENALTY: 0.25,
  // A Storyteller treats the Sailor's drunkenness as the price the town
  // pays for having somebody unkillable, not as a weapon.
  SAILOR_ON_EVIL_PENALTY: 0.15,
};

// The ranges I would defend as equally plausible. Running the solve
// across them says how much of a figure is evidence and how much is me,
// and which guess is doing the work.
export const PRIOR_RANGES = {
  OUTSIDER_HIDING_PENALTY: [0.15, 0.60],
  TOWNSFOLK_LIE_PENALTY: [0.005, 0.10],
  BLUFF_COLLISION_PENALTY: [0.10, 0.60],
  NIGHT_DEATH_EVIL_PENALTY: [0.02, 0.15],
  POISON_HIT_PENALTY: [0.20, 0.55],
  POISON_REPEAT_PENALTY: [0.50, 0.90],
  FABRICATED_INFO_PENALTY: [0.20, 0.70],
  SUNK_KILL_PENALTY: [0.25, 0.70],
  READ_ODDS_STEP: [1.5, 3.0],
};

/** Run something with one prior moved, and put it back afterwards. */
export function withPrior(name, value, run) {
  const was = PRIORS[name];
  PRIORS[name] = value;
  try {
    return run();
  } finally {
    PRIORS[name] = was;
  }
}
