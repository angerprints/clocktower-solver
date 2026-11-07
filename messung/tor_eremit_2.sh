#!/bin/bash
# The gate for the Hermit, stage 2 (07.11.2026, claude/eremit-lesarten.md,
# claude/eremit-2.md): with the Drunk's ability it thinks it is a
# Townsfolk, with the Lunatic's the Demon (B, C); the Damsel's jinxes
# poison it whole and the Heretic's keep it from the Minions they name
# (D); with the Recluse's ability it misregisters in the simulator too
# (Patrick, 07.11.2026). In the lines "H" and "S" the Hermit is dealt
# more often (SIM_HERMIT_FAVOUR, for the gate only).
#   bash messung/tor_eremit_2.sh OUTDIR [base|new1|new2]
# A line whose file is complete is skipped. Writes `eremit2.<part>.done`.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
case "$2" in
base)
  line tor_none 4 0
  line torDL 4 0 Drunk Lunatic Marionette Chambermaid
  line torPR 4 0 Philosopher Recluse Slayer
  for sc in TB BMR SV EASTER XNINEB; do
    f=$OUT/sim_$sc.txt
    grep -q verworfen "$f" 2>/dev/null \
      || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
  done
  grep -q SV "$OUT/hash.txt" 2>/dev/null \
    || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
  ;;
new1)
  line torH0 4 0 Hermit
  export SIM_HERMIT_FAVOUR=1
  line torH1 4 0 Hermit Saint Klutz Moonchild
  line torH2 4 0 Hermit Sweetheart Barber Tinker
  line torH3 4 0 Hermit Golem Goon Ogre Chambermaid
  line torH4 4 0 Hermit Damsel Puzzlemaster Recluse
  line torH5 4 0 Hermit Hatter PlagueDoctor Butler Chambermaid
  ;;
new2)
  export SIM_HERMIT_FAVOUR=1
  line torH6 4 0 Hermit Baron Godfather Vigormortis
  line torH7 4 0 Hermit Huntsman Damsel Philosopher
  line torH8 4 0 Hermit Drunk Lunatic Chambermaid
  line torS1 4 0 Hermit Drunk Saint Klutz
  line torS2 4 0 Hermit Lunatic Butler Chambermaid
  line torS3 4 0 Hermit Drunk Lunatic Moonchild
  line torS4 4 0 Hermit Damsel Spy Widow
  line torS5 4 0 Hermit Heretic Baron Spy
  line torS6 4 0 Hermit Recluse Empath FortuneTeller Investigator Slayer
  line torS7 4 0 Hermit Drunk Mathematician Sweetheart
  ;;
esac
echo done > "$OUT/eremit2.$2.done"
