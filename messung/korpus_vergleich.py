"""Which boards of the corpus changed between two copies of it.

    cp tests/fixtures/conformance.json /somewhere/before.json
    python3 tests/make_fixtures.py
    python3 messung/korpus_vergleich.py /somewhere/before.json tests/fixtures/conformance.json

Prints how many boards each has, how many are new or gone, and every board
whose expected answer changed, with what changed. Every change has to be
explained in the report.
"""
import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
def cases(x): return {c['name']:c for c in (x['cases'] if isinstance(x,dict) and 'cases' in x else x)}
A=cases(a); B=cases(b)
print(len(A), len(B), 'new', len(set(B)-set(A)), 'gone', len(set(A)-set(B)))
ch=[n for n in A if n in B and A[n]['expect']!=B[n]['expect']]
print('changed', len(ch))
for n in ch[:30]:
    ea,eb=A[n]['expect'],B[n]['expect']
    keys=[k for k in set(ea)|set(eb) if ea.get(k)!=eb.get(k)] if isinstance(ea,dict) else '?'
    print(' ', n, keys, {k:(ea.get(k),eb.get(k)) for k in keys if k in ('valid','legal','error')})
