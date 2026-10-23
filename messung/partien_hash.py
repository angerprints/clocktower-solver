"""One line per played game, to see which games another version plays
differently (the night order of 23.10.2026).

    python3 messung/partien_hash.py SCRIPT N NIGHTS > out.txt

Run it in two checkouts and compare the files line by line: a line that
differs is a game the simulator plays differently.
"""
import hashlib
import random
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import simulate  # noqa: E402
from botc import scripts  # noqa: E402
from test_js_worlds import EASTER  # noqa: E402
from test_experimental_9 import NINE_BMR  # noqa: E402

WHICH = {"TB": scripts.TROUBLE_BREWING, "BMR": scripts.BAD_MOON_RISING,
         "SV": scripts.SECTS_AND_VIOLETS, "EASTER": scripts.from_json(EASTER),
         "XNINEB": NINE_BMR}

name, n_games, nights = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for seed in range(n_games):
    n = [7, 8, 9, 10, 11][seed % 5]
    d, h = simulate.play(n, random.Random(seed), nights=nights,
                         script=WHICH[name])
    text = repr((d.roles, sorted(d.deaths.items()), d.changes,
                 [repr(r) for r in h]))
    print(seed, hashlib.sha1(text.encode()).hexdigest()[:16])
