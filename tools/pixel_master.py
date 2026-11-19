"""도트풍 그림 한 장 → 픽셀 마스터 (기획서 9.11).

AI 가 '도트처럼' 그린 그림(칸이 고르지 않고 색이 많다)을 격자로 나눠 칸마다 한 색을 칠해
진짜 도트로 만든다. 칸 크기를 하나로 정하지 않고 후보 여러 개로 돌려 원본 옆에 나란히 놓는다.
도구가 하나를 추천하지만 고르는 것은 사람이다 (docs/pipeline/PIXEL_SPRITE_PIPELINE.md 4장의 원칙 6).

    python tools/pixel_master.py <그림.png> <출력 폴더> --name 이름 [--cells 7.5,8,9] [--target-height 83]
                                 [--colors 24] [--pick 7.75] [--no-ppa]

순서
  1 배경 제거   투명 PNG 면 알파를 쓴다. 아니면 마젠타 배경을 지운다 (process_sheet.key_mask).
  2 칸 크기 후보 그림의 경계선 간격(주기)을 재서 후보를 만든다. --cells 로 더할 수 있다.
                --target-height 는 '키가 그 칸 수가 되도록 억지로 맞춘' 후보다 (원칙 3을 어기는 비교용, 추천하지 않는다).
  3 격자 맞춤   축마다 경계선이 센 자리를 따라 줄을 긋는다 (칸 너비는 후보의 0.75~1.25배, 동적 계획법).
                AI 그림은 칸이 조금씩 밀리므로 고정 간격으로 자르지 않는다.
                proper-pixel-art(pixel_width = 후보를 반올림한 정수)로도 돌려 함께 견준다 (--no-ppa 로 끈다).
  4 칸의 색     먼저 그림 전체를 --pre-colors 색(기본 48)으로 나눈 뒤, 칸의 가운데(가장자리 1/4씩 뺀 곳)에서 가장 많은 색 하나를 칠한다.
                색을 섞지 않는다. 칸의 반 넘게 배경이면 투명.
  5 팔레트 잠금 마스터에서 --colors 색을 뽑아 다시 칠한다 (tools/pxl.py, docs/pipeline/pxl.py 를 그대로 복사한 것).
  6 검사        반투명 · 팔레트 이탈 (pxl.qa), 원본과의 오차, 외톨이 픽셀, 키 · 머리 높이 · 등신.
  7 저장        <이름>.png (마스터, 1배) · <이름>_x8.png · <이름>_palette.hex/.gpl · <이름>_info.json
                <이름>_candidates.png (후보 비교 그림) · candidates/ (후보마다의 마스터)

추천: 오차가 가장 작은 후보보다 0.5 넘게 크지 않은 후보 가운데 칸이 가장 큰 것 (칸을 반으로 쪼갠 후보도 오차는 작으므로).
격자가 고른지: '칸 너비 들쭉날쭉'(격자 줄 사이 간격의 (최대-최소)/평균)이 0.3 안쪽이면 고르게 그려진 그림이다.
고르지 않은 그림은 어느 후보도 어딘가를 망가뜨리므로 추천을 믿지 말고 눈으로 고른다.
--pick 으로 다른 후보를 마스터로 고른다 (값은 후보 이름, 예: 7.75 또는 ppa8).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pxl import extract_palette, qa, quantize, to_oklab  # noqa: E402  (docs/pipeline/pxl.py 의 복사본)
from process_sheet import key_mask  # noqa: E402

FONT = "C:/Windows/Fonts/malgunbd.ttf"
BG = (30, 32, 40)


def font(size: int):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- 1 배경

def load_cutout(path: Path) -> np.ndarray:
    im = Image.open(path)
    a = np.array(im.convert("RGBA"))
    if im.mode in ("RGBA", "LA", "P") and (a[..., 3] < 128).mean() > 0.05:
        a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
        return a
    bg = key_mask(a[..., :3])
    a[..., 3] = np.where(bg, 0, 255)
    return a


def bbox(alpha: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(alpha > 0)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


# ---------------------------------------------------------------- 2 칸 크기

def edge_profiles(rgba: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """경계의 세기. px[i] = i-1 과 i 사이의 색 차이 합 (배경은 한 색으로 눌러서 잡음을 뺀다)."""
    lab = to_oklab(rgba[..., :3].reshape(-1, 3)).reshape(rgba.shape[:2] + (3,))
    lab[rgba[..., 3] == 0] = 0
    dx = np.linalg.norm(np.diff(lab, axis=1), axis=-1)
    dy = np.linalg.norm(np.diff(lab, axis=0), axis=-1)
    px = np.concatenate([[0], dx.sum(0)])
    py = np.concatenate([[0], dy.sum(1)])
    return px, py


def period(profile: np.ndarray, lo: float = 3.0, hi: float = 24.0) -> list[tuple[float, float]]:
    p = profile - profile.mean()
    k = np.arange(len(p))
    out = []
    for s in np.arange(lo, hi, 0.05):
        out.append((float(np.abs((p * np.exp(-2j * np.pi * k / s)).sum())), round(float(s), 2)))
    out.sort(reverse=True)
    return out


def auto_cells(px: np.ndarray, py: np.ndarray) -> tuple[float, list[float]]:
    sx, sy = period(px), period(py)
    best = {}
    for c, s in sx[:40] + sy[:40]:
        key = round(s * 4) / 4
        best[key] = best.get(key, 0) + c
    s0 = max(best, key=best.get)
    cands = sorted({round(s0 * f * 4) / 4 for f in (0.87, 0.94, 1.0, 1.07, 1.15)})
    return s0, cands


# ---------------------------------------------------------------- 3 격자

def dp_lines(profile: np.ndarray, s: float, n: int, weight: float = 0.6) -> np.ndarray:
    """0 과 n 을 포함하는 줄의 자리. 칸 너비는 s 의 0.75~1.25배, 경계가 센 자리를 따라간다."""
    lo, hi = max(1, int(np.floor(s * 0.75))), int(np.ceil(s * 1.25))
    p = profile[: n + 1].astype(np.float64)
    if len(p) < n + 1:
        p = np.concatenate([p, np.zeros(n + 1 - len(p))])
    p = p / (p.mean() + 1e-9) - 1.0  # 평균보다 센 경계에서만 줄을 긋는 것이 이득이다 (아니면 줄을 많이 긋는 쪽으로 치우친다)
    neg = -1e18
    score = np.full(n + 1, neg)
    prev = np.full(n + 1, -1, dtype=np.int64)
    score[0] = 0.0
    for x in range(1, n + 1):
        best, arg = neg, -1
        first = x <= hi  # 첫 칸은 잘려 있어도 된다
        last = x == n
        gl = 1 if (first or last) else lo
        for g in range(gl, hi + 1):
            q = x - g
            if q < 0:
                break
            if score[q] == neg:
                continue
            pen = 0.0 if ((q == 0) or last) else weight * ((g - s) / (0.25 * s)) ** 2
            v = score[q] + p[x] - pen
            if v > best:
                best, arg = v, q
        score[x], prev[x] = best, arg
    lines = [n]
    while lines[-1] > 0:
        lines.append(int(prev[lines[-1]]))
    return np.array(lines[::-1])


def uniform_lines(profile: np.ndarray, s: float, n: int) -> np.ndarray:
    """고른 간격 s 의 줄. 시작 자리만 경계가 가장 센 곳으로 고른다 (억지 맞춤 후보에 쓴다)."""
    best, arg = -1.0, 0.0
    for ox in np.arange(0, s, 0.25):
        pos = np.round(np.arange(ox, n, s)).astype(int)
        pos = pos[(pos > 0) & (pos < n)]
        v = profile[pos].sum()
        if v > best:
            best, arg = v, ox
    pos = np.round(np.arange(arg, n, s)).astype(int)
    pos = pos[(pos > 0) & (pos < n)]
    return np.unique(np.concatenate([[0], pos, [n]]))


def cell_index(lines: np.ndarray, n: int) -> np.ndarray:
    idx = np.searchsorted(lines, np.arange(n), side="right") - 1
    return np.clip(idx, 0, len(lines) - 2)


def inner_mask(lines: np.ndarray, n: int) -> np.ndarray:
    """칸의 가운데인가 (칸 너비의 1/4 씩 양쪽을 뺀다)."""
    idx = cell_index(lines, n)
    x = np.arange(n)
    left, right = lines[idx], lines[idx + 1]
    w = right - left
    m = w / 4.0
    return (x >= left + m - 0.01) & (x < right - m + 0.01) | (w <= 2)


def fill_cells(rgba: np.ndarray, lab_idx: np.ndarray, pal64: np.ndarray, lx: np.ndarray, ly: np.ndarray) -> np.ndarray:
    h, w = rgba.shape[:2]
    cx, cy = cell_index(lx, w), cell_index(ly, h)
    nx, ny = len(lx) - 1, len(ly) - 1
    cid = cy[:, None] * nx + cx[None, :]
    inner = inner_mask(ly, h)[:, None] & inner_mask(lx, w)[None, :]
    opaque = rgba[..., 3] > 0
    ncell = nx * ny
    # 투명: 칸의 반 넘게 배경
    tot = np.bincount(cid.ravel(), minlength=ncell)
    opq = np.bincount(cid.ravel(), weights=opaque.ravel().astype(float), minlength=ncell)
    solid = opq * 2 > tot
    k = len(pal64)
    out = np.zeros((ncell, 4), np.uint8)
    for use in (inner & opaque, opaque):
        sel = use.ravel()
        counts = np.bincount(cid.ravel()[sel] * k + lab_idx.ravel()[sel], minlength=ncell * k).reshape(ncell, k)
        has = counts.sum(1) > 0
        todo = solid & has & (out[:, 3] == 0)
        out[todo, :3] = pal64[counts[todo].argmax(1)]
        out[todo, 3] = 255
    return out.reshape(ny, nx, 4)


def ppa_master(src_rgba: np.ndarray, width: int) -> tuple[np.ndarray, int] | None:
    try:
        from proper_pixel_art import pixelate
        from proper_pixel_art.config import PixelateConfig
    except ImportError:
        return None
    img = src_rgba.copy()
    img[img[..., 3] == 0, :3] = (255, 0, 255)
    res = pixelate(Image.fromarray(img, "RGBA"), PixelateConfig(pixel_width=width, transparent_background=True))
    a = np.array(res.image.convert("RGBA"))
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    a[key_mask(a[..., :3]) & (a[..., 3] > 0), 3] = 0
    mx, my = res.mesh
    f = res.upscale_factor
    lx = np.round(np.asarray(mx) / f).astype(int)
    ly = np.round(np.asarray(my) / f).astype(int)
    return a, lx, ly


# ---------------------------------------------------------------- 6 검사

def crop_alpha(a: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = bbox(a[..., 3])
    return a[y0:y1, x0:x1]


def head_height(a: np.ndarray) -> tuple[int, int]:
    """(키, 머리 높이). 머리 높이 = 정수리에서 목(위쪽 몸에서 가장 좁은 줄)까지. 자동으로 잰 값이다."""
    op = a[..., 3] > 0
    rows = np.where(op.any(1))[0]
    top, bot = rows[0], rows[-1]
    hgt = bot - top + 1
    widths = []
    for y in range(top + int(hgt * 0.15), top + int(hgt * 0.45)):
        xs = np.where(op[y])[0]
        # 가장 큰 덩어리의 너비 (뒤로 뻗은 귀 장치 끝 같은 떨어진 조각은 뺀다)
        runs = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1) if len(xs) else []
        widths.append((max((len(r) for r in runs), default=0), y))
    neck = min(widths)[1]
    return int(hgt), int(neck - top)


def orphan_ratio(a: np.ndarray) -> float:
    op = a[..., 3] > 0
    rgb = a[..., :3].astype(int)
    key = rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]
    key[~op] = -1
    pad = np.pad(key, 1, constant_values=-2)
    c = pad[1:-1, 1:-1]
    same = (pad[:-2, 1:-1] == c) | (pad[2:, 1:-1] == c) | (pad[1:-1, :-2] == c) | (pad[1:-1, 2:] == c)
    return float((op & ~same).sum() / max(1, op.sum()))


def recon_error(src: np.ndarray, master_full: np.ndarray, lx, ly) -> tuple[float, float]:
    """마스터를 격자대로 원본 크기로 되돌려 원본과 견준다. (색 오차 ΔE×100, 실루엣 불일치 %)"""
    h, w = src.shape[:2]
    cx, cy = cell_index(lx, w), cell_index(ly, h)
    back = master_full[cy[:, None], cx[None, :]]
    so, bo = src[..., 3] > 0, back[..., 3] > 0
    both = so & bo
    d = np.linalg.norm(to_oklab(src[both][:, :3]) - to_oklab(back[both][:, :3]), axis=-1)
    return float(d.mean() * 100), float((so ^ bo).sum() / max(1, (so | bo).sum()) * 100)


def lock_palette(m: np.ndarray, colors: int) -> tuple[np.ndarray, np.ndarray]:
    img = Image.fromarray(m, "RGBA")
    pal = extract_palette(img, n=colors)
    pal = pal[np.argsort(to_oklab(pal)[:, 0])]
    return np.array(quantize(img, pal)), pal


def metrics(master: np.ndarray, pal: np.ndarray) -> dict:
    c = crop_alpha(master)
    hgt, head = head_height(c)
    used = np.unique(c[c[..., 3] > 0][:, :3], axis=0)
    return {
        "size": [int(c.shape[1]), int(c.shape[0])],
        "height": hgt,
        "head": head,
        "heads_tall": round(hgt / max(1, head), 2),
        "colors": int(len(used)),
        "orphan_pct": round(orphan_ratio(c) * 100, 1),
        "qa": qa([Image.fromarray(c, "RGBA")], pal, c.shape[1], c.shape[0]),
    }


# ---------------------------------------------------------------- 그림

def label(draw, xy, text, size=18, fill=(235, 235, 240)):
    draw.text(xy, text, font=font(size), fill=fill)


def on_bg(a: np.ndarray, scale: int) -> Image.Image:
    im = Image.fromarray(a, "RGBA")
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    b = Image.new("RGBA", im.size, BG + (255,))
    b.alpha_composite(im)
    return b


def candidate_sheet(src_crop: np.ndarray, cands: list[dict], path: Path, title: str) -> None:
    disp_h = 640
    head_h = 300
    panels = []
    # 원본
    s = disp_h / src_crop.shape[0]
    o = Image.fromarray(src_crop, "RGBA").resize((int(src_crop.shape[1] * s), disp_h), Image.BOX)
    ob = Image.new("RGBA", o.size, BG + (255,)); ob.alpha_composite(o)
    hs = int(src_crop.shape[0] * 0.36)
    oh = Image.fromarray(src_crop[:hs], "RGBA")
    k = head_h / hs
    oh = oh.resize((int(oh.width * k), head_h), Image.BOX)
    ohb = Image.new("RGBA", oh.size, BG + (255,)); ohb.alpha_composite(oh)
    panels.append(("원본 (축소해서 보임)", ["도트풍 그림, 진짜 도트가 아니다"], ob, ohb, False))
    for c in cands:
        m = crop_alpha(c["master"])
        sc = max(1, disp_h // m.shape[0])
        body = on_bg(m, sc)
        hrows = max(1, int(round(m.shape[0] * 0.36)))
        hk = max(1, head_h // hrows)
        headim = on_bg(m[:hrows], hk)
        # 머리 높이(목) 표시: 오른쪽에 짧은 눈금
        d = ImageDraw.Draw(body)
        neck_y = c["metrics"]["head"] * sc
        d.line([(body.width - 10, neck_y), (body.width - 1, neck_y)], fill=(255, 200, 60), width=2)
        mt = c["metrics"]
        lines = [f"키 {mt['height']} · 머리 {mt['head']} · {mt['heads_tall']}등신",
                 f"오차 {c['err']:.2f} · 실루엣 {c['sil']:.1f}% · 외톨이 {mt['orphan_pct']}%",
                 f"{mt['colors']}색 · 칸 너비 들쭉날쭉 {c.get('spread', '-')} · ×{sc} 확대"]
        name = c["name"]
        tag = f"{c['method_ko']} 칸 {c['cell']}px"
        panels.append((tag + ("  ← 추천" if c.get("recommended") else "") + ("  (억지 맞춤)" if c.get("forced") else ""),
                       lines, body, headim, c.get("recommended")))
    pad = 24
    col_w = [max(p[2].width, p[3].width, 300) for p in panels]
    W = sum(col_w) + pad * (len(panels) + 1)
    H = 70 + 80 + disp_h + 20 + head_h + 40
    sheet = Image.new("RGB", (W, H), (18, 19, 24))
    d = ImageDraw.Draw(sheet)
    label(d, (pad, 16), title, 26)
    x = pad
    for (tag, lines, body, headim, rec), cw in zip(panels, col_w):
        label(d, (x, 64), tag, 18, (255, 210, 90) if rec else (235, 235, 240))
        for i, t in enumerate(lines):
            label(d, (x, 88 + i * 20), t, 14, (190, 195, 205))
        y0 = 150
        sheet.paste(body.convert("RGB"), (x, y0 + disp_h - body.height))
        sheet.paste(headim.convert("RGB"), (x, y0 + disp_h + 20))
        if rec:
            d.rectangle([x - 6, 58, x + cw + 6, H - 12], outline=(255, 210, 90), width=2)
        x += cw + pad
    sheet.save(path)


# ---------------------------------------------------------------- main

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="도트풍 그림 → 픽셀 마스터 (기획서 9.11)")
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--name", default="master")
    ap.add_argument("--cells", default="", help="더할 칸 크기 후보 (원본 px, 쉼표로). 예: 7.5,8,9")
    ap.add_argument("--target-height", type=int, action="append", default=[],
                    help="키가 이 칸 수가 되도록 억지로 맞춘 후보를 더한다 (비교용, 추천하지 않는다)")
    ap.add_argument("--colors", type=int, default=24)
    ap.add_argument("--pre-colors", type=int, default=48, help="칸의 색을 고르기 전에 그림을 나누는 색 수")
    ap.add_argument("--pick", default=None, help="마스터로 쓸 후보 이름 (예: 7.75, ppa8). 없으면 추천")
    ap.add_argument("--no-ppa", action="store_true", help="proper-pixel-art 후보를 만들지 않는다")
    ap.add_argument("--title", default=None)
    a = ap.parse_args()

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "candidates").mkdir(exist_ok=True)
    full = load_cutout(Path(a.src))
    x0, y0, x1, y1 = bbox(full[..., 3])
    m = 24
    X0, Y0 = max(0, x0 - m), max(0, y0 - m)
    X1, Y1 = min(full.shape[1], x1 + m), min(full.shape[0], y1 + m)
    src = full[Y0:Y1, X0:X1].copy()
    char_h = y1 - y0
    h, w = src.shape[:2]

    px, py = edge_profiles(src)
    s0, cands = auto_cells(px, py)
    for t in a.cells.split(","):
        if t.strip():
            cands.append(float(t))
    forced = {}
    for t in a.target_height:
        s = round(char_h / t, 2)
        forced[s] = t
        cands.append(s)
    cands = sorted(set(cands))
    print(f"[grid] 경계 주기로 잰 칸 크기 약 {s0}px, 후보 {cands}")

    # 4 칸의 색을 고를 64색
    op = src[..., 3] > 0
    pal64 = extract_palette(Image.fromarray(src, "RGBA"), n=a.pre_colors)
    from pxl import _nearest
    idx = np.zeros(op.shape, np.int64)
    idx[op] = _nearest(to_oklab(src[op][:, :3]), to_oklab(pal64))

    results = []
    for s in cands:
        if s in forced:
            lx, ly = uniform_lines(px, s, w), uniform_lines(py, s, h)
        else:
            lx, ly = dp_lines(px, s, w), dp_lines(py, s, h)
        mfull = fill_cells(src, idx, pal64, lx, ly)
        locked, pal = lock_palette(mfull, a.colors)
        err, sil = recon_error(src, locked, lx, ly)
        gx, gy = np.diff(lx)[1:-1], np.diff(ly)[1:-1]
        r = {"name": f"{s:g}", "method": "dp", "method_ko": "직접", "cell": s, "master": locked, "pal": pal,
             "err": err, "sil": sil, "forced": s in forced,
             "grid": {"cols": len(lx) - 1, "rows": len(ly) - 1,
                      "gap_x": [int(gx.min()), int(gx.max())] if len(gx) else None,
                      "gap_y": [int(gy.min()), int(gy.max())] if len(gy) else None,
                      "mean_x": round(float(gx.mean()), 2) if len(gx) else None,
                      "mean_y": round(float(gy.mean()), 2) if len(gy) else None}}
        if s in forced:
            r["forced_height"] = forced[s]
        r["spread"] = round(max(float((gx.max() - gx.min()) / gx.mean()) if len(gx) else 0,
                                float((gy.max() - gy.min()) / gy.mean()) if len(gy) else 0), 2)
        r["metrics"] = metrics(locked, pal)
        results.append(r)
        print(f"[dp  {s:>6}] 키 {r['metrics']['height']:>4} 머리 {r['metrics']['head']:>3} 오차 {err:5.2f} 실루엣 {sil:4.1f}% "
              f"외톨이 {r['metrics']['orphan_pct']}% 칸 너비 x{r['grid']['gap_x']} y{r['grid']['gap_y']}")

    # 추천 (억지 맞춤 제외)
    pool = [r for r in results if not r["forced"]]
    emin = min(r["err"] for r in pool)
    rec = max((r for r in pool if r["err"] <= emin + 0.5), key=lambda r: r["cell"])
    rec["recommended"] = True

    if not a.no_ppa:
        for wpx in sorted({int(round(rec["cell"])), int(np.floor(rec["cell"])), int(np.ceil(rec["cell"]))}):
            got = ppa_master(src, wpx)
            if got is None:
                print("[ppa] proper-pixel-art 가 없어 건너뛴다 (pip install proper-pixel-art)")
                break
            pm, plx, ply = got
            locked, pal = lock_palette(pm, a.colors)
            r = {"name": f"ppa{wpx}", "method": "ppa", "method_ko": "proper-pixel-art", "cell": wpx,
                 "master": locked, "pal": pal, "forced": False, "err": float("nan"), "sil": float("nan"),
                 "grid": {"cols": int(pm.shape[1]), "rows": int(pm.shape[0])}}
            if len(plx) - 1 == pm.shape[1] and len(ply) - 1 == pm.shape[0]:
                r["err"], r["sil"] = recon_error(src, locked, plx, ply)
            gx, gy = np.diff(plx)[1:-1], np.diff(ply)[1:-1]
            r["grid"].update({"gap_x": [int(gx.min()), int(gx.max())], "gap_y": [int(gy.min()), int(gy.max())]})
            r["spread"] = round(max(float((gx.max() - gx.min()) / gx.mean()), float((gy.max() - gy.min()) / gy.mean())), 2)
            r["metrics"] = metrics(locked, pal)
            results.append(r)
            print(f"[ppa {wpx:>6}] 키 {r['metrics']['height']:>4} 머리 {r['metrics']['head']:>3} 오차 {r['err']:5.2f} "
                  f"외톨이 {r['metrics']['orphan_pct']}%")

    pick = rec
    if a.pick:
        pick = next((r for r in results if r["name"] == a.pick), None)
        if pick is None:
            sys.exit(f"--pick {a.pick} 후보가 없다: {[r['name'] for r in results]}")

    for r in results:
        Image.fromarray(crop_alpha(r["master"]), "RGBA").save(out / "candidates" / f"{a.name}_{r['name']}.png")

    title = a.title or f"{a.name} — 칸 크기 후보 (원본 {Path(a.src).name}, 경계 주기 약 {s0}px)"
    shown = [r for r in results if r["method"] == "dp"] + [r for r in results if r["method"] == "ppa"]
    candidate_sheet(src, shown, out / f"{a.name}_candidates.png", title)

    mst = crop_alpha(pick["master"])
    pal = pick["pal"]
    used = {tuple(c) for c in mst[mst[..., 3] > 0][:, :3].tolist()}
    pal = np.array([p for p in pal.tolist() if tuple(p) in used], np.uint8)
    base = out / a.name
    Image.fromarray(mst, "RGBA").save(f"{base}.png")
    Image.fromarray(mst, "RGBA").resize((mst.shape[1] * 8, mst.shape[0] * 8), Image.NEAREST).save(f"{base}_x8.png")
    Path(f"{base}_palette.hex").write_text("\n".join("%02x%02x%02x" % tuple(p) for p in pal) + "\n")
    with open(f"{base}_palette.gpl", "w", encoding="utf-8") as f:
        f.write(f"GIMP Palette\nName: {a.name}\nColumns: 8\n#\n")
        for p in pal:
            f.write(f"{p[0]:3d} {p[1]:3d} {p[2]:3d}\t#{'%02X%02X%02X' % tuple(p)}\n")

    def row(r):
        d = {k: v for k, v in r.items() if k not in ("master", "pal")}
        d["err"] = round(r["err"], 3); d["sil"] = round(r["sil"], 2)
        return d

    info = {
        "src": str(Path(a.src)).replace("\\", "/"),
        "char_px_height_in_src": int(char_h),
        "period_estimate_px": s0,
        "colors": a.colors,
        "recommended": rec["name"],
        "picked": pick["name"],
        "master": row(pick) | {"palette_size": int(len(pal))},
        "candidates": [row(r) for r in results],
        "notes": {
            "err": "마스터를 격자대로 원본 크기로 되돌렸을 때 원본과의 평균 색 차이 (OKLab ΔE×100). 칸이 작을수록 작아진다",
            "sil": "실루엣(불투명 영역)이 원본과 다른 픽셀의 비율 %",
            "head": "정수리에서 목(위쪽 몸에서 가장 좁은 줄)까지. 자동으로 잰 값이니 그림으로 확인한다",
            "orphan_pct": "네 이웃이 모두 다른 색인 픽셀의 비율 (잡티의 정도)",
            "recommend_rule": "오차가 가장 작은 후보 + 0.5 안에서 칸이 가장 큰 것. 억지 맞춤(--target-height)과 ppa 는 추천에서 뺀다",
            "spread": "칸 너비 들쭉날쭉 = 격자 줄 사이 간격의 (최대-최소)/평균, 가로·세로 중 큰 쪽. 0.3 안쪽이면 고른 격자",
        },
    }
    Path(f"{base}_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[master] {pick['name']} → {base}.png  {info['master']['metrics']}")


if __name__ == "__main__":
    main()
