#!/usr/bin/env python3
# Control flow of one phase from a user-mode trace (tools/trace.sh output).
# Usage: tools/flow.py trace FROM TO
#   FROM, TO - octal addresses of the Э70 that load the phase and the next
#   one (e.g. 01226 01311 for the macro editor); the phase is the stretch of
#   the trace between the first executions of these addresses.
# Prints the subroutines called by ПВ (vjm) in the order of their first call,
# with call counts and callers, then the extracodes executed in the phase.
import re, sys
from collections import OrderedDict, defaultdict
fn, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
calls = OrderedDict(); callers = defaultdict(set); ecodes = defaultdict(int)
inphase = False; pend = None; prev = None
for l in open(fn, errors='replace'):
    m = re.match(r'^([0-7]{5}): (\S+)\s+(\S*)', l)
    if not m:
        continue
    pc, op, arg = m.groups()
    if not inphase:
        if pc == a and op == '*70':
            inphase = True
        continue
    if pc == b and op == '*70':
        break
    if pend:                    # first instruction after a ПВ is its target
        calls[pc] = calls.get(pc, 0) + 1
        callers[pc].add(pend)
        pend = None
    if op == 'vjm':
        pend = pc
    elif op.startswith('*'):
        ecodes['%s %s' % (op, pc)] += 1
for t, n in calls.items():
    print('%s  %5d  из %s' % (t, n, ' '.join(sorted(callers[t]))))
print()
for e, n in sorted(ecodes.items()):
    print('%s  %d' % (e, n))
