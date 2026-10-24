# -*- coding: utf-8 -*-
r"""이름 입력 자판 한글화 (2026-10-24): 실행 파일 0x14AC40·0x14AD00·0x14ADC0 자판 표 3벌(각 90칸 = 6줄×15칸, 180바이트).
  게임은 칸 «위치»로 ←(89번째)·終(90번째)을 판정하고 전각 공백(0x8140)만 코드에서 건너뜀 → 칸 수·자리 그대로.
  1벌(히라가나 자리) = 받침 없는 기본 85자, 2벌(가타카나 자리) = 이름에 흔한 받침 음절 85자, 영문 = 形號号車→형호번차·終→끝.
  python tools/kbd_kr.py → work/tr/tr_11.tsv 에 세 줄(이미 있으면 바꿈)."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAIL = '－　　←끝'
K1 = ('가거고구그나너노누느다더도두드'
      '라러로루르마머모무므바버보부브'
      '사서소수스아어오우으자저조주즈'
      '차처초추츠카커코쿠크타터토투트'
      '파퍼포푸프하허호후흐기니디리미'
      '비시이지치키티피히해')
K2 = ('김박최정강장윤임한신권황안송전'
      '홍문양손배백남심유민준연현영성'
      '진혜은경희석철훈동상태재원용종'
      '광명범혁숙순선빈율람솔별찬건환'
      '완운근길일열웅형국승식창예래채'
      '새세레메베제개내대매')
EN = ('ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ　　　　'
      '１２３４５６７８９０　　　　　．－！？／형호번차' + '　' * 34 + '←끝')
ROWS = {'14AC40.000': K1 + TAIL, '14AD00.000': K2 + TAIL, '14ADC0.000': EN}

for k, s in ROWS.items():
    assert len(s) == 90, (k, len(s))
for a, b in ((K1, K2),):
    assert len(set(a)) == len(a) == 85 and len(set(b)) == len(b) == 85 and not set(a) & set(b)
assert all(c in K1 for c in '하스피')

p = os.path.join(ROOT, 'work', 'tr', 'tr_11.tsv')
L = [l for l in open(p, encoding='utf-8-sig').read().split('\n') if l and l.split('\t')[0] not in ROWS]
L += ['%s\t%s' % kv for kv in ROWS.items()]
open(p, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
sys.stdout.reconfigure(encoding='utf-8')
for k, s in ROWS.items():
    print(k); [print('  ' + ' '.join(s[i:i + 15])) for i in range(0, 90, 15)]
