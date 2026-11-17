"""python3 final3.py MESSUNG.jsonl — Kalibrierung und Treffer an Morgen mit 3 Lebenden."""
import json, sys, collections
def order(ph):
    k, n = ph[0], int(ph[1:])
    return n * 3 + {"N": 0, "D": 1, "E": 2}[k]
def living(r):
    for L in range(1, 9):
        m = order(f"D{L}")
        alive = [s for s in range(r['n']) if str(s) not in (r['deaths'] or {})
                 or all(order(ph) > m for ph in ([r['deaths'][str(s)]] if isinstance(r['deaths'][str(s)], str) else r['deaths'][str(s)]))]
        if len(alive) == r['alive']:
            return alive
    return None
rs = [json.loads(l) for l in open(sys.argv[1])]
pred = collections.Counter(); act = collections.Counter(); n = collections.Counter()
hit = tot = 0
for r in rs:
    if r['alive'] != 3: continue
    al = living(r)
    if al is None: continue
    tot += 1; hit += r['rank'] == 1
    for s in al:
        c = r['claims'].get(str(s), '(keine)')
        pred[c] += r['pcts'][s] / 100; act[c] += s == r['demon']; n[c] += 1
print(f"Morgen mit 3 Lebenden: {tot}, Dämon vorn {hit} ({100*hit/max(tot,1):.0f} %)")
for c in sorted(n, key=lambda c: -n[c]):
    if n[c] < 15: continue
    print(f"  {c:14s} Sitze {n[c]:3d}  erwartet {pred[c]:5.1f}  Dämon {act[c]:3d}  Verhältnis {act[c]/max(pred[c],1e-9):.2f}")
