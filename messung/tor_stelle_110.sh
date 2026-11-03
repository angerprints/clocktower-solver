#!/bin/bash
# The gate for Stelle 110 (03.11.2026): the side a Pit-Hag's player keeps
# is read at the Pit-Hag's turn, not as the night began. Three lines with
# the Pit-Hag making Demons on half its turns (`SIM_PIT_HAG_DEMONS`, as in
# Stelle 83) and one without.
#   bash messung/tor_stelle_110.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
export SIM_PIT_HAG_DEMONS=0.5
line torHB 4 0 PitHag Barber SnakeCharmer
line torHS 4 0 PitHag ScarletWoman FangGu
line torHP 4 0 PitHag
unset SIM_PIT_HAG_DEMONS
line torP0 4 0 PitHag
