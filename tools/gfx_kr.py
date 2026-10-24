# -*- coding: utf-8 -*-
r"""그림 글자(TRAIN.SUB 4bpp 텍스처) 한글로 다시 그리기 (2026-10-24, «파이널» tools/gfx_kr.py 를 옮김 — 번호 = 텍스처 위치 16진)
  번역 표 work/text/ui_*.tsv (번호 = <묶음>#<순번>, MSG#a-b = 6DA800 긴 설명문 두 줄 × 조각 5)
  방법: 크기·팔레트 그대로. 원본 글자의 «꼴»을 배워서 한글 획에 입힌다.
    - 원본 잉크(알파>0) 화소마다 특징 = (안쪽 거리 d, 가장자리 방향, 글자 높이 안 세로 위치) → 팔레트 번호 분포
    - 한글 = 나눔고딕(굵기·부풀림은 원본 획 두께에 맞춰 고름) 을 원본 잉크 높이로, 넘치면 가로로 좁힘
    - 가장자리(d=1) 는 한글 덮임 정도 순으로 원본 d=1 번호를 «세기 순 분위»로 → 안티에일리어스 흉내
  python tools/gfx_kr.py preview [번호접두 ...] → work/gfx/prev_<n>.png (원본 | 한글, 실제 색, 2배)
  build.py 가 blobs() 로 (위치, 새 바이트) 를 받아 제자리 덮어쓴다(크기 불변).
"""
import os
import re
import struct
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sub_dump as S  # noqa: E402

FONTS = {
    'R': r'C:\claude\utils\font\nanum-gothic\NanumGothic.ttf',
    'B': r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf',
    'X': r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf',
    'H': r'C:\Windows\Fonts\malgunbd.ttf',
    'M': r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoExtraBold.ttf',
}
SS = 4   # 초과 표본
SYM = '△○◎×■'
WEIGHTS = ('X',)   # 굵기 고르기는 묶음마다 들쭉날쭉해서 하나로 고정
CAP = 12

# 번호별 손 설정: italic(기울임 화소/높이), font, vert(세로쓰기), lines(줄 나눔 기호), align
OVR = {}


def _ovr(keys, **kw):
    for k in keys:
        OVR.setdefault(k, {}).update(kw)


# ── 여정편 개별 설정(번호 = 텍스처 위치 16진) ──


# ── 자료 ─────────────────────────────────────────
def index():
    d = {}
    for ln in open(os.path.join(ROOT, 'work/ui/index.tsv'), encoding='utf-8').read().split('\n')[1:]:
        a = ln.split('\t')
        if len(a) < 4:
            continue
        d[a[0]] = (int(a[2], 16), int(a[3]))
    return d


def rows():
    out = []
    for fn in sorted(os.listdir(os.path.join(ROOT, 'work/text'))):
        if not fn.startswith('ui_'):
            continue
        for ln in open(os.path.join(ROOT, 'work/text', fn), encoding='utf-8').read().split('\n')[1:]:
            a = ln.split('\t')
            if len(a) < 3 or not a[2].strip():
                continue
            out.append((a[0], a[1], a[2]))
    return out


class Tex:
    def __init__(self, f, off, size):
        self.off, self.size = off, size
        f.seek(S.BASE + off); self.blob = f.read(size); self._f = f
        self.w, self.h = struct.unpack_from('<HH', self.blob, 2)
        self.n = 16 + 64 + self.w * self.h // 2
        assert 0 <= size - self.n < 16, '4bpp 아님'   # 끝 정렬 채움 0~12 B
        self.P = np.frombuffer(self.blob[16:80], np.uint8).reshape(16, 4).astype(int)
        d = np.frombuffer(self.blob[80:self.n], np.uint8)
        self.idx = np.stack([d & 15, d >> 4], 1).ravel().reshape(self.h, self.w)

    def rgba(self, idx=None):
        idx = self.idx if idx is None else idx
        P = self.P.copy(); P[:, 3] = np.minimum(255, P[:, 3] * 2)
        return P[idx].astype(np.uint8)

    def encode(self, idx):
        flat = idx.reshape(-1).astype(np.uint8)
        return self.blob[:80] + bytes((flat[0::2] | (flat[1::2] << 4)).tolist()) + self.blob[self.n:]


