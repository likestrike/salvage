"""캐릭터 픽셀 파이프라인 — 설정화에서 픽셀 마스터 · 대기 · 달리기까지 (docs/pipeline/CHARACTER_PIPELINE.md).

NX-07 한 캐릭터로 밟은 과정(기획서 9.11 ~ 9.11.6)을 캐릭터 설정 파일 하나로 다른 캐릭터에도 밟게 한다.
캐릭터에 묶인 값(이름 · 경로 · 색 · 칸 수 · 프롬프트의 캐릭터 문장 · 손본 칸 · 층의 표)은 모두
art/characters/<id>/pixel/pipeline.json 에 있다. 이 코드에는 없다.

    python -X utf8 tools/pixpipe.py status [id]            # 단계마다: 됨 / 기획자 결정 대기 / 아직
    python -X utf8 tools/pixpipe.py init <id>              # 설정 파일의 빈 틀을 만든다 (값은 비어 있다)
    python -X utf8 tools/pixpipe.py prompts <id>           # 1 · 2단계 프롬프트를 공통 틀 + 캐릭터 문장으로 쓴다 (API 호출 없음)
    python -X utf8 tools/pixpipe.py s1 <id> [--plan A] [--dry-run]      # 1단계 뽑기 (밑그림 없이). fal.ai 호출
    python -X utf8 tools/pixpipe.py guide <id> [--job C36]               # 밑그림 (목표 칸 수로 다시 깔기, 머리 비율 보정)
    python -X utf8 tools/pixpipe.py s2 <id> [--job C36] [--dry-run]     # 2단계 뽑기 (격자 그대로 다시 그리기). fal.ai 호출
    python -X utf8 tools/pixpipe.py master <id> [--job C36]              # 마스터 만들기 (알려진 격자로 칸 읽기 · 색 묶기 · 칸 손보기)
    python -X utf8 tools/pixpipe.py measure <id>           # 재기: 형식(통과/실패)과 그림(참고 그림과의 거리)을 따로
    python -X utf8 tools/pixpipe.py compare <id>           # 비교 그림 (기획자가 보는 그림)
    python -X utf8 tools/pixpipe.py pick <id> --job C36 --quote "원문" [--layer scarf=S2] [--saw 그림]   # 기획자가 고른 것을 적는다
    python -X utf8 tools/pixpipe.py layer <id>             # 층 더하기 (고른 마스터 위에, 설정 파일의 표대로)
    python -X utf8 tools/pixpipe.py approve <id> --quote "원문" [--saw 그림]   # 기획자의 승인을 적는다 (마스터를 제자리로 복사 · 등록 · 승인)
    python -X utf8 tools/pixpipe.py spec <id>              # 규격 (승인된 마스터에서 잰다)
    python -X utf8 tools/pixpipe.py rig-init <id>          # 애니메이션 표(rig.json)의 틀과 대기(변형) 타임라인을 만든다
    python -X utf8 tools/pixpipe.py anim <id> [idle run]   # 애니메이션: 프레임 · 검사 · 시트 · GIF · 비교 그림
    python -X utf8 tools/pixpipe.py together <id> --with nx07:scarf [idle run]   # 승인된 다른 캐릭터와 같은 게임 화면 · 발바닥 줄에 함께 (GIF)
    python -X utf8 tools/pixpipe.py review <id> --quote "원문" [--verdict 받아들임]   # 기획자의 애니메이션 평가를 적는다
    python -X utf8 tools/pixpipe.py report                 # 등록부 검사와 보고 화면 (charpipe build)

  스튜디오(tools/pixstudio.py)가 부르는 명령 — 명령줄에서도 같다 (CHARACTER_PIPELINE.md 12장)
    python -X utf8 tools/pixpipe.py defaults <id> [--form 값.json] [--add]   # 캐릭터에 묶이지 않은 기본 문장 + 기획자의 메모로 설정을 채운다
    python -X utf8 tools/pixpipe.py fix <id> --job A38 --cell 5,6 (--color '#rrggbb' | --transparent) --why "이유"   # 칸 손보기
    python -X utf8 tools/pixpipe.py unfix <id> --job A38 --cell 5,6        # 칸 손보기 되돌리기
    python -X utf8 tools/pixpipe.py reject <id> --job A38 --quote "원문"     # 기획자가 후보를 채택하지 않음
    python -X utf8 tools/pixpipe.py candidates <id>        # 후보 마스터를 등록부에 올린다 (실험 · 승인 기록 없음)
    python -X utf8 tools/pixpipe.py lineup <id> [--with nx07:scarf]   # 승인된 캐릭터와 후보를 어두운 게임 화면에 함께 (1배)
  환경 변수 PIXPIPE_MOCK_FROM=mirine 이면 s1 · s2 가 fal.ai 를 부르지 않고 그 캐릭터의 그림을 복사한다 (스튜디오의 연습 모드)
    python -X utf8 tools/pixpipe.py verify nx07            # NX-07 재현 검증 (이미지 생성 0회)
    python -X utf8 tools/pixpipe.py ref-targets [--check]  # 참고 그림의 숫자를 다시 잰다 (참고 그림이 PC 에 있을 때만)

사람의 결정 (도구가 대신 정하지 않는다)
- 단순화안: [제안]이어도 뽑기는 진행한다 (뽑기 기록에 "[제안]으로 진행"을 남긴다). 기획자가 정하면 simplify.status 를 "결정"으로.
- 고름(pick): 없으면 층 · 승인이 멈춘다.
- 승인(approve): 없으면 규격 · 애니메이션이 멈춘다. --allow-unapproved 로 돌리면 결과에 "승인 기록 없음"이 찍힌다.
- 평가(review): 기록만 한다. 다음 동작(걷기 · 점프)은 평가 뒤에 한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import pixel_measure as pm  # noqa: E402
from pixel_master import head_height, load_cutout  # noqa: E402
from process_sheet import key_mask  # noqa: E402

COMMON = ROOT / "art/characters/_pipeline"
TEMPLATE_CFG = COMMON / "pipeline.template.json"
TARGETS = COMMON / "reference_targets.json"
S1_TPL = ROOT / "art/prompts/pipeline/_stage1.txt"
S2_TPL = ROOT / "art/prompts/pipeline/_stage2.txt"
FAL = ROOT / "tools/fal_image.py"
MAGENTA = (255, 0, 255)
FONT, FONT_B = "C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"
BG, PANEL = (18, 20, 28), (34, 37, 50)
TXT, SUB, GOLD, BAD = (236, 236, 242), (160, 166, 184), (240, 196, 80), (230, 110, 100)

# 단계 (순서 = NX-07 에서 실제로 밟은 순서). who: 에이전트 / 기획자 / 에이전트 + fal.ai
STEPS = [
    ("register", "등록 · 원화 검사", "에이전트", "charpipe.py register · build"),
    ("simplify", "도트판 단순화안", "기획자 (에이전트가 [제안])", "pipeline.json 의 simplify"),
    ("s1", "1단계 뽑기 (밑그림 없이)", "에이전트 + fal.ai", "pixpipe s1"),
    ("guide", "밑그림 (목표 칸 수 · 머리 비율)", "에이전트", "pixpipe guide"),
    ("s2", "2단계 뽑기 (격자 그대로)", "에이전트 + fal.ai", "pixpipe s2"),
    ("master", "마스터 · 칸 손보기", "에이전트", "pixpipe master"),
    ("measure", "재기", "에이전트", "pixpipe measure"),
    ("compare", "비교 그림", "에이전트", "pixpipe compare"),
    ("pick", "기획자가 고름", "기획자", "pixpipe pick"),
    ("layer", "층 더하기", "에이전트 (층이 여럿이면 기획자가 고름)", "pixpipe layer"),
    ("approve", "승인 기록", "기획자", "pixpipe approve"),
    ("spec", "규격 (그림에서 잰다)", "에이전트", "pixpipe spec"),
    ("anim", "애니메이션 · 검사 · 내보내기", "에이전트", "pixpipe rig-init · anim"),
    ("review", "기획자 평가", "기획자", "pixpipe review"),
]
STATE_DONE, STATE_WAIT, STATE_TODO, STATE_NA = "됨", "기획자 결정 대기", "아직", "해당 없음"


# ---------------------------------------------------------------- 작은 도구

def today() -> str:
    return date.today().isoformat()


def rel(p: Path) -> str:
    p = Path(p)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, data, indent: int = 1) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def font(n: int, bold: bool = False):
    try:
        return ImageFont.truetype(FONT_B if bold else FONT, n)
    except OSError:
        return ImageFont.load_default()


def hexrgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hx(c) -> str:
    return "%02x%02x%02x" % tuple(int(v) for v in c[:3])


def die(msg: str) -> None:
    sys.exit(f"[pixpipe] {msg}")


def fill(text: str, values: dict) -> str:
    """{이름} 칸을 채운다. 채운 문장 안의 {이름}도 채운다. 남은 칸이 있으면 멈춘다."""
    for _ in range(4):
        new = re.sub(r"\{([a-z0-9_]+)\}", lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), text)
        if new == text:
            break
        text = new
    left = re.findall(r"\{([a-z0-9_]+)\}", text)
    if left:
        die(f"프롬프트의 칸이 채워지지 않았다: {sorted(set(left))} (pipeline.json 의 prompt 를 채운다)")
    return text


def template(p: Path) -> str:
    return "\n".join(l for l in p.read_text(encoding="utf-8").splitlines() if not l.startswith("##")).strip()


# ---------------------------------------------------------------- 캐릭터 설정

class Ctx:
    """캐릭터 하나의 설정과 파일 자리. replay 를 주면 모든 쓰기를 그 폴더 아래로 돌린다 (읽기는 고정된 원본을 그대로)."""

    def __init__(self, cid: str, replay: Path | None = None):
        self.cid = cid
        self.cfg_path = ROOT / "art/characters" / cid / "pixel" / "pipeline.json"
        if not self.cfg_path.exists():
            die(f"{rel(self.cfg_path)} 가 없다. 먼저 pixpipe init {cid}")
        self.cfg = read_json(self.cfg_path)
        self.replay = replay
        P = self.cfg["paths"]
        self.dirs = {k: ROOT / v.format(id=cid) for k, v in P.items()}
        if replay:
            self.dirs = {k: Path(replay) / k for k in P}

    def save(self) -> None:
        if self.replay:
            return
        write_json(self.cfg_path, self.cfg, indent=1)

    # 경로
    @property
    def work(self) -> Path:
        return self.dirs["work"]

    def plans(self) -> dict:
        return self.cfg.get("plans") or {}

    def jobs(self) -> dict:
        return self.cfg.get("jobs") or {}

    def pinned(self, kind: str, name: str, key: str) -> Path | None:
        """그때 실제로 쓴 파일 (NX-07 처럼 파이프라인 전에 만든 캐릭터). 없으면 None."""
        d = (self.plans() if kind == "plan" else self.jobs()).get(name, {})
        v = (d.get("pinned") or {}).get(key)
        return ROOT / v if v else None

    def find(self, default: Path, pinned: Path | None) -> Path:
        """읽을 파일: 이 파이프라인이 만든 것이 있으면 그것, 없으면 고정된 원본."""
        if default.exists():
            return default
        if pinned is not None and pinned.exists():
            return pinned
        return default

    def s1_out(self, plan: str) -> Path:
        return self.work / "s1" / f"{self.cid}_s1_{plan}.png"

    def s1_raw(self, plan: str) -> Path:
        return self.find(self.s1_out(plan), self.pinned("plan", plan, "s1_raw"))

    def guide_out(self, job: str) -> Path:
        return self.dirs["prompts"] / f"guide_{job}.png"

    def guide_used(self, job: str) -> Path:
        return self.find(self.guide_out(job), self.pinned("job", job, "guide"))

    def s2_out(self, job: str) -> Path:
        return self.work / "s2" / f"{self.cid}_s2_{job}.png"

    def s2_raw(self, job: str) -> Path:
        return self.find(self.s2_out(job), self.pinned("job", job, "s2_raw"))

    def master_out(self, job: str) -> Path:
        return self.work / job / f"{self.cid}_{job}_master.png"

    def master(self, job: str) -> Path:
        return self.find(self.master_out(job), self.pinned("job", job, "master"))

    def layer_out(self, layer: str, option: str) -> Path:
        return self.work / "layers" / f"{self.cid}_{layer}_{option}.png"

    def layer_file(self, layer: str, option: str) -> Path:
        o = self.cfg["layers"][layer]["options"][option]
        return self.find(self.layer_out(layer, option), ROOT / o["pinned"] if o.get("pinned") else None)

    def final(self, variant: str) -> Path:
        return self.dirs["final"] / f"{self.cid}_px_{variant}.png"

    def variants(self) -> list[str]:
        """승인될 마스터의 벌: base(층 없음) + 층마다 하나."""
        return ["base"] + list((self.cfg.get("layers") or {}).keys())

    def guides_json(self) -> Path:
        return self.work / "guides" / "guides.json"

    def gen_log(self) -> Path:
        return self.work / "gen_log.json"


def ctx_of(a) -> Ctx:
    """명령의 설정. 재현 검증(verify)은 a.ctx 로 쓰기 자리를 돌린 설정을 넘긴다."""
    return getattr(a, "ctx", None) or Ctx(a.id)


# ---------------------------------------------------------------- init · status

def cmd_init(a) -> None:
    p = ROOT / "art/characters" / a.id / "pixel" / "pipeline.json"
    if p.exists():
        die(f"이미 있다: {rel(p)}")
    import charpipe as cp
    cfg = read_json(TEMPLATE_CFG)
    cfg["id"] = a.id
    c = cp.load_char(a.id)  # 등록되지 않았으면 멈춘다
    cfg["name"] = c["name"]
    cfg["story_height_cm"] = (c.get("story") or {}).get("height_cm")
    avail = [f"{k}: {s['file']}" for k, s in c["assets"].items() if s["group"] in ("view", "sheet", "design", "design_ref")]
    cfg["_available_files"] = avail
    write_json(p, cfg)
    (ROOT / "art/characters" / a.id / "pixel" / "work").mkdir(parents=True, exist_ok=True)
    print(f"[init] {rel(p)} — 값은 비어 있다. CHARACTER_PIPELINE.md 의 체크리스트대로 채운다")


def approvals(cid: str) -> dict[str, bool]:
    """px_<variant> 의 승인이 지금 파일과 같은 해시로 있는가."""
    import charpipe as cp
    try:
        c = cp.load_char(cid)
    except SystemExit:
        return {}
    out = {}
    for ap in c.get("approvals", []):
        for k, h in ap["assets"].items():
            if k.startswith("px_") and k in c["assets"]:
                f = ROOT / c["assets"][k]["file"]
                out[k[3:]] = f.exists() and sha(f) == h
    return out


def status(cid: str) -> list[dict]:
    """단계마다 상태. charpipe 의 보고 화면도 이것을 쓴다."""
    import charpipe as cp
    rows = []
    cfg_p = ROOT / "art/characters" / cid / "pixel" / "pipeline.json"

    def add(key, state, detail=""):
        st = next(s for s in STEPS if s[0] == key)
        rows.append({"key": key, "name": st[1], "who": st[2], "cmd": st[3], "state": state, "detail": detail})

    chk = ROOT / "art/characters" / cid / "check.json"
    if cp.char_path(cid).exists():
        r = read_json(chk)["result"] if chk.exists() else "검사 전"
        add("register", STATE_DONE if r in ("통과", "주의", "정보") else STATE_TODO, f"원화 검사 {r}")
    else:
        add("register", STATE_TODO, "등록되지 않았다")
    if not cfg_p.exists():
        for k in [s[0] for s in STEPS[1:]]:
            add(k, STATE_TODO, "pipeline.json 없음 (pixpipe init)")
        return rows
    x = Ctx(cid)
    cfg = x.cfg
    sim = cfg.get("simplify") or {}
    if not sim.get("prompt"):
        add("simplify", STATE_TODO, "단순화안이 비어 있다")
    elif sim.get("status") == "결정":
        add("simplify", STATE_DONE, sim.get("note", "기획자 결정"))
    else:
        add("simplify", STATE_WAIT, "[제안] 상태 — 뽑기는 [제안]으로 진행할 수 있다")
    plans, jobs = x.plans(), x.jobs()
    have = [p for p in plans if x.s1_raw(p).exists()]
    add("s1", STATE_DONE if plans and len(have) == len(plans) else STATE_TODO, f"{len(have)}/{len(plans)} 안")
    have = [j for j in jobs if x.guide_used(j).exists()]
    add("guide", STATE_DONE if jobs and len(have) == len(jobs) else STATE_TODO, f"{len(have)}/{len(jobs)} 후보")
    have = [j for j in jobs if x.s2_raw(j).exists()]
    add("s2", STATE_DONE if jobs and len(have) == len(jobs) else STATE_TODO, f"{len(have)}/{len(jobs)} 후보")
    have = [j for j in jobs if x.master(j).exists()]
    add("master", STATE_DONE if jobs and len(have) == len(jobs) else STATE_TODO, f"{len(have)}/{len(jobs)} 후보")
    pinned_measure = (cfg.get("pinned") or {}).get("measure")
    add("measure", STATE_DONE if (x.work / "measure.json").exists() or pinned_measure else STATE_TODO,
        "work/measure.json" if (x.work / "measure.json").exists() else (f"그때의 측정: {pinned_measure}" if pinned_measure else ""))
    pinned_cmp = (cfg.get("pinned") or {}).get("compare")
    add("compare", STATE_DONE if (x.work / "compare.png").exists() or pinned_cmp else STATE_TODO,
        "work/compare.png" if (x.work / "compare.png").exists() else (f"그때의 비교 그림: {pinned_cmp}" if pinned_cmp else ""))
    dec = cfg.get("decisions") or {}
    pick = dec.get("pick")
    if pick:
        add("pick", STATE_DONE, f"{pick['job']} ({pick.get('date', '')}) \"{pick.get('quote', '')}\"")
    else:
        add("pick", STATE_WAIT if (x.work / "compare.png").exists() else STATE_TODO, "")
    layers = cfg.get("layers") or {}
    if not layers:
        add("layer", STATE_NA, "층 없음 (설정의 layers 가 비어 있다)")
    else:
        parts = []
        state = STATE_DONE
        for ln, L in layers.items():
            ch = (dec.get("layers") or {}).get(ln)
            built = [o for o in L["options"] if x.layer_file(ln, o).exists()]
            if not built:
                state = STATE_TODO if state == STATE_DONE else state
                parts.append(f"{ln}: 아직")
            elif not ch:
                state = STATE_WAIT
                parts.append(f"{ln}: 변형 {len(built)}개, 고르지 않음")
            else:
                parts.append(f"{ln}: {ch['option']}")
        if not pick:
            state = STATE_TODO
        add("layer", state, " · ".join(parts))
    ap = approvals(cid)
    vs = x.variants()
    ok = [v for v in vs if ap.get(v)]
    if len(ok) == len(vs):
        add("approve", STATE_DONE, " · ".join(f"px_{v}" for v in vs))
    else:
        add("approve", STATE_WAIT if pick else STATE_TODO, f"승인 기록 {len(ok)}/{len(vs)} 벌")
    spec = x.dirs["final"] / f"{cid}_px_spec.json"
    add("spec", STATE_DONE if spec.exists() else STATE_TODO, rel(spec) if spec.exists() else "")
    anims = (cfg.get("anim") or {}).get("anims") or []
    done = []
    for n in anims:
        ck = x.dirs["anim"] / n / "check.json"
        if ck.exists() and read_json(ck)["summary"].get("pass"):
            done.append(n)
    add("anim", STATE_DONE if anims and len(done) == len(anims) else STATE_TODO,
        f"{len(done)}/{len(anims)} 동작 ({', '.join(anims)})" if anims else "동작을 정하지 않았다")
    rv = dec.get("review")
    if rv:
        add("review", STATE_DONE, f"{rv.get('verdict', '')} ({rv.get('date', '')}) \"{rv.get('quote', '')}\"")
    else:
        add("review", STATE_WAIT if anims and len(done) == len(anims) else STATE_TODO, "")
    return rows


def cmd_status(a) -> None:
    import charpipe as cp
    ids = a.ids or cp.ids_all()
    for cid in ids:
        print(f"== {cid}")
        for r in status(cid):
            print(f"  {r['state']:<10} {r['name']:<24} {r['detail']}")


# ---------------------------------------------------------------- 프롬프트

def prompt_values(x: Ctx) -> dict:
    P = dict(x.cfg.get("prompt") or {})
    need = ["subject", "top_of_figure", "facing_note", "figure", "pose", "materials_merge", "accent_strokes", "saturated",
            "colors", "s1_cell", "s1_height"]
    miss = [k for k in need if not P.get(k)]
    if miss:
        die(f"pipeline.json 의 prompt 가 비어 있다: {miss}")
    refs = x.cfg.get("references") or []
    if not refs:
        die("pipeline.json 의 references 가 비어 있다 (설정화의 측면 · 정면 등)")
    for r in refs:
        if "guide" in Path(r["file"]).name:
            die(f"1단계에는 밑그림을 넣지 않는다 (v1 의 실패: 뻣뻣한 밑그림을 옮겼다): {r['file']}")
    sim = x.cfg.get("simplify") or {}
    if not sim.get("prompt"):
        die("단순화안(simplify.prompt)이 비어 있다. 기획자가 정하거나 에이전트가 [제안]으로 채운다")
    v = {k: P[k] for k in P if not isinstance(P[k], (list, dict))}
    v["references"] = "\n".join(f"- image {i} = {r['role']}" for i, r in enumerate(refs, 1))
    v["pose"] = "\n".join(f"- {s}" for s in P["pose"])
    v["s1_height_px"] = int(P["s1_cell"]) * int(P["s1_height"])
    v["simplify"] = sim["prompt"]
    return v


def s1_prompt(x: Ctx, plan: str) -> str:
    v = prompt_values(x)
    pl = x.plans()[plan]
    body = fill(template(S1_TPL), v)
    block = f"LIGHT AND DARK PLAN — \"{pl['title']}\":\n" + "\n".join(f"- {b}" for b in pl["s1"])
    return body + "\n\n" + fill(block, v)


def s2_prompt(x: Ctx, job: str, g: dict) -> str:
    v = prompt_values(x)
    P = x.cfg["prompt"]
    J = x.jobs()[job]
    t = int(J["height"])
    for row in P.get("s2_vars") or []:
        if t <= row["max_height"]:
            v.update({k: val for k, val in row.items() if k != "max_height"})
            break
    for k in ("s2_image1", "s2_curves", "s2_accents", "s2_keep_color", "s2_figure"):
        if not P.get(k):
            die(f"pipeline.json 의 prompt.{k} 가 비어 있다")
    v["s2_parts"] = "\n".join(f"- {s}" for s in P.get("s2_parts") or [])
    v.update(c=g["cell"], ox=g["origin"][0], oy=g["origin"][1], t=t, plan=x.plans()[J["plan"]]["s2"])
    return fill(template(S2_TPL), v)


def write_prompt(x: Ctx, name: str, text: str) -> Path:
    p = x.dirs["prompts"] / f"{name}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text + "\n", encoding="utf-8")
    return p


def cmd_prompts(a) -> None:
    x = ctx_of(a)
    for plan in x.plans():
        print("[prompts]", rel(write_prompt(x, f"s1_{plan}", s1_prompt(x, plan))))
    if x.guides_json().exists():
        g = read_json(x.guides_json())
        for job in x.jobs():
            if job in g:
                print("[prompts]", rel(write_prompt(x, f"s2_{job}", s2_prompt(x, job, g[job]))))
    else:
        print("[prompts] 2단계 프롬프트는 밑그림(pixpipe guide) 뒤에 쓴다")


# ---------------------------------------------------------------- 뽑기 (fal.ai)

def mock_source(x: Ctx, step: str, name: str, mock: str) -> Path:
    """연습: 이미 뽑아 둔 다른 캐릭터(mock)의 그림. 밝기 계획은 순서대로 그 캐릭터의 안(A · B · C …)에 맞춘다."""
    m = Ctx(mock)
    mplans = list(m.plans())
    plan = name if step == "s1" else x.jobs()[name]["plan"]
    mp = mplans[list(x.plans()).index(plan) % len(mplans)]
    if step == "s1":
        src = m.s1_raw(mp)
    else:
        mj = next((j for j, J in m.jobs().items() if J["plan"] == mp and m.s2_raw(j).exists()), None)
        src = m.s2_raw(mj) if mj else Path("")
    if not src.exists():
        die(f"연습에 쓸 그림이 없다: {mock} {step} {mp}")
    return src


def gen(x: Ctx, step: str, name: str, prompt_file: Path, refs: list[Path], out: Path, dry: bool, over: bool) -> None:
    G = x.cfg.get("generate") or {}
    log_p = x.gen_log()
    log = read_json(log_p) if log_p.exists() else []
    used = sum(1 for e in log if not e.get("dry_run"))
    budget = G.get("budget")
    if not dry:
        if budget is None:
            die("generate.budget (이 캐릭터에 쓸 이미지 생성 횟수의 상한)이 비어 있다. 기획자와 정해 적는다")
        if used + 1 > budget and not over:
            die(f"이미지 생성 상한 {budget}회를 넘는다 (지금까지 {used}회). 기획자에게 묻고 --over-budget")
    for r in refs:
        if not r.exists():
            die(f"참조 그림이 없다: {rel(r)}")
        if rel(r).startswith("reference/pixel_style"):  # 다른 회사의 참고 그림은 생성기에 올리지 않는다 (9.11.1)
            die(f"다른 회사의 참고 그림은 생성기에 보내지 않는다: {rel(r)}")
    w, h = G.get("image_size", [1024, 1024])
    mock = os.environ.get("PIXPIPE_MOCK_FROM")
    if mock and not dry:  # 연습 (스튜디오의 시험 방식): fal.ai 를 부르지 않고 이미 뽑아 둔 다른 캐릭터의 그림을 복사한다
        src = mock_source(x, step, name, mock)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out)
        entry = {"date": today(), "step": step, "name": name, "dry_run": False, "mock": rel(src), "model": "연습 (이미지 생성 없음)",
                 "prompt_file": {"path": rel(prompt_file), "sha256": sha(prompt_file)},
                 "refs": [{"path": rel(p), "sha256": sha(p)} for p in refs],
                 "out": {"path": rel(out), "sha256": sha(out)}}
        log.append(entry)
        write_json(log_p, log)
        print(f"[{step}] 연습 — 이미지 생성 없이 {rel(src)} 를 복사 · 기록 {rel(log_p)} · 지금까지 {used + 1}회 (연습 포함)")
        return
    cmd = [sys.executable, "-X", "utf8", str(FAL), "--model", G.get("model", "openai/gpt-image-2.6/sunburst/edit"),
           "--prompt-file", str(prompt_file)]
    for r in refs:
        cmd += ["--ref", str(r)]
    cmd += ["--aspect", "none", "--resolution", "none", "--arg", "image_size=" + json.dumps({"width": w, "height": h})]
    for k, v in (G.get("args") or {}).items():
        cmd += ["--arg", f"{k}={v}"]
    cmd += ["--out", str(out)]
    if dry:
        cmd.append("--dry-run")
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if not (dry and x.replay):  # 재현 검증의 dry-run 은 프롬프트 전문을 찍지 않는다 (verify.json 에서 견준다)
        print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr.strip())
        die(f"fal_image.py 실패 ({step} {name})")
    sim = (x.cfg.get("simplify") or {}).get("status")
    entry = {"date": today(), "step": step, "name": name, "dry_run": dry, "model": G.get("model"),
             "prompt_file": {"path": rel(prompt_file), "sha256": sha(prompt_file)},
             "refs": [{"path": rel(p), "sha256": sha(p)} for p in refs],
             "args": {"image_size": [w, h], **(G.get("args") or {})},
             "simplify_status": sim if sim == "결정" else "[제안]으로 진행 (기획자 결정 없음)"}
    if not dry and out.exists():
        with Image.open(out) as im:
            entry["out"] = {"path": rel(out), "sha256": sha(out), "size": list(im.size)}
    log.append(entry)
    write_json(log_p, log)
    print(f"[{step}] {'dry-run (호출 안 함)' if dry else '뽑음'} — 기록 {rel(log_p)} · 지금까지 생성 {used + (0 if dry else 1)}회")


def cmd_s1(a) -> None:
    x = ctx_of(a)
    plans = a.plan or list(x.plans())
    if not plans:
        die("plans(밝기 계획의 변형)가 비어 있다")
    refs = [ROOT / r["file"] for r in x.cfg["references"]]
    for plan in plans:
        pf = write_prompt(x, f"s1_{plan}", s1_prompt(x, plan))
        gen(x, "s1", plan, pf, refs, x.s1_out(plan), a.dry_run, a.over_budget)


def cmd_s2(a) -> None:
    x = ctx_of(a)
    if not x.guides_json().exists():
        die("밑그림이 없다. 먼저 pixpipe guide")
    g = read_json(x.guides_json())
    for job in a.job or list(x.jobs()):
        if job not in g:
            die(f"{job} 의 밑그림이 없다 (pixpipe guide --job {job})")
        pf = write_prompt(x, f"s2_{job}", s2_prompt(x, job, g[job]))
        J = x.jobs()[job]
        gen(x, "s2", job, pf, [x.s1_raw(J["plan"]), x.guide_used(job)], x.s2_out(job), a.dry_run, a.over_budget)


# ---------------------------------------------------------------- 밑그림 (옛 v2/make_guide.py)

def cell_color(a: np.ndarray, x0: float, x1: float, y0: float, y1: float):
    """원본 사각형의 가운데 60% 에서 가장 많은 색. 반 넘게 배경이면 None."""
    h, w = a.shape[:2]
    mx, my = (x1 - x0) * 0.2, (y1 - y0) * 0.2
    xa, xb = int(round(x0 + mx)), int(round(x1 - mx))
    ya, yb = int(round(y0 + my)), int(round(y1 - my))
    xa, ya = max(xa, 0), max(ya, 0)
    xb, yb = min(max(xb, xa + 1), w), min(max(yb, ya + 1), h)
    if xa >= w or ya >= h or xb <= 0 or yb <= 0:
        return None
    p = a[ya:yb, xa:xb].reshape(-1, 4)
    fg = p[p[:, 3] > 0][:, :3].astype(int)
    if len(fg) < 0.5 * len(p):
        return None
    q = fg // 10
    keys, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    sel = fg[inv.ravel() == cnt.argmax()]
    return tuple(int(v) for v in np.round(sel.mean(0)))


def build_guide(a: np.ndarray, T: int, heads: float, head_px: int | None = None) -> tuple[np.ndarray, dict]:
    """1단계 그림을 목표 칸 수 T 로 다시 깐다. 머리(정수리 ~ 목)와 몸을 따로 줄여 heads 등신으로 맞춘다.
    head_px 를 주면 목을 자동으로 찾지 않고 그 값(정수리에서 목까지의 원본 px)을 쓴다 — 긴 머리카락 · 넓은 옷처럼
    '가장 좁은 줄 = 목'이 맞지 않는 그림 (미리네 A, CHARACTER_PIPELINE.md 11장)."""
    op = a[..., 3] > 0
    ys, xs = np.where(op)
    top, bot = ys.min(), ys.max() + 1
    H, head = head_height(a[top:bot, xs.min():xs.max() + 1])
    auto_head = head
    if head_px:
        head = int(head_px)
    neck = top + head
    nx = np.where(op[neck])[0]
    anchor = float(nx.mean())
    hh = int(round(T / heads))
    hb = T - hh
    sh = head / hh
    sb = (bot - neck) / hb
    left = max(anchor - xs.min(), 1)
    right = max(xs.max() + 1 - anchor, 1)
    ai = int(np.ceil(left / min(sh, sb))) + 1
    W = ai + int(np.ceil(right / min(sh, sb))) + 1
    cells = np.zeros((T, W, 4), np.uint8)
    for j in range(T):
        if j < hh:
            s, y0 = sh, top + j * sh
        else:
            s, y0 = sb, neck + (j - hh) * sb
        for i in range(W):
            x0 = anchor + (i - ai) * s
            c = cell_color(a, x0, x0 + s, y0, y0 + s)
            if c is not None:
                cells[j, i, :3] = c
                cells[j, i, 3] = 255
    cols = np.where(cells[..., 3].any(0))[0]
    cells = cells[:, cols.min():cols.max() + 1]
    meta = {"src_head_px": int(head), "src_height_px": int(H), "head_cells": hh, "body_cells": hb,
            "src_cell_head": round(sh, 2), "src_cell_body": round(sb, 2)}
    if head_px:  # 손으로 준 목일 때만 적는다 (NX-07 재현의 guides.json 은 그대로)
        meta.update({"neck": "설정의 head_px (손으로 잰 값)", "auto_head_px": int(auto_head)})
    return cells, meta


def cmd_guide(a) -> None:
    x = ctx_of(a)
    size = x.cfg.get("size") or {}
    heads = size.get("heads_guide")
    if not heads:
        die("size.heads_guide (밑그림의 머리 비율 목표)가 비어 있다")
    W, H = (x.cfg.get("generate") or {}).get("image_size", [1024, 1024])
    out = x.work / "guides"
    out.mkdir(parents=True, exist_ok=True)
    info = read_json(x.guides_json()) if x.guides_json().exists() else {}
    for job in a.job or list(x.jobs()):
        J = x.jobs()[job]
        src = x.s1_raw(J["plan"])
        if not src.exists():
            die(f"1단계 그림이 없다: {rel(src)} (pixpipe s1 --plan {J['plan']})")
        T, C = int(J["height"]), int(J["cell"])
        cells, meta = build_guide(load_cutout(src), T, float(heads), x.plans()[J["plan"]].get("head_px"))
        h, w = cells.shape[:2]
        ox, oy = (W - w * C) // 2, (H - h * C) // 2
        g = Image.new("RGB", (W, H), MAGENTA)
        big = Image.fromarray(cells, "RGBA").resize((w * C, h * C), Image.NEAREST)
        g.paste(big, (ox, oy), big)
        gp = x.guide_out(job)
        gp.parent.mkdir(parents=True, exist_ok=True)
        g.save(gp)
        Image.fromarray(cells, "RGBA").save(out / f"{job}_cells.png")
        Image.fromarray(cells, "RGBA").resize((w * 8, h * 8), Image.NEAREST).save(out / f"{job}_cells_x8.png")
        hh2, hd2 = head_height(cells)
        info[job] = {"guide": rel(gp), "from": rel(src), "cell": C, "origin": [ox, oy], "cells": [w, h],
                     "heads": round(hh2 / hd2, 2), **meta}
        if "neck" in meta:  # 목을 손으로 줬으면 자동 측정(가장 좁은 줄)은 믿을 수 없다
            info[job]["heads_auto"] = info[job]["heads"]
            info[job]["heads"] = round(T / meta["head_cells"], 2)
        print(f"[guide] {job}: {rel(gp)} 칸 {C}px 원점 ({ox}, {oy}) {w}×{h} · {info[job]['heads']}등신")
    write_json(x.guides_json(), info)


# ---------------------------------------------------------------- 마스터 (옛 v2/make_master.py + v1 의 색 묶기 · 저장)

def grid_read(rgb: np.ndarray, cell: int, ox: int, oy: int) -> tuple[float, int, np.ndarray]:
    """알려진 격자로 칸을 읽는다. 칸 가운데의 90% 넘게 대표색과 같은 칸 = 고른 칸."""
    bg = key_mask(rgb)
    h, w = rgb.shape[:2]
    m = max(2, int(round(cell * 0.2)))
    nx, ny = (w - ox) // cell, (h - oy) // cell
    good = tot = 0
    out = np.zeros((ny, nx, 4), np.uint8)
    for j in range(ny):
        for i in range(nx):
            y0, x0 = oy + j * cell, ox + i * cell
            if bg[y0:y0 + cell, x0:x0 + cell].mean() > 0.5:
                continue
            inner = rgb[y0 + m:y0 + cell - m, x0 + m:x0 + cell - m].reshape(-1, 3).astype(int)
            q = inner // 12
            keys, inv, cnt = np.unique(q, axis=0, return_inverse=True, return_counts=True)
            rep = inner[inv.ravel() == cnt.argmax()].mean(0)
            same = (np.abs(inner - rep).sum(1) < 40).mean()
            tot += 1
            good += same > 0.9
            out[j, i, :3] = np.round(rep).astype(np.uint8)
            out[j, i, 3] = 255
    return good / max(1, tot), tot, out


def merge_colors(m: np.ndarray, target: int, stop: float) -> tuple[np.ndarray, list[dict]]:
    """색 묶기. Lab ΔE 가 가장 가까운 두 색부터 (칸이 적은 쪽을 많은 쪽 색으로). target 색이 되거나 stop 보다 멀면 멈춘다."""
    op = m[..., 3] > 0
    cols, cnt = np.unique(m[op][:, :3].astype(int), axis=0, return_counts=True)
    L = pm.lab(cols)
    root = list(range(len(cols)))
    weight = {i: int(cnt[i]) for i in range(len(cols))}
    alive = list(range(len(cols)))
    merged = []
    while len(alive) > target:
        best = None
        for ai in range(len(alive)):
            for bi in range(ai + 1, len(alive)):
                p, q = alive[ai], alive[bi]
                dd = float(np.linalg.norm(L[p] - L[q]))
                if best is None or dd < best[0]:
                    best = (dd, p, q)
        dd, p, q = best
        if dd > stop:
            break
        big, small = (p, q) if weight[p] >= weight[q] else (q, p)
        root = [big if r == small else r for r in root]
        merged.append({"from": hx(cols[small]), "into": hx(cols[big]), "cells": weight[small], "dE": round(dd, 1)})
        weight[big] += weight.pop(small)
        alive.remove(small)
    out = m.copy()
    lut = {tuple(int(v) for v in cols[i]): cols[root[i]] for i in range(len(cols))}
    ys, xs = np.where(op)
    for y, x in zip(ys, xs):
        out[y, x, :3] = lut[tuple(int(v) for v in m[y, x, :3])]
    return out, merged


def palette_of(m: np.ndarray) -> np.ndarray:
    op = m[..., 3] > 0
    cols = np.unique(m[op][:, :3], axis=0)
    lum = cols @ np.array([0.299, 0.587, 0.114])
    return cols[np.argsort(lum)]


def save_master(m: np.ndarray, d: Path, stem: str, extra: dict) -> dict:
    d.mkdir(parents=True, exist_ok=True)
    pal = palette_of(m)
    Image.fromarray(m, "RGBA").save(d / f"{stem}.png")
    Image.fromarray(m, "RGBA").resize((m.shape[1] * 8, m.shape[0] * 8), Image.NEAREST).save(d / f"{stem}_x8.png")
    (d / f"{stem}_palette.hex").write_text("\n".join(hx(c) for c in pal) + "\n", encoding="utf-8")
    gpl = ["GIMP Palette", f"Name: {stem}", "Columns: 8", "#"] + [f"{c[0]:3d} {c[1]:3d} {c[2]:3d}\t{hx(c)}" for c in pal]
    (d / f"{stem}_palette.gpl").write_text("\n".join(gpl) + "\n", encoding="utf-8")
    hh, hd = head_height(m)
    f = pm.fmt(m, {tuple(int(v) for v in c) for c in pal})
    mt = {"size": [m.shape[1], m.shape[0]], "height": hh, "head": hd, "heads_tall": round(hh / hd, 2), **f}
    # charpipe.py 가 읽는 모양 (master.metrics)
    info = {"master": {"name": "known-grid", "cell": extra.get("grid", {}).get("cell"), "metrics": mt, "spread": 0.0},
            "picked": "known-grid", "recommended": None, "metrics": mt, **extra}
    write_json(d / f"{stem}_info.json", info)
    return mt


def cmd_master(a) -> None:
    x = ctx_of(a)
    if not x.guides_json().exists():
        die("밑그림의 격자(guides.json)가 없다. 먼저 pixpipe guide")
    g = read_json(x.guides_json())
    pal = x.cfg.get("palette") or {}
    target, stop = int(pal.get("max_colors", 16)), float(pal.get("merge_stop_dE", 14.0))
    res = read_json(x.work / "grid_check.json") if (x.work / "grid_check.json").exists() else {}
    for job in a.job or list(x.jobs()):
        raw = x.s2_raw(job)
        if not raw.exists():
            die(f"2단계 그림이 없다: {rel(raw)}")
        gi = g[job]
        c, (ox, oy) = gi["cell"], gi["origin"]
        rgb = np.array(Image.open(raw).convert("RGB"))
        r0, n, m = grid_read(rgb, c, ox, oy)
        r1, _, _ = grid_read(rgb, c, ox + c // 2, oy + c // 2)
        ys, xs = np.where(m[..., 3] > 0)
        m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        d = x.master_out(job).parent
        d.mkdir(parents=True, exist_ok=True)
        stem = f"{x.cid}_{job}"
        Image.fromarray(m, "RGBA").save(d / f"{stem}_known.png")
        res[job] = {"cell": c, "origin": [ox, oy], "good": round(r0, 3), "half": round(r1, 3), "cells": n, "size": list(m.shape[1::-1])}
        mm, merged = merge_colors(m, target, stop)
        mm[..., 3] = np.where(mm[..., 3] > 0, 255, 0)
        base = {"src": rel(raw), "grid": {"cell": c, "origin": [ox, oy], "good": round(r0, 3)}, "guide": gi["guide"],
                "method": f"알려진 격자의 칸 대표색 → Lab ΔE 가 가까운 색끼리 묶기 (목표 {target}색, ΔE {stop:g} 넘으면 멈춤)",
                "merged": merged, "made_by": "tools/pixpipe.py master", "doc": "docs/pipeline/CHARACTER_PIPELINE.md"}
        fx = x.jobs()[job].get("fixes") or []
        if fx:
            save_master(mm, d, f"{stem}_unfixed", base | {"note": "손보기 전"})
            log = []
            for f in fx:
                (cx, cy), (sx, sy) = f["cell"], f["from"]
                before = hx(mm[cy, cx]) if mm[cy, cx, 3] else "투명"
                mm[cy, cx] = mm[sy, sx]
                after = hx(mm[cy, cx]) if mm[cy, cx, 3] else "투명"
                log.append({"cell": [cx, cy], "before": before, "after": after, "color_from": [sx, sy], "why": f["why"]})
            write_json(d / f"{stem}_fixes.json", log)
            base = base | {"fixes": f"{stem}_fixes.json", "unfixed": f"{stem}_unfixed.png"}
        mt = save_master(mm, d, f"{stem}_master", base)
        flag = "" if r0 >= 0.9 else "  ← 격자가 맞지 않은 칸이 많다. 그림을 보고 다시 뽑을지 정한다"
        print(f"[master] {job}: 고른 칸 {r0 * 100:.0f}% (반 칸 민 격자 {r1 * 100:.0f}%) · {mt['size'][0]}×{mt['size'][1]} · {mt['colors']}색"
              f" · 반투명 {mt['semi_transparent']} · 팔레트 이탈 {mt['off_palette']} · 손본 칸 {len(fx)}{flag}")
    write_json(x.work / "grid_check.json", res)


# ---------------------------------------------------------------- 층 (옛 v3_scarf/make_scarf.py)

def layer_table(rows) -> dict[tuple[int, int], str]:
    out = {}
    for y, x0, s in rows:
        for i, ch in enumerate(s):
            if ch == ".":
                continue
            out[(x0 + i, y)] = ch
    return out


def build_layer(base: np.ndarray, L: dict, option: str) -> tuple[np.ndarray, int, dict, dict]:
    o = L["options"][option]
    rows = []
    for part in o["parts"]:
        rows += L["parts"][part]
    t = layer_table(rows)
    for k in L.get("protect") or []:
        assert tuple(k) not in t, f"지켜야 할 칸(얼굴 · 엠블럼 등)을 덮는다: {k}"
    minx = min(xx for xx, _ in t)
    pad = max(0, -minx)
    h, w = base.shape[:2]
    out = np.zeros((h, w + pad, 4), np.uint8)
    out[:, pad:] = base
    pal = L["colors"][o["color"]]
    for (xx, yy), ch in t.items():
        out[yy, xx + pad] = hexrgb(pal[ch]) + (255,)
    # 표 밖의 칸이 바뀌지 않았는가
    inner = out[:, pad:]
    diff = (inner != base).any(2)
    allowed = np.zeros((h, w), bool)
    for (xx, yy) in t:
        if 0 <= xx < w:
            allowed[yy, xx] = True
    stray = diff & ~allowed
    assert not stray.any(), f"층의 표 밖의 칸이 바뀌었다: {np.argwhere(stray)}"
    op0 = base[..., 3] > 0
    n_out = int((out[:, :pad, 3] > 0).sum())
    chk = {"cells_replaced": int((diff & op0).sum()), "cells_added": int((diff & ~op0).sum()) + n_out,
           "base_cells": int(op0.sum()), "base_cells_unchanged": int((~diff & op0).sum()), "other_cells_changed": int(stray.sum())}
    return out, pad, t, chk


def picked_master(x: Ctx) -> Path:
    pick = (x.cfg.get("decisions") or {}).get("pick")
    if not pick:
        die("기획자가 고른 후보가 없다 (decisions.pick). 비교 그림을 보이고 기획자의 말을 pixpipe pick 으로 적는다")
    return x.master(pick["job"])


def cmd_layer(a) -> None:
    x = ctx_of(a)
    layers = x.cfg.get("layers") or {}
    if not layers:
        print("[layer] 층이 없다 (해당 없음)")
        return
    base = np.array(Image.open(picked_master(x)).convert("RGBA"))
    for ln, L in layers.items():
        for opt in L["options"]:
            out, pad, t, chk = build_layer(base, L, opt)
            p = x.layer_out(ln, opt)
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(out, "RGBA").save(p)
            Image.fromarray(out, "RGBA").resize((out.shape[1] * 12, out.shape[0] * 12), Image.NEAREST).save(p.with_name(p.stem + "_x12.png"))
            write_json(p.with_name(p.stem + "_info.json"),
                       {"layer": ln, "option": opt, "label": L["options"][opt].get("label"), "base": rel(picked_master(x)),
                        "canvas_pad_left": pad, "size": [int(out.shape[1]), int(out.shape[0])], "diff_vs_base": chk,
                        "made_by": "tools/pixpipe.py layer", "mark": L.get("mark", "")})
            print(f"[layer] {ln} {opt}: {rel(p)} · 넓힘 {pad} · 덮음 {chk['cells_replaced']} 더함 {chk['cells_added']}")
        if len(L["options"]) > 1 and not ((x.cfg.get("decisions") or {}).get("layers") or {}).get(ln):
            print(f"[layer] {ln}: 변형 {len(L['options'])}개 — 기획자가 고른다 (pixpipe pick {x.cid} --layer {ln}=<변형> --quote …)")


# ---------------------------------------------------------------- 재기 · 비교 그림

def targets() -> dict:
    return read_json(TARGETS)["figures"] if TARGETS.exists() else {}


def candidates(x: Ctx) -> list[tuple[str, str, Path]]:
    """(이름, 설명, 파일): 후보 마스터와 층 변형."""
    out = []
    for job, J in x.jobs().items():
        p = x.master(job)
        if p.exists():
            out.append((job, f"{x.plans()[J['plan']].get('label', J['plan'])} · {J['height']}칸", p))
    for ln, L in (x.cfg.get("layers") or {}).items():
        for opt, o in L["options"].items():
            p = x.layer_file(ln, opt)
            if p.exists():
                out.append((f"{ln}:{opt}", o.get("label", opt), p))
    return out


def measure_all(x: Ctx) -> dict:
    T = targets()
    gc = read_json(x.work / "grid_check.json") if (x.work / "grid_check.json").exists() else {}
    items = {}
    for name, label, p in candidates(x):
        a = pm.crop(pm.load_rgba(p))
        pic = pm.picture(a)
        f = pm.fmt(a)
        f["grid_good"] = gc.get(name, {}).get("good")
        items[name] = {"label": label, "file": rel(p), "format": f, "picture": pic,
                       "distance": {k: pm.distance(pic.get(k), T, k) for k, _, _ in pm.PICTURE_KEYS}}
    return {"date": today(), "targets": rel(TARGETS), "items": items,
            "note": "형식은 통과 · 실패가 있다. 그림은 참고 그림과의 거리일 뿐이다. 마지막 판정은 기획자의 눈이다 (9.11.3)."}


def cmd_measure(a) -> None:
    x = ctx_of(a)
    res = measure_all(x)
    write_json(x.work / "measure.json", res)
    T = targets()
    for name, it in res["items"].items():
        f, p = it["format"], it["picture"]
        print(f"[measure] {name} — 형식 {'통과' if f['pass'] else '실패'} (반투명 {f['semi_transparent']} · 팔레트 이탈 {f['off_palette']}"
              f" · 격자 {f['grid_good']} · {f['colors']}색 · 외톨이 {f['orphan_pct']}%)")
        for k, lab, unit in pm.PICTURE_KEYS:
            refs = " · ".join(f"{d['ref']} {d['value']}" for d in it["distance"][k])
            print(f"           {lab}: {p.get(k)}{unit}  (참고: {refs})")
    if not T:
        print("[measure] 참고 숫자 파일이 없다:", rel(TARGETS))
    print("[measure]", rel(x.work / "measure.json"))


def dark_screen(a: np.ndarray, screen: list[int], z: int, press=(0.25, 0.70), crop_w: int = 96) -> Image.Image:
    """어두운 게임 화면(지금 게임의 배경을 화면 높이로 줄이고 누른 것)에 실제 크기로 세운다."""
    w, h = screen
    src = Image.open(ROOT / "game/assets/style_c/bg.png").convert("RGB")
    k = h / src.height
    bg = src.resize((int(round(src.width * k)), h), Image.NEAREST).crop((0, 0, w, h))
    keep, dim = press
    bg = Image.blend(bg.convert("L").convert("RGB"), bg, keep).convert("RGBA")
    floor = int(round(h * 304 / 360))
    bg.alpha_composite(Image.new("RGBA", (w, floor), (10, 12, 24, int(255 * dim))))
    ImageDraw.Draw(bg).rectangle([0, floor, w, h], fill=(18, 19, 28, 255))
    cx = w // 2
    bg.alpha_composite(Image.fromarray(a, "RGBA"), (cx - a.shape[1] // 2, floor - a.shape[0]))
    x0 = max(0, cx - crop_w // 2)
    return bg.crop((x0, max(0, floor - a.shape[0] - 12), x0 + crop_w, min(h, floor + 8))).convert("RGB").resize(
        (crop_w * z, (min(h, floor + 8) - max(0, floor - a.shape[0] - 12)) * z), Image.NEAREST)


def on_panel(a: np.ndarray, z: int, h_cells: int | None = None) -> Image.Image:
    h_cells = h_cells or a.shape[0]
    cell = Image.new("RGBA", (a.shape[1], h_cells), PANEL + (255,))
    cell.alpha_composite(Image.fromarray(a, "RGBA"), (0, h_cells - a.shape[0]))
    return cell.convert("RGB").resize((a.shape[1] * z, h_cells * z), Image.NEAREST)


def thumb_h(p: Path, h: int) -> Image.Image:
    im = Image.open(p).convert("RGB")
    return im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)


def compare_image(x: Ctx, res: dict, with_refs: dict | None = None) -> Image.Image:
    Z = 10
    screen = (x.cfg.get("screen") or {}).get("size") or [320, 180]
    W = 2200
    img = Image.new("RGB", (W, 6000), BG)
    d = ImageDraw.Draw(img)
    d.text((32, 20), f"{x.cfg['name']} 픽셀 마스터 후보 — 비교 그림 (tools/pixpipe.py compare)", font=font(30, True), fill=TXT)
    d.text((32, 62), f"후보마다: 1단계 그림 · 밑그림 · 2단계 그림 · 마스터 (모두 같은 배율) · 어두운 게임 화면 {screen[0]}×{screen[1]} ×3. "
                     f"아래 표의 그림 숫자는 참고 그림과의 거리다 (통과 · 실패가 아니다). 고르는 것은 기획자다.", font=font(16), fill=SUB)
    y = 110
    g = read_json(x.guides_json()) if x.guides_json().exists() else {}
    maxh = max((pm.load_rgba(p).shape[0] for _, _, p in candidates(x)), default=36)
    Z = max(4, 380 // maxh)  # 마스터의 확대: 가장 큰 후보가 약 380px 높이가 되게 (같은 배율로 견준다)
    for name, label, p in candidates(x):
        a = pm.crop(pm.load_rgba(p))
        d.text((32, y), f"{name} — {label}", font=font(20, True), fill=GOLD)
        y += 32
        xx = 32
        row_h = maxh * Z
        if name in x.jobs():
            J = x.jobs()[name]
            for t, q in (("1단계", x.s1_raw(J["plan"])), ("밑그림", x.guide_used(name)), ("2단계", x.s2_raw(name))):
                if q.exists():
                    im = thumb_h(q, row_h)
                    img.paste(im, (xx, y))
                    d.text((xx, y + row_h + 4), t, font=font(14), fill=SUB)
                    xx += im.width + 14
        mp = on_panel(a, Z, maxh)
        img.paste(mp, (xx, y))
        d.text((xx, y + row_h + 4), f"마스터 {a.shape[1]}×{a.shape[0]} ×{Z}", font=font(14), fill=SUB)
        xx += mp.width + 14
        ds = dark_screen(a, screen, 3)
        img.paste(ds, (xx, y + row_h - ds.height))
        d.text((xx, y + row_h + 4), "어두운 게임 화면 ×3", font=font(14), fill=SUB)
        it = res["items"].get(name)
        y += row_h + 28
        if it:
            tx = 32
            f, pc = it["format"], it["picture"]
            lines = [(f"형식: {'통과' if f['pass'] else '실패'} — 반투명 {f['semi_transparent']} · 팔레트 이탈 {f['off_palette']} · "
                      f"격자 {('%d%%' % round(100 * f['grid_good'])) if f.get('grid_good') is not None else '—'} · {f['colors']}색 · 외톨이 {f['orphan_pct']}%",
                      TXT if f["pass"] else BAD)]
            lines.append((f"키 {pc['height']} · 머리 {pc['head']} · {pc['heads_tall']}등신", SUB))
            pics = []
            for k, lab, unit in pm.PICTURE_KEYS:
                refs = " · ".join(f"{dd['ref']} {'—' if dd['value'] is None else dd['value']}" for dd in it["distance"][k])
                pics.append(f"{lab} {'—' if pc.get(k) is None else pc.get(k)}{unit} ({refs})")
            lines.append(("그림 (참고 그림과의 거리, 통과 · 실패 없음): " + " / ".join(pics[:4]), SUB))
            lines.append(("    " + " / ".join(pics[4:]), SUB))
            for i, (t, col) in enumerate(lines):
                d.text((tx, y + i * 22), t, font=font(15), fill=col)
            y += len(lines) * 22
        y += 30
    if with_refs:
        d.text((32, y), "참고 그림의 인물 (다른 회사의 작품, 1배로 복원) — 이 그림은 공개하지 않는다", font=font(20, True), fill=GOLD)
        y += 32
        xx = 32
        for nm, a in with_refs.items():
            mp = on_panel(a, Z)
            img.paste(mp, (xx, y))
            d.text((xx, y + mp.height + 4), nm, font=font(14), fill=SUB)
            xx += mp.width + 24
        y += max(a.shape[0] for a in with_refs.values()) * Z + 40
    T = targets()
    if T:
        d.text((32, y), "참고 숫자 (art/characters/_pipeline/reference_targets.json): " +
               " / ".join(f"{t.get('label', k)}: " + ", ".join(f"{lab} {t['picture'].get(kk)}" for kk, lab, _ in pm.PICTURE_KEYS[:3]) for k, t in T.items()),
               font=font(14), fill=SUB)
        y += 30
    return img.crop((0, 0, W, y + 10))


def ref_figures() -> dict | None:
    """참고 그림이 PC 에 있으면 1배로 복원한 인물들. 없으면 None (비교 그림의 그 줄만 건너뛴다)."""
    if not TARGETS.exists():
        return None
    src = read_json(TARGETS)["source"]
    p = ROOT / src["image"]
    if not p.exists():
        return None
    a = pm.restore_grid(p)
    bg = np.array(hexrgb(src["bg"]))
    dd = np.linalg.norm(pm.lab(a[..., :3]) - pm.lab(bg), axis=2)
    a[dd < src["bg_dE"], 3] = 0
    a = pm.cluster_colors(a, src["cluster_dE"])
    gm = np.zeros(a.shape[:2], bool)
    gm[src["split"]["row"]:, src["split"]["col"]:] = True
    out = {}
    for nm, where in src["figures"].items():
        b = a.copy()
        b[gm if where == "outside" else ~gm, 3] = 0
        out[nm] = pm.crop(b)
    return out


def cmd_compare(a) -> None:
    x = ctx_of(a)
    res = read_json(x.work / "measure.json") if (x.work / "measure.json").exists() else measure_all(x)
    p = x.work / "compare.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    compare_image(x, res).save(p)
    print("[compare]", rel(p))
    refs = ref_figures()
    if refs:
        q = ROOT / "reference/pixel_style/analysis" / f"compare_{x.cid}_pipeline.png"
        compare_image(x, res, refs).save(q)
        print("[compare] 참고 그림과 나란히 (공개하지 않는 폴더):", rel(q))
    else:
        print("[compare] 참고 그림이 PC 에 없어 참고 그림과 나란히 놓는 그림은 건너뛴다")


# ---------------------------------------------------------------- 기획자의 결정을 적는다

def record(cid: str, kind: str, what: str, quote: str, keys: list[str], saw: list[str] | None, note: str = "") -> None:
    import charpipe as cp
    c = cp.load_char(cid)
    r = {"date": today(), "by": "기획자", "kind": kind, "what": what, "quote": quote, "keys": keys,
         "doc": "docs/pipeline/CHARACTER_PIPELINE.md", "note": note}
    if saw:
        r["saw"] = saw
    c.setdefault("records", []).append(r)
    cp.log(c, f"기획자 {kind} 기록", by="agent", note=what)
    cp.save_char(c)


def mark_candidates(x: Ctx, job: str) -> None:
    """등록부에 올린 후보(pm_<후보>)의 상태에 고름을 적는다 (NX-07 에서는 손으로 했다, 11장). 올리지 않은 후보는 건너뛴다."""
    import charpipe as cp
    c = cp.load_char(x.cid)
    n = 0
    for j in x.jobs():
        k = f"pm_{j}"
        if k not in c["assets"]:
            continue
        if j == job:
            c["assets"][k]["status"] = f"작업 폴더의 원본 · 기획자가 {job} 를 골랐다 ({today()}). 승인되면 px_base 로 복사한다"
        else:
            c["assets"][k]["status"] = f"실험 · 채택하지 않음 — 기획자가 {job} 를 골랐다 ({today()})"
        n += 1
    if n:
        cp.log(c, "후보의 상태에 고름을 적음", by="agent", note=f"{job} (pixpipe pick)")
        cp.save_char(c)


def cmd_pick(a) -> None:
    x = ctx_of(a)
    dec = x.cfg.setdefault("decisions", {})
    if a.job:
        if a.job not in x.jobs() or not x.master(a.job).exists():
            die(f"후보가 없다: {a.job}")
        dec["pick"] = {"job": a.job, "date": today(), "quote": a.quote, "saw": a.saw or [rel(x.work / "compare.png")]}
        (dec.get("rejected") or {}).pop(a.job, None)  # 채택하지 않았던 후보를 다시 고르면 그 표시만 지운다 (등록부의 기록은 남는다)
        record(x.cid, "결정", f"픽셀 마스터 후보 가운데 {a.job} 를 골랐다", a.quote, [a.job], a.saw)
        mark_candidates(x, a.job)
        print(f"[pick] {a.job}")
    for item in a.layer or []:
        ln, _, opt = item.partition("=")
        L = (x.cfg.get("layers") or {}).get(ln)
        if not L or opt not in L["options"]:
            die(f"층 변형이 없다: {item}")
        dec.setdefault("layers", {})[ln] = {"option": opt, "date": today(), "quote": a.quote}
        record(x.cid, "결정", f"층 {ln} 의 변형 가운데 {opt} 를 골랐다", a.quote, [f"{ln}:{opt}"], a.saw)
        print(f"[pick] 층 {ln} = {opt}")
    x.save()


def cmd_approve(a) -> None:
    """기획자가 대화에서 승인했을 때만. 고른 마스터(와 층 변형)를 제자리로 복사하고, 등록부에 올리고, 승인을 적는다."""
    import charpipe as cp
    x = ctx_of(a)
    dec = x.cfg.get("decisions") or {}
    src = {"base": picked_master(x)}
    for ln in (x.cfg.get("layers") or {}):
        ch = (dec.get("layers") or {}).get(ln)
        if not ch:
            die(f"층 {ln} 의 변형을 고르지 않았다 (pixpipe pick --layer {ln}=…)")
        src[ln] = x.layer_file(ln, ch["option"])
    c = cp.load_char(x.cid)
    hashes = {}
    for v, s in src.items():
        dst = x.final(v)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s, dst)
        key = f"px_{v}"
        label = f"픽셀 마스터 · {'층 없음' if v == 'base' else (x.cfg['layers'][v].get('label') or v)}"
        if key not in c["assets"]:
            c["assets"][key] = cp.new_asset("pixel_master", label, rel(dst),
                                            {"made_by": "tools/pixpipe.py approve (고른 후보를 복사)", "from": rel(s),
                                             "doc": "docs/pipeline/CHARACTER_PIPELINE.md"}, status=f"승인 ({today()}, 기획자)", facing="right")
        else:
            base = c["assets"][key].get("base") or {}
            if base.get("sha256") != sha(dst):
                ver = (base.get("version") or 0) + 1
                c["assets"][key]["base"] = {"version": ver, "date": today(), **cp.file_facts(dst)}
                cp.log(c, "새 판으로 받아들임", by="agent", asset=key, version=ver, note="pixpipe approve")
            c["assets"][key]["status"] = f"승인 ({today()}, 기획자)"
        hashes[key] = sha(dst)
        print(f"[approve] {key} = {rel(dst)}")
    pj = (dec.get("pick") or {}).get("job")
    if pj and f"pm_{pj}" in c["assets"]:
        c["assets"][f"pm_{pj}"]["status"] = f"작업 폴더의 원본 · 기획자가 {pj} 를 골랐다 ({dec['pick'].get('date', '')}). 승인된 마스터 px_base 로 복사했다 ({today()})"
    ap = {"date": today(), "by": "기획자", "assets": hashes, "note": a.note or "pixpipe approve", "quote": a.quote}
    if a.saw:
        ap["saw"] = a.saw
    c["approvals"].append(ap)
    cp.log(c, "승인", by="기획자", assets=list(hashes), note="pixpipe approve")
    cp.save_char(c)
    x.cfg.setdefault("decisions", {})["approved"] = {"date": today(), "quote": a.quote, "variants": list(src)}
    x.save()


def register_output(x: Ctx, key: str, group: str, label: str, file: Path, source: dict, status: str | None = None, **extra) -> None:
    """파이프라인이 만든 것(규격 · 애니메이션 시트)을 등록부에 올린다. 있으면 해시가 바뀐 때만 새 판. 재현 검증(replay)에서는 하지 않는다.
    (NX-07 에서는 손으로 올렸다 — 11장)"""
    if x.replay:
        return
    import charpipe as cp
    c = cp.load_char(x.cid)
    if key not in c["assets"]:
        c["assets"][key] = cp.new_asset(group, label, rel(file), source, **({"status": status} if status else {}), **extra)
        cp.log(c, "파일 더함", by="agent", asset=key, file=rel(file), note="pixpipe")
    else:
        a = c["assets"][key]
        a.update({"label": label, "source": source, **extra})
        if status and not str(a.get("status", "")).startswith("기획자 평가:"):
            a["status"] = status
        base = a.get("base") or {}
        if base.get("sha256") != sha(file):
            ver = (base.get("version") or 0) + 1
            a["base"] = {"version": ver, "date": today(), **cp.file_facts(file)}
            cp.log(c, "새 판", by="agent", asset=key, version=ver, note="pixpipe")
    cp.save_char(c)


def require_approved(x: Ctx, allow: bool) -> str:
    ap = approvals(x.cid)
    miss = [v for v in x.variants() if not ap.get(v)]
    if not miss:
        return "승인"
    if x.replay:
        return "재현 검증 (승인된 마스터와 해시가 같은지 따로 확인한다)"
    if not allow:
        die(f"승인 기록 없음: {', '.join('px_' + v for v in miss)}. 기획자의 승인 뒤 pixpipe approve. "
            f"승인 전에 돌려 보려면 --allow-unapproved (결과에 '승인 기록 없음'이 찍힌다)")
    print(f"[pixpipe] 주의: 승인 기록 없음 ({', '.join(miss)}) — 결과에 그렇게 적는다")
    return "승인 기록 없음"


# ---------------------------------------------------------------- 규격 (옛 nx07/pixel/make_spec.py)

def spec_data(x: Ctx) -> tuple[dict, dict]:
    S = x.cfg.get("spec") or {}
    parts = S.get("parts")
    if not parts:
        die("spec.parts (머리 · 몸통 · 다리의 줄, 앞쪽 팔의 사각형)가 비어 있다")
    masters = {v: x.final(v) for v in x.variants()}
    for v, p in masters.items():
        if not p.exists():
            die(f"승인된 마스터가 없다: {rel(p)}")
    b = np.array(Image.open(masters["base"]).convert("RGBA"))
    h, w = b.shape[:2]
    op = b[..., 3] > 0
    ys, xs = np.where(op)
    top, sole = int(ys.min()), int(ys.max()) + 1
    arm = parts.get("near_arm")
    part = np.full((h, w), "", object)
    for yy in range(h):
        for xx in range(w):
            if not op[yy, xx]:
                continue
            if arm and arm[0] <= xx <= arm[2] and arm[1] <= yy <= arm[3]:
                part[yy, xx] = "near_arm"
            elif parts["head"][0] <= yy <= parts["head"][1]:
                part[yy, xx] = "head"
            elif parts["upper"][0] <= yy <= parts["upper"][1]:
                part[yy, xx] = "upper"
            else:
                part[yy, xx] = "legs"
    counts = {k: int((part == k).sum()) for k in ("head", "upper", "near_arm", "legs")}
    # 바뀌어도 되는 칸 (머리 · 몸통 띠 안에 있지만 프레임마다 고쳐 찍어도 되는 곳. 미리네: 긴 머리카락의 끝 · 앞쪽 손). 없으면 전과 같다
    free_rects = parts.get("free") or []
    free = np.zeros((h, w), bool)
    for fr in free_rects:
        x0, y0, x1, y1 = fr["rect"]
        free[max(0, y0):y1 + 1, max(0, x0):x1 + 1] = True
    free &= np.isin(part, ["head", "upper"])
    names = S.get("palette_names") or {}
    bands = {k: parts[k] for k in ("head", "upper", "legs")}
    band_label = S.get("band_labels") or {"head": "머리", "upper": "몸통 · 팔", "legs": "다리"}
    allcols = {}
    arrays = {v: np.array(Image.open(p).convert("RGBA")) for v, p in masters.items()}
    for v, arr in arrays.items():
        for c in arr[arr[..., 3] > 0]:
            allcols[hx(c)] = True
    pal = []
    lum = lambda c: sum(int(c[i:i + 2], 16) * k for i, k in ((0, .2126), (2, .7152), (4, .0722)))  # noqa: E731
    for c in sorted(allcols, key=lum):
        rgb = np.array(hexrgb(c))
        cells = {v: int(((arr[..., :3] == rgb).all(-1) & (arr[..., 3] > 0)).sum()) for v, arr in arrays.items()}
        rows = sorted({band_label[k] for k, (a0, a1) in bands.items()
                       for yy, xx in zip(*np.where((b[..., :3] == rgb).all(-1) & op)) if a0 <= yy <= a1})
        key, name, use = (names.get(c) or ["", "?", ""])
        pal.append({"hex": "#" + c, "key": key, "name": name, "use": use, "cells": cells, "in_base": cells["base"] > 0,
                    "rows": rows or ["층"]})
    layers = {}
    for ln, L in (x.cfg.get("layers") or {}).items():
        s = arrays[ln]
        ch = ((x.cfg.get("decisions") or {}).get("layers") or {}).get(ln, {}).get("option")
        pad = s.shape[1] - w
        inner = s[:, pad:]
        diff = (inner != b).any(-1)
        covers = [[int(xx), int(yy)] for yy, xx in zip(*np.where(diff & op))]
        adds = [[int(xx), int(yy)] for yy, xx in zip(*np.where(diff & ~op))] + \
               [[int(xx) - pad, int(yy)] for yy, xx in zip(*np.where(s[:, :pad, 3] > 0))]
        fixed = sorted([list(k) for k in layer_table(L["parts"][L["fixed_part"]])]) if L.get("fixed_part") else []
        layers[ln] = {"option": ch, "pad_left": pad, "fixed_cells": fixed, "covers_base_cells": covers, "adds_cells": adds,
                      "counts": {"covers": len(covers), "adds": len(adds), "fixed": len(fixed)},
                      "colors": ["#" + v for v in L["colors"][L["options"][ch]["color"]].values()] if ch else [],
                      "rule": L.get("rule", ""), "story": L.get("story", "")}
    hh, hd = head_height(b)
    inv = {
        "_": "[제안] 프레임이 바뀌어도 칸 단위로 옮기기만 하고 한 칸도 바꾸지 않는 부분",
        "fixed": [{"part": "head", "rows": parts["head"], "cells": counts["head"]},
                  {"part": "upper (앞쪽 팔 제외)", "rows": parts["upper"], "cells": counts["upper"]}],
        "free": [{"part": "legs", "rows": parts["legs"], "cells": counts["legs"]},
                 {"part": "near_arm", "rect": arm, "cells": counts["near_arm"]}],
        "limit": "윗몸이 돌거나 주포 · 무기를 드는 동작(공격 · 피격)에서는 이 고정을 풀어야 한다. 그 동작은 이 방법의 범위 밖이다",
    }
    if free_rects:
        inv["fixed"] = [{"part": "head", "rows": parts["head"], "cells": int(((part == "head") & ~free).sum())},
                        {"part": "upper (앞쪽 팔 · 바뀌어도 되는 칸 제외)", "rows": parts["upper"],
                         "cells": int(((part == "upper") & ~free).sum())}]
        inv["free"] += [{"part": fr.get("label", "free"), "rect": fr["rect"],
                         "cells": int(free[max(0, fr["rect"][1]):fr["rect"][3] + 1, max(0, fr["rect"][0]):fr["rect"][2] + 1].sum())}
                        for fr in free_rects]
        inv["fixed_cells_total"] = sum(f["cells"] for f in inv["fixed"])
    for k in ("near_arm_label",):
        if parts.get(k):
            inv[k] = parts[k]
    bottom = np.where(op[sole - 1])[0]
    runs = np.split(bottom, np.where(np.diff(bottom) > 1)[0] + 1)
    data = {
        "format": "salvage-pixel-spec/2",
        "character": x.cid,
        "doc": "docs/pipeline/CHARACTER_PIPELINE.md",
        "_": "이 캐릭터를 픽셀로 그릴 때 지키는 규칙. 숫자는 tools/pixpipe.py spec 이 승인된 마스터에서 잰 값이다. 글은 pipeline.json 의 spec 에서 온다.",
        "masters": {v: {"file": rel(p), "size": [int(arrays[v].shape[1]), int(arrays[v].shape[0])],
                        "colors": int(len({hx(c) for c in arrays[v][arrays[v][..., 3] > 0]}))} for v, p in masters.items()},
        "canvas": {"master_base": [w, h], "top_row": top, "sole_row": sole,
                   "bottom_row_runs": [[int(r[0]), int(r[-1])] for r in runs if len(r)]},
        "height": {"cells": sole - top, "bands": {band_label[k]: {"rows": list(v), "cells_tall": v[1] - v[0] + 1} for k, v in bands.items()},
                   "measured_head": {"height": hh, "head": hd, "heads_tall": round(hh / hd, 1)}},
        "parts_cells": counts,
        "rules": S.get("rules") or {},
        "palette": pal,
        "materials": S.get("materials") or [],
        "simplified": S.get("simplified") or [],
        "layers": layers,
        "invariant_proposal": {**inv, "fixed": inv["fixed"] + [{"part": f"{ln} 의 고정 부분", "cells": len(v["fixed_cells"])}
                                                               for ln, v in layers.items()]},
        "measured_by": "tools/pixpipe.py spec",
    }
    if S.get("hand_measured"):  # 자동 측정이 틀리는 캐릭터 (긴 머리: 11장). 손으로 잰 값을 함께 적는다
        data["height"]["hand_measured"] = S["hand_measured"]
    return data, {"b": b, "arrays": arrays, "part": part, "counts": counts, "free": free}


def cmd_spec(a) -> None:
    x = ctx_of(a)
    state = require_approved(x, a.allow_unapproved)
    data, raw = spec_data(x)
    data["approval"] = state
    p = x.dirs["final"] / f"{x.cid}_px_spec.json"
    write_json(p, data)
    draw_spec(x, data, raw).save(p.with_suffix(".png"))
    register_output(x, "px_spec", "pixel_spec", "픽셀 마스터 규격 그림 (부위 · 팔레트 · 기준점)", p.with_suffix(".png"),
                    {"made_by": "tools/pixpipe.py spec (승인된 마스터에서 잼)", "doc": "docs/pipeline/CHARACTER_PIPELINE.md"},
                    also={"json": rel(p)})
    unnamed = [c["hex"] for c in data["palette"] if c["name"] == "?"]
    print(f"[spec] {rel(p)} · {rel(p.with_suffix('.png'))} · 부위 칸 {data['parts_cells']} · 승인: {state}")
    if unnamed:
        print(f"[spec] 이름이 없는 색 {len(unnamed)}개 — spec.palette_names 에 적는다: {', '.join(unnamed)}")


def draw_spec(x: Ctx, data: dict, raw: dict) -> Image.Image:
    Z = 16
    PC = {"head": (255, 92, 92), "upper": (120, 200, 120), "near_arm": (255, 210, 80), "legs": (110, 130, 255)}
    arrays, part = raw["arrays"], raw["part"]
    S = x.cfg.get("spec") or {}
    PL = {"head": "머리", "upper": "몸통", "near_arm": "앞쪽 팔", "legs": "다리", **(S.get("part_labels") or {})}
    free = raw.get("free")
    img = Image.new("RGB", (1900, 1400), BG)
    d = ImageDraw.Draw(img)
    d.text((32, 20), f"{x.cfg['name']} 픽셀 마스터 규격 — {data['approval']} (tools/pixpipe.py spec)", font=font(30, True), fill=TXT)
    d.text((32, 64), f"숫자는 승인된 마스터에서 잰 값이다. 부위 지도: 빨강 {PL['head']} · 초록 {PL['upper']} · 노랑 {PL['near_arm']} · 파랑 {PL['legs']}"
           + (f" · 보라 {PL.get('free', '바뀌어도 되는 칸')}" if free is not None and free.any() else "") + ".", font=font(17), fill=SUB)
    xx, y0 = 40, 110
    for v, arr in arrays.items():
        im = on_panel(arr, Z)
        img.paste(im, (xx, y0 + 30))
        d.text((xx, y0), v, font=font(19, True), fill=TXT)
        xx += im.width + 50
    b = raw["b"]
    m = np.zeros_like(b)
    for yy in range(b.shape[0]):
        for x2 in range(b.shape[1]):
            if part[yy, x2]:
                m[yy, x2] = (PC[part[yy, x2]] if free is None or not free[yy, x2] else (190, 120, 255)) + (255,)
    im = on_panel(m, Z)
    img.paste(im, (xx, y0 + 30))
    d.text((xx, y0), "부위 지도", font=font(19, True), fill=TXT)
    tx = xx + im.width + 50
    ty = y0 + 30
    hm = data["height"].get("hand_measured")
    lines = [f"키 {data['height']['cells']}칸 · 발바닥 줄 {data['canvas']['sole_row']} · 캔버스 {data['canvas']['master_base']}"]
    for k, v in data["height"]["bands"].items():
        lines.append(f"{k}: {v['rows'][0]}~{v['rows'][1]}줄 ({v['cells_tall']}칸)")
    mh = data["height"]["measured_head"]
    lines.append(f"자동 측정 머리 {mh['head']}칸 · {mh['heads_tall']}등신" + (" — 믿지 않는다 (아래 손으로 잰 값)" if hm else ""))
    if hm:
        lines += [f"손으로 잰 값: {hm.get('text', '')}"]
    inv = data["invariant_proposal"]
    lines.append("")
    lines.append("바뀌면 안 되는 부분 [제안]:")
    lines += [f"  · {PL.get(f['part'], f['part'])} {f['cells']}칸" for f in inv["fixed"]]
    lines.append("바뀌어도 되는 부분:")
    lines += [f"  · {PL.get(f['part'], f['part'])} {f['cells']}칸" for f in inv["free"]]
    for ln in lines:
        d.text((tx, ty), ln, font=font(17, ln.endswith(":")), fill=TXT if ln.endswith(":") else SUB)
        ty += 26
    py = max(y0 + 30 + max(a.shape[0] for a in arrays.values()) * Z, ty) + 40
    d.text((32, py), f"팔레트 ({len(data['palette'])}색) — 새 색을 만들지 않는다", font=font(21, True), fill=TXT)
    py += 40
    for i, p in enumerate(data["palette"]):
        cx, cy = 32 + (i % 6) * 300, py + (i // 6) * 66
        d.rectangle([cx, cy, cx + 44, cy + 44], fill=hexrgb(p["hex"]), outline=(90, 94, 110))
        d.text((cx + 54, cy - 2), f"{p['hex']}  {p['key']}".strip(), font=font(15, True), fill=TXT)
        d.text((cx + 54, cy + 18), p["name"], font=font(14), fill=SUB)
        d.text((cx + 54, cy + 36), " · ".join(f"{k} {v}" for k, v in p["cells"].items()), font=font(13), fill=(120, 126, 144))
    py += ((len(data["palette"]) + 5) // 6) * 66 + 20
    for k, v in (data.get("rules") or {}).items():
        d.text((32, py), f"· {k}: {v}", font=font(15), fill=SUB)
        py += 24
    return img.crop((0, 0, 1900, py + 20))


# ---------------------------------------------------------------- 애니메이션 (tools/pixel_anim.py)

def cmd_rig_init(a) -> None:
    x = ctx_of(a)
    A = x.cfg.get("anim") or {}
    d = x.dirs["anim"]
    if (d / "rig.json").exists():
        die(f"이미 있다: {rel(d / 'rig.json')}")
    for k in ("canvas", "anchor", "anchor_x_in_master"):
        if A.get(k) is None:
            die(f"anim.{k} 가 비어 있다")
    data, _ = spec_data(x)
    parts = x.cfg["spec"]["parts"]
    base = x.final("base")
    h = data["canvas"]["sole_row"]
    place = [A["anchor"][0] - A["anchor_x_in_master"], A["anchor"][1] - h]
    names = (x.cfg.get("spec") or {}).get("palette_names") or {}
    keys = {v[0]: k for k, v in names.items() if v and v[0]}
    rig = {
        "format": "salvage-pixel-rig/1", "id": x.cid,
        "_": "pixpipe rig-init 이 만든 틀. 다리 자세(leg_poses) · 앞쪽 팔 자세(arm_poses) · 층의 끝(tails)은 에이전트가 표로 찍는다. 글자 하나 = 칸 하나, '.' = 비움.",
        "master": rel(base), "canvas": A["canvas"], "place": place, "anchor": A["anchor"],
        "anchor_note": f"발 기준점 = 캔버스 {tuple(A['anchor'])}. 마스터를 {tuple(place)}에 놓는다 (마스터 x {A['anchor_x_in_master']} = 기준점).",
        "variants": {"body": "층 없음"}, "variant_short": {"body": "층 없음"},
        "keys": keys,
        "parts": {"head": {"rows": parts["head"]}, "upper": {"rows": parts["upper"], "minus": ["near_arm"]},
                  "legs": {"rows": parts["legs"]}},
        "shade_far": {}, "arm_poses": {"back": {"from_master": True, "label": "마스터 그대로"}}, "leg_poses": {},
        "preview": {"screen": (x.cfg.get("screen") or {}).get("size") or [320, 180], "press": [0.25, 0.70]},
    }
    if parts.get("near_arm"):
        rig["parts"]["near_arm"] = {"rect": parts["near_arm"]}
        if parts.get("near_arm_label"):
            rig["parts"]["near_arm"]["label"] = parts["near_arm_label"]
    if parts.get("free"):  # 바뀌면 안 되는 칸 = 머리 + 몸통 - 앞쪽 팔 - free. 검사가 프레임마다 마스터와 같은지 본다
        rig["fixed"] = {"_": "바뀌면 안 되는 칸 = 머리 + 몸통(앞쪽 팔 제외) 가운데 free 사각형 밖 (규격의 invariant_proposal). 검사(fixed_same_all)가 통과 조건에 들어간다",
                        "free": parts["free"]}
        rig["patches"] = {}
        rig["patches_note"] = ("덧칠: 머리카락 끝 · 옷자락 · 손처럼 몇 칸만 고쳐 찍는 표. {이름: {label, follow: upper | none, cells: 표}}. "
                               "프레임의 patch 목록에서 고른다. '_' = 그 칸을 지움. 마스터 칸은 free 안에서만 바꾼다 (검사가 본다)")
    for ln, L in (x.cfg.get("layers") or {}).items():
        ch = ((x.cfg.get("decisions") or {}).get("layers") or {}).get(ln, {}).get("option")
        o = L["options"][ch]
        rig["master_layer"] = rel(x.final(ln))
        rig["master_layer_pad_left"] = data["layers"][ln]["pad_left"]
        rig["layer_name"] = ln
        rig["variants"][ln] = L.get("label", ln)
        rig["variant_short"].update({"layer": f"{ln} 층", ln: L.get("label", ln)})
        tail_parts = [p for p in o["parts"] if p != L.get("fixed_part")]
        rig["layer"] = {"wrap": L["parts"][L["fixed_part"]] if L.get("fixed_part") else [],
                        "master_tail": "master", "tails": {"master": {"cells": [r for p in tail_parts for r in L["parts"][p]]}}}
        rig["keys"].update({k: v for k, v in L["colors"][o["color"]].items()})
        break  # 지금은 층 하나만 (NX-07 의 스카프). 둘 이상은 해 보지 않았다
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / "rig.json", rig, indent=2)
    idle = {"format": "salvage-pixel-anim/1", "name": "idle", "label": "대기", "loop": True,
            "method": "변형: 다리는 마스터 그대로, 머리 · 몸통이 함께 1칸 내려갔다 올라온다 (숨쉬기). 앞쪽 팔은 한 프레임 늦게 따라온다 (NX-07 9.11.6 과 같은 틀).",
            "frames": [
                {"ticks": 36, "upper": [0, 0], "arm": "back", "arm_off": [0, 0], "legs": "master", "tail": "master"},
                {"ticks": 8, "upper": [0, 1], "arm": "back", "arm_off": [0, 0], "legs": "master", "tail": "master"},
                {"ticks": 36, "upper": [0, 1], "arm": "back", "arm_off": [0, 1], "legs": "master", "tail": "master"},
                {"ticks": 8, "upper": [0, 0], "arm": "back", "arm_off": [0, 1], "legs": "master", "tail": "master"}]}
    write_json(d / "idle" / "timeline.json", idle, indent=2)
    print(f"[rig-init] {rel(d / 'rig.json')} · {rel(d / 'idle/timeline.json')} — 대기는 바로 돌릴 수 있다. 달리기는 다리 자세 표를 찍은 뒤")


def cmd_anim(a) -> None:
    import pixel_anim as pa
    x = ctx_of(a)
    state = require_approved(x, a.allow_unapproved)
    d = x.dirs["anim"] if not x.replay else ROOT / x.cfg["paths"]["anim"].format(id=x.cid)
    rig = pa.Rig(d) if not x.replay else pa.Rig(d, master=x.final("base"),
                                                 master_layer=x.final(x.variants()[1]) if len(x.variants()) > 1 else None)
    names = a.names or (x.cfg.get("anim") or {}).get("anims") or [p.parent.name for p in sorted(d.glob("*/timeline.json"))]
    out = x.dirs["anim"] if x.replay else None
    for n in names:
        res = pa.build_one(rig, n, out_dir=out)
        if state != "승인":
            ck = (out or d) / n / "check.json"
            r = read_json(ck)
            r["approval"] = state
            write_json(ck, r)
        tl = read_json(d / n / "timeline.json")
        for v, o in res["outputs"].items():
            if not isinstance(o, dict):
                continue
            register_output(x, f"anim_{n}_{v}", "pixel_anim", f"{tl.get('label', n)} · {rig.labels.get(v, v)}", ROOT / o["sheet"],
                            {"made_by": f"tools/pixpipe.py anim {x.cid} (tools/pixel_anim.py)", "rig": rel(d / "rig.json"),
                             "timeline": rel(d / n / "timeline.json"), "from": rel(x.final("base")), "doc": "docs/pipeline/CHARACTER_PIPELINE.md"},
                            status="기획자 평가 전", facing="right",
                            anim={"frames": res["summary"]["frames"], "cell": [rig.W, rig.H], "ticks": res["summary"]["ticks"],
                                  "loop": bool(tl.get("loop")), "anchor": list(rig.anchor)},
                            also={"gif": o["gif"], "meta": o["meta"], "check": rel(d / n / "check.json"), "frames": rel(d / n / "frames") + "/"})
    if not x.replay:
        pa.preview(rig, names)


def cmd_together(a) -> None:
    """승인된 다른 캐릭터와 같은 어두운 게임 화면 · 같은 발바닥 줄에 함께 세운 GIF (두 번째 캐릭터부터, 11장).
    --with nx07:scarf (다른 캐릭터:벌). 동작은 이름이 같은 것끼리 (idle_b 처럼 밑줄 뒤가 다르면 앞 이름의 동작과)."""
    import pixel_anim as pa
    x = ctx_of(a)
    me = pa.Rig(x.dirs["anim"])
    names = a.names or (x.cfg.get("anim") or {}).get("anims") or []
    made = []
    for w in a.with_ or []:
        oid, _, var = w.partition(":")
        other = pa.Rig(ROOT / Ctx(oid).cfg["paths"]["anim"].format(id=oid))
        var = var or "body"
        if var not in other.variants:
            die(f"{oid} 에 벌 {var} 가 없다: {other.variants}")
        oname = Ctx(oid).cfg["name"]
        for n in names:
            on = n if (other.folder / n / "timeline.json").exists() else n.split("_")[0]
            if not (other.folder / on / "timeline.json").exists():
                print(f"[together] {oid} 에 {on} 가 없어 건너뛴다")
                continue
            tl = read_json(me.folder / n / "timeline.json")
            sw, sh = (me.d.get("preview") or {}).get("screen", [320, 180])
            p = me.folder / "preview" / f"together_{oid}_{n}_{sw}x{sh}_x4.gif"
            made.append(pa.together([
                {"rig": other, "anim": on, "variant": var, "label": f"{oname} ({other.short.get(var, var)})"},
                {"rig": me, "anim": n, "variant": "body", "label": x.cfg["name"]}],
                p, f"{tl.get('label', n)} — {oname} 과 함께 (발바닥 줄 같음)"))
    if not made:
        die("만든 것이 없다 (--with 다른캐릭터[:벌])")


def cmd_review(a) -> None:
    import charpipe as cp
    x = ctx_of(a)
    anims = (x.cfg.get("anim") or {}).get("anims") or []
    keys = [k for k in cp.load_char(x.cid)["assets"] if k.startswith("anim_")]
    x.cfg.setdefault("decisions", {})["review"] = {"date": today(), "verdict": a.verdict, "quote": a.quote, "anims": anims}
    record(x.cid, "평가", f"애니메이션({', '.join(anims)})을 보고: {a.verdict}", a.quote, keys, a.saw, a.note or "")
    x.save()
    print(f"[review] {x.cid}: {a.verdict}")


def cmd_report(a) -> None:
    r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/charpipe.py"), "build"], cwd=ROOT)
    sys.exit(r.returncode)


# ---------------------------------------------------------------- 스튜디오가 쓰는 명령 (tools/pixstudio.py, CHARACTER_PIPELINE.md 12장)
# 명령줄에서도 같게 쓴다. 스튜디오는 이 명령들을 셸 없이 인자 목록으로 부른다.

STUDIO_DEFAULTS = COMMON / "studio_defaults.json"
PLAN_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
KIND_KO = {"side": "측면", "front": "정면", "back": "후면", "other": "그 밖"}


def note_text(s) -> str:
    """기획자의 메모를 프롬프트에 넣을 한 줄로. '{ }'는 틀의 칸으로 읽히므로 괄호로 바꾸고, 제어 문자는 지운다."""
    s = str(s or "").replace("{", "(").replace("}", ")").replace("«", "\"").replace("»", "\"")
    s = re.sub(r"[\x00-\x09\x0b-\x1f\x7f]", " ", s)
    s = re.sub(r"\s*\n\s*", "; ", s.strip())
    return s[:300]


def is_approved_char(x: Ctx) -> bool:
    return bool((x.cfg.get("decisions") or {}).get("approved")) or any(approvals(x.cid).values())


def suggest_cells(cm) -> tuple[int, str]:
    """목표 키(칸)의 제안: 기획자가 정한 NX-07 의 '칸 ÷ cm' (36칸 = 170cm, 9.11.5)."""
    n = Ctx("nx07").cfg
    r = n["size"]["height_cells"] / n["story_height_cm"]
    if not cm:
        return n["size"]["height_cells"], f"설정상 키가 없어 NX-07 과 같은 {n['size']['height_cells']}칸"
    return int(round(cm * r)), f"NX-07 {n['size']['height_cells']}칸 = {n['story_height_cm']}cm 의 비율로 {cm:g}cm ≈ {cm * r:.1f}칸"


def studio_refs(cid: str, D: dict) -> list[dict]:
    """1단계 참조: 측면 · 정면 · 그 밖 (없으면 후면). 설정화 묶음이 있으면 그것, 없으면 스튜디오로 올린 원화(up_<종류>_<n>)."""
    import charpipe as cp
    A = cp.load_char(cid)["assets"]

    def first(kind):
        if kind in A and A[kind]["group"] == "view":
            return kind
        ks = sorted(k for k in A if k.startswith(f"up_{kind}_"))
        return ks[0] if ks else None

    s, f = first("side"), first("front")
    order = [(k, v) for k, v in (("side", s), ("front", f), ("other", first("other"))) if v]
    if not s and not f and first("back"):
        order.append(("back", first("back")))
    if not order:
        die("원화가 없다: 설정화 묶음(측면 · 정면)도, 스튜디오로 올린 그림도 없다")
    refs = []
    for kind, k in order:
        file = A[k]["file"]
        if file.startswith("reference/"):
            die(f"reference/ 의 그림은 참조로 보내지 않는다: {file}")
        refs.append({"file": file, "role": D["references"][kind],
                     "note": f"{'스튜디오로 올린 원화' if k.startswith('up_') else '설정화'} · {KIND_KO[kind]} ({k})"})
    return refs


def style_ref(cid: str, cell: int) -> Path | None:
    """승인된 NX-07 마스터를 nearest 로 cell 배 키워 1024 마젠타 캔버스 가운데에 놓는다 — '그리는 방식의 기준' (미리네의 ×22 와 같은 방법)."""
    if not approvals("nx07").get("base"):
        return None
    m = Image.open(Ctx("nx07").final("base")).convert("RGBA")
    big = m.resize((m.width * cell, m.height * cell), Image.NEAREST)
    canvas = Image.new("RGB", (1024, 1024), MAGENTA)
    canvas.paste(big, ((1024 - big.width) // 2, (1024 - big.height) // 2), big)
    p = ROOT / "art/prompts/pipeline" / cid / f"style_nx07_px_base_x{cell}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(p)
    return p


def cmd_defaults(a) -> None:
    """캐릭터에 묶이지 않은 기본 문장(studio_defaults.json) + 기획자의 메모로 pipeline.json 을 채운다.
    --form = 만들 준비의 값 (JSON: height_cells · screen · plans · kinds · budget · heads_guide · notes{keep, drop, main}).
    --add = 다시 뽑기: 이미 있는 안은 그대로 두고 변형을 더한다."""
    import charpipe as cp
    D = read_json(STUDIO_DEFAULTS)
    F = read_json(Path(a.form)) if a.form else {}
    if not (ROOT / "art/characters" / a.id / "pixel" / "pipeline.json").exists():
        cmd_init(argparse.Namespace(id=a.id))
    x = Ctx(a.id)
    cfg = x.cfg
    if is_approved_char(x):
        die("승인된 캐릭터다. 기본 문장으로 다시 채우지 않는다")
    if not cfg.get("studio") and (cfg.get("plans") or (cfg.get("prompt") or {}).get("subject")):
        die("에이전트가 손으로 쓴 설정이 있다 (studio 표시가 없다). 기본 문장으로 덮지 않는다")
    have = [p for p in x.plans() if x.s1_raw(p).exists()]
    if have and not a.add:
        die(f"이미 뽑은 1단계 그림이 있다 ({', '.join(have)}). 바꾸려면 변형을 더한다 (--add, 다시 뽑기)")
    cm = (cp.load_char(a.id).get("story") or {}).get("height_cm")
    S = D["sizes"]
    sug, sug_note = suggest_cells(cm)
    T = int(F.get("height_cells") or (cfg.get("size") or {}).get("height_cells") or sug)
    if not 12 <= T <= 96:
        die(f"목표 키는 12 ~ 96칸: {T}")
    kinds_all = [k["kind"] for k in D["plans"]]
    n = int(F.get("plans") or 2)
    kinds = F.get("kinds") or (kinds_all[:n] if not a.add else None)
    if kinds is None:  # 다시 뽑기에서 고르지 않았으면 덜 쓴 계획부터
        used = [p.get("kind") for p in x.plans().values()]
        kinds = sorted(kinds_all, key=lambda k: (used.count(k), kinds_all.index(k)))[:n]
    if not 1 <= len(kinds) <= 3 or any(k not in kinds_all for k in kinds):
        die(f"밝기 계획은 1 ~ 3개, {kinds_all} 가운데서: {kinds}")
    screen = [int(v) for v in (F.get("screen") or (cfg.get("screen") or {}).get("size") or [320, 180])]
    heads = float(F.get("heads_guide") or (cfg.get("size") or {}).get("heads_guide")
                  or (S["heads_child"] if cm and cm < S["child_below_cm"] else S["heads_default"]))
    notes = {k: note_text((F.get("notes") or {}).get(k)) for k in ("keep", "drop", "main")}
    s1h = int(round(T * S["s1_height_ratio"]))
    s1c = max(14, min(24, S["s1_canvas"] // s1h))
    gcell = min(S["guide_cell_max"], S["guide_canvas"] // T)
    # 프롬프트의 캐릭터 문장 = 기본 문장 + 메모
    P = json.loads(json.dumps(D["prompt"]))
    P.update(s1_cell=s1c, s1_height=s1h)
    if notes["keep"]:
        P["accent_strokes"] += "; and what the game designer asks to keep readable (written in Korean): «" + notes["keep"] + "»"
    sim = D["simplify"]
    if notes["keep"]:
        sim += ". " + D["notes"]["keep"].replace("{text}", notes["keep"])
    if notes["drop"]:
        sim += (". " if not notes["keep"] else " ") + D["notes"]["drop"].replace("{text}", notes["drop"])
    main = D["notes"]["main"].replace("{text}", notes["main"]) if notes["main"] else D["notes"]["main_default"]
    cfg["prompt"] = P
    cfg["simplify"] = {"status": "[제안]", "by": "스튜디오의 기본 문장 (캐릭터에 묶이지 않음, art/characters/_pipeline/studio_defaults.json)"
                       + (" + 기획자의 메모" if any(notes.values()) else ""),
                       "note": "[제안] 기본 문장으로 진행한다. 기획자의 메모는 프롬프트에 원문(한국어)으로 들어간다",
                       "keep": [notes["keep"]] if notes["keep"] else [], "merge": [], "drop": [notes["drop"]] if notes["drop"] else [],
                       "main": notes["main"], "prompt": sim}
    refs = studio_refs(a.id, D)
    sp = style_ref(a.id, s1c)
    if sp:
        refs.append({"file": rel(sp), "role": D["references"]["style"],
                     "note": f"승인된 NX-07 픽셀 마스터를 nearest ×{s1c} 로 키운 것 — 그리는 방식의 기준 (디자인 · 색은 따르지 않게) [제안]"})
    cfg["references"] = refs
    cfg["size"] = {"height_cells": T, "height_mark": f"스튜디오의 만들 준비에서 정함 (제안: {sug_note})", "heads_guide": heads,
                   "heads_note": "[제안] 스튜디오의 기본값 (설정상 키가 150cm 아래면 3.0, 아니면 3.2)" if not F.get("heads_guide") else "스튜디오의 만들 준비에서 정함"}
    cfg["screen"] = {"size": screen, "mark": "스튜디오의 만들 준비에서 정함"}
    G = cfg.setdefault("generate", {})
    if F.get("budget") is not None:
        G["budget"] = int(F["budget"])
        G["budget_note"] = "스튜디오의 만들 준비에서 기획자가 정한 상한"
    elif G.get("budget") is None:
        G["budget"] = len(kinds) * 2 + 2
        G["budget_note"] = "[제안] 스튜디오의 기본값 (변형 수 × 2 + 2)"
    # 밝기 계획 · 후보
    plans = cfg.get("plans") or {}
    jobs = cfg.get("jobs") or {}
    if not a.add:
        plans, jobs = {}, {}
    free = [L for L in PLAN_LETTERS if L not in plans]
    added = []
    for k, L in zip(kinds, free):
        K = next(p for p in D["plans"] if p["kind"] == k)
        plans[L] = {"label": K["label"], "title": K["title"], "kind": k, "why": K["why"],
                    "s1": [s.replace("{main}", main) for s in K["s1"]], "s2": K["s2"].replace("{main}", main),
                    "notes_at": notes, "made_by": f"pixpipe defaults ({today()})"}
        jobs[f"{L}{T}"] = {"plan": L, "height": T, "cell": gcell, "fixes": []}
        added.append(L)
    cfg["plans"], cfg["jobs"] = plans, jobs
    st = cfg.setdefault("studio", {"generic": True, "defaults": rel(STUDIO_DEFAULTS), "history": []})
    st["last_form"] = {"height_cells": T, "screen": screen, "plans": len(kinds), "kinds": kinds, "budget": G["budget"],
                       "heads_guide": heads, "notes": notes}
    st["history"].append({"date": today(), "add": bool(a.add), "plans": added, "form": st["last_form"]})
    x.save()
    x = Ctx(a.id)
    for L in added:  # 새 안의 프롬프트만 쓴다 (이미 보낸 안의 파일은 그대로)
        write_prompt(x, f"s1_{L}", s1_prompt(x, L))
    print(f"[defaults] {a.id}: 키 {T}칸 · 밝기 계획 {', '.join(f'{L}={plans[L]['label']}' for L in added)} · 한도 {G['budget']}회 · "
          f"참조 {len(refs)}장 · 메모 {'있음' if any(notes.values()) else '없음'}")


def editable_job(x: Ctx, job: str) -> None:
    if job not in x.jobs():
        die(f"후보가 없다: {job}")
    if is_approved_char(x):
        die("승인된 캐릭터의 후보는 손보지 않는다 (승인된 마스터를 지킨다)")
    if x.pinned("job", job, "master"):
        die("파이프라인 전에 만든 후보는 손보지 않는다")
    if not x.master(job).exists():
        die(f"{job} 의 마스터가 아직 없다")


def cell_arg(s: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*", s or "")
    if not m:
        die(f"칸은 x,y 로: {s}")
    return int(m.group(1)), int(m.group(2))


def cmd_fix(a) -> None:
    """칸 손보기: 후보 마스터의 칸 하나를 그 그림의 팔레트 색(또는 투명)으로. 기록은 jobs.<후보>.fixes (cell · from · why)
    그대로다 — 색은 '같은 색을 가진 다른 칸(from)'으로 적는다 (새 색을 만들지 않는다). 그 뒤 master 를 다시 돈다."""
    x = ctx_of(a)
    editable_job(x, a.job)
    if not (a.why or "").strip():
        die("고치는 이유(--why)를 적는다")
    cx, cy = cell_arg(a.cell)
    m = np.array(Image.open(x.master(a.job)).convert("RGBA"))
    h, w = m.shape[:2]
    if not (0 <= cx < w and 0 <= cy < h):
        die(f"칸이 마스터 밖이다: ({cx}, {cy}), 마스터 {w}×{h}")
    want = None if a.transparent else hexrgb(a.color or "")
    if want is None and not a.transparent:
        die("--color #rrggbb 또는 --transparent")
    fx = [f for f in (x.jobs()[a.job].get("fixes") or []) if tuple(f["cell"]) != (cx, cy)]
    targets = {tuple(f["cell"]) for f in fx} | {(cx, cy)}
    cur = None if m[cy, cx, 3] == 0 else tuple(int(v) for v in m[cy, cx, :3])
    if cur == want and not any(tuple(f["cell"]) == (cx, cy) for f in x.jobs()[a.job].get("fixes") or []):
        die("이미 그 색이다")
    src = None
    for yy in range(h):
        for xx in range(w):
            if (xx, yy) in targets:
                continue
            p = m[yy, xx]
            if (want is None and p[3] == 0) or (want is not None and p[3] > 0 and tuple(int(v) for v in p[:3]) == want):
                src = (xx, yy)
                break
        if src:
            break
    if src is None:
        die("그 색(또는 투명)인 칸이 이 마스터의 다른 곳에 없다 — 새 색은 만들지 않는다")
    fx.append({"cell": [cx, cy], "from": [src[0], src[1]], "why": a.why.strip()[:500], "by": a.by, "date": today()})
    x.jobs()[a.job]["fixes"] = fx
    x.save()
    print(f"[fix] {a.job} ({cx}, {cy}) → {'투명' if want is None else '#' + hx(want)} (색은 ({src[0]}, {src[1]}) 칸에서) · 손본 칸 {len(fx)}")
    cmd_master(argparse.Namespace(id=x.cid, job=[a.job]))


def cmd_unfix(a) -> None:
    """칸 손보기를 되돌린다 (기록에서 그 칸을 빼고 master 를 다시 돈다)."""
    x = ctx_of(a)
    editable_job(x, a.job)
    cx, cy = cell_arg(a.cell)
    fx = x.jobs()[a.job].get("fixes") or []
    left = [f for f in fx if tuple(f["cell"]) != (cx, cy)]
    if len(left) == len(fx):
        die(f"({cx}, {cy}) 는 손본 칸이 아니다")
    x.jobs()[a.job]["fixes"] = left
    x.save()
    if not left:  # 손본 칸이 없으면 손보기 전 그림 · 기록 파일은 쓰지 않는다
        d = x.master_out(a.job).parent
        for f in (d / f"{x.cid}_{a.job}_unfixed.png", d / f"{x.cid}_{a.job}_unfixed_x8.png", d / f"{x.cid}_{a.job}_fixes.json"):
            f.unlink(missing_ok=True)
        for f in d.glob(f"{x.cid}_{a.job}_unfixed_*"):
            f.unlink()
    print(f"[unfix] {a.job} ({cx}, {cy}) 되돌림 · 남은 손본 칸 {len(left)}")
    cmd_master(argparse.Namespace(id=x.cid, job=[a.job]))


def cmd_reject(a) -> None:
    """기획자가 후보를 채택하지 않았다고 적는다 (pick 과 같은 모양의 기록)."""
    import charpipe as cp
    x = ctx_of(a)
    if a.job not in x.jobs():
        die(f"후보가 없다: {a.job}")
    dec = x.cfg.setdefault("decisions", {})
    if (dec.get("pick") or {}).get("job") == a.job:
        die(f"{a.job} 는 고른 후보다. 다른 후보를 고른 뒤에 채택하지 않음으로 적는다")
    dec.setdefault("rejected", {})[a.job] = {"date": today(), "quote": a.quote, "saw": a.saw or [rel(x.work / "compare.png")]}
    record(x.cid, "결정", f"픽셀 마스터 후보 {a.job} 를 채택하지 않았다", a.quote, [a.job], a.saw)
    c = cp.load_char(x.cid)
    if f"pm_{a.job}" in c["assets"]:
        c["assets"][f"pm_{a.job}"]["status"] = f"실험 · 채택하지 않음 — 기획자 ({today()})"
        cp.save_char(c)
    x.save()
    print(f"[reject] {a.job}")


def cmd_candidates(a) -> None:
    """후보 마스터를 등록부에 올린다 (pm_<후보>). 처음 올릴 때 '실험 · 승인 기록 없음'. 손본 뒤에는 새 판으로. (미리네는 charpipe add 로 손으로 했다, 11장)"""
    import charpipe as cp
    x = ctx_of(a)
    have = cp.load_char(x.cid)["assets"]
    n = 0
    for job, J in x.jobs().items():
        p = x.master(job)
        if not p.exists() or x.pinned("job", job, "master"):
            continue
        d, stem = p.parent, f"{x.cid}_{job}"
        also = {k: rel(d / f) for k, f in (("x8", f"{stem}_master_x8.png"), ("unfixed", f"{stem}_unfixed.png"),
                                             ("fixes", f"{stem}_fixes.json")) if (d / f).exists()}
        if (x.work / "compare.png").exists():
            also["compare"] = rel(x.work / "compare.png")
        pl = x.plans().get(J["plan"], {})
        key = f"pm_{job}"
        register_output(x, key, "pixel_master", f"{job} · {pl.get('label', J['plan'])} · 키 {J['height']}칸", p,
                        {"made_by": "tools/pixpipe.py master (pixpipe candidates 가 등록)", "from": rel(x.s2_raw(job)),
                         "prompts": [rel(x.dirs["prompts"] / f"s1_{J['plan']}.txt"), rel(x.dirs["prompts"] / f"s2_{job}.txt")],
                         "doc": "docs/pipeline/CHARACTER_PIPELINE.md"},
                        status=None if key in have else "실험 · 승인 기록 없음", facing="right",
                        info=rel(d / f"{stem}_master_info.json"), also=also)
        n += 1
    print(f"[candidates] {x.cid}: 후보 {n}개를 등록부에 올림")


def cmd_lineup(a) -> None:
    """승인된 다른 캐릭터와 후보 마스터를 어두운 게임 화면(1배)에 같은 발바닥 줄로 세운다 → work/lineup_screen.png · lineup.json."""
    import charpipe as cp
    import pixel_anim as pa
    x = ctx_of(a)
    w, h = (x.cfg.get("screen") or {}).get("size") or [320, 180]
    withs = a.with_
    if not withs:
        withs = []
        for oid in cp.ids_all():
            ok = [v for v, good in approvals(oid).items() if good] if oid != x.cid else []
            if ok:
                withs.append(f"{oid}:{ok[-1]}")
    items = []
    for wv in withs:
        oid, _, var = wv.partition(":")
        var = var or "base"
        o = Ctx(oid)
        p = o.final(var)
        if not approvals(oid).get(var) or not p.exists():
            print(f"[lineup] {wv}: 승인된 마스터가 없어 건너뛴다")
            continue
        lab = o.cfg["name"] + ("" if var == "base" else f" ({(o.cfg.get('layers') or {}).get(var, {}).get('label', var)})")
        items.append({"label": lab, "kind": "approved", "id": oid, "variant": var, "file": rel(p)})
    dec = x.cfg.get("decisions") or {}
    for job in x.jobs():
        p = x.master(job)
        if p.exists():
            st = "고름" if (dec.get("pick") or {}).get("job") == job else ("채택하지 않음" if job in (dec.get("rejected") or {}) else "")
            items.append({"label": job, "kind": "candidate", "job": job, "file": rel(p), "state": st})
    bg, floor = pa.screen_bg({"screen": [w, h], "press": [0.25, 0.70]})
    ImageDraw.Draw(bg).line([(0, floor), (w, floor)], fill=(58, 64, 88, 255))
    arrs = [pm.crop(pm.load_rgba(ROOT / it["file"])) for it in items]
    gap = 6
    total = lambda g: sum(q.shape[1] for q in arrs) + g * max(0, len(arrs) - 1)  # noqa: E731
    while total(gap) > w - 8 and gap > 1:
        gap -= 1
    x0 = max(0, (w - total(gap)) // 2)
    for it, q in zip(items, arrs):
        it.update(x=int(x0), y=int(floor - q.shape[0]), w=int(q.shape[1]), h=int(q.shape[0]))
        bg.alpha_composite(Image.fromarray(q, "RGBA"), (x0, floor - q.shape[0]))
        x0 += q.shape[1] + gap
    out = x.work / "lineup_screen.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    bg.convert("RGB").save(out)
    write_json(x.work / "lineup.json", {"screen": [w, h], "floor": floor, "gap": gap, "items": items, "file": rel(out),
                                        "fits": total(gap) <= w, "made_by": "tools/pixpipe.py lineup",
                                        "note": "1배 그림. 지금 게임의 배경을 화면 높이로 줄이고 누른 것 (pixel_anim.screen_bg) 위에 같은 발바닥 줄로 세웠다"})
    print(f"[lineup] {rel(out)} · {len(items)}명 · 사이 {gap}칸" + ("" if total(gap) <= w else " · 화면에 다 들어가지 않는다"))


# ---------------------------------------------------------------- 참고 숫자

def ref_numbers(figs: dict) -> dict:
    hidden = read_json(TARGETS)["source"].get("face_hidden", [])
    out = {}
    for nm, a in figs.items():
        out[nm] = {"picture": pm.picture(a)}
        out[nm]["picture"].pop("face_skin_cells", None)
        if nm in hidden:  # 얼굴을 가린 인물: 살색처럼 잡히는 칸이 있어도 얼굴이 아니다 (9.11.3)
            out[nm]["picture"]["face_contrast"] = None
    return out


def cmd_ref_targets(a) -> None:
    figs = ref_figures()
    if figs is None:
        die("참고 그림이 PC 에 없다. 숫자는 그대로 둔다 (" + rel(TARGETS) + ")")
    new = ref_numbers(figs)
    T = read_json(TARGETS)
    if a.check:
        same = all(T["figures"][k]["picture"] == v["picture"] for k, v in new.items())
        print("[ref-targets]", "같다" if same else "다르다", json.dumps(new, ensure_ascii=False))
        return
    for k, v in new.items():
        T["figures"].setdefault(k, {})["picture"] = v["picture"]
    T["measured"] = today()
    write_json(TARGETS, T)
    print("[ref-targets]", rel(TARGETS))


# ---------------------------------------------------------------- NX-07 재현 검증

def cmd_verify(a) -> None:
    """이미 뽑아 둔 그림(고정된 원본)만으로 밑그림 → 마스터 → 층 → 규격 → 애니메이션을 다시 만들고 승인된 파일과 견준다. 이미지 생성 0회."""
    cid = a.id
    out = Path(a.out) if a.out else ROOT / "art/characters" / cid / "pixel/work/verify"
    if out.exists():
        shutil.rmtree(out)
    x = Ctx(cid, replay=out)
    V = x.cfg.get("verify") or {}
    rep = {"date": today(), "character": cid, "out": rel(out), "image_generation_calls": 0, "checks": []}

    def same(label: str, mine: Path, theirs: Path) -> bool:
        ok = mine.exists() and theirs.exists() and sha(mine) == sha(theirs)
        rep["checks"].append({"what": label, "made": rel(mine), "expected": rel(theirs), "same_sha256": ok,
                              "sha256": sha(mine)[:16] if mine.exists() else None})
        print(f"[verify] {'같음' if ok else '다름'} — {label}: {rel(mine)} vs {rel(theirs)}")
        return ok

    def same_value(label: str, mine, theirs) -> bool:
        ok = mine == theirs
        rep["checks"].append({"what": label, "same_value": ok, **({} if ok else {"made": mine, "expected": theirs})})
        print(f"[verify] {'같음' if ok else '다름'} — {label}")
        return ok

    ns = argparse.Namespace(id=cid, job=None, plan=None, dry_run=True, over_budget=False, allow_unapproved=False, names=None, ctx=x)
    # 1 프롬프트: 공통 틀 + 캐릭터 문장 = 그때 보낸 프롬프트
    for plan in x.plans():
        olds = [ROOT / p for p in (x.plans()[plan].get("pinned") or {}).get("prompt_files", [])]
        if olds:
            sent = "\n\n".join(p.read_text(encoding="utf-8").strip() for p in olds)
            same_value(f"1단계 프롬프트 {plan} (fal_image 가 보내는 글)", s1_prompt(x, plan), sent)
            write_prompt(x, f"s1_{plan}", s1_prompt(x, plan))
    # 2 밑그림
    cmd_guide(ns)
    for job in x.jobs():
        pg = x.pinned("job", job, "guide")
        if pg:
            same(f"밑그림 {job}", x.guide_out(job), pg)
        pc = x.pinned("job", job, "guide_cells")
        if pc:
            same(f"밑그림의 1배 칸 그림 {job}", x.work / "guides" / f"{job}_cells.png", pc)
    g = read_json(x.guides_json())
    for job in x.jobs():
        ps = x.pinned("job", job, "s2_prompt")
        if ps:
            same_value(f"2단계 프롬프트 {job}", s2_prompt(x, job, g[job]), ps.read_text(encoding="utf-8").strip())
            write_prompt(x, f"s2_{job}", s2_prompt(x, job, g[job]))
    # 3 뽑기는 dry-run 만 (보낼 참조가 그때와 같은지)
    for plan in x.plans():
        pf = x.dirs["prompts"] / f"s1_{plan}.txt"
        if pf.exists():
            gen(x, "s1", plan, pf, [ROOT / r["file"] for r in x.cfg["references"]], x.s1_out(plan), True, False)
    for job, J in x.jobs().items():
        pf = x.dirs["prompts"] / f"s2_{job}.txt"
        if pf.exists():
            gen(x, "s2", job, pf, [x.s1_raw(J["plan"]), x.guide_used(job)], x.s2_out(job), True, False)
    # 4 마스터
    cmd_master(ns)
    for job in x.jobs():
        pmst = x.pinned("job", job, "master")
        if pmst:
            same(f"마스터 {job}", x.master_out(job), pmst)
        pu = x.pinned("job", job, "unfixed")
        if pu:
            same(f"손보기 전 {job}", x.master_out(job).with_name(f"{cid}_{job}_unfixed.png"), pu)
    # 5 층 (고른 후보 위에)
    cmd_layer(ns)
    for ln, L in (x.cfg.get("layers") or {}).items():
        for opt, o in L["options"].items():
            if o.get("pinned"):
                same(f"층 {ln} {opt}", x.layer_out(ln, opt), ROOT / o["pinned"])
    # 6 승인된 마스터 두 벌과 해시가 같은가 (승인을 적지 않고 복사만)
    dec = x.cfg["decisions"]
    x.final("base").parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(x.master_out(dec["pick"]["job"]), x.final("base"))
    for ln in (x.cfg.get("layers") or {}):
        shutil.copyfile(x.layer_out(ln, dec["layers"][ln]["option"]), x.final(ln))
    real = Ctx(cid)
    for v in x.variants():
        same(f"승인된 마스터 px_{v}", x.final(v), real.final(v))
    # 7 재기 (옮긴 측정 코드가 그때와 같은 숫자를 내는가)
    res = measure_all(x)
    write_json(x.work / "measure.json", res)
    for name, src in (V.get("measure") or {}).items():
        if not (ROOT / src["file"]).exists():
            rep["checks"].append({"what": f"그림 숫자 {name}", "skipped": f"옛 측정 파일이 PC 에 없다: {src['file']}"})
            continue
        old = read_json(ROOT / src["file"])[src["key"]]
        mine = res["items"][name]["picture"]
        oldv = {"largest_value_mass_pct": old.get("largest_value_mass_pct") or max(v["largest_pct"] for v in old["value_bands"].values()),
                "value_top3_pct": old["value_top3_pct"],
                "region_big_pct": old["region_big_mid_small_pct"][0], "region_mid_pct": old["region_big_mid_small_pct"][1],
                "region_small_pct": old["region_big_mid_small_pct"][2], "accent_pct": old["accent_pct"], "L_mean": old["L_mean"],
                "face_contrast": old["face"].get("contrast")}
        same_value(f"그림 숫자 {name} = {src['file']}#{src['key']}", {k: mine[k] for k in oldv}, oldv)
    T = read_json(TARGETS)
    for nm, src in (T.get("from_old_measure") or {}).items():
        p = ROOT / src["file"]
        if p.exists():
            old = read_json(p)[src["key"]]
            oldv = {"largest_value_mass_pct": max(v["largest_pct"] for v in old["value_bands"].values()),
                    "value_top3_pct": old["value_top3_pct"], "region_big_pct": old["region_big_mid_small_pct"][0],
                    "region_mid_pct": old["region_big_mid_small_pct"][1], "region_small_pct": old["region_big_mid_small_pct"][2],
                    "accent_pct": old["accent_pct"], "L_mean": old["L_mean"], "face_contrast": old["face"].get("contrast")}
            same_value(f"참고 숫자 {nm} (reference_targets.json = 옛 측정)", {k: T["figures"][nm]["picture"][k] for k in oldv}, oldv)
    figs = ref_figures()
    if figs is not None:
        new = ref_numbers(figs)
        same_value("참고 그림을 다시 재면 reference_targets.json 과 같은가", {k: v["picture"] for k, v in new.items()},
                   {k: T["figures"][k]["picture"] for k in new})
    else:
        rep["checks"].append({"what": "참고 그림 다시 재기", "skipped": "참고 그림이 PC 에 없다"})
    compare_image(x, res).save(x.work / "compare.png")
    # 8 규격 (숫자가 옛 규격과 같은가)
    sd, _ = spec_data(x)
    old = read_json(ROOT / V["spec"])
    same_value("규격: 캔버스 · 키 · 발바닥 줄", [sd["canvas"]["master_base"], sd["height"]["cells"], sd["canvas"]["sole_row"]],
               [old["canvas"]["master_base"], old["height"]["cells"], old["height"]["sole_row"]])
    same_value("규격: 부위마다의 칸 수", sd["parts_cells"], old["parts_cells"])
    same_value("규격: 팔레트 (색 · 칸 수 · 놓인 줄)",
               [(p["hex"], p["cells"]["base"], p["cells"].get("scarf"), p["in_base"], p["rows"] if p["in_base"] else ["층"]) for p in sd["palette"]],
               [(p["hex"], p["cells_base"], p["cells_scarf"], p["in_base"], p["rows"] if p["in_base"] else ["층"]) for p in old["palette"]])
    for ln, lay in sd["layers"].items():
        o = old.get(f"{ln}_layer") or {}
        same_value(f"규격: 층 {ln} (덮는 칸 · 더하는 칸 · 고정 부분)",
                   [sorted(lay["covers_base_cells"]), sorted(lay["adds_cells"]), lay["fixed_cells"]],
                   [sorted(o.get("covers_base_cells", [])), sorted(o.get("adds_cells", [])), o.get("wrap_cells")])
    same_value("규격: 측정한 머리", sd["height"]["measured_head"], old["height"]["measured_head"])
    write_json(x.dirs["final"] / f"{cid}_px_spec.json", sd)
    # 9 애니메이션 (프레임 · 시트 · 메타 · GIF)
    ns.names = None
    cmd_anim(ns)
    real_anim = ROOT / x.cfg["paths"]["anim"].format(id=cid)
    for n in (x.cfg.get("anim") or {}).get("anims") or []:
        for f in sorted((real_anim / n / "frames").glob("*.png")):
            same(f"프레임 {n}/{f.name}", x.dirs["anim"] / n / "frames" / f.name, f)
        for f in sorted((real_anim / n / "out").glob("*")):
            same(f"내보낸 것 {n}/{f.name}", x.dirs["anim"] / n / "out" / f.name, f)
        mine, theirs = read_json(x.dirs["anim"] / n / "check.json"), read_json(real_anim / n / "check.json")
        same_value(f"검사 요약 {n}", mine["summary"], theirs["summary"])
        same_value(f"검사 프레임별 {n}", mine["frames"], theirs["frames"])
    n_ok = sum(1 for c in rep["checks"] if c.get("same_sha256") or c.get("same_value"))
    n_all = sum(1 for c in rep["checks"] if "skipped" not in c)
    rep["summary"] = {"same": n_ok, "total": n_all, "all_same": n_ok == n_all}
    write_json(out / "verify.json", rep)
    print(f"[verify] {n_ok}/{n_all} 같음 — {rel(out / 'verify.json')}")


# ---------------------------------------------------------------- main

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="캐릭터 픽셀 파이프라인 (docs/pipeline/CHARACTER_PIPELINE.md)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status"); p.add_argument("ids", nargs="*")
    p = sub.add_parser("init"); p.add_argument("id")
    p = sub.add_parser("prompts"); p.add_argument("id")
    for name in ("s1", "s2"):
        p = sub.add_parser(name); p.add_argument("id")
        p.add_argument("--plan" if name == "s1" else "--job", action="append")
        p.add_argument("--dry-run", action="store_true"); p.add_argument("--over-budget", action="store_true")
    for name in ("guide", "master"):
        p = sub.add_parser(name); p.add_argument("id"); p.add_argument("--job", action="append")
    for name in ("measure", "compare", "layer", "rig-init"):
        p = sub.add_parser(name); p.add_argument("id")
    p = sub.add_parser("pick"); p.add_argument("id"); p.add_argument("--job"); p.add_argument("--layer", action="append")
    p.add_argument("--quote", required=True); p.add_argument("--saw", action="append")
    p = sub.add_parser("approve"); p.add_argument("id"); p.add_argument("--quote", required=True)
    p.add_argument("--saw", action="append"); p.add_argument("--note")
    p = sub.add_parser("spec"); p.add_argument("id"); p.add_argument("--allow-unapproved", action="store_true")
    p = sub.add_parser("anim"); p.add_argument("id"); p.add_argument("names", nargs="*")
    p.add_argument("--allow-unapproved", action="store_true")
    p = sub.add_parser("together"); p.add_argument("id"); p.add_argument("names", nargs="*")
    p.add_argument("--with", dest="with_", action="append", required=True)
    p = sub.add_parser("review"); p.add_argument("id"); p.add_argument("--quote", required=True)
    p.add_argument("--verdict", default="받아들임"); p.add_argument("--saw", action="append"); p.add_argument("--note")
    sub.add_parser("report")
    p = sub.add_parser("defaults"); p.add_argument("id"); p.add_argument("--form"); p.add_argument("--add", action="store_true")
    p = sub.add_parser("fix"); p.add_argument("id"); p.add_argument("--job", required=True); p.add_argument("--cell", required=True)
    p.add_argument("--color"); p.add_argument("--transparent", action="store_true"); p.add_argument("--why", required=True)
    p.add_argument("--by", default="에이전트")
    p = sub.add_parser("unfix"); p.add_argument("id"); p.add_argument("--job", required=True); p.add_argument("--cell", required=True)
    p = sub.add_parser("reject"); p.add_argument("id"); p.add_argument("--job", required=True); p.add_argument("--quote", required=True)
    p.add_argument("--saw", action="append")
    p = sub.add_parser("candidates"); p.add_argument("id")
    p = sub.add_parser("lineup"); p.add_argument("id"); p.add_argument("--with", dest="with_", action="append")
    p = sub.add_parser("verify"); p.add_argument("id"); p.add_argument("--out")
    p = sub.add_parser("ref-targets"); p.add_argument("--check", action="store_true")
    a = ap.parse_args()
    {"status": cmd_status, "init": cmd_init, "prompts": cmd_prompts, "s1": cmd_s1, "s2": cmd_s2, "guide": cmd_guide,
     "master": cmd_master, "measure": cmd_measure, "compare": cmd_compare, "pick": cmd_pick, "layer": cmd_layer,
     "approve": cmd_approve, "spec": cmd_spec, "rig-init": cmd_rig_init, "anim": cmd_anim, "together": cmd_together,
     "review": cmd_review, "defaults": cmd_defaults, "fix": cmd_fix, "unfix": cmd_unfix, "reject": cmd_reject,
     "candidates": cmd_candidates, "lineup": cmd_lineup,
     "report": cmd_report, "verify": cmd_verify, "ref-targets": cmd_ref_targets}[a.cmd](a)


if __name__ == "__main__":
    main()
