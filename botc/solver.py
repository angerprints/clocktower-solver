"""Step 3: build worlds, test them against what people said, weigh, report.

Worlds are no longer counted equally. Two things change a world's weight:

  * A good player who lied.  Evil players bluff constantly - that costs a
    world nothing. A good player claiming a role they do not hold is rare,
    so those worlds are pushed far down instead of being treated as equals.
  * Your own social read.  Each step of a read multiplies the odds that
    seat is evil, so a read shifts the picture without ever forcing it.
"""

import itertools
import math
import random
import sys
from collections import defaultdict
from itertools import product

from .info import each_real_side
from .info import (CourtierChoice, GameState, FortuneTeller,
                   AcrobatChoice, GrandmotherInfo, SlayerShot,
                   VirginNomination, BecameInfo, EvilTwinPair,
                   ChoirboyInfo, PrincessNominated,
                   PreacherChoice, HuntsmanChoice, EngineerChoice,
                   PixieLearned, VillageIdiotInfo, LycanthropeChose,
                   LeviathanAnnounced, ExecutionNomination, InnkeeperChoice,
                   ExorcistChoice, GolemNomination, AlHadikhiaChose,
                   LilMonstaBabysat, SageInfo, SavantInfo, KnightInfo,
                   ClockmakerInfo, FlowergirlInfo, SnakeCharmerChoice,
                   PuzzlemasterGuess, PitHagChoice, MoonchildChoice,
                   babysitter_at,
                   acts_as_cult_leader, cult_sides, knows_it_turned_evil,
                   went_on_after, phase_index,
                   begin_reads, end_reads, listen_for_sides, replay_reads,
                   _LISTENING, falls_as, holding_now, taken_by_a_philosopher,
                   took_it, BoffinGave, BOFFIN_NEVER_GIVES, boffin_gift,
                   boffin_holders, boffin_seat, sober_seat,
                   faux_paw_lycanthrope, side_open)
from .roles import (ABSENT, ARBITRARY, GENUINE, SETUP, TEAM,
                    ability_state, believed_tokens, believes_another,
                    INVERTED, registers_as_role, evil_registrations,
                    is_evil, must_hide, show, wake_fits)
from . import deaths as death_causes
from . import impairment
from .catalogue import CHARACTERS, slot_of
from .waking import LEVIATHAN_CHOOSES_FOR
from .worlds import _at as moment_of
from .worlds import READ_AT, SETUP_SLOT, _row_slot, reading_at
from .worlds import Engineered
from .worlds import BOFFIN_UNSEEN, BoffinGift, boffin_gift_change
from .worlds import (BABYSAT_READS, Babysits, Change, HandedOn, NotSummoned,
                     SUMMON_READS, Summoned, TEA_READS, TeaParty,
                     Timeline, TurnedEvil, World,
                     enumerate_worlds, iter_worlds, lil_monsta_world,
                     dealt_roles, sample_worlds, summoner_world)

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

# A Pixie mad about the Townsfolk whose holder died, and the Storyteller
# judged it not mad enough to gain the ability (table ruling, 11.10.2026:
# both are possible, the refusal costs something). Priced like a hiding
# Outsider: a thing that happens, not the thing that usually does.
PIXIE_DENIED_PENALTY = 0.35

# A Yaggababble kills once for each time it said its phrase, so any
# number of bodies in a night is its doing. The first costs nothing; each
# one more is another time it had to have said it and the Storyteller to
# have acted on it, and without a price it would explain every board
# there is (table ruling, 11.10.2026).
YAGGABABBLE_AGAIN_PENALTY = 0.5
# "It is rare for the Yaggababble to kill during the day." A player who
# drops dead nominating may be its doing rather than a Witch's.
YAGGABABBLE_BY_DAY_PENALTY = 0.25

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
_ACTS_AT = {"a_bounty_hunter_brings_an_evil_townsfolk": 0,   # the setup
            # Ahead of the Snake Charmer (11), which on night two points
            # at night one's babysitter: each night's is chosen at 35,
            # after every reader of the last one (21.10.2026).
            "the_minions_choose_a_babysitter": 5,
            "a_snake_charmer_takes_the_star": 11,
            "a_pit_hag_makes_somebody_else": 16,
            # The Engineer (26.10.2026): after the Sailor, before the
            # Preacher, the Poisoner, the Snake Charmer and every Demon —
            # on the first night after the Summoner, which does nothing
            # then.
            "an_engineer_rebuilds_the_evil": 8,
            # After the Scarlet Woman, before the Lunatic, the Exorcist
            # and every Demon (21.10.2026).
            "the_summoner_summons": 19,
            # And one a Minion became at a tea party (Hatter stage 2,
            # 25.10.2026): at the same turn.
            "a_hatted_summoner_summons": 19,
            # At the very start of the night after the Hatter died by day,
            # before anybody acts (C, 22.10.2026).
            "a_hatters_tea_party": 1,
            # After a death at night, straight after it (C; Hatter stage
            # 3c, 23.10.2026): after the Summoner, before the Barber,
            # whose swap comes later in the night.
            "a_hatters_tea_party_at_night": 30,
            "a_barber_lets_the_demon_swap_two": 40,
            "a_huntsman_finds_the_damsel": 45,
            "a_farmer_hands_it_on": 48,
            # Late on the first night, after every information role: an
            # Empath or Noble on night one still sees the Ogre as good.
            "an_ogre_picks_a_side": 60,
            "demon_handovers": 99,      # a death, so after everything
            # The Boffin gives the Demon an ability at the setup — first,
            # so every rule after it sees it (a Demon's Farmer dying at
            # night). What it gives a new Demon is told with each story
            # (`boffin_new_demon_stories`, 26.10.2026).
            "a_boffin_gives_the_demon": -1}


# Whose turn each rule is (Hatter stage 3b, 23.10.2026): the rule reads
# every night at that character's slot, and every change it makes on a
# night is stamped with the slot (`Change.slot`), so a reader earlier that
# night does not see it and one later does. The Bounty Hunter's Townsfolk
# was evil from the start, or from a Philosopher's turn; the babysitter is
# chosen at Lil' Monsta's turn. The tea party after a death by day is at
# the very start (C), the Demon's handovers at the turn of the Demon that
# fell (`demon_lineages`), the Ogre's turn by day.
_TURN_OF = {"a_snake_charmer_takes_the_star": "SnakeCharmer",
            "a_pit_hag_makes_somebody_else": "PitHag",
            "a_pit_hag_nobody_wrote_down": "PitHag",
            "the_summoner_summons": "Summoner",
            "a_hatted_summoner_summons": "Summoner",
            "a_barber_lets_the_demon_swap_two": "Barber",
            "a_huntsman_finds_the_damsel": "Huntsman",
            "an_engineer_rebuilds_the_evil": "Engineer",
            "a_farmer_hands_it_on": "Farmer",
            "the_minions_choose_a_babysitter": "LilMonsta",
            "a_bounty_hunter_brings_an_evil_townsfolk": "Philosopher"}


def _turn(rule):
    """`reading_at` for a rule's character, every night."""
    key = _TURN_OF.get(rule.__name__)
    if key is None:
        return reading_at(None, 0, 0)
    return reading_at(None, slot_of(key, 1) or 0, slot_of(key, 2) or 0)


def _turn_of(key, night):
    """`reading_at` this character's turn of that night."""
    return reading_at(f"N{night}", slot_of(key, 1) or 0,
                      slot_of(key, night) or 0)


def stamped(changes, key):
    """These changes, each made at this character's turn of its night —
    unless it already says where it happened."""
    out = []
    for c in changes:
        if c.slot is None and c.phase[:1] == "N" and key is not None:
            slot = slot_of(key, int(c.phase[1:]))
            if slot is not None:
                c = c._replace(slot=slot)
        out.append(c)
    return tuple(out)


def _offers(rule, view, state):
    """What a rule offers, asked at its turn and stamped with it."""
    key = _TURN_OF.get(rule.__name__)
    with _turn(rule):
        return [(stamped(extra, key), cost)
                for extra, cost in rule(view, state)]


# Where each cause of a night death reads the board (deaths.CAUSE_TURNS).
# The Demons wake together on the sheet, from the Legion to the Kazali,
# all before the Assassin; the Leviathan's place after dawn is no kill.
_DEMONS_DONE = max(c.other_night for c in CHARACTERS.values()
                   if c.team == "demon"
                   and c.other_night < CHARACTERS["Assassin"].other_night) + 5
