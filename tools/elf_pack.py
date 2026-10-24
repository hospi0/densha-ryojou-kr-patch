# -*- coding: utf-8 -*-
r"""실행 파일 평문 다시 채우기 분석·적용 (2026-10-24)
  문자열 구역(0x126000~0x14B000)에서 «연속 구간»(문자열 + 그 사이 0 패딩 < 16 B 만) 안의 문자열을 번역으로 바꿔
  빈틈없이(8 정렬) 다시 채우고, 각 문자열을 가리키는 32비트 포인터(4 정렬 워드)를 전부 고친다.
  안전:
   - 구간은 0 이 아닌 바이트(문자열 밖)에서 끊는다. 문자열 시작이 아닌 곳을 가리키는 포인터가 있으면 거기서도 끊는다.
   - 코드에서 lui/addiu(ori·lb 등) 쌍으로 주소를 만드는 문자열은 그 자리에 고정(구간 경계).
   - 구간마다 «새 길이 합 ≤ 구간 크기» 확인, 넘치면 그 구간은 알림(빌드 거부).
  번역 = work/text/kr_elf.tsv(tools/units.py check 결과). 한글 → 글꼴 코드 변환은 enc 함수로 받는다.
  python tools/elf_pack.py          # 분석만"""
import os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
A, B = 0x126000, 0x14B000
FOFF, VBASE = 0x80, 0x100000                       # 프로그램 헤더 0: 파일 0x80 = 가상 0x100000
VA = lambda o: o - FOFF + VBASE
FILESZ = 0x14B580                                  # 프로그램 헤더 0 파일 크기
ALIGN = 8


def unesc(t):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', '\\': '\\'}[m.group(1)], t)


def scan(b):
    """→ ptrs {대상 파일 오프셋: [포인터 워드 위치]}, coderef {대상 파일 오프셋}"""
    ptrs = {}
    lo_v, hi_v = VA(A), VA(B)
    for p in range(FOFF, FOFF + FILESZ - 3, 4):           # 적재 구간만(그 뒤 파일 0x14B600~ 은 심볼·디버그 정보)
        v = struct.unpack_from('<I', b, p)[0]
        if lo_v <= v < hi_v: ptrs.setdefault(v - VBASE + FOFF, []).append(p)
    coderef = set()
    text_end = A                                     # 코드는 문자열 구역 앞
    lui = {}
    for p in range(FOFF, text_end, 4):
        w = struct.unpack_from('<I', b, p)[0]
        if w >> 26 == 0x0F:                          # lui rt, imm
            rt, imm = (w >> 16) & 31, w & 0xFFFF
            for q in range(p + 4, min(text_end, p + 40), 4):
                w2 = struct.unpack_from('<I', b, q)[0]
                op, rs, imm2 = w2 >> 26, (w2 >> 21) & 31, w2 & 0xFFFF
                if rs == rt and op in (0x09, 0x0D, 0x20, 0x24, 0x23, 0x21, 0x25):
                    v = (imm << 16) + (imm2 - 0x10000 if imm2 >= 0x8000 and op != 0x0D else imm2)
                    if lo_v <= v < hi_v: coderef.add(v - VBASE + FOFF)
    return ptrs, coderef


def items(b, ptrs):
    """포인터 대상 = 문자열 시작 → [(시작, 끝(NUL 포함 다음))]"""
    out = []
    for s in sorted(ptrs):
        if not (A <= s < B): continue
        if b[s - 1] != 0: continue                   # 문자열 중간 = 우연히 범위에 든 다른 데이터(u16 숫자표 등) — 포인터 아님
        e = b.index(b'\0', s) + 1
        out.append((s, e))
    return out


