#!/bin/bash
# The gate for Stelle 112 (03.11.2026): a drunk or poisoned Monk still
# chooses, and the Goon answers it. Two lines with Monk and Goon, and the
# Al-Hadikhia line of Stelle 103/107.
#   bash messung/tor_stelle_112.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torMG 4 0 Monk Goon Poisoner
line torMX 4 0 Monk Goon Xaan
line torAM 4 0 AlHadikhia Monk Innkeeper TeaLady Goon
