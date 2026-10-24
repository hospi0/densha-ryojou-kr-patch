# -*- coding: utf-8 -*-
r"""노선 지도 3장 역 이름 한글화 (2026-10-24 — 이요 지도 map_kr 과 같은 규칙)
  에노덴 8463CB80 · 하코다테 84714C40 · 란덴 84780BE0 (504×300 4bpp).
  - 글자 덩어리 = map2_survey.blobs(검은 1·2 번호 연결 덩어리) — 순서대로 NAMES. 상자+1px 안 글자 번호(TEXT)를 둘레 최빈 색으로 지움.
  - 한글 = 갈무리11 보통(가는 꼴) 한 높이. 세로 원문은 세로(음절 하나씩 12px 간격), 가로 원문은 가로(안 들어가면 갈무리11 좁게).
    자리 = 원래 덩어리 근처에서 선·동그라미·다른 이름과 안 겹치는 곳(세로는 위·아래 끝 중 원래와 가까운 쪽 기준).
  - 빨간 강조 이름표(불투명 크림 판, ui_stname 에서 빼고 여기서 그림): 판 자리 = 원본 빨간 글자 가운데 ↔ 원본 검은 덩어리 가운데, 실기 보정 1px 아래(map_kr 과 같음).
    검은 글자는 판 안쪽(가로 0·세로 2px 여유)에만, 판이 작으면 그 판에 들어가는 꼴(11→9→7)로 줄임. 빨강도 같은 꼴·같은 자리.
  python tools/map2_kr.py → work/gfx/prev_map2_<위치>.png(원본|새것) · work/gfx/prev_map2_label.png · build.py 가 apply(out_iso)"""
import json, os, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402
from map2_survey import blobs  # noqa: E402
import map_kr as MK  # noqa: E402
from map_sprites import POS  # noqa: E402

BG = 12
MAPS = {
    '8463CB80': dict(sea=10, text={1, 2, 3, 4, 6, 9, 11}, names=[
        '쇼난카이간|코엔', '후지사와', '이시가미', '야나기코지', '쿠게누마', '에노시마', '코시고에', '카마쿠라코코마에', '시치리가하마',
        '이나무라가사키', '고쿠라쿠지', '하세', '유이가하마', '와다즈카', '카마쿠라'],
        ovl={'84650EB0': '후지사와', '84650B70': '카마쿠라', '84650CC0': '에노시마'}),
    '84714C40': dict(sea=9, text={1, 2, 3, 4, 5, 8, 10, 11}, names=[
        '하코다테도쿠마에', '야치가시라', '아오야기초', '오마치', '스에히로초', '호라이초', '쥬지가이', '우오이치바마에', '시야쿠쇼마에',
        '하코다테에키마에', '마츠카제초', '신카와초', '치토세초', '쇼와바시', '호리카와초', '치요가다이', '츄오뵤인마에', '고료카쿠코엔마에',
        '스기나미초', '카시와기초', '후카호리초', '케이바죠마에', '코마바샤코마에', '시민카이칸', '유노카와온센', '유노카와'],
        ovl={'847287E0': '유노카와', '847289B0': '코마바샤코마에', '84728C80': '고료카쿠코엔마에', '84728FD0': '하코다테도쿠마에', '84729320': '야치가시라'}),
    '84780BE0': dict(sea=None, text={1, 2, 3, 4, 5, 9, 10, 11}, names=[
        '아라시야마', '사가에키마에', '로쿠오인', '쿠루마자키', '아리스가와', '토키와', '카타비라노츠지', '나루타키', '타카오구치', '우즈마사',
        '오무로', '묘신지', '카이코노야시로', '료안지미치', '토지인', '야마노우치', '키타노하쿠바이초', '산조구치', '사이', '시조오미야'],
        ovl={'847945D0': '시조오미야', '84794840': '사이', '84794990': '카타비라노츠지', '84794BE0': '아라시야마', '84794D30': '키타노하쿠바이초'}),
}
OVL_DY, OVL_MX, OVL_MY = 1, 0, 2
# 지도 위에 따로 찍히는 사진 판(지도와 같은 배율): 자리 = 실기 스샷 실측. 이름은 이 영역을 피함(에노덴 «江ノ島» 판이 세로 이름을 가림 — 사용자)
PIC_POS = {'8463CB80': '8464F320', '84714C40': '847273E0', '84780BE0': '84793380'}   # 사진 판(자리 = map_sprites.POS)
# 사진 판 안 글자: (판, [(상자, 한글, 최대 폭)]) — 상자 안 바탕 아닌 화소를 지우고 가장 진한 초록(0)으로
PICS = {'8464F320': [((7, 10, 44, 24), '에노시마', 60)],
        '847273E0': [((97, 45, 137, 60), '고료카쿠', 60)],
        '84793380': [((13, 10, 54, 22), '토에이 우즈마사', 58), ((13, 22, 52, 37), '영화촌', 38)]}
