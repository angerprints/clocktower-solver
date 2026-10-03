"""Whose ability was not working, and what could have stopped it.

Drunk and poisoned are one thing. A poisoned Soldier can be killed at
night; a drunk Empath's count is invented; a poisoned Monk guards
nobody. The cause differs and nothing downstream cares — so this module
talks about a seat being *impaired* on a night, and leaves what did it to
the sources registered below.

Trouble Brewing has two sources and they look nothing alike, which is
what makes the shape worth having. The Drunk is impaired every night of
the game for free, because that is simply what they are. The Poisoner
impairs one seat a night and has to have guessed right, which costs. Bad
Moon Rising adds four more — the Sailor every night, the Innkeeper from
the second, the Courtier for three nights running, the Minstrel hitting
everybody at once — and none of them fit "the Poisoner did it".

The search never enumerates who was impaired. It works the other way
round: something came out wrong, so somebody must have been impaired, and
the question is whether the sources in play could have managed it and
what that costs. Same as the poison schedule always was, generalised.
"""

from itertools import permutations
from typing import NamedTuple

from .info import phase_index


class Source(NamedTuple):
    """One thing that can stop abilities working on a given night.

    `seats` is who it could have reached, `capacity` how many at once,
    and `cost` what each hit is worth as a weight multiplier — how lucky
    it had to be to land where the world needs it. A source that reaches
    everybody for free, like being the Drunk, costs nothing.

    `cost` may be a number or a function of the seat, because some
    sources are far likelier to land on one seat than another. The Sailor
    is the case: whichever of two people it drunks is the Storyteller's
    call, and a Storyteller treats it as a price the town pays rather
    than a weapon to point at evil — so the Sailor drunking itself is
    ordinary and the Sailor drunking the evil player it picked is not.
    """

    name: str
    seats: frozenset
    capacity: int = 1
    cost: float = 1.0
    # Hitting the same seat as last night is cheaper than a fresh guess,
    # because that is what people actually do.
    repeat_cost: float = 1.0

    def price(self, seat, again=False):
        rate = self.repeat_cost if again else self.cost
        return rate(seat) if callable(rate) else rate

    def free_for_everyone(self):
        """Nothing to be lucky about, whoever it lands on."""
        return (not callable(self.cost) and not callable(self.repeat_cost)
                and self.cost >= 1.0 and self.repeat_cost >= 1.0)

    def unavoidable(self):
        """Free **and** it hits everything it reaches: being the Drunk, a
        Minstrel, a No Dashii's two neighbours.

        Free is not enough. A Sweetheart drunks one player out of the
        whole table, a Vigormortis one of two, a Goon one of whoever chose
        it — free, because the Storyteller picks, but they pick *one*.
        Treating their whole reach as impaired made every seat impaired
        once a Sweetheart had died, so "the Demon was working" could never
        hold. The engine of the single-player game exposed it (phase 1):
        a working Demon that killed on the night after a Sweetheart's
        death was called impossible.
        """
        return self.free_for_everyone() and self.capacity >= len(self.seats)


SOURCE_RULES = []


def source_rule(fn):
    """Register something that can impair a seat.

    Called with (world, state, night) and returns the Sources it offers
    that night, or an empty list.
    """
    SOURCE_RULES.append(fn)
    return fn


def sources_on(world, state, night):
    """Everything that could impair somebody on this night of this world.

    Kept on the view it was asked of. Within one story the Demon's kill
    asks it to know whether the Demon could have been stopped, and the
    impairment plan asks it again for every night it settles — the same
    answer each time, and on a busy Sects & Violets board a sixth of the
    solve went on working it out again.
    """
    # Good for this state in this epoch only — see `solver.best_story`.
    epoch = getattr(state, "_epoch", None)
    memo = getattr(world, "_sources_memo", None)
    if memo is None or memo[0] is not state or memo[1] != epoch:
        memo = (state, epoch, {})
        try:
            object.__setattr__(world, "_sources_memo", memo)
        except AttributeError:
            pass
    got = memo[2].get(night)
    if got is None:
        got = []
        for rule in SOURCE_RULES:
            got.extend(rule(world, state, night))
        memo[2][night] = got
    return list(got)


def _alive_through(world, state, seat, night):
    """Was this seat still able to act on this night?"""
    return seat in state.alive_set(f"N{night}")


@source_rule
def always_impaired(world, state, night):
    """Whoever was handed the wrong token.

    They are impaired every night of the game and it costs nothing —
    being the Drunk is not a piece of luck, it is what they are. Elsewhere
    the Marionette and the Lunatic are the same story.
    """
    # Holding a token *is* being a believer, and the tokens are already
    # on the world — so this is a tuple scan rather than a character
    # lookup per seat per night.
    seats = frozenset(seat for seat, token in enumerate(world.believes)
                      if token is not None)
    if not seats:
        return []
    return [Source("believer", seats, capacity=len(seats), cost=1.0,
                   repeat_cost=1.0)]


