"""Why does a told quiet night cost the true world? python3 klass.py NIGHTS N"""
import sys, random, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
sc = scripts.BAD_MOON_RISING; nights = int(sys.argv[1]); N = int(sys.argv[2])
cats = collections.Counter(); ex = collections.defaultdict(list)
for seed in range(N):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    rec = d.record(); quiet = set(rec["quiet_nights"]); w = World(tuple(d.roles), tuple(d.believes))
    def ok(q, days=None):
        r = dict(rec); r["quiet_nights"] = set(q); r["days_done"] = rec["days_done"] if days is None else days
        st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                       votes=dict(d.votes), nominations=dict(d.nominations), **r)
        return S.explanation_cost(w, st) is not None
    if ok(quiet): continue
    if not ok(set(), set()): cats["schon ohne verloren"] += 1; continue
    if ok(quiet, set()): cats["nur wegen der Tage"] += 1; ex["nur wegen der Tage"].append(seed); continue
    culprit = [k for k in sorted(quiet) if ok(quiet - {k})]
    if not culprit: cats["mehrere Nächte zusammen"] += 1; ex["mehrere Nächte zusammen"].append(seed); continue
    for k in culprit[:1]:
        ph = f"N{k}"; dem = d.demon_at(ph); kind = d.role_at(dem, ph)
        g = d.goon_first.get(k); gp = d.goon_first.get(k - 1)
        dead_demon = d.mastermind_day is not None and k == d.mastermind_day
        if dead_demon: why = "Nacht vor dem Zusatztag (Dämon tot)"
        elif g and g[0] == dem: why = f"{kind}: wählte in dieser Nacht den Schläger zuerst"
        elif kind == "Pukka" and gp and gp[0] == dem: why = "Pukka: wählte in der Nacht davor den Schläger zuerst"
        elif not d.working(dem, k): why = f"{kind}: anders gestört"
        elif kind == "Pukka" and k >= 2 and not d.working(dem, k - 1): why = "Pukka: in der Nacht davor anders gestört"
        else: why = f"{kind}: anderes"
        cats[why] += 1; ex[why].append((seed, k))
print(f"BMR {nights} Nächte, {N} Partien:")
for why, c in cats.most_common(): print(f"  {c:3}  {why}   {ex[why][:8]}")
