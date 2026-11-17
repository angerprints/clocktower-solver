"""python3 eigene_wahl.py SCRIPT OUT BASELINE.jsonl — dmeas with every recorded
choice read only from the seat that holds the character in the world (in
memory only). Today `_by` reads anybody's row when one seat holds it, so a
liar's Innkeeper or Sailor row binds the real one (BMR seed 175, 17.11.2026).
Runs only the seeds whose claims name the Innkeeper, the Sailor or the
Acrobat; the others cannot change. Run from a checkout's root."""
import json
import runpy
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

S._by = lambda holders, seat: seat

script, out, base = sys.argv[1:4]
ROLES = ("Innkeeper", "Sailor", "Acrobat")
seeds = []
for line in open(base):
    r = json.loads(line)
    claims = r["claims"].values() if isinstance(r["claims"], dict) else r["claims"]
    if any(c in ROLES for c in claims):
        seeds.append(r["seed"])
for seed in seeds:
    sys.argv = ["dmeas.py", script, out, str(seed), str(seed + 1), "4"]
    runpy.run_path("messung/dmeas.py", run_name="__main__")
