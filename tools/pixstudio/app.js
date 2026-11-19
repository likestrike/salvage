// 캐릭터 픽셀 스튜디오 — 화면 (tools/pixstudio.py 가 내준다). 프레임워크 없이.
"use strict";

const TOKEN = document.querySelector('meta[name="studio-token"]').content;
const PRACTICE = document.querySelector('meta[name="studio-practice"]').content === "1";
const S = { bust: Date.now(), zoom: 0, d: null, ov: null, poll: null, tab: "prepare", id: null };
const PK = [
  ["largest_value_mass_pct", "가장 큰 밝기 덩어리", "%"], ["value_top3_pct", "밝기 덩어리 위 3개", "%"],
  ["region_big_pct", "큰 색 덩어리 (20칸 이상)", "%"], ["region_mid_pct", "중간 조각 (4~19칸)", "%"],
  ["region_small_pct", "작은 획 (3칸 이하)", "%"], ["accent_pct", "채도 높은 칸", "%"],
  ["L_mean", "평균 밝기 L*", ""], ["face_contrast", "얼굴과 둘레의 밝기 차", ""],
];
const STATE_CLASS = { "됨": "done", "기획자 결정 대기": "wait", "해당 없음": "na", "아직": "" };
const UPK = { side: "측면", front: "정면", back: "후면", other: "그 밖" };

// ---------------------------------------------------------------- 작은 도구
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k in el && k !== "list") el[k] = v;
    else el.setAttribute(k, v);
  }
  for (const c of kids.flat(3)) if (c !== null && c !== undefined && c !== false) el.append(c.nodeType ? c : String(c));
  return el;
}
const $ = (s, el = document) => el.querySelector(s);
const put = (el, ...kids) => { for (const c of kids.flat(3)) if (c !== null && c !== undefined && c !== false && c !== "") el.append(c); };
const fill = (el, ...kids) => { el.replaceChildren(); put(el, ...kids); };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const F = (p) => "/files/" + p.split("/").map(encodeURIComponent).join("/") + "?v=" + S.bust;

