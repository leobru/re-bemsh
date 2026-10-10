#!/bin/sh
# Run a job under the dispak debugger with a full instruction trace ("t2")
# and print the user-mode trace lines to stdout (feed them to phases.py).
# Usage: tools/trace.sh job.b6 [output.txt] | tools/phases.py - covdir
# Runs in a temporary directory with an empty 2222 and a private copy of
# 2099 (so ЗПКОМП and ЗОНМОД never touch the system disks).
# IN2222=file - start from this 2222 instead of an empty one (object
# modules for a РВС job).
job=$(realpath "$1"); prn=${2:+$(realpath -m "$2")}
path=${BESM6_PATH:-/usr/local/share/besm6}
tmp=$(mktemp -d)
if [ -n "$IN2222" ]; then cp "$IN2222" "$tmp/2222"; else touch "$tmp/2222"; fi
cp "$path/2099" "$tmp/2099" && chmod u+w "$tmp/2099"
(cd "$tmp" && printf 't2\ng\nq\n' |
    dispak --path=.:$path -b "$job" 2>&1 >prn.txt | grep -E '^[0-7]{5}:')
[ -n "$prn" ] && cp "$tmp/prn.txt" "$prn"
rm -rf "$tmp"
