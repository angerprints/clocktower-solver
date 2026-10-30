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
        self.sides_at_dusk = dict(sides)    # ... and as the night began
        self.alive = set(alive)
        self.droisoned = set()
        self.died = set()
        self.chosen_by = {}                 # seat -> who chose it first
        self.guarded = set()                # safe from the Demon tonight
        self.guards = {}                    # seat -> who is guarding it
        self.gained = {}                    # seat -> ability it took
        # The Boffin's (26.10.2026): the Demon's seat -> the good ability
        # it has tonight, and the Boffin whose sobriety it rests on.
        self.boffin = {}
        self.boffin_has = {}
        self.boffin_seat = None
        self.silenced = set()               # Demons that cannot kill
        self.spared = set()                 # safe from execution tomorrow
        self.fool_spent = set()             # Fools with no free death left
        self.safe = {}                      # seat -> the Innkeeper keeping it
        self.undead = None                  # a Zombuul under its shroud
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
        # Nightwatchman seat -> the player it woke, or None when it
        # pointed and nobody was woken because it had no ability.
        self.woken_by_nightwatchman = {}
        # Minions a Preacher chose tonight (10.10.2026): no ability, which
        # is not being drunk, so an Acrobat that picks one lives.
        self.preached = set()
        # The Lycanthrope killed tonight, so the Demon kills nobody
        # (11.10.2026), and the faux paw it cannot kill.
        self.lycanthrope_killed = False
        self.faux_paw = None
        self.made_drunk = {}                # Sailor/Innkeeper -> its drunk

    def choose(self, chooser, target, slot):
        """Somebody's ability aimed at somebody.

        Recorded so the Goon can ask who was **first**, which is the
        thing no set can answer.
        """
        self.chosen_by.setdefault(target, (slot, chooser))
        self.log.append((slot, "chose", chooser, target))

    def has(self, seat, role):
        """Holding that character, or a Philosopher that took it
        (13.10.2026), or a Demon the Boffin gave it (26.10.2026)."""
        return self.roles.get(seat) == role or (
            self.roles.get(seat) == "Philosopher"
            and self.gained.get(seat) == role) or (
            role in self.boffin_has.get(seat, ())
            and self.roles.get(seat) != "Philosopher")

    def sober_of(self, seat, role):
        """Whose sobriety this seat's ability as that character rests on:
        the Boffin's for a Demon it gave it, else its own."""
        if self.roles.get(seat) != role \
                and role in self.boffin_has.get(seat, ()) \
                and self.boffin_seat is not None:
            return self.boffin_seat
        return seat

    def works(self, seat, role):
        """Alive, and its ability as that character working — through the
        Boffin's sobriety for a Demon the Boffin gave it."""
        return seat in self.alive and self.working(self.sober_of(seat, role))

    def gift_ends(self, seat):
        """What the Boffin gave ends with the Demon's change of character,
        or the Boffin's own (C and I Weg 1, 27.10.2026)."""
        if seat in self.boffin or seat == self.boffin_seat:
            self.boffin.clear()
            self.boffin_has.clear()

    def lets_go(self, seat, slot):
        """This seat became somebody else in the middle of the night: what
        it did earlier tonight as its old character ends — a guard it set,
        a pair it kept safe, somebody it made drunk (Stelle 81, Patrick
        26.10.2026: "ein Mönch, der später geändert wird, beschützt
        niemanden mehr", and so for every character)."""
        for target, giver in list(self.guards.items()):
            if giver == seat:
                del self.guards[target]
                self.guarded.discard(target)
        for target, keeper in list(self.safe.items()):
            if keeper == seat:
                del self.safe[target]
        self.gift_ends(seat)
        target = self.made_drunk.pop(seat, None)
        if target is not None:
            self.droisoned.discard(target)
            self.log.append((slot, "sober", target, "changed"))
        # And one it chose tonight that was handed in as drunk from the
        # start but sober by the end: a Sailor's or an Innkeeper's drunk
        # the record keeps for the whole night (`hidden_from`).
        for entry in self.log:
            if len(entry) >= 4 and entry[1] == "chose" and entry[2] == seat \
                    and entry[3] in getattr(self, "lifted", ()) \
                    and entry[3] in self.droisoned:
                self.droisoned.discard(entry[3])
                self.log.append((slot, "sober", entry[3], "changed"))

    def droison(self, seat, slot, why, by=None):
        # A Sailor or an Innkeeper droisoned after making somebody drunk
        # tonight: that drunkenness ends with it. The simulator has it so,
        # and a Lleech the Sailor had drunked, whose Sailor the Poisoner
        # then took, died with its host there and lived here (11.10.2026).
        for source, target in list(self.made_drunk.items()):
            if source == seat:
                del self.made_drunk[source]
                self.droisoned.discard(target)
                self.log.append((slot, "sober", target, why))
        if why in ("Sailor", "Innkeeper") and seat not in self.droisoned:
            # Whoever made them drunk: told, or the one holding it.
            source = by if by is not None else next(
                (p for p, r in self.roles.items()
                 if r == why and p in self.alive), None)
            if source is not None:
                self.made_drunk[source] = seat
        self.droisoned.add(seat)
        self.log.append((slot, "droisoned", seat, why))

    def kill(self, seat, slot, why, unstoppable=False):
        """Somebody dies — unless a Tea Lady is keeping them alive.

        **Both her living neighbours good means neither can die.** Full
        stop, whatever the death comes from: a Demon, a Gambler's wrong
        guess, an Acrobat's droisoned pick, a Tinker simply going.

        Asked here rather than at each cause, because there are six ways
        to die in this walk and every one of them has to ask. The
        simulator learned that the same way — a Tinker died beside a
        working Tea Lady and no world could explain it.
        """
        if unstoppable:
            self.died.add(seat)
            self.alive.discard(seat)
            self.log.append((slot, "died", seat, why))
            return
        if self._a_tea_lady_holds(seat):
            self.prevented.add(seat)
            self.log.append((slot, "kept alive", seat, "Tea Lady"))
            return
        # The other two that keep somebody alive whatever the death is: a
        # sober Sailor cannot die, and neither can the pair a working
        # Innkeeper chose tonight. Only the Demon's kill asked about the
        # Innkeeper, and nothing asked about the Sailor — so a Gambler
        # the Innkeeper had just protected guessed wrong and died here,
        # where the simulator had it live (03.10.2026; one in a hundred
        # and sixty nights disagreed for this alone).
        if self.has(seat, "Sailor") and self.works(seat, "Sailor"):
            self.prevented.add(seat)
            self.log.append((slot, "kept alive", seat, "Sailor"))
            return
        keeper = self.safe.get(seat)
        if keeper is not None and self.working(keeper):
            self.prevented.add(seat)
            self.log.append((slot, "kept alive", seat, "Innkeeper"))
            return
        # A Fool's first death does not happen. Last, so a guard that
        # held earlier has not used it up — and once, so the walk is told
        # which Fools had already spent theirs before tonight.
        if self.has(seat, "Fool") and seat not in self.fool_spent \
                and self.works(seat, "Fool"):
            self.fool_spent.add(seat)
            self.prevented.add(seat)
            self.log.append((slot, "kept alive", seat, "Fool"))
            return
        self.died.add(seat)
        self.alive.discard(seat)
        self.log.append((slot, "died", seat, why))

    def _a_tea_lady_holds(self, seat):
        # Deaths that land together are asked about the table as it stood
        # before any of them: an Al-Hadikhia's three (21.10.2026).
        standing = getattr(self, "at_once", None) or self.alive
        for lady in self.roles:
            if not self.has(lady, "TeaLady") or lady not in standing:
                continue
            if self.sober_of(lady, "TeaLady") in self.droisoned:
                continue
            around = []
            for step in (1, -1):
                for gap in range(1, len(self.roles)):
                    other = (lady + step * gap) % len(self.roles)
                    if other == lady:
                        break
                    if other in standing:
                        around.append(other)
                        break
            if seat in around and len(around) >= 2 \
                    and all(self.sides.get(p) == "good" for p in around):
                return True
        return False

    def working(self, seat):
        # A Demon acting at the turn of the ability the Boffin gave it
        # works by the Boffin's sobriety, not its own (26.10.2026).
        if getattr(self, "gift_turn", None) == seat \
                and self.boffin_seat is not None:
            return seat in self.alive and self.boffin_seat in self.alive \
                and self.boffin_seat not in self.droisoned
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

    def demons_at(self, phase):
        return self.world.demons_at(phase)


