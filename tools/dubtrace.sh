#!/bin/sh
# Run a job of the Dubna monitor system (*bemsh deck) under the Dubna
# simulator (~/git/dubna; tape 739 = 2048 from zone 0144 is built in) with
# a dispak-format instruction trace on stdout (feed it to phases.py with
# ZOFS=144). BEMSH under Dubna runs in its mode 1122: zgr converts the
# module to a Dubna standard array.
# Usage: tools/dubtrace.sh job.dub [printer.txt] | ZOFS=144 tools/phases.py - covdir
# Runs in a temporary directory (the simulator leaves scratch files there).
# DUBNA=path - the simulator (default: dubna in PATH).
job=$(realpath "$1"); prn=${2:+$(realpath -m "$2")}
tmp=$(mktemp -d)
(cd "$tmp" && ${DUBNA:-dubna} -r -d d "$job" 2>&1 >prn.txt | grep -E '^[0-7]{5}[:;] ')
[ -n "$prn" ] && cp "$tmp/prn.txt" "$prn"
rm -rf "$tmp"
