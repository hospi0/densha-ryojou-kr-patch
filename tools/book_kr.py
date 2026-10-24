# -*- coding: utf-8 -*-
r"""이름 입력 책 그림(8bpp 616×340, TRAIN.SUB A46F9230 — 사본 없음) «運転士：» → «운전사 :» (2026-10-24)
  글자 칸(x 116~212, y 80~102)의 회색 글자를 판 색(점무늬 225/228 — 칸 짝수·홀수별 최빈)으로 지우고,
  나눔명조 엑스트라볼드(원본 명조 꼴)를 원본 글자 중심 자리(運 転 士 ： = x 130·156·180·204)에 한 자씩.
  덮임 → 판~가장 어두운 글자 색 사이 밝기에서 원본 글자에 쓰인 번호 중 가장 가까운 것(disclaimer_kr 와 같음).
  python tools/book_kr.py → work/gfx/prev_book.png(원본|새것 3배) · build.py 가 apply(out_iso)"""
import os, sys
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sub_dump as S  # noqa: E402

OFF, W, H = 0xA46F9230, 616, 340
FONT = r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoExtraBold.ttf'
X0, Y0, X1, Y1 = 116, 80, 212, 102
CHARS = [('운', 130), ('전', 156), ('사', 180), (':', 204)]
SS = 4


def load(f):
    f.seek(S.BASE + OFF); b = f.read(16 + 1024 + W * H)
    return b, np.frombuffer(b[1040:], np.uint8).reshape(H, W).copy(), np.frombuffer(b[16:1040], np.uint8).reshape(256, 4)


def make(ix, P):
    lum = P[:, :3].astype(float) @ (.3, .59, .11)
    out = ix.copy(); sub = out[Y0:Y1, X0:X1]
    yy, xx = np.mgrid[Y0:Y1, X0:X1]; par = (xx + yy) % 2
    plate = Counter(sub.ravel().tolist()).most_common(1)[0][0]
    text = np.abs(lum[sub] - lum[plate]) > 8
    pp = {p: Counter(sub[(par == p) & ~text].tolist()).most_common(1)[0][0] for p in (0, 1)}
    sat = lambda k: int(P[k, :3].max()) - int(P[k, :3].min())
    used = sorted((k for k in set(sub[text].tolist()) if sat(k) < 24), key=lambda k: lum[k])   # 회색만(가장자리 누런 번짐 번호 → 올리브색으로 나옴)
    dark = used[0]
    ys = np.nonzero(text.any(1))[0]; gh = ys.max() + 1 - ys.min(); gy = Y0 + ys.min()
    for p in (0, 1): sub[text & (par == p)] = pp[p]
    font = ImageFont.truetype(FONT, gh * SS)
    for ch, cx in CHARS:
        im = Image.new('L', (gh * SS * 2, gh * SS * 2), 0)
        ImageDraw.Draw(im).text((SS * 4, SS * 4), ch, font=font, fill=255, stroke_width=SS // 4, stroke_fill=255)   # 조금 굵게(사용자 «흐림»)
        a = np.array(im); ry = np.nonzero(a.any(1))[0]; rx = np.nonzero(a.any(0))[0]
        a = a[ry.min():ry.max() + 1, rx.min():rx.max() + 1]
        hh = gh if ch != ':' else max(2, int(round(a.shape[0] / (gh * SS) * gh)))   # 쌍점은 제 크기, 글자 줄 아래쪽에 맞춤
        ww = max(1, int(round(a.shape[1] * hh / a.shape[0])))
        cov = np.array(Image.fromarray(a).resize((ww, hh), Image.LANCZOS), float) / 255
        oy = gy if ch != ':' else gy + gh - hh - 2
        ox = cx - ww // 2
        for (r, c) in zip(*np.nonzero(cov > 0.15)):
            y, x = oy + r, ox + c
            base = pp[(x + y) % 2]
            tgt = lum[base] + min(1, cov[r, c] * 1.6) * (lum[dark] - lum[base])
            out[y, x] = min(used + [base], key=lambda k: abs(lum[k] - tgt))
    return out


def preview():
    f = open(S.ISO, 'rb'); b, ix, P = load(f); new = make(ix, P)
    rgb = lambda i: P[i][..., :3]
    c = (slice(60, 120), slice(100, 330))
    a = np.concatenate([rgb(ix[c]), np.full((60, 3, 3), 255, np.uint8), rgb(new[c])], 1)
    Image.fromarray(a.astype(np.uint8)).resize((a.shape[1] * 3, a.shape[0] * 3), Image.NEAREST).save(os.path.join(ROOT, 'work/gfx/prev_book.png'))


def apply(out_iso):
    f = open(S.ISO, 'rb'); b, ix, P = load(f); new = make(ix, P)
    with open(out_iso, 'r+b') as g:
        g.seek(S.BASE + OFF + 1040); g.write(new.tobytes())
        g.seek(S.BASE + OFF + 1040); assert g.read(W * H) == new.tobytes()
    return 1


if __name__ == '__main__':
    preview()
