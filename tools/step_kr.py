# -*- coding: utf-8 -*-
r"""옵션 «아날로그 컨트롤러 캘리브레이션» Step1·2·3·Finish 판(480×56 4bpp) 두 줄 설명 (2026-10-24)
  알약 칸(x146~458·y8~44) 안의 글자 번호를 바탕(1)으로 지우고, 두 줄을 명조 기울임으로 다시 씀.
  {…} 로 감싼 낱말 = 주황(10, 원본 保ちの左端·非常 강조), 나머지 = 진갈색(7). Step/Finish 그림 글자는 원본.
  python tools/step_kr.py → work/gfx/prev_step.png · build.py 가 apply(out_iso)"""
import json, os, re, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

BOX = (152, 8, 461, 44)    # 알약 테두리 안쪽(왼쪽 곡선 x~150, 오른쪽 테 x~462, 아래 테 y44~)
LINE2 = '안내 방송 버튼을 눌러 주세요'
ROWS = [
    ('856C7480', '브레이크 레버를 {유지 왼쪽 끝}에 맞추고,'),
    ('856CA950', '브레이크 레버를 {유지 오른쪽 끝}에 맞추고,'),
    ('856CDE20', '브레이크 레버를 {비상}에 맞추고,'),
    ('856D12F0', '캘리브레이션 설정이 끝났습니다.'),
]
H = 14


def seg_masks(text):
    out = []
    for part in re.split(r'(\{[^}]*\})', text):
        if not part: continue
        hi = part.startswith('{'); s = part.strip('{}')
        lead = len(s) - len(s.lstrip(' ')); trail = len(s) - len(s.rstrip(' '))
        m = L.render_mask(s.strip(' '), H, 400, 0, L.FONTS['M'], 0.15) if s.strip(' ') else np.zeros((H, 0), bool)
        sp = np.zeros((m.shape[0], 4), bool)
        for _ in range(lead): out.append((sp, False))
        out.append((m, hi))
        for _ in range(trail): out.append((sp, False))
    return out


def colors(t, box):
    """판마다 팔레트가 다름(Finish = 분홍) → 바탕 = 칸 최다 번호, 글자 = 가장 어두운 불투명, 강조 = 가장 주황(빨강 크고 파랑 작은)"""
    x0, y0, x1, y1 = box; P = t.P.astype(int)
    bg = int(np.bincount(t.idx[y0:y1, x0:x1].ravel(), minlength=16).argmax())
    op = [i for i in range(16) if P[i, 3] > 100]
    dark = min(op, key=lambda i: np.abs(P[i, :3] - (115, 68, 48)).sum())   # 원본 글자 진갈색(가장 어두운 65,3,1 은 너무 검음)
    hi = max(op, key=lambda i: P[i, 0] - P[i, 2] + (P[i, 1] > 60) * 40 - (P[i, 0] < 200) * 300)
    return bg, dark, hi


def draw_line(idx, text, y0, x0, x1, DARK, HI):
    segs = seg_masks(text)
    hh = max(m.shape[0] for m, _ in segs); w = sum(m.shape[1] for m, _ in segs)
    sx = min(1.0, (x1 - x0) / w)
    x = x0 + int(((x1 - x0) - w * sx) // 2)
    for m, hi in segs:
        if m.shape[1] == 0: continue
        nw = max(1, int(round(m.shape[1] * sx)))
        if nw != m.shape[1]:
            m = np.array(Image.fromarray(m.astype(np.uint8) * 255).resize((nw, m.shape[0]), Image.NEAREST)) > 127
        oy = y0 + (hh - m.shape[0]) // 2
        idx[oy:oy + m.shape[0], x:x + m.shape[1]][m] = HI if hi else DARK
        x += m.shape[1]


def make(t, line1):
    idx = t.idx.copy(); x0, y0, x1, y1 = BOX
    bg, dark, hi = colors(t, BOX)
    idx[y0:y1, x0:x1] = bg
    r = idx[8:26, 455:470]; r[r != 2] = bg   # 오른쪽 테(x470~ 진갈색, 2 는 안쪽 그림자) 곁 «、» 잔여
    draw_line(idx, line1, 10, x0, x1 - 2, dark, hi)
    draw_line(idx, LINE2, 28, x0, x1 - 2, dark, hi)
    return idx


def apply(out_iso):
    I = L.index(); f = open(S.ISO, 'rb'); n = 0
    canon = json.load(open(os.path.join(ROOT, 'work/gfx/canon.json')))
    dups = json.load(open(os.path.join(ROOT, 'work/gfx/dups.json')))
    with open(out_iso, 'r+b') as g:
        for key, line1 in ROWS:
            t = L.Tex(f, *I[key]); blob = t.encode(make(t, line1)); c = canon.get(key, key)
            for k in [c] + dups.get(c, []):
                off, size = I[k]
                f.seek(S.BASE + off); assert f.read(size) == t.blob, '사본 다름 %s' % k
                g.seek(S.BASE + off); g.write(blob); g.seek(S.BASE + off); assert g.read(len(blob)) == blob
                n += 1
    return n


def preview():
    I = L.index(); f = open(S.ISO, 'rb'); rows = []
    for key, line1 in ROWS:
        t = L.Tex(f, *I[key])
        rows.append(np.concatenate([t.rgba()[..., :3], np.full((t.h, 4, 3), 255, np.uint8), t.rgba(make(t, line1))[..., :3]], 1))
    a = np.concatenate(rows, 0)
    Image.fromarray(a).resize((a.shape[1] * 2, a.shape[0] * 2), Image.NEAREST).save(os.path.join(ROOT, 'work/gfx/prev_step.png'))


if __name__ == '__main__':
    preview()
