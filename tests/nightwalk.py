"""Walking a night in slot order.

The experiment the design asks for, and nothing more: **can a night be
replayed?** Take a game the simulator has already played, walk its night
slot by slot, and see whether the walk produces what was recorded.

If a night that was just played cannot be reproduced, one that has to be
*inferred* certainly cannot, and that is worth knowing before any of the
solver's three passes is touched.

## Why this is the shape

The solver settles a night in three passes — transitions, death causes,
impairment plan — none of which can see the others. Almost every
character depends on the order. The **Goon** is the clearest: the first
player to choose it tonight is drunk and the Goon becomes *their
alignment*, so a Sailor acting before a Poisoner leaves the Goon good.
No set of "who was droisoned" can express that.

The walk is not a branch at every slot. Eleven choices are already
recorded, because good players announce what they did; the hidden ones
are the evil choices, which the impairment plan already searches over. So
the intended shape is **propose, then walk** — the plan proposes an
assignment, and the walk *checks* it.

This module is the walk half. The proposing half is not built.
"""

from botc.catalogue import CHARACTERS
from botc.roles import TEAM


class Night:
    """What is true as a night is walked, and what happened in it.

    Deliberately mutable and deliberately dumb: the whole point is that
    a character acting at slot 39 can see what the one at slot 7 did.
    """

    def __init__(self, roles, sides, alive):
        self.roles = dict(roles)            # seat -> character, now
        self.sides = dict(sides)            # seat -> "good"/"evil", now
        self.alive = set(alive)
        self.droisoned = set()
        self.died = set()
        self.chosen_by = {}                 # seat -> who chose it first
        self.guarded = set()                # safe from the Demon tonight
        self.gained = {}                    # seat -> ability it took
        self.silenced = set()               # Demons that cannot kill
        self.spared = set()                 # safe from execution tomorrow
        self.cursed = set()                 # dies if it nominates
        self.log = []                       # what happened, in order
        # Characters that always act and were not told what they did.
        #
        # Being under-informed used to look exactly like being wrong: a
        # probe that forgot the Gambler's guess made the walk refuse a
        # kill, and the failure pointed at the walk. Now the walk says so
        # itself, and a comparison can refuse to draw any conclusion
        # until this is empty.
        self.untold = set()
        self.readings = []                  # (slot, seat, role, answer)
        self.asked = {}                     # seat -> who it asked about
        self.executed_yesterday = None      # what an Undertaker sees
        self.night = 1                      # which night is being walked
        self.woke_count = {}                # Chambermaid answers, handed in
        self.red_herring = None             # the Fortune Teller's
        self.demon_voted = None             # what a Flowergirl hears
        self.minion_nominated = None        # what a Town Crier hears
        # Abilities stopped from doing what they say — a Monk's guard
        # holding, a Soldier surviving. By the rules a prevented ability
        # is one that went wrong, so a Mathematician counts it.
        self.prevented = set()

    def choose(self, chooser, target, slot):
        """Somebody's ability aimed at somebody.

        Recorded so the Goon can ask who was **first**, which is the
        thing no set can answer.
        """
        self.chosen_by.setdefault(target, (slot, chooser))
        self.log.append((slot, "chose", chooser, target))

    def droison(self, seat, slot, why):
        self.droisoned.add(seat)
        self.log.append((slot, "droisoned", seat, why))

    def kill(self, seat, slot, why):
        """Somebody dies — unless a Tea Lady is keeping them alive.

        **Both her living neighbours good means neither can die.** Full
        stop, whatever the death comes from: a Demon, a Gambler's wrong
        guess, an Acrobat's droisoned pick, a Tinker simply going.

        Asked here rather than at each cause, because there are six ways
        to die in this walk and every one of them has to ask. The
        simulator learned that the same way — a Tinker died beside a
        working Tea Lady and no world could explain it.
        """
        if self._a_tea_lady_holds(seat):
            self.prevented.add(seat)
            self.log.append((slot, "kept alive", seat, "Tea Lady"))
            return
        self.died.add(seat)
        self.alive.discard(seat)
        self.log.append((slot, "died", seat, why))

    def _a_tea_lady_holds(self, seat):
        for lady, role in self.roles.items():
            if role != "TeaLady" or lady not in self.alive:
                continue
            if lady in self.droisoned:
                continue
            around = []
            for step in (1, -1):
                for gap in range(1, len(self.roles)):
                    other = (lady + step * gap) % len(self.roles)
                    if other == lady:
                        break
                    if other in self.alive:
                        around.append(other)
                        break
            if seat in around and len(around) >= 2 \
                    and all(self.sides.get(p) == "good" for p in around):
                return True
        return False

    def working(self, seat):
        return seat in self.alive and seat not in self.droisoned


def slots(roles, night):
    """Every seat that acts tonight, in the order it acts.

    Read off what each seat *holds*, since a character that changed
    hands acts in its new slot — which is what makes an Imp starpassing
    to an Assassin cost the Assassin its night.
    """
    field = "first_night" if night == 1 else "other_night"
    out = []
    for seat, role in roles.items():
        got = getattr(CHARACTERS[role], field, 0) if role in CHARACTERS else 0
        if got:
            out.append((got, seat))
    return [seat for _slot, seat in sorted(out)]


def _turns(night):
    """Every slot number a character could act on, in order.

    The walk used to iterate **seats**, in an order fixed by who held
    what when the night began. That breaks the moment a character moves
    backwards through the order: a Snake Charmer at slot 11 takes the
    Demon's character, the Demon acts at 32, and the seat now holding it
    was visited at 11 and never comes round again. Nobody killed, on a
    night the record says somebody died.

    Iterating the slots and asking each time *who holds a character with
    this slot now* fixes it, because the question is asked after every
    change rather than once at the start. It is also what the simulator
    does, which is why the two disagreed.
    """
    field = "first_night" if night == 1 else "other_night"
    return sorted({getattr(c, field, 0) for c in CHARACTERS.values()
                   if getattr(c, field, 0)})


