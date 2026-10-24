# -*- coding: utf-8 -*-
r"""줄임 번역 반영(2026-10-24): python tools/apply_fit.py work/fit_51.tsv — tr_*.tsv 의 같은 키 줄을 바꿈(CRLF 유지)."""
import glob, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fit = dict(l.rstrip('\r\n').split('\t', 1) for l in open(sys.argv[1], encoding='utf-8') if l.strip())
n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'work/tr/tr_[0-9][0-9].tsv'))):
    L = open(p, encoding='utf-8', newline='').read().split('\n'); ch = False
    for i, l in enumerate(L):
        k = l.split('\t', 1)[0]
        if k in fit: L[i] = k + '\t' + fit[k] + ('\r' if l.endswith('\r') else ''); n += 1; ch = True
    if ch: open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print('반영', n, '/', len(fit))
