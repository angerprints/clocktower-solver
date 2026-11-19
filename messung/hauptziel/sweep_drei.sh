#!/bin/bash
# usage: sweep.sh NAME=V ... ; runs each sequentially at final 3
for nv in "$@"; do
  f=messung/daten/hauptziel/versuche/letzte3/S3_${nv//=/_}.jsonl
  rm -f $f
  timeout 3000 python3 messung/hauptziel/setze_drei.py $nv TB $f messung/daten/hauptziel/TB_600_91c9e69.jsonl >/dev/null 2>&1
done
