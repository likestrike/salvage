"""캐릭터 설정화 묶음 (기획서 9.4.1).

캐릭터마다 일곱 장을 만든다: 정면 전신 · 측면 전신 · 후면 전신 · 얼굴 확대 · 신체 확대 ·
무기(없으면 소지품) 단독 · 주요 포즈. 정의는 art/concept/setting/setting.json 에 있다.

    python tools/setting_sheets.py guide                  # 기존 시트에서 세 시점을 잘라 참조 그림을 만든다
    python tools/setting_sheets.py gen nx07 turnaround    # fal.ai 로 한 장 뽑는다 (--dry-run 가능)
    python tools/setting_sheets.py split nx07             # 세 시점 그림을 정면 · 측면 · 후면으로 나눈다
    python tools/setting_sheets.py clean                  # 뽑은 뒤의 손질 (감정 표시 지우기, 반대쪽을 보는 포즈 뒤집기)
    python tools/setting_sheets.py overview nx07          # 일곱 장과 화풍 기준 그림을 한 장에 늘어놓는다

그림은 tools/fal_image.py --keep-style 로 뽑는다 (화풍 기준 그림 · 화풍 설명 · 고정 문구 · 모델이 붙는다).
참조 이미지의 순서: image 1 = 참조 그림(guide), image 2… = setting.json 의 refs, 그 뒤 extra_refs, 맨 뒤 = 화풍 기준 그림.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "art" / "concept" / "setting" / "setting.json"
ANCHORS = {"android": "art/style_anchor/android.png", "human": "art/style_anchor/human.png"}
WHITE = (255, 255, 255)


def load() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def ink_mask(a: np.ndarray, floor: int = 175, spread: int = 28) -> np.ndarray:
    """배경(밝고 채도 낮은 색)을 뺀 그림 부분. 시트의 연한 바닥 그림자도 배경으로 본다."""
    r, g, b = (a[..., i].astype(int) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    return ~((mn > floor) & (mx - mn < spread))


def figure_mask(a: np.ndarray) -> np.ndarray:
    """그림 한 개의 자리. 테두리에서 이어진 밝은 영역(배경 · 바닥 그림자)을 빼고, 남은 것 중 가장 큰 덩어리만 남긴다.

    외곽선 안쪽의 밝은 색(은발, 흰 장갑, 흰 가운)은 테두리와 이어져 있지 않으므로 지워지지 않는다.
    """
    import cv2

    light = (~ink_mask(a)).astype(np.uint8)
    n, lab = cv2.connectedComponents(light, connectivity=4)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    outside = np.isin(lab, edge[edge > 0])
    solid = (~outside).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(solid, connectivity=8)
    if n <= 1:
        return solid.astype(bool)
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == biggest


def bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    cols, rows = np.where(mask.sum(axis=0) > 2)[0], np.where(mask.sum(axis=1) > 2)[0]
    return int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1


# ---------------------------------------------------------------- guide

def cmd_guide(cfg: dict, names: list[str]) -> None:
    """기존 시트의 정면 · 측면 · 후면을 잘라 한 줄로 놓는다. 측면은 오른쪽을 보게 뒤집는다 (게임의 방향)."""
    for name in names:
        ch = cfg["characters"][name]
        sheet = Image.open(ROOT / ch["sheet"]).convert("RGB")
        xs, (y0, y1) = ch["views"]["x"], ch["views"]["y"]
        crops = []
        for i in range(3):
            c = sheet.crop((xs[i], y0, xs[i + 1], y1))
            if i == 1:
                c = c.transpose(Image.FLIP_LEFT_RIGHT)
            a = np.asarray(c).copy()
            m = figure_mask(a)
            x0, _, x1, _ = bbox(m)
            a[~m] = 255  # 바깥 배경 · 바닥 그림자 · 옆 칸의 글자를 흰색으로. 그림 안쪽의 밝은 색은 그대로 둔다
            crops.append(Image.fromarray(a).crop((x0, 0, x1, c.height)))
        gap, pad = 150, 90
        w = sum(c.width for c in crops) + gap * 2 + pad * 2
        out = Image.new("RGB", (w, crops[0].height + pad * 2), WHITE)
        x = pad
        for c in crops:
            out.paste(c, (x, pad))
            x += c.width + gap
        target = ROOT / cfg["prompts"] / f"guide_{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        out.save(target)
        print(f"[guide] {target.relative_to(ROOT)} {out.size}")


# ---------------------------------------------------------------- gen

def cmd_gen(cfg: dict, name: str, kind: str, dry: bool, suffix: str) -> None:
    ch, pdir = cfg["characters"][name], ROOT / cfg["prompts"]
    prompts = [pdir / f"{name}_design.txt", pdir / f"{name}_{kind}.txt", pdir / cfg["kinds"][kind]["layout"]]
    refs = [pdir / f"guide_{name}.png"] + [ROOT / r for r in ch.get("refs", [])]
    refs += [ROOT / r for r in ch.get("extra_refs", {}).get(kind, [])]
    out = ROOT / cfg["out"] / name / ch["files"][kind]
    if suffix:
        out = out.with_name(f"{out.stem}_{suffix}{out.suffix}")
    cmd = [sys.executable, "-X", "utf8", str(ROOT / "tools" / "fal_image.py"), "--keep-style", ch["style"]]
    for p in prompts:
        cmd += ["--prompt-file", str(p)]
    for r in refs:
        cmd += ["--ref", str(r)]
    cmd += ["--out", str(out)]
    if dry:
        cmd.append("--dry-run")
    print(f"[gen] {name} {kind} -> {out.relative_to(ROOT)}", flush=True)
    sys.exit(subprocess.call(cmd))


# ---------------------------------------------------------------- split

def cmd_split(cfg: dict, names: list[str]) -> None:
    """세 시점 그림을 세 장으로 나눈다. 세 장은 같은 크기의 캔버스에 같은 배율 · 같은 발바닥 줄로 놓인다."""
    for name in names:
        ch = cfg["characters"][name]
        folder = ROOT / cfg["out"] / name
        src = Image.open(folder / ch["files"]["turnaround"]).convert("RGB")
        a = np.asarray(src)
        m = ink_mask(a, floor=228, spread=22)
        col = m.sum(axis=0)
        empty = col <= 2
        runs, start = [], None
        for i, e in enumerate(empty):
            if e and start is None:
                start = i
            if not e and start is not None:
                runs.append((start, i))
                start = None
        inner = sorted((r for r in runs if r[0] > 0), key=lambda r: r[1] - r[0], reverse=True)[:2]
        if len(inner) < 2 or min(r[1] - r[0] for r in inner) < 12:
            cuts = [src.width // 3, src.width * 2 // 3]
            print(f"[split] {name}: 그림 사이의 빈 줄을 찾지 못해 3등분했다. 눈으로 확인할 것")
        else:
            cuts = sorted((r[0] + r[1]) // 2 for r in inner)
        edges = [0] + cuts + [src.width]
        boxes = []
        for i in range(3):
            x0, y0, x1, y1 = bbox(m[:, edges[i]:edges[i + 1]])
            boxes.append((x0 + edges[i], y0, x1 + edges[i], y1))
        top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
        pad = 80
        cw = max(b[2] - b[0] for b in boxes) + pad * 2
        chh = (bottom - top) + pad * 2
        for (x0, _, x1, _), fname in zip(boxes, cfg["split"]):
            piece = src.crop((x0, top, x1, bottom))
            canvas = Image.new("RGB", (cw, chh), WHITE)
            canvas.paste(piece, ((cw - piece.width) // 2, pad))
            canvas.save(folder / fname)
            print(f"[split] {name}/{fname} {canvas.size}  키 {bottom - top}px")
        heights = [b[3] - b[1] for b in boxes]
        print(f"[split] {name}: 세 그림의 키 {heights} (차이 {max(heights) - min(heights)}px), "
              f"발바닥 줄 {[b[3] for b in boxes]}")


# ---------------------------------------------------------------- clean

def cmd_clean(cfg: dict, names: list[str]) -> None:
    """뽑은 뒤의 손질 (setting.json 의 clean). 처음 뽑힌 그림은 *_raw.png 로 남기고, 늘 거기서 다시 만든다.

    flip  : 상자 안을 좌우로 뒤집는다 (한 포즈만 반대쪽을 보게 그려졌을 때).
    paste : 다시 뽑은 그림(from)의 같은 상자를 옮겨 넣는다 (한 포즈만 다시 뽑은 것으로 바꿀 때).
    erase : 상자 안에서 캐릭터와 떨어져 있는 작은 조각(감정 표시 따위)을 흰색으로 지운다. 큰 덩어리는 건드리지 않는다.
    """
    import cv2

    for name in names:
        ch = cfg["characters"][name]
        folder = ROOT / cfg["out"] / name
        for fname, ops in ch.get("clean", {}).items():
            path = folder / fname
            raw = path.with_name(f"{path.stem}_raw{path.suffix}")
            if not raw.exists():
                raw.write_bytes(path.read_bytes())
            a = np.asarray(Image.open(raw).convert("RGB")).copy()
            for op in ops:
                x0, y0, x1, y1 = op["box"]
                if op["op"] == "flip":
                    a[y0:y1, x0:x1] = a[y0:y1, x0:x1][:, ::-1]
                elif op["op"] == "paste":
                    src = np.asarray(Image.open(folder / op["from"]).convert("RGB"))
                    dy = op.get("down", 0)  # 발바닥 줄을 맞추려고 아래로 내리는 양
                    region = a[y0:y1, x0:x1]
                    region[:] = np.median(region[region.min(axis=2) > 245], axis=0).astype(np.uint8)
                    region[dy:] = src[y0:y1 - dy, x0:x1]
                elif op["op"] == "erase":
                    ink = (a.min(axis=2) < 246).astype(np.uint8)
                    n, lab, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
                    small = np.zeros(n, bool)
                    small[1:] = stats[1:, cv2.CC_STAT_AREA] < op.get("max_area", 12000)
                    sel = np.zeros(ink.shape, np.uint8)
                    sel[y0:y1, x0:x1] = small[lab[y0:y1, x0:x1]]
                    sel = cv2.dilate(sel, np.ones((7, 7), np.uint8)).astype(bool)
                    sel &= ~np.isin(lab, np.where(~small)[0][1:])  # 큰 덩어리의 픽셀은 남긴다
                    paper = a[y0:y1, x0:x1][ink[y0:y1, x0:x1] == 0]
                    a[sel] = np.median(paper, axis=0).astype(np.uint8) if len(paper) else 255  # 둘레의 배경색으로 메운다
                    print(f"[clean] {name}/{fname} erase {op['box']}: {int(sel.sum())}px")
                    continue
                print(f"[clean] {name}/{fname} {op['op']} {op['box']}")
            Image.fromarray(a).save(path)


# ---------------------------------------------------------------- overview

def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for f in (("malgunbd.ttf" if bold else "malgun.ttf"), "malgun.ttf", "gulim.ttc"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit(im: Image.Image, w: int, h: int) -> Image.Image:
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def cmd_overview(cfg: dict, names: list[str]) -> None:
    """일곱 장을 한 장에 늘어놓고, 오른쪽 위에 화풍 기준 그림을 함께 놓는다 (나란히 보고 그림체를 확인한다)."""
    for name in names:
        ch = cfg["characters"][name]
        folder = ROOT / cfg["out"] / name
        W, M, LAB = 3000, 40, 56
        row1_h = 1000
        cell_w = (W - M * 3) // 2
        cell_h = round(cell_w * 2 / 3)
        H = 110 + (LAB + row1_h + M) + (LAB + cell_h + M) * 2
        page = Image.new("RGB", (W, H), (244, 244, 246))
        d = ImageDraw.Draw(page)
        d.text((M, 28), f"{ch['name']} — 설정화 묶음", font=font(52, True), fill=(30, 32, 40))

        y = 110
        views = [Image.open(folder / f).convert("RGB") for f in cfg["split"]]
        anchor = Image.open(ROOT / ANCHORS[ch["style"]]).convert("RGB")
        anchor_t = fit(anchor, 1400, row1_h)
        view_w = (W - M * 5 - anchor_t.width) // 3
        x = M
        for im, lab, fname in zip(views, cfg["split_labels"], cfg["split"]):
            t = fit(im, view_w, row1_h)
            d.text((x, y), f"{lab}  ·  {fname}", font=font(30, True), fill=(30, 32, 40))
            page.paste(Image.new("RGB", (view_w, row1_h), WHITE), (x, y + LAB))
            page.paste(t, (x + (view_w - t.width) // 2, y + LAB + (row1_h - t.height) // 2))
            x += view_w + M
        d.text((x, y), "화풍 기준 그림 (비교용)", font=font(30, True), fill=(150, 60, 40))
        page.paste(anchor_t, (x, y + LAB))

        y += LAB + row1_h + M
        kinds = ["face", "body", "items", "poses"]
        for i, kind in enumerate(kinds):
            cx, cy = M + (cell_w + M) * (i % 2), y + (LAB + cell_h + M) * (i // 2)
            lab = ch.get("items_label") if kind == "items" else cfg["kinds"][kind]["label"]
            d.text((cx, cy), f"{lab}  ·  {ch['files'][kind]}", font=font(30, True), fill=(30, 32, 40))
            path = folder / ch["files"][kind]
            page.paste(Image.new("RGB", (cell_w, cell_h), WHITE), (cx, cy + LAB))
            if path.exists():
                t = fit(Image.open(path).convert("RGB"), cell_w, cell_h)
                page.paste(t, (cx + (cell_w - t.width) // 2, cy + LAB + (cell_h - t.height) // 2))
            else:
                d.text((cx + 40, cy + LAB + 40), "(아직 없음)", font=font(36), fill=(160, 160, 160))
        target = folder / "overview.png"
        page.save(target)
        print(f"[overview] {target.relative_to(ROOT)} {page.size}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = load()
    everyone = list(cfg["characters"])
    ap = argparse.ArgumentParser(description="캐릭터 설정화 묶음")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("guide", "split", "clean", "overview"):
        p = sub.add_parser(c)
        p.add_argument("names", nargs="*", choices=everyone + [[]], default=[])
    g = sub.add_parser("gen")
    g.add_argument("name", choices=everyone)
    g.add_argument("kind", choices=list(cfg["kinds"]))
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--suffix", default="", help="다시 뽑을 때 파일 이름 뒤에 붙인다 (예: v2). 기존 그림을 덮어쓰지 않는다")
    args = ap.parse_args()
    if args.cmd == "gen":
        cmd_gen(cfg, args.name, args.kind, args.dry_run, args.suffix)
    else:
        names = args.names or everyone
        {"guide": cmd_guide, "split": cmd_split, "clean": cmd_clean, "overview": cmd_overview}[args.cmd](cfg, names)


if __name__ == "__main__":
    main()
