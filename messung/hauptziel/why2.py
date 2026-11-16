import json,sys,collections
sys.path.insert(0,'.')
import app
from botc import solver
TEAM=solver.TEAM
cap={}
orig=app.analyze
def spy(state,*a,**k):
    cap['s']=state; return orig(state,*a,**k)
app.analyze=spy
import botc.solver as s2
c={x['name']:x for x in json.load(open('tests/fixtures/conformance.json'))['cases']}
for name in sys.argv[1:]:
    solver.BAG_PRIOR_POWER=1.0
    app.run_solve(c[name]['payload'])
    state=cap['s']; _,worlds=solver.solve(state)
    weights=[solver.world_weight(w,state) for w in worlds]
    g=collections.defaultdict(lambda:[0,0.0,0.0])
    for w,wt in zip(worlds,weights or [1]*len(worlds)):
        b=solver.bag_weight(w,state)
        dem=[(i,r) for i,r in enumerate(w.roles) if TEAM.get(r)=='demon']
        o=sum(TEAM.get(r)=='outsider' for r in set(w.roles))
        mins=[r for r in w.roles if TEAM.get(r)=='minion']
        key=(str(dem),o,('t%d'%sum(TEAM.get(r)=='townsfolk' for r in set(w.roles)))+' '+('/'.join(sorted(mins)) if len(sys.argv)<9 else ''))
        g[key][0]+=1; g[key][1]+=wt/b; g[key][2]+=wt
    t0=sum(v[1] for v in g.values()); t1=sum(v[2] for v in g.values())
    print('==',name)
    for k,v in sorted(g.items(),key=lambda kv:-kv[1][2])[:10]:
        print(f"  {v[0]:4d} Welten  ohne {100*v[1]/t0:5.1f} %  mit {100*v[2]/t1:5.1f} %   Dämon {k[0]}  Außenseiter {k[1]}  Diener {k[2]}")
