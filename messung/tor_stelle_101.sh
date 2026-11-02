#!/bin/bash
# The gate for Stelle 101 (02.11.2026): a Philosopher somebody made later
# — the Pit-Hag, the Huntsman's Damsel, the Barber — chooses on its first
# night it can. Three lines that make one.
#   bash messung/tor_stelle_101.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torPP 4 0 PitHag Philosopher
line torHP 4 0 Huntsman Damsel Philosopher
line torBP 4 0 Barber Philosopher
line torTP 4 0 Hatter EvilTwin Godfather Gambler Philosopher
