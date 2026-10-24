# -*- coding: utf-8 -*-
r"""시험 빌드 (2026-10-24): 원본 ISO 복사본에 «글꼴 한글 + 실행 파일 평문(다시 채우기)» 를 넣는다.
  python tools/build.py [출력 iso]   (기본 work/build/Densha de Go! Ryojou-hen (Japan) [KR].iso)
  - 번역 = work/text/kr_elf.tsv (tools/units.py check 결과 — 먼저 돌릴 것)
  - 한글 음절 → 2수준 한자 빈 칸(font_kr.free_slots 순서) → work/charmap.tsv, 글자 꼴 A(나눔고딕 엑스트라볼드 19px, «파이널» 승인)
  - 실행 파일: tools/elf_pack.py 배치대로 연속 구간을 비우고 다시 채운 뒤 포인터 워드를 새 주소로. 코드 직접 참조 문자열은 제자리.
  - 검산: 모든 번역 문자열을 «포인터가 가리키는 곳»에서 다시 읽어 기대값과 같은지, 구역 밖 변경은 포인터 워드뿐인지.
  ⛔원본 ISO 는 읽기만."""
import os, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import elf_pack as P  # noqa: E402
import font_kr as F  # noqa: E402
import gfx_build  # noqa: E402
import disclaimer_kr  # noqa: E402
import logo_kr  # noqa: E402
import newtag_kr  # noqa: E402
import map_kr  # noqa: E402
import map2_kr  # noqa: E402
import title_kr  # noqa: E402
import step_kr  # noqa: E402
import ctrl_kr  # noqa: E402
import lohi_kr  # noqa: E402
import sign3d_kr  # noqa: E402
import screenadj_kr  # noqa: E402
import book_kr  # noqa: E402
from iso2048 import Iso  # noqa: E402

ELF_NAME = 'SLPM_651.48'
OUT = os.path.join(ROOT, 'work', 'build', 'Densha de Go! Ryojou-hen (Japan) [KR].iso')


def encode(s, cmap):
    out = bytearray()
    for c in s:
        out += cmap[c].to_bytes(2, 'big') if c in cmap else c.encode('cp932')
    return bytes(out)