async function api(path, body) {
  const r = await fetch("/api" + path, {
    method: body ? "POST" : "GET",
    headers: { "X-Studio-Token": TOKEN, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  let j = {};
  try { j = await r.json(); } catch (e) { j = { error: "응답을 읽지 못했다 (" + r.status + ")" }; }
  if (!r.ok) throw new Error(j.error || ("요청 실패 " + r.status));
  return j;
}

function toast(msg, ok) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (ok ? " okt" : "");
  t.hidden = false;
  clearTimeout(toast.tm);
  toast.tm = setTimeout(() => (t.hidden = true), ok ? 3500 : 9000);
}

function openModal(node) {
  const m = $("#modal");
  m.replaceChildren(h("div", { class: "dialog" }, node));
  m.hidden = false;
}
function closeModal() { $("#modal").hidden = true; $("#modal").replaceChildren(); }

// 확인 대화 상자. text: true 면 의견 칸을 두고 그 글을 돌려준다
function ask({ title, body, ok = "확인", okClass = "primary", text = false, placeholder = "" }) {
  return new Promise((resolve) => {
    const ta = text ? h("textarea", { placeholder, rows: 3 }) : null;
    const done = (v) => { closeModal(); resolve(v); };
    openModal(h("div", {},
      h("h2", { text: title }), body,
      ta ? h("label", { class: "f", text: "의견 (원문 그대로 기록에 남는다)" }) : null, ta,
      h("div", { class: "actions" },
        h("button", { class: okClass, text: ok, onclick: () => done(text ? ta.value : true) }),
        h("button", { text: "취소", onclick: () => done(null) }))));
    if (ta) ta.focus();
  });
}

function pixImg(file, w, hgt, z, extra = {}) {
  return h("img", { class: "px", src: F(file), width: w * z, height: hgt * z, alt: file.split("/").pop(), ...extra });
}

// 한글 이름 → 영문 식별자 제안 (국어의 로마자 표기법을 단순화. 받침의 연음은 하지 않는다)
const CHO = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"];
const JUNG = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"];
const JONG = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"];
function romanize(name) {
  let s = "";
  for (const ch of name.trim().toLowerCase()) {
    const c = ch.codePointAt(0);
    if (c >= 0xac00 && c <= 0xd7a3) {
      const i = c - 0xac00;
      s += CHO[Math.floor(i / 588)] + JUNG[Math.floor((i % 588) / 28)] + JONG[i % 28];
    } else if (/[a-z0-9]/.test(ch)) s += ch;
    else s += "_";
  }
  s = s.replace(/_+/g, "_").replace(/^_|_$/g, "");
  if (!/^[a-z]/.test(s)) s = "c_" + s;
  s = s.slice(0, 32).replace(/_$/, "");
  if (s.length < 2) s = "char";
  const ids = new Set((S.ov ? S.ov.characters : []).map((c) => c.id));
  let out = s, n = 2;
  while (ids.has(out)) out = s.slice(0, 29) + "_" + n++;
  return out;
}

// ---------------------------------------------------------------- 길 (#/ · #/new · #/c/<id>/<탭>)
async function route() {
  clearInterval(S.poll);
  S.poll = null;
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const app = $("#app");
  try {
    if (!parts.length) return await renderList(app);
    if (parts[0] === "new") return await renderNew(app);
    if (parts[0] === "c" && parts[1]) {
      if (S.id !== parts[1]) S.zoom = 0;
      S.id = parts[1];
      S.tab = parts[2] || "prepare";
      return await renderChar(app);
    }
    location.hash = "#/";
  } catch (e) {
    app.replaceChildren(h("div", { class: "err" }, "화면을 그리지 못했다: " + e.message), h("p", {}, h("a", { href: "#/", text: "목록으로" })));
  }
}
window.addEventListener("hashchange", route);

async function busyTick() {
  try {
    const j = await api("/busy");
    const b = $("#busy");
    if (j.busy) { b.hidden = false; b.textContent = "작업 중: " + j.busy.what + (j.busy.cid ? " (" + j.busy.cid + ")" : ""); }
    else b.hidden = true;
  } catch (e) { /* 서버가 꺼졌을 수 있다 */
    const b = $("#busy"); b.hidden = false; b.textContent = "스튜디오와 연결이 끊겼다 — 검은 창이 닫혔는지 본다";
  }
}

// ---------------------------------------------------------------- 1. 목록
async function renderList(app) {
  $("#crumb").textContent = "";
  S.ov = await api("/overview");
  const cards = S.ov.characters.map((c) => {
    let th = null;
    if (c.thumb && c.thumb.pixel) {
      const z = clamp(Math.floor(176 / c.thumb.size[1]), 1, 12);
      th = pixImg(c.thumb.file, c.thumb.size[0], c.thumb.size[1], z);
    } else if (c.thumb) th = h("img", { class: "illu", src: F(c.thumb.file), alt: c.name });
    const badges = [];
    if (c.flags.approved) badges.push(h("span", { class: "badge ok", text: "픽셀 마스터 승인됨" }));
    if (c.flags.handwritten) badges.push(h("span", { class: "badge", text: "에이전트가 쓴 설정" }));
    if (c.flags.studio) badges.push(h("span", { class: "badge", text: "스튜디오로 만듦" }));
    if (!c.flags.pipeline) badges.push(h("span", { class: "badge", text: "픽셀 아직" }));
    if (c.job === "도는 중") badges.push(h("span", { class: "badge wait", text: "만드는 중" }));
    if (c.job === "실패") badges.push(h("span", { class: "badge bad", text: "지난 작업 실패" }));
    const done = c.status.filter((r) => r.state === "됨").length;
    return h("div", { class: "card", onclick: () => (location.hash = "#/c/" + c.id + "/" + (c.flags.pipeline ? "review" : "prepare")) },
      h("div", { class: "thumb" }, th || h("span", { class: "dim", text: "그림 없음" })),
      h("div", { class: "name", text: c.name }),
      h("div", { class: "dim", text: c.id + " · " + c.kind }),
      h("div", { class: "badges" }, badges),
      h("div", { class: "steps", title: c.status.map((r) => r.name + ": " + r.state).join("\n") },
        c.status.map((r) => h("i", { class: STATE_CLASS[r.state] || "" }))),
      h("div", { class: "dim" }, "파이프라인 " + done + " / " + c.status.length + " 단계 됨",
        c.next ? h("span", {}, " · 다음: " + c.next.name + " (" + c.next.state + ")") : null));
  });
  app.replaceChildren(
    h("div", { class: "row" }, h("h1", { text: "캐릭터" }), h("span", { style: { flex: 1 } }),
      h("button", { class: "primary", text: "새 캐릭터", onclick: () => (location.hash = "#/new") })),
    h("p", { class: "sub", text: "등록부의 캐릭터와 픽셀 파이프라인의 어느 단계인지. 카드를 누르면 연다. 막대의 칸 = 파이프라인의 14단계 (초록 됨 · 노랑 기획자 결정 대기 · 회색 아직)." }),
    h("div", { class: "cards" }, cards));
}

// ---------------------------------------------------------------- 2. 새 캐릭터 (올리기)
async function renderNew(app) {
  $("#crumb").textContent = "› 새 캐릭터";
  if (!S.ov) S.ov = await api("/overview");
  const files = [];
  let idTouched = false;
  const name = h("input", { type: "text", placeholder: "예: 미리네의 삼촌", style: { width: "260px" } });
  const id = h("input", { type: "text", placeholder: "영문 소문자 · 숫자 · 밑줄", style: { width: "260px" } });
  const kind = h("select", {}, [["npc", "등장인물"], ["companion", "동행"], ["enemy", "적"], ["player", "플레이어"]].map(([v, t]) => h("option", { value: v, text: t })));
  const cm = h("input", { type: "number", min: 30, max: 500, step: 1, placeholder: "선택" });
  const list = h("div", { class: "uplist" });
  const pick = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp", multiple: true, hidden: true });
  const drop = h("div", { class: "drop" }, "원화를 여기에 끌어 놓거나 ", h("button", { text: "파일 고르기", onclick: () => pick.click() }),
    h("div", { class: "dim", text: "PNG · JPG · WebP, 한 장에 20MB 까지, 8장까지. 측면 한 장만 있어도 된다." }));
  name.addEventListener("input", () => { if (!idTouched) id.value = romanize(name.value); });
  id.addEventListener("input", () => (idTouched = true));
  const add = (fl) => {
    for (const f of fl) {
      if (files.length >= 8) { toast("원화는 8장까지"); break; }
      if (!/^image\/(png|jpeg|webp)$/.test(f.type)) { toast(f.name + ": PNG · JPG · WebP 만 올린다"); continue; }
      if (f.size > 20 * 1024 * 1024) { toast(f.name + ": 20MB 를 넘는다"); continue; }
      files.push({ file: f, kind: files.some((x) => x.kind === "side") ? (files.some((x) => x.kind === "front") ? "other" : "front") : "side", url: URL.createObjectURL(f) });
    }
    draw();
  };
  const draw = () => fill(list, ...files.map((it, i) => h("div", { class: "u" },
    h("img", { src: it.url, alt: it.file.name }),
    h("div", { class: "dim", text: it.file.name }),
    h("div", { class: "row" },
      h("select", { onchange: (e) => (it.kind = e.target.value) }, Object.entries(UPK).map(([v, t]) => h("option", { value: v, text: t, selected: it.kind === v }))),
      h("button", { text: "빼기", onclick: () => { files.splice(i, 1); draw(); } })))));
  pick.addEventListener("change", () => add(pick.files));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); add(e.dataTransfer.files); });
  const go = h("button", { class: "primary", text: "올리고 등록하기" });
  go.addEventListener("click", async () => {
    if (!name.value.trim()) return toast("이름을 적는다");
    if (!/^[a-z][a-z0-9_]{1,31}$/.test(id.value)) return toast("식별자는 영문 소문자로 시작하고 영문 소문자 · 숫자 · 밑줄만 (2~32자)");
    if (!files.length) return toast("원화를 한 장 이상 올린다");
    if (!files.some((f) => f.kind === "side")) {
      const ok = await ask({ title: "측면 그림이 없다", body: h("p", { text: "게임의 도트는 오른쪽을 보는 옆모습이다. 측면 그림 없이도 진행할 수 있지만 첫 그림(정면)에서 옆모습을 지어내야 한다. 그대로 올릴까?" }), ok: "그대로 올림" });
      if (!ok) return;
    }
    go.disabled = true; go.textContent = "올리는 중…";
    try {
      const images = await Promise.all(files.map((f) => new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res({ kind: f.kind, name: f.file.name, data: r.result });
        r.onerror = () => rej(new Error(f.file.name + " 을 읽지 못했다"));
        r.readAsDataURL(f.file);
      })));
      const j = await api("/new", { name: name.value, id: id.value, kind: kind.value, height_cm: cm.value || null, images });
      toast("등록했다: " + j.id, true);
      S.ov = null;
      location.hash = "#/c/" + j.id + "/prepare";
    } catch (e) { toast(e.message); go.disabled = false; go.textContent = "올리고 등록하기"; }
  });
  app.replaceChildren(
    h("h1", { text: "새 캐릭터 — 원화 올리기" }),
    h("p", { class: "sub", text: "이름과 원화를 올리면 등록부에 올리고 픽셀 파이프라인의 설정 파일을 만든다. 설정화 묶음이 이미 있는 캐릭터(아버지 · 삼촌)는 여기서 올리지 않고 목록에서 연다." }),
    h("div", { class: "panel" },
      h("label", { class: "f", text: "이름 (한글)" }), name,
      h("label", { class: "f", text: "식별자 (영문 — 이름에서 제안한다. 파일 이름이 된다)" }), id,
      h("div", { class: "row" },
        h("div", {}, h("label", { class: "f", text: "종류" }), kind),
        h("div", {}, h("label", { class: "f", text: "설정상의 키 (cm, 선택)" }), cm,
          h("span", { class: "dim", text: "  목표 키(칸)를 제안할 때 쓴다" }))),
      h("label", { class: "f", text: "원화 (그림마다 종류를 고른다)" }), drop, pick, list),
    h("div", { class: "actions" }, go, h("button", { text: "취소", onclick: () => (location.hash = "#/") })));
}

