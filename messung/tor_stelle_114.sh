#!/bin/bash
# The gate for Stelle 114 (03.11.2026): an Innkeeper or a Sailor the Xaan
# poisons on its night drunks nobody. The line of Stelle 104 where the two
# seeds were lost, two with the Xaan asked for, and the line of Stelle 115.
#   bash messung/tor_stelle_114.sh OUTDIR
cd "$(dirname "$0")/.."
OUT=$1
mkdir -p "$OUT"
line() {
  f=$OUT/$1.txt; shift
  grep -q "Zeilen:" "$f" 2>/dev/null && return
  python3 messung/tor.py 3000 "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"
}
line torIP 4 0 Innkeeper Poisoner TeaLady Sailor Saint
line torXI 4 0 Xaan Innkeeper Damsel
line torXS 4 0 Xaan Sailor TeaLady
# Stelle 115: the line Innkeeper, Pit-Hag, No Dashii of Stelle 105.
line torIH 4 0 Innkeeper PitHag NoDashii
