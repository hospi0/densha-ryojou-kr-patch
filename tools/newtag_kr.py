# -*- coding: utf-8 -*-
r"""자료관 목록 «NEW» 붙은 버튼(336×48, 35장) (2026-10-24)
  NEW 없는 같은 버튼(336×40, ui_lib.tsv 로 번역)을 그리고, 원본 48 판에서 NEW 화소(40 판과 다른 곳 + 아래 8줄)만 떼어
  한글 글자 끝 뒤 같은 간격 자리로 옮겨 붙인 뒤 48 판 팔레트로 맞춤(팔레트가 40 판과 다름).
  짝 = work/text_off/lib_new48.tsv(40 위치 · 48 위치).
  python tools/newtag_kr.py → work/gfx/prev_new48.png(원본 | 새것) · build.py 가 apply(out_iso)"""
import json, os, sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402


def pairs():
    return [l.split('\t') for l in open(os.path.join(ROOT, 'work/text_off/lib_new48.tsv'), encoding='utf-8').read().split('\n') if l]


def text_span(rgba):
    """글자 잉크(어두운 갈색) 열 범위 — 버튼 테(맨 위·아래 줄, 양 끝 열)는 뺌"""
    a = rgba[6:34, 6:-6].astype(int); lum = a[..., :3] @ np.array([.3, .59, .11])
    xs = np.nonzero(((lum < 120) & (a[..., 3] > 0)).any(0))[0] + 6
    return xs.min(), xs.max()


def make(f, I, rows, k40, k48):
    kr, memo = rows[k40]
    t40, cur40 = L.make(f, I, k40, kr, memo)
    t48 = L.Tex(f, *I[k48])
    o40, n40, o48 = t40.rgba().astype(int), t40.rgba(cur40).astype(int), t48.rgba().astype(int)
    # NEW 는 글자 길이와 상관없이 늘 같은 자리(원본 35장 모두 x≈250) → 옮기지 않고 그 자리 화소만 원본 48 판에서
    low = np.nonzero((o48[40:, :, 3] > 0).any(0))[0]; x0, x1 = low.min() - 2, low.max() + 3
    box = np.zeros(o48.shape[:2], bool); box[24:, x0:x1] = True   # NEW 상자(밖의 차이는 글자 렌더 차이 — 점 찌꺼기)
    tag = box & ((np.abs(o48 - np.concatenate([o40, o48[40:]], 0)).sum(-1) > 40) | (np.arange(48) >= 40)[:, None])
    want = o48.copy(); want[:40] = n40
    want[tag] = o48[tag]
    P = t48.P.astype(int); Pa = P.copy(); Pa[:, 3] = np.minimum(255, P[:, 3] * 2)
    clear = [i for i in range(16) if P[i, 3] == 0]
    d = np.abs(want[..., None, :3] - Pa[None, None, :, :3]).sum(-1) + np.abs(want[..., None, 3] - Pa[None, None, :, 3]) * 4
    idx = d.argmin(-1)
    if clear: idx[want[..., 3] == 0] = clear[0]
    keep = (want == o48).all(-1); idx[keep] = t48.idx[keep]   # 안 바뀐 화소는 원래 번호 그대로
    return t48, idx


def rows_lib():
    r = {}
    for fn, key, src, kr, memo in L.rows():
        if fn.startswith('ui_lib'): r[key] = (kr, memo)
    return r


def apply(out_iso):
    I = L.index(); f = open(S.ISO, 'rb'); R = rows_lib()
    canon = json.load(open(os.path.join(ROOT, 'work/gfx/canon.json')))
    dups = json.load(open(os.path.join(ROOT, 'work/gfx/dups.json')))
    n = 0
    with open(out_iso, 'r+b') as g:
        for k40, k48 in pairs():
            t, idx = make(f, I, R, k40, k48)
            blob = t.encode(idx); c = canon.get(k48, k48)
            for k in [c] + dups.get(c, []):
                off, size = I[k]
                f.seek(S.BASE + off); assert f.read(size) == t.blob, '사본 다름 %s' % k
                g.seek(S.BASE + off); g.write(blob); g.seek(S.BASE + off); assert g.read(len(blob)) == blob
                n += 1
    return n


def preview():
    I = L.index(); f = open(S.ISO, 'rb'); R = rows_lib(); tiles = []
    BG = np.array([90, 90, 90])
    flat = lambda x: (x[..., :3] * (x[..., 3:4] / 255.0) + BG * (1 - x[..., 3:4] / 255.0)).astype(np.uint8)
    for k40, k48 in pairs():
        t, idx = make(f, I, R, k40, k48)
        tiles.append(np.concatenate([flat(t.rgba()), np.full((48, 4, 3), 255, np.uint8), flat(t.rgba(idx))], 1))
        tiles.append(np.full((4, tiles[-1].shape[1], 3), 40, np.uint8))
    a = np.concatenate(tiles, 0)
    p = os.path.join(ROOT, 'work/gfx/prev_new48.png')
    Image.fromarray(a).resize((a.shape[1] * 2, a.shape[0] * 2), Image.NEAREST).save(p)


if __name__ == '__main__':
    preview()
