#!/bin/bash
# The gate for the Boffin, stage 2 (27.10.2026): the gate of stage 1 (the
# Hatter's set, the Engineer's lines, five Boffin lines) and three lines
# for what stage 2 reckons.
#   bash messung/tor_laborratte_2.sh OUTDIR
# A line whose file is complete is skipped, so a run cut short goes on
# where it stopped. Writes `boffin2.done` at the end.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line tor4 4 0 Hatter
line tor6 6 0 Hatter
line torW 4 0 Hatter Widow Poisoner Chambermaid
line torJ 4 0 Hatter Leviathan Summoner
line torE 4 0 Hatter EvilTwin Godfather Gambler Philosopher
line torM 4 0 Hatter Marionette Lunatic Drunk ScarletWoman
line torD 4 0 Hatter Imp Po NoDashii
line tor_none 4 0
for sc in TB BMR SV EASTER XNINEB; do
  f=$OUT/sim_$sc.txt
  grep -q verworfen "$f" 2>/dev/null \
    || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
done
grep -q SV "$OUT/hash.txt" 2>/dev/null \
  || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
line torI 4 0 Engineer
line torIS 4 0 Engineer Summoner Leviathan
line torIC 4 0 Engineer SnakeCharmer PitHag Barber
line torIP 4 0 Engineer Pukka NoDashii Widow Lleech
line torL 4 0 Boffin
line torLS 4 0 Boffin Fool Sailor Soldier Monk TeaLady
line torLD 4 0 Boffin Poisoner Courtier Minstrel Goon
line torLN 4 0 Boffin ScarletWoman SnakeCharmer PitHag Barber
# In 12 pieces of 250: a game of it (seed 2189) takes hours, and a piece
# survives a restart (Stelle 92, Weg 1, 28.10.2026). The pieces are added
# up by hand; each prints its own summary.
for start in 0 250 500 750 1000 1250 1500 1750 2000 2250 2500 2750; do
  f=$OUT/torL2_$start.txt
  grep -q "Zeilen:" "$f" 2>/dev/null && continue
  python3 messung/tor.py 250 4 $start Boffin Summoner Engineer Hatter \
    > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
done
# Stage 2: abilities that act (N, H, M), the brackets (E), and the gifts
# only a row names (L) beside new Demons.
line torLA 4 0 Boffin Professor Engineer Nightwatchman Pixie Philosopher
line torLE 4 0 Boffin Balloonist Huntsman Damsel Choirboy BountyHunter
line torLB 4 0 Boffin Barber Hatter ScarletWoman Imp
echo done > "$OUT/boffin2.done"
