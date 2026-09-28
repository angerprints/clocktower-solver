"""Shared scaffolding for the test suite.

The point of these helpers is that a test should read like the situation
it describes. `game(7, claims=..., infos=[...])` then `evil(state, 3)`,
not fifteen lines of dictionary building.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from botc.info import GameState                       # noqa: E402
from botc.roles import TEAM, TOWNSFOLK, is_evil       # noqa: E402
from botc.solver import solve, summarize              # noqa: E402
from botc.worlds import enumerate_worlds              # noqa: E402

# A tidy spread of claims for the common table sizes: enough Townsfolk to
# fill the good seats, plus Outsider claims where the setup needs them.
SPREAD = {
    7:  ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
         "FortuneTeller", "Undertaker"],
    9:  ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
         "FortuneTeller", "Undertaker", "Recluse", "Saint"],
    12: ["Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
         "FortuneTeller", "Undertaker", "Monk", "Ravenkeeper", "Virgin",
         "Recluse", "Saint"],
}


def spread(n):
    """The default claim list for n seats."""
    return {i: r for i, r in enumerate(SPREAD[n])}


def game(n, claims=None, **kw):
    """Build a GameState. `claims` defaults to the standard spread."""
    if claims is None:
        claims = spread(n) if n in SPREAD else {}
    return GameState(n_players=n, claims=claims, **kw)


def solved(state, **kw):
    """(valid worlds, per-seat rows)."""
    _all, valid = solve(state, **kw)
    return valid, summarize(valid, state)


def evil(state, seat, **kw):
    return solved(state, **kw)[1][seat]["evil_pct"]


def role_pct(rows, seat, role):
    """Weighted share of worlds giving this seat that exact role."""
    return dict(rows[seat]["roles"]).get(role, 0.0)


def counts(world):
    """{team: how many seats} for one world."""
    out = {"townsfolk": 0, "outsider": 0, "minion": 0, "demon": 0}
    for r in world.roles:
        out[TEAM[r]] += 1
    return out


def tokens_used(world):
    """Every role token on the board, including the Drunk's."""
    used = list(world.roles)
    used += [b for b in world.believes if b]
    return used


class SolverTest(unittest.TestCase):
    """Assertions phrased for probabilities rather than exact floats."""

    def assertPct(self, actual, expected, tol=0.5, msg=""):
        self.assertAlmostEqual(actual, expected, delta=tol, msg=msg)

    def assertBetween(self, actual, low, high, msg=""):
        self.assertTrue(low <= actual <= high,
                        msg or f"{actual:.2f} not within [{low}, {high}]")

    def assertRises(self, before, after, msg=""):
        self.assertGreater(after, before + 0.01,
                           msg or f"expected a rise, got {before:.2f} → {after:.2f}")

    def assertFalls(self, before, after, msg=""):
        self.assertLess(after, before - 0.01,
                        msg or f"expected a fall, got {before:.2f} → {after:.2f}")


__all__ = ["SolverTest", "game", "spread", "solved", "evil", "role_pct",
           "counts", "tokens_used", "enumerate_worlds", "is_evil", "TEAM",
           "TOWNSFOLK", "SPREAD"]
