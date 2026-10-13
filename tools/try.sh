#!/bin/sh
# Quick experiment: run program lines against macro definition files.
# Usage: tools/try.sh [-o] [-t SEC] [-c CARDS] file.mac... -- 'line' 'line'...
#   builds a job (ПЕЧМАК, full listing; -o adds ОТЛПЕЧ 1-9999, -c - other
#   control cards) from the macro files and the given lines after
#   "ПР СТАРТ '1000'", runs it with a time limit (default 20 s) and prints
#   the listing from the program on (-r - the whole output as is).
cards=ПЕЧМАК; lim=20; raw=
while :; do case "$1" in
    -r) raw=1; shift;;
    -o) cards="$cards,ОТЛПЕЧ      1-9999"; shift;;
    -c) cards="$cards,$2"; shift 2;;
    -t) lim=$2; shift 2;;
    *) break;;
esac; done
tmp=$(mktemp -d)
while [ "$1" != -- ]; do cat "$1" >> $tmp/t.be; shift; done; shift
echo "ПР СТАРТ '1000'" >> $tmp/t.be
for l; do echo "$l" >> $tmp/t.be; done
echo " ФИНИШ" >> $tmp/t.be
$(dirname $0)/job.pl -l -c "$cards" $tmp/t.be > $tmp/t.b6
timeout $lim $(dirname $0)/run.sh $tmp/t.b6 > $tmp/out.txt
[ $? = 0 ] || echo "(не завершилось за $lim с)"
[ -n "$raw" ] && cat $tmp/out.txt
[ -z "$raw" ] && awk '/ПР +СТАРТ/{p=1} p' $tmp/out.txt | grep -v '^ИПМ\|^ОШИБКИ ' |
    awk '{print substr($0,1,12) substr($0,49,92)}'
rm -rf $tmp
