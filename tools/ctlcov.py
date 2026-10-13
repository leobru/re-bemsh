#!/usr/bin/env python3
# Control cards of the monitor (parts/mon74.bin: pairs "name, handler
# address" from 076722 to 077140 - АРАП directives, then translation
# modes) and whether the handler of each was ever executed by the jobs
# (traces/*.cov, see tools/cover.py). Handlers shared by several cards are
# counted too, and the last column tells in how many jobs (jobs/*.b6,
# jobs/*/*.b6) the card itself occurs at the beginning of a line.
# Usage: tools/ctlcov.py
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkbe

BASE, LO, HI = 0o74000, 0o76722, 0o77142
img = open('parts/mon74.bin', 'rb').read()
word = lambda a: int.from_bytes(img[(a - BASE) * 6:(a - BASE) * 6 + 6], 'big')
cov = set()
for z in ('0150', '0151', '0152'):
    for c in glob.glob('traces/*.cov/%s.cov' % z) + glob.glob('traces/*/*.cov/%s.cov' % z):
        cov.update(int(x.split(':')[0], 8) for x in open(c))
rows = []
a = LO
while a < HI:
    t = mkbe.t8const(word(a), True, True)
    h = word(a + 1)
    if t and "'" in t and 0o70000 <= h <= 0o77777:
        rows.append((t[t.index("'") + 1:-1].strip(), h, a)); a += 2
    else:
        a += 1
jobs = [open(f, errors='replace').read().split('\n')
        for f in glob.glob('jobs/*.b6') + glob.glob('jobs/*/*.b6')]
def used(n):
    return sum(any(l.startswith(n) for l in j) for j in jobs)
share = {}
for n, h, a in rows:
    share[h] = share.get(h, 0) + 1
for n, h, a in rows:
    print('%05o %-7s обр. %05o %-14s в заданиях: %d' % (a, n, h, 'исполнялся' if h in cov else 'НЕ ИСПОЛНЯЛСЯ', used(n)))
