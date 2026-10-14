#!/usr/bin/env python3
# Compare the BEMSH zones of disk volumes word by word.
# Usage: tools/volcmp.py [-w] [FROM TO] VOLUME VOLUME...
#   VOLUME - a disk number (dumped with "besmtool dump") or a dump file
#   (6 bytes per word, 1024 words per zone). FROM, TO - octal zones
#   (default 0137 0177, the BEMSH area of 2048). The first volume is the
#   reference: for every zone prints the number of words that differ in
#   each other volume and their ranges (word offsets in the zone); with -w
#   also every differing word in octal.
import os, re, subprocess, sys, tempfile

args = [a for a in sys.argv[1:] if a != '-w']
lo, hi = 0o137, 0o177
if len(args) > 2 and re.fullmatch(r'[0-7]{3,4}', args[0]) and re.fullmatch(r'[0-7]{3,4}', args[1]):
    lo, hi = int(args[0], 8), int(args[1], 8)
    args = args[2:]

def load(src):
    if os.path.exists(src):
        return open(src, 'rb').read()
    with tempfile.NamedTemporaryFile(suffix='.bin') as t:
        subprocess.run(['besmtool', 'dump', src, '--to-file=' + t.name],
                       check=True, stdout=subprocess.DEVNULL)
        return open(t.name, 'rb').read()

def word(d, z, i):
    return int.from_bytes(d[z * 6144 + 6 * i:z * 6144 + 6 * i + 6], 'big')

vols = [(a, load(a)) for a in args]
ref, rd = vols[0]
for z in range(lo, hi + 1):
    out = []
    for name, d in vols[1:]:
        diff = [i for i in range(1024) if word(rd, z, i) != word(d, z, i)]
        rng, i = [], 0
        while i < len(diff):
            j = i
            while j + 1 < len(diff) and diff[j + 1] == diff[j] + 1:
                j += 1
            rng.append('%04o' % diff[i] + ('-%04o' % diff[j] if j > i else ''))
            i = j + 1
        out.append('%s: %4d %s' % (name, len(diff), ' '.join(rng[:8]) + (' …' if len(rng) > 8 else '')))
        if '-w' in sys.argv and 0 < len(diff) < 64:
            for i in diff:
                out.append('      %04o  %s %016o  %s %016o' % (i, ref, word(rd, z, i), name, word(d, z, i)))
    print('%04o  ' % z + '\n      '.join(out))
