#!/bin/bash
# The gate set used for the Summoner (21./22.10.2026), as one run.
#   bash messung/tor_beschwoerer.sh OUTDIR
# Writes one file per line into OUTDIR and `all.done` at the end. About
# 25 minutes; start it in the background and look into OUTDIR later.
# Compare two runs with `diff` on the third line of each tor*.txt.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
python3 messung/tor.py 3000 4 0 Summoner > $OUT/tor4.txt 2>&1
python3 messung/tor.py 3000 6 0 Summoner > $OUT/tor6.txt 2>&1
python3 messung/tor.py 3000 4 0 Summoner SnakeCharmer Exorcist Chambermaid > $OUT/torS.txt 2>&1
python3 messung/tor.py 3000 4 0 Summoner Clockmaker Courtier Preacher Marionette PoppyGrower > $OUT/torJ.txt 2>&1
python3 messung/tor.py 3000 4 0 Summoner Pukka Zombuul LordOfTyphon NoDashii > $OUT/torD.txt 2>&1
python3 messung/tor.py 3000 4 0 Summoner ScarletWoman Mastermind Slayer Professor > $OUT/torM.txt 2>&1
python3 messung/tor.py 3000 4 0 Summoner Marionette Lunatic Drunk > $OUT/torL.txt 2>&1
python3 messung/tor.py 3000 4 0 > $OUT/tor_none.txt 2>&1
for sc in TB BMR SV EASTER XNINEB; do python3 messung/sim5.py $sc 3000 4 > $OUT/sim_$sc.txt 2>&1; done
python3 messung/tbhash.py > $OUT/hash.txt 2>&1
python3 messung/seite.py 0 300 4 Summoner > $OUT/seite.txt 2>&1
echo done > $OUT/all.done
