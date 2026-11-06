#!/usr/bin/env python3
# Table of the procedures of an object module disassembled by
# tools/moddis.sh (OUT.code - every word as code, OUT.dis - texts):
# entry, name, arguments (k - 4 of ЗП k(М17); the last one comes in the
# accumulator), frame size, words, the externals and own entries it loads
# into М15 (calls; calls through the method slots of a descriptor
# are not followed), the extracodes and the message texts in its range.
# Usage: tools/modprocs.py upd/klyuch
import re, sys

base = sys.argv[1]
lines = open(base + '.code', encoding='utf-8').read().split('\n')
ins = []                    # (address, label, op, operand)
cur = None
for l in lines:
    m = re.match(r'^([0-7]{5})?[ :]?\s*[0-7]{2} [0-7]{2,3} +[0-7]{4,5} \t(\S*)\t(\S+)\t?(\S*)', l)
    if not m:
        m2 = re.match(r'^\t\t\t\t(\S+)\t(\S*)', l)
        if m2:
            ins.append((cur, '', m2.group(1), m2.group(2)))
        continue
    if m.group(1):
        cur = int(m.group(1), 8)
    ins.append((cur, m.group(2), m.group(3), m.group(4)))
texts = {}
for l in open(base + '.dis', encoding='utf-8'):
    m = re.match(r"^([0-7]{5}) [0-7]{16}\t\S*\tконд\tп'(.*)'$", l)
    if m:
        texts[int(m.group(1), 8)] = m.group(2)
starts = [i for i in range(len(ins) - 1)
          if ins[i][2] == 'зп' and re.fullmatch(r'\d+\(М17\)', ins[i][3])
          and ins[i + 1][2] == 'счи' and ins[i + 1][3] == 'М13']
starts.append(len(ins))
for s, e in zip(starts, starts[1:]):
    body = ins[s:e]
    k = int(body[0][3].split('(')[0])
    frame = next((b[3] for b in body if b[2] == 'слиа' and b[3].endswith('(М17)')), '?')
    calls = sorted({b[3].split('(')[0] for b in body if b[2] == 'уиа' and b[3].endswith('(М15)')
                    and re.match(r'[А-ЯA-Z]', b[3]) and not b[3].startswith(('G', 'D'))})
    calls += sorted({b[3] for b in body if b[2] in ('дк',) and '(М15)' in b[3]})
    ex = sorted({b[2] + (' ' + b[3] if b[3] else '') for b in body if re.fullmatch(r'Э\d+', b[2])})
    lo, hi = body[0][0], body[-1][0]
    t = [texts[a] for a in sorted(texts) if lo <= a <= hi]
    msg = ''.join(x for x in t if re.search(r'[А-Я]{2}', x) and not re.search(r'\d[РА]', x))
    print('%05o %-7s арг %d кадр %-4s слов %4o  %s %s %s' % (
        lo, body[0][1] or '-', k - 4, frame.split('(')[0], hi - lo + 1,
        ' '.join(calls), ' '.join(ex), ('"%s"' % msg.strip()) if msg else ''))
