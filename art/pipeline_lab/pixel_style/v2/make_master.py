"""v2 마스터 후보를 만든다 (기획서 9.11.4).

    python art/pipeline_lab/pixel_style/v2/make_master.py

1) 격자 검사: 2단계 그림(s2/*_raw.png)이 밑그림의 격자(guides/guides.json 의 칸 · 원점)에 맞게 그려졌는지 잰다.
   칸 가운데(가장자리 칸 크기의 20% 를 뺀 영역)의 픽셀이 대표색과 같은(ΔRGB<40) 비율이 90% 넘는 칸 = 고른 칸.
   반 칸 민 격자도 재서 견준다 (grid_check.py 와 같은 방법, 칸 크기만 다르다).
2) 칸 읽기: 그 격자로 칸마다 대표색(가운데에서 가장 많은 색). 칸의 반 넘게 마젠타면 투명.
3) 색 묶기: v1 의 make_master.py 와 같다 (Lab ΔE 가 가장 가까운 두 색부터, 칸이 적은 쪽을 많은 쪽 색으로.
   목표 16색, ΔE 14 넘으면 멈춘다). 색을 새로 만들지 않는다.
4) 손보기: FIXES 의 칸만 바꾼다 (그 그림에 이미 있는 칸의 색을 가져온다). 손보기 전(_unfixed.png)과 _fixes.json 을 남긴다.
5) 검사와 저장: 반투명 0 · 팔레트 이탈 0 · 키 · 머리 · 등신 · 색 수 · 외톨이 픽셀.
출력: <안>/nx07_v2<안>_master.png (1배) · _x8.png · _palette.hex · .gpl · _info.json, grid_check.json
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
sys.path.insert(0, str(LAB.parent / "v1"))
from process_sheet import key_mask  # noqa: E402
from make_master import merge_colors, save  # noqa: E402  (v1 의 색 묶기 · 저장을 그대로 쓴다)

JOBS = ["A36", "C36", "C48", "B48"]

# 손보기 (x, y, 색을 가져올 칸 sx, sy, 이유). 칸 좌표는 마스터(1배, 잘라 낸 뒤)의 것.
FIXES: dict[str, list[tuple[int, int, int, int, str]]] = {
    "C36": [(14, 3, 12, 3, "헬멧 앞 끝(엠블럼 위)의 1칸이 배경 마젠타(#f904f7)로 읽혔다. 뽑힌 그림에서 그 칸은 헬멧 가장자리와 배경이 섞인 자리다. "
                           "옆 칸의 헬멧 올리브로 메운다 (팔레트에서 마젠타가 빠진다)")],
    "A36": [(14, 4, 14, 3, "이마 엠블럼이 가로 2칸 막대로만 나왔다 (역삼각이 읽히지 않는다). 앞쪽 칸 아래 1칸을 같은 시안으로 칠해 "
                           "위 2칸 · 아래 1칸의 작은 역삼각으로 만든다 (C36 · C48 과 같은 꼴)")],
    "B48": [(17, 10, 17, 11, "눈 바로 앞의 1칸이 이 칸에만 있는 붉은 살색(#dfa987)이라 눈이 둘이거나 볼에 점이 찍힌 것처럼 보인다. "
                             "바로 아래 얼굴색으로 메운다")],
}


def measure(rgb: np.ndarray, cell: int, ox: int, oy: int) -> tuple[float, int, np.ndarray]:
    bg = key_mask(rgb)
    h, w = rgb.shape[:2]
    m = max(2, int(round(cell * 0.2)))
    nx, ny = (w - ox) // cell, (h - oy) // cell
    good = tot = 0
    out = np.zeros((ny, nx, 4), np.uint8)
    for j in range(ny):
        for i in range(nx):
            y0, x0 = oy + j * cell, ox + i * cell
            if bg[y0:y0 + cell, x0:x0 + cell].mean() > 0.5:
                continue
            inner = rgb[y0 + m:y0 + cell - m, x0 + m:x0 + cell - m].reshape(-1, 3).astype(int)
            q = inner // 12
            keys, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
            rep = inner[inv.ravel() == cnt.argmax()].mean(0)
            same = (np.abs(inner - rep).sum(1) < 40).mean()
            tot += 1
            good += same > 0.9
            out[j, i, :3] = np.round(rep).astype(np.uint8)
            out[j, i, 3] = 255
    return good / max(1, tot), tot, out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    g = json.loads((LAB / "guides/guides.json").read_text(encoding="utf-8"))
    res = {}
    for job in JOBS:
        raw = LAB / "s2" / f"nx07_v2_{job}_raw.png"
        if not raw.exists():
            continue
        gi = g[job]
        c, (ox, oy) = gi["cell"], gi["origin"]
        rgb = np.array(Image.open(raw).convert("RGB"))
        r0, n, m = measure(rgb, c, ox, oy)
        r1, _, _ = measure(rgb, c, ox + c // 2, oy + c // 2)
        ys, xs = np.where(m[..., 3] > 0)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        d = LAB / job
        d.mkdir(exist_ok=True)
        stem = f"nx07_v2{job}"
        Image.fromarray(m, "RGBA").save(d / f"{stem}_known.png")
        res[job] = {"cell": c, "origin": [ox, oy], "good": round(r0, 3), "half": round(r1, 3), "cells": n, "size": list(m.shape[1::-1])}
        print(f"{job}: 고른 칸 {r0*100:.0f}% (반 칸 민 격자 {r1*100:.0f}%), 칸 {n}개, {m.shape[1]}×{m.shape[0]}")

        mm, merged = merge_colors(m)
        mm[..., 3] = np.where(mm[..., 3] > 0, 255, 0)
        base = {"src": f"art/pipeline_lab/pixel_style/v2/s2/nx07_v2_{job}_raw.png", "grid": {"cell": c, "origin": [ox, oy]},
                "guide": gi["guide"], "method": "알려진 격자의 칸 대표색 → Lab ΔE 가 가까운 색끼리 묶기 (목표 16색, ΔE 14 넘으면 멈춤)",
                "merged": merged, "doc": "docs/GAME_DESIGN.md 9.11.4"}
        fx = FIXES.get(job, [])
        if fx:
            save(mm, d, f"{stem}_unfixed", base | {"note": "손보기 전"})
            log = []
            for x, y, sx, sy, why in fx:
                before = "%02x%02x%02x" % tuple(mm[y, x, :3]) if mm[y, x, 3] else "투명"
                mm[y, x] = mm[sy, sx]
                after = "%02x%02x%02x" % tuple(mm[y, x, :3]) if mm[y, x, 3] else "투명"
                log.append({"cell": [x, y], "before": before, "after": after, "color_from": [sx, sy], "why": why})
            (d / f"{stem}_fixes.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
            base = base | {"fixes": f"{stem}_fixes.json", "unfixed": f"{stem}_unfixed.png"}
        save(mm, d, f"{stem}_master", base)
    (LAB / "grid_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