# ── 특징 ─────────────────────────────────────────
def dist_in(m, cap=CAP):
    """잉크 안쪽 거리(바깥 이웃과 맞닿으면 1). 8이웃 침식 반복."""
    d = np.zeros(m.shape, int); cur = m.copy(); k = 0
    while cur.any() and k < cap:
        k += 1; d[cur] = k
        p = np.pad(cur, 1)
        e = cur.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                e &= p[1 + dy:1 + dy + m.shape[0], 1 + dx:1 + dx + m.shape[1]]
        cur = e
    return d


def ridge_w(d):
    """획 반폭 — 거리 지도의 능선(8이웃 극대) 값 중앙. 빽빽한 한자가 뭉친 곳에 덜 휘둘린다."""
    p = np.pad(d, 1); h, w = d.shape; mx = np.zeros_like(d)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                mx = np.maximum(mx, p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w])
    r = (d > 0) & (d >= mx)
    return float(np.median(d[r])) if r.any() else 0.0


def edge_cls(m):
    p = np.pad(m, 1); h, w = m.shape
    up = ~p[0:h, 1:w + 1]; lf = ~p[1:h + 1, 0:w]; dn = ~p[2:h + 2, 1:w + 1]; rt = ~p[1:h + 1, 2:w + 2]
    a = up | lf; b = dn | rt
    return a.astype(int) + 2 * b.astype(int)


def ybin(m, nb=4):
    ys = np.nonzero(m.any(1))[0]
    y = np.arange(m.shape[0])[:, None].repeat(m.shape[1], 1)
    if not len(ys):
        return np.zeros(m.shape, int)
    t = (y - ys.min()) / max(1, ys.max() - ys.min() + 1)
    return np.clip((t * nb).astype(int), 0, nb - 1)


