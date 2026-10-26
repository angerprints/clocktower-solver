"""Step 1 of the solver: which role assignments are legal at all?

A "world" is a complete mapping seat -> true role.
The Drunk is the special case: their true role is Drunk, but they think
they are some Townsfolk. That Townsfolk token is used up and nobody else
can hold it.

Worlds are produced by a generator, so the caller can score them one at a
time and never hold millions of them in memory at once.
"""

import random
from dataclasses import dataclass
from typing import NamedTuple

from .catalogue import CHARACTERS
from .info import _READS, note_side_read, phase_index
from .roles import (EVIL, TEAM, SETUP, alignment, believed_tokens,
                    believes_another, is_evil, knows_what_it_is,
                    must_hide, thinks_it_is_evil, wake_fits)
from .scripts import DEFAULT



@dataclass(frozen=True)
class World:
    # roles[i] = true role of seat i
    roles: tuple
    # believes[i] = role seat i thinks they have (only set for the Drunk)
    believes: tuple

    def apparent_role(self, i):
        return self.believes[i] or self.roles[i]

    def find(self, role):
        """Index of the seat holding this role, or None.

        Indexed on first use. Every character rule on a script asks this
        of every world on every night, and with a full script that is
        twenty-odd scans of the table per night — enough to cost more
        than the reasoning does.
        """
        index = self.__dict__.get("_index")
        if index is None:
            # The first seat, when more than one holds it (a second
            # Village Idiot) — as the JavaScript does.
            index = {}
            for i, r in enumerate(self.roles):
                index.setdefault(r, i)
            object.__setattr__(self, "_index", index)
        return index.get(role)

    # ----------------------------------------------------------------
    # Asking about a moment rather than about the game
    # ----------------------------------------------------------------
    # A world is one starting assignment, so today these three ignore the
    # phase entirely and answer from the deal. They exist so that every
    # check that cares *when* it is asking says so out loud, and the day a
    # character can change hands - the Imp passing the star, a Pit-Hag
    # rewriting somebody - only these have to learn about it. Asking
    # `roles[seat]` directly is fine for questions about the whole game,
    # like who claimed what; it is wrong for anything a handover moves.

    def role_at(self, seat, phase):
        """The character this seat held at this phase."""
        if TEA_READS[0] is not None:
            _tea_read(phase)
        return self.roles[seat]

    def find_at(self, role, phase):
        """Which seat held this character at this phase."""
        if TEA_READS[0] is not None:
            _tea_read(phase)
        return self.find(role)

    def demon_at(self, phase):
        """Which seat held the Demon at this phase."""
        if TEA_READS[0] is not None:
            _tea_read(phase)
        for i, r in enumerate(self.roles):
            if TEAM[r] == "demon":
                return i
        return None

    def demons_at(self, phase):
        """Every seat that is a Demon at this phase: one, or none before a
        Summoner made one. Two only in a story (`Timeline.demons_at`)."""
        seat = self.demon_at(phase)
        return () if seat is None else (seat,)

    def team_at(self, seat, phase):
        return TEAM[self.role_at(seat, phase)]

    def alignment_at(self, seat, phase):
        """Which side this seat was on at this phase.

        Kept apart from the character because the two come apart: an Ogre
        turns evil without changing character, a Politician turns good. A
        plain world has nothing to move, so this is simply where the
        character started.
        """
        if _READS:
            note_side_read(seat, phase)
        if TEA_READS[0] is not None and len(TEA_READS[0]) > 2:
            _tea_read(phase)
        return alignment(self.roles[seat])

    def evil_at(self, seat, phase):
        return self.alignment_at(seat, phase) == EVIL

    def evil_players(self):
        return [i for i, r in enumerate(self.roles) if is_evil(r)]


class OffScript(ValueError):
    """A seat claimed a character that is not on this script."""

    def __init__(self, claim, script_name):
        self.claim = claim
        self.script_name = script_name
        super().__init__(
            f"{claim} is not on {script_name}, so nobody can be claiming "
            f"it. Change the script, or change the claim.")


class Change(NamedTuple):
    """One seat becoming something else, from one phase onward.

    Either half may be left alone. `role=None` keeps the character and
    moves only the side, which is what an Ogre or a Politician does;
    `side=None` takes whichever side the new character normally sits on,
    which covers a Minion catching the star. Both together cover a
    Pit-Hag rewriting somebody into anything at all.
    """

    phase: str
    seat: int
    role: str = None
    side: str = None
    # Where in its night it happened (Hatter stage 3b, 23.10.2026): the
    # slot of the character that made it, from the publisher's night sheet
    # (`catalogue.slot_of`). None is the end of the night, as every change
    # was before — and as one still is that no character's turn made.
    # SETUP_SLOT is before anybody acts.
    slot: int = None


class TurnedEvil(Change):
    """A seat turned evil that knows it and keeps its character: the
    Bounty Hunter's evil Townsfolk, whoever a Mezepheles turned
    (11.10.2026). Told apart from an Ogre's turn because such a seat may
    lie about what it learns from then on (`info.knows_it_turned_evil`).
    """
    __slots__ = ()


class Babysits(Change):
    """Who babysits Lil' Monsta from this night on, and "is the Demon"
    (21.10.2026). Chosen by the Minions each night at its place in the
    night — so one made on night three is the Demon for whoever reads
    after that place on night three, and on day three. Changes nothing
    about the seat: no character, no side (B, Weg 1: anybody may).
    """
    __slots__ = ()


# Which nights' babysitters were looked at, while somebody is listening
# (solver._best_babysat_story): a telling that failed without asking
# about a night fails the same whoever babysat then.
BABYSAT_READS = [None]


def lil_monsta_world(world):
    """Was this world dealt with Lil' Monsta in the bag — nobody holding a
    Demon? The only other bag without one has a Summoner in it."""
    return not any(TEAM[r] == "demon" for r in world.roles) \
        and "Summoner" not in world.roles


