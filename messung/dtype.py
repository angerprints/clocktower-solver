"""Which Demon does the solver think is in play? python3 dtype.py OUT.jsonl FIRST LAST"""
import sys, random, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
sc = scripts.BAD_MOON_RISING
out = open(sys.argv[1], "a")
for seed in range(int(sys.argv[2]), int(sys.argv[3])):
    rng = random.Random(seed); n = [7, 8, 9, 10][seed % 4]
    d, h = simulate.play(n, rng, nights=4, script=sc)
    if d.game_ends_after is not None: continue
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                   votes=dict(d.votes), nominations=dict(d.nominations), **d.record(told=False))
    r = S.analyze(st, rng=random.Random(1))
    demon = d.demon_at("D4"); kind = d.role_at(demon, "D4")
    mass = {k: 0.0 for k in ("Zombuul", "Pukka", "Shabaloth", "Po")}
    for row in r["rows"]:
        for role, pct in row["roles"]:
            if role in mass: mass[role] += pct
    here = dict(r["rows"][demon]["roles"])
    nd = {k: sorted(d.died_on(f"N{k}")) for k in range(2, 5)}
    ed = {k: sorted(d.died_on(f"E{k}", f"D{k}")) for k in range(1, 4)}
    out.write(json.dumps(dict(seed=seed, n=n, kind=kind, mass=mass, here=here.get(kind, 0.0),
        dp=r["rows"][demon]["demon_pct"], shroud=demon not in d.alive_at("D4"),
        demon_killed={str(k): list(v) for k, v in d.demon_killed.items()}, nd=nd, ed=ed,
        roles=list(d.roles))) + "\n"); out.flush()
