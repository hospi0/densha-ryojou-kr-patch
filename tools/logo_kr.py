# -*- coding: utf-8 -*-
r"""제목 로고(TRAIN.SUB 86DFD850, 400×240 8bpp) «電車で»→«전차로», «旅情編»→«여정편» (2026-10-24 사용자 «타이틀도 해야해»)
  «파이널» tools/logo_kr.py 이식(층: 줄무늬 채움 · 안쪽 흰 가장자리 · 바깥 검정+그림자). GO!·®·도장(LET'S GO BY TRAIN!)은 그대로.
  여정편 = 흰 채움 + 주황 테 + 하늘색 그림자(원본 旅情編 꼴).
  python tools/logo_kr.py → work/gfx/prev_logo.png(원본|한글, 3배) · build.py 가 apply(out_iso)"""
import os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sub_dump as S  # noqa: E402
sys.path.insert(0, r'C:\claude\project\densha-final-kr-patch\tools')
import gfx8_kr as G  # noqa: E402   (Tex8: CSM1 팔레트 순서)
G.S = S

OFF = 0x86DFD850; W, H = 400, 240
FONT = r'C:\claude\utils\font\logo\BlackHanSans.ttf'
SS = 4
BIG = ('전차', (18, 32, 98, 76))
SMALL = ('로', (100, 52, 124, 76))
SUB = ('여정편', (86, 90, 278, 148))
SHADOW = (4, 5); SHADOW_S = (2, 2); SHEAR = 0.15
CUT_X, CUT_Y = 132, 82


def classes(t):
    P = t.pal.astype(int); a = P[t.px]
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    gray = (np.abs(r - g) < 25) & (np.abs(g - b) < 25)
    op = al > 0
    lum = a[..., :3].max(-1)
    green = op & ~gray & (g > r) & (g >= b) & (lum > 40)
    blue = op & ~gray & (b > r) & (b > g) & (lum > 40)
    return op, lum, green, blue


def mask_text(text, box, gap=1, grow=1, shear=0.0):
    x0, y0, x1, y1 = box; HH = (y1 - y0) * SS
    f = ImageFont.truetype(FONT, HH * 2); gl = []
    for ch in text:
        l, t_, r, b = f.getbbox(ch)
        im = Image.new('L', (r - l + 8, b - t_ + 8)); ImageDraw.Draw(im).text((4 - l, 4 - t_), ch, font=f, fill=255)
        a = np.array(im); ys = np.nonzero(a.max(1))[0]; xs = np.nonzero(a.max(0))[0]
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        gl.append(np.array(Image.fromarray(a).resize((max(1, int(round(a.shape[1] * HH / a.shape[0]))), HH), Image.LANCZOS)))
    g4, w4 = gap * SS, grow * SS
    Wd = sum(g.shape[1] for g in gl) + g4 * (len(gl) - 1) + 2 * w4 + int(shear * HH)
    sx = min(1.0, (x1 - x0) * SS / Wd)
    out = np.zeros((H * SS, W * SS), np.uint8)
    x = x0 * SS + int(round(((x1 - x0) * SS - Wd * sx) / 2)) + w4; Y0 = y0 * SS
    for g in gl:
        w = max(1, int(round(g.shape[1] * sx)))
        g = np.array(Image.fromarray(g).resize((w, HH), Image.LANCZOS))
        for yy in range(HH):
            dx = int(round(shear * sx * (HH - 1 - yy)))
            out[Y0 + yy, x + dx:x + dx + w] = np.maximum(out[Y0 + yy, x + dx:x + dx + w], g[yy])
        x += w + int(round(g4 * sx))
    m = out >= 128
    if grow:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * w4 + 1, 2 * w4 + 1))
        m = cv2.dilate(m.astype(np.uint8), k).astype(bool)
    return m


def learn(t):
    op, lum, green, blue = classes(t)
    P = t.pal.astype(int)
    core = op & (lum > 40) & ~blue
    core[:, 100:] = False; core[CUT_Y:, :] = False
    d = cv2.distanceTransform(core.astype(np.uint8), cv2.DIST_L2, 3)
    edge = []
    for lo, hi in ((0, 1.5), (1.5, 2.5), (2.5, 3.5)):
        v = t.px[core & (d > lo) & (d <= hi)]
        edge.append(P[int(np.bincount(v, minlength=256).argmax())].astype(float))
    rgb = P[t.px][..., :3]
    colored = (rgb.max(-1) - rgb.min(-1)) > 60

    def rows(m, pure):
        out = {}
        for y in range(H):
            v = t.px[y][m[y] & colored[y]]
            if len(v) >= 3:
                c = P[int(np.bincount(v, minlength=256).argmax())].astype(float)
                if pure(c): out[y] = c
        ys = sorted(out)
        return np.array([out[min(ys, key=lambda r: abs(r - y))] for y in range(H)])
    bl = blue.copy(); bl[:, CUT_X:] = False; bl[CUT_Y:, :] = False
    return edge, rows(core & (d > 3.5), lambda c: c[1] <= 8), rows(bl, lambda c: c[0] <= 12)


