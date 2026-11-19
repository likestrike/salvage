"""픽셀 마스터 실험(기획서 9.11)의 최종 비교 그림 compare.png 를 만든다.

    python art/pipeline_lab/pixel_master/make_compare.py

(가) 설정화 측면 (나) E2-64 뽑힌 그림 + 마스터 + 첫 시도 (다) E2-83 뽑힌 그림 + 마스터 + 첫 시도 (라) E1 마스터 (마) 지금 게임의 도트 C.
마스터는 모두 같은 배율(×8, nearest), 발바닥을 한 줄에. 아래에 실제 크기(640×360 게임 화면 위, ×2).
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from pixel_master import crop_alpha, head_height, load_cutout  # noqa: E402

F = "C:/Windows/Fonts/malgunbd.ttf"
BG = (18, 19, 24)
PANEL = (30, 32, 40)
Z = 8

# 마스터 파일 (pixel_master.py 의 출력)
E2_64 = LAB / "e2_64"
E2_83 = LAB / "e2_83"
E1 = LAB / "e1"


def font(n):
    return ImageFont.truetype(F, n)


def rgba(p: Path) -> np.ndarray:
    return np.array(Image.open(p).convert("RGBA"))


def stats(a: np.ndarray) -> list[str]:
    h, head = head_height(a)
    n = len(np.unique(a[a[..., 3] > 0][:, :3], axis=0))
    return [f"키 {h}px · 머리 {head}px", f"{h / head:.1f}등신 · {n}색"]


def on_panel(im: Image.Image) -> Image.Image:
    b = Image.new("RGBA", im.size, PANEL + (255,))
    b.alpha_composite(im)
    return b


def master_img(a: np.ndarray) -> Image.Image:
    return on_panel(Image.fromarray(a, "RGBA").resize((a.shape[1] * Z, a.shape[0] * Z), Image.NEAREST))


def ref_img(a: np.ndarray, height: int) -> Image.Image:
    a = crop_alpha(a)
    k = height / a.shape[0]
    return on_panel(Image.fromarray(a, "RGBA").resize((max(1, int(a.shape[1] * k)), height), Image.BOX))


def setting_cutout() -> np.ndarray:
    """설정화는 흰 배경이다. 테두리에서 이어진 흰색만 지운다 (보기용)."""
    rgb = np.array(Image.open(ROOT / "art/concept/setting/nx07/02_side.png").convert("RGB"))
    h, w = rgb.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    img = rgb.copy()
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        cv2.floodFill(img, mask, seed, (0, 0, 0), (12, 12, 12), (12, 12, 12), cv2.FLOODFILL_MASK_ONLY | 8 | (255 << 8))
    a = np.dstack([rgb, np.where(mask[1:-1, 1:-1] > 0, 0, 255).astype(np.uint8)])
    return a


def main() -> None:
    c_idle = crop_alpha(rgba(ROOT / "art/sprites/nx07_states/idle.png")[:, :112])
    m64 = crop_alpha(rgba(LAB / "e2_64b/nx07_side_px64b.png"))      # 64칸 목표, 다시 뽑은 것
    m64a = crop_alpha(rgba(LAB / "e2_64/nx07_side_px64.png"))       # 64칸 목표, 첫 시도 (90칸으로 나옴)
    m83 = crop_alpha(rgba(LAB / "e2_83b/nx07_side_px83b.png"))      # 83칸 목표, 다시 뽑은 것
    m83a = crop_alpha(rgba(LAB / "e2_83/nx07_side_px83.png"))       # 83칸 목표, 첫 시도 (98칸으로 나옴)
    m1 = crop_alpha(rgba(E1 / "e1_side.png"))
    raw64 = load_cutout(LAB / "e2_64b/nx07_side_px64b_raw.png")
    raw83 = load_cutout(LAB / "e2_83b/nx07_side_px83b_raw.png")

    tallest = max(x.shape[0] for x in (c_idle, m64, m64a, m83, m83a, m1)) * Z
    ref_h = 83 * Z
    groups = [
        ("(가) 설정화 측면", "참고. 일러스트", [(ref_img(setting_cutout(), ref_h), ["02_side.png", "축소해서 보임"])]),
        ("(나) E2 · 키 64칸을 목표로 다시 그림", "다시 뽑은 것(뽑힌 그림 → 마스터)  |  첫 시도의 마스터",
         [(ref_img(raw64, ref_h), ["뽑힌 그림", "도트풍, 축소해서 보임", "격자가 고르지 않다"]),
          (master_img(m64), ["마스터 ×8"] + stats(m64)),
          (master_img(m64a), ["첫 시도 ×8", "목표보다 크게 나옴"] + stats(m64a) + ["격자가 고르다"])]),
        ("(다) E2 · 키 83칸을 목표로 다시 그림", "다시 뽑은 것(뽑힌 그림 → 마스터)  |  첫 시도의 마스터",
         [(ref_img(raw83, ref_h), ["뽑힌 그림", "도트풍, 축소해서 보임", "격자가 고르지 않다"]),
          (master_img(m83), ["마스터 ×8"] + stats(m83)),
          (master_img(m83a), ["첫 시도 ×8", "목표보다 크게 나옴"] + stats(m83a))]),
        ("(라) E1 · 있던 원본의 격자 복원", "stylec_side_raw.png (생성 0회)",
         [(master_img(m1), ["마스터 ×8"] + stats(m1))]),
        ("(마) C · 지금 게임의 도트", "nx07_states/idle.png 첫 프레임",
         [(master_img(c_idle), ["게임 그림 ×8"] + stats(c_idle))]),
    ]

    pad, gap = 36, 18
    head_area = 110
    W = pad
    for title, _, items in groups:
        W += max(sum(im.width for im, _ in items) + gap * (len(items) - 1), len(title) * 22) + pad
    base_y = 90 + head_area + tallest
    info_h = 120

    # 실제 크기: 640×360 게임 화면 위에 1배로 세우고 ×2
    view = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGBA").crop((0, 0, 640, 360))
    dim = Image.new("RGBA", (640, 304), (10, 12, 24, int(255 * 0.4)))
    view.alpha_composite(dim)
    d0 = ImageDraw.Draw(view)
    d0.rectangle([0, 304, 640, 360], fill=(18, 19, 28, 255))
    d0.line([(0, 304), (640, 304)], fill=(58, 64, 88, 255))
    actual = [("나", m64), ("나 첫", m64a), ("다", m83), ("다 첫", m83a), ("라", m1), ("마", c_idle)]
    x = 40
    for name, a in actual:
        view.alpha_composite(Image.fromarray(a, "RGBA"), (x, 304 - a.shape[0]))
        x += a.shape[1] + 46
    view2 = view.resize((1280, 720), Image.NEAREST)
    lab = ImageDraw.Draw(view2)
    x = 40
    for name, a in actual:
        lab.text((x * 2, 304 * 2 + 12), f"({name})", font=font(20), fill=(235, 235, 240))
        lab.text((x * 2, 304 * 2 + 40), f"{a.shape[0]}px", font=font(16), fill=(170, 175, 190))
        x += a.shape[1] + 46

    H = base_y + info_h + 70 + 720 + pad
    W = max(W, 1280 + 2 * pad)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), "NX-07 픽셀 마스터 실험 — 도트용으로 다시 그린 그림 → 격자로 칸마다 한 색 (기획서 9.11)", font=font(30), fill=(240, 240, 245))
    d.text((pad, 62), "마스터와 게임 그림은 모두 같은 배율(×8)이고 발바닥이 한 줄에 있다. 뽑힌 그림과 설정화는 참고로 축소해서 보인다.",
           font=font(17), fill=(170, 175, 190))
    x = pad
    for title, sub, items in groups:
        gw = max(sum(im.width for im, _ in items) + gap * (len(items) - 1), len(title) * 22)
        d.text((x, 100), title, font=font(22), fill=(255, 210, 90))
        d.text((x, 130), sub, font=font(15), fill=(170, 175, 190))
        ix = x
        for im, lines in items:
            sheet.paste(im.convert("RGB"), (ix, base_y - im.height))
            for i, t in enumerate(lines):
                d.text((ix, base_y + 10 + i * 22), t, font=font(16 if i else 17), fill=(235, 235, 240) if i == 0 else (190, 195, 205))
            ix += im.width + gap
        x += gw + pad
    d.line([(pad, base_y), (W - pad, base_y)], fill=(70, 74, 92), width=1)
    y2 = base_y + info_h + 20
    d.text((pad, y2), "실제 크기 — 게임 화면(640×360)에 1배로 세운 것을 2배로 확대", font=font(22), fill=(255, 210, 90))
    sheet.paste(view2.convert("RGB"), (pad, y2 + 40))
    out = LAB / "compare.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
