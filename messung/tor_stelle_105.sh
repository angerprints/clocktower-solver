#!/bin/bash
# The gate for Stelle 105 (03.11.2026): a droisoned seat the Pit-Hag made
# after its place waits for its next night too (Lesart K), the solver's
# Innkeeper is read only at its turn, and the Goon answers a Snake
# Charmer in the simulator.
#   bash messung/tor_stelle_105.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torP2A 4 0 PlagueDoctor PitHag Mezepheles Summoner
line torGS 4 0 Philosopher Grandmother SnakeCharmer
line torIH 4 0 Innkeeper PitHag NoDashii
line torSG 4 0 SnakeCharmer Goon Ojo
