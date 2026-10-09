#!/usr/bin/env python3
# Where the macro editor raises each error code: the entries
# "уиа КОД(М16) / пб ОШИБКА" of parts/mred2.be and every jump to them
# from mred2, mred24 and mred74 (with the routine label before the jump),
# including ПВЛ parameters (second return addresses).
# Usage: tools/errsites.py   (run after make be; codes are octal)
import re
PARTS = ['mred2', 'mred24', 'mred74']

def lines(name):
    """(address, label, op, operand) of parts/NAME.be.lst source lines."""
    res = []; cur = None
    for l in open('parts/%s.be.lst' % name, encoding='utf-8', errors='replace'):
        a = l[25:30]
        if re.fullmatch(r'[0-7]{5}', a):
            cur = a
        m = re.search(r' \d{4}  \d{4} (.*)$', l)
        if not m or cur is None:
            continue
        f = m.group(1).rstrip('\n')
        lab, rest = f[:7].strip(), f[7:].split(None, 1)
        if not rest or rest[0].startswith('*'):
            continue
        res.append((cur, lab, rest[0].upper(), rest[1].split()[0] if len(rest) > 1 else ''))
    return res

m2 = lines('mred2')
code = {}               # entry label/address -> code
for i, (a, lab, op, arg) in enumerate(m2[:-1]):
    m = re.fullmatch(r"’?([0-7]+)’?\(М16\)", arg)
    if op == 'УИА' and m and m2[i + 1][2] == 'ПБ' and m2[i + 1][3] == 'ОШИБКА':
        c = int(m.group(1), 8 if '’' in arg else 10)
        code[lab or a] = c
        code[a] = c
sites = {}
for p in PARTS:
    routine = '?'
    for a, lab, op, arg in lines(p):
        if lab and not re.fullmatch(r'[GD][0-7]{5}', lab):
            routine = lab
        if not op.startswith('П') and op not in ('ЦИКЛ', 'КОНК'):
            continue
        t = re.sub(r'\(М\d+\)$', '', arg).strip('’')
        if re.fullmatch(r'[0-7]{4,5}', t):
            t = '%05o' % int(t, 8)
        m = re.fullmatch(r"В’([0-7]{8})’", arg)
        if op == 'КОНК' and m:       # parameter of a ПВЛ: second return
            t = '%05o' % (int(m.group(1), 8) & 0o77777)
        if t in code and not (p == 'mred2' and arg == 'ОШИБКА'):
            sites.setdefault(code[t], []).append('%s:%s %s %s (%s)' % (p, a, op, arg, routine))
for c in sorted(set(code.values())):
    print('%04o' % c, '; '.join(sites.get(c, ['-'])))
