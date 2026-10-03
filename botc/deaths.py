"""What killed somebody, not merely that they died.

Trouble Brewing only ever kills at night one way, so "died at night" and
"died by the Demon" were the same sentence and the solver never had to
tell them apart. They are not the same sentence. A Soldier cannot be
killed by the Demon and can be killed by a Gossip, an Assassin or a
Godfather without any trouble at all. So a death is attributed to a
*cause*, and what a character is safe from is a question about the cause
rather than about the night.

Three things a cause carries beyond who it could have reached:

  kind        What sort of death it is. The Soldier's protection reads
              "safe from the Demon", so it turns on this and not on the
              character doing the killing.
  must_fire   Whether it happens whether or not anybody wants it to. The
              Demon kills every night, so a night where nobody died is a
              night something stopped it. A Gossip only kills when it
              said something true, so a quiet night owes it nothing.
  implies     Deaths that follow from this one. A Grandmother dies when
              her grandchild is killed by the Demon — which is exactly
              why the kind matters, since the grandchild dying to a
              Gossip leaves her standing.

Protection is not modelled as a property of the night either. The Monk
guards against the Demon; the Innkeeper guards against everything, so a
Grandmother's grief and a Gambler's bad guess are stopped by one and not
by the other.
"""

from typing import NamedTuple

DEMON = "demon"          # the Demon's own kill
OTHER = "other"          # anything else that kills at night
# A Moonchild's pick, written down. Told apart because it is the one
# death that names its victim in public beforehand — so when that player
# lives, there is something to explain that no other cause has.
PICKED = "picked"


class Cause(NamedTuple):
    name: str
    kind: str
    seats: frozenset          # who it could have reached
    capacity: int = 1
    cost: float = 1.0
    must_fire: bool = False   # does it happen whether or not it is wanted
    # Does anything stop it? An Assassin kills "even if they could not",
    # which overrides every shield there is — a Sailor that cannot die, a
    # Fool's free one, a Monk's target, an Innkeeper's pair. Nothing else
    # in the game does this, and a seat killed this way tells you nothing
    # about whether its protection was working.
    unstoppable: bool = False
    # Some kills are the far end of something that started earlier. A
    # Pukka poisons on one night and the poison kills on the next, so the
    # victim has to have been the one it poisoned — which is a demand on
    # a night that has already been explained. Given as a span number.
    victim_impaired_at: int = None
    # And some need more than the victim to have been impaired back
    # then. A Pukka that was itself drunk for a night kept its poison
    # waiting and killed a night late: (span, seat) pairs that also had
    # to be impaired, on nights already explained.
    also_impaired: tuple = ()
    # Seats that die as a consequence, given who this one killed.
    # Called with (victim) and returns further seats.
    implies: object = None
    # The seat whose ability this is, when it has one. A must-fire cause
    # that killed nobody may then have been stopped at its **source**: a
    # poisoned Imp kills nobody, which is a quiet night as legal as a
    # Monk's. Without this the only explanation on offer was a shield on
    # the victim, and a Poisoner that hit its own Demon made the whole
    # board impossible. And the other way round: a cause that did kill
    # had a working source.
    actor: int = None
    # What it costs to explain a quiet night by stopping the actor. A
    # Poisoner hitting its own Demon is legal and rare; see solver.py.
    actor_cost: float = 1.0


CAUSE_RULES = []
IMMUNITY_RULES = []
IMPLICATION_RULES = []


class Implication(NamedTuple):
    """A death that follows from another one.

    `seat` is who else goes. `needs` is the seat whose ability makes it
    happen, which has to have been working — a poisoned Grandmother
    grieves nobody.

    What makes this awkward is that the thing linking them is usually a
    marker rather than a character. The grandchild is not a character
    anybody holds; it is a token the Storyteller put on a seat when the
    Grandmother was shown it. So a rule reads the board, including the
    readings on the ledger, rather than reading the roles.
    """

    seat: int
    needs: int


def implication_rule(fn):
    """Register a death that drags another one with it.

    Called with (world, state, night, victim, kind) and returns the
    Implications that follow from that victim dying that way.
    """
    IMPLICATION_RULES.append(fn)
    return fn


def implications_of(world, state, night, victim, kind):
    out = []
    for rule in IMPLICATION_RULES:
        out.extend(rule(world, state, night, victim, kind))
    return out


def cause_rule(fn):
    """Register something that can kill at night.

    Called with (world, state, night); returns the Causes available.
    """
    CAUSE_RULES.append(fn)
    return fn


