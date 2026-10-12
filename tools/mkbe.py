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
#            a label, a ПАМ block is split at an address inside it (an ЭКВ
#            is left only for an address without a source line of its own);
#   USES   = ['mon0', 'mred24']         parts in memory together with this
#            one: a literal address 'ааааа' inside one of them becomes
#            its name (NAMES there, else its label Gааааа/Dааааа, else a
#            new label Dааааа), declared after the header with
#            МОДУЛЬ ВНЕШ ИМЯ,...; the owner lists it in ВХОД ИМЯ,...
#            (ВЭКВ from an external is not resolved by РВС: it takes such
#            a pair for a common area). ВНЕШ, ВХОД and М come from macros.be.
#            Modules are linked together by tools/reasm.pl;
#   BASEREG = {'М3': '70546', 'М14': None}   base registers of position-
#            independent code: the value is the base at the start of the
#            part (None - not set); УИА ааааа(Мr) with an address of the
#            part sets it from there on (in source order), another УИА,
#            СЛИА, УИ or УИИ of Мr drops it. An operand 'смещение'(Мr) whose
#            base + offset is inside the part becomes the plain label under
#            УПОТР БАЗА(Мr), and the load of the base - УИА БАЗА(Мr). УПОТР
#            is switched off (ОТМЕН (Мr)) before a command that addresses
#            a label of the part directly; missing labels Dааааа are added;
#   A КОНД word that is text in the 8-bit code of БЕМШ is written as
#   КОНД Т'...' (see t8const).
#   NOTADDR = ['76001', ...]            literal values that are numbers (loop
#            counters), not addresses in a part of USES: left as they are;
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


# operations whose register field is a destination, not an index (the
# flag in the assembler's table ТСВОП): no base register for them
REGDEST = {'уиа', 'слиа', 'пв', 'пвл', 'пво', 'цикл', 'уии', 'сли', 'пио',
           'пино', 'дк', 'дкб', 'кк', 'ккб'}
JUMPS = {'пб', 'по', 'пе', 'мода', 'мод'}
# not commands: УПОТР does not touch them
NOTCMD = {'конд', 'конк', 'текст', 'пам', 'экв', 'внеш', 'вход', 'старт',
          'финиш', 'м', 'употр', 'отмен', 'адрес', 'литер', 'внешн', 'входн'}


# The 8-bit text code of БЕМШ (КОНД Т'...'), found by translating a
# constant for every character; letters common to both alphabets are
# given as Russian ones.
T8 = {0o100: ' ', 0o101: '!', 0o102: '"', 0o104: '$', 0o105: '%', 0o106: '&',
      0o107: "''", 0o110: '(', 0o111: ')', 0o112: '*', 0o113: '+', 0o114: ',',
      0o115: '-', 0o116: '.', 0o117: '/', 0o132: ':', 0o133: ';', 0o134: '<',
      0o135: '=', 0o136: '>', 0o240: '@', 0o273: '[', 0o275: ']', 0o277: '_'}
T8.update({0o120 + i: str(i) for i in range(10)})
T8.update(zip(range(0o241, 0o273), 'АВСDЕFGНIJКLМNОРQRSТUVWХУZ'))
T8.update({0o300: 'Ю', 0o302: 'Б', 0o303: 'Ц', 0o304: 'Д', 0o306: 'Ф',
           0o307: 'Г', 0o311: 'И', 0o312: 'Й', 0o314: 'Л', 0o320: 'П',
           0o321: 'Я', 0o326: 'Ж', 0o330: 'Ь', 0o331: 'Ы', 0o332: 'З',
           0o333: 'Ш', 0o334: 'Э', 0o335: 'Щ', 0o336: 'Ч'})


LATONLY = {b for b, c in T8.items() if c in 'DFGIJLNQRSUVWZ'}


