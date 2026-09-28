# Als Nächstes — Stand 28.09.2026

**Die aktuelle Roadmap steht in `ROADMAP.md`.** Kurz:

0. Zuhause und Auslieferung: eigener Ordner mit git oder direkter Push, statt ZIP
1. Unabhängiger Schiedsrichter: Partien aus der Engine des Einzelspieler-Spiels als Bretter
2. Deine Skripte vollständig: Ogre, Marionette, dann Mastermind, Mutant, Cerenovus, Savant
3. Gemeinsames Regelwissen, wenn das Spiel bei v2 ankommt
4. Eine echte Partie

Alles darunter ist das Protokoll der bisherigen Sitzungen.

---

# Where this is going

**Breadth, not polish.** Settled at the table: the aim is a solver that
handles *any* script, not one that squeezes a few more points out of the
three published ones.

That is a deliberate trade and worth restating whenever the road feels
long, because the road *is* long and nothing visible changes for a
while.

## Why not polish

The Demon is already the top suspect in 24 of 40 games, median rank 1 of
9, never worse than third. Three separate attempts to close the
calibration gap came back negative, and the finding each time was that
the gap is not a defect: on a board with one or two readings, half the
legal worlds genuinely have that seat evil, so a solver saying about half
is *right*. There may not be much left to win there.

## What breadth means, concretely

  * **68 of 138 released characters are not modelled** — half the game.
  * **Homebrew scripts mix anything**, and mixing found nine bugs that
    cannot arise on a published script.
  * **Experimental characters** are the point of the exercise, and the
    Acrobat is half-built, blocked on exactly the night-order work.

Almost every character has timing in its text. Until the solver walks a
night it cannot hold them, which is why the night order is the unlock for
all three.

## The one thing that is not on this road

Everything is measured against a simulator written here, which is
circular. **A real game, played by real people, would say more about
whether any of this is useful than another month of building.** Worth
doing whenever there is one to hand.

---

# What to do next, in phases

Each phase is sized to finish inside one session — roughly a dozen
commands, with the slow bits given room. Say **"do phase 3"** and that is
what gets done.

They are ordered so that a phase never depends on one below it. Phases 1
and 2 are housekeeping and unblock everything else; if only one thing
gets done, make it phase 1.

---

## Phase 1 — Make the tests runnable again  ✅ done

Timing each class separately showed the cost was not spread: four classes
were essentially all of it, and the worst was not recent work at all.

    262s  BadMoonRisingPlaysAndSolves
    145s  TheDemonGetsEasierToFind
    118s  RepairingABoardSomebodyLiedTo

Everything else was under a second.

Two changes. **Seed counts trimmed** — several tests played and *solved*
twenty to sixty whole games to show something a handful shows just as
well. And **the curves are cached**: three tests each recomputed the same
fourteen five-night games, solving every night of each, which cost 145
seconds for no coverage at all.

`test_claims` now finishes in 280s and passes. All four quarters are
green, 792 tests.

And it caught something in the act: trimming `games(count=20)` to six
made `assertGreater(solved, 15)` unreachable, so the test failed for a
reason that said nothing about the solver. It counts a *share* now, which
is what it meant all along.

<details><summary>the original plan</summary>

`test_claims` no longer finishes. Three attempts in a row were killed
before printing a summary, which means the repair change from last
session is **unverified**, and so is anything else that file covers.

The cause is not mysterious: each of its tests plays whole games and
solves every phase, several of them across dozens of seeds. That is
minutes of work per test.

  * Cut the seed counts to what actually proves the point — a test that
    plays forty games to show an average is usually just as convincing on
    ten.
  * Move the genuinely slow checks behind a marker so they run on demand
    rather than every time.
  * Confirm `run_tests.py claims` completes, then run all four quarters.

**Done when** the whole suite passes in four parts, each finishing well
inside a session.

</details>

---

## Phase 2 — A pattern that matches nothing should fail  ✅ done

`run_tests.py waking` now exits 2, says nothing matches, suggests
`wakes`, and lists every test file. Same for a `-k` keyword that filters
everything away, and for any run that ends with no tests at all.

The suggestion compares by *spelling* rather than by prefix, which
matters: the first attempt matched on the first four letters and missed
the one case it was written for — "waki" is not a substring of "wakes".

`test_runner.py` covers both the failing paths and the ordinary ones, so
a future change cannot quietly make a typo green again.

<details><summary>the original plan</summary>

`run_tests.py waking` reported "Ran 0 tests — all good". The file is
`test_wakes`. For a whole session that hid the very tests being looked
for, and it will do it again.

  * `run_tests.py` exits non-zero, loudly, when the pattern matches no
    file — and says which files exist.
  * Same for a `-k` keyword that filters everything away.

Small, and it prevents a repeat of a mistake that cost a session.

**Done when** `run_tests.py nonsense` fails and lists the real files.

</details>

---

## Phase 3 — The seed-8 mystery  ✅ done

Seat 9 softclaimed **"conditional"**, and that is not a pattern anybody
can say at a table. The five real ones are `every`, `first`, `never`,
`other`, `sometimes`; a Sage's are `never` and `sometimes`. So the search
produced no world at all with that seat as itself, and the true world was
never enumerated.

The cause was in `claims.py`, reading `CHARACTERS[role].nights` instead
of the `wake` set. `nights` describes the *shape* of an ability —
"conditional" for a Sage, "other" for a Demon — and is not a claim.

**Third time that same confusion has bitten.** The Chambermaid read
`nights` and thought Demons slept through night one; the solver's own
waking check did the same; now this. Three places, one misreading, and
the `wake` set had the honest answer every time.

Two things fell out of fixing it. Repair became **usable**: opening a
seat and allowing hidden Outsiders on the other eight hit the 300,000
cap at 208 seconds a seat, which is half an hour to repair one board. It
runs on a tenth of the budget now and weighs the result on a sample. And
boards needing repair went from about one in six to **one in forty** —
most of what used to need it was the simulator producing a claim nobody
could make.

<details><summary>the original plan</summary>

Two of ten Sects & Violets games rule the true Demon out entirely. One is
the known Townsfolk-lie gap. The other is not understood, and it is a
hard bug: the true world explains the board *perfectly* (cost 1.0) and is
simply never generated.

What is already established, so this does not start from nothing:

  * every seat's true character **is** individually admitted by its own
    claim;
  * both softclaims are truthful;
  * the bag is legal — a Fang Gu game with three Outsiders.

So something about the *combination* excludes it. Tracing ran the
nine-seat search out of memory with good lies allowed, so:

  * shrink it first — find the smallest board that still loses the truth,
    by dropping seats and claims until it stops happening;
  * then walk the enumeration on that board rather than the full one.

**Reproduce with** seed 8 on Sects & Violets, nine players, three nights.

**Done when** the exclusion is named — as a bug to fix or a documented
limit like the Townsfolk lie, either is an answer.

</details>

---

## Phase 4 — The rest of the Sects & Violets readings  ✅ done

Mathematician, Juggler, Savant, Artist and Evil Twin are produced, so
nine of the sixteen now appear in played games and no board comes out
impossible.

Two things it found:

**Python's Juggler could not read a page-shaped row.** The page sends
`{player, role}` and the tests hand over `[seat, role]`; the JavaScript
learned to read both months ago and Python never did, because nothing had
ever fed it the page's shape — the conformance corpus is built from
tuples. A simulator producing the page's shape found it in one game.

**And the Mathematician counts every way of going wrong, not just the
Poisoner.** Sects & Violets droisons four other ways and all of them are
standing: a No Dashii poisons its two nearest Townsfolk all game, a
Vigormortis beside each Minion it killed, a Sweetheart from the night it
dies, a Philosopher whoever already had the ability it took. Counting
only the Poisoner made it say nought while a No Dashii was quietly
poisoning two — and the solver rightly called that board impossible.

<details><summary>the original plan</summary>

Six of sixteen are produced. These need nothing new:

  * **Mathematician** — how many abilities went wrong, which the
    simulator already knows exactly since it decides the droisoning.
  * **Juggler** — guesses in the day, hears the count that night.
  * **Savant** and **Artist** — free text, recorded and not weighed, so
    the simulator only has to produce something plausible.
  * **Evil Twin** — a pair on the first night.

**Done when** all six appear in played games and no board becomes
impossible.

</details>

---

## Phase 5 — The readings that need the day recorded  ✅ done

Nominations and votes are simulated, and the execution now *follows* from
them: two or three nominations, everybody votes with a coin weighted by
suspicion, and whoever draws most votes goes up. Evil votes a little less
for its own, which is what makes a Flowergirl's answer carry anything.

Flowergirl and Town Crier are produced, so eleven of the sixteen readings
now appear.

**One bug fixed:** `_make_false` inverted a `yes` field and nothing else,
so a Flowergirl or Town Crier reading came through a Vortox unchanged —
still true, on a board where every Townsfolk reading must be false. It
inverts every yes-or-no field by name now.

**The rules question is settled**: a poisoning from a Vigormortis kill
triggers and registers on the night it killed. Asked rather than reasoned
out, and the solver had it right.

Following that through found a **real solver bug**.
`_possible_impairment_counts` treated any *free* source as impairing
everybody it reached, ignoring capacity — but a Vigormortis reaches the
two Townsfolk beside a dead Minion and poisons only one. The range came
out (0, 0) where the truth was (0, 1), so a Mathematician correctly
saying 1 made the board impossible. A Drunk holding somebody else's token
impairs its whole reach because there is nothing to choose; a Vigormortis
is free *and* has to pick, and only the first belongs in "always".

Cleaning up after it took four test failures, and every one was worth
having:

  * **Five helpers built boards without votes and nominations**, because
    they predate the simulator having a day. A reading about the day
    before referred to a day the state thought nobody voted on.
  * **`CONFIDENTLY_WRONG` moved for the second time.** A seed is a
    terrible way to name a property: it drifts whenever the simulator
    consumes randomness differently. The tests measure the property now.
  * **A Poisoner that caught the star kept poisoning as the Demon.** Its
    seat was worked out at deal time and never rechecked.

Eleven of the sixteen readings are produced, and 804 tests pass.

<details><summary>the original plan</summary>

**Flowergirl** asks whether the Demon voted, **Town Crier** whether a
Minion nominated. The board records both, but the simulator has no
concept of a day beyond who was executed.

  * Give the simulator votes and nominations: who nominated whom, who
    voted, and let the execution follow from that rather than being
    chosen at random.
  * Then both readings fall out.

Worth doing for its own sake — an execution picked at random is the least
realistic thing the simulator does, and it feeds every game the
calibration will eventually use.

**Done when** votes and nominations appear in the transcripts and both
readings are produced.

</details>

---

## Phase 6 — The three that change the board  ✅ done

All three are simulated and **no board comes out impossible** across
twenty-five Sects & Violets games. All sixteen readings are producible.

`role_at` works from a general change list now rather than assuming every
change is a Demon handover, and there is a `side_at` beside it for the
cases where side and character move independently — a Snake Charmer swap,
a Pit-Hag creation.