def immunity_rule(fn):
    """Register something that stops a death.

    Called with (world, state, night, seat, kind) and returns True if
    that seat cannot be killed that way tonight — but only when the thing
    doing the protecting is working. Whether it *was* working is the
    impairment plan's business, so a rule that depends on it says so by
    returning the seat whose ability has to have held, via `needs`.
    """
    IMMUNITY_RULES.append(fn)
    return fn


class Shield(NamedTuple):
    """A reason somebody could not have died that way.

    `needs` is the seat whose ability had to be working for it to hold —
    a Soldier protects itself, a Monk protects somebody else. The plan is
    then asked to leave that seat unimpaired, and if it cannot, the
    protection did not happen and the death is back on the table.

    `cost` is what leaning on this shield is worth. A protector doing its
    job costs nothing. Aiming a kill at a corpse is a deliberate play
    rather than the default, so it costs — and it has no `needs`, because
    nothing had to be working for a corpse to stay dead.
    """

    by: str
    needs: int = None
    cost: float = 1.0
    # Did somebody choose to point this at them? A Soldier is safe every
    # night whether anybody likes it or not, so a Soldier who died must
    # have been impaired. A Monk picks one player a night, so a death
    # only ever means it guarded somebody else — it implies nothing about
    # the victim, and must not be read as though it did.
    chosen: bool = False


def shields_on(world, state, night, seat, kind):
    """Every reason this seat could have survived that kind of death."""
    out = []
    for rule in IMMUNITY_RULES:
        got = rule(world, state, night, seat, kind)
        if got:
            out.extend(got)
    return out


def causes_on(world, state, night):
    out = []
    for rule in CAUSE_RULES:
        out.extend(rule(world, state, night))
    return out


def explain_night(world, state, night, died, blame=False):
    """How the night's deaths could have come about.

    Returns a list of (cost, impaired, working) — what each account
    costs, which seats it needs to have been impaired, and which it needs
    to have been working. Empty means no account fits and the world is
    impossible.

    Not every body needs a cause of its own. A Grandmother dies because
    her grandchild was killed, so one Demon kill can leave two bodies —
    and the same link runs the other way, which is where the deduction
    is: if the grandchild died to the Demon and the Grandmother is still
    standing, that seat was not the grandchild, or she was poisoned.
    """
    causes = causes_on(world, state, night)
    if not causes:
        return [] if died else [(1.0, frozenset(), frozenset(), {})]

    died = sorted(died)
    out = []
    # Which bodies were somebody's aim, and which followed from another.
    # With nothing on the script that drags a second death along, every
    # body was aimed at and there is only the one split to try.
    splits = _subsets(died) if IMPLICATION_RULES else [set(died)]
    for picked in splits:
        directly = [v for v in died if v in picked]
        followed = [v for v in died if v not in picked]
        out.extend(_account_for(world, state, night, causes,
                                directly, followed, blame))
    if blame:
        return out

    seen, unique = set(), []
    for cost, impaired, working, before in out:
        key = (round(cost, 9), frozenset(impaired), frozenset(working),
               tuple(sorted((n, tuple(sorted(v))) for n, v in before.items())))
        if key in seen:
            continue
        seen.add(key)
        unique.append((cost, frozenset(impaired), frozenset(working), before))
    unique.sort(key=lambda x: -x[0])
    return unique


def _subsets(items):
    """Every way of splitting the bodies into aimed-at and consequent."""
    out = [set()]
    for item in items:
        out += [chosen | {item} for chosen in out]
    return out


