"""Step 3: build worlds, test them against what people said, weigh, report.

Worlds are no longer counted equally. Two things change a world's weight:

  * A good player who lied.  Evil players bluff constantly - that costs a
    world nothing. A good player claiming a role they do not hold is rare,
    so those worlds are pushed far down instead of being treated as equals.
  * Your own social read.  Each step of a read multiplies the odds that
    seat is evil, so a read shifts the picture without ever forcing it.
"""

import math
import random
import sys
from collections import defaultdict
from itertools import product

from .info import (CourtierChoice, GameState, FortuneTeller,
                   AcrobatChoice, GrandmotherInfo, SlayerShot,
                   VirginNomination, BecameInfo, EvilTwinPair,
                   phase_index)
from .roles import (ABSENT, ARBITRARY, GENUINE, SETUP, TEAM,
                    ability_state, believed_tokens, believes_another,
                    INVERTED,
                    is_evil, must_hide, show, wake_fits)
from . import deaths as death_causes
from . import impairment
from .catalogue import CHARACTERS
from .worlds import (Change, Timeline, World, enumerate_worlds,
                     iter_worlds, sample_worlds)

# Two different limits, and keeping them apart matters.
#
# EXACT_LIMIT is where `analyze` stops walking every world and samples
# instead. A full Bad Moon Rising board has a hundred times as many worlds
# as the same table on Trouble Brewing — thirty-eight characters and four
# Demons — and walking all of them takes thirteen seconds against one for a
# sampled answer that agrees inside its own margins. The margins are
# shown, so what you give up is visible.
#
# DEFAULT_MAX_WORLDS is the hard ceiling on enumeration, and it is much
# higher. Setting the first and using it as the second made `solve`
# quietly return a truncated world set, which is a different and worse
# thing than sampling: no margins, no warning worth the name, and no way
# to tell which worlds were dropped.
EXACT_LIMIT = 40_000
DEFAULT_MAX_WORLDS = 300_000

# Good players lie far less than evil ones, but not all good lies are the
# same. An Outsider covering their role is close to routine - a Recluse or
# a Saint claiming a Townsfolk is a normal way to stay alive. A Townsfolk
# claiming to be a *different* Townsfolk is something else entirely: it
# poisons their own team's information for no gain, and is rare enough
# that those worlds should almost vanish.
OUTSIDER_HIDING_PENALTY = 0.35
TOWNSFOLK_LIE_PENALTY = 0.02
# A Cerenovus exists to make good players lie: each night it names
# somebody who must convince the table they are some other good
# character tomorrow. In a world with one alive, a good Townsfolk's false
# claim is madness rather than chaos — up to one per night it was alive.
CERENOVUS_MADNESS_PENALTY = 0.25

# Evil is handed bluffs drawn from roles that are NOT in play, and the team
# knows each other, so a clean bluff is one that collides with nothing: not
# with a role someone genuinely holds, and not with a teammate's bluff.
# Both collisions happen - a deliberate double-claim is a real tactic - but
# neither is the default, so those worlds are discounted once per bluff.
BLUFF_COLLISION_PENALTY = 0.3

# Each point of social read multiplies the odds of that seat being evil.
READ_ODDS_STEP = 2.0

# Marking a seat as possibly unreliable multiplies the odds that they were
# handed somebody else's token. It says nothing about their side — a
# suspected Drunk is a good player being wrong, which is a different
# suspicion from a suspected Minion, and the two sliders stay separate.
#
# It does not tilt towards *poisoning*, and the reason is that it cannot:
# being poisoned is not a property of a world, it is part of the story the
# solver tells about one. What the marker can do is raise the odds of the
# case that lives in the world itself.
DRUNK_SUSPICION_STEP = 3.0

# The Demon kills good players. Killing your own Minion wastes a night, and
# the one real reason to do it - the Imp passing the star - happens late,
# once the Imp is cornered. So a seat that died on an early night is very
# unlikely to be evil, and the discount fades one night at a time.
# Nobody dies on night 1 in Trouble Brewing, so night 2 is the first kill
# and carries the full discount: it keeps 5% of the weight, night 3 keeps
# 10%, and by night 21 the factor has climbed back to 1 and stops mattering.
NIGHT_DEATH_EVIL_PENALTY = 0.05

# A world that only survives because the Poisoner hit exactly the right
# seat on exactly the right night is not as good a story as one where the
# information is simply true. Every required hit costs this much - so two
# lucky hits cost twice over, and three worlds of corroborating info that
# all hold up beat one that needs the Poisoner to be clairvoyant.
POISON_HIT_PENALTY = 0.35

# Staying on the same target is what Poisoners actually do, so repeat hits
# on a seat already being poisoned are much cheaper than fresh ones.
POISON_REPEAT_PENALTY = 0.7

# Sinking a kill into a corpse is a real play — it fakes protection, and
# it is exactly what a Demon bluffing Soldier or Monk wants the table to
# believe. But it is a deliberate choice rather than the default, so a
# quiet night that can only be explained that way costs something. A quiet
# night with a working protector in play costs nothing.
SUNK_KILL_PENALTY = 0.45

# A Poisoner hitting its own Demon is legal — a poisoned Imp kills nobody,
# which fakes a Monk's save — and it is rare. Settled at the table
# (28.09.2026): rare. Priced on top of the poison itself, so a quiet night
# with a claimed Monk still leaves that Monk at 99.5 per cent rather than
# the 90.9 that pricing it like any other poison target gave. Before the
# engine found it this explanation did not exist at all, and a quiet
# night was proof of a protector.
DEMON_POISONED_PENALTY = 0.05

# Information with no genuine source anywhere in a world had to be invented
# out of nothing. That happens - people bluff detailed readings - but it is
# a deliberate risk, so those worlds are discounted. This is what makes an
# unclaimed role fit itself onto the table: if someone calls Empath numbers
# and no seat has claimed Empath, worlds where an Empath quietly exists
# explain the call, and worlds with no Empath at all have to pay for it.
FABRICATED_INFO_PENALTY = 0.4

# What one step of "I believe this reading" is worth, as an odds
# multiplier on the row being genuine. Trusting a reading makes inventing
# it expensive; distrusting it makes inventing it free, which is the same
# as not counting the row at all. A row nobody vouches for sits at the
# default above.
INFO_TRUST_STEP = 2.0

# What one confirmed reading is worth, as an odds multiplier on its
# source really being that character.
#
# Evidence, not proof. An Undertaker whose readings keep checking out is
# more likely to be the Undertaker — but a Spy reading the grimoire can
# feed a Minion true information all game, so no pile of confirmations
# ever reaches certainty. That is what separates this from the seat-level
# "confirmed", which pins a character absolutely and is right for a
# Virgin that triggered or a Slayer that fired.
#
# It accumulates per reading: four confirmed rows from one seat multiply.
CONFIRMED_READING_STEP = 2.5


def invention_cost(info):
    """What a world pays for having made this reading up."""
    trust = getattr(info, "trust", 0) or 0
    return min(1.0, FABRICATED_INFO_PENALTY / (INFO_TRUST_STEP ** trust))


# --------------------------------------------------------------------------
# Consistency
# --------------------------------------------------------------------------

def scarlet_woman_takes_over(world, state, phase):
    """Does the Scarlet Woman become the Demon if it dies at this phase?

    Her condition is her own: she must be alive, and five or more players
    still alive when the Demon goes. She takes priority over any other
    Minion, so when this is true there is no choice to be made.
    """
    seat = world.find_at("ScarletWoman", phase)
    if seat is None:
        return False
    alive = state.alive_at(phase)
    return seat in alive and len(alive) >= 5


def starpass_heirs(world, state, phase):
    """Which Minions could take the star when the Imp kills itself.

    The Imp's own ability hands the star to a Minion regardless of how
    many players are left — that count is the Scarlet Woman's condition,
    not the Imp's. But when she qualifies she takes it, so the list
    collapses to her alone.
    """
    alive = set(state.alive_at(phase))
    minions = [m for m in range(state.n_players)
               if world.team_at(m, phase) == "minion" and m in alive]
    if not minions:
        return []
    if scarlet_woman_takes_over(world, state, phase):
        return [world.find_at("ScarletWoman", phase)]
    return minions


# --------------------------------------------------------------------------
# Characters that rewrite other characters
# --------------------------------------------------------------------------
# A rule is called with a view of the world (the changes so far already
# applied) and the state, and answers: what could this character have done,
# and what does each story cost? It returns (changes, weight) pairs, where
# an empty changes tuple means "nothing happened", which is usually the
# only answer.
#
# Rules must be *anchored* to something on the record — a death, an
# execution, an event the table saw. A rule that could fire on any night
# for no reason would multiply the search by the number of seats times the
# number of nights, for stories nothing is asking for. Where a character
# really does act unprompted, the way in is to record the event: the same
# way a Virgin trigger or a Slayer shot gets in today. Repair-on-demand —
# positing a change only where a statement would otherwise be false — is
# the harder version and is not built.
TRANSITION_RULES = []


# The slot each rule's character acts at, so the rules run in the order
# the night ran.
#
# **Order does matter**, and the comment here used to say it did not.
# Each rule sees the previous ones' work through a `Timeline` and appends
# its own changes, and `role_at` takes the last change at a phase — so
# the sequence the rules run in *is* the sequence of the night.
#
# They ran Barber, Pit-Hag, Farmer, Snake Charmer — slots 40, 16, 48 and
# 11, almost exactly backwards. On a night with a charmer swap and a
# Pit-Hag the Pit-Hag's change landed first and the swap overwrote it, so
# the Pit-Hag's own row read as false and needed a Pit-Hag nothing could
# droison.
#
# Sorting the chain afterwards was the other way to fix this and it needs
# a field `Change` does not have: the *actor's* slot, not the granted
# character's. Ordering the rules needs nothing new at all.
_ACTS_AT = {"a_snake_charmer_takes_the_star": 11,
            "a_pit_hag_makes_somebody_else": 16,
            "a_barber_lets_the_demon_swap_two": 40,
            "a_farmer_hands_it_on": 48,
            # Late on the first night, after every information role: an
            # Empath or Noble on night one still sees the Ogre as good.
            "an_ogre_picks_a_side": 60,
            "demon_handovers": 99}      # a death, so after everything


def transition_rule(fn):
    """Register a rule. They run in night order; see `_ACTS_AT`."""
    TRANSITION_RULES.append(fn)
    TRANSITION_RULES.sort(key=lambda f: _ACTS_AT.get(f.__name__, 50))
    return fn


def possible_timelines(world, state, cap=128):
    """Every account of who was what, and when.

    Rules compose: each is offered the changes agreed so far and may add
    its own. An empty result from any rule means nothing can explain this
    world, which is how a Demon dead in daylight with nobody to inherit
    gets ruled out.

    **128, not 48.** A Barber's death offers every pair of seats, which
    is fifty-five at eleven players, and the cap cut the true swap off
    the end (29.09.2026). 128 covers every pair up to fifteen; measured
    on the corpus it costs three per cent.

    **A night at a time.** The rules run in night-slot order, and each
    covers every night at once — so run as one pass, the Snake Charmer
    (slot 11) never saw what the Barber (slot 40) or a Fang Gu's jump
    (a handover, last) had done on an *earlier* night, and a charmer that
    swapped with the Demon they had moved read as pointing at the wrong
    seat (29.09.2026, once the simulator played the jump). Now every rule
    is asked once per night, sees everything decided before that night,
    and keeps only that night's changes.

    Two things a night-at-a-time pass has to allow for, both learned the
    hard way on the first try:

    * **Only the last pass may call a story impossible.** A rule asked on
      night one sees a board without night four's swap, and the Demon's
      lineage then finds a death on night four with nobody to inherit.
      Early on, "nothing fits" means "nothing to add tonight".
    * **A change may arrive late for an earlier night**, when the rule
      could only offer it once a later night was in view. It is added if
      nothing in the story contradicts it — the same seat changed
      differently at the same moment, or a different Demon made at the
      same moment — and the story is kept in time order, because a
      timeline reads its changes in order.

    A cost is charged when an offer adds something, so a story pays for
    each change once.
    """
    # One rule that can move anybody, beside the Demon's own lineage, and
    # there is nothing for a night at a time to untangle: nobody else's
    # change can be missing from its view. That is every Trouble Brewing
    # and Bad Moon Rising board, and the single pass is a third quicker
    # over the corpus.
    #
    # Counted **in this world**, not on the script. Asked of the script,
    # every Sects & Violets board took the slow road for every world —
    # including the three quarters with no Barber, no Fang Gu and nothing
    # recorded for a Snake Charmer or a Pit-Hag — and once the Mutant
    # multiplied the worlds that was most of the time a solve took.
    if _movers_in(world, state) < 2:
        return _all_nights_at_once(world, state, cap)

    last = max(1, int(state.final_phase()[1:]))
    # A story is (changes, weight, owned): `owned[i]` is what rule i has
    # contributed, so it can be asked again without its own earlier work
    # in view — exactly as it saw the board when all rules ran once.
    stories = [((), 1.0, ())]
    try:
        stories = _night_by_night(world, state, cap, last, stories)
    finally:
        state._horizon = None
    return [(changes, weight) for changes, weight, _owned in stories]


def _movers_in(world, state):
    """How many kinds of change could actually happen in this world.

    Each counts only when its rule could offer something here: a Snake
    Charmer or a Pit-Hag through a recorded row (the rules apply those
    whoever holds what), a Barber, Farmer or Fang Gu only if one is in
    the world — dealt, or made by a recorded Pit-Hag creation — and has
    the death that sets it off, an Ogre only if one was dealt.
    """
    made, swapped = set(), False
    for info in state.infos:
        source = getattr(info, "source_role", None)
        if source == "PitHag" and getattr(info, "role", None):
            made.add(info.role)
        elif source == "SnakeCharmer" and getattr(info, "swapped", False):
            swapped = True
    deaths = [(s, p) for s, p in state.death_phases() if p]
    phases = [p for _s, p in deaths]
    at_night = any(p[0].upper() == "N" for p in phases)
    # A Barber counts only once a seat that claimed it has died.
    barber_died = bool(barber_claimants(state) & {s for s, _p in deaths})
    roles = set(world.roles) | made
    count = int(swapped) + int(bool(made))
    for key, needs in (("Barber", barber_died), ("Farmer", at_night),
                       ("FangGu", at_night), ("Ogre", True)):
        if needs and key in roles and _in_bag(state, key):
            count += 1
    return count


def _all_nights_at_once(world, state, cap):
    """Every rule once, over the whole game, in night-slot order."""
    stories = [((), 1.0)]
    for rule in TRANSITION_RULES:
        grown = []
        for changes, weight in stories:
            view = Timeline(world, changes) if changes else world
            for extra, cost in rule(view, state):
                grown.append((changes + tuple(extra), weight * cost))
                if len(grown) >= cap:
                    break
            if len(grown) >= cap:
                break
        if not grown:
            return []
        stories = grown
    return stories


def _nights_it_acts(rule, state):
    """The nights a transition rule could add anything, or None for all.

    Asking every rule on every night's pass made a busy Sects & Violets
    board ten times slower — the Barber alone was asked four hundred
    thousand times to enumerate its pairs for nights where no Barber had
    died. The last pass still asks every rule about the whole game, so
    this only saves the passes where nothing could have happened.
    """
    deaths = [(int(p[1:]), p[0].upper()) for _s, p in state.death_phases()]
    rows = lambda role, field: {
        info.night for info in state.infos
        if getattr(info, "source_role", None) == role
        and getattr(info, field, None)}
    name = rule.__name__
    if name == "a_barber_lets_the_demon_swap_two":
        claimed = barber_claimants(state)
        return {int(p[1:]) + 1 if p[0].upper() != "N" else int(p[1:])
                for seat, p in state.death_phases()
                if p and seat in claimed}
    if name == "a_pit_hag_makes_somebody_else":
        return rows("PitHag", "role")
    if name == "a_snake_charmer_takes_the_star":
        return rows("SnakeCharmer", "swapped")
    if name == "a_farmer_hands_it_on":
        return {k for k, kind in deaths if kind == "N"}
    if name == "an_ogre_picks_a_side":
        return {1}
    if name == "demon_handovers":
        return {k for k, _kind in deaths}
    return None


def _night_by_night(world, state, cap, last, stories):
    acts = [_nights_it_acts(rule, state) for rule in TRANSITION_RULES]
    for night in range(1, last + 1):
        final = night == last
        # How far the Demon's lineage looks on this pass. A death after
        # tonight has not happened yet: a Fang Gu jump on night two needs
        # a Snake Charmer swap on night three to explain what follows, and
        # judged whole on night two the jump was thrown out before the
        # swap could exist.
        state._horizon = night
        for i, rule in enumerate(TRANSITION_RULES):
            if not final and acts[i] is not None and night not in acts[i]:
                continue                  # nothing it could add tonight
            grown, seen = [], {}

            def keep(changes, got, owned):
                # In time order and, within one moment, in the order the
                # rules act: a Snake Charmer's swap at slot 11 and a
                # Barber's at 40 on the same night touch the same seat
                # one after the other, and asking a rule again on a later
                # pass must not move its change behind the other's.
                owner = {c: k for k, mine in owned for c in mine}
                key = tuple(sorted(changes, key=lambda c: (
                    phase_index(c.phase), owner.get(c, len(TRANSITION_RULES)))))
                if key in seen:
                    j = seen[key]
                    if got > grown[j][1]:
                        grown[j] = (key, got, owned)
                    return
                seen[key] = len(grown)
                grown.append((key, got, owned))

            for changes, weight, owned in stories:
                if len(grown) >= cap:
                    break
                mine = dict(owned).get(i, ())
                others = tuple(c for c in changes if c not in mine)
                view = Timeline(world, others) if others else world
                fitted = False
                for extra, cost in rule(view, state):
                    upto = tuple(c for c in extra
                                 if int(c.phase[1:]) <= night)
                    # What this rule already settled for earlier nights
                    # has to stand; an offer that drops or changes it is
                    # another story.
                    if any(int(c.phase[1:]) < night and c not in upto
                           for c in mine):
                        continue
                    fitted = True
                    added = [c for c in upto if c not in mine]
                    again = tuple((k, v) for k, v in owned if k != i)
                    keep(others + upto, weight * (cost if added else 1.0),
                         again + ((i, upto),))
                    if len(grown) >= cap:
                        break
                if not fitted and not final:
                    keep(changes, weight, owned)  # judged once all is in
            if not grown:
                return []
            stories = grown
    return stories



# Who can catch the Demon when it drops. The trigger is fixed by the rules
# of the game — the Demon died, something has to have happened — but the
# list of who could take it is the part scripts keep adding to. A rule is
# given the view, the phase of the death and the character being handed
# on, and returns the Changes it would allow.
HEIR_RULES = []


def heir_rule(fn):
    """Register a way for the Demon to change hands."""
    HEIR_RULES.append(fn)
    return fn


# Demons that hand the star on when they kill themselves. The Imp is the
# only one in print, and saying so out loud matters: this used to be
# offered to *every* Demon dying at night, so a Zombuul or a Fang Gu that
# fell to a Slayer or an Assassin could quietly pass to a Minion and the
# game carried on. Good had actually won.
STARPASSES = {"Imp"}


@heir_rule
def a_minion_catches_the_star(view, state, phase, character):
    """The Imp kills itself and a Minion takes over.

    Only the Imp. Every other Demon dying at night is the end of it —
    unless that Demon has a rule of its own, like the Fang Gu jumping
    into an Outsider.
    """
    if phase[0].upper() != "N" or character not in STARPASSES:
        return []
    return [Change(phase, seat, character)
            for seat in starpass_heirs(view, state, phase)]


@heir_rule
def an_outsider_becomes_the_fang_gu(view, state, phase, character):
    """The Fang Gu killed an Outsider, and they took its place.

    Not a death and a replacement: the Outsider *lives*, turns evil and
    becomes the Fang Gu, and the old one dies instead. So the table sees
    exactly one body — the Demon's own seat — which is why this belongs
    with the handovers rather than with the kills.

    Once per game. The new Fang Gu cannot jump again, so this is offered
    only while the star is still where it was dealt.
    """
    if character != "FangGu" or phase[0].upper() != "N":
        return []
    # Once per game — asked of the jump itself, not of whether the star
    # has moved at all. A Snake Charmer swap moves it too, and was read
    # as the jump already spent (29.09.2026). A jump leaves one mark: an
    # evil Fang Gu written onto a seat that was dealt an Outsider.
    # Earlier than this moment only: a story built a night at a time
    # already holds this very jump when it is asked again later.
    if any(c.role == "FangGu" and c.side == "evil"
           and TEAM[view.roles[c.seat]] == "outsider"
           and phase_index(c.phase) < phase_index(phase)
           for c in getattr(view, "changes", ())):
        return []                         # it has already jumped once
    alive = state.alive_set(phase)
    return [Change(phase, seat, "FangGu", "evil")
            for seat in range(state.n_players)
            if seat in alive and view.team_at(seat, phase) == "outsider"]


@heir_rule
def the_scarlet_woman_steps_up(view, state, phase, character):
    """The Demon killed in daylight, with her standing by."""
    if phase[0].upper() == "N":
        return []
    if not scarlet_woman_takes_over(view, state, phase):
        return []
    return [Change(phase, view.find_at("ScarletWoman", phase), character)]


@transition_rule
def a_barber_lets_the_demon_swap_two(world, state):
    """The Barber died today, so tonight the Demon may swap two players.

    Characters only — a swapped player keeps their side, so a good player
    can end up holding a Minion's character. Rare, and legal, and the
    reason `Change` has kept its two halves separate all along.

    Anchored to the Barber's death, which is the rule every transition
    here follows: something on the record has to have happened. Without
    that anchor this would be "any two seats on any night", which is the
    shape that multiplies the search for stories nothing is asking for.

    A "may", so doing nothing is always among the answers — and it comes
    first, because it is what usually happened.
    """
    if not _in_bag(state, "Barber"):
        return [((), 1.0)]
    # Its offers depend only on the board it is shown, and a night-by-night
    # solve shows it the same board once for every story it already made
    # — fifty-odd times on a ten-seat table. Kept per deal and per exact
    # set of changes; the offers are never changed by whoever reads them.
    base = world.world if isinstance(world, Timeline) else world
    memo = _memo_for(base, "_barber_memo", state)
    key = tuple(getattr(world, "changes", ()))
    got = memo.get(key)
    if got is None:
        got = memo[key] = _barber_offers(world, state)
    return list(got)


def barber_claimants(state):
    """Seats that said they were the Barber — as their claim, or in a
    row saying they became it or had been it.

    **A swap is only considered once one of them has died** (table
    ruling, 29.09.2026). A Barber's death offers every pair of seats,
    fifty-odd stories each explained in full, and a Barber nobody claimed
    is a death the table has no reason to read as one. The price: a
    Barber who hid behind another claim, died, and whose Demon really
    swapped leaves a board the solver cannot explain.

    Opening the swap to every dead seat once somebody reports an
    unexplained change of character was tried and measured (30.09.2026):
    it rescued none of the lost games and made the reported ones worse —
    a swap touches two seats and usually only one of them says so. Kept on
    the branch `barber-trigger-experiment`.
    """
    out = {seat for seat, role in (state.claims or {}).items()
           if role == "Barber"}
    for info in state.infos:
        if isinstance(info, BecameInfo) and "Barber" in (info.role, info.was):
            out.add(info.player)
    return out


