# -*- coding: utf-8 -*-
r"""평문 글꼴(TRAIN.SUB 0x85191000)에 한글 넣기 (2026-10-24, «파이널» tools/font_kr.py 를 위치만 바꿔 옮김)
  글꼴: 조각0 = 머리 16 B(크기·비한자 209·1수준 2,965·2수준 3,390) + SJIS 코드표 u16 LE 6,564자
        조각1~3 이어서 = 글자 6,564 × 272 B(24×22 4bpp 낮은 니블 왼쪽 264 B + 0 8 B). 가나는 이 글꼴에 없음(별도).
  글자 꼴: 획 안쪽 F/E, 위·왼 가장자리 9, 아래·오른 가장자리 C·D, 바깥 2px 테두리 5, 바탕 0. 쓰는 칸 약 21×22.
  한글 칸 = 2수준 한자(0x989F~) 중 실행 파일에 한 번도 안 나오는 것, 앞에서부터.
  python tools/font_kr.py preview → work/font_kr_preview.png (원본 한자 | 한글 후보 A·B, 1:1 과 3배)
"""
import os
import re
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf  # noqa: E402

ISO = r'C:\claude\roms\ps2\Densha de Go! Ryojou-hen (Japan).iso'
BASE = 0x85617800                                 # TRAIN.SUB(LBA 2317) 0x85191000 글꼴 DAT — «파이널» 과 같은 꼴
CODES_OFF = 0x30 + 16
GLYPH_OFF = 0x3390
N = 6564; GW, GH, GSZ = 24, 22, 272
NANUM = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
GALMURI14 = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf'


def load():
    f = open(ISO, 'rb')
    f.seek(BASE + CODES_OFF); codes = struct.unpack('<%dH' % N, f.read(N * 2))
    f.seek(BASE + GLYPH_OFF); G = bytearray(f.read(N * GSZ))
    return list(codes), G


def get(G, i):
    a = np.frombuffer(bytes(G[i * GSZ:i * GSZ + 264]), np.uint8)
    return np.stack([a & 15, a >> 4], 1).reshape(GH, GW)


def put(G, i, g):
    flat = g.reshape(-1).astype(np.uint8)
    G[i * GSZ:i * GSZ + 264] = bytes((flat[0::2] | (flat[1::2] << 4)).tolist())
    G[i * GSZ + 264:i * GSZ + 272] = bytes(8)


def hangul_used():
    s = open(os.path.join(ROOT, 'work/text/kr_elf.tsv'), encoding='utf-8').read()
    return sorted(set(c for c in s if '\uac00' <= c <= '\ud7a3'))


def free_slots(codes):
    """2수준 한자 중 실행 파일 원문 «문자열»에 안 나오는 칸(코드표 순번). 번역한 문자열의 한자도 «사용 중»으로 센다(보수적).
    (2026-10-24 여정편: «파이널» 처럼 파일 전체 바이트 쌍으로 세면 코드·디버그 정보까지 걸려 869칸뿐 → 한글 912자에 모자람)"""
    used = set()
    for ln in open(os.path.join(ROOT, 'work/text/src_elf.tsv'), encoding='utf-8').read().split('\n')[1:]:
        for c in ln.split('\t', 2)[-1]:
            try:
                b = c.encode('cp932')
            except UnicodeEncodeError:
                continue
            if len(b) == 2: used.add(int.from_bytes(b, 'big'))
    return [i for i in range(209 + 2965, N) if codes[i] not in used]


# ── 획 모양(마스크) 만들기 ─────────────────────────────
def mask_nanum(ch, size=19):
    im = Image.new('L', (40, 40)); d = ImageDraw.Draw(im)
    d.text((4, 2), ch, font=ImageFont.truetype(NANUM, size), fill=255)
    return np.array(im) >= 110


_G14 = None


