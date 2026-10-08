#!/usr/bin/env python3
# Build the memory image of one phase (0..077777) from parts, with the union
# of their coverage, and disassemble it as a whole for reading (labels shared
# across parts). Not meant for reassembly; that is done per part.
# Usage: tools/image.py OUT part1 part2 ...   ->  OUT.bin OUT.cov OUT.adr
import os, subprocess, sys

def notes_entries(name):
    """Extra entry points from notes/NAME.py (ENTRIES = ['ааааа', ...])."""
    fn = 'notes/%s.py' % name
    if not os.path.exists(fn):
        return []
    g = {}
    exec(open(fn).read(), g)
    return ['-e' + e for e in g.get('ENTRIES', [])]



def altret(data, base):
    """Second-return addresses: a word 'ПВ x(М) / 00 000 aaaa' (call in the
    left half, address in the right) - the callee may return to aaaa."""
    res = set()
    for i in range(len(data) // 6):
        w = int.from_bytes(data[i*6:i*6+6], 'big')
        l, r = w >> 24, w & 0xffffff
        if (l & 0o3700000) == 0o3100000 and (r >> 15) == 0 and \
                base <= r < base + len(data) // 6 and r != base + i + 1:
            res.add(r)
    return res

DIS = os.environ.get('DISBESM6', os.path.expanduser('~/git/leobru/dispak-tools/disbesm6'))
out, names = sys.argv[1], sys.argv[2:]
parts = {}
for l in open('parts.txt'):
    if l.startswith('#') or not l.strip():
        continue
    n, mod, addr, *zones = l.split()
    parts[n] = (int(addr, 8), len(zones))
mem = bytearray(6 * 0o100000)
cov = set()
for n in names:
    addr, nz = parts[n]
    data = open('parts/%s.bin' % n, 'rb').read()
    mem[addr * 6:addr * 6 + len(data)] = data
    cov.update(x.split(':')[0] for x in open('parts/%s.cov' % n))
open(out + '.bin', 'wb').write(mem)
with open(out + '.cov', 'w') as f:
    f.writelines('%s: L\n' % a for a in sorted(cov))
with open(out + '.adr', 'w') as f:
    alt = ['-e%05o' % a for a in sorted(altret(bytes(mem), 0)) if a]
    subprocess.run([DIS, '-t', '-a0', '-e' + min(cov)] + alt + sum((notes_entries(n) for n in names), []) + ['--trace=' + out + '.cov',
                    out + '.bin'], stdout=f, check=True)