// ---------------------------------------------------------------- 3~6. 캐릭터
const TABS = [["prepare", "만들 준비"], ["make", "픽셀 만들기"], ["review", "리뷰"], ["anim", "동작"], ["records", "기록"]];

async function loadDetail() { S.d = await api("/char/" + S.id); return S.d; }

async function renderChar(app) {
  const d = await loadDetail();
  $("#crumb").textContent = "› " + d.name;
  const f = d.flags;
  const badges = [];
  if (f.approved) badges.push(h("span", { class: "badge ok", text: "픽셀 마스터 승인됨" }));
  if (f.handwritten) badges.push(h("span", { class: "badge", text: "에이전트가 손으로 쓴 설정" }));
  if (f.studio) badges.push(h("span", { class: "badge", text: "스튜디오의 기본 문장" }));
  if (d.practice) badges.push(h("span", { class: "badge prac", text: "연습 모드" }));
  const body = h("div", {});
  app.replaceChildren(
    h("div", { class: "row" }, h("h1", { text: d.name }), h("span", { class: "dim", text: d.id + " · " + d.kind_ko + (d.story && d.story.height_cm ? " · 설정상 키 " + d.story.height_cm + "cm" : "") }), h("div", { class: "badges" }, badges)),
    h("div", { class: "status", title: "파이프라인의 단계 (pixpipe status)" },
      d.status.map((r) => h("div", { class: STATE_CLASS[r.state] || "", title: r.who + " · " + r.cmd + (r.detail ? "\n" + r.detail : "") }, r.name, h("br"), h("b", { text: r.state })))),
    h("nav", { class: "tabs" }, TABS.map(([k, t]) => h("a", { href: "#/c/" + d.id + "/" + k, class: S.tab === k ? "on" : "", text: t }))),
    body);
  ({ prepare: tabPrepare, make: tabMake, review: tabReview, anim: tabAnim, records: tabRecords }[S.tab] || tabPrepare)(d, body);
}

function lockedNote(d) {
  if (d.flags.handwritten || d.flags.approved)
    return h("div", { class: "note" }, d.flags.handwritten
      ? "이 캐릭터는 에이전트가 손으로 쓴 설정으로 만들었고 픽셀 마스터가 승인됐다. 스튜디오에서 다시 만들거나 손보지 않는다 — 리뷰 · 동작 · 기록은 볼 수 있다. 바꾸려면 에이전트에게 맡긴다."
      : "이 캐릭터의 픽셀 마스터는 승인됐다. 승인된 그림을 지키려고 스튜디오에서 다시 뽑거나 손보지 않는다 (보기와 동작 평가만).");
  return null;
}

