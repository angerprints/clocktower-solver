#!/bin/bash
# The gate for the Boffin, stage 1 (26.10.2026): the Engineer's set (the
# Hatter's and four Engineer lines), so the run can be laid beside the last
# one, and five lines that ask for the Boffin.
#   bash messung/tor_laborratte.sh OUTDIR
# Writes `all.done` after the Hatter's set, `engineer.done` after the
# Engineer's lines and `boffin.done` at the end.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
bash messung/tor_ingenieur.sh "$OUT"
python3 messung/tor.py 3000 4 0 Boffin > $OUT/torL.txt 2>&1
# Who dies and who does not: the abilities it may give on the script.
python3 messung/tor.py 3000 4 0 Boffin Fool Sailor Soldier Monk TeaLady > $OUT/torLS.txt 2>&1
# Who is drunk: a Boffin that may be poisoned, and the drunk-makers.
python3 messung/tor.py 3000 4 0 Boffin Poisoner Courtier Minstrel Goon > $OUT/torLD.txt 2>&1
# New Demons (C Weg 1): the star moving, a swap, a Pit-Hag's Demon.
python3 messung/tor.py 3000 4 0 Boffin ScarletWoman SnakeCharmer PitHag Barber > $OUT/torLN.txt 2>&1
# Two living Demons (D Weg 2) and a Boffin made in the middle (I Weg 1).
python3 messung/tor.py 3000 4 0 Boffin Summoner Engineer Hatter > $OUT/torL2.txt 2>&1
echo done > $OUT/boffin.done