TIGHT = {'시조오미야'}   # 판 안에서 간격을 줄여 선을 피함(사용자 «시조오미야 네모 침범»)
FREE = set()   # (2026-10-24) 5개를 키웠다가 라벨 판보다 길어 강조 때 판 밖이 검게 남음 → 사용자 «문제 있는 건 줄여야지», 전부 판에 드는 꼴로 되돌림   # 사용자 «공간 많아 작게 할 필요 없음» — 검은 글자는 일반 역처럼(판에 안 묶음), 빨간 판은 판에 맞는 작은 꼴 그대로
VFONTS = (('Galmuri11.bdf', 12, 2), ('Galmuri11.bdf', 12, 1), ('Galmuri9.bdf', 10, 2), ('Galmuri9.bdf', 10, 1), ('Galmuri7.bdf', 8, 2), ('Galmuri7.bdf', 8, 1))   # 음절 사이 0px 은 안 씀(붙어 뭉개짐) — 판이 작으면 꼴을 줄임
HFONTS = (('Galmuri11.bdf', 12, 0), ('Galmuri11-Condensed.bdf', 12, 0), ('Galmuri9.bdf', 10, 0))


def trim(m):
    ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def vmask(kr, fn, h, gap):
    """세로쓰기: 음절마다 글꼴 줄 높이 칸(위아래 공통 여백만 깎음)·가운데 정렬로 쌓음."""
    cs = [L.bitmap_mask(c, h, fn) for c in kr if c.strip()]
    W = max(c.shape[1] for c in cs); rows = []
    for i, c in enumerate(cs):
        o = (W - c.shape[1]) // 2; r = np.zeros((c.shape[0], W), bool); r[:, o:o + c.shape[1]] = c; rows.append(r)
        if gap and i < len(cs) - 1: rows.append(np.zeros((gap, W), bool))
    return trim(np.concatenate(rows, 0))


def hmask(kr, fn, h, gap=2):
    lines = [trim(L.bitmap_mask(s, h, fn)) for s in kr.split('|')]
    W = max(x.shape[1] for x in lines); rows = []
    for i, x in enumerate(lines):   # 두 줄(쇼난카이간/코엔) — 가운데 정렬, 줄 사이 2px
        o = (W - x.shape[1]) // 2; r = np.zeros((x.shape[0], W), bool); r[:, o:o + x.shape[1]] = x; rows.append(r)
        if i < len(lines) - 1: rows.append(np.zeros((gap, W), bool))
    return np.concatenate(rows, 0)


def masks(kr, vert, limit=None):
    """limit=(W,H) 면 그 안에 드는 첫 꼴(판 안), 없으면 첫 꼴."""
    for fn, h, gap in (VFONTS if vert else HFONTS):
        m = vmask(kr, fn, h, gap) if vert else hmask(kr, fn, h)
        if limit is None or (m.shape[1] <= limit[0] and m.shape[0] <= limit[1]): return m
    if vert and limit:   # 세로로도 안 들어가는 작은 판(16×32 아라시야마·카마쿠라): 한 줄 두 음절씩 가로로 쌓음(아라/시야/마)
        cs = [c for c in kr if c.strip()]
        for fn, h in (('Galmuri9.bdf', 10), ('Galmuri7.bdf', 8)):
            m = hmask('|'.join(''.join(cs[i:i + 2]) for i in range(0, len(cs), 2)), fn, h)
            if m.shape[1] <= limit[0] and m.shape[0] <= limit[1]: return m
    raise AssertionError('판에 안 들어감 %s' % kr)


def red_rect(t_lab, box):
    a = t_lab.P[t_lab.idx].astype(int); red = (a[..., 0] > 180) & (a[..., 1] < 120) & (a[..., 2] < 120)
    ys, xs = np.nonzero(red); x0, y0, x1, y1 = box
    px = int(round((x0 + x1 - 1) / 2 - (xs.min() + xs.max()) / 2)); py = int(round((y0 + y1 - 1) / 2 - (ys.min() + ys.max()) / 2)) + OVL_DY
    return px, py


