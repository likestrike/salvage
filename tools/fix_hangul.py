"""생성된 시트의 한글 오타 중 'ㅡ 에 짧은 세로획이 잘못 붙은 글자'를 획 단위로 고친다.

이미지 모델이 자주 내는 오타가 이 종류다 (측→축, 등→동, 블→볼, 글→골, 죽→족).
글자를 새로 쓰지 않고 잘못 붙은 세로획만 지우므로 원래 글꼴이 그대로 남는다.

사용 예:
    python tools/fix_hangul.py art/concept/father_sheet.png --below 1182,1271,1220,1314
    python tools/fix_hangul.py sheet.png --above 1900,975,1945,1030 --out fixed.png

    --below x0,y0,x1,y1   가로획 '아래'에 붙은 세로획을 지운다 (축 → 측)
    --above x0,y0,x1,y1   가로획 '위'에 붙은 세로획을 지운다 (동 → 등, 볼 → 블, 골 → 글)
    --replace x0,y0,x1,y1=글자
                          상자 안의 글자를 지우고 맑은 고딕으로 다시 써 넣는다.
                          획을 지우는 것으로 안 되는 오타(해드 → 헤드)에 쓴다.

--below / --above 의 상자는 고칠 글자 '한 자'만 감싸야 한다. 여러 번 지정할 수 있다.
고친 뒤에는 반드시 확대해서 눈으로 확인한다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DARK = 80  # 이 밝기보다 어두우면 글자 획으로 본다 (획 가장자리의 번진 회색은 뺀다)


def _runs(row: np.ndarray, gap: int = 0) -> list[tuple[int, int]]:
    """어두운 픽셀이 이어진 구간들. gap 픽셀 이하로 끊긴 곳은 한 구간으로 본다."""
    xs = np.flatnonzero(row)
    if len(xs) == 0:
        return []
    parts = np.split(xs, np.flatnonzero(np.diff(xs) > 1 + gap) + 1)
    return [(int(p[0]), int(p[-1])) for p in parts]


def remove_stem(a: np.ndarray, box: tuple[int, int, int, int], side: str) -> bool:
    """box 안 글자에서 가장 긴 가로획(ㅡ)에 붙은 세로획을 지운다. 고쳤으면 True."""
    x0, y0, x1, y1 = (int(v) for v in box)
    lum = a[y0:y1, x0:x1].mean(-1)
    dark = lum < DARK
    if not dark.any():
        return False
    counts = dark.sum(1)
    rows = np.flatnonzero(counts)
    top, bot = int(rows[0]), int(rows[-1])

    bar = int(counts.argmax())
    full = int(counts[bar])
    b0 = b1 = bar
    while b0 - 1 >= top and counts[b0 - 1] >= 0.75 * full:
        b0 -= 1
    while b1 + 1 <= bot and counts[b1 + 1] >= 0.75 * full:
        b1 += 1

    step = 1 if side == "below" else -1
    edge = b1 if side == "below" else b0

    # 가로획에서 출발해 좁은 획 하나만 이어지는 줄을 따라간다 = 세로획
    stem_rows: list[int] = []
    stem: tuple[int, int] | None = None
    limit = max(6, int(0.3 * full))
    r = edge + step
    # 가로획 가장자리가 고르지 않아 군데군데만 어두운 줄은 가로획의 일부로 보고 건너뛴다.
    for _ in range(2):
        if top <= r <= bot and counts[r] >= 0.3 * full and len(_runs(dark[r])) != 1:
            r += step
    empty = 0
    while top <= r <= bot:
        runs = _runs(dark[r], gap=2)  # 획 가장자리가 한두 픽셀 끊겨 보여도 한 획으로 본다
        if stem is None:
            if not runs:
                empty += 1
                if empty > 2:
                    return False
            elif len(runs) == 1 and runs[0][1] - runs[0][0] + 1 <= limit:
                stem = runs[0]
                stem_rows.append(r)
            else:
                return False
        else:
            over = [u for u in runs if u[0] <= stem[1] + 1 and u[1] >= stem[0] - 1]
            width = stem[1] - stem[0] + 1
            if len(over) == 1 and over[0][1] - over[0][0] + 1 <= width + 2:
                stem_rows.append(r)
            else:
                break
        r += step
    if stem is None or not stem_rows:
        return False
    far = r  # 세로획이 끝난 다음 줄

    sx0, sx1 = max(stem[0] - 2, 0), min(stem[1] + 2, dark.shape[1] - 1)

    # 세로획 자리를 덮을 '깨끗한 열': 가로획은 지나가고, 세로획이 있던 줄들은 비어 있는 열
    best, best_score = None, -1.0
    for c in [sx0 - d for d in range(2, 14)] + [sx1 + d for d in range(2, 14)]:
        if not (0 <= c < dark.shape[1]) or not dark[edge, c] or dark[stem_rows, c].any():
            continue
        tail = stem_rows[1:] or stem_rows
        score = float(lum[tail, c].min())
        if score > best_score:
            best, best_score = c, score
    if best is None:
        return False

    wipe = list(stem_rows)
    if top <= far <= bot and not dark[far, sx0 : sx1 + 1].any():
        wipe.append(far)  # 세로획 끝의 번진 회색까지 지운다
    for rr in wipe:
        a[y0 + rr, x0 + sx0 : x0 + sx1 + 1] = a[y0 + rr, x0 + best]
    return True


FONTS = {
    "bold": "C:/Windows/Fonts/malgunbd.ttf",
    "regular": "C:/Windows/Fonts/malgun.ttf",
}


def replace_text(a: np.ndarray, box: tuple[int, int, int, int], text: str) -> bool:
    """box 안의 글자를 지우고 같은 자리·같은 크기로 text 를 다시 써 넣는다.

    세로획 지우기로 고칠 수 없는 오타(다른 글자가 된 경우)에 쓴다.
    글꼴은 맑은 고딕이라 주변 글자와 모양이 조금 다를 수 있다.
    """
    x0, y0, x1, y1 = (int(v) for v in box)
    region = a[y0:y1, x0:x1]
    lum = region.mean(-1)
    dark = lum < DARK
    if not dark.any():
        return False
    ys, xs = np.flatnonzero(dark.any(1)), np.flatnonzero(dark.any(0))
    ty0, ty1, tx0, tx1 = int(ys[0]), int(ys[-1]), int(xs[0]), int(xs[-1])
    ink = tuple(int(v) for v in np.median(region[dark], axis=0))
    paper = tuple(int(v) for v in np.median(region[lum > 200], axis=0)) if (lum > 200).any() else (245, 245, 245)

    # 획 굵기로 굵은 글꼴인지 판단한다 (가로로 이어진 어두운 구간의 중간값 / 글자 높이)
    widths = [b - s + 1 for row in dark for s, b in _runs(row)]
    weight = "bold" if np.median(widths) / (ty1 - ty0 + 1) > 0.1 else "regular"

    target_h, target_w = ty1 - ty0 + 1, tx1 - tx0 + 1
    size = target_h
    for _ in range(40):  # 글자 높이가 원래와 같아질 때까지 크기를 맞춘다
        font = ImageFont.truetype(FONTS[weight], size)
        l, t, r, b = font.getbbox(text)
        if b - t < target_h:
            size += 1
        elif b - t > target_h + 1:
            size -= 1
        else:
            break
    l, t, r, b = font.getbbox(text)
    while r - l > target_w + 2 and size > 8:  # 원래 폭을 넘지 않게 줄인다
        size -= 1
        font = ImageFont.truetype(FONTS[weight], size)
        l, t, r, b = font.getbbox(text)

    img = Image.fromarray(a)
    draw = ImageDraw.Draw(img)
    pad = 3
    draw.rectangle([x0 + tx0 - pad, y0 + ty0 - pad, x0 + tx1 + pad, y0 + ty1 + pad], fill=paper)
    # 원래 글자 묶음의 가운데에 맞춘다
    ox = x0 + tx0 + (target_w - (r - l)) // 2 - l
    oy = y0 + ty0 + (target_h - (b - t)) // 2 - t
    draw.text((ox, oy), text, font=font, fill=ink)
    a[:] = np.asarray(img)
    return True


def parse_box(text: str) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = (int(v) for v in text.split(","))
    return x0, y0, x1, y1


def parse_replace(text: str) -> tuple[tuple[int, int, int, int], str]:
    box, _, label = text.partition("=")
    return parse_box(box), label


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="시트의 한글 오타 수정")
    ap.add_argument("src")
    ap.add_argument("--below", action="append", default=[], type=parse_box)
    ap.add_argument("--above", action="append", default=[], type=parse_box)
    ap.add_argument("--replace", action="append", default=[], type=parse_replace,
                    metavar="x0,y0,x1,y1=글자", help="상자 안의 글자를 지우고 새로 써 넣는다")
    ap.add_argument("--out", help="생략하면 원본을 덮어쓴다")
    args = ap.parse_args()

    a = np.array(Image.open(args.src).convert("RGB"))
    for side, boxes in (("below", args.below), ("above", args.above)):
        for box in boxes:
            ok = remove_stem(a, box, side)
            print(f"{side} {box}: {'고침' if ok else '고칠 획을 찾지 못함'}")
    for box, label in args.replace:
        ok = replace_text(a, box, label)
        print(f"replace {box} -> {label}: {'고침' if ok else '글자를 찾지 못함'}")
    Image.fromarray(a).save(args.out or args.src)
    print(f"[saved] {Path(args.out or args.src)}")


if __name__ == "__main__":
    main()
