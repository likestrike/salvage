"""스프라이트 시트의 색을 바꾼다.

    --mode enemy   NX-07 → ARTEMIS 에 연결된 NX 양산형.
                   올리브색 장갑은 어두운 강철색으로, 시안 발광은 붉은색으로 바꾼다.
    --mode olive   새로 뽑은 시트의 장갑이 회색으로 나왔을 때 기존 시트의 올리브색에 맞춘다.
                   --rows 로 지정한 행(0부터)에만 적용한다. 칸 크기는 96px.
    --mode skin    올리브색 장갑을 색상 바리에이션 B~F 로 바꾼다 (--skin).
    --mode match   새로 뽑은 시트의 장갑 색을 --like 로 준 기존 시트의 장갑 색에 맞춘다.
                   밝기는 그대로 두고 색상과 채도만 기존 시트에서 가져온다.
                   장갑이 회색으로 나온 시트라면 --gray 를 붙인다.

브라우저에서 file:// 로 연 그림은 픽셀을 읽을 수 없어서, 실행 중이 아니라 미리 만들어 둔다.

사용 예:
    python tools/recolor_sheet.py --mode enemy art/sprites/nx07_sheet_1x.png game/assets/nx_trooper_1x.png
    python tools/recolor_sheet.py --mode olive --rows 0,1 art/sprites/combat_sheet_1x.png game/assets/combat_sheet_1x.png
    python tools/recolor_sheet.py --mode match --like game/assets/nx07_sheet_1x.png art/sprites/nx07_uppercut_1x.png game/assets/uppercut_sheet_1x.png
"""
from __future__ import annotations

import argparse
import colorsys

import numpy as np
from PIL import Image

CELL = 96


HUE_LO = 40.0   # 장갑으로 보는 색상의 아래쪽 경계 (--hue-lo)
SAT_LO = None   # 장갑으로 보는 채도의 아래쪽 경계 (--sat-lo)


def enemy(r: int, g: int, b: int):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    deg = h * 360
    if HUE_LO <= deg <= 110 and s > (0.12 if SAT_LO is None else SAT_LO) and v <= 0.74:   # 올리브 장갑 → 어두운 강철색
        return colorsys.hsv_to_rgb(225 / 360, s * 0.35, v * 0.82)
    if 160 <= deg <= 205 and s > 0.3:        # 시안 발광 → 붉은 발광
        return colorsys.hsv_to_rgb(356 / 360, min(1.0, s * 1.05), v)
    return None


def olive(r: int, g: int, b: int):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    deg = h * 360
    # 누르스름한 회색의 중간 밝기 = 회색으로 나온 장갑. 순수한 회색(연기, 흰 판의 그림자)은 건드리지 않는다.
    if 30 <= deg <= 110 and 0.05 <= s <= 0.2 and 0.2 <= v <= 0.64:
        return colorsys.hsv_to_rgb(70 / 360, min(0.26, s * 1.6 + 0.07), v)
    return None


# 색상 바리에이션 (art/concept/nx07_color_variations.png 의 B~F).
# 올리브 장갑의 밝기에 따라 (위치, 색) 을 잇는 색 띠로 바꾼다. 흰 판·검은 슈트·시안 발광은 그대로 둔다.
SKINS = {
    "b": [(0.0, "#B85A1C"), (0.42, "#EE8A3A"), (0.43, "#D9D5CC"), (1.0, "#FFFFFF")],   # 화이트 오렌지
    "c": [(0.0, "#16306E"), (0.55, "#2F62C8"), (1.0, "#6FA0F2")],                       # 코발트 블루
    "d": [(0.0, "#5E0F1A"), (0.55, "#B8242F"), (1.0, "#EA5E66")],                       # 크림슨 레드
    "e": [(0.0, "#15161A"), (0.55, "#30323A"), (1.0, "#555964")],                       # 차콜 블랙
    "f": [(0.0, "#9A6A12"), (0.55, "#E0AE2A"), (1.0, "#F8DA66")],                       # 인더스트리얼 옐로
}


def _hex(c: str):
    return tuple(int(c[i : i + 2], 16) / 255 for i in (1, 3, 5))