def label_idx(t, m, lx, ly):
    lum = t.P[:, :3].astype(int)
    bg = int(np.argmin(((lum - np.array([239, 228, 207])) ** 2).sum(1) + (t.P[:, 3] == 0) * 10 ** 6))   # 크림 판 번호(작은 판은 빨강이 최다)
    red = int(np.argmin(lum[:, 1] + lum[:, 2] + (lum[:, 0] < 180) * 10 ** 6 + (t.P[:, 3] == 0) * 10 ** 6))
    # 원본 라벨의 빨강 계열(글자·번짐: r−g>15)만 둘레 최빈 색으로 지움 — 라벨에 그려진 바다·해안선(江ノ島·函館どっく前)은 그대로(사용자 «맵 다 지우는거야?»)
    txt = ((lum[:, 0] - lum[:, 1]) > 15) | ((np.abs(lum[:, 0] - lum[:, 1]) < 15) & (np.abs(lum[:, 1] - lum[:, 2]) < 15) & (lum[:, 0] < 200)); idx = t.idx.copy()   # 회색 = 바다 위 한자 번짐(江ノ島)
    for yy, xx in zip(*np.nonzero(txt[t.idx])):
        nb = t.idx[max(0, yy - 3):yy + 4, max(0, xx - 3):xx + 4].ravel(); nb = [v for v in nb if not txt[v]]
        idx[yy, xx] = max(set(nb), key=nb.count) if nb else bg
    idx[ly:ly + m.shape[0], lx:lx + m.shape[1]][m] = red
    return idx


