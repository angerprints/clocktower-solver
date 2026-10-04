"""How often a night is quiet, by Demon and by whether the day before had a death.
Simulator only, no solver."""
import sys, random, collections, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate
from botc import scripts
sc = scripts.BAD_MOON_RISING
N = int(sys.argv[1])
cnt = collections.Counter(); games = collections.Counter(); pat = collections.defaultdict(collections.Counter)
for seed in range(N):
    n = [7, 8, 9, 10][seed % 4]
    d, _ = simulate.play(n, random.Random(seed), nights=6, script=sc)
    k = d.nights_played
    kind = d.role_at(d.demon_at("N1"), "N1")
    games[kind] += 1
    q_after_death = 0; loud_after_death = 0
    for j in range(2, k + 1):
        if d.role_at(d.demon_at(f"N{j}"), f"N{j}") != kind: continue
        day = bool(d.died_on(f"D{j-1}", f"E{j-1}"))
        quiet = not d.died_on(f"N{j}")
        cnt[(kind, "day death" if day else "no day death", "quiet" if quiet else "bodies")] += 1
        if day and quiet: q_after_death += 1
        if day and not quiet: loud_after_death += 1
    pat[(min(q_after_death, 4), min(loud_after_death, 2))][kind] += 1
print(dict(games))
for kind in ("Zombuul", "Po", "Pukka", "Shabaloth"):
    for day in ("day death", "no day death"):
        q = cnt[(kind, day, "quiet")]; b = cnt[(kind, day, "bodies")]
        print(f"{kind:10s} {day:13s} quiet {q:6d} of {q+b:6d} = {100*q/max(1,q+b):5.1f}%")
print("quiet nights after a day with a death (capped 4), nights with bodies after such a day (capped 2) -> who it was")
for key in sorted(pat):
    c = pat[key]; t = sum(c.values())
    print(key, t, {k: f"{100*v/t:.0f}%" for k, v in sorted(c.items())})
