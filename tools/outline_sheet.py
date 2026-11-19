"""게임 해상도 시트의 실루엣 가장자리를 한 가지 외곽선 색으로 통일한다 (AI 호출 없음).
    python tools/outline_sheet.py <입력_1x.png> <출력.png> [칸=96]
칸마다 가장 큰 덩어리(몸)의 가장자리 픽셀만 바꾼다. 시안·주황 이펙트와 그 둘레 2px, 따로 떨어진 조각(탄, 연기)은 건드리지 않는다.
"""
import colorsys
import sys

import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
C = int(sys.argv[3]) if len(sys.argv) > 3 else 96
OUTLINE = (20, 20, 24)
a = np.array(Image.open(src).convert("RGBA"))
op = a[..., 3] > 0
h, w = op.shape
body = np.zeros_like(op)
for y0 in range(0, h, C):
    for x0 in range(0, w, C):
        cell = op[y0:y0 + C, x0:x0 + C]; seen = np.zeros_like(cell); best = []
        for y in range(cell.shape[0]):
            for x in range(cell.shape[1]):
                if not cell[y, x] or seen[y, x]:
                    continue
                stack, comp = [(y, x)], []; seen[y, x] = True
                while stack:
                    cy, cx = stack.pop(); comp.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < cell.shape[0] and 0 <= nx < cell.shape[1] and cell[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True; stack.append((ny, nx))
                if len(comp) > len(best):
                    best = comp
        for cy, cx in best:
            body[y0 + cy, x0 + cx] = True

rgb = a[..., :3].astype(float) / 255
mx, mn = rgb.max(axis=2), rgb.min(axis=2)
sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
hue = np.zeros_like(mx)
for y, x in zip(*np.nonzero(op & (sat > 0.3) & (mx > 0.55))):
    hue[y, x] = colorsys.rgb_to_hsv(*rgb[y, x])[0] * 360
eff = op & (((hue >= 160) & (hue <= 215) & (sat > 0.35) & (mx > 0.6)) | ((hue >= 8) & (hue <= 62) & (sat > 0.5) & (mx > 0.75)))
near = eff.copy()
for _ in range(2):
    g = near.copy()
    g[1:, :] |= near[:-1, :]; g[:-1, :] |= near[1:, :]; g[:, 1:] |= near[:, :-1]; g[:, :-1] |= near[:, 1:]
    near = g
pad = np.pad(op, 1)
edge = op & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
target = edge & body & ~near
a[target, :3] = OUTLINE
Image.fromarray(a).save(out)
print(f"[saved] {out} (외곽선 {int(target.sum())}px)")
