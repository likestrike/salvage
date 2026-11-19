/* SALVAGE 전투 프로토타입 — 실행 루프, 조작, 소리, 안내 글자 */
(function () {
  'use strict';
  var S = window.SALVAGE, sim = S.sim, R = S.render, C = sim.C;
  var canvas = document.getElementById('screen'), ctx = canvas.getContext('2d');
  var elMedia = document.getElementById('media'), elCombo = document.getElementById('combo');
  var elMsg = document.getElementById('message'), elMsgText = elMsg.querySelector('span');

  var game = sim.createGame();
  var keys = {}, paused = false, muted = false, msgT = 0;

  // 색상 바리에이션 (art/concept/nx07_color_variations.png 의 A~F)
  var SKINS = [
    { id: 'a', name: 'A 올리브 드랩' }, { id: 'b', name: 'B 화이트 오렌지' }, { id: 'c', name: 'C 코발트 블루' },
    { id: 'd', name: 'D 크림슨 레드' }, { id: 'e', name: 'E 차콜 블랙' }, { id: 'f', name: 'F 인더스트리얼 옐로' },
  ];
  // 화면은 스타일 3 으로 고정이다 (2026-11-18). NX-07 과 적은 상태별 시트(assets/style_c/states/)로 그린다.
  // 표(프레임 수 · 프레임 시간 · 칸 크기)는 states.js 에 있다 (tools/state_sheets.py 가 만든다).
  var STYLES = [
    { id: 'c', name: '스타일 3', states: 'states/', dir: 'assets/style_c/', bg: 'bg.png', bgDim: 0.4 },
  ];
  // 플레이어의 캐릭터 시트. V 로 바꾼다. 그림만 바뀌고 조작과 전투 규칙은 같다. 적과 배경은 스타일 3 그대로다.
  // NOVA 시안 = 기획자가 넣은 NX-07 새 디자인의 스트립 (art/concept/nova/, 기획서 9.10). 표는 assets/nova/states/states.js 에 있다.
  var LOOKS = [
    { id: 'c', name: 'NX-07 · 스타일 3', skins: true },
    { id: 'nova', name: 'NOVA 시안', dir: 'assets/nova/states/' },
  ];
  var query = new URLSearchParams(location.search);
  var lookIdx = Math.max(0, LOOKS.map(function (k) { return k.id; }).indexOf(query.get('look') || 'c'));
  var skinIdx = Math.max(0, SKINS.map(function (k) { return k.id; }).indexOf(query.get('skin') || 'a'));
  var styleIdx = 0;
  var elSkin = document.getElementById('skin');
  var MEDIA_LABEL = { locman: '<b>LOCMAN</b> 게임팩 — 기본 공격 3타 · 차지샷', movie: '<b>무술 영화</b> — 너클 펀치' };

  // ───────────── 화면 크기 ─────────────
  function fit() {
    var s = Math.max(1, Math.floor(Math.min(window.innerWidth / C.VIEW_W, (window.innerHeight - 40) / C.VIEW_H)));
    document.documentElement.style.setProperty('--s', s);
  }
  window.addEventListener('resize', fit); fit();

  // ───────────── 소리 (WebAudio 로 합성) ─────────────
  var ac = null, noiseBuf = null;
  function audio() {
    if (ac || muted) return ac;
    try {
      ac = new (window.AudioContext || window.webkitAudioContext)();
      noiseBuf = ac.createBuffer(1, ac.sampleRate * 0.5, ac.sampleRate);
      var d = noiseBuf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    } catch (e) { ac = null; }
    return ac;
  }
  function tone(type, f0, f1, dur, vol, delay) {
    if (!ac || muted) return;
    var t = ac.currentTime + (delay || 0), o = ac.createOscillator(), g = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(ac.destination); o.start(t); o.stop(t + dur + 0.02);
  }
  function noise(dur, vol, delay) {
    if (!ac || muted) return;
    var t = ac.currentTime + (delay || 0), n = ac.createBufferSource(), g = ac.createGain();
    n.buffer = noiseBuf; g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    n.connect(g); g.connect(ac.destination); n.start(t); n.stop(t + dur + 0.02);
  }
  var SFX = {
    shot: function () { tone('square', 980, 420, 0.07, 0.05); },
    charge_mid: function () { tone('sine', 520, 700, 0.1, 0.05); },
    charge_full: function () { tone('sine', 760, 1100, 0.14, 0.06); },
    charge_shot: function () { tone('sawtooth', 520, 70, 0.3, 0.09); noise(0.18, 0.06); },
    jump: function () { tone('square', 300, 520, 0.08, 0.03); },
    punch_start: function () { tone('triangle', 240, 120, 0.12, 0.06); },
    punch_hit: function () { noise(0.45, 0.28); tone('sine', 150, 30, 0.55, 0.34); tone('square', 520, 50, 0.2, 0.09); },   // 기폭
    whiff: function () { noise(0.07, 0.04); },
    enemy_hit: function () { tone('square', 320, 200, 0.05, 0.05); },
    enemy_down: function () { tone('sawtooth', 260, 50, 0.3, 0.07); },
    enemy_shot: function () { tone('square', 520, 300, 0.08, 0.03); },
    explode: function () { noise(0.4, 0.2); tone('sine', 110, 30, 0.4, 0.2); },
    hurt: function () { tone('sawtooth', 220, 90, 0.2, 0.09); },
    pickup: function () { tone('square', 660, 660, 0.07, 0.05); tone('square', 990, 990, 0.1, 0.05, 0.08); },
    learned: function () { [523, 659, 784, 1047].forEach(function (f, i) { tone('square', f, f, 0.1, 0.05, i * 0.09); }); },
    arm: function () { tone('square', 180, 90, 0.06, 0.06); noise(0.05, 0.05, 0.05); tone('sawtooth', 120, 300, 0.14, 0.04, 0.08); },   // 기믹 전개
    steam: function () { noise(0.35, 0.05); },
    burst: function () { tone('sawtooth', 700, 120, 0.16, 0.08); noise(0.1, 0.05); },                       // 마무리탄
    heavy_hit: function () { tone('square', 240, 90, 0.12, 0.09); noise(0.08, 0.07); },                     // 넉백
    chase: function () { noise(0.3, 0.2); tone('sine', 220, 40, 0.4, 0.26); tone('square', 880, 220, 0.14, 0.07); },   // 추격 · 공중 추격
    land: function () { tone('sine', 90, 40, 0.18, 0.16); noise(0.12, 0.08); },                             // 띄운 적이 떨어진다
  };

  // ───────────── 조작 ─────────────
  var MAP = {
    ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right',
    KeyZ: 'jump', Space: 'jump', ArrowUp: 'jump', KeyW: 'jump',
    KeyX: 'attack', KeyJ: 'attack', KeyK: 'attack',
  };
  window.addEventListener('keydown', function (e) {
    audio();
    if (MAP[e.code]) { keys[MAP[e.code]] = true; e.preventDefault(); return; }
    if (e.repeat) return;
    var p = game.player;
    if (e.code === 'KeyR') { game = sim.createGame(); msgT = 0; }
    else if (e.code === 'Digit1') { p.melee = !p.melee; showMessage(p.melee ? '너클 펀치 켬 (테스트)' : '너클 펀치 끔 (테스트)', 90); if (p.melee && game.learned.indexOf('movie') < 0) game.learned.push('movie'); if (!p.melee) game.learned = ['locman']; }
    else if (e.code === 'Digit2') sim.spawn(game, 'trooper', Math.max(40, Math.min(C.STAGE_W - 40, p.x + p.facing * 230)));
    else if (e.code === 'Digit3') sim.spawn(game, 'drone', Math.max(40, Math.min(C.STAGE_W - 40, p.x + p.facing * 200)));
    else if (e.code === 'KeyV') { lookIdx = (lookIdx + 1) % LOOKS.length; applyLook().then(function () { showMessage('캐릭터: ' + LOOKS[lookIdx].name, 90); }); }
    else if (e.code === 'KeyC') {
      if (LOOKS[lookIdx].skins) { skinIdx = (skinIdx + 1) % SKINS.length; applyLook(); }
      else showMessage(LOOKS[lookIdx].name + '은 색상이 한 가지다', 90);
    }
    else if (e.code === 'KeyH') R.showBoxes = !R.showBoxes;
    else if (e.code === 'KeyN') R.showStates = (R.showStates + 1) % (R.statePages() + 1);   // 꺼짐 → 1쪽 → 2쪽 → 꺼짐
    else if (e.code === 'KeyB') { R.showCast = !R.showCast; showMessage(R.showCast ? '등장인물 보기 켬' : '등장인물 보기 끔', 60); }
    else if (e.code === 'KeyP') paused = !paused;
    else if (e.code === 'KeyM') { muted = !muted; showMessage(muted ? '소리 끔' : '소리 켬', 60); }
  });
  window.addEventListener('keyup', function (e) { if (MAP[e.code]) { keys[MAP[e.code]] = false; e.preventDefault(); } });
  window.addEventListener('blur', function () { keys = {}; });

  // ───────────── 안내 글자 ─────────────
  function showMessage(text, frames) { elMsgText.textContent = text; elMsg.style.opacity = 1; msgT = frames; }
  function drainEvents() {
    for (var i = 0; i < game.events.length; i++) {
      var ev = game.events[i];
      if (ev.type === 'message') showMessage(ev.text, ev.time);
      else if (ev.type === 'sfx' && SFX[ev.name]) SFX[ev.name]();
    }
    game.events.length = 0;
  }
  function updateOverlay() {
    var html = '';
    for (var i = 0; i < game.learned.length; i++) html += '<div>' + MEDIA_LABEL[game.learned[i]] + '</div>';
    if (elMedia.innerHTML !== html) elMedia.innerHTML = html;
    if (game.combo >= 2) { elCombo.style.display = 'block'; elCombo.innerHTML = '<small>COMBO</small>' + game.combo; }
    else elCombo.style.display = 'none';
    if (msgT > 0) { msgT--; if (msgT === 0) elMsg.style.opacity = 0; }
  }

  function tick() {
    sim.step(game, { left: !!keys.left, right: !!keys.right, jump: !!keys.jump, attack: !!keys.attack });
    drainEvents();
    updateOverlay();
    if (game.frame % 30 === 0) document.documentElement.dataset.frame = game.frame;  // 루프가 도는지 밖에서 확인하는 용도
  }

  // ───────────── 실행 ─────────────
  var last = 0, acc = 0, STEP = 1000 / 60;
  function frame(now) {
    if (!last) last = now;
    acc += Math.min(100, now - last); last = now;
    while (acc >= STEP) { if (!paused) tick(); acc -= STEP; }
    R.draw(ctx, game);
    requestAnimationFrame(frame);
  }

  // 화면 확인용: index.html?demo=이름 으로 열면 정해진 장면까지 진행한 뒤 한 번만 그린다.
  function runDemo(name) {
    var g, p, e, i, K = sim.ACTIONS.knuckle;
    function steps(n, inp) { for (var k = 0; k < n; k++) { sim.step(game, inp || {}); drainEvents(); updateOverlay(); } }
    function until(cond, inp, limit) { for (var k = 0; k < (limit || 300) && !cond(); k++) steps(1, inp); }
    function duel(melee, gap) {                          // 빈 무대에 쏘지 않는 적 하나
      game = sim.createGame({ empty: true, melee: melee }); if (melee) game.learned.push('movie');
      g = game; p = g.player; p.x = 250; e = sim.spawn(g, 'trooper', p.x + gap); e.cool = 99999;
      steps(4);
    }
    if (name === 'start') { steps(40); }
    else if (name === 'shoot') { steps(2); steps(1, { attack: true }); steps(4); }                         // 1타의 발사 프레임
    else if (name === 'combo3') {                                                                           // 3타: 마무리탄을 쏘는 프레임
      duel(false, 170);
      steps(1, { attack: true }); steps(8); steps(1, { attack: true }); steps(8); steps(1, { attack: true }); steps(9);
    } else if (name === 'knockback') {                                                                      // 3타에 맞아 밀려나는 적
      duel(false, 170);
      steps(1, { attack: true }); steps(8); steps(1, { attack: true }); steps(8); steps(1, { attack: true });
      until(function () { return e.state === 'knockback'; }); steps(g.hitstop + 6);
    } else if (name === 'chase') {                                                                          // 넉백된 적을 차지샷으로 추격
      duel(false, 170);
      steps(1, { attack: true }); steps(8); steps(1, { attack: true }); steps(8);
      until(function () { return p.chargeT >= C.CHARGE_MID + 1; }, { attack: true }); steps(1);
      until(function () { return g.chases > 0; }); steps(4);
    } else if (name === 'charge') { steps(C.CHARGE_FULL + 6, { attack: true }); }
    else if (name === 'chargeshot') { steps(C.CHARGE_FULL + 4, { attack: true }); steps(6); }
    else if (name === 'learn') { game.player.x = 850; game.player.y = game.platforms[0].y; game.camX = 600; steps(40); }
    else if (name === 'windup' || name === 'punch' || name === 'launch' || name === 'airchase') {
      duel(true, 50);
      if (name === 'windup') { steps(1, { attack: true }); steps(13); }                                     // 통전
      else if (name === 'punch') { steps(1, { attack: true }); until(function () { return p.act && p.act.hit; }); steps(3); }      // 기폭
      else if (name === 'launch') { steps(1, { attack: true }); until(function () { return p.act && p.act.hit; }); steps(g.hitstop + 16); }   // 떠오른 적
      else { until(function () { return p.act && p.act.hit; }, { attack: true }); steps(1); until(function () { return g.chases > 0; }); steps(3); }   // 공중 추격
    } else if (name === 'drone') {
      game = sim.createGame({ empty: true }); g = game; g.player.x = 240;
      sim.spawn(g, 'drone', 420); sim.spawn(g, 'trooper', 520);
      steps(60); steps(14, { jump: true }); steps(1, { jump: true, attack: true }); steps(3, { jump: true });
    } else if (name === 'bot') {
      var n = parseInt(query.get('frames') || '900', 10), holdT = 0;
      game.player.hp = 9999;
      for (i = 0; i < n && !game.cleared; i++) {
        p = game.player; var inp = {};
        var ups = game.enemies.filter(function (q) { return q.alive && !q.dying; }).sort(function (a, b) { return Math.abs(a.x - p.x) - Math.abs(b.x - p.x); });
        var near = ups[0], movie = game.pickups.filter(function (k) { return !k.taken; })[0];
        if (movie && (!near || near.x > movie.x + 40)) { inp.right = p.x < movie.x - 4; inp.left = p.x > movie.x + 4; inp.jump = Math.abs(p.x - 800) < 26 && p.onGround; }
        else if (near) {
          var dx = near.x - p.x;
          if (near.type === 'drone') { inp.right = dx > 130; inp.left = dx < -130; inp.jump = i % 50 < 22; inp.attack = i % 9 < 2; }
          else if (p.melee) { inp.right = dx > 44; inp.left = dx < -44; if (Math.abs(dx) <= 56 || holdT > 0) { holdT++; inp.attack = holdT <= 40; if (holdT > 62) holdT = 0; } }
          else { inp.right = dx > 210; inp.left = dx < -210; inp.attack = (i % 60) < 2 || ((i % 60) >= 10 && (i % 60) < 12) || ((i % 60) >= 20 && (i % 60) < 48); }
        } else inp.right = true;
        steps(1, inp);
      }
    }
    R.draw(ctx, game);
    document.title = 'READY';
  }

  var cache = {};
  function load(src) {
    if (!cache[src]) cache[src] = new Promise(function (resolve) {
      var img = new Image();
      img.onload = function () { resolve(img); };
      img.onerror = function () { resolve(null); };
      img.src = src;
    });
    return cache[src];
  }

  // 목록의 그림을 차례로 불러 보고 처음으로 불러와진 것을 돌려준다 (없으면 null).
  function firstOf(list) {
    return list.reduce(function (acc, src) {
      return acc.then(function (img) { return img || load(src); });
    }, Promise.resolve(null));
  }

  // 상태별 시트: 상태마다 그림 한 장. 색상은 skin_b~f 폴더, 적(NX 양산형)은 trooper 폴더에 같은 이름으로 있다.
  function loadStates(st, sk) {
    var table = st.states && S.stateSheets && S.stateSheets[st.id];
    if (!table) return Promise.resolve(null);
    var names = Object.keys(table.states), dir = st.dir + st.states;
    return Promise.all(names.map(function (n) {
      var own = sk.id === 'a' ? [] : [dir + 'skin_' + sk.id + '/' + n + '.png'];
      return Promise.all([firstOf(own.concat([dir + n + '.png'])), firstOf([dir + 'trooper/' + n + '.png', dir + n + '.png'])]);
    })).then(function (im) {
      var out = { table: table, player: {}, trooper: {} };
      names.forEach(function (n, i) { out.player[n] = im[i][0]; out.trooper[n] = im[i][1]; });
      return names.every(function (n) { return out.player[n]; }) ? out : null;
    });
  }

  // 캐릭터 시트 하나: 표(S.stateSheets[id])와 상태마다 그림 한 장.
  function loadLook(look) {
    var table = S.stateSheets && S.stateSheets[look.id];
    if (!look.dir || !table) return Promise.resolve(null);
    var names = Object.keys(table.states);
    return Promise.all(names.map(function (n) { return load(look.dir + n + '.png'); })).then(function (im) {
      var images = {};
      names.forEach(function (n, i) { images[n] = im[i]; });
      return names.every(function (n) { return images[n]; }) ? { id: look.id, name: look.name, table: table, images: images } : null;
    });
  }

  // 지금 고른 캐릭터와 색상의 그림을 불러와 적용한다. 그 색상의 그림이 없으면 기본 색상으로 대신한다.
  // 드론 · 아이템 · 이펙트는 아직 스타일 3 의 그림이 없어서 처음 만든 시트(assets/combat_sheet_1x.png)를 쓴다.
  function applyLook() {
    var sk = SKINS[skinIdx], st = STYLES[styleIdx], look = LOOKS[lookIdx];
    return Promise.all([
      load('assets/combat_sheet_1x.png'),
      load(st.dir + st.bg),
      load(st.dir + 'cast_idle_1x.png'),
      loadStates(st, sk),
      loadLook(look),
    ]).then(function (im) {
      R.images.combat = im[0]; R.images.bg = im[1]; R.images.cast = im[2];
      R.hasCombat = !!im[0];
      R.states = im[3] ? im[3].table : null; R.stImages = im[3] ? im[3].player : {}; R.stTrooper = im[3] ? im[3].trooper : {};
      R.style = st.id; R.bgDim = st.bgDim || 0.22;
      if (look.dir && !im[4]) { lookIdx = 0; look = LOOKS[0]; showMessage('assets/nova/states/ 의 그림을 불러오지 못했습니다', 240); }   // 없으면 기본 캐릭터로
      R.look = (look.dir && im[4]) || (im[3] ? { id: 'c', name: LOOKS[0].name, table: im[3].table, images: im[3].player } : null);
      R.showStates = Math.min(R.showStates, R.statePages());
      elSkin.innerHTML = '<b>' + look.name + '</b> <kbd>V</kbd>' + (look.skins ? '<br>색상 ' + sk.name + ' <kbd>C</kbd>' : '');
      return !!im[3] && !!im[0];
    });
  }

  applyLook().then(function (ok) {
    if (!ok) { showMessage('assets/style_c/states/ 의 그림을 불러오지 못했습니다', 99999); return; }
    var demo = query.get('demo');
    if (demo) { runDemo(demo); return; }
    drainEvents(); updateOverlay();
    requestAnimationFrame(frame);
  });

  S.debug = { game: function () { return game; } };
})();
