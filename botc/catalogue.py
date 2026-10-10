"""Every character the solver knows about, and what it knows about them.

A character's team, its night schedule and how it misregisters belong to
the character, not to the script it appears on. A *script* is only a
selection: a name and a set of characters. So the facts live here once,
and `Script` in `scripts.py` picks from them.

`modelled` is the honest flag. A character can be in the catalogue —
enough to fill a team slot and be claimed — without its ability being
implemented. Those are named to the person using the tool rather than
quietly ignored, because a Grandmother whose reading is never checked
looks exactly like a Grandmother who has not spoken yet.
"""

from typing import NamedTuple

# What waking up feels like from the seat. See `wake_fits`.
NEVER = "never"
FIRST = "first"
EVERY = "every"
OTHER = "other"
SOMETIMES = "sometimes"
WAKE_PATTERNS = [NEVER, FIRST, EVERY, OTHER, SOMETIMES]

WAKE_LABELS = {
    NEVER: "Never wakes",
    FIRST: "Only the first night",
    EVERY: "Every night",
    OTHER: "Every night but the first",
    SOMETIMES: "Only sometimes",
}


# How far a character is reasoned about.
FULLY = "fully"
PARTLY = "partly"
NOT = "not"


class Character(NamedTuple):
    key: str            # how the solver names it: "FortuneTeller"
    id: str             # how scripts name it: "fortuneteller"
    name: str           # how a person names it: "Fortune Teller"
    team: str           # townsfolk / outsider / minion / demon
    wake: frozenset     # what an honest holder could say about waking
    # Where in the night this character acts, or 0 for a night it does
    # not. Two numbers because the first night is a different order: a
    # Washerwoman acts then and never again, and the Demon learning its
    # Minions has a slot that later nights do not have.
    #
    # Taken from `data/roles.json` and **not renumbered** — the gaps are
    # the point. A character added later drops into its true position
    # without disturbing anything around it.
    #
    # This is what makes an Imp starpassing to an Assassin work: the Imp
    # acts at 24 and the Assassin at 36, so by the time the Assassin's
    # slot arrives that seat is holding the Imp and the ability is gone.
    first_night: int = 0
    other_night: int = 0
    registers: frozenset = frozenset()   # teams it may *also* register as
    setup: tuple = ()   # ways it shifts the bag, e.g. the Baron
    believes: bool = False   # the holder thinks they are somebody else
    # Which teams the token they were handed can come from. The Drunk is
    # always given a Townsfolk; the Marionette thinks it is any good
    # character, so either side of good.
    believes_from: tuple = ("townsfolk",)
    # How far this character is reasoned about. Three states rather than
    # two, because "not built yet" and "built as far as it ever will be"
    # are different things and the script panel should not pretend
    # otherwise. A Savant sitting in the same list as an unstarted Demon
    # tells somebody the wrong thing about both.
    #
    #   FULLY   the ability is reasoned about
    #   PARTLY  what it says is recorded and shown, but not weighed —
    #           because its content can be anything at all
    #   NOT     nothing is done with it, and the note says why
    handled: str = FULLY
    # Is this as far as it goes? A Mutant leaves nothing on the board to
    # read, so it is finished at NOT — unlike a character nobody has got
    # to yet. PARTLY is always settled; that is what it means.
    settled: bool = False
    note: str = ""           # what is missing, when something is
    # Can this character stop somebody else's ability working? Only the
    # Mathematician asks, and it asks for a narrow reason: its number is
    # the size of the impairment set, so an *unmodelled* character that
    # droisons means the solver cannot know how much went wrong and must
    # say nothing. An unmodelled character that only produces
    # information it cannot check — a Savant, an Artist — costs it
    # nothing, and used to silence it anyway.
    impairs: bool = False
    # Does this character deliberately point at a player at night? That
    # is what a Goon reacts to — not being looked at, being *chosen*. A
    # Courtier names a character rather than a player and never triggers
    # one; a Grandmother is shown somebody by the Storyteller rather than
    # choosing them.
    chooses: bool = False
    # Can this seat genuinely be on either side, as opposed to merely
    # reading as the other one? A Recluse is good and reads evil; a Goon
    # that turned really is evil while it lasts. The two are different
    # questions and only the second changes which team somebody is on.
    alignment_open: bool = False
    # When the holder is actually woken *for their own ability*, which is
    # a different question from `wake` above. `wake` is forgiving — it is
    # what somebody could honestly claim, and a Courtier's honest answer
    # depends on when they spent it. This is the fact, and the Chambermaid
    # needs the fact. "conditional" means it depends on the board, and a
    # rule in `waking.py` works it out.
    nights: str = "never"
    # Does this take a seat? The Fabled do not — they are put on the table
    # by the Storyteller and shown to everybody, and they are in play
    # without anybody holding them.
    seated: bool = True
    # A setup rule about *where* this character sits: the team one of its
    # two neighbours has to hold when the tokens are dealt. The Marionette
    # neighbours the Demon. Only the deal — a Demon that moves on later
    # does not move the Marionette with it.
    beside: str = ""
    # Can the holder not say what it is? A Mutant "mad about being an
    # Outsider" might be executed, so it never claims one: it always
    # stands behind a Townsfolk. Unlike every other good player, whose
    # lie is a choice and costs a world, this one is the rules talking.
    hides: bool = False
    # Characters the setup puts in play beside this one: "[+the King]".
    # Asked of the finished deal, like `beside` (worlds.seated_legally).
    brings: tuple = ()


