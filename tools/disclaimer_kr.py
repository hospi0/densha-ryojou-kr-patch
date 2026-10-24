# -*- coding: utf-8 -*-
r"""시작 경고문(8bpp 616×432 사진 텍스처 86E66B00) 한글로 (2026-10-24)
  판 안 글자(어두운 회색 + 회색 단계)를 판 색으로 지우고, 나눔고딕 엑스트라볼드로 5줄을 원본 줄 자리에 다시 씀.
  덮임 비율 → 판 색~글자 색 사이 밝기에서 «원본 글자에 쓰인 번호» 중 가장 가까운 것(팔레트는 그대로).
  python tools/disclaimer_kr.py preview → work/gfx/disclaimer.png(원본|한글) · build.py 가 apply(out_iso) 호출"""
import os, sys
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sub_dump as S  # noqa: E402

OFF, W, H = 0x86E66B00, 616, 432
FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
LINES = ['본 작품은 실제 운행·운전을 게임으로',
         '각색했기 때문에 현실의 운행·운전',
         '시스템과 다른 점이 있습니다.',
         '노선 데이터 등은 2002년 2월 현재의',
         '것을 참고했습니다.']
SS = 4


def load(f):
    f.seek(S.BASE + OFF); b = f.read(16 + 1024 + W * H)
    return b, np.frombuffer(b[1040:], np.uint8).reshape(H, W).copy(), np.frombuffer(b[16:1040], np.uint8).reshape(256, 4)


def make(ix, P):
    lum = P[:, :3].astype(float) @ (.3, .59, .11)
    sub = ix[138:297, 66:553]
    plate = Counter(sub.ravel().tolist()).most_common(1)[0][0]
    dark = int(min(set(sub.ravel().tolist()), key=lambda k: lum[k]))
    text = np.abs(lum[sub] - lum[plate]) > 8
    ys, xs = np.nonzero(text)
    y0, y1, x0 = ys.min(), ys.max() + 1, xs.min()
    sat = lambda k: int(P[k, :3].max()) - int(P[k, :3].min())
    used = [k for k in set(sub[text].tolist()) if sat(k) < 20]   # 회색만(가장자리 붉은 번짐 번호 제외)
    # 원본 줄 자리: 글자 있는 줄 덩어리
    rr = np.nonzero(text.any(1))[0]; bands = []; s = p = rr[0]
    for r in rr[1:]:
        if r - p > 2: bands.append((s, p + 1)); s = r
        p = r
    bands.append((s, p + 1))
    out = ix.copy(); o = out[138:297, 66:553]; o[text] = plate
    gh = int(np.median([b - a for a, b in bands]))
    font = ImageFont.truetype(FONT, int(gh * SS * 1.15))
    cand = sorted(used + [plate], key=lambda k: lum[k])
    for (a, b), line in zip(bands, LINES):
        im = Image.new('L', (o.shape[1] * SS, gh * SS * 2), 0)
        ImageDraw.Draw(im).text((SS * 2, SS * 2), line, font=font, fill=255, stroke_width=SS // 2, stroke_fill=255)   # 원본 굵기
        arr = np.array(im); ry = np.nonzero(arr.any(1))[0]; rx = np.nonzero(arr.any(0))[0]
        arr = arr[ry.min():ry.max() + 1, :rx.max() + 1]
        hh = gh; ww = int(round(arr.shape[1] * hh / arr.shape[0]))
        ww = min(ww, o.shape[1] - x0 - 2)
        cov = np.array(Image.fromarray(arr).resize((ww, hh), Image.LANCZOS), float) / 255
        cy = (a + b) // 2 - hh // 2
        for (r, c) in zip(*np.nonzero(cov > 0.12)):
            tgt = lum[plate] + cov[r, c] * (lum[dark] - lum[plate])
            o[cy + r, x0 + c] = min(cand, key=lambda k: abs(lum[k] - tgt))
    return out


def preview():
    f = open(S.ISO, 'rb'); b, ix, P = load(f); new = make(ix, P)
    rgb = lambda i: P[i][..., :3]
    a = np.concatenate([rgb(ix), np.full((H, 4, 3), 255, np.uint8), rgb(new)], 1)
    Image.fromarray(a.astype(np.uint8)).save(os.path.join(ROOT, 'work/gfx/disclaimer.png'))


def apply(out_iso):
    f = open(S.ISO, 'rb'); b, ix, P = load(f); new = make(ix, P)
    with open(out_iso, 'r+b') as g:
        g.seek(S.BASE + OFF + 1040); g.write(new.tobytes())
        g.seek(S.BASE + OFF + 1040); assert g.read(W * H) == new.tobytes()
    return 1


if __name__ == '__main__':
    preview()
