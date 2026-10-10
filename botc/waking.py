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
    answer up. So impairment never changes this count — except for a
    Wraith, whose ability *is* waking (table ruling, 08.10.2026).
  * The Demon on the first night. It is woken to learn its Minions and
    its bluffs, which is not its ability — the same reason a Baron does
    not count. That is the table's ruling (02.10.2026), and only the
    Pukka, which already chooses on night one, counts for certain. But
    Storytellers elsewhere do count it, and this tool is used at their
    tables too: so it is *open*, both numbers stay legal, and the true
    world survives either way.
  * A Professor after somebody came back to life, when a Shabaloth is
    about. Whichever of them did it is not written down.
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


# Woken to be *shown* something rather than to do anything.
#
# A Spy is shown the grimoire and an Evil Twin its twin. They wake, and
# none of it is their own ability working — the same reason a Chambermaid
# does not count a Baron being shown the other evil players.
#
# Two characters were on this list and came off it by table ruling
# (02.10.2026), because both *act*, and only think they are somebody
# else while they do:
#
#   * The Lunatic chooses who it thinks it kills. The rule below said it
#     counts while this list said it does not, and the list won.
#   * The Marionette is handed a good character's token and lives that
#     character's nights, so the Chambermaid gets the number that token
#     gives — exactly as for the Drunk, which was never on the list.
#
# The distinction is that `woke` answers two questions at once: *did this
# seat wake*, which decides what a player could honestly claim about
# their nights, and *did its own ability fire*, which is what a
# Chambermaid asks. They are the same for almost every character and not
# for these.
SHOWN_NOT_ACTING = frozenset({"Spy", "EvilTwin"})


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
    """On the schedule of the Demon it thinks it is, and it counts.

    It is shown a night rather than acting in one, and a Chambermaid
    counts it all the same — being woken to choose who you think you
    kill is a Lunatic's ability doing what it does (table ruling,
    02.10.2026).

    So it wakes when that Demon would: one that thinks it is the Pukka
    chooses on the first night, one that thinks it is the Po does not —
    the first night it is only shown "its Minions", and whether that
    counts is open the same way it is for a real Demon. See `uncertain`.

    Missing entirely at first, and `nights == "conditional"` is checked
    before the night-one branch, so a character without a rule here
    silently never wakes at all. Found by a Chambermaid counting two
    where the solver could only reach one.
    """
    return woke_as(world, state, seat, night,
                   _acts_as(world, seat, f"N{night}"))


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
        # `<` until 07.10.2026, which made the comment a lie: on the
        # night it chose it was asked whether the *taken* character
        # wakes, and one that took the Saint had not woken at all.
        if phase_index(f"N{night}") <= phase_index(since):
            return True               # up to and on the night it chose
        # Nothing to wake for, if what it took is no ability of its own:
        # a Lunatic's nights are the Demon's it thinks it is, and a
        # Philosopher thinks nothing of the kind. Asked anyway, the
        # Lunatic's rule asked whose night this seat was living, heard
        # "a Philosopher's", and the two called each other until the
        # stack ran out (found on the 3,265th mixed game, 07.10.2026).
        if taken == "Philosopher" or CHARACTERS[taken].believes:
            return False
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
    """Every night until it names a character, then never again.

    In this life. A Courtier that died and came back is a new one with
    the ability afresh (table ruling, 03.10.2026), so what counts is
    whether it has named anything since it last returned.
    """
    born = max([int(str(at)[1:])
                for at in (state.resurrections or {}).get(seat, ())
                if int(str(at)[1:]) <= night] or [1])
    for info in state.infos:
        if getattr(info, "source_role", None) == "Courtier" \
                and info.player == seat and info.night >= born:
            return night <= info.night
    return True                           # never spent, so still being woken


def _raised_on(state):
    """The first night anybody came back to life, or None."""
    nights = [int(str(phase)[1:])
              for phases in (state.resurrections or {}).values()
              for phase in phases if str(phase)[:1].upper() == "N"]
    return min(nights) if nights else None


