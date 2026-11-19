"""격자를 찾아 줄이는 도구(proper-pixel-art 등)의 결과를 게임용 시트로 다시 깐다.
그런 도구는 그림이 그려진 격자대로 줄이므로 칸 크기가 정수로 떨어지지 않는다 (마젠타 배경).

    python tools/repack_sheet.py <도구의 결과.png> <출력.png> --cols 8 --rows 4 --cell 112

1. 마젠타 배경을 투명으로 바꾼다.
2. 칸 경계(전체 폭 / 열 수)를 기준으로 칸을 잘라, 같은 크기의 정사각 칸에 가운데·바닥 맞춤으로 다시 깐다.
"""
import argparse

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--cols", type=int, required=True)
ap.add_argument("--rows", type=int, required=True)
ap.add_argument("--cell", type=int, required=True)
args = ap.parse_args()

a = np.array(Image.open(args.src).convert("RGBA"))
r, g, b = (a[..., i].astype(int) for i in range(3))
keyed = (r - g > 50) & (b - g > 50) & (np.abs(r - b) < 90)
spill = (r - g > 30) & (b - g > 30)
for _ in range(2):                      # 배경과 맞닿은 분홍 테두리
    near = np.zeros_like(keyed)
    near[1:, :] |= keyed[:-1, :]; near[:-1, :] |= keyed[1:, :]
    near[:, 1:] |= keyed[:, :-1]; near[:, :-1] |= keyed[:, 1:]
    keyed |= near & spill
a[keyed] = 0

h, w = a.shape[:2]
cw, ch = w / args.cols, h / args.rows
C = args.cell
out = np.zeros((C * args.rows, C * args.cols, 4), dtype=np.uint8)
for row in range(args.rows):
    for col in range(args.cols):
        x0, x1 = round(col * cw), round((col + 1) * cw)
        y0, y1 = round(row * ch), round((row + 1) * ch)
        crop = a[y0:y1, x0:x1]
        kh, kw = crop.shape[:2]
        if kw > C:
            off = (kw - C) // 2; crop = crop[:, off:off + C]
        if kh > C:
            crop = crop[kh - C:]            # 넘치면 위쪽(머리 위 빈 곳)을 잘라 바닥을 지킨다
        kh, kw = crop.shape[:2]
        oy, ox = row * C + (C - kh), col * C + (C - kw) // 2
        out[oy:oy + kh, ox:ox + kw] = crop
Image.fromarray(out).save(args.out)

op = out[..., 3] > 0
print(f"[saved] {args.out} ({out.shape[1]}x{out.shape[0]}, 칸 {C}px, 원래 칸 {cw:.1f}x{ch:.1f})")
for row in range(args.rows):
    line = []
    for col in range(args.cols):
        cell = op[row * C:(row + 1) * C, col * C:(col + 1) * C]
        ys = np.flatnonzero(cell.any(axis=1))
        line.append("-" if len(ys) == 0 else f"{ys[0]}-{ys[-1]}")
    print("  row", row, "y", " ".join(line))
