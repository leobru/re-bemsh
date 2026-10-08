#!/usr/bin/env python3
# Word-level comparison of two BESM-6 raw dumps (6 bytes per word).
# Usage: tools/wdiff.py a.bin b.bin [base_octal]   (base defaults to 070000)
import signal, sys
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
a, b = (open(f, 'rb').read() for f in sys.argv[1:3])
base = int(sys.argv[3], 8) if len(sys.argv) > 3 else 0o70000
n = max(len(a), len(b)) // 6
for i in range(n):
    wa, wb = a[i*6:i*6+6], b[i*6:i*6+6]
    if wa != wb:
        print('%05o: %016o %016o' % (base + i, int.from_bytes(wa or b'\0'*6, 'big'),
                                     int.from_bytes(wb or b'\0'*6, 'big')))