Two real bugs found:

  * **A Vortox was falsifying choices**, which it does not do. Ten row
    types are marked as choices now. And underneath that, the
    **Philosopher's gained ability was immune to a Vortox** — it returned
    GENUINE without checking, so a Philosopher holding the Clockmaker
    gave the true answer where the real Clockmaker could not.
  * **`demon_at` read the deal rather than the changes**, so a Demon that
    swapped away with a Snake Charmer went on killing from a seat that
    was no longer the Demon.

And a third, which the failing test turned out to be pointing at rather
than being wrong about: **`_make_false` was flipping `swapped`**. A
Vortox falsifies information, not choices, and whether a Snake Charmer
swapped is not something anybody told it — so a charmer that chose an
ordinary player came out claiming it had swapped with them, which cannot
happen. Every boolean was being flipped by name, and two of them —
`swapped` and `triggered` — record what happened rather than what was
heard.

Thirty games, no impossible boards, all sixteen readings produced.

<details><summary>the original plan</summary>

**Philosopher**, **Snake Charmer** and **Pit-Hag** do not report
information, they *change who holds what* — and the simulator has no way
to express that mid-game.

  * A seat's character becomes a function of time, as it already is for
    the Demon after a handover.
  * Then each of the three is a small rule on top.

The hardest of the remaining phases, and the one most likely to find
another solver bug, since these three are the least exercised parts of
the transition machinery.

**Done when** all sixteen readings are produced and games on all three
scripts come out legal.

</details>

---

## Phase 7 — Calibration  ◐ measured, not yet tuned

`tools/calibrate.py` buckets every seat-reading from a pile of played
games and compares what the solver claimed against what happened. 250
games, 2,250 readings:

    is this seat evil?
      bucket     said   happened   readings   gap
        0-10      3.3%     11.6%        861     +8.4
       10-20     15.0%     11.5%        364     -3.5
       20-30     24.7%     29.9%        338     +5.1
       30-40     34.8%     38.0%        284     +3.2
       40-50     45.0%     39.4%        155     -5.6
       50-60     54.2%     31.8%        110    -22.4
       60-70     64.6%     37.3%         51    -27.3
       70-80     74.6%     42.5%         40    -32.1

**The middle is honest and the top is not.** Below 50% the solver is
within a few points. Above it, everything it is confident about is worth
roughly 35-40% — a seat called 75% evil is evil about 42% of the time,
and one called 95% about 32%.

That is a systematic overconfidence, not noise: the gap grows steadily
with the claimed figure and the pattern repeats in the Demon table more
mildly (worst -13.3 at 40-50).

**And the cause is not what it looks like.** Of the seats called 70%+
evil that were actually good, **nineteen of twenty-eight were claiming
honestly** — not hiding, not chaos-claiming. So this is not the
Townsfolk-lie gap. The solver is over-punishing honest players when the
evidence points at them, which means something in the weighting is too
sharp rather than something in the search being too narrow.

**The confirmed marker is built** — a "checked out" tick on each ledger
row, worth an odds multiplier of 2.5 on its source really being that
character. Evidence not proof, accumulating per reading, never reaching
certainty, and not offered on a Virgin or Slayer row because those are
proof already.

**Before it can improve calibration, the simulator has to decide when a
table would tick it**, and that is a modelling decision rather than a
rule. The honest version is "a reading that was true *and* the table
could have established it" — an Undertaker's reading confirmed only once
the seat it read is settled by other means. The cheap version is "a true
reading from a working seat, some of the time".

Worth choosing deliberately: the cheap version hands the solver free
information a real table would not have, and calibration measured
against it would look better than the solver deserves.

**Two theories tested and both wrong**, which is worth as much as a fix
since either would have led to tuning the wrong thing. The silent Drunk
was not the cause — it speaks now and the table is unchanged. Nor were
missing confirmations: the marker is built and used, and the gaps moved
by a point or two.

**What the trail does show.** Confidence does not scale with evidence:

    readings on the board    confident calls   right
    1-3                                   28     18%
    4-5                                   26     43%
    6+                                    25     52%

A board with one or two readings can still produce a 70% call, and those
calls are right about a fifth of the time. That is the shape of the
overconfidence — not a character being mispriced, but the solver reaching
certainty on almost no evidence.

**A candidate, not yet a conclusion.** `NIGHT_DEATH_EVIL_PENALTY` is
0.05, a twentyfold swing on a single fact and by far the sharpest
constant. Raising it to 0.25 took confident calls from 38% right to 45%
across ninety games — suggestive, and nowhere near enough games to act
on. It needs a proper sweep across several hundred, and the sensitivity
tool already exists for exactly that.

**Next**: sweep it properly. The sensitivity sweep says which ones
matter; this table says which direction to move them. Do not tune
against a single run — the buckets above 80% are thin even at 250 games.

<details><summary>the original plan</summary>

The point of all of it. Across hundreds of games: of the seats the solver
called 30% evil, how many were?

  * Bucket every reading from every played game.
  * Compare the claimed probability against what actually happened.
  * Then, and only then, tune the judgement-call constants —
    `POISON_HIT_PENALTY`, `OUTSIDER_HIDING_PENALTY` and the rest — against
    evidence instead of instinct.

**Needs phases 4 to 6 first.** Calibrating against a simulator that can
only produce a third of a script's readings would measure that third and
call it the truth.

**Done when** there is a calibration table and at least one constant has
moved because of it.

</details>

---

## Not a phase: the standing limit

A Townsfolk claiming to be a *different* Townsfolk is a world the search
never generates, in any mode. `TOWNSFOLK_LIE_PENALTY` has therefore never
been reachable. Repair-on-demand covers the impossible boards and not the
merely misleading ones, and a board can be **confidently wrong** with
nothing inside the solver able to tell.

Fixing it needs the search to afford that lie, which today it cannot —
letting every Townsfolk claim be any Townsfolk takes a nine-player board
from a hundred worlds to a quarter of a million.

Worth revisiting after phase 7, when there are numbers to say how much it
actually costs in practice.


---

# What comes after phase 7

Phases 1 to 6 are done and phase 7 has its measurement. These are the
next pieces, again sized to finish in one sitting each. Say **"do phase
8"** and that is what gets done.

They are ordered so that no phase depends on one below it — except that
**phase 8 comes first**, because the tree has not been fully checked
since the confirmed marker and the trust wiring went in.

---

## Phase 8 — Verify and package

The four quarters have not run since `confirmed` and `trustSel` landed,
and the packaged zip predates both. Nine new tests exist and pass
individually, which is not the same as the tree being green.

  * Run the four quarters.
  * Fix whatever they turn up.
  * Rebuild, repackage, upload.

Dull, and the shortest of these. Everything after it is easier to trust
once it is done.

**Done when** four quarters are green and the zip is current.

---

## Phase 9 — Sweep the sharp constant properly  ✗ dropped

Phase 10 answered this without needing it: the night-death penalty
is not the lever, and sweeping it would have found a number that
moved the table without touching the cause. Left here because a
dropped plan is worth as much as a finished one when the reason is
written down.

<details><summary>the original plan</summary>

`NIGHT_DEATH_EVIL_PENALTY` is 0.05 — a twentyfold swing on one fact, and
by far the sharpest number in the file. Raising it to 0.25 took confident
calls from 38% right to 45% across ninety games, which is suggestive and
nothing more: ninety games gives about twenty confident calls, and that
difference could be noise.

  * Several hundred games per value, at 0.05, 0.15, 0.25, 0.4.
  * Report the calibration gap at each, not just the confident-call rate.
  * Move the constant only if the improvement survives the larger sample,
    and only in both languages together.

The sensitivity tool already sweeps constants; this needs it pointed at
calibration rather than at world counts.

**Careful about**: tuning one constant to fix a symptom several might be
causing. If 0.25 helps but the gap stays above 30 points, the answer is
probably not this number alone.

**Done when** the sweep is run at a defensible sample size and the
constant has either moved or been ruled out.

</details>

---

## Phase 10 — Why confidence does not scale with evidence  ✅ done

The finding worth understanding, and possibly the real fix.

    readings on the board    confident calls   right
    1-3                                   28     18%
    4-5                                   26     43%
    6+                                    25     52%

A board with one or two readings should not produce a 70% call at all,
and when it does it is right about a fifth of the time. One case: a Drunk
read at 71% evil on a single reading with eleven thousand worlds still
standing.

Eleven thousand worlds and a 71% call means the *weighting* is doing
almost all the work and the evidence almost none. Worth looking at
directly rather than through a constant:

  * On a board like that, which factor in `prior_weight` produces the
    spread? Print the weight of the top few worlds and see what separates
    them.
  * If a single prior dominates when there is little evidence, that is
    the thing to soften — and softening it is different from softening
    every constant.

### What is established so far

Reproduce with **seed 542 on Trouble Brewing**, nine players, three
nights: one Librarian reading, eleven thousand surviving worlds, and
seat 9 — really the Drunk, honestly claiming the Monk — read at 71% evil.

Comparing a world with an evil seat 9 against a good one:

    evil at 9: prior 0.1050  x cost 0.35  =  0.0367
    good at 9: prior 0.0032  x cost 0.35  =  0.0011

**The costs are identical.** The whole 33x gap is in `prior_weight`, and
the evidence contributes nothing to separating them.

Both worlds have the same *shape* — two evil bluffing, one good hiding —
so it is not the count of liars. The difference is *which* seat hides:
the good world needs an Outsider hiding behind the Monk claim at seat 9,
the evil world gets an Imp bluffing as the Monk for free.

But `OUTSIDER_HIDING_PENALTY` is 0.35, which is a 3x gap and not 33x. So
something else multiplies on top, and the candidates are all in
`prior_weight`: `BLUFF_COLLISION_PENALTY`, `READ_ODDS_STEP` and
`DRUNK_SUSPICION_STEP`.

**Next step**: print each factor of `prior_weight` separately for those
two worlds. It is a few lines and it names the culprit outright.

### Answered

On seed 542 the two competing worlds cost the *same* — 0.35 each — and
differ 33x in prior. Printing every factor:

    EVIL at 9:  0.35 (hiding) x 0.3 (bluff collision)              = 0.105
    GOOD at 9:  0.3 x 0.3 (two collisions) x 0.35 x 0.1 (night death) = 0.00315

The extra 33x is one more bluff collision times a night death landing on
an evil seat. And across ninety games, **every one of the twenty-three
confident calls happened on a board with a night death** — the solver is
reasoning from who died, not from what was read.

**Softening the night-death penalty does not fix it.** At 0.25 instead of
0.05 the 60-80 bucket improves from 32% to 39% and the 80-100 bucket gets
*worse*, 53% to 42%. Both within noise. So phase 9 as written is not
worth running: it would sweep a constant that is not the lever.

