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
FONT_SMALL = r'C:/Windows/Fonts/malgunbd.ttf'   # 로 = 작은 글자, 블랙한산스는 획 사이가 1px 로 막힘
FONT_SUB = r'C:\claude\utils\font\jua\Jua-Regular.ttf'   # 旅情編 = 둥근 고딕
SS = 4
BIG = ('전차', (17, 32, 103, 76))   # 4차(사용자 «전차로 부분은 파이널에서 한거랑 똑같이»): 파이널 logo_kr 그대로 — «전차» 한 번에 렌더(사이 1px)·같은 층
SMALL = ('로', (103, 51, 126, 75))   # 파이널 で 자리 비율(電車 상자 기준 ×0.71) · 블랙한산스 얇은 테·얇은 그림자
SC, SR = (317, 88), 69   # 도장 원
SUB = ('여정편', (100, 95, 270, 145))   # 3차: 사용자 «여정편이 너무 큼» → 높이 50·오른쪽 끝은 도장 위 編 자리(plate) 덮게 그대로
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


def mask_text(text, box, gap=1, grow=1, shear=0.0, font=FONT, stretch=False):
    x0, y0, x1, y1 = box; HH = (y1 - y0) * SS
    f = ImageFont.truetype(font, HH * 2); gl = []
    for ch in text:
        l, t_, r, b = f.getbbox(ch)
        im = Image.new('L', (r - l + 8, b - t_ + 8)); ImageDraw.Draw(im).text((4 - l, 4 - t_), ch, font=f, fill=255)
        a = np.array(im); ys = np.nonzero(a.max(1))[0]; xs = np.nonzero(a.max(0))[0]
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        gl.append(np.array(Image.fromarray(a).resize((max(1, int(round(a.shape[1] * HH / a.shape[0]))), HH), Image.LANCZOS)))
    g4, w4 = gap * SS, grow * SS
    Wd = sum(g.shape[1] for g in gl) + g4 * (len(gl) - 1) + 2 * w4 + int(shear * HH)
    sx = (x1 - x0) * SS / Wd if stretch else min(1.0, (x1 - x0) * SS / Wd)
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


def layer_out(m, fill, rings, shadow=SHADOW_S):
    """で 꼴: 획은 채움색 그대로, 테는 획 «바깥»에 rings=[(두께px, 색), …] 순서로(흰 1·회색 1·검정 2) + 그림자"""
    H4, W4 = m.shape
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5) / SS
    tot = sum(w for w, _ in rings)
    o = d <= tot
    dx, dy = shadow[0] * SS, shadow[1] * SS
    sh = np.zeros_like(o); sh[dy:, dx:] = o[:-dy, :-dx]
    img = np.zeros((H4, W4, 4))
    img[sh] = (1, 1, 1, 128)
    acc = tot
    for w, c in reversed(rings):
        img[d <= acc] = c; acc -= w
    col = np.broadcast_to(np.repeat(fill, SS, 0)[:, None, :], (H4, W4, 4))
    img[m] = col[m]
    return img


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


