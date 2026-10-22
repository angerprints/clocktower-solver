"""Deal a real game, then ask what everybody honestly learned.

This is the oracle the solver gets checked against. It knows the answer,
so if the solver ever throws away the world this produced, the solver is
wrong — no argument, no tuning discussion.

Deliberately independent of `botc.solver`: it re-derives what each
character sees from the seating and the roles, so a shared misreading of
a rule cannot hide in both.
"""

import random

from botc.info import (registers_as_role,
                       Chef, ChambermaidInfo, ClockmakerInfo, CourtierChoice,
                       AcrobatChoice, AlsaahirGuess, ArtistInfo,
                       NobleInfo,
                       StewardInfo, KnightInfo, ShugenjaInfo, KingInfo,
                       NightwatchmanChoice, NightwatchmanSeen,
                       BansheeAnnounced, GoblinClaim,
                       DamselGuess, FearmongerChose, VizierAnnounced,
                       BlindVote,
                       ChoirboyInfo, PrincessNominated, GolemNomination,
                       PsychopathKill, PsychopathRoshambo, WidowKnown,
                       SlayerShot, VirginNomination,
                       PreacherChoice, HuntsmanChoice, PuzzlemasterGuess,
                       BoomdandyExploded, BecameInfo,
                       PixieLearned, VillageIdiotInfo, LycanthropeChose,
                       HarpyMadness,
                       BountyHunterInfo, CultCalled, LeviathanAnnounced,
                       ExecutionNomination, AlHadikhiaChose,
                       HighPriestessInfo, GeneralInfo, FishermanAdvice,
                       BalloonistInfo,
                       DreamerInfo,
                       ExorcistChoice, InnkeeperChoice,
                       MoonchildChoice, SailorChoice, Empath, EvilTwinPair,
                       FlowergirlInfo, JugglerInfo, KlutzChoice,
                       PhilosopherChoice, PitHagChoice,
                       SnakeCharmerChoice,
                       MathematicianInfo, TownCrierInfo,
                       OracleInfo, SavantInfo,
                       SageInfo, SeamstressInfo,
                       FortuneTeller, GamblerGuess, GameState,
                       GrandmotherInfo, Investigator, Librarian, Ravenkeeper,
                       Undertaker, Washerwoman)
from botc.roles import (DEMONS, MINIONS, OUTSIDERS, SETUP, TEAM, TOWNSFOLK,
                        evil_registrations,
                        is_evil)
from botc.info import phase_index
from botc.worlds import World


class Deal:
    """One dealt game: the true world plus everything that happened."""

    def __init__(self, roles, believes, red_herring, poisoned, deaths, seed):
        self.roles = list(roles)
        self.believes = list(believes)
        self.red_herring = red_herring
        self.poisoned = dict(poisoned)      # {night: seat}
        self.deaths = dict(deaths)          # {seat: phase}
        self.seed = seed
        # Who held the Demon, and from when. A starpass or a Scarlet Woman
        # taking over appends to this, so a seat's character is a function
        # of time and not just of the deal.
        self.handovers = []                 # [(phase, seat)]
        # Every character change, not only the Demon's. A handover is one
        # of these; so is a Pit-Hag creation and a Snake Charmer swap.
        self.changes = []                   # [(phase, seat, role)]
        # Seats poisoned for the rest of the game — a swapped Snake
        # Charmer, and nothing else yet.
        self.perma_poisoned = set()
        # {seat: the character a Philosopher took}. Not a change of
        # character, so it cannot live in `changes`.
        self.philosophies = {}
        self.poisoned_by = {}
        self.side_changes = []              # [(phase, seat, role, side)]
        # State a Demon carries between nights. A Pukka's poison kills on
        # the night after it lands; a Po that took nobody takes three the
        # next time.
        self.pukka_poisoned = None          # where its token sits now
        self.pukka_history = {}             # night -> (came due, freshly hit)
        # The Pukka's poison, kept apart from the Poisoner's: one table
        # for both lost whichever was written second.
        #   marks  night -> the seat it poisoned on that night's turn
        #   due    night -> the seat still poisoned from before, until
        #          its turn (and through the night, if that seat died)
        self.pukka_marks = {}
        self.pukka_due = {}
        self.pukka_owner = None             # the seat the tokens belong to
        self.po_charged = False
        # What it chose, in order — whether or not the kill landed — and
        # who died of it. They were one list until a Shabaloth went for a
        # Fool twice: the first try was shrugged off and left no trace, so
        # a replay saw one attack and a Fool still standing (03.10.2026).
        self.demon_aimed = {}               # night -> who the Demon aimed at
        self.demon_killed = {}              # night -> who it killed
        self.monk_guarded = {}              # night -> who the Monk kept safe
        self.cursed = {}                    # night -> who a Witch aimed at
        self.exorcised = {}                 # night -> who an Exorcist named
        self.balloonist_last = {}           # seat -> who it was shown last
        self.exorcised_last = {}            # seat -> its previous target
        self.sailor_drunk = {}              # night -> which of the two
        self.innkeeper_guarded = {}         # night -> the pair kept safe
        self.innkeeper_void = set()         # nights it chose with no ability
        self.innkeeper_drunk = {}           # night -> which of them is drunk
        # Each holder's choice on its own, by (character, night) -> {seat:
        # what it chose}: the real holder and a Philosopher that took the
        # character both choose, and only a working one counts
        # (13.10.2026). The fields above keep the first, for the walk.
        self.chose_by = {}
        # What the table did in daylight. Only a Flowergirl and a Town
        # Crier ask, but the day is where the answer lives.
        # A Zombuul that survived its first death — registered dead, still
        # the Demon, still killing on quiet days. And the day after which
        # a Mastermind's extra day runs out and the game is over.
        self.zombuul_up = None
        # Lil' Monsta (21.10.2026): who babysat it each night, chosen by
        # the Minions, and so "is the Demon" from then on.
        self.babysat = {}                   # night -> seat
        self.fanggu_jumped = False
        self.game_ends_after = None
        # The moment evil won, if it did: "N4" at dawn, "D3" when a Witch's
        # curse took the third from last, "E3" at an execution. The game
        # stops there, and `game_ends_after` is then the last night that
        # was played. `None` for a game that was still open when the
        # nights asked for ran out (04.10.2026).
        self.ended_at = None
        self.ended_why = None               # "two alive" or "vortox"
        self.nights_played = 0              # how far `play` got
        self.votes = {}                     # {day: {seat, ...}}
        self.nominations = {}               # {day: {seat, ...}}
        self.tally = {}                     # {day: {nominee: votes}}
        # Death stopped being permanent, and an execution stopped being a
        # death (03.10.2026). `deaths` stays what it always was — the
        # death a seat is lying under *now* — so everything that asks
        # "is this seat dead" goes on working. What came before a return
        # is kept beside it, and `record()` puts the two together for
        # anybody who wants the whole story.
        self.earlier_deaths = []            # [(seat, phase)] since undone
        self.resurrections = []             # [(seat, phase, by whom)]
        self.executions = {}                # {day: seat} executed, and lived
        self.walked_because = {}            # {day: what kept them alive}
        self.witch_deaths = {}              # {day: seat} died nominating
        self.fool_spent = {}                # Fool seat -> when its free death went
        self.fool_spent_ever = []           # [(seat, phase)], never forgotten
        self.spared = {}                    # night -> (advocate, who it chose)
        self.professor_chose = {}           # seat -> the night it spent it
        self.professor_raised = {}          # night -> who came back
        self.shabaloth_took = {}            # night -> (shabaloth, who died of it)
        self.regurgitated = {}              # night -> who came back
        self.moonchild_picked = {}          # night -> who it named
        self.cursed_by = {}                 # night -> the Witch that cursed
        self.pacifist_spared = 0            # how often it has stepped in
        # A character that dies and comes back is a new instance of it:
        # its old effects ended with the death, and it uses the ability
        # afresh (table ruling, 03.10.2026). So a Courtier can name a
        # character more than once a game, and each naming is its own
        # three days.
        self.courtier_chose = {}            # Courtier seat -> night, this life
        # The Goon, and the three that kill besides the Demon. All four
        # were dealt and never acted until 03.10.2026.
        self.goon_first = {}                # night -> (who chose it first, Goon)
        self.assassin_chose = {}            # Assassin seat -> the night it struck
        self.assassin_aimed = {}            # night -> whom
        self.godfather_aimed = {}           # night -> whom
        self.gossip_killed = {}             # night -> whom the Storyteller took
        self.lunatic_chose = {}             # night -> whom it thinks it attacked
        self.courtier_nights = set()        # {(seat, night)} it ever chose on
        self.courtier_drunks = []           # [(night, holder, courtier)]
        # The Nightwatchman points once a life. Whom, by night, for the
        # replay; and the row its choice put in *another* seat's mouth,
        # which `_for_role` cannot return since it is not that seat's own.
        self.nightwatchman_chose = {}       # seat -> the night it chose
        self.nightwatchman_aimed = {}       # night -> {seat: whom}
        self.said_by_others = []            # rows waiting to be heard
        # The fourth four (10.10.2026).
        self.damsel_guessed = False         # the Minions' one guess, spent
        self.fear_chose = {}                # night -> whom the Fearmonger chose
        self.fear_target = {}               # Fearmonger seat -> its current pick
        self.fear_nominated = {}            # day -> whom it nominated
        self.vizier_seen = set()            # Viziers whose first day has passed
        self.vizier_forced = {}             # day -> whom it executed at once
        self.grinder_drunk = set()          # nights the Organ Grinder chose drink
        self.blind_days = set()             # days voted with eyes closed
        self.hidden_votes = {}              # {day: {seat, ...}} on those days
        self.voted_for = {}                 # {day: {nominee: {seat, ...}}}
        # The fifth five (10.10.2026).
        self.princess_nominated = {}        # day -> (Princess, her nominee)
        self.princess_stop = {}             # night -> the Princess stopping it
        self.golem_spent = set()            # Golems whose nomination is gone
        self.phil_token = {}                # Philosopher -> token shown (I)
        self.slayer_spent = set()           # Slayers that have shot
        self.virgin_spent = set()           # Virgins nominated once
        self.virgin_executed = {}           # {day: nominator executed}
        self.shown_in_the_open = set()      # a Slayer that shot, a Virgin
                                            # that took its nominator
        self.psychopath_struck = {}         # day -> (Psychopath, target)
        self.roshambo = {}                  # day -> the Psychopath executed
        self.widow_poison = []              # [(Widow, target, night)]
        self.day_heard = []                 # rows the day produced
        # The sixth five (10.10.2026).
        self.preached = []                  # [(Preacher, Minion, night)]
        self.huntsman_spent = set()         # Huntsmen that have chosen
        self.puzzle_drunk = None            # the Puzzlemaster's drunk seat
        self.puzzle_spent = set()           # Puzzlemasters that guessed
        self.huntsman_chose = {}            # night -> (Huntsman, target, made)
        self.huntsman_night = {}            # Huntsman seat -> the night it chose
        # The seventh five (11.10.2026).
        self.vi_drunk = None                # the drunk Village Idiot
        self.faux_paw = None                # the good seat that reads evil
        self.lyc_quiet = set()              # nights the Lycanthrope killed
        self.lyc_aimed = {}                 # night -> (Lycanthrope, target)
        self.harpy_mad = {}                 # night -> (Harpy, mad, second)
        self.harpy_chose = {}               # night -> (Harpy, mad), all aims
        self.harpy_struck = {}              # day -> [who the Harpy took]
        self.lleech_hosts = {}              # Lleech seat -> its host
        self.lleech_lost = None             # when the Mastermind's jinx hit
        self.pixie_learned = {}             # Pixie seat -> Townsfolk shown
        self.pixie_mad = {}                 # Pixie seat -> claims it
        # The eighth five (11.10.2026).
        self.bh_evil = None                 # the Townsfolk dealt evil
        self.bh_known = {}                  # Bounty Hunter -> who it knows
        self.bh_seen = {}                   # Bounty Hunter -> all it was shown
        self.bh_woke = set()                # {(seat, night)} it was shown one
        self.cult_seen = set()              # Cult Leaders past their first turn
        self.cult_fixed = set()             # made the Cult Leader while evil
        self.cult_woke = set()              # {(seat, night)} its side changed
        self.mez_marked = None              # (who said the word, the day)
        self.mez_turned = None              # (who turned evil, the night)
        self.lev_first = None               # the Leviathan's first day
        self.lev_announced = None           # the day the table was told
        self.lev_good_executed = 0          # good players executed beside it
        self.lev_picked = set()             # good players it chose (jinxes)
        self.lev_chose = {}                 # night -> (Leviathan, its pick)
        self.lev_aimed = {}                 # night -> whom it pointed at
        self.nominated_by = {}              # {day: {nominee: nominator}}
        self.yag_said = {}                  # day -> times the phrase was said
        self.yag_by_day = {}                # day -> whom it took nominating

    def demon_at(self, phase):
        """The seat holding the Demon at this phase."""
        from botc.info import phase_index
        here = phase_index(phase)
        # Whichever Demon holds it *at this phase*, not whichever was
        # dealt one. Two bugs have lived here: the name was hardcoded to
        # "Imp", so every Bad Moon Rising and Sects & Violets game
        # reported no Demon at all; and it read the deal rather than the
        # changes, so a Demon that swapped away with a Snake Charmer went
        # on killing from a seat that was no longer the Demon.
        seat = next((i for i in range(len(self.roles))
                     if TEAM[self.role_at(i, phase)] == "demon"), None)
        # Lil' Monsta's babysitter: chosen at its place in the night, so
        # whatever reads before that tonight still sees last night's.
        if seat is None and self.babysat:
            night = int(phase[1:])
            upto = [k for k in self.babysat if k <= night]
            if upto:
                seat = self.babysat[max(upto)]
        for when, heir in self.handovers:
            if phase_index(when) <= here:
                seat = heir
        return seat

    def role_at(self, seat, phase):
        """The character this seat held at this phase.

        Everything before the first change is just the deal. After one,
        whatever it became — which is what an Undertaker or a Ravenkeeper
        would learn about them.

        Handovers used to be the only kind, and the heir was assumed to
        be an Imp. A Philosopher, a Snake Charmer and a Pit-Hag all move
        characters around without a Demon dying, so changes are recorded
        as (phase, seat, role) and a handover is just one of them.
        """
        from botc.info import phase_index
        here = phase_index(phase)
        role = self.roles[seat]
        for when, who, became in self.changes:
            if who == seat and phase_index(when) <= here:
                role = became
        return role

    def side_at(self, seat, phase):
        """Which side this seat was on at this phase.

        Almost always the side its character sits on — but not after a
        Snake Charmer swap, where a Demon becomes a *good* Snake Charmer,
        or a Pit-Hag creation, where a Townsfolk turned into the Poisoner
        keeps its own side.
        """
        from botc.info import phase_index
        from botc.roles import is_evil
        here = phase_index(phase)
        side = "evil" if is_evil(self.roles[seat]) else "good"
        for when, who, _became, moved in self.side_changes:
            if who == seat and phase_index(when) <= here:
                side = moved
        return side

    @property
    def n(self):
        return len(self.roles)

    @property
    def mastermind_day(self):
        """The extra day a Mastermind bought, or None.

        `game_ends_after` alone said so while a Mastermind was the only
        thing that could end a game. Evil winning with two left sets it
        too, and those games have `ended_at` beside it.
        """
        return self.game_ends_after if self.ended_at is None else None

    def world(self):
        """The deal as the solver reads it. With a Summoner the Marionette
        is nobody's until the Demon comes (22.10.2026): the seat that
        became it — or, if none did, the one that would have — is dealt
        it there, believing the character it really held until then."""
        roles, believes = list(self.roles), list(self.believes)
        seat = getattr(self, "marionette_made", None)
        if seat is None:
            seat = getattr(self, "marionette_slot", None)
        if seat is not None:
            # A Drunk or a Lunatic made it goes on believing its token
            # (22.10.2026); anybody else, the character it was dealt —
            # what it became before the Demon came is the solver's story
            # to tell (a Damsel the Huntsman found).
            before = (getattr(self, "marionette_before", None)
                      if seat == getattr(self, "marionette_made", None)
                      else None)
            believes[seat] = before or self.roles[seat]
            roles[seat] = "Marionette"
        return World(tuple(roles), tuple(believes))

    def apparent(self, seat):
        """The character this seat believes they are. A Philosopher that
        took the Trunkenbold lives by the Townsfolk it was shown (I, S)."""
        if self.philosophies.get(seat) == "Drunk" \
                and self.phil_token.get(seat):
            return self.phil_token[seat]
        return self.believes[seat] or self.roles[seat]

    def token(self, seat, phase):
        """The wrong token this seat is still living by at this phase.

        Until its character changes. A Drunk a Fang Gu jumped into *is*
        the Fang Gu, is told so and kills like one; it was droisoned for
        the rest of the game because the token was read off the deal,
        so the new Demon never killed and the solver could not say why
        the nights had gone quiet (07.10.2026).
        """
        if self.believes[seat] is None:
            return None
        # Made the Marionette when the Summoner's Demon came: from then on
        # it lives by the character it held (22.10.2026).
        if seat == getattr(self, "marionette_made", None):
            if self.role_at(seat, phase) == "Marionette":
                return self.believes[seat]
            # Before it: the Drunk's or the Lunatic's token, or nothing.
            if self.role_at(seat, phase) != self.roles[seat]:
                return None
            return self.marionette_before
        if self.role_at(seat, phase) != self.roles[seat]:
            return None
        return self.believes[seat]

    def seat_of(self, role):
        return self.roles.index(role) if role in self.roles else None

    def alive_at(self, phase):
        from botc.info import phase_index
        here = phase_index(phase)
        if not self.resurrections:
            return [p for p in range(self.n)
                    if self.deaths.get(p) is None
                    or phase_index(self.deaths[p]) >= here]
        # Somebody came back, so a seat's life is a run of events and not
        # one date. The same reading as `GameState._alive`: a death takes
        # effect *after* its moment — killed on night two, alive during
        # night two — and a return *at* its moment.
        out = []
        for p in range(self.n):
            events = [(phase_index(at), False) for at in self.deaths_of(p)]
            events += [(phase_index(at), True)
                       for who, at, _by in self.resurrections if who == p]
            standing = True
            for at, back in sorted(events):
                if back:
                    if at <= here:
                        standing = True
                elif at < here:
                    standing = False
            if standing:
                out.append(p)
        return out

    def deaths_of(self, seat):
        """Every moment this seat died, in order. Usually none or one."""
        out = [at for who, at in self.earlier_deaths if who == seat]
        if self.deaths.get(seat) is not None:
            out.append(self.deaths[seat])
        return out

    def died_on(self, *phases):
        """Who died at any of these moments, whether or not they stayed dead.

        `deaths` forgets a death once the seat is back, which is right for
        "who is dead now" and wrong for "did anybody die yesterday" — an
        Undertaker still learns who was executed after a Professor has
        raised them.
        """
        out = {seat for seat, at in self.deaths.items() if at in phases}
        out |= {seat for seat, at in self.earlier_deaths if at in phases}
        return out

    def back_at(self, seat, phase):
        """Whoever stood this seat up again at this moment, or None."""
        return next((by for who, at, by in self.resurrections
                     if who == seat and at == phase), None)

    def raise_up(self, seat, phase, by):
        """This seat is alive again, with its ability back.

        "Even a once per game ability they used already" — so a Fool gets
        its free death again and a Professor its one choice.
        """
        self.earlier_deaths.append((seat, self.deaths.pop(seat)))
        self.resurrections.append((seat, phase, by))
        self.fool_spent.pop(seat, None)
        self.professor_chose.pop(seat, None)
        self.courtier_chose.pop(seat, None)
        self.assassin_chose.pop(seat, None)
        self.nightwatchman_chose.pop(seat, None)

    def record(self, upto=None, told=True):
        """What the table saw happen to its players, for a `GameState`.

        Use as `GameState(..., **deal.record())`. Handing over
        `dict(deal.deaths)` was enough while a death was the only thing
        that could happen to a seat; now it would drop every return, every
        execution somebody walked away from, and the first death of
        anybody who came back.

        `upto` cuts it off at a phase, for a board as it stood mid-game.

        And what it saw *not* happen: the nights nobody died, and the
        days it got through. Neither was ever handed over, so no played
        game asked the solver what it makes of a night without a body —
        only hand-made boards did (04.10.2026). `told=False` leaves the
        two out again, for a measurement that wants the difference.

        A day is done once the night after it has begun. The day a game
        ended on is not one the town got through.
        """
        from botc.info import phase_index
        limit = None if upto is None else phase_index(upto)
        seen = lambda at: limit is None or phase_index(at) <= limit
        nothing = {}
        if told:
            nothing = {
                "quiet_nights": {
                    night for night in range(2, self.nights_played + 1)
                    if seen(f"N{night}") and not self.died_on(f"N{night}")},
                "days_done": {
                    day for day in range(1, self.nights_played)
                    if seen(f"N{day + 1}")},
            }
        deaths = {}
        for seat in range(self.n):
            got = tuple(at for at in self.deaths_of(seat) if seen(at))
            if got:
                deaths[seat] = got
        back = {}
        for seat, at, _by in self.resurrections:
            if seen(at):
                back[seat] = back.get(seat, ()) + (at,)
        return {
            **nothing,
            # Whether the board is one from after the end. The solver
            # takes a game to be going on unless told, and reads that as
            # evidence (04.10.2026).
            "game_over": self.ended_at is not None
                         and (limit is None
                              or phase_index(self.ended_at) <= limit),
            "deaths": deaths,
            "resurrections": back,
            "executions": {day: seat for day, seat in self.executions.items()
                           if seen(f"D{day}")},
            "witch_deaths": {day: seat
                             for day, seat in self.witch_deaths.items()
                             if seen(f"D{day}")},
        }

    def events(self, seat):
        """The same, for one seat, in the status codes the page posts.

            N2 died at night      X3 executed and died   S3 executed, lived
            D3 died by day        W3 died nominating     R3 back at night 3
        """
        from botc.info import phase_index
        out = []
        for at in self.deaths_of(seat):
            day = int(at[1:])
            if at[0] == "E":
                code = f"X{day}"
            elif at[0] == "D" and self.witch_deaths.get(day) == seat:
                code = f"W{day}"
            else:
                code = at
            out.append((phase_index(at), code))
        for who, at, _by in self.resurrections:
            if who == seat:
                out.append((phase_index(at), f"R{at[1:]}"))
        for day, who in self.executions.items():
            if who == seat:
                out.append((phase_index(f"D{day}"), f"S{day}"))
        return [code for _at, code in sorted(out)]

    def working(self, seat, night, by_day=False):
        """Is this seat's ability actually doing anything tonight?

        `by_day` asks about the day that follows instead. A night and its
        day are one span for nearly everything, and the one thing that
        can end between them is a drunkenness whose source died in the
        night.

        Asked of `droisoned_at`, which is the one place that knows every
        way of going wrong. This used to check the Drunk and the Poisoner
        and nothing else, so a No Dashii's neighbour, a Vigormortis's,
        a Sweetheart's, a Philosopher's, a swapped Snake Charmer and a
        whole table a Minstrel had silenced were all "working".
        
        Two functions answering the same question differently is how a
        Demon killed straight through its own silencing: the kill asked
        `working`, which said yes, while `droisoned_at` said no.
        """
        # A Philosopher that took the Trunkenbold has no ability that
        # works: what it does as the Townsfolk it was shown does nothing
        # (I, 14.10.2026). Not a droisoning the Mathematician counts.
        if self.philosophies.get(seat) == "Drunk":
            return False
        return seat not in droisoned_at(self, night, by_day)


def deal(n, rng, script=None, told=None):
    """A random legal setup for n seats, from a script.

    The script argument is the whole reason the other two published
    scripts can be dealt at all: everything here used to read the
    module-level Trouble Brewing lists, so every game the simulator ever
    produced was Trouble Brewing whatever anybody asked for.

    Setup changers are handled by name rather than by rule, because there
    are only a few and each moves the bag differently. A Baron adds two
    Outsiders and drops two Townsfolk; a Godfather moves one either way;
    a Fang Gu adds one Outsider.
    """
    from botc import scripts as script_mod
    script = script or script_mod.TROUBLE_BREWING
    townsfolk = list(script.townsfolk)
    outsiders = list(script.outsiders)
    minions = list(script.minions)
    demons = list(script.demons)

    tf, out, mi, de = SETUP[n]
    dealt_tf, dealt_out = tf, out

    # One setup changer at most, chosen before the bag is filled — which
    # is how the Storyteller does it.
    changer = None
    # The Vigormortis joined on 02.10.2026. Its "[-1 Outsider]" was in
    # neither the catalogue nor here, so it was dealt like a Demon that
    # changes nothing and the two agreed with each other about it.
    movers = [k for k in ("Baron", "Godfather", "FangGu", "Vigormortis")
              if k in minions or k in demons]
    # A quarter of the time for each script with one changer — and half
    # the time on Sects & Violets, which has two of its four Demons on
    # the list, so that every Demon is still dealt equally often.
    if movers and rng.random() < 0.25 * len(movers):
        changer = rng.choice(movers)
        if changer == "Baron" and tf >= 2 and out + 2 <= len(outsiders):
            tf, out = tf - 2, out + 2
        elif changer == "Godfather" and out + 1 <= len(outsiders) and tf >= 1:
            tf, out = tf - 1, out + 1
        elif changer == "FangGu" and out + 1 <= len(outsiders) and tf >= 1:
            tf, out = tf - 1, out + 1
        elif changer == "Vigormortis":
            # One Outsider fewer, if there is one to take.
            if out >= 1 and tf + 1 <= len(townsfolk):
                tf, out = tf + 1, out - 1
        else:
            changer = None

    # "One at most" has to hold on both teams. With a Baron chosen the
    # Demon was drawn from all of them, so a mixed script could put a
    # Fang Gu beside it in a bag counted for the Baron alone — one
    # Outsider short, and no legal world at all (07.10.2026). No
    # published script has a changer on each team, so nothing they deal
    # moves: the lists below are the whole lists there.
    plain_minions = [m for m in minions if m not in ("Baron", "Godfather")]
    plain_demons = [d for d in demons if d not in ("FangGu", "Vigormortis")]
    if changer in ("Baron", "Godfather"):
        rest = [m for m in plain_minions]
        if len(rest) < mi - 1:
            rest = [m for m in minions if m != changer]
        picked_minions = [changer] + rng.sample(rest, mi - 1)
        picked_demons = list(rng.sample(
            plain_demons if len(plain_demons) >= de else demons, de))
    elif changer in ("FangGu", "Vigormortis"):
        picked_minions = rng.sample(
            plain_minions if len(plain_minions) >= mi else minions, mi)
        rest = plain_demons
        picked_demons = [changer] + list(rng.sample(rest, de - 1))
    else:
        # A setup changer that is not chosen must stay out of the bag:
        # its change is mandatory, so it cannot sit in a bag that did not
        # make room for it.
        rest = [m for m in minions if m not in ("Baron", "Godfather")]
        picked_minions = rng.sample(rest, mi) if len(rest) >= mi \
            else rng.sample(minions, mi)
        spare_demons = [d for d in demons
                        if d not in ("FangGu", "Vigormortis")]
        picked_demons = list(rng.sample(spare_demons, de)) \
            if len(spare_demons) >= de else list(rng.sample(demons, de))

    # "[No Demon]": the Summoner (21.10.2026). A Townsfolk instead, and
    # the Demon comes on the third night.
    if "Summoner" in picked_minions:
        # A Demon that moved the Outsiders is not in play after all.
        if changer in ("FangGu", "Vigormortis"):
            tf, out = dealt_tf, dealt_out
        tf += de
        picked_demons, de = [], 0

    # "[+1 Minion]" and no Demon dealt: Lil' Monsta (21.10.2026). The
    # Minions hand it round from the first night.
    if "LilMonsta" in picked_demons:
        more = [m for m in minions if m not in picked_minions
                and m not in ("Baron", "Godfather", "Summoner")]
        if more:
            picked_demons.remove("LilMonsta")
            picked_minions.append(rng.choice(more))
            mi, de = mi + 1, de - 1
        else:
            picked_demons[picked_demons.index("LilMonsta")] = next(
                k for k in demons if k != "LilMonsta")

    # "[+1 Minion. -? to +? Outsiders]": the Lord of Typhon (19.10.2026).
    # One Minion more than the table has, and the Outsiders anywhere from
    # two fewer to two more, as room allows.
    typhon = "LordOfTyphon" in picked_demons
    # "[You choose which players are which Minions. -? to +? Outsiders]":
    # the Kazali (20.10.2026). The usual Minions (A, Weg 1), made on the
    # first night out of players who were dealt good tokens, and the
    # Outsiders anywhere as for the Lord of Typhon.
    kazali = "Kazali" in picked_demons
    if typhon:
        # Never a Summoner: it comes with no Demon at all (21.10.2026).
        more = [m for m in minions if m not in picked_minions
                and m != "Summoner"]
        if more and tf >= 1:
            picked_minions.append(rng.choice(more))
            mi += 1
            tf -= 1
    if typhon or kazali:
        room = [x for x in range(max(0, out - 2), out + 3)
                if x <= len(outsiders) and 0 <= n - mi - de - x
                <= len(townsfolk)]
        if room:
            out = rng.choice(room)
            tf = n - mi - de - out

    # "[X Outsiders]": a Xaan sets the number, whatever else would move
    # it — here 1 to 3, as the wiki suggests (10.10.2026).
    if "Xaan" in picked_minions:
        room = [x for x in (1, 2, 3)
                if x <= len(outsiders) and 0 <= n - mi - de - x
                <= len(townsfolk)]
        if room:
            out = rng.choice(room)
            tf = n - mi - de - out
    picked_outsiders = rng.sample(outsiders, out)
    spare = list(townsfolk)
    rng.shuffle(spare)

    chosen, believes_for = [], {}
    for o in picked_outsiders:
        chosen.append(o)
        if o == "Drunk":
            believes_for[o] = spare.pop()      # a token nobody else can hold
    chosen += spare[:tf]
    # "[+the King]": a Choirboy in the bag brings the King with it, in
    # place of another Townsfolk (10.10.2026). A script with a Choirboy
    # and no King is built wrong, and then nothing is added.
    if "Choirboy" in chosen and "King" not in chosen \
            and "King" in townsfolk:
        out_go = [r for r in spare[:tf] if r != "Choirboy"]
        if out_go:
            gone = rng.choice(out_go)
            chosen[chosen.index(gone)] = "King"
            i = spare.index(gone)
            if "King" in spare:
                j = spare.index("King")
                spare[i], spare[j] = "King", gone
            else:
                # A Drunk was handed the King's token. It takes the one
                # that just left the bag instead: the King is in play now.
                spare[i] = "King"
                believes_for["Drunk"] = gone
    # "[+the Damsel]": a Huntsman brings her in place of a Townsfolk,
    # unless she is in the bag anyway (10.10.2026).
    if "Huntsman" in chosen and "Damsel" not in chosen \
            and "Damsel" in outsiders:
        out_go = [r for r in spare[:tf]
                  if r not in ("Huntsman", "Choirboy", "King")]
        if out_go:
            gone = rng.choice(out_go)
            chosen.remove(gone)
            chosen.insert(0, "Damsel")
            spare.remove(gone)
            spare.insert(tf - 1, gone)
            tf -= 1
    # "[+0 to +2 Village Idiots]", in place of other Townsfolk — none half
    # the time, one a third, two the rest (11.10.2026).
    if "VillageIdiot" in chosen:
        roll = rng.random()
        extra = 0 if roll < 0.5 else (1 if roll < 0.8 else 2)
        keep = ("VillageIdiot", "Huntsman", "Choirboy", "King")
        for _ in range(extra):
            out_go = [r for r in chosen if TEAM[r] == "townsfolk"
                      and r not in keep]
            if not out_go:
                break
            gone = rng.choice(out_go)
            chosen[chosen.index(gone)] = "VillageIdiot"
    chosen += picked_minions
    chosen += picked_demons

    # The Marionette thinks it is a good character — a Townsfolk or an
    # Outsider nobody holds — and is never told otherwise. Worked out
    # from the tokens left over, the same way the Drunk's is.
    if "Marionette" in picked_minions:
        from botc.catalogue import CHARACTERS as _C
        unused = spare[tf:] + [o for o in outsiders
                               if o not in picked_outsiders
                               and not _C[o].believes]
        if unused:
            believes_for["Marionette"] = rng.choice(unused)

    order = list(range(n))
    rng.shuffle(order)
    roles = [None] * n
    believes = [None] * n
    for seat, role in zip(order, chosen):
        roles[seat] = role
        believes[seat] = believes_for.get(role)
    if typhon:
        roles, believes = _typhon_seats(roles, believes, rng)
    if typhon or kazali:
        # Each Minion was handed a good token first and turned on the
        # first night; that token is not in play (Lord of Typhon D,
        # 19.10.2026; Kazali C and D, 20.10.2026: a Townsfolk or an
        # Outsider, whoever the Kazali picked).
        unused = [r for r in spare[tf:] + [o for o in outsiders
                                           if o not in picked_outsiders]
                  if r not in roles and r not in believes
                  and r not in ("Drunk", "Marionette", "Lunatic")]
        rng.shuffle(unused)
        for seat, role in enumerate(roles):
            if TEAM[role] == "minion" and role != "Marionette" and unused:
                if told is not None:
                    told[seat] = unused.pop()

    # "[You neighbour the Demon]": if the shuffle put it elsewhere, it
    # trades seats with whoever sits beside the Demon. Written from the
    # rule rather than from the solver's catalogue field on purpose.
    # With Lil' Monsta it sits beside the first babysitter instead, whom
    # the Minions choose on the first night (`_minions_choose`).
    # So it trades seats to sit beside another Minion, who may then be
    # chosen first even under the Magician's jinx.
    # With a Summoner the Demon is made beside it instead (their jinx,
    # `_summoner_summons`).
    if "Marionette" in roles and not any(TEAM[r] == "demon" for r in roles) \
            and "Summoner" not in roles:
        m = roles.index("Marionette")
        others = [i for i in range(n)
                  if TEAM[roles[i]] == "minion" and i != m]
        if others and not any(TEAM[roles[(m + k) % n]] == "minion"
                              for k in (-1, 1)):
            mate = rng.choice(others)
            swap = rng.choice([(mate - 1) % n, (mate + 1) % n])
            roles[m], roles[swap] = roles[swap], roles[m]
            believes[m], believes[swap] = believes[swap], believes[m]
    if "Marionette" in roles and any(TEAM[r] == "demon" for r in roles):
        m = roles.index("Marionette")
        demon = next(i for i in range(n) if TEAM[roles[i]] == "demon")
        beside = [(demon - 1) % n, (demon + 1) % n]
        if m not in beside:
            swap = rng.choice(beside)
            roles[m], roles[swap] = roles[swap], roles[m]
            believes[m], believes[swap] = believes[swap], believes[m]
    return roles, believes


def _typhon_seats(roles, believes, rng):
    """Seat the evil team in a line, the Lord of Typhon not at an end.

    Patrick, 19.10.2026: anywhere in the line but an end (A, Weg 2); a
    Recluse may stand anywhere in it, registering as a Minion — here a
    third of the time. A Marionette sits beside the Lord of Typhon, as it
    must beside any Demon. Everybody else keeps the order the shuffle
    gave them.
    """
    n = len(roles)
    pairs = list(zip(roles, believes))
    lord = next(pr for pr in pairs if pr[0] == "LordOfTyphon")
    minions = [pr for pr in pairs if TEAM[pr[0]] == "minion"]
    rest = [pr for pr in pairs if pr is not lord and pr not in minions]
    rng.shuffle(minions)
    recluse = next((pr for pr in rest if pr[0] == "Recluse"), None)
    line = list(minions)
    if recluse is not None and rng.random() < 1 / 3:
        rest.remove(recluse)
        line.insert(rng.randrange(len(line) + 1), recluse)
    if len(line) < 2:
        return roles, believes            # nobody to stand either side
    at = rng.randrange(1, len(line))      # never at an end
    line.insert(at, lord)
    puppet = next((i for i, pr in enumerate(line)
                   if pr[0] == "Marionette"), None)
    if puppet is not None and abs(puppet - at) != 1:
        near = at - 1 if puppet < at else at + 1
        line[puppet], line[near] = line[near], line[puppet]
    start = rng.randrange(n)
    seats = [None] * n
    for i, pr in enumerate(line):
        seats[(start + i) % n] = pr
    free = [s for s in range(n) if seats[s] is None]
    for s, pr in zip(free, rest):
        seats[s] = pr
    return [pr[0] for pr in seats], [pr[1] for pr in seats]