def _handled(self):
    """Is this character reasoned about at all?

    Kept because a dozen places ask it and all of them mean the same
    thing: can the solver be trusted about this ability. Recording what
    somebody said without weighing it does not count.
    """
    return self.handled == FULLY


Character.modelled = property(_handled)


def _c(key, id_, name, team, wake, **kw):
    return Character(key, id_, name, team, frozenset(wake), **kw)


# --------------------------------------------------------------------------
# Trouble Brewing
# --------------------------------------------------------------------------
_TB = [
    _c("Washerwoman", "washerwoman", "Washerwoman", "townsfolk", {FIRST}, nights="first"),
    _c("Librarian", "librarian", "Librarian", "townsfolk", {FIRST}, nights="first"),
    _c("Investigator", "investigator", "Investigator", "townsfolk", {FIRST}, nights="first"),
    _c("Chef", "chef", "Chef", "townsfolk", {FIRST}, nights="first"),
    _c("Empath", "empath", "Empath", "townsfolk", {EVERY}, nights="every"),
    _c("FortuneTeller", "fortuneteller", "Fortune Teller", "townsfolk", {EVERY}, nights="every", chooses=True),
    _c("Undertaker", "undertaker", "Undertaker", "townsfolk",
       {OTHER, EVERY, SOMETIMES}, nights="conditional"),
    _c("Monk", "monk", "Monk", "townsfolk", {OTHER, EVERY}, nights="other", chooses=True),
    _c("Ravenkeeper", "ravenkeeper", "Ravenkeeper", "townsfolk",
       {NEVER, SOMETIMES}, nights="conditional", chooses=True),
    _c("Virgin", "virgin", "Virgin", "townsfolk", {NEVER}),

    # Experimental. Guesses the whole evil team in daylight; if it is
    # exactly right, good wins. No night action at all — the only other
    # character here shaped like that is the Slayer.
    _c("Alsaahir", "alsaahir", "Alsaahir", "townsfolk", {NEVER}),

    # Experimental. Shown a player each night whose character *type*
    # differs from the one shown the night before — never told the type.
    #
    # The setup is the Godfather's shape: the Storyteller **may** add an
    # Outsider, and it is not knowable which they did. Hence two options,
    # one of them no change at all.
    _c("Balloonist", "balloonist", "Balloonist", "townsfolk",
       {EVERY, FIRST}, nights="every",
       setup=({"townsfolk": -1, "outsider": 1}, {})),

    # Experimental. Picks somebody each night and dies if they are
    # droisoned — which makes it the only character whose death is
    # evidence *about the impairment plan* rather than about the board.
    _c("Acrobat", "acrobat", "Acrobat", "townsfolk", {EVERY, OTHER},
       nights="other", chooses=True),

    # Experimental. Dies at night and hands the character on.
    #
    # Never wakes: being told you are the new Farmer is a *game rule* —
    # you learn any character you are given — not the Farmer's ability
    # doing something to you. So a Chambermaid does not count it.
    _c("Farmer", "farmer", "Farmer", "townsfolk", {NEVER}),
    _c("Slayer", "slayer", "Slayer", "townsfolk", {NEVER}),
    _c("Soldier", "soldier", "Soldier", "townsfolk", {NEVER}),
    _c("Mayor", "mayor", "Mayor", "townsfolk", {NEVER}),

    _c("Butler", "butler", "Butler", "outsider", {EVERY}, nights="every", chooses=True),
    _c("Drunk", "drunk", "Drunk", "outsider", set(WAKE_PATTERNS),
       believes=True, nights="conditional"),
    _c("Recluse", "recluse", "Recluse", "outsider", {NEVER},
       registers=frozenset({"minion", "demon"})),
    _c("Saint", "saint", "Saint", "outsider", {NEVER}),

    _c("Poisoner", "poisoner", "Poisoner", "minion", {EVERY}, nights="every", chooses=True),
    _c("Spy", "spy", "Spy", "minion", {EVERY},
       registers=frozenset({"townsfolk", "outsider"}), nights="every"),
    _c("ScarletWoman", "scarletwoman", "Scarlet Woman", "minion",
       {FIRST, SOMETIMES}, nights="conditional"),
    _c("Baron", "baron", "Baron", "minion", {FIRST},
       setup=({"townsfolk": -2, "outsider": 2},)),

    _c("Imp", "imp", "Imp", "demon", {FIRST, EVERY}, nights="other", chooses=True),

    # Woken on the first night to learn the Outsiders, and after that
    # only on a night it kills — see `waking._godfather`.
    _c("Godfather", "godfather", "Godfather", "minion", {FIRST, EVERY},
       nights="conditional", chooses=True,
       setup=({"townsfolk": 1, "outsider": -1},
              {"townsfolk": -1, "outsider": 1})),
    _c("DevilsAdvocate", "devilsadvocate", "Devil's Advocate", "minion",
       {EVERY}, nights="every", chooses=True),
    _c("Assassin", "assassin", "Assassin", "minion",
       {FIRST, EVERY, SOMETIMES}, nights="conditional", chooses=True),
    _c("Zombuul", "zombuul", "Zombuul", "demon", {FIRST, EVERY, SOMETIMES},
       nights="conditional", chooses=True),
    _c("Pukka", "pukka", "Pukka", "demon", {FIRST, EVERY}, nights="every",
       chooses=True),
    _c("Shabaloth", "shabaloth", "Shabaloth", "demon", {FIRST, EVERY},
       nights="other", chooses=True),
    _c("Po", "po", "Po", "demon", {FIRST, EVERY}, nights="other",
       chooses=True),

    # Changes how the game is won, not what happens on the board — but
    # a game that carries on after the Demon's execution is only legal
    # with a working Mastermind alive and no Scarlet Woman able to take
    # over, and that the solver weighs (`_mastermind_day`).
    _c("Mastermind", "mastermind", "Mastermind", "minion", {NEVER}),
]