def t8const(w):
    """A word as a text constant in the БЕМШ code: Т'...' (right-justified)
    or МnТ'...' (shifted left by n bits), None if it is not text: two or
    more characters with a letter, or four or more without."""
    bs = [(w >> (40 - 8 * k)) & 0xff for k in range(6)]
    lead = next((k for k, b in enumerate(bs) if b), 6)
    trail = next((k for k, b in enumerate(reversed(bs)) if b), 6)
    if lead and trail or lead == 6:
        return None
    body = bs[lead:6 - trail]
    if any(b not in T8 for b in body):
        return None
    letters = any(b >= 0o241 for b in body)
    if not (len(body) >= 4 or len(body) >= 2 and letters):
        return None
    text = ''.join(T8[b] for b in body)
    # a word with Latin-only letters and no Russian-only ones is Latin
    if any(b in LATONLY for b in body) and not any(b >= 0o300 for b in body):
        text = text.translate(str.maketrans('АВСЕНКМОРТХУ', 'ABCEHKMOPTXY'))
    return "%sт'%s'" % ('м%d' % (8 * trail) if trail else '', text)


def fieldmap(lst):
    """Source line number -> value of the address field of the instruction
    (None for a short address with the extension bit)."""
    res = {}
    for l in open(lst, encoding='utf-8', errors='replace'):
        m = re.search(r' (\d{4})  (\d{4}) ', l[31:])
        c = re.fullmatch(r'(\d\d) (\d{2,3}) +(\d{4,5})', l[31:49].strip()) if m else None
        if c and not (len(c.group(2)) == 3 and c.group(2)[0] != '0'):
            res[int(m.group(2))] = int(c.group(3), 8)
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
    notaddr = {int(a, 8) for a in load_notes(part).get('NOTADDR', [])}
    for l in open('parts/%s.dis' % part, encoding='utf-8'):
        f = l.rstrip('\n').split('\t')
        if len(f) < 3:
            continue
        for m in re.finditer(LITADDR, f[2]):
            a = int(m.group(1), 8)
            if lo <= a < hi or a in notaddr:
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
    # operands relative to a base register (BASEREG)
    based = {}                      # source line -> (target, base, 'Мr')
    setbase = {}                    # source line of УИА -> (base, 'Мr')
    fmap = {}
    if notes.get('BASEREG'):
        fmap = fieldmap(plain + '.lst')
        plo, phi = ranges()[name]
        cur = {r: (int(b, 8) if b else None) for r, b in notes['BASEREG'].items()}
        for i, l in enumerate(L, 1):
            f = l.split('\t')
            m = re.fullmatch(r'(.*)\((М\d+)\)', f[2]) if len(f) >= 3 else None
            if len(f) >= 3 and f[1] == 'уи' and f[2] in cur:
                cur[f[2]] = None
            if len(f) >= 3 and f[1] == 'уии' and f[2].split('(')[0] in cur:
                cur[f[2].split('(')[0]] = None      # Мr := another register
                continue
            if not m or m.group(2) not in cur or \
                    f[1] in ('кк', 'ккб', 'дк', 'дкб', 'конк', 'конд', 'текст'):
                continue
            r, v = m.group(2), fmap.get(i)
            if f[1] in ('уиа', 'слиа'):
                cur[r] = v if f[1] == 'уиа' and v is not None and plo <= v < phi else None
                if cur[r] is not None:
                    setbase[i] = ('%05o' % v, r)
            elif f[1] in REGDEST:
                pass                # the register is not an index here
            elif cur[r] is not None and m.group(1) and v and v < 0o40000 and \
                    plo <= cur[r] + v < phi:
                based[i] = ('%05o' % (cur[r] + v), '%05o' % cur[r], r)
        labs0 = dis_labels(name)
        for t, b, r in list(based.values()) + [(t, t, r) for t, r in setbase.values()]:
            for a in (t, b):
                if a not in names and a not in labs0 and int(a, 8) != (plo or 1):
                    names[a] = 'D' + a
    # МЕТКА+N(Мr) -> the label of the exact word: the start of a table, or
    # the address loaded by УИА. Left as it is when the index is negative
    # (the register is loaded with a negative number just before, or
    # counted by ЦИКЛ just after)
    exact = {}                      # source line -> (target, 'Мr')
    literal = {}                    # source line -> operand
    plo, phi = ranges()[name]
    labs0 = dis_labels(name)
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        m = re.fullmatch(r'[GD]([0-7]{5})([+-]\d+)?\((М\d+)\)', f[2]) if len(f) >= 3 else None
        if not m or i in based or i in setbase:
            continue
        t, r = int(m.group(1), 8) + int(m.group(2) or 0), m.group(3)
        prev = L[i - 2].split('\t') if i >= 2 else []
        tl = byaddr.get('%05o' % t)
        # image at 0: an "address" of a command used with an index register
        # to read or write is an offset from the register
        incode = plo == 0 and f[1] not in REGDEST and f[1] not in JUMPS and tl and \
            L[tl - 1].split('\t')[1] not in ('конд', 'конк', 'пам', 'текст')
        if incode or m.group(2) and (not plo <= t < phi or len(prev) >= 3 and
                                     prev[1] == 'мода' and prev[2].startswith("'")):
            literal[i] = "'%o'(%s)" % (t, r)    # a number, not an address
            continue
        if not m.group(2):
            continue
        if f[1] not in REGDEST:
            near = L[max(0, i - 16):i - 1]
            after = L[i:i + 16]
            if any(re.match(r"\S*\tуиа\t(-\d+|'7[0-7]{4}')\(%s\)" % r, x) for x in near) or \
                    any(re.match(r'\S*\tцикл\t.*\(%s\)' % r, x) for x in after):
                continue
        exact[i] = ('%05o' % t, r)
        if exact[i][0] not in names and exact[i][0] not in labs0 and t != (plo or 1):
            names[exact[i][0]] = 'D' + exact[i][0]
    # УИА 'адрес'(Мr) with an address inside this part is written with
    # the label of that word
    jreg = {m.group(1) for l in L for m in [re.match(r'\S*\tпб\t\S*\((М\d+)\)', l)] if m}
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        m = re.fullmatch(r"(?:'([0-7]+)'|(\d+))\((М\d+)\)", f[2]) if len(f) >= 3 and f[1] == 'уиа' else None
        if not m or i in setbase:
            continue
        t, r = int(m.group(1), 8) if m.group(1) else int(m.group(2)), m.group(3)
        tl = byaddr.get('%05o' % t)
        nxt = [x.split('\t')[1] for x in L[i:i + 2] if len(x.split('\t')) >= 2]
        # (an image at 0: small numbers look like addresses, so there a
        # jump through the register is required)
        if not plo <= t < phi or plo == 0 and not (t >= 0o100 and (r in jreg or 'пб' in nxt)):
            continue
        exact[i] = ('%05o' % t, r)
        if exact[i][0] not in names and exact[i][0] not in labs0:
            data = not tl or L[tl - 1].split('\t')[1] in ('конд', 'конк', 'пам', 'текст')
            names[exact[i][0]] = ('D' if data else 'G') + exact[i][0]
    # labels of this part by address
    lab = {}
    for i, l in enumerate(L, 1):
        m = re.match(r'^([GD]([0-7]{5}))\t', l)
        if m:
            lab[m.group(2)] = m.group(1)
    rename = {lab[a]: n for a, n in names.items() if a in lab}
    newlab = {a: n for a, n in names.items() if a not in lab and a in byaddr}
    ekv_own = {a: n for a, n in names.items() if a not in lab and a not in byaddr}
    # a name inside a ПАМ block splits the block instead of an ЭКВ
    split = {}                      # source line -> [(address, name), ...]
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        if len(f) >= 3 and f[1] == 'пам' and re.fullmatch(r'\d+', f[2]) and \
                re.fullmatch(r'[0-7]{5}', amap.get(i, '')):
            a0 = int(amap[i], 8)
            inside = sorted((int(a, 8), n) for a, n in ekv_own.items()
                            if re.fullmatch(r'[0-7]{5}', a) and
                            a0 < int(a, 8) < a0 + int(f[2]))
            if inside:
                split[i] = inside
                for a, n in inside:
                    del ekv_own['%05o' % a]
    used_ext = {}

    def final(a):                   # the label of an address of this part
        return names.get(a) or lab.get(a) or mods[name]

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

    def direct(l):
        """A command that addresses a label of this part without an index
        register: УПОТР would give it a base."""
        f = l.split('\t')
        if len(f) < 3 or f[1] in REGDEST or f[1] in NOTCMD or '(М' in f[2] \
                or f[1].startswith('*'):
            return False
        opnd = f[2].split(',')[0]   # after a comma - a comment
        syms = set(re.findall(r"(?<![А-ЯA-Z0-9'])[А-ЯA-Z][А-ЯA-Z0-9]*", opnd))
        syms = {x for x in syms if not re.fullmatch(r'М\d+', x)}
        return bool(syms - set(ext.values())) or opnd.startswith('=')

    plo, phi = ranges()[name]
    image = open('parts/%s.bin' % name, 'rb').read()
    using = None                    # (register, base) of the УПОТР in effect
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
        f = l.split('\t')
        if first and len(f) >= 3 and f[1] == 'конд' and not f[2].startswith('A(') \
                and re.fullmatch(r'[0-7]{5}', a) and plo <= int(a, 8) < phi:
            k = (int(a, 8) - plo) * 6
            t = t8const(int.from_bytes(image[k:k + 6], 'big'))
            if t:
                f[2] = t
                l = '\t'.join(f)
        if i in based:
            t, b, r = based[i]
            if using != (r, b):
                if using and using[0] != r:     # УПОТР replaces the base
                    out.append('\tотмен\t(%s)' % using[0])
                out.append('\tупотр\t%s(%s)' % (final(b), r))
                using = (r, b)
            f = l.split('\t')
            f[2] = final(t)
            l = '\t'.join(f)
        elif i in literal:
            f = l.split('\t')
            f[2] = literal[i]
            l = '\t'.join(f)
        elif i in exact:
            f = l.split('\t')
            f[2] = '%s(%s)' % (final(exact[i][0]), exact[i][1])
            l = '\t'.join(f)
        elif i in setbase:
            f = l.split('\t')
            f[2] = '%s(%s)' % (final(setbase[i][0]), setbase[i][1])
            l = '\t'.join(f)
        l = subst(l)
        if i in literal:            # a number stays a number
            f = l.split('\t')
            f[2] = literal[i]
            l = '\t'.join(f)
        if using and i not in based and direct(l):
            out.append('\tотмен\t(%s)' % using[0])
            using = None
        if first and a in notes.get('INLINE', {}):
            f = l.split('\t')
            if len(f) >= 3 and f[2]:
                l = l + '\t' + notes['INLINE'][a]
            else:
                l = '\t'.join(f[:2]) + '\t,' + notes['INLINE'][a]
        if i in split:
            f = l.split('\t')
            a0, total = int(a, 8), int(f[2])
            bounds = [x for x, n in split[i]] + [a0 + total]
            f[2] = str(bounds[0] - a0)
            out.append('\t'.join(f))
            for k, (x, n) in enumerate(split[i]):
                blk = notes.get('BLOCK', {}).get('%05o' % x)
                if blk:
                    out.extend(blk.strip('\n').split('\n'))
                l = '%s\tпам\t%d' % (n, bounds[k + 1] - x)
                if '%05o' % x in notes.get('INLINE', {}):
                    l += '\t' + notes['INLINE']['%05o' % x]
                out.append(l)
            continue
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
    insplit = {'%05o' % x for v in split.values() for x, n in v}
    for k in list(notes.get('BLOCK', {})) + list(notes.get('INLINE', {})) + list(newlab):
        if k not in byaddr and k not in insplit:
            print('%s: no source line at %s' % (name, k), file=sys.stderr)
    for f in (plain, plain + '.lst'):
        os.remove(f)


# all sources first, then translate them and link all parts in one РВС run
for n in sys.argv[1:]:
    make(n)
print(run('tools/reasm.pl', *['parts/%s.be' % n for n in sys.argv[1:]]), end='')
