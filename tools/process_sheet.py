"""AI 가 뽑은 스프라이트 시트(마젠타 배경)를 게임용으로 정리한다.

1. 마젠타 배경과 격자선을 투명으로 바꾼다.
2. 격자선을 찾아 칸을 자르고, 같은 크기의 칸으로 다시 깐다.
3. 원본의 '큰 픽셀'을 실제 1픽셀로 줄인 1x 시트를 만든다 (팔레트 제한 + 블록 최빈색).

사용 예:
    python tools/process_sheet.py art/sprites/nx07_sheet_raw.png --cols 6 --rows 4 \
        --scale 4 --cell 104 --out art/sprites/nx07_sheet.png

출력:
    nx07_sheet.png      투명 배경, 원본 해상도 (칸 = cell*scale)
    nx07_sheet_1x.png   투명 배경, 게임 해상도 (칸 = cell)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def key_mask(rgb: np.ndarray) -> np.ndarray:
    """마젠타 계열(배경·격자선·그 경계 번짐)이면 True."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    keyed = (r - g > 50) & (b - g > 50) & (np.abs(r - b) < 70)
    # 배경과 맞닿은 테두리에 남은 분홍·보라 번짐을 두 번 더 깎아 낸다.
    spill = (r - g > 30) & (b - g > 30)
    for _ in range(2):
        near = np.zeros_like(keyed)
        near[1:, :] |= keyed[:-1, :]
        near[:-1, :] |= keyed[1:, :]
        near[:, 1:] |= keyed[:, :-1]
        near[:, :-1] |= keyed[:, 1:]
        keyed |= near & spill
    return keyed


def despill(rgb: np.ndarray) -> np.ndarray:
    """배경의 마젠타가 흰색·회색에 묻어난 붉은 보랏빛을 걷어 낸다."""
    out = rgb.astype(int)
    cast = np.clip(np.minimum(out[..., 0], out[..., 2]) - out[..., 1], 0, None)
    out[..., 0] -= cast
    out[..., 2] -= cast
    return out.astype(np.uint8)


def bands(flags: np.ndarray) -> list[tuple[int, int]]:
    idx = np.flatnonzero(flags)
    out, start, prev = [], None, None
    for i in idx:
        if start is None:
            start = i
        elif i != prev + 1:
            out.append((start, prev))
            start = i
        prev = i
    if start is not None:
        out.append((start, prev))
    return out


