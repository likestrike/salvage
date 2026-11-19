# SALVAGE

횡스크롤 픽셀 액션 게임. 컨셉 단계이고, 기본 전투를 시험하는 프로토타입이 `game/`에 있다.

## 기준 문서

작업 전에 읽는다. 설정이나 기획이 바뀌면 코드보다 문서를 먼저 고친다.

@docs/STORY.md
@docs/GAME_DESIGN.md

그림을 뽑거나 고치는 작업이면 `docs/ART_STYLE.md`(화풍 기준)도 먼저 읽는다.

## 규칙

- `.env.local`의 내용은 읽지도 출력하지도 않는다. fal.ai 키는 `tools/fal_image.py`가 직접 읽는다.
- 문서의 `[해석]` · `[제안]` · `[미정]` 표기를 지킨다. 기획자가 정하지 않은 내용을 확정처럼 쓰지 않는다.
- 캐릭터가 나오는 그림을 뽑을 때는 `reference/`의 해당 설정화를 참조 이미지로 넣는다.
- NX-07은 소년형 안드로이드다. 체형을 프롬프트에 글로 '가는 허리 · 긴 다리'처럼 적으면 여성스럽게 나온다. 설정화(시안 A 시트)의 해당 시점 그림을 잘라 참조로 넣고 그 체형(큰 헬멧, 4등신이 조금 못 되는 키, 굵은 정강이와 부츠)을 그대로 따르게 한다.
- **화풍은 지금 그림체로 확정됐다.** 기획자가 요청하지 않으면 화풍을 바꾸거나 바꿔 보는 시도를 하지 않는다. 화풍을 바꿔 본 두 번의 시도는 모두 채택되지 않았다 (`docs/ART_STYLE.md`).
- 캐릭터 시트·설정화·일러스트는 `tools/fal_image.py --keep-style`로 뽑는다. `art/style_anchor/`의 기준 그림, 화풍 설명, 화풍 고정 문구, 모델이 자동으로 붙는다.
- `art/style_anchor/`, `art/prompts/_style_illustration.txt`, `art/prompts/_style_lock.txt`는 고치지 않는다. 셋 중 하나라도 바뀌면 그림체가 달라진다.
- 뽑은 그림은 기준 그림과 나란히 놓고 확인한다. 선, 형태의 둥글기, 메카 디테일의 양, 색, 눈이 다르면 쓰지 않고 다시 뽑는다.
- 그림체 레퍼런스(`reference/reference_그림체*.jpg`)는 다른 회사의 작품이다. 캐릭터 디자인은 가져오지 않는다.
- 컨셉 단계에서는 키 비주얼보다 캐릭터 시트를 우선 만든다.
- 캐릭터 설정화 묶음(일곱 장)은 `tools/setting_sheets.py`로 만든다 (기획서 9.4.1). 정면 · 측면 · 후면은 한 장에 함께 그려서 나눈다 (따로 뽑으면 비례가 달라진다). 그림 안에 글자를 넣지 않는다. 뽑은 뒤의 손질은 `setting.json`의 `clean`에 적고, 손보기 전의 그림은 `*_raw.png`로 남긴다.
- 생성한 시트의 한글 글자는 확대해서 오타를 확인한다. ㅡ에 세로획이 잘못 붙은 오타(측→축, 등→동, 블→볼, 죽→족)는 `tools/fix_hangul.py`로 고친다.
- 생성한 그림에 기존 게임이나 브랜드의 캐릭터·아이콘이 섞여 나오면 지우거나 우리 것으로 바꾼다.
- **NX-07의 픽셀 마스터는 승인된 두 벌이다** (기획자 승인 2026-11-19, 기획서 9.11.6): 스카프 없음 `art/characters/nx07/pixel/nx07_px_base.png`(v2 C36, 저항군 합류 전) · 스카프 있음 `art/characters/nx07/pixel/nx07_px_scarf.png`(v3 S2 주황, 합류 뒤). 스카프는 저항군에 합류한 뒤에 두른다 (STORY.md 4장). 그리는 규칙은 규격 `art/characters/nx07/pixel/nx07_px_spec.json`(그림 `nx07_px_spec.png`)을 따른다: 키 36칸 · 마스터의 팔레트만(새 색 없음) · 외곽선 없음 · 빛은 뒤-위에서 · 주포는 먼 쪽 팔. 두 마스터의 칸은 고치지 않는다 (흠이 보이면 보고한다). **스카프는 층이다**: 프레임은 스카프 없는 몸으로 짜고 스카프는 그 위에 얹어, 두 벌을 함께 낸다 (층을 빼면 한 칸도 다르지 않아야 한다). 머리 · 몸통 · 주포 팔은 프레임마다 칸 단위로 옮기기만 한다 `[제안]`. 애니메이션은 표(`art/characters/nx07/anim/rig.json` · `<동작>/timeline.json`)로 적고 `tools/pixel_anim.py`로 만들고 검사한다. AI가 프레임을 직접 그리게 하지 않는다.
- **게임 화면의 도트는 새 방향으로 간다** (기획자 결정 2026-11-19, 기획서 9.11.2): 검은 외곽선 없음(색과 밝기로 실루엣을 읽힌다) · 캐릭터 키 36칸 (처음에는 약 56칸, 9.11.5에서 바뀜) · 재질마다 2톤 안팎의 큰 색 덩어리 · 16색 안팎 · 내부 해상도는 36칸에 맞춰 320×180 근처 `[제안]` (처음에는 약 480×270). 승인을 꾸며 적지 않는다 (`approve`는 기획자가 대화에서 승인했을 때만. 보고 정한 그림은 `--saw`, 한 말은 `--quote`로 원문 그대로 적는다).
- **새 도트의 캐릭터는 캐릭터 픽셀 파이프라인으로 만든다** (기획서 9.11.7). 설명서 `docs/pipeline/CHARACTER_PIPELINE.md`를 먼저 읽는다. 도구는 `tools/pixpipe.py`, 캐릭터마다 설정 파일 `art/characters/<id>/pixel/pipeline.json` 하나 (채운 예 = NX-07). 순서: 등록 → 단순화안 → 1단계 뽑기(밑그림 없이) → 밑그림 → 2단계 뽑기(격자 그대로) → 마스터 → 재기 → 비교 그림 → **기획자가 고름** → 층 → **승인** → 규격 → 애니메이션 → **기획자 평가**. 캐릭터에 묶인 값은 설정 파일에 두고 코드에 두지 않는다. 프롬프트는 공통 틀(`art/prompts/pipeline/_stage1.txt` · `_stage2.txt`)에 캐릭터 문장을 채워 만든다. 이미지 생성은 설정의 상한(`generate.budget`) 안에서만. 성공은 형식(통과 / 실패)과 그림(참고 숫자와의 거리)을 따로 보고하고, 마지막 판정은 기획자의 눈이다. 도구(`pixpipe.py` · `pixel_anim.py` · `pixel_measure.py`)나 공통 틀을 고치면 `python -X utf8 tools/pixpipe.py verify nx07`이 92/92 같음인지 본다. 진행 상태는 `pixpipe.py status <id>`와 보고 화면에 보인다.
- **캐릭터 픽셀 스튜디오** (`픽셀스튜디오.bat` → `tools/pixstudio.py`, 기획서 9.11.10 · 설명서 12장)는 기획자가 혼자 원화를 올리고 → 픽셀 후보를 만들고 → 리뷰 · 결정하는 화면이다. PC 안의 작은 서버(`127.0.0.1`, 토큰 확인)로 돈다 — 게임 · 보고 화면의 "더블클릭으로 연다" 규칙과는 별개다. 스튜디오는 일을 직접 하지 않고 `pixpipe.py`의 명령을 셸 없이 부른다 (같은 일을 두 벌로 짜지 않는다. 스튜디오가 쓰는 명령: `defaults` · `fix` · `unfix` · `reject` · `candidates` · `lineup`). 캐릭터에 묶이지 않은 기본 문장은 `art/characters/_pipeline/studio_defaults.json` `[제안]`. 승인된 캐릭터는 스튜디오에서 다시 뽑거나 손보지 않는다. 화면을 고치면 `--practice`(이미지 생성 없이 미리네의 그림을 복사)로 브라우저에서 흐름을 밟아 보고, 연습으로 만든 캐릭터는 지운다.
- **지금 게임에 들어 있는 그림은 스타일 3(중간 등신)이다.** 적 · 배경 · 기본 캐릭터는 스타일 3이다. 새 그림이 준비될 때까지 그대로 두고, 게임 코드(640×360 · 스프라이트)는 아직 바꾸지 않았다. 아래의 스타일 3 규칙(상태별 시트 등)은 지금 게임에 들어 있는 그림의 규칙이다. NX-07의 키는 170cm다 (미리네 142cm보다 크다).
- **픽셀 아트에서는 에너지 주포가 왼팔이다** (오른쪽을 볼 때 먼 쪽 팔. 앞쪽 팔은 보통의 건틀릿과 검은 손). 설정화 · 기획서 4.1 · 지금 게임의 스프라이트는 오른팔이다. 설정화는 고치지 않는다 (기획서 9.11.2).
- 기획자가 넣은 NX-07 새 디자인 시안 **NOVA**(`art/concept/nova/`)는 게임에서 `V`로 바꿔 볼 수 있다 (기획서 9.10). 채택 여부는 `[미정]`이고, 설정 문서(170cm · 소년형)는 그대로다. NOVA의 컨셉과 스트립은 기획자의 원본이므로 고치지 않는다 (줄이기 · 다시 칠하기 · 프레임 수정 없음). 게임에는 `tools/nova_sheets.py`로 그대로 복사하고, 어느 동작에 어느 프레임을 쓰는지는 `art/sprites/nx07_nova/layout.json`에 적는다. `V`는 그림만 바꾼다: 전투 규칙(`sim.js`)은 캐릭터에 따라 달라지지 않는다.
- 전투는 기획서 4.3의 설계(공격이 적의 상태를 바꾸고, 그 상태가 다음 공격의 기회가 된다)를 따른다. 동작의 타이밍 · 캔슬 창 · 프레임은 `game/src/sim.js`의 `ACTIONS`, 타격은 `HITS` 표에 있고, 기획서 4.3의 표와 같은 값이어야 한다. 한쪽을 고치면 다른 쪽도 고친다. 이동 · 점프 · 충돌(`moveBody`)은 전투 때문에 바꾸지 않는다.
- 스타일 3의 스프라이트(지금 게임에 들어 있는 그림)는 상태별 시트다 (`art/sprites/nx07_states/`, 상태마다 한 장). 원본 시트에서 `tools/state_sheets.py`로 만든다. 고정하는 것은 발바닥 줄과 기준 위치의 가로 자리뿐이고, 정수리·키·머리의 오르내림은 상태마다의 허용 범위(`layout.json`의 `allow`) 안에서 그려진 대로 둔다. 프레임은 게임 해상도의 px 단위로만 옮긴다 (기본 시트의 상태는 머리 아래가 처음 시트와 픽셀까지 같아야 한다). 머리는 `parts/head.png` 한 장을 모든 프레임이 함께 쓰고, 그 프레임에 그려져 있던 머리의 자리에 놓는다 (처음 시트에 없던 움직임을 만들지 않는다). 코드로 줄을 눌러 동작을 만들지 않는다 (눌려 보인다는 평가). 대기처럼 거의 움직이지 않는 상태는 파츠 리그로 만든다: 키 그림 한 장을 파츠 지도(`parts/idle_parts.png`)대로 나누고 파츠를 px 단위로 옮긴다. 장갑 위의 작은 하늘색 점은 지운다 (`clean_cyan`). 검사(`gate.json`)를 통과해야 쓰고, 만든 GIF는 `tools/gif_frames.cjs`(Playwright)로 프레임 단위로 풀어 처음 시트보다 움직임이 늘지 않았는지 본다. 줄이는 방법은 처음 방식(5px 블록) 그대로 둔다 (기획서 9.9).
- 스타일 3의 새 시트를 뽑을 때는 설정화, 기본 시트 원본(`stylec_nx07_sheet_raw.png`), 배치 안내 그림(`art/prompts/stylec_guide_*.png`)을 참조로 넣는다. 그래도 크기와 색이 조금 다르게 나오므로 `layout.json`의 `zoom` · `match`로 맞춘다.
- 전투 로직(`game/src/sim.js`)을 고치면 `node game/test/sim.test.js`를 돌린다. 화면은 `game/index.html?demo=이름`을 브라우저로 캡처해서 확인한다 (`game/README.md`).
- 게임은 `game/index.html`을 더블클릭해서 열 수 있어야 한다. ES 모듈과 `fetch`를 쓰지 않고, 그림의 픽셀을 읽는 처리는 미리 파일로 만들어 둔다 (file://에서는 막힌다).
- 캐릭터 등록부(`art/characters/<id>/character.json`, 기획서 9.11)는 파일을 경로로 가리킨다. 파일을 옮기거나 복사하지 않는다. 캐릭터의 그림을 새로 만들거나 바꾸면 `python tools/charpipe.py build`를 돌려 검사와 보고 화면(`art/characters/index.html`)을 다시 만든다. 바뀐 파일의 새 판 받아들이기(`accept`)와 승인(`approve`)은 기획자가 대화에서 말했을 때만 적는다. 승인을 꾸며 적지 않는다.

## 폴더

| 경로 | 내용 |
|---|---|
| `docs/` | 스토리 바이블, 게임 기획서, 화풍 기준 |
| `reference/` | 설정화와 그림체 레퍼런스 (원본, 수정하지 않는다) |
| `reference/pixel_style/` | 기획자가 준 도트 스타일 참고 그림 7장 (`reference_도트1~7.png`, 기획서 9.11.1 · 9.11.3). `analysis/` = 참고 그림을 1배로 복원해 재던 옛 스크립트와 비교 그림 (9.11.3 · 9.11.4, 공개하지 않는다. 측정 코드는 `tools/pixel_measure.py`로 옮겼고 파이프라인은 이 폴더에 기대지 않는다). **다른 회사의 작품이다.** 그리는 방식만 참고하고, 이미지 생성기에 올리지 않는다 |
| `docs/pipeline/` | `CHARACTER_PIPELINE.md` = 캐릭터 픽셀 파이프라인 설명서 (기획서 9.11.7). `PIXEL_SPRITE_PIPELINE.md` · `pxl.py` · `restore_master.py` = 기획자가 넣은 원본 (고치지 않는다) |
| `art/style_anchor/` | 화풍 기준 그림 (고치지 않는다) |
| `art/prompts/` | 이미지 생성 프롬프트 (`_style_illustration.txt` = 화풍 설명, `_style_lock.txt` = 화풍 고정 문구, `setting/` = 설정화 묶음의 프롬프트와 참조 그림) |
| `art/concept/` | 캐릭터 시트, 컨셉 이미지 (`archive_v2/` = 채택하지 않은 화풍 시도, `nova/` = 기획자가 넣은 NX-07 새 디자인 시안의 컨셉과 스프라이트 시트. 원본, 수정하지 않는다. `setting/` = 캐릭터 설정화 묶음: 캐릭터마다 정면 · 측면 · 후면 · 얼굴 · 신체 · 무기(소지품) · 포즈 일곱 장, 기획서 9.4.1) |
| `art/sprites/` | 스프라이트 시트 (`*_raw` = 생성 원본, `*_1x` = 게임 해상도). `nx07_states/` = 스타일 3의 NX-07 상태별 시트, `nx07_side/` = PixelLab에 넣을 옆모습 한 장, `cast_idle/` = 등장인물 대기 시트, `nx07_nova/` = NOVA 시안을 게임에 올리는 표 |
| `art/pipeline_lab/` | 캐릭터 제작 파이프라인 실험 (기획서 9.11). NX-07 을 만든 기록이고 옮기지 않는다 (NX-07 의 `pipeline.json`이 `pinned`로 가리킨다). 새 캐릭터의 작업 파일은 여기가 아니라 `art/characters/<id>/pixel/work/`에 둔다. `pixel_master/` = 도트풍 그림 → 픽셀 마스터 실험 (뽑힌 원본 `*_raw.png`, 후보 비교 그림, 마스터, 팔레트, info, 최종 비교 그림 `compare.png`와 그것을 만드는 `make_compare.py`). 프롬프트와 안내 그림은 `art/prompts/pipeline/` |
| `art/pipeline_lab/pixel_style/` | 참고 그림의 도트 스타일 견본 (기획서 9.11.1, 견본 단계). `scaled/` = E1 마스터를 줄인 것 · `sample_flat/` · `sample_dark/`(격자가 밀려 버림) · `sample_dark2/` = 새 견본의 뽑힌 그림과 마스터, `compare.png` = 비교 그림. 만드는 스크립트 `make_scaled.py` · `grid_check.py` · `make_compare.py`. `v1/` = NX-07 픽셀 마스터 v1 후보 (기획서 9.11.2, 주포 왼팔 · 외곽선 없음, 승인 전): `a_selout/` · `b_flat/`(추천) · `c_flat2/`, `compare.png`, 스크립트 `make_guide.py` · `grid_check_v1.py` · `make_master.py` · `make_compare_v1.py`. `v2/` = v2 후보 (기획서 9.11.4, 두 번에 나눠 뽑기, 실험 · 승인 전): `s1/`(1단계, 밑그림 없이) · `guides/` · `s2/`(2단계) · `A36/` · `C36/` · `C48/` · `B48/`, `compare.png`, 스크립트 `make_guide.py` · `make_prompts.py` · `make_master.py` · `make_compare_v2.py`. 기획자가 C36의 형태를 골랐다. `v3_scarf/` = C36에 스카프를 칸으로 얹은 변형 S1~S4 (기획서 9.11.5, 실험 · 승인 전): 변형마다 1배 · ×12 · 팔레트 · info, `compare.png`, 스크립트 `make_scarf.py`(스카프 칸 표 · C36 칸이 그대로인지 검사) · `measure_scarf.py` · `make_compare_scarf.py`. 참고 그림과 견준 비교 그림은 `reference/pixel_style/analysis/compare_v2_vs_ref.png` (공개하지 않음) |
| `art/characters/` | 캐릭터 등록부 (Character Master, 기획서 9.11). `registry.json` = 목록, `<id>/character.json` = 캐릭터마다의 원화 · 픽셀 마스터 후보 · 스프라이트의 경로 · 출처 · 해시 · 승인 · 기록, `<id>/check.json` = 원화 검사 결과. `<id>/pixel/pipeline.json` = 캐릭터 픽셀 파이프라인의 설정, `<id>/pixel/work/` = 그 작업 파일(뽑힌 그림 · 밑그림의 칸 · 후보 마스터 · 층 · 재기 · 비교 그림 · 뽑기 기록 `gen_log.json`), `<id>/pixel/<id>_px_*.png` = 승인된 마스터, `_pipeline/` = 파이프라인 공통 (`reference_targets.json` = 참고 그림에서 잰 숫자, `pipeline.template.json` = 설정의 빈 틀). `nx07/pixel/` = 승인된 NX-07 픽셀 마스터 두 벌과 규격 (`work/verify/verify.json` = 재현 검증 결과), `nx07/anim/` = 애니메이션의 표(`rig.json` · `<동작>/timeline.json`) · 프레임 · 검사 · 시트 · GIF · 비교 그림(`preview/`). `index.html` = 더블클릭으로 여는 보고 화면 (`_report/` = 화면의 스크립트 · 자료 · 미리보기 그림) |
| `art/aseprite/` | Aseprite Lua 스크립트로 빈 캔버스에 그린 스프라이트 시험 (기획서 9.7). `preview/`는 Aseprite 없이 같은 스크립트로 만든 미리보기 |
| `game/` | 전투 프로토타입 (브라우저용). 실행·조작·구조는 `game/README.md` |
| `tools/` | `fal_image.py` (이미지 생성), `setting_sheets.py` (캐릭터 설정화 묶음: 기존 시트에서 세 시점을 잘라 참조로 넣고, 뽑고, 정면 · 측면 · 후면으로 나누고, 한눈에 보기 그림을 만든다, 기획서 9.4.1), `process_sheet.py` (스프라이트 시트 후처리. 처음 시트를 만든 방식), `state_sheets.py` (원본 시트를 상태별 시트로 나눈다. 키 위치를 재서 맞추고 검사한다, 기획서 9.9), `nova_sheets.py` (NOVA 시안의 스트립을 게임 폴더로 복사하고 표를 쓴다, 기획서 9.10), `gif_frames.cjs` (GIF를 Playwright로 프레임 단위로 풀어 늘어놓고 프레임마다의 움직임을 잰다), `pixelize_sheet.py` (새 처리 시험. 쓰지 않는다, 기획서 9.5.1), `recolor_sheet.py` (시트 색 바꾸기), `fix_hangul.py` (시트의 한글 오타 수정), `outline_sheet.py` (스프라이트의 외곽선을 한 색으로 통일. 시험 중), `repack_sheet.py` (격자를 찾아 줄인 시트를 게임용 칸으로 다시 깔기. 시험 중), `monopix/` (mono-pix 로 시트 줄이기. 시험 중), `pixel_master.py` (도트풍 그림 한 장 → 픽셀 마스터. 칸 크기 후보 여러 개를 원본 옆에 나란히 놓고 사람이 고른다, 기획서 9.11), `pixpipe.py` (캐릭터 픽셀 파이프라인: 단계마다 명령 하나, 기획서 9.11.7 · `docs/pipeline/CHARACTER_PIPELINE.md`), `pixel_measure.py` (픽셀 마스터를 재는 함수: 형식과 그림을 따로, 참고 그림의 격자 복원), `pixel_anim.py` (승인된 픽셀 마스터의 부위와 자세 표로 애니메이션 프레임을 짜고 검사한 뒤 시트 · GIF · 비교 그림을 내보낸다. 층 없음 / 있음 두 벌, 기획서 9.11.6), `pxl.py` (`docs/pipeline/pxl.py`를 그대로 복사한 것. 팔레트 · quantize · 검사 함수), `charpipe.py` (캐릭터 등록부: 등록 · 파일 더하기 · 해시 다시 재기 · 원화 검사 · 보고 화면, 새 판 받아들이기 · 승인 적기, 기획서 9.11), `pixstudio.py` + `pixstudio/` (캐릭터 픽셀 스튜디오: 기획자가 쓰는 화면, PC 안의 서버. 켜기는 루트의 `픽셀스튜디오.bat`, 기획서 9.11.10) |
