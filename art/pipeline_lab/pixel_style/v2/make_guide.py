"""v2 2단계의 밑그림을 만든다 (기획서 9.11.4).

    python art/pipeline_lab/pixel_style/v2/make_guide.py

1단계(밑그림 없이 자유롭게 그린 그림, s1/*_raw.png)는 칸이 고르지 않다 (칸 너비 12~26px).
그 그림을 목표 칸 수로 다시 깐다: 목표 칸마다 원본의 해당 사각형에서 가장 많은 색(색을 섞지 않는다).
머리와 몸은 따로 줄인다: 1단계 그림은 약 3등신으로 나와서, 머리(정수리 ~ 목)를 조금 작게 잡아
약 3.2등신으로 맞춘다 (CLAUDE.md: "4등신이 조금 못 되는 키"). 가로는 각 부분이 제 세로와 같은 비율로 줄어
모양이 눌리지 않는다. 기준은 목 줄의 가운데 열이다.
출력: art/prompts/pipeline/nx07_side_v2_guide<T>_<안>.png (1024, 마젠타 배경, 칸 C px)
      v2/guides/<안><T>_cells.png (1배) · _x8.png · guides.json (칸 · 원점 · 머리)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from pixel_master import head_height, load_cutout  # noqa: E402

HEADS = 3.2  # 목표 등신 (head_height 의 기준: 정수리 ~ 목). 3.45 로 하면 헬멧이 눌려 작아 보였다
# (안, 목표 키 칸 수, 칸 px)
JOBS = [("A", 36, 24), ("B", 36, 24), ("C", 36, 24), ("A", 48, 18), ("B", 48, 18), ("C", 48, 18)]
MAGENTA = (255, 0, 255)


def cell_color(a: np.ndarray, x0: float, x1: float, y0: float, y1: float):
    """원본 사각형의 가운데 60% 에서 가장 많은 색. 반 넘게 배경이면 None."""
    h, w = a.shape[:2]
    mx, my = (x1 - x0) * 0.2, (y1 - y0) * 0.2
    xa, xb = int(round(x0 + mx)), int(round(x1 - mx))
    ya, yb = int(round(y0 + my)), int(round(y1 - my))
    xa, ya = max(xa, 0), max(ya, 0)
    xb, yb = min(max(xb, xa + 1), w), min(max(yb, ya + 1), h)
    if xa >= w or ya >= h or xb <= 0 or yb <= 0:
        return None
    p = a[ya:yb, xa:xb].reshape(-1, 4)
    fg = p[p[:, 3] > 0][:, :3].astype(int)
    if len(fg) < 0.5 * len(p):
        return None
    q = fg // 10
    keys, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    sel = fg[inv.ravel() == cnt.argmax()]
    return tuple(int(v) for v in np.round(sel.mean(0)))


def build(plan: str, T: int) -> tuple[np.ndarray, dict]:
    a = load_cutout(LAB / "s1" / f"nx07_v2s1_{plan}_raw.png")
    op = a[..., 3] > 0
    ys, xs = np.where(op)
    top, bot = ys.min(), ys.max() + 1
    H, head = head_height(a[top:bot, xs.min():xs.max() + 1])
    neck = top + head
    # 목 줄의 가운데 열
    nx = np.where(op[neck])[0]
    anchor = float(nx.mean())
    hh = int(round(T / HEADS))
    hb = T - hh
    sh = head / hh   # 머리 부분의 원본 칸 크기 (px)
    sb = (bot - neck) / hb  # 몸 부분
    # 가로 범위: 원본 전체 너비를 덮도록
    left = max(anchor - xs.min(), 1)
    right = max(xs.max() + 1 - anchor, 1)
    ai = int(np.ceil(left / min(sh, sb))) + 1
    W = ai + int(np.ceil(right / min(sh, sb))) + 1
    cells = np.zeros((T, W, 4), np.uint8)
    for j in range(T):
        if j < hh:
            s, y0 = sh, top + j * sh
        else:
            s, y0 = sb, neck + (j - hh) * sb
        for i in range(W):
            x0 = anchor + (i - ai) * s
            c = cell_color(a, x0, x0 + s, y0, y0 + s)
            if c is not None:
                cells[j, i, :3] = c
                cells[j, i, 3] = 255
    # 빈 열 자르기
    cols = np.where(cells[..., 3].any(0))[0]
    cells = cells[:, cols.min():cols.max() + 1]
    return cells, {"src_head_px": int(head), "src_height_px": int(H), "head_cells": hh, "body_cells": hb,
                   "src_cell_head": round(sh, 2), "src_cell_body": round(sb, 2)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out = LAB / "guides"
    out.mkdir(exist_ok=True)
    info = {}
    for plan, T, C in JOBS:
        cells, meta = build(plan, T)
        h, w = cells.shape[:2]
        ox = (1024 - w * C) // 2
        oy = (1024 - h * C) // 2
        g = Image.new("RGB", (1024, 1024), MAGENTA)
        big = Image.fromarray(cells, "RGBA").resize((w * C, h * C), Image.NEAREST)
        g.paste(big, (ox, oy), big)
        name = f"nx07_side_v2_guide{T}_{plan}.png"
        g.save(ROOT / "art/prompts/pipeline" / name)
        Image.fromarray(cells, "RGBA").save(out / f"{plan}{T}_cells.png")
        Image.fromarray(cells, "RGBA").resize((w * 8, h * 8), Image.NEAREST).save(out / f"{plan}{T}_cells_x8.png")
        hh, hd = head_height(cells)
        info[f"{plan}{T}"] = {"guide": f"art/prompts/pipeline/{name}", "cell": C, "origin": [ox, oy],
                              "cells": [w, h], "heads": round(hh / hd, 2), **meta}
        print(plan, T, info[f"{plan}{T}"])
    (out / "guides.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
