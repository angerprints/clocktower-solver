import sys, random
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
sc = scripts.BAD_MOON_RISING; nights = int(sys.argv[1])
for seed in map(int, sys.argv[2:]):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                   votes=dict(d.votes), nominations=dict(d.nominations), **d.record())
    w = World(tuple(d.roles), tuple(d.believes))
    out = []
    for cap in (96, 128, 160, 200, 256, 400):
        S.ACCOUNTS_KEPT = cap
        out.append(S.explanation_cost(w, st))
    print(seed, out)
