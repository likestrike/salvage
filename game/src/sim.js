/* SALVAGE 전투 프로토타입 — 게임 로직 (화면·브라우저와 무관)
 *
 * 한 번의 step() 이 1/60 초(= 1틱)다. 입력을 받아 상태만 바꾸고 그리지는 않는다.
 * 브라우저에서는 window.SALVAGE.sim 으로, Node 에서는 require() 로 쓴다.
 *
 * 전투 시스템의 설계는 docs/GAME_DESIGN.md 4.3 에 있다. 아래 ACTIONS · HITS 표가 그 문서의 표와 같은 값이다.
 *   입력(버퍼) → 동작(player.act) → 판정 → 적의 상태 → 다음 공격의 기회
 */
(function (root) {
  'use strict';

  var C = {
    VIEW_W: 640, VIEW_H: 360, GROUND_Y: 304, STAGE_W: 1920,
    GRAVITY: 0.38, WALK: 2.3, JUMP_V: -7.0, MAX_FALL: 8,
    PLAYER_HP: 12, INVULN: 70,
    // LOCMAN 게임팩: 기본 공격과 차지샷
    SHOT_SPEED: 7, SHOT_MAX: 3,
    CHARGE_MID: 24, CHARGE_FULL: 54,
    // 무술 영화: 너클 펀치 (숏어퍼 간장치기)
    MELEE_RANGE: 60,                                   // 이 거리 안에 적이 있으면 공격 버튼이 펀치가 된다
    FIST: { x0: 8, x1: 52, y0: 16, y1: 72 },           // 주먹의 판정: 플레이어 앞 x0~x1, 발바닥에서 위로 y0~y1
    FIST_X: 34, FIST_Y: 51,                            // 폭발 · 충격파가 터지는 자리 (melee 시트의 폭발 그림에 맞춘 값)
    // 입력
    BUFFER: 10,                                        // 공격 · 점프를 기억하는 틱
    CHARGE_BUFFER: 20,                                 // 차지샷(떼는 입력)을 기억하는 틱
    CHAIN_KEEP: 12,                                    // 앞의 타가 끝난 뒤 이 틱 안에 눌러야 다음 타로 이어진다
    // 적의 상태
    STAGGER: 18, DOWN_TIME: 40, GETUP_TIME: 24, DEAD_TIME: 70,
    CHASE_MULT: 1.5, AIR_CHASE_MULT: 2, JUGGLE_MAX: 3,
    LEARN_TIME: 110,
    MUZZLE_X: 36, MUZZLE_Y: 46,
    TROOPER_HP: 12, DRONE_HP: 4,
  };

  // ───────────── 동작 (틱 단위) ─────────────
  // anti 준비 → startup 시동 → active 판정 → recovery 후딜.  판정이 나오는 틱 = anti + startup.
  // root   : 지상 동작. 'move' 캔슬 틱까지 발이 묶인다.      air: 공중 동작. 움직임을 막지 않고, 착지하면 끝난다.
  // fire   : 판정 틱에 나가는 탄.                           cancel: 그 틱부터 그 행동으로 넘어갈 수 있다.
  // cancelOnHit: 맞혔을 때만 열리는 캔슬 창 (빗나가면 끝까지 간다).
  // anim   : [상태 시트, 프레임, 이 틱 전까지]. 그림은 이 표만 보고 고른다 → 그림과 판정이 어긋나지 않는다.
  var ACTIONS = {
    shot1: { name: '기본 1타', anti: 0, startup: 3, active: 2, recovery: 11, root: true, fire: 'shot',
      cancel: { knuckle: 5, attack: 8, jump: 8, charge: 8, move: 12 },
      anim: [['shoot', 0, 3], ['shoot', 1, 6], ['shoot', 2, 16]] },
    shot2: { name: '기본 2타', anti: 0, startup: 3, active: 2, recovery: 12, root: true, fire: 'shot',
      cancel: { knuckle: 5, attack: 8, jump: 8, charge: 8, move: 12 },
      anim: [['shot2', 0, 3], ['shot2', 1, 6], ['shot2', 2, 17]] },
    shot3: { name: '기본 3타', anti: 5, startup: 3, active: 3, recovery: 19, root: true, fire: 'burst',
      cancel: { knuckle: 18, jump: 18, charge: 18, attack: 22, move: 22 },
      anim: [['shot3', 0, 5], ['shot3', 1, 8], ['shot3', 2, 12], ['shot3', 3, 22], ['shot3', 4, 30]] },
    knuckle: { name: '너클 펀치', anti: 12, startup: 6, active: 4, recovery: 26, root: true, melee: true, stepIn: 6,
      cancelOnHit: { charge: 20, jump: 24, attack: 28 },
      // 접근 · 웅크림 · 통전 · 숏어퍼 · 기폭 · 충격파 · 회수 · 복귀. 빗나가면 기폭과 충격파 없이 끝난다
      anim: [['melee', 0, 6], ['melee', 1, 12], ['melee', 2, 15], ['melee', 3, 18], ['melee', 4, 24], ['melee', 5, 32], ['melee', 6, 42], ['melee', 7, 48]],
      animMiss: [['melee', 0, 6], ['melee', 1, 12], ['melee', 2, 15], ['melee', 3, 30], ['melee', 6, 40], ['melee', 7, 48]] },
    charge1: { name: '차지샷 1단', anti: 0, startup: 2, active: 2, recovery: 12, root: true, fire: 'charge1',
      cancel: { knuckle: 10, attack: 10, jump: 10, charge: 10, move: 10 },
      anim: [['charge', 2, 2], ['charge_shot', 0, 7], ['charge_shot', 1, 12], ['charge_shot', 2, 16]] },
    charge2: { name: '차지샷 2단', anti: 0, startup: 3, active: 3, recovery: 18, root: true, fire: 'charge2',
      cancel: { knuckle: 16, attack: 16, jump: 16, charge: 16, move: 16 },
      anim: [['charge', 3, 3], ['charge_shot', 0, 10], ['charge_shot', 1, 18], ['charge_shot', 2, 24]] },
    air_shot: { name: '공중 기본탄', anti: 0, startup: 2, active: 2, recovery: 8, air: true, fire: 'shot',
      cancel: { attack: 6, charge: 6 },
      anim: [['air_shoot', 0, 2], ['air_shoot', 1, 7], ['air_shoot', 0, 12]] },
    air_burst: { name: '공중 마무리탄', anti: 0, startup: 3, active: 2, recovery: 9, air: true, fire: 'burst',
      cancel: { charge: 8, attack: 10 },
      anim: [['air_shoot', 0, 3], ['air_burst', 0, 8], ['air_burst', 1, 14]] },
    air_charge: { name: '공중 차지샷', anti: 0, startup: 2, active: 2, recovery: 12, air: true, fire: 'charge',
      cancel: { attack: 10, charge: 10 },
      anim: [['air_charge', 0, 2], ['air_charge', 1, 9], ['air_shoot', 0, 16]] },
  };
  var CHAIN = ['shot1', 'shot2', 'shot3'];

  // ───────────── 타격 ─────────────
  // dmg 피해 · stop 타격 정지(틱) · flash 번쩍임(틱) · shake 화면 흔들림
  var HITS = {
    shot:    { dmg: 1, stop: 2,  flash: 4, shake: 0,  push: 0.9 },                    // 경직
    burst:   { dmg: 2, stop: 5,  flash: 6, shake: 3,  kbVx: 4.6, kbT: 38 },           // 넉백
    knuckle: { dmg: 3, stop: 10, flash: 8, shake: 10, upVx: 0.9, upVy: -7.6 },        // 띄움
    charge1: { dmg: 3, stop: 6,  flash: 6, shake: 5,  kbVx: 5.4, kbT: 42 },           // 넉백 (강)
    charge2: { dmg: 5, stop: 9,  flash: 8, shake: 9,  blowVx: 4.2, blowVy: -5.2 },    // 날아감
  };
  var SHOTS = {
    shot:    { w: 10, h: 6,  speed: 0, pierce: false },
    burst:   { w: 16, h: 10, speed: 0, pierce: false },
    charge1: { w: 16, h: 10, speed: 0, pierce: false },
    charge2: { w: 30, h: 20, speed: 2, pierce: true },
  };

  function total(d) { return d.anti + d.startup + d.active + d.recovery; }
  function fireTick(d) { return d.anti + d.startup; }
  // 지금 틱에 보여 줄 [상태 시트, 프레임]. 그림(render.js)과 테스트가 함께 쓴다.
  function animOf(act) {
    var d = ACTIONS[act.id], tl = (d.animMiss && !act.hit) ? d.animMiss : d.anim;
    for (var i = 0; i < tl.length; i++) if (act.t < tl[i][2]) return [tl[i][0], tl[i][1]];
    return [tl[tl.length - 1][0], tl[tl.length - 1][1]];
  }

  var PLATFORMS = [
    { x: 820, y: C.GROUND_Y - 44, w: 96, kind: 'crate' },
    { x: 1330, y: C.GROUND_Y - 60, w: 150, kind: 'container' },
  ];

  function rng(g) { // 결정적 난수 (테스트에서 항상 같은 결과)
    g.seed = (g.seed * 1664525 + 1013904223) >>> 0;
    return g.seed / 4294967296;
  }

  function makeEnemy(type, x, y) {
    var hp = type === 'drone' ? C.DRONE_HP : C.TROOPER_HP;
    return {
      type: type, x: x, y: y, baseY: y, vx: 0, vy: 0, facing: -1,
      hp: hp, maxHp: hp,
      state: 'idle', t: 0, cool: 60 + (x % 50), flash: 0, alive: true, anim: 0,
      onGround: type !== 'drone',
      juggle: 0, hitSeq: 0, dying: false,
    };
  }

  function createGame(opts) {
    opts = opts || {};
    var g = {
      C: C, platforms: PLATFORMS, frame: 0, seed: 12345,
      player: {
        x: 110, y: C.GROUND_Y, vx: 0, vy: 0, facing: 1, onGround: true,
        hp: C.PLAYER_HP, state: 'normal', stateT: 0, invuln: 0,
        act: null,                     // 지금 하는 공격 동작 { id, t, hit, hitList, level, target }
        chain: 0, chainT: 0,           // 기본 공격의 다음 타 (0 = 1타), 이어 칠 수 있는 남은 틱
        charging: false, chargeT: 0,   // 공격 버튼을 누르고 있는 동안 모인다
        bufAttack: 0, bufJump: 0,      // 입력 버퍼: 남은 틱
        bufCharge: 0, bufChargeT: 0,   // 기억해 둔 차지샷 단계와 남은 틱
        landT: 0, anim: 0, idleT: 0,
        melee: !!opts.melee,           // 무술 영화를 학습했는가
      },
      learned: ['locman'],             // 처음부터 LOCMAN 게임팩의 전투 데이터가 들어 있다
      enemies: [], shots: [], enemyShots: [], fx: [], pickups: [], events: [],
      prev: { left: false, right: false, jump: false, attack: false },
      camX: 0, hitstop: 0, shake: 0, freeze: 0,
      combo: 0, comboT: 0, kills: 0, launches: 0, chases: 0, cleared: false,
    };
    if (opts.empty) return g;          // 테스트용 빈 무대
    g.enemies.push(makeEnemy('trooper', 470, C.GROUND_Y));
    g.enemies.push(makeEnemy('trooper', 650, C.GROUND_Y));
    g.pickups.push({ kind: 'movie', x: 868, y: C.GROUND_Y - 44 - 16, taken: false });
    g.enemies.push(makeEnemy('trooper', 1160, C.GROUND_Y));
    g.enemies.push(makeEnemy('drone', 1300, C.GROUND_Y - 104));
    g.enemies.push(makeEnemy('trooper', 1520, C.GROUND_Y));
    g.enemies.push(makeEnemy('drone', 1640, C.GROUND_Y - 104));
    g.enemies.push(makeEnemy('trooper', 1780, C.GROUND_Y));
    g.events.push({ type: 'message', text: 'LOCMAN 게임팩 로드 완료 — 기본 공격 3타 · 차지샷', time: 240 });
    return g;
  }

  function emit(g, ev) { g.events.push(ev); }
  function fx(g, kind, x, y, extra) {
    var o = { kind: kind, x: x, y: y, t: 0, life: 18 };
    if (extra) for (var k in extra) o[k] = extra[k];
    g.fx.push(o);
  }

  // ───────────── 물리 (이동 · 점프 · 충돌. 전투 시스템은 이 부분을 건드리지 않는다) ─────────────
  function moveBody(g, b, hw) {
    b.vy = Math.min(b.vy + C.GRAVITY, C.MAX_FALL);
    b.x += b.vx;
    var prevY = b.y;
    b.y += b.vy;
    b.onGround = false;
    if (b.vy >= 0) {
      for (var i = 0; i < g.platforms.length; i++) {   // 위에서 내려올 때만 올라서는 발판
        var p = g.platforms[i];
        if (b.x > p.x - hw && b.x < p.x + p.w + hw && prevY <= p.y && b.y >= p.y) {
          b.y = p.y; b.vy = 0; b.onGround = true;
        }
      }
      if (b.y >= C.GROUND_Y) { b.y = C.GROUND_Y; b.vy = 0; b.onGround = true; }
    }
    if (b.x < 14) b.x = 14;
    if (b.x > C.STAGE_W - 14) b.x = C.STAGE_W - 14;
  }

  function centerY(e) { return e.type === 'drone' ? e.y : e.y - 38; }
  // 맞을 수 있는 상태인가. 다운 · 기상 중과, 체력이 0 이 되어 날아가는 중에는 맞지 않는다.
  function hittable(e) { return e.alive && !e.dying && e.state !== 'down' && e.state !== 'getup' && e.state !== 'dead' && e.state !== 'fall'; }

  // ───────────── 적이 맞았을 때: 공격의 종류와 지금 상태에 따라 다음 상태가 정해진다 ─────────────
  function launch(e, vx, vy) { e.state = 'launch'; e.t = 0; e.vx = vx; e.vy = vy; e.onGround = false; }

  function applyHit(g, e, kind, dir) {
    if (!hittable(e)) return null;
    var H = HITS[kind], air = e.state === 'launch', kb = e.state === 'knockback';
    var charge = kind === 'charge1' || kind === 'charge2';
    var dmg = H.dmg, tag = '';
    if (charge && air) { dmg = Math.ceil(dmg * C.AIR_CHASE_MULT); tag = 'air_chase'; }    // 띄운 적에게 차지샷 = 공중 추격
    else if (charge && kb) { dmg = Math.ceil(dmg * C.CHASE_MULT); tag = 'chase'; }        // 넉백된 적에게 차지샷 = 추격
    e.hp -= dmg; e.flash = H.flash; e.hitSeq++;
    g.combo++; g.comboT = 150;
    g.hitstop = Math.max(g.hitstop, H.stop + (tag ? 3 : 0));
    g.shake = Math.max(g.shake, H.shake + (tag ? 3 : 0));
    if (tag) g.chases++;

    if (e.type === 'drone') {            // 떠 있어서 띄울 수 없다: 경직 또는 넉백(공중에서 밀려난다)
      if (e.hp <= 0) { e.hp = 0; e.dying = true; g.kills++; e.state = 'fall'; e.t = 0; e.vx = dir * 1.6; e.vy = -1.5; fx(g, 'boom', e.x, e.y, { life: 20 }); }
      else if (kind === 'shot' && !kb) { e.state = 'stagger'; e.t = 14; e.vx = dir * 1.1; }
      else if (kind === 'shot') { e.t = Math.max(e.t, 12); }
      else { e.state = 'knockback'; e.t = 34; e.vx = dir * (tag ? 4.4 : 3.4); }
    } else {
      if (kind === 'knuckle') launch(e, dir * H.upVx, H.upVy);
      else if (air) {
        if (tag) { e.vx = dir * (kind === 'charge2' ? 7 : 5.5); e.vy = kind === 'charge2' ? -4.5 : -3.5; }   // 멀리 날려 보낸다
        else if (e.juggle < C.JUGGLE_MAX) {                                                                  // 저글: 조금 더 뜬다 (횟수가 늘수록 덜 뜬다)
          e.vy = Math.min(e.vy, kind === 'burst' ? -4.2 : -3.4 + 0.5 * e.juggle);
          e.vx = dir * (kind === 'burst' ? 2.4 : 0.8);
          e.juggle++;
        }
      }
      else if (tag === 'chase') launch(e, dir * (kind === 'charge2' ? 5 : 3.6), kind === 'charge2' ? -6.2 : -5.6);
      else if (kind === 'charge2') launch(e, dir * H.blowVx, H.blowVy);
      else if (kind === 'burst' || kind === 'charge1') { e.state = 'knockback'; e.t = H.kbT; e.vx = dir * H.kbVx; }
      else if (kb) { e.t = Math.max(e.t, 14); e.vx += dir * 0.6; }                        // 넉백 중의 기본탄: 조금 더 밀려난다
      else { e.state = 'stagger'; e.t = C.STAGGER; e.vx = dir * H.push; }
      e.facing = -dir;                                                                    // 맞은 쪽을 본다 (뒤로 밀려난다)
      if (e.hp <= 0) {                   // 쓰러진다: 서 있었으면 그 자리에서 날아간다
        e.hp = 0; e.dying = true; g.kills++;
        if (e.state !== 'launch') launch(e, dir * 2.2, -4.0);
      }
    }
    emit(g, { type: 'sfx', name: e.dying ? 'enemy_down' : tag ? 'chase' : kind === 'knuckle' ? 'punch_hit' : kind === 'burst' ? 'heavy_hit' : 'enemy_hit' });
    emit(g, { type: 'hit', kind: kind, tag: tag, state: e.state, dmg: dmg });
    return { dmg: dmg, tag: tag };
  }

  // ───────────── 플레이어 ─────────────
  function muzzle(p) { return { x: p.x + p.facing * C.MUZZLE_X, y: p.y - C.MUZZLE_Y }; }

  function shotsFree(g) {
    var mine = 0;
    for (var i = 0; i < g.shots.length; i++) if (g.shots[i].kind === 'shot') mine++;
    return mine < C.SHOT_MAX;
  }

  function fireShot(g, kind) {
    var p = g.player, m = muzzle(p), S = SHOTS[kind];
    // from = 쏜 동작. 판정에는 쓰지 않는다. 그림 쪽에서 캐릭터마다 다른 총구 높이에 탄을 그리는 데 쓴다 (render.js 의 shotDy)
    g.shots.push({ kind: kind, x: m.x, y: m.y, vx: p.facing * (C.SHOT_SPEED + S.speed), w: S.w, h: S.h, pierce: S.pierce, hit: [], from: p.act ? p.act.id : null });
    fx(g, 'muzzle', m.x, m.y, { life: kind === 'shot' ? 5 : 9, big: kind !== 'shot', dir: p.facing });
    emit(g, { type: 'sfx', name: kind === 'shot' ? 'shot' : kind === 'burst' ? 'burst' : 'charge_shot' });
    if (kind === 'charge2') g.shake = Math.max(g.shake, 5);
  }

  // 너클 펀치를 걸 수 있는 적: 땅에 서 있고(띄운 적은 아니다), 정면 MELEE_RANGE 안이거나 바로 등 뒤에 붙어 있다
  function findMeleeTarget(g) {
    var p = g.player, best = null, bestD = 1e9;
    for (var i = 0; i < g.enemies.length; i++) {
      var e = g.enemies[i];
      if (!hittable(e) || e.state === 'launch') continue;
      var dx = e.x - p.x, ahead = dx * p.facing;
      if (Math.abs(centerY(e) - (p.y - 38)) > 46) continue;
      if ((ahead >= 0 && ahead <= C.MELEE_RANGE) || Math.abs(dx) <= 18) {
        if (Math.abs(dx) < bestD) { bestD = Math.abs(dx); best = e; }
      }
    }
    return best;
  }

  function canCancel(p, what) {
    var a = p.act;
    if (!a) return true;
    var d = ACTIONS[a.id];
    if (d.cancelOnHit) return a.hit && d.cancelOnHit[what] !== undefined && a.t >= d.cancelOnHit[what];
    return d.cancel[what] !== undefined && a.t >= d.cancel[what];
  }

  function startAction(g, id, extra) {
    var p = g.player;
    p.act = { id: id, t: 0, hit: false, hitList: [], level: 0, target: null };
    if (extra) for (var k in extra) p.act[k] = extra[k];
  }

  // 입력을 기억한다. 타격 정지 중에도 부른다 (그때 누른 것도 잃지 않는다).
  function readInput(g, inp, frozen) {
    var p = g.player;
    var pressed = inp.attack && !g.prev.attack, released = !inp.attack && g.prev.attack;
    if (p.state === 'dead' || p.state === 'learn') { p.bufAttack = p.bufJump = p.bufCharge = p.bufChargeT = 0; p.charging = false; p.chargeT = 0; return; }
    if (pressed) { p.bufAttack = C.BUFFER; p.charging = true; p.chargeT = 0; }
    else if (!frozen && p.bufAttack > 0) p.bufAttack--;
    if (inp.jump && !g.prev.jump) p.bufJump = C.BUFFER;
    else if (!frozen && p.bufJump > 0) p.bufJump--;
    if (p.charging && inp.attack) {                    // 누르고 있는 동안 모인다 (동작 중에도, 타격 정지 중에도)
      p.chargeT++;
      if (p.chargeT === C.CHARGE_MID) emit(g, { type: 'sfx', name: 'charge_mid' });
      if (p.chargeT === C.CHARGE_FULL) emit(g, { type: 'sfx', name: 'charge_full' });
    }
    if (released && p.charging) {
      var lvl = p.chargeT >= C.CHARGE_FULL ? 2 : p.chargeT >= C.CHARGE_MID ? 1 : 0;
      p.charging = false; p.chargeT = 0;
      if (lvl) { p.bufCharge = lvl; p.bufChargeT = C.CHARGE_BUFFER; }
    } else if (!frozen && p.bufChargeT > 0 && --p.bufChargeT === 0) p.bufCharge = 0;
  }

  function stepKnuckle(g, a, d) {
    var p = g.player, t = a.t, hitT = fireTick(d), i;
    if (t < hitT + d.active + 6) p.invuln = Math.max(p.invuln, 2);     // 준비부터 판정 뒤 6틱까지는 맞지 않는다
    if (t < d.stepIn && a.target) {                                    // 파고들기: 적 앞 34px 까지
      var gap = (a.target.x - p.x) * p.facing - 34;
      if (gap > 0) p.vx = p.facing * Math.min(gap / Math.max(1, d.stepIn - t), 7);
    }
    if (t === d.stepIn) emit(g, { type: 'sfx', name: 'arm' });          // 너클 전개
    if (t >= hitT && t < hitT + d.active) {                            // 판정: 주먹이 닿은 적마다 한 번
      var cx = p.x + p.facing * (C.FIST.x0 + C.FIST.x1) / 2, cy = p.y - (C.FIST.y0 + C.FIST.y1) / 2;
      var hw = (C.FIST.x1 - C.FIST.x0) / 2, hh = (C.FIST.y1 - C.FIST.y0) / 2;
      for (i = 0; i < g.enemies.length; i++) {
        var e = g.enemies[i];
        if (!hittable(e) || a.hitList.indexOf(e) >= 0) continue;
        var ew = e.type === 'drone' ? 20 : 12, eh = e.type === 'drone' ? 14 : 36;
        if (Math.abs(e.x - cx) >= hw + ew || Math.abs(centerY(e) - cy) >= hh + eh) continue;
        applyHit(g, e, 'knuckle', p.facing);
        a.hitList.push(e);
        if (!a.hit) {                                                  // 조건 충족 → 연출 보상
          a.hit = true; g.launches++;
          if (p.charging && p.chargeT < C.CHARGE_MID) {                // 누른 채로 맞혔다 → 차지가 1단까지 바로 찬다 (띄운 적을 바로 쏠 수 있게)
            p.chargeT = C.CHARGE_MID; emit(g, { type: 'sfx', name: 'charge_mid' });
          }
          var bx = p.x + p.facing * (C.FIST_X + 6), by = p.y - C.FIST_Y;
          fx(g, 'boom', bx, by, { life: 30, big: true });
          fx(g, 'ring', bx, by, { life: 24 });
          fx(g, 'text', bx, by - 44, { life: 50, text: 'LAUNCH' });
        }
      }
      if (t === hitT + d.active - 1 && !a.hit) {
        fx(g, 'spark', p.x + p.facing * C.FIST_X, p.y - C.FIST_Y, { life: 8 });
        emit(g, { type: 'sfx', name: 'whiff' });
      }
    }
    if (t === hitT + 20) { fx(g, 'dust', p.x, p.y, { life: 18 }); emit(g, { type: 'sfx', name: 'steam' }); }   // 배기
  }

  function hurtPlayer(g, dmg, dir) {
    var p = g.player;
    if (p.invuln > 0 || p.state === 'dead' || p.state === 'learn') return false;
    p.hp -= dmg; g.combo = 0; g.comboT = 0;
    p.act = null; p.chain = 0; p.charging = false; p.chargeT = 0;
    p.bufAttack = p.bufJump = p.bufCharge = p.bufChargeT = 0;
    emit(g, { type: 'sfx', name: 'hurt' });
    if (p.hp <= 0) {
      p.hp = 0; p.state = 'dead'; p.stateT = 0; p.vx = dir * 2.4; p.vy = -4;
      emit(g, { type: 'message', text: '기능 정지 — R 키로 다시 시작', time: 600 });
    } else {
      p.state = 'hurt'; p.stateT = 18; p.vx = dir * 2.2; p.vy = -2.6; p.invuln = C.INVULN;
    }
    g.shake = Math.max(g.shake, 6);
    return true;
  }

  function stepPlayer(g, inp) {
    var p = g.player;
    if (p.invuln > 0) p.invuln--;
    if (p.landT > 0) p.landT--;
    p.anim++;
    var idleT = p.idleT;                               // 가만히 서 있은 틱 수. 아래에서 여전히 가만히 있을 때만 이어 센다
    p.idleT = 0;
    if (p.chainT > 0 && --p.chainT === 0) p.chain = 0; // 다음 타로 이어 갈 시간이 지났다 → 1타부터

    if (p.state === 'dead') {
      p.stateT++; p.vx *= 0.94; moveBody(g, p, 10); return;
    }
    if (p.state === 'learn') {                       // 데이터 학습 중: 움직이지 않는다
      p.vx = 0; p.stateT--;
      moveBody(g, p, 10);
      if (p.stateT <= 0) {
        p.state = 'normal'; p.melee = true; g.learned.push('movie');
        emit(g, { type: 'learned', what: 'melee' });
        emit(g, { type: 'message', text: '무술 영화 학습 완료 — 너클 펀치 해금. 붙어서 공격하면 적을 띄운다!', time: 300 });
        emit(g, { type: 'sfx', name: 'learned' });
      }
      return;
    }
    if (p.state === 'hurt') {
      p.stateT--; p.vx *= 0.9; moveBody(g, p, 10);
      if (p.stateT <= 0) p.state = 'normal';
      return;
    }

    var dir = (inp.right ? 1 : 0) - (inp.left ? 1 : 0), id;

    // ── 다음 동작으로 넘어가기: 기억해 둔 입력을, 캔슬 창이 열려 있을 때만 쓴다 ──
    if (p.bufCharge && canCancel(p, 'charge')) {                       // 차지샷 (떼는 입력)
      var lvl = p.bufCharge;
      p.bufCharge = 0; p.bufChargeT = 0;
      if (dir !== 0) p.facing = dir;
      startAction(g, p.onGround ? 'charge' + lvl : 'air_charge', { level: lvl });
      p.chain = 0; p.chainT = 0;
    } else if (p.bufAttack > 0) {                                      // 공격 (누르는 입력)
      var target = (p.melee && p.onGround && canCancel(p, 'knuckle')) ? findMeleeTarget(g) : null;
      if (target) {                                                    // 주먹이 닿는 거리 → 너클 펀치
        p.bufAttack = 0;
        if (target.x !== p.x) p.facing = target.x > p.x ? 1 : -1;
        startAction(g, 'knuckle', { target: target });
        p.chain = 0; p.chainT = 0;
        emit(g, { type: 'sfx', name: 'punch_start' });
      } else if (canCancel(p, 'attack') && (shotsFree(g) || p.chain === 2)) {   // 기본 공격: 1타 → 2타 → 3타
        p.bufAttack = 0;
        if (dir !== 0) p.facing = dir;
        id = p.onGround ? CHAIN[p.chain] : (p.chain === 2 ? 'air_burst' : 'air_shot');
        startAction(g, id);
        p.chain = (p.chain + 1) % 3;
        p.chainT = p.chain === 0 ? 0 : total(ACTIONS[id]) + C.CHAIN_KEEP;
      }
    }
    if (p.bufJump > 0 && p.onGround && canCancel(p, 'jump')) {         // 점프 (점프 캔슬 포함)
      p.bufJump = 0; p.act = null;
      p.vy = C.JUMP_V; p.onGround = false;
      emit(g, { type: 'sfx', name: 'jump' });
    }

    // ── 이동: 지상 동작은 '이동' 캔슬 틱까지 발이 묶인다 ──
    var a = p.act, d = a && ACTIONS[a.id];
    if (a && d.root && dir !== 0 && canCancel(p, 'move')) { p.act = null; a = null; d = null; }
    if (a && d.root) p.vx = 0;
    else { p.vx = dir * C.WALK; if (!a && dir !== 0) p.facing = dir; }
    if (!inp.jump && p.vy < -2.4) p.vy = -2.4;      // 버튼을 일찍 떼면 낮게 뛴다

    // ── 동작의 한 틱: 판정이 나오는 틱에 탄을 쏘거나 주먹 판정을 낸다 ──
    if (a) {
      if (a.id === 'knuckle') stepKnuckle(g, a, d);
      else if (a.t === fireTick(d)) fireShot(g, d.fire === 'charge' ? 'charge' + a.level : d.fire);
      a.t++;
      if (a.t >= total(d)) p.act = null;
    }

    var wasAir = !p.onGround;
    moveBody(g, p, 10);
    if (wasAir && p.onGround) {
      p.landT = 6;
      if (p.act && ACTIONS[p.act.id].air) p.act = null;               // 공중 동작은 착지하면 끝난다
    }
    if (p.onGround && dir === 0 && !p.act && !p.charging && p.landT === 0) p.idleT = idleT + 1;

    // 아이템
    for (var i = 0; i < g.pickups.length; i++) {
      var k = g.pickups[i];
      if (k.taken) continue;
      if (Math.abs(k.x - p.x) < 20 && Math.abs(k.y - (p.y - 30)) < 40) {
        k.taken = true;
        if (k.kind === 'movie' && !p.melee) {
          p.state = 'learn'; p.stateT = C.LEARN_TIME; p.act = null; p.charging = false; p.chargeT = 0; p.vx = 0;
          g.freeze = C.LEARN_TIME;
          emit(g, { type: 'learn_start', what: 'movie' });
          emit(g, { type: 'message', text: '무술 영화 발견 — 데이터 학습 중…', time: C.LEARN_TIME });
          emit(g, { type: 'sfx', name: 'pickup' });
        }
      }
    }
  }

  // ───────────── 적 ─────────────
  function stepDrone(g, e, dx, dist) {
    var p = g.player;
    if (e.state === 'fall') {                          // 격추: 떨어져서 터진다
      e.t++;
      e.vy = Math.min(e.vy + C.GRAVITY, C.MAX_FALL); e.x += e.vx; e.y += e.vy;
      if (e.y >= C.GROUND_Y - 10) {
        fx(g, 'boom', e.x, C.GROUND_Y - 12, { life: 24, big: true });
        emit(g, { type: 'sfx', name: 'explode' });
        e.alive = false; e.state = 'dead';
      }
      return;
    }
    e.y = e.baseY + Math.sin((g.frame + e.baseY) / 22) * 5;
    if (e.state === 'stagger' || e.state === 'knockback') {            // 공중에서 멈칫하거나 밀려난다
      e.t--; e.x += e.vx; e.vx *= e.state === 'stagger' ? 0.85 : 0.93;
      e.x = Math.max(14, Math.min(C.STAGE_W - 14, e.x));
      if (e.t <= 0) { e.state = 'idle'; e.vx = 0; }
      return;
    }
    if (dx !== 0) e.facing = dx > 0 ? 1 : -1;
    if (dist < 340) {
      e.x += dist > 150 ? e.facing * 0.9 : 0;
      if (e.state === 'idle') { e.cool--; if (e.cool <= 0) { e.state = 'aim'; e.t = 24; } }
      else if (e.state === 'aim') {
        e.t--;
        if (e.t <= 0) {
          var tx = p.x - e.x, ty = (p.y - 40) - e.y, len = Math.sqrt(tx * tx + ty * ty) || 1;
          g.enemyShots.push({ kind: 'laser', x: e.x + e.facing * 16, y: e.y + 4, vx: tx / len * 3.4, vy: ty / len * 3.4, dmg: 1 });
          emit(g, { type: 'sfx', name: 'enemy_shot' });
          e.state = 'recoil'; e.t = 16; e.cool = 120 + Math.floor(rng(g) * 60);
        }
      } else if (e.state === 'recoil') { e.t--; if (e.t <= 0) e.state = 'idle'; }
    }
  }

  function stepEnemy(g, e) {
    var p = g.player;
    if (e.flash > 0) e.flash--;
    e.anim++;
    var dx = p.x - e.x, dist = Math.abs(dx);
    if (e.type === 'drone') { stepDrone(g, e, dx, dist); return; }

    // 지상형(NX 양산형)의 리액션 상태. 4.3 의 전이도와 같다.
    if (e.state === 'stagger') {                       // 경직: 움직이지도 쏘지도 못한다
      e.t--; e.vx *= 0.8; moveBody(g, e, 10);
      if (e.t <= 0) { e.state = 'idle'; e.vx = 0; e.cool = Math.max(e.cool, 24); }
      return;
    }
    if (e.state === 'knockback') {                     // 넉백: 뒤로 밀려나며 미끄러진다
      e.t--; e.vx *= 0.93; moveBody(g, e, 10);
      if (e.t % 7 === 0 && Math.abs(e.vx) > 0.6) fx(g, 'dust', e.x, e.y, { life: 12 });
      if (e.t <= 0) { e.state = 'idle'; e.vx = 0; e.cool = Math.max(e.cool, 30); }
      return;
    }
    if (e.state === 'launch') {                        // 띄움 · 날아감: 땅에 닿으면 다운
      e.t++; moveBody(g, e, 10);
      if (e.onGround && e.t > 3) {
        e.state = 'down'; e.t = e.dying ? C.DEAD_TIME : C.DOWN_TIME; e.vx = 0; e.juggle = 0;
        g.shake = Math.max(g.shake, 4);
        fx(g, 'dust', e.x, e.y, { life: 16 });
        emit(g, { type: 'sfx', name: 'land' });
      }
      return;
    }
    if (e.state === 'down') {
      e.t--;
      if (e.t <= 0) {
        if (e.dying) { e.alive = false; e.state = 'dead'; }
        else { e.state = 'getup'; e.t = C.GETUP_TIME; }
      }
      return;
    }
    if (e.state === 'getup') { e.t--; if (e.t <= 0) { e.state = 'idle'; e.cool = Math.max(e.cool, 40); } return; }

    // 서 있음: 다가오기 → 조준 → 사격 (인공지능은 예전 그대로다)
    if (dx !== 0) e.facing = dx > 0 ? 1 : -1;
    e.vx = 0;
    if (dist < 330) {
      var level = Math.abs(e.y - p.y) < 50;
      if (e.state === 'idle') {
        if (dist > 190) e.vx = e.facing * 0.7;
        e.cool--;
        if (e.cool <= 0 && level && dist < 300) { e.state = 'aim'; e.t = 26; }
      } else if (e.state === 'aim') {
        e.t--;
        if (e.t <= 0) {
          g.enemyShots.push({ kind: 'bullet', x: e.x + e.facing * C.MUZZLE_X, y: e.y - C.MUZZLE_Y, vx: e.facing * 3.2, vy: 0, dmg: 1 });
          emit(g, { type: 'sfx', name: 'enemy_shot' });
          e.state = 'recoil'; e.t = 20; e.cool = 100 + Math.floor(rng(g) * 70);
        }
      } else if (e.state === 'recoil') { e.t--; if (e.t <= 0) e.state = 'idle'; }
    }
    moveBody(g, e, 10);
  }

  // ───────────── 탄 ─────────────
  var TAG_TEXT = { chase: 'CHASE', air_chase: 'AIR CHASE' };
  function stepShots(g) {
    var p = g.player, i, j;
    for (i = g.shots.length - 1; i >= 0; i--) {
      var s = g.shots[i];
      s.x += s.vx;
      var gone = s.x < g.camX - 40 || s.x > g.camX + C.VIEW_W + 40;
      for (j = 0; j < g.enemies.length && !gone; j++) {
        var e = g.enemies[j];
        if (!hittable(e) || s.hit.indexOf(e) >= 0) continue;
        var hw = e.type === 'drone' ? 20 : 12, hh = e.type === 'drone' ? 14 : 36;
        if (Math.abs(s.x - e.x) < hw + s.w / 2 && Math.abs(s.y - centerY(e)) < hh + s.h / 2) {
          var res = applyHit(g, e, s.kind, s.vx > 0 ? 1 : -1);
          fx(g, 'spark', s.x, s.y, { life: s.kind === 'shot' ? 8 : 12, big: s.kind !== 'shot' });
          if (res && res.tag) {
            fx(g, 'boom', e.x, centerY(e), { life: 22 });
            fx(g, 'text', e.x, centerY(e) - 46, { life: 46, text: TAG_TEXT[res.tag] });
          }
          s.hit.push(e);
          if (!s.pierce) gone = true;
        }
      }
      if (gone) g.shots.splice(i, 1);
    }
    for (i = g.enemyShots.length - 1; i >= 0; i--) {
      var b = g.enemyShots[i];
      b.x += b.vx; b.y += b.vy;
      var out = b.x < g.camX - 60 || b.x > g.camX + C.VIEW_W + 60 || b.y > C.GROUND_Y + 4 || b.y < -40;
      if (!out && Math.abs(b.x - p.x) < 13 && b.y > p.y - 70 && b.y < p.y) {
        if (hurtPlayer(g, b.dmg, b.vx > 0 ? 1 : -1)) { fx(g, 'spark', b.x, b.y, { life: 8, red: true }); out = true; }
      }
      if (out) g.enemyShots.splice(i, 1);
    }
  }

  // ───────────── 한 프레임 ─────────────
  function step(g, inp) {
    inp = inp || {};
    var i;
    g.frame++;
    for (i = g.fx.length - 1; i >= 0; i--) { g.fx[i].t++; if (g.fx[i].t >= g.fx[i].life) g.fx.splice(i, 1); }
    if (g.shake > 0) g.shake--;

    if (g.hitstop > 0) {             // 타격 정지: 연출만 흐르고 나머지는 멈춘다. 입력은 기억하고 차지는 계속 모인다
      g.hitstop--;
      readInput(g, inp, true);
      g.prev = { left: !!inp.left, right: !!inp.right, jump: !!inp.jump, attack: !!inp.attack };
      return g;
    }

    readInput(g, inp, false);
    stepPlayer(g, inp);
    if (g.freeze > 0) g.freeze--;
    else {
      for (i = 0; i < g.enemies.length; i++) if (g.enemies[i].alive) stepEnemy(g, g.enemies[i]);
      stepShots(g);
    }
    for (i = g.enemies.length - 1; i >= 0; i--) if (!g.enemies[i].alive) g.enemies.splice(i, 1);

    if (g.comboT > 0) { g.comboT--; if (g.comboT === 0) g.combo = 0; }
    if (!g.cleared && g.enemies.length === 0 && g.kills > 0) {
      g.cleared = true;
      emit(g, { type: 'message', text: '전투 테스트 완료 — R: 다시 시작 / 2: 적 소환', time: 900 });
    }

    var target = Math.max(0, Math.min(C.STAGE_W - C.VIEW_W, g.player.x - C.VIEW_W * 0.4));
    g.camX += (target - g.camX) * 0.14;
    g.prev = { left: !!inp.left, right: !!inp.right, jump: !!inp.jump, attack: !!inp.attack };
    return g;
  }

  // 테스트·디버그용
  function spawn(g, type, x, y) {
    var e = makeEnemy(type, x, y === undefined ? (type === 'drone' ? C.GROUND_Y - 104 : C.GROUND_Y) : y);
    g.enemies.push(e); g.cleared = false;
    return e;
  }

  var api = {
    C: C, ACTIONS: ACTIONS, HITS: HITS, CHAIN: CHAIN, PLATFORMS: PLATFORMS,
    createGame: createGame, step: step, spawn: spawn, muzzle: muzzle, findMeleeTarget: findMeleeTarget,
    hittable: hittable, isUp: hittable, animOf: animOf, total: total, fireTick: fireTick, canCancel: canCancel,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else { root.SALVAGE = root.SALVAGE || {}; root.SALVAGE.sim = api; }
})(typeof window !== 'undefined' ? window : globalThis);