def _barber_offers(world, state):
    """Every swap the Demon could make for each Barber death, and none."""
    # Whoever was the Barber when they died — dealt one, or made one by a
    # Pit-Hag. Only the dealt one was looked for, so a Pit-Hag's Barber
    # that was executed swapped nothing (29.09.2026). And only a seat that
    # claimed it: see `barber_claimants`.
    claimed = barber_claimants(state)
    deaths = [(seat, phase) for seat in range(state.n_players)
              if seat in claimed
              for phase in state.died_at(seat)
              if world.role_at(seat, phase) == "Barber"]
    if not deaths:
        return [((), 1.0)]

    stories = [((), 1.0)]
    for _barber, phase in deaths:
        day = int(phase[1:])
        night = f"N{day + 1}" if phase[0].upper() in "DEX" else f"N{day}"
        if phase_index(night) > phase_index(state.final_phase()):
            continue                      # the game had already finished
        view = world
        seats = range(state.n_players)
        demon = view.demon_at(night)
        for first in seats:
            for second in seats:
                if second <= first:
                    continue
                a, b = view.role_at(first, night), view.role_at(second, night)
                if a == b:
                    continue
                # The Demon with one of its own Minions is the usual swap
                # at this table and costs a world nothing; any other pair
                # is a deliberate play priced as one (table habit,
                # 30.09.2026). `_barber_share` splits the credit inside.
                ours = ((first == demon and TEAM[b] == "minion")
                        or (second == demon and TEAM[a] == "minion"))
                kind = DemonMinionSwap if ours else OtherSwap
                # Sides written out, not left to the new character: a
                # Change with no side takes the character's, so a swapped
                # Demon read as a good Flowergirl and an Oracle counting
                # it dead and evil looked wrong (29.09.2026).
                side_a = "evil" if view.evil_at(first, night) else "good"
                side_b = "evil" if view.evil_at(second, night) else "good"
                stories.append(((kind(night, first, b, side_a),
                                 kind(night, second, a, side_b)),
                                1.0 if ours else BARBER_SWAP_PENALTY))
    return stories


class DemonMinionSwap(Change):
    """A Barber swap between the Demon and one of its Minions."""
    __slots__ = ()


class OtherSwap(Change):
    """Any other Barber swap."""
    __slots__ = ()


def _barber_share(world, changes, state):
    """How much of a world's credit a story gets for its Barber swap.

    Two questions, answered apart (table ruling, 30.09.2026). *World
    against world* is the story's cost: a Demon–Minion swap costs
    nothing, any other swap `BARBER_SWAP_PENALTY`. *Inside one world* —
    who is what now — the credit is shared out by what the table does:
    "no swap" gets 1 − `BARBER_SWAP_SHARE`; of the rest, Demon–Minion
    pairs get `BARBER_DEMON_MINION_SHARE` between them and every other
    pair shares what is left, however many pairs there are. Splitting by
    cost alone gave forty-five pairs at 0.15 each nearly nine tenths of
    the credit and the usual swap almost none of it.

    Returned as a factor on the story's cost: the swap's own price is
    taken back out and its share put in.
    """
    swaps = [c for c in changes if isinstance(c, (DemonMinionSwap, OtherSwap))]
    rest = tuple(c for c in changes
                 if not isinstance(c, (DemonMinionSwap, OtherSwap)))
    view = Timeline(world, rest) if rest else world
    counts = {}
    for extra, _cost in a_barber_lets_the_demon_swap_two(view, state):
        if extra:
            ours = isinstance(extra[0], DemonMinionSwap)
            got = counts.setdefault(extra[0].phase, [0, 0])
            got[0 if ours else 1] += 1
    factor = 1.0
    for night, (n_ours, n_other) in counts.items():
        mine = [c for c in swaps if c.phase == night]
        if not mine:
            factor *= 1.0 - BARBER_SWAP_SHARE
            continue
        ours = isinstance(mine[0], DemonMinionSwap)
        if n_ours and n_other:
            part = (BARBER_DEMON_MINION_SHARE if ours
                    else 1.0 - BARBER_DEMON_MINION_SHARE)
        else:
            part = 1.0
        factor *= (BARBER_SWAP_SHARE * part / (n_ours if ours else n_other)
                   / (1.0 if ours else BARBER_SWAP_PENALTY))
    return factor


@transition_rule
def a_pit_hag_makes_somebody_else(world, state):
    """Recorded creations, applied from the night they happened.

    The side is carried over rather than taken from the new character:
    a Townsfolk turned into the Poisoner keeps its own side and gains the
    ability, which is what makes a good Poisoner possible.
    """
    made = [info for info in state.infos
            if getattr(info, "source_role", None) == "PitHag"
            and getattr(info, "role", None)]
    if not made:
        return [((), 1.0)]
    changes = []
    for info in made:
        phase = f"N{info.night}"
        # The side as it stood when the Pit-Hag acted, at slot 16 — not
        # after a Fang Gu jumped into the same seat later that night,
        # which is what a story built a night at a time shows it on the
        # next pass (29.09.2026).
        before = _before(info.night, phase)
        side = "evil" if world.evil_at(info.target, before) else "good"
        changes.append(Change(phase, info.target, info.role, side))
    return [(tuple(changes), 1.0)]


def _could_be_good(world, seat, phase):
    """Could this seat have shown as good, if the Storyteller liked?

    Registration, not truth. A Spy is evil and registers as good, so the
    Storyteller may hand it the Farmer on that basis — and it stays evil.
    An evil Farmer is a real thing, the same shape as a Pit-Hag creation
    keeping its own side.
    """
    if not world.evil_at(seat, phase):
        return True
    role = world.role_at(seat, phase)
    return bool({"townsfolk", "outsider"} & CHARACTERS[role].registers)


@transition_rule
def a_farmer_hands_it_on(world, state):
    """It died in the night, so somebody good becomes the Farmer.

    Anchored to the death, like every transition here: something on the
    record has to have happened. **Any** night death does it — a Gossip
    kill, an Assassin, a Pukka's poison — not only the Demon's, which is
    what separates this from the Grandmother's grief.

    Not on an execution, and not while droisoned: a droisoned
    *information* role yields whatever the Storyteller likes, because the
    information is arbitrary, but a plain ability simply does not
    function. Handing the character on is a plain ability.

    **Chosen by registration, and the side does not move.** A Spy
    registers as good, so a Spy may be made the Farmer — and stays evil.
    An evil Farmer is a real thing this has to be able to represent,
    which is the same shape as a Pit-Hag creation keeping its own side.

    It chains: the new Farmer is a new instance, so if it too dies at
    night the character is handed on again.
    """
    if not _in_bag(state, "Farmer"):
        return [((), 1.0)]

    stories = [((), 1.0)]
    latest = phase_index(state.final_phase())
    night = 0
    while True:
        night += 1
        phase = f"N{night}"
        if phase_index(phase) > latest:
            break
        # Asked of each story so far, not of the bare world. It chains —
        # the new Farmer is a new instance — so a heir made on night two
        # can hand it on again on night three, and the seat holding it
        # differs from story to story.
        grown = []
        for changes, cost in stories:
            view = Timeline(world, changes) if changes else world
            # Every seat holding it, not the first one found.
            #
            # `find_at` returns the earliest, which is the Farmer that
            # was *dealt* — and it goes on being a Farmer in the base
            # world after it dies, so the chain never looked past it. The
            # heir made on night two was invisible on night three.
            holders = [p for p in range(state.n_players)
                       if view.role_at(p, phase) == "Farmer"
                       and phase in state.died_at(p)]
            if not holders:
                grown.append((changes, cost))
                continue
            seat = holders[0]
            after = f"D{night}"
            heirs = [p for p in state.alive_set(phase)
                     if p != seat and _could_be_good(view, p, phase)]
            # "Nothing happened" stays among the answers, and it is the
            # droisoned case: a droisoned Farmer's ability does not
            # function, so the character is not handed on at all.
            #
            # It cannot be decided here. Whether a seat was droisoned is
            # *chosen* as part of the explanation — that is what the
            # impairment plan is for — and transitions are settled before
            # it runs. So both stories are offered and the plan pays for
            # whichever it needs, the same shape as the Barber's "may".
            grown.append((changes, cost))
            for heir in heirs:
                grown.append((changes + (Change(after, heir, "Farmer", None),),
                              cost))
        stories = grown[:48]
    return stories


def _evil_to_the_ogre(view, seat, phase):
    """Would this seat hand an Ogre the evil side?

    Its true side — and the jinx on top: "the Spy and the Recluse
    register as evil to the Ogre". Not a Storyteller's choice as with
    other readings: the Recluse *does* register evil here. Asked of the
    catalogue rather than by name, so any character that can register as
    a Minion or Demon counts.
    """
    if view.evil_at(seat, phase):
        return True
    return bool({"minion", "demon"}
                & CHARACTERS[view.role_at(seat, phase)].registers)


@transition_rule
def an_ogre_picks_a_side(world, state):
    """On its first night the Ogre takes the side of whoever it chose.

    "Even if drunk or poisoned", so nothing can stop it, and it is never
    told which side it landed on — an evil Ogre plays exactly like a good
    one. Only the side moves, never the character: `Change` with no role.

    Written from the first **day**, not the night. The Ogre acts late on
    night one, after the Empath, the Noble and the Grandmother, so their
    first readings still see it good.

    Two stories when the choice was not written down. Staying good costs
    nothing; turning evil is weighed by the table — evil seats against
    good ones, with the Recluse counted as evil — because an Ogre that
    points at somebody at random lands on each side about that often.
    When the Ogre said whom it chose, and it really is the Ogre in this
    world, there is one story and no weighing.
    """
    if not _in_bag(state, "Ogre"):
        return [((), 1.0)]
    ogre = world.find_at("Ogre", "N1")
    if ogre is None:
        return [((), 1.0)]
    turn = (Change("D1", ogre, None, "evil"),)

    picked = [info for info in state.infos
              if getattr(info, "source_role", None) == "Ogre"
              and info.player == ogre]
    if picked:
        target = picked[0].target
        if target == ogre:
            return []                     # "not yourself"
        return [(turn, 1.0)] if _evil_to_the_ogre(world, target, "N1") \
            else [((), 1.0)]

    others = [p for p in range(state.n_players) if p != ogre]
    evil = sum(1 for p in others if _evil_to_the_ogre(world, p, "N1"))
    good = len(others) - evil
    if good == 0:
        return [(turn, 1.0)]
    return [((), 1.0), (turn, min(1.0, evil / good))]


@transition_rule
def a_snake_charmer_takes_the_star(world, state):
    """Choosing the Demon swaps character and side, both ways.

    The only handover where the star moves *sideways* rather than on:
    the Snake Charmer becomes the Demon, and the Demon becomes a good
    Snake Charmer — poisoned from that moment for the rest of the game,
    which is what the impairment rule below is for.

    Anchored to a recorded choice, so nothing is enumerated. A choice
    that swapped says so, and the row that says it did not is checked as
    an ordinary reading instead.
    """
    swaps = [info for info in state.infos
             if getattr(info, "source_role", None) == "SnakeCharmer"
             and getattr(info, "swapped", False)]
    if not swaps:
        return [((), 1.0)]

    stories = [((), 1.0)]
    base = world
    for info in sorted(swaps, key=lambda i: i.night):
        # Each swap sees the ones before it. Two swaps in a game — a
        # charmer takes the star, and later a Philosopher working the
        # Snake Charmer takes it from them — were each judged against the
        # board with no swap at all, and the second found the Demon where
        # it had been dealt (29.09.2026).
        so_far = stories[0][0] if stories else ()
        world = Timeline(base, so_far) if so_far else base
        # Who acted, which is the board as it stood when the night
        # *began* — not after the swap this rule is about to write.
        #
        # The swap is dated at the night now that it is immediate, so
        # asking `find_at` at that phase finds the seat the character
        # ended up at rather than the seat that pointed. The charmer's
        # own row then read as invented, and a world where the swap could
        # really have happened scored 0.4 against 1.0 for one where it
        # could not. That symptom was recorded here for a long time and
        # paid for by dating the swap a phase late; this is the actual
        # cause.
        phase = f"N{info.night}"
        before = _before(info.night, phase)
        # Held, or a Philosopher working it — nobody *holds* the character
        # then, and the swap plainly happened.
        #
        # **The seat that said so, if it has the ability.** With a
        # Philosopher that took the Snake Charmer there are two seats
        # with it — the Philosopher and the real one it made drunk — and
        # asking for "whoever works it" found the drunk one first. The
        # swap landed on the wrong seat and the real Demon was nowhere
        # (29.09.2026).
        charmer = (info.player
                   if _has_ability(world, state, info.player,
                                   "SnakeCharmer", before)
                   else _whoever_works(world, state, "SnakeCharmer", before))
        demon = world.demon_at(before)
        if charmer is None or demon is None or charmer == demon:
            continue
        if info.target != demon:
            continue                      # they pointed at somebody else
        # Applied from the night, because the swap is immediate.
        #
        # Settled at the table: a Snake Charmer acts at slot 11 and every
        # Demon at 24 or later, so by the time the night's kill is made
        # the charmer is holding the Demon — and it is the charmer's seat
        # that kills. The old Demon is a poisoned good Snake Charmer and
        # kills nobody.
        #
        # This was written at the *day* after for a real reason, which is
        # worth keeping in view: writing it at the night made the speaker
        # stop holding the Snake Charmer at the very moment its own row is
        # attributed, so the row read as invented, and a world where the
        # swap could really have happened scored 0.4 against 1.0 for one
        # where it could not. Exactly backwards.
        #
        # The fix for *that* is that a row is attributed to whoever held
        # the character when it acted, which is slot 11 — before the
        # swap. Attribution asks about the moment of acting, and the
        # board asks about the moment after; they are different questions
        # and the phase alone cannot tell them apart. Another instance of
        # a phase not being an instant.
        after = f"N{info.night}"
        # The character the Demon held **when the swap happened**, which
        # is slot 11 — not whatever it holds by the end of the night.
        #
        # Read at `phase` this took the board *after* the rules that run
        # before this one. A Pit-Hag acts at slot 16 and its rule runs
        # first, so on a night with both, the charmer was handed
        # *Innkeeper* instead of the Demon's character: two Innkeepers,
        # no Demon on the board from that night on, no cause for any
        # night kill, and the whole board refused.
        #
        # `before` was already being computed to find *who* the Demon is,
        # and correctly. It simply was not used for *what* to copy.
        stories = [(changes + (Change(after, charmer,
                                      world.role_at(demon, before), "evil"),
                               Change(after, demon, "SnakeCharmer", "good")),
                    cost)
                   for changes, cost in stories]
    return stories


@impairment.source_rule
def a_swapped_snake_charmer_is_poisoned_for_good(world, state, night):
    """Whoever became the Snake Charmer by the swap, from then on.

    The new Demon is untouched; it is the *new Snake Charmer* — the old
    Demon — that is poisoned, and permanently. Free, because nothing had
    to go right for it.
    """
    if not _in_bag(state, "SnakeCharmer"):
        return []
    out = []
    for info in state.infos:
        if getattr(info, "source_role", None) != "SnakeCharmer":
            continue
        if not getattr(info, "swapped", False):
            continue
        # From the day after the swap, which is when it took effect.
        if phase_index(f"N{night}") < phase_index(f"D{info.night}"):
            continue
        # The old Demon — the seat it pointed at — rather than the first
        # seat holding a Snake Charmer, which can be the real one a
        # Philosopher made drunk.
        seat = info.target
        # The *player* is poisoned, whatever they hold later — a Pit-Hag
        # that turned the swapped Snake Charmer into a Sweetheart left
        # them poisoned all the same (29.09.2026). Only in a story where
        # the swap happened, which is the change written on that seat.
        if not any(c.seat == seat and c.role == "SnakeCharmer"
                   and c.phase == f"N{info.night}"
                   for c in getattr(world, "changes", ())):
            continue
        out.append(impairment.Source("Snake Charmer", frozenset({seat}),
                                     capacity=1, cost=1.0, repeat_cost=1.0))
    return out


@transition_rule
def demon_handovers(world, state):
    """The Demon dying, as a transition rule.

    A starpass is not charged for: the Demon's own seat dying at night is
    already discounted hard by the night-death prior, and billing it twice
    would be double-counting.
    """
    return [(chain, 1.0) for chain in demon_lineages(world, state)]


def _executed(state, day, seat):
    """Was this seat executed on this day — by any route the rules call
    an execution?

    The town's vote, a Virgin's nominator ("is executed immediately") and
    a Cerenovus's madness. Not a Slayer's shot, a Witch's curse or a
    Tinker going of its own accord: those are deaths in daylight, and the
    Mastermind asks for an *execution*.
    """
    if state.executed_on(day) == seat:
        return True
    if (getattr(state, "madness_executions", None) or {}).get(day) == seat:
        return True
    return any(isinstance(info, VirginNomination) and info.triggered
               and info.night == day and info.nominator == seat
               for info in state.infos)


def _mastermind_day(world, state, phase, holder):
    """Could play have carried on with no Demon at all?

    "If the Demon dies by execution (ending the game), play for 1 more
    day." So only after an **execution** — a Slayer's shot ends the game
    as it always did — only with the Mastermind alive, and only for one
    more day: a board that runs on past that is not what happened.

    Whether the Mastermind was *working*, and whether a Scarlet Woman
    should have taken over instead, are questions for the impairment plan
    and are asked in `_plain_failures`, where the story is recognised by
    its marker.
    """
    if not _in_bag(state, "Mastermind") or phase[0].upper() != "D":
        return False
    day = int(phase[1:])
    if not _executed(state, day, holder):
        return False
    seat = world.find_at("Mastermind", phase)
    if seat is None or seat not in state.alive_set(phase):
        return False
    latest = phase_index(state.final_phase())
    return latest <= phase_index(f"D{day + 1}")


def mastermind_marker(phase, seat):
    """The mark a Mastermind's extra day leaves in a story.

    A change that changes nothing — no character, no side — on the Demon
    that was executed. Nothing else writes one, so it is unambiguous, and
    because it moves nothing it needs no special case anywhere a story is
    read. `_plain_failures` looks for it to ask what the day needs.
    """
    return Change(phase, seat, None, None)


def is_mastermind_marker(change):
    return change.role is None and change.side is None


def demon_lineages(world, state, cap=24):
    """Every way the Demon could have changed hands in this world.

    The timing is not a free choice — it is pinned by the deaths already
    on the record. A Demon dead at night killed itself, and the star has
    to land on a living Minion. A Demon killed in daylight ends the game
    outright unless the Scarlet Woman was standing by, so a death like
    that on the record means she took over.

    Only the recipient is ever open, and usually not even that: she takes
    priority whenever her own condition holds. Chains are handled by
    walking on — an heir who dies later hands it on again.

    Returns a list of handover tuples. Empty means no story fits, and the
    world is impossible.
    """
    start = world.demon_at("N1")
    if start is None:
        return [()]

    found = []

    def walk(view, holder, so_far, after=-1, held=frozenset()):
        if len(found) >= cap:
            return
        # A seat that stopped being the Demon before it died hands
        # nothing on. A Snake Charmer swap moves the Demon to the
        # charmer's seat and leaves a *good* Snake Charmer behind — and
        # when the new Demon later kills that seat, this walk was still
        # tracking it as the holder, looked for an heir, found none, and
        # declared the whole world impossible.
        phases = state.died_at(holder)
        # A Zombuul's first death is not one. It registers dead and goes
        # on killing, so the star has not moved and nobody inherits; only
        # the second death is real. Reading the first as final made every
        # board with an executed Zombuul impossible — nobody could take
        # over, so no story fitted. Found with the Mastermind, whose
        # third wiki example is exactly this Zombuul executed twice.
        if phases and view.role_at(holder, phases[0]) == "Zombuul":
            phases = phases[1:]
        # Not yet, on a pass that only looks this far (possible_timelines).
        horizon = getattr(state, "_horizon", None)
        if horizon is not None:
            phases = [p for p in phases if int(p[1:]) <= horizon]
        phase = phases[0] if phases else None
        # Moved sideways before it died — or before the board ends, if it
        # never did. A Snake Charmer swap hands the star across without a
        # death, and the walk stopped there: whoever the charmer became
        # was never walked, so when *that* Demon died — a Fang Gu jumping
        # into an Outsider, an execution — nobody could inherit and the
        # world was impossible (29.09.2026). Follow the star instead.
        check = phase if phase is not None else (
            f"D{horizon}" if horizon is not None else state.final_phase())
        if view.role_at(holder, check) is not None \
                and TEAM[view.role_at(holder, check)] != "demon":
            successor = view.demon_at(check)
            if successor is not None and successor != holder \
                    and successor not in held:
                walk(view, successor, so_far, after, held | {holder})
                return
            found.append(so_far)
            return
        # A handover has to happen *later* than the one before it, and no
        # seat can hold the star twice. Both were true by construction
        # until a Barber let the Demon swap characters around: with two
        # seats trading, the star could be handed back to somebody who
        # had already had it and the walk went round for ever. The stack
        # ran out before anything noticed.
        # Strictly *earlier* is impossible; the same phase is not. A
        # Shabaloth kills twice in a night, so the Demon and its heir can
        # both fall at once and the star passes on again — reading this
        # as "no later than" ended those lineages early and quietly
        # added worlds to two Bad Moon Rising boards.
        if phase is not None and (phase_index(phase) < after
                                  or holder in held):
            found.append(so_far)
            return
        if phase is None:
            found.append(so_far)          # they held it to the end
            return
        character = view.role_at(holder, phase)
        moves = []
        for rule in HEIR_RULES:
            moves.extend(rule(view, state, phase, character))

        # A Mastermind buys one more day after the Demon is executed.
        # Nobody inherits — there simply is no Demon after this — so the
        # lineage ends here rather than continuing, and the nights that
        # follow have no Demon kill to explain. Marked, so the plan can be
        # told what that day needs.
        if _mastermind_day(view, state, phase, holder):
            found.append(so_far + (mastermind_marker(phase, holder),))

        # No offers at all, and no Mastermind, means good won right there
        # and there is no story to tell about what came after.
        for move in moves:
            if move.seat is None:
                continue
            grown = so_far + (move,)
            walk(Timeline(world, grown), move.seat, grown,
                 phase_index(phase), held | {holder})

    walk(world, start, ())
    return found


# Demons with a kill rule of their own. A Demon not named here kills the
# ordinary way, which is the right default: an unmodelled Demon that
# cannot kill would make every board it appears on impossible, while an
# unmodelled Demon that kills once a night is merely incomplete.
KILLS_ITS_OWN_WAY = set()


def kills_its_own_way(*names):
    """Say that these Demons are handled by a rule of their own."""
    KILLS_ITS_OWN_WAY.update(names)


kills_its_own_way("Zombuul", "Pukka", "Shabaloth", "Po")


@death_causes.cause_rule
def the_demon_kills(world, state, night):
    """The one cause Trouble Brewing has.

    It fires every night from the second, whether or not anybody wants it
    to, and it can aim anywhere — including at a corpse, which is how a
    Demon bluffing protection buys itself a quiet night.
    """
    if night < 2:
        return []                         # nobody dies on the first night
    demon = world.demon_at(f"N{night}")
    if demon is None:
        return []
    # Each Demon that kills differently has its own rule below, and says
    # so by registering its name. Everything else kills the ordinary way.
    #
    # This used to name the Imp instead, which quietly meant "no Demon on
    # any script but Trouble Brewing and Bad Moon Rising can kill at
    # all". Recording a night death on a third script made every world
    # impossible — an ordinary board reading as a contradiction, which is
    # much worse than a Demon whose special trick is not modelled yet.
    if world.role_at(demon, f"N{night}") in KILLS_ITS_OWN_WAY:
        return []
    if demon not in state.alive_set(f"N{night}"):
        return []                         # it was not standing to do it
    # The Demon may have been stopped at its source — a poisoned Imp kills
    # nobody — but only offered when something tonight could reach it.
    # Offered blindly it was a dead end on every quiet night of a board
    # with no Poisoner, and `_night_accounts` keeps only the first 24
    # combinations: five quiet nights of dead ends crowded out the one
    # real story, an Imp aiming at corpses, and a legal game read as
    # impossible.
    reachable = any(demon in source.seats
                    for source in impairment.sources_on(world, state, night))
    # Not on a night a Sweetheart dies. The Demon kills her working, and
    # her drunkenness can land on the Demon the moment she falls — still
    # tonight, before the later readings. The plan knows whole nights, so
    # "working" and "drunk" on one night read as a contradiction, and a
    # Vortox that killed its Sweetheart made the board impossible
    # (29.09.2026). Left unasked tonight: permissive, never wrong.
    if any(f"N{night}" in state.died_at(p)
           and world.role_at(p, f"N{night}") == "Sweetheart"
           for p in range(state.n_players)):
        reachable = False
    return [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON,
        seats=frozenset(range(state.n_players)),   # a corpse is a valid aim
        capacity=1, must_fire=True,
        actor=demon if reachable else None,
        actor_cost=DEMON_POISONED_PENALTY)]