**The finding is structural.** No single penalty is too sharp. The
problem is that several sharp penalties **multiply** on a board with
almost no evidence, and nothing stops them compounding: 0.3, 0.3, 0.35
and 0.1 together produce a 33x swing out of facts that individually mean
very little.

**Done when** it is known what makes a near-empty board confident. ✅

---

## Phase 13 — Stop the penalties compounding  ✗ superseded

Aimed wrong. It would damp the prior on *every* board to fix a problem
that only appears on thin ones — flattening Bad Moon Rising, which is
already reasonable, to help Trouble Brewing. Replaced by phase 15.

<details><summary>the original plan</summary>

Phase 10's finding, made into a change. No single penalty is too sharp;
the problem is that several **multiply** on a board with almost no
evidence.

The obvious shape is to damp the *product* rather than any one factor —
raise `prior_weight` to a power below one, which softens a stack of
penalties without changing which world is favoured. A first attempt at
measuring this ran out of time, and the reason is worth knowing: a
flatter prior leaves more worlds in play, so the damped run is
substantially slower than the undamped one.

  * Measure at powers 1.0, 0.7 and 0.5, in the background, one value per
    run so a timeout loses one measurement rather than all of them.
  * The baseline at power 1.0 is already measured:

        0-20: 11%   20-40: 34%   40-60: 37%   60-80: 32%   80-100: 53%

  * Damping should pull the top buckets down toward their true rate
    *and* leave the bottom ones alone. If it flattens everything equally
    it has made the solver vaguer rather than better calibrated, and is
    not worth having.

**Careful about**: this changes every board, not just the confident ones.
Both languages, the whole corpus, and the conformance figures will move.

**Done when** the damping is measured at three powers and either adopted
with the corpus regenerated, or rejected with the numbers written down.

</details>

---

## Phase 14 — Make the harness sample  ✅ done

Four structural fixes, and only the first was the one I expected:

1. **Sample wide boards.** One in twenty-two hit 263,594 worlds — four
   seats had softclaimed "never", which on Sects & Violets narrows
   twenty-five characters to ten apiece. 430s to 11s.
2. **The sampler had no good-lies fallback.** `solve` turns them on when
   a plain search finds nothing; the sampler did not, so it returned
   *nothing at all* on the first simulated board it was handed.
3. **A tiny estimate needs sampling too.** A board that fits nothing is
   the expensive one: `pilot_size` reports zero and then
   `solve_or_repair` opens nine claims in turn with good lies allowed.
   Three boards took 40, 147 and 296 seconds while the pilot said 0, 0
   and 195.
4. **The gate has to match `_CORNERED`.** Having found (3) I picked 40
   out of the air; boards estimating 99 and 195 still repaired and still
   cost 158s and 294s. Their surviving world counts were 3 and 14 — both
   under the solver's own cornered threshold, which is the number that
   actually decides whether repair fires.

Validated against enumeration on 54 boards where both are possible:
median worst-seat difference 1.8 points, worst 6.2.

**The lesson, and it took three wrong guesses to learn.** An average hid
the shape completely — 18 seconds a game was one 430-second outlier and
twenty-one fast ones. Logging every game and reading the distribution
took one command and answered it immediately.

Two measurements have now failed to finish: Sects & Violets calibration,
and twelve- and fifteen-player Trouble Brewing. Both hit the same wall —
full enumeration on a board with many worlds.

This is not an optimisation any more. It is the thing blocking the rest
of the measurement work, and the sampler already exists.

  * Point `calibrate.py` at the sampler when the world count is large,
    rather than enumerating.
  * Check a sampled table against an enumerated one on a board small
    enough to do both — the numbers should agree within a point or two,
    and if they do not the sampler is not measuring the same thing.
  * Then finish the Sects & Violets table, and answer whether a
    fifteen-player table is better calibrated than a nine-player one.
    More players means more information *and* more worlds; which wins is
    an open question.

**Done when** a Sects & Violets calibration completes and the sampled
figures are shown to match enumerated ones where both are possible.

---

## Phase 15 — Soften confidence when evidence is thin  ✗ tried and reverted

Built, measured, removed. The measurement is worth more than the change
would have been.

The idea: below about four weighed readings, raise `prior_weight` to a
power under one, so a stack of penalties stops separating worlds
thirty-fold on the strength of two or three coincidences. It ranked
worlds identically and touched nothing else.

**Trouble Brewing barely moved**: 40.8 to 40.7. Only nine of thirty-four
confident calls come from thin boards; the rest have four or more
readings and were untouched by design. The earlier "1-3 readings, 17%
right" split was real, but those boards are a minority of the confident
calls.

**And damping cannot fix even those.** On the board that prompted all
this, the suspected seat is evil in **50.6% of surviving worlds,
unweighted**. No reweighting gets below that. Pushing the floor from 0.45
to 0.1 moved the reading 58.8% to 55.9% and would asymptote at 50.

**It made Bad Moon Rising worse**, 11.5 to 20.1 — the exact failure this
phase was written to watch for. A change that fixes one script by
spoiling another is not a fix.

### What this actually establishes

Thin-board overconfidence is a property of the **world population**, not
of the weighting. Half the legal worlds have that seat evil, so any
honest summary says about half. Making the solver quieter there means
changing *which worlds are legal* — more constraints, not different
weights — and that is a much larger question than a constant.

It may also mean the solver is behaving correctly and the calibration
target is wrong, which is what a player said early on: those seats would
be suspects at a real table too. A board with one reading genuinely does
not distinguish nine seats, and a solver that says so is not
miscalibrated, it is honest.

<details><summary>the original plan</summary>

Phase 11's finding, made into a change, and pointed at the right target.

A board with one or two readings should not produce a 70% call. It does
because several penalties multiply, and nothing in `prior_weight` knows
how little is actually known. So the correction should scale with the
evidence rather than apply everywhere:

  * Damp the prior by an amount that depends on how many *weighed*
    readings the board has — strongly on a board with one, not at all on
    a board with six.
  * Measure on Trouble Brewing, where the problem is, **and** on Bad Moon
    Rising, where it is not. The second is the real test: a change that
    fixes one script by spoiling another is not a fix.

**Careful about**: "number of readings" is a crude measure of evidence. A
single Washerwoman that names two seats says more than three Chef counts.
If the crude version works, good; if it half-works, that is probably why.

**Done when** the thin-board buckets improve on Trouble Brewing and Bad
Moon Rising is left where it was.

</details>

---

## Phase 11 — Calibrate the other two scripts  ✅ done

    worst gap in a bucket with 30+ readings
      Trouble Brewing    40.8
      Bad Moon Rising    11.5
      Sects & Violets    11.4

**Bad Moon Rising is far better calibrated.** A 75% call there is right
two thirds of the time; on Trouble Brewing about a third. That is not
noise, and it changes what the overconfidence is.

**The cause is evidence density.** Splitting Trouble Brewing's confident
calls by how much was on the board:

    1-3 readings:  18 calls, right 17%
    4+  readings:  29 calls, right 45%

Boards average 3.7 readings, so about half sit in the thin band where a
confident call is right one time in six. Bad Moon Rising has more
characters waking every night and fewer starved boards — same machinery,
different diet.

**Trouble Brewing is the outlier.** The other two land within a point of
each other and are roughly three times better calibrated — on Sects &
Violets a 74% call is right 73% of the time, and the 60-70 bucket is
actually *under*-confident. Both scripts have more characters speaking
every night; Trouble Brewing has thin boards, and half its confident
calls come from one or two readings.

Everything measured so far is Trouble Brewing. The simulator plays all
three now, so Bad Moon Rising and Sects & Violets can be measured too —
and they are different enough to be worth it: Sects & Violets droisons
four ways and has a Demon that falsifies information wholesale.

  * A calibration run per script.
  * Compare the shape. If the overconfidence is the same everywhere it is
    structural; if it is much worse on one script, that script has
    something specific wrong.

**Done when** there are three tables and a note on whether they agree.

---

## Phase 12 — A game to read, again  ✅ five bugs, one open

Reading four Sects & Violets transcripts found five, all in the
simulator:

  * **A red herring was dealt without a Fortune Teller.** It is that
    character's herring; a board without one should not have it.
  * **The Dreamer showed neither role true.** It read what the target
    *believes it is*, so a Drunk holding a Monk token was shown as the
    Monk and the reading was false while nothing was wrong with the
    Dreamer.
  * **A Barber execution produced no swap.** The simulator had no Barber
    at all — the solver has modelled it since the Barber went in, and no
    played game ever contained one.
  * **A Sage killed by the Demon said nothing.** The death-trigger list
    held only the Ravenkeeper, so a Sage or a Klutz dying at night stayed
    silent.
  * **A Philosopher did not use what it took**, and a Pit-Hag's creation
    was invisible to the seat it happened to. Both from asking
    `d.roles[seat]` — the *dealt* character — instead of the timeline.

### Still open: seed 3 comes out impossible

One board in twenty-five now fails, and it is a Snake Charmer swap the
solver refuses. What is established:

  * The row is legal: charmer at seat 1, Demon at seat 4, target seat 4,
    and the solver's own `demon_at` agrees.
  * `a_snake_charmer_takes_the_star` **produces the right chain** when
    called directly, and the row `holds` under it.
  * And yet `explanation_cost` on a state containing only that row
    returns None.

So the chain exists and satisfies the row, and something *else* rejects
the world. The Barber rule offers 37 options on that board; the likely
answer is that chains from different rules are combined in a way that
loses the Snake Charmer's, or that a combination is chosen which the row
then fails under.

**Next step**: print the chains `possible_timelines` actually assembles
for that board, against the one the Snake Charmer rule offers alone.

The last one found the ceremadness mislabel, the Vigormortis capacity bug
and the Vortox-and-choices rule. It is the cheapest thing here per bug
found, and nothing has been read since the simulator learned three
scripts, days, and character changes.

  * Generate transcripts across all three scripts, including games with
    a Pit-Hag creation and a Snake Charmer swap, which have never been
    looked at by anybody.
  * Read them for whether the *Storyteller* behaved.

**Done when** somebody who knows the rules has read a game from each
script.


---

## Mixing before adding  ✅ done

Before any experimental character goes in, the characters already
implemented had to be checked against each other. On a homebrew script
they can be mixed freely, and the published three only ever exercise each
character against its own neighbours.

`tools/play_games.py` builds deliberately awkward scripts — several
droison sources at once, more than one character that moves roles around,
demons from three different scripts — and forty games on those went from
**6 impossible boards to 0**.

Nine bugs, none of which can arise on a published script. They are listed
in the README under "Characters that have never met".

**Keep this as a standing gate.** Every new character gets forty
mixed-script games before it is called done. The harness exists and is
clean, so the check costs one command.


---

## A droisoned character cannot misregister

**Rule, from the table**: a Storyteller may choose freely what a droisoned
*information* role yields, because the information becomes arbitrary. But
a plain ability simply does not function — and registration is a plain
ability. A droisoned Recluse cannot register as evil.