class AsBoard:
    """A solver world, in the shape the walk expects.

    The walk asks a deal four things — `n`, `role_at`, `side_at`,
    `alive_at` — and a `World` answers two of them already. This is the
    whole adapter, which is the encouraging part: the walk was written
    against a simulated game and turns out to want almost nothing that a
    solver world cannot say.

    Deaths come from the state rather than the world, because a world is
    a story about who holds what and the record of who died is separate.

    **A bare `World` carries no changes.** It says who was dealt what,
    and a swap or a creation lives in a `Timeline` wrapped around it —
    which is what `possible_timelines` produces and `_explain` scores. So
    the thing to hand here is the *view*, not the world underneath, or
    the walk starts every night from the deal and misses everything that
    has happened since.
    """

    def __init__(self, world, state):
        self.world = world
        self.state = state
        self.n = state.n_players

    def role_at(self, seat, phase):
        return self.world.role_at(seat, phase)

    def side_at(self, seat, phase):
        return "evil" if self.world.evil_at(seat, phase) else "good"

    def alive_at(self, phase):
        return self.state.alive_set(phase)

    @property
    def roles(self):
        return self.world.roles

    def demon_at(self, phase):
        return self.world.demon_at(phase)


def hidden_from(deal, night, heard):
    """Everything the walk needs to be told, read off a played game.

    **Use this rather than assembling the dictionary by hand.**

    The list of hidden inputs grows every time the walk learns a
    character, and three separate comparisons failed this way: an
    ad-hoc probe passed the Tinker and the Moonchild but not the
    Gambler's guess, or not the Pukka's poison coming due, and the walk
    refused a kill it had no way to know about. Each time it looked like
    a walk bug and was a probe bug.

    Keeping it in one place means a new character is added here once and
    every caller gets it. In the solver these come from the impairment
    plan instead; here they come from what the simulator chose.
    """
    phase = f"N{night}"
    # Droisonings already standing when the night began: a Sweetheart's
    # from the night it died, a Courtier's three-day run, and above all a
    # **swapped Snake Charmer**, which is poisoned for the rest of the
    # game and so cannot swap again.
    #
    # The walk has had a channel for these since the Mathematician needed
    # them and this never filled it — so a charmer that had already
    # swapped kept its ability, pointed at the seat now holding the
    # Demon, and swapped straight back.
    # Only those poisoned *before* tonight. `perma_poisoned` is the state
    # at the end of the game, so handing it over whole silenced seats on
    # nights before they were ever touched — 178 nights became 176.
    #
    # A swapped Snake Charmer is poisoned from the swap onward, and the
    # swap is in `changes` with the phase it happened at.
    # Built by **subtraction** rather than by listing sources.
    #
    # Listing them meant a swapped Snake Charmer was passed while a
    # Sweetheart's droison and a Courtier's three-day run were not — and
    # a missing hidden input looks exactly like a rule disagreement,
    # which is the fourth time that has cost a diagnosis here.
    #
    # What the walk works out for itself is the Poisoner's hit; anything
    # else standing has to be handed over.
    import simulate
    derives = set()
    if deal.poisoned.get(night) is not None:
        derives.add(deal.poisoned[night])
    # The Pukka's fresh poison is the walk's own to place, at its slot —
    # so it is asked for with that token lifted, rather than subtracted
    # afterwards: a Gambler the Courtier had already made drunk was
    # poisoned by the Pukka on top, and subtracting the seat handed the
    # walk a sober Gambler. The token still standing from last night is
    # different. It was on the board when the night began.
    fresh = deal.pukka_marks.pop(night, None)
    try:
        standing = set(simulate.droisoned_at(deal, night)) - derives
    finally:
        if fresh is not None:
            deal.pukka_marks[night] = fresh
    # Whoever the Pukka's poison came due for was still poisoned as the
    # night began, whether or not they lived to see the morning.
    came_due = deal.pukka_history.get(night)
    if came_due and came_due[0] is not None:
        standing.add(came_due[0])
    if standing:
        out = {("standing", night): standing}
    else:
        out = {}
    out.update({"red_herring": deal.red_herring,
                "gained": dict(getattr(deal, "philosophies", {}) or {})})

    def row(kind):
        return [h for h in heard
                if type(h).__name__ == kind and h.night == night]

    if deal.poisoned.get(night) is not None:
        out[("poisoner", night)] = deal.poisoned[night]
    if deal.demon_aimed.get(night):
        out[("demon", night)] = deal.demon_aimed[night]
    # A Fang Gu's jump: it aimed at an Outsider and they took its place.
    # The simulator leaves no aim behind for it, since nobody died of it.
    jump = getattr(deal, "fanggu_jump", None)
    if jump and jump[0] == night:
        out[("fanggu_jump", night)] = jump[1]
    # A Barber's swap, at slot 40: without it a Dreamer at 56 read the
    # seat as it was before (30.09.2026, once the Demon swapped with its
    # own Minion half the time).
    swap = (getattr(deal, "barber_swaps", None) or {}).get(night)
    if swap:
        out[("barber", night)] = swap
    due = deal.pukka_history.get(night)
    if due and due[0] is not None:
        out[("pukka_due", night)] = due[0]
    if due and due[1] is not None:
        out[("pukka_fresh", night)] = due[1]
    if deal.monk_guarded.get(night) is not None:
        out[("monk", night)] = deal.monk_guarded[night]
    if deal.innkeeper_guarded.get(night):
        out[("innkeeper", night)] = deal.innkeeper_guarded[night]
    if deal.innkeeper_drunk.get(night) is not None:
        out[("innkeeper_drunk", night)] = deal.innkeeper_drunk[night]
    if deal.sailor_drunk.get(night) is not None:
        out[("sailor_drunk", night)] = deal.sailor_drunk[night]
    if deal.cursed.get(night) is not None:
        out[("witch", night)] = deal.cursed[night]

    # Choices the table *hears*, read straight off the rows. These were
    # missing and the walk's own warning found them — a Sailor, a Snake
    # Charmer and an Exorcist all announce what they did, the row sits in
    # `heard`, and nothing was reading it.
    # Whether this night's Snake Charmer row was the one that swapped.
    charm = row("SnakeCharmerChoice")
    if charm:
        out[("snakecharmer_swapped", night)] = bool(charm[0].swapped)

    for kind, key in (("SailorChoice", "sailor"),
                      ("SnakeCharmerChoice", "snakecharmer"),
                      ("ExorcistChoice", "exorcist"),
                      ("AcrobatChoice", "acrobat"),
                      ("MonkChoice", "monk")):
        got = row(kind)
        if got and (key, night) not in out:
            out[(key, night)] = got[0].target

    # What a Pit-Hag made. The walk has had the branch since it learned
    # the character and nothing ever filled it: the comparisons happened
    # to draw no game where it mattered until the deal changed shape
    # (02.10.2026), and then a Dreamer at 56 read the seat as it had been.
    made = row("PitHagChoice")
    if made:
        out[("pithag", night)] = (made[0].target, made[0].role)

    guess = row("GamblerGuess")
    if guess:
        out[("gambler", night)] = (guess[0].target, guess[0].role)
    moon = row("MoonchildChoice")
    if moon:
        out[("moonchild", night)] = moon[0].target
    gran = [h for h in heard if type(h).__name__ == "GrandmotherInfo"]
    if gran:
        out["grandchild"] = gran[0].target
    if any(deal.role_at(p, phase) == "Tinker"
           and deal.deaths.get(p) == phase for p in range(deal.n)):
        out[("tinker", night)] = True

    executed = [p for p, at in deal.deaths.items()
                if at == f"E{night - 1}"]
    if executed:
        out[("executed", night)] = executed[0]
    return out