# Outsiders who hurt the town while they live, and choose death when the
# Al-Hadikhia asks (Patrick, E, 21.10.2026): as the seat believes it is.
_BETTER_DEAD = frozenset({"Recluse", "Saint", "Butler", "Mutant", "Goon",
                          "Damsel", "Politician", "Ogre"})


def _al_hadikhia_acts(d, night):
    """Is the Demon tonight an Al-Hadikhia, standing to choose?"""
    phase = f"N{night}"
    demon = d.demon_at(phase)
    return (demon is not None and d.role_at(demon, phase) == "AlHadikhia"
            and demon in d.alive_at(phase) and d.deaths.get(demon) is None)


def _spent(d, seat, night):
    """Has this good player used up what its ability does?"""
    from botc.catalogue import CHARACTERS as _C
    phase = f"N{night}"
    role = d.apparent(seat)
    if _C[role].nights == "first" and night > 1:
        return True
    return (seat in d.slayer_spent or seat in d.huntsman_spent
            or seat in d.professor_chose or seat in d.courtier_chose
            or seat in getattr(d, "nightwatchman_chose", {}))


def _al_hadikhia_answer(d, seat, night, alive, rng):
    """Life or death, as Patrick's E has it (21.10.2026): evil chooses
    life; a good player whose ability is spent, or an Outsider that hurts
    the town while it lives, mostly death; anybody else mostly life."""
    phase = f"N{night}"
    if d.side_at(seat, phase) == "evil":
        return True
    if _spent(d, seat, night) or d.apparent(seat) in _BETTER_DEAD:
        return rng.random() >= 0.8
    return rng.random() < (0.8 if alive else 0.7)


def _al_hadikhia_chooses(d, night, rng, heard):
    """Three players, announced; each chooses life or death in turn, and
    if all three live all three die (21.10.2026).

    A: the row names them. B: one who cannot die tonight counts as
    choosing life and stays when the others go. C: drunk or poisoned, it
    chooses and the names are announced, and nothing happens. D: the same
    player may come up twice. A dead one who chooses life comes back.
    Never itself here, though the rules let it.
    """
    phase = f"N{night}"
    ah = d.demon_at(phase)
    if _exorcised(d, night) or rng.random() < 0.1:
        return []                         # it chose nobody
    others = [p for p in range(d.n) if p != ah]
    dead = [p for p in others if d.deaths.get(p) is not None]
    living = [p for p in others if d.deaths.get(p) is None]
    picks = []
    for _ in range(3):
        if picks and rng.random() < 0.1:
            picks.append(rng.choice(picks))
            continue
        pool = [p for p in (dead if dead and rng.random() < 0.15
                            else living) if p not in picks] \
            or [p for p in others if p not in picks]
        if not pool:
            break
        picks.append(rng.choice(pool))
    if not picks:
        return []
    padded = picks + [None] * (3 - len(picks))
    heard.append(AlHadikhiaChose(night, picks[0], a=padded[0],
                                 b=padded[1], c=padded[2]))
    d.ah_chose = getattr(d, "ah_chose", {})
    d.ah_chose[night] = list(picks)
    working = d.working(ah, night)
    # What each answered, in turn, for the night-walk: the answers are as
    # hidden as a Demon's aim, and the walk works out what they did.
    answers = d.ah_answers = getattr(d, "ah_answers", {})
    answers[night] = []
    killed = []                           # by it, in the order they went

    def tonight():
        return {p for p in picks if d.deaths.get(p) == phase}

    # In turn, and each answer lands at once: a dead one choosing life is
    # standing for the next answer, and one choosing death is down — which
    # moves a Tea Lady's neighbours for whoever answers after.
    for p in picks:
        # A Goon it chose first makes it drunk on the spot, so that choice
        # already fails and nothing after it happens; the Goon turns even
        # if it was drunk before (C: drunk, it still chooses).
        if _the_goon_answers(d, night, ah, p):
            working = False
        if not working:
            continue
        standing = d.deaths.get(p) is None
        # One that died earlier tonight chooses death here: back before
        # dawn, its death and its return would both be unseen, and the
        # solver does not look for a death nobody saw.
        if not standing and d.deaths[p] == phase:
            life = False
        else:
            life = _al_hadikhia_answer(d, p, night, standing, rng)
        answers[night].append((p, life))
        if life and not standing:
            d.ah_from_before = getattr(d, "ah_from_before", {})
            d.ah_from_before.setdefault(night, set()).add(p)
            d.raise_up(p, phase, "AlHadikhia")
        elif not life and standing and not _protected(
                d, night, p, by_exorcist=False, gone=tonight()):
            d.deaths[p] = phase           # B: kept alive counts as life
            killed.append(p)
    if working and all(d.deaths.get(p) is None for p in picks):
        # All three live, so all three die — at once, so who is kept
        # alive is asked of the table before any of them goes.
        going = [p for p in dict.fromkeys(picks)
                 if not _protected(d, night, p, by_exorcist=False)]
        for p in going:
            d.deaths[p] = phase
            killed.append(p)
        d.ah_together = getattr(d, "ah_together", set()) | {night}
    # One dead before tonight, back and down again before dawn, is a night
    # the table saw nothing of (`_nobody_returns_only_to_die`).
    back = getattr(d, "ah_from_before", {}).get(night, set())
    # Only its own: one the Lycanthrope took first is not its kill.
    return [p for p in dict.fromkeys(killed)
            if d.deaths.get(p) == phase and p not in back]


def _al_hadikhia_decides(d, night, rng, heard):
    """The Mastermind's jinx: three good players; all choosing life means
    evil wins, anything else good. The game ends tonight."""
    phase = f"N{night}"
    good = [p for p in d.alive_at(phase)
            if d.side_at(p, phase) == "good" and d.deaths.get(p) is None]
    picks = rng.sample(good, min(3, len(good))) if good else []
    padded = picks + [None] * (3 - len(picks))
    if picks:
        heard.append(AlHadikhiaChose(night, picks[0], a=padded[0],
                                     b=padded[1], c=padded[2]))
    lives = all(_al_hadikhia_answer(d, p, night, True, rng) for p in picks)
    d.ended_at = phase
    d.ended_why = "al-hadikhia: evil" if picks and lives \
        else "al-hadikhia: good"
    d.game_ends_after = night


def _heir(d, phase, rng):
    """Who catches the Demon when it dies at this phase.

    The Scarlet Woman takes it whenever her own condition holds — alive,
    with five or more players left. Otherwise the Storyteller passes the
    star to any living Minion.
    """
    alive = [p for p in d.alive_at(phase) if p != d.demon_at(phase)]
    minions = [m for m in alive if TEAM[d.role_at(m, phase)] == "minion"]
    if not minions:
        return None
    sw = [m for m in minions if d.roles[m] == "ScarletWoman"]
    if sw and len(d.alive_at(phase)) >= 5:
        return sw[0]
    return rng.choice(minions)


def play(n, rng, nights=1, starpass_chance=0.0, allow_takeover=False,
         script=None):
    """Deal a game and play it out, returning (deal, everything heard).

    The order inside a night matters. In Trouble Brewing the Poisoner
    goes first and the Demon kills before the Empath and the Fortune
    Teller wake, so the night's victim is already dead when those two
    read the table.

    `script` decides the bag and, through it, which characters can wake
    at all. What each one *learns* is added a script at a time — asking
    for one whose characters are not built yet gives a legal game with
    very little said in it, which is honest and not much use.
    """
    from botc import scripts as script_mod
    script = script or script_mod.TROUBLE_BREWING
    told = {}
    roles, believes = deal(n, rng, script, told)
    # With a Summoner the Marionette enters play only after the Demon, as
    # its neighbour (their jinx, Patrick 22.10.2026): the token it would
    # believe is a real good character until then, and the seat holding
    # it is only where it would sit if no Demon ever came.
    marionette_slot = None
    if "Summoner" in roles and "Marionette" in roles:
        marionette_slot = roles.index("Marionette")
        roles[marionette_slot] = believes[marionette_slot]
        believes[marionette_slot] = None
    good = [p for p in range(n) if not is_evil(roles[p])]
    # Only when there is a Fortune Teller to have one. The red herring is
    # *that character's* — the Storyteller picks a good player who will
    # register as the Demon to it — so a board without one should not
    # have a red herring at all.
    red_herring = rng.choice(good) if "FortuneTeller" in roles else None
    poisoner = roles.index("Poisoner") if "Poisoner" in roles else None

    d = Deal(roles, believes, red_herring, {}, {}, None)
    d.script = script
    # Lil' Monsta in play: no Demon was dealt (21.10.2026).
    d.lil_monsta = "LilMonsta" in script.keys \
        and not any(TEAM[r] == "demon" for r in roles)
    # The Summoner, and what it made when (21.10.2026).
    d.summoner = roles.index("Summoner") if "Summoner" in roles else None
    d.marionette_slot = marionette_slot
    d.marionette_made = None
    d.summoned = None                   # (night, seat, Demon)
    d.summon_failed = None              # the night it made none
    # The good tokens the Lord of Typhon's or the Kazali's Minions were
    # handed first.
    d.first_tokens = dict(told)
    heard = []
    # "1 player is drunk, even if you die": mostly a Townsfolk, now and
    # then an Outsider, never evil here (10.10.2026).
    if "Puzzlemaster" in roles:
        town = [p for p in range(n) if TEAM[roles[p]] == "townsfolk"]
        outs = [p for p in range(n) if TEAM[roles[p]] == "outsider"
                and roles[p] != "Puzzlemaster"]
        pool = town if (town and (not outs or rng.random() < 0.8)) else outs
        if pool:
            d.puzzle_drunk = rng.choice(pool)
    _the_eighth_five_set_up(d, rng)
    _the_seventh_five_set_up(d, rng)

    for night in range(1, nights + 1):
        d.nights_played = night
        living = d.alive_at(f"N{night}")
        # Lil' Monsta's first babysitter, at 15: before the Poisoner and
        # the Snake Charmer, who may choose it.
        if d.lil_monsta and night == 1:
            _minions_choose(d, 1, rng, heard)
        # The Preacher acts before every Minion (14, then 6), so a Minion
        # it chooses has no ability from tonight (10.10.2026).
        heard += _preacher_preaches(d, night, rng)
        # A Poisoner that catches the star stops being one. The seat was
        # worked out at deal time and never checked again, so a Poisoner
        # promoted to Imp went on poisoning as well as killing — and the
        # solver rightly called those boards impossible, because a Demon
        # poisons nobody.
        #
        # And whoever holds the character *tonight* is the one poisoning
        # — the same thing said properly. On a mixed script a Pit-Hag
        # unmakes a Poisoner and makes one, and the dealt seat went on
        # poisoning as a Philosopher while the new one never did
        # (07.10.2026). Nothing a published script deals moves by this:
        # the only way out of the character there is the star.
        if poisoner is not None or "Poisoner" in script.keys:
            poisoner = next((p for p in living
                             if d.role_at(p, f"N{night}") == "Poisoner"),
                            None)
        # And only with its ability: a Poisoner the Widow poisoned on the
        # first night poisons nobody while that lasts (10.10.2026). It
        # poisoned all the same, and the night-walk, which asks, found a
        # Monk nobody had told it about.
        if (poisoner is not None and poisoner in living
                and (d.demon_at(f"N{night}") != poisoner
                     or _babysits(d, poisoner, f"N{night}"))
                and d.working(poisoner, night)):
            d.poisoned[night] = rng.choice(living)
            d.poisoned_by[night] = poisoner

        # An Organ Grinder chooses whether to be drunk until dusk. Its own
        # business: nothing else reads it, and a Mathematician does not
        # count it (10.10.2026). Nothing is drawn on a script without one.
        if "OrganGrinder" in script.keys:
            grinder = next((p for p in living
                            if d.role_at(p, f"N{night}") == "OrganGrinder"),
                           None)
            if grinder is not None and rng.random() < 0.3:
                d.grinder_drunk.add(night)

        # A Pukka's token carries into the night: whoever it poisoned
        # stays poisoned until the Pukka has had its turn.
        _pukka_token_carries(d, night)

        # A Monk guards somebody from the Demon; a Witch curses somebody
        # who dies if they nominate. Neither is announced, so neither has
        # a row — they are hidden choices the Storyteller writes down,
        # like the Poisoner's.
        #
        # Both were dealt and never acted, which meant the night-walk's
        # rules for them had nothing to check against.
        _monk_guards(d, night, rng)
        _witch_curses(d, night, rng)

        # Choices made before the Demon swings — an Innkeeper's guard, a
        # Monk's, a Sailor's drunk. By slot they are at 9, 12 and 4, so
        # they must exist before any kill is worked out.
        #
        # This sat after the kills at first, which is worth recording:
        # `_protected` was asked whether a seat was guarded while the
        # guard was still `None`, so it always said no and the Innkeeper
        # protected nobody. The rule was right and the moment was wrong.
        heard += early_choices(d, night, rng)
        # A Lleech made since chooses its host tonight; the Harpy at 18
        # (27 the first night), before every Demon (11.10.2026).
        _lleech_picks_a_host(d, night, rng)
        _harpy_chooses(d, night, rng, heard)
        # The Mezepheles at 18 too: whoever said its word turns evil.
        _mezepheles_turns(d, night, rng)
        # The Summoner at 19, after the Scarlet Woman and before the
        # Lunatic, the Exorcist and every Demon (21.10.2026).
        if d.summoner is not None:
            _summoner_summons(d, night, rng, heard)

        # A Pukka poisons on the *first* night and kills from the
        # second, so it is the one Demon that acts before anybody else
        # does. Skipping night one entirely put its poison a night late
        # and left night two with nobody dying — a board the solver
        # rightly called impossible.
        if night == 1 and d.roles[d.demon_at("N1") or 0] == "Pukka":
            _demon_kills(d, night, rng)

        # The Lycanthrope at 22, before every Demon: a good player it
        # takes means the Demon kills nobody tonight (11.10.2026).
        heard += _lycanthrope_hunts(d, night, rng)

        # The Mastermind's jinx: an Al-Hadikhia executed yesterday with a
        # living Mastermind chooses three good players tonight, and that
        # decides the game (21.10.2026).
        if getattr(d, "ah_final_night", None) == night:
            _al_hadikhia_decides(d, night, rng, heard)
            break

        if night > 1:
            demon = d.demon_at(f"N{night}")
            heir = _heir(d, f"N{night}", rng)
            # A Princess that had her nominee executed yesterday: the
            # Demon kills nobody tonight, itself included (10.10.2026).
            if heir is not None and rng.random() < starpass_chance \
                    and d.role_at(demon, f"N{night}") == "Imp" \
                    and not _the_princess_stops(d, night):
                # The Imp kills itself and the star passes on. This always
                # leaves a body, so it can never make a night quiet.
                d.deaths[demon] = f"N{night}"
                d.handovers.append((f"N{night}", heir))
                d.changes.append((f"N{night}", heir, d.roles[demon]))
            else:
                # An Al-Hadikhia's three choose for themselves; whoever
                # dies of it has died to the Demon all the same, and a
                # Grandmother grieves (21.10.2026).
                aimed = (_al_hadikhia_chooses(d, night, rng, heard)
                         if _al_hadikhia_acts(d, night)
                         else _lil_monsta_night(d, night, rng, heard)
                         if d.lil_monsta
                         else _demon_kills(d, night, rng))
                # What it *aimed* at, kept for the replay: a Shabaloth
                # kill sunk into a corpse leaves no body, so reading the
                # deaths back gives an incomplete assignment.
                d.demon_killed[night] = list(aimed)
                d.demon_aimed.setdefault(night, list(aimed))
                for victim in aimed:
                    d.deaths[victim] = f"N{night}"
                    # A Grandmother whose grandchild the Demon takes goes
                    # with it. The simulator dealt Bad Moon Rising games
                    # without this and produced boards the solver called
                    # impossible — correctly, since a living Grandmother
                    # beside a dead grandchild is not a legal world.
                    for info in heard:
                        if type(info).__name__ != "GrandmotherInfo":
                            continue
                        if info.target != victim:
                            continue
                        gran = info.player
                        # The grandchild she has *now*. One who died and
                        # came back is a new Grandmother with a new
                        # grandchild; the old one is nothing to her. And
                        # on the night she returns she has none yet.
                        if info is not _grandchild_row(heard, gran, night) \
                                or d.back_at(gran, f"N{night}") is not None:
                            continue
                        # Working, not merely unpoisoned: a Courtier's drunk
                        # Grandmother does not die of grief either
                        # (29.09.2026).
                        # And able to die at all: a Tea Lady beside her,
                        # or an Innkeeper's pick, stops grief like
                        # anything else. The night-walk had that right.
                        if _acts_as(d, gran, "Grandmother", f"N{night}") \
                                and gran in d.alive_at(f"N{night}") \
                                and d.deaths.get(gran) is None \
                                and d.working(gran, night) \
                                and not _kept_alive_by_a_tea_lady(
                                    d, gran, f"N{night}"):
                            d.deaths[gran] = f"N{night}"
                # "If the Demon kills you, all players learn this" — that
                # a Banshee died, not which seat. Only one whose ability
                # was working: a poisoned Banshee goes quietly.
                for victim in aimed:
                    held = d.role_at(victim, f"N{night}")
                    if (held == "Banshee" or (
                            held == "Philosopher"
                            and d.philosophies.get(victim) == "Banshee")) \
                            and d.working(victim, night):
                        heard.append(BansheeAnnounced(night, victim))

        # Board-changing steps run **before** the readings, because by
        # slot they happen before every character that reads.
        #
        #     Acrobat 39   Barber 40   Farmer 48
        #     Empath 53   Oracle 59   Mathematician 71
        #
        # They used to run after, and it cost a real bug: a Barber swap
        # recorded at N2 made a seat a Pit-Hag *after* the Mathematician
        # had counted, and because a change is stamped with a phase and
        # not a slot, it back-dated to the start of the night. The
        # Mathematician's row was then computed against a board that no
        # longer existed.
        #
        # Worth naming as a class: **a phase is not an instant.** `N2`
        # covers seventy-odd slots, so two things on the same night are
        # indistinguishable to `phase_index`. Ordering the code is the
        # cheap fix; the night-walk is the real one, because it holds one
        # state and moves forward through it.
        # These are the night's own consequences, so they happen on every
        # night including the last. The guard below is for the *day* that
        # follows, and a day after the final night never comes.
        #
        # Sitting under that guard meant an Acrobat never fell on the
        # last night, a Moonchild never took anybody, and a Tinker never
        # went — eight of thirty-eight acrobat nights disagreed with the
        # night-walk because of it.
        if True:
            # An Acrobat whose pick turned out droisoned falls. The rule
            # is "are *or become* droisoned tonight", so this waits for
            # the night's droisoning to be settled.
            # A Moonchild that died in daylight named somebody; if they
            # are good, they die tonight. Acts at 50, after the Demon, so
            # it can add a body the Demon did not take.
            #
            # A Tinker may simply go, and the Storyteller decides when.
            # Both were dealt and never acted at all.
            # The three that kill besides the Demon, in the order they
            # act: Assassin 36, Godfather 37, Gossip 38.
            _assassin_strikes(d, night, rng)
            _godfather_kills(d, night, rng)
            _gossip_comes_true(d, night, rng)
            # A Professor raises a dead Townsfolk, once. At 43: after
            # every Demon, before the Tinker and the Moonchild.
            #
            # Not once two are left standing. Evil won at that moment,
            # and nobody is brought back into a game that is over.
            if not _evil_has_won(d, f"N{night}"):
                _professor_raises(d, night, rng)
            _moonchild_takes_one(d, night, heard, rng)
            _tinker_may_go(d, night, rng)

            _acrobat_may_fall(d, night, heard, rng)

            # A Farmer that fell in the night hands the character on.
            # Done after every death is recorded, because it fires on
            # *any* night death — a Gossip kill, an Assassin, a Pukka's
            # poison — not only the Demon's.
            _farmer_hands_it_on(d, night, rng)

            # A Barber that died today lets the Demon swap two players
            # tonight — characters only, so a swapped player keeps their
            # own side and a good seat can end up holding a Minion's
            # character.
            #
            # The solver has modelled this since the Barber went in and
            # the simulator never fired it, so no played game ever
            # contained one. Found by somebody reading a transcript and
            # asking why a Barber execution on day 1 produced nothing on
            # night 2.
            heard += _barber_swap(d, night, rng)

            # The Huntsman at 45, after the Barber: a Damsel it finds is a
            # Townsfolk not in play before anybody reads (10.10.2026).
            heard += _huntsman_hunts(d, night, rng)

        # A Lleech whose host died tonight dies with it — or tonight, if
        # it is working again after its host went while it was not.
        if _lleech_follows(d, f"N{night}", night, rng):
            d.ended_at, d.ended_why = f"N{night}", "lleech"
            d.game_ends_after = night
            break

        _nobody_returns_only_to_die(d, night)

        # The Cult Leader takes a living neighbour's side at 48, then 66:
        # after every kill, before the Chambermaid counts who woke. Its
        # new side is dated from the day, so tonight's readings see the
        # old one, as they do at the table (11.10.2026).
        _cult_leader_turns(d, night, rng)

        heard += [row for row in honest_info(d, night, rng)
                  if d.role_at(row.player, f"N{night}") not in CHOOSES_EARLY]
        # What an ability put in somebody else's mouth: the player a
        # Nightwatchman woke, saying so.
        heard += d.said_by_others
        d.said_by_others = []

        # The Ogre picks late on its first night, after every reading.
        if night == 1:
            _ogre_picks(d, heard, rng)
        _cerenovus_maddens(d, night, heard, rng)

        # Dawn, and just two players alive: evil has won and the game
        # stops here. It used to run on — three more nights with one
        # player left — and every measurement taken over several nights
        # counted those as games (04.10.2026). The night itself is played
        # to its end, so the record of the last night is a whole one.
        # Lil' Monsta's babysitter killed in the night by something else:
        # good has won at dawn, or the Scarlet Woman babysits from now.
        if d.lil_monsta and _lil_monsta_check(d, f"N{night}"):
            d.ended_at, d.ended_why = d.lm_fallen, "lil monsta"
            d.game_ends_after = night
            break
        # No Demon came, or none can come now: good has won.
        if d.summoner is not None and _summoner_check(d, night):
            d.game_ends_after = night
            break
        if _evil_has_won(d, f"N{night}"):
            d.ended_at, d.ended_why = f"N{night}", "two alive"
            d.game_ends_after = night
            break

        if night < nights:
            # A Savant visits the Storyteller in daylight.
            _savant_visits(d, night, heard, rng)
            # So may a Fisherman, once a game (12.10.2026).
            _fisherman_visits(d, night, heard, rng)

            # The day happens first: nominations, then votes, then the
            # execution that follows from them.
            # A public guess at the evil team, before the day's business.
            # If it lands, good wins and the game stops there — so the
            # record ends rather than running on, which is the same rule
            # that stopped a Pit-Hag unmaking the Demon and the game
            # carrying on for two more nights.
            if _alsaahir_guesses(d, night, rng, heard):
                break

            # The fourth four (10.10.2026): a Vizier is announced on its
            # first day, a Minion may guess the Damsel, and an Organ
            # Grinder may have everybody vote with their eyes closed.
            _vizier_is_announced(d, night, heard)
            # The eighth five (11.10.2026): a Leviathan is announced on
            # its first day, a Yaggababble says its phrase or does not,
            # somebody may say the Mezepheles's word, and a Cult Leader
            # may call its cult.
            _leviathan_is_announced(d, night, heard)
            _yaggababble_speaks(d, night, rng)
            _mezepheles_hears(d, night, rng)
            _cult_is_called(d, night, rng, heard)
            if _a_minion_guesses_the_damsel(d, night, rng, heard):
                d.ended_at, d.ended_why = f"D{night}", "damsel"
                d.game_ends_after = night
                break

            # A Psychopath may kill somebody in the open, before the
            # nominations (10.10.2026).
            _psychopath_strikes(d, night, rng, heard)
            # A Slayer may shoot, before the nominations (Stelle 59).
            if _slayer_shoots(d, night, rng, heard):
                d.ended_at, d.ended_why = f"D{night}", "slayer"
                d.game_ends_after = night
                break
            _harpy_strikes(d, night, rng, heard)
            if _lleech_follows(d, f"D{night}", night, rng, by_day=True):
                d.ended_at, d.ended_why = f"D{night}", "lleech"
                d.game_ends_after = night
                break
            _puzzlemaster_guesses(d, night, rng, heard)
            _hold_a_day(d, night, rng)
            heard += d.day_heard
            d.day_heard = []
            if night in d.blind_days:
                grinder = next(p for p in d.alive_at(f"E{night}")
                               if d.role_at(p, f"E{night}") == "OrganGrinder")
                heard.append(BlindVote(night, grinder))
            # A Witch's curse can take the third from last in daylight.
            if _evil_has_won(d, f"D{night}"):
                d.ended_at, d.ended_why = f"D{night}", "two alive"
                d.game_ends_after = night
                break
            # A Virgin's nominator was executed on the spot: that was
            # the day's execution (Stelle 59).
            if night in d.virgin_executed:
                executed = d.virgin_executed[night]
                if night in d.walked_because:
                    executed = None
            else:
                executed = _execute(d, night, rng, allow_takeover)
            if executed is not None:
                d.deaths[executed] = f"E{night}"
            # The Lleech's host on the gallows takes the Lleech with it.
            if _lleech_follows(d, f"D{night}", night, rng, by_day=True,
                               hanged=executed):
                d.ended_at, d.ended_why = f"E{night}", "lleech"
                d.game_ends_after = night
                break
            # Roshambo on the gallows: only ever a working Psychopath.
            if night in d.roshambo:
                heard.append(PsychopathRoshambo(night, d.roshambo[night]))
            # A working Boomdandy executed — dead of it or not — explodes,
            # and the game ends with the pointing (10.10.2026).
            boom = executed if executed is not None else (
                d.executions.get(night) if night in d.walked_because
                else None)
            if boom is not None and _boomdandy_explodes(d, night, boom, rng,
                                                        heard):
                d.ended_at, d.ended_why = f"E{night}", "boomdandy"
                d.game_ends_after = night
                break
            # A Goblin that said so and went to the gallows: its team has
            # won, and the game stops there — dead of it or not. An
            # ability that triggers on execution does not need the
            # execution to kill (table ruling, 08.10.2026).
            hanged = executed if executed is not None else (
                d.executions.get(night) if night in d.walked_because
                else None)
            # A Leviathan: the second good player executed, its
            # grandchild on the gallows, or the end of day five, and evil
            # has won (11.10.2026).
            if "Leviathan" in script.keys and _leviathan_takes_the_day(
                    d, night, hanged, rng, heard):
                d.ended_at, d.ended_why = f"E{night}", "leviathan"
                d.game_ends_after = night
                break
            # The Princess's nominee went up: the Demon kills nobody
            # tonight, if she has her ability then.
            picked = d.princess_nominated.get(night)
            if hanged is not None and picked is not None \
                    and picked[1] == hanged:
                d.princess_stop[night + 1] = picked[0]
            if hanged is not None \
                    and _a_goblin_said_so(d, night, hanged, rng, heard):
                d.ended_at, d.ended_why = f"E{night}", "goblin"
                d.game_ends_after = night
                break
            # The Fearmonger nominated its pick and the town executed them:
            # their team loses, dead of it or not (10.10.2026).
            if hanged is not None and _the_fearmonger_wins(d, night, hanged):
                d.ended_at, d.ended_why = f"E{night}", "fearmonger"
                d.game_ends_after = night
                break
            # Lil' Monsta's babysitter died today — on the gallows or
            # otherwise.
            if d.lil_monsta and _lil_monsta_check(d, f"E{night}"):
                d.ended_at, d.ended_why = d.lm_fallen, "lil monsta"
                d.game_ends_after = night
                break
            # The Summoner died today with no Demon made: good has won.
            if d.summoner is not None and _summoner_check(d, night):
                d.game_ends_after = night
                break
            # Or the town hangs one of the last three.
            if _evil_has_won(d, f"E{night}"):
                d.ended_at, d.ended_why = f"E{night}", "two alive"
                d.game_ends_after = night
                break
            # Or it hangs nobody, under a Vortox: "each day, if no-one is
            # executed, evil wins". The solver reads a day like that as
            # proof there was no working Vortox, so a game that ran on
            # past one is a game it is right to refuse.
            if executed is None and night not in d.executions \
                    and _a_vortox_takes_the_day(d, night):
                d.ended_at, d.ended_why = f"E{night}", "vortox"
                d.game_ends_after = night
                break
            # The Mastermind's extra day was this one: whoever went up,
            # or nobody, the game is over now.
            if d.game_ends_after is not None and night >= d.game_ends_after:
                break

    return d, _one_change_a_night(heard)


def _one_change_a_night(heard):
    """Two "Claim changed" rows for one seat on one night become one:
    what it was before the first, what it is after the last. The page
    takes one a night (a Pit-Hag's Klutz handed the Farmer the same
    night, say)."""
    from botc.info import BecameInfo
    first = {}
    out = []
    for row in heard:
        if isinstance(row, BecameInfo):
            key = (row.night, row.player)
            if key in first:
                merged = BecameInfo(row.night, row.player, role=row.role,
                                    was=first[key].was or row.was)
                out[out.index(first[key])] = merged
                first[key] = merged
                continue
            first[key] = row
        out.append(row)
    return out


def _claimed_before(d, seat, phase):
    """What this seat claimed before a change at this moment: the last
    character it was handed, or what it was dealt as it believes it."""
    from botc.info import phase_index
    here = phase_index(phase)
    earlier = [what for when, who, what in d.changes
               if who == seat and phase_index(when) < here]
    return earlier[-1] if earlier else d.apparent(seat)


def _says_it_became(d, night, seat, role, phase, rng):
    """The "Claim changed" row a seat handed a character files (Stelle 58,
    14.10.2026): always when it is good (A, F); an evil one, a Spy made
    the Farmer, may keep its bluff instead (E), and then the row has no
    "was" — what it bluffed is decided later, with the claims."""
    from botc.info import BecameInfo
    if d.side_at(seat, phase) == "good":
        d.said_by_others.append(BecameInfo(
            night, seat, role=role, was=_claimed_before(d, seat, phase)))
        return
    if rng.random() < 0.5:
        if not hasattr(d, "evil_told_became"):
            d.evil_told_became = set()
        d.evil_told_became.add(seat)
        d.said_by_others.append(BecameInfo(night, seat, role=role, was=""))


def _evil_has_won(d, phase):
    """Just two players alive, one of them the Demon: evil wins.

    Counted from who is really standing *now*, in the middle of a phase
    if need be — `alive_at` answers for the start of one. A Zombuul that
    survived its first death is on the board as dead and counts all the
    same: "the game goes on, even with only two alive besides it; evil
    wins when really only two live, it and one other" (the table's rule
    book, 02.10.2026).

    Not during a Mastermind's extra day. The Demon is dead by then, and
    the day is played out however few are left.
    """
    if d.game_ends_after is not None:
        return False
    standing = [p for p in range(d.n)
                if d.deaths.get(p) is None or p == d.zombuul_up]
    return len(standing) <= 2 and d.demon_at(phase) in standing


def _a_vortox_takes_the_day(d, day):
    """Is the Demon a Vortox today, with its ability working?"""
    phase = f"E{day}"
    seat = d.demon_at(phase)
    return (seat is not None and d.role_at(seat, phase) == "Vortox"
            and d.deaths.get(seat) is None
            and d.working(seat, day, by_day=True))


def _ogre_picks(d, heard, rng):
    """The Ogre points at somebody and takes their side, unknowing.

    "Even if drunk or poisoned", so nothing here asks whether it works.
    The jinx says a Spy and a Recluse register as evil to it. Its new
    side counts from the first day, since it acts after the night's
    readings. It announces whom it chose about half the time — which is
    the only way anybody could ever learn it.
    """
    from botc.catalogue import CHARACTERS
    from botc.info import OgreChoice
    # The holder, then a Philosopher that took it: it chooses on the night
    # it took it, the first (ruling G, 13.10.2026).
    ogres = [d.seat_of("Ogre")] + [
        p for p in sorted(d.philosophies) if _took(d, p, "Ogre", "N1")]
    for ogre in ogres:
        if ogre is None:
            continue
        target = rng.choice([p for p in range(d.n) if p != ogre])
        role = d.role_at(target, "N1")
        if d.side_at(target, "N1") == "evil" \
                or {"minion", "demon"} & CHARACTERS[role].registers:
            d.side_changes.append(("D1", ogre, "Ogre", "evil"))
        if rng.random() < 0.5:
            heard.append(OgreChoice(1, ogre, target=target))


def _moonchild_takes_one(d, night, heard, rng):
    """It named somebody on learning it died, and tonight they die — if
    they were good.

    "When you learn that you died": on the spot if it went in daylight,
    at dawn if it went in the night. Either way the pick lands on the
    night that follows, which for a Moonchild killed on night two is
    night three. Only the daylight half was played here, so a Moonchild
    the Demon took never named anybody (03.10.2026).

    The choice is public, so it is on the record whether or not it does
    anything. What decides that is the Moonchild's state **tonight**, not
    when it chose: "drunk or poisoned at night but sober and healthy when
    they chose a player today, that player doesn't die" — and the other
    way round they do. This asked about the day, and wrote nothing down
    for a Moonchild that was not working then.
    """
    phase = f"N{night}"
    day = night - 1
    if day < 1:
        return
    for seat in range(d.n):
        # Or a Philosopher that took it (13.10.2026).
        if not _acts_as(d, seat, "Moonchild", f"D{day}"):
            continue
        if d.deaths.get(seat) not in (f"N{day}", f"D{day}", f"E{day}"):
            continue
        # Alive when it chose, which was in daylight: not somebody who
        # only came back tonight.
        others = [p for p in d.alive_at(phase)
                  if p != seat and d.back_at(p, phase) is None]
        if not others:
            continue
        target = rng.choice(others)
        heard.append(MoonchildChoice(night, seat, target=target))
        d.moonchild_picked[night] = target
        if not d.working(seat, night):
            continue
        if d.side_at(target, f"D{day}") != "good":
            continue
        # Made the Demon tonight, before the Moonchild's turn: evil by
        # then (21.10.2026).
        made = getattr(d, "summoned", None)
        if made is not None and made[:2] == (night, target):
            continue
        if d.deaths.get(target) is not None:
            continue                      # the Demon got there first
        if d.back_at(target, phase) is not None:
            continue                      # as with the Tinker, below
        if _kept_alive_by_a_tea_lady(d, target, phase) \
                or _a_fool_shrugs_it_off(d, target, phase):
            continue
        d.deaths[target] = phase


def _the_goon_answers(d, night, chooser, target):
    """Has `chooser` just been made drunk, by choosing the Goon first?

    "Each night, the 1st player to choose you with their ability is drunk
    until dusk. You become their alignment." Drunk **at once**, so the
    choice that did it already fails: a Shabaloth that takes the Goon
    first and somebody else second kills neither. And the Goon turns even
    when its chooser was already drunk or poisoned.

    Only a player choosing a player counts — not the Storyteller picking
    for a Gossip or a Tinker, not a Moonchild pointing in daylight. A
    Courtier naming the Goon's character does count: the wiki's Goon page
    has exactly that (table ruling, 08.10.2026), and so does an Ojo. A dead Goon has no ability, and a
    droisoned one does nothing.

    Dealt in a quarter of all games and never played until 03.10.2026.
    """
    phase = f"N{night}"
    if night in d.goon_first or target is None or chooser == target:
        return False
    # Or a Philosopher that took it: it turns as well (ruling G,
    # 13.10.2026).
    if not _acts_as(d, target, "Goon", phase) \
            or d.deaths.get(target) is not None:
        return False
    if not d.working(target, night):
        return False
    d.goon_first[night] = (chooser, target)
    side = d.side_at(chooser, phase)
    if d.side_at(target, phase) != side:
        d.side_changes.append((phase, target, "Goon", side))
    return True


