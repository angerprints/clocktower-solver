"""Is the true world kept with quiet nights told, under each variant?
   python3 quietsweep.py NIGHTS N VARIANTS(comma)     Bad Moon Rising only
   Variants: base (the solver as it is), source (base plus "the Demon
   itself was stopped"), logic (the strict reading of quiet.py).
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
        base = [(sh.cost, set(), {sh.needs} if sh.needs is not None else set()) for _t, sh in got]
        if v == "source" and demon_kill:
            dm = world.demon_at(f"N{night}")
            if dm is not None and dm not in working:
                base.append((1.0, {dm}, set()))
        return base
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
nights, N = int(sys.argv[1]), int(sys.argv[2]); variants = sys.argv[3].split(",")
bad = {v: [] for v in variants}
for seed in range(N):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                   votes=dict(d.votes), nominations=dict(d.nominations), **d.record())
    truth = World(tuple(d.roles), tuple(d.believes))
    for v in variants:
        VARIANT = v
        if S.explanation_cost(truth, st) is None: bad[v].append(seed)
for v in variants: print(f"BMR {nights} Nächte {N} Partien, Variante {v}: verworfen {len(bad[v])} {bad[v][:12]}")
