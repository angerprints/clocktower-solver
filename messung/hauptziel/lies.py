"""Which measured games had a good player lying? python3 lies.py SCRIPT FILE"""
import sys, random, json, collections
sys.path[:0] = [".", "tests"]
import simulate, claims as C
from botc import scripts
sc = {"BMR": scripts.BAD_MOON_RISING, "SV": scripts.SECTS_AND_VIOLETS, "TB": scripts.TROUBLE_BREWING}[sys.argv[1]]
recs = {json.loads(l)["seed"]: json.loads(l) for l in open(sys.argv[2])}
KIND = {}
grp = collections.defaultdict(lambda: [0, 0, 0, 0.0])   # games, top, valid0, dp sum
for seed, r in sorted(recs.items()):
    rng = random.Random(seed); n = [7, 8, 9, 10][seed % 4]
    d, h = simulate.play(n, rng, nights=4, script=sc)
    cl, wk, notes = C.claims_for(d, rng, script=sc)
    kinds = set()
    for s, t in notes.items():
        if "for no reason" in t: kinds.add("Chaos")
        elif "hiding behind" in t and not simulate.TEAM[d.roles[s]] in ("minion", "demon"): kinds.add("versteckt")
    key = "+".join(sorted(kinds)) or "keine"; KIND[seed] = key
    g = grp[key]; g[0] += 1; g[1] += r["rank"] == 1; g[2] += r["valid"] == 0; g[3] += r["dp"]
json.dump(KIND, open(sys.argv[2] + ".kinds.json", "w"))
for k, (g, t, z, dp) in grp.items():
    print(f"{k:18s} Partien {g:4d}  vorn {t:4d} ({100*t/g:.0f} %)  ohne Welt {z:3d}  Ø Dämon {dp/g:.1f} %")
