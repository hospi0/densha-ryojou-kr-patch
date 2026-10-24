# -*- coding: utf-8 -*-
r"""UI 그림 한글 넣기 (2026-10-24): work/text/ui_*.tsv 를 label_kr.make 로 그려 ISO 의 텍스처 «모든 사본»에 쓴다.
  - 팔레트·머리는 그대로, 4bpp 화소만 바꿈(크기 같음). 사본 = work/gfx/canon.json·dups.json(바이트 같은 묶음).
  - 검산: 쓴 뒤 다시 읽어 기대값과 같은지, 바뀐 텍스처 밖은 안 건드렸는지(쓰기 범위 = 텍스처 화소 구역뿐).
  build.py 가 부른다. 따로: python tools/gfx_build.py <iso>  (미리 원본 복사본이어야 함)"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402


def pack(idx):
    a = idx.ravel()
    return bytes(int(a[i]) | (int(a[i + 1]) << 4) for i in range(0, len(a), 2))


def apply(out_iso):
    I = L.index(); src = open(S.ISO, 'rb')
    canon = json.load(open(os.path.join(ROOT, 'work/gfx/canon.json')))
    dups = json.load(open(os.path.join(ROOT, 'work/gfx/dups.json')))
    jobs = {}                                       # 위치 → 새 화소 바이트
    for fn, key, s, kr, memo in L.rows():
        t, cur = L.make(src, I, key, kr, memo)
        if (cur == t.idx).all(): continue
        pix = pack(cur); c = canon.get(key, key)
        for k in [c] + dups.get(c, []):
            off, size = I[k]
            src.seek(S.BASE + off); assert src.read(size) == t.blob, '사본 다름 %s/%s' % (key, k)
            assert jobs.get(off, pix) == pix, '같은 그림에 다른 번역 %s' % k
            jobs[off] = pix
    with open(out_iso, 'r+b') as f:
        for off, pix in jobs.items():
            f.seek(S.BASE + off + 80); f.write(pix)
        for off, pix in jobs.items():
            f.seek(S.BASE + off + 80); assert f.read(len(pix)) == pix
    return len(jobs)


if __name__ == '__main__':
    print('텍스처 %d곳' % apply(sys.argv[1]))
