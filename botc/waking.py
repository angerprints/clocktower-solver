"""Who was actually woken on a given night, for their own ability.

This is not the same question as the wake table answers. That one is
forgiving on purpose: it records what a holder could *honestly claim*,
and a Courtier's honest answer depends on when they spent their ability.
The Chambermaid needs the fact, and the fact depends on the board — a
Ravenkeeper wakes only on the night it dies, an Undertaker only after an
execution killed somebody, a Courtier only until it has named a
character.

Two things make the answer uncertain rather than merely unknown, and both
are handled by returning the *set* of counts a reading could have taken
rather than a single number:

  * The Exorcist. A Demon it chose does not wake for its own ability that
    night — it is woken to be told who the Exorcist is, which is not the
    same thing. Nobody records who the Exorcist picked, so with one in
    play the Demon's waking is genuinely open.
  * Anybody impaired still wakes. Being drunk or poisoned does not let
    you sleep through the night; the Storyteller wakes you and makes an
    answer up. So impairment never changes this count.
"""

from .catalogue import CHARACTERS

NEVER = "never"
FIRST = "first"
EVERY = "every"
OTHER = "other"
CONDITIONAL = "conditional"

CONDITION_RULES = {}


def condition(key):
    """Register how to tell whether a character woke on a given night."""
    def take(fn):
        CONDITION_RULES[key] = fn
        return fn
    return take


@condition("Ravenkeeper")
def _ravenkeeper(world, state, seat, night):
    """Only on the night it dies, and it does wake then."""
    return f"N{night}" in state.died_at(seat)


@condition("Undertaker")
def _undertaker(world, state, seat, night):
    """Only when yesterday's execution actually killed somebody."""
    return night >= 2 and state.execution_death(night - 1) is not None


@condition("ScarletWoman")
def _scarlet_woman(world, state, seat, night):
    """Woken when she becomes the Demon, and not otherwise.

    The first night she is woken to be shown the Demon, which is not her
    own ability and does not count.
    """
    demon = world.demon_at(f"N{night}")
    return demon == seat and world.demon_at("N1") != seat


# Woken to be *told* something rather than to do anything.
#
# A Lunatic is shown a Demon's night and made to choose victims who never
# die — it wakes, and none of it is its own ability working. A Chambermaid
# does not count it, for the same reason it does not count a Baron being
# shown the other evil players.
#
# The distinction is that `woke` answers two questions at once: *did this
# seat wake*, which decides what a player could honestly claim about
# their nights, and *did its own ability fire*, which is what a
# Chambermaid asks. They are the same for almost every character and not
# for these.
SHOWN_NOT_ACTING = frozenset({"Lunatic", "Spy", "EvilTwin", "Marionette"})


def woke_for_own_ability(world, state, seat, night):
    """What a Chambermaid counts.

    Narrower than `woke`. A seat shown its team, or shown a night that
    never happened, was woken to be deceived rather than to act.
    """
    if not woke(world, state, seat, night):
        return False
    phase = f"N{night}"
    return world.role_at(seat, phase) not in SHOWN_NOT_ACTING


@condition("Lunatic")
def _lunatic(world, state, seat, night):
    """Every night, believing it is the Demon.

    It is *shown* a night rather than acting in one, and a Chambermaid
    counts it — being woken to be told you killed somebody is still being
    woken for your own ability, which is what a Lunatic's ability is.

    Missing entirely, and `nights == "conditional"` is checked before the
    night-one branch, so a character without a rule here silently never
    wakes at all. Found by a Chambermaid counting two where the solver
    could only reach one.
    """
    return True


@condition("Philosopher")
def _philosopher(world, state, seat, night):
    """The night it chooses, and thereafter on its gained schedule.

    A Philosopher that took a character is that character, ability wise —
    settled at the table — so one that took the Clockmaker wakes on the
    first night and never again.

    This said "always", and a Chambermaid beside it then counted a seat
    that had not woken: it reported nobody awake and the solver insisted
    somebody was. The docstring called the approximation "the direction
    that keeps worlds rather than ruling them out", which was wrong —
    saying a seat woke when it did not rules out every world where the
    Chambermaid was right.
    """
    from .info import phase_index      # local: info imports waking
    took = (state.philosophies() or {}).get(seat)
    if took:
        taken, since = took
        if phase_index(f"N{night}") < phase_index(since):
            return True               # the night it chose
        return woke_as(world, state, seat, night, taken)
    return True


@condition("Juggler")
def _juggler(world, state, seat, night):
    """Answered on the night after the day it guessed, and never again."""
    return night == 2


@condition("Seamstress")
def _seamstress(world, state, seat, night):
    """Once a game, and the simulator spends it on the first night."""
    return night == 1


