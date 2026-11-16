import json,sys
def cases(x): return {c['name']:c for c in (x['cases'] if isinstance(x,dict) and 'cases' in x else x)}
A=cases(json.load(open(sys.argv[1]))); B=cases(json.load(open(sys.argv[2])))
same=[n for n in A if n in B]
vchg=[n for n in same if A[n]['expect'].get('valid')!=B[n]['expect'].get('valid') or A[n]['expect'].get('error')!=B[n]['expect'].get('error')]
rchg=[];top=[];big=[]
for n in same:
    ra,rb=A[n]['expect'].get('rows') or [],B[n]['expect'].get('rows') or []
    if ra==rb: continue
    rchg.append(n)
    if len(ra)!=len(rb): continue
    d=max(abs((x.get('demon_pct') or 0)-(y.get('demon_pct') or 0)) for x,y in zip(ra,rb))
    big.append((d,n))
    ta=max(range(len(ra)),key=lambda i:ra[i].get('demon_pct') or 0); tb=max(range(len(rb)),key=lambda i:rb[i].get('demon_pct') or 0)
    if (ra[ta].get('demon_pct') or 0)!=(ra[tb].get('demon_pct') or 0): top.append(n)
print(f"{len(A)} -> {len(B)} Bretter; Weltenzahl geändert: {len(vchg)}; Prozente geändert: {len(rchg)}; anderer Platz vorn: {len(top)}")
big.sort(reverse=True)
print("größte Verschiebung Dämon-%:")
for d,n in big[:12]: print(f"  {d:5.1f}  {n}")
print("Weltenzahl geändert:",vchg[:20])