**The solver does not know this.** `registers_as_role(actual, claimed)`
takes two characters and nothing else: no seat, no phase, no world. So it
cannot tell whether the Recluse was poisoned at the time, and an
Investigator shown a droisoned Recluse as the Poisoner reads as legal
when it is not.

This is not a small change. Registration is asked about in a dozen
places, and every one would have to pass a seat and a phase, and have a
world to ask about impairment. It also cuts the other way: worlds
currently kept would be ruled out, so the corpus moves and every
misregistering board changes.

Worth doing, and worth doing deliberately rather than alongside a new
character.

## A marker for what a Vortox touches

Suggested at the table, and right: a Vortox falsifies **information
roles** and nothing else. Rather than asking the question character by
character — which is what I have been doing, and getting wrong — the
catalogue should carry a flag, and the inversion should read it.

That also makes the answer for a new character a one-line decision
instead of a conversation.

## Learning a new character is not waking

Also from the table: being told your new role when you get one is a
**game rule**, not any character's ability. So it does not come from the
Farmer, and a Chambermaid does not count it.

The same applies to a Pit-Hag creation, a Snake Charmer swap and a Barber
swap — none of those wake anybody for their own ability. Worth checking
the Chambermaid against all four.


---

## The Farmer  ✅ done — 0 impossible boards in 40 mixed games

Implemented on both sides. Every behaviour checked in isolation:

  * fires on **any** night death, not only the Demon's; an execution does
    nothing;
  * offers "nothing happened" alongside every heir, which is the
    droisoned case — whether a seat was droisoned is *chosen* by the
    impairment plan, and transitions are settled before it runs, so both
    stories are offered and the plan pays for whichever it needs;
  * heirs by **registration**: a Spy can inherit and stays evil, an Imp
    cannot;
  * and it **chains**.

Chaining took a fix worth remembering: `find_at` returns the *first* seat
holding a character, which is the Farmer that was dealt — and it goes on
being a Farmer in the base world after it dies, so the chain never looked
past it. It collects every holder now. The Farmer is the first character
built where several seats genuinely hold it across a game.

### The gate: 2 of 40 boards impossible

Both need tracing. **Seed 16** is the further one:

  * A Zombuul kills seat 4 and a **Gambler** guesses wrong and dies on
    the same night — two causes for two deaths, which is legal.
  * The death record alone cannot explain it, and **it still cannot with
    the Gambler's guess present**. So the solver's Gambler cause is not
    firing on a board where it should.
  * Worth knowing: that guess named the Zombuul on a seat that had
    already swapped away with a Snake Charmer, so the guess was wrong for
    an interesting reason.

**Next step**: call the Gambler cause directly on that board and see why
it declines. `a_gambler_dies_guessing_wrong` requires a guess recorded
for that night, which there is — so it is something further in.

Seed 9 is untraced; the Farmer was dealt but never handed on, so it is
probably unrelated to the Farmer.


---

## Prevention is failure, and nothing modelled that

From the table, while building the Acrobat: **an ability that was
*prevented* counts as one that went wrong.** An Acrobat whose pick was
droisoned should die; a Tea Lady beside it stops that; nothing was
poisoned, and yet a Mathematician counts one more.

Nothing in the solver treats prevention as failure. `_possible_impairment_
counts` counts *impairment*, and the two are not the same thing — the
Acrobat is the first character where they come apart visibly, but it is
unlikely to be the only one. A Soldier surviving the Demon is an ability
prevented, and so is a Monk's guard landing on the seat the Demon chose.

Worth doing properly rather than as an Acrobat special case: the question
is "which abilities did not do what they say", and impairment is only one
reason among several.


---

## The Acrobat  ◐ built, gate not passed

**Each night\*, choose a player: if they are or become drunk or poisoned
tonight, you die.**

Built in the solver and the simulator. The design question the rules
forced is the interesting part: because a seat can *become* droisoned
after the Acrobat has chosen, the death cannot be resolved in night order
at all. It is settled in the **impairment plan**, where an Acrobat death
requires its pick impaired.

    Empath reads falsely (so it was poisoned)   0.35
      + Acrobat picked it and DIED              0.35   consistent

### Neither a living nor a dead Acrobat says anything yet

Both directions were tried and both are wrong for the same underlying
reason: the inference needs the impairment plan and the death causes
settled *together*, and they are settled separately.

**A surviving Acrobat** means the pick was clean **or** the Acrobat was
itself droisoned — a disjunction, and the plan takes sets of seats, not
alternatives.

**A dead Acrobat** looked solid: its pick was droisoned and it was
working. But an Acrobat can die of anything. On one board the Demon took
it on a night its own pick was clean and it was poisoned besides, and
demanding both ruled a legal board out. The death machinery already
chooses which cause explains each death and has an Acrobat cause among
them; the constraint ran regardless of what it chose.

So the Acrobat is modelled as far as it goes — the pick is recorded, the
death is explicable — and the part that would make it *informative* is
not built. Doing it properly means the plan and the causes deciding
together, which is a real change to how a night is settled.

### The old note, kept because the reasoning still applies

The first version had a living Acrobat *forbid* its pick being droisoned.
That is wrong: it means the pick was clean **or** the Acrobat was itself
droisoned, since a droisoned Acrobat does not function. A disjunction —
and the plan takes sets of seats that must and must not be impaired, with
no way to hold "one of these two things".

A board where both the Acrobat and its pick were poisoned is perfectly
legal, and forbidding ruled it out. Saying nothing loses information and
keeps worlds that happened, which is the direction to err in. Holding the
disjunction properly would mean the plan taking alternatives, which is a
real change.

### The gate: 4 of 40, two traced

  * **A Minstrel was never in the simulator's `droisoned_at`.** It
    silences the whole table for the night after a Minion is executed,
    and the Acrobat exposed it: an Acrobat that lived contradicted a
    solver that knew the table was silenced. Added.
  * **Fixing that produced a new failure on the same board.** With
    everybody silenced on night two, three seats still died — and a
    silenced Demon should not be killing. The Shabaloth kills twice, so
    the deaths look like a Demon acting through its own silencing.
    **Next step**: make `_demon_kills` return nothing when the Demon is
    droisoned.
  * Seeds 16 and 26 are untraced. Seed 26 has no Acrobat dealt at all, so
    it is probably unrelated.


---

## Seed 26: a Pukka, a Fortune Teller, and a repeat cost

Untraced to the end, and narrowed to this. Reproduce with seed 26 on an
awkward script with the Acrobat forced in, twelve players, four nights.

  * The Fortune Teller reads on all four nights and every reading
    explains fine **alone** (0.0171 each).
  * Adding them one at a time, the board survives three and dies on the
    fourth.
  * Nights three and four ask the *same two seats* and get different
    answers, so one of them must have been droisoned — which is correct,
    and the simulator poisoned it on night four.
  * The Pukka can reach the Fortune Teller on every night, so the plan
    has somewhere to put it.

So the arrangement exists and the plan will not find it. The suspicion is
**`POISON_REPEAT_PENALTY`**: a source landing on the same seat twice is
charged 0.7, and with a chain of nights the product may fall below
whatever floor the search keeps. That would make this a *pricing* failure
rather than a legality one — the board is not impossible, it is too
expensive to survive.

**Next step**: print the plan's cost per night for that board and see
whether it is being refused or merely priced out.


---

## Night order  ◐ data in, simulator sequenced, solver untouched

`data/roles.json` is vendored from the townsquare repository that backs
botc.app, and the catalogue reads two numbers from it per character:
`first_night` and `other_night`. **Un-renumbered**, so a character added
later drops into its true position without disturbing anything, and the
data stays checkable against its source.

    Poisoner    other  7
    Imp         other 24
    Assassin    other 36
    Acrobat     other 39
    Farmer      other 48

Both cases from the table check out. The Imp acts before the Assassin, so
a starpass to an Assassin costs it the night — by slot 36 that seat is
holding the Imp. And the Acrobat sits between the Poisoner and the
Farmer, which is what makes "are **or become** droisoned tonight" more
than a turn of phrase.

`honest_info` walks seats in night order now rather than seat order, read
off what each seat *believes* it is — a Drunk holding a Fortune Teller
token acts in the Fortune Teller's slot.

### The gate moved rather than improved: 4 of 40

Seeds 27, 38 and 39 are **new** — they passed before the night was
ordered. Seed 26 is the Pukka-and-Fortune-Teller board from before, still
open.

New failures are the point of the exercise, not a regression: a board
that only holds together when characters act in the wrong order was
always wrong, and now it says so. Each needs tracing.

### What is still not done

The **solver** knows nothing about any of this. A night is still settled
in three separate passes — transitions, death causes, impairment plan —
and none can see the others. That is what defeated the Acrobat in both
directions, and it is the change the ordering was meant to enable.

The simulator failure list above is what should scope it.


---

## Where this stands, and what is unshipped

**Quarters**: 1, 2 and 3 green (151, 297, 239). Quarter 4 has **two
failures**.

Quarter 1 caught a real gap first time round: the Acrobat's death cause
was registered in Python and not in JavaScript. The two registries must
hold the same rules in the same order, and the cross-language check is
what noticed. Fixed.

### The two open failures

**`test_no_board_is_impossible`**, seed 24 on Sects & Violets. The
Mathematician is the row that breaks — the *third* time it has been, and
that is not a coincidence: it constrains every other reading on its
night, so it is where a disagreement anywhere on that night surfaces.

What is established, and it is odd:

  * the row alone costs 1.0 and `holds` is True;
  * the simulator droisoned nobody at N2;
  * the solver's range at N2 is (0, 0), with and without the deaths;
  * the Mathematician said 0.

So both sides agree on the number, the row holds in isolation, and the
board is still refused. The conflict must be with a *different* night —
the Mathematician's count is per night, but the impairment plan is
settled across all of them at once, and a source forced somewhere on
night three could make night two unsatisfiable.

**Next step**: print the plan's chosen impairment for every night on that
board, not just N2.

**`test_and_a_night_death_separately`** is untraced. It checks a
transcript contains a night death, so it is probably the ordered night
changing which seeds produce one — a test pinned to a seed again.

### Unshipped

Nothing has been packaged since the nine mixed-script fixes. Waiting: the
Farmer, a partially-modelled Acrobat, the night order, and the Minstrel
and `working()` fixes.


---

# Phases, from here

Each sized to finish in one sitting. Say **"do phase A"** and that is what
gets done. Ordered so none depends on one below it.

---

## Phase A — Settle the Mathematician, then package  ✅ done

**The cross-night theory was wrong**, and worth recording why: the
`(1, 1)` range that suggested it came from a stale interpreter. A fresh
one said `(0, 0)`, agreeing with the Mathematician exactly. An hour could
have gone into a redesign chasing that.

The real cause was the fourth droison source missing from the
simulator's `droisoned_at`: **a Philosopher that takes an ability drunks
whoever really holds that character.** Seat 2 took the Seamstress and
seat 7 really was one, so seat 7 was drunk and the Mathematician counted
nought. The solver models it; the simulator did not.