def _stands_to_act(d, seat, role, night):
    """Holding this character tonight, and not dead before its turn."""
    phase = f"N{night}"
    return (d.role_at(seat, phase) == role and seat in d.alive_at(phase)
            and d.deaths.get(seat) is None)


def _good_and_standing(d, night, but=()):
    phase = f"N{night}"
    # Never Lil' Monsta's babysitter: the Minions know who it is.
    sitter = d.babysat.get(night) if d.babysat else None
    return [p for p in d.alive_at(phase)
            if d.deaths.get(p) is None and p not in but and p != sitter
            and d.side_at(p, phase) == "good"]


def _assassin_strikes(d, night, rng):
    """Once a game, a player dies — "even if for some reason they could
    not". Nothing stops it: not a Tea Lady, not a sober Sailor, not a
    Fool's free death, not the Innkeeper's pair.

    Except the Assassin's own state. Drunk or poisoned, nothing happens
    and the ability is gone all the same.

    The Goon is the one wrinkle: chosen by a working Assassin it dies
    *and* turns evil; chosen by one that was already drunk it lives, and
    turns evil.
    """
    if night < 2:
        return
    phase = f"N{night}"
    for seat in range(d.n):
        if seat in d.assassin_chose \
                or not _stands_to_act(d, seat, "Assassin", night):
            continue
        targets = _good_and_standing(d, night, but=(seat,))
        if not targets or rng.random() >= 0.3:
            continue
        target = rng.choice(targets)
        d.assassin_chose[seat] = night
        d.assassin_aimed[night] = target
        able = d.working(seat, night)
        _the_goon_answers(d, night, seat, target)
        if able:
            d.deaths[target] = phase


def _godfather_kills(d, night, rng):
    """An Outsider died today, so tonight the Godfather takes somebody.

    In daylight only — by execution or otherwise — and one kill however
    many Outsiders went. A death like any other: what keeps a seat alive
    keeps it alive from this.
    """
    if night < 2:
        return
    phase, day = f"N{night}", night - 1
    if not any(TEAM[d.role_at(who, f"D{day}")] == "outsider"
               for who in d.died_on(f"D{day}", f"E{day}")):
        return
    for seat in range(d.n):
        if not _stands_to_act(d, seat, "Godfather", night):
            continue
        targets = _good_and_standing(d, night, but=(seat,))
        if not targets:
            continue
        target = rng.choice(targets)
        d.godfather_aimed[night] = target
        if _the_goon_answers(d, night, seat, target) \
                or not d.working(seat, night):
            continue
        if _kept_alive_by_a_tea_lady(d, target, phase) \
                or _a_fool_shrugs_it_off(d, target, phase):
            continue
        d.deaths[target] = phase


def _gossip_comes_true(d, night, rng):
    """It said something true today, so tonight a player dies.

    The Storyteller chooses who. What counts is the Gossip's state
    tonight: said while drunk and sober now, somebody dies; dead or
    droisoned now, nobody does.

    Never somebody who could not die anyway — a true statement would
    then look exactly like a false one — and never the Demon, which
    would end the game.
    """
    if night < 2:
        return
    phase, day = f"N{night}", night - 1
    for seat in range(d.n):
        if not _stands_to_act(d, seat, "Gossip", night) \
                and not (_took(d, seat, "Gossip", phase)
                         and seat in d.alive_at(phase)
                         and d.deaths.get(seat) is None):
            continue
        if seat not in d.alive_at(f"E{day}"):
            continue                      # back tonight: it said nothing today
        if not d.working(seat, night) or rng.random() >= 0.3:
            continue
        demon = d.demon_at(phase)
        able_to_die = [
            p for p in d.alive_at(phase)
            if d.deaths.get(p) is None and p != demon
            and d.back_at(p, phase) is None
            and not _kept_alive_by_a_tea_lady(d, p, phase)
            and not _an_innkeeper_or_sailor_keeps(d, night, p)
            and not (_acts_as(d, p, "Fool", phase) and p not in d.fool_spent
                     and d.working(p, night))]
        if not able_to_die:
            continue
        target = rng.choice(able_to_die)
        d.gossip_killed[night] = target
        d.deaths[target] = phase


def _nobody_returns_only_to_die(d, night):
    """Up and down again before dawn is a night the table saw nothing of.

    A Grandmother regurgitated just before the Shabaloth takes her
    grandchild dies of it there and then. By morning she is as dead as
    she was the evening before, and nobody announces a return that did
    not last the night — so the record keeps her first death and drops
    the rest. Without this the two events shared one moment, and "back
    at night three, dead at night three" read as alive.
    """
    phase = f"N{night}"
    for seat, at, by in list(d.resurrections):
        if at != phase or d.deaths.get(seat) != phase:
            continue
        d.resurrections.remove((seat, at, by))
        before = [x for x in d.earlier_deaths if x[0] == seat][-1]
        d.earlier_deaths.remove(before)
        d.deaths[seat] = before[1]
        if d.regurgitated.get(night) == seat:
            del d.regurgitated[night]
        if d.professor_raised.get(night) == seat:
            del d.professor_raised[night]


def _grandchild_row(heard, gran, night):
    """The reading that makes somebody this Grandmother's grandchild
    tonight: her latest from before tonight. (On the first night, the
    one she is given — nobody dies then anyway.)"""
    rows = [h for h in heard
            if type(h).__name__ == "GrandmotherInfo" and h.player == gran
            and (h.night < night or night == 1)]
    return rows[-1] if rows else None


def _a_fool_shrugs_it_off(d, seat, phase):
    """A working Fool's first death does not happen — and then it is gone.

    Asked last, after everything else that might have kept the seat
    alive: a Fool the Monk was guarding has not used anything up.

    Never played at all until executions could be survived (03.10.2026):
    the town simply did not pick the Fool, and the Demon killed it like
    anybody else.
    """
    if not _acts_as(d, seat, "Fool", phase) or seat in d.fool_spent:
        return False
    if not d.working(seat, int(phase[1:]), by_day=phase[0] != "N"):
        return False
    d.fool_spent[seat] = phase
    d.fool_spent_ever.append((seat, phase))
    return True


def _professor_raises(d, night, rng):
    """Once a game, a dead player — and if they are a Townsfolk, they live.

    Anybody else and nothing happens, and the ability is gone all the
    same; drunk or poisoned and nothing happens either. So the table sees
    a Professor's choice only when it worked.

    Never somebody who died tonight: the Storyteller shakes their head at
    a player who is not dead yet as far as the Professor can know.

    Mostly a Townsfolk, because a table usually knows which of its dead
    is worth having back.
    """
    if night < 2:
        return
    phase = f"N{night}"
    for seat in range(d.n):
        # Or a Philosopher that took it (13.10.2026).
        if not _acts_as(d, seat, "Professor", phase) \
                or seat in d.professor_chose:
            continue
        if seat not in d.alive_at(phase) or d.deaths.get(seat) == phase:
            continue                      # dead before its turn came
        dead = [p for p in range(d.n)
                if d.deaths.get(p) is not None and d.deaths[p] != phase
                and p != d.zombuul_up]
        if not dead or rng.random() >= 0.5:
            continue
        worth = [p for p in dead if TEAM[d.role_at(p, phase)] == "townsfolk"]
        target = rng.choice(worth if worth and rng.random() < 0.7 else dead)
        d.professor_chose[seat] = night
        if not d.working(seat, night):
            continue
        if TEAM[d.role_at(target, phase)] != "townsfolk":
            continue
        d.raise_up(target, phase, "Professor")
        d.professor_raised[night] = target


def _tinker_may_go(d, night, rng):
    """It dies when the Storyteller says, which is not often."""
    phase = f"N{night}"
    for seat in range(d.n):
        # Or a Philosopher that took it (13.10.2026).
        if not _acts_as(d, seat, "Tinker", phase):
            continue
        if seat not in d.alive_at(phase):
            continue
        # Not on the night it came back: down, up and down again before
        # dawn is a night the table sees nothing of.
        if d.back_at(seat, phase) is not None:
            continue
        # The one a Philosopher took it from is drunk, so it does not go
        # by its ability; asked after the dice, which stay as they were.
        if rng.random() < 0.15 and not _kept_alive_by_a_tea_lady(
                d, seat, phase) \
                and not _drunk_by_its_philosopher(d, seat, "Tinker", phase):
            d.deaths.setdefault(seat, phase)


def _witch_curses(d, night, rng):
    """Whoever it points at dies if they nominate tomorrow.

    Acts at 14. Nothing happens tonight — the curse is a day matter — but
    the aim is taken now, which is why the walk records it at the slot
    rather than at the moment it bites.

    Stops once only one player is left alive besides the Witch, and a
    droisoned Witch curses nobody.
    """
    phase = f"N{night}"
    # Alive, or killed by a Vigormortis: "Minions you kill keep their
    # ability". A dead Witch stopped cursing here whatever killed it.
    witch = next((p for p in range(d.n)
                  if d.role_at(p, phase) == "Witch"
                  and _has_its_ability(d, p, phase)), None)
    if witch is None or not d.working(witch, night):
        return
    others = [p for p in d.alive_at(phase) if p != witch]
    # "If just 3 players live, you lose this ability."
    if len(d.alive_at(phase)) > 3 and len(others) >= 2:
        d.cursed[night] = rng.choice(others)
        d.cursed_by[night] = witch


def _has_its_ability(d, seat, phase):
    """Alive — or a Minion a Vigormortis killed, which keeps what it had."""
    if seat in d.alive_at(phase):
        return True
    return _a_vigormortis_killed(d, seat, phase)


def _a_vigormortis_killed(d, seat, phase):
    """Did the Vigormortis that is still about kill this Minion at night?"""
    gone = d.deaths.get(seat)
    if not gone or gone[0] != "N" or phase_index(gone) > phase_index(phase):
        return False
    if TEAM[d.role_at(seat, phase)] != "minion":
        return False
    killer = d.demon_at(gone)
    if killer is None or d.role_at(killer, gone) != "Vigormortis":
        return False
    if seat not in d.demon_killed.get(int(gone[1:]), ()):
        return False
    now = d.demon_at(phase)
    return now is not None and now in d.alive_at(phase) \
        and d.role_at(now, phase) == "Vigormortis"


def _devils_advocate_picks(d, night, rng):
    """Somebody who will not die if the town executes them tomorrow.

    Every night including the first, a living player, and never the one
    it chose the night before. Hidden, like the Monk's guard: the table
    learns of it only when somebody walks away from the gallows.

    It looks after its own. Most nights that is the Demon.
    """
    phase = f"N{night}"
    advocate = next((p for p in range(d.n)
                     if d.role_at(p, phase) == "DevilsAdvocate"
                     and p in d.alive_at(phase)), None)
    if advocate is None:
        return
    before = d.spared.get(night - 1)
    last = before[1] if before and before[0] == advocate else None
    # Not a Zombuul lying under a shroud: it registers as dead.
    living = [p for p in d.alive_at(phase) if p != last]
    if not living:
        return
    evil = [p for p in living if d.side_at(p, phase) == "evil"]
    demon = d.demon_at(phase)
    if demon in living and rng.random() < 0.5:
        target = demon
    elif evil and rng.random() < 0.5:
        target = rng.choice(evil)
    else:
        target = rng.choice(living)
    # Chosen either way, so "different to last night" counts a night it
    # was drunk; but a drunk Advocate's choice protects nobody.
    d.spared[night] = (advocate, target)
    _the_goon_answers(d, night, advocate, target)


def _monk_guards(d, night, rng):
    """A Monk keeps one player safe from the Demon tonight.

    Acts at slot 12, before every Demon, which is the whole point: the
    Demon arrives later and finds the seat protected.

    A droisoned Monk guards nobody — a plain ability does not function.
    """
    if night < 2:
        return
    phase = f"N{night}"
    # The first working one: the holder, or a Philosopher that took it
    # while the holder is drunk (13.10.2026).
    monk = next((p for p in _holders(d, "Monk", phase)
                 if p in d.alive_at(phase) and d.working(p, night)), None)
    if monk is None:
        return
    others = [p for p in d.alive_at(phase) if p != monk]
    if others:
        d.monk_guarded[night] = rng.choice(others)
        _chose(d, "Monk", night, monk, d.monk_guarded[night])


def _acrobat_may_fall(d, night, heard, rng):
    """An Acrobat whose pick was droisoned tonight dies.

    A droisoned Acrobat does not: a plain ability simply does not
    function. And a Tea Lady beside it keeps it alive, because her
    neighbours cannot die at all — which by the rules counts as an
    ability *prevented*, and so as one that went wrong.
    """
    # The pick is made **here**, not read out of `heard`.
    #
    # An Acrobat acts at slot 39: after the Demon at 24, before the
    # readings at 53. Its row used to come from `honest_info`, which runs
    # later — so this scanned `heard` for a row that did not exist yet
    # and never killed anybody. Thirty of thirty-eight nights agreed with
    # the night-walk and the eight that did not were all this.
    #
    # Sitting between the two passes is the honest place for it, and the
    # cost is that it makes its own choice rather than being handed one.
    phase = f"N{night}"
    droisoned = droisoned_at(d, night)
    for seat in range(d.n):
        # Or a Philosopher that took it (13.10.2026).
        if not _acts_as(d, seat, "Acrobat", phase) or night < 2:
            continue
        if seat not in d.alive_at(phase):
            continue
        others = [p for p in range(d.n) if p != seat]
        if not others:
            continue
        row = AcrobatChoice(night, seat, target=rng.choice(others))
        heard.append(row)
        if seat not in d.alive_at(phase):
            continue
        if not d.working(seat, night):
            continue                      # droisoned: it does not function
        # Preached is no ability, not drunk: it does not fell an Acrobat
        # (10.10.2026) — unless something else droisoned that Minion too.
        if row.target not in droisoned or (
                row.target in _preached(d, night)
                and row.target not in _droisoned_without_preaching(d,
                                                                   night)):
            continue                      # the pick was fine
        if _kept_alive_by_a_tea_lady(d, seat, phase):
            continue                      # prevented, not failed
        d.deaths.setdefault(seat, phase)


def _kept_alive_by_a_tea_lady(d, seat, phase):
    """Both her living neighbours good, so neither of them **can die**.

    Full stop, and it does not matter where the death comes from — a
    Demon, a Gambler's wrong guess, an Acrobat's droisoned pick, a Tinker
    simply going. Settled at the table.

    This was reached only by the Acrobat, so a Tinker died beside a
    working Tea Lady and the solver — which applies her shield to every
    cause — had to demand she was impaired, with nothing able to impair
    her. That board had no legal world.
    """
    from botc.roles import TEAM
    # And the two others that keep somebody alive whatever the death is:
    # a sober Sailor cannot die, and neither can the pair a working
    # Innkeeper chose tonight. Only the Tea Lady was asked, so a Gambler
    # the Innkeeper had just protected guessed wrong and died of it — the
    # Innkeeper acts first, so its guard already stands. Nothing showed
    # it until the solver held a recorded Innkeeper to its word
    # (02.10.2026).
    if phase[0] == "N":
        night = int(phase[1:])
        if _acts_as(d, seat, "Sailor", phase) and d.working(seat, night):
            return True
        # Still standing: an Innkeeper the Demon took at 27 keeps nobody
        # from a Moonchild's pick at 50. The same for a Tea Lady, below.
        # (A Gambler at 10 asks before anybody has died.)
        if _an_innkeeper_guards(d, night, seat, standing=True):
            return True
    for lady in range(d.n):
        if not _acts_as(d, lady, "TeaLady", phase):
            continue
        if lady not in d.alive_at(phase) or not d.working(
                lady, int(phase[1:]), by_day=phase[0] != "N") \
                or d.deaths.get(lady) is not None:
            continue
        around = []
        for step in (1, -1):
            for gap in range(1, d.n):
                other = (lady + step * gap) % d.n
                if other == lady:
                    break
                if other in d.alive_at(phase) \
                        and d.deaths.get(other) is None:
                    around.append(other)
                    break
        if seat in around and len(around) >= 2 \
                and all(d.side_at(p, phase) == "good" for p in around):
            return True
    return False


def _farmer_hands_it_on(d, night, rng):
    """A Farmer that died tonight makes somebody else the Farmer.

    Any night death does it, not only the Demon's. Not an execution, and
    not while droisoned — a droisoned *information* role yields whatever
    the Storyteller likes, because the information is arbitrary, but a
    plain ability simply does not function, and handing the character on
    is a plain ability.

    Chosen by **registration**: a Spy registers as good, so a Spy may be
    made the Farmer, and it stays evil. An evil Farmer is a real thing.

    It chains, because the new Farmer is a new instance — so this looks
    at whoever holds the character now rather than at whoever was dealt
    it.
    """
    from botc.catalogue import CHARACTERS
    phase = f"N{night}"
    # The holder, or a Philosopher that took it (13.10.2026).
    holders = [p for p in range(d.n)
               if _acts_as(d, p, "Farmer", phase)
               and d.deaths.get(p) == phase]
    for seat in holders:
        if not d.working(seat, night):
            continue                      # droisoned: it does not function
        def good_enough(p):
            role = d.role_at(p, phase)
            # Good now, which a Townsfolk turned evil is not (11.10.2026).
            if not is_evil(role) and d.side_at(p, phase) == "good":
                return True
            return bool({"townsfolk", "outsider"}
                        & CHARACTERS[role].registers)
        # An heir killed the same night hands it on at once, so the next
        # day two may say they became the Farmer, one of them alive
        # (Stelle 58, D, 14.10.2026).
        gone = {seat}
        while True:
            heirs = [p for p in d.alive_at(phase)
                     if p not in gone and good_enough(p)]
            if not heirs:
                break
            # From the day after, like every change that follows an
            # ability working: the Farmer was still the Farmer when it did.
            heir = rng.choice(heirs)
            _says_it_became(d, night, heir, "Farmer", phase, rng)
            d.changes.append((f"D{night}", heir, "Farmer"))
            if d.deaths.get(heir) != phase or not d.working(heir, night):
                break
            gone = gone | {heir}
    # Its jinx with the Leviathan: "a chosen Farmer uses their ability
    # but does not die" (11.10.2026). The new one says so.
    lev, chosen = getattr(d, "lev_chose", {}).get(night, (None, None))
    if chosen is not None and d.role_at(chosen, phase) == "Farmer" \
            and d.deaths.get(chosen) is None and d.working(chosen, night) \
            and d.working(lev, night):
        heirs = [p for p in d.alive_at(phase)
                 if p != chosen and d.deaths.get(p) is None
                 and d.role_at(p, phase) != "Farmer"
                 and d.side_at(p, phase) == "good"]
        if heirs:
            heir = rng.choice(heirs)
            was = d.apparent(heir)
            d.changes.append((f"D{night}", heir, "Farmer"))
            d.said_by_others.append(BecameInfo(night, heir, role="Farmer",
                                               was=was))


def _took(d, seat, role, phase):
    """A Philosopher that took that character, and still the Philosopher
    then. It chooses on its first night, so it has it from night one."""
    return d.role_at(seat, phase) == "Philosopher" \
        and (getattr(d, "philosophies", None) or {}).get(seat) == role


def _drunk_by_its_philosopher(d, seat, role, phase):
    """Was the real holder drunk then, because a living Philosopher had
    taken its character? Alive at a phase includes dying at it."""
    return any(p != seat and _took(d, p, role, phase)
               and p in d.alive_at(phase)
               for p in (getattr(d, "philosophies", None) or {}))


def _falls_as(d, seat, role, phase):
    """Died then as that character with its ability working, as far as a
    Philosopher is concerned: the solver's `info.falls_as` (way 1 of A to
    D, 13.10.2026)."""
    if d.role_at(seat, phase) == role:
        return not _drunk_by_its_philosopher(d, seat, role, phase)
    return _took(d, seat, role, phase)


def _acts_as(d, seat, role, phase):
    """Holding that character then, or a Philosopher that took it."""
    return d.role_at(seat, phase) == role or _took(d, seat, role, phase)


def _answering(d, chooser, role, phase):
    """Whose ability a recorded choice stands on: a Philosopher's own, or
    else the character's holder as the night ends, as it always was — a
    Pit-Hag may have made the one that chose something else after it
    chose (13.10.2026, the gate of group 1)."""
    if _took(d, chooser, role, phase):
        return chooser
    return next((p for p in range(d.n) if d.role_at(p, phase) == role),
                None)


def _holders(d, role, phase):
    """Every seat with that ability then, in seat order."""
    return [p for p in range(d.n) if _acts_as(d, p, role, phase)]


def _chose(d, role, night, seat, what, last=False):
    """Record one holder's choice. Of the dealt holders only one counts a
    night, as it always did — the first, or for the Exorcist the last (a
    Pit-Hag's new Innkeeper choosing after the old one); a Philosopher's
    is kept beside it (13.10.2026)."""
    got = d.chose_by.setdefault((role, night), {})
    base = role.replace("Drunk", "").replace("Void", "")
    phase = f"N{night}"
    if not _took(d, seat, base, phase):
        dealt = [p for p in got if not _took(d, p, base, phase)]
        if dealt and not last:
            return
        for p in dealt:
            del got[p]
    got[seat] = what


def _choices(d, role, night):
    return d.chose_by.get((role, night), {})


def _a_working_monk(d, night, living):
    """The dealt Monk, as always; failing that a Philosopher that took the
    Monk (13.10.2026). Working and alive, or None."""
    monk = d.roles.index("Monk") if "Monk" in d.roles else None
    if monk is not None and monk in living and d.working(monk, night):
        return monk
    phase = f"N{night}"
    return next((p for p in range(d.n) if _took(d, p, "Monk", phase)
                 and p in living and d.working(p, night)), None)


def _an_innkeeper_guards(d, night, target, gone=(), standing=False):
    """Is this seat in the pair of a working Innkeeper — the holder, or a
    Philosopher that took it — alive tonight? `standing`: and not dead
    yet, for a death that comes later in the night."""
    phase = f"N{night}"
    for chooser, pair in _choices(d, "Innkeeper", night).items():
        if target not in pair:
            continue
        if _choices(d, "InnkeeperVoid", night).get(chooser):
            continue
        keeper = _answering(d, chooser, "Innkeeper", phase)
        if keeper is None or keeper in gone \
                or keeper not in d.alive_at(phase):
            continue
        if standing and d.deaths.get(keeper) is not None:
            continue
        if d.working(keeper, night):
            return True
    return False


def _barber_swap(d, night, rng):
    """If a Barber died yesterday, the Demon may swap two seats tonight.

    Characters move and sides do not, which is the whole point of it: a
    good player can wake up holding the Poisoner's character and still be
    good.
    """
    yesterday = night - 1
    # "If you died today **or tonight**": a Barber killed tonight lets the
    # Demon swap tonight, not tomorrow night — the swap is at slot 40,
    # after the kill. This waited a night, where the solver did not
    # (29.09.2026).
    # And a Philosopher that took the Barber; a real one drunk by that
    # Philosopher when it died swaps nothing (13.10.2026).
    died = [p for p in range(d.n)
            if d.deaths.get(p) in (f"D{yesterday}", f"E{yesterday}",
                                   f"N{night}")
            and ((d.role_at(p, f"N{night}") == "Barber"
                  and not _drunk_by_its_philosopher(d, p, "Barber",
                                                    d.deaths[p]))
                 or _took(d, p, "Barber", d.deaths[p]))]
    # At this table the Demon usually swaps, and half the time with one of
    # its own Minions — the Barber's death is loud, the swap is quiet
    # (table habit, 30.09.2026).
    if not died or rng.random() > 0.75:
        return []
    # Alive after tonight's kill, which has already happened: the Barber
    # acts at 40. Swapping the Demon's character into tonight's corpse
    # left a dead Demon and a game that should have ended (29.09.2026).
    living = sorted(p for p in d.alive_at(f"N{night}")
                    if d.deaths.get(p) != f"N{night}")
    if len(living) < 2:
        return []
    phase = f"N{night}"
    demon = d.demon_at(phase)
    minions = [p for p in living if TEAM[d.role_at(p, phase)] == "minion"]
    if demon in living and minions and rng.random() < 0.5:
        a, b = demon, rng.choice(minions)
    else:
        a, b = rng.sample(living, 2)
    got_a = d.role_at(a, phase)
    got_b = d.role_at(b, phase)
    # Lil' Monsta's babysitter keeps the baby: it is the player's, not
    # the character's (21.10.2026).
    sitter = demon if _babysits(d, demon, phase) else None
    d.changes.append((phase, a, got_b))
    d.changes.append((phase, b, got_a))
    # Kept for the night walk, which swaps at the Barber's own slot when
    # it is told who (tests/nightwalk.py).
    if not hasattr(d, "barber_swaps"):
        d.barber_swaps = {}
    d.barber_swaps[night] = (a, b)
    # And the star moves with the character, as with the Snake Charmer.
    if demon in (a, b) and sitter is None:
        d.handovers.append((phase, b if demon == a else a))
    # "Each player learns which character they become." A good player
    # handed a good character says so, often — the one trace a swap leaves
    # when the Barber hid.
    from botc.info import BecameInfo
    told = []
    for seat, was, now in ((a, got_a, got_b), (b, got_b, got_a)):
        if was != now and d.side_at(seat, phase) == "good" \
                and TEAM[now] in ("townsfolk", "outsider") \
                and rng.random() < 0.6:
            told.append(BecameInfo(night, seat, role=now, was=was))
    return told


def _alsaahir_guesses(d, day, rng, heard):
    """A public guess at the whole evil team, once in the day.

    It need not guess every day, and mostly should not — the wiki
    suggests waiting a few days to hide the role. So this guesses
    sometimes, and mostly wrongly, which is the interesting case: a
    failed guess rules out that exact configuration.

    A droisoned Alsaahir simply does not work, so its guess does nothing
    even when right.

    Named by **character type at the time of the guess**, alive or dead.
    A Fang Gu that jumped leaves two Demons to name — the corpse and the
    seat that inherited — and a Pit-Hag can make a Minion that is good.
    """
    phase = f"D{day}"
    for seat in range(d.n):
        # And a Philosopher that took it (group 5, 14.10.2026).
        if not _acts_as(d, seat, "Alsaahir", phase):
            continue
        if seat not in d.alive_at(phase):
            continue
        if rng.random() > 0.35:
            continue                      # most days it says nothing
        real_d, real_m = set(), set()
        for p in range(d.n):
            team = TEAM[d.role_at(p, phase)]
            if team == "demon":
                real_d.add(p)
            elif team == "minion":
                real_m.add(p)
        if rng.random() < 0.25 and real_d:
            demons, minions = real_d, real_m      # a correct guess
        else:
            pool = [p for p in range(d.n) if p != seat]
            demons = set(rng.sample(pool, min(len(real_d) or 1, len(pool))))
            rest = [p for p in pool if p not in demons]
            minions = set(rng.sample(rest, min(len(real_m), len(rest))))
        won = (d.working(seat, day)
               and demons == real_d and minions == real_m)
        heard.append(AlsaahirGuess(day, seat, demons=frozenset(demons),
                                   minions=frozenset(minions), won=won))
        return won
    return False


def _vizier_is_announced(d, day, heard):
    """ "All players know you are the Vizier" — on its first day, and only
    if it has its ability then: one drunk or poisoned that day is never
    announced (table ruling, 10.10.2026). Not at all with an Investigator
    or an Alsaahir on the script (their jinxes)."""
    if "Vizier" not in d.script.keys:
        return
    phase = f"D{day}"
    for seat in d.alive_at(phase):
        if d.role_at(seat, phase) != "Vizier" or seat in d.vizier_seen:
            continue
        d.vizier_seen.add(seat)
        if "Investigator" in d.script.keys or "Alsaahir" in d.script.keys:
            continue
        if d.working(seat, day, by_day=True):
            heard.append(VizierAnnounced(day, seat))


def _a_vizier_stands(d, seat, day):
    """A Vizier cannot die during the day — working, or drunk by a
    Courtier (their jinx). Drunk or poisoned otherwise, it can."""
    if d.role_at(seat, f"D{day}") != "Vizier":
        return False
    if d.working(seat, day, by_day=True):
        return True
    # Preached, it learns so and still cannot die by day (their jinx).
    if seat in _preached(d, day, f"D{day}", by_day=True):
        return True
    return any(holder == seat and when <= day < when + 3
               for when, holder, _courtier in d.courtier_drunks)


def _spy_ever(d):
    """A Spy or a Widow in play, ever: either poisons the Damsel (their
    jinxes; the Widow's 10.10.2026)."""
    return any(r in d.roles or any(became == r
                                   for _at, _who, became in d.changes)
               for r in ("Spy", "Widow"))


def _the_princess_stops(d, night):
    """ "On your 1st day, if you nominated & executed a player, the Demon
    doesn't kill tonight." Her ability is asked at night: alive then, and
    working (10.10.2026)."""
    princess = d.princess_stop.get(night)
    if princess is None:
        return False
    phase = f"N{night}"
    return (_acts_as(d, princess, "Princess", phase)
            and princess in d.alive_at(phase)
            and d.working(princess, night))


def _can_die_by_day(d, seat, day):
    """Would a daylight kill land on this seat? A sober Sailor, a Vizier,
    a Tea Lady's good neighbour and a Fool's first death say no — the
    Fool's spent by the asking, so this is asked last."""
    phase = f"D{day}"
    if _acts_as(d, seat, "Sailor", phase) \
            and d.working(seat, day, by_day=True):
        return False
    if _a_vizier_stands(d, seat, day):
        return False
    if _a_lleech_holds(d, seat, phase, day, by_day=True):
        return False
    if _kept_alive_by_a_tea_lady(d, seat, phase):
        return False
    return not _a_fool_shrugs_it_off(d, seat, phase)


def _psychopath_strikes(d, day, rng, heard):
    """ "Each day, before nominations, you may publicly choose a player:
    they die." Now and then, and never its own Demon. Drunk or poisoned
    it says so all the same and nobody dies (10.10.2026)."""
    if "Psychopath" not in d.script.keys:
        return
    phase = f"D{day}"
    living = [p for p in d.alive_at(phase) if d.deaths.get(p) is None]
    psycho = next((p for p in living
                   if d.role_at(p, phase) == "Psychopath"), None)
    if psycho is None or len(living) < 4 or rng.random() >= 0.3:
        return
    demon = d.demon_at(phase)
    pool = [p for p in living if p not in (psycho, demon)]
    if not pool:
        return
    target = rng.choice(pool)
    died = d.working(psycho, day, by_day=True) \
        and _can_die_by_day(d, target, day)
    if died:
        d.deaths[target] = phase
    d.psychopath_struck[day] = (psycho, target)
    heard.append(PsychopathKill(day, psycho, target=target, died=died))


def _slayer_shoots(d, day, rng, heard):
    """ "Once per game, during the day, publicly choose a player: if they
    are the Demon, they die." Now and then, at the Demon one time in three
    and otherwise at anybody, with a Philosopher that took it shooting too
    (Stelle 59, 14.10.2026). Drunk or poisoned it shoots and nothing
    happens; a working Recluse may register as the Demon.

    A Demon that would not die of it (a Zombuul's first death, a Lleech
    with its host) is not shot at: that game is not what is being tested.
    Hitting the Demon hands it to a Scarlet Woman with five alive, or ends
    the game — returns True then.
    """
    if "Slayer" not in d.script.keys:
        return False
    phase = f"D{day}"
    living = [p for p in d.alive_at(phase) if d.deaths.get(p) is None]
    if len(living) < 4:
        return False
    for seat in living:
        if not _acts_as(d, seat, "Slayer", phase) or seat in d.slayer_spent:
            continue
        if rng.random() >= 0.25:
            continue
        demon = d.demon_at(phase)
        pool = [p for p in living if p != seat]
        safe = [p for p in pool if TEAM[d.role_at(p, phase)] != "demon"
                and not _babysits(d, p, phase)]
        target = demon if demon in pool and rng.random() < 0.3 \
            else rng.choice(pool)
        working = d.working(seat, day, by_day=True)
        if target == demon and (d.role_at(demon, phase) == "Zombuul"
                                or not _can_die_by_day(d, demon, day)):
            if not safe:
                return False
            target = rng.choice(safe)
        held = d.role_at(target, phase)
        died = False
        if working and (TEAM[held] == "demon"
                        or _babysits(d, target, phase)):
            died = True
        elif working and held == "Recluse" \
                and d.working(target, day, by_day=True) \
                and _can_die_by_day(d, target, day) and rng.random() < 0.5:
            died = True
        d.slayer_spent.add(seat)
        d.shown_in_the_open.add(seat)
        heard.append(SlayerShot(day, seat, target=target, died=died))
        if not died:
            return False
        if _babysits(d, target, phase):
            d.deaths[target] = phase
            return _lil_monsta_check(d, phase)
        if TEAM[held] == "demon":
            heir = _heir(d, phase, rng)
            if heir is not None and d.roles[heir] == "ScarletWoman" \
                    and len(d.alive_at(phase)) >= 5:
                d.deaths[target] = phase
                d.handovers.append((phase, heir))
                d.changes.append((phase, heir, held))
                return False
            d.deaths[target] = phase
            return True                   # good has won
        d.deaths[target] = phase
        return False
    return False


def _virgin_answers(d, day, who, nominee, rng):
    """ "The 1st time you are nominated, if the nominator is a Townsfolk,
    they are executed immediately." Its first nomination, drunk or not,
    and a Philosopher that took it too (Stelle 59, 14.10.2026). A Spy
    nominating registers as a Townsfolk, as the solver reads it. Returns
    the row, or None if the nominee is no Virgin it spends."""
    phase = f"D{day}"
    if nominee in d.virgin_spent or not _acts_as(d, nominee, "Virgin", phase):
        return None
    d.virgin_spent.add(nominee)
    held = d.role_at(who, phase)
    townsfolk = TEAM[held] == "townsfolk" or held == "Spy"
    triggered = townsfolk and d.working(nominee, day, by_day=True)
    return VirginNomination(day, nominee, nominator=who, triggered=triggered)


def _golem_strikes(d, golem, nominee, day, rng):
    """ "When you [nominate], if the nominee is not the Demon, they die."
    Once a game, drunk or not; a Recluse may register as the Demon."""
    phase = f"D{day}"
    d.golem_spent.add(golem)
    if not d.working(golem, day, by_day=True):
        return False
    held = d.role_at(nominee, phase)
    if TEAM[held] == "demon" or _babysits(d, nominee, phase):
        return False
    if held == "Recluse" and d.working(nominee, day, by_day=True) \
            and rng.random() < 0.5:
        return False
    if not _can_die_by_day(d, nominee, day):
        return False
    d.deaths[nominee] = phase
    return True


def _a_minion_guesses_the_damsel(d, day, rng, heard):
    """Did a Minion's public guess just win the game?

    The Minions get one guess between them; a Demon or a good player
    guessing spends nothing and wins nothing. Right, and the Damsel alive
    and working, and evil has won — a drunk or poisoned Minion guessing
    right wins all the same, and a Spy in play, ever, poisons the Damsel
    (their jinx). Now and then somebody else tries it on.
    """
    if "Damsel" not in d.script.keys:
        return False
    phase = f"D{day}"
    living = d.alive_at(phase)
    if rng.random() < 0.03:
        others = [p for p in living if TEAM[d.role_at(p, phase)] != "minion"]
        if others:
            who = rng.choice(others)
            heard.append(DamselGuess(day, who,
                                     target=rng.choice(living)))
    if d.damsel_guessed:
        return False
    minions = [p for p in living if TEAM[d.role_at(p, phase)] == "minion"]
    if not minions or rng.random() >= 0.25:
        return False
    who = rng.choice(minions)
    # Or a Philosopher that took her (group 6, O, 14.10.2026).
    damsel = next((p for p in living if _acts_as(d, p, "Damsel", phase)),
                  None)
    if damsel is not None and rng.random() < 0.4:
        target = damsel
    else:
        target = rng.choice([p for p in living if p != who] or [who])
    heard.append(DamselGuess(day, who, target=target))
    d.damsel_guessed = True
    return (target == damsel and damsel is not None
            and d.working(damsel, day, by_day=True) and not _spy_ever(d))


def _the_fearmonger_wins(d, day, hanged):
    """ "If you nominate & execute them, their team loses." Its pick as it
    stands, nominated by the Fearmonger itself, and the Fearmonger with
    its ability. Executed is enough, as for the Goblin."""
    target = d.fear_nominated.get(day)
    if target is None or target != hanged:
        return False
    phase = f"D{day}"
    fear = next((p for p in d.alive_at(phase)
                 if d.role_at(p, phase) == "Fearmonger"), None)
    return fear is not None and d.fear_target.get(fear) == target \
        and d.working(fear, day, by_day=True)


