#!/bin/bash
# The gate for Stellen-Paket 2 (30.10.2026: Stellen 64, 65, 67, 69, 41):
# six lines that ask for what the package touched — the Mathematician
# beside the Vortox (64) and beside a Courtier and a Philosopher, the
# Huntsman, the Damsel and the Pixie (65), the Al-Hadikhia beside a Tea
# Lady (67) and beside a Professor (69), the Fang Gu beside an Innkeeper
# (41) — and then everything the gate of package 1 ran.
#   bash messung/tor_stellen_2.sh OUTDIR [extra]
# With `extra`, only the six new lines (for a baseline on main).
# A line whose file is complete is skipped. Writes `stellen2.done`.
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torMV 4 0 Mathematician Vortox
line torMC 4 0 Mathematician Courtier Philosopher Xaan
line torHP 4 0 Huntsman Damsel Pixie
line torAT 4 0 AlHadikhia Monk Innkeeper TeaLady Goon
line torAP 4 0 AlHadikhia Grandmother Professor Shabaloth
line torFI 4 0 FangGu Innkeeper Mutant
if [ "$2" != extra ]; then
  bash messung/tor_stellen_1.sh "$OUT"
fi
echo done > "$OUT/stellen2.done"
