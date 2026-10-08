#!/usr/bin/env python3
# After reassembly: compare each address-named label (Gааааа/Dааааа) in the
# listing with the address it was assigned; print the first mismatches.
# Usage: tools/labchk.py rvs.be.lst [n]
import re, sys
n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
for l in open(sys.argv[1]):
    m = re.match(r'^.{25}([0-7]{5}) .*? ([GD])([0-7]{5}) ', l)
    if m and m.group(1) != m.group(3):
        print(l.rstrip()); n -= 1
        if not n: break
