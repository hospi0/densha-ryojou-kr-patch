# -*- coding: utf-8 -*-
r"""입문편 노선 지도(TRAIN.SUB 846A7C80, 504×300 4bpp) 역 이름 한글화 (2026-10-24, 할일 11)
  - 글자 상자 = 검은 글자 덩어리(work 에서 잰 좌표, 아래 LABELS). 상자 안 «글자 번호»(검정·회색 계단)만 바탕(14)으로 지움 — 선·동그라미·녹지는 안 건드림.
  - 한글 = 갈무리 비트맵(11 굵게 → 11 좁게 → 9), 검정(1). 원래 상자 가운데 기준 ±24px 안에서 선·동그라미(바탕 아닌 화소)와 안 겹치는 자리 중 가장 가까운 곳.
  python tools/map_kr.py → work/gfx/prev_map.png(원본|새것 2배) · build.py 가 apply(out_iso)"""
import json, os, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402
from map_sprites import POS  # noqa: E402

KEY = '846A7C80'
BG, INK = 14, 1
TEXT = {1, 2, 3, 4, 6, 10, 12, 13}    # 글자 몸·계단(6 회색 포함 — 빼면 유령 글자). 3 진한 초록 = 녹지 위 글자 번짐(글자 상자 안에만 있음 — 켄쵸마에 얼룩·도고온센 초록 점). 15 흰색은 철길 점선이라 뺌
RAIL_COLS = (36, 37, 58, 59)          # 松山駅前 이 지나는 역 네모 세로 테(6) — 지운 뒤 다시 그림
LABELS = [   # (x0, y0, x1, y1, 한글) — 원본 글자 덩어리
    (217, 8, 256, 20, '키야초'), (98, 11, 159, 24, '혼마치 6초메'), (426, 11, 477, 24, '도고온센'),
    (350, 23, 399, 36, '헤이와도리'), (237, 25, 276, 38, '시미즈마치'), (293, 29, 332, 42, '텟포초'),
    (356, 38, 393, 50, '1초메'), (73, 45, 134, 58, '카야마치 6초메'), (399, 45, 426, 58, '미나미마치'),
    (196, 57, 235, 70, '타카사고초'), (321, 71, 359, 84, '세키쥬지'), (175, 73, 236, 86, '혼마치 5초메'),
    (84, 79, 111, 92, '코마치'), (435, 79, 474, 92, '코엔마에'), (321, 85, 360, 98, '뵤인마에'),
    (389, 86, 428, 98, '카미이치만'), (48, 109, 87, 122, '미야타초'), (390, 117, 441, 130, '케이사츠쇼마에'),
    (105, 119, 166, 132, '혼마치 4초메'), (257, 143, 296, 156, '켄쵸마에'), (101, 153, 162, 166, '혼마치 3초메'),
    (20, 155, 71, 168, '마츠야마에키마에'), (367, 175, 406, 188, '카츠야마초'), (297, 179, 335, 192, '오카이도'),
    (127, 199, 166, 212, '니시호리바타'), (271, 209, 322, 222, '시야쿠쇼마에'), (72, 231, 111, 244, '오테마치'),
    (219, 249, 258, 262, '미나미호리바타'), (164, 273, 203, 286, '시에키마에'),
]
# 지도 성 그림(낱장 — 강조 이름표 市駅前 등 3장은 ui_stname.tsv 에 이미 있음): (위치, 상자, 지울 번호, 바탕, 글자 번호, 한글) — 노란 JR 선(5)·성 그림은 안 건드림
EXTRA = [
    ('846BA420', (4, 4, 58, 17), set(range(0, 12)) - {12}, 12, 2, '마츠야마성'),
]
FONTS = (('Galmuri11.bdf', 12), ('Galmuri11-Condensed.bdf', 12))   # 전부 가는 꼴 한 높이(사용자 «이럴 거면 전부 가늘게» — 굵은/9px 섞여 크기 들쭉날쭉)
FONTS_EXTRA = (('Galmuri11-Bold.bdf', 12), ('Galmuri11-Condensed.bdf', 12), ('Galmuri9.bdf', 10))   # 성 그림(승인된 그대로)


