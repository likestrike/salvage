"""캐릭터 픽셀 스튜디오 — 기획자가 직접 쓰는 화면 (docs/pipeline/CHARACTER_PIPELINE.md 12장, 기획서 9.11.10).

    python -X utf8 tools/pixstudio.py [--port 8790] [--no-browser] [--practice]

프로젝트 폴더의 '픽셀스튜디오.bat' 을 더블클릭하면 이것이 뜨고 브라우저가 열린다. 그 창을 닫으면 꺼진다.
- PC 안(127.0.0.1)에서만 돈다. 켤 때 만든 무작위 토큰과 Host · Origin 을 요청마다 본다.
- 파이프라인의 일은 모두 tools/pixpipe.py 의 명령을 셸 없이 인자 목록으로 부른다 (스튜디오로 한 일 = 명령줄로 한 일).
- 한 번에 한 작업만 돈다. 작업의 상태는 art/characters/<id>/pixel/work/studio_job.json 에 남는다 (창을 닫았다 열어도 보인다).
- .env.local 은 읽지 않는다 (fal.ai 키는 tools/fal_image.py 가 직접 읽는다).
--practice: 연습 모드. 이미지 생성 없이 미리네의 그림을 복사한다 (PIXPIPE_MOCK_FROM=mirine). 화면에 '연습'이 크게 보인다.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hmac
import io
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
STATIC = TOOLS / "pixstudio"
sys.path.insert(0, str(TOOLS))
import charpipe as cp  # noqa: E402
import pixpipe as pp  # noqa: E402
from PIL import Image  # noqa: E402

PY = [sys.executable, "-X", "utf8"]
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
# 내주는 파일: 이 폴더들 안의 그림 · 표 · 글뿐. reference/ · .env.local · 코드는 내주지 않는다.
FILE_ROOTS = ("art/characters/", "art/concept/setting/", "art/prompts/pipeline/",
              "art/pipeline_lab/pixel_style/v2/", "art/pipeline_lab/pixel_style/v3_scarf/")
FILE_ONE = {"game/assets/style_c/bg.png"}
FILE_EXT = {".png": "image/png", ".gif": "image/gif", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
            ".json": "application/json; charset=utf-8", ".txt": "text/plain; charset=utf-8"}
STATIC_FILES = {"app.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8"}
MAX_BODY = 64 << 20
MAX_IMAGE = 20 << 20
MAX_IMAGES = 8
MAX_PIXELS = 40_000_000
UP_KINDS = {"side": "측면", "front": "정면", "back": "후면", "other": "그 밖"}
KINDS = {"player": "플레이어", "companion": "동행", "npc": "등장인물", "enemy": "적"}
SCREENS = [[320, 180], [384, 216], [480, 270]]
VERDICTS = ["받아들임", "고칠 것", "보류"]
SECRET_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}:[0-9a-fA-F]{16,}"
                       r"|FAL_KEY\s*[=:]\s*\S+|Key\s+[0-9a-fA-F-]{20,}\S*")
RUNNING = STATIC / "running.json"


class Conf:
    token = ""
    port = 0
    practice = False
    hosts: set[str] = set()
    origins: set[str] = set()


# ---------------------------------------------------------------- 한 번에 한 작업

class Busy:
    lock = threading.Lock()
    what: dict | None = None

    @classmethod
    def take(cls, what: str, cid: str | None) -> bool:
        with cls.lock:
            if cls.what:
                return False
            cls.what = {"what": what, "cid": cid, "since": now()}
            return True

    @classmethod
    def give(cls) -> None:
        with cls.lock:
            cls.what = None


class Refused(Exception):
    """기획자에게 보일 거절 (HTTP 4xx)."""

    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def redact(s: str) -> str:
    return SECRET_RE.sub("[가림]", s)


def env() -> dict:
    e = {k: v for k, v in os.environ.items() if k != "PIXPIPE_MOCK_FROM"}
    e["PYTHONIOENCODING"] = "utf-8"
    if Conf.practice:
        e["PIXPIPE_MOCK_FROM"] = "mirine"
    return e


def run_tool(tool: str, args: list[str]) -> tuple[int, str]:
    """도구를 셸 없이 부른다. 기획자가 적은 글은 인자 하나로만 들어간다."""
    r = subprocess.run(PY + [str(TOOLS / tool)] + [str(a) for a in args], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env())
    return r.returncode, redact((r.stdout or "") + (r.stderr or ""))


def pixpipe(*args) -> str:
    code, out = run_tool("pixpipe.py", list(args))
    if code:
        raise Refused(last_reason(out) or f"pixpipe {args[0]} 실패", 409)
    return out


def last_reason(out: str) -> str:
    lines = [l for l in out.strip().splitlines() if l.strip()]
    pick = [l for l in lines if l.startswith("[pixpipe]") or l.startswith("[charpipe]") or "Error" in l or "실패" in l]
    return (pick[-1] if pick else (lines[-1] if lines else "")).replace("[pixpipe] ", "")[:600]


def clean_text(s, n: int) -> str:
    s = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", str(s or "")).strip()
    return s[:n]


def rel(p: Path) -> str:
    return pp.rel(p)


def char_dir(cid: str) -> Path:
    return ROOT / "art/characters" / cid


def need_id(cid: str) -> str:
    if not ID_RE.fullmatch(cid or "") or cid not in cp.ids_all():
        raise Refused(f"등록된 캐릭터가 아니다: {cid}", 404)
    return cid


# ---------------------------------------------------------------- 캐릭터 읽기

def cfg_path(cid: str) -> Path:
    return char_dir(cid) / "pixel" / "pipeline.json"


def flags(cid: str) -> dict:
    has = cfg_path(cid).exists()
    cfg = pp.read_json(cfg_path(cid)) if has else {}
    approved = any(pp.approvals(cid).values()) or bool((cfg.get("decisions") or {}).get("approved"))
    studio = bool(cfg.get("studio"))
    hand = has and not studio and bool(cfg.get("plans") or (cfg.get("prompt") or {}).get("subject"))
    return {"pipeline": has, "studio": studio, "handwritten": hand, "approved": approved,
            "editable": not approved and not hand}


def suggest_form(cid: str) -> dict:
    c = cp.load_char(cid)
    cm = (c.get("story") or {}).get("height_cm")
    D = pp.read_json(pp.STUDIO_DEFAULTS)
    S = D["sizes"]
    T, note = pp.suggest_cells(cm)
    kinds = [k["kind"] for k in D["plans"]][:2]
    return {"height_cells": T, "height_note": note, "screen": [320, 180], "plans": 2, "kinds": kinds, "budget": 6,
            "heads_guide": S["heads_child"] if cm and cm < S["child_below_cm"] else S["heads_default"],
            "notes": {"keep": "", "drop": "", "main": ""}, "suggested": True}


def gen_used(x: pp.Ctx) -> tuple[int, list]:
    log = pp.read_json(x.gen_log()) if x.gen_log().exists() else []
    return sum(1 for e in log if not e.get("dry_run")), log


def plan_steps(cid: str) -> tuple[list[tuple[str, str, list[str]]], dict]:
    """픽셀 만들기의 단계. 이미 있는 1 · 2단계 그림은 다시 뽑지 않는다 (실패한 곳부터 다시)."""
    x = pp.Ctx(cid)
    s1 = [p for p in x.plans() if not x.s1_raw(p).exists()]
    s2 = [j for j in x.jobs() if not x.s2_raw(j).exists()]
    steps = [("s1", f"1단계 뽑기 · 안 {p} ({x.plans()[p].get('label', '')})", ["s1", cid, "--plan", p]) for p in s1]
    steps.append(("guide", "밑그림 (목표 칸 수로 다시 깔기)", ["guide", cid]))
    steps += [("s2", f"2단계 뽑기 · 후보 {j}", ["s2", cid, "--job", j]) for j in s2]
    steps += [("master", "마스터 (칸 읽기 · 색 묶기 · 손본 칸)", ["master", cid]),
              ("measure", "재기 (형식 · 그림)", ["measure", cid]),
              ("compare", "비교 그림", ["compare", cid]),
              ("lineup", "승인된 캐릭터와 어두운 게임 화면에 함께", ["lineup", cid]),
              ("candidates", "후보를 등록부에 올리기", ["candidates", cid]),
              ("report", "보고 화면 갱신 (charpipe build)", ["report"])]
    used, _ = gen_used(x)
    budget = (x.cfg.get("generate") or {}).get("budget")
    cost = {"s1": s1, "s2": s2, "calls": len(s1) + len(s2), "used": used, "budget": budget,
            "remaining": None if budget is None else budget - used, "practice": Conf.practice}
    return steps, cost


def palette_info(m) -> tuple[list[dict], bool, set]:
    import numpy as np
    a = np.array(m.convert("RGBA"))
    op = a[..., 3] > 0
    cols, cnt = np.unique(a[op][:, :3], axis=0, return_counts=True)
    lum = cols @ np.array([0.299, 0.587, 0.114])
    order = np.argsort(lum)
    return [{"hex": "#" + pp.hx(cols[i]), "cells": int(cnt[i])} for i in order], bool((~op).any()), set()


def job_info(x: pp.Ctx, job: str, J: dict, grid: dict, meas: dict, dec: dict) -> dict:
    m = x.master(job)
    d = m.parent
    stem = f"{x.cid}_{job}"
    info = {"key": job, "plan": J["plan"], "plan_label": x.plans().get(J["plan"], {}).get("label", J["plan"]),
            "plan_kind": x.plans().get(J["plan"], {}).get("kind"), "height": J["height"], "cell": J["cell"],
            "s1": rel(x.s1_raw(J["plan"])) if x.s1_raw(J["plan"]).exists() else None,
            "guide": rel(x.guide_used(job)) if x.guide_used(job).exists() else None,
            "guide_cells": rel(x.work / "guides" / f"{job}_cells_x8.png") if (x.work / "guides" / f"{job}_cells_x8.png").exists() else None,
            "s2": rel(x.s2_raw(job)) if x.s2_raw(job).exists() else None,
            "master": rel(m) if m.exists() else None,
            "fixes": J.get("fixes") or [], "grid": grid.get(job), "measure": meas.get(job),
            "decision": ("승인" if (dec.get("approved") and (dec.get("pick") or {}).get("job") == job) else
                         "고름" if (dec.get("pick") or {}).get("job") == job else
                         "채택하지 않음" if job in (dec.get("rejected") or {}) else ""),
            "decision_detail": (dec.get("rejected") or {}).get(job) or ((dec.get("pick") if (dec.get("pick") or {}).get("job") == job else None)),
            "pinned": bool(x.pinned("job", job, "master"))}
    if m.exists():
        with Image.open(m) as im:
            info["size"] = list(im.size)
            info["palette"], info["has_transparent"], _ = palette_info(im)
        un = d / f"{stem}_unfixed.png"
        if info["fixes"] and un.exists():
            info["unfixed"] = rel(un)
        fj = d / f"{stem}_fixes.json"
        if info["fixes"] and fj.exists():
            info["fix_log"] = pp.read_json(fj)
    return info


def anim_info(cid: str, cfg: dict) -> dict:
    d = char_dir(cid) / "anim"
    out = {"anims": [], "previews": [], "compare": None, "review": (cfg.get("decisions") or {}).get("review")}
    for n in (cfg.get("anim") or {}).get("anims") or []:
        tl = d / n / "timeline.json"
        ck = d / n / "check.json"
        gifs = sorted(rel(p) for p in (d / n / "out").glob("*_x8.gif")) if (d / n / "out").exists() else []
        out["anims"].append({"name": n, "label": pp.read_json(tl).get("label", n) if tl.exists() else n, "gifs": gifs,
                             "pass": pp.read_json(ck)["summary"].get("pass") if ck.exists() else None})
    if (d / "preview").exists():
        out["previews"] = sorted(rel(p) for p in (d / "preview").glob("*.gif"))
        if (d / "preview" / "compare.png").exists():
            out["compare"] = rel(d / "preview" / "compare.png")
    return out


def approved_masters() -> list[dict]:
    out = []
    for oid in cp.ids_all():
        ap = pp.approvals(oid)
        if not cfg_path(oid).exists():
            continue
        o = pp.Ctx(oid)
        for v, ok in ap.items():
            p = o.final(v)
            if ok and p.exists():
                with Image.open(p) as im:
                    lab = o.cfg["name"] + ("" if v == "base" else f" ({(o.cfg.get('layers') or {}).get(v, {}).get('label', v)})")
                    out.append({"id": oid, "variant": v, "label": lab, "file": rel(p), "size": list(im.size)})
    return out


def char_detail(cid: str) -> dict:
    c = cp.load_char(cid)
    A = c["assets"]
    f = flags(cid)
    images = [{"key": k, "label": a["label"], "file": a["file"], "group": a["group"],
               "kind": k if a["group"] == "view" else (k.split("_")[1] if k.startswith("up_") else None)}
              for k, a in A.items() if a["group"] == "view" or k.startswith("up_")]
    out = {"id": cid, "name": c["name"], "kind": c.get("kind"), "kind_ko": KINDS.get(c.get("kind"), c.get("kind")),
           "story": c.get("story"), "flags": f, "images": images, "status": pp.status(cid),
           "records": list(reversed(c.get("records", [])))[:40],
           "approvals": [{k: ap.get(k) for k in ("date", "by", "quote", "note")} | {"assets": list(ap["assets"])} for ap in c.get("approvals", [])],
           "others": [m for m in approved_masters() if m["id"] != cid], "practice": Conf.practice,
           "targets": {k: v.get("label", k) for k, v in pp.targets().items()},
           "busy": Busy.what, "job": read_job(cid),
           "kinds": [{"kind": k["kind"], "label": k["label"], "why": k["why"]} for k in pp.read_json(pp.STUDIO_DEFAULTS)["plans"]]}
    if not f["pipeline"] or not (pp.read_json(cfg_path(cid)).get("references")):
        try:  # 준비 전: 어느 그림을 보낼지 미리 보인다 (pixpipe defaults 가 고를 것과 같은 함수)
            out["predicted_refs"] = [r["file"] for r in pp.studio_refs(cid, pp.read_json(pp.STUDIO_DEFAULTS))]
        except SystemExit:
            out["predicted_refs"] = []
    if not f["pipeline"]:
        out["form"] = suggest_form(cid)
        return out
    x = pp.Ctx(cid)
    cfg = x.cfg
    dec = cfg.get("decisions") or {}
    grid = pp.read_json(x.work / "grid_check.json") if (x.work / "grid_check.json").exists() else {}
    if (x.work / "measure.json").exists():
        meas = pp.read_json(x.work / "measure.json")["items"]
    else:  # 재기 파일이 없는 캐릭터(NX-07 은 파이프라인 전에 쟀다): 화면에 보일 숫자만 그 자리에서 잰다 (쓰지 않는다)
        try:
            meas = pp.measure_all(x)["items"] if any(x.master(j).exists() for j in x.jobs()) else {}
        except Exception:  # noqa: BLE001
            meas = {}
    used, log = gen_used(x)
    steps, cost = plan_steps(cid) if cfg.get("plans") else ([], None)
    out.update({
        "form": dict((cfg.get("studio") or {}).get("last_form") or suggest_form(cid)),
        "size": cfg.get("size"), "screen": cfg.get("screen"),
        "references": [{"file": r["file"], "note": r.get("note", "")} for r in cfg.get("references") or []],
        "plans": [{"key": k, "label": p.get("label", k), "kind": p.get("kind"), "why": p.get("why"),
                   "s1": rel(x.s1_raw(k)) if x.s1_raw(k).exists() else None,
                   "prompt": rel(x.dirs["prompts"] / f"s1_{k}.txt") if (x.dirs["prompts"] / f"s1_{k}.txt").exists() else None,
                   "notes_at": p.get("notes_at")} for k, p in x.plans().items()],
        "jobs": [job_info(x, j, J, grid, meas, dec) for j, J in x.jobs().items()],
        "decisions": dec, "cost": cost, "planned_steps": [s[1] for s in steps],
        "gen": {"used": used, "budget": (cfg.get("generate") or {}).get("budget"),
                "log": [{k: e.get(k) for k in ("date", "step", "name", "dry_run", "mock")} | {"out": (e.get("out") or {}).get("path")} for e in log]},
        "compare": rel(x.work / "compare.png") if (x.work / "compare.png").exists() else None,
        "lineup": pp.read_json(x.work / "lineup.json") if (x.work / "lineup.json").exists() else None,
        "anim": anim_info(cid, cfg),
    })
    return out


def overview() -> dict:
    chars = []
    for cid in cp.ids_all():
        c = cp.load_char(cid)
        f = flags(cid)
        st = pp.status(cid)
        thumb = None
        if f["pipeline"]:
            x = pp.Ctx(cid)
            ap = [v for v, ok in pp.approvals(cid).items() if ok]
            if ap:
                thumb = {"file": rel(x.final(ap[0])), "pixel": True}
            else:
                ms = [x.master(j) for j in x.jobs() if x.master(j).exists()]
                if ms:
                    thumb = {"file": rel(ms[0]), "pixel": True}
        if not thumb:
            k = "side" if "side" in c["assets"] else next((k for k in c["assets"] if k.startswith("up_")), None)
            if k:
                thumb = {"file": c["assets"][k]["file"], "pixel": False}
        if thumb and thumb["pixel"]:
            with Image.open(ROOT / thumb["file"]) as im:
                thumb["size"] = list(im.size)
        nxt = next((r for r in st if r["state"] not in (pp.STATE_DONE, pp.STATE_NA)), None)
        chars.append({"id": cid, "name": c["name"], "kind": KINDS.get(c.get("kind"), c.get("kind")), "flags": f,
                      "status": [{"name": r["name"], "state": r["state"]} for r in st], "next": nxt, "thumb": thumb,
                      "job": (read_job(cid) or {}).get("state")})
    return {"characters": chars, "practice": Conf.practice, "busy": Busy.what}


# ---------------------------------------------------------------- 작업 (픽셀 만들기)

def job_file(cid: str) -> Path:
    return char_dir(cid) / "pixel" / "work" / "studio_job.json"


def read_job(cid: str) -> dict | None:
    p = job_file(cid)
    if not p.exists():
        return None
    try:
        return pp.read_json(p)
    except (json.JSONDecodeError, OSError):
        return None


def save_job(J: dict) -> None:
    p = job_file(J["cid"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(J, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def run_job(J: dict) -> None:
    try:
        for st in J["steps"]:
            st["state"], st["started"] = "도는 중", now()
            save_job(J)
            J["log"].append(f"── {st['label']}  (pixpipe {' '.join(st['args'][:1])})")
            p = subprocess.Popen(PY + [str(TOOLS / "pixpipe.py")] + st["args"], cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env())
            last = time.time()
            out_lines = []
            for line in p.stdout:
                line = redact(line.rstrip())[:1500]
                if not line:
                    continue
                out_lines.append(line)
                J["log"].append(line)
                if len(J["log"]) > 800:
                    J["log"] = J["log"][-800:]
                if time.time() - last > 0.5:
                    save_job(J)
                    last = time.time()
            rc = p.wait()
            st["ended"] = now()
            if rc:
                st["state"] = "실패"
                J["state"] = "실패"
                J["error"] = {"step": st["label"], "reason": last_reason("\n".join(out_lines)) or f"끝 코드 {rc}",
                              "note": "이미 뽑은 그림은 남아 있다. 원인을 고친 뒤 '픽셀 만들기'를 다시 누르면 없는 것만 다시 한다."}
                break
            st["state"] = "됨"
        else:
            J["state"] = "됨"
    except Exception as e:  # noqa: BLE001
        J["state"] = "실패"
        J["error"] = {"step": "스튜디오", "reason": redact(f"{type(e).__name__}: {e}"), "note": ""}
        J["log"].append(redact(traceback.format_exc()))
    finally:
        J["ended"] = now()
        save_job(J)
        Busy.give()


def start_job(cid: str, confirm: int) -> dict:
    f = flags(cid)
    if not f["editable"]:
        raise Refused("승인된 캐릭터 · 에이전트가 손으로 쓴 설정의 캐릭터는 스튜디오에서 다시 만들지 않는다", 403)
    if not f["pipeline"] or not pp.read_json(cfg_path(cid)).get("plans"):
        raise Refused("먼저 '만들 준비'를 한다")
    steps, cost = plan_steps(cid)
    if confirm != cost["calls"]:
        raise Refused(f"확인한 생성 횟수({confirm})와 지금 필요한 횟수({cost['calls']})가 다르다. 화면을 새로 고쳐 다시 확인한다", 409)
    if cost["budget"] is None or cost["used"] + cost["calls"] > cost["budget"]:
        raise Refused(f"이미지 생성 한도를 넘는다: 한도 {cost['budget']}회 · 지금까지 {cost['used']}회 · 이번 {cost['calls']}회. "
                      f"'만들 준비' 또는 '다시 뽑기'에서 한도를 올린다", 409)
    if not Busy.take("픽셀 만들기", cid):
        raise Refused(f"다른 작업이 돌고 있다: {Busy.what}", 409)
    J = {"cid": cid, "state": "도는 중", "practice": Conf.practice, "started": now(), "cost": cost,
         "steps": [{"key": k, "label": lab, "args": args, "state": "기다림"} for k, lab, args in steps], "log": []}
    save_job(J)
    threading.Thread(target=run_job, args=(J,), daemon=True).start()
    return J


def mark_stale_jobs() -> None:
    for cid in cp.ids_all():
        J = read_job(cid)
        if J and J.get("state") == "도는 중":
            J["state"] = "실패"
            J["error"] = {"step": next((s["label"] for s in J["steps"] if s["state"] == "도는 중"), "?"),
                          "reason": "스튜디오가 꺼져 작업이 멈췄다", "note": "'픽셀 만들기'를 다시 누르면 없는 것만 다시 한다."}
            for s in J["steps"]:
                if s["state"] == "도는 중":
                    s["state"] = "실패"
            save_job(J)


# ---------------------------------------------------------------- 바꾸는 요청

def sync(what: str, cid: str | None, fn):
    if not Busy.take(what, cid):
        raise Refused(f"다른 작업이 돌고 있다: {Busy.what}", 409)
    try:
        return fn()
    finally:
        Busy.give()


def after_change(cid: str) -> None:
    """후보가 바뀐 뒤: 재기 · 비교 그림 · 함께 세우기 · 등록부 · 보고 화면."""
    for args in (["measure", cid], ["compare", cid], ["lineup", cid], ["candidates", cid]):
        pixpipe(*args)
    run_tool("pixpipe.py", ["report"])


def decode_image(d: dict, i: int) -> tuple[Image.Image, dict]:
    data = str(d.get("data") or "")
    if data.startswith("data:"):
        data = data.split(",", 1)[-1]
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise Refused(f"{i + 1}번째 파일을 읽지 못했다")
    if len(raw) > MAX_IMAGE:
        raise Refused(f"{i + 1}번째 그림이 너무 크다 ({len(raw) >> 20}MB, 한도 {MAX_IMAGE >> 20}MB)")
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(raw)) as im:
            fmt = im.format
            im.verify()
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:  # noqa: BLE001 — 그림이 아닌 파일 · 깨진 파일 · 너무 큰 그림
        raise Refused(f"{i + 1}번째 파일은 그림(PNG · JPG · WebP)이 아니다")
    if fmt not in ("PNG", "JPEG", "WEBP"):
        raise Refused(f"{i + 1}번째 파일의 형식({fmt})은 받지 않는다. PNG · JPG · WebP 만")
    if min(im.size) < 64:
        raise Refused(f"{i + 1}번째 그림이 너무 작다 ({im.width}×{im.height})")
    kind = d.get("kind")
    if kind not in UP_KINDS:
        raise Refused(f"{i + 1}번째 그림의 종류를 고른다 (측면 / 정면 / 후면 / 그 밖)")
    return im.convert("RGBA"), {"kind": kind, "name": clean_text(Path(str(d.get("name") or "")).name, 80), "format": fmt, "size": list(im.size)}


def api_new(b: dict) -> dict:
    name = clean_text(b.get("name"), 40)
    cid = str(b.get("id") or "")
    if not name:
        raise Refused("이름을 적는다")
    if not ID_RE.fullmatch(cid):
        raise Refused("식별자는 영문 소문자로 시작하고 영문 소문자 · 숫자 · 밑줄만 (2~32자)")
    if cid in cp.ids_all() or char_dir(cid).exists() or (ROOT / "art/prompts/pipeline" / cid).exists():
        raise Refused(f"이미 있는 식별자다: {cid}", 409)
    kind = b.get("kind") if b.get("kind") in KINDS else "npc"
    cm = b.get("height_cm")
    if cm not in (None, ""):
        try:
            cm = float(cm)
        except (TypeError, ValueError):
            raise Refused("키(cm)는 숫자로")
        if not 30 <= cm <= 500:
            raise Refused("키(cm)는 30 ~ 500")
    else:
        cm = None
    imgs = b.get("images") or []
    if not imgs:
        raise Refused("원화를 한 장 이상 올린다")
    if len(imgs) > MAX_IMAGES:
        raise Refused(f"원화는 {MAX_IMAGES}장까지")
    decoded = [decode_image(d, i) for i, d in enumerate(imgs)]  # 모두 확인한 뒤에 쓴다

    def work():
        up = char_dir(cid) / "upload"
        made_reg = False
        try:
            up.mkdir(parents=True, exist_ok=False)
            files = []
            count = {}
            for im, meta in decoded:
                count[meta["kind"]] = count.get(meta["kind"], 0) + 1
                k = f"{meta['kind']}_{count[meta['kind']]}"
                p = up / f"{k}.png"
                im.save(p)
                files.append((k, p, meta))
            args = ["register", cid, "--name", name, "--kind", kind]
            if cm:
                args += ["--height-cm", str(cm), "--height-mark", "스튜디오에서 기획자가 넣은 값"]
            code, out = run_tool("charpipe.py", args)
            if code:
                raise Refused("등록 실패: " + last_reason(out), 500)
            made_reg = True
            for k, p, meta in files:
                extra = {"source": {"made_by": "tools/pixstudio.py (기획자가 올림)", "uploaded_name": meta["name"],
                                    "uploaded_format": meta["format"], "converted": "PNG (RGBA)", "date": now()[:10]},
                         "upload_kind": meta["kind"]}
                if meta["kind"] == "side":
                    extra["facing"] = "right"
                code, out = run_tool("charpipe.py", ["add", cid, f"up_{k}", rel(p), "--group", "design",
                                                     "--label", f"올린 원화 · {UP_KINDS[meta['kind']]} {k.split('_')[1]}",
                                                     "--extra", json.dumps(extra, ensure_ascii=False)])
                if code:
                    raise Refused("원화 등록 실패: " + last_reason(out), 500)
            pixpipe("init", cid)
            return {"id": cid}
        except Exception:
            # 되돌린다: 이번에 만든 폴더와 등록부의 줄만
            shutil.rmtree(char_dir(cid), ignore_errors=True)
            if made_reg:
                reg = cp.load_registry()
                reg["characters"] = [c for c in reg["characters"] if c["id"] != cid]
                cp.save_registry(reg)
            raise

    return sync("새 캐릭터", cid, work)


def form_of(b: dict, cid: str, add: bool) -> dict:
    F = {}
    if not add:
        try:
            F["height_cells"] = int(b.get("height_cells"))
        except (TypeError, ValueError):
            raise Refused("목표 키(칸)는 숫자로")
        if not 12 <= F["height_cells"] <= 96:
            raise Refused("목표 키는 12 ~ 96칸")
        sc = b.get("screen")
        if sc not in SCREENS:
            raise Refused("화면 밀도는 " + " · ".join(f"{w}×{h}" for w, h in SCREENS))
        F["screen"] = sc
        try:
            F["heads_guide"] = round(float(b.get("heads_guide")), 2)
        except (TypeError, ValueError):
            raise Refused("머리 비율은 숫자로")
        if not 2.0 <= F["heads_guide"] <= 6.0:
            raise Refused("머리 비율은 2.0 ~ 6.0")
    kinds_all = [k["kind"] for k in pp.read_json(pp.STUDIO_DEFAULTS)["plans"]]
    if add:
        kinds = [k for k in (b.get("kinds") or []) if k in kinds_all]
        if not 1 <= len(kinds) <= 3:
            raise Refused("밝기 계획을 1 ~ 3개 고른다")
        F["kinds"], F["plans"] = kinds, len(kinds)
    else:
        try:
            n = int(b.get("plans"))
        except (TypeError, ValueError):
            raise Refused("변형 수는 1 ~ 3")
        if not 1 <= n <= 3:
            raise Refused("변형 수는 1 ~ 3")
        F["plans"], F["kinds"] = n, kinds_all[:n]
    try:
        F["budget"] = int(b.get("budget"))
    except (TypeError, ValueError):
        raise Refused("생성 한도는 숫자로")
    if not 0 <= F["budget"] <= 40:
        raise Refused("생성 한도는 0 ~ 40회")
    nb = b.get("notes") or {}
    F["notes"] = {k: clean_text(nb.get(k), 300) for k in ("keep", "drop", "main")}
    return F


def api_prepare(cid: str, b: dict, add: bool) -> dict:
    f = flags(cid)
    if not f["editable"]:
        raise Refused("승인된 캐릭터 · 에이전트가 손으로 쓴 설정의 캐릭터는 스튜디오에서 다시 만들지 않는다", 403)
    F = form_of(b, cid, add)

    def work():
        p = char_dir(cid) / "pixel" / "work" / "studio_form.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(F, ensure_ascii=False, indent=1), encoding="utf-8")
        args = ["defaults", cid, "--form", rel(p)] + (["--add"] if add else [])
        return {"out": pixpipe(*args)}

    return sync("다시 뽑기 준비" if add else "만들 준비", cid, work)


def api_fix(cid: str, b: dict, undo: bool) -> dict:
    f = flags(cid)
    if not f["editable"]:
        raise Refused("승인된 캐릭터의 후보는 손보지 않는다", 403)
    job = str(b.get("job") or "")
    cell = b.get("cell") or []
    if not (isinstance(cell, list) and len(cell) == 2 and all(isinstance(v, int) and 0 <= v < 512 for v in cell)):
        raise Refused("칸이 잘못됐다")
    args = (["unfix", cid, "--job", job, "--cell", f"{cell[0]},{cell[1]}"] if undo else
            ["fix", cid, "--job", job, "--cell", f"{cell[0]},{cell[1]}", "--by", "기획자 (스튜디오)"])
    if not undo:
        why = clean_text(b.get("why"), 500)
        if not why:
            raise Refused("고치는 이유를 적는다")
        color = b.get("color")
        if color == "transparent":
            args.append("--transparent")
        elif isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            args += ["--color", color]
        else:
            raise Refused("색을 고른다")
        args += ["--why", why]

    def work():
        out = pixpipe(*args)
        after_change(cid)
        return {"out": out}

    return sync("칸 되돌리기" if undo else "칸 손보기", cid, work)


def api_decide(cid: str, b: dict) -> dict:
    f = flags(cid)
    if f["approved"] or f["handwritten"]:
        raise Refused("이 캐릭터의 고름 · 승인은 이미 끝났다 (에이전트와 함께 한 기록). 스튜디오에서 바꾸지 않는다", 403)
    act, job = b.get("action"), str(b.get("job") or "")
    quote = clean_text(b.get("quote"), 1000) or "(의견을 적지 않았다)"
    x = pp.Ctx(cid)
    if job not in x.jobs() or not x.master(job).exists():
        raise Refused(f"후보가 없다: {job}")
    saw = ["스튜디오 리뷰 화면 (tools/pixstudio.py)", rel(x.master(job))]
    for p in (x.work / "lineup_screen.png", x.work / "compare.png"):
        if p.exists():
            saw.append(rel(p))
    sv = [a for s in saw for a in ("--saw", s)]
    if act == "pick":
        args = ["pick", cid, "--job", job, "--quote", quote] + sv
    elif act == "approve":
        if ((x.cfg.get("decisions") or {}).get("pick") or {}).get("job") != job:
            raise Refused("승인은 고른 후보에만 한다. 먼저 '이 후보로 고름'")
        args = ["approve", cid, "--quote", quote, "--note", "스튜디오에서 기획자가 승인"] + sv
    elif act == "reject":
        args = ["reject", cid, "--job", job, "--quote", quote] + sv
    else:
        raise Refused("결정의 종류가 잘못됐다")

    def work():
        out = pixpipe(*args)
        pixpipe("lineup", cid)
        run_tool("pixpipe.py", ["report"])
        return {"out": out}

    return sync("결정 기록", cid, work)


def api_review(cid: str, b: dict) -> dict:
    verdict = b.get("verdict")
    if verdict not in VERDICTS:
        raise Refused("평가를 고른다: " + " / ".join(VERDICTS))
    if not cfg_path(cid).exists():
        raise Refused("파이프라인이 없는 캐릭터다")
    quote = clean_text(b.get("quote"), 1000) or "(의견을 적지 않았다)"

    def work():
        out = pixpipe("review", cid, "--quote", quote, "--verdict", verdict, "--saw", "스튜디오 동작 화면 (tools/pixstudio.py)",
                      "--note", "스튜디오에서 기획자가 적음")
        run_tool("pixpipe.py", ["report"])
        return {"out": out}

    return sync("평가 기록", cid, work)


# ---------------------------------------------------------------- HTTP

def safe_file(path: str) -> Path | None:
    path = unquote(path)
    if "\x00" in path or "\\" in path or ":" in path:
        return None
    parts = path.split("/")
    if any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        return None
    if not (path in FILE_ONE or path.startswith(FILE_ROOTS)):
        return None
    p = (ROOT / path).resolve()
    try:
        r = p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None
    if not (r in FILE_ONE or r.startswith(FILE_ROOTS)) or p.suffix.lower() not in FILE_EXT or not p.is_file():
        return None
    return p


class Handler(BaseHTTPRequestHandler):
    server_version = "pixstudio"
    sys_version = ""

    def log_message(self, fmt, *args):  # 조용히 (오류만 찍는다)
        pass

    # 응답
    def send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def json(self, code: int, data) -> None:
        self.send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def deny(self, code: int, msg: str) -> None:
        self.json(code, {"error": msg})

    # 확인
    def host_ok(self) -> bool:
        return self.headers.get("Host", "") in Conf.hosts

    def origin_ok(self) -> bool:
        o = self.headers.get("Origin")
        if o is not None and o not in Conf.origins:
            return False
        return self.headers.get("Sec-Fetch-Site", "same-origin") in ("same-origin", "none")

    def token_ok(self) -> bool:
        return hmac.compare_digest(self.headers.get("X-Studio-Token", ""), Conf.token)

    def cookie_ok(self) -> bool:
        ck = self.headers.get("Cookie", "")
        m = re.search(r"(?:^|;\s*)pxs=([A-Za-z0-9_\-]+)", ck)
        return bool(m) and hmac.compare_digest(m.group(1), Conf.token)

    def do_GET(self):
        if not self.host_ok():
            return self.deny(403, "Host 가 맞지 않는다")
        u = urlsplit(self.path)
        path = u.path
        if path == "/ping":
            return self.send(200, b"pixstudio", "text/plain; charset=utf-8")
        if path in ("/", "/index.html"):
            html = (STATIC / "index.html").read_text(encoding="utf-8")
            html = html.replace("__TOKEN__", Conf.token).replace("__PRACTICE__", "1" if Conf.practice else "0")
            return self.send(200, html.encode("utf-8"), "text/html; charset=utf-8", {
                "Set-Cookie": f"pxs={Conf.token}; Path=/; HttpOnly; SameSite=Strict",
                "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; "
                                           "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"})
        if path.startswith("/static/"):
            name = path[len("/static/"):]
            if name not in STATIC_FILES:
                return self.deny(404, "없다")
            return self.send(200, (STATIC / name).read_bytes(), STATIC_FILES[name])
        if path.startswith("/files/"):
            if not self.cookie_ok() or not self.origin_ok():
                return self.deny(403, "스튜디오 화면에서만 연다")
            p = safe_file(path[len("/files/"):])
            if p is None:
                return self.deny(404, "내줄 수 없는 파일이다")
            return self.send(200, p.read_bytes(), FILE_EXT[p.suffix.lower()], {"Cache-Control": "no-cache"})
        if path.startswith("/api/"):
            if not self.token_ok() or not self.origin_ok():
                return self.deny(403, "토큰이 없거나 맞지 않는다")
            return self.route("GET", path, None)
        return self.deny(404, "없다")

    def do_POST(self):
        if not self.host_ok():
            return self.deny(403, "Host 가 맞지 않는다")
        if not self.origin_ok():
            return self.deny(403, "다른 곳에서 온 요청이다")
        if not self.token_ok():
            return self.deny(403, "토큰이 없거나 맞지 않는다")
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return self.deny(415, "JSON 만 받는다")
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.deny(400, "길이가 잘못됐다")
        if n > MAX_BODY:
            return self.deny(413, f"요청이 너무 크다 (한도 {MAX_BODY >> 20}MB)")
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.deny(400, "JSON 이 아니다")
        if not isinstance(body, dict):
            return self.deny(400, "JSON 객체가 아니다")
        u = urlsplit(self.path)
        if not u.path.startswith("/api/"):
            return self.deny(404, "없다")
        return self.route("POST", u.path, body)

    def do_PUT(self):
        self.deny(405, "쓰지 않는 방법")

    do_DELETE = do_PATCH = do_OPTIONS = do_PUT

    def route(self, method: str, path: str, body):
        parts = path.strip("/").split("/")[1:]  # api/... 뒤
        try:
            if method == "GET":
                if parts == ["overview"]:
                    return self.json(200, overview())
                if parts == ["busy"]:
                    return self.json(200, {"busy": Busy.what})
                if len(parts) == 2 and parts[0] == "char":
                    return self.json(200, char_detail(need_id(parts[1])))
                if len(parts) == 3 and parts[0] == "char" and parts[2] == "job":
                    return self.json(200, {"job": read_job(need_id(parts[1])), "busy": Busy.what})
            else:
                if parts == ["new"]:
                    return self.json(200, api_new(body))
                if len(parts) == 3 and parts[0] == "char":
                    cid, act = need_id(parts[1]), parts[2]
                    if act == "prepare":
                        return self.json(200, api_prepare(cid, body, add=False))
                    if act == "redraw":
                        return self.json(200, api_prepare(cid, body, add=True))
                    if act == "run":
                        try:
                            confirm = int(body.get("confirm_calls"))
                        except (TypeError, ValueError):
                            raise Refused("확인한 생성 횟수가 없다")
                        return self.json(200, {"job": start_job(cid, confirm)})
                    if act == "fix":
                        return self.json(200, api_fix(cid, body, undo=False))
                    if act == "unfix":
                        return self.json(200, api_fix(cid, body, undo=True))
                    if act == "decide":
                        return self.json(200, api_decide(cid, body))
                    if act == "review":
                        return self.json(200, api_review(cid, body))
            return self.deny(404, "없는 요청")
        except Refused as e:
            return self.deny(e.code, str(e))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self.deny(500, redact(f"스튜디오 오류: {type(e).__name__}: {e}"))


class Server(ThreadingHTTPServer):
    allow_reuse_address = False  # Windows 에서 SO_REUSEADDR 는 같은 포트를 두 프로그램이 잡게 한다
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def already_running() -> int | None:
    if not RUNNING.exists():
        return None
    try:
        port = int(json.loads(RUNNING.read_text(encoding="utf-8"))["port"])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/ping", timeout=1.5) as r:
            if r.read() == b"pixstudio":
                return port
    except Exception:  # noqa: BLE001
        return None
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="캐릭터 픽셀 스튜디오 (PC 안에서만 도는 화면)")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--practice", action="store_true", help="연습 모드: 이미지 생성 없이 미리네의 그림을 복사한다")
    a = ap.parse_args()
    other = already_running()
    if other:
        print(f"스튜디오가 이미 켜져 있다: http://127.0.0.1:{other}/ — 그 화면을 연다. (이 창은 닫아도 된다)")
        if not a.no_browser:
            webbrowser.open(f"http://127.0.0.1:{other}/")
        return
    srv = None
    for port in list(range(a.port, a.port + 20)) + [0]:
        try:
            srv = Server(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if srv is None:
        sys.exit("포트를 잡지 못했다")
    Conf.port = srv.server_address[1]
    Conf.token = secrets.token_urlsafe(32)
    Conf.practice = a.practice
    Conf.hosts = {f"127.0.0.1:{Conf.port}", f"localhost:{Conf.port}"}
    Conf.origins = {f"http://127.0.0.1:{Conf.port}", f"http://localhost:{Conf.port}"}
    mark_stale_jobs()
    RUNNING.write_text(json.dumps({"pid": os.getpid(), "port": Conf.port, "started": now(), "practice": a.practice}), encoding="utf-8")
    url = f"http://127.0.0.1:{Conf.port}/"
    print("=" * 64)
    print(" 캐릭터 픽셀 스튜디오" + ("  [연습 모드 — 이미지 생성 없음]" if a.practice else ""))
    print(f" 화면: {url}")
    print(" 이 창을 닫으면 스튜디오가 꺼진다. (PC 안에서만 열린다)")
    print("=" * 64)
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if RUNNING.exists() and json.loads(RUNNING.read_text(encoding="utf-8")).get("pid") == os.getpid():
                RUNNING.unlink()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    main()
