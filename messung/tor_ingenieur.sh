#!/bin/bash
# The gate for the Engineer (26.10.2026): the Hatter's set, so the run can
# be laid beside the last one, and four lines that ask for the Engineer.
#   bash messung/tor_ingenieur.sh OUTDIR
# Writes `all.done` after the Hatter's set and `engineer.done` at the end.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
bash messung/tor_hutmacher.sh "$OUT"
python3 messung/tor.py 3000 4 0 Engineer > $OUT/torI.txt 2>&1
python3 messung/tor.py 3000 4 0 Engineer Summoner Leviathan > $OUT/torIS.txt 2>&1
python3 messung/tor.py 3000 4 0 Engineer SnakeCharmer PitHag Barber > $OUT/torIC.txt 2>&1
python3 messung/tor.py 3000 4 0 Engineer Pukka NoDashii Widow Lleech > $OUT/torIP.txt 2>&1
echo done > $OUT/engineer.done