# --------------------------------------------------------------------------
# Known, but not yet reasoned about
# --------------------------------------------------------------------------
# Enough to fill a team slot, be claimed, and be counted. Their abilities
# do nothing, which the tool says out loud rather than leaving to be
# discovered.
_UNMODELLED = [
    # Three players, exactly one evil **by registration** — so a Spy can
    # sit among the two good ones and a Recluse can be the evil one.
    _c("Noble", "noble", "Noble", "townsfolk", {FIRST}, nights="first"),
    _c("Grandmother", "grandmother", "Grandmother", "townsfolk", {FIRST}, nights="first"),
    _c("Sailor", "sailor", "Sailor", "townsfolk", {EVERY}, nights="every", chooses=True),
    _c("Exorcist", "exorcist", "Exorcist", "townsfolk", {OTHER, EVERY}, nights="other", chooses=True),
    _c("Innkeeper", "innkeeper", "Innkeeper", "townsfolk", {OTHER, EVERY}, nights="other", chooses=True),
    # Once per game, then they stop being woken. Which pattern an honest
    # holder reports depends on when they spent it: the first night only,
    # every night if they never did, somewhere in between otherwise.
    _c("Courtier", "courtier", "Courtier", "townsfolk",
       {FIRST, EVERY, SOMETIMES}, nights="conditional"),
    _c("Professor", "professor", "Professor", "townsfolk",
       {OTHER, SOMETIMES}, nights="conditional", chooses=True),
    _c("Gambler", "gambler", "Gambler", "townsfolk", {OTHER, EVERY}, nights="other", chooses=True),
    _c("Gossip", "gossip", "Gossip", "townsfolk", {NEVER}),
    _c("Minstrel", "minstrel", "Minstrel", "townsfolk", {NEVER}),
    _c("Chambermaid", "chambermaid", "Chambermaid", "townsfolk", {EVERY},
       nights="every", chooses=True),
    _c("Pacifist", "pacifist", "Pacifist", "townsfolk", {NEVER}),
    _c("TeaLady", "tealady", "Tea Lady", "townsfolk", {NEVER}),
    _c("Fool", "fool", "Fool", "townsfolk", {NEVER}),

    _c("Goon", "goon", "Goon", "outsider", {NEVER}, alignment_open=True),
    _c("Tinker", "tinker", "Tinker", "outsider", {NEVER}),
    _c("Moonchild", "moonchild", "Moonchild", "outsider", {NEVER},
       chooses=True),
    # Believes it is the Demon rather than a Townsfolk, which is the same
    # machinery pointed somewhere new — and it means the holder bluffs
    # like the Demon would, because as far as they know they are it.
    _c("Lunatic", "lunatic", "Lunatic", "outsider", set(WAKE_PATTERNS),
       believes=True, believes_from=("demon",), nights="conditional",
       chooses=True),
    # Takes the side of whoever it picks on night one, and never learns
    # which: `an_ogre_picks_a_side` in the solver moves the side, the
    # character stays. It points at somebody, so a Goon notices.
    _c("Ogre", "ogre", "Ogre", "outsider", {FIRST}, nights="first",
       chooses=True),
    # Named in limits.py as characters the solver will not reason about.
    # They still belong here, so a script can contain one and be told.
    _c("Atheist", "atheist", "Atheist", "townsfolk", {NEVER},
       handled=NOT,
       note="with an Atheist in play the Storyteller may break the rules, "
            "so there may be no legal world at all"),
    _c("Legion", "legion", "Legion", "demon", {NEVER},
       handled=NOT,
       note="most of the table is evil, so every team count the search "
            "prunes on is wrong"),
    _c("Riot", "riot", "Riot", "demon", {NEVER},
       handled=NOT,
       note="every Minion is a Demon, and days work differently"),

    _c("Marionette", "marionette", "Marionette", "minion",
       set(WAKE_PATTERNS), believes=True,
       believes_from=("townsfolk", "outsider"), beside="demon",
       nights="conditional"),
]


