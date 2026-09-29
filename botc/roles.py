"""Facts about characters, and about the standard bag.

Everything here now reads from `catalogue.py`, which holds one record per
character. The module-level lists are Trouble Brewing, kept because most
of the package was written against them and because it is still the
default script — but nothing depends on them being the only script. Pass
a `Script` where one is wanted and these are simply not consulted.
"""

from .catalogue import (CHARACTERS, EVERY, FIRST, NEVER, OTHER, SOMETIMES,
                        WAKE_LABELS, WAKE_PATTERNS, lookup, normalise)
from .scripts import DEFAULT, TROUBLE_BREWING

GOOD = "good"
EVIL = "evil"

# Team is a property of the character, not of the script, so this covers
# everything the catalogue knows.
TEAM = {key: c.team for key, c in CHARACTERS.items()}
DISPLAY = {key: c.name for key, c in CHARACTERS.items() if c.name != key}
WAKE = {key: c.wake for key, c in CHARACTERS.items()}

TOWNSFOLK = TROUBLE_BREWING.townsfolk
OUTSIDERS = TROUBLE_BREWING.outsiders
MINIONS = TROUBLE_BREWING.minions
DEMONS = TROUBLE_BREWING.demons
ALL_ROLES = list(TROUBLE_BREWING.keys)
SETUP_MODIFIERS = TROUBLE_BREWING.setup_modifiers

# Standard distribution: player count -> (townsfolk, outsiders, minions, demons)
SETUP = {
    5:  (3, 0, 1, 1),
    6:  (3, 1, 1, 1),
    7:  (5, 0, 1, 1),
    8:  (5, 1, 1, 1),
    9:  (5, 2, 1, 1),
    10: (7, 0, 2, 1),
    11: (7, 1, 2, 1),
    12: (7, 2, 2, 1),
    13: (9, 0, 3, 1),
    14: (9, 1, 3, 1),
    15: (9, 2, 3, 1),
}


def show(role):
    """Human readable character name."""
    if role is None:
        return "-"
    return DISPLAY.get(role, role)


def is_evil(role):
    """Actual team membership - not how a character *registers*."""
    return TEAM[role] in ("minion", "demon")


def alignment(role):
    """Which side this character starts on.

    Kept apart from the character itself because the two come apart. An
    Ogre turns evil without changing character; a Politician turns good.
    Anything asking "which side is this seat on" has to ask about a
    moment, not about the deal.
    """
    return EVIL if is_evil(role) else GOOD


def believes_another(role):
    """Does whoever holds this think they are somebody else?

    The Drunk, and on other scripts the Marionette and the Lunatic. They
    are woken on the schedule of the character they were handed and given
    answers to match, so nothing they say is a lie.
    """
    return CHARACTERS[role].believes


def thinks_it_is_evil(role):
    """Does the holder believe they are on the evil team?

    A Lunatic does, so it bluffs the way the Demon would — which makes it
    a good player who lies deliberately, and the only one.
    """
    character = CHARACTERS[role]
    return character.believes and any(
        team in ("minion", "demon") for team in character.believes_from)


def must_hide(role):
    """Is this a good character that cannot say what it is?

    The Mutant: claiming to be an Outsider might get it executed, so it
    claims a Townsfolk instead — every time, and without choosing to.
    """
    return CHARACTERS[role].hides


def believed_tokens(role, script):
    """Which characters this one could have been handed to believe in.

    Empty for everybody who knows what they are.
    """
    character = CHARACTERS[role]
    if not character.believes:
        return []
    out = []
    for team in character.believes_from:
        out.extend(script.by_team(team))
    return [k for k in out if not CHARACTERS[k].believes]


def knows_what_it_is(role):
    """Can this seat's holder be relied on to know their own character?

    The distinction matters more than "is it evil". A knowing bluffer
    says whatever suits them, so nothing they claim constrains anything.
    Somebody who was handed the wrong token says what they honestly
    believe — and that *does* constrain, against the token rather than
    against the truth. The Drunk is the Trouble Brewing case; the
    Marionette is the one that shows the two are not the same question,
    because it is evil and still does not know it.
    """
    return not CHARACTERS[role].believes


def evil_registrations(role, side=None):
    """What can this character register as for information purposes?

    Returns the possible values for "is evil". A character that may
    register as a team on the other side is ambiguous, and the
    Storyteller decides which - so both values stay possible. The Recluse
    and the Spy are the Trouble Brewing pair; the catalogue holds the
    rule rather than the code.

    `side` overrides where the seat currently stands, for the characters
    that can be turned. A turned Recluse is still ambiguous, because the
    misregistration belongs to the character and not to the side.
    """
    character = CHARACTERS[role]
    mine = (side == EVIL) if side is not None else is_evil(role)
    # A Goon really is on whichever side last claimed it, and nobody
    # writes down who chose it, so both are live. This is not
    # misregistration: it changes which team they are on, not merely how
    # they read.
    if character.alignment_open:
        return (True, False)
    if not character.registers:
        return (mine,)
    seen = {mine}
    for team in character.registers:
        seen.add(team in ("minion", "demon"))
    return tuple(sorted(seen, reverse=True))


