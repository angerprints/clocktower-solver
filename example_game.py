"""Example game - replace this with your real one.

Players are indexed 0..n-1 in seating order around the circle, so
player 0 and player n-1 are neighbours (matters for Empath and Chef).
"""

# Makes the import work no matter which folder you run this from.
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botc.info import (GameState, Washerwoman, Librarian, Investigator,
                       Chef, Empath, FortuneTeller, Undertaker,
                       Ravenkeeper, SlayerShot)
from botc.solver import solve, print_report

state = GameState(
    n_players=7,
    names=["Ada", "Ben", "Cem", "Dana", "Eli", "Finn", "Gina"],
    claims={
        0: "Washerwoman",
        1: "Librarian",
        2: "Investigator",
        3: "Chef",
        4: "Empath",
        5: "FortuneTeller",
        6: "Undertaker",
    },
    deaths={},          # e.g. {4: "N2", 7: "D2"}  N = night, D = execution
    infos=[
        Washerwoman(night=1, player=0, a=3, b=5, role="Chef"),
        Librarian(night=1, player=1, a=None, b=None, role=""),  # "no Outsiders"
        Investigator(night=1, player=2, a=4, b=6, role="Poisoner"),
        Chef(night=1, player=3, count=0),
        Empath(night=1, player=4, count=1),
        FortuneTeller(night=1, player=5, a=0, b=6, yes=False),
    ],
)

all_worlds, valid = solve(state)
print(f"Legal role assignments in total: {len(all_worlds)}")
print_report(valid, state)
