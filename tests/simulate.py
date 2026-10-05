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
        # What the table did in daylight. Only a Flowergirl and a Town
        # Crier ask, but the day is where the answer lives.
        # A Zombuul that survived its first death — registered dead, still
        # the Demon, still killing on quiet days. And the day after which
        # a Mastermind's extra day runs out and the game is over.
        self.zombuul_up = None
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
        return World(tuple(self.roles), tuple(self.believes))

    def apparent(self, seat):
        """The character this seat believes they are."""
        return self.believes[seat] or self.roles[seat]

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
        return seat not in droisoned_at(self, night, by_day)


def deal(n, rng, script=None):
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

    if changer in ("Baron", "Godfather"):
        rest = [m for m in minions if m != changer]
        picked_minions = [changer] + rng.sample(rest, mi - 1)
        picked_demons = list(rng.sample(demons, de))
    elif changer in ("FangGu", "Vigormortis"):
        picked_minions = rng.sample(minions, mi)
        rest = [d for d in demons if d not in ("FangGu", "Vigormortis")]
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

    picked_outsiders = rng.sample(outsiders, out)
    spare = list(townsfolk)
    rng.shuffle(spare)

    chosen, believes_for = [], {}
    for o in picked_outsiders:
        chosen.append(o)
        if o == "Drunk":
            believes_for[o] = spare.pop()      # a token nobody else can hold
    chosen += spare[:tf]
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

    # "[You neighbour the Demon]": if the shuffle put it elsewhere, it
    # trades seats with whoever sits beside the Demon. Written from the
    # rule rather than from the solver's catalogue field on purpose.
    if "Marionette" in roles:
        m = roles.index("Marionette")
        demon = next(i for i in range(n) if TEAM[roles[i]] == "demon")
        beside = [(demon - 1) % n, (demon + 1) % n]
        if m not in beside:
            swap = rng.choice(beside)
            roles[m], roles[swap] = roles[swap], roles[m]
            believes[m], believes[swap] = believes[swap], believes[m]
    return roles, believes


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
    roles, believes = deal(n, rng, script)
    good = [p for p in range(n) if not is_evil(roles[p])]
    # Only when there is a Fortune Teller to have one. The red herring is
    # *that character's* — the Storyteller picks a good player who will
    # register as the Demon to it — so a board without one should not
    # have a red herring at all.
    red_herring = rng.choice(good) if "FortuneTeller" in roles else None
    poisoner = roles.index("Poisoner") if "Poisoner" in roles else None

    d = Deal(roles, believes, red_herring, {}, {}, None)
    d.script = script
    heard = []

    for night in range(1, nights + 1):
        d.nights_played = night
        living = d.alive_at(f"N{night}")
        # A Poisoner that catches the star stops being one. The seat was
        # worked out at deal time and never checked again, so a Poisoner
        # promoted to Imp went on poisoning as well as killing — and the
        # solver rightly called those boards impossible, because a Demon
        # poisons nobody.
        if (poisoner is not None and poisoner in living
                and d.demon_at(f"N{night}") != poisoner):
            d.poisoned[night] = rng.choice(living)

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

        # A Pukka poisons on the *first* night and kills from the
        # second, so it is the one Demon that acts before anybody else
        # does. Skipping night one entirely put its poison a night late
        # and left night two with nobody dying — a board the solver
        # rightly called impossible.
        if night == 1 and d.roles[d.demon_at("N1") or 0] == "Pukka":
            _demon_kills(d, night, rng)

        if night > 1:
            demon = d.demon_at(f"N{night}")
            heir = _heir(d, f"N{night}", rng)
            if heir is not None and rng.random() < starpass_chance:
                # The Imp kills itself and the star passes on. This always
                # leaves a body, so it can never make a night quiet.
                d.deaths[demon] = f"N{night}"
                d.handovers.append((f"N{night}", heir))
                d.changes.append((f"N{night}", heir, d.roles[demon]))
            else:
                aimed = _demon_kills(d, night, rng)
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
                        if d.role_at(gran, f"N{night}") == "Grandmother" \
                                and gran in d.alive_at(f"N{night}") \
                                and d.deaths.get(gran) is None \
                                and d.working(gran, night) \
                                and not _kept_alive_by_a_tea_lady(
                                    d, gran, f"N{night}"):
                            d.deaths[gran] = f"N{night}"

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

        _nobody_returns_only_to_die(d, night)

        heard += [row for row in honest_info(d, night, rng)
                  if d.role_at(row.player, f"N{night}") not in CHOOSES_EARLY]

        # The Ogre picks late on its first night, after every reading.
        if night == 1:
            _ogre_picks(d, heard, rng)
        _cerenovus_maddens(d, night, heard, rng)

        # Dawn, and just two players alive: evil has won and the game
        # stops here. It used to run on — three more nights with one
        # player left — and every measurement taken over several nights
        # counted those as games (04.10.2026). The night itself is played
        # to its end, so the record of the last night is a whole one.
        if _evil_has_won(d, f"N{night}"):
            d.ended_at, d.ended_why = f"N{night}", "two alive"
            d.game_ends_after = night
            break

        if night < nights:
            # A Savant visits the Storyteller in daylight.
            _savant_visits(d, night, heard, rng)

            # The day happens first: nominations, then votes, then the
            # execution that follows from them.
            # A public guess at the evil team, before the day's business.
            # If it lands, good wins and the game stops there — so the
            # record ends rather than running on, which is the same rule
            # that stopped a Pit-Hag unmaking the Demon and the game
            # carrying on for two more nights.
            if _alsaahir_guesses(d, night, rng, heard):
                break

            _hold_a_day(d, night, rng)
            # A Witch's curse can take the third from last in daylight.
            if _evil_has_won(d, f"D{night}"):
                d.ended_at, d.ended_why = f"D{night}", "two alive"
                d.game_ends_after = night
                break
            executed = _execute(d, night, rng, allow_takeover)
            if executed is not None:
                d.deaths[executed] = f"E{night}"
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

    return d, heard


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
    ogre = d.seat_of("Ogre")
    if ogre is None:
        return
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
        if d.role_at(seat, f"D{day}") != "Moonchild":
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
    for a Gossip or a Tinker, not a Courtier naming a character, not a
    Moonchild pointing in daylight. A dead Goon has no ability, and a
    droisoned one does nothing.

    Dealt in a quarter of all games and never played until 03.10.2026.
    """
    phase = f"N{night}"
    if night in d.goon_first or target is None or chooser == target:
        return False
    if d.role_at(target, phase) != "Goon" or d.deaths.get(target) is not None:
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
    return [p for p in d.alive_at(phase)
            if d.deaths.get(p) is None and p not in but
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
        if not _stands_to_act(d, seat, "Gossip", night):
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
            and not (d.role_at(p, phase) == "Fool" and p not in d.fool_spent
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
    if d.role_at(seat, phase) != "Fool" or seat in d.fool_spent:
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
        if d.role_at(seat, phase) != "Professor" or seat in d.professor_chose:
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
        if d.role_at(seat, phase) != "Tinker":
            continue
        if seat not in d.alive_at(phase):
            continue
        # Not on the night it came back: down, up and down again before
        # dawn is a night the table sees nothing of.
        if d.back_at(seat, phase) is not None:
            continue
        if rng.random() < 0.15 and not _kept_alive_by_a_tea_lady(
                d, seat, phase):
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
    monk = next((p for p in range(d.n)
                 if d.role_at(p, phase) == "Monk"
                 and p in d.alive_at(phase)), None)
    if monk is None or not d.working(monk, night):
        return
    others = [p for p in d.alive_at(phase) if p != monk]
    if others:
        d.monk_guarded[night] = rng.choice(others)


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
        if d.role_at(seat, phase) != "Acrobat" or night < 2:
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
        if row.target not in droisoned:
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
        if d.role_at(seat, phase) == "Sailor" and d.working(seat, night):
            return True
        pair = d.innkeeper_guarded.get(night)
        if pair and seat in pair and night not in d.innkeeper_void:
            # Still standing: an Innkeeper the Demon took at 27 keeps
            # nobody from a Moonchild's pick at 50. The same for a Tea
            # Lady, below. (A Gambler at 10 asks before anybody has died.)
            keeper = next((p for p in range(d.n)
                           if d.role_at(p, phase) == "Innkeeper"
                           and p in d.alive_at(phase)
                           and d.deaths.get(p) is None), None)
            if keeper is not None and d.working(keeper, night):
                return True
    for lady in range(d.n):
        if d.role_at(lady, phase) != "TeaLady":
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
    holders = [p for p in range(d.n)
               if d.role_at(p, phase) == "Farmer"
               and d.deaths.get(p) == phase]
    for seat in holders:
        if not d.working(seat, night):
            continue                      # droisoned: it does not function
        def good_enough(p):
            role = d.role_at(p, phase)
            if not is_evil(role):
                return True
            return bool({"townsfolk", "outsider"}
                        & CHARACTERS[role].registers)
        heirs = [p for p in d.alive_at(phase)
                 if p != seat and good_enough(p)]
        if not heirs:
            continue
        # From the day after, like every change that follows an ability
        # working: the Farmer was still the Farmer when it did.
        d.changes.append((f"D{night}", rng.choice(heirs), "Farmer"))


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
    died = [p for p in range(d.n)
            if d.role_at(p, f"N{night}") == "Barber"
            and d.deaths.get(p) in (f"D{yesterday}", f"E{yesterday}",
                                    f"N{night}")]
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
    d.changes.append((phase, a, got_b))
    d.changes.append((phase, b, got_a))
    # Kept for the night walk, which swaps at the Barber's own slot when
    # it is told who (tests/nightwalk.py).
    if not hasattr(d, "barber_swaps"):
        d.barber_swaps = {}
    d.barber_swaps[night] = (a, b)
    # And the star moves with the character, as with the Snake Charmer.
    if demon in (a, b):
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
        if d.role_at(seat, phase) != "Alsaahir":
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

    tally = {}
    for who in nominators:
        if d.deaths.get(who) is not None:
            continue                      # went down nominating, just now
        nominee = rng.choice([p for p in living
                              if p != who and d.deaths.get(p) is None]
                             or [who])
        d.nominations.setdefault(day, set()).add(who)
        # "If they nominate tomorrow, they die" — at once, and the
        # nomination still counts. The Witch was dealt, aimed every night
        # and never killed anybody, so a death the solver reads as "a
        # Witch is in play, and working" never came up (03.10.2026).
        if who == cursed and _the_curse_bites(d, who, day):
            d.deaths[who] = f"D{day}"
            d.witch_deaths[day] = who
        votes = set()
        for voter in living:
            # Evil is a shade less willing to put its own up, which is
            # the whole reason a Flowergirl's answer carries anything.
            chance = 0.45
            if is_evil(d.roles[voter]) and is_evil(d.roles[nominee]):
                chance = 0.2
            if rng.random() < chance:
                votes.add(voter)
        if votes:
            d.votes.setdefault(day, set()).update(votes)
        tally[nominee] = max(tally.get(nominee, 0), len(votes))
    d.tally[day] = tally


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
    if d.role_at(seat, phase) == "Sailor" and d.working(seat, day):
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
    if role == "Sailor" and d.working(seat, day, by_day=True):
        return "Sailor"
    if _kept_alive_by_a_tea_lady(d, seat, phase):
        return "TeaLady"
    advocate, chosen = d.spared.get(day) or (None, None)
    if chosen == seat and advocate in d.alive_at(phase) \
            and d.deaths.get(advocate) is None \
            and d.role_at(advocate, phase) == "DevilsAdvocate" \
            and d.working(advocate, day, by_day=True):
        return "DevilsAdvocate"
    pacifist = next((p for p in d.alive_at(phase)
                     if d.role_at(p, phase) == "Pacifist"
                     and d.deaths.get(p) is None), None)
    if pacifist is not None and d.working(pacifist, day, by_day=True) \
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
    mastermind = d.seat_of("Mastermind")
    extra_day = (not takeover and not zombuul_first
                 and mastermind is not None
                 and d.role_at(mastermind, phase) == "Mastermind"
                 and mastermind in d.alive_at(phase)
                 and d.working(mastermind, day)
                 and d.game_ends_after is None)
    # Or a Devil's Advocate has it covered, and it walks away.
    advocate, chosen = d.spared.get(day) or (None, None)
    covered = (demon is not None and chosen == demon
               and advocate in d.alive_at(phase)
               and d.deaths.get(advocate) is None
               and d.role_at(advocate, phase) == "DevilsAdvocate"
               and d.working(advocate, day))
    if not (takeover or zombuul_first or extra_day or covered):
        living = [p for p in living if p != demon]
    if not living:
        return None
    tally = d.tally.get(day) or {}
    ranked = [seat for seat, count in
              sorted(tally.items(), key=lambda kv: -kv[1])
              if seat in living and count]
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
        else:
            d.handovers.append((phase, heir))
            d.changes.append((phase, heir, d.roles[victim]))
    return victim


def simulate(n, rng, nights=1):
    """Backwards-compatible single return for the night-one checks."""
    return play(n, rng, nights)[0]


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
    if demon is None or d.exorcised[night] != demon:
        return False
    exo = next((p for p in range(d.n)
                if d.role_at(p, phase) == "Exorcist"
                and p in d.alive_at(phase)), None)
    return exo is not None and d.working(exo, night)


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
    # Working, which is every way of going wrong, not only the Poisoner.
    if d.role_at(target, phase) == "Soldier" and d.working(target, night):
        return True

    # A sober Sailor cannot die. Missing here while the solver has always
    # had it as a shield; nothing tripped only because the Sailor is so
    # often the drunk one of its own pair.
    if d.role_at(target, phase) == "Sailor" and d.working(target, night):
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
        if d.role_at(lady, phase) != "TeaLady" or lady not in d.alive_at(phase):
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

    if d.monk_guarded.get(night) == target:
        monk = next((p for p in range(d.n)
                     if d.role_at(p, phase) == "Monk"
                     and p in d.alive_at(phase)), None)
        if monk is not None and d.working(monk, night) and monk not in gone:
            return True

    pair = d.innkeeper_guarded.get(night)
    if pair and target in pair and night not in d.innkeeper_void:
        keeper = next((p for p in range(d.n)
                       if d.role_at(p, phase) == "Innkeeper"
                       and p in d.alive_at(phase)), None)
        # A guard goes with whoever gave it: an Innkeeper the Shabaloth
        # took first protects nobody from its second kill.
        if keeper is not None and d.working(keeper, night) \
                and keeper not in gone:
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

    # The Monk guards, whoever is swinging.
    monk = d.roles.index("Monk") if "Monk" in d.roles else None
    guarded = None
    if monk is not None and monk in living and d.working(monk, night) \
            and rng.random() < 0.3:
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

    monk = d.roles.index("Monk") if "Monk" in d.roles else None
    monk_works = (monk is not None and monk in living
                  and d.working(monk, night))
    if monk_works and rng.random() < 0.3 and target != monk:
        return None                             # the Monk guarded them

    if d.role_at(target, f"N{night}") == "Soldier" \
            and d.working(target, night):
        return None                             # a sober Soldier survives
    return target


# --------------------------------------------------------------------------
# What each character honestly learns
# --------------------------------------------------------------------------

# Characters whose ability fires *because* they died. Everybody else
# stays silent on the night they are killed.
ON_DEATH = frozenset({"Ravenkeeper", "Sage", "Klutz"})


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
    if role == "Courtier":
        # Woken until it names a character, and here it always does so
        # at its first chance: the first night, and the first night after
        # it has come back.
        return (seat, night) in d.courtier_nights
    if role in ("Philosopher", "Sage", "Klutz", "Juggler",
                "Seamstress", "Artist", "Savant"):
        # Once-a-game characters: they woke on the night they used it,
        # which the simulator records by having produced a row.
        return False
    if role == "Assassin":
        return False                      # once, and the row would say
    return False


def _droisoned_info(d, seat, night, rng):
    """What a droisoned seat was told, which is the Storyteller's choice.

    Read off what the seat *believes* it is: a Drunk holding a Fortune
    Teller token wakes when a Fortune Teller wakes and hears a Fortune
    Teller's kind of answer. Nobody tells it otherwise.

    Mostly false, and sometimes true by accident — a Storyteller handing
    out only lies would be a Storyteller with a tell.
    """
    if d.deaths.get(seat) is not None and _died_before(d, seat, night):
        return None
    apparent = d.apparent(seat)
    if apparent == d.roles[seat] and d.believes[seat] is None:
        # Poisoned rather than drunk: it is still its own character and
        # wakes on its own schedule.
        apparent = d.roles[seat]
    made = _for_role(d, seat, apparent, night, rng)
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
    if (d.believes[seat] is None
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
        what = d.believes[seat] or held
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
CHOOSES_EARLY = frozenset({"Innkeeper", "Sailor", "Monk", "Exorcist",
                           "SnakeCharmer", "PitHag", "Gambler", "Courtier",
                           "DevilsAdvocate", "Lunatic"})


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
    for seat in _in_night_order(d, night):
        role = before[seat]
        # A Philosopher that took an early chooser chooses early too. It
        # waited for the late pass, after the kill and the Barber, so one
        # holding the Snake Charmer pointed at a Demon the Barber had only
        # just made at slot 40 (29.09.2026).
        if role == "Philosopher" and night > 1 \
                and d.philosophies.get(seat) in CHOOSES_EARLY:
            role = d.philosophies[seat]
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
                and d.role_at(seat, f"N{night}") not in ON_DEATH:
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
        if (d.deaths.get(seat) == f"N{night}"
                and role_now not in ON_DEATH):
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
        if made is None and role == "Philosopher":
            took = d.philosophies.get(seat)
            # An early chooser it took has already acted, in the early pass.
            if took and not (took in CHOOSES_EARLY and night > 1):
                made = _for_role(d, seat, took, night, rng)
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
        if d.believes[p] is not None:
            out.add(p)

    if d.poisoned.get(night) is not None:
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
    got = d.innkeeper_drunk.get(night)
    if got is not None:
        keeper = next((p for p in range(d.n)
                       if d.role_at(p, phase) == "Innkeeper"
                       and p in living), None)
        if keeper is not None and keeper not in out:
            out.add(got)
    got = d.sailor_drunk.get(night)
    if got is not None:
        sailor = next((p for p in range(d.n)
                       if d.role_at(p, phase) == "Sailor"
                       and p in living), None)
        if sailor is not None and sailor not in out:
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
        minstrel = next((p for p in range(d.n)
                         if d.role_at(p, phase) == "Minstrel"
                         and p in living
                         and p in d.alive_at(f"E{day}")), None)
        if minstrel is not None:
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
        elif role == "Sweetheart":
            gone = d.deaths.get(seat)
            if gone and phase_index(gone) <= phase_index(phase):
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
        if not died:
            out.add(holder)

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

    if hasattr(info, "count") and info.count is not None:
        wrong = [n for n in range(0, d.n) if n != info.count]
        info.count = rng.choice(wrong)
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

    if kind == "Undertaker" and getattr(info, "role", None):
        # A Vortox makes it name the wrong character.
        #
        # There was no case for a row that carries a *role*, so an
        # Undertaker on a Vortox board announced the truth and the solver
        # rightly refused the game. Found on a board where a Philosopher
        # was working the ability, which is why it looked like a
        # Philosopher problem — it is not, a plain Undertaker was always
        # wrong here too.
        wrong = [k for k in d.script.keys if k != info.role]
        if not wrong:
            return None
        return type(info)(info.night, info.player, role=rng.choice(wrong))

    if kind == "NobleInfo":
        # A Vortox makes it false, and false here means the three shown
        # were **not** exactly one evil by registration — none of them,
        # or two, or all three.
        #
        # It has no count to spoil and no role to swap, so the generic
        # paths above walked straight past it and left a true reading on
        # a Vortox board. The solver rightly refused the whole game.
        phase = f"N{night}"

        def could(p):
            return sorted(evil_registrations(d.role_at(p, phase)))

        evil = [p for p in range(d.n) if could(p) == [True]]
        good = [p for p in range(d.n) if could(p) == [False]]
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
        spare = [k for k in pool if k not in (d.roles[info.a], d.roles[info.b])]
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
            outsiders = [p for p in range(d.n) if TEAM[d.roles[p]] == "outsider"]
            if not outsiders:
                return Librarian(1, seat, a=None, b=None, role="")
            return _pair_info(d, seat, night, rng, Librarian,
                              lambda p: TEAM[d.roles[p]] == "outsider",
                              team="outsider")
        if role == "Chef":
            pairs = sum(1 for i in range(d.n)
                        if is_evil(d.roles[i]) and is_evil(d.roles[(i + 1) % d.n]))
            return Chef(1, seat, count=pairs)

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
            opts = sorted(evil_registrations(d.role_at(p, phase)))
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
                                if d.side_at(p, f"N{night}") == "evil"))

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
        recluse = [p for p in (a, b) if d.roles[p] == "Recluse"]
        yes = (demon in (a, b) or d.red_herring in (a, b)
               or (bool(recluse) and rng.random() < 0.35))
        return FortuneTeller(night, seat, a=a, b=b, yes=yes)

    # --- Sects & Violets ------------------------------------------------

    if role == "Clockmaker" and night == 1:
        # Steps from the Demon to its nearest Minion, the shorter way
        # round the circle.
        demon = d.demon_at("N1")
        gaps = [min((m - demon) % d.n, (demon - m) % d.n)
                for m in range(d.n) if TEAM[d.roles[m]] == "minion"]
        if not gaps:
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
        # The side does not move: a Townsfolk turned into the Poisoner is
        # a *good* Poisoner.
        d.changes.append((phase, target, became))
        return PitHagChoice(night, seat, target=target, role=became)

    if role == "Philosopher" and night == 1:
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
        return PhilosopherChoice(night, seat, role=took)

    if role == "Flowergirl" and night > 1:
        # Whether the Demon voted during the day just gone.
        day = night - 1
        demon = d.demon_at(f"D{day}")
        voted = demon is not None and demon in d.votes.get(day, set())
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
                                    if d.side_at(p, phase) == "evil"))

    if role == "Seamstress" and night == 1:
        # Once a game, and the simulator uses it on the first night so
        # every game that has one produces the reading.
        others = [p for p in range(d.n) if p != seat]
        if len(others) < 2:
            return None
        a, b = sorted(rng.sample(others, 2))
        same = d.side_at(a, "N1") == d.side_at(b, "N1")
        return SeamstressInfo(night, seat, a=a, b=b, same=same)

    if role == "Sage" and d.deaths.get(seat) == f"N{night}":
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
        woke = 0
        for p in (a, b):
            what = d.apparent(p)             # a Drunk wakes on its token
            # A Lunatic lives the night of the Demon it thinks it is —
            # here always the real one — and choosing who it thinks it
            # kills counts (table ruling, 02.10.2026).
            if d.role_at(p, f"N{night}") == "Lunatic":
                real = d.demon_at(f"N{night}")
                what = (d.role_at(real, f"N{night}") if real is not None
                        else "Lunatic")
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
                continue
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
            if what in ("Spy", "EvilTwin"):
                continue
            if when == "never":
                continue
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
                woke += night >= 2 and (spent is None or spent >= night)
                continue
            # The Philosopher chooses on the first night here, always,
            # and choosing is waking for its ability. Its wake set says
            # "never" or "sometimes", so night one never counted it.
            if what == "Philosopher" and night == 1:
                woke += p in d.philosophies
                continue
            if when == "conditional":
                woke += bool(_conditionally_woke(d, p, what, night))
            elif night == 1:
                if when == "every" or ("first" in patterns
                                       and char.team != "demon"):
                    woke += 1
            elif when in ("every", "other"):
                woke += 1
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
        _the_goon_answers(d, night, seat, target)
        return ExorcistChoice(night, seat, target=target)

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
        if void:
            d.innkeeper_void.add(night)
        drunk = rng.choice([a, b])
        # Asked first, as with the Sailor. An Innkeeper that picked the
        # Pukka and the Goon it had poisoned found a Goon with no ability
        # — and only then made the Pukka drunk, which rests the poison.
        # Applying its drunkenness first had each undoing the other.
        if not any([_the_goon_answers(d, night, seat, picked)
                    for picked in (a, b)]) and not void:
            d.innkeeper_drunk.setdefault(night, drunk)
        return InnkeeperChoice(night, seat, a=a, b=b)

    if role == "DevilsAdvocate":
        # At 13, between the Gambler and the Exorcist — in the early pass
        # so that who chose the Goon *first* comes out in night order.
        _devils_advocate_picks(d, night, rng)
        return None

    if role == "Lunatic" and night > 1:
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
        named = rng.choice(list(d.script.townsfolk) + list(d.script.minions))
        # And the drunkenness itself, which was never applied: the row
        # was written and nobody got drunk. Decided now, while it is
        # known whether the Courtier itself was working tonight.
        holder = next((p for p in range(d.n)
                       if d.role_at(p, f"N{night}") == named), None)
        if holder is not None and d.working(seat, night):
            d.courtier_drunk = (night, holder, seat)
            d.courtier_drunks.append((night, holder, seat))
        return CourtierChoice(night, seat, role=named)

    if role == "Undertaker" and night > 1:
        executed = sorted(d.died_on(f"E{night - 1}"))
        if executed:
            when = f"E{night - 1}"
            return Undertaker(night, seat, target=executed[0],
                              role=d.role_at(executed[0], when))

    if role == "Ravenkeeper" and d.deaths.get(seat) == f"N{night}":
        others = [p for p in range(d.n) if p != seat]
        pick = rng.choice(others)
        return Ravenkeeper(night, seat, target=pick,
                           role=d.role_at(pick, f"N{night}"))
    return None


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


def _shown_as(d, seat, team, rng):
    """A character the Storyteller could show this seat as, for that team.

    A Recluse shown to an Investigator is not shown *as the Recluse* — it
    is shown as some Minion, and which one is the Storyteller's choice.
    Returning the true character would have produced a reading no legal
    world explains: "seat 4 is the Recluse" from a character that only
    ever names Minions.
    """
    from botc.catalogue import CHARACTERS
    role = d.roles[seat]
    if TEAM[role] == team:
        return role
    # Misregistering. Pick something of the right team that is not
    # already in play, since a Storyteller pointing at a character
    # somebody else really holds is asking to be caught.
    pool = {"townsfolk": TOWNSFOLK, "outsider": OUTSIDERS,
            "minion": MINIONS, "demon": DEMONS}[team]
    spare = [k for k in pool if k not in d.roles]
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
                 and _registers_as(d.roles[p], team)]

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
    role = d.roles[shown] if team is None else _shown_as(d, shown, team, rng)
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
        else:
            claims[seat] = d.apparent(seat)

    # The day comes through too. This predates the simulator having
    # nominations and votes at all, and without them a reading about the
    # day before refers to a day the state thinks nobody voted on.
    return GameState(n_players=d.n, claims=claims, **d.record(),
                     infos=list(infos), votes=dict(d.votes),
                     nominations=dict(d.nominations))
