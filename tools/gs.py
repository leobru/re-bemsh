#!/usr/bin/env python3
# Print a ГС block (macro editor output, macro machine input) element by
# element: header (text words, line, ?, length), text words in the 8-bit
# code, byte code (see tools/gsdis.py).
# Usage: tools/gs.py snap.bin [block_octal]    (default 032000)
import sys
sys.argv += [] if len(sys.argv) > 2 else ['032000']
NAMES = ('КВС AIF SET ВС ВДЧ MEND ПГП ПС КНК ИНДВ ИНДЗ ЗПС ЗПСГ КЛЧ ВЫД КОНЕЦ '
         'EQ GT GE NE LT LE АТРN ACTR СЛ ВЧ УМН ДЕЛ NOT AND OR АТРК АТРР АТРL '
         'АТРС SRCHA SRCHC КНКП КОШ AGO TEQ TGT TGE TNE TLT TLE БЛОК ВС0 ЗПСУ '
         'АТРУ MNOTE АТРМ АТРА').split()
K = 'ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧЪ'
def c(b):
    if 0o100 <= b <= 0o137: return chr(b - 0o40)
    if 0o240 <= b <= 0o337:
        x = b - 0o140
        return K[x - 0o140] if x >= 0o140 else chr(x)
    return '{%o}' % b
d = open(sys.argv[1], 'rb').read()
def w(a): return int.from_bytes(d[a * 6:a * 6 + 6], 'big')
def code(words):
    bs = [b for x in words for b in x.to_bytes(6, 'big')]
    while bs and bs[-1] == 0: bs.pop()
    out = []; i = 0
    while i < len(bs):
        b = bs[i]
        if b >> 6 == 1:
            out.append(NAMES[b & 0o77] if (b & 0o77) < len(NAMES) else '?%o' % b); i += 1
        else:
            v = ((b << 8) | (bs[i + 1] if i + 1 < len(bs) else 0)) ^ 0o100000
            t = {0o10: 'т', 0o11: 'к', 0o12: 'п'}.get(v >> 12, '')
            out.append('%s%o' % (t, v & 0o7777) if t else '=%o' % v); i += 2
    return ' '.join(out)
a = int(sys.argv[2], 8); n = w(a); end = a + n; a += 1
print('блок %06o длина %o' % (a - 1, n))
while a < end:
    h = w(a); ln = h & 0o7777; nt = (h >> 40) & 0o77
    texts = ['"%s"' % ''.join(c(b) for b in w(a + 1 + i).to_bytes(6, 'big')) for i in range(nt)]
    print('%06o стр %04o т%d дл%o [%04o %04o]: %s | %s' % (a, (h >> 24) & 0o7777, nt, ln,
          h >> 36, (h >> 12) & 0o7777, ' '.join(texts), code([w(x) for x in range(a + 1 + nt, a + ln)])))
    a += max(ln, 1)