@death_causes.immunity_rule
def the_soldier_cannot_be_demon_killed(world, state, night, seat, kind):
    if not _in_bag(state, "Soldier"):
        return []
    if kind != death_causes.DEMON:
        return []
    if world.role_at(seat, f"N{night}") != "Soldier":
        return []
    # Only while working — a poisoned Soldier dies like anybody else.
    return [death_causes.Shield("Soldier", needs=seat)]


@death_causes.immunity_rule
def the_monk_guards_against_the_demon(world, state, night, seat, kind):
    if not _in_bag(state, "Monk"):
        return []
    if kind != death_causes.DEMON:
        return []
    # Every night but the first, like the Innkeeper and the Exorcist.
    if night < 2:
        return []
    phase = f"N{night}"
    monk = world.find_at("Monk", phase)
    if monk is None or monk == seat or monk not in state.alive_set(phase):
        return []
    return [death_causes.Shield("Monk", needs=monk, chosen=True)]


# --------------------------------------------------------------------------
# Bad Moon Rising, so far
# --------------------------------------------------------------------------

# Ways of walking away from your own execution. Trouble Brewing has none,
# so an execution recorded as survived there is not a world at all. The
# Sailor is the first; a Devil's Advocate will be the second, and the two
# are told apart by which seat had to be working.
SURVIVES_EXECUTION_RULES = []


def survives_execution_rule(fn):
    SURVIVES_EXECUTION_RULES.append(fn)
    return fn


def survivals_of(world, state, day, seat, but=None):
    out = []
    for rule in SURVIVES_EXECUTION_RULES:
        if rule is not but:
            out.extend(rule(world, state, day, seat))
    return out


def _walked_away(state, day, seat):
    """Was this seat executed that day and left standing?"""
    return (state.executions or {}).get(day) == seat \
        and state.execution_death(day) is None


@survives_execution_rule
def a_devils_advocate_saves_from_the_gallows(world, state, day, seat):
    """The gallows only. It chose somebody last night, and if the town
    executes them today they walk away — but nothing else about their day
    changes, so a Tinker it protected can still go of its own accord.
    """
    if not _in_bag(state, "DevilsAdvocate"):
        return []
    phase = f"N{day}"
    advocate = world.find_at("DevilsAdvocate", phase)
    if advocate is None or advocate not in state.alive_set(phase):
        return []
    # "Different to last night": it cannot keep the same player from the
    # gallows two days running. If they walked away yesterday too and
    # nothing but the Advocate could have managed that, it was spent on
    # them then.
    if _walked_away(state, day - 1, seat) and not survivals_of(
            world, state, day - 1, seat,
            but=a_devils_advocate_saves_from_the_gallows):
        return []
    return [advocate]


@survives_execution_rule
def a_pacifist_may_spare_the_good(world, state, day, seat):
    """Some executed good players do not die — the Storyteller decides.

    A choice rather than a rule, so an executed good player who *did* die
    proves nothing. It only ever explains a survival.
    """
    if not _in_bag(state, "Pacifist"):
        return []
    phase = f"D{day}"
    pacifist = world.find_at("Pacifist", phase)
    if pacifist is None or pacifist not in state.alive_set(phase):
        return []
    if world.evil_at(seat, phase):
        return []                         # only the good are spared
    return [pacifist]


def _died_between(state, seat, since, night):
    """Did this seat die after night `since` began and before `night` did?

    The lifetime of an ability. Whatever a character set going on night
    `since` is over by `night` if it has been dead in between, whether or
    not it is standing again.
    """
    return any(phase_index(f"N{since}") <= phase_index(at)
               < phase_index(f"N{night}") for at in state.died_at(seat))


def _returned_at(state, phase):
    """Who came back to life at this moment."""
    return frozenset(seat for seat, phases
                     in (state.resurrections or {}).items()
                     if phase in phases)


def _rosters(state, phase):
    """Who was alive at this moment — which, on a night somebody came
    back, has two answers.

    A return is dated to a night, and a night is seventy-odd slots long.
    A Shabaloth regurgitates just before it chooses; a Professor raises
    at 43, after every Demon has been and gone. So whoever came back
    tonight was dead for the first part of it and alive for the rest, and
    nothing on the board says where the line fell. Anything that depends
    on who was standing has to hold both ways before it may be demanded.
    """
    alive = state.alive_set(phase)
    back = _returned_at(state, phase)
    return [alive, alive - back] if back else [alive]


def _tea_lady_keeping(world, state, seat, phase, alive=None):
    """The Tea Lady whose protection covers this seat right now, if any.

    Both her living neighbours good, and this seat one of them. Asked of
    a phase, because who is living beside her changes as people die —
    and it is asked at night and in daylight alike.
    """
    if alive is None:
        alive = state.alive_set(phase)
    lady = world.find_at("TeaLady", phase)
    if lady is None or lady not in alive:
        return None
    around = _living_beside(state, lady, phase, alive)
    # One other player left alive is her neighbour on both sides, and
    # "both your alive neighbours are good" is true of them. This wanted
    # two different seats, so the last player standing beside her could
    # be executed and die (03.10.2026 — a Zombuul under its shroud, a
    # Fool and a Tea Lady, in a game that ran six nights).
    if seat not in around:
        return None
    if any(world.evil_at(p, phase) for p in around):
        return None                       # one of them is evil, so nothing
    return lady


def _beside_a_side_nobody_knows(world, state, lady, phase, alive=None):
    """Is one of her living neighbours on a side that can turn?

    A Goon is on whichever side last chose it, and nobody writes that
    down. With one beside her she may be protecting and she may not, and
    the board cannot say — so her protection can explain somebody living
    and a death beside her proves nothing about her (03.10.2026, the
    first played games in which a Goon turned).
    """
    return any(CHARACTERS[world.role_at(p, phase)].alignment_open
               for p in _living_beside(state, lady, phase, alive))


@survives_execution_rule
def a_tea_lady_keeps_her_neighbours_from_the_gallows(world, state, day,
                                                     seat):
    """ "Cannot die" means cannot die: the gallows as much as the Demon.

    Her night-time protection has been here since she went in and the
    daylight half never was — so a neighbour executed and left standing
    had nothing to explain it, and the world that really happened was
    not a world (02.10.2026, found reading every character against the
    rulebook).
    """
    if not _in_bag(state, "TeaLady"):
        return []
    lady = _tea_lady_keeping(world, state, seat, f"D{day}")
    return [] if lady is None else [lady]


@survives_execution_rule
def a_fool_walks_away_once(world, state, day, seat):
    """Its one free death covers the gallows as well as the night."""
    if not _in_bag(state, "Fool"):
        return []
    if world.role_at(seat, f"D{day}") != "Fool":
        return []
    # Once. An earlier walk from the gallows that nothing else explains
    # was the Fool's one free death, and it is gone.
    #
    # Unless it has been dead and back since. "The regurgitated player
    # regains their ability, even a once per game ability already used" —
    # and the same for a Professor's. A Fool that walked from the gallows,
    # was taken by the Shabaloth and came back walks again (03.10.2026).
    for earlier in range(1, day):
        if any(earlier < int(at[1:]) <= day
               for at in (state.resurrections or {}).get(seat, ())):
            continue
        if _walked_away(state, earlier, seat) and not survivals_of(
                world, state, earlier, seat, but=a_fool_walks_away_once):
            return []
    return [seat]


@survives_execution_rule
def a_sober_sailor_walks_away(world, state, day, seat):
    """It cannot die, and that holds in daylight.

    This is the deduction the table can make for itself: execute the
    Sailor, watch it live, and you know it was working — which means the
    person it chose the night before is the one carrying its drunkenness.
    The solver gets there the same way, by demanding the Sailor was
    unimpaired across that span and letting the plan put the drunkenness
    somewhere else.
    """
    if not _in_bag(state, "Sailor"):
        return []
    if world.role_at(seat, f"D{day}") != "Sailor":
        return []
    return [seat]


def _in_bag(state, key):
    """Is this character on the script at all?

    Every rule below asks first. A Trouble Brewing board should not pay
    for scanning the table for a Sailor on every night of every world,
    and this is a set lookup against something already computed.
    """
    cached = getattr(state, "_bag_cache", None)
    if cached is None:
        cached = set(state.script.keys)
        state._bag_cache = cached
    return key in cached


# A Gossip only kills when what it said that day was true, and the table
# hears several people claim Gossip on any given day. So this is a cause
# that may fire rather than one that must, priced for how often a
# statement turns out to be worth a body.
GOSSIP_KILL_PENALTY = 0.4

# A Tinker goes when the Storyteller feels like it, which is not often on
# any particular night.
TINKER_DEATH_PENALTY = 0.3

# One strike for the whole game, so on any given night it is unlikely to
# be the night they spent it.
ASSASSIN_STRIKE_PENALTY = 0.25


def _zombuul_still_going(world, state, seat, phase):
    """A Zombuul is dead on the board before it is dead in fact.

    The first time it would die it does not — but it registers as dead,
    so the table crosses it off while it carries on killing. It is only
    really gone the second time. Nothing else in the game is recorded
    dead and alive at once, which is why this is asked here rather than
    handled by `alive_at`.
    """
    gone = [p for p in state.died_at(seat)
            if phase_index(p) < phase_index(phase)]
    return len(gone) < 2


def _demon_kill_rule(name, kind=None):
    """Shared shape for a Demon's nightly kill."""
    return name


def _could_be_stopped(world, state, seat, night):
    """Could anything have made this seat drunk or poisoned that night?

    A Demon that has to kill and killed nobody may have been stopped at
    its source: it chose the Goon first, a Sailor or an Innkeeper made it
    drunk, a Courtier named it, a Minstrel silenced the town. The four
    Demons of Bad Moon Rising had no such explanation — only "the target
    could not die" — and once played games began telling the solver
    their quiet nights, 83 in 60,000 lost the world that happened
    (04.10.2026).

    Offered only where something could reach it, for the reason the
    ordinary Demon gives: a dead end on every quiet night crowds the
    real account out of the ones that are kept.
    """
    return any(seat in source.seats
               for source in impairment.sources_on(world, state, night))


@death_causes.cause_rule
def a_zombuul_kills_on_a_quiet_day(world, state, night):
    """Only if nobody died during the day before.

    Any death at all stops it — an execution, a Slayer shot, a Tinker
    going of its own accord. And it kills while registered dead, which is
    the whole point of it.
    """
    if not _in_bag(state, "Zombuul") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Zombuul", phase)
    if seat is None or not _zombuul_still_going(world, state, seat, phase):
        return []
    if any(f"D{night - 1}" in state.died_at(who)
           for who in (state.deaths or {})):
        return []                         # somebody went in daylight
    return [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON,
        seats=frozenset(range(state.n_players)), capacity=1, must_fire=True,
        actor=seat if _could_be_stopped(world, state, seat, night) else None,
        actor_kills_working=False)]


@death_causes.cause_rule
def a_pukka_kills_what_it_poisoned(world, state, night):
    """Poisons on one night, and that poison kills on the next.

    It starts a night earlier than any other Demon: on the first night it
    only poisons. From then on it kills whoever it poisoned last night and
    poisons somebody new — so the victim has to be the seat its poison
    was on, which is a demand on a night already accounted for.
    """
    if not _in_bag(state, "Pukka") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Pukka", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    # Three ways a Pukka's night passes without a body besides "the one
    # it poisoned could not die".
    #
    # Drunk or poisoned tonight: it does not attack, and the token stays
    # where it is. That is the actor, as for any Demon.
    #
    # Or it was last night: it poisoned nobody then, so nothing it chose
    # last night can come due. What does come due is the token it left
    # the night before that, which rested — and that player could not
    # die. Or there was no night before that: a Pukka stopped on the
    # first night has nothing due on the second.
    excuses = []
    for back in (1, 2):
        chose = night - 1 - back          # the night the resting token is from
        if any(world.find_at("Pukka", f"N{k}") != seat
               or seat not in state.alive_set(f"N{k}")
               or not _could_be_stopped(world, state, seat, k)
               for k in range(max(chose, 0) + 1, night)):
            break
        demands = tuple((k, seat) for k in range(max(chose, 0) + 1, night))
        if chose < 1:
            excuses.append((None, demands))
            break
        if world.find_at("Pukka", f"N{chose}") != seat \
                or seat not in state.alive_set(f"N{chose}"):
            break
        excuses.append((frozenset(state.alive_set(f"N{chose}")), demands))
    out = [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON,
        seats=frozenset(state.alive_set(f"N{night - 1}")),
        capacity=1, must_fire=True, victim_impaired_at=night - 1,
        actor=seat if _could_be_stopped(world, state, seat, night) else None,
        actor_kills_working=False, excuses=tuple(excuses))]
    # A night late, or two. A drunk or poisoned Pukka does not attack and
    # its token stays where it is (the flowchart), and the poison rests
    # while it does (table ruling, 02.10.2026). So the one it poisoned on
    # night two was sober through night three and died on night four —
    # which, read the plain way, needs them poisoned on a night they were
    # demonstrably working: a Tea Lady who kept her neighbour from the
    # gallows that day, a Professor who raised somebody.
    #
    # The same kill under the same name, so it shares the one a night;
    # and never owed, since the plain cause already is.
    for late in (1, 2):
        chose = night - 1 - late
        if chose < 1:
            break
        if any(world.find_at("Pukka", f"N{k}") != seat
               or seat not in state.alive_set(f"N{k}")
               for k in range(chose, night)):
            break
        out.append(death_causes.Cause(
            name="Demon", kind=death_causes.DEMON,
            seats=frozenset(state.alive_set(f"N{chose}")),
            capacity=1, victim_impaired_at=chose,
            also_impaired=tuple((k, seat) for k in range(chose + 1, night))))
    return out


@death_causes.cause_rule
def a_shabaloth_kills_twice(world, state, night):
    """Two a night, and it may bring one of them back.

    Either kill can be aimed at somebody already dead, so the table may
    only ever see one body.
    """
    if not _in_bag(state, "Shabaloth") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Shabaloth", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    return [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON,
        seats=frozenset(range(state.n_players)), capacity=2, must_fire=True,
        actor=seat if _could_be_stopped(world, state, seat, night) else None,
        actor_kills_working=False)]


@death_causes.cause_rule
def a_po_kills_none_or_three(world, state, night):
    """It may choose nobody — and then it takes three the next night.

    Whether it chose nobody is not written down, so a night with no
    bodies is read as it possibly having declined. That is permissive
    rather than exact: a Po that sank a kill into a corpse also leaves no
    body, and this lets it have three tonight when it should have one. It
    errs towards keeping worlds rather than throwing them away.
    """
    if not _in_bag(state, "Po") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Po", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    # A Po charges by taking **nobody**, and then takes three.
    #
    # This asked whether *anybody* died last night, which is a different
    # question: a Tinker that simply went, or an Acrobat that fell, or a
    # Gambler that guessed wrong, all die without the Po lifting a
    # finger. One of those on the charging night made the solver offer a
    # capacity of one against a record of three, and the board had no
    # legal world.
    #
    # Whether the Po killed cannot be read off the deaths, because the
    # deaths are what is being explained. So both capacities are offered
    # and the search decides — which is what `must_fire=False` was always
    # for.
    # One cause, with the larger capacity.
    #
    # Two causes broke a standing rule the tests hold: exactly one Demon
    # rule answers for any world. A capacity is a *ceiling* — the search
    # may use fewer — so offering three covers taking one as well, and
    # the shape stays what everything else expects.
    #
    # Except on the second night. Three is for the night after it chose
    # nobody, and the first night is not a choice — so its first kill is
    # always a single one.
    return [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON,
        seats=frozenset(range(state.n_players)),
        capacity=1 if night == 2 else 3, must_fire=False)]


def _pit_hag_made_a_demon(state, night):
    """Did a recorded creation make a Demon on this night?"""
    for info in state.infos:
        if getattr(info, "source_role", None) != "PitHag":
            continue
        role = getattr(info, "role", None)
        if role and info.night == night and TEAM.get(role) == "demon":
            return True
    return False


@death_causes.cause_rule
def a_pit_hag_making_a_demon_makes_deaths_arbitrary(world, state, night):
    """A Demon was created, so tonight's deaths are the Storyteller's.

    Nought to everybody, and no shield touches them — the same shape as
    the Assassin, and for the same reason: the rule says deaths *are*
    arbitrary rather than that somebody kills. A Storyteller will usually
    take the old Demon and one more to signal the change, but that is a
    habit rather than a rule and the solver should not insist on it.

    These are the Pit-Hag's, not the Demon's, so a Grandmother's
    grandchild lost to one leaves her standing and a Soldier is no safer
    than anybody else.
    """
    if not _in_bag(state, "PitHag") or not _pit_hag_made_a_demon(state, night):
        return []
    return [death_causes.Cause(
        "Pit-Hag", death_causes.OTHER, frozenset(range(state.n_players)),
        capacity=state.n_players, cost=1.0, unstoppable=True)]


@death_causes.cause_rule
def a_gossip_may_kill(world, state, night):
    """A second way to die at night, and not the Demon's.

    Which matters more than it sounds: a Soldier is safe from the Demon
    and not from this, and a grandchild lost to it leaves the Grandmother
    standing.

    The Storyteller may sink it into somebody already dead, exactly as
    with the Demon's kill, so it can also come to nothing.
    """
    if not _in_bag(state, "Gossip") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Gossip", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    return [death_causes.Cause(
        name="Gossip", kind=death_causes.OTHER,
        seats=frozenset(range(state.n_players)),
        capacity=1, cost=GOSSIP_KILL_PENALTY, must_fire=False)]


@death_causes.cause_rule
def a_godfather_answers_an_outsider(world, state, night):
    """An Outsider lost in *daylight*, and the Godfather kills tonight.

    Daylight specifically. An Outsider taken in the night triggers
    nothing, which is a clean piece of deduction for the table.

    Whether the seat that died was an Outsider is a question about the
    world, not about the board — nobody knows a character until they do —
    so this fires in the worlds where it holds and not in the others.

    Mandatory, but it can be aimed at somebody already dead, so it need
    not leave a body. And it is not the Demon's kill: a grandchild lost
    to it leaves the Grandmother standing.
    """
    if not _in_bag(state, "Godfather") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Godfather", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    day = f"D{night - 1}"
    lost = any(day in state.died_at(who)
               and world.team_at(who, day) == "outsider"
               for who in (state.deaths or {}))
    if not lost:
        return []
    return [death_causes.Cause(
        name="Godfather", kind=death_causes.OTHER,
        seats=frozenset(range(state.n_players)), capacity=1, must_fire=True,
        # Drunk or poisoned it kills nobody, and so does one that chose
        # the Goon first: a quiet night stopped at its source.
        actor=seat)]


@death_causes.cause_rule
def an_assassin_kills_through_anything(world, state, night):
    """Once per game, and nothing stops it.

    "Dies even if they could not" overrides every shield in the game — a
    Sailor that cannot die, a Fool's free one, a Tea Lady's neighbour, an
    Innkeeper's pair. So a seat killed this way tells you nothing about
    whether its protection was working, which is exactly what
    `unstoppable` means.

    Not the Demon's kill either, so it leaves a Grandmother standing.
    """
    if not _in_bag(state, "Assassin") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Assassin", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    spent = [info.night for info in state.infos
             if getattr(info, "source_role", None) == "Assassin"]
    if spent and night not in spent:
        return []                         # used on some other night
    return [death_causes.Cause(
        name="Assassin", kind=death_causes.OTHER,
        seats=frozenset(range(state.n_players)), capacity=1,
        cost=ASSASSIN_STRIKE_PENALTY, unstoppable=True)]


