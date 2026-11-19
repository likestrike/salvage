"""스카프 변형 비교 그림 compare.png (기획서 9.11.5). 우리 그림만 들어간다.

    python -X utf8 art/pipeline_lab/pixel_style/v3_scarf/make_scarf.py
    python -X utf8 art/pipeline_lab/pixel_style/v3_scarf/measure_scarf.py
    python -X utf8 art/pipeline_lab/pixel_style/v3_scarf/make_compare_scarf.py

① C36 원본과 변형을 같은 배율(×12)로, 발 기준점을 맞춰 나란히. 그 아래 C36 과 다른 칸의 지도.
② 어두운 게임 화면에 실제 크기로: 320×180 (×6) · 480×270 (×4), 배경 누르기 2단계 (v2 와 같다).
배경은 높이 360 의 지금 그림을 줄여(nearest) 대신 썼다 (그 밀도로 그린 배경이 아니다).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / "v2"))
from make_compare_v2 import BG, GOLD, PANEL, SUB, TXT, font, screen  # noqa: E402

RECOMMEND = "S2"
WHY = "S2 · 목에 감긴 띠와 등 뒤로 늘어진 한 가닥이 함께 있어 목도리로 읽히고, 서 있는 자세와 어울린다. 실루엣은 거의 그대로 (단단함 0.71 → 0.70)."
ORDER = ["C36", "S1", "S2", "S3", "S4"]
NAMES = {
    "C36": ("v2 C36 원본", "기획자가 고른 형태 · 바꾸지 않음"),
    "S1": ("S1 주황 · 감기만", "목에 감긴 띠만"),
    "S2": ("S2 주황 · 한 가닥 늘어짐", "S1 + 등 뒤로 늘어진 끝"),
    "S3": ("S3 주황 · 뒤로 날림", "S1 + 뒤로 흐르는 끝"),
    "S4": ("S4 황토 · 한 가닥 늘어짐", "S2 와 같은 모양, 색만 다르다"),
}


def load(k: str) -> tuple[np.ndarray, int, dict]:
    if k == "C36":
        p = ROOT / "art/pipeline_lab/pixel_style/v2/C36/nx07_v2C36_master.png"
        return np.array(Image.open(p).convert("RGBA")), 0, {}
    info = json.loads((HERE / k / f"nx07_v3{k}_info.json").read_text(encoding="utf-8"))
    a = np.array(Image.open(HERE / k / f"nx07_v3{k}.png").convert("RGBA"))
    return a, info["canvas_pad_left"], info


def zoom(a: np.ndarray, z: int) -> Image.Image:
    im = Image.fromarray(a, "RGBA").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST)
    b = Image.new("RGBA", im.size, PANEL + (255,))
    b.alpha_composite(im)
    return b


def diff_map(a: np.ndarray, pad: int, base: np.ndarray) -> np.ndarray:
    """C36 과 같은 칸은 흐린 회색, 다른 칸(스카프)은 그 색 그대로."""
    h, w = a.shape[:2]
    big = np.zeros_like(a)
    op = a[..., 3] > 0
    same = np.zeros((h, w), bool)
    same[:, pad:] = (a[:, pad:] == base).all(2) & op[:, pad:]
    big[same] = (70, 72, 84, 255)
    big[op & ~same] = a[op & ~same]
    return big


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ms = json.loads((HERE / "measure_scarf.json").read_text(encoding="utf-8"))
    data = {k: load(k) for k in ORDER}
    base = data["C36"][0]
    maxpad = max(p for _, p, _ in data.values())
    pad, gap, Z = 36, 34, 12
    W = 1920 + 2 * pad
    sheet = Image.new("RGB", (W, 5200), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 22), "NX-07 픽셀 마스터 v2 C36 + 스카프 — 변형 넷 (기획서 9.11.5)", font=font(30), fill=(240, 240, 245))
    d.text((pad, 66), "기획자가 정한 것: C36 의 형태 · 밝기 그대로 · 키 36칸 · 큰 덩어리 / 큰 실루엣은 더하지 않음 · 스카프를 더함.  "
                      "스카프의 색과 모양은 [제안]. 실험 · 승인 기록 없음.", font=font(16), fill=SUB)
    d.text((pad, 90), "칸을 직접 찍었다 (이미지 생성 0회). C36 의 칸은 스카프 자리(목 둘레 12칸)만 바뀌고, 나머지 432칸은 한 칸도 같다. "
                      "끝이 몸 뒤로 나가는 것은 캔버스를 왼쪽으로 넓혔다 (발 기준점 그대로).", font=font(16), fill=SUB)

    # ①
    y = 140
    d.text((pad, y), "① 같은 배율 ×12 (nearest) — 발 기준점을 맞춰 나란히", font=font(24), fill=TXT)
    y += 46
    colw = (21 + maxpad) * Z
    tallest = 36 * Z
    top = y + 70
    base_y = top + tallest
    x = pad
    for k in ORDER:
        a, p, info = data[k]
        im = zoom(a, Z)
        rec = k == RECOMMEND
        ox = x + (maxpad - p) * Z
        d.text((x, y), NAMES[k][0], font=font(20), fill=GOLD if rec else TXT)
        d.text((x, y + 30), NAMES[k][1], font=font(16), fill=SUB)
        sheet.paste(im.convert("RGB"), (ox, base_y - im.height))
        if rec:
            d.rectangle([ox - 8, base_y - im.height - 8, ox + im.width + 8, base_y + 8], outline=GOLD, width=4)
        m = ms[k]
        lines = [f"{a.shape[1]}×{a.shape[0]}칸 · {m['colors']}색",
                 "C36 과 같다" if k == "C36" else
                 f"C36 과 다른 칸 {info['diff_vs_c36']['cells_changed_total']} (덮음 {info['diff_vs_c36']['cells_replaced']} · 더함 {info['diff_vs_c36']['cells_added']})",
                 f"채도 높은 칸 {m['accent_pct']}% · 평균 밝기 {m['L_mean']}",
                 f"얼굴 둘레와의 밝기 차 {m['face']['contrast']}",
                 f"가장 큰 밝기 덩어리 {m['largest_value_mass_pct']}%"]
        for i, t in enumerate(lines):
            d.text((x, base_y + 16 + i * 24), t, font=font(16), fill=TXT if i == 1 else SUB)
        x += colw + gap
    y = base_y + 16 + 5 * 24 + 30

    # C36 과 다른 칸
    d.text((pad, y), "C36 과 다른 칸 — 회색은 C36 과 같은 칸, 색이 있는 칸이 바뀌거나 더해진 칸 (×6)", font=font(20), fill=TXT)
    y += 36
    x = pad
    Z2 = 6
    for k in ORDER:
        a, p, _ = data[k]
        im = zoom(diff_map(a, p, base) if k != "C36" else diff_map(base, 0, base), Z2)
        sheet.paste(im.convert("RGB"), (x + (maxpad - p) * Z2, y))
        x += colw + gap
    y += 36 * Z2 + 50

    # 고른 것
    d.text((pad, y), "가장 낫다고 본 것: " + WHY, font=font(20), fill=GOLD)
    y += 34
    d.text((pad, y), "S1 은 목 보호대 · 깃처럼도 읽힌다. S3 은 서 있는데 바람에 날리는 그림이라 대기 자세에는 어색하고, 끝이 평평한 띠처럼 보인다. "
                      "S4(황토)는 뒤 빛의 크림색 · 올리브와 색상이 가까워 덜 튄다.", font=font(16), fill=SUB)
    y += 24
    d.text((pad, y), "색의 역할 (기획서 9.2): 시안 = NX-07 의 빛 · 청록 = ARTEMIS · 레드 = 적의 센서와 경고 · 주황 = 폭발과 불. "
                      "주황은 NOVA 시안의 스카프 색이지만 폭발 · 불과 겹친다. 붉은색은 적의 색이라 견주지 않았다.", font=font(16), fill=SUB)
    y += 60

    # ②
    chars = [(k, crop_alpha(data[k][0]), k == RECOMMEND) for k in ORDER]
    scr = [
        ("② 320×180 (×6) · 배경 누르기 2단계 (채도 25% · 70% 어둡게) — 36칸이 화면 높이의 1/5", screen(320, 180, "p2", chars)),
        ("② 480×270 (×4) · 배경 누르기 2단계 — 36칸이 화면 높이의 1/7.5", screen(480, 270, "p2", chars)),
    ]
    for title, im in scr:
        d.text((pad, y), title, font=font(22), fill=TXT)
        sheet.paste(im.convert("RGB"), (pad, y + 40))
        y += 40 + im.height + 90
    sheet = sheet.crop((0, 0, W, y))
    out = HERE / "compare.png"
    sheet.save(out)
    print(out, sheet.size)


def crop_alpha(a: np.ndarray) -> np.ndarray:
    ys, xs = np.where(a[..., 3] > 0)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


if __name__ == "__main__":
    main()
