import sys, random, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
sc = scripts.SECTS_AND_VIOLETS
N = int(sys.argv[1]); nights = int(sys.argv[2])
kinds = collections.Counter(); odd = []
for seed in range(N):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    rec = d.record() if hasattr(d, "record") else {"deaths": dict(d.deaths)}
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h), votes=dict(d.votes), nominations=dict(d.nominations), **rec)
    if S.explanation_cost(World(tuple(d.roles), tuple(d.believes)), st) is not None: continue
    claimed = S.barber_claimants(st)
    swaps = getattr(d, "barber_swaps", {})
    hid = [p for p, at in d.deaths.items() if d.role_at(p, at) == "Barber" and p not in claimed]
    tag = ("swap" if swaps else "no swap") + ", " + ("barber hid" if hid else "barber claimed or none")
    kinds[tag] += 1
    if not (swaps and hid): odd.append(seed)
print(N, nights, dict(kinds), odd[:20])
