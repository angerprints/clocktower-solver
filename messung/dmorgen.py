"""How often is the Demon found on the last morning the game is still open?
   python3 dmorgen.py SCRIPT OUT.jsonl FIRST LAST [MAXNIGHTS] [untold]

The game is played to its end (or MAXNIGHTS, 6 unless said). The board is
the one the table has on the last morning before the game is decided: all
of that night, nothing of the day. Quiet nights and days done are told,
unless "untold" is given. One line per game, readable by dana.py."""
import sys, random, time, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
sc = {"BMR": scripts.BAD_MOON_RISING, "SV": scripts.SECTS_AND_VIOLETS,
      "TB": scripts.TROUBLE_BREWING}[sys.argv[1]]
first, last = int(sys.argv[3]), int(sys.argv[4])
most = int(sys.argv[5]) if len(sys.argv) > 5 else 6
told = "untold" not in sys.argv
out = open(sys.argv[2], "a")
for seed in range(first, last):
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
               pcts=[round(p, 2) for p in pcts], t=round(dt, 1))
    out.write(json.dumps(rec) + "\n"); out.flush()
