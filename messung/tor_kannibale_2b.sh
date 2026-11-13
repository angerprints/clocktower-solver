#!/bin/bash
# The gate for the Cannibal, stage 2b (13.11.2026): the Alchemist as a
# meal, with the Minion ability that Alchemist had (D in
# claude/kannibale-2-lesarten.md; report claude/kannibale-2b.md). In the
# new lines the Cannibal is dealt more often (SIM_CANNIBAL_FAVOUR), the
# Alchemist executed more often (SIM_CANNIBAL_MEAL) and one Minion ability
# given it more often (SIM_ALCH_FAVOUR), for the gate only.
#   bash messung/tor_kannibale_2b.sh OUTDIR [base|new]
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
  bash messung/tor_kannibale_2.sh "$OUT" base
  ;;
new)
  line torK0 4 0 Cannibal
  export SIM_CANNIBAL_FAVOUR=1 SIM_CANNIBAL_MEAL=Alchemist
  line torA0 4 0 Cannibal Alchemist Empath Chef
  SIM_ALCH_FAVOUR=Poisoner line torA1 4 0 Cannibal Alchemist Empath Mathematician
  SIM_ALCH_FAVOUR=Witch line torA2 4 0 Cannibal Alchemist Klutz Chambermaid
  SIM_ALCH_FAVOUR=Assassin line torA3 4 0 Cannibal Alchemist Undertaker Monk
  SIM_ALCH_FAVOUR=PitHag line torA4 4 0 Cannibal Alchemist Chambermaid Oracle
  SIM_ALCH_FAVOUR=Cerenovus line torA5 4 0 Cannibal Alchemist Empath Juggler
  ;;
esac
echo done > "$OUT/kannibale2b.$2.done"
