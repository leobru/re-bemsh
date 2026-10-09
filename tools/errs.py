#!/usr/bin/env python3
# Print the assembler/macro error message table of the pass-2 part:
# code (index from 05065, even), severity and the 12-character text.
# Words are 8-bit БЕМШ text; bits 48 and 40 of the first word hold the
# severity and are forced to 1 before printing (cf. 05025 in parts/list.be):
# severity = 2*bit48 + bit40 + 1.
# Usage: tools/errs.py [parts/list.bin]
import sys
data = open(sys.argv[1] if len(sys.argv) > 1 else 'parts/list.bin', 'rb').read()
BASE, TAB, END = 0o4000, 0o5065, 0o5432
KOI7 = {}
for i, c in enumerate('ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧ'):
    KOI7[0o140 + i] = c
def ch(b):
    if 0o240 <= b <= 0o337:
        b -= 0o140
    elif 0o100 <= b <= 0o137:
        b -= 0o40
    if b >= 0o140:
        return KOI7.get(b, '·')
    return chr(b) if 0o40 <= b < 0o140 else '·'
def word(a):
    i = (a - BASE) * 6
    return int.from_bytes(data[i:i + 6], 'big')
for code in range(0, END - TAB, 2):
    w1, w2 = word(TAB + code), word(TAB + code + 1)
    sev = 2 * (w1 >> 47 & 1) + (w1 >> 39 & 1) + 1
    w1 |= 0o4010000000000000
    txt = ''.join(ch(w >> (40 - 8 * k) & 255) for w in (w1, w2) for k in range(6))
    # Latin letters that look Cyrillic are stored with Latin codes
    txt = txt.translate(str.maketrans('ABEKMHOPCTYX', 'АВЕКМНОРСТУХ'))
    print('%04o %d %s' % (code, sev, txt.rstrip()))
