"""NX-07 픽셀 마스터 v2 C36 에 스카프를 더한 변형 (기획서 9.11.5). 이미지 생성 0회, 칸을 직접 찍었다.

    python -X utf8 art/pipeline_lab/pixel_style/v3_scarf/make_scarf.py

기획자가 정한 것: 기준은 v2 C36 의 형태 · 밝기 그대로 · 키 36칸 · 큰 덩어리나 큰 실루엣은 더하지 않음 · 스카프를 더함.
스카프의 색과 모양은 [제안] 이다. 변형마다 축 하나만 바꾼다 (S1~S3 = 모양, S2 와 S4 = 색).

규칙
- C36 의 칸은 스카프 표에 적힌 칸만 바뀐다. 나머지는 한 칸도 바뀌지 않는다 (아래 check 가 확인하고, 어긋나면 멈춘다).
- 스카프 끝이 C36 캔버스 뒤쪽(왼쪽, 캐릭터는 오른쪽을 본다) 밖으로 나가면 캔버스를 왼쪽으로 넓힌다. 발 기준점은 캐릭터에 대해 그대로다 (넓힌 만큼 x 만 더한다).
- 그리는 방식은 C36 과 같다: 검은 외곽선 없음, 세 톤(H 밝음 · M 가운데 · S 그늘). 빛이 뒤-위에서 오므로 위쪽 · 뒤쪽 가장자리가 H.
- 얼굴(살색) 칸 · 눈 칸 · 엠블럼 칸은 표에 넣지 않는다 (check 가 확인한다).

표: (y, x0, "글자들") — 글자 하나가 칸 하나. x 는 C36 원래 좌표 (음수 = 원래 캔버스의 왼쪽 밖). '.' 은 바꾸지 않는다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from pixel_master import head_height, orphan_ratio  # noqa: E402

SRC = ROOT / "art/pipeline_lab/pixel_style/v2/C36/nx07_v2C36_master.png"

# 색 [제안]. 주황 = NOVA 시안의 스카프 쪽 (기획서 9.2 에서 주황은 폭발과 불의 색이기도 하다).
# 황토 = 다른 색 하나. 9.2 의 역할(시안 · 청록 · 레드 · 주황)과 겹치지 않는다. 레드는 적의 센서와 경고라서 쓰지 않았다.
COLORS = {
    "orange": {"label": "주황", "H": "e88a46", "M": "c25a26", "S": "7e3518"},
    "ochre": {"label": "황토", "H": "e2bc5c", "M": "b48a30", "S": "6e5220"},
}

# 목에 감긴 부분 (모든 변형이 같다). 턱 아래 (10,10)(11,10) 살색과 (9,10) 헬멧 볼은 그대로 둔다.
WRAP = [
    (10, 6, "HHM"),
    (11, 5, "HMMMSS"),
    (12, 7, "SSS"),
]

# 뒤로 한 가닥이 늘어진 것: 목 뒤에서 어깨 위를 지나 등 뒤로 떨어진다. 등(x=2)에 붙지 않고 1칸 떨어져 늘어진다.
HANG = [
    (10, 2, "HHHM"),
    (11, 0, "HHM"),
    (12, -1, "HM"),
    (13, -1, "HS"),
    (14, -1, "MS"),
    (15, -1, "MS"),
    (16, -1, "S"),
]

# 뒤로 날리는 것: 목 뒤에서 두 칸 두께로 뒤로 흐르며 한 번 솟았다 내려온다 (물결 하나). 끝은 가늘어진다.
FLY = [
    (9, -4, "HHHH"),
    (10, -6, "HHMMMMHHHHHM"),
    (11, -7, "SMS....MMS"),
]

SHAPES = {
    "wrap": {"label": "감기만", "cells": WRAP},
    "hang": {"label": "한 가닥 늘어짐", "cells": WRAP + HANG},
    "fly": {"label": "뒤로 날림", "cells": WRAP + FLY},
}

VARIANTS = [
    ("S1", "orange", "wrap"),
    ("S2", "orange", "hang"),
    ("S3", "orange", "fly"),
    ("S4", "ochre", "hang"),
]

FACE = [(10, 8), (10, 9), (11, 9), (12, 9), (10, 10), (11, 10), (11, 8)]  # 살색 6칸 + 눈 1칸 (x, y)
EMBLEM = [(13, 4), (14, 4)]


def hexrgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def table(cells) -> dict[tuple[int, int], str]:
    out = {}
    for y, x0, s in cells:
        for i, ch in enumerate(s):
            if ch == ".":
                continue
            out[(x0 + i, y)] = ch  # 뒤에 적힌 것이 이긴다
    return out


def build(color: str, shape: str, base: np.ndarray):
    t = table(SHAPES[shape]["cells"])
    for k in FACE + EMBLEM:
        assert k not in t, f"얼굴 · 엠블럼 칸을 덮는다: {k}"
    minx = min(x for x, _ in t)
    pad = max(0, -minx)
    h, w = base.shape[:2]
    out = np.zeros((h, w + pad, 4), np.uint8)
    out[:, pad:] = base
    pal = COLORS[color]
    for (x, y), ch in t.items():
        out[y, x + pad] = hexrgb(pal[ch]) + (255,)
    return out, pad, t


def check(base: np.ndarray, out: np.ndarray, pad: int, t: dict) -> dict:
    h, w = base.shape[:2]
    inner = out[:, pad:]
    diff = (inner != base).any(2)
    allowed = np.zeros((h, w), bool)
    for (x, y) in t:
        if 0 <= x < w:
            allowed[y, x] = True
    stray = diff & ~allowed
    assert not stray.any(), f"스카프 표 밖의 칸이 바뀌었다: {np.argwhere(stray)}"
    # 넓힌 쪽에 스카프 아닌 것이 없는가
    outside = out[:, :pad, 3] > 0
    n_out = int(outside.sum())
    assert n_out == sum(1 for (x, _) in t if x < 0)
    op0 = base[..., 3] > 0
    replaced = int((diff & op0).sum())            # C36 의 칸 가운데 스카프로 덮인 것
    added_in = int((diff & ~op0).sum())           # 원래 캔버스 안의 빈 칸에 더한 것
    untouched = int((~diff & op0).sum())
    return {"cells_replaced": replaced, "cells_added": added_in + n_out, "cells_changed_total": replaced + added_in + n_out,
            "c36_cells": int(op0.sum()), "c36_cells_unchanged": untouched,
            "other_cells_changed": int(stray.sum())}


def palette(a: np.ndarray) -> list[str]:
    op = a[..., 3] > 0
    cols = np.unique(a[op][:, :3], axis=0)
    lum = cols @ np.array([0.2126, 0.7152, 0.0722])
    return ["%02x%02x%02x" % tuple(int(v) for v in c) for c in cols[np.argsort(lum)]]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    base = np.array(Image.open(SRC).convert("RGBA"))
    assert set(np.unique(base[..., 3])) <= {0, 255}
    ys, xs = np.where(base[..., 3] > 0)
    sole = int(ys.max()) + 1
    front = xs[ys == ys.max()]
    front = front[front >= 10]  # 앞발 (오른쪽 부츠)
    anchor0 = [round(float(front.min() + front.max() + 1) / 2, 1), sole]
    summary = []
    for name, color, shape in VARIANTS:
        out, pad, t = build(color, shape, base)
        chk = check(base, out, pad, t)
        assert set(np.unique(out[..., 3])) <= {0, 255}
        pal = palette(out)
        stem = f"nx07_v3{name}"
        d = HERE / name
        d.mkdir(exist_ok=True)
        Image.fromarray(out, "RGBA").save(d / f"{stem}.png")
        Image.fromarray(out, "RGBA").resize((out.shape[1] * 12, out.shape[0] * 12), Image.NEAREST).save(d / f"{stem}_x12.png")
        (d / f"{stem}_palette.hex").write_text("\n".join(pal) + "\n", encoding="utf-8")
        gpl = ["GIMP Palette", f"Name: {stem}", "Columns: 8", "#"]
        gpl += ["%3d %3d %3d\t%s" % (*hexrgb(p), p) for p in pal]
        (d / f"{stem}_palette.gpl").write_text("\n".join(gpl) + "\n", encoding="utf-8")
        title = f"{name} {COLORS[color]['label']} · {SHAPES[shape]['label']}"
        # 머리는 C36 과 같은 칸이다. 자동 측정(head_height)은 스카프 끝이 목 줄의 너비를 바꿔 목을 잘못 잡으므로 C36 에서 잰 값을 쓴다.
        hh, hd = head_height(base)
        mets = {"size": [int(out.shape[1]), int(out.shape[0])], "height": hh, "head": hd, "heads_tall": round(hh / hd, 1),
                "head_note": "C36 에서 잰 값 (머리 칸은 같다)",
                "colors": len(pal), "semi_transparent": 0, "off_palette": 0, "orphan_pct": round(100 * orphan_ratio(out), 1)}
        info = {
            "master": {"name": "c36_plus_scarf", "cell": None, "metrics": mets, "spread": None},
            "picked": "c36_plus_scarf", "recommended": None,
            "name": title, "base": "art/pipeline_lab/pixel_style/v2/C36/nx07_v2C36_master.png",
            "method": "칸을 직접 찍었다 (make_scarf.py 의 표). 이미지 생성 0회",
            "size": [int(out.shape[1]), int(out.shape[0])], "height": 36,
            "canvas_pad_left": pad,
            "foot_anchor": {"c36": anchor0, "here": [anchor0[0] + pad, sole],
                            "note": "앞발(오른쪽 부츠) 바닥의 가운데 x, 발바닥 줄 y (칸 경계). 넓힌 만큼 x 만 더했다"},
            "colors": len(pal), "c36_colors": 15, "scarf_colors": {k: "#" + COLORS[color][k] for k in "HMS"},
            "semi_transparent": int(((out[..., 3] > 0) & (out[..., 3] < 255)).sum()),
            "off_palette": 0,
            "diff_vs_c36": chk,
            "scarf_mark": "[제안] 색 · 모양. 실험 · 승인 기록 없음",
            "doc": "docs/GAME_DESIGN.md 9.11.5",
        }
        (d / f"{stem}_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        summary.append((title, out.shape[1], chk, len(pal)))
        print(title, f"폭 {out.shape[1]} (넓힘 {pad})", chk, f"색 {len(pal)}")


if __name__ == "__main__":
    main()
