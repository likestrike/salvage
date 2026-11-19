# SALVAGE 전투 프로토타입

기본 전투를 손으로 만져 보기 위한 시험판이다. 사격 → 차지 샷 → 무술 영화 학습 → 근접 어퍼컷으로 쓰러뜨리기까지 들어 있다.

## 실행

`game/index.html`을 브라우저로 연다. 설치도 서버도 필요 없다.

## 조작

| 키 | 동작 |
|---|---|
| `←` `→` (또는 `A` `D`) | 이동 |
| `Z` (또는 `Space`, `↑`, `W`) | 점프. 일찍 떼면 낮게 뛴다 |
| `X` (또는 `J`, `K`) | 공격 |

공격 버튼은 하나다. 무엇이 나가는지는 누르는 방법과 적과의 거리로 정해진다.

| 입력 | 나가는 것 | 맞은 적 |
|---|---|---|
| 짧게 누른다 | 기본 공격. 이어서 누르면 1타 → 2타 → 3타(마무리탄) | 1 · 2타: 멈춰 선다(경직). 3타: 뒤로 밀려난다(넉백) |
| 누르고 있다가 뗀다 | 차지샷. 눈금을 넘기면 1단, 끝까지 채우면 관통하는 2단 | 1단: 넉백. 2단: 날아간다 |
| 적에게 붙어서 누른다 (무술 영화를 학습한 뒤) | 너클 펀치 (숏어퍼 간장치기) | 공중에 뜬다(띄움) |
| 3타나 펀치를 누른 채로 있다가 뗀다 | 그 동작에 이어서 차지샷 | 넉백된 적: 추격(피해 1.5배). 띄운 적: 공중 추격(피해 2배) |
| 공중에서 누른다 | 공중 기본탄(세 번째는 마무리탄), 떼면 공중 차지샷 | 띄운 적은 조금 더 뜬다(저글, 3번까지) |

- 다음 타는 새로 눌러야 나간다. 누르고만 있으면 차지가 모인다.
- 동작 중에 미리 누른 공격 · 점프는 10틱 동안 기억했다가, 넘어갈 수 있는 순간(캔슬 창)에 나간다.
- 지상에서 공격하는 동안은 잠깐 발이 묶인다. 1 · 2타는 12틱, 3타는 22틱 뒤부터 다시 움직일 수 있다.
- 펀치를 맞힌 뒤에는 점프로 끊고 뛰어올라 공중에서 이어 쏠 수 있다.

테스트용 키: `R` 다시 시작 · `1` 너클 펀치 켜기/끄기 · `2` 양산형 소환 · `3` 드론 소환 · `H` 판정 상자 보기(펀치가 걸리는 거리와 주먹의 판정이 보인다) · `P` 일시 정지 · `M` 소리.

## 색상과 화면 스타일

게임은 스타일 3으로 고정이다 (2026-11-18). 스타일 1 · 2는 게임에서 뺐다. `V`로는 플레이어의 그림을 NX-07의 새 디자인 시안(NOVA)으로 바꿔 볼 수 있다 → 아래의 "NOVA 시안".

**프레임 속도** — 한 프레임을 보여 주는 시간(틱 = 1/60초). `assets/style_c/states/states.js`(스타일 3)와 `assets/nova/states/states.js`(NOVA 시안)의 값을 쓴다.

| 동작 | 예전 | 지금 | |
|---|---|---|---|
| 대기 | 4프레임 × 10틱 | 16프레임 × 9틱 | 키 그림 한 장을 파츠(머리 · 몸통 · 뒤쪽 팔 · 주포 · 다리)로 나눠 파츠별로 움직인다. 한 바퀴 2.4초, 눈도 깜빡인다 |
| 주포 확인 | — | 10프레임 × 9틱 | 4.8초 동안 가만히 서 있으면 주포를 들어 올려 확인한다. 그 뒤로는 9.6초마다. 움직이거나 쏘면 끊긴다 (`sim`의 `player.idleT`) |
| 달리기 | 4틱 | 5틱 | 한 바퀴의 보폭 92px ÷ 이동 속도 2.3px/틱 ÷ 8프레임 = 5틱. 더 느리게 하려면 이동 속도(`C.WALK`)도 함께 낮춰야 발이 미끄러지지 않는다 |
| 학습 자세 | 8틱 | 12틱 | |
| 적의 대기 · 걷기 | 12 · 8틱 | 18 · 14틱 | 적은 0.7px/틱으로 걷는다 |
| 등장인물 대기 | 14틱 | 20틱 | |

공격의 프레임은 동작 표(`src/sim.js`의 `ACTIONS`)가 정한다. 점프 · 착지는 오르내리는 속도로 고른다.

