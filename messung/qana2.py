import sys, json, statistics as st
S = sys.argv[1]
rows = {}
for f in ("all0", "all1", "ab0", "ab1"):
    try:
        for l in open(f"{S}/told/{f}.jsonl"):
            r = json.loads(l); rows.setdefault(r["seed"], dict(r, v={}))["v"].update(r["v"])
    except FileNotFoundError: pass
dm = {r["seed"]: r for r in map(json.loads, open(f"{S}/dm_bmr.jsonl"))}
dt = {r["seed"]: r for f in ("dt_a", "dt_b") for r in map(json.loads, open(f"{S}/{f}.jsonl"))}
for s, r in rows.items():
    r["v"]["untold"] = dict(ok=1, valid=dm[s]["valid"], mass=dt[s]["mass"], dp=dm[s]["dp"], rank=dm[s]["rank"], t=dm[s]["t"])
rows = [r for r in rows.values() if dm[r["seed"]]["alive"] > 2]   # the game still open
K = ("Shabaloth", "Po", "Pukka", "Zombuul")
def share(x, t): return 100 * x["mass"][t] / max(sum(x["mass"].values()), 1e-9)
def table(name, g, variants):
    print(f"\n== {name} (n={len(g)})")
    print(f"{'Variante':12}" + "".join(f"{k:>10}" for k in K) + "    vorn  top2 top3  Ødp  verloren ohneWelt  Øt")
    for v in variants:
        h = [r for r in g if v in r["v"]]
        if not h: continue
        hv = [r["v"][v] for r in h]
        live = [x for x in hv if x["rank"] is not None and sum(x["mass"].values()) > 0]
        m = [st.mean(share(x, t) for x in live) for t in K] if live else [0] * 4
        print(f"{v:12}" + "".join(f"{x:10.1f}" for x in m) + f"   {sum(x['rank'] == 1 for x in live):3}/{len(h):3} {sum(x['rank'] <= 2 for x in live):4} {sum(x['rank'] <= 3 for x in live):4} {st.mean(x['dp'] for x in live) if live else 0:5.1f}  {sum(x['ok'] is None for x in hv):3}  {len(hv) - len(live):3}   {st.mean(x['t'] for x in hv):.1f}")
A = ["untold", "base", "logic"]
V = ["untold", "base", "no_dead", "no_tealady", "no_fool", "no_sailor", "no_innkeeper", "no_exorcist", "no_free", "logic"]
done = [r for r in rows if "base" in r["v"]]
table("alle Partien", done, A)
for k in K: table(f"wahrer Dämon {k}", [r for r in done if r["kind"] == k], A)
z = [r for r in done if r["kind"] == "Zombuul"]
table("Zombuul scheintot", [r for r in z if r["shroud"]], A)
table("Zombuul sichtbar", [r for r in z if not r["shroud"]], A)
for q in (0, 1, 2, 3):
    table(f"{q} stille Nächte, alle Dämonen", [r for r in done if r["quiet"] == q], A)
ab = [r for r in rows if "no_free" in r["v"]]
table("Ablation: 2-3 stille Nächte, wahrer Dämon Zombuul", [r for r in ab if r["kind"] == "Zombuul"], V)
table("Ablation: 3 stille Nächte, wahrer Dämon Zombuul", [r for r in ab if r["kind"] == "Zombuul" and r["quiet"] == 3], V)
table("Ablation: 2-3 stille Nächte, anderer Dämon", [r for r in ab if r["kind"] != "Zombuul"], V)
for k in ("Shabaloth", "Pukka", "Po"):
    table(f"Ablation: 2-3 stille Nächte, wahrer Dämon {k}", [r for r in ab if r["kind"] == k], V)
# calibration: share of games that really are type T vs mean belief, by quiet nights
print("\n== Kalibrierung Zombuul nach stillen Nächten (wirklich / untold / base / logic)")
for q in (0, 1, 2, 3):
    g = [r for r in done if r["quiet"] == q]
    if not g: continue
    real = 100 * sum(r["kind"] == "Zombuul" for r in g) / len(g)
    def bel(v):
        xs = [share(r["v"][v], "Zombuul") for r in g if r["v"][v]["rank"] is not None and sum(r["v"][v]["mass"].values()) > 0]
        return st.mean(xs)
    print(f"  still {q}: n={len(g):3} wirklich {real:5.1f}  nicht gesagt {bel('untold'):5.1f}  gesagt {bel('base'):5.1f}  streng {bel('logic'):5.1f}")
