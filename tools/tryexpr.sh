#!/bin/sh
# Try expressions of the macro language one by one: each line of stdin is
# put as "&Ч SЕТА line" (or "&С SЕТС line" with -c) into its own macro
# and its own job; prints the line, the macro editor's message for it and
# the generated value ("-" if nothing was generated).
# Usage: tools/tryexpr.sh [-c] [ARG] < expressions     (ARG - the macro argument &А, default Z)
op=SЕТА; decl=LСLА
[ "$1" = -c ] && { op=SЕТС; decl=LСLС; shift; }
arg=${1:-Z}
tmp=$(mktemp -d)
while IFS= read -r e; do
    printf ' МАСRО\n ОП &А\n %s &Ч\n&Ч %s %s\n ТЕКСТ П'"'"'=&Ч'"'"'\n МЕND\n' "$decl" "$op" "$e" > $tmp/m.mac
    "$(dirname "$0")/try.sh" -r $tmp/m.mac -- " ОП $arg" > $tmp/out 2>&1
    msg=$(grep -a "&Ч\|∧Ч" $tmp/out | grep -a "$op" | head -1 | awk '{print substr($0,1,13)}' | sed 's/ *$//')
    grep -aq 'КОНТРОЛЬ КОМАНДЫ\|^ *[0-7]\{5\}: [0-7 ]*	' $tmp/out && msg="$msg [АВОСТ]"
    val=$(grep -a '+[0-9]\{4\}+ .*ТЕКСТ П’=' $tmp/out | head -1 | sed 's/.*ТЕКСТ П’=//; s/’.*//')
    grep -aq 'МАКРО С ОШИБ' $tmp/out && val='МАКРО С ОШИБ'
    printf '%-16s| %-14s| %s\n' "$e" "$msg" "${val--}"
done
rm -rf $tmp
