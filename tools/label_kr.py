# -*- coding: utf-8 -*-
r"""여정편 그림 글자(4bpp 텍스처) 한글 렌더러 (2026-10-24)
  «파이널» gfx_kr(꼴 학습)는 이 게임 HUD 글자에서 점무늬 바탕·검은 둘레·굵은 획을 못 따라가서 새로 짬.
  규칙(메모리 feedback_hud_pixel_style_match·graphic_erase_text_only):
   - 판정: 바탕 = 상자 가장자리에 나오는 번호(점무늬면 둘), 글자 = 그 밖. 글자 = 채움(밝은) + 둘레(바탕과 맞닿은 어두운) 번호.
   - 지우기: 글자 화소를 바탕 무늬대로 메움 — 바탕 번호를 (x+y)%2 칸마다 따로 세어 그 칸의 최빈 번호.
   - 그리기: 나눔고딕 ExtraBold 를 8배로 그려 덮임 ≥ 0.5 만 이진(중간 단계 없음). 획 굵기 = 원본 채움 획 폭(거리 변환)에 맞춰 부풀림.
     채움 색 = 원본 글자 줄(상대 높이)별 최빈 채움 번호, 둘레 = 원본에 있을 때만 같은 두께·같은 번호.
     자리 = 원본 잉크 상자(왼쪽 정렬이면 왼쪽, 아니면 가운데). 넓으면 가로만 좁힘(이진 다시).
  표 = work/text/ui_*.tsv (번호 = 텍스처 위치 16진 · 원문 · 번역 · 메모), 상자 지정 = 메모의 «box=x0,y0,x1,y1»(여러 구역은 «|» 로 번역도 나눔)
  python tools/label_kr.py preview [표 이름 접두…] → work/gfx/lab_N.png (원본 | 새것, 실제 색, 확대)"""