@condition("Professor")
def _professor(world, state, seat, night):
    """Every night but the first, until it has raised somebody.

    "Once per game, at night*": it is woken from the second night on and
    may decline, the same as an Assassin. This said *never*, because
    nothing records which night it used — which had a Chambermaid beside
    an unspent Professor counting one where the solver allowed none.

    What the board does record is somebody coming back to life. With no
    Shabaloth about, that was the Professor, and it sleeps from then on.
    With one, see `uncertain`.
    """
    if night == 1:
        return False
    raised = _raised_on(state)
    return raised is None or night <= raised


@condition("Godfather")
def _godfather(world, state, seat, night):
    """The first night, and after a day an Outsider died.

    On the first night it learns which Outsiders are in play, which is
    its ability. After that it is woken only to kill, and it only kills
    when an Outsider died *today* — in daylight, the same condition the
    kill itself has. The catalogue said "every", so a Chambermaid beside
    a Godfather on a night nothing had happened counted one too many.
    """
    if night == 1:
        return True
    day = f"D{night - 1}"
    return any(day in state.died_at(who)
               and world.team_at(who, day) == "outsider"
               for who in (state.deaths or {}))


@condition("Zombuul")
def _zombuul(world, state, seat, night):
    """Only on nights it can actually kill — which is nights after a day
    when nobody died.

    On the first it is only told its Minions and its bluffs, like every
    Demon but the Pukka. Whether that counts is open; see `uncertain`.
    """
    if night < 2:
        return False
    return not any(f"D{night - 1}" in state.died_at(who)
                   for who in (state.deaths or {}))


@condition("Assassin")
def _assassin(world, state, seat, night):
    """Every night until it uses its one kill, then never again.

    Every night but the **first**: the card says "at night*". On night
    one it is only shown its team, which is not its ability — the same
    as a Baron. This said yes on night one too, and nothing noticed
    because the simulator made the same mistake the other way round: it
    counted the Assassin on night one and never after (29.09.2026, found
    with the Mastermind's wider sweep).
    """
    if night == 1:
        return False
    for info in state.infos:
        if getattr(info, "source_role", None) == "Assassin" \
                and info.player == seat:
            return night <= info.night
    return True


def _chose_on(state, seat, role):
    """The night this seat said it used a once-a-game choice, or None.

    Its own row, not one somebody else filed about the same character:
    the player a Nightwatchman woke speaks a row with that source too,
    and it is theirs.
    """
    for info in state.infos:
        if getattr(info, "source_role", None) == role \
                and info.player == seat \
                and getattr(info, "is_a_choice", False):
            return info.night
    return None


@condition("Nightwatchman")
def _nightwatchman(world, state, seat, night):
    """Every night until it points at somebody, then never again.

    "Once per game, at night" with no asterisk, so from the first night:
    it is woken, and shakes its head or points. What records the night
    is its own row. Without one, see `uncertain`.
    """
    spent = _chose_on(state, seat, "Nightwatchman")
    return spent is None or night <= spent


@condition("King")
def _king(world, state, seat, night):
    """Only once the dead equal or outnumber the living.

    Counted at its own turn, after tonight's kills, and by who is really
    alive — a Zombuul under its shroud is. On the first night the Demon
    is shown who the King is, which is not the King waking.
    """
    from .info import the_dead_outnumber_or_equal
    if night < 2:
        return False
    if f"N{night}" in state.died_at(seat):
        return False                      # dead before its turn came
    return the_dead_outnumber_or_equal(world, state, night)


def _evil_eyes_open(world, state, seat, night):
    """Did another evil seat open its eyes tonight, for certain or maybe?

    (certain, maybe): `certain` if one surely woke for its own ability,
    `maybe` if one's waking is open — a Demon on the first night, an
    Exorcist's choice, an Assassin that may have struck. Woken to be
    shown something counts here, a Spy its grimoire: that is still
    somebody evil with their eyes open, which is all a Wraith asks.
    """
    phase = f"N{night}"
    certain = maybe = False
    poppy = world.find_at("PoppyGrower", phase)
    poppy_lives = poppy is not None and poppy in state.alive_set(phase)
    for other in state.alive_set(phase):
        if other == seat or not world.evil_at(other, phase) \
                or world.role_at(other, phase) == "Wraith":
            continue
        # The Spy does not see the Grimoire while a Poppy Grower lives
        # (their jinx, as the table reads it: 08.10.2026), so it opens no
        # eyes.
        if poppy_lives and world.role_at(other, phase) == "Spy":
            continue
        if uncertain(world, state, other, night):
            maybe = True
        elif woke(world, state, other, night):
            certain = True
    return certain, maybe


