#!/usr/bin/env python3
# Split a dispak instruction trace (debugger "t2") of a БЕМШ run by overlay.
# Tracks which zone of tape 30 (2048 from zone 06200, i.e. 2048 zones
# 0147-0177 after the 12-bit wrap) is loaded into each page by Э70, and
# attributes every executed user-mode address to the zone in its page.
#
# Usage: tools/phases.py trace.log|- [covdir]
#   prints the load events (where, page <- zone) in order;
#   with covdir, writes covdir/ZZZZ.cov ("ааааа: L R" lines, disbesm6 --trace
#   format) for every zone that had code executed in it.
import re, sys, os
from collections import defaultdict

page = {}                       # page -> zone of tape 30 (or None)
cov = defaultdict(lambda: defaultdict(set))
events = []
seen = defaultdict(int)         # addr -> count of lines at this addr in a row
prev = None
src = sys.stdin if sys.argv[1] == '-' else open(sys.argv[1], errors='replace')
for l in src:
    m = re.match(r'^([0-7]{5})([:;]) (\S+)', l)
    if not m:
        continue
    addr = int(m.group(1), 8)
    user = m.group(2) == ':'
    if not user:
        prev = None
        continue
    pg = addr >> 10
    z = page.get(pg)
    half = 'R' if prev == addr else 'L'
    prev = addr
    if z is not None:
        cov[z][addr].add(half)
    if m.group(3) == '*70':
        w = re.search(r'\(=([0-7]{16})\)', l)
        if w:
            w = int(w.group(1), 8)
            unit = (w >> 12) & 0o77
            zone = w & 0o7777
            p = (w >> 30) & 0o37
            rd = (w >> 39) & 1
            if unit == 0o30 and rd:
                page[p] = zone
                events.append('%05o: лист %02o (%05o) <- зона 30:%04o (2048:%04o)'
                              % (addr, p, p << 10, zone, (zone + 0o6200) & 0o7777))
            elif rd:
                page[p] = None
                events.append('%05o: лист %02o <- устр %02o зона %04o' % (addr, p, unit, zone))
            else:
                events.append('%05o: лист %02o -> устр %02o зона %04o' % (addr, p, unit, zone))
print('\n'.join(events))
if len(sys.argv) > 2:
    os.makedirs(sys.argv[2], exist_ok=True)
    for z, a in cov.items():
        with open(os.path.join(sys.argv[2], '%04o.cov' % ((z + 0o6200) & 0o7777)), 'w') as f:
            for x in sorted(a):
                f.write('%05o: %s\n' % (x, ''.join(sorted(a[x]))))
        print('2048:%04o: %d адресов' % ((z + 0o6200) & 0o7777, len(a)), file=sys.stderr)
