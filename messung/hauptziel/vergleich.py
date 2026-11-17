"""python3 vergleich.py VARIANTE.jsonl [GRUND.jsonl] — Dämon vorn, getrennt nach Info-Behauptung."""
import json, sys, collections
INFO = {"Washerwoman", "Librarian", "Investigator", "Chef", "Empath",
        "FortuneTeller", "Undertaker", "Ravenkeeper"}
v = {r['seed']: r for r in map(json.loads, open(sys.argv[1]))}
g = {r['seed']: r for r in map(json.loads, open(sys.argv[2] if len(sys.argv) > 2 else "/home/claude/out/TB_600_bluff.jsonl"))}
c = collections.Counter()
for s, r in v.items():
    k = "Info" if r['claim'] in INFO else "anderes"
    c[k, 'n'] += 1; c[k, 'g'] += g[s]['rank'] == 1; c[k, 'v'] += r['rank'] == 1
    c['alle', 'n'] += 1; c['alle', 'g'] += g[s]['rank'] == 1; c['alle', 'v'] += r['rank'] == 1
    c['alle', 'neu'] += r['rank'] == 1 and g[s]['rank'] != 1
    c['alle', 'weg'] += r['rank'] != 1 and g[s]['rank'] == 1
    c['alle', 'lost'] += not r['ok']
for k in ("Info", "anderes", "alle"):
    print(f"  Dämon behauptet {k:8s} n={c[k,'n']:3d}  Grund {c[k,'g']:3d}  Variante {c[k,'v']:3d}")
print(f"  neu vorn {c['alle','neu']}, nicht mehr vorn {c['alle','weg']}, wahre Welt verloren {c['alle','lost']}")
