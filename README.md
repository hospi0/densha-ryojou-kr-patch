# 전차로 GO! 여정편 (PS2 일본판 SLPM-65148) 한글 패치

- 대상: `Densha de Go! Ryojou-hen (Japan).iso`
- 원본md5 `0A8C89CAE4D34113AA2A202F40974ADB` → 패치md5 `BAA8D1F97C1FA1F2B5D489E6A27E42B3`
- 배포 파일은 릴리즈의 zip(xdelta + 적용 bat + readme).

## 구성
- `tools/build.py` — 원본 ISO 복사본에 글꼴 한글·실행 파일 평문(다시 채우기)·UI 그림(`tools/gfx_build.py`)을 넣음
- `tools/label_kr.py` — UI 텍스처 글자 바꾸기 렌더러(`work/text/ui_*.tsv` 표, `preview` 로 원본|새것 미리보기)
- `tools/units.py`·`tools/elf_pack.py` — 실행 파일 문장 조판·재배치, 번역은 `work/tr/`
- `tools/make_dist.py` — 배포 묶음(xdelta 적용 결과 md5 검산)
- 조사·작업 기록: `docs/00_초기조사.md`
