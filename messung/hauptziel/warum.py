"""python3 warum.py SCRIPT SEED — for one game's last open morning: the
true world's weight against the best world for each living seat as Demon."""
import sys, random, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
sc = {"BMR": scripts.BAD_MOON_RISING, "SV": scripts.SECTS_AND_VIOLETS,
      "TB": scripts.TROUBLE_BREWING}[sys.argv[1]]
seed = int(sys.argv[2]); nights = 4
rng = random.Random(seed); n = [7, 8, 9, 10][seed % 4]
d, h = simulate.play(n, rng, nights=nights, script=sc)
cl, wk, notes = C.claims_for(d, rng, script=sc)
last = min(nights, d.game_ends_after or nights)
told = C.told_table(d, h, cl, notes, last, seed)
st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=told,
               votes=dict(d.votes), nominations=dict(d.nominations), **d.record(told=False))
end = f"D{last}"; alive = sorted(d.alive_at(end))
for s in range(n):
    print(s, d.roles[s], cl.get(s), notes.get(s), "lebt" if s in alive else f"tot {d.deaths.get(s)}")
for r in told: print("  ", r)
w0 = d.world()
print("wahr: prior", S.prior_weight(w0, st), "cost", S.explanation_cost(w0, st))
_a, valid, _l = S.solve_or_repair(st)
best = collections.defaultdict(list); tot = collections.Counter(); T = 0
for w in valid:
    c = S.explanation_cost(w, st)
    if c is None: continue
    p = S.prior_weight(w, st); wt = p * c; T += wt
    dem = [s for s in range(n) if simulate.TEAM.get(w.roles[s]) == "demon"]
    for s in dem: tot[s] += wt
    best[tuple(dem)].append((wt, p, c, w.roles))
print("Dämon-Anteil", {s: round(100 * v / T, 1) for s, v in tot.items()})
for k in sorted(best, key=lambda k: -sum(x[0] for x in best[k]))[:5]:
    xs = sorted(best[k], reverse=True)[:2]
    for wt, p, c, roles in xs:
        print(k, f"wt {wt:.4f} prior {p:.4f} cost {c:.4f}", roles)

def parts(w):
    return dict(bag=S.bag_weight(w, st), nacht=S.prior_weight(w, st) / S.bag_weight(w, st))
print("wahr", parts(w0))
from botc.worlds import World
for k in sorted(best, key=lambda k: -sum(x[0] for x in best[k]))[:2]:
    wt, p, c, roles = max(best[k])
    ww = next(w for w in valid if tuple(w.roles) == tuple(roles))
    print(k, parts(ww))
