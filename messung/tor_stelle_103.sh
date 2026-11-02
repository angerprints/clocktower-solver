#!/bin/bash
# The gate for Stelle 103 (02.11.2026): the Monk choosing the Goon. The
# Goon answered every chooser but the Monk, so a later one read as first.
#   bash messung/tor_stelle_103.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torAT 4 0 AlHadikhia Monk Innkeeper TeaLady Goon
line torMG 4 0 Monk Goon
