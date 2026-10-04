"""dmorgen.py with a price tried in memory: a night nobody died costs
PRICE in every world whose Demon was up to kill that night.
   PRICE=0.5 python3 messung/dmorgen_preis.py BMR OUT.jsonl FIRST LAST [MAXNIGHTS]
   SEEDS=1,2,3 in the environment limits it to those seeds. PRICE=1 is
   the solver as it is.

Nothing in the solver is changed by this script. Each line also carries
`zpcts` (how likely each seat is the Zombuul), `mass` (the solver's
belief per Demon type), and what died by day and by night."""
import sys, random, time, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
from botc.info import phase_index
# Experiment: a night nobody died, in a world whose Demon was up to kill
# that night, costs PRICE. Nothing in the solver is changed.
import os as _os
from botc import deaths as _D
PRICE = float(_os.environ.get("PRICE", "1"))
_real_night = S._explained_night
def _priced_night(world, state, night):
    got = _real_night(world, state, night)
    if PRICE == 1 or night not in (getattr(state, "quiet_nights", None) or ()):
        return got
    if not any(c.name == "Demon" for c in _D.causes_on(world, state, night)):
        return got
    return [(c * PRICE, i, w, e) for c, i, w, e in got]
S._explained_night = _priced_night
sc = {"BMR": scripts.BAD_MOON_RISING, "SV": scripts.SECTS_AND_VIOLETS,
      "TB": scripts.TROUBLE_BREWING}[sys.argv[1]]
first, last = int(sys.argv[3]), int(sys.argv[4])
most = int(sys.argv[5]) if len(sys.argv) > 5 else 6
told = True
out = open(sys.argv[2], "a")
import os
ONLY = set(map(int, os.environ['SEEDS'].split(','))) if os.environ.get('SEEDS') else None
for seed in range(first, last):
    if ONLY is not None and seed not in ONLY: continue
    n = [7, 8, 9, 10][seed % 4]
    whole, _ = simulate.play(n, random.Random(seed), nights=most, script=sc)
    # The last morning the game was open, and what closed it.
    if whole.mastermind_day is not None:
        k, how = whole.mastermind_day - 1, "demon executed, extra day"
    elif whole.ended_at is None:
        k, how = whole.nights_played, "still open"
    elif whole.ended_at[0] == "N":
        k, how = int(whole.ended_at[1:]) - 1, "two alive at dawn"
    elif whole.ended_why == "vortox":
        k, how = int(whole.ended_at[1:]), "no execution under a Vortox"
    else:
        k, how = int(whole.ended_at[1:]), "two alive after the day"
    if k < 1:
        continue
    # The same game, stopped that morning: the same seed plays the same
    # nights, and the claims are then made from what had happened by then.
    rng = random.Random(seed)
    d, h = simulate.play(n, rng, nights=k, script=sc)
    assert d.ended_at is None and d.mastermind_day is None, (seed, k, d.ended_at)
    cl, wk, _ = C.claims_for(d, rng, script=sc)
    st = GameState(n_players=n, script=sc, claims=cl, wakes=wk, infos=list(h),
                   votes=dict(d.votes), nominations=dict(d.nominations),
                   **d.record(told=told))
    end = f"D{k}"
    demon = d.demon_at(end)
    kind = d.role_at(demon, end)
    alive = sorted(d.alive_at(end))
    standing = len(alive) + (d.zombuul_up is not None and d.zombuul_up not in alive)
    t = time.time()
    ok = S.explanation_cost(World(tuple(d.roles), tuple(d.believes)), st) is not None
    r = S.analyze(st, rng=random.Random(1))
    dt = time.time() - t
    rows = r["rows"] or []
    dp = rows[demon]["demon_pct"] if rows else None
    pcts = [row["demon_pct"] for row in rows]
    rank = (1 + sum(p > dp + 1e-9 for p in pcts)) if rows else None
    tied = sum(abs(p - dp) <= 1e-9 for p in pcts) if rows else None
    lrank = (1 + sum(pcts[p] > dp + 1e-9 for p in alive)) if rows and demon in alive else None
    rec = dict(seed=seed, n=n, kind=kind, demon=demon, morning=k, how=how, told=told,
               ended=None, alive=len(alive), standing=standing,
               demon_alive=demon in alive, quiet=sorted(d.record()["quiet_nights"]),
               ok=ok, valid=r["valid"], sampled=bool(r.get("sampled")), dp=dp,
               rank=rank, tied=tied, lrank=lrank, top=max(pcts) if pcts else None,
               claim=cl.get(demon), roles=list(d.roles),
               deaths={str(k_): v for k_, v in d.deaths.items()},
               pcts=[round(p, 2) for p in pcts], t=round(dt, 1),
               zpcts=[round(dict(row['roles']).get('Zombuul', 0.0), 2) for row in rows],
               mass={k: round(sum(dict(row['roles']).get(k, 0.0) for row in rows), 2) for k in ('Zombuul', 'Po', 'Pukka', 'Shabaloth')},
               executed={str(p_): v for p_, v in d.deaths.items() if v[0] == 'E'}, walked={str(k_): v for k_, v in d.walked_because.items()},
               night_deaths={str(j): sorted(d.died_on(f'N{j}')) for j in range(2, k + 1)}, day_deaths={str(j): sorted(d.died_on(f'D{j}', f'E{j}')) for j in range(1, k)})
    out.write(json.dumps(rec) + "\n"); out.flush()
