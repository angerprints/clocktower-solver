#!/bin/bash
# The gate for the Cannibal, stage 2 (13.11.2026, Patrick's answers in
# claude/kannibale-2-lesarten.md; report claude/kannibale-2.md): the
# Drunk, the Lunatic, the Philosopher and the Hermit as meals, and the
# jinxes. In the new lines the Cannibal is dealt more often
# (SIM_CANNIBAL_FAVOUR) and the characters it should eat are executed more
# often (SIM_CANNIBAL_MEAL), for the gate only.
#   bash messung/tor_kannibale_2.sh OUTDIR [base|new]
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
  line torK4 4 0 Cannibal Professor Lycanthrope Philosopher
  SIM_CANNIBAL_MEAL=Philosopher line torP1 4 0 Cannibal Philosopher Empath Chef
  SIM_CANNIBAL_MEAL=Philosopher line torP2 4 0 Cannibal Philosopher SnakeCharmer Innkeeper
  SIM_CANNIBAL_MEAL=Philosopher line torP3 4 0 Cannibal Philosopher Chambermaid Mathematician
  SIM_CANNIBAL_MEAL=Drunk,Lunatic line torD1 4 0 Cannibal Drunk Lunatic Chambermaid
  SIM_CANNIBAL_MEAL=Drunk line torD2 4 0 Cannibal Drunk Mathematician Empath
  SIM_CANNIBAL_MEAL=Hermit line torE1 4 0 Cannibal Hermit Klutz Butler
  SIM_CANNIBAL_MEAL=Hermit line torE2 4 0 Cannibal Hermit Recluse Saint
  SIM_CANNIBAL_MEAL=Princess,Juggler,Zealot line torJ1 4 0 Cannibal Princess Zealot Juggler
  ;;
esac
echo done > "$OUT/kannibale2.$2.done"