OVERLAYS = {'846BAFC0': '오카이도', '846BB190': '시에키마에', '846BB410': '혼마치 6초메', '846BB870': '마츠야마에키마에', '846BAD70': '도고온센', '846BB6E0': '코마치'}   # 지도 위 빨간 강조 이름표 — 大街道·市駅前·本町六丁目·松山駅前 (ui_stname.tsv 에서 빼고 여기서 그림)
# (라벨 자리는 map_sprites.POS — 실행 파일 장면 표. 예전 추정·OVL_ART_DX 는 폐기)
OVL_DY, OVL_MX, OVL_MY = 1, 0, 2
RED_I = 2   # 한글 지도가 안 쓰는 번호(원래 글자 번짐) → 이름표 팔레트에서 빨강   # 실기: 가로는 딱 맞고 세로만 1px 아래
OVL_OUT = {}   # make() 가 채움: 이름표 키 → (Tex, 새 번호)


def overlay_rects():
    """빨간 강조 이름표(불투명 크림 판)가 지도 위에 찍히는 사각형: 원본 빨간 한자 가운데 = 원본 지도 검은 한자 상자 가운데.
    실기(2026-10-24 스샷 오카이도)로 보면 실제는 이 계산보다 1px 아래 → OVL_DY. 검은 글자는 이 판 안쪽 OVL_M px 여유 안에만 둠
    (판이 불투명하니 1~2px 어긋나도 안 보임 — 판 꽉 채워 그렸더니 윗줄이 판 밖으로 삐져나와 «검은 줄»)."""
    I = L.index(); f = open(S.ISO, 'rb'); out = {}
    for k, kr in OVERLAYS.items():
        t = L.Tex(f, *I[k])
        a = t.P[t.idx].astype(int); red = (a[..., 0] > 180) & (a[..., 1] < 120)
        ys, xs = np.nonzero(red)
        x0, y0, x1, y1, _ = [b for b in LABELS if b[4] == kr][0]
        mx, my = (x0 + 2 + x1 - 3) / 2, (y0 + 1 + y1 - 2) / 2            # 원본 지도 글자 상자(LABELS 는 좌우 2·위아래 1 부풀린 덩어리)
        px, py = POS[k]   # 실행 파일 장면 표(map_sprites) — 추정 안 씀
        out[kr] = (k, t, px, py)
    return out


def copy_label(mt, midx, tl, px, py, m, ox, oy, red_i):
    """강조 이름표 = 한글 지도 완성본에서 이름표 자리를 그대로 잘라 그 역 글자만 빨강(사용자 «덮어쓸 자리의 글자를 색 바꿔서 그대로»).
    이름표 팔레트를 지도 팔레트로 바꾸고, 지도가 안 쓰는 번호 red_i 를 빨강으로. 판이 지도 밖으로 나가면 바탕색."""
    import copy
    H, W = tl.h, tl.w; li = np.full((H, W), int(np.bincount(midx.ravel(), minlength=16).argmax()), np.uint8)
    y0, x0 = max(0, py), max(0, px); y1, x1 = min(mt.h, py + H), min(mt.w, px + W)
    li[y0 - py:y1 - py, x0 - px:x1 - px] = midx[y0:y1, x0:x1]
    mm = np.zeros((H, W), bool)
    ys, xs = np.nonzero(m)
    for y, x in zip(ys + oy - py, xs + ox - px):
        if 0 <= y < H and 0 <= x < W: mm[y, x] = True
    li[mm] = red_i
    pal = bytearray(mt.blob[16:80]); pal[red_i * 4:red_i * 4 + 4] = bytes((216, 22, 22, 128))
    nt = copy.copy(tl); nt.newpal = bytes(pal); nt.P = np.frombuffer(bytes(pal), np.uint8).reshape(16, 4).astype(int); nt.px, nt.py = px, py
    return nt, li


