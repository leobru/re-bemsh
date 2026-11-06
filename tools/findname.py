#!/usr/bin/env python3
# Find the words that hold names (as ВХОД/ВНЕШ of ЗОНМОД modules write
# them: 6 characters of 8 bits, tools/findmod.py name()) on disk volumes:
# who defines or calls an entry outside the known modules.
# Usage: tools/findname.py NAME[,NAME...] VOLUME|FILE...
#   prints volume, zone, word in zone (octal), the word and its neighbour
#   (in ВХОД the next word is the address, in ВНЕШ the previous one is the
#   name and the next the module).
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from findmod import words, name

LAT = 'ABEKMHOPCTYX'
CYR = 'ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧ'


def encode(s):
    """Inverse of findmod.name(), as the modules write names: digits and
    signs 040-077 -> +040, Latin letters and @ 0100-0137 -> +0140 (so are
    the Cyrillic letters that look Latin), other Cyrillic -> 0300 + index
    in CYR; padded with spaces (0100)."""
    v = 0
    for c in s.ljust(6)[:6]:
        if c in 'АВЕКМНОРСТУХ':
            c = LAT['АВЕКМНОРСТУХ'.index(c)]
        if c in CYR:
            b = 0o300 + CYR.index(c)
        elif 0o40 <= ord(c) < 0o100:
            b = ord(c) + 0o40
        else:
            b = ord(c) + 0o140
        v = v << 8 | b
    return v


def main():
    names = sys.argv[1].split(',')
    want = {}
    for n in names:
        v = encode(n)
        if name(v) != n:
            sys.exit('cannot encode %s (%016o -> %s)' % (n, v, name(v)))
        want[v] = n
    for src in sys.argv[2:]:
        w = words(src)
        for i, x in enumerate(w):
            if x in want:
                z, k = divmod(i, 1024)
                prv = w[i - 1] if i else 0
                nxt = w[i + 1] if i + 1 < len(w) else 0
                print('%s %04o %04o %-6s  пред %016o (%s)  след %016o (%s)' %
                      (src, z, k, want[x], prv, name(prv), nxt, name(nxt)))


if __name__ == '__main__':
    main()