class Summoned(Change):
    """The player the Summoner made an evil Demon of its choice
    (21.10.2026, claude/beschwoerer-lesarten.md): on the third night, or
    a Pukka on the second (their jinx). Before it there is no Demon at
    all. A character change like any other — the old one is gone — told
    apart so the search over who and which can see it was asked about.
    """
    __slots__ = ()


class HandedOn(Change):
    """Which Demon a handover took the star from, where two Demons live
    (Hatter stage 2, 25.10.2026): a mark on the seat that fell, at the
    moment of the move it stands beside. Changes nothing. With one Demon
    there is nothing to tell apart and nobody writes one."""
    __slots__ = ()


class NotSummoned(Change):
    """No Demon came: the Summoner died before its turn, or was drunk or
    poisoned on it, and good won there (D and E, Weg 1, 21.10.2026). A
    mark that changes nothing, at the moment the game ended."""
    __slots__ = ()


# Whether anything about the summoned Demon was looked at while a story
# was told (solver._best_summoned_story): who held what, or which side,
# or who the Demon was, from the moment of the summoning on. A telling
# that failed without looking fails the same for every summoning.
SUMMON_READS = [None]


def summoner_world(world):
    """Was the Summoner dealt in this world? Then nobody was dealt the
    Demon."""
    return "Summoner" in world.roles


class TeaParty(Change):
    """A Minion or the Demon that chose a new character when the Hatter
    died (22.10.2026, claude/hutmacher-lesarten.md): of the same type, or
    under the optional rule the Demon and a Minion swapping types (B Weg 2,
    J Weg 1). From the start of the night after a death by day (C). Told
    apart so the search over who chose what can see it was asked about."""
    __slots__ = ()


# Whether anything from the Hatter's night on was looked at while a story
# was told (solver._best_tea_story): [moment, looked]. A telling where
# nobody chose anything new, that failed without looking, fails the same
# for every choice. A third element asks for sides as well: a Summoner's
# Demon turns its player evil (Hatter stage 2, 25.10.2026), where a tea
# party keeps everybody's side.
TEA_READS = [None]


def tea_made(world, seat, night):
    """Did this seat take its character at that night's tea party? Then
    that night is its first with it (O Weg 1, 22.10.2026)."""
    phase = f"N{night}"
    return any(isinstance(c, TeaParty) and c.seat == seat
               and c.phase == phase for c in getattr(world, "changes", ()))


# A change made before anybody acts that night: a Marionette's real
# character until a Summoner's Demon comes, a babysitter from the moment
# after the last one fell.
SETUP_SLOT = -1

# Whose turn of the night is reading the board, while one is
# (Hatter stage 3b, 23.10.2026; E Weg 1): (phase, first-night slot,
# other-nights slot). With a phase, only that night is read at the slot —
# a row of night three asking about night two asks about all of night
# two. Without one (None), every night is read at the slot — a rule
# asking what its character did on each night of the game.
#
# Read **at the end of** that slot: the reader sees what it did itself
# (a Pit-Hag's row sees the seat it changed) and everything before it,
# nothing after. Before, every reader saw the whole night (open item 36:
# a Snake Charmer that chose early read as whatever the Pit-Hag made it
# later).
READ_AT = [None]


def _within(here, slot, offset):
    """A moment inside a night: past the board as it began ("B", +0.75
    from the day before) and before the night as a whole."""
    return here - 0.25 + (slot + offset) / 4000


def moment(phase):
    """A phase as a number on one line with the changes: `phase_index`,
    and "B" — the board as a night began, after a tea party at its very
    start (22.10.2026) — a little past the day before it. A tea party is
    stamped on its night and stands a little before it (`_at`). And a
    night read by one character's turn (`READ_AT`) stands at that turn."""
    here = phase_index(phase)
    if phase[0] == "B":
        return here + 0.75
    at = READ_AT[0]
    if at is not None and phase[0] == "N" and (at[0] is None
                                               or at[0] == phase):
        slot = at[1] if phase == "N1" else at[2]
        if slot:
            return _within(here, slot, 0.75)
    return here


def _at(change):
    """Where a change stands on that line: a tea party just before the
    night it is stamped with, after the day before; a change made at a
    slot of its night just after that slot (`Change.slot`)."""
    here = phase_index(change.phase)
    if change.slot is not None and change.phase[0] == "N":
        return _within(here, change.slot, 0.5)
    return here - 0.5 if isinstance(change, TeaParty) else here


class reading_at:
    """`with reading_at(phase, first, other):` — see `READ_AT`."""

    __slots__ = ("got", "was")

    def __init__(self, phase, first, other):
        self.got = (phase, first, other) if (first or other) else None

    def __enter__(self):
        self.was = READ_AT[0]
        if self.got is not None:
            READ_AT[0] = self.got
        return self

    def __exit__(self, *_exc):
        READ_AT[0] = self.was
        return False


def _tea_read(phase):
    reads = TEA_READS[0]
    if reads is not None and moment(phase) >= reads[0]:
        reads[1] = True


def dealt_roles(world):
    """The characters the players really hold when the game starts.

    The deal itself, but for a Summoner's Marionette: nobody is the
    Marionette until the Demon comes (Patrick, 22.10.2026), so until then
    its seat holds the good character it believes — a Bounty Hunter there
    brings in its evil Townsfolk, a Puzzlemaster keeps somebody drunk, the
    seat may be the red herring."""
    roles = world.roles
    if "Summoner" in roles and "Marionette" in roles:
        m = roles.index("Marionette")
        token = world.believes[m]
        if token:
            # One thinking it is a Demon was the Lunatic. One holding a
            # Townsfolk token may have been the Drunk; read as that
            # Townsfolk here, which only lets more through.
            held = "Lunatic" if TEAM[token] == "demon" else token
            return roles[:m] + (held,) + roles[m + 1:]
    return roles


