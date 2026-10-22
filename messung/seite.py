"""Boards as the page posts them, solved the way the page does (`app.run_solve`).

    python3 messung/seite.py START STOP NIGHTS CHARACTER[,CHARACTER...]

Seeds START..STOP, 7 to 9 players, scripts that must hold the characters.
Only games where the first of them was dealt (or, for the Summoner, where
one was dealt) count. Games where a good player lies for no reason are
skipped: the page allows that only when asked. Per board: seed, players,
seconds, worlds. At the end: boards with no world and boards over 120 s.
Used as the page gate for the Summoner (21./22.10.2026).
"""
import sys, random, time, signal
class Slow(Exception): pass
def _alarm(*a): raise Slow()
signal.signal(signal.SIGALRM, _alarm)
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'tests'), str(ROOT / 'tools')]
import simulate, play_games, app, claims as C
from make_fixtures import played
start, stop, nights = (int(x) for x in sys.argv[1:4])
MUST=tuple(sys.argv[4].split(','))
t=time.time(); boards=liars=0; empty=[]; times=[]; slow=[]
for seed in range(start, stop):
    n=[7,8,9][seed%3]
    probe=random.Random(seed); sc=play_games.an_awkward_script(probe, must_have=MUST)
    d,_=simulate.play(n,probe,nights=nights,script=sc)
    if MUST[0] not in d.roles: continue
    _cl,_wk,notes=C.claims_for(d,probe,script=sc)
    if any("for no reason" in v for v in notes.values()):
        liars+=1; continue
    rng=random.Random(seed); sc=play_games.an_awkward_script(rng, must_have=MUST)
    p=played(f"x{seed}", sc, seed, n, nights, rng=rng)['payload']
    t0=time.time(); signal.alarm(120)
    try:
        r=app.run_solve(p)
    except Slow:
        r=None
    signal.alarm(0); dt=time.time()-t0; times.append(dt)
    boards+=1
    print(seed, n, round(dt,1), 'slow' if r is None else (r.get('error') or r.get('valid')), flush=True)
    if r is None:
        slow.append(seed); continue
    if r.get('error') or not r.get('valid'):
        empty.append((seed, r.get('error') or 0))
times.sort()
print(f"seeds {start}-{stop}: boards {boards}, skipped (good liar) {liars}, no world {len(empty)} {empty}, over 120 s {len(slow)} {slow}")
print(f"  time total {round(time.time()-t)} s, median {round(times[len(times)//2],1) if times else 0}, max {round(times[-1],1) if times else 0}")
