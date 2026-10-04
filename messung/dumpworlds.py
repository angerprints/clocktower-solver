import sys, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import app
from botc import solver as S
from botc.worlds import iter_worlds
name = sys.argv[1]
case = next(c for c in json.load(open("tests/fixtures/conformance.json"))["cases"] if c["name"] == name)
got = {}; real = app.analyze
def spy(state, *a, **k):
    got["st"] = state; raise SystemExit
app.analyze = spy
try: app.run_solve(case["payload"])
except SystemExit: pass
app.analyze = real
st = got["st"]
out = []
for w in iter_worlds(st.n_players, st.claims, getattr(st, "certainties", None), False, S.forced_roles(st), getattr(st, "wakes", None), st.script, getattr(st, "fabled", ())):
    out.append([list(w.roles), list(w.believes), S.explanation_cost(w, st)])
json.dump({"payload": case["payload"], "worlds": out}, open(sys.argv[2], "w"))
print(len(out), "worlds,", sum(1 for o in out if o[2] is not None), "possible")
