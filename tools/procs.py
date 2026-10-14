#!/usr/bin/env python3
# Table of the procedures of a part written in a compiled language
# (mred24), found by their prologues, and a check of the operands.
# Usage: tools/procs.py [-c] [-w] PART        (after "make check")
#   A procedure starts with  ЗП k(М17) / СЧИ М13 / ЗП 1(М17) / УИИ М13(М17) /
#   СЛИА n(М17) / СЧИМ Мr ... / ЗП (М17), then loads its base (УИА *(М14) or
#   УИИ М14(М15)) and jumps to the body; the epilogue follows that jump.
#   Columns: entry, number of arguments (k - 4; the last one comes in the
#   accumulator), frame size n, saved registers, body, epilogue, last word,
#   words of code, words never executed (traces/, as tools/cover.py), calls.
#   -c  check: a jump to a label of the part must land on an instruction,
#       a read or write - on data; prints the exceptions. (It does not see
#       a base that is wrong by a word when both words are data.)
#   -d FROM TO  the data words of this address range: address=value.
#   -w  print the words of the part, one per line ("-" - never executed).
import glob, os, re, sys

args = [a for a in sys.argv[1:] if not a.startswith('-')]
name = args[0]
JUMPS = ('ПБ', 'ПЕ', 'ПО', 'ПВ', 'ПИО', 'ПИНО', 'ЦИКЛ')
NOTDATA = JUMPS + ('УИА', 'СЛИА', 'МОДА', 'КОНК', 'КК', 'ДК', 'ДКБ', 'КОНД',
                   'ТЕКСТ', 'ПАМ', 'УПОТР', 'ОТМЕН', 'ВХОД', 'ВНЕШ', 'ЭКВ')

zones = []
for l in open('parts.txt'):
    f = l.split()
    if f and f[0] == name:
        zones = f[3:]
hit = set()
for z in zones:
    for c in glob.glob('traces/*.cov/%s.cov' % z) + glob.glob('traces/*/*.cov/%s.cov' % z):
        hit.update(int(x.split(':')[0], 8) for x in open(c))

labels = {}         # label -> address
vals = {}           # address -> value of a data word
for l in open('parts/%s.be.lst' % name, errors='replace'):
    m = re.match(r'^.{0,24} ([0-7]{5}) .{0,24}\d{4}  \d{4} (\S{1,6}) ', l)
    if m:
        labels[m.group(2)] = int(m.group(1), 8)
    m = re.match(r'^.{0,24} ([0-7]{5})  ([0-7]{16}) ', l)
    if m:
        vals[int(m.group(1), 8)] = m.group(2)

if '-d' in sys.argv:
    lo, hi = int(args[1], 8), int(args[2], 8)
    print(' '.join('%05o=%s' % (a, v) for a, v in sorted(vals.items()) if lo <= a <= hi))
    sys.exit()

words = {}          # address -> list of (label, op, operand)
code = set()        # addresses of instruction words
order = []
cur = None
for l in open('parts/%s.be.lst' % name, errors='replace'):
    m = re.match(r'^.{0,36}?(?:([0-7]{5}) )?([0-7]{2} [0-7]{2,3} +[0-7]{4,5}|[0-7]{16})'
                 r'(?: +[0-7]{5})? +\d{4}  \d{4} (.{0,6}) ?(\S*) *(\S*)', l)
    if not m:
        continue
    if m.group(1):
        cur = int(m.group(1), 8)
        words[cur] = []
        order.append(cur)
    if cur is None:
        continue
    words[cur].append((m.group(3).strip(), m.group(4), m.group(5)))
    if ' ' in m.group(2) and m.group(4) not in ('КОНК', 'КОНД', 'КК', 'ДК', 'ДКБ'):
        code.add(cur)

def text(a):
    return ' | '.join(' '.join(x for x in w if x) for w in words[a])

if '-w' in sys.argv:
    for a in order:
        print('%s%05o %s' % ('-' if a in code and a not in hit else ' ', a, text(a)))
    sys.exit()

if '-c' in sys.argv:
    for a in order:
        for lab, op, opd in words[a]:
            m = re.fullmatch(r'[GD]?([0-7]{5})', opd)
            if a not in code or not (m or opd in labels):
                continue
            t = labels[opd] if opd in labels else int(m.group(1), 8)
            if t not in words:
                continue
            if op in JUMPS and t not in code:
                print('%05o %s %s: переход на данные' % (a, op, opd))
            elif op not in NOTDATA and t in code:
                print('%05o %s %s: операнд в коде' % (a, op, opd))
    sys.exit()

flat = [(a, w) for a in order for w in words[a]]
procs = []
for i, (a, (lab, op, opd)) in enumerate(flat):
    m = re.fullmatch(r'(\d+)\(М17\)', opd)
    if not (op == 'ЗП' and m and flat[i + 1][1][1:] == ('СЧИ', 'М13')):
        continue
    k = int(m.group(1))
    regs, n, base, body, j = [], None, '', None, i + 2
    while j < len(flat):
        a2, (lab2, op2, opd2) = flat[j]
        if op2 == 'СЛИА' and opd2.endswith('(М17)') and n is None:
            n = int(opd2.split('(')[0])
        elif op2 == 'СЧИМ':
            regs.append(opd2[1:])
        elif op2 == 'УИА' and opd2.endswith('(М14)'):
            base = 'своя'
        elif op2 == 'УИИ' and opd2 == 'М14(М15)':
            base = 'М15'
        elif op2 == 'ПБ':
            body = opd2
            break
        j += 1
    procs.append([a, k - 4, n, regs, base, body, flat[j + 1][0]])
for p, q in zip(procs, procs[1:] + [[max(order) + 1]]):
    ws = [a for a in order if p[0] <= a < q[0] and a in code]
    # the code ends where the constants begin
    last = ws[-1]
    calls = sorted({opd for a in ws for lab, op, opd in words[a]
                    if op == 'УИА' and opd.endswith('(М15)') and
                    (opd[:-5] in labels or re.fullmatch(r'[GD][0-7]{5}', opd[:-5]))})
    print('%05o  арг %d  кадр %2d  рег %-16s база %-4s тело %-7s выход %05o  до %05o  %4d слов, не исп. %4d  %s'
          % (p[0], p[1], p[2] or 0, ','.join(p[3]), p[4], p[5], p[6], last, len(ws),
             sum(1 for a in ws if a not in hit), ' '.join(c.split('(')[0] for c in calls)))
