# -*- coding: utf-8 -*-
r"""강조 라벨 자리 규칙(2026-10-24, 실기 4곳으로 맞춤 — 오카이도·고료카쿠코엔마에 스샷, 혼마치 6초메·마츠야마에키마에 라벨에 그려진 선):
  원본 빨간 한자 잉크 상자의 «역 동그라미 쪽» 가장자리를 원본 검은 한자 잉크 상자의 같은 가장자리에 맞추고(위 −2 / 아래 +2 / 오른쪽 −1 / 왼쪽 +1),
  다른 축은 가운데. 실측 4곳 오차 ≤2px."""
import numpy as np


def red_ink(tl):
    a = tl.P[tl.idx].astype(int); r = (a[..., 0] > 180) & (a[..., 1] < 120) & (a[..., 2] < 120)
    ys, xs = np.nonzero(r); return xs.min(), xs.max(), ys.min(), ys.max()


def rule_rect(tl, black, circles):
    """black = (x0, x1, y0, y1) 원본 검은 한자 잉크(포함 끝). circles = [(cx, cy)]. → (px, py)"""
    rx0, rx1, ry0, ry1 = red_ink(tl); bx0, bx1, by0, by1 = black
    bcx, bcy = (bx0 + bx1) / 2, (by0 + by1) / 2
    cx, cy = min(circles, key=lambda c: (c[0] - bcx) ** 2 + (c[1] - bcy) ** 2)
    dx = 0 if bx0 <= cx <= bx1 else (cx - bx1 if cx > bx1 else cx - bx0)
    dy = 0 if by0 <= cy <= by1 else (cy - by1 if cy > by1 else cy - by0)
    if abs(dy) >= abs(dx):   # 동그라미가 위/아래 → 가로 가운데
        px = round(bcx - (rx0 + rx1) / 2)
        py = by0 - 2 - ry0 if dy < 0 else by1 + 2 - ry1
    else:                    # 동그라미가 왼/오른쪽 → 세로 가운데
        py = round(bcy - (ry0 + ry1) / 2)
        px = bx1 - 1 - rx1 if dx > 0 else bx0 + 1 - rx0
    return int(px), int(py)
