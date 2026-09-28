"""A script is a name and a selection of characters. That is all.

The three published scripts are three such selections, and there is no
mechanism behind them that a homebrew script does not also get. Custom
scripts are the general case; Trouble Brewing is a special one only in
being the first thing implemented.
"""

import json
from typing import NamedTuple

from .catalogue import CHARACTERS, Character, lookup, normalise


class Script(NamedTuple):
    name: str
    keys: tuple
    author: str = ""
    # Characters the file named that the catalogue has never heard of.
    # Kept rather than dropped, so a script can say what it is missing.
    unknown: tuple = ()

    # ------------------------------------------------------------------
    def characters(self):
        return [CHARACTERS[k] for k in self.keys]

    @property
    def seated_keys(self):
        """The characters that can actually be dealt to a seat."""
        return [k for k in self.keys if CHARACTERS[k].seated]

    @property
    def fabled(self):
        """Characters the Storyteller puts on the table, not in the bag.

        Being on the script only means one is available. Which are in play
        is decided per game and shown to everybody, so it is told to the
        solver rather than discovered by it.
        """
        return [k for k in self.keys if not CHARACTERS[k].seated]

    def by_team(self, team):
        return [k for k in self.keys if CHARACTERS[k].team == team]

    @property
    def townsfolk(self):
        return self.by_team("townsfolk")

    @property
    def outsiders(self):
        return self.by_team("outsider")

    @property
    def minions(self):
        return self.by_team("minion")

    @property
    def demons(self):
        return self.by_team("demon")

    @property
    def setup_modifiers(self):
        """{key: shifts} for the characters on this script that move the bag."""
        return {c.key: c.setup for c in self.characters()
                if c.setup and c.seated}

    def wake_table(self):
        return {c.key: c.wake for c in self.characters()}

    # ------------------------------------------------------------------
    def fabled_in_play(self, chosen):
        """Which of the chosen Fabled are actually on this script."""
        available = set(self.fabled)
        return tuple(k for k in (chosen or ()) if k in available)

    def unmodelled(self):
        """Characters whose abilities the solver does not reason about.

        Both kinds together, because a caller asking "what can I not
        trust here" wants one list. Use `handling()` to tell them apart.
        """
        return [c for c in self.characters() if not c.modelled]

    def handling(self):
        """How far each character is reasoned about, in three groups.

        "Recorded but not weighed" and "not built yet" look the same from
        the outside and are completely different things: a Savant is
        finished — its pair of statements can be anything at all, so the
        words are kept and shown and that is as far as it will ever go —
        while a Vortox is simply not started. Showing them in one list
        tells somebody the wrong thing about both.
        """
        from .catalogue import PARTLY
        out = {"recorded": [], "coming": [], "nothing to read": []}
        for c in self.characters():
            if c.modelled:
                continue
            if c.handled == PARTLY:
                out["recorded"].append(c)
            elif c.settled:
                out["nothing to read"].append(c)
            else:
                out["coming"].append(c)
        return out

    def is_playable(self):
        """Enough of a bag to deal from? Every team needs somebody."""
        return bool(self.townsfolk and self.minions and self.demons)

    def too_small_for(self, n_players):
        """Which teams run out of characters at this table size.

        A script with three Townsfolk cannot fill a nine-player game,
        and the search would simply return nothing with no explanation.
        Returns [] when the bag is deep enough.
        """
        from .roles import SETUP
        if n_players not in SETUP:
            return []
        wanted = dict(zip(("townsfolk", "outsider", "minion", "demon"),
                          SETUP[n_players]))
        # A setup-changer can only ever ask for more, so take the worst case.
        for shifts in self.setup_modifiers.values():
            for shift in shifts:
                for team, delta in shift.items():
                    wanted[team] = max(wanted[team], wanted[team] + delta)
        short = []
        for team, need in wanted.items():
            have = len(self.by_team(team))
            if have < need:
                short.append({"team": team, "need": need, "have": have})
        return short

    def complaints(self, n_players=None):
        """Everything worth telling somebody before they rely on this."""
        out = []
        for short in (self.too_small_for(n_players) if n_players else []):
            out.append({
                "kind": "too small",
                "characters": [],
                "text": f"only {short['have']} {short['team']} characters, "
                        f"and a {n_players}-player game needs "
                        f"{short['need']}. Nothing can be dealt.",
            })
        if self.unknown:
            out.append({
                "kind": "unknown",
                "characters": list(self.unknown),
                "text": "not in the catalogue at all, so they were left out "
                        "of the bag. Team counts will be wrong if they were "
                        "meant to be in play.",
            })
        # Three kinds of "not reasoned about", said separately, because
        # they mean different things to somebody deciding what to trust.
        groups = self.handling()
        if groups["coming"]:
            out.append({
                "kind": "unmodelled",
                "characters": [c.name for c in groups["coming"]],
                "text": "in the bag and can be claimed, but their abilities "
                        "are not reasoned about yet. Anything that depends "
                        "on them is guesswork.",
            })
        if groups["recorded"]:
            out.append({
                "kind": "recorded",
                "characters": [c.name for c in groups["recorded"]],
                "text": "what they say is written down and shown, but not "
                        "weighed — it can be anything at all, and checking "
                        "arbitrary claims about a board is beyond this. "
                        "That is as far as they go.",
            })
        if groups["nothing to read"]:
            out.append({
                "kind": "nothing to read",
                "characters": [c.name for c in groups["nothing to read"]],
                "text": "nothing they do leaves a mark the solver could "
                        "read, so there is nothing to model. Mark the seat "
                        "yourself if the table works it out.",
            })
        if not self.is_playable():
            out.append({
                "kind": "unplayable",
                "characters": [],
                "text": "this script has no complete set of teams, so there "
                        "is nothing to deal.",
            })
        return out


