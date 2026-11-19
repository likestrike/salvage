# 원화 → 횡스크롤 픽셀아트 스프라이트 파이프라인

> 대상 게임: 횡스크롤 액션 (Godot 4)
> 대상 캐릭터: NX-07A (범용 전투 안드로이드, 4등신)
> 이 문서는 claude.ai 대화에서 실제로 진행한 작업과 확정된 결정을 정리한 것이다. Claude Code에서 이 문서와 `scripts/`를 기준으로 이어서 작업한다.

---

## 0. 확정된 결정

| 항목 | 결정 |
|---|---|
| 아트 방향 | **픽셀아트** (고해상도 일러스트 + Spine 방식은 보류. 더 빠른 쪽 선택) |
| 캐릭터 비율 | **4등신** (8등신 원화는 픽셀로 줄였을 때 몸이 18px 폭으로 가늘어져 읽히지 않아 폐기) |
| 마스터 생성 방식 | **AI 도트풍 원화 → 그리드 복원** (셀마다 대표색 1개). 손으로 다시 그리지 않는다 |
| 마스터 크기 | **원화의 네이티브 그리드 그대로: 89×172px** (도트 1칸 = 원화 8px) |
| 팔레트 | 마스터에서 추출한 **24색**으로 잠금 |
| 외부 생성 서비스 | Higgsfield 사용하지 않음 |
| 애니메이션 1차 목표 | Idle / Run / Jump / Attack / Hit 5개 |

---

## 1. 전체 흐름

```
[1] AI 도트풍 원화 (4등신, 투명 배경 PNG)
      │  사람이 준비: 이미지 생성 AI로 "도트 스타일" 캐릭터 1장
      ▼
[2] 그리드 검출 → 셀 단위 색 스냅           scripts/restore_master.py
      │  proper-pixel-art, pixel_width 지정
      ▼
[3] 알파 이진화 · 크롭 · 팔레트 추출/잠금    (같은 스크립트)
      │  OKLab k-means 24색 → quantize
      ▼
[4] QA → 마스터 승인                       master.png + palette.gpl/.hex
      │  ★ 이후 모든 프레임의 기준 (팔레트·크기·앵커 상수)
      ▼
[5] 애니메이션 프레임 제작                  (미완 — 6장 참고)
      │  Idle·Hit: 마스터 직접 변형
      │  Run·Jump·Attack: 새 포즈 이미지 → [2]~[3] 동일 처리
      ▼
[6] 일관성 잠금                            pxl.py: quantize / align_frames / reduce_flicker
      ▼
[7] 시트 패킹 · 미리보기 · QA              pxl.py: pack_sheet / preview_gif / qa
      ▼
[8] Godot 4 임포트
```

---

## 2. 실제 진행 기록 (무엇을 했고 왜 바꿨나)

시행착오를 그대로 남긴다. 같은 실수를 반복하지 않기 위한 근거다.

### 시도 1: 8등신 일러스트 캐릭터 시트 → 64px 자동 픽셀화 (실패)
- 입력: 고해상도 캐릭터 시트(3면도, 표정, 무기, 포즈, 팔레트 포함)에서 **측면 전신**만 잘라냄
- 배경 제거: 흰 배경을 테두리에서 flood fill(명도>200, 채도<30), 그림자 줄 잘라냄
- 축소 방식 3가지 비교
  - 단순 k-means + 다수결 축소 → 얼룩덜룩, 외곽선 소실
  - PixelOE(contrast 모드, thickness 1~3) → 더 지저분함
  - 고정 팔레트 + "시안 우선 / 외곽선 우선" 규칙 다수결 + 고립 픽셀 제거 → 그나마 나음
- **결론: 일러스트를 기계적으로 줄이면 원화 디테일 밀도 때문에 무조건 뭉개진다.**

### 시도 2: 8등신 측면을 손으로 다시 찍음 (사용자 기각: "너무 이상함")
- 18×64px로 픽셀을 직접 배치
- 깔끔하지만 8등신 비율 자체가 64px에서 안 읽힘 → 사용자가 **4등신 AI 도트 원화**를 새로 제공

