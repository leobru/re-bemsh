#!/usr/bin/env python3
# Code coverage of the parts by the test jobs.
# Usage: tools/cover.py [-r] [-j JOB]... [-u] [PART...]
#   Builds the jobs of jobs/OPTS (tools/mkjobs.py), then traces every
#   jobs/*.b6 and jobs/*/*.b6 that has no traces/NAME.cov yet
#   (or is newer than it; -r - all of them again) with tools/trace.sh |
#   tools/phases.py, then compares the executed addresses with the code
#   words of each part (instruction lines of parts/PART.be.lst, made by
#   "make check") and prints a table: code words, executed, percent.
#   PART... - also list the unexecuted code ranges of these parts with the
#             nearest label above ("МЕТКА+N").
#   -j JOB  - count only these jobs (name as in traces/, e.g. komp, dir/АIF).
#   -u      - with -j: print what these jobs execute that no other job does.
#   -l      - instead of the ranges print the source of PART... (label,
#             operation, operand, comment) with the address of each word;
#             '-' marks the code words that were never executed.
#   A job marked "<PREV" in jobs/OPTS starts from the 2222 left by PREV
#   (traces/PREV.2222, made by tools/run.sh), a job marked "@PREV" - from
#   the archive 2099 left by PREV (traces/PREV.2099, the whole chain of
#   "@" jobs before it is run by tools/run.sh with ARCH).
#   -d      - list the executed addresses that the source shows as data
#             (candidates for ENTRIES in notes/PART.py).
# rvs75 is traced by "make traces/rvs75.ev" (it needs the object modules).
import glob, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkjobs

args = sys.argv[1:]
redo = '-r' in args
uniq = '-u' in args
listing = '-l' in args
data = '-d' in args
only = []
want = []
i = 0
while i < len(args):
    if args[i] == '-j':
        only.append(args[i + 1]); i += 1
    elif not args[i].startswith('-'):
        want.append(args[i])
    i += 1

def jobname(b6):
    return os.path.splitext(os.path.relpath(b6, 'jobs'))[0]

subprocess.run(['tools/mkjobs.py'], check=True, stdout=subprocess.DEVNULL)
opts = mkjobs.opts()

done = {}                       # archives made in this run

def archive(n):
    # the 2099 left by job n (run after the jobs it depends on); its time
    if n not in done:
        done[n] = archive1(n)
    return done[n]

def archive1(n):
    b6, d = 'jobs/%s.b6' % n, 'traces/%s.2099' % n
    t = os.path.getmtime(b6)
    before = None
    if opts[n][3]:
        before, t0 = archive(opts[n][3])
        t = max(t, t0)
    if redo or not os.path.exists(d) or os.path.getmtime(d) < t:
        os.makedirs(os.path.dirname(d), exist_ok=True)
        if os.path.exists(d):
            os.remove(d)
        if before:
            shutil.copy(before, d)
        subprocess.run(['tools/run.sh', b6], stdout=subprocess.DEVNULL,
                       env=dict(os.environ, ARCH=d))
    return d, t

for b6 in sorted(glob.glob('jobs/*.b6') + glob.glob('jobs/*/*.b6')):
    n = jobname(b6)
    cov = 'traces/%s.cov' % n
    if n == 'rvs75':
        continue
    env = ''
    prev = opts[n][1] if n in opts else None
    if n in opts and opts[n][2]:
        env = 'timeout %d ' % opts[n][2]
    t = os.path.getmtime(b6)
    if prev:
        p6, d = 'jobs/%s.b6' % prev, 'traces/%s.2222' % prev
        t = max(t, os.path.getmtime(p6))
        if redo or not os.path.exists(d) or os.path.getmtime(d) < os.path.getmtime(p6):
            subprocess.run(['tools/run.sh', p6, d], stdout=subprocess.DEVNULL)
        env = 'IN2222="%s" ' % d + env
    if n in opts and opts[n][3]:
        d, t0 = archive(opts[n][3])
        t = max(t, t0)
        env = 'ARCH="%s" ' % d + env
    if redo or not os.path.isdir(cov) or os.path.getmtime(cov) < t:
        os.makedirs(cov, exist_ok=True)
        for f in glob.glob(cov + '/*.cov'):
            os.remove(f)
        subprocess.run(env + 'tools/trace.sh "%s" "traces/%s.txt" | tools/phases.py - "%s" '
                       '> "traces/%s.ev" 2>/dev/null' % (b6, n, cov, n), shell=True)
        os.utime(cov)
        print('трасса', n, file=sys.stderr)