// 3. 만들 준비
function tabPrepare(d, root) {
  const f = d.flags;
  const ready = (d.references || []).length > 0;
  const sent = new Set(ready ? d.references.map((r) => r.file) : (d.predicted_refs || []));
  const imgs = h("div", { class: "imgs" }, d.images.map((im) => h("figure", {},
    h("img", { class: "illu", src: F(im.file), alt: im.label }),
    h("figcaption", {}, im.label, sent.size ? (sent.has(im.file) ? h("b", { text: ready ? " · 생성기에 보냄" : " · 생성기에 보낼 것", style: { color: "var(--gold)" } }) : " · 보내지 않음") : null))));
  const style = (d.references || []).find((r) => r.file.includes("style_nx07"));
  if (style) imgs.append(h("figure", {}, h("img", { class: "px", src: F(style.file), style: { height: "220px" }, alt: "style" }),
    h("figcaption", {}, "그리는 방식의 기준: 승인된 NX-07 마스터를 키운 것 ", h("b", { text: "· 생성기에 보냄", style: { color: "var(--gold)" } }))));
  put(root, lockedNote(d) || "",
    h("h2", { text: "쓸 그림" }),
    h("p", { class: "sub", text: d.images.some((i) => i.group === "view") ? "설정화 묶음의 그림이다. 측면 · 정면을 1단계 뽑기의 참조로 보낸다 (디자인과 몸의 비례만 가져가게)." : "올린 원화다. 측면 · 정면 · 그 밖 한 장씩을 1단계 뽑기의 참조로 보낸다." }),
    d.images.length ? imgs : h("div", { class: "err", text: "원화가 없다." }));
  if (f.handwritten || f.approved) {
    if (d.size) put(root, h("div", { class: "panel" },
      h("p", {}, "목표 키 ", h("b", { text: d.size.height_cells + "칸" }), " · 화면 " + (d.screen && d.screen.size ? d.screen.size.join("×") : "—"),
        " · 밝기 계획 " + (d.plans || []).map((p) => p.key + " " + p.label).join(" / ")),
      h("p", { class: "dim", text: "이미지 생성 " + d.gen.used + "회 썼다 (한도 " + d.gen.budget + "회)" })));
    return;
  }
  const fm = d.form;
  const locked = (d.plans || []).some((p) => p.s1);
  const T = h("input", { type: "number", min: 12, max: 96, value: fm.height_cells });
  const scr = h("select", {}, [[320, 180], [384, 216], [480, 270]].map((s) => h("option", { value: s.join("x"), text: s.join(" × ") + (s[0] === 320 ? " (NX-07 · 미리네와 같다)" : ""), selected: fm.screen && fm.screen.join("x") === s.join("x") })));
  const n = h("select", {}, [1, 2, 3].map((v) => h("option", { value: v, text: v + "개", selected: (fm.plans || 2) === v })));
  const bud = h("input", { type: "number", min: 0, max: 40, value: fm.budget });
  const heads = h("input", { type: "number", min: 2, max: 6, step: 0.1, value: fm.heads_guide });
  const notes = { keep: h("textarea", { value: (fm.notes || {}).keep || "", placeholder: "예: 이마에 올린 용접 고글, 노란 작업 점퍼" }),
    drop: h("textarea", { value: (fm.notes || {}).drop || "", placeholder: "예: 주머니의 작은 공구, 단추" }),
    main: h("textarea", { value: (fm.notes || {}).main || "", placeholder: "예: 노란 작업 점퍼 (비우면 옷이나 장갑의 가장 큰 부분을 모델이 고른다)" }) };
  const kinds = d.kinds || [];
  const planList = h("div", { class: "dim" });
  const drawPlans = () => fill(planList, "뽑을 밝기 계획: ", kinds.slice(0, +n.value).map((k, i) => h("span", {}, (i ? " / " : "") + k.label)));
  n.addEventListener("change", () => { drawPlans(); if (!bud.dataset.touched) bud.value = (+n.value) * 2 + 2; });
  bud.addEventListener("input", () => (bud.dataset.touched = "1"));
  drawPlans();
  const save = h("button", { class: "primary", text: d.flags.pipeline && (d.plans || []).length ? "설정 다시 저장" : "이 설정으로 준비", disabled: locked });
  save.addEventListener("click", async () => {
    save.disabled = true;
    try {
      await api("/char/" + d.id + "/prepare", { height_cells: +T.value, screen: scr.value.split("x").map(Number), plans: +n.value,
        budget: +bud.value, heads_guide: +heads.value, notes: { keep: notes.keep.value, drop: notes.drop.value, main: notes.main.value } });
      toast("준비했다. '픽셀 만들기'로 간다", true);
      location.hash = "#/c/" + d.id + "/make";
    } catch (e) { toast(e.message); save.disabled = false; }
  });
  const fset = (label, help, el) => h("div", {}, h("label", { class: "f", text: label }), el, help ? h("div", { class: "dim", text: help }) : null);
  put(root, 
    h("h2", { text: "만들 준비" }),
    locked ? h("div", { class: "note", text: "이미 1단계 그림을 뽑았다. 처음 설정은 바꿀 수 없다 (뽑은 그림과 기록이 어긋난다). 다른 메모 · 계획으로 더 뽑으려면 '리뷰' 아래의 '다시 뽑기'를 쓴다." }) : null,
    h("div", { class: "panel" },
      h("div", { class: "grid2" },
        h("div", {},
          fset("목표 키 (칸)", "제안: " + (fm.height_note || "") + ". 도트 한 칸 = 게임 화면의 1픽셀.", T),
          fset("화면 밀도 (게임 화면의 크기)", "비교 그림과 '어두운 게임 화면'에 쓴다.", scr),
          fset("밝기 계획의 변형 수", "변형마다 이미지 생성 2회 (1단계 1 + 2단계 1). 첫째는 승인된 두 캐릭터가 모두 고른 '어두운 몸 + 뒤 빛'.", n), planList,
          fset("이 캐릭터의 이미지 생성 한도 (회)", "fal.ai 는 부를 때마다 비용이 든다. 한도를 넘으면 뽑기가 멈춘다. 기본 = 변형 수 × 2 + 2 (다시 뽑기 여유).", bud),
          h("details", {}, h("summary", { text: "더 고칠 것 (보통은 그대로)" }),
            fset("밑그림의 머리 비율 (등신)", "밑그림에서 머리(정수리 ~ 목)를 키의 몇 분의 1로 깔지. 기본: 설정상 키가 150cm 아래면 3.0, 아니면 3.2.", heads))),
        h("div", {},
          h("p", { class: "sub", text: "캐릭터 메모 (선택, 한국어로 적어도 된다). 적은 글은 원문 그대로 프롬프트에 들어간다. 비워도 기본 문장으로 뽑는다: 그림에서 정체성을 읽어 큰 덩어리로 다시 설계하라는 지시." }),
          fset("꼭 지킬 것", "작은 크기에서도 읽혀야 하는 것. 작은 강조 획으로 들어간다.", notes.keep),
          fset("빼도 되는 것", "", notes.drop),
          fset("주인 덩어리", "몸의 대부분을 차지할 한 덩어리 (밝기 계획이 이 덩어리의 밝기를 정한다).", notes.main))),
      h("div", { class: "actions" }, save)));
  if ((d.plans || []).length) {
    put(root, h("h2", { text: "준비된 밝기 계획과 프롬프트" }),
      h("div", { class: "panel" }, d.plans.map((p) => h("details", {},
        h("summary", {}, p.key + " — " + p.label + (p.s1 ? " (뽑음)" : " (아직)")),
        h("p", { class: "dim", text: "근거: " + (p.why || "—") }),
        p.prompt ? h("pre", { class: "log", text: "불러오는 중…", "data-src": p.prompt }) : h("p", { class: "dim", text: "프롬프트 파일이 아직 없다" }))),
        h("p", { class: "dim", text: "기본 문장은 art/characters/_pipeline/studio_defaults.json 에 있다 (캐릭터에 묶이지 않음 · [제안])." })));
    root.querySelectorAll("details").forEach((det) => det.addEventListener("toggle", async () => {
      const pre = det.querySelector("pre[data-src]");
      if (det.open && pre && pre.textContent === "불러오는 중…") {
        try { pre.textContent = await (await fetch(F(pre.dataset.src))).text(); } catch (e) { pre.textContent = "읽지 못했다"; }
      }
    }));
  }
}