@death_causes.cause_rule
def a_tinker_may_go_at_any_time(world, state, night):
    """The Storyteller decides, and there is no trigger to wait for.

    Not the Demon's doing, which is why a Monk is no help — it guards
    against the Demon and the Storyteller is not the Demon. A Tea Lady or
    an Innkeeper does stop it, because they guard against everything.
    """
    if not _in_bag(state, "Tinker"):
        return []
    phase = f"N{night}"
    seat = world.find_at("Tinker", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    return [death_causes.Cause(name="Tinker", kind=death_causes.OTHER,
                               seats=frozenset({seat}), capacity=1,
                               cost=TINKER_DEATH_PENALTY)]


@death_causes.cause_rule
def a_moonchild_takes_somebody_with_it(world, state, night):
    """Its pick lands the night *after* it learns it died.

    A player learns they are dead at dawn, or on the spot if it happened
    in daylight, and names somebody there and then — but the rest of it
    resolves the following night. So a Moonchild killed on night two
    reaches out on night three, not night two.

    Only a good target dies. Picking an evil one does nothing at all,
    which is why this may fire rather than must.
    """
    if not _in_bag(state, "Moonchild") or night < 2:
        return []
    phase = f"N{night}"
    child = world.find_at("Moonchild", phase)
    if child is None:
        return []
    # Did it go down in the span before this one?
    if not any(p in (f"N{night - 1}", f"D{night - 1}")
               for p in state.died_at(child)):
        return []
    good = frozenset(seat for seat in state.alive_set(phase)
                     if not world.evil_at(seat, phase))
    # Recorded, it points somewhere in particular — so a seat that died
    # reads good and one that did not reads evil, which is the whole
    # value of writing the pick down.
    #
    # The second half of that was a promise this did not keep. The pick
    # *may* kill when nobody said who it was; once it is written down and
    # the player is good, it **does** — and a good player it named who is
    # still standing needs a reason: somebody keeping them alive, or the
    # Moonchild's ability not working that night. Without that, "they
    # lived, so they are evil" was never drawn (02.10.2026).
    picked = _chosen(state, "Moonchild", night, by=child)
    if picked is None:
        if not good:
            return []
        return [death_causes.Cause(name="Moonchild",
                                   kind=death_causes.OTHER,
                                   seats=good, capacity=1)]
    good = good & picked
    if not good:
        return []                         # it named somebody evil
    # A Goon it named may have been turned by then, and nobody knows:
    # the pick may kill and need not.
    if any(CHARACTERS[world.role_at(seat, phase)].alignment_open
           for seat in good):
        return [death_causes.Cause(name="Moonchild",
                                   kind=death_causes.OTHER,
                                   seats=good, capacity=1)]
    return [death_causes.Cause(name="Moonchild", kind=death_causes.PICKED,
                               seats=good, capacity=1, must_fire=True)]


@death_causes.immunity_rule
def a_moonchild_that_was_not_working(world, state, night, seat, kind):
    """The pick did nothing because the Moonchild's ability did not.

    What counts is its state on the night the pick lands, and the dead
    can be drunk or poisoned like anybody else — a Minstrel, a Courtier,
    a Pukka that would rather its Minion lived. The plan does not reach
    the dead, so this is priced like a poisoning rather than routed
    through it: possible, and it has to be paid for.
    """
    if kind != death_causes.PICKED:
        return []
    return [death_causes.Shield("Moonchild not working", needs=None,
                                cost=POISON_HIT_PENALTY, chosen=True)]


@death_causes.cause_rule
def an_acrobat_may_fall(world, state, night):
    """Its pick was droisoned, so it dies — and nothing else does.

    Reaches exactly its own seat, like the Gambler's. Whether it *did*
    fall is not decided here: that depends on whether the seat it picked
    was impaired, which the impairment plan settles later. This only says
    the death is available to be explained.

    Not a Demon kill, so a Soldier or a Monk is no help. A Tea Lady is,
    because her neighbours cannot die at all — and by the rules a
    prevented ability counts as one that went wrong, so a Mathematician
    sees that.
    """
    if not _in_bag(state, "Acrobat") or night < 2:
        return []
    phase = f"N{night}"
    seat = world.find_at("Acrobat", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    if not any(isinstance(info, AcrobatChoice) and info.night == night
               for info in state.infos):
        return []                         # no pick recorded, no risk
    return [death_causes.Cause(name="Acrobat", kind=death_causes.OTHER,
                               seats=frozenset({seat}), capacity=1,
                               must_fire=False)]


def _has_ability(world, state, seat, role, phase):
    """Does this seat have that ability — held, or taken by a Philosopher?"""
    if world.role_at(seat, phase) == role:
        return True
    taken = (state.philosophies() or {}).get(seat)
    return bool(taken and taken[0] == role
                and world.role_at(seat, phase) == "Philosopher"
                and phase_index(phase) >= phase_index(taken[1]))


def _whoever_works(world, state, role, phase):
    """Who has this ability — held, or gained by a Philosopher.

    **A Philosopher that took a character is that character, ability
    wise, while still registering as a Philosopher.** Settled at the
    table.

    `find_at` only finds a seat *holding* the token; this also finds a
    Philosopher working it.
    """
    seat = world.find_at(role, phase)
    if seat is not None:
        return seat
    for who, (taken, since) in (state.philosophies() or {}).items():
        if taken != role:
            continue
        if world.role_at(who, phase) != "Philosopher":
            continue
        if phase_index(phase) >= phase_index(since):
            return who
    return None


@death_causes.cause_rule
def a_gambler_may_lose(world, state, night):
    """Guessing wrong kills you, and nothing else.

    It reaches exactly one seat — its own — so it can never account for
    anybody else's death. A Gambler who was impaired guesses nothing and
    dies of nothing.
    """
    if not _in_bag(state, "Gambler") or night < 2:
        return []
    phase = f"N{night}"
    began = f"D{night - 1}"
    # Whoever held it as the night began: it guesses tenth, and a Gambler
    # that guessed wrong and died was then made the Mathematician by a
    # Pit-Hag at sixteen — the night ended with no Gambler on the board
    # and a death nothing accounted for (07.10.2026).
    #
    # And *everybody* who has the ability, not the first seat found. A
    # Philosopher that took the Gambler stands beside the real one, drunk
    # and harmless; looking only at the seat holding the character found
    # that one, and the Philosopher's wrong guess killed nobody
    # (07.10.2026, the same sweep).
    holders = []
    for at in (began, phase):
        seat = world.find_at("Gambler", at)
        if seat is not None and seat not in holders:
            holders.append(seat)
    for who, (taken, since) in sorted((state.philosophies() or {}).items()):
        if taken == "Gambler" and who not in holders \
                and world.role_at(who, began) == "Philosopher" \
                and phase_index(phase) >= phase_index(since):
            holders.append(who)
    guesses = [info for info in state.infos
               if getattr(info, "source_role", None) == "Gambler"
               and info.night == night]
    causes = []
    for seat in holders:
        if seat not in state.alive_set(phase):
            continue
        # Its own guess where the row says whose it was; a guess relayed
        # by somebody who has no such ability could be anybody's.
        mine = [g for g in guesses if g.player == seat] \
            or [g for g in guesses if g.player not in holders]
        if not mine:
            continue                      # no guess recorded, no risk
        # And a guess that was right kills nobody. Then a Gambler dead by
        # morning went some other way, and that way has to be found.
        # Judged as the guess was made, before anything moved tonight —
        # see `GamblerGuess.holds`.
        if all(world.role_at(g.target, began) == g.role for g in mine):
            continue
        causes.append(death_causes.Cause(
            name="Gambler", kind=death_causes.OTHER,
            seats=frozenset({seat}), capacity=1))
    return causes


@death_causes.implication_rule
def a_grandmother_grieves(world, state, night, victim, kind):
    """Her grandchild taken by the Demon takes her with it.

    Only the Demon. A grandchild lost to a Gossip or an Assassin leaves
    her standing, which is why a death has to record what killed it.

    The grandchild is read off her reading rather than off the world: it
    is a token the Storyteller put on the seat she was shown, and it sits
    there whether what she was told was true or invented.
    """
    if not _in_bag(state, "Grandmother"):
        return []
    if kind != death_causes.DEMON:
        return []
    out = []
    for info in state.infos:
        if not isinstance(info, GrandmotherInfo) or info.target != victim:
            continue
        seat = info.player
        if world.role_at(seat, f"N{night}") != "Grandmother":
            continue
        # The grandchild she has *now*: her latest reading, from this
        # life. One who died and came back is a new Grandmother and is
        # shown a new grandchild (03.10.2026) — the old one is nothing to
        # her, and if nobody wrote the new one down there is no telling
        # who it is.
        later = any(isinstance(other, GrandmotherInfo)
                    and other.player == seat
                    and info.night < other.night < night
                    for other in state.infos)
        if later or info.night >= night > 1 \
                or _died_between(state, seat, info.night, night):
            continue
        # A Grandmother already dead cannot die again of grief. She was
        # executed on day 2, her grandchild fell on night 3, and this
        # demanded a second death from a seat that had none left to give
        # — so the board had no legal world at all.
        if seat not in state.alive_set(f"N{night}"):
            continue
        # Nor one who only came back tonight and is standing at dawn. A
        # Professor raises at 43, after every Demon: she was still dead
        # when her grandchild fell. (Regurgitated *before* the Shabaloth
        # chose, she would have died of it — and then nobody would have
        # announced her return.)
        if seat in _returned_at(state, f"N{night}"):
            continue
        out.append(death_causes.Implication(seat=seat, needs=seat))
    return out


@death_causes.immunity_rule
def a_tea_lady_keeps_her_neighbours(world, state, night, seat, kind):
    """Both her living neighbours good, and neither of them can die.

    Whether they are good is exactly what is in question, so this depends
    on the world being scored rather than on the board — the same shape as
    the Courtier's reach. Always on rather than aimed: she picks nobody,
    so a neighbour who died means she was not working.

    Her neighbours are whoever is living beside her at the time, which
    changes as people die.
    """
    if not _in_bag(state, "TeaLady"):
        return []
    phase = f"N{night}"
    # On a night somebody came back, who stood beside her has two
    # answers. She was raised at 43 and her neighbour was killed at 28:
    # she was not there to keep them. Or the one beside her came back
    # late, and at 28 her neighbour was somebody else. Her protection is
    # only *demanded* when it held whichever way the night went
    # (03.10.2026 — the first played game with a return in it).
    held = [_tea_lady_keeping(world, state, seat, phase, alive)
            for alive in _rosters(state, phase)]
    lady = next((who for who in held if who is not None), None)
    if lady is None:
        return []
    either_way = all(who is not None for who in held)
    # A Tea Lady who died tonight herself stops protecting the moment she
    # goes. A Shabaloth that takes her first and her neighbour second
    # kills both, and the plan knows whole nights rather than the order
    # within one — so on such a night her protection may explain a
    # survival but demands nothing of a death.
    fell = f"N{night}" in state.died_at(lady)
    # And one living beside a Goon: its side is not on the board.
    unsure = any(_beside_a_side_nobody_knows(world, state, lady, phase, alive)
                 for alive in _rosters(state, phase))
    return [death_causes.Shield("Tea Lady", needs=lady,
                                chosen=fell or unsure or not either_way)]


def _living_beside(state, seat, phase, alive=None):
    """The nearest living player on each side, going round the circle."""
    if alive is None:
        alive = state.alive_set(phase)
    n = state.n_players
    out = []
    for step in (1, -1):
        for gap in range(1, n):
            other = (seat + step * gap) % n
            if other == seat:
                break
            if other in alive:
                out.append(other)
                break
    return set(out)


@death_causes.immunity_rule
def a_fool_survives_once(world, state, night, seat, kind):
    """The first death does not take it, whatever the death was.

    Marked as aimed rather than always on, and the reason is worth
    saying: a Fool's first would-be death leaves no record at all,
    because nothing happened. So a Fool that *is* dead says nothing —
    the free one was spent out of sight. What it can do is explain a
    survival, which is exactly what an aimed shield does.
    """
    if not _in_bag(state, "Fool"):
        return []
    phase = f"N{night}"
    if world.role_at(seat, phase) != "Fool":
        return []
    return [death_causes.Shield("Fool", needs=seat, chosen=True)]


@death_causes.immunity_rule
def a_sober_sailor_cannot_die(world, state, night, seat, kind):
    """Not by the Demon, not by anything.

    Always on rather than aimed, so a Sailor who died must have been
    impaired — including by its own ability, which is the price the town
    pays for having one.
    """
    if not _in_bag(state, "Sailor"):
        return []
    if world.role_at(seat, f"N{night}") != "Sailor":
        return []
    return [death_causes.Shield("Sailor", needs=seat)]


@death_causes.immunity_rule
def an_innkeeper_guards_two(world, state, night, seat, kind):
    """From everything, not only the Demon — and it picks who."""
    if not _in_bag(state, "Innkeeper"):
        return []
    phase = f"N{night}"
    keeper = world.find_at("Innkeeper", phase)
    if keeper is None or night < 2 or keeper not in state.alive_set(phase):
        return []
    if keeper in _returned_at(state, phase):
        return []                         # back tonight, after its turn
    # Written down, the choice is no longer free. The two it named cannot
    # die tonight while it is working, so one of them dead means it was
    # not — and nobody else is covered at all. Unless the Innkeeper fell
    # tonight itself: its protection goes with it, and the plan does not
    # know which came first.
    picked = _chosen(state, "Innkeeper", night, ("a", "b"), by=keeper)
    if picked is None:
        return [death_causes.Shield("Innkeeper", needs=keeper, chosen=True)]
    if seat not in picked:
        return []
    fell = phase in state.died_at(keeper)
    return [death_causes.Shield("Innkeeper", needs=keeper, chosen=fell)]


@death_causes.immunity_rule
def an_exorcist_sends_the_demon_to_bed(world, state, night, seat, kind):
    """Choosing the Demon stops it waking at all, so nobody dies by it.

    Aimed rather than always on: it says nothing about a seat that did
    die, only that it could have been the reason one did not.
    """
    if not _in_bag(state, "Exorcist"):
        return []
    if kind != death_causes.DEMON or night < 2:
        return []
    phase = f"N{night}"
    demon = world.demon_at(phase)
    if demon is not None and world.role_at(demon, phase) == "Pukka":
        # A Pukka is the exception, because what dies tonight was chosen
        # last night. Naming it stops it *choosing* — so yesterday's
        # victim still dies, and the quiet night is the one after, when
        # there is no poison left to come due (the flowchart's steps 1
        # and 3 to 5; table ruling, 02.10.2026).
        #
        # Read the plain way, a board played by that rule had its quiet
        # night a night late for the Exorcist's row, and had to be
        # explained by something else or not at all.
        before = f"N{night - 1}"
        exorcist = world.find_at("Exorcist", before)
        if night < 3 or exorcist is None \
                or exorcist not in state.alive_set(before):
            return []
        picked = _chosen(state, "Exorcist", night - 1, by=exorcist)
        if picked is not None and world.demon_at(before) not in picked:
            return []
        # It had to be working *then*, which is not tonight's question.
        return [death_causes.Shield("Exorcist", chosen=True)]
    exorcist = world.find_at("Exorcist", phase)
    if exorcist is None or exorcist not in state.alive_set(phase):
        return []
    if exorcist in _returned_at(state, phase):
        return []                         # back tonight, after its turn
    # Recorded, the choice is no longer free: it only stops the Demon if
    # it named the seat holding it. That is the deduction the table draws
    # from a silent night, and it cannot be drawn while the choice is a
    # secret — which is why the row is worth having.
    picked = _chosen(state, "Exorcist", night, by=exorcist)
    # The Demon as the Exorcist's turn came, at 21 — before any Demon
    # acts. One that died tonight handed the star on *after* that: a
    # Fang Gu jumping, an Imp killing itself. The night is one moment
    # here, so the Outsider the Fang Gu was about to jump into read as
    # the Demon the Exorcist had named, the kill that followed as
    # impossible, and the game was lost (07.10.2026).
    demon = world.demon_at(phase)
    began = world.demon_at(f"D{night - 1}")
    if began is not None and began != demon and phase in state.died_at(began):
        demon = began
    if picked is not None and demon not in picked:
        return []
    # And it cuts the other way. Named and written down, the Demon does
    # not act tonight — so a Demon kill on that night says the Exorcist
    # was not working, or that this seat is not the Demon. That second
    # reading is what the table draws from it, and it was not drawn here:
    # the shield was only ever an excuse for a quiet night.
    return [death_causes.Shield("Exorcist", needs=exorcist,
                                chosen=picked is None)]


@death_causes.immunity_rule
def a_mayors_death_may_be_moved(world, state, night, seat, kind):
    """The Demon went for the Mayor, and the Storyteller sent it
    elsewhere — including into somebody already dead.

    Only the corpse case needs modelling. Bouncing onto a *living* player
    is invisible: "the Demon attacked the Mayor and it landed on Cara" and
    "the Demon attacked Cara" leave exactly the same board, and the solver
    never tracked who was aimed at in the first place. Bouncing into a
    corpse is different — it is a night where the Demon fired and nobody
    fell, which nothing else on this script explains for free.

    So it is offered only when there is a corpse to bounce into, and it is
    marked as aimed: the Storyteller chooses whether to move the kill, so
    a Mayor that died at night proves nothing about whether it was
    working.
    """
    if not _in_bag(state, "Mayor") or kind != death_causes.DEMON:
        return []
    phase = f"N{night}"
    if world.role_at(seat, phase) != "Mayor":
        return []
    # Somebody has to already be dead for the kill to go nowhere.
    if len(state.alive_at(phase)) >= state.n_players:
        return []
    return [death_causes.Shield("Mayor", needs=seat, chosen=True)]


@death_causes.immunity_rule
def the_dead_cannot_die_again(world, state, night, seat, kind):
    """Aiming at a corpse kills nobody, whatever the aim.

    Nothing had to be working for that, so there is nobody to keep
    unimpaired — but it is a deliberate play rather than the default, and
    a Demon bluffing Soldier or Monk has every reason to make it, so it
    is priced rather than free.
    """
    phase = f"N{night}"
    if seat in state.alive_set(phase):
        # Back tonight, so dead for the first part of it: a Pukka's
        # poison that came due at 26 found a corpse, and a Professor
        # stood it up at 43. The same sunk kill, except that from then on
        # the seat can die like anybody else — so it is an excuse on
        # offer, not a bar.
        if seat in _returned_at(state, phase):
            return [death_causes.Shield("already dead", needs=None,
                                        cost=SUNK_KILL_PENALTY, chosen=True)]
        return []
    return [death_causes.Shield("already dead", needs=None,
                                cost=SUNK_KILL_PENALTY)]


def _night_deaths(state):
    """{night: [seats that died that night]}"""
    out = defaultdict(list)
    for seat, phase in state.death_phases():
        if phase and phase[0].upper() == "N":
            out[int(phase[1:])].append(seat)
    return out


# A floor rather than a threshold, and the difference matters.
#
# Below this, the executed seat being the Demon is treated as essentially
# impossible and no Mastermind hint is shown. The town executing the real
# Demon is rare — around eight percent even with strong reads — so any
# higher threshold would fire on nothing. Above it the number is shown.
MASTERMIND_HINT = 0.02

# Below this many surviving worlds, a board is treated as argued into a
# corner rather than solved: few enough that one bad claim could have
# done it, and worth asking whether somebody lied.
_CORNERED = 24


# The Demon may swap two players when a Barber dies, and mostly does not
# — it is a deliberate play with a cost, not the default. Priced so that
# a world needing one is a worse story than a world that does not.
BARBER_SWAP_PENALTY = 0.15
# Inside a world, how the credit is shared once a Barber swap was open:
# how often the Demon swaps at all, and how much of that is the Demon with
# one of its own Minions (table habit, 30.09.2026). See `_barber_share`.
BARBER_SWAP_SHARE = 0.75
BARBER_DEMON_MINION_SHARE = 0.5

# How many worlds are enough to settle what killed somebody. It is a
# proportion, not a tally, so a spread across the space answers it as
# well as walking all of it — and walking all of it on a full script
# costs more than the solve itself.
BLAME_SAMPLE = 4000


def mastermind_days(state, allow_good_lies=False, max_worlds=200_000):
    """Days that might be the extra one a Mastermind bought.

    The trigger is the day after the Demon died, so a quiet night
    following an execution is exactly the shape to look for. It happens
    late in a game if it happens at all.

    The question is not "who is the Demon now" — in these worlds nobody
    is. It is whether the seat the town executed *was* the Demon at the
    moment it went, which is a different number and the one that matters.

    A nudge rather than a finding.
    """
    if "Mastermind" not in state.script.keys:
        return []
    executed = [(day, seat) for day, seat in sorted((state.executions or {}).items())
                if state.execution_death(day) == seat]
    if not executed:
        return []

    was_demon = {seat: 0.0 for _day, seat in executed}
    total = 0.0
    for world in iter_worlds(state.n_players, state.claims,
                             getattr(state, "certainties", None),
                             allow_good_lies, forced_roles(state),
                             getattr(state, "wakes", None), state.script,
                             getattr(state, "fabled", ())):
        cost, changes = best_story(world, state)
        if cost is None:
            continue
        view = Timeline(world, changes) if changes else world
        weight = prior_weight(world, state) * cost
        total += weight
        for day, seat in executed:
            if view.demon_at(f"D{day}") == seat:
                was_demon[seat] += weight
    if total <= 0:
        return []

    out = []
    for day, seat in executed:
        odds = was_demon[seat] / total
        if odds < MASTERMIND_HINT:
            continue
        out.append({"day": day + 1, "seat": seat,
                    "demon_pct": round(100 * odds, 1)})
    return out


def _tally_blame(into, view, state, weight):
    """Add one world's account of each night death to the running totals."""
    for night, victims in _night_deaths(state).items():
        died = set(victims)
        accounts = death_causes.explain_night(view, state, night, died,
                                              blame=True)
        share = sum(c for c, _i, _w, _b in accounts)
        if share <= 0:
            continue
        for account_cost, _imp, _wk, who in accounts:
            slice_ = weight * account_cost / share
            for seat, cause in who.items():
                into.setdefault(night, {}).setdefault(seat, {})
                into[night][seat][cause] = \
                    into[night][seat].get(cause, 0.0) + slice_


def blame_for_deaths(state, worlds, allow_good_lies=False):
    """Which cause accounts for each night death, and how strongly.

    Returns {night: {seat: {cause: share}}}, weighed across every world
    that survives — so it answers "given everything on the board, how
    much of this death looks like a Gossip" and is worked out fresh each
    time rather than typed in.

    Deliberately not asking you to rate anything. Several people claim
    Gossip on any given day, most of them bluffing, and a statement is a
    sentence about the world rather than about the board: no solver is
    going to weigh "the Demon has long hair". The statements themselves
    belong in the notes, where you can judge them yourself.
    """
    tally = {}
    for world in worlds:
        cost, changes = best_story(world, state)
        if cost is None:
            continue
        view = Timeline(world, changes) if changes else world
        weight = prior_weight(world, state) * cost
        for night, victims in _night_deaths(state).items():
            died = set(victims)
            accounts = death_causes.explain_night(view, state, night, died,
                                                  blame=True)
            share = sum(c for c, _i, _w, _b in accounts)
            if share <= 0:
                continue
            for account_cost, _imp, _wk, blame in accounts:
                slice_ = weight * account_cost / share
                for seat, cause in blame.items():
                    tally.setdefault(night, {}).setdefault(seat, {})
                    tally[night][seat][cause] = \
                        tally[night][seat].get(cause, 0.0) + slice_

    out = {}
    for night, seats in tally.items():
        out[night] = {}
        for seat, causes in seats.items():
            total = sum(causes.values()) or 1.0
            out[night][seat] = {name: value / total
                                for name, value in causes.items()}
    return out


_EPOCHS = __import__("itertools").count(1)


def _memo_for(base, name, state):
    """A memo on this deal, good for this state in this epoch only."""
    epoch = getattr(state, "_epoch", None)
    memo = getattr(base, name, None)
    if memo is None or memo[0] is not state or memo[1] != epoch:
        memo = (state, epoch, {})
        object.__setattr__(base, name, memo)
    return memo[2]


def _explained_night(world, state, night):
    """`explain_night`, kept per deal and per what had happened by then.

    A night's deaths are explained from the board as it stood that night,
    so they depend only on the changes up to it. Every story of one world
    shares its deal, and most share their early nights too: a Barber
    dying on night two offers fifty-five swaps, and night two's deaths
    read the same in all of them. Worked out once rather than fifty-five
    times — the answer is the same object, never changed by its readers.
    """
    base = world.world if isinstance(world, Timeline) else world
    here = phase_index(f"N{night}")
    upto = tuple(c for c in getattr(world, "changes", ())
                 if phase_index(c.phase) <= here)
    memo = _memo_for(base, "_nights_memo", state)
    key = (night, upto)
    got = memo.get(key)
    if got is None:
        died = set(_night_deaths(state).get(night, ()))
        got = memo[key] = _the_ones_that_can_win(
            death_causes.explain_night(world, state, night, died))
    return got


def _the_ones_that_can_win(options):
    """A night's explanations, without those another one makes pointless.

    One explanation asks for some seats impaired and some working. If a
    second asks for all of that *and more*, and is no cheaper, it can
    never be the one that wins: any plan that grants the second grants
    the first, at a price at least as good. Dropping it loses nothing.

    It matters because the nights multiply. Five ways to read night two
    and thirteen to read night three are sixty-five accounts before night
    four has begun, and the cap in `_night_accounts` cuts
    whatever does not fit — which by the sixth night of a Bad Moon Rising
    game with an Assassin and a Gossip in it was, three times in twenty
    thousand, the account that really happened (03.10.2026). Fewer ways
    per night is the only saving that is not a guess.
    """
    def within(a, b):
        return all(seats <= b.get(night, frozenset())
                   for night, seats in a.items())

    kept = []
    for i, (cost, impaired, working, earlier) in enumerate(options):
        beaten = False
        for j, (c, imp, wrk, ear) in enumerate(options):
            if i == j or c < cost or not imp <= impaired \
                    or not wrk <= working or not within(ear, earlier):
                continue
            # Asking exactly the same at the same price: the first stays.
            same = (c == cost and imp == impaired and wrk == working
                    and within(earlier, ear))
            if same and j > i:
                continue
            beaten = True
            break
        if not beaten:
            kept.append((cost, impaired, working, earlier))
    return kept


ACCOUNTS_KEPT = 400


def _the_ones_the_board_allows(night, options, impaired_already, working_already):
    """A night's explanations, without those the rest of the board refuses.

    An explanation asks for some seats impaired and some working. The
    board asks too, before any night is explained: a reading that came
    out false had a source that was impaired, and whoever walked away
    from an execution was working. An explanation that needs one of
    those seats the other way round is dead whatever else happens — the
    plan refuses a seat asked to be both — but it is not found out until
    the plan is tried, after the cap has made its cut. Until then it
    holds a place among the accounts kept.

    That cost two games in 24,000 over six nights once quiet nights were
    told and a stopped Demon could explain them (04.10.2026): more ways
    to read each night, the same four hundred places, and every one of
    the four hundred an account the readings ruled out. Nothing is lost
    by dropping these first — the plan would refuse every one.
    """
    def clash(when, impaired, working):
        return (impaired & set(working_already.get(when, ()))
                or working & set(impaired_already.get(when, ())))

    return [option for option in options
            if not clash(night, option[1], option[2])
            and not any(clash(when, seats, set())
                        for when, seats in option[3].items())]


def _night_accounts(world, state, impaired_already=None,
                    working_already=None):
    """How every night of this game could have gone.

    Returns a list of (cost, extra impaired, extra working) — one entry
    per way of attributing the deaths and explaining the causes that
    fired regardless. Empty means no account fits.

    A night that killed nobody is explained here rather than separately,
    because "the Demon was stopped" and "the Demon killed somebody" are
    the same question asked of the same cause.

    `impaired_already` and `working_already` are what the board asks of
    each night before any of this — see `_the_ones_the_board_allows`.
    """
    nights = set(_night_deaths(state))
    nights |= set(getattr(state, "quiet_nights", None) or ())
    if not nights:
        return [(1.0, {}, {})]

    # One account per set of demands, the cheapest excuses first.
    #
    # What an account asks of the impairment plan is who had to be
    # impaired and who had to be working, night by night. Two accounts
    # that ask the same differ only in what they cost, and the dearer one
    # can never win — so only the best of each is kept, which loses
    # nothing.
    #
    # Then a cap, because the nights multiply. It used to be the first
    # twenty-four *as they came*, unsorted and with every duplicate still
    # in: a Bad Moon Rising night has a Demon, a Gossip, an Assassin and a
    # Gambler all able to explain the same body, ten ways for one night
    # and seven for the next, and by the fourth night the account that
    # really happened was past the cut. The world was then thrown out
    # with nothing wrong with it (03.10.2026, found when the simulator
    # began playing games with more in them).
    #
    # Built without copying. Every account times every explanation used
    # to be made in full — each night's sets copied, each key sorted out
    # of them — and only then compared, which is where a long board
    # spent its time once a stopped Demon gave quiet nights more
    # explanations (04.10.2026). The sets are frozen now and shared, an
    # account's key grows by one night's entry, and an account that
    # another already beats is never built. The only ones made the long
    # way are those that put a demand on an earlier night: a Pukka's.
    none = frozenset()
    accounts = [(1.0, {}, {}, ())]
    done = []
    for night in sorted(nights):
        options = []
        for extra_cost, extra_impaired, extra_working, earlier \
                in _the_ones_the_board_allows(
                    night, _explained_night(world, state, night),
                    impaired_already or {}, working_already or {}):
            if extra_impaired & extra_working:
                continue                  # asked to be both at once
            extra_impaired = frozenset(extra_impaired)
            extra_working = frozenset(extra_working)
            # A kill that started on an earlier night puts its demand
            # back where it belongs.
            early = tuple((when, frozenset(seats))
                          for when, seats in sorted(earlier.items()) if seats)
            options.append((extra_cost, extra_impaired, extra_working, early,
                            (night, extra_impaired, extra_working)))
        if not options:
            return []
        done.append(night)
        best = {}
        for cost, impaired, working, key in accounts:
            for extra_cost, extra_impaired, extra_working, early, entry \
                    in options:
                total = cost * extra_cost
                merged = None
                if not early:
                    grown = key + (entry,)
                else:
                    merged = dict(impaired)
                    merged[night] = extra_impaired
                    clash = False
                    for when, seats in early:
                        merged[when] = merged.get(when, none) | seats
                        if merged[when] & working.get(when, none):
                            clash = True  # impaired and working at once
                    if clash:
                        continue
                    grown = tuple(
                        (n, merged.get(n, none),
                         extra_working if n == night
                         else working.get(n, none))
                        for n in sorted(set(done) | set(merged)))
                had = best.get(grown)
                if had is not None and total <= had[0]:
                    continue              # the same demands, no cheaper
                if merged is None:
                    merged = dict(impaired)
                    merged[night] = extra_impaired
                best[grown] = (total, merged,
                               {**working, night: extra_working}, grown)
        accounts = sorted(best.values(),
                          key=lambda account: -account[0])[:ACCOUNTS_KEPT]
        if not accounts:
            return []
    return [(cost, impaired, working)
            for cost, impaired, working, _key in accounts]


def forced_roles(state):
    """Roles pinned down by events the whole table watched.

    These are the same facts the hard checks enforce, but handed to the
    search up front so it never builds the worlds they rule out. Without
    this a Virgin trigger still gives the right answer - it just has to
    generate and discard millions of worlds to get there, and can hit the
    ceiling before it finishes.
    """
    pinned = {}

    def pin(seat, roles):
        roles = frozenset(roles)
        pinned[seat] = roles if seat not in pinned else pinned[seat] & roles

    for info in state.infos:
        if isinstance(info, VirginNomination) and info.triggered:
            pin(info.player, ["Virgin"])
            # The nomination only fires on a Townsfolk, or the Spy wearing
            # one. The Drunk is an Outsider, so a Drunk nominator is out.
            townsfolk = list(state.script.townsfolk)
            spies = [k for k in state.script.keys
                     if "townsfolk" in CHARACTERS[k].registers]
            pin(info.nominator, townsfolk + spies)
        elif isinstance(info, SlayerShot) and info.died:
            pin(info.player, ["Slayer"])
            pin(info.target, ["Imp", "Recluse"])
    return pinned


def _spent_nominations(state):
    """Quiet Virgin nominations that carry nothing.

    The ability only fires the first time a Townsfolk nominates, so once
    one nomination is on the record the later quiet ones say nothing.
    """
    cached = getattr(state, "_spent_noms_cache", None)
    if cached is not None:
        return cached
    spent, seen = set(), set()
    for i in sorted(range(len(state.infos)),
                    key=lambda j: state.infos[j].night):
        info = state.infos[i]
        if not isinstance(info, VirginNomination):
            continue
        if info.player in seen and not info.triggered:
            spent.add(i)
        seen.add(info.player)
    state._spent_noms_cache = spent
    return spent


def _source_seats(state):
    """Cached per state: which seat each ledger row is attributed to."""
    seats = getattr(state, "_source_seats_cache", None)
    if seats is None:
        seats = [info.source_seat(state) for info in state.infos]
        state._source_seats_cache = seats
    return seats


# What became of a recorded reading in one particular world. Four
# outcomes rather than true-or-false, because two of them are neither.
HELD = "held"          # the source was genuine and what they said was so
EXCUSED = "excused"    # genuine, and false — something had to have stopped them
MADE_UP = "made up"    # they were handed the wrong token, so it was never theirs
INVENTED = "invented"  # nobody in this world could have produced it
SPENT = "spent"        # the ability had already been used, so it says nothing


def rh_for(info):
    """The red herring to use while checking a Vortox'd reading.

    None, for every row but the Fortune Teller's, which no longer comes
    here: its answer under a Vortox is settled in the herring search
    with the others, because the herring *can* make an answer false —
    a no on the pair it sits in (07.10.2026).
    """
    return None


def _plain_failures(world, state, outcome=None):
    """Sort every ledger row into: fits, contradicts, or was invented.

    Returns (failures, fortune teller readings, what the inventions cost),
    or (None, None, 1.0) if the world is flatly impossible. The cost is a
    product rather than a count, because how much a made-up reading costs
    now depends on how far you said you believed it.

    A row is traced back to a source seat. When a seat has claimed the
    role, that is the source. When nobody has claimed it, the source is
    whoever holds the role in this particular world - which is how a
    statement finds its way onto a seat that has said nothing.
    """
    # The Balloonist's chain is **not** judged here, deliberately.
    #
    # It was, and it threw out seven of forty mixed-script boards. A
    # droisoned Balloonist may be shown the same type as last night, and
    # the solver does not know which nights those were — the impairment
    # plan settles that, for a cost.
    #
    # So a chain of three Townsfolk running is not impossible. It is a
    # Poisoner sitting on the Balloonist for two nights, which is
    # expensive and legal. **A check that cannot price something should
    # not judge it**: the same conclusion the Acrobat reached, from the
    # opposite direction.
    #
    # `a_balloonist_chain_fits` is kept and tested. Wiring it in needs
    # the chain to say what it *requires* — these nights droisoned, or
    # this world ruled out — and hand that to the plan, which is real
    # work rather than a call in the right place.

    failures = defaultdict(set)
    # Nights where a reading came out true under a Vortox: {night:
    # (vortox, the readings' sources)}. Either will do — see `_explain`.
    state._vortox_or = vortox_or = {}
    working = {}
    ft_infos = []
    invented = 1.0
    if outcome is None:
        outcome = {}

    # A day that ended with nobody executed, and the game carried on.
    #
    # Evil wins on the spot if a Vortox is working when that happens, so
    # play continuing says there was not one — that day. Per day rather
    # than per game, because a Pit-Hag can bring one along later or
    # replace one earlier, and because a droisoned Vortox does nothing.
    for day in sorted(state.days_done or ()):
        if day in (state.executions or {}):
            continue                      # somebody was executed
        vortox = world.find_at("Vortox", f"D{day}")
        if vortox is None or vortox not in state.alive_set(f"D{day}"):
            continue
        failures[day].add(vortox)

    # Two deaths that name a character nobody chose to reveal.
    #
    # A seat dropping dead as it nominates is a Witch, and a seat
    # executed for breaking *ceremadness* is a Cerenovus. Named that way
    # deliberately: this confirms the Cerenovus and nothing else, and
    # other characters madden people too. Neither character can
    # be got at any other way: both make a hidden choice the board never
    # records, so the only handle is what the table plainly saw. Both are
    # worth a lot, because each says that character is *in play*.
    #
    # The one who did it has to have been working, which is why this
    # demands them rather than merely wanting them.
    for day, seat in sorted((state.witch_deaths or {}).items()):
        witch = world.find_at("Witch", f"N{day}")
        if witch is None or not minion_still_acts(world, state, witch,
                                                  f"N{day}"):
            return None, None, 1.0, None
        # "If just 3 players live, you lose this ability" — and the curse
        # goes with it, so nobody drops dead nominating at a table of
        # three.
        if len(state.alive_set(f"D{day}")) <= 3:
            return None, None, 1.0, None
        working.setdefault(day, set()).add(witch)
    for day, seat in sorted((state.madness_executions or {}).items()):
        maddener = world.find_at("Cerenovus", f"N{day}")
        if maddener is None or not minion_still_acts(world, state, maddener,
                                                     f"N{day}"):
            return None, None, 1.0, None
        working.setdefault(day, set()).add(maddener)

    # The good twin executed, and the game carried on. Evil wins on the
    # spot when that happens, so play continuing says the Evil Twin was
    # not working — or that the one who hanged was the evil one, which is
    # the deduction the table draws and this never did (02.10.2026).
    for info in state.infos:
        if not isinstance(info, EvilTwinPair):
            continue
        for day in (state.executions or {}):
            hanged = state.execution_death(day)
            if hanged not in (info.a, info.b):
                continue
            other = info.b if hanged == info.a else info.a
            phase = f"D{day}"
            if world.role_at(other, phase) != "EvilTwin" \
                    or other not in state.alive_set(phase) \
                    or world.evil_at(hanged, phase):
                continue
            failures[day].add(other)

    # A Mastermind's extra day, if this story has one.
    #
    # The Mastermind had to be working: a droisoned one has no ability,
    # and the execution would simply have ended the game. And the day is
    # only extra because the game *would have ended* — a Scarlet Woman
    # who qualified would have become the Demon instead, so in a story
    # where she did not, she was the one not working.
    #
    # Both used to go unasked, so a Mastermind day and a Scarlet Woman
    # taking over stood side by side at no cost to either, and the solver
    # split the Demon between them on a board where the rules pick her.
    for change in getattr(world, "changes", ()):
        if not is_mastermind_marker(change):
            continue
        day = int(change.phase[1:])
        mastermind = world.find_at("Mastermind", change.phase)
        if mastermind is None \
                or mastermind not in state.alive_set(change.phase):
            return None, None, 1.0, None
        working.setdefault(day, set()).add(mastermind)
        if scarlet_woman_takes_over(world, state, change.phase):
            failures[day].add(world.find_at("ScarletWoman", change.phase))

    # Executing the Saint ends the game on the spot — while it is
    # *working*. A poisoned or drunk Saint is executed and the game
    # carries on, so an execution that killed somebody does not rule the
    # Saint out; it says something had to have stopped them.
    #
    # This used to throw those worlds away outright, which is both wrong
    # and the wrong direction to be wrong in: a Poisoner going for the
    # Saint on the day the town is minded to execute them is a real play,
    # and the solver was insisting it never happened.
    for day in (state.executions or {}):
        seat = state.execution_death(day)
        if seat is None:
            continue
        if world.role_at(seat, f"D{day}") == "Saint":
            failures[day].add(seat)
        # A Sailor cannot die, and that holds in daylight too — so a
        # working one walks away from its own execution. Somebody
        # executed and killed was not a working Sailor, which means
        # something had to have stopped it working.
        if world.role_at(seat, f"D{day}") == "Sailor":
            failures[day].add(seat)
        # And the same for a Tea Lady's neighbour: executed and dead, so
        # she was not working. The mirror of her saving one.
        if _in_bag(state, "TeaLady"):
            lady = _tea_lady_keeping(world, state, seat, f"D{day}")
            if lady is not None and not _beside_a_side_nobody_knows(
                    world, state, lady, f"D{day}"):
                failures[day].add(lady)

    # Somebody standing again needs a reason, and the reason has to have
    # been working. Two characters do it.
    #
    # A Professor raises one Townsfolk, once — which is not the same as
    # raising somebody good: the Spy registers as a Townsfolk and would
    # be raised like anybody else.
    #
    # A Shabaloth may regurgitate somebody it chose the night before,
    # whatever they are and as often as the Storyteller likes. That was
    # missing altogether: with no Professor in the world the board was
    # thrown out, and a second resurrection always was (02.10.2026).
    # Which dead player it chose is not recorded, so any of them will do.
    by_professor = 0
    for seat, phases in (state.resurrections or {}).items():
        for phase in phases:
            night = int(phase[1:]) if phase[1:].isdigit() else None
            if night is None:
                continue
            shabaloth = (world.find_at("Shabaloth", phase)
                         if _in_bag(state, "Shabaloth") else None)
            if shabaloth is not None and night >= 3 \
                    and shabaloth in state.alive_set(phase):
                continue                  # it could have; nothing demanded
            prof = world.find_at("Professor", phase)
            if prof is None or not _in_bag(state, "Professor"):
                return None, None, 1.0, None
            if prof not in state.alive_set(phase) or night < 2:
                return None, None, 1.0, None
            raised = world.role_at(seat, phase)
            if TEAM[raised] != "townsfolk" \
                    and "townsfolk" not in CHARACTERS[raised].registers:
                return None, None, 1.0, None
            working.setdefault(night, set()).add(prof)
            by_professor += 1
    # Once per game, so two of the Professor's is not a game.
    if by_professor > 1:
        return None, None, 1.0, None

    # An execution that killed nobody needs a reason, and the reason has
    # to have been working.
    for day, seat in (state.executions or {}).items():
        if state.execution_death(day) is not None:
            continue                      # it did kill; nothing to explain
        survivors = set(survivals_of(world, state, day, seat))
        if not survivors:
            return None, None, 1.0, None  # nothing here survives an execution
        # One of them did it, and that one was working. With a single
        # candidate that is a demand; with several it is "one of these",
        # which the plan cannot hold — it knows sets, not alternatives.
        # Demanding all of them, as this did, threw out a Devil's
        # Advocate's rescue whenever a Pacifist on the same board was
        # drunk. And it *replaced* whatever else had to be working that
        # day rather than adding to it.
        if len(survivors) == 1:
            working.setdefault(day, set()).update(survivors)

    spent = _spent_nominations(state)
    for idx, (info, src) in enumerate(zip(state.infos, _source_seats(state))):
        if idx in spent:
            outcome[idx] = SPENT
            continue                      # the Virgin was already used up
        if info.hard():
            if not info.holds(world, state, None):
                return None, None, 1.0, None   # this cannot have happened
            outcome[idx] = HELD
            continue

        role = info.source_role
        phase = f"N{info.night}"
        seat = src
        if seat is None:
            # Who *acted*, not who holds the character now.
            #
            # A Snake Charmer swap is dated at the night, so asking here
            # finds the seat the character ended up at rather than the
            # seat that spoke — and the row then reads as invented. Look
            # at the board as it stood when the night began, and fall
            # back to now for a character that arrived tonight.
            began = _before(info.night, phase)
            seat = world.find_at(role, began)
            if seat is None:
                # Held now, or a Philosopher working it.
                seat = _whoever_works(world, state, role, phase)
            if seat is None:
                seat = next((i for i, b in enumerate(world.believes)
                             if b == role), None)

        # A Philosopher works two abilities at once, so a seat holding
        # one may be the source of the other's readings from the night it
        # took them.
        gained = None
        took = state.philosophies().get(seat)
        if took is not None:
            taken, since = took
            gained = (taken, since, phase_index(phase) >= phase_index(since))
        # A Vortox in play makes every Townsfolk ability yield something
        # false. Alive, because a dead Demon does nothing; and its own
        # droisoning is left to the plan below rather than decided here,
        # the same way poison always has been.
        vortox = world.find_at("Vortox", phase)
        vortoxed = vortox is not None and vortox in state.alive_set(phase)
        # Asked of the moment it *acted*. A Snake Charmer swap is dated
        # at the night, so at `phase` the charmer no longer holds the
        # character — and its own row was charged as invented, which put
        # a world where the swap really happened at 0.4 against 1.0 for
        # one where it could not. Exactly backwards, and the reason the
        # swap used to be dated a phase late.
        acted = _before(info.night, phase)
        # Held then, **or taken by a Philosopher then** — a Philosopher
        # that took the Snake Charmer and swapped is the Demon by `phase`,
        # and its own row read as invented (29.09.2026).
        if seat is not None and world.role_at(seat, phase) != role \
                and _has_ability(world, state, seat, role, acted):
            held = ability_state(world, seat, role, acted, gained, vortoxed)
        else:
            held = (ABSENT if seat is None
                    else ability_state(world, seat, role, phase, gained,
                                       vortoxed))
        # A row told to somebody *other* than the holder — the player a
        # Nightwatchman chose saying they were woken. A Drunk holding the
        # token has no ability, so the Storyteller wakes nobody for it:
        # there is no made-up answer for anybody else to have heard.
        witnessed = getattr(info, "witnessed", False)
        if witnessed and held is ARBITRARY:
            held = ABSENT
        if held is ABSENT:
            invented *= invention_cost(info)   # no such source in this world
            outcome[idx] = INVENTED
            continue
        if held is ARBITRARY:
            outcome[idx] = MADE_UP        # the Drunk's answer was made up
            continue
        if seat != info.player and world.evil_at(info.player, phase):
            invented *= invention_cost(info)   # an evil messenger is none
            outcome[idx] = INVENTED
            continue

        # A Vortox falsifies information, not choices. Nobody told a
        # Philosopher what it took or a Courtier which character to name,
        # so there is nothing about those rows for a Vortox to make
        # false — and treating them as readings made every board with a
        # Philosopher on it impossible.
        #
        # What follows from the choice is a different matter: a
        # Philosopher that took the Town Crier gets that ability and
        # *that* reading is inverted, a Gambler that guesses wrong still
        # dies, a Snake Charmer that chose the Vortox still swaps.
        # One question, asked in one place: does a Vortox reach this row?
        if held is INVERTED and not info.is_information(state):
            outcome[idx] = HELD
            continue

        if held is INVERTED and isinstance(info, FortuneTeller):
            # Whether it came out false depends on the red herring, like
            # everything else about a Fortune Teller. Chosen with the
            # herring in the pair, the true answer is yes and a Vortox
            # makes it no — and a no on two players of whom neither is
            # the Demon was read here as true, with no herring to say
            # otherwise, so the Vortox had to be off and the true world
            # of nine mixed games in three thousand was thrown out
            # (07.10.2026). Settled with the herring, below.
            ft_infos.append((info, seat, idx, vortox))
            continue

        if held is INVERTED:
            # It had to come out false. A reading that is *true* means
            # the Vortox itself was not working that night, which the
            # plan can pay for like any other droisoning.
            #
            # A false one is left alone rather than charged for, and that
            # is an approximation worth naming: on a night where some
            # readings are true and others false, this takes the Vortox
            # as droisoned and does not additionally charge the false
            # ones for needing their own excuse. Permissive, which is the
            # direction to err in — it keeps worlds that happened rather
            # than ruling them out.
            # Truth, not legality. Misregistration is the mechanic that
            # lets a Storyteller give false information *legally* — a Spy
            # shown as the Slayer is still a Spy, so that reading is
            # already false and a Vortox may produce it freely.
            #
            # `holds` answers "could this have been said", which is right
            # nearly everywhere and wrong here. Rows that can misregister
            # carry `is_true` for exactly this question, and asking the
            # wrong one made a legal misregistered reading look true —
            # so the Vortox had to be droisoned to explain it, and boards
            # that really happened were priced as though something had
            # gone wrong.
            was_true = (info.is_true(world, state, seat)
                        if hasattr(info, "is_true")
                        else info.holds(world, state, rh_for(info), seat))
            if was_true:
                # Then the Vortox was not working, and nothing else will
                # do. "Even if they are drunk or poisoned, it must be
                # false" — the card's own clarification.
                #
                # For three days this also accepted the seat itself being
                # droisoned, on the reasoning that a droisoned Townsfolk
                # is told anything and anything includes the truth. Under
                # a Vortox it does not, and the simulator that produced
                # such a board was making the same mistake (corrected
                # 02.10.2026, reading the script against the wiki).
                #
                # The Mathematician is left with both ways out. Its number
                # is checked against a range rather than a value, so a
                # false one can sit inside what this would call true.
                if type(info).__name__ == "MathematicianInfo":
                    got = vortox_or.setdefault(info.night, (vortox, set()))
                    got[1].add(seat)
                else:
                    failures[info.night].add(vortox)
                outcome[idx] = EXCUSED
            else:
                outcome[idx] = HELD
            continue

        if isinstance(info, FortuneTeller):
            # Whether it held depends on where the red herring was, which
            # is settled later. Left open until then.
            ft_infos.append((info, seat, idx, None))
        elif witnessed and not info.holds(world, state, None, seat):
            # Nothing excuses it. A droisoned source does not tell the
            # other player something false — it tells them nothing, they
            # are never woken. So the words did not come from the game.
            invented *= invention_cost(info)
            outcome[idx] = INVENTED
        elif not info.holds(world, state, None, seat):
            # Poison has to land on whoever the information came from -
            # poisoning the messenger changes nothing.
            failures[info.night].add(seat)
            outcome[idx] = EXCUSED
        else:
            outcome[idx] = HELD
            # **A droisoned character cannot misregister.** A Storyteller
            # chooses freely what a droisoned *information* role yields,
            # because the information is arbitrary — but registration is
            # a plain ability, and a plain ability simply does not
            # function. A poisoned Recluse is a Recluse and shows as one.
            #
            # Whether a seat was droisoned is not known here: it is
            # *chosen*, by the impairment plan, which settles afterwards.
            # So a row that held only by somebody misregistering says so,
            # and that seat is forbidden from being droisoned that night.
            # The plan already understood "must not be impaired"; this is
            # the first caller to use it for registration.
            for who in info.leaned_on(world, state, seat):
                working.setdefault(info.night, set()).add(who)

    return failures, ft_infos, invented, working


def _chosen(state, role, night, fields=("target",), by=None):
    """What a declared choice named on this night, if it was recorded.

    Returns the seats, or None when nothing was written down. None is not
    the same as an empty answer: it means "nobody said", and the rule
    falls back to reaching everybody rather than reaching nobody.

    `by` is the seat that really holds the character in this world. A
    row from anybody else is a bluff's story, and what the real one
    chose is then as unrecorded as if nobody had spoken.
    """
    for info in state.infos:
        if getattr(info, "source_role", None) != role or info.night != night:
            continue
        if by is not None and info.player != by:
            continue
        got = [getattr(info, f) for f in fields
               if getattr(info, f, None) is not None]
        if got:
            return frozenset(got)
    return None


def _nearest_townsfolk(world, state, seat, phase, n):
    """The nearest Townsfolk each way round the circle.

    By *team*, not by side: a Townsfolk can be evil, and this skips
    Outsiders and Minions rather than skipping the evil. And the dead are
    not skipped either — a dead Townsfolk is still the nearest one, and
    still gets poisoned.
    """
    out = set()
    for step in (1, -1):
        for gap in range(1, n):
            other = (seat + step * gap) % n
            if other == seat:
                break
            if world.team_at(other, phase) == "townsfolk":
                out.add(other)
                break
    return out


@impairment.source_rule
def a_no_dashii_poisons_its_townsfolk_neighbours(world, state, night):
    """Its two nearest Townsfolk, all game.

    Nothing is chosen and nothing is lucky, so this costs nothing. It
    moves as the table changes shape — whoever is nearest *now* — and it
    stops the moment the No Dashii does.
    """
    if not _in_bag(state, "NoDashii"):
        return []
    phase = f"N{night}"
    seat = world.find_at("NoDashii", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    hit = _nearest_townsfolk(world, state, seat, phase, state.n_players)
    out = []
    if hit:
        out.append(impairment.Source("No Dashii", frozenset(hit),
                                     capacity=len(hit), cost=1.0,
                                     repeat_cost=1.0))
    # Whoever was beside it as the night began, and no longer is. "The
    # players who are poisoned may change immediately" — so on a night a
    # Pit-Hag turns its Townsfolk neighbour into something else, that
    # neighbour was poisoned for the part of the night before it
    # happened. A Snake Charmer there pointed at the No Dashii, nothing
    # came of it, and by the end of the night it was an Evil Twin with
    # no reason to have failed (02.10.2026). On offer, not forced.
    began = _before(night, phase)
    then = world.find_at("NoDashii", began)
    if then is not None:
        earlier = _nearest_townsfolk(world, state, then, began,
                                     state.n_players) - set(hit)
        if earlier:
            out.append(impairment.Source(
                "No Dashii, as the night began", frozenset(earlier),
                capacity=len(earlier), cost=lambda who: 1.0,
                repeat_cost=lambda who: 1.0))
    return out


def killed_by_a_vigormortis(world, state, who, phase):
    """Is this a dead Minion a living Vigormortis killed?

    "Minions you kill keep their ability": at night, while a Vigormortis
    was the Demon, and only for as long as it stays alive.
    """
    if world.team_at(who, phase) != "minion":
        return False
    gone = [p for p in state.died_at(who)
            if phase_index(p) <= phase_index(phase)]
    if not gone:
        return False
    first = min(gone, key=phase_index)
    if first[0].upper() != "N":
        return False
    killer = world.demon_at(first)
    if killer is None or world.role_at(killer, first) != "Vigormortis":
        return False
    now = world.find_at("Vigormortis", phase)
    return now is not None and now in state.alive_set(phase)


def minion_still_acts(world, state, seat, phase):
    """Alive — or dead at a Vigormortis's hand, which keeps its ability.

    A Witch it killed goes on cursing and a Cerenovus goes on maddening.
    Only "alive" was asked, so a nominator dropping dead on the day after
    a Vigormortis took its own Witch had nobody to have cursed them, and
    the board was not a world (02.10.2026).
    """
    return seat in state.alive_set(phase) \
        or killed_by_a_vigormortis(world, state, seat, phase)


@impairment.source_rule
def a_vigormortis_poisons_beside_its_dead_minions(world, state, night):
    """Every Minion it killed keeps its ability and drunks a neighbour.

    A Townsfolk beside the dead Minion, and the Storyteller chooses which
    — so the reach is both neighbours and the capacity is one per corpse.
    Dead or alive makes no difference to who can be picked.

    Like the No Dashii and unlike the Sweetheart, it stops when the
    Vigormortis does.
    """
    if not _in_bag(state, "Vigormortis"):
        return []
    phase = f"N{night}"
    seat = world.find_at("Vigormortis", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    out = []
    for who in range(state.n_players):
        if world.team_at(who, phase) != "minion":
            continue
        gone = state.died_at(who)
        if not gone or phase_index(min(gone, key=phase_index)) > \
                phase_index(phase):
            continue                      # still standing
        # Only a Minion **it killed**: at night, while a Vigormortis was
        # the Demon. Every dead Minion counted, an executed one too — the
        # simulator read the card the same way, so neither noticed. Found
        # when a Snake Charmer took the Vigormortis's seat and the
        # simulator, reading the deal, stopped poisoning altogether
        # (29.09.2026).
        first = min(gone, key=phase_index)
        if first[0].upper() != "N":
            continue
        killer = world.demon_at(first)
        if killer is None or world.role_at(killer, first) != "Vigormortis":
            continue
        beside = _nearest_townsfolk(world, state, who, phase,
                                    state.n_players)
        if beside:
            out.append(impairment.Source(
                "Vigormortis", frozenset(beside), capacity=1,
                cost=1.0, repeat_cost=1.0))
    return out


@impairment.source_rule
def a_philosopher_drunks_whoever_had_it(world, state, night):
    """Taking an ability drunks whoever already had it.

    Only while the Philosopher lives — unlike the Sweetheart, this one
    switches off again. And only when somebody actually holds the chosen
    character: a Philosopher may take one nobody has, and then it drunks
    nobody.

    Free rather than priced: the Philosopher declared what it took, so
    there is no luck in where this landed.
    """
    if not _in_bag(state, "Philosopher"):
        return []
    out = []
    phase = f"N{night}"
    for who, (taken, since) in state.philosophies().items():
        if phase_index(phase) < phase_index(since):
            continue
        if who not in state.alive_set(phase):
            continue                      # it stops when they do
        # The span in which it stops being the Philosopher, or dies, is
        # half and half: whoever it drunk is drunk until that moment and
        # sober after it. A Philosopher that took the Snake Charmer and
        # swapped tonight is the Demon by the end of the night — and the
        # real Snake Charmer, pointing at the same Demon a moment
        # earlier, was still drunk when nothing happened. So there the
        # drunkenness is on offer rather than forced, and it is read off
        # the board as the night began.
        began = _before(night, phase)
        still = world.role_at(who, phase) == "Philosopher"
        if not still and world.role_at(who, began) != "Philosopher":
            continue
        went = (not still) or any(at in state.died_at(who)
                                  for at in (phase, f"D{night}"))
        had = world.find_at(taken, began if not still else phase)
        if had is None or had == who:
            continue                      # nobody else was holding it
        free = (lambda seat: 1.0) if went else 1.0
        out.append(impairment.Source("Philosopher", frozenset({had}),
                                     capacity=1, cost=free,
                                     repeat_cost=free))
    return out


def _died_on(state, night):
    """Everybody the board records as dying on this night."""
    phase = f"N{night}"
    return frozenset(seat for seat in (state.deaths or {})
                     if phase in state.died_at(seat))


@impairment.source_rule
def a_pukka_poisons_whoever_it_will_kill(world, state, night):
    """It poisons on one night and that poison kills on the next.

    The kill rule demands the victim was poisoned the night before
    (`victim_impaired_at=night - 1`), so this is what provides that
    poison. Two tokens can matter on one night, and they are priced
    differently.

    **The one it places tonight.** Whoever goes on to die tomorrow night
    was certainly the one it chose, so that costs nothing: the Pukka
    poisons somebody every night and the body says who. This charged the
    Poisoner's price for it, as though the poison had to get lucky, and
    so every Pukka kill cost its world 0.35 — the true world of a Pukka
    game weighed a fifth of any other Demon's (02.10.2026). Anybody else
    is a guess and is priced like one: it reaches the whole table, so
    left free it would excuse any reading at no cost.

    **The one it placed last night.** That player stays poisoned until
    the Pukka's turn comes round again — so a Sailor, a Fool or an
    Innkeeper that dies tonight was still poisoned as the night began,
    and chose, guarded or failed to survive in that state. Free for the
    same reason for tonight's dead.

    And somebody it did not kill: a Tea Lady's neighbour, an Innkeeper's
    pick, a Fool. They carried the token into the night all the same, so
    an Innkeeper among them chose with no ability — nobody drunk, nobody
    safe — and is healthy again by morning. Nothing on the board says who
    that was, so it is a guess and priced like one (03.10.2026: this
    reached only the dead, and a poisoned Innkeeper kept alive by a Tea
    Lady had to have made somebody drunk).

    Neither is forced on anybody. A night and its day share one span
    here, and a seat that acted *before* the Pukka on the night it was
    chosen was still sober when it did.
    """
    if not _in_bag(state, "Pukka"):
        return []
    phase = f"N{night}"
    seat = world.find_at("Pukka", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    alive = frozenset(state.alive_set(phase))
    due_tomorrow = _died_on(state, night + 1)

    def fresh(who):
        return 1.0 if who in due_tomorrow else POISON_HIT_PENALTY

    def fresh_again(who):
        return 1.0 if who in due_tomorrow else POISON_REPEAT_PENALTY

    out = [impairment.Source("Pukka", alive, capacity=1, cost=fresh,
                             repeat_cost=fresh_again)]
    due_tonight = _died_on(state, night) & alive

    def carried(who):
        return 1.0 if who in due_tonight else POISON_HIT_PENALTY

    if night >= 2:
        out.append(impairment.Source("Pukka's token", alive,
                                     capacity=1, cost=carried,
                                     repeat_cost=carried))
    return out


@impairment.source_rule
def a_sweetheart_leaves_somebody_drunk(world, state, night):
    """From the night it dies, one player is drunk for good.

    Any death does it, and the Storyteller never says who — so the reach
    is everybody and it never turns off again. That last part is what
    makes it different from a Poisoner: a seat it landed on is impaired
    for the rest of the game, so every reading they ever give afterwards
    is arbitrary.

    Free rather than priced. There is no luck in it: the Storyteller
    picks, and picking somebody is not a coincidence that needs paying
    for.
    """
    if not _in_bag(state, "Sweetheart"):
        return []
    # Whoever was the Sweetheart when they died — dealt one, or made one by
    # a Pit-Hag. Only the dealt one was looked for (29.09.2026).
    out = []
    for seat in range(state.n_players):
        gone = [p for p in state.died_at(seat)
                if world.role_at(seat, p) == "Sweetheart"]
        if not gone:
            continue
        first = min(gone, key=phase_index)
        if phase_index(first) > phase_index(f"N{night}"):
            continue                      # it had not died yet
        out.append(impairment.Source(
            "Sweetheart", frozenset(range(state.n_players)),
            capacity=1, cost=1.0, repeat_cost=1.0))
    return out


impairment.source_rule(
    impairment.make_poisoner_rule(lambda: POISON_HIT_PENALTY,
                                  lambda: POISON_REPEAT_PENALTY))


# A Storyteller treats the Sailor's drunkenness as the price the town pays
# for having somebody who cannot die, not as a weapon to point at evil. So
# the Sailor drunking itself is ordinary, and the Sailor drunking the evil
# player it happened to pick is not — possible, but rarely what happens.
SAILOR_ON_EVIL_PENALTY = 0.15


@impairment.source_rule
def a_sailor_drunks_one_of_two(world, state, night):
    """Either the Sailor or whoever it chose, and it is not told which.

    It has to choose somebody living, so the reach is the living table
    plus itself. Landing on the Sailor is the common case and priced as
    such; landing on an evil seat is the one a Storyteller avoids.
    """
    if not _in_bag(state, "Sailor"):
        return []
    phase = f"N{night}"
    seat = world.find_at("Sailor", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    # Whoever came back tonight was dead when its turn came — a Shabaloth
    # regurgitates at 27 and a Professor raises at 43, and the Sailor
    # chooses at 4. The same for the Innkeeper at 9 and the Exorcist at
    # 21: no choice, so nobody drunk and nobody guarded.
    if seat in _returned_at(state, phase):
        return []

    def price(hit):
        if hit == seat:
            return 0.6                    # the usual half of the coin
        return SAILOR_ON_EVIL_PENALTY if world.evil_at(hit, phase) else 0.6

    # It is one of two: the Sailor, or whoever it chose. Recorded, that
    # is a pair rather than the whole table — which is most of what
    # confirming a Sailor is worth.
    picked = _chosen(state, "Sailor", night)
    reach = (state.alive_set(phase) if picked is None
             else frozenset({seat}) | picked)
    return [impairment.Source("Sailor", reach, capacity=1,
                              cost=price, repeat_cost=price)]


@impairment.source_rule
def a_goon_drunks_whoever_chose_it(world, state, night):
    """The first person to point at the Goon that night goes drunk.

    Only the first, and only somebody whose ability actually chooses a
    player — a Courtier names a character and never triggers one. Nobody
    records who chose whom, so the reach is everybody who could have.

    The Goon's own side follows whoever got there first, and it can go
    back and forth all game. That is handled where it shows: its side is
    open, so an Empath counting neighbours has to allow both.
    """
    if not _in_bag(state, "Goon"):
        return []
    phase = f"N{night}"
    goon = world.find_at("Goon", phase)
    if goon is None or goon not in state.alive_set(phase):
        return []
    pickers = frozenset(
        seat for seat in state.alive_set(phase)
        if seat != goon and CHARACTERS[world.role_at(seat, phase)].chooses)
    if not pickers:
        return []
    # On offer, never forced. With one chooser left alive this was a free
    # source that could reach everybody it could reach — which the plan
    # reads as unavoidable, so the last Sailor standing was drunk every
    # night whether or not it had pointed at the Goon. Found when a Sailor
    # walked away from the gallows and had to have been sober
    # (03.10.2026).
    free = lambda who: 1.0
    return [impairment.Source("Goon", pickers, capacity=1,
                              cost=free, repeat_cost=free)]


@impairment.source_rule
def a_courtier_names_a_character(world, state, night):
    """Whoever holds the named character, drunk for three days and nights.

    The reach depends on the world being scored, not on the night: the
    Courtier named a character, and which seat that lands on is different
    in every world. Nobody holding it means nothing happens — and the
    ability is spent all the same.

    Free rather than lucky. It is a declared action, not a guess, so
    there is nothing to have got right.
    """
    if not _in_bag(state, "Courtier"):
        return []
    out = []
    for info in state.infos:
        if not isinstance(info, CourtierChoice):
            continue
        # Three days and nights: the span it was used in and the two after.
        if not info.night <= night <= info.night + 2:
            continue
        phase = f"N{night}"
        courtier = world.find_at("Courtier", phase)
        if courtier is None or courtier != info.player:
            continue                      # not really the Courtier here
        # Only while the Courtier lives. A drunkenness rests when the one
        # causing it dies (table ruling, 02.10.2026) — and this ran the
        # full three days regardless, so a Sailor the dead Courtier had
        # named was still "drunk" when it walked away from the gallows.
        if courtier not in state.alive_set(phase):
            continue
        # And it *ends* there. An ability ends with the death of whoever
        # has it, and a character that comes back is a new instance with
        # the ability afresh (table ruling, 03.10.2026): what the old
        # Courtier named is sober for good, and the new one names again
        # — which is a new row, and its own three days.
        if _died_between(state, courtier, info.night, night):
            continue
        hit = world.find_at(info.role, phase)
        if hit is None:
            continue                      # named somebody nobody is
        # In the span the Courtier dies, the named one is drunk for part
        # of it and sober for the rest — and a night and its day are one
        # key here. So there it is on offer rather than forced: free to
        # explain something that went wrong, and no bar to something
        # that worked.
        went = any(at in state.died_at(courtier)
                   for at in (phase, f"D{night}"))
        free = (lambda who: 1.0) if went else 1.0
        out.append(impairment.Source("Courtier", frozenset({hit}),
                                     capacity=1, cost=free,
                                     repeat_cost=free))
    return out


@impairment.source_rule
def a_minstrel_silences_the_table(world, state, night):
    """A Minion executed, and everybody else is drunk until dusk tomorrow.

    Which is the whole table at once, for nothing — by far the largest
    lever on this script. Two Minions executed on consecutive days gives
    two such nights running, which is the thing to check if the span
    arithmetic is wrong.

    Covers the night after the execution and the day following it. The
    remainder of the execution day itself is not covered: a night and its
    day share one key here, and stretching it back would wrongly excuse
    readings from a night that had already happened.
    """
    if not _in_bag(state, "Minstrel"):
        return []
    phase = f"N{night}"
    seat = world.find_at("Minstrel", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    # There to hear it: a Minstrel raised tonight was dead when the
    # Minion hanged, and its ability did nothing.
    if seat not in state.alive_set(f"D{night - 1}"):
        return []
    # "If a Minion *died* by execution." One that walked away — a Devil's
    # Advocate's pick — silences nobody, and this used to drunk the whole
    # table for it.
    executed = state.execution_death(night - 1)
    if executed is None:
        return []
    if world.team_at(executed, f"D{night - 1}") != "minion":
        return []
    everyone = frozenset(p for p in range(state.n_players) if p != seat)
    return [impairment.Source("Minstrel", everyone, capacity=len(everyone),
                              cost=1.0, repeat_cost=1.0)]


@impairment.source_rule
def an_innkeeper_drunks_one_of_the_two_it_guards(world, state, night):
    """One of the pair it protected, and it does not choose which.

    Lasts the night and the day after, which needs no special handling:
    a night and the day that follows it share one span already, because
    poison works the same way.
    """
    if not _in_bag(state, "Innkeeper"):
        return []
    phase = f"N{night}"
    seat = world.find_at("Innkeeper", phase)
    if seat is None or night < 2 or seat not in state.alive_set(phase):
        return []
    if seat in _returned_at(state, phase):
        return []                         # back tonight, after its turn
    # One of the two it protected, and it does not choose which — so a
    # recorded choice narrows the drunk from the table to a pair.
    picked = _chosen(state, "Innkeeper", night, ("a", "b"))
    reach = state.alive_set(phase) if picked is None else picked
    return [impairment.Source("Innkeeper", reach,
                              capacity=1, cost=0.5, repeat_cost=0.5)]


def _impairment_plan(world, state, failures, forbidden):
    """Who had to be impaired each night, and what that cost.

    Returns ({night: {source: seat}}, cost) or None if no arrangement of
    the sources in play could have produced what the world needs.

    `failures` is who must have been impaired — a reading that came out
    false, an ability that did not fire. `forbidden` is who must not have
    been: a Monk that is the only explanation for a quiet night was
    working, so nothing can have stopped it.
    """
    got = _plan_as_given(world, state, failures, forbidden)
    if got is not None:
        return got
    # A Courtier that was itself drunk or poisoned when it chose made
    # nobody drunk at all. Its drunkenness is unavoidable while it
    # stands, so a world that needs the named character *working* fails
    # above — and then the other story is tried: the Courtier impaired
    # on the night it chose, and its three days never happening.
    #
    # The same goes for a Philosopher: one that was drunk or poisoned
    # when it chose gained nothing and drunk nobody.
    for info in state.infos:
        source = getattr(info, "source_role", None)
        if source not in ("Courtier", "Philosopher") \
                or not getattr(info, "role", None):
            continue
        phase = f"N{info.night}"
        holder = info.player
        if world.role_at(holder, _before(info.night, phase)) != source \
                and world.role_at(holder, phase) != source:
            continue
        again = {night: set(seats) for night, seats in failures.items()}
        again.setdefault(info.night, set()).add(holder)
        got = _plan_as_given(world, state, again, forbidden,
                             without=(source,))
        if got is not None:
            return got
    return None


def _plan_as_given(world, state, failures, forbidden, without=()):
    plan, total = {}, 1.0
    previous = {}
    nights = set(failures) | set(forbidden)
    for night in sorted(nights):
        wanted = failures.get(night, set())
        blocked = forbidden.get(night, set())
        if wanted & blocked:
            return None                   # asked to be both at once
        sources = impairment.sources_on(world, state, night)
        if without:
            sources = [s for s in sources if s.name not in without]
        got = impairment.plan_night(
            sources, sorted(wanted), sorted(blocked), previous)
        if got is None:
            return None
        cost, hits = got
        total *= cost
        plan[night] = hits
        previous = dict(previous, **hits)
    return plan, total


def row_outcomes(world, state):
    """What became of each recorded reading in this world.

    Returns {row index: outcome}. Four of them, because true-or-false is
    not enough: a reading can hold, or be false and need excusing, or
    have been made up by the Storyteller for somebody holding the wrong
    token, or have no possible source in this world at all. The middle
    two are not the speaker lying — they are the speaker being wrong
    without knowing it.
    """
    outcome = {}
    _explain(world, state, outcome)
    return outcome


def _before(night, phase):
    """The board as it stood when this night began.

    On night one there is no earlier phase — `N1` is index zero — so a
    swap written at N1 is already in the board at N1, and asking there
    finds the seat the character ended up at rather than the seat that
    acted. The **deal** is the board before night one, and `role_at` on a
    world with no changes gives exactly that.

    Written once because three call sites need it and each got it
    slightly differently the first time.

    `"N0"` rather than something like `"deal"`: it has to survive
    `phase_index`, which parses a letter and a number and raises on
    anything else. A sentinel that only works in the paths that never
    index it is a trap for whoever adds the fourth call site.
    """
    return f"E{night - 1}" if night > 1 else "N0"


def _the_balloonist_holds_up(world, state):
    """The chain, judged against whether a Vortox is in play.

    Sober, consecutive shown players must be *different* character types.
    Under a Vortox they must be the **same** — the reading is false, and
    false here is not a wrong player but an unchanged type.

    A droisoned Balloonist is told anything, so a night where it was not
    working exempts the pair that ends on it. Whether it was droisoned is
    settled later by the impairment plan, so this asks only whether the
    chain is *possible*, and lets the plan pay for the rest.
    """
    rows = [info for info in state.infos
            if getattr(info, "source_role", None) == "Balloonist"]
    if len(rows) < 2:
        return True

    # Only where the seat that spoke really holds it.
    #
    # These rows are what somebody *said*. In a world where that seat is
    # not the Balloonist, they are a lie or a mistake and the chain has
    # no business fitting — judging it anyway threw out every world in
    # which the claim was false, which is most of them. A fifth of
    # generated boards stopped being solvable at all.
    #
    # The rest of the solver reaches this through `_plain_failures`,
    # which traces each row to a source seat; this check is outside that
    # machinery because it is about the board rather than a row, and so
    # it has to ask the same question for itself.
    speaker = rows[0].player
    if any(info.player != speaker for info in rows):
        return True                       # more than one claimant: no chain
    if world.role_at(speaker, f"N{rows[0].night}") != "Balloonist":
        return True                       # not the Balloonist here
    vortox = world.find("Vortox")
    if vortox is not None:
        return _balloonist_all_same(world, state, rows)
    return a_balloonist_chain_fits(world, state)


def _balloonist_all_same(world, state, rows):
    """Under a Vortox every consecutive pair is the same type."""
    rows = sorted(rows, key=lambda info: info.night)
    reachable = _balloonist_types(world, rows[0].target, rows[0].night)
    for info in rows[1:]:
        here = _balloonist_types(world, info.target, info.night)
        shared = reachable & here
        if not shared:
            return False
        reachable = shared
    return True


def _balloonist_types(world, seat, night):
    """Every character type this seat could have been shown as."""
    role = world.role_at(seat, f"N{night}")
    if role is None:
        return set()
    return {TEAM[role]} | set(CHARACTERS[role].registers)


def a_balloonist_chain_fits(world, state):
    """Could a Balloonist have been shown these players, in this order?

    Each night's player must be a different **character type** from the
    night before — and registration applies, so a Recluse counts as
    Outsider, Minion *or* Demon and one seat can satisfy several links.
    The wiki notes a devious Storyteller could show the Recluse every
    night.

    So this is a search rather than a comparison: is there a choice of
    type for each shown player, from the types that player could
    register as, such that no two consecutive nights match?

    A droisoned night is exempt — the Storyteller may show any type — but
    the player shown still becomes "the previous" for the night after,
    which the wiki's own example turns on.

    Under a Vortox the reading must be false, and false here means the
    types were the **same**. Handled by the caller, which knows whether
    the world is inverted; this answers the sober question.
    """
    rows = sorted((info for info in state.infos
                   if getattr(info, "source_role", None) == "Balloonist"),
                  key=lambda info: info.night)
    if len(rows) < 2:
        return True                       # nothing to contradict

    def types_for(seat, phase):
        role = world.role_at(seat, phase)
        if role is None:
            return set()
        out = {TEAM[role]}
        out |= set(CHARACTERS[role].registers)
        return out

    # Walk the chain, keeping every type the run could have ended on.
    #
    # **This is the sober question only.** A droisoned Balloonist may be
    # shown the same type as last night — the wiki's own example — and
    # which nights those were is the impairment plan's business, not
    # this function's.
    #
    # So a False here means "not without a droisoned night", never
    # "impossible". It was wired into scoring as though it meant the
    # latter and threw out seven of forty mixed-script boards. A check
    # that cannot price something must not judge it.
    reachable = types_for(rows[0].target, f"N{rows[0].night}")
    for info in rows[1:]:
        phase = f"N{info.night}"
        here = types_for(info.target, phase)
        nxt = {t for t in here if any(t != was for was in reachable)}
        if not nxt:
            return False
        reachable = nxt
    return True


def best_story(world, state, outcome=None, viable=None):
    """The cheapest account of this world: (cost, changes).

    (None, ()) means nothing explains it. The changes come back as well
    as the cost because the report needs them — after a handover, "who is
    the Demon" has a different answer than the deal gives.

    `outcome`, if given, is filled with what became of each reading under
    the story that won. `viable`, if given, is filled with every story
    that fits, as (cost, changes) — see `_story_shares`.
    """
    # A new epoch for the memos below (`sources_on`, `_explained_night`,
    # the Barber's offers). They save work between the stories of one
    # world; kept past that, a constant or a rule changed between two
    # solves of the same world would be answered from before the change.
    state._epoch = next(_EPOCHS)
    stories = possible_timelines(world, state)
    if not stories:
        return None, ()
    if stories == [((), 1.0)]:
        cost = _explain(world, state, outcome)
        if viable is not None and cost is not None:
            viable.append((cost, ()))
        return cost, ()

    best, best_changes, best_marks = None, (), None
    for changes, weight in stories:
        view = Timeline(world, changes) if changes else world
        marks = {} if outcome is not None else None
        cost = _explain(view, state, marks)
        if cost is None:
            continue
        cost *= weight
        if viable is not None:
            viable.append((cost, changes))
        if best is None or cost > best:
            best, best_changes, best_marks = cost, changes, marks
    if outcome is not None and best_marks:
        outcome.update(best_marks)
    return best, best_changes


def _report_phase(state):
    """The moment the report describes: now, but never before day one.

    Nobody reads the board during the first night. What the table learns
    that night is only said out loud on day one, and by then the Ogre has
    picked its side and a Snake Charmer's swap has happened. Asking at
    "N1" showed a fresh board with every Ogre good, because its change is
    written from the first day. `final_phase` itself stays as it is: the
    rules use it to know how far the game went, and that is a different
    question.
    """
    now = state.final_phase()
    return now if phase_index(now) >= phase_index("D1") else "D1"


def _story_shares(world, viable, state=None):
    """Each fitting story as (view, share of the world's weight).

    **A world weighs what its best story costs** — that is unchanged, and
    it is what every count and every comparison between worlds rests on.
    What changes is who gets the credit inside it. Only the best story
    used to be tallied, so an Ogre that may have turned evil showed as
    plainly good whenever staying good cost nothing, and after a starpass
    the likeliest heir took the whole of "who is the Demon now" while the
    others got none.

    So the weight is split across the stories in proportion to what each
    costs. An Ogre beside two evil seats out of six turns evil in a third
    of its stories' weight, which is what a random pick would do.
    """
    # A Barber swap gets the share the table gives it, not its price:
    # see `_barber_share`. Only asked where a swap was open at all.
    if state is not None and len(viable) > 1 and _in_bag(state, "Barber") \
            and barber_claimants(state):
        viable = [(cost * _barber_share(world, changes, state), changes)
                  for cost, changes in viable]
    total = sum(cost for cost, _changes in viable)
    if total <= 0:
        return []
    return [(Timeline(world, changes) if changes else world, cost / total)
            for cost, changes in viable]


def explanation_cost(world, state):
    """How much explaining this world needs, as a multiplier, or None.

    None means nothing can explain it. 1.0 means every statement stands on
    its own. Anything less is the price of the excuses required: invented
    information, a Poisoner who had to aim precisely, a kill sunk into a
    corpse.

    Where the Demon changed hands there is more than one story to try, so
    this takes the best of them. A starpass is not charged for on top: the
    Demon's own seat dying at night is already discounted hard by the
    night-death prior, and billing it twice would be double-counting.
    """
    return best_story(world, state)[0]


def _moments_with_two_left(state):
    """Every moment the game was going on with two or fewer on the board
    as alive. Almost always none, and worked out once a board.

    A moment is the start of a night or of a day. The game was going on
    at each one the board reaches — something is recorded at it or after
    it — and at the one after the last, which is now, unless the board
    says the game is over.
    """
    cached = getattr(state, "_two_left_cache", None)
    if cached is not None:
        return cached
    final = phase_index(state.final_phase())
    out = []
    night = 1
    while True:
        beyond = False
        for phase in (f"N{night}", f"D{night}"):
            if phase_index(phase) > final:
                beyond = True
                if getattr(state, "game_over", False):
                    break
            if len(state.alive_set(phase)) <= 2:
                out.append(phase)
            if beyond:
                break
        if beyond:
            break
        night += 1
    state._two_left_cache = out
    return out


def _the_game_went_on(world, state):
    """Evil wins with two players alive, so while the game goes on there
    are three.

    The solver takes the game to be going on and never asked how many
    that needs. With a Zombuul it is the whole clue: two on the board
    and no winner means somebody the table crossed off is alive, and
    only a Zombuul that died once is. Without the rule a Zombuul playing
    dead led in 3 games of 44; in half of those the board showed two
    alive, and there the solver still gave the living most of the
    weight (04.10.2026).

    So where two are left: a Zombuul on the board as dead makes three
    and the world stands. Any other Demon still standing has won, and
    the world goes. A Demon that is really dead leaves a Mastermind's
    day or nothing, which the lineage settles and this does not.

    **Only with a Zombuul on the script** (table decision, the same
    day). The rule is true everywhere, but elsewhere it can only ever
    say "this game is over" — and a board somebody enters after the end
    would turn from an answer into "impossible".
    """
    if not _in_bag(state, "Zombuul"):
        return True
    for phase in _moments_with_two_left(state):
        board = state.alive_set(phase)
        demon = world.demon_at(phase)
        if demon is None:
            continue
        if demon in board:
            return False                  # it would have won there and then
        if world.role_at(demon, phase) == "Zombuul" \
                and _zombuul_still_going(world, state, demon, phase) \
                and len(board) < 2:
            return False                  # it and one other: won as well
    return True


def _explain(world, state, outcome=None):
    """The cost of one telling of this world, with the lineage settled."""
    if not _the_game_went_on(world, state):
        return None
    failures, ft_infos, invented_factor, must_work = _plain_failures(
        world, state, outcome)
    if failures is None:
        return None
    vortox_or = getattr(state, "_vortox_or", None) or {}

    # Every way the nights could have gone. Each brings its own demands
    # on who was impaired and who was working, so the impairment plan is
    # solved once per account and the cheapest wins.
    accounts = _night_accounts(world, state, failures, must_work)
    if not accounts:
        return None

    # An Acrobat's death is evidence about the *plan* rather than about
    # the board, which no other character's is.
    #
    # It picked somebody; if that seat is or **becomes** droisoned that
    # night, the Acrobat dies. The "becomes" is why this cannot be
    # settled in night order — a Poisoner reaching the seat after the
    # Acrobat chose still kills it — so it is settled here, where the
    # night's droisoning is decided.
    #
    # Dead it demands the target impaired; alive it forbids that. And a
    # dead player may be picked: the Drunk is drunk whether or not it is
    # breathing.
    acro_wanted, acro_needed = {}, {}
    for info in state.infos:
        if not isinstance(info, AcrobatChoice):
            continue
        night = info.night
        phase = f"N{night}"
        seat = world.find_at("Acrobat", phase)
        if seat is None or seat != info.player:
            continue                      # somebody else's claim
        if seat not in state.alive_set(phase):
            continue                      # already gone; it did not act
        # And an Acrobat death is deliberately left saying nothing too.
        #
        # An Acrobat says nothing here, dead or alive.
        #
        # Dead: it can die of anything, and only the death machinery knows
        # whether its own ability was the cause. Alive: that means its
        # pick was clean *or* it was itself droisoned, and the plan holds
        # sets of seats, not disjunctions. Forbidding the pick outright
        # rules out a legal board where both were poisoned.

    def settle(readings):
        best = None
        for night_cost, impaired, working in accounts:
            # The accounts come dearest last, and a plan never makes one
            # better than it is: every price a source asks is at most
            # one. So once what an account could reach at best is no
            # more than what is already in hand, neither this one nor
            # any after it can win, and their plans need not be tried.
            #
            # A stopped Demon made this worth having (04.10.2026). A
            # quiet night gained explanations, the accounts multiplied,
            # and a long Bad Moon Rising board took half as long again
            # — nearly all of it spent planning accounts that had
            # already lost.
            if best is not None and night_cost * invented_factor <= best:
                break
            wanted = {n: set(seats) for n, seats in readings.items()}
            for night, seats in acro_wanted.items():
                wanted.setdefault(night, set()).update(seats)
            for night, seats in impaired.items():
                wanted.setdefault(night, set()).update(seats)
            # Whoever walked away from an execution had to be working
            # across that span — which is the same span as the night
            # before it, so it lands in the plan alongside everything else.
            needed = {n: set(seats) for n, seats in working.items()}
            for night, seats in acro_needed.items():
                needed.setdefault(night, set()).update(seats)
            for day, seats in (must_work or {}).items():
                needed.setdefault(day, set()).update(seats)
            planned = _impairment_plan(world, state, wanted, needed)
            if planned is None:
                continue
            got = planned[1] * night_cost * invented_factor
            if best is None or got > best:
                best = got
        return best

    def settle_either(readings):
        """`settle`, trying each way a true reading under a Vortox can be
        excused: per night, the Vortox off, or every source droisoned.
        One of the two covers the whole night, so this is two choices a
        night rather than one per reading."""
        nights = sorted(vortox_or)
        if not nights:
            return settle(readings)
        best = None
        for picks in product((True, False), repeat=min(len(nights), 6)):
            trial = {n: set(seats) for n, seats in readings.items()}
            for night, off in zip(nights, picks + (True,) * 6):
                vortox, sources = vortox_or[night]
                trial.setdefault(night, set()).update(
                    {vortox} if off else sources)
            got = settle(trial)
            if got is not None and (best is None or got > best):
                best = got
        return best

    ceiling = settle_either(failures)
    if ceiling is None:
        return None
    if not ft_infos:
        return ceiling
    for _info, _src, idx, _vortox in ft_infos:
        if outcome is not None:
            outcome[idx] = HELD           # replaced below if a herring is used

    # The herring only matters when it sits in one of the pairs the
    # Fortune Teller asked about, so those are the only seats worth
    # trying - plus one uninvolved seat to stand for "somewhere else".
    asked = {x for info, *_rest in ft_infos for x in (info.a, info.b)}
    herrings = [p for p in asked if not is_evil(world.roles[p])]
    for p in range(state.n_players):
        if p not in asked and not is_evil(world.roles[p]):
            herrings.append(p)
            break

    best, best_marks = None, None
    for rh in herrings:
        combined = {night: set(seats) for night, seats in failures.items()}
        marks = {}
        for info, src, idx, vortox in ft_infos:
            fits = info.holds(world, state, rh, src)
            if vortox is not None:
                # Under a Vortox it is the other way about: an answer
                # that fits was true, and then the Vortox was not
                # working. The seat's own droisoning excuses nothing.
                fits, src = not fits, vortox
            if fits:
                marks[idx] = HELD
            else:
                combined.setdefault(info.night, set()).add(src)
                marks[idx] = EXCUSED
        cost = settle_either(combined)
        if cost is None:
            continue
        if best is None or cost > best:
            best, best_marks = cost, marks
        if best >= ceiling:
            break                         # cannot do better than this
    if outcome is not None and best_marks is not None:
        outcome.update(best_marks)
    return best


def world_consistent(world, state):
    return explanation_cost(world, state) is not None


# --------------------------------------------------------------------------
# Weighting
# --------------------------------------------------------------------------

def is_lying(world, state, p):
    """Is seat p saying something they know to be false in this world?

    Covers both kinds of claim: the role they named, and anything softer
    they said about waking at night. The Drunk is not lying either way -
    they believe their token, and they are woken on its schedule.
    """
    role = world.roles[p]
    believed = world.believes[p]

    # Somebody handed the wrong token is not lying when they name it.
    # That holds however evil the character underneath turns out to be —
    # a Marionette believes what it says as sincerely as the Drunk does.
    claim = state.claims.get(p)
    if claim and not (role == claim
                      or (believes_another(role) and believed == claim)):
        return True

    said = (getattr(state, "wakes", None) or {}).get(p)
    if said and not wake_fits(role, believed, said):
        return True
    return False


def in_play(world, role):
    """Is this role on the grimoire at all?

    A Drunk's token counts: the Storyteller put it on the board, so the
    Demon was never offered it as a bluff.
    """
    return role in world.roles or role in world.believes


def night_death_factor(night):
    """Weight kept by a world in which an early night victim is evil.

    Counted from night 2, the first night anyone can die.
    """
    return min(1.0, NIGHT_DEATH_EVIL_PENALTY * max(night - 1, 1))


def confirmed_boost(world, state):
    """What the table's confirmations are worth to a world.

    A reading the players later agreed was *right* is evidence that its
    source really is that character. It multiplies rather than settles
    anything: four confirmed rows from one seat compound, and no pile of
    them reaches certainty, because a Spy reading the grimoire can feed a
    Minion true information all game.

    Counted only where the world agrees the seat holds the character —
    the boost is *for* that reading having come from who it says.
    """
    got = 1.0
    for info in state.infos:
        if not getattr(info, "confirmed", False):
            continue
        seat = info.source_seat(state)
        if seat is None:
            continue
        source = getattr(info, "source_role", None)
        if source and world.role_at(seat, f"N{info.night}") == source:
            got *= CONFIRMED_READING_STEP
    return got


# Damping a thin board's priors was tried here and removed. The note is
# kept because the measurement is worth more than the change was.
#
# The idea: below about four weighed readings, raise `prior_weight` to a
# power under one, so a stack of penalties stops separating worlds
# thirty-fold on the strength of two or three coincidences. It ranked
# worlds identically and only touched thin boards.
#
# It did not work, for two reasons.
#
# **Most confident calls are not from thin boards.** Nine of thirty-four
# came from boards with fewer than four readings; the rest had plenty and
# were untouched by construction. Trouble Brewing's worst calibration gap
# moved 40.8 to 40.7.
#
# **And on a thin board the weights are not the problem.** On the board
# that prompted all this, the suspected seat is evil in **50.6% of
# surviving worlds, unweighted**. No reweighting gets below that — the
# search itself favours it. Pushing the damping from 0.45 to 0.1 moved
# the reading 58.8% to 55.9% and would asymptote at 50.
#
# **It also made Bad Moon Rising worse**, 11.5 to 20.1, which is the
# thing a change like this must not do: fixing one script by spoiling
# another is not a fix.
#
# The real finding is that thin-board overconfidence is a property of the
# *world population*, not of the weighting. Half the legal worlds have
# that seat evil, so any honest summary says about half. Making the
# solver quieter there means changing which worlds are legal, not how
# they are weighed.

def _could_have_inherited(world, state):
    """Seats whose claim could be honest because they were handed it.

    A Farmer that dies at night gives the character to a living good
    player, who then says "I am the Farmer" — truthfully. `is_lying`
    compares against the character they were *dealt*, so it says yes, and
    a good seat that lies pays `TOWNSFOLK_LIE_PENALTY` at 0.02.

    A Demon bluffing the same character pays only
    `BLUFF_COLLISION_PENALTY` at 0.3, so without this the honest heir
    weighed fifteen times less than the bluff.

    Only the seat that claims the character, only when a seat claiming
    the same character died at night, and only for characters that hand
    themselves on.
    """
    handed = {"Farmer"}
    claims = state.claims or {}
    died_at_night = set()
    for seat, at in (state.deaths or {}).items():
        phases = (at,) if isinstance(at, str) else tuple(at or ())
        if any(x.startswith("N") for x in phases):
            died_at_night.add(seat)

    out = set()
    for seat, claim in claims.items():
        if claim not in handed or seat in died_at_night:
            continue
        # **Only where the claim could be true.** An evil seat cannot
        # have been handed the Farmer, so exempting it too just made the
        # demon's bluff cheaper — both worlds went to 1.0 and the answer
        # got worse, 95.5 to 98.6.
        if is_evil(world.roles[seat]):
            continue
        if any(claims.get(other) == claim for other in died_at_night):
            out.add(seat)
    return out


def _madness_nights(world, state):
    """How many nights a Cerenovus was alive to make somebody mad.

    Each is one good player who may be claiming a character they are
    not — see `CERENOVUS_MADNESS_PENALTY`.
    """
    last = state.final_phase()
    nights = int(last[1:]) if last[1:].isdigit() else 0
    got = 0
    for night in range(1, nights + 1):
        who = world.find_at("Cerenovus", f"N{night}")
        if who is not None and minion_still_acts(world, state, who,
                                                 f"N{night}"):
            got += 1
    return got


def prior_weight(world, state):
    """Everything that makes a world plausible except the poison story."""
    w = confirmed_boost(world, state)
    reads = getattr(state, "reads", None) or {}
    suspects = getattr(state, "suspects", None) or {}
    bluffs = defaultdict(int)
    for p in range(state.n_players):
        if is_evil(world.roles[p]) and is_lying(world, state, p):
            claimed = state.claims.get(p)
            if claimed:
                bluffs[claimed] += 1

    inherited = _could_have_inherited(world, state)
    madness = _madness_nights(world, state)

    for p in range(state.n_players):
        evil = is_evil(world.roles[p])
        if is_lying(world, state, p) and p not in inherited \
                and not must_hide(world.roles[p]):
            # A Mutant's cover story is not a choice (catalogue `hides`),
            # so it costs the world nothing.
            if not evil:
                if TEAM[world.roles[p]] == "outsider":
                    w *= OUTSIDER_HIDING_PENALTY
                elif madness > 0:
                    w *= CERENOVUS_MADNESS_PENALTY
                    madness -= 1
                else:
                    w *= TOWNSFOLK_LIE_PENALTY
            else:
                claim = state.claims.get(p)
                if claim and (in_play(world, claim) or bluffs[claim] > 1):
                    w *= BLUFF_COLLISION_PENALTY
        step = reads.get(p, 0)
        if step and evil:
            w *= READ_ODDS_STEP ** step
        if suspects.get(p) and believes_another(world.roles[p]):
            w *= DRUNK_SUSPICION_STEP

    for p, phase in state.death_phases():
        if not phase or phase[0].upper() != "N":
            continue                      # executions say nothing by themselves
        if is_evil(world.roles[p]):
            w *= night_death_factor(int(phase[1:]))
    return w


def world_weight(world, state):
    cost = explanation_cost(world, state)
    if cost is None:
        return 0.0
    return prior_weight(world, state) * cost


def ranked(valid, state):
    """(weight, world) pairs, most plausible first."""
    pairs = [(world_weight(w, state), w) for w in valid]
    pairs.sort(key=lambda x: -x[0])
    return pairs


# --------------------------------------------------------------------------
# Solving
# --------------------------------------------------------------------------

def solve(state, allow_good_lies=False, max_worlds=DEFAULT_MAX_WORLDS):
    all_worlds = enumerate_worlds(state.n_players, state.claims,
                                  getattr(state, "certainties", None),
                                  allow_good_lies=allow_good_lies,
                                  max_worlds=max_worlds,
                                  forced=forced_roles(state),
                                  wakes=getattr(state, "wakes", None),
                                  script=state.script,
                                  fabled=getattr(state, "fabled", ()))
    if len(all_worlds) >= max_worlds:
        print(f"WARNING: hit the cap of {max_worlds:,} worlds. The result is\n"
              "incomplete. Add more claims, or raise max_worlds if you can wait.")
    valid = [w for w in all_worlds if world_consistent(w, state)]
    return all_worlds, valid


def sampled_rows(state, dives=8000, rng=None, allow_good_lies=False):
    """A per-seat picture from random walks rather than enumeration.

    For boards too big to enumerate. Two measurements hit that wall
    before this existed — a Sects & Violets calibration and a fifteen
    player table — and neither is an unusual board, they are just wide.

    A dive that hits a dead end yields nothing and still counts, because
    dropping those would bias the answer towards whatever is easy to
    reach. The weight each world carries is the walk's own correction
    times the ordinary explanation cost, so a sampled table means the
    same thing as an enumerated one.
    """
    from botc.worlds import sample_worlds, _sampling_setups, DEFAULT
    # Fall back to allowing good lies when nothing else fits, the same as
    # `solve` does. A board where every seat claims a Townsfolk needs
    # somebody hiding, and without that the sampler has no bag to walk at
    # all — it returned nothing on the first real board it was handed.
    if not allow_good_lies:
        setups = _sampling_setups(
            state.n_players, state.claims,
            getattr(state, "certainties", None), False, forced_roles(state),
            getattr(state, "wakes", None), state.script or DEFAULT,
            tuple(getattr(state, "fabled", ())))
        if not setups:
            allow_good_lies = True

    seen, weights = [], []
    for world, share in sample_worlds(
            state.n_players, state.claims,
            certainties=getattr(state, "certainties", None),
            allow_good_lies=allow_good_lies,
            forced=forced_roles(state),
            wakes=getattr(state, "wakes", None),
            dives=dives, rng=rng or random.Random(),
            script=state.script, fabled=tuple(getattr(state, "fabled", ()))):
        if world is None or share <= 0:
            continue
        cost = explanation_cost(world, state)
        if cost is None:
            continue
        seen.append(world)
        weights.append(share * prior_weight(world, state) * cost)
    if not seen:
        return []
    return summarize(seen, state, weights)


def solve_or_repair(state, max_worlds=DEFAULT_MAX_WORLDS):
    """Solve, and if nothing fits, ask who might have lied.

    Repair on demand rather than enumeration, which is the same shape the
    Pit-Hag uses: do not widen the search for a possibility, posit it
    only when something would otherwise be false.

    The alternative was letting every Townsfolk claim be any Townsfolk,
    which takes a nine-player board from a hundred worlds to a quarter of
    a million — so the truth goes missing anyway, now through truncation
    rather than through the search being too narrow. This costs nothing
    on an ordinary board and only pays where it is needed.

    Returns (all, valid, liar) — the seat that had to be lying, or None
    when the board fitted without anybody.

    Repairs are searched with good lies allowed, which was missing at
    first: the board did not fit, so somebody said something untrue, and
    an Outsider hiding behind a Townsfolk claim is by far the commonest
    way. Opening a claim and then refusing to consider the ordinary
    reason it needed opening was self-defeating.

    Worth being plain about the limit, and it is a real one. This fires
    when a board fits nothing or almost nothing. A board can also be
    *confidently wrong*: two good players lied in one played game, the
    search could not represent one of the lies, ninety-six worlds
    survived, and it named an innocent seat at 58% while the real Demon
    sat at zero.

    Nothing inside the solver distinguishes that from a board it has
    genuinely solved — high confidence is what both look like. Detecting
    it needs the thing the search cannot do: represent a Townsfolk
    claiming to be a different Townsfolk. Until that is affordable, this
    catches the impossible boards and not the misleading ones, and saying
    so is better than a guard that fires on the wrong signal.
    """
    everything, valid = solve(state, max_worlds=max_worlds)
    if len(valid) > _CORNERED:
        return everything, valid, None

    # Nothing fits, or so little fits that the board has been argued into
    # a corner. The second case is the one that matters and it took a
    # played game to see: a good player chaos-claimed the Saint while
    # somebody really was the Saint, seven worlds survived, and the real
    # Demon was evil in none of them. Nothing was *impossible* — the
    # solver had simply committed, hard, to the wrong side of a
    # double-claim.
    #
    # So repair fires on a board that fits badly as well as one that fits
    # nothing. A handful of surviving worlds out of a legal space in the
    # thousands is not confidence, it is a board that has been told
    # something untrue.

    # Somebody said something untrue. Try them one at a time and keep
    # whoever gives the best-explained board, which is the cheapest
    # single lie rather than the first one that happens to work.
    # Start from what we have: a cornered board keeps its own answer
    # unless a posited lie explains it better. A board that fits nothing
    # starts from no answer at all, and any repair beats that — but the
    # placeholder still has to be a tuple, since the comparison below
    # indexes it. It was left as None, which worked on every board that
    # fitted something and fell over on the first that did not.
    best = (None, everything, valid, None)
    for seat in sorted(state.claims):
        opened = _without_claim(state, seat)
        # With good lies allowed, because that is the whole point of
        # repairing: the board did not fit, so somebody said something
        # untrue, and an Outsider hiding behind a Townsfolk claim is by
        # far the commonest way. Repairing without it opened a claim and
        # then refused to consider the ordinary reason it needed opening.
        #
        # On a tight budget: opening one seat *and* allowing hidden
        # Outsiders elsewhere hits the world cap and takes minutes per
        # seat, which is half an hour to repair one board. A repair
        # that expensive is not a repair.
        #
        # A tenth of the budget is enough: the answer, when there is one,
        # is usually found early, and a repair that needs a quarter of a
        # million worlds to show itself is not one worth waiting for.
        _all, got = solve(opened, allow_good_lies=True,
                          max_worlds=max(20_000, max_worlds // 10))
        if not got:
            continue
        # Weighed on a sample rather than all of it. A repaired board
        # can have twelve thousand surviving worlds and there are nine of
        # them to compare; weighing every one took longer than the search
        # that produced them. The comparison only needs to rank the nine,
        # and a few hundred worlds rank them the same way.
        sample = got if len(got) <= 400 else got[::len(got) // 400]
        weight = (sum(world_weight(w, opened) for w in sample)
                  * len(got) / len(sample))
        # A repaired board has to be *better explained*, not merely
        # larger: opening a claim always admits more worlds, so counting
        # them would repair every board on the table.
        if best[0] is None or weight > best[0]:
            best = (weight, _all, got, seat)
    _weight, _all, got, seat = best
    return _all, got, seat


def _without_claim(state, seat):
    """The same board with one seat treated as having said nothing."""
    claims = {p: c for p, c in state.claims.items() if p != seat}
    return GameState(
        n_players=state.n_players, script=state.script, claims=claims,
        certainties=dict(getattr(state, "certainties", {}) or {}),
        reads=dict(getattr(state, "reads", {}) or {}),
        wakes={p: w for p, w in (getattr(state, "wakes", {}) or {}).items()
               if p != seat},
        suspects=dict(getattr(state, "suspects", {}) or {}),
        deaths=dict(state.deaths or {}),
        resurrections=dict(getattr(state, "resurrections", {}) or {}),
        executions=dict(getattr(state, "executions", {}) or {}),
        quiet_nights=set(getattr(state, "quiet_nights", ()) or ()),
        days_done=set(getattr(state, "days_done", ()) or ()),
        game_over=bool(getattr(state, "game_over", False)),
        votes=dict(getattr(state, "votes", {}) or {}),
        nominations=dict(getattr(state, "nominations", {}) or {}),
        witch_deaths=dict(getattr(state, "witch_deaths", {}) or {}),
        madness_executions=dict(getattr(state, "madness_executions", {})
                                or {}),
        fabled=list(getattr(state, "fabled", ()) or ()),
        infos=list(state.infos), names=list(getattr(state, "names", []) or []))


def summarize(valid, state, weights=None):
    """Weighted per-seat picture. Percentages are shares of total weight.

    `weights` lets a caller supply its own, which is what sampling needs:
    a sampled world stands for however many the walk could have reached,
    so its weight has to carry that correction. Enumeration passes
    nothing and gets the ordinary calculation.
    """
    n = state.n_players
    if weights is None:
        weights = [world_weight(w, state) for w in valid]
    total = sum(weights)
    if total <= 0:
        total = 1.0

    rows = []
    for p in range(n):
        evil = demon = drunk = lying = 0.0
        roles = defaultdict(float)
        for w, wt in zip(valid, weights):
            role = w.roles[p]
            roles[role] += wt
            if is_evil(role):
                evil += wt
            if TEAM[role] == "demon":
                demon += wt
            if believes_another(role):
                drunk += wt
            if is_lying(w, state, p):
                lying += wt
        rows.append({
            "player": p,
            "claim": state.claims.get(p),
            "evil_pct": 100 * evil / total,
            "demon_pct": 100 * demon / total,
            "drunk_pct": 100 * drunk / total,
            "lying_pct": 100 * lying / total,
            "roles": sorted(((r, 100 * v / total) for r, v in roles.items()),
                            key=lambda x: -x[1]),
        })
    return rows


def print_report(valid, state, show_worlds=5):
    print(f"\nPossible worlds: {len(valid)}")
    if not valid:
        print("No consistent scenario. Either a good player is lying,")
        print("an info is missing, or a claim was entered incorrectly.")
        print("Try: solve(state, allow_good_lies=True)")
        return

    print("\n Player       | Claim          | evil  | demon | drunk | lying | most likely roles")
    print("-" * 104)
    for row in summarize(valid, state):
        top = ", ".join(f"{show(r)} {pc:.0f}%" for r, pc in row["roles"][:3])
        print(f"{state.label(row['player']):<13}| {show(row['claim']):<15}| "
              f"{row['evil_pct']:4.0f}% | {row['demon_pct']:4.0f}% | "
              f"{row['drunk_pct']:4.0f}% | {row['lying_pct']:4.0f}% | {top}")

    if show_worlds:
        print(f"\nMost plausible worlds (up to {show_worlds}):")
        for weight, w in ranked(valid, state)[:show_worlds]:
            parts = []
            for p, r in enumerate(w.roles):
                tag = show(r)
                if believes_another(r):
                    tag += f"(thinks {show(w.believes[p])})"
                parts.append(f"{p}={tag}")
            print("  " + "  ".join(parts))


def pilot_size(state, allow_good_lies=False, walks=1500, rng=None):
    """A rough count of how many legal worlds are out there.

    A few hundred random walks are enough to tell a search worth walking
    in full from one that is hopeless, and they cost a fraction of a
    second — much better than discovering it half a million worlds in.
    """
    rng = rng or random.Random(0)
    total = 0.0
    walked = 0
    for _world, stands_for in sample_worlds(
            state.n_players, state.claims, getattr(state, "certainties", None),
            allow_good_lies, forced_roles(state),
            getattr(state, "wakes", None), dives=walks, rng=rng,
            script=state.script, fabled=getattr(state, "fabled", ())):
        walked += 1
        total += stands_for
    return total / walked if walked else 0.0


def analyze(state, allow_good_lies=False, max_worlds=EXACT_LIMIT,
            keep_samples=8, dives=25_000, rng=None):
    """Score every legal world if that is feasible, or sample if not.

    Nothing is stored per world except running sums and a handful of the
    most plausible examples, so the exact path is limited by time rather
    than memory. Past that limit it stops counting and starts looking:
    see `estimate`.
    """
    if pilot_size(state, allow_good_lies) > max_worlds:
        return estimate(state, allow_good_lies, dives, keep_samples, rng)

    n = state.n_players
    now = _report_phase(state)
    acc = _accumulator(n)
    legal = valid = 0
    total = 0.0
    best = []

    # Two more things worked out in the same pass, because each used to
    # walk every world again and that trebled the cost of a solve.
    blame = {}
    blame_stride = 1
    executed = [(day, seat)
                for day, seat in sorted((state.executions or {}).items())
                if state.execution_death(day) == seat]
    hanged = {seat: 0.0 for _day, seat in executed}

    # What became of each reading, weighed across every surviving world.
    # Worked out in the same pass, because the story that settles a
    # world's cost is the same story that says which rows held.
    told = [defaultdict(float) for _ in state.infos]

    for world in iter_worlds(n, state.claims,
                             getattr(state, "certainties", None),
                             allow_good_lies, forced_roles(state),
                             getattr(state, "wakes", None), state.script,
                             getattr(state, "fabled", ())):
        legal += 1
        if legal > max_worlds:
            # Walking the whole search would take too long. Stop, throw
            # the partial count away — it is the first corner of the tree
            # and nothing like a fair sample — and go looking instead.
            return estimate(state, allow_good_lies, dives, keep_samples, rng)
        outcome = {}
        viable = []
        cost, changes = best_story(world, state, outcome, viable)
        if cost is None:
            continue
        view = Timeline(world, changes) if changes else world

        valid += 1
        wt = prior_weight(world, state) * cost
        for idx, mark in outcome.items():
            told[idx][mark] += wt
        total += wt
        for story, share in _story_shares(world, viable, state):
            _tally(acc, world, story, state, wt * share, n, now)
            for day, seat in executed:
                if story.demon_at(f"D{day}") == seat:
                    hanged[seat] += wt * share
        # Blame is a share rather than a count, so a spread of worlds
        # settles it as well as all of them — and working it out for
        # every world on a full script trebled the cost of a solve.
        # It follows the best story, like the readings' outcomes above.
        if valid % blame_stride == 0:
            _tally_blame(blame, view, state, wt * blame_stride)

        if len(best) < keep_samples:
            best.append((wt, world))
            best.sort(key=lambda x: x[0])
        elif wt > best[0][0]:
            best[0] = (wt, world)
            best.sort(key=lambda x: x[0])

    rows = _rows(acc, state, total)
    shares = {night: {seat: {name: value / (sum(causes.values()) or 1.0)
                             for name, value in causes.items()}
                      for seat, causes in seats.items()}
              for night, seats in blame.items()}
    hints = []
    if "Mastermind" in state.script.keys and total > 0:
        for day, seat in executed:
            odds = hanged[seat] / total
            if odds >= MASTERMIND_HINT:
                hints.append({"day": day + 1, "seat": seat,
                              "demon_pct": round(100 * odds, 1)})

    readings = []
    for idx, info in enumerate(state.infos):
        weight = sum(told[idx].values())
        readings.append({
            "index": idx,
            "type": type(info).__name__,
            "night": info.night,
            "player": info.player,
            "shares": {mark: value / weight for mark, value in
                       told[idx].items()} if weight > 0 else {},
        })

    best.sort(key=lambda x: -x[0])
    for row in rows:
        row["margin"] = 0.0
    return {"legal": legal, "valid": valid, "truncated": False,
            "sampled": False, "dives": 0, "ess": None,
            "rows": rows, "samples": [w for _wt, w in best],
            "blame": shares, "mastermind": hints, "readings": readings}


# --------------------------------------------------------------------------
# When there are too many worlds to count, look at a lot of them instead
# --------------------------------------------------------------------------

def _accumulator(n):
    return {"evil": [0.0] * n, "demon": [0.0] * n, "drunk": [0.0] * n,
            "lying": [0.0] * n, "roles": [defaultdict(float) for _ in range(n)]}


def _tally(acc, world, view, state, weight, n, phase):
    """Add one world to the running totals.

    Character and side are read from `view` at `phase` — the moment the
    game has reached — because after a handover the useful answer to
    "who is the Demon" is who holds it now, not who was dealt it. Lying
    is read from the deal, since a claim is about the whole game.
    """
    demon = view.demon_at(phase)
    for p in range(n):
        role = view.role_at(p, phase)
        acc["roles"][p][role] += weight
        if view.evil_at(p, phase):
            acc["evil"][p] += weight
        if p == demon:
            acc["demon"][p] += weight
        if believes_another(role):
            acc["drunk"][p] += weight
        if is_lying(world, state, p):
            acc["lying"][p] += weight


def _share(value, denom):
    """A weight as a percentage, kept inside nought and a hundred.

    Adding a few thousand floats and dividing lands on 100.00000000000001
    often enough to matter, and a figure over a hundred is the kind of
    thing somebody reasonably stops trusting the rest of the answer over.
    """
    return min(100.0, max(0.0, 100 * value / denom))


def _rows(acc, state, total, ess=None):
    n = state.n_players
    denom = total if total > 0 else 1.0
    out = []
    for p in range(n):
        row = {
            "player": p,
            "claim": state.claims.get(p),
            "evil_pct": _share(acc["evil"][p], denom),
            "demon_pct": _share(acc["demon"][p], denom),
            "drunk_pct": _share(acc["drunk"][p], denom),
            "lying_pct": _share(acc["lying"][p], denom),
            "roles": sorted(((r, _share(v, denom))
                             for r, v in acc["roles"][p].items()),
                            key=lambda x: -x[1]),
        }
        row["margin"] = _margin(row["evil_pct"], ess)
        out.append(row)
    return out


def _margin(pct, ess):
    """Roughly how far off a sampled percentage could be, in points.

    Two standard errors of a proportion, using the effective sample size
    rather than the number of walks — importance weighting means a
    thousand uneven samples can carry the weight of a hundred even ones,
    and pretending otherwise would overstate the precision.
    """
    if not ess or ess <= 1:
        return 0.0 if ess is None else 50.0
    p = min(max(pct / 100.0, 0.0), 1.0)
    return 100 * 2 * math.sqrt(max(p * (1 - p), 1e-9) / ess)


def estimate(state, allow_good_lies=False, dives=25_000, keep_samples=8,
             rng=None):
    """Probabilities from random walks instead of an exhaustive count.

    Each walk picks uniformly among whatever is open at every seat, so a
    world found down a path with k choices at each step stands for the
    product of those k's. Carrying that weight is what makes the answer
    an estimate of the real distribution rather than of whichever corner
    of the search the walk happened to like.
    """
    n = state.n_players
    now = _report_phase(state)
    rng = rng or random.Random()
    acc = _accumulator(n)
    total = 0.0
    sq = 0.0
    legal_sum = 0.0
    valid_sum = 0.0
    walked = 0
    best = []

    for world, stands_for in sample_worlds(
            n, state.claims, getattr(state, "certainties", None),
            allow_good_lies, forced_roles(state),
            getattr(state, "wakes", None), dives=dives, rng=rng,
            script=state.script, fabled=getattr(state, "fabled", ())):
        walked += 1
        if world is None:
            continue                      # a dead end still counts as a walk
        legal_sum += stands_for

        viable = []
        cost, changes = best_story(world, state, viable=viable)
        if cost is None:
            continue
        valid_sum += stands_for

        weight = stands_for * prior_weight(world, state) * cost
        total += weight
        sq += weight * weight
        for story, share in _story_shares(world, viable, state):
            _tally(acc, world, story, state, weight * share, n, now)

        if len(best) < keep_samples:
            best.append((weight, world))
            best.sort(key=lambda x: x[0])
        elif weight > best[0][0]:
            best[0] = (weight, world)
            best.sort(key=lambda x: x[0])

    ess = (total * total / sq) if sq > 0 else 0.0
    best.sort(key=lambda x: -x[0])
    return {
        "legal": int(round(legal_sum / walked)) if walked else 0,
        "valid": int(round(valid_sum / walked)) if walked else 0,
        "truncated": False,
        "sampled": True,
        "dives": walked,
        "ess": ess,
        "rows": _rows(acc, state, total, ess),
        "samples": [w for _wt, w in best],
    }


# --------------------------------------------------------------------------
# How much of the answer is the evidence, and how much is my guesswork
# --------------------------------------------------------------------------
# Every figure the solver prints mixes two things. Some of it is rules —
# a landed Slayer shot means the target was the Demon or the Recluse, and
# that is checkable against the rulebook. The rest rests on the constants
# above, which were picked by judgement and are printed in the same font.
#
# These are the ranges I would defend as equally plausible. Running the
# solve across them says how much of a figure is evidence and how much is
# me, and which guess is doing the work.
PRIOR_RANGES = {
    "OUTSIDER_HIDING_PENALTY": (0.15, 0.60),
    "TOWNSFOLK_LIE_PENALTY": (0.005, 0.10),
    "CERENOVUS_MADNESS_PENALTY": (0.10, 0.50),
    "BARBER_SWAP_SHARE": (0.50, 0.90),
    "BARBER_DEMON_MINION_SHARE": (0.25, 0.75),
    "BLUFF_COLLISION_PENALTY": (0.10, 0.60),
    "NIGHT_DEATH_EVIL_PENALTY": (0.02, 0.15),
    "POISON_HIT_PENALTY": (0.20, 0.55),
    "POISON_REPEAT_PENALTY": (0.50, 0.90),
    "FABRICATED_INFO_PENALTY": (0.20, 0.70),
    "SUNK_KILL_PENALTY": (0.25, 0.70),
    "DEMON_POISONED_PENALTY": (0.02, 0.15),
    "READ_ODDS_STEP": (1.5, 3.0),
}

_HERE = sys.modules[__name__]


def sensitivity(state, allow_good_lies=False, ranges=None, seed=0,
                dives=3500, **kw):
    """Re-solve across the plausible range of each prior.

    Returns the usual answer plus, for every seat, how far its reading
    moves and which constant moves it. A seat the evidence has pinned down
    barely shifts; a seat resting on one of these guesses swings, and it
    is worth knowing which guess before trusting the number.

    Deliberately done by sampling, with the same seed every time. The
    walks are then identical across all the settings and only the weights
    differ, so what comes back is the effect of the guess and nothing
    else — no sampling noise mixed in. It also keeps the cost the same
    whatever the table size, which re-solving exactly would not.

    One constant is varied at a time. Combinations would be more thorough
    and far slower, and the point is to find the load-bearing guess rather
    than to bound the worst case.
    """
    ranges = ranges or PRIOR_RANGES

    def solve_now():
        return estimate(state, allow_good_lies, dives=dives,
                        rng=random.Random(seed), **kw)

    base = solve_now()
    rows = [{"player": i, "evil_pct": r["evil_pct"],
             "low": r["evil_pct"], "high": r["evil_pct"],
             "driver": None, "swing": 0.0}
            for i, r in enumerate(base["rows"])]

    for name, (low, high) in ranges.items():
        original = getattr(_HERE, name)
        seen = []
        for value in (low, high):
            setattr(_HERE, name, value)
            try:
                seen.append(solve_now()["rows"])
            finally:
                setattr(_HERE, name, original)

        for i, row in enumerate(rows):
            here = [got[i]["evil_pct"] for got in seen]
            row["low"] = min(row["low"], *here)
            row["high"] = max(row["high"], *here)
            moved = max(here) - min(here)
            if moved > row["swing"]:
                row["swing"], row["driver"] = moved, name

    return {"base": base, "rows": rows}


# --------------------------------------------------------------------------
# When nothing fits
# --------------------------------------------------------------------------

def _anything_fits(state, allow_good_lies=False, ceiling=120_000):
    """Is there a single world that survives? Stops at the first one.

    Cheap when the answer is yes and expensive when it is no, which is
    exactly the wrong way round for a diagnosis — hence the ceiling, and
    the second return value saying whether the search finished.
    """
    seen = 0
    for world in iter_worlds(state.n_players, state.claims,
                             getattr(state, "certainties", None),
                             allow_good_lies, forced_roles(state),
                             getattr(state, "wakes", None), state.script,
                             getattr(state, "fabled", ())):
        seen += 1
        if seen > ceiling:
            return False, False           # gave up rather than concluded
        if explanation_cost(world, state) is not None:
            return True, True
    return False, True


def _without(state, drop_info=None, drop_death=None, drop_quiet=None):
    """The same board with one entry taken out.

    Dropping a death drops the execution that went with it, if any —
    otherwise the board would claim the town executed somebody who never
    died, which is a different situation and not the one being tested.
    """
    executions = dict(getattr(state, "executions", None) or {})
    if drop_death is not None:
        executions = {day: seat for day, seat in executions.items()
                      if seat != drop_death}
    return GameState(
        n_players=state.n_players,
        claims=dict(state.claims),
        certainties=dict(getattr(state, "certainties", None) or {}),
        reads=dict(getattr(state, "reads", None) or {}),
        wakes=dict(getattr(state, "wakes", None) or {}),
        deaths={k: v for k, v in (state.deaths or {}).items()
                if k != drop_death},
        resurrections=dict(getattr(state, "resurrections", None) or {}),
        executions=executions,
        quiet_nights={n for n in (getattr(state, "quiet_nights", None) or ())
                      if n != drop_quiet},
        game_over=bool(getattr(state, "game_over", False)),
        infos=[x for i, x in enumerate(state.infos) if i != drop_info],
        names=list(state.names),
        script=state.script,
        fabled=getattr(state, "fabled", ()),
    )


def claims_cannot_fill_the_bag(state, allow_good_lies=False):
    """Is the trouble the claims themselves rather than anything recorded?

    A common way to end up with no worlds at all, and one the entry-by-
    entry search cannot see: twelve seats all claiming Townsfolk when
    every bag for that table needs two Outsiders, and only the Drunk can
    sit behind a Townsfolk claim. Removing a reading will never fix that.

    Returns a sentence, or None when the claims are not the problem.
    """
    from .worlds import _bags
    n = state.n_players
    if n not in SETUP:
        return None

    # How many seats could hold an Outsider *at the same time*, which is
    # not the same as how many could individually. A Townsfolk claim can
    # hide the Drunk — but only one of them can, because there is only one
    # Drunk. Counting them one at a time made this never fire.
    open_seats = 0
    claimed_outsider = 0
    hidden = set()
    for seat in range(n):
        claim = state.claims.get(seat)
        certainty = (getattr(state, "certainties", None) or {}).get(seat, "")
        if claim is None or certainty in ("hiding", "unsure") or allow_good_lies:
            open_seats += 1
        elif claim in state.script.outsiders:
            claimed_outsider += 1
        else:
            for key in state.script.outsiders:
                if believes_another(key) \
                        and claim in believed_tokens(key, state.script):
                    hidden.add(key)       # one seat each, however many claim it
    could = min(claimed_outsider + open_seats + len(hidden),
                len(state.script.outsiders))

    wanted = min(counts["outsider"] for _p, counts in _bags(n, state.script,
                                                            getattr(state, "fabled", ())))
    if could >= wanted:
        return None
    return (f"{n} seats, and the smallest bag for that table still needs "
            f"{wanted} Outsiders — but only {could} of them could be one "
            f"without lying about it. Somebody has to be an Outsider, so "
            f"either a claim is wrong or a seat needs marking as "
            f"\u201cmight be hiding\u201d.")


def diagnose(state, allow_good_lies=False, ceiling=120_000):
    """A board fits nothing. Work out what would have to give.

    Tries removing one entry at a time and reports which removals let a
    world through. One culprit usually means a mis-entered reading or
    somebody lying. *No* single culprit is the interesting case: the board
    is contradictory in a way no one entry accounts for, which is where a
    script that lets the Storyteller break the rules deserves a mention.
    """
    culprits = []
    complete = True

    for i, info in enumerate(state.infos):
        fits, done = _anything_fits(_without(state, drop_info=i),
                                    allow_good_lies, ceiling)
        complete &= done
        if fits:
            culprits.append({
                "kind": "information",
                "label": f"{type(info).__name__} on night {info.night}, "
                         f"seat {info.player + 1}",
            })

    for seat in list((state.deaths or {})):
        fits, done = _anything_fits(_without(state, drop_death=seat),
                                    allow_good_lies, ceiling)
        complete &= done
        if fits:
            culprits.append({"kind": "death",
                             "label": f"seat {seat + 1} dying"})

    for night in list(getattr(state, "quiet_nights", None) or ()):
        fits, done = _anything_fits(_without(state, drop_quiet=night),
                                    allow_good_lies, ceiling)
        complete &= done
        if fits:
            culprits.append({"kind": "quiet night",
                             "label": f"the quiet night {night}"})

    return {"culprits": culprits, "complete": complete}
