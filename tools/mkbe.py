#!/usr/bin/env python3
# Make the commented source parts/NAME.be from the raw disassembly
# parts/NAME.dis and the notes in notes/NAME.py, then check it reassembles.
#
# Usage: tools/mkbe.py NAME [NAME ...]
#
# notes/NAME.py may define (all keys are octal addresses as strings,
# "ааааап" meaning the right half of the word):
#   NAMES  = {'77316': 'ЛИТЕРА', ...}   names of this part's addresses: an
#            existing Gааааа/Dааааа label is renamed, an unlabelled word gets
#            a label, an address inside a ПАМ block gets an ЭКВ;
#   USES   = ['mon0', 'mred24']         parts in memory together with this
#            one: a literal address 'ааааа' inside one of them becomes
#            its name (NAMES there, else its label Gааааа/Dааааа, else a
#            new label Dааааа), declared after the header with
#            МОДУЛЬ ВНЕШ ИМЯ,...; the owner lists it in ВХОД ИМЯ,...
#            (ВЭКВ from an external is not resolved by РВС: it takes such
#            a pair for a common area). ВНЕШ, ВХОД and М come from macros.be.
#            Modules are linked together by tools/reasm.pl;
#   TOP    = '''* ...'''                block comment after the СТАРТ lines;
#   BLOCK  = {'77316': '''* ...'''}     block comments before an address;
#   INLINE = {'77316': '...'}           end-of-line comments (after a comma
#            when the operand is empty).
import importlib.util, os, re, subprocess, sys


def load_notes(name):
    fn = 'notes/%s.py' % name
    if not os.path.exists(fn):
        return {}
    spec = importlib.util.spec_from_file_location('notes_' + name, fn)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {k: getattr(mod, k) for k in dir(mod) if k.isupper()}


def addrmap(lst):
    """Source line number -> 'ааааа' (word, left half) or 'ааааап'."""
    res = {}; cur = None
    for l in open(lst, encoding='utf-8', errors='replace'):
        a = l[25:30]
        m = re.search(r' (\d{4})  (\d{4}) ', l[31:])
        if re.fullmatch(r'[0-7]{5}', a) and l[24] == ' ' and not m:
            cur = a + 'ф'           # automatic filler in the left half
            continue
        if not m or len(l) < 31:
            continue
        line = int(m.group(2))
        if re.fullmatch(r'[0-7]{5}', a) and l[24] == ' ':
            cur = a
            res[line] = a
        elif a.strip() == '' and cur and cur.endswith('ф') and l[31:40].strip():
            res[line] = cur[:-1]    # the instruction after it owns the word
        elif a.strip() == '' and cur and l[31:40].strip():
            res[line] = cur.rstrip('ф') + 'п'
    return res


def modules():
    """part -> module name, from parts.txt"""
    res = {}
    for l in open('parts.txt', encoding='utf-8'):
        f = l.split()
        if f and not l.startswith('#'):
            res[f[0]] = f[1]
    return res


# a literal address operand 'ааааа' (not a constant like п'2000')
LITADDR = r"(?<![А-Яа-яA-Za-z])'([0-7]{4,5})'"


def ranges():
    """part -> (first address, address after the last word)"""
    res = {}
    for l in open('parts.txt', encoding='utf-8'):
        f = l.split()
        if f and not l.startswith('#'):
            lo = int(f[2], 8)
            res[f[0]] = (lo, lo + os.path.getsize('parts/%s.bin' % f[0]) // 6)
    return res


def dis_labels(part):
    """address -> G/D label of parts/PART.dis"""
    res = {}
    for l in open('parts/%s.dis' % part, encoding='utf-8'):
        m = re.match(r'^([GD]([0-7]{5}))\t', l)
        if m:
            res[m.group(2)] = m.group(1)
    return res


def ext_map(part):
    """Literal addresses 'ааааа' of parts/PART.dis that fall into a part of
    USES (parts in memory together with PART): address -> (name, owner).
    The name is the owner's NAMES entry, else its label, else Dааааа."""
    rng = ranges()
    lo, hi = rng[part]
    res = {}
    uses = load_notes(part).get('USES', [])
    for l in open('parts/%s.dis' % part, encoding='utf-8'):
        f = l.rstrip('\n').split('\t')
        if len(f) < 3:
            continue
        for m in re.finditer(LITADDR, f[2]):
            a = int(m.group(1), 8)
            if lo <= a < hi:
                continue
            for u in uses:      # a name of the owner, even outside its range
                if '%05o' % a in load_notes(u).get('NAMES', {}):
                    res['%05o' % a] = u
                    break
            else:
                for u in uses:
                    if rng[u][0] <= a < rng[u][1]:
                        res['%05o' % a] = u
                        break
    out = {}
    for u in set(res.values()):
        names = load_notes(u).get('NAMES', {})
        labs = dis_labels(u)
        for a in [a for a in res if res[a] == u]:
            out[a] = (names.get(a) or labs.get(a) or 'D' + a, u)
    return out


def exports(name):
    """address -> name of NAME used by the parts that list it in USES."""
    res = {}
    for fn in sorted(os.listdir('notes')):
        other = fn[:-3]
        if not fn.endswith('.py') or other == name or \
                name not in load_notes(other).get('USES', []):
            continue
        res.update({a: n for a, (n, u) in ext_map(other).items() if u == name})
    return res


def chunks(names, n=5):      # a card holds 5 names of 6 letters
    return [names[i:i + n] for i in range(0, len(names), n)]


def run(*cmd):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True).stdout


