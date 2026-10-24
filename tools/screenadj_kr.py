# -*- coding: utf-8 -*-
r"""화면 위치 조정 배경 사진(8bpp 616×432, TRAIN.SUB 7F2249E0) 한글화 (2026-10-24, 사용자 «기존 한글화한 요소를 모아 통일»)
  사진에 찍힌 HUD 텍스처(1:1, 자리 = 사진과 원본 텍스처 맞추기로 찾음)를 «한글로 바꾼 같은 텍스처»로 갈아 끼움:
  사진 = a·원본 + (1−a)·배경 → 배경을 되살려 a'·한글 + (1−a')·배경 으로 다시 섞고 사진 팔레트(256색) 가장 가까운 색으로.
  한글 텍스처 = work/text/ui_*.tsv 의 그 줄을 label_kr.make 로 그린 것(빌드와 같음).
  python tools/screenadj_kr.py → work/gfx/prev_screenadj.png(원본|한글) · build.py 가 apply(out_iso)"""
import os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

OFF, W, H = 0x7F2249E0, 616, 432
FLAT = {'843436C0', '843432B0'}
NOTINT = {'84359B60'}
PLATE = {'84359B60': (9, 67, 72, 89)}   # 차내 신호 이름판(텍스처 좌표)   # 사진 램프가 텍스처와 달라 색 곱 추정이 틀어짐
WHOLE = {}   # (차내 신호는 이름판 기준 1:1 자리 18,228 — 판 전체 맞추기는 램프가 달라 2px 틀렸음)   # 到着時刻·現在時刻
ITEMS = [('84343AD0', 5, 4), ('842C3400', 240, 20), ('843436C0', 254, 48), ('843432B0', 254, 74), ('84342010', 238, 106),
         ('8435C3F0', 428, 50), ('83F67A10', 500, 120), ('84359B60', 18, 228), ('83EC84D0', 5, 330), ('83EC58F0', 5, 362)]


def load(f):
    f.seek(S.BASE + OFF); b = f.read(16 + 1024 + W * H)
    return b, np.frombuffer(b[1040:], np.uint8).reshape(H, W).copy(), np.frombuffer(b[16:1040], np.uint8).reshape(256, 4)


def make(f):
    I = L.index(); R = {k: (kr, m) for fn, k, s, kr, m in L.rows()}
    b, ix, P = load(f); pal = P[:, :3].astype(float); photo = pal[ix]
    out = photo.copy()
    for k, x, y in ITEMS:
        t, nidx = L.make(f, I, k, *R[k])
        o = t.rgba().astype(float); n = t.rgba(nidx).astype(float); h, w = o.shape[:2]
        ao, an = o[..., 3:4] / 255, n[..., 3:4] / 255
        reg = photo[y:y + h, x:x + w]
        op = o[..., 3] > 230   # 게임이 정점 색을 곱해 찍음(現在時刻 = 노랑) → 불투명 자리에서 채널별 곱 추정
        if op.sum() > 20 and k not in NOTINT:
            tint = np.clip((reg[op] * o[..., :3][op]).sum(0) / np.maximum((o[..., :3][op] ** 2).sum(0), 1), 0, 2)
            o = o.copy(); n = n.copy(); o[..., :3] *= tint; n[..., :3] *= tint
        bg = np.where(ao < 0.98, (reg - ao * o[..., :3]) / np.maximum(1 - ao, 1e-3), reg)
        if (ao >= 0.98).any():   # 원본이 불투명했던 자리의 배경 = 둘레 반투명 자리 배경 평균(드묾)
            m = (ao[..., 0] < 0.98)
            if m.any(): bg[~m] = bg[m].mean(0)
        if k in PLATE:   # 이름판 상자만 통째로, 텍스처 판 색 → 사진 판 색(차내 신호: 사진 크림이 더 회색)
            x0_, y0_, x1_, y1_ = PLATE[k]; nn = t.rgba(nidx)[y0_:y1_, x0_:x1_, :3].astype(float); oo = t.rgba()[y0_:y1_, x0_:x1_, :3].astype(int)
            rr = reg[y0_:y1_, x0_:x1_]; cream = oo.sum(-1) > 550
            pc = np.median(rr[cream], 0); tc = np.median(oo[cream], 0)
            nb = nn.sum(-1) > 550; nn[nb] = nn[nb] * (pc / np.maximum(tc, 1))
            out[y + y0_:y + y1_, x + x0_:x + x1_] = nn; continue
        if k in WHOLE:   # 사진에선 크기가 조금 다름(차내 신호 96→98) → 한글 텍스처를 그 크기로 늘려 불투명 자리 통째로
            ww, hh = WHOLE[k]; nn = np.asarray(Image.fromarray(t.rgba(nidx)).resize((ww, hh), Image.NEAREST)).astype(float)
            m = nn[..., 3] > 200; r2 = out[y:y + hh, x:x + ww]; r2[m] = nn[..., :3][m]; continue
        if k in FLAT:   # 사진 글자가 텍스처와 미세하게 달라 찌꺼기 → 칸 전체를 판 바탕(어두운 화소 중앙값)으로 지우고 얹음
            lum = reg @ np.array([.3, .59, .11]); pb = np.median(reg[lum < np.percentile(lum, 40)], 0)
            bg = np.broadcast_to(pb, reg.shape)
            new = an * n[..., :3] + (1 - an) * bg; changed = np.ones(reg.shape[:2], bool)
        else:
            new = an * n[..., :3] + (1 - an) * np.clip(bg, 0, 255)
            changed = (np.abs(nidx.astype(int) - t.idx.astype(int)) > 0)
        out[y:y + h, x:x + w][changed] = new[changed]
    # 사진 팔레트로
    d = ((out[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)
    nix = d.argmin(-1).astype(np.uint8)
    ch = (out != photo).any(-1); res = ix.copy(); res[ch] = nix[ch]
    return b, ix, res, P


def apply(out_iso):
    f = open(S.ISO, 'rb'); b, ix, res, P = make(f)
    with open(out_iso, 'r+b') as g:
        g.seek(S.BASE + OFF + 1040); g.write(res.tobytes())
    return 1


if __name__ == '__main__':
    f = open(S.ISO, 'rb'); b, ix, res, P = make(f); pal = P[:, :3]
    a = np.concatenate([pal[ix], np.full((H, 6, 3), 255, np.uint8), pal[res]], 1)
    Image.fromarray(a.astype(np.uint8)).resize((a.shape[1] * 2, H * 2), Image.NEAREST).save(os.path.join(ROOT, 'work/gfx/prev_screenadj.png'))
