"""도트 스타일 방향 비교 그림 compare.png (기획서 9.11 '참고 그림의 스타일').

    python art/pipeline_lab/pixel_style/make_scaled.py     # (ㄴ) 축소본과 안내 그림
    python art/pipeline_lab/pixel_style/grid_check.py      # 뽑힌 그림의 격자 검사
    python art/pipeline_lab/pixel_style/make_compare.py

① 지금 게임의 도트(C) · E1 마스터 · (ㄴ) 도트를 줄인 두 가지 — 모두 ×8
② "저 상태로 작게"의 두 길을 게임 화면에: (ㄱ) 960×540 에 E1 그대로 / (ㄴ) 640×360 에 줄인 것
③ 새 스타일 견본: 밑그림 · 뽑힌 그림 · 마스터 (같은 배율 ×16)
④ 새 견본을 게임 화면에: 480×270 / 지금 해상도 640×360
화면은 모두 1920×1080 으로 정수배 확대(nearest)해서 같은 크기로 보이고, 왼쪽 절반만 잘라 보인다.
배경은 style_c/bg.png(높이 360) 하나뿐이라 다른 해상도에서는 늘이거나 줄여(nearest) 대신 썼다.
참고 그림(reference/pixel_style/)은 넣지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from pixel_master import crop_alpha, head_height, load_cutout  # noqa: E402

F = "C:/Windows/Fonts/malgunbd.ttf"
BG = (18, 19, 24)
PANEL = (30, 32, 40)
TXT = (235, 235, 240)
SUB = (175, 180, 195)
GOLD = (255, 210, 90)


def font(n):
    return ImageFont.truetype(F, n)


def rgba(p: Path) -> np.ndarray:
    return crop_alpha(np.array(Image.open(p).convert("RGBA")))


def stats(a: np.ndarray) -> list[str]:
    h, head = head_height(a)
    n = len(np.unique(a[a[..., 3] > 0][:, :3], axis=0))
    return [f"키 {h}px · 머리 {head}px", f"{h / head:.1f}등신 · {n}색"]


def zoom(a: np.ndarray, z: int) -> Image.Image:
    im = Image.fromarray(a, "RGBA").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST)
    b = Image.new("RGBA", im.size, PANEL + (255,))
    b.alpha_composite(im)
    return b


def raw_crop(p: Path) -> Image.Image:
    """뽑힌 그림(1024, 칸 16px)을 캐릭터 둘레만 잘라 배경을 패널색으로."""
    a = load_cutout(p)
    ys, xs = np.where(a[..., 3] > 0)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    b = Image.new("RGBA", (a.shape[1], a.shape[0]), PANEL + (255,))
    b.alpha_composite(Image.fromarray(a, "RGBA"))
    return b


def screen(w: int, h: int, chars: list[tuple[str, np.ndarray]]) -> Image.Image:
    """내부 해상도 w×h 의 게임 화면. 배경을 늘이거나 줄여 쓰고, 게임처럼 40% 어둡게 누른다. 발판 줄은 높이의 304/360."""
    src = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGBA")
    k = h / 360
    bg = src.resize((int(round(src.width * k)), h), Image.NEAREST).crop((0, 0, w, h))
    floor = int(round(h * 304 / 360))
    bg.alpha_composite(Image.new("RGBA", (w, floor), (10, 12, 24, int(255 * 0.4))))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, floor, w, h], fill=(18, 19, 28, 255))
    d.line([(0, floor), (w, floor)], fill=(58, 64, 88, 255))
    x = int(w * 0.06)
    pos = []
    for name, a in chars:
        bg.alpha_composite(Image.fromarray(a, "RGBA"), (x, floor - a.shape[0]))
        pos.append((name, x, a.shape[0]))
        x += max(a.shape[1] + int(w * 0.05), 230 // (1080 // h))  # 글자가 겹치지 않게
    z = 1080 // h
    big = bg.resize((w * z, h * z), Image.NEAREST).crop((0, 0, 960, 1080))
    dd = ImageDraw.Draw(big)
    for name, x, ch in pos:
        dd.text((x * z, floor * z + 14), name, font=font(20), fill=TXT)
        dd.text((x * z, floor * z + 42), f"{ch}px · 화면 높이의 1/{h / ch:.1f}", font=font(15), fill=SUB)
    return big


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    c_idle = crop_alpha(np.array(Image.open(ROOT / "art/sprites/nx07_states/idle.png").convert("RGBA"))[:, :112])
    e1 = rgba(LAB.parent / "pixel_master/e1/e1_side.png")
    maj83 = rgba(LAB / "scaled/e1_majority83.png")
    reg83 = rgba(LAB.parent / "pixel_master/e1/candidates/e1_side_11.02.png")
    flat = rgba(LAB / "sample_flat/nx07_side_flat.png")
    dark = rgba(LAB / "sample_dark2/nx07_side_dark2.png")

    pad, gap = 36, 22
    blocks: list[tuple[str, str, list[tuple[Image.Image, list[str]]]]] = []

    # ① ×8
    row1 = [
        ("(가) C · 지금 게임의 도트", "nx07_states/idle.png 첫 프레임", [(zoom(c_idle, 8), ["×8"] + stats(c_idle))]),
        ("(나) E1 마스터 = '마스터 8'로 읽은 것", "pixel_master/e1/e1_side.png · 지난 비교 그림 (라)", [(zoom(e1, 8), ["×8"] + stats(e1))]),
        ("(ㄴ) 도트를 줄인 것 (118 → 83)", "왼쪽: 다수결 축소  |  오른쪽: 원본에서 큰 칸(약 11px)으로 다시 격자 복원",
         [(zoom(maj83, 8), ["다수결 ×8"] + stats(maj83) + ["눈 · 귀 원반 · 외곽선이 끊긴다"]),
          (zoom(reg83, 8), ["다시 복원 ×8"] + stats(reg83) + ["9.11의 '억지 맞춤' 후보"])]),
    ]
    # ③ ×16 (뽑힌 그림의 칸이 16px 이므로 같은 배율)
    guide = raw_crop(ROOT / "art/prompts/pipeline/nx07_side_style_guide56.png")
    gm = load_cutout(ROOT / "art/prompts/pipeline/nx07_side_style_guide56.png")
    row3 = [
        ("밑그림 (넣은 것)", "E1 마스터를 다수결로 56칸, 칸 16px", [(guide, ["밑그림 ×16", "키 56칸 · 크기와 격자만 준다"])]),
        ("(다) 견본 1 · 검은 외곽선 없음", "뽑힌 그림  |  마스터", [
            (raw_crop(LAB / "sample_flat/nx07_side_flat_raw.png"), ["뽑힌 그림 (칸 16px)", "격자에 맞은 칸 99%"]),
            (zoom(flat, 16), ["마스터 ×16"] + stats(flat))]),
        ("(라) 견본 2 · 진한 색 외곽선", "뽑힌 그림  |  마스터  (첫 시도는 격자가 밀려 버림, 아래 작은 글)", [
            (raw_crop(LAB / "sample_dark2/nx07_side_dark2_raw.png"), ["뽑힌 그림 (칸 16px)", "격자에 맞은 칸 99%", "첫 시도: 66% (반 칸씩 밀림)"]),
            (zoom(dark, 16), ["마스터 ×16"] + stats(dark))]),
    ]

    def block_w(title, sub, items):
        return max(sum(im.width for im, _ in items) + gap * (len(items) - 1), int(len(title) * 21), int(len(sub) * 13))

    def draw_row(sheet, d, y, row, info_h=120):
        tallest = max(im.height for _, _, items in row for im, _ in items)
        base = y + 80 + tallest
        x = pad
        for title, sub, items in row:
            d.text((x, y), title, font=font(22), fill=GOLD)
            d.text((x, y + 32), sub, font=font(15), fill=SUB)
            ix = x
            for im, lines in items:
                sheet.paste(im.convert("RGB"), (ix, base - im.height))
                for i, t in enumerate(lines):
                    d.text((ix, base + 10 + i * 22), t, font=font(16), fill=TXT if i == 0 else SUB)
                ix += im.width + gap
            x += block_w(title, sub, items) + pad
        return base + info_h

    def row_w(row):
        return pad + sum(block_w(*b) + pad for b in row)

    scr2 = [
        ("(ㄱ) 해상도를 960×540 으로 올린다 · 도트는 그대로", screen(960, 540, [("E1 마스터", e1)])),
        ("(ㄴ) 해상도는 640×360 그대로 · 도트를 줄인다", screen(640, 360, [("C 지금", c_idle), ("다수결", maj83), ("다시 복원", reg83)])),
    ]
    scr4 = [
        ("480×270 (참고 그림의 화면 밀도에 가깝다)", screen(480, 270, [("견본 1", flat), ("견본 2", dark)])),
        ("지금 해상도 640×360 그대로 두면", screen(640, 360, [("C 지금", c_idle), ("견본 1", flat), ("견본 2", dark)])),
    ]
    W = max(row_w(row1), row_w(row3), pad + 2 * (960 + pad))
    H = 140 + (80 + 944 + 140) + (60 + 1080 + 40) + (80 + 896 + 140) + (60 + 1080 + 40) + 40
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), "NX-07 도트 스타일 방향 — 'E1 마스터를 작게' 두 길과, 참고 그림 방식의 새 견본 (기획서 9.11)", font=font(30), fill=(240, 240, 245))
    d.text((pad, 64), "①③ 은 확대 배율을 적었다 (nearest). ②④ 의 화면은 모두 1920×1080 으로 정수배 확대해 같은 크기로 보이고 왼쪽 절반만 보인다. "
                      "배경은 높이 360 의 지금 그림을 늘이거나 줄여 대신 썼다.", font=font(16), fill=SUB)
    d.text((pad, 90), "참고 그림 5장은 넣지 않았다 (reference/pixel_style/).", font=font(16), fill=SUB)

    y = 140
    d.text((pad, y), "① 지금 게임 · E1 마스터 · 도트를 줄인 것 (모두 ×8)", font=font(24), fill=TXT)
    y = draw_row(sheet, d, y + 44, row1)
    d.text((pad, y), "② '저 상태로 작게' — 화면에서 보이는 크기를 맞춘 두 길", font=font(24), fill=TXT)
    x = pad
    for t, im in scr2:
        d.text((x, y + 36), t, font=font(19), fill=GOLD)
        sheet.paste(im.convert("RGB"), (x, y + 66))
        x += im.width + pad
    y += 66 + 1080 + 40
    d.text((pad, y), "③ 새 스타일 견본 — 밑그림 · 뽑힌 그림 · 마스터 (같은 배율 ×16)", font=font(24), fill=TXT)
    y = draw_row(sheet, d, y + 44, row3)
    d.text((pad, y), "④ 새 견본을 어두운 게임 화면에 실제 크기로", font=font(24), fill=TXT)
    x = pad
    for t, im in scr4:
        d.text((x, y + 36), t, font=font(19), fill=GOLD)
        sheet.paste(im.convert("RGB"), (x, y + 66))
        x += im.width + pad
    y += 66 + 1080 + 40
    sheet = sheet.crop((0, 0, W, y))
    out = LAB / "compare.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
