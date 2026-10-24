# -*- coding: utf-8 -*-
r"""노선 지도 3장(에노덴 8463CB80·하코다테 84714C40·란덴 84780BE0) 글자 덩어리 자동 찾기(2026-10-24) — 검은 글자(번호 1·2) 연결 덩어리를 부풀려 묶음.
  python tools/map2_survey.py → work/gfx/map2_<위치>.png(상자·번호) + 표준 출력 상자 목록"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

def comps(m):
    lab = np.zeros(m.shape, int); n = 0
    for y, x in zip(*np.nonzero(m)):
        if lab[y, x]: continue
        n += 1; st = [(y, x)]; lab[y, x] = n
        while st:
            cy, cx = st.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and m[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n; st.append((ny, nx))
    return lab, n

def blobs(t, dark=(1, 2), grow=2):
    m = np.isin(t.idx, dark); g = L.dilate(m, grow); lab, n = comps(g); out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero((lab == i) & m)
        if len(ys) < 6: continue
        out.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return sorted(out, key=lambda b: (b[0], b[1]))

if __name__ == '__main__':
    I = L.index(); f = open(S.ISO, 'rb')
    for k in ('8463CB80', '84714C40', '84780BE0'):
        t = L.Tex(f, *I[k]); bs = blobs(t)
        im = Image.fromarray(t.rgba()[..., :3]).resize((t.w * 3, t.h * 3), Image.NEAREST); d = ImageDraw.Draw(im)
        for i, (x0, y0, x1, y1) in enumerate(bs):
            d.rectangle([x0 * 3, y0 * 3, x1 * 3, y1 * 3], outline=(255, 0, 255)); d.text((x1 * 3 + 2, y0 * 3), str(i), fill=(255, 0, 0))
        im.save(os.path.join(ROOT, 'work/gfx/map2_%s.png' % k))
        print(k, len(bs)); print('  ' + ' '.join('%d:%s' % (i, b) for i, b in enumerate(bs)))
