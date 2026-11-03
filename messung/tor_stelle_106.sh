#!/bin/bash
# The gate for Stelle 106 (03.11.2026): the simulator makes a Farmer's
# heir at the Farmer's place (690), after the Barber's swap (590) and the
# Huntsman (660), and no longer keeps the fresh heir out of the swap.
#   bash messung/tor_stelle_106.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torBF 4 0 Barber Farmer PitHag
line torHF 4 0 PitHag Farmer Politician
line torBH 4 0 Barber Huntsman Damsel
line torFB 4 0 Farmer Barber Leviathan