import os, re, struct, sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sub_dump as S  # noqa: E402

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
FONTS = {'M': r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoExtraBold.ttf'}
SS = 8


def index():
    d = {}
    for ln in open(os.path.join(ROOT, 'work/ui/index.tsv'), encoding='utf-8').read().split('\n')[1:]:
        a = ln.split('\t')
        if len(a) >= 4: d[a[0]] = (int(a[2], 16), int(a[3]))
    return d


class Tex:
    def __init__(self, f, off, size):
        self.off = off
        f.seek(S.BASE + off); self.blob = f.read(size)
        self.w, self.h = struct.unpack_from('<HH', self.blob, 2)
        self.n = 16 + 64 + self.w * self.h // 2
        assert 0 <= size - self.n < 16, '4bpp 아님 %X' % off
        self.P = np.frombuffer(self.blob[16:80], np.uint8).reshape(16, 4).astype(int)
        d = np.frombuffer(self.blob[80:self.n], np.uint8)
        self.idx = np.stack([d & 15, d >> 4], 1).ravel().reshape(self.h, self.w).copy()

    def rgba(self, idx=None):
        idx = self.idx if idx is None else idx
        P = self.P.copy(); P[:, 3] = np.minimum(255, P[:, 3] * 2)
        return P[idx].astype(np.uint8)

    def lum(self):
        return self.P[:, :3] @ np.array([0.3, 0.59, 0.11])

    def efflum(self):
        return self.lum() * np.clip(self.P[:, 3] / 128.0, 0, 1)

    def encode(self, idx):
        flat = idx.reshape(-1).astype(np.uint8)
        return self.blob[:80] + bytes((flat[0::2] | (flat[1::2] << 4)).tolist()) + self.blob[self.n:]


def dist_in(m):
    """잉크 안쪽 거리(4이웃 침식 횟수+1)."""
    d = np.zeros(m.shape, int); cur = m.copy(); k = 0
    while cur.any():
        k += 1; d[cur] = k
        n = cur.copy()
        n[1:] &= cur[:-1]; n[:-1] &= cur[1:]; n[:, 1:] &= cur[:, :-1]; n[:, :-1] &= cur[:, 1:]
        cur = n
    return d


def dilate(m, r):
    out = m.copy()
    for _ in range(r):
        n = out.copy()
        n[1:] |= out[:-1]; n[:-1] |= out[1:]; n[:, 1:] |= out[:, :-1]; n[:, :-1] |= out[:, 1:]
        out = n
    return out


def analyse(t, box, mode=None, inv=False):
    """상자 안 바탕·글자 판정 → dict(bg=칸별 바탕 번호, text 마스크, fill/outline 번호 등)
    mode='row': 줄마다 바탕이 다른 판(양피지 버튼 등) — 줄별 최빈 번호 = 바탕, 바탕과 밝기 차 > 20 = 글자."""
    x0, y0, x1, y1 = box
    sub = t.idx[y0:y1, x0:x1]
    lum = t.lum()
    yy, xx = np.mgrid[y0:y1, x0:x1]; par = (xx + yy) % 2
    if mode and mode.startswith('row'):
        rc = mode[3:]   # «mode=row225» = 줄별 바탕을 그림의 x=225 열에서(상자 가장자리가 판 밖·테두리에 걸릴 때)
        mg = t.idx[y0:y1, int(rc):int(rc) + 1] if rc else sub[:, list(range(6)) + list(range(sub.shape[1] - 6, sub.shape[1]))]   # 줄별 바탕 = 상자 좌우 가장자리 6열(글자 없음)의 최빈
        rowbg = np.array([Counter(r.tolist()).most_common(1)[0][0] for r in mg])
        text = np.abs(lum[sub] - lum[rowbg][:, None]) > 20
        erase = dilate(np.abs(lum[sub] - lum[rowbg][:, None]) > 6, 1)   # 옅은 번짐까지 지움
        bgset = sorted(set(rowbg.tolist())); bgpar = None
        bglum = float(np.mean(lum[rowbg]))
    else:
        rowbg = None; erase = None
        edge = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])
        c = Counter(edge.tolist()); tot = sum(c.values())
        bgset = [k for k, v in c.most_common() if v >= tot * 0.12][:2] or [c.most_common(1)[0][0]]
        if not t.P[bgset[0], 3] and len(bgset) > 1:   # 투명 바탕: 둘째가 점무늬(짝/홀 칸 한쪽에 몰림)일 때만 남김 — 아니면 그림 조각(신호기 잡티)
            ep = np.concatenate([par[0], par[-1], par[:, 0], par[:, -1]]); m2 = edge == bgset[1]
            if not m2.any() or max(ep[m2].mean(), 1 - ep[m2].mean()) < 0.8: bgset = bgset[:1]
        text = ~np.isin(sub, bgset)
        # 바탕 무늬: (x+y)%2 칸마다 최빈 바탕 번호
        bgpar = {}
        for p in (0, 1):
            v = sub[(par == p) & ~text]
            bgpar[p] = Counter(v.tolist()).most_common(1)[0][0] if len(v) else bgset[0]
        bglum = float(np.mean([lum[k] for k in bgset])) if t.P[bgset[0], 3] else None
    # 글자 번호를 둘로: 바탕과 차이가 큰 쪽 = 심(채움, 줄별 색), 작은 쪽 = 둘레·그림자·번짐(한 번호)
    tid = Counter(sub[text].tolist())
    if tid and bglum is not None:
        dist = {k: abs(lum[k] - bglum) for k in tid}
        dmin, dmax = min(dist.values()), max(dist.values())
        bright = {k for k in tid if dist[k] >= (dmin + dmax) / 2 or dmax - dmin < 40}
    elif tid:                                       # 투명 바탕: 밝은 쪽 = 채움
        lmin = min(lum[k] for k in tid); lmax = max(lum[k] for k in tid)
        bright = {k for k in tid if lum[k] >= (lmin + lmax) / 2 or lmax - lmin < 40}
    else:
        bright = set()
    if inv: bright = set(tid) - bright              # fill=dark: 어두운 쪽이 채움(안내 띠 — 사용자 «색반전»)
    core = text & np.isin(sub, list(bright))
    dark = text & ~core
    fill_ids = Counter(sub[core].tolist())
    main_fill = max(fill_ids, key=lambda k: fill_ids[k]) if fill_ids else None
    outline = None; ol_w = 0
    if dark.sum() >= 0.12 * max(1, text.sum()):
        dc = Counter(sub[dark].tolist()); outline = dc.most_common(1)[0][0]
        ws = []                                       # 둘레 두께 = 가로로 이어진 어두운 화소 수(중앙값)
        for r in range(sub.shape[0]):
            run = 0
            for v in dark[r]:
                if v: run += 1
                elif run: ws.append(run); run = 0
        ol_w = max(1, min(int(np.median(ws)) if ws else 1, 3))
    # 그림자 판정: 어두운 화소가 심의 아래·오른쪽에만 있으면 «그림자»(같은 방향·거리로), 사방이면 «둘레»
    shadow = None
    if outline is not None and core.any():
        sh = lambda m, dy, dx: np.roll(np.roll(m, dy, 0), dx, 1)
        up = (sh(core, -1, 0) & ~core).sum(); upd = (sh(core, -1, 0) & dark).sum()
        dn = (sh(core, 1, 0) & ~core).sum(); dnd = (sh(core, 1, 0) & dark).sum()
        if dn and dnd / dn > 2 * (upd / up if up else 0) + 0.2:
            best = max(((dy, dx) for dy in (1, 2) for dx in (0, 1, 2)),
                       key=lambda o: (sh(core, *o) & dark).sum() - (sh(core, *o) & ~text).sum())
            shadow = best
    d = dist_in(core)
    stroke = int(np.percentile(d[core], 90)) if core.any() else 1
    ys, xs = np.nonzero(text)
    ink = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else (0, 0, x1 - x0, y1 - y0)
    # 줄별 채움 번호(상대 높이 → 번호)
    ramp = []
    for r in range(ink[1], ink[3]):
        v = Counter(sub[r][core[r]].tolist())
        ramp.append(v.most_common(1)[0][0] if v else main_fill)
    # 위아래로 «한 방향» 바뀌는 명암만 줄별 색으로 — 원본 한자 획 명암이 한글에 가로 띠로 찍히던 것(사용자 «진행 오테마치에 가로줄» 2026-10-24)
    if ramp and None not in ramp:   # 글자 못 찾은 칸(main_fill None)은 건너뜀
        L = [lum[k] for k in ramp]
        ups = sum(1 for a, b in zip(L, L[1:]) if b > a + 1); downs = sum(1 for a, b in zip(L, L[1:]) if b < a - 1)
        if ups and downs: ramp = [main_fill] * len(ramp)
    # 안티에일리어스 글자 판정: 글자 번호가 바탕~채움 사이 밝기로 5단계 이상 고르게 있으면(역 이름판 등)
    aa = None
    eff = t.efflum()                                # 실효 밝기 = 밝기 × 불투명도(투명 바탕 = 0)
    ebg = float(np.mean([eff[k] for k in bgset]))
    if main_fill is not None and len(tid) >= 5 and not (mode or '').startswith('row'):
        fl = eff[main_fill]
        lvl = (eff[sub[text]] - ebg) / (fl - ebg + 1e-9)
        tv = sub[text]; mids = [k for k in tid if 0.15 < (eff[k] - ebg) / (fl - ebg + 1e-9) < 0.85 and (tv == k).mean() >= 0.03]
        if ((lvl > 0.15) & (lvl < 0.85)).mean() >= 0.25 and len(mids) >= 3:   # 중간 단계가 여러 번호로 고르게(테두리 글자는 둘레 번호 1~2개)
            aa = sorted(set(list(tid) + bgset), key=lambda k: eff[k])
    return dict(box=box, bgset=bgset, bgpar=bgpar, rowbg=rowbg, erase=erase, text=text, outline=outline, ol_w=ol_w, shadow=shadow, aa=aa, ebg=ebg, stroke=stroke,
                ink=ink, ramp=ramp, fill=main_fill)