# --------------------------------------------------------------------------
# Fabled
# --------------------------------------------------------------------------
# Not dealt to anybody. The Storyteller puts one on the table and everyone
# can see it, so whether it is in play is public — but what it *did* is
# not, which is the whole point of the Sentinel.
_FABLED = [
    # An extra Outsider replaces a Townsfolk and a missing one is
    # replaced by a Townsfolk. The table still seats the same people, so
    # a shift that only moved one number would deal a game of the wrong
    # size — which is exactly what it did until somebody asked.
    _c("Sentinel", "sentinel", "Sentinel", "fabled", {NEVER}, seated=False,
       setup=({"townsfolk": 1, "outsider": -1},
              {},
              {"townsfolk": -1, "outsider": 1})),
]


# --------------------------------------------------------------------------
# Sects & Violets
# --------------------------------------------------------------------------
# The script where information stops being merely unreliable and starts
# being wrong. A Vortox does not droison anybody — protection works as
# normal — it makes Townsfolk abilities *yield false information*, which
# constrains a world in the opposite direction from poison: a poisoned
# Empath may be told anything, a Vortox'd one must be told something that
# is not so.
#
# Everything here is dealt and can be claimed. What each one *does* is
# added a few at a time; until then it says so rather than pretending.
_SV = [
    _c("Clockmaker", "clockmaker", "Clockmaker", "townsfolk", {FIRST},
       nights="first"),
    _c("Dreamer", "dreamer", "Dreamer", "townsfolk", {EVERY},
       nights="every", chooses=True),
    _c("SnakeCharmer", "snakecharmer", "Snake Charmer", "townsfolk",
       {EVERY}, nights="every", chooses=True),
    _c("Mathematician", "mathematician", "Mathematician", "townsfolk",
       {EVERY}, nights="every"),
    _c("Flowergirl", "flowergirl", "Flowergirl", "townsfolk", {OTHER},
       nights="other"),
    _c("TownCrier", "towncrier", "Town Crier", "townsfolk", {OTHER},
       nights="other"),
    _c("Oracle", "oracle", "Oracle", "townsfolk", {OTHER},
       nights="other"),
    # Weighed when both statements are entered in a shape the board can
    # answer (info.SAVANT_KINDS); words alone are kept and shown.
    _c("Savant", "savant", "Savant", "townsfolk", {NEVER}),
    _c("Seamstress", "seamstress", "Seamstress", "townsfolk",
       {NEVER, SOMETIMES}, nights="conditional", chooses=True),
    _c("Philosopher", "philosopher", "Philosopher", "townsfolk",
       {NEVER, SOMETIMES}, nights="conditional", chooses=True),
    _c("Artist", "artist", "Artist", "townsfolk", {NEVER},
       handled=PARTLY,
       note="its question is kept but not weighed — whatever the player "
            "thought to ask, which can be trivial or impossible"),
    _c("Juggler", "juggler", "Juggler", "townsfolk", {NEVER, SOMETIMES},
       nights="conditional"),
    _c("Sage", "sage", "Sage", "townsfolk", {NEVER, SOMETIMES},
       nights="conditional"),

    _c("Mutant", "mutant", "Mutant", "outsider", {NEVER}, hides=True),
    _c("Sweetheart", "sweetheart", "Sweetheart", "outsider", {NEVER}),
    _c("Barber", "barber", "Barber", "outsider", {NEVER}),
    _c("Klutz", "klutz", "Klutz", "outsider", {NEVER}),

    _c("EvilTwin", "eviltwin", "Evil Twin", "minion", {FIRST},
       nights="first"),
    _c("Witch", "witch", "Witch", "minion", {EVERY}, nights="every",
       chooses=True),
    # Madness leaves no mark of its own. What the table can see is: a
    # seat executed for breaking ceremadness, somebody saying they were
    # made mad (info.CerenovusMadness), and a good player claiming what
    # they are not — cheaper in a world with a Cerenovus alive
    # (solver.CERENOVUS_MADNESS_PENALTY) when the seat is marked unsure.
    _c("Cerenovus", "cerenovus", "Cerenovus", "minion", {EVERY},
       nights="every", chooses=True),
    _c("PitHag", "pithag", "Pit-Hag", "minion", {EVERY}, nights="every",
       chooses=True),

    _c("FangGu", "fanggu", "Fang Gu", "demon", {FIRST, EVERY},
       nights="other", chooses=True,
       setup=({"townsfolk": -1, "outsider": 1},)),
    # "[-1 Outsider]". Missing until the script was read against the
    # wiki (02.10.2026): every Vigormortis game was searched with one
    # Outsider too many, so its true bag was never among the worlds.
    _c("Vigormortis", "vigormortis", "Vigormortis", "demon",
       {FIRST, EVERY}, nights="other", chooses=True,
       setup=({"townsfolk": 1, "outsider": -1},)),
    _c("NoDashii", "nodashii", "No Dashii", "demon", {FIRST, EVERY},
       nights="other", chooses=True),
    _c("Vortox", "vortox", "Vortox", "demon", {FIRST, EVERY},
       nights="other", chooses=True),
]


