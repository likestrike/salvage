"""v1 마스터 후보를 만든다 (기획서 9.11.2).

    python art/pipeline_lab/pixel_style/v1/make_master.py

1) 알려진 격자로 칸을 읽는다: grid_check_v1.py 가 저장한 _known16.png (칸 16px, 원점 320·64, 칸 가운데의 대표색).
   tools/pixel_master.py 의 16색 잠금은 얼굴의 살색을 흰색에 합쳐 버려서(눈으로 확인) 마스터로 쓰지 않는다.
   pixel_master.py 의 출력은 격자 검사(칸 후보가 모두 같은 격자로 모이는가)의 근거로만 남긴다.
2) 색 묶기: 지각 거리(Lab ΔE)가 가장 가까운 두 색부터 묶는다 (칸이 적은 쪽을 많은 쪽 색으로).
   TARGET 색이 되거나 가장 가까운 두 색도 STOP 보다 멀면 멈춘다. 묶은 기록은 info 의 merged 에 남는다.
   색을 새로 만들지 않는다. 뽑힌 그림에 있던 색만 남는다.
3) 손보기: FIXES 의 칸만 바꾼다. 손보기 전 그림(_unfixed.png)을 남기고, 바꾼 칸을 _fixes.json 에 적는다.
4) 검사: 반투명 0, 팔레트 이탈 0, 키 · 머리 · 등신 · 색 수 · 외톨이 픽셀.
출력: <폴더>/<이름>_master.png (1배) · _master_x8.png · _palette.hex · _palette.gpl · _master_info.json
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
from pixel_master import head_height, orphan_ratio  # noqa: E402

TARGET = 16  # 색 수의 목표
STOP = 14.0  # 이보다 먼 두 색은 묶지 않는다 (Lab ΔE)
RUNS = {"a_selout": "nx07_v1a", "b_flat": "nx07_v1b", "c_flat2": "nx07_v1c"}

# 손보기 (x, y, 새 색 = 같은 그림의 다른 칸 (sx, sy) 의 색, 이유). 칸 좌표는 마스터(1배)의 것.
# 새 색을 만들지 않고 그 그림에 이미 있는 칸의 색을 가져온다.
EAR = "귀 원반 가운데의 시안 1칸이 회색 고리 안의 눈동자처럼 보여 얼굴에 눈이 둘로 읽힌다 (견본 2 에서 짚은 문제). 원반의 밝은 회색으로 메워 민 원반으로 만든다"
FIXES: dict[str, list[tuple[int, int, int, int, str]]] = {
    "a_selout": [
        (7, 12, 8, 12, EAR),
        (22, 24, 22, 25, "총구 테두리의 모서리 1칸이 이 칸에만 있는 어두운 청록(#295140)이다. 바로 아래 테두리 색으로 맞춘다 (팔레트에서 한 색이 빠진다)"),
    ],
    "b_flat": [
        (7, 12, 6, 12, EAR),
    ],
}


def lab(c: np.ndarray) -> np.ndarray:
    """sRGB (0~255) → CIE Lab."""
    c = c.astype(float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def merge_colors(m: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    """색 묶기. 지각 거리(Lab ΔE)가 가장 가까운 두 색부터 묶는다 (칸이 적은 쪽을 많은 쪽 색으로).
    TARGET 색이 되거나, 가장 가까운 두 색도 STOP 보다 멀면 멈춘다 (살색 · 슈트처럼 다른 색이 합쳐지지 않게)."""
    op = m[..., 3] > 0
    cols, cnt = np.unique(m[op][:, :3].astype(int), axis=0, return_counts=True)
    L = lab(cols)
    root = list(range(len(cols)))
    weight = {i: int(cnt[i]) for i in range(len(cols))}
    alive = list(range(len(cols)))
    merged = []
    while len(alive) > TARGET:
        best = None
        for ai in range(len(alive)):
            for bi in range(ai + 1, len(alive)):
                p, q = alive[ai], alive[bi]
                dd = float(np.linalg.norm(L[p] - L[q]))
                if best is None or dd < best[0]:
                    best = (dd, p, q)
        dd, p, q = best
        if dd > STOP:
            break
        big, small = (p, q) if weight[p] >= weight[q] else (q, p)
        root = [big if r == small else r for r in root]
        merged.append({"from": "%02x%02x%02x" % tuple(cols[small]), "into": "%02x%02x%02x" % tuple(cols[big]),
                       "cells": weight[small], "dE": round(dd, 1)})
        weight[big] += weight.pop(small)
        alive.remove(small)
    out = m.copy()
    lut = {tuple(int(v) for v in cols[i]): cols[root[i]] for i in range(len(cols))}
    ys, xs = np.where(op)
    for y, x in zip(ys, xs):
        out[y, x, :3] = lut[tuple(int(v) for v in m[y, x, :3])]
    return out, merged


def palette_of(m: np.ndarray) -> np.ndarray:
    op = m[..., 3] > 0
    cols, cnt = np.unique(m[op][:, :3], axis=0, return_counts=True)
    lum = cols @ np.array([0.299, 0.587, 0.114])
    return cols[np.argsort(lum)]


def check(m: np.ndarray, pal: np.ndarray) -> dict:
    a = m[..., 3]
    semi = int(((a > 0) & (a < 255)).sum())
    pset = {tuple(int(v) for v in c) for c in pal}
    off = int(sum(tuple(int(v) for v in m[y, x, :3]) not in pset for y, x in zip(*np.where(a > 0))))
    h, head = head_height(m)
    return {"size": [m.shape[1], m.shape[0]], "height": h, "head": head, "heads_tall": round(h / head, 2),
            "colors": len(pal), "semi_transparent": semi, "off_palette": off, "orphan_pct": round(orphan_ratio(m) * 100, 1)}


def save(m: np.ndarray, d: Path, stem: str, extra: dict) -> None:
    pal = palette_of(m)
    Image.fromarray(m, "RGBA").save(d / f"{stem}.png")
    Image.fromarray(m, "RGBA").resize((m.shape[1] * 8, m.shape[0] * 8), Image.NEAREST).save(d / f"{stem}_x8.png")
    (d / f"{stem}_palette.hex").write_text("\n".join("%02x%02x%02x" % tuple(c) for c in pal) + "\n", encoding="utf-8")
    gpl = ["GIMP Palette", f"Name: {stem}", "Columns: 8", "#"] + [f"{c[0]:3d} {c[1]:3d} {c[2]:3d}\t{'%02x%02x%02x' % tuple(c)}" for c in pal]
    (d / f"{stem}_palette.gpl").write_text("\n".join(gpl) + "\n", encoding="utf-8")
    mt = check(m, pal)
    # charpipe.py 가 읽는 모양 (master.metrics) 을 따른다
    info = {"master": {"name": "known16", "cell": 16, "metrics": mt, "spread": 0.0}, "picked": "known16",
            "recommended": None, "metrics": mt, **extra}
    (d / f"{stem}_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(stem, mt)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for d, n in RUNS.items():
        k = LAB / d / f"{n}_known16.png"
        if not k.exists():
            continue
        m, merged = merge_colors(np.array(Image.open(k).convert("RGBA")))
        m[..., 3] = np.where(m[..., 3] > 0, 255, 0)
        base = {"src": f"art/pipeline_lab/pixel_style/v1/{d}/{n}_raw.png", "grid": {"cell": 16, "origin": [320, 64]},
                "method": f"알려진 격자의 칸 대표색 → Lab ΔE 가 가까운 색끼리 묶기 (목표 {TARGET}색, ΔE {STOP} 넘으면 멈춤)", "merged": merged, "doc": "docs/GAME_DESIGN.md 9.11.2"}
        fx = FIXES.get(d, [])
        if fx:
            save(m, LAB / d, f"{n}_unfixed", base | {"note": "손보기 전"})
            log = []
            for x, y, sx, sy, why in fx:
                before = "%02x%02x%02x" % tuple(m[y, x, :3])
                m[y, x] = m[sy, sx]
                log.append({"cell": [x, y], "before": before, "after": "%02x%02x%02x" % tuple(m[y, x, :3]), "color_from": [sx, sy], "why": why})
            (LAB / d / f"{n}_fixes.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
            base = base | {"fixes": f"{n}_fixes.json", "unfixed": f"{n}_unfixed.png"}
        save(m, LAB / d, f"{n}_master", base)


if __name__ == "__main__":
    main()
