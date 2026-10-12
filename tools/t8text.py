#!/usr/bin/env python3
# Print a file of text in the 8-bit БЕМШ code (as kept in the АРАП text
# archive): 0276 ends a line, unknown bytes are shown as <ooo>.
# Usage: tools/t8text.py FILE [> text]
import sys
sys.path.insert(0, 'tools')
from mkbe import T8

d = open(sys.argv[1], 'rb').read()
out = []
for b in d:
    if b == 0o276:
        out.append('\n')
    elif b in T8:
        out.append(T8[b].replace("''", "'"))
    elif b == 0:
        out.append('\0')
    else:
        out.append('<%o>' % b)
sys.stdout.write(''.join(out).replace('\0', ''))