@dataclass(frozen=True)
class Timeline:
    """A world plus the times a character changed hands.

    The world underneath is still a single starting assignment. What
    changes with time is layered on top, in the same lazy way the poison
    schedule and the red herring already are: posited only when something
    forces it, and searched over rather than stored.

    The changes are `Change` records, applied in order. Nothing here is
    specific to what caused them: the Demon dying is simply the first
    rule that produces any. See `TRANSITION_RULES` in the solver.
    """

    world: World
    changes: tuple = ()

    def __post_init__(self):
        # A timeline laid over a timeline is one timeline. The rules are
        # handed a view and build their own on top of it — the Demon's
        # lineage walk and the Farmer both do — and every question here
        # reads `self.world.roles`, which on a nested view is the deal:
        # the changes underneath were silently dropped (29.09.2026).
        if isinstance(self.world, Timeline):
            object.__setattr__(self, "changes",
                               tuple(self.world.changes) + tuple(self.changes))
            object.__setattr__(self, "world", self.world.world)
        # And in time order. Every question here takes the last change
        # that applies, reading the list front to back — so a night-two
        # jump written after a night-three swap overwrote the swap, and a
        # Sweetheart the Snake Charmer had swapped away was still the Fang
        # Gu (29.09.2026). Stable, so changes at one moment keep the order
        # the rules made them in.
        object.__setattr__(self, "changes", tuple(sorted(
            self.changes, key=_at)))
        # Indexed once, by seat, with each moment already turned into a
        # number. Every question below used to walk all the changes and
        # parse every phase again — fourteen million times on one ten-seat
        # board — when most seats never change at all. Same answers, same
        # order; only the walk is shorter.
        roles, sides, demons, held = {}, {}, [], set()
        handed = {}
        for change in self.changes:
            at = _at(change)
            if isinstance(change, Babysits):
                demons.append((at, change.seat, change.phase, False))
                continue
            if isinstance(change, HandedOn):
                handed.setdefault(at, set()).add(change.seat)
                continue
            sides.setdefault(change.seat, []).append((at, change))
            if change.role is not None:
                mine = roles.setdefault(change.seat, [])
                was = mine[-1][1] if mine else self.world.roles[change.seat]
                mine.append((at, change.role))
                held.add(change.role)
                # A tea party moves the Demon only where a Minion took a
                # Demon character (the optional rule's swap). The Demon
                # taking another Demon is the same holder — and a seat
                # that was no Minion at all is a story asked about without
                # the handover that made it the Demon (a Fang Gu's jump),
                # which the lineage has to be free to find (seed 852).
                if TEAM[change.role] == "demon" and not (
                        isinstance(change, TeaParty)
                        and TEAM.get(was) != "minion"):
                    demons.append((at, change.seat, None,
                                   isinstance(change, Summoned)))
        object.__setattr__(self, "_roles_by_seat", roles)
        object.__setattr__(self, "_sides_by_seat", sides)
        object.__setattr__(self, "_roles_changed_to", held)
        object.__setattr__(self, "_demon_changes",
                           self._demon_steps(demons, handed))
        # A story with Lil' Monsta in it: somebody babysits. Only then is
        # a Demon holding no Demon character a babysitter — not where a
        # Pit-Hag made the Demon something else (21.10.2026).
        object.__setattr__(self, "lil_monsta", any(
            babysat is not None for _at, _seat, babysat, _s in demons))
        # Where a Summoner made the Demon, if it did in this story.
        object.__setattr__(self, "_summon_at", next(
            (phase_index(c.phase) for c in self.changes
             if isinstance(c, Summoned)), None))

    def _demon_steps(self, demons, handed):
        """Who the Demons are after each change that moves one:
        [(moment, seats, babysat)], the seats in the order their lines
        began.

        Two Demons live only after a Summoner made one beside the Demon in
        play (Hatter stage 2, 25.10.2026, A Weg 1). Every other change
        that makes somebody the Demon takes over one line: the line of the
        seat marked as having handed it on (`HandedOn`), else the Demon
        that no longer holds a Demon character by then (a Snake Charmer's
        swap, a tea party's), else the first. With one Demon this is
        exactly "the last to have become one", as before."""
        if not demons:
            return []
        start = self.world.demon_at("N1")
        line = () if start is None else (start,)
        out = []
        for at, seat, babysat, summoned in demons:
            if seat in line:
                pass
            elif summoned and len(line) == 1:
                line = line + (seat,)
            elif len(line) <= 1:
                line = (seat,)
            else:
                marked = handed.get(at, ())
                which = next((i for i, d in enumerate(line) if d in marked),
                             None)
                if which is None:
                    which = next(
                        (i for i, d in enumerate(line)
                         if TEAM[self._role_by(d, at)] != "demon"), 0)
                line = line[:which] + (seat,) + line[which + 1:]
            out.append((at, line, babysat))
        return out

    def _role_by(self, seat, at):
        """The character a seat holds at this point on the line."""
        role = self.world.roles[seat]
        for when, changed in self._roles_by_seat.get(seat, ()):
            if when <= at:
                role = changed
        return role

    # Questions about the whole game go straight through: who was dealt
    # what, who claimed what. Only questions about a moment consult the
    # changes.
    @property
    def roles(self):
        return self.world.roles

    @property
    def believes(self):
        return self.world.believes

    def find(self, role):
        return self.world.find(role)

    def apparent_role(self, i):
        return self.world.apparent_role(i)

    def evil_players(self):
        return self.world.evil_players()

    def _summon_read(self, phase):
        """Anything asked from the summoning on depends on it."""
        if self._summon_at is not None and SUMMON_READS[0] is not None \
                and phase_index(phase) >= self._summon_at:
            SUMMON_READS[0][0] = True

    def role_at(self, seat, phase):
        if self._summon_at is not None:
            self._summon_read(phase)
        if TEA_READS[0] is not None:
            _tea_read(phase)
        role = self.world.roles[seat]
        mine = self._roles_by_seat.get(seat)
        if mine:
            here = moment(phase)
            for at, changed in mine:
                if at <= here:
                    role = changed
        return role

    def alignment_at(self, seat, phase):
        if _READS:
            note_side_read(seat, phase)
        if self._summon_at is not None:
            self._summon_read(phase)
        if TEA_READS[0] is not None and len(TEA_READS[0]) > 2:
            _tea_read(phase)
        side = alignment(self.world.roles[seat])
        mine = self._sides_by_seat.get(seat)
        if mine:
            here = moment(phase)
            for at, change in mine:
                if at > here:
                    continue
                # An explicit side wins; otherwise the new character's.
                side = change.side or (alignment(change.role) if change.role
                                       else side)
        return side

    def evil_at(self, seat, phase):
        return self.alignment_at(seat, phase) == EVIL

    def find_at(self, role, phase):
        if TEA_READS[0] is not None:
            _tea_read(phase)
        # Nobody dealt it and nobody changed into it: nobody holds it.
        if role not in self._roles_changed_to and role not in self.world.roles:
            return None
        for seat in range(len(self.world.roles)):
            if self.role_at(seat, phase) == role:
                return seat
        return None

    def demon_at(self, phase):
        """Which seat is the Demon now — the last to have become one.

        Tracked through the changes rather than read off the board,
        because **holding a demon character is not the same as being the
        Demon**. A handover leaves the old character where it was: an
        executed Imp still holds the Imp when the Scarlet Woman inherits,
        so two seats hold one and the board cannot say which is which.

        Reading the board instead threw away eight legal worlds on
        Trouble Brewing — the lineage walk started at the corpse and
        found nothing.

        A Snake Charmer swap is tracked here too, because the swap grants
        the charmer the Demon's *character*, which is a change with a
        demon role in it. That only failed while the swap was copying the
        wrong character; the tracking was never the fault.
        """
        seats = self.demons_at(phase)
        return seats[0] if seats else None

    def demons_at(self, phase):
        """Every seat that is a Demon now, in the order their lines began:
        the one dealt (or the Summoner's) first, a second only after a
        Summoner made one beside it (Hatter stage 2, 25.10.2026).
        `demon_at` is the first of them."""
        seat = self.world.demon_at(phase)
        if self._summon_at is not None:
            self._summon_read(phase)
        if TEA_READS[0] is not None:
            _tea_read(phase)
        seats = () if seat is None else (seat,)
        if self._demon_changes:
            here = moment(phase)
            sat = None
            for at, changed, babysat in self._demon_changes:
                if at <= here:
                    seats, sat = changed, babysat
            reads = BABYSAT_READS[0]
            if sat is not None and reads is not None:
                reads.add(sat)
        return seats

    def team_at(self, seat, phase):
        return TEAM[self.role_at(seat, phase)]