def _droisoned_as_the_night_began(deal, night):
    """`droisoned_at`, asked of the board before tonight had happened.

    Tonight's changes of character and tonight's deaths are put aside
    for the asking, and with them the poison on a Demon a Snake Charmer
    swapped with tonight — recorded apart from the change that caused it.
    """
    import simulate
    phase = f"N{night}"
    changes, deaths = deal.changes, deal.deaths
    poisoned = getattr(deal, "perma_poisoned", set())
    # Except a tea party's (22.10.2026): that is the very start of the
    # night, before anybody acts.
    tea = getattr(deal, "tea_made", None) or {}
    # And the Storyteller's jinxes (Pestdoktor Stufe 2), as it began.
    jinx = set(getattr(deal, "st_jinx", {}).get(night, ()))
    deal.changes = [c for c in changes if c[0] != phase
                    or tea.get((c[1], night)) == c[2]
                    or (c[1], c[2]) in jinx]
    deal.deaths = {p: at for p, at in deaths.items() if at != phase}
    deal.perma_poisoned = {
        p for p in poisoned
        if any(seat == p and role == "SnakeCharmer"
               for _at, seat, role in deal.changes)}
    fresh = deal.pukka_marks.pop(night, None)
    try:
        return set(simulate.droisoned_at(deal, night))
    finally:
        deal.changes, deal.deaths = changes, deaths
        deal.perma_poisoned = poisoned
        if fresh is not None:
            deal.pukka_marks[night] = fresh


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
    # A Widow's pick tonight, on its first night, is the walk's to place
    # at its slot. On every later night it is standing, and handed over.
    widow_tonight = [(w, t) for w, t, since
                     in getattr(deal, "widow_poison", ()) if since == night]
    derives |= {t for _w, t in widow_tonight}
    # The same for a Preacher's Minion tonight: it acts at 14, then 6.
    preached_tonight = {t for _p, t, since in getattr(deal, "preached", ())
                        if since == night}
    derives |= preached_tonight
    # The Pukka's fresh poison is the walk's own to place, at its slot —
    # so it is asked for with that token lifted, rather than subtracted
    # afterwards: a Gambler the Courtier had already made drunk was
    # poisoned by the Pukka on top, and subtracting the seat handed the
    # walk a sober Gambler. The token still standing from last night is
    # different. It was on the board when the night began.
    #
    # And the same for whoever the Goon made drunk tonight: the walk
    # works that out for itself, at the slot it happened.
    #
    # But *only* that seat is lifted, and only if the Goon is the one
    # reason for it. Asking with the Goon's doing left out altogether
    # brought back everything it had prevented: an Innkeeper the Goon
    # made drunk makes nobody else drunk, and without the Goon in the
    # picture its pick was handed over as drunk when the night began.
    fresh = deal.pukka_marks.pop(night, None)
    try:
        standing = set(simulate.droisoned_at(deal, night)) - derives
        gooned = getattr(deal, "goon_first", {}).pop(night, None)
        if gooned is not None:
            try:
                if gooned[0] not in simulate.droisoned_at(deal, night):
                    standing.discard(gooned[0])
            finally:
                deal.goon_first[night] = gooned
    finally:
        if fresh is not None:
            deal.pukka_marks[night] = fresh
    # Whoever the Pukka's poison came due for was still poisoned as the
    # night began, whether or not they lived to see the morning.
    came_due = deal.pukka_history.get(night)
    token_only = False
    if came_due and came_due[0] is not None:
        # Poisoned by that token and nothing else? Then they are healthy
        # again from the Pukka's turn, if they are still about — "dead or
        # not, that token comes off". A dead Moonchild's pick at 50 lands.
        token_only = came_due[0] not in standing
        standing.add(came_due[0])
    out = {}
    # ...and "when the night began" has to mean that. `droisoned_at`
    # answers for the board as the night *ended*: a Sweetheart the Demon
    # killed tonight has already made somebody drunk, a Barber's swap at
    # 40 has already moved the No Dashii and its poison with it. Handed
    # over as standing, that reached back to slot 29 — the Demon that
    # killed the Sweetheart was drunk before it killed her, and the walk
    # had nobody die on a night the record shows a body.
    #
    # Sixty nights in 16,641 of Sects & Violets, and every one of them
    # this or the Philosopher below (05.10.2026). Third time a set that
    # means "by the end" has been given as the answer to an earlier
    # moment. So the walk is told three things: who was droisoned as the
    # night began, who became so in the course of it, and who stopped.
    began = _droisoned_as_the_night_began(deal, night) - derives
    ended = set(simulate.droisoned_at(deal, night)) - derives
    later, lifted = ended - began, began - ended
    standing = (standing - later) | lifted
    # Whoever the Pukka's token came due for carried it as the night
    # began, whatever the board looked like with tonight's changes put
    # aside: a Snake Charmer that swapped into the Pukka tonight leaves no
    # living Pukka in that picture, and the token went "later" — after the
    # Demon's turn, where a Princess's day then held (10.10.2026).
    if came_due and came_due[0] is not None:
        standing.add(came_due[0])
        later.discard(came_due[0])
    if standing:
        out[("standing", night)] = standing
    if later:
        out[("standing_later", night)] = later
    if lifted:
        out[("standing_lifted", night)] = lifted
    # A Philosopher back from the dead is a new one that has not chosen:
    # from the night it returned it has nothing (Stelle 69, Weg 1). Dead
    # until then that night, it had nothing to use before either.
    from botc.info import phase_index as _pi
    lost = getattr(deal, "phil_lost", None) or {}
    out.update({"red_herring": deal.red_herring,
                "gained": {seat: took for seat, took in (
                    getattr(deal, "philosophies", {}) or {}).items()
                    if seat not in lost
                    or _pi(phase) < _pi(lost[seat])}})
    # The Boffin's gift, as the simulator has it tonight (26.10.2026).
    gift = getattr(deal, "boffin_gift", None)
    if gift is not None:
        got = simulate._gift(deal, gift[0], phase)
        boffin = simulate._boffin_at(deal, phase)
        # Changed later tonight — a Barber's swap, a Snake Charmer's — the
        # Demon still had it until then: the simulator played its turn
        # before the change was written (seeds 1794 and 2919 of the gate,
        # 27.10.2026). The walk ends it at the change (`lets_go`).
        if got is None and night > 1:
            before = f"D{night - 1}"
            boffin = simulate._boffin_at(deal, before)
            if boffin is not None and boffin in deal.alive_at(phase):
                got = simulate._gift(deal, gift[0], before)
        if got is not None:
            out[("boffin", night)] = {gift[0]: got}
            out[("boffin_seat", night)] = boffin
    if token_only:
        out[("pukka_token_only", night)] = True

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
    # Each holder's own choice, where the simulator kept them apart: the
    # real holder and a Philosopher that took it (13.10.2026).
    for role, key in (("Monk", "monk"), ("Innkeeper", "innkeeper"),
                      ("InnkeeperDrunk", "innkeeper_drunk"),
                      ("SailorDrunk", "sailor_drunk"),
                      ("Exorcist", "exorcist")):
        got = getattr(deal, "chose_by", {}).get((role, night))
        if got:
            out[(key + "s", night)] = dict(got)
    if deal.innkeeper_guarded.get(night):
        out[("innkeeper", night)] = deal.innkeeper_guarded[night]
    if deal.innkeeper_drunk.get(night) is not None:
        out[("innkeeper_drunk", night)] = deal.innkeeper_drunk[night]
    if deal.sailor_drunk.get(night) is not None:
        out[("sailor_drunk", night)] = deal.sailor_drunk[night]
    if deal.cursed.get(night) is not None:
        out[("witch", night)] = deal.cursed[night]
    if getattr(deal, "fear_chose", {}).get(night) is not None:
        out[("fearmonger", night)] = deal.fear_chose[night]
    if widow_tonight:
        out[("widow", night)] = dict(widow_tonight)
    # Whom each Preacher chose, and the Minions only a sermon silences —
    # those an Acrobat may pick and live (10.10.2026).
    sermons = {r.player: r.target for r in heard
               if type(r).__name__ == "PreacherChoice" and r.night == night}
    if sermons:
        out[("preacher", night)] = sermons
    only = simulate._preached(deal, night) \
        - simulate._droisoned_without_preaching(deal, night)
    if only:
        out[("preached_only", night)] = only
    hunted = {r.player: r.target for r in heard
              if type(r).__name__ == "HuntsmanChoice" and r.night == night}
    if hunted:
        out[("huntsman", night)] = hunted
        made = getattr(deal, "huntsman_chose", {}).get(night)
        if made is not None:
            out[("huntsman_made", night)] = made[2]
    # The seventh five (11.10.2026): whom the Lycanthrope chose and who is
    # its faux paw; whom the Harpy made mad, for a Goon; each Lleech's
    # host, and whether that host was already dead as the night began.
    aimed = getattr(deal, "lyc_aimed", {}).get(night)
    if aimed is not None:
        # Each its own: the holder and a Philosopher that took it.
        out[("lycanthrope", night)] = dict(
            getattr(deal, "chose_by", {}).get(("Lycanthrope", night))
            or {aimed[0]: aimed[1]})
    if getattr(deal, "faux_paw", None) is not None:
        out["faux_paw"] = deal.faux_paw
    mad = getattr(deal, "harpy_chose", {}).get(night)
    if mad is not None:
        out[("harpy", night)] = {mad[0]: mad[1]}
    hosts = getattr(deal, "lleech_hosts", {})
    if hosts:
        out[("lleech", night)] = {
            # Raised tonight counts as dead as the night began: a host a
            # Professor stands up at 43 does not save a Lleech that went
            # with it at dusk (11.10.2026).
            seat: (host, host not in deal.alive_at(phase)
                   or deal.back_at(host, phase) is not None)
            for seat, host in hosts.items()}
        from botc.info import phase_index as _at
        lost = getattr(deal, "lleech_lost", None)
        if lost is not None and _at(lost) <= _at(phase):
            out[("lleech_lost", night)] = True
    # The eighth five (11.10.2026): who said the Mezepheles's word
    # yesterday, and whom a Leviathan pointed at by its jinxes. A
    # Yaggababble's kills are the Demon's aims above.
    marked = getattr(deal, "mez_marked", None)
    if marked is not None and marked[1] == night - 1:
        out[("mezepheles", night)] = marked[0]
    pick = getattr(deal, "lev_aimed", {}).get(night)
    if pick is not None:
        out[("leviathan", night)] = pick
    # A Princess whose nominee was executed yesterday, by seat: the walk
    # asks whether she has her ability at the Demon's turn.
    princess = getattr(deal, "princess_stop", {}).get(night)
    if princess is not None:
        out[("princess", night)] = princess
    # The three that kill besides the Demon, and a Lunatic's pointing.
    for key, where in (("assassin", "assassin_aimed"),
                       ("godfather", "godfather_aimed"),
                       ("gossip", "gossip_killed"),
                       ("lunatic", "lunatic_chose")):
        got = getattr(deal, where, {}).get(night)
        if got is not None:
            out[(key, night)] = got
    # What the Storyteller killed with an ability the Plague Doctor's death
    # gave it (28.10.2026): {ability: whom}, at that ability's turn.
    st_kills = getattr(deal, "st_kills", {}).get(night)
    if st_kills:
        out[("st_kills", night)] = dict(st_kills)
    # Whom its jinxes made something as tonight began (stage 2).
    jinx = getattr(deal, "st_jinx", {}).get(night)
    if jinx:
        out[("st_jinx", night)] = list(jinx)
    # Whom its Pit-Hag made what tonight (stage 2, A).
    st_made = getattr(deal, "st_made", {}).get(night)
    if st_made is not None:
        out[("st_pithag", night)] = st_made
    # A Devil's Advocate's pick, hidden like the Monk's guard.
    spared = getattr(deal, "spared", {}).get(night)
    if spared is not None:
        out[("devilsadvocate", night)] = spared[1]
    # Who came back tonight, and by whose hand: they were dead when the
    # night began, and the walk has to stand them up at the right slot.
    # Whom a Nightwatchman pointed at, by seat. Announced, but by the
    # Nightwatchman's own row rather than one row a night, so it is read
    # off the game.
    aimed = (getattr(deal, "nightwatchman_aimed", None) or {}).get(night)
    if aimed:
        out[("nightwatchman", night)] = dict(aimed)
    back = getattr(deal, "regurgitated", {}).get(night)
    if back is not None:
        out[("regurgitated", night)] = back
    back = getattr(deal, "professor_raised", {}).get(night)
    if back is not None:
        out[("professor", night)] = back
    # Dead players the Al-Hadikhia chose who chose life (21.10.2026):
    # back at its slot, after every early chooser.
    raised = {seat for seat, at, by in getattr(deal, "resurrections", ())
              if by == "AlHadikhia" and at == f"N{night}"}
    if raised:
        out[("ah_raised", night)] = raised
        # Those dead before tonight were not there when it began; one
        # killed earlier tonight and chosen afterwards was.
        out[("ah_raised_from_before", night)] = raised & set(
            getattr(deal, "ah_from_before", {}).get(night, ()))
    # Whom it chose and what each answered, in turn: as hidden as any
    # Demon's aim. The walk works out what they did.
    picks = getattr(deal, "ah_chose", {}).get(night)
    if picks:
        out[("ah_picks", night)] = list(picks)
        out[("ah_answers", night)] = list(
            getattr(deal, "ah_answers", {}).get(night, ()))
    # Lil' Monsta (21.10.2026): who babysat it as the night began — the
    # one a Snake Charmer at 11 or an Exorcist at 21 can name — whom the
    # Minions chose tonight, and whom it went for. On the first night the
    # choice at 15 comes before the Snake Charmer at 20.
    if getattr(deal, "lil_monsta", False):
        before = deal.demon_at(f"E{night - 1}") if night > 1 \
            else deal.babysat.get(1)
        out[("lm", night)] = {
            "before": before,
            "tonight": deal.demon_at(f"N{night}"),
            "aimed": getattr(deal, "lm_aimed", {}).get(night),
            # Standing as the night began — asked of the record, not of
            # the end of the game.
            "alive": night > 1 and before is not None
            and before in deal.alive_at(f"N{night}")}
    # The Summoner's Demon (21.10.2026): whom it made which, and who
    # beside a Lord of Typhon was made a Minion.
    # The Hatter's tea party (22.10.2026): who chose what tonight.
    tea = {seat: role for (seat, at), role
           in (getattr(deal, "tea_made", None) or {}).items() if at == night}
    if tea:
        out[("tea", night)] = tea
        slot = (getattr(deal, "tea_slot", None) or {}).get(night)
        if slot is not None:
            out[("tea_slot", night)] = slot
    # Or the one a Summoner chosen at a tea party made beside the Demon
    # (Hatter stage 2, 25.10.2026), whose kill is its own.
    made = getattr(deal, "summoned", None) \
        or getattr(deal, "tea_summoned", None)
    # The seat that acted as it tonight — a Scarlet Woman that took over
    # later in the night is not it.
    second = (getattr(deal, "demon2_seat", None) or {}).get(night)
    if second is not None:
        out[("second_demon", night)] = second
        aim = (getattr(deal, "demon_aimed2", None) or {}).get(night)
        if aim is not None:
            out[("demon2", night)] = aim
    if made is not None and made[0] == night:
        out[("summoned", night)] = (made[1], made[2],
                                    tuple(getattr(deal, "summoned_extra",
                                                  ())))
    if getattr(deal, "zombuul_up", None) is not None:
        out[("zombuul_up", night)] = deal.zombuul_up
    # Fools whose one free death was gone before tonight.
    from botc.info import phase_index
    # Read off the whole history, not the Fool's state at the end of the
    # game: one that came back has its free death again, and the record
    # of having spent the first is gone from it by then.
    now = phase_index(phase)
    out[("fool_spent", night)] = {
        seat for seat, at in getattr(deal, "fool_spent_ever", ())
        if phase_index(at) < now and not any(
            who == seat and phase_index(at) < phase_index(back) <= now
            for who, back, _by in getattr(deal, "resurrections", ()))}

    # Choices the table *hears*, read straight off the rows. These were
    # missing and the walk's own warning found them — a Sailor, a Snake
    # Charmer and an Exorcist all announce what they did, the row sits in
    # `heard`, and nothing was reading it.
    # Whether this night's Snake Charmer row was the one that swapped.
    charm = row("SnakeCharmerChoice")
    if charm:
        out[("snakecharmer_swapped", night)] = bool(charm[0].swapped)
        # By seat as well, because a table can hold two: the real one and
        # a Philosopher that took its ability. One key could only name
        # one of them, and the walk gave both the same target.
        out[("snakecharmers", night)] = {c.player: c.target for c in charm}

    sailors = row("SailorChoice")
    if sailors:
        out[("sailors", night)] = {r.player: r.target for r in sailors}
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
        # Each its own, as with the Snake Charmers above: a Philosopher
        # that took the Gambler guesses beside the real one, and the
        # walk gave both the first row's guess (07.10.2026).
        out[("gamblers", night)] = {g.player: (g.target, g.role)
                                    for g in guess}
    moon = row("MoonchildChoice")
    if moon:
        out[("moonchild", night)] = moon[0].target
        out[("moonchilds", night)] = {m.player: m.target for m in moon}
    acro = row("AcrobatChoice")
    if acro:
        out[("acrobats", night)] = {a.player: a.target for a in acro}
    # The grandchild a Grandmother has tonight: her latest reading from
    # before tonight, and none at all on the night she comes back — one
    # who died and returned is a new Grandmother (03.10.2026).
    # And a Philosopher that took her has one of its own (group 6).
    took = getattr(deal, "philosophies", {}) or {}
    for seat in range(deal.n):
        if deal.role_at(seat, phase) != "Grandmother" \
                and not (deal.role_at(seat, phase) == "Philosopher"
                         and took.get(seat) == "Grandmother"):
            continue
        if getattr(deal, "back_at", lambda *_: None)(seat, phase) is not None:
            continue
        mine = [h for h in heard
                if type(h).__name__ == "GrandmotherInfo"
                and h.player == seat and (h.night < night or night == 1)]
        if mine:
            out["grandchild"] = mine[-1].target
            out.setdefault("grandchildren", {})[seat] = mine[-1].target
    # Which Tinkers went: the holder, or a Philosopher that took it.
    took = getattr(deal, "philosophies", {}) or {}
    went = {p for p in range(deal.n) if p in deal.died_on(phase)
            and (deal.role_at(p, phase) == "Tinker"
                 or (deal.role_at(p, phase) == "Philosopher"
                     and took.get(p) == "Tinker"))}
    if went:
        out[("tinker", night)] = went

    executed = sorted(deal.died_on(f"E{night - 1}"))
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
    "Fearmonger": "fearmonger", "Preacher": "preacher",
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
        if state.roles.get(seat) != role:
            continue                      # made something else tonight
        if seat in (hidden.get(("regurgitated", night)),
                    hidden.get(("professor", night))) \
                or seat in (hidden.get(("ah_raised_from_before", night))
                            or ()):
            continue                      # back tonight, after its turn
        # With one other player left there is nobody to choose: an
        # Innkeeper needs two, an Exorcist somebody it did not name last
        # night, a Sailor somebody at all.
        if role in ("Innkeeper", "Exorcist", "Sailor") \
                and len(state.alive | state.died) < 3:
            continue
        # "If just 3 players live, you lose this ability."
        if role == "Witch" and len(state.alive | state.died) <= 3:
            continue
        if hidden.get((key, night)) is None:
            state.untold.add(role)


