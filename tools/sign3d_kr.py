# -*- coding: utf-8 -*-
r"""선로 옆 3D 표지 텍스처(停止位置·確認位置) 한글화 (2026-10-24, 실기 스샷 — 정차 때 화면 아래 크게 보임)
  표 = work/text/sign3d.tsv(label_kr 표와 같은 꼴, ui_ 아님 — gfx_build 가 안 씀).
  사본은 노선마다 여러 벌이고 머리 16바이트(VRAM 자리)만 다름 → 사본마다 «자기 머리 그대로 + 새 팔레트·화소».
  python tools/sign3d_kr.py → work/gfx/prev_sign3d.png · build.py 가 apply(out_iso)"""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

TSV = os.path.join(ROOT, 'work', 'text', 'sign3d.tsv')


def rows():
    out = []
    for ln in open(TSV, encoding='utf-8').read().split('\n')[1:]:
        a = ln.rstrip('\r').split('\t')
        if len(a) >= 4 and a[2].strip(): out.append(a)
    return out


def copies(f, I, key):
    o, s = I[key]; f.seek(S.BASE + o); body = f.read(s)[16:]
    out = [key]
    for k, (o2, s2) in I.items():
        if s2 == s and k != key:
            f.seek(S.BASE + o2 + 16)
            if f.read(s - 16) == body: out.append(k)
    return out


def jobs(f, I):
    for key, src, kr, memo in rows():
        t, idx = L.make(f, I, key, kr, memo); yield key, t, idx


def apply(out_iso):
    I = L.index(); f = open(S.ISO, 'rb'); n = 0
    cache = os.path.join(ROOT, 'work', 'gfx', 'sign3d_copies.json')
    cp = json.load(open(cache)) if os.path.exists(cache) else {}
    with open(out_iso, 'r+b') as g:
        for key, t, idx in jobs(f, I):
            if key not in cp: cp[key] = copies(f, I, key)
            new = t.encode(idx)[16:]
            for k in cp[key]:
                off, size = I[k]
                f.seek(S.BASE + off); orig = f.read(size); assert orig[16:] == t.blob[16:], k
                g.seek(S.BASE + off + 16); g.write(new); n += 1
    json.dump(cp, open(cache, 'w'))
    return n


if __name__ == '__main__':
    I = L.index(); f = open(S.ISO, 'rb'); ims = []
    for key, t, idx in jobs(f, I):
        a = np.concatenate([t.rgba()[..., :3], np.full((t.h, 3, 3), 255, np.uint8), t.rgba(idx)[..., :3]], 1)
        ims.append(Image.fromarray(a).resize((a.shape[1] * 4, a.shape[0] * 4), Image.NEAREST))
    W = max(i.width for i in ims); c = Image.new('RGB', (W, sum(i.height + 8 for i in ims)), (40, 40, 40)); y = 0
    for i in ims: c.paste(i, (0, y)); y += i.height + 8
    c.save(os.path.join(ROOT, 'work', 'gfx', 'prev_sign3d.png'))
