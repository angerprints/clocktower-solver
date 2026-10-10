"""Why is the truth rejected? python3 sim4c.py SCRIPT NIGHTS SEED..."""
import sys, random
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
from test_js_worlds import EASTER
which = {"TB": scripts.TROUBLE_BREWING, "BMR": scripts.BAD_MOON_RISING,
         "SV": scripts.SECTS_AND_VIOLETS, "EASTER": scripts.from_json(EASTER)}
# The scripts made for the experimental characters.
from test_experimental import SPY, VORTOX
from test_experimental_2 import OJO, OJO_BMR
from test_experimental_3 import WRAITH, WRAITH_BMR
from test_experimental_4 import FOUR, FOUR_BMR
from test_experimental_5 import FIVE, FIVE_BMR
from test_experimental_6 import SIX, SIX_BMR
which.update({"XSPY": SPY, "XVORTOX": VORTOX, "XOJO": OJO, "XOJOB": OJO_BMR,
              "XWRAITH": WRAITH, "XWRAITHB": WRAITH_BMR,
         "XFOUR": FOUR, "XFOURB": FOUR_BMR,
         "XFIVE": FIVE, "XFIVEB": FIVE_BMR,
         "XSIX": SIX, "XSIXB": SIX_BMR})
sc = which[sys.argv[1]]; nights = int(sys.argv[2])
for seed in map(int, sys.argv[3:]):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    def mk(infos, rec=None, wakes=wk):
        return GameState(n_players=n, script=sc, claims=cl, wakes=wakes, infos=list(infos),
                         votes=dict(d.votes), nominations=dict(d.nominations), **(rec or d.record()))
    w = World(tuple(d.roles), tuple(d.believes))
    print("=====", seed, list(enumerate(d.roles)), "believes", [x for x in enumerate(d.believes) if x[1]])
    print("  record", d.record())
    print("  walked", d.walked_because, "raised", d.resurrections, "prof", d.professor_chose, "spared", d.spared)
    print("  changes", d.changes, "poisoned", d.poisoned, "pukka", d.pukka_history, "courtier", getattr(d, "courtier_drunk", None))
    print("  sailor", d.sailor_drunk, "innkeeper", d.innkeeper_guarded, d.innkeeper_drunk, "aimed", d.demon_aimed, "cursed", d.cursed)
    print("  goon", d.goon_first, [x for x in d.side_changes if x[2]=="Goon"], "assassin", d.assassin_aimed, "godfather", d.godfather_aimed, "gossip", d.gossip_killed, "lunatic", d.lunatic_chose, "moon", d.moonchild_picked, "killed", d.demon_killed)
    print("  all:", S.explanation_cost(w, mk(h)))
    print("  no wakes:", S.explanation_cost(w, mk(h, wakes={})))
    for i, row in enumerate(h):
        if S.explanation_cost(w, mk(h[:i] + h[i+1:])) is not None: print("   culprit row:", row)
    rec = d.record()
    for key in ("resurrections", "executions", "witch_deaths"):
        for k in list(rec[key]):
            r2 = {a: dict(b) for a, b in rec.items()}; r2[key].pop(k)
            try:
                if S.explanation_cost(w, mk(h, r2)) is not None: print("   culprit record:", key, k, rec[key][k])
            except Exception as e: print("   (", key, k, "->", e, ")")
    if "-v" in sys.argv[0:1] or True:
        for row in h: print("      ", row)