# Characters a Philosopher may take that *act* in the night, beyond the
# three the walk knew first (Snake Charmer, Nightwatchman, Gambler). Grown
# group by group (open item 56, step 2, 13.10.2026).
TAKEN_ACTS = ("Sailor", "Innkeeper", "Monk", "Exorcist",
              # Group 2: the ones that kill (13.10.2026).
              "Tinker", "Acrobat", "Gossip", "Moonchild", "Lycanthrope",
              # Group 3: the ones that disturb (13.10.2026).
              "Preacher",
              # Group 4: character and side (13.10.2026).
              "Huntsman", "Professor")


def _by_seat(hidden, key, night, seat):
    """What this seat chose, where the walk is told each holder's choice
    on its own (`key + "s"`): the real holder and a Philosopher that took
    the character both choose (13.10.2026). Otherwise the one choice."""
    by = hidden.get((key + "s", night))
    if by is not None:
        return by.get(seat)
    return hidden.get((key, night))


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
    # Whom the Storyteller's jinxes made something as the night began
    # (Pestdoktor Stufe 2): before anybody acts.
    for seat, role in hidden.get(("st_jinx", night)) or ():
        roles[seat] = role
    sides = {seat: deal.side_at(seat, was) for seat in range(deal.n)}
    # Alive when the night began. `alive_at` counts somebody who comes
    # back tonight as alive tonight, which is right for the night as a
    # whole and wrong for its first half: a regurgitated Innkeeper was
    # dead at slot 9 and guarded nobody.
    back_tonight = {hidden.get(("regurgitated", night)),
                    hidden.get(("professor", night))} - {None}
    back_tonight |= set(hidden.get(("ah_raised_from_before", night)) or ())
    state = Night(roles, sides, set(deal.alive_at(phase)) - back_tonight)
    state.fool_spent = set(hidden.get(("fool_spent", night)) or ())
    state.undead = hidden.get(("zombuul_up", night))
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
    # And what the Boffin gave the Demon, tonight (26.10.2026).
    # A Philosopher's ability given (stage 2): it has both, and acts as
    # what it took at that character's turn.
    from botc.info import boffin_abilities
    given = dict(hidden.get(("boffin", night)) or {})
    state.boffin_has = {seat: set(boffin_abilities(got, f"N{night}"))
                        for seat, got in given.items()}
    state.boffin = {seat: boffin_abilities(got, f"N{night}")[-1]
                    for seat, got in given.items()
                    if boffin_abilities(got, f"N{night}")}
    state.boffin_seat = hidden.get(("boffin_seat", night))

    state.night = night
    state.faux_paw = hidden.get("faux_paw")
    state.executed_yesterday = hidden.get(("executed", night))
    state.asked = dict(hidden.get(("asked", night)) or {})
    state.woke_count = dict(hidden.get(("woke", night)) or {})
    state.red_herring = hidden.get("red_herring")
    state.demon_voted = hidden.get(("demon_voted", night))
    state.minion_nominated = hidden.get(("minion_nominated", night))

    field = "first_night" if night == 1 else "other_night"
    # What became droisoned in the course of tonight, and what stopped
    # being so, by causes the walk is told rather than works out: a
    # Sweetheart dying, a Barber's swap moving a No Dashii. The last of
    # those acts at the Sweetheart's slot, and everybody who reads acts
    # after it — so that is where the board is brought up to date.
    becomes_droisoned = set(hidden.get(("standing_later", night)) or ())
    stops_being_droisoned = set(hidden.get(("standing_lifted", night)) or ())
    state.lifted = stops_being_droisoned
    last_cause = getattr(CHARACTERS["Sweetheart"], field, 0)
    charmer_slot = getattr(CHARACTERS["SnakeCharmer"], field, 0)
    # The same for a Philosopher that took the Nightwatchman: it points
    # when the Nightwatchman would.
    watch_slot = getattr(CHARACTERS["Nightwatchman"], field, 0)
    # And one that took the Gambler guesses when the Gambler would — and
    # dies of a wrong guess, where the real one beside it is drunk and
    # dies of nothing (07.10.2026).
    gamble_slot = getattr(CHARACTERS["Gambler"], field, 0)
    # And every other character a Philosopher may take that *acts*: it
    # does what they do, at their place in the night (open item 56, step
    # 2, 13.10.2026). Readings it took are asked further down.
    taken_slot = {g: getattr(CHARACTERS[g], field, 0) for g in TAKEN_ACTS}
    settled = False
    lm = hidden.get(("lm", night))
    lm_slot = getattr(CHARACTERS["LilMonsta"], field, 0)
    state.lm_sitter = lm["before"] if lm else None
    state.lm_silenced = False
    summon = hidden.get(("summoned", night))
    summon_slot = getattr(CHARACTERS["Summoner"], field, 0)
    tea = hidden.get(("tea", night))
    # At the very start after a death by day; straight after the death
    # after one at night, at the slot the simulator wrote down (C; Hatter
    # stage 3c, 23.10.2026).
    tea_slot = hidden.get(("tea_slot", night)) \
        or getattr(CHARACTERS["Hatter"], field, 0)
    acrobats = []
    acrobats_fall = getattr(CHARACTERS["Gossip"], field, 0)
    st_kills = dict(hidden.get(("st_kills", night)) or {})

    def _acrobat_falls_now(slot):
        only = hidden.get(("preached_only", night)) or set()
        for seat, target in acrobats:
            # Still working by then: an Acrobat poisoned after its pick
            # (a Pukka's choice) has no ability left to fell it.
            if seat in state.alive and state.working(seat) \
                    and target in state.droisoned and target not in only:
                state.kill(seat, slot, "Acrobat")
        acrobats.clear()

    for slot in _turns(night):
        state.gift_turn = None       # a Demon's Boffin turn ends with it
        if acrobats and slot > acrobats_fall:
            _acrobat_falls_now(slot)
        # The Hatter's tea party at 1, before anybody acts (C, 22.10.2026):
        # each holds its new character from here, on its own side.
        if tea and slot >= tea_slot:
            for seat, role in tea.items():
                # A Marionette that chose a new character is no longer
                # handed the wrong token (P Weg 2): it works from here.
                if state.roles[seat] == "Marionette":
                    state.droisoned.discard(seat)
                state.lets_go(seat, slot)
                state.roles[seat] = role
            n = len(state.roles)
            for seat, role in tea.items():
                # A poisoning that held its old character only is lifted.
                if seat in stops_being_droisoned:
                    state.droisoned.discard(seat)
                # A Lleech chooses its host as it is made, poisoned from
                # here on; a No Dashii poisons its Townsfolk neighbours
                # (as for the Summoner's).
                if role == "Lleech":
                    host = (hidden.get(("lleech", night)) or {}).get(
                        seat, (None,))[0]
                    if host in becomes_droisoned:
                        state.droison(host, slot, "Lleech")
                        becomes_droisoned.discard(host)
                # A Widow made at the party looks and poisons at once (O
                # Weg 1), as the simulator has it: before anybody acts.
                if role == "Widow":
                    target = (hidden.get(("widow", night)) or {}).get(seat)
                    if target is not None:
                        state.droison(target, slot, "Widow")
                if role == "NoDashii":
                    near = set()
                    for step in (-1, 1):
                        for k in range(1, n):
                            p = (seat + step * k) % n
                            if CHARACTERS[state.roles[p]].team == "townsfolk":
                                near.add(p)
                                break
                    state.droisoned |= {p for p in becomes_droisoned
                                        if p in near}
            tea = None
        # The Summoner at 19 (21.10.2026): the player it chose holds the
        # Demon it chose from here on, and is evil.
        if summon and slot == summon_slot:
            seat, demon, extra = summon
            state.lets_go(seat, slot)
            state.roles[seat] = demon
            state.sides[seat] = "evil"
            for other, role in extra:
                state.lets_go(other, slot)
                state.roles[other] = role
                state.sides[other] = "evil"
            # A poisoning that held its old character only — a Xaan's
            # night, which poisons Townsfolk — is lifted from here.
            if seat in stops_being_droisoned:
                state.droisoned.discard(seat)
            # A Lleech chooses its host as it is made, poisoned from here
            # on (as the simulator has it).
            if demon == "Lleech":
                host = (hidden.get(("lleech", night)) or {}).get(
                    seat, (None,))[0]
                if host in becomes_droisoned:
                    state.droison(host, slot, "Lleech")
                    becomes_droisoned.discard(host)
            # A No Dashii poisons its Townsfolk neighbours from now on.
            if demon == "NoDashii":
                n = len(state.roles)
                near = set()
                for step in (-1, 1):
                    for k in range(1, n):
                        p = (seat + step * k) % n
                        if CHARACTERS[state.roles[p]].team == "townsfolk":
                            near.add(p)
                            break
                state.droisoned |= {p for p in becomes_droisoned
                                    if p in near}
            # A Philosopher made the Demon gives up what it took, and the
            # one it made drunk for it is sober again.
            taken = state.gained.pop(seat, None)
            if taken is not None:
                for p, held in state.roles.items():
                    if held == taken and p in stops_being_droisoned:
                        state.droisoned.discard(p)
            # A guard it set earlier tonight as a Monk or an Innkeeper
            # went with the character that set it (`lets_go`, above).
            summon = None
        # The Storyteller's Pit-Hag (Pestdoktor Stufe 2, A): at the
        # Pit-Hag's turn, nobody's ability to stop.
        st_made = hidden.get(("st_pithag", night))
        if st_made is not None \
                and slot == getattr(CHARACTERS["PitHag"], field, 0):
            target, became = st_made
            was = state.roles.get(target)
            state.lets_go(target, slot)
            state.roles[target] = became   # the side does not move
            state.log.append((slot, "made", target, became))
            if became == "Goon":
                state.chosen_by.pop(target, None)
            if was == "Drunk" and target in stops_being_droisoned:
                state.droisoned.discard(target)
                stops_being_droisoned.discard(target)
        # The Storyteller's Assassin and Godfather, the Plague Doctor's
        # gift (28.10.2026): at their turn, nobody's ability to stop.
        for key, target in st_kills.items():
            if slot == getattr(CHARACTERS[key], field, 0) \
                    and target in state.alive:
                state.kill(target, slot, key, unstoppable=key == "Assassin")
        # Lil' Monsta at 35: the Minions choose, then a player might die
        # — never the babysitter, nobody an Exorcist that named last
        # night's babysitter left awake for (21.10.2026).
        if lm and slot == lm_slot:
            _lil_monsta_takes_its_turn(state, lm, slot, hidden, night)
            continue
        # Who holds a character with this slot **now**.
        #
        # Asked afresh at every slot, because a swap moves characters
        # between seats mid-night and the answer changes as the walk
        # goes. A seat may act twice if two characters pass through it,
        # which is correct: the Storyteller wakes whoever holds the
        # token when that token's turn comes.
        if not settled and slot > last_cause:
            settled = True
            state.droisoned |= becomes_droisoned
            state.droisoned -= stops_being_droisoned
        here = [p for p in sorted(state.roles)
                if getattr(CHARACTERS.get(state.roles[p]), field, 0) == slot
                or (state.roles[p] == "Philosopher" and slot == charmer_slot
                    and state.gained.get(p) == "SnakeCharmer")
                or (state.roles[p] == "Philosopher" and slot == watch_slot
                    and state.gained.get(p) == "Nightwatchman")
                or (state.roles[p] == "Philosopher" and gamble_slot
                    and slot == gamble_slot
                    and state.gained.get(p) == "Gambler")
                or (state.roles[p] == "Philosopher"
                    and state.gained.get(p) in taken_slot
                    and taken_slot[state.gained[p]]
                    and slot == taken_slot[state.gained[p]])
                # A Demon the Boffin gave one of these acts at its turn
                # (26.10.2026).
                or (state.boffin.get(p) in taken_slot
                    and taken_slot[state.boffin[p]]
                    and slot == taken_slot[state.boffin[p]])]
        for seat in here:
            role = state.roles[seat]
            state.gift_turn = None
            if state.boffin.get(seat) in taken_slot \
                    and slot == taken_slot.get(state.boffin.get(seat)) \
                    and getattr(CHARACTERS.get(role), field, 0) != slot:
                role = state.boffin[seat]
                state.gift_turn = seat
            # A Philosopher that took the Snake Charmer's ability on an
            # earlier night chooses when the Snake Charmer does. It only
            # ever *read* with what it had taken, so its swap never
            # happened here: the Demon stayed where it was, and a Fang Gu
            # that should have jumped from the Philosopher's seat jumped
            # from its own (05.10.2026).
            if role == "Philosopher" and slot == charmer_slot \
                    and state.gained.get(seat) == "SnakeCharmer":
                role = "SnakeCharmer"
            if role == "Philosopher" and slot == watch_slot \
                    and state.gained.get(seat) == "Nightwatchman":
                role = "Nightwatchman"
            if role == "Philosopher" and gamble_slot and slot == gamble_slot \
                    and state.gained.get(seat) == "Gambler":
                role = "Gambler"
            if role == "Philosopher" and state.gained.get(seat) in taken_slot \
                    and slot == taken_slot[state.gained[seat]]:
                role = state.gained[seat]

            if role == "Poisoner":
                target = hidden.get(("poisoner", night))
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
                if state.working(seat):
                    state.droison(target, slot, "Poisoner")

            elif role == "Sailor":
                target = _by_seat(hidden, "sailor", night, seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
                # One of the two is drunk; which is the Storyteller's, so the
                # walk is told rather than deciding.
                drunk = _by_seat(hidden, "sailor_drunk", night, seat)
                if drunk is not None:
                    state.droison(drunk, slot, "Sailor", by=seat)

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
                if named is None:
                    continue
                # Naming the Goon is choosing it (the wiki's example, and
                # the table's ruling of 08.10.2026). It answers first, and
                # a Courtier it makes drunk names nobody into drunkenness.
                if named == "Goon":
                    for other, role_there in state.roles.items():
                        if role_there == "Goon":
                            state.choose(seat, other, slot)
                            _goon_answers(state, seat, other, slot)
                if not state.working(seat):
                    continue
                for other, role_there in state.roles.items():
                    if role_there == named:
                        state.droison(other, slot, "Courtier")

            elif role == "SnakeCharmer":
                # Swaps with the Demon if it points at one. Acts at 11, so
                # the swap happens *before* the Demon's kill — and the seat
                # that kills is the charmer's, holding the Demon now.
                by_seat = hidden.get(("snakecharmers", night))
                target = (by_seat.get(seat) if by_seat is not None
                          else hidden.get(("snakecharmer", night)))
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
                if not state.working(seat):
                    continue
                # Lil' Monsta's babysitter is swapped like a Demon, and
                # keeps the baby until the Minions choose (E, Weg 1).
                if target == getattr(state, "lm_sitter", None):
                    became = state.roles[target]
                    state.roles[seat], state.roles[target] = \
                        became, "SnakeCharmer"
                    state.sides[seat], state.sides[target] = \
                        state.sides[target], state.sides[seat]
                    state.droison(target, slot, "SnakeCharmer swap")
                    state.log.append((slot, "swapped", seat, target))
                    continue
                if TEAM.get(state.roles.get(target, ""), "") != "demon":
                    continue
                became = state.roles[target]
                state.roles[seat], state.roles[target] = became, "SnakeCharmer"
                state.gift_ends(target)
                state.gained.pop(seat, None)     # a Philosopher no longer
                state.sides[seat], state.sides[target] = "evil", "good"
                state.droison(target, slot, "SnakeCharmer swap")
                state.log.append((slot, "swapped", seat, target))
                # A Lleech moves with its poison: the old host is sober
                # and the new one, chosen as the charmer becomes it, is
                # poisoned from here on, not from the Sweetheart's slot
                # (11.10.2026).
                if became == "Lleech":
                    hosts = hidden.get(("lleech", night)) or {}
                    old = hosts.get(target, (None,))[0]
                    new = hosts.get(seat, (None,))[0]
                    if old in stops_being_droisoned:
                        state.droisoned.discard(old)
                        stops_being_droisoned.discard(old)
                    if new in becomes_droisoned:
                        state.droison(new, slot, "Lleech")
                        becomes_droisoned.discard(new)

            elif role == "Monk":
                # Guards somebody from the Demon. Acts at 12, before every
                # Demon, which is what makes the guard mean anything: the
                # Demon arrives later and finds the seat already protected.
                target = _by_seat(hidden, "monk", night, seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
                if state.working(seat):
                    state.guarded.add(target)
                    state.guards[target] = seat

            elif role == "Innkeeper":
                # Two players are safe tonight and one of them is drunk. Acts
                # at 9, before the Monk and long before the Demon.
                # A pair, but tolerate a single seat: the enumerator hands
                # over a tuple sized by the source's capacity, and a source
                # that can only reach one seat gives an int.
                picked = _by_seat(hidden, "innkeeper", night, seat) or ()
                if isinstance(picked, int):
                    picked = (picked,)
                if not picked or seat not in state.alive:
                    continue
                for target in picked:
                    state.choose(seat, target, slot)
                    _goon_answers(state, seat, target, slot)
                if state.working(seat):
                    state.guarded |= set(picked)
                    for target in picked:
                        state.safe[target] = seat
                        state.guards[target] = seat
                    drunk = _by_seat(hidden, "innkeeper_drunk", night, seat)
                    if drunk is not None:
                        state.droison(drunk, slot, "Innkeeper", by=seat)

            elif role == "Gambler":
                # Names somebody and a character, and dies if it guessed
                # wrong. Acts at 10, so a Poisoner at 7 has already had its
                # say — and a droisoned Gambler dies of nothing, because a
                # plain ability simply does not function.
                by_seat = hidden.get(("gamblers", night))
                guess = (by_seat.get(seat) if by_seat is not None
                         else hidden.get(("gambler", night)))
                if guess is None:
                    continue
                # Judged *after* its target answers back. A Gambler that
                # picks the Goon first is drunk on the spot, so the guess
                # it has just made costs it nothing. This had it the other
                # way round — "the guess is already made" — which is not
                # what the card or the table says (03.10.2026).
                if seat not in state.alive:
                    continue
                target, said = guess
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if state.working(seat) and state.roles.get(target) != said:
                    state.kill(seat, slot, "Gambler")

            elif role == "Tinker":
                # May die at any time, and the Storyteller decides. Nothing
                # to derive: the walk is told whether it went tonight.
                went = hidden.get(("tinker", night))
                if went and (went is True or seat in went) \
                        and seat in state.alive:
                    state.kill(seat, slot, "Tinker")

            elif role == "Acrobat":
                # Picks somebody and dies if they are — or **become** —
                # droisoned tonight. On the publisher's night sheet it
                # picks early, after the Poisoner and before every Demon
                # (23.10.2026; the older file had it after them, at 39).
                # So the pick is made here and the fall is settled later,
                # once everything that could droison the pick has acted —
                # after the Gossip, where the simulator settles it too
                # (`_acrobat_falls_now`).
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
                target = _by_seat(hidden, "acrobat", night, seat)
                if target is None or seat not in state.alive:
                    continue
                if not state.working(seat):
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                acrobats.append((seat, target))

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
                target = _by_seat(hidden, "moonchild", night, seat)
                if target is None:
                    continue
                # Its state *tonight* decides, and the dead can be drunk
                # or poisoned like anybody else. The pick is public, so
                # it is handed in whether or not it did anything.
                if seat in state.droisoned:
                    continue
                # Good *when it was chosen*, which was in daylight: a
                # Goon the Demon has turned since still dies of it. Not a
                # seat made a Demon tonight before its turn — a Snake
                # Charmer's swap — which is evil by then, as in the
                # simulator (27.10.2026).
                if state.sides_at_dusk.get(target) == "good" \
                        and TEAM.get(state.roles.get(target, ""), "") \
                        != "demon" \
                        and target in state.alive:
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
                # A Lunatic points at somebody, and for the Goon that is
                # a player choosing a player (table ruling, 02.10.2026).
                target = hidden.get(("lunatic", night))
                if role == "Lunatic" and target is not None \
                        and seat in state.alive:
                    state.choose(seat, target, slot)
                    _goon_answers(state, seat, target, slot)

            elif role == "Exorcist":
                # Names the Demon, and it does not kill tonight. Acts at 21,
                # before every Demon, which is what lets it work at all.
                target = _by_seat(hidden, "exorcist", night, seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
                if state.working(seat) \
                        and TEAM.get(state.roles.get(target, ""), "") == "demon":
                    state.silenced.add(target)
                    state.log.append((slot, "exorcised", target, ""))
                # Last night's babysitter named: Lil' Monsta kills nobody
                # tonight (F, Weg 1).
                if state.working(seat) \
                        and target == getattr(state, "lm_sitter", None):
                    state.lm_silenced = True
                    state.log.append((slot, "exorcised", target, "baby"))

            elif role == "DevilsAdvocate":
                # Keeps somebody from dying by execution tomorrow. Nothing
                # happens tonight, but the choice is made now.
                target = hidden.get(("devilsadvocate", night))
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
                state.spared.add(target)

            elif role == "Fearmonger":
                # Chooses a player every night (10.10.2026). Nothing comes
                # of it tonight, but it points at somebody, so a Goon
                # answers — drunk or sober, the choice is made.
                target = hidden.get(("fearmonger", night))
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)

            elif role == "Widow":
                # Poisons somebody on its first night, for as long as it
                # lives (10.10.2026). Told only the pick that landed, so a
                # Widow that was drunk already or chose the Goon first is
                # handed nothing and does nothing.
                target = (hidden.get(("widow", night)) or {}).get(seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if state.working(seat):
                    state.droison(target, slot, "Widow")

            elif role == "Preacher":
                # Chooses a player every night; a Minion it chooses while
                # working has no ability from now on (10.10.2026).
                target = (hidden.get(("preacher", night)) or {}).get(seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if state.working(seat) and TEAM.get(
                        state.roles.get(target, ""), "") == "minion":
                    state.droison(target, slot, "Preacher")
                    state.preached.add(target)

            elif role == "Huntsman":
                # Once a game, a living player; a Damsel it finds while
                # working is the Townsfolk the walk is told (10.10.2026).
                target = (hidden.get(("huntsman", night)) or {}).get(seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                made = hidden.get(("huntsman_made", night))
                if state.working(seat) and made is not None \
                        and state.roles.get(target) == "Damsel":
                    state.roles[target] = made
                    state.log.append((slot, "made", target, made))

            elif role == "Lycanthrope":
                # Each night but the first, a living player: a good one
                # that is not the faux paw dies, and the Demon kills
                # nobody tonight (11.10.2026).
                target = (hidden.get(("lycanthrope", night)) or {}).get(seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat) or target not in state.alive \
                        or target == state.faux_paw \
                        or state.sides.get(target) != "good":
                    continue
                state.kill(target, slot, "Lycanthrope")
                if target in state.died:
                    state.lycanthrope_killed = True

            elif role == "Harpy":
                # Two players; only the first is chosen by its ability in
                # a way a Goon could answer, and nothing dies tonight.
                target = (hidden.get(("harpy", night)) or {}).get(seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)

            elif role == "Mezepheles":
                # Whoever said its word yesterday turns evil at its turn,
                # 18 — if it held the character when the night began and
                # has its ability now (11.10.2026). Nobody is chosen, so
                # there is nothing for a Goon to answer.
                turned = hidden.get(("mezepheles", night))
                # (`was` is the Pit-Hag's by now, further down this loop.)
                dusk = f"E{night - 1}" if night > 1 else phase
                if turned is None or not state.working(seat) \
                        or deal.role_at(seat, dusk) != "Mezepheles":
                    continue
                if state.sides.get(turned) == "good":
                    state.sides[turned] = "evil"
                    state.log.append((slot, "turned", turned, "Mezepheles"))

            elif role == "Witch":
                # Curses somebody: if they nominate tomorrow, they die.
                # Again nothing tonight, but the aim is taken now.
                target = hidden.get(("witch", night))
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
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
                    was = state.roles.get(target)
                    state.lets_go(target, slot)
                    state.roles[target] = became   # the side does not move
                    state.log.append((slot, "made", target, became))
                    # A Goon made just now has not been chosen by anybody:
                    # the Pit-Hag pointed at what the seat was before, and
                    # the next to choose it is the first (found at the
                    # gate of the eighth five, 11.10.2026).
                    if became == "Goon":
                        state.chosen_by.pop(target, None)
                    # A Drunk made into something is sober from here, not
                    # from the Sweetheart's slot: a Drunk made a
                    # Lycanthrope at 16 kills at 22 (11.10.2026).
                    if was == "Drunk" and target in stops_being_droisoned:
                        state.droisoned.discard(target)
                        stops_being_droisoned.discard(target)

            elif role == "Assassin":
                # One kill, once a game, and it ignores protection. Acts at
                # 36 — *after* every Demon, which is what makes a starpass
                # to an Assassin cost it the night: by 36 that seat is
                # holding the Demon and this branch never runs.
                target = hidden.get(("assassin", night))
                if target is None or seat not in state.alive:
                    continue
                # The one choice the Goon does not turn away: chosen by a
                # working Assassin it dies *and* turns evil. Chosen by one
                # that was drunk already, it lives and turns evil.
                able = state.working(seat)
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not able:
                    continue
                if target in state.alive:
                    state.kill(target, slot, "Assassin", unstoppable=True)

            elif role == "Professor":
                # Once a game, a dead Townsfolk stands up again. At 43,
                # after every Demon — so whoever comes back was not there
                # to be killed tonight, and wakes only if their own slot
                # is still to come.
                back = hidden.get(("professor", night))
                if back is None or not state.working(seat):
                    continue
                state.alive.add(back)
                state.log.append((slot, "raised", back, "Professor"))

            elif role == "Godfather":
                # Kills if an Outsider died in daylight. Acts at 37, after
                # the Demon, so it can add a second body to the night.
                target = hidden.get(("godfather", night))
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                if not state.working(seat):
                    continue      # drunk already, or by the Goon just now
                if target in state.alive:
                    state.kill(target, slot, "Godfather")

            elif role == "Nightwatchman":
                # Points at somebody once a game, late: 47 on the first
                # night and 65 after, when every kill has landed. The
                # player is woken and shown who it is — unless it has no
                # ability by then, and then nobody is woken at all. A
                # player choosing a player, so the Goon is asked.
                target = (hidden.get(("nightwatchman", night)) or {}).get(seat)
                if target is None or seat not in state.alive:
                    continue
                state.choose(seat, target, slot)
                _goon_answers(state, seat, target, slot)
                state.woken_by_nightwatchman[seat] = (
                    target if state.working(seat) else None)

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
                state.lets_go(a, slot)
                state.lets_go(b, slot)
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
                    # The Demon killed it: its Grandmother goes too
                    # (Stelle 87, Weg 1, 30.10.2026).
                    if seat in state.died:
                        _grandmother_grieves(state, seat, slot, hidden, night)
                    state.roles[jump] = "FangGu"
                    state.log.append((slot, "jumped", seat, jump))
                    continue
                if role == "Pukka":
                    _pukka_takes_its_turn(state, seat, slot, hidden, night)
                    continue
                # "Just before waking the Shabaloth": one it chose last
                # night may be alive again, before it chooses tonight.
                if role == "AlHadikhia":
                    _al_hadikhia_takes_its_turn(state, seat, slot, hidden,
                                                night)
                    continue
                back = hidden.get(("regurgitated", night))
                if role == "Shabaloth" and back is not None \
                        and state.working(seat):
                    state.alive.add(back)
                    state.log.append((slot, "raised", back, "Shabaloth"))
                aimed = hidden.get(("demon", night))
                # The second of two Demons has an aim of its own (Hatter
                # stage 2).
                if seat == hidden.get(("second_demon", night)):
                    aimed = hidden.get(("demon2", night))
                # A Yaggababble chooses nobody: the Storyteller takes a
                # player for each time it said its phrase, so no Goon
                # answers. A Leviathan kills nobody at all, and points at
                # a good player only by its jinxes — and then a Banshee
                # it pointed at dies (11.10.2026).
                points = role != "Yaggababble"
                if role == "Leviathan":
                    pick = hidden.get(("leviathan", night))
                    if pick is None or not state.working(seat) \
                            or seat in state.silenced:
                        continue
                    state.choose(seat, pick, slot)
                    _goon_answers(state, seat, pick, slot)
                    held = state.roles.get(pick)
                    if seat in state.droisoned or not (
                            held == "Banshee"
                            or (held == "Philosopher"
                                and state.gained.get(pick) == "Banshee")):
                        continue
                    aimed, points = [pick], False
                # A Zombuul that survived its first death is down on the
                # board and still the Demon: being off the living list
                # does not stop it, only being droisoned does.
                able = state.working(seat) or (
                    seat == state.undead and seat not in state.droisoned)
                if aimed is None or not able:
                    continue
                targets = [aimed] if isinstance(aimed, int) else list(aimed)
                if seat in state.silenced:
                    state.log.append((slot, "exorcised", seat, "no kill"))
                    continue
                if _the_princess_holds(state, hidden, night):
                    # It still chooses, so a Goon still answers.
                    for target in targets:
                        if not points:
                            break
                        state.choose(seat, target, slot)
                        _goon_answers(state, seat, target, slot)
                    state.log.append((slot, "princess", seat, "no kill"))
                    continue

                # Whether the ability functions is decided when the
                # character acts — and for the Goon, after it has answered
                # back: the first to choose it is drunk on the spot, so
                # that very choice fails (rulebook of the game, confirmed
                # 03.10.2026). This said the opposite until then.
                for target in targets:
                    if points:
                        state.choose(seat, target, slot)
                        _goon_answers(state, seat, target, slot)
                    # Drunk the moment it chooses the Goon first: that
                    # kill fails, and every later one tonight with it.
                    if seat in state.droisoned:
                        continue

                    if target not in state.alive:
                        continue              # sunk into a corpse
                    # A guard set earlier tonight holds, which is the whole
                    # reason the Monk acts at 12 and the Demon at 24.
                    # ...while whoever set it is still standing and
                    # working. A Shabaloth that takes the Innkeeper first
                    # finds its pair unguarded for the second kill.
                    giver = state.guards.get(target)
                    if target in state.guarded and (
                            giver is None or state.working(giver)):
                        state.log.append((slot, "guarded", target, role))
                        state.prevented.add(seat)
                        continue
                    if state.has(target, "Soldier") \
                            and state.works(target, "Soldier"):
                        state.log.append((slot, "guarded", target, "Soldier"))
                        state.prevented.add(seat)
                        continue
                    state.kill(target, slot, role)
                    _grandmother_grieves(state, target, slot, hidden, night)

    state.gift_turn = None
    # An Acrobat's pick still unsettled when the night ran out of slots.
    if acrobats:
        _acrobat_falls_now(10_000)

    # A Lleech whose host died tonight dies with it; one whose host went
    # while it was not working dies tonight if it is now (11.10.2026).
    if not hidden.get(("lleech_lost", night)):
        for lleech, (host, before) in sorted(
                (hidden.get(("lleech", night)) or {}).items()):
            if lleech not in state.alive \
                    or state.roles.get(lleech) != "Lleech":
                continue
            if (before or host in state.died) and state.working(lleech):
                state.kill(lleech, 99, "Lleech's host", unstoppable=True)

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
    "Steward", "Knight", "Shugenja", "King",
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

    # NOTE: the Savant and the Artist are deliberately absent, and so
    # are the High Priestess, the General and the Fisherman (12.10.2026):
    # what the Storyteller believes, kept and not weighed.
    #
    # A Savant is told two statements, one true; an Artist asks a
    # question and is told yes or no. Both are free text the Storyteller
    # invents, so there is nothing for a replay to derive — the walk can
    # say *when* they were told and nothing about *what*.
    #
    # The solver treats them the same way: `weighed` returns False, so
    # they are kept rather than solved. Listing them here with a
    # derivation that returned None would look like coverage and be none.

    if role == "Steward":
        # One player, and whether they are good as the board stands at
        # its slot — late on the first night, before an Ogre has picked.
        target = state.asked.get(seat)
        if target is None:
            return None
        # Good, or a Spy the Storyteller may show as good — while its
        # ability to misregister is working.
        held = state.roles.get(target, "")
        passes = held in CHARACTERS and bool(
            {"townsfolk", "outsider"} & set(CHARACTERS[held].registers))
        return state.sides.get(target) == "good" or (
            passes and target not in state.droisoned)

    if role == "Knight":
        # Two players, and whether neither holds a Demon *now* — so a
        # Snake Charmer that swapped at 20 is the Demon it reads.
        pair = state.asked.get(seat)
        if not pair:
            return None
        return all(TEAM.get(state.roles.get(p, ""), "") != "demon"
                   for p in pair)

    if role == "Shugenja":
        # Which way the closest evil player sits: True clockwise, False
        # anticlockwise, None for a tie, which is the Storyteller's.
        n = len(state.roles)
        best = {1: None, -1: None}
        for gap in range(1, n):
            other = (seat + gap) % n
            if state.sides.get(other) != "evil":
                continue
            back = n - gap
            if gap <= back and (best[1] is None or gap < best[1]):
                best[1] = gap
            if back <= gap and (best[-1] is None or back < best[-1]):
                best[-1] = back
        if best[1] == best[-1]:
            return None
        return best[-1] is None or (best[1] is not None
                                    and best[1] < best[-1])

    if role == "King":
        # Reads at 63, after every kill — so it counts the dead as they
        # are *now*, tonight's among them, and a Zombuul under its
        # shroud among the living. False for a night it learns nothing;
        # otherwise every character somebody alive holds, since which
        # one it is shown is the Storyteller's choice.
        if state.night < 2:
            return None
        living = set(state.alive)
        if state.undead is not None:
            living.add(state.undead)
        if len(state.roles) - len(living) < len(living):
            return False
        return sorted({state.roles[p] for p in living})

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


def _lil_monsta_takes_its_turn(state, lm, slot, hidden, night):
    """The Minions' choice, then the kill it may make (21.10.2026)."""
    target = lm["aimed"]
    if night > 1 and lm["alive"] and target is not None \
            and not state.lm_silenced and target in state.alive \
            and not _the_princess_holds(state, hidden, night) \
            and not _a_guard_holds(state, target, slot, None, "LilMonsta"):
        state.kill(target, slot, "LilMonsta")
        if target in state.died:
            _grandmother_grieves(state, target, slot, hidden, night)
    state.lm_sitter = lm["tonight"]


def _grandmother_grieves(state, victim, slot, hidden, night):
    """Her grandchild taken by the Demon takes her with it.

    Only the Demon's kill does this, and only if she is working — which
    the walk knows because everything that could have droisoned her has
    already acted by the time a Demon kills.

    Which seat is the grandchild was settled on night one and is handed
    in, like every other thing the walk is told rather than guesses.
    """
    children = hidden.get("grandchildren") or {}
    if victim not in children.values():
        return
    # Only if the grandchild really died. A Tea Lady keeping them alive
    # left nothing to grieve, and this grieved anyway (03.10.2026).
    if victim in state.alive:
        return
    # Each Grandmother whose grandchild it was, and a Philosopher that
    # took her (group 6, 14.10.2026).
    for seat in list(state.roles):
        if children.get(seat) != victim or seat not in state.alive \
                or not state.has(seat, "Grandmother"):
            continue
        if not state.works(seat, "Grandmother"):
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
    # Or a Philosopher that took it (13.10.2026).
    if not state.has(target, "Goon"):
        return
    first_slot, first = state.chosen_by.get(target, (None, None))
    if first != chooser or first_slot != slot:
        return                              # somebody got there first
    if not state.works(target, "Goon"):
        return                              # a droisoned Goon does nothing
    # A Demon the Boffin gave it does not turn good (their jinx).
    if state.boffin.get(target) != "Goon":
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


def _al_hadikhia_takes_its_turn(state, seat, slot, hidden, night):
    """Three chosen and announced; each answers life or death in turn,
    and if all three live, all three die (21.10.2026).

    The answers are handed in like a Demon's aim; what they do is worked
    out here. A dead one choosing life is back at once; one choosing
    death dies at once, unless something keeps it alive — and then it
    counts as having chosen life (Patrick's B). All three standing at the
    end die together, so a Tea Lady is asked about the table as it stood
    before any of them went. Drunk or poisoned, it chooses and nothing
    happens (C); a Goon chosen first makes it so on the spot.
    """
    picks = hidden.get(("ah_picks", night))
    if not picks or seat in state.silenced:
        return
    answers = list(hidden.get(("ah_answers", night)) or ())
    able = state.working(seat)
    princess = _the_princess_holds(state, hidden, night)
    back = set()            # dead before tonight, and up again now
    for target in picks:
        state.choose(seat, target, slot)
        _goon_answers(state, seat, target, slot)
        if not able or seat in state.droisoned:
            continue
        if not answers or answers[0][0] != target:
            state.log.append((slot, "no answer", target, "AlHadikhia"))
            continue
        _who, life = answers.pop(0)
        if life and target not in state.alive:
            if target not in state.died:
                back.add(target)
            else:
                # Down and up again tonight: nothing the table saw.
                state.died.discard(target)
            state.alive.add(target)
            state.log.append((slot, "raised", target, "AlHadikhia"))
        elif not life and target in state.alive:
            if not princess and not _a_guard_holds(state, target, slot,
                                                   seat, "AlHadikhia"):
                state.kill(target, slot, "AlHadikhia")
                if target in state.died and target not in back:
                    _grandmother_grieves(state, target, slot, hidden, night)
    if not able or seat in state.droisoned \
            or not all(p in state.alive for p in picks):
        _up_and_down_again(state, back)
        return
    if princess:
        state.log.append((slot, "princess", seat, "no kill"))
        return
    # One dead before tonight who chose life never stood: it does not
    # count beside a Tea Lady (Stelle 67, Weg 2, 30.10.2026).
    state.at_once = set(state.alive) - back
    try:
        going = [p for p in dict.fromkeys(picks)
                 if not _a_guard_holds(state, p, slot, seat, "AlHadikhia")]
        for p in going:
            state.kill(p, slot, "AlHadikhia")
    finally:
        state.at_once = None
    for p in going:
        if p in state.died and p not in back:
            _grandmother_grieves(state, p, slot, hidden, night)
    _up_and_down_again(state, back)


def _up_and_down_again(state, back):
    """Dead before tonight, back and down again before dawn: the table saw
    nothing of it (the simulator's `_nobody_returns_only_to_die`)."""
    for p in back:
        if p in state.died and p not in state.alive:
            state.died.discard(p)


def _a_guard_holds(state, target, slot, demon, role):
    """A Monk's guard or a sober Soldier: the two the Demon's own kill
    asks about before `kill` asks the rest."""
    giver = state.guards.get(target)
    if target in state.guarded and (giver is None or state.working(giver)):
        state.log.append((slot, "guarded", target, role))
        if demon is not None:             # Lil' Monsta is nobody
            state.prevented.add(demon)
        return True
    if state.has(target, "Soldier") and state.works(target, "Soldier"):
        state.log.append((slot, "guarded", target, "Soldier"))
        if demon is not None:
            state.prevented.add(demon)
        return True
    return False


def _the_princess_holds(state, hidden, night):
    """Yesterday's Princess had her nominee executed, and has her ability
    now: the Demon kills nobody tonight (10.10.2026)."""
    if state.lycanthrope_killed:
        return True                       # the Lycanthrope's, 11.10.2026
    princess = hidden.get(("princess", night))
    return princess is not None and state.has(princess, "Princess") \
        and state.works(princess, "Princess")


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
            state.choose(seat, fresh, slot)
            _goon_answers(state, seat, fresh, slot)
            # The Goon, first: drunk on the spot. Nobody poisoned, the
            # old token stays and rests, no attack.
            if not state.working(seat):
                return
            state.droison(fresh, slot, "Pukka")
    stale = hidden.get(("pukka_due", night))
    lifted = hidden.get(("pukka_token_only", night))
    # A Princess's day: the poison from before kills nobody, and the token
    # comes off all the same (10.10.2026).
    if stale is not None and _the_princess_holds(state, hidden, night):
        state.log.append((slot, "princess", stale, "Pukka"))
        if lifted:
            state.droisoned.discard(stale)
        return
    if stale is None or stale not in state.alive:
        if stale is not None and lifted:
            state.droisoned.discard(stale)    # the token comes off a corpse too
        return
    # A guard holds only while whoever gave it is still working, and the
    # Pukka has just poisoned somebody: an Innkeeper it chose tonight
    # protects nobody from the poison of the night before.
    keepers = [p for p in state.roles
               if (state.has(p, "Innkeeper") or state.has(p, "Monk"))
               and p in state.alive]
    if stale in state.guarded and any(state.working(p) for p in keepers):
        state.log.append((slot, "guarded", stale, "Pukka"))
        state.prevented.add(seat)
        if lifted:
            state.droisoned.discard(stale)    # lived, and healthy from here
        return
    state.kill(stale, slot, "Pukka")
    if lifted and stale in state.alive:
        state.droisoned.discard(stale)        # kept alive, and healthy now
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


