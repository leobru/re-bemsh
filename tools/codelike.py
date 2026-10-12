#!/usr/bin/env python3
# Find runs of data words (КОНД) in the parts that look like code missed
# by the disassembler: both halves are plausible instructions.
# Usage: tools/codelike.py [-n MINRUN] [part ...]   (default: all, run >= 4)
# NOTCODE = ['ааааа', ...] in notes/NAME.py lists false candidates to skip.
# Reads parts/NAME.be.lst (left by tools/mkbe.py / reasm.pl -t).
# Prints "part first-last words" - candidates for ENTRIES in notes/NAME.py.
# Also single words "command / МОДА filler" (the right half is 02200000):
# a ПБ, or a command next to code; "part addr-addr 1 stop" when the word
# after it is data (STOPS in notes/NAME.py: the flow must not go there).
import re, sys

MIN = 4
args = sys.argv[1:]
if args[:1] == ['-n']:
    MIN = int(args[1]); args = args[2:]

parts = {}
for l in open('parts.txt', encoding='utf-8'):
    f = l.split()
    if f and not l.startswith('#'):
        parts[f[0]] = int(f[2], 8)


def half_ok(h, lo, hi):
    """A 24-bit half-word as an instruction: known opcode, sane address."""
    if h == 0:
        return 0.5                  # ЗП 0 - filler, neutral
    if h >> 19 & 1:                 # long address
        op, a = 0o20 + (h >> 15 & 0o17), h & 0o77777
        if op in (0o20, 0o21, 0o36):
            return 0
        if op in (0o26, 0o27, 0o30, 0o31, 0o34, 0o35, 0o37):   # jumps
            return 1 if lo <= a < hi or a < 0o2000 or a >= 0o70000 else 0
        return 1
    op, a = h >> 12 & 0o77, h & 0o7777
    if h >> 18 & 1:
        a |= 0o70000
    if op in (0o46, 0o47) or 0o50 <= op <= 0o77 and op not in \
            (0o50, 0o64, 0o66, 0o70, 0o71, 0o74, 0o75):
        return 0
    return 1


def notcode(p):
    """NOTCODE = ['ааааа', ...] in notes/NAME.py: starts of runs to skip."""
    g = {}
    try:
        exec(open('notes/%s.py' % p, encoding='utf-8').read(), g)
    except OSError:
        pass
    return {int(a, 8) for a in g.get('NOTCODE', [])}


for p in args or parts:
    base = parts[p]
    skip = notcode(p)
    words = []
    try:
        lst = open('parts/%s.be.lst' % p, encoding='utf-8', errors='replace')
    except OSError:
        continue
    code = set()                    # addresses of words with commands
    for l in lst:
        m = re.match(r'^.{24} ([0-7]{5})  ([0-7]{16}) .*(КОНД|КОНК)', l)
        if m and m.group(3) == 'КОНД':
            words.append((int(m.group(1), 8), int(m.group(2), 8)))
        m = re.match(r'^.{24} ([0-7]{5}) \d\d \d{2,3} ', l)
        if m:
            code.add(int(m.group(1), 8))
    hi = max([a for a, w in words] + [base]) + 1
    run = []

    def flush():
        # code has few repeated words and a jump every several words
        jumps = sum(1 for a, w, s in run for h in (w >> 24, w & 0xffffff)
                    if h >> 19 & 1 and (h >> 15 & 0o17) in (6, 7, 8, 9, 12, 13, 15))
        if len(run) >= MIN and run[0][0] not in skip and len({w for a, w, s in run}) * 10 >= len(run) * 7 \
                and jumps * 8 >= len(run):
            print('%-7s %05o-%05o %d' % (p, run[0][0], run[-1][0], len(run)))
        run.clear()

    data = dict(words)
    for a, w in words:
        l = w >> 24
        if w & 0xffffff != 0o02200000 or l in (0, 0o02200000) or not half_ok(l, base, hi + 0o2000):
            continue
        jump = l >> 19 & 1 and (l >> 15 & 0o17) == 0o10
        rzha = l >> 12 == 0o37       # РЖА n - the first command of a routine
        if a not in skip and (jump or rzha or a - 1 in code or a + 1 in code):
            nxt = data.get(a + 1)   # a constant: zero right half or bad code
            stop = not jump and nxt is not None and (nxt & 0xffffff == 0 or
                half_ok(nxt >> 24, base, hi) + half_ok(nxt & 0xffffff, base, hi) < 2)
            print('%-7s %05o-%05o 1%s' % (p, a, a, ' stop' if stop else ''))
    for a, w in words:
        s = half_ok(w >> 24, base, hi + 0o2000) + half_ok(w & 0xffffff, base, hi + 0o2000)
        bs = [(w >> (40 - 8 * k)) & 0xff for k in range(6)]
        text = all(b == 0 or 0o100 <= b <= 0o137 or 0o240 <= b <= 0o337 for b in bs)
        # a zero left half is a small constant, register 017 in both
        # halves with ЦИКЛ - a mask
        mask = (w >> 39) == 0o777 and (w >> 15 & 0o777) == 0o777
        ok = s >= 1.5 and not text and (w >> 24) != 0 and not mask
        if run and (not ok or a != run[-1][0] + 1):
            flush()
        if ok:
            run.append((a, w, s))
    flush()
