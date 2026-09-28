"""Characters this solver cannot honestly reason about.

Everything else in the package rests on two assumptions, and a handful of
characters take one of them away:

  * **The bag is known.** The distribution for a table size is fixed, a
    listed modifier may shift it, and every seat holds exactly one of the
    characters on the script. All the pruning comes from this.
  * **The teams are the usual size.** One Demon, a couple of Minions, the
    rest good. Every count in the search is bounded by that.

A character that breaks either one does not make the solver slightly less
accurate. It makes the whole world set wrong, quietly, while the output
looks exactly as confident as ever. So they are named here rather than
half-supported.

Two kinds, and they need different handling:

  BREAKS_THE_BAG    The setup itself may be a lie, so no legal world
                    exists to find. The saving grace is that this has a
                    visible signature — nothing fits — and when a board
                    produces that on a script containing one of these,
                    saying so is more useful than saying nothing.

  BREAKS_THE_TEAMS  The counts are wrong from the first night and there
                    is no signature at all. The board will look perfectly
                    solvable and every number will be wrong. There is
                    nothing to detect, so the only honest thing is to
                    refuse before starting.
"""

BREAKS_THE_BAG = "breaks the bag"
BREAKS_THE_TEAMS = "breaks the teams"


UNSUPPORTED = {
    "Atheist": {
        "kind": BREAKS_THE_BAG,
        "short": "the Storyteller may have broken the rules",
        "why": ("With an Atheist in play the Storyteller is allowed to "
                "break the rules, and there may be no evil players at "
                "all. Nothing the solver enumerates is a legal world, so "
                "there is no honest answer to give."),
        "signal": ("A board that fits nothing is the signature. It is not "
                   "proof — a mis-entered reading or a good player lying "
                   "does the same thing — but it is worth raising."),
    },
    "Legion": {
        "kind": BREAKS_THE_TEAMS,
        "short": "most of the table is evil",
        "why": ("Legion replaces the usual one-Demon-and-some-Minions "
                "split with most of the table being evil Demons. Every "
                "count the search prunes on is wrong, and nothing about "
                "the board would look unusual."),
        "signal": None,
    },
    "Riot": {
        "kind": BREAKS_THE_TEAMS,
        "short": "every Minion is a Demon",
        "why": ("Riot turns every Minion into a Demon and rewrites how "
                "days work. The team counts and the death rules both stop "
                "holding."),
        "signal": None,
    },
}


def unsupported_on(script):
    """Which named characters on this script the solver cannot handle.

    Accepts a Script or any collection of character keys.
    """
    keys = set(getattr(script, "keys", script))
    return {name: entry for name, entry in UNSUPPORTED.items()
            if name in keys}


def refuses(script):
    """Characters that make solving dishonest before it even starts."""
    return {name: entry for name, entry in unsupported_on(script).items()
            if entry["kind"] == BREAKS_THE_TEAMS}


def could_explain_nothing_fitting(script):
    """Characters whose signature is a board that fits no world at all."""
    return {name: entry for name, entry in unsupported_on(script).items()
            if entry["kind"] == BREAKS_THE_BAG}
