#!/usr/bin/env python3
# Drop the empty "мода" fillers of a disbesm6 -s listing that BEMSH puts back
# by itself (before ПВ and extracodes, which BEMSH always places in a right
# half, and before labels). A filler that only pads to a word boundary in the
# original is kept as one explicit "мода" so that the code reassembles to the
# same addresses. A labelled filler before ПВ or an extracode gives its label
# to that instruction (the label starts the word, BEMSH pads the left half).
# Usage: tools/stripmoda.py in.be out.be
import sys
L = open(sys.argv[1]).read().split('\n')
out = []; kept = 0; i = 0
while i < len(L):
    f = L[i].rstrip('\t').split('\t')
    if len(f) == 2 and f[0] and f[1] == 'мода':
        g = L[i + 1].split('\t')
        if g[0] == '' and len(g) > 1 and (g[1] == 'пв' or g[1].startswith('Э')):
            L[i + 1] = f[0] + L[i + 1]
            i += 1
            continue
    if L[i].rstrip('\t') == '\tмода':
        j = i
        while L[j].rstrip('\t') == '\tмода':
            j += 1
        f = L[j].split('\t')
        op = f[1] if len(f) > 1 else ''
        right_only = op == 'пв' or op.startswith('Э')
        if f[0] == '' and j > i + 1:
            # a run of fillers may hold a whole filler word: keep it as is
            out.extend(['\tмода\t,ЗАПОЛНИТЕЛЬ, КАК В ОРИГИНАЛЕ'] * (j - i))
            kept += j - i
        elif f[0] == '' and not right_only:
            out.append('\tмода\t,ДО ГРАНИЦЫ СЛОВА, КАК В ОРИГИНАЛЕ')
            kept += 1
        i = j
        continue
    out.append(L[i]); i += 1
open(sys.argv[2], 'w').write('\n'.join(out))
print(kept, 'fillers kept', file=sys.stderr)