def _anything(script):
    """Every character on this script, with the believers expanded.

    A character whose holder believes they are somebody else - the Drunk,
    and elsewhere the Marionette - is not one option but one per token it
    could have been handed.
    """
    out = []
    for key in script.seated_keys:
        if believes_another(key):
            out.extend((key, token) for token in believed_tokens(key, script))
        else:
            out.append((key, None))
    return out


def _candidates(claim, allow_good_lies, certainty="", allowed=None,
                wake=None, script=DEFAULT):
    """Which (role, believes-they-are) options fit a given claim?

    Baseline assumption: good players do not lie. Someone claiming a
    Townsfolk is either really that Townsfolk, the Drunk holding that
    token, or evil (i.e. bluffing).

    `allow_good_lies` opens exactly one more door: an Outsider covering up
    behind someone else's role. That is the good lie people actually tell,
    and it stays cheap to search. A Townsfolk falsely claiming a different
    Townsfolk is left to the per-seat "not trusted" setting, because it is
    both very rare and very expensive to enumerate.

    `certainty` overrides that per seat:
      "self"      - your own seat. You can see your token, so you hold
                    that role - unless the Storyteller made you the Drunk,
                    which you would not know.
      "confirmed" - the role is established, e.g. a Virgin that triggered.
                    A drunk Virgin would not have triggered, so no Drunk.
      "hiding"    - this seat may be a good player covering up, i.e. an
                    Outsider claiming somebody else's role. Cheap, and it
                    is the good lie people actually tell.
      "unsure"    - this claim is not trusted at all. The seat could hold
                    any role, good or evil. Expensive: it multiplies the
                    search space, so use it sparingly.

    `wake` is what the seat has said about waking at night - see
    roles.WAKE. It is a softer kind of claim and prunes the same way.

    `allowed` is a set of roles this seat is restricted to by something
    the whole table watched happen - a Virgin that triggered, a Slayer
    shot that landed. It narrows whatever the claim allows; it never
    widens it, so a claim still does its own pruning underneath.
    """
    opts = _candidates_from_claim(claim, allow_good_lies, certainty, script)

    # A soft claim about waking narrows the good roles the same way a hard
    # claim does. Evil is never held to it - they know what they are and
    # will describe whatever suits the bluff.
    # Held to a wake claim if the seat knows what it is — a knowing
    # bluffer is not, because they say whatever suits them. Somebody
    # handed the wrong token is, because they answer honestly about the
    # character they think they have. That is not the same question as
    # "are they evil": a Marionette is evil and still does not know.
    if wake and certainty not in ("hiding", "unsure"):
        opts = [o for o in opts
                if (is_evil(o[0]) and knows_what_it_is(o[0]))
                or must_hide(o[0])
                or wake_fits(o[0], o[1], wake)]

    if allowed is not None:
        opts = [o for o in opts if o[0] in allowed]
    return opts


def _itself(key, script):
    """This character as a candidate, with a token if it needs one.

    Somebody handed the wrong character always holds something. Claiming
    to *be* the Drunk is a legal thing to say, and dealing one with no
    token behind it produces a world that is not a game.
    """
    if believes_another(key):
        return [(key, token) for token in believed_tokens(key, script)]
    return [(key, None)]


def _evil_options(evil, script):
    """Evil characters that could be bluffing this claim.

    Believers are left out on purpose. Somebody handed the wrong token
    says what they believe, so the only claim they make is that token —
    which the line above already covers. Letting them in here would offer
    a Marionette who thinks it is the Recluse while claiming to be the
    Soldier, and that is a deliberate lie from somebody who thinks they
    are good.
    """
    out = [(key, None) for key in evil
           if knows_what_it_is(key) and CHARACTERS[key].dealt]
    # Somebody who thinks they are the Demon bluffs like the Demon. A
    # Lunatic is good and lies anyway, because as far as it knows it has
    # every reason to.
    for key in script.keys:
        if thinks_it_is_evil(key):
            out.extend((key, token) for token in believed_tokens(key, script))
    # A Lunatic beside the Summoner's Demon becomes its Marionette and goes
    # on thinking it is a Demon (22.10.2026): a Marionette holding a Demon
    # token, bluffing like the Lunatic it was. Only with a Summoner dealt
    # (`believes_legally`).
    if {"Summoner", "Marionette", "Lunatic"} <= set(script.keys):
        out.extend(("Marionette", token)
                   for token in believed_tokens("Lunatic", script))
    return out