@condition("Wraith")
def _wraith(world, state, seat, night):
    """Whenever another evil player wakes, the Wraith is woken first.

    "You wake when other evil players do" — the Storyteller wakes it for
    every evil player who opens their eyes for their own ability, and
    that is the Wraith's ability doing what it does, so a Chambermaid
    counts it (table ruling, 08.10.2026). Being shown your team on the
    first night is not anybody's ability, the same line as for the
    Demon there.

    Drunk or poisoned it is **not** woken (table ruling, 08.10.2026) —
    the one character whose waking impairment changes, because waking
    is all its ability is. This says what a sober one does; who was
    impaired is the plan's to choose, so the Chambermaid's row asks for
    it (`info.ChambermaidInfo`) and `possible_counts(asleep=...)` gives
    the count with the Wraith stopped.
    """
    return _evil_eyes_open(world, state, seat, night)[0]


@condition("Vizier")
def _vizier(world, state, seat, night):
    """Only beside a Fearmonger: "the Vizier wakes with the Fearmonger and
    learns who they choose" (their jinx). Built for the Chambermaid, and
    the rest of the jinx is not (table ruling, 10.10.2026)."""
    other = world.find_at("Fearmonger", f"N{night}")
    return other is not None and woke(world, state, other, night)


@condition("Drunk")
@condition("Marionette")
def _believer(world, state, seat, night):
    """Woken on the schedule of whatever they think they are."""
    token = world.believes[seat]
    if not token:
        return False
    return woke_as(world, state, seat, night, token)


def _is_demon(role):
    return CHARACTERS[role].team == "demon"


def woke_as(world, state, seat, night, role):
    """Did somebody holding this character wake for it on this night?

    A Demon is the awkward case. Its `nights` says "other", because that
    is when it *kills* — and on the first night it is woken to learn its
    Minions and its bluffs. That is not its ability (table ruling,
    02.10.2026), so this says no; but it is not a settled no, and
    `uncertain` keeps both counts legal. Only a Demon whose `nights` is
    "every" — the Pukka — acts on the first night and counts outright.

    This has been wrong in both directions. Reading `nights` alone and
    calling the answer final made a Chambermaid who counted two beside a
    Demon and a Courtier into a board with no legal world at all; reading
    the `wake` set made every Demon count for certain, which rules out a
    Chambermaid at a table where it does not.
    """
    when = CHARACTERS[role].nights
    if when == CONDITIONAL:
        rule = CONDITION_RULES.get(role)
        return bool(rule and rule(world, state, seat, night))
    if when == NEVER:
        return False
    if night == 1:
        # "every" means every night including the first, and its wake set
        # does not bother to say so — reading the set alone made every
        # Empath and Poisoner sleep through night one.
        if when == EVERY:
            return True
        # Being told who your Minions are is not your ability. A Baron
        # says "first night" honestly — its `wake` set is what a *player*
        # could truthfully claim — and has no night ability at all.
        if _is_demon(role):
            return False
        return FIRST in CHARACTERS[role].wake
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
    if _came_back_tonight(world, state, seat, night) == ASLEEP:
        return False
    return woke_as(world, state, seat, night, role)


ASLEEP, OPEN = "asleep", "open"


def _came_back_tonight(world, state, seat, night):
    """A seat that returned to life this night: was its turn still to come?

    "They wake later tonight if they normally would." A Shabaloth
    regurgitates just before its own turn and a Professor raises at its
    own, so whoever came back was dead for every slot before that. An
    Innkeeper at 9 slept through; a Chambermaid at 70 did not.

    Which of the two did it is not written down. Before both, it was
    ASLEEP; after both, it woke as it normally would (None); between
    them, OPEN.
    """
    phase = f"N{night}"
    if phase not in (state.resurrections or {}).get(seat, ()):
        return None
    acting = _acts_as(world, seat, phase)
    slot = getattr(CHARACTERS[acting], "other_night", 0) or 0
    raisers = [getattr(CHARACTERS[who], "other_night", 0) or 0
               for who in ("Shabaloth", "Professor")
               if world.find_at(who, phase) is not None]
    if not raisers or slot > max(raisers):
        return None
    return ASLEEP if slot <= min(raisers) else OPEN


