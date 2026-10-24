# -*- coding: utf-8 -*-
r"""노선 지도 위 스프라이트(사진 판·강조 라벨) 자리 — 실행 파일 SLPM_651.48 의 장면 표에서 뽑음(2026-10-24).
  표 = 기록 5×i32 «번호, 층, 화면 x, 화면 y, 0», 번호 2 = 지도(화면 원점), 3~ = 묶음 안 텍스처 순서(지도 다음부터).
  에노덴 0xD7FD0(원점 48,50) · 이요 0xD85A0 · 하코다테 0xD9990 · 란덴 0xDB290(원점 60,60).
  실측 대조: 오카이도 (292,178)·고료카쿠코엔마에 (311,88) 스샷, 혼마치 x=80·마츠야마 라벨 그림 — 모두 일치.
  python tools/map_sprites.py → 표 다시 뽑아 POS 와 대조"""
import os, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = {   # 지도 키: (표 위치, [번호 3, 4, … 에 해당하는 텍스처 키])
    '8463CB80': (0xD7FD0, ['8464F320', '84650B70', '84650CC0', '84650EB0']),
    '846A7C80': (0xD85A0, ['846BA420', '846BAD70', '846BAFC0', '846BB190', '846BB410', '846BB6E0', '846BB870']),
    '84714C40': (0xD9990, ['847273E0', '847287E0', '847289B0', '84728C80', '84728FD0', '84729320']),
    '84780BE0': (0xDB290, ['84793380', '847945D0', '84794840', '84794990', '84794BE0', '84794D30']),
}


def load(elf_path=os.path.join(ROOT, 'work', 'SLPM_651.48')):
    elf = open(elf_path, 'rb').read(); pos = {}
    for mk, (off, keys) in TABLES.items():
        recs = {}; o = off
        while True:
            n, layer, x, y, z = struct.unpack_from('<5i', elf, o)
            if z != 0 or not (0 < n < 40): break
            recs[n] = (x, y); o += 20
        ox, oy = recs[2]
        for i, k in enumerate(keys):
            x, y = recs[3 + i]; pos[k] = (x - ox, y - oy)   # 지도 좌표
    return pos


POS = load()

if __name__ == '__main__':
    for k, v in sorted(POS.items()): print(k, v)
