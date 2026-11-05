#!/usr/bin/env python3
# Print the tables of an object module written by ЗОНМОД (format: see
# tools/findmod.py): header, ВХОД (entry names and addresses), ВНЕШ and
# ЗОНМЕТ, each name also as raw octal (to compare the codes of letters
# like @ with what the assembler writes).
# Usage: tools/modinfo.py VOLUME|FILE ZONE      (ZONE - octal, first zone
#        of the module on VOLUME, or of the module in FILE)
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from findmod import words, chunk, pair, name

src, z = sys.argv[1], int(sys.argv[2], 8)
w = words(src)
h = chunk(w, z, 0)
print('%s  СТАРТ %05o  ДИАП %05o-%05o  ДЛИНА %05o  кусков кода %d' %
      (name(h[1]), h[2], h[3], h[4], h[6], h[5]))
k = 1 + h[5]
for title, i in (('ВХОД', 7), ('ВНЕШ', 8), ('ЗОНМЕТ', 9)):
    c, n = pair(h[i])
    vals = []
    for j in range(c):
        vals += chunk(w, z, k + j)
    k += c
    for j in range(n):
        nm, v = vals[2 * j], vals[2 * j + 1]
        if title == 'ВНЕШ':         # the name is the second word
            nm, v = v, nm
        print('%-6s %-6s %016o  %016o' % (title, name(nm), nm, v))