# --------------------------------------------------------------------------
# Experimental, one at a time
# --------------------------------------------------------------------------
# Added singly and without a script of their own (05.10.2026). The first
# five all give information and leave the night as it was.
_EXPERIMENTAL = [
    # Shown one good player on its first night — by registration, so a
    # Spy may be the one (the wiki's own example).
    _c("Steward", "steward", "Steward", "townsfolk", {FIRST},
       nights="first"),
    # Shown two players who are not the Demon. They may be Minions, so
    # what it says holds for that night: a Minion it was shown can take
    # the star later.
    _c("Knight", "knight", "Knight", "townsfolk", {FIRST}, nights="first"),
    # Told which way round the circle its closest evil player sits. A
    # tie is the Storyteller's to break either way.
    _c("Shugenja", "shugenja", "Shugenja", "townsfolk", {FIRST},
       nights="first"),
    # Woken every night until it points at somebody, once; that player is
    # then woken and shown who the Nightwatchman is. A drunk or poisoned
    # one wakes nobody. It points at a player, so a Goon notices.
    _c("Nightwatchman", "nightwatchman", "Nightwatchman", "townsfolk",
       {FIRST, EVERY, SOMETIMES}, nights="conditional", chooses=True),
    # Learns a living character each night once the dead equal or
    # outnumber the living — counted at its own turn, which is after
    # every kill. The Demon is told who it is, which leaves no mark.
    _c("King", "king", "King", "townsfolk", {NEVER, SOMETIMES},
       nights="conditional"),

    # The second five (07.10.2026), chosen for being small: none of them
    # reads anything, and only the Ojo acts at night.
    #
    # Killed by the Demon, and the whole table is told a Banshee died —
    # not which seat. Only while its ability works: a poisoned one dies
    # like anybody. It then nominates and votes twice, dead as it is.
    _c("Banshee", "banshee", "Banshee", "townsfolk", {NEVER}),
    # Must vote on every nomination while five or more are alive, and
    # "must" is the player's to keep — drunk or poisoned makes no
    # difference to somebody who cannot know.
    _c("Zealot", "zealot", "Zealot", "outsider", {NEVER}),
    # Turns the result round, and nothing else: the game ends at the same
    # moment it would have. So nothing here reads it.
    _c("Heretic", "heretic", "Heretic", "outsider", {NEVER}),
    # Says "I am the Goblin" when nominated, and if it is then executed
    # its team wins. Anybody may say it. Shown its team on the first
    # night like any Minion, which is not an ability.
    _c("Goblin", "goblin", "Goblin", "minion", {FIRST}),
    # Names a *character*, and whoever holds it dies; if nobody does, the
    # Storyteller picks. Seen from the board that is a Demon that kills
    # one player a night, which is the ordinary kill. It names the
    # Goon's character to reach the Goon, and that counts as choosing it
    # (the wiki has a Courtier doing the same).
    _c("Ojo", "ojo", "Ojo", "demon", {FIRST, EVERY}, nights="other",
       chooses=True),

    # The third five (08.10.2026), chosen for being the smallest left:
    # four of them change only what the evil team knows or how the game
    # is scored, which no board shows, and the fifth only who is awake.
    #
    # Shown to the Demon as a Minion and to the Minions as the Demon, on
    # the first night. Wakes for nothing. Its jinx with the Wraith — a
    # public guess after an execution — is not built.
    _c("Magician", "magician", "Magician", "townsfolk", {NEVER}),
    # While it lives the evil team does not learn each other; the night
    # it dies they are woken and told. Being told is not their ability,
    # so a Chambermaid counts none of it.
    _c("PoppyGrower", "poppygrower", "Poppy Grower", "townsfolk", {NEVER}),
    # Changes side and wins if the Storyteller judges it lost the game
    # for its team. Decided after the game, so nothing here reads it.
    _c("Politician", "politician", "Politician", "outsider", {NEVER}),
    # Every Minion is shown three bluffs on the first night. Being shown
    # them is not the Minions' ability, and the Snitch itself never wakes.
    _c("Snitch", "snitch", "Snitch", "outsider", {NEVER}),
    # "You may choose to open your eyes at night. You wake when other
    # evil players do." Woken first whenever another evil player opens
    # their eyes for their own ability (waking._wraith). Its wake set is
    # wide on purpose: an evil seat says what it likes about its nights.
    _c("Wraith", "wraith", "Wraith", "minion", {FIRST, EVERY, SOMETIMES},
       nights="conditional"),

    # The fourth four (10.10.2026): the last small ones. Each brings a row
    # or changes the vote; the readings are the table's of that day.
    #
    # Guessed publicly by a Minion — the Minions' first guess — and its
    # team loses. Never wakes; the Minions are shown it on the first
    # night, which is not its ability (info.DamselGuess).
    _c("Damsel", "damsel", "Damsel", "outsider", {NEVER}),
    # Chooses a player every night, and the table is told when the player
    # is a new one (info.FearmongerChose). It points at a player, so a
    # Goon notices.
    _c("Fearmonger", "fearmonger", "Fearmonger", "minion", {FIRST, EVERY},
       nights="every", chooses=True),
    # Announced to everybody on its first day if it has its ability then
    # (info.VizierAnnounced), and cannot die during the day. Its own
    # nights are none — it wakes only beside a Fearmonger, by their jinx
    # (waking._vizier).
    _c("Vizier", "vizier", "Vizier", "minion", {NEVER, EVERY, SOMETIMES},
       nights="conditional"),
    # Eyes closed for every vote while it works (info.BlindVote). Chooses
    # each night whether to be drunk until dusk — itself, nobody else.
    _c("OrganGrinder", "organgrinder", "Organ Grinder", "minion",
       {FIRST, EVERY}, nights="every"),

    # The fifth five (10.10.2026), the first of the middling ones, read
    # with the table before anything was built.
    #
    # "If the Demon kills the King, you learn which player is the Demon.
    # [+the King]" Woken only on that night (waking.uncertain), and the
    # King comes with it — a script with a Choirboy and no King is one
    # built wrong (table ruling, 10.10.2026), so the deal insists.
    _c("Choirboy", "choirboy", "Choirboy", "townsfolk", {NEVER, SOMETIMES},
       nights="conditional", brings=("King",)),
    # On her first day, if she nominated the player the town executed,
    # the Demon kills nobody that night (info.PrincessNominated).
    _c("Princess", "princess", "Princess", "townsfolk", {NEVER}),
    # Nominates once a game, and a nominee who is not the Demon dies
    # (info.GolemNomination).
    _c("Golem", "golem", "Golem", "outsider", {NEVER}),
    # Kills in daylight, in the open, and plays roshambo on the gallows
    # (info.PsychopathKill, info.PsychopathRoshambo).
    _c("Psychopath", "psychopath", "Psychopath", "minion", {NEVER}),
    # Looks at the Grimoire on its first night and poisons a player for as
    # long as it lives; one good player is told a Widow is in play
    # (info.WidowKnown). It points at a player, so a Goon notices.
    _c("Widow", "widow", "Widow", "minion", {FIRST, SOMETIMES},
       nights="conditional", chooses=True),

    # The sixth five (10.10.2026), read with the table before anything
    # was built.
    #
    # Points at a player every night; a Minion it points at has no
    # ability while the Preacher lives and works (info.PreacherChoice,
    # solver.a_preacher_silences_its_minions). A Goon notices.
    _c("Preacher", "preacher", "Preacher", "townsfolk", {EVERY},
       nights="every", chooses=True),
    # Once a game it points at a living player, and a Damsel it finds
    # becomes a Townsfolk not in play (info.HuntsmanChoice). Woken every
    # night until then (waking._huntsman). "[+the Damsel]": in place of a
    # Townsfolk, unless the Damsel is in the bag anyway.
    _c("Huntsman", "huntsman", "Huntsman", "townsfolk",
       {FIRST, EVERY, SOMETIMES}, nights="conditional", chooses=True,
       setup=({"townsfolk": -1, "outsider": 1}, {}), brings=("Damsel",)),
    # One player is drunk all game, even after it dies; it may guess once
    # who, and learns the Demon or somebody who is not
    # (info.PuzzlemasterGuess, solver.a_puzzlemaster_keeps_one_drunk).
    _c("Puzzlemaster", "puzzlemaster", "Puzzlemaster", "outsider", {NEVER}),
    # "[X Outsiders]": any number at all, whatever else would move it. On
    # night X every Townsfolk is poisoned until dusk, if the Xaan lives
    # and works then (solver.a_xaan_poisons_the_town).
    _c("Xaan", "xaan", "Xaan", "minion", {NEVER},
       setup=tuple({"townsfolk": -k, "outsider": k} if k else {}
                   for k in (0, 1, -1, 2, -2, 3, -3, 4, -4))),
    # Executed, it explodes: all but three die, the Demon among the three,
    # and one more by pointing (info.BoomdandyExploded).
    _c("Boomdandy", "boomdandy", "Boomdandy", "minion", {NEVER}),
]


