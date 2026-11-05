#!/bin/bash
# The gate for Stelle 117 (05.11.2026): the Boffin gives at the setup,
# before anybody acts. The Boffin lines of `tor_laborratte_2.sh` (without
# the hours-long torL2) and one for a Huntsman's Damsel beside the Boffin.
#   bash messung/tor_stelle_117.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torLH 4 0 Boffin Huntsman Damsel SnakeCharmer
line torL 4 0 Boffin
line torLS 4 0 Boffin Fool Sailor Soldier Monk TeaLady
line torLD 4 0 Boffin Poisoner Courtier Minstrel Goon
line torLN 4 0 Boffin ScarletWoman SnakeCharmer PitHag Barber
line torLA 4 0 Boffin Professor Engineer Nightwatchman Pixie Philosopher
line torLE 4 0 Boffin Balloonist Huntsman Damsel Choirboy BountyHunter
line torLB 4 0 Boffin Barber Hatter ScarletWoman Imp
grep -q SV "$OUT/hash.txt" 2>/dev/null \
  || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
echo done > "$OUT/s117.done"