class Style:
    def __init__(self, tex, ink=None, ref=None, fillpct=None):
        self.tex = tex
        P = tex.P
        alpha = P[:, 3]
        self.ink = alpha[tex.idx] > 0 if ink is None else ink
        lum = P[:, :3] @ np.array([0.3, 0.59, 0.11])
        self.strength = lum * alpha / 128.0
        if ref is not None:   # 판 위 글자: 세기 = 판 색과의 차이
            self.strength = np.abs(P[:, :3] - P[ref, :3]).sum(1) / 3.0
        bg = Counter(tex.idx[~self.ink].ravel().tolist()).most_common(1)
        self.bg = bg[0][0] if bg else int(np.argmin(alpha))
        self.base = None
        m = self.ink
        self.d = dist_in(m); self.e = edge_cls(m); self.yb = ybin(m)
        self.tab = {}
        for key, v in zip(zip(np.minimum(self.d[m], CAP), self.e[m], self.yb[m]), tex.idx[m]):
            self.tab.setdefault(key, Counter())[v] += 1
        self.dmax = int(self.d.max()) if m.any() else 0
        self.sw = ridge_w(self.d)
        # 테두리 겹 수 R: 바깥 d 층부터 «속 색보다 확 어두운» 층이 몇 겹인가
        R = 0
        if m.any():
            core = m & (self.d >= max(2, self.sw))
            if fillpct:   # 어두운 몸통이 넓은 꼴(회색 기울임): 잉크 상위 세기
                fill = np.percentile(self.strength[tex.idx[m]], fillpct)
            else:
                fill = np.median(self.strength[tex.idx[core]]) if core.any() else self.strength[tex.idx[m]].max()
            for dd in range(1, int(self.sw)):
                lay = m & (self.d == dd)
                # 테두리 = 불투명한데 어두운 층 (반투명 층은 안티에일리어스일 뿐)
                if lay.any() and np.median(self.strength[tex.idx[lay]]) < 0.6 * fill                         and np.median(alpha[tex.idx[lay]]) >= 0x60:
                    R = dd
                else:
                    break
        self.R = R
        self.fill = fill if m.any() else 0
        # d=1 번호 세기 순 분위표 (세로 칸별)
        self.edge_q = {}
        for b in range(4):
            v = sorted(tex.idx[m & (self.d == 1) & (self.yb == b)].tolist(), key=lambda i: self.strength[i])
            if v:
                self.edge_q[b] = v
        self.edge_all = sorted(tex.idx[m & (self.d == 1)].tolist(), key=lambda i: self.strength[i])
        self.lut = self._lut()

    def _lut(self):
        """(d, e, yb) → 번호. 빈 칸은 단계적으로 메움."""
        agg = {}
        for (d, e, yb), c in self.tab.items():
            for kk in ((d, e, yb), (d, e, None), (d, None, yb), (d, None, None)):
                agg.setdefault(kk, Counter()).update(c)
        top = max([k[0] for k in agg] or [1])
        lut = {}
        for d in range(1, CAP + 1):
            dd = min(d, top)
            for e in range(4):
                for yb in range(4):
                    for kk in ((dd, e, yb), (dd, e, None), (dd, None, yb), (dd, None, None)):
                        if kk in agg:
                            lut[(d, e, yb)] = agg[kk].most_common(1)[0][0]; break
                    else:
                        lut[(d, e, yb)] = 15
        # 능선 층(d >= sw) 이상 = 속 색: 가장자리 방향 무시, 세로 칸별로 «밝은 번호» 중 최빈
        m = self.ink; idx = self.tex.idx
        deep = m & (self.d >= max(1, self.sw))
        ok = self.strength >= 0.75 * self.fill
        allc = Counter([v for v in idx[deep].tolist() if ok[v]])
        for yb in range(4):
            c = Counter([v for v in idx[deep & (self.yb == yb)].tolist() if ok[v]]) or allc
            if not c:
                continue
            v = c.most_common(1)[0][0]
            for d in range(int(max(1, self.sw)), CAP + 1):
                for e in range(4):
                    lut[(d, e, yb)] = v
        return lut


# ── 한글 그리기 ─────────────────────────────────────
_fc = {}


def font(k, size):
    key = (k, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FONTS[k], size)
    return _fc[key]


def render_line(text, fk, size):
    """초과표본 덮임(L) 과 기준 높이('한' 잉크 위·아래)."""
    f = font(fk, size * SS)
    l, t, r, b = f.getbbox(text)
    im = Image.new('L', (r - l + 8 * SS, (b - t) + 8 * SS)); d = ImageDraw.Draw(im)
    d.text((4 * SS - l, 4 * SS - t), text, font=f, fill=255)
    rl, rt, rr, rb = f.getbbox('한')
    return np.array(im), (4 * SS - t + rt, 4 * SS - t + rb)


def ink_box(m):
    ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
    if not len(ys):
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def coverage(text, fk, height, italic=0.0, maxw=None):
    """한 줄 → 1배 덮임(0~1), 기준 위치 top. 한글 높이 = height 화소, 넘치면 가로로 좁힘."""
    size = max(4, height)
    for _ in range(3):
        a, (y0, y1) = render_line(text, fk, size)
        size = max(4, int(round(size * height / max(1, (y1 - y0) / SS))))
    a, (y0, y1) = render_line(text, fk, size)
    xs = np.nonzero(a.max(0) > 0)[0]
    if len(xs):
        a = a[:, xs.min():xs.max() + 1]
    sc = height * SS / max(1, (y1 - y0))
    im = Image.fromarray(a)
    if italic:
        im = im.transform((int(im.width + im.height * italic) + 1, im.height), Image.AFFINE,
                          (1, italic, -im.height * italic, 0, 1, 0), Image.BILINEAR)
    W = im.width * sc / SS
    sx = maxw / W if maxw and W > maxw else 1.0
    nw = max(1, int(im.width * sc * sx / SS)); nh = max(1, int(round(im.height * sc / SS)))
    cov = np.array(im.resize((nw, nh), Image.BOX)).astype(float) / 255
    return cov, y0 * sc / SS, sx


