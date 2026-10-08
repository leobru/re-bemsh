#!/usr/bin/env python3
# Compact view of a БЕМШ listing: address, code, label, operation, operand,
# comment; page headers dropped. Usage: tools/lst.py file.lst [from to]
import re, sys
lo = int(sys.argv[2], 8) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3], 8) if len(sys.argv) > 3 else 0o77777
cur = None
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    if l.startswith('ИПМ') or l.startswith('ОШИБКИ   НПК'):
        continue
    a = l[25:30]
    if re.fullmatch(r'[0-7]{5}', a):
        cur = int(a, 8)
    if cur is None or not (lo <= cur <= hi):
        continue
    src = l.rstrip('\n')[60:] if re.match(r' *\d{4} [ +]\d{4}[ +]', l[48:60]) else ''
    print('%-6s %-18s %s' % (l[25:30].strip(), l[31:48].rstrip(), src.rstrip()))