GAL = r'C:\claude\utils\font\Galmuri-v2.40.3'
_BDF = {}


def bitmap_mask(text, h, name=None):
    """작은 글자(높이 ≤ 12): 갈무리 비트맵 그대로(축소·중간 단계 없음 — 메모리 feedback_hud_pixel_style_match)."""
    import bdf
    name = name or ('Galmuri11-Bold.bdf' if h >= 11 else 'Galmuri9.bdf' if h >= 9 else 'Galmuri7.bdf')
    if name not in _BDF: _BDF[name] = bdf.Font(os.path.join(GAL, name))
    pts, w = _BDF[name].draw(text)
    if not pts: return np.zeros((h, 1), bool)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for x, y in pts: m[y - min(ys), x - min(xs)] = True
    return m


def render_mask(text, h, w_max, stroke, font=None, italic=0.0, raw=False):
    """한글 한 줄 → 이진 마스크(높이 h = 잉크 높이)"""
    if not text.strip():
        return np.zeros((h, 1), bool)
    if h <= 12:
        # 폭에 들어가는 첫 갈무리(굵게 → 보통 → 좁은꼴 → 9 → 7). 잘라 넣지 않음.
        names = (['Galmuri11-Bold.bdf', 'Galmuri11.bdf', 'Galmuri11-Condensed.bdf'] if h >= 11 else []) + \
                (['Galmuri9.bdf'] if h >= 9 else []) + ['Galmuri7.bdf']
        m = None
        for nm in names:
            m = bitmap_mask(text, h, nm)
            if m.shape[1] <= w_max: break
        return m
    f = ImageFont.truetype(FONTS.get(font, FONT), int(h * SS * 1.25))
    im = Image.new('L', (int(len(text) * h * SS * 1.6) + 40 + int(h * SS * 2.2 * italic), int(h * SS * 2.2)), 0)
    ImageDraw.Draw(im).text((10 + int(h * SS * 2.2 * italic), 10), text, font=f, fill=255)
    if italic:                                      # 기울임(메뉴 항목·붓글씨 버튼)
        im = im.transform(im.size, Image.AFFINE, (1, italic, 0, 0, 1, 0), Image.BILINEAR)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    H, W = a.shape
    w = max(1, int(round(W * h / H)))
    if w > w_max: w = w_max
    big = Image.fromarray(a.astype(np.uint8) * 255).resize((w * SS, h * SS), Image.BILINEAR)
    cov = np.array(big, float).reshape(h, SS, w, SS).mean((1, 3)) / 255
    if raw: return cov                              # 안티에일리어스 글자용 덮임 비율
    m = cov >= 0.5
    # 획 굵기 맞추기: 원본 획(거리 변환 90 분위)보다 가늘면 부풀림
    cur = int(np.percentile(dist_in(m)[m], 90)) if m.any() else 1
    if stroke - cur >= 2:                           # 원본이 확실히 굵을 때만 1px
        m = dilate(m, 1)
    return m


