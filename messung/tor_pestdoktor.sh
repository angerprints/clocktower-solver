#!/bin/bash
# The gate for the Plague Doctor, stage 1 (28.10.2026,
# claude/pestdoktor-lesarten.md): the lines without it, to see nothing
# else moved (the Hatter's, none, the Boffin's, the fixed scripts and their
# checksums), and seven lines with it.
#   bash messung/tor_pestdoktor.sh OUTDIR
# A line whose file is complete is skipped, so a run cut short goes on
# where it stopped. Writes `pestdoktor.done` at the end.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line tor4 4 0 Hatter
line tor_none 4 0
line torL 4 0 Boffin
for sc in TB BMR SV EASTER XNINEB; do
  f=$OUT/sim_$sc.txt
  grep -q verworfen "$f" 2>/dev/null \
    || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
done
grep -q SV "$OUT/hash.txt" 2>/dev/null \
  || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
# The Plague Doctor: alone, then beside the Minions of each group of stage
# 1 — poison and death at night (K), executions (H), the jinxed ones (J),
# the Widow, the Xaan and the Spy (X), the Wraith a Chambermaid counts and
# a Philosopher that may take it (W), and a Boffin that may give it (B).
line torP 4 0 PlagueDoctor
line torPK 4 0 PlagueDoctor Poisoner Godfather Assassin
line torPH 4 0 PlagueDoctor Witch DevilsAdvocate Mastermind
line torPJ 4 0 PlagueDoctor ScarletWoman Goblin Fearmonger
line torPX 4 0 PlagueDoctor Widow Xaan Spy
line torPW 4 0 PlagueDoctor Wraith Chambermaid Philosopher
line torPB 4 0 PlagueDoctor Boffin Imp
echo done > "$OUT/pestdoktor.done"
