# -*- coding: utf-8 -*-
"""크기별 대표 그림 목록 그림(번호 붙임) — 번역 표 채우기용 (2026-10-24)
  python tools/cat_sheet.py 184x32 [배율] → work/cat/<크기>_N.png"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S
sz = sys.argv[1]; sc = int(sys.argv[2]) if len(sys.argv) > 2 else 2
bs = json.load(open(os.path.join(ROOT, 'work/cat/bysize.json')))
I = L.index(); f = open(S.ISO, 'rb'); tiles = []
for k in bs[sz]:
    t = L.Tex(f, *I[k]) if True else None
    a = t.rgba(); BG = np.array([90, 90, 90])
    im = Image.fromarray((a[..., :3] * (a[..., 3:4] / 255) + BG * (1 - a[..., 3:4] / 255)).astype(np.uint8))
    tiles.append((k, im.resize((im.width * sc, im.height * sc), 0)))
W = 1600; x = y = rh = 0; pages = []; cv = Image.new('RGB', (W, 2000), (30, 30, 30)); d = ImageDraw.Draw(cv)
for k, im in tiles:
    if x + im.width > W: x = 0; y += rh + 4; rh = 0
    if y + im.height + 14 > 2000: pages.append(cv.crop((0, 0, W, y))); cv = Image.new('RGB', (W, 2000), (30, 30, 30)); d = ImageDraw.Draw(cv); y = 0
    d.text((x, y), k, fill=(255, 255, 0)); cv.paste(im, (x, y + 12)); x += im.width + 8; rh = max(rh, im.height + 12)
pages.append(cv.crop((0, 0, W, y + rh)))
for i, p in enumerate(pages): p.save(os.path.join(ROOT, 'work/cat/%s_%d.png' % (sz, i)))
print(len(tiles), len(pages))
