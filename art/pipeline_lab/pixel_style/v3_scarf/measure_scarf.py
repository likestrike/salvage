"""스카프 변형을 9.11.3 · 9.11.4 와 같은 측정으로 잰다 (기획서 9.11.5).

    python -X utf8 art/pipeline_lab/pixel_style/v3_scarf/measure_scarf.py

measure.py 의 metrics, measure_v2.py 의 face 를 그대로 쓴다. 참고 그림은 읽지 않는다.
출력: measure_scarf.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
AN = ROOT / "reference/pixel_style/analysis"
sys.path.insert(0, str(AN))
sys.path.insert(0, str(ROOT / "tools"))
from common import components, crop, load_rgba  # noqa: E402
from measure import metrics  # noqa: E402
from measure_v2 import face  # noqa: E402
from pixel_master import head_height  # noqa: E402

FIGS = {"C36": ROOT / "art/pipeline_lab/pixel_style/v2/C36/nx07_v2C36_master.png"}
for n in ("S1", "S2", "S3", "S4"):
    FIGS[n] = HERE / n / f"nx07_v3{n}.png"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    res = {}
    for k, p in FIGS.items():
        a = crop(load_rgba(p))
        m = metrics(a)
        hh, hd = head_height(a)
        sizes = [len(q) for _, q in components(a)]
        n = sum(sizes)
        vb = m["value_bands"]
        f = face(a)
        r = {
            "size": m["size"], "cells": m["cells"], "colors": m["colors"], "height": hh, "head": hd,
            "largest_value_mass_pct": max(v["largest_pct"] for v in vb.values()),
            "value_top3_pct": m["value_top3_pct"],
            "region_big_mid_small_pct": [round(100 * sum(x for x in sizes if x >= 20) / n, 1),
                                         round(100 * sum(x for x in sizes if 4 <= x < 20) / n, 1),
                                         round(100 * sum(x for x in sizes if x <= 3) / n, 1)],
            "accent_pct": m["accent_pct"], "L_mean": m["L_mean"], "bright_pct": m["bright_pct"],
            "face": f,
            "solidity": m["solidity"], "perimeter_per_sqrt_area": m["perimeter_per_sqrt_area"],
            "edge_L_mean": m["edge_L_mean"],
        }
        res[k] = r
        print(k, f"칸 {r['cells']} 폭 {r['size'][0]} 키 {hh} | 가장 큰 밝기 덩어리 {r['largest_value_mass_pct']}% 위3 {r['value_top3_pct']}% "
                 f"| 큰/중간/작은 {r['region_big_mid_small_pct']} | 채도 높은 칸 {r['accent_pct']}% | L {r['L_mean']} "
                 f"| 얼굴 {f.get('skin_cells')}칸 대비 {f.get('contrast')} (둘레 L {f.get('around_L')}) "
                 f"| 단단함 {r['solidity']} 둘레/√넓이 {r['perimeter_per_sqrt_area']} | 색 {r['colors']}")
    (HERE / "measure_scarf.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