// 4. 픽셀 만들기
function tabMake(d, root) {
  const f = d.flags;
  put(root, lockedNote(d) || "");
  if (!d.flags.pipeline || !(d.plans || []).length) {
    put(root, h("div", { class: "note" }, "먼저 ", h("a", { href: "#/c/" + d.id + "/prepare", text: "만들 준비" }), "를 한다."));
    return;
  }
  const c = d.cost;
  const costBox = h("div", { class: "panel cost" });
  if (c) {
    const after = c.used + c.calls;
    put(costBox, 
      h("p", {}, "이번에 쓸 이미지 생성: ", h("b", { text: c.calls + "회" }), " (1단계 " + c.s1.length + " · 2단계 " + c.s2.length + ")" + (c.practice ? " — 연습 모드라 실제로는 부르지 않는다" : "")),
      h("p", {}, "이 캐릭터의 한도 ", h("b", { text: (c.budget ?? "없음") + "회" }), " · 지금까지 " + c.used + "회 · 끝나면 " + after + "회 · 남는 한도 " + (c.budget == null ? "—" : (c.budget - after) + "회")),
      c.calls === 0 ? h("p", { class: "dim", text: "새로 뽑을 그림이 없다. 밑그림 · 마스터 · 재기 · 비교 그림만 다시 한다 (생성 0회)." }) : null,
      c.budget != null && after > c.budget ? h("div", { class: "err" }, "한도를 넘는다. ", h("a", { href: "#/c/" + d.id + "/prepare", text: "만들 준비" }), " (또는 리뷰의 다시 뽑기)에서 한도를 올린다.") : null);
  }
  const running = d.job && d.job.state === "도는 중";
  const go = h("button", { class: "primary", text: running ? "도는 중…" : (d.job && d.job.state === "실패" ? "실패한 곳부터 다시 만들기" : "픽셀 만들기"),
    disabled: !f.editable || running || !!d.busy || (c && c.budget != null && c.used + c.calls > c.budget) });
  go.addEventListener("click", async () => {
    const ok = await ask({ title: "픽셀 만들기", ok: c.calls ? "생성 " + c.calls + "회 쓰고 만들기" : "만들기 (생성 0회)",
      body: h("div", {},
        h("p", {}, "이미지 생성(fal.ai)을 ", h("b", { text: c.calls + "회" }), " 쓴다: 1단계 " + (c.s1.join(", ") || "없음") + " · 2단계 " + (c.s2.join(", ") || "없음") + "."),
        h("p", { text: "한도 " + c.budget + "회 가운데 지금까지 " + c.used + "회 → 끝나면 " + (c.used + c.calls) + "회." }),
        c.practice ? h("p", { class: "note", text: "연습 모드: 실제로는 부르지 않고 미리네의 그림을 복사한다 (기록에는 '연습'으로 남는다)." }) : null,
        h("p", { class: "dim", text: "도는 동안 이 화면을 닫아도 된다. 검은 창(스튜디오)은 닫지 않는다." }),
        h("p", { class: "dim" }, "단계: " + d.planned_steps.join(" → "))) });
    if (!ok) return;
    try { await api("/char/" + d.id + "/run", { confirm_calls: c.calls }); S.bust = Date.now(); route(); }
    catch (e) { toast(e.message); }
  });
  put(root, costBox, h("div", { class: "actions" }, go, d.busy && !running ? h("span", { class: "dim", text: "다른 작업이 돌고 있다: " + d.busy.what }) : null));
  const box = h("div", {});
  put(root, box);
  const draw = (J) => {
    if (!J) { fill(box, h("h2", { text: "단계" }), h("ol", { class: "steplist" }, d.planned_steps.map((s) => h("li", {}, h("span", { class: "st", text: "기다림" }), s)))); return; }
    fill(box, 
      h("h2", {}, "지난 작업 — ", h("span", { class: "st " + (J.state === "도는 중" ? "run" : J.state), text: J.state }), h("span", { class: "dim", text: "  시작 " + (J.started || "") + (J.ended ? " · 끝 " + J.ended : "") + (J.practice ? " · 연습" : "") })),
      J.error ? h("div", { class: "err" }, h("b", { text: "실패한 곳: " + J.error.step }), h("br"), "까닭: " + J.error.reason, h("br"), h("span", { class: "dim", text: J.error.note || "" })) : null,
      J.state === "됨" ? h("div", { class: "ok" }, "다 됐다. ", h("a", { href: "#/c/" + d.id + "/review", text: "리뷰로 가서 후보를 본다" })) : null,
      h("ol", { class: "steplist" }, J.steps.map((s) => h("li", {}, h("span", { class: "st " + (s.state === "도는 중" ? "run" : s.state), text: s.state }), s.label))),
      h("details", { open: J.state !== "됨" }, h("summary", { text: "기록 (도구가 찍은 줄)" }), h("pre", { class: "log", text: (J.log || []).join("\n") })));
    const pre = box.querySelector("pre.log");
    if (pre) pre.scrollTop = pre.scrollHeight;
  };
  draw(d.job);
  if (running) {
    S.poll = setInterval(async () => {
      try {
        const r = await api("/char/" + d.id + "/job");
        draw(r.job);
        if (!r.job || r.job.state !== "도는 중") { clearInterval(S.poll); S.bust = Date.now(); setTimeout(route, 300); }
      } catch (e) { /* 다음에 */ }
    }, 1000);
  }
}

// 5. 리뷰
function measureBlock(m, targets) {
  if (!m) return h("p", { class: "dim", text: "아직 재지 않았다" });
  const f = m.format;
  const fmt = h("p", {}, h("span", { class: "chip " + (f.pass ? "pass" : "fail"), text: "형식 " + (f.pass ? "통과" : "실패") }),
    " 반투명 " + f.semi_transparent + " · 팔레트 이탈 " + f.off_palette + " · 격자 " + (f.grid_good == null ? "—" : Math.round(f.grid_good * 100) + "%") + " · " + f.colors + "색 · 외톨이 " + f.orphan_pct + "%");
  const rows = PK.map(([k, lab, u]) => {
    const v = m.picture[k];
    const refs = (m.distance[k] || []).map((x) => x.ref + " " + (x.value == null ? "—" : x.value) + (x.diff == null ? "" : " (" + (x.diff > 0 ? "+" : "") + x.diff + ")")).join(" · ");
    return h("tr", {}, h("td", { text: lab }), h("td", { class: "v", text: v == null ? "—" : v + u }), h("td", { class: "dim", text: refs }));
  });
  return h("div", {}, fmt,
    h("p", { class: "dim", text: "그림 쪽 숫자 — 통과 · 실패가 없다. 괄호는 참고 그림의 인물(" + Object.values(targets || {}).join(" · ") + ")과의 차이. 숫자가 참고에 닿아야 하는 것이 아니다 (NX-07 C36 은 36.9%였고 기획자가 골랐다)." }),
    h("table", { class: "t measure" }, h("tr", {}, h("th", { text: "그림" }), h("th", { text: "값" }), h("th", { text: "참고와의 거리" })), rows),
    h("p", { class: "dim", text: "키 " + m.picture.height + "칸 · 자동 측정 머리 " + m.picture.head + "칸 (" + m.picture.heads_tall + "등신 — 긴 머리 · 모자에서는 틀린다)" }));
}