# Who can stop somebody else's ability working.
#
# Only the Mathematician asks, and for a narrow reason: its number is the
# size of the impairment set, so an *unmodelled* character that droisons
# means the solver cannot know how much went wrong and has to say
# nothing. An unmodelled character that only produces information it
# cannot check — a Savant, an Artist — costs it nothing, and a guard
# written as "any unmodelled character at all" would silence the
# Mathematician for good on a script that has one.
#
# Listed here rather than set on each entry, so the whole set can be read
# at once and nothing is missed by being spelled differently.
IMPAIRS = frozenset({
    # Handed the wrong token, and impaired every night of the game.
    "Drunk", "Marionette", "Lunatic",
    # Trouble Brewing and Bad Moon Rising.
    "Poisoner", "Sailor", "Goon", "Courtier", "Minstrel", "Innkeeper",
    # Sects & Violets.
    "Philosopher", "NoDashii", "Vigormortis", "Sweetheart", "SnakeCharmer",
    # It can create any of the above.
    "PitHag",
    # Experimental: poisoned, drunk or without an ability, by these.
    "Widow", "Preacher", "Puzzlemaster", "Xaan",
})

CHARACTERS = {c.key: c for c in _TB + _SV + _UNMODELLED + _FABLED
              + _EXPERIMENTAL}
