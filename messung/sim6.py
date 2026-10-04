"""Truth sweep with the quiet nights told. python3 sim6.py SCRIPT N NIGHTS [START]"""
import sys, random, time, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
from test_js_worlds import EASTER
which = {"TB": scripts.TROUBLE_BREWING, "BMR": scripts.BAD_MOON_RISING,
         "SV": scripts.SECTS_AND_VIOLETS, "EASTER": scripts.from_json(EASTER)}
name, N, nights = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
sc = which[name]
tot = collections.Counter(); bad = collections.defaultdict(list); t0 = time.time()
for seed in range(start, start + N):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    last = min(nights, d.game_ends_after or nights)
    quiet = {k for k in range(2, last + 1) if not d.died_on(f"N{k}")}
    w = World(tuple(d.roles), tuple(d.believes))
    def state(**extra):
        return GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                         votes=dict(d.votes), nominations=dict(d.nominations), **d.record(), **extra)
    plain = S.explanation_cost(w, state()) is not None
    told = S.explanation_cost(w, state(quiet_nights=set(quiet))) is not None
    kind = d.role_at(d.demon_at(f"N{last}"), f"N{last}") if d.demon_at(f"N{last}") is not None else "?"
    key = (kind, len(quiet))
    tot[key] += 1; tot[("alle", "")] += 1
    if quiet: tot[("mit stiller Nacht", "")] += 1
    if plain and not told:
        bad[key].append(seed); bad[("alle", "")].append(seed)
    if not plain: bad[("schon vorher", "")].append(seed)
print(f"{name}: {N} Partien ab {start}, {nights} Nächte ({time.time()-t0:.0f} s)")
for key in sorted(tot, key=str):
    print("  ", key, "Partien", tot[key], "verworfen wegen stiller Nacht", len(bad[key]), bad[key][:12])
print("   schon ohne stille Nächte verworfen:", len(bad[("schon vorher", "")]))
