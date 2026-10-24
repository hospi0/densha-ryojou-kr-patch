# -*- coding: utf-8 -*-
r"""제목 화면 «スタートボタンを押してください»(TRAIN.SUB 86E3D310, 400×50 4bpp) → «스타트 버튼을 눌러 주세요» (2026-10-24 실기 지적)
  원본 꼴 = 두꺼운 둥근 글씨: 연노랑 채움 + 안쪽 어두운 노랑 1px + 검정 테 2px + 바깥 반투명 남색 그림자 1~2px.
  주아 꼴을 4배로 그려 층을 만들고 텍스처 팔레트 가장 가까운 번호로(RGBA). 글자 자리 = 원본 잉크 x10~390·y12~38.
  python tools/title_kr.py → work/gfx/prev_start.png(원본|새것 3배) · build.py 가 apply(out_iso)"""
import os, sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

KEY = '86E3D310'
TEXT = '스타트 버튼을 눌러 주세요'
FONT = r'C:\claude\utils\font\jua\Jua-Regular.ttf'
BOX = (14, 13, 386, 37)   # 채움 글자 상자(테 2px·그림자는 바깥)
SS = 4
FILL, INNER, EDGE = (241, 244, 164, 128), (150, 151, 110, 128), (43, 43, 19, 128)
SHADOW = (13, 12, 183, 31)   # 2차(사용자 «테두리가 원본보다 너무 진함»): 원본 = 검정 1px + 옅은 반투명 1px


def mask():
    x0, y0, x1, y1 = BOX; Hh = (y1 - y0) * SS
    f = ImageFont.truetype(FONT, Hh * 2)
    l, t_, r, b = f.getbbox(TEXT)
    im = Image.new('L', (r - l + 8, b - t_ + 8)); ImageDraw.Draw(im).text((4 - l, 4 - t_), TEXT, font=f, fill=255)
    a = np.array(im); ys = np.nonzero(a.max(1))[0]; xs = np.nonzero(a.max(0))[0]
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    w = (x1 - x0) * SS   # 원본처럼 상자 폭 꽉(가로로 늘림)
    a = np.array(Image.fromarray(a).resize((w, Hh), Image.LANCZOS)) >= 128
    out = np.zeros((50 * SS, 400 * SS), bool)
    ox = x0 * SS + ((x1 - x0) * SS - w) // 2
    out[y0 * SS:y0 * SS + Hh, ox:ox + w] = a
    return out


def make(t):
    m = mask()
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5) / SS   # 바깥 거리
    di = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5) / SS    # 안쪽 거리
    img = np.zeros(m.shape + (4,))
    img[(d > 0) & (d <= 2.0)] = SHADOW
    img[(d > 0) & (d <= 1.25)] = EDGE
    img[m] = FILL; img[m & (di <= 1.0)] = INNER
    Hh, Ww = 50, 400
    a = img.reshape(Hh, SS, Ww, SS, 4)
    al = a[..., 3]; A = al.mean((1, 3))
    C = (a[..., :3] * al[..., None]).sum((1, 3)) / np.maximum(al.sum((1, 3)), 1e-6)[..., None]
    want = np.concatenate([C, A[..., None]], -1)
    P = t.P.astype(float)
    dist = np.abs(want[..., None, :3] - P[None, None, :, :3]).sum(-1) * (want[..., None, 3] / 128) + np.abs(want[..., None, 3] - P[None, None, :, 3]) * 3
    idx = dist.argmin(-1)
    clear = int(np.argmin(t.P[:, 3])); idx[A < 4] = clear
    return idx


def apply(out_iso):
    I = L.index(); f = open(S.ISO, 'rb'); t = L.Tex(f, *I[KEY]); blob = t.encode(make(t))
    off = I[KEY][0]
    with open(out_iso, 'r+b') as g:
        g.seek(S.BASE + off); g.write(blob); g.seek(S.BASE + off); assert g.read(len(blob)) == blob
    return 1


def preview():
    I = L.index(); f = open(S.ISO, 'rb'); t = L.Tex(f, *I[KEY])
    BG = np.array([60, 110, 70])
    flat = lambda x: (x[..., :3] * (x[..., 3:4] / 255.0) + BG * (1 - x[..., 3:4] / 255.0)).astype(np.uint8)
    a = np.concatenate([flat(t.rgba()), np.full((50, 4, 3), 255, np.uint8), flat(t.rgba(make(t)))], 1)
    Image.fromarray(a).resize((a.shape[1] * 3, a.shape[0] * 3), Image.NEAREST).save(os.path.join(ROOT, 'work/gfx/prev_start.png'))


if __name__ == '__main__':
    preview()
