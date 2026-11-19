"""스프라이트 시트를 상태별 시트로 나눈다. 프레임마다 키 위치를 재서, 프레임 사이에 출렁이지 않게 맞춘 뒤 줄인다.

  python tools/state_sheets.py art/sprites/nx07_states/layout.json
  python tools/state_sheets.py art/sprites/nx07_states/layout.json --measure   # 재기만 하고 저장하지 않는다

하는 일
  1. 원본 시트(큰 그림, 마젠타 배경)의 칸마다 키 위치를 잰다: 발바닥 줄, 앞발·뒷발, 머리 중심, 정수리, 키.
  2. 상태마다 기준 키 위치(anchor)가 모든 프레임에서 같은 자리에 오도록 프레임을 통째로 옮긴다.
     고정하는 것은 두 가지뿐이다: 땅에 닿은 프레임의 발바닥 줄과, 기준 위치의 가로 자리.
     정수리·키·머리의 오르내림은 그려진 대로 둔다 (상태마다 allow 로 허용 범위를 주고, 넘으면 실패로 적는다).
     옮기는 양은 게임 해상도의 px 단위(원본 scale px 의 배수)뿐이다. 그래서 줄인 픽셀은 process_sheet.py 로 만든 처음 시트와 똑같고,
     프레임의 자리만 px 단위로 바뀐다. 반 px 안쪽의 어긋남은 건드리지 않는다 (건드리면 프레임마다 픽셀이 다르게 뽑혀 오히려 출렁인다).
  3. process_sheet.py 와 같은 방법(scale x scale 블록에서 가장 많은 색)으로 줄인다. 팔레트는 원본 시트마다 뽑는다
     (기본 시트의 상태가 처음 시트와 색까지 같게). 새로 뽑은 시트는 장갑 색을 첫 시트에 맞춘다 (match).
  4. 머리 고정: 머리는 키 그림 한 장(parts/head.png)을 모든 프레임이 함께 쓴다.
     놓는 자리는 그 프레임에 그려져 있던 머리의 자리(정수리)다. 그려진 머리가 키 머리보다 길었던 프레임은 그 머리를 다 지우고
     목을 그만큼 늘려 메운다 (턱 줄이 남지 않는다). 머리의 움직임은 처음 그려진 그대로다.
     parts/head.png 을 고치고 다시 돌리면 모든 프레임의 머리가 함께 바뀐다.
  5. 파츠 리그(rig): 대기처럼 거의 움직이지 않는 상태는 프레임을 따로 그리지 않는다. 키 그림 한 장을 파츠(다리 · 몸통 · 뒤쪽 팔 · 머리 · 주포)로
     나누고, 파츠를 px 단위로 옮겨 프레임을 만든다. 파츠 안의 픽셀은 모든 프레임에서 같다 (줄을 눌러 없애지 않는다).
     파츠가 겹치는 자리는 아래 파츠를 2px 늘려 두어서, 위 파츠가 움직여도 틈이 생기지 않는다.
  6. 상태마다 가로 한 줄 시트로 저장하고, 줄인 그림에서 키 위치를 다시 재서 검사한다 (gate.json).

layout.json
  scale    원본의 큰 픽셀 한 칸이 몇 px 인지      cell   [너비, 높이] (1x)      base   칸 안에서 발바닥이 닿는 줄 (1x, 0부터)
  colors   팔레트 색 수                           out    상태별 시트를 둘 폴더 (없으면 layout.json 이 있는 폴더)
  shared_anchors   여러 상태가 같은 x 를 쓰는 anchor 종류. 예: ["front_foot"] → 서 있는 상태끼리 앞발이 같은 자리에 온다
  head     {"from": [상태, 프레임], "rows": 머리 높이(1x px), "file": "parts/head.png", "min_match": 0.7}
           file 이 이미 있으면 그 그림을 쓰고, 없으면 from 의 프레임에서 잘라 만든다
  pack     모든 상태를 한 장(상태 = 행)으로도 저장할 파일 이름
  clean_cyan   장갑 위에 흩어진 작은 하늘색 점을 지운다: 이 크기(px) 이하이고, 몸에 붙어 있고, 큰 하늘색(주포의 빛, 이펙트)에서 9px 안이 아닌 것.
               머리(엠블럼 · 눈 · 귀)는 건드리지 않는다. 상태에 keep_specks: true 를 주면 그 상태는 건너뛴다 (전류가 흐르는 근접 등).
               상태에 clean_cyan 을 따로 적으면 그 상태만 그 크기를 쓴다 (새로 뽑은 시트에 점이 더 크게 찍혔을 때)
  game     {"dir": 게임의 그림 폴더, "id": 이름} — use 가 false 가 아닌 상태의 시트를 복사하고, 게임이 읽는 표(states.js)를 쓴다
           (게임은 file:// 로 열리므로 JSON 을 fetch 하지 못한다. 그래서 표를 스크립트 파일로 둔다)
  sheets   [{src, grid: [열, 행], states: [...]}]  원본 시트가 여러 장일 때. 한 장이면 src · grid · states 를 바로 적어도 된다
     cell    이 시트의 상태가 쓰는 칸 크기 (이펙트가 커서 칸을 넓혀야 할 때)
     zoom    원본을 키우는 배율. 새로 뽑은 시트가 기준 시트보다 작게 그려졌을 때 맞춘다 (원본 단계에서 키우므로 도트가 뭉개지지 않는다)
     match   true 면 장갑 색을 첫 시트의 색에 맞춘다 (recolor_sheet.py 의 match). gray: true 면 회색으로 나온 장갑도 바꾼다
     before  {"sheet": 예전 1x 시트, "cell": 칸 크기} — 있으면 같은 방법으로 재서 나란히 보여 준다 (상태의 before_cols 로 견줄 열을 줄 수 있다)
  states   [{name, row, cols 또는 cells: [[행, 열], ...], kind, anchor, ticks, loop, ground, ground_from, x, head_lock, allow, use}]
     kind    planted  발을 땅에 붙인 상태 (대기, 사격)      cycle  제자리에서 도는 상태 (달리기)
             air      공중 프레임이 있는 상태. ground 에 적은 프레임만 땅에 닿아 있고, 나머지는 그려진 높이를 지킨다
             single   한 장짜리
     anchor  front_foot · rear_foot · feet(두 발의 가운데) · head · body(몸 전체의 무게중심) · none(옮기지 않는다)
     ticks   한 프레임을 몇 틱(1/60초) 동안 보여 줄지
     allow   이 상태의 허용 범위 (1x px). sole = 발바닥이 줄에서 벗어나도 되는 양, anchor_x = 기준 위치의 가로 흔들림,
             top = 정수리의 오르내림, height = 키의 변화, head_y = 머리의 오르내림. 적지 않으면 kind 의 기본값을 쓴다
     head_lock  true 면 이 상태의 프레임에 키 머리를 놓는다. 머리 모양이 키 그림과 많이 다른 프레임(min_match 아래)은 건너뛴다
     use     false 면 비교용으로만 만든다 (게임이 쓰지 않는다)
     center_y  공중에서 도는 몸(띄워진 적)에 쓴다: 몸의 무게중심을 칸의 이 줄에 놓는다. ground 는 [] 로 둔다
     min_match  이 상태에서만 쓰는 머리 겹침 한계 (0 이면 모든 프레임에 키 머리를 놓는다)
     head_anchor  "neck" 이면 키 머리를 목 줄에 맞춰 놓는다. 한 장짜리 그림에 쓴다 (움직이는 상태에 쓰면 머리가 오르내린다)
     rig     {"parts": 파츠 지도(칸 크기의 그림, 파츠마다 한 색), "colors": {파츠: "#rrggbb"}, "order": [뒤 → 앞],
              "tracks": {파츠: [[dx, dy], ...]}, "blink": {"file": 눈 감은 머리, "frames": [프레임 번호]}}
             cols 의 첫 프레임이 키 그림이다. tracks 의 길이만큼 프레임을 만든다. 적지 않은 파츠는 움직이지 않는다

필요한 것: pip install numpy pillow opencv-python
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from process_sheet import despill, downscale, key_mask  # noqa: E402

# 허용 범위의 기본값 (1x px). 상태의 allow 로 바꾼다. None = 재기만 하고 검사하지 않는다.
ALLOW = {
    "planted": {"sole": 0, "anchor_x": 1, "top": 2, "height": 2, "head_y": 2},
    "cycle": {"sole": 0, "anchor_x": 1, "top": 3, "height": None, "head_y": 3},
    "air": {"sole": 0, "anchor_x": 1, "top": None, "height": None, "head_y": None},
    "single": {},
}
CHECKS = (("sole", "sole_drift"), ("anchor_x", "anchor_x_range"), ("top", "head_top_range"), ("height", "height_range"),
          ("head_y", "head_y_range"))


def body_of(opaque: np.ndarray) -> np.ndarray | None:
    n, lab, st, _ = cv2.connectedComponentsWithStats(opaque.astype(np.uint8), connectivity=8)
    if n <= 1:
        return None
    return lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))      # 가장 큰 덩어리 = 몸 (떨어진 이펙트는 재지 않는다)


def measure(opaque: np.ndarray, unit: int) -> dict | None:
    """불투명 마스크에서 키 위치를 잰다. unit = 게임 해상도의 1px 이 이 그림에서 몇 px 인지 (원본 5, 1x 는 1)."""
    body = body_of(opaque)
    if body is None:
        return None
    ys = np.flatnonzero(body.any(axis=1))
    top, bot = int(ys[0]), int(ys[-1])
    height = bot - top + 1
    band = body[max(top, bot - 3 * unit + 1): bot + 1]              # 발바닥에서 3px(1x) 위까지 = 발
    cols = np.flatnonzero(band.any(axis=0))
    runs = np.split(cols, np.flatnonzero(np.diff(cols) > 1.2 * unit) + 1)
    feet = [(int(r[0]), int(r[-1])) for r in runs]
    head = body[top: top + max(1, round(height * 0.27))]
    return {
        "top": top, "bot": bot, "height": height, "feet": feet,
        "rear_foot": (feet[0][0] + feet[0][1]) / 2, "front_foot": (feet[-1][0] + feet[-1][1]) / 2,
        "feet_c": (feet[0][0] + feet[-1][1]) / 2, "head": float(np.nonzero(head)[1].mean()), "body": float(np.nonzero(body)[1].mean()),
        "boot": feet[-1][1] - feet[-1][0] + 1, "body_y": float(np.nonzero(body)[0].mean()),
    }


def anchor_of(keys: dict, kind: str) -> float | None:
    return None if kind == "none" else keys[{"feet": "feet_c"}.get(kind, kind)]


def shifted(cell: np.ndarray, dx: int, dy: int, cw: int, ch: int) -> tuple[np.ndarray, int]:
    """칸 그림을 (dx, dy) 만큼 옮겨 cw x ch 캔버스에 놓는다. 캔버스 밖으로 나가 잘린 불투명 px 수도 돌려준다."""
    out = np.zeros((ch, cw, 4), dtype=np.uint8)
    h, w = cell.shape[:2]
    x0, y0 = max(0, dx), max(0, dy)
    x1, y1 = min(cw, dx + w), min(ch, dy + h)
    if x1 > x0 and y1 > y0:
        out[y0:y1, x0:x1] = cell[y0 - dy: y1 - dy, x0 - dx: x1 - dx]
    lost = int((cell[..., 3] > 0).sum() - (out[..., 3] > 0).sum())
    return out, lost


# ───────────── 머리 ─────────────
def head_span(body: np.ndarray) -> tuple[int, int, int]:
    """정수리 줄, 목 줄(머리의 마지막 줄), 머리의 왼쪽 끝. 목 = 헬멧의 가장 넓은 줄 아래에서 폭이 처음으로 가장 좁아지는 줄."""
    top = int(np.flatnonzero(body.any(axis=1))[0])
    w = []
    for y in range(top, min(body.shape[0], top + 32)):
        idx = np.flatnonzero(body[y])
        runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if len(idx) else []
        w.append(max((len(r) for r in runs), default=0))            # 줄에서 가장 길게 이어진 구간 (뒤로 뻗은 깃이나 팔은 뺀다)
    widest = int(np.argmax(w[:14]))
    lo = widest + 4
    neck = top + lo + int(np.argmin(w[lo: lo + 14]))
    x0 = int(np.flatnonzero(body[top: neck + 1].any(axis=0))[0])
    return top, neck, x0


def cut_head(f: np.ndarray, rows: int) -> np.ndarray:
    """키 그림에서 머리(목 줄까지 rows 줄)를 잘라 낸다."""
    body = body_of(f[..., 3] > 0)
    top, neck, _ = head_span(body)
    y0 = neck - rows + 1
    band = body[y0: neck + 1]
    xs = np.flatnonzero(band.any(axis=0))
    patch = f[y0: neck + 1, xs[0]: xs[-1] + 1].copy()
    patch[~band[:, xs[0]: xs[-1] + 1]] = 0
    return patch


def find_head(f: np.ndarray, patch: np.ndarray) -> dict:
    """이 프레임에서 키 머리를 놓을 자리. 세로는 그려진 머리의 정수리, 가로는 머리 모양이 가장 잘 겹치는 자리다."""
    rows, w = patch.shape[:2]
    pm = patch[..., 3] > 0
    body = body_of(f[..., 3] > 0)
    top, neck, x0 = head_span(body)
    hh = min(rows, neck - top + 1)                                  # 그려진 머리와 키 머리가 함께 있는 높이만 견준다
    pad = 3
    best = (0.0, x0)
    for x in range(max(pad, x0 - 4), min(f.shape[1] - w - pad, x0 + 4) + 1):
        win = body[top: top + hh, x - pad: x + w + pad]             # 머리 둘레만 견준다 (머리 옆으로 든 주포 같은 것은 빼고)
        key = np.zeros_like(win)
        key[:, pad: pad + w] = pm[:hh]
        iou = (win & key).sum() / max(1, (win | key).sum())
        if iou > best[0]:
            best = (float(iou), x)
    return {"top": top, "neck": neck, "x": best[1], "match": best[0], "body": body}


def put_head(f: np.ndarray, patch: np.ndarray, at: dict, x: int | None = None, at_neck: bool = False) -> np.ndarray:
    """프레임의 머리(정수리~목 줄)를 지우고 키 머리를 같은 정수리에 놓는다. at_neck 이면 목 줄에 맞춰 놓는다 (한 장짜리 그림)."""
    rows, w = patch.shape[:2]
    pm = patch[..., 3] > 0
    x = at["x"] if x is None else x
    top, neck = at["top"], at["neck"]
    g = f.copy()
    xa, xb = max(0, x - 3), x + w + 3
    own = at["body"][top: neck + 1, xa: xb]
    g[top: neck + 1, xa: xb][own] = 0
    if at_neck:                                                     # 머리의 맨 아랫줄을 목 줄에 맞춘다. 정수리의 높이가 달라진다
        y0, cut = max(0, neck - rows + 1), max(0, rows - neck - 1)
        g[y0: neck + 1, x: x + w][pm[cut:]] = patch[cut:][pm[cut:]]
        return g
    g[top: top + rows, x: x + w][pm] = patch[pm]
    for y in range(top + rows, neck + 1):                           # 그려진 머리가 더 길었다 → 빈 줄을 몸의 첫 줄(목)로 메운다
        g[y, xa: xb] = f[neck + 1, xa: xb]
    return g


# ───────────── 하늘색 점 ─────────────
def is_cyan(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(rgb.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_RGB2HSV).reshape(rgb.shape[:-1] + (3,)).astype(int)
    h, s_, v = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    return (h >= 150) & (h <= 215) & (s_ > 0.30) & (v > 0.45)


def clean_cyan(f: np.ndarray, max_size: int) -> tuple[np.ndarray, int]:
    """장갑 위의 작은 하늘색 점을 둘레의 색으로 메운다. 지운 px 수도 돌려준다."""
    op = f[..., 3] > 0
    body = body_of(op)
    if body is None:
        return f, 0
    cy = is_cyan(f[..., :3]) & op
    n, lab, st, _ = cv2.connectedComponentsWithStats(cy.astype(np.uint8), connectivity=8)
    big = np.zeros_like(cy)
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] >= max(8, max_size + 1):
            big |= lab == k
    near_big = cv2.dilate(big.astype(np.uint8), np.ones((19, 19), np.uint8)) > 0     # 큰 하늘색에서 9px 안 = 그 빛의 일부 (주포의 빛 띠)
    _, neck, _ = head_span(body)
    g, removed = f.copy(), 0
    for k in range(1, n):
        m = lab == k
        if st[k, cv2.CC_STAT_AREA] > max_size or st[k, cv2.CC_STAT_TOP] <= neck or (m & near_big).any() or not body[m].all():
            continue
        ring = (cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0) & ~cy & op
        if ring.sum() < 3:                                           # 몸에 붙어 있지 않고 떠 있는 불꽃은 그대로 둔다
            continue
        cols, cnt = np.unique(f[ring][:, :3], axis=0, return_counts=True)
        g[m, :3] = cols[int(np.argmax(cnt))]                          # 둘레에서 가장 많은 색
        removed += int(m.sum())
    return g, removed


# ───────────── 파츠 리그 ─────────────
def split_parts(key: np.ndarray, pmap: np.ndarray, colors: dict, order: list) -> dict:
    """키 그림을 파츠 지도대로 나눈다. 아래 파츠는 위 파츠 밑으로 2px 늘려 둔다 (위 파츠가 움직여도 틈이 없게)."""
    op = key[..., 3] > 0
    masks = {}
    for name in order:
        c = tuple(int(colors[name][i: i + 2], 16) for i in (1, 3, 5))
        masks[name] = op & (pmap[..., 0] == c[0]) & (pmap[..., 1] == c[1]) & (pmap[..., 2] == c[2])
    left = op & ~np.any(list(masks.values()), axis=0)
    if left.any():
        raise SystemExit(f"파츠 지도에 색이 칠해지지 않은 픽셀이 {int(left.sum())}개 있다 (예: x={np.nonzero(left)[1][0]}, y={np.nonzero(left)[0][0]})")
    parts = {}
    for li, name in enumerate(order):
        img = np.zeros_like(key)
        img[masks[name]] = key[masks[name]]
        above = np.any([masks[o] for o in order[li + 1:]], axis=0) if li + 1 < len(order) else np.zeros_like(op)
        have = masks[name].copy()
        for _ in range(2):                                           # 위 파츠의 자리로 한 px 씩 두 번 늘린다 (세로 → 가로 → 대각선 순서)
            add = np.zeros_like(have)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                src = np.roll(np.roll(have, dy, axis=0), dx, axis=1)
                take = src & above & ~have & ~add
                ys, xs = np.nonzero(take)
                img[ys, xs] = img[ys - dy, xs - dx]
                add |= take
            have |= add
        parts[name] = img
    return parts


def rig_frame(parts: dict, order: list, offsets: dict) -> np.ndarray:
    """파츠를 저마다 (dx, dy) 만큼 옮겨 뒤에서 앞으로 겹친다."""
    out = None
    for name in order:
        img = parts[name]
        dx, dy = offsets.get(name, (0, 0))
        moved = np.zeros_like(img)
        h, w = img.shape[:2]
        moved[max(0, dy): h + min(0, dy), max(0, dx): w + min(0, dx)] = img[max(0, -dy): h - max(0, dy), max(0, -dx): w - max(0, dx)]
        if out is None:
            out = moved
        else:
            m = moved[..., 3] > 0
            out[m] = moved[m]
    return out


# ───────────── 검사 ─────────────
def frame_checks(frames: list[np.ndarray], st: dict, base: int) -> dict:
    """줄인 프레임(1x)에서 키 위치를 다시 재서 흔들림을 수치로 낸다."""
    K = [measure(f[..., 3] > 0, 1) for f in frames]
    ground = [i for i in st["_ground"] if i < len(K)]
    out = {"keys": [{"sole": k["bot"], "top": k["top"], "height": k["height"], "front_foot": k["front_foot"],
                     "rear_foot": k["rear_foot"], "head": round(k["head"], 1)} for k in K]}
    out["sole_drift"] = max([abs(K[i]["bot"] - base) for i in ground], default=0)
    an = [anchor_of(k, st["anchor"]) for k in K]
    out["anchor_x_range"] = 0 if an[0] is None else round(max(an) - min(an), 1)
    out["height_range"] = max(k["height"] for k in K) - min(k["height"] for k in K)
    out["head_top_range"] = max(k["top"] for k in K) - min(k["top"] for k in K)
    out["head_x_range"] = round(max(k["head"] for k in K) - min(k["head"] for k in K), 1)
    hy = st.get("_head_y") or []
    out["head_y_range"] = (max(hy) - min(hy)) if hy else 0
    # 이웃한 프레임 사이에 바뀌는 픽셀의 비율 (도는 상태는 끝 → 처음도 센다)
    pairs = list(zip(frames, frames[1:])) + ([(frames[-1], frames[0])] if st.get("loop") and len(frames) > 1 else [])
    ch = []
    for a, b in pairs:
        union = (a[..., 3] > 0) | (b[..., 3] > 0)
        ch.append(((a != b).any(-1) & union).sum() / max(1, union.sum()))
    out["changed_px"] = round(float(np.mean(ch)), 3) if ch else 0.0
    return out


def gif(frames: list[np.ndarray], ticks: int, path: Path, zoom: int = 4, base: int | None = None) -> None:
    ims = []
    for f in frames:
        bg = np.zeros((f.shape[0], f.shape[1], 3), dtype=np.uint8)
        bg[...] = (38, 36, 48)
        if base is not None:
            bg[base + 1] = (77, 73, 89)                              # 땅
        a = f[..., 3:4] / 255.0
        im = Image.fromarray((bg * (1 - a) + f[..., :3] * a).astype(np.uint8))
        ims.append(im.resize((im.width * zoom, im.height * zoom), Image.NEAREST))
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=max(20, round(ticks * 1000 / 60)), loop=0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="상태별 스프라이트 시트 만들기 (키 위치 맞춤)")
    ap.add_argument("layout")
    ap.add_argument("--measure", action="store_true", help="원본의 키 위치만 재서 보여 준다")
    args = ap.parse_args()

    lay_path = Path(args.layout)
    L = json.loads(lay_path.read_text(encoding="utf-8"))
    s, base = L["scale"], L["base"]
    out_dir = Path(L.get("out") or lay_path.parent)
    sheets = L.get("sheets") or [{k: L[k] for k in ("src", "grid", "states", "before", "zoom", "match") if k in L}]

    # ── 1. 원본에서 키 위치 재기 ──
    states = []
    for si, sh in enumerate(sheets):
        rgb = np.asarray(Image.open(sh["src"]).convert("RGB"))
        keyed = key_mask(rgb)
        rgba = np.dstack([despill(rgb), np.where(keyed, 0, 255).astype(np.uint8)])
        cols, rows = sh["grid"]
        gw, gh = rgb.shape[1] / cols, rgb.shape[0] / rows            # 원본의 칸 크기
        zoom = sh.get("zoom", 1)
        cw1, ch1 = sh.get("cell", L["cell"])
        print(f"원본 {sh['src']}  칸 {gw:.0f}x{gh:.0f}px" + (f"  x{zoom} 로 키운다" if zoom != 1 else ""))
        for st in sh["states"]:
            cells = st.get("cells") or [[st["row"], c] for c in st["cols"]]
            st["_cells"] = []
            for r, c in cells:
                cell = rgba[round(r * gh): round((r + 1) * gh), round(c * gw): round((c + 1) * gw)]
                if zoom != 1:                                        # 원본 단계에서 키운다 (가장 가까운 픽셀로, 색이 섞이지 않게)
                    cell = cv2.resize(cell, (round(cell.shape[1] * zoom), round(cell.shape[0] * zoom)), interpolation=cv2.INTER_NEAREST)
                st["_cells"].append(cell)
            st["_keys"] = [measure(c[..., 3] > 0, s) for c in st["_cells"]]
            n = len(cells)
            st["_ground"] = list(range(n)) if st.get("ground", "all") == "all" else list(st["ground"])
            st.setdefault("anchor", "none")
            st.setdefault("kind", "single" if n == 1 else "planted")
            st["_cw"], st["_ch"], st["_sheet"] = cw1, ch1, si
            st["_allow"] = {**ALLOW[st["kind"]], **st.get("allow", {})}
            states.append(st)
    by_name = {st["name"]: st for st in states}

    print("── 원본의 키 위치 (원본 px) ──")
    for st in states:
        K = st["_keys"]
        rng = lambda key: f"{min(k[key] for k in K):.0f}~{max(k[key] for k in K):.0f}"   # noqa: E731
        print(f"{st['name']:16s} {len(K)}장  발바닥 {rng('bot')}  정수리 {rng('top')}  키 {rng('height')}  "
              f"앞발 {rng('front_foot')}  뒷발 {rng('rear_foot')}  머리 {rng('head')}  앞 부츠 폭 {rng('boot')}")
        if args.measure:
            for i, k in enumerate(K):
                print(f"      {i}: 발바닥 {k['bot']} 정수리 {k['top']} 키 {k['height']} 발 {k['feet']} 머리x {k['head']:.0f} 몸x {k['body']:.0f}")
    if args.measure:
        return

    # ── 2. 기준 키 위치가 같은 자리에 오도록 옮길 양 정하기 ──
    # 발바닥의 맨 아랫줄이 올 자리. 블록은 절반 넘게 찬 줄만 남으므로, 여기서 ±2px(px 단위로 옮기고 남는 어긋남) 안이면 발바닥이 base 줄이 된다.
    target_bot = base * s + s - 1
    shared: dict[str, int] = {}                                      # 칸의 가운데에서 잰 자리 (칸 너비가 달라도 같은 자리가 되게)
    for st in states:
        K, cells, cw, ch = st["_keys"], st["_cells"], st["_cw"] * s, st["_ch"] * s
        # 세로: 땅에 닿은 프레임은 저마다 발바닥을 base 줄에, 공중 프레임은 이 상태의 땅 높이를 기준으로 그려진 높이를 지킨다
        ref = st if (st["_ground"] or "center_y" in st) else by_name[st["ground_from"]]
        ground_y = round(float(np.median([ref["_keys"][i]["bot"] for i in ref["_ground"]]))) if ref["_ground"] else 0
        dys = [s * round((target_bot - (K[i]["bot"] if i in st["_ground"] else ground_y)) / s) for i in range(len(K))]
        if "center_y" in st:                                           # 공중에서 도는 몸(띄움): 몸의 무게중심을 칸의 정해진 줄에 놓는다
            dys = [s * round((st["center_y"] * s - k["body_y"]) / s) for k in K]
        # 가로
        an = [anchor_of(k, st["anchor"]) for k in K]
        if an[0] is None:
            dxs = [s * round((cw - c.shape[1]) / 2 / s) for c in cells]
        else:
            if "x" in st:
                tx = st["x"] * s
            elif st["anchor"] in shared:
                tx = shared[st["anchor"]] + cw // 2
            else:
                tx = round(float(np.median(an)) + (cw - cells[0].shape[1]) / 2)
                if st["anchor"] in L.get("shared_anchors", []):
                    shared[st["anchor"]] = tx - cw // 2
            # 게임 해상도의 px 단위(원본 s px 의 배수)로만 옮긴다. 반 px 안쪽의 어긋남은 그대로 둔다.
            dxs = [s * round((tx - a) / s) for a in an]
        st["_shift"] = list(zip(dxs, dys))

    # ── 3. 옮겨서 원본 시트마다 한 장으로 모으고, 처음 방식 그대로 줄인다 ──
    # 팔레트는 원본 시트마다 따로 뽑는다. 그래야 기본 시트의 상태가 처음 시트와 색까지 같다. (새로 뽑은 시트의 색은 3-1 에서 맞춘다)
    for si in range(len(sheets)):
        mine = [st for st in states if st["_sheet"] == si]
        wide = max(len(st["_cells"]) * st["_cw"] for st in mine) * s
        tops = np.cumsum([0] + [st["_ch"] * s for st in mine])
        sheet = np.zeros((int(tops[-1]), wide, 4), dtype=np.uint8)
        for r, st in enumerate(mine):
            st["_lost"] = []
            cw, ch = st["_cw"] * s, st["_ch"] * s
            for i, (cell, (dx, dy)) in enumerate(zip(st["_cells"], st["_shift"])):
                img, lost = shifted(cell, dx, dy, cw, ch)
                sheet[tops[r]: tops[r] + ch, i * cw: (i + 1) * cw] = img
                st["_lost"].append(lost)
        small = downscale(sheet, s, L.get("colors", 64))
        for r, st in enumerate(mine):
            y, cw1, ch1 = int(tops[r]) // s, st["_cw"], st["_ch"]
            st["_frames"] = [small[y: y + ch1, i * cw1: (i + 1) * cw1].copy() for i in range(len(st["_cells"]))]
            # 발바닥의 맨 아랫줄이 얇게 그려진 프레임은 줄인 뒤 발바닥이 한 줄 어긋날 수 있다. 땅에 닿은 프레임은 px 단위로 한 번 더 맞춘다.
            for i in st["_ground"]:
                rows_ = np.flatnonzero((body_of(st["_frames"][i][..., 3] > 0)).any(axis=1))
                d = base - int(rows_[-1])
                if d:
                    f = np.zeros_like(st["_frames"][i])
                    f[max(0, d): ch1 + min(0, d)] = st["_frames"][i][max(0, -d): ch1 - max(0, d)]
                    st["_frames"][i] = f
                    st["_shift"][i] = (st["_shift"][i][0], st["_shift"][i][1] + d * s)

    # ── 3-1. 새로 뽑은 시트의 장갑 색을 첫 시트에 맞춘다 ──
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "preview").mkdir(exist_ok=True)
    if any(sh.get("match") for sh in sheets):
        from recolor_sheet import make_match
        ref_png = out_dir / "_match_ref.png"
        Image.fromarray(np.concatenate([f for st in states if st["_sheet"] == 0 for f in st["_frames"]
                                        if f.shape[:2] == (L["cell"][1], L["cell"][0])], axis=1)).save(ref_png)
        for si, sh in enumerate(sheets):
            if not sh.get("match"):
                continue
            fn = make_match(str(ref_png), bool(sh.get("gray")))
            for st in states:
                if st["_sheet"] != si:
                    continue
                for f in st["_frames"]:
                    for y, x in zip(*np.nonzero(f[..., 3])):
                        new = fn(int(f[y, x, 0]), int(f[y, x, 1]), int(f[y, x, 2]))
                        if new is not None:
                            f[y, x, :3] = [round(c * 255) for c in new]
        ref_png.unlink()

    # ── 4. 머리: 키 그림 한 장을 모든 프레임이 함께 쓴다. 놓는 자리는 프레임마다의 목 줄이다 ──
    patch, H = None, L.get("head")
    if H:
        part = out_dir / H.get("file", "parts/head.png")
        if part.exists():
            patch = np.asarray(Image.open(part).convert("RGBA")).copy()
            print(f"머리 키 그림: {part} (있는 파일을 쓴다, {patch.shape[1]}x{patch.shape[0]})")
        else:
            patch = cut_head(by_name[H["from"][0]]["_frames"][H["from"][1]], H["rows"])
            part.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(patch).save(part)
            print(f"머리 키 그림: {part} 을 {H['from'][0]} {H['from'][1]}번 프레임에서 잘라 만들었다 ({patch.shape[1]}x{patch.shape[0]})")
    cleaned = 0
    for st in states:
        st["_head"], st["_head_y"] = [], []
        if L.get("clean_cyan") and not st.get("keep_specks"):
            for i, f in enumerate(st["_frames"]):
                st["_frames"][i], k = clean_cyan(f, st.get("clean_cyan", L["clean_cyan"]))
                cleaned += k
        st["_pre"] = [f.copy() for f in st["_frames"]]              # 머리를 놓기 전 (눈 감은 머리를 따로 놓을 때 쓴다)
        if patch is None or not st.get("head_lock"):
            continue
        mm = st.get("min_match", H.get("min_match", 0.7))
        found = [find_head(f, patch) for f in st["_frames"]]
        st["_found"] = found
        ok = [a["match"] >= mm for a in found]
        # 머리가 기준인 상태(달리기 등)는 머리를 모든 프레임에서 같은 x 에 놓는다 → 머리는 위아래로만 움직인다
        same_x = int(np.median([a["x"] for a, o in zip(found, ok) if o])) if st["anchor"] == "head" and any(ok) else None
        for i, (f, a, o) in enumerate(zip(st["_frames"], found, ok)):
            if o:
                st["_frames"][i] = put_head(f, patch, a, same_x, at_neck=st.get("head_anchor") == "neck")
                st["_head_y"].append(a["top"])
            st["_head"].append((round(a["match"], 2), o, a["neck"] - a["top"] + 1))

    if L.get("clean_cyan"):
        print(f"장갑 위의 작은 하늘색 점 {cleaned}px 을 지웠다 (크기 {L['clean_cyan']}px 이하)")

    # ── 4-1. 파츠 리그: 키 그림을 파츠로 나눠 파츠별로 움직인다 ──
    for st in states:
        rg = st.get("rig")
        if not rg:
            continue
        key = st["_frames"][0]
        pmap = np.asarray(Image.open(out_dir / rg["parts"]).convert("RGB"))
        parts = split_parts(key, pmap, rg["colors"], rg["order"])
        rest = rig_frame(parts, rg["order"], {})
        if (rest != key).any():
            raise SystemExit(f"{st['name']}: 파츠를 제자리에 겹친 그림이 키 그림과 다르다 ({int((rest != key).any(-1).sum())}px)")
        blink_head = None
        if rg.get("blink"):
            bp = np.asarray(Image.open(out_dir / rg["blink"]["file"]).convert("RGBA")).copy()
            blink_head = split_parts(put_head(st["_pre"][0], bp, st["_found"][0]), pmap, rg["colors"], rg["order"])["head"]
        n = max(len(v) for v in rg["tracks"].values())
        frames = []
        for i in range(n):
            use = dict(parts)
            if blink_head is not None and i in rg["blink"]["frames"]:
                use["head"] = blink_head
            frames.append(rig_frame(use, rg["order"], {k: tuple(v[i]) for k, v in rg["tracks"].items()}))
        st["_frames"] = frames
        st["_ground"] = list(range(n))
        st["_shift"] = [st["_shift"][0]] * n
        st["_lost"] = [st["_lost"][0]] + [0] * (n - 1)
        st["_head"] = [st["_head"][0]] * n if st["_head"] else []
        st["_head_y"] = [st["_head_y"][0] + rg["tracks"].get("head", [[0, 0]] * n)[i][1] for i in range(n)] if st["_head_y"] else []
        st["_rig"] = True

    # ── 5. 상태별 시트 저장, 다시 재서 검사 ──
    table = {"cell": L["cell"], "base": base, "scale": s, "states": {}}
    gate = {"states": {}, "pass": True}
    print("\n── 줄인 뒤 다시 잰 값 (1x px) ──   [화살표가 있으면 앞 = 예전 시트, 뒤 = 지금]")
    for st in states:
        frames, cw1, ch1 = st["_frames"], st["_cw"], st["_ch"]
        n = len(frames)
        Image.fromarray(np.concatenate(frames, axis=1)).save(out_dir / f"{st['name']}.png")
        chk = frame_checks(frames, st, base)
        fails = [key for name, key in CHECKS if st["_allow"].get(name) is not None and chk[key] > st["_allow"][name]]
        used = st.get("use", True)
        g = {"kind": st["kind"], "anchor": st["anchor"], "allow": st["_allow"], "pass": not fails, "fails": fails,
             **{k: chk[k] for k in ("sole_drift", "anchor_x_range", "height_range", "head_top_range", "head_x_range", "head_y_range", "changed_px")},
             "clipped_px": sum(st["_lost"])}
        gate["states"][st["name"]] = g
        if used:
            gate["pass"] &= not fails
        table["states"][st["name"]] = {"file": f"{st['name']}.png", "frames": n, "ticks": st.get("ticks", 8), "loop": bool(st.get("loop")),
                                       "cell": [cw1, ch1], "kind": st["kind"], "anchor": st["anchor"], "use": used,
                                       "head_locked": sum(o for _, o, _ in st["_head"]), "rig": bool(st.get("_rig")),
                                       "shift_raw": [list(map(int, v)) for v in st["_shift"]], "keys": chk["keys"]}
        line = f"{st['name'] + ('' if used else ' (비교용)'):18s} {'통과' if not fails else '실패 ' + ','.join(fails):16s}"
        bf = sheets[st["_sheet"]].get("before")
        if bf:
            b = np.asarray(Image.open(bf["sheet"]).convert("RGBA"))
            bc = bf["cell"]
            old = [b[st["row"] * bc: (st["row"] + 1) * bc, c * bc: (c + 1) * bc] for c in st.get("before_cols", st["cols"])]
            ob = [measure(f[..., 3] > 0, 1) for f in old]
            gr = [i for i in st["_ground"] if i < len(ob)]
            obase = int(np.median([ob[i]["bot"] for i in gr])) if gr else base
            oc = frame_checks(old, {**st, "_head_y": []}, obase)
            g["before"] = {k: oc[k] for k in ("sole_drift", "anchor_x_range", "height_range", "head_top_range", "head_x_range", "changed_px")}
            line += (f" 발바닥 {oc['sole_drift']}→{chk['sole_drift']}  기준x {oc['anchor_x_range']}→{chk['anchor_x_range']}  "
                     f"정수리 {oc['head_top_range']}→{chk['head_top_range']}  키 {oc['height_range']}→{chk['height_range']}  "
                     f"바뀌는 픽셀 {oc['changed_px'] * 100:.0f}%→{chk['changed_px'] * 100:.0f}%")
            if n > 1:
                both = []                                            # 왼쪽 = 예전, 오른쪽 = 지금 (칸 크기와 땅 높이를 맞춰서)
                for o, f in zip(old, frames):
                    pad = np.zeros_like(f)
                    dy, oh, ow = base - obase, min(o.shape[0], ch1), min(o.shape[1], cw1)
                    src = o[max(0, -dy): oh - max(0, dy), :ow]
                    pad[max(0, dy): max(0, dy) + src.shape[0], (cw1 - ow) // 2: (cw1 - ow) // 2 + ow] = src
                    both.append(np.concatenate([pad, f], axis=1))
                gif(both, st.get("ticks", 8), out_dir / "preview" / f"{st['name']}_before_after.gif", base=base)
        else:
            line += (f" 발바닥 {chk['sole_drift']}  기준x {chk['anchor_x_range']}  정수리 {chk['head_top_range']}  "
                     f"키 {chk['height_range']}  바뀌는 픽셀 {chk['changed_px'] * 100:.0f}%")
        if st["_head"]:
            line += (f"  머리 {sum(o for _, o, _ in st['_head'])}/{len(st['_head'])} (겹침 {' '.join(str(v) for v, _, _ in st['_head'])} · "
                     f"AI 가 그린 높이 {' '.join(str(h) for _, _, h in st['_head'])} · 오르내림 {chk['head_y_range']})")
        if st["kind"] == "cycle" and st.get("loop"):
            steps = [k["front_foot"] - k["rear_foot"] for k in chk["keys"] if k["front_foot"] != k["rear_foot"]]
            if steps and n >= 4:
                g["cycle_px"] = 2 * max(steps)
                line += f"  한 바퀴 {g['cycle_px']:.0f}px → 발이 미끄러지지 않는 속도 {g['cycle_px'] / (n * st.get('ticks', 8)):.2f}px/틱"
        if st.get("_rig"):
            line += "  [키 그림 1장을 파츠로 나눠 만듦]"
        if sum(st["_lost"]):
            line += f"  (칸 밖으로 잘린 원본 px {sum(st['_lost'])})"
        print(line)
        if n > 1:
            gif(frames, st.get("ticks", 8), out_dir / "preview" / f"{st['name']}.gif", base=base)

    if L.get("pack"):
        used = [st for st in states if st.get("use", True)]
        cw1, ch1 = L["cell"]
        pk = np.zeros((ch1 * len(used), cw1 * max(len(st["_frames"]) for st in used), 4), dtype=np.uint8)
        for r, st in enumerate(used):
            for i, f in enumerate(st["_frames"]):
                pk[r * ch1: (r + 1) * ch1, i * cw1: (i + 1) * cw1] = f
        Image.fromarray(pk).save(out_dir / L["pack"])
    (out_dir / "states.json").write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=1), encoding="utf-8")
    if L.get("game"):
        gdir = Path(L["game"]["dir"])
        gdir.mkdir(parents=True, exist_ok=True)
        used = {k: v for k, v in table["states"].items() if v["use"]}
        for k in used:
            Image.open(out_dir / f"{k}.png").save(gdir / f"{k}.png")
        slim = {"cell": table["cell"], "base": base,
                "states": {k: {"frames": v["frames"], "ticks": v["ticks"], "loop": v["loop"], "cell": v["cell"]} for k, v in used.items()}}
        js = ("/* tools/state_sheets.py 가 만든 파일이다. 고치려면 " + lay_path.as_posix() + " 을 고치고 도구를 다시 돌린다.\n"
              " * frames = 프레임 수, ticks = 한 프레임을 보여 주는 틱(1/60초), cell = 칸 크기, base = 칸 안에서 발바닥이 닿는 줄. */\n"
              "(function (root) {\n  var S = root.SALVAGE = root.SALVAGE || {};\n  S.stateSheets = S.stateSheets || {};\n"
              "  S.stateSheets[" + json.dumps(L["game"]["id"]) + "] = " + json.dumps(slim, ensure_ascii=False) + ";\n"
              "})(typeof window !== 'undefined' ? window : this);\n")
        (gdir / "states.js").write_text(js, encoding="utf-8")
        print(f"[saved] {gdir} — 게임용 시트 {len(used)}장, states.js")
    print(f"\n[saved] {out_dir} — 상태 {len(states)}개, states.json, gate.json, preview/  →  검사 {'통과' if gate['pass'] else '실패'}")


if __name__ == "__main__":
    main()
