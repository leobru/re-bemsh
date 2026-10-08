#!/usr/bin/env python3
# Disassemble a ГС byte-code sequence (macro machine code) from a snapshot.
# A byte 01xxxxxx is a command (number xxxxxx, names from the table at
# mmash 02074); any other byte starts a 2-byte operand (b1<<8 | b2) ^ 0100000
# pushed on the stack (as fetched by mmash 02411-02426).
# Usage: tools/gsdis.py snap.bin from_octal to_octal
import sys
NAMES = ('КВС AIF SET ВС ВДЧ MEND ПГП ПС КНК ИНДВ ИНДЗ ЗПС ЗПСГ КЛЧ ВЫД КОНЕЦ '
         'EQ GT GE NE LT LE АТРN ACTR СЛ ВЧ УМН ДЕЛ NOT AND OR АТРК АТРР АТРL '
         'АТРС SRCHA SRCHC КНКП КОШ AGO TEQ TGT TGE TNE TLT TLE БЛОК ВС0 ЗПСУ '
         'АТРУ MNOTE АТРМ АТРА').split()
d = open(sys.argv[1], 'rb').read()
lo, hi = int(sys.argv[2], 8), int(sys.argv[3], 8)
bs = []
for a in range(lo, hi + 1):
    for i, b in enumerate(d[a * 6:a * 6 + 6]):
        bs.append((a, i, b))
out = []; i = 0
while i < len(bs):
    a, k, b = bs[i]
    if b >> 6 == 1:
        out.append('%05o.%d %s' % (a, k, NAMES[b & 0o77] if (b & 0o77) < len(NAMES) else '?%o' % b))
        i += 1
    else:
        v = ((b << 8) | (bs[i + 1][2] if i + 1 < len(bs) else 0)) ^ 0o100000
        out.append('%05o.%d =%06o' % (a, k, v))
        i += 2
print('\n'.join(out))
