#!/usr/bin/env python3
# Find the expansions of the macros of the macro editor's source text
# (macros.be: ПРСЛ, ХЭШ, ДС, НЗП, ЗБП, ПОСР, ПРОД, ПРКЛ, ДСПРКЛ,
# ПРНЕОБ; ОБМЕН - the assembler's own name of Э70) in the restored parts
# and write notes/mac/PART.py - macro calls
# in place of their expansions (MAC = {address: ('macro', NAME, operands,
# comment) or ('drop',)}) that tools/mkbe.py applies after the source
# text of notes/src (whose lines win) unless NOSRC=1.
# A call never crosses a label, a comment or a block comment inside the
# expansion; operands are the cells of the part (a literal of the source,
# =В'77', is the pool cell D... here, as in notes/src).
# Usage: tools/macapply.py -c [part ...]   counts per part and macro (all
#                                          patterns, whatever SCOPE says)
#        tools/macapply.py part [part ...]  writes notes/mac/PART.py for
#                                          the macros of SCOPE
import os, re, subprocess, sys, collections
sys.path.insert(0, 'tools')
from mkbe import addrmap, load_notes

# where the macros are used: the macro editor (its author's notation) and
# the hash of a term in the macro machine (the same computation)
SCOPE = {'mred74': None, 'mred2': None, 'mmash': {'ХЭШ'}}
PAIRS = 3                   # pairs of a ПРКЛ chain on one card
CALLS = {'ДС': 'ДС', 'НЗП': 'НЗП', 'ЗБП': 'ЗБП', 'ПОСР': 'ПОСР', 'ПРОДОЛ': 'ПРОД'}


def lines(p):
    """Instructions of parts/p.be: dicts with address, label, op,
    operand, comment; 'stop' - something between it and the previous
    instruction (a comment line, a non-command)."""
    amap = addrmap('parts/%s.be.lst' % p)
    notes = load_notes(p)
    blk = set(notes.get('BLOCK', {})) | set(notes.get('INLINE', {}))
    res = []; stop = True
    for i, l in enumerate(open('parts/%s.be' % p, encoding='utf-8').read().split('\n'), 1):
        f = l.split('\t')
        if l.startswith('*') or i not in amap or len(f) < 2:
            stop = True
            continue
        opnd = f[2] if len(f) > 2 else ''
        cmt = f[3] if len(f) > 3 else ''
        if opnd.startswith(','):
            opnd, cmt = '', opnd[1:]
        res.append(dict(a=amap[i], lab=f[0], op=f[1].lower(), opnd=opnd, cmt=cmt,
                        stop=stop or amap[i] in blk))
        stop = False
    return res


def free(x):
    """x may be swallowed into the call before it."""
    return not x['lab'] and not x['cmt'] and not x['stop']