def make(f, I, key):
    cfg = MAPS[key]; t = L.Tex(f, *I[key]); bs = blobs(t); names = cfg['names']
    assert len(bs) == len(names), (key, len(bs), len(names))
    idx = t.idx.copy(); T = cfg['text']
    for x0, y0, x1, y1 in bs:   # 지우기: 상자+1 안 글자 번호 → 둘레 7×7 의 글자 아닌 최빈 색(원본 기준)
        X0, Y0, X1, Y1 = max(0, x0 - 1), max(0, y0 - 1), x1 + 1, y1 + 1
        s = idx[Y0:Y1, X0:X1]
        for yy, xx in zip(*np.nonzero(np.isin(s, list(T)))):
            nb = t.idx[max(0, Y0 + yy - 3):Y0 + yy + 4, max(0, X0 + xx - 3):X0 + xx + 4].ravel()
            nb = [v for v in nb if v not in T]
            s[yy, xx] = max(set(nb), key=nb.count) if nb else BG
        sea = cfg['sea']
        if sea is not None:   # 바다 위 글자 번짐에 동그라미 파랑을 씀(極楽寺 의 寺) → 바다에 둘러싸인 파랑 점은 바다로
            blue = int(np.argmin(((t.P[:, :3].astype(int) - np.array([142, 173, 203])) ** 2).sum(1)))
            for yy, xx in zip(*np.nonzero(s == blue)):
                nb = idx[max(0, Y0 + yy - 2):Y0 + yy + 3, max(0, X0 + xx - 2):X0 + xx + 3]
                if (nb == sea).sum() >= 8: s[yy, xx] = sea
    lum = t.P[:, :3] @ np.array([.3, .59, .11])
    ok = [BG] + ([cfg['sea']] if cfg['sea'] is not None else []) + [i for i in range(16) if 195 <= lum[i] < 240 and i != BG]   # 바탕·바다·해안 번짐(밝은 색) 위엔 글자 가능 — 흰 철길 점선(13)은 안 됨
    busy = ~np.isin(idx, ok)
    if key in PIC_POS:
        pk = PIC_POS[key]; qx, qy = POS[pk]; pt_ = L.Tex(f, *I[pk]); pw, ph = pt_.w, pt_.h
        busy[max(0, qy):qy + ph, max(0, qx):qx + pw] = True
    rects = {}
    for lk, kr in cfg['ovl'].items():
        tl = L.Tex(f, *I[lk]); px, py = POS[lk]   # 실행 파일 장면 표(map_sprites)
        rects[kr] = (lk, tl, px, py)
    labs = {}; names_px = np.zeros(idx.shape, bool); pend = []
    order = sorted(range(len(bs)), key=lambda i: (names[i] not in rects, len(names[i])))   # 판 안 이름 먼저, 그다음 짧은 이름부터(긴 이름이 남은 자리로 비켜 감 — 야마노우치·산조구치)
    for i in order:
        kr = names[i]; x0, y0, x1, y1 = bs[i]; vert = (y1 - y0) > (x1 - x0) and '|' not in kr
        r = rects.get(kr)
        def place(m, cand, ref):
            mh, mw = m.shape
            pad = np.zeros((mh + 2, mw + 2), bool); pad[1:-1, 1:-1] = m; halo = L.dilate(pad, 1); best = None
            P = 5; pad5 = np.zeros((mh + 2 * P, mw + 2 * P), bool); pad5[P:-P, P:-P] = m; near = L.dilate(pad5, P)
            for ox, oy in cand:
                if ox < 1 or oy < 1 or ox + mw + 1 >= t.w or oy + mh + 1 >= t.h: continue
                hit = (busy[oy - 1:oy + mh + 1, ox - 1:ox + mw + 1] & halo).sum()
                nb = names_px[max(0, oy - P):oy + mh + P, max(0, ox - P):ox + mw + P]
                nr = (nb & near[P - (oy - max(0, oy - P)):P - (oy - max(0, oy - P)) + nb.shape[0], P - (ox - max(0, ox - P)):P - (ox - max(0, ox - P)) + nb.shape[1]]).sum()
                sc = hit * 100 + nr * 2 + ref(ox, oy, mh, mw)   # 다른 이름과 5px 안으로 붙으면 감점(야마노우치+산조구치 «치» 가 한 낱말처럼 읽힘)
                if best is None or sc < best[0]: best = (sc, ox, oy, hit)
            return best
        best = None; lab_only = None
        if r:
            lk, tl, px, py = r
            m = masks(kr, vert, (tl.w - 2 * OVL_MX, tl.h - 2 * OVL_MY)); mh, mw = m.shape
            cand = [(ox, oy) for ox in range(px + OVL_MX, px + tl.w - OVL_MX - mw + 1) for oy in range(py + OVL_MY, py + tl.h - OVL_MY - mh + 1)]
            best = place(m, cand, lambda ox, oy, mh, mw: abs(ox + mw / 2 - (px + tl.w / 2)) + abs(oy + mh / 2 - (py + tl.h / 2)))
            if kr in TIGHT and best[3]:   # 판 안에서 선을 덮음(시조오미야 — 노란 네모 가로선) → 판에 드는 다른 간격·꼴 중 안 겹치는 것
                for fn, h, gap in VFONTS:
                    m_ = vmask(kr, fn, h, gap)
                    if m_.shape[1] > tl.w - 2 * OVL_MX or m_.shape[0] > tl.h - 2 * OVL_MY: continue
                    mh_, mw_ = m_.shape
                    c_ = [(ox, oy) for ox in range(px + OVL_MX, px + tl.w - OVL_MX - mw_ + 1) for oy in range(py + OVL_MY, py + tl.h - OVL_MY - mh_ + 1)]
                    b_ = place(m_, c_, lambda ox, oy, mh, mw: abs(ox + mw / 2 - (px + tl.w / 2)) + abs(oy + mh / 2 - (py + tl.h / 2)))
                    if b_ and b_[3] < best[3]: best, m = b_, m_
                    if best[3] == 0: break
            if kr in FREE:   # 빨간 판만 이 꼴·자리로, 검은 글자는 아래 일반 규칙으로
                lab_only = (r, m, best[1], best[2]); r = None; best = None
        if r: pass
        elif vert:   # 세로: 동그라미 쪽 끝(원본 위/아래 띠에 선·동그라미가 더 많은 쪽)을 원래 자리에 고정, 반대쪽으로 늘어남. 지도 끝에 걸리면 음절 간격 2→1→0
            cx = (x0 + x1) / 2; xa, xb = max(0, x0 - 2), x1 + 2
            blue = int(np.argmin(((t.P[:, :3].astype(int) - np.array([142, 173, 203])) ** 2).sum(1)))   # 동그라미 파랑만 셈(선로를 세면 야마노우치·산조구치 방향이 뒤집힘)
            BD = 12
            up = (t.idx[max(0, y0 - BD):y0, xa:xb] == blue).sum(); dn = (t.idx[y1:y1 + BD, xa:xb] == blue).sum()
            if up == dn == 0 and kr in FREE:   # 동그라미가 멀리 있음(카마쿠라) — 이 세 이름만 넓게(다른 역은 손대지 않음)
                BD = 30; up = (t.idx[max(0, y0 - BD):y0, xa:xb] == blue).sum(); dn = (t.idx[y1:y1 + BD, xa:xb] == blue).sum()
            # 동그라미 위치(원래 이름 쪽 띠에서 찾은 파랑 중심) — 반대쪽으로 뒤집을 때 기준
            ys_, xs_ = np.nonzero(t.idx[max(0, y0 - BD):y0, xa:xb] == blue) if up >= dn else np.nonzero(t.idx[y1:y1 + BD, xa:xb] == blue)
            for side, gap in ((0, 2), (0, 1), (1, 2), (1, 1)):   # 원래 쪽 → (자리 없으면) 동그라미 건너편 세로(야마노우치: 선로와 동그라미 사이가 좁음)
                m_ = vmask(kr, 'Galmuri11.bdf', 12, gap); mh, mw = m_.shape
                below = (up >= dn) != bool(side)
                if side:   # 건너편: 동그라미 반대쪽 끝에서 4px 띄움
                    if not len(ys_): continue
                    ccy = (max(0, y0 - BD) if up >= dn else y1) + ys_.mean()
                    ys0 = int(ccy + 17) if below else int(ccy - 17) - mh   # 띠 안 파랑 평균은 동그라미 한쪽 테 → 지름(16)+1 만큼 건너감
                else: ys0 = y0 if below else y1 - mh
                DX = 12 if side else 3   # 건너편은 옆으로 더 비켜설 수 있음(야마노우치 아래 노란 JR 선)
                if below: cand = [(int(round(cx - mw / 2)) + dx, ys0 + dy) for dx in range(-DX, DX + 1) for dy in range(-2, 9)]; ref = (lambda a, pen: lambda ox, oy, mh, mw: abs(oy - a) * 3 + abs(ox + mw / 2 - cx) * 4 + pen)(ys0, side * 30)
                else: cand = [(int(round(cx - mw / 2)) + dx, ys0 + dy) for dx in range(-DX, DX + 1) for dy in range(-8, 3)]; ref = (lambda a, pen: lambda ox, oy, mh, mw: abs(oy - a) * 3 + abs(ox + mw / 2 - cx) * 4 + pen)(ys0, side * 30)
                b_ = place(m_, cand, ref)
                if b_ and (best is None or b_[3] < best[3]): best, m = b_, m_
                if best and best[3] == 0: break
            if best is None or best[3]:   # 세로로 안 들어감(지도 끝 — 고쿠라쿠지): 같은 동그라미 쪽에 가로쓰기
                m_ = hmask(kr, 'Galmuri11.bdf', 12); mh, mw = m_.shape
                if up >= dn: cand = [(int(round(cx - mw / 2)) + dx, y0 + dy) for dx in range(-20, 21) for dy in range(-2, 30)]; ref = lambda ox, oy, mh, mw: abs(oy - y0) * 3 + abs(ox + mw / 2 - cx)
                else: cand = [(int(round(cx - mw / 2)) + dx, y1 - mh + dy) for dx in range(-20, 21) for dy in range(-30, 3)]; ref = lambda ox, oy, mh, mw: abs(oy + mh - y1) * 3 + abs(ox + mw / 2 - cx)
                b_ = place(m_, cand, ref)
                if b_ and (best is None or b_[3] < best[3]): best, m = b_, m_
        else:        # 가로: 왼쪽 끝/오른쪽 끝 중 가까운 쪽, 세로 ±4
            m = masks(kr, vert); mh, mw = m.shape; cy = (y0 + y1) / 2
            cand = [(x0 + dx, int(round(cy - mh / 2)) + dy) for dx in range(-30 - mw, 31) for dy in range(-4, 5)]
            best = place(m, cand, lambda ox, oy, mh, mw: min(abs(ox - x0), abs(ox + mw - x1)) + abs(oy + mh / 2 - cy) * 4)
        assert best, kr
        _, ox, oy, _ = best; mh, mw = m.shape
        idx[oy:oy + mh, ox:ox + mw][m] = 1; names_px[oy:oy + mh, ox:ox + mw] |= m
        busy[oy - 1:oy + mh + 1, ox - 1:ox + mw + 1] = True
        if r: pend.append((r[0], r[1], r[2], r[3], m, ox, oy))
        if lab_only: pend.append((lab_only[0][0], lab_only[0][1], lab_only[0][2], lab_only[0][3], m, ox, oy))   # 키운 이름도 그 자리 글자 그대로 빨강
    for lk_, tl_, px_, py_, m_, ox_, oy_ in pend:
        labs[lk_] = MK.copy_label(t, idx, tl_, px_, py_, m_, ox_, oy_, 14)   # 14 = 세 지도 모두 안 쓰는 번호
    return t, idx, labs


