"""Where does the truth die? python3 sim4d.py SCRIPT NIGHTS SEED"""
import sys, random
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S, deaths as D, impairment
from botc.info import GameState
from botc.worlds import World, Timeline
from test_js_worlds import EASTER
which = {"TB": scripts.TROUBLE_BREWING, "BMR": scripts.BAD_MOON_RISING,
         "SV": scripts.SECTS_AND_VIOLETS, "EASTER": scripts.from_json(EASTER)}
sc = which[sys.argv[1]]; nights = int(sys.argv[2]); seed = int(sys.argv[3])
n = [7, 8, 9, 10, 11][seed % 5]
rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
cl, wk, _ = C.claims_for(d, rng, script=sc)
st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
               votes=dict(d.votes), nominations=dict(d.nominations), **d.record())
w = World(tuple(d.roles), tuple(d.believes))
print("claims", cl); print("wakes", wk)
chains = S.possible_timelines(w, st)
print("chains", len(chains))
for chain, cost in chains[:6]:
    view = Timeline(w, chain) if chain else w
    got = S._plain_failures(view, st, None)
    print(" chain", chain, cost, "-> failures", None if got[0] is None else dict(got[0]), "must_work", got[3] if len(got) > 3 else None)
    if got[0] is None: continue
    acc = S._night_accounts(view, st)
    print("   accounts", len(acc) if acc else acc)
    for k in range(1, nights + 1):
        print("   night", k, "causes", [(c.name, c.kind, sorted(c.seats), c.capacity, c.must_fire) for c in D.causes_on(view, st, k)],
              "sources", [(s.name, sorted(s.seats)) for s in impairment.sources_on(view, st, k)])
    print("   explain:", S._explain(view, st))