| 키 | 동작 |
|---|---|
| `V` | 플레이어의 캐릭터를 바꾼다: NX-07 · 스타일 3 (기본) ↔ NOVA 시안. 그림만 바뀌고 조작과 전투 규칙은 같다 |
| `C` | 캐릭터 색상을 차례로 바꾼다: A 올리브 드랩 → B 화이트 오렌지 → C 코발트 블루 → D 크림슨 레드 → E 차콜 블랙 → F 인더스트리얼 옐로. NOVA 시안은 색상이 한 가지다 |
| `B` | 등장인물 보기를 켜고 끈다. 미리네 · 삼촌 · BX-05의 대기 동작이 무대 시작 지점에 서 있다 (크기와 스타일을 보는 용도, 전투에는 관여하지 않는다) |
| `N` | 상태 시트 보기. 지금 캐릭터의 모든 상태가 제 프레임 시간으로 돈다. 한 화면에 다 들어가지 않아 누를 때마다 1쪽 → 2쪽 → 꺼짐으로 넘어간다 (NX-07 25가지, NOVA 27가지). 게임에 아직 넣지 않은 동작(회피, NOVA의 검 · 채찍 등)도 여기서 본다. 게임이 쓰지 않는 것은 이름이 회색이다 |

지금 고른 캐릭터와 색상은 화면 오른쪽 위에 표시된다. 주소로도 고를 수 있다: `index.html?look=nova`, `index.html?skin=c`.

미리보기 그림은 `preview/`에 있다: `state_sheets.png`(상태별 시트 전체), `states_before_after.gif`(처음 시트와 지금), `head_lock.png`(머리 고정 전과 후), `frames_*.png`(GIF를 프레임 단위로 풀어 본 것), `cast_styles.png`(등장인물과 NX-07의 키), `skins.png`. 스타일 1 · 2의 그림 파일(`assets/`의 한 장짜리 시트, `assets/style_b/`)과 비교 그림(`style_compare3.png` 등)은 기록으로 남아 있다.

## NOVA 시안

기획자가 `art/concept/nova/`에 넣은 NX-07 새 디자인의 스프라이트 시트를 그대로 올린 것이다 (기획서 9.10). 채택 여부는 정해지지 않았다.

- 스트립 27장(칸 160×160)은 `assets/nova/states/`에 있다. 원본을 고치지 않고 복사한 것이고, `tools/nova_sheets.py`가 만든다.
- 어느 동작에 어느 프레임을 쓰는지는 `art/sprites/nx07_nova/layout.json`에 적는다. 도구가 그것을 `assets/nova/states/states.js`로 옮기고, `render.js`의 `lookFrame`이 그 표로 프레임을 고른다.
- 전투 동작의 길이와 판정 틱은 `sim.js`의 것 그대로다. 표의 길이와 판정 프레임이 맞는지는 테스트가 확인한다.
- NOVA는 주포가 더 높이 있다 (발바닥에서 49~68px, 판정은 46px). 판정은 그대로 두고 탄의 그림만 주포 높이에 그린다.
- 서 있는 키가 97px로, 스타일 3의 NX-07 · 적(83px)보다 크다. 줄이지 않고 그대로 그린다.
- 장면: `preview/nova_ingame.png`. 주소 `index.html?demo=이름&look=nova`로 장면을 한 장씩 볼 수 있다.

## 진행

1. 시작할 때는 'LOCMAN' 게임팩의 전투 데이터만 들어 있다. 기본 공격 3타와 차지샷을 쓸 수 있다.
2. 앞의 양산형 둘: 3타로 밀어내고, 3타를 누른 채로 있다가 떼서 차지샷으로 추격한다.
3. 나무 상자 위의 비디오테이프(무술 영화)를 줍는다. 잠시 학습한 뒤 너클 펀치가 열린다.
4. 남은 양산형 셋: 붙어서 펀치로 띄우고, 누른 채로 있다가 떼서 공중 추격하거나 뛰어올라 이어 쏜다. 드론 둘은 뛰어올라 쏜다 (너클은 머리 위의 드론에게 닿지 않는다).
5. 적을 모두 쓰러뜨리면 끝난다. `2` · `3`으로 적을 더 불러 계속 시험할 수 있다.

## 들어 있는 것

| 요소 | 내용 |
|---|---|
| 플레이어 | 이동, 가변 점프, 기본 공격 3타, 2단계 차지샷, 너클 펀치, 공중 기본탄과 공중 차지샷, 학습 연출, 피격과 무적 시간, 기능 정지 |
| 적의 상태 | 서 있음(다가오기 · 조준 · 사격) → 경직 → 넉백 → 띄움 → 다운 → 기상. 체력이 0이면 날아가 떨어진 뒤 사라진다 |
| 타격 연출 | 공격마다 다른 타격 정지 · 흰 실루엣 번쩍임 · 화면 흔들림 · 밀어내는 힘. 큰 타격에는 화면 번쩍임, 폭발, "LAUNCH" · "CHASE" · "AIR CHASE" 표시 |
| 적 | NX 양산형(체력 12), RS-2 드론(체력 4, 떠 있어서 띄울 수 없다) |
| 무대 | 화면 세 개 넓이. 발판 둘(나무 상자, 컨테이너) |
| 화면 표시 | 체력, 학습한 매체 칸, 차지 게이지, 콤보 수, 맞은 적의 남은 체력 |
| 소리 | 브라우저에서 합성한 임시 효과음 |