def make_poisoner_rule(hit_cost, repeat_cost):
    """The Poisoner, as a source.

    The costs are read late, through callables, so the sensitivity pass
    can still move the solver's constants and have it mean something.
    """

    def poisoner(world, state, night):
        # Looked up per night: a Poisoner who inherits the Demon has
        # stopped being the Poisoner.
        seat = world.find_at("Poisoner", f"N{night}")
        if seat is None or not _alive_through(world, state, seat, night):
            return []
        reach = state.alive_set(f"N{night}")
        return [Source("Poisoner", reach, capacity=1,
                       cost=hit_cost(), repeat_cost=repeat_cost())]

    return poisoner


def arrangements(sources, cap=64):
    """Every way tonight's sources could have been placed.

    `plan_night` prices an arrangement somebody else chose; this proposes
    them. The distinction sounds small and is the whole reason the
    night-walk could not be switched on: the walk needs a concrete
    assignment to replay, and a cost model has none to give.

    Free sources are not enumerated. A Drunk holding somebody else's
    token reaches exactly one seat and always hits it; a Minstrel
    silences everybody. There is nothing to choose, so they are folded in
    as a fixed part of every arrangement.

    Yields `(fixed, chosen)` where `chosen` maps a source name to the
    seat it took. Capped, because a Poisoner with twelve seats beside a
    Monk with twelve is a hundred and forty-four before anything else —
    and the cap is the number worth measuring rather than assuming.
    """
    fixed = set()
    paid = []
    for source in sources:
        if source.unavoidable():
            fixed |= set(source.seats)
        elif source.seats:
            paid.append(source)

    out = [(frozenset(fixed), {})]
    for source in paid:
        grown = []
        # A source that takes more than one seat hands over a tuple.
        #
        # An Innkeeper drunks one of the two it protects and its capacity
        # says two, so giving it a single seat made the walk try to
        # iterate an integer. The source knows how many it takes, so this
        # is the place to say so rather than making every caller guess.
        import itertools
        width = max(1, min(source.capacity, len(source.seats)))
        picks = (sorted(source.seats) if width == 1
                 else list(itertools.combinations(sorted(source.seats),
                                                  width)))
        for base, chosen in out:
            for pick in picks:
                taken = dict(chosen)
                taken[source.name] = pick
                seats = {pick} if isinstance(pick, int) else set(pick)
                grown.append((base | seats, taken))
            if len(grown) >= cap:
                break
        out = grown[:cap]
    return out


def plan_night(sources, required, forbidden, previous):
    """Could these sources have impaired exactly who the world needs?

    `required` must be impaired, `forbidden` must not be. Returns
    (cost, who each source hit) for the cheapest arrangement, or None if
    there is no arrangement at all.

    Free sources are applied first: a seat covered by one needs nothing
    else, and a seat a free source cannot avoid reaching makes a
    `forbidden` seat impossible.
    """
    free = [s for s in sources if s.unavoidable()]
    paid = [s for s in sources if s not in free]

    covered_free = set()
    for source in free:
        covered_free |= source.seats
    if covered_free & set(forbidden):
        return None                       # something unavoidable reached them

    if set(required) & set(forbidden):
        return None                       # asked to be working and not

    outstanding = [seat for seat in required if seat not in covered_free]
    if not outstanding:
        return 1.0, {}

    # One seat to cover and one source that can pay for it is what nearly
    # every night looks like, and it is worth not building the machinery
    # for it. Trouble Brewing never looks like anything else.
    if len(outstanding) == 1 and len(paid) == 1:
        seat, source = outstanding[0], paid[0]
        if source.capacity < 1 or seat not in source.seats \
                or seat in forbidden:
            return None
        same = previous.get(source.name) == seat
        return source.price(seat, same), {source.name: seat}

    # Beyond that the numbers stay tiny, so trying the arrangements
    # outright is simpler than being clever and just as fast.
    slots = []
    for source in paid:
        slots.extend([source] * source.capacity)
    if len(outstanding) > len(slots):
        return None

    best, best_hits = None, None
    # In the order they come, which is the order the JavaScript tries
    # them in. Two arrangements often cost the same, the first one found
    # is kept, and what it chose decides what the *next* night costs — so
    # walking a `set` of them, in whatever order the hashes fell, let the
    # two languages disagree on a tie (03.10.2026).
    for arrangement in permutations(range(len(slots)), len(outstanding)):
        cost, hits, ok = 1.0, {}, True
        for seat, slot in zip(outstanding, arrangement):
            source = slots[slot]
            if seat not in source.seats or seat in forbidden:
                ok = False
                break
            same = previous.get(source.name) == seat
            cost *= source.price(seat, same)
            hits[source.name] = seat
        if ok and (best is None or cost > best):
            best, best_hits = cost, hits
    if best is None:
        return None
    return best, best_hits