# Characters that act every night they are alive and working. If one of
# these is on the board and the walk was told nothing about it, the walk
# has been under-informed — which is a different thing from the character
# having done nothing, and must not be mistaken for it.
ALWAYS_ACTS = {
    "Poisoner": "poisoner", "Monk": "monk", "Sailor": "sailor",
    "Innkeeper": "innkeeper", "SnakeCharmer": "snakecharmer",
    "Witch": "witch", "Exorcist": "exorcist", "Acrobat": "acrobat",
}


def _note_what_we_were_not_told(state, deal, roles, night, hidden):
    """Characters that should have acted and were never mentioned.

    Run once the night is over, because whether a character acted depends
    on whether it was droisoned, and the Poisoner acts at slot 7 — inside
    the walk. Asked beforehand, every seat looks sober.

    A seat that *became* one of these mid-game is exempt: a Snake Charmer
    swap leaves the old Demon holding the character from the day after,
    and it has no row for that night because it was not one when the
    readings were taken.
    """
    for seat, role in roles.items():
        key = ALWAYS_ACTS.get(role)
        if key is None or seat not in state.alive:
            continue
        if seat in state.droisoned:
            continue                      # droisoned, so it does nothing
        if deal.roles[seat] != role:
            continue                      # arrived mid-game
        if hidden.get((key, night)) is None:
            state.untold.add(role)


