# -*- coding: utf-8 -*-
r"""평문 번역 단위(쪽) 나누기·다시 합치기·조판 검사 (2026-10-23)
  단위 = 문자열을 $p 로 나눈 쪽. 쪽 앞 제어 코드($z$b02$u$v5 등)와 끝 $k 는 도구가 원문 그대로 붙인다 → 번역은 본문만.
  줄 나눔: 원문이 여러 줄인 문자열은 «상자 폭»(그 문자열의 원문 최대 줄 폭, 바이트) 에 맞춰 띄어쓰기에서 자동으로 $n.
           번역에 직접 쓴 $n 은 강제 줄바꿈(차량 제원처럼 줄마다 항목인 것). 원문이 한 줄이면 줄 나눔 안 함.
  폭: 한글·전각 2바이트, 반각 공백·영숫자 1바이트(«파이널» 과 같음).
  검사: 쪽당 줄 수 ≤ 원문 문자열의 최대 쪽 줄 수(관광 안내 4줄), 본문 안 제어 코드 개수·순서 같음, 문자열 바이트 ≤ 원문(넘으면 목록).
  python tools/units.py export     → work/units/units_NN.tsv (번호·앞·원문·번역 — 원문 본문은 $n 을 ⏎ 로 보여 줌)
  python tools/units.py check      → work/tr/*.tsv 를 읽어 조판·검사 → work/text/kr_elf.tsv(위치·완성 문자열) + work/text/layout.txt"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = lambda *p: os.path.join(ROOT, 'work', *p)
TOK = re.compile(r'\$(?:[nNkpzZu]|[a-zA-Z][0-9]*(?:,[0-9]+)*)|~[a-zA-Z] *[0-9]+(?:, *[0-9]+)*')   # $n 뒤 반각 숫자는 글(«$n501»)
LEAD = re.compile(r'^(?:%s|\$[0-9]+,[0-9]+|\.[0-9])+' % TOK.pattern)   # 쪽 머리 «$15,0»·«.1» = 원문 오타 코드 조각(교토 안내) — 원문 그대로
SPLIT = 20 * 1024
HALF = str.maketrans({',': '，', '.': '．', '!': '！', '?': '？', ':': '：', '(': '（', ')': '）', '~': '～', '·': '・'})   # % 는 printf(«%s») — 바꾸지 않음


def TOKSAFE(s, f):
    """제어 코드는 건드리지 않고 그 사이 글에만 f."""
    out, pos = [], 0
    for m in TOK.finditer(s):
        out.append(f(s[pos:m.start()])); out.append(m.group(0)); pos = m.end()
    return ''.join(out) + f(s[pos:])


def unesc(t):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', '\\': '\\'}[m.group(1)], t)


def bw(s):
    """화면 폭(바이트)."""
    s = TOK.sub('', s)
    return sum(0 if '' <= c <= '' else                 # 줄바꿈 중 토큰 자리표(wrap)
               2 if ('가' <= c <= '힣' or len(c.encode('cp932', 'replace')) == 2) else 1 for c in s)


def src_rows():
    out = []
    for ln in open(W('text', 'src_elf.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if ln:
            o, n, t = ln.split('\t', 2); out.append((o, int(n), unesc(t)))
    return out


def pages(t):
    """→ [(앞 토큰, 본문, 끝)] — 끝 = '$k' 또는 ''."""
    out = []
    for pg in t.split('$p'):
        m = LEAD.match(pg); lead = m.group(0) if m else ''
        body = pg[len(lead):]; tail = ''
        if body.endswith('$k'): body, tail = body[:-2], '$k'
        out.append((lead, body, tail))
    return out


BOXES = [(0x1261E0, 0x138440, 52),                  # 관광 안내 창 26칸(스샷 11.png, 원문 최대 52)
         (0x138440, 0x13E670, 50),                  # 자료관 설명 창 25칸(스샷 5.png) — 차량·특산품·명소 설명
         (0x13F820, 0x140400, 50),
         (0x141B80, 0x1423D0, 52),                  # 입문 시작·끝 교관 말(관광 안내와 같은 창, 스샷 11·20.png)
         (0x146DD0, 0x149800, 32)]                  # 운전 중 조언 창 16칸×3줄(스샷 12~15.png) — 엔진이 글자 단위로 자동 줄바꿈 → 낱말 단위로 미리 $n                  # 자료관 노선 소개(같은 상자, $k$p 씀). 그 사이 0x13E670~ = 목록 제목(한 줄)


def box(t, o=None):
    """상자 폭(바이트)·최대 줄 수. 폭 = 구역별 실제 상자 폭(스샷 실측), 그 밖은 원문 최대 줄 폭."""
    ls = [bw(x) for x in re.split(r'\$[nN]|\n|\$p', t)]
    mx_lines = max(len(re.split(r'\$[nN]|\n', b)) for _, b, _ in pages(t))
    width = max(ls); multi = len(ls) > len(t.split('$p')); region = None
    for k, (a, b, wd) in enumerate(BOXES):
        if o is not None and a <= int(o, 16) < b: width = max(width, wd); multi = True; region = k
    if region == 4:                                 # 조언 창: 폭 = 상자(원문 줄이 더 넓어도 엔진이 32 에서 꺾음), 줄 수 = 원문 자동 줄바꿈 줄 수와 3 중 큰 것
        width = 32
        return width, max(3, max(sum(-(-bw(x) // 32) or 1 for x in re.split(r'\$[nN]|\n', b)) for _, b, _ in pages(t))), True, region
    return width, max(mx_lines, 4), multi, region   # 상자 = 4줄(관광 안내·자료관 스샷)


def export():
    os.makedirs(W('units'), exist_ok=True)
    for f in glob.glob(W('units', 'units_*.tsv')): os.remove(f)
    seen = set(); rows = []
    for k, (o, n, t) in enumerate(src_rows(), 1):
        if t in seen: continue
        seen.add(t)
        for i, (lead, body, tail) in enumerate(pages(t)):
            if not body.strip() and not lead: continue
            rows.append('%s.%03d\t%s\t%s\t' % (o, i, lead, body.replace('$n', '⏎').replace('\n', '⏎')))
    head = '번호\t앞\t원문\t번역\n'; files, cur = [], head
    for r in rows:
        if len((cur + r + '\n').encode('utf-8')) > SPLIT: files.append(cur); cur = head
        cur += r + '\n'
    files.append(cur)
    for k, b in enumerate(files, 1):
        open(W('units', 'units_%02d.tsv' % k), 'w', encoding='utf-8').write(b)
    print('단위 %d · 파일 %d' % (len(rows), len(files)))


CENTER = [(0x1407E0, 0x141B80), (0x143240, 0x143360), (0x146A50, 0x146A90), (0x14A7F0, 0x14A9D0)]      # 메모리카드 안내·확인창 — 전각 공백으로 가운데 맞춘 줄
LBRK = re.compile(r'(\$[nN]|\$l[0-9]+,[0-9]+|\n)')
KEEP_LEAD = ('ボタン', 'はい', 'は　い', 'いいえ')          # 버튼 아이콘이 앞 채움 자리에 그려짐(«파이널» 과 같음) → 앞 채움 그대로


def center_lines(src, kr):
    """원문 줄마다 가운데(앞 채움 + 글 폭/2)를 재서 번역 줄도 같은 가운데에. 줄 구조(줄바꿈 토큰)는 원문과 같아야 함."""
    sp, kp = LBRK.split(src), LBRK.split(kr)
    if len(sp) != len(kp) or sp[1::2] != kp[1::2]: return kr, '줄 구조 다름 %d≠%d' % (len(sp), len(kp))
    out = []
    for i, (s, k) in enumerate(zip(sp, kp)):
        if i % 2: out.append(k); continue
        m = re.match(r'^((?:%s)*)([　 ]*)' % TOK.pattern, s)
        pre, lead = m.group(1), m.group(2); text = s[m.end():]
        k = k.lstrip(' 　')
        mk = re.match(r'^((?:%s)*)[　 ]*' % TOK.pattern, k); kpre = mk.group(1); ktext = k[mk.end():]
        if not lead:
            out.append(k); continue
        if text.startswith(KEEP_LEAD) or TOK.sub('', text).startswith(KEEP_LEAD):
            out.append(kpre + lead + ktext); continue
        c = bw(lead) + bw(text) / 2
        nl = max(0, int(round(c - bw(ktext) / 2)))
        out.append(kpre + '　' * (nl // 2) + ' ' * (nl % 2) + ktext)
    return ''.join(out), None


def wrap(text, width):
    """띄어쓰기에서 줄 나눔(강제 $n 유지). 낱말이 폭보다 길면 글자 단위로.
    제어 코드(«~c128, 48, 48» 처럼 공백 든 것)는 자리표 한 글자로 바꿔 두고 나눈 뒤 되돌린다."""
    toks = []
    def hold(m):
        if m.group(0) in ('$n', '$N'): return m.group(0)
        toks.append(m.group(0)); return chr(0xE000 + len(toks) - 1)
    text = TOK.sub(hold, text)
    back = lambda s: re.sub('[-]', lambda m: toks[ord(m.group(0)) - 0xE000], s)
    return [back(x) for x in _wrap(text, width)]


def _wrap(text, width):
    out = []
    for para in text.split('$n'):
        line = ''
        for word in re.split(r'(?<= )|(?<=[，．！？、。」』）…～：；])(?=[^，．！？、。」』）…～：；])', para):   # 띄어쓰기·문장부호 뒤에서 나눔
            if not line or bw(line + word.rstrip(' ')) <= width:
                line += word
            else:
                out.append(line.rstrip(' ')); line = word
            while bw(line.rstrip(' ')) > width:          # 긴 낱말
                cut = len(line)
                while bw(line[:cut]) > width: cut -= 1
                out.append(line[:cut]); line = line[cut:]
        out.append(line.rstrip(' '))
    return out


def check():
    tr = {}
    for f in sorted(glob.glob(W('tr', '*.tsv'))):
        for ln in open(f, encoding='utf-8-sig').read().split('\n')[1:]:
            c = ln.split('\t')                         # 번호·번역 두 칸 또는 번호·앞·원문·번역 네 칸
            if len(c) >= 2 and c[-1].strip(): tr[c[0]] = c[-1].strip()
    done, lay, bad, over, paged, wide = [], [], [], [], [], []
    seen = {}
    for o, n, t in src_rows():
        if t in seen:
            if seen[t] is not None: done.append((o, n, seen[t]))
            continue
        width, maxl, multi, region = box(t, o)
        pg = pages(t); outp = []; ok = True
        for i, (lead, body, tail) in enumerate(pg):
            key = '%s.%03d' % (o, i)
            if not body.strip() and not lead:
                outp.append(lead + body + tail); continue
            k = tr.get(key)
            if k is None: ok = False; break
            src_tok = [x for x in TOK.findall(body) if x not in ('$n',)]
            kr_tok = [x for x in TOK.findall(k) if x not in ('$n',)]
            if src_tok != kr_tok: bad.append((key, '토큰 %s≠%s' % (src_tok, kr_tok))); ok = False; break
            k = TOKSAFE(k, lambda s: re.sub(r'%[0-9]*[a-z]|[A-Za-z0-9]', lambda m: m.group() if m.group()[0] == '%' else chr(ord(m.group()) + 0xFEE0), s).translate(HALF))   # 반각 영숫자는 글꼴에 없음(실기 «메모리 카드()» — PS2 빠짐) → 전각              # 반각 부호 → 전각(«파이널» 과 같게, 숫자·공백은 반각)
            k = re.sub(r'([，．、。！？…」』）～♪：；・·]) +', r'\1', k)    # 문장부호 뒤 공백 지움(표준 목록 전부)
            if '\n' in body and '$n' not in body: k = k.replace('$n', '\n')    # 원문 줄바꿈이 \n 인 문자열(체험판 안내 ~h24)
            if 0x144100 <= int(o, 16) < 0x146900:   # 아래 흐르는 띠는 2바이트씩 읽음 → 반각 공백(1바이트)에서 짝이 어긋나 글자 깨짐·크래시(실기 2026-10-24) → 전각 공백
                k = TOKSAFE(k, lambda s: s.replace(' ', '　'))
            if any(a <= int(o, 16) < b for a, b in CENTER):
                k, why = center_lines(body, k)
                if why: bad.append((key, why)); ok = False; break
                multi = False                           # 줄을 직접 나눈 화면 — 자동 줄바꿈 안 함
            L = wrap(k, width) if multi else [k]
            for x in (L if multi else [y for i, y in enumerate(LBRK.split(L[0])) if i % 2 == 0]):
                if bw(x) > width:
                    if multi: bad.append((key, '폭 %d > %d: %s' % (bw(x), width, x)))
                    else: wide.append((key, bw(x), width, x))   # 한 줄 문자열(목록 제목 등) — 칸 폭은 실기로
            if len(L) > maxl and region in (1, 2):         # 자료관 = 4줄마다 쪽 넘김(노선 소개 13F820 등이 같은 상자에서 $k$p) ⏳명소·특산품 화면 실기
                paged.append(key)
                chunks = ['$n'.join(L[i:i + maxl]) for i in range(0, len(L), maxl)]
                lay.append('%s [%d줄/폭%d·쪽 나눔]\n  ' % (key, len(L), width) + '\n  ── 쪽 ──\n  '.join('\n  '.join(L[i:i + maxl]) for i in range(0, len(L), maxl)))
                outp.append(lead + '$k$p'.join(chunks) + tail); continue
            if len(L) > maxl: bad.append((key, '줄 %d > %d' % (len(L), maxl)))
            lay.append('%s [%d줄/폭%d]\n  ' % (key, len(L), width) + '\n  '.join(L))
            outp.append(lead + '$n'.join(L) + tail)
        if not ok: seen[t] = None; continue
        s = '$p'.join(outp)
        nb = len(s.encode('cp932', 'replace')) if not re.search('[가-힣]', s) else sum(
            2 if '가' <= c <= '힣' else len(c.encode('cp932', 'replace')) for c in s)
        if nb > n: over.append((o, n, nb))
        seen[t] = s; done.append((o, n, s))
    open(W('text', 'kr_elf.tsv'), 'w', encoding='utf-8').write(
        '위치\t바이트\t번역\n' + ''.join('%s\t%d\t%s\n' % (o, n, s.replace('\n', '\\n')) for o, n, s in done))
    open(W('text', 'layout.txt'), 'w', encoding='utf-8').write('\n'.join(lay) + '\n')
    sys.stdout.reconfigure(encoding='utf-8')
    print('완성 문자열 %d · 문제 %d · 원문보다 긴 문자열 %d · 자료관 쪽 나눔 %d · 한 줄 원문보다 넓음 %d(work/text/wide.txt, 실기 확인)'
          % (len(done), len(bad), len(over), len(paged), len(wide)))
    open(W('text', 'wide.txt'), 'w', encoding='utf-8').write(''.join('%s\t%d>%d\t%s\n' % w for w in wide))
    for b in bad[:30]: print(' ', *b)
    for o in over[:30]: print('  넘침', *o)


if __name__ == '__main__':
    {'export': export, 'check': check}[sys.argv[1]]()