def layer_sub(m, white, orange, plate=None, ring=4.5):
    """여정편: 흰 채움 + 주황 테(원본 4~5px, 바깥 1px 반투명) — 원본에 하늘색 그림자 없음.
    plate = 도장 위에서 編 이 덮고 있던 자리 — 주황 테로 메워 도장 구멍을 가림"""
    d = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5) / SS
    o = d <= ring
    if plate is not None: o |= plate
    soft = ~o & (cv2.distanceTransform((~o).astype(np.uint8), cv2.DIST_L2, 5) / SS <= 1.0)
    img = np.zeros(m.shape + (4,))
    img[soft] = orange; img[soft, 3] = 64
    img[o] = orange; img[m] = white
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
    # G 는 초록 몸통 + 테 2px 만 남김(で 의 흰·회색 테가 G 테에 붙어 있어 7px 로 두면 찌꺼기)
    rgb0 = t.pal.astype(int)[t.px][..., :3]
    gstrong = green & (rgb0[..., 1] - np.maximum(rgb0[..., 0], rgb0[..., 2]) > 40)   # 진한 초록만(で 흰 테의 옅은 초록빛 화소 220,247,234 가 G 로 잡혀 흰 점 찌꺼기)
    dG = cv2.distanceTransform((~gstrong).astype(np.uint8), cv2.DIST_L2, 3)
    keepG = (X >= 118) & op & (gstrong | ((dG <= 4.5) & (dG < dB)))   # G 자기 테(흰·회색·검정 ~4px) 까지 — 2.5 면 G 왼쪽 테가 깎임(사용자 지적)
    px = t.px.copy(); bg = int(t.px[5, 5])
    erase = (X < CUT_X) & (Y < CUT_Y) & ~keepG
    px[erase] = bg
    P = t.pal.astype(int); rgb = P[t.px][..., :3]
    # 旅情編: 흰 몸통(도장 밖에서 시작하는 덩어리) + 둘레 6px(주황 테 5px+반투명 1px)만 지움
    reg = (Y >= 80) & (Y < 170) & (X >= 55) & (X < 285)
    wh = reg & (rgb.min(-1) > 225) & (P[t.px][..., 3] == 128)
    n, lab, st, _ = cv2.connectedComponentsWithStats(wh.astype(np.uint8), connectivity=4)
    gw = np.isin(lab, [i for i in range(1, n) if st[i, 0] < 250]) & wh
    sw = wh & ~gw   # 도장 흰 바탕
    dW = cv2.distanceTransform((~gw).astype(np.uint8), cv2.DIST_L2, 5)
    sub = reg & (dW <= 7.5) & ~sw & op
    px[sub] = bg
    # 도장 위 編 자리 복원(3차 — 여정편을 줄이면 주황 판이 위아래로 삐져나옴): 도장 = 원(중심 317,88·반지름 69).
    # 구멍 화소마다 같은 반지름에서 구멍 각도 범위의 가까운 끝을 기준으로 거울 각도 화소를 가져옴(고리 띠가 이어짐)
    hole = sub & (X >= 240)
    R = np.hypot(X - SC[0], Y - SC[1]); A = np.arctan2(Y - SC[1], X - SC[0]) % (2 * np.pi)
    hy, hx = np.nonzero(hole & (R <= SR + 1.5))
    for y, x in zip(hy, hx):
        r = R[y, x]; band = hole & (np.abs(R - r) < 0.75)
        a0, a1 = A[band].min(), A[band].max(); a = A[y, x]
        s = a0 - (a - a0) - 0.02 if a - a0 < a1 - a else a1 + (a1 - a) + 0.02
        sx, sy = int(round(SC[0] + r * np.cos(s))), int(round(SC[1] + r * np.sin(s)))
        if 0 <= sx < W and 0 <= sy < H and not hole[sy, sx]: px[y, x] = t.px[sy, sx]
    plate = None
    limit = ((Y < CUT_Y) | ((Y <= CUT_Y + 3) & (P[px][..., :3].max(-1) < 40))) & (X < CUT_X + 8)
    compose(t, px, down(layer(mask_text(*BIG, gap=3, shear=SHEAR), edge, red_rows)), limit)   # 파이널 gap=1 은 0.71배 크기에서 테에 묻혀 붙음 → 3
    compose(t, px, down(layer(mask_text(*SMALL, grow=0, shear=SHEAR), edge, blue_rows, thin=True, ring=1, shadow=SHADOW_S)), limit)
    px[keepG] = t.px[keepG]   # G 가 로 위
    # G 왼쪽 테 다시 그림(원본은 で 테와 붙어 있어 판정으로는 못 살림 — 사용자 «G자 왼쪽 지워짐»): 진한 초록 바깥 흰1·회색1·검정2
    Pf = t.pal.astype(int)
    near = lambda c: int(np.abs(Pf[:, :3] - np.array(c)).sum(1).argmin() if True else 0)
    iw, ig, ik = near((255, 255, 255)), near((172, 169, 168)), near((1, 1, 1))
    gfix = gstrong.copy()   # で 가 덮던 G 왼쪽 몸통(y50~70 이 1px 패임) → 위아래 끝(x131→130)을 이어 채움
    for yy in range(50, 71):
        xl = int(round(131 - (yy - 50) / 20)); xs_ = np.nonzero(gstrong[yy, 118:160])[0]
        if len(xs_) and xl < 118 + xs_.min():
            x0_ = 118 + xs_.min(); px[yy, xl:x0_ + 1] = t.px[yy, x0_ + 3]; gfix[yy, xl:x0_] = True   # 가장자리 번호는 어두운 계단 → 3px 안쪽 색
    dG = cv2.distanceTransform((~gfix).astype(np.uint8), cv2.DIST_L2, 3)
    gl = (X >= 118) & (X < CUT_X) & (Y < CUT_Y) & ~gfix
    px[gl & (dG <= 4.5) & (dG > 2.5)] = ik; px[gl & (dG <= 2.5) & (dG > 1.5)] = ig; px[gl & (dG <= 1.5)] = iw
    white = P[255].astype(float); orange = np.array([234, 123, 21, 128.])
    m = mask_text(*SUB, gap=2, grow=1, font=FONT_SUB, stretch=True)
    up = None
    compose(t, px, down(layer_sub(m, white, orange, up)), (Y >= 78) & (Y < 165))
    return px


MASK = 0x86E15360   # 로고 등장 연출 검은 판(640×480 4bpp, 번호 = 알파 계단 0~128). 원본 = «128 − 로고 알파»(로고와 같은 좌표, 오차 평균 0.09)


def make_mask(t, px):
    import label_kr as LK
    m = LK.Tex(open(S.ISO, 'rb'), MASK, LK.index()['86E15360'][1])
    want = 128 - t.pal[px][..., 3].astype(int)
    A = m.P[:, 3].astype(int)
    idx = m.idx.copy()
    idx[:H, :W] = np.abs(want[..., None] - A[None, None, :]).argmin(-1)
    return m, idx


def apply(out_iso):
    f = open(S.ISO, 'rb'); t = G.Tex8(f, OFF); px = make(t); blob = t.encode(px)
    m, midx = make_mask(t, px); mblob = m.encode(midx)
    with open(out_iso, 'r+b') as g:
        for o, b in ((OFF, blob), (MASK, mblob)):
            g.seek(S.BASE + o); g.write(b); g.seek(S.BASE + o); assert g.read(len(b)) == b
    return 2


def preview():
    f = open(S.ISO, 'rb'); t = G.Tex8(f, OFF); n = make(t)
    a = np.concatenate([t.rgb(), np.full((t.h, 4, 3), 200, np.uint8), t.rgb(n)], 1)[:170]
    p = os.path.join(ROOT, 'work', 'gfx', 'prev_logo4.png')
    Image.fromarray(a).resize((a.shape[1] * 2, a.shape[0] * 2), Image.NEAREST).save(p)


if __name__ == '__main__':
    preview()