function tabReview(d, root) {
  const jobs = (d.jobs || []).filter((j) => j.master);
  put(root, lockedNote(d) || "");
  if (!jobs.length) {
    put(root, h("div", { class: "note" }, "아직 후보가 없다. ", h("a", { href: "#/c/" + d.id + "/make", text: "픽셀 만들기" }), "를 먼저 한다."));
    return;
  }
  const maxH = Math.max(...jobs.map((j) => j.size[1]), ...d.others.map((o) => o.size[1]));
  if (!S.zoom) S.zoom = clamp(Math.floor(340 / maxH), 2, 16);
  const z = S.zoom;
  const ed = d.flags.editable;
  const zin = h("input", { type: "range", min: 2, max: 16, value: z });
  zin.addEventListener("input", () => { S.zoom = +zin.value; const b = $("#app > div:last-child"); b.replaceChildren(); tabReview(d, b); });
  put(root, h("div", { class: "row" }, h("h2", { text: "후보 — 모두 같은 배율" }), h("span", { class: "dim", text: "배율 ×" + z }), zin,
    d.compare ? h("a", { href: F(d.compare), target: "_blank", text: "파이프라인의 비교 그림 (compare.png) 열기" }) : null));
  const cards = jobs.map((j) => {
    const cls = "cand" + (j.decision === "고름" || j.decision === "승인" ? " picked" : "") + (j.decision === "채택하지 않음" ? " rejected" : "");
    const acts = [];
    if (ed && !j.pinned) {
      acts.push(h("button", { text: "칸 손보기", onclick: () => openPaint(j) }));
      if (j.decision !== "고름") acts.push(h("button", { class: "good", text: "이 후보로 고름", onclick: () => decide(d, j, "pick") }));
      if (j.decision === "고름") acts.push(h("button", { class: "primary", text: "픽셀 마스터로 승인", onclick: () => decide(d, j, "approve") }));
      if (!j.decision) acts.push(h("button", { class: "danger", text: "채택하지 않음", onclick: () => decide(d, j, "reject") }));
    }
    const dd = j.decision_detail;
    return h("div", { class: cls },
      h("h3", {}, j.key + " ", h("span", { class: "dim", text: j.plan_label + " · 키 " + j.height + "칸" })),
      j.decision ? h("div", { class: "badges" }, h("span", { class: "badge " + (j.decision === "채택하지 않음" ? "bad" : "ok"), text: j.decision }),
        dd && dd.quote ? h("span", { class: "dim", text: "\"" + dd.quote + "\" (" + (dd.date || "") + ")" }) : null) : null,
      h("div", { class: "stage", style: { height: maxH * z + 20 + "px" } }, pixImg(j.master, j.size[0], j.size[1], z)),
      h("p", { class: "dim", text: j.size[0] + "×" + j.size[1] + " · " + j.palette.length + "색 · 격자에 맞은 칸 " + (j.grid ? Math.round(j.grid.good * 100) + "%" : "—") + (j.fixes.length ? " · 손본 칸 " + j.fixes.length : "") }),
      measureBlock(j.measure, d.targets),
      h("details", {}, h("summary", { text: "1단계 그림 · 밑그림 · 2단계 그림 펼쳐 보기" }),
        h("div", { class: "imgs" },
          j.s1 ? h("figure", {}, h("img", { class: "px", src: F(j.s1), style: { height: "300px" } }), h("figcaption", { text: "1단계 (밑그림 없이 자유 설계)" })) : null,
          j.guide_cells ? h("figure", {}, h("img", { class: "px", src: F(j.guide_cells), style: { height: "300px" } }), h("figcaption", { text: "밑그림 (목표 칸 수)" })) : null,
          j.s2 ? h("figure", {}, h("img", { class: "px", src: F(j.s2), style: { height: "300px" } }), h("figcaption", { text: "2단계 (격자 그대로)" })) : null)),
      j.fixes.length ? h("details", {}, h("summary", { text: "손보기 전 그림과 손본 칸 " + j.fixes.length }),
        j.unfixed ? h("div", { class: "stage", style: { height: maxH * z + 20 + "px" } }, pixImg(j.unfixed, j.size[0], j.size[1], z)) : null,
        h("table", { class: "t" }, j.fixes.map((fx) => {
          const lg = (j.fix_log || []).find((l) => l.cell[0] === fx.cell[0] && l.cell[1] === fx.cell[1]) || {};
          return h("tr", {}, h("td", { text: "(" + fx.cell.join(", ") + ")" }), h("td", { text: (lg.before ? "#" + lg.before : "") + " → " + (lg.after ? (lg.after === "투명" ? "투명" : "#" + lg.after) : "") }),
            h("td", { text: fx.why }), h("td", { class: "dim", text: (fx.by || "") + " " + (fx.date || "") }),
            h("td", {}, ed && !j.pinned ? h("button", { text: "되돌리기", onclick: () => unfix(d, j, fx.cell) }) : null));
        }))) : null,
      acts.length ? h("div", { class: "actions" }, acts) : h("p", { class: "dim", text: ed ? "" : "보기만 (결정은 끝났다)" }));
  });
  put(root, h("div", { class: "cands" }, cards));

  // 승인된 캐릭터 옆에 — 같은 칸 크기
  put(root, h("h2", { text: "승인된 캐릭터 옆에 — 같은 칸 크기 (×" + z + ")" }),
    h("p", { class: "sub", text: "같은 게임의 그림으로 보이는가. 칸 하나의 크기가 같다 (발바닥을 맞췄다)." }),
    h("div", { class: "lineup" },
      d.others.map((o) => h("figure", {}, pixImg(o.file, o.size[0], o.size[1], z), h("figcaption", { text: o.label + " · 승인" }))),
      jobs.map((j) => h("figure", { class: "cand-f" }, pixImg(j.master, j.size[0], j.size[1], z), h("figcaption", { text: d.name + " " + j.key + (j.decision ? " · " + j.decision : "") })))));

  // 어두운 게임 화면
  const L = d.lineup;
  if (L) {
    const k = 3;
    const wrap = h("div", { class: "screenwrap" }, pixImg(L.file, L.screen[0], L.screen[1], k));
    for (const it of L.items) wrap.append(h("div", { class: "lbl", style: { left: (it.x + it.w / 2) * k + "px", top: (L.floor + 3) * k + "px" }, text: it.kind === "approved" ? it.label : it.label + (it.state ? " · " + it.state : "") }));
    put(root, h("h2", { text: "어두운 게임 화면 — " + L.screen.join("×") + " 실제 크기 ×" + k }),
      h("p", { class: "sub", text: "지금 게임의 배경을 화면 높이로 줄이고 누른 화면에, 실제 크기로 같은 발바닥 줄에 세웠다 (pixpipe lineup)." + (L.fits ? "" : " 화면에 다 들어가지 않는다.") }), wrap);
  } else put(root, h("p", { class: "dim", text: "어두운 게임 화면 그림이 아직 없다 (픽셀 만들기를 다시 돌리면 생긴다)." }));

  if (ed) put(root, redrawBox(d));
}

function redrawBox(d) {
  const nt = d.form.notes || {};
  const notes = { keep: h("textarea", { value: nt.keep || "" }), drop: h("textarea", { value: nt.drop || "" }), main: h("textarea", { value: nt.main || "" }) };
  const kinds = (d.kinds || []).map((k, i) => ({ k, box: h("input", { type: "checkbox", checked: i === 0 }) }));
  const bud = h("input", { type: "number", min: 0, max: 40, value: d.gen.budget });
  const cost = h("p", { class: "dim" });
  const upd = () => { const n = kinds.filter((x) => x.box.checked).length; cost.textContent = "더할 변형 " + n + "개 = 이미지 생성 " + n * 2 + "회. 한도 " + bud.value + "회 · 지금까지 " + d.gen.used + "회 · 끝나면 " + (d.gen.used + n * 2) + "회" + (d.gen.used + n * 2 > +bud.value ? " — 한도를 넘는다 (한도를 올린다)" : ""); };
  kinds.forEach((x) => x.box.addEventListener("change", upd)); bud.addEventListener("input", upd); upd();
  const go = h("button", { class: "primary", text: "변형 더하기 (설정 저장 → 픽셀 만들기로)" });
  go.addEventListener("click", async () => {
    const ks = kinds.filter((x) => x.box.checked).map((x) => x.k.kind);
    if (!ks.length) return toast("밝기 계획을 하나 이상 고른다");
    try {
      await api("/char/" + d.id + "/redraw", { kinds: ks, budget: +bud.value, notes: { keep: notes.keep.value, drop: notes.drop.value, main: notes.main.value } });
      toast("변형을 더했다. 생성 횟수를 확인하고 만든다", true);
      location.hash = "#/c/" + d.id + "/make";
    } catch (e) { toast(e.message); }
  });
  return h("div", {}, h("h2", { text: "다시 뽑기 — 메모를 고쳐 변형을 더한다" }),
    h("div", { class: "panel" },
      h("p", { class: "sub", text: "이미 뽑은 후보는 그대로 남는다. 새 변형은 새 이름(다음 글자)으로 더해진다. 메모는 새 변형에만 쓰인다." }),
      h("div", { class: "grid2" },
        h("div", {}, h("label", { class: "f", text: "밝기 계획 (더할 것)" }),
          kinds.map((x) => h("div", {}, h("label", {}, x.box, " " + x.k.label), h("div", { class: "dim", text: "근거: " + x.k.why }))),
          h("label", { class: "f", text: "이 캐릭터의 이미지 생성 한도 (회)" }), bud, cost),
        h("div", {}, h("label", { class: "f", text: "꼭 지킬 것" }), notes.keep, h("label", { class: "f", text: "빼도 되는 것" }), notes.drop,
          h("label", { class: "f", text: "주인 덩어리" }), notes.main)),
      h("div", { class: "actions" }, go)));
}

