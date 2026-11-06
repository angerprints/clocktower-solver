#!/bin/bash
# The gate for the Alchemist with the Summoner's ability, stage 5b
# (06.11.2026, claude/alchemist-5b.md): a Philosopher's makes a second
# Demon, the Clockmaker learns 0 beside a dealt one. As stage 5
# (claude/alchemist-5.md): three lines where an Alchemist mostly gets it
# (SIM_ALCH_FAVOUR), and the lines it may move — the Summoner's, the
# Alchemist's setup, Lil' Monsta's — with the fixed scripts and their
# checksums.
#   bash messung/tor_alchemist_5.sh OUTDIR [base|new]
# "base" runs only the old lines (for main), "new" only the new ones. A
# line whose file is complete is skipped. Writes `alchemist5b.done`.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
if [ "$2" != new ]; then
  line torS4 4 0 Summoner
  line torSD 4 0 Summoner Pukka Zombuul LordOfTyphon NoDashii
  line torLM 4 0 Leviathan LilMonsta Summoner
  line torA 4 0 Alchemist
  line torAB 4 0 Alchemist Baron Godfather
  line torAG 4 0 Alchemist Godfather Xaan
  line torAF 4 0 Alchemist Boffin Philosopher
  line torJ 4 0 Hatter Leviathan Summoner
  line torE 4 0 Hatter EvilTwin Godfather Gambler Philosopher
  line tor_none 4 0
  for sc in TB BMR SV EASTER XNINEB; do
    f=$OUT/sim_$sc.txt
    grep -q verworfen "$f" 2>/dev/null \
      || { python3 messung/sim5.py $sc 3000 4 > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
  done
  grep -q SV "$OUT/hash.txt" 2>/dev/null \
    || { python3 messung/tbhash.py > "$OUT/hash.tmp" 2>&1 && mv "$OUT/hash.tmp" "$OUT/hash.txt"; }
fi
if [ "$2" != base ]; then
  # Found with this stage: an Alchemist beside Lil' Monsta (lost on main).
  line torAM5 4 0 Alchemist LilMonsta
  export SIM_ALCH_FAVOUR=Summoner
  line torZ1 4 0 Alchemist Summoner
  line torZ2 4 0 Alchemist Summoner Pukka Zombuul Clockmaker Chambermaid
  line torZ3 4 0 Alchemist Summoner LilMonsta Poisoner Courtier
  line torZ4 4 0 Alchemist Summoner Clockmaker Poisoner
  # A Philosopher that takes the Alchemist, mostly with the Summoner's.
  export SIM_PHIL_FAVOUR=Alchemist
  line torP1 4 0 Philosopher Alchemist Summoner
  line torP2 4 0 Philosopher Alchemist Summoner Pukka Clockmaker Hatter
  line torP3 4 0 Philosopher Alchemist Summoner Courtier Preacher Poisoner
fi
echo done > "$OUT/alchemist5b.done"