def runs(b, its, coderef, ptrs):
    """연속 구간 목록: [[(시작, 끝), …]] — 구간 끝 = 마지막 문자열 끝을 다음 정렬까지(0 인 곳만)."""
    starts = {s for s, _ in its}
    coderef = coderef & starts                       # 코드 lui/addiu 가 «문자열 시작»을 만드는 것만 고정
    rs, cur = [], []
    for k, (s, e) in enumerate(its):
        if cur and (s in coderef or any(b[cur[-1][1]:s]) or s - cur[-1][1] >= 16 or s < cur[-1][1]):
            rs.append(cur); cur = []
        if s in coderef:
            continue                                 # 고정
        cur.append((s, e))
    if cur: rs.append(cur)
    # 구간 안(문자열 시작 아닌 곳)을 가리키는 포인터가 있으면 그 구간은 쓰지 않음
    bad = set()
    for i, r in enumerate(rs):
        lo, hi = r[0][0], r[-1][1]
        for t in ptrs:
            if lo <= t < hi and t not in starts and b[t - 1] == 0: bad.add(i); break   # 앞 바이트 0 아닌 대상 = 포인터 아님(items 와 같은 기준)
    return rs, bad


def load_tr():
    tr = {}
    for ln in open(W('text', 'kr_elf.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if ln:
            o, n, s = ln.split('\t', 2); tr[int(o, 16)] = unesc(s)
    return tr


def nbytes(s):
    return sum(2 if '가' <= c <= '힣' else len(c.encode('cp932', 'replace')) for c in s)


def plan(b, tr, size=None):
    """→ (구간별 [(시작, 새 바이트 길이)…], 넘친 구간) — size(s,문자열)=새 바이트 수"""
    size = size or (lambda s, t: nbytes(t) + 1)
    ptrs, coderef = scan(b)
    its = items(b, ptrs)
    rs, bad = runs(b, its, coderef, ptrs)
    al = lambda x: (x + ALIGN - 1) // ALIGN * ALIGN
    res, over, fixed_over, homeless = [], [], [], []
    for i, r in enumerate(rs):
        lo = r[0][0]; hi = r[-1][1]; hi_al = hi
        while hi_al % ALIGN and hi_al < len(b) and b[hi_al] == 0: hi_al += 1
        if i in bad:
            over.append((lo, hi_al, 0, len(r), True)); continue
        sz = [(s, size(s, tr[s]) if s in tr else e - s) for s, e in r]
        # 넘치면 큰 번역 문자열부터 구간 밖으로 빼서(다른 구간 남는 자리로) 맞춘다
        while sum(al(n) for _, n in sz) > hi_al - lo:
            k = max((j for j, (s, n) in enumerate(sz) if s in tr), key=lambda j: sz[j][1])
            homeless.append(sz.pop(k))
        lay, need = [], 0
        for s, n in sz:
            lay.append((s, lo + need, n)); need = al(need + n)
        res.append([lo, hi_al, lay, need])
    for s, n in sorted(homeless, key=lambda x: -x[1]):   # 남는 자리가 큰 구간 끝에
        r = max(res, key=lambda r: r[1] - r[0] - r[3])
        if r[1] - r[0] - r[3] < n:
            over.append((s, s, n, 1, False)); continue
        r[2].append((s, r[0] + r[3], n)); r[3] = al(r[3] + n)
    res = [(lo, hi, lay) for lo, hi, lay, _ in res]
    for s in coderef:
        if s in tr and nbytes(tr[s]) + 1 > b.index(b'\0', s) + 1 - s: fixed_over.append(s)
    return res, over, fixed_over, ptrs, coderef


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    b = open(W('SLPM_651.48'), 'rb').read()
    tr = load_tr()
    res, over, fixed_over, ptrs, coderef = plan(b, tr)
    nstr = sum(len(l) for _, _, l in res)
    print('연속 구간 %d · 문자열 %d · 코드 직접 참조(고정) %d · 번역 %d' % (len(res), nstr, len(coderef), len(tr)))
    print('넘친 구간 %d' % len(over))
    for lo, hi, need, n, isbad in over[:20]:
        print('  %X~%X 크기 %d 필요 %d (문자열 %d)%s' % (lo, hi, hi - lo, need, n, ' 안쪽 포인터' if isbad else ''))
    print('고정 문자열인데 번역이 더 김 %d: %s' % (len(fixed_over), ' '.join('%X' % s for s in fixed_over[:20])))
    big = sorted(res, key=lambda r: -(r[1] - r[0]))[:8]
    for lo, hi, lay in big: print('  구간 %X~%X %d B, 문자열 %d' % (lo, hi, hi - lo, len(lay)))


if __name__ == '__main__':
    main()
