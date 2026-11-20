"""python3 setze_drei.py NAME=WERT[,NAME=WERT] SKRIPT OUT GRUNDMESSUNG.jsonl —
setze.py, aber nur für die Partien, deren letzter offener Morgen drei
Lebende hat (19.11.2026). Aus dem Wurzelordner eines Checkouts starten."""
import json
import runpy
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

for pair in sys.argv[1].split(","):
    name, value = pair.split("=")
    assert hasattr(S, name), name
    setattr(S, name, float(value))
script, out, base = sys.argv[2:5]
for seed in [r["seed"] for r in map(json.loads, open(base)) if r["alive"] == 3]:
    sys.argv = ["dmeas.py", script, out, str(seed), str(seed + 1), "4"]
    runpy.run_path("messung/dmeas.py", run_name="__main__")
