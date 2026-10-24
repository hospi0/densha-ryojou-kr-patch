# -*- coding: utf-8 -*-
"""번역 표에 범주 공통 글자 높이(size=) 붙이기 (2026-10-24 — 사용자 «원본은 다 같은 폰트인데 우리껀 제각각»)
  같은 그림 크기(w×h)끼리 원본 잉크 높이 중앙값 → 그 크기의 모든 줄 메모에 size=N. 상자 지정·bmp·size 가 있는 줄은 그대로.
  python tools/fix_size.py ui_hud.tsv ui_station.tsv …"""
import os, re, sys
from collections import defaultdict
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

I = L.index(); f = open(S.ISO, 'rb')
for fn in sys.argv[1:]:
    p = os.path.join(ROOT, 'work/text', fn)
    lines = open(p, encoding='utf-8').read().split('\n')
    rows = [(i, (ln.split('\t') + ['', ''])[:4]) for i, ln in enumerate(lines[1:], 1) if ln.strip()]
    hs = defaultdict(list); sz = {}
    for i, c in rows:
        if re.search(r'box=|bmp=|size=|mode=row', c[3]): continue
        t = L.Tex(f, *I[c[0]]); b = L.plate_box(t, (0, 0, t.w, t.h))
        an = L.analyse(t, b); ink = an['ink']
        hs[(t.w, t.h)].append(ink[3] - ink[1]); sz[i] = (t.w, t.h)
    med = {k: int(np.median(v)) for k, v in hs.items()}
    for i, c in rows:
        if i in sz:
            c[3] = (c[3] + ' size=%d' % med[sz[i]]).strip(); lines[i] = '\t'.join(c)
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    print(fn, {('%dx%d' % k): v for k, v in med.items()})
