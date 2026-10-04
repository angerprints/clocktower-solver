import sys, random, time, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, app
import make_fixtures as F
from botc import scripts
BMR=scripts.BAD_MOON_RISING
found = collections.defaultdict(list)
def tags(d, h, nights):
    t = set()
    for day, why in d.walked_because.items(): t.add("walked:" + why)
    for seat, at, by in d.resurrections: t.add("raised:" + by)
    if d.fool_spent_ever and d.resurrections: t.add("fool and back")
    if d.zombuul_up is not None: t.add("zombuul up")
    if d.game_ends_after is not None and "Mastermind" in d.roles: t.add("mastermind?%s" % d.game_ends_after)
    for night, target in d.moonchild_picked.items():
        m = [r for r in h if type(r).__name__ == "MoonchildChoice" and r.night == night][0].player
        if d.deaths_of(m)[-1][0] == "N" and target in d.died_on(f"N{night}"): t.add("moonchild night kill")
    hist = d.pukka_history
    for k in range(3, nights + 1):
        if k - 1 not in hist and k in hist and hist[k][0] is not None and hist[k][0] in d.died_on(f"N{k}") and (k - 2) in hist:
            t.add("pukka late")
    for k, (ch, g) in d.goon_first.items():
        r = d.role_at(ch, f"N{k}")
        t.add("goon:" + ("demon" if simulate.TEAM[r] == "demon" else r))
        if simulate.TEAM[r] == "demon" and not d.died_on(f"N{k}"): t.add("goon:demon, quiet night")
    if any(x[2] == "Goon" and x[3] == "evil" for x in d.side_changes):
        t.add("goon turned evil")
        for p in range(d.n):
            if d.roles[p] == "TeaLady": t.add("goon turned evil, tea lady in play")
    for k, tg in d.assassin_aimed.items(): t.add("assassin" + ("" if tg in d.died_on(f"N{k}") else ", nothing"))
    for k, tg in d.godfather_aimed.items(): t.add("godfather" + ("" if tg in d.died_on(f"N{k}") else ", nothing"))
    if d.gossip_killed: t.add("gossip")
    if len(d.courtier_nights) > 1: t.add("courtier chose again")
    if sum(1 for r in h if type(r).__name__ == "GrandmotherInfo") > 1: t.add("grandmother shown again")
    if d.innkeeper_void: t.add("innkeeper void")
    return t
check = [int(x) for x in sys.argv[1:]]
for seed in check:
    d, h = simulate.play(7, random.Random(seed), nights=4, script=BMR)
    print(seed, sorted(tags(d, h, 4)), d.roles)
if not check:
    for seed in range(3000):
        d, h = simulate.play(7, random.Random(seed), nights=4, script=BMR)
        for t in tags(d, h, 4):
            if len(found[t]) < 5: found[t].append(seed)
    for t, seeds in sorted(found.items()):
        out = []
        for seed in seeds[:3]:
            b = F.played("x", BMR, seed, 7, 4)
            t0 = time.time(); r = app.run_solve(b["payload"]); dt = time.time() - t0
            out.append((seed, round(dt, 1)))
        print(t, seeds, out)
