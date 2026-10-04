import sys, random, time
sys.path.insert(0,"."); sys.path.insert(0,"tests")
import simulate, claims as C
from botc import scripts, solver as S
from botc.info import GameState
sc=scripts.BAD_MOON_RISING
cap=int(sys.argv[1]); nights=int(sys.argv[2]); S.ACCOUNTS_KEPT=cap
tot=0; res=[]
for seed in map(int, sys.argv[3:]):
    rng=random.Random(seed); n=[7,8,9,10,11][seed%5]
    d,h=simulate.play(n,rng,nights=nights,script=sc)
    cl,wk,_=C.claims_for(d,rng,script=sc)
    st=GameState(n_players=n,script=sc,claims=cl,wakes=wk,infos=list(h),votes=dict(d.votes),nominations=dict(d.nominations),**d.record())
    t=time.time(); r=S.analyze(st, rng=random.Random(seed)); dt=time.time()-t; tot+=dt
    res.append((seed, round(dt,1), r["legal"], r["valid"], [round(x["demon_pct"],2) for x in r["rows"]] if "demon_pct" in r["rows"][0] else None))
for x in res: print(x)
print("cap", cap, "gesamt", round(tot,1))