def _acting_as(d, seat, role, phase):
    """Holding this character, or the Drunk's token of it."""
    return d.role_at(seat, phase) == role or d.token(seat, phase) == role


def _preacher_preaches(d, night, rng):
    """ "Each night, choose a player: a Minion, if chosen, learns this. All
    chosen Minions have no ability." Anybody, the dead too, now and then
    one it chose before. Drunk or poisoned — or drunk by the Goon it
    chose — it silences nobody (10.10.2026)."""
    if "Preacher" not in d.script.keys:
        return []
    phase = f"N{night}"
    out = []
    for seat in d.alive_at(phase):
        # Or a Philosopher that took it (13.10.2026).
        if not (_acting_as(d, seat, "Preacher", phase)
                or _took(d, seat, "Preacher", phase)):
            continue
        others = [p for p in range(d.n) if p != seat]
        if not others:
            continue
        target = rng.choice(others)
        out.append(PreacherChoice(night, seat, target=target))
        if not _acts_as(d, seat, "Preacher", phase):
            continue                      # the Drunk's token: nothing
        if _the_goon_answers(d, night, seat, target) \
                or not d.working(seat, night):
            continue
        if TEAM[d.role_at(target, phase)] == "minion":
            d.preached.append((seat, target, night))
    return out


def _preached(d, night, phase=None, by_day=False):
    """The Minions a living, working Preacher has silenced tonight."""
    phase = phase or f"N{night}"
    living = d.alive_at(f"D{night}" if by_day else phase)
    return {target for preacher, target, since in d.preached
            if since <= night and preacher in living
            and _acts_as(d, preacher, "Preacher", phase)
            and TEAM[d.role_at(target, phase)] == "minion"}


def _made_after_its_place(d, seat, night):
    """Made tonight by the Huntsman, after its own place in the night?

    Then it waits for its next night (Patrick, Lesart K, Weg 1,
    20.10.2026) — unless it is a first-night character, which learns at
    once; that is not asked here. A Philosopher the Damsel became on the
    first night chose straight away, at slot 2 of a night already at 30.
    """
    from botc.catalogue import CHARACTERS as _C
    got = d.huntsman_chose.get(night)
    if not got or got[1] != seat:
        return False
    made = _C[got[2]]
    if made.nights == "first":
        return False
    slot = made.first_night if night == 1 else made.other_night
    hunts = (_C["Huntsman"].first_night if night == 1
             else _C["Huntsman"].other_night)
    return 0 < slot < hunts


def _huntsman_hunts(d, night, rng):
    """Once a game it points at a living player; a Damsel it finds while
    working becomes a Townsfolk not in play, and says so most of the
    time. Anybody else, or a Huntsman off: nothing, and spent."""
    if "Huntsman" not in d.script.keys:
        return []
    phase = f"N{night}"
    out = []
    for seat in d.alive_at(phase):
        if d.deaths.get(seat) is not None or seat in d.huntsman_spent \
                or not (_acting_as(d, seat, "Huntsman", phase)
                        or _took(d, seat, "Huntsman", phase)):
            continue
        if rng.random() >= 0.35:
            continue                      # shakes its head tonight
        living = [p for p in d.alive_at(phase)
                  if p != seat and d.deaths.get(p) is None]
        if not living:
            continue
        damsel = next((p for p in living
                       if _acts_as(d, p, "Damsel", phase)), None)
        target = damsel if damsel is not None and rng.random() < 0.4 \
            else rng.choice(living)
        d.huntsman_spent.add(seat)
        d.huntsman_night[seat] = night
        out.append(HuntsmanChoice(night, seat, target=target))
        if not _acts_as(d, seat, "Huntsman", phase):
            continue
        if _the_goon_answers(d, night, seat, target) \
                or not d.working(seat, night) \
                or not _acts_as(d, target, "Damsel", phase):
            continue
        was = _claimed_before(d, target, phase)
        in_play = {d.role_at(p, phase) for p in range(d.n)}
        in_play |= {b for b in d.believes if b}
        spare = [k for k in d.script.townsfolk if k not in in_play]
        if not spare:
            continue
        made = rng.choice(spare)
        d.changes.append((phase, target, made))
        d.huntsman_chose[night] = (seat, target, made)
        # A first-night character made tonight learns its information at
        # once, its own place passed or not (Patrick, Lesart K,
        # 20.10.2026); any other waits for its next night. The Pixie is
        # the one whose place comes before the Huntsman's on the first
        # night: it is shown a Townsfolk really in play, as when dealt.
        if made == "Pixie" and night == 1:
            town = [d.role_at(p, phase) for p in range(d.n)
                    if p != target and TEAM[d.role_at(p, phase)]
                    == "townsfolk"]
            if town:
                d.pixie_learned[target] = rng.choice(town)
                d.pixie_mad[target] = rng.random() < 0.8
        if rng.random() < 0.8:
            out.append(BecameInfo(night, target, role=made, was=was))
    return out


def _puzzlemaster_guesses(d, day, rng, heard):
    """Once a game, a guess at the drunk player, and the Storyteller names
    somebody: the Demon if it guessed right and works, else anybody
    else. Drunk or poisoned, it is told anything (10.10.2026)."""
    if "Puzzlemaster" not in d.script.keys:
        return
    phase = f"D{day}"
    living = [p for p in d.alive_at(phase) if d.deaths.get(p) is None]
    for seat in living:
        if seat in d.puzzle_spent \
                or not (_acting_as(d, seat, "Puzzlemaster", phase)
                        or _took(d, seat, "Puzzlemaster", phase)):
            continue
        if rng.random() >= 0.25:
            continue
        others = [p for p in range(d.n) if p != seat]
        # Its own drunk: a Philosopher's is not the dealt one (13.10.2026).
        mine = getattr(d, "puzzle_drunks", {}).get(seat, d.puzzle_drunk) \
            if _took(d, seat, "Puzzlemaster", phase) else d.puzzle_drunk
        if mine is not None and mine != seat \
                and rng.random() < 0.4:
            guess = mine
        else:
            guess = rng.choice(others)
        d.puzzle_spent.add(seat)
        demon = d.demon_at(phase)
        real = _acts_as(d, seat, "Puzzlemaster", phase) \
            and d.working(seat, day, by_day=True)
        if real and guess == mine and demon is not None:
            shown = demon
        elif real:
            pool = [p for p in others if p != demon]
            shown = rng.choice(pool) if pool else guess
        else:
            shown = rng.choice(others)
        heard.append(PuzzlemasterGuess(day, seat, guess=guess, shown=shown))


def _boomdandy_explodes(d, day, hanged, rng, heard):
    """Executed, a working Boomdandy explodes: everybody but three dies,
    never the Demon, and then one more by pointing. Those that cannot die
    by day stay standing, so four may be left (10.10.2026)."""
    if "Boomdandy" not in d.script.keys:
        return False
    phase = f"D{day}"
    if d.role_at(hanged, phase) != "Boomdandy" \
            or not d.working(hanged, day, by_day=True):
        return False
    demon = d.demon_at(f"E{day}")
    standing = lambda: [p for p in range(d.n)
                        if d.deaths.get(p) is None or p == d.zombuul_up]
    order = [p for p in standing() if p != demon]
    rng.shuffle(order)
    for p in order:
        if len(standing()) <= 3:
            break
        if _can_die_by_day(d, p, day):
            d.deaths[p] = phase
    # Not a Zombuul still on its first life: it would only seem to die,
    # and the game would not be over (10.10.2026).
    left = [p for p in standing()
            if not (p == demon and d.role_at(p, phase) == "Zombuul"
                    and d.zombuul_up is None)]
    pointed = rng.choice(left) if left else None
    if pointed is not None and _can_die_by_day(d, pointed, day):
        # A Zombuul under its shroud dies for real now, and its first
        # death stays on the record beside the second.
        if pointed == d.zombuul_up and d.deaths.get(pointed) is not None:
            d.earlier_deaths.append((pointed, d.deaths[pointed]))
        d.deaths[pointed] = phase
    else:
        pointed = None
    heard.append(BoomdandyExploded(day, hanged,
                                   pointed=-1 if pointed is None
                                   else pointed))
    return True


# --------------------------------------------------------------------------
# The seventh five (11.10.2026)
# --------------------------------------------------------------------------

def _the_seventh_five_set_up(d, rng):
    """What the Storyteller settles before the first night: which Village
    Idiot is drunk, who is the faux paw, which Townsfolk the Pixie is
    shown, and whether it plays mad about it (mostly)."""
    n = d.n
    idiots = [p for p in range(n) if d.roles[p] == "VillageIdiot"]
    if len(idiots) >= 2:
        d.vi_drunk = rng.choice(idiots)
    if "Lycanthrope" in d.roles:
        # "1 good player": not the Townsfolk a Bounty Hunter brought in
        # evil (11.10.2026). The list is as it was without one.
        good = [p for p in range(n) if not is_evil(d.roles[p])
                and p != getattr(d, "bh_evil", None)]
        if good:
            d.faux_paw = rng.choice(good)
    for seat in range(n):
        if d.roles[seat] != "Pixie":
            continue
        town = [d.roles[p] for p in range(n)
                if p != seat and TEAM[d.roles[p]] == "townsfolk"]
        if not town:
            continue
        d.pixie_learned[seat] = rng.choice(town)
        d.pixie_mad[seat] = rng.random() < 0.8


def _reads_evil(d, seat, phase):
    """The side a reading is told: the truth, and the faux paw evil while
    the Lycanthrope lives and works (11.10.2026)."""
    if d.side_at(seat, phase) == "evil":
        return True
    if seat != getattr(d, "faux_paw", None):
        return False
    night = int(phase[1:])
    # The holder, or a Philosopher that took it (13.10.2026).
    return any(_acts_as(d, p, "Lycanthrope", f"N{night}")
               and d.working(p, night) for p in d.alive_at(f"N{night}"))


def _an_innkeeper_or_sailor_keeps(d, night, target):
    """The Innkeeper's pair and a sober Sailor, asked without spending
    anything. The Gossip's death went straight through both, where the
    night-walk kept them alive (11.10.2026, found with three Village
    Idiots and an Innkeeper)."""
    phase = f"N{night}"
    if _an_innkeeper_guards(d, night, target):
        return True
    return _acts_as(d, target, "Sailor", phase) and d.working(target, night)


def _kept_alive_at_night(d, night, target):
    """What stops a night death that is not the Demon's: an Innkeeper's
    pair, a sober Sailor, a Tea Lady, and a Fool's free death, last."""
    phase = f"N{night}"
    if _an_innkeeper_guards(d, night, target):
        return True
    if _acts_as(d, target, "Sailor", phase) and d.working(target, night):
        return True
    if _kept_alive_by_a_tea_lady(d, target, phase):
        return True
    return _a_fool_shrugs_it_off(d, target, phase)


def _lycanthrope_hunts(d, night, rng):
    """ "Each night*, choose an alive player. If good, they die & the
    Demon doesn't kill tonight." Never the faux paw, which reads evil to
    it; what keeps a seat alive at night keeps it alive from this, a Monk
    or a Soldier excepted (11.10.2026)."""
    if night < 2 or "Lycanthrope" not in d.script.keys:
        return []
    phase = f"N{night}"
    out = []
    for seat in d.alive_at(phase):
        if d.deaths.get(seat) is not None \
                or not (_acting_as(d, seat, "Lycanthrope", phase)
                        or _took(d, seat, "Lycanthrope", phase)):
            continue
        living = [p for p in d.alive_at(phase)
                  if p != seat and d.deaths.get(p) is None]
        if not living:
            continue
        target = rng.choice(living)
        d.lyc_aimed[night] = (seat, target)
        _chose(d, "Lycanthrope", night, seat, target)
        if rng.random() < 0.7:
            out.append(LycanthropeChose(night, seat, target=target))
        if not _acts_as(d, seat, "Lycanthrope", phase):
            continue                      # the Drunk's token: nothing
        if _the_goon_answers(d, night, seat, target) \
                or not d.working(seat, night):
            continue
        if target == d.faux_paw or d.side_at(target, phase) != "good":
            continue
        if _kept_alive_at_night(d, night, target):
            continue
        d.deaths[target] = phase
        d.lyc_quiet.add(night)
    return out


def _harpy_chooses(d, night, rng, heard):
    """Two players each night: the first, a good one here, is mad
    tomorrow that the second is evil. Drunk or poisoned, it tells nobody
    anything (11.10.2026)."""
    if "Harpy" not in d.script.keys:
        return
    phase = f"N{night}"
    for seat in range(d.n):
        if not _stands_to_act(d, seat, "Harpy", night):
            continue
        good = [p for p in d.alive_at(phase) if p != seat
                and d.deaths.get(p) is None and d.side_at(p, phase) == "good"]
        if not good:
            continue
        mad = rng.choice(good)
        second = rng.choice([p for p in range(d.n) if p != mad])
        d.harpy_chose[night] = (seat, mad)
        if _the_goon_answers(d, night, seat, mad) \
                or not d.working(seat, night):
            continue
        d.harpy_mad[night] = (seat, mad, second)


def _harpy_strikes(d, day, rng, heard):
    """The mad player sometimes breaks madness and says what the Harpy
    did; then the Storyteller may kill one of the two, or both — never the
    Demon, as with the Boomdandy (11.10.2026)."""
    got = d.harpy_mad.get(day)
    if got is None:
        return
    _harpy, mad, second = got
    if rng.random() >= 0.4:
        return                            # plays along: nothing to hear
    heard.append(HarpyMadness(day, mad, second=second))
    if rng.random() >= 0.6:
        return
    phase = f"D{day}"
    demon = d.demon_at(phase)
    pool = [p for p in (mad, second) if p != demon
            and p in d.alive_at(phase) and d.deaths.get(p) is None]
    if not pool:
        return
    pick = rng.choice([pool[:1], pool[-1:], pool])
    took = []
    for p in pick:
        if p not in took and _can_die_by_day(d, p, day):
            d.deaths[p] = phase
            took.append(p)
    d.harpy_struck[day] = took


def _lleech_picks_a_host(d, night, rng):
    """On its first night a Lleech chooses its host: a good player, a
    Townsfolk most of the time. One made later chooses on its first
    night too (11.10.2026)."""
    if "Lleech" not in d.script.keys:
        return
    phase = f"N{night}"
    for seat in d.alive_at(phase):
        if d.role_at(seat, phase) != "Lleech" or seat in d.lleech_hosts \
                or d.deaths.get(seat) is not None:
            continue
        good = [p for p in d.alive_at(phase) if p != seat
                and d.deaths.get(p) is None and d.side_at(p, phase) == "good"]
        if not good:
            continue
        town = [p for p in good if TEAM[d.role_at(p, phase)] == "townsfolk"]
        pool = town if town and rng.random() < 0.8 else good
        host = rng.choice(pool)
        _the_goon_answers(d, night, seat, host)
        d.lleech_hosts[seat] = host


def _lleech_lost(d, phase):
    """Had a Mastermind's jinx taken the Lleech's ability by now? Dated,
    so the nights before it are as they were."""
    lost = getattr(d, "lleech_lost", None)
    return lost is not None and phase_index(lost) <= phase_index(phase)


def _host_gone(d, host, phase):
    # Dead now, not once: a host the Professor raised before the Lleech
    # chose it is alive (21.10.2026).
    at = d.deaths.get(host)
    return at is not None and phase_index(at) <= phase_index(phase)


def _a_lleech_holds(d, seat, phase, night, by_day=False):
    """A working Lleech whose host lives cannot die."""
    if d.role_at(seat, phase) != "Lleech" or _lleech_lost(d, phase):
        return False
    host = d.lleech_hosts.get(seat)
    if host is not None and _host_gone(d, host, phase):
        return False
    return d.working(seat, night, by_day=by_day)


def _lleech_follows(d, phase, night, rng, by_day=False, hanged=None):
    """ "You die if & only if they are dead." A working Lleech whose host
    has died dies now, and the Scarlet Woman takes it on if she can.
    True when that ends the game. A Mastermind alive when the host is
    executed keeps it alive without its ability (their jinx)."""
    if "Lleech" not in d.script.keys or _lleech_lost(d, phase):
        return False
    for lleech, host in sorted(d.lleech_hosts.items()):
        if d.role_at(lleech, phase) != "Lleech" \
                or d.deaths.get(lleech) is not None:
            continue
        if not _host_gone(d, host, phase):
            continue
        if hanged is not None and hanged == host:
            mastermind = next((p for p in d.alive_at(phase)
                               if d.role_at(p, phase) == "Mastermind"
                               and d.deaths.get(p) is None), None)
            if mastermind is not None:
                d.lleech_lost = phase
                return False
        if not d.working(lleech, night, by_day=by_day):
            continue                      # off now: it goes when it is not
        at = f"D{night}" if by_day else f"N{night}"
        was_demon = d.demon_at(at) == lleech
        d.deaths[lleech] = at
        if not was_demon:
            continue
        sw = next((p for p in d.alive_at(at)
                   if d.role_at(p, at) == "ScarletWoman"
                   and d.deaths.get(p) is None), None)
        if sw is not None and len(d.alive_at(at)) >= 5:
            d.handovers.append((at, sw))
            d.changes.append((at, sw, "Lleech"))
            continue
        return True
    return False


def _pixie_gain(d, seat):
    """(the Townsfolk, the first night it works as one) for a mad Pixie
    whose Townsfolk died while it lived and worked, or None."""
    if d.roles[seat] != "Pixie" or not d.pixie_mad.get(seat):
        return None
    learned = d.pixie_learned.get(seat)
    holder = next((p for p in range(d.n)
                   if p != seat and d.roles[p] == learned), None)
    if holder is None:
        return None
    gone = d.deaths_of(holder)
    if not gone:
        return None
    first = min(gone, key=phase_index)
    if seat not in d.alive_at(first):
        return None
    k = int(first[1:])
    if not d.working(seat, k, by_day=first[0] in "DE"):
        return None
    return learned, k + 1


# --------------------------------------------------------------------------
# The eighth five (11.10.2026): Bounty Hunter, Cult Leader, Mezepheles,
# Leviathan, Yaggababble. Written from the wiki and the table's rulings of
# that day, not from the solver. Nothing here draws a number on a script
# without the character it is for.
# --------------------------------------------------------------------------

LEVIATHAN_CHOOSES_FOR = ("Banshee", "Farmer", "Ravenkeeper", "Sage")


def _the_eighth_five_set_up(d, rng):
    """ "[1 Townsfolk is evil]": with a Bounty Hunter dealt — the
    character, not a Drunk's token of it — one Townsfolk is evil from the
    start. Any of them, now and then the Bounty Hunter itself (table
    ruling, 11.10.2026, way 2 of C)."""
    if "BountyHunter" not in d.roles:
        return
    hunter = d.roles.index("BountyHunter")
    town = [p for p in range(d.n) if TEAM[d.roles[p]] == "townsfolk"]
    others = [p for p in town if p != hunter]
    pick = hunter if (not others or rng.random() < 0.1) else rng.choice(others)
    d.bh_evil = pick
    d.side_changes.append(("N1", pick, d.roles[pick], "evil"))


def _turned_evil_and_knows(d, seat, night):
    """A seat that keeps a good character and is evil and knows it: the
    Bounty Hunter's Townsfolk, or whoever the Mezepheles turned, from the
    night it did."""
    if seat == getattr(d, "bh_evil", None):
        return True
    turned = getattr(d, "mez_turned", None)
    return turned is not None and turned[0] == seat and night >= turned[1]


# Readings such a seat may lie about. Plain information only: a row the
# game goes on to use — a Grandmother's grandchild, a choice — is left as
# it was.
A_LIAR_MAY_CHANGE = frozenset({
    "Chef", "Empath", "Undertaker", "Washerwoman", "Librarian",
    "Investigator", "OracleInfo", "SeamstressInfo", "FlowergirlInfo",
    "TownCrierInfo", "ClockmakerInfo", "NobleInfo", "StewardInfo",
    "KnightInfo", "ShugenjaInfo", "VillageIdiotInfo", "BountyHunterInfo"})


def _a_liars_version(d, made, night, rng):
    """The same reading, made false, for a seat that chose to lie. What
    it was really shown stays what the game knows."""
    known = dict(d.bh_known)
    seen = {seat: set(got) for seat, got in d.bh_seen.items()}
    try:
        return _make_false(d, made, night, rng) or made
    finally:
        d.bh_known, d.bh_seen = known, seen


def _may_register_either_way(d, seat, night):
    """A Recluse or a Spy with its ability: the Storyteller's to say."""
    from botc.catalogue import CHARACTERS
    role = d.role_at(seat, f"N{night}")
    return bool(CHARACTERS[role].registers) and d.working(seat, night)


def _bounty_hunter_is_shown(d, seat, night, rng):
    """ "You start knowing 1 evil player. If the player you know dies,
    you learn another evil player tonight." Somebody who registers evil:
    an evil player — a Minion before the Demon — the faux paw, or now and
    then the Recluse. Never the same player twice."""
    phase = f"N{night}"
    known = d.bh_known.get(seat)
    if seat in d.bh_seen and (known is None or d.deaths.get(known) is None):
        return None                       # the one it knows is still alive
    seen = d.bh_seen.setdefault(seat, set())
    others = [p for p in range(d.n) if p != seat and p not in seen]
    evil = [p for p in others if _reads_evil(d, p, phase)]
    maybe = [p for p in others if p not in evil
             and d.side_at(p, phase) == "good"
             and _may_register_either_way(d, p, night)
             and True in evil_registrations(d.role_at(p, phase))]
    demon = d.demon_at(phase)
    pool = [p for p in evil if p != demon] or evil
    if maybe and (not pool or rng.random() < 0.2):
        pool = maybe
    if not pool:
        d.bh_known[seat] = None
        return None
    target = rng.choice(pool)
    d.bh_known[seat] = target
    seen.add(target)
    d.bh_woke.add((seat, night))
    return BountyHunterInfo(night, seat, target=target)


def _acts_as_cult_leader(d, seat, phase):
    role = d.role_at(seat, phase)
    return role == "CultLeader" or (
        role == "Philosopher" and d.philosophies.get(seat) == "CultLeader")


def _cult_leader_turns(d, night, rng):
    """ "Each night, you become the alignment of an alive neighbour."

    At the end of the night, the first included. Which neighbour is the
    Storyteller's, and so is how a Recluse or a Spy among them registers
    (table ruling, 11.10.2026): the faux paw reads evil. A Zombuul under
    its shroud is on the board as dead and is no neighbour. Drunk or
    poisoned, or dead, it stays as it is — and one that was evil when a
    Pit-Hag made it stays evil (their jinx).
    """
    if "CultLeader" not in d.script.keys:
        return
    phase = f"N{night}"
    for seat in range(d.n):
        if d.deaths.get(seat) is not None \
                or not _acts_as_cult_leader(d, seat, phase):
            continue
        if seat not in d.cult_seen:
            d.cult_seen.add(seat)
            if d.roles[seat] != d.role_at(seat, phase) \
                    and d.side_at(seat, phase) == "evil":
                d.cult_fixed.add(seat)
        if seat in d.cult_fixed or not d.working(seat, night):
            continue
        around = [p for p in _living_beside(d, seat, phase) if p != seat]
        if not around:
            continue
        other = rng.choice(around)
        if _reads_evil(d, other, phase):
            side = "evil"
        else:
            side = "good"
        if not _acts_as_cult_leader(d, other, phase) \
                and _may_register_either_way(d, other, night) \
                and len(set(evil_registrations(d.role_at(other, phase)))) > 1:
            side = rng.choice(["evil", "good"])
        if side != d.side_at(seat, f"D{night}"):
            d.side_changes.append((f"D{night}", seat,
                                   d.role_at(seat, phase), side))
            d.cult_woke.add((seat, night))


def _cult_is_called(d, day, rng, heard):
    """A Cult Leader now and then calls its cult, and people join or do
    not — the dead too, as for an exile. The game is to go on, so with
    its ability working one good player always stays out; without it
    everybody may join and nothing happens."""
    if "CultLeader" not in d.script.keys:
        return
    phase = f"D{day}"
    for seat in d.alive_at(phase):
        if d.deaths.get(seat) is not None \
                or not _acts_as_cult_leader(d, seat, phase):
            continue
        if rng.random() >= 0.25:
            continue
        others = [p for p in range(d.n) if p != seat]
        joined = {p for p in others if rng.random() < 0.5}
        good = [p for p in others if d.side_at(p, phase) == "good"]
        if d.working(seat, day, by_day=True) \
                and all(p in joined for p in good):
            if not good:
                continue                  # nobody good to stay out
            joined.discard(rng.choice(good))
        heard.append(CultCalled(day, seat, joined=frozenset(joined)))


def _mezepheles_hears(d, day, rng):
    """Somebody good says the word, on about one day in three — the
    first to do so, and only once a game."""
    if "Mezepheles" not in d.script.keys or d.mez_marked is not None:
        return
    phase = f"D{day}"
    if not any(d.role_at(p, phase) == "Mezepheles" for p in range(d.n)):
        return
    if rng.random() >= 0.3:
        return
    good = [p for p in d.alive_at(phase) if d.deaths.get(p) is None
            and d.side_at(p, phase) == "good"]
    if good:
        d.mez_marked = (rng.choice(good), day)


def _mezepheles_turns(d, night, rng):
    """ "The 1st good player to say this word becomes evil that night."

    At its turn, 18, if it is still about and has its ability: executed
    since, or drunk or poisoned tonight, nobody turns and the ability is
    spent all the same. A Mezepheles a Vigormortis killed keeps it.
    """
    marked = d.mez_marked
    if marked is None or d.mez_turned is not None or marked[1] != night - 1:
        return
    phase = f"N{night}"
    seat = marked[0]
    mez = next((p for p in range(d.n)
                if d.role_at(p, phase) == "Mezepheles"
                and d.role_at(p, f"E{night - 1}") == "Mezepheles"), None)
    if mez is None or not _has_its_ability(d, mez, phase) \
            or not d.working(mez, night):
        return
    if d.side_at(seat, phase) != "good":
        return
    d.side_changes.append((phase, seat, d.role_at(seat, phase), "evil"))
    d.mez_turned = (seat, night)


def _living_leviathan(d, phase):
    """The seat holding the Leviathan now, standing and the Demon."""
    seat = d.demon_at(phase)
    if seat is None or d.role_at(seat, phase) != "Leviathan" \
            or d.deaths.get(seat) is not None:
        return None
    return seat


def _leviathan_is_announced(d, day, heard):
    """ "All players know you are in play" — on its first day, and only
    with its ability then, as for the Vizier (table ruling, 11.10.2026,
    way 2 of O)."""
    if "Leviathan" not in d.script.keys or d.lev_first is not None:
        return
    lev = _living_leviathan(d, f"D{day}")
    if lev is None:
        return
    d.lev_first = day
    if d.working(lev, day, by_day=True):
        d.lev_announced = day
        heard.append(LeviathanAnnounced(day, lev))


def _stands_behind(d, seat, day):
    """Is this a player the Leviathan must not put on the gallows: a
    sober Soldier, the pair a working Innkeeper chose last night, the
    one a working Exorcist named (their jinxes — good would win)."""
    phase = f"D{day}"
    if _acts_as(d, seat, "Soldier", phase) \
            and d.working(seat, day, by_day=True):
        return True
    # Each holder's own choice, and only a working one (13.10.2026).
    for role, chosen in (("Innkeeper", _choices(d, "Innkeeper", day)),
                         ("Exorcist", {who: (target,) for who, target
                                       in _choices(d, "Exorcist",
                                                   day).items()})):
        for chooser, picked in chosen.items():
            who = _answering(d, chooser, role, phase)
            if seat in picked and who is not None \
                    and who in d.alive_at(phase) \
                    and d.deaths.get(who) is None \
                    and d.working(who, day, by_day=True):
                return True
    return False


def _leviathan_takes_the_day(d, day, hanged, rng, heard):
    """Has evil just won by the Leviathan? "If more than 1 good player is
    executed, evil wins... After day 5, evil wins." Executed is enough,
    dead of it or not. And its jinx with the Grandmother: her grandchild
    dead on the gallows."""
    lev = _living_leviathan(d, f"E{day}")
    if lev is None:
        return False
    working = d.working(lev, day, by_day=True)
    if hanged is not None:
        by = d.nominated_by.get(day, {}).get(hanged)
        if by is not None and rng.random() < 0.6:
            heard.append(ExecutionNomination(day, by))
        if d.side_at(hanged, f"D{day}") == "good":
            d.lev_good_executed += 1
            if d.lev_good_executed >= 2 and working:
                return True
        if working and d.deaths.get(hanged) == f"E{day}":
            for info in heard:
                if type(info).__name__ != "GrandmotherInfo" \
                        or info.target != hanged:
                    continue
                gran = info.player
                if info is _grandchild_row(heard, gran, day + 1) \
                        and d.deaths.get(gran) is None \
                        and _acts_as(d, gran, "Grandmother", f"D{day}") \
                        and d.working(gran, day, by_day=True):
                    return True
    return day >= 5 and working


def _yaggababble_speaks(d, day, rng):
    """How often it said its phrase today: not at all one day in five,
    once most days, now and then two or three times."""
    if "Yaggababble" not in d.script.keys:
        return
    phase = f"D{day}"
    demon = d.demon_at(phase)
    if demon is None or d.role_at(demon, phase) != "Yaggababble" \
            or d.deaths.get(demon) is not None:
        return
    roll = rng.random()
    d.yag_said[day] = (0 if roll < 0.2 else 1 if roll < 0.75
                       else 2 if roll < 0.92 else 3)


def _hold_a_day(d, day, rng):
    """Nominations and votes, and the execution that follows from them.

    An execution used to appear from nowhere: a seat chosen at random,
    with no nomination and no vote behind it. That was the least
    realistic thing here, and it made two characters unmodellable — a
    Flowergirl asks whether the Demon voted and a Town Crier whether a
    Minion nominated, and neither question has an answer on a board where
    nobody did either.

    Kept simple on purpose. Two or three nominations, everybody votes or
    does not with a coin weighted by how suspicious the nominee is, and
    whoever draws most votes goes up. Evil votes a little less for its
    own, which is the one piece of strategy worth having: it is what
    makes a Flowergirl's answer mean anything.
    """
    phase = f"E{day}"
    living = sorted(d.alive_at(phase))
    if len(living) < 3:
        return
    how_many = min(len(living), rng.randint(1, 3))
    nominators = rng.sample(living, how_many)

    # A Demon the Witch cursed keeps its hand down: nominating would kill
    # it, and the record would run on past the end of the game.
    night = day
    cursed = d.cursed.get(night)
    if cursed is not None and cursed == d.demon_at(phase):
        nominators = [p for p in nominators if p != cursed]

    # A Zealot must vote on every nomination while five or more are
    # alive — and so does whoever only thinks it is one. Drunk or
    # poisoned changes nothing: it cannot know.
    zealots = set()
    if "Zealot" in d.script.keys:
        # And a Philosopher that took it (group 5, 14.10.2026).
        zealots = {p for p in living
                   if (d.token(p, phase) or d.role_at(p, phase)) == "Zealot"
                   or _took(d, p, "Zealot", phase)}

    # An Organ Grinder with its ability — not drunk by its own choice nor
    # by anything else — has everybody vote with their eyes closed, and
    # nobody can write the votes down (10.10.2026).
    blind = False
    if "OrganGrinder" in d.script.keys:
        grinder = next((p for p in living
                        if d.role_at(p, phase) == "OrganGrinder"), None)
        blind = (grinder is not None and day not in d.grinder_drunk
                 and d.working(grinder, day, by_day=True))
    # A Fearmonger may go for its pick: nominated by the Fearmonger itself,
    # and if the town executes them, their team loses.
    fear = fear_pick = None
    if "Fearmonger" in d.script.keys:
        fear = next((p for p in living
                     if d.role_at(p, phase) == "Fearmonger"), None)
        fear_pick = d.fear_target.get(fear) if fear is not None else None
        if fear_pick is not None and fear_pick in living \
                and fear_pick != fear and rng.random() < 0.3:
            nominators = [fear] + [p for p in nominators if p != fear]
        else:
            fear = None

    # A Princess nominates on her first day as the Princess, mostly, and a
    # Golem now and then spends its one nomination (10.10.2026).
    princess = golem = None
    if "Princess" in d.script.keys:
        princess = next((p for p in living
                         if _acts_as(d, p, "Princess", phase)
                         and (day == 1 or not _acts_as(d, p, "Princess",
                                                       f"D{day - 1}"))),
                        None)
        if princess is not None and rng.random() < 0.6:
            nominators = [princess] + [p for p in nominators if p != princess]
        else:
            princess = None
    if "Golem" in d.script.keys:
        golem = next((p for p in living
                      if _acts_as(d, p, "Golem", phase)
                      and p not in d.golem_spent and p != cursed), None)
        if golem is not None and rng.random() < 0.3:
            nominators = [golem] + [p for p in nominators if p != golem]
        else:
            golem = None

    # A Leviathan does not put up a player good would win by: the
    # Soldier, one the Innkeeper guards, the one the Exorcist chose
    # (their jinxes, 11.10.2026).
    leviathan = (_living_leviathan(d, phase)
                 if "Leviathan" in d.script.keys else None)
    # "It is rare for the Yaggababble to kill during the day": now and
    # then, having said its phrase, somebody drops as they nominate —
    # which the table sees exactly as it sees a Witch's curse.
    drops = None
    if "Yaggababble" in d.script.keys and d.yag_said.get(day) \
            and rng.random() < 0.06:
        yagga = d.demon_at(phase)
        if yagga is not None and d.working(yagga, day, by_day=True):
            pool = [p for p in nominators if p not in (yagga, cursed)]
            drops = rng.choice(pool) if pool else None

    tally = {}
    for who in nominators:
        if d.deaths.get(who) is not None:
            continue                      # went down nominating, just now
        nominee = rng.choice([p for p in living
                              if p != who and d.deaths.get(p) is None]
                             or [who])
        if who == fear and d.deaths.get(fear_pick) is None:
            nominee = fear_pick
            d.fear_nominated[day] = fear_pick
        if who == leviathan and _stands_behind(d, nominee, day):
            free = [p for p in living if p != who and d.deaths.get(p) is None
                    and not _stands_behind(d, p, day)]
            if not free:
                continue
            nominee = rng.choice(free)
        # Not a Virgin's nominator whose execution would end the game:
        # the good twin with the Evil Twin standing (Stelle 59).
        twins = getattr(d, "twins", None)
        if "Virgin" in d.script.keys and twins is not None \
                and who == twins[1] \
                and _acts_as(d, nominee, "Virgin", f"D{day}"):
            others = [p for p in living if p not in (who, nominee)
                      and d.deaths.get(p) is None]
            if not others:
                continue
            nominee = rng.choice(others)
        d.nominations.setdefault(day, set()).add(who)
        d.nominated_by.setdefault(day, {}).setdefault(nominee, who)
        if "Virgin" in d.script.keys and d.deaths.get(who) is None:
            row = _virgin_answers(d, day, who, nominee, rng)
            if row is not None:
                d.day_heard.append(row)
                if row.triggered:
                    d.shown_in_the_open.add(nominee)
                    # Executed at once, and that is the day's execution.
                    why = _walks_away(d, who, day, rng)
                    if why is not None:
                        d.executions[day] = who
                        d.walked_because[day] = why
                    d.virgin_executed[day] = who
                    break
        if who == drops and day not in d.witch_deaths \
                and _can_die_by_day(d, who, day):
            d.deaths[who] = f"D{day}"
            d.witch_deaths[day] = who
            d.yag_by_day[day] = who
            d.yag_said[day] -= 1
        if who == princess and nominee != who:
            d.princess_nominated[day] = (princess, nominee)
            d.day_heard.append(PrincessNominated(day, princess,
                                                 target=nominee))
        # "If they nominate tomorrow, they die" — at once, and the
        # nomination still counts. The Witch was dealt, aimed every night
        # and never killed anybody, so a death the solver reads as "a
        # Witch is in play, and working" never came up (03.10.2026).
        if who == cursed and _the_curse_bites(d, who, day):
            d.deaths[who] = f"D{day}"
            d.witch_deaths[day] = who
        if who == golem and nominee != who:
            died = (d.deaths.get(golem) is None
                    and _golem_strikes(d, golem, nominee, day, rng))
            d.golem_spent.add(golem)
            d.day_heard.append(GolemNomination(day, golem, target=nominee,
                                               died=died))
            if died:
                continue                  # nobody votes on a corpse
        votes = set()
        for voter in living:
            # Evil is a shade less willing to put its own up, which is
            # the whole reason a Flowergirl's answer carries anything.
            chance = 0.45
            if is_evil(d.roles[voter]) and is_evil(d.roles[nominee]):
                chance = 0.2
            if rng.random() < chance:
                votes.add(voter)
            elif voter in zealots and d.deaths.get(voter) is None \
                    and sum(1 for p in living
                            if d.deaths.get(p) is None) >= 5:
                votes.add(voter)
        if votes:
            store = d.hidden_votes if blind else d.votes
            store.setdefault(day, set()).update(votes)
            d.voted_for.setdefault(day, {}).setdefault(
                nominee, set()).update(votes)
        tally[nominee] = max(tally.get(nominee, 0), len(votes))
    d.tally[day] = tally
    if blind and d.nominations.get(day):
        d.blind_days.add(day)


