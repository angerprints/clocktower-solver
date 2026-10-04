"""Truth sweep with tags for everything the simulator has learned to play.
   python3 sim5.py SCRIPT N NIGHTS [START]"""
import sys, random, time, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
from test_js_worlds import EASTER
which = {"TB": scripts.TROUBLE_BREWING, "BMR": scripts.BAD_MOON_RISING,
         "SV": scripts.SECTS_AND_VIOLETS, "EASTER": scripts.from_json(EASTER)}
name, N, nights = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
sc = which[name]
stats = collections.Counter(); bad = []; t0 = time.time(); badtags = collections.Counter()
for seed in range(start, start + N):
    n = [7, 8, 9, 10, 11][seed % 5]
    rng = random.Random(seed); d, h = simulate.play(n, rng, nights=nights, script=sc)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                   votes=dict(d.votes), nominations=dict(d.nominations), **d.record())
    tags = set()
    for day, why in d.walked_because.items(): tags.add("walked:" + why)
    for seat, at, by in d.resurrections: tags.add("raised:" + by)
    if d.witch_deaths: tags.add("witch death")
    if d.moonchild_picked: tags.add("moonchild pick")
    for k, (ch, g) in d.goon_first.items(): tags.add("goon:" + ("demon" if simulate.TEAM[d.role_at(ch, f"N{k}")] == "demon" else d.role_at(ch, f"N{k}")))
    if any(x[2] == "Goon" and x[3] == "evil" for x in d.side_changes): tags.add("goon turned evil")
    for k, t in d.assassin_aimed.items(): tags.add("assassin" + ("" if t in d.died_on(f"N{k}") else ", nothing"))
    for k, t in d.godfather_aimed.items(): tags.add("godfather" + ("" if t in d.died_on(f"N{k}") else ", nothing"))
    if d.gossip_killed: tags.add("gossip")
    if len(d.courtier_nights) > 1: tags.add("courtier chose again")
    if sum(1 for r in h if type(r).__name__ == "GrandmotherInfo") > 1: tags.add("grandmother shown again")
    for t in tags: stats[t] += 1
    if S.explanation_cost(World(tuple(d.roles), tuple(d.believes)), st) is None:
        bad.append(seed)
        for t in tags or {"(none)"}: badtags[t] += 1
print(f"{name}: {N} Partien ab {start}, {nights} Nächte, verworfen {len(bad)} {bad[:30]} ({time.time()-t0:.0f} s)")
print(" gespielt:", dict(sorted(stats.items())))
print(" verworfen mit:", dict(sorted(badtags.items())))
