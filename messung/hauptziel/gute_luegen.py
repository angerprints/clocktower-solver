"""python3 gute_luegen.py PRICE SCRIPT OUT BASELINE.jsonl [ALL] — dmeas with
"good players may lie" switched on for every seat (the page's switch), a
good seat's lie costing PRICE instead of TOWNSFOLK_LIE_PENALTY; in memory
only. Runs only the seeds whose last open morning has three alive, unless
ALL is given. Run from a checkout's root (18.11.2026)."""
import functools
import json
import runpy
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

price, script, out, base = sys.argv[1:5]
everything = len(sys.argv) > 5
S.TOWNSFOLK_LIE_PENALTY = float(price)
S.analyze = functools.partial(S.analyze, allow_good_lies=True)
seeds = [r["seed"] for r in map(json.loads, open(base))
         if everything or r["alive"] == 3]
for seed in seeds:
    sys.argv = ["dmeas.py", script, out, str(seed), str(seed + 1), "4"]
    runpy.run_path("messung/dmeas.py", run_name="__main__")
