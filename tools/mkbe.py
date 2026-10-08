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
#   USES   = ['mon0', 'mred24']         parts whose NAMES may be referenced:
#            literal addresses 'ааааа' of those names become the names,
#            declared with ЭКВ at the end;
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
    ext = {}
    for u in notes.get('USES', []):
        ext.update(load_notes(u).get('NAMES', {}))
    plain = 'parts/%s.plain.be' % name
    run('tools/stripmoda.py', 'parts/%s.dis' % name, plain)
    out = run('tools/reasm.pl', plain)
    if 'matches' not in out:
        sys.exit('%s: plain source does not reassemble\n%s' % (name, out))
    amap = addrmap(plain + '.lst')
    byaddr = {}
    for n, a in sorted(amap.items()):
        byaddr.setdefault(a, n)
    L = open(plain, encoding='utf-8').read().split('\n')
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
            if a in ext and a not in names:
                used_ext[a] = ext[a]
                return ext[a]
            if a in ekv_own:
                return ekv_own[a]
            return m.group(0)
        f = l.split('\t')
        if len(f) >= 3:
            f[2] = re.sub(r"'([0-7]{4,5})'", r2, f[2])
            l = '\t'.join(f)
        return l

    out = []
    for i, l in enumerate(L, 1):
        a = amap.get(i)
        first = a is not None and byaddr.get(a) == i
        if i == 5 and 'TOP' in notes:
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
            for a2, n in sorted(used_ext.items()):
                out.append("%s\tэкв\t'%s'" % (n, a2))
        l = subst(l)
        if first and a in notes.get('INLINE', {}):
            f = l.split('\t')
            if len(f) >= 3 and f[2]:
                l = l + '\t' + notes['INLINE'][a]
            else:
                l = '\t'.join(f[:2]) + '\t,' + notes['INLINE'][a]
        out.append(l)
    # second pass for ext names first seen after ФИНИШ was written: redo once
    text = '\n'.join(out)
    missing = [a for a in used_ext if "%s\tэкв" % used_ext[a] not in text]
    if missing:
        text = text.replace('\n\tФИНИШ', ''.join("\n%s\tэкв\t'%s'" % (used_ext[a], a)
                                                  for a in sorted(missing)) + '\n\tФИНИШ')
    open('parts/%s.be' % name, 'w', encoding='utf-8').write(text)
    for k in list(notes.get('BLOCK', {})) + list(notes.get('INLINE', {})) + list(newlab):
        if k not in byaddr:
            print('%s: no source line at %s' % (name, k), file=sys.stderr)
    res = run('tools/reasm.pl', 'parts/%s.be' % name).strip().split('\n')[-1]
    print('%s: %s' % (name, res))
    for f in (plain, plain + '.lst'):
        os.remove(f)


for n in sys.argv[1:]:
    make(n)
