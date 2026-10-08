#!/bin/sh
# Run a job under the dispak debugger with a full instruction trace ("t2")
# and print the user-mode trace lines to stdout (feed them to phases.py).
# Usage: tools/trace.sh job.b6 [output.txt] | tools/phases.py - covdir
# Runs in a temporary directory with an empty 2222 and a private copy of
# 2099 (so ЗПКОМП and ЗОНМОД never touch the system disks).
job=$(realpath "$1"); prn=${2:+$(realpath -m "$2")}
path=${BESM6_PATH:-/usr/local/share/besm6}
tmp=$(mktemp -d)
touch "$tmp/2222"
cp "$path/2099" "$tmp/2099" && chmod u+w "$tmp/2099"
(cd "$tmp" && printf 't2\ng\nq\n' |
    dispak --path=.:$path -b "$job" 2>&1 >prn.txt | grep -E '^[0-7]{5}:')
[ -n "$prn" ] && cp "$tmp/prn.txt" "$prn"
rm -rf "$tmp"
