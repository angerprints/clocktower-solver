"""What the simulator's village does by day. Simulator only, no solver.
   python3 messung/dorf.py N [NIGHTS]

For Trouble Brewing, Bad Moon Rising and Sects & Violets, N games each:
how often a day ends with an execution, how many votes stood behind it
(a real table needs half the living), and who went up, set against who
was standing. Nothing in the simulator is changed: the day's last step
is watched from outside."""
import sys, random, collections, math
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate
from botc import scripts
from botc.roles import TEAM

N = int(sys.argv[1]); NIGHTS = int(sys.argv[2]) if len(sys.argv) > 2 else 6
LOG = []
_real = simulate._execute
def _watched(d, day, rng, allow_takeover=False):
    phase = f"E{day}"
    living = [p for p in d.alive_at(phase) if d.deaths.get(p) is None]
    tally = dict(d.tally.get(day) or {})
    victim = _real(d, day, rng, allow_takeover)
    went = victim if victim is not None else d.executions.get(day)
    LOG.append(dict(day=day, living=len(living), tally=tally,
                    died=victim is not None, walked=victim is None and day in d.executions,
                    went=went,
                    team=None if went is None else TEAM[d.role_at(went, phase)],
                    teams=collections.Counter(TEAM[d.role_at(p, phase)] for p in living),
                    demon=d.role_at(d.demon_at(phase), phase) if d.demon_at(phase) is not None else None))
    return victim
simulate._execute = _watched

def pct(a, b): return f"{100 * a / b:5.1f}%" if b else "    -"
for name, sc in (("Trouble Brewing", scripts.TROUBLE_BREWING),
                 ("Bad Moon Rising", scripts.BAD_MOON_RISING),
                 ("Sects & Violets", scripts.SECTS_AND_VIOLETS)):
    LOG.clear(); zomb = collections.Counter()
    for seed in range(N):
        n = [7, 8, 9, 10][seed % 4]
        d, _ = simulate.play(n, random.Random(seed), nights=NIGHTS, script=sc)
        if sc is scripts.BAD_MOON_RISING and d.role_at(d.demon_at("N1"), "N1") == "Zombuul":
            for j in range(2, d.nights_played + 1):
                zomb["nights"] += 1
                zomb["free to kill"] += not d.died_on(f"D{j-1}", f"E{j-1}")
    days = len(LOG)
    died = sum(r["died"] for r in LOG); walked = sum(r["walked"] for r in LOG)
    print(f"\n=== {name}: {N} games, {days} days")
    print(f"  somebody executed and dead   {pct(died, days)}")
    print(f"  executed, but walked away    {pct(walked, days)}")
    print(f"  nobody executed              {pct(days - died - walked, days)}")
    for day in range(1, NIGHTS):
        rs = [r for r in LOG if r["day"] == day]
        print(f"    day {day}: {len(rs):5d} days, execution {pct(sum(r['died'] or r['walked'] for r in rs), len(rs))}, living {sum(r['living'] for r in rs) / max(1, len(rs)):.1f}")
    ex = [r for r in LOG if r["went"] is not None]
    voted = [r for r in ex if r["tally"].get(r["went"])]
    need = lambda r: math.ceil(r["living"] / 2)
    enough = sum(r["tally"][r["went"]] >= need(r) for r in voted)
    print(f"  executions with a vote behind them   {pct(len(voted), len(ex))}  (the rest: nobody voted, a seat was drawn)")
    print(f"  executions with half the living      {pct(enough, len(ex))}")
    print(f"  mean votes for whoever went up       {sum(r['tally'].get(r['went'], 0) for r in ex) / max(1, len(ex)):.2f} of {sum(r['living'] for r in ex) / max(1, len(ex)):.1f} living, needed {sum(need(r) for r in ex) / max(1, len(ex)):.1f}")
    def real_table(r):
        top = sorted(r["tally"].values(), reverse=True)
        return bool(top) and top[0] >= need(r) and (len(top) < 2 or top[1] < top[0])
    print(f"  days a real table would have executed {pct(sum(map(real_table, LOG)), days)}  (most votes, half the living, no tie)")
    noms = collections.Counter(len(r["tally"]) for r in LOG)
    print(f"  nominees a day                       {dict(sorted(noms.items()))}")
    print("  who went up, against who was standing:")
    stand = collections.Counter()
    for r in ex: stand.update(r["teams"])
    tot = sum(stand.values())
    for team in ("townsfolk", "outsider", "minion", "demon"):
        went = sum(r["team"] == team for r in ex)
        print(f"    {team:10s} executed {pct(went, len(ex))}   standing {pct(stand[team], tot)}")
    if zomb:
        print(f"  Zombuul: free to kill on {pct(zomb['free to kill'], zomb['nights'])} of its nights")
