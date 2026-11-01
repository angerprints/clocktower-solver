#!/bin/bash
# The gate for Stelle 83 (01.11.2026): a Pit-Hag that makes a Demon beside
# the Demon in play. The simulator does it only when asked
# (`SIM_PIT_HAG_DEMONS`, C Weg 2), so the first five lines ask for it on
# half the Pit-Hag's turns; the last three do not, and must match main.
#   bash messung/tor_stelle_83.sh OUTDIR [plain]
# With `plain`, only the three lines without the switch (for a baseline
# on main).
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
if [ "$2" != plain ]; then
  export SIM_PIT_HAG_DEMONS=0.5
  line torHP 4 0 PitHag
  line torHS 4 0 PitHag ScarletWoman FangGu
  line torHV 4 0 PitHag Vortox Flowergirl
  line torHG 4 0 PitHag Grandmother Monk
  line torHB 4 0 PitHag Barber SnakeCharmer
  unset SIM_PIT_HAG_DEMONS
fi
line torP0 4 0 PitHag
line torJ0 4 0 Hatter Leviathan Summoner
line torN0 4 0
