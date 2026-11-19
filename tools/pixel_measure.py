"""픽셀 마스터를 재는 함수 (캐릭터 픽셀 파이프라인, docs/pipeline/CHARACTER_PIPELINE.md).

기획서 9.11.3 ~ 9.11.5 에서 쓴 측정 코드를 옮겨 왔다. 원래 자리는 공개하지 않는 reference/pixel_style/analysis/
(common.py · measure.py · measure_v2.py · restore.py)였다. 그 폴더는 다른 회사의 그림 때문에 저장소에서 빠져 있으므로,
파이프라인은 이 파일만 쓴다. 계산은 바꾸지 않았다 (같은 그림에서 같은 숫자가 나오는지 pixpipe verify 가 확인한다).

참고 그림(다른 회사의 작품)은 이 파일이 읽지 않는다. 참고 그림에서 잰 숫자는 art/characters/_pipeline/reference_targets.json 에
있고, 그 숫자를 다시 재는 일(pixpipe ref-targets)만 참고 그림이 PC 에 있을 때 restore_grid 를 쓴다.

두 갈래로 보고한다 (9.11.3 의 교훈: 형식만 재고 성공이라고 한 것이 잘못이었다).
- 형식 (format): 팔레트 이탈 · 반투명 · 격자 · 색 수 · 외톨이 — 통과 / 실패가 있다.
- 그림 (picture): 밝기 덩어리 · 색 덩어리 · 채도 · 밝기 · 얼굴 — 통과 / 실패가 없다. 참고 그림과의 거리로만 보인다.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image


# ---------------------------------------------------------------- 공통 (옛 common.py)

def lab(c) -> np.ndarray:
    """sRGB (0~255) → CIE Lab."""
    c = np.asarray(c, float) / 255
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def cluster_colors(a: np.ndarray, de: float = 6.0) -> np.ndarray:
    """복원한 그림의 색 잡음을 묶는다. 가장 가까운 두 색(Lab ΔE)부터, 칸이 많은 쪽 색으로. ΔE 가 de 를 넘으면 멈춘다."""
    op = a[..., 3] > 0
    cols, inv, cnt = np.unique(a[op][:, :3], axis=0, return_inverse=True, return_counts=True)
    inv = inv.ravel()
    L = lab(cols)
    alive = list(range(len(cols)))
    root = np.arange(len(cols))
    w = cnt.astype(float).copy()
    while len(alive) > 1:
        P = L[alive]
        d = np.linalg.norm(P[:, None] - P[None], axis=2)
        np.fill_diagonal(d, 1e9)
        i, j = np.unravel_index(d.argmin(), d.shape)
        if d[i, j] > de:
            break
        p, q = alive[i], alive[j]
        big, small = (p, q) if w[p] >= w[q] else (q, p)
        root[root == small] = big
        w[big] += w[small]
        alive.remove(small)
    out = a.copy()
    vals = out[op]
    vals[:, :3] = cols[root[inv]]
    out[op] = vals
    return out


def load_rgba(path) -> np.ndarray:
    a = np.array(Image.open(path).convert("RGBA"))
    a[..., 3] = np.where(a[..., 3] > 127, 255, 0)
    return a


def crop(a: np.ndarray) -> np.ndarray:
    ys, xs = np.where(a[..., 3] > 0)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def components(a: np.ndarray) -> list[tuple[tuple, list]]:
    """같은 색으로 4방향 이어진 영역들. [(색, [(y,x),...]), ...]"""
    h, w = a.shape[:2]
    seen = np.zeros((h, w), bool)
    out = []
    for y in range(h):
        for x in range(w):
            if seen[y, x] or a[y, x, 3] == 0:
                continue
            c = tuple(int(v) for v in a[y, x, :3])
            st = [(y, x)]
            seen[y, x] = True
            pts = []
            while st:
                cy, cx = st.pop()
                pts.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and a[ny, nx, 3] > 0 \
                            and tuple(int(v) for v in a[ny, nx, :3]) == c:
                        seen[ny, nx] = True
                        st.append((ny, nx))
            out.append((c, pts))
    return out


# ---------------------------------------------------------------- 그림의 숫자 (옛 measure.py 의 metrics)

def metrics(a: np.ndarray) -> dict:
    import cv2
    from scipy import ndimage
    op = a[..., 3] > 0
    h, w = op.shape
    n = int(op.sum())
    cols = np.unique(a[op][:, :3], axis=0)
    L3 = lab(a[..., :3])
    L, A, B = L3[..., 0], L3[..., 1], L3[..., 2]
    C = np.hypot(A, B)

    comps = components(a)
    sizes = sorted((len(p) for _, p in comps), reverse=True)
    small = sum(s for s in sizes if s <= 3)

    diff = tot = 0
    for dy, dx in ((0, 1), (1, 0)):
        p = op[:h - dy, :w - dx] & op[dy:, dx:]
        ne = (a[:h - dy, :w - dx, :3] != a[dy:, dx:, :3]).any(2)
        diff += int((p & ne).sum())
        tot += int(p.sum())

    pad = np.pad(op, 1)
    edge = op & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    inner = op & ~edge
    darker = same = black = 0
    ey, ex = np.where(edge)
    for y, x in zip(ey, ex):
        nb = [(y + dy, x + dx) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
              if 0 <= y + dy < h and 0 <= x + dx < w and inner[y + dy, x + dx]]
        if L[y, x] < 20:
            black += 1
        if not nb:
            continue
        li = np.mean([L[q] for q in nb])
        if L[y, x] < li - 8:
            darker += 1
        if any((a[q][:3] == a[y, x, :3]).all() for q in nb):
            same += 1
    ne_ = max(len(ey), 1)

    vx = vy = 0.0
    cnt = 0
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        for y in range(max(0, -dy), h - max(0, dy)):
            for x in range(max(0, -dx), w - max(0, dx)):
                y2, x2 = y + dy, x + dx
                if not (0 <= x2 < w and op[y, x] and op[y2, x2]):
                    continue
                if math.hypot(A[y, x] - A[y2, x2], B[y, x] - B[y2, x2]) > 12:
                    continue
                dl = L[y2, x2] - L[y, x]
                if abs(dl) < 6:
                    continue
                s = 1 if dl > 0 else -1
                nrm = math.hypot(dx, dy)
                vx += s * dx / nrm
                vy += s * -dy / nrm
                cnt += 1
    coh = math.hypot(vx, vy) / cnt if cnt else 0
    ang = math.degrees(math.atan2(vy, vx)) if cnt else None

    pts = np.column_stack(np.where(op))[:, ::-1].astype(np.int32)
    hull = cv2.convexHull(pts)
    harea = cv2.contourArea(hull) + 0.5 * cv2.arcLength(hull, True) + 1
    perim = int(edge.sum())

    cl = lab(cols)
    fam = []
    for i, c in enumerate(cols):
        ch = math.hypot(cl[i, 1], cl[i, 2])
        hue = math.degrees(math.atan2(cl[i, 2], cl[i, 1])) % 360
        cnt_i = int(((a[..., :3] == c).all(2) & op).sum())
        fam.append({"hex": "%02x%02x%02x" % tuple(int(v) for v in c), "L": round(float(cl[i, 0]), 1),
                    "C": round(ch, 1), "hue": round(hue), "cells": cnt_i})
    fam.sort(key=lambda f: -f["cells"])

    # 밝기 덩어리: 밝기를 세 단(어두움 < 35 ≤ 중간 < 65 ≤ 밝음)으로만 나눠 이어진 영역을 센다 (색은 잊는다)
    band = np.full(op.shape, -1)
    band[op & (L < 35)] = 0
    band[op & (L >= 35) & (L < 65)] = 1
    band[op & (L >= 65)] = 2
    vsizes = []
    vb = {}
    for bi, nm in enumerate(("dark", "mid", "light")):
        lab_, k = ndimage.label(band == bi)
        s = sorted(np.bincount(lab_.ravel())[1:].tolist(), reverse=True)
        vsizes += s
        vb[nm] = {"pct": round(100 * sum(s) / n, 1), "pieces": k, "largest_pct": round(100 * (s[0] if s else 0) / n, 1)}
    vsizes.sort(reverse=True)

    lw = L[op]
    return {
        "value_bands": vb, "value_top3_pct": round(100 * sum(vsizes[:3]) / n, 1), "value_pieces": len(vsizes),
        "size": [w, h], "cells": n, "colors": len(cols),
        "regions": len(sizes), "region_mean": round(n / len(sizes), 1),
        "top5_share_pct": round(100 * sum(sizes[:5]) / n, 1),
        "top10_share_pct": round(100 * sum(sizes[:10]) / n, 1),
        "small_region_share_pct": round(100 * small / n, 1),
        "region_sizes_top10": sizes[:10],
        "boundary_pct": round(100 * diff / tot, 1),
        "L_min": round(float(lw.min()), 1), "L_max": round(float(lw.max()), 1), "L_mean": round(float(lw.mean()), 1),
        "dark_pct": round(100 * float((lw < 30).mean()), 1), "mid_pct": round(100 * float(((lw >= 30) & (lw < 60)).mean()), 1),
        "bright_pct": round(100 * float((lw >= 60).mean()), 1),
        "accent_pct": round(100 * float((C[op] > 35).mean()), 1),
        "neutral_pct": round(100 * float((C[op] < 12).mean()), 1),
        "edge_cells": int(len(ey)), "edge_L_mean": round(float(L[edge].mean()), 1),
        "edge_black_pct": round(100 * black / ne_, 1), "edge_darker_than_inside_pct": round(100 * darker / ne_, 1),
        "edge_same_as_inside_pct": round(100 * same / ne_, 1),
        "light_coherence": round(coh, 2), "light_angle_deg": None if ang is None else round(ang),
        "light_pairs": cnt,
        "solidity": round(n / harea, 2), "perimeter_per_sqrt_area": round(perim / math.sqrt(n), 2),
        "palette": fam,
    }


def face(a: np.ndarray) -> dict:
    """얼굴 (옛 measure_v2.py). 살색 칸(밝기 L*>65, 색상 40~90°, 채도 8~45, 위 40% 안)과 눈 칸(살색에 붙은 어두운 청록 칸)을 센다.
    대비 = 살색 칸의 평균 밝기 − 얼굴 둘레(살색 · 눈에서 2칸 안)의 평균 밝기."""
    from scipy import ndimage
    op = a[..., 3] > 0
    L3 = lab(a[..., :3])
    L = L3[..., 0]
    C = np.hypot(L3[..., 1], L3[..., 2])
    hue = np.degrees(np.arctan2(L3[..., 2], L3[..., 1])) % 360
    skin = op & (L > 65) & (hue > 40) & (hue < 90) & (C > 8) & (C < 45)
    h = a.shape[0]
    skin[int(h * 0.4):] = False
    if not skin.any():
        return {"skin_cells": 0}
    near = ndimage.binary_dilation(skin) & op & ~skin & (L < 50)
    eye = near & (C > 10) & (hue > 150) & (hue < 260)
    ring = ndimage.binary_dilation(skin | eye, iterations=2) & op & ~skin & ~eye
    n = int(op.sum())
    return {"skin_cells": int(skin.sum()), "skin_pct": round(100 * skin.sum() / n, 1), "eye_cells": int(eye.sum()),
            "face_L": round(float(L[skin].mean()), 1), "around_L": round(float(L[ring].mean()), 1) if ring.any() else None,
            "contrast": round(float(L[skin].mean() - L[ring].mean()), 1) if ring.any() else None}


def region_split(a: np.ndarray) -> list[float]:
    """색 덩어리의 몫: 큰(20칸 이상) / 중간(4~19칸) / 작은(3칸 이하) %."""
    sizes = [len(p) for _, p in components(a)]
    n = sum(sizes)
    return [round(100 * sum(x for x in sizes if x >= 20) / n, 1),
            round(100 * sum(x for x in sizes if 4 <= x < 20) / n, 1),
            round(100 * sum(x for x in sizes if x <= 3) / n, 1)]


def orphan_ratio(a: np.ndarray) -> float:
    """네 이웃이 모두 다른 색인 칸의 몫 (tools/pixel_master.py 와 같다)."""
    op = a[..., 3] > 0
    rgb = a[..., :3].astype(int)
    key = rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]
    key[~op] = -1
    pad = np.pad(key, 1, constant_values=-2)
    c = pad[1:-1, 1:-1]
    same = (pad[:-2, 1:-1] == c) | (pad[2:, 1:-1] == c) | (pad[1:-1, :-2] == c) | (pad[1:-1, 2:] == c)
    return float((op & ~same).sum() / max(1, op.sum()))


# ---------------------------------------------------------------- 파이프라인이 보고하는 두 갈래

PICTURE_KEYS = [
    # (키, 이름, 단위)
    ("largest_value_mass_pct", "가장 큰 밝기 덩어리", "%"),
    ("value_top3_pct", "밝기 덩어리 위 3개", "%"),
    ("region_big_pct", "큰 색 덩어리 (20칸 이상)", "%"),
    ("region_mid_pct", "중간 조각 (4~19칸)", "%"),
    ("region_small_pct", "작은 획 (3칸 이하)", "%"),
    ("accent_pct", "채도 높은 칸 (C*>35)", "%"),
    ("L_mean", "평균 밝기 L*", ""),
    ("face_contrast", "얼굴과 둘레의 밝기 차", ""),
]


def picture(a: np.ndarray) -> dict:
    """그림 쪽 숫자 (통과 · 실패가 없다)."""
    from pixel_master import head_height
    a = crop(a)
    m = metrics(a)
    vb = m["value_bands"]
    big, mid, small = region_split(a)
    f = face(a)
    hh, hd = head_height(a)
    return {
        "largest_value_mass_pct": max(v["largest_pct"] for v in vb.values()),
        "value_top3_pct": m["value_top3_pct"],
        "region_big_pct": big, "region_mid_pct": mid, "region_small_pct": small,
        "accent_pct": m["accent_pct"], "L_mean": m["L_mean"],
        "face_contrast": f.get("contrast"), "face_skin_cells": f.get("skin_cells"),
        "height": hh, "head": hd, "heads_tall": round(hh / hd, 2) if hd else None,
        "solidity": m["solidity"], "edge_L_mean": m["edge_L_mean"],
    }


def fmt(a: np.ndarray, palette: set | None = None) -> dict:
    """형식 쪽 숫자 (통과 · 실패가 있다). palette 를 주면 그 밖의 색을 센다."""
    op = a[..., 3] > 0
    semi = int(((a[..., 3] > 0) & (a[..., 3] < 255)).sum())
    cols = {tuple(int(v) for v in c) for c in a[op][:, :3]}
    off = len(cols - palette) if palette is not None else 0
    return {"semi_transparent": semi, "off_palette": off, "colors": len(cols),
            "orphan_pct": round(100 * orphan_ratio(a), 1), "pass": semi == 0 and off == 0}


def distance(value: float | None, targets: dict, key: str) -> list[dict]:
    """참고 그림의 인물마다 (이름, 값, 차이). 통과 · 실패가 아니다."""
    out = []
    for name, t in targets.items():
        tv = t.get("picture", {}).get(key)
        lab_ = t.get("label", name)
        if value is None or tv is None:
            out.append({"ref": lab_, "value": tv, "diff": None})
        else:
            out.append({"ref": lab_, "value": tv, "diff": round(value - tv, 1)})
    return out


# ---------------------------------------------------------------- 참고 그림의 격자 복원 (옛 restore.py)

def _edge_profile(a: np.ndarray, axis: int) -> np.ndarray:
    d = np.abs(np.diff(a.astype(int), axis=axis)).sum(axis=2)
    return d.sum(axis=1 - axis)


def _best_grid(prof: np.ndarray) -> tuple[float, float, float]:
    n = len(prof)
    best = (0, 0, 0)
    tot = prof.sum()
    for p in np.arange(6.0, 12.0, 0.01):
        for ph in np.arange(0, p, 0.25):
            lines = np.arange(ph, n, p)
            idx = np.round(lines).astype(int)
            idx = idx[(idx >= 0) & (idx < n)]
            s = prof[idx].sum() / tot / (len(idx) / n)
            if s > best[0]:
                best = (s, p, ph)
    return best


def restore_grid(path: Path) -> np.ndarray:
    """깨끗한 도트 그림(확대된 것)을 1배로 복원한다. 칸 크기 6~12px 를 찾고 칸 가운데의 색을 읽는다. 배경(가장자리의 가장 많은 색)은 투명."""
    im = np.array(Image.open(path).convert("RGB"))
    px = _edge_profile(im, 1)
    py = _edge_profile(im, 0)
    _, gx, phx = _best_grid(px)
    _, gy, phy = _best_grid(py)
    x0, y0 = phx + 1, phy + 1
    xs = np.arange(x0 % gx, im.shape[1], gx)
    ys = np.arange(y0 % gy, im.shape[0], gy)
    cx = np.round(xs[:-1] + gx / 2 - 0.5).astype(int)
    cy = np.round(ys[:-1] + gy / 2 - 0.5).astype(int)
    cx = cx[cx < im.shape[1]]
    cy = cy[cy < im.shape[0]]
    small = im[np.ix_(cy, cx)]
    edge = np.concatenate([small[0], small[-1], small[:, 0], small[:, -1]])
    cols, cnt = np.unique(edge, axis=0, return_counts=True)
    bg = cols[cnt.argmax()]
    return np.dstack([small, np.where((small == bg).all(2), 0, 255).astype(np.uint8)]).astype(np.uint8)