def find(L):
    """(index, length, name, operands) of the macro calls, left to right."""
    res = []; k = 0
    while k < len(L):
        x = L[k]
        nxt = lambda n: k + n < len(L) and free(L[k + n])
        op = lambda n: L[k + n]['op'] if k + n < len(L) else None
        arg = lambda n: L[k + n]['opnd']
        m = None
        if x['op'] == 'сч' and [op(n) for n in range(1, 5)] == ['сда', 'нтж', 'и', 'уи'] \
                and all(nxt(n) for n in range(1, 5)) and arg(1) == '64+6' and arg(2) == x['opnd']:
            o = arg(4)
            if x['opnd'] != 'Т':
                o += ',Т=' + x['opnd']
            if arg(3) != 'В77':
                o += ',К=' + arg(3)
            m = (5, 'ХЭШ', o)
        elif x['op'] == 'сч' and x['opnd'] == 'ЗАГЗАП' and [op(n) for n in range(1, 5)] == \
                ['или', 'зп', 'уиа', 'пв'] and all(nxt(n) for n in range(1, 5)) and \
                arg(2) == 'ЗАГЗАП' and arg(3) == 'ПИФ(М1)' and arg(4) == 'ПИШЗАП(М2)':
            m = (5, 'ПРНЕОБ', arg(1))
        elif x['op'] == 'сч' and op(1) == 'пв' and nxt(1) and arg(1) == 'ЗБП(М16)':
            m = (2, 'ЗБП', x['opnd'])
        elif x['op'] == 'сч' and x['opnd'] == 'S' and op(1) == 'нтж' and op(2) == 'по' \
                and nxt(1) and nxt(2):
            n = 1; pairs = []
            while op(n) == 'нтж' and op(n + 1) == 'по' and nxt(n) and nxt(n + 1):
                pairs += [arg(n), arg(n + 1)]; n += 2
            m = (n, 'ПРКЛ', 'S,(%s)' % ','.join(pairs))
        elif x['op'] == 'пв' and re.fullmatch(r'(\w+)\(М16\)', x['opnd']) and \
                x['opnd'][:-5] in CALLS:
            name = CALLS[x['opnd'][:-5]]
            n = 1; pairs = []
            if name == 'ДС':
                while op(n) == 'нтж' and op(n + 1) == 'по' and nxt(n) and nxt(n + 1):
                    pairs += [arg(n), arg(n + 1)]; n += 2
            m = (n, 'ДСПРКЛ', '(%s)' % ','.join(pairs)) if pairs else (1, name, '')
        elif x['op'] == 'э70':
            m = (1, 'ОБМЕН', x['opnd'])
        elif x['op'] == 'сч' and op(1) == 'зп' and nxt(1):
            n = 1; to = []
            while op(n) == 'зп' and nxt(n) and n <= 4:
                to.append(arg(n)); n += 1
            if all(t and ',' not in t for t in to) and ',' not in x['opnd']:
                m = (n, 'ПРСЛ', '%s,%s' % (x['opnd'], to[0] if len(to) == 1 and not to[0].startswith('(') else '(%s)' % ','.join(to)))
        if m and m[1] in ('ПРКЛ', 'ДСПРКЛ') and len(pairs) > 2 * PAIRS:
            # a long chain does not fit a card: ПРКЛ ,(...) continues it
            n0 = m[0] - len(pairs)
            for c in range(0, len(pairs), 2 * PAIRS):
                ch = pairs[c:c + 2 * PAIRS]
                if c == 0:
                    o = m[2][:m[2].index('(')] + '(%s)' % ','.join(ch)
                    res.append((k, n0 + len(ch), m[1], o))
                else:
                    res.append((k + n0 + c, len(ch), 'ПРКЛ', ',(%s)' % ','.join(ch)))
            k += m[0]
        elif m:
            res.append((k,) + m)
            k += m[0]
        else:
            k += 1
    return res


def main():
    args = sys.argv[1:]
    count = args[:1] == ['-c']
    if count:
        args = args[1:] or [l.split()[0] for l in open('parts.txt') if l.strip() and not l.startswith('#')]
    # the parts without notes/src and notes/mac
    subprocess.run(['tools/mkbe.py'] + args, env=dict(os.environ, NOSRC='1'),
                   stdout=subprocess.DEVNULL, check=True)
    os.makedirs('notes/mac', exist_ok=True)
    for p in args:
        L = lines(p)
        calls = find(L)
        if not count:
            calls = [c for c in calls if p in SCOPE and (SCOPE[p] is None or c[2] in SCOPE[p])]
        if count:
            c = collections.Counter(c[2] for c in calls)
            print('%-7s' % p, ' '.join('%s %d' % x for x in sorted(c.items())))
            # the same idioms without the names of the macro editor: a
            # chain of 2+ НТЖ/ПО pairs after СЧ of any cell or after a call
            ch = collections.Counter()
            for k, x in enumerate(L):
                n = 1
                while k + n + 1 < len(L) and L[k + n]['op'] == 'нтж' and \
                        L[k + n + 1]['op'] == 'по' and free(L[k + n]) and free(L[k + n + 1]):
                    n += 2
                if n >= 5 and x['op'] in ('сч', 'пв'):
                    ch['цепочка после ' + x['op']] += 1
            if ch:
                print('%-7s' % '', ' '.join('%s %d' % x for x in sorted(ch.items())))
            continue
        MAC = {}
        for k, n, name, o in calls:
            MAC[L[k]['a']] = ('macro', name, o, L[k]['cmt'])
            for j in range(1, n):
                MAC[L[k + j]['a']] = ('drop',)
        with open('notes/mac/%s.py' % p, 'w', encoding='utf-8') as f:
            f.write('# generated by tools/macapply.py: do not edit\n')
            f.write('MAC = {\n')
            for a, t in sorted(MAC.items()):
                f.write(' %r: %r,\n' % (a, t))
            f.write('}\n')
        print(p, ':', len(calls), 'calls')
    subprocess.run(['tools/mkbe.py'] + args, stdout=subprocess.DEVNULL, check=True)


if __name__ == '__main__':
    main()
