"""How often is the Demon found? python3 dmeas.py SCRIPT OUT.jsonl FIRST LAST NIGHTS"""
import sys, random, time, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
sc = {"BMR": scripts.BAD_MOON_RISING, "SV": scripts.SECTS_AND_VIOLETS,
      "TB": scripts.TROUBLE_BREWING}[sys.argv[1]]
first, last, nights = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
out = open(sys.argv[2], "a")
for seed in range(first, last):
    rng = random.Random(seed); n = [7, 8, 9, 10][seed % 4]
    d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                   votes=dict(d.votes), nominations=dict(d.nominations), **d.record())
    last_night = min(nights, d.game_ends_after or nights)
    end = f"D{last_night}"
    demon = d.demon_at(end)
    if demon is None: demon = d.demon_at(f"N{last_night}")
    dealt = next(r for r in d.roles if simulate.TEAM[r] == "demon")
    kind = d.role_at(demon, end)
    alive = sorted(d.alive_at(end))
    t = time.time()
    ok = S.explanation_cost(World(tuple(d.roles), tuple(d.believes)), st) is not None
    r = S.analyze(st, rng=random.Random(1))
    dt = time.time() - t
    rows = r["rows"] or []
    dp = rows[demon]["demon_pct"] if rows else None
    pcts = [row["demon_pct"] for row in rows]
    rank = (1 + sum(p > dp + 1e-9 for p in pcts)) if rows else None
    tied = sum(abs(p - dp) <= 1e-9 for p in pcts) if rows else None
    # among the living only: who would you execute next?
    lrank = (1 + sum(pcts[p] > dp + 1e-9 for p in alive)) if rows and demon in alive else None
    rec = dict(seed=seed, n=n, dealt=dealt, kind=kind, demon=demon, ended=d.game_ends_after, ended_at=d.ended_at,
               demon_alive=demon in alive, alive=len(alive), ok=ok, valid=r["valid"],
               sampled=bool(r.get("sampled")), dp=dp, rank=rank, tied=tied, lrank=lrank,
               top=max(pcts) if pcts else None, ep=rows[demon]["evil_pct"] if rows else None,
               claim=cl.get(demon), roles=list(d.roles), claims={str(k): v for k, v in cl.items()},
               deaths={str(k): v for k, v in d.deaths.items()}, changes=[list(map(str, c)) for c in d.changes],
               pcts=[round(p, 2) for p in pcts], t=round(dt, 1))
    out.write(json.dumps(rec) + "\n"); out.flush()