# Characters a seat can come to hold without being dealt them.
#
def _candidates_from_claim(claim, allow_good_lies, certainty="",
                           script=DEFAULT):
    townsfolk = script.townsfolk
    outsiders = script.outsiders
    evil = script.minions + script.demons
    believers = [k for k in script.keys if believes_another(k)]

    if claim and certainty == "confirmed":
        return _itself(claim, script)

    if claim and certainty == "self":
        out = list(_itself(claim, script))
        out += [(b, claim) for b in believers
                if claim in believed_tokens(b, script)]
        return out

    # An empty claim is no claim. The server never sends one, so this
    # went unnoticed until a second implementation was held against this
    # one — before which an empty string reached the bottom of this
    # function and raised "  is not on Trouble Brewing", which is a
    # confusing way to say "this seat said nothing".
    if not claim or certainty == "unsure":
        return _anything(script)

    if certainty == "hiding":
        allow_good_lies = True

    out = []
    if claim in townsfolk:
        out.extend(_itself(claim, script))
        out.extend((b, claim) for b in believers
                   if claim in believed_tokens(b, script))
        out.extend(_evil_options(evil, script))
        if allow_good_lies:
            out.extend((r, None) for r in outsiders
                       if not believes_another(r))
        else:
            # A Mutant is behind a Townsfolk claim whether or not good
            # lies are allowed: it has no other claim it can safely make.
            out.extend((r, None) for r in outsiders if must_hide(r))
        # And a Pixie, mad about being the Townsfolk it was shown: that is
        # its ability asking it to lie (11.10.2026).
        if "Pixie" in script.keys and claim != "Pixie":
            out.append(("Pixie", None))
        return out

    if claim in outsiders:
        out.extend(_itself(claim, script))
        out.extend((b, claim) for b in believers
                   if claim in believed_tokens(b, script))
        out.extend(_evil_options(evil, script))
        if allow_good_lies:
            out.extend((r, None) for r in outsiders
                       if r != claim and not believes_another(r))
        return out

    if claim in evil and not CHARACTERS[claim].dealt:
        # Lil' Monsta is nobody's character: claiming it says nothing
        # about the seat (a babysitter says so in its own row).
        return _anything(script)

    if claim in evil:
        # Openly claiming an evil character. Still needs its token if it
        # is the kind that holds one — a Marionette claiming to be a
        # Marionette is odd, but it is not a world with a gap in it.
        return _itself(claim, script)

    # Nobody can claim a character that is not in the bag. This used to be
    # set aside as "no constraint", which was wrong twice over: it is not
    # what the board says, and a table of such claims leaves every seat
    # unconstrained and the search with nothing to prune on — which does
    # not fail, it hangs.
    raise OffScript(claim, script.name)


def _bags(n_players, script=DEFAULT, fabled=()):
    """Every distribution this table size could have been dealt.

    One entry per combination of setup-changing characters: which of them
    are in the bag, and what the counts become. Trouble Brewing has only
    the Baron, so this yields two — the plain split, and the split with a
    Baron in it. The shape is general because other scripts stack several,
    and some offer a choice of shift rather than a fixed one.
    """
    base = dict(zip(("townsfolk", "outsider", "minion", "demon"),
                    SETUP[n_players]))
    bags = [(frozenset(), base)]
    for role, shifts in script.setup_modifiers.items():
        grown = []
        for present, counts in bags:
            grown.append((present, counts))       # this one stayed out
            # A shift that would take a team below nought cannot be made.
            # Where there is another to choose — a Godfather's "-1 or +1"
            # at a table with no Outsiders — that one is taken. Where
            # there is not, the character is in play and changes nothing:
            # a Vigormortis removes an Outsider "if there is one".
            possible = [shift for shift in shifts
                        if all(counts[team] + delta >= 0
                               for team, delta in shift.items())] or [{}]
            for shift in possible:
                moved = dict(counts)
                for team, delta in shift.items():
                    moved[team] += delta
                grown.append((present | {role}, moved))
        bags = grown

    # A Fabled is on the table, not in the bag. It is in play because the
    # Storyteller said so and showed everybody, so there is no "it stayed
    # out" branch — only the question of what it did, which nobody at the
    # table knows. "It changed nothing" is one of the Sentinel's answers,
    # and ruling it in still costs a whole extra search.
    for key in fabled:
        shifts = CHARACTERS[key].setup or ({},)
        grown = []
        for present, counts in bags:
            for shift in shifts:
                moved = dict(counts)
                for team, delta in shift.items():
                    moved[team] += delta
                grown.append((present, moved))
        bags = grown

    bags += _marionette_to_be(bags, script)

    # Whatever the shifts did, the bag still has to seat everybody. A
    # modifier that moves one number without moving another back is a
    # mistake in the catalogue, and it would otherwise show up as a
    # silently wrong world count rather than as an error.
    bags = [(present, counts) for present, counts in bags
            if sum(counts.values()) == n_players]

    out = []
    seen = set()
    room = {"townsfolk": len(script.townsfolk),
            "outsider": len(script.outsiders),
            "minion": len(script.minions), "demon": len(script.demons)}
    for present, counts in bags:
        if any(counts[t] < 0 or counts[t] > room[t] for t in counts):
            continue                              # no such bag exists
        # Two Fabled answers can land on the same distribution. Searching
        # it twice would count every world in it twice.
        signature = (present, tuple(sorted(counts.items())))
        if signature in seen:
            continue
        seen.add(signature)
        out.append((present, counts))
    return out


