#!/usr/bin/env python3
# Words that were instructions in the committed parts/NAME.be and came out
# as data after "make parts be" (disbesm6 --trace takes the branch of a
# traced conditional jump that was never taken for data, so more coverage
# can turn code into КОНД).
# Usage: tools/coderegr.py [NAME...]     (all parts by default)
#   translates the HEAD version (parts/NAME.old.be, listing only) and the
#   current one, prints for every part an ENTRIES line for notes/NAME.py
#   with the first address of each run of lost code.
import glob, os, re, subprocess, sys

def code(lst):
    res = set()
    for l in open(lst, errors='replace'):
        m = re.match(r'^.{0,36}?([0-7]{5}) ([0-7]{2} [0-7]{2,3} +[0-7]{4,5})(?: +[0-7]{5})? +\d{4}  \d{4} (.{0,6}) ?(\S*)', l)
        if m and m.group(4) not in ('КОНК', 'КК', 'ДК', 'ДКБ'):
            res.add(int(m.group(1), 8))
    return res

names = sys.argv[1:] or [l.split()[0] for l in open('parts.txt')
                         if l.strip() and not l.startswith('#')]
for n in names:
    old = subprocess.run(['git', 'show', 'HEAD:parts/%s.be' % n],
                         capture_output=True, check=True).stdout
    open('parts/%s.old.be' % n, 'wb').write(old)
    subprocess.run(['tools/reasm.pl', '-t', 'parts/%s.old.be' % n, 'parts/%s.be' % n],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lost = sorted(code('parts/%s.old.be.lst' % n) - code('parts/%s.be.lst' % n))
    first = [a for a in lost if a - 1 not in lost]
    if first:
        print("%s: %d слов\nENTRIES = list(globals().get('ENTRIES', [])) + [%s]"
              % (n, len(lost), ', '.join("'%05o'" % a for a in first)))
    for f in glob.glob('parts/%s.old.*' % n):
        os.remove(f)
