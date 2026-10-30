#!/bin/bash
# The gate for the Plague Doctor, stage 2 (29.10.2026,
# claude/pestdoktor-stufe-2-lesarten.md): the lines without it, to see
# nothing else moved (the Hatter's, none, the Boffin's, the fixed scripts
# and their checksums), the seven lines of stage 1 again, and four with the
# Minions of stage 2.
#   bash messung/tor_pestdoktor_2.sh OUTDIR
# A line whose file is complete is skipped, so a run cut short goes on
# where it stopped. Writes `pestdoktor2.done` at the end.
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
# Stage 1 again: the Storyteller now picks from stage 2 too.
line torP 4 0 PlagueDoctor
line torPK 4 0 PlagueDoctor Poisoner Godfather Assassin
line torPH 4 0 PlagueDoctor Witch DevilsAdvocate Mastermind
line torPJ 4 0 PlagueDoctor ScarletWoman Goblin Fearmonger
line torPX 4 0 PlagueDoctor Widow Xaan Spy
line torPW 4 0 PlagueDoctor Wraith Chambermaid Philosopher
line torPB 4 0 PlagueDoctor Boffin Imp
# Stage 2: the Pit-Hag, the Mezepheles and the Summoner (A, B, C); the
# Boffin and the Baron (D, E); the Evil Twin, the Boomdandy and the
# Marionette (E, F, G); the Spy beside an Empath and an Investigator (H).
line torP2A 4 0 PlagueDoctor PitHag Mezepheles Summoner
line torP2B 4 0 PlagueDoctor Boffin Baron
line torP2C 4 0 PlagueDoctor EvilTwin Boomdandy Marionette
line torP2D 4 0 PlagueDoctor Spy Empath Investigator Undertaker
echo done > "$OUT/pestdoktor2.done"