def pic_idx(t, items):
    idx = t.idx.copy()
    for (x0, y0, x1, y1), kr, mw in items:
        s_ = idx[y0:y1, x0:x1]; bg = np.bincount(s_.ravel(), minlength=16).argmax(); s_[:] = bg
        for fn, h in (('Galmuri11-Bold.bdf', 12), ('Galmuri11-Condensed.bdf', 12), ('Galmuri9.bdf', 10)):
            m = trim(L.bitmap_mask(kr, h, fn))
            if m.shape[1] <= mw and m.shape[0] <= y1 - y0: break
        oy = y0 + (y1 - y0 - m.shape[0]) // 2; ox = x0
        idx[oy:oy + m.shape[0], ox:ox + m.shape[1]][m] = 0
    return idx


def jobs(f, I):
    for key in MAPS:
        t, idx, labs = make(f, I, key); yield key, t, idx
        for lk, (tl, li) in labs.items(): yield lk, tl, li
    for pk, items in PICS.items():
        t = L.Tex(f, *I[pk]); yield pk, t, pic_idx(t, items)


def apply(out_iso):
    I = L.index(); f = open(S.ISO, 'rb')
    canon = json.load(open(os.path.join(ROOT, 'work/gfx/canon.json')))
    dups = json.load(open(os.path.join(ROOT, 'work/gfx/dups.json')))
    n = 0
    with open(out_iso, 'r+b') as g:
        for key, t, idx in jobs(f, I):
            blob = t.encode(idx); c = canon.get(key, key)
            if getattr(t, 'newpal', None): blob = blob[:16] + t.newpal + blob[80:]   # 이름표: 지도 팔레트
            for k in [c] + dups.get(c, []):
                off, size = I[k]
                f.seek(S.BASE + off); assert f.read(size) == t.blob, '사본 다름 %s' % k
                g.seek(S.BASE + off); g.write(blob); g.seek(S.BASE + off); assert g.read(len(blob)) == blob
                n += 1
    return n


