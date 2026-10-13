#!/usr/bin/env python3
# Build the test jobs listed in jobs/OPTS with tools/job.pl.
# Usage: tools/mkjobs.py [NAME...]      (all of them by default)
#   A jobs/NAME.b6 is rewritten only when its text changes, so the traces
#   of unchanged jobs stay valid (tools/cover.py looks at the file times).
# jobs/OPTS: "NAME: job.pl options [sources] [<PREV] [!SEC]"; the source
#   is jobs/NAME.be unless given; <PREV - the job runs on the scratch disk
#   2222 left by job PREV (a macro library written by ЗПКОМП); !SEC - the
#   job never ends by itself, stop it after SEC seconds; @PREV - the job
#   starts from the archive 2099 (tape 42) left by job PREV.
import os, shlex, subprocess, sys

def opts():
    res = {}
    for l in open('jobs/OPTS'):
        if l.strip() and not l.startswith('#'):
            n, o = l.split(':', 1)
            o = shlex.split(o)
            prev = [x[1:] for x in o if x.startswith('<')]
            lim = [int(x[1:]) for x in o if x.startswith('!')]
            arch = [x[1:] for x in o if x.startswith('@')]
            o = [x for x in o if x[0] not in '<!@']
            if not any(x.startswith('jobs/') for x in o):
                o.append('jobs/%s.be' % n)
            res[n] = (o, prev[0] if prev else None, lim[0] if lim else None,
                      arch[0] if arch else None)
    return res

if __name__ == '__main__':
    o = opts()
    for n in sys.argv[1:] or o:
        text = subprocess.run(['tools/job.pl'] + o[n][0], check=True,
                              capture_output=True).stdout
        f = 'jobs/%s.b6' % n
        os.makedirs(os.path.dirname(f), exist_ok=True)
        if not os.path.exists(f) or open(f, 'rb').read() != text:
            open(f, 'wb').write(text)
            print(f)
