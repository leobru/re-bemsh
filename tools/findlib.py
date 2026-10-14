#!/usr/bin/env python3
# Find compiled macro libraries (made by ЗПКОМП, read by ЧТКОМП) on disk
# volumes. Usage: tools/findlib.py [-n N] VOLUME|FILE...
#   VOLUME - a disk number (dumped with "besmtool dump"), FILE - a dump
#   (6 bytes per word, 1024 words per zone).
# A library (README, "Макрокомпилятор"): zones +0..+5 - the common name
# table (010000-023777), +6, +7... - pages of code (030000). Three tests:
#   1. signature: word 01677 of zone +5 (023677) & 7777777777777000 =
#      1234567654321000, the low 9 bits - number of code pages (ЧТБИБ of
#      mred2 checks exactly this; the 12/77 version has no signature);
#   2. code page: words 0, 1 = 02000, 01777 and calls ПВ 02003-02077(М12)
#      (handlers of the macro machine, ТКОМ; both 06/78 and 12/77 build
#      them from the template ПВ 02003(М12));
#   3. -n N: every zone with at least N such calls (default 3).
import os, subprocess, sys, tempfile

args = sys.argv[1:]
nmin = 3
if args[:1] == ['-n']:
    nmin = int(args[1]); args = args[2:]

def load(src):
    if os.path.exists(src):
        return open(src, 'rb').read()
    with tempfile.NamedTemporaryFile(suffix='.bin') as t:
        subprocess.run(['besmtool', 'dump', src, '--to-file=' + t.name],
                       check=True, stdout=subprocess.DEVNULL)
        return open(t.name, 'rb').read()

def calls(w):
    n = 0
    for x in w:
        for h in (x >> 24, x & 0xffffff):
            if h >> 20 == 0o12 and h >> 19 & 1 and h >> 15 & 0o37 == 0o31 \
                    and 0o2003 <= h & 0o77777 <= 0o2077:
                n += 1
    return n

for src in args:
    d = load(src)
    print('%s: %d зон' % (src, len(d) // 6144))
    for z in range(len(d) // 6144):
        w = [int.from_bytes(d[z * 6144 + i:z * 6144 + i + 6], 'big') for i in range(0, 6144, 6)]
        if w[0o1677] & 0o7777777777777000 == 0o1234567654321000:
            print('  %04o: подпись в слове 01677, страниц кода %o -> библиотека с зоны %04o'
                  % (z, w[0o1677] & 0o777, z - 5))
        n = calls(w)
        if w[0] == 0o2000 and w[1] == 0o1777:
            print('  %04o: начало страницы кода (02000, 01777), вызовов %d' % (z, n))
        elif n >= nmin:
            print('  %04o: вызовов ПВ 020xx(М12): %d' % (z, n))
