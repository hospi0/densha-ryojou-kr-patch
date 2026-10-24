# -*- coding: utf-8 -*-
r"""스테이트 RAM 에 올라온 텍스처 찾기 (2026-10-24): TRAIN.SUB 모든 4/8bpp 조각(한 번 훑어 work/leaves.pkl) 의 화소 가운데 64 B 가 eeMemory 에 있으면 «화면에 쓰임».
  python tools/find_tex_in_state.py work/mem/todo7 [work/mem/todo20 …] → 크기·bpp·위치, work/gfx/fs_<위치>.png"""
import os, pickle, struct, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sub_dump as S  # noqa: E402

PK = os.path.join(ROOT, 'work', 'leaves.pkl')


def leaves():
    if os.path.exists(PK): return pickle.load(open(PK, 'rb'))
    f = open(S.ISO, 'rb'); lv = []
    for l in open(os.path.join(ROOT, 'work', 'train_dat_all.txt')):
        if l.strip():
            try: S.walk(f, int(l.split('\t')[0], 16), lv)
            except Exception: pass
    out = {}
    for o, s, hh in lv:
        if o in out or s < 600: continue
        w, h = struct.unpack_from('<HH', hh, 2)
        if not (0 < w <= 1024 and 0 < h <= 1024): continue
        for bpp, pal in ((8, 256), (4, 16)):
            if abs(s - (16 + pal * 4 + w * h * bpp // 8)) <= 16: out[o] = (s, w, h, bpp, pal)
    pickle.dump(out, open(PK, 'wb')); return out


def main(dirs):
    L = leaves(); f = open(S.ISO, 'rb')
    for d in dirs:
        m = open(os.path.join(d, 'eeMemory.bin'), 'rb').read(); hits = []
        for o, (s, w, h, bpp, pal) in L.items():
            f.seek(S.BASE + o + 16 + pal * 4 + (w * h * bpp // 8) // 2); b = f.read(64)
            if len(set(b)) >= 4 and m.find(b) >= 0:
                hits.append((o, w, h, bpp))
                f.seek(S.BASE + o); a, _ = S.decode(f.read(s))
                Image.fromarray(a[..., :3]).save(os.path.join(ROOT, 'work/gfx', 'fs_%X.png' % o))
        print(d, ' '.join('%X:%dx%d/%d' % x for x in sorted(hits)))


if __name__ == '__main__':
    main(sys.argv[1:])
