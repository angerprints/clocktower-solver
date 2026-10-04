"""If the solver knew the Demon type: rank of the true seat by P(seat = that type)."""
import sys, random, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
sc = scripts.BAD_MOON_RISING
seeds = [json.loads(l) for f in ("dt_a", "dt_b") for l in open(f"{sys.argv[1]}/{f}.jsonl")]
part = int(sys.argv[2]); out = open(f"{sys.argv[1]}/dc_{part}.jsonl", "w")
for i, rec in enumerate(seeds):
    if i % 2 != part: continue
    seed = rec["seed"]; rng = random.Random(seed); n = [7, 8, 9, 10][seed % 4]
    d, h = simulate.play(n, rng, nights=4, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                   votes=dict(d.votes), nominations=dict(d.nominations), **d.record(told=False))
    r = S.analyze(st, rng=random.Random(1))
    demon = d.demon_at("D4"); kind = rec["kind"]
    per = [dict(row["roles"]).get(kind, 0.0) for row in r["rows"]]
    rank = 1 + sum(x > per[demon] + 1e-9 for x in per)
    dp = [row["demon_pct"] for row in r["rows"]]
    out.write(json.dumps(dict(seed=seed, kind=kind, crank=rank, rank=1 + sum(x > dp[demon] + 1e-9 for x in dp),
                              shroud=rec["shroud"])) + "\n"); out.flush()