# Stelle 73, A (Patrick, 22.10.2026): with a Summoner nobody is dealt the
# Marionette. Its Minion's place goes to a good character of either kind,
# and the Marionette is whoever neighbours the Demon when it comes. A world
# still seats it where it ends up, believing what that player held until
# then, so the deal it shows is off by one where those two are of
# different kinds. These bags carry that, marked with the kind the
# Marionette's player must have held.
MARIONETTE_HELD = {"Marionette@outsider": "outsider",
                   "Marionette@townsfolk": "townsfolk"}


def _marionette_to_be(bags, script):
    """The extra bags for a Summoner's Marionette (Stelle 73, A)."""
    if "Marionette" not in script.keys:
        return []
    out = []
    for present, counts in bags:
        if "Summoner" not in present or counts["minion"] < 2:
            continue
        # Held an Outsider, its place got a Townsfolk: one Townsfolk more
        # and one Outsider fewer than the deal shows; and the other way.
        for held, more, fewer in (("outsider", "townsfolk", "outsider"),
                                  ("townsfolk", "outsider", "townsfolk")):
            if counts[fewer] < 1:
                continue
            moved = dict(counts)
            moved[more] += 1
            moved[fewer] -= 1
            out.append((present | {"Marionette", f"Marionette@{held}"},
                        moved))
    return out


def _held_before(token, script):
    """The kinds a Summoner's Marionette believing this token may have
    held until the Demon came: that character, the Drunk holding a
    Townsfolk token, the Lunatic thinking it is a Demon."""
    team = TEAM[token]
    if team == "demon":
        return {"outsider"}
    if team == "townsfolk" and "Drunk" in script.keys:
        return {"townsfolk", "outsider"}
    return {team}


def _branches(n_players, claims, certainties, allow_good_lies, forced, wakes,
              script=DEFAULT, fabled=()):
    """One search per possible bag, with the candidates already narrowed."""
    if n_players not in SETUP:
        raise ValueError("Table sizes from 5 to 15 players.")
    certainties = certainties or {}
    forced = forced or {}
    wakes = wakes or {}
    movers = script.setup_modifiers

    out = []
    for present, target in _bags(n_players, script, fabled):
        cands = []
        for i in range(n_players):
            opts = _candidates(claims.get(i), allow_good_lies,
                               certainties.get(i, ""), forced.get(i),
                               wakes.get(i), script)
            # A character that changes the bag can only be dealt in a bag
            # that was changed by it.
            opts = [o for o in opts if o[0] not in movers or o[0] in present]
            for mark, held in MARIONETTE_HELD.items():
                if mark in present:
                    opts = [o for o in opts if o[0] != "Marionette"
                            or held in _held_before(o[1], script)]
            cands.append(opts)

        # Seats with fewest options first, so the search prunes earlier
        order = sorted(range(n_players), key=lambda i: len(cands[i]))
        # What has to land on a seat: not Lil' Monsta, which changes the
        # bag and is never dealt (21.10.2026).
        dealt = frozenset(k for k in present
                          if k in CHARACTERS and CHARACTERS[k].dealt)
        out.append((target, cands, order, dealt))
    return out


# Characters more than one seat may hold: the Village Idiot, up to three
# (11.10.2026). Everything else is one token in the bag.
COPIES = {key: c.copies for key, c in CHARACTERS.items() if c.copies > 1}


def _free(role, used, taken):
    """Is a token of this character still in the bag?"""
    if role not in used:
        return True
    return role in COPIES and taken.get(role, 0) < COPIES[role]


def _take(role, used, taken):
    used.add(role)
    taken[role] = taken.get(role, 0) + 1


def _give_back(role, used, taken):
    taken[role] -= 1
    if not taken[role]:
        del taken[role]
        used.discard(role)


def _viable(cands_i, used, count, target, taken=None):
    """Which options are still open for this seat right now."""
    taken = taken if taken is not None else {}
    return [(role, belief) for role, belief in cands_i
            if _free(role, used, taken)
            and (belief is None or _free(belief, used, taken))
            and count[TEAM[role]] < target[TEAM[role]]]


def _lookahead(cands, order):
    """Precomputed answers to "what can the seats after this one give me?"

    For each position and team: how many later seats could supply it, and
    which roles of that team they could supply between them. The second
    is what matters — a dozen seats can all offer to be the Drunk, but
    there is only one Drunk token, so they cannot cover two Outsiders.
    """
    teams = [frozenset(TEAM[r] for r, _b in opts) for opts in cands]
    keys = ("townsfolk", "outsider", "minion", "demon")
    n = len(order)

    seats = [dict.fromkeys(keys, 0) for _ in range(n + 1)]
    roles = [{t: frozenset() for t in keys} for _ in range(n + 1)]
    for k in range(n - 1, -1, -1):
        i = order[k]
        seats[k] = dict(seats[k + 1])
        roles[k] = dict(roles[k + 1])
        for t in teams[i]:
            seats[k][t] += 1
        for role, _b in cands[i]:
            t = TEAM[role]
            roles[k][t] = roles[k][t] | {role}
    return teams, seats, roles


def _fits_ahead(count, target, look, order, k, used):
    """Could the seats from position k onward fill what is still missing?

    Deliberately a relaxation: it never rules out a world that could
    actually be reached, it only cuts walks already going nowhere.
    """
    teams, seats, roles = look
    need = {t: target[t] - count[t] for t in target}
    wanted = {t for t, want in need.items() if want > 0}
    for t, want in need.items():
        if want <= 0:
            continue
        if seats[k][t] < want:
            return False                  # not enough seats left
        # A character more than one seat may hold is more than one
        # token. Counted at its most, which keeps this a relaxation.
        left = roles[k][t] - used
        spare = sum(COPIES[r] - 1 for r in roles[k][t] if r in COPIES)
        if len(left) + spare < want:
            return False                  # not enough tokens left
    for j in order[k:]:
        if not (teams[j] & wanted):
            return False                  # this seat can fill nothing needed
    return True