def make(name):
    notes = load_notes(name)
    names = notes.get('NAMES', {})
    bad = [n for n in names.values()
           if not re.fullmatch(r'[А-ЯA-Z][А-ЯA-Z0-9]{0,5}', n)]
    if bad:
        sys.exit('%s: bad label names: %s' % (name, ' '.join(bad)))
    owner = ext_map(name)
    ext = {a: n for a, (n, u) in owner.items()}
    mods = modules()
    expo = exports(name)
    # an exported address without a name of its own gets its label name
    # (an unlabelled word gets the label, a word inside ПАМ - an ЭКВ)
    names = dict(names)
    labs = dis_labels(name)
    for a in expo:
        if a not in names and a not in labs:
            names[a] = expo[a]
    plain = 'parts/%s.plain.be' % name
    run('tools/stripmoda.py', 'parts/%s.dis' % name, plain)
    # of the disbesm6 header macros Б, Е, М the parts need only М
    src = open(plain, encoding='utf-8').read().split('\n')
    src = [l for i, l in enumerate(src) if not (i < 4 and l in ('\tБ', '\tЕ'))]
    open(plain, 'w', encoding='utf-8').write('\n'.join(src))
    run('tools/reasm.pl', '-t', plain)     # translation only, for the listing
    if not os.path.exists(plain + '.lst'):
        sys.exit('%s: plain source was not translated' % name)
    amap = addrmap(plain + '.lst')
    byaddr = {}
    for n, a in sorted(amap.items()):
        byaddr.setdefault(a, n)
    L = open(plain, encoding='utf-8').read().split('\n')
    # a ПАМ running past 077777 overflows the location counter (warning
    # ПЕРЕПОЛН СЧА): one word is enough, the rest of the image is zero
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        if len(f) >= 3 and f[1] == 'пам' and amap.get(i) and \
                re.fullmatch(r'\d+', f[2]) and \
                int(amap[i], 8) + int(f[2]) >= 0o100000:
            f[2] = '1'
            L[i - 1] = '\t'.join(f)
    # labels of this part by address
    lab = {}
    for i, l in enumerate(L, 1):
        m = re.match(r'^([GD]([0-7]{5}))\t', l)
        if m:
            lab[m.group(2)] = m.group(1)
    rename = {lab[a]: n for a, n in names.items() if a in lab}
    newlab = {a: n for a, n in names.items() if a not in lab and a in byaddr}
    ekv_own = {a: n for a, n in names.items() if a not in lab and a not in byaddr}
    used_ext = {}

    def subst(l):
        def r1(m):
            return rename.get(m.group(1), m.group(1))
        l = re.sub(r'(?<![А-Я0-9A-Z])([GD][0-7]{5})(?![0-7])', r1, l)

        def r2(m):
            a = '%05o' % int(m.group(1), 8)
            if a in ext:
                used_ext[a] = ext[a]
                return ext[a]
            if a in ekv_own:
                return ekv_own[a]
            return m.group(0)
        f = l.split('\t')
        if len(f) >= 3:
            f[2] = re.sub(LITADDR, r2, f[2])
            l = '\t'.join(f)
        return l

    out = []
    for i, l in enumerate(L, 1):
        a = amap.get(i)
        first = a is not None and byaddr.get(a) == i
        if i == 3 and 'TOP' in notes:
            out.extend(notes['TOP'].strip('\n').split('\n'))
        if first and a in notes.get('BLOCK', {}):
            out.extend(notes['BLOCK'][a].strip('\n').split('\n'))
        if first and a in newlab:
            if not l.startswith('\t') or a.endswith('п'):
                sys.exit('%s: cannot label %s: %s' % (name, a, l))
            if out and out[-1].startswith('\tмода\t,'):
                out.pop()
            l = newlab[a] + l
        if l.startswith('\tФИНИШ'):
            for a2, n in sorted(ekv_own.items()):
                out.append("%s\tэкв\t'%s'" % (n, a2))
        l = subst(l)
        if first and a in notes.get('INLINE', {}):
            f = l.split('\t')
            if len(f) >= 3 and f[2]:
                l = l + '\t' + notes['INLINE'][a]
            else:
                l = '\t'.join(f[:2]) + '\t,' + notes['INLINE'][a]
        out.append(l)
    # externals and entries go after the СТАРТ/М header
    head = []
    imp = {}                        # owner -> names
    for a2 in used_ext:
        imp.setdefault(owner[a2][1], set()).add(used_ext[a2])
    for u in sorted(imp):
        for c in chunks(sorted(imp[u])):
            head.append('%s\tвнеш\t%s' % (mods[u], ','.join(c)))
    for c in chunks(sorted(set(expo.values()))):
        head.append('\tвход\t' + ','.join(c))
    out[2:2] = head
    text = '\n'.join(out)
    open('parts/%s.be' % name, 'w', encoding='utf-8').write(text)
    for k in list(notes.get('BLOCK', {})) + list(notes.get('INLINE', {})) + list(newlab):
        if k not in byaddr:
            print('%s: no source line at %s' % (name, k), file=sys.stderr)
    for f in (plain, plain + '.lst'):
        os.remove(f)


# all sources first, then translate them and link all parts in one РВС run
for n in sys.argv[1:]:
    make(n)
print(run('tools/reasm.pl', *['parts/%s.be' % n for n in sys.argv[1:]]), end='')
