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
    res = {k: getattr(mod, k) for k in dir(mod) if k.isupper()}
    # the text of an original source fragment (tools/srcapply.py)
    fn = 'notes/src/%s.py' % name
    if os.path.exists(fn) and not os.environ.get('NOSRC'):     # NOSRC=1: plain
        ns = {}
        exec(open(fn, encoding='utf-8').read(), ns)
        res.update({k: ns[k] for k in ('SRC', 'SRCREG', 'SRCNAMES')})
        res['NAMES'] = dict(ns['SRCNAMES'], **res.get('NAMES', {}))
    return res


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


GOST = {i: str(i) for i in range(10)}
GOST.update({0o12: '+', 0o13: '-', 0o14: '/', 0o15: ',', 0o16: '.', 0o17: ' ',
             0o22: '(', 0o23: ')', 0o25: '=', 0o26: ';', 0o31: '*', 0o35: '<',
             0o36: '>', 0o37: ':'})
GOST.update({0o40 + i: c for i, c in enumerate('АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЫЬЭЮЯ')})


def gostconst(b, adj):
    """п'...' for a word of six GOST characters that disbesm6 left octal:
    with a letter next to another text word, or with two letters."""
    end = ''
    if b.count(0o231) == 1:         # the end-of-text marker: п'...0' plus в'231'
        k = b.index(0o231)
        end = "в'231'" if k == 5 else "м%dв'231'" % (8 * (5 - k))
        b = b[:k] + bytes([0]) + b[k + 1:]
    if not all(x in GOST for x in b):
        return None
    n = sum(x >= 0o40 for x in b)
    if n >= 2 or adj and (n == 1 or end):
        return "п'%s'%s" % (''.join(GOST[x] for x in b), end)


def counter(L, i, r):
    """Is register r, loaded in source line i, a loop counter: ЦИКЛ by it
    follows before the register is loaded again."""
    for x in L[i:i + 16]:
        if re.match(r'\S*\tцикл\t.*\(%s\)' % r, x):
            return True
        if re.match(r'\S*\t(уиа\t.*\(%s\)|уи\t%s$|уии\t%s\()' % (r, r, r), x):
            return False
    return False