def label_idx(t, m, lx, ly):
    """강조 이름표 새 그림: 판 바탕(최다 번호)으로 다 지우고 지도와 같은 갈무리 글자를 가장 진한 빨강(1)으로 같은 자리에."""
    # 원본 라벨의 빨강 계열(글자·번짐)만 둘레 최빈 색으로 지움 — 라벨에 그려진 노란 선·역 네모는 그대로(사용자 «라벨이 맵 지우고 있다»)
    P = t.P[:, :3].astype(int); txt = ((P[:, 0] - P[:, 1]) > 15) & (np.abs(P[:, 1] - P[:, 2]) < 40)
    bg = int(np.bincount(t.idx.ravel(), minlength=16).argmax()); idx = t.idx.copy()
    for yy, xx in zip(*np.nonzero(txt[t.idx])):
        nb = t.idx[max(0, yy - 3):yy + 4, max(0, xx - 3):xx + 4].ravel(); nb = [v for v in nb if not txt[v]]
        idx[yy, xx] = max(set(nb), key=nb.count) if nb else bg
    red = int(np.argmin(P[:, 1] + P[:, 2] + (P[:, 0] < 180) * 10 ** 6))
    idx[ly:ly + m.shape[0], lx:lx + m.shape[1]][m] = red
    return idx


def make(t):
    idx = t.idx.copy()
    for x0, y0, x1, y1, _ in LABELS:
        s = idx[y0:y1 + 1, x0:x1]
        for yy, xx in zip(*np.nonzero(np.isin(s, list(TEXT)))):   # 글자 화소 → 둘레 7×7 의 글자 아닌 최빈 색(녹지 위 県庁前 가 크림색 판으로 남던 것 — 실기 지적)
            nb = t.idx[max(0, y0 + yy - 3):y0 + yy + 4, max(0, x0 + xx - 3):x0 + xx + 4].ravel()
            nb = [v for v in nb if v not in TEXT and v != 15]
            s[yy, xx] = max(set(nb), key=nb.count) if nb else BG
        for yy, xx in zip(*np.nonzero(s == BG)):   # 녹지 안 한자 획 사이 크림 점 → 3×3 이웃 대부분 녹지면 녹지(켄쵸마에)
            nb = idx[max(0, y0 + yy - 2):y0 + yy + 3, max(0, x0 + xx - 2):x0 + xx + 3]   # 5×5(두 화소짜리 점도)
            if (nb == 5).sum() >= 15: s[yy, xx] = 5
        s = idx[y0:y1 + 1, x0:x1]                       # 녹지 위 흰 글자(本町五丁目의 丁目·赤十字) → 둘레 다수 색(녹지 5 / 바탕)
        for yy, xx in zip(*np.nonzero(s == 15)):
            nb = idx[max(0, y0 + yy - 3):y0 + yy + 4, max(0, x0 + xx - 3):x0 + xx + 4].ravel()
            nb = [v for v in nb if v in (BG, 5)]
            if nb: s[yy, xx] = max(set(nb), key=nb.count)
    for x in RAIL_COLS: idx[155:168, x] = 6
    busy = ~np.isin(idx, [BG, 5, 3, 11, 8])             # 선·동그라미·다른 글자 자리(녹지·물·노란 JR 선 위 검정 글자는 읽힘 — 원본도 노란 선을 가로지름)
    cx_, cy_ = POS['846BA420']; ct_ = L.Tex(open(S.ISO, 'rb'), *L.index()['846BA420']); busy[cy_:cy_ + ct_.h, cx_:cx_ + ct_.w] = True   # 성 그림 판(지도 위에 따로 찍힘)
    ovl = overlay_rects(); pend = []
    for x0, y0, x1, y1, kr in LABELS:
        rect = ovl.get(kr)
        cx = (x0 + x1) / 2; best = None
        for fi, (fn, h) in enumerate(FONTS):
            m = L.bitmap_mask(kr, h, fn)
            ys = np.nonzero(m.any(1))[0]; m = m[ys.min():ys.max() + 1]
            mh, mw = m.shape
            pad = np.zeros((mh + 2, mw + 2), bool); pad[1:-1, 1:-1] = m; halo = L.dilate(pad, 1)
            pad2 = np.zeros((mh + 4, mw + 4), bool); pad2[2:-2, 2:-2] = m; halo2 = L.dilate(pad2, 2)
            if rect:   # 강조 이름표 판 안쪽(여유 OVL_M)만
                _, lt, px, py = rect
                cand = [(ox, oy) for ox in range(px + OVL_MX, px + lt.w - OVL_MX - mw + 1) for oy in range(py + OVL_MY, py + lt.h - OVL_MY - mh + 1)]
                ccx, ccy = px + lt.w / 2, py + lt.h / 2
            else:
                cand = [(int(round(cx - mw / 2)) + a, int(round((y0 + y1) / 2 - mh / 2)) + b) for a in range(-24, 25) for b in range(-3, 4)]   # 세로 ±3 도(카미이치만 — 옆 줄 코엔마에와 겹침)
                ccx, ccy = cx, (y0 + y1) / 2
            for ox, oy in cand:
                if ox < 1 or ox + mw + 1 >= t.w or oy < 1 or oy + mh + 1 >= t.h: continue
                if rect:   # 이름표 판 안: 동그라미·선과 2px 띄움(원본 市駅前 도 3px 떨어짐)
                    if ox < 2 or oy < 2: continue
                    hit = (busy[oy - 1:oy + mh + 1, ox - 1:ox + mw + 1] & halo).sum() + (busy[oy - 2:oy + mh + 2, ox - 2:ox + mw + 2] & halo2).sum() / 40
                else: hit = (busy[oy - 1:oy + mh + 1, ox - 1:ox + mw + 1] & halo).sum()
                dx, dy = ox + mw / 2 - ccx, oy + mh / 2 - ccy
                sc = hit * 100 + abs(dx) + abs(dy) * 4 + fi * 400   # 글꼴은 웬만하면 하나(굵기 들쭉날쭉 방지) · 이름표 판 안은 동그라미 피하기 우선(실기 «시에키마에 동그라미 가림»)
                if best is None or sc < best[0]: best = (sc, m, ox, oy)
        _, m, ox, oy = best
        idx[oy:oy + m.shape[0], ox:ox + m.shape[1]][m] = INK
        if rect: pend.append((rect[0], rect[1], rect[2], rect[3], m, ox, oy))
        busy[oy - 1:oy + m.shape[0] + 1, ox - 1:ox + m.shape[1] + 1] = True   # 다음 이름이 겹치지 않게
    for k_, tl_, px_, py_, m_, ox_, oy_ in pend:
        OVL_OUT[k_] = copy_label(t, idx, tl_, px_, py_, m_, ox_, oy_, RED_I)
    return idx


