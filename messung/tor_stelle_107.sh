#!/bin/bash
# The gate for Stelle 107 (03.11.2026): a dead Barber the Al-Hadikhia
# chose may have died again that night and its Demon swap again; and a
# story that swapped already is told on with the next night's swap.
#   bash messung/tor_stelle_107.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torAM 4 0 AlHadikhia Monk Innkeeper TeaLady Goon
line torAB 4 0 AlHadikhia Barber Monk
line torBF 4 0 Barber Farmer PitHag
line torBP 4 0 Barber Philosopher PitHag
