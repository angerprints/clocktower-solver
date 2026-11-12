#!/bin/bash
# The gate for the Hermit, stage 2b (12.11.2026, Patrick's answers to
# claude/eremit-2.md; report claude/eremit-2b.md): thinking it is the Demon
# it still uses its choosing Outsider abilities; thinking it is a Townsfolk
# the Mathematician counts it as the Drunk, where the Drunk is on the
# script. In the lines with Outsiders the Hermit is dealt more often
# (SIM_HERMIT_FAVOUR, for the gate only).
#   bash messung/tor_eremit_2b.sh OUTDIR [base|new]
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
  line torDM 4 0 Drunk Mathematician Lunatic
  for sc in TB BMR SV EASTER XNINEB; do
    f=$OUT/sim_$sc.txt
    grep -q verworfen "$f" 2>/dev/null \
      || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
  done
  grep -q SV "$OUT/hash.txt" 2>/dev/null \
    || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
  ;;
new)
  line torH0 4 0 Hermit
  export SIM_HERMIT_FAVOUR=1
  line torH8 4 0 Hermit Drunk Lunatic Chambermaid
  line torS1 4 0 Hermit Drunk Saint Klutz
  line torS2 4 0 Hermit Lunatic Butler Chambermaid
  line torS3 4 0 Hermit Drunk Lunatic Moonchild
  line torS7 4 0 Hermit Drunk Mathematician Sweetheart
  line torS8 4 0 Hermit Lunatic Klutz Moonchild
  line torS9 4 0 Hermit Lunatic Ogre Golem
  ;;
esac
echo done > "$OUT/eremit2b.$2.done"
