"""Step 2 of the solver: what do players say - and does it fit the world?

Core idea: a piece of information constrains a world ONLY if that player
truly holds the role that produces it. If they are evil (lying) or the
Drunk, any statement is possible. Poisoning is not enumerated; it is
only checked for feasibility at the end (see solver.py).
"""

from dataclasses import dataclass, field
from itertools import product
from typing import Optional

from .catalogue import CHARACTERS
from .roles import (TOWNSFOLK, OUTSIDERS, MINIONS, DEMONS, TEAM, is_evil,
                    evil_registrations, is_really_role,
                    registers_as_role)


# --------------------------------------------------------------------------
# Game state
# --------------------------------------------------------------------------

def _as_phases(value):
    """One phase or several, always returned as a tuple."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


_PHASE_INDEX = {}


def phase_index(phase):
    """'N1' -> 0, 'D1' -> 1, 'N2' -> 2, ...

    Only two kinds of moment: 'N' for a night and 'D' for a day. Whether
    a daytime death was an execution is recorded separately, because the
    two facts are independent — a player can be executed and live, and a
    player can die in the day without being executed.

    'E' is accepted for old saved games, which used it to mean an
    execution death.
    """
    got = _PHASE_INDEX.get(phase)
    if got is None:
        kind, num = phase[0].upper(), int(phase[1:])
        got = (num - 1) * 2 + (0 if kind == "N" else 1)
        _PHASE_INDEX[phase] = got
    return got


@dataclass
class GameState:
    n_players: int
    claims: dict = field(default_factory=dict)   # {index: "Role"}
    # Which characters were in the bag. Everything the search does is
    # relative to this; the default is only the first script implemented.
    script: object = None
    # Which Fabled the Storyteller put on the table. Public knowledge, so
    # this is told to the solver rather than discovered by it — what a
    # Fabled *did* stays hidden, which is the point of the Sentinel.
    fabled: tuple = ()
    # {index: "self" | "confirmed"} - see worlds._candidates
    certainties: dict = field(default_factory=dict)
    # {index: -3..+3} social read; negative reads good, positive reads evil
    reads: dict = field(default_factory=dict)
    # Seats somebody thinks may have been handed the wrong token. A
    # suspicion about their *information*, not about their side.
    suspects: dict = field(default_factory=dict)
    # {index: "never"|"first"|"every"|"other"|"sometimes"} - soft claims
    # about waking at night; see roles.WAKE
    wakes: dict = field(default_factory=dict)
    # {seat: ("N2",) or ("D1", "N4")} — every moment they died. A tuple,
    # because death stopped being permanent: a Professor can raise a
    # Townsfolk, and whoever it raised can be killed again.
    deaths: dict = field(default_factory=dict)
    # {seat: ("N3",)} — every moment they came back. Nothing about this
    # assumes the character doing it is good; plenty of scripts raise the
    # dead for reasons of their own.
    resurrections: dict = field(default_factory=dict)
    # {day: seat} - who the town executed that day, whether or not it
    # killed them. Kept apart from `deaths` because the two come apart:
    # a Zombuul survives its first execution, and a Devil's Advocate can
    # save somebody from theirs. The day still ends either way.
    executions: dict = field(default_factory=dict)
    # Nights on which nobody died at all. Strong information: something
    # has to have stopped the kill.
    quiet_nights: set = field(default_factory=set)
    # Days the town got through without executing anybody. No world is
    # ruled out by it — the solver already assumes no execution unless
    # one is recorded — but it says the game *reached* that day, which
    # bounds how long a lineage can run and how far a Mastermind's extra
    # day can stretch.
    days_done: set = field(default_factory=set)
    # Who voted, and who nominated, on each day. Nothing else on the
    # board needs either — they exist because the Flowergirl and the Town
    # Crier ask about them, and a day is where they belong rather than a
    # seat, since "did the Demon vote today" is a question about a day.
    votes: dict = field(default_factory=dict)
    nominations: dict = field(default_factory=dict)
    # Two things the table sees plainly, each of which gives away a
    # character nobody chose to reveal. A seat dropping dead as it
    # nominates is a Witch; a seat executed for breaking ceremadness is a
    # Cerenovus. Neither needs the hidden choice modelled — recording
    # what happened does the work, which is the only way the solver can
    # get at either of them.
    witch_deaths: set = field(default_factory=set)      # {day: seat}
    madness_executions: set = field(default_factory=set)
    infos: list = field(default_factory=list)
    names: list = field(default_factory=list)    # optional, display only

    def alive_at(self, phase):
        """Who was still standing at this moment.

        Worked out from the whole run of a seat's life rather than from
        one death, because a seat can die, be raised and die again.
        Cached: the impairment plan asks this for every night of every
        world, and the answer does not change while a board is solved.
        """
        cached = self._alive_cache.get(phase)
        if cached is not None:
            return cached
        pi = phase_index(phase)
        alive = [p for p in range(self.n_players) if self._alive(p, pi)]
        self._alive_cache[phase] = alive
        return alive

    def _alive(self, seat, index):
        """Standing at this point, given everything that happened to them.

        A death takes effect *after* the moment it happened: somebody
        killed on night two was alive during night two, which is what
        every check that asks "who was around then" means. A return takes
        effect *at* its moment, because that is when they are back.
        """
        standing = True
        for at, living in self._life.get(seat, ()):
            if living:
                if at <= index:
                    standing = True
            elif at < index:
                standing = False
        return standing

    def died_at(self, seat):
        """Every moment this seat died. Usually one, sometimes none."""
        return self.deaths.get(seat, ())

    def death_phases(self):
        """(seat, phase) for every death on the record."""
        for seat, phases in (self.deaths or {}).items():
            for phase in phases:
                yield seat, phase

    def __post_init__(self):
        self._alive_cache = {}
        self._alive_set_cache = {}
        if self.script is None:
            from .scripts import DEFAULT
            self.script = DEFAULT

        # Two tidying jobs.
        #
        # A single phase is accepted wherever a tuple belongs, because one
        # death is what a seat usually has and writing `{2: "N3"}` is how
        # anybody would say it.
        #
        # And "executed on day n" written as a death is split apart:
        # `deaths[seat] = "E1"` is how most people describe it and how the
        # older saved games recorded it, but the two facts are separate.
        # The death goes in `deaths` as an ordinary day death and the
        # execution goes in `executions`, which is what lets a board say
        # somebody was executed and lived.
        moved = {}
        for seat, phases in (self.deaths or {}).items():
            out = []
            for phase in _as_phases(phases):
                if phase and phase[0].upper() == "E":
                    day = int(phase[1:])
                    out.append(f"D{day}")
                    self.executions.setdefault(day, seat)
                else:
                    out.append(phase)
            moved[seat] = tuple(out)
        self.deaths = moved
        self.resurrections = {seat: _as_phases(phases) for seat, phases
                              in (self.resurrections or {}).items()}

        # One run of events per seat, in order, so aliveness is a question
        # about a moment rather than about a single death.
        self._life = {}
        for seat in set(self.deaths) | set(self.resurrections):
            events = [(phase_index(p), False) for p in self.deaths.get(seat, ())]
            events += [(phase_index(p), True)
                       for p in self.resurrections.get(seat, ())]
            # A death and a return at the same moment reads as the return,
            # since that is the only order in which both could be true.
            self._life[seat] = tuple(sorted(events, key=lambda e: (e[0], e[1])))

    def executed_on(self, day):
        """Who the town executed that day, alive or dead afterwards."""
        return (self.executions or {}).get(day)

    def execution_death(self, day):
        """Who was executed that day *and* died of it.

        This is what the Undertaker learns from, and what the Saint's
        losing condition keys off. An execution somebody walked away from
        gives neither of them anything.
        """
        seat = self.executed_on(day)
        if seat is None:
            return None
        return seat if f"D{day}" in self.died_at(seat) else None

    def final_phase(self):
        """The latest moment the game has reached.

        What "evil" means for a seat depends on when you ask, so the
        report has to pick a moment. It picks now.
        """
        latest = "N1"
        for _seat, phase in self.death_phases():
            if phase_index(phase) > phase_index(latest):
                latest = phase
        for phases in (self.resurrections or {}).values():
            for phase in phases:
                if phase_index(phase) > phase_index(latest):
                    latest = phase
        for night in (self.quiet_nights or ()):
            if phase_index(f"N{night}") > phase_index(latest):
                latest = f"N{night}"
        # A day the town got through without executing anybody still
        # happened, and saying so is how the board records that the game
        # moved on.
        for day in (self.days_done or ()):
            if phase_index(f"D{day}") > phase_index(latest):
                latest = f"D{day}"
        for info in self.infos:
            phase = f"N{info.night}"
            if phase_index(phase) > phase_index(latest):
                latest = phase
        return latest

    def philosophies(self):
        """Which character each Philosopher took, and from when.

        {seat: (role, phase)}. Read off the ledger rather than the world,
        because it is a declared action: the table watched somebody claim
        it, and whether they really are the Philosopher is a question the
        world answers separately.
        """
        got = getattr(self, "_philosophies", None)
        if got is None:
            got = {}
            for info in self.infos:
                if getattr(info, "source_role", None) == "Philosopher" \
                        and getattr(info, "role", None):
                    got[info.player] = (info.role, f"N{info.night}")
            self._philosophies = got
        return got

    def alive_set(self, phase):
        """`alive_at` as a set, cached. Sources ask for it per night of
        every world, and building it each time is most of what the
        impairment plan costs."""
        cached = self._alive_set_cache.get(phase)
        if cached is None:
            cached = frozenset(self.alive_at(phase))
            self._alive_set_cache[phase] = cached
        return cached

    def label(self, i):
        if self.names and i < len(self.names):
            return f"{i}:{self.names[i]}"
        return str(i)


# --------------------------------------------------------------------------
# Information types
# --------------------------------------------------------------------------
# Every info knows: which night/day, who received it, and which role
# produced it.

def _misregistered(w, seat, phase, claimed):
    """Did this seat have to misregister to match what it was shown as?

    True only when it is *not* that character and could show as one.
    A seat that really is what it was called leaned on nothing.
    """
    if seat is None:
        return False
    actual = w.role_at(seat, phase)
    return actual != claimed and registers_as_role(actual, claimed)


@dataclass
class Info:
    night: int
    # The person who said this out loud, claiming it as their own info.
    player: int
    # How far you believe the reading itself, -3 to +3, separately from
    # whoever announced it. This is the piece that matters for readings
    # attributed to a role nobody has claimed, where there is no seat to
    # form an opinion about.
    trust: int = 0
    # Did the table later establish that this reading was *right*?
    #
    # Different from `trust`, which says "I believe this row is real" and
    # prices making it up. This says the content checked out — an
    # Undertaker whose reading matched what was later confirmed, a
    # Washerwoman whose pair turned out as described.
    #
    # Evidence rather than proof, and it accumulates: a seat right four
    # nights running is much harder to doubt than one right once. It
    # never reaches certainty, because a Spy reading the grimoire can
    # feed a Minion true information all game.
    #
    # The players tick it, between them. Nothing here can derive it —
    # the solver does not know what the table later agreed.
    confirmed: bool = False
    source_role = None

    # Is this row a *choice* the seat made, rather than information it
    # was told?
    #
    # A Vortox makes Townsfolk abilities yield false information — and a
    # choice is not information. Nobody told a Philosopher what it took;
    # it decided. Nobody told a Courtier which character to name, or a
    # Klutz where to point, or a Gambler what to guess.
    #
    # The distinction matters because the *consequences* still land: a
    # Philosopher that took the Town Crier gets the Town Crier's ability
    # and **that** reading is inverted; a Gambler that guesses wrong
    # still dies; a Snake Charmer that chose the Vortox still swaps
    # character and alignment with it. The choice is untouched, what
    # follows from it is not.
    #
    # Left as False here, so anything not saying otherwise is treated as
    # information — which is the safe direction: a reading wrongly
    # inverted shows up as an impossible board, and a choice wrongly
    # inverted shows up as nothing at all.
    is_a_choice = False

    def leaned_on(self, w, s, seat=None):
        """Seats this reading needed to *misregister* to hold.

        **A droisoned character cannot misregister.** A Storyteller may
        choose freely what a droisoned *information* role yields, because
        the information is arbitrary — but registration is a plain
        ability, and a plain ability simply does not function. A poisoned
        Recluse is a Recluse and shows as one.

        `holds` cannot decide this on its own, because whether a seat was
        droisoned is not known when it runs: droisoning is *chosen* as
        part of the explanation, by the impairment plan, which settles
        afterwards. So a row reports which seats it leaned on instead,
        and those seats are forbidden from being droisoned that night —
        the plan already understands "must not be impaired", and this is
        simply the first caller to use it for registration.

        Nothing by default. Only rows whose answer can turn on
        registration need say anything.
        """
        return ()

    def is_information(self, state):
        """Does a Vortox reach this row?

        **A Vortox falsifies information roles and nothing else.** Asking
        that character by character is how it was done for a long time,
        and it was got wrong twice — a Philosopher's choice was inverted
        when nothing had told it anything, and a Snake Charmer's swap was
        flipped so a charmer claimed to have swapped with a seat it never
        touched.

        So it is one question answered in one place. A row is information
        unless it is a *choice* the seat announced, or its content is
        kept rather than weighed.

        A character that changes who holds what — a Farmer making a new
        Farmer, a Pit-Hag creating somebody — yields no information at
        all, and a Vortox has nothing to falsify.
        """
        return not self.is_a_choice and self.weighed(state)

    def weighed(self, state):
        """Is this row's content actually checked?

        Nearly always. The exceptions are rows that are *kept* rather
        than solved — a Savant's pair, an Artist's question — and the
        Mathematician on a script whose droison sources are not all
        built.

        It matters because those rows answer `holds` with True by
        default, and under a Vortox "true" is a claim: it would mean the
        Vortox was not working. A row that says nothing must go on saying
        nothing.
        """
        return True

    def hard(self):
        """True if this is a fact about the world rather than a claim.

        A claim only binds when the speaker really holds that role - if
        they are evil or the Drunk, they can say anything. A hard fact
        binds in every world and cannot be excused by poison either.
        """
        return False

    def source_seat(self, state):
        """Whose information this actually is.

        Usually the speaker. But handing your information to someone else
        and letting them share it is ordinary play, so when the speaker
        claims a different role and exactly one seat claims the matching
        one, the information is attributed to that seat instead - the
        speaker is relaying. With nobody to attribute it to, it falls back
        to the speaker's own claim.
        """
        if state.claims.get(self.player) == self.source_role:
            return self.player
        # A Philosopher speaking a reading it gained is not relaying — it
        # is the source. Without this the row is handed to whoever claims
        # that character, which is somebody else entirely, and the
        # Philosopher's own information ends up judged against a seat
        # that never said it.
        took = state.philosophies().get(self.player)
        if took is not None and took[0] == self.source_role \
                and phase_index(f"N{self.night}") >= phase_index(took[1]):
            return self.player
        holders = [p for p, role in state.claims.items()
                   if role == self.source_role]
        if len(holders) == 1:
            return holders[0]
        # Nobody has claimed it. That does not make the information false -
        # there may well be an Empath nobody has heard from yet. Returning
        # None means "whoever turns out to hold this role", so the solver
        # fits the statement onto the unclaimed seats instead of the
        # speaker.
        return None

    def holds(self, world, state, red_herring, seat=None):
        """Is this reading true in that world?

        `seat` is who the information actually belongs to, which is not
        always the speaker - somebody may be relaying it. Checks that
        depend on where the character sits must use it.
        """
        raise NotImplementedError


@dataclass
class Washerwoman(Info):
    a: int = 0
    b: int = 0
    role: str = ""
    source_role = "Washerwoman"

    def holds(self, w, s, rh, seat=None):
        # Read at the night this was heard rather than at night one.
        # For a character dealt at the start those are the same; for one
        # a Pit-Hag made on night four they are not, and "your first
        # night" means the first night *of this character*.
        phase = f"N{self.night}"
        return (registers_as_role(w.role_at(self.a, phase), self.role) or
                registers_as_role(w.role_at(self.b, phase), self.role))

    def is_true(self, w, s, seat=None):
        """Whether one of the pair really *is* that character.

        Legality allows registration; truth does not. A Spy shown as the
        Slayer is still a Spy, so the reading is false — and a Vortox may
        produce it freely, because falsifying is exactly its job.
        """
        phase = f"N{self.night}"
        return any(who is not None and w.role_at(who, phase) == self.role
                   for who in (self.a, self.b))

    def leaned_on(self, w, s, seat=None):
        # Nothing, if one of the pair really is that character: either
        # could then have been droisoned. Only a match that *depends* on
        # registration needs the seat to have been working.
        phase = f"N{self.night}"
        for who in (self.a, self.b):
            if who is not None and w.role_at(who, phase) == self.role:
                return ()
        return tuple(who for who in (self.a, self.b)
                     if _misregistered(w, who, phase, self.role))

    def is_true(self, w, s, seat=None):
        """Whether one of the pair really *is* that character.

        Legality allows registration; truth does not. A Spy shown as the
        Slayer is still a Spy, so the reading is false — and a Vortox may
        produce it freely.
        """
        phase = f"N{self.night}"
        return any(who is not None and w.role_at(who, phase) == self.role
                   for who in (self.a, self.b))

    def leaned_on(self, w, s, seat=None):
        # If one of the pair really is that character, nothing was leaned
        # on and either could have been droisoned. Only when the match
        # *depends* on registration does the seat have to have been
        # working.
        phase = f"N{self.night}"
        for who in (self.a, self.b):
            if who is not None and w.role_at(who, phase) == self.role:
                return ()
        return tuple(who for who in (self.a, self.b)
                     if _misregistered(w, who, phase, self.role))


@dataclass
class Librarian(Info):
    a: Optional[int] = None
    b: Optional[int] = None
    role: str = ""
    source_role = "Librarian"

    def holds(self, w, s, rh, seat=None):
        if self.a is None:          # "no Outsiders in play"
            # Not "there are no Outsiders" — "none of them showed as one".
            # A Recluse registers as a Minion or the Demon whenever the
            # Storyteller likes, so a Librarian can honestly be told
            # nobody with a Recluse sitting right there. Demanding the
            # true team threw those worlds away, which is the wrong
            # direction to be wrong in: it ruled out a game that happens.
            return all(_can_show_as_something_else(
                w.role_at(p, f"N{self.night}")) for p in range(len(w.roles)))
        # Read at the night this was heard rather than at night one.
        # For a character dealt at the start those are the same; for one
        # a Pit-Hag made on night four they are not, and "your first
        # night" means the first night *of this character*.
        phase = f"N{self.night}"
        return (registers_as_role(w.role_at(self.a, phase), self.role) or
                registers_as_role(w.role_at(self.b, phase), self.role))

    def is_true(self, w, s, seat=None):
        """Whether one of the pair really *is* that character.

        Legality allows registration; truth does not. A Spy shown as the
        Slayer is still a Spy, so the reading is false — and a Vortox may
        produce it freely, because falsifying is exactly its job.
        """
        phase = f"N{self.night}"
        return any(who is not None and w.role_at(who, phase) == self.role
                   for who in (self.a, self.b))

    def leaned_on(self, w, s, seat=None):
        # Nothing, if one of the pair really is that character: either
        # could then have been droisoned. Only a match that *depends* on
        # registration needs the seat to have been working.
        phase = f"N{self.night}"
        for who in (self.a, self.b):
            if who is not None and w.role_at(who, phase) == self.role:
                return ()
        return tuple(who for who in (self.a, self.b)
                     if _misregistered(w, who, phase, self.role))

    def is_true(self, w, s, seat=None):
        """Whether one of the pair really *is* that character.

        Legality allows registration; truth does not. A Spy shown as the
        Slayer is still a Spy, so the reading is false — and a Vortox may
        produce it freely.
        """
        phase = f"N{self.night}"
        return any(who is not None and w.role_at(who, phase) == self.role
                   for who in (self.a, self.b))

    def leaned_on(self, w, s, seat=None):
        # If one of the pair really is that character, nothing was leaned
        # on and either could have been droisoned. Only when the match
        # *depends* on registration does the seat have to have been
        # working.
        phase = f"N{self.night}"
        for who in (self.a, self.b):
            if who is not None and w.role_at(who, phase) == self.role:
                return ()
        return tuple(who for who in (self.a, self.b)
                     if _misregistered(w, who, phase, self.role))


@dataclass
class Investigator(Info):
    a: int = 0
    b: int = 0
    role: str = ""
    source_role = "Investigator"

    def holds(self, w, s, rh, seat=None):
        # Read at the night this was heard rather than at night one.
        # For a character dealt at the start those are the same; for one
        # a Pit-Hag made on night four they are not, and "your first
        # night" means the first night *of this character*.
        phase = f"N{self.night}"
        return (registers_as_role(w.role_at(self.a, phase), self.role) or
                registers_as_role(w.role_at(self.b, phase), self.role))

    def is_true(self, w, s, seat=None):
        """Whether one of the pair really *is* that character.

        Legality allows registration; truth does not. A Spy shown as the
        Slayer is still a Spy, so the reading is false — and a Vortox may
        produce it freely.
        """
        phase = f"N{self.night}"
        return any(who is not None and w.role_at(who, phase) == self.role
                   for who in (self.a, self.b))

    def leaned_on(self, w, s, seat=None):
        # If one of the pair really is that character, nothing was leaned
        # on and either could have been droisoned. Only when the match
        # *depends* on registration does the seat have to have been
        # working.
        phase = f"N{self.night}"
        for who in (self.a, self.b):
            if who is not None and w.role_at(who, phase) == self.role:
                return ()
        return tuple(who for who in (self.a, self.b)
                     if _misregistered(w, who, phase, self.role))


def _can_show_as_something_else(role):
    """Could this character avoid being counted as an Outsider?

    True for everybody who is not one, and for an Outsider that may
    register as another team. The Butler, the Drunk and the Saint have no
    such option, so one of those in play means the Librarian is shown
    somebody.
    """
    if TEAM[role] != "outsider":
        return True
    return any(team != "outsider" for team in CHARACTERS[role].registers)


def _possible_evil_counts(world, players, phase):
    """All values "number of evil among these players" could take.

    Asked of a moment, because on scripts where a player can change
    alignment the answer is not the same all game.

    **These have no `leaned_on`, deliberately.** A count reading holds if
    the number it was given is anywhere in this range, and the range is
    built from every combination of how everybody could register — so
    there is no single seat the answer depended on. A Chef told "one"
    beside two Recluses leaned on *one of them*, and which is not a
    question the reading can answer.

    Handling it properly would mean carrying a set of alternative
    explanations rather than one, and forbidding droisoning in whichever
    the plan chose. That is a real piece of work and it is not this one.
    Until then a count reading is permissive here: it can still hold with
    a droisoned Recluse in the middle of it, which is wrong and is
    written down rather than half-fixed.
    """
    options = [evil_registrations(world.role_at(p, phase),
                                  world.alignment_at(p, phase))
               for p in players]
    return {sum(combo) for combo in product(*options)}


@dataclass
class Chef(Info):
    count: int = 0
    source_role = "Chef"

    def holds(self, w, s, rh, seat=None):
        n = len(w.roles)
        phase = f"N{self.night}"
        options = [evil_registrations(w.role_at(p, phase),
                                      w.alignment_at(p, phase))
                   for p in range(n)]
        possible = set()
        for combo in product(*options):
            pairs = sum(1 for i in range(n)
                        if combo[i] and combo[(i + 1) % n])
            possible.add(pairs)
        return self.count in possible


def _living_neighbours(state, night, p):
    """The nearest living seat each way, as the Empath sees it.

    In Trouble Brewing the Demon kills before the Empath wakes, so
    tonight's victim is already gone and the count reads past them.
    """
    phase = f"N{night}"
    alive = [q for q in state.alive_at(phase)
             if phase not in state.died_at(q)]
    if p not in alive or len(alive) < 3:
        return [x for x in alive if x != p]
    idx = alive.index(p)
    return [alive[(idx - 1) % len(alive)], alive[(idx + 1) % len(alive)]]


@dataclass
class Empath(Info):
    count: int = 0
    source_role = "Empath"

    def holds(self, w, s, rh, seat=None):
        who = self.player if seat is None else seat
        # Killed before they could wake: there is no reading to check.
        if f"N{self.night}" in s.died_at(who):
            return True
        nb = _living_neighbours(s, self.night, who)
        return self.count in _possible_evil_counts(w, nb, f"N{self.night}")


@dataclass
class FortuneTeller(Info):
    a: int = 0
    b: int = 0
    yes: bool = False
    source_role = "FortuneTeller"

    def holds(self, w, s, rh, seat=None):
        pair = (self.a, self.b)
        phase = f"N{self.night}"
        # Looking for the Demon specifically, not for evil — so a Goon
        # that has turned is nothing to it.
        hard_demon = w.demon_at(phase) in pair
        recluse = any(w.role_at(x, phase) == "Recluse" for x in pair)
        herring = rh in pair
        if self.yes:
            return hard_demon or recluse or herring
        # A "no" means: no actual Demon and not the red herring.
        # The Recluse MAY register as good, so it does not interfere.
        return (not hard_demon) and (not herring)


@dataclass
class Undertaker(Info):
    target: int = 0
    role: str = ""
    source_role = "Undertaker"

    def holds(self, w, s, rh, seat=None):
        # Only an execution that killed somebody gives the Undertaker
        # anything, and the character they held when it happened is not
        # the character they were dealt if the Demon changed hands.
        day = self.night - 1
        if s.execution_death(day) != self.target:
            return False
        return registers_as_role(w.role_at(self.target, f"D{day}"), self.role)

    def is_true(self, w, s, seat=None):
        """Whether the executed seat really was that character."""
        return w.role_at(self.target, f"D{self.night - 1}") == self.role

    def leaned_on(self, w, s, seat=None):
        # Read at the day of the execution, which is when the seat had to
        # be showing as what the Undertaker was told.
        day = self.night - 1
        if _misregistered(w, self.target, f"D{day}", self.role):
            return (self.target,)
        return ()


@dataclass
class Ravenkeeper(Info):
    target: int = 0
    role: str = ""
    source_role = "Ravenkeeper"

    def holds(self, w, s, rh, seat=None):
        return registers_as_role(w.role_at(self.target, f"N{self.night}"),
                                 self.role)

    def is_true(self, w, s, seat=None):
        """Whether that seat really was that character."""
        return w.role_at(self.target, f"N{self.night}") == self.role

    def leaned_on(self, w, s, seat=None):
        phase = f"N{self.night}"
        if _misregistered(w, self.target, phase, self.role):
            return (self.target,)
        return ()


def _registers_townsfolk(role):
    return TEAM[role] == "townsfolk" or role == "Spy"


@dataclass
class GrandmotherInfo(Info):
    """Shown a good player and the character they hold.

    That seat is the grandchild from then on — a token the Storyteller
    puts down, not a character anybody holds. Whether the reading was
    true or invented, the token goes on the seat she was shown, which is
    why the grandchild is read off this row rather than off the world.
    """

    target: int = 0
    role: str = ""
    source_role = "Grandmother"

    def holds(self, w, s, rh, seat=None):
        shown = w.role_at(self.target, "N1")
        if not registers_as_role(shown, self.role):
            return False
        # She is shown a *good* player, and the Spy can be one of those.
        return not w.evil_at(self.target, "N1") or shown == "Spy"


def _possible_impairment_counts(world, state, night):
    """How many seats could have been impaired on this night.

    **And how many abilities went wrong without being impaired.** Those
    are different things, and the Acrobat is what forced the distinction:
    an Acrobat whose pick was droisoned should die, and a Tea Lady beside
    it stops that. Nothing was poisoned — the ability was *prevented* —
    and by the rules a prevented ability is one that went wrong, so a
    Mathematician sees it.

    Counted as a widening of the top of the range rather than a
    certainty, because whether the Acrobat would have died depends on
    where the night's droisoning landed, which is settled later.


    A range rather than a number, because the solver never decides where
    a Poisoner went unless something forces it. What it does know is the
    shape: whoever is *always* impaired — anybody holding somebody else's
    token, or a whole table a Minstrel has silenced — plus at most one
    seat per source that has to land somewhere.

    The bottom of the range is the always-impaired on their own, which
    assumes every source landed on somebody already impaired. The top is
    those plus every source landing somewhere fresh.

    Returned as a pair, since every count between the two is reachable:
    a source that can hit a fresh seat can also hit one already taken.
    """
    from .impairment import sources_on

    always, movable = set(), []
    for source in sources_on(world, state, night):
        # Free *and* reaching everybody it touches — a Drunk holding
        # somebody else's token, a Minstrel silencing the table. Those
        # have capacity enough for their whole reach and there is nothing
        # to choose.
        #
        # A free source that still has to pick is a different thing: a
        # Vigormortis poisons *one* of the two Townsfolk beside a dead
        # Minion and the Storyteller chooses which. Counting its whole
        # reach as certainly impaired said two where the answer was one —
        # and worse, a capacity of one against a reach of two came out as
        # a range of (0, 0), because it went into `always` and `always`
        # was then compared against nothing.
        if source.free_for_everyone() and source.capacity >= len(source.seats):
            always |= set(source.seats)
        else:
            movable.append(source)

    most = len(always)
    for source in movable:
        most += min(source.capacity, len(set(source.seats) - always))
    return len(always), min(most, state.n_players)


def _could_be_minion(world, seat, phase):
    """Could this seat have shown as a Minion, if the Storyteller liked?"""
    return (world.team_at(seat, phase) == "minion"
            or "minion" in CHARACTERS[world.role_at(seat, phase)].registers)


def _must_be_minion(world, seat, phase):
    """Is there no way for this seat to have shown as anything else?

    A Spy is a Minion that registers as good, so it can nominate without
    the Town Crier hearing a thing. Nobody else on these scripts can.
    """
    if world.team_at(seat, phase) != "minion":
        return False
    return not any(t != "minion"
                   for t in CHARACTERS[world.role_at(seat, phase)].registers)


@dataclass
class FlowergirlInfo(Info):
    """Whether the Demon voted during the day just gone.

    Asked on the night after, so a reading on night three is about day
    two. Read off the Demon at that day rather than off the deal, because
    after a handover the question is about whoever held it then.
    """

    voted: bool = False
    source_role = "Flowergirl"

    def holds(self, w, s, rh, seat=None):
        day = self.night - 1
        if day < 1:
            return False              # there was no day before the first
        phase = f"D{day}"
        demon = w.demon_at(phase)
        if demon is None:
            return not self.voted     # no Demon, so it voted for nothing
        return (demon in (s.votes or {}).get(day, ())) == self.voted


@dataclass
class TownCrierInfo(Info):
    """Whether a Minion nominated during the day just gone.

    A "yes" needs only one nominator who could have shown as a Minion —
    the Storyteller chooses how anybody registers. A "no" is the harder
    claim: every nominator has to have been able to show as something
    else, which a Spy can and an ordinary Minion cannot.
    """

    nominated: bool = False
    source_role = "TownCrier"

    def holds(self, w, s, rh, seat=None):
        day = self.night - 1
        if day < 1:
            return False
        phase = f"D{day}"
        who = (s.nominations or {}).get(day, ())
        if self.nominated:
            return any(_could_be_minion(w, seat_, phase) for seat_ in who)
        return not any(_must_be_minion(w, seat_, phase) for seat_ in who)

    def is_true(self, w, s, seat=None):
        """Whether a Minion really nominated, as against could have.

        `holds` allows for registration both ways — a Spy may be shown as
        a Townsfolk, so "no Minion nominated" is a legal thing to say on
        a day one did. That is right for legality and wrong for truth,
        and a Vortox needs truth: it falsifies what an ability yields,
        and a reading made false by registration is already false.
        """
        day = self.night - 1
        if day < 1:
            return False
        phase = f"D{day}"
        who = (s.nominations or {}).get(day, ())
        really = any(TEAM[w.role_at(seat_, phase)] == "minion"
                     for seat_ in who)
        return really if self.nominated else not really


@dataclass
class OracleInfo(Info):
    """How many of the dead are evil.

    The Empath's question asked of the other half of the table. Counted
    by how a seat *registers*, so a dead Recluse may be shown either way
    and a dead Spy likewise — which is why this is a set of possible
    answers rather than one.
    """

    count: int = 0
    source_role = "Oracle"

    def holds(self, w, s, rh, seat=None):
        # Including whoever fell tonight.
        #
        # The Oracle reads at slot 59 and a Demon kills at 24, so by the
        # time it counts, tonight's victim is dead. `alive_set` reports
        # who was alive at the *start* of the night, which is a different
        # question — and the night order is what makes the difference
        # visible.
        phase = f"N{self.night}"
        dead = [p for p in range(len(w.roles))
                if p not in s.alive_set(phase) or phase in s.died_at(p)]
        return self.count in _possible_evil_counts(w, dead, phase)


@dataclass
class SeamstressInfo(Info):
    """Whether two players are the same side.

    Once per game, and strong: it splits the table in one reading. By
    registration, so a Recluse may read either way.
    """

    a: int = 0
    b: int = 0
    same: bool = False
    source_role = "Seamstress"

    def holds(self, w, s, rh, seat=None):
        phase = f"N{self.night}"
        # Every way the pair could have registered, and whether any of
        # them gives the answer that was heard.
        for first in evil_registrations(w.role_at(self.a, phase)):
            for second in evil_registrations(w.role_at(self.b, phase)):
                if (first == second) == self.same:
                    return True
        return False


@dataclass
class JugglerInfo(Info):
    """How many of the day's guesses were right.

    Guessed publicly during the day, answered that night, so the row sits
    on the night the number arrived and carries the guesses with it.

    "Its first day" means the first day of *this* Juggler — a Pit-Hag can
    make one on night three, and it juggles on day three. Nothing here
    enforces which day that was; the row says which night the number came
    on, and that is what gets checked.

    Guesses are matched by registration, so guessing "Recluse" at a seat
    the Storyteller was showing as a Minion can be wrong even though the
    seat really is the Recluse.
    """

    guesses: tuple = ()          # ((seat, role), ...)
    count: int = 0
    source_role = "Juggler"

    def holds(self, w, s, rh, seat=None):
        # Guessed during the day before, so read at that day.
        phase = f"D{self.night - 1}"
        right = 0
        for guess in self.guesses:
            # The page sends {player, role} and the tests hand over
            # [seat, role]. Both are read here rather than normalised on
            # the way in, so a row loaded from an old save still means
            # what it meant when it was written.
            #
            # The JavaScript learned this months ago and Python never
            # did, because nothing had ever fed it a page-shaped row —
            # the corpus is built from tuples. A simulator producing the
            # page's shape found it in one game.
            if isinstance(guess, dict):
                who, role = guess.get("player"), guess.get("role")
            else:
                who, role = guess
            if role and registers_as_role(w.role_at(int(who), phase), role):
                right += 1
        return right == self.count


@dataclass
class SavantInfo(Info):
    """Two statements, one true and one false — written down, not solved.

    A Savant's pair can be anything from "the Demon sits beside an
    Outsider" to "no Minion has yet chosen a man", and checking arbitrary
    claims about a board is a different program from this one. So the
    words are kept and shown, and the solver does not pretend to weigh
    them.

    It is not nothing, though: recording one is still somebody claiming
    to have visited the Storyteller, so a world with no Savant in it pays
    for that claim the same as any other.
    """

    first: str = ""
    second: str = ""
    source_role = "Savant"

    def weighed(self, state):
        return False

    def holds(self, w, s, rh, seat=None):
        return True                    # the words are kept, not weighed


@dataclass
class ArtistInfo(Info):
    """A yes-or-no question to the Storyteller — the question kept, the
    answer not solved.

    Same reason as the Savant: an Artist's question is whatever the
    player thought to ask, and it can be trivial or impossible. Recording
    it is still evidence there is an Artist.
    """

    question: str = ""
    answer: bool = False
    source_role = "Artist"

    def weighed(self, state):
        return False

    def holds(self, w, s, rh, seat=None):
        return True                    # kept, not weighed


@dataclass
class MoonchildChoice(Info):
    """Who the Moonchild pointed at on learning it died.

    Only a *good* target dies, so a seat that died the next day reads
    good and a seat that did not reads evil — which is the deduction, and
    it is the death rules that draw it rather than this row. What this
    does is say who was picked, since nobody else can know.
    """

    is_a_choice = True

    target: int = 0
    source_role = "Moonchild"

    def holds(self, w, s, rh, seat=None):
        return True                    # the consequence is a death, not a claim


@dataclass
class ExorcistChoice(Info):
    """Which character the Exorcist named.

    Naming the Demon stops it waking, so a quiet night is explained by
    it — and that makes the seat holding that character likelier to be
    the Demon. The row records the choice; the shield rule does the rest.
    """

    is_a_choice = True

    target: int = 0
    source_role = "Exorcist"

    def holds(self, w, s, rh, seat=None):
        return True


@dataclass
class InnkeeperChoice(Info):
    """The two the Innkeeper protected.

    Both are safe and one of them is drunk, and the Storyteller does not
    say which — so this narrows the drunk from the whole table to a pair,
    which is most of the value of confirming an Innkeeper at all.
    """

    is_a_choice = True

    a: int = 0
    b: int = 0
    source_role = "Innkeeper"

    def holds(self, w, s, rh, seat=None):
        return True


@dataclass
class SailorChoice(Info):
    """Who the Sailor chose.

    One of the two — the Sailor or whoever it chose — is drunk, and it is
    not told which. A Sailor executed and still standing was working, so
    in that case the drunk is the other one.
    """

    is_a_choice = True

    target: int = 0
    source_role = "Sailor"

    def holds(self, w, s, rh, seat=None):
        return True


@dataclass
class PitHagChoice(Info):
    """A seat that became a character it was not dealt.

    Recorded rather than searched for, and that is the whole design.
    A Pit-Hag acts on any night, on any seat, for no reason the table
    sees — enumerating that would multiply the search by seats times
    characters times nights, almost all of it stories nothing is asking
    for. But when it *is* known, it is known loudly: somebody says they
    changed, and from then on they are answering as something else.

    Three things follow from the rules and are checked here.

    The character has to have been **not in play**, and that is read off
    the true assignment rather than off the tokens: a Drunk holding the
    Fortune Teller token does not stop a real Fortune Teller being made,
    because there is no Fortune Teller — only somebody who thinks so.

    The **side does not move**. A Townsfolk turned into the Poisoner is a
    *good Poisoner*: good side, Poisoner ability. Rare, legal, and the
    reason `Change` has kept its two halves apart since the Ogre.

    And the new character starts **that night**, which is why the
    first-night readings were taught to read their own night rather than
    night one.
    """

    is_a_choice = True

    target: int = 0
    role: str = ""
    source_role = "PitHag"

    def holds(self, w, s, rh, seat=None):
        phase = f"N{self.night}"
        if w.role_at(self.target, phase) != self.role:
            return False              # the change did not take
        # It could only make something nobody already was. Checked on the
        # night before, since by this phase the change has landed.
        earlier = f"N{self.night - 1}" if self.night > 1 else "N1"
        if self.night > 1:
            for p in range(len(w.roles)):
                if p != self.target and w.role_at(p, earlier) == self.role:
                    return False
        return True


@dataclass
class SnakeCharmerChoice(Info):
    """Who the Snake Charmer pointed at, and whether anything happened.

    Recorded rather than guessed, because the outcome is visible: choose
    the Demon while working and you swap characters *and* sides with it,
    which the table finds out about immediately. Choose anybody else and
    nothing at all happens — and that is worth a lot, since it says that
    seat was not the Demon.

    A choice that did nothing is checked here. A choice that swapped is
    a change of character, so it is handled with the other handovers.
    """

    is_a_choice = True

    target: int = 0
    swapped: bool = False
    source_role = "SnakeCharmer"

    def holds(self, w, s, rh, seat=None):
        phase = f"N{self.night}"
        if self.swapped:
            # Checked *after* the swap, because that is the world being
            # scored: the seat pointed at is now holding the Snake
            # Charmer's character, and whoever pointed has the star.
            #
            # Saying nothing here instead would make a swap almost free —
            # it would hold in every world, including the ones where the
            # target was never the Demon and no swap could have happened.
            return w.role_at(self.target, f"D{self.night}") == "SnakeCharmer"
        # Nothing happened, so either they were not the Demon, or the
        # Snake Charmer was not working — and the second is somebody
        # else's excuse to pay for.
        return w.demon_at(phase) != self.target


@dataclass
class PhilosopherChoice(Info):
    """The night a Philosopher took somebody else's ability.

    It does not *become* that character — it keeps its own, and the
    chosen character may well be sitting elsewhere at the same time,
    which the world enumeration forbids two seats from doing. So this is
    an overlay: from this night on, that seat also acts as the chosen
    character.

    Which makes it the same machinery a Pit-Hag will need, from the other
    direction: a seat that started being something at a particular phase,
    where "first night" means the first night *since arriving*. A
    Philosopher taking the Juggler on night three juggles on day three
    and hears the number on night four.

    It may choose a character nobody holds, and it may choose an
    Outsider. A droisoned Philosopher still gains the ability — it simply
    malfunctions, like any other.
    """

    is_a_choice = True

    role: str = ""
    source_role = "Philosopher"

    def holds(self, w, s, rh, seat=None):
        # Choosing is the whole of it; there is no answer to be wrong
        # about. What it *gained* is checked wherever those readings are.
        return not is_evil(self.role)


@dataclass
class EvilTwinPair(Info):
    """Two seats that know each other, one good and one evil.

    Set on the first night, so that is where it is read. One of the pair
    is the Evil Twin itself and the other is good — which is a lot to
    learn from one row, and the reason it is worth recording even though
    the table only hears it if somebody says so.

    They usually claim the same character, and the point of that is that
    it is probably true for one of them. That is a prior rather than a
    rule, and the solver already prices a good player lying, so nothing
    extra is needed here.
    """

    a: int = 0
    b: int = 0
    source_role = "EvilTwin"

    def holds(self, w, s, rh, seat=None):
        first, second = w.role_at(self.a, "N1"), w.role_at(self.b, "N1")
        if "EvilTwin" not in (first, second):
            return False
        # One of each side, which follows from one of them being it — but
        # said outright, because a Pit-Hag could later make the other one
        # evil too and this row is about the first night.
        return is_evil(first) != is_evil(second)


@dataclass
class SageInfo(Info):
    """Killed by the Demon, it learns two players, one of them the killer.

    No misregistration here, which is unlike almost every other reading:
    it is shown *the Demon that killed it*, so a Recluse being shown as
    the Demon cannot fill the pair. Reading it the usual permissive way
    would be wrong by reflex.

    Read at the night it died, and off the Demon at that moment rather
    than off the deal — after a handover the killer is whoever held it
    then.
    """

    a: int = 0
    b: int = 0
    source_role = "Sage"

    def holds(self, w, s, rh, seat=None):
        phase = f"N{self.night}"
        demon = w.demon_at(phase)
        return demon is not None and demon in (self.a, self.b)


@dataclass
class NobleInfo(Info):
    """Three players, exactly one of whom is evil.

    **By registration, not by truth.** The Storyteller marks two players
    who register good and one who registers evil, so a Spy can sit among
    the two good ones and a Recluse can be the evil one. The wiki's own
    example has a Spy registering good, which leaves the Noble shown a
    set where *two* seats are really evil.

    So this asks whether there is any assignment of registrations under
    which exactly one of the three counts as evil — legal rather than
    true, the same distinction as everywhere else here.

    The Noble may be shown itself. Nothing forbids it, and being one of
    the two good ones is legal and useless.

    First night only. A Noble created mid-game learns on its own first
    night, which is the night it was created — not night one — and that
    is why the night is carried rather than assumed.
    """

    a: int = 0
    b: int = 0
    c: int = 0
    source_role = "Noble"

    def holds(self, w, s, rh, seat=None):
        phase = f"N{self.night}"
        options = [evil_registrations(w.role_at(p, phase))
                   for p in (self.a, self.b, self.c)]
        return any(x + y + z == 1
                   for x in options[0]
                   for y in options[1]
                   for z in options[2])


@dataclass
class BecameInfo(Info):
    """A seat was handed a character it was not dealt, and says so.

    **Provenance, not a claim.** "I am the Farmer" and "I became the
    Farmer on night two" are different statements, and the speaker knows
    which one they are making — they were dealt something else and woken
    to be given a new token.

    Kept whether or not it moves a number, because this tool is for
    playing with as much as for solving with: "seat 3 claimed Monk until
    day 2 and claims Farmer now" is worth having written down even when
    the arithmetic is unchanged.

    `was` is the character they claimed before. It is for reading, not
    for the search, which derives the dealt role itself — and it goes
    stale if the claim is edited afterwards. A stale value beats silently
    rewriting somebody's notes.

    Nothing here forces the claim to be true. An evil player may file one
    and be lying, and the search still weighs that.
    """

    # The game hands the token over; the Storyteller is not telling
    # anybody anything, so a Vortox does not touch it.
    is_a_choice = True

    role: str = ""
    was: str = ""

    def said_by(self):
        return self.player

    def holds(self, w, s, rh, seat=None):
        after = f"D{self.night}"
        return (w.role_at(self.player, after) == self.role
                and w.roles[self.player] != self.role)


@dataclass
class AlsaahirGuess(Info):
    """A public daytime guess at the whole evil team, and what happened.

    **Once per day, if you publicly guess which players are Minion(s) and
    which are Demon(s), good wins.**

    Not an alignment question. Minions and Demons count *even if they are
    good* — a Pit-Hag can make a good Minion and it still has to be
    named. And a dead seat still holds its character, so a Fang Gu that
    jumped leaves two Demons to name: the corpse and the seat that
    inherited.

    Every seat whose **current character** is a Minion or a Demon, alive
    or dead, and each named as the right one. The slightest offset fails.

    A guess that *won* is proof: nothing but a sober, healthy Alsaahir
    naming the team exactly can end a game, so it binds in every world.
    A guess that did nothing is the interesting one — it rules out that
    exact team, unless the Alsaahir was droisoned. Same shape as the
    Slayer's empty shot, and stronger, because it eliminates a whole
    configuration rather than one seat.
    """

    # A Vortox falsifies *information*, and nobody tells the Alsaahir
    # anything. This is a public statement whose consequence the table
    # watches — the same shape as a Slayer's shot or a Virgin's
    # nomination, where the Storyteller does not answer and the game
    # does.
    #
    # Without this the guess was being inverted, and explaining it needed
    # the Vortox droisoned on the night matching the day number.
    is_a_choice = True

    demons: frozenset = frozenset()
    minions: frozenset = frozenset()
    won: bool = False
    source_role = "Alsaahir"

    def settled(self):
        # A game that ended is not a story anybody can tell.
        return self.won

    def said_by(self):
        # Guessed in the open, so the guesser is never in doubt.
        return self.player

    def _exact(self, w, s, phase):
        """Does the guess name the current teams precisely?"""
        demons, minions = set(), set()
        for seat in range(len(w.roles)):
            role = w.role_at(seat, phase)
            if role is None:
                continue
            if TEAM[role] == "demon":
                demons.add(seat)
            elif TEAM[role] == "minion":
                minions.add(seat)
        return demons == set(self.demons) and minions == set(self.minions)

    def holds(self, w, s, rh, seat=None):
        phase = f"D{self.night}"
        if self.won:
            return (w.role_at(self.player, phase) == "Alsaahir"
                    and self._exact(w, s, phase))
        # A guess that did nothing is only evidence if a real Alsaahir
        # made it. Otherwise anybody may guess and be wrong, which says
        # nothing about the board.
        if w.role_at(self.player, phase) != "Alsaahir":
            return True
        return not self._exact(w, s, phase)


@dataclass
class BalloonistInfo(Info):
    """A player, shown for being a different character type than last night.

    **The Balloonist is never told the type** — only the player. So this
    row carries a seat and nothing else, and means nothing on its own:
    what it says is about the *pair* of consecutive nights.

    That makes it the first reading here whose truth is not a property of
    one night. Every other row can be checked against a world in
    isolation; this one needs the row before it.

    Registration applies, and it is what makes the chain interesting. A
    Recluse registers as a Minion or a Demon as well as being an
    Outsider, so the same seat can satisfy several links — the wiki notes
    a devious Storyteller could show the Recluse *every night*. The check
    is therefore not "do these two differ" but "is there an assignment of
    registrations under which every consecutive pair differs".

    Under a Vortox the reading must be false, and false here means the
    types were the **same** rather than different — which the wiki calls
    out as unique to this character.
    """

    target: int = 0
    source_role = "Balloonist"

    def holds(self, w, s, rh, seat=None):
        return True                       # the chain is judged elsewhere

    def weighed(self, state):
        # Kept rather than solved, for now. Judging it needs the whole
        # chain of Balloonist rows and a search over registrations, which
        # no single row can do — and a row that answers `True` in
        # isolation would look verified while checking nothing.
        return False


@dataclass
class AcrobatChoice(Info):
    """Who the Acrobat picked tonight.

    A **choice**, announced by the seat that made it — nobody told the
    Acrobat anything, so a Vortox has nothing to falsify here. What
    follows from the choice is another matter: if the seat picked is or
    *becomes* droisoned tonight, the Acrobat dies.

    That "becomes" is the whole difficulty. The check runs across the
    whole night, so a seat the Poisoner reaches after the Acrobat has
    chosen still kills it — which means this cannot be settled in night
    order. It is settled by the impairment plan instead, where an Acrobat
    death *requires* its target impaired and an Acrobat still standing
    *forbids* it.

    A dead player may be picked, and a dead droisoned one still kills:
    the Drunk is drunk whether or not it is breathing.
    """

    is_a_choice = True

    target: int = 0
    source_role = "Acrobat"

    def holds(self, w, s, rh, seat=None):
        return True                       # a declared choice, always


@dataclass
class KlutzChoice(Info):
    """Who the Klutz pointed at on dying.

    Good loses on the spot if that player is evil, so a board where the
    game carried on says they were not — while it was working. A
    droisoned Klutz points wherever it likes and nothing happens, which
    is the same shape as the Saint being executed while poisoned.
    """

    is_a_choice = True

    target: int = 0
    source_role = "Klutz"

    def holds(self, w, s, rh, seat=None):
        return not w.evil_at(self.target, f"N{self.night}")


@dataclass
class MathematicianInfo(Info):
    """How many abilities went wrong tonight.

    A reading about the solver's own workings rather than about the
    table, and the only one of its kind: every other row says something
    about who holds what, while this one says how much of the night
    misfired.

    Two things about it are approximations, and both are the permissive
    kind — they rule out numbers that cannot happen and never rule out a
    world that could.

    The first is that this checks the count is *reachable* rather than
    forcing the impairment plan to produce it. The plan posits a
    poisoning only when something would otherwise be false, so on a quiet
    board it has no opinion about where the Poisoner went; insisting it
    match a count would mean deciding that everywhere, for every world.

    The second is the span. "Since dawn" straddles the day before and
    tonight, while the solver's impairment spans run night-then-day. The
    night's own span is used, which is the larger part of what is being
    asked about.
    """

    count: int = 0
    source_role = "Mathematician"

    def weighed(self, state):
        # Silent on a script it cannot account for, and silence has to
        # survive a Vortox.
        return not any(c.impairs and not c.modelled
                       for c in state.script.characters())

    def holds(self, w, s, rh, seat=None):
        # It can only count what the solver knows how to break. A script
        # with characters still to be built may have any number of ways
        # to go wrong that nothing here has heard of, and ruling out a
        # number on that basis would throw away worlds that really
        # happened — the wrong direction to be wrong in.
        #
        # So on a script that is not fully modelled this constrains
        # nothing, and says so, rather than being confidently wrong.
        if any(c.impairs and not c.modelled for c in s.script.characters()):
            return True
        low, high = _possible_impairment_counts(w, s, self.night)
        return low <= self.count <= high


@dataclass
class ClockmakerInfo(Info):
    """How many steps from the Demon to its nearest Minion.

    Steps around the circle, the shorter way, and the nearest Minion when
    there is more than one — so a Minion sitting beside the Demon is 1.

    First night only, which is why the dead never come into it: nobody
    has died yet. Read off the true Demon and the true Minions rather
    than off how anybody registers, because it is the Storyteller
    counting seats rather than a character reading anybody.
    """

    count: int = 0
    source_role = "Clockmaker"

    def holds(self, w, s, rh, seat=None):
        phase = f"N{self.night}"
        demon = w.demon_at(phase)
        if demon is None:
            return False
        n = len(w.roles)
        steps = [min((m - demon) % n, (demon - m) % n)
                 for m in range(n) if w.team_at(m, phase) == "minion"]
        return bool(steps) and min(steps) == self.count


@dataclass
class DreamerInfo(Info):
    """One good character and one evil one, and the target is one of them.

    Two constraints rather than one, which is what makes it strong: the
    pair has to be one of each side, *and* the seat asked about has to
    actually be one of the two. In a world where the Dreamer is genuine
    that narrows a seat to a choice of two.

    The Storyteller picks which is true and which is the decoy, and never
    says — so this holds whichever way round it was.
    """

    target: int = 0
    good_role: str = ""
    evil_role: str = ""
    source_role = "Dreamer"

    def holds(self, w, s, rh, seat=None):
        # One of each side, or the reading is not a Dreamer's at all.
        if is_evil(self.good_role) or not is_evil(self.evil_role):
            return False
        phase = f"N{self.night}"
        actual = w.role_at(self.target, phase)
        # Legality on the way in, truth on the way out.
        #
        # A Dreamer is *shown* one of these, and misregistration decides
        # what may be shown — but whether the reading was true is whether
        # the seat is one of them. Asking only about registration made a
        # Spy shown as the Slayer read as **true**, and a Vortox board
        # containing one had no legal world at all.
        return (registers_as_role(actual, self.good_role)
                or registers_as_role(actual, self.evil_role))

    def is_true(self, w, s, seat=None):
        """Whether the reading is *true*, as against merely legal.

        A Vortox falsifies what an ability yields, and misregistration is
        the mechanic that lets a Storyteller give false information
        legally — a Spy shown as the Slayer is still a Spy, so that
        reading is already false and a Vortox may produce it.
        `holds` answers "could this have been said"; this answers "was it
        so", and the inversion needs the second.
        """
        phase = f"N{self.night}"
        actual = w.role_at(self.target, phase)
        return (is_really_role(actual, self.good_role)
                or is_really_role(actual, self.evil_role))


@dataclass
class ChambermaidInfo(Info):
    """Two living players, and how many of them woke tonight.

    For their *own* ability. A Demon woken because the Exorcist chose it
    was woken to be told something, not to do anything, and does not
    count — which is why the answer can be a range rather than a number.
    """

    a: int = 0
    b: int = 0
    count: int = 0
    source_role = "Chambermaid"

    def holds(self, w, s, rh, seat=None):
        from .waking import possible_counts
        return self.count in possible_counts(w, s, (self.a, self.b),
                                             self.night)


@dataclass
class GamblerGuess(Info):
    """Named a player and guessed their character. Wrong means they die.

    Which way this cuts depends on whether they are still standing, so
    the row reads the deaths rather than carrying the answer. A Gambler
    who died guessed wrong; a Gambler who lived guessed right — or was
    impaired, which the plan can pay for. A Gambler who never dies
    therefore tells you very little, which is the character working as
    designed.
    """

    is_a_choice = True

    target: int = 0
    role: str = ""
    source_role = "Gambler"

    def holds(self, w, s, rh, seat=None):
        who = self.player if seat is None else seat
        right = registers_as_role(w.role_at(self.target, f"N{self.night}"),
                                  self.role)
        return not right if f"N{self.night}" in s.died_at(who) else right


@dataclass
class CourtierChoice(Info):
    """Named a character, not a player. Once per game.

    Whoever holds it is drunk for three days and nights. Naming a
    character nobody holds still spends the ability and does nothing at
    all, which is why this row constrains nothing by itself — its whole
    effect is the drunkenness it licenses.
    """

    is_a_choice = True

    role: str = ""
    source_role = "Courtier"

    def holds(self, w, s, rh, seat=None):
        return True


@dataclass
class VirginNomination(Info):
    """Someone nominated the seat claiming Virgin. night = the day number.

    Both outcomes carry information. If the nominator died, this is a
    fact the table watched: the Virgin is real, sober and healthy, and
    the nominator registered as a Townsfolk. If nothing happened, it only
    bites in worlds where that seat really is the Virgin - and then the
    nominator was no Townsfolk, or the Virgin was poisoned.
    """
    nominator: int = 0
    triggered: bool = True
    source_role = "Virgin"

    def hard(self):
        # A trigger is a death everyone saw. A quiet nomination is not,
        # so it goes through the usual claim gate instead.
        return self.triggered

    def source_seat(self, state):
        return self.player

    def holds(self, w, s, rh, seat=None):
        phase = f"D{self.night}"
        if self.triggered:
            return (w.role_at(self.player, phase) == "Virgin"
                    and _registers_townsfolk(w.role_at(self.nominator, phase)))
        return not _registers_townsfolk(w.role_at(self.nominator, phase))


# Older name, kept so existing scripts still run.
VirginTrigger = VirginNomination


@dataclass
class SlayerShot(Info):
    """night = the day number on which the shot was fired."""
    target: int = 0
    died: bool = False
    source_role = "Slayer"

    def hard(self):
        # A shot that killed someone is not a story anyone can tell - a
        # body hit the floor. Nothing but a real, sober, healthy Slayer
        # hitting the Demon can do that, so it binds in every world.
        return self.died

    def source_seat(self, state):
        # A shot happens in the open, so the shooter is never in doubt
        # and there is nothing here to relay.
        return self.player

    def holds(self, w, s, rh, seat=None):
        phase = f"D{self.night}"
        t = w.role_at(self.target, phase)
        if self.died:
            return (w.role_at(self.player, phase) == "Slayer"
                    and (t in DEMONS or t == "Recluse"))
        # A shot that did nothing is only evidence if a real Slayer fired
        # it, and that is handled by the usual claim gate.
        return t not in DEMONS
