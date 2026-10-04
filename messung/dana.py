import sys, json, collections, statistics as st
rows = [json.loads(l) for l in open(sys.argv[1])]
key = sys.argv[2] if len(sys.argv) > 2 else "kind"
# "offen" as a third argument: only games still open after night four —
# not ended by the Demon's execution, and at least three players alive.
# Without it the decided games are in, and the numbers look better than
# they are (found 04.10.2026).
if len(sys.argv) > 3 and sys.argv[3] == "offen":
    rows = [r for r in rows if r["ended"] is None and r["alive"] > 2]
def line(name, g):
    g2 = [r for r in g if r["rank"] is not None]
    n = len(g)
    if not g2: print(f"{name:28} n={n} (keine Welten)"); return
    r1 = sum(r["rank"] == 1 for r in g2); solo = sum(r["rank"] == 1 and r["tied"] == 1 for r in g2)
    r2 = sum(r["rank"] <= 2 for r in g2); r3 = sum(r["rank"] <= 3 for r in g2)
    lost = sum(not r["ok"] for r in g); none = n - len(g2)
    dp = [r["dp"] for r in g2]
    base = st.mean(100 / r["n"] for r in g2)
    print(f"{name:28} n={n:4} vorn {r1:4} ({100*r1/n:4.0f}%) allein {solo:4} top2 {r2:4} ({100*r2/n:4.0f}%) top3 {r3:4} ({100*r3/n:4.0f}%) "
          f"Ø {st.mean(dp):5.1f}% Median {st.median(dp):5.1f}% Zufall {base:4.1f}% verloren {lost} ohneWelt {none} sampled {sum(r['sampled'] for r in g)} Øt {st.mean(r['t'] for r in g):.1f}s")
groups = collections.defaultdict(list)
for r in rows:
    k = r[key] if key in r else eval(key, {}, r)
    groups[k].append(r)
line("alle", rows)
for k in sorted(groups, key=str): line(str(k), groups[k])
