"""v1 의 뽑힌 그림이 밑그림의 격자(칸 16px, 원점 x=320 · y=64)에 맞는지 잰다 (기획서 9.11.2).

    python art/pipeline_lab/pixel_style/v1/grid_check_v1.py

재는 방법은 ../grid_check.py 와 같다 (칸 가운데 10×10 이 대표색과 같은 비율이 90% 넘는 칸 = 고른 칸).
반 칸(8px) 민 격자도 재서 견준다. 알려진 격자로 바로 뽑은 마스터(_known16.png)도 저장한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB.parent))
from grid_check import measure  # noqa: E402

OX, OY = 320, 64
RUNS = {"a_selout": "nx07_v1a", "b_flat": "nx07_v1b", "c_flat2": "nx07_v1c"}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    res = {}
    for d, n in RUNS.items():
        raw = LAB / d / f"{n}_raw.png"
        if not raw.exists():
            continue
        rgb = np.array(Image.open(raw).convert("RGB"))
        r0, cells, m = measure(rgb, OX, OY)
        r1, _, _ = measure(rgb, OX + 8, OY + 8)
        rx, _, _ = measure(rgb, OX + 8, OY)
        ry, _, _ = measure(rgb, OX, OY + 8)
        ys, xs = np.where(m[..., 3] > 0)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        Image.fromarray(m, "RGBA").save(LAB / d / f"{n}_known16.png")
        res[d] = {"good": round(r0, 3), "half_xy": round(r1, 3), "half_x": round(rx, 3), "half_y": round(ry, 3),
                  "cells": cells, "known16": list(m.shape[1::-1])}
        print(f"{d}: 고른 칸 {r0*100:.0f}% (반 칸 민 격자 xy {r1*100:.0f}% · x {rx*100:.0f}% · y {ry*100:.0f}%), 칸 {cells}개, known16 {m.shape[1]}×{m.shape[0]}")
    (LAB / "grid_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
