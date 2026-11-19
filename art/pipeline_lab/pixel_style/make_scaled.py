"""E1 마스터(키 118px)를 '작게' 만드는 길 (ㄴ)과, 새 스타일 견본을 뽑을 안내 그림을 만든다 (기획서 9.11).

    python art/pipeline_lab/pixel_style/make_scaled.py

(ㄴ-1) 다수결 축소: 118 → 83. 목표 칸마다 원본에서 덮는 영역의 픽셀 가운데 가장 많은 색 하나 (색을 섞지 않는다).
(ㄴ-2) 다시 격자 복원: 원본 그림(stylec_side_raw.png)을 키 83칸이 되는 큰 칸(약 11px)으로 복원한 것.
       9.11 E1 의 '억지 맞춤' 후보 e1/candidates/e1_side_11.02.png 를 그대로 쓴다 (새로 만들지 않는다).
안내 그림: E1 마스터를 같은 다수결로 키 56칸으로 줄여, 1024×1024 마젠타 위에 칸 16px 로 정확히 깐다.
       모델이 칸 수를 세지 못하므로(9.11) 크기와 격자를 그림으로 준다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parent
OUT = LAB / "scaled"


def majority_resize(a: np.ndarray, th: int) -> np.ndarray:
    """키를 th 칸으로. 가로도 같은 비율. 칸마다 덮는 원본 픽셀의 다수결 (투명도 한 표)."""
    h, w = a.shape[:2]
    k = th / h
    tw = max(1, int(round(w * k)))
    key = (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2]
    key[a[..., 3] == 0] = -1
    out = np.zeros((th, tw, 4), np.uint8)
    for ty in range(th):
        y0, y1 = int(np.floor(ty / k)), max(int(np.floor(ty / k)) + 1, int(np.ceil((ty + 1) / k)))
        for tx in range(tw):
            x0, x1 = int(np.floor(tx / k)), max(int(np.floor(tx / k)) + 1, int(np.ceil((tx + 1) / k)))
            block = key[y0:min(y1, h), x0:min(x1, w)].ravel()
            if block.size == 0:
                continue
            vals, cnt = np.unique(block, return_counts=True)
            v = vals[cnt.argmax()]
            if v >= 0:
                out[ty, tx] = (v >> 16 & 255, v >> 8 & 255, v & 255, 255)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    e1 = np.array(Image.open(LAB.parent / "pixel_master/e1/e1_side.png").convert("RGBA"))
    m83 = majority_resize(e1, 83)
    Image.fromarray(m83, "RGBA").save(OUT / "e1_majority83.png")
    m56 = majority_resize(e1, 56)
    Image.fromarray(m56, "RGBA").save(OUT / "e1_majority56.png")

    # 안내 그림: 칸 16px, 바닥 960
    cell = 16
    g = np.zeros((1024, 1024, 4), np.uint8)
    g[...] = (255, 0, 255, 255)
    big = np.array(Image.fromarray(m56, "RGBA").resize((m56.shape[1] * cell, m56.shape[0] * cell), Image.NEAREST))
    hh, ww = big.shape[:2]
    x0 = (1024 - ww) // 2 // cell * cell
    y0 = 960 - hh
    sub = g[y0:y0 + hh, x0:x0 + ww]
    op = big[..., 3] > 0
    sub[op] = big[op]
    Image.fromarray(g[..., :3], "RGB").save(ROOT / "art/prompts/pipeline/nx07_side_style_guide56.png")
    print("83:", m83.shape[:2], "56:", m56.shape[:2], "guide box", x0, y0, ww, hh)


if __name__ == "__main__":
    main()
