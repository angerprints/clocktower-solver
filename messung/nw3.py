import sys, random
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, nightwalk
from botc import scripts
which = {"BMR": scripts.BAD_MOON_RISING, "SV": scripts.SECTS_AND_VIOLETS}
# The scripts made for the experimental characters.
from test_experimental import SPY, VORTOX
from test_experimental_2 import OJO, OJO_BMR
from test_experimental_3 import WRAITH, WRAITH_BMR
which.update({"XSPY": SPY, "XVORTOX": VORTOX, "XOJO": OJO, "XOJOB": OJO_BMR,
              "XWRAITH": WRAITH, "XWRAITHB": WRAITH_BMR})
sc = which[sys.argv[1]]; nights = int(sys.argv[2])
for seed in map(int, sys.argv[3:]):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    print("=== seed", seed, list(enumerate(d.roles)))
    print("  record", d.record(), "raised", d.resurrections, "fool", d.fool_spent, "walked", d.walked_because)
    print("  aimed", d.demon_aimed, "changes", d.changes, "courtier", getattr(d, "courtier_drunk", None), "pukka", d.pukka_history, "cursed", d.cursed)
    for night in range(2, nights + 1):
        hid = nightwalk.hidden_from(d, night, h)
        got = nightwalk.walk(d, night, hid)
        if got.died != d.died_on(f"N{night}") or got.untold:
            print("  night", night, "walk", sorted(got.died), "sim", sorted(d.died_on(f"N{night}")), "untold", got.untold)
            print("    droisoned", simulate.droisoned_at(d, night), "innkeeper", d.innkeeper_guarded.get(night), d.innkeeper_drunk.get(night), "sailor", d.sailor_drunk.get(night), "monk", d.monk_guarded.get(night))
            print("    hidden", hid); print("    log", got.log)
    for r in h: print("     ", r)
