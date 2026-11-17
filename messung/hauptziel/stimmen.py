"""python3 stimmen.py SKRIPT OUT GRUNDMESSUNG.jsonl [BOESE_FUER_BOESE] — Versuch C
(17.11.2026): Der Solver erfährt, wer an jedem Tag für welchen Nominierten
stimmte, und gewichtet jede Welt mit dem Abstimmungsmodell des Simulators
(ein Böser stimmt für einen bösen Nominierten mit 0,2, sonst jeder mit 0,45).
Eine Obergrenze: Der Solver kennt dabei die wahren Zahlen des Simulators.
Nur die Partien der Grundmessung mit drei Lebenden werden neu gerechnet.
Aus dem Wurzelordner eines Checkouts starten."""
import json
import sys
import runpy

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
import botc.solver as S                                   # noqa: E402

BASE = 0.45
EVIL = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2
YES = EVIL / BASE                 # an evil vote for an evil nominee
NO = (1 - EVIL) / (1 - BASE)      # an evil voter holding back on one

orig_prior = S.prior_weight
orig_analyze = S.analyze


def prior(world, state):
    w = orig_prior(world, state)
    record = state.__dict__.get("_voted_for")
    if not record:
        return w
    for day, (nominees, voters_alive) in record.items():
        phase = f"D{day}"
        evil = {p: world.evil_at(p, phase) for p in voters_alive}
        for nominee, voters in nominees.items():
            if not world.evil_at(nominee, phase):
                continue
            for v in voters_alive:
                if evil[v]:
                    w *= YES if v in voters else NO
    return w


def analyze(st, *a, **kw):
    g = sys._getframe(1).f_globals
    d, alive = g.get("d"), g.get("alive")
    if d is not None and alive is not None and len(alive) == 3:
        end = int(g["end"][1:])
        record = {}
        for day, tally in d.tally.items():
            if day > end:
                continue
            voted = d.voted_for.get(day, {})
            record[day] = ({n: set(voted.get(n, ())) for n in tally},
                           sorted(d.alive_at(f"D{day}")))
        st.__dict__["_voted_for"] = record
    return orig_analyze(st, *a, **kw)


S.prior_weight = prior
S.analyze = analyze
script, out, base = sys.argv[1], sys.argv[2], sys.argv[3]
seeds = [json.loads(l)["seed"] for l in open(base) if json.loads(l)["alive"] == 3]
for seed in seeds:
    sys.argv = ["dmeas.py", script, out, str(seed), str(seed + 1), "4"]
    runpy.run_path("messung/dmeas.py", run_name="__main__")
