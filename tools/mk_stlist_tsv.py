# -*- coding: utf-8 -*-
"""노선도 역 목록(416/552/600×112, 세로쓰기 역 이름 줄) 번역 표 → work/text/ui_stlist.tsv (2026-10-24)
  역 이름 = work/text/ui_station.tsv 음역 + 아래 보충. 열 = 잉크 덩어리(가는 세로줄은 버림), 개수가 역 수와 다르면 멈춤.
  글자 크기는 그림 안 가장 긴 이름에 맞춰 통일(cell=), 위 맞춤."""
import os, sys
from collections import Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import label_kr as L, sub_dump as S  # noqa: E402

ST = {}
for ln in open(os.path.join(ROOT, 'work/text/ui_station.tsv'), encoding='utf-8').read().split('\n')[1:]:
    a = ln.split('\t')
    if len(a) >= 3 and a[1]: ST[a[1]] = a[2].replace(' ', '')
ST.update({'平和通一丁目': '헤이와도리1초메', '函館どっく前': '하코다테도쿠마에', '駒場車庫': '코마바샤코', '湯の川温泉': '유노카와온센',
           '萱町六丁目': '카야마치6초메'})

ENO = '藤沢 石上 柳小路 鵠沼 湘南海岸公園 江ノ島 腰越 鎌倉高校前 七里ヶ浜 稲村ヶ崎 極楽寺 長谷 由比ヶ浜 和田塚 鎌倉'
IYO1 = '松山駅前 大手町 西堀端 南堀端 市役所前 県庁前 大街道 勝山町 警察署前 上一万 南町 公園前 道後温泉'
IYO2 = '市駅前 南堀端 市役所前 県庁前 大街道 勝山町 警察署前 上一万 南町 公園前 道後温泉'
IYO3 = '本町六丁目 本町五丁目 本町四丁目 本町三丁目 西堀端 南堀端 市役所前 県庁前 大街道 勝山町 警察署前 上一万 南町 公園前 道後温泉'
IYO_C = '市駅前 南堀端 市役所前 県庁前 大街道 勝山町 警察署前 上一万 平和通一丁目 赤十字病院前 鉄砲町 清水町 高砂町 木屋町 本町六丁目 萱町六丁目 古町 宮田町 松山駅前 大手町 西堀端 南堀端 市駅前'
HK_D = '五稜郭公園前 中央病院前 千代台 堀川町 昭和橋 千歳町 新川町 松風町 函館駅前 市役所前 魚市場通 十字街 末広町 大町 函館どっく前'
HK_Y = '五稜郭公園前 中央病院前 千代台 堀川町 昭和橋 千歳町 新川町 松風町 函館駅前 市役所前 魚市場通 十字街 宝来町 青柳町 谷地頭'
HK_KD = '駒場車庫 駒場車庫前 競馬場前 深堀町 柏木町 杉並町 五稜郭公園前 中央病院前 千代台 堀川町 昭和橋 千歳町 新川町 松風町 函館駅前 市役所前 魚市場通 十字街 末広町 大町 函館どっく前'
HK_KY = '駒場車庫 駒場車庫前 競馬場前 深堀町 柏木町 杉並町 五稜郭公園前 中央病院前 千代台 堀川町 昭和橋 千歳町 新川町 松風町 函館駅前 市役所前 魚市場通 十字街 宝来町 青柳町 谷地頭'
HK_YD = '湯の川 湯の川温泉 市民会館前 駒場車庫前 競馬場前 深堀町 柏木町 杉並町 五稜郭公園前 中央病院前 千代台 堀川町 昭和橋 千歳町 新川町 松風町 函館駅前 市役所前 魚市場通 十字街 末広町 大町 函館どっく前'
HK_YY = '湯の川 湯の川温泉 市民会館前 駒場車庫前 競馬場前 深堀町 柏木町 杉並町 五稜郭公園前 中央病院前 千代台 堀川町 昭和橋 千歳町 新川町 松風町 函館駅前 市役所前 魚市場通 十字街 宝来町 青柳町 谷地頭'
KEI1 = '嵐山 嵯峨駅前 鹿王院 車折 有栖川 帷子ノ辻 太秦 蚕ノ社 山ノ内 三条口 西院 四条大宮'
KEI2 = '帷子ノ辻 常盤 鳴滝 高雄口 御室 妙心寺 竜安寺道 等持院 北野白梅町'
LISTS = {
    '847F1CC0': ENO, '847FDCC0': ENO, '84809E40': '藤沢 石上 柳小路 鵠沼 湘南海岸公園 江ノ島',
    '84815CC0': IYO1, '84821CC0': IYO1, '8482DD00': IYO2, '84839D00': IYO2, '84867CC0': IYO3, '84873CC0': IYO3,
    '8487FDC0': '松山駅前 大手町 西堀端 南堀端 市役所前 県庁前 大街道',
    '8488BC80': '古町 宮田町 松山駅前 大手町 西堀端 南堀端 市駅前 南堀端 市役所前 県庁前 大街道 勝山町 警察署前 上一万 南町 公園前 道後温泉',
    '84919540': '湯の川 湯の川温泉 市民会館前 駒場車庫前 競馬場前 深堀町 柏木町 杉並町 五稜郭公園前',
    '849254C0': HK_D, '849314C0': HK_D, '8493D4C0': HK_Y, '849494C0': HK_Y,
    '84955500': KEI1, '84961540': KEI2, '8496D500': KEI1, '84979540': KEI2, '84985640': '嵐山 嵯峨駅前 鹿王院 車折 有栖川 帷子ノ辻',
    '848DD280': HK_KD, '848ECA80': HK_KD, '848FC280': HK_KY, '8490BA80': HK_KY,
    '848484C0': IYO_C, '848594C0': IYO_C, '84899CC0': HK_YD, '848AACC0': HK_YY, '848BBCC0': HK_YD, '848CCCC0': HK_YY,
}


def cols(ix, n):
    sub = ix[21:110]; bg = Counter(sub.ravel().tolist()).most_common(1)[0][0]
    ink = sub != bg
    for gap in (3, 2, 1):
        xs = np.nonzero(ink.sum(0) > 0)[0]; out = []; s = p = xs[0]
        for x in xs[1:]:
            if x - p > gap: out.append((int(s), int(p) + 1)); s = x
            p = x
        out.append((int(s), int(p) + 1))
        out = [c for c in out if c[1] - c[0] >= 4 and ink[:, c[0]:c[1]].sum() > 20 and c[1] < ix.shape[1] - 1]   # 오른쪽 끝 테두리 줄 버림   # 가는 세로줄·점 버림
        if len(out) == n: return out
    raise SystemExit('열 수 %d ≠ 역 %d' % (len(out), n))


I = L.index(); f = open(S.ISO, 'rb'); rows = ['번호\t원문\t번역\t메모']
for k, lst in LISTS.items():
    names = lst.split(); t = L.Tex(f, *I[k]); c = cols(t.idx, len(names))
    kr = [ST[x] for x in names]
    cell = 13   # 이름별로 칸 높이에 맞춰 자동으로 줄어듦(긴 이름만 작아짐)
    boxes = ' '.join('box=%d,20,%d,110:fv' % (max(0, a - 2), min(t.w, b + 2)) for a, b in c)
    rows.append('%s\t%s\t%s\t%s cell=%d top' % (k, '|'.join(names), '|'.join(kr), boxes, cell))
open(os.path.join(ROOT, 'work/text/ui_stlist.tsv'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
print(len(rows) - 1)