The other failure was a seed-pinned test again — the ordered night left
that game with no night death in it. It searches now.

833 tests, four quarters green, packaged.

Two things, and the first is one command.

**The cross-night theory.** On seed 24 the Mathematician says 0, the
simulator droisoned nobody, and the solver's range for that night is
(0, 0) — and the board is still refused. Everything agrees in isolation,
so the conflict must be with a *different* night: the count is per night,
but the impairment plan is settled across all nights at once, and a
source forced somewhere on night three can make night two unsatisfiable.

Print the plan's chosen impairment for **every** night on that board. If
the theory holds, this is not a bug at all — it is the Mathematician
constraining a cross-night plan, which is the character working. Worth
knowing before any redesign, because the new design has to hold it too.

**Then package**, with the two failing tests marked known-failing rather
than deleted. A build has been waiting behind them for a long time: the
Farmer complete and through its gate, the night order, the Minstrel and
`working()` fixes.

**Done when** the theory is confirmed or killed, and there is a zip.

---

## Phase B — The solver's night order  ◐ design agreed, not built

The **Goon** settled it: the first player to choose it tonight is drunk,
and the Goon becomes *their alignment*. A Sailor acts before a Poisoner,
so if both choose the Goon it stays good. No set of "who was droisoned"
holds that — it needs the order, and it changes alignment rather than
merely whether an ability worked.

So constraint-passing is not enough and the solver has to walk the night.

**But the walk is cheaper than feared.** Eleven choices are already
recorded, because good players announce what they did — Acrobat,
Courtier, Exorcist, Gambler, Innkeeper, Klutz, Moonchild, Philosopher,
Pit-Hag, Sailor, Snake Charmer. The hidden ones are the evil choices, and
those are exactly what the impairment plan already searches over.

So the shape is **propose, then walk**: the plan proposes an assignment
of the hidden choices as it does today, and a candidate is checked by
*replaying* the night in slot order rather than by set arithmetic. The
search space is unchanged; only the evaluation is.

### The replay works  ✅

`tests/nightwalk.py` walks a night slot by slot, and
`tests/test_nightwalk.py` checks it against nights the simulator already
played.

**120 of 120 nights reproduced.** The walk is handed the hidden choices —
where the Poisoner went, who the Demon took — because in the solver those
come from the impairment plan, which already searches over exactly them.
The walk's job is to *check* an assignment, not to guess one.

And the Goon comes out right, which is the whole point:

    Sailor at slot 4, Poisoner at 7
      both choose the Goon  ->  good   (the Sailor was first)
      only the Poisoner     ->  evil

Order decides an *alignment* there, not merely whether an ability worked.

**What this de-risks**: the largest change in the project turns out to be
a change to how a candidate is *checked*, not an explosion in how many
candidates there are. The walk is about a hundred and fifty lines and
reproduced every night it was given.

**Eleven characters are in it now**: Poisoner, Sailor, Goon, Acrobat,
Philosopher, Courtier, Snake Charmer, Innkeeper, Monk, Soldier, Scarlet
Woman, and every Demon. Still 120 of 120 nights reproduced after adding
seven, which is the encouraging part — the walk did not need reshaping to
take them.

Twelve tests, and the ordering cases are stated explicitly rather than
left implicit:

  * a **Monk** guards at 12 and the Demon kills at 24, so the guard holds;
  * a **Snake Charmer** swaps at 11, so the seat that kills afterwards is
    the charmer's, now holding the Demon, and the old Demon is a poisoned
    good Snake Charmer;
  * a **Philosopher** at 2 drunks whoever really holds the character it
    took — and that seat may still have to act tonight;
  * a **Soldier** survives the Demon, but **not a poisoned one**, which
    the walk gets for free because the Poisoner acts at 7.

That last one is the shape of the whole argument: no rule says "a
poisoned Soldier dies". It falls out of walking the night in order.

**Nineteen characters are in it now**, adding the Exorcist, Devil's
Advocate, Witch, Pit-Hag and Pukka, and letting a Demon take more than
one seat.

    Trouble Brewing   100/100 nights reproduced
    Bad Moon Rising    78/100

The Bad Moon Rising gap is **the harness, not the walk**: every
difference is a Pukka or a Shabaloth, and the check is not handing them
the right hidden choices. A Pukka's death tonight is *last night's*
poison coming due, so the assignment needs a `pukka_due` for the night;
a Shabaloth takes two, and the harness reads only what the record shows
as dying, which loses a kill sunk into a corpse.

That is worth being precise about because it is easy to read as the walk
failing. It is not — the walk asks for an assignment and the harness is
giving it an incomplete one.

### The harness now hands over what it should

The simulator records two things it was throwing away: **what the Demon
aimed at** (a Shabaloth kill sunk into a corpse leaves no body, so
reading the deaths back gave an incomplete assignment) and the **Pukka's
history per night** (its death tonight is last night's poison coming
due, and the running value was overwritten before anybody could ask).

    Trouble Brewing   80/80 nights reproduced
    Sects & Violets   80/80
    Bad Moon Rising   68/80

Two scripts exact. The Bad Moon Rising twelve are all **missing** deaths,
never extra — the walk refuses kills the record shows, so something kills
that it does not know about. Adding the Grandmother's grief moved it by
one, so grief is not the cause.

**Next step**: on a differing night, print the walk's log beside the
record and find what killed the seat the walk left standing. The log
exists for exactly this and has not been used yet.

**Thirty-five characters left.** Each is a block in the same loop; the
pattern has not needed reshaping once in four batches.

### The next step is not to write code

Replay a night that is **already known**: take a simulated game, walk its
night in slot order, and check the walk reproduces what the simulator
recorded. If it cannot reproduce a night that was just played, it will
not reproduce one it has to infer — and that is worth finding out before
any of the three passes is touched.

`docs-design/night-order.md` sets out three ways to do it and recommends
one. It is written to be argued with, and the recommendation depends on a
question only somebody who knows the experimental characters can answer.

**The question**: how many characters need to see what happened at an
earlier slot in order to *decide what they do* — rather than merely to
decide whether their ability worked?

If it is only the second kind, constraint-passing is enough and the
search survives. If several are the first kind, the solver has to walk
the night the way the simulator does, and that is a much larger change
with a real risk of the search exploding.

The change the ordering was meant to enable, and the one that matters.

A night is settled in three passes — transitions, then death causes, then
the impairment plan — and none can see the others. That is what defeated
the Acrobat in **both** directions:

  * a surviving Acrobat means the pick was clean *or* the Acrobat was
    droisoned, and the plan takes sets of seats, not alternatives;
  * a dead Acrobat is only informative if its own ability killed it, and
    that is decided in a different pass.

The simulator already acts in order. The solver needs the equivalent: not
a sequence to execute, but a constraint that the events it infers could
have happened in the real order.

**Scope it before starting.** This is most of the solver, and the honest
first step is a written design rather than code — what replaces the three
passes, what a rule looks like afterwards, and how much of the existing
rule set survives.

**Done when** there is a design agreed at the table, not when code is
written.

---

## Phase C — The four ordered-night boards

Seeds 26, 27, 38 and 39 from the mixed-script gate, four different
causes, three of them *new* since the night was ordered. They only held
together when characters acted in the wrong order.

Worth doing after phase B rather than before: some may be exactly what
the redesign fixes, and tracing them twice would be waste.

**Done when** the gate is back to zero of forty.

---

## Phase D — Finish the Acrobat

It is modelled as far as it goes — the pick is recorded, the death is
explicable, no legal board is refused — and the part that makes it
*informative* is missing, because that needs phase B.

Also missing: **prevention as failure**. A Tea Lady stopping an Acrobat
death should make a Mathematician count higher, and nothing in the solver
treats a prevented ability as one that went wrong. That is broader than
the Acrobat — a Soldier surviving the Demon is a prevented ability too.

**Done when** the Acrobat constrains the plan and the gate stays clean.

---

## Phase E — The next experimental character

Sixty-eight of the released hundred and thirty-eight are not modelled.
The process works: state what I think it does, get corrected before
writing anything, list the interactions, implement in both languages,
then forty mixed-script games.

Worth choosing one **without** timing in its text until phase B is done.


---

## The walk, and what comparing readings is teaching

Twenty-five characters in, all three scripts still replaying every night,
and the readings pass now derives the Empath, Chef, Undertaker,
Chambermaid and Oracle.

**The Empath is exact**: 29 of 29 matched the simulator. That is the
first evidence the walk derives *information* correctly and not only
deaths, which matters because an Empath's count depends on who is alive
at its slot.

**The Oracle is not, and the reasons are instructive.** Comparing raw
gave 13 of 25. Three separate things were in the way, and only the third
is a real disagreement:

  * a **Vortox** falsifies the reading, so the simulator records a lie
    and the walk derives the truth — comparing them is meaningless;
  * a **droisoned Oracle** is told whatever the Storyteller likes, same
    problem;
  * with both excluded it is 18 of 23, and **five still differ**.

So the comparison harness has to filter to readings where a *true* answer
is owed, and that filter is itself a useful thing to have — it applies to
every reading character, not just the Oracle.

**Next step**: the remaining five. The Oracle counts the dead who are
evil, and the candidates are a Goon that turned tonight (counted by side
*now*, which the walk does) and whether a seat that died tonight is
counted at all. Print one and see.

**Twenty-eight characters left**, and the reading derivations are the
slower half: each needs its answer worked out and then compared against
the simulator with the filter above.


---

## The walk: fourteen readings verified, one open

    Empath 29/29   Undertaker 24/24   Chef 23/23   Oracle 23/23
    FortuneTeller 20/20   Ravenkeeper 2/2   Dreamer 22/22
    TownCrier 18/18   Flowergirl 14/14   Clockmaker 16/16
    Seamstress 15/15   Washerwoman/Librarian/Investigator 75/75
    Mathematician 26/27

### Two structural fixes came out of the Mathematician

**Standing droisonings are carried in.** The walk starts each night
fresh, so a Sweetheart's droison from the night it died, a swapped Snake
Charmer's, or a Courtier's three-day run were invisible to it. It cannot
count abilities that went wrong before it started watching. 13 of 27
became 23 of 27.

**A Philosopher's gain is a proper hidden choice now**, keyed by seat and
carried across nights. It was keyed by night — so a table with two
Philosophers could only name one — and a gain made on night one was
forgotten by night two. The test harness had been reaching into the
walk's internals to work around it, which is exactly the smell that says
the interface is wrong.

### The one open case

Seed 46, night 2, Sects & Violets. The **simulator contradicts itself**:
its own `droisoned_at` says seat 1 is droisoned, its Mathematician is
working and counts with `len(droisoned_at(...))`, and the row it recorded
says **0** where that expression gives 1.

So either the row was built from a different night's state, or something
mutates the droison set between the row being made and the game ending.

### Traced further, and the walk is right

