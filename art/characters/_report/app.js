// 캐릭터 등록부 보고 화면 (기획서 9.11). file:// 에서 열리도록 fetch 와 ES 모듈을 쓰지 않는다.
// 자료: window.CHARPIPE (tools/charpipe.py report 가 _report/data.js 로 쓴다).
(function () {
  'use strict';
  var D = window.CHARPIPE;
  var app = document.getElementById('app');
  if (!D) return;
  var R = D.root; // index.html 에서 프로젝트 폴더까지

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function proj(f) { return R + encodeURI(f); } // 프로젝트 파일의 주소
  function pic(t) { return t.indexOf('_report/') === 0 ? t : proj(t); } // 미리보기(_report/…) 또는 프로젝트 파일
  function link(f, text) { return '<a href="' + proj(f) + '" target="_blank">' + esc(text || f) + '</a>'; }
  function badge(r) { return '<span class="badge r-' + esc(r) + '">' + esc(r) + '</span>'; }
  function mark(t) {
    if (!t) return '';
    var c = /미정/.test(t) ? 'undecided' : /제안/.test(t) ? 'proposal' : /확정/.test(t) ? 'fixed' : '';
    return '<span class="mark ' + c + '">' + esc(t) + '</span>';
  }
  var KIND = { player: '주인공 (플레이어)', companion: '동행', npc: '등장인물', enemy: '적' };
  var STATE_R = { '그대로': '통과', '바뀜': '주의', '없음': '실패', '기준 없음': '주의' };

  function byKey(c) { var m = {}; c.assets.forEach(function (a) { m[a.key] = a; }); return m; }
  function ofGroup(c, g) { return c.assets.filter(function (a) { return a.group === g; }); }
  function approvalText(c) {
    return c.approvals && c.approvals.length ? '승인 ' + c.approvals.length + '건 (마지막 ' + esc(c.approvals[c.approvals.length - 1].date) + ')' : '승인 기록 없음';
  }
  function idleFrame(c) {
    var s = c.assets.filter(function (a) { return a.group === 'sprite' && a.frame0; });
    return s.length ? s[0] : null;
  }
  // 도트 그림은 그려진 크기의 z배로 (가장자리를 흐리지 않는다)
  function pxImg(srcUrl, z, size, extra) {
    var st = size ? ' style="width:' + size[0] * z + 'px;height:' + size[1] * z + 'px"' : ' data-z="' + z + '"';
    return '<img class="px"' + st + ' src="' + srcUrl + '"' + (extra || '') + ' alt="">';
  }
  function fixPx(root) {
    root.querySelectorAll('img.px[data-z]').forEach(function (im) {
      function go() { im.style.width = im.naturalWidth * +im.dataset.z + 'px'; }
      if (im.complete && im.naturalWidth) go(); else im.addEventListener('load', go);
    });
  }

  // ------------------------------------------------------------ 목록
  function renderList() {
    var h = '<h1>캐릭터 목록</h1><p class="lead">카드를 누르면 그 캐릭터의 원화 · 픽셀 마스터 후보 · 게임 스프라이트 · 검사 결과 · 출처 · 기록이 나온다. ' +
      '그림을 누르면 원본 파일이 열린다.</p><div class="cards">';
    D.characters.forEach(function (c) {
      var A = byKey(c), side = A.side || A.front, f0 = idleFrame(c);
      h += '<a class="card" href="#' + esc(c.id) + '"><div class="pics">' +
        (side && side.thumb ? '<img class="art" src="' + pic(side.thumb) + '" alt="">' : '<div class="empty">원화 없음</div>') +
        (f0 ? '<div style="text-align:center">' + pxImg(pic(f0.frame0), 2) + '<div class="note">게임 (2배)</div></div>' : '') +
        '</div><div class="body"><div class="name">' + esc(c.name) + ' <span class="note">' + esc(c.id) + '</span></div><dl>' +
        '<dt>구분</dt><dd>' + esc(KIND[c.kind] || c.kind) + '</dd>' +
        '<dt>디자인</dt><dd>' + esc(c.design.current) + ' ' + mark(c.design.status) + '</dd>' +
        '<dt>설정 키</dt><dd>' + (c.story.height_cm ? esc(c.story.height_cm) + 'cm ' + mark(c.story.height_mark) : '—') + '</dd>' +
        '<dt>원화 검사</dt><dd>' + badge(c.check.result) + '</dd>' +
        '<dt>승인</dt><dd>' + approvalText(c) + '</dd>' +
        '<dt>파일</dt><dd>' + c.assets.length + '개 등록' + changedNote(c) + '</dd>' +
        '</dl></div></a>';
    });
    h += '</div>';
    h += '<section class="box"><h2>이 화면에 대해</h2><ul class="note">' +
      '<li>등록부는 캐릭터마다 JSON 한 개다: <code>art/characters/&lt;id&gt;/character.json</code>. 파일은 옮기지 않고 경로로 가리킨다.</li>' +
      '<li>파일마다 등록할 때의 내용 해시를 적어 두었다. 그 뒤에 파일이 바뀌면 "바뀜"으로 보인다.</li>' +
      '<li>승인은 기획자가 대화에서 말하면 에이전트가 적는다. 화면에서 승인할 수는 없다 (file:// 은 파일을 쓸 수 없다).</li>' +
      '<li>다시 만들기: <code>python tools/charpipe.py build</code> · 기준: 기획서 9.11</li></ul></section>';
    app.innerHTML = h;
    fixPx(app);
  }
  function changedNote(c) {
    var n = c.assets.filter(function (a) { return a.now.state !== '그대로'; }).length;
    return n ? ' · <b style="color:var(--warn)">' + n + '개 바뀜/없음</b>' : '';
  }

  // ------------------------------------------------------------ 캐릭터
  function renderChar(c) {
    var A = byKey(c);
    var sec = [];
    sec.push(['summary', '요약', summary(c)]);
    sec.push(['views', '정면 · 측면 · 후면', views(c, A)]);
    sec.push(['sheets', '나머지 원화', sheets(c)]);
    if (ofGroup(c, 'pixel_master').length) sec.push(['pm', '픽셀 마스터 후보 (실험)', pixelMasters(c)]);
    sec.push(['sprites', '게임의 스프라이트', sprites(c)]);
    sec.push(['design', '디자인 시안', designs(c)]);
    sec.push(['check', '검사 결과', checks(c)]);
    sec.push(['source', '출처', sources(c)]);
    sec.push(['files', '파일과 판', files(c)]);
    sec.push(['history', '승인 · 기록', history(c)]);
    var h = '<p><a href="#">← 캐릭터 목록</a></p><h1>' + esc(c.name) + ' <span class="note">' + esc(c.id) + '</span> ' + badge(c.check.result) + '</h1>' +
      '<div class="toc">' + sec.map(function (s) { return '<a href="javascript:void(0)" data-go="' + s[0] + '">' + s[1] + '</a>'; }).join('') + '</div>';
    sec.forEach(function (s) { h += '<section class="box" id="s-' + s[0] + '"><h2>' + s[1] + '</h2>' + s[2] + '</section>'; });
    app.innerHTML = h;
    app.querySelectorAll('[data-go]').forEach(function (a) {
      a.addEventListener('click', function () { document.getElementById('s-' + a.dataset.go).scrollIntoView({ behavior: 'smooth' }); });
    });
    fixPx(app);
    window.scrollTo(0, 0);
  }

  function summary(c) {
    var g = c.game;
    return '<div class="kv">' +
      '<div>구분</div><div>' + esc(KIND[c.kind] || c.kind) + '</div>' +
      '<div>디자인</div><div>' + esc(c.design.current) + ' ' + mark(c.design.status) + '<div class="note">' + esc(c.design.note) + ' (' + esc(c.design.doc) + ')</div></div>' +
      '<div>설정</div><div>' + (c.story.height_cm ? '키 ' + esc(c.story.height_cm) + 'cm ' + mark(c.story.height_mark) : '') + (c.story.body ? ' · ' + esc(c.story.body) : '') +
      '<div class="note">' + esc(c.story.note || '') + ' (' + esc(c.story.doc) + ')</div></div>' +
      '<div>게임</div><div>' + (g ? esc(g.style) + (g.height_px ? ' · 키 ' + g.height_px + 'px' : '') + '<div class="note">' + esc(g.note || '') + '</div>' : '게임 스프라이트 없음') + '</div>' +
      '<div>원화 검사</div><div>' + badge(c.check.result) + ' <span class="note">' + esc(c.check.date) + '</span></div>' +
      '<div>승인</div><div>' + approvalText(c) + '</div>' +
      (c.links && c.links.length ? '<div>함께 볼 것</div><div>' + c.links.map(function (l) { return link(l.file, l.label); }).join(' · ') + '</div>' : '') +
      '</div>';
  }

  function views(c, A) {
    var vs = ['front', 'side', 'back'].map(function (k) { return A[k]; }).filter(function (a) { return a && a.now.exists; });
    if (!vs.length) return '<div class="empty">정면 · 측면 · 후면 원화가 없다</div>';
    var VH = 600, H = vs[0].now.size[1], k = VH / H, m0 = vs[0].now.measure;
    var h = '<p class="lead">세 장을 <b>같은 배율</b>로 나란히 놓았다. 빨간 줄 = 정면 그림의 발바닥, 파란 점선 = 정면 그림의 정수리. ' +
      '왼쪽 눈금은 설정 키(' + (c.story.height_cm ? esc(c.story.height_cm) + 'cm' : '없음') + ')를 정면 그림의 키에 맞춘 것이다.</p>';
    h += '<div class="views-wrap"><div class="stage" style="--vh:' + VH + 'px;height:' + (VH + 28) + 'px">';
    vs.forEach(function (a) {
      h += '<figure><a href="' + proj(a.file) + '" target="_blank"><img src="' + pic(a.thumb) + '" alt=""></a><figcaption>' + esc(a.label) + '</figcaption></figure>';
    });
    if (m0 && m0.height) {
      h += '<div class="hline hl-top" style="top:' + (m0.top * k).toFixed(1) + 'px"><span>정수리 (정면)</span></div>';
      h += '<div class="hline hl-sole" style="top:' + (m0.sole * k).toFixed(1) + 'px"><span>발바닥 (정면)</span></div>';
      var cm = c.story.height_cm;
      if (cm) {
        var per = (m0.height * k) / cm;
        h += '<div class="ruler" style="top:' + (m0.top * k).toFixed(1) + 'px;height:' + (m0.height * k).toFixed(1) + 'px">';
        for (var v = 0; v <= cm; v += 10) {
          var big = v % 50 === 0;
          h += '<div class="tick' + (big ? ' big' : '') + '" style="top:' + ((cm - v) * per).toFixed(1) + 'px">' + (big ? '<span>' + v + 'cm</span>' : '') + '</div>';
        }
        h += '<div class="tick big" style="top:0"><span>' + cm + 'cm</span></div></div>';
      }
    }
    h += '</div></div>';
    h += '<table style="margin-top:10px"><tr><th>그림</th><th>캔버스</th><th>캐릭터 키 (px)</th><th>정수리 줄</th><th>발바닥 줄</th><th>캔버스 끝까지 여백</th><th>원본</th></tr>';
    vs.forEach(function (a) {
      var m = a.now.measure || {};
      h += '<tr><td>' + esc(a.label) + '</td><td>' + a.now.size.join(' × ') + '</td><td class="num">' + esc(m.height) + '</td><td class="num">' + esc(m.top) +
        '</td><td class="num">' + esc(m.sole) + '</td><td class="num">' + esc(m.margin) + '</td><td>' + link(a.file, '열기') + '</td></tr>';
    });
    return h + '</table><p class="note">키와 발바닥 줄은 흰 배경에서 그림이 있는 줄을 잰 값이다 (원화의 px).</p>';
  }

  function tile(a, extra) {
    if (!a.now.exists) return '<div class="tile"><div class="empty">없음: ' + esc(a.file) + '</div></div>';
    return '<div class="tile"><a href="' + proj(a.file) + '" target="_blank"><img src="' + pic(a.thumb) + '" alt=""></a><div class="cap"><b>' +
      esc(a.label) + '</b>' + (extra || '') + '<span class="note">' + esc(a.file) + ' · ' + (a.now.size ? a.now.size.join('×') : '') + '</span></div></div>';
  }

  function sheets(c) {
    var main = ofGroup(c, 'sheet'), src = ofGroup(c, 'source');
    var h = '<div class="grid">' + main.map(function (a) { return tile(a); }).join('') + '</div>';
    if (src.length) {
      h += '<details style="margin-top:12px"><summary>원화의 재료 ' + src.length + '장 (나누기 전 · 손보기 전)</summary><div class="grid" style="margin-top:10px">' +
        src.map(function (a) { return tile(a); }).join('') + '</div></details>';
    }
    return h;
  }

  function pixelMasters(c) {
    var pms = ofGroup(c, 'pixel_master'), f0 = idleFrame(c), Z = 4;
    var h = '<p class="lead"><span class="mark undecided">실험</span> 기획서 9.11의 실험 결과다. 어느 것도 기준으로 정하지 않았다. 캐릭터 크기와 등신은 <span class="mark undecided">[미정]</span>. ' +
      '모두 같은 배율(' + Z + '배)이고 발바닥을 한 줄에 맞췄다.</p>';
    h += '<div class="pmrow">';
    if (f0) h += '<div class="pm c">' + pxImg(pic(f0.frame0), Z) + '<div class="lab">C · 지금 게임의 도트<br>(대기 첫 프레임)</div></div>';
    pms.forEach(function (a) {
      if (!a.now.exists) return;
      h += '<div class="pm"><a href="' + proj(a.also && a.also.x8 ? a.also.x8 : a.file) + '" target="_blank">' + pxImg(pic(a.thumb), Z, a.now.size) + '</a><div class="lab">' + esc(a.label) + '</div></div>';
    });
    h += '</div>';
    h += '<table class="pmtable" style="margin-top:10px"><tr><th>후보</th><th>마스터 (칸)</th><th>키</th><th>머리</th><th>등신</th><th>칸 너비 들쭉날쭉</th><th>원본과의 오차</th><th>외톨이 픽셀</th><th>고른 칸 / 도구의 추천</th><th>파일</th></tr>';
    pms.forEach(function (a) {
      var m = a.now.metrics || {};
      var even = m.spread != null && m.spread <= 0.3;
      h += '<tr><td>' + esc(a.label) + '</td><td>' + (m.size ? m.size.join(' × ') : '') + '</td><td class="num">' + esc(m.height) + '</td><td class="num">' + esc(m.head) +
        '</td><td class="num">' + esc(m.heads_tall) + '</td><td class="num">' + esc(m.spread) + (even ? ' <span class="badge r-통과">고른 격자</span>' : '') +
        '</td><td class="num">' + esc(m.err) + '</td><td class="num">' + esc(m.orphan_pct) + '%</td><td>' + esc(m.picked) + ' / ' + esc(m.recommended) +
        '</td><td>' + link(a.file, '마스터') + (a.also && a.also.candidates ? ' · ' + link(a.also.candidates, '후보 비교') : '') + '</td></tr>';
    });
    if (f0) h += '<tr><td>C · 지금 게임</td><td>52 × 83</td><td class="num">83</td><td class="num">20</td><td class="num">4.2</td><td>—</td><td>—</td><td>—</td><td>—</td><td>' + link(f0.file, '시트') + '</td></tr>';
    h += '</table><p class="note">칸 너비 들쭉날쭉이 0.3 안쪽이면 그림이 고른 격자에 그려진 것이다. 머리는 도구가 자동으로 잰 값이다. C의 값은 기획서 9.11의 표에서 옮겼다.</p>';
    var raws = pms.filter(function (a) { return a.raw_thumb; });
    if (raws.length) {
      h += '<h3>재료: 도트풍으로 그려진 그림</h3><div class="grid">' + raws.map(function (a) {
        return '<div class="tile"><a href="' + proj(a.source.from) + '" target="_blank"><img src="' + pic(a.raw_thumb) + '" alt="" style="max-height:360px;width:auto;margin:auto"></a><div class="cap"><b>' +
          esc(a.label) + '</b><span class="note">' + esc(a.source.from) + '</span></div></div>';
      }).join('') + '</div>';
    }
    var recs = (c.records || []);
    if (recs.length) h += '<h3>기록된 평가</h3><ul>' + recs.map(function (r) { return '<li>' + esc(r.date) + ' ' + esc(r.by) + ': ' + esc(r.what) + ' <span class="note">— "' + esc(r.quote) + '" (' + esc(r.doc) + '). ' + esc(r.note) + '</span></li>'; }).join('') + '</ul>';
    return h;
  }

  function sprites(c) {
    var sp = ofGroup(c, 'sprite');
    if (!sp.length) return '<div class="empty">게임에 쓰이는 스프라이트가 없다</div>';
    var Z = sp.length > 6 ? 2 : 3;
    var h = '<p class="lead">' + Z + '배로 키워 제 속도(1틱 = 1/60초)로 돌린다. 끝나는 동작도 되풀이해서 보여 준다.</p><div class="sprites">';
    sp.forEach(function (a) {
      if (!a.now.exists) { h += '<div class="spr">없음: ' + esc(a.file) + '</div>'; return; }
      var an = a.anim;
      if (an && an.frames > 1) {
        var w = an.cell[0] * Z, hh = an.cell[1] * Z, sw = a.now.size[0] * Z, dur = (an.frames * (an.ticks || 8) / 60).toFixed(2);
        h += '<div class="spr"><a href="' + proj(a.file) + '" target="_blank"><div class="anim" style="width:' + w + 'px;height:' + hh + 'px;background-image:url(\'' + pic(a.thumb) +
          '\');background-size:' + sw + 'px ' + hh + 'px;--end:-' + sw + 'px;animation:play ' + dur + 's steps(' + an.frames + ') infinite"></div></a>' +
          esc(a.label) + '<br><span style="color:#aab">' + an.frames + '프레임 × ' + esc(an.ticks || '—') + '틱</span></div>';
      } else {
        var cell = an ? an.cell : a.now.size;
        h += '<div class="spr"><a href="' + proj(a.file) + '" target="_blank"><div class="anim" style="width:' + cell[0] * Z + 'px;height:' + cell[1] * Z + 'px;background-image:url(\'' + pic(a.thumb) +
          '\');background-size:' + a.now.size[0] * Z + 'px ' + a.now.size[1] * Z + 'px"></div></a>' + esc(a.label) + '</div>';
      }
    });
    return h + '</div>';
  }

  function designs(c) {
    var d = ofGroup(c, 'design'), ref = ofGroup(c, 'design_ref'), only = ofGroup(c, 'reference_only');
    var h = '<p class="lead">지금: ' + esc(c.design.current) + ' ' + mark(c.design.status) + ' — ' + esc(c.design.note) + '</p><div class="grid">' +
      d.map(function (a) { return tile(a); }).join('') +
      ref.map(function (a) { return tile(a, '<span class="mark">원본 설정화 · reference/</span> '); }).join('') + '</div>';
    if (only.length) {
      h += '<h3>참조만 <span class="mark ref">기획자 원본 · 고치지 않는다</span></h3><div class="grid">' +
        only.map(function (a) { return tile(a, '<span class="mark ref">참조만</span> '); }).join('') + '</div>';
    }
    return h;
  }

  function checks(c) {
    var h = '<table><tr><th style="width:70px">결과</th><th style="width:240px">검사</th><th>내용</th><th style="width:90px">대상</th></tr>';
    c.check.items.forEach(function (i) {
      h += '<tr><td>' + badge(i.result) + '</td><td>' + esc(i.name) + '</td><td>' + esc(i.detail) + '</td><td class="note">' + esc(i.what) + '</td></tr>';
    });
    var t = c.check.thresholds;
    return h + '</table><p class="note">문턱 <span class="mark proposal">[제안]</span>: 키 · 발바닥 줄의 차이 ' + t.height_pass * 100 + '% 안 통과, ' + t.height_warn * 100 +
      '% 안 주의 · 배경 흰색 ' + t.white_pass * 100 + '% 넘게 통과 · 잘림 여백 ' + t.margin_min + 'px. 검사한 날 ' + esc(c.check.date) + '.</p>';
  }

  function list(arr) { return (arr || []).map(function (f) { return link(f); }).join('<br>'); }
  function sources(c) {
    var rows = c.assets.filter(function (a) { return a.source && a.group !== 'sprite'; });
    var h = '<table><tr><th>그림</th><th>만든 방법</th><th>재료 · 프롬프트</th><th>참조 그림</th><th>모델 · 문서</th></tr>';
    rows.forEach(function (a) {
      var s = a.source;
      h += '<tr><td>' + esc(a.label) + '<div class="note">' + esc(D.groups[a.group] || a.group) + '</div></td><td>' + esc(s.made_by || '') + (s.tool ? '<div class="note">' + esc(s.tool) + '</div>' : '') +
        (s.cleaned ? '<div class="note">손본 것: ' + s.cleaned.map(function (o) { return esc(o.op + ' — ' + o.why); }).join('; ') + '</div>' : '') + '</td><td>' +
        (s.from ? '재료: ' + link(s.from) + '<br>' : '') + list(s.prompts) + (s.note ? '<div class="note">' + esc(s.note) + '</div>' : '') + '</td><td>' + list(s.refs) +
        (s.style_anchor ? '<br>화풍 기준: ' + link(s.style_anchor) : '') + (s.refs_note ? '<div class="note">' + esc(s.refs_note) + '</div>' : '') + '</td><td>' + esc(s.model || '') +
        '<div class="note">' + esc(s.doc || '') + '</div></td></tr>';
    });
    var spr = ofGroup(c, 'sprite');
    if (spr.length) {
      var tables = {};
      spr.forEach(function (a) { var t = (a.source && (a.source.table || a.source.made_by)) || ''; tables[t] = (tables[t] || 0) + 1; });
      h += '<tr><td>게임의 스프라이트 ' + spr.length + '장</td><td colspan="4">' + Object.keys(tables).map(function (t) { return esc(t) + ' (' + tables[t] + '장)'; }).join('<br>') +
        '<div class="note">상태별 시트는 state_sheets.py 가 원본 시트에서 만든다 (기획서 9.9). 원본과 프롬프트는 그 표(layout.json)에 있다.</div></td></tr>';
    }
    return h + '</table>';
  }

  function files(c) {
    var h = '<p class="lead">등록할 때 적은 내용 해시(sha256 앞 12자)와 지금의 해시를 견준다. 같으면 "그대로", 다르면 "바뀜". 바뀐 파일은 기획자가 확인한 뒤 새 판으로 받아들인다.</p>' +
      '<table class="files"><tr><th>구분</th><th>이름</th><th>파일</th><th>판</th><th>등록</th><th>해시</th><th>지금</th></tr>';
    c.assets.forEach(function (a) {
      var b = a.base || {}, n = a.now;
      h += '<tr><td class="note">' + esc(D.groups[a.group] || a.group) + '</td><td>' + esc(a.label) + '</td><td class="path">' + link(a.file) + '</td><td class="num">' + esc(b.version || '—') +
        '</td><td>' + esc(b.date || '—') + '</td><td class="hash">' + esc((b.sha256 || '').slice(0, 12)) + (n.state === '바뀜' ? '<br>→ ' + esc((n.sha256 || '').slice(0, 12)) : '') +
        '</td><td>' + badge(STATE_R[n.state] || '정보').replace('>' + (STATE_R[n.state] || '정보') + '<', '>' + esc(n.state) + '<') + '</td></tr>';
    });
    return h + '</table>';
  }

  function history(c) {
    var h = '<h3>승인</h3>';
    if (c.approvals && c.approvals.length) {
      h += '<table><tr><th>날짜</th><th>누가</th><th>무엇을</th><th>메모</th></tr>' + c.approvals.map(function (a) {
        return '<tr><td>' + esc(a.date) + '</td><td>' + esc(a.by) + '</td><td>' + Object.keys(a.assets).map(function (k) { return esc(k) + ' <span class="hash">' + esc(a.assets[k].slice(0, 12)) + '</span>'; }).join('<br>') +
          '</td><td>' + esc(a.note) + '</td></tr>';
      }).join('') + '</table>';
    } else {
      h += '<div class="empty">승인 기록 없음. 기획자가 대화에서 "' + esc(c.name) + ' 정면 · 측면 · 후면 승인"처럼 말하면, 에이전트가 누가 · 언제 · 어느 파일을 · 그때의 해시로 승인했는지 적는다.</div>';
    }
    if (c.records && c.records.length) {
      h += '<h3>문서에 남은 평가 (승인이 아니다)</h3><ul>' + c.records.map(function (r) { return '<li>' + esc(r.date) + ' ' + esc(r.by) + ' — ' + esc(r.what) + ' <span class="note">(' + esc(r.doc) + ')</span></li>'; }).join('') + '</ul>';
    }
    h += '<h3>등록과 판의 기록</h3><table><tr><th style="width:100px">날짜</th><th style="width:150px">무엇</th><th style="width:70px">누가</th><th>내용</th></tr>';
    c.history.forEach(function (e) {
      var rest = Object.keys(e).filter(function (k) { return ['date', 'what', 'by'].indexOf(k) < 0 && e[k] !== '' && e[k] != null; })
        .map(function (k) { return esc(k) + ': ' + esc(Array.isArray(e[k]) ? e[k].join(', ') : e[k]); }).join(' · ');
      h += '<tr><td>' + esc(e.date) + '</td><td>' + esc(e.what) + '</td><td>' + esc(e.by) + '</td><td class="note">' + rest + '</td></tr>';
    });
    return h + '</table>';
  }

  function route() {
    var id = decodeURIComponent(location.hash.replace(/^#/, ''));
    var c = D.characters.filter(function (x) { return x.id === id; })[0];
    if (c) { document.title = c.name + ' — 캐릭터 등록부'; renderChar(c); }
    else { document.title = '캐릭터 등록부'; renderList(); }
  }
  document.getElementById('gen').textContent = '자료를 만든 날 ' + D.generated + ' · 캐릭터 ' + D.characters.length + '명';
  window.addEventListener('hashchange', route);
  route();
})();