def make_extra(t, box, textset, bg, ink, kr):
    idx = t.idx.copy(); x0, y0, x1, y1 = box
    if textset == 'red':
        P = t.P.astype(int); r, g, b = P[:, 0], P[:, 1], P[:, 2]
        textset = {i for i in range(16) if P[i, 3] and r[i] > 200 and r[i] - b[i] > 40 and r[i] - g[i] > 30 and not (g[i] > 170 and b[i] < 110)}
        bg = int(np.bincount(t.idx.ravel(), minlength=16).argmax())
        ink = min(textset, key=lambda i: g[i] + b[i])
    s = idx[y0:y1, x0:x1]; s[np.isin(s, list(textset))] = bg
    W, H = x1 - x0, y1 - y0
    for fn, h in FONTS_EXTRA + (('Galmuri7.bdf', 8),):
        m = L.bitmap_mask(kr, h, fn); ys = np.nonzero(m.any(1))[0]; m = m[ys.min():ys.max() + 1]
        if m.shape[1] <= W - 2 and m.shape[0] <= H: break
    oy = y0 + (H - m.shape[0]) // 2; ox = x0 + (W - m.shape[1]) // 2
    idx[oy:oy + m.shape[0], ox:ox + m.shape[1]][m] = ink
    return idx


def jobs(f, I):
    t = L.Tex(f, *I[KEY]); yield KEY, t, make(t)
    for k in OVERLAYS: yield (k,) + OVL_OUT[k]
    for k, *a in EXTRA:
        t = L.Tex(f, *I[k]); yield k, t, make_extra(t, *a)


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
    I = L.index(); f = open(S.ISO, 'rb'); rows = []
    for key, t, idx in jobs(f, I):
        a = np.concatenate([t.rgba()[..., :3], np.full((t.h, 4, 3), 255, np.uint8), t.rgba(idx)[..., :3]], 1)
        if key != KEY: a = np.repeat(np.repeat(a, 3, 0), 3, 1)
        else: a = np.repeat(np.repeat(a, 2, 0), 2, 1)
        rows.append(np.pad(a, ((0, 8), (0, 2100 - a.shape[1]), (0, 0)), constant_values=60))
    Image.fromarray(np.concatenate(rows, 0)).save(os.path.join(ROOT, 'work/gfx/prev_map.png'))


if __name__ == '__main__':
    preview()