The seat in question is a **Sweetheart**, killed by the Demon on that
same night. Its droison fires from the moment it dies, and the slots
settle who is correct:

    Demon kills          24
    Sweetheart droison   41
    Mathematician counts 71

So the droison is in force well before the Mathematician counts, and the
answer is 1. **The walk has it right and the simulator's row is wrong.**

Two things were checked and cleared along the way, both worth recording
so they are not re-checked:

  * readings are taken **after** the night's kills, not before;
  * the simulator's night order is correct — a Sweetheart at 41 does sort
    before a Mathematician at 71, despite `nights="never"`.

So the ordering is right and the row is still stale, which means the
Mathematician's count is being computed from something other than the
board at its own slot.

### The snapshot theory was wrong, and so was the next one

`honest_info` does **not** snapshot: it calls `d.working(seat, night)`
per seat. Cleared.

Nor is it the deal-versus-timeline pattern, tempting as that was — the
seat holds a Sweetheart in both the deal and the timeline.

What is now established, and it is stranger than either guess:

  * at the moment `honest_info(2)` runs, seat 3 has **already died**
    (`deaths` shows it), and `droisoned_at(2)` returns **empty**;
  * after the game finishes, the same call returns **seat 1**;
  * and seat 1 is not the Sweetheart's neighbour, so whatever droisons it
    is a different source entirely.

So the set genuinely changes between the row being built and the game
ending, and the thing that changes it is not the Sweetheart. Something
recorded *later* in the game is being read as though it were true at
night two.

**Next step**: print every source `droisoned_at(2)` finds, after the
game, with the seat and reason. One of them is claiming a droison for a
night that had not happened yet when the row was built — most likely a
rule reading a *later* death or change and comparing phases the wrong
way round.


---

## Twelve characters are dealt and never act

Found while looking for the Gossip, which turned out to be one of them.
Counting what the simulator *records* against what it *deals*, over 180
games across all three scripts:

    Innkeeper   Lunatic     Monk        Moonchild
    Poisoner    Professor   Sailor      ScarletWoman
    Spy         Sweetheart  Tinker      Witch

Each is dealt between thirteen and thirty-five times and produces
nothing: no reading, no change, no death.

**Some of these are fine.** A Poisoner's choice is hidden, so there is
nothing for the table to hear — but its *effect* shows in
`droisoned_at`, and that is checked separately. A Spy is shown the
grimoire and says nothing. A Lunatic is shown a night that never
happened.

**Others are simply missing.** A Monk should be guarding somebody; a
Sailor should be drunking one of two; a Witch should be cursing; a
Moonchild should be able to kill when it dies in daylight. The night-walk
has rules for all four, and the simulator never gives it a night where
they matter.

### Why this matters more than it looks

The walk is verified against nights the simulator plays. A character the
simulator never fires is a character the walk's rule for it has **never
been checked** — the Professor was withdrawn for exactly this reason, and
the same argument applies to the Monk, the Sailor, the Witch and the
Moonchild, whose rules are in the walk right now on the strength of my
reading of the cards alone.

So the coverage figure — 43 of 55 characters handled — is honest about
what is *written* and misleading about what is *verified*. Sixteen
readings are verified exact. The board-changing rules are much thinner
than that.

**Next step**: make the simulator fire them, starting with the Monk and
the Sailor, since both are simple and both are already in the walk
waiting to be checked. Then re-run the comparison and see which of my
readings of the cards were wrong.


---

## Silent characters made to act

Four of the twelve characters that were dealt and never acted now do, and
three of them found bugs on the way in:

  * **Sailor** and **Innkeeper** — both announce a choice, and adding
    them exposed that `_protected` knew only about the Soldier, that
    `droisoned_at` knew about neither of their drunks, and that early
    choices were being made after the kills they were supposed to
    prevent.
  * **Monk** — a hidden choice, like the Poisoner's. Verified **31 of 31**
    nights against the simulator, where before it was a rule written from
    the card with nothing to check it.
  * **Witch** — 47 curses across 60 games. Nothing happens on the night;
    the curse bites the next day.

**Moonchild** and **Tinker** are in as well, and the walk agrees on 10 of
12 nights containing one.

### The two that differ, and a caution about the probe

The failing comparison prints a board whose roles do not match the game
it is describing — the same seed produces **different roles under
different scripts**, and the diagnostic loop iterated over two scripts
while the follow-up printed only one.

So the two differences are real but **not yet correctly characterised**,
and the obvious next step is to make the probe print the script it is
talking about. Worth doing before drawing any conclusion: the last three
times a diagnosis looked obvious it was wrong, and twice the reason was
the probe rather than the code.

**Next step**: re-run that comparison with the script recorded alongside
the seed, then trace whichever board actually fails.


---

## The walk says when it has not been told

Three comparisons in a row failed because a probe forgot a hidden input,
and each time the failure pointed at the walk. Being under-informed
looked exactly like being wrong.

Two changes, and the second is the one that matters.

**`nightwalk.hidden_from(deal, night, heard)`** builds every hidden input
in one place, so a probe is one line instead of ten and a new character
is added once. That makes the correct path cheaper than the mistake —
which works better than resolving to remember.

**And the walk now records `untold`**: characters on the board that
always act, are alive and working, and that it was told nothing about. A
comparison can refuse to draw any conclusion until it is empty.

### It found three more silent characters immediately

Turned on, it flagged 41 of 180 fully-informed nights. Not noise — the
Sailor, Snake Charmer and Exorcist all *announce* what they did, the row
sits in `heard`, and `hidden_from` was reading none of them. Fixed, and
the count fell to 14.

The remaining fourteen are a genuine finding: **an Exorcist produces no
rows at all** across 180 games, like the Monk and the Sailor before it.
Another character dealt and never acting, whose walk rule has never been
checked.

The Demon is deliberately exempt from the warning: a Po may take nobody
and a Zombuul only kills after a quiet day, so an empty aim is a real
answer. Flagging it would cry wolf on every such night, and a warning
that cries wolf is one people learn to ignore.

**Next step**: make the Exorcist act, then the Snake Charmer's remaining
three, then re-check that `untold` is empty on every informed night —
which is the standing gate this is for.


---

## The Snake Charmer swap is immediate

Settled at the table. A charmer acts at slot 11 and every Demon at 24 or
later, so by the time the kill is made the charmer holds the Demon — and
it is the charmer's seat that kills. The old Demon is a poisoned good
Snake Charmer and kills nobody.

Both sides recorded the swap at `D{night}`, the day *after*, which had
the old Demon killing on the night it stopped being one. The night-walk,
which swaps at 11 and then looks up the Demon fresh, disagreed and was
right.

### Which resurrected an old problem, and named it properly

The solver's comment had warned that writing the swap at the night made
the charmer's own row read as **invented**: the speaker stops holding the
Snake Charmer at the very moment its row is attributed, so a world where
the swap really happened scored 0.4 against 1.0 for one where it could
not. Exactly backwards.

That warning was right, and the cause is now clear. **A row belongs to
whoever acted**, which is the board as it stood when the pass began. The
board *afterwards* is a different question. `role_at(seat, "N{night}")`
answers the second, so three nights of Snake Charmer rows were filed
under the seat the character ended up at rather than the seat that acted.

Fixed by snapshotting the board at the start of the early-choice pass.
Same shape as everything else this session: **a phase is not an instant**,
and two questions that agree almost always do not agree here.

    Trouble Brewing   solver 0 impossible | walk 40/40
    Bad Moon Rising   solver 0 impossible | walk 40/40
    Sects & Violets   solver 0 impossible | walk 38/40

**Next step**: the two remaining walk nights. Both are Sects & Violets,
which is where the Snake Charmer lives, so they are most likely the same
attribution question seen from the walk's side.


---

## The walk should start before the night, not after it

Raised at the table and correct: `role_at(seat, "N2")` already contains
every change stamped at N2, so the walk was starting from the board
*after* tonight and then walking the night — applying tonight's changes a
second time.

For a Pit-Hag creation that is invisible, because setting a seat to a
character it already holds does nothing. **For a Snake Charmer swap it is
a bug**: doing it twice swaps the pair back, and the seat holding the
Demon becomes a charmer again and kills nobody.

The walk now starts at the end of the previous day and *becomes* the
board by walking. Anything else is applying history twice and hoping it
is idempotent.

### But that exposed the real question underneath

Two nights still differ, and they are not a timing problem. On seed 17
the swap happened on **night one**; on night two the charmer — now the
old Demon, holding the Snake Charmer — points again, and its target is
the seat that now holds the Demon. So by the rules as written it swaps
**back**.

The simulator does not swap back. Its row says `swapped=False` for that
night, because it decides the swap by comparing against the Demon *it*
tracked, which is a different seat.

So the open question is a rules one, and it needs an answer rather than a
guess:

  * **Can a swapped Snake Charmer swap again?** The old Demon now holds
    the Snake Charmer character and is poisoned for the rest of the game
    — so its ability should not function at all, and pointing at the
    Demon should do nothing.

If that is right, the fix is that a **droisoned** charmer cannot swap,
and the perma-poisoning of the old Demon already covers it. The walk
knows about `standing` droisonings but is not being told this one,
because `hidden_from` reads `droisoned_at` only for the seats it already
knows about.

**Next step**: confirm the rule, then check whether the walk is told that
the old Demon is permanently poisoned.


---

## The switch is in, and inert

`WALK_CHECKS_STORIES`, off by default, at the seam in `best_story`:
`possible_timelines` proposes chains, and each is replayed before being
scored.

    for changes, weight in stories:
        view = Timeline(world, changes) if changes else world
        if WALK_CHECKS_STORIES and not _the_night_could_have_run(view, state):
            continue

The adapter turned out to be almost nothing. The walk asks a board four
things — `n`, `role_at`, `side_at`, `alive_at` — and a solver world
answers two already. **180 of 180 nights replay over the views the solver
actually scores.**

One mistake worth keeping: handing over the bare `World` gave 174 of 180.
A `World` carries no changes; a swap lives in the `Timeline` wrapped
around it. The thing to hand over is the **view**, not the world
underneath.

### What is honestly still missing

`_what_the_walk_is_told` returns `None`, so the check is silent even when
switched on — it can be turned on today and changes nothing, which is
what makes it safe to land.

The gap is real and it is the last piece of the design: **the impairment
plan proposes where the Poisoner went and who the Demon took, and the
walk checks it.** Those two have never been connected. In the tests the
hidden choices come from what the simulator chose; in the solver they
have to come from the plan.

That is the remaining work, and it is the part where the search cost
could actually bite — every candidate assignment now needs a replay
rather than a set comparison.

**Next step**: hand the plan's chosen assignment to `_what_the_walk_is_told`
for one night on one board, and see both that it works and what it costs.


---

## The plan and the walk are connected

Done on one night of one board, which is what the plan asked for.

    impairment.plan_night(sources, required, forbidden, previous)
      -> (0.35, {"Poisoner": 5})

    nightwalk.walk(AsBoard(view, state), 2,
                   {("poisoner", 2): 5, ("demon", 2): [...]})
      -> died {3}          which is what the record says

