#!/usr/bin/env python3
# Show a dispak punch file written with -c FILE --punch-binary (5 bytes per
# memory word - its low 40 bits, 24 words per card).
# Default: each byte is a GOST character with bit 8 making the parity odd;
# a zero byte ends a line. БЕМШ punches Диспак loader cards this way:
# "В" + address, "К" + word as two halfwords rr ooo aaaa (as in job decks).
# Usage: tools/cards.py FILE [-r]   (-r: card rows as pictures instead)
import sys
data = open(sys.argv[1], 'rb').read()
if '-r' in sys.argv:
    for c in range(len(data) // 120):
        print('карта %d' % (c + 1))
        for r in range(12):
            row = int.from_bytes(data[c * 120 + r * 10:c * 120 + r * 10 + 10], 'big')
            print('  %2d %s' % (r, format(row, '080b').replace('0', '.').replace('1', 'O')))
    sys.exit()
GOST = {i: str(i) for i in range(10)}
GOST.update({0o12: '+', 0o13: '-', 0o14: '/', 0o15: ',', 0o16: '.', 0o17: ' '})
for i, c in enumerate('АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЫЬЭЮЯ'):
    GOST[0o40 + i] = c
line, bad = '', 0
for b in data:
    if b == 0:
        if line:
            print(line)
        line = ''
        continue
    if bin(b).count('1') % 2 == 0:
        bad += 1
    line += GOST.get(b & 0o177, '<%03o>' % (b & 0o177))
if line:
    print(line)
if bad:
    print('байтов с чётным числом пробивок: %d' % bad, file=sys.stderr)