## 전투 시스템

설계는 `docs/GAME_DESIGN.md` 4.3에 있다 (상태 전이도, 연결 구조, 동작의 타이밍, 판정, 타격 연출, 검증 기준). 코드는 그 표를 그대로 옮긴 것이다.

- `sim.ACTIONS` — 동작마다 준비 · 시동 · 판정 · 후딜의 틱, 캔슬 창, 그리고 "몇 틱까지 어느 프레임"(`anim`). 그림(`render.js`)은 이 표만 보고 프레임을 고르므로 판정과 어긋나지 않는다.
- `sim.HITS` — 공격마다 피해 · 타격 정지 · 번쩍임 · 흔들림 · 밀어내는 힘.
- 입력(`player.bufAttack` · `bufJump` · `bufCharge`)과 동작(`player.act`)과 그림은 따로 관리한다.
- 적이 맞으면 `applyHit`이 공격의 종류와 적의 지금 상태를 보고 다음 상태를 정한다. 이것이 연결의 전부다.

장면을 한 장으로 보려면 `index.html?demo=이름`: `shoot`(1타) · `combo3`(3타) · `knockback`(넉백) · `chase`(추격) · `charge` · `chargeshot` · `windup`(너클 통전) · `punch`(기폭) · `launch`(띄움) · `airchase`(공중 추격) · `drone` · `bot`.

## 수치

`src/sim.js` 맨 위의 `C` · `ACTIONS` · `HITS`에 모여 있다. 모두 시안이고 손으로 해 보며 고치면 된다. 고치면 기획서 4.3의 표도 함께 고친다.

| 값 | 지금 | 뜻 |
|---|---|---|
| `HITS.*.dmg` | 1 · 2 · 3 · 3 · 5 | 기본 1 · 2타 / 3타 / 너클 / 차지 1단 / 차지 2단의 피해 |
| `CHASE_MULT` / `AIR_CHASE_MULT` | 1.5 / 2 | 넉백된 적 · 띄운 적에게 차지샷을 맞혔을 때의 배율 |
| `CHARGE_MID` / `CHARGE_FULL` | 24 / 54틱 | 차지 단계에 이르는 시간 (60틱 = 1초) |
| `MELEE_RANGE` | 60px | 이 거리 안에 (땅에 선) 적이 있으면 공격이 너클 펀치가 된다 |
| `FIST` | 앞 8~52px, 위 16~72px | 주먹의 판정 |
| `BUFFER` / `CHARGE_BUFFER` | 10 / 20틱 | 공격 · 점프 / 차지샷을 기억하는 시간 |
| `CHAIN_KEEP` | 12틱 | 앞의 타가 끝난 뒤 이 안에 눌러야 다음 타로 이어진다 |
| `STAGGER` / `DOWN_TIME` / `GETUP_TIME` | 18 / 40 / 24틱 | 경직 / 다운 / 기상의 길이 |
| `JUGGLE_MAX` | 3 | 띄운 적이 기본탄으로 더 뜨는 횟수 |
| `TROOPER_HP` / `DRONE_HP` | 12 / 4 | 양산형 / 드론의 체력 |
| `PLAYER_HP` | 12 | 플레이어 체력 |

## 구조