def layer(m, edge, fill, thin=False, ring=2, shadow=SHADOW, shcol=(1, 1, 1)):
    H4, W4 = m.shape
    img = np.zeros((H4, W4, 4))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ring * SS + 1, 2 * ring * SS + 1))
    o = cv2.dilate(m.astype(np.uint8), k)
    dx, dy = shadow[0] * SS, shadow[1] * SS
    sh = np.zeros_like(o); sh[dy:, dx:] = o[:-dy, :-dx]
    outl = (o | sh).astype(bool)
    dd = cv2.distanceTransform((~outl).astype(np.uint8), cv2.DIST_L2, 5) / SS
    soft = (~outl) & (dd <= 2.0)
    img[soft] = list(shcol) + [0]; img[soft, 3] = 128 * (1 - dd[soft] / 2.0) * 0.8
    img[outl] = list(shcol) + [128]
    d = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5) / SS
    col = np.broadcast_to(np.repeat(fill, SS, 0)[:, None, :], (H4, W4, 4)).copy()
    if thin: col[d <= 1.0] = edge[1]
    else: col[d <= 3.0] = edge[2]; col[d <= 2.0] = edge[1]; col[d <= 1.0] = edge[0]
    img[m] = col[m]
    return img


def layer_sub(m, white, orange, cyan):
    """여정편: 흰 채움 + 주황 테 3px + 하늘색 그림자(오른쪽 아래 3px)"""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * 3 * SS + 1, 2 * 3 * SS + 1))
    o = cv2.dilate(m.astype(np.uint8), k).astype(bool)
    sh = np.zeros_like(o); d3 = 3 * SS; sh[d3:, d3:] = o[:-d3, :-d3]
    img = np.zeros(m.shape + (4,))
    img[sh] = cyan; img[o] = orange; img[m] = white
    return img


def down(img):
    Hh, Ww = img.shape[0] // SS, img.shape[1] // SS
    a = img.reshape(Hh, SS, Ww, SS, 4); al = a[..., 3]
    A = al.mean((1, 3))
    C = (a[..., :3] * al[..., None]).sum((1, 3)) / np.maximum(al.sum((1, 3)), 1e-6)[..., None]
    return np.concatenate([C, A[..., None]], -1)


def compose(t, px, new, limit):
    P = t.pal.astype(float); cur = P[px]
    na = new[..., 3:4] / 128; ca = cur[..., 3:4] / 128
    oa = na + ca * (1 - na)
    oc = (new[..., :3] * na + cur[..., :3] * ca * (1 - na)) / np.maximum(oa, 1e-6)
    want = np.concatenate([oc, oa * 128], -1)
    sel = limit & (new[..., 3] > 2)
    Wt = want[sel]
    d = np.abs(Wt[:, None, :3] - P[None, :, :3]).sum(-1) * (Wt[:, None, 3] / 128) + np.abs(Wt[:, None, 3] - P[None, :, 3]) * 3
    px[sel] = d.argmin(-1)


def make(t):
    op, lum, green, blue = classes(t)
    edge, red_rows, blue_rows = learn(t)
    dG = cv2.distanceTransform((~green).astype(np.uint8), cv2.DIST_L2, 3)
    dB = cv2.distanceTransform((~blue).astype(np.uint8), cv2.DIST_L2, 3)
    X = np.arange(W)[None, :]; Y = np.arange(H)[:, None]
    keepG = (X >= 118) & (dG <= 7) & (dG < dB) & op
    px = t.px.copy(); bg = int(t.px[5, 5])
    erase = (X < CUT_X) & (Y < CUT_Y) & ~keepG
    px[erase] = bg
    # 旅情編: 도장(오른쪽 원) 왼쪽까지, 흰·주황·하늘색 글자 층만 지움
    P = t.pal.astype(int); rgb = P[t.px][..., :3]
    sub = (Y >= CUT_Y) & (Y < 160) & (X >= 60) & (X < 268) & op
    stamp = (X - 330) ** 2 + (Y - 95) ** 2 < 75 ** 2
    px[sub & ~stamp] = bg
    glyphc = (rgb.min(-1) > 225) | ((rgb[..., 0] > 200) & (rgb[..., 2] < 80)) | ((rgb[..., 2] > 200) & (rgb[..., 0] < 150))   # 흰·주황·하늘색
    px[sub & stamp & (X < 266) & glyphc & (Y > 100)] = bg   # 編 이 도장 위에 걸친 부분
    limit = ((Y < CUT_Y) | ((Y <= CUT_Y + 3) & (P[px][..., :3].max(-1) < 40))) & (X < CUT_X + 8)
    compose(t, px, down(layer(mask_text(*BIG, shear=SHEAR), edge, red_rows)), limit)
    compose(t, px, down(layer(mask_text(*SMALL, grow=0, shear=SHEAR), edge, blue_rows, thin=True, ring=1, shadow=SHADOW_S)), limit)
    white = P[255].astype(float); orange = P[108].astype(float); cyan = np.array([110, 200, 240, 128.])
    cy = [i for i in range(256) if P[i, 3] == 128 and P[i, 2] > 200 and P[i, 0] < 150 and P[i, 1] > 150]
    if cy: cyan = P[cy[0]].astype(float)
    m = mask_text(*SUB, gap=3, grow=0)
    compose(t, px, down(layer_sub(m, white, orange, cyan)), (Y >= CUT_Y - 2) & (Y < 165))
    return px


def apply(out_iso):
    f = open(S.ISO, 'rb'); t = G.Tex8(f, OFF); blob = t.encode(make(t))
    with open(out_iso, 'r+b') as g:
        g.seek(S.BASE + OFF); g.write(blob); g.seek(S.BASE + OFF); assert g.read(len(blob)) == blob
    return 1


def preview():
    f = open(S.ISO, 'rb'); t = G.Tex8(f, OFF); n = make(t)
    a = np.concatenate([t.rgb(), np.full((t.h, 4, 3), 200, np.uint8), t.rgb(n)], 1)[:170]
    p = os.path.join(ROOT, 'work', 'gfx', 'prev_logo4.png')
    Image.fromarray(a).resize((a.shape[1] * 2, a.shape[0] * 2), Image.NEAREST).save(p)


if __name__ == '__main__':
    preview()
