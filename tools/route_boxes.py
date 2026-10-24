# -*- coding: utf-8 -*-
"""행선판(320×69) 칸 자동 측정 (2026-10-24): 왼쪽 이름판 = 안쪽 바탕 범위 안의 «가장 큰 글자 줄»(아래 로마자 줄 제외),
  오른쪽 띠 = 바탕 범위 안 첫 글자 덩어리(下り/上り) + 나머지(노선). mk_route_tsv 가 부른다."""
import numpy as np
from collections import Counter


def _runs(v):
    idx = np.nonzero(v)[0]
    if not len(idx): return []
    out = []; s = p = idx[0]
    for i in idx[1:]:
        if i - p > 1: out.append((int(s), int(p) + 1)); s = i
        p = i
    out.append((int(s), int(p) + 1)); return out


def inner(ix, x0, x1, y0, y1):
    """구역 안 가장 많은 번호(판 바탕)가 가로·세로로 이어진 안쪽 범위"""
    sub = ix[y0:y1, x0:x1]; bg = Counter(sub.ravel().tolist()).most_common(1)[0][0]
    m = sub == bg
    cols = [r for r in _runs(m.sum(0) >= max(3, 0.25 * (y1 - y0)))]; ca = max(cols, key=lambda r: r[1] - r[0])
    rows = [r for r in _runs(m[:, ca[0]:ca[1]].sum(1) >= 0.3 * (ca[1] - ca[0]))]; ra = max(rows, key=lambda r: r[1] - r[0])
    return bg, x0 + ca[0], y0 + ra[0], x0 + ca[1], y0 + ra[1]


def name_box(ix, x0, x1, y0=0, y1=44):
    bg, ax0, ay0, ax1, ay1 = inner(ix, x0, x1, y0, y1)
    ink = ix[ay0:ay1, ax0:ax1] != bg
    segs = _runs(ink.any(1))
    big = max(segs, key=lambda r: r[1] - r[0])      # 가장 큰 줄 = 이름(로마자는 낮음)
    cs = _runs(ink[big[0]:big[1]].any(0)); lx = cs[0][0]
    return (ax0, ay0 + big[0] - 1 if big[0] > 0 else ay0, ax1, ay0 + big[1] + (1 if big[1] < ay1 - ay0 else 0)), lx


def strip_boxes(ix, x0, x1, y0=0, y1=44):
    bg, ax0, ay0, ax1, ay1 = inner(ix, x0, x1, y0, y1)
    ink = ix[ay0:ay1, ax0:ax1] != bg
    cs = _runs(ink.any(0))
    # 첫 덩어리 = 下り/上り (세로로 긴 좁은 덩어리), 사이 간격 1~2 는 붙임
    merged = [list(cs[0])]
    for a, b in cs[1:]:
        if a - merged[-1][1] <= 2 and merged[-1][1] - merged[-1][0] < 10: merged[-1][1] = b
        else: merged.append([a, b])
    la, lb = merged[0]; ra = merged[1][0]
    return (ax0 + la - 1, ay0, ax0 + lb + 1, ay1), (ax0 + lb + 2, ay0, ax1, ay1)