### 시도 3: 4등신 AI 도트 원화 → 64px로 강제 축소 + 얼굴 다시 그림 (사용자 기각: "얼굴이 왜 커졌냐")
- 원화 네이티브 해상도(키 약 170px)를 64px로 2.7배 축소 → 눈이 뭉개져 얼굴을 손으로 다시 찍음 → **원화 비율이 바뀜**
- 슈트 색이 외곽선과 거의 같아 덩어리로 보이는 문제도 있었음
- **결론: 손으로 다시 그리면 원화와 달라진다. 목표 크기에 억지로 맞추지 않는다.**

### 시도 4: 그리드 복원 (채택 ✅)
- 사용자 지시: "AI가 도트처럼 뽑은 거니까 그리드로 나눠서 영역마다 색 찍어라"
- 그리드 크기 찾기
  - 직접 구현한 주기 검출(경계 강도 투영 + 주기/위상 탐색): x=11.04, y=9.04처럼 축마다 다르게 나와 **불안정**
  - proper-pixel-art 자동 검출: pixel_width 6(2배 업스케일 기준) → 실제의 약 1/3 크기 셀로 **과분할**
  - **수동 지정 pixel_width=8 → 원화와 시각적으로 일치** ✅ (9는 약간 퍼짐)
- 결과: **89×172px, 원래 약 144색 → 24색으로 잠금**, QA 통과(반투명 0, 팔레트 이탈 0)

---

## 3. 단계별 상세

### [1] 원화 준비 규칙
- **투명 배경 PNG** (반투명 가장자리가 많아도 됨. 알파 128 기준으로 이진화)
- 이미지 생성 AI에 "pixel art / 도트 스타일"로 요청한 이미지여야 한다. 일반 일러스트는 2장의 시도 1처럼 실패한다
- 캐릭터 1명, 전신, 잘린 곳 없음
- 비율은 4등신 전후(머리가 커야 얼굴이 읽힌다)

### [2]~[4] 마스터 생성
```bash
pip install proper-pixel-art pillow numpy
python scripts/restore_master.py input.png out/ --pixel-width 8 --colors 24 --name nx07a
```
출력:
- `nx07a.png` — 1배율 마스터 (이게 기준)
- `nx07a_x4.png` — 확인용 4배 nearest 확대
- `nx07a_palette.hex`, `nx07a_palette.gpl` — Aseprite에서 바로 불러옴
- `nx07a_info.json` — 크기, 사용한 pixel_width, 색 수, QA 결과

**pixel_width 정하는 법 (자동 검출 믿지 말 것)**
1. 원화를 400% 확대해서 도트 한 칸이 몇 px인지 눈으로 잰다 (NX-07A는 약 8~9px)
2. 후보값(예: 8, 9)으로 각각 돌려서 x4 미리보기를 원화 옆에 놓고 비교
3. 눈, 엠블럼, 외곽선이 원화와 같은 모양인 값을 채택
4. 검산: `캐릭터 키(px) / pixel_width ≈ 결과 높이`

**팔레트 색 수 기준** (원화와의 평균 오차, RGB 합)
| 색 수 | 평균 오차 |
|---|---|
| 16 | 6.0 |
| 24 | 4.2 ← 채택 |
| 32 | 2.8 |

### [5] 애니메이션 (다음 할 일)

| 동작 | 프레임 | fps | 방법 |
|---|---|---|---|
| Idle | 4 | 6 | 마스터 직접 변형: 상체 1px 상하(호흡), 머리 0~1px 지연 |
| Hit | 3 | 12 | 마스터 직접 변형: 1프레임 흰색 플래시(불투명 픽셀 전부 팔레트 최밝은 색), 2~3프레임 뒤로 2~3px 밀림 + 상체 기울임 |
| Run | 6 | 12 | 새 포즈 필요 |
| Jump | 4 (준비/상승/정점/하강) | 상태별 재생 | 새 포즈 필요 |
| Attack | 6 (예비 2 → 타격 1~2 → 회복 2) | 14 | 새 포즈 필요 |

