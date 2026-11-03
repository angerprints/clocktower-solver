#!/bin/bash
# The gate for Stelle 111 (03.11.2026): Pit-Hag nights where the
# night-walk and the simulator disagreed (the Goon, the Acrobat, a new
# Lleech), and seed 729. The four lines of Stelle 110, and two more for
# the Acrobat beside a Snake Charmer and the Goon beside a Pit-Hag.
#   bash messung/tor_stelle_111.sh OUTDIR [neu]
# With `neu`, only the two new lines (for a baseline on main).
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
if [ "$2" != neu ]; then
  export SIM_PIT_HAG_DEMONS=0.5
  line torHB 4 0 PitHag Barber SnakeCharmer
  line torHS 4 0 PitHag ScarletWoman FangGu
  line torHP 4 0 PitHag
  unset SIM_PIT_HAG_DEMONS
  line torP0 4 0 PitHag
fi
line torAS 4 0 Acrobat SnakeCharmer
SIM_PIT_HAG_DEMONS=0.5 line torHG 4 0 PitHag Goon
