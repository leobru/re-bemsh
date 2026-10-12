#!/usr/bin/env python3
# List unlabelled КОНД words that directly follow an executable instruction
# (candidates for code that disbesm6 left as data), with both halves decoded.
# Usage: tools/kondafter.py [part ...]      (default: all parts of parts.txt)
import re, sys
sys.path.insert(0, 'tools')
from mkbe import addrmap, ranges, NOTCMD

SHORT = {0: 'зп', 1: 'зпм', 2: 'рег', 3: 'счм', 4: 'сл', 5: 'вч', 6: 'вчоб', 7: 'вчаб',
         0o10: 'сч', 0o11: 'и', 0o12: 'нтж', 0o13: 'слц', 0o14: 'знак', 0o15: 'или',
         0o16: 'дел', 0o17: 'умн', 0o20: 'сбр', 0o21: 'рзб', 0o22: 'чед', 0o23: 'нед',
         0o24: 'слп', 0o25: 'вчп', 0o26: 'сд', 0o27: 'рж', 0o30: 'счрж', 0o31: 'счмр',
         0o32: 'э32', 0o33: 'увв', 0o34: 'слпа', 0o35: 'вчпа', 0o36: 'сда', 0o37: 'ржа',
         0o40: 'уи', 0o41: 'уим', 0o42: 'счи', 0o43: 'счим', 0o44: 'уии', 0o45: 'сли',
         0o46: 'э46', 0o47: 'э47'}
LONG = {0o20: 'э20', 0o21: 'э21', 0o22: 'мода', 0o23: 'мод', 0o24: 'уиа', 0o25: 'слиа',
        0o26: 'по', 0o27: 'пе', 0o30: 'пб', 0o31: 'пв', 0o32: 'выпр', 0o33: 'стоп',
        0o34: 'пио', 0o35: 'пино', 0o36: 'э36', 0o37: 'цикл'}


def half(h):
    r = h >> 20
    if h & 0o2000000:
        op, a = LONG[(h >> 15) & 0o37], h & 0o77777
    else:
        c = (h >> 12) & 0o77
        op = SHORT.get(c, 'э%o' % c)
        a = h & 0o7777 | (0o70000 if h & 0o1000000 else 0)
    return '%-5s %05o%s' % (op, a, '(М%o)' % r if r else '')


def main(parts):
    for p in parts:
        plo, phi = ranges()[p]
        img = open('parts/%s.bin' % p, 'rb').read()
        amap = addrmap('parts/%s.be.lst' % p)
        L = open('parts/%s.be' % p, encoding='utf-8').read().split('\n')
        prev = None
        for i, l in enumerate(L, 1):
            f = l.split('\t')
            if l.startswith('*') or len(f) < 2:
                continue
            a = amap.get(i, '')
            if not f[0] and f[1] == 'конд' and prev and prev not in NOTCMD and \
                    re.fullmatch(r'[0-7]{5}', a):
                # the whole run of unlabelled КОНД
                j = i
                while j <= len(L):
                    g = L[j - 1].split('\t')
                    if len(g) < 2 or g[0] or g[1] != 'конд':
                        break
                    b = amap.get(j, '')
                    if re.fullmatch(r'[0-7]{5}', b):
                        k = (int(b, 8) - plo) * 6
                        w = int.from_bytes(img[k:k + 6], 'big')
                        print('%-6s %s  %016o  %-22s %-22s %s' % (
                            p if j == i else '', b, w, half(w >> 24),
                            half(w & 0o77777777), g[2] if len(g) > 2 else ''))
                    j += 1
            prev = f[1]


if __name__ == '__main__':
    main(sys.argv[1:] or [l.split()[0] for l in open('parts.txt') if l[0] != '#' and l.strip()])
