"""python3 final3_unsure.py MODUS SKRIPT OUT GRUNDMESSUNG.jsonl — Versuch:
An einem Morgen mit drei Lebenden gelten Behauptungen als „nicht vertraut“
(Sitz kann jeden Charakter halten, gute Lüge kostet TOWNSFOLK_LIE_PENALTY).
MODUS: lebende (nur die drei Lebenden) oder alle (jeder Sitz mit Behauptung).
Nur die Partien der Grundmessung mit drei Lebenden werden neu gerechnet."""
import json
import sys
import runpy

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

mode = sys.argv[1]
orig = S.analyze


def analyze(st, *a, **kw):
    alive = sys._getframe(1).f_globals.get("alive")
    if alive is not None and len(alive) == 3:
        seats = alive if mode == "lebende" else list(st.claims)
        st.certainties = dict(st.certainties or {})
        for p in seats:
            if p in st.claims:
                st.certainties[p] = "unsure"
    return orig(st, *a, **kw)


S.analyze = analyze
script, out, base = sys.argv[2], sys.argv[3], sys.argv[4]
seeds = [json.loads(l)["seed"] for l in open(base) if json.loads(l)["alive"] == 3]
for seed in seeds:
    sys.argv = ["dmeas.py", script, out, str(seed), str(seed + 1), "4"]
    runpy.run_path("messung/dmeas.py", run_name="__main__")