def _a_goblin_said_so(d, day, executed, rng, heard):
    """Did a working Goblin just win the game by being executed?

    "If you publicly claim to be the Goblin when nominated & are executed
    that day, your team wins." It usually says so — that is what it is
    for — and now and then somebody who is no Goblin says it too, hoping
    the town flinches. The town here does not flinch, which is the one
    case the words can be checked: the claimant hangs, and the game
    either ends or it does not.

    A drunk or poisoned Goblin says it just the same and wins nothing.

    Nothing is drawn on a script without one, so no other game moves.
    """
    if "Goblin" not in d.script.keys:
        return False
    if d.role_at(executed, f"D{day}") == "Goblin":
        if rng.random() >= 0.7:
            return False                  # kept quiet, and simply died
        heard.append(GoblinClaim(day, executed))
        return d.working(executed, day, by_day=True)
    if rng.random() < 0.06:
        heard.append(GoblinClaim(day, executed))
    return False


def _the_curse_bites(d, seat, day):
    """Does the cursed player, nominating, drop dead?

    The Witch has to have its ability still: alive (or a Vigormortis's
    own kill), sober, and more than three players living. And the seat
    has to be able to die at all.
    """
    phase = f"D{day}"
    witch = d.cursed_by.get(day)
    if witch is None or d.role_at(witch, phase) != "Witch":
        return False
    if not _has_its_ability(d, witch, phase) or not d.working(witch, day):
        return False
    if len(d.alive_at(phase)) <= 3:
        return False
    if _acts_as(d, seat, "Sailor", phase) and d.working(seat, day):
        return False
    if _a_vizier_stands(d, seat, day):
        return False
    if _kept_alive_by_a_tea_lady(d, seat, phase):
        return False
    return not _a_fool_shrugs_it_off(d, seat, phase)


def _walks_away(d, seat, day, rng):
    """What keeps this seat alive if the town executes it today, if anything.

    Five things can. A sober Sailor cannot die; a Tea Lady's neighbours
    cannot either; a Devil's Advocate chose them last night; a Pacifist is
    about and the Storyteller is feeling kind; and a Fool has its one free
    death left. The Fool is asked last, so it is not spent on a day
    something else would have done.

    These seats used to be simply *not picked* — `_survives_execution`
    took them out of the pool, because the record had no way to say
    "executed and lived". It has now, so they go up like anybody else.
    Until this, no played game had an execution anybody walked away from
    (03.10.2026).
    """
    phase = f"D{day}"
    role = d.role_at(seat, phase)
    if _acts_as(d, seat, "Sailor", phase) and d.working(seat, day,
                                                         by_day=True):
        return "Sailor"
    if _a_vizier_stands(d, seat, day):
        return "Vizier"
    if _a_lleech_holds(d, seat, phase, day, by_day=True):
        return "Lleech"
    if _kept_alive_by_a_tea_lady(d, seat, phase):
        return "TeaLady"
    advocate, chosen = d.spared.get(day) or (None, None)
    if chosen == seat and advocate in d.alive_at(phase) \
            and d.deaths.get(advocate) is None \
            and d.role_at(advocate, phase) == "DevilsAdvocate" \
            and d.working(advocate, day, by_day=True):
        return "DevilsAdvocate"
    # "If executed, you only die if you lose roshambo." Played only by a
    # Psychopath with its ability, and won two times in three.
    if role == "Psychopath" and d.working(seat, day, by_day=True):
        d.roshambo[day] = seat
        if rng.random() < 2 / 3:
            return "Psychopath"
        return None
    pacifist = next((p for p in d.alive_at(phase)
                     if _acts_as(d, p, "Pacifist", phase)
                     and d.deaths.get(p) is None
                     and d.working(p, day, by_day=True)), None)
    if pacifist is not None \
            and d.side_at(seat, phase) == "good":
        # "Once per game is usually about right."
        if rng.random() < (0.5 if d.pacifist_spared == 0 else 0.15):
            d.pacifist_spared += 1
            return "Pacifist"
    if _a_fool_shrugs_it_off(d, seat, phase):
        return "Fool"
    return None


def _execute(d, day, rng, allow_takeover=False):
    """The town executes somebody.

    Never the Saint — that ends the game, and a finished game is not what
    we are testing. The Demon can go, but only when the Scarlet Woman is
    standing by to take over; otherwise good would have won there.

    Who goes up comes from the day's voting when there was one, so the
    execution is the *consequence* of the day rather than a coin flip.
    """
    phase = f"E{day}"
    demon = d.demon_at(phase)
    # A town told of a Leviathan executes with great care (the table,
    # 11.10.2026): at all only every other day, and once somebody good
    # has gone, only when it is sure — which here it almost never is.
    # "Sure" is what the Storyteller knows, less a mistake now and then.
    if getattr(d, "lev_announced", None) is not None \
            and _living_leviathan(d, phase) is not None:
        if rng.random() < 0.5:
            return None
        if d.lev_good_executed >= 1 and rng.random() >= 0.1:
            return None
    # The Saint it is *now*. A Pit-Hag can make one mid-game, and reading
    # the deal let the town execute it — which ends the game, and the
    # record then ran on for two more days.
    #
    # Fifth time the deal has been mistaken for the timeline. The sweep
    # after the fourth missed this one because it is in the *day*, and I
    # only looked at the night.
    # And not somebody a Witch's curse has just dropped: dead since this
    # morning's nominations, though "alive today" still lists them.
    living = [p for p in d.alive_at(phase)
              if d.role_at(p, phase) != "Saint"
              and not _took(d, p, "Saint", phase)
              and d.deaths.get(p) is None]
    # Nor the good twin while the Evil Twin stands: evil wins on the spot,
    # the same as with the Saint, and the record would run on past the
    # end of the game.
    twins = getattr(d, "twins", None)
    if twins is not None:
        evil, good = twins
        if evil in d.alive_at(phase) and d.role_at(evil, phase) == "EvilTwin":
            living = [p for p in living if p != good]
    heir = _heir(d, phase, rng)
    takeover = (allow_takeover and heir is not None
                and d.roles[heir] == "ScarletWoman"
                and len(d.alive_at(phase)) >= 5)
    # Two more ways the Demon can go up without the game ending there.
    #
    # A Zombuul survives its first death: it is recorded dead and goes on.
    # Only the first — the record keeps one death a seat, so a second
    # execution would overwrite the first and the solver would read the
    # real death as the survivable one.
    #
    # A Mastermind, alive and working, buys one more day: "if the Demon
    # dies by execution (ending the game), play for 1 more day". Only
    # when nothing else would have kept the game going — a Scarlet Woman
    # taking over comes first. Written from the wiki, not from the solver.
    zombuul_first = (demon is not None
                     and d.role_at(demon, phase) == "Zombuul"
                     and d.zombuul_up is None
                     and d.deaths.get(demon) is None)
    # "Comes first" has to hold when takeovers are switched off as well:
    # a Scarlet Woman standing by takes the Demon whether or not this
    # run wants to play that, so the game would not have ended and a
    # Mastermind has no extra day to buy. On a mixed script the town
    # hanged a Vortox between the two, the simulator played the extra
    # day and the solver — rightly — had the Scarlet Woman holding the
    # Vortox (07.10.2026). No published script has both.
    she_would = (heir is not None
                 and d.role_at(heir, phase) == "ScarletWoman"
                 and len(d.alive_at(phase)) >= 5)
    mastermind = d.seat_of("Mastermind")
    extra_day = (not takeover and not zombuul_first and not she_would
                 and mastermind is not None
                 and d.role_at(mastermind, phase) == "Mastermind"
                 and mastermind in d.alive_at(phase)
                 # Hanged itself, babysitting Lil' Monsta: dead, it has
                 # no ability to buy the day with (21.10.2026).
                 and mastermind != demon
                 and d.working(mastermind, day)
                 and d.game_ends_after is None)
    # Or a Devil's Advocate has it covered, and it walks away.
    advocate, chosen = d.spared.get(day) or (None, None)
    covered = (demon is not None and chosen == demon
               and advocate in d.alive_at(phase)
               and d.deaths.get(advocate) is None
               and d.role_at(advocate, phase) == "DevilsAdvocate"
               and d.working(advocate, day))
    # A Lleech whose host lives walks away from it (11.10.2026).
    lleech_stands = (demon is not None
                     and _a_lleech_holds(d, demon, f"D{day}", day,
                                         by_day=True))
    if not (takeover or zombuul_first or extra_day or covered
            or lleech_stands):
        living = [p for p in living if p != demon]
    if not living:
        return None
    tally = d.tally.get(day) or {}
    ranked = [seat for seat, count in
              sorted(tally.items(), key=lambda kv: -kv[1])
              if seat in living and count]
    # "If good voted, you may choose to execute immediately." A Vizier
    # with its ability sometimes does, on a nominee at least one good
    # player voted for — never the Magician, which is immune (their
    # jinx). The solver reads no vote counts, so this only moves who
    # goes up (10.10.2026).
    forced = None
    if "Vizier" in d.script.keys:
        vizier = next((p for p in d.alive_at(phase)
                       if d.role_at(p, phase) == "Vizier"
                       and d.deaths.get(p) is None), None)
        if vizier is not None and d.working(vizier, day, by_day=True):
            backed = sorted(
                nominee for nominee, voters
                in (d.voted_for.get(day) or {}).items()
                if nominee in living
                and d.role_at(nominee, phase) != "Magician"
                and any(d.side_at(v, phase) == "good" for v in voters))
            if backed and rng.random() < 0.3:
                forced = rng.choice(backed)
                d.vizier_forced[day] = forced
    if forced is not None:
        ranked = [forced]
    if ranked:
        # Most votes goes up. A tie is broken by whoever was nominated
        # first, which is what a Storyteller does.
        victim = ranked[0]
    else:
        if rng.random() >= 0.8:
            return None
        victim = rng.choice(living)
    # Executed — and whether that kills them is a separate question now.
    why = _walks_away(d, victim, day, rng)
    if why is not None:
        d.executions[day] = victim
        d.walked_because[day] = why
        return None
    if victim == demon:
        if zombuul_first:
            d.zombuul_up = demon          # down on the board, not in fact
        elif extra_day:
            d.game_ends_after = day + 1   # one more day, then it is over
            # An Al-Hadikhia chooses for the game tonight instead (its
            # jinx with the Mastermind, 21.10.2026).
            if d.role_at(demon, phase) == "AlHadikhia":
                d.ah_final_night = day + 1
        elif _babysits(d, victim, phase):
            # Lil' Monsta's babysitter: the Scarlet Woman babysits for the
            # rest of the game (their jinx), from the night after.
            d.handovers.append((f"N{day + 1}", heir))
            d.lm_fallen = phase
            d.lm_fallen_seats = getattr(d, "lm_fallen_seats", set()) \
                | {victim}
        else:
            d.handovers.append((phase, heir))
            d.changes.append((phase, heir, d.roles[victim]))
    return victim


def simulate(n, rng, nights=1):
    """Backwards-compatible single return for the night-one checks."""
    return play(n, rng, nights)[0]


# --------------------------------------------------------------------------
# Lil' Monsta (21.10.2026, claude/lil-monsta-lesarten.md)
# --------------------------------------------------------------------------

# The Summoner (21.10.2026, claude/beschwoerer-lesarten.md). Patrick's H:
# it makes a living good player the Demon — one whose character the
# table has seen confirmed, if there is one, otherwise any — and the
# Demon at random from the script's; a Pukka mostly on the second night.

def _confirmed(d, seat, heard, phase):
    """Has the table seen this seat's character confirmed by now: named
    by a Washerwoman, Librarian or Grandmother, shown good to a Steward,
    or out in the open as a Slayer that shot or a Virgin that took her
    nominator?"""
    if seat in d.shown_in_the_open:
        return True
    role = d.role_at(seat, phase)
    for row in heard:
        kind = type(row).__name__
        if kind in ("Washerwoman", "Librarian") \
                and seat in (row.a, row.b) and row.role == role:
            return True
        if kind == "GrandmotherInfo" and row.target == seat:
            return True
        if kind == "StewardInfo" and row.target == seat:
            return True
        if kind == "VirginNomination" and row.triggered \
                and row.player == seat:
            return True
    return False


def _summoner_has_it(d, night):
    """Is the Summoner's ability worked tonight — by itself, or by the
    Storyteller where a Courtier or a Preacher took it (their jinxes)?"""
    s = d.summoner
    if d.working(s, night):
        return True
    courtier = any(holder == s and n <= night <= n + 2
                   for n, holder, _c in d.courtier_drunks)
    preached = any(minion == s for _p, minion, _n in d.preached)
    return courtier or preached


def _summoner_summons(d, night, rng, heard):
    """The third night, or the second for a Pukka: somebody becomes an
    evil Demon of the script."""
    if d.summoned is not None or night not in (2, 3):
        return
    s = d.summoner
    phase = f"N{night}"
    if s not in d.alive_at(phase) or d.deaths.get(s) is not None:
        return
    if getattr(d, "summon_pick", None) is None:
        allowed = [k for k in d.script.demons
                   if k not in ("LilMonsta", "Legion", "Riot")]
        d.summon_pick = rng.choice(allowed) if allowed else None
    demon = d.summon_pick
    if demon is None:
        return
    if night == 2 and not (demon == "Pukka" and rng.random() < 0.75):
        return
    if not _summoner_has_it(d, night):
        if night == 3:
            d.summon_failed = 3           # no Demon: good wins at dawn
        return
    n = d.n
    # Standing at its turn: not somebody a Gambler's guess took earlier
    # tonight.
    living = [p for p in d.alive_at(phase) if d.deaths.get(p) is None]
    good = [p for p in living if d.side_at(p, phase) == "good"]
    pool = good
    # A Zombuul may be made of somebody dead, who has then died once.
    dead = [p for p in range(n) if p not in living
            and d.side_at(p, phase) == "good"]
    if demon == "Zombuul" and dead and rng.random() < 0.15:
        pool = dead
    # A living Poppy Grower: the Storyteller picks the player.
    if any(d.role_at(p, phase) == "PoppyGrower" for p in living):
        pool = list(living)
    # The Marionette's jinx: it enters play beside the Demon, alive or
    # dead (22.10.2026) — a good neighbour, a Drunk or a Lunatic too.
    def puppets(p):
        return [q for q in ((p - 1) % n, (p + 1) % n)
                if q != p and d.side_at(q, phase) == "good"
                and (d.believes[q] is None
                     or d.role_at(q, phase) == d.roles[q])]
    if d.marionette_slot is not None:
        pool = [p for p in pool if puppets(p)] or pool
    # The Lord of Typhon's: beside a Minion.
    minion = lambda p: TEAM[d.role_at(p, phase)] == "minion"
    if demon == "LordOfTyphon":
        pool = [p for p in pool
                if any(minion(q) for q in ((p - 1) % n, (p + 1) % n))]
        if not pool:
            return
    confirmed = [p for p in pool if p in living
                 and _confirmed(d, p, heard, phase)]
    seat = rng.choice(confirmed or pool) if (confirmed or pool) else s
    d.changes.append((phase, seat, demon))
    d.side_changes.append((phase, seat, demon, "evil"))
    d.summoned = (night, seat, demon)
    if d.marionette_slot is not None and puppets(seat):
        q = rng.choice(puppets(seat))
        # A Drunk or a Lunatic keeps the token it lives by (22.10.2026).
        d.marionette_before = d.believes[q]
        if d.believes[q] is None:
            d.believes[q] = d.role_at(q, phase)
        d.changes.append((phase, q, "Marionette"))
        d.side_changes.append((phase, q, "Marionette", "evil"))
        d.marionette_made = q
        d.summoned_extra = tuple(getattr(d, "summoned_extra", ())) \
            + ((q, "Marionette"),)
    if seat not in living:
        d.zombuul_up = seat               # "has already died once"
    # A Lleech made tonight chooses its host tonight, at its own turn.
    if demon == "Lleech":
        _lleech_picks_a_host(d, night, rng)
    if demon == "LordOfTyphon":
        left, right = (seat - 1) % n, (seat + 1) % n
        other = right if minion(left) else left
        if not minion(other) and other != seat:
            held = {d.role_at(p, phase) for p in range(n)}
            spare = [k for k in d.script.minions
                     if k not in held and k != "Summoner"]
            if spare:
                role = rng.choice(spare)
                d.changes.append((phase, other, role))
                d.side_changes.append((phase, other, role, "evil"))
                d.summoned_extra = tuple(getattr(d, "summoned_extra",
                                                 ())) + ((other, role),)


def _summoner_check(d, night):
    """After a night or a day: did the game end because no Demon came?
    The Summoner dead before it made one, or drunk on its turn."""
    if d.summoned is not None:
        return False
    s = d.summoner
    if d.summon_failed is not None:
        d.ended_at, d.ended_why = f"N{d.summon_failed}", "summoner"
        return True
    gone = d.deaths.get(s)
    if gone is None:
        return False
    d.ended_at, d.ended_why = gone, "summoner"
    return True


def _babysits(d, seat, phase):
    """Is this seat Lil' Monsta's babysitter at this moment — "the Demon"
    without a Demon character?"""
    if not d.babysat or seat is None:
        return False
    return d.demon_at(phase) == seat \
        and TEAM[d.role_at(seat, phase)] != "demon"


def _lil_monsta_lives(d, phase):
    """Is there a babysitter standing — Lil' Monsta not yet dead?"""
    sitter = d.demon_at(phase)
    return (sitter is not None and d.deaths.get(sitter) is None
            and TEAM[d.role_at(sitter, phase)] != "demon")


def _minions_choose(d, night, rng, heard):
    """The Minions point at tonight's babysitter (H, Weg 1): the same one
    seven nights in ten, a Minion nearly always, now and then somebody
    good — who is woken and shown the token, and says so (C).

    Not after the Scarlet Woman took it over: hers for the rest of the
    game. The Magician's jinx keeps it with a Minion; the Marionette's
    has the first one sit beside it.
    """
    from botc.info import LilMonstaBabysat
    phase = f"N{night}"
    if d.handovers:
        return None
    living = [p for p in d.alive_at(phase) if d.deaths.get(p) is None]
    if not living:
        return None
    minions = [p for p in living if TEAM[d.role_at(p, phase)] == "minion"]
    magician = next((p for p in living
                     if d.role_at(p, phase) == "Magician"), None)
    pool = minions if magician is not None and minions else living
    before = d.babysat.get(night - 1)
    if night == 1 and "Marionette" in d.roles:
        m = d.roles.index("Marionette")
        beside = [p for p in ((m - 1) % d.n, (m + 1) % d.n) if p in pool]
        pick = rng.choice(beside) if beside else rng.choice(pool)
    elif before in pool and rng.random() < 0.7:
        pick = before
    elif minions and (magician is not None or rng.random() < 0.95):
        pick = rng.choice([p for p in minions if p in pool] or minions)
    else:
        others = [p for p in pool if p not in minions]
        pick = rng.choice(others or pool)
    d.babysat[night] = pick
    if d.side_at(pick, phase) == "good":
        heard.append(LilMonstaBabysat(night, pick))
    return pick


def _lil_monsta_night(d, night, rng, heard):
    """A night but the first: the Minions choose, and then a player might
    die (D, Weg 1). Never the babysitter; a Minion now and then late on,
    so good is not left guessing among several. Whatever keeps a player
    from the Demon keeps them from this, an Exorcist that named last
    night's babysitter included — so the kill is settled before tonight's
    choice is written down."""
    phase = f"N{night}"
    if not _lil_monsta_lives(d, f"D{night - 1}"):
        return []                         # a Mastermind's day: no Demon
    sitter = d.babysat.get(night - 1) if not d.handovers \
        else d.demon_at(phase)
    choice = None
    if not d.handovers:
        living = [p for p in d.alive_at(phase) if d.deaths.get(p) is None]
        minions = [p for p in living if TEAM[d.role_at(p, phase)] == "minion"]
        # Chosen now, written down after the kill.
        snapshot = dict(d.babysat)
        choice = _minions_choose(d, night, rng, heard)
        d.babysat = snapshot
        sitter = choice
    living = [p for p in d.alive_at(phase)
              if d.deaths.get(p) is None and p != sitter]
    aimed = []
    if living and rng.random() < 0.85:
        minions = [p for p in living if TEAM[d.role_at(p, phase)] == "minion"]
        good = [p for p in living if d.side_at(p, phase) == "good"]
        if minions and len(living) <= 5 and rng.random() < 0.3:
            target = rng.choice(minions)
        elif good:
            target = rng.choice(good)
        else:
            target = None
        if target is not None:
            d.lm_aimed = getattr(d, "lm_aimed", {})
            d.lm_aimed[night] = target
            if not _protected(d, night, target):
                aimed = [target]
    if choice is not None:
        d.babysat[night] = choice
    return aimed


def _lil_monsta_fell(d, phase):
    """Lil' Monsta's babysitter died at this moment. With five or more
    alive the Scarlet Woman babysits for the rest of the game, from the
    moment after (their jinx); otherwise good has won — True."""
    from botc.info import phase_index
    index = phase_index(phase) + 1
    after = f"{'D' if index % 2 else 'N'}{index // 2 + 1}"
    scarlet = next((p for p in d.alive_at(phase)
                    if d.role_at(p, phase) == "ScarletWoman"
                    and d.deaths.get(p) is None), None)
    d.lm_fallen = phase
    if scarlet is not None and len(d.alive_at(phase)) >= 5:
        d.handovers.append((after, scarlet))
        return False
    return True


def _lil_monsta_check(d, phase):
    """After a night or a day: did the babysitter die of something else?
    True if the game ended there."""
    if not d.babysat:
        return False
    sitter = d.demon_at(phase)
    if sitter is None or d.deaths.get(sitter) is None:
        return False
    if d.game_ends_after is not None:
        return False                      # a Mastermind's day
    fallen = getattr(d, "lm_fallen_seats", set())
    if sitter in fallen:
        return False                      # seen to already
    d.lm_fallen_seats = fallen | {sitter}
    if fallen:
        d.lm_fallen = d.deaths[sitter]
        return True                       # the Scarlet Woman fell too
    return _lil_monsta_fell(d, d.deaths[sitter])


def _alive(deaths, n, phase):
    from botc.info import phase_index
    here = phase_index(phase)
    return [p for p in range(n)
            if deaths.get(p) is None or phase_index(deaths[p]) >= here]


# Sects & Violets: started.
#
# Six readings are in — Clockmaker, Dreamer, Oracle, Seamstress, Sage,
# Klutz — and the **Vortox inverts them**, which is the thing that makes
# this script different from the other two: it is not a droisoning, the
# ability works and what it yields is false. `_make_false` turns a true
# reading into a false one by its shape: any wrong number for a count,
# *neither* of the two for a pair, the opposite for a yes or no.
#
# That took twenty games from three impossible boards to none. Two of ten
# measured still rule the true Demon out, and both are the *search* not
# reaching the true world rather than the solver rejecting it — the world
# explains the board perfectly (cost 1.0) and is simply never generated.
#
# One is the known Townsfolk-lie gap. The other is not yet understood:
# every seat's true character is individually admitted by its own claim,
# the softclaims are truthful, and the bag is legal (a Fang Gu game with
# three Outsiders) — so something about the combination excludes it, and
# tracing it ran out of memory on a nine-seat search with good lies
# allowed. Reproduce with seed 8 on Sects & Violets.
#
# Not yet produced: Mathematician, Flowergirl, Town Crier, Juggler,
# Savant, Artist, Evil Twin, Philosopher, Snake Charmer, Pit-Hag. Ten of
# sixteen, and several need the day recorded rather than the night.


# Bad Moon Rising: done, and it found two bugs in the *solver*.
#
# All four Demons kill in their own way, the Grandmother grieves, and the
# Chambermaid counts by the `wake` set. Of twenty-five games, the number
# the solver called impossible went nine, three, two, then **none**.
#
# The last two were not the simulator at all:
#
#   * A **Pukka's** kill demanded its victim was poisoned the night
#     before and nothing provided that poison, so every Pukka board was
#     impossible. Unnoticed because a board only breaks once a death is
#     recorded on the right night, and no corpus board had one.
#   * **Every Demon wakes on night one** to learn its Minions, and the
#     waking check read `nights` — which says "other", describing when it
#     *kills*. A Chambermaid beside a Demon counted two and the solver
#     said no world could produce that.
#
# Still to do: Sects & Violets, where none of the seventeen good
# characters can be resolved yet.


def _living_beside(d, seat, phase, gone=()):
    """The nearest living player on each side, going round the circle."""
    # Not somebody already dead tonight by another hand — a Gambler that
    # guessed wrong at 10 is no neighbour at 27.
    alive = [p for p in d.alive_at(phase)
             if p not in gone and d.deaths.get(p) != phase]
    out = []
    for step in (1, -1):
        for gap in range(1, d.n):
            other = (seat + step * gap) % d.n
            if other == seat:
                break
            if other in alive:
                out.append(other)
                break
    return out


def _live_pukka(d, night):
    """The seat holding the Pukka tonight, if it is alive."""
    phase = f"N{night}"
    demon = d.demon_at(phase)
    if demon is None or demon not in d.alive_at(phase):
        return None
    return demon if d.role_at(demon, phase) == "Pukka" else None


def _pukka_token_carries(d, night):
    """At nightfall: whose poison is still standing from before.

    "If the Pukka dies or changes player, remove all Pukka reminder
    tokens" — so the token belongs to a seat, and goes when that seat
    stops being a living Pukka.
    """
    pukka = _live_pukka(d, night)
    if pukka is None or pukka != d.pukka_owner:
        d.pukka_poisoned = None
    d.pukka_owner = pukka
    if d.pukka_poisoned is not None:
        d.pukka_due[night] = d.pukka_poisoned


def _still_under_the_token(d, night, seat):
    """Is this seat choosing while a Pukka's poison from before is on it?

    That poison lasts into the night, until the Pukka's turn. A Sailor
    or an Innkeeper acts well before that: its choice is made with no
    ability and does nothing — and it stays nothing if the token comes
    off later because something kept them alive. `droisoned_at` answers
    for the night as a whole, and by morning such a seat reads healthy;
    so its choice made one of its pair drunk after all, and a Chambermaid
    was told nonsense with nothing on the board to explain it
    (03.10.2026, a Tea Lady beside an Innkeeper the Pukka had poisoned).
    """
    return d.pukka_due.get(night) == seat and not d.working(seat, night)


def _exorcised(d, night):
    """Did a working Exorcist name the Demon tonight?"""
    phase = f"N{night}"
    if d.exorcised.get(night) is None:
        return False
    demon = d.demon_at(phase)
    if demon is None:
        return False
    # Each Exorcist's own choice, and only a working one (13.10.2026).
    for chooser, target in _choices(d, "Exorcist", night).items():
        exo = _answering(d, chooser, "Exorcist", phase)
        if target == demon and exo is not None \
                and exo in d.alive_at(phase) and d.working(exo, night):
            return True
    return False


def _protected(d, night, target, by_exorcist=True, gone=()):
    """Would the kill be stopped before it landed?

    Shared by every Demon, because none of them cares which one is
    swinging: a sober Soldier is safe, a Monk can guard somebody else.

    `by_exorcist` is for the one kill an Exorcist does not stop: a
    Pukka's poison coming due. The Exorcist keeps the Demon from
    *choosing*, and that death was chosen the night before.

    `gone` is who this Demon has already taken tonight. A Shabaloth and
    a Po kill one after another — "in the order chosen, each chosen
    player dies" — so by the second kill the first is dead: a Tea Lady
    taken first protects nobody, and one whose evil neighbour was taken
    first now has a good one beside her. This asked about the table as
    it stood at nightfall, and the night-walk, which goes in order, said
    otherwise (03.10.2026).
    """
    phase = f"N{night}"
    # A Princess's day stops the Demon whatever it aims at, the poison of
    # a Pukka's coming due included (10.10.2026). Asked first, so nothing
    # else — a Fool's free death above all — is spent on it.
    if _the_princess_stops(d, night):
        return True
    # The Lycanthrope killed tonight: the Demon kills nobody, the
    # Pukka's poison included (11.10.2026).
    if night in getattr(d, "lyc_quiet", ()):
        return True
    # Working, which is every way of going wrong, not only the Poisoner.
    if _acts_as(d, target, "Soldier", phase) and d.working(target, night):
        return True

    # A sober Sailor cannot die. Missing here while the solver has always
    # had it as a shield; nothing tripped only because the Sailor is so
    # often the drunk one of its own pair.
    if _acts_as(d, target, "Sailor", phase) and d.working(target, night):
        return True

    # An Innkeeper keeps two players safe. The docstring above has
    # promised a Monk since this was written and neither was here — the
    # Innkeeper was dealt twenty-four times across a hundred and eighty
    # games and never acted at all, so nothing ever tested it.
    #
    # A droisoned Innkeeper protects nobody: a plain ability simply does
    # not function.
    # A Tea Lady keeps both her living neighbours alive, if both are
    # good. Always on rather than aimed: she chooses nobody, so a
    # neighbour who died means she was not working.
    #
    # The solver has modelled her since she went in and the simulator
    # never did — a Demon killed straight through her, and the board had
    # no legal world because nothing could explain why she failed.
    for lady in range(d.n):
        if not _acts_as(d, lady, "TeaLady", phase) \
                or lady not in d.alive_at(phase):
            continue
        if not d.working(lady, night) or lady in gone:
            continue
        around = _living_beside(d, lady, phase, gone)
        if len(around) < 2 or target not in around:
            continue
        if all(d.side_at(p, phase) == "good" for p in around):
            return True

    # An Exorcist that named the Demon stops it choosing at all tonight.
    if by_exorcist and _exorcised(d, night):
        return True

    for chooser, guarded in _choices(d, "Monk", night).items():
        monk = _answering(d, chooser, "Monk", phase)
        if guarded == target and monk is not None \
                and monk in d.alive_at(phase) and d.working(monk, night) \
                and monk not in gone:
            return True

    # A guard goes with whoever gave it: an Innkeeper the Shabaloth took
    # first protects nobody from its second kill.
    if _an_innkeeper_guards(d, night, target, gone=gone):
        return True

    # And a Fool, last: its one free death, spent only if nothing else
    # had already kept it alive.
    return _a_fool_shrugs_it_off(d, target, phase)


