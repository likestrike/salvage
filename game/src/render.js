/* SALVAGE 전투 프로토타입 — 화면 그리기
 *
 * 게임 상태(sim.js)를 받아 640x360 캔버스에 그린다. 상태는 바꾸지 않는다.
 */
(function (root) {
  'use strict';
  var S = root.SALVAGE = root.SALVAGE || {};
  var C = S.sim.C;
  var CELL = 96;                        // 드론 · 아이템 · 이펙트 시트(combat_sheet)의 칸

  var R = { images: {}, hasCombat: false, showBoxes: false, bgDim: 0.4, style: 'c', showCast: true, castW: 112, castH: 112, castBase: [100, 100, 100],
    states: null, stImages: {}, stTrooper: {}, showStates: 0,
    look: null };                       // 플레이어의 캐릭터 시트 { id, name, table, images }. V 로 바꾼다 (main.js)

  function hash(n) { var x = Math.sin(n * 127.1) * 43758.5453; return x - Math.floor(x); }

  // ───────────── 어떤 프레임을 그릴까 ─────────────
  // 그림은 상태별 시트(assets/style_c/states/)에서 고른다. 공격 중에는 sim 의 동작 표(ACTIONS 의 anim)가 정한 프레임을 그대로 쓴다.
  // 판정이 나오는 틱과 쏘는 · 치는 프레임이 같은 표에서 나오므로 그림과 판정이 어긋나지 않는다.
  var CAST_TICKS = 20;
  function hasState(name) { return !!(R.states && R.states.states[name]); }
  // 표 t 의 상태 시트에서 프레임 i. 칸 크기는 상태마다 다를 수 있다 (근접은 폭발이 들어가도록 옆으로 넓다).
  // dx = 그 프레임을 가로로 옮기는 px (그림 안에서 미끄러진 만큼 되돌린다. NOVA 시안의 3타 · 피격).
  function SF(t, name, i) {
    var st = t.states[name], cell, col;
    if (!st) { name = 'idle'; st = t.states.idle; i = 0; }
    cell = st.cell || t.cell; col = (i | 0) % st.frames;
    return { st: name, row: 0, col: col, base: t.base, cw: cell[0], ch: cell[1], dx: st.dx ? st.dx[col] : 0 };
  }
  function ST(name, i) { return SF(R.states, name, i); }       // 스타일 3 의 표 (NX-07 과 적)
  function loopFrame(name, counter) { return ST(name, (counter / R.states.states[name].ticks) | 0); }

  // 대기. 파츠로 만든 대기를 처음 프레임부터 돌리고, 한동안 서 있으면 주포를 확인하는 모션을 한 번 끼운다.
  // 확인 모션은 대기가 쉬는 자세(0번 프레임)일 때 시작하고, 끝나면 대기를 0번 프레임부터 다시 돈다.
  var CHECK_AFTER_LOOPS = 2, CHECK_EVERY_LOOPS = 4;      // 처음에는 대기 2바퀴 뒤, 그 뒤로는 4바퀴마다
  function idleFrame(t) {
    var st = R.states.states.idle, loop = st.frames * st.ticks;
    if (!hasState('idle_check') || t < CHECK_AFTER_LOOPS * loop) return ST('idle', (t / st.ticks) | 0);
    var ck = R.states.states.idle_check, len = ck.frames * ck.ticks;
    var k = (t - CHECK_AFTER_LOOPS * loop) % (len + CHECK_EVERY_LOOPS * loop);
    return k < len ? ST('idle_check', (k / ck.ticks) | 0) : ST('idle', ((k - len) / st.ticks) | 0);
  }

  // 플레이어의 프레임. 캐릭터 시트의 표에 자세(poses)가 있으면 그 표로 고르고(NOVA 시안), 없으면 스타일 3 의 NX-07 이다.
  function playerFrame(g) {
    var t = R.look && R.look.table;
    return t && t.poses ? lookFrame(g, t) : nx07Frame(g);
  }

  // 표에 자세(poses)와 동작 표(actions)가 들어 있는 캐릭터 시트. 동작의 틱은 sim 의 것이고, 어느 프레임을 보일지만 표가 정한다.
  // 표의 길이와 판정 프레임이 sim 의 동작과 맞는지는 game/test/sim.test.js 가 확인한다.
  function lookFrame(g, t) {
    var p = g.player, P = t.poses, q, f, k, i, tl;
    function pose(name, k) {                               // 자세의 k 번째 프레임 (frames 가 있으면 그 목록에서 고른다)
      var q = P[name], fr = q.frames, n = fr ? fr.length : t.states[q.state].frames;
      k = Math.max(0, Math.min(n - 1, k | 0));
      var f = SF(t, q.state, fr ? fr[k] : k);
      if (q.muzzle) f.muzzle = q.muzzle;
      if (q.orb) f.orb = true;
      return f;
    }
    function loop(name, counter) { var st = t.states[P[name].state]; return pose(name, ((counter / st.ticks) | 0) % st.frames); }
    if (p.state === 'dead') return pose('dead', p.stateT / P.dead.ticks);
    if (p.state === 'hurt') return pose('hurt', (1 - p.stateT / 18) * P.hurt.frames.length);
    if (p.state === 'learn') {                             // 무릎을 꿇고, 머무르다, 끝날 때 일어난다
      q = P.learn; k = Math.min(C.LEARN_TIME - p.stateT, p.stateT) / q.ticks;
      return pose('learn', k < q.down ? k : q.down + ((g.frame / 14) | 0) % (t.states[q.state].frames - q.down));
    }
    if (p.act && t.actions[p.act.id]) {                    // 공격 동작: 표가 정한 프레임
      tl = t.actions[p.act.id];
      for (i = 0; i < tl.length - 1 && p.act.t >= tl[i][2]; i++);
      f = SF(t, tl[i][0], tl[i][1]); f.orb = true; f.muzzle = t.muzzle[p.act.id];
      return f;
    }
    var charging = p.charging && p.chargeT > 8;
    if (!p.onGround) {
      if (charging) return pose('air_charge', 0);
      return pose('jump', p.vy < -5.5 ? 0 : p.vy < -2 ? 1 : p.vy < 2 ? 2 : 3);     // 박차기 · 오름 · 꼭대기 · 떨어짐
    }
    if (Math.abs(p.vx) > 0.1) return loop(charging ? 'run_charge' : 'run', p.anim);
    if (charging) return pose('charge', p.chargeT < C.CHARGE_MID ? (g.frame >> 3) % 2 : p.chargeT < C.CHARGE_FULL ? 2 + (g.frame >> 3) % 2 : 3 + (g.frame >> 2) % 2);
    if (p.landT > 0) return pose('land', 0);
    return loop('idle', p.idleT || 0);
  }

  function nx07Frame(g) {
    var p = g.player, f;
    if (p.state === 'dead') return p.onGround ? ST('down', 0) : ST('launch', 1);
    if (p.state === 'hurt') return ST('stagger', 0);
    if (p.state === 'learn') return ST('learn', 0);
    if (p.act) {                                            // 공격 동작: 동작 표가 정한 프레임
      var a = S.sim.animOf(p.act);
      f = ST(a[0], a[1]); f.orb = true;
      return f;
    }
    var charging = p.charging && p.chargeT > 8;
    if (!p.onGround) {
      if (charging) { f = ST('air_charge', 0); f.orb = true; return f; }
      return ST('jump', p.vy < -2 ? 2 : p.vy < 2 ? 3 : 4);
    }
    if (Math.abs(p.vx) > 0.1) return loopFrame('run', p.anim);
    if (charging) {                                         // 모으는 중: 빛이 커지고, 다 차면 깜빡인다
      f = ST('charge', p.chargeT < C.CHARGE_MID ? (g.frame >> 2) % 2 : p.chargeT < C.CHARGE_FULL ? 2 : 2 + ((g.frame >> 2) % 2));
      f.orb = true;
      return f;
    }
    if (p.landT > 0) return ST('jump', 5);
    return idleFrame(p.idleT || 0);
  }

  // 적(NX 양산형): 상태가 곧 그림이다. 리액션 프레임은 react 시트에서 나온다.
  function trooperFrame(e) {
    var s = e.state;
    if (s === 'stagger') return ST('stagger', e.hitSeq % 2);                                   // 맞을 때마다 두 자세를 번갈아
    if (s === 'knockback') return ST('knockback', e.t > 14 ? 0 : 1);                           // 밀려남 → 버팀
    if (s === 'launch') return ST('launch', e.t < 4 ? 0 : e.vy < -1.5 ? 1 : e.vy < 2.5 ? 2 : 3);   // 맞은 직후 · 오름 · 꼭대기 · 떨어짐
    if (s === 'down') return ((e.dying ? C.DEAD_TIME : C.DOWN_TIME) - e.t) < 8 ? ST('land', 0) : ST('down', 0);
    if (s === 'getup') return ST('getup', e.t > C.GETUP_TIME / 2 ? 0 : 1);
    if (s === 'aim') return ST('shoot', 0);
    if (s === 'recoil') return ST('shoot', e.t > 12 ? 1 : 2);
    if (Math.abs(e.vx) > 0.1) return ST('run', (e.anim / 14) | 0);                             // 적은 0.7px/틱으로 걷는다
    return loopFrame('idle', e.anim);
  }

  // 번쩍임(Hit Flash): 맞은 스프라이트를 흰 실루엣으로 그린다. 픽셀을 읽지 않고 겹쳐 그리기만 하므로 file:// 에서도 된다.
  var flashCanvas = null;
  function drawCellWhite(ctx, img, f, x, y, facing) {
    if (!flashCanvas) { flashCanvas = document.createElement('canvas'); flashCanvas.width = 192; flashCanvas.height = 128; }
    var c = flashCanvas.getContext('2d'), cw = f.cw, ch = f.ch;
    c.globalCompositeOperation = 'source-over'; c.clearRect(0, 0, 192, 128);
    c.drawImage(img, f.col * cw, f.row * ch, cw, ch, 0, 0, cw, ch);
    c.globalCompositeOperation = 'source-atop'; c.fillStyle = '#ffffff'; c.fillRect(0, 0, cw, ch);
    ctx.save();
    ctx.translate(Math.round(x), Math.round(y));
    if (facing < 0) ctx.scale(-1, 1);
    ctx.drawImage(flashCanvas, 0, 0, cw, ch, -cw / 2 + (f.dx || 0), -f.base, cw, ch);
    ctx.restore();
  }

  function drawCell(ctx, img, f, x, y, facing, alpha) {
    var cw = f.cw || CELL, ch = f.ch || CELL;
    ctx.save();
    ctx.translate(Math.round(x), Math.round(y));
    if (facing < 0) ctx.scale(-1, 1);
    if (alpha !== undefined) ctx.globalAlpha = alpha;
    ctx.drawImage(img, f.col * cw, f.row * ch, cw, ch, -cw / 2 + (f.dx || 0), -f.base, cw, ch);
    ctx.restore();
  }

  // ───────────── 배경 ─────────────
  var SKY = ['#231d3c', '#2b2146', '#352650', '#422b59', '#55305f', '#6b3765', '#854067', '#a14c66', '#bd5c62', '#d6735c', '#e88e58', '#f3ab60'];

  // 스타일 2: 그려 둔 배경 그림을 좌우로 뒤집어 가며 이어 붙이고, 바닥만 코드로 그린다.
  function drawBackgroundImage(ctx, g) {
    var img = R.images.bg, cam = g.camX, w = img.width, off = cam, i, x;   // 길가 건물이 바닥과 함께 움직이도록 1:1
    var first = Math.floor(off / w);
    for (i = first; i <= first + Math.ceil(C.VIEW_W / w) + 1; i++) {
      x = Math.round(i * w - off);
      ctx.save();
      if (i % 2) { ctx.translate(x + w, 0); ctx.scale(-1, 1); ctx.drawImage(img, 0, 0); }
      else ctx.drawImage(img, x, 0);
      ctx.restore();
    }
    ctx.fillStyle = 'rgba(10, 12, 24, ' + R.bgDim + ')'; ctx.fillRect(0, 0, C.VIEW_W, C.GROUND_Y);   // 배경을 눌러 캐릭터가 묻히지 않게
    ctx.fillStyle = '#12131c'; ctx.fillRect(0, C.GROUND_Y, C.VIEW_W, C.VIEW_H - C.GROUND_Y);
    ctx.fillStyle = '#3a4058'; ctx.fillRect(0, C.GROUND_Y, C.VIEW_W, 1);
    ctx.fillStyle = '#1c1e2b'; ctx.fillRect(0, C.GROUND_Y + 1, C.VIEW_W, 2);
    for (i = 0; i < 90; i++) {                      // 젖은 바닥의 네온 반사
      x = Math.round(i * 29 + hash(i) * 22 - cam);
      if (x < -30 || x > C.VIEW_W) continue;
      ctx.fillStyle = hash(i + 2) > 0.7 ? '#5a2d5e' : hash(i + 4) > 0.55 ? '#1f4f5c' : '#1a1c28';
      ctx.fillRect(x, C.GROUND_Y + 6 + Math.floor(hash(i + 5) * 40), 10 + Math.floor(hash(i + 9) * 22), 1);
    }
  }

  function drawBackground(ctx, g) {
    if (R.images.bg) { drawBackgroundImage(ctx, g); return; }
    var cam = g.camX, i, x, w, h;
    for (i = 0; i < SKY.length; i++) { ctx.fillStyle = SKY[i]; ctx.fillRect(0, i * 20, C.VIEW_W, 21); }
    ctx.fillStyle = SKY[SKY.length - 1]; ctx.fillRect(0, 240, C.VIEW_W, 120);

    // ARTEMIS: 도시 위에 떠 있는 청록색 구체
    var ax = 440 - cam * 0.04, ay = 118, ar = 66;
    ctx.save();
    ctx.globalAlpha = 0.5; ctx.fillStyle = '#3fb7b4';
    ctx.beginPath(); ctx.arc(ax, ay, ar, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 0.55; ctx.strokeStyle = '#9af3ea'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(ax, ay, ar, 0, Math.PI * 2); ctx.stroke();
    for (i = -2; i <= 2; i++) {
      ctx.beginPath(); ctx.ellipse(ax, ay, Math.abs(ar * Math.cos(i * 0.55)) + 1, ar, 0, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath(); ctx.ellipse(ax, ay + i * 22, Math.sqrt(Math.max(1, ar * ar - i * i * 484)), 5, 0, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();

    // 먼 도시
    for (i = 0; i < 46; i++) {
      w = 22 + Math.floor(hash(i) * 26); h = 60 + Math.floor(hash(i + 50) * 120);
      x = Math.round(i * 38 - cam * 0.18) - 60;
      if (x + w < 0 || x > C.VIEW_W) continue;
      ctx.fillStyle = i % 3 ? '#3c2f58' : '#46365f';
      ctx.fillRect(x, 246 - h, w, h + 60);
      ctx.fillStyle = '#7fe0dc';
      for (var k = 0; k < 9; k++) if (hash(i * 31 + k) > 0.62) ctx.fillRect(x + 4 + (k % 3) * 6, 252 - h + Math.floor(k / 3) * 14, 2, 3);
    }
    // 슬럼의 판잣집
    for (i = 0; i < 40; i++) {
      w = 54 + Math.floor(hash(i + 7) * 46); h = 34 + Math.floor(hash(i + 99) * 54);
      x = Math.round(i * 74 - cam * 0.5) - 80;
      if (x + w < 0 || x > C.VIEW_W) continue;
      ctx.fillStyle = i % 2 ? '#2a2238' : '#322842';
      ctx.fillRect(x, C.GROUND_Y - h, w, h);
      ctx.fillStyle = '#1f1a2b'; ctx.fillRect(x - 3, C.GROUND_Y - h - 4, w + 6, 5);
      if (hash(i + 3) > 0.45) { ctx.fillStyle = '#f2b36b'; ctx.fillRect(x + 10, C.GROUND_Y - h + 12, 8, 9); }
      if (hash(i + 11) > 0.7) { ctx.fillStyle = '#e24fa0'; ctx.fillRect(x + w - 16, C.GROUND_Y - h + 8, 5, 18); }
      ctx.fillStyle = '#1a1624'; ctx.fillRect(x + w - 6, C.GROUND_Y - h - 22, 2, 22);
    }
    ctx.strokeStyle = '#1a1624'; ctx.lineWidth = 1; ctx.beginPath();
    for (i = 0; i < 16; i++) {
      x = Math.round(i * 148 - cam * 0.5);
      ctx.moveTo(x, C.GROUND_Y - 96); ctx.quadraticCurveTo(x + 74, C.GROUND_Y - 78, x + 148, C.GROUND_Y - 96);
    }
    ctx.stroke();

    // 바닥
    ctx.fillStyle = '#2b2933'; ctx.fillRect(0, C.GROUND_Y, C.VIEW_W, C.VIEW_H - C.GROUND_Y);
    ctx.fillStyle = '#4d4959'; ctx.fillRect(0, C.GROUND_Y, C.VIEW_W, 2);
    ctx.fillStyle = '#211f28';
    for (i = 0; i < 80; i++) {
      x = Math.round(i * 31 + hash(i) * 20 - cam);
      if (x < -20 || x > C.VIEW_W) continue;
      ctx.fillRect(x, C.GROUND_Y + 8 + Math.floor(hash(i + 5) * 34), 8 + Math.floor(hash(i + 9) * 16), 1);
    }
  }

  function drawPlatforms(ctx, g) {
    for (var i = 0; i < g.platforms.length; i++) {
      var p = g.platforms[i], x = Math.round(p.x - g.camX), y = p.y, h = C.GROUND_Y - p.y, k;
      if (p.kind === 'container') {
        ctx.fillStyle = '#35513f'; ctx.fillRect(x, y, p.w, h);
        ctx.fillStyle = '#4a6b55'; ctx.fillRect(x, y, p.w, 3);
        ctx.fillStyle = '#27402f';
        for (k = 8; k < p.w - 4; k += 10) ctx.fillRect(x + k, y + 5, 3, h - 8);
        ctx.fillStyle = '#7a4a2e'; ctx.fillRect(x + 12, y + 20, 14, 6);
      } else {
        ctx.fillStyle = '#5b4031'; ctx.fillRect(x, y, p.w, h);
        ctx.fillStyle = '#7b5a43'; ctx.fillRect(x, y, p.w, 3);
        ctx.fillStyle = '#3f2c22';
        ctx.fillRect(x, y + h / 2 - 1, p.w, 2); ctx.fillRect(x + p.w / 2 - 1, y + 3, 2, h - 3);
        ctx.fillRect(x, y + 3, 2, h - 3); ctx.fillRect(x + p.w - 2, y + 3, 2, h - 3);
      }
    }
  }

  // ───────────── 물체 ─────────────
  function itemCell(ctx, col, x, y, scale) {
    var img = R.images.combat, s = scale || 1;
    ctx.drawImage(img, col * CELL, 3 * CELL, CELL, CELL, Math.round(x - CELL * s / 2), Math.round(y - CELL * s / 2), CELL * s, CELL * s);
  }

  function drawPickups(ctx, g) {
    for (var i = 0; i < g.pickups.length; i++) {
      var k = g.pickups[i];
      if (k.taken) continue;
      var x = k.x - g.camX, y = k.y + Math.sin(g.frame / 14) * 3;
      ctx.save(); ctx.globalAlpha = 0.35 + 0.2 * Math.sin(g.frame / 9); ctx.fillStyle = '#7ff5ee';
      ctx.beginPath(); ctx.arc(x, y, 15, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      if (R.hasCombat) itemCell(ctx, 1, x, y, 0.75);
      else { ctx.fillStyle = '#16161c'; ctx.fillRect(x - 11, y - 7, 22, 14); ctx.fillStyle = '#f2f2ee'; ctx.fillRect(x - 7, y - 4, 14, 5); }
    }
  }

  function drawEnemies(ctx, g) {
    for (var i = 0; i < g.enemies.length; i++) {
      var e = g.enemies[i], x = e.x - g.camX;
      if (x < -90 || x > C.VIEW_W + 90) continue;
      if (e.dying && e.state === 'down' && e.t < 40 && (g.frame >> 2) % 2) continue;       // 사라지기 전에 깜빡인다
      var flash = e.flash > 0;
      if (e.type === 'drone') {
        var col = e.state === 'fall' ? 7 : (e.state === 'stagger' || e.state === 'knockback') ? 6 : e.state === 'aim' ? 4 : e.state === 'recoil' ? 5 : (e.anim / 5 | 0) % 4;
        ctx.save(); ctx.translate(Math.round(x), Math.round(e.y));
        if (e.facing > 0) ctx.scale(-1, 1);              // 시트의 드론은 왼쪽을 본다
        if (e.state === 'fall') ctx.rotate(e.t * 0.12);
        ctx.drawImage(R.images.combat, col * CELL, 2 * CELL, CELL, CELL, -CELL / 2, -CELL / 2, CELL, CELL);
        if (flash) { ctx.globalAlpha = 0.75; ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.ellipse(0, 0, 22, 13, 0, 0, Math.PI * 2); ctx.fill(); }
        ctx.restore();
      } else {
        var tf = trooperFrame(e), img = R.stTrooper[tf.st];
        if (flash) drawCellWhite(ctx, img, tf, x, e.y, e.facing);
        else drawCell(ctx, img, tf, x, e.y, e.facing);
      }
      if (!e.dying && e.hp < e.maxHp) {                     // 맞은 적의 체력
        var top = e.type === 'drone' ? e.y - 26 : e.y - 92, w = 26;
        ctx.fillStyle = 'rgba(14, 13, 20, 0.8)'; ctx.fillRect(Math.round(x) - w / 2 - 1, Math.round(top) - 1, w + 2, 5);
        ctx.fillStyle = '#ff6b5e'; ctx.fillRect(Math.round(x) - w / 2, Math.round(top), Math.round(w * e.hp / e.maxHp), 3);
      }
      if (R.showBoxes) {
        ctx.strokeStyle = '#ff4d4d'; ctx.lineWidth = 1;
        if (e.type === 'drone') ctx.strokeRect(x - 20, e.y - 14, 40, 28); else ctx.strokeRect(x - 12, e.y - 74, 24, 72);
      }
    }
  }

  function drawPlayer(ctx, g) {
    var p = g.player, x = p.x - g.camX, f = playerFrame(g);
    if (p.invuln > 0 && !(p.act && p.act.id === 'knuckle') && p.state !== 'learn' && (g.frame >> 1) % 2) return;
    var img = (R.look ? R.look.images : R.stImages)[f.st], glow = (R.look && R.look.table.glow) || ['#7ff5ee', '#4fe3e6'];

    // 차지 중: 총구로 모이는 빛 (전용 프레임이 없을 때만 직접 그린다)
    if (p.charging && p.chargeT > 8) {
      var m = f.muzzle ? { x: p.x + p.facing * f.muzzle[0], y: p.y - f.muzzle[1] } : S.sim.muzzle(p), mx = m.x - g.camX, lvl = p.chargeT >= C.CHARGE_FULL ? 2 : p.chargeT >= C.CHARGE_MID ? 1 : 0, i;
      ctx.fillStyle = lvl === 2 ? '#ffffff' : glow[0];
      for (i = 0; i < 6; i++) {
        var a = (g.frame * 0.3 + i * 1.05), rr = 18 - ((g.frame * 1.3 + i * 5) % 16);
        ctx.fillRect(Math.round(mx + Math.cos(a) * rr), Math.round(m.y + Math.sin(a) * rr), 2, 2);
      }
      if (!f.orb) {
        ctx.fillStyle = glow[1] && R.look && R.look.table.glow ? glow[0] : '#4fe3e6'; ctx.beginPath(); ctx.arc(mx, m.y, 3 + lvl * 3 + (g.frame & 2 ? 1 : 0), 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(mx, m.y, 1 + lvl * 2, 0, Math.PI * 2); ctx.fill();
      }
    }
    if (p.state === 'learn') {                             // 학습 중: 머리 둘레의 데이터 고리
      ctx.strokeStyle = '#7ff5ee'; ctx.lineWidth = 1;
      for (var k = 0; k < 3; k++) {
        var ry = p.y - 20 - ((g.frame * 1.2 + k * 26) % 78);
        ctx.globalAlpha = 0.7; ctx.beginPath(); ctx.ellipse(x, ry, 22, 5, 0, 0, Math.PI * 2); ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    drawCell(ctx, img, f, x, p.y, p.facing);
    if (R.showBoxes) {
      ctx.strokeStyle = '#4de3ff'; ctx.lineWidth = 1; ctx.strokeRect(x - 12, p.y - 70, 24, 70);
      if (p.melee) { ctx.strokeStyle = 'rgba(255, 210, 77, 0.5)'; ctx.strokeRect(p.facing > 0 ? x : x - C.MELEE_RANGE, p.y - 84, C.MELEE_RANGE, 92); }   // 펀치가 걸리는 거리
      var A = p.act && p.act.id === 'knuckle' ? S.sim.ACTIONS.knuckle : null;
      if (A && p.act.t >= S.sim.fireTick(A) && p.act.t < S.sim.fireTick(A) + A.active + 1) {                                    // 주먹의 판정 (판정 틱에만)
        ctx.strokeStyle = '#ffffff'; ctx.strokeRect(p.facing > 0 ? x + C.FIST.x0 : x - C.FIST.x1, p.y - C.FIST.y1, C.FIST.x1 - C.FIST.x0, C.FIST.y1 - C.FIST.y0);
      }
    }
  }

  // 탄의 그림은 쏜 캐릭터의 총구 높이에 그린다. 판정의 자리(sim 의 MUZZLE_Y)는 캐릭터가 바뀌어도 그대로다.
  // 표에 총구(muzzle)가 없는 캐릭터(스타일 3 의 NX-07)는 0 이다.
  function shotDy(s) {
    var t = R.look && R.look.table, m = t && t.muzzle && t.muzzle[s.from];
    return m ? C.MUZZLE_Y - m[1] : 0;
  }
  function drawShots(ctx, g) {
    var i, s, x;
    for (i = 0; i < g.shots.length; i++) {
      s = g.shots[i]; x = Math.round(s.x - g.camX);
      if (R.hasCombat) {                                   // 시트의 탄 그림 (오른쪽을 본다)
        var col = s.kind === 'charge2' ? 5 : 4, sc = s.kind === 'charge1' ? 1.5 : s.kind === 'burst' ? 1.3 : 1;
        ctx.save(); ctx.translate(x, Math.round(s.y + shotDy(s)));
        if (s.vx < 0) ctx.scale(-1, 1);
        ctx.drawImage(R.images.combat, col * CELL, 3 * CELL, CELL, CELL, -CELL * sc / 2 - (col === 5 ? 10 : 0), -CELL * sc / 2, CELL * sc, CELL * sc);
        ctx.restore();
        continue;
      }
      if (s.kind === 'charge2') {
        ctx.fillStyle = '#35c9d6'; ctx.fillRect(x - 22, s.y - 8, 36, 16);
        ctx.fillStyle = '#9af3f4'; ctx.fillRect(x - 16, s.y - 6, 32, 12);
        ctx.fillStyle = '#ffffff'; ctx.fillRect(x - 6, s.y - 4, 20, 8);
        ctx.fillStyle = '#35c9d6';
        ctx.fillRect(x - (s.vx > 0 ? 34 : -22), s.y - 3, 12, 2); ctx.fillRect(x - (s.vx > 0 ? 30 : -18), s.y + 3, 12, 2);
      } else if (s.kind === 'charge1') {
        ctx.fillStyle = '#35c9d6'; ctx.fillRect(x - 9, s.y - 5, 18, 10);
        ctx.fillStyle = '#e9ffff'; ctx.fillRect(x - 5, s.y - 3, 12, 6);
      } else {
        ctx.fillStyle = '#35c9d6'; ctx.fillRect(x - 6, s.y - 3, 12, 6);
        ctx.fillStyle = '#e9ffff'; ctx.fillRect(x - 3, s.y - 2, 8, 4);
      }
    }
    for (i = 0; i < g.enemyShots.length; i++) {
      s = g.enemyShots[i]; x = Math.round(s.x - g.camX);
      ctx.fillStyle = '#b3202a'; ctx.fillRect(x - 5, Math.round(s.y) - 3, 10, 6);
      ctx.fillStyle = '#ff9a8a'; ctx.fillRect(x - 3, Math.round(s.y) - 1, 6, 2);
    }
  }

  function drawFx(ctx, g) {
    for (var i = 0; i < g.fx.length; i++) {
      var f = g.fx[i], x = Math.round(f.x - g.camX), y = Math.round(f.y), k = f.t / f.life, r, j;
      if (f.kind === 'muzzle') {
        continue;                                          // 총구의 섬광은 쏘는 프레임에 이미 그려져 있다
        if (R.hasCombat) {                                 // 시트의 섬광 그림
          var ms = (f.big ? 0.95 : 0.55) * (1 - k * 0.5);
          ctx.drawImage(R.images.combat, 7 * CELL, 3 * CELL, CELL, CELL, Math.round(x + f.dir * 6 - CELL * ms / 2), Math.round(y - CELL * ms / 2), CELL * ms, CELL * ms);
          continue;
        }
        r = f.big ? 12 : 6;
        ctx.fillStyle = '#ffffff'; ctx.fillRect(x - (f.dir < 0 ? r : 0), y - r / 2, r, r);
        ctx.fillStyle = '#7ff5ee'; ctx.fillRect(x - (f.dir < 0 ? r + 6 : -r), y - 2, 6, 4);
      } else if (f.kind === 'spark') {
        r = (f.big ? 12 : 7) * (1 - k);
        ctx.fillStyle = f.red ? '#ff8b7a' : '#ffffff';
        ctx.fillRect(x - r, y - 1, r * 2, 2); ctx.fillRect(x - 1, y - r, 2, r * 2);
      } else if (f.kind === 'boom' && R.hasCombat) {       // 시트의 폭발 그림
        var bs = (f.big ? 1.25 : 0.8) * (0.55 + k * 0.6);
        ctx.globalAlpha = k < 0.6 ? 1 : 1 - (k - 0.6) / 0.4;
        ctx.drawImage(R.images.combat, 6 * CELL, 3 * CELL, CELL, CELL, Math.round(x - CELL * bs / 2), Math.round(y - CELL * bs / 2), CELL * bs, CELL * bs);
        ctx.globalAlpha = 1;
      } else if (f.kind === 'boom') {
        r = (f.big ? 34 : 20) * (0.35 + k * 0.65);
        ctx.fillStyle = k < 0.3 ? '#ffffff' : k < 0.6 ? '#ffc94d' : '#f26a2e';
        ctx.globalAlpha = 1 - k * 0.75;
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#35c9d6';
        for (j = 0; j < 8; j++) ctx.fillRect(Math.round(x + Math.cos(j * 0.785) * r * 1.25) - 2, Math.round(y + Math.sin(j * 0.785) * r * 1.25) - 2, 4, 4);
        ctx.globalAlpha = 1;
      } else if (f.kind === 'ring') {
        ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3 * (1 - k) + 1; ctx.globalAlpha = 1 - k;
        ctx.beginPath(); ctx.ellipse(x, y, 10 + k * 56, 6 + k * 40, 0, 0, Math.PI * 2); ctx.stroke(); ctx.globalAlpha = 1;
      } else if (f.kind === 'dust') {
        ctx.fillStyle = '#8f8a99'; ctx.globalAlpha = 1 - k;
        for (j = -2; j <= 2; j++) ctx.fillRect(x + j * 9 * (0.4 + k), y - 3 - k * 6, 5, 4);
        ctx.globalAlpha = 1;
      } else if (f.kind === 'text') {
        ctx.font = 'bold 14px monospace'; ctx.textAlign = 'center';
        ctx.fillStyle = '#1b1422'; ctx.fillText(f.text, x + 1, y - k * 14 + 1);
        ctx.fillStyle = (f.t >> 2) % 2 ? '#ffd24d' : '#ffffff'; ctx.fillText(f.text, x, y - k * 14);
      }
    }
  }

  // ───────────── 상태 표시 ─────────────
  function drawHud(ctx, g) {
    var p = g.player, i;
    ctx.fillStyle = '#14121c'; ctx.fillRect(10, 10, 132, 16);
    ctx.fillStyle = '#35c9d6'; ctx.fillRect(10, 10, 2, 16);
    for (i = 0; i < C.PLAYER_HP; i++) {
      ctx.fillStyle = i < p.hp ? '#4fe3e6' : '#2b2a38';
      ctx.fillRect(16 + i * 10, 13, 8, 10);
    }
    // 학습한 매체 칸: 1 LOCMAN 게임팩, 2 무술 영화
    for (i = 0; i < 3; i++) {
      var sx = 10 + i * 30;
      ctx.fillStyle = '#14121c'; ctx.fillRect(sx, 30, 26, 26);
      ctx.strokeStyle = i < g.learned.length ? '#4fe3e6' : '#3b3a4a'; ctx.lineWidth = 1; ctx.strokeRect(sx + 0.5, 30.5, 25, 25);
      if (i >= g.learned.length) continue;
      if (R.hasCombat) itemCell(ctx, g.learned[i] === 'locman' ? 0 : 1, sx + 13, 43, g.learned[i] === 'locman' ? 0.6 : 0.5);
      else { ctx.fillStyle = g.learned[i] === 'locman' ? '#8d8f99' : '#16161c'; ctx.fillRect(sx + 6, 36, 14, 14); ctx.fillStyle = g.learned[i] === 'locman' ? '#3c6fd1' : '#f2f2ee'; ctx.fillRect(sx + 8, 38, 10, 6); }
    }
    // 차지 게이지
    ctx.fillStyle = '#14121c'; ctx.fillRect(10, 60, 86, 7);
    var ch = Math.min(1, p.chargeT / C.CHARGE_FULL);
    ctx.fillStyle = p.chargeT >= C.CHARGE_FULL ? ((g.frame >> 2) % 2 ? '#ffffff' : '#ffd24d') : p.chargeT >= C.CHARGE_MID ? '#9af3f4' : '#35c9d6';
    ctx.fillRect(12, 62, Math.round(82 * ch), 3);
    ctx.fillStyle = '#6a6880'; ctx.fillRect(12 + Math.round(82 * C.CHARGE_MID / C.CHARGE_FULL), 60, 1, 7);
  }

  // 등장인물 보기: 미리네·삼촌·BX-05 의 대기 동작을 무대 시작 지점에 세워 둔다 (스타일 비교용. 전투에는 관여하지 않는다)
  var CAST = [
    { row: 0, x: 176, facing: -1 },    // 미리네 (시작 지점의 NX-07 을 본다)
    { row: 1, x: 232, facing: -1 },    // 삼촌
    { row: 2, x: 356, facing: -1 },    // BX-05
  ];
  function drawCast(ctx, g) {
    var img = R.images.cast;
    if (!img || !R.showCast) return;
    var cw = R.castW, ch = R.castH, fr = ((g.frame / CAST_TICKS) | 0) % 4;
    for (var i = 0; i < CAST.length; i++) {
      var c = CAST[i], x = Math.round(c.x - g.camX);
      if (x < -cw || x > C.VIEW_W + cw) continue;
      ctx.save();
      ctx.translate(x, C.GROUND_Y);
      if (c.facing < 0) ctx.scale(-1, 1);
      ctx.drawImage(img, fr * cw, c.row * ch, cw, ch, -cw / 2, -R.castBase[c.row], cw, ch);
      ctx.restore();
    }
  }

  // 상태 보기 (N): 지금 스타일의 상태 시트를 모두, 저마다의 프레임 시간으로 돌려 본다. 게임에 아직 쓰지 않는 상태(회피)도 여기서 본다.
  // 상태 시트 보기 (N): 지금 캐릭터의 모든 상태를 제 프레임 시간으로 돌린다.
  // 한 화면에 다 들어가지 않아서 N 을 누를 때마다 다음 쪽으로 넘어간다. 게임이 쓰지 않는 상태는 이름이 회색이다.
  function boardGrid() {
    var t = R.look && R.look.table, b = (t && t.board) || [105, 116];
    var per = Math.max(1, Math.floor(C.VIEW_W / b[0])), size = per * Math.max(1, Math.floor((C.VIEW_H - 4) / b[1]));
    return { t: t, w: b[0], h: b[1], per: per, size: size, pages: t ? Math.ceil(Object.keys(t.states).length / size) : 0 };
  }
  function drawStateBoard(ctx, g) {
    var G = boardGrid(), t = G.t, i;
    if (!t) return;
    var names = Object.keys(t.states), page = Math.max(1, Math.min(G.pages, R.showStates)) - 1, left = Math.round((C.VIEW_W - G.per * G.w) / 2);
    ctx.fillStyle = 'rgba(14, 13, 20, 0.9)'; ctx.fillRect(0, 0, C.VIEW_W, C.VIEW_H);
    ctx.font = '8px monospace'; ctx.textBaseline = 'top'; ctx.textAlign = 'left';
    for (i = page * G.size; i < names.length && i < (page + 1) * G.size; i++) {
      var st = t.states[names[i]], cell = st.cell || t.cell, k = i - page * G.size;
      var x0 = left + (k % G.per) * G.w, y0 = 2 + ((k / G.per) | 0) * G.h, ground = y0 + G.h - 8;
      var fr = ((g.frame / st.ticks) | 0) % st.frames, img = R.look.images[names[i]];
      ctx.fillStyle = '#4d4959'; ctx.fillRect(x0 + 6, ground + 1, G.w - 12, 1);
      if (img) ctx.drawImage(img, fr * cell[0], 0, cell[0], cell[1], x0 + ((G.w - cell[0]) >> 1) + (st.dx ? st.dx[fr] : 0), ground - t.base, cell[0], cell[1]);
      ctx.fillStyle = st.used === false ? '#9a96ad' : '#7ff5ee'; ctx.fillText(names[i], x0 + 4, y0);
      ctx.fillStyle = '#77738a'; ctx.fillText(st.frames + 'f ' + st.ticks + 't', x0 + 4, y0 + 9);
    }
    ctx.textAlign = 'right'; ctx.fillStyle = '#ffffff';
    ctx.fillText((R.look.id === 'c' ? 'NX-07 STYLE 3' : String(R.look.id).toUpperCase()) + '  ' + (page + 1) + '/' + G.pages + '  [N]', C.VIEW_W - 4, C.VIEW_H - 10);
    ctx.textAlign = 'left';
  }
  R.statePages = function () { return boardGrid().pages; };

  function draw(ctx, g) {
    ctx.imageSmoothingEnabled = false;
    ctx.save();
    if (g.shake > 0) ctx.translate(Math.round((Math.random() - 0.5) * g.shake), Math.round((Math.random() - 0.5) * g.shake * 0.7));
    drawBackground(ctx, g);
    drawPlatforms(ctx, g);
    drawPickups(ctx, g);
    drawCast(ctx, g);
    drawEnemies(ctx, g);
    drawPlayer(ctx, g);
    drawShots(ctx, g);
    drawFx(ctx, g);
    ctx.restore();
    if (g.hitstop > 6) { ctx.fillStyle = 'rgba(255,255,255,0.35)'; ctx.fillRect(0, 0, C.VIEW_W, C.VIEW_H); }  // 타격 순간의 번쩍임
    drawHud(ctx, g);
    if (R.showStates) drawStateBoard(ctx, g);
  }

  R.draw = draw; R.playerFrame = playerFrame;
  S.render = R;
})(window);
