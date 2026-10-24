# -*- coding: utf-8 -*-
r"""사운드 설정 막대 양 끝 «低/高» → «저/고» (2026-10-24 사용자). 音楽·音声·効果音 줄(480×56 4bpp) 3장.
  글자 칸만 바탕(2)으로 지우고 나눔 엑스트라볼드 15px 을 팔레트 섞은 중간색으로(ctrl_kr 와 같은 방식). 줄 이름은 ui_opt.tsv 가 먼저 씀.
  python tools/lohi_kr.py → work/gfx/prev_lohi.png · build.py 가 apply(out_iso) (gfx_build 뒤)"""
import json, os, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

KEYS = ('856BD610', '856C0AE0', '856C3FB0')
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
CELLS = (((150, 19, 172, 37), '저'), ((430, 19, 452, 37), '고'))
H = 15


def glyph(ch):
    """같은 글꼴 크기·같은 세로 기준(«저고» 공통 상자)으로 — 글자마다 잉크 높이에 맞추면 납작한 «고»가 커짐"""
    SS = 8; f = ImageFont.truetype(FONT, 16 * SS)
    l, t_, r, b = f.getbbox('저고')
    im = Image.new('L', (f.getbbox(ch)[2] + 16, b + 16)); ImageDraw.Draw(im).text((8, 8), ch, font=f, fill=255)
    a = np.array(im)[8 + t_:8 + b]; xs = np.nonzero(a.max(0))[0]; a = a[:, xs.min():xs.max() + 1]
    h = H; w = max(1, int(round(a.shape[1] * h / a.shape[0])))
    return np.array(Image.fromarray(a).resize((w, h), Image.BOX)) / 255.0


def make(t, idx):
    idx = idx.copy(); P = t.P.astype(float); op = np.nonzero(P[:, 3] >= 120)[0]
    for (x0, y0, x1, y1), ch in CELLS:
        sub = idx[y0:y1, x0:x1]
        ink = t.idx[y0:y1, x0:x1]; bg = int(np.bincount(ink.ravel(), minlength=16).argmax())
        fg = min(op, key=lambda i: np.abs(P[i, :3] - (119, 44, 9)).sum())   # 원본 글자 진갈색(9)
        sub[:] = bg
        m = glyph(ch); mh, mw = m.shape; oy = (y1 - y0 - mh) // 2; ox = (x1 - x0 - mw) // 2
        want = P[bg, :3] * (1 - m[..., None]) + P[fg, :3] * m[..., None]
        near = op[np.abs(want[..., None, :] - P[op][None, None, :, :3]).sum(-1).argmin(-1)]
        reg = sub[oy:oy + mh, ox:ox + mw]; reg[m > 0.12] = near[m > 0.12]
    return idx


def base(f, I, key):
    R = {k: (kr, m) for fn, k, s, kr, m in L.rows()}
    t, cur = L.make(f, I, key, *R[key]) if key in R else (L.Tex(f, *I[key]), None)
    return t, (t.idx if cur is None else cur)


def apply(out_iso):
    I = L.index(); f = open(S.ISO, 'rb'); n = 0
    canon = json.load(open(os.path.join(ROOT, 'work/gfx/canon.json'))); dups = json.load(open(os.path.join(ROOT, 'work/gfx/dups.json')))
    with open(out_iso, 'r+b') as g:
        for key in KEYS:
            t, cur = base(f, I, key); blob = t.encode(make(t, cur)); c = canon.get(key, key)
            for k in [c] + dups.get(c, []):
                off, size = I[k]
                f.seek(S.BASE + off); assert f.read(size) == t.blob, '사본 다름 %s' % k
                g.seek(S.BASE + off); g.write(blob); g.seek(S.BASE + off); assert g.read(len(blob)) == blob
                n += 1
    return n


def preview():
    I = L.index(); f = open(S.ISO, 'rb'); rows = []
    for key in KEYS:
        t, cur = base(f, I, key)
        rows.append(np.concatenate([t.rgba()[..., :3], np.full((t.h, 4, 3), 255, np.uint8), t.rgba(make(t, cur))[..., :3]], 1))
    a = np.concatenate(rows, 0)
    Image.fromarray(a).resize((a.shape[1] * 2, a.shape[0] * 2), Image.NEAREST).save(os.path.join(ROOT, 'work/gfx/prev_lohi.png'))


if __name__ == '__main__':
    preview()
