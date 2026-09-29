"""How a table claims, which is most of what the solver ever reads.

The simulator has always dealt honest boards: every good player claiming
what they are, every evil player taking a clean bluff nobody else wanted.
That is a table that does not exist, and a solver tested only against it
is being asked the easy question.

What a real table does, and what this produces:

  * **Good players mostly tell the truth**, either a full claim or a
    softclaim — "I wake every night", "I never wake" — which the board
    already records as a wake pattern.
  * **About one in ten lies anyway.** Nearly all of those are Outsiders
    hiding behind a Townsfolk claim, which is ordinary self-preservation.
    A few are chaos: somebody claiming whatever, for no reason worth
    modelling.
  * **Evil is handed three bluffs** that are not in play and takes one,
    at random rather than cleverly.
  * **And on a bigger table the bluffs collide.** With four evil players
    and three bluffs between them, somebody ends up double-claiming a
    character a good player really has.

The chaos claim is the part worth defending. Every other lie here is one
the solver already expects and prices — an Outsider hiding costs 0.35, a
Townsfolk lying costs 0.02. If those were the only lies generated, the
simulation would keep agreeing with the solver's own assumptions and
prove nothing. A claim with no logic behind it is the noise a real table
has, and it is the only thing here that can surprise the priors.

Random rather than clever, deliberately. The moment this reasons about
which bluff is *plausible*, it is doing a weak version of the solver's
own job — and the two would agree because they share an assumption,
rather than because the solver is right.
"""

from botc.roles import (OUTSIDERS, TEAM, TOWNSFOLK, is_evil,
                        knows_what_it_is, must_hide)

# How often a good player says something untrue. Most tables have one.
GOOD_LIE_CHANCE = 0.10
# Of those lies, how many are an Outsider hiding rather than pure chaos.
HIDING_SHARE = 0.8
# How often somebody softclaims a wake pattern instead of a character.
SOFTCLAIM_CHANCE = 0.15


def _pool(deal, script=None):
    """The good characters somebody on this board could claim to be.

    Off the script rather than off the global lists, which is not a
    detail: a chaos claim drawn from every character in the catalogue
    produced a Fortune Teller on Bad Moon Rising, and the solver
    correctly refused a board where somebody claims a character that is
    not in the bag.
    """
    script = script or getattr(deal, "script", None)
    if script is None:
        from botc import scripts as script_mod
        script = script_mod.TROUBLE_BREWING
    return list(script.townsfolk), list(script.outsiders)


def bluffs_for(deal, rng, count=3, script=None):
    """The three characters the Storyteller hands evil to lie with.

    Not in play, which includes anything a Drunk believes it is: the
    Storyteller has that token on the board and does not offer it twice.
    """
    townsfolk, outsiders = _pool(deal, script)
    in_play = set(deal.roles) | {b for b in deal.believes if b}
    # And never the Drunk. It is not a token anybody ever sees — the
    # Storyteller hands the seat a *Townsfolk* token and says nothing —
    # so there is no such thing as a Drunk to bluff as, and a table where
    # somebody claims it is a table that has never happened.
    #
    # The same goes for any character whose whole point is that its
    # holder does not know: a Marionette believes it is a Townsfolk too.
    never_seen = {"Drunk", "Marionette", "Lunatic"}
    spare = [t for t in townsfolk + outsiders
             if t not in in_play and t not in never_seen]
    rng.shuffle(spare)
    return spare[:count]


def _hiding_claim(deal, seat, rng, script=None):
    """An Outsider claiming to be a Townsfolk nobody has taken."""
    townsfolk, _outsiders = _pool(deal, script)
    taken = set(deal.roles) | {b for b in deal.believes if b}
    spare = [t for t in townsfolk if t not in taken and t != "Drunk"]
    return rng.choice(spare) if spare else None


