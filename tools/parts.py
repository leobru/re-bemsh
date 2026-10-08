#!/usr/bin/env python3
# Build the parts listed in parts.txt: parts/NAME.bin (zones concatenated),
# parts/NAME.cov (union of traces/*.cov/ZZZZ.cov for its zones) and
# parts/NAME.dis (raw disbesm6 -s output, module name from parts.txt).
# Usage: tools/parts.py [name ...]     (default: all)
import glob, os, re, subprocess, sys

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
os.makedirs('parts', exist_ok=True)
for l in open('parts.txt'):
    if l.startswith('#') or not l.strip():
        continue
    name, mod, addr, *zones = l.split()
    if len(sys.argv) > 1 and name not in sys.argv[1:]:
        continue
    with open('parts/%s.bin' % name, 'wb') as f:
        for z in zones:
            f.write(open('zones/%s.bin' % z, 'rb').read())
    cov = set()
    for z in zones:
        for c in glob.glob('traces/*.cov/%s.cov' % z):
            cov.update(x.split(':')[0] for x in open(c))
    with open('parts/%s.cov' % name, 'w') as f:
        f.writelines('%s: L\n' % a for a in sorted(cov))
    entry = min(cov) if cov else addr
    alt = ['-e%05o' % a for a in sorted(altret(open('parts/%s.bin' % name, 'rb').read(), int(addr, 8)))]
    out = subprocess.run([DIS, '-s', '-a' + addr, '-e' + entry] + alt + notes_entries(name) + [
                          '--trace=parts/%s.cov' % name, 'parts/%s.bin' % name],
                         stdout=subprocess.PIPE, check=True).stdout.decode()
    with open('parts/%s.dis' % name, 'w') as f:
        # the first word carries the module name, not a D/G label
        # (disbesm6 starts an image loaded at 0 from word 1)
        start = int(addr, 8) or 1
        out = re.sub(r'(?<![А-Я0-9])[GD]%05o(?![0-7])' % start, mod, out)
        f.write(out.replace('НЕИМЯ\tСТАРТ', mod + '\tСТАРТ', 1))
    print('%-7s %s %s: %d адресов исполнялось' % (name, addr, ' '.join(zones), len(cov)))