def from_ids(name, ids, author=""):
    """Build a script from whatever a file called its characters."""
    keys, unknown = [], []
    for entry in ids:
        found = lookup(entry)
        if found is None:
            unknown.append(str(entry))
        elif found.key not in keys:
            keys.append(found.key)
    return Script(name=name or "Untitled script", keys=tuple(keys),
                  author=author, unknown=tuple(unknown))


def from_json(text_or_data, fallback_name="Uploaded script"):
    """Read the format Storytellers actually pass around.

    A list whose entries are either character ids as plain strings, or
    objects with an `id`. One of those objects may be `_meta`, carrying
    the script's name and author. Homebrew characters appear as full
    objects; they are recognised by id if the catalogue knows them and
    reported as unknown if not.
    """
    data = json.loads(text_or_data) if isinstance(text_or_data, (str, bytes)) \
        else text_or_data

    if isinstance(data, dict):              # some tools wrap it in an object
        data = data.get("characters") or data.get("roles") or []

    name, author, ids = fallback_name, "", []
    for entry in data:
        if isinstance(entry, dict):
            if normalise(entry.get("id", "")) == "meta":
                name = entry.get("name") or name
                author = entry.get("author") or author
                continue
            ids.append(entry.get("id") or entry.get("name") or "")
        else:
            ids.append(entry)
    return from_ids(name, ids, author)


def _script(name, keys):
    return Script(name=name, keys=tuple(keys))


TROUBLE_BREWING = _script("Trouble Brewing", [
    "Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
    "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin",
    "Slayer", "Soldier", "Mayor",
    "Butler", "Drunk", "Recluse", "Saint",
    "Poisoner", "Spy", "ScarletWoman", "Baron",
    "Imp",
])

# Bad Moon Rising, as far as it is modelled. Named so a board can be set
# up on it; the characters not yet reasoned about say so when it loads.
BAD_MOON_RISING = _script("Bad Moon Rising", [
    "Grandmother", "Sailor", "Chambermaid", "Exorcist", "Innkeeper",
    "Gambler", "Gossip", "Courtier", "Professor", "Minstrel",
    "TeaLady", "Pacifist", "Fool",
    "Tinker", "Moonchild", "Goon", "Lunatic",
    "Godfather", "DevilsAdvocate", "Assassin", "Mastermind",
    "Zombuul", "Pukka", "Shabaloth", "Po",
])

# Taken from the official file rather than typed out. Bad Moon Rising was
# built by hand once and came out with thirty-eight characters instead of
# twenty-five, which inflated the search fivefold and had the solver being
# optimised against a number that was wrong.
SECTS_AND_VIOLETS = _script("Sects & Violets", [
    "Clockmaker", "Dreamer", "SnakeCharmer", "Mathematician", "Flowergirl",
    "TownCrier", "Oracle", "Savant", "Seamstress", "Philosopher", "Artist",
    "Juggler", "Sage",
    "Mutant", "Sweetheart", "Barber", "Klutz",
    "EvilTwin", "Witch", "Cerenovus", "PitHag",
    "FangGu", "Vigormortis", "NoDashii", "Vortox",
])

# Publication order, and it is load-bearing: the page offers them in
# whatever order this is written.
BUILT_IN = {TROUBLE_BREWING.name: TROUBLE_BREWING,
            BAD_MOON_RISING.name: BAD_MOON_RISING,
            SECTS_AND_VIOLETS.name: SECTS_AND_VIOLETS}
DEFAULT = TROUBLE_BREWING
