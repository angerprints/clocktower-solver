#!/bin/bash
# The gate for Stellen-Paket 5 (31.10.2026: the lost seeds 208, 2183, 109,
# 2268, 2709, 590, 768, 418 and 885): seven lines that ask for what the
# package touched — a Cult Leader under a Vortox and a Pit-Hag (208, 2709),
# a Chambermaid counting a Pit-Hag's late creation (109, Lesart K), a
# Gambler choosing a Goon the Fang Gu jumps into (2268), a Snake Charmer
# taking the Lleech (590), a Huntsman's Damsel made the Minstrel (768), a
# Summoner's Marionette believing the Lycanthrope (418), a Philosopher's
# Grandmother beside a Snake Charmer (885, Weg 1) — then everything the
# gate of package 4 ran.
#   bash messung/tor_stellen_5.sh OUTDIR [extra]
# With `extra`, only the seven new lines (for a baseline on main).
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torCV 4 0 CultLeader Vortox PitHag
line torKC 4 0 Chambermaid PitHag Courtier
line torGF 4 0 Goon FangGu Gambler
line torLS 4 0 Lleech SnakeCharmer Gambler
line torMD 4 0 Minstrel Huntsman Damsel
line torSL 4 0 Summoner Marionette Lycanthrope
line torGS 4 0 Philosopher Grandmother SnakeCharmer
if [ "$2" != extra ]; then
  bash messung/tor_stellen_4.sh "$OUT"
fi
echo done > "$OUT/stellen5.done"
