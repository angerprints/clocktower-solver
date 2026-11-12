#!/bin/bash
# The gate for the Cannibal, stage 1 (12.11.2026, Patrick's answers in
# claude/kannibale-lesarten.md; report claude/kannibale-1.md): the ability
# of the last executee, poisoned after an evil one, its rows (C). In the
# lines with other characters the Cannibal is dealt more often
# (SIM_CANNIBAL_FAVOUR, for the gate only).
#   bash messung/tor_kannibale_1.sh OUTDIR [base|new]
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
  line torPLP 4 0 Professor Lycanthrope Philosopher
  line torBof 4 0 Boffin Professor Lycanthrope
  line torSPA 4 0 SnakeCharmer PitHag Acrobat
  SIM_HERMIT_FAVOUR=1 line torH8 4 0 Hermit Drunk Lunatic Chambermaid
  for sc in TB BMR SV EASTER XNINEB; do
    f=$OUT/sim_$sc.txt
    grep -q verworfen "$f" 2>/dev/null \
      || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
  done
  grep -q SV "$OUT/hash.txt" 2>/dev/null \
    || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
  ;;
new)
  line torK0 4 0 Cannibal
  export SIM_CANNIBAL_FAVOUR=1
  line torK1 4 0 Cannibal Empath Chef Slayer
  line torK2 4 0 Cannibal Gambler Juggler Mathematician
  line torK3 4 0 Cannibal SnakeCharmer Professor Juggler
  line torK4 4 0 Cannibal Professor Lycanthrope Philosopher
  line torK5 4 0 Cannibal Klutz Moonchild Saint
  line torK6 4 0 Cannibal Chambermaid Innkeeper Sailor
  line torK7 4 0 Cannibal Sweetheart Monk Undertaker
  line torK8 4 0 Cannibal Ravenkeeper Virgin Huntsman
  ;;
esac
echo done > "$OUT/kannibale1.$2.done"
