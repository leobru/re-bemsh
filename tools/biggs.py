#!/usr/bin/env python3
# A job with a big macro library: N macros of K model lines each, to make
# the ГС larger than the 13 memory pages of the buffer pool of mred24
# (jobs/biggs.be: tools/biggs.py 60 40 > jobs/biggs.be; with 24 macros the
# ГС takes several blocks, but no buffer is evicted).
# Usage: tools/biggs.py N K > jobs/NAME.be
import sys
n, k = int(sys.argv[1]), int(sys.argv[2])
for i in range(n):
    print(' МАСRО')
    print('&М МАК%d &А,&Б' % i)
    for j in range(k):
        print("%s СЧ &А+%d" % ('&М' if j == 0 else '', j))
        print(" ЗП &Б+%d" % j)
    print(' МЕND')
print("ТЕСТ СТАРТ '1000'")
for i in range(0, n, 7):
    print(' МАК%d X,Y' % i)
print("X КОНД В'1'")
print('Y ПАМ 100')
print(' ФИНИШ')
