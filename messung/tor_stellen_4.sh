#!/bin/bash
# The gate for Stellen-Paket 4 (31.10.2026: Stellen 42, 82 b and the seeds
# 1877, 108, 2126, 46, 2040): seven lines that ask for what the package
# touched — a Spy the Preacher silenced beside Village Idiots (42), the
# Vortox beside the Seamstress, the Shugenja and the Lycanthrope (82 b), a
# Pit-Hag beside a Farmer (1877), an Acrobat beside a Pit-Hag (108), a
# Philosopher's Nightwatchman under a Vortox (2126), a Tea Lady beside a
# Snake Charmer and a Gambler (46), a Philosopher's Damsel (2040) — then
# everything the gate of package 3 ran.
#   bash messung/tor_stellen_4.sh OUTDIR [extra]
# With `extra`, only the seven new lines (for a baseline on main).
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torVP 4 0 VillageIdiot Preacher Spy
line torVS 4 0 Vortox Seamstress Shugenja Lycanthrope
line torHF 4 0 PitHag Farmer Politician
line torAH 4 0 Acrobat PitHag
line torNV 4 0 Nightwatchman Philosopher Vortox
line torTG 4 0 TeaLady SnakeCharmer Gambler
line torDP 4 0 Damsel Philosopher Huntsman
if [ "$2" != extra ]; then
  bash messung/tor_stellen_3.sh "$OUT"
fi
echo done > "$OUT/stellen4.done"
