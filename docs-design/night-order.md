# The solver's night order — a design, not yet built

Written to be argued with. Nothing here is implemented.

## What is wrong now

A night is settled in three passes, and none can see the others.

    possible_timelines(world, state)     transitions: who became what
      └─ _explain(view, state)
           ├─ deaths: which cause killed whom
           └─ _impairment_plan: who was droisoned

They run in that order, once each, and each is finished before the next
begins. The Acrobat is what made the cost visible, because it needs all
three at once:

  * it dies **if** its pick was droisoned — needs the plan;
  * but only if its **own** ability was what killed it — needs the causes;
  * and whether it is even the Acrobat depends on transitions.

Both directions of the inference were tried and both had to be withdrawn:

  * a **surviving** Acrobat means the pick was clean *or* the Acrobat was
    itself droisoned. A disjunction, and the plan takes sets of seats.
  * a **dead** Acrobat looked solid, until the Demon killed one on a
    night its pick was clean. The death machinery had already chosen a
    different cause; the constraint ran regardless.

This is not an Acrobat problem. It is the shape of every character whose
text says *when*.

## What "night order" means here

The simulator plays a game, so ordering it was easy: sort by slot, act.
Done, and it immediately found three boards that had only ever held
together because characters acted in the wrong order.

The solver does not play. It asks *which worlds could have produced this
record*, and a night order there is a **constraint on the account**, not
a sequence to execute. The question changes from

> who was droisoned, and separately, who killed whom

to

> is there an ordering of tonight's actions, consistent with the slots,
> that produces exactly this record

## Three ways to do it, and what each costs

### 1. Leave the passes and add ordering facts

Keep the three passes. Give each rule access to the slot numbers, and let
individual rules ask questions like "was this seat still the Assassin
when slot 36 came round".

**Cheapest by far.** It fixes the Assassin starpass immediately, because
that only needs `role_at` at the right moment, which already exists.

**But it does not fix the Acrobat**, because the passes still cannot see
each other. It buys the easy half and leaves the hard half exactly where
it is.

### 2. One pass per night, in slot order

Replace the three with a single walk. For each night, step through the
slots; at each slot, the character acting may droison, kill, change
somebody, or produce a reading, and everything after it sees the result.

**This is what the rules describe**, and it makes the Acrobat natural
rather than awkward: by slot 39 the night knows who the Poisoner took at
slot 7, and the Acrobat's death is settled there and then.

**The cost is that the solver does not know what happened.** The
simulator can walk the night because it decides; the solver must consider
every way the night *could* have gone. A Poisoner with nine choices and a
Demon with nine is eighty-one branches before anything else, per night.
That is exactly the explosion the current design avoids by settling
droisoning once, globally, with a cost rather than a branch.

So this needs the walk to carry *constraints* rather than choices —
"whoever the Poisoner took, it was not seat 4, because the Acrobat lived"
— which is a different and harder kind of program than the present one.

### 3. Two passes: order-aware causes, then the plan

A middle path. Keep the impairment plan as the last word, but let the
death causes and transitions run **in slot order** and record what they
need from the plan as constraints rather than resolving them.

An Acrobat at slot 39 would emit: *if my own cause killed me, seat 4 was
droisoned; if not, nothing*. The plan then satisfies whichever causes the
death machinery actually chose.

**This fixes the Acrobat** without branching on every droison choice, and
it is a change to how the two passes talk rather than a rewrite of both.

## The Goon settles it, and changes the estimate

Raised at the table, and it is sharper than the Acrobat: **the first
player to choose the Goon tonight is drunk, and the Goon becomes their
alignment.**

*First* is doing all the work. A Sailor acts at its slot and a Poisoner
at 7; if both choose the Goon, whichever comes first decides whether the
Goon ends the night good or evil. No set of "who was droisoned" can hold
that — it needs the order, and it changes *alignment*, not merely whether
an ability worked.

So option 3 is not enough. Constraint-passing can say "seat 4 was
droisoned"; it cannot say "by the Sailor rather than the Poisoner, and
therefore the Goon is still good".

**Option 2 is required.** But it is cheaper than the first estimate,
because of something the first estimate missed.

### Most choices are already recorded

Eleven of them, and they are the good ones, because good players announce
what they did:

    Acrobat  Courtier  Exorcist  Gambler  Innkeeper  Klutz
    Moonchild  Philosopher  PitHag  Sailor  SnakeCharmer

The hidden choices are the evil ones — where the Poisoner went, who the
Demon killed — and **those are exactly what the impairment plan already
searches over**. It proposes an assignment and prices it.

So the branching is not "nine choices at every slot". It is the search
the plan already does, with the *evaluation* changed: instead of checking
set membership, walk the night in slot order and see whether the record
comes out.

### Which makes the shape: propose, then walk

    for each candidate assignment of the hidden choices:
        for each night:
            for each slot, in order:
                the character acts, seeing everything before it
        does the resulting record match what was written down?

The search space is what it is today. What changes is that a candidate is
verified by *replaying* the night rather than by set arithmetic — and
replaying is exactly what makes the Goon, the Acrobat and the Assassin
starpass fall out without special cases.

It is still the largest change this project has had. But it is a change
to how a candidate is *checked*, not an explosion in how many candidates
there are, and that is a very different prospect.

## What I would recommend

**Option 2, as propose-and-walk.** The recommendation changed once the
Goon was raised: almost every character depends on the order, and the
Goon depends on it for *alignment*, which no amount of constraint-passing
can express.

Option 1 remains worth doing first and separately. It fixes the Assassin
starpass with what already exists, it is small, and nothing in option 2
makes it wasted work.

The step after that is not to start writing. It is to **replay a night
that is already known** — take a simulated game, walk its night in slot
order, and check the walk reproduces what the simulator recorded. If the
walk cannot reproduce a night the simulator just played, it will not
reproduce one it has to infer, and that is worth finding out before any
of the three passes is touched.

## What it touches, measured

    transition rules        5
    death cause rules      13
    immunity rules          6
    implication rules       5
    impairment sources     13
    characters with a slot 55

    best_story             29 lines   orchestrates the three
    possible_timelines     23 lines
    _impairment_plan       29 lines

Option 1 touches individual rules and nothing structural. Option 3
touches `best_story`, the cause rules that care about timing, and the
plan's interface. Option 2 replaces all three passes and every rule that
registers with them.

## Not to be forgotten

**Prevention is failure.** A Tea Lady stopping an Acrobat death means an
ability was prevented, and a Mathematician counts that. Nothing models
it, and it is the same shape as a Soldier surviving the Demon. Whatever
design wins should have somewhere for it to live.
