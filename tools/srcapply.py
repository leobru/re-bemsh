#!/usr/bin/env python3
# Put the text of an original source fragment into the restored parts:
# for the instructions aligned by tools/srcmatch.py (same operation
# sequence) the operand and the comment of the source line replace the
# disassembled ones, the known macros (ПРСЛ, ХЭШ, ОБМЕН, ПОСР) replace
# their expansions. Writes notes/src/PART.py (SRC, SRCREG, NAMES) that
# tools/mkbe.py applies; lines listed in notes/src/PART.skip (addresses,
# one per line) are left as disassembled - put there what does not
# reassemble to the same bytes.
# Usage: tools/srcapply.py SOURCE.txt part [part ...]
import re, sys, os, collections
sys.path.insert(0, 'tools')
import srcmatch
from srcmatch import OPS, W, reg, shift

MACROS = {
    'прсл': lambda o: [('сч', o.split(',')[0] if o.split(',')[0] != '0' else ''),
                       ('зп', ','.join(o.split(',')[1:]))],
    'хэш': lambda o: [('сч', 'Т'), ('сда', '64+6'), ('нтж', 'Т'), ('и', "=В'77'"), ('уи', o)],
    'обмен': lambda o: [('э70', o)],
    'поср': lambda o: [('пв', 'ПОСР(ВПОСР)')],
}


def value(o, known):
    """Value of an address expression without its register part: names
    (known addresses), decimal and 'octal' numbers, + and -; None if it
    cannot be computed."""
    o = re.sub(r'\([^()]*\)$', '', o)
    if o == '':
        return 0
    v = 0
    for sg, t in re.findall(r"([+-]?)('[0-7]+'|\d+|[А-ЯA-Z][А-ЯA-Z0-9]*)", o):
        if t[0] == "'":
            x = int(t[1:-1], 8)
        elif t.isdigit():
            x = int(t)
        elif re.fullmatch(r'[GD][0-7]{5}', t):
            x = int(t[1:], 8)
        elif t in known and re.fullmatch(r'[0-7]{5}', known[t]):
            x = int(known[t], 8)
        else:
            return None
        v += -x if sg == '-' else x
    if re.sub(r"[+-]?('[0-7]+'|\d+|[А-ЯA-Z][А-ЯA-Z0-9]*)", '', o):
        return None
    return v & 0o77777


def sreg(o):
    return None if o.startswith('=') else reg(o)


def virtual(src):
    """Source lines expanded to instructions: (line index, k of n, op, operand)."""
    res = []
    for i, (lab, op, opnd, cmt, blk) in enumerate(src):
        if op in MACROS and not (op == 'прсл' and opnd.count(',') != 1):
            exp = MACROS[op](opnd)
            res += [(i, k, len(exp), o, a) for k, (o, a) in enumerate(exp)]
        elif op in OPS:
            res.append((i, 0, 1, op, opnd))
        else:
            res.append((i, 0, 0, None, None))       # breaks a run
    return res