parts = []
for l in open('parts.txt'):
    f = l.split()
    if f and not l.startswith('#'):
        parts.append((f[0], f[3:]))

def zonecov(zone, jobs=None, excl=None):
    s = set()
    for c in glob.glob('traces/*.cov/%s.cov' % zone) + glob.glob('traces/*/*.cov/%s.cov' % zone):
        n = os.path.relpath(os.path.dirname(c), 'traces')[:-4]
        if jobs and n not in jobs or excl and n in excl:
            continue
        s.update(int(x.split(':')[0], 8) for x in open(c))
    return s

allw = {}                       # part -> all addresses of its listing

def code(name):
    # address -> label+offset for the words that hold instructions
    res = {}
    allw[name] = set()
    lab, base = '', 0
    try:
        f = open('parts/%s.be.lst' % name, errors='replace')
    except OSError:
        return res
    for l in f:
        m = re.match(r'^.{0,36}?([0-7]{5}) ([0-7]{2} [0-7]{2,3} +[0-7]{4,5}|[0-7]{16})(?: +[0-7]{5})? +\d{4}  \d{4} (.{0,6}) ?(\S*)', l)
        if not m:
            continue
        a = int(m.group(1), 8)
        allw[name].add(a)
        if m.group(3).strip():
            lab, base = m.group(3).strip(), a
        # a word that starts with КОНК, КК or ДК is data in command format
        if ' ' in m.group(2) and m.group(4) not in ('КОНК', 'КОНД', 'КК', 'ДК', 'ДКБ'):
            res[a] = (lab + ('+%o' % (a - base) if a != base else '')) if lab else ''
    return res

tot = [0, 0]
for name, zones in parts:
    c = code(name)
    ex = set()
    for z in zones:
        ex |= zonecov(z, only) - (zonecov(z, None, only) if uniq and only else set())
    hit = ex & set(c)
    tot[0] += len(c); tot[1] += len(hit)
    print('%-7s %5d слов кода, исполнялось %5d (%3d%%)'
          % (name, len(c), len(hit), 100 * len(hit) // max(len(c), 1)))
    if data:
        bad = sorted((ex & allw[name]) - set(c))
        if bad:
            print('    данные исполнялись: ' + ' '.join('%05o' % a for a in bad))
    if name in want and listing:
        miss = set(c) - hit
        for l in open('parts/%s.be.lst' % name, errors='replace'):
            m = re.match(r'^.{0,36}?(?:([0-7]{5}) )?(?:[0-7]{2} [0-7]{2,3} +[0-7]{4,5}|[0-7]{16})(?: +[0-7]{5})? +\d{4}  \d{4} (.*)', l)
            if m:
                a = int(m.group(1), 8) if m.group(1) else None
                print('%s %5s %s' % ('-' if a in miss else ' ', m.group(1) or '', m.group(2).rstrip()))
            elif re.match(r'^ {30,}\d{4}  \d{4} \*', l):
                print('        ' + l[l.index('*', 40):].rstrip())
    elif name in want:
        miss = sorted(set(c) - hit)
        j = 0
        while j < len(miss):
            k = j
            while k + 1 < len(miss) and miss[k + 1] == miss[k] + 1:
                k += 1
            print('    %05o-%05o %4d  %s' % (miss[j], miss[k], k - j + 1, c[miss[j]]))
            j = k + 1
print('%-7s %5d слов кода, исполнялось %5d (%3d%%)'
      % ('всего', tot[0], tot[1], 100 * tot[1] // max(tot[0], 1)))