def _prune(options, count, target, look, order, k, used):
    """Drop options whose team cannot be afforded later on."""
    if k >= len(order):
        return options
    verdict = {}
    for role, belief in options:
        team = TEAM[role]
        if team not in verdict:
            count[team] += 1
            had = role in used            # a second Village Idiot
            used.add(role)
            verdict[team] = _fits_ahead(count, target, look, order, k, used)
            if not had:
                used.discard(role)
            count[team] -= 1
    return [o for o in options if verdict[TEAM[o[0]]]]


def in_a_line(roles, lord):
    """Do the evil characters sit in one line, `lord` not at either end?

    The Lord of Typhon's setup (Patrick, 19.10.2026):

    * A: anywhere in the line but at an end — evil on both sides.
    * Who may stand in the line beside the Minions and the Demon: a
      character that can register as a Minion, at any place in it (the
      Recluse), and an evil Townsfolk of the Bounty Hunter's (B, Weg 1:
      may be part of it, need not). Which Townsfolk turned evil is the
      Bounty Hunter's story, not the deal's, so any one Townsfolk may
      stand in for it while a Bounty Hunter was dealt — permissive.
    """
    n = len(roles)
    evil = {s for s, r in enumerate(roles)
            if TEAM[r] in ("minion", "demon")}
    bounty = "BountyHunter" in roles

    def kind(seat):
        role = roles[seat]
        if seat in evil:
            return "evil"
        if "minion" in CHARACTERS[role].registers:
            return "registers"
        if bounty and TEAM[role] == "townsfolk":
            return "townsfolk"
        return None

    kinds = [kind(s) for s in range(n)]
    if kinds[(lord - 1) % n] is None or kinds[(lord + 1) % n] is None:
        return False
    for start in range(n):
        if kinds[start] is None or start == lord:
            continue
        townsfolk = 0
        covered = 0
        for length in range(1, n + 1):
            seat = (start + length - 1) % n
            if kinds[seat] is None:
                break
            townsfolk += kinds[seat] == "townsfolk"
            if townsfolk > 1:
                break
            covered += seat in evil
            if covered == len(evil) and seat != lord and length >= 3:
                return True
    return False


def believes_legally(roles, believes):
    """A Marionette that thinks it is a Demon was a Lunatic until the
    Summoner's Demon came (22.10.2026): only where a Summoner was dealt."""
    for role, token in zip(roles, believes):
        if role == "Marionette" and token is not None \
                and TEAM[token] == "demon" and "Summoner" not in roles:
            return False
    return True


def seated_legally(roles, believes=None):
    """Does every character sit where the setup says it must?

    The bag decides *which* characters are dealt; this decides whether
    they could have been dealt to *these seats*. The Marionette is the
    one that asks: it neighbours the Demon. The catalogue holds the rule
    (`beside`), so the next character with a seating rule is a line
    there rather than a new branch here.

    Asked of the finished deal, not seat by seat during the search. The
    neighbour may be the last seat filled, and a check halfway through
    would have to know which seats are still empty.
    """
    n = len(roles)
    # No Demon dealt is Lil' Monsta's bag: a Marionette sits beside the
    # first babysitter instead, which the Minions choose on the first
    # night (its jinx, solver.the_minions_choose_a_babysitter).
    no_demon = not any(TEAM[r] == "demon" for r in roles)
    for seat, role in enumerate(roles):
        team = CHARACTERS[role].beside
        if team == "demon" and no_demon:
            continue
        if team and not any(TEAM[roles[(seat + step) % n]] == team
                            for step in (-1, 1)):
            return False
        if CHARACTERS[role].lines_up and not in_a_line(roles, seat):
            return False
        # "[+the King]": a Choirboy dealt means a King dealt (10.10.2026).
        # A Summoner's Marionette-to-be may hold it until the Demon comes
        # (Stelle 73, 22.10.2026).
        for other in CHARACTERS[role].brings:
            if other not in roles and not (
                    believes is not None and "Summoner" in roles
                    and "Marionette" in roles
                    and believes[roles.index("Marionette")] == other):
                return False
    return True


def iter_worlds(n_players, claims, certainties=None, allow_good_lies=False,
                forced=None, wakes=None, script=None, fabled=()):
    """Yield every legal role assignment for n seats.

    claims:      {seat: "RoleName"}; missing entries = no claim.
    certainties: {seat: "self" | "confirmed" | "hiding" | "unsure"}.
    forced:      {seat: set of roles} that a witnessed event pins down.
    wakes:       {seat: what they said about waking}; see roles.WAKE.
    """
    for target, cands, order, required in _branches(
            n_players, claims, certainties, allow_good_lies, forced, wakes,
            script or DEFAULT, fabled or ()):

        n = n_players
        roles = [None] * n
        believes = [None] * n
        used = set()
        taken = {}
        count = {"townsfolk": 0, "outsider": 0, "minion": 0, "demon": 0}

        def rec(k):
            if k == len(order):
                if not required <= used:
                    return                # this bag's characters never landed
                if not seated_legally(roles, believes) \
                        or not believes_legally(roles, believes):
                    return                # dealt to seats it cannot sit in
                yield World(tuple(roles), tuple(believes))
                return
            i = order[k]
            for role, belief in _viable(cands[i], used, count, target,
                                        taken):
                _take(role, used, taken)
                if belief is not None:
                    _take(belief, used, taken)
                count[TEAM[role]] += 1
                roles[i], believes[i] = role, belief

                yield from rec(k + 1)

                roles[i], believes[i] = None, None
                count[TEAM[role]] -= 1
                _give_back(role, used, taken)
                if belief is not None:
                    _give_back(belief, used, taken)

        yield from rec(0)


