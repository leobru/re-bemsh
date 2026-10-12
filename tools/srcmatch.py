#!/usr/bin/env python3
# Match a fragment of original source text (decoded by tools/t8text.py)
# against the disassembled parts: runs of machine instructions after a
# label are searched in parts/NAME.be by their operation sequence, then
# the operands of the aligned lines give "source name -> address" (labels,
# cells) and "source register name -> number".
# Usage: tools/srcmatch.py SOURCE.txt part [part ...]   (table on stdout:
#        L label, S symbol, R register, C line comment, B comment block)
import re, sys, collections
sys.path.insert(0, 'tools')
from mkbe import addrmap, fieldmap

W = 6       # window of instructions that must match uniquely
OPS = set('''зп зпм рег счм сл вч вчоб вчаб сч и нтж слц знак или дел умн сбр рзб
чед нед слп вчп сд рж счрж счмр увв слпа вчпа сда ржа уи уим счи счим уии сли
мода мод уиа слиа по пе пб пв выпр стоп пио пино цикл'''.split())


def source(fn):
    """Source lines: (label, operation, operand, comment, comment block
    before the line)."""
    res = []; blk = []
    for l in open(fn, encoding='utf-8'):
        l = l.rstrip('\n').rstrip()
        if l.startswith('*'):
            blk.append(l)
            continue
        if not l.strip():
            continue
        m = re.match(r'(\S*)\s+(\S+)(?:\s+(\S+))?(?:\s+(.*))?', l)
        if m:
            res.append((m.group(1), m.group(2).lower(), m.group(3) or '',
                        (m.group(4) or '').strip(), blk))
        blk = []
    return res


def part(p):
    amap = addrmap('parts/%s.be.lst' % p)
    fmap = fieldmap('parts/%s.be.lst' % p)
    res = []
    for i, l in enumerate(open('parts/%s.be' % p, encoding='utf-8').read().split('\n'), 1):
        f = l.split('\t')
        if l.startswith('*') or len(f) < 2 or i not in amap:
            continue
        op, opnd = f[1].lower(), (f[2] if len(f) > 2 else '').split(',')[0] if f[1] != 'пв' else (f[2] if len(f) > 2 else '')
        if op == 'пвл':
            op = 'пв'
        if op == 'мода' and not opnd:
            continue                # an automatic filler
        res.append((amap[i], op, opnd, fmap.get(i)))
    return res


def allnames():
    """Name -> address from the NAMES of all notes (for external operands)."""
    import glob
    res = {}
    for fn in glob.glob('notes/*.py'):
        ns = {}
        exec(open(fn, encoding='utf-8').read(), ns)
        for a, n in ns.get('NAMES', {}).items():
            res.setdefault(n, a)
    return res


def resolve(o, fld, known):
    """Address of the symbol part of an operand of a part (without +N)."""
    m = re.match(r"([А-ЯA-Z][А-ЯA-Z0-9]*)([+-]\d+)?", o)
    if not m:
        return None
    k = int(m.group(2) or 0)
    n = m.group(1)
    if re.fullmatch(r'[GD][0-7]{5}', n):
        return int(n[1:], 8) + k
    if n in known and re.fullmatch(r'[0-7]{5}', known[n]):
        return int(known[n], 8) + k
    return fld if fld else None


def reg(o):
    m = re.search(r'\(([^()]*)\)$', o)
    return m.group(1) if m else None


def shift(o):
    m = re.fullmatch(r'64([+-]\d+)', o)
    return m.group(1) if m else None


def main():
    args = sys.argv[1:]
    src = source(args[0])
    known = allnames()
    for p in args[1:]:
        code = part(p)
        ops = [c[1] for c in code]
        sym = collections.defaultdict(collections.Counter)
        regs = collections.defaultdict(collections.Counter)
        labs = {}
        cmt = {}; blks = {}
        i = 0
        while i < len(src):
            j = i                   # a run of machine instructions
            while j < len(src) and src[j][1] in OPS:
                j += 1
            run = src[i:j]
            i = max(j, i + 1)
            if len(run) < 4:
                continue
            # the whole run, else its unique windows of W instructions
            wins = [(0, len(run))] + [(x, x + W) for x in range(len(run) - W + 1)]
            done = set()
            for x0, x1 in wins:
                seq = [r[1] for r in run[x0:x1]]
                hits = [k for k in range(len(ops) - len(seq) + 1) if ops[k:k + len(seq)] == seq
                        and all(shift(r[2]) is None or shift(r[2]) == shift(code[k + n][2])
                                for n, r in enumerate(run[x0:x1]))]
                if len(hits) != 1:
                    continue
                for n, r in enumerate(run[x0:x1]):
                    if x0 + n in done:
                        continue
                    done.add(x0 + n)
                    a, op, o, fld = code[hits[0] + n]
                    if r[0]:
                        labs[r[0]] = a
                    if r[3] and '<' not in r[3]:
                        cmt[a] = r[3]
                    if r[4] and any(x.strip('* ') for x in r[4]):
                        blks[a] = r[4]
                    sr, pr = reg(r[2]), reg(o)
                    if sr and pr and not sr.lstrip('-').isdigit():
                        regs[sr][pr] += 1
                    m = re.fullmatch(r'([А-ЯA-Z][А-ЯA-Z0-9]*)([+-]\d+)?(\(.*\))?', r[2])
                    if m and op not in ('уи', 'счи', 'уии', 'сли', 'уим', 'счим') \
                            and (m.group(3) is None) == (pr is None):
                        t = resolve(o, fld, known)
                        if t is not None:
                            sym[m.group(1)]['%05o' % ((t - int(m.group(2) or 0)) & 0o77777)] += 1
        print('==', p, ': labels', len(labs), 'symbols', len(sym))
        for n, a in sorted(labs.items(), key=lambda x: x[1]):
            print('L %-7s %s' % (n, a))
        for n, c in sorted(sym.items()):
            print('S %-7s %s' % (n, ' '.join('%s×%d' % x for x in c.most_common(3))))
        for n, c in sorted(regs.items()):
            print('R %-7s %s' % (n, ' '.join('%s×%d' % x for x in c.most_common(3))))
        for a, c in sorted(cmt.items()):
            print('C %s %s' % (a, c))
        for a, c in sorted(blks.items()):
            print('B %s %s' % (a, '|'.join(c)))


if __name__ == '__main__':
    main()