CHARACTERS = {k: c._replace(impairs=k in IMPAIRS)
              for k, c in CHARACTERS.items()}


def _night_order():
    """Where each character acts, from `data/roles.json`.

    Read rather than written down here, because it is somebody else's
    data and hand-copying a hundred and thirty pairs of numbers is a way
    to introduce errors that nothing would catch.

    A character the file does not know keeps zero, which means "does not
    act" — safe, and visible, since a character that should act and does
    not will show up the moment a game is played.
    """
    import json
    import pathlib as _p
    path = _p.Path(__file__).resolve().parent.parent / "data" / "roles.json"
    if not path.exists():
        return {}
    out = dict(_NOT_IN_THE_FILE)
    for entry in json.loads(path.read_text()):
        got = entry.get("id")
        if got:
            out[got] = (int(entry.get("firstNight") or 0),
                        int(entry.get("otherNight") or 0))
    return out


# Characters newer than the vendored file. Checked on 28.09.2026: the
# upstream file is byte-for-byte the one in data/, and it has no Ogre.
#
# The Ogre acts late on the first night, after the Spy (49) and before
# the General (50) in the official order. There is no whole number in
# between, so it shares the General's slot — nothing on any script here
# holds both, and the file wins the moment a refresh brings the real one.
#
# The Steward, the Knight and the Shugenja are missing the same way
# (05.10.2026). In the publisher's current order the first night runs
# ... Seamstress, Steward, Knight, Noble, Balloonist, Shugenja, Village
# Idiot, Bounty Hunter, Nightwatchman ... — so the first two belong
# between 43 and 44 and the third between 45 and 46. They share the slot
# that follows them, for the Ogre's reason: all three only read, nothing
# acts between them and their neighbour, and nothing else is renumbered.
_NOT_IN_THE_FILE = {
    "ogre": (50, 0),
    "steward": (44, 0),
    "knight": (44, 0),
    "shugenja": (46, 0),
    # The Organ Grinder is newer than the file too. It reads nothing and
    # nothing at night reads it, so where it sits changes nothing; it
    # shares the Fearmonger's slots (10.10.2026). The Vizier needs none:
    # it never wakes for itself.
    "organgrinder": (26, 17),
    # The publisher's other nights run ... Vortox, Lord of Typhon,
    # Vigormortis, Ojo, Al-Hadikhia ... — after the Vigormortis at 32 and
    # before anything the file numbers 33, so it shares the Vigormortis's
    # slot. Only one of them is the Demon on any night.
    "ojo": (0, 32),
}


_ORDER = _night_order()
CHARACTERS = {
    k: c._replace(first_night=_ORDER.get(c.id, (0, 0))[0],
                  other_night=_ORDER.get(c.id, (0, 0))[1])
    for k, c in CHARACTERS.items()}
BY_ID = {c.id: c for c in CHARACTERS.values()}


def normalise(name):
    """Turn anything a script might write into a catalogue id."""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def lookup(name):
    """Find a character by id, key or display name. None if unknown."""
    wanted = normalise(name)
    got = BY_ID.get(wanted)
    if got is not None:
        return got
    for character in CHARACTERS.values():
        if wanted in (normalise(character.key), normalise(character.name)):
            return character
    return None
