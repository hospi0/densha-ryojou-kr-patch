# -*- coding: utf-8 -*-
"""신호기 패널(104×144·128×144) 번역 표 자동 생성 → work/text/ui_signal.tsv (2026-10-24)
  아래 낱말(116행~) = 채움색으로 進行/停止/注意 판정. 검은 이름판·흰 판은 화소 모양(md5)으로 판정 — 표 PLATES.
  흰 판 세로(높이 > 폭) = 세로쓰기(:v). 숫자판(1 2·14 13 12 11)·화살표는 그대로.
  python tools/mk_signal_tsv.py"""
import hashlib, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

BLACK = {'bf545c08': ('場内', '장내'), 'e64ec400': ('場内', '장내'), '2754c828': ('場内', '장내'), 'f528ee26': ('場内', '장내'),
         '1cf71e3e': ('出発', '출발'), '006f9b0a': ('出発', '출발'),
         'af3c0f7e': ('第1閉塞', '제1폐색'), 'e1be215b': ('第1閉塞', '제1폐색'),
         '6f9bbf01': ('第2閉塞', '제2폐색'), '074cb8f5': ('第2閉塞', '제2폐색'),
         'fd312900': ('遠方', '원방'), '3a245458': ('遠方', '원방'), '87f0c71d': ('遠方', '원방'), '46fae5b1': ('遠方', '원방')}
WHITE = {h: ('電車用信号', '전차용 신호') for h in ('6cf98937', '4afce328', 'fd6d4dea', '45fc0996', 'faf07db8')}
WHITE.update({h: ('電車用信号', '전차용신호') for h in ('6f80e407', 'ad6f8be6', '2c91baff', 'fb6b8ebe', '6df6aec8', '96125d2b', '3239a1f4', '6181f070')})
WHITE.update({'93fc7de5': ('進入許可灯', '진입 허가등'), 'bd50e14c': ('進入許可灯', '진입 허가등'),
              'ff55a373': ('合図灯', '신호등'), 'dc53677a': ('合図灯', '신호등')})
WORD = {'g': ('進行', '진행'), 'r': ('停止', '정지'), 'y': ('注意', '주의')}


def comps(m):
    lab = np.zeros(m.shape, int); n = 0; out = []
    for y, x in zip(*np.nonzero(m)):
        if lab[y, x]: continue
        n += 1; st = [(y, x)]; lab[y, x] = n; pts = []
        while st:
            a, b = st.pop(); pts.append((a, b))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c, d = a + dy, b + dx
                if 0 <= c < m.shape[0] and 0 <= d < m.shape[1] and m[c, d] and not lab[c, d]:
                    lab[c, d] = n; st.append((c, d))
        ys = [p[0] for p in pts]; xs = [p[1] for p in pts]
        out.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1, len(pts)))
    return out


def main():
    I = L.index(); f = open(S.ISO, 'rb')
    bs = json.load(open(os.path.join(ROOT, 'work/cat/bysize.json')))
    rows = ['번호\t원문\t번역\t메모']; miss = 0
    for k in [k for k in bs['104x144'] + bs.get('128x144', []) if k not in ('840BE120', '840C0570')]:   # 일시정지 메뉴(같은 128×144) 제외 — ui_menu.tsv
        t = L.Tex(f, *I[k]); op = t.P[:, 3][t.idx] > 0; lum = t.lum()[t.idx]
        items = []
        for x0, y0, x1, y1, n in comps(op[:116]):
            if n < 20: continue
            crop = t.idx[y0:y1, x0:x1]
            h = hashlib.md5(crop.tobytes() + t.P[np.unique(crop)].astype(np.uint8).tobytes()).hexdigest()[:8]
            if h in BLACK: items.append(((x0, y0, x1, y1), BLACK[h], False))
        for x0, y0, x1, y1, n in comps((lum > 215) & op & (np.arange(t.h)[:, None] < 116)):
            if n < 40: continue
            h = hashlib.md5(t.idx[y0:y1, x0:x1].tobytes()).hexdigest()[:8]
            if h in WHITE: items.append(((x0, y0, x1, y1), WHITE[h], (y1 - y0) > (x1 - x0)))
        ys, xs = np.nonzero(op[116:])
        if len(xs):
            x0, y0, x1, y1 = xs.min(), ys.min() + 116, xs.max() + 1, ys.max() + 117
            c = t.P[np.bincount(t.idx[y0:y1, x0:x1][lum[y0:y1, x0:x1] > 80].ravel(), minlength=16).argmax(), :3]
            col = 'g' if c[1] > c[0] * 1.3 else 'r' if c[0] > c[1] * 1.5 else 'y'
            items.append(((max(0, x0 - 1), y0 - 1, min(t.w, x1 + 1), min(t.h, y1 + 1)), WORD[col], False))
        if not items: miss += 1; continue
        rows.append('%s\t%s\t%s\t%s' % (k, '｜'.join(i[1][0] for i in items), '|'.join(i[1][1] for i in items),
                                        ' '.join('box=%d,%d,%d,%d%s' % (tuple(int(v) for v in i[0]) + (':v' if i[2] else '',)) for i in items)))
    open(os.path.join(ROOT, 'work/text/ui_signal.tsv'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    print('신호기 %d장(글자 없음 %d)' % (len(rows) - 1, miss))


if __name__ == '__main__':
    main()