def _demon_kills(d, night, rng):
    """Who dies tonight, as a list, because not every Demon takes one.

    Each Bad Moon Rising Demon kills in its own way and the simulator
    used to kill like an Imp regardless — which produced boards the
    solver called impossible, correctly, since a Pukka that kills the
    night it poisons is not a legal game.

    What each one does is derived here rather than read from the solver,
    the same as every other rule in this file: a shared misreading that
    lives in both is exactly what this is meant to catch.
    """
    phase = f"N{night}"
    demon = d.demon_at(phase)
    living = d.alive_at(phase)
    # A Zombuul that survived its first death is on the board as dead and
    # still the Demon, so being off the living list does not stop it.
    if demon is None or (demon not in living and d.zombuul_up != demon):
        return []
    # The Demon it is *now*, not the one this seat was dealt.
    #
    # A Snake Charmer that swaps takes the Demon's character, so a seat
    # dealt a Snake Charmer can be holding a Zombuul by night two — and
    # reading `d.roles` gave it the generic kill instead of the
    # Zombuul's. It killed on a night after an execution, which a Zombuul
    # may not do, and the solver rightly refused the board.
    #
    # Same mistake as `demon_at` had twice: the deal is not the timeline.
    kind = d.role_at(demon, phase)

    # A droisoned Demon kills nobody. Its ability is a plain one and
    # simply does not function — the same rule that keeps a droisoned
    # Farmer from handing the character on.
    #
    # Never checked here, so a Demon killed straight through its own
    # poisoning. It went unseen until a Minstrel silenced the whole table
    # and three seats still died on that night; before the Acrobat there
    # was no reason to look at a night where the Demon was impaired.
    if not d.working(demon, night):
        return []
    # Not somebody who has already died tonight. A Gambler that guessed
    # wrong at 10 was still "alive tonight" at 28, so the Po took it a
    # second time — and its Grandmother died of grief for a grandchild
    # the Demon never killed (03.10.2026, the night-walk again).
    others = [p for p in living if p != demon and d.deaths.get(p) is None]

    # The Monk guards, whoever is swinging — or a Philosopher that took
    # it, while the Monk it drunk does not (13.10.2026).
    monk = _a_working_monk(d, night, living)
    guarded = None
    if monk is not None and rng.random() < 0.3:
        guarded = rng.choice([p for p in living if p != monk] or [monk])

    tried = d.demon_aimed[night] = []

    def take(pool, gone=()):
        """One kill from a pool, or nothing if it was stopped.

        **Never itself.** A Demon does not choose its own seat, and no
        rule anywhere lets it — but the pool was simply everyone living,
        so a Po taking three when only two were alive reached for itself.

        The board then had no legal world at all: a Demon that dies needs
        an heir, and with no Scarlet Woman and no living Minion there was
        none. `demon_lineages` returned nothing, no timeline could be
        built, and every world died — which looked like a Snake Charmer
        problem because that was the first row added when the board
        tipped over.

        Asked here because there are four Demons with their own kill
        rules and every one of them draws from a pool.
        """
        # And two different players, when it takes more than one.
        pool = [p for p in pool if p != demon and p not in tried]
        if not pool:
            return None
        target = rng.choice(pool)
        # The old coin-flip Monk above is a second guard beside the one
        # `_monk_guards` records, and nothing replaying the night is told
        # about it. An aim it turned away is left off the record, as it
        # always was — taking the coin out would redeal every Trouble
        # Brewing game the tests name by seed. On the roadmap.
        if target == guarded:
            return None
        tried.append(target)
        # The Goon, chosen first, makes it drunk on the spot: this kill
        # fails, and so does every other it makes tonight.
        if _the_goon_answers(d, night, demon, target) \
                or not d.working(demon, night):
            return None
        if _protected(d, night, target, gone=gone):
            return None
        return target

    if kind == "Pukka":
        # Step by step as the flowchart has it (Not_Quite_Vertical's,
        # which the table plays by, 02.10.2026). A drunk or poisoned
        # Pukka never gets here — the early return above is the
        # flowchart's "the token stays where it is, and no attack".
        #
        #   1  Exorcised: it is shown the Exorcist and does not choose.
        #   2  Otherwise it chooses, and that player is poisoned.
        #   3  Was somebody already poisoned from before?
        #   4  Then it attacks them, their own ability still poisoned.
        #   5  Dead or not, that token comes off.
        #
        # The Exorcist had this backwards: `_protected` said yes for
        # every target once the Demon was named, so yesterday's victim
        # lived and the Pukka went on to choose a new one. It is the
        # choosing the Exorcist stops. The night after is the quiet one,
        # because there is no token left to come due.
        out = []
        stale = d.pukka_poisoned
        fresh = None
        if not _exorcised(d, night):
            pool = [p for p in others if p != stale]
            fresh = rng.choice(pool) if pool else None
        # It chose the Goon, first: drunk on the spot. Nobody is
        # poisoned, the old token stays where it is and rests, and there
        # is no attack — the flowchart's drunk Pukka, arrived at halfway
        # through its own turn.
        if fresh is not None and _the_goon_answers(d, night, demon, fresh):
            d.pukka_history[night] = (None, fresh)
            d.demon_aimed[night] = []
            return []
        # The new poison lands *before* the old one comes due (steps 2
        # and 4), so a Tea Lady or an Innkeeper poisoned tonight is no
        # help to the one poisoned yesterday. The night-walk had this
        # right and found it here.
        if fresh is not None:
            d.pukka_marks[night] = fresh
        # The poison comes due as a death, and a death can be stopped: a
        # Tea Lady beside it, a sober Sailor, an Innkeeper's pick. Asked
        # while the victim is still poisoned, so a Sailor or a Fool that
        # was the one poisoned has nothing to be saved by.
        if stale is not None:
            if stale in living \
                    and not _protected(d, night, stale, by_exorcist=False):
                out.append(stale)           # and what its death sets off
            else:                           # is poisoned still
                d.pukka_due.pop(night, None)    # lived: healthy from here
        d.pukka_poisoned = fresh
        # Kept per night as well as carried forward. A replay has to be
        # told which seat's poison came due tonight, and the running
        # value is overwritten before anybody can ask.
        d.pukka_history[night] = (stale, fresh)
        d.demon_aimed[night] = list(out)
        return out

    if kind == "Zombuul":
        # Only on a day when nobody died, and it survives its own first
        # death — which the deaths record rather than this.
        # "If no-one died **today**": the day, not the night before it.
        # A death on night four let nobody wake on night five here, where
        # the rule and the solver say it does (29.09.2026).
        day = night - 1
        if day >= 1 and d.died_on(f"D{day}", f"E{day}"):
            return []
        got = take(others)
        return [got] if got is not None else []

    if kind == "Shabaloth":
        # "A dead player you chose last night might be regurgitated."
        # Just before it wakes, the Storyteller may stand one of them up
        # again — whatever they are, with their ability back. Never
        # played here, so the solver's rule for it had no game to be held
        # against (03.10.2026).
        #
        # Only its own: the same seat holding the Shabaloth both nights.
        # And the one who came back is left alone tonight. Nothing says
        # it must be, but a seat that returns and dies again before dawn
        # is a night the table sees nothing of.
        took = d.shabaloth_took.get(night - 1)
        if took is not None and took[0] == demon:
            lying = [p for p in took[1] if d.deaths.get(p) == f"N{night - 1}"]
            # Nor into a game a Gambler's wrong guess has just ended.
            if lying and not _evil_has_won(d, phase) \
                    and rng.random() < 0.35:
                back = rng.choice(lying)
                d.raise_up(back, phase, "Shabaloth")
                d.regurgitated[night] = back
        # Two a night, and either may be sunk into somebody already dead,
        # so the table often sees one body.
        out = []
        for _ in range(2):
            pool = [p for p in others if p not in out]
            got = take(pool, out)
            if got is not None:
                out.append(got)
        d.shabaloth_took[night] = (demon, list(out))
        return out

    if kind == "Po":
        # It may take nobody, and then three the following night.
        if d.po_charged:
            d.po_charged = False
            out = []
            for _ in range(3):
                pool = [p for p in others if p not in out]
                got = take(pool, out)
                if got is not None:
                    out.append(got)
            return out
        if rng.random() < 0.3:
            d.po_charged = True
            return []
        got = take(others)
        return [got] if got is not None else []

    if kind == "FangGu":
        # Killing an Outsider the first time is a jump: the Outsider lives
        # and becomes an evil Fang Gu, and the old one dies instead. Never
        # played here until now, so every Fang Gu that took an Outsider
        # simply killed it — a game the rules do not allow, and one the
        # solver never objected to because it does not insist on the jump.
        got = take(others)
        # A Fang Gu that cannot die tonight cannot die instead, so the
        # Outsider does not become it either — it dies like anybody, and
        # the Fang Gu lives (Patrick, Lesart J, Weg 3, 20.10.2026: the
        # second half of the ability is an "and"). Not spent: no Outsider
        # became a Fang Gu.
        if got is not None and not d.fanggu_jumped \
                and TEAM[d.role_at(got, phase)] == "outsider" \
                and _protected(d, night, demon, by_exorcist=False):
            return [got]
        if got is not None and not d.fanggu_jumped \
                and TEAM[d.role_at(got, phase)] == "outsider":
            d.fanggu_jumped = True
            d.fanggu_jump = (night, got)      # for the night-walk to replay
            d.deaths[demon] = phase
            d.handovers.append((phase, got))
            d.changes.append((phase, got, "FangGu"))
            d.side_changes.append((phase, got, "FangGu", "evil"))
            return []
        return [got] if got is not None else []

    if kind == "Leviathan":
        # It kills nobody. Only by its jinxes does it choose at all: a
        # living good player each night, never the same one twice, and a
        # Banshee it chooses dies (11.10.2026). The Farmer, the
        # Ravenkeeper and the Sage it chooses use their ability and live,
        # which is theirs to act on.
        if not any(k in d.script.keys for k in LEVIATHAN_CHOOSES_FOR) \
                or _exorcised(d, night):
            return []
        good = [p for p in others if d.side_at(p, phase) == "good"
                and p not in d.lev_picked]
        if not good:
            return []
        target = rng.choice(good)
        d.lev_picked.add(target)
        d.lev_aimed[night] = target       # for the replay, Goon or not
        if _the_goon_answers(d, night, demon, target) \
                or not d.working(demon, night):
            return []
        d.lev_chose[night] = (demon, target)
        held = d.role_at(target, phase)
        if not (held == "Banshee" or (held == "Philosopher"
                                      and d.philosophies.get(target)
                                      == "Banshee")):
            return []
        tried.append(target)
        if _protected(d, night, target):
            return []
        return [target]

    if kind == "Yaggababble":
        # One player might die for each time it said its phrase today,
        # and the Storyteller chooses who — letting one pass now and then.
        # Its own kills, so everything that stops a Demon stops these;
        # but it chooses nobody, so a Goon has nothing to answer.
        out = []
        for _ in range(d.yag_said.get(night - 1, 0)):
            if rng.random() >= 0.85:
                continue
            pool = [p for p in others if p not in out and p not in tried]
            if not pool:
                break
            target = rng.choice(pool)
            if target == guarded:
                continue
            tried.append(target)
            if _protected(d, night, target, gone=out):
                continue
            out.append(target)
        return out

    if kind == "Lleech":
        # Never its own host, which would take it too; and nothing at all
        # once a Mastermind has left it without its ability.
        if _lleech_lost(d, phase):
            return []
        host = d.lleech_hosts.get(demon)
        got = take([p for p in others if p != host])
        return [got] if got is not None else []

    got = take(others)
    return [got] if got is not None else []


def _demon_kill(d, night, rng):
    """One victim, for the callers that still expect a single seat."""
    demon = d.demon_at(f"N{night}")
    living = d.alive_at(f"N{night}")
    if demon not in living:
        return None
    targets = [p for p in living if p != demon]
    if not targets:
        return None
    target = rng.choice(targets)

    monk = _a_working_monk(d, night, living)
    if monk is not None and rng.random() < 0.3 and target != monk:
        return None                             # the Monk guarded them

    if _acts_as(d, target, "Soldier", f"N{night}") \
            and d.working(target, night):
        return None                             # a sober Soldier survives
    return target


# --------------------------------------------------------------------------
# What each character honestly learns
# --------------------------------------------------------------------------

# Characters whose ability fires *because* they died. Everybody else
# stays silent on the night they are killed.
ON_DEATH = frozenset({"Ravenkeeper", "Sage", "Klutz"})


def _woke_for_own_ability(d, p, night, shown=False):
    """Did this seat wake tonight for its own ability — what a Chambermaid
    counts.

    `shown` also says yes for a seat woken to be *shown* something, a Spy
    its grimoire or an Evil Twin its twin. That is still somebody evil
    opening their eyes, which is what a Wraith wakes for.

    Was the body of the Chambermaid's loop until the Wraith needed to ask
    the same question about somebody else (08.10.2026).
    """
    from botc.catalogue import CHARACTERS
    # A Drunk wakes on its token, and everybody else on what they
    # hold *tonight*. This read the deal, so a seat a Snake Charmer
    # or a Pit-Hag had moved was counted on the schedule of a
    # character it no longer was (tenth place the deal has been
    # mistaken for the timeline, 07.10.2026).
    what = d.token(p, f"N{night}") or d.role_at(p, f"N{night}")
    # A Philosopher that has taken an ability wakes when that
    # character would — settled at the table, and what the night
    # order above has done since 29.09. Here it fell through to
    # "once a game, so not tonight" and never woke again.
    if what == "Philosopher" and p in d.philosophies and night > 1:
        what = d.philosophies[p]
        # Took the Trunkenbold: the Townsfolk it was shown. Took the
        # Verrückte: the Demon in play, as a Lunatic (I, 14.10.2026).
        if what == "Drunk":
            what = d.phil_token.get(p) or "Drunk"
        elif what == "Lunatic":
            real = d.demon_at(f"N{night}")
            what = (d.role_at(real, f"N{night}") if real is not None
                    else "Lunatic")
    # A Lunatic lives the night of the Demon it thinks it is —
    # here always the real one — and choosing who it thinks it
    # kills counts (table ruling, 02.10.2026).
    if d.role_at(p, f"N{night}") == "Lunatic":
        real = d.demon_at(f"N{night}")
        what = (d.role_at(real, f"N{night}") if real is not None
                else "Lunatic")
        # Before a Summoner has made the Demon it is shown one all the
        # same and woken as one: an Imp's nights (21.10.2026).
        if real is None and getattr(d, "summoner", None) is not None:
            what = "Imp"
        # With Lil' Monsta the Demon in play is Lil' Monsta, which wakes
        # for nothing of its own (21.10.2026).
        if _babysits(d, real, f"N{night}"):
            what = "LilMonsta"
    char = CHARACTERS[what]
    when, patterns = char.nights, char.wake
    # Back from the dead tonight: "they wake later tonight if they
    # normally would". Regurgitated at the Shabaloth's turn or
    # raised at the Professor's, and dead for every slot before
    # it — an Innkeeper at 9 slept through, a Chambermaid at 70
    # did not.
    by = d.back_at(p, f"N{night}")
    if by is not None and (char.other_night or 0) \
            <= (CHARACTERS[by].other_night or 0):
        return False
    # Woken to be *shown* something rather than to do anything:
    # a Spy the grimoire, an Evil Twin its twin. Neither is their
    # own ability working, so a Chambermaid does not count them —
    # the same rule as a Baron being shown its team.
    #
    # A Marionette is not here. `apparent` has already turned it
    # into the token it was handed, and it counts as that token
    # does (table ruling, 02.10.2026) — which this always did,
    # while the solver said otherwise and no script on the sweep
    # had both characters to show it.
    #
    # Asked with `shown`, they did open their eyes — on their own nights
    # all the same: an Evil Twin is shown its twin on the first night and
    # never again. Returning `shown` here woke a Wraith beside it every
    # night of the game (seed 1623 of the gate, 08.10.2026).
    if what in ("Spy", "EvilTwin") and not shown:
        return False
    if when == "never":
        return False
    # The Assassin and the Professor are woken every night but
    # the first ("at night*") until they spend it, pointing or
    # shaking their head — and this simulator never spends
    # either. The Assassin's wake set holds "first" because it is
    # shown its team then, which is not its ability.
    if what in ("Assassin", "Professor"):
        # Until it is spent: woken on the night it chooses, and
        # not again after.
        spent = (d.professor_chose if what == "Professor"
                 else d.assassin_chose).get(p)
        return night >= 2 and (spent is None or spent >= night)
    # The Philosopher chooses on the first night here, always,
    # and choosing is waking for its ability. Its wake set says
    # "never" or "sometimes", so night one never counted it.
    if what == "Philosopher" and night == 1:
        return p in d.philosophies
    if when == "conditional":
        return bool(_conditionally_woke(d, p, what, night))
    if night == 1:
        # A Demon told its Minions is not acting; a Yaggababble shown its
        # phrase is, and its `nights` says so (11.10.2026).
        return when == "every" or ("first" in patterns
                                   and (char.team != "demon"
                                        or when == "first"))
    return when in ("every", "other")


def _conditionally_woke(d, seat, role, night):
    """Did a character that wakes *sometimes* wake tonight?

    This was a thirty per cent coin, which is wrong for every character
    it covers: whether an Undertaker wakes is not luck, it is whether
    anybody was executed yesterday. A mixed script put a Philosopher
    holding the Chambermaid next to an Undertaker on a night after an
    execution, and the simulator said nobody woke while the solver knew
    somebody had.

    Derived here rather than asked of the solver, as everything in this
    file is — but derived from the facts rather than from a die.
    """
    from botc.info import phase_index
    from botc.roles import TEAM
    if role == "Undertaker":
        return bool(d.died_on(f"E{night - 1}"))
    # The Summoner: shown its bluffs on the first night (its own ability,
    # G, Weg 1) and woken on the night it summons — drunk or not
    # (21.10.2026).
    if role == "Summoner":
        if night == 1:
            return True
        made = getattr(d, "summoned", None)
        return night == (made[0] if made is not None else 3)
    if role in ("Ravenkeeper", "Sage") and seat == getattr(
            d, "lev_chose", {}).get(night, (None, None))[1]:
        return True                       # chosen by the Leviathan: a jinx
    if role == "BountyHunter":
        return (seat, night) in d.bh_woke
    if role == "CultLeader":
        return (seat, night) in d.cult_woke
    if role == "Leviathan":
        return night >= 2 and any(k in d.script.keys
                                  for k in LEVIATHAN_CHOOSES_FOR)
    if role == "Ravenkeeper":
        return d.deaths.get(seat) == f"N{night}"
    if role == "Zombuul":
        # Only on a night after a day when nobody died. On the first it
        # is only told its Minions and bluffs, which is not its ability.
        if night == 1:
            return False
        day = night - 1
        return not d.died_on(f"D{day}", f"E{day}")
    if role == "Godfather":
        # Learns the Outsiders on the first night; after that it is woken
        # only to kill, which is after a day an Outsider died.
        if night == 1:
            return True
        day = night - 1
        return any(TEAM[d.role_at(who, f"D{day}")] == "outsider"
                   for who in d.died_on(f"D{day}", f"E{day}"))
    if role == "Vizier":
        # Only beside a Fearmonger: "the Vizier wakes with the Fearmonger"
        # (their jinx — the waking is all of it that is built, 10.10.2026).
        phase = f"N{night}"
        return any(d.role_at(q, phase) == "Fearmonger"
                   and _woke_for_own_ability(d, q, night)
                   for q in d.alive_at(phase))
    if role == "Wraith":
        # "You wake when other evil players do": whenever another evil
        # seat opens its eyes tonight for its own ability, the Wraith is
        # woken first. Being shown the grimoire counts as opening them;
        # being shown your team on the first night does not, which is the
        # same line the Chambermaid draws (08.10.2026).
        #
        # Drunk or poisoned it is not woken at all (table ruling,
        # 08.10.2026). And a Spy does not look while a Poppy Grower lives
        # (their jinx, as the table reads it), so it opens no eyes.
        phase = f"N{night}"
        if seat in droisoned_at(d, night):
            return False
        blind = any(d.role_at(q, phase) == "PoppyGrower"
                    for q in d.alive_at(phase))
        return any(q != seat and d.side_at(q, phase) == "evil"
                   and d.role_at(q, phase) != "Wraith"
                   and not (blind and d.role_at(q, phase) == "Spy")
                   and _woke_for_own_ability(d, q, night, shown=True)
                   for q in d.alive_at(phase))
    if role == "Courtier":
        # Woken until it names a character, and here it always does so
        # at its first chance: the first night, and the first night after
        # it has come back.
        return (seat, night) in d.courtier_nights
    # Once-a-game characters woke on the night they used it. This said
    # so and then answered "no" for every one of them on every night, so
    # a Chambermaid beside a Seamstress on the first night counted one
    # too few (07.10.2026). When each uses it is this simulator's habit,
    # and the same nights `_for_role` hands out their rows.
    if role == "Seamstress":
        return night == 1
    if role == "Juggler":
        return night == 2                 # answered after the first day
    if role == "Sage":
        return d.deaths.get(seat) == f"N{night}"
    if role == "Philosopher":
        # Only reached before it has chosen; after that the caller asks
        # about the character it took.
        return night == 1 and seat in d.philosophies
    if role in ("Klutz", "Artist", "Savant"):
        return False                      # by day, which is not waking
    if role == "Assassin":
        return False                      # once, and the row would say
    if role == "Nightwatchman":
        # Woken every night until it has pointed, the night it points
        # included — "at night" with no asterisk, so from the first.
        spent = d.nightwatchman_chose.get(seat)
        return spent is None or spent >= night
    if role == "Huntsman":
        # Every night until it chooses, that night included (10.10.2026).
        spent = d.huntsman_night.get(seat)
        return spent is None or spent >= night
    if role == "Choirboy":
        # Woken on the night the Demon killed the King, if alive to wake.
        return d.deaths.get(seat) is None and _a_king_fell(d, night)
    if role == "Widow":
        # Its first night as the Widow, and never again (10.10.2026).
        return night == 1 or d.role_at(seat, f"D{night - 1}") != "Widow"
    if role == "King":
        # Only once the dead equal or outnumber the living, counted when
        # its turn comes — after tonight's kills, itself among them.
        if night < 2 or d.deaths.get(seat) is not None:
            return False
        return _the_dead_have_it(d)
    return False


def _a_king_fell(d, night):
    """Did the Demon kill a King tonight? Its own kill only."""
    phase = f"N{night}"
    return any(_acts_as(d, p, "King", phase)
               for p in d.demon_killed.get(night, ()))


def _really_standing(d):
    """Who is alive right now, a Zombuul under its shroud included.

    Asked in the middle of a night, of the deaths as they stand at that
    moment — the same count `_evil_has_won` makes, for the same reason.
    """
    return [p for p in range(d.n)
            if d.deaths.get(p) is None or p == d.zombuul_up]


def _the_dead_have_it(d):
    """The King's condition: as many dead as living, or more."""
    standing = len(_really_standing(d))
    if d.n - standing >= standing:
        return True
    # "If the Leviathan is in play and at least 1 player is dead, the
    # King learns an alive character each night" (their jinx).
    if d.n - standing < 1 or "Leviathan" not in d.script.keys:
        return False
    phase = f"N{d.nights_played}"
    return any(d.deaths.get(p) is None and d.role_at(p, phase) == "Leviathan"
               for p in range(d.n))


def _droisoned_info(d, seat, night, rng, apparent=None):
    """What a droisoned seat was told, which is the Storyteller's choice.

    Read off what the seat *believes* it is: a Drunk holding a Fortune
    Teller token wakes when a Fortune Teller wakes and hears a Fortune
    Teller's kind of answer. Nobody tells it otherwise.

    Mostly false, and sometimes true by accident — a Storyteller handing
    out only lies would be a Storyteller with a tell.
    """
    if d.deaths.get(seat) is not None and _died_before(d, seat, night):
        return None
    # The token while it lasts, and otherwise what the seat holds
    # *tonight*: poisoned rather than drunk, it is still its own
    # character and wakes on its own schedule. Read off the deal, a seat
    # a Snake Charmer had swapped went on hearing answers for the
    # character it had given away (07.10.2026).
    if apparent is None and d.philosophies.get(seat) == "Drunk" \
            and night > 1:
        apparent = d.phil_token.get(seat)
    apparent = apparent or d.token(seat, f"N{night}") \
        or d.role_at(seat, f"N{night}")
    made = _for_role(d, seat, apparent, night, rng)
    # A drunk Philosopher that took the Klutz still points on dying —
    # in public, so the table sees it; nothing comes of it (13.10.2026).
    if made is None and _took(d, seat, "Klutz", f"N{night}"):
        made = _for_role(d, seat, "Klutz", night, rng)
    if made is None:
        return None
    # A quarter of the time the lie happens to be the truth. The rest of
    # the time it is not.
    #
    # Never under a Vortox, for a real Townsfolk: "even if they are drunk
    # or poisoned, it must be false". The coin was tossed regardless, so
    # a drunk Oracle told the truth beside a working Vortox — and the
    # solver was taught to allow it rather than the simulator to stop
    # (both corrected 02.10.2026).
    false = rng.random() < 0.75
    if (d.token(seat, f"N{night}") is None
            and TEAM[d.role_at(seat, f"N{night}")] == "townsfolk"
            and _vortox_working(d, night)
            and not getattr(made, "is_a_choice", False)):
        false = True
    if false:
        made = _make_false(d, made, night, rng)
    return made


def _in_night_order(d, night):
    """The seats, in the order their characters act tonight.

    Seat order is arbitrary and was what this used. The real order is in
    `data/roles.json`: a Poisoner acts at 7 and an Acrobat at 39, so the
    Acrobat can be poisoned before it chooses — and the Imp at 24 acts
    before the Assassin at 36, so a starpass to an Assassin costs it the
    night, because by slot 36 that seat is holding the Imp.
    
    Read off what each seat *believes* it is, since that is the schedule
    it experiences: a Drunk holding a Fortune Teller token acts in the
    Fortune Teller's slot.

    And off the character it holds **tonight**, not the one it was
    dealt. This read the deal, so an Oracle a Pit-Hag had made a Snake
    Charmer went on acting at the Oracle's 59 — after the Pit-Hag at 16,
    which turned it into a Barber before it swapped with the Demon. At a
    table the Snake Charmer at 11 goes first. One night in 9,458 of
    Sects & Violets, found once the night-walk stopped disagreeing for
    reasons of its own (05.10.2026). The deal mistaken for the timeline,
    a sixth time.

    A seat with no slot keeps its place at the end. It does not act at
    night, so where it sits does not matter — but dropping it would lose
    the ones whose ability fires on their own death.
    """
    from botc.catalogue import CHARACTERS
    field = "first_night" if night == 1 else "other_night"

    def slot(seat):
        held = d.role_at(seat, f"N{night}")
        what = d.token(seat, f"N{night}") or held
        # A Lunatic is woken before the real Demon, at its own slot,
        # whatever Demon it thinks it is.
        if held == "Lunatic":
            what = "Lunatic"
        # A Philosopher that has taken an ability wakes when that
        # character would. It kept its own slot 2, so one holding the
        # Mathematician counted before the Pit-Hag at 16 had turned the
        # drunk real Mathematician into somebody else (29.09.2026).
        if what == "Philosopher" and seat in d.philosophies and night > 1:
            what = d.philosophies[seat]
        got = getattr(CHARACTERS[what], field, 0) if what in CHARACTERS else 0
        return (got if got else 10_000, seat)

    return sorted(range(d.n), key=slot)


# Characters whose row is a *choice* they make early, not information
# they are told late. Their slots sit before every Demon, so the choice
# has to exist before the kills are worked out — an Innkeeper at 9 cannot
# be asked who it protected after the Po at 28 has already swung.
#
# `honest_info` was one pass over everything, which meant choices that
# must precede the night were made in the same breath as readings that
# must follow it. Splitting them is the fix; ordering alone was not
# enough.
# Kept deliberately narrow: only the ones whose choice has to exist
# before a Demon swings, because something later depends on it.
#
# A first attempt listed every character that chooses, which swept in the
# Gambler — whose *death* follows from its guess, so moving it early
# changed who was alive when the Demon picked (it is early now all the
# same, since 02.10.2026: that is the order the night really has, and a
# Pukka's poison made the difference visible) — and the Chambermaid,
# which is not early at all but sits at slot 70. Being wrong about that
# turned one impossible board into five.
# The Snake Charmer is here because its swap changes *who the Demon is*,
# and that has to be settled before the Demon acts.
# The Pit-Hag too, at slot 16: it acted in the late pass, after the kill,
# so it could remake a seat the Demon had already killed or jumped into,
# and create a character that was in play when it really acted
# (29.09.2026).
# The Gambler and the Courtier joined on 02.10.2026. Both act before
# every Demon, and until the Pukka's poison was dated to its turn nothing
# could tell: a Gambler the Pukka poisoned *tonight* had already guessed,
# and was being read as poisoned when it did — so it lived through a
# wrong guess the night-walk rightly said had killed it.
# The Fearmonger joined on 10.10.2026: it points at a player before every
# Demon (17), so a Goon it chose answers before the kills.
CHOOSES_EARLY = frozenset({"Innkeeper", "Sailor", "Monk", "Exorcist",
                           "SnakeCharmer", "PitHag", "Gambler", "Courtier",
                           "DevilsAdvocate", "Lunatic", "Fearmonger",
                           "Widow"})


def early_choices(d, night, rng):
    """The choices made before the Demon acts, in slot order."""
    out = []
    # Who *held* the character when the pass began.
    #
    # A Snake Charmer swap is written at `N{night}` now that it is
    # immediate — and `role_at` then reports the board *after* it, so the
    # charmer's own row was filed under the seat the character ended up
    # at rather than the seat that acted. Three nights of rows attributed
    # to the old Demon.
    #
    # A row belongs to whoever acted, and that is the board as it stood
    # when this pass started. The board afterwards is a different
    # question — the same distinction that made the swap look wrong when
    # written at the night in the first place.
    before = {seat: d.role_at(seat, f"N{night}") for seat in range(d.n)}
    # The Philosopher chooses first on the first night, ahead of every
    # early chooser: a real Courtier it took from is drunk at its own turn
    # and names nobody. It chose in the late pass, so the Courtier's
    # drunkenness still landed (13.10.2026, the gate of group 1).
    if night == 1:
        for seat in _in_night_order(d, night):
            if before[seat] == "Philosopher" and seat not in d.philosophies \
                    and seat in d.alive_at(f"N{night}"):
                made = _for_role(d, seat, "Philosopher", night, rng)
                if made is not None:
                    out.append(made)
                # The Preacher preached before this pass; one this
                # Philosopher has just drunk did it drunk (13.10.2026).
                # What a Pixie is shown, from the night of taking.
                if d.philosophies.get(seat) == "Pixie":
                    shown = _for_role(d, seat, "Pixie", night, rng)
                    # False under a Vortox, and mostly false droisoned, as
                    # any Townsfolk's reading.
                    if shown is not None and (
                            _vortox_working(d, night)
                            or (not d.working(seat, night)
                                and rng.random() < 0.75)):
                        shown = _make_false(d, shown, night, rng)
                    if shown is not None:
                        out.append(shown)
                if d.philosophies.get(seat) == "Preacher":
                    d.preached = [(p, t, since) for p, t, since in d.preached
                                  if not (since == 1 and p != seat)]
                # Shown a grandchild from the night of taking (C, group 6).
                if d.philosophies.get(seat) == "Grandmother":
                    shown = _for_role(d, seat, "Grandmother", night, rng)
                    if shown is not None and (
                            _vortox_working(d, night)
                            or (not d.working(seat, night)
                                and rng.random() < 0.75)):
                        shown = _make_false(d, shown, night, rng)
                    if shown is not None:
                        out.append(shown)
                # Took the Trunkenbold: it lives by the Townsfolk it was
                # shown, and what it is told as that one is made up (I).
                if d.philosophies.get(seat) == "Drunk" \
                        and d.phil_token.get(seat):
                    made = _droisoned_info(d, seat, night, rng,
                                           apparent=d.phil_token[seat])
                    if made is not None:
                        out.append(made)
    for seat in _in_night_order(d, night):
        role = before[seat]
        # A Philosopher that took an early chooser chooses early too. It
        # waited for the late pass, after the kill and the Barber, so one
        # holding the Snake Charmer pointed at a Demon the Barber had only
        # just made at slot 40 (29.09.2026).
        if role == "Philosopher" and night > 1 \
                and d.philosophies.get(seat) in CHOOSES_EARLY:
            role = d.philosophies[seat]
        # The Fearmonger acts at 17, after the Pit-Hag at 16 — so a seat
        # the Pit-Hag has just unmade chooses nothing, and one it has just
        # made a Fearmonger chooses tonight (the gate, seeds 898 and 2928,
        # 10.10.2026). Asked of the board as it stands at its turn.
        # The Widow at 18 the same (10.10.2026).
        now = d.role_at(seat, f"N{night}")
        for late in ("Fearmonger", "Widow"):
            if late in (role, now):
                if now != late:
                    role = None
                else:
                    role = now
                break
        if role is None:
            continue
        if role not in CHOOSES_EARLY:
            continue
        if seat not in d.alive_at(f"N{night}"):
            continue
        made = _for_role(d, seat, role, night, rng)
        if made is not None:
            out.append(made)
    return out


def honest_info(d, night, rng):
    """Every reading the working characters would truthfully get.

    Seats that are drunk or poisoned are left out — their information is
    whatever the Storyteller invented, so there is no honest version.
    """
    out = []
    began = f"E{night - 1}" if night > 1 else "N1"
    for seat in _in_night_order(d, night):
        # Acted in the early pass already — judged by what it held when
        # the night began, since a swap there changes what it holds now.
        # A charmer that swapped and was then drunk by a Sweetheart dying
        # later that night was handed a second, invented Snake Charmer
        # row saying nothing happened (29.09.2026).
        if d.role_at(seat, began) in CHOOSES_EARLY \
                and d.apparent(seat) == d.role_at(seat, began):
            continue
        # Dead before it woke hears nothing, droisoned or not — this was
        # asked only of working seats, so a poisoned Oracle killed at
        # night went on being told something (29.09.2026).
        if d.deaths.get(seat) is not None and _died_before(d, seat, night):
            continue
        if d.deaths.get(seat) == f"N{night}" \
                and d.role_at(seat, f"N{night}") not in ON_DEATH \
                and not _took(d, seat, "Klutz", f"N{night}"):
            continue
        if not d.working(seat, night):
            # A droisoned seat is not silent. It wakes on the schedule of
            # the character it *believes* it is and is told something —
            # whatever the Storyteller likes, which is mostly false and
            # occasionally true by accident.
            #
            # Leaving them out entirely was worse than it looks: a Drunk
            # that says nothing reads as a seat with nothing to prove,
            # while a Drunk that talks confidently and turns out wrong is
            # exactly what draws suspicion at a real table. Their absence
            # removed the main source of honestly-wrong information —
            # which is the thing the calibration run was trying to
            # measure.
            made = _droisoned_info(d, seat, night, rng)
            if made is not None:
                out.append(made)
            continue
        # Already acted in the early pass, so not again here.
        #
        # `early_choices` filters on `CHOOSES_EARLY` and this did not, so
        # every early chooser acted **twice** a night. Invisible for most
        # of them — an Innkeeper simply guarded a second pair — but a
        # Snake Charmer swap is not idempotent: it swapped, then swapped
        # the same pair straight back, leaving four changes on one night
        # and a board with no legal world.
        #
        # It also produced two rows for one character, which is the
        # cheaper thing to have noticed.
        if d.role_at(seat, f"N{night}") in CHOOSES_EARLY:
            continue
        if d.deaths.get(seat) is not None and _died_before(d, seat, night):
            continue
        # The Demon kills before the Empath, Undertaker and Fortune Teller
        # wake, so tonight's victim hears nothing. The Ravenkeeper is the
        # exception - dying is the whole trigger.
        # Dying tonight is the trigger for some characters, not a reason
        # to stay silent. A Ravenkeeper learns a character, a Sage learns
        # two players one of whom killed it, a Klutz points at somebody.
        # Only the Ravenkeeper was listed, so a Sage killed by the Demon
        # said nothing at all.
        role_now = d.role_at(seat, f"N{night}")
        # A Philosopher that took the Klutz points on dying too
        # (13.10.2026).
        if (d.deaths.get(seat) == f"N{night}"
                and role_now not in ON_DEATH
                and not (role_now == "Philosopher"
                         and d.philosophies.get(seat) == "Klutz")):
            continue
        # The character it holds *now*, not the one it was dealt. A
        # Pit-Hag turns somebody into the Sage and the Sage should then
        # act like one; a Philosopher gains an ability and should use it.
        # Reading `d.roles[seat]` meant every mid-game change was
        # invisible to the very seat it happened to.
        role = role_now
        made = _for_role(d, seat, role, night, rng)
        # A Philosopher that took an ability uses it. Gaining one is not
        # a character change — it stays the Philosopher and works two at
        # once — so `role_at` does not see it and the seat said nothing
        # but its own choice, night after night.
        # Not on the first night: it chose in the early pass, and used
        # nothing that night, as before.
        # One that took the Trunkenbold is told, as the Townsfolk it was
        # shown, whatever the Storyteller likes (I, 14.10.2026).
        if made is None and role == "Philosopher" and night > 1 \
                and d.philosophies.get(seat) == "Drunk" \
                and d.phil_token.get(seat):
            made = _droisoned_info(d, seat, night, rng,
                                   apparent=d.phil_token[seat])
            if made is not None:
                out.append(made)
            continue
        if made is None and role == "Philosopher" and night > 1:
            took = d.philosophies.get(seat)
            # An early chooser it took has already acted, in the early pass.
            if took and not (took in CHOOSES_EARLY and night > 1):
                made = _for_role(d, seat, took, night, rng)
        # A mad Pixie whose Townsfolk died has that ability, from the
        # night after (11.10.2026).
        if made is None and role == "Pixie" and night > 1:
            got = _pixie_gain(d, seat)
            if got and night >= got[1] and got[0] not in CHOOSES_EARLY:
                made = _for_role(d, seat, got[0], night, rng)
        if made is None:
            continue
        # A Vortox makes every *Townsfolk* ability yield something false.
        # Not a droisoning — the ability works and what it produces is a
        # lie, which is a stronger claim than poison and constrains the
        # world the other way.
        # A Vortox falsifies information, not choices — so a row that
        # records what a seat *did* passes through untouched, and only
        # what an ability *yielded* is inverted.
        #
        # `_make_false` was flipping every boolean by name, `swapped`
        # among them: a Snake Charmer that chose an ordinary player came
        # out claiming it had swapped with them, which is a thing that
        # cannot happen and made the board unreadable.
        if (TEAM[role] == "townsfolk" and _vortox_working(d, night)
                and not getattr(made, "is_a_choice", False)):
            made = _make_false(d, made, night, rng)
            if made is None:
                continue
        # Turned evil and knowing it, it is told the truth and says what
        # suits it: about half its plain readings come out false
        # (11.10.2026).
        elif _turned_evil_and_knows(d, seat, night) \
                and type(made).__name__ in A_LIAR_MAY_CHANGE \
                and rng.random() < 0.5:
            made = _a_liars_version(d, made, night, rng)
        out.append(made)
    return out


