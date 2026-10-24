# -*- coding: utf-8 -*-
r"""전차로 GO! 파이널 — TRAIN0.SUB(DAT 묶음 이어 붙임) 텍스처 일괄 풀기 (2026-10-17)
  DAT 묶음: "DAT\0" u32 조각수, (u32 위치, u32 크기)×n — 위치는 묶음 시작 기준, 조각이 또 DAT 일 수 있음(재귀).
  텍스처: 머리 16 B = [0]=0x14 [1]=형식 [2:4]=가로 [4:6]=세로 … 뒤에 팔레트(RGBA, A=0x80 불투명) + 화소.
          크기로 판정: 4bpp(팔레트 16색 64 B) / 8bpp(256색 1 KB). 4bpp 는 낮은 니블이 왼쪽.
  python tools/sub_dump.py → work/tex/<묶음위치>_<조각위치>.png · work/tex/list.tsv
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ISO = r'D:\hospi\My Documents\한글패치\PS2\ps2\Densha de Go! Final (Japan).iso'
BASE = 1485 * 2048; SIZE = 2159128576
OUT = os.path.join(ROOT, 'work', 'tex')


def walk(f, off, out, depth=0):
    f.seek(BASE + off); h = f.read(8)
    n = struct.unpack_from('<I', h, 4)[0]
    if n > 4096:
        return
    f.seek(BASE + off); h = f.read(8 + n * 8)
    for k in range(n):
        o, s = struct.unpack_from('<II', h, 8 + k * 8)
        f.seek(BASE + off + o); hh = f.read(16)
        if hh[:4] == b'DAT\x00':
            walk(f, off + o, out, depth + 1)
        else:
            out.append((off + o, s, hh))


def decode(blob):
    w, h = struct.unpack_from('<HH', blob, 2)
    if not (0 < w <= 1024 and 0 < h <= 1024):
        return None
    n = w * h
    for bpp, pal in ((4, 16), (8, 256)):
        need = 16 + pal * 4 + n * bpp // 8
        if abs(len(blob) - need) <= 16:
            P = np.frombuffer(blob[16:16 + pal * 4], np.uint8).reshape(pal, 4).astype(int)
            P[:, 3] = np.minimum(255, P[:, 3] * 2)
            d = np.frombuffer(blob[16 + pal * 4:16 + pal * 4 + n * bpp // 8], np.uint8)
            if bpp == 4:
                idx = np.stack([d & 15, d >> 4], 1).ravel()
            else:
                idx = d
            if len(idx) < n:
                return None
            return P[idx[:n]].reshape(h, w, 4).astype(np.uint8), bpp
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    dats = [int(x, 16) for x in open(os.path.join(ROOT, 'work', 'train0_dat.txt')).read().split()]
    f = open(ISO, 'rb'); rows = []; ok = 0
    for d in dats:
        ents = []; walk(f, d, ents)
        for o, s, hh in ents:
            if hh[0] != 0x14 or s > 4 << 20:
                continue
            f.seek(BASE + o); blob = f.read(s)
            r = decode(blob)
            if r is None:
                rows.append('%X\t%X\t%d\t%02X\t-' % (d, o, s, hh[1])); continue
            img, bpp = r
            Image.fromarray(img, 'RGBA').save(os.path.join(OUT, '%08X.png' % o))
            rows.append('%X\t%X\t%d\t%02X\t%dx%d %dbpp' % (d, o, s, hh[1], img.shape[1], img.shape[0], bpp)); ok += 1
    open(os.path.join(OUT, 'list.tsv'), 'w').write('묶음\t위치\t크기\t형식\t그림\n' + '\n'.join(rows))
    print('텍스처', ok, '/', len(rows))


if __name__ == '__main__':
    main()
