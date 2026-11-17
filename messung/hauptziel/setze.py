"""python3 setze.py NAME=WERT[,NAME=WERT] SKRIPT OUT ERSTE LETZTE — dmeas mit
geänderten Solver-Konstanten (nur im Speicher). Aus dem Wurzelordner eines
Checkouts starten."""
import sys
import runpy

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

for pair in sys.argv[1].split(","):
    name, value = pair.split("=")
    assert hasattr(S, name), name
    setattr(S, name, float(value))
sys.argv = ["dmeas.py", sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], "4"]
runpy.run_path("messung/dmeas.py", run_name="__main__")
