import json, sys, collections
sys.path.insert(0,'.')
from botc.roles import TOWNSFOLK, OUTSIDERS
EVIL={'Imp','Poisoner','Spy','ScarletWoman','Baron','Po','Pukka','Shabaloth','Zombuul','Godfather','DevilsAdvocate','Assassin','Mastermind','FangGu','Vigormortis','NoDashii','Vortox','EvilTwin','Witch','Cerenovus','PitHag'}
def key(r):
    k='keine'
    for s in range(r['n']):
        ro=r['roles'][s]; c=r['claims'].get(str(s))
        if ro in EVIL or ro=='Drunk' or c is None or c==ro: continue
        if ro in OUTSIDERS and c in TOWNSFOLK: k = k if k=='chaos' else 'versteckt'
        else: k='chaos'
    return k
base={r['seed']:r for r in map(json.loads,open(sys.argv[1]))}
for f in sys.argv[2:]:
    new={r['seed']:r for r in map(json.loads,open(f))}
    c=collections.Counter(); b=collections.Counter(); t0=t1=0
    for s,r in new.items():
        k=key(r); c[k]+=r['rank']==1; b[k]+=base[s]['rank']==1; c['n'+k]+=1
        t0+=base[s]['t']; t1+=r['t']
    print(f, 'gesamt', sum(r['rank']==1 for r in new.values()), 'statt', sum(base[s]['rank']==1 for s in new), 'von', len(new),
          '| ' + ', '.join(f"{k}: {b[k]}→{c[k]} von {c['n'+k]}" for k in ('keine','versteckt','chaos')),
          f'| Zeit {t0/60:.0f}→{t1/60:.0f} min, verloren {sum(not r["ok"] for r in new.values())}')