def registers_as_role(actual_role, claimed_role):
    """Can `actual_role` show up as `claimed_role` in character info?

    **Legality, not truth.** Misregistration is the mechanic that lets a
    Storyteller give false information legally — a Spy shown as the
    Slayer is still a Spy, and the reading is still false. It does not
    become true by being permitted.

    Most callers want this one: could the Storyteller have said it. The
    Vortox wants `is_really_role` below, because it falsifies what an
    ability *yields*, and a misregistered reading is already false.
    """
    if actual_role == claimed_role:
        return True
    if claimed_role not in TEAM:
        return False
    return TEAM[claimed_role] in CHARACTERS[actual_role].registers


def is_really_role(actual_role, claimed_role):
    """Is this seat *actually* that character?

    The other half of the question above. A Spy registering as a Townsfolk
    makes showing it as the Slayer legal; it does not make the seat the
    Slayer. Under a Vortox, every Townsfolk reading has to be false, and
    "false" means what the seat is — not what it may be shown as.
    """
    return actual_role == claimed_role


def wake_fits(actual_role, believed_role, said):
    """Could a seat holding this character honestly describe waking so?

    Whoever believes they are somebody else experiences that character's
    schedule, so that is what gets checked for them.
    """
    if not said:
        return True
    apparent = believed_role or actual_role
    return said in WAKE.get(apparent, frozenset(WAKE_PATTERNS))


# --------------------------------------------------------------------------
# Whether an ability is actually doing anything
# --------------------------------------------------------------------------
# "Sober and healthy" is not a yes-or-no question once you leave Trouble
# Brewing, so this is deliberately three-valued rather than a boolean.
#
#   GENUINE    the seat holds the character and the ability works, so
#              whatever it produced has to be true
#   ARBITRARY  the ability is running but the Storyteller made the answer
#              up - the Drunk, and anyone poisoned. Nothing to check
#   INVERTED   the ability produced something actively false rather than
#              merely unreliable. Vortox does this to every Townsfolk, and
#              it is a different claim from ARBITRARY: "not necessarily
#              true" and "guaranteed wrong" cut the world set differently
#   ABSENT     this seat is not that character at all
GENUINE = "genuine"
ARBITRARY = "arbitrary"
INVERTED = "inverted"
ABSENT = "absent"


def ability_state(world, seat, role, phase, gained=None,
                  vortoxed=False):
    """How much weight can be put on what this seat produced.

    Poison is not decided here. The solver posits a poisoning only when a
    statement would otherwise be false, which cannot be known until the
    statement has been checked - so a poisoned seat looks GENUINE at this
    point and is excused afterwards. See `explanation_cost`.
    """
    if world.role_at(seat, phase) == role:
        # A Vortox does not droison anybody: abilities work, and what
        # they *yield* is false. So this is not a weaker GENUINE, it is a
        # stronger one — a poisoned Empath may be told anything, and a
        # Vortox'd one must be told something that is not so.
        #
        # Read off what the seat *is* rather than what it thinks it is: a
        # Drunk holding a Townsfolk token is an Outsider, so a Vortox
        # leaves it alone and its answer stays arbitrary.
        if vortoxed and TEAM[role] == "townsfolk":
            return INVERTED
        return GENUINE
    if believes_another(world.role_at(seat, phase)) \
            and world.believes[seat] == role:
        return ARBITRARY          # they were woken on this role's schedule
    # A Philosopher keeps its own character and gains another's ability,
    # so a seat can be working two at once. `gained` is
    # (role, from, has-it-arrived) for that seat — a Philosopher that
    # took the Juggler on night three was not one on night two.
    if gained is not None:
        taken, since, arrived = gained
        # Ordered by the caller rather than here: `phase_index` lives in
        # info.py, which imports this module, so reaching for it would
        # close a circle. The caller already knows both phases.
        if taken == role and arrived \
                and world.role_at(seat, phase) == "Philosopher":
            # A Vortox reaches a gained ability the same as any other.
            # The *choice* to take it is untouched — nobody told the
            # Philosopher what to take — but what the ability yields is
            # information, and information is what a Vortox falsifies.
            #
            # This returned GENUINE regardless, so a Philosopher holding
            # the Clockmaker gave the true answer on a board where the
            # real Clockmaker could not.
            if vortoxed and TEAM[role] == "townsfolk":
                return INVERTED
            return GENUINE
    return ABSENT