def preview():
    I = L.index(); f = open(S.ISO, 'rb'); lab_tiles = []
    for key in MAPS:
        t, idx, labs = make(f, I, key)
        a = np.concatenate([t.rgba()[..., :3], np.full((t.h, 6, 3), 255, np.uint8), t.rgba(idx)[..., :3]], 1)
        Image.fromarray(np.repeat(np.repeat(a, 2, 0), 2, 1)).save(os.path.join(ROOT, 'work/gfx/prev_map2_%s.png' % key))
        base = t.rgba(idx)[..., :3]
        for lk, (tl, li) in labs.items():   # 이름표 얹은 모습: 계산 자리 | 1px 위 | 이름표 없음
            px, py = tl.px, tl.py
            row = []
            for dy in (0, -1, None):
                im = base.copy()
                if dy is not None: im[py + dy:py + dy + tl.h, px:px + tl.w] = tl.rgba(li)[..., :3]
                y0_, x0_ = max(0, py - 10), max(0, px - 14)
                c = im[y0_:py + tl.h + 10, x0_:px + tl.w + 14]
                row.append(np.pad(c, ((0, 120 - c.shape[0]), (0, 4), (0, 0)), constant_values=60))
            lab_tiles.append(np.concatenate(row, 1))
    W = max(x.shape[1] for x in lab_tiles)
    tiles = [np.pad(x, ((0, 0), (0, W - x.shape[1] + 8), (0, 0)), constant_values=40) for x in lab_tiles]
    rows = [np.concatenate(tiles[i:i + 4] + [np.full_like(tiles[0], 40)] * (4 - len(tiles[i:i + 4])), 1) for i in range(0, len(tiles), 4)]
    sh = np.concatenate(rows, 0)
    Image.fromarray(np.repeat(np.repeat(sh, 3, 0), 3, 1)).save(os.path.join(ROOT, 'work/gfx/prev_map2_label.png'))


if __name__ == '__main__':
    preview()
