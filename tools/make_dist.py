# -*- coding: utf-8 -*-
r"""전차로 GO! 여정편 배포 묶음(파이널 make_dist 이식) — dist/DenshaDeGoRyojou_KR_<VER>/ : ISO xdelta + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat (2026-10-24)
  검증: 원본 ISO → xdelta 적용 → md5 = 빌드 결과(KR ISO) md5.
  python tools/make_dist.py   (먼저 python tools/build.py)
"""
import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
ROMNAME = 'Densha de Go! Ryojou-hen (Japan)'
SRC = r'C:\claude\roms\ps2\Densha de Go! Ryojou-hen (Japan).iso'
BUILD = r'C:\claude\project\densha-ryojou-kr-patch\work\build\Densha de Go! Ryojou-hen (Japan) [KR].iso'
NAME = 'DenshaDeGoRyojou_KR_' + VER
TITLE = '전차로 GO! 여정편 (PS2 일본판 SLPM-65148) 한글 패치 ' + VER


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


HEAD = """{rom}.iso (DVD 이미지, SLPM-65148) 에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.
"""

BODY = """

[ 적용 방법 ]

  1) 원본 ISO 파일을 이 폴더에 복사
       "{iso}"
  2) 한글패치_적용.bat 실행 → 이름 끝에 [KR] 이 붙은 ISO 가 만들어집니다
     (ISO 가 커서 몇 분 걸릴 수 있습니다)

  직접 적용:
    xdelta.exe -d -B 268435456 -s "원본 ISO" "{patch}" "결과 ISO"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 운전 안내·자료관 해설·조언 창·메모리카드 안내 등 게임 속 문장 전부
  - 메뉴 버튼·옵션·노선 선택(행선판·방향 띠·노선도 역 목록·역 이름)·차량 번호판
  - 운전 중 표시(평가 문구·정지 위치·속도 제한·신호·남은/까지 거리·브레이크 단·차내 신호 등)
  - 결과 화면·일시정지 메뉴·운전사 등록·이름 입력·안내 문구·효과음 글자
  - 영어 부제·로마자 역 이름·숫자, 이요 철도 전차 앞 작은 행선 방향막, 3D 운전석·객실 안 작은 간판은 원본 그대로입니다


[ 알려진 점 ]

  - 아직 끝까지 실기로 확인하지 못했습니다. 남은 일본어나 깨지는 글자가 있으면 알려 주세요.
  - 실행 파일이 바뀌어 PCSX2 의 게임별 설정(CRC)이 원본과 따로 잡힙니다.
    원본에서 쓰던 설정(디인터레이스 등)이 있으면 패치본에도 다시 맞춰 주세요.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
if not exist "%~dp0{iso}" (
  echo   [오류] 원본 ISO 파일을 이 폴더에 넣어 주세요 - readme 참고.
  pause & exit /b 1
)
echo   패치 중... 몇 분 걸릴 수 있습니다.
"%XD%" -d -f -B 268435456 -s "%~dp0{iso}" "%~dp0{patch}" "%~dp0{kiso}"
if errorlevel 1 (
  echo   [오류] 패치 실패 - 원본이 다를 수 있습니다 - readme 의 원본md5 확인.
  pause & exit /b 1
)
echo   완료: "{kiso}"
pause
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    iso = ROMNAME + '.iso'
    patch = NAME + '.xdelta'; pp = os.path.join(d, patch)
    subprocess.run([XDELTA, '-e', '-9', '-f', '-B', '268435456', '-s', SRC, BUILD, pp], check=True)
    chk = os.path.join(d, '_check.iso')
    subprocess.run([XDELTA, '-d', '-f', '-B', '268435456', '-s', SRC, pp, chk], check=True)
    o, want, got = md5(SRC), md5(BUILD), md5(chk)
    os.remove(chk)
    assert got == want, ('패치 적용 결과가 빌드와 다름', got, want)
    kiso = ROMNAME + ' [KR].iso'
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    readme = (TITLE + '\n' + '=' * 60 + '\n\n' + HEAD.format(rom=ROMNAME, o=o, d=want)
              + BODY.format(iso=iso, patch=patch))
    open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(
        BAT.format(iso=iso, patch=patch, kiso=kiso).replace('\n', '\r\n').encode('cp949'))
    zp = shutil.make_archive(d, 'zip', os.path.dirname(d), NAME)
    print('원본md5 %s → 패치md5 %s · %s %d B' % (o, want, patch, os.path.getsize(pp)))
    print('zip', zp, os.path.getsize(zp), md5(zp))
    for f in sorted(os.listdir(d)):
        print('  %-50s %12d' % (f, os.path.getsize(os.path.join(d, f))))


if __name__ == '__main__':
    main()
