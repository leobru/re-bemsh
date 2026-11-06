#!/bin/sh
# Disassemble an object module (ЗОНМОД format) from a disk volume: every
# procedure prologue (ЗП k(М17) / СЧИ М13, tools/procs.py) is taken as
# code, the rest as disbesm6 decides.
# Usage: tools/moddis.sh VOLUME ZONE NZONES OUT   (ZONE - octal, without 0)
#   writes OUT.obj (the zones) and OUT.dis (the listing).
# Example: tools/moddis.sh 2148 1022 1 upd/klyuch
DIS=${DISBESM6:-$HOME/git/leobru/dispak-tools/disbesm6}
vol=$1 zone=$2 n=$3 out=$4
besmtool dump "$vol" --start=0"$zone" --length="$n" --to-file="$out.obj" >/dev/null || exit 1
[ -s "$out.obj" ] || { echo "$out.obj: empty dump" >&2; exit 1; }
ents=$("$DIS" -r "$out.obj" | sed -n 's/^\([0-7]\{5\}\) 7[0-7]\{7\}00420013\t.*/-e\1/p')
"$DIS" -r $ents "$out.obj" > "$out.dis"
# OUT.code: every word of the module as code (for reading compiled code
# where disbesm6 does not reach)
all=$("$DIS" -r "$out.obj" | sed -n 's/^\([0-7]\{5\}\)[ :][0-7]\{16\}.*/-e\1/p')
"$DIS" -r $ents $all "$out.obj" > "$out.code"
