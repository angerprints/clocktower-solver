#!/bin/bash
# The gate for Stelle 5 (01.11.2026: the lost seeds 77, 2442, 2799, 447,
# 2507 and 1931 with a claimed Barber): four lines that ask for what it
# touched — a Barber beside a No Dashii and its Townsfolk (2442), a
# Barber beside a Farmer (1931, 2799), a Huntsman finding a Damsel the
# Barber moved (447, 77), a Barber beside a Lycanthrope (2507) — then
# everything the gate of package 5 ran.
#   bash messung/tor_stelle_5.sh OUTDIR [extra]
# With `extra`, only the four new lines (for a baseline on main).
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torBN 4 0 Barber NoDashii Investigator
line torBF 4 0 Barber Farmer PitHag
line torBH 4 0 Barber Huntsman Damsel
line torBL 4 0 Barber Lycanthrope Yaggababble
if [ "$2" != extra ]; then
  bash messung/tor_stellen_5.sh "$OUT"
fi
