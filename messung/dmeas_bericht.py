"""How often the Demon is ranked first, overall and split by the good
players' lies (15.11.2026, B Weg 1).

    python3 messung/dmeas_bericht.py OUT.jsonl [BEFORE.jsonl]

"keine" are honest boards, "versteckt" an Outsider hiding behind a
Townsfolk claim, "Chaos" a good player claiming something for no reason
(tests/claims.py). With a second file, games are matched by seed and the
games newly first and no longer first are counted per group too.
"""
import collections
import json
import sys


def load(path):
    return {r["seed"]: r for r in map(json.loads, open(path))}


def group(r):
    return "mit Chaos" if "Chaos" in r.get("lie", "") else "ohne Chaos"


def main():
    now = load(sys.argv[1])
    before = load(sys.argv[2]) if len(sys.argv) > 2 else {}
    rows = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for seed, r in now.items():
        for g in ("alle", group(r)):
            row = rows[g]
            row[0] += 1
            row[1] += r["rank"] == 1
            row[4] += not r["ok"]
            b = before.get(seed)
            if b:
                row[2] += r["rank"] == 1 and b["rank"] != 1
                row[3] += r["rank"] != 1 and b["rank"] == 1
    if any("lie" not in r for r in now.values()):
        print("Achtung: Partien ohne Feld 'lie' zählen als 'ohne Chaos'.")
    for g in ("alle", "ohne Chaos", "mit Chaos"):
        n, top, new, lost, bad = rows[g]
        if not n:
            continue
        line = f"{g:11s} {n:5d} Partien, Dämon vorn {top:5d} ({100 * top / n:.0f} %)"
        if before:
            line += f", neu vorn {new}, nicht mehr vorn {lost}"
        print(line + f", wahre Welt verloren {bad}")


if __name__ == "__main__":
    main()
