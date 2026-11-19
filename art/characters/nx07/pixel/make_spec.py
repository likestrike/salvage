"""NX-07 픽셀 마스터 규격 (기획서 9.11.6). 그림에서 재서 nx07_px_spec.json 과 규격 그림 nx07_px_spec.png 를 쓴다.

    python -X utf8 art/characters/nx07/pixel/make_spec.py

재는 것: 캔버스 · 키 · 머리/몸통/다리의 줄 · 색마다의 칸 수와 놓인 부위 · 스카프 층(덮는 칸 · 더하는 칸).
사람이 정한 것(색의 쓰임 이름 · 불변 부위 제안)은 아래 USE · 문서의 표기를 따른다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE / "nx07_px_base.png"
SCARF = HERE / "nx07_px_scarf.png"
RIG = HERE.parent / "anim" / "rig.json"
PAD = 1  # 스카프 마스터는 왼쪽으로 1칸 넓다

# 색의 쓰임 (에이전트가 그림을 보고 붙인 이름. 칸 수와 부위는 아래에서 잰다)
USE = {
    "1f201c": ("k", "가장 어두운 색", "틈 · 그늘 · 발바닥 · 앞쪽 팔의 가장자리"),
    "262921": ("", "헬멧 뒤 그늘 (1칸)", "단독 색"),
    "2f3131": ("s", "슈트", "몸통 · 넓적다리 · 위팔"),
    "333926": ("d", "어두운 올리브", "장갑의 그늘 면"),
    "3f3f3d": ("g", "주먹 회색", "앞쪽 팔의 주먹"),
    "3d422b": ("", "안테나 끝 (1칸)", "단독 색"),
    "545837": ("o", "올리브", "헬멧 · 장갑의 기본 면"),
    "0d7172": ("", "눈", "짙은 청록 1칸"),
    "626640": ("l", "밝은 올리브", "가슴 장갑의 밝은 면"),
    "b7a897": ("", "주포 고리의 그늘", "주포 팔"),
    "cdbeaa": ("w", "흰 장갑", "앞쪽 팔뚝 · 넓적다리 판"),
    "01f9fe": ("c", "시안", "이마 엠블럼 · 주포의 빛 띠 · 총구"),
    "d1c8a5": ("r", "뒤 빛 (크림)", "뒤 · 위 가장자리의 1칸 획"),
    "e5d9c4": ("", "주포 고리의 빛", "주포 팔"),
    "fde1c4": ("", "얼굴", "살색 6칸"),
    "e88a46": ("H", "스카프 밝음", "스카프 층"),
    "c25a26": ("M", "스카프 가운데", "스카프 층"),
    "7e3518": ("S", "스카프 그늘", "스카프 층"),
}
MATERIALS = [
    ("헬멧 · 장갑 (올리브)", ["333926", "545837", "626640"], "3톤 + 뒤 빛(d1c8a5)"),
    ("슈트", ["1f201c", "2f3131"], "2톤"),
    ("흰 장갑", ["cdbeaa"], "1톤 (뒤 빛과 맞닿음)"),
    ("주먹", ["3f3f3d", "1f201c"], "2톤"),
    ("얼굴", ["fde1c4"], "1톤 + 눈 1칸(0d7172)"),
    ("시안 빛", ["01f9fe"], "1톤. 엠블럼 · 주포만"),
    ("주포 고리", ["e5d9c4", "b7a897"], "2톤"),
    ("스카프 (층)", ["e88a46", "c25a26", "7e3518"], "3톤. 위 · 뒤가 밝다"),
]
BANDS = {"head": (0, 10), "torso": (11, 24), "legs": (25, 35)}
BAND_LABEL = {"head": "머리", "torso": "몸통 · 팔", "legs": "다리"}
PART_COL = {"head": (255, 92, 92), "upper": (120, 200, 120), "near_arm": (255, 210, 80), "legs": (110, 130, 255),
            "scarf_wrap": (255, 150, 60), "scarf_tail": (255, 110, 200)}


def hx(c) -> str:
    return "%02x%02x%02x" % tuple(int(v) for v in c[:3])


def font(n: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf", n)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    b = np.array(Image.open(BASE).convert("RGBA"))
    s = np.array(Image.open(SCARF).convert("RGBA"))
    rig = json.loads(RIG.read_text(encoding="utf-8"))
    h, w = b.shape[:2]
    op = b[..., 3] > 0
    ys, xs = np.where(op)
    top, sole = int(ys.min()), int(ys.max()) + 1
    # 부위 (rig.json 과 같은 나눔)
    x0, y0, x1, y1 = rig["parts"]["near_arm"]["rect"]
    part = np.full((h, w), "", object)
    for y in range(h):
        for x in range(w):
            if not op[y, x]:
                continue
            if x0 <= x <= x1 and y0 <= y <= y1:
                part[y, x] = "near_arm"
            elif y <= 10:
                part[y, x] = "head"
            elif y <= 24:
                part[y, x] = "upper"
            else:
                part[y, x] = "legs"
    counts = {k: int((part == k).sum()) for k in ("head", "upper", "near_arm", "legs")}
    # 스카프 층: S2 와 C36 의 차이
    inner = s[:, PAD:]
    diff = (inner != b).any(-1)
    covers = [[int(x), int(y)] for y, x in zip(*np.where(diff & op))]
    adds_in = [[int(x), int(y)] for y, x in zip(*np.where(diff & ~op))]
    adds_out = [[int(x) - PAD, int(y)] for y, x in zip(*np.where(s[:, :PAD, 3] > 0))]
    wrap = set()
    for yy, xx, st in rig["scarf"]["wrap"]:
        for i, ch in enumerate(st):
            if ch != ".":
                wrap.add((xx + i, yy))
    # 팔레트
    pal = []
    for a, name in ((b, "base"), (s, "scarf")):
        pass
    cols_b = {hx(c) for c in b[op]}
    ops = s[..., 3] > 0
    cols_s = {hx(c) for c in s[ops]}
    for c in sorted(cols_s, key=lambda c: sum(int(c[i:i + 2], 16) * k for i, k in ((0, .2126), (2, .7152), (4, .0722)))):
        key, name, use = USE.get(c, ("", "?", ""))
        nb = int(((b[..., :3] == np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)])).all(-1) & op).sum())
        ns = int(((s[..., :3] == np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)])).all(-1) & ops).sum())
        where = sorted({BAND_LABEL[k] for k, (a0, a1) in BANDS.items()
                        for yy, xx in zip(*np.where((b[..., :3] == np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)])).all(-1) & op))
                        if a0 <= yy <= a1})
        pal.append({"hex": "#" + c, "key": key, "name": name, "use": use, "cells_base": nb, "cells_scarf": ns,
                    "in_base": c in cols_b, "rows": where or (["스카프 층"] if c not in cols_b else [])})
    head_rows = None
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from pixel_master import head_height
        hh, hd = head_height(b)
        head_rows = {"height": hh, "head": hd, "heads_tall": round(hh / hd, 1)}
    except Exception as e:  # noqa: BLE001
        head_rows = {"error": str(e)}
    spec = {
        "format": "salvage-pixel-spec/1",
        "character": "nx07",
        "doc": "docs/GAME_DESIGN.md 9.11.6",
        "_": "NX-07 을 픽셀로 그릴 때 지키는 규칙. 숫자는 make_spec.py 가 마스터에서 잰 값이다. 'proposal' 이 붙은 것은 [제안].",
        "masters": {
            "base": {"file": "art/characters/nx07/pixel/nx07_px_base.png", "from": "art/pipeline_lab/pixel_style/v2/C36/nx07_v2C36_master.png",
                     "label": "스카프 없음 (저항군 합류 전)", "size": [w, h], "colors": len(cols_b)},
            "scarf": {"file": "art/characters/nx07/pixel/nx07_px_scarf.png", "from": "art/pipeline_lab/pixel_style/v3_scarf/S2/nx07_v3S2.png",
                      "label": "스카프 있음 (저항군 합류 뒤)", "size": [int(s.shape[1]), int(s.shape[0])], "colors": len(cols_s),
                      "pad_left": PAD, "note": "base 위에 스카프 층을 얹은 것. 층을 빼면 base 와 한 칸도 다르지 않다"},
            "approved": "2026-11-19 기획자 (character.json 의 approvals)",
        },
        "canvas": {"master_base": [w, h], "master_scarf": [int(s.shape[1]), int(s.shape[0])],
                   "anim": rig["canvas"], "anim_place": rig["place"], "anim_anchor": rig["anchor"],
                   "anchor_note": rig["anchor_note"],
                   "master_front_foot": {"x": 14.0, "sole": sole, "note": "앞발(오른쪽 부츠) 바닥의 가운데 · 발바닥 줄 (C36 좌표, 9.11.5)"}},
        "height": {"cells": sole - top, "top_row": top, "sole_row": sole,
                   "bands": {BAND_LABEL[k]: {"rows": list(v), "cells_tall": v[1] - v[0] + 1} for k, v in BANDS.items()},
                   "measured_head": head_rows,
                   "note": "머리 줄(0~10)은 턱 줄까지다. 도구(pixel_master.head_height)가 잰 정수리 ~ 목은 10칸, 3.6등신"},
        "parts_cells": counts,
        "facing": "right",
        "cannon_arm": "먼 쪽 팔 (캐릭터의 왼팔). 앞쪽 팔(오른팔)은 흰 팔뚝 · 회색 주먹 (기획자 결정, 9.11.2)",
        "outline": "검은 외곽선 없음. 실루엣은 색과 밝기로 읽힌다 (9.11.2)",
        "light": "뒤-위에서 온다. 뒤쪽 · 위쪽 가장자리에 1칸 두께의 크림색 획(d1c8a5). 닫힌 테두리가 아니다 (9.11.4 의 C 안)",
        "brightness": "어두운 몸이 주인 (평균 밝기 L* 32, 가장 큰 밝기 덩어리 37%, 채도 높은 칸 1.8% — 9.11.4 C36). 밝기는 그대로 (기획자, 9.11.5)",
        "palette": pal,
        "palette_rule": "새 색을 만들지 않는다. 스카프 없음 = 위 표에서 in_base 인 15색, 스카프 있음 = 18색",
        "materials": [{"name": n, "colors": ["#" + c for c in cs], "tones": t} for n, cs, t in MATERIALS],
        "simplified": [
            "귀 장치는 헬멧의 어두운 톤 동그라미로 눌렀다 (흰 원반 · 시안 점 없음). 얼굴만 밝다 (9.11.4)",
            "작은 흰 판 · 작은 시안 점은 빼거나 합쳤다. 시안은 엠블럼 · 주포의 빛 띠 · 총구뿐이고 눈은 짙은 청록이다",
            "올리브는 설정화의 올리브 드랩(#6F7457) 쪽과 그보다 어두운 쪽으로 돌렸다",
            "주먹은 회색 덩어리라 손가락은 그리지 않는다",
        ],
        "scarf_layer": {
            "colors": ["#e88a46", "#c25a26", "#7e3518"],
            "wrap_cells": sorted([list(c) for c in wrap]),
            "covers_base_cells": covers,
            "adds_cells": adds_in + adds_out,
            "counts": {"covers": len(covers), "adds": len(adds_in) + len(adds_out)},
            "rule": "목에 감긴 부분(wrap, 12칸)은 늘 같다. 끝(tail)은 동작마다 rig.json 의 표에서 고른다. 얼굴 · 눈 · 엠블럼 칸은 덮지 않는다. 몸통과 함께 움직인다",
            "story": "스카프는 저항군에 합류한 뒤에 두른다 (기획자, 2026-11-19). STORY.md 4장",
        },
        "invariant_proposal": {
            "_": "[제안] 프레임이 바뀌어도 칸 단위로 옮기기만 하고 한 칸도 바꾸지 않는 부분",
            "fixed": [
                {"part": "머리 (0~10줄)", "cells": counts["head"], "rule": "모든 프레임에서 마스터와 같다. 다른 층에 가려도 안 된다"},
                {"part": "몸통 · 등짐 · 골반 · 주포 팔 (11~24줄, 앞쪽 팔 제외)", "cells": counts["upper"],
                 "rule": "마스터와 같다. 앞쪽 팔 · 다리가 앞에서 가리는 칸만 허용하고 몇 칸인지 적는다"},
                {"part": "스카프의 목에 감긴 부분", "cells": len(wrap), "rule": "스카프 있음 프레임에서 S2 와 같다"},
            ],
            "free": [
                {"part": "다리 (25~35줄)", "cells": counts["legs"], "rule": "프레임마다 새로 찍는다. 색은 마스터의 다리 색, 먼 쪽 다리는 한 톤 어둡게"},
                {"part": "앞쪽 팔 (16~24줄, x 0~4)", "cells": counts["near_arm"], "rule": "자세 표(뒤 · 아래 · 앞)에서 고른다. 팔이 비운 몸통 뒤 가장자리는 슈트 색으로 채운다"},
                {"part": "스카프 끝", "rule": "동작마다 표에서 고른다"},
            ],
            "limit": "공격 · 피격처럼 몸통이 돌아가거나 주포를 드는 동작에서는 몸통 · 주포 팔의 불변을 풀어야 한다 (이번 범위 밖)",
        },
        "measured_by": "art/characters/nx07/pixel/make_spec.py",
    }
    (HERE / "nx07_px_spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    draw(b, s, part, wrap, pal, spec, counts)
    print("규격:", rel(HERE / "nx07_px_spec.json"), "·", rel(HERE / "nx07_px_spec.png"), "· 부위 칸", counts,
          "· 스카프 덮음", len(covers), "더함", len(adds_in) + len(adds_out))


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT.resolve()).as_posix()


def draw(b, s, part, wrap, pal, spec, counts) -> None:
    Z = 16
    h, w = b.shape[:2]
    W, H = 1900, 1290
    BG = (20, 22, 30)
    TXT, SUB, GOLD = (236, 236, 242), (160, 166, 184), (240, 196, 80)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((32, 20), "NX-07 픽셀 마스터 규격 — 승인 2026-11-19 (기획서 9.11.6)", font=font(30), fill=TXT)
    d.text((32, 64), "스카프 없음 = v2 C36 (저항군 합류 전) · 스카프 있음 = v3 S2 (합류 뒤). 스카프는 몸 위에 얹는 층이다. 숫자는 make_spec.py 가 그림에서 잰 값.",
           font=font(17, False), fill=SUB)
    y0 = 120

    def panel(a, x, title, pad=0):
        hh, ww = a.shape[:2]
        cell = Image.new("RGBA", (ww * Z, hh * Z), (34, 37, 50, 255))
        cell.alpha_composite(Image.fromarray(a, "RGBA").resize((ww * Z, hh * Z), Image.NEAREST))
        img.paste(cell.convert("RGB"), (x, y0 + 30))
        d.text((x, y0), title, font=font(19), fill=TXT)
        return x + ww * Z

    # ① 스카프 없음 + 줄 띠
    x = 90
    right = panel(b, x, "스카프 없음 (C36)")
    for k, (a0, a1) in BANDS.items():
        yy0, yy1 = y0 + 30 + a0 * Z, y0 + 30 + (a1 + 1) * Z
        d.line([(x - 14, yy0 + 2), (x - 14, yy1 - 2)], fill=GOLD, width=3)
        d.text((x - 80, (yy0 + yy1) // 2 - 22), BAND_LABEL[k], font=font(16), fill=GOLD)
        d.text((x - 80, (yy0 + yy1) // 2), f"{a1 - a0 + 1}칸", font=font(15, False), fill=SUB)
    soly = y0 + 30 + 36 * Z
    d.line([(x - 6, soly), (right + 6, soly)], fill=(220, 80, 80), width=2)
    fx = x + int(14 * Z)
    d.polygon([(fx, soly), (fx - 8, soly + 12), (fx + 8, soly + 12)], fill=(220, 80, 80))
    d.text((x, soly + 16), f"키 36칸 · 캔버스 {w}×{h} · 발바닥 줄 36", font=font(15, False), fill=SUB)
    d.text((x, soly + 36), "▲ 앞발 (x 14, 9.11.5) · 애니메이션의 기준점은 골반 가운데(x 8) 아래", font=font(15, False), fill=SUB)
    d.text((x, soly + 56), "   → 40×40 캔버스의 (20, 38)", font=font(15, False), fill=SUB)

    # ② 스카프 있음
    x2 = right + 70
    right2 = panel(s, x2, "스카프 있음 (S2)")
    # ③ 부위 지도
    x3 = right2 + 70
    hh, ww = s.shape[:2]
    m = np.zeros((hh, ww, 4), np.uint8)
    for y in range(h):
        for xx in range(w):
            if part[y, xx]:
                m[y, xx + PAD] = PART_COL[part[y, xx]] + (255,)
    inner = s[:, PAD:]
    diffm = (inner != b).any(-1)
    for y in range(hh):
        for xx in range(ww):
            X = xx - PAD
            if s[y, xx, 3] and (X < 0 or diffm[y, X]):
                m[y, xx] = PART_COL["scarf_wrap" if (X, y) in wrap else "scarf_tail"] + (255,)
    right3 = panel(m, x3, "부위 지도")
    ly = y0 + 40
    legend = [("head", f"머리 {counts['head']}칸 — 바뀌지 않음 [제안]"), ("upper", f"몸통 · 주포 팔 {counts['upper']}칸 — 바뀌지 않음 [제안]"),
              ("near_arm", f"앞쪽 팔 {counts['near_arm']}칸 — 자세 표에서 고름"), ("legs", f"다리 {counts['legs']}칸 — 프레임마다 새로 찍음"),
              ("scarf_wrap", f"스카프 목 부분 {len(wrap)}칸 — 바뀌지 않음"), ("scarf_tail", "스카프 끝 — 동작마다 표에서 고름")]
    for k, t in legend:
        d.rectangle([right3 + 24, ly, right3 + 44, ly + 20], fill=PART_COL[k])
        d.text((right3 + 54, ly - 2), t, font=font(16, False), fill=TXT)
        ly += 32
    ly += 10
    notes = ["주포 = 먼 쪽 팔 (캐릭터의 왼팔)", "오른쪽을 본다 · 소년형 · 3.6등신", "검은 외곽선 없음",
             "빛은 뒤-위에서: 뒤 · 위 가장자리에 크림색 1칸 획", "밝기는 C36 그대로 (어두운 몸이 주인)",
             "스카프 층은 C36 의 칸 12개를 덮고 16개를 더한다", "얼굴 · 눈 · 엠블럼은 덮지 않는다"]
    for t in notes:
        d.text((right3 + 24, ly), "· " + t, font=font(16, False), fill=SUB)
        ly += 28

    # ④ 팔레트
    py = y0 + 30 + 36 * Z + 80
    d.text((32, py), "팔레트 — 새 색을 만들지 않는다 (스카프 없음 15색 · 스카프 있음 18색)", font=font(21), fill=TXT)
    py += 40
    colw = 300
    for i, p in enumerate(pal):
        cx, cy = 32 + (i % 6) * colw, py + (i // 6) * 66
        rgb = tuple(int(p["hex"][j:j + 2], 16) for j in (1, 3, 5))
        d.rectangle([cx, cy, cx + 44, cy + 44], fill=rgb, outline=(90, 94, 110))
        d.text((cx + 54, cy - 2), f"{p['hex']}  {p['key']}".strip(), font=font(15), fill=TXT)
        d.text((cx + 54, cy + 18), f"{p['name']}", font=font(14, False), fill=SUB)
        cnt = f"{p['cells_base']}칸" if p["in_base"] else f"층 {p['cells_scarf']}칸"
        d.text((cx + 54, cy + 36), cnt, font=font(13, False), fill=(120, 126, 144))
    py += 3 * 66 + 10
    d.text((32, py), "재질마다의 톤", font=font(19), fill=TXT)
    py += 32
    for i, mt in enumerate(spec["materials"]):
        cx, cy = 32 + (i % 2) * 920, py + (i // 2) * 34
        for j, c in enumerate(mt["colors"]):
            rgb = tuple(int(c[k:k + 2], 16) for k in (1, 3, 5))
            d.rectangle([cx + j * 22, cy, cx + j * 22 + 18, cy + 18], fill=rgb)
        d.text((cx + len(mt["colors"]) * 22 + 8, cy - 3), f"{mt['name']}: {mt['tones']}", font=font(14, False), fill=SUB)
    img.save(HERE / "nx07_px_spec.png")


if __name__ == "__main__":
    main()
