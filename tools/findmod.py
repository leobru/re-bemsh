#!/usr/bin/env python3
# Find the object modules written by ЗОНМОД on disk volumes.
# Usage: tools/findmod.py [-v] VOLUME|FILE...
#   VOLUME - a disk number (dumped with "besmtool dump"), FILE - a dump
#   (6 bytes per word, 1024 words per zone). For every zone that starts a
#   module prints: zone, zones taken, name, СТАРТ, ДИАП ЗАГР, length,
#   chunks of code/ВХОД/ВНЕШ/ЗОНМЕТ, and the warnings (-v - also the
#   zones that pass the header test but fail the chunk test). The code
#   chunks must go up in address; a drop at a zone boundary means the
#   rest of the module was overwritten ("обрыв").
# Module format (README, "Заголовок модуля"; disbesm6 -r): 12-word chunks,
# 85 to a zone (the last 4 words of a zone are not used). Chunk 0 is the
# header: 1, name, СТАРТ, ДИАП ЗАГР low, high, code chunks, length,
# (chunks << 24 | count) of ВХОД, ВНЕШ and ЗОНМЕТ; words 10-11 are left
# over in the buffer. A code chunk is
# 20 half-words in words 0-9; words 10-11 hold 4 flags per half-word and
# the address of the first half-word ((w10 & 0177) << 8 | w11 & 0377).
# ВХОД/ВНЕШ/ЗОНМЕТ: 6 pairs per chunk.
import os, subprocess, sys, tempfile

def words(src):
    if os.path.exists(src):
        d = open(src, 'rb').read()
    else:
        with tempfile.NamedTemporaryFile(suffix='.bin') as t:
            subprocess.run(['besmtool', 'dump', src, '--to-file=' + t.name],
                           check=True, stdout=subprocess.DEVNULL)
            d = open(t.name, 'rb').read()
    return [int.from_bytes(d[i:i + 6], 'big') for i in range(0, len(d) - 5, 6)]

def chunk(w, z, k):
    # chunk k of the module starting at zone z
    a = (z + k // 85) * 1024 + k % 85 * 12
    return w[a:a + 12] if a + 12 <= len(w) else None

def pair(v):
    return v >> 24, v & 0xffffff

def header(h):
    # problems of a header chunk, None if it is not one at all
    if h[0] != 1 or h[1] == 0:
        return None
    if any(h[i] >> 15 for i in (2, 3, 4, 5, 6)) or h[3] > h[4]:
        return None
    for i in (7, 8, 9):
        c, n = pair(h[i])
        if c != (n + 5) // 6 or n >> 15:
            return None
    if h[5] == 0:
        return None
    return []

def check(w, z):
    h = chunk(w, z, 0)
    if h is None or header(h) is None:
        return None
    warn = []
    prev = -1
    for k in range(1, h[5] + 1):
        c = chunk(w, z, k)
        if c is None:
            return 'за концом тома'
        a = (c[10] & 0o177) << 8 | c[11] & 0o377
        if a < prev and k % 85 == 0:
            warn.append('обрыв: зона %04o не продолжает модуль' % (z + k // 85))
            break
        if a < prev:
            return 'кусок %d: адрес %05o < %05o' % (k, a, prev)
        prev = a + 1
    if prev - 1 > h[4] + h[6] + 0o100000:
        warn.append('адрес за длиной')
    n = 1 + h[5] + sum(pair(h[i])[0] for i in (7, 8, 9))
    return warn, n

def name(v):
    # as disbesm6 debemsh: 0100-0137 -> 040-077, 0240-0337 -> 0100-0177, KOI-7
    s = ''
    for i in range(6):
        b = v >> (40 - 8 * i) & 0o377
        if 0o100 <= b <= 0o137:
            b -= 0o40
        elif 0o240 <= b <= 0o337:
            b -= 0o140
        if 0o140 <= b <= 0o176:
            s += 'ЮАБЦДЕФГХИЙКЛМНОПЯРСТУЖВЬЫЗШЭЩЧ'[b - 0o140]
        elif 0o40 <= b < 0o140:
            s += 'АВЕКМНОРСТУХ'['ABEKMHOPCTYX'.index(chr(b))] if chr(b) in 'ABEKMHOPCTYX' else chr(b)
        else:
            s += '?'
    return s.rstrip()

if __name__ == '__main__':
    verbose = '-v' in sys.argv
    for src in [a for a in sys.argv[1:] if a != '-v']:
        w = words(src)
        nz = len(w) // 1024
        print('%s: %d зон' % (src, nz))
        for z in range(nz):
            r = check(w, z)
            if r is None:
                continue
            h = chunk(w, z, 0)
            if isinstance(r, str):
                if verbose:
                    print('  %04o  не модуль: %s' % (z, r))
                continue
            warn, n = r
            print('  %04o  %d зон  %-6s  СТАРТ %05o  ДИАП %05o-%05o  ДЛИНА %05o  '
                  'кусков %d/%d/%d/%d%s'
                  % (z, (n + 84) // 85, name(h[1]), h[2], h[3], h[4], h[6], h[5],
                     pair(h[7])[0], pair(h[8])[0], pair(h[9])[0],
                     '  ' + ', '.join(warn) if warn else ''))
