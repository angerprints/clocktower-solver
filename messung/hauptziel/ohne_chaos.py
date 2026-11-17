"""python3 ohne_chaos.py SKRIPT OUT GRUNDMESSUNG.jsonl — Obergrenze: In den
Partien mit Chaos-Lüge sagt der Lügner die Wahrheit (behauptet seinen
wahren Charakter, meldet seine echten Zeilen). Nur diese Partien werden
neu gerechnet. Aus dem Wurzelordner eines Checkouts starten."""
import json
import sys
import runpy

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import claims as C                                        # noqa: E402

orig = C.claims_for


def honest(deal, rng, script=None, **kw):
    cl, wk, notes = orig(deal, rng, script=script, **kw)
    for seat, why in list(notes.items()):
        if "for no reason" in why:
            cl[seat] = deal.roles[seat]
            # Kept apart in the notes so dmeas still files it under Chaos,
            # but no longer "for no reason": its rows are heard.
            notes[seat] = "good, told the truth this time"
    return cl, wk, notes


C.claims_for = honest
script, out, base = sys.argv[1], sys.argv[2], sys.argv[3]
seeds = [json.loads(l)["seed"] for l in open(base)
         if "Chaos" in json.loads(l)["lie"]]
for seed in seeds:
    sys.argv = ["dmeas.py", script, out, str(seed), str(seed + 1), "4"]
    runpy.run_path("messung/dmeas.py", run_name="__main__")