The plan chose seat 6, the simulator had poisoned seat 6, and the walk
reproduced the night exactly. **The two halves fit.**

### Two things that cost time and were both mine

`plan_night` returns hits keyed by the source's **name**, not the source
object — `{"Poisoner": 5}`. Worth knowing before writing against it.

And a probe reported `SOURCE_RULES` holding only one rule, which looked
like a serious gap. It was not: the Poisoner rule is registered from
`solver.py`, and the probe had imported `impairment` alone. **Importing
the module that registers the rules is part of the setup**, and a probe
that skips it sees a solver with almost no rules in it.

That is the fourth time this session a probe rather than the code was
wrong. The pattern is consistent enough to state: when something core
looks broken, check the harness before believing it.

### What is left

`_what_the_walk_is_told` still returns `None`, so the switch is inert.
Filling it means, for each night: ask `sources_on`, run `plan_night`,
translate the hits into the walk's hidden inputs. The translation is the
new code — the names differ, and the walk wants more than the plan
supplies (a Demon's aim, a Gambler's guess), which have to come from the
readings.

**And the cost is still unmeasured.** Every candidate story would now
need a replay per night instead of a set comparison. That number decides
whether this approach survives, and nothing has measured it yet.


---

## Decided: the walk checks, it does not propose

Two findings settle the design, and they point the same way.

### The cost is not the problem

    one walk     15 us
    one _explain 156 us
    ratio        0.1x

**A replay is ten times cheaper than the scoring it would guard.** The
fear was that replaying every candidate would swamp the search; the
opposite is true. A walk that discards a story before `_explain` runs
*saves* time.

### But the plan cannot tell the walk where the Poisoner went

`plan_night(sources, required, forbidden, previous)` answers "can these
sources impair exactly who is **required**". With nothing required, the
cheapest arrangement is to place nobody — so it returns an empty
assignment, and the walk has nothing to replay.

That is not a coding slip. The two halves want different things:

  * the **walk** wants a concrete assignment to replay;
  * the **plan** wants the cheapest assignment satisfying constraints,
    and with no constraints the cheapest is the empty one.

### So the walk is a filter, not an oracle

The design said "propose then walk", and the proposing half does not
exist — the plan is a *cost model*, not a generator. Making it enumerate
assignments would be a new search, and that is where the cost would
actually land.

What the walk can do today, cheaply and safely:

  * **check a story it is fully told about.** Where the readings force an
    assignment — which is exactly when the plan has something to say —
    the walk can replay it and discard the story if the night could not
    have run. Free, given the ratio above.
  * **stay silent otherwise**, which is what `untold` already ensures.

That is worth having and is much less than the design imagined. The
Acrobat still cannot be made informative this way, because its inference
needs the plan and the death causes settled together — and the plan
still is not a generator.

**Next**: leave `WALK_CHECKS_STORIES` off, keep the join, and take the
narrow win — replay only where the readings pin the assignment. The
larger prize needs the plan to enumerate, which is a separate piece of
work with its own cost question.


---

## Correction: the four discarded worlds were a bug of mine

Reported as evidence that the check invents requirements. It was not.

`_what_the_walk_is_told` returns `{}` when nothing is forced and `None`
when the plan cannot satisfy what is. The guard read `if told is None`,
so an **empty** assignment fell through and the walk ran with no inputs
at all — killed nobody, disagreed with every record, and discarded four
true worlds.

    if told is None:   ->   if not told:

With that, the switch is genuinely inert: 0 impossible of 45 either way.

**The earlier reasoning about `holds` needing context still stands** — a
Fortune Teller's does need the red herring — but it was not what caused
those four. I should not have concluded from a broken harness, which is
the fifth time this session.

### Where the design actually stands

  * **Cost is not a problem.** A walk is 15 us against `_explain`'s
    156 us. A check that discards a story early *saves* time.
  * **The seam works.** `AsBoard` is a dozen lines, and the walk replays
    180 of 180 nights over the views the solver scores.
  * **The plan is a cost model, not a generator.** It answers "can these
    sources impair exactly who is required", so with nothing required it
    places nobody. That is the real gap, and it is unchanged by the
    correction above.

So the switch stays off, and what would turn it on is a way to *propose*
assignments — enumerating where each source could have gone, rather than
pricing an arrangement somebody else chose. That is a new search, and the
cost measurement above says it is affordable to check each candidate once
it exists.


---

## Phase B: the enumeration question is answered

The missing piece was a **generator**. `plan_night` prices an arrangement
somebody else chose; the walk needs a concrete assignment to replay.
`impairment.arrangements(sources)` now proposes them — free sources
folded in as fixed, paid ones enumerated over their reach.

The worry was that enumeration would multiply against the world search.
It does not:

    published scripts   median 1, mean 1.8, max 16   (180 nights)
    mixed scripts       median 1, mean 4.1, max 12   (100 nights)

**Most nights have exactly one arrangement.** A board with a single
Poisoner and nothing else has nine or twelve seats it could have gone to
— but on most nights the only sources are free ones, which are not
choices at all.

And the walk earns its place:

    arrangements tried 77, survived the walk 52  ->  32% pruned

A walk is 15 microseconds against `_explain`'s 156, so a third of
candidates discarded before scoring is a saving, not a cost.

### What is left to switch it on

  * **`_what_the_walk_is_told` should take an arrangement**, rather than
    asking `plan_night` for one it cannot give.
  * **`best_story` has to try each arrangement**, keeping a story if any
    arrangement survives — a story is impossible only when *every* way of
    placing the sources fails.
  * **The Innkeeper wants a pair, not a seat.** The enumerator hands a
    single seat per source and the walk's Innkeeper branch iterates. One
    of these has to change; the source knows its capacity, so the
    enumerator is the right place.

None of that is deep. The measurement said this approach was affordable
and it is; the remaining work is plumbing with a known shape.


---

## Phase B: wired, and it exposes a circularity

The enumerator is in and `best_story` tries every arrangement, keeping a
story if **any** of them survives. The Innkeeper's capacity is handled —
a source that takes two seats hands over a tuple.

Turning the switch on still gives the same answers, and the reason is not
good: **`_the_night_could_have_run` returns False on true worlds**, and
repair rescues the boards afterwards. The counts matched by luck.

### Why every arrangement fails

The walk needs to know **what the Demon aimed at** to reproduce a kill.
The impairment plan has no such source — a Demon does not droison, so it
is not in `sources_on` and never will be. Every arrangement therefore
says "nobody died tonight", disagrees with the record, and the story is
discarded.

And the aim cannot simply be enumerated alongside the droisoning, because
**the aim is what the deaths are evidence for**. Whoever died at night is
who the Demon aimed at, *modulo protection* — and protection is exactly
what the walk exists to decide. Feeding the deaths in as the aim would
make the check tautological: it would confirm whatever it was told.

### So the honest position

The walk can settle **who was droisoned**, given an arrangement. It
cannot settle **who the Demon aimed at** without being told, and being
told makes the answer worthless.

What would break the circle is enumerating the aim as well — every living
seat the Demon could have chosen, crossed with every droison arrangement
— and letting the walk find which pairs reproduce the record. That is a
genuine search rather than a check, and the arrangement counts say the
droison half is cheap; the aim half multiplies it by the table size.

**Next step**: measure that. Nine seats times a median of one droison
arrangement is nine walks a night at 15 microseconds — likely still
cheaper than one `_explain`. If so, the walk becomes the thing that
*finds* the night rather than the thing that checks it.


---

## Measured: the walk can find a night, not just check one

Enumerating the Demon's aim alongside the droisoning breaks the
circularity, and it is affordable.

    nights 120, explained 119
    walks per night: median 4, mean 13.6, max 648
    0.09 seconds for the lot

**Median four walks a night.** The mean is dragged up by the demons that
need more: a Shabaloth or a Po takes two seats, so the aim is every pair
rather than every seat, and a Pukka's kill is *last night's* poison, so
its delayed victim has to be enumerated too. Those are the 648.

At roughly 78 microseconds a walk, a whole night costs less than one
`_explain` at 156. **The walk is cheaper than the thing it would
replace**, which is the answer the design needed.

### The one night it cannot explain

One of a hundred and twenty. Worth finding before building on this — a
single unexplained night is either a rule the walk still lacks or a
board the record genuinely does not determine, and those want opposite
responses.

### What this changes about the design

The walk stops being a *check on* the impairment plan and becomes the
thing that **finds** the night: enumerate what could have happened,
replay each, keep what reproduces the record. The plan then prices what
the walk found, rather than proposing something the walk verifies.

That is simpler than "propose then walk" and it removes the circularity
outright — the aim is no longer an input the check needs handed to it,
it is one of the things being searched for.

**Next step**: the unexplained night, then wire this shape into
`_the_night_could_have_run` and turn the switch on for real.


---

## Phase B: the search is wired, one board short

`_a_night_fits` searches the night rather than checking it: every
arrangement of the droison sources, crossed with everything the Demon
could have aimed at.

    nights 120, explained 120
    walks per night: median 5, mean 10.3, max 209

**Every night explained**, once two things were added. A **Gambler's
guess** is on the record rather than something to search — leaving it out
cost the first missing night. And a **Po takes three**, so aims of size
one and two were not enough.

With the switch on, 45 boards give **1 impossible** against 0 with it
off. And the interesting part: `_the_night_could_have_run` returns
**True** on that board's true world. So the truth is not what is being
rejected — some *other* story is, and the board ends with nothing left.

That is a different failure from the one expected. It means the check is
discarding a story the solver needed for another reason, most likely one
where a transition makes a night the walk then cannot fit.

**Next step**: on that board, list the stories `possible_timelines`
offers and see which ones the check refuses. If the truth survives and
the board still fails, the loss is somewhere between the two.


---

## Phase D: the Acrobat works, 33 of 35

**Four lines in the walk**, and all three cases come out right:

    pick is poisoned   ->  Acrobat dies
    pick is clean      ->  Acrobat lives
    Acrobat poisoned   ->  Acrobat lives

That is the character the night order was built for. It could not be
modelled in the three-pass design at all — the inference needs the
impairment plan and the death causes settled together — and here it is
four lines, because the night has happened.

### Two simulator bugs on the way

**The night's own consequences sat under `if night < nights`**, a guard
meant for the *day* that follows. So on the last night an Acrobat never
fell, a Moonchild never took anybody, a Tinker never went.

**And the Acrobat's row was produced after the rule that read it.** It
acts at slot 39 — after the Demon at 24, before the readings at 53 — so
its pick belongs with the night's consequences, not with `honest_info`
which runs later. Scanning `heard` for a row that did not exist yet
killed nobody. Moved, and 30 of 38 became 33 of 35.

### The two that remain

Opposite failures, which is useful:

  * **seed 34**: the walk kills an Acrobat the simulator spares. The walk
    has seat 9 droisoned where the simulator has seat 5 — so
    `hidden_from` is not passing a standing droisoning, and
    `("standing", 3)` comes back `None`.
  * **seed 7**: the reverse, the simulator kills and the walk does not.

