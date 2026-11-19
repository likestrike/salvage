"""미리네 픽셀 마스터 후보 — 기획자가 고르는 비교 그림 한 장 (우리 그림만).

    python -X utf8 art/characters/mirine/pixel/work/make_board.py [--pick B30]

① 후보들을 같은 배율로 나란히 (밝기 계획 한 줄 · 잰 값)
② 승인된 NX-07 (스카프 있음)과 후보를 같은 칸 크기 · 같은 발바닥 줄로
③ 어두운 게임 화면 320×180 ×3 에 NX-07 과 후보들
④ 설정화 측면 (참고, 작게)
입력: pipeline.json · work/measure.json · 후보 마스터 · nx07_px_scarf.png. 출력: work/board.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "tools"))
import pixpipe as pp  # noqa: E402

FONT_B, FONT = "C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"
BG, PANEL = (18, 20, 28), (34, 37, 50)
TXT, SUB, GOLD, GREEN = (236, 236, 242), (160, 166, 184), (240, 196, 80), (120, 220, 140)


def f(n, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT, n)


def load(p):
    a = np.array(Image.open(p).convert("RGBA"))
    ys, xs = np.where(a[..., 3] > 0)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def big(a, z):
    return Image.fromarray(a, "RGBA").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST)


def screen(figs, size=(320, 180), z=3, gap=14):
    """지금 게임의 배경을 화면 높이로 줄이고 누른 것 (pixpipe.dark_screen 과 같은 누르기) 위에 여럿을 세운다."""
    w, h = size
    src = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGB")
    k = h / src.height
    bg = src.resize((int(round(src.width * k)), h), Image.NEAREST).crop((0, 0, w, h))
    bg = Image.blend(bg.convert("L").convert("RGB"), bg, 0.25).convert("RGBA")
    floor = int(round(h * 304 / 360))
    bg.alpha_composite(Image.new("RGBA", (w, floor), (10, 12, 24, int(255 * 0.70))))
    ImageDraw.Draw(bg).rectangle([0, floor, w, h], fill=(18, 19, 28, 255))
    tot = sum(a.shape[1] for _, a in figs) + gap * (len(figs) - 1)
    x = (w - tot) // 2
    pos = []
    for name, a in figs:
        bg.alpha_composite(Image.fromarray(a, "RGBA"), (x, floor - a.shape[0]))
        pos.append((name, x, a.shape[1], floor - a.shape[0]))
        x += a.shape[1] + gap
    return bg.convert("RGB").resize((w * z, h * z), Image.NEAREST), pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick", help="에이전트가 가장 낫다고 보는 후보")
    ap.add_argument("--notes", help="후보마다의 눈으로 본 판단 JSON 파일 {job: [줄, …]}")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    x = pp.Ctx("mirine")
    jobs = [j for j in x.jobs() if x.master(j).exists()]
    meas = pp.read_json(x.work / "measure.json")["items"]
    notes = json.loads(Path(args.notes).read_text(encoding="utf-8")) if args.notes else {}
    nx = load(ROOT / "art/characters/nx07/pixel/nx07_px_scarf.png")
    ms = {j: load(x.master(j)) for j in jobs}

    W = 2000
    img = Image.new("RGB", (W, 4200), BG)
    d = ImageDraw.Draw(img)
    d.text((40, 24), "미리네 픽셀 마스터 후보 — 고르기 위한 비교 그림", font=f(34), fill=TXT)
    d.text((40, 74), "모두 [제안]이다 (디자인 시안 A · 키 30칸 · 단순화안 · 밝기 계획). 우리 그림만. "
                     "확대는 모두 nearest. 고르는 것은 기획자다.", font=f(18, False), fill=SUB)
    y = 130

    # ① 후보들
    Z = 12
    d.text((40, y), "① 후보 — 같은 배율 ×12", font=f(24), fill=GOLD)
    y += 44
    maxh = max(m.shape[0] for m in ms.values())
    xx = 40
    colw = 600
    for j in jobs:
        m = ms[j]
        J = x.jobs()[j]
        pl = x.plans()[J["plan"]]
        panel = Image.new("RGB", (colw - 30, maxh * Z + 24), PANEL)
        im = big(m, Z)
        panel.paste(im, ((panel.width - im.width) // 2, panel.height - 12 - im.height), im)
        img.paste(panel, (xx, y))
        if j == args.pick:
            d.rectangle([xx - 6, y - 6, xx + panel.width + 5, y + panel.height + 5], outline=GREEN, width=5)
            d.text((xx + 12, y + 10), "에이전트 추천", font=f(22), fill=GREEN)
        ty = y + panel.height + 12
        d.text((xx, ty), f"{j} — {pl['label']}", font=f(20), fill=GOLD)
        it = meas.get(j, {})
        fm, pc = it.get("format", {}), it.get("picture", {})
        lines = [
            f"{m.shape[1]}×{m.shape[0]}칸 · {fm.get('colors')}색 · 격자 {round(100 * (fm.get('grid_good') or 0))}% · 반투명 {fm.get('semi_transparent')} · 팔레트 이탈 {fm.get('off_palette')}",
            f"가장 큰 밝기 덩어리 {pc.get('largest_value_mass_pct')}% · 위 3개 {pc.get('value_top3_pct')}%",
            f"채도 높은 칸 {pc.get('accent_pct')}% · 평균 밝기 L* {pc.get('L_mean')} · 외톨이 {fm.get('orphan_pct')}%",
            f"얼굴 살색 {pc.get('face_skin_cells')}칸 · 얼굴 대비 {pc.get('face_contrast')}",
        ]
        for i, t in enumerate(lines):
            d.text((xx, ty + 32 + i * 26), t, font=f(16, False), fill=TXT if i == 0 else SUB)
        for i, t in enumerate(notes.get(j, [])):
            d.text((xx, ty + 32 + (len(lines) + i) * 26 + 6), t, font=f(16, False), fill=(220, 200, 160))
        xx += colw
    y += maxh * Z + 24 + 12 + 32 + 26 * (4 + max((len(v) for v in notes.values()), default=0)) + 40

    # ② NX-07 과 나란히
    Z2 = 10
    d.text((40, y), "② 승인된 NX-07 (스카프 있음, 36칸)과 같은 칸 크기 · 같은 발바닥 줄 ×10 — 키의 비율 36 : 30 (설정 170 : 142cm)", font=f(24), fill=GOLD)
    y += 44
    figs = [("NX-07", nx)] + [(j, ms[j]) for j in jobs]
    hmax = max(a.shape[0] for _, a in figs)
    pw = sum(a.shape[1] * Z2 + 60 for _, a in figs) + 60
    panel = Image.new("RGB", (pw, hmax * Z2 + 70), PANEL)
    pd = ImageDraw.Draw(panel)
    floor = 30 + hmax * Z2
    px = 50
    for name, a in figs:
        im = big(a, Z2)
        panel.paste(im, (px, floor - im.height), im)
        pd.text((px, floor + 8), f"{name} {a.shape[0]}칸", font=f(18), fill=TXT)
        px += im.width + 60
    # 머리 높이를 견줄 수 있게 NX-07 정수리 줄
    pd.line([(30, floor - nx.shape[0] * Z2), (pw - 30, floor - nx.shape[0] * Z2)], fill=(90, 96, 120), width=1)
    pd.line([(30, floor), (pw - 30, floor)], fill=(200, 90, 80), width=2)
    img.paste(panel, (40, y))
    y += panel.height + 30

    # ③ 어두운 게임 화면
    d.text((40, y), "③ 어두운 게임 화면 320×180 ×3 (지금 게임의 배경을 줄이고 누른 것) — 실제 크기", font=f(24), fill=GOLD)
    y += 44
    sc, pos = screen(figs)
    img.paste(sc, (40, y))
    for name, px0, w0, top in pos:
        d.text((40 + px0 * 3, y + top * 3 - 26), name, font=f(16), fill=TXT)
    side = Image.open(ROOT / "art/concept/setting/mirine/02_side.png").convert("RGB")
    th = 420
    side = side.resize((int(side.width * th / side.height), th), Image.LANCZOS)
    sx = 40 + sc.width + 40
    img.paste(side, (sx, y))
    d.text((sx, y + th + 8), "④ 설정화 측면 (참고)", font=f(18), fill=SUB)
    y += max(sc.height, th + 40) + 30

    out = Path(args.out) if args.out else x.work / "board.png"
    img.crop((0, 0, W, y)).save(out)
    print("[board]", out)


if __name__ == "__main__":
    main()