def make_skin(stops, v_lo: float, v_hi: float):
    stops = [(t, _hex(c)) for t, c in stops]

    def fn(r: int, g: int, b: int):
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        deg = h * 360
        if not (HUE_LO <= deg <= 110 and (0.08 if SAT_LO is None else SAT_LO) <= s <= 0.42 and 0.10 <= v <= 0.74):   # 올리브 장갑만
            return None
        t = min(1.0, max(0.0, (v - v_lo) / (v_hi - v_lo)))
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t <= t1:
                k = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                return tuple(c0[i] + (c1[i] - c0[i]) * k for i in range(3))
        return stops[-1][1]

    return fn


def make_match(ref_path: str, gray: bool):
    """기준 시트의 장갑 색(밝기 구간마다의 색상·채도)을 읽어, 같은 밝기의 장갑 픽셀에 입힌다."""
    lo, hi, bins = 0.10, 0.70, 12
    ref = np.array(Image.open(ref_path).convert("RGBA"))
    acc = [[] for _ in range(bins)]
    for r, g, b in ref[ref[..., 3] > 0][:, :3]:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if 20 <= h * 360 <= 110 and 0.06 <= s <= 0.45 and lo <= v <= hi:
            acc[min(bins - 1, int((v - lo) / (hi - lo) * bins))].append((h, s))
    filled = [i for i in range(bins) if acc[i]]
    if not filled:
        raise SystemExit(f"{ref_path} 에서 장갑 색을 찾지 못했다")
    table = []
    for i in range(bins):
        src = np.array(acc[min(filled, key=lambda j: abs(j - i))])
        table.append((float(np.median(src[:, 0])), float(np.median(src[:, 1]))))

    def fn(r: int, g: int, b: int):
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        deg = h * 360
        if not lo <= v <= hi:
            return None
        armor = 20 <= deg <= 110 and 0.05 <= s <= 0.45
        # 회색으로 나온 장갑. 시안 발광이 비친 푸른 면과 흰 판의 밝은 그림자는 건드리지 않는다.
        grayish = gray and s <= 0.30 and v <= 0.58 and not (150 <= deg <= 260 and s > 0.18)
        if not (armor or grayish):
            return None
        th, ts = table[min(bins - 1, int((v - lo) / (hi - lo) * bins))]
        return colorsys.hsv_to_rgb(th, ts, v)

    return fn


def main() -> None:
    ap = argparse.ArgumentParser(description="스프라이트 시트 색 바꾸기")
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--mode", choices=["enemy", "olive", "skin", "match"], default="enemy")
    ap.add_argument("--like", help="--mode match 일 때 색을 맞출 기준 시트")
    ap.add_argument("--gray", action="store_true", help="--mode match 에서 회색으로 나온 장갑도 바꾼다")
    ap.add_argument("--skin", choices=sorted(SKINS), help="--mode skin 일 때의 색상 (b~f)")
    ap.add_argument("--v-range", default="0.20,0.58", help="올리브 장갑의 가장 어두운 밝기와 가장 밝은 밝기")
    ap.add_argument("--rows", default="", help="적용할 행 (쉼표로 구분, 0부터). 비우면 전체")
    ap.add_argument("--hue-lo", type=float, default=40.0, help="장갑으로 보는 색상의 아래쪽 경계. 스타일 2 시트는 28")
    ap.add_argument("--sat-lo", type=float, default=None, help="장갑으로 보는 채도의 아래쪽 경계. 스타일 2 시트는 0.06")
    args = ap.parse_args()

    global HUE_LO, SAT_LO
    HUE_LO, SAT_LO = args.hue_lo, args.sat_lo

    if args.mode == "skin":
        lo, hi = (float(v) for v in args.v_range.split(","))
        fn = make_skin(SKINS[args.skin], lo, hi)
    elif args.mode == "match":
        if not args.like:
            ap.error("--mode match 에는 --like 가 필요하다")
        fn = make_match(args.like, args.gray)
    else:
        fn = enemy if args.mode == "enemy" else olive
    rows = {int(v) for v in args.rows.split(",") if v != ""}
    a = np.array(Image.open(args.src).convert("RGBA"))
    h, w = a.shape[:2]
    changed = 0
    for y in range(h):
        if rows and y // CELL not in rows:
            continue
        for x in range(w):
            r, g, b, alpha = a[y, x]
            if alpha == 0:
                continue
            new = fn(int(r), int(g), int(b))
            if new is None:
                continue
            a[y, x, :3] = [round(c * 255) for c in new]
            changed += 1
    Image.fromarray(a).save(args.out)
    print(f"[saved] {args.out} ({w}x{h}, {changed} px 변경)")


if __name__ == "__main__":
    main()
