#!/bin/sh
# Compare РВС 10/75 (2048:0144, part rvs75) with РВС 01/78 (2248:0105-0106)
# on the same volume 2222: modules ПР (jobs/zgr.be, zone 0), ДРУГОЙ
# (jobs/rvscmp/drugoj.be, zone 4), ПР2 with a common area
# (jobs/rvscmp/pr2.be, zone 010).
# Usage: tools/rvscmp.sh [jobs/rvscmp/*.deck ...]   (cards of a РВС run,
# one per line with ^; "конец" is added)
path=${BESM6_PATH:-/usr/local/share/besm6}
tmp=$(mktemp -d)
for m in zgr:jobs/zgr.be drugoj:jobs/rvscmp/drugoj.be pr2:jobs/rvscmp/pr2.be; do
    n=${m%%:*}; f=${m#*:}
    tools/job.pl -z "$f" > "$tmp/$n.b6"
    tools/run.sh "$tmp/$n.b6" "$tmp/$n.2222" > /dev/null
    mkdir "$tmp/$n" && cp "$tmp/$n.2222" "$tmp/$n/2222"
    (cd "$tmp/$n" && BESM6_PATH=. besmtool dump 2222 --start=0 --length=4 --to-file=m > /dev/null 2>&1)
done
mkdir "$tmp/vol" && cp "$tmp/zgr.2222" "$tmp/vol/2222"
(cd "$tmp/vol" && BESM6_PATH=. besmtool write 2222 --start=4 --from-file=../drugoj/m > /dev/null 2>&1 &&
    BESM6_PATH=. besmtool write 2222 --start=010 --from-file=../pr2/m > /dev/null 2>&1)
[ $# -gt 0 ] || set -- jobs/rvscmp/*.deck
for deck in "$@"; do
    for v in 75 78; do
        echo "######## $(basename "$deck" .deck) / РВС $v"
        rm -rf "$tmp/r" && mkdir "$tmp/r" && cp "$tmp/vol/2222" "$tmp/r/2222"
        if [ $v = 75 ]; then
            printf 'шифр 419999^\nлен 30(2048)^\nлен 43(2222-зп)^\nросп 0^\nвход 1000^\nе\nв 1000\nк 00 070 1002\nк 00 30 40000\nс 0010 2000 0030 0144\nв 2000\nа1\n'
        else
            printf 'шифр 419999^\nлен 67(2248)42(2113)^\nлен 43(2222-зп)^\nросп 0^\nвход 1000^\nе\nв 1000\nк 00 070 1003\nк 00 070 1004\nк 00 30 70000\nс 0010 3400 0067 0105\nс 0010 3500 0067 0106\nв 2000\nа1\n'
        fi > "$tmp/r/j.b6"
        { cat "$deck"; printf 'конец ^\n_$\nеконец\n'; } >> "$tmp/r/j.b6"
        (cd "$tmp/r" && dispak --path=.:$path j.b6 2>&1 | grep -v '^ *$')
    done
done
rm -rf "$tmp"
