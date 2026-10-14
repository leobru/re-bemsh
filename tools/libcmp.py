#!/usr/bin/env python3
# Compare the procedures of an object module (e.g. a УПД library module
# found by tools/findmod.py) with the procedures of a part.
# Usage: tools/libcmp.py [-d N] MODULE.bin PART
#   MODULE.bin - the zones of the module (from its first zone); it is
#   disassembled by "disbesm6 -r" with every entry as code. PART - a part
#   of parts.txt (parts/PART.bin, names from notes/PART.py).
#   A procedure starts with the prologue ЗП k(М17) / СЧИ М13 (see
#   tools/procs.py). Half-words are compared by register, operation and
#   address; an address above 01000 is taken as absolute (relocated) and
#   not compared. For every procedure of the module prints the most similar
#   procedure of the part: similarity (difflib ratio), lengths in words,
#   number of the arguments (k - 4) and frame size of both.
#   -d N - also print the differences for the procedure of the module at
#          octal address N.
import difflib, os, re, subprocess, sys

DIS = os.environ.get('DISBESM6', os.path.expanduser('~/git/leobru/dispak-tools/disbesm6'))
args = sys.argv[1:]
show = None
if args[0] == '-d':
    show = int(args[1], 8); args = args[2:]
mod, part = args

def halves(word):
    return [word >> 24, word & 0xffffff]

def module_words(path):
    out = subprocess.run([DIS, '-r', path], capture_output=True, text=True).stdout
    ents = ['-e' + m.group(1) for m in re.finditer(r'^([0-7]{5}) 7[0-7]{6}00420013\t\S', out, re.M)]
    out = subprocess.run([DIS, '-r'] + ents + [path], capture_output=True, text=True).stdout
    w, names, cur, hw = {}, {}, None, []
    for l in out.split('\n'):
        m = re.match(r'^([0-7]{5})[ :]([0-7]{16})\t(\S*)', l)
        if m:
            cur = int(m.group(1), 8)
            w[cur] = int(m.group(2), 8)
            if m.group(3):
                names[cur] = m.group(3)
            continue
        m = re.match(r'^([0-7]{5})?[ :]?\s*([0-7]{2}) ([0-7]{2,3}) +([0-7]{4,5})\t(\S*)', l)
        if not m:
            continue
        if m.group(1):
            cur = int(m.group(1), 8); hw = []
            if m.group(5):
                names[cur] = m.group(5)
        r, op, a = int(m.group(2), 8), m.group(3), int(m.group(4), 8)
        h = r << 20 | (int(op, 8) << 15 if len(op) == 2 else int(op, 8) << 12) | a
        hw.append(h)
        if len(hw) == 2:
            w[cur] = hw[0] << 24 | hw[1]
    return w, names

def part_words(name):
    org = None
    for l in open('parts.txt'):
        f = l.split()
        if f and f[0] == name:
            org = int(f[2], 8)
    d = open('parts/%s.bin' % name, 'rb').read()
    w = {org + i // 6: int.from_bytes(d[i:i + 6], 'big') for i in range(0, len(d) - 5, 6)}
    names = {}
    if os.path.exists('notes/%s.py' % name):
        ns = {}
        exec(open('notes/%s.py' % name).read(), ns)
        names = {int(a, 8): n for a, n in ns.get('NAMES', {}).items()}
    return w, names

def key(h):
    r, rest = h >> 20, h & 0xfffff
    if rest & 0x80000:
        op, a = rest >> 15, rest & 0o77777
    else:
        op, a = rest >> 12, rest & 0o7777
    return (r, op, a if a < 0o1000 or a > 0o77000 else '*')

def procs(w):
    # address -> (k, frame); prologue: ЗП k(М17) / СЧИ М13 in one word
    res = {}
    for a, v in sorted(w.items()):
        l, r = halves(v)
        if l >> 12 == 0o17 << 8 and r == 0o00420013:
            k = l & 0o7777
            frame = None
            if a + 2 in w and halves(w[a + 2])[0] >> 15 == 0o17 << 5 | 0o25:
                frame = halves(w[a + 2])[0] & 0o77777
            res[a] = (k - 4, frame)
    return res

def bodies(w, ps):
    starts = sorted(ps) + [max(w) + 1]
    return {a: [key(h) for x in range(a, b) if x in w for h in halves(w[x])]
            for a, b in zip(starts, starts[1:])}

mw, mn = module_words(mod)
pw, pn = part_words(part)
mp, pp = procs(mw), procs(pw)
mb, pb = bodies(mw, mp), bodies(pw, pp)

def pname(names, a):
    return names.get(a) or names.get(a - 1, '') + ('+1' if a - 1 in names else '') or '%05o' % a

for a in sorted(mp):
    best = max(pp, key=lambda b: difflib.SequenceMatcher(None, mb[a], pb[b], autojunk=False).ratio())
    sm = difflib.SequenceMatcher(None, mb[a], pb[best], autojunk=False)
    print('%05o %-7s арг %d кадр %2s %4d сл.  ~ %05o %-7s арг %d кадр %2s %4d сл.  %3d%%'
          % (a, pname(mn, a), mp[a][0], mp[a][1], len(mb[a]) // 2,
             best, pname(pn, best), pp[best][0], pp[best][1], len(pb[best]) // 2,
             round(100 * sm.ratio())))
    if show == a:
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != 'equal':
                print('   %s модуль %05o+%d (%d) / часть %05o+%d (%d)'
                      % (tag, a, i1 // 2, i2 - i1, best, j1 // 2, j2 - j1))
