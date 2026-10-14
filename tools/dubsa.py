#!/usr/bin/env python3
# The Dubna standard array made by zgr (BEMSH mode 1122): runs a *bemsh job
# under the Dubna simulator with its own trace of instructions and memory
# writes ("-d iem") and prints the words zgr wrote into the buffer from
# 06000 before writing it to the drum (Э70 in 02371).
# Usage: tools/dubsa.py [-a] job.dub
#   Collects the memory writes after zgr is loaded ("Disk 30 Read
#   [02000-03777] = Zone 1") up to the first drum write of the buffer.
#   Prints the nonzero words: address, offset in the array, octal, TEXT
#   reading (Dubna 6-bit code, 8 characters per word); -a - also zeros
#   up to the end of the written part.
# DUBNA=path - the simulator (default: dubna in PATH).
import os, re, subprocess, sys, tempfile

TEXT = ' .БЦДФГИ()*ЙЛЯЖ/0123456789Ь,П-+ЫЗАВСDЕFGНIJКLМNОРQRSТUVWХУZШЭЩЧЮ'

def text(w):
    return ''.join(TEXT[w >> (42 - 6 * i) & 0o77] for i in range(8))

args = [a for a in sys.argv[1:] if a != '-a']
job = os.path.abspath(args[0])
mem, state, pages = {}, 0, []
with tempfile.TemporaryDirectory() as tmp:
    p = subprocess.Popen([os.environ.get('DUBNA', 'dubna'), '-r', '-d', 'iem',
                          '--trace=/dev/stdout', job], cwd=tmp, text=True,
                         errors='replace', stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL)
    for l in p.stdout:
        if state == 0:
            if 'Disk 30 Read [02000-03777] = Zone 1' in l:
                state = 1
            continue
        m = re.match(r'^\s+Memory Write \[([0-7]{5})\] = ([0-7 ]{19})$', l.rstrip())
        if m:
            mem[int(m.group(1), 8)] = int(m.group(2).replace(' ', ''), 8)
            continue
        if l.startswith('02371 R:') and '*70' in l:
            state = 2
            continue
        m = re.match(r'^\s+Drum \d+ Write \[([0-7]{5})-([0-7]{5})\]', l)
        if state == 2 and m:
            pages.append((int(m.group(1), 8), int(m.group(2), 8)))
            continue
        if state == 2 and pages and not l.startswith('0237'):
            break
    p.kill()
    p.wait()
if not pages:
    sys.exit('нет записи стандартного массива (Э70 в 02371)')
lo, hi = pages[0][0], pages[-1][1]
print('записано: %s' % ' '.join('%05o-%05o' % x for x in pages))
last = max([a for a in mem if lo <= a <= hi and mem[a]] or [lo])
for a in range(lo, last + 1):
    w = mem.get(a, 0)
    if w or '-a' in sys.argv:
        print('%05o %4o  %016o  %s' % (a, a - lo, w, text(w)))