async function decide(d, j, action) {
  const T = { pick: ["이 후보로 고름", "good"], approve: ["픽셀 마스터로 승인", "primary"], reject: ["채택하지 않음", "danger"] }[action];
  const body = h("div", {},
    h("p", {}, h("b", { text: d.name + " · " + j.key }), " (" + j.plan_label + " · 키 " + j.height + "칸)"),
    action === "approve" ? h("div", { class: "note", text: "승인하면 이 후보가 " + d.id + "_px_base.png 로 복사되고 등록부에 승인으로 적힌다 (그때의 해시와 함께). 그 뒤로는 스튜디오에서 이 캐릭터의 후보를 손보거나 다시 뽑지 않는다 (승인된 그림을 지킨다). 규격 · 동작 만들기는 에이전트의 일이다." }) : null,
    action === "pick" ? h("p", { class: "dim", text: "고른 뒤 다른 후보들은 등록부에서 '채택하지 않음 — 기획자가 " + j.key + " 를 골랐다'로 바뀐다. 승인은 따로 한다." }) : null,
    h("p", { class: "dim", text: "기록: 누가 — 기획자 · 언제 — 오늘 · 무엇을 보고 — 스튜디오 리뷰 화면 (후보 그림 · 어두운 게임 화면 · 비교 그림) · 한 말 — 아래 칸. pixpipe " + action + " 이 명령줄과 같은 모양으로 적는다." }));
  const quote = await ask({ title: T[0], body, ok: T[0], okClass: T[1], text: true, placeholder: "예: 이게 제일 아버지 같다" });
  if (quote === null) return;
  try { await api("/char/" + d.id + "/decide", { action, job: j.key, quote }); S.bust = Date.now(); toast(T[0] + " — 기록했다", true); route(); }
  catch (e) { toast(e.message); }
}

async function unfix(d, j, cell) {
  const ok = await ask({ title: "칸 되돌리기", body: h("p", { text: j.key + " 의 (" + cell.join(", ") + ") 손보기를 되돌린다. 마스터를 다시 만든다." }), ok: "되돌리기" });
  if (!ok) return;
  try { await api("/char/" + d.id + "/unfix", { job: j.key, cell }); S.bust = Date.now(); toast("되돌렸다", true); route(); }
  catch (e) { toast(e.message); }
}

// 칸 손보기
function openPaint(j0) {
  let j = j0, sel = null, cell = null;
  const z = clamp(Math.floor(560 / Math.max(j.size[0], j.size[1])), 6, 24);
  const cv = h("canvas", { class: "px paintc", width: j.size[0] * z, height: j.size[1] * z });
  const one = h("canvas", { width: j.size[0], height: j.size[1] });
  const info = h("p", { class: "sub", text: "칸을 누른다." });
  const why = h("input", { type: "text", placeholder: "예: 귀 장치가 눈처럼 보인다", style: { width: "100%" } });
  const pal = h("div", { class: "palette" });
  const apply = h("button", { class: "primary", text: "이 칸 바꾸기", disabled: true });
  const fixes = h("div", {});
  let img = new Image();
  const fixedSet = () => new Set(j.fixes.map((f) => f.cell.join(",")));
  const colorAt = (x, y) => { const p = one.getContext("2d", { willReadFrequently: true }).getImageData(x, y, 1, 1).data; return p[3] === 0 ? "transparent" : "#" + [p[0], p[1], p[2]].map((v) => v.toString(16).padStart(2, "0")).join(""); };
  const draw = () => {
    const g = cv.getContext("2d");
    g.imageSmoothingEnabled = false;
    g.clearRect(0, 0, cv.width, cv.height);
    g.drawImage(img, 0, 0, cv.width, cv.height);
    g.strokeStyle = "rgba(255,255,255,0.07)";
    for (let x = 0; x <= j.size[0]; x++) { g.beginPath(); g.moveTo(x * z + .5, 0); g.lineTo(x * z + .5, cv.height); g.stroke(); }
    for (let y = 0; y <= j.size[1]; y++) { g.beginPath(); g.moveTo(0, y * z + .5); g.lineTo(cv.width, y * z + .5); g.stroke(); }
    g.fillStyle = "#f0c450";
    for (const k of fixedSet()) { const [x, y] = k.split(",").map(Number); g.fillRect(x * z + 1, y * z + 1, 4, 4); }
    if (cell) { g.strokeStyle = "#ffffff"; g.lineWidth = 2; g.strokeRect(cell[0] * z + 1, cell[1] * z + 1, z - 2, z - 2); g.lineWidth = 1; }
  };
  const load = () => {
    img = new Image();
    img.onload = () => { const g = one.getContext("2d", { willReadFrequently: true }); g.clearRect(0, 0, one.width, one.height); g.drawImage(img, 0, 0); draw(); };
    img.src = F(j.master);
  };
  const upd = () => {
    if (cell) {
      const cur = colorAt(cell[0], cell[1]);
      info.textContent = "칸 (" + cell.join(", ") + "): 지금 " + (cur === "transparent" ? "투명" : cur) + " → " + (sel ? (sel === "transparent" ? "투명" : sel) : "(색을 고른다)") + (fixedSet().has(cell.join(",")) ? " · 이미 손본 칸이다 (다시 바꾸면 기록이 바뀐다)" : "");
    }
    apply.disabled = !(cell && sel);
    pal.querySelectorAll("button").forEach((b) => b.classList.toggle("sel", b.dataset.c === sel));
  };
  const drawPal = () => fill(pal, 
    ...j.palette.map((p) => h("button", { title: p.hex + " · " + p.cells + "칸", style: { background: p.hex }, "data-c": p.hex, onclick: () => { sel = p.hex; upd(); } })),
    j.has_transparent ? h("button", { class: "clear", title: "투명 (칸을 지운다)", "data-c": "transparent", onclick: () => { sel = "transparent"; upd(); } }) : null);
  const drawFixes = () => fill(fixes, h("h3", { text: "손본 칸 " + j.fixes.length }),
    j.fixes.length ? h("table", { class: "t" }, j.fixes.map((fx) => h("tr", {}, h("td", { text: "(" + fx.cell.join(", ") + ")" }), h("td", { text: fx.why }), h("td", { class: "dim", text: fx.by || "" }),
      h("td", {}, h("button", { text: "되돌리기", onclick: async () => {
        try { await api("/char/" + S.id + "/unfix", { job: j.key, cell: fx.cell }); await refresh(); toast("되돌렸다", true); } catch (e) { toast(e.message); }
      } }))))) : h("p", { class: "dim", text: "없다" }));
  const refresh = async () => {
    S.bust = Date.now();
    const d = await loadDetail();
    j = d.jobs.find((x) => x.key === j.key);
    drawPal(); drawFixes(); load(); upd();
  };
  cv.addEventListener("click", (e) => {
    const r = cv.getBoundingClientRect();
    cell = [Math.floor((e.clientX - r.left) * (cv.width / r.width) / z), Math.floor((e.clientY - r.top) * (cv.height / r.height) / z)];
    upd(); draw();
  });
  apply.addEventListener("click", async () => {
    if (!why.value.trim()) return toast("고치는 이유를 적는다 (기록에 남는다)");
    apply.disabled = true;
    try { await api("/char/" + S.id + "/fix", { job: j.key, cell, color: sel, why: why.value }); await refresh(); toast("바꿨다. 마스터 · 재기 · 비교 그림을 다시 만들었다", true); }
    catch (e) { toast(e.message); upd(); }
  });
  openModal(h("div", {},
    h("h2", { text: "칸 손보기 — " + j.key }),
    h("p", { class: "sub", text: "칸을 누르고 이 그림의 팔레트 색(또는 투명)을 골라 바꾼다. 새 색은 만들지 않는다. 바꾼 칸은 이유와 함께 기록되고 (pipeline.json 의 fixes, pixpipe fix), 손보기 전 그림이 남는다. 되돌릴 수 있다." }),
    h("div", { class: "paint" }, cv,
      h("div", { style: { flex: 1, minWidth: "300px" } },
        h("label", { class: "f", text: "팔레트 (이 그림의 색)" }), pal, info,
        h("label", { class: "f", text: "이유 (꼭 적는다)" }), why,
        h("div", { class: "actions" }, apply, h("button", { text: "닫기", onclick: () => { closeModal(); S.bust = Date.now(); route(); } })),
        fixes))));
  drawPal(); drawFixes(); load(); upd();
}

