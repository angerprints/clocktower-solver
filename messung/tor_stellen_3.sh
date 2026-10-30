#!/bin/bash
# The gate for Stellen-Paket 3 (30.10.2026: seed 91, Stellen 82 a, 48 a,
# 48 e, seed 1753): five lines that ask for what the package touched —
# the Village Idiots beside a Lleech (91), the Minstrel beside a Harpy and
# a Professor (82 a), the Philosopher beside a Snake Charmer (48 a), the
# Moonchild beside a Snake Charmer and a Fang Gu (48 e), the Slayer beside
# a Scarlet Woman and a Psychopath (1753) — then everything the gate of
# package 2 ran.
#   bash messung/tor_stellen_3.sh OUTDIR [extra]
# With `extra`, only the five new lines (for a baseline on main).
# A line whose file is complete is skipped. Writes `stellen3.done`.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torVL 4 0 VillageIdiot Lleech Preacher
line torMH 4 0 Minstrel Harpy Professor
line torPS 4 0 Philosopher SnakeCharmer Hatter
line torMS 4 0 Moonchild SnakeCharmer FangGu
line torSW 4 0 Slayer ScarletWoman Psychopath
if [ "$2" != extra ]; then
  bash messung/tor_stellen_2.sh "$OUT"
fi
echo done > "$OUT/stellen3.done"