**새 포즈(Run/Jump/Attack) 만드는 규칙**
- 이미지 생성 AI에 넣는 레퍼런스는 **마스터 픽셀아트를 nearest로 6배 확대한 것**. 일반 원화를 넣으면 프레임마다 다시 해석해서 스타일이 흔들린다
- 프롬프트 요소: `same character as reference, identical palette and proportions, pixel art, side view facing the same direction as reference, N frames in a single row, equal cell size, transparent or flat solid background, no motion blur, no anti-aliasing`
- 한 번에 4~6프레임까지만 요청
- 받은 시트 → **프레임별로 자른 뒤** `restore_master.py`의 그리드 복원 단계를 프레임마다 적용 (pixel_width는 프레임 이미지 기준으로 다시 잼)
- 팔레트는 새로 뽑지 말고 **마스터 팔레트로 quantize**
- 생성 도구는 미정(Higgsfield 제외). 후보: 사용 중인 이미지 생성 API, PixelLab(유료, Aseprite 확장), Aseprite 수작업

### [6] 일관성 잠금 (`pxl.py`)
```python
from pxl import *
pal = np.array([[int(h[i:i+2],16) for i in (0,2,4)] for h in open("nx07a_palette.hex").read().split()], np.uint8)
frames = [quantize(f, pal) for f in raw_frames]          # 팔레트 재잠금 + 알파 이진화
frames = align_frames(frames, CELL_W, CELL_H)            # 발 앵커를 셀 하단 중앙에 고정
frames = reduce_flicker(frames)                          # 프레임 간 미세 색 떨림 제거
print(qa(frames, pal, CELL_W, CELL_H))                   # 빈 리스트면 통과
```
- 셀 크기: 마스터 89×172 기준으로 **공격·점프 여유를 둔 고정 셀** (예: 128×192). 모든 동작이 같은 셀 크기를 쓴다
- 점프는 앵커 정렬 대신 의도한 높이 오프셋을 수동으로 준다

### [7] 시트 출력
```python
sheet, meta = pack_sheet({"idle": idle, "run": run, "jump": jump, "attack": attack, "hit": hit}, CELL_W, CELL_H)
sheet.save("nx07a_sheet.png"); json.dump(meta, open("nx07a_sheet.json", "w"))
for name, fr in anims.items(): preview_gif(fr, f"preview_{name}.gif", scale=3)
```
- 행 = 동작, 열 = 프레임, 셀 사이 1px 패딩
- 결과물: 시트 PNG(1배율), meta JSON, 동작별 GIF, 팔레트. zip으로 묶지 않는다

### [8] Godot 4 임포트
- 프로젝트 설정 → Rendering → Textures → Default Texture Filter: **Nearest**
- 2D 픽셀 스냅 켜기 (Snap 2D Transforms/Vertices to Pixel)
- `CharacterBody2D` + `AnimatedSprite2D`, SpriteFrames에서 시트를 셀 크기로 분할
- 원점은 발 앵커(셀 하단 중앙)에 맞춘다
- 좌우 방향은 `flip_h` (마스터는 화면 왼쪽을 향한 파이팅 자세 — 오른쪽 이동 시 반전)

---

## 4. 반드시 지킬 원칙
1. **마스터가 기준이다.** 모든 프레임은 마스터의 팔레트·도트 크기·외곽선을 따른다
2. **손으로 다시 그려서 맞추지 않는다.** 원화와 달라진다(시도 2·3 기각 사유)
3. **목표 크기에 억지로 맞추지 않는다.** 크기는 원화의 네이티브 그리드가 정한다. 작게 원하면 원화를 처음부터 그 크기의 도트로 다시 받는다
4. **1배율로 작업, 확대는 nearest로만**
5. **색을 섞지 않는다.** bicubic·평균 축소 금지, 알파는 0/255만
6. **pixel_width 자동 검출을 믿지 않는다.** 후보를 돌려 원화와 나란히 비교한다
7. **사람이 마지막에 손본다.** 자동은 초벌까지. 고립 픽셀, 끊긴 외곽선은 Aseprite에서 수정

---

## 5. 파일 구성
```
PIXEL_SPRITE_PIPELINE.md     이 문서
scripts/
  pxl.py                     팔레트 추출·quantize·다수결 축소·외곽선·앵커 정렬·플리커 제거·시트 패킹·QA·GIF
  restore_master.py          AI 도트 원화 → 그리드 복원 마스터 (검증됨: NX-07A → 89×172, 24색, QA 통과)
```

## 6. 환경
- Python 3.11+, `pip install proper-pixel-art pillow numpy`
- (선택) `opencv-python` — 일러스트 배경 제거용. 투명 PNG면 불필요
- 편집: Aseprite (팔레트 .gpl 불러오기)