def droisoned_at(d, night, by_day=False):
    """Everybody whose ability is not working tonight, by any cause.

    Not just the Poisoner. Sects & Violets droisons four other ways and
    every one of them is standing — a No Dashii poisons its two nearest
    Townsfolk all game, a Vigormortis poisons beside each Minion it
    killed, a Sweetheart from the night it dies, a Philosopher whoever
    already had the ability it took.

    The Mathematician counts exactly this set, which is why it is worth
    deriving once rather than guessing at the call site. Counting only
    the Poisoner made it say nought while a No Dashii was quietly
    poisoning two, and the solver rightly called the board impossible.
    """
    from botc.roles import TEAM
    phase = f"N{night}"
    living = d.alive_at(phase)
    out = set()

    # Handed the wrong token: wrong every night of the game.
    for p in range(d.n):
        if d.token(p, phase) is not None:
            out.add(p)

    # While the seat that did it is still the Poisoner. Made something
    # else by a Pit-Hag later the same night, its poison is gone with
    # the ability, and a Mathematician asked after that is sober — the
    # solver, which sees no Poisoner that night, already said so
    # (07.10.2026).
    if d.poisoned.get(night) is not None:
        by = getattr(d, "poisoned_by", {}).get(night)
        if by is None or d.role_at(by, phase) == "Poisoner":
            out.add(d.poisoned[night])

    # Whoever chose the Goon first tonight is drunk until dusk — from
    # that moment, so its own choice already fails. Before the Sailor and
    # the Innkeeper below, because one of those drunk by the Goon makes
    # nobody else drunk.
    #
    # An ability ends with the death of whoever has it (table ruling,
    # 03.10.2026): a Goon killed in the night leaves its chooser sober
    # for the day.
    first = getattr(d, "goon_first", {}).get(night)
    if first is not None:
        chooser, goon = first
        if not (by_day and d.deaths.get(goon) == phase):
            out.add(chooser)

    # A Pukka's poison is added last, below: it rests while the Pukka
    # itself is drunk or poisoned, so everybody else has to be known.

    # A swapped Snake Charmer is poisoned for the rest of the game.
    #
    # `perma_poisoned` was written when the swap happened and read in
    # exactly one place — the Snake Charmer's own rule, to stop it
    # swapping twice. `droisoned_at` never consulted it, so every other
    # question about that seat said it was working.
    #
    # Fifth droison source found missing from here, after the Minstrel,
    # the Philosopher, the Innkeeper and the Sailor. The rule stands:
    # anything that droisons belongs *here*, not merely where it happened.
    # ...but only from the night the swap happened, not before it.
    #
    # `perma_poisoned` is the state at the *end* of the game. Handing it
    # over whole marked a seat droisoned on the very night it was
    # swapped, so the Demon could not act on the night it stopped being
    # one. The swap is in `changes` with the phase it happened at, which
    # is where the date comes from.
    #
    # Second time this exact mistake has been made — the first was in
    # `hidden_from`, fixed the same way. A set that means "by the end"
    # is not an answer to "on this night".
    for p in getattr(d, "perma_poisoned", ()):
        if p not in living:
            continue
        since = next((at for at, seat, role in d.changes
                      if seat == p and role == "SnakeCharmer"), None)
        if since is None or phase_index(since) < phase_index(phase):
            out.add(p)

    # An Innkeeper drunks one of the two it protects, and a Sailor one of
    # itself and its target. Both were recorded and neither was in this
    # list, so a Demon the Innkeeper had drunked went on killing — and
    # the night-walk, which does honour it, refused a kill the record
    # showed.
    #
    # Third and fourth droison sources found missing from here, after the
    # Minstrel and the Philosopher. Worth a standing check: anything that
    # droisons must be *here*, not merely recorded where it happened.
    # Each holder's own, and not one a Philosopher that took the same
    # character has drunk — that Philosopher's own counts instead
    # (13.10.2026).
    for role, key in (("Innkeeper", "InnkeeperDrunk"),
                      ("Sailor", "SailorDrunk")):
        for chooser, got in _choices(d, key, night).items():
            holder = _answering(d, chooser, role, phase)
            # Killed later that night, it leaves its drunk sober for the
            # day, like the Goon above: an ability ends with its holder's
            # death (Stelle 61, 20.10.2026).
            if by_day and holder is not None \
                    and d.deaths.get(holder) == phase:
                continue
            if holder is not None and holder in living \
                    and holder not in out \
                    and not _drunk_by_its_philosopher(d, holder, role,
                                                      phase):
                out.add(got)

    # A Philosopher that took an ability drunks whoever really holds that
    # character, for the rest of the game. Never in this list, so a
    # Mathematician standing beside one counted nought where the answer
    # was one — and the solver, which does model it, refused the board.
    for seat, took in (getattr(d, "philosophies", None) or {}).items():
        if d.role_at(seat, phase) != "Philosopher":
            continue                      # no longer the one who took it
        if seat not in living:
            continue
        for other in range(d.n):
            if other != seat and d.role_at(other, phase) == took:
                out.add(other)

    # A Minstrel silences the whole table for the night after a Minion is
    # executed. Never modelled here, and the Acrobat is what exposed it —
    # an Acrobat that lived forbids its pick being droisoned, and the
    # solver knew the table was silenced when the simulator did not.
    day = night - 1
    if day >= 1:
        # Alive tonight, and alive when the Minion hanged: one raised
        # since was not there for its ability to do anything.
        # The holder, or a Philosopher that took it — and not the
        # holder that Philosopher drunk (13.10.2026).
        for minstrel in range(d.n):
            if not _acts_as(d, minstrel, "Minstrel", phase) \
                    or minstrel not in living \
                    or minstrel not in d.alive_at(f"E{day}") \
                    or _drunk_by_its_philosopher(d, minstrel, "Minstrel",
                                                 phase):
                continue
            executed = [p for p in d.died_on(f"E{day}")
                        if TEAM[d.role_at(p, f"D{day}")] == "minion"]
            if executed:
                out |= {p for p in range(d.n) if p != minstrel}

    def nearest_townsfolk(seat):
        got = set()
        for step in (1, -1):
            for gap in range(1, d.n):
                other = (seat + step * gap) % d.n
                if other == seat:
                    break
                if TEAM[d.role_at(other, phase)] == "townsfolk":
                    got.add(other)
                    break
        return got

    for seat in range(d.n):
        # The character it holds tonight, not the one it was dealt: a
        # Snake Charmer that swapped into a Vigormortis or a No Dashii is
        # the one poisoning now. Reading the deal stopped the poison the
        # moment the dealt seat died (29.09.2026) — the deal mistaken for
        # the timeline once more.
        role = d.role_at(seat, phase)
        if role == "NoDashii" and seat in living:
            out |= nearest_townsfolk(seat)
        elif role == "Sweetheart" or (
                role == "Philosopher"
                and (getattr(d, "philosophies", None) or {}).get(seat)
                == "Sweetheart"):
            # A Philosopher that took it as well, and not a real one that
            # Philosopher had drunk when it died (13.10.2026).
            gone = d.deaths.get(seat)
            if gone and phase_index(gone) <= phase_index(phase) \
                    and _falls_as(d, seat, "Sweetheart", gone):
                # Somebody, and the Storyteller never says who — the
                # simulator has to pick, so it picks the seat after.
                out.add((seat + 1) % d.n)
        elif role == "Vigormortis" and seat in living:
            for other in range(d.n):
                if TEAM[d.role_at(other, phase)] != "minion":
                    continue
                gone = d.deaths.get(other)
                # Only the Minions it killed — the card says so. Every
                # dead Minion used to count, an executed one too.
                if not gone or gone[0] != "N":
                    continue
                k = int(gone[1:])
                killer = d.demon_at(gone)
                if other not in d.demon_killed.get(k, ()) or killer is None \
                        or d.role_at(killer, gone) != "Vigormortis":
                    continue
                # The poison triggers and registers on the night the
                # Vigormortis killed, not the night after. Settled by
                # asking rather than by reasoning: it was a real
                # disagreement between the simulator and the solver, and
                # the solver had it right.
                #
                # The tempting argument for the other reading — a
                # Mathematician counts abilities that went wrong *since
                # dawn*, and a Townsfolk poisoned at 3am has not used an
                # ability while poisoned yet — is simply not how the
                # poison works. It registers when it lands.
                if gone and phase_index(gone) <= phase_index(phase):
                    beside = sorted(nearest_townsfolk(other))
                    if beside:
                        out.add(beside[0])

    # The Courtier: whoever holds the named character is drunk for three
    # nights and three days. Sixth droison source found missing from this
    # list — the row was written and nothing happened, so a Courtier that
    # named the Mastermind left it working, and the Demon's execution
    # ran on for a day the rules do not give (29.09.2026).
    #
    # Only while the Courtier lives: a drunkenness rests when the one
    # causing it dies (table ruling, 02.10.2026). It ran its three days
    # regardless, so a Gambler a dead Courtier had named went on
    # surviving wrong guesses.
    #
    # And it *ends* there (03.10.2026): a Courtier that comes back is a
    # new one, and what the old one named stays sober until it names
    # again. So each naming runs from its night until three nights are
    # up or the Courtier has died, whichever comes first.
    for since, holder, courtier in getattr(d, "courtier_drunks", ()):
        if not since <= night <= since + 2:
            continue
        died = any(phase_index(f"N{since}") <= phase_index(at)
                   < phase_index(phase) for at in d.deaths_of(courtier))
        # The character is drunk, not the player: one who has become
        # somebody else since is sober (Stelle 70, Patrick, 22.10.2026).
        # And a Courtier that has become somebody else has no ability
        # left to keep it drunk, as the solver has it.
        named = d.role_at(holder, f"N{since}")
        if d.role_at(holder, phase) != named \
                or d.role_at(courtier, phase) != d.role_at(
                    courtier, f"N{since}"):
            continue
        if not died:
            out.add(holder)

    # The Preacher's silenced Minions and the Xaan's night, both asked
    # against what came before them and not each other — the solver's
    # one pass (10.10.2026). And the Puzzlemaster's drunk, all game.
    silenced = set()
    for preacher, target, since in getattr(d, "preached", ()):
        if since > night or not _acts_as(d, preacher, "Preacher", phase):
            continue
        if preacher not in (d.alive_at(f"D{night}") if by_day else living):
            continue
        if preacher not in out \
                and TEAM[d.role_at(target, phase)] == "minion":
            silenced.add(target)
    xaan = next((p for p in range(d.n)
                 if d.role_at(p, phase) == "Xaan"), None)
    if xaan is not None and xaan not in out \
            and _has_its_ability(d, xaan, phase) \
            and night == sum(1 for r in d.roles
                             if TEAM[r] == "outsider"):
        silenced |= {p for p in range(d.n)
                     if TEAM[d.role_at(p, phase)] == "townsfolk"}
    out |= silenced
    if getattr(d, "puzzle_drunk", None) is not None:
        # Not while a Philosopher that took the Puzzlemaster lives and
        # drunks the real one (13.10.2026); that Philosopher's own instead.
        held = next((p for p in range(d.n)
                     if d.role_at(p, phase) == "Puzzlemaster"), None)
        if held is None or not _drunk_by_its_philosopher(
                d, held, "Puzzlemaster", phase):
            out.add(d.puzzle_drunk)
    for seat, drunk in getattr(d, "puzzle_drunks", {}).items():
        if _took(d, seat, "Puzzlemaster", phase):
            out.add(drunk)
    # The drunk Village Idiot, all game (11.10.2026).
    if getattr(d, "vi_drunk", None) is not None:
        out.add(d.vi_drunk)

    # A Widow's poison, for as long as it lives — resting while it is
    # drunk or poisoned itself (10.10.2026). After everybody else, so its
    # own state is known; before the Pukka, whose poison it can stop.
    for widow, target, since in getattr(d, "widow_poison", ()):
        if since > night or d.role_at(widow, phase) != "Widow":
            continue
        if widow not in (d.alive_at(f"D{night}") if by_day else living):
            continue
        if widow not in out:
            out.add(target)

    # A Lleech's host, for as long as the Lleech lives and has its
    # ability — resting while it is drunk or poisoned (11.10.2026).
    if not _lleech_lost(d, phase):
        for lleech, host in getattr(d, "lleech_hosts", {}).items():
            if d.role_at(lleech, phase) != "Lleech":
                continue
            if lleech not in (d.alive_at(f"D{night}") if by_day
                              else living):
                continue
            if lleech not in out and host in living:
                out.add(host)

    # The Pukka, last. Whoever it poisoned on its turn tonight, and
    # whoever was still carrying its token from before: poisoned from the
    # Pukka's turn, through the day, and into the next night until the
    # Pukka's turn comes round again. That last stretch was missing — the
    # poison stopped at dusk, so a Sailor poisoned yesterday was sober
    # again and unkillable on the night the poison came for it.
    #
    # And it rests while the Pukka itself is drunk or poisoned, which is
    # why this is asked after everybody else is settled.
    pukka = _live_pukka(d, night)
    if pukka is not None and pukka not in out:
        for marked in (d.pukka_marks.get(night), d.pukka_due.get(night)):
            if marked is not None:
                out.add(marked)
    return out


def _droisoned_without_preaching(d, night):
    """`droisoned_at` with every sermon set aside, for the Acrobat."""
    kept = d.preached
    d.preached = []
    try:
        return droisoned_at(d, night)
    finally:
        d.preached = kept


def _vortox_working(d, night):
    """Is a Vortox in play, alive, and not droisoned itself?"""
    phase = f"N{night}"
    seat = d.demon_at(phase)
    if seat is None or d.role_at(seat, f"N{night}") != "Vortox":
        return False
    return seat in d.alive_at(phase) and d.working(seat, night)


def _make_false(d, info, night, rng):
    """Turn a true reading into a false one, by its shape.

    Any wrong number for a count; *neither* of the two for a pair; the
    opposite for a yes or no. Returns None when there is no false version
    to give, which should not happen but is better than inventing one.
    """
    kind = type(info).__name__

    if kind == "VillageIdiotInfo":
        # The other side from the one it is really on: a faux paw's evil
        # is already a false thing to be told (11.10.2026).
        info.evil = d.side_at(info.target, f"N{night}") != "evil"
        return info
    if kind == "BountyHunterInfo":
        # Somebody who does not read evil at all — and that is who it
        # knows now: "when that shown player dies, the Bounty Hunter
        # learns a new player".
        phase = f"N{night}"
        good = [p for p in range(d.n) if p != info.player
                and not _reads_evil(d, p, phase)
                and True not in evil_registrations(d.role_at(p, phase))]
        if not good:
            return None
        d.bh_seen.setdefault(info.player, set()).discard(info.target)
        info.target = rng.choice(good)
        d.bh_known[info.player] = info.target
        d.bh_seen[info.player].add(info.target)
        return info
    if kind == "PixieLearned":
        held = {d.role_at(p, f"N{night}") for p in range(d.n)}
        town = list(d.script.townsfolk) if d.script else list(TOWNSFOLK)
        spare = [k for k in town if k not in held]
        if not spare:
            return None
        info.role = rng.choice(spare)
        return info

    if hasattr(info, "count") and info.count is not None:
        wrong = [n for n in range(0, d.n) if n != info.count]
        info.count = rng.choice(wrong)
        return info

    if kind == "FortuneTeller" and _vortox_working(d, night):
        # A yes on a Recluse is already false (table ruling, 07.10.2026),
        # so flipping an honest yes that came from one gave a *true* no —
        # found beside a Widow's batch, a Vortox board where the Widow had
        # poisoned the Recluse one night and not the next (10.10.2026).
        # False means: yes exactly when neither is a Demon or the herring.
        # Only under a Vortox, the one place falseness is asked: a drunk
        # Fortune Teller may be told anything, and flipping stays as it
        # was so no Trouble Brewing game is dealt anew.
        phase = f"N{night}"
        really = any(TEAM[d.role_at(x, phase)] == "demon"
                     or _babysits(d, x, phase)
                     for x in (info.a, info.b)) \
            or d.red_herring in (info.a, info.b)
        info.yes = not really
        return info

    # Every yes-or-no field, by name. A single `yes` was enough until
    # the Flowergirl and the Town Crier arrived with their own booleans
    # and quietly came through a Vortox unchanged — the reading stayed
    # true, and the solver rightly called the board impossible.
    # `swapped` and `triggered` are deliberately not here: they record
    # what happened, not what somebody was told, and a Vortox does not
    # reach them.
    for field in ("yes", "voted", "nominated", "same", "answer"):
        if getattr(info, field, None) is not None:
            setattr(info, field, not getattr(info, field))
            return info

    if kind in ("Undertaker", "Ravenkeeper") and getattr(info, "role", None):
        # A Vortox makes it name the wrong character.
        #
        # There was no case for a row that carries a *role*, so an
        # Undertaker on a Vortox board announced the truth and the solver
        # rightly refused the game. Found on a board where a Philosopher
        # was working the ability, which is why it looked like a
        # Philosopher problem — it is not, a plain Undertaker was always
        # wrong here too.
        #
        # Twice mended (07.10.2026). The case rebuilt the row from night,
        # player and character and so dropped `target`: every falsified
        # Undertaker was speaking of seat 0, executed or not. And the
        # Ravenkeeper had no case at all — no script the sweep knew put
        # one beside a Vortox, and the mixed ones do.
        #
        # Wrong means: not what the seat really was. What it could
        # register as is beside the point — showing a Spy as the Mayor is
        # legal and still false.
        when = f"E{night - 1}" if kind == "Undertaker" else f"N{night}"
        real = d.role_at(info.target, when)
        wrong = [k for k in d.script.keys if k != real]
        if not wrong:
            return None
        info.role = rng.choice(wrong)
        return info

    if kind == "NobleInfo":
        # A Vortox makes it false, and false here means the three shown
        # were **not** exactly one evil by registration — none of them,
        # or two, or all three.
        #
        # It has no count to spoil and no role to swap, so the generic
        # paths above walked straight past it and left a true reading on
        # a Vortox board. The solver rightly refused the whole game.
        #
        # **Really** evil, since 07.10.2026 ("Adlige auch"): this drew
        # only from seats that could register one way, so that no
        # registration made the three exactly one. What is so is what
        # counts — two good players and a Recluse is nobody evil, and
        # that is false enough for any Vortox.
        phase = f"N{night}"
        evil = [p for p in range(d.n) if d.side_at(p, phase) == "evil"]
        good = [p for p in range(d.n) if d.side_at(p, phase) == "good"]
        if len(good) >= 3:
            picked = rng.sample(good, 3)          # nobody evil: false
        elif len(evil) >= 2 and good:
            picked = rng.sample(evil, 2) + [rng.choice(good)]
        elif len(evil) >= 3:
            picked = rng.sample(evil, 3)
        else:
            return None                           # cannot be made false
        rng.shuffle(picked)
        return NobleInfo(info.night, info.player,
                         a=picked[0], b=picked[1], c=picked[2])

    if kind == "StewardInfo":
        # Shown somebody who is not good. A Spy will do: it is evil
        # however it registers, so naming it is already false.
        evil = [p for p in range(d.n) if p != info.player
                and d.side_at(p, f"N{night}") == "evil"]
        if not evil:
            return None
        info.target = rng.choice(evil)
        return info

    if kind == "ChoirboyInfo":
        # Anybody but the Demon.
        demon = d.demon_at(f"N{night}")
        others = [p for p in range(d.n) if p not in (info.player, demon)]
        if not others:
            return None
        info.target = rng.choice(others)
        return info

    if kind == "KnightInfo":
        # "Must include the Demon" — the wiki's own Vortox example.
        demon = d.demon_at(f"N{night}")
        others = [p for p in range(d.n) if p not in (info.player, demon)]
        if demon is None or demon == info.player or not others:
            return None
        info.a, info.b = sorted([demon, rng.choice(others)])
        return info

    if kind == "ShugenjaInfo":
        # The other way — unless it was a tie, which is arbitrary and so
        # has no false version. Then either answer is as good as before.
        nearest = _nearest_evil_each_way(d, info.player, night)
        if nearest[1] == nearest[-1]:
            return info
        truly = nearest[-1] is None or (
            nearest[1] is not None and nearest[1] < nearest[-1])
        info.clockwise = not truly
        return info

    if kind == "KingInfo":
        # A character nobody alive holds. A King told nothing was not
        # told anything false either: it simply was not woken.
        if not info.role:
            return info
        phase = f"N{night}"
        held = {d.role_at(p, phase) for p in _really_standing(d)}
        spare = [k for k in d.script.keys if k not in held]
        if not spare:
            return None
        info.role = rng.choice(spare)
        return info

    if kind == "DreamerInfo":
        # Neither of the two is what the seat really is.
        #
        # Only that. An earlier version also excluded everything the seat
        # could *register* as, to stop a Spy being shown as the Slayer —
        # and that was wrong on the rules. Misregistration makes
        # information **legal, not true**: the seat is still a Spy, so
        # showing it as the Slayer is already false and a Vortox may
        # produce it freely.
        #
        # It did paper over something real, which is written up at
        # `registers_as_role` in info.py: the solver asks one question
        # where there are two.
        real = d.role_at(info.target, f"N{night}")
        good = [k for k in d.script.townsfolk + d.script.outsiders
                if k != real]
        evil = [k for k in d.script.minions + d.script.demons if k != real]
        if not good or not evil:
            return None
        info.good_role, info.evil_role = rng.choice(good), rng.choice(evil)
        return info



    if kind == "SageInfo":
        # Neither of the two is the Demon that killed it.
        demon = d.demon_at(f"N{night}")
        others = [p for p in range(d.n) if p not in (info.player, demon)]
        if len(others) < 2:
            return None
        info.a, info.b = sorted(rng.sample(others, 2))
        return info

    if kind == "GrandmotherInfo":
        # A false character for her grandchild, but still a *good* one.
        # Seeing only good characters is what a Grandmother's ability
        # does, and a Vortox falsifies what an ability yields without
        # changing what kind of thing it yields.
        real = d.role_at(info.target, f"N{night}")
        spare = [k for k in d.script.townsfolk + d.script.outsiders
                 if k != real]
        if not spare:
            return None
        info.role = rng.choice(spare)
        return info

    if kind in ("Washerwoman", "Librarian", "Investigator"):
        # A Librarian told *nobody* has no pair to alter, and returning
        # it unchanged left a **true** reading on a Vortox board — which
        # is the one thing a Vortox forbids. The false version of "no
        # Outsiders in play" is naming a pair, so build one.
        if info.a is None or info.b is None:
            others = [p for p in range(d.n) if p != info.player]
            if len(others) < 2 or not d.script.outsiders:
                return None               # nothing false can be said
            a, b = sorted(rng.sample(others, 2))
            info.a, info.b = a, b
            info.role = rng.choice(list(d.script.outsiders))
            return info
        # Neither of the pair is the character named.
        pool = {"Washerwoman": d.script.townsfolk,
                "Librarian": d.script.outsiders,
                "Investigator": d.script.minions}[kind]
        spare = [k for k in pool
                 if k not in (d.role_at(info.a, f"N{night}"),
                              d.role_at(info.b, f"N{night}"))]
        if not spare:
            return None
        info.role = rng.choice(spare)
        return info

    # Anything with no false version worth inventing — a Savant's pair,
    # an Artist's question — is left alone rather than mangled.
    return info


def _died_before(d, seat, night):
    from botc.info import phase_index
    return phase_index(d.deaths[seat]) < phase_index(f"N{night}")


