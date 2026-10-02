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
from .info import phase_index
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
            index = {r: i for i, r in enumerate(self.roles)}
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
        return self.roles[seat]

    def find_at(self, role, phase):
        """Which seat held this character at this phase."""
        return self.find(role)

    def demon_at(self, phase):
        """Which seat held the Demon at this phase."""
        for i, r in enumerate(self.roles):
            if TEAM[r] == "demon":
                return i
        return None

    def team_at(self, seat, phase):
        return TEAM[self.role_at(seat, phase)]

    def alignment_at(self, seat, phase):
        """Which side this seat was on at this phase.

        Kept apart from the character because the two come apart: an Ogre
        turns evil without changing character, a Politician turns good. A
        plain world has nothing to move, so this is simply where the
        character started.
        """
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
            self.changes, key=lambda c: phase_index(c.phase))))
        # Indexed once, by seat, with each moment already turned into a
        # number. Every question below used to walk all the changes and
        # parse every phase again — fourteen million times on one ten-seat
        # board — when most seats never change at all. Same answers, same
        # order; only the walk is shorter.
        roles, sides, demons, held = {}, {}, [], set()
        for change in self.changes:
            at = phase_index(change.phase)
            sides.setdefault(change.seat, []).append((at, change))
            if change.role is not None:
                roles.setdefault(change.seat, []).append((at, change.role))
                held.add(change.role)
                if TEAM[change.role] == "demon":
                    demons.append((at, change.seat))
        object.__setattr__(self, "_roles_by_seat", roles)
        object.__setattr__(self, "_sides_by_seat", sides)
        object.__setattr__(self, "_demon_changes", demons)
        object.__setattr__(self, "_roles_changed_to", held)

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

    def role_at(self, seat, phase):
        role = self.world.roles[seat]
        mine = self._roles_by_seat.get(seat)
        if mine:
            here = phase_index(phase)
            for at, changed in mine:
                if at <= here:
                    role = changed
        return role

    def alignment_at(self, seat, phase):
        side = alignment(self.world.roles[seat])
        mine = self._sides_by_seat.get(seat)
        if mine:
            here = phase_index(phase)
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
        seat = self.world.demon_at(phase)
        if self._demon_changes:
            here = phase_index(phase)
            for at, changed in self._demon_changes:
                if at <= here:
                    seat = changed
        return seat

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
    out = [(key, None) for key in evil if knows_what_it_is(key)]
    # Somebody who thinks they are the Demon bluffs like the Demon. A
    # Lunatic is good and lies anyway, because as far as it knows it has
    # every reason to.
    for key in script.keys:
        if thinks_it_is_evil(key):
            out.extend((key, token) for token in believed_tokens(key, script))
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
            cands.append(opts)

        # Seats with fewest options first, so the search prunes earlier
        order = sorted(range(n_players), key=lambda i: len(cands[i]))
        out.append((target, cands, order, present))
    return out


def _viable(cands_i, used, count, target):
    """Which options are still open for this seat right now."""
    return [(role, belief) for role, belief in cands_i
            if role not in used
            and (belief is None or belief not in used)
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
        if len(roles[k][t] - used) < want:
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
            used.add(role)
            verdict[team] = _fits_ahead(count, target, look, order, k, used)
            used.discard(role)
            count[team] -= 1
    return [o for o in options if verdict[TEAM[o[0]]]]


def seated_legally(roles):
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
    for seat, role in enumerate(roles):
        team = CHARACTERS[role].beside
        if team and not any(TEAM[roles[(seat + step) % n]] == team
                            for step in (-1, 1)):
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
        count = {"townsfolk": 0, "outsider": 0, "minion": 0, "demon": 0}

        def rec(k):
            if k == len(order):
                if not required <= used:
                    return                # this bag's characters never landed
                if not seated_legally(roles):
                    return                # dealt to seats it cannot sit in
                yield World(tuple(roles), tuple(believes))
                return
            i = order[k]
            for role, belief in _viable(cands[i], used, count, target):
                used.add(role)
                if belief is not None:
                    used.add(belief)
                count[TEAM[role]] += 1
                roles[i], believes[i] = role, belief

                yield from rec(k + 1)

                roles[i], believes[i] = None, None
                count[TEAM[role]] -= 1
                used.discard(role)
                if belief is not None:
                    used.discard(belief)

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
    count = {"townsfolk": 0, "outsider": 0, "minion": 0, "demon": 0}
    stands_for = 1.0

    for k, i in enumerate(order):
        options = _prune(_viable(cands[i], used, count, target),
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

        used.add(role)
        if belief is not None:
            used.add(belief)
        count[TEAM[role]] += 1
        roles[i], believes[i] = role, belief

    if not required <= used:
        return None
    # A dead end like any other: counting it as a walk that found nothing
    # keeps the estimate unbiased for the worlds that do sit legally.
    if not seated_legally(roles):
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
