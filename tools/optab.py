#!/usr/bin/env python3
# Print the operation table of the assembler (parts/asm1.bin): for each of
# the 0371 names of ТИМОП (04673) its word of properties from ТСВОП (05264).
# Usage: tools/optab.py [NAME ...]    (default: all; names as printed)
# Columns: index, name, word of properties in octal, class (bits 42-37),
# code (bits 36-25 as written in the word), handler of the first pass.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkbe

BASE, TIM, TSV, N = 0o4000, 0o4673, 0o5264, 0o371
img = open('parts/asm1.bin', 'rb').read()

def word(a):
    return int.from_bytes(img[(a - BASE) * 6:(a - BASE) * 6 + 6], 'big')

for i in range(N):
    t = mkbe.t8const(word(TIM + i), True, True) or '?'
    name = t[t.index("'") + 1:-1] if "'" in t else t
    if sys.argv[1:] and name not in sys.argv[1:]:
        continue
    p = word(TSV + i)
    print('%03o %-6s %016o  класс %02o  код %04o  обр. %05o  ст.разр. %o'
          % (i, name, p, (p >> 36) & 0o77, (p >> 24) & 0o7777, p & 0o77777, p >> 42))
