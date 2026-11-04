#!/bin/bash
# The gate for the Alchemist, group 1 (04.11.2026, claude/alchemist-
# gruppen.md): the lines without it, to see nothing else moved (the
# Hatter's, none, the Boffin's, the Plague Doctor's, the fixed scripts and
# their checksums), and six lines with it.
#   bash messung/tor_alchemist.sh OUTDIR [base]
# With "base" only the lines without it run (for main, which has none).
# A line whose file is complete is skipped, so a run cut short goes on
# where it stopped. Writes `alchemist.done` at the end.
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
line torP 4 0 PlagueDoctor
for sc in TB BMR SV EASTER XNINEB; do
  f=$OUT/sim_$sc.txt
  grep -q verworfen "$f" 2>/dev/null \
    || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
done
grep -q SV "$OUT/hash.txt" 2>/dev/null \
  || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
if [ "$2" != base ]; then
  # The Alchemist: alone, then beside the Minions of group 1 — poison and
  # death at night (K), executions and curses (H), madness and fear (C),
  # a Chambermaid that counts it and a Philosopher that may take it (W),
  # and a Plague Doctor whose gift runs through the same marks (P).
  line torA 4 0 Alchemist
  line torAK 4 0 Alchemist Poisoner Assassin
  line torAH 4 0 Alchemist Witch DevilsAdvocate
  line torAC 4 0 Alchemist Cerenovus Fearmonger Harpy
  line torAW 4 0 Alchemist Chambermaid Philosopher
  line torAP 4 0 Alchemist PlagueDoctor
  # Patrick's answers of 04.11.2026: its Assassin may hit the Demon, its
  # save and a Devil's Advocate's both count, and a Philosopher that takes
  # it has a Minion ability of its own.
  line torAX 4 0 Alchemist Assassin DevilsAdvocate Philosopher
  # Group 2 (04.11.2026): the Minions that change the setup, beside a dealt
  # one (A: both count).
  line torAB 4 0 Alchemist Baron Godfather
  line torAG 4 0 Alchemist Godfather Xaan
fi
echo done > "$OUT/alchemist.done"
