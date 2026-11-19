"""기획자에게 보일 그림 (기획서 9.11.6): 비교 그림 preview/compare.png · 게임 화면 GIF preview/ingame_run_320x180_x4.gif.

    python -X utf8 tools/pixel_anim.py build art/characters/nx07/anim     # 먼저 프레임과 검사
    python -X utf8 art/characters/nx07/anim/make_preview.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import pixel_anim as pa  # noqa: E402

OUT = HERE / "preview"
BG, PANEL = (18, 20, 28), (34, 37, 50)
TXT, SUB, GOLD = (236, 236, 242), (160, 166, 184), (240, 196, 80)
CAT = {"moved": (120, 124, 140), "drawn": (255, 150, 60), "scarf": (255, 110, 200)}
PRESS = (0.25, 0.70)  # 배경 누르기 2단계 (채도 25% · 70% 어둡게), 9.11.2


def frames_of(rig: pa.Rig, name: str):
    tl = json.loads((HERE / name / "timeline.json").read_text(encoding="utf-8"))
    out = []
    for f in tl["frames"]:
        body, layer, owner, _ = pa.compose(rig, tl, f)
        out.append({"spec": f, "body": body, "layer": layer, "scarf": pa.put_on(body, layer), "owner": owner})
    return tl, out


def category_map(rig: pa.Rig, fr: dict) -> tuple[np.ndarray, int, int]:
    """칸마다: 마스터의 칸을 옮긴 그대로(회색) / 새로 찍은 칸(주황) / 스카프 층(분홍)."""
    f, body, owner, layer = fr["spec"], fr["body"], fr["owner"], fr["layer"]
    ux, uy = f["upper"]
    ax, ay = f.get("arm_off", [0, 0])
    m = np.zeros_like(body)
    moved = drawn = 0
    master_at: dict = {}  # 부위마다 따로: 그 칸을 그린 부위의 마스터 칸과 견준다
    offs = {"head": (ux, uy), "upper": (ux, uy), "legs": (0, 0)}
    if rig.d["arm_poses"][f["arm"]].get("from_master"):
        offs["near_arm"] = (ax, ay)
    for nm, (dx, dy) in offs.items():
        master_at[nm] = {(x + dx + rig.PX, y + dy + rig.PY): c for (x, y), c in rig.parts[nm].items()}
    for Y, X in zip(*np.where(body[..., 3] > 0)):
        c = tuple(int(v) for v in body[Y, X, :3])
        if master_at.get(owner[Y, X], {}).get((X, Y)) == c:
            m[Y, X] = CAT["moved"] + (255,)
            moved += 1
        else:
            m[Y, X] = CAT["drawn"] + (255,)
            drawn += 1
    sl = layer[..., 3] > 0
    m[sl] = CAT["scarf"] + (255,)
    return m, moved, drawn


def put(img: Image.Image, a: np.ndarray, x: int, y: int, z: int, crop=(4, 0, 38, 40)) -> int:
    a = a[crop[1]:crop[3], crop[0]:crop[2]]
    cell = Image.new("RGBA", (a.shape[1], a.shape[0]), PANEL + (255,))
    cell.alpha_composite(Image.fromarray(np.ascontiguousarray(a), "RGBA"))
    img.paste(cell.convert("RGB").resize((a.shape[1] * z, a.shape[0] * z), Image.NEAREST), (x, y))
    return a.shape[1] * z


def compare(rig: pa.Rig) -> Path:
    Z = 6
    font = pa.font
    W = 1860
    img = Image.new("RGB", (W, 3000), BG)
    d = ImageDraw.Draw(img)
    d.text((32, 20), "NX-07 대기 · 달리기 — 첫 증명 (기획서 9.11.6)", font=font(30, True), fill=TXT)
    d.text((32, 62), "승인된 픽셀 마스터 두 벌(스카프 없음 = 합류 전 · 있음 = 합류 뒤)에서 만들었다. 이미지 생성 0회. 머리 · 몸통 · 주포는 마스터의 칸을 칸 단위로 옮기기만 했고, "
           "다리 · 앞쪽 팔 · 스카프 끝은 에이전트가 칸을 찍은 표다.", font=font(16), fill=SUB)
    d.text((32, 86), f"모든 그림 ×{Z} (nearest). 빨간 줄 = 발바닥 줄. 셋째 줄: 회색 = 마스터의 칸을 옮긴 그대로 · 주황 = 새로 찍은 칸 · 분홍 = 스카프 층.",
           font=font(16), fill=SUB)
    y = 130
    # 마스터
    d.text((32, y), "① 승인된 마스터 (같은 캔버스 40×40, 같은 기준점)", font=font(22, True), fill=TXT)
    y += 36
    x = 32
    for label, path, pad in (("스카프 없음 (C36)", rig.d["master"], 0), ("스카프 있음 (S2)", rig.d["master_scarf"], 1)):
        a = np.array(Image.open(ROOT / path).convert("RGBA"))
        c = np.zeros((rig.H, rig.W, 4), np.uint8)
        c[rig.PY:rig.PY + a.shape[0], rig.PX - pad:rig.PX - pad + a.shape[1]] = a
        d.text((x, y), label, font=font(16, True), fill=GOLD)
        w = put(img, c, x, y + 26, Z)
        d.line([(x, y + 26 + 38 * Z), (x + w, y + 26 + 38 * Z)], fill=(200, 70, 70), width=2)
        x += w + 24
    y += 26 + 40 * Z + 30
    checks = {}
    for name in ("idle", "run"):
        tl, frs = frames_of(rig, name)
        chk = json.loads((HERE / name / "check.json").read_text(encoding="utf-8"))
        checks[name] = chk
        S = chk["summary"]
        n = len(frs)
        title = {"idle": "② 대기", "run": "③ 달리기"}[name]
        ticks = " · ".join(str(t) for t in S["ticks"])
        d.text((32, y), f"{title} — {n}프레임, 프레임마다 틱 {ticks} (1틱 = 1/60초), 되풀이", font=font(22, True), fill=TXT)
        y += 34
        d.text((32, y), tl["method"], font=font(15), fill=SUB)
        y += 54
        for label, key in (("스카프 없음", "body"), ("스카프 있음", "scarf"), ("새로 찍은 칸", "cat")):
            d.text((32, y + 100), label, font=font(16, True), fill=TXT)
            x = 160
            for i, fr in enumerate(frs):
                if key == "cat":
                    m, mv, dr = category_map(rig, fr)
                    w = put(img, m, x, y, Z)
                    lay = int((fr["layer"][..., 3] > 0).sum())
                    d.text((x, y + 40 * Z + 4), f"옮김 {mv} · 새로 {dr} · 스카프 {lay}", font=font(13), fill=SUB)
                else:
                    w = put(img, fr[key], x, y, Z)
                    d.line([(x, y + 38 * Z), (x + w, y + 38 * Z)], fill=(200, 70, 70), width=1)
                    if key == "body":
                        sp = fr["spec"]
                        t = f"#{i} · {sp['ticks']}틱" + (f" · {sp['near']}/{sp['far']}" if "near" in sp else "") + f" · 팔 {sp['arm']}"
                        d.text((x, y - 20), t, font=font(13), fill=SUB)
                x += w + 10
            y += 40 * Z + (30 if key == "cat" else 26)
        y += 20
    # 검사 요약
    d.text((32, y), "④ 검사 (tools/pixel_anim.py, 숫자)", font=font(22, True), fill=TXT)
    y += 36
    rows = []
    for name, lab in (("idle", "대기"), ("run", "달리기")):
        S = checks[name]["summary"]
        heads = [f"{r['head']['same']}/{r['head']['cells']}" for r in checks[name]["frames"]]
        uppers = [f"{r['upper']['same']}" for r in checks[name]["frames"]]
        rows.append(f"{lab}: 팔레트 이탈 {S['off_palette']} · 반투명 {S['semi_transparent']} · 캔버스 40×40 · 발바닥 줄(38) 고정 {'예' if S['sole_fixed'] else '아니오'}"
                    f" · 스카프 층을 빼면 스카프 없음과 같음 {'예' if S['scarf_off_equals_body'] else '아니오'}")
        rows.append(f"    머리 107칸이 마스터와 같은 프레임: {sum(1 for h in heads if h == '107/107')}/{len(heads)} · 몸통 · 주포 168칸 가운데 마스터와 같은 칸: {' · '.join(uppers)}"
                    f" (나머지는 앞쪽 팔이 앞에서 가림)")
        nc = checks[name]["neighbor_change"]
        rows.append(f"    이웃 프레임 사이에 바뀐 칸: 스카프 없음 {' · '.join(f'{v * 100:.0f}%' for v in nc['body'])} / 스카프 있음 {' · '.join(f'{v * 100:.0f}%' for v in nc['scarf'])}")
        if "foot_slip" in checks[name]:
            sl = checks[name]["foot_slip"]
            rows.append(f"    발 미끄러짐: 딛고 있는 발의 앞끝이 프레임마다 {' · '.join(str(s['moved']) for s in sl)}칸 움직임 — 가정한 속도 1.0칸/틱 × 5틱 = -5칸과의 차이 최대 "
                        f"{S['foot_slip_max']}칸")
    for r in rows:
        d.text((32, y), r, font=font(16), fill=TXT if not r.startswith("    ") else SUB)
        y += 26
    y += 10
    d.text((32, y), "읽는 법: '이웃 프레임 사이에 바뀐 칸'은 9.9 와 같은 잣대(같은 자리의 칸이 다른가)다. 달리기는 69~71% 로 9.9 의 지금 게임(68~94%)과 비슷하게 나온다 — 몸이 1칸 오르내리면 같은 칸이 옮겨질 뿐인데도",
           font=font(15), fill=SUB)
    y += 24
    d.text((32, y), "잣대에는 '바뀜'으로 잡히기 때문이다. 내용으로 보면 다르다: 9.9 는 AI 가 머리 아래를 프레임마다 다시 그렸고, 여기서는 머리 · 몸통 · 주포가 마스터와 한 칸도 다르지 않고 새로 찍은 칸은 다리 · 팔뿐이다 (셋째 줄).",
           font=font(15), fill=SUB)
    y += 40
    out = OUT / "compare.png"
    img.crop((0, 0, W, y)).save(out)
    return out


def ingame(rig: pa.Rig) -> Path:
    """320×180 (×4) 어두운 게임 화면에서 달리기 두 벌. 땅의 눈금이 가정한 속도로 흐른다 (발이 미끄러지는지 보려고)."""
    w, h, Z = 320, 180, 4
    src = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGB")
    k = h / 360
    bg = src.resize((int(round(src.width * k)), h), Image.NEAREST).crop((0, 0, w, h))
    keep, dim = PRESS
    bg = Image.blend(bg.convert("L").convert("RGB"), bg, keep).convert("RGBA")
    floor = int(round(h * 304 / 360))
    bg.alpha_composite(Image.new("RGBA", (w, floor), (10, 12, 24, int(255 * dim))))
    dd = ImageDraw.Draw(bg)
    dd.rectangle([0, floor, w, h], fill=(18, 19, 28, 255))
    tl, frs = frames_of(rig, "run")
    speed = tl["speed"]
    # GIF 팔레트: 배경을 줄인 색 + 캐릭터(두 마스터)의 색 전부 + 글자 색. 캐릭터 색이 다른 색으로 바뀌지 않게 한다.
    sprite_cols = set()
    for p in (rig.d["master"], rig.d["master_scarf"]):
        a = np.array(Image.open(ROOT / p).convert("RGBA"))
        sprite_cols |= {tuple(int(v) for v in c) for c in a[a[..., 3] > 0][:, :3]}
    fixed = sorted(sprite_cols) + [TXT, SUB, (70, 76, 100), (110, 118, 150), (58, 64, 88), (18, 19, 28)]
    bgq = bg.convert("RGB").quantize(colors=256 - len(fixed), method=Image.MEDIANCUT, dither=Image.NONE)
    flat = bgq.getpalette()[: 3 * (256 - len(fixed))]
    for c in fixed:
        flat += list(c)
    palimg = Image.new("P", (1, 1))
    palimg.putpalette(flat)
    imgs, durs = [], []
    x_at = {"body": 96, "scarf": 196}
    off = 0.0
    for i, fr in enumerate(frs):
        b = bg.copy()
        db = ImageDraw.Draw(b)
        for gx in range(-10, w + 10, 10):
            X = int(gx - off) % (w + 10)
            db.line([(X, floor + 1), (X + 2, floor + 1)], fill=(110, 118, 150, 255))
        db.line([(0, floor), (w, floor)], fill=(58, 64, 88, 255))
        for v, x in x_at.items():
            b.alpha_composite(Image.fromarray(fr[v], "RGBA"), (x - rig.anchor[0], floor - rig.anchor[1]))
        big = b.convert("RGB").resize((w * Z, h * Z), Image.NEAREST)
        dg = ImageDraw.Draw(big)
        dg.text((x_at["body"] * Z - 70, (floor + 8) * Z), "스카프 없음 (합류 전)", font=pa.font(20, True), fill=TXT)
        dg.text((x_at["scarf"] * Z - 70, (floor + 8) * Z), "스카프 있음 (합류 뒤)", font=pa.font(20, True), fill=TXT)
        dg.text((16, 12), f"320×180 ×{Z} · 배경 누르기 2단계 · 달리기 6프레임 × 5틱 · 땅의 눈금 = 가정한 속도 {speed}칸/틱 · 키 36칸 = 화면 높이의 1/5",
                font=pa.font(18), fill=SUB)
        imgs.append(big.quantize(palette=palimg, dither=Image.NONE))
        durs.append(round(fr["spec"]["ticks"] * 1000 / 60))
        off += speed * fr["spec"]["ticks"]
    out = OUT / "ingame_run_320x180_x4.gif"
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=1)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    rig = pa.Rig(HERE)
    print(pa.rel(compare(rig)))
    print(pa.rel(ingame(rig)))


if __name__ == "__main__":
    main()
