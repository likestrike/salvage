"""뽑힌 그림이 안내 그림의 격자(칸 16px, 원점 x=336·y=64)에 맞게 그려졌는지 잰다 (기획서 9.11).

    python art/pipeline_lab/pixel_style/grid_check.py

칸마다 가운데(가장자리 3px 뺀 10×10)의 픽셀이 칸의 대표색(가장 많은 색)과 얼마나 같은지(ΔRGB < 40)를 잰다.
'고른 칸'은 그 비율이 90% 넘는 칸이다. 칸 원점을 반 칸(8px) 밀어 같은 값을 재서 견준다 (격자에 맞으면 원래 원점이 높다).
또 '알려진 격자'로 바로 칸을 뽑은 마스터(known16)를 저장한다: 칸 가운데의 다수결, 칸의 반 넘게 마젠타면 투명.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from process_sheet import key_mask  # noqa: E402

CELL, OX, OY = 16, 336, 64


def measure(rgb: np.ndarray, ox: int, oy: int) -> tuple[float, int, np.ndarray]:
    bg = key_mask(rgb)
    h, w = rgb.shape[:2]
    nx, ny = (w - ox) // CELL, (h - oy) // CELL
    good = tot = 0
    out = np.zeros((ny, nx, 4), np.uint8)
    for j in range(ny):
        for i in range(nx):
            y0, x0 = oy + j * CELL, ox + i * CELL
            c = rgb[y0:y0 + CELL, x0:x0 + CELL].reshape(-1, 3).astype(int)
            b = bg[y0:y0 + CELL, x0:x0 + CELL].ravel()
            if b.mean() > 0.5:
                continue
            inner = rgb[y0 + 3:y0 + CELL - 3, x0 + 3:x0 + CELL - 3].reshape(-1, 3).astype(int)
            q = inner // 12
            keys, cnt = np.unique(q, axis=0, return_counts=True)
            rep = inner[(q == keys[cnt.argmax()]).all(1)].mean(0)
            same = (np.abs(inner - rep).sum(1) < 40).mean()
            tot += 1
            good += same > 0.9
            out[j, i, :3] = np.round(rep).astype(np.uint8)
            out[j, i, 3] = 255
    return good / max(1, tot), tot, out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for v in ("flat", "dark", "dark2"):
        rgb = np.array(Image.open(LAB / f"sample_{v}/nx07_side_{v}_raw.png").convert("RGB"))
        r0, n, m = measure(rgb, OX, OY)
        r1, _, _ = measure(rgb, OX + 8, OY + 8)
        ys, xs = np.where(m[..., 3] > 0)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        Image.fromarray(m, "RGBA").save(LAB / f"sample_{v}/nx07_side_{v}_known16.png")
        print(f"{v}: 고른 칸 {r0*100:.0f}% (반 칸 민 격자 {r1*100:.0f}%), 칸 {n}개, known16 마스터 {m.shape[1]}×{m.shape[0]}")


if __name__ == "__main__":
    main()
