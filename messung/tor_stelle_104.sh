#!/bin/bash
# The gate for Stelle 104 (02.11.2026): a source of drunkenness or poison
# whose actor dies in the night stops there and does not reach the day.
#   bash messung/tor_stelle_104.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torTG 4 0 TeaLady SnakeCharmer Gambler
line torIP 4 0 Innkeeper Poisoner TeaLady Sailor Saint
