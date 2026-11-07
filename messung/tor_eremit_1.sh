#!/bin/bash
# The gate for the Hermit, stage 1 (07.11.2026, claude/eremit-lesarten.md,
# claude/eremit-1.md): every Outsider ability of the script but the
# Drunk's and the Lunatic's, and "[-0 or -1 Outsider]" with the Hermit
# itself the one taken out (A). In the lines "H" the Hermit is dealt more
# often (SIM_HERMIT_FAVOUR, for the gate only). The base lines are those
# the simulator's fix for two Goons in one night may move, the fixed
# scripts and their checksums.
#   bash messung/tor_eremit_1.sh OUTDIR [base|new]
# "base" runs only the old lines (for main), "new" only the new ones. A
# line whose file is complete is skipped. Writes `eremit1.done`.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
if [ "$2" != new ]; then
  line tor_none 4 0
  line torPG 4 0 Philosopher Goon
  line torPGC 4 0 Philosopher Goon Courtier Sailor
  for sc in TB BMR SV EASTER XNINEB; do
    f=$OUT/sim_$sc.txt
    grep -q verworfen "$f" 2>/dev/null \
      || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
  done
  grep -q SV "$OUT/hash.txt" 2>/dev/null \
    || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
fi
if [ "$2" != base ]; then
  line torH0 4 0 Hermit
  export SIM_HERMIT_FAVOUR=1
  line torH1 4 0 Hermit Saint Klutz Moonchild
  line torH2 4 0 Hermit Sweetheart Barber Tinker
  line torH3 4 0 Hermit Golem Goon Ogre Chambermaid
  line torH4 4 0 Hermit Damsel Puzzlemaster Recluse
  line torH5 4 0 Hermit Hatter PlagueDoctor Butler Chambermaid
  line torH6 4 0 Hermit Baron Godfather Vigormortis
  line torH7 4 0 Hermit Huntsman Damsel Philosopher
  line torH8 4 0 Hermit Drunk Lunatic Chambermaid
fi
echo done > "$OUT/eremit1.done"
