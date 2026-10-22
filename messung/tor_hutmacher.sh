#!/bin/bash
# The gate set used for the Hatter (22.10.2026), its first stage, as one run.
#   bash messung/tor_hutmacher.sh OUTDIR
# Writes one file per line into OUTDIR and `all.done` at the end. About
# 15 minutes; start it in the background and look into OUTDIR later.
# Every line asks for the Hatter, so `tor.py` also counts the tea parties,
# the games it leaves out as not reckoned yet, and the lost games whose
# Hatter nobody claimed (T, the Barber's price).
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
python3 messung/tor.py 3000 4 0 Hatter > $OUT/tor4.txt 2>&1
python3 messung/tor.py 3000 6 0 Hatter > $OUT/tor6.txt 2>&1
python3 messung/tor.py 3000 4 0 Hatter Widow Poisoner Chambermaid > $OUT/torW.txt 2>&1
python3 messung/tor.py 3000 4 0 Hatter Leviathan Summoner > $OUT/torJ.txt 2>&1
python3 messung/tor.py 3000 4 0 Hatter EvilTwin Godfather Gambler Philosopher > $OUT/torE.txt 2>&1
python3 messung/tor.py 3000 4 0 Hatter Marionette Lunatic Drunk ScarletWoman > $OUT/torM.txt 2>&1
python3 messung/tor.py 3000 4 0 Hatter Imp Po NoDashii > $OUT/torD.txt 2>&1
python3 messung/tor.py 3000 4 0 > $OUT/tor_none.txt 2>&1
for sc in TB BMR SV EASTER XNINEB; do python3 messung/sim5.py $sc 3000 4 > $OUT/sim_$sc.txt 2>&1; done
python3 messung/tbhash.py > $OUT/hash.txt 2>&1
echo done > $OUT/all.done
