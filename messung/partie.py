"""One mixed game of the gate, looked at closely.

    python3 messung/partie.py SEED CHARACTER[,CHARACTER...] [NIGHTS]

The same game `messung/tor.py` plays for that seed and those characters.
Prints the deal, the world the solver is handed (`deal.world()`), the
changes, every row the table heard, the cost of the true world with all
rows and with none, and a smallest set of rows that still makes the true
world impossible (rows are dropped one at a time while it stays so).
"""
import copy
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "tools")]
import claims as C                                            # noqa: E402
import play_games                                             # noqa: E402
import simulate                                               # noqa: E402
from botc import solver as S                                  # noqa: E402
from botc.info import GameState                               # noqa: E402

seed = int(sys.argv[1])
must = tuple(sys.argv[2].split(","))
nights = int(sys.argv[3]) if len(sys.argv) > 3 else 4
n = [7, 8, 9, 10, 11][seed % 5]
rng = random.Random(seed)
script = play_games.an_awkward_script(rng, must_have=must)
deal, heard = simulate.play(n, rng, nights=nights, script=script)
claims, wakes, _ = C.claims_for(deal, rng, script=script)
record = deal.record()


def cost(rows):
    state = GameState(n_players=n, script=script, claims=claims, wakes=wakes,
                      infos=list(rows), votes=dict(deal.votes),
                      nominations=dict(deal.nominations),
                      **copy.deepcopy(record))
    return S.explanation_cost(deal.world(), state)


print("players", n)
print("dealt   ", deal.roles)
print("believes", deal.believes)
print("world   ", deal.world())
print("changes ", deal.changes)
print("sides   ", deal.side_changes)
print("summoned", getattr(deal, "summoned", None),
      "marionette", getattr(deal, "marionette_made", None))
print("record  ", record)
for row in heard:
    print("  ", row)
print("cost, all rows:", cost(heard))
print("cost, no rows: ", cost([]))
if cost(heard) is None:
    rows = list(heard)
    i = 0
    while i < len(rows):
        fewer = rows[:i] + rows[i + 1:]
        if cost(fewer) is None:
            rows = fewer
        else:
            i += 1
    print("smallest impossible set:")
    for row in rows:
        print("  ", row)