def grey_dilate(c, k):
    for _ in range(k):
        p = np.pad(c, 1); h, w = c.shape
        o = c.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy or dx:
                    o = np.maximum(o, p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w])
        c = o
    return c


def groups(m, k):
    """원본 잉크 열을 큰 틈 k-1 개로 나눈 묶음(x0, x1)."""
    xs = np.nonzero(m.any(0))[0]
    if not len(xs):
        return []
    if k <= 1:
        return [(xs.min(), xs.max() + 1)]
    gaps = [(b - a, a, b) for a, b in zip(xs[:-1], xs[1:]) if b - a > 1]
    gaps = sorted(sorted(gaps, reverse=True)[:k - 1], key=lambda g: g[1])
    out = []; s = xs.min()
    for _, a, b in gaps:
        out.append((s, a + 1)); s = b
    out.append((s, xs.max() + 1))
    return out


def paste(canvas, cov, x, y):
    H, W = canvas.shape; h, w = cov.shape
    sx0 = max(0, -x); sy0 = max(0, -y)
    ex = min(w, W - x); ey = min(h, H - y)
    if ex <= sx0 or ey <= sy0:
        return
    canvas[y + sy0:y + ey, x + sx0:x + ex] = np.maximum(canvas[y + sy0:y + ey, x + sx0:x + ex], cov[sy0:ey, sx0:ex])


def layout(tex, st, text, o, pad, fk):
    """한글 «속 획» 덮임(텍스처 크기). pad = 뒤에 두를 테두리 화소 → 그만큼 작게·안쪽으로."""
    W, H = tex.w, tex.h
    x0, y0, x1, y1 = ink_box(st.ink)
    fk = o.get('font', fk); italic = o.get('italic', 0.0)
    canvas = np.zeros((H, W))
    if o.get('vert'):
        chars = [c for c in text if c.strip()]
        n = len(chars); cell = (y1 - y0) / n
        hgt = int(round(min(o.get('vw', x1 - x0), cell) * 0.85 * o.get('vscale', 1.0))) - 2 * pad
        for i, c in enumerate(chars):
            cov, top, _ = coverage(c, fk, max(4, hgt), 0, o.get('vw', x1 - x0) - 2 * pad)
            cy = int(round(y0 + cell * i + cell / 2 - (top + hgt / 2))); cx = int(round((x0 + x1 - cov.shape[1]) / 2))
            paste(canvas, cov, cx, cy)
        return canvas
    lines = text.split(o['lines']) if o.get('lines') else [text]
    if len(lines) > 1:
        rws = st.ink.any(1); bands = []; s = None
        for y in range(H + 1):
            v = rws[y] if y < H else False
            if v and s is None:
                s = y
            if not v and s is not None:
                bands.append((s, y)); s = None
        for ln, (b0, b1) in zip(lines, bands):
            sub = st.ink.copy(); sub[:b0] = False; sub[b1:] = False
            place_line(canvas, tex, sub, ln, fk, italic, pad, o.get('align'), getattr(st, 'rx', None))
        return canvas
    place_line(canvas, tex, st.ink, text, fk, italic, pad, o.get('align'), getattr(st, 'rx', None))
    return canvas


