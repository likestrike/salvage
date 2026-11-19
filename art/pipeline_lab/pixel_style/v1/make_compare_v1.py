"""NX-07 픽셀 마스터 v1 후보 비교 그림 compare.png (기획서 9.11.2).

    python art/pipeline_lab/pixel_style/v1/make_guide.py      # 밑그림
    (fal.ai)                                                 # 뽑기
    python tools/pixel_master.py <뽑힌 그림> <폴더> --name <이름> --cells 16 --colors 16   # 격자 검사의 근거
    python art/pipeline_lab/pixel_style/v1/grid_check_v1.py  # 알려진 격자로 칸 읽기
    python art/pipeline_lab/pixel_style/v1/make_master.py    # 색 묶기 · 손보기 · 마스터
    python art/pipeline_lab/pixel_style/v1/make_compare_v1.py

① 직전 견본 1 · 2 와 v1 후보를 같은 배율(×12)로 나란히. 주포가 어느 팔에 있는지 적는다.
② v1 후보를 480×270 화면에 실제 크기로 (×4 = 1920×1080): 배경 누르기 1단계 · 2단계, 게임이 그릴 때 더하는 테두리 빛.
③ 지금 게임의 도트(C)를 640×360 화면에 (×3 = 1920×1080, 게임과 같은 누르기 40%).
배경은 높이 360 의 지금 그림(game/assets/style_c/bg.png) 하나뿐이라 480×270 에서는 0.75배로 줄여(nearest) 대신 썼다.
참고 그림(reference/pixel_style/)은 넣지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
from pixel_master import crop_alpha, head_height, load_cutout  # noqa: E402

F = "C:/Windows/Fonts/malgunbd.ttf"
BG = (18, 19, 24)
PANEL = (30, 32, 40)
TXT = (235, 235, 240)
SUB = (175, 180, 195)
GOLD = (255, 210, 90)

# 추천 후보 (비교 그림에 금색 테두리로 표시)
RECOMMEND = "b"

# 배경 누르기: (채도를 남기는 비율, 어둡게 덮는 색의 불투명도). 덮는 색은 게임과 같은 (10, 12, 24)
PRESS = {"game": (1.0, 0.40), "p1": (0.5, 0.55), "p2": (0.25, 0.70)}
RIM = (176, 196, 228, 140)  # 게임이 그릴 때 더하는 1칸 테두리 빛 (색 · 불투명도) [제안]


def font(n):
    return ImageFont.truetype(F, n)


def rgba(p: Path) -> np.ndarray:
    return crop_alpha(np.array(Image.open(p).convert("RGBA")))


def stats(a: np.ndarray) -> list[str]:
    h, head = head_height(a)
    n = len(np.unique(a[a[..., 3] > 0][:, :3], axis=0))
    return [f"키 {h}칸 · 머리 {head}칸", f"{h / head:.1f}등신 · {n}색"]


def zoom(a: np.ndarray, z: int) -> Image.Image:
    im = Image.fromarray(a, "RGBA").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST)
    b = Image.new("RGBA", im.size, PANEL + (255,))
    b.alpha_composite(im)
    return b


def raw_crop(p: Path, scale: float = 0.75) -> Image.Image:
    a = load_cutout(p)
    ys, xs = np.where(a[..., 3] > 0)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    b = Image.new("RGBA", (a.shape[1], a.shape[0]), PANEL + (255,))
    b.alpha_composite(Image.fromarray(a, "RGBA"))
    return b.resize((int(b.width * scale), int(b.height * scale)), Image.NEAREST)


def rim(a: np.ndarray) -> np.ndarray:
    """실루엣 바깥 1칸의 테두리 (게임이 그릴 때 더하는 효과의 흉내). 캔버스를 사방 1칸 넓힌다."""
    h, w = a.shape[:2]
    op = np.zeros((h + 2, w + 2), bool)
    op[1:-1, 1:-1] = a[..., 3] > 0
    ring = np.zeros_like(op)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        ring |= np.roll(np.roll(op, dy, 0), dx, 1)
    ring &= ~op
    out = np.zeros((h + 2, w + 2, 4), np.uint8)
    out[ring] = RIM
    out[1:-1, 1:-1][a[..., 3] > 0] = a[a[..., 3] > 0]
    return out


def background(w: int, h: int, press: str) -> tuple[Image.Image, int]:
    src = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGB")
    k = h / 360
    bg = src.resize((int(round(src.width * k)), h), Image.NEAREST).crop((0, 0, w, h))
    keep, dim = PRESS[press]
    if keep < 1:
        g = bg.convert("L").convert("RGB")
        bg = Image.blend(g, bg, keep)
    bg = bg.convert("RGBA")
    floor = int(round(h * 304 / 360))
    bg.alpha_composite(Image.new("RGBA", (w, floor), (10, 12, 24, int(255 * dim))))
    d = ImageDraw.Draw(bg)
    d.rectangle([0, floor, w, h], fill=(18, 19, 28, 255))
    d.line([(0, floor), (w, floor)], fill=(58, 64, 88, 255))
    return bg, floor


def screen(w: int, h: int, press: str, chars: list[tuple[str, str, np.ndarray, bool]]) -> Image.Image:
    """내부 해상도 w×h 의 화면을 1920×1080 으로 정수배 확대. chars = (이름, 작은 글, 그림, 추천인가)."""
    bg, floor = background(w, h, press)
    n = len(chars)
    span = w * 0.86
    pos = []
    for i, (name, sub, a, rec) in enumerate(chars):
        x = int(w * 0.07 + span * i / max(1, n))
        bg.alpha_composite(Image.fromarray(a, "RGBA"), (x, floor - a.shape[0]))
        pos.append((name, sub, x, a.shape[0], a.shape[1], rec))
    z = 1080 // h
    big = bg.resize((w * z, h * z), Image.NEAREST)
    dd = ImageDraw.Draw(big)
    for name, sub, x, ch, cw, rec in pos:
        if rec:
            dd.rectangle([x * z - 10, (floor - ch) * z - 10, (x + cw) * z + 10, floor * z + 4], outline=GOLD, width=4)
            dd.text((x * z - 10, (floor - ch) * z - 40), "추천", font=font(22), fill=GOLD)
        dd.text((x * z, floor * z + 14), name, font=font(22), fill=TXT)
        for i, t in enumerate(sub.split("\n")):
            dd.text((x * z, floor * z + 44 + i * 22), t, font=font(16), fill=SUB)
    return big


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    c_idle = crop_alpha(np.array(Image.open(ROOT / "art/sprites/nx07_states/idle.png").convert("RGBA"))[:, :112])
    s1 = rgba(LAB.parent / "sample_flat/nx07_side_flat.png")
    s2 = rgba(LAB.parent / "sample_dark2/nx07_side_dark2.png")
    va = rgba(LAB / "a_selout/nx07_v1a_master.png")
    vb = rgba(LAB / "b_flat/nx07_v1b_master.png")
    vc = rgba(LAB / "c_flat2/nx07_v1c_master.png")
    va0 = rgba(LAB / "a_selout/nx07_v1a_unfixed.png")
    vb0 = rgba(LAB / "b_flat/nx07_v1b_unfixed.png")

    pad, gap = 36, 26
    Z = 12
    row1 = [
        ("직전 견본 1 · 외곽선 없음", "주포: 앞쪽 팔 (오른팔)", s1, False),
        ("직전 견본 2 · 진한 색 외곽선", "주포: 앞쪽 팔 (오른팔)", s2, False),
        ("v1 후보 A · 제 색의 진한 톤 테두리", "주포: 먼 쪽 팔 (왼팔) · 손본 2칸", va, RECOMMEND == "a"),
        ("v1 후보 B · 외곽선 없음", "주포: 먼 쪽 팔 (왼팔) · 손본 1칸", vb, RECOMMEND == "b"),
        ("v1 후보 C · B 와 같은 프롬프트로 한 번 더", "주포: 먼 쪽 팔 (왼팔) · 손보지 않음", vc, False),
    ]
    guide = raw_crop(ROOT / "art/prompts/pipeline/nx07_side_v1_guide56.png")
    row1b = [
        ("밑그림 (넣은 것)", ["견본 2 마스터에서 몸통을 칸 단위로", "다시 깔았다. 칸 16px, 키 56칸"], guide),
        ("후보 A 뽑힌 그림", ["격자에 맞은 칸 99%"], raw_crop(LAB / "a_selout/nx07_v1a_raw.png")),
        ("후보 B 뽑힌 그림", ["격자에 맞은 칸 100%"], raw_crop(LAB / "b_flat/nx07_v1b_raw.png")),
        ("A 손보기 전 → 후", ["귀 원반 가운데 시안 1칸,", "총구 모서리 1칸"], None),
        ("B 손보기 전 → 후", ["귀 원반 가운데 시안 1칸"], None),
    ]

    # ② ③ 화면
    def sub(a):
        h, head = head_height(a)
        return f"키 {h}칸 · 화면 높이의 1/{270 / h:.1f}"

    scr = [
        ("② 480×270 · 배경 누르기 1단계 (채도 50% · 55% 어둡게)",
         screen(480, 270, "p1", [("견본 1", sub(s1), s1, False), ("견본 2", sub(s2), s2, False),
                                 ("후보 A", sub(va), va, RECOMMEND == "a"), ("후보 B", sub(vb), vb, RECOMMEND == "b")])),
        ("② 480×270 · 배경 누르기 2단계 (채도 25% · 70% 어둡게) + 오른쪽 둘은 게임이 그릴 때 더하는 테두리 빛",
         screen(480, 270, "p2", [("후보 A", sub(va), va, RECOMMEND == "a"), ("후보 B", sub(vb), vb, RECOMMEND == "b"),
                                 ("A + 테두리 빛", "스프라이트에는 없다\n게임이 그릴 때 더한다", rim(va), False),
                                 ("B + 테두리 빛", "스프라이트에는 없다\n게임이 그릴 때 더한다", rim(vb), False)])),
        ("③ 지금 게임 640×360 · 지금 누르기 (40% 어둡게) — C 지금의 도트",
         screen(640, 360, "game", [("C 지금 (스타일 3)", f"키 {head_height(c_idle)[0]}칸 · 화면 높이의 1/{360 / head_height(c_idle)[0]:.1f}", c_idle, False)])),
    ]

    W = max(1920 + 2 * pad, pad + len(row1) * (330 + gap + 30))
    H = 4000 + 3 * (1080 + 110)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), "NX-07 픽셀 마스터 v1 후보 — 주포를 먼 쪽 팔(왼팔)로, 어두운 화면에서 읽히게 (기획서 9.11.2)", font=font(30), fill=(240, 240, 245))
    d.text((pad, 66), "①은 ×12 (nearest). ②③의 화면은 모두 1920×1080 으로 정수배 확대 (480×270 은 ×4, 640×360 은 ×3). "
                      "배경은 높이 360 의 지금 그림을 줄여 대신 썼다 (그 밀도로 그린 배경이 아니다).", font=font(16), fill=SUB)
    d.text((pad, 90), "참고 그림 5장은 넣지 않았다. 오른쪽을 보는 옆모습에서 앞쪽(보는 사람 쪽) 팔 = 캐릭터의 오른팔, 먼 쪽 팔 = 왼팔.", font=font(16), fill=SUB)

    y = 140
    d.text((pad, y), "① 직전 견본과 v1 후보 — 같은 배율 ×12", font=font(24), fill=TXT)
    y += 44
    tallest = max(a.shape[0] for _, _, a, _ in row1) * Z
    base = y + 70 + tallest
    x = pad
    for title, sub1, a, rec in row1:
        im = zoom(a, Z)
        d.text((x, y), title, font=font(20), fill=GOLD if rec else TXT)
        d.text((x, y + 30), sub1, font=font(16), fill=SUB)
        sheet.paste(im.convert("RGB"), (x, base - im.height))
        if rec:
            d.rectangle([x - 8, base - im.height - 8, x + im.width + 8, base + 8], outline=GOLD, width=4)
            d.text((x + im.width + 14, base - im.height - 4), "추천", font=font(22), fill=GOLD)
        for i, t in enumerate(stats(a)):
            d.text((x, base + 14 + i * 24), t, font=font(18), fill=TXT if i == 0 else SUB)
        x += max(im.width, 330) + gap + 30
    y = base + 90

    d.text((pad, y), "밑그림 · 뽑힌 그림 · 손보기", font=font(22), fill=TXT)
    y += 40
    x = pad
    th = max(im.height for _, _, im in row1b if im is not None)
    base = y + 60 + th
    for title, lines, im in row1b:
        d.text((x, y), title, font=font(18), fill=TXT)
        if im is None:
            pair = (va0, va) if title.startswith("A") else (vb0, vb)
            ims = [zoom(pair[0], 8), zoom(pair[1], 8)]
            xx = x
            for k, z in enumerate(ims):
                sheet.paste(z.convert("RGB"), (xx, base - z.height))
                d.text((xx, base - z.height - 24), "전" if k == 0 else "후", font=font(16), fill=SUB)
                xx += z.width + 16
            w_used = xx - x
        else:
            sheet.paste(im.convert("RGB"), (x, base - im.height))
            w_used = im.width
        for i, t in enumerate(lines):
            d.text((x, base + 10 + i * 22), t, font=font(15), fill=SUB)
        x += max(w_used, 260) + gap
    y = base + 80

    for title, im in scr:
        d.text((pad, y), title, font=font(22), fill=GOLD if "②" in title else TXT)
        sheet.paste(im.convert("RGB"), (pad, y + 40))
        y += 40 + im.height + 60
    sheet = sheet.crop((0, 0, W, y))
    out = LAB / "compare.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    main()
