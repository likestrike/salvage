"""픽셀 애니메이션 만들기 · 검사 · 내보내기 (기획서 9.11.6, 캐릭터 픽셀 파이프라인의 애니메이션 단계).

    python -X utf8 tools/pixel_anim.py build art/characters/nx07/anim          # 모든 동작: 프레임 · 검사 · 시트 · GIF
    python -X utf8 tools/pixel_anim.py build art/characters/nx07/anim idle     # 한 동작만
    python -X utf8 tools/pixel_anim.py build art/characters/nx07/anim --out <폴더>   # 다른 자리에 만든다 (재현 검증)
    python -X utf8 tools/pixel_anim.py preview art/characters/<id>/anim [동작…]  # 기획자가 보는 비교 그림 · 게임 화면 GIF
    (보통은 tools/pixpipe.py anim <id> 가 build 와 preview 를 함께 부른다)

원본은 표다: <anim>/rig.json (마스터에서 잘라 쓰는 부위 · 다리와 팔의 자세 표 · 층의 표)과
<anim>/<동작>/timeline.json (프레임마다 무엇을 어디에 두는가 · 시간). 이 도구가 프레임 PNG(1배율, 고정 캔버스)를 만들고,
시트와 GIF 는 그 프레임에서 내보낸다 (시트는 출력물이다).

벌(variant): body = 층 없음. 층이 있으면(rig.json 의 layer 또는 scarf) 그 층을 얹은 벌이 하나 더 나온다 (NX-07: scarf = 스카프 있음).
캐릭터에 묶인 이름(id · 벌의 이름 · 층의 이름)은 rig.json 에 있다.

규칙
- 새 색을 만들지 않는다. body 는 마스터의 색만, 층을 얹은 벌은 층 마스터의 색만 쓴다.
- 머리 · 몸통 · 주포 팔은 마스터의 칸을 칸 단위로 옮기기만 한다. 줄을 눌러 없애지 않는다.
- 다리 · 앞쪽 팔 · 층의 끝은 rig.json 의 표에서 고른다 (글자 하나 = 칸 하나).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from pxl import pack_sheet  # noqa: E402

DARK = (24, 26, 36)
FONT = "C:/Windows/Fonts/malgun.ttf"
FONT_B = "C:/Windows/Fonts/malgunbd.ttf"


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT.resolve()).as_posix()


def hexrgb(h: str) -> tuple[int, int, int]:
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(n: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_B if bold else FONT, n)


# ---------------------------------------------------------------- 재료

class Rig:
    def __init__(self, folder: Path, master: Path | None = None, master_layer: Path | None = None):
        """master · master_layer 를 주면 rig.json 의 경로 대신 그 그림을 쓴다 (재현 검증)."""
        self.folder = folder
        self.d = json.loads((folder / "rig.json").read_text(encoding="utf-8"))
        d = self.d
        self.id = d.get("id") or folder.parent.name
        self.master = np.array(Image.open(master or ROOT / d["master"]).convert("RGBA"))
        # 층: 새 이름(layer · master_layer)과 NX-07 의 이름(scarf · master_scarf)을 함께 읽는다
        self.layer = d.get("layer") or d.get("scarf")
        self.layer_name = d.get("layer_name") or ("scarf" if "scarf" in d else "layer")
        lp = master_layer or (ROOT / (d.get("master_layer") or d.get("master_scarf")) if self.layer else None)
        self.master_scarf = np.array(Image.open(lp).convert("RGBA")) if self.layer else None
        self.layer_pad = d.get("master_layer_pad_left", d.get("master_scarf_pad_left", 0))
        self.master_tail = (self.layer or {}).get("master_tail")  # 층 마스터와 같은 모양의 끝 (그 프레임은 층 마스터와 픽셀까지 같아야 한다)
        self.variants = ["body"] + ([self.layer_name] if self.layer else [])
        self.labels = d.get("variants") or {}
        self.short = d.get("variant_short") or {}
        self.W, self.H = d["canvas"]
        self.PX, self.PY = d["place"]
        self.anchor = tuple(d["anchor"])
        self.keys = {k: hexrgb(v) for k, v in d["keys"].items()}
        self.legs_top = d["parts"]["legs"]["rows"][0]
        self.parts = self._cut()

    def _cut(self) -> dict[str, dict]:
        """마스터에서 부위를 자른다. 부위 = {(x, y): (r, g, b)} (마스터 좌표)."""
        m = self.master
        h, w = m.shape[:2]
        allc = {(x, y): tuple(int(v) for v in m[y, x, :3]) for y in range(h) for x in range(w) if m[y, x, 3] > 0}
        P = self.d["parts"]
        if "near_arm" in P:
            x0, y0, x1, y1 = P["near_arm"]["rect"]
        else:
            x0, y0, x1, y1 = -1, -1, -2, -2  # 앞쪽 팔을 따로 두지 않는 캐릭터
        arm = {k: v for k, v in allc.items() if x0 <= k[0] <= x1 and y0 <= k[1] <= y1}
        r0, r1 = P["head"]["rows"]
        head = {k: v for k, v in allc.items() if r0 <= k[1] <= r1}
        r0, r1 = P["upper"]["rows"]
        upper = {k: v for k, v in allc.items() if r0 <= k[1] <= r1 and k not in arm}
        r0, r1 = P["legs"]["rows"]
        legs = {k: v for k, v in allc.items() if r0 <= k[1] <= r1}
        assert len(head) + len(arm) + len(upper) + len(legs) == len(allc), "부위가 마스터를 빠짐없이 나누지 못했다"
        return {"head": head, "near_arm": arm, "upper": upper, "legs": legs}

    def table(self, rows, dx=0, dy=0, shade: dict | None = None) -> dict:
        """표 → 칸. 두 형식: [[줄, 시작 x, "칸들"], …] 또는 {"x0": …, "y0": …, "grid": ["칸들", …]} (줄마다 x0 에서 시작)."""
        if isinstance(rows, dict):
            rows = [[rows.get("y0", 0) + j, rows["x0"], s] for j, s in enumerate(rows["grid"])]
        out = {}
        for y, x, s in rows:
            for i, ch in enumerate(s):
                if ch == ".":
                    continue
                if ch == "_":  # 지운다 (덧칠 patches 에서만 쓴다: 그 칸을 비운다)
                    out[(x + i + dx, y + dy)] = None
                    continue
                if shade:
                    ch = shade.get(ch, ch)
                out[(x + i + dx, y + dy)] = self.keys[ch]
        return out

    def fixed_cells(self) -> dict | None:
        """바뀌면 안 되는 칸 = 머리 + 몸통(앞쪽 팔 제외) 가운데 rig.json 의 fixed.free 사각형 밖. fixed 가 없으면 None (NX-07: 전과 같은 검사)."""
        F = self.d.get("fixed")
        if not F:
            return None
        rects = [r["rect"] for r in F.get("free", [])]
        cells = {**self.parts["head"], **self.parts["upper"]}
        return {k: v for k, v in cells.items() if not any(x0 <= k[0] <= x1 and y0 <= k[1] <= y1 for x0, y0, x1, y1 in rects)}

    def palette(self, scarf: bool) -> set:
        a = self.master_scarf if (scarf and self.layer) else self.master
        return {tuple(int(v) for v in c) for c in a[a[..., 3] > 0][:, :3]}


def shift(cells: dict, dx: int, dy: int) -> dict:
    return {(x + dx, y + dy): c for (x, y), c in cells.items()}


# ---------------------------------------------------------------- 프레임 짜기

def compose(rig: Rig, tl: dict, f: dict) -> tuple[np.ndarray, np.ndarray, dict, dict]:
    """한 프레임: (body RGBA, 스카프 층 RGBA, 칸마다 어느 층이 그렸는가, 층별 칸).
    좌표는 마스터 좌표로 짜고 마지막에 캔버스로 옮긴다."""
    ux, uy = f["upper"]
    ax, ay = f.get("arm_off", [0, 0])
    layers: list[tuple[str, dict]] = []
    if f.get("legs") == "master":
        layers.append(("legs", shift(rig.parts["legs"], ux * 0, 0)))
    else:
        hips = tl["hips"]
        lp = rig.d["leg_poses"]
        far = rig.table(lp[f["far"]], hips["far"], rig.legs_top + uy, rig.d["shade_far"])
        layers.append(("far_leg", far))
    up = shift(rig.parts["upper"], ux, uy)
    pose = rig.d["arm_poses"][f["arm"]]
    if pose.get("fill"):
        up.update(rig.table(pose["fill"], ux, uy))
    layers.append(("upper", up))
    layers.append(("head", shift(rig.parts["head"], ux, uy)))

    def patch_layers(z: str) -> None:
        # 덧칠 (rig.json 의 patches): 머리카락 끝 · 옷자락처럼 몇 칸만 고쳐 찍는 것. follow 가 upper 면 윗몸과 함께 옮긴다. '_' = 지움
        # z: "top"(기본, 모든 것 위) · "mid"(먼 쪽 다리 · 윗몸 위, 가까운 쪽 다리 · 앞쪽 팔 아래)
        for pn in f.get("patch", []):
            P = rig.d["patches"][pn]
            if P.get("z", "top") != z:
                continue
            dx, dy = (ux, uy) if P.get("follow", "upper") == "upper" else (0, 0)
            layers.append(("patch", rig.table(P["cells"], dx, dy)))

    patch_layers("mid")
    if f.get("legs") != "master":
        hips = tl["hips"]
        lp = rig.d["leg_poses"]
        layers.append(("near_leg", rig.table(lp[f["near"]], hips["near"], rig.legs_top + uy)))
    if pose.get("from_master"):
        arm = shift(rig.parts["near_arm"], ax, ay)
    else:
        arm = rig.table(pose["cells"], ax, ay)
    layers.append(("near_arm", arm))
    patch_layers("top")

    body = np.zeros((rig.H, rig.W, 4), np.uint8)
    owner = np.full((rig.H, rig.W), "", object)
    for name, cells in layers:
        for (x, y), c in cells.items():
            X, Y = x + rig.PX, y + rig.PY
            assert 0 <= X < rig.W and 0 <= Y < rig.H, f"캔버스 밖: {name} ({x}, {y})"
            if c is None:
                body[Y, X] = 0
                owner[Y, X] = ""
                continue
            body[Y, X] = c + (255,)
            owner[Y, X] = name
    layer = np.zeros_like(body)
    if rig.layer:
        sc = rig.layer
        scells = rig.table(sc["wrap"], ux, uy)
        scells.update(rig.table(sc["tails"][f["tail"]]["cells"], ux, uy))
        for (x, y), c in scells.items():
            layer[y + rig.PY, x + rig.PX] = c + (255,)
    return body, layer, owner, dict(layers)


def put_on(body: np.ndarray, layer: np.ndarray) -> np.ndarray:
    out = body.copy()
    m = layer[..., 3] > 0
    out[m] = layer[m]
    return out


# ---------------------------------------------------------------- 검사

def checks(rig: Rig, tl: dict, frames: list[dict]) -> dict:
    res = {"frames": [], "summary": {}}
    pal_b, pal_s = rig.palette(False), rig.palette(True)
    H, W = rig.H, rig.W
    sole = rig.anchor[1]
    head0 = rig.parts["head"]
    upper0 = rig.parts["upper"]
    fixed0 = rig.fixed_cells()
    LN = rig.layer_name
    wrap0 = rig.table(rig.layer["wrap"]) if rig.layer else {}
    V = rig.variants  # ["body"] 또는 ["body", 층 이름]
    prev = {v: None for v in V}
    changes = {v: [] for v in V}
    for i, fr in enumerate(frames):
        f, body, layer, comp, owner = fr["spec"], fr["body"], fr["layer"], fr.get(LN, fr["body"]), fr["owner"]
        ux, uy = f["upper"]
        r: dict = {"i": i}
        for nm, a, pal in (("body", body, pal_b), (LN, comp, pal_s))[:len(V)]:
            op = a[..., 3] > 0
            cols = {tuple(int(v) for v in c) for c in a[op][:, :3]}
            r[f"{nm}_off_palette"] = len(cols - pal)
            r[f"{nm}_semi"] = int(((a[..., 3] > 0) & (a[..., 3] < 255)).sum())
            r[f"{nm}_colors"] = len(cols)
            ys = np.where(op.any(1))[0]
            r[f"{nm}_lowest_row"] = int(ys.max())
            r[f"{nm}_top_row"] = int(ys.min())
        r["canvas"] = [W, H]
        r["sole_ok"] = r["body_lowest_row"] == sole - 1
        # 머리: 마스터의 머리 칸이 옮긴 자리에 그대로 있는가 (다른 층에 가렸는가)
        same = hidden = 0
        for (x, y), c in head0.items():
            X, Y = x + ux + rig.PX, y + uy + rig.PY
            if tuple(int(v) for v in body[Y, X, :3]) == c and body[Y, X, 3] == 255:
                same += 1
            elif owner[Y, X] not in ("head", ""):
                hidden += 1
        r["head"] = {"cells": len(head0), "same": same, "hidden": hidden, "other": len(head0) - same - hidden}
        same = hidden = 0
        by: dict = {}
        for (x, y), c in upper0.items():
            X, Y = x + ux + rig.PX, y + uy + rig.PY
            if tuple(int(v) for v in body[Y, X, :3]) == c and body[Y, X, 3] == 255:
                same += 1
            else:
                hidden += 1
                by[owner[Y, X]] = by.get(owner[Y, X], 0) + 1
        r["upper"] = {"cells": len(upper0), "same": same, "covered": hidden, "covered_by": by}
        if fixed0 is not None:  # 바뀌면 안 되는 칸이 모두 마스터와 같은가. 앞쪽 팔(미리네: 단말기를 든 손)이 앞에서 가린 칸만 따로 세고 허용한다
            ok = arm_cov = 0
            for (x, y), c in fixed0.items():
                X, Y = x + ux + rig.PX, y + uy + rig.PY
                if tuple(int(v) for v in body[Y, X, :3]) == c and body[Y, X, 3] == 255:
                    ok += 1
                elif owner[Y, X] == "near_arm":
                    arm_cov += 1
            r["fixed"] = {"cells": len(fixed0), "same": ok, "covered_by_near_arm": arm_cov, "changed": len(fixed0) - ok - arm_cov}
        # 층: 층을 빼면 body 와 한 칸도 다르지 않은가 · 고정 부분(NX-07: 목에 감긴 부분)이 층 마스터와 같은가
        if rig.layer:
            m = layer[..., 3] == 0
            r[f"{LN}_off_equals_body"] = int((comp[m] != body[m]).any(-1).sum()) == 0
            r[f"{LN}_layer_cells"] = int((~m).sum())
            ok = 0
            for (x, y), c in wrap0.items():
                X, Y = x + ux + rig.PX, y + uy + rig.PY
                ok += tuple(int(v) for v in comp[Y, X, :3]) == c
            r[f"{LN}_wrap_same"] = f"{ok}/{len(wrap0)}"
        # 마스터 그대로인 프레임(옮김 0 · 다리 마스터 · 팔이 마스터 그대로)은 마스터와 픽셀까지 같아야 한다
        arm_master = rig.d["arm_poses"][f["arm"]].get("from_master")
        if (f.get("legs") == "master" and list(f["upper"]) == [0, 0] and list(f.get("arm_off", [0, 0])) == [0, 0] and arm_master
                and not f.get("patch") and not rig.d["arm_poses"][f["arm"]].get("fill")):
            mb = np.zeros_like(body)
            hb, wb = rig.master.shape[:2]
            mb[rig.PY:rig.PY + hb, rig.PX:rig.PX + wb] = rig.master
            r["equals_master_base"] = bool((body == mb).all())
            if rig.layer and f.get("tail") == rig.master_tail:
                pad = rig.layer_pad
                ms = np.zeros_like(body)
                hs, ws = rig.master_scarf.shape[:2]
                ms[rig.PY:rig.PY + hs, rig.PX - pad:rig.PX - pad + ws] = rig.master_scarf
                r[f"equals_master_{LN}"] = bool((comp == ms).all())
        for nm, a in (("body", body), (LN, comp))[:len(V)]:
            if prev[nm] is not None:
                p = prev[nm]
                union = (a[..., 3] > 0) | (p[..., 3] > 0)
                diff = (a != p).any(-1) & union
                changes[nm].append(round(float(diff.sum()) / float(union.sum()), 3))
            prev[nm] = a
        res["frames"].append(r)
    if tl.get("loop") and len(frames) > 1:
        for nm in V:
            a, p = frames[0][nm], frames[-1][nm]
            union = (a[..., 3] > 0) | (p[..., 3] > 0)
            changes[nm].append(round(float(((a != p).any(-1) & union).sum()) / float(union.sum()), 3))
    res["neighbor_change"] = changes
    # 발 미끄러짐 (달리기): 딛고 있는 발의 앞끝 x 가 프레임마다 얼마나 뒤로 가는가
    if "speed" in tl:
        slips = []
        foot = []
        for i, fr in enumerate(frames):
            owner = fr["owner"]
            rowY = sole - 1
            row = {}
            for name in ("near_leg", "far_leg"):
                xs = [x for x in range(W) if owner[rowY, x] == name]
                if xs:
                    row[name] = max(xs)
            foot.append(row)
        for i in range(len(frames)):
            j = (i + 1) % len(frames)
            if not tl.get("loop") and j == 0:
                break
            for name in ("near_leg", "far_leg"):
                if name in foot[i] and name in foot[j]:
                    d = foot[j][name] - foot[i][name]
                    want = -tl["speed"] * frames[i]["spec"]["ticks"]
                    slips.append({"from": i, "to": j, "leg": name, "moved": d, "want": want, "slip": round(d - want, 2)})
        res["foot_toe_x"] = foot
        res["foot_slip"] = slips
    S = res["summary"]
    S["frames"] = len(frames)
    S["ticks"] = [fr["spec"]["ticks"] for fr in frames]
    S["off_palette"] = sum(r[f"{v}_off_palette"] for r in res["frames"] for v in V)
    S["semi_transparent"] = sum(r[f"{v}_semi"] for r in res["frames"] for v in V)
    S["sole_fixed"] = all(r["sole_ok"] for r in res["frames"])
    S["head_same_all"] = all(r["head"]["same"] == r["head"]["cells"] for r in res["frames"])
    S["upper_same_min"] = min(r["upper"]["same"] for r in res["frames"])
    S["upper_cells"] = len(upper0)
    if rig.layer:
        S[f"{LN}_off_equals_body"] = all(r[f"{LN}_off_equals_body"] for r in res["frames"])
    S["neighbor_change_mean"] = {k: round(float(np.mean(v)), 3) if v else 0 for k, v in changes.items()}
    if "foot_slip" in res:
        S["foot_slip_max"] = max((abs(s["slip"]) for s in res["foot_slip"]), default=None)
    eq = [r[k] for r in res["frames"] for k in ("equals_master_base", f"equals_master_{LN}") if k in r]
    S["master_frames_identical"] = f"{sum(eq)}/{len(eq)}" if eq else "해당 없음"
    if fixed0 is not None:
        S["fixed_cells"] = len(fixed0)
        S["fixed_same_min"] = min(r["fixed"]["same"] for r in res["frames"])
        S["fixed_changed_max"] = max(r["fixed"]["changed"] for r in res["frames"])
        S["fixed_covered_by_near_arm_max"] = max(r["fixed"]["covered_by_near_arm"] for r in res["frames"])
        S["fixed_same_all"] = S["fixed_changed_max"] == 0
    S["pass"] = (S["off_palette"] == 0 and S["semi_transparent"] == 0 and S["sole_fixed"] and S["head_same_all"]
                 and S.get(f"{LN}_off_equals_body", True) and all(eq) and S.get("fixed_same_all", True))
    return res


# ---------------------------------------------------------------- 내보내기

def gif(frames: list[np.ndarray], ticks: list[int], path: Path, z: int = 8, bg=DARK) -> None:
    imgs = []
    for a in frames:
        b = Image.new("RGBA", (a.shape[1], a.shape[0]), bg + (255,))
        b.alpha_composite(Image.fromarray(a, "RGBA"))
        imgs.append(b.convert("RGB").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST))
    durs = [max(20, round(t * 1000 / 60)) for t in ticks]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=1)


def strip(rows: list[tuple[str, list[np.ndarray]]], path: Path, sole: int, z: int = 8) -> None:
    """프레임을 가로로 늘어놓은 확인용 그림 (발바닥 줄 표시)."""
    h, w = rows[0][1][0].shape[:2]
    n = max(len(fs) for _, fs in rows)
    gap, lab = 8, 150
    img = Image.new("RGB", (lab + n * (w * z + gap), len(rows) * (h * z + gap) + 30), DARK)
    d = ImageDraw.Draw(img)
    for j in range(n):
        d.text((lab + j * (w * z + gap) + 4, 6), str(j), font=font(16), fill=(200, 200, 210))
    for i, (name, fs) in enumerate(rows):
        y = 30 + i * (h * z + gap)
        d.text((6, y + 8), name, font=font(16, True), fill=(220, 220, 230))
        for j, a in enumerate(fs):
            x = lab + j * (w * z + gap)
            cell = Image.new("RGBA", (w, h), (34, 37, 50, 255))
            cell.alpha_composite(Image.fromarray(a, "RGBA"))
            img.paste(cell.convert("RGB").resize((w * z, h * z), Image.NEAREST), (x, y))
            d.line([(x, y + sole * z), (x + w * z, y + sole * z)], fill=(110, 70, 70))
    img.save(path)


def make_frames(rig: Rig, tl: dict) -> list[dict]:
    frames = []
    for f in tl["frames"]:
        body, layer, owner, _ = compose(rig, tl, f)
        fr = {"spec": f, "body": body, "layer": layer, "owner": owner}
        if rig.layer:
            fr[rig.layer_name] = put_on(body, layer)
        frames.append(fr)
    return frames


def build_one(rig: Rig, name: str, out_dir: Path | None = None) -> dict:
    """한 동작. 표는 rig.folder/<동작>/timeline.json 에서 읽고, 결과는 (out_dir 또는 rig.folder)/<동작>/ 에 쓴다."""
    src = rig.folder / name
    d = (out_dir or rig.folder) / name
    tl = json.loads((src / "timeline.json").read_text(encoding="utf-8"))
    frames = make_frames(rig, tl)
    LN = rig.layer_name
    fd, od = d / "frames", d / "out"
    fd.mkdir(parents=True, exist_ok=True)
    od.mkdir(parents=True, exist_ok=True)
    for old in fd.glob("*.png"):
        old.unlink()
    for i, fr in enumerate(frames):
        Image.fromarray(fr["body"], "RGBA").save(fd / f"body_{i:02d}.png")
        if rig.layer:
            Image.fromarray(fr["layer"], "RGBA").save(fd / f"{LN}_layer_{i:02d}.png")
            Image.fromarray(fr[LN], "RGBA").save(fd / f"{LN}_{i:02d}.png")
    res = checks(rig, tl, frames)
    ticks = [fr["spec"]["ticks"] for fr in frames]
    stem = f"{rig.id}_{name}"
    outs = {}
    for v in rig.variants:
        ims = [Image.fromarray(fr[v], "RGBA") for fr in frames]
        sheet, meta = pack_sheet({name: ims}, rig.W, rig.H, pad=0)
        sheet.save(od / f"{stem}_{v}.png")
        meta["animations"][name].pop("fps", None)
        meta["animations"][name].update({"ticks": ticks, "loop": tl.get("loop", False)})
        meta.update({"anchor": list(rig.anchor), "variant": v, "variant_label": rig.labels.get(v, v),
                     "made_from": rel(src / "timeline.json"), "rig": rel(rig.folder / "rig.json"), "tick": "1/60초"})
        (od / f"{stem}_{v}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        gif([fr[v] for fr in frames], ticks, od / f"{stem}_{v}_x8.gif")
        outs[v] = {"sheet": rel(od / f"{stem}_{v}.png"), "meta": rel(od / f"{stem}_{v}.json"), "gif": rel(od / f"{stem}_{v}_x8.gif")}
    rows = [(rig.short.get("body", "body"), [fr["body"] for fr in frames])]
    if rig.layer:
        rows += [(rig.short.get("layer", "layer"), [fr["layer"] for fr in frames]), (rig.short.get(LN, LN), [fr[LN] for fr in frames])]
    strip(rows, od / f"{stem}_frames_x8.png", sole=rig.anchor[1])
    res["outputs"] = outs | {"frames_x8": rel(od / f"{stem}_frames_x8.png"), "frames": rel(fd)}
    res["timeline"] = rel(src / "timeline.json")
    (d / "check.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    S = res["summary"]
    print(f"[{name}] {'통과' if S['pass'] else '실패'} — 프레임 {S['frames']} · 틱 {S['ticks']} · 팔레트 이탈 {S['off_palette']} · 반투명 {S['semi_transparent']}"
          f" · 발바닥 줄 고정 {S['sole_fixed']} · 머리 같음 {S['head_same_all']} · 몸통 같은 칸 최소 {S['upper_same_min']}/{S['upper_cells']}"
          + (f" · 층을 빼면 같음 {S[f'{LN}_off_equals_body']}" if rig.layer else "") + f" · 이웃 프레임 변화 {S['neighbor_change_mean']}"
          + (f" · 발 미끄러짐 최대 {S['foot_slip_max']}칸" if 'foot_slip_max' in S else "")
          + (f" · 바뀌면 안 되는 {S['fixed_cells']}칸 가운데 바뀐 칸 최대 {S['fixed_changed_max']} (앞쪽 팔이 가림 최대 {S['fixed_covered_by_near_arm_max']})" if 'fixed_cells' in S else ""))
    return res


# ---------------------------------------------------------------- 기획자가 보는 그림 (NX-07 의 anim/make_preview.py 를 캐릭터에 묶이지 않게 옮긴 것)

PBG, PPANEL = (18, 20, 28), (34, 37, 50)
PTXT, PSUB, PGOLD = (236, 236, 242), (160, 166, 184), (240, 196, 80)
CAT = {"moved": (120, 124, 140), "drawn": (255, 150, 60), "layer": (255, 110, 200)}


def category_map(rig: Rig, fr: dict) -> tuple[np.ndarray, int, int]:
    """칸마다: 마스터의 칸을 옮긴 그대로(회색) / 새로 찍은 칸(주황) / 층(분홍)."""
    f, body, owner, layer = fr["spec"], fr["body"], fr["owner"], fr["layer"]
    ux, uy = f["upper"]
    ax, ay = f.get("arm_off", [0, 0])
    m = np.zeros_like(body)
    moved = drawn = 0
    offs = {"head": (ux, uy), "upper": (ux, uy), "legs": (0, 0)}
    if rig.d["arm_poses"][f["arm"]].get("from_master"):
        offs["near_arm"] = (ax, ay)
    master_at = {nm: {(x + dx + rig.PX, y + dy + rig.PY): c for (x, y), c in rig.parts[nm].items()} for nm, (dx, dy) in offs.items()}
    for Y, X in zip(*np.where(body[..., 3] > 0)):
        c = tuple(int(v) for v in body[Y, X, :3])
        if master_at.get(owner[Y, X], {}).get((X, Y)) == c:
            m[Y, X] = CAT["moved"] + (255,)
            moved += 1
        else:
            m[Y, X] = CAT["drawn"] + (255,)
            drawn += 1
    m[layer[..., 3] > 0] = CAT["layer"] + (255,)
    return m, moved, drawn


def _put(img: Image.Image, a: np.ndarray, x: int, y: int, z: int) -> int:
    cell = Image.new("RGBA", (a.shape[1], a.shape[0]), PPANEL + (255,))
    cell.alpha_composite(Image.fromarray(np.ascontiguousarray(a), "RGBA"))
    img.paste(cell.convert("RGB").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST), (x, y))
    return a.shape[1] * z


def preview(rig: Rig, names: list[str], out_dir: Path | None = None) -> list[Path]:
    """비교 그림 preview/compare.png 와, 속도(speed)가 있는 동작마다 어두운 게임 화면 GIF."""
    out = (out_dir or rig.folder) / "preview"
    out.mkdir(parents=True, exist_ok=True)
    Z = 6
    W = 1860
    img = Image.new("RGB", (W, 4000), PBG)
    d = ImageDraw.Draw(img)
    d.text((32, 20), f"{rig.id} 애니메이션 — 비교 그림 (tools/pixel_anim.py preview)", font=font(30, True), fill=PTXT)
    d.text((32, 62), "승인된 마스터에서 만들었다. 머리 · 몸통은 마스터의 칸을 칸 단위로 옮기기만 했고, 다리 · 앞쪽 팔 · 층의 끝은 표에서 찍은 칸이다.",
           font=font(16), fill=PSUB)
    d.text((32, 86), f"모든 그림 ×{Z} (nearest). 빨간 줄 = 발바닥 줄. 마지막 줄: 회색 = 마스터의 칸을 옮긴 그대로 · 주황 = 새로 찍은 칸 · 분홍 = 층.",
           font=font(16), fill=PSUB)
    y = 130
    sole = rig.anchor[1]
    head_n, upper_n = len(rig.parts["head"]), len(rig.parts["upper"])
    # 승인된 마스터 (이 그림에서 모든 프레임을 만들었다)
    d.text((32, y), "승인된 마스터", font=font(22, True), fill=PTXT)
    y += 34
    x = 180
    masters = [(rig.short.get("body", "body"), rig.master)] + ([(rig.short.get(rig.layer_name, rig.layer_name), rig.master_scarf)] if rig.layer else [])
    for label, m in masters:
        canvas = np.zeros((rig.H, rig.W, 4), np.uint8)
        hb, wb = m.shape[:2]
        pad = rig.layer_pad if m is rig.master_scarf else 0
        canvas[rig.PY:rig.PY + hb, rig.PX - pad:rig.PX - pad + wb] = m
        w = _put(img, canvas, x, y, Z)
        d.line([(x, y + sole * Z), (x + w, y + sole * Z)], fill=(200, 70, 70), width=1)
        d.text((x, y + rig.H * Z + 4), f"{label} · {wb}×{hb}칸", font=font(14), fill=PSUB)
        x += w + 10
    fixed0 = rig.fixed_cells()
    if fixed0 is not None:
        fm = np.zeros((rig.H, rig.W, 4), np.uint8)
        for (cx, cy), c in {**rig.parts["head"], **rig.parts["upper"]}.items():
            fm[cy + rig.PY, cx + rig.PX] = (CAT["moved"] if (cx, cy) in fixed0 else (190, 120, 255)) + (255,)
        for nm in ("legs", "near_arm"):
            for (cx, cy) in rig.parts[nm]:
                fm[cy + rig.PY, cx + rig.PX] = (190, 120, 255, 255)
        w = _put(img, fm, x, y, Z)
        d.text((x, y + rig.H * Z + 4), f"회색 = 바뀌면 안 되는 {len(fixed0)}칸 · 보라 = 바뀌어도 되는 칸", font=font(14), fill=PSUB)
        x += w + 10
    y += rig.H * Z + 40
    for name in names:
        tl = json.loads((rig.folder / name / "timeline.json").read_text(encoding="utf-8"))
        frs = make_frames(rig, tl)
        res = checks(rig, tl, frs)
        S = res["summary"]
        d.text((32, y), f"{tl.get('label', name)} — {len(frs)}프레임, 틱 {' · '.join(str(t) for t in S['ticks'])} (1틱 = 1/60초)"
                        + (", 되풀이" if tl.get("loop") else ""), font=font(22, True), fill=PTXT)
        y += 34
        d.text((32, y), tl.get("method", ""), font=font(15), fill=PSUB)
        y += 40
        rows = [(rig.short.get(v, v), v) for v in rig.variants] + [("새로 찍은 칸", "cat")]
        for label, key in rows:
            d.text((32, y + 100), label, font=font(16, True), fill=PTXT)
            x = 180
            for i, fr in enumerate(frs):
                if key == "cat":
                    m, mv, dr = category_map(rig, fr)
                    w = _put(img, m, x, y, Z)
                    d.text((x, y + rig.H * Z + 4), f"옮김 {mv} · 새로 {dr}", font=font(13), fill=PSUB)
                else:
                    w = _put(img, fr[key], x, y, Z)
                    d.line([(x, y + sole * Z), (x + w, y + sole * Z)], fill=(200, 70, 70), width=1)
                x += w + 10
            y += rig.H * Z + (30 if key == "cat" else 20)
        d.text((32, y), f"검사: {'통과' if S['pass'] else '실패'} · 팔레트 이탈 {S['off_palette']} · 반투명 {S['semi_transparent']} · 발바닥 줄 고정 "
                        f"{'예' if S['sole_fixed'] else '아니오'} · 머리 {head_n}칸이 마스터와 같음 {'예' if S['head_same_all'] else '아니오'} · "
                        f"몸통 {upper_n}칸 가운데 마스터와 같은 칸 최소 {S['upper_same_min']}"
                        + (f" · 바뀌면 안 되는 {S['fixed_cells']}칸 가운데 바뀐 칸 최대 {S['fixed_changed_max']} (앞쪽 팔이 가림 최대 {S['fixed_covered_by_near_arm_max']})" if 'fixed_cells' in S else "")
                        + (f" · 발 미끄러짐 최대 {S['foot_slip_max']}칸" if 'foot_slip_max' in S else ""), font=font(16), fill=PTXT)
        y += 50
    p = out / "compare.png"
    img.crop((0, 0, W, y)).save(p)
    made = [p]
    for name in names:
        tl = json.loads((rig.folder / name / "timeline.json").read_text(encoding="utf-8"))
        if "speed" in tl:
            made.append(ingame(rig, name, tl, out))
    for q in made:
        print("[preview]", rel(q))
    return made


def screen_bg(pv: dict) -> tuple[Image.Image, int]:
    """어두운 게임 화면: 지금 게임의 배경을 화면 크기로 줄이고 누른 것과 땅의 줄."""
    w, h = pv.get("screen", [320, 180])
    src = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGB")
    bg = src.resize((int(round(src.width * h / 360)), h), Image.NEAREST).crop((0, 0, w, h))
    keep, dim = pv.get("press", [0.25, 0.70])
    bg = Image.blend(bg.convert("L").convert("RGB"), bg, keep).convert("RGBA")
    floor = int(round(h * 304 / 360))
    bg.alpha_composite(Image.new("RGBA", (w, floor), (10, 12, 24, int(255 * dim))))
    ImageDraw.Draw(bg).rectangle([0, floor, w, h], fill=(18, 19, 28, 255))
    return bg, floor


def together(actors: list[dict], out_path: Path, title: str, z: int = 4, max_ticks: int = 720) -> Path:
    """승인된 캐릭터 여럿을 같은 어두운 게임 화면 · 같은 발바닥 줄에 세운다 (두 번째 캐릭터부터의 질문: 같은 게임의 그림인가).
    actors = [{"rig": Rig, "anim": 동작, "variant": 벌, "label": 글}]. 동작마다 자기 틱으로 돈다. 속도가 있으면 땅의 눈금이 흐른다."""
    pv = actors[0]["rig"].d.get("preview") or {}
    w, h = pv.get("screen", [320, 180])
    bg, floor = screen_bg(pv)
    tracks = []
    for a in actors:
        rig = a["rig"]
        tl = json.loads((rig.folder / a["anim"] / "timeline.json").read_text(encoding="utf-8"))
        frs = make_frames(rig, tl)
        ticks = [fr["spec"]["ticks"] for fr in frs]
        tracks.append({**a, "tl": tl, "frames": [fr[a["variant"]] for fr in frs], "ticks": ticks, "cycle": sum(ticks)})
    total = 1
    for t in tracks:
        total = total * t["cycle"] // np.gcd(total, t["cycle"])
    total = min(total, max_ticks)
    speeds = {t["tl"].get("speed", 0) for t in tracks}
    speed = max(speeds)
    # 프레임이 바뀌는 틱을 모은다
    cuts = {0}
    for t in tracks:
        acc = 0
        while acc < total:
            for k in t["ticks"]:
                acc += k
                if acc < total:
                    cuts.add(acc)
    cuts = sorted(cuts) + [total]
    # GIF 의 시간은 10ms 단위다. 끝 시각을 누적으로 반올림하고 (틀림이 쌓이지 않게), 20ms 보다 짧은 조각은 앞 조각에 붙인다 (브라우저가 100ms 로 늘린다)
    ms = lambda t: int(round(t * 1000 / 60 / 10)) * 10  # noqa: E731
    keep = [cuts[0]]
    for c in cuts[1:-1]:
        if ms(c) - ms(keep[-1]) >= 20:
            keep.append(c)
    if ms(total) - ms(keep[-1]) < 20 and len(keep) > 1:
        keep.pop()
    cuts = keep + [total]
    n = len(tracks)
    span = min(w - 80, 44 * n)  # 함께 달리는 거리 (캐릭터 사이 44칸)
    xs = [int(w / 2 - span / 2 + span * (i + 0.5) / n) for i in range(n)]

    def frame_at(t, tick):
        tick %= t["cycle"]
        acc = 0
        for i, k in enumerate(t["ticks"]):
            if tick < acc + k:
                return t["frames"][i]
            acc += k
        return t["frames"][-1]

    imgs, durs = [], []
    for c0, c1 in zip(cuts[:-1], cuts[1:]):
        b = bg.copy()
        db = ImageDraw.Draw(b)
        off = speed * c0
        for gx in range(-10, w + 10, 10):
            X = int(gx - off) % (w + 10)
            db.line([(X, floor + 1), (X + 2, floor + 1)], fill=(110, 118, 150, 255))
        db.line([(0, floor), (w, floor)], fill=(58, 64, 88, 255))
        for t, x in zip(tracks, xs):
            rig = t["rig"]
            b.alpha_composite(Image.fromarray(frame_at(t, c0), "RGBA"), (x - rig.anchor[0], floor - rig.anchor[1]))
        big = b.convert("RGB").resize((w * z, h * z), Image.NEAREST)
        dg = ImageDraw.Draw(big)
        for i, (t, x) in enumerate(zip(tracks, xs)):
            fnt = font(18, True)
            tw = dg.textlength(t["label"], font=fnt)
            dg.text((x * z - tw / 2, (floor + 6 + 7 * (i % 2)) * z), t["label"], font=fnt, fill=PTXT)
        dg.text((16, 12), f"{w}×{h} ×{z} · {title}" + (f" · 땅의 눈금 = 가정한 속도 {speed}칸/틱" if speed else ""), font=font(18), fill=PSUB)
        imgs.append(big)
        durs.append(ms(c1) - ms(c0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imgs[0].save(out_path, save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=1)
    print("[together]", rel(out_path))
    return out_path


def ingame(rig: Rig, name: str, tl: dict, out: Path) -> Path:
    """어두운 게임 화면에서 벌마다 나란히. 땅의 눈금이 가정한 속도로 흐른다 (발이 미끄러지는지 보려고)."""
    pv = rig.d.get("preview") or {}
    w, h = pv.get("screen", [320, 180])
    Z = 4
    bg, floor = screen_bg(pv)
    frs = make_frames(rig, tl)
    speed = tl["speed"]
    xs = {v: int(w * (i + 1) / (len(rig.variants) + 1)) for i, v in enumerate(rig.variants)}
    imgs, durs, off = [], [], 0.0
    for fr in frs:
        b = bg.copy()
        db = ImageDraw.Draw(b)
        for gx in range(-10, w + 10, 10):
            X = int(gx - off) % (w + 10)
            db.line([(X, floor + 1), (X + 2, floor + 1)], fill=(110, 118, 150, 255))
        db.line([(0, floor), (w, floor)], fill=(58, 64, 88, 255))
        for v, x in xs.items():
            b.alpha_composite(Image.fromarray(fr[v], "RGBA"), (x - rig.anchor[0], floor - rig.anchor[1]))
        big = b.convert("RGB").resize((w * Z, h * Z), Image.NEAREST)
        dg = ImageDraw.Draw(big)
        for v, x in xs.items():
            dg.text((x * Z - 70, (floor + 8) * Z), rig.short.get(v, v), font=font(20, True), fill=PTXT)
        dg.text((16, 12), f"{w}×{h} ×{Z} · {tl.get('label', name)} {len(frs)}프레임 · 땅의 눈금 = 가정한 속도 {speed}칸/틱", font=font(18), fill=PSUB)
        imgs.append(big)
        durs.append(round(fr["spec"]["ticks"] * 1000 / 60))
        off += speed * fr["spec"]["ticks"]
    p = out / f"ingame_{name}_{w}x{h}_x{Z}.gif"
    imgs[0].save(p, save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=1)
    return p


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if len(args) < 2 or args[0] not in ("build", "preview"):
        sys.exit(__doc__)
    out = None
    if "--out" in args:
        i = args.index("--out")
        out = Path(args[i + 1])
        out = out if out.is_absolute() else ROOT / out
        del args[i:i + 2]
    rig = Rig(ROOT / args[1])
    names = args[2:] or [p.parent.name for p in sorted(rig.folder.glob("*/timeline.json"))]
    if args[0] == "build":
        for n in names:
            build_one(rig, n, out_dir=out)
    else:
        preview(rig, names, out_dir=out)


if __name__ == "__main__":
    main()
