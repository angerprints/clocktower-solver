"""What carries a must-kill Demon through a quiet night?
   python3 quiet.py OUT.jsonl PART VARIANTS(comma) [all]
   Patches the excuse step of deaths._account_for in memory only."""
import sys, random, json, inspect, itertools, time
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S, deaths as D
from botc.info import GameState
from botc.worlds import World

src = inspect.getsource(D._account_for)
old1 = '''            for target in sorted(cause.seats):
                for shield in shields_on(world, state, night, target,
                                         cause.kind):
                    if shield.needs is not None and shield.needs in impaired:
                        continue          # it was impaired, so it held nothing
                    grown.append((
                        cost * shield.cost, set(impaired),
                        working | ({shield.needs} if shield.needs is not None
                                   else set()),
                        used, before,
                    ))
'''
new1 = '''            for xc, ximp, xwk in EXCUSES(world, state, night, cause, impaired, working, 0):
                grown.append((cost * xc, set(impaired) | ximp, working | xwk, used, before))
'''
old2 = '''                grown.append((cost, impaired, working, used, before))
                continue
'''
new2 = '''                for xc, ximp, xwk in EXCUSES(world, state, night, cause, impaired, working, used[cause.name]):
                    grown.append((cost * xc, set(impaired) | ximp, working | xwk, used, before))
                continue
'''
assert src.count(old1) == 1 and src.count(old2) == 1
VARIANT = "base"

def singles(world, state, night, cause, impaired, skip=()):
    out = []
    for target in sorted(cause.seats):
        for sh in D.shields_on(world, state, night, target, cause.kind):
            if sh.needs is not None and sh.needs in impaired: continue
            if sh.by in skip: continue
            out.append((target, sh))
    return out

def EXCUSES(world, state, night, cause, impaired, working, used):
    v = VARIANT
    demon_kill = cause.kind == D.DEMON
    if used > 0:
        if v != "logic" or not demon_kill or cause.capacity != 2 or used >= 2:
            return [(1.0, set(), set())]
    skip = ()
    if demon_kill and v.startswith("no_"):
        skip = {"no_dead": ("already dead",), "no_tealady": ("Tea Lady",), "no_fool": ("Fool",),
                "no_sailor": ("Sailor",), "no_innkeeper": ("Innkeeper",), "no_exorcist": ("Exorcist",),
                "no_free": ("Tea Lady", "Fool", "Sailor", "Innkeeper", "Exorcist")}[v]
    got = singles(world, state, night, cause, impaired, skip)
    if v != "logic" or not demon_kill:
        return [(sh.cost, set(), {sh.needs} if sh.needs is not None else set()) for _t, sh in got]
    phase = f"N{night}"
    demon = world.demon_at(phase)
    role = world.role_at(demon, phase) if demon is not None else None
    out = {}
    def add(cost, imp, wk):
        key = (round(cost, 9), frozenset(imp), frozenset(wk))
        out[key] = (cost, set(imp), set(wk))
    # stopped at the source: the Demon itself drunk or poisoned
    if demon is not None and demon not in working:
        add(1.0, {demon}, set())
    if role == "Pukka":
        # what dies tonight was poisoned last night: its own ability protects nobody
        got = [(t, sh) for t, sh in got if sh.needs != t]
    wk = lambda sh: {sh.needs} if sh.needs is not None else set()
    if cause.capacity == 2 and used == 0:
        for t, sh in got:
            if sh.by == "Exorcist": add(sh.cost, set(), wk(sh))
        rest = [(t, sh) for t, sh in got if sh.by != "Exorcist"]
        for (t1, s1), (t2, s2) in itertools.combinations(rest, 2):
            if t1 != t2: add(s1.cost * s2.cost, set(), wk(s1) | wk(s2))
    elif cause.capacity == 2 and used == 1:
        for t, sh in got:
            if sh.by != "Exorcist": add(sh.cost, set(), wk(sh))
    else:
        for t, sh in got: add(sh.cost, set(), wk(sh))
    return list(out.values())

ns = D.__dict__
ns["EXCUSES"] = EXCUSES
exec(src.replace(old1, new1).replace(old2, new2), ns)

sc = scripts.BAD_MOON_RISING
out = open(sys.argv[1], "a"); part = int(sys.argv[2]); variants = sys.argv[3].split(",")
everything = len(sys.argv) > 4
todo = 0
for seed in range(400):
    rng = random.Random(seed); n = [7, 8, 9, 10][seed % 4]
    d, h = simulate.play(n, rng, nights=4, script=sc)
    if d.game_ends_after is not None: continue
    quiet = sum(1 for k in (2, 3, 4) if not d.died_on(f"N{k}"))
    if quiet < 2 and not everything: continue
    todo += 1
    if todo % 2 != part: continue
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    demon = d.demon_at("D4"); kind = d.role_at(demon, "D4")
    rec = dict(seed=seed, n=n, kind=kind, quiet=quiet, shroud=demon not in d.alive_at("D4"), v={})
    for v in variants:
        VARIANT = v
        st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                       votes=dict(d.votes), nominations=dict(d.nominations), **d.record(),
                       quiet_nights={k for k in (2, 3, 4) if not d.died_on(f"N{k}")})
        truth = World(tuple(d.roles), tuple(d.believes))
        t = time.time()
        ok = S.explanation_cost(truth, st)
        r = S.analyze(st, rng=random.Random(1))
        mass = {k: 0.0 for k in ("Zombuul", "Pukka", "Shabaloth", "Po")}
        for row in r["rows"]:
            for role, pct in row["roles"]:
                if role in mass: mass[role] += pct
        pc = [row["demon_pct"] for row in r["rows"]]
        rec["v"][v] = dict(ok=ok, valid=r["valid"], mass=mass,
                           dp=pc[demon] if pc else None,
                           rank=(1 + sum(x > pc[demon] + 1e-9 for x in pc)) if pc else None,
                           t=round(time.time() - t, 1))
    out.write(json.dumps(rec) + "\n"); out.flush()
