"""NX-07 픽셀 마스터 v2 후보 비교 그림 compare.png (기획서 9.11.4). 우리 그림만 들어간다.

    python art/pipeline_lab/pixel_style/v2/make_guide.py
    python art/pipeline_lab/pixel_style/v2/make_prompts.py
    (fal.ai 2단계)
    python art/pipeline_lab/pixel_style/v2/make_master.py
    python art/pipeline_lab/pixel_style/v2/make_compare_v2.py

① v1 후보 B 와 v2 후보를 같은 칸 크기(×10)로.
② 만든 길: 1단계(밑그림 없이 자유롭게) → 밑그림(목표 칸 수로 다시 깐 것) → 2단계(밑그림 위에 깨끗하게) → 마스터.
③ 어두운 게임 화면에 실제 크기로: 480×270 (×4) 누르기 1단계 · 2단계, 320×180 (×6) 누르기 2단계.
배경은 높이 360 의 지금 그림을 줄여(nearest) 대신 썼다 (그 밀도로 그린 배경이 아니다).
참고 그림(다른 회사의 작품)은 넣지 않는다. 참고 그림과 나란히 놓은 그림은 reference/pixel_style/analysis/compare_v2_vs_ref.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(LAB.parent / "v1"))
from pixel_master import crop_alpha, head_height, load_cutout  # noqa: E402
from make_compare_v1 import BG, GOLD, PANEL, PRESS, SUB, TXT, font  # noqa: E402

RECOMMEND = "C48"
NAMES = {
    "A36": ("v2 A36 · 어두운 몸이 주인", "키 36칸 (도트6 굵기)"),
    "C36": ("v2 C36 · 어두운 몸 + 뒤에서 오는 빛", "키 36칸 (도트6 굵기)"),
    "C48": ("v2 C48 · 어두운 몸 + 뒤에서 오는 빛", "키 48칸 (게임 화면 쪽)"),
    "B48": ("v2 B48 · 올리브 장갑이 주인", "키 48칸 (게임 화면 쪽)"),
}
ORDER = ["A36", "C36", "C48", "B48"]


def master(j: str, fixed: bool = True) -> np.ndarray:
    p = LAB / j / f"nx07_v2{j}_{'master' if fixed else 'unfixed'}.png"
    if not p.exists():
        p = LAB / j / f"nx07_v2{j}_master.png"
    return crop_alpha(np.array(Image.open(p).convert("RGBA")))


def zoom(a: np.ndarray, z: int, bg=PANEL) -> Image.Image:
    im = Image.fromarray(a, "RGBA").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST)
    b = Image.new("RGBA", im.size, bg + (255,))
    b.alpha_composite(im)
    return b


def raw_fit(p: Path, h: int) -> Image.Image:
    a = load_cutout(p)
    ys, xs = np.where(a[..., 3] > 0)
    a = a[max(ys.min() - 8, 0):ys.max() + 9, max(xs.min() - 8, 0):xs.max() + 9]
    b = Image.new("RGBA", (a.shape[1], a.shape[0]), PANEL + (255,))
    b.alpha_composite(Image.fromarray(a, "RGBA"))
    k = h / b.height
    return b.resize((int(b.width * k), h), Image.NEAREST)


def background(w: int, h: int, press: str) -> tuple[Image.Image, int]:
    src = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGB")
    k = h / 360
    bg = src.resize((int(round(src.width * k)), h), Image.NEAREST).crop((0, 0, w, h))
    keep, dim = PRESS[press]
    if keep < 1:
        bg = Image.blend(bg.convert("L").convert("RGB"), bg, keep)
    bg = bg.convert("RGBA")
    floor = int(round(h * 304 / 360))
    bg.alpha_composite(Image.new("RGBA", (w, floor), (10, 12, 24, int(255 * dim))))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, floor, w, h], fill=(18, 19, 28, 255))
    d.line([(0, floor), (w, floor)], fill=(58, 64, 88, 255))
    return bg, floor


def screen(w: int, h: int, press: str, chars: list[tuple[str, np.ndarray, bool]]) -> Image.Image:
    bg, floor = background(w, h, press)
    span = w * 0.86
    pos = []
    for i, (name, a, rec) in enumerate(chars):
        x = int(w * 0.06 + span * i / max(1, len(chars)))
        bg.alpha_composite(Image.fromarray(a, "RGBA"), (x, floor - a.shape[0]))
        pos.append((name, x, a.shape[0], a.shape[1], rec))
    z = 1080 // h
    big = bg.resize((w * z, h * z), Image.NEAREST)
    dd = ImageDraw.Draw(big)
    for name, x, ch, cw, rec in pos:
        if rec:
            dd.rectangle([x * z - 8, (floor - ch) * z - 8, (x + cw) * z + 8, floor * z + 4], outline=GOLD, width=4)
        dd.text((x * z, floor * z + 14), name, font=font(22), fill=GOLD if rec else TXT)
        dd.text((x * z, floor * z + 44), f"키 {ch}칸 · 화면 높이의 1/{h / ch:.1f}", font=font(16), fill=SUB)
    return big


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    v1b = master_v1 = crop_alpha(np.array(Image.open(LAB.parent / "v1/b_flat/nx07_v1b_master.png").convert("RGBA")))
    ms = {j: master(j) for j in ORDER}
    pad, gap, Z = 36, 40, 10

    W = 1920 + 2 * pad
    H = 6400
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), "NX-07 픽셀 마스터 v2 후보 — 두 번에 나눠 뽑기: 자유롭게 그리기 → 칸 맞춰 다시 그리기 (기획서 9.11.4)", font=font(30), fill=(240, 240, 245))
    d.text((pad, 66), "①은 ×10 (nearest). 단순화와 밝기 계획은 [제안]. 주포는 먼 쪽 팔(캐릭터의 왼팔), 앞쪽 팔은 검은 주먹. 승인 기록 없음 (실험).", font=font(16), fill=SUB)
    d.text((pad, 90), "참고 그림(다른 회사의 작품)은 이 그림에 넣지 않았다. 참고 그림과 같은 칸 크기로 견준 것은 reference/pixel_style/analysis/compare_v2_vs_ref.png (공개하지 않음).", font=font(16), fill=SUB)

    # ①
    y = 140
    d.text((pad, y), "① v1 후보 B (채택되지 않음) 와 v2 후보 — 같은 칸 크기 ×10", font=font(24), fill=TXT)
    y += 44
    row = [("v1 후보 B", "채택되지 않음 · 키 56칸", v1b, False)] + [(NAMES[j][0], NAMES[j][1], ms[j], j == RECOMMEND) for j in ORDER]
    tallest = max(a.shape[0] for *_, a, _ in row) * Z
    base = y + 70 + tallest
    x = pad
    for title, sub, a, rec in row:
        im = zoom(a, Z)
        d.text((x, y), title, font=font(19), fill=GOLD if rec else TXT)
        d.text((x, y + 30), sub, font=font(16), fill=SUB)
        sheet.paste(im.convert("RGB"), (x, base - im.height))
        if rec:
            d.rectangle([x - 8, base - im.height - 8, x + im.width + 8, base + 8], outline=GOLD, width=4)
            d.text((x, base - im.height - 40), "가장 낫다고 본 것", font=font(20), fill=GOLD)
        hh, hd = head_height(a)
        n = len(np.unique(a[a[..., 3] > 0][:, :3], axis=0))
        d.text((x, base + 14), f"키 {hh}칸 · {hh / hd:.1f}등신 · {n}색", font=font(17), fill=TXT)
        x += max(im.width, 300) + gap
    y = base + 80

    # ②
    d.text((pad, y), "② 만든 길 — 1단계 (밑그림 없이, 단순화와 밝기 계획을 글로만) → 밑그림 (목표 칸 수로 다시 깐 것) → 2단계 (그 격자 위에 깨끗하게) → 마스터", font=font(22), fill=TXT)
    y += 40
    d.text((pad, y), "1단계가 자세 · 덩어리 · 밝기를 설계했다 (칸은 12~26px 로 고르지 않다). 밑그림에서 머리를 조금 줄여 약 3등신 → 3.4~3.6등신으로 맞췄다. 2단계는 그 격자에 93~99% 맞았다.", font=font(16), fill=SUB)
    y += 34
    for j in ORDER:
        plan = j[0]
        th = 300
        parts = [("1단계 그림", raw_fit(LAB / "s1" / f"nx07_v2s1_{plan}_raw.png", th)),
                 ("밑그림", raw_fit(ROOT / f"art/prompts/pipeline/nx07_side_v2_guide{j[1:]}_{plan}.png", th)),
                 ("2단계 그림", raw_fit(LAB / "s2" / f"nx07_v2_{j}_raw.png", th))]
        fx = (LAB / j / f"nx07_v2{j}_unfixed.png").exists()
        mz = 300 // ms[j].shape[0]
        if fx:
            parts.append(("손보기 전", zoom(master(j, False), mz)))
        parts.append(("마스터" + (" (손본 뒤)" if fx else ""), zoom(ms[j], mz)))
        d.text((pad, y), f"{NAMES[j][0]} · {NAMES[j][1]}", font=font(19), fill=GOLD if j == RECOMMEND else TXT)
        yy = y + 32
        x = pad
        for t, im in parts:
            sheet.paste(im.convert("RGB"), (x, yy + th - im.height))
            d.text((x, yy + th + 6), t, font=font(15), fill=SUB)
            x += im.width + 22
        y = yy + th + 44

    # ③
    v1 = ("v1 B", v1b, False)
    cs = [(j, ms[j], j == RECOMMEND) for j in ORDER]
    scr = [
        ("③ 480×270 (×4) · 배경 누르기 1단계 (채도 50% · 55% 어둡게) — 실제 크기 그대로", screen(480, 270, "p1", [v1] + cs)),
        ("③ 480×270 (×4) · 배경 누르기 2단계 (채도 25% · 70% 어둡게)", screen(480, 270, "p2", [v1] + cs)),
        ("③ 320×180 (×6) · 누르기 2단계 — 36칸 후보가 화면 높이의 1/5 가 되는 해상도 (참고 게임 화면의 캐릭터 비율)", screen(320, 180, "p2", [(j, ms[j], False) for j in ("A36", "C36")])),
    ]
    for title, im in scr:
        d.text((pad, y), title, font=font(22), fill=GOLD if "2단계" in title else TXT)
        sheet.paste(im.convert("RGB"), (pad, y + 40))
        y += 40 + im.height + 90
    sheet = sheet.crop((0, 0, W, y))
    out = LAB / "compare.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
