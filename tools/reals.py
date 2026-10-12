#!/usr/bin/env python3
# List КОНД В'...' words of the parts that hold a normalized БЭСМ-6 real
# number equal to an integer or to 1/integer (candidates for КОНД Е'...').
# Usage: tools/reals.py [part ...]
import re, sys
from fractions import Fraction
sys.path.insert(0, 'tools')


def real(w):
    """Value of a normalized БЭСМ-6 real as a Fraction, None if the word
    is not normalized (or zero)."""
    e = w >> 41
    m = w & ((1 << 41) - 1)
    if m >> 40:
        m -= 1 << 41
    if m == 0 or ((w >> 40) & 1) == ((w >> 39) & 1):
        return None
    return Fraction(m, 1 << 40) * Fraction(2) ** (e - 64)


def nice(v):
    """'123', '-5', '0.1' ... for an integer or 1/integer, else None."""
    if v.denominator == 1 and abs(v) < 10 ** 12:
        return '%d.' % v
    return None


def recip(w):
    """n if the word is 1/n rounded or truncated to 40 bits (|n| < 10**6)."""
    v = real(w)
    if v is None or v.denominator == 1 or abs(v) >= 1:
        return None
    n = round(1 / v)
    if abs(n) < 2 or abs(n) >= 10 ** 6:
        return None
    e = w >> 41
    exact = Fraction(1, n) / Fraction(2) ** (e - 64) * (1 << 40)
    m = v / Fraction(2) ** (e - 64) * (1 << 40)
    return n if abs(exact - m) <= 1 else None


if __name__ == '__main__':
    from mkbe import addrmap, ranges
    for p in sys.argv[1:] or [l.split()[0] for l in open('parts.txt') if l[0] != '#' and l.strip()]:
        plo, phi = ranges()[p]
        img = open('parts/%s.bin' % p, 'rb').read()
        amap = addrmap('parts/%s.be.lst' % p)
        for i, l in enumerate(open('parts/%s.be' % p, encoding='utf-8').read().split('\n'), 1):
            f = l.split('\t')
            a = amap.get(i, '')
            if len(f) < 3 or f[1] != 'конд' or not re.fullmatch(r"в'[0-7]{16}'", f[2]) \
                    or not re.fullmatch(r'[0-7]{5}', a):
                continue
            k = (int(a, 8) - plo) * 6
            w = int.from_bytes(img[k:k + 6], 'big')
            v = real(w)
            if v is None:
                continue
            t = nice(v) or (recip(w) and '1/%d' % recip(w))
            if t:
                print(p, a, '%016o' % w, t)