def draw(t, an, kr, cur, align=None, opt=None):
    opt = opt or {}
    x0, y0, x1, y1 = an['box']; ix0, iy0, ix1, iy1 = an['ink']
    out = cur.copy()
    sub = out[y0:y1, x0:x1]
    yy, xx = np.mgrid[y0:y1, x0:x1]; par = (xx + yy) % 2
    er = an['erase'] if an['erase'] is not None else dilate(an['text'], 1)
    if an['rowbg'] is not None:                     # 줄별 바탕(명암 살림)
        for r in range(sub.shape[0]): sub[r][er[r]] = an['rowbg'][r]
    else:
        for p in (0, 1): sub[er & (par == p)] = an['bgpar'][p]
    olw = an['ol_w'] if an['outline'] is not None else 0
    if iy1 - iy0 <= 14 and not opt.get('ol'): olw = 0   # 작은 글자는 갈무리 그대로(둘레 넣으면 뭉개짐)
    if opt.get('ol') and an['outline'] is not None: olw = int(opt['ol'])
    if an.get('shadow'): olw = 0                    # 그림자는 높이·폭을 깎지 않음
    h = iy1 - iy0 - 2 * olw - (an['shadow'][0] if an.get('shadow') else 0)
    if opt.get('size'):                             # 범주 공통 글자 높이(원본 잉크 높이 중앙값) — 그림마다 크기 들쭉날쭉 막음
        h = int(opt['size']) - 2 * olw
        cy = (iy0 + iy1) / 2; iy0 = int(round(cy - int(opt['size']) / 2)); iy1 = iy0 + int(opt['size'])
        if iy0 < 0: iy1 -= iy0; iy0 = 0
        if iy1 > y1 - y0: iy0 -= iy1 - (y1 - y0); iy1 = y1 - y0; iy0 = max(0, iy0)
        h = min(h, iy1 - iy0 - 2 * olw)
    wmax = min((x1 - x0) - 2 - 2 * olw, max(ix1 - ix0, int((x1 - x0) * 0.9)))   # 판 끝에 닿지 않게(원본 잉크 폭 또는 90%)
    if opt.get('vert'):                             # 세로쓰기: 음절을 잉크 폭 정사각 칸에 하나씩, 높이에 고르게
        cw = max(ix1 - ix0, (x1 - x0) - 2) - 2 * olw;   # 세로쓰기 폭 = 상자 폭(원본 下 가 上 보다 좁아 가는 꼴로 떨어지던 것)
        chars = [c for c in kr if c.strip()]
        cell = min(cw, (h - (len(chars) - 1)) // max(1, len(chars)))
        ms = [render_mask(c, cell, cw, an['stroke']) for c in chars]
        gap = (h - sum(x.shape[0] for x in ms)) / max(1, len(ms) - 1) if len(ms) > 1 else 0
        W_ = max(x.shape[1] for x in ms); m = np.zeros((h, W_), bool); yy_ = 0.0
        for x in ms:
            o = (W_ - x.shape[1]) // 2; r0 = int(round(yy_)); m[r0:r0 + x.shape[0], o:o + x.shape[1]] |= x[:h - r0]
            yy_ += x.shape[0] + gap
    else:
        if opt.get('bmp'):                          # 범주 전체를 같은 갈무리 하나로(안내 띠 — 사용자 «원본은 다 같은 폰트인데 제각각»)
            m = bitmap_mask(kr, 14, opt['bmp'])
            if not opt.get('thin'):                 # 가로 1px 굵게(원본 획 2px) — thin: 굵은 꼴 그대로(차내 신호 «차내»가 «치니»로 뭉개짐)
                m = np.pad(m, ((0, 0), (0, 1))); m[:, 1:] |= m[:, :-1].copy()
        else:
            m = render_mask(kr, max(4, h), wmax, an['stroke'], opt.get('font'), float(opt.get('italic', 0)))
    mh, mw = m.shape
    left = align == 'l' or (align is None and ix0 <= 3)
    ox = (ix0 + olw) if left else int(round((ix0 + ix1) / 2 - mw / 2))
    ox = max(olw, min(ox, (x1 - x0) - mw - olw)); oy = iy0 + olw
    if opt.get('vc'): oy = max(0, ((y1 - y0) - mh) // 2)   # 상자 세로 가운데(화면 조정 버튼 — 갈무리가 위로 붙음)
    if an.get('aa') and not opt.get('vert') and not opt.get('bmp') and not opt.get('noaa') and h > 12:
        # 안티에일리어스 글자: 덮임 비율 → 바탕~채움 사이 목표 밝기 → 원본 글자에 쓰인 번호 중 가장 가까운 것
        cov = render_mask(kr, max(4, h), wmax, an['stroke'], opt.get('font'), float(opt.get('italic', 0)), raw=True)
        ch_, cw_ = cov.shape
        ox = (ix0 if left else int(round((ix0 + ix1) / 2 - cw_ / 2))); ox = max(0, min(ox, (x1 - x0) - cw_))
        C = np.zeros(sub.shape); C[oy:oy + ch_, ox:ox + cw_] = cov[:sub.shape[0] - oy, :sub.shape[1] - ox]
        lumP = t.efflum(); fl = lumP[an['fill']]; cand = np.array(an['aa']); cl = lumP[cand]
        for (r, c) in zip(*np.nonzero(C > 0.08)):
            tgt = an['ebg'] + C[r, c] * (fl - an['ebg'])
            sub[r, c] = cand[np.argmin(np.abs(cl - tgt))]
        out[y0:y1, x0:x1] = sub
        return out
    full = np.zeros(sub.shape, bool); full[oy:oy + mh, ox:ox + mw] = m[:sub.shape[0] - oy, :sub.shape[1] - ox]
    if an.get('shadow') and an['outline'] is not None:
        dy, dx = an['shadow']                       # 그림자: 오른쪽 아래로 민 모양만
        sm = np.zeros_like(full); sm[dy:, dx:] = full[:full.shape[0] - dy, :full.shape[1] - dx]
        sub[sm & ~full] = an['outline']
    elif olw:
        ring = dilate(full, olw) & ~full
        sub[ring] = an['outline']
    ramp = an['ramp']
    for r in range(sub.shape[0]):
        if not full[r].any(): continue
        k = min(len(ramp) - 1, max(0, int((r - oy) * len(ramp) / max(1, mh))))
        sub[r][full[r]] = ramp[k]
    out[y0:y1, x0:x1] = sub
    return out


def rows():
    out = []
    for fn in sorted(os.listdir(os.path.join(ROOT, 'work/text'))):
        if not fn.startswith('ui_'): continue
        for ln in open(os.path.join(ROOT, 'work/text', fn), encoding='utf-8').read().split('\n')[1:]:
            a = ln.split('\t')
            if len(a) >= 3 and a[2].strip(): out.append((fn, a[0], a[1], a[2], a[3] if len(a) > 3 else ''))
    return out


def wood_box(t):
    """나무 틀 버튼(메인 메뉴 등)의 안쪽 판. 왼쪽 가운데 줄에서 «틀 색·틀 안쪽 어두운 테» 두 덩이의 색 번호를 얻고,
    네 방향 끝에서 투명·그 색들을 건너뛴 자리가 판의 경계(아래·오른쪽은 그림자·틀 순서라도 같은 색들)."""
    ix = t.idx; a = t.P[:, 3][ix] > 0; cy = t.h // 2
    xs = [x for x in range(t.w) if a[cy, x]]; E = set(); x = xs[0]
    for _ in range(2):                                   # 틀, 어두운 테
        v = ix[cy, x]; E.add(int(v))
        while x < t.w and ix[cy, x] == v: x += 1
    skip = lambda v, al: (not al) or int(v) in E
    def edge(line, al):
        lo = 0
        while lo < len(line) and skip(line[lo], al[lo]): lo += 1
        hi = len(line)
        while hi > lo and skip(line[hi - 1], al[hi - 1]): hi -= 1
        return lo, hi
    x0, x1 = edge(ix[cy], a[cy])
    y0, y1 = edge(ix[:, x0 + 2], a[:, x0 + 2])
    return (x0, y0, x1, y1)


def plate_box(t, box, dens=0.6):
    """바깥 바탕(점무늬 등)과 다른 단색 판이 안쪽에 크게 있으면 그 판의 상자(通過駅 흰 판·停止位置 초록 판·過走 빨간 판).
    없으면 그대로. (2026-10-24 사용자 «통과역 원본 대비 색반전»)"""
    x0, y0, x1, y1 = box; sub = t.idx[y0:y1, x0:x1]
    edge = Counter(np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]]).tolist())
    c = Counter(sub[2:-2, 2:-2].ravel().tolist())
    found = []
    for k, n in c.most_common(4):
        if k in edge and edge[k] >= 0.4 * sum(edge.values()): continue   # 바깥 바탕(점무늬는 두 색이 각 50%)
        if n < 0.2 * sub[2:-2, 2:-2].size: continue
        ys, xs = np.nonzero(sub == k)
        bx_ = (x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1)
        area = (bx_[2] - bx_[0]) * (bx_[3] - bx_[1])
        if area >= 0.25 * sub.size and len(xs) >= dens * area: found.append((area, bx_))   # 판은 빽빽(밀도 0.66~0.8), 글자 채움색은 0.53 이하
    # 여럿이면 가장 안쪽 판(나무 틀 안 양피지 — 바깥 틀을 판으로 잡으면 버튼째 깨짐)
    return min(found)[1] if found else box