The first is a missing hidden input rather than a rule disagreement,
which is the fourth time that shape has appeared. `hidden_from` builds
`standing` only from Snake Charmer swaps; a Sweetheart's droison and a
Courtier's three-day run are not in it.

**Next step**: build `standing` from `droisoned_at` minus what the walk
derives itself, rather than from one hand-listed source.


---

## Phase D: the Acrobat is exact, and the fix moved something else

`standing` is built by **subtraction** now — everything `droisoned_at`
says, minus the Poisoner hit the walk works out itself. Listing sources
by hand had passed a swapped Snake Charmer and missed a Sweetheart's
droison and a Courtier's run.

    acrobat nights: 35 | matched 35 | differed 0

**The Acrobat is exact.** The character the night order was built for,
which the three-pass design could not express at all, is four lines in
the walk and agrees with the simulator everywhere.

### But two things moved

    TB    solver 0 impossible | walk 40/40
    BMR   solver 1 impossible | walk 40/40
    S&V   solver 0 impossible | walk 38/40

Both are new since the Acrobat was moved out of `honest_info` into the
night's consequences, which changed the order rows are produced in — and
therefore which seeds produce which games.

The S&V case is traced one step: seat 5 dies in the record and not in the
walk, with `standing` and `droisoned_at` agreeing on seat 2. So the
missing death is the Demon's, and something is stopping it — a guard the
walk applies and the simulator does not, or an aim that is no longer
passed.

**Next step**: the walk's log on that night, which has answered this
class of question every time it has been looked at and has been ignored
three times running.


---

## Phase D: the Acrobat is done

    acrobat nights: 35 | matched 35 | differed 0
    TB    solver 0 impossible | walk 40/40
    BMR   solver 1 impossible | walk 40/40
    S&V   solver 0 impossible | walk 40/40

**The walk is exact on all three scripts**, and the Acrobat — the
character the night order was built for, which the three-pass design
could not express at all — is four lines and agrees everywhere.

### The fifth missing droison source

`perma_poisoned` was written when a Snake Charmer swap happened, read in
exactly one place, and **never consulted by `droisoned_at`**. So a
swapped charmer counted as working for every other question. After the
Minstrel, the Philosopher, the Innkeeper and the Sailor, that is five.

And the fix needed fixing: handing over the set whole marked a seat
droisoned on the very night it was swapped, so the Demon could not act on
the night it stopped being one. The date comes from `changes` now. **A
set that means "by the end" is not an answer to "on this night"** — the
same mistake, in a second place, having been fixed once already.

### One board left

Bad Moon Rising seed 16. The trace names a Sailor row, but that is a
red herring: `SailorChoice.holds` is `return True` and the source it
creates is correct. The real shape is **three deaths on night three**
with a Shabaloth, which takes two — so a third cause is needed and the
deaths alone already cost 0.18.

**Next step**: `explain_night` on that night, which will name what the
third cause could be.


---

## Phase E: the Balloonist, mostly built

**Each night, you learn a player of a different character type than last
night. [+0 or +1 Outsider]**

Built: catalogue entry with the Godfather's two-option setup (the
Storyteller *may* add an Outsider and it is not knowable), a row carrying
a seat and no type, the chain check, the Vortox case where consecutive
types must be the **same**, the simulator, and the ledger.

    two townsfolk running   impossible
    townsfolk then demon    1.0
    recluse three nights    1.0

That last is the wiki's own example: a Recluse registers three ways, so
one seat can satisfy every link.

### The data file was wrong, which is the more useful finding

`data/roles.json` carries the **old** Balloonist — "learn 1 player of
each character type, until there are no more types to learn". A different
mechanic. Building from it would have produced the wrong character.

`data/README.md` now says plainly: authoritative for night order, **not**
for what a character does. The wiki is the source for that.

### The gate: 5 of 40, two of them the Balloonist

Two are pre-existing failures with no Balloonist rows on the board at
all; one is a Washerwoman.

Of the two real ones, **one is fixed**: the simulator compared the
previous seat's type *as it now stands* rather than as it was when shown.
A seat shown on night one can swap into a Demon by night two. Taken on my
own reading — the card says "a different character type than last night",
and last night's type is what it was last night — and reversible if the
table disagrees.

**The other is open.** Seed 22 has a valid chain by the simulator's
reckoning (townsfolk, minion, townsfolk, demon) and the solver reads seat
8 as townsfolk on night four when it holds the Zombuul by then. Passing
the `Timeline` view rather than the bare world did not change it, so the
swap is not in the story `possible_timelines` offers for that board.

**Next step**: print the chains offered on seed 22 and see whether the
swap appears in any of them.


---

## The Alsaahir: built, one bug found

**Once per day, if you publicly guess which players are Minion(s) and
which are Demon(s), good wins.** A day ability, like the Slayer, and not
in `data/roles.json` at all — the wiki was the only source.

Solver, ledger and app are wired, and four cases check out:

    exact guess, did not win   impossible
    swapped Demon/Minion       fine — a failed guess says nothing
    exact guess, won           holds
    missed a minion, won       impossible

And the Fang Gu case from the table works: a dead seat still *holds* its
character, so a jumped Fang Gu leaves two Demons to name and giving only
the living one fails. That let the rule be simply "every seat whose
current character is a Minion or Demon, alive or dead", which covers good
Minions too since it is `TEAM` rather than side.

### The gate: 6 of 40, one of them the Alsaahir

Three fail on deaths alone and two on a Pit-Hag — pre-existing on those
mixed scripts. The real one is **seed 34**, and the cause is a shape
problem rather than a rules one.

`Info.night` is a night number everywhere else. An Alsaahir guess happens
in **daylight**, and putting the day number in that field makes the rest
of the pipeline read it as a night reading: `_plain_failures` demanded a
seat be droisoned on night two to explain a guess made on day two.

`holds` is right and returns True; everything downstream is wrong,
because the field means something different for this row.

The Slayer has the same shape and gets away with it — `SlayerShot` also
carries a day in `night` — so this is a latent problem the Alsaahir
happened to expose rather than one it introduced.

**Next step**: decide whether day-actions get their own field or whether
`weighed` should be False for them, as it is for the Slayer. Checking
what `SlayerShot.weighed` returns is the first thing to look at.


---

## The Farmer heir: a confirmed diagnosis that was not the cause

A board with a Farmer that died at night and a second seat claiming
Farmer puts that second seat at **95.5 per cent evil**. It should not:
the handover is the ability working, and the heir is making an honest
statement.

`is_lying` compares a claim against `world.roles[p]` — the character the
seat was **dealt**. An heir therefore reads as a liar. That is real, and
was confirmed directly.

**It is not what drives the number.** Three separate fixes were tried —
widening the candidates for any possible heir, dropping the claim for a
seat that files a handover row, and replacing the claim with good roles
plus the lie. Then measured across 48 boards, six player counts, both
nights:

    heir looks better with the row:   0
    heir looks worse:                 1
    no real change:                  47

The heir sits above ninety per cent evil regardless. Something else
dominates and the claim machinery is at most a small part of it.

All of it is reverted. What survives is the design, which is still right:

### The ledger row, as agreed at the table

`BecameInfo(night, player, role, was)` — *"seat 3 became the Farmer
during night 2, having claimed Chef"*.

  * **Editing a claim is a correction**, silent, no ledger. **"became
    this"** is an event and files a row. Two entry points rather than a
    popup: the click already says which one was meant.
  * `is_a_choice = True` — the game hands over the token, the Storyteller
    is not telling anybody anything, so a Vortox does not touch it.
  * `was` is for the ledger to read, not the solver, and goes stale if
    the claim is edited afterwards. A stale value beats silently
    rewriting somebody's notes.

### Next step, and only this

**Count before changing anything.** Enumerate the surviving worlds on
that board, split them by what seat three holds, and find out why the
ratio is what it is. A plausible part of it: if seat six is the real
Farmer, the Storyteller hands the character to one of five or six living
good players, so most worlds have somebody *else* as the heir — while
seat three could be any of four evil characters. That may be much of the
ninety-five per cent and may be correct.

Do not touch the claim machinery again until that number is understood.


---

## Five gate boards left, and two dead ends recorded

Five failures across the character sweeps, and they are **two shared
boards** rather than five problems:

    Noble       seeds 9, 29
    Alsaahir    seeds 9, 29     — the same two boards
    Balloonist  seed 27

### Seed 9: a Pit-Hag and a Snake Charmer on the same night

A charmer swaps at slot 11, then a Pit-Hag changes the same seat at slot
16. Both legal in that order, and the simulator records both — so the
solver receives two changes stamped `N3` for one seat, and
`demon_handovers` then finds no Demon at all.

**The representation already handles this.** `role_at` walks the change
list and takes the last match, so the tuple order *is* the resolution:
charmer-then-Pit-Hag gives Innkeeper, reversed gives Snake Charmer.
Verified directly.

So the theory was that chains come out in *rule* order rather than slot
order — the rules run Barber, Pit-Hag, Farmer, Snake Charmer, handovers,
and each appends its own. Sorting the chain by phase and slot is twenty
lines and it works.

**It changes nothing.** Measured before and after across all three
published scripts and all five character gates: five impossible boards
both times, not one moved either way. A true observation about a real
mechanism that is not what drives the number — the same shape as the
Farmer heir earlier. Reverted rather than kept.

### What has not been tried

Printing what `demon_lineages` is actually walking on seed 9 — who it
thinks holds the Demon at each phase and where the walk stops. Every
attempt so far has theorised about the chain and then tested a fix;
none has watched the lineage search fail.

**That is the next thing, and it should come before any further change.**


---

## The night-walk switch: measured, and closed

`WALK_CHECKS_STORIES` stays off. Not blocked, not unfinished — answered.

    259 stories checked across 45 published boards
      9 refused
      0 true worlds lost

    on the board where it refuses most (S&V seed 1):
      switch off   672 worlds,  5.7s
      switch on    672 worlds, 60.9s
      every seat's evil percentage identical

Three and a half thousand refusals on that board and not one number
moved. Every story the walk rejects would have scored zero anyway.

The enumeration question that blocked this for two sessions turned out
to be already solved — `impairment.arrangements` was built in phase B and
works. The switch runs, enumerates, and refuses correctly. It simply buys
nothing.

**The walk keeps its real job**: an independent second implementation of
the night, replaying 180 of 180 and catching bugs by disagreeing with the
simulator. Do not delete it. Do not turn the switch on.

### What is worth doing instead

  * **A real game.** Everything here is measured against a simulator
    written alongside the solver, which is circular — several bugs
    existed because both sides shared a wrong assumption. A board from an
    actual game is the one test that cannot be faked, and it needs
    nothing built.
  * **More characters.** 43 unmodelled. Each of the last two shook out
    three or four pre-existing faults, which is the real argument for
    them.