def t8const(w, adj=False, single=False):
    """A word as a text constant in the БЕМШ code: Т'...' (right-justified)
    or МnТ'...' (shifted left by n bits), None if it is not text: two or
    more characters with a letter, or three or more without; two without a
    letter next to another text (adj); one in a table of characters
    (single: CHARS in the notes)."""
    bs = [(w >> (40 - 8 * k)) & 0xff for k in range(6)]
    lead = next((k for k, b in enumerate(bs) if b), 6)
    trail = next((k for k, b in enumerate(reversed(bs)) if b), 6)
    if lead and trail or lead == 6:
        return None
    body = bs[lead:6 - trail]
    if any(b not in T8 for b in body):
        return None
    letters = any(b >= 0o241 for b in body)
    if not (len(body) >= 3 or len(body) >= 2 and (letters or adj) or single):
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
    # names of the owners in the operands of the source text (SRC)
    inv = {}
    for u in uses:
        for a, n in load_notes(u).get('NAMES', {}).items():
            inv.setdefault(n, (a, u))
    for t in load_notes(part).get('SRC', {}).values():
        if t[0] == 'drop' or t[-2] is None:
            continue
        for x in re.findall(r"(?<![А-ЯA-Z0-9'])[А-ЯA-Z][А-ЯA-Z0-9]*", re.sub(r"'[^']*'", '', t[-2])):
            if x in inv and inv[x][0] not in out:
                out[inv[x][0]] = (x, inv[x][1])
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
    # Э66 with an address inside the part addresses its labelled word
    have = {l.split('\t')[0] for l in L}
    for i, l in enumerate(L):
        m = re.fullmatch(r"\tэ66\t'([0-7]+)'", l)
        if m:
            for c in 'DG':
                if '%s%05o' % (c, int(m.group(1), 8)) in have:
                    L[i] = '\tэ66\t%s%05o' % (c, int(m.group(1), 8))
    # a ПАМ running past 077777 overflows the location counter (warning
    # ПЕРЕПОЛН СЧА): one word is enough, the rest of the image is zero
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        if len(f) >= 3 and f[1] == 'пам' and amap.get(i) and \
                re.fullmatch(r'\d+', f[2]) and \
                int(amap[i], 8) + int(f[2]) >= 0o100000:
            f[2] = '1'
            L[i - 1] = '\t'.join(f)
    # the last ПАМ of a part is not filled up to the end: РВС does it
    fin = next((i for i, l in enumerate(L) if l.startswith('\tФИНИШ')), None)
    if fin:
        f = L[fin - 1].split('\t')
        a0 = amap.get(fin, '')
        if len(f) >= 3 and f[1] == 'пам' and re.fullmatch(r'\d+', f[2]) and \
                re.fullmatch(r'[0-7]{5}', a0) and amap.get(fin + 1) not in names:
            last = max([int(a, 8) for a in names if re.fullmatch(r'[0-7]{5}', a)
                        and a0 <= a < '%05o' % (int(a0, 8) + int(f[2]))] + [int(a0, 8)])
            f[2] = str(last - int(a0, 8) + 1)
            L[fin - 1] = '\t'.join(f)
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
    # a negative loop counter that disbesm6 took for an address of a part
    # in high memory: УИА D7xxxx(Мr) with ЦИКЛ by the same register after it
    for i, l in enumerate(L, 1):
        m = re.fullmatch(r"(\S*\tуиа\t)[GD](7[0-7]{4})\((М\d+)\)", l)
        if m and counter(L, i, m.group(3)):
            L[i - 1] = '%s%d(%s)' % (m.group(1), int(m.group(2), 8) - 0o100000, m.group(3))
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
        # a negative loop counter: ЦИКЛ by the same register follows
        if t >= 0o70000 and counter(L, i, r):
            continue
        exact[i] = ('%05o' % t, r)
        if exact[i][0] not in names and exact[i][0] not in labs0:
            data = not tl or L[tl - 1].split('\t')[1] in ('конд', 'конк', 'пам', 'текст')
            names[exact[i][0]] = ('D' if data else 'G') + exact[i][0]
    # the parameter in the right half after ПВЛ (as in ПВЛ СООБЩ(М16): the
    # length in bits 20-16 and the address of the text) is written as
    # ДК код,МЕТКА; the right half after ПБ in the left half is never
    # executed: an address there is КОНК A(МЕТКА), a second ПБ stays ПБ
    msg = {}; keep = {}; kka = {}
    byname = {n: a for a, n in names.items()}
    fmt = {byname.get(x, x) for x in notes.get('FMTPAR', [])}
    byname = {n: a for a, n in names.items()}
    fmt = {byname.get(x, x) for x in notes.get('FMTPAR', [])}
    sa = [a for a, n in list(ext.items()) + list(names.items()) if n == 'СООБЩ']
    call = re.compile(r"\S*\tпвл\t(?:'%o'|[GD]%s)\(М16\)" % (int(sa[0], 8), sa[0])) if sa else None
    img = open('parts/%s.bin' % name, 'rb').read()
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        a = amap.get(i, '')
        if i < 2 or len(f) < 3 or f[0] or f[1] != 'конк' or not a.endswith('п'):
            continue
        pf = L[i - 2].split('\t')
        k = (int(a[:5], 8) - plo) * 6
        h = int.from_bytes(img[k + 3:k + 6], 'big')
        t, c, r = h & 0o77777, (h >> 15) & 0o37, h >> 20
        own = plo <= t < phi and not (plo == 0 and t < 0o100)
        ta = '%05o' % t
        if len(pf) > 1 and pf[1] == 'пб':
            if r == 0 and c in (0, 0o30) and (own or ta in ext):
                kka[i] = (ta, 'пб\t%s' if c else 'конк\tA(%s)')
                if own and ta not in names and ta not in labs0:
                    names[ta] = ('G' if c else 'D') + ta
            continue
        if len(pf) < 2 or pf[1] != 'пвл':
            continue
        m = re.fullmatch(r"(?:[GD]([0-7]{5})|'([0-7]+)')\(М\d+\)", pf[2]) if len(pf) > 2 else None
        if m and '%05o' % int(m.group(1) or m.group(2), 8) in fmt:
            w, o = (h >> 12) & 0o377, h & 0o7777    # a format, not an address
            keep[i] = '\tкк\t%s,%s%s' % (w if w < 0o100 else "'%o'" % w,
                                         o if o < 8 else "'%o'" % o, '(%d)' % r if r else '')
            continue
        m = re.fullmatch(r"(?:[GD]([0-7]{5})|'([0-7]+)')\(М\d+\)", pf[2]) if len(pf) > 2 else None
        if m and '%05o' % int(m.group(1) or m.group(2), 8) in fmt:
            w, o = (h >> 12) & 0o377, h & 0o7777    # a format, not an address
            keep[i] = '\tкк\t%s,%s%s' % (w if w < 0o100 else "'%o'" % w,
                                         o if o < 8 else "'%o'" % o, '(%d)' % r if r else '')
            continue
        if r:                       # an offset by a register
            o = t - 0o100000 if t >= 0o70000 else t
            keep[i] = '\tдк\t%d,%s(М%o)' % (c, (o or '') if abs(o) < 0o100 else "'%o'" % t, r)
        elif own or call and call.fullmatch(L[i - 2]) and ta in ext:
            msg[i] = (c, ta)
            if own and ta not in names and ta not in labs0:
                names[ta] = 'D' + ta
        else:                       # a number
            keep[i] = '\tдк\t%d,%s' % (c, t if t < 8 else "'%o'" % t)
    # half-words of information words that disbesm6 shows as КК: an address
    # of this part is КОНК A(МЕТКА), an offset by a register stays a number
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        if len(f) < 3 or f[1] != 'кк':
            continue
        m = re.fullmatch(r"7,'([0-7]{1,4})'", f[2])
        if m and plo <= 0o70000 + int(m.group(1), 8) < phi:
            ta = '%05o' % (0o70000 + int(m.group(1), 8))
            kka[i] = (ta, 'конк\tA(%s)')
            if ta not in names and ta not in labs0:
                names[ta] = 'D' + ta
        m = re.fullmatch(r"0,'([0-7]+)'(\(М\d+\))", f[2])
        if m:
            f[2] = '0,%d%s' % (int(m.group(1), 8), m.group(2))
            L[i - 1] = '\t'.join(f)
    # a whole word "address of this part / filler" is КОНК A(МЕТКА): BEMSH
    # pads it with МОДА itself before the labelled word that follows
    kword = {}
    for i, l in enumerate(L, 1):
        f = l.split('\t')
        a = amap.get(i, '')
        if len(f) < 3 or f[1] != 'конд' or not re.fullmatch(r'[0-7]{5}', a) \
                or not plo <= int(a, 8) < phi:
            continue
        k = (int(a, 8) - plo) * 6
        w = int.from_bytes(img[k:k + 6], 'big')
        t = w >> 24
        if w & 0o77777777 != 0o02200000 or not plo <= t < phi or plo == 0 and t < 0o100:
            continue
        na = '%05o' % (int(a, 8) + 1)
        if i < len(L) and not L[i].split('\t')[0] and na not in names and byaddr.get(na) == i + 1:
            names[na] = ('D' if L[i].split('\t')[1] in ('конд', 'конк', 'пам', 'текст') else 'G') + na
        kword[i] = ('%05o' % t, i < len(L) and (bool(L[i].split('\t')[0]) or na in names))
        if kword[i][0] not in names and kword[i][0] not in labs0:
            names[kword[i][0]] = 'D' + kword[i][0]
    # explicit fillers kept by stripmoda: BEMSH pads a word itself before a
    # labelled line and before ПВ/extracodes, so the line after a filler in
    # a right half gets a label (its address has a name then) and that
    # filler is dropped; only fillers that nothing implies stay as МОДА
    dropfill = set(); leftfill = set(); addlab = {}
    i = 1
    while i <= len(L):
        if not L[i - 1].startswith('\tмода\t,'):
            i += 1
            continue
        j = i
        while j <= len(L) and L[j - 1].startswith('\tмода\t,'):
            j += 1
        fills = list(range(i, j))     # filler lines, the next line is j
        i = j
        if j > len(L) or any(not amap.get(k) for k in fills):
            continue
        f = L[j - 1].split('\t')
        if len(f) < 2 or f[1] == 'ФИНИШ':
            continue
        aj = amap.get(j, '')
        ronly = f[1] == 'пв' or f[1].startswith('Э')
        if ronly and aj.endswith('п') and not amap[fills[-1]].endswith('п'):
            dropfill.add(fills.pop())             # the left half before ПВ
        elif fills and amap[fills[-1]].endswith('п') and re.fullmatch(r'[0-7]{5}', aj):
            if not f[0] and aj not in names:    # the next line starts a word
                names[aj] = ('D' if f[1] in ('конд', 'конк', 'пам', 'текст') else 'G') + aj
            dropfill.add(fills.pop())
        if fills and amap[fills[0]].endswith('п'):  # padding after a left half
            nl = fills[1] if len(fills) > 1 else j  # the line that starts the word
            a = amap[nl][:5] if nl != j else aj[:5]
            if nl != j or not L[j - 1].split('\t')[0]:
                if a not in names:
                    names[a] = 'G' + a
                addlab[nl] = a
            dropfill.add(fills.pop(0))
        leftfill.update(fills)
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
    # source text for whole lines (SRC): a macro call replaces its expansion
    # unless a line inside it has to carry a label
    extinv = {n: a for a, n in ext.items()}
    srcsub = {}
    SRC = notes.get('SRC', {})
    order = [(i, amap.get(i)) for i in range(1, len(L) + 1)
             if amap.get(i) and byaddr.get(amap.get(i)) == i]
    for k, (i, a) in enumerate(order):
        t = SRC.get(a)
        if not t or t[0] == 'drop':
            continue
        if t[0] == 'line':
            srcsub[i] = t
            continue
        grp = []
        for i2, a2 in order[k + 1:]:
            if SRC.get(a2) != ('drop',):
                break
            grp.append((i2, a2))
        if any(L[i2 - 1].split('\t')[0] or a2 in names for i2, a2 in grp):
            continue
        srcsub[i] = t
        for i2, a2 in grp:
            srcsub[i2] = ('drop',)
    errtab = {}; errskip = set()
    if notes.get('ERRTAB'):
        e0, e1 = [int(x, 8) for x in notes['ERRTAB']]
        for x in range(e0, e1, 2):
            k = (x - plo) * 6
            errtab['%05o' % x] = (int.from_bytes(image[k:k + 6], 'big'),
                                  int.from_bytes(image[k + 6:k + 12], 'big'))
    # CHARS = ['ааааа-ббббб', 'ааааа', ...]: tables of single characters
    chars = [tuple((x.split('-') * 2)[:2]) for x in notes.get('CHARS', [])]
    using = None                    # (register, base) of the УПОТР in effect
    out = []
    for i, l in enumerate(L, 1):
        a = amap.get(i)
        first = a is not None and byaddr.get(a) == i
        if i == 3 and 'TOP' in notes:
            out.extend(notes['TOP'].strip('\n').split('\n'))
        if i == 3 and notes.get('SRCREG'):
            out.append('* ИМЕНА РЕГИСТРОВ ИЗ ИСХОДНОГО ТЕКСТА')
            out.extend('%s\tэкв\t%d' % x for x in sorted(notes['SRCREG'].items(), key=lambda x: (x[1], x[0])))
        if first and a in notes.get('BLOCK', {}):
            out.extend(notes['BLOCK'][a].strip('\n').split('\n'))
        if first and a in newlab:
            if not l.startswith('\t') or a.endswith('п'):
                sys.exit('%s: cannot label %s: %s' % (name, a, l))
            k = len(out) - 1            # over the comment block, if any
            while k >= 0 and out[k].startswith('*'):
                k -= 1
            if k >= 0 and out[k].startswith('\tмода\t,'):
                del out[k]
            if l.startswith('\tФИНИШ'):     # zeros up to the end: РВС fills them
                out.append('%s\tпам\t1' % newlab[a])
            else:
                l = newlab[a] + l
        if l.startswith('\tФИНИШ'):
            for a2, n in sorted(ekv_own.items()):
                out.append("%s\tэкв\t'%s'" % (n, a2))
        # ERRTAB = ('ааааа', 'ббббб'): messages of two words; bits 48 and 40
        # of the first word hold the severity instead of the top bits of
        # the first two characters. One ТЕКСТ for a message; with a
        # severity below 4 the first word is КОНД with the bits taken off.
        if first and a in errskip:
            continue
        if first and a in errtab:
            w1, w2 = errtab[a]
            b12 = [(w >> (40 - 8 * k)) & 0xff for w in (w1 | 0o4010000000000000, w2) for k in range(6)]
            n2 = '%05o' % (int(a, 8) + 1)
            two = not L[byaddr[n2] - 1].split('\t')[0] and n2 not in names
            if all(x in T8 for x in b12):
                tx = ''.join(T8[x] for x in b12)
                if any(x in LATONLY for x in b12) and not any(x >= 0o300 for x in b12):
                    tx = tx.translate(str.maketrans('АВСЕНКМОРТХУ', 'ABCEHKMOPTXY'))
                cut = lambda t: (t.rstrip(' ') or ' ')
                h1, h2 = tx[:len(tx) - len(''.join(T8[x] for x in b12[6:]))], ''.join(T8[x] for x in b12[6:])
                h1, h2 = ''.join(T8[x] for x in b12[:6]), ''.join(T8[x] for x in b12[6:])
                sev = ('' if w1 >> 47 & 1 else "м47в'1'") + ('' if w1 >> 39 & 1 else "м39в'1'")
                lab0 = l.split('\t')[0]
                if not sev and two:
                    t12 = (h1 + h2).rstrip(' ')
                    out.append("%s\tтекст\tт'%s'" % (lab0, t12 + ' ' * max(7 - len((h1 + h2).rstrip(' ').replace("''", "'")), 0)))
                    errskip.add(n2)
                    continue
                out.append("%s\t%s\tт'%s'%s" % (lab0, 'конд' if sev else 'текст',
                                                  h1 if sev else cut(h1), sev))
                if two:
                    out.append("\tтекст\tт'%s'" % cut(h2))
                    errskip.add(n2)
                continue
        f = l.split('\t')
        if first and len(f) >= 3 and f[1] == 'конд' and not f[2].startswith('A(') \
                and re.fullmatch(r'[0-7]{5}', a) and plo <= int(a, 8) < phi:
            k = (int(a, 8) - plo) * 6
            def strict(j):          # is source line j a text word by itself
                b2 = amap.get(j, '')
                g = L[j - 1].split('\t') if 0 < j <= len(L) else []
                if len(g) < 3 or g[1] != 'конд' or not re.fullmatch(r'[0-7]{5}', b2):
                    return False
                k2 = (int(b2, 8) - plo) * 6
                return bool(t8const(int.from_bytes(image[k2:k2 + 6], 'big')))
            t = t8const(int.from_bytes(image[k:k + 6], 'big'),
                        strict(i - 1) or strict(i + 1),
                        any(lo <= a <= hi for lo, hi in chars))
            if a in notes.get('REALS', {}):         # КОНД Е'число'
                t = "е'%s'" % notes['REALS'][a]
            if not t and f[2].startswith("в'"):
                t = gostconst(image[k:k + 6], any(
                    "\tконд\tп'" in L[j] for j in (i - 2, i) if 0 <= j < len(L)))
            if t:
                f[2] = t
                l = '\t'.join(f)
        if i in dropfill:
            continue
        if i in leftfill:
            l = '\tмода\t'
        if i in addlab and l.startswith('\t'):
            l = final(addlab[i]) + l
        if i in kword:
            l = '%s\tконк\tA(%s)' % (l.split('\t')[0], final(kword[i][0]))
            if not kword[i][1]:
                l += '\n\tмода\t,ДО ГРАНИЦЫ СЛОВА, КАК В ОРИГИНАЛЕ'
        if i in kka:
            ta = kka[i][0]
            own = plo <= int(ta, 8) < phi
            if not own:
                used_ext[ta] = ext[ta]
            l = l.split('\t')[0] + '\t' + kka[i][1] % (final(ta) if own else ext[ta])
        if i in msg:
            ta = msg[i][1]
            own = plo <= int(ta, 8) < phi
            if not own:
                used_ext[ta] = ext[ta]
            l = '\tдк\t%d,%s' % (msg[i][0], final(ta) if own else ext[ta])
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
        # МЕТКА+N that hits a named word is that name
        l = re.sub(r'(?<![А-Я0-9A-Z])[GD]([0-7]{5})\+(\d+)(?!\d)',
                   lambda m: names.get('%05o' % (int(m.group(1), 8) + int(m.group(2))),
                                       m.group(0)), l)
        l = subst(l)
        if i in keep:               # a number stays a number
            l = keep[i]
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
        st = srcsub.get(i)
        if st and st[0] == 'drop':
            continue
        if st:
            f = l.split('\t')
            if st[0] == 'macro':
                f = [f[0], st[1], st[2]]
            elif st[1] is not None:
                f = f[:2] + [st[1]]
            else:
                f = f[:3] if len(f) > 2 and not f[2].startswith(',') else f[:2] + ['']
            cm = st[-1] or (l.split('\t')[3] if len(l.split('\t')) > 3 and st[0] == 'line' else '')
            for x in re.findall(r"(?<![А-ЯA-Z0-9'])[А-ЯA-Z][А-ЯA-Z0-9]*", re.sub(r"'[^']*'", '', f[2])):
                if x in extinv:
                    used_ext[extinv[x]] = x
            l = '\t'.join(f) + (('\t' if f[2] else ',') + cm if cm else '')
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
    # consecutive whole words of text are one ТЕКСТ (up to 6 words in a line)
    def whole(l):
        m = re.fullmatch(r"(\S*)\tконд\t([пт])'(.*)'", l)
        if m and len(m.group(3).replace("''", "'")) == 6:
            return m.groups()
    merged = []; grp = None         # grp: [label, kind, text, words]
    def flush():
        if grp:
            # ТЕКСТ pads the last word with spaces: trailing ones are dropped
            t = grp[2].rstrip(' ')
            keep = 6 * (grp[3] - 1) + 1 - len(t.replace("''", "'"))
            t += ' ' * max(keep, 0)
            if grp[3] == 1 and t == grp[2]:
                merged.append("%s\tконд\t%s'%s'" % (grp[0], grp[1], t))
            else:
                merged.append("%s\tтекст\t%s'%s'" % (grp[0], grp[1], t))
    for l in out:
        w = whole(l)
        if w and grp and not w[0] and w[1] == grp[1] and grp[3] < 6:
            grp[2] += w[2]; grp[3] += 1
            continue
        flush()
        grp = [w[0], w[1], w[2], 1] if w else None
        if not w:
            merged.append(l)
    flush()
    out = merged
    # equal КОНД words in a row: КОНД (count)value
    rep = []
    for l in out:
        m = re.fullmatch(r"(\S*)\tконд\t((?:м\d+)?[впт]'[^\t]*')", l)
        p = re.fullmatch(r"(\S*)\tконд\t(?:\((\d+)\))?((?:м\d+)?[впт]'[^\t]*')", rep[-1]) if rep and m else None
        if m and p and not m.group(1) and p.group(3) == m.group(2):
            rep[-1] = '%s\tконд\t(%d)%s' % (p.group(1), int(p.group(2) or 1) + 1, m.group(2))
        else:
            rep.append(l)
    out = rep
    text = '\n'.join(out)
    open('parts/%s.be' % name, 'w', encoding='utf-8').write(text)
    insplit = {'%05o' % x for v in split.values() for x, n in v}
    for k in list(notes.get('BLOCK', {})) + list(notes.get('INLINE', {})) + list(newlab):
        if k not in byaddr and k not in insplit:
            print('%s: no source line at %s' % (name, k), file=sys.stderr)
    for f in (plain, plain + '.lst'):
        os.remove(f)


# all sources first, then translate them and link all parts in one РВС run
if __name__ == '__main__':
    for n in sys.argv[1:]:
        make(n)
    print(run('tools/reasm.pl', *['parts/%s.be' % n for n in sys.argv[1:]]), end='')
