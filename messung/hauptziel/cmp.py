import json,sys
a=[json.loads(l) for l in open(sys.argv[1])]; b=[json.loads(l) for l in open(sys.argv[2])]
n=min(len(a),len(b)); a=a[:n]; b=b[:n]
f=lambda r:r["rank"]==1
print(f"{n} Partien: vorher {sum(map(f,a))}, nachher {sum(map(f,b))}, neu vorn {sum(f(y) and not f(x) for x,y in zip(a,b))}, nicht mehr vorn {sum(f(x) and not f(y) for x,y in zip(a,b))}, echte Welt verloren {sum(not y['ok'] for y in b)}")