def draw_alpha(t, kr, cur, opt):
    """알파 계단 팔레트(같은 색, 번호마다 불투명도만 다름 — 브레이크 減圧·非常·加圧·保ち): 덮임 비율 → 불투명도가 가장 가까운 번호.
    일반 판정은 «밝은 = 글자»로 잡아 색이 뒤집힘(사용자 «색반전»)."""
    A = t.P[:, 3].astype(float) / 128; ix = t.idx
    bg = int(np.argmin(A))
    if opt.get('ramp'):                             # 색 계단(일시정지 메뉴 흰 글자 → 바탕색 쪽으로 흐려짐): 밝기로 덮임 비율
        from collections import Counter
        bg = Counter(ix.ravel().tolist()).most_common(1)[0][0]
        used = sorted(set(ix.ravel().tolist()) - {bg}); lum = t.P[:, :3].astype(float) @ (.299, .587, .114)
        fi = max(used, key=lambda i: lum[i]); A = np.full(16, 9.0)
        for i in used + [bg]: A[i] = (lum[i] - lum[bg]) / (lum[fi] - lum[bg])
    ys, xs = np.nonzero((ix != bg) if opt.get('ramp') else (A[ix] > 0.05))
    iy0, iy1, ix0, ix1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    ink = (ix != bg) if opt.get('ramp') else (A[ix] > 0.05)   # 알파 계단은 투명 번호가 여럿(11~15)
    out = cur.copy(); out[ink] = bg
    h = int(opt.get('size', iy1 - iy0))
    if opt.get('bmp'):   # 같은 줄 버튼들과 같은 갈무리 꼴(이름 입력 «선택» — 사용자 «나머지랑 크기 맞추고»)
        cov = bitmap_mask(kr, 11, opt['bmp']).astype(float)
    else:
        cov = render_mask(kr, h, max(ix1 - ix0, int(t.w * 0.9)), 0, opt.get('font'), float(opt.get('italic', 0)), raw=True)
    ch, cw = cov.shape
    oy = int(round((iy0 + iy1) / 2 - ch / 2)); ox = int(round((ix0 + ix1) / 2 - cw / 2))
    oy = max(0, min(oy, t.h - ch)); ox = max(0, min(ox, t.w - cw))
    if opt.get('bmp'): ox, oy = 1, max(0, (t.h - ch) // 2)   # 다른 이름 입력 버튼처럼 왼쪽·세로 가운데
    for (r, c) in zip(*np.nonzero(cov > 0.04)):
        out[oy + r, ox + c] = int(np.argmin(np.abs(A - cov[r, c])))
    return out


def draw_flat(t, cur, b, kr, vert, opt):
    """평판 칸(«box=…:f»): 칸 안 가장 많은 번호 = 판 색, 나머지 전부 글자로 보고 판 색으로 지운 뒤
    원본 글자 번호 중 판과 가장 대비 큰 것 한 색으로 씀(행선판 역 이름 — 테두리·안티에일리어스 판정이 판을 깨뜨림)."""
    x0, y0, x1, y1 = b; sub = cur[y0:y1, x0:x1]
    edge = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]])   # 판 바탕 = 칸 가장자리에 가장 많은 색(큰 글자가 빽빽하면 글자색이 최다)
    ec = Counter(edge.tolist()); tc = Counter(sub.ravel().tolist())
    cands = [k for k, c in ec.items() if c >= 0.25 * len(edge)] or [ec.most_common(1)[0][0]]
    bg = int(opt['bgi']) if opt.get('bgi') else max(cands, key=lambda k: tc[k])             # 가장자리에 넉넉히 있는 색 중 칸 전체 최다(테두리 회색 띠·빽빽한 글자색 배제)
    rbg = []                                         # 줄마다 바탕(두 톤 판 — 케이후쿠 위 회색·아래 흰색)
    lum0 = t.efflum()
    for r in sub:   # 줄 바탕 = 칸 양 끝 화소가 같고 판 바탕과 밝기가 비슷하면 그 색(띠 판), 아니면 판 바탕
        if opt.get('rows'):   # 줄 바탕 = 그 줄에서 판 바탕과 밝기 비슷한 색 중 최다(명암 띠 판 — 케이후쿠)
            rc = [(c, v) for v, c in Counter(r.tolist()).items() if abs(lum0[v] - lum0[bg]) < 60]
            rbg.append(max(rc)[1] if rc else bg)
        else: rbg.append(bg)
    rbg = np.array(rbg)[:, None]
    ink = sub != rbg
    if not ink.any() or not kr: return
    lum = t.efflum(); ys, xs = np.nonzero(ink); n = ink.sum()
    cnt = Counter(sub[ink].tolist()); cand = [k for k, c in cnt.items() if c >= 0.05 * n] or list(cnt)
    fill = int(opt['fi']) if opt.get('fi') else max(cand, key=lambda k: abs(lum[k] - lum[bg]))
    iy0, iy1 = ys.min(), ys.max() + 1
    sub[ink] = np.broadcast_to(rbg, sub.shape)[ink]
    W, H = x1 - x0, y1 - y0
    h = H if vert else min(int(opt['size']) if opt.get('size') else iy1 - iy0, H)   # 세로쓰기는 칸 전체 높이(원본 이름 길이 따라 글자 크기가 달라지던 것)
    if vert:
        chars = [c for c in kr if c.strip()]; cw = W - 2
        cell = min(cw, (h - (len(chars) - 1)) // max(1, len(chars)))
        if opt.get('cell'):   # 역 목록: 한 꼴(갈무리11 굵게)로 통일, 길면 글자 사이 0, 그래도 넘치면 9px
            n_ = len(chars)
            for nm_, cell, gp in (('Galmuri11-Bold.bdf', 11, 1), ('Galmuri11-Bold.bdf', 11, 0), ('Galmuri9.bdf', 9, 0), ('Galmuri7.bdf', 7, 0)):
                if n_ * (cell + gp) - gp <= h: break
            ms = [bitmap_mask(c, cell, nm_) for c in chars]
        else:
            ms = [render_mask(c, cell, cw, 0) for c in chars]
        gap = gp if opt.get('cell') else min(3, (h - sum(x.shape[0] for x in ms)) / max(1, len(ms) - 1)) if len(ms) > 1 else 0   # 글자 사이 최대 3px(칸이 길면 위아래로 벌어짐)
        hh = int(sum(x.shape[0] for x in ms) + gap * (len(ms) - 1)); Wm = max(x.shape[1] for x in ms); m = np.zeros((hh, Wm), bool); yy_ = 0.0
        for x in ms:
            o = (Wm - x.shape[1]) // 2; r0 = int(round(yy_)); m[r0:r0 + x.shape[0], o:o + x.shape[1]] |= x[:hh - r0]
            yy_ += x.shape[0] + gap
        if m.shape[0] > h:   # 넘치면 먼저 글자마다 위아래 빈 줄을 떼고 다시 쌓음(줄 솎기로 «마»의 ㅁ 윗변이 지워지던 것)
            ms2 = [x[np.nonzero(x.any(1))[0].min():np.nonzero(x.any(1))[0].max() + 1] if x.any() else x for x in ms]
            tot = sum(x.shape[0] for x in ms2); g2 = max(0, min(1, (h - tot) // max(1, len(ms2) - 1))) if len(ms2) > 1 else 0
            if tot <= h:
                m = np.zeros((h, Wm), bool); r0 = max(0, (h - tot - g2 * (len(ms2) - 1)) // 2) if not opt.get('top') else 0
                for x in ms2:
                    o = (Wm - x.shape[1]) // 2; m[r0:r0 + x.shape[0], o:o + x.shape[1]] |= x; r0 += x.shape[0] + g2
        while m.shape[0] > h:   # 바로 윗줄과 똑같은 줄부터 하나씩 뺌(획 모양은 그대로 — 고르게 솎으면 ㅁ 윗변이 사라짐)
            dup = [i for i in range(1, m.shape[0]) if m[i].any() and (m[i] == m[i - 1]).all()]
            if not dup: break
            m = np.delete(m, dup[len(dup) // 2], 0)
        if m.shape[0] > h:   # 그래도 넘치면 줄을 솎아 칸 높이에 맞춤(아래가 잘려 나가던 것 — 사용자 «아라시야마의 마 벗어남»)
            m = m[np.round(np.linspace(0, m.shape[0] - 1, h)).astype(int)]
    elif opt.get('bmp'):
        m = bitmap_mask(kr, 14, opt['bmp'])
    elif h <= 12:   # 작은 글자는 꼴 하나로 고정(폭 따라 굵게/보통이 바뀌면 판마다 굵기 들쭉날쭉)
        for nm in (['Galmuri11.bdf', 'Galmuri11-Condensed.bdf'] if h >= 11 else []) + ['Galmuri9.bdf', 'Galmuri7.bdf']:
            m = bitmap_mask(kr, h, nm)
            if m.shape[1] <= W: break
        else:   # 가장 작은 꼴도 넘치면 9px 꼴을 열 솎아 가로로 눌러 그림(자르지 않음)
            m = bitmap_mask(kr, h, 'Galmuri9.bdf')
            m = m[:, np.round(np.linspace(0, m.shape[1] - 1, W - 1)).astype(int)]
    else:
        m = render_mask(kr, max(4, h), W - 2, 0, opt.get('font'), float(opt.get('italic', 0)))
    mh, mw = m.shape; mh = min(mh, H); mw = min(mw, W); m = m[:mh, :mw]
    oy = 0 if opt.get('top') else max(0, (H - mh) // 2)   # 칸 세로 가운데(원본 잉크 중심을 따르면 판마다 위·아래로 붙음 — 사용자 지적)
    ox = max(0, (W - mw) // 2)
    if opt.get('oi'):   # 평판 글자에 둘레(효과음 — 빨간 글자 + 남색 테)
        full = np.zeros(sub.shape, bool); full[oy:oy + mh, ox:ox + mw] = m
        sub[dilate(full, 1) & ~full] = int(opt['oi'])
    sub[oy:oy + mh, ox:ox + mw][m] = fill


def make(f, I, key, kr, memo):
    t = Tex(f, *I[key])
    bx = re.findall(r'box=([0-9,]+)(:[a-z0-9]+)?', memo)     # «box=x0,y0,x1,y1:v» = 그 구역 세로쓰기, «:f» 평판, «:fv» 둘 다, «:f12» 평판+글자 높이
    if any('f' in v for _, v in bx):
        cur = t.idx.copy(); texts = kr.split('|')
        o2 = dict(re.findall(r'(font|italic|bmp|size|fi|cell|bgi|oi)=([\w.-]+)', memo))
        if re.search(r'(?:^| )top(?: |$)', memo): o2['top'] = True
        for bi, ((b, v), k) in enumerate(zip(bx, texts)):
            bb = tuple(map(int, b.split(',')))
            sz = re.search(r'\d+', v)
            o3 = dict(o2, size=sz.group()) if sz else dict(o2)
            if bi == 0:   # fi1/bgi1 = 첫 칸(역 이름판)에만
                for a_ in ('fi', 'bgi'):
                    m1 = re.search(r'(?:^| )%s1=(\d+)' % a_, memo)
                    if m1: o3[a_] = m1.group(1)
            if 'r' in v: o3['rows'] = True                  # «:fr» 줄별 바탕(띠 판)
            draw_flat(t, cur, bb, k.strip(), 'v' in v, o3)   # «:f» 가 하나라도 있으면 그 표 줄의 칸 전부 평판
        return t, cur
    bx = [(b, v) for b, v in bx]
    boxes = [(tuple(map(int, b.split(','))), v == ':v') for b, v in bx] or [((0, 0, t.w, t.h), 'vert' in memo)]
    texts = kr.split('|')
    al = re.search(r'align=(\w)', memo); al = al.group(1) if al else None
    md = re.search(r'mode=(\w+)', memo); md = md.group(1) if md else None
    opt = dict(re.findall(r'(font|italic|bmp|ol|size)=([\w.-]+)', memo))
    if 'noaa' in memo: opt['noaa'] = True
    if re.search(r'(?:^| )vc(?: |$)', memo): opt['vc'] = True
    if re.search(r'(?:^| )thin(?: |$)', memo): opt['thin'] = True
    cur = t.idx.copy()
    if 'alpha' in memo.split() or 'ramp' in memo.split():
        if 'ramp' in memo.split(): opt['ramp'] = True
        if bx:                                      # 구역마다(일시정지 메뉴 4칸)
            for (b, v), k in zip([(tuple(map(int, b.split(','))), 0) for b, _ in bx], texts):
                x0, y0, x1, y1 = b; sub = Tex.__new__(Tex); sub.__dict__.update(t.__dict__); sub.idx = cur[y0:y1, x0:x1]; sub.w, sub.h = x1 - x0, y1 - y0
                cur[y0:y1, x0:x1] = draw_alpha(sub, k.strip(), cur[y0:y1, x0:x1], opt)
            return t, cur
        return t, draw_alpha(t, kr, cur, opt)
    if not bx:
        boxes = [((wood_box(t) if 'wood' in memo else plate_box(t, boxes[0][0])), boxes[0][1])]
    fi = re.search(r'(?:^| )fi=(\d+)', memo); oi = re.search(r'(?:^| )oi=(\d+)', memo)   # 채움·둘레 번호 직접 지정(판정이 뒤집히는 그림)
    cl = re.findall(r'(?:^| )clear=(\d+),(\d+)', memo)   # 상자 안 번호 a → b 로 먼저 지움(글자 뒤 강조 판 — 選択 버튼 점 잔상), 여러 개 가능
    for (b, v), k in zip(boxes, texts):
        for a_, b2 in cl:
            s_ = cur[b[1]:b[3], b[0]:b[2]]; s_[s_ == int(a_)] = int(b2)
        an = analyse(t, b, md, 'fill=dark' in memo)
        if cl:   # 지운 판 색으로 바탕 고정(원본 판정은 바탕을 어두운 테로 잡아 판이 검게 칠해짐 — 車内信号)
            pb = int(cl[0][1]); an['bgpar'] = {0: pb, 1: pb}; an['rowbg'] = None
        if fi: an['fill'] = int(fi.group(1)); an['ramp'] = [int(fi.group(1))]
        if oi: an['outline'] = int(oi.group(1))
        # 묶음 통일(나무 버튼 — 사용자 «입문편 자료관 진동설정도 다른것들이랑 폰트 맞춰»): 획 굵기·둘레색(가장 가까운 색)·둘레 폭 고정
        sk = re.search(r'(?:^| )stroke=(\d+)', memo); oc = re.search(r'(?:^| )olc=(\d+),(\d+),(\d+)', memo)
        if sk: an['stroke'] = int(sk.group(1))
        if oc:
            tgt = np.array([int(x) for x in oc.groups()]); cand = [i for i in range(16) if t.P[i, 3] and i not in an['bgset']]
            an['outline'] = min(cand, key=lambda i: ((t.P[i, :3] - tgt) ** 2).sum()); an['ol_w'] = int(opt.get('ol', an['ol_w']))
        if re.search(r'(?:^| )bright(?: |$)', memo):   # 가장 밝은 번호 한 색·둘레 없음(화면 조정 버튼 — 下 판정이 분홍 둘레로 잡힘)
            lumP = t.P[:, :3] @ np.array([.3, .59, .11]); op = [i for i in range(16) if t.P[i, 3] > 100]
            b_ = max(op, key=lambda i: lumP[i]); an['fill'] = b_; an['ramp'] = [b_]; an['outline'] = None; an['shadow'] = None
        cur = draw(t, an, k.strip(), cur, al, dict(opt, vert=v))
    kp =re.search(r'(?:^| )keep=(\d+),(\d+),(\d+)', memo)
    if kp:   # 원본 화살표 그림(x0~x1)을 살려 한글 앞에 붙이고 둘을 함께 가운데로(사용자 «화살표 왜 안 고쳤어» — 한글 꼴 ↑ 이 작음)
        ax0, ax1, gap = map(int, kp.groups()); bx0, by0, bx1, by1 = boxes[0][0]
        rows_ = slice(by0, by1)                     # 줄마다 바탕(맨 윗줄은 테두리 밝은 띠)
        bg = np.array([Counter(r.tolist()).most_common(1)[0][0] for r in t.idx[rows_, bx0:bx1]])[:, None]
        arrow = t.idx[rows_, ax0:ax1].copy(); am = arrow != bg
        reg = cur[rows_, bx0:bx1]; cols = np.nonzero((reg != bg).any(0))[0]
        txt = reg[:, cols.min():cols.max() + 1].copy(); tm = txt != bg
        reg[:] = bg
        tw = txt.shape[1]; aw = ax1 - ax0; st = (bx1 - bx0 - (aw + gap + tw)) // 2
        reg[:, st:st + aw][am] = arrow[am]
        reg[:, st + aw + gap:st + aw + gap + tw][tm] = txt[tm]
    return t, cur


def preview(prefixes):
    I = index(); f = open(S.ISO, 'rb'); tiles = []
    for fn, key, src, kr, memo in rows():
        if prefixes and not any(fn[3:].startswith(p) for p in prefixes): continue
        t, idx = make(f, I, key, kr, memo)
        tiles.append((key, t.rgba(), t.rgba(idx)))
    BG = np.array([90, 90, 90]); sc = 3; W = 1800; pages = []; cv = None
    flat = lambda x: (x[..., :3] * (x[..., 3:4] / 255.0) + BG * (1 - x[..., 3:4] / 255.0)).astype(np.uint8)
    x = y = rowh = 0; cv = Image.new('RGB', (W, 2400), (60, 60, 60)); dr = ImageDraw.Draw(cv)
    for nm, a, b in tiles:
        im = np.concatenate([flat(a), np.full((a.shape[0], 3, 3), 255, np.uint8), flat(b)], 1)
        im = Image.fromarray(im); s = sc if im.width * sc <= W else max(1, W // im.width)
        im = im.resize((im.width * s, im.height * s), Image.NEAREST)
        if x + im.width > W: x = 0; y += rowh + 6; rowh = 0
        if y + im.height + 14 > 2400 and y:
            pages.append(cv.crop((0, 0, W, y))); cv = Image.new('RGB', (W, 2400), (60, 60, 60)); dr = ImageDraw.Draw(cv); y = 0
        dr.text((x + 2, y), nm, fill=(255, 255, 0)); cv.paste(im, (x, y + 12)); x += im.width + 10; rowh = max(rowh, im.height + 14)
    pages.append(cv.crop((0, 0, W, y + rowh)))
    os.makedirs(os.path.join(ROOT, 'work/gfx'), exist_ok=True)
    for fn in os.listdir(os.path.join(ROOT, 'work/gfx')):
        if fn.startswith('lab_'): os.remove(os.path.join(ROOT, 'work/gfx', fn))
    for i, p in enumerate(pages): p.save(os.path.join(ROOT, 'work/gfx', 'lab_%d.png' % i))
    print('미리보기 %d장 %d쪽' % (len(tiles), len(pages)))


if __name__ == '__main__':
    preview(sys.argv[2:])
