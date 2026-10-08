#!/bin/sh
# Run a job (no trace) with an empty 2222 and a private copy of 2099;
# print the printer output. Usage: tools/run.sh job.b6
job=$(realpath "$1")
path=${BESM6_PATH:-/usr/local/share/besm6}
tmp=$(mktemp -d)
touch "$tmp/2222"
cp "$path/2099" "$tmp/2099" && chmod u+w "$tmp/2099"
(cd "$tmp" && dispak --path=.:$path "$job" 2>&1)
rm -rf "$tmp"