def main():
    # the parts as disassembled, without the source text applied before
    import subprocess
    subprocess.run(['tools/mkbe.py'] + sys.argv[2:], env=dict(os.environ, NOSRC='1'),
                   stdout=subprocess.DEVNULL, check=True)
    src = srcmatch.source(sys.argv[1])
    vs = virtual(src)
    known = srcmatch.allnames()
    os.makedirs('notes/src', exist_ok=True)
    for p in sys.argv[2:]:
        code = srcmatch.part(p)
        ops = [c[1] for c in code]
        pair = {}                   # index in vs -> index in code
        i = 0
        while i < len(vs):
            j = i
            while j < len(vs) and vs[j][3]:
                j += 1
            run = vs[i:j]
            i0 = i
            i = max(j, i + 1)
            if len(run) < 4:
                continue
            for x0, x1 in [(0, len(run))] + [(x, x + W) for x in range(len(run) - W + 1)]:
                seq = [r[3] for r in run[x0:x1]]
                hits = [k for k in range(len(ops) - len(seq) + 1) if ops[k:k + len(seq)] == seq
                        and all(shift(r[4]) is None or shift(r[4]) == shift(code[k + n][2])
                                for n, r in enumerate(run[x0:x1]))]
                if len(hits) == 1:
                    for n in range(x1 - x0):
                        pair.setdefault(i0 + x0 + n, hits[0] + n)
        # registers: a source name must always meet the same register
        regs = collections.defaultdict(collections.Counter)
        for v, c in pair.items():
            sr, pr = sreg(vs[v][4]), reg(code[c][2])
            if sr and pr and not sr.lstrip('-').isdigit():
                regs[sr][pr] += 1
        regs = {n: c.most_common(1)[0][0] for n, c in regs.items()
                if len(c) == 1 and re.fullmatch(r'М[0-7]+', c.most_common(1)[0][0])}
        num = lambda m: int(m[1:], 8)       # М16 -> 14
        skip = set()
        if os.path.exists('notes/src/%s.skip' % p):
            skip = set(open('notes/src/%s.skip' % p).read().split())
        used = {}                   # a part address is taken by one source line
        SRC = {}; NAMES = {}; usedreg = {}
        # whole source lines only: every instruction of the line is paired,
        # with consecutive addresses, same registers, usable operands
        byline = collections.defaultdict(list)
        for v, c in sorted(pair.items()):
            byline[vs[v][0]].append((v, c))
        for li, lst in sorted(byline.items()):
            lab, op, opnd, cmt, blk = src[li]
            n = vs[lst[0][0]][2]
            if len(lst) != n or [c for _, c in lst] != list(range(lst[0][1], lst[0][1] + n)):
                continue
            addrs = [code[c][0] for _, c in lst]
            if any(a in used or a in skip for a in addrs):
                continue
            ok = True; rr = {}
            for v, c in lst:
                sr, pr = sreg(vs[v][4]), reg(code[c][2])
                # the same address value on both sides (registers aside)
                if not vs[v][4].startswith('=') and vs[v][3] not in ('уи', 'счи', 'уии', 'сли', 'уим', 'счим'):
                    a1, a2 = value(vs[v][4], known), value(code[c][2], known)
                    if a1 is None or a2 is None or a1 != a2:
                        ok = False
                if (sr is None) != (pr is None):
                    ok = False
                elif sr and sr.lstrip('-').isdigit():
                    ok = ok and pr.startswith('М') and int(sr) == num(pr)
                elif sr:
                    ok = ok and regs.get(sr) == pr
                    rr[sr] = pr
            # symbols of the operand must be known names (or labels of the
            # source that got an address); a literal cannot be reproduced
            body = opnd
            syms = re.findall(r"(?<![А-ЯA-Z0-9'])[А-ЯA-Z][А-ЯA-Z0-9]*", re.sub(r"'[^']*'", '', body))
            lit = '=' in body
            for s_ in ([] if lit and n == 1 and op not in MACROS else syms):
                if s_ in rr or s_ in regs:
                    if s_ in regs:
                        rr.setdefault(s_, regs[s_])
                    continue
                if s_ not in known:
                    ok = False
            if not ok:
                continue
            if lit and op in MACROS:
                continue
            if lit and n == 1:
                # keep the operand of the part, the literal goes to the comment
                text = (None, (opnd + '  ' + cmt).strip())
            elif lit:
                continue
            else:
                text = (opnd, cmt)
            for a in addrs:
                used[a] = li
            usedreg.update(rr)
            if op not in MACROS:
                SRC[addrs[0]] = ('line',) + text
            else:
                SRC[addrs[0]] = ('macro', src[li][1].upper(), opnd, cmt)
                for a in addrs[1:]:
                    SRC[a] = ('drop',)
            if lab and re.fullmatch(r'[А-ЯA-Z][А-ЯA-Z0-9]{0,5}', lab) and \
                    re.fullmatch(r'[0-7]{5}', addrs[0]) and lab not in known:
                NAMES[addrs[0]] = lab
        with open('notes/src/%s.py' % p, 'w', encoding='utf-8') as f:
            f.write('# generated by tools/srcapply.py from %s: do not edit\n' % sys.argv[1])
            f.write('SRCREG = %r\n' % {n: num(m) for n, m in sorted(usedreg.items())})
            f.write('SRCNAMES = %r\n' % NAMES)
            f.write('SRC = {\n')
            for a, t in sorted(SRC.items()):
                f.write(' %r: %r,\n' % (a, t))
            f.write('}\n')
        print(p, ': lines', sum(1 for t in SRC.values() if t[0] == 'line'),
              'macros', sum(1 for t in SRC.values() if t[0] == 'macro'),
              'names', len(NAMES), 'registers', len(usedreg))


if __name__ == '__main__':
    main()
