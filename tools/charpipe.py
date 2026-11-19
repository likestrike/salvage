"""캐릭터 등록부 (Character Master) — 기획서 9.11 "시스템의 모양과 등록부".

캐릭터마다 JSON 한 개(art/characters/<id>/character.json)가 그 캐릭터의 원화 · 픽셀 마스터 · 게임 스프라이트를
경로로 가리킨다. 파일은 옮기거나 복사하지 않는다. git 이 없으므로 파일마다 내용 해시(sha256)를 적어 두고,
등록한 뒤에 파일이 바뀌면 검사에서 드러나게 한다.

    python tools/charpipe.py build                      # 전부: 해시 다시 재기 · 검사 · 미리보기 · 보고 화면 (이것 하나면 된다)
    python tools/charpipe.py check [id…]                # 해시를 다시 재고 검사만 한다 (art/characters/<id>/check.json)
    python tools/charpipe.py report                     # 미리보기 그림과 보고 화면의 자료(_report/data.js)를 만든다
    python tools/charpipe.py register <id> --setting <설정화 묶음의 키> --name 이름 --kind player
                                                        # 새 캐릭터를 등록한다 (설정화 묶음의 일곱 장과 출처를 setting.json 에서 읽는다)
    python tools/charpipe.py add <id> <key> <파일> --group design --label "…"
                                                        # 파일 하나를 더 등록한다 (시안 · 참조 · 나중의 파츠 · 리그 …)
    python tools/charpipe.py add-sprites <id> <states.json> [--names a,b] [--set 이름]
    python tools/charpipe.py add-pixel-lab <id> <실험 폴더>
    python tools/charpipe.py accept <id> <key…|--changed> --note "…"
                                                        # 바뀐 파일을 새 판으로 받아들인다 (기준 해시를 바꾸고 판 번호를 올린다)
    python tools/charpipe.py approve <id> <key…> --by 기획자 --note "…"
                                                        # 승인을 적는다. 기획자가 대화에서 승인했을 때만 쓴다

--root 로 다른 폴더를 프로젝트처럼 다룰 수 있다 (바뀜 감지 시험용).
보고 화면: art/characters/index.html (더블클릭으로 연다. fetch · ES 모듈을 쓰지 않는다).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

FORMAT = "salvage-character/1"
REG_FORMAT = "salvage-registry/1"
STYLE_MODEL = "openai/gpt-image-2.6/sunburst/edit"  # tools/fal_image.py 의 --keep-style 모델 (읽기만 한다)
VIEWS = ["front", "side", "back"]
SEVEN = ["front", "side", "back", "face", "body", "items", "poses"]
LABELS = {"front": "정면 전신", "side": "측면 전신", "back": "후면 전신", "face": "얼굴 확대", "body": "신체 확대",
          "items": "무기 · 소지품 단독", "poses": "주요 포즈", "turnaround": "세 시점 원본 (나누기 전)"}
KIND_OF = {"face": "face", "body": "body", "items": "items", "poses": "poses", "turnaround": "turnaround"}
GROUPS = {
    "view": "정면 · 측면 · 후면",
    "sheet": "나머지 원화",
    "source": "원화의 재료 (나누기 전 · 손보기 전)",
    "design": "디자인 시안",
    "design_ref": "원본 설정화 (reference/)",
    "reference_only": "참조만 (기획자 원본, 고치지 않는다)",
    "pixel_master": "픽셀 마스터 후보 (실험)",
    "sprite": "게임의 스프라이트",
}
# 검사의 문턱 [제안]
TH = {"height_pass": 0.01, "height_warn": 0.03, "white_pass": 0.98, "white_warn": 0.90, "edge_warn": 0.002, "margin_min": 10}

ROOT = Path(__file__).resolve().parent.parent


def today() -> str:
    return date.today().isoformat()


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reg_dir() -> Path:
    return ROOT / "art" / "characters"


def char_path(cid: str) -> Path:
    return reg_dir() / cid / "character.json"


def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_registry() -> dict:
    p = reg_dir() / "registry.json"
    if p.exists():
        return read_json(p)
    return {"format": REG_FORMAT, "_": "캐릭터 등록부의 목록. 캐릭터마다의 내용은 <id>/character.json (기획서 9.11)", "characters": []}


def save_registry(reg: dict) -> None:
    write_json(reg_dir() / "registry.json", reg)


def ids_all() -> list[str]:
    return [c["id"] for c in load_registry()["characters"]]


def load_char(cid: str) -> dict:
    p = char_path(cid)
    if not p.exists():
        sys.exit(f"[charpipe] 등록되지 않은 캐릭터: {cid} ({rel(p)} 없음)")
    return read_json(p)


def save_char(c: dict) -> None:
    write_json(char_path(c["id"]), c)


def file_facts(path: Path) -> dict:
    """파일의 해시 · 크기 · 바이트 수. 그림이면 가로 × 세로도."""
    facts = {"sha256": sha256(path), "bytes": path.stat().st_size}
    if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        with Image.open(path) as im:
            facts["size"] = list(im.size)
    return facts


def new_asset(group: str, label: str, file: str, source: dict | None = None, **extra) -> dict:
    """등록하는 순간의 해시를 기준(base)으로 적는다. 판 번호는 1부터."""
    path = ROOT / file
    a = {"group": group, "label": label, "file": file}
    if source:
        a["source"] = source
    a.update(extra)
    if path.exists():
        a["base"] = {"version": 1, "date": today(), **file_facts(path)}
    else:
        a["base"] = None
        print(f"[charpipe] 주의: 파일이 없다 — {file}")
    return a


def log(c: dict, what: str, **kw) -> None:
    c.setdefault("history", []).append({"date": today(), "what": what, **kw})


# ---------------------------------------------------------------- register

def setting_assets(key: str) -> tuple[dict, dict]:
    """설정화 묶음(setting.json)에서 일곱 장과 재료의 자리 · 출처를 읽는다."""
    cfg = read_json(ROOT / "art" / "concept" / "setting" / "setting.json")
    ch = cfg["characters"][key]
    out, pdir = cfg["out"], cfg["prompts"]
    anchor = f"art/style_anchor/{ch['style']}.png"
    folder = f"{out}/{key}"

    def gen_source(kind: str) -> dict:
        prompts = [f"{pdir}/{key}_design.txt", f"{pdir}/{key}_{kind}.txt", f"{pdir}/{cfg['kinds'][kind]['layout']}"]
        refs = [f"{pdir}/guide_{key}.png"] + list(ch.get("refs", [])) + list(ch.get("extra_refs", {}).get(kind, []))
        return {"made_by": f"tools/setting_sheets.py gen {key} {kind}", "tool": "tools/fal_image.py --keep-style " + ch["style"],
                "model": STYLE_MODEL, "prompts": prompts, "refs": refs, "style_anchor": anchor,
                "doc": "docs/GAME_DESIGN.md 9.4.1", "definition": "art/concept/setting/setting.json"}

    assets: dict = {}
    turn = f"{folder}/{ch['files']['turnaround']}"
    for fname, view in zip(cfg["split"], VIEWS):
        assets[view] = new_asset("view", LABELS[view], f"{folder}/{fname}",
                                 {"made_by": f"tools/setting_sheets.py split {key}", "from": turn,
                                  "note": "세 시점을 한 장에 그린 뒤 같은 캔버스 · 같은 배율 · 같은 발바닥 줄로 나눴다" +
                                          (". 측면은 오른쪽을 본다" if view == "side" else ""),
                                  "doc": "docs/GAME_DESIGN.md 9.4.1"}, **({"facing": "right"} if view == "side" else {}))
    for kind in ("face", "body", "items", "poses"):
        fname = ch["files"][kind]
        src = gen_source(kind)
        cleaned = ch.get("clean", {}).get(fname)
        if cleaned:
            src["cleaned"] = [{"op": o["op"], "why": o["why"]} for o in cleaned]
            src["raw"] = f"{folder}/{Path(fname).stem}_raw.png"
        label = ch.get("items_label", LABELS[kind]) if kind == "items" else LABELS[kind]
        assets[kind] = new_asset("sheet", label, f"{folder}/{fname}", src)
        if cleaned:
            assets[f"{kind}_raw"] = new_asset("source", f"{LABELS[kind]} — 손보기 전", src["raw"], gen_source(kind))
    assets["turnaround"] = new_asset("source", LABELS["turnaround"], turn, gen_source("turnaround"))
    return assets, ch


def cmd_register(a) -> None:
    p = char_path(a.id)
    if p.exists():
        sys.exit(f"[register] 이미 등록되어 있다: {rel(p)}. 파일을 더하려면 add 를 쓴다")
    assets, ch = setting_assets(a.setting) if a.setting else ({}, {})
    c = {
        "format": FORMAT,
        "id": a.id,
        "name": a.name or ch.get("name", a.id),
        "kind": a.kind,
        "design": {"current": a.design or "", "status": "[미정]", "note": "", "doc": "docs/STORY.md 4장"},
        "story": {"height_cm": a.height_cm, "height_mark": a.height_mark, "doc": "docs/STORY.md 4장"},
        "assets": assets,
        "approvals": [],
        "records": [],
        "history": [],
    }
    log(c, "등록", by="agent", assets=len(assets), note=f"설정화 묶음 setting.json#{a.setting}" if a.setting else "")
    save_char(c)
    reg = load_registry()
    reg["characters"].append({"id": a.id, "name": c["name"], "kind": a.kind, "file": f"{a.id}/character.json"})
    save_registry(reg)
    print(f"[register] {rel(p)} — 파일 {len(assets)}개")


def cmd_add(a) -> None:
    c = load_char(a.id)
    if a.key in c["assets"]:
        sys.exit(f"[add] 이미 있는 키: {a.key}")
    extra = json.loads(a.extra) if a.extra else {}
    src = extra.pop("source", None)
    c["assets"][a.key] = new_asset(a.group, a.label or a.key, Path(a.file).as_posix(), src, **extra)
    log(c, "파일 더함", by="agent", asset=a.key, file=Path(a.file).as_posix())
    save_char(c)
    print(f"[add] {a.id}.{a.key} = {a.file}")


def cmd_add_sprites(a) -> None:
    """상태별 시트의 표(states.json)에서 게임이 쓰는 상태를 등록한다."""
    c = load_char(a.id)
    table = Path(a.table)
    t = read_json(ROOT / table)
    names = a.names.split(",") if a.names else [n for n, s in t["states"].items() if s.get("use", True)]
    n = 0
    for name in names:
        s = t["states"][name]
        key = f"sprite_{a.set}_{name}" if a.set else f"sprite_{name}"
        if key in c["assets"]:
            continue
        file = (table.parent / s["file"]).as_posix()
        c["assets"][key] = new_asset("sprite", name, file, {"table": table.as_posix()},
                                     set=a.set or table.parent.name,
                                     anim={"frames": s["frames"], "cell": s["cell"], "ticks": s.get("ticks"),
                                           "loop": s.get("loop", False), "sole": t.get("base")})
        n += 1
    log(c, "스프라이트 등록", by="agent", table=table.as_posix(), count=n)
    save_char(c)
    print(f"[add-sprites] {a.id}: {n}개")


def cmd_add_pixel_lab(a) -> None:
    """픽셀 마스터 실험 폴더(tools/pixel_master.py 의 출력)마다 마스터 한 장을 후보로 등록한다."""
    c = load_char(a.id)
    lab = ROOT / a.folder
    n = 0
    for info in sorted(lab.glob("*/*_info.json")):
        d = read_json(info)
        stem = info.name[: -len("_info.json")]
        exp = info.parent.name
        key = f"pm_{exp}"
        if key in c["assets"]:
            continue
        master = info.parent / f"{stem}.png"
        c["assets"][key] = new_asset(
            "pixel_master", exp, rel(master),
            {"made_by": f"tools/pixel_master.py (고른 칸 {d.get('picked')}, 도구의 추천 {d.get('recommended')})",
             "from": d.get("src"), "doc": "docs/GAME_DESIGN.md 9.11"},
            status="실험", info=rel(info),
            also={k: rel(info.parent / f"{stem}{suf}") for k, suf in
                  (("x8", "_x8.png"), ("candidates", "_candidates.png"), ("palette", "_palette.hex"))
                  if (info.parent / f"{stem}{suf}").exists()})
        n += 1
    log(c, "픽셀 마스터 후보 등록", by="agent", folder=rel(lab), count=n)
    save_char(c)
    print(f"[add-pixel-lab] {a.id}: {n}개")


# ---------------------------------------------------------------- accept / approve

def current_sha(c: dict, key: str) -> str | None:
    p = ROOT / c["assets"][key]["file"]
    return sha256(p) if p.exists() else None


def cmd_accept(a) -> None:
    c = load_char(a.id)
    keys = a.keys
    if a.changed:
        keys = [k for k, s in c["assets"].items() if s.get("base") and current_sha(c, k) not in (None, s["base"]["sha256"])]
    for k in keys:
        s = c["assets"][k]
        p = ROOT / s["file"]
        if not p.exists():
            print(f"[accept] {k}: 파일이 없어서 건너뛴다")
            continue
        old = s.get("base") or {}
        facts = file_facts(p)
        if old.get("sha256") == facts["sha256"]:
            print(f"[accept] {k}: 바뀌지 않았다")
            continue
        ver = (old.get("version") or 0) + 1
        s["base"] = {"version": ver, "date": today(), **facts}
        log(c, "새 판으로 받아들임", by="agent", asset=k, version=ver,
            from_sha=(old.get("sha256") or "")[:12], to_sha=facts["sha256"][:12], note=a.note or "")
        print(f"[accept] {k}: 판 {ver}")
    save_char(c)


def cmd_approve(a) -> None:
    """승인 기록. 기획자가 대화에서 승인했다고 말했을 때만 쓴다. 승인하는 순간의 해시를 함께 적는다."""
    c = load_char(a.id)
    hashes = {}
    for k in a.keys:
        if k not in c["assets"]:
            sys.exit(f"[approve] 없는 키: {k}")
        s = c["assets"][k]
        cur = current_sha(c, k)
        if cur is None:
            sys.exit(f"[approve] {k}: 파일이 없다")
        if s.get("base") and cur != s["base"]["sha256"]:
            sys.exit(f"[approve] {k}: 등록한 뒤 파일이 바뀌었다. 먼저 accept 로 새 판을 받아들인다")
        hashes[k] = cur
    c["approvals"].append({"date": today(), "by": a.by, "assets": hashes, "note": a.note or ""})
    log(c, "승인", by=a.by, assets=list(hashes), note=a.note or "")
    save_char(c)
    print(f"[approve] {a.id}: {', '.join(hashes)}")


# ---------------------------------------------------------------- measure / check

def ink_mask(a: np.ndarray, floor: int, spread: int) -> np.ndarray:
    """배경(밝고 채도 낮은 색)이 아닌 곳. tools/setting_sheets.py 의 나누기와 같은 기준."""
    r, g, b = (a[..., i].astype(int) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    return ~((mn > floor) & (mx - mn < spread))


def measure_image(path: Path, figure: bool) -> dict:
    im = Image.open(path)
    a = np.asarray(im.convert("RGB"))
    h, w = a.shape[:2]
    m = {}
    # 배경: 가장자리 8px 띠에서 거의 흰색(가장 어두운 채널 ≥ 240, 채도 ≤ 12)인 픽셀의 비율
    ring = np.ones((h, w), bool)
    ring[8:-8, 8:-8] = False
    px = a[ring].astype(int)
    white = (px.min(axis=1) >= 240) & (px.max(axis=1) - px.min(axis=1) <= 12)
    m["white_ratio"] = round(float(white.mean()), 4)
    m["edge_color"] = "#%02x%02x%02x" % tuple(int(v) for v in np.median(px, axis=0))
    # 잘림: 가장 바깥 2px 띠에 그림(진한 색)이 닿은 비율
    ink = ink_mask(a, 200, 28)
    edge = np.concatenate([ink[:2].ravel(), ink[-2:].ravel(), ink[:, :2].ravel(), ink[:, -2:].ravel()])
    m["edge_ink"] = round(float(edge.mean()), 5)
    if figure:
        fm = ink_mask(a, 228, 22)
        rows, cols = np.where(fm.sum(axis=1) > 2)[0], np.where(fm.sum(axis=0) > 2)[0]
        if len(rows):
            top, sole = int(rows.min()), int(rows.max()) + 1
            left, right = int(cols.min()), int(cols.max()) + 1
            m.update(top=top, sole=sole, height=sole - top, left=left, right=right,
                     margin=min(top, h - sole, left, w - right))
    return m


def scan(c: dict) -> dict:
    """파일마다 지금의 상태. character.json 은 고치지 않는다 (기준 해시는 accept 로만 바뀐다)."""
    now = {}
    for k, s in c["assets"].items():
        p = ROOT / s["file"]
        st: dict = {"exists": p.exists()}
        if p.exists():
            st.update(file_facts(p))
            base = s.get("base")
            st["state"] = "그대로" if base and base["sha256"] == st["sha256"] else ("바뀜" if base else "기준 없음")
            if s["group"] in ("view", "sheet"):
                st["measure"] = measure_image(p, figure=s["group"] == "view")
            if s["group"] == "pixel_master" and s.get("info") and (ROOT / s["info"]).exists():
                d = read_json(ROOT / s["info"])
                mm = d["master"]
                st["metrics"] = {"size": mm["metrics"]["size"], "height": mm["metrics"]["height"],
                                 "head": mm["metrics"]["head"], "heads_tall": mm["metrics"]["heads_tall"],
                                 "colors": mm["metrics"]["colors"], "orphan_pct": mm["metrics"]["orphan_pct"],
                                 "spread": mm.get("spread"), "err": mm.get("err"), "cell": mm.get("cell"),
                                 "picked": d.get("picked"), "recommended": d.get("recommended")}
        else:
            st["state"] = "없음"
        now[k] = st
    return now


def worst(results: list[str]) -> str:
    order = {"실패": 3, "주의": 2, "통과": 1, "정보": 0}
    return max(results, key=lambda r: order[r]) if results else "정보"


def check_char(c: dict) -> dict:
    now = scan(c)
    A = c["assets"]
    items = []

    def add(name: str, result: str, detail: str, what: str = "원화"):
        items.append({"name": name, "result": result, "detail": detail, "what": what})

    # 1 일곱 장
    has = [k for k in SEVEN if k in A]
    missing = [LABELS[k] for k in SEVEN if k not in A or not now[k]["exists"]]
    if not has:
        add("원화 일곱 장", "정보", "설정화 묶음이 없는 캐릭터다")
    else:
        add("원화 일곱 장", "실패" if missing else "통과",
            ("없음: " + ", ".join(missing)) if missing else "정면 · 측면 · 후면 · 얼굴 · 신체 · 무기/소지품 · 포즈가 모두 있다")

    views = [k for k in VIEWS if k in A and now[k]["exists"]]
    if len(views) == 3:
        sizes = [tuple(now[k]["size"]) for k in views]
        add("세 시점의 캔버스 크기", "통과" if len(set(sizes)) == 1 else "실패",
            " / ".join(f"{LABELS[k][:2]} {s[0]}×{s[1]}" for k, s in zip(views, sizes)))
        ms = [now[k]["measure"] for k in views]
        if all("height" in m for m in ms):
            hs, ss = [m["height"] for m in ms], [m["sole"] for m in ms]
            d = (max(hs) - min(hs)) / max(hs)
            r = "통과" if d <= TH["height_pass"] else "주의" if d <= TH["height_warn"] else "실패"
            add("세 시점의 캐릭터 키", r, f"정면 {hs[0]} · 측면 {hs[1]} · 후면 {hs[2]} px (차이 {max(hs) - min(hs)}px, {d * 100:.1f}%)")
            ds = (max(ss) - min(ss)) / max(hs)
            r = "통과" if ds <= TH["height_pass"] else "주의" if ds <= TH["height_warn"] else "실패"
            add("세 시점의 발바닥 줄", r, f"정면 {ss[0]} · 측면 {ss[1]} · 후면 {ss[2]} (차이 {max(ss) - min(ss)}px)")
            low = [f"{LABELS[k][:2]} {m['margin']}px" for k, m in zip(views, ms) if m["margin"] < TH["margin_min"]]
            add("세 시점이 잘리지 않았나", "실패" if low else "통과",
                ("캔버스 끝에 닿음: " + ", ".join(low)) if low else
                "캔버스 끝까지 여백 " + " · ".join(f"{m['margin']}px" for m in ms))
        else:
            add("세 시점의 캐릭터 키", "실패", "그림에서 캐릭터를 찾지 못했다")

    # 배경 · 가장자리 (일곱 장)
    bg_bad, bg_warn, edge = [], [], []
    for k in SEVEN:
        if k in A and now[k]["exists"]:
            m = now[k]["measure"]
            if m["white_ratio"] < TH["white_warn"]:
                bg_bad.append(f"{LABELS[k]} {m['white_ratio'] * 100:.0f}%")
            elif m["white_ratio"] < TH["white_pass"]:
                bg_warn.append(f"{LABELS[k]} {m['white_ratio'] * 100:.0f}%")
            if m["edge_ink"] > TH["edge_warn"]:
                edge.append(f"{LABELS[k]} {m['edge_ink'] * 100:.1f}%")
    if has:
        r = "실패" if bg_bad else "주의" if bg_warn else "통과"
        add("배경이 흰색인가", r, ("가장자리가 흰색이 아님: " + ", ".join(bg_bad + bg_warn)) if r != "통과"
            else "일곱 장 모두 가장자리 띠의 98% 넘게 흰색")
        add("가장자리에 그림이 닿았나", "주의" if edge else "통과",
            ("가장자리 2px 에 그림이 닿음 (잘렸을 수 있다): " + ", ".join(edge)) if edge else "일곱 장 모두 가장자리에 닿은 그림이 없다")

    # 바뀜 · 없음 (모든 등록 파일)
    changed = [k for k in A if now[k]["state"] == "바뀜"]
    gone = [k for k in A if now[k]["state"] == "없음"]
    add("등록한 뒤 바뀐 파일", "주의" if changed else "통과",
        ("바뀜: " + ", ".join(f"{A[k]['label']} ({A[k]['file']})" for k in changed)) if changed
        else f"등록한 {len(A)}개 파일의 내용이 등록할 때와 같다", "모든 파일")
    if gone:
        add("없어진 파일", "실패", ", ".join(A[k]["file"] for k in gone), "모든 파일")

    # 승인 뒤 바뀜
    if not c.get("approvals"):
        add("승인 뒤 바뀐 파일", "정보", "승인 기록 없음 — 비교할 승인이 없다", "승인")
    else:
        broke = []
        for ap in c["approvals"]:
            for k, h in ap["assets"].items():
                cur = now.get(k, {}).get("sha256")
                if cur != h:
                    broke.append(f"{A.get(k, {}).get('label', k)} ({ap['date']} {ap['by']} 승인)")
        add("승인 뒤 바뀐 파일", "실패" if broke else "통과",
            ("승인한 그림이 바뀜: " + ", ".join(broke)) if broke else "승인한 파일이 모두 승인할 때와 같다", "승인")

    # 게임 스프라이트의 검사 결과(gate.json)를 옮겨 적는다
    tables = sorted({s["source"]["table"] for s in A.values() if s["group"] == "sprite" and s.get("source", {}).get("table")})
    for t in tables:
        gate = ROOT / Path(t).parent / "gate.json"
        if gate.exists():
            g = read_json(gate)
            add(f"스프라이트 검사 ({Path(t).parent.as_posix()}/gate.json)", "통과" if g.get("pass") else "실패",
                "상태별 시트를 만든 도구(state_sheets.py)의 검사 결과를 옮겨 적었다", "스프라이트")

    return {"id": c["id"], "date": today(), "result": worst([i["result"] for i in items]), "items": items, "now": now,
            "thresholds": TH}


def cmd_check(a) -> dict:
    out = {}
    for cid in (a.ids or ids_all()):
        c = load_char(cid)
        r = check_char(c)
        write_json(reg_dir() / cid / "check.json", r)
        out[cid] = r
        print(f"[check] {cid}: {r['result']}")
        for i in r["items"]:
            if i["result"] in ("주의", "실패"):
                print(f"         {i['result']} — {i['name']}: {i['detail']}")
    return out


# ---------------------------------------------------------------- report

def thumb(src: Path, dst_dir: Path, sha: str, *, height: int | None = None, width: int | None = None,
          scale: float | None = None, pixel: bool = False) -> str:
    """미리보기 그림. 이름에 해시 앞 10자를 붙여 원본이 바뀌면 새로 만든다."""
    ext = ".png" if pixel else ".jpg"
    dst = dst_dir / f"{src.stem}_{sha[:10]}{ext}"
    if not dst.exists():
        im = Image.open(src)
        if scale is None:
            scale = (height / im.height) if height else (width / im.width)
        size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
        if pixel:
            im.convert("RGBA").resize(size, Image.NEAREST).save(dst)
        else:
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[3])
            bg.resize(size, Image.LANCZOS).save(dst, quality=86)
    return dst.relative_to(reg_dir()).as_posix()


def first_frame_crop(src: Path, cell: list[int], dst_dir: Path, sha: str) -> str:
    """시트의 첫 프레임을 그림이 있는 곳만 잘라 둔다 (픽셀 마스터와 같은 배율로 견주기 위해)."""
    dst = dst_dir / f"{src.stem}_f0_{sha[:10]}.png"
    if not dst.exists():
        im = Image.open(src).convert("RGBA").crop((0, 0, cell[0], cell[1]))
        im.crop(im.getbbox()).save(dst)
    return dst.relative_to(reg_dir()).as_posix()


def cmd_report(a, checks: dict | None = None) -> None:
    rd = reg_dir()
    tdir = rd / "_report" / "thumbs"
    keep: set[Path] = set()
    chars = []
    for cid in ids_all():
        c = load_char(cid)
        chk = (checks or {}).get(cid) or (read_json(rd / cid / "check.json") if (rd / cid / "check.json").exists() else check_char(c))
        now = chk["now"]
        d = tdir / cid
        d.mkdir(parents=True, exist_ok=True)
        # 세 시점은 같은 배율로 줄인다 (캔버스가 다르면 가장 큰 것을 기준으로 한 배율)
        vh = [now[k]["size"][1] for k in VIEWS if k in c["assets"] and now[k]["exists"]]
        vscale = 720 / max(vh) if vh else None
        assets = []
        # 카드와 픽셀 마스터 비교에 쓸 게임 그림: 처음 등록한 움직이는 스프라이트(대기)의 첫 프레임
        first_sprite = next((k for k, s in c["assets"].items() if s["group"] == "sprite" and s.get("anim")), None)
        for k, s in c["assets"].items():
            st = now[k]
            item = {"key": k, **{f: s.get(f) for f in ("group", "label", "file", "source", "status", "facing", "anim", "set", "also", "info", "note", "readonly")},
                    "base": s.get("base"), "now": {f: st.get(f) for f in ("exists", "state", "sha256", "size", "bytes", "measure", "metrics")}}
            if st["exists"]:
                p = ROOT / s["file"]
                g = s["group"]
                if g == "view":
                    item["thumb"] = thumb(p, d, st["sha256"], scale=vscale)
                elif g == "pixel_master":
                    item["thumb"] = rel(p)  # 1배 그대로 (화면에서 확대)
                    raw = ROOT / (s.get("source") or {}).get("from", "")
                    if raw.is_file():
                        item["raw_thumb"] = thumb(raw, d, sha256(raw), height=360)
                elif g == "sprite":
                    item["thumb"] = rel(p)
                    if k == first_sprite:
                        item["frame0"] = first_frame_crop(p, s["anim"]["cell"], d, st["sha256"])
                else:
                    item["thumb"] = thumb(p, d, st["sha256"], width=760)
                keep.update((rd / item[t]) for t in ("thumb", "raw_thumb", "frame0") if item.get(t) and not item[t].startswith("art/"))
            assets.append(item)
        chars.append({k: c.get(k) for k in ("id", "name", "kind", "design", "story", "game", "approvals", "records", "history", "links")}
                     | {"assets": assets, "check": {k: chk[k] for k in ("date", "result", "items", "thresholds")}})
    # 쓰지 않게 된 미리보기 지우기
    for f in tdir.rglob("*.*"):
        if f not in keep:
            f.unlink()
    data = {"generated": today(), "root": "../../", "groups": GROUPS, "characters": chars}
    js = "// tools/charpipe.py report 가 만든다. 고치지 않는다.\nwindow.CHARPIPE = " + json.dumps(data, ensure_ascii=True) + ";\n"
    (rd / "_report" / "data.js").write_text(js, encoding="utf-8")
    print(f"[report] {rel(rd / 'index.html')} (자료 {rel(rd / '_report' / 'data.js')}, 미리보기 {len(keep)}장)")


def cmd_build(a) -> None:
    a.ids = []
    checks = cmd_check(a)
    cmd_report(a, checks)


def main() -> None:
    global ROOT
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="캐릭터 등록부 (기획서 9.11)")
    ap.add_argument("--root", help="프로젝트 대신 이 폴더를 다룬다 (시험용)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    p = sub.add_parser("check"); p.add_argument("ids", nargs="*")
    sub.add_parser("report")
    p = sub.add_parser("register")
    p.add_argument("id"); p.add_argument("--setting"); p.add_argument("--name"); p.add_argument("--design")
    p.add_argument("--kind", default="npc", choices=["player", "companion", "npc", "enemy"])
    p.add_argument("--height-cm", type=float); p.add_argument("--height-mark", default="")
    p = sub.add_parser("add")
    p.add_argument("id"); p.add_argument("key"); p.add_argument("file")
    p.add_argument("--group", required=True); p.add_argument("--label"); p.add_argument("--extra", help="JSON 으로 더 적을 것")
    p = sub.add_parser("add-sprites")
    p.add_argument("id"); p.add_argument("table"); p.add_argument("--names"); p.add_argument("--set", default="")
    p = sub.add_parser("add-pixel-lab"); p.add_argument("id"); p.add_argument("folder")
    p = sub.add_parser("accept"); p.add_argument("id"); p.add_argument("keys", nargs="*")
    p.add_argument("--changed", action="store_true"); p.add_argument("--note")
    p = sub.add_parser("approve"); p.add_argument("id"); p.add_argument("keys", nargs="+")
    p.add_argument("--by", required=True); p.add_argument("--note")
    a = ap.parse_args()
    if a.root:
        ROOT = Path(a.root).resolve()
    {"build": cmd_build, "check": cmd_check, "report": cmd_report, "register": cmd_register, "add": cmd_add,
     "add-sprites": cmd_add_sprites, "add-pixel-lab": cmd_add_pixel_lab, "accept": cmd_accept,
     "approve": cmd_approve}[a.cmd](a)


if __name__ == "__main__":
    main()
