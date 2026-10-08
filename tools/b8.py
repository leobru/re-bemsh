#!/usr/bin/env python3
# Show BESM-6 words as 8-bit БЕМШ text (6 bytes per word), the encoding of
# names in object modules and macro tables (cf. Module::debemsh in disbesm6).
# Usage: tools/b8.py file.bin base_octal [from_octal to_octal]
import sys
KOI7 = {}
for i, c in enumerate('юабцдефгхийклмнопярстужвьызшэщчъ'):
    KOI7[0o100 + i] = c
for i, c in enumerate('ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧ'):
    KOI7[0o140 + i] = c
def ch(b):
    if 0o240 <= b <= 0o337:
        b -= 0o140
    elif 0o100 <= b <= 0o137:
        b -= 0o40
    if b in KOI7 and b >= 0o140:
        return KOI7[b]
    if 0o40 <= b < 0o140:
        return chr(b)
    return '·'
data = open(sys.argv[1], 'rb').read()
base = int(sys.argv[2], 8)
lo = int(sys.argv[3], 8) if len(sys.argv) > 3 else base
hi = int(sys.argv[4], 8) if len(sys.argv) > 4 else base + len(data) // 6 - 1
for a in range(lo, hi + 1):
    w = data[(a - base) * 6:(a - base) * 6 + 6]
    print('%05o %016o %s' % (a, int.from_bytes(w, 'big'), ''.join(ch(b) for b in w)))