def main(out_iso):
    sys.stdout.reconfigure(encoding='utf-8')
    tr = P.load_tr()
    # 1) 글자 배정·글꼴
    codes, G = F.load(); hs = sorted(set(c for t in tr.values() for c in t if '가' <= c <= '힣')); fs = F.free_slots(codes)
    assert len(hs) <= len(fs), (len(hs), len(fs))
    cmap = {}; rows = ['음절\t코드\t칸']
    for ch, i in zip(hs, fs):
        cmap[ch] = codes[i]; F.put(G, i, F.make(ch, 'A')); rows.append('%s\t%04X\t%d' % (ch, codes[i], i))
    open(os.path.join(ROOT, 'work', 'charmap.tsv'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    enc = {s: encode(t, cmap) + b'\0' for s, t in tr.items()}
    # 2) 실행 파일 다시 채우기
    elf0 = open(os.path.join(ROOT, 'work', ELF_NAME), 'rb').read(); elf = bytearray(elf0)
    res, over, fixed_over, ptrs, coderef = P.plan(elf0, tr, size=lambda s, t: len(enc[s]))
    assert not over and not fixed_over, (over, fixed_over)
    pwords = {w for ws in ptrs.values() for w in ws}
    for lo, hi, lay in res:
        assert not any(lo <= w < hi for w in pwords), '포인터 워드가 구간 안 %X' % lo
    blob = {}
    for lo, hi, lay in res:
        for s, at, n in lay:
            blob[s] = enc[s] if s in enc else elf0[s:elf0.index(b'\0', s) + 1]
            assert len(blob[s]) == n
    for lo, hi, lay in res: elf[lo:hi] = bytes(hi - lo)
    newat = {}
    for lo, hi, lay in res:
        for s, at, n in lay:
            elf[at:at + n] = blob[s]; newat[s] = at
            for w in ptrs[s]: struct.pack_into('<I', elf, w, P.VA(at))
    nfix = 0
    for s in coderef & set(enc):                     # 제자리(코드가 주소를 직접 만듦)
        if s in newat: continue
        n0 = elf0.index(b'\0', s) + 1 - s; b = enc[s]; assert len(b) <= n0
        elf[s:s + n0] = b + bytes(n0 - len(b)); newat[s] = s; nfix += 1
    miss = [s for s in enc if s not in newat]
    assert not miss, '안 들어간 번역 %s' % ['%X' % s for s in miss[:10]]
    # 검산
    for s, b in enc.items():
        at = newat[s]; assert bytes(elf[at:at + len(b)]) == b, '%X' % s
        for w in ptrs.get(s, []): assert struct.unpack_from('<I', elf, w)[0] == P.VA(at)
    outside = [i for i in range(len(elf)) if elf[i] != elf0[i] and not (P.A <= i < P.B)]
    assert all(any(w <= i < w + 4 for w in (i - i % 4,)) and (i - i % 4) in pwords for i in outside), '구역 밖 변경'
    # 2b) 이름 입력 «終» 판정 = 코드가 글자를 리틀엔디언 반워드로 읽어 0x498F 와 비교(addiu $v0,$zero,imm 3곳, 2026-10-24 실기 «끝»이 글자로 써짐)
    #     자판 끝 칸을 «끝»으로 바꿨으니 비교값도 «끝» 코드로. «←»(0x81A9)는 자판에 원래 글자 그대로라 손대지 않음.
    end = int.from_bytes(encode('끝', cmap), 'little'); assert end < 0x8000   # addiu 부호 확장
    for o in (0xA84C8, 0xA84F8, 0xA85CC):
        assert struct.unpack_from('<I', elf0, o)[0] == 0x2402498F, '%X' % o
        struct.pack_into('<I', elf, o, 0x24020000 | end)
    # 3) ISO
    os.makedirs(os.path.dirname(out_iso), exist_ok=True)
    print('ISO 복사…', flush=True); shutil.copyfile(F.ISO, out_iso)   # 매번 원본에서 새로(표에서 뺀 그림이 옛 빌드대로 남지 않게)
    iso = Iso(F.ISO)
    ent = [e for e in iso.walk() if os.path.basename(e[0]).upper().startswith(ELF_NAME)][0]
    assert ent[2] == len(elf)
    with open(out_iso, 'r+b') as f:
        f.seek(ent[1] * 2048); f.write(elf)
        f.seek(F.BASE + F.GLYPH_OFF); f.write(bytes(G))
    open(os.path.join(ROOT, 'work', 'build', ELF_NAME), 'wb').write(elf)
    ntex = gfx_build.apply(out_iso)                  # 4) UI 그림(work/text/ui_*.tsv)
    ntex += disclaimer_kr.apply(out_iso)             # 5) 시작 경고문(8bpp 사진)
    ntex += logo_kr.apply(out_iso)                   # 6) 제목 로고(8bpp) + 등장 연출 구멍 판(640×480)
    ntex += newtag_kr.apply(out_iso)                 # 7) 자료관 NEW 버튼(336×48 — 40 판 번역 + 원본 NEW)
    ntex += map_kr.apply(out_iso)                    # 8) 입문편 노선 지도·강조 이름표·성 그림
    ntex += map2_kr.apply(out_iso)                   # 8b) 에노덴·하코다테·란덴 노선 지도 + 강조 이름표 13장
    ntex += title_kr.apply(out_iso)                  # 9) 제목 화면 «스타트 버튼을 눌러 주세요»
    ntex += step_kr.apply(out_iso)                   # 10) 옵션 캘리브레이션 Step1~3·Finish 두 줄 설명
    ntex += ctrl_kr.apply(out_iso)                   # 11) 컨트롤러 설명 그림 2장(8bpp)
    ntex += lohi_kr.apply(out_iso)                   # 12) 사운드 막대 低/高 → 저/고(ui_opt 줄 이름 위에 덮어씀)
    ntex += sign3d_kr.apply(out_iso)                 # 13) 선로 옆 3D 표지 停止位置·確認位置(사본마다 머리 유지)
    ntex += screenadj_kr.apply(out_iso)              # 14) 화면 위치 조정 배경 사진(찍힌 HUD 를 한글 텍스처로 갈아 끼움)
    ntex += book_kr.apply(out_iso)                   # 15) 이름 입력 책 그림(8bpp) 運転士： → 운전사 :
    moved = sum(1 for s in enc if newat[s] != s)
    print('번역 문자열 %d(자리 옮김 %d · 제자리 고정 %d) · 한글 %d자 · UI 그림 %d곳 · ELF 바뀐 바이트 %d(구역 밖 포인터 %d) · 출력 %s'
          % (len(enc), moved, nfix, len(hs), ntex, sum(x != y for x, y in zip(elf, elf0)), len(outside), out_iso))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else OUT)
