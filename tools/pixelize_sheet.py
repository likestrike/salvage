"""AI 가 그린 스프라이트 시트를 게임에 쓸 도트 시트로 바꾼다.

순서 (docs/GAME_DESIGN.md 9.5):
  1. 배경 제거      마젠타 배경은 색으로, 흰색·회색·체크무늬 배경은 테두리에서 이어진 영역으로 지운다.
  2. 격자 복원      proper-pixel-art 로 그림에 그려진 픽셀 격자를 찾아 1배율로 줄인다.
                   시트 전체를 한 번에 처리한다. 프레임마다 따로 하면 프레임마다 잡히는 칸 수가 달라
                   캐릭터 크기가 ±5% 흔들린다 (시트 전체로 하면 ±1~3%, 원본 자체의 흔들림과 같다).
  3. 프레임 분리    줄인 시트를 열 x 행으로 자른다.
  4. 프레임 정리    옆 칸에서 넘어온 조각과 1~2px 짜리 외딴 조각을 지우고,
                   주변과 비슷한 색의 외톨이 픽셀(잡티)을 주변 색으로 메운다. 대비가 큰 1px 은 남긴다 (빛, 눈).
  5. 공통 팔레트    모든 프레임의 색을 모아 팔레트 하나(기본 32색)를 만들고 다시 칠한다.
                   다른 시트와 팔레트를 맞추려면 --palette-in 으로 그 시트의 팔레트를 쓴다.
  6. 기준선 맞추기  행마다 땅에 선 프레임의 발바닥을 같은 줄에 맞춘다. 공중 프레임은 땅에서 뜬 높이를 지킨다.
  7. 시트로 합치기  같은 크기의 칸에 다시 깔고, 기준선·프레임별 정보를 JSON 으로 남긴다.
그 뒤에 Aseprite 등에서 손으로 다듬는다 (이 도구는 하지 않는다).

필요: pip install proper-pixel-art   (2.0.0 으로 확인)

사용 예:
    python tools/pixelize_sheet.py art/sprites/nx07_sheet_raw.png --cols 8 --rows 4 \\
        --out art/sprites/nx07_sheet_px.png --colors 32
출력:
    nx07_sheet_px.png          게임용 시트 (칸 크기는 --cell, 기본은 자동)
    nx07_sheet_px.json         칸 크기, 행별 기준선, 프레임별 배율·몸 높이, 팔레트
    nx07_sheet_px_palette.png  팔레트 (한 칸 = 한 색)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from process_sheet import despill, key_mask  # noqa: E402


# ───────── 1. 배경 제거 ─────────
def remove_background(rgb: np.ndarray, tol: int = 40) -> np.ndarray:
    """RGBA 를 돌려준다. 테두리가 마젠타면 색으로 지우고, 아니면 테두리에서 이어진 배경색 영역을 지운다."""
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(int)
    magenta = ((border[:, 0] - border[:, 1] > 50) & (border[:, 2] - border[:, 1] > 50)).mean() > 0.5
    if magenta:
        bg = key_mask(rgb)
        out = despill(rgb)
    else:
        # 테두리에서 가장 흔한 색 두 가지 (체크무늬면 두 색)
        q = (border // 16)
        keys, cnt = np.unique(q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2], return_counts=True)
        tops = keys[np.argsort(cnt)[::-1][:2]]
        cols = [border[(q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]) == t].mean(axis=0) for t in tops]
        near = np.zeros(rgb.shape[:2], bool)
        for c in cols:
            near |= np.abs(rgb.astype(int) - c).sum(axis=2) < tol
        n, lab = cv2.connectedComponents(near.astype(np.uint8), connectivity=4)
        edge_labels = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        bg = np.isin(lab, edge_labels[edge_labels > 0])
        out = rgb.copy()
    rgba = np.dstack([out, np.where(bg, 0, 255).astype(np.uint8)])
    rgba[bg, :3] = 0
    return rgba


# ───────── 2. 격자 복원 ─────────
def restore_grid(rgba: np.ndarray, pixel_width: int) -> np.ndarray:
    try:
        import proper_pixel_art as ppa
        from proper_pixel_art.config import PixelateConfig
    except ImportError:
        sys.exit("proper-pixel-art 가 없습니다: pip install proper-pixel-art")
    res = ppa.pixelate(Image.fromarray(rgba, "RGBA"), PixelateConfig(pixel_width=pixel_width))
    out = np.array(res.image.convert("RGBA"))
    out[out[..., 3] < 128] = 0
    out[out[..., 3] >= 128, 3] = 255
    return out


# ───────── 4. 프레임 정리 ─────────
def components(op: np.ndarray):
    n, lab, st, _ = cv2.connectedComponentsWithStats(op.astype(np.uint8), connectivity=8)
    return n, lab, st


def clean_frame(f: np.ndarray, speck_de: float = 18.0) -> tuple[np.ndarray, dict]:
    f = f.copy()
    op = f[..., 3] > 0
    info = {"bleed_px": 0, "speck_px": 0, "despeckled": 0}
    n, lab, st = components(op)
    if n > 1:
        areas = st[1:, cv2.CC_STAT_AREA]
        body = 1 + int(np.argmax(areas))
        h, w = op.shape
        for k in range(1, n):
            if k == body:
                continue
            x, y, cw, ch, a = st[k]
            touches = x == 0 or y == 0 or x + cw >= w or y + ch >= h
            if (touches and a < 0.15 * areas.max()) or a <= 2:
                f[lab == k] = 0
                info["bleed_px" if touches else "speck_px"] += int(a)
    # 잡티: 상하좌우 이웃이 모두 같은 색 c 이고, 자기 색이 c 와 비슷하면 c 로 메운다
    op = f[..., 3] > 0
    lab_img = cv2.cvtColor(f[..., :3], cv2.COLOR_RGB2LAB).astype(float)
    rgb = f[..., :3].astype(int)
    key = (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    key[~op] = -1
    H, W = op.shape
    pad = np.pad(key, 1, constant_values=-1)
    nb = np.stack([pad[0:H, 1:W + 1], pad[2:H + 2, 1:W + 1], pad[1:H + 1, 0:W], pad[1:H + 1, 2:W + 2]], axis=-1)
    same4 = (nb == nb[..., :1]).all(-1) & (nb[..., 0] >= 0)
    cand = op & same4 & (nb[..., 0] != key)
    ys, xs = np.nonzero(cand)
    for y, x in zip(ys, xs):
        yy, xx = (y - 1, x) if y > 0 else (y + 1, x)
        if np.linalg.norm(lab_img[y, x] - lab_img[yy, xx]) < speck_de:
            f[y, x, :3] = f[yy, xx, :3]
            info["despeckled"] += 1
    return f, info


# ───────── 5. 공통 팔레트 ─────────
def build_palette(frames: list[np.ndarray], n_colors: int) -> np.ndarray:
    """모든 프레임의 불투명 픽셀로 Lab 공간에서 k-means. 채도 높은 색(빛·이펙트)은 따로 몫을 둬서 묻히지 않게 한다."""
    px = np.concatenate([f[..., :3][f[..., 3] > 0] for f in frames]).reshape(-1, 1, 3)
    lab = cv2.cvtColor(px, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    chroma = np.hypot(lab[:, 1] - 128, lab[:, 2] - 128)
    accent = chroma > 28
    k_acc = min(max(6, n_colors // 4), int(accent.sum()))
    k_base = n_colors - k_acc
    centers = []
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    for sel, k in ((~accent, k_base), (accent, k_acc)):
        data = lab[sel]
        if k <= 0 or len(data) == 0:
            continue
        k = min(k, len(np.unique(data, axis=0)))
        cv2.setRNGSeed(7)
        _, _, c = cv2.kmeans(data, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
        centers.append(c)
    lab_c = np.concatenate(centers).reshape(-1, 1, 3).clip(0, 255).astype(np.uint8)
    return cv2.cvtColor(lab_c, cv2.COLOR_LAB2RGB).reshape(-1, 3)


def apply_palette(f: np.ndarray, pal: np.ndarray) -> np.ndarray:
    f = f.copy()
    op = f[..., 3] > 0
    lab = cv2.cvtColor(f[..., :3], cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    pl = cv2.cvtColor(pal.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    d = ((lab[:, None, :] - pl[None, :, :]) ** 2).sum(-1)
    idx = d.argmin(1).reshape(op.shape)
    f[..., :3] = np.where(op[..., None], pal[idx], 0)
    return f


# ───────── 6. 기준선 ─────────
def body_box(f: np.ndarray):
    op = f[..., 3] > 0
    n, lab, st = components(op)
    if n <= 1:
        return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _ = st[k]
    return int(x), int(y), int(w), int(h)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="AI 스프라이트 시트 → 도트 시트")
    ap.add_argument("src")
    ap.add_argument("--cols", type=int, required=True)
    ap.add_argument("--rows", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--colors", type=int, default=32, help="공통 팔레트 색 수 (기본 32)")
    ap.add_argument("--palette-in", help="다른 시트의 팔레트 PNG 를 그대로 쓴다 (같은 캐릭터의 시트끼리 색을 맞출 때)")
    ap.add_argument("--pixel", type=int, default=5, help="원본의 픽셀 한 칸 크기의 대략값 (격자 찾기의 출발점)")
    ap.add_argument("--cell", type=int, default=0, help="출력 칸 크기. 0 이면 자동 (8의 배수)")
    ap.add_argument("--margin", type=int, default=6, help="칸 아래쪽 여백 (기준선 = 칸 - 여백)")
    ap.add_argument("--ground-tol", type=int, default=3, help="행의 땅에서 이만큼(px) 안이면 땅에 선 프레임으로 본다")
    args = ap.parse_args()

    rgb = np.asarray(Image.open(args.src).convert("RGB"))
    H, W = rgb.shape[:2]

    rgba = remove_background(rgb)                                   # 1
    small = restore_grid(rgba, args.pixel)                          # 2
    sh, sw = small.shape[:2]
    cw, ch = sw / args.cols, sh / args.rows
    scale = (W / sw, H / sh)
    print(f"[2] 격자 복원: {W}x{H} → {sw}x{sh} (원본 {scale[0]:.2f} x {scale[1]:.2f}px 가 한 픽셀), 칸 {cw:.1f}x{ch:.1f}")

    frames, infos = [], []                                          # 3, 4
    for r in range(args.rows):
        for c in range(args.cols):
            f = small[round(r * ch):round((r + 1) * ch), round(c * cw):round((c + 1) * cw)]
            f, info = clean_frame(f)
            frames.append(f)
            infos.append(info)
    print(f"[4] 정리: 옆 칸 조각 {sum(i['bleed_px'] for i in infos)}px, 외딴 조각 {sum(i['speck_px'] for i in infos)}px 지움, "
          f"잡티 {sum(i['despeckled'] for i in infos)}px 메움")

    if args.palette_in:                                             # 5
        pal = np.array(Image.open(args.palette_in).convert("RGB")).reshape(-1, 3)
        pal = np.unique(pal, axis=0)
    else:
        pal = build_palette(frames, args.colors)
    frames = [apply_palette(f, pal) for f in frames]
    print(f"[5] 공통 팔레트 {len(pal)}색")

    boxes = [body_box(f) for f in frames]                           # 6
    need = max(max(f.shape[0], f.shape[1]) for f in frames)
    cell = args.cell or int(np.ceil((need + 4) / 8) * 8)
    base = cell - args.margin
    sheet = np.zeros((cell * args.rows, cell * args.cols, 4), np.uint8)
    meta = {"source": str(args.src), "cell": cell, "cols": args.cols, "rows": args.rows, "baseline": [], "frames": [],
            "raw_px_per_pixel": [round(scale[0], 3), round(scale[1], 3)],
            "palette": ["#%02X%02X%02X" % tuple(int(v) for v in p) for p in pal]}
    for r in range(args.rows):
        idx = [r * args.cols + c for c in range(args.cols)]
        bottoms = [boxes[i][1] + boxes[i][3] for i in idx if boxes[i]]
        ground = max(bottoms) if bottoms else 0
        meta["baseline"].append(base)
        for c, i in enumerate(idx):
            f, b = frames[i], boxes[i]
            fh, fw = f.shape[:2]
            if b is None:
                meta["frames"].append({"row": r, "col": c, "empty": True})
                continue
            bottom = b[1] + b[3]
            grounded = ground - bottom <= args.ground_tol
            dy = base - (bottom if grounded else ground)            # 땅에 선 프레임은 발바닥을, 공중 프레임은 행의 땅을 기준선에 맞춘다
            dx = (cell - fw) // 2
            y0, x0 = r * cell + dy, c * cell + dx
            sy0, sx0 = max(0, -dy), max(0, -dx)
            ey, ex = min(fh, cell - dy), min(fw, cell - dx)
            dst = sheet[y0 + sy0:y0 + ey, x0 + sx0:x0 + ex]
            src = f[sy0:ey, sx0:ex]
            m = src[..., 3] > 0
            dst[m] = src[m]
            lost = int((f[..., 3] > 0).sum() - m.sum())                 # 칸 밖으로 나가 잘린 불투명 픽셀
            meta["frames"].append({"row": r, "col": c, "grounded": bool(grounded), "body_h": b[3], "body_w": b[2],
                                   "clipped_px": lost})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(sheet).save(out)
    swatch = np.repeat(np.repeat(pal.reshape(1, -1, 3).astype(np.uint8), 8, 0), 8, 1)
    Image.fromarray(swatch).save(out.with_name(out.stem + "_palette.png"))
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    hs = np.array([m["body_h"] for m in meta["frames"] if not m.get("empty")])
    clipped = [f"{m['row']},{m['col']}({m['clipped_px']}px)" for m in meta["frames"] if m.get("clipped_px")]
    print(f"[6] 칸 {cell}px, 기준선 {base}, 몸 높이 {hs.min()}~{hs.max()}px" + (f", 칸 밖으로 잘린 프레임: {' '.join(clipped)}" if clipped else ""))
    print(f"[7] [saved] {out}  ({sheet.shape[1]}x{sheet.shape[0]})")


if __name__ == "__main__":
    main()
