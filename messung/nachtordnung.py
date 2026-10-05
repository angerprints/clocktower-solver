"""The simulator's night order read off the character a seat holds NOW, in memory only."""
import sys, random
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, nightwalk
from botc import scripts
from botc.catalogue import CHARACTERS
from test_js_worlds import EASTER
def fixed(d, night):
    field = "first_night" if night == 1 else "other_night"
    def slot(seat):
        what = d.believes[seat] or d.role_at(seat, f"N{night}")
        if d.role_at(seat, f"N{night}") == "Lunatic": what = "Lunatic"
        if what == "Philosopher" and seat in d.philosophies and night > 1: what = d.philosophies[seat]
        got = getattr(CHARACTERS[what], field, 0) if what in CHARACTERS else 0
        return (got if got else 10_000, seat)
    return sorted(range(d.n), key=slot)
real = simulate._in_night_order
def games(sc, N, nights):
    out = []
    for seed in range(N):
        n = [7, 8, 9, 10, 11][seed % 5]
        d, h = simulate.play(n, random.Random(seed), nights=nights, script=sc)
        dev = 0
        for night in range(2, nights + 1):
            if d.game_ends_after is not None and night > d.game_ends_after: continue
            got = nightwalk.walk(d, night, nightwalk.hidden_from(d, night, h))
            dev += got.died != d.died_on(f"N{night}") or bool(got.untold)
        out.append((repr((d.roles, sorted(d.deaths.items()), d.changes, [repr(r) for r in h])), dev))
    return out
for name, sc, N, nights in (("SV", scripts.SECTS_AND_VIOLETS, 6000, 4), ("SV", scripts.SECTS_AND_VIOLETS, 3000, 6),
                            ("BMR", scripts.BAD_MOON_RISING, 2000, 6), ("TB", scripts.TROUBLE_BREWING, 3000, 4),
                            ("EASTER", scripts.from_json(EASTER), 3000, 4)):
    simulate._in_night_order = real; a = games(sc, N, nights)
    simulate._in_night_order = fixed; b = games(sc, N, nights)
    diff = [i for i in range(N) if a[i][0] != b[i][0]]
    print(f"{name} {N} games, {nights} nights: {len(diff)} games play differently; walk deviates in {sum(x[1] for x in a)} nights as it is, {sum(x[1] for x in b)} with the order fixed; e.g. {diff[:8]}")
