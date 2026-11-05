#!/usr/bin/env python3
# Align a fragment of original source text (decoded by tools/t8text.py)
# with the disassembled code of a part by operation sequence (difflib) and
# print the differences side by side: the parts that are the same are
# shown as one line "= N команд" with the address range, inserted /
# deleted / replaced instructions are listed in full.
# Usage: tools/srcdiff.py SOURCE.utf8 PART [FROM_LABEL [TO_LABEL]]
#        (FROM/TO_LABEL limit the source lines; by default all of them)
import difflib, sys
sys.path.insert(0, 'tools')
from srcmatch import source, part, OPS, plain

src = source(sys.argv[1])
plain([sys.argv[2]])            # without notes/src and notes/mac
code = part(sys.argv[2])
plain([sys.argv[2]], False)
if len(sys.argv) > 3:
    i = [s[0] for s in src].index(sys.argv[3])
    j = [s[0] for s in src].index(sys.argv[4]) if len(sys.argv) > 4 else len(src)
    src = src[i:j]
src = [s for s in src if s[1] in OPS]


def key(op):
    return 'пв' if op == 'пвл' else op


sm = difflib.SequenceMatcher(None, [key(s[1]) for s in src],
                             [key(c[1]) for c in code], autojunk=False)
fmt = '%-8s %-6s %-22s | %-7s %-6s %s'
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        print('= %d команд  %s–%s  (%s … %s)' % (
            i2 - i1, code[j1][0], code[j2 - 1][0], src[i1][0] or src[i1][1],
            src[i2 - 1][0] or src[i2 - 1][1]))
        continue
    if tag == 'delete' and i1 == 0 or tag == 'insert' and j1 == 0:
        continue
    n = max(i2 - i1, j2 - j1)
    if j2 - j1 > 60 or tag == 'insert' and i1 == len(src):
        print('%s %d строк исходника, %d команд образа %s–%s' % (
            tag, i2 - i1, j2 - j1, code[j1][0], code[j2 - 1][0]))
        continue
    print('~' if tag == 'replace' else '-' if tag == 'delete' else '+')
    for k in range(n):
        s = src[i1 + k] if i1 + k < i2 else ('', '', '', '', [])
        c = code[j1 + k] if j1 + k < j2 else ('', '', '', '')
        print(fmt % (s[0], s[1], s[2], c[0], c[1], c[2]))
