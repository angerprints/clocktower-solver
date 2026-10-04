"""Compares dm_preis_1.jsonl (the solver as it is) with a priced run.
   python3 messung/preis_vergleich.py 0.5 0.25"""
import json, sys, collections
def load(p): return {r["seed"]: r for l in open(f"messung/daten/morgen/dm_preis_{p}.jsonl") for r in [json.loads(l)]}
base = load("1")
for p in sys.argv[1:]:
    got = load(p)
    seeds = [s for s in base if s in got]
    print(f"price {p}: {len(seeds)} games; first {sum(base[s]['rank']==1 for s in seeds)} -> {sum(got[s]['rank']==1 for s in seeds)}; top3 {sum(base[s]['rank']<=3 for s in seeds)} -> {sum(got[s]['rank']<=3 for s in seeds)}; true world kept {sum(base[s]['ok'] for s in seeds)} -> {sum(got[s]['ok'] for s in seeds)}; mean dp {sum(base[s]['dp'] for s in seeds)/len(seeds):.1f} -> {sum(got[s]['dp'] for s in seeds)/len(seeds):.1f}")
    for kind in ("Zombuul", "Po", "Pukka", "Shabaloth"):
        ks = [s for s in seeds if base[s]["kind"] == kind]
        tm0 = sum(base[s]["mass"][kind] for s in ks)/len(ks); tm1 = sum(got[s]["mass"][kind] for s in ks)/len(ks)
        up = sum(got[s]["rank"] < base[s]["rank"] for s in ks); dn = sum(got[s]["rank"] > base[s]["rank"] for s in ks)
        print(f"   {kind:10s} n={len(ks):3d} first {sum(base[s]['rank']==1 for s in ks):3d} -> {sum(got[s]['rank']==1 for s in ks):3d}   belief in the true type {tm0:.0f} -> {tm1:.0f}%   true seat {sum(base[s]['dp'] for s in ks)/len(ks):.0f} -> {sum(got[s]['dp'] for s in ks)/len(ks):.0f}%   rank better {up}, worse {dn}")
    zs = [s for s in seeds if base[s]["kind"] == "Zombuul"]
    for lab, pick in (("Zombuul alive on board", lambda r: r["demon_alive"]), ("counted dead, board 2", lambda r: not r["demon_alive"] and r["alive"] == 2), ("counted dead, board 3+", lambda r: not r["demon_alive"] and r["alive"] >= 3)):
        ks = [s for s in zs if pick(base[s])]
        print(f"   {lab:24s} n={len(ks):3d} first {sum(base[s]['rank']==1 for s in ks)} -> {sum(got[s]['rank']==1 for s in ks)}  top3 {sum(base[s]['rank']<=3 for s in ks)} -> {sum(got[s]['rank']<=3 for s in ks)}")
