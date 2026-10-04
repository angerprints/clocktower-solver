"""Why was the night quiet, in the simulator? No solver involved."""
import sys, random, collections
sys.path.insert(0, "."); sys.path.insert(0, "tests")
import simulate
from botc import scripts
sc = scripts.BAD_MOON_RISING
nights_by = collections.Counter(); quiet_by = collections.Counter(); why = collections.defaultdict(collections.Counter)
for seed in range(int(sys.argv[1])):
    n = [7, 8, 9, 10][seed % 4]
    d, h = simulate.play(n, random.Random(seed), nights=4, script=sc)
    last = min(4, d.game_ends_after or 4)
    for k in range(2, last + 1):
        phase = f"N{k}"; demon = d.demon_at(phase)
        if demon is None or demon not in d.alive_at(phase) and d.role_at(demon, phase) != "Zombuul": continue
        kind = d.role_at(demon, phase)
        if len(d.alive_at(phase)) + (demon not in d.alive_at(phase)) < 3: continue   # the game is over
        nights_by[kind] += 1
        if d.died_on(phase): continue
        quiet_by[kind] += 1
        aimed = list(d.demon_aimed.get(k) or [])
        first = d.goon_first.get(k)
        if kind == "Zombuul" and d.died_on(f"D{k-1}", f"E{k-1}"): r = "am Tag starb jemand (Zombuul schläft)"
        elif simulate._exorcised(d, k): r = "Exorzist hat den Dämon gewählt"
        elif first is not None and first[0] == demon: r = "Dämon wählte den Schläger zuerst"
        elif any(s <= k <= s + 2 and holder == demon for s, holder, c in d.courtier_drunks) and not d.working(demon, k): r = "Dämon betrunken: Höfling"
        elif d.sailor_drunk.get(k) == demon and not d.working(demon, k): r = "Dämon betrunken: Segler"
        elif d.innkeeper_drunk.get(k) == demon and not d.working(demon, k): r = "Dämon betrunken: Gastwirt"
        elif not d.working(demon, k): r = "Dämon gestört: anderes (Minnesänger …)"
        elif kind == "Po" and not aimed: r = "Poe wählt niemanden (lädt auf)"
        elif kind == "Pukka":
            stale = (d.pukka_history.get(k) or (None, None))[0]
            if stale is None: r = "Pukka: kein Gift fällig (Nacht nach Exorzist oder Rausch)"
            elif stale not in d.alive_at(phase): r = "Ziel war schon tot"
            else:
                role = d.role_at(stale, phase)
                pair = d.innkeeper_guarded.get(k) or ()
                r = "Ziel geschützt: " + ("Gastwirt" if stale in pair and k not in d.innkeeper_void else "Teedame oder anderes")
        else:
            labels = []
            for t in aimed:
                role = d.role_at(t, phase); pair = d.innkeeper_guarded.get(k) or ()
                if t not in d.alive_at(phase): labels.append("tot")
                elif role == "Sailor": labels.append("Segler")
                elif role == "Fool": labels.append("Narr")
                elif t in pair: labels.append("Gastwirt")
                else: labels.append("Teedame")
            r = "Ziel geschützt: " + "+".join(sorted(labels)) if labels else "kein Ziel"
        why[kind][r] += 1
for kind in ("Shabaloth", "Pukka", "Po", "Zombuul"):
    print(f"\n{kind}: {quiet_by[kind]} stille von {nights_by[kind]} Nächten ({100*quiet_by[kind]/nights_by[kind]:.0f} %)")
    for r, c in why[kind].most_common(12): print(f"   {100*c/quiet_by[kind]:5.1f}%  {r}")
