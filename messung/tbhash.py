import sys, random, hashlib
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate
from botc import scripts
from test_js_worlds import EASTER
for name, sc in (("TB", scripts.TROUBLE_BREWING), ("EASTER", scripts.from_json(EASTER)), ("SV", scripts.SECTS_AND_VIOLETS)):
    h = hashlib.sha256()
    for seed in range(600):
        n = [7, 8, 9, 10, 11][seed % 5]
        d, heard = simulate.play(n, random.Random(seed), nights=4, script=sc)
        h.update(repr((d.roles, sorted(d.deaths.items()), d.changes, [repr(r) for r in heard], sorted((k, sorted(v)) for k, v in d.votes.items()))).encode())
    print(name, h.hexdigest()[:16])
