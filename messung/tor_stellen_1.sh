#!/bin/bash
# The gate for Stellen-Paket 1 (30.10.2026: Stellen 78, 94, 95, 97, 87):
# everything the Plague Doctor's stage-2 gate ran, to see nothing else
# moved, and five lines that ask for what the package touched — the
# Engineer's (87), Lil' Monsta beside the Summoner (78), the Gambler (94),
# the Huntsman with the Damsel, the Barber and the Philosopher (95, 97).
#   bash messung/tor_stellen_1.sh OUTDIR [extra]
# With `extra`, only the five new lines (for a baseline on main).
# A line whose file is complete is skipped. Writes `stellen1.done`.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torI 4 0 Engineer
line torLM 4 0 Leviathan LilMonsta Summoner
line torG 4 0 Gambler
line torHD 4 0 Huntsman Damsel Barber Philosopher Chambermaid
if [ "$2" != extra ]; then
  bash messung/tor_pestdoktor_2.sh "$OUT"
fi
echo done > "$OUT/stellen1.done"