death_causes.CAUSE_TURNS.update({
    "the_demon_kills": _DEMONS_DONE,
    "a_zombuul_kills_on_a_quiet_day": _DEMONS_DONE,
    "a_pukka_kills_what_it_poisoned": _DEMONS_DONE,
    "an_al_hadikhia_chooses": _DEMONS_DONE,
    "a_lil_monsta_may_kill": _DEMONS_DONE,
    "a_shabaloth_kills_twice": _DEMONS_DONE,
    "a_po_kills_none_or_three": _DEMONS_DONE,
    "a_yaggababble_kills_for_each_time": _DEMONS_DONE,
    "a_lleech_follows_its_host": _DEMONS_DONE,
    "a_pit_hag_making_a_demon_makes_deaths_arbitrary":
        CHARACTERS["PitHag"].other_night,
    "a_second_demon_makes_deaths_arbitrary":
        CHARACTERS["Summoner"].other_night,
    "a_gossip_may_kill": CHARACTERS["Gossip"].other_night,
    "a_godfather_answers_an_outsider": CHARACTERS["Godfather"].other_night,
    "an_assassin_kills_through_anything": CHARACTERS["Assassin"].other_night,
    "a_gambler_may_lose": CHARACTERS["Gambler"].other_night,
    "a_lycanthrope_may_kill": CHARACTERS["Lycanthrope"].other_night,
})


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
    # One story for each Townsfolk a Bounty Hunter may have brought in
    # evil, beside everything else: room for all of them (11.10.2026).
    dealt = dealt_roles(world)
    hunted = 1
    if _in_bag(state, "BountyHunter") and "BountyHunter" in dealt:
        hunted = max(1, sum(1 for r in dealt if TEAM[r] == "townsfolk"))
        cap *= hunted
    # Room for every babysitter story Lil' Monsta offers (21.10.2026).
    if _in_bag(state, "LilMonsta") and lil_monsta_world(world):
        cap = max(cap, LIL_MONSTA_STORIES)
    # And for every way a tea party went (22.10.2026) — once for each
    # Townsfolk a Bounty Hunter may have turned: the parties multiply its
    # stories, and with room for only one set of them the Townsfolk past
    # the first few were never told (the gate, seed 54).
    if _hatter_on_board(state):
        # Once more for each slot a party at night may stand at (stage 3c):
        # each is a story of every way they chose.
        died = hatter_deaths(world, state)
        slots = max([len(tea_slots(state, int(p[1:]), s))
                     for s, p in died if p[0].upper() == "N"] or [1])
        # And for each party past the first: a Hatter raised and killed
        # again, the parties multiply (gate, seed 1509).
        cap = max(cap, HATTER_STORIES * hunted * slots * max(1, len(died)))
        # And for every way a Summoner chosen at a party before its third
        # night may have summoned (Hatter stage 2, 25.10.2026) — after one
        # party only: two already fill the room they have, and more would
        # take minutes.
        if "Summoner" in state.script.keys and len(died) == 1 \
                and _tea_night(died[0][1]) <= 3:
            cap *= 1 + len(_summonable(state)) * state.n_players
    # And for every way the Engineer's choice went (26.10.2026), and a
    # Summoner it chose summoning beside the Demon.
    if _engineer_on_board(state):
        cap = max(cap, cap * (1 + ENGINEER_STORIES // 8))
        if "Summoner" in state.script.keys:
            cap *= 1 + len(_summonable(state)) * state.n_players
    # And for every ability the Boffin may have given, at the setup and to
    # a new Demon (26.10.2026).
    if _boffin_on_board(state):
        seen = sum(1 for k in state.script.keys if k in BOFFIN_SEEN)
        cap *= 1 + seen
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
    made, swapped, last_swap = set(), False, 0
    for info in state.infos:
        source = getattr(info, "source_role", None)
        if source == "PitHag" and getattr(info, "role", None):
            made.add(info.role)
        elif source == "SnakeCharmer" and getattr(info, "swapped", False):
            swapped = True
            last_swap = max(last_swap, info.night)
    deaths = [(s, p) for s, p in state.death_phases() if p]
    phases = [p for _s, p in deaths]
    at_night = any(p[0].upper() == "N" for p in phases)
    # A Barber counts only once a seat that claimed it has died.
    barber_died = bool(barber_claimants(state) & {s for s, _p in deaths})
    roles = set(world.roles) | made
    # And whatever a Philosopher took: a Barber, a Farmer, an Ogre, a
    # Huntsman (13.10.2026).
    roles |= {taken for taken, _since in (state.philosophies() or {}).values()}
    count = int(swapped) + int(bool(made))
    # The Demon handed on before a Snake Charmer chose it: a Scarlet Woman
    # stepping up in daylight, or a starpass. Run all at once, the charmer
    # (slot 11) is asked before the lineage (last) and looks for the Demon
    # where it was dealt, so the swap with the heir was never offered
    # (Stelle 60, 15.10.2026).
    if swapped:
        dealt = {seat for seat, role in enumerate(world.roles)
                 if TEAM[role] == "demon"}
        if any(seat in dealt
               and phase_index(p) < phase_index(f"N{last_swap}")
               for seat, p in deaths):
            count += 1
    # A Huntsman that chose, and may have found the Damsel (10.10.2026).
    if "Huntsman" in roles and any(isinstance(info, HuntsmanChoice)
                                   for info in state.infos):
        count += 1
    # The Summoner's Demon, once the board reaches it: a Snake Charmer
    # that swaps with it later has to see it (21.10.2026).
    if summoner_world(world) and _in_bag(state, "Summoner") \
            and phase_index(state.final_phase()) >= phase_index("N2"):
        count += 1
    # A tea party after a death by day. Night by night, always: run once
    # over the whole game it is asked first and would not see who held
    # the Demon after a handover the night before (22.10.2026).
    if _hatter_on_board(state):
        claimed = hatter_claimants(state)
        if any(s in claimed for s, p in deaths):
            count += 2
    # The Engineer's choice: night by night, always, for the same reason
    # (26.10.2026).
    if _engineer_on_board(state):
        count += 2
    for key, needs in (("Barber", barber_died), ("Farmer", at_night),
                       ("FangGu", at_night), ("Ogre", True)):
        on = _barber_on_board(state) if key == "Barber" else _on_board(state,
                                                                       key)
        if needs and key in roles and on:
            count += 1
    return count


def _all_nights_at_once(world, state, cap):
    """Every rule once, over the whole game, in night-slot order."""
    stories = [((), 1.0)]
    for rule in TRANSITION_RULES:
        grown = []
        # What the rule offered a story that differs from this one only
        # in who turned evil, if it never asked which side they were on:
        # a Bounty Hunter's seven stories are then asked once, not seven
        # times (`_explain_or_recall` has the reasoning).
        asked_before = {}
        for changes, weight in stories:
            if not _LISTENING[0]:         # nobody turns evil that way here
                view = Timeline(world, changes) if changes else world
                for extra, cost in _offers(rule, view, state):
                    grown.append((changes + tuple(extra), weight * cost))
                    if len(grown) >= cap:
                        break
                if len(grown) >= cap:
                    break
                continue
            flips, _turns, rest = _who_turned(changes)
            offers = None
            before = asked_before.setdefault(rest, [])
            for theirs, reads, kept in before:
                if _differ_only_unasked(flips, theirs, reads):
                    offers = kept
                    break
            if offers is None:
                view = Timeline(world, changes) if changes else world
                begin_reads()
                try:
                    offers = [(tuple(extra), cost)
                              for extra, cost in _offers(rule, view, state)]
                finally:
                    reads = end_reads()
                before.append((flips, reads, offers))
            for extra, cost in offers:
                grown.append((changes + extra, weight * cost))
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
    if name == "a_huntsman_finds_the_damsel":
        return {info.night for info in state.infos
                if isinstance(info, HuntsmanChoice)}
    if name == "an_ogre_picks_a_side":
        return {1}
    if name == "a_bounty_hunter_brings_an_evil_townsfolk":
        return {1} | rows("Philosopher", "role")
    if name == "demon_handovers":
        return {k for k, _kind in deaths}
    if name in ("the_summoner_summons", "a_hatted_summoner_summons"):
        return {1, 2, 3}
    if name == "an_engineer_rebuilds_the_evil":
        return {info.night for info in engineer_rows(state)}
    if name == "a_hatters_tea_party":
        claimed = hatter_claimants(state)
        return {int(p[1:]) + 1 for seat, p in state.death_phases()
                if p and seat in claimed and p[0].upper() != "N"}
    if name == "a_hatters_tea_party_at_night":
        claimed = hatter_claimants(state)
        return {int(p[1:]) for seat, p in state.death_phases()
                if p and seat in claimed and p[0].upper() == "N"}
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
                for extra, cost in _offers(rule, view, state):
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
    """The Demon died, with her standing by.

    In daylight, or at night when it was not the Imp's own starpass —
    that rule already hands her the star first. "If there are 5 or more
    players alive & the Demon dies" is any death: a Lleech that went with
    its host in the night was the first Demon to die there of anything
    but its own kill (11.10.2026), and an Assassin's or a Gossip's kill
    on the Demon had the same gap.
    """
    if phase[0].upper() == "N" and character in STARPASSES:
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
    if not _barber_on_board(state):
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


def _barber_on_board(state):
    """A Barber on the script, or a Philosopher that took one (13.10.2026)."""
    return _in_bag(state, "Barber") or taken_by_a_philosopher(state, "Barber")


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
    # A Philosopher that wrote down taking the Barber: as good as a claim
    # (way 1 of C, 13.10.2026).
    for who, (taken, _since) in (state.philosophies() or {}).items():
        if taken == "Barber":
            out.add(who)
    # A Boffin row naming it (L Weg 1, 27.10.2026): whichever seat is the
    # Demon then, so every seat; only one holding it can die as one.
    if _boffin_names(state, "Barber"):
        out |= set(range(state.n_players))
    return out


def _barber_offers(world, state):
    """Every swap the Demon could make for each Barber death, and none."""
    # Whoever was the Barber when they died — dealt one, or made one by a
    # Pit-Hag. Only the dealt one was looked for, so a Pit-Hag's Barber
    # that was executed swapped nothing (29.09.2026). And only a seat that
    # claimed it: see `barber_claimants`.
    claimed = barber_claimants(state)
    # A Philosopher that took it counts as one, and a real one drunk by
    # that Philosopher when it died swaps nothing (13.10.2026).
    deaths = [(seat, phase) for seat in range(state.n_players)
              if seat in claimed
              for phase in state.died_at(seat)
              if falls_as(world, state, seat, "Barber", phase)]
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
        demons = view.demons_at(night)
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
                ours = ((first in demons and TEAM[b] == "minion")
                        or (second in demons and TEAM[a] == "minion"))
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
    # Asked as the stories were told, at the Barber's turn (Hatter stage
    # 3b): the rule keeps its offers per board, and an answer worked out
    # for the whole night was otherwise handed to the turn, or back.
    for extra, _cost in _offers(a_barber_lets_the_demon_swap_two, view,
                                state):
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
        # At least one of its kind: its own swap. Counted again over a
        # view that has the *later* rules' work in it, the pairs may come
        # out as another kind — the Demon executed and the Scarlet Woman
        # already in its place, offered as "Demon and Minion" before the
        # handover was told and as two of anybody after. Then there were
        # none to share with, and this divided by nought (11.10.2026).
        among = max(1, n_ours if ours else n_other)
        factor *= (BARBER_SWAP_SHARE * part / among
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


@transition_rule
def a_pit_hag_nobody_wrote_down(world, state):
    """A seat said it became something, on a night a Pit-Hag could have
    made it so, and no Pit-Hag row names it: that may have been the
    Pit-Hag, whose choice an evil player does not say. Free, like any
    choice evil keeps to itself (Stelle 58, C, 14.10.2026).

    Only from the second night, with the Pit-Hag alive, and only for a
    character nobody held as the night began — the Pit-Hag cannot make
    one that is in play, so beside a Farmer who died that night it was
    the Farmer.
    """
    if not _in_bag(state, "PitHag"):
        return [((), 1.0)]
    recorded = {(info.night, info.target) for info in state.infos
                if getattr(info, "source_role", None) == "PitHag"
                and getattr(info, "role", None)}
    stories = [((), 1.0)]
    for info in state.infos:
        if not isinstance(info, BecameInfo) or info.night < 2 \
                or info.role not in CHARACTERS \
                or (info.night, info.player) in recorded:
            continue
        phase = f"N{info.night}"
        before = _before(info.night, phase)
        hag = world.find_at("PitHag", phase)
        if hag is None or hag not in state.alive_set(phase):
            continue
        if any(world.role_at(p, before) == info.role
               for p in range(state.n_players)):
            continue
        side = "evil" if world.evil_at(info.player, before) else "good"
        made = Change(phase, info.player, info.role, side)
        stories = (stories + [(changes + (made,), cost)
                              for changes, cost in stories])[:48]
    return stories


@transition_rule
def a_huntsman_finds_the_damsel(world, state):
    """A Damsel the Huntsman chose becomes a Townsfolk not in play.

    Anchored to its row. Two kinds of story when it chose the Damsel:
    she stayed — then the Huntsman was not working, which its row asks
    for (info.HuntsmanChoice) — or she became a Townsfolk, the one she
    said she became if she said so, otherwise any not in play. From the
    night it chose, so what she learns as the new Townsfolk that night
    counts (10.10.2026).
    """
    if not _on_board(state, "Huntsman"):
        return [((), 1.0)]
    for info in state.infos:
        if not isinstance(info, HuntsmanChoice):
            continue
        night = info.night
        phase = f"N{night}"
        if not _has_ability(world, state, info.player, "Huntsman", phase):
            continue
        if info._earlier(state):
            continue
        began = f"B{night - 1}" if night > 1 else "N0"
        target = info.target
        # Or a Philosopher that took her (group 6, P, 14.10.2026).
        if world.role_at(target, began) != "Damsel" \
                and not took_it(world, state, target, "Damsel", began):
            continue
        said = [b.role for b in state.infos
                if isinstance(b, BecameInfo) and b.player == target
                and b.night >= night and b.role in state.script.townsfolk]
        in_play = {world.role_at(p, began) for p in range(state.n_players)}
        options = said[:1] or [k for k in state.script.townsfolk
                               if k not in in_play]
        side = "evil" if world.evil_at(target, began) else "good"
        out = [((), 1.0)]
        for role in options[:16]:
            out.append(((Change(phase, target, role, side),), 1.0))
        return out
    return [((), 1.0)]


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
    if not _on_board(state, "Farmer"):
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
            # And a Philosopher that took it (13.10.2026).
            holders = [p for p in range(state.n_players)
                       if (view.role_at(p, phase) == "Farmer"
                           or took_it(view, state, p, "Farmer", phase))
                       and phase in state.died_at(p)]
            if not holders:
                grown.append((changes, cost))
                # Its jinx with the Leviathan: "each night*, the Leviathan
                # chooses an alive good player: a chosen Farmer uses their
                # ability but does not die" (11.10.2026). Anchored to a
                # seat saying it became the Farmer that night, with a
                # Farmer and a Leviathan alive to have done it.
                if night >= 2 and _in_bag(state, "Leviathan") \
                        and _leviathan_at(view, state, phase) is not None:
                    living = [p for p in state.alive_set(phase)
                              if view.role_at(p, phase) == "Farmer"
                              and not view.evil_at(p, phase)]
                    for info in state.infos:
                        if not isinstance(info, BecameInfo) \
                                or info.role != "Farmer" \
                                or info.night != night or not living:
                            continue
                        heir = info.player
                        if heir in living or heir not in state.alive_set(
                                phase) or not _could_be_good(view, heir,
                                                             phase):
                            continue
                        grown.append((changes + (Change(
                            f"D{night}", heir, "Farmer", None),), cost))
                continue
            seat = holders[0]
            after = f"D{night}"
            # Whoever said they became the Farmer that night first, so the
            # cap below keeps them (Stelle 58, 14.10.2026).
            told = {info.player for info in state.infos
                    if isinstance(info, BecameInfo) and info.role == "Farmer"
                    and info.night == night}
            heirs = sorted((p for p in state.alive_set(phase)
                            if p != seat and _could_be_good(view, p, phase)),
                           key=lambda p: (p not in told, p))
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

            # An heir killed the same night hands it on at once, so the
            # next day two may say they became the Farmer, one of them
            # alive (Stelle 58, D, 14.10.2026).
            def hand_on(made, gone):
                for heir in heirs:
                    if heir in gone:
                        continue
                    more = made + (Change(after, heir, "Farmer", None),)
                    grown.append((more, cost))
                    if phase in state.died_at(heir):
                        hand_on(more, gone | {heir})
            hand_on(changes, {seat})
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
    if not _on_board(state, "Ogre"):
        return [((), 1.0)]
    # The holder, and a Philosopher that took it: it chooses on the night
    # it took it, which is the first (ruling G, 13.10.2026). "Even if
    # drunk or poisoned", so the holder it drunk chooses too.
    ogres = [world.find_at("Ogre", "N1")] + [
        who for who in sorted(state.philosophies() or {})
        if took_it(world, state, who, "Ogre", "N1")]
    stories = [((), 1.0)]
    for ogre in ogres:
        if ogre is None:
            continue
        mine = _an_ogres_side(world, state, ogre)
        stories = [(changes + more, cost * price)
                   for changes, cost in stories for more, price in mine]
    return stories


def _an_ogres_side(world, state, ogre):
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
def a_bounty_hunter_brings_an_evil_townsfolk(world, state):
    """ "[1 Townsfolk is evil]": with a Bounty Hunter dealt, one Townsfolk
    is evil from the setup, and it may be the Bounty Hunter itself (table
    ruling, 11.10.2026, way 2 of C).

    One story for each Townsfolk it could be, at no cost: there always is
    one. That seat keeps its character and its ability, knows what it is,
    and may lie from the start (`worlds.TurnedEvil`).

    Not for a token a Drunk or a Marionette holds, nor a Bounty Hunter a
    Pit-Hag makes later: "if the Bounty Hunter is in play at setup". A
    Philosopher that takes the ability *might* turn one (their jinx), so
    there both stories are told.

    A Townsfolk claiming something else is found only where the search
    offers it at all — a seat marked as not trusted. One such claim
    beside a Bounty Hunter costs what a bluff costs (`prior_weight`); it
    is not taken here to *be* the evil one, since a good player's stray
    claim would then name the wrong seat.
    """
    if not _in_bag(state, "BountyHunter"):
        return [((), 1.0)]
    dealt = dealt_roles(world)
    town = [p for p, role in enumerate(dealt) if TEAM[role] == "townsfolk"]
    if "BountyHunter" in dealt:
        return [((TurnedEvil("N0", p, None, "evil"),), 1.0) for p in town]
    stories = [((), 1.0)]
    for info in state.infos:
        if getattr(info, "source_role", None) != "Philosopher" \
                or getattr(info, "role", None) != "BountyHunter" \
                or world.roles[info.player] != "Philosopher":
            continue
        phase = f"N{info.night}"
        stories += [((TurnedEvil(phase, p, None, "evil"),), 1.0)
                    for p in town if not world.evil_at(p, phase)]
        break
    return stories


class MezephelesTurn(TurnedEvil):
    """The good player a Mezepheles turned, on the night it turned."""
    __slots__ = ()


_SEAT_FIELDS = ("a", "b", "c", "target", "guess", "shown", "second",
                "nominator", "pointed")
_SEAT_SETS = ("joined", "demons", "minions")


def _seats_the_board_looks_at(world, state):
    """Seats whose side something on the board asks about from the second
    night on: named in a row or the source of one, beside an Empath,
    among an Oracle's dead, dead themselves or executed, or beside a Cult
    Leader.

    A Mezepheles may turn anybody, and most of those stories change
    nothing the board can see. Only these do, and they are the only ones
    told (the faux paw's way of keeping the count down, 11.10.2026).
    """
    from .info import _beside_alive, _living_neighbours
    n = state.n_players
    cached = getattr(state, "_looked_at_cache", None)
    if cached is None:
        seats, unclaimed = set(), set()
        for info, src in zip(state.infos, _source_seats(state)):
            if info.night < 2:
                continue
            seats.add(info.player)
            role = getattr(info, "source_role", None)
            if src is not None:
                seats.add(src)
            elif role:
                unclaimed.add(role)
            # The fields that name seats, by name: the same list in
            # scoring.mjs, so both sides tell the same stories whatever
            # else a row happens to carry.
            for name in _SEAT_FIELDS:
                value = getattr(info, name, None)
                if isinstance(value, int) and not isinstance(value, bool):
                    seats.add(value)
            for name in _SEAT_SETS:
                seats.update(x for x in (getattr(info, name, None) or ())
                             if isinstance(x, int)
                             and not isinstance(x, bool))
            for guess in getattr(info, "guesses", None) or ():
                # A Juggler's, as (seat, character) or as the page sends
                # them, {player, role}.
                who = (guess.get("player") if isinstance(guess, dict)
                       else guess[0])
                if isinstance(who, int) and not isinstance(who, bool):
                    seats.add(who)
            kind = type(info).__name__
            if kind == "Empath" and src is not None:
                seats.update(_living_neighbours(state, info.night, src))
            elif kind in ("Empath", "Chef", "SavantInfo"):
                # Wherever the Empath turns out; every pair at the table
                # for a Chef; whatever a Savant's statements were about.
                seats.update(range(n))
            elif kind == "OracleInfo":
                phase = f"N{info.night}"
                seats.update(p for p in range(n)
                             if p not in state.alive_set(phase)
                             or phase in state.died_at(p))
        seats.update(seat for seat, _phase in state.death_phases())
        seats.update((state.executions or {}).values())
        cached = state._looked_at_cache = (
            frozenset(p for p in seats if 0 <= p < n), frozenset(unclaimed))
    seats, unclaimed = cached
    out = set(seats)
    for role in unclaimed:
        holder = world.find(role)
        if holder is not None:
            out.add(holder)
    if _in_bag(state, "CultLeader") and "CultLeader" in world.roles:
        leader = world.find("CultLeader")
        last = int(state.final_phase()[1:])
        for day in range(1, last + 1):
            out.update(_beside_alive(state, leader, f"D{day}"))
        out.add(leader)
    return out


def _acted_before_the_demon_only(world, state, night):
    """Could something later that night have reached a Mezepheles that
    had already done its turning at 18?

    A Pukka poisons at 26, and a Sweetheart dying in the night leaves
    somebody drunk from then on. The plan knows whole nights, so beside
    either it is not asked to have worked the night through — as for the
    Harpy and the Widow.
    """
    phase = f"N{night}"
    if _demon_holding(world, phase, "Pukka") is not None:
        return True
    return any(phase in state.died_at(p)
               and falls_as(world, state, p, "Sweetheart", phase)
               for p in range(state.n_players))


def a_mezepheles_may_have_turned(world, state):
    """ "The 1st good player to say this word becomes evil that night."

    Nothing on the board records it: not the word, not who said it. So
    it is a story — one good player on one night from the second, the
    Mezepheles holding its character when that night began and still
    standing (a Vigormortis's own kill keeps it too). That it was
    working is asked where the readings are judged (`_plain_failures`).
    Free, and once only (table ruling, 11.10.2026).

    The seat keeps its character and its ability. It was good and honest
    until that night, and from then on it reads evil and says what suits
    it (`worlds.TurnedEvil`).

    **Told only where something needs it**, not as a transition rule
    (`best_story`). As a rule it stood beside every other story at once:
    a Barber's fifty pairs times a Bounty Hunter's seven Townsfolk times
    thirty turns ran past any limit on how many stories are kept, and
    the one that happened was cut off (found at the gate, 11.10.2026).
    A turn costs nothing, so a story that already explains everything
    cannot be bettered by one; it is offered to the stories that do not.

    Returns the turns that could be laid over this view, as changes.
    """
    stories = []
    if not _in_bag(state, "Mezepheles"):
        return stories
    last = int(state.final_phase()[1:])
    seats = None
    for night in range(2, last + 1):
        phase = f"N{night}"
        began = _before(night, phase)
        mez = world.find_at("Mezepheles", began)
        if mez is None or not minion_still_acts(world, state, mez, phase):
            continue
        if seats is None:
            seats = sorted(_seats_the_board_looks_at(world, state))
        for seat in seats:
            if seat == mez or world.evil_at(seat, phase):
                continue
            if side_open(world, state, seat, phase) \
                    and not acts_as_cult_leader(world, state, seat, phase):
                continue                  # a Goon's side nobody follows
            # At the Mezepheles's turn of that night (Hatter stage 3b):
            # a reader earlier in the night still sees the seat good.
            stories.append((MezephelesTurn(phase, seat, None, "evil",
                                           slot_of("Mezepheles", night)),))
    return stories


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
        # The one it chose, of two living Demons (Hatter stage 2, B Weg 1).
        demons = world.demons_at(before)
        demon = (info.target if info.target in demons
                 else (demons[0] if demons else None))
        # Lil' Monsta's first babysitter is chosen at 15, before the
        # charmer's turn at 20 (E, Weg 1, 21.10.2026).
        if demon is None and info.night == 1:
            demon = babysitter_at(world, phase)
        if charmer is None or demon is None or charmer == demon:
            continue
        if info.target != demon:
            continue                      # they pointed at somebody else
        # A babysitter is swapped like a Demon: character and side, both
        # ways, and the old babysitter is the poisoned Snake Charmer.
        sitter = babysitter_at(world, before if info.night > 1 else phase)
        sides = (("evil", "good") if sitter != demon
                 else (world.alignment_at(demon, before),
                       world.alignment_at(charmer, before)))
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
        # Unless an Engineer made it another Demon earlier that night, at
        # its turn before the charmer's (26.10.2026): that one is handed
        # over.
        held = world.role_at(demon, before)
        for c in getattr(world, "changes", ()):
            if isinstance(c, Engineered) and c.seat == demon \
                    and c.phase == after:
                held = c.role
        stories = [(changes + (Change(after, charmer, held, sides[0]),
                               Change(after, demon, "SnakeCharmer",
                                      sides[1])),
                    cost)
                   for changes, cost in stories]
    return stories


# --------------------------------------------------------------------------
# Lil' Monsta (21.10.2026, claude/lil-monsta-lesarten.md)
# --------------------------------------------------------------------------
# Nobody is dealt it. Each night the Minions choose a babysitter, who "is
# the Demon" until they choose again: written into the story as
# `Babysits` changes, one a night, which `demon_at` reads.
#
# A, Weg 1: one babysitter a night, the same for every reading of that
# night and the day after — searched only where something asks. Each
# night offers the seats a reading points at as the Demon, and one seat
# nothing asks about, standing for all of them: who it is changes nothing
# that is checked. B, Weg 1: anybody alive may babysit.

def _babysitter_asked(state):
    """{night: (pointed at, ruled out, every seat)} — what the board's
    readings ask about the babysitter of each night.

    "Pointed at" are seats a reading could find to be the Demon: a
    Fortune Teller's yes, a Sage's pair, a Snake Charmer that swapped.
    "Ruled out" are seats a reading says are not, if it worked: a no, a
    Knight's pair, a shot that missed. A seat in neither is one nothing
    asks about. A Clockmaker counts from the Demon's seat, so every seat
    matters on the first night.
    """
    asked = {}

    def at(night):
        return asked.setdefault(night, (set(), set(), [False]))

    for info in state.infos:
        k = info.night
        if isinstance(info, FortuneTeller):
            at(k)[0 if info.yes else 1].update((info.a, info.b))
        elif isinstance(info, SageInfo):
            at(k)[0].update((info.a, info.b))
        elif isinstance(info, ChoirboyInfo):
            at(k)[0].add(info.target)
        elif isinstance(info, KnightInfo):
            at(k)[1].update((info.a, info.b))
        elif isinstance(info, ClockmakerInfo):
            at(k)[2][0] = True
        elif isinstance(info, LilMonstaBabysat):
            at(k)[0].add(info.player)
        elif isinstance(info, SlayerShot):
            at(k)[0 if info.died else 1].add(info.target)
        elif isinstance(info, GolemNomination):
            at(k)[1 if info.died else 0].add(info.target)
        elif isinstance(info, PuzzlemasterGuess):
            at(k)[0].add(info.shown)
        elif isinstance(info, SavantInfo):
            for says in (info.first_says, info.second_says):
                if says and says.get("kind") == "demon_among":
                    at(k)[0].update(int(x) for x in says.get("seats") or ())
        elif isinstance(info, FlowergirlInfo) and k > 1:
            voters = set((state.votes or {}).get(k - 1, ()))
            at(k - 1)[0 if info.voted else 1].update(voters)
        elif isinstance(info, SnakeCharmerChoice):
            # At slot 11: last night's babysitter, or on the first night
            # the one chosen at 15 before it.
            before = k - 1 if k > 1 else 1
            at(before)[0 if info.swapped else 1].add(info.target)
        elif isinstance(info, ExorcistChoice) and k > 1:
            # Naming last night's babysitter stops the kill and says
            # nothing else: it may well have.
            at(k - 1)[0].add(info.target)
    return asked


def _made_minions(state):
    """Seats the board says may have become a Minion: a Snake Charmer that
    swapped, a Pit-Hag's Minion."""
    out = set()
    for info in state.infos:
        if isinstance(info, SnakeCharmerChoice) and info.swapped:
            out.add(info.player)
        elif getattr(info, "source_role", None) == "PitHag" \
                and TEAM.get(getattr(info, "role", None) or "") == "minion":
            out.add(info.target)
    return out


def _babysitters_on(world, state, night, asked):
    """The seats worth trying as this night's babysitter, best first."""
    phase = f"N{night}"
    alive = sorted(state.alive_set(phase))
    if not alive:
        return []
    # Read off the deal, not the story: this rule is asked again on later
    # passes with other rules' changes in view, and what it settled for
    # an earlier night has to come out the same (a Pit-Hag that made the
    # stand-in a Townsfolk moved it, and no story was left).
    dealt = world.roles
    # The Magician's jinx: the Storyteller picks among the Minions.
    magician = world.find("Magician")
    if magician is not None and magician in state.alive_set(phase) \
            and _on_board(state, "Magician"):
        alive = [p for p in alive if TEAM[dealt[p]] == "minion"
                 or p in _made_minions(state)]
    # The Marionette's: it starts beside the first babysitter.
    if night == 1:
        marionette = world.find("Marionette")
        if marionette is not None:
            n = state.n_players
            alive = [p for p in alive
                     if p in ((marionette - 1) % n, (marionette + 1) % n)]
    pointed, ruled_out, every = asked.get(night, (set(), set(), [False]))
    if every[0]:
        return alive
    span = (phase_index(phase), phase_index(f"D{night}"))
    # Dead in the span, or on the gallows that day: what became of them
    # is a question for the story, so they are tried but never stand in
    # for the seats nothing asks about.
    died = {p for p in alive
            if any(span[0] <= phase_index(at) <= span[1]
                   for at in state.died_at(p))
            or state.executed_on(night) == p}
    out = [p for p in alive if p in pointed]
    # A seat that died in the span is tried too: it may have been the
    # babysitter, and what followed is the story's to explain.
    out += [p for p in alive if p in died and p not in out]
    neutral = [p for p in alive
               if p not in pointed and p not in ruled_out and p not in died]
    # First, the one standing for every seat nothing asks about: where it
    # will do, it is the story told (`_best_babysat_story`).
    if neutral:
        minions = [p for p in neutral if TEAM[dealt[p]] == "minion"]
        out.insert(0, (minions or neutral)[0])
    else:
        # Nobody nothing asks about: then anybody, the ruled out last.
        out += [p for p in alive if p not in out and p not in ruled_out]
        out += [p for p in alive if p not in out]
    return out


def _babysitter_falls(world, state, seat, night, last):
    """What becomes of the babysitter chosen on this night, until the
    Minions choose again: (how the story goes on, the changes it needs).

    "go on" — it lives; "over" — it died and the game ended there, good
    winning; "scarlet" — it died with five or more alive and the Scarlet
    Woman babysits for the rest of the game (their jinx); "mastermind" —
    executed, with a Mastermind buying one more day. None if its death
    leaves no story.
    """
    span = (phase_index(f"N{night}"), phase_index(f"D{night}"))
    gone = sorted((at for at in state.died_at(seat)
                   if span[0] <= phase_index(at) <= span[1]),
                  key=phase_index)
    if not gone:
        return [("go on", ())]
    at = gone[0]
    out = []
    if getattr(state, "game_over", False) \
            and phase_index(at) >= phase_index(state.final_phase()):
        out.append(("over", ()))
    # The Scarlet Woman: who holds her by then is settled once the whole
    # story is in (a Snake Charmer may have swapped into her at 11, after
    # this rule), so the fall is marked and the handovers settle it.
    if _on_board(state, "ScarletWoman"):
        out.append(("scarlet", (LilMonstaFell(at, seat),)))
    if _mastermind_day(world, state, at, seat):
        out.append(("mastermind", (mastermind_marker(at, seat),)))
    return out


LIL_MONSTA_STORIES = 256
# Up to this many combinations of babysitters are all told; beyond it a
# night at a time (`_best_babysat_story`).
BABYSITTERS_TOLD_IN_FULL = 64


def babysitter_options(world, state):
    """Each night's babysitters worth trying, in order: [[seats], ...]."""
    last = max(1, int(state.final_phase()[1:]))
    asked = _babysitter_asked(state)
    return [_babysitters_on(world, state, night, asked)
            for night in range(1, last + 1)]


@transition_rule
def the_minions_choose_a_babysitter(world, state):
    """Every night, who babysat Lil' Monsta (A and B, Weg 1)."""
    if not _in_bag(state, "LilMonsta") or not lil_monsta_world(world):
        return [((), 1.0)]
    last = max(1, int(state.final_phase()[1:]))
    # One babysitter a night, as `_best_babysat_story` is trying them; the
    # first of each night's options where nobody says.
    fixed = getattr(state, "_babysitters", None)
    if fixed is None:
        fixed = tuple(options[0] if options else None
                      for options in babysitter_options(world, state))
    stories = []

    def walk(night, so_far):
        if len(stories) >= LIL_MONSTA_STORIES:
            return
        if night > last:
            stories.append((so_far, 1.0))
            return
        seat = fixed[night - 1] if night - 1 < len(fixed) else None
        for seat in ([] if seat is None else [seat]):
            chosen = so_far + (Babysits(f"N{night}", seat),)
            for how, extra in _babysitter_falls(world, state, seat, night,
                                                last):
                if how == "go on":
                    walk(night + 1, chosen)
                else:
                    stories.append((chosen + extra, 1.0))
                if len(stories) >= LIL_MONSTA_STORIES:
                    return

    walk(1, ())
    return stories


# --------------------------------------------------------------------------
# The Summoner (21.10.2026, claude/beschwoerer-lesarten.md)
# --------------------------------------------------------------------------
# No Demon is dealt. On the third night the Summoner makes any player an
# evil Demon of the script — a Pukka already on the second, their jinx —
# and until then there is none. Written into the story as one `Summoned`
# change; who and which are searched (`_best_summoned_story`).
#
# A Weg 1: every player with every Demon. B Weg 1: anybody alive,
# itself and other Minions too; somebody dead only as a Zombuul, which
# has then died once (their jinx). C Weg 1: every Demon of the script
# but Lil' Monsta (nobody holds it), Legion and Riot (the solver reasons
# about neither); a Lord of Typhon beside a Minion, its other neighbour
# made an evil Minion (their jinx). D and E Weg 1: no Demon, because the
# Summoner died before its turn or was drunk or poisoned on it, ends the
# game there — unless a Courtier or a Preacher took its ability, when
# the Storyteller summons instead (their jinxes).

NOT_SUMMONED = ("LilMonsta", "Legion", "Riot")


def _summonable(state):
    """The Demons the Summoner can make: the script's, less three."""
    return [k for k in state.script.keys
            if TEAM.get(k) == "demon" and k not in NOT_SUMMONED]


def _neighbours(n, seat):
    return ((seat - 1) % n, (seat + 1) % n)


def _summoned_seats(world, state, night, demon, puppet=True):
    """Who could have been made this Demon on this night. `puppet`: the
    Marionette's jinx applies — not to a Summoner chosen at a tea party,
    where the Marionette is in play already (Hatter stage 2)."""
    n = state.n_players
    phase = f"N{night}"
    standing = state.alive_set(phase)
    # Back tonight is back after the Summoner's turn: the Professor, the
    # Al-Hadikhia and the Shabaloth all act later.
    back = {p for p, at in (state.resurrections or {}).items()
            if phase in at}
    seats = [p for p in range(n)
             if (p in standing and p not in back) or demon == "Zombuul"]
    # The Marionette's jinx: it enters play after the Demon, as its
    # neighbour — whoever that neighbour is, alive or dead (Patrick,
    # 22.10.2026). The seat that becomes it is the one dealt it here, so
    # the Demon is made beside that seat.
    if puppet and "Marionette" in world.roles:
        m = world.roles.index("Marionette")
        seats = [p for p in seats if p in _neighbours(n, m)]
    return seats


def _marionette_enters(world, state, made):
    """With a Summoner there is no Marionette until the Demon comes: the
    player who becomes it holds the good character it believes in until
    then, really (22.10.2026). The changes that say so, for one way the
    summoning went."""
    if "Marionette" not in world.roles:
        return [()]
    m = world.roles.index("Marionette")
    token = world.believes[m]
    if token is None:
        return [()]
    # Who it was until then (22.10.2026): one that thinks it is a Demon
    # was the Lunatic; one holding a Townsfolk token that character, or
    # the Drunk holding it.
    if TEAM[token] == "demon":
        held = ["Lunatic"]
    else:
        held = [token]
        if TEAM[token] == "townsfolk" and "Drunk" not in world.roles \
                and _in_bag(state, "Drunk"):
            held.append("Drunk")
    after = (() if made is None
             else (Change(made.phase, m, "Marionette", "evil"),))
    return [(Change("N1", m, role, "good", SETUP_SLOT),) + after
            for role in held]


def _typhon_neighbours(world, state, night, seat, demon):
    """What else a summoned Lord of Typhon brings: "they must neighbour a
    Minion & their other neighbour becomes an evil Minion" (their jinx).
    One tuple of changes per way; () alone for every other Demon, and
    nothing at all where a Lord of Typhon cannot sit."""
    if demon != "LordOfTyphon":
        return [()]
    n = state.n_players
    before = _before(night, f"N{night}")
    phase = f"N{night}"
    minion = lambda p: TEAM.get(world.role_at(p, before)) == "minion"
    held = {world.role_at(p, before) for p in range(n)}
    spare = [k for k in state.script.keys
             if TEAM.get(k) == "minion" and k not in held
             and k != "Summoner"]
    out = []
    left, right = _neighbours(n, seat)
    for mate, other in ((left, right), (right, left)):
        if mate == seat or not minion(mate):
            continue
        if minion(other) or other == seat:
            if () not in out:
                out.append(())
            continue
        for role in spare:
            got = (Change(phase, other, role, "evil"),)
            if got not in out:
                out.append(got)
    return out


def summon_options(world, state):
    """Every way the Summoner's ability can have gone, as the changes each
    writes: a `Summoned` (and what a Lord of Typhon brings), a
    `NotSummoned` mark where no Demon came and the game ended, or nothing
    where the board has not reached the summoning yet. [] if none fits."""
    summoner = world.roles.index("Summoner")
    final = state.final_phase()
    reached = lambda night: phase_index(final) >= phase_index(f"N{night}")
    died = sorted(state.died_at(summoner), key=phase_index)
    gone = died[0] if died else None
    over = getattr(state, "game_over", False)
    standing = lambda night: gone is None \
        or phase_index(gone) >= phase_index(f"N{night}")
    # An Engineer that may have taken its character: the Storyteller
    # summons then, alive or dead as the player is (their jinx,
    # 26.10.2026). Offered beside the Summoner's own; the plan keeps the
    # one the story fits.
    jinxed = _engineer_on_board(state) \
        and _engineer_may_take_the_summoner(state)
    out = []
    for demon in _summonable(state):
        for night in ((2, 3) if demon == "Pukka" else (3,)):
            if not reached(night) or not (standing(night) or jinxed):
                continue
            for seat in _summoned_seats(world, state, night, demon):
                for extra in _typhon_neighbours(world, state, night, seat,
                                                demon):
                    out.append((Summoned(f"N{night}", seat, demon,
                                         "evil"),) + extra)
    if standing(3):
        if not reached(3):
            out.insert(0, ())             # not yet: nothing to say
        elif over and phase_index(final) == phase_index("N3"):
            # Drunk or poisoned on its turn: no Demon, good won at dawn.
            out.append((NotSummoned("N3", summoner),))
    elif over and phase_index(final) == phase_index(gone):
        # Dead before its turn: nothing can come, good won there.
        out.append((NotSummoned(gone, summoner),))
    return [way + enters for way in out
            for enters in _marionette_enters(
                world, state, next((c for c in way
                                    if isinstance(c, Summoned)), None))]


@transition_rule
def the_summoner_summons(world, state):
    """The night the Summoner made the Demon, as `_best_summoned_story` is
    trying it; the first way where nobody is asking."""
    if not _in_bag(state, "Summoner") or not summoner_world(world):
        return [((), 1.0)]
    fixed = getattr(state, "_summoned", None)
    if fixed is None:
        options = summon_options(world, state)
        if not options:
            return []
        fixed = options[0]
    return [(tuple(fixed), 1.0)]


def summoned_change(world):
    """The `Summoned` change of this story, or None."""
    return next((c for c in getattr(world, "changes", ())
                 if isinstance(c, Summoned)), None)


# --------------------------------------------------------------------------
# The Hatter (22.10.2026, claude/hutmacher-lesarten.md)
# --------------------------------------------------------------------------
# "If you died today or tonight, the Minion & Demon players may choose
# new Minion & Demon characters to be." Nobody at the table is told who
# chose what, so every way is a story (A Weg 1), told like every other:
# each evil player keeps its character or takes one of its type nobody
# holds, and under the optional rule (B Weg 2) the Demon and one Minion
# may swap types — never leaving more or fewer Demons than before (J Weg
# 1). A death by day: they choose at the very start of the next night,
# before anybody acts (C). A death at night: straight after it, at the
# slot after the turn of whoever may have killed it (stage 3c,
# 23.10.2026, `tea_slots`) — the night read in its order, stage 3b.
#
# Not reckoned yet, and the report says so (`hatter_unreckoned`): Lil'
# Monsta taken in the middle of the game (U). A Minion choosing the
# Summoner while a Demon lives makes two living Demons, reckoned since
# stage 2 (25.10.2026, below).

NOT_HATTED = ("Legion", "Riot", "LilMonsta")

# Room for every way a tea party can go, beside everything else.
HATTER_STORIES = 1024

# Set by the tests: switch the prune in `_best_story_told` off and
# compare.
TEA_PRUNE = True
# And the one over a tea party's Summoner (stage 2, 25.10.2026).
SUMMON_TEA_PRUNE = True

# How many stories with a tea party a solve may tell (V Weg 1,
# 22.10.2026). Each world is told once for every way the evil players can
# have chosen, twenty to fifty times over, and a board with many worlds
# took minutes on the page. Past this, `analyze` samples rather than
# counting, and `estimate` stops walking: the figures carry their margin
# as any sampled answer does. Boards with no tea party never count.
TEA_BUDGET = 30_000
# Counting every world may tell more: a board that would finish counting
# is quicker counted than sampled.
TEA_EXACT_BUDGET = 100_000
# Not fewer walks than this, whatever the budget says.
TEA_MIN_DIVES = 1_000
# Stories with a tea party told since the solve began.
TEA_TOLD = [0]


def _hatter_on_board(state):
    """A Hatter on the script, or a Philosopher that took one."""
    return _in_bag(state, "Hatter") or taken_by_a_philosopher(state, "Hatter")


def hatter_claimants(state):
    """Seats that said they were the Hatter — as their claim, in a row
    saying they became it or had been it, or a Philosopher that wrote down
    taking it.

    **Only their deaths are a tea party** (Patrick, 22.10.2026, T: "auch
    hier wie beim Barbier, jemand muss schon Hutmacher behaupten, damit
    der Solver damit rechnet; wenn keiner Hutmacher behauptet, schadet er
    dem Dorf"). A Hatter hiding behind another claim, whose death let the
    evil players choose, leaves a board the solver may not explain — the
    same price as the Barber's (`barber_claimants`)."""
    out = {seat for seat, role in (state.claims or {}).items()
           if role == "Hatter"}
    for info in state.infos:
        if isinstance(info, BecameInfo) and "Hatter" in (info.role, info.was):
            out.add(info.player)
    for who, (taken, _since) in (state.philosophies() or {}).items():
        if taken == "Hatter":
            out.add(who)
    # A Boffin row naming it (L Weg 1, 27.10.2026), as for the Barber.
    if _boffin_names(state, "Hatter"):
        out |= set(range(state.n_players))
    return out


def hatter_deaths(world, state):
    """Every moment a Hatter that said so died as one, ability in hand as
    far as a Philosopher goes: [(seat, phase)] in time order. A dealt
    Hatter, one a Pit-Hag made, or a Philosopher that took it (I)."""
    out = []
    claimed = hatter_claimants(state)
    for seat in range(state.n_players):
        if seat not in claimed:
            continue
        for phase in state.died_at(seat):
            if falls_as(world, state, seat, "Hatter", phase):
                out.append((seat, phase))
    out.sort(key=lambda got: phase_index(got[1]))
    return out


def _tea_night(phase):
    """The night they choose after a death at this moment: the next one
    after a death by day, the same night after a death at night (C;
    Hatter stage 3c, 23.10.2026)."""
    if phase[0].upper() in "DEX":
        return int(phase[1:]) + 1
    return int(phase[1:])


# Who may have killed a Hatter at night, and where the party is then: the
# slot after their turn (C, "directly after his death"). The table sees
# only that the Hatter died in the night, so every killer on the board is
# a story of its own. The Demons are taken together — they wake one after
# another and the last of them before the Assassin is the Demons' turn
# (`_DEMONS_DONE`) — and since the party comes after their turn, a Demon
# that killed tonight does not kill again (D Weg 1), and a Minion that
# takes the Demon in the swap kills from the next night.
_TEA_KILLERS = ("Lycanthrope", "PitHag", "Assassin", "Godfather",
                "Gossip", "Moonchild")


def tea_slots(state, night, seat=None):
    """The slots a tea party may stand at after the Hatter in this seat
    died that night, one for each killer that could have done it — as far
    as the board says: a Lycanthrope that named somebody else, a Pit-Hag
    that made no Demon, a Godfather with no Outsider dead that day, a
    Moonchild that pointed elsewhere did not. Fewer slots, fewer stories
    to tell; each slot is a story of every way they chose (A Weg 1)."""
    out = [_DEMONS_DONE + 1]
    rows = lambda kind: [i for i in state.infos if isinstance(i, kind)
                         and i.night == night]
    for key in _TEA_KILLERS:
        slot = slot_of(key, night)
        if slot is None or not _on_board(state, key):
            continue
        if seat is not None:
            if key == "Lycanthrope":
                said = rows(LycanthropeChose)
                if said and all(i.target != seat for i in said):
                    continue
            if key == "PitHag":
                said = rows(PitHagChoice)
                if said and not any(TEAM.get(getattr(i, "role", None))
                                    == "demon" for i in said):
                    continue
            if key == "Godfather":
                day = f"D{night - 1}"
                if not any(day in state.died_at(p) or f"E{night - 1}"
                           in state.died_at(p)
                           for p in range(state.n_players)):
                    continue
            if key == "Moonchild":
                if not any(isinstance(i, MoonchildChoice)
                           and i.target == seat for i in state.infos):
                    continue
        out.append(slot + 1)
    return sorted(set(out))


def _hatted(state, team, night, held, demon_alive):
    """The characters of this type somebody may take at that tea party."""
    out = []
    for key in state.script.keys:
        if TEAM.get(key) != team or key in held or key in NOT_HATTED:
            continue
        # "The Leviathan cannot enter play after day 5" (their jinx).
        if key == "Leviathan" and night > 5:
            continue
        # A Summoner taken while the third night is still ahead summons a
        # Demon beside the one in play: two living Demons, reckoned since
        # stage 2 (25.10.2026, `a_hatted_summoner_summons`).
        out.append(key)
    return out


def tea_party_choices(view, state, night, slot=None):
    """Every way the evil players can have chosen at the start of this
    night — or at this slot of it, after a Hatter died that night — as the
    changes each writes. The first is "nobody did"."""
    if slot is not None:
        with reading_at(f"N{night}", slot, slot):
            return _tea_party_choices(view, state, night, slot)
    return _tea_party_choices(view, state, night, None)


def _tea_party_choices(view, state, night, slot):
    n = state.n_players
    phase = f"N{night}"
    # The board as the day before ended: the party is the first thing
    # that happens tonight (`_before` already has it in). After a death
    # at night, the board at the party's slot (read there by the caller).
    before = f"D{night - 1}" if slot is None else phase
    alive = state.alive_set(phase)
    held = {view.role_at(p, before) for p in range(n)}
    side = lambda p: "evil" if view.evil_at(p, before) else "good"
    seats = [p for p in range(n) if p in alive
             and TEAM[view.role_at(p, before)] in ("minion", "demon")]
    demons = [p for p in seats if TEAM[view.role_at(p, before)] == "demon"]
    demon_alive = bool(demons)
    each = {p: _hatted(state, TEAM[view.role_at(p, before)], night, held,
                       demon_alive) for p in seats}
    # A Summoner that has not summoned yet keeps its character: leaving
    # it before the third night means no Demon ever comes, and good has
    # won — not a choice evil makes.
    for p in seats:
        if view.role_at(p, before) == "Summoner" and night <= 3:
            each[p] = []

    out = []

    def grow(at, so_far, taken):
        if at == len(seats):
            out.append(tuple(so_far))
            return
        p = seats[at]
        grow(at + 1, so_far, taken)                   # keeps its own
        for key in each[p]:
            if key in taken:
                continue
            grow(at + 1, so_far + [TeaParty(phase, p, key, side(p), slot)],
                 taken | {key})

    grow(0, [], frozenset())
    # The optional rule: the Demon becomes a Minion and one Minion the
    # Demon, both characters nobody holds (B Weg 2, J Weg 1). The other
    # Minions choose as before.
    spare_demons = [k for k in _hatted(state, "demon", night, held, True)]
    spare_minions = _hatted(state, "minion", night, held, True)
    for demon in demons:
        for minion in seats:
            if minion in demons:
                continue
            for d_key in spare_demons:
                for m_key in spare_minions:
                    swap = [TeaParty(phase, minion, d_key, side(minion),
                                     slot),
                            TeaParty(phase, demon, m_key, side(demon), slot)]
                    rest = [p for p in seats if p not in (demon, minion)]

                    def more(at, so_far, taken):
                        if at == len(rest):
                            out.append(tuple(sorted(
                                so_far, key=lambda c: c.seat)))
                            return
                        p = rest[at]
                        more(at + 1, so_far, taken)
                        for key in each[p]:
                            if key in taken:
                                continue
                            more(at + 1,
                                 so_far + [TeaParty(phase, p, key, side(p),
                                                    slot)],
                                 taken | {key})

                    more(0, swap, frozenset({d_key, m_key}))
    return out


def _tea_stories(world, state, at_night):
    if not _hatter_on_board(state):
        return [((), 1.0)]
    final = phase_index(state.final_phase())
    over = getattr(state, "game_over", False)
    stories = [((), 1.0)]
    for _seat, phase in hatter_deaths(world, state):
        night = _tea_night(phase)
        if (phase[0].upper() == "N") != at_night \
                or final < phase_index(f"N{night}"):
            continue
        # Not if the game ended with that death: nobody chooses after.
        if at_night and over and final == phase_index(phase):
            continue
        slots = tea_slots(state, night, _seat) if at_night else [None]
        grown = []
        for changes, cost in stories:
            view = Timeline(world, changes) if changes else world
            for slot in slots:
                for choice in tea_party_choices(view, state, night, slot):
                    # "Nobody chose" is one story, whichever the slot.
                    if not choice and slot != slots[0]:
                        continue
                    grown.append((changes + choice, cost))
        stories = grown
    return stories


@transition_rule
def a_hatters_tea_party(world, state):
    """The evil players choosing new characters after a Hatter died by
    day: every way, "nobody did" first (A Weg 1)."""
    return _tea_stories(world, state, at_night=False)


@transition_rule
def a_hatters_tea_party_at_night(world, state):
    """And after a Hatter died at night, straight after its death (C;
    Hatter stage 3c, 23.10.2026): at the slot after each killer's turn
    that could have done it (`tea_slots`)."""
    return _tea_stories(world, state, at_night=True)


def tea_parties(world):
    """The `TeaParty` changes of this story, by night: {phase: [...]} —
    the Hatter's, not the Engineer's."""
    out = {}
    for change in getattr(world, "changes", ()):
        if isinstance(change, TeaParty) \
                and not isinstance(change, Engineered):
            out.setdefault(change.phase, []).append(change)
    return out


# --------------------------------------------------------------------------
# Two living Demons (Hatter stage 2, 25.10.2026, claude/hutmacher-stufe-2-
# lesarten.md)
# --------------------------------------------------------------------------
# A Minion that chose the Summoner at a tea party while a Demon lives
# summons on the third night — a Pukka on the second (their jinx) — if it
# still holds it at its turn: any living player, itself and the Demon too,
# into any Demon of the script nobody holds (E Weg 1). Choosing the Demon
# makes it that Demon, and there is still one; anybody else is a second
# living Demon. That night the deaths are arbitrary (their jinx, C Weg 1),
# and from the next each Demon kills by its own ability. Every reading
# that asks for "the Demon" means either (B Weg 1); good wins only once
# both are dead. Taken at a tea party after its turn that night, it does
# nothing (stage 3, C Weg 1).


def hatted_summoners(view):
    """The tea-party changes that made somebody the Summoner."""
    return [c for c in getattr(view, "changes", ())
            if isinstance(c, TeaParty) and c.role == "Summoner"]


def _summons_on(change, night):
    """Could a Summoner chosen at this tea party act on this night?"""
    at = int(change.phase[1:])
    if night != at:
        return night > at
    return change.slot is None \
        or change.slot < slot_of("Summoner", night)


# While a solve estimates (Hatter stage 2, Patrick 26.10.2026, Weg 2): how
# many of a tea party's Summoner's ways each world tells, or None for all.
# A fixed spread across them, the same on every pass over the world and in
# both languages, so the stories of one world agree with each other.
SUMMON_SAMPLE = [None]
SUMMON_SAMPLE_SIZE = 8


def _stable(text):
    """A number from a string, the same in Python and JavaScript."""
    got = 0
    for i, ch in enumerate(text):
        got = (got + (i + 1) * ord(ch)) % 2147483647
    return got


def _sampled_ways(world, change, ways):
    """Every way, or while estimating a fixed spread of k of them."""
    k = SUMMON_SAMPLE[0]
    if k is None or len(ways) <= k:
        return ways
    step = -(-len(ways) // k)
    offset = _stable("|".join(world.roles)
                     + f"|{change.seat}|{change.phase}") % step
    return ways[offset::step]


@transition_rule
def a_hatted_summoner_summons(world, state):
    """Every way a Summoner chosen at a tea party summoned: "nobody" first
    (it died first, was drunk or poisoned, or the board has not reached its
    night), then each night it could, each player, each free Demon."""
    tea = hatted_summoners(world)
    if not tea:
        return [((), 1.0)]
    final = phase_index(state.final_phase())
    n = state.n_players
    out = [((), 1.0)]
    for change in tea:
        seat = change.seat
        ways = []
        for night in (2, 3):
            phase = f"N{night}"
            if final < phase_index(phase) or not _summons_on(change, night):
                continue
            if seat not in state.alive_set(phase) \
                    or world.role_at(seat, phase) != "Summoner":
                continue
            held = {world.role_at(p, phase) for p in range(n)}
            for demon in _summonable(state):
                if demon in held or (night == 2 and demon != "Pukka"):
                    continue
                for target in _summoned_seats(world, state, night, demon,
                                              puppet=False):
                    for extra in _typhon_neighbours(world, state, night,
                                                    target, demon):
                        ways.append(((Summoned(phase, target, demon, "evil"),)
                                     + extra, 1.0))
        out.extend(_sampled_ways(world, change, ways))
    return out


def summoned_beside(view):
    """The `Summoned` change that made a second living Demon in this
    story, or None: one made where a Demon already was, on another
    seat."""
    for change in getattr(view, "changes", ()):
        if not isinstance(change, Summoned):
            continue
        if len(view.demons_at(change.phase)) > 1:
            return change
    return None


# --------------------------------------------------------------------------
# The Engineer (26.10.2026, claude/ingenieur-lesarten.md)
# --------------------------------------------------------------------------
# "Once per game, at night, choose which Minions or which Demon is in
# play." Reckoned only from its row (A Weg 1): without one nothing
# happened, as with the Barber and the Hatter. At its turn — after the
# Sailor, before the Preacher, the Poisoner and every Demon — whoever
# already holds a chosen character keeps it, and the others are handed
# out to the other Minions: every way is a story, each as likely (B Weg
# 1). Fewer chosen than Minions without one: that many change and the
# rest stay; more: every choice of the right number (D Weg 1). A Demon
# chosen makes the Demon it. Drunk or poisoned, nothing changes and the
# choice is spent (C Weg 1).
#
# The changes are tea-party changes (`worlds.Engineered`): the side kept,
# the night its first with the new character, so a later turn acts that
# night and what acts "at the start" acts at once (E Weg 1); a Summoner
# chosen while a Demon lives summons beside it on the third night (F
# Weg 1). A living Summoner it removes leaves its ability to the
# Storyteller, who summons all the same (their jinx, F Weg 1).
#
# Not reckoned, and the report says so (`engineer_unreckoned`, G Weg 1):
# Lil' Monsta, Legion or Riot chosen as the Demon, and a Demon chosen
# while two live.

NOT_ENGINEERED = ("LilMonsta", "Legion", "Riot")

# Room for every way the Engineer's choice went, beside everything else.
ENGINEER_STORIES = 512


def engineer_rows(state):
    """The Engineer rows that could have done anything: the first each
    seat wrote, with a choice an Engineer can make."""
    got = getattr(state, "_engineer_cache", None)
    if got is not None and got[0] is state.infos \
            and got[1] == len(state.infos):
        return got[2]
    out = [i for i in state.infos if isinstance(i, EngineerChoice)
           and not i._earlier(state) and i.chosen(state) is not None]
    state._engineer_cache = (state.infos, len(state.infos), out)
    return out


def _engineer_on_board(state):
    """An Engineer on the script, or taken by a Philosopher, with a row."""
    return _on_board(state, "Engineer") and bool(engineer_rows(state))


def _tea_on_board(state):
    """A Hatter, or an Engineer that chose: somebody may change character
    in the middle of the game the tea-party way."""
    return _hatter_on_board(state) or _engineer_on_board(state)


def _engineer_works(view, state, info):
    """Could this seat have used the Engineer's ability that night: alive
    and holding it, at its turn? Whether it was drunk or poisoned is the
    plan's (`engineer_failed`)."""
    phase = f"N{info.night}"
    if phase_index(state.final_phase()) < phase_index(phase):
        return False
    if info.player not in state.alive_set(phase):
        return False
    with _turn_of("Engineer", info.night):
        return _has_ability(view, state, info.player, "Engineer", phase)


def engineer_options(view, state, info):
    """Every way a working Engineer's choice changed somebody, as the
    changes each writes; [] where it changes nobody, or the solver does not
    reckon it (`engineer_unreckoned`)."""
    chosen = info.chosen(state)
    if chosen is None:
        return []
    night = info.night
    phase = f"N{night}"
    n = state.n_players
    with _turn_of("Engineer", night):
        roles = [view.role_at(p, phase) for p in range(n)]
        side = {p: "evil" if view.evil_at(p, phase) else "good"
                for p in range(n)}
        demons = list(view.demons_at(phase))
    if TEAM[chosen[0]] == "demon":
        key = chosen[0]
        if key in NOT_ENGINEERED or len(demons) != 1:
            return []
        seat = demons[0]
        if roles[seat] == key or TEAM.get(roles[seat]) != "demon":
            return []
        # A Zombuul that has died once, alive but dead to the board, stays
        # what it is (Stelle 86, 26.10.2026: to be asked). Not "not
        # reckoned": every world where an executed player was the Zombuul
        # would leave the whole board without figures.
        if seat not in state.alive_set(phase):
            return []
        return [(Engineered(phase, seat, key, side[seat]),)]
    seats = [p for p in range(n) if TEAM.get(roles[p]) == "minion"]
    held = set(roles)
    spare = [k for k in chosen if k not in held]
    free = [p for p in seats if roles[p] not in chosen]
    k = min(len(spare), len(free))
    if not k:
        return []
    out = []
    for who in itertools.combinations(free, k):
        for what in itertools.permutations(spare, k):
            out.append(tuple(Engineered(phase, p, r, side[p])
                             for p, r in zip(who, what)))
            if len(out) >= ENGINEER_STORIES:
                return out
    return out


@transition_rule
def an_engineer_rebuilds_the_evil(world, state):
    """Every way the Engineer's choice went: "nothing changed" first (it
    was drunk or poisoned, or is no Engineer at all), then each way the
    Storyteller may have handed it out (B and D Weg 1)."""
    if not _engineer_on_board(state):
        return [((), 1.0)]
    stories = [((), 1.0)]
    for info in engineer_rows(state):
        grown = []
        for changes, cost in stories:
            grown.append((changes, cost))
            view = Timeline(world, changes) if changes else world
            if not _engineer_works(view, state, info):
                continue
            for way in engineer_options(view, state, info):
                grown.append((changes + way, cost))
        stories = grown
    return stories


def engineered(view):
    """The Engineer's changes in this story."""
    return [c for c in getattr(view, "changes", ())
            if isinstance(c, Engineered)]


def engineer_failed(world, state):
    """What the Engineer's rows ask of the plan: {night: seats not
    working} for a working Engineer whose choice would have changed
    somebody and did not (C Weg 1).

    A choice that changed somebody asks nothing, as the Huntsman's does:
    the plan settles whole nights, and a poison that reaches the Engineer
    later the same night — a Pukka's, a No Dashii it has just made —
    would otherwise read as one it carried at its turn, and the true
    story was lost (simulator, 26.10.2026)."""
    failures = {}
    made = {c.phase for c in engineered(world)}
    for info in engineer_rows(state):
        if not _engineer_works(world, state, info):
            continue
        night = info.night
        if f"N{night}" not in made and engineer_options(world, state, info):
            failures.setdefault(night, set()).add(info.player)
    return failures


def _summoner_engineered_away(world, state):
    """The night an Engineer's change took a living Summoner's character
    before it summoned, or None. The Storyteller then has its ability
    (their jinx, F Weg 1)."""
    for c in engineered(world):
        night = int(c.phase[1:])
        if night > 3 or c.role == "Summoner":
            continue
        if world.role_at(c.seat, f"B{night - 1}" if night > 1 else "N0") \
                == "Summoner" and c.seat in state.alive_set(c.phase):
            return night
    return None


def _engineer_may_take_the_summoner(state):
    """Could an Engineer's row have taken the Summoner's character before
    it summoned? Then the Storyteller may have summoned where the
    Summoner could not."""
    return _on_board(state, "Engineer") and any(
        info.night <= 3 and TEAM[info.chosen(state)[0]] == "minion"
        and "Summoner" not in info.chosen(state)
        for info in engineer_rows(state))


def engineer_unreckoned(view, state):
    """What the Engineer's row leaves out that the solver does not reckon,
    or None: Lil' Monsta, Legion or Riot chosen as the Demon, or a Demon
    chosen while two live (G Weg 1)."""
    if not _engineer_on_board(state):
        return None
    for info in engineer_rows(state):
        if not _engineer_works(view, state, info):
            continue
        chosen = info.chosen(state)
        if TEAM[chosen[0]] != "demon":
            continue
        if chosen[0] in NOT_ENGINEERED:
            return "engineer"
        with _turn_of("Engineer", info.night):
            if len(view.demons_at(f"N{info.night}")) > 1:
                return "engineer"
    return None


# --------------------------------------------------------------------------
# The Boffin (26.10.2026, claude/laborratte-lesarten.md)
# --------------------------------------------------------------------------
# "The Demon (even if drunk or poisoned) has a not-in-play good
# character's ability. You both know which." Which one is a story
# (`worlds.BoffinGift`), told at each moment the Boffin gives one:
#
# * when the game is set up, to the Demon dealt;
# * when somebody becomes a Demon character — a handover, a Snake
#   Charmer's swap, a Pit-Hag's Demon, a tea party, the Engineer, the
#   Summoner — a new one, which may differ (C Weg 1);
# * when somebody becomes the Boffin while a Demon lives (I Weg 1);
# * when a second living Demon comes, the Storyteller decides: the first
#   keeps it, or the second gets one and the first's ends (D Weg 2).
#
# What it may give: a good character of the script nobody holds then,
# none of the four their jinxes forbid, a Village Idiot only while a
# token is spare (B Weg 1). Each that changes what the town sees is a
# story of its own; the others are one story together, "nothing anybody
# sees" (A Weg 3). A world weighs what its best story costs, and the
# shares go by cost: so that story costs 1 and each of the others one
# over how many it holds — the shares then go as a random pick would.
# A Boffin row (`BoffinGave`) names it, and only that one is told.
#
# Whether the ability works is the Boffin's: alive, holding its
# character, sober (`info.boffin_gift`, `info.sober_seat`).

# The abilities reckoned so far, each a story of its own (stage 1,
# 26.10.2026). The rest change nothing the town sees, or are reckoned in
# stage 2 and until then go with them.
BOFFIN_SEEN = frozenset({
    # Who dies, and who does not.
    "Fool", "Sailor", "TeaLady", "Soldier", "Monk", "Innkeeper", "Mayor",
    "Pacifist", "Princess", "Tinker", "Gambler", "Acrobat", "Grandmother",
    "Moonchild", "Gossip", "Lycanthrope", "Golem", "Banshee", "Farmer",
    # Executions, votes and the end of the game.
    "Virgin", "Saint", "Klutz", "Zealot",
    # Who is drunk or poisoned.
    "Sweetheart", "Courtier", "Minstrel", "Preacher", "Goon",
    "Puzzlemaster",
    # Stage 2 (N and H, Patrick 26./27.10.2026): what a Demon would use
    # for evil, and what he asked for.
    "Engineer", "Nightwatchman", "Pixie", "Professor", "Huntsman",
})

# Told only where a Boffin row names them (L Weg 1, Patrick 27.10.2026):
# like the Barber and the Hatter themselves, reckoned only once somebody
# says so.
BOFFIN_ROW_ONLY = frozenset({"Barber", "Hatter"})


def _boffin_names(state, role):
    """Does a Boffin row name this character?"""
    return _boffin_on_board(state) and any(
        info.given(state) == role for info in boffin_rows(state))


def _boffin_on_board(state):
    """A Boffin on the script."""
    return "Boffin" in state.script.keys


def boffin_rows(state):
    """The Boffin rows that name something it could give."""
    got = getattr(state, "_boffin_rows_cache", None)
    if got is not None and got[0] is state.infos \
            and got[1] == len(state.infos):
        return got[2]
    out = [i for i in state.infos if isinstance(i, BoffinGave)
           and i.given(state) is not None]
    state._boffin_rows_cache = (state.infos, len(state.infos), out)
    return out


def boffin_may_give(view, state, phase):
    """Every good character the Boffin could give at that moment: on the
    script, nobody holding it (alive or dead), none their jinxes forbid,
    a Village Idiot only while one of its tokens is spare (B Weg 1)."""
    n = state.n_players
    held = [view.role_at(p, phase) for p in range(n)]
    out = []
    for key in state.script.keys:
        if TEAM.get(key) not in ("townsfolk", "outsider"):
            continue
        if key in BOFFIN_NEVER_GIVES:
            continue
        count = held.count(key)
        if count and count >= CHARACTERS[key].copies:
            continue
        out.append(key)
    return out


def _boffin_named(state, night, setup):
    """What a Boffin row says it gave, for a moment of that night, or
    None. A row of the first night names what the Demon dealt was given —
    the Boffin wakes at 12, before anything that night could make another
    Demon; a row of a later night names what the Demon made that night was
    given (26.10.2026, seed 683: a Snake Charmer's swap on the first night
    is not what the first night's row is about)."""
    named = None
    for info in boffin_rows(state):
        if info.night == night and (night > 1 or setup):
            named = info.given(state)
    return named


def boffin_offers(view, state, phase, seat, slot, setup=False):
    """Every ability the Boffin may have given this seat at that moment,
    as ((mark,), cost) — "nothing the town sees" first."""
    may = boffin_may_give(view, state, phase)
    named = _boffin_named(state, int(phase[1:]), setup)
    if named is not None:
        if named not in may:
            return []
        # Named, it is that ability, whatever it is: its readings are
        # weighed as its own (G Weg 1, stage 2, 27.10.2026).
        return [((boffin_gift_change(phase, seat, named, slot),), 1.0)]
    seen = _sampled_gifts(view, phase, seat,
                          [k for k in may if k in BOFFIN_SEEN])
    # A reading of a good character on this seat makes that character a
    # story of its own here (K Weg 2, 27.10.2026): never thinned.
    said = [k for k in _readings_of(state, seat)
            if k in may and k not in BOFFIN_SEEN]
    unseen = len([k for k in may if k not in BOFFIN_SEEN])
    out = []
    if unseen:
        out.append(((boffin_gift_change(phase, seat, BOFFIN_UNSEEN, slot),),
                    1.0))
    each = 1.0 / unseen if unseen else 1.0
    out.extend(((boffin_gift_change(phase, seat, k, slot),), each)
               for k in seen + said)
    return out


def _readings_of(state, seat):
    """The good characters whose readings this seat wrote down, in the
    order of the script (K Weg 2)."""
    got = getattr(state, "_readings_cache", None)
    if got is None or got[0] is not state.infos \
            or got[1] != len(state.infos):
        by_seat = {}
        for info in state.infos:
            role = getattr(info, "source_role", None)
            if role and TEAM.get(role) in ("townsfolk", "outsider") \
                    and isinstance(info.player, int) \
                    and not isinstance(info, BoffinGave):
                by_seat.setdefault(info.player, set()).add(role)
        got = (state.infos, len(state.infos), by_seat)
        state._readings_cache = got
    mine = got[2].get(seat, ())
    return [k for k in state.script.keys if k in mine]


# While a solve estimates (Stelle 91, Patrick 27.10.2026): how many of the
# abilities the town can see each moment tells. A script holds four to six
# of them, so eight (the Summoner's) saved nothing; with one, seed 164 of
# the gate took 237 s on the page instead of 575.
BOFFIN_SAMPLE_SIZE = 1


def _sampled_gifts(view, phase, seat, seen):
    """Every ability the town can see, or while a solve estimates a fixed
    spread of `BOFFIN_SAMPLE_SIZE` of them, as for the Summoner (Stelle 91,
    Weg 2). "Nothing the town sees" and a gift a row names are always
    told; only the others are thinned, each keeping its own cost."""
    k = None if SUMMON_SAMPLE[0] is None else BOFFIN_SAMPLE_SIZE
    if k is None or len(seen) <= k:
        return seen
    base = view.world if isinstance(view, Timeline) else view
    step = -(-len(seen) // k)
    offset = _stable("|".join(base.roles) + f"|{seat}|{phase}|boffin") % step
    return seen[offset::step]


def _boffin_moments(view, state, setup):
    """When the Boffin gives something in this story, and to whom:
    [(phase, slot, seat, beside)] in time order — `beside` the Demon that
    already had one, where a second living Demon came (D Weg 2). At the
    setup only, or every moment after it."""
    base = view.world if isinstance(view, Timeline) else view
    out = []
    if setup:
        if "Boffin" in base.roles:
            start = base.demon_at("N1")
            if start is not None:
                out.append(("N1", SETUP_SLOT, start, None))
        return out
    changes = sorted((c for c in getattr(view, "changes", ())
                      if not isinstance(c, BoffinGift)), key=moment_of)
    for i, c in enumerate(changes):
        if c.role is None:
            continue
        # The board just before this change, and just after it.
        prior = Timeline(base, tuple(changes[:i])) if i else base
        after = Timeline(base, tuple(changes[:i + 1]))
        was = prior.role_at(c.seat, c.phase)
        if TEAM.get(c.role) == "demon":
            if was == c.role:
                continue                  # the same Demon as before
            others = [d for d in after.demons_at(c.phase)
                      if d != c.seat and d in state.alive_set(c.phase)]
            beside = others[0] if isinstance(c, Summoned) and others \
                else None
            out.append((c.phase, c.slot, c.seat, beside))
        elif c.role == "Boffin" and was != "Boffin" \
                and boffin_seat(prior, state, c.phase) is None:
            for d in after.demons_at(c.phase):
                out.append((c.phase, c.slot, d, None))
    return out


@transition_rule
def a_boffin_gives_the_demon(world, state):
    """Every ability the Boffin may have given the Demon dealt."""
    return _boffin_stories(world, state, True)


def boffin_new_demon_stories(world, state):
    """Every ability the Boffin may have given each new Demon (C Weg 1),
    a second living one (D Weg 2), or the Demon when somebody became the
    Boffin (I Weg 1): [(changes, cost)]. Not a transition rule: told for
    each story as it is explained (`_best_story_told`), so the stories do
    not multiply by it."""
    return _boffin_stories(world, state, False)


def _boffin_stories(world, state, setup):
    """Every ability the Boffin may have given, at each moment it gives one,
    as [(changes, cost)].

    At the setup that is every one. For new Demons it is the story where
    each got "nothing the town sees" (or what it is first offered), and
    each story where exactly one of them got something else (26.10.2026):
    beside a tea party, an Engineer and a Summoner there were four such
    moments in one story and four thousand ways (gate, seed 444). Two new
    Demons in one game both using what they were given is left out."""
    if not _boffin_on_board(state):
        return [((), 1.0)]
    moments = []
    for phase, slot, seat, beside in _boffin_moments(world, state, setup):
        if boffin_seat(world, state, phase) is None \
                and phase != "N1":
            continue                      # nobody to give it
        offers = boffin_offers(world, state, phase, seat, slot, setup)
        if beside is not None:
            # The Storyteller decides (D Weg 2): the first keeps it, or the
            # second gets one and the first's ends.
            end = boffin_gift_change(phase, beside, "", slot)
            offers = [((), 1.0)] + [(way + (end,), c) for way, c in offers]
        if not offers:
            return []                     # a row names what it cannot be
        moments.append(offers)
    if not moments:
        return [((), 1.0)]
    if setup:
        stories = [((), 1.0)]
        for offers in moments:
            stories = [(changes + way, cost * c)
                       for changes, cost in stories for way, c in offers]
        return stories
    first = tuple(c for offers in moments for c in offers[0][0])
    base = 1.0
    for offers in moments:
        base *= offers[0][1]
    stories = [(first, base)]
    for i, offers in enumerate(moments):
        for way, c in offers[1:]:
            changes = tuple(ch for j, other in enumerate(moments)
                            for ch in (way if j == i else other[0][0]))
            stories.append((changes, base / offers[0][1] * c))
    return stories


def boffin_unreckoned(view, state):
    """What the Boffin leaves out that the solver does not reckon, or
    None: Lil' Monsta, whose babysitter changes every night."""
    if not _boffin_on_board(state) or "Boffin" not in view.roles:
        return None
    if _in_bag(state, "LilMonsta") and lil_monsta_world(
            view.world if isinstance(view, Timeline) else view):
        return "boffin"
    return None


def hatter_unreckoned(view, state):
    """What this story leaves out that the solver does not reckon yet, or
    None: Lil' Monsta taken in the middle of the game ("lil monsta", U Weg
    2). A Hatter dead at night ("hatter at night") is reckoned since stage
    3c (23.10.2026), two living Demons through the Summoner ("two demons")
    since stage 2 (25.10.2026). And what the Engineer leaves out
    (`engineer_unreckoned`, 26.10.2026)."""
    if not _hatter_on_board(state):
        return engineer_unreckoned(view, state) \
            or boffin_unreckoned(view, state)
    final = phase_index(state.final_phase())
    for _seat, phase in hatter_deaths(view, state):
        night = _tea_night(phase)
        at_night = phase[0].upper() == "N"
        # A Hatter dead at night is reckoned since stage 3c (23.10.2026).
        # Not if the game ended with that death.
        if at_night and getattr(state, "game_over", False) \
                and final == phase_index(phase):
            continue
        if final < phase_index(f"N{night}"):
            continue
        # The board as the party's night began (after a death at night,
        # the night it died in).
        before = f"D{night - 1}" if not at_night else (
            f"B{night - 1}" if night > 1 else "N1")
        alive = state.alive_set(f"N{night}")
        n = state.n_players
        # The Demon may have chosen Lil' Monsta (their jinx), which then
        # comes into play in the middle of the game: not reckoned yet (U
        # Weg 2, Patrick 22.10.2026).
        if "LilMonsta" in state.script.keys and any(
                p in alive and TEAM[view.role_at(p, before)] == "demon"
                for p in range(n)):
            return "lil monsta"
    return engineer_unreckoned(view, state) or boffin_unreckoned(view, state)


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
    # Hanged itself, babysitting Lil' Monsta: dead, it has no ability to
    # buy the day with (21.10.2026).
    if seat == holder:
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
    return change.role is None and change.side is None \
        and not isinstance(change, (Babysits, LilMonstaFell, NotSummoned,
                                    HandedOn, BoffinGift))


class LilMonstaFell(Change):
    """Lil' Monsta's babysitter died here and the game went on: the
    Scarlet Woman's jinx, settled by `_the_scarlet_woman_babysits`."""
    __slots__ = ()


def _the_scarlet_woman_babysits(world, state):
    """"If Lil' Monsta dies with 5 or more players alive, the Scarlet
    Woman babysits Lil' Monsta for the rest of the game" — from the
    moment after: a reading of the moment it died, the Slayer's own shot,
    was about the babysitter that fell. She has to see it through."""
    fell = [c for c in getattr(world, "changes", ())
            if isinstance(c, LilMonstaFell)]
    if not fell:
        return [()]
    at, seat = fell[0].phase, fell[0].seat
    scarlet = world.find_at("ScarletWoman", at)
    if scarlet is None or scarlet == seat \
            or not scarlet_woman_takes_over(world, state, at):
        return []
    index = phase_index(at) + 1
    after = f"{'D' if index % 2 else 'N'}{index // 2 + 1}"
    over = getattr(state, "game_over", False)
    final = phase_index(state.final_phase())
    if any(phase_index(gone) >= index and not (over
                                               and phase_index(gone) >= final)
           for gone in state.died_at(scarlet)):
        return []
    return [(Babysits(after, scarlet, slot=SETUP_SLOT),)]


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
    # Lil' Monsta's babysitters are the Minions' choice, and what a
    # babysitter's death leads to is settled where they are chosen
    # (the_minions_choose_a_babysitter) — but for the Scarlet Woman's
    # jinx, settled here with the whole story in view.
    if _in_bag(state, "LilMonsta") and lil_monsta_world(world):
        return _the_scarlet_woman_babysits(world, state)
    start = world.demon_at("N1")
    # The Summoner's Demon starts its line where it was made; a death
    # before that was no Demon's (21.10.2026).
    since = None
    if start is None:
        summoned = summoned_change(world)
        if summoned is None:
            return [()]
        start, since = summoned.seat, phase_index(summoned.phase)

    # A second living Demon a Summoner made (Hatter stage 2, 25.10.2026):
    # each line is walked on its own, the second on top of the first, and
    # a line may end with its Demon dead while the other goes on — which
    # the story has to bear out once both are in (`_a_demon_left`).
    beside = summoned_beside(world)
    if beside is None:
        return [line for line, _ends in _demon_line(
            world, state, world, start, since, 0, None, cap)]
    out = []
    for first, ends in _demon_line(world, state, world, start, since, 0,
                                   beside, cap):
        view = Timeline(world, first) if first else world
        for second, more in _demon_line(world, state, view, beside.seat,
                                        phase_index(beside.phase), 1,
                                        beside, cap):
            story = first + second
            if _a_demon_left(Timeline(world, story) if story else world,
                             state, ends + more):
                out.append(story)
            if len(out) >= cap:
                return out
    return out


def _scarlet_woman_stays(view, state, phase, fallen):
    """Would a Scarlet Woman stepping up for this Demon make two living
    Demons, with a Fang Gu or an Al-Hadikhia in play? Then she stays the
    Scarlet Woman (their jinxes)."""
    here = phase_index(phase)
    if not any(view.role_at(p, phase) in ("FangGu", "AlHadikhia")
               for p in range(state.n_players)):
        return False
    return any(d != fallen and not any(phase_index(p) <= here
                                       for p in state.died_at(d))
               for d in view.demons_at(phase))


def _a_demon_left(view, state, ends):
    """Every Demon that fell with nobody to take over, while the game went
    on, left another standing (Hatter stage 2, 25.10.2026)."""
    for holder, phase in ends:
        here = phase_index(phase)
        if not any(d != holder and not any(phase_index(p) <= here
                                           for p in state.died_at(d))
                   for d in view.demons_at(phase)):
            return False
    return True


def _demon_line(world, state, base, start, since, line, beside, cap):
    """One Demon's line: every way it changed hands, as (changes, ends) —
    `ends` the deaths it ended with while another Demon stood. `line` is
    its place among the Demons (`Timeline.demons_at`); `beside` the
    summoning that made a second one, or None."""
    found = []

    def walk(view, holder, so_far, after=-1, held=frozenset(), ends=()):
        if len(found) >= cap:
            return
        first = holder == start and since is not None and not so_far
        # A seat that stopped being the Demon before it died hands
        # nothing on. A Snake Charmer swap moves the Demon to the
        # charmer's seat and leaves a *good* Snake Charmer behind — and
        # when the new Demon later kills that seat, this walk was still
        # tracking it as the holder, looked for an heir, found none, and
        # declared the whole world impossible.
        phases = state.died_at(holder)
        # Made a Zombuul while dead, it "has already died once" (their
        # jinx): the next death is the real one.
        spent = False
        if first:
            spent = any(phase_index(p) < since for p in phases)
            phases = tuple(p for p in phases if phase_index(p) >= since)
        # A Zombuul's first death is not one. It registers dead and goes
        # on killing, so the star has not moved and nobody inherits; only
        # the second death is real. Reading the first as final made every
        # board with an executed Zombuul impossible — nobody could take
        # over, so no story fitted. Found with the Mastermind, whose
        # third wiki example is exactly this Zombuul executed twice.
        if phases and not spent \
                and view.role_at(holder, phases[0]) == "Zombuul":
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
            # Where a tea party took the Demon's character, the star went
            # to the Minion that swapped then — not to whoever holds it at
            # the end, past a Fang Gu that jumped in between (seed 1511).
            gave = next((c.phase for c in getattr(view, "changes", ())
                         if isinstance(c, TeaParty) and c.seat == holder
                         and TEAM[c.role] != "demon"
                         and phase_index(c.phase) > after
                         and phase_index(c.phase) <= phase_index(check)),
                        None)
            now = view.demons_at(gave if gave is not None else check)
            successor = now[line] if len(now) > line else None
            if successor is not None and successor != holder \
                    and successor not in held:
                walk(view, successor, so_far, after, held | {holder}, ends)
                return
            found.append((so_far, ends))
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
            found.append((so_far, ends))
            return
        if phase is None:
            found.append((so_far, ends))  # they held it to the end
            return
        character = view.role_at(holder, phase)
        moves = []
        for rule in HEIR_RULES:
            # At the turn of the Demon that fell (Hatter stage 3b): a
            # starpass at the Imp's, a jump at the Fang Gu's. A Demon that
            # fell to somebody else's kill hands on at its own turn too —
            # the night says only that it died.
            moves.extend(stamped(rule(view, state, phase, character),
                                 character))
        # "If there would be two living Demons, one of which was the
        # Scarlet Woman, the Scarlet Woman remains the Scarlet Woman" —
        # with a Fang Gu or an Al-Hadikhia in play (their jinxes; Hatter
        # stage 2, Patrick 26.10.2026).
        if beside is not None and _scarlet_woman_stays(view, state, phase,
                                                       holder):
            moves = [m for m in moves if m.seat is None
                     or view.role_at(m.seat, phase) != "ScarletWoman"]

        # A Mastermind buys one more day after the Demon is executed.
        # Nobody inherits — there simply is no Demon after this — so the
        # lineage ends here rather than continuing, and the nights that
        # follow have no Demon kill to explain. Marked, so the plan can be
        # told what that day needs.
        if _mastermind_day(view, state, phase, holder):
            found.append((so_far + (mastermind_marker(phase, holder),),
                          ends))

        # No offers at all, and no Mastermind, means good won right there
        # and there is no story to tell about what came after.
        #
        # Which is a story when the board says the game is over and this
        # was its last moment: the pointing after a Boomdandy took the
        # Demon (10.10.2026). Until then a dead Demon with nobody to take
        # over had no story at all, because the town never won here.
        #
        # Even beside a Scarlet Woman on offer: everybody who died that
        # day still stands on the board, and with them she would have had
        # her five — when the explosion had already taken them.
        if getattr(state, "game_over", False) \
                and phase_index(phase) >= phase_index(state.final_phase()):
            found.append((so_far, ends))
        # Beside a second Demon made by then, the line may simply end: the
        # other goes on, and good has not won (B Weg 1). Not where the
        # Scarlet Woman steps up — she does whenever she can (D Weg 1).
        elif beside is not None \
                and phase_index(beside.phase) <= phase_index(phase) \
                and not any(view.role_at(m.seat, phase) == "ScarletWoman"
                            for m in moves if m.seat is not None):
            found.append((so_far, ends + ((holder, phase),)))
        for move in moves:
            if move.seat is None:
                continue
            # Which Demon this was, where two live (`Timeline.demons_at`).
            mark = (() if beside is None
                    else (HandedOn(move.phase, holder, slot=move.slot),))
            grown = so_far + mark + (move,)
            walk(Timeline(base, grown), move.seat, grown,
                 phase_index(phase), held | {holder}, ends)

    walk(base, start, (), -1 if since is None else since)
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
# The eighth five (11.10.2026): one that never kills, and one that kills
# as often as it said its phrase.
kills_its_own_way("Leviathan", "Yaggababble")
# The Al-Hadikhia (21.10.2026): only the three it chose, by their choices.
kills_its_own_way("AlHadikhia")


@death_causes.cause_rule
def the_demon_kills(world, state, night):
    """The one cause Trouble Brewing has.

    It fires every night from the second, whether or not anybody wants it
    to, and it can aim anywhere — including at a corpse, which is how a
    Demon bluffing protection buys itself a quiet night.
    """
    if night < 2:
        return []                         # nobody dies on the first night
    # Each living Demon kills once, by its own ability (Hatter stage 2,
    # C Weg 1): one cause each, named apart so each has its own one.
    out = []
    for i, demon in enumerate(world.demons_at(f"N{night}")):
        for cause in _the_demon_kills(world, state, night, demon):
            cause = cause._replace(demon=demon)
            out.append(cause if i == 0
                       else cause._replace(name=f"Demon {i + 1}"))
    return out


def _demon_holding(world, phase, role, at=None):
    """The Demon at this moment that holds this character (read at `at`,
    if given), or None — either of two (Hatter stage 2, B Weg 1)."""
    for demon in world.demons_at(phase):
        if world.role_at(demon, at or phase) == role:
            return demon
    return None


def _the_demon_kills(world, state, night, demon):
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
    # A babysitter holds no Demon character: Lil' Monsta kills its own
    # way (a_lil_monsta_may_kill).
    if babysitter_at(world, f"N{night}") == demon:
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
           and falls_as(world, state, p, "Sweetheart", f"N{night}")
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
    if not _on_board(state, "Soldier"):
        return []
    if kind != death_causes.DEMON:
        return []
    if not _has_ability(world, state, seat, "Soldier", f"N{night}"):
        return []
    # Dead already, it has no ability: "the dead cannot die again" is the
    # whole account, at its price (13.10.2026, the gate of group 1 — a
    # dead Philosopher-Soldier was a free way to read every quiet night
    # after, and the accounts ran past their cap).
    if seat not in state.alive_set(f"N{night}"):
        return []
    # Only while working — a poisoned Soldier dies like anybody else.
    return [death_causes.Shield("Soldier", needs=sober_seat(
        world, state, seat, "Soldier", f"N{night}"))]


@death_causes.immunity_rule
def the_monk_guards_against_the_demon(world, state, night, seat, kind):
    if not _on_board(state, "Monk"):
        return []
    if kind != death_causes.DEMON:
        return []
    # Every night but the first, like the Innkeeper and the Exorcist.
    if night < 2:
        return []
    phase = f"N{night}"
    return [death_causes.Shield("Monk", needs=sober_seat(
                world, state, monk, "Monk", phase), chosen=True)
            for monk in _holders(world, state, "Monk", phase)
            if monk != seat and monk in state.alive_set(phase)]


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
def a_vizier_cannot_die_by_day(world, state, day, seat):
    """ "You cannot die during the day." Working, it walks away from the
    gallows. Drunk by a Courtier it does too — "if the Vizier loses their
    ability, they learn this and cannot die during the day" (their jinx)
    — so a Courtier that named the Vizier lately is a second way, and
    with two the plan demands neither (10.10.2026)."""
    if not _in_bag(state, "Vizier"):
        return []
    phase = f"D{day}"
    if world.role_at(seat, phase) != "Vizier":
        return []
    # Babysitting Lil' Monsta, it dies when executed (their jinx).
    if babysitter_at(world, phase) == seat:
        return []
    out = [seat]
    for info in state.infos:
        if getattr(info, "source_role", None) == "Courtier" \
                and getattr(info, "role", None) == "Vizier" \
                and info.night <= day < info.night + 3:
            out.append(info.player)
        # The same jinx with the Preacher (10.10.2026): a Vizier it chose
        # has no ability, learns it, and cannot die by day all the same.
        if isinstance(info, PreacherChoice) and info.target == seat \
                and info.night <= day and info.player not in out:
            out.append(info.player)
    return out


@survives_execution_rule
def a_lleech_outlives_the_gallows(world, state, day, seat):
    """A working Lleech whose host lives walks away from its execution
    (11.10.2026). Any Lleech: one made later has a host nobody tracks."""
    if not _in_bag(state, "Lleech"):
        return []
    phase = f"D{day}"
    if world.role_at(seat, phase) != "Lleech":
        return []
    if seat == world.find("Lleech") \
            and _host_gone_by(state, _lleech_host(state), phase):
        return []
    return [seat]


@survives_execution_rule
def a_psychopath_wins_at_roshambo(world, state, day, seat):
    """ "If executed, you only die if you lose roshambo." Working, it may
    walk away from the gallows, and that costs nothing (10.10.2026)."""
    if not _in_bag(state, "Psychopath"):
        return []
    if world.role_at(seat, f"D{day}") != "Psychopath":
        return []
    # Babysitting Lil' Monsta, it dies when executed (their jinx).
    if babysitter_at(world, f"D{day}") == seat:
        return []
    return [seat]


@survives_execution_rule
def a_pacifist_may_spare_the_good(world, state, day, seat):
    """Some executed good players do not die — the Storyteller decides.

    A choice rather than a rule, so an executed good player who *did* die
    proves nothing. It only ever explains a survival.
    """
    if not _on_board(state, "Pacifist"):
        return []
    phase = f"D{day}"
    if world.evil_at(seat, phase):
        return []                         # only the good are spared
    return [sober_seat(world, state, p, "Pacifist", phase)
            for p in _holders(world, state, "Pacifist", phase)
            if p in state.alive_set(phase)]


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


def _at_the_gallows(state, day, world=None):
    """Who is standing when the town executes: the day's living, less
    anybody who already died earlier that day — a Witch's curse, a Golem's
    nominee, a Psychopath's pick. A Tea Lady's neighbours are counted
    then: the Golem killed the player beside her, and the next one along
    walked away from the gallows (10.10.2026). The executed seat stays.

    With `world`, a Lleech stays too: it dies *after* the gallows, of its
    host hanging there (11.10.2026). Asked only where a death beside her
    is held against the Tea Lady, where keeping it can only excuse her."""
    phase = f"D{day}"
    hanged = state.executed_on(day)
    return frozenset(p for p in state.alive_set(phase)
                     if p == hanged or phase not in state.died_at(p)
                     or (world is not None
                         and world.role_at(p, phase) == "Lleech"))


def _tea_lady_keeping(world, state, seat, phase, alive=None):
    """The Tea Lady whose protection covers this seat right now, if any.

    Both her living neighbours good, and this seat one of them. Asked of
    a phase, because who is living beside her changes as people die —
    and it is asked at night and in daylight alike.
    """
    ladies = _tea_ladies_keeping(world, state, seat, phase, alive)
    return ladies[0] if ladies else None


def _tea_ladies_keeping(world, state, seat, phase, alive=None):
    """Every Tea Lady whose protection covers this seat right now.

    There can be two: a Philosopher that took the Tea Lady sits beside
    the seat as well, and the real one is drunk for it. Asking only the
    first had the drunk one keep a neighbour from the gallows, and the
    world that really happened was not a world (21.10.2026)."""
    if alive is None:
        alive = state.alive_set(phase)
    return [lady for lady in _holders(world, state, "TeaLady", phase)
            if lady in alive and _keeps(world, state, lady, seat, phase,
                                        alive)]


def _keeps(world, state, lady, seat, phase, alive):
    """Does this Tea Lady's protection cover this seat right now?"""
    around = _living_beside(state, lady, phase, alive)
    # One other player left alive is her neighbour on both sides, and
    # "both your alive neighbours are good" is true of them. This wanted
    # two different seats, so the last player standing beside her could
    # be executed and die (03.10.2026 — a Zombuul under its shroud, a
    # Fool and a Tea Lady, in a game that ran six nights).
    if seat not in around:
        return False
    # In seat order, as in JavaScript: which of two neighbours is asked
    # first decides whose side was asked about at all (`note_side_read`).
    if any(world.evil_at(p, phase) for p in sorted(around)):
        return False                      # one of them is evil, so nothing
    return True


def _beside_a_side_nobody_knows(world, state, lady, phase, alive=None):
    """Is one of her living neighbours on a side that can turn?

    A Goon is on whichever side last chose it, and nobody writes that
    down. With one beside her she may be protecting and she may not, and
    the board cannot say — so her protection can explain somebody living
    and a death beside her proves nothing about her (03.10.2026, the
    first played games in which a Goon turned).
    """
    return any(side_open(world, state, p, phase)
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
    if not _on_board(state, "TeaLady"):
        return []
    return [sober_seat(world, state, lady, "TeaLady", f"D{day}")
            for lady in _tea_ladies_keeping(world, state, seat, f"D{day}",
                                            _at_the_gallows(state, day))]


@survives_execution_rule
def a_fool_walks_away_once(world, state, day, seat):
    """Its one free death covers the gallows as well as the night."""
    if not _on_board(state, "Fool"):
        return []
    if not _has_ability(world, state, seat, "Fool", f"D{day}"):
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
    return [sober_seat(world, state, seat, "Fool", f"D{day}")]


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
    if not _on_board(state, "Sailor"):
        return []
    if not _has_ability(world, state, seat, "Sailor", f"D{day}"):
        return []
    return [sober_seat(world, state, seat, "Sailor", f"D{day}")]


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
    seat = holding_now(world, state, "Zombuul", phase)
    if seat is None or not _zombuul_still_going(world, state, seat, phase):
        return []
    if any(f"D{night - 1}" in state.died_at(who)
           for who in (state.deaths or {})):
        return []                         # somebody went in daylight
    return [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON, demon=seat,
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
    seat = holding_now(world, state, "Pukka", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    # Made the Pukka tonight — by an Engineer, or at a tea party — it only
    # poisons, as on a first night: nothing it chose is due yet
    # (26.10.2026).
    from .worlds import tea_made
    if tea_made(world, seat, night):
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
        if any(holding_now(world, state, "Pukka", f"N{k}") != seat
               or seat not in state.alive_set(f"N{k}")
               or not _could_be_stopped(world, state, seat, k)
               for k in range(max(chose, 0) + 1, night)):
            break
        demands = tuple((k, seat) for k in range(max(chose, 0) + 1, night))
        if chose < 1:
            excuses.append((None, demands))
            break
        if holding_now(world, state, "Pukka", f"N{chose}") != seat \
                or seat not in state.alive_set(f"N{chose}"):
            break
        excuses.append((frozenset(state.alive_set(f"N{chose}")), demands))
    out = [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON, demon=seat,
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
        if any(holding_now(world, state, "Pukka", f"N{k}") != seat
               or seat not in state.alive_set(f"N{k}")
               for k in range(chose, night)):
            break
        out.append(death_causes.Cause(
            name="Demon", kind=death_causes.DEMON, demon=seat,
            seats=frozenset(state.alive_set(f"N{chose}")),
            capacity=1, victim_impaired_at=chose,
            also_impaired=tuple((k, seat) for k in range(chose + 1, night))))
    return out


def al_hadikhia_chosen(state, night):
    """Every seat the Al-Hadikhia's row names for that night, once each."""
    return sorted({p for info in state.infos
                   if isinstance(info, AlHadikhiaChose)
                   and info.night == night for p in info.chosen()})


@death_causes.cause_rule
def an_al_hadikhia_chooses(world, state, night):
    """The three it chose, and each chose life or death.

    Any of them may die: whoever chose death, or all of them if all chose
    life. So it fires — at least one of the three is not standing at
    dawn — unless one of them was a corpse that chose death, which leaves
    the three short and nobody else need die; or one was kept from dying
    (Patrick's B, 21.10.2026: a protected player counts as choosing life
    and stays when the others go — the shields on the Demon's kind do
    that, and a shield on any one of the three is taken to be enough,
    which is the permissive side of it); or the Al-Hadikhia itself was
    drunk or poisoned, and then nothing happened (C).

    Only seats it chose, and only with a row: a night with no row is one
    on which it chose nobody, and nobody dies of it (A).
    """
    if night < 2 or not _in_bag(state, "AlHadikhia"):
        return []
    chosen = al_hadikhia_chosen(state, night)
    if not chosen:
        return []
    phase = f"N{night}"
    seat = holding_now(world, state, "AlHadikhia", phase)
    if seat is None or world.role_at(seat, phase) != "AlHadikhia" \
            or seat not in state.alive_set(phase):
        return []
    alive = state.alive_set(phase)
    # A corpse that chose death leaves it nobody to kill — and so does one
    # that died earlier tonight by another hand, a Gambler's wrong guess
    # (4-night gate seed 1932, 21.10.2026): dead by its turn.
    corpse = any(p not in alive or phase in state.died_at(p)
                 for p in chosen)
    return [death_causes.Cause(
        name="AlHadikhia", kind=death_causes.DEMON, demon=seat,
        seats=frozenset(chosen), capacity=len(chosen), must_fire=True,
        actor=seat, actor_cost=DEMON_POISONED_PENALTY,
        excuses=((None, ()),) if corpse else ())]


@death_causes.cause_rule
def a_lil_monsta_may_kill(world, state, night):
    """"Each night*, a player might die" (D, Weg 1, 21.10.2026).

    The Storyteller's choice, so it may kill nobody, and never the
    babysitter. A kill by the Demon: a Monk, a Soldier, a Tea Lady keep
    a player from it, a Princess's day or an Exorcist that named the
    babysitter stop it, a Grandmother goes with her grandchild. Lil'
    Monsta is no player, so nothing droisons it. Once its babysitter is
    dead it kills nobody: a Mastermind's day.
    """
    if night < 2 or not _in_bag(state, "LilMonsta"):
        return []
    phase = f"N{night}"
    sitter = babysitter_at(world, phase)
    if sitter is None or sitter not in state.alive_set(phase):
        return []
    if any(phase_index(at) < phase_index(phase)
           for at in state.died_at(sitter)):
        return []
    return [death_causes.Cause(
        name="LilMonsta", kind=death_causes.DEMON, demon=sitter,
        seats=frozenset(p for p in range(state.n_players) if p != sitter),
        capacity=1, must_fire=False)]


@death_causes.cause_rule
def a_shabaloth_kills_twice(world, state, night):
    """Two a night, and it may bring one of them back.

    Either kill can be aimed at somebody already dead, so the table may
    only ever see one body.
    """
    if not _in_bag(state, "Shabaloth") or night < 2:
        return []
    phase = f"N{night}"
    seat = holding_now(world, state, "Shabaloth", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    return [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON, demon=seat,
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
    seat = holding_now(world, state, "Po", phase)
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
        name="Demon", kind=death_causes.DEMON, demon=seat,
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
    if not _on_board(state, "Gossip") or night < 2:
        return []
    phase = f"N{night}"
    # Any living holder, a Philosopher's too (13.10.2026). One kill
    # however many: the holder a Philosopher took it from is drunk.
    if not any(seat in state.alive_set(phase)
               for seat in _holders(world, state, "Gossip", phase)):
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
    if not _on_board(state, "Tinker"):
        return []
    phase = f"N{night}"
    # Each living holder, a Philosopher's too (13.10.2026).
    seats = frozenset(seat for seat in _holders(world, state, "Tinker", phase)
                      if seat in state.alive_set(phase))
    if not seats:
        return []
    return [death_causes.Cause(name="Tinker", kind=death_causes.OTHER,
                               seats=seats, capacity=len(seats),
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
    if not _on_board(state, "Moonchild") or night < 2:
        return []
    phase = f"N{night}"
    # The holder, and a Philosopher that took it (13.10.2026).
    holders = _holders(world, state, "Moonchild", phase)
    return [cause for child in holders
            for cause in _a_moonchilds_pick(
                world, state, night, child,
                _cause_name(world, holders, "Moonchild", child, phase))]


def _a_moonchilds_pick(world, state, night, child, name="Moonchild"):
    phase = f"N{night}"
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
        return [death_causes.Cause(name=name,
                                   kind=death_causes.OTHER,
                                   seats=good, capacity=1)]
    good = good & picked
    if not good:
        return []                         # it named somebody evil
    # A Goon it named may have been turned by then, and nobody knows:
    # the pick may kill and need not.
    if any(side_open(world, state, seat, phase) for seat in good):
        return [death_causes.Cause(name=name,
                                   kind=death_causes.OTHER,
                                   seats=good, capacity=1)]
    return [death_causes.Cause(name=name, kind=death_causes.PICKED,
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
    if not _on_board(state, "Acrobat") or night < 2:
        return []
    phase = f"N{night}"
    # Each living holder with a pick recorded — its own, when a
    # Philosopher took it too (13.10.2026).
    holders = _holders(world, state, "Acrobat", phase)
    seats = frozenset(
        seat for seat in holders if seat in state.alive_set(phase)
        and any(isinstance(info, AcrobatChoice) and info.night == night
                and _by(holders, seat) in (None, info.player)
                for info in state.infos))
    if not seats:
        return []                         # no pick recorded, no risk
    return [death_causes.Cause(name="Acrobat", kind=death_causes.OTHER,
                               seats=seats, capacity=len(seats),
                               must_fire=False)]


def _has_ability(world, state, seat, role, phase):
    """Does this seat have that ability — held, taken by a Philosopher, or
    given the Demon by the Boffin (26.10.2026)?"""
    if world.role_at(seat, phase) == role:
        return True
    return took_it(world, state, seat, role, phase)


def _on_board(state, role):
    """On the script, or taken by a Philosopher on this board."""
    if _in_bag(state, role):
        return True
    # Asked hundreds of thousands of times a solve once a tea party
    # multiplies the stories (22.10.2026): what the Philosophers took is
    # read off the board once, as `philosophies` already is.
    taken = getattr(state, "_taken_cache", None)
    if taken is None or taken[0] is not state.philosophies():
        got = state.philosophies() or {}
        taken = (got, frozenset(role for role, _since in got.values()))
        state._taken_cache = taken
    return role in taken[1]


def _holders(world, state, role, phase):
    """Every seat with that ability then: the one holding it, and any
    Philosopher that took it (open item 56, step 2, 13.10.2026). The
    holder a Philosopher took it from is drunk while the Philosopher
    lives (`a_philosopher_drunks_whoever_had_it`), so both are asked and
    the plan settles which one worked."""
    out = []
    seat = world.find_at(role, phase)
    if seat is not None:
        out.append(seat)
    for who in sorted(state.philosophies() or {}):
        if who not in out and took_it(world, state, who, role, phase):
            out.append(who)
    # And a Demon the Boffin gave it (26.10.2026).
    for who in boffin_holders(world, state, role, phase):
        if who not in out:
            out.append(who)
    return out


def _by(holders, seat):
    """Whose recorded choice to read: anybody's when there is one holder,
    as always; its own when there are two (13.10.2026)."""
    return seat if len(holders) > 1 else None


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
    # A Demon the Boffin gave it (26.10.2026).
    given = boffin_holders(world, state, role, phase)
    return given[0] if given else None


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
    began = f"B{night - 1}"
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
    # And a Demon the Boffin gave it (26.10.2026).
    for who in boffin_holders(world, state, "Gambler", began):
        if who not in holders:
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


def _a_sweetheart_died(world, state, night):
    phase = f"N{night}"
    return any(phase in state.died_at(p)
               and falls_as(world, state, p, "Sweetheart", phase)
               for p in range(state.n_players))


# A night nothing was due: no phrase said, or the Storyteller let it
# pass. A cause that fires and may always have had nothing to fire for.
_NOTHING_DUE = ((None, ()),)


@death_causes.cause_rule
def a_yaggababble_kills_for_each_time(world, state, night):
    """ "For each time you said it publicly today, a player might die."

    How often it said its phrase only the Storyteller knows, so from the
    second night it may be behind any number of bodies, or none. The
    first costs nothing, every further one `YAGGABABBLE_AGAIN_PENALTY`,
    and a quiet night nothing — it "might". Two causes for that reason:
    the same Demon, the first kill and the ones after it.

    The Demon's own kills (table ruling, 11.10.2026): a Soldier is safe
    and a Monk guards, a Sage and a Grandmother answer to it, and the
    Exorcist naming it stops it (their jinx, and every Demon's rule).
    What counts is the moment of the kill, so drunk or poisoned that
    night it kills nobody — whatever it was when it spoke. Never itself.
    """
    if not _in_bag(state, "Yaggababble") or night < 2:
        return []
    phase = f"N{night}"
    demon = _demon_holding(world, phase, "Yaggababble")
    # Whoever held it when its deaths were counted. One that died tonight
    # handed the star on *after* that — to a Scarlet Woman — and the
    # night is one moment here, so the heir would read as having killed
    # the Demon it inherited from. As for the Exorcist: only a Demon that
    # died *as* one — a Snake Charmer swaps at 11, and the new Yaggababble
    # may well take the old one, a charmer by then.
    began = _demon_holding(world, f"B{night - 1}", "Yaggababble", phase)
    if began is not None and began != demon \
            and phase in state.died_at(began):
        demon = began
    elif demon is None:
        return []
    if demon not in state.alive_set(phase):
        return []
    reach = frozenset(p for p in state.alive_set(phase) if p != demon)
    if not reach:
        return []
    # Not on a night a Sweetheart dies: see `the_demon_kills`.
    actor = None if _a_sweetheart_died(world, state, night) else demon
    return [
        death_causes.Cause(
            name="Demon", kind=death_causes.DEMON, demon=demon, seats=reach,
            capacity=1,
            must_fire=True, actor=actor, excuses=_NOTHING_DUE),
        death_causes.Cause(
            name="Yaggababble, again", kind=death_causes.DEMON, demon=demon,
            seats=reach,
            capacity=max(1, len(reach) - 1),
            cost=YAGGABABBLE_AGAIN_PENALTY, must_fire=True, actor=actor,
            excuses=_NOTHING_DUE)]


def _a_leviathan_is_told_of(world):
    """Is there a Leviathan anywhere in this telling — dealt, or made
    since? Asked before anything is looked for: its rules are asked of
    every story of every world on a script that has one, and nearly all
    of those have none."""
    return "Leviathan" in world.roles or any(
        change.role == "Leviathan"
        for change in getattr(world, "changes", ()))


def _leviathan_at(world, state, phase):
    """The living seat holding the Leviathan at this moment, if any."""
    if not _a_leviathan_is_told_of(world):
        return None
    for seat in sorted(state.alive_set(phase)):
        if world.role_at(seat, phase) == "Leviathan":
            return seat
    return None


@death_causes.cause_rule
def a_leviathan_fells_a_banshee(world, state, night):
    """A Leviathan kills nobody — but for one jinx: "each night*, the
    Leviathan chooses an alive good player (different to previous
    nights): a chosen Banshee dies & gains their ability."

    So with a Banshee about, a body in the night may be hers and the
    Demon's doing after all, which is what her announcement needs. A
    choice, so a night without it owes nothing.
    """
    if not _in_bag(state, "Leviathan") or not _in_bag(state, "Banshee") \
            or night < 2:
        return []
    phase = f"N{night}"
    lev = _leviathan_at(world, state, phase)
    if lev is None or lev not in world.demons_at(phase):
        return []
    reach = frozenset(
        p for p in state.alive_set(phase)
        if p != lev and _has_ability(world, state, p, "Banshee", phase)
        and not world.evil_at(p, phase))
    if not reach:
        return []
    actor = None if _a_sweetheart_died(world, state, night) else lev
    return [death_causes.Cause(
        name="Demon", kind=death_causes.DEMON, demon=lev, seats=reach,
        capacity=1,
        must_fire=True, actor=actor, excuses=_NOTHING_DUE)]


@death_causes.cause_rule
def a_lycanthrope_may_kill(world, state, night):
    """ "Each night*, choose an alive player. If good, they die & the
    Demon doesn't kill tonight." Not the Demon's kill: a Monk or a Soldier
    is no help, an Innkeeper or a Tea Lady is (11.10.2026). Whoever it
    killed registered good, so never the faux paw; and when it kills, the
    Demon kills nobody (`deaths.Cause.quiets_demon`). A choice, so it may
    come to nothing and that costs nothing.
    """
    if not _on_board(state, "Lycanthrope") or night < 2:
        return []
    phase = f"N{night}"
    # Each living holder, a Philosopher's too, with its own actor
    # (13.10.2026).
    holders = _holders(world, state, "Lycanthrope", phase)
    return [cause for seat in holders
            if seat in state.alive_set(phase)
            for cause in _a_lycanthropes_pick(world, state, night, seat,
                                              _cause_name(world, holders,
                                                          "Lycanthrope",
                                                          seat, phase))]


def _cause_name(world, holders, role, seat, phase):
    """A Philosopher's kill beside the holder's has a name of its own:
    the death machinery counts each name's kills, and two of one name
    were one Lycanthrope firing twice (13.10.2026)."""
    if len(holders) > 1 and world.role_at(seat, phase) != role:
        return f"{role} (Philosopher)"
    return role


def _a_lycanthropes_pick(world, state, night, seat, name="Lycanthrope"):
    phase = f"N{night}"
    faux = _faux_paw(state)
    reach = frozenset(
        p for p in state.alive_set(phase)
        if p != faux and False in evil_registrations(
            world.role_at(p, phase), world.alignment_at(p, phase)))
    if not reach:
        return []
    return [death_causes.Cause(
        name=name, kind=death_causes.OTHER, seats=reach,
        capacity=1, actor=sober_seat(world, state, seat, "Lycanthrope",
                                     phase), quiets_demon=True)]


def _host_gone_by(state, host, phase):
    """Had the Lleech's host died by this moment?"""
    return host is not None and host >= 0 and any(
        phase_index(at) <= phase_index(phase) for at in state.died_at(host))


@death_causes.cause_rule
def a_lleech_follows_its_host(world, state, night):
    """ "You die if & only if they are dead." Its host died tonight or
    earlier, so the Lleech dies — tonight with the host, or the night it
    is working again (table ruling, 11.10.2026). Nothing stops it."""
    if not _in_bag(state, "Lleech"):
        return []
    # Dealt, or made later: a Summoner's (21.10.2026) is nobody's deal.
    dealt = world.find("Lleech")
    if dealt is None and "Lleech" not in getattr(world, "_roles_changed_to",
                                                 ()):
        return []
    phase = f"N{night}"
    here = phase_index(phase)
    reach = set()
    for seat in state.alive_set(phase):
        if world.role_at(seat, phase) != "Lleech":
            continue
        if seat == dealt:
            if _host_gone_by(state, _lleech_host(state), phase):
                reach.add(seat)
        # A Lleech made later — a Scarlet Woman's — chose a host nobody
        # follows: anybody already dead may have been it (11.10.2026).
        elif any(phase_index(at) <= here
                 for p, at in state.death_phases() if p != seat):
            reach.add(seat)
    if not reach:
        return []
    return [death_causes.Cause(
        name="Lleech's host", kind=death_causes.OTHER,
        seats=frozenset(reach), capacity=len(reach), unstoppable=True)]


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
        # Or a Philosopher that took her; not the real one it made drunk
        # (group 6, 14.10.2026).
        if not falls_as(world, state, seat, "Grandmother", f"N{night}"):
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
        out.append(death_causes.Implication(seat=seat, needs=sober_seat(
            world, state, seat, "Grandmother", f"N{night}")))
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
    if not _on_board(state, "TeaLady"):
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
    return [death_causes.Shield("Tea Lady", needs=sober_seat(
                world, state, lady, "TeaLady", phase),
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
    if not _on_board(state, "Fool"):
        return []
    phase = f"N{night}"
    if not _has_ability(world, state, seat, "Fool", phase):
        return []
    if seat not in state.alive_set(phase):
        return []                         # dead already, so no ability
    return [death_causes.Shield("Fool", needs=sober_seat(
        world, state, seat, "Fool", phase), chosen=True)]


@death_causes.immunity_rule
def a_sober_sailor_cannot_die(world, state, night, seat, kind):
    """Not by the Demon, not by anything.

    Always on rather than aimed, so a Sailor who died must have been
    impaired — including by its own ability, which is the price the town
    pays for having one.
    """
    if not _on_board(state, "Sailor"):
        return []
    if not _has_ability(world, state, seat, "Sailor", f"N{night}"):
        return []
    if seat not in state.alive_set(f"N{night}"):
        return []                         # dead already, so no ability
    return [death_causes.Shield("Sailor", needs=sober_seat(
        world, state, seat, "Sailor", f"N{night}"))]


@death_causes.immunity_rule
def an_innkeeper_guards_two(world, state, night, seat, kind):
    """From everything, not only the Demon — and it picks who."""
    if not _on_board(state, "Innkeeper"):
        return []
    phase = f"N{night}"
    holders = _holders(world, state, "Innkeeper", phase)
    return [shield for keeper in holders
            for shield in _an_innkeepers_pair(world, state, night, seat,
                                              keeper)]


def _an_innkeepers_pair(world, state, night, seat, keeper):
    phase = f"N{night}"
    if night < 2 or keeper not in state.alive_set(phase):
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
        return [death_causes.Shield("Innkeeper", needs=sober_seat(
            world, state, keeper, "Innkeeper", phase), chosen=True)]
    if seat not in picked:
        return []
    fell = phase in state.died_at(keeper)
    return [death_causes.Shield("Innkeeper", needs=sober_seat(
        world, state, keeper, "Innkeeper", phase), chosen=fell)]


@death_causes.immunity_rule
def an_exorcist_sends_the_demon_to_bed(world, state, night, seat, kind):
    """Choosing the Demon stops it waking at all, so nobody dies by it.

    Aimed rather than always on: it says nothing about a seat that did
    die, only that it could have been the reason one did not.

    Of two living Demons only the one chosen stays asleep; the other kills
    as ever (Hatter stage 2, Patrick 26.10.2026). Each Demon is then asked
    on its own, and the shield holds against that Demon's kill only.
    """
    if not _on_board(state, "Exorcist"):
        return []
    if kind != death_causes.DEMON or night < 2:
        return []
    phase = f"N{night}"
    demons = world.demons_at(phase)
    if len(demons) < 2:
        return _exorcist_shields(world, state, night, None)
    out = []
    for demon in demons:
        out.extend(s._replace(against=frozenset({demon}))
                   for s in _exorcist_shields(world, state, night, demon))
    return out


def _exorcist_shields(world, state, night, only):
    """Every Exorcist's shield against the Demon — or against this one of
    two (`only`)."""
    phase = f"N{night}"
    # Beside a Pukka what counts is last night's choice (below), so the
    # Exorcists of last night.
    pukka = (_demon_holding(world, phase, "Pukka") is not None
             if only is None else world.role_at(only, phase) == "Pukka")
    when = f"N{night - 1}" if pukka else phase
    return [shield
            for exorcist in _holders(world, state, "Exorcist", when)
            for shield in _an_exorcists_choice(world, state, night,
                                               exorcist, only, pukka)]


def _an_exorcists_choice(world, state, night, exorcist, only=None,
                         pukka=None):
    """One Exorcist's shield — the holder's or a Philosopher's (13.10.2026)
    — against the Demon, or against `only` of two."""
    phase = f"N{night}"
    if pukka is None:
        pukka = _demon_holding(world, phase, "Pukka") is not None
    if pukka:
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
        if night < 3 or exorcist not in state.alive_set(before):
            return []
        picked = _chosen(state, "Exorcist", night - 1, by=exorcist)
        targets = world.demons_at(before) if only is None else (only,)
        if picked is not None and not any(d in picked for d in targets):
            return []
        # It had to be working *then*, which is not tonight's question.
        return [death_causes.Shield("Exorcist", chosen=True)]
    if exorcist not in state.alive_set(phase):
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
    named = set()
    nows, befores = world.demons_at(phase), world.demons_at(f"B{night - 1}")
    sitter = babysitter_at(world, phase) is not None
    # Line by line, where two Demons live (Hatter stage 2, 25.10.2026):
    # only the line of the Demon asked about.
    for i in range(max(len(nows), len(befores), 1)):
        demon = nows[i] if i < len(nows) else None
        if only is not None and demon != only:
            continue
        began = befores[i] if i < len(befores) else None
        # Lil' Monsta's babysitter is chosen at 35, after the Exorcist: it
        # is last night's that the Exorcist can name (F, Weg 1,
        # 21.10.2026).
        if sitter:
            demon = began
        # Only a Demon that died *as* one. A Snake Charmer swaps at 11,
        # ahead of the Exorcist, and the new Demon may then kill the old —
        # which is a charmer by now, and was already one when the
        # Exorcist chose.
        if began is not None and began != demon \
                and phase in state.died_at(began) \
                and TEAM[world.role_at(began, phase)] == "demon":
            demon = began
        named.add(demon)
    if picked is not None and not named & set(picked):
        return []
    # And it cuts the other way. Named and written down, the Demon does
    # not act tonight — so a Demon kill on that night says the Exorcist
    # was not working, or that this seat is not the Demon. That second
    # reading is what the table draws from it, and it was not drawn here:
    # the shield was only ever an excuse for a quiet night.
    return [death_causes.Shield("Exorcist", needs=exorcist,
                                chosen=picked is None)]


@death_causes.immunity_rule
def an_announced_banshee_fell_to_the_demon(world, state, night, seat, kind):
    """The Banshee the table was told about died to the Demon, and to
    nothing else.

    "If the Demon kills you, all players learn this" — and only then: a
    Banshee taken by an Assassin, a Gossip or a grieving grandchild goes
    quietly (table ruling, 08.10.2026: the announcement, and the
    ability with it, comes only from a Demon's kill). So on the night of
    an announcement, every other way of dying is closed to that seat.

    Written as a shield nothing had to be working for, the same shape
    as a corpse that cannot be killed again.
    """
    if kind == death_causes.DEMON or not _in_bag(state, "Banshee"):
        return []
    for info in state.infos:
        if getattr(info, "source_role", None) == "Banshee" \
                and info.night == night and info.hard() \
                and seat in info.leaned_on(world, state):
            return [death_causes.Shield("Banshee announced")]
    return []


@death_causes.immunity_rule
def a_choirboys_king_fell_to_the_demon(world, state, night, seat, kind):
    """A working Choirboy was shown the Demon, so the King it died with
    fell to the Demon and to nothing else (10.10.2026). Any other way of
    dying that night says the Choirboy was not working — the Soldier's
    shape, needing the Choirboy rather than the King."""
    if kind == death_causes.DEMON or not _in_bag(state, "Choirboy"):
        return []
    phase = f"N{night}"
    # A Philosopher with either counts (group 6, Q, 14.10.2026).
    if not _has_ability(world, state, seat, "King", phase):
        return []
    out = []
    for info in state.infos:
        if isinstance(info, ChoirboyInfo) and info.night == night \
                and _has_ability(world, state, info.player, "Choirboy",
                                 phase):
            out.append(death_causes.Shield("Choirboy", needs=info.player))
    return out[:1]


@death_causes.immunity_rule
def the_killer_of_two_was_named(world, state, night, seat, kind):
    """Of two living Demons, the one that killed is the one a Sage is
    shown among its two and a Choirboy is shown (Hatter stage 2, Patrick
    26.10.2026): the other Demon's kill cannot have taken this seat while
    the reading was genuine. A bar, never a reason a kill came to
    nothing."""
    if kind != death_causes.DEMON or night < 2:
        return []
    if not (_on_board(state, "Sage") or _on_board(state, "Choirboy")):
        return []
    phase = f"N{night}"
    demons = world.demons_at(phase)
    if len(demons) < 2:
        return []
    for info in state.infos:
        if info.night != night:
            continue
        if isinstance(info, SageInfo) and info.player == seat:
            named, needs = (info.a, info.b), seat
        elif isinstance(info, ChoirboyInfo) \
                and _has_ability(world, state, seat, "King", phase):
            named, needs = (info.target,), info.player
        else:
            continue
        others = frozenset(d for d in demons if d not in named)
        if others:
            return [death_causes.Shield("named", needs=needs, against=others,
                                        bars_only=True)]
    return []


@death_causes.immunity_rule
def a_princess_stops_the_demon(world, state, night, seat, kind):
    """ "On your 1st day, if you nominated & executed a player, the Demon
    doesn't kill tonight." Her first day as the Princess, the nominee
    executed — dead of it or not — and her ability working at night: a
    drunk Princess by day and sober at night still stops it (10.10.2026).
    The Demon chooses as ever; nobody dies of it."""
    if kind != death_causes.DEMON or not _on_board(state, "Princess"):
        return []
    day = night - 1
    if day < 1:
        return []
    for info in state.infos:
        if not isinstance(info, PrincessNominated) or info.night != day:
            continue
        princess = info.player
        if not _has_ability(world, state, princess, "Princess", f"D{day}"):
            continue
        if day > 1 and _has_ability(world, state, princess, "Princess",
                                    f"D{day - 1}"):
            continue                      # not her first day
        if state.executed_on(day) != info.target:
            continue
        if princess not in state.alive_set(f"N{night}"):
            continue                      # dead, so no ability tonight
        # Made something else tonight, she may have been so before the
        # Demon's turn — a Pit-Hag at 16 — or after it, a Barber at 40.
        # The night is one moment here, so then it explains a quiet
        # night and a kill says nothing about her (found at the gate of
        # the eighth five, 11.10.2026: a Princess the Pit-Hag made a Goon
        # and the Demon then killed).
        unmade = not _has_ability(world, state, princess, "Princess",
                                  f"N{night}")
        return [death_causes.Shield("Princess", needs=sober_seat(
                    world, state, princess, "Princess", f"N{night}"),
                                    chosen=unmade)]
    return []


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
    if not _on_board(state, "Mayor") or kind != death_causes.DEMON:
        return []
    phase = f"N{night}"
    if not _has_ability(world, state, seat, "Mayor", phase):
        return []
    if seat not in state.alive_set(phase):
        return []                         # dead already, so no ability
    # Somebody has to already be dead for the kill to go nowhere.
    if len(state.alive_at(phase)) >= state.n_players:
        return []
    return [death_causes.Shield("Mayor", needs=sober_seat(
        world, state, seat, "Mayor", phase), chosen=True)]


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


@death_causes.immunity_rule
def the_lleech_lives_while_its_host_does(world, state, night, seat, kind):
    """ "You die if & only if they are dead": while its host lives, a
    working Lleech cannot die (11.10.2026). Aiming its own kill at
    itself is a quiet night like a sunk kill, and priced as one."""
    if not _in_bag(state, "Lleech"):
        return []
    lleech = world.find("Lleech")
    if lleech is None or seat != lleech:
        return []
    phase = f"N{night}"
    if world.role_at(lleech, phase) != "Lleech":
        return []
    if _host_gone_by(state, _lleech_host(state), phase):
        return []
    cost = SUNK_KILL_PENALTY if kind == death_causes.DEMON else 1.0
    return [death_causes.Shield("Lleech", needs=lleech, cost=cost)]


def _night_deaths(state):
    """{night: [seats that died that night]}"""
    # Held for the length of one `best_story`, like `final_phase`.
    held = getattr(state, "_night_deaths_held", None)
    if held is not None:
        return held
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
    for world in iter_worlds(state.n_players, state.dealt_claims(),
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
            if seat in view.demons_at(f"D{day}"):
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
    # And the hidden choices of this telling: whom a Lycanthrope cannot
    # kill, and whose death takes a Lleech with it (`_hidden_choices`).
    if not _LISTENING[0]:                 # nobody turns evil that way here
        key = (night, upto, getattr(state, "_hidden", None))
        got = memo.get(key)
        if got is None:
            died = set(_night_deaths(state).get(night, ()))
            got = memo[key] = _the_ones_that_can_win(
                death_causes.explain_night(world, state, night, died))
        return got
    # Kept per everything but who turned evil, and with whose side was
    # asked about on the way: a story that differs only in a seat nobody
    # asked about is handed the same answer (`_explain_or_recall`).
    flips, _turns, rest = _who_turned(upto)
    key = ("turned", night, rest, getattr(state, "_hidden", None))
    kept = memo.setdefault(key, [])
    for theirs, reads, got in kept:
        if _differ_only_unasked(flips, theirs, reads):
            replay_reads(reads)
            return got
    died = set(_night_deaths(state).get(night, ()))
    begin_reads()
    try:
        got = _the_ones_that_can_win(
            death_causes.explain_night(world, state, night, died))
    finally:
        reads = end_reads()
    kept.append((flips, reads, got))
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


# Sources a fallback of the plan may set aside whole: one that was itself
# off when it chose (see `_impairment_plan`).
_SET_ASIDE = ("Courtier", "Philosopher", "Preacher")


def _surely_impaired(world, state, night):
    """Seats impaired tonight whatever the plan decides.

    An unavoidable source — a Minstrel's whole table, the Drunk — that no
    path of the plan can set aside: not a resting one, not a Courtier's,
    a Philosopher's or a Preacher's, and not one whose actor is a
    Philosopher (a drunk one gained nothing). An account asking one of
    these seats to be working is refused by the plan every time, but only
    after the cap has made its cut — the same as with what the board asks
    (13.10.2026, the gate of group 1: a Minstrel's night where a dead
    Philosopher-Soldier had been one more way to read it).
    """
    took = state.philosophies() or {}
    out = set()
    for source in impairment.silenced_out(
            impairment.sources_on(world, state, night)):
        if not source.unavoidable() or source.name in impairment.RESTING \
                or source.name in _SET_ASIDE or source.actor in took:
            continue
        out |= set(source.seats)
    return out


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
        sure = None
        for extra_cost, extra_impaired, extra_working, earlier \
                in _the_ones_the_board_allows(
                    night, _explained_night(world, state, night),
                    impaired_already or {}, working_already or {}):
            if extra_impaired & extra_working:
                continue                  # asked to be both at once
            if extra_working:
                if sure is None:
                    sure = _surely_impaired(world, state, night)
                if extra_working & sure:
                    continue              # the plan would refuse it
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
        if seat in changed:
            return                        # it said it was handed another
        roles = frozenset(roles)
        pinned[seat] = roles if seat not in pinned else pinned[seat] & roles

    # Pinned on the character the seat was *dealt*, which is what the
    # search enumerates. Where something can change characters that is
    # not the one it held in daylight: a Pit-Hag's Slayer, a Snake
    # Charmer that swapped into the Demon it was then shot as (Stelle 59,
    # 14.10.2026). Then nothing is pinned and the hard row does the work.
    movers = ("PitHag", "Barber", "SnakeCharmer", "Farmer", "Huntsman",
              "FangGu")
    if any(_on_board(state, key) for key in movers):
        return pinned
    changed = {info.player for info in state.infos
               if isinstance(info, BecameInfo)}

    # A Philosopher that wrote down taking it may be the one (group 5,
    # 14.10.2026).
    def or_its_philosopher(seat, role):
        taken = (state.philosophies() or {}).get(seat)
        out = [role, "Philosopher"] if taken and taken[0] == role \
            else [role]
        # Or a Demon the Boffin gave it (26.10.2026).
        if _boffin_on_board(state):
            out += list(state.script.demons)
        return out

    for info in state.infos:
        if isinstance(info, VirginNomination) and info.triggered:
            pin(info.player, or_its_philosopher(info.player, "Virgin"))
            # The nomination only fires on a Townsfolk, or the Spy wearing
            # one. The Drunk is an Outsider, so a Drunk nominator is out.
            townsfolk = list(state.script.townsfolk)
            spies = [k for k in state.script.keys
                     if "townsfolk" in CHARACTERS[k].registers]
            pin(info.nominator, townsfolk + spies)
        elif isinstance(info, SlayerShot) and info.died:
            pin(info.player, or_its_philosopher(info.player, "Slayer"))
            # Not the target: the Demon it hit may be a Minion that caught
            # the star, which was dealt something else. It pinned Imp or
            # Recluse until 14.10.2026, which also lost every landed shot
            # at another Demon.
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


# A Zealot that did not vote on a day with a nomination and five alive.
#
# "Must" is the player's to keep: the wiki calls not voting cheating,
# says the Storyteller does not police it, and that it holds drunk or
# poisoned — so there is no excuse the plan could pay for.
#
# Priced at first (0.1), on the reasoning that a vote nobody wrote down
# is likelier at a real table. Table ruling, 08.10.2026: the votes are
# to be entered correctly, and a Zealot that did not vote is no Zealot.
# So it rules the world out.


def _a_zealot_kept_its_hand_down(world, state):
    """Did this world's Zealot sit out a vote it had to cast?"""
    if not _in_bag(state, "Zealot"):
        return False
    for day, voted in (state.votes or {}).items():
        # Only a day somebody wrote votes down for, with a nomination
        # to have voted on.
        if not voted or not (state.nominations or {}).get(day):
            continue
        phase = f"D{day}"
        alive = state.alive_set(phase)
        # Five alive at every nomination: whoever dropped during the day
        # other than at the gallows may have gone before the vote.
        fell = sum(1 for p in alive if phase in state.died_at(p)
                   and state.execution_death(day) != p)
        if len(alive) - fell < 5:
            continue
        for seat in alive:
            # And a Philosopher that took it (group 5, 14.10.2026).
            if seat not in voted and phase not in state.died_at(seat) \
                    and (world.role_at(seat, phase) == "Zealot"
                         or took_it(world, state, seat, "Zealot", phase)):
                return True
    return False


class _AsRecluse:
    """The world with one seat read as the Recluse, for registration only.

    A Philosopher that took the Recluse registers as it would, dead or
    alive (group 6, N and F, 14.10.2026). Registration is asked in fifty
    places by character; rather than teach each one, a row that does not
    hold is asked again with that seat read as the Recluse. Everything
    else is the world's own."""

    def __init__(self, world, seat):
        self._world = world
        self._seat = seat

    def role_at(self, seat, phase):
        return "Recluse" if seat == self._seat \
            else self._world.role_at(seat, phase)

    def team_at(self, seat, phase):
        return TEAM[self.role_at(seat, phase)]

    def find_at(self, role, phase):
        for seat in range(len(self._world.roles)):
            if self.role_at(seat, phase) == role:
                return seat
        return None

    def __getattr__(self, name):
        return getattr(self._world, name)


def _philosopher_recluses(world, state, phase):
    """Philosophers that took the Recluse, by then — alive or dead (F)."""
    return [who for who in sorted(state.philosophies() or {})
            if took_it(world, state, who, "Recluse", phase)]


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
    # Rows that held only if somebody other than their source was
    # impaired or working: (night, the source, impaired, working). Either
    # that or the source off will do, and the plan holds sets rather than
    # alternatives, so `_explain` tries both. So far only a Chambermaid
    # whose count turns on a Wraith (table ruling, 08.10.2026).
    state._either = either = []
    # Rows that held only with the faux paw reading evil: (night, the
    # Lycanthrope) -> their sources. See below.
    faux_working = {}
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
        vortox = holding_now(world, state, "Vortox", f"D{day}")
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
        # "If just 3 players live, you lose this ability" — and the curse
        # goes with it, so nobody drops dead nominating at a table of
        # three.
        if witch is not None and minion_still_acts(world, state, witch,
                                                   f"N{day}") \
                and len(state.alive_set(f"D{day}")) > 3:
            working.setdefault(day, set()).add(witch)
            continue
        # Or a Yaggababble's kill by day, which is rare and costs: "for
        # each time you said it publicly today, a player might die", and
        # the Storyteller may take them there and then (table ruling,
        # 11.10.2026, way 1 of X). Never itself.
        yagga = (_yaggababble_at(world, state, f"D{day}")
                 if _in_bag(state, "Yaggababble") else None)
        if yagga is None or yagga == seat:
            return None, None, 1.0, None
        invented *= YAGGABABBLE_BY_DAY_PENALTY
        working.setdefault(day, set()).add(yagga)
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
        # Not when she is the one executed: a Scarlet Woman babysitting
        # Lil' Monsta (21.10.2026).
        if scarlet_woman_takes_over(world, state, change.phase) \
                and world.find_at("ScarletWoman", change.phase) \
                != change.seat:
            failures[day].add(world.find_at("ScarletWoman", change.phase))

    # The Summoner (21.10.2026): working when it made the Demon — unless a
    # Courtier or a Preacher took its ability, and the Storyteller made it
    # instead (their jinxes) — and drunk or poisoned on a turn that made
    # none (E, Weg 1).
    if _in_bag(state, "Summoner"):
        # An Engineer that took a living Summoner's character left its
        # ability to the Storyteller (their jinx, 26.10.2026, F Weg 1):
        # then the Demon comes whatever became of that player.
        away = (_summoner_engineered_away(world, state)
                if _engineer_on_board(state) else None)
        jinxed = away is None and _engineer_on_board(state) \
            and _engineer_may_take_the_summoner(state)
        # Whether the Engineer took it is a question about the board from
        # its night on: asked as one, so a telling that fails here is not
        # taken for one that fails with any choice (`_best_story_told`).
        if _engineer_on_board(state) and world.find("Summoner") is not None \
                and _engineer_may_take_the_summoner(state):
            world.role_at(world.find("Summoner"), "N3")
        for change in getattr(world, "changes", ()):
            summoner = world.find("Summoner")
            if summoner is None:
                break
            night = int(change.phase[1:])
            if isinstance(change, NotSummoned) and away is not None:
                return None, None, 1.0, None
            if isinstance(change, Summoned) and jinxed:
                # Offered for the Storyteller's summoning: the Summoner's
                # own needs it alive on its turn.
                gone = sorted(state.died_at(summoner), key=phase_index)
                if gone and phase_index(gone[0]) < phase_index(change.phase):
                    return None, None, 1.0, None
            if isinstance(change, Summoned):
                if away is None and not (_on_board(state, "Courtier")
                                         or _on_board(state, "Preacher")):
                    working.setdefault(night, set()).add(summoner)
            elif isinstance(change, NotSummoned) and change.phase == "N3" \
                    and summoner in state.alive_set("N3"):
                failures[night].add(summoner)

    # A Summoner chosen at a tea party (Hatter stage 2, 25.10.2026): working
    # when it made a Demon, and drunk or poisoned on a third night it
    # reached holding it, alive, with none made.
    if _in_bag(state, "Summoner") and _tea_on_board(state):
        made = next((c for c in getattr(world, "changes", ())
                     if isinstance(c, Summoned)), None)
        final = phase_index(state.final_phase())
        for change in hatted_summoners(world):
            seat = change.seat
            if made is not None:
                if not (_on_board(state, "Courtier")
                        or _on_board(state, "Preacher")):
                    working.setdefault(int(made.phase[1:]), set()).add(seat)
            elif final >= phase_index("D3") and _summons_on(change, 3) \
                    and seat in state.alive_set("N3") \
                    and "N3" not in state.died_at(seat) \
                    and world.role_at(seat, "N3") == "Summoner":
                failures[3].add(seat)

    # The Hatter (22.10.2026): whoever chose a new character did so
    # because a Hatter died working. Nobody choosing asks nothing — they
    # may always keep what they have.
    # The Engineer (26.10.2026): drunk or poisoned where its choice would
    # have changed somebody and did not.
    if _engineer_on_board(state):
        for night, seats in engineer_failed(world, state).items():
            failures[night].update(seats)

    parties = tea_parties(world) if _hatter_on_board(state) else {}
    if parties:
        died = hatter_deaths(world, state)
        for at in parties:
            night = int(at[1:])
            why = [(seat, phase) for seat, phase in died
                   if _tea_night(phase) == night]
            if not why:
                return None, None, 1.0, None
            seat, phase = why[-1]
            working.setdefault(int(phase[1:]), set()).add(seat)

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
        # And a Philosopher that took her (group 6, D, 14.10.2026).
        if _has_ability(world, state, seat, "Saint", f"D{day}"):
            failures[day].add(sober_seat(world, state, seat, "Saint",
                                         f"D{day}"))
        # A Sailor cannot die, and that holds in daylight too — so a
        # working one walks away from its own execution. Somebody
        # executed and killed was not a working Sailor, which means
        # something had to have stopped it working.
        if _has_ability(world, state, seat, "Sailor", f"D{day}"):
            failures[day].add(sober_seat(world, state, seat, "Sailor",
                                         f"D{day}"))
        # And the same for a Tea Lady's neighbour: executed and dead, so
        # she was not working. The mirror of her saving one.
        if _on_board(state, "TeaLady"):
            standing = _at_the_gallows(state, day, world)
            for lady in _tea_ladies_keeping(world, state, seat, f"D{day}",
                                            standing):
                if not _beside_a_side_nobody_knows(
                        world, state, lady, f"D{day}", standing):
                    failures[day].add(sober_seat(world, state, lady,
                                                 "TeaLady", f"D{day}"))

    # A Vizier cannot die during the day — by the gallows or anything
    # else. One that did was not working: drunk or poisoned, it dies like
    # anybody (table ruling, 10.10.2026). Drunk by a Courtier it would
    # not die even so (their jinx), which the plan cannot tell apart from
    # any other drunkenness; so that is allowed rather than ruled out.
    if _in_bag(state, "Vizier"):
        for seat, phase in state.death_phases():
            if phase[:1] == "D" \
                    and world.role_at(seat, phase) == "Vizier" \
                    and not (_executed(state, int(phase[1:]), seat)
                             and babysitter_at(world, phase) == seat):
                failures[int(phase[1:])].add(seat)

    # A Lleech dies when its host does and not before (11.10.2026). The
    # host is this telling's hidden choice. Dying with it, the Lleech was
    # working; outliving it, or dying first, it was not — it dies as
    # anybody would only while drunk or poisoned, and a host gone while
    # it was off takes it the moment it works again.
    if _in_bag(state, "Lleech"):
        lleech = world.find("Lleech")
        host = _lleech_host(state)
        if lleech is not None and host is not None:
            mine = sorted(state.died_at(lleech), key=phase_index)
            gone = mine[0] if mine else None
            theirs = (sorted(state.died_at(host), key=phase_index)
                      if host >= 0 else [])
            at = theirs[0] if theirs else None
            if at is not None and world.role_at(lleech, at) == "Lleech" \
                    and lleech in state.alive_set(at) \
                    and (gone is None
                         or phase_index(gone) >= phase_index(at)):
                if gone == at:
                    working.setdefault(int(at[1:]), set()).add(lleech)
                elif not _a_mastermind_keeps_the_lleech(world, state,
                                                        host, at):
                    failures[int(at[1:])].add(lleech)
            if gone is not None and world.role_at(lleech, gone) == "Lleech" \
                    and (at is None or phase_index(gone) < phase_index(at)):
                failures[int(gone[1:])].add(lleech)

    # A day with votes on the board was voted with eyes open, so no Organ
    # Grinder was working then: dead, not in play, or drunk — by its own
    # choice, which costs nothing, or by anything else (10.10.2026).
    if _in_bag(state, "OrganGrinder"):
        for day, voters in (state.votes or {}).items():
            if not voters:
                continue
            phase = f"D{day}"
            grinder = world.find_at("OrganGrinder", phase)
            if grinder is not None and grinder in state.alive_set(phase):
                failures[day].add(grinder)

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
    # Once per game for each Professor — the holder, a Philosopher that
    # took it — and again for one raised since (a new instance, ruling of
    # 03.10.2026). In the order they happened (13.10.2026).
    used = {}
    raises = sorted((int(phase[1:]), seat, phase)
                    for seat, phases in (state.resurrections or {}).items()
                    for phase in phases if phase[1:].isdigit())
    for night, seat, phase in raises:
        # A dead player the Al-Hadikhia chose, who chose life: back, and
        # the Al-Hadikhia was working (21.10.2026).
        if _in_bag(state, "AlHadikhia") \
                and seat in al_hadikhia_chosen(state, night):
            # Asked at its turn (Hatter stage 3c): a party later that
            # night may have made it something else.
            with _turn_of("AlHadikhia", night):
                ah = holding_now(world, state, "AlHadikhia", phase)
                held = ah is not None \
                    and world.role_at(ah, phase) == "AlHadikhia"
            if held and ah in state.alive_set(phase):
                working.setdefault(night, set()).add(ah)
                continue
        # At its turn: a Shabaloth that regurgitated and then chose
        # another Demon at a party later that night (gate, seed 2897).
        with _turn_of("Shabaloth", night):
            shabaloth = (holding_now(world, state, "Shabaloth", phase)
                         if _in_bag(state, "Shabaloth") else None)
        if shabaloth is not None and night >= 3 \
                and shabaloth in state.alive_set(phase):
            continue                  # it could have; nothing demanded
        # The holder, or a Philosopher that took it — the one that
        # drunk the holder ahead of it (13.10.2026).
        back = _returned_at(state, phase)
        # And a Demon the Boffin gave it (stage 2, 27.10.2026).
        with _turn_of("Professor", night):
            prof = next((who for who in sorted(state.philosophies() or {})
                         if who in state.alive_set(phase) and who != seat
                         and who not in back
                         and took_it(world, state, who, "Professor", phase)),
                        world.find_at("Professor", phase))
            if prof is None:
                prof = next((who for who in boffin_holders(
                    world, state, "Professor", phase)
                    if who != seat and who not in back), None)
        if prof is None or not _on_board(state, "Professor"):
            return None, None, 1.0, None
        if prof not in state.alive_set(phase) or night < 2:
            return None, None, 1.0, None
        raised = world.role_at(seat, phase)
        if TEAM[raised] != "townsfolk" \
                and "townsfolk" not in CHARACTERS[raised].registers:
            return None, None, 1.0, None
        working.setdefault(night, set()).add(prof)
        if prof in used and not any(
                used[prof] < int(at[1:]) <= night
                for at in (state.resurrections or {}).get(prof, ())
                if at[1:].isdigit()):
            return None, None, 1.0, None  # once per game
        used[prof] = night

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

    if _a_zealot_kept_its_hand_down(world, state):
        return None, None, 1.0, None      # a Zealot that did not vote

    if _in_bag(state, "Leviathan"):
        _leviathan_demands(world, state, failures, either)

    # A player a Mezepheles turned: it was working that night — unless
    # something later that night may have reached it, which the plan
    # could not tell from its not having worked at all.
    for change in getattr(world, "changes", ()):
        if not isinstance(change, MezephelesTurn):
            continue
        night = int(change.phase[1:])
        mez = world.find_at("Mezepheles", _before(night, change.phase))
        if mez is None:
            return None, None, 1.0, None
        if not _acted_before_the_demon_only(world, state, night):
            working.setdefault(night, set()).add(mez)

    spent = _spent_nominations(state)
    # Each row read at its character's turn of its night, attribution
    # included (Hatter stage 3b, E Weg 1): who held the character when
    # it acted, and whether it worked then. See `worlds._row_slot`.
    was_reading = READ_AT[0]
    try:
        for idx, (info, src) in enumerate(zip(state.infos, _source_seats(state))):
            READ_AT[0] = _row_slot(info) or was_reading
            if idx in spent:
                outcome[idx] = SPENT
                continue                      # the Virgin was already used up
            # Shown Lil' Monsta: true of whoever babysat that night, and made
            # up by anybody else (21.10.2026, C, Weg 1).
            if isinstance(info, LilMonstaBabysat):
                if info.holds(world, state, None):
                    outcome[idx] = HELD
                else:
                    invented *= invention_cost(info)
                    outcome[idx] = INVENTED
                continue
            if info.hard():
                if not info.holds(world, state, None):
                    return None, None, 1.0, None   # this cannot have happened
                outcome[idx] = HELD
                # A fact can lean on somebody too: a Banshee announced was a
                # Banshee whose ability worked that night — or the Boffin
                # behind a Demon it gave that ability (26.10.2026).
                for who in info.leaned_on(world, state):
                    if info.source_role:
                        who = sober_seat(world, state, who, info.source_role,
                                         f"N{info.night}")
                    working.setdefault(info.night, set()).add(who)
                continue

            # Something that happened in front of everybody and is judged by
            # what the day did with it — a claim to be the Goblin, and the
            # town executing the claimant. Nobody is its source, so there is
            # nobody to have invented it: either the world has nothing to
            # explain, or somebody's ability has to have been off.
            if getattr(info, "event", False):
                failed = info.must_have_failed(world, state)
                for who in failed:
                    failures[info.night].add(who)
                outcome[idx] = EXCUSED if failed else HELD
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
                    seat = world.find_at(role, phase)
                # Nobody holds it, and the one who said it believes it does:
                # a Drunk with that token. Its own row, made up — not the
                # reading of a Philosopher that took the character, which
                # then had to have been off on a night nothing could reach it
                # (13.10.2026, a mixed game with a Philosopher-Knight).
                if seat is None and isinstance(info.player, int) \
                        and 0 <= info.player < len(world.believes) \
                        and world.believes[info.player] == role:
                    seat = info.player
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
            vortox = holding_now(world, state, "Vortox", phase)
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
            # A Pixie mad about this character: made up until its holder
            # dies, at no cost, and its own from the night after (11.10.2026).
            if held is ABSENT and seat is not None \
                    and (world.role_at(seat, phase) == "Pixie"
                         or took_it(world, state, seat, "Pixie", phase)) \
                    and _on_board(state, "Pixie"):
                got = _pixie_gain(world, state, seat)
                if got is not None and got[0] == role:
                    if got[1] is not None and info.night >= got[1]:
                        held = (INVERTED if vortoxed
                                and TEAM[role] == "townsfolk" else GENUINE)
                    else:
                        held = ARBITRARY
            # A Demon the Boffin gave this ability (26.10.2026): its own,
            # worked through the Boffin — and what it yields is weighed
            # like the character's own (G Weg 1). Whether it was working is
            # the Boffin's (`sober`, below).
            # On the first night "before it acted" is before the setup,
            # where no gift is marked yet: asked of the night itself.
            given_at = phase if info.night <= 1 else acted
            if held is ABSENT and seat is not None and role is not None \
                    and boffin_gift(world, state, seat, given_at) == role:
                held = (INVERTED if vortoxed and TEAM[role] == "townsfolk"
                        else GENUINE)
            sober = seat if seat is None \
                else sober_seat(world, state, seat, role, given_at)
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

            # A seat that was turned evil and knows it — the Bounty Hunter's
            # evil Townsfolk, a Mezepheles's catch — still has its ability
            # and is told the truth, and says what suits it. What holds is
            # taken as said; what does not was made up, at the price of any
            # made-up reading (11.10.2026).
            if knows_it_turned_evil(world, seat, phase):
                if isinstance(info, FortuneTeller) or held is INVERTED \
                        or info.holds(world, state, None, seat):
                    outcome[idx] = HELD
                else:
                    invented *= invention_cost(info)
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
            # A shot or a Virgin's nomination is not information either, but
            # what the town watched is still checked like any act: a missed
            # shot at the Demon under a Vortox wants the Slayer off (Stelle
            # 59, 14.10.2026).
            if held is INVERTED and not info.is_information(state) \
                    and getattr(info, "in_the_open", False):
                held = GENUINE
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
                # True every way an open side could be (Stelle 72).
                was_true = (all(info.is_true(view, state, seat)
                                for view in each_real_side(
                                    world, state, f"N{info.night}"))
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

            # The Lycanthrope's faux paw registers evil while it works, and
            # whether it worked is the plan's (11.10.2026). A row that asked
            # about the faux paw is tried both ways: holding only with it
            # evil asks the Lycanthrope to be working; holding only with it
            # as it is asks the Lycanthrope off — or the row's own source.
            ok = faux_need = None
            if not isinstance(info, FortuneTeller) \
                    and _faux_paw(state) is not None:
                state._faux_mode, state._faux_hit = "on", False
                ok = info.holds(world, state, None, seat)
                if state._faux_hit:
                    state._faux_mode = "off"
                    ok_off = info.holds(world, state, None, seat)
                    state._faux_mode = "on"
                    lyc = faux_paw_lycanthrope(world, state, phase,
                                               living=False)
                    if ok and not ok_off:
                        faux_need = ("working", lyc)
                    elif ok_off and not ok:
                        faux_need = ("impaired", lyc)
                state._faux_hit = False
            if ok is None and not isinstance(info, FortuneTeller):
                ok = info.holds(world, state, None, seat)
            # Or it holds with a Philosopher that took the Recluse read as the
            # Recluse: then that Philosopher was working (group 6, N).
            recluse_need = None
            if ok is False and not isinstance(info, FortuneTeller):
                for who in _philosopher_recluses(world, state, phase):
                    if info.holds(_AsRecluse(world, who), state, None, seat):
                        recluse_need = who
                        break
            # That, or its own source was off: either explains it.
            if recluse_need is not None and not witnessed:
                either.append((info.night, frozenset({sober}), frozenset(),
                               frozenset({recluse_need})))
                outcome[idx] = EXCUSED
                continue
            if recluse_need is not None:
                ok = True

            if faux_need is not None and faux_need[0] == "impaired" \
                    and not witnessed:
                either.append((info.night, frozenset({sober}),
                               frozenset({faux_need[1]}), frozenset()))
                outcome[idx] = EXCUSED
                continue

            if isinstance(info, FortuneTeller):
                # Whether it held depends on where the red herring was, which
                # is settled later. Left open until then.
                ft_infos.append((info, seat, idx, None))
            elif witnessed and not ok:
                # Nothing excuses it. A droisoned source does not tell the
                # other player something false — it tells them nothing, they
                # are never woken. So the words did not come from the game.
                invented *= invention_cost(info)
                outcome[idx] = INVENTED
            elif not ok:
                # Poison has to land on whoever the information came from -
                # poisoning the messenger changes nothing. Or on the Boffin
                # behind a Demon it gave the ability (26.10.2026).
                failures[info.night].add(sober)
                outcome[idx] = EXCUSED
            else:
                outcome[idx] = HELD
                if faux_need is not None and witnessed:
                    working.setdefault(info.night, set()).add(faux_need[1])
                elif faux_need is not None:
                    # Held only with the faux paw reading evil, so the
                    # Lycanthrope worked — or it did not, the reading was
                    # false, and its source was droisoned. One choice a night
                    # covers every such row: with the Lycanthrope off, all of
                    # their sources are (open item 57, 12.10.2026: a Xaan
                    # poisoned the Lycanthrope and the Noble alike, and only
                    # the first was asked).
                    faux_working.setdefault((info.night, faux_need[1]),
                                            set()).add(sober)
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
                if recluse_need is not None:
                    working.setdefault(info.night, set()).add(recluse_need)
                # And one that held only if somebody else was impaired or
                # working: a Chambermaid's count that turns on a Wraith, which
                # a drunk one does not wake (table ruling, 08.10.2026). Its
                # own source being off explains it just as well.
                instead = getattr(info, "instead", None)
                needs = instead(world, state, seat) if instead else None
                if needs is not None:
                    either.append((info.night, frozenset({sober}))
                                  + tuple(needs))
                    if needs[0]:
                        outcome[idx] = EXCUSED
    finally:
        READ_AT[0] = was_reading

    for (night, lyc), sources in sorted(faux_working.items()):
        either.append((night, frozenset(sources), frozenset(),
                       frozenset({lyc})))
    return failures, ft_infos, invented, working


def _yaggababble_at(world, state, phase):
    """The living Demon at this moment, if it is a Yaggababble."""
    demon = _demon_holding(world, phase, "Yaggababble")
    if demon is None or demon not in state.alive_set(phase):
        return None
    return demon


def _days_reached(state):
    """How many days the board has got to."""
    return (phase_index(state.final_phase()) + 1) // 2


def _all_executed(state, day):
    """Every seat executed that day, by any route the rules call one: the
    town's vote, a Virgin's nominator, a Cerenovus's madness."""
    out = []
    seat = state.executed_on(day)
    if seat is not None:
        out.append(seat)
    mad = (getattr(state, "madness_executions", None) or {}).get(day)
    if mad is not None and mad not in out:
        out.append(mad)
    for info in state.infos:
        if isinstance(info, VirginNomination) and info.triggered \
                and info.night == day and info.nominator not in out:
            out.append(info.nominator)
    return out


def _surely_good(world, state, seat, phase):
    """Good, with nothing open about it: a Goon may be on either side and
    a Cult Leader on whichever its neighbours allow."""
    role = world.role_at(seat, phase)
    if acts_as_cult_leader(world, state, seat, phase):
        return cult_sides(world, state, seat, phase) == {False}
    if side_open(world, state, seat, phase):
        return False
    return not world.evil_at(seat, phase)


def _who_nominated_the_executed(state, day):
    """The seat that nominated whoever the town executed that day, when
    the board can say: its own row, a Princess's or a Golem's naming the
    executed player, or a day with a single nominator."""
    hanged = state.executed_on(day)
    if hanged is None:
        return None
    for info in state.infos:
        if info.night != day:
            continue
        if isinstance(info, ExecutionNomination):
            return info.player
        if isinstance(info, (PrincessNominated, GolemNomination)) \
                and info.target == hanged:
            return info.player
    who = (state.nominations or {}).get(day) or ()
    if len(who) == 1:
        return next(iter(who))
    return None


def _leviathan_demands(world, state, failures, either):
    """What a game going on says about a Leviathan in this world.

    "If more than 1 good player is executed, evil wins. All players know
    you are in play. After day 5, evil wins." Every reading is the
    table's of 11.10.2026.

      * **Not announced**, it was drunk or poisoned on its first day (way
        2 of O, as for the Vizier). Announced is `LeviathanAnnounced`.
      * **A second good player executed**, and the game went on: it was
        not working that day. Executed is enough, dead of it or not, and
        a Virgin's nominator and a Cerenovus's madness count. Only while
        a Leviathan lives, and only players surely good.
      * **Past the end of day five**, the same.
      * **Its jinxes with the Soldier, the Innkeeper and the Exorcist**:
        "if the Leviathan nominates and executes" the Soldier, a player
        the Innkeeper guards or the one the Exorcist chose, good wins.
        So where the board says who nominated the executed player and
        the game went on, that nominator was no working Leviathan — or
        whoever stood behind the executed player was not working. The
        Monk's is the same jinx and is not here: nobody writes down whom
        a Monk guarded.
      * **With the Grandmother**: "if the Leviathan is in play and the
        Grandchild dies by execution, evil wins." The game went on, so
        one of the two was not working.

    The Banshee's, the Farmer's, the Ravenkeeper's, the Sage's and the
    King's jinxes live where those characters do.
    """
    if not _a_leviathan_is_told_of(world):
        return
    reached = _days_reached(state)
    first = None
    for day in range(1, reached + 1):
        seat = _leviathan_at(world, state, f"D{day}")
        if seat is not None:
            first = (day, seat)
            break
    if first is None:
        return
    if not any(isinstance(info, LeviathanAnnounced) for info in state.infos):
        failures[first[0]].add(first[1])

    good_gone = 0
    for day in range(first[0], reached + 1):
        phase = f"D{day}"
        lev = _leviathan_at(world, state, phase)
        if lev is None:
            continue
        on = went_on_after(state, day)
        for seat in _all_executed(state, day):
            if not _surely_good(world, state, seat, phase):
                continue
            good_gone += 1
            if good_gone >= 2 and on:
                failures[day].add(lev)
        if day >= 5 and on:
            failures[day].add(lev)
        if not on:
            continue

        hanged = state.executed_on(day)
        if hanged is not None and _who_nominated_the_executed(
                state, day) == lev:
            behind = []
            if _has_ability(world, state, hanged, "Soldier", phase):
                behind.append(hanged)
            night = f"N{day}"
            for info in state.infos:
                if info.night != day:
                    continue
                if isinstance(info, InnkeeperChoice) \
                        and hanged in (info.a, info.b) \
                        and _has_ability(world, state, info.player,
                                         "Innkeeper", night):
                    behind.append(info.player)
                elif isinstance(info, ExorcistChoice) \
                        and info.target == hanged \
                        and _has_ability(world, state, info.player,
                                         "Exorcist", night):
                    behind.append(info.player)
            for who in behind:
                either.append((day, frozenset({lev}), frozenset({who}),
                               frozenset()))

        dead = state.execution_death(day)
        if dead is not None and _in_bag(state, "Grandmother"):
            for info in state.infos:
                if isinstance(info, GrandmotherInfo) and info.target == dead \
                        and info.night <= day \
                        and info.player in state.alive_set(phase) \
                        and _has_ability(world, state, info.player,
                                         "Grandmother", phase):
                    either.append((day, frozenset({lev}),
                                   frozenset({info.player}), frozenset()))


def _a_mastermind_keeps_the_lleech(world, state, host, at):
    """Their jinx: "If the Mastermind is alive and the Lleech's host dies
    by execution, the Lleech lives but loses their ability" (11.10.2026)."""
    if at[:1] != "D" or not _in_bag(state, "Mastermind"):
        return False
    if state.execution_death(int(at[1:])) != host:
        return False
    mastermind = world.find_at("Mastermind", at)
    return mastermind is not None and mastermind in state.alive_set(at)


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
    seat = holding_now(world, state, "NoDashii", phase)
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
    then = holding_now(world, state, "NoDashii", began)
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
    if _demon_holding(world, first, "Vigormortis") is None:
        return False
    now = holding_now(world, state, "Vigormortis", phase)
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
    seat = holding_now(world, state, "Vigormortis", phase)
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
        if _demon_holding(world, first, "Vigormortis") is None:
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
        # Coming back tonight is the same span the other way round: a
        # real Professor raising its dead Philosopher was sober when it
        # chose, and drunk from the moment the Philosopher stood up.
        went = (not still) or any(at in state.died_at(who)
                                  for at in (phase, f"D{night}")) \
            or who in _returned_at(state, phase)
        # Every seat holding it: three Village Idiots are all drunk
        # (11.10.2026).
        at = began if not still else phase
        had = frozenset(p for p in range(state.n_players)
                        if p != who and world.role_at(p, at) == taken)
        if not had:
            continue                      # nobody else was holding it
        free = (lambda seat: 1.0) if went else 1.0
        out.append(impairment.Source("Philosopher", had,
                                     capacity=len(had), cost=free,
                                     repeat_cost=free, actor=who))
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
    seat = holding_now(world, state, "Pukka", phase)
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
    if not _in_bag(state, "Sweetheart") \
            and not taken_by_a_philosopher(state, "Sweetheart") \
            and not _boffin_on_board(state):
        return []
    # Whoever was the Sweetheart when they died — dealt one, or made one by
    # a Pit-Hag. Only the dealt one was looked for (29.09.2026). And a
    # Philosopher that took it; a real one a Philosopher had drunk when it
    # died leaves nobody drunk (way 1 of A and B, 13.10.2026).
    out = []
    for seat in range(state.n_players):
        gone = [p for p in state.died_at(seat)
                if falls_as(world, state, seat, "Sweetheart", p)]
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
    if not _on_board(state, "Sailor"):
        return []
    phase = f"N{night}"
    holders = _holders(world, state, "Sailor", phase)
    return [source for seat in holders
            for source in _a_sailors_drunk(world, state, night, seat,
                                           _by(holders, seat))]


def _a_sailors_drunk(world, state, night, seat, by):
    phase = f"N{night}"
    if seat not in state.alive_set(phase):
        return []
    # Whoever came back tonight was dead when its turn came — a Shabaloth
    # regurgitates at 27 and a Professor raises at 43, and the Sailor
    # chooses at 4. The same for the Innkeeper at 9 and the Exorcist at
    # 21: no choice, so nobody drunk and nobody guarded.
    if seat in _returned_at(state, phase):
        return []

    # Drunk itself, a Demon the Boffin gave the Sailor's ability makes
    # only that copy drunk — the Boffin's, since it has nothing else
    # (26.10.2026).
    me = sober_seat(world, state, seat, "Sailor", phase)

    def price(hit):
        if hit == me:
            return 0.6                    # the usual half of the coin
        return SAILOR_ON_EVIL_PENALTY if world.evil_at(hit, phase) else 0.6

    # It is one of two: the Sailor, or whoever it chose. Recorded, that
    # is a pair rather than the whole table — which is most of what
    # confirming a Sailor is worth.
    picked = _chosen(state, "Sailor", night, by=by)
    reach = (state.alive_set(phase) | {me} if picked is None
             else frozenset({me}) | picked)
    return [impairment.Source("Sailor", frozenset(reach), capacity=1,
                              cost=price, repeat_cost=price, actor=me)]


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
    if not _on_board(state, "Goon"):
        return []
    phase = f"N{night}"
    # The holder, and a Philosopher that took it (13.10.2026).
    return [source for goon in _holders(world, state, "Goon", phase)
            if goon in state.alive_set(phase)
            for source in _a_goons_chooser(world, state, night, goon)]


def _a_goons_chooser(world, state, night, goon):
    phase = f"N{night}"
    pickers = frozenset(
        seat for seat in state.alive_set(phase)
        if seat != goon and CHARACTERS[world.role_at(seat, phase)].chooses)
    # A Leviathan chooses a good player each night but the first where
    # its jinxes have it choose at all (`waking.LEVIATHAN_CHOOSES_FOR`),
    # and the Goon may be the one: found at the gate, a Leviathan drunk
    # for a day on which the game should have ended (11.10.2026).
    if night >= 2 and _in_bag(state, "Leviathan") \
            and any(_in_bag(state, key) for key in LEVIATHAN_CHOOSES_FOR):
        pickers |= frozenset(
            seat for seat in state.alive_set(phase)
            if seat != goon and world.role_at(seat, phase) == "Leviathan")
    # And a Courtier that named the Goon tonight. It names a character,
    # not a player — but the wiki's own Goon page has exactly this: "The
    # Courtier chooses the Goon. The Goon turns good, and the Courtier
    # becomes drunk" (table ruling, 08.10.2026: as the wiki has it).
    for info in state.infos:
        if isinstance(info, CourtierChoice) and info.night == night \
                and info.role == "Goon" and info.player != goon \
                and world.role_at(info.player, phase) == "Courtier" \
                and info.player in state.alive_set(phase):
            pickers |= {info.player}
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
        # The Courtier — or a Philosopher that took its ability, which
        # this never asked, so one that named somebody drunk nobody
        # (found in mixed games, 11.10.2026).
        courtier = info.player
        if not _has_ability(world, state, courtier, "Courtier", phase):
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
        # Everybody holding it: three Village Idiots are all drunk.
        hit = frozenset(p for p in range(state.n_players)
                        if world.role_at(p, phase) == info.role)
        if not hit:
            continue                      # named somebody nobody is
        # In the span the Courtier dies, the named one is drunk for part
        # of it and sober for the rest — and a night and its day are one
        # key here. So there it is on offer rather than forced: free to
        # explain something that went wrong, and no bar to something
        # that worked.
        went = any(at in state.died_at(courtier)
                   for at in (phase, f"D{night}"))
        # Named the Goon, it may have been the first to choose it — then
        # the Courtier was drunk on the spot and nothing happened to the
        # Goon. Whether it was first nobody writes down, so on offer.
        went = went or info.role == "Goon"
        free = (lambda who: 1.0) if went else 1.0
        out.append(impairment.Source(
            "Courtier", hit, capacity=len(hit), cost=free, repeat_cost=free,
            actor=sober_seat(world, state, courtier, "Courtier", phase)))
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
    if not _on_board(state, "Minstrel"):
        return []
    phase = f"N{night}"
    # The holder, and a Philosopher that took it (13.10.2026).
    return [source for seat in _holders(world, state, "Minstrel", phase)
            for source in _a_minstrels_song(world, state, night, seat)]


def _a_minstrels_song(world, state, night, seat):
    phase = f"N{night}"
    if seat not in state.alive_set(phase):
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
                              cost=1.0, repeat_cost=1.0,
                              actor=sober_seat(world, state, seat,
                                               "Minstrel", phase))]


@impairment.source_rule
def an_organ_grinder_may_drink(world, state, night):
    """ "Each night, choose if you are drunk until dusk." Itself and
    nobody else, and its own choice, so it costs nothing and is never
    forced (10.10.2026). A Mathematician does not count it: nothing else
    did it (`info._possible_impairment_counts`)."""
    if not _in_bag(state, "OrganGrinder"):
        return []
    phase = f"N{night}"
    seat = world.find_at("OrganGrinder", phase)
    if seat is None or seat not in state.alive_set(phase):
        return []
    return [impairment.Source(impairment.ORGAN_GRINDER_BY_CHOICE, frozenset({seat}),
                              capacity=1, cost=lambda who: 1.0,
                              repeat_cost=lambda who: 1.0)]


@impairment.source_rule
def a_widow_poisons_one(world, state, night):
    """ "On your 1st night, look at the Grimoire & choose a player: they
    are poisoned." Anybody, itself included, for as long as it lives —
    resting while it is drunk or poisoned itself (10.10.2026). Its own
    choice, so free and never forced. One seat for the whole game is not
    held to here: the plan may land it differently on different nights,
    which keeps worlds rather than losing them, as with the Sweetheart."""
    if not _in_bag(state, "Widow"):
        return []
    phase = f"N{night}"
    seat = world.find_at("Widow", phase)
    if seat is None or not minion_still_acts(world, state, seat, phase):
        return []
    free = lambda who: 1.0
    return [impairment.Source("Widow", frozenset(range(state.n_players)),
                              capacity=1, cost=free, repeat_cost=free,
                              actor=seat)]


@impairment.source_rule
def a_preacher_silences_its_minions(world, state, night):
    """ "All chosen Minions have no ability." A Minion the Preacher chose
    while it worked, from that night on — it acts before every Minion —
    for as long as the Preacher lives and works (10.10.2026). Forced, not
    on offer: a Minion it silenced cannot have acted. Resting while the
    Preacher is drunk or poisoned is `plan_night_resting`; a Preacher
    that was off when it chose is the other story in `_impairment_plan`.
    """
    if not _on_board(state, "Preacher"):
        return []
    phase = f"N{night}"
    # The holder, and a Philosopher that took it (13.10.2026).
    return [source for preacher in _holders(world, state, "Preacher", phase)
            if preacher in state.alive_set(phase)
            for source in _a_preachers_sermons(world, state, night,
                                               preacher)]


def _a_preachers_sermons(world, state, night, preacher):
    phase = f"N{night}"
    hit = set()
    for info in state.infos:
        if not isinstance(info, PreacherChoice) or info.player != preacher \
                or info.night > night:
            continue
        if not _has_ability(world, state, preacher, "Preacher",
                            f"N{info.night}"):
            continue
        # An ability ends with the death of whoever has it.
        if _died_between(state, preacher, info.night, night):
            continue
        target = info.target
        if world.team_at(target, f"N{info.night}") == "minion" \
                and world.team_at(target, phase) == "minion":
            hit.add(target)
    if not hit:
        return []
    # On the night or day it dies, silenced for part of the span and not
    # for the rest — and a night and its day are one key here. So there it
    # is on offer rather than forced, as for the Courtier.
    went = any(at in state.died_at(preacher) for at in (phase, f"D{night}"))
    cost = (lambda who: 1.0) if went else 1.0
    return [impairment.Source("Preacher", frozenset(hit), capacity=len(hit),
                              cost=cost, repeat_cost=cost,
                              actor=sober_seat(world, state, preacher,
                                               "Preacher", phase))]


@impairment.source_rule
def a_puzzlemaster_keeps_one_drunk(world, state, night):
    """ "1 player is drunk, even if you die." Whoever the Storyteller
    likes, evil too, for the whole game (10.10.2026). Free and never
    forced; one seat all game is not held to, as with the Sweetheart."""
    if not _on_board(state, "Puzzlemaster"):
        return []
    # One drunk for the one dealt, and one for each Philosopher that took
    # it by tonight (13.10.2026).
    phase = f"N{night}"
    many = (1 if "Puzzlemaster" in dealt_roles(world) else 0) + sum(
        1 for who in (state.philosophies() or {})
        if took_it(world, state, who, "Puzzlemaster", phase)) + len(
        boffin_holders(world, state, "Puzzlemaster", phase))
    if not many:
        return []                         # dealt, or nobody is drunk of it
    free = lambda who: 1.0
    return [impairment.Source("Puzzlemaster",
                              frozenset(range(state.n_players)),
                              capacity=many, cost=free, repeat_cost=free)]


@impairment.source_rule
def a_xaan_poisons_the_town(world, state, night):
    """ "On night X, all Townsfolk are poisoned until dusk. [X Outsiders]"
    X is the Outsiders dealt, whatever happened since. Every Townsfolk,
    forced, if the Xaan lives then and works (10.10.2026) — the
    Mathematician among them, who is told anything at all."""
    if not _in_bag(state, "Xaan"):
        return []
    phase = f"N{night}"
    xaan = world.find_at("Xaan", phase)
    if xaan is None or not minion_still_acts(world, state, xaan, phase):
        return []
    x = sum(1 for role in world.roles if TEAM[role] == "outsider")
    if night != x:
        return []
    town = frozenset(p for p in range(state.n_players)
                     if world.team_at(p, phase) == "townsfolk")
    if not town:
        return []
    went = any(at in state.died_at(xaan) for at in (phase, f"D{night}"))
    cost = (lambda who: 1.0) if went else 1.0
    return [impairment.Source("Xaan", town, capacity=len(town), cost=cost,
                              repeat_cost=cost, actor=xaan)]


@impairment.source_rule
def a_village_idiot_is_drunk(world, state, night):
    """ "[+0 to +2 Village Idiots. 1 of the extras is drunk]" With two or
    three dealt, one of them is drunk all game, and which is the
    Storyteller's (11.10.2026). Free; one seat all game is not held to,
    as with the Puzzlemaster's."""
    if not _in_bag(state, "VillageIdiot"):
        return []
    # Dealt, or held by a Summoner's Marionette-to-be (22.10.2026).
    idiots = frozenset(p for p, role in enumerate(dealt_roles(world))
                       if role == "VillageIdiot")
    if len(idiots) < 2:
        return []
    return [impairment.Source("Village Idiot", idiots, capacity=1,
                              cost=1.0, repeat_cost=1.0)]


@impairment.source_rule
def a_lleech_poisons_its_host(world, state, night):
    """ "You start by choosing a player: they are poisoned." For as long
    as the Lleech lives, resting while it is drunk or poisoned itself
    (table ruling, 11.10.2026; `impairment.RESTING`). The host is the
    hidden choice of this telling (`_hidden_choices`): a seat, forced —
    or -1, somebody who never died, who may then be anybody alive."""
    if not _in_bag(state, "Lleech"):
        return []
    phase = f"N{night}"
    # The living one: a dealt Lleech that died still holds the character
    # beside the Scarlet Woman who took it on.
    holder = next((p for p in range(state.n_players)
                   if p in state.alive_set(phase)
                   and world.role_at(p, phase) == "Lleech"), None)
    if holder is None:
        return []
    dealt = world.find("Lleech")
    host = _lleech_host(state)
    if holder == dealt and host is not None and host >= 0:
        if host not in state.alive_set(phase):
            return []
        return [impairment.Source("Lleech", frozenset({host}), capacity=1,
                                  cost=1.0, repeat_cost=1.0, actor=holder)]
    # Somebody who never died — or the host of a Lleech made later, a
    # Scarlet Woman's or a Pit-Hag's, which "must choose an alive player"
    # that night and is not followed further.
    reach = frozenset(p for p in state.alive_set(phase) if p != holder)
    free = lambda who: 1.0
    return [impairment.Source("Lleech", reach, capacity=1, cost=free,
                              repeat_cost=free, actor=holder)]


# A Pixie that did not get the ability it was mad about. Named so the
# Mathematician can leave it out: nobody's ability went wrong.
PIXIE_NOT_GRANTED = "Pixie, not granted"


def _is_pixie(world, state, seat):
    """Dealt the Pixie, or a Philosopher that took it on night one: it
    starts knowing from the night of taking (ruling C, 13.10.2026)."""
    if world.roles[seat] == "Pixie":
        return True
    taken = (state.philosophies() or {}).get(seat)
    return bool(taken and taken[0] == "Pixie"
                and world.roles[seat] == "Philosopher")


def _pixie_gain(world, state, seat):
    """(the Townsfolk, the first night it works as one) for a dealt Pixie
    mad about it, or None. The night is None while its holder lives.

    "If you were mad that you were this character, you gain their ability
    when they die." Madness is the claim (table ruling, 11.10.2026); the
    character is the one its own row names, or else the one it claims.
    From the night after the holder died, if the Pixie was alive then.
    """
    if not _is_pixie(world, state, seat):
        return None
    claim = state.claims.get(seat)
    learned = None
    for info in state.infos:
        if isinstance(info, PixieLearned) and info.player == seat:
            learned = info.role
            break
    learned = learned or claim
    if not learned or claim != learned or learned == "Pixie" \
            or TEAM.get(learned) != "townsfolk":
        return None
    holder = next((p for p in range(state.n_players)
                   if p != seat and world.role_at(p, "N1") == learned),
                  None)
    if holder is None:
        return (learned, None)
    gone = sorted(state.died_at(holder), key=phase_index)
    if not gone:
        return (learned, None)
    first = gone[0]
    if seat not in state.alive_set(first):
        return (learned, None)
    return (learned, int(first[1:]) + 1)


def _mad_pixie(world, state, seat):
    """Is this seat a Pixie claiming the Townsfolk it was shown?

    Its madness, which costs a world nothing (11.10.2026). Without its
    own row the claim has to be a Townsfolk somebody else holds — or one
    a Spy could have been shown as.
    """
    if not _is_pixie(world, state, seat):
        return False
    claim = state.claims.get(seat)
    if not claim or TEAM.get(claim) != "townsfolk":
        return False
    for info in state.infos:
        if isinstance(info, PixieLearned) and info.player == seat:
            return info.role == claim
    return any(p != seat and registers_as_role(world.roles[p], claim)
               for p in range(state.n_players))


@impairment.source_rule
def a_pixie_may_be_denied(world, state, night):
    """A Pixie the Storyteller judged not mad enough has no ability, and
    may say what it likes. On offer from the night it would have started,
    and it costs (`PIXIE_DENIED_PENALTY`)."""
    if not _on_board(state, "Pixie"):
        return []
    out = []
    for seat in range(len(world.roles)):
        if not _is_pixie(world, state, seat):
            continue
        got = _pixie_gain(world, state, seat)
        if got is None or got[1] is None or night < got[1]:
            continue
        out.append(impairment.Source(PIXIE_NOT_GRANTED, frozenset({seat}),
                                     capacity=1, cost=PIXIE_DENIED_PENALTY,
                                     repeat_cost=1.0))
    return out


@impairment.source_rule
def an_innkeeper_drunks_one_of_the_two_it_guards(world, state, night):
    """One of the pair it protected, and it does not choose which.

    Lasts the night and the day after, which needs no special handling:
    a night and the day that follows it share one span already, because
    poison works the same way.
    """
    if not _on_board(state, "Innkeeper"):
        return []
    phase = f"N{night}"
    holders = _holders(world, state, "Innkeeper", phase)
    return [source for seat in holders
            for source in _an_innkeepers_drunk(world, state, night, seat,
                                               _by(holders, seat))]


def _an_innkeepers_drunk(world, state, night, seat, by):
    phase = f"N{night}"
    if night < 2 or seat not in state.alive_set(phase):
        return []
    if seat in _returned_at(state, phase):
        return []                         # back tonight, after its turn
    # One of the two it protected, and it does not choose which — so a
    # recorded choice narrows the drunk from the table to a pair.
    picked = _chosen(state, "Innkeeper", night, ("a", "b"), by=by)
    reach = state.alive_set(phase) if picked is None else picked
    # A Demon the Boffin gave it that guards itself: the drunk one is its
    # copy, which is the Boffin's (26.10.2026).
    me = sober_seat(world, state, seat, "Innkeeper", phase)
    if me != seat and seat in reach:
        reach = (frozenset(reach) - {seat}) | {me}
    return [impairment.Source("Innkeeper", frozenset(reach),
                              capacity=1, cost=0.5, repeat_cost=0.5,
                              actor=me)]


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
        # And a Philosopher that gained nothing has nothing of the
        # character it named to act with: its own Sailor cannot be what
        # made it drunk (13.10.2026).
        mine = (holder, info.role) if source == "Philosopher" else None
        got = _plan_as_given(world, state, again, forbidden,
                             without=(source,), mine=mine)
        if got is not None:
            return got
    # And a Preacher that was drunk or poisoned when it chose silenced
    # nobody (10.10.2026). Set aside whole, which keeps worlds.
    for info in state.infos:
        if not isinstance(info, PreacherChoice):
            continue
        if not _has_ability(world, state, info.player, "Preacher",
                            f"N{info.night}"):
            continue
        again = {night: set(seats) for night, seats in failures.items()}
        again.setdefault(info.night, set()).add(info.player)
        got = _plan_as_given(world, state, again, forbidden,
                             without=("Preacher",))
        if got is not None:
            return got
    return None


def _plan_as_given(world, state, failures, forbidden, without=(), mine=None):
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
        if mine is not None:
            sources = [s for s in sources
                       if (s.actor, s.name) != mine]
        got = impairment.plan_night_resting(
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
    return f"B{night - 1}" if night > 1 else "N0"


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
    # Whose side is asked about is only written down where a story can
    # differ in who turned evil (`_explain_or_recall`).
    listen_for_sides(_in_bag(state, "BountyHunter")
                     or _in_bag(state, "Mezepheles"))
    state._final_phase_held = state._night_deaths_held = None
    state._final_phase_held = state.final_phase()
    state._night_deaths_held = _night_deaths(state)
    try:
        return _best_story(world, state, outcome, viable)
    finally:
        state._final_phase_held = state._night_deaths_held = None


def _best_story(world, state, outcome, viable):
    if _in_bag(state, "LilMonsta") and lil_monsta_world(world):
        return _best_babysat_story(world, state, outcome, viable)
    if _in_bag(state, "Summoner") and summoner_world(world):
        return _best_summoned_story(world, state, outcome, viable)
    return _best_story_told(world, state, outcome, viable)


# Measured both ways on the gate: a telling that failed without asking
# about anything from the summoning on fails for every summoning.
SUMMON_PRUNE = True


def _best_summoned_story(world, state, outcome, viable):
    """The Summoner's Demon, told one way at a time (A, Weg 1, 21.10.2026).

    Each way is a whole story: who it made the Demon and which Demon, or
    that none came. Every way that fits is kept for the report, because
    who is the Demon now is the question the table is asking — so this
    stops early only when nothing is listening for the shares. A telling
    that failed before anything from the summoning on was looked at fails
    for every way, and the world is done (`worlds.SUMMON_READS`).
    """
    options = summon_options(world, state)
    if not options:
        return None, ()
    best = (None, (), None)
    for fixed in options:
        state._summoned = fixed
        SUMMON_READS[0] = [False]
        try:
            marks = {} if outcome is not None else None
            fits = [] if viable is not None else None
            cost, changes = _best_story_told(world, state, marks, fits)
        finally:
            state._summoned = None
            read = SUMMON_READS[0][0]
            SUMMON_READS[0] = None
        if viable is not None and fits:
            viable.extend(fits)
        if cost is not None and (best[0] is None or cost > best[0]):
            best = (cost, changes, marks)
            if viable is None and cost >= 1.0:
                break                     # nothing explains it better
        if cost is None and SUMMON_PRUNE and not read \
                and any(isinstance(c, Summoned) for c in fixed):
            break                         # failed before it mattered
    if outcome is not None and best[2]:
        outcome.update(best[2])
    return best[0], best[1]


def _best_babysat_story(world, state, outcome, viable):
    """Lil' Monsta's babysitters, one a night (A, Weg 1, 21.10.2026).

    Every combination is too many to tell: a few seats a night over four
    nights, times whatever else the story may hold. So the stand-ins are
    told first — the seat nothing asks about, each night — and then one
    night at a time is tried with each of its other seats, keeping what
    explains the board better, until nothing improves. A night's
    babysitter is read by that night, the day after and the start of the
    next, so the nights hardly lean on each other.
    """
    options = babysitter_options(world, state)
    if not options or any(not got for got in options):
        return None, ()
    tried = {}
    # Tellings that fitted nothing, with the nights they asked about: one
    # that differs from them only on other nights fails the same, and is
    # not told (the shortcut `_explain_or_recall` takes for sides).
    failed = []
    # A babysitter dead or on the gallows in its span is always asked
    # about: what followed is part of the story.
    marked = []
    for night, seats in enumerate(options):
        span = (phase_index(f"N{night + 1}"), phase_index(f"D{night + 1}"))
        marked.append({p for p in seats
                       if state.executed_on(night + 1) == p
                       or any(span[0] <= phase_index(at) <= span[1]
                              for at in state.died_at(p))})

    def tell(fixed):
        if fixed in tried:
            return tried[fixed]
        for before, asked in failed:
            if all(fixed[k] == before[k] if k in asked
                   else fixed[k] not in marked[k]
                   for k in range(len(fixed))):
                tried[fixed] = (None, (), None, None)
                return tried[fixed]
        state._babysitters = fixed
        reads = BABYSAT_READS[0] = set()
        try:
            marks = {} if outcome is not None else None
            fits = [] if viable is not None else None
            cost, changes = _best_story_told(world, state, marks, fits)
        finally:
            state._babysitters = None
            BABYSAT_READS[0] = None
        if cost is None:
            asked = {int(at[1:]) - 1 for at in reads if at[:1] == "N"}
            asked |= {k for k, seat in enumerate(fixed)
                      if k < len(marked) and seat in marked[k]}
            failed.append((fixed, asked))
        tried[fixed] = (cost, changes, marks, fits)
        return tried[fixed]

    fixed = tuple(got[0] for got in options)
    best = tell(fixed)
    # Few enough to tell them all: then every one is.
    size = 1
    for got in options:
        size *= len(got)
    if size <= BABYSITTERS_TOLD_IN_FULL:
        for trial in itertools.product(*options):
            if best[0] is not None and best[0] >= 1.0:
                break
            got = tell(tuple(trial))
            if got[0] is not None and (best[0] is None or got[0] > best[0]):
                best, fixed = got, tuple(trial)
        options = []                      # nothing left to try
    # Where to start: the stand-ins, and — the Minions mostly keep it —
    # each seat babysitting every night it can.
    seen = []
    for got in options:
        seen += [p for p in got if p not in seen]
    for seat in seen:
        if best[0] is not None and best[0] >= 1.0:
            break
        trial = tuple(seat if seat in got else got[0] for got in options)
        got = tell(trial)
        if got[0] is not None and (best[0] is None or got[0] > best[0]):
            best, fixed = got, trial
    # Nothing fitted yet: one night changed from any of the starts.
    if best[0] is None:
        for start in list(tried):
            for night, seats in enumerate(options):
                for seat in seats:
                    trial = start[:night] + (seat,) + start[night + 1:]
                    got = tell(trial)
                    if got[0] is not None and (best[0] is None
                                               or got[0] > best[0]):
                        best, fixed = got, trial
            if best[0] is not None:
                break
    for _round in range(3):
        better = False
        for night, seats in enumerate(options):
            if best[0] is not None and best[0] >= 1.0:
                break
            for seat in seats:
                if seat == fixed[night]:
                    continue
                trial = fixed[:night] + (seat,) + fixed[night + 1:]
                got = tell(trial)
                if got[0] is not None and (best[0] is None
                                           or got[0] > best[0]):
                    best, fixed, better = got, trial, True
        if not better:
            break
    if viable is not None:
        for _cost, _changes, _marks, fits in tried.values():
            viable.extend(fits or ())
    if outcome is not None and best[2]:
        outcome.update(best[2])
    return best[0], best[1]


def _best_story_told(world, state, outcome, viable):
    stories = possible_timelines(world, state)
    if not stories:
        return None, ()
    turning = _in_bag(state, "Mezepheles")
    if stories == [((), 1.0)] and not turning:
        cost = _explain(world, state, outcome)
        if viable is not None and cost is not None:
            viable.append((cost, ()))
        return cost, ()

    best, best_changes, best_marks = None, (), None
    # Stories that differ only in who turned evil, kept with what was
    # asked while each was explained (`_explain_or_recall`).
    told_before = {}
    # A tea party (22.10.2026): the stories where nobody chose anything
    # new go first. One that could not be explained, and never looked at
    # anything from the earliest party on, cannot be with any choice made
    # there: the choices change nothing it looked at, and ask one thing
    # more — a Hatter that was working. `tea` holds those stories.
    tea = None
    if TEA_PRUNE and _tea_on_board(state):
        parties = [moment_of(c) for got, _w in stories
                   for c in got if isinstance(c, TeaParty)]
        if parties:
            tea = (min(parties), set())
    # And a Summoner chosen at a party (Hatter stage 2, 25.10.2026): the
    # stories where it summoned nobody go before those where it did. One
    # that could not be explained without looking at anything — sides too
    # — from the earliest summoning on cannot be with any summoning that
    # shares what came before: that changes nothing it looked at.
    summ = None
    if SUMMON_TEA_PRUNE and tea is not None \
            and "Summoner" in state.script.keys:
        made = [moment_of(c) for got, _w in stories
                for c in got if isinstance(c, Summoned)]
        if made:
            summ = (min(made), set())
    if tea is not None:
        def _order(got):
            party = any(isinstance(c, TeaParty) for c in got[0])
            return (party, party and any(isinstance(c, Summoned)
                                         for c in got[0]))
        stories = sorted(stories, key=_order)
    for changes, weight in stories:
        plain = None
        before = None
        if tea is not None:
            rest = tuple(c for c in changes if not isinstance(c, TeaParty))
            if rest != changes:
                if rest in tea[1] and not CHECK_RECALLS:
                    STORIES["skipped"] += 1
                    continue
                if summ is not None:
                    before = tuple(c for c in changes
                                   if moment_of(c) < summ[0])
                    if before in summ[1] and not CHECK_RECALLS:
                        STORIES["skipped"] += 1
                        continue
                TEA_TOLD[0] += 1
            else:
                plain = rest
        told = [(changes, weight)]
        # What the Boffin gave each new Demon in this story (C, D and I),
        # told here one at a time rather than as stories of their own:
        # beside a tea party, an Engineer and a Summoner they multiplied
        # the stories past what memory holds (gate, 26.10.2026, seed 444).
        if _boffin_on_board(state):
            view = Timeline(world, changes) if changes else world
            ways = boffin_new_demon_stories(view, state)
            if not ways:
                continue                  # nothing it could have given
            if ways != [((), 1.0)]:
                told = [(changes + extra, weight * c) for extra, c in ways]
        at = 0
        while at < len(told):
            changes, weight = told[at]
            at += 1
            watch = at == 1 and (plain is not None or before is not None)
            if watch:
                TEA_READS[0] = ([tea[0], False] if plain is not None
                                else [summ[0], False, "sides"])
                fresh = STORIES["explained"]
            try:
                cost, marks, asked = _explain_or_recall(
                    world, changes, state, outcome is not None, told_before)
            finally:
                if watch:
                    looked = TEA_READS[0][1]
                    TEA_READS[0] = None
            # Only a story really told here says what it looked at; one
            # recalled from another (`_explain_or_recall`) does not.
            if watch and cost is None \
                    and not looked and (not _LISTENING[0]
                                        or STORIES["explained"] > fresh):
                if plain is not None:
                    tea[1].add(plain)
                else:
                    summ[1].add(before)
            # A story that leaves something to pay for, or does not fit
            # at all, is told again with each player a Mezepheles could
            # have turned (`a_mezepheles_may_have_turned`).
            if turning and at == 1 and (cost is None or cost < 1.0):
                view = Timeline(world, changes) if changes else world
                for turn in a_mezepheles_may_have_turned(view, state):
                    # Not if the story could not be explained and never
                    # asked about that player's side from that night on:
                    # the second shortcut of `_explain_or_recall`, taken
                    # here before the story is even put together.
                    if cost is None and not CHECK_RECALLS and not (
                            asked.get(turn[0].seat, 0)
                            >> (phase_index(turn[0].phase) + 2)):
                        STORIES["skipped"] += 1
                        continue
                    told.append((changes + turn, weight))
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


# Counted for the measurement scripts: stories explained, stories whose
# cost was recalled from one that differs only in who turned evil, and
# turns skipped because the story without them already could not be.
STORIES = {"explained": 0, "recalled": 0, "skipped": 0}
# Set by the tests: explain the recalled ones anyway and compare.
CHECK_RECALLS = False


_NOBODY_ASKED = {}


def _who_turned(changes):
    """A story taken apart: {seat: from which moment it is evil}, the
    nights a Mezepheles turned somebody, and every other change."""
    if not changes:
        return {}, (), ()
    flips, turns, rest = {}, [], []
    for change in changes:
        if isinstance(change, TurnedEvil):
            at = phase_index(change.phase)
            flips[change.seat] = min(at, flips.get(change.seat, at))
            if isinstance(change, MezephelesTurn):
                turns.append(change.phase)
        else:
            rest.append(change)
    return flips, tuple(turns), tuple(rest)


def _differ_only_unasked(flips, others, reads):
    """Do two stories differ only where nobody looked?

    Each seat is evil from some moment on in one story and from another
    (or never) in the other. Between those two moments the stories
    disagree about its side; if the explanation of one never asked about
    that seat in between, it went exactly as the other's would.
    """
    for seat in flips.keys() | others.keys():
        mine, theirs = flips.get(seat), others.get(seat)
        if mine == theirs:
            continue
        if mine is None or theirs is None:
            first, last = (theirs if mine is None else mine), None
        else:
            first, last = min(mine, theirs), max(mine, theirs)
        asked = reads.get(seat, 0) >> (first + 2)
        if last is not None:
            asked &= (1 << (last - first)) - 1
        if asked:
            return False
    return True


def _explain_or_recall(world, changes, state, with_marks, told_before):
    """`_explain`, unless a story told before settles this one.

    With a Bounty Hunter dealt every world is told once for each
    Townsfolk that may be the evil one, and beside a Mezepheles once more
    for each player and night it could have turned somebody. Most of
    those differ in a seat nothing on the board asks about, and explaining
    them one by one was nearly all the time such a board took (measured
    11.10.2026, open item 52). Two shortcuts, and neither changes an
    answer:

      * **Recalled.** A story with the same changes otherwise and the
        same night of turning, differing only in seats whose side was
        never asked about while the first was explained, costs the same.
      * **Skipped.** A story that could not be explained cannot be once a
        Mezepheles turns somebody whose side was never asked about from
        that night on: the turn changes nothing that was looked at, and
        asks one thing more — that the Mezepheles was working.
    """
    if not _LISTENING[0]:                 # nobody turns evil that way here
        marks = {} if with_marks else None
        view = Timeline(world, changes) if changes else world
        return _explain(view, state, marks), marks, _NOBODY_ASKED
    flips, turns, rest = _who_turned(changes)
    before = told_before.setdefault(rest, [])
    found = None
    for theirs, their_turns, reads, cost, marks in before:
        if their_turns == turns:
            if _differ_only_unasked(flips, theirs, reads):
                found = ("recalled", cost, marks)
                break
        elif cost is None and not their_turns and len(turns) == 1 \
                and _differ_only_unasked(flips, theirs, reads):
            found = ("skipped", None, None)
            break
    if found is not None and not CHECK_RECALLS:
        STORIES[found[0]] += 1
        return found[1], (dict(found[2]) if with_marks and found[2] else
                          ({} if with_marks else None)), reads
    marks = {} if with_marks else None
    view = Timeline(world, changes) if changes else world
    begin_reads()
    try:
        cost = _explain(view, state, marks)
    finally:
        reads = end_reads()
    STORIES["explained"] += 1
    if found is not None:                 # CHECK_RECALLS
        same = (cost is None) == (found[1] is None) and (
            cost is None or abs(cost - found[1]) < 1e-12)
        if found[0] == "recalled":
            same = same and (not with_marks or marks == (found[2] or {}))
        if not same:
            raise AssertionError(
                f"{found[0]} {found[1]} but explained {cost}: "
                f"{view.roles} {changes}")
    before.append((flips, turns, reads, cost, marks))
    return cost, marks, reads


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
    if state is not None and len(viable) > 1 and _barber_on_board(state) \
            and barber_claimants(state):
        viable = [(cost * _barber_share(world, changes, state), changes)
                  for cost, changes in viable]
    # A Summoner chosen at a tea party is one choice, however many ways it
    # then summoned: each way gets its share of that one (Hatter stage 2,
    # 25.10.2026), as a random pick of player and Demon would.
    if state is not None and len(viable) > 1 and _tea_on_board(state) \
            and "Summoner" in state.script.keys:
        viable = [(cost * _summon_share(world, changes, state), changes)
                  for cost, changes in viable]
    total = sum(cost for cost, _changes in viable)
    if total <= 0:
        return []
    return [(Timeline(world, changes) if changes else world, cost / total)
            for cost, changes in viable]


def _summon_share(world, changes, state):
    """One over the number of ways the tea party's Summoner could have
    summoned, for a story where it did; 1 otherwise."""
    if not any(isinstance(c, Summoned) for c in changes):
        return 1.0
    tea = tuple(c for c in changes if isinstance(c, TeaParty))
    if not any(c.role == "Summoner" for c in tea):
        return 1.0
    ways = len(_offers(a_hatted_summoner_summons, Timeline(world, tea),
                       state)) - 1
    return 1.0 / ways if ways > 0 else 1.0


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
        # A Zombuul on the board as dead stands all the same; of two
        # living Demons either wins (Hatter stage 2): count who really
        # stands, and evil has won if two or fewer do with a Demon among
        # them.
        demons = world.demons_at(phase)
        up = [d for d in demons if d not in board
              and world.role_at(d, phase) == "Zombuul"
              and _zombuul_still_going(world, state, d, phase)]
        if (up or any(d in board for d in demons)) \
                and len(board) + len(up) <= 2:
            return False                  # it would have won there and then
    return True


def _explain(world, state, outcome=None):
    """The cost of one telling of this world, with the lineage settled —
    tried for each hidden choice the world leaves open, the best kept.

    Two characters make a choice the board never shows and that every
    reading has to agree on: which good player is the Lycanthrope's faux
    paw, and which player is the Lleech's host (11.10.2026). Each is tried
    as a fixed seat, and the telling that fits best wins, as for the
    Fortune Teller's red herring.
    """
    choices = _hidden_choices(world, state)
    if choices is None:
        state._hidden = None
        return _explain_once(world, state, outcome)
    best, best_marks = None, None
    for choice in choices:
        state._hidden = choice
        marks = {} if outcome is not None else None
        cost = _explain_once(world, state, marks)
        if cost is not None and (best is None or cost > best):
            best, best_marks = cost, marks
    state._hidden = None
    if outcome is not None and best_marks:
        outcome.update(best_marks)
    return best


def _faux_paw_candidates(world, state):
    """The good players worth trying as the faux paw.

    Only a seat some reading looks at, or the Lycanthrope could have hit,
    can make a difference; one seat nobody looks at stands for all the
    rest. Good when the game began: "one good player".
    """
    n = state.n_players
    good = [p for p in range(n) if not world.evil_at(p, "N0")]
    if not good:
        return [None]
    looked = set()
    everybody = False
    for info in state.infos:
        kind = type(info).__name__
        if kind in ("Chef", "Empath", "OracleInfo", "ShugenjaInfo"):
            everybody = True
            break
        for field in ("a", "b", "c", "target"):
            # And the Bounty Hunter's evil player (Stelle 62, 20.10.2026):
            # left off, the faux paw it was shown was never tried, so a
            # Bounty Hunter told of a good player read as droisoned.
            if kind in ("SeamstressInfo", "NobleInfo", "StewardInfo",
                        "VillageIdiotInfo", "LycanthropeChose",
                        "BountyHunterInfo"):
                got = getattr(info, field, None)
                if isinstance(got, int):
                    looked.add(got)
    if everybody:
        return good
    for seat, phase in state.death_phases():
        if phase[:1] == "N":
            looked.add(seat)
    out = [p for p in good if p in looked]
    rest = [p for p in good if p not in looked]
    return out + rest[:1]


def _hidden_choices(world, state):
    """Every (faux paw, Lleech host) worth trying, or None for neither.

    The host: anybody who died, since only a death can show it — or -1,
    "somebody who never died", which then may be poisoned anywhere.
    """
    faux = [None]
    host = [None]
    if _on_board(state, "Lycanthrope") and (
            "Lycanthrope" in world.roles
            or taken_by_a_philosopher(state, "Lycanthrope")):
        faux = _faux_paw_candidates(world, state)
    if _in_bag(state, "Lleech"):
        lleech = world.find("Lleech")
        if lleech is not None:
            dead = sorted({seat for seat, _p in state.death_phases()
                           if seat != lleech})
            host = dead + [-1]
    if faux == [None] and host == [None]:
        return None
    return [(f, h) for f in faux for h in host]


def _faux_paw(state):
    hidden = getattr(state, "_hidden", None)
    return hidden[0] if hidden else None


def _lleech_host(state):
    """The host in this telling: a seat, -1 for one who never died, or
    None when there is no Lleech to ask about."""
    hidden = getattr(state, "_hidden", None)
    return hidden[1] if hidden else None


def _explain_once(world, state, outcome=None):
    """The cost of one telling of this world, with the lineage settled."""
    if not _the_game_went_on(world, state):
        return None
    # A night nothing at all explains settles it before any reading is
    # judged. The answer is the same either way — `_night_accounts` below
    # would come back empty — but asked first, a story that fails on its
    # deaths has asked about nobody's side on the way, and the stories
    # that differ from it only in who turned evil need not be told
    # (`_explain_or_recall`). Nine in ten stories of a busy board with a
    # Bounty Hunter end here (measured 11.10.2026).
    if _LISTENING[0]:
        for night in sorted(set(_night_deaths(state)) | set(
                getattr(state, "quiet_nights", None) or ())):
            if not _explained_night(world, state, night):
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

    def settle(readings, extra_working=None):
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
            for day, seats in (extra_working or {}).items():
                needed.setdefault(day, set()).update(seats)
            planned = _impairment_plan(world, state, wanted, needed)
            if planned is None:
                continue
            got = planned[1] * night_cost * invented_factor
            if best is None or got > best:
                best = got
        return best

    either = getattr(state, "_either", None) or []

    def settle_either(readings):
        """`settle`, trying each way a true reading under a Vortox can be
        excused: per night, the Vortox off, or every source droisoned.
        One of the two covers the whole night, so this is two choices a
        night rather than one per reading.

        And each row that held only with somebody else impaired or
        working: that, or its source off (a Chambermaid and a Wraith,
        08.10.2026). Six choices at most are tried both ways; past that
        the first is taken, which for a row is the Wraith."""
        choices = [("vortox", night) for night in sorted(vortox_or)]
        choices += [("row", i) for i in range(len(either))]
        if not choices:
            return settle(readings)
        best = None
        for picks in product((True, False), repeat=min(len(choices), 6)):
            trial = {n: set(seats) for n, seats in readings.items()}
            working = {}
            for (kind, key), first in zip(choices, picks + (True,) * len(choices)):
                if kind == "vortox":
                    vortox, sources = vortox_or[key]
                    trial.setdefault(key, set()).update(
                        {vortox} if first else sources)
                    continue
                night, source, impaired, needed = either[key]
                if first:
                    trial.setdefault(night, set()).update(impaired)
                    working.setdefault(night, set()).update(needed)
                else:
                    trial.setdefault(night, set()).update(source)
            got = settle(trial, working)
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
    # Chosen at setup, among the good: a Summoner's Marionette-to-be too
    # (22.10.2026).
    dealt = dealt_roles(world)
    herrings = [p for p in asked if not is_evil(dealt[p])]
    for p in range(state.n_players):
        if p not in asked and not is_evil(dealt[p]):
            herrings.append(p)
            break

    best, best_marks = None, None
    for rh in herrings:
        combined = {night: set(seats) for night, seats in failures.items()}
        marks = {}
        for info, src, idx, vortox in ft_infos:
            if vortox is not None:
                # Under a Vortox it is the other way about: an answer
                # that was true means the Vortox was not working. The
                # seat's own droisoning excuses nothing. And true, not
                # legal — a yes on a Recluse is false.
                fits, src = not info.is_true_with(world, rh), vortox
            else:
                fits = info.holds(world, state, rh, src) or any(
                    info.holds(_AsRecluse(world, who), state, rh, src)
                    for who in _philosopher_recluses(
                        world, state, f"N{info.night}"))
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
    claim = state.dealt_claims().get(p)
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
            claimed = state.dealt_claims().get(p)
            if claimed:
                bluffs[claimed] += 1

    inherited = _could_have_inherited(world, state)
    madness = _madness_nights(world, state)
    # A Pixie claiming what it was shown is mad, as its ability asks: no
    # lie to pay for (11.10.2026).
    pixies = _on_board(state, "Pixie")
    # Beside a Bounty Hunter one Townsfolk is evil and bluffs like any
    # evil player: one Townsfolk's false claim there is that one's, and
    # costs what a bluff costs (11.10.2026).
    evil_townsfolk = (_in_bag(state, "BountyHunter")
                      and "BountyHunter" in dealt_roles(world))

    for p in range(state.n_players):
        evil = is_evil(world.roles[p])
        if is_lying(world, state, p) and p not in inherited \
                and not must_hide(world.roles[p]) \
                and not (pixies and _mad_pixie(world, state, p)):
            # A Mutant's cover story is not a choice (catalogue `hides`),
            # so it costs the world nothing.
            if not evil:
                if TEAM[world.roles[p]] == "outsider":
                    w *= OUTSIDER_HIDING_PENALTY
                elif evil_townsfolk:
                    evil_townsfolk = False
                elif madness > 0:
                    w *= CERENOVUS_MADNESS_PENALTY
                    madness -= 1
                else:
                    w *= TOWNSFOLK_LIE_PENALTY
            else:
                claim = state.dealt_claims().get(p)
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
    all_worlds = enumerate_worlds(state.n_players, state.dealt_claims(),
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
            state.n_players, state.dealt_claims(),
            getattr(state, "certainties", None), False, forced_roles(state),
            getattr(state, "wakes", None), state.script or DEFAULT,
            tuple(getattr(state, "fabled", ())))
        if not setups:
            allow_good_lies = True

    seen, weights = [], []
    for world, share in sample_worlds(
            state.n_players, state.dealt_claims(),
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
            state.n_players, state.dealt_claims(), getattr(state, "certainties", None),
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
    pilot = pilot_size(state, allow_good_lies)
    if pilot > max_worlds:
        return estimate(state, allow_good_lies, dives, keep_samples, rng)

    n = state.n_players
    now = _report_phase(state)
    acc = _accumulator(n)
    legal = valid = 0
    TEA_TOLD[0] = 0
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
    # The weight of worlds a case not reckoned yet runs through (the
    # Hatter's Stufe 1): the report says so instead of a figure.
    unreckoned = defaultdict(float)

    for world in iter_worlds(n, state.dealt_claims(),
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
        # The same once the tea parties, at the rate so far, would take
        # more stories than a solve may tell (V Weg 1).
        if TEA_BUDGET is not None and TEA_TOLD[0] and legal > 50 \
                and TEA_TOLD[0] * max(pilot, legal) / legal \
                > TEA_EXACT_BUDGET:
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
        why = hatter_unreckoned(view, state)
        if why is not None:
            unreckoned[why] += wt
        for story, share in _story_shares(world, viable, state):
            _tally(acc, world, story, state, wt * share, n, now)
            for day, seat in executed:
                if seat in story.demons_at(f"D{day}"):
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
            "blame": shares, "mastermind": hints, "readings": readings,
            "unreckoned": _unreckoned(unreckoned, total)}


# --------------------------------------------------------------------------
# When there are too many worlds to count, look at a lot of them instead
# --------------------------------------------------------------------------

def _unreckoned(weights, total):
    """{what is not reckoned yet: its share of the weight in per cent}."""
    if total <= 0:
        return {}
    return {why: _share(value, total) for why, value in weights.items()
            if value > 0}


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
    demons = view.demons_at(phase)
    for p in range(n):
        role = view.role_at(p, phase)
        acc["roles"][p][role] += weight
        if acts_as_cult_leader(view, state, p, phase) \
                and _in_bag(state, "CultLeader"):
            # On whichever side its neighbours allow, and evenly where
            # they allow both (11.10.2026).
            sides = cult_sides(view, state, p, phase)
            if True in sides:
                acc["evil"][p] += weight / len(sides)
        elif view.evil_at(p, phase):
            acc["evil"][p] += weight
        if p in demons:
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
    SUMMON_SAMPLE[0] = SUMMON_SAMPLE_SIZE
    try:
        return _estimate(state, allow_good_lies, dives, keep_samples, rng)
    finally:
        SUMMON_SAMPLE[0] = None


def _estimate(state, allow_good_lies, dives, keep_samples, rng):
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
    unreckoned = defaultdict(float)
    TEA_TOLD[0] = 0

    for world, stands_for in sample_worlds(
            n, state.dealt_claims(), getattr(state, "certainties", None),
            allow_good_lies, forced_roles(state),
            getattr(state, "wakes", None), dives=dives, rng=rng,
            script=state.script, fabled=getattr(state, "fabled", ())):
        # Enough tea parties told: stop walking (V Weg 1).
        if TEA_BUDGET is not None and TEA_TOLD[0] > TEA_BUDGET \
                and walked >= TEA_MIN_DIVES:
            break
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
        why = hatter_unreckoned(Timeline(world, changes) if changes
                                else world, state)
        if why is not None:
            unreckoned[why] += weight
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
        "unreckoned": _unreckoned(unreckoned, total),
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
    for world in iter_worlds(state.n_players, state.dealt_claims(),
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
        claim = state.dealt_claims().get(seat)
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


# Last of the causes, as in the JavaScript (Hatter stage 2, 25.10.2026).
@death_causes.cause_rule
def a_second_demon_makes_deaths_arbitrary(world, state, night):
    """"If the Summoner creates a second living Demon, deaths tonight are
    arbitrary" (their jinx, C Weg 1): the same shape as the Pit-Hag's."""
    made = summoned_beside(world)
    if made is None or made.phase != f"N{night}":
        return []
    return [death_causes.Cause(
        "Summoner", death_causes.OTHER, frozenset(range(state.n_players)),
        capacity=state.n_players, cost=1.0, unstoppable=True)]