def claims_for(deal, rng, script=None):
    """What each seat says it is, and what it says about waking.

    Returns (claims, wakes, notes) — the last a per-seat account of *why*
    each claim is what it is, which is what makes a played-out game worth
    reading afterwards.
    """
    townsfolk, outsiders = _pool(deal, script)
    # Nobody claims the Drunk, even at random: it is not a token anybody
    # has ever been handed.
    pool = [k for k in townsfolk + outsiders
            if k not in ("Drunk", "Marionette", "Lunatic")]

    bluffs = bluffs_for(deal, rng, script=script)
    # Handed out one at a time, so the team does not double up on itself.
    # More evil players than bluffs means somebody has to improvise, and
    # then a clash with a *good* claim is exactly what happens.
    spare = list(bluffs)
    rng.shuffle(spare)
    claims, wakes, notes = {}, {}, {}

    for seat in range(deal.n):
        role = deal.roles[seat]
        honest = deal.apparent(seat)        # what a Drunk thinks it is

        # Turned good by a swap: a Demon a Snake Charmer swapped with is
        # a Snake Charmer now, knows it, and says so. Its opening bluff
        # stood instead, so the rows it went on to write as the Snake
        # Charmer were charged to whoever else claimed one (29.09.2026).
        became = [(when, who, what) for when, who, what in deal.changes
                  if who == seat]
        if became:
            when, _who, now = became[-1]
            if deal.side_at(seat, when) == "good" and now != role \
                    and not is_evil(now):
                claims[seat] = now
                notes[seat] = f"was the {role}, now the {now}, claiming it"
                continue

        # A Marionette is evil and does not know it, so it claims the
        # token it was handed like any good player — only the knowing
        # evil bluff.
        if is_evil(role) and knows_what_it_is(role):
            # The team knows each other and divides the three between
            # them, so two Minions do not walk in claiming the same
            # thing. Taking one each is the whole reason there are three.
            #
            # Left to chance, they collided with *each other* two-thirds
            # of the time — which is not a table anybody has played at,
            # and it made the solver's job far easier than it should be.
            if spare:
                claims[seat] = spare.pop()
                notes[seat] = f"evil, bluffing as the {claims[seat]}"
            else:
                # More evil than bluffs, so somebody has to improvise —
                # and the thing they actually do is claim a character a
                # good player really has, forcing a double-claim the town
                # must resolve. Re-using a *bluff* would mean two evil
                # claiming the same not-in-play character, which is the
                # one thing a team that knows each other never does.
                honest = [deal.apparent(p) for p in range(deal.n)
                          if not is_evil(deal.roles[p])]
                claims[seat] = (rng.choice(honest) if honest
                                else rng.choice(bluffs or ["Mayor"]))
                notes[seat] = (f"evil, out of bluffs — double-claiming "
                               f"the {claims[seat]}")
            continue

        # A Mutant never says it is an Outsider: it might be executed
        # for it. It always stands behind a Townsfolk nobody has taken.
        if must_hide(role):
            hidden = _hiding_claim(deal, seat, rng, script)
            if hidden:
                claims[seat] = hidden
                notes[seat] = f"the {role}, hiding behind the {hidden}"
                continue

        if rng.random() < GOOD_LIE_CHANCE:
            if TEAM[role] == "outsider" and rng.random() < HIDING_SHARE:
                hidden = _hiding_claim(deal, seat, rng, script)
                if hidden:
                    claims[seat] = hidden
                    notes[seat] = (f"good {role}, hiding behind the "
                                   f"{hidden}")
                    continue
            # Chaos: whatever came to mind. No logic to model, which is
            # the point of having it.
            claims[seat] = rng.choice(pool)
            notes[seat] = (f"good {role}, claiming the {claims[seat]} for "
                           f"no reason")
            continue

        if rng.random() < SOFTCLAIM_CHANCE:
            # A softclaim: no character, only when they wake. The board
            # records this as a wake pattern and the solver fits every
            # character that matches.
            from botc.catalogue import CHARACTERS
            # From the `wake` set, not from `nights`.
            #
            # `nights` describes the *shape* of an ability — "conditional"
            # for a Sage, "other" for a Demon — and is not something a
            # player can say at the table. The patterns anybody can claim
            # are the five in WAKE_PATTERNS, and a seat softclaiming
            # "conditional" fits no character at all: the search then
            # produced no world with that seat as itself, and the true
            # world was never enumerated.
            #
            # Third time this exact confusion has bitten. The Chambermaid
            # read `nights` and thought Demons slept through night one;
            # the solver's own waking check did the same.
            choices = sorted(CHARACTERS[honest].wake)
            pattern = rng.choice(choices) if choices else None
            if pattern:
                wakes[seat] = pattern
                notes[seat] = f"good {role}, softclaiming \u201c{pattern}\u201d"
                continue

        claims[seat] = honest
        notes[seat] = (f"good {role}, claiming honestly"
                       if honest == role
                       else f"the Drunk, honestly claiming the {honest}")

    return claims, wakes, notes


def confirm_readings(deal, heard, rng, chance=0.6):
    """Tick the readings a table could honestly have established.

    Two conditions, and the second is the one that matters.

    The reading has to be **true** — a table does not confirm something
    that turned out wrong. And the table has to have been *able* to check
    it: the seats it named have to be settled by something else, which
    for an Undertaker means the character it read was later confirmed by
    other means.

    The cheap version of this — mark any true reading — was tempting and
    wrong. It would hand the solver information a real table never had,
    because the simulator can see the grimoire and the table cannot.
    Calibration measured against that would flatter the solver, and the
    whole point of calibration is to stop flattering it.

    Even then, not always: tables do not verify everything, so `chance`
    is how often somebody bothers.
    """
    settled = _settled_seats(deal)
    for row in heard:
        if not _was_true(deal, row):
            continue
        if not _table_could_check(deal, row, settled):
            continue
        if rng.random() < chance:
            row.confirmed = True
    return heard


def _settled_seats(deal):
    """Seats whose character the table could have established.

    Deliberately narrow: a seat that died and was seen, which is the
    commonest way a table learns anything for certain. Widening this is
    the same trap as marking every true reading — it invents knowledge
    the table did not have.
    """
    return {seat for seat in range(deal.n) if deal.deaths.get(seat)}


def _was_true(deal, row):
    """Did this reading hold in the world that actually happened?"""
    from botc.info import GameState
    from botc.worlds import World
    kind = type(row).__name__
    if kind in ("SavantInfo", "ArtistInfo"):
        return False              # never checkable; the content is free text
    state = GameState(n_players=deal.n, script=getattr(deal, "script", None),
                      claims={}, deaths=dict(deal.deaths))
    try:
        return bool(row.holds(World(tuple(deal.roles), tuple(deal.believes)),
                              state, None))
    except Exception:
        return False


def _table_could_check(deal, row, settled):
    """Could the table have established this, without the grimoire?

    The seats a reading names have to be settled. A reading that names
    nobody — a Chef count, an Empath count — cannot be checked at all,
    which is exactly right: those are the readings a table argues about
    rather than confirms.
    """
    named = [getattr(row, f, None) for f in ("a", "b", "target")]
    named = [x for x in named if isinstance(x, int)]
    return bool(named) and all(x in settled for x in named)
