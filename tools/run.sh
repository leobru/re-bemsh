#!/bin/sh
# Run a job (no trace) with an empty 2222 and a private copy of 2099;
# print the printer output. Usage: tools/run.sh job.b6 [out2222]
#   out2222 - where to keep the resulting 2222 (ЗОНМОД object modules).
#   PUNCH=file - punch output (ПФГП, ПФМОД) to file in binary format.
#   ARCH=file  - use file as 2099 (АРАП archive, tape 42) and save it back
#                after the run (created from the system 2099 if missing).
job=$(realpath "$1")
path=${BESM6_PATH:-/usr/local/share/besm6}
tmp=$(mktemp -d)
touch "$tmp/2222"
if [ -n "$ARCH" ] && [ -f "$ARCH" ]; then cp "$ARCH" "$tmp/2099"; else cp "$path/2099" "$tmp/2099"; fi
chmod u+w "$tmp/2099"
(cd "$tmp" && dispak --path=.:$path ${PUNCH:+-c "$(realpath -m "$PUNCH")" --punch-binary} "$job" 2>&1)
[ -n "$2" ] && cp "$tmp/2222" "$2"
[ -n "$ARCH" ] && cp "$tmp/2099" "$ARCH"
rm -rf "$tmp"
