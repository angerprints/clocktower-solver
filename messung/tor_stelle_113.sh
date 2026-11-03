#!/bin/bash
# The gate for Stelle 113 (03.11.2026): sources whose holder dies in the
# night cover the night and not the day after — the No Dashii, the
# Vigormortis, the Pukka and the Goon, as Stelle 104 did for those with
# an actor.
#   bash messung/tor_stelle_113.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torND 4 0 NoDashii Slayer Gossip
line torVG 4 0 Vigormortis Goon Slayer
line torPK 4 0 Pukka Slayer Gossip
line torGS 4 0 Goon Slayer Monk
