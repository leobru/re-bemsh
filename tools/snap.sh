#!/bin/sh
# Snapshot all user memory (0..077777) when execution reaches an address.
# Usage: tools/snap.sh job.b6 ADDR[:N] out.bin [more debugger commands file]
#   ADDR - octal breakpoint, N - stop at its N-th hit (default 1).
#   The image is written in besmtool dump format (6 bytes per word);
#   registers М1-М17 go to out.bin.regs.
# Runs in a temporary directory with an empty 2222 and a copy of 2099.
job=$(realpath "$1"); bp=${2%%:*}; n=${2#*:}; [ "$n" = "$2" ] && n=1
out=$(realpath -m "$3")
path=${BESM6_PATH:-/usr/local/share/besm6}
tmp=$(mktemp -d)
touch "$tmp/2222"
cp "$path/2099" "$tmp/2099" && chmod u+w "$tmp/2099"
{
    echo "b$bp"
    i=0; while [ $i -lt $n ]; do echo g; i=$((i + 1)); done
    for r in 1 2 3 4 5 6 7 10 11 12 13 14 15 16 17; do echo "i$r-"; done
    a=0; while [ $a -lt 32768 ]; do printf '%o-\n' $a; a=$((a + 8)); done
    echo q
} > "$tmp/cmds"
(cd "$tmp" && dispak --path=.:$path -b "$job" < cmds > dbg.out 2>&1)
python3 - "$tmp/dbg.out" "$out" <<'EOF'
import re, sys
txt = open(sys.argv[1], errors='replace').read()
words = re.findall(r'^(?:- )?([0-7]{4}) ([0-7]{4}) ([0-7]{4}) ([0-7]{4})$', txt, re.M)
regs = re.findall(r'^- ([0-7]{5})$', txt, re.M)
if len(words) < 32768:
    sys.exit('snap: got only %d words (breakpoint not reached?)' % len(words))
words = words[-32768:]
with open(sys.argv[2], 'wb') as f:
    for w in words:
        f.write(int(''.join(w), 8).to_bytes(6, 'big'))
open(sys.argv[2] + '.regs', 'w').write(' '.join(regs[:15]) + '\n')
EOF
rm -rf "$tmp"
