"""Aseprite 가 없는 곳에서 nx07_pixel.lua 를 돌려 결과를 미리 본다.

같은 Lua 파일을 Lua 5.4 (Aseprite 와 같은 버전) 로 실행하고, 스크립트가 돌려준 픽셀 데이터를 PNG·GIF 로 저장한다.
그림을 계산하는 코드는 Aseprite 에서 돌릴 때와 똑같다. 다른 것은 파일로 저장하는 부분뿐이다.

    pip install lupa
    python art/aseprite/preview_without_aseprite.py
출력 (art/aseprite/preview/):
    nx07_pixel_sheet.png   한 줄에 애니메이션 하나, 칸 96 x 96 (색 인덱스, 투명 배경)
    nx07_pixel_sheet_x4.png 4배 확대
    <애니메이션>.gif        4배 확대 GIF
    check.txt              규칙 검사 (색 수, 반투명, 윤곽선, 키, 발바닥 행)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from lupa import lua54

HERE = Path(__file__).resolve().parent
OUT = HERE / "preview"
OUT.mkdir(exist_ok=True)

lua = lua54.LuaRuntime(encoding=None)
pack = lua.execute((HERE / "nx07_pixel.lua").read_bytes())

W, H = int(pack[b"W"]), int(pack[b"H"])
ground = int(pack[b"ground"])
pal_hex = [pack[b"palette"][i + 1].decode() for i in range(len(pack[b"palette"]))]
pal = [(0, 0, 0)] + [tuple(int(h[k:k + 2], 16) for k in (0, 2, 4)) for h in pal_hex]
flat_pal = [v for c in pal for v in c] + [0] * (768 - 3 * len(pal))

anims = []
for ai in range(len(pack[b"anims"])):
    a = pack[b"anims"][ai + 1]
    frames = []
    for fi in range(len(a[b"frames"])):
        f = a[b"frames"][fi + 1]
        px = np.frombuffer(f[b"px"], dtype=np.uint8).reshape(H, W)
        frames.append((px, float(f[b"dur"])))
    anims.append((a[b"name"].decode(), frames))


def indexed(arr):
    im = Image.fromarray(arr, "P")
    im.putpalette(flat_pal)
    im.info["transparency"] = 0
    return im


# 시트
maxf = max(len(f) for _, f in anims)
sheet = np.zeros((H * len(anims), W * maxf), np.uint8)
for r, (_, frames) in enumerate(anims):
    for i, (px, _) in enumerate(frames):
        sheet[r * H:(r + 1) * H, i * W:(i + 1) * W] = px
indexed(sheet).save(OUT / "nx07_pixel_sheet.png", transparency=0)
rgba = indexed(sheet).convert("RGBA")
bg = Image.new("RGBA", rgba.size, (52, 50, 70, 255))
bg.alpha_composite(rgba)
bg.resize((rgba.width * 4, rgba.height * 4), Image.NEAREST).convert("RGB").save(OUT / "nx07_pixel_sheet_x4.png")

# GIF (4배, 어두운 바탕)
for name, frames in anims:
    imgs, durs = [], []
    for px, d in frames:
        im = indexed(px).convert("RGBA")
        b = Image.new("RGBA", im.size, (52, 50, 70, 255))
        b.alpha_composite(im)
        imgs.append(b.resize((W * 4, H * 4), Image.NEAREST).convert("RGB"))
        durs.append(int(d * 1000))
    imgs[0].save(OUT / f"{name}.gif", save_all=True, append_images=imgs[1:], duration=durs, loop=0)

# 규칙 검사
lines = []
used = set(np.unique(sheet).tolist()) - {0}
lines.append(f"색: 팔레트 {len(pal)}칸 (투명 1 + 색 {len(pal) - 1}), 실제로 쓴 색 {len(used)}")
lines.append("반투명: 없음 (색 인덱스 이미지, 투명은 0번 한 가지)")
bad = 0
total = 0
for name, frames in anims:
    for px, _ in frames:
        op = px != 0
        pad = np.pad(op, 1)
        edge = op & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        # 이펙트 색(시안·흰 빛·주황·노랑·흰 판 그늘 먼지)은 윤곽선 없이 그린다
        fxcol = np.isin(px, [9, 10, 13, 14, 15, 7, 8])
        e = edge & ~fxcol
        total += int(e.sum())
        bad += int((e & (px != 1)).sum())
lines.append(f"윤곽선: 이펙트를 뺀 실루엣 가장자리 {total}px 중 윤곽선 색이 아닌 것 {bad}px")
for name, frames in anims:
    hs, bots = [], []
    for px, _ in frames:
        ys = np.flatnonzero((px != 0).any(axis=1))
        hs.append(int(ys[-1] - ys[0] + 1))
        bots.append(int(ys[-1]))
    lines.append(f"{name:7s} {len(frames)}프레임  높이 {min(hs)}~{max(hs)}px  가장 낮은 행 {sorted(set(bots))}")
(OUT / "check.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
json.dump({"cell": [W, H], "baseline": ground, "palette": ["#" + h for h in pal_hex],
           "anims": [{"name": n, "row": r, "frames": len(f), "durations": [d for _, d in f]} for r, (n, f) in enumerate(anims)]},
          open(OUT / "nx07_pixel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n".join(lines))
print("saved:", OUT)
