"""Calibration: python3 cal.py FILE — predicted demon share vs truth, by bin and by claim."""
import json, sys, collections
recs = [json.loads(l) for l in open(sys.argv[1])]
bins = collections.defaultdict(lambda: [0.0, 0, 0])
claim = collections.defaultdict(lambda: [0.0, 0, 0])
for r in recs:
    for s, p in enumerate(r["pcts"]):
        truth = 1 if s == r["demon"] else 0
        b = min(int(p // 10), 9)
        bins[b][0] += p / 100; bins[b][1] += truth; bins[b][2] += 1
        c = r["claims"].get(str(s), "(keine)")
        claim[c][0] += p / 100; claim[c][1] += truth; claim[c][2] += 1
print("Bereich | Sitze | erwartet Dämon | wirklich Dämon")
for b in sorted(bins):
    e, t, k = bins[b]
    print(f"{b*10:3d}-{b*10+10:3d} % | {k:4d} | {e:6.1f} | {t:4d}")
print("\nBehauptung | Sitze | erwartet | wirklich | Verhältnis")
for c, (e, t, k) in sorted(claim.items(), key=lambda x: -x[1][0]):
    print(f"{c:14s} {k:4d} {e:6.1f} {t:4d}  {t/e if e else 0:.2f}")