| 파일 | 내용 |
|---|---|
| `src/sim.js` | 게임 로직. 화면과 무관하다. `step()` 한 번이 1/60초 |
| `src/render.js` | 상태를 받아 640×360 캔버스에 그린다 |
| `src/main.js` | 실행 루프, 조작, 소리, 안내 글자 |
| `assets/` | 스타일 1의 스프라이트 시트. 기본(`nx07_sheet`), 추가(`combat_sheet`), 어퍼컷(`uppercut_sheet`, 칸 96×144), 적(`nx_trooper`). `skins/`에 색상 B~F. 스타일 폴더마다 `cast_idle_1x.png`(등장인물 대기 시트, 4열 × 3행, 칸 112×112, 발바닥 줄 100)가 있다 |
| `assets/style_b/` | 스타일 2의 스프라이트 시트와 배경(`bg.png`). 위의 시트에 차지(`charge_sheet`)가 더 있다. `skins/`에 색상 B~F |
| `assets/style_c/` | **스타일 3 (기본).** `states/`에 상태별 시트가 있다: 상태마다 한 장, 25가지 (목록은 기획서 9.4). 칸 112×96, `melee`만 144×96. 색상 B~F는 `states/skin_b/`~`skin_f/`, 적(NX 양산형)은 `states/trooper/`, 프레임 수 · 프레임 시간 · 칸 크기는 `states/states.js`에 있다 (`tools/state_sheets.py`가 만든다). 배경(`bg.png`), 등장인물 대기 시트(`cast_idle_1x.png`)도 여기 있다 |
| `assets/nova/` | **NOVA 시안.** `states/`에 스트립 27장과 표(`states.js`)가 있다. 칸 160×160, 발바닥 줄 139 (`tools/nova_sheets.py`가 만든다) |
| `assets/px_a/` · `assets/px_b/` · `assets/px_c/` | 스타일 1·2·3의 새 처리 시험. 기획자 평가로 쓰지 않는다 (더 출렁인다). `V` 순환에서 뺐고 파일만 남겼다 |
| `assets/style_c_mono/` · `assets/style_c_line/` · `assets/style_c_grid/` | 스타일 3의 픽셀 다듬기 시험 A · B · C. `V` 순환에서는 뺐고 파일만 남겼다 (`?style=cm` `cl` `cg`로는 열리지 않는다) |
| `preview/` | 두 스타일, 색상 6종, 어퍼컷 장면을 나란히 놓은 미리보기 그림 |
| `test/sim.test.js` | 전투 로직 테스트 |

## 테스트

스프라이트의 움직임은 GIF를 프레임 단위로 풀어서 본다: `node tools/gif_frames.cjs out.png art/sprites/nx07_states/preview/run_before_after.gif halves` (Playwright가 있어야 한다. 처음 시트와 지금을 프레임마다 견줘 정수리와 머리 앞끝이 얼마나 움직였는지 숫자로 낸다).

```bash
node game/test/sim.test.js
```

전투 시스템의 검증 기준 일곱 가지(기획서 4.3), 그림과 판정의 일치, 캔슬 창, 드론, 학습, 피격을 확인하고, 마지막에 무대 전체를 자동으로 끝까지 진행해 본다. NOVA 시안의 동작 표가 전투 동작과 맞는지도 본다 (36개).

화면은 `index.html?demo=이름`으로 연다. 정해진 장면까지 진행한 뒤 한 번만 그리므로 캡처해서 확인할 수 있다.
이름: `start` `shoot` `combo3` `knockback` `chase` `charge` `chargeshot` `windup` `punch` `launch` `airchase` `learn` `drone` `bot`. 뒤에 `&look=nova`를 붙이면 NOVA 시안으로 그린다.

## 스프라이트를 바꿨을 때

```bash
# 플레이어 시트 → 적(NX 양산형) 시트
python tools/recolor_sheet.py --mode enemy art/sprites/nx07_sheet_1x.png game/assets/nx_trooper_1x.png
# 추가 시트의 장갑 색을 기존 시트에 맞추기
python tools/recolor_sheet.py --mode olive --rows 0,1 art/sprites/combat_sheet_1x.png game/assets/combat_sheet_1x.png
# 색상 B~F (b c d e f 를 차례로)
python tools/recolor_sheet.py --mode skin --skin b game/assets/nx07_sheet_1x.png game/assets/skins/nx07_b.png
python tools/recolor_sheet.py --mode skin --skin b --rows 0,1 game/assets/combat_sheet_1x.png game/assets/skins/combat_b.png
# 스타일 2 시트는 장갑이 더 어둡고 갈색에 가까워서 범위를 넓힌다
python tools/recolor_sheet.py --mode enemy --hue-lo 28 --sat-lo 0.06 game/assets/style_b/nx07_sheet_1x.png game/assets/style_b/nx_trooper_1x.png
python tools/recolor_sheet.py --mode skin --skin b --hue-lo 28 --sat-lo 0.06 --v-range 0.12,0.56 game/assets/style_b/nx07_sheet_1x.png game/assets/style_b/skins/nx07_b.png
# 어퍼컷·차지 시트: 장갑 색을 기본 시트에 맞춘 뒤, 위와 같은 방법으로 색상 B~F 를 만든다 (skins/uppercut_b.png, skins/charge_b.png)
python tools/recolor_sheet.py --mode match --like game/assets/nx07_sheet_1x.png art/sprites/nx07_uppercut_1x.png game/assets/uppercut_sheet_1x.png
python tools/recolor_sheet.py --mode match --like game/assets/style_b/nx07_sheet_1x.png art/sprites/styleb_uppercut_1x.png game/assets/style_b/uppercut_sheet_1x.png
python tools/recolor_sheet.py --mode match --gray --like game/assets/style_b/nx07_sheet_1x.png art/sprites/styleb_charge_1x.png game/assets/style_b/charge_sheet_1x.png
```
