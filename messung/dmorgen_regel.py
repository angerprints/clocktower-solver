"""dmorgen.py with one rule tried in memory: the game is going on, so at
least three players are really alive.
   python3 dmorgen_regel.py BMR OUT.jsonl FIRST LAST 6 [rule]
   SEEDS=1,2,3 in the environment limits it to those seeds.

Two on the board and the game not over means somebody on the board as
dead is alive: a Zombuul that died once. A world whose Demon is any
other and still standing would have won. Nothing in the solver is
changed by this script. Each line also carries `zpcts`, how likely each
seat is the Zombuul."""
import sys, random, time, json
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
from botc.worlds import World
from botc.info import phase_index
RULE = "rule" in sys.argv
_real = S.best_story
def _three_alive(world, state, outcome=None, viable=None):
    """Experiment: the game is going on, so at least three are really alive."""
    if RULE:
        k = NOW
        for phase in [f"N{j}" for j in range(2, k + 1)] + [f"D{j}" for j in range(1, k + 1)]:
            board = state.alive_set(phase)
            if len(board) > 2:
                continue
            # Two on the board. A Zombuul that died once makes three. Any
            # other Demon still standing has won; one that is dead leaves
            # only a Mastermind's day, which the solver judges itself.
            demon = next((p for p in range(state.n_players)
                          if world.role_at(p, phase) in ("Zombuul", "Pukka", "Shabaloth", "Po")), None)
            if demon is None:
                continue
            if demon in board:
                return None, ()
            if world.role_at(demon, phase) == "Zombuul":
                gone = [p for p in state.died_at(demon) if phase_index(p) < phase_index(phase)]
                if len(gone) < 2 and len(board) + 1 > 2:
                    continue
                if len(gone) < 2:
                    return None, ()
    return _real(world, state, outcome, viable)
S.best_story = _three_alive
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
    NOW = k
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
               zpcts=[round(dict(row['roles']).get('Zombuul', 0.0), 2) for row in rows])
    out.write(json.dumps(rec) + "\n"); out.flush()
