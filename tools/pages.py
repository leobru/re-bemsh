#!/usr/bin/env python3
# Per-page summary of memory snapshots: non-zero words, and words changed
# between two snapshots. Usage: tools/pages.py a.bin [b.bin]
import sys
a = open(sys.argv[1], 'rb').read()
b = open(sys.argv[2], 'rb').read() if len(sys.argv) > 2 else None
for p in range(32):
    rng = range(p * 1024, (p + 1) * 1024)
    nz = sum(1 for i in rng if a[i*6:i*6+6] != b'\0' * 6)
    s = '%02o %06o: %4d' % (p, p * 1024, nz)
    if b:
        nzb = sum(1 for i in rng if b[i*6:i*6+6] != b'\0' * 6)
        ch = sum(1 for i in rng if a[i*6:i*6+6] != b[i*6:i*6+6])
        s += ' -> %4d, изменено %4d' % (nzb, ch)
    print(s)