def _for_role(d, seat, role, night, rng):
    if night == 1:
        # What the seat holds *now*, not what it was dealt.
        #
        # A Snake Charmer acts at first-night slot 20 and a Washerwoman
        # reads at 33, so a swap has already happened when she is shown
        # her pair — and reading `d.roles` showed her a character that
        # seat no longer held. The solver then had to poison her to
        # explain it, and an Empath beside the swapped seat had nothing
        # consistent left to sit on.
        #
        # Ninth place the deal has been mistaken for the timeline.
        here = f"N{night}"
        if role == "Washerwoman":
            return _pair_info(d, seat, night, rng, Washerwoman,
                              lambda p: TEAM[d.role_at(p, here)] == "townsfolk",
                              team="townsfolk")
        if role == "Investigator":
            return _pair_info(d, seat, night, rng, Investigator,
                              lambda p: TEAM[d.role_at(p, here)] == "minion",
                              team="minion")
        if role == "Librarian":
            outsiders = [p for p in range(d.n)
                         if TEAM[d.role_at(p, here)] == "outsider"]
            if not outsiders:
                return Librarian(1, seat, a=None, b=None, role="")
            return _pair_info(d, seat, night, rng, Librarian,
                              lambda p: TEAM[d.role_at(p, here)] == "outsider",
                              team="outsider")
        if role == "Chef":
            # By what each seat reads as: the faux paw evil (11.10.2026).
            pairs = sum(1 for i in range(d.n)
                        if _reads_evil(d, i, here)
                        and _reads_evil(d, (i + 1) % d.n, here))
            return Chef(1, seat, count=pairs)

    if role == "Pixie" and night == 1:
        # One Townsfolk in play; a Drunk holding its token is shown one
        # off the script.
        learned = d.pixie_learned.get(seat)
        if learned is None:
            town = list(d.script.townsfolk) if d.script else list(TOWNSFOLK)
            learned = rng.choice(town)
        return PixieLearned(1, seat, role=learned)

    if role == "BountyHunter":
        return _bounty_hunter_is_shown(d, seat, night, rng)

    if role == "VillageIdiot":
        # Any player, and their side — the faux paw read evil.
        others = [p for p in range(d.n) if p != seat]
        if not others:
            return None
        target = rng.choice(others)
        return VillageIdiotInfo(night, seat, target=target,
                                evil=_reads_evil(d, target, f"N{night}"))

    if role == "Noble" and night == 1:
        # Three players, exactly one evil **by registration** — two who
        # register good and one who registers evil. The Storyteller is
        # choosing among registrations, so a Spy may sit among the good
        # two and a Recluse may be the evil one.
        #
        # The Noble may be shown itself, which is legal and useless.
        phase = "N1"
        # Whether a seat *could* be shown as evil, then a coin for the
        # ones that may go either way — a Recluse the Storyteller chose
        # to mark, a Spy it chose to hide.
        def shown_evil(p):
            if _reads_evil(d, p, phase) and d.side_at(p, phase) == "good":
                return True               # the faux paw (11.10.2026)
            # By the side it is on now, which is not always its
            # character's: a Bounty Hunter's evil Townsfolk reads evil,
            # and a Cult Leader as whichever it is tonight (11.10.2026).
            if _acts_as_cult_leader(d, p, phase):
                return d.side_at(p, phase) == "evil"
            opts = sorted(evil_registrations(d.role_at(p, phase),
                                             d.side_at(p, phase)))
            return rng.choice(opts) if len(opts) > 1 else opts[0]
        evil = [p for p in range(d.n) if shown_evil(p)]
        good = [p for p in range(d.n) if p not in evil]
        if not evil or len(good) < 2:
            return None
        # **Three different players.** The two good ones are drawn from
        # the seats that are not the evil one, so the same seat cannot
        # appear twice — it named one seat twice and gave only two
        # distinct players, which is not a reading the card allows.
        one = rng.choice(evil)
        rest = [p for p in good if p != one]
        if len(rest) < 2:
            return None
        picked = [one] + rng.sample(rest, 2)
        rng.shuffle(picked)
        return NobleInfo(1, seat, a=picked[0], b=picked[1], c=picked[2])

    if role == "Steward" and night == 1:
        # One good player. Usually really good; now and then a Spy the
        # Storyteller chose to show as good, which is the wiki's example.
        phase = "N1"
        good = [p for p in range(d.n) if p != seat
                and not _reads_evil(d, p, phase)]
        # A droisoned character cannot misregister (table rule): a
        # poisoned Spy is a Spy and reads as one.
        spies = [p for p in range(d.n) if p != seat
                 and d.side_at(p, phase) == "evil"
                 and False in evil_registrations(d.role_at(p, phase), "evil")
                 and not _acts_as_cult_leader(d, p, phase)
                 and d.working(p, night)]
        if spies and rng.random() < 0.25:
            return StewardInfo(1, seat, target=rng.choice(spies))
        if not good:
            return None
        return StewardInfo(1, seat, target=rng.choice(good))

    if role == "Knight" and night == 1:
        # Two players who are not the Demon — Minions among them, as
        # likely as anybody else.
        demon = d.demon_at("N1")
        others = [p for p in range(d.n) if p not in (seat, demon)]
        if len(others) < 2:
            return None
        a, b = sorted(rng.sample(others, 2))
        return KnightInfo(1, seat, a=a, b=b)

    if role == "Shugenja" and night == 1:
        # Which way its closest evil player sits; a coin on a tie.
        nearest = _nearest_evil_each_way(d, seat, night)
        if nearest[1] is None and nearest[-1] is None:
            return None
        if nearest[1] == nearest[-1]:
            return ShugenjaInfo(1, seat, clockwise=rng.random() < 0.5)
        clockwise = nearest[-1] is None or (
            nearest[1] is not None and nearest[1] < nearest[-1])
        return ShugenjaInfo(1, seat, clockwise=clockwise)

    if role == "King" and night > 1:
        # A living character, once the dead equal or outnumber the
        # living. Counted now — this runs after the night's kills — and
        # with a Zombuul under its shroud among the living.
        phase = f"N{night}"
        standing = _really_standing(d)
        if not _the_dead_have_it(d):
            # It learned nothing, and mostly nobody remarks on that. But
            # it is said when the board *looks* as though it should have
            # — as many crossed off as not — which is the one time it
            # tells the table something.
            shown = sum(1 for p in range(d.n) if d.deaths.get(p) is None)
            if d.n - shown >= shown or rng.random() < 0.3:
                return KingInfo(night, seat, role="")
            return None
        who = rng.choice(standing)
        return KingInfo(night, seat, role=d.role_at(who, phase))

    if role == "Nightwatchman" and seat not in d.nightwatchman_chose \
            and rng.random() < 0.4:
        # Points at somebody, once a life, on a night of its choosing —
        # any player, alive or dead. That player is woken and shown who
        # the Nightwatchman is: unless it has no ability tonight, and
        # then nobody is woken at all.
        phase = f"N{night}"
        target = rng.choice([p for p in range(d.n) if p != seat])
        d.nightwatchman_chose[seat] = night
        real = (d.role_at(seat, phase) == "Nightwatchman"
                or d.philosophies.get(seat) == "Nightwatchman")
        # A Drunk holding the token points too, and nothing comes of it:
        # it has no ability to choose anybody *with*, so a Goon does not
        # stir and the replay is told nothing.
        gooned = False
        if real:
            d.nightwatchman_aimed.setdefault(night, {})[seat] = target
            gooned = _the_goon_answers(d, night, seat, target)
        if real and not gooned and d.working(seat, night) \
                and d.side_at(target, phase) == "good" \
                and rng.random() < 0.85:
            shown = seat
            if _vortox_working(d, night):
                # False, like everything else a Townsfolk's ability
                # yields under a Vortox: the wrong player is pointed at.
                wrong = [p for p in range(d.n) if p not in (seat, target)]
                shown = rng.choice(wrong) if wrong else None
            if shown is not None:
                d.said_by_others.append(
                    NightwatchmanSeen(night, target, shown=shown))
        return NightwatchmanChoice(night, seat, target=target)

    if role == "Balloonist":
        # A player whose character *type* differs from the one shown last
        # night — and the Balloonist is never told the type.
        #
        # Registration is what makes this work: a Recluse counts as
        # Outsider, Minion or Demon, so the Storyteller has room. The
        # shown player may be alive or dead, good or evil.
        #
        # A droisoned Balloonist may be shown the same type, and that
        # player still becomes "the previous" for the night after — which
        # is the part of the card easiest to get wrong.
        from botc.catalogue import CHARACTERS
        phase = f"N{night}"
        last = d.balloonist_last.get(seat)

        def types(p, when):
            """What that seat could have been shown as, **then**.

            Not now. A seat shown on night one may have swapped into a
            Demon by night two, and what the Balloonist saw was the
            character it held when the token was pointed at. Comparing
            against what it has since become let a townsfolk follow a
            townsfolk, and the solver — which asks at the night shown —
            called the board impossible.

            Taken on my own reading rather than a ruling: the card says
            "a different character type than last night", and last
            night's type is what it was last night. Reversible if the
            table says otherwise.
            """
            r = d.role_at(p, when)
            return {TEAM[r]} | set(CHARACTERS[r].registers)

        others = [p for p in range(d.n) if p != seat]
        if last is not None and d.working(seat, night):
            was, shown_at = last
            others = [p for p in others
                      if types(p, phase) - types(was, shown_at)]
        if not others:
            return None
        shown = rng.choice(others)
        d.balloonist_last[seat] = (shown, phase)
        return BalloonistInfo(night, seat, target=shown)

    if role == "Empath":
        nb = _neighbours(d, seat, night)
        # By the side the seat is on tonight, not the character it was
        # dealt: an Ogre that picked an evil player is evil from day one.
        return Empath(night, seat,
                      count=sum(1 for p in nb
                                if _reads_evil(d, p, f"N{night}")))

    if role == "FortuneTeller":
        others = [p for p in d.alive_at(f"N{night}")
                  if p != seat and d.deaths.get(p) != f"N{night}"]
        if len(others) < 2:
            return None
        a, b = rng.sample(others, 2)
        demon = d.demon_at(f"N{night}")
        # A Recluse registers as the Demon whenever the Storyteller
        # likes, so a Fortune Teller can ping on one — which is the whole
        # reason a Recluse is a nuisance to its own team, and something
        # the simulator never produced.
        recluse = [p for p in (a, b)
                   if d.role_at(p, f"N{night}") == "Recluse"]
        yes = (demon in (a, b) or d.red_herring in (a, b)
               or (bool(recluse) and rng.random() < 0.35))
        return FortuneTeller(night, seat, a=a, b=b, yes=yes)

    # --- Sects & Violets ------------------------------------------------

    if role == "Clockmaker" and night == 1:
        # Steps from the Demon to its nearest Minion, the shorter way
        # round the circle.
        demon = d.demon_at("N1")
        # "The Summoner registers as the Demon to the Clockmaker" (their
        # jinx): counted from it, and 0 with no other Minion (F,
        # 21.10.2026).
        summoner = getattr(d, "summoner", None)
        if demon is None and summoner is not None:
            demon = summoner
        if demon is None:
            return None
        # The Minions at its turn, after a Snake Charmer that swapped
        # with Lil' Monsta's babysitter (21.10.2026); the deal otherwise,
        # as always.
        held = (d.role_at if getattr(d, "lil_monsta", False)
                else lambda m, _phase: d.roles[m])
        gaps = [min((m - demon) % d.n, (demon - m) % d.n)
                for m in range(d.n)
                if m != demon and TEAM[held(m, "N1")] == "minion"]
        if not gaps:
            if demon == summoner:
                return ClockmakerInfo(1, seat, count=0)
            return None
        return ClockmakerInfo(1, seat, count=min(gaps))

    if role == "Dreamer":
        # One good character and one evil, and the target really is one
        # of them. Which of the two is true is the Storyteller's choice
        # and it never says.
        others = [p for p in range(d.n) if p != seat]
        if not others:
            return None
        target = rng.choice(others)
        # One good character and one evil, and — while the Dreamer is
        # sober and healthy — one of them is what the target really is.
        # The Storyteller chooses the other freely.
        #
        # This read `d.apparent(target)`, which is what the *target*
        # believes it is. A Drunk holding a Monk token would be shown as
        # the Monk, and the reading would be false while nothing was
        # wrong with the Dreamer. What a seat believes is not what it is.
        real = d.role_at(target, f"N{night}")
        pool_good = [k for k in d.script.townsfolk + d.script.outsiders
                     if k != real]
        pool_evil = [k for k in d.script.minions + d.script.demons
                     if k != real]
        if is_evil(real):
            evil_shown = real
            good_shown = rng.choice(pool_good) if pool_good else real
        else:
            good_shown = real
            evil_shown = rng.choice(pool_evil) if pool_evil else real
        return DreamerInfo(night, seat, target=target,
                           good_role=good_shown, evil_role=evil_shown)

    if role == "Mathematician" and night > 1:
        # How many abilities went wrong since dawn. The simulator knows
        # exactly, because it is the thing that decides the droisoning —
        # which is the one reading here that is easier for the simulator
        # than for the solver.
        # Only the living: a dead player has no ability to go wrong. See
        # the solver's `_possible_impairment_counts`.
        living = set(d.alive_at(f"N{night}"))
        return MathematicianInfo(
            night, seat, count=len(droisoned_at(d, night) & living))

    if role == "Juggler" and night == 2:
        # Guessed publicly on the first day, answered the night after —
        # so the row sits on night two and carries the guesses with it.
        others = [p for p in range(d.n) if p != seat]
        if len(others) < 2:
            return None
        how_many = rng.randint(1, min(5, len(others)))
        picked = rng.sample(others, how_many)
        guesses, right = [], 0
        for who in picked:
            # Mostly a guess at what they claim, sometimes a wild one.
            if rng.random() < 0.5:
                said = d.apparent(who)
            else:
                said = rng.choice(list(d.script.townsfolk))
            guesses.append({"player": who, "role": said})
            # A guess counts if the seat **registers** as what was said,
            # not only if it holds it exactly.
            #
            # A Spy registers as any Townsfolk, so guessing "Washerwoman"
            # at a Spy is a right guess the Storyteller may allow. This
            # counted only exact matches, so the number it announced was
            # lower than the solver could reach — and the board had no
            # legal world, because no impairment can make a Juggler
            # *undercount*.
            if registers_as_role(d.role_at(who, f"D{night - 1}"), said):
                right += 1
        return JugglerInfo(night, seat, guesses=tuple(guesses), count=right)

    # A Savant is a day ability: see `_savant_visits`, run once the
    # night is over.

    # The ninth three (12.10.2026): what the Storyteller believes, kept
    # and not weighed, so any answer will do — at random (way 1). Every
    # night, the first included.
    if role == "HighPriestess":
        # Any player, alive or dead, good or evil; here never itself.
        return HighPriestessInfo(night, seat, target=rng.choice(
            [p for p in range(d.n) if p != seat]))
    if role == "General":
        return GeneralInfo(night, seat,
                           says=rng.choice(("good", "evil", "neither")))

    if role == "Artist" and night == 1:
        # One yes-or-no question, once a game. Also kept and not weighed.
        who = rng.choice([p for p in range(d.n) if p != seat])
        return ArtistInfo(night, seat,
                          question=f"is seat {who + 1} evil?",
                          answer=is_evil(d.roles[who]))

    if role == "EvilTwin" and night == 1:
        # It and one good player know each other. Recorded from the evil
        # side, since that is the seat that always knows.
        # Somebody else, and good *now* rather than in the deal.
        #
        # A Pit-Hag can make a good seat the Evil Twin, and reading
        # `d.roles` still called that seat good — so it picked itself as
        # its own twin and the row named one seat twice. The deal is not
        # the timeline; this is the fourth place that has caught me.
        phase = f"N{night}"
        good = [p for p in range(d.n)
                if p != seat and d.side_at(p, phase) == "good"]
        if not good:
            return None
        other = rng.choice(good)
        d.twins = (seat, other)
        return EvilTwinPair(1, seat, a=seat, b=other)

    # NOTE: the Acrobat is not here. It acts at slot 39, between the
    # Demon and the readings, so its pick is made in `_acrobat_may_fall`
    # where the night's consequences are settled — not in this pass,
    # which runs later and would hand it a row after it was needed.

    if role == "SnakeCharmer":
        # It points at somebody every night. Choosing the Demon while
        # working swaps character *and* side both ways — the charmer
        # becomes the Demon, the Demon becomes a good Snake Charmer,
        # poisoned for the rest of the game.
        #
        # The swap is recorded as a change from the *day after*, because
        # the ability worked and so the seat was still the Snake Charmer
        # when it did.
        phase = f"N{night}"
        others = [p for p in d.alive_at(phase) if p != seat]
        if not others:
            return None
        target = rng.choice(others)
        demon = d.demon_at(phase)
        # `working` is the one place that answers this, and this asked
        # its own narrower question instead — the Poisoner and the
        # perma-poisoned, and nothing else.
        #
        # So a **Drunk** that believed it was the Snake Charmer performed
        # a real swap: it took the Imp's character, the Imp took a
        # character the Drunk never held, and the board had no legal
        # world at all. A droisoned charmer does not function, and the
        # Drunk is droisoned for the whole game.
        #
        # Sixth thing found asking a narrower question than `working`.
        working = d.working(seat, night)
        swapped = target == demon and working and demon is not None
        if swapped:
            # **Immediately**, not from the day after.
            #
            # A Snake Charmer acts at slot 11 and every Demon at 24 or
            # later, so the swap has already happened by the time the
            # night's kill is made — and the seat that kills is the
            # charmer's, now holding the Demon. The old Demon is a
            # poisoned good Snake Charmer and kills nobody.
            #
            # Recording it at `D{night}` had the old Demon killing on the
            # night it stopped being one. The night-walk, which does the
            # swap at 11 and then looks up the Demon fresh, disagreed —
            # and was right.
            after = f"N{night}"
            became = d.role_at(demon, phase)
            # Lil' Monsta's babysitter is swapped like a Demon, character
            # and side both ways, and keeps the baby until the Minions
            # choose again (E, Weg 1, 21.10.2026).
            if _babysits(d, demon, phase):
                sides = (d.side_at(demon, phase), d.side_at(seat, phase))
                d.changes.append((after, seat, became))
                d.changes.append((after, demon, "SnakeCharmer"))
                d.side_changes.append((after, seat, became, sides[0]))
                d.side_changes.append((after, demon, "SnakeCharmer",
                                       sides[1]))
                d.perma_poisoned.add(demon)
                return SnakeCharmerChoice(night, seat, target=target,
                                          swapped=True)
            d.changes.append((after, seat, became))
            d.changes.append((after, demon, "SnakeCharmer"))
            # And the star moves with it. `demon_at` reads the handovers
            # last, so after a Fang Gu jump its handover outranked the
            # swap and the new Snake Charmer went on killing — the charmer
            # it had swapped with, once (29.09.2026).
            d.handovers.append((after, seat))
            d.side_changes.append((after, seat, became, "evil"))
            d.side_changes.append((after, demon, "SnakeCharmer", "good"))
            # The new Snake Charmer — the old Demon — is poisoned from
            # now on, and never recovers.
            d.perma_poisoned.add(demon)
        return SnakeCharmerChoice(night, seat, target=target,
                                  swapped=swapped)

    if role == "PitHag":
        # It turns somebody into a character not in play, **from the
        # second night**. The card is "each night*", and the asterisk is
        # the whole difference.
        #
        # This said "on any night" and fired on the first, which put a
        # change at N1 that no reading could sit beside: a Dreamer read a
        # seat the same night and the two were impossible together. Two
        # of the four remaining gate boards were this.
        #
        # `first_night = 0` in the vendored data says so plainly, and was
        # sitting there unread — the catalogue has the number and the
        # simulator never asked for it.
        if night < 2:
            return None
        if rng.random() > 0.25:
            return None
        phase = f"N{night}"
        living = [p for p in d.alive_at(phase) if p != seat]
        if not living:
            return None
        in_play = {d.role_at(p, phase) for p in range(d.n)}
        # And as the night began: this runs after the Demon, and a Fang Gu
        # that jumped into the Klutz made the Klutz look free to create
        # when, at slot 16, it was still in play (29.09.2026).
        in_play |= {d.role_at(p, f"E{night - 1}") for p in range(d.n)}
        in_play |= {b for b in d.believes if b}
        spare = [k for k in (d.script.townsfolk + d.script.outsiders
                             + d.script.minions) if k not in in_play]
        if not spare:
            return None
        # Never the Demon, unless what it becomes is also a Demon.
        #
        # A Pit-Hag turning the Demon into a Clockmaker leaves the game
        # with no Demon at all — good has won, and the record should stop
        # rather than carry on for two more nights. The solver noticed
        # before I did: with no Demon, the guard that keeps the town from
        # executing it did nothing, the ex-Demon was executed, and the
        # board had no legal world.
        #
        # Creating a *new* Demon is a real and interesting play, and the
        # solver already models the arbitrary deaths it causes. It is
        # left in; only the game-ending case is kept out.
        # The Demon at slot 16, as the night began — not after the kill.
        # This runs after the Demon has swung, so a Fang Gu that had just
        # jumped left its old seat looking like anybody, and the Pit-Hag
        # unmade the Demon it acts before (29.09.2026).
        demons = {d.demon_at(phase), d.demon_at(f"E{night - 1}")}
        choosable = [p for p in living if p not in demons] or living
        target = rng.choice(choosable)
        if target in demons:
            spare = [k for k in spare if TEAM[k] == "demon"]
            if not spare:
                return None
        became = rng.choice(spare)
        # Drunk or poisoned it chooses and nothing happens. It made its
        # change all the same until a Widow poisoned one (10.10.2026): the
        # night-walk, which asks, kept the seat as it was. Asked after the
        # draws, so every other game is dealt as before.
        if not d.working(seat, night):
            return None
        # The side does not move: a Townsfolk turned into the Poisoner is
        # a *good* Poisoner. A good one says what it became (Stelle 58, F).
        if d.side_at(target, phase) == "good":
            _says_it_became(d, night, target, became, phase, rng)
        d.changes.append((phase, target, became))
        return PitHagChoice(night, seat, target=target, role=became)

    if role == "Philosopher" and night == 1 and seat not in d.philosophies \
            and not _made_after_its_place(d, seat, night):
        # It takes a good character's ability, once a game. Not a change
        # of character — it stays the Philosopher and works two at once —
        # so this records the choice and nothing else. The gained
        # readings are the solver's business.
        pool = [k for k in d.script.townsfolk + d.script.outsiders
                if k != "Philosopher"]
        if not pool:
            return None
        took = rng.choice(pool)
        d.philosophies[seat] = took
        # The Lycanthrope's "1 good player registers as evil" comes with
        # it, where nobody dealt one already chose (13.10.2026).
        # The Pixie starts knowing an in-play Townsfolk from the night of
        # taking (ruling C); it plays the Philosopher, not mad about it.
        if took == "Pixie":
            town = [d.roles[p] for p in range(d.n)
                    if TEAM[d.roles[p]] == "townsfolk" and p != seat]
            if town:
                d.pixie_learned[seat] = rng.choice(town)
                d.pixie_mad[seat] = False
        # The Puzzlemaster's "1 player is drunk" the same: one of its own.
        if took == "Puzzlemaster":
            town = [p for p in range(d.n) if TEAM[d.roles[p]] == "townsfolk"
                    and p != seat]
            if town:
                d.puzzle_drunks = dict(getattr(d, "puzzle_drunks", {}))
                d.puzzle_drunks[seat] = rng.choice(town)
        # Ruling I: shown a token to match. The Trunkenbold a Townsfolk
        # not in play (S), the Verrückte the Demon in play (T).
        if took == "Drunk":
            in_play = set(d.roles) | {b for b in d.believes if b}
            spare = [k for k in d.script.townsfolk if k not in in_play]
            if spare:
                d.phil_token[seat] = rng.choice(spare)
        if took == "Lunatic":
            demon = d.demon_at("N1")
            if demon is not None:
                d.phil_token[seat] = d.role_at(demon, "N1")
        if took == "Lycanthrope" and getattr(d, "faux_paw", None) is None:
            good = [p for p in range(d.n) if not is_evil(d.roles[p])
                    and p != getattr(d, "bh_evil", None)]
            if good:
                d.faux_paw = rng.choice(good)
        return PhilosopherChoice(night, seat, role=took)

    if role == "Flowergirl" and night > 1:
        # Whether the Demon voted during the day just gone.
        day = night - 1
        demon = d.demon_at(f"D{day}")
        # Eyes closed or not, the Storyteller saw who voted.
        voted = demon is not None and (
            demon in d.votes.get(day, set())
            or demon in d.hidden_votes.get(day, set()))
        return FlowergirlInfo(night, seat, voted=voted)

    if role == "TownCrier" and night > 1:
        # Whether a Minion nominated during the day just gone.
        day = night - 1
        # What they held *that day*, not what they were dealt. A Pit-Hag
        # can make a Minion mid-game, and a Snake Charmer swap moves a
        # character between seats.
        #
        # Seventh place the deal has been mistaken for the timeline, and
        # the second found by the night-walk deriving an answer
        # independently and disagreeing.
        who = d.nominations.get(day, set())
        said = any(TEAM[d.role_at(p, f"D{day}")] == "minion" for p in who)
        return TownCrierInfo(night, seat, nominated=said)

    if role == "Oracle" and night > 1:
        # Counted by side *now*, not by what they were dealt. A Pit-Hag
        # creation, a Snake Charmer swap and a Goon that turned all move
        # a seat's side, and reading `d.roles` missed every one.
        #
        # Sixth place the deal has been mistaken for the timeline, and
        # this one was found by the night-walk deriving the answer
        # independently and disagreeing.
        # Including tonight's victim. The Oracle reads at slot 59 and
        # the Demon kills at 24, so whoever fell tonight is dead by the
        # time it counts — and `alive_at` reports the state at the
        # *start* of the night, which is a different question.
        #
        # Found by the night-walk deriving the count independently and
        # disagreeing. It is the kind of error that only shows once
        # something knows what order things happen in.
        phase = f"N{night}"
        dead = [p for p in range(d.n)
                if p not in d.alive_at(phase) or d.deaths.get(p) == phase]
        return OracleInfo(night, seat,
                          count=sum(1 for p in dead
                                    if _reads_evil(d, p, phase)))

    if role == "Seamstress" and night == 1:
        # Once a game, and the simulator uses it on the first night so
        # every game that has one produces the reading.
        others = [p for p in range(d.n) if p != seat]
        if len(others) < 2:
            return None
        a, b = sorted(rng.sample(others, 2))
        same = _reads_evil(d, a, "N1") == _reads_evil(d, b, "N1")
        return SeamstressInfo(night, seat, a=a, b=b, same=same)

    if role == "Sage" and (
            seat == getattr(d, "lev_chose", {}).get(night, (None, None))[1]
            or (d.deaths.get(seat) == f"N{night}"
                and not (night in getattr(d, "lyc_quiet", ())
                         and seat not in d.demon_killed.get(night, ())))):
        # Killed by the Demon, it learns two players and one is the
        # killer — the *specific* Demon, so no misregistration here.
        demon = d.demon_at(f"N{night}")
        if demon is None:
            return None
        others = [p for p in range(d.n) if p not in (seat, demon)]
        if not others:
            return None
        a, b = sorted([demon, rng.choice(others)])
        return SageInfo(night, seat, a=a, b=b)

    if role == "Klutz" and d.deaths.get(seat) == f"N{night}":
        # On dying it points at somebody, and good loses if they are
        # evil — so a game that carried on means it pointed at a good
        # player. Which is what a Klutz that is working does.
        # Good **now**, and alive — "choose 1 alive player". It read the
        # deal, so a Snake Charmer that had swapped into the Fang Gu still
        # looked good, the Klutz picked it, and a game good had just lost
        # ran on (29.09.2026).
        phase = f"N{night}"
        good = [p for p in d.alive_at(phase)
                if p != seat and d.deaths.get(p) != phase
                and d.side_at(p, phase) == "good"]
        if not good:
            return None
        return KlutzChoice(night, seat, target=rng.choice(good))

    # --- Bad Moon Rising ------------------------------------------------

    if role == "Grandmother" and (
            night == 1 or d.back_at(seat, f"N{night}") is not None):
        # A good player and their character, and from then on that seat
        # is her grandchild: if the Demon kills them, she goes too.
        #
        # Again on the night she comes back: "who only acts on the first
        # night does it again at once", and it is a new grandchild.
        # Somebody still standing, so the new link starts with tomorrow.
        phase = f"N{night}"
        others = [p for p in range(d.n)
                  if p != seat and d.side_at(p, phase) == "good"
                  and not is_evil(d.role_at(p, phase))
                  and (night == 1 or d.deaths.get(p) is None)]
        if not others:
            return None
        child = rng.choice(others)
        return GrandmotherInfo(night, seat, target=child,
                               role=d.role_at(child, phase))

    if role == "Chambermaid":
        # How many of two chosen players woke for their own ability
        # tonight. Read off the catalogue rather than re-derived, since
        # "did this character wake" is exactly what the catalogue is for.
        from botc.catalogue import CHARACTERS
        others = [p for p in d.alive_at(f"N{night}") if p != seat]
        if len(others) < 2:
            return None
        a, b = sorted(rng.sample(others, 2))
        # She chooses two players, and if one is the Goon and nobody got
        # there first tonight, she is drunk and told anything.
        if any([_the_goon_answers(d, night, seat, p) for p in (a, b)]):
            return ChambermaidInfo(night, seat, a=a, b=b,
                                   count=rng.randint(0, 2))
        # Derived here rather than asked of the solver, like every other
        # rule in this file — the point of the simulator is that a shared
        # misreading shows up as an impossible board instead of agreeing
        # with itself.
        #
        # But derived from the same *facts*. The rule is "woke for its
        # own ability tonight", and there are three ways to be counted
        # and one trap:
        #
        #   * `nights` says never — a Barber, a Baron — and it does not
        #     count, whatever its `wake` set claims. That set is what a
        #     *player* could honestly say, and a Baron truthfully says
        #     "first night" because it is shown the other evil players.
        #     Being shown your team is not your ability working.
        #   * "every" includes the first night, though its wake set does
        #     not bother to say so.
        #   * "other" means from the second. A Demon is told its Minions
        #     and its bluffs on the first, and that is *not* its ability
        #     (table ruling, 02.10.2026) — only a Pukka, which already
        #     chooses then, counts. The solver keeps both counts legal
        #     for other tables; this Storyteller is the table's own.
        woke = sum(_woke_for_own_ability(d, p, night) for p in (a, b))
        return ChambermaidInfo(night, seat, a=a, b=b, count=woke)

    if role == "Gambler" and night > 1:
        # It names somebody and a character, and dies if it guessed
        # wrong. Recorded either way, since the guess is public.
        others = [p for p in d.alive_at(f"N{night}") if p != seat]
        if not others:
            return None
        target = rng.choice(others)
        # Mostly a real guess at what they claim to be, sometimes wild.
        guess = (d.apparent(target) if rng.random() < 0.6
                 else rng.choice(list(d.script.townsfolk)))
        _the_goon_answers(d, night, seat, target)
        # And it dies if it guessed wrong, which the comment above has
        # claimed since the Gambler went in while the code did nothing
        # about it. A wrong guess and a living Gambler is not a legal
        # board, and the solver said so the first time a mixed script put
        # one in front of it.
        #
        # A droisoned Gambler is a different matter: its ability is not
        # working, so the Storyteller decides, and here it survives.
        if d.working(seat, night) \
                and d.role_at(target, f"N{night}") != guess \
                and not _kept_alive_by_a_tea_lady(d, seat, f"N{night}"):
            d.deaths.setdefault(seat, f"N{night}")
        return GamblerGuess(night, seat, target=target, role=guess)

    if role == "Exorcist" and night > 1:
        # Names somebody, and if it is the Demon that Demon does not kill
        # tonight. Acts at 21, before every Demon, which is what lets it
        # work at all — and it may not name the same seat two nights
        # running.
        #
        # Dealt and never acting until now, which the night-walk's own
        # `untold` warning is what found: an Exorcist on the board that
        # the walk was told nothing about.
        others = [p for p in d.alive_at(f"N{night}") if p != seat]
        others = [p for p in others if p != d.exorcised_last.get(seat)]
        if not others:
            return None
        target = rng.choice(others)
        d.exorcised_last[seat] = target
        d.exorcised[night] = target
        _chose(d, "Exorcist", night, seat, target, last=True)
        _the_goon_answers(d, night, seat, target)
        return ExorcistChoice(night, seat, target=target)

    if role == "Choirboy":
        # "If the Demon kills the King, you learn which player is the
        # Demon." Its own kill only, and a drunk or poisoned King is still
        # the King (10.10.2026).
        if not _a_king_fell(d, night) or d.deaths.get(seat) is not None:
            return None
        demon = d.demon_at(f"N{night}")
        if demon is None:
            return None
        return ChoirboyInfo(night, seat, target=demon)

    if role == "Widow":
        # "On your 1st night, look at the Grimoire & choose a player: they
        # are poisoned. 1 good player knows a Widow is in play." Anybody,
        # itself included — which here does nothing. Drunk or poisoned, or
        # drunk by the Goon it chose, it poisons nobody and nobody is told
        # (10.10.2026).
        if night > 1 and d.role_at(seat, f"D{night - 1}") == "Widow":
            return None
        phase = f"N{night}"
        living = d.alive_at(phase)
        target = rng.choice(living)
        gooned = _the_goon_answers(d, night, seat, target)
        if gooned or not d.working(seat, night):
            return None
        if target != seat:
            d.widow_poison.append((seat, target, night))
        told = [p for p in living if p != seat and d.deaths.get(p) is None
                and d.side_at(p, phase) == "good"]
        if told:
            d.said_by_others.append(WidowKnown(night, rng.choice(told)))
        return None

    if role == "Fearmonger":
        # Chooses a player every night, and the table is told when it is
        # a new one — drunk or poisoned too (table ruling, 10.10.2026).
        # It keeps its last pick half the time.
        others = [p for p in d.alive_at(f"N{night}") if p != seat]
        if not others:
            return None
        before = d.fear_target.get(seat)
        if before in others and rng.random() < 0.5:
            target = before
        else:
            target = rng.choice(others)
        d.fear_chose[night] = target
        d.fear_target[seat] = target
        _the_goon_answers(d, night, seat, target)
        if target == before:
            return None                   # the same one: nothing is said
        return FearmongerChose(night, seat)

    if role == "Sailor":
        # Points at somebody every night; one of the two of them is drunk
        # until dusk, and the Storyteller chooses which. A sober Sailor
        # cannot die at night, which the deaths already handle.
        #
        # Never fired before: dealt twenty-eight times across a hundred
        # and eighty games and it acted in none of them, so the walk's
        # rule for it had never been checked against anything.
        others = [p for p in d.alive_at(f"N{night}") if p != seat]
        if not others:
            return None
        target = rng.choice(others)
        drunk = rng.choice([seat, target])
        # The Goon is asked before anything the choice does, as the board
        # stood at that moment — and if it answers, the choice does
        # nothing: no second drunk.
        if not _the_goon_answers(d, night, seat, target) \
                and not _still_under_the_token(d, night, seat):
            d.sailor_drunk.setdefault(night, drunk)
            _chose(d, "SailorDrunk", night, seat, drunk)
        return SailorChoice(night, seat, target=target)

    if role == "Innkeeper" and night > 1:
        # Two players are safe from the Demon tonight, and one of them is
        # drunk. Same story: dealt twenty-four times, never acted.
        others = [p for p in d.alive_at(f"N{night}") if p != seat]
        if len(others) < 2:
            return None
        a, b = sorted(rng.sample(others, 2))
        void = _still_under_the_token(d, night, seat)
        d.innkeeper_guarded.setdefault(night, (a, b))
        _chose(d, "Innkeeper", night, seat, (a, b))
        if void:
            d.innkeeper_void.add(night)
            _chose(d, "InnkeeperVoid", night, seat, True)
        drunk = rng.choice([a, b])
        # Asked first, as with the Sailor. An Innkeeper that picked the
        # Pukka and the Goon it had poisoned found a Goon with no ability
        # — and only then made the Pukka drunk, which rests the poison.
        # Applying its drunkenness first had each undoing the other.
        if not any([_the_goon_answers(d, night, seat, picked)
                    for picked in (a, b)]) and not void:
            d.innkeeper_drunk.setdefault(night, drunk)
            _chose(d, "InnkeeperDrunk", night, seat, drunk)
        return InnkeeperChoice(night, seat, a=a, b=b)

    if role == "DevilsAdvocate":
        # At 13, between the Gambler and the Exorcist — in the early pass
        # so that who chose the Goon *first* comes out in night order.
        _devils_advocate_picks(d, night, rng)
        return None

    if role == "Lunatic" and night > 1 and not getattr(d, "lil_monsta",
                                                       False):
        # It lives a Demon's night and points at somebody; nothing comes
        # of it. But it is a player choosing a player, and that counts
        # for the Goon (table ruling, 02.10.2026).
        others = [p for p in d.alive_at(f"N{night}") if p != seat]
        if others:
            target = rng.choice(others)
            d.lunatic_chose[night] = target
            _the_goon_answers(d, night, seat, target)
        return None

    if role == "Courtier" and seat not in d.courtier_chose:
        # Three days and nights of drunkenness for whoever holds the
        # character it names. Used once a life — the first night, and
        # the first night after coming back — and the table hears which.
        d.courtier_chose[seat] = night
        d.courtier_nights.add((seat, night))
        # The Goon too, where there is one: naming it is choosing it,
        # and it turns to the Courtier's side — the wiki's own example on
        # the Goon's page (table ruling, 08.10.2026). Never offered until
        # then, so every Bad Moon Rising game with a Courtier is dealt a
        # little differently from that day.
        pool = list(d.script.townsfolk) + list(d.script.minions)
        if "Goon" in d.script.outsiders:
            pool.append("Goon")
        named = rng.choice(pool)
        # And the drunkenness itself, which was never applied: the row
        # was written and nobody got drunk. Decided now, while it is
        # known whether the Courtier itself was working tonight.
        holder = next((p for p in range(d.n)
                       if d.role_at(p, f"N{night}") == named), None)
        if holder is not None and named == "Goon":
            _the_goon_answers(d, night, seat, holder)
        if holder is not None and d.working(seat, night):
            d.courtier_drunk = (night, holder, seat)
            # Every seat holding it: three Village Idiots are all drunk
            # (11.10.2026).
            for p in range(d.n):
                if d.role_at(p, f"N{night}") == named:
                    d.courtier_drunks.append((night, p, seat))
        return CourtierChoice(night, seat, role=named)

    if role == "Undertaker" and night > 1:
        executed = sorted(d.died_on(f"E{night - 1}"))
        if executed:
            when = f"E{night - 1}"
            return Undertaker(night, seat, target=executed[0],
                              role=d.role_at(executed[0], when))

    if role == "Ravenkeeper" and (
            d.deaths.get(seat) == f"N{night}"
            or seat == getattr(d, "lev_chose", {}).get(night,
                                                        (None, None))[1]):
        others = [p for p in range(d.n) if p != seat]
        pick = rng.choice(others)
        return Ravenkeeper(night, seat, target=pick,
                           role=d.role_at(pick, f"N{night}"))
    return None


def _nearest_evil_each_way(d, seat, night):
    """How many steps to the closest evil player, each way round.

    {1: clockwise, -1: anticlockwise}, None where there is nobody. Seats
    run clockwise. By the side each seat is really on tonight — the
    simulator's Storyteller does not use a Recluse here, though it could.
    A seat exactly opposite is as far one way as the other.
    """
    phase = f"N{night}"
    out = {1: None, -1: None}
    for gap in range(1, d.n):
        other = (seat + gap) % d.n
        if not _reads_evil(d, other, phase):
            continue
        for way, steps in ((1, gap), (-1, d.n - gap)):
            if steps <= d.n - steps and (out[way] is None or steps < out[way]):
                out[way] = steps
    return out


def _neighbours(d, seat, night):
    """The nearest living seat each way, worked out independently of the
    solver so a shared misreading cannot hide.

    The Demon has already killed by the time the Empath wakes, so
    tonight's victim does not count as a neighbour.
    """
    alive = [p for p in d.alive_at(f"N{night}")
             if d.deaths.get(p) != f"N{night}"]
    if seat not in alive or len(alive) < 3:
        return [p for p in alive if p != seat]
    i = alive.index(seat)
    return [alive[(i - 1) % len(alive)], alive[(i + 1) % len(alive)]]


def _registers_as(role, team):
    """Could the Storyteller show this character as that team?

    A Spy is a Minion that may be shown as a Townsfolk or an Outsider; a
    Recluse is an Outsider that may be shown as a Minion or the Demon.
    Everybody else is what they are.
    """
    from botc.catalogue import CHARACTERS
    return TEAM[role] == team or team in CHARACTERS[role].registers


def _shown_as(d, seat, team, rng, night=1):
    """A character the Storyteller could show this seat as, for that team.

    A Recluse shown to an Investigator is not shown *as the Recluse* — it
    is shown as some Minion, and which one is the Storyteller's choice.
    Returning the true character would have produced a reading no legal
    world explains: "seat 4 is the Recluse" from a character that only
    ever names Minions.
    """
    from botc.catalogue import CHARACTERS
    role = d.role_at(seat, f"N{night}")
    if TEAM[role] == team:
        return role
    # Misregistering. Pick something of the right team that is not
    # already in play, since a Storyteller pointing at a character
    # somebody else really holds is asking to be caught.
    pool = {"townsfolk": TOWNSFOLK, "outsider": OUTSIDERS,
            "minion": MINIONS, "demon": DEMONS}[team]
    held = {d.role_at(p, f"N{night}") for p in range(d.n)}
    spare = [k for k in pool if k not in held]
    return rng.choice(spare or pool)


def _cerenovus_maddens(d, night, heard, rng):
    """The Cerenovus names a player and a good character each night.

    Nothing in the game changes: madness is a matter of what somebody
    says tomorrow, and the simulator's claims do not play along. What can
    reach the table is the chosen player breaking madness to say they
    were shown the Cerenovus — a good one, now and then.
    """
    from botc.info import CerenovusMadness
    phase = f"N{night}"
    for seat in range(d.n):
        if d.role_at(seat, phase) != "Cerenovus":
            continue
        if seat not in d.alive_at(phase):
            continue
        target = rng.choice([p for p in range(d.n) if p != seat])
        good = list(d.script.townsfolk) + list(d.script.outsiders)
        role = rng.choice(good)
        if d.side_at(target, phase) == "good" and rng.random() < 0.25:
            heard.append(CerenovusMadness(night, target, role=role))


def _savant_visits(d, night, heard, rng):
    """Each day a Savant may ask the Storyteller for two things, one true
    and one false.

    Mostly in the shapes the solver can check (`SAVANT_KINDS`), judged
    here by what the seats *are* — this simulator's own reading, not the
    solver's function — so the two can disagree. Now and then only words,
    which the solver keeps and does not weigh.

    Under a working Vortox both are false. A droisoned Savant is told
    whatever the Storyteller likes. Dead, it asks nothing.
    """
    phase = f"D{night}"
    for seat in range(d.n):
        if d.role_at(seat, phase) != "Savant":
            continue
        if seat not in d.alive_at(phase) or rng.random() < 0.3:
            continue
        if rng.random() < 0.2:
            heard.append(SavantInfo(night, seat,
                                    first=_savant_line(d, rng, True),
                                    second=_savant_line(d, rng, False)))
            continue
        if not d.working(seat, night):
            wanted = [rng.random() < 0.5, rng.random() < 0.5]
            # Under a Vortox even a drunk Savant hears nothing true.
            if _vortox_working(d, night):
                wanted = [False, False]
        elif _vortox_working(d, night):
            wanted = [False, False]
        else:
            wanted = [True, False]
            rng.shuffle(wanted)
        said = [_savant_statement(d, seat, phase, truth, rng)
                for truth in wanted]
        if None in said:
            continue
        heard.append(SavantInfo(night, seat,
                                first=said[0][1], second=said[1][1],
                                first_says=said[0][0],
                                second_says=said[1][0]))


FISHERMAN_SAYS = ("Trust the quiet ones.", "Execute today.",
                  "Do not execute today.", "Count the Outsiders.",
                  "Your Empath is right.", "Look to your left.")


def _fisherman_visits(d, day, heard, rng):
    """A Fisherman asks the Storyteller for advice, once a game.

    Kept and not weighed (12.10.2026), so the advice is any line at all;
    a drunk or poisoned one may be told something unhelpful, and here
    every line is as good as any other. A seat holding the Fisherman's
    token — a Drunk who thinks it is one — visits too. Dead, it asks
    nothing.
    """
    phase = f"D{day}"
    asked = d.__dict__.setdefault("fisherman_asked", set())
    for seat in range(d.n):
        held = d.token(seat, phase) or d.role_at(seat, phase)
        if held != "Fisherman" or seat in asked:
            continue
        if seat not in d.alive_at(phase) or rng.random() < 0.6:
            continue
        asked.add(seat)
        heard.append(FishermanAdvice(day, seat,
                                     advice=rng.choice(FISHERMAN_SAYS)))


def _savant_statement(d, seat, phase, truth, rng):
    """One statement with the given truth, and some words for it."""
    from botc.roles import TEAM
    others = [p for p in range(d.n) if p != seat]
    roles = [d.role_at(p, phase) for p in range(d.n)]
    good = list(d.script.townsfolk) + list(d.script.outsiders)
    for _ in range(40):
        kind = rng.choice(("evil", "good", "same", "different", "is",
                           "in_play", "not_in_play", "outsiders",
                           "demon_among"))
        if kind in ("evil", "good"):
            p = rng.choice(others)
            says = {"kind": kind, "seat": p}
            real = (d.side_at(p, phase) == "evil") == (kind == "evil")
        elif kind in ("same", "different"):
            a, b = rng.sample(range(d.n), 2)
            says = {"kind": kind, "a": a, "b": b}
            real = ((d.side_at(a, phase) == d.side_at(b, phase))
                    == (kind == "same"))
        elif kind == "is":
            p = rng.choice(others)
            role = rng.choice([roles[p]] + good)
            says = {"kind": kind, "seat": p, "role": role}
            real = roles[p] == role
        elif kind in ("in_play", "not_in_play"):
            role = rng.choice(good + list(d.script.minions))
            says = {"kind": kind, "role": role}
            real = (role in roles) == (kind == "in_play")
        elif kind == "outsiders":
            actual = sum(1 for r in roles if TEAM[r] == "outsider")
            count = rng.choice([actual, max(actual - 1, 0), actual + 1])
            says = {"kind": kind, "count": count}
            real = count == actual
        else:
            seats = sorted(rng.sample(range(d.n), 3))
            says = {"kind": kind, "seats": seats}
            real = d.demon_at(phase) in seats
        if real == truth:
            return says, f"{kind} {says}"
    return None


def _savant_line(d, rng, true_one):
    """Something shaped like a Savant statement.

    Deliberately shallow: a Savant's pair can be anything from "the Demon
    sits beside an Outsider" to "no Minion has yet chosen a man", the
    solver keeps the words without weighing them, and inventing something
    cleverer here would be inventing something nobody reads.
    """
    from botc.roles import TEAM
    demon = d.demon_at("N1")
    outsiders = sum(1 for r in d.roles if TEAM[r] == "outsider")
    # No Demon yet with a Summoner (21.10.2026): the count only.
    if demon is None:
        return (f"there are {outsiders} outsiders in play" if true_one
                else f"there are {outsiders + 1} outsiders in play")
    if true_one:
        return rng.choice([
            f"there are {outsiders} outsiders in play",
            f"the demon is not seat {(demon + 2) % d.n + 1}",
        ])
    return rng.choice([
        f"there are {outsiders + 1} outsiders in play",
        f"the demon is seat {(demon + 2) % d.n + 1}",
    ])


def _pair_info(d, seat, night, rng, cls, matches, team=None,
               misregister=0.35):
    """Two players, one of whom is shown as something.

    `team` is what the reading is looking for. When it is given, seats
    that could *register* as that team are candidates too — which is the
    whole of misregistration, and the simulator produced none of it until
    now. Every game it dealt was one where the Storyteller had told the
    plain truth, which is the easy half of the problem.
    """
    honest = [p for p in range(d.n) if p != seat and matches(p)]
    liars = []
    if team is not None:
        liars = [p for p in range(d.n)
                 if p != seat and p not in honest
                 and _registers_as(d.role_at(p, f"N{night}"), team)
                 # A droisoned character cannot misregister (table
                 # rule): a Spy the Courtier has made drunk, or a Pukka
                 # poisoned, is a Spy and reads as one. Never asked here,
                 # so a Librarian was shown a drunk Spy as the Drunk
                 # (07.10.2026, on a mixed script; a poisoned Spy in
                 # Trouble Brewing was shown wrongly too, and nothing
                 # there could tell).
                 and d.working(p, night)]

    # Prefer the truth, but take the lie often enough to matter.
    if liars and (not honest or rng.random() < misregister):
        shown = rng.choice(liars)
    elif honest:
        shown = rng.choice(honest)
    else:
        return None

    others = [p for p in range(d.n) if p != seat and p != shown]
    if not others:
        return None
    a, b = sorted([shown, rng.choice(others)])
    # What the seat holds tonight. This read the deal, and a Washerwoman
    # at slot 33 was shown the character a seat had held before the
    # Snake Charmer at 20 swapped it away (07.10.2026).
    role = (d.role_at(shown, f"N{night}") if team is None
            else _shown_as(d, shown, team, rng, night))
    return cls(night, seat, a=a, b=b, role=role)


# --------------------------------------------------------------------------
# Turning a dealt game into what the table would enter
# --------------------------------------------------------------------------

def relay_some(d, infos, rng, chance=0.4):
    """Hand some readings to another good player to announce.

    Information dumping is ordinary play, and it is where the seat a
    reading belongs to stops being the seat that says it.
    """
    good = [p for p in range(d.n) if not is_evil(d.roles[p])]
    out = []
    for info in infos:
        movable = [p for p in good
                   if p != info.player and d.deaths.get(p) is None]
        if movable and rng.random() < chance and not info.hard():
            info.player = rng.choice(movable)
        out.append(info)
    return out


def table_view(d, infos, rng, bluff_pool=None):
    """The GameState a player would build watching this game.

    Good players claim what they believe they are. Evil players claim a
    character that is not in play, which is what the Storyteller hands
    them to bluff with.
    """
    in_play = set(d.roles) | {b for b in d.believes if b}
    spare = [t for t in TOWNSFOLK if t not in in_play]
    rng.shuffle(spare)

    claims = {}
    for seat in range(d.n):
        if is_evil(d.roles[seat]):
            claims[seat] = spare.pop() if spare else "Mayor"
        elif d.roles[seat] == "Pixie" and d.pixie_mad.get(seat):
            claims[seat] = d.pixie_learned[seat]   # mad about it
        else:
            claims[seat] = d.apparent(seat)

    # The day comes through too. This predates the simulator having
    # nominations and votes at all, and without them a reading about the
    # day before refers to a day the state thinks nobody voted on.
    return GameState(n_players=d.n, claims=claims, **d.record(),
                     infos=list(infos), votes=dict(d.votes),
                     nominations=dict(d.nominations))
