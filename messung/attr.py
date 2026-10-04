"""Which excuses are on offer for a quiet night, world by world, weighted."""
import sys, random, json, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S, deaths as D
from botc.info import GameState
from botc.worlds import iter_worlds, Timeline
sc = scripts.BAD_MOON_RISING
agg = collections.defaultdict(lambda: collections.Counter()); tot = collections.Counter(); games = 0
free_nights = collections.defaultdict(collections.Counter)
for seed in map(int, sys.argv[1:]):
    rng = random.Random(seed); n = [7, 8, 9, 10][seed % 4]
    d, h = simulate.play(n, rng, nights=4, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    quiet = {k for k in (2, 3, 4) if not d.died_on(f"N{k}")}
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h), votes=dict(d.votes),
                   nominations=dict(d.nominations), **d.record(told=False), quiet_nights=set(quiet))
    if S.pilot_size(st, False) > 40000: continue
    games += 1
    for w in iter_worlds(n, st.claims, getattr(st, "certainties", None), False, S.forced_roles(st), getattr(st, "wakes", None), st.script, getattr(st, "fabled", ())):
        c = S.explanation_cost(w, st)
        if c is None: continue
        kind = next(r for r in w.roles if simulate.TEAM[r] == "demon")
        tot[kind] += c
        if kind == "Zombuul": continue
        nfree = 0
        for k in sorted(quiet):
            causes = [x for x in D.causes_on(w, st, k) if x.kind == D.DEMON and x.must_fire]
            if not causes:
                agg[kind]["(kein Pflicht-Kill in dieser Nacht)"] += c; nfree += 1; continue
            best = {}
            for cause in causes:
                for target in cause.seats:
                    for sh in D.shields_on(w, st, k, target, cause.kind):
                        best[sh.by] = max(best.get(sh.by, 0), sh.cost)
            free = sorted(by for by, cost in best.items() if cost >= 1.0)
            if free: nfree += 1
            label = "frei: " + "+".join(free) if free else ("nur bezahlt: " + "+".join(sorted(best)) if best else "nichts")
            agg[kind][label] += c
        free_nights[kind][f"{nfree} von {len(quiet)} stillen Nächten gratis"] += c
print("Partien:", games, " Gewicht je Typ:", {k: round(v, 2) for k, v in tot.items()})
for kind in agg:
    s = sum(agg[kind].values())
    print("\n", kind, "— stille Nächte nach angebotener Erklärung (Anteil am Gewicht):")
    for label, v in agg[kind].most_common(14): print(f"   {100*v/s:5.1f}%  {label}")
    s2 = sum(free_nights[kind].values())
    for label, v in sorted(free_nights[kind].items()): print(f"   ## {100*v/s2:5.1f}%  {label}")
