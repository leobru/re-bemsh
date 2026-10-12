#!/usr/bin/env python3
# Propose names for tables: labels Gааааа/Dааааа used with an index
# register in commands where the register is an index (not УИА, ПВ, ЦИКЛ...).
# The name tells the kind of the contents and the address:
#   МС - masks, ТП - jump table, ТТ - text (БЕМШ code), ТЧ - small numbers,
#   ТА - address constants / pointers into the part, МВ - array in ПАМ or
#   zeros, ТБ - other table; then the 4 low octal digits of the address.
# Usage: tools/tabnames.py [-w] [part ...]
#   -w  append the names to notes/NAME.py (NAMES.update); without it - print.
# Reads parts/NAME.be and parts/NAME.bin; run tools/mkbe.py afterwards.
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))

REGDEST = {'уиа', 'слиа', 'пв', 'пвл', 'пво', 'цикл', 'уии', 'сли', 'пио',
           'пино', 'дк', 'дкб', 'кк', 'ккб'}
args = sys.argv[1:]
write = args[:1] == ['-w']
if write:
    args = args[1:]
parts = {}
for l in open('parts.txt', encoding='utf-8'):
    f = l.split()
    if f and not l.startswith('#'):
        parts[f[0]] = int(f[2], 8)


def is_mask(w):
    """ones in one run (or all but one run)"""
    def run(x):
        if x == 0:
            return False
        x >>= (x & -x).bit_length() - 1
        return x & (x + 1) == 0
    return run(w) or run(w ^ (1 << 48) - 1)


def text(w):
    bs = [(w >> (40 - 8 * k)) & 0xff for k in range(6)]
    return sum(1 for b in bs if 0o100 <= b <= 0o137 or 0o240 <= b <= 0o337) >= 4


def kind(words, base, hi, pam):
    if pam or all(w == 0 for w in words):
        return 'МВ'
    n = len(words)
    if sum(1 for w in words if (w >> 39 & 0o37) == 0o30 or (w >> 15 & 0o37) == 0o30) * 2 > n:
        return 'ТП'
    if sum(1 for w in words if text(w)) * 2 > n:
        return 'ТТ'
    if sum(1 for w in words if w >> 15 == 0 and base <= w < hi) * 2 > n:
        return 'ТА'
    if sum(1 for w in words if w < 1 << 15) * 2 > n:
        return 'ТЧ'
    if sum(1 for w in words if is_mask(w)) * 3 >= n * 2:
        return 'МС'
    return 'ТБ'


used = set()
for p in parts:                     # names already taken, in all parts
    g = {}
    if os.path.exists('notes/%s.py' % p):
        exec(open('notes/%s.py' % p, encoding='utf-8').read(), g)
    used |= set(g.get('NAMES', {}).values())

for p in args or parts:
    base = parts[p]
    data = open('parts/%s.bin' % p, 'rb').read()
    hi = base + len(data) // 6
    src = open('parts/%s.be' % p, encoding='utf-8').read().split('\n')
    labels = sorted(int(m.group(1), 8) for l in src
                    for m in [re.match(r'[GD]([0-7]{5})\t', l)] if m)
    pam = {int(m.group(1), 8) for l in src
           for m in [re.match(r'[GD]([0-7]{5})\tпам\t', l)] if m}
    tabs = set()
    for l in src:
        f = l.split('\t')
        m = re.fullmatch(r'[GD]([0-7]{5})\((М\d+)\)', f[2]) if len(f) >= 3 else None
        if m and f[1] not in REGDEST and f[1] not in ('пб', 'по', 'пе', 'употр', 'отмен'):
            tabs.add(int(m.group(1), 8))
    names = {}
    for a in sorted(tabs):
        if not base <= a < hi:
            continue
        nxt = min([x for x in labels if x > a] + [hi, a + 8])
        words = [int.from_bytes(data[(x - base) * 6:(x - base) * 6 + 6], 'big')
                 for x in range(a, max(nxt, a + 1))]
        n = '%s%04o' % (kind(words, base, hi, a in pam), a & 0o7777)
        if n in used:
            continue                # keep the D label
        used.add(n)
        names['%05o' % a] = n
    if not names:
        continue
    body = ''.join(" '%s': '%s',\n" % x for x in sorted(names.items()))
    if write:
        with open('notes/%s.py' % p, 'a', encoding='utf-8') as f:
            f.write("\n# таблицы и массивы (tools/tabnames.py): вид содержимого и адрес\n"
                    "NAMES = dict(globals().get('NAMES', {}))\nNAMES.update({\n%s})\n" % body)
    print('%s: %d' % (p, len(names)))
    if not write:
        sys.stdout.write(body)
