"""Demon calibration by claim group and game length: python3 byinfo.py FILE"""
import json,sys,collections
G={'nachts':{'FortuneTeller','Empath','Undertaker'},'erste Nacht':{'Washerwoman','Librarian','Investigator','Chef'},
   'keine Info':{'Saint','Soldier','Mayor','Butler','Recluse','Monk','Slayer','Virgin','Ravenkeeper'}}
grp=lambda c:next((g for g,s in G.items() if c in s),'sonst')
recs=[json.loads(l) for l in open(sys.argv[1])]
t=collections.defaultdict(lambda:[0,0.0,0])
for r in recs:
    if not r['pcts'] or len(r['pcts'])<r['n']: continue
    L=min(r['ended'] or 9,4)
    for s in range(r['n']):
        c=r['claims'].get(str(s));
        if not c: continue
        k=(grp(c),L); t[k][0]+=1; t[k][1]+=r['pcts'][s]/100; t[k][2]+= (s==r['demon'])
for k in sorted(t):
    n,e,a=t[k]; print(f"{k[0]:12s} Tag {k[1]}  Sitze {n:5d}  erwartet {e:6.1f}  wirklich {a:4d}  Verhältnis {a/e if e else 0:4.2f}")