@condition("Sage")
def _sage(world, state, seat, night):
    """Only if the Demon killed it tonight."""
    return f"N{night}" in state.died_at(seat)


@condition("Courtier")
def _courtier(world, state, seat, night):
    """Every night until it names a character, then never again."""
    for info in state.infos:
        if getattr(info, "source_role", None) == "Courtier" \
                and info.player == seat:
            return night <= info.night
    return True                           # never spent, so still being woken


@condition("Professor")
def _professor(world, state, seat, night):
    """Once a game, so only on the night it spends it.

    Returning True on every night had a Chambermaid counting a Professor
    that had raised nobody. There is nothing on the record to say which
    night it used — so this says *no* unless something else does, which
    keeps the count honest rather than inventing a wake.
    """
    return False


@condition("Zombuul")
def _zombuul(world, state, seat, night):
    """Only on nights it can actually kill — which is nights after a day
    when nobody died.

    Except the first, when it wakes like every other Demon to learn its
    Minions and its bluffs. That is what a Chambermaid beside it counts,
    and the killing schedule is a separate question from the waking one.
    """
    if night == 1:
        return True
    if night < 2:
        return False
    return not any(f"D{night - 1}" in state.died_at(who)
                   for who in (state.deaths or {}))


@condition("Assassin")
def _assassin(world, state, seat, night):
    """Every night until it uses its one kill, then never again."""
    for info in state.infos:
        if getattr(info, "source_role", None) == "Assassin" \
                and info.player == seat:
            return night <= info.night
    return True


@condition("Drunk")
@condition("Marionette")
def _believer(world, state, seat, night):
    """Woken on the schedule of whatever they think they are."""
    token = world.believes[seat]
    if not token:
        return False
    return woke_as(world, state, seat, night, token)


def woke_as(world, state, seat, night, role):
    """Did somebody holding this character wake for it on this night?

    A Demon is the awkward case. Its `nights` says "other", because that
    is when it *kills* — but it also wakes on the first night to learn
    its Minions and its bluffs, and a Chambermaid sitting beside one
    counts that. Reading the single word said every Demon slept through
    night one, which made a Chambermaid who correctly counted two into a
    board with no legal world at all.

    The `wake` set is the honest answer and has been on every character
    since the beginning: it holds "first" for every Demon and not for an
    Exorcist, which is exactly the distinction being asked about.
    """
    when = CHARACTERS[role].nights
    if when == CONDITIONAL:
        rule = CONDITION_RULES.get(role)
        return bool(rule and rule(world, state, seat, night))
    if when == NEVER:
        return False
    if night == 1:
        # Being shown the other evil players is not waking for your own
        # ability, so a Chambermaid does not count it. A Baron says
        # "first night" honestly — its `wake` set is what a *player*
        # could truthfully claim — and yet it has no night ability at
        # all, which `nights` records as "never".
        #
        # Reading the wake set alone made a Chambermaid beside a Baron
        # say one where the answer is none. A Demon is the opposite case
        # and does count: it wakes on the first night to learn its
        # Minions and bluffs, and that is its own ability working.
        if when == NEVER:
            return False
        # "every" means every night including the first, and its wake set
        # does not bother to say so — reading the set alone made every
        # Empath and Poisoner sleep through night one, which is a worse
        # bug than the one being fixed.
        return when == EVERY or FIRST in CHARACTERS[role].wake
    if when == FIRST:
        return False                      # night one only, and this is not
    return True                           # "other" and "every" both wake


def woke(world, state, seat, night):
    """Did this seat wake for its own ability on this night?

    The dead do not wake — except the Ravenkeeper, whose whole ability is
    waking as it goes.
    """
    phase = f"N{night}"
    role = world.role_at(seat, phase)
    if seat not in state.alive_set(phase) and role != "Ravenkeeper":
        return False
    return woke_as(world, state, seat, night, role)


def uncertain(world, state, seat, night):
    """Could this seat's waking have gone either way?

    Only one thing does this: an Exorcist sending the Demon to bed. It is
    a choice nobody writes down, so with one in play the Demon's waking
    is genuinely open rather than merely unrecorded.
    """
    if night < 2 or "Exorcist" not in state.script.keys:
        return False
    phase = f"N{night}"
    if world.demon_at(phase) != seat:
        return False
    exorcist = world.find_at("Exorcist", phase)
    return exorcist is not None and exorcist in state.alive_set(phase)


def possible_counts(world, state, seats, night):
    """Every value "how many of these woke" could have taken."""
    fixed = 0
    open_ended = 0
    for seat in seats:
        if uncertain(world, state, seat, night):
            open_ended += 1
        elif woke_for_own_ability(world, state, seat, night):
            fixed += 1
    return {fixed + extra for extra in range(open_ended + 1)}
