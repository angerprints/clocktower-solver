"""Summarise a dmeas jsonl: python3 ana.py FILE"""
import json, sys, collections
recs = [json.loads(l) for l in open(sys.argv[1])]
n = len(recs)
top = sum(r["rank"] == 1 for r in recs if r["rank"])
two = sum(r["rank"] <= 2 for r in recs if r["rank"])
three = sum(r["rank"] <= 3 for r in recs if r["rank"])
avg = sum(r["dp"] for r in recs if r["dp"] is not None) / n
lost = sum(not r["ok"] for r in recs)
print(f"{n} Partien: vorn {top} ({100*top/n:.0f} %), unter 2 {two}, unter 3 {three}, Ø {avg:.1f} %, echte Welt verloren {lost}")
miss = [r for r in recs if r["rank"] and r["rank"] > 1]
why = collections.Counter()
for r in miss:
    pcts = r["pcts"]; best = max(range(len(pcts)), key=lambda i: pcts[i])
    who = r["roles"][best]
    tags = []
    tags.append("Dämon tot" if not r["demon_alive"] else "Dämon lebt")
    if r["kind"] != r["dealt"] or r["changes"]: tags.append("Wechsel")
    tags.append("vorn: " + who)
    why[" | ".join(tags)] += 1
for k, v in why.most_common(): print(f"  {v:3d}  {k}")
print("vorn-Rollen:", collections.Counter(r["roles"][max(range(len(r['pcts'])), key=lambda i: r['pcts'][i])] for r in miss).most_common())
print("Abstand Dämon zu vorn (Median):", sorted(round(max(r['pcts']) - r['dp'], 1) for r in miss)[len(miss)//2] if miss else None)
