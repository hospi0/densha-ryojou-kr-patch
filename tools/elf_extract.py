# -*- coding: utf-8 -*-
r"""실행 파일(SLPM_651.48) 평문 SJIS 문자열 → work/text/src_elf.tsv + 번역할 파일 work/todo/번역할것_NN.tsv (2026-10-23)
  («파이널» tools/elf_extract.py 를 여정편 범위로)
  범위 0x126000~0x14B000(관광 안내 대사·차량 소개·노선 설명·시스템 글). 그 밖의 «가나 든» 바이트는 코드 잡음.
  제어 코드 $z $V/$v $b $t x,y $n(줄바꿈) $k(키 대기) $p(쪽 넘김) ~c R,G,B 등 — 번역에서 그대로 유지.
  번역할 파일: 같은 원문은 한 줄(처음 위치), 20 KB(UTF-8 BOM) 단위. 열 = 번호·위치·바이트·원문·번역.
  python tools/elf_extract.py"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
A, B = 0x126000, 0x14B000                  # 0x120000~0x126000 의 걸린 것은 코드 잡음
SPLIT = 20 * 1024


def esc(t):
    return t.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')


def strings():
    b = open(W('SLPM_651.48'), 'rb').read(); i = A
    while i < B:
        if b[i] == 0:
            i += 1; continue
        j = b.index(b'\0', i); s = b[i:j]
        try:
            t = s.decode('cp932')
        except UnicodeDecodeError:
            i = j + 1; continue
        if len(s) >= 4 and re.search('[\u3040-\u30ff\u4e00-\u9fff\uff01-\uff5e]', t) and all(c.isprintable() or c in '　\n' for c in t):
            # 반각 가나는 거르지 않는다 — 에노덴 안내(0x12A3E0)에 원문 오타 «､» 가 섞여 있음. \n = USB 컨트롤러 안내(0x1426D0~)
            if t.endswith('\n') and not t.startswith('~'):     # 디버그 출력(«…の確保に失敗しました\n» 등 13개)
                i = j + 1; continue
            yield i, len(s), t
        i = j + 1


def main():
    os.makedirs(W('text'), exist_ok=True); os.makedirs(W('todo'), exist_ok=True)
    rows = list(strings())
    open(W('text', 'src_elf.tsv'), 'w', encoding='utf-8').write(
        '위치\t바이트\t원문\n' + ''.join('%X\t%d\t%s\n' % (o, n, esc(t)) for o, n, t in rows))
    seen, uniq = set(), []
    for o, n, t in rows:
        if t not in seen:
            seen.add(t); uniq.append((o, n, t))
    for f in os.listdir(W('todo')):
        if f.startswith('번역할것_'): os.remove(W('todo', f))
    head = '번호\t위치\t바이트\t원문\t번역\n'; files, cur = [], head
    for k, (o, n, t) in enumerate(uniq, 1):
        line = 'E%05d\t%X\t%d\t%s\t\n' % (k, o, n, esc(t))
        if len((cur + line).encode('utf-8')) + 3 > SPLIT:
            files.append(cur); cur = head
        cur += line
    files.append(cur)
    for k, body in enumerate(files, 1):
        open(W('todo', '번역할것_%02d.tsv' % k), 'w', encoding='utf-8-sig').write(body)
    print('문자열 %d · 고유 %d(%d자) → work/todo 파일 %d개' % (len(rows), len(uniq), sum(len(t) for _, _, t in uniq), len(files)))


if __name__ == '__main__':
    main()
