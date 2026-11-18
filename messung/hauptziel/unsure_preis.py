"""python3 unsure_preis.py PRICE MODUS SKRIPT OUT GRUNDMESSUNG.jsonl —
final3_unsure.py with a good seat's lie costing PRICE instead of
TOWNSFOLK_LIE_PENALTY (0.02). 0.11 is the simulator's rate: a good player
lies one time in ten (18.11.2026). In memory only."""
import runpy
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

S.TOWNSFOLK_LIE_PENALTY = float(sys.argv[1])
sys.argv = ["final3_unsure.py"] + sys.argv[2:]
runpy.run_path("messung/hauptziel/final3_unsure.py", run_name="__main__")
