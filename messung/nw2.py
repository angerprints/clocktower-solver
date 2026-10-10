"""Simulator against the night-walk, night by night. python3 nw2.py SCRIPT N NIGHTS"""
import sys, random, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, nightwalk
from botc import scripts
from test_js_worlds import EASTER
from test_experimental import SPY, VORTOX
from test_experimental_2 import OJO, OJO_BMR
from test_experimental_3 import WRAITH, WRAITH_BMR
from test_experimental_4 import FOUR, FOUR_BMR
which = {"TB": scripts.TROUBLE_BREWING, "BMR": scripts.BAD_MOON_RISING,
         "SV": scripts.SECTS_AND_VIOLETS, "EASTER": scripts.from_json(EASTER),
         # The two scripts made for the experimental characters.
         "XSPY": SPY, "XVORTOX": VORTOX,
         # And for the second five.
         "XOJO": OJO, "XOJOB": OJO_BMR,
         "XWRAITH": WRAITH, "XWRAITHB": WRAITH_BMR,
         "XFOUR": FOUR, "XFOURB": FOUR_BMR}
sc = which[sys.argv[1]]; N = int(sys.argv[2]); nights = int(sys.argv[3])
tot = collections.Counter(); bad = collections.Counter(); ex = []
for seed in range(N):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    for night in range(2, nights + 1):
        if d.game_ends_after is not None and night > d.game_ends_after: continue
        hid = nightwalk.hidden_from(d, night, h)
        try: got = nightwalk.walk(d, night, hid)
        except Exception as e:
            bad["crash " + type(e).__name__] += 1; ex.append((seed, night, repr(e))); continue
        tags = ["all"]
        if ("regurgitated", night) in hid: tags.append("regurgitated")
        if ("professor", night) in hid: tags.append("professor raised")
        if ("moonchild", night) in hid: tags.append("moonchild pick")
        if hid.get(("fool_spent", night)): tags.append("fool spent")
        if any(d.role_at(p, f"N{night}") == "Fool" for p in range(n)): tags.append("fool in play")
        for t in tags: tot[t] += 1
        if got.died != d.died_on(f"N{night}") or got.untold:
            for t in tags: bad[t] += 1
            ex.append((seed, night, sorted(got.died), sorted(d.died_on(f"N{night}")), sorted(got.untold)))
print({t: f"{bad[t]} von {tot[t]}" for t in tot}); print({k: v for k, v in bad.items() if k.startswith("crash")}); print(ex[:12])