def _account_for(world, state, night, causes, directly, followed,
                 blame=False):
    """One split: these were aimed at, those followed from them."""
    accounts = [(1.0, set(), set(), {c.name: 0 for c in causes}, [], {})]

    for victim in directly:
        grown = []
        for cost, impaired, working, used, chain, before in accounts:
            for cause in causes:
                if victim not in cause.seats:
                    continue
                if used[cause.name] >= cause.capacity:
                    continue
                # A shield that was always there has to have failed, and
                # that means whatever provided it was impaired. A shield
                # somebody had to aim says nothing: they aimed elsewhere.
                # Unless nothing could have stopped this in the first
                # place, in which case no shield has anything to answer
                # for — including the one that says you cannot kill a
                # corpse, which still holds because a corpse is not a
                # kill.
                blocked = [s for s in shields_on(world, state, night, victim,
                                                 cause.kind)
                           if not s.chosen
                           and (not cause.unstoppable or s.needs is None)]
                if any(shield.needs is None for shield in blocked):
                    continue              # nothing could undo this one
                # The sets copied, not only the dict around them: they
                # are shared between every account that grew from this
                # one, and adding to one in place added to them all.
                earlier = {span: set(seats) for span, seats in before.items()}
                if cause.victim_impaired_at is not None:
                    earlier.setdefault(cause.victim_impaired_at,
                                       set()).add(victim)
                for span, who in cause.also_impaired:
                    earlier.setdefault(span, set()).add(who)
                grown.append((
                    cost * cause.cost,
                    impaired | {s.needs for s in blocked},
                    set(working),
                    dict(used, **{cause.name: used[cause.name] + 1}),
                    chain + [(victim, cause.kind, cause.name)],
                    earlier,
                ))
        accounts = grown
        if not accounts:
            return []

    # What follows from those deaths, and whether the board agrees.
    settled = []
    for cost, impaired, working, used, chain, before in accounts:
        implied = []
        for victim, kind, _name in chain:
            implied.extend(implications_of(world, state, night, victim, kind))

        options = [(cost, set(impaired), set(working))]
        for hit in implied:
            grown = []
            # A death that follows is still a death, and what keeps a
            # seat alive keeps it alive from this too: a Grandmother
            # beside a working Tea Lady, or in the Innkeeper's pair,
            # does not die of grief. Not the Demon's own kill, so a Monk
            # or a Soldier's kind of safety is no help.
            #
            # None of that was asked. She lived, so she "was not
            # working" — and with nothing able to impair her the world
            # that happened was thrown out (03.10.2026, found as soon as
            # the simulator stopped killing her through a Tea Lady).
            shields = shields_on(world, state, night, hit.seat, OTHER)
            for c, imp, wk in options:
                if hit.seat in followed:
                    # It happened: whatever caused it was working, and
                    # anything always-on that should have stopped it was
                    # not.
                    blocked = [s for s in shields if not s.chosen]
                    if any(s.needs is None for s in blocked):
                        continue
                    grown.append((c, imp | {s.needs for s in blocked},
                                  wk | {hit.needs}))
                elif hit.seat in imp:
                    grown.append((c, imp, wk | {hit.needs}))
                else:
                    # It did not happen. Whatever would have caused it
                    # was not working —
                    grown.append((c, imp | {hit.needs}, set(wk)))
                    # — or something kept them alive, and *that* was.
                    for s in shields:
                        if s.needs is not None and s.needs in imp:
                            continue
                        grown.append((c * s.cost, set(imp),
                                      wk | ({s.needs} if s.needs is not None
                                            else set())))
            options = grown

        for c, imp, wk in options:
            covered = {hit.seat for hit in implied if hit.needs not in imp}
            if any(v not in covered for v in followed):
                continue                  # a body nothing accounts for
            if imp & wk:
                continue                  # asked to be both at once
            if blame:
                who = {victim: name for victim, _kind, name in chain}
                who.update({v: "followed on" for v in followed})
                settled.append((c, imp, wk, used, who))
            else:
                settled.append((c, imp, wk, used, before))

    # Anything that fires whether or not it is wanted, and killed nobody,
    # was stopped — and something had to do the stopping.
    if blame:
        return [(cost, imp, wk, who) for cost, imp, wk, _used, who in settled]

    for cause in causes:
        if not cause.must_fire:
            continue
        grown = []
        for cost, impaired, working, used, before in settled:
            if used[cause.name] > 0:
                # It did the killing, so there is nothing to explain —
                # except that whoever did it was working.
                if cause.actor is not None:
                    if cause.actor in impaired:
                        continue
                    working = working | {cause.actor}
                grown.append((cost, impaired, working, used, before))
                continue
            if cause.actor is not None and cause.actor not in working:
                # Stopped at its source: the killer was droisoned.
                grown.append((cost * cause.actor_cost,
                              impaired | {cause.actor}, working,
                              used, before))
            for target in sorted(cause.seats):
                for shield in shields_on(world, state, night, target,
                                         cause.kind):
                    if shield.needs is not None and shield.needs in impaired:
                        continue          # it was impaired, so it held nothing
                    grown.append((
                        cost * shield.cost, set(impaired),
                        working | ({shield.needs} if shield.needs is not None
                                   else set()),
                        used, before,
                    ))
        settled = grown
        if not settled:
            return []
    return [(cost, impaired, working, before)
            for cost, impaired, working, _used, before in settled]