def dive(setup, n_players, rng):
    """One random walk from the top of the search to a finished world.

    Returns (world, how many worlds it stands for), or None if the walk
    painted itself into a corner.

    The choice at each seat is deliberately not uniform. A seat claiming a
    Townsfolk typically offers one honest option against five evil ones,
    so tossing a fair coin over them makes a seat evil five times too
    often — the walk lands in a thin corner of the tree and the weight
    needed to correct it explodes. Instead each team is picked roughly in
    proportion to how many of its slots are still unfilled, which is what
    the finished world will actually look like. The weight then divides by
    the probability the walk actually used, so the estimate stays
    unbiased either way; matching the shape only makes it steadier.
    """
    target, cands, order, required, look = setup
    roles = [None] * n_players
    believes = [None] * n_players
    used = set()
    taken = {}
    count = {"townsfolk": 0, "outsider": 0, "minion": 0, "demon": 0}
    stands_for = 1.0

    for k, i in enumerate(order):
        options = _prune(_viable(cands[i], used, count, target, taken),
                         count, target, look, order, k + 1, used)

        # A bag is only that bag if its characters actually land in it.
        # When this is the last seat that could take one, it must.
        for role in required - used:
            later = any(role in (r for r, _b in cands[order[j]])
                        for j in range(k + 1, len(order)))
            if not later:
                options = [o for o in options if o[0] == role]

        if not options:
            return None

        per_team = {}
        for role, _b in options:
            team = TEAM[role]
            per_team[team] = per_team.get(team, 0) + 1
        shares = [(target[TEAM[r]] - count[TEAM[r]]) / per_team[TEAM[r]]
                  for r, _b in options]
        pool = sum(shares)

        cut = rng.random() * pool
        running = 0.0
        chosen = len(options) - 1
        for idx, share in enumerate(shares):
            running += share
            if running >= cut:
                chosen = idx
                break
        role, belief = options[chosen]
        stands_for *= pool / shares[chosen]

        _take(role, used, taken)
        if belief is not None:
            _take(belief, used, taken)
        count[TEAM[role]] += 1
        roles[i], believes[i] = role, belief

    if not required <= used:
        return None
    # A dead end like any other: counting it as a walk that found nothing
    # keeps the estimate unbiased for the worlds that do sit legally.
    if not seated_legally(roles, believes) \
            or not believes_legally(roles, believes):
        return None
    return World(tuple(roles), tuple(believes)), stands_for


def _sampling_setups(*args):
    """Branches with the look-ahead tables attached, for the sampler.

    Bags that cannot produce a single world are dropped here rather than
    wasting walks on them. With every seat claiming a Townsfolk, for
    instance, the Baron's bag wants four Outsiders and the table can only
    reach one — there is nothing down there to find.
    """
    out = []
    for target, cands, order, required in _branches(*args):
        look = _lookahead(cands, order)
        empty = dict.fromkeys(target, 0)
        if _fits_ahead(empty, target, look, order, 0, set()):
            out.append((target, cands, order, required, look))
    return out


def sample_worlds(n_players, claims, certainties=None, allow_good_lies=False,
                  forced=None, wakes=None, dives=20000, rng=None, script=None,
                  fabled=()):
    """Yield (world, weight) for `dives` random walks.

    A walk that hits a dead end yields (None, 0.0). Those still count as
    dives — dropping them would quietly bias everything upwards.
    """
    rng = rng or random.Random()
    setups = _sampling_setups(n_players, claims, certainties, allow_good_lies,
                              forced, wakes, script or DEFAULT, fabled or ())
    if not setups:
        return
    for _ in range(dives):
        setup = setups[rng.randrange(len(setups))]
        got = dive(setup, n_players, rng)
        if got is None:
            yield None, 0.0
        else:
            world, stands_for = got
            yield world, stands_for * len(setups)


def enumerate_worlds(n_players, claims, certainties=None,
                     allow_good_lies=False, max_worlds=300_000, forced=None,
                     wakes=None, script=None, fabled=()):
    """List form of iter_worlds, stopping at max_worlds."""
    out = []
    for w in iter_worlds(n_players, claims, certainties, allow_good_lies,
                         forced, wakes, script, fabled):
        out.append(w)
        if len(out) >= max_worlds:
            break
    return out


# ----------------------------------------------------------------------
# Every row read at its character's turn (Hatter stage 3b, 23.10.2026)
# ----------------------------------------------------------------------
# A row is what one character's turn produced: the Empath's count at the
# Empath's slot, the Snake Charmer's choice at the Snake Charmer's. While
# the row is judged, its own night is read at that slot (`READ_AT`), so a
# change later the same night — a Pit-Hag's, a Barber's swap — no longer
# reaches back into it (open item 36, E Weg 1). A row whose character
# does not wake that night reads the whole night, as every row did before.
#
# Done once here for every kind of row rather than in each `holds`: the
# rows ask the board through `role_at`, `alignment_at`, `demon_at` and
# `find_at` with their night's phase, and seventy-six of them doing it by
# hand is seventy-six places to forget.

_ROW_METHODS = ("holds", "is_true", "is_true_with", "leaned_on", "hard",
                "weighed", "must_have_failed", "instead")


def _row_slot(row):
    role = getattr(row, "source_role", None)
    night = getattr(row, "night", None)
    if role is None or not isinstance(night, int):
        return None
    first = CHARACTERS[role].first_night if role in CHARACTERS else 0
    other = CHARACTERS[role].other_night if role in CHARACTERS else 0
    slot = first if night == 1 else other
    return (f"N{night}", first, other) if slot else None


def _at_its_turn(fn):
    def at_its_turn(self, *args, **kwargs):
        got = _row_slot(self)
        if got is None:
            return fn(self, *args, **kwargs)
        was = READ_AT[0]
        READ_AT[0] = got
        try:
            return fn(self, *args, **kwargs)
        finally:
            READ_AT[0] = was
    at_its_turn.__name__ = fn.__name__
    at_its_turn.__doc__ = fn.__doc__
    at_its_turn.__wrapped__ = fn
    return at_its_turn


def _read_rows_at_their_turn():
    from . import info as _info
    seen = set()
    todo = [_info.Info]
    while todo:
        cls = todo.pop()
        if cls in seen:
            continue
        seen.add(cls)
        todo.extend(cls.__subclasses__())
        for name in _ROW_METHODS:
            fn = cls.__dict__.get(name)
            if fn is not None and callable(fn) \
                    and not hasattr(fn, "__wrapped__"):
                setattr(cls, name, _at_its_turn(fn))


_read_rows_at_their_turn()