def cell_spans(line_ratio: np.ndarray, n: int) -> list[tuple[int, int]]:
    """격자선 띠를 찾아 칸 구간을 돌려준다. 못 찾으면 균등 분할."""
    size = len(line_ratio)
    found = bands(line_ratio > 0.5)
    inner = [b for b in found if b[0] > size * 0.05 and b[1] < size * 0.95]
    if len(inner) == n - 1:
        start = found[0][1] + 1 if found and found[0][0] <= 2 else 0
        end = found[-1][0] - 1 if found and found[-1][1] >= size - 3 else size - 1
        edges = [start] + [v for b in inner for v in (b[0] - 1, b[1] + 1)] + [end]
        return [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    step = size / n
    return [(round(i * step), round((i + 1) * step) - 1) for i in range(n)]


def downscale(rgba: np.ndarray, scale: int, colors: int) -> np.ndarray:
    """scale x scale 블록마다 가장 많이 나온 색 하나로 줄인다."""
    h, w = rgba.shape[0] // scale, rgba.shape[1] // scale
    rgba = rgba[: h * scale, : w * scale]
    opaque = rgba[..., 3] > 127

    # 팔레트는 불투명 픽셀만으로 뽑는다 (배경색이 팔레트 자리를 차지하지 않게).
    solid = rgba[..., :3][opaque].reshape(1, -1, 3)
    # FASTOCTREE: 폭발의 주황처럼 양이 적은 색도 팔레트에 남는다.
    pal_src = Image.fromarray(solid).quantize(
        colors, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE
    )
    pal_img = Image.fromarray(rgba[..., :3]).quantize(palette=pal_src, dither=Image.Dither.NONE)
    palette = np.array(pal_src.getpalette()[: colors * 3], dtype=np.uint8).reshape(-1, 3)
    idx = np.asarray(pal_img).astype(np.int16)
    idx[~opaque] = -1

    blocks = idx.reshape(h, scale, w, scale).transpose(0, 2, 1, 3).reshape(h, w, scale * scale)
    counts = np.stack([(blocks == k).sum(-1) for k in range(len(palette))], axis=-1)
    best = counts.argmax(-1)
    filled = (blocks >= 0).sum(-1) >= (scale * scale) // 2

    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = palette[best]
    out[..., 3] = np.where(filled, 255, 0)
    out[~filled, :3] = 0
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="스프라이트 시트 후처리")
    ap.add_argument("src")
    ap.add_argument("--cols", type=int, required=True)
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--scale", type=int, default=4, help="원본의 큰 픽셀 한 칸이 몇 px 인지")
    ap.add_argument("--cell", type=int, default=104, help="1x 시트의 칸 크기(px)")
    ap.add_argument("--cell-h", type=int, default=None,
                    help="1x 시트의 칸 높이(px). 세로로 긴 칸일 때만 준다 (기본: --cell 과 같다)")
    ap.add_argument("--colors", type=int, default=48, help="1x 시트 팔레트 색 수")
    ap.add_argument("--no-despill", action="store_true",
                    help="분홍·보라가 원래 들어간 캐릭터라면 켠다 (마젠타 번짐 제거를 끈다)")
    ap.add_argument("--auto-rows", action="store_true",
                    help="행 높이가 고르지 않게 그려진 시트: 빈 줄을 기준으로 행을 찾고, 각 행을 칸의 바닥에 맞춰 깐다")
    ap.add_argument("--bottom", type=int, default=6, help="--auto-rows 일 때 칸 아래쪽 여백 (1x px)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rgb = np.asarray(Image.open(args.src).convert("RGB"))
    keyed = key_mask(rgb)
    dark_line = keyed & (rgb[..., 0] < 160)

    xs = cell_spans(dark_line.mean(axis=0), args.cols)
    ys = cell_spans(dark_line.mean(axis=1), args.rows)
    if args.auto_rows:
        filled = np.flatnonzero((~keyed).any(axis=1))
        found, start, prev = [], filled[0], filled[0]
        for y in filled[1:]:
            if y - prev > 12:
                found.append((int(start), int(prev)))
                start = y
            prev = y
        found.append((int(start), int(prev)))
        if len(found) != args.rows:
            sys.exit(f"행을 {args.rows}개 찾아야 하는데 {len(found)}개를 찾았다: {found}")
        ys = found

    if not args.no_despill:
        rgb = despill(rgb)
    rgba = np.dstack([rgb, np.where(keyed, 0, 255).astype(np.uint8)])
    big = args.cell * args.scale                       # 칸 너비
    big_h = (args.cell_h or args.cell) * args.scale    # 칸 높이
    sheet = np.zeros((big_h * args.rows, big * args.cols, 4), dtype=np.uint8)
    for r, (y0, y1) in enumerate(ys):
        for c, (x0, x1) in enumerate(xs):
            crop = rgba[y0 : y1 + 1, x0 : x1 + 1]
            ch, cw = crop.shape[:2]
            # 칸보다 크면 가운데 기준으로 잘라 낸다.
            if cw > big:
                off = (cw - big) // 2
                crop = crop[:, off : off + big]
            if ch > big_h:
                off = (ch - big_h) // 2
                crop = crop[off : off + big_h]
            ch, cw = crop.shape[:2]
            oy, ox = r * big_h + (big_h - ch) // 2, c * big + (big - cw) // 2
            if args.auto_rows:      # 행 전체를 같은 만큼 옮겨 바닥에 맞춘다 (프레임 사이의 움직임은 그대로 남는다)
                oy = r * big_h + big_h - args.bottom * args.scale - ch
            sheet[oy : oy + ch, ox : ox + cw] = crop

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(sheet).save(out)
    small = downscale(sheet, args.scale, args.colors)
    out_1x = out.with_name(f"{out.stem}_1x{out.suffix}")
    Image.fromarray(small).save(out_1x)

    print(f"칸 구간 x: {xs}")
    print(f"칸 구간 y: {ys}")
    print(f"[saved] {out} ({sheet.shape[1]}x{sheet.shape[0]}, 칸 {big}x{big_h}px)")
    print(f"[saved] {out_1x} ({small.shape[1]}x{small.shape[0]}, 칸 {args.cell}x{args.cell_h or args.cell}px)")


if __name__ == "__main__":
    main()