def _acts_as(world, seat, phase):
    """The character whose night this seat is living through."""
    role = world.role_at(seat, phase)
    if role != "Lunatic":
        return role
    # The token it was shown — and when nobody recorded one, the Demon
    # that is really in play, which is what a Storyteller reaches for.
    if world.believes[seat]:
        return world.believes[seat]
    demon = world.demon_at(phase)
    return world.role_at(demon, phase) if demon is not None else "Imp"


def uncertain(world, state, seat, night):
    """Could this seat's waking have gone either way?

    Three things do this, and each is something nobody writes down (and
    a Wraith, which follows whoever else evil woke):

      * An Exorcist sending the Demon to bed.
      * The Demon on the first night, told its Minions and its bluffs.
        Not its ability at this table; counted at others. A Lunatic that
        thinks it is that Demon is shown the same thing.
      * A Professor once somebody has come back to life with a Shabaloth
        in play: either of them could have done it.
    """
    phase = f"N{night}"
    acting = _acts_as(world, seat, phase)
    if acting == "Wraith":
        # Open exactly when no other evil seat surely woke and one may
        # have — a Demon on the first night is the usual one.
        if seat not in state.alive_set(phase):
            return False
        certain, maybe = _evil_eyes_open(world, state, seat, night)
        return maybe and not certain
    if night == 1:
        return _is_demon(acting) and CHARACTERS[acting].nights != EVERY
    if _came_back_tonight(world, state, seat, night) == OPEN:
        return True
    if acting == "Assassin":
        # The same as the Professor below, and for the same reason: it is
        # woken until it strikes, and nobody writes down when that was. A
        # body it left looks like any other, and struck while drunk it
        # leaves none. So night two is certain — its first chance — and
        # after that either, unless the strike itself is on the record.
        if night < 3 or seat not in state.alive_set(phase):
            return False
        return not any(getattr(info, "source_role", None) == "Assassin"
                       and info.player == seat for info in state.infos)
    if acting == "Nightwatchman":
        # The first night is certain: its first chance. After that it
        # may have chosen and nobody wrote it down — the player it woke
        # need not have said so, and chosen while drunk it woke nobody.
        # Its own row settles it either way.
        if night < 2 or seat not in state.alive_set(phase):
            return False
        return _chose_on(state, seat, "Nightwatchman") is None
    if acting == "Professor":
        # Night two it is woken for certain: its first chance. After
        # that, it may have chosen somebody who was no Townsfolk, or
        # chosen while drunk — nothing happens, the ability is gone, and
        # nobody at the table can see that it went. Only a return with no
        # Shabaloth about pins it: that was the Professor, awake until
        # then and asleep after.
        if night < 3 or seat not in state.alive_set(phase):
            return False
        raised = _raised_on(state)
        if raised is None:
            return True
        return world.find_at("Shabaloth", f"N{raised}") is not None
    if "Exorcist" not in state.script.keys:
        return False
    if world.demon_at(phase) != seat:
        return False
    exorcist = world.find_at("Exorcist", phase)
    return exorcist is not None and exorcist in state.alive_set(phase)


def possible_counts(world, state, seats, night, asleep=()):
    """Every value "how many of these woke" could have taken.

    `asleep` are seats taken as impaired tonight and so not woken —
    only a Wraith changes by that.
    """
    fixed = 0
    open_ended = 0
    for seat in seats:
        if uncertain(world, state, seat, night):
            open_ended += 1
        elif seat in asleep:
            continue
        elif woke_for_own_ability(world, state, seat, night):
            fixed += 1
    return {fixed + extra for extra in range(open_ended + 1)}


def woken_wraiths(world, state, seats, night):
    """The seats among these that are a Wraith a sober one would surely
    have woken tonight — the ones whose impairment changes the count."""
    phase = f"N{night}"
    return frozenset(
        seat for seat in seats
        if _acts_as(world, seat, phase) == "Wraith"
        and not uncertain(world, state, seat, night)
        and woke_for_own_ability(world, state, seat, night))