def mask_galmuri(ch):
    global _G14
    if _G14 is None:
        _G14 = bdf.Font(GALMURI14)
    ink, _ = _G14.draw(ch)
    m = np.zeros((40, 40), bool)
    for x, y in ink:
        m[y + 4, x + 4] = True
    m2 = m.copy(); m2[:, 1:] |= m[:, :-1]; m2[1:, :] |= m[:-1, :]   # 오른쪽·아래로 1px 굵게 → 획 2px
    return m2


def fit(m, box_w=18, box_h=19):
    """잉크를 획 칸(왼 2·위 2, 17×19 — 원본 한자 획 범위) 가운데로."""
    ys, xs = np.nonzero(m)
    if not len(xs):
        return np.zeros((GH, GW), bool)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = m.shape
    assert w <= box_w and h <= box_h, '글자가 획 칸보다 큼 %dx%d' % (w, h)   # ⛔잘라 넣지 않음
    out = np.zeros((GH, GW), bool)
    x0 = 2 + max(0, (box_w - w) // 2); y0 = 2 + max(0, (box_h - h) // 2)
    out[y0:y0 + min(h, box_h), x0:x0 + min(w, box_w)] = m[:box_h, :box_w]
    return out


def style(core):
    """획 마스크 → 원본 꼴 화소값(0/5/9/C/D/E/F)."""
    g = np.zeros((GH, GW), np.uint8)
    pad = np.pad(core, 2)
    out = np.zeros_like(pad)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if abs(dy) == 2 and abs(dx) == 2:
                continue
            out |= np.roll(np.roll(pad, dy, 0), dx, 1)
    g[out[2:-2, 2:-2]] = 5
    up = np.pad(core, ((1, 0), (0, 0)))[:-1]; lf = np.pad(core, ((0, 0), (1, 0)))[:, :-1]
    dn = np.pad(core, ((0, 1), (0, 0)))[1:]; rt = np.pad(core, ((0, 0), (0, 1)))[:, 1:]
    g[core] = 0xF
    g[core & rt & ~dn] = 0xE
    g[core & (~rt | ~dn)] = 0xD
    g[core & (~up | ~lf)] = 0x9
    return g


def make(ch, kind='A'):
    return style(fit(mask_nanum(ch) if kind == 'A' else mask_galmuri(ch)))


def preview():
    codes, G = load(); idx = {c: i for i, c in enumerate(codes)}
    jp = '運転速度表示説明入門経験'
    kr = '이것이 속도계예요 현재 속도를 표시해요 입문 다이아 경험'
    rows = [np.hstack([get(G, idx[int.from_bytes(c.encode('cp932'), 'big')]) for c in jp])]
    for k in 'AB':
        rows.append(np.hstack([make(c, k) if c != ' ' else np.zeros((GH, 12), np.uint8) for c in kr]))
    W = max(r.shape[1] for r in rows)
    sheet = np.vstack([np.pad(r, ((2, 2), (0, W - r.shape[1]))) for r in rows])
    pal = np.array([(40, 30, 60)] + [(int(v * 17),) * 3 for v in range(1, 16)], np.uint8)
    rgb = pal[sheet]
    im1 = Image.fromarray(rgb); im3 = im1.resize((im1.width * 3, im1.height * 3), 0)
    cv = Image.new('RGB', (max(im3.width, 10), im1.height + im3.height + 30), (90, 90, 90))
    d = ImageDraw.Draw(cv); cv.paste(im1, (0, 14)); cv.paste(im3, (0, im1.height + 28))
    d.text((2, 0), '1:1  위 = 원본 한자 / 가운데 = A 나눔고딕 엑스트라볼드 19px / 아래 = B 갈무리14 굵게', fill=(255, 255, 0),
           font=ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 11))
    cv.save(os.path.join(ROOT, 'work/font_kr_preview.png'))
    hs = hangul_used(); fs = free_slots(codes)
    print('한글 %d자 / 빈 칸 %d' % (len(hs), len(fs)))


if __name__ == '__main__':
    preview()