def place_line(canvas, tex, m, text, fk, italic, pad, align=None, rx=None):
    """rx = 구역 가로 범위(rx0, rx1) — 여러 구역 그림에서 그 구역 밖으로 안 나가게."""
    RX0, W = rx if rx else (0, tex.w)
    x0, y0, x1, y1 = ink_box(m)
    hgt = max(5, int(round((y1 - y0) * 0.92)) - 2 * pad)
    parts = text.split('　')
    gs = groups(m, len(parts))
    if len(parts) > 1 and len(gs) != len(parts):
        parts = [text.replace('　', '  ')]; gs = [(x0, x1)]
    L, R = x0 - RX0, W - x1
    for i, (pt, (g0, g1)) in enumerate(zip(parts, gs)):
        if len(parts) == 1:
            if L > 4 and R > 4 and (abs(L - R) <= 3 or abs(L - R) < 0.25 * (L + R)):
                al = 'c'
            else:
                al = 'l' if (L <= R or (L <= 4 and R <= 4)) else 'r'
            al = align or al
            lim0, lim1 = RX0 + 1 + pad, W - 1 - pad
        else:
            al = 'c'   # 여러 칸: 원본 칸 가운데에
            # 칸 경계 = 원본 틈 한가운데 ±3 (이웃 칸과 겹치지 않게)
            lim0 = ((gs[i - 1][1] + g0) // 2 + 3) if i else RX0 + 1 + pad
            lim1 = ((g1 + gs[i + 1][0]) // 2 - 3) if i < len(parts) - 1 else W - 1 - pad
        cov, top, sx = coverage(pt.strip(), fk, hgt, italic, lim1 - lim0)
        cw = cov.shape[1]
        if al == 'l':
            cx = g0 + pad
        elif al == 'r':
            cx = g1 - pad - cw
        else:
            cx = int(round((g0 + g1 - cw) / 2))
        cx = int(max(lim0, min(cx, lim1 - cw)))
        cy = int(round((y0 + y1) / 2 - (top + hgt / 2)))
        paste(canvas, cov, cx, cy)


def dil_bin(m):
    p = np.pad(m, 1); h, w = m.shape; o = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    return o


def colorize(st, cov, thr=0.15):
    """속 획 덮임 → 팔레트 번호.
    원본 거리 d 와 맞추기: 속 획 안 = R + 안쪽거리, 테두리 r 겹째 = R+1-r (획 사이 테두리는 공유돼 안 뭉친다)."""
    R = st.R
    core = cov >= 0.5
    dc = dist_in(core)
    # 속 획 가장자리(dc=1) = 원본 R+1 층(방향별 음영), 그 안쪽 = 원본 능선 층(속 색)
    top = int(max(R + 1, st.sw))
    kr = ridge_w(dc) if core.any() else 1
    if R == 0:
        # 테두리 없는 꼴: 꽉 찬 화소 = 속 색, 덜 찬 가장자리 = 안티에일리어스(덮임 순 분위)
        deq = np.where(core, np.where(cov >= 0.85, top, 1), 0)
    else:
        # 테두리 꼴: 속 획이 굵을 때만 가장자리(dc=1)를 원본 R+1 층(방향별 음영)으로
        edge1 = (dc <= 1) & (kr >= 2) & (not st.flat)
        deq = np.where(core, np.where(edge1, R + 1, top), 0)
    cur = core.copy()
    for r in range(1, R + 1):
        nx = dil_bin(cur) & ~cur
        deq[nx] = R + 1 - r; cur |= nx
    outer = grey_dilate(cov, R) if R else cov
    fringe = ~cur & (outer >= thr)          # 바깥 안티에일리어스
    deq[fringe] = 1
    m = deq > 0
    edge_c = np.where(cur & (deq > 1), 1.0, np.where(core, cov, outer))
    e = edge_cls(m); yb = ybin(m)
    out = np.full(cov.shape, st.bg, np.uint8) if st.base is None else st.base.copy()
    for y, x in zip(*np.nonzero(m)):
        dd = deq[y, x]
        if dd == 1 and st.edge_all and edge_c[y, x] < 0.999:
            q = st.edge_q.get(yb[y, x], st.edge_all)
            out[y, x] = q[min(len(q) - 1, int(edge_c[y, x] * len(q)))]
        else:
            out[y, x] = st.lut[(min(dd, CAP), e[y, x], yb[y, x])]
    return out


def best_core(st, fn, R=0, flat=False):
    """fn(pad, 글꼴) → 속 획 덮임. 테두리 겹 수 R 은 손 설정(OVR 'R', 기본 0 = 안티에일리어스 꼴).
    자동 추정은 한자·한글 획 구조 차이로 들쭉날쭉해서 버림(2026-10-17)."""
    fk = WEIGHTS[0]
    st.R = R; st.flat = flat
    return fk, fn(R, fk)


# ── 묶음 처리 ─────────────────────────────────────
def jobs():
    """(이름, 원문, 번역, [텍스처 이름...]) — MSG 는 조각 10장."""
    out = []
    for k, src, kr in rows():
        if k.startswith('MSG#'):
            a, b = map(int, k[4:].split('-'))
            out.append((k, src, kr, ['6DA800#%d' % i for i in range(a, b + 1)]))
        elif not kr.startswith('('):                     # 여정편 번호 = 텍스처 위치(«#» 없음)
            out.append((k, src, kr, [k]))
    return out


def wrap2(text, fk, hgt):
    """긴 설명문 → 두 줄. 띄어쓰기 단위, 긴 줄이 가장 짧게."""
    words = text.split(' '); best = None
    for i in range(1, len(words)):
        a = ' '.join(words[:i]); b = ' '.join(words[i:])
        sc = max(coverage(a, fk, hgt)[0].shape[1], coverage(b, fk, hgt)[0].shape[1])
        if best is None or sc < best[0]:
            best = (sc, a, b)
    return best[1], best[2]


def make(f, I, job):
    """→ [(Tex, 새 번호그림)]"""
    name, src, kr, texs = job
    T = [Tex(f, *I[t]) for t in texs]
    if name.startswith('MSG#'):
        # ★조각 10장 = 화면 아래를 흐르는 «한 줄» 띠(조각 1→10 이어짐). 두 줄×5 로 보면 반쪽마다 빈칸이 생겨 잘려 보임(2026-10-18 실기)
        st = Style(T[0]); n = len(T)
        W = sum(t.w for t in T[:n]); H = T[0].h
        y0, y1 = ink_box(st.ink)[1::2]
        out = []
        for li, ln in enumerate([kr]):
            def fn(pad, fk, ln=ln):
                hgt = int(round((y1 - y0) * 0.92)) - 2 * pad
                cov, top, _ = coverage(ln, fk, hgt, 0, W - 2 - 2 * pad)
                cv = np.zeros((H, W)); paste(cv, cov, 1 + pad, int(round((y0 + y1) / 2 - (top + hgt / 2))))
                return cv
            _, c = best_core(st, fn, OVR.get(name, {}).get('R', 0))
            x = 0
            for t in T[li * n:(li + 1) * n]:
                out.append((t, colorize(st, c[:, x:x + t.w]))); x += t.w
        return out
    t = T[0]; o = OVR.get(name, {})
    st = Style(t, fillpct=o.get('fillpct'))
    if not st.ink.any():
        return []
    if o.get('glow'):
        return [(t, glow(t, st, kr, o))]
    if o.get('multi'):
        # 한 그림 안 여러 구역: 구역마다 지우고 쓰기 (번역문은 OVR 에 구역별로)
        cur = t.idx.copy()
        for box, text, pidx, ro in o['multi']:
            rs = panel_style(t, box, pidx, cur, margin=ro.get('margin', 2))
            _, c = best_core(rs, lambda pad, fk: layout(t, rs, text, ro, pad, fk), ro.get('R', 0), ro.get('flat', False))
            cur = colorize(rs, c)
        return [(t, cur)]
    if o.get('panel'):
        st = panel_style(t, o['panel'], o.get('pidx'))
    elif (t.P[:, 3][t.idx] > 0).mean() > 0.6:
        # 여정편: 바탕판까지 불투명한 그림(HUD 글자·역 이름판 등) → 판 색 = 최빈 번호, 그 밖 = 글자 (2026-10-24)
        st = panel_style(t, (0, 0, t.w, t.h), o.get('pidx'))
    keep = 0
    if o.get('icon') or (kr[0] in SYM and src.startswith(kr[0])):
        # 맨 앞 기호(△○◎×■)는 원본 그림 그대로 — 기호 열 다음부터 한글
        cols = st.ink.any(0); x = int(np.argmax(cols)); gap = 0
        while x < t.w and gap < 3:
            gap = 0 if cols[x] else gap + 1; x += 1
        keep = x - gap
        while x < t.w and not cols[x]:
            x += 1
        lay = Style.__new__(Style); lay.__dict__.update(st.__dict__)
        lay.ink = st.ink.copy(); lay.ink[:, :x] = False
        kr = (kr if o.get('icon') else kr[1:]).strip(); o = dict(o, align=o.get('align', 'l'))
    else:
        lay = st
    _, c = best_core(st, lambda pad, fk: layout(t, lay, kr, o, pad, fk), o.get('R', 0), o.get('flat', False))
    idx = colorize(st, c)
    if keep:
        idx[:, :keep] = t.idx[:, :keep]
    return [(t, idx)]


def panel_style(t, box, pidx=None, cur=None, tight=False, margin=0):
    """판 위 글자(알약 배지·기계 이름표): 판 색 = 상자 안 최빈 번호, 글자 = 상자 안 판 색 아닌 화소.
    box = (x0, y0, x1, y1) 또는 'auto'(불투명 영역을 2px 깎은 안쪽). pidx = 판 번호(묶음이면 첫째로 메움),
    'clear' 면 상자 안 잉크 전부가 글자(투명으로 지움). cur = 앞 구역까지 고친 번호 그림."""
    if pidx == 'clear':
        x0, y0, x1, y1 = box; B = np.zeros(t.idx.shape, bool); B[y0:y1, x0:x1] = True
        text = B & (t.P[:, 3][t.idx] > 0)
        st = Style(t, ink=text)
        st.bg = int(np.argmin(t.P[:, 3]))
        st.base = (t.idx if cur is None else cur).copy(); st.base[text] = st.bg
        st.rx = (x0, x1)
        return st
    if isinstance(pidx, tuple):
        pset = pidx; pidx = pidx[0]
    else:
        pset = None
    rx = None
    if box == 'auto':
        B = dist_in(t.P[:, 3][t.idx] > 0) >= 3
    else:
        x0, y0, x1, y1 = box; B = np.zeros(t.idx.shape, bool); B[y0:y1, x0:x1] = True
        if pidx is not None and tight:
            # 대략 상자 → 판 번호 화소의 외접 상자(틀 선은 빠진다)
            P = B & (t.idx == pidx)
            rr = np.nonzero(P.sum(1) > 0.5 * P.sum(1).max())[0]; cc = np.nonzero(P.sum(0) > 0.5 * P.sum(0).max())[0]
            x0, y0, x1, y1 = cc.min(), rr.min(), cc.max() + 1, rr.max() + 1
            B[:] = False; B[y0:y1, x0:x1] = True
        rx = (x0, x1)
    if pidx is None:
        pidx = Counter(t.idx[B].tolist()).most_common(1)[0][0]
    Bi = B.copy()
    if box != 'auto' and margin:   # 글자 판정은 상자 가장자리 안쪽에서만(틀 그늘 화소 섞임 방지)
        Bi[:] = False; Bi[y0 + margin:y1 - margin, x0 + margin:x1 - margin] = True
    text = Bi & ~np.isin(t.idx, pset or (pidx,))
    st = Style(t, ink=text, ref=pidx)
    st.bg = pidx
    st.base = (t.idx if cur is None else cur).copy()
    st.base[B & ~np.isin(t.idx, pset or (pidx,))] = pidx   # 지우기는 상자 전체
    if pset:
        st.base[B & np.isin(t.idx, pset)] = pidx           # 판 무늬 색(틈새 회색 등)도 판 색 하나로
    st.rx = rx
    return st


def glow(t, st, kr, o):
    """흐린 빛 번짐판 — 바탕판(o['glow'] 번호)과 같은 배치의 한글을 부풀려 흐리고, 원본 번호를 «세기 순위»로 그대로 옮긴다."""
    from PIL import ImageFilter
    base = Tex(t._f, *index()[o['glow']]); bst = Style(base)
    c = layout(base, bst, kr, OVR.get(o['glow'], {}), 0, o.get('font', WEIGHTS[0]))
    im = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
    im = im.filter(ImageFilter.MaxFilter(o.get('grow', 7))).filter(ImageFilter.GaussianBlur(o.get('blur', 4)))
    v = np.array(im).astype(float).ravel()
    order = np.argsort(v, kind='stable')
    src = np.sort(st.strength[t.idx].ravel(), kind='stable')
    ranked = t.idx.ravel()[np.argsort(st.strength[t.idx].ravel(), kind='stable')]
    out = np.empty(v.size, np.uint8); out[order] = ranked
    return out.reshape(t.h, t.w)


def preview(prefixes):
    I = index(); f = open(S.ISO, 'rb')
    js = [j for j in jobs() if not prefixes or any(j[0].startswith(p) for p in prefixes)]
    tiles = []
    for j in js:
        for t, idx in make(f, I, j):
            tiles.append((j[0], t.rgba(), t.rgba(idx)))
    sc = 2; W = 1600; PH = 2000; pages = []
    BG = np.array([40, 30, 50])

    def flat(x):
        al = x[..., 3:4] / 255.0
        return (x[..., :3] * al + BG * (1 - al)).astype(np.uint8)
    y = x = rowh = 0
    cv = Image.new('RGB', (W, PH), (90, 90, 90)); dr = ImageDraw.Draw(cv)
    for nm, a, b in tiles:
        im = np.concatenate([flat(a), np.full((a.shape[0], 4, 3), 200, np.uint8), flat(b)], 1)
        im = Image.fromarray(im).resize((im.shape[1] * sc, im.shape[0] * sc), Image.NEAREST)
        if im.width > W:
            im = im.resize((W, int(im.height * W / im.width)), Image.NEAREST)
        if x + im.width > W:
            x = 0; y += rowh + 4; rowh = 0
        if y + im.height + 12 > PH and y > 0:
            pages.append(cv.crop((0, 0, W, y))); cv = Image.new('RGB', (W, PH), (90, 90, 90)); dr = ImageDraw.Draw(cv); y = 0
        dr.text((x + 2, y), nm, fill=(255, 255, 0))
        cv.paste(im, (x, y + 11)); x += im.width + 8; rowh = max(rowh, im.height + 12)
    pages.append(cv.crop((0, 0, W, y + rowh)))
    os.makedirs(os.path.join(ROOT, 'work/gfx'), exist_ok=True)
    for fn in os.listdir(os.path.join(ROOT, 'work/gfx')):
        if fn.startswith('prev_'):
            os.remove(os.path.join(ROOT, 'work/gfx', fn))
    for i, p in enumerate(pages):
        p.save(os.path.join(ROOT, 'work/gfx/prev_%d.png' % i))
    print('미리보기', len(tiles), '장', len(pages), '쪽')


def blobs():
    I = index(); f = open(S.ISO, 'rb'); out = []
    # 같은 그림이 TRAIN0 다른 묶음에 또 있음(25장 85벌, 화면마다 다른 묶음을 읽음) → 바이트가 같은 사본에도 똑같이 (2026-10-18)
    import json
    dp = os.path.join(ROOT, 'work', 'gfx', 'dups.json')
    D = {int(k, 16): [int(x, 16) for x in v] for k, v in json.load(open(dp)).items()} if os.path.exists(dp) else {}
    prim = {I[t][0] for j in jobs() for t in j[3] if t in I}   # 표에 따로 있는 자리는 그 번역을 따름(사본으로 덮지 않음)
    for j in jobs():
        for t, idx in make(f, I, j):
            b = t.encode(idx)
            out.append((t.off, b))
            f.seek(S.BASE + t.off); orig = f.read(len(b))
            for o2 in D.get(t.off, []):
                if o2 in prim:
                    continue
                f.seek(S.BASE + o2); assert f.read(len(b)) == orig, '사본 다름 %X' % o2
                out.append((o2, b))
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        preview(sys.argv[2:])
