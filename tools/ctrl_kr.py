# -*- coding: utf-8 -*-
r"""옵션 «컨트롤러 설정» 설명 그림(TRAIN.SUB 856D5850·856E4AD0, 280×218 8bpp) 한글화 (2026-10-24)
  찾은 경로: 스테이트 RAM 0xA5F290·0xA6E510 에 머리째 있고 디스크와 바이트 같음(처음 RAM 대조는 표본 64 B 가 안 맞아 놓침).
  이름표 칸(베이지 바탕) 안 글자만 바탕으로 지우고 다시 씀. 아이콘(△○×)·화살표(▲▼)·테두리는 원본.
  표기(사용자 2026-10-24): 칸이 좁아 붙여 씀 — 문개폐·시점변경·안내방송·시점이동, «브레이크 유지»만 띄움. 切る=끔(HUD 와 통일), マスコン=마스콘.
  python tools/ctrl_kr.py → work/gfx/prev_ctrl.png(원본|새것 3배) · build.py 가 apply(out_iso)"""
import os, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402
sys.path.insert(0, r'C:\claude\project\densha-final-kr-patch\tools')
import gfx8_kr as G  # noqa: E402
G.S = S

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
COMMON = [((12, 5, 122, 22), 'L1&R1:문개폐'), ((161, 5, 242, 23), '시점변경'), ((176, 43, 263, 61), '안내방송'),
          ((214, 85, 259, 103), '경적'), ((27, 110, 103, 127), '시점이동')]
TEX = {   # 칸 = 베이지 바탕 덩어리 그대로(아이콘·▲▼ 자리는 뺌)
    0x856D5850: COMMON + [((121, 108, 189, 125), '브레이크'), ((4, 137, 60, 153), '마스콘'), ((4, 160, 39, 177), '끔'),
                          ((4, 188, 39, 205), '가속'), ((137, 152, 171, 168), '감압'), ((239, 152, 273, 168), '가압'),
                          ((153, 180, 257, 196), '브레이크 유지')],
    0x856E4AD0: COMMON + [((4, 133, 60, 149), '마스콘'), ((6, 148, 54, 163), '비상'), ((6, 171, 54, 185), '끔'),
                          ((6, 196, 54, 210), '가속')],
}
TH = 14   # 글자 잉크 높이(원본 12~14)


def glyphs(kr, h, wmax):
    """덮임 비율(0~1) — 원본처럼 가장자리 중간색. 넓으면 가로만 줄임"""
    from PIL import ImageDraw, ImageFont
    SS = 8; f = ImageFont.truetype(FONT, h * SS * 2)
    l, t_, r, b = f.getbbox(kr)
    im = Image.new('L', (r - l + 16, b - t_ + 16)); ImageDraw.Draw(im).text((8 - l, 8 - t_), kr, font=f, fill=255)
    a = np.array(im); ys = np.nonzero(a.max(1))[0]; xs = np.nonzero(a.max(0))[0]
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    w = min(int(round(a.shape[1] * h / a.shape[0])), wmax)
    return np.array(Image.fromarray(a).resize((w, h), Image.BOX)) / 255.0


def make(t, labels):
    px = t.px.copy(); P = t.pal.astype(float)
    op = np.nonzero(P[:, 3] >= 120)[0]
    for (x0, y0, x1, y1), kr in labels:
        sub = px[y0:y1, x0:x1]
        bg = int(np.bincount(sub.ravel(), minlength=256).argmax())
        ink = sub[sub != bg]
        fg = int(np.bincount(ink, minlength=256).argmax()) if len(ink) else 0
        sub[:] = bg
        m = glyphs(kr, min(TH, y1 - y0 - 2), x1 - x0 - 2)
        mh, mw = m.shape
        oy = (y1 - y0 - mh) // 2; ox = (x1 - x0 - mw) // 2
        want = P[bg, :3][None, None] * (1 - m[..., None]) + P[fg, :3][None, None] * m[..., None]
        d = np.abs(want[..., None, :] - P[op][None, None, :, :3]).sum(-1)
        idx = op[d.argmin(-1)]
        reg = sub[oy:oy + mh, ox:ox + mw]
        reg[m > 0.12] = idx[m > 0.12]
    return px


def apply(out_iso):
    f = open(S.ISO, 'rb'); n = 0
    with open(out_iso, 'r+b') as g:
        for off, labels in TEX.items():
            t = G.Tex8(f, off); blob = t.encode(make(t, labels))
            g.seek(S.BASE + off); g.write(blob); g.seek(S.BASE + off); assert g.read(len(blob)) == blob
            n += 1
    return n


def preview():
    f = open(S.ISO, 'rb'); rows = []
    for off, labels in TEX.items():
        t = G.Tex8(f, off)
        rows.append(np.concatenate([t.rgb(), np.full((t.h, 4, 3), 255, np.uint8), t.rgb(make(t, labels))], 1))
    a = np.concatenate(rows, 0)
    Image.fromarray(a).resize((a.shape[1] * 3, a.shape[0] * 3), Image.NEAREST).save(os.path.join(ROOT, 'work/gfx/prev_ctrl.png'))


if __name__ == '__main__':
    preview()
