#!/bin/sh
# Quick experiment with a compiled macro library: compile the macro files
# with ЗПКОМП430040, then run program lines with ЧТКОМП430040 and ПЕЧМАК.
# Usage: tools/trylib.sh [-t SEC] [-c CARDS] file.mac... -- 'line' 'line'...
#   prints the compiler report lines with errors and the listing of the
#   program (compare with tools/try.sh - the same macros interpreted).
cards=ПЕЧМАК; lim=20
while :; do case "$1" in
    -c) cards="$cards,$2"; shift 2;;
    -t) lim=$2; shift 2;;
    *) break;;
esac; done
t=$(dirname $0); tmp=$(mktemp -d); mac=
while [ "$1" != -- ]; do mac="$mac $1"; shift; done; shift
echo "ПР СТАРТ '1000'" > $tmp/t.be
for l; do echo "$l" >> $tmp/t.be; done
echo " ФИНИШ" >> $tmp/t.be
$t/job.pl -f -c ЗПКОМП430040 $mac > $tmp/z.b6
$t/run.sh $tmp/z.b6 $tmp/2222 | grep 'ИМЕЕТ ОШИБКИ\|НЕ ОПРЕД\|ОТСУТСТВУЕТ\|ЧИСЛО ОШИБОК  *[1-9]'
$t/job.pl -l -c "ЧТКОМП430040,$cards" $tmp/t.be > $tmp/t.b6
cp ${BESM6_PATH:-/usr/local/share/besm6}/2099 $tmp/2099; chmod u+w $tmp/2099
(cd $tmp && timeout $lim dispak --path=.:${BESM6_PATH:-/usr/local/share/besm6} t.b6 > out.txt 2>&1)
[ $? = 0 ] || echo "(не завершилось за $lim с)"
awk '/ПР +СТАРТ/{p=1} p' $tmp/out.txt | grep -v '^ИПМ\|^ОШИБКИ ' |
    awk '{print substr($0,1,12) substr($0,49,92)}'
rm -rf $tmp
