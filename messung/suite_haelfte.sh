#!/bin/bash
# One half of the test suite, each file on its own, one after the other.
#   bash messung/suite_haelfte.sh OUTFILE test_a test_b ...
# Run two halves side by side in the background (the whole suite takes
# about two hours on one core). Each line: file | seconds | unittest tail.
# Ends with FINISHED. Split used on 22.10.2026: see the handover.
cd "$(dirname "$0")/.."
out=$1; shift
for t in "$@"; do
  start=$(date +%s)
  res=$(PYTHONPATH=tests python3 -m unittest -q $t 2>&1 | tail -4 | tr '\n' ' ')
  echo "$t | $(( $(date +%s) - start )) s | $res" >> $out
done
echo FINISHED >> $out
