import json,sys,collections
G={'FortuneTeller':'nachts','Empath':'nachts','Undertaker':'nachts','Washerwoman':'1.Nacht','Librarian':'1.Nacht','Investigator':'1.Nacht','Chef':'1.Nacht'}
g=lambda c:G.get(c,'ohne Info' if c else 'keine')
recs=[json.loads(l) for l in open(sys.argv[1])]
tot=collections.Counter(); miss=collections.Counter(); topg=collections.Counter(); dpm=collections.defaultdict(list)
for r in recs:
    dc=r['claims'].get(str(r['demon'])); k=g(dc); tot[k]+=1
    if r['rank']!=1:
        miss[k]+=1
        top=max(range(len(r['pcts'])),key=lambda i:r['pcts'][i]); topg[(k,g(r['claims'].get(str(top))))]+=1
        dpm[k].append(round(r['pcts'][top]-r['dp']))
for k in tot: print(f"Dämon behauptet {k:10s}: {tot[k]:4d} Partien, verfehlt {miss[k]:4d} ({100*miss[k]/tot[k]:.0f} %), Median Abstand {sorted(dpm[k])[len(dpm[k])//2] if dpm[k] else '-'}")
print('verfehlt: (Dämon-Gruppe, Gruppe des Vordersten)'); [print(' ',k,v) for k,v in topg.most_common(10)]