// 6. 동작
function tabAnim(d, root) {
  put(root, h("div", { class: "note" }, h("b", { text: "동작 만들기(대기 · 달리기 · 걷기 …)는 아직 에이전트의 일이다." }),
    " 이 화면은 이미 만든 동작을 보고 평가를 적는 곳이다. 스튜디오는 동작을 새로 만들지 않는다."));
  const A = d.anim;
  if (!A || !A.anims.length) { put(root, h("p", { class: "sub", text: "이 캐릭터에는 아직 동작이 없다." })); return; }
  for (const a of A.anims) {
    put(root, h("h2", {}, a.label + " ", h("span", { class: "dim", text: a.name + (a.pass === true ? " · 검사 통과" : a.pass === false ? " · 검사 실패" : "") })),
      h("div", { class: "imgs" }, a.gifs.map((g) => h("figure", {}, h("img", { class: "px", src: F(g) }), h("figcaption", { text: g.split("/").pop() })))));
  }
  if (A.previews.length) put(root, h("h2", { text: "게임 화면 · 함께 세운 것" }),
    h("div", { class: "imgs" }, A.previews.map((g) => h("figure", {}, h("img", { class: "px", src: F(g), style: { maxWidth: "100%" } }), h("figcaption", { text: g.split("/").pop() })))));
  if (A.compare) put(root, h("details", {}, h("summary", { text: "동작의 비교 그림 (compare.png)" }), h("img", { src: F(A.compare), style: { maxWidth: "100%" } })));
  const rv = A.review;
  put(root, h("h2", { text: "평가" }),
    rv ? h("div", { class: "panel" }, h("b", { text: rv.verdict }), " (" + rv.date + ") \"" + rv.quote + "\"", h("div", { class: "dim", text: "평가는 승인이 아니다. 새로 적으면 기록이 하나 더 남는다." })) : h("p", { class: "dim", text: "아직 평가가 없다." }));
  const v = h("select", {}, ["받아들임", "고칠 것", "보류"].map((t) => h("option", { value: t, text: t })));
  const go = h("button", { class: "primary", text: "평가 적기" });
  go.addEventListener("click", async () => {
    const quote = await ask({ title: "동작 평가 — " + v.value, text: true, ok: "적기", body: h("p", { class: "dim", text: "pixpipe review 가 기록한다 (누가 기획자 · 오늘 · 본 것: 스튜디오 동작 화면 · 한 말)." }), placeholder: "예: 달리기의 윗몸이 굳어 보인다" });
    if (quote === null) return;
    try { await api("/char/" + d.id + "/review", { verdict: v.value, quote }); toast("평가를 적었다", true); route(); } catch (e) { toast(e.message); }
  });
  put(root, h("div", { class: "row" }, h("span", { text: "평가: " }), v, go));
}

// 기록
function tabRecords(d, root) {
  put(root, h("h2", { text: "기획자의 결정 · 평가 (등록부의 records, 새것부터)" }),
    d.records.length ? h("table", { class: "t" }, h("tr", {}, ["날짜", "누가", "종류", "무엇", "한 말"].map((t) => h("th", { text: t }))),
      d.records.map((r) => h("tr", {}, h("td", { text: r.date }), h("td", { text: r.by }), h("td", { text: r.kind }), h("td", { text: r.what }), h("td", { text: r.quote })))) : h("p", { class: "dim", text: "없다" }),
    h("h2", { text: "승인" }),
    d.approvals.length ? h("table", { class: "t" }, d.approvals.map((a) => h("tr", {}, h("td", { text: a.date }), h("td", { text: a.by }), h("td", { text: a.assets.join(", ") }), h("td", { text: a.quote || a.note || "" })))) : h("p", { class: "dim", text: "없다" }));
  if (d.gen) put(root, h("h2", { text: "이미지 생성 기록 (gen_log.json) — " + d.gen.used + "회 / 한도 " + d.gen.budget + "회" }),
    d.gen.log.length ? h("table", { class: "t" }, h("tr", {}, ["날짜", "단계", "이름", "종류", "나온 그림"].map((t) => h("th", { text: t }))),
      d.gen.log.map((e) => h("tr", {}, h("td", { text: e.date }), h("td", { text: e.step }), h("td", { text: e.name }), h("td", { text: e.dry_run ? "dry-run (부르지 않음)" : e.mock ? "연습 (복사)" : "fal.ai" }), h("td", { class: "dim", text: e.out || "" })))) : h("p", { class: "dim", text: "없다" }));
}

// ---------------------------------------------------------------- 시작
if (PRACTICE) $("#practice").hidden = false;
route();
busyTick();
setInterval(busyTick, 2500);