def walk(deal, night, hidden):
    """Replay one night and return what it produced.

    `hidden` is the assignment the plan would propose: where the Poisoner
    went, who the Demon killed. Everything else is read off the deal,
    because it was announced.

    Only the characters needed to test the idea are here — a Poisoner, a
    Sailor, a Goon, a Demon, an Acrobat. That is enough to say whether
    replay reproduces a known night; it is not a night order.
    """
    phase = f"N{night}"

    # The board as it stood **before** tonight, not as it stands after.
    #
    # `role_at(seat, "N2")` already contains every change stamped at N2 —
    # so starting there and then walking the night applied tonight's
    # changes a *second* time. For a Pit-Hag creation that is invisible,
    # because setting a seat to a character it already holds does
    # nothing. For a Snake Charmer swap it is a bug: doing it twice
    # swaps the pair straight back, and the seat holding the Demon became
    # a charmer again and killed nobody.
    #
    # Raised at the table, and it is the right shape: the walk should
    # start where the night started and *become* the board by walking.
    # Anything else is applying history twice and hoping it is
    # idempotent.
    was = f"E{night - 1}" if night > 1 else phase
    roles = {seat: deal.role_at(seat, was) for seat in range(deal.n)}
    sides = {seat: deal.side_at(seat, was) for seat in range(deal.n)}
    state = Night(roles, sides, deal.alive_at(phase))
    # Droisonings that were already standing when the night began — a
    # Sweetheart's from the night it died, a swapped Snake Charmer's, a
    # Courtier's three-day run. The walk starts each night fresh, so
    # anything that persists has to be carried in.
    #
    # A Mathematician counting nought where the answer was two is what
    # showed this up: the walk cannot count abilities that went wrong
    # before it started watching.
    for seat in (hidden.get(("standing", night)) or ()):
        state.droisoned.add(seat)

    # Abilities gained on an *earlier* night. A Philosopher chooses once
    # and keeps what it took, so a gain made on night one is still in
    # force on night three — and the walk, which starts each night fresh,
    # would otherwise forget it.
    #
    # This was reached into from outside by the test harness for a while,
    # which is a smell: the walk should take everything it is told
    # through `hidden`, like every other thing it does not derive.
    state.gained.update(hidden.get("gained") or {})

    state.night = night
    state.executed_yesterday = hidden.get(("executed", night))
    state.asked = dict(hidden.get(("asked", night)) or {})
    state.woke_count = dict(hidden.get(("woke", night)) or {})
    state.red_herring = hidden.get("red_herring")
    state.demon_voted = hidden.get(("demon_voted", night))
    state.minion_nominated = hidden.get(("minion_nominated", night))

    field = "first_night" if night == 1 else "other_night"
    for slot in _turns(night):
        # Who holds a character with this slot **now**.
        #
        # Asked afresh at every slot, because a swap moves characters
        # between seats mid-night and the answer changes as the walk
        # goes. A seat may act twice if two characters pass through it,
        # which is correct: the Storyteller wakes whoever holds the
        # token when that token's turn comes.
        here = [p for p in sorted(state.roles)
                if getattr(CHARACTERS.get(state.roles[p]), field, 0) == slot]
        for seat in here:
            role = state.roles[seat]

            if role == "Poisoner":
                target = hidden.get(("poisoner", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if state.working(seat):
                    state.droison(target, slot, "Poisoner")

            elif role == "Sailor":
                target = hidden.get(("sailor", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                # One of the two is drunk; which is the Storyteller's, so the
                # walk is told rather than deciding.
                drunk = hidden.get(("sailor_drunk", night))
                if drunk is not None:
                    state.droison(drunk, slot, "Sailor")

            elif role == "Philosopher":
                # Takes a good character's ability. Acts at 2 — before almost
                # everything, which matters because whoever really holds that
                # character is drunk from then on, and they may act later
                # tonight.
                # Keyed by seat, because a table can hold more than one and
                # `("philosopher", night)` could only ever name one of them.
                took = (hidden.get(("philosopher", night)) or {}).get(seat)
                if took is None or not state.working(seat):
                    continue
                state.gained[seat] = took
                for other, role_there in state.roles.items():
                    if other != seat and role_there == took:
                        state.droison(other, slot, "Philosopher")

            elif role == "Courtier":
                # Three days and nights of drunkenness for whoever holds the
                # character it names. Acts at 8, before the Demon.
                named = hidden.get(("courtier", night))
                if named is None or not state.working(seat):
                    continue
                for other, role_there in state.roles.items():
                    if role_there == named:
                        state.droison(other, slot, "Courtier")

            elif role == "SnakeCharmer":
                # Swaps with the Demon if it points at one. Acts at 11, so
                # the swap happens *before* the Demon's kill — and the seat
                # that kills is the charmer's, holding the Demon now.
                target = hidden.get(("snakecharmer", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue
                if TEAM.get(state.roles.get(target, ""), "") != "demon":
                    continue
                became = state.roles[target]
                state.roles[seat], state.roles[target] = became, "SnakeCharmer"
                state.sides[seat], state.sides[target] = "evil", "good"
                state.droison(target, slot, "SnakeCharmer swap")
                state.log.append((slot, "swapped", seat, target))

            elif role == "Monk":
                # Guards somebody from the Demon. Acts at 12, before every
                # Demon, which is what makes the guard mean anything: the
                # Demon arrives later and finds the seat already protected.
                target = hidden.get(("monk", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if state.working(seat):
                    state.guarded.add(target)

            elif role == "Innkeeper":
                # Two players are safe tonight and one of them is drunk. Acts
                # at 9, before the Monk and long before the Demon.
                # A pair, but tolerate a single seat: the enumerator hands
                # over a tuple sized by the source's capacity, and a source
                # that can only reach one seat gives an int.
                picked = hidden.get(("innkeeper", night)) or ()
                if isinstance(picked, int):
                    picked = (picked,)
                if not picked or not state.working(seat):
                    continue
                for target in picked:
                    state.choose(seat, target, slot)
                    _goon_answers(state, seat, target, slot)
                if state.working(seat):
                    state.guarded |= set(picked)
                    drunk = hidden.get(("innkeeper_drunk", night))
                    if drunk is not None:
                        state.droison(drunk, slot, "Innkeeper")

            elif role == "Gambler":
                # Names somebody and a character, and dies if it guessed
                # wrong. Acts at 10, so a Poisoner at 7 has already had its
                # say — and a droisoned Gambler dies of nothing, because a
                # plain ability simply does not function.
                guess = hidden.get(("gambler", night))
                if guess is None:
                    continue
                # Judged when it acts, not after its target answers back —
                # the same rule the Demon needed. A Gambler that picks the
                # Goon is drunked by it, and the guess is already made, so
                # the wrong guess still kills.
                able = state.working(seat)
                target, said = guess
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if able and state.roles.get(target) != said:
                    state.kill(seat, slot, "Gambler")

            elif role == "Tinker":
                # May die at any time, and the Storyteller decides. Nothing
                # to derive: the walk is told whether it went tonight.
                if hidden.get(("tinker", night)) and seat in state.alive:
                    state.kill(seat, slot, "Tinker")

            elif role == "Acrobat":
                # Picks somebody and dies if they are — or **become** —
                # droisoned tonight. Acts at 39, after the Poisoner at 7 and
                # every Demon, which is what makes "or become" more than a
                # turn of phrase: the walk has already seen everything that
                # could have touched the pick.
                #
                # This is the character the whole night order was built for.
                # It could not be modelled in the three-pass design at all —
                # the inference needs the impairment plan and the death
                # causes settled together, and they were settled separately.
                # Here it is four lines, because the night has happened.
                #
                # A droisoned Acrobat does not function: a plain ability
                # simply does not work. And a dead player may be picked — the
                # Drunk is drunk whether or not it is breathing.
                target = hidden.get(("acrobat", night))
                if target is None or seat not in state.alive:
                    continue
                if not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if target in state.droisoned:
                    state.kill(seat, slot, "Acrobat")

            elif role == "Gossip":
                # Said something in public yesterday, and if it was true a
                # player dies tonight. Acts at 38 — after the Demon at 24 and
                # before the readings, so a Gossip kill is on the board by
                # the time an Empath counts neighbours at 53.
                #
                # Whether the statement was true is a matter of what was said
                # out loud, which no replay can work out. So the *victim* is
                # handed in, like every other thing the walk is told: the
                # walk's contribution is that the death lands here rather
                # than at some unordered moment.
                target = hidden.get(("gossip", night))
                if target is None or not state.working(seat):
                    continue
                if target in state.alive:
                    state.kill(target, slot, "Gossip")

            elif role == "Moonchild":
                # Named somebody when it died in daylight; if they are good,
                # they die tonight. Acts at 50, after the Demon, so it can
                # add a body the Demon did not take.
                target = hidden.get(("moonchild", night))
                if target is None:
                    continue
                if state.sides.get(target) == "good" and target in state.alive:
                    state.kill(target, slot, "Moonchild")

            elif role == "Sage":
                # Killed by the Demon, learns two players one of whom did it.
                # Acts at 42 — after the Demon at 24, which is the only way
                # it can know. Nothing to change, only to learn.
                continue

            elif role == "Butler":
                # Picks a master and may only vote with them. A day matter,
                # decided at night. Nothing tonight to change.
                target = hidden.get(("butler", night))
                if target is not None:
                    state.choose(seat, target, slot)
                    _goon_answers(state, seat, target, slot)

            elif role in ("Spy", "EvilTwin", "Lunatic"):
                # All three are *shown* something rather than doing anything:
                # the Spy sees the grimoire, an Evil Twin its twin, a Lunatic
                # a Demon's night. None of them changes the board, so the
                # walk records that they woke and moves on.
                state.log.append((slot, "shown", seat, role))

            elif role == "Exorcist":
                # Names the Demon, and it does not kill tonight. Acts at 21,
                # before every Demon, which is what lets it work at all.
                target = hidden.get(("exorcist", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if state.working(seat) \
                        and TEAM.get(state.roles.get(target, ""), "") == "demon":
                    state.silenced.add(target)
                    state.log.append((slot, "exorcised", target, ""))

            elif role == "DevilsAdvocate":
                # Keeps somebody from dying by execution tomorrow. Nothing
                # happens tonight, but the choice is made now.
                target = hidden.get(("devilsadvocate", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                state.spared.add(target)

            elif role == "Witch":
                # Curses somebody: if they nominate tomorrow, they die.
                # Again nothing tonight, but the aim is taken now.
                target = hidden.get(("witch", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                state.cursed.add(target)

            elif role == "PitHag":
                # Turns somebody into a character not in play. Acts at 16 —
                # before every Demon, so a seat made into a Demon tonight
                # could act at the Demon's slot, and a Demon unmade before
                # its slot never acts at all.
                made = hidden.get(("pithag", night))
                if made is None or not state.working(seat):
                    continue
                target, became = made
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if state.working(seat):
                    state.roles[target] = became   # the side does not move
                    state.log.append((slot, "made", target, became))

            elif role == "Assassin":
                # One kill, once a game, and it ignores protection. Acts at
                # 36 — *after* every Demon, which is what makes a starpass
                # to an Assassin cost it the night: by 36 that seat is
                # holding the Demon and this branch never runs.
                target = hidden.get(("assassin", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if target in state.alive:
                    state.kill(target, slot, "Assassin")

            elif role == "Godfather":
                # Kills if an Outsider died in daylight. Acts at 37, after
                # the Demon, so it can add a second body to the night.
                target = hidden.get(("godfather", night))
                if target is None or not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if target in state.alive:
                    state.kill(target, slot, "Godfather")

            elif role == "Sweetheart":
                # From the night it dies, somebody is drunk for good. Acts at
                # 41, so whoever it drunks has already acted tonight — the
                # effect is felt from tomorrow.
                drunk = hidden.get(("sweetheart", night))
                if drunk is not None:
                    state.droison(drunk, slot, "Sweetheart")

            elif role == "Barber":
                # Died today, so the Demon may swap two players tonight.
                # Characters only — a swapped seat keeps its own side.
                swap = hidden.get(("barber", night))
                if swap is None:
                    continue
                a, b = swap
                state.roles[a], state.roles[b] = state.roles[b], state.roles[a]
                state.log.append((slot, "swapped", a, b))

            elif role == "ScarletWoman":
                # Not an action so much as a standing readiness: it takes the
                # star if the Demon falls with five alive. Nothing to do at
                # its own slot — the Demon's death is what triggers it, and
                # that happens later in the night.
                continue

            elif TEAM[role] == "demon":
                # A list, because a Shabaloth takes two and a Po none or
                # three. What it aimed at is handed in like every other
                # hidden choice; the walk decides what *lands*.
                # A Fang Gu that took an Outsider for the first time: the
                # Outsider lives and is the Fang Gu now, the old one dies.
                # Asked first — a jump leaves no aim behind, since nobody
                # died of the kill itself.
                jump = hidden.get(("fanggu_jump", night))
                if role == "FangGu" and jump is not None \
                        and state.working(seat):
                    state.choose(seat, jump, slot)
                    state.kill(seat, slot, "FangGu jumped")
                    state.roles[jump] = "FangGu"
                    state.log.append((slot, "jumped", seat, jump))
                    continue
                if role == "Pukka":
                    _pukka_takes_its_turn(state, seat, slot, hidden, night)
                    continue
                aimed = hidden.get(("demon", night))
                if aimed is None or not state.working(seat):
                    continue
                targets = [aimed] if isinstance(aimed, int) else list(aimed)
                if seat in state.silenced:
                    state.log.append((slot, "exorcised", seat, "no kill"))
                    continue

                # Whether the ability functions is decided **when the
                # character acts**, not after its own target has answered
                # back. A Demon that chooses the Goon is made drunk by it —
                # and the choice is already made, so the kill still lands.
                #
                # Checking afterwards had the Goon protecting itself from
                # every Demon that picked it, which is not what the card
                # says and cost twelve of eighty nights.
                able = state.working(seat)
                for target in targets:
                    state.choose(seat, target, slot)
                    _goon_answers(state, seat, target, slot)
                    if not able:
                        break

                    if target not in state.alive:
                        continue              # sunk into a corpse
                    # A guard set earlier tonight holds, which is the whole
                    # reason the Monk acts at 12 and the Demon at 24.
                    if target in state.guarded:
                        state.log.append((slot, "guarded", target, role))
                        state.prevented.add(seat)
                        continue
                    if state.roles.get(target) == "Soldier" \
                            and state.working(target):
                        state.log.append((slot, "guarded", target, "Soldier"))
                        state.prevented.add(seat)
                        continue
                    state.kill(target, slot, role)
                    _grandmother_grieves(state, target, slot, hidden, night)

    # Everything above changed the board. What follows only *reads* it —
    # and reads it as it stands at that seat's slot, which is the whole
    # reason they come late in the night.
    #
    # An Undertaker at 55 sees who was executed; an Empath at 53 counts
    # neighbours who may have died at 24; a Ravenkeeper at 52 learns a
    # character that a Pit-Hag may have changed at 16. None of them can
    # be answered before the night has been walked to their slot.
    for seat in slots(state.roles, night):
        role = state.roles[seat]
        slot = getattr(CHARACTERS[role],
                       "first_night" if night == 1 else "other_night", 0)
        # A Philosopher reads with the ability it took, at *that*
        # character's slot rather than its own — it acts at 2 to choose
        # and then again wherever the gained character sits.
        #
        # Reading its own name found nothing, which is why four
        # Flowergirl readings came back absent rather than wrong. Absent
        # is the harder kind to notice.
        gained = state.gained.get(seat)
        if gained and gained in READS:
            role = gained
        if role not in READS:
            continue
        # The dead stop hearing — except a Ravenkeeper, whose whole
        # ability is that it died. `working` requires being alive, so
        # asking it first rejected the one character that has to be dead
        # to read at all, and no Ravenkeeper reading was ever taken.
        if seat not in state.alive and role != "Ravenkeeper":
            continue
        if seat in state.droisoned:
            continue                      # told anything, so nothing true
        state.readings.append((slot, seat, role, _reads(state, seat, role)))

    # Asked once the night is over, because whether a character acted
    # depends on whether it was droisoned — and the Poisoner acts at slot
    # 7, inside this walk. Asked beforehand, every seat looks sober, and
    # a Monk the Poisoner was about to reach looked like a Monk nobody
    # had mentioned.
    _note_what_we_were_not_told(state, deal, roles, night, hidden)

    return state


# Characters whose ability produces information rather than changing
# anything. They are walked in a second pass over the same order, so a
# seat that died at 24 is dead when the Empath counts at 53.
READS = frozenset({
    "Empath", "FortuneTeller", "Undertaker", "Ravenkeeper", "Chef",
    "Washerwoman", "Librarian", "Investigator", "Dreamer", "Oracle",
    "Seamstress", "Juggler", "Flowergirl", "TownCrier", "Clockmaker",
    "Mathematician", "Chambermaid", "Professor", "Sage", "Gossip",
    "Moonchild", "Klutz", "Farmer",
})


def _reads(state, seat, role):
    """What this seat would learn, from the night as it now stands.

    Deliberately thin: the walk's job here is to say *when* a reading is
    taken and what the board looked like then. Deriving the answer for
    thirty characters is the simulator's work and is already done there —
    what was missing was the moment.
    """
    if role == "Empath":
        alive = sorted(state.alive)
        if len(alive) < 3:
            return None
        where = alive.index(seat) if seat in alive else 0
        around = [alive[(where - 1) % len(alive)],
                  alive[(where + 1) % len(alive)]]
        return sum(1 for p in around if state.sides.get(p) == "evil")
    if role == "Undertaker":
        # Who was executed yesterday, and what they held *then*. Reads at
        # 55, so anything that changed them tonight is irrelevant — it is
        # yesterday's execution being looked at.
        return state.executed_yesterday

    if role == "Chambermaid":
        # How many of two chosen seats woke for their own ability
        # tonight. The walk knows exactly, because it watched them: this
        # is the reading that most obviously needs the night to have
        # happened before it can be answered.
        picked = state.asked.get(seat)
        if not picked:
            return None
        # Whether a seat *woke for its own ability*, which is not the
        # same as whether it chose anybody.
        #
        # A Courtier names a character rather than pointing at a seat; a
        # Tinker may simply die; a Godfather is shown the Outsiders. All
        # of them wake, none of them chooses. Counting only `chose`
        # missed every one — seven of sixteen.
        #
        # So it is asked of the catalogue, the same question the solver's
        # `woke` asks: does this character have a slot tonight at all?
        # A slot says a character *can* wake; it does not say it did.
        #
        # Three tries at this. Counting `chose` missed a Courtier, which
        # names a character rather than a seat. Counting the slot alone
        # counted a Lunatic that never acted. What is wanted is the
        # narrower question — did this seat wake **for its own ability**
        # tonight — and the walk cannot answer it for characters it has
        # not implemented yet.
        #
        # So it is left to the caller, like every other thing the walk is
        # told rather than derives. When the walk covers every character
        # this becomes derivable and the hand-in can go.
        return state.woke_count.get(seat)

    if role == "Oracle":
        # How many of the dead are evil, counted by side *now* — so a
        # Goon that turned tonight counts the way it turned.
        return sum(1 for p in range(len(state.roles))
                   if p not in state.alive
                   and state.sides.get(p) == "evil")

    if role == "Ravenkeeper":
        # Dies at night and learns a character. Reads at 52, after every
        # Demon, which is what lets it read at all — and it learns what
        # the seat holds *now*, so a Pit-Hag creation at 16 is what it
        # sees, not what was dealt.
        target = state.asked.get(seat)
        if target is None:
            return None
        return state.roles.get(target)

    if role == "FortuneTeller":
        # Two players, and whether either registers as the Demon. Reads
        # at 54, so a seat the Demon killed at 24 is dead — and a dead
        # Demon still registers as one.
        pair = state.asked.get(seat)
        if not pair:
            return None
        herring = state.red_herring
        return any(TEAM.get(state.roles.get(p, ""), "") == "demon"
                   or p == herring for p in pair)

    if role in ("Washerwoman", "Librarian", "Investigator"):
        # Two players, one of whom is the character named. Read on the
        # first night only, and the *shown* character is the
        # Storyteller's choice — misregistration is legal, so what the
        # walk can check is which team the pair was drawn from, not the
        # exact name.
        pair = state.asked.get(seat)
        if not pair:
            return None
        want = {"Washerwoman": "townsfolk", "Librarian": "outsider",
                "Investigator": "minion"}[role]
        return sorted(p for p in pair
                      if _shows_as(state, p, want))

    if role == "Flowergirl":
        # Whether the Demon voted today. Reads at 57 — after the Demon
        # has acted, though what it wants is yesterday's vote, so this is
        # handed in like the Undertaker's execution.
        return state.demon_voted

    if role == "TownCrier":
        # Whether a Minion nominated today. Same shape: yesterday's
        # business, read tonight.
        return state.minion_nominated

    if role == "Dreamer":
        # A good character and an evil one for a chosen seat, one of
        # which is true. Reads at 56, so a seat changed by a Pit-Hag at
        # 16 is read as what it holds *now*.
        target = state.asked.get(seat)
        if target is None:
            return None
        return state.roles.get(target)

    # NOTE: the Professor is deliberately absent.
    #
    # It was written, and then removed, because **the simulator never
    # fires one** — eighty games of Bad Moon Rising produced no Professor
    # reading at all. So there was nothing to compare it against, and an
    # unverified derivation is worth less than an honest gap: the
    # Ravenkeeper silently compared zero cases and looked verified for a
    # whole round.
    #
    # Add it back when the simulator can raise the dead. Until then this
    # comment is the more useful artefact.

    if role == "Clockmaker":
        # How many steps from the Demon to its nearest Minion. Read on
        # the first night, so it is the board as dealt — but read off
        # `state.roles`, which means a Pit-Hag or a swap earlier that
        # night is already accounted for.
        demon = next((p for p, r in state.roles.items()
                      if TEAM.get(r) == "demon"), None)
        if demon is None:
            return None
        n = len(state.roles)
        best = None
        for p, r in state.roles.items():
            if TEAM.get(r) != "minion":
                continue
            gap = min((p - demon) % n, (demon - p) % n)
            best = gap if best is None else min(best, gap)
        return best

    if role == "Seamstress":
        # Two players, and whether they are the same side. Reads at 60,
        # so a Goon that turned at 7 is read the way it turned.
        pair = state.asked.get(seat)
        if not pair:
            return None
        a, b = pair
        return state.sides.get(a) == state.sides.get(b)

    if role == "Mathematician":
        # How many abilities went wrong tonight. Reads at 62, last of
        # all, which is exactly right: it has to wait for the whole night
        # to have happened before it can count.
        #
        # The walk can answer this properly where the three-pass design
        # cannot, because it *watched*. Every droisoning it recorded is
        # an ability that did not work — and by the rules an ability that
        # was **prevented** counts too, which is why the guarded seats
        # are in here alongside the droisoned ones.
        wrong = set(state.droisoned)
        wrong |= {p for p in state.prevented}
        return len(wrong - {seat})

    if role == "Juggler":
        # How many of yesterday's public guesses were right. Reads at 61,
        # and the guesses were made in daylight — so what matters is what
        # each seat held *then*, which is handed in with the guesses.
        guesses = state.asked.get(seat)
        if not guesses:
            return None
        return sum(1 for who, what in guesses
                   if state.roles.get(who) == what)

    # NOTE: the Savant and the Artist are deliberately absent.
    #
    # A Savant is told two statements, one true; an Artist asks a
    # question and is told yes or no. Both are free text the Storyteller
    # invents, so there is nothing for a replay to derive — the walk can
    # say *when* they were told and nothing about *what*.
    #
    # The solver treats them the same way: `weighed` returns False, so
    # they are kept rather than solved. Listing them here with a
    # derivation that returned None would look like coverage and be none.

    if role == "Chef":
        alive = sorted(state.alive)
        pairs = 0
        for i, p in enumerate(alive):
            q = alive[(i + 1) % len(alive)]
            if state.sides.get(p) == "evil" and state.sides.get(q) == "evil":
                pairs += 1
        return pairs
    return None



def _shows_as(state, seat, team):
    """Could this seat have been shown as that team?

    Registration, not truth — a Spy shows as a Townsfolk, a Recluse as a
    Minion. What the walk contributes here is *when*: the pair is drawn
    on the first night, from the board as it stood then.
    """
    role = state.roles.get(seat)
    if role is None:
        return False
    if TEAM.get(role) == team:
        return True
    return team in CHARACTERS[role].registers


def _grandmother_grieves(state, victim, slot, hidden, night):
    """Her grandchild taken by the Demon takes her with it.

    Only the Demon's kill does this, and only if she is working — which
    the walk knows because everything that could have droisoned her has
    already acted by the time a Demon kills.

    Which seat is the grandchild was settled on night one and is handed
    in, like every other thing the walk is told rather than guesses.
    """
    child = hidden.get("grandchild")
    if child is None or child != victim:
        return
    for seat, role in state.roles.items():
        if role != "Grandmother" or seat not in state.alive:
            continue
        if not state.working(seat):
            continue                      # droisoned: she feels nothing
        state.kill(seat, slot, "grief")


def _goon_answers(state, chooser, target, slot):
    """If that was a Goon, and the first to choose it, it turns.

    **The reason the whole walk exists.** The Goon takes the alignment of
    whoever chose it *first*, and makes them drunk — so a Sailor acting
    before a Poisoner leaves the Goon good, and the Poisoner arriving
    later changes nothing about its side.

    Order decides an *alignment* here, not merely whether an ability
    worked, which is why no amount of set arithmetic could hold it.
    """
    if state.roles.get(target) != "Goon":
        return
    first_slot, first = state.chosen_by.get(target, (None, None))
    if first != chooser or first_slot != slot:
        return                              # somebody got there first
    if not state.working(target):
        return                              # a droisoned Goon does nothing
    state.sides[target] = state.sides[chooser]
    state.droison(chooser, slot, "Goon")
    state.log.append((slot, "turned", target, state.sides[chooser]))



# ----------------------------------------------------------------------
# The solver-side switch, moved here from botc/solver.py.
#
# `WALK_CHECKS_STORIES` replayed every candidate story before scoring it.
# Measured, it buys nothing: on the board where it refuses most, 672
# worlds both ways, 5.7s against 60.9s, every percentage identical. Every
# story it rejects would have scored zero anyway.
#
# Kept because the *measurement* is worth repeating if the solver changes
# shape, and because the join between the impairment plan and the walk
# is real work that took two sessions. It lives with the experiment now,
# not in the hot path of every solve.
# ----------------------------------------------------------------------

from botc import impairment
from botc.solver import _before, phase_index
from botc.catalogue import CHARACTERS as _CHARS

# Whether a candidate story has to survive being *replayed* before it is
# scored.
#
# Off by default, deliberately. The night-walk reproduces every night of
# every simulated game and runs over the solver's own views, but the two
# have never been compared on the boards this solver actually sees — and
# a check that quietly discards a legal story is worse than no check.
#
# The plan is to run both against the corpus, compare, and only then
# decide which is authoritative. Until that is done this stays off and
# the old path is the one that ships.
WALK_CHECKS_STORIES = False

# How often the walk was asked, and how often it said no.
#
# A checker that never rejects anything is pure cost, and comparing two
# full solves to find out was far too slow to finish — eight mixed boards
# ran for seventeen minutes without answering. Counting inside the check
# is one pass and answers the question directly.
WALK_TALLY = {"asked": 0, "refused": 0}

# Measured before deciding, on the whole corpus:
#
#     switch off  46.1s
#     switch on   48.8s
#     cases that differ: 0 of 138
#
# So it agrees everywhere and costs six per cent. That is enough to land
# it but not enough to make it authoritative — agreeing on 138 stored
# boards says it does not *break* anything, not that it is right where
# the old path is wrong. Those boards were all built by the old path.
#
# What would earn the switch being on by default is a board where the two
# disagree and the walk is right. The mixed-script gate is where to look
# for one, since that is where the old path has been wrong nine times.




def _the_night_could_have_run(view, state):
    """Could each night of this story actually have played out?

    The seam the night-order design points at: three passes that cannot
    see each other, replaced by one walk that holds a single state and
    moves forward through it. The walk is the only thing here that can
    say a Goon took the Sailor's alignment rather than the Poisoner's, or
    that an Assassin lost its night to a starpass.

    Returns True when it cannot tell — a story is discarded only on a
    definite disagreement, because keeping a world that happened matters
    more than dropping one that did not.
    """
    WALK_TALLY["asked"] += 1
    board = AsBoard(view, state)
    latest = phase_index(state.final_phase())
    night = 0
    while True:
        night += 1
        phase = f"N{night}"
        if phase_index(phase) > latest:
            return True
        # Every way the sources could have been placed, not one.
        #
        # A story is impossible only when **every** arrangement fails.
        # Asking `plan_night` for a single assignment could never work:
        # it prices an arrangement rather than proposing one, and with
        # nothing required it places nobody.
        #
        # Cheap because most nights have exactly one arrangement — median
        # 1, mean 1.8 across a hundred and eighty nights — since the only
        # sources on most boards are free ones, which are not choices.
        # Search the night rather than check it.
        #
        # The Demon's aim cannot be handed in: it is what the deaths are
        # *evidence for*, so feeding them back would make the check
        # confirm whatever it was told. Enumerating it instead breaks the
        # circle — and the measurement says that is affordable, median
        # five walks a night at 78 microseconds against one `_explain` at
        # 156.
        died = {p for p in range(state.n_players)
                if phase in state.died_at(p)}
        if _a_night_fits(board, view, state, night, died):
            continue
        WALK_TALLY["refused"] += 1
        return False


# What the plan calls a source, and what the walk calls the choice it
# made. The names were never meant to line up — one is a cost model and
# the other is a replay — so the translation lives here rather than in
# either of them.


def _readings_that_must_be_droisoned(view, state, night):
    """Which seats a story *forces* to have been droisoned.

    **Returns nothing, deliberately.** Two attempts and the reasoning is
    worth more than either.

    The idea was to ask each weighed row whether it holds against the
    world being scored: a row that does not hold had to be invented, and
    inventing needs the speaker droisoned. That pins a source to a seat,
    which is the one thing the impairment plan can be asked for.

    It does not work, because **`holds` is not a question a row can
    answer alone**. A Fortune Teller needs the red herring; other rows
    need a Philosopher's gained ability, or which of two the Storyteller
    picked. The solver's scoring path supplies all of that as it goes.
    Asking with `None` in those places makes *true* readings look false,
    so their seats look forced, the plan cannot arrange it, and legal
    stories are thrown away — four true worlds in forty-five, which is
    exactly the failure a check like this must never have.

    Skipping the Fortune Teller left it at four, so more rows need
    context than were found. The shortcut is wrong in kind rather than in
    detail.
    """
    return set()


def _pukka_takes_its_turn(state, seat, slot, hidden, night):
    """The Pukka's turn, step by step as the flowchart has it.

      1  Exorcised: it does not choose.
      2  Otherwise it chooses, and that player is poisoned — unless the
         Pukka is itself drunk or poisoned, when nothing happens at all
         and the old token stays where it is.
      3  Somebody already carrying its poison is attacked, their own
         ability still poisoned, and the token comes off either way.

    It droisoned the seat that *died* and ignored the Exorcist for the
    death, which was the simulator's own reading before 02.10.2026.
    """
    if not state.working(seat):
        return
    if seat in state.silenced:
        state.log.append((slot, "exorcised", seat, "no choice"))
    else:
        fresh = hidden.get(("pukka_fresh", night))
        if fresh is not None:
            able = state.working(seat)
            state.choose(seat, fresh, slot)
            _goon_answers(state, seat, fresh, slot)
            if not able:
                return
            state.droison(fresh, slot, "Pukka")
    stale = hidden.get(("pukka_due", night))
    if stale is None or stale not in state.alive:
        return
    # A guard holds only while whoever gave it is still working, and the
    # Pukka has just poisoned somebody: an Innkeeper it chose tonight
    # protects nobody from the poison of the night before.
    keepers = [p for p, r in state.roles.items()
               if r in ("Innkeeper", "Monk") and p in state.alive]
    if stale in state.guarded and any(state.working(p) for p in keepers):
        state.log.append((slot, "guarded", stale, "Pukka"))
        state.prevented.add(seat)
        return
    state.kill(stale, slot, "Pukka")
    _grandmother_grieves(state, stale, slot, hidden, night)


_PLAN_TO_WALK = {"Poisoner": "poisoner", "Monk": "monk",
                 "Sailor": "sailor", "Innkeeper": "innkeeper",
                 "Exorcist": "exorcist", "SnakeCharmer": "snakecharmer",
                 "Witch": "witch"}


def _a_night_fits(board, view, state, night, died):
    """Is there any way this night could have produced that record?

    Every arrangement of the droison sources, crossed with everything the
    Demon could have aimed at — nobody, or any living seat, or any pair
    for a Shabaloth, or any three for a Po. A Pukka's kill is last
    night's poison, so its delayed victim is searched for too.

    True as soon as one combination reproduces the deaths, and true when
    the walk says it was under-informed: a story is refused only on a
    definite disagreement.
    """
    import itertools

    phase = f"N{night}"
    alive = sorted(state.alive_set(phase))
    demon = view.demon_at(phase)
    kind = view.role_at(demon, phase) if demon is not None else ""
    width = 3 if kind == "Po" else (2 if kind == "Shabaloth" else 1)

    aims = [[]]
    for size in range(1, width + 1):
        aims += [list(p) for p in itertools.combinations(alive, size)]
    dues = [None] + (alive if kind == "Pukka" else [])
    spread = impairment.arrangements(impairment.sources_on(view, state, night))

    for aim in aims:
        for due in dues:
            for _fixed, chosen in spread:
                told = _translate(chosen, night, state, view)
                told[("demon", night)] = aim
                if due is not None:
                    told[("pukka_due", night)] = due
                got = walk(board, night, told)
                if got.untold or got.died == died:
                    return True
    return False


def _translate(chosen, night, state, view_changes=None):
    """An arrangement, in the words the walk uses.

    The plan names sources and the walk names choices, and the two were
    never meant to line up — one is a cost model and the other a replay.
    Anything the walk does not know about is dropped rather than guessed
    at.
    """
    told = {}
    for name, pick in chosen.items():
        key = _PLAN_TO_WALK.get(name)
        if key is None:
            continue
        told[(key, night)] = pick

    # And everything the table *heard*, which is not a thing to search.
    #
    # A Gambler's guess, an Acrobat's pick, a Moonchild's target are all
    # on the record. Leaving them out cost the one night in a hundred and
    # twenty that could not be explained: a Gambler had guessed wrong and
    # died, and no arrangement of droisoning or Demon aim could produce
    # that death because the guess was never handed over.
    for info in state.infos:
        if info.night != night:
            continue
        source = getattr(info, "source_role", None)
        target = getattr(info, "target", None)
        if source == "Gambler" and isinstance(target, int):
            told[("gambler", night)] = (target, getattr(info, "role", None))
            continue
        key = _PLAN_TO_WALK.get(source)
        if key is not None and isinstance(target, int):
            told.setdefault((key, night), target)
        elif source == "Moonchild" and isinstance(target, int):
            told[("moonchild", night)] = target

    # A swapped Snake Charmer is poisoned for the rest of the game and
    # cannot swap again.
    #
    # The walk starts each night from the board as it stands, and a
    # charmer keeps pointing every night — so without this it re-did a
    # swap from an earlier night, put the pair back, and the seat holding
    # the Demon became a charmer again and killed nobody. `hidden_from`
    # has passed this since the tests needed it; the solver-side join did
    # not, which is what a shared builder would have prevented.
    standing = set()
    for at, seat, role, _side in getattr(view_changes, "changes", ()) or ():
        if role == "SnakeCharmer" and phase_index(at) < phase_index(
                f"N{night}"):
            standing.add(seat)
    if standing:
        told[("standing", night)] = standing
    return told


