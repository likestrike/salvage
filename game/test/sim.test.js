/* 전투 로직 테스트 — node game/test/sim.test.js
 *
 * 전투 시스템(docs/GAME_DESIGN.md 4.3)의 검증 기준을 그대로 옮긴 것이다.
 */
'use strict';
const assert = require('node:assert');
const sim = require('../src/sim.js');
const C = sim.C, A = sim.ACTIONS, H = sim.HITS;

function run(g, frames, inp) { for (let i = 0; i < frames; i++) sim.step(g, inp || {}); return g; }
function tap(g, extra) { sim.step(g, Object.assign({ attack: true }, extra)); sim.step(g, extra || {}); }
function arena(opts) { return sim.createGame(Object.assign({ empty: true }, opts)); }
function dummy(g, x, type) { const e = sim.spawn(g, type || 'trooper', x); e.cool = 99999; return e; }   // 쏘지 않는 적
function actId(g) { return g.player.act ? g.player.act.id : null; }
function hits(g) { return g.events.filter(ev => ev.type === 'hit'); }
// 조건이 될 때까지 진행한다 (타격 정지로 틱 수가 달라지므로 틱을 세지 않고 상태를 본다)
function until(g, cond, inp, limit) {
  for (let i = 0; i < (limit || 400); i++) { if (cond()) return i; sim.step(g, typeof inp === 'function' ? inp() : (inp || {})); }
  assert.fail('조건이 되지 않았다: ' + cond);
}

const tests = [];
function test(name, fn) { tests.push([name, fn]); }

// ───────────── 기본 공격 ─────────────
test('공격을 누르면 기본 1타가 시작되고, 시동 3틱 뒤에 탄이 나간다', () => {
  const g = arena();
  sim.step(g, { attack: true });
  assert.strictEqual(actId(g), 'shot1');
  assert.strictEqual(g.shots.length, 0, '시동 중에는 아직 탄이 없다');
  run(g, 3);
  assert.strictEqual(g.shots.length, 1);
  assert.strictEqual(g.shots[0].kind, 'shot');
  assert.ok(g.shots[0].vx > 0, '바라보는 쪽으로 날아간다');
});

test('[검증 1] 기본 공격 3타가 이어진다: 1타 → 2타 → 3타(마무리탄), 적은 경직 → 경직 → 넉백', () => {
  const g = arena(), e = dummy(g, 300), seen = [];
  for (let n = 0; n < 3; n++) { tap(g); seen.push(actId(g)); run(g, 7); }
  assert.deepStrictEqual(seen, ['shot1', 'shot2', 'shot3']);
  until(g, () => hits(g).length === 3);
  assert.deepStrictEqual(hits(g).map(h => h.kind + '>' + h.state), ['shot>stagger', 'shot>stagger', 'burst>knockback']);
  assert.strictEqual(e.hp, C.TROOPER_HP - 4);
  assert.ok(e.x > 300, '넉백으로 뒤로 밀려났다');
});

test('3타 뒤에는 다시 1타부터 시작한다', () => {
  const g = arena(), seen = [];
  for (let n = 0; n < 3; n++) { tap(g); run(g, 7); }
  until(g, () => !g.player.act);
  tap(g); seen.push(actId(g));
  assert.deepStrictEqual(seen, ['shot1']);
});

test('늦게 누르면 이어지지 않고 1타부터 다시 나간다', () => {
  const g = arena();
  tap(g);
  run(g, sim.total(A.shot1) + C.CHAIN_KEEP + 2);
  tap(g);
  assert.strictEqual(actId(g), 'shot1');
});

test('누르고만 있으면 다음 타가 자동으로 나가지 않는다 (차지만 모인다)', () => {
  const g = arena(), seen = new Set();
  for (let i = 0; i < 40; i++) { sim.step(g, { attack: true }); if (g.player.act) seen.add(g.player.act.id); }
  assert.deepStrictEqual([...seen], ['shot1']);
  assert.strictEqual(g.shots.length + g.events.filter(ev => ev.type === 'sfx' && ev.name === 'shot').length >= 1, true);
  assert.ok(g.player.chargeT >= C.CHARGE_MID, '차지가 모였다');
});

test('화면에 기본탄이 세 발 있으면 네 번째는 나가지 않는다', () => {
  const g = arena();
  g.player.chain = 0;
  for (let i = 0; i < 3; i++) g.shots.push({ kind: 'shot', x: 300 + i * 20, y: 250, vx: 0, w: 10, h: 6, pierce: false, hit: [] });
  tap(g);
  assert.strictEqual(actId(g), null);
});

// ───────────── 입력 버퍼와 캔슬 창 ─────────────
test('[검증 6] 동작 중에 미리 누른 공격은 캔슬 창이 열리는 틱에 나간다 (입력을 잃지 않는다)', () => {
  const g = arena(), log = [];
  const inputs = [{ attack: true }, {}, {}, {}, { attack: true }, {}];      // 1타를 누르고, 4틱째(창이 열리기 전)에 한 번 더
  for (let i = 0; i < 14; i++) {
    sim.step(g, inputs[i] || {});
    log.push(actId(g) + ':' + (g.player.act ? g.player.act.t : '-'));
  }
  const first2 = log.findIndex(v => v.startsWith('shot2'));
  assert.strictEqual(first2, A.shot1.cancel.attack, '2타는 1타의 캔슬 창(8틱)에서 시작한다: ' + log.join(' '));
  assert.ok(log.slice(0, first2).every(v => v.startsWith('shot1')), '그 전에는 1타가 끝까지 이어진다');
});

test('캔슬 창이 열리기 전에는 점프로도 끊기지 않는다', () => {
  const g = arena();
  sim.step(g, { attack: true });
  sim.step(g, { jump: true });
  run(g, 3, { jump: true });
  assert.strictEqual(actId(g), 'shot1');
  assert.ok(g.player.onGround, '아직 땅에 있다');
  until(g, () => !g.player.onGround, { jump: true }, 20);
  assert.strictEqual(actId(g), null, '창이 열리자 점프로 넘어갔다');
});

test('타격 정지 중에 누른 입력도 기억한다', () => {
  const g = arena();
  g.hitstop = 5;
  sim.step(g, { attack: true });
  run(g, 4);
  assert.strictEqual(actId(g), null, '정지 중에는 시작하지 않는다');
  run(g, 2);
  assert.strictEqual(actId(g), 'shot1');
});

test('지상에서 쏘는 동안은 발이 묶이고, 이동 캔슬 틱부터 다시 움직인다', () => {
  const g = arena(), x0 = g.player.x;
  sim.step(g, { attack: true, right: true });
  run(g, A.shot1.cancel.move - 1, { right: true });
  assert.strictEqual(g.player.x, x0, '이동 캔슬 전에는 제자리');
  run(g, 3, { right: true });
  assert.ok(g.player.x > x0, '이동 캔슬 뒤에는 걷는다');
  assert.strictEqual(actId(g), null);
});

// ───────────── 차지샷 ─────────────
test('짧게 누르고 떼면 차지샷이 나가지 않는다', () => {
  const g = arena();
  run(g, C.CHARGE_MID - 2, { attack: true });
  run(g, 30, {});
  assert.deepStrictEqual(g.events.filter(ev => ev.type === 'sfx' && /shot/.test(ev.name)).map(ev => ev.name), ['shot']);
});

test('누르고 있다가 떼면 차지샷 1단, 끝까지 모으면 관통하는 2단이 나간다', () => {
  let g = arena();
  run(g, C.CHARGE_MID + 2, { attack: true }); run(g, 1, {});
  assert.strictEqual(actId(g), 'charge1');
  until(g, () => g.shots.some(s => s.kind === 'charge1'));
  g = arena(); dummy(g, 300); dummy(g, 380);
  run(g, C.CHARGE_FULL + 2, { attack: true }); run(g, 1, {});
  assert.strictEqual(actId(g), 'charge2');
  until(g, () => hits(g).filter(h => h.kind === 'charge2').length === 2);
  assert.ok(true, '한 줄로 선 적 둘을 관통한다');
});

// ───────────── 너클 펀치 ─────────────
test('근접을 배우기 전에는 적이 붙어 있어도 총을 쏜다', () => {
  const g = arena(); dummy(g, g.player.x + 50);
  tap(g);
  assert.strictEqual(actId(g), 'shot1');
});

test('무술 영화를 주우면 학습을 거쳐 너클 펀치가 열린다', () => {
  const g = arena();
  g.pickups.push({ kind: 'movie', x: g.player.x + 6, y: C.GROUND_Y - 16, taken: false });
  run(g, 2);
  assert.strictEqual(g.player.state, 'learn');
  run(g, C.LEARN_TIME + 2);
  assert.strictEqual(g.player.state, 'normal');
  assert.ok(g.player.melee);
  assert.deepStrictEqual(g.learned, ['locman', 'movie']);
});

test('[검증 2] 붙어서 공격하면 너클 펀치가 적을 띄운다 (띄움 → 다운 → 기상 → 다시 서 있음)', () => {
  const g = arena({ melee: true }), e = dummy(g, g.player.x + 50);
  tap(g);
  assert.strictEqual(actId(g), 'knuckle');
  until(g, () => hits(g).length === 1);
  assert.strictEqual(hits(g)[0].kind + '>' + hits(g)[0].state, 'knuckle>launch');
  assert.strictEqual(e.hp, C.TROOPER_HP - H.knuckle.dmg, '한 방에 쓰러뜨리지 않는다');
  let top = 0;
  until(g, () => { top = Math.max(top, C.GROUND_Y - e.y); return e.state === 'down'; });
  assert.ok(top > 50, '공중으로 떴다: ' + top.toFixed(0) + 'px');
  until(g, () => e.state === 'getup');
  until(g, () => e.state === 'idle');
});

test('너클의 판정은 준비 12 + 시동 6 = 18틱째에 나오고, 그 틱에 기폭 프레임이 보인다', () => {
  const g = arena({ melee: true }); dummy(g, g.player.x + 40);
  sim.step(g, { attack: true });
  const t = until(g, () => hits(g).length === 1);
  assert.strictEqual(t, sim.fireTick(A.knuckle), '판정 틱');
  assert.deepStrictEqual(sim.animOf(g.player.act), ['melee', 4]);
});

test('너클은 가슴 높이로 친다: 머리 위의 드론에게는 닿지 않고, 드론만 있으면 총을 쏜다', () => {
  let g = arena({ melee: true });
  const tr = dummy(g, g.player.x + 44), dr = dummy(g, g.player.x + 40, 'drone');
  tap(g);
  until(g, () => !g.player.act);
  assert.ok(tr.hp < C.TROOPER_HP, '지상의 적은 맞았다');
  assert.strictEqual(dr.hp, C.DRONE_HP, '머리 위의 드론은 맞지 않았다');
  g = arena({ melee: true }); dummy(g, g.player.x + 30, 'drone');
  tap(g);
  assert.strictEqual(actId(g), 'shot1');
});

test('빗나간 너클은 캔슬할 수 없고, 폭발 프레임 없이 끝난다', () => {
  const g = arena({ melee: true }), e = dummy(g, g.player.x + 50), frames = new Set();
  sim.step(g, { attack: true });
  e.x += 400;                                         // 누른 뒤 적이 사라졌다
  for (let i = 0; i < 60 && g.player.act; i++) {
    frames.add(sim.animOf(g.player.act).join(':'));
    sim.step(g, i > 20 ? { jump: true } : {});
  }
  assert.ok(g.player.onGround || g.player.act === null);
  assert.ok(!frames.has('melee:4') && !frames.has('melee:5'), '기폭 · 충격파 프레임이 나오지 않았다');
  assert.strictEqual(hits(g).length, 0);
});

test('너클 동작 중에는 맞지 않는다', () => {
  const g = arena({ melee: true }); dummy(g, g.player.x + 50);
  tap(g);
  g.enemyShots.push({ kind: 'bullet', x: g.player.x + 4, y: g.player.y - 30, vx: 0, vy: 0, dmg: 1 });
  run(g, 4);
  assert.strictEqual(g.player.hp, C.PLAYER_HP);
});

test('등 뒤에 바짝 붙은 적도 돌아서서 친다', () => {
  const g = arena({ melee: true }), e = dummy(g, g.player.x - 14);
  tap(g);
  assert.strictEqual(actId(g), 'knuckle');
  assert.strictEqual(g.player.facing, -1);
  until(g, () => hits(g).length === 1);
  assert.strictEqual(e.state, 'launch');
});

// ───────────── 연결: 적의 상태가 다음 공격의 기회가 된다 ─────────────
test('[검증 3] 띄운 적에게 차지샷: 펀치를 누른 채로 있다가 떼면 공중 추격(피해 2배)이 들어간다', () => {
  const g = arena({ melee: true }), e = dummy(g, g.player.x + 50);
  until(g, () => g.player.act && g.player.act.hit, { attack: true });                         // 누른 채로 펀치가 맞을 때까지
  run(g, 1, {});                                                                               // 맞자마자 뗀다 (창이 열리기 전 → 버퍼)
  until(g, () => actId(g) === 'charge1', {}, 20);
  until(g, () => hits(g).length === 2);
  const h = hits(g)[1];
  assert.strictEqual(h.tag, 'air_chase');
  assert.strictEqual(h.dmg, H.charge1.dmg * C.AIR_CHASE_MULT);
  assert.strictEqual(e.hp, C.TROOPER_HP - H.knuckle.dmg - h.dmg);
});

test('[검증 4] 넉백된 적을 차지샷으로 추격: 3타를 누른 채로 있다가 떼면 추격(피해 1.5배)이 들어간다', () => {
  const g = arena(), e = dummy(g, 300);
  tap(g); run(g, 7); tap(g); run(g, 7);
  until(g, () => g.player.chargeT >= C.CHARGE_MID + 1, { attack: true });                      // 3타를 누른 채로
  assert.strictEqual(actId(g), 'shot3');
  run(g, 1, {});
  until(g, () => actId(g) === 'charge1', {}, 20);
  until(g, () => hits(g).length === 4);
  const h = hits(g)[3];
  assert.strictEqual(hits(g)[2].state, 'knockback', '3타에 넉백');
  assert.strictEqual(h.tag, 'chase', '넉백 중에 차지샷이 닿았다');
  assert.strictEqual(h.dmg, Math.ceil(H.charge1.dmg * C.CHASE_MULT));
  assert.strictEqual(h.state, 'launch', '추격당한 적은 날아간다');
});

test('[검증 5] 공중 조합: 펀치로 띄우고 점프 캔슬 → 공중 기본탄으로 저글 → 공중 마무리탄', () => {
  const g = arena({ melee: true }), e = dummy(g, g.player.x + 50), air = [];
  tap(g);
  until(g, () => g.player.act && g.player.act.hit);
  until(g, () => !g.player.onGround, { jump: true }, 40);                                      // 점프를 미리 눌러 둔다 → 창에서 점프 캔슬
  assert.ok(g.player.act === null && e.state === 'launch');
  for (let n = 0; n < 3; n++) { tap(g, { jump: true }); air.push(actId(g)); until(g, () => sim.canCancel(g.player, 'attack'), { jump: true }, 20); }
  assert.deepStrictEqual(air, ['air_shot', 'air_shot', 'air_burst']);
  assert.ok(!g.player.onGround, '세 발 모두 공중에서 쐈다');
  until(g, () => hits(g).length >= 3, { jump: true }, 60);
  const airHits = hits(g).slice(1);
  assert.ok(airHits.every(h => h.state === 'launch'), '띄운 적이 떠 있는 동안 맞았다');
  assert.ok(e.juggle >= 2, '저글 횟수 ' + e.juggle);
});

test('공중에서도 차지샷이 나가고, 떠 있는 적에게 맞으면 공중 추격이다', () => {
  const g = arena(), e = dummy(g, g.player.x + 120);
  sim.step(g, { jump: true });
  assert.ok(!g.player.onGround);
  run(g, C.CHARGE_MID + 2, { jump: true, attack: true });                                      // 공중에서 누른 채로 (처음 누를 때 공중 기본탄이 나간다)
  e.state = 'launch'; e.onGround = false; e.y = g.player.y - 4; e.vy = -1; e.vx = 0;           // 적을 같은 높이에 띄워 둔다
  run(g, 1, { jump: true });
  assert.strictEqual(actId(g), 'air_charge');
  assert.ok(!g.player.onGround);
  until(g, () => hits(g).some(h => h.tag === 'air_chase'), {}, 60);
});

test('저글은 세 번까지만 더 뜬다 (끝없이 이어지지 않는다)', () => {
  const g = arena(), e = dummy(g, 300), ups = [];
  e.state = 'launch'; e.onGround = false; e.y -= 20; e.vy = 2;
  for (let n = 0; n < 5; n++) { e.vy = 2; g.shots.push({ kind: 'shot', x: e.x - 8, y: e.y - 38, vx: 7, w: 10, h: 6, pierce: false, hit: [] }); g.hitstop = 0; sim.step(g, {}); ups.push(e.vy < 0); g.hitstop = 0; }
  assert.deepStrictEqual(ups, [true, true, true, false, false]);
});

test('다운 · 기상 중에는 맞지 않는다', () => {
  const g = arena(), e = dummy(g, 300);
  e.state = 'down'; e.t = 30;
  g.shots.push({ kind: 'charge2', x: 290, y: C.GROUND_Y - 40, vx: 7, w: 30, h: 20, pierce: true, hit: [] });
  run(g, 4);
  assert.strictEqual(e.hp, C.TROOPER_HP);
  assert.strictEqual(hits(g).length, 0);
});

test('[검증 7] 공격마다 역할이 다르다: 서 있는 적이 맞았을 때의 상태 · 타격 정지 · 흔들림', () => {
  const out = {};
  for (const kind of ['shot', 'burst', 'charge1', 'charge2']) {
    const g = arena(), e = dummy(g, 300);
    g.shots.push({ kind: kind, x: 284, y: C.GROUND_Y - 40, vx: 7, w: 10, h: 6, pierce: false, hit: [] });
    sim.step(g, {});
    out[kind] = [e.state, g.hitstop, g.shake];
  }
  const g = arena({ melee: true }), e = dummy(g, g.player.x + 44);
  tap(g); until(g, () => hits(g).length === 1);
  out.knuckle = [e.state, g.hitstop, g.shake];
  assert.deepStrictEqual(out, {
    shot: ['stagger', H.shot.stop, H.shot.shake], burst: ['knockback', H.burst.stop, H.burst.shake],
    charge1: ['knockback', H.charge1.stop, H.charge1.shake], charge2: ['launch', H.charge2.stop, H.charge2.shake],
    knuckle: ['launch', H.knuckle.stop, H.knuckle.shake],
  });
  const stops = Object.values(out).map(v => v[1]);
  assert.strictEqual(new Set(stops).size, stops.length, '타격 정지가 공격마다 다르다');
});

// ───────────── 그림과 판정 ─────────────
test('판정이 나오는 틱에는 쏘는 · 치는 프레임이 나온다 (그림과 판정이 어긋나지 않는다)', () => {
  const want = { shot1: ['shoot', 1], shot2: ['shot2', 1], shot3: ['shot3', 2], charge1: ['charge_shot', 0], charge2: ['charge_shot', 0],
    air_shot: ['air_shoot', 1], air_burst: ['air_burst', 0], air_charge: ['air_charge', 1], knuckle: ['melee', 4] };
  for (const id of Object.keys(A)) {
    const d = A[id];
    assert.deepStrictEqual(sim.animOf({ id: id, t: sim.fireTick(d), hit: true }), want[id], id);
    for (const tl of [d.anim, d.animMiss].filter(Boolean)) {
      assert.strictEqual(tl[tl.length - 1][2], sim.total(d), id + ': 그림의 길이가 동작의 길이와 같다');
      assert.ok(tl.every((v, i) => i === 0 || v[2] > tl[i - 1][2]), id + ': 프레임이 틱 순서대로다');
    }
  }
  assert.deepStrictEqual(sim.animOf({ id: 'knuckle', t: sim.fireTick(A.knuckle), hit: false }), ['melee', 3], '빗나가면 휘두른 프레임 그대로');
});

test('캔슬 창은 판정이 나온 뒤에만 열린다', () => {
  for (const id of Object.keys(A)) {
    const d = A[id], c = d.cancel || d.cancelOnHit;
    for (const k of Object.keys(c)) if (k !== 'knuckle') assert.ok(c[k] > sim.fireTick(d), id + '.' + k);
  }
});

// ───────────── 기존 시스템 ─────────────
test('이동 · 점프 · 중력은 그대로다', () => {
  assert.deepStrictEqual([C.WALK, C.JUMP_V, C.GRAVITY, C.MAX_FALL], [2.3, -7.0, 0.38, 8]);
  const g = arena(), x0 = g.player.x;
  run(g, 10, { right: true });
  assert.ok(Math.abs(g.player.x - x0 - 23) < 1e-9, '10틱에 23px');
  let top = 0;
  sim.step(g, { jump: true });
  for (let i = 0; i < 60; i++) { sim.step(g, { jump: true }); top = Math.max(top, C.GROUND_Y - g.player.y); }
  assert.ok(top > 55 && top < 62, '점프 높이 ' + top.toFixed(1));
  assert.ok(g.player.onGround);
});

test('뛰어올라 드론을 쏘아 떨어뜨린다', () => {
  const g = arena(), d = dummy(g, g.player.x + 130, 'drone');
  for (let i = 0; i < 900 && d.alive; i++) sim.step(g, { jump: i % 50 < 22, attack: i % 9 < 2 });
  assert.ok(!d.alive, '드론을 떨어뜨리지 못했다 (체력 ' + d.hp + ')');
});

test('적의 탄에 맞으면 체력이 줄고 잠시 무적이 된다. 하던 동작은 끊긴다', () => {
  const g = arena();
  sim.step(g, { attack: true });
  g.enemyShots.push({ kind: 'bullet', x: g.player.x + 4, y: g.player.y - 30, vx: 0, vy: 0, dmg: 1 });
  run(g, 2);
  assert.strictEqual(g.player.hp, C.PLAYER_HP - 1);
  assert.strictEqual(g.player.state, 'hurt');
  assert.strictEqual(g.player.act, null);
  assert.ok(g.player.invuln > 0);
});

test('기본 무대: 처음에는 LOCMAN 만 들어 있고 적이 일곱이다', () => {
  const g = sim.createGame();
  assert.deepStrictEqual(g.learned, ['locman']);
  assert.strictEqual(g.enemies.length, 7);
  assert.strictEqual(g.player.melee, false);
});

test('기본 무대를 처음부터 끝까지 진행할 수 있고, 그 사이에 띄우기와 추격이 나온다', () => {
  const g = sim.createGame();
  g.player.hp = 99999;
  let sawLearn = false, holdT = 0;
  for (let i = 0; i < 40000 && !g.cleared; i++) {
    const p = g.player, inp = {};
    const ups = g.enemies.filter(e => e.alive && !e.dying).sort((a, b) => Math.abs(a.x - p.x) - Math.abs(b.x - p.x));
    const near = ups[0], movie = g.pickups.find(k => !k.taken);
    if (movie && (!near || near.x > movie.x + 40)) {
      inp.right = p.x < movie.x - 4; inp.left = p.x > movie.x + 4; inp.jump = Math.abs(p.x - 800) < 26 && p.onGround;
    } else if (near) {
      const dx = near.x - p.x;
      if (near.type === 'drone') { inp.right = dx > 130; inp.left = dx < -130; inp.jump = i % 50 < 22; inp.attack = i % 9 < 2; }
      else if (p.melee) {                                                                          // 붙어서 누른 채로 있다가 뗀다 → 펀치 → 공중 추격
        inp.right = dx > 44; inp.left = dx < -44;
        if (Math.abs(dx) <= 56 || holdT > 0) { holdT++; inp.attack = holdT <= 40; if (holdT > 62) holdT = 0; }
      }
      else { inp.right = dx > 210; inp.left = dx < -210; inp.attack = (i % 60) < 2 || ((i % 60) >= 10 && (i % 60) < 12) || ((i % 60) >= 20 && (i % 60) < 48); }   // 3타를 누른 채로 → 추격
      if (!inp.left && !inp.right && Math.sign(dx) !== p.facing && !p.act) { inp.left = dx < 0; inp.right = dx > 0; }
    } else inp.right = true;
    sim.step(g, inp);
    if (g.events.some(ev => ev.type === 'learned')) sawLearn = true;
    g.events.length = 0;
  }
  assert.ok(g.cleared, '무대를 끝까지 진행하지 못했다 (남은 적 ' + g.enemies.length + ')');
  assert.ok(sawLearn, '무술 영화를 학습했다');
  assert.ok(g.launches >= 1, '펀치로 띄운 적이 있다');
  assert.ok(g.chases >= 1, '추격이 들어갔다');
});

let failed = 0;
// ───────────── 캐릭터 시트 (NOVA 시안) ─────────────
test('탄은 어느 동작이 쏘았는지 적어 둔다 (그림 쪽에서 총구 높이를 맞추는 데만 쓴다)', () => {
  const g = arena();
  tap(g); until(g, () => g.shots.length > 0);
  assert.strictEqual(g.shots[0].from, 'shot1');
  assert.strictEqual(g.shots[0].y, g.player.y - C.MUZZLE_Y, '판정의 높이는 그대로다');
});

test('NOVA 시안의 동작 표가 전투 동작과 맞는다 (길이 · 판정 틱의 프레임 · 총구)', () => {
  require('../assets/nova/states/states.js');
  const T = globalThis.SALVAGE.stateSheets.nova;
  for (const id of Object.keys(A)) {
    const d = A[id], tl = T.actions[id];
    assert.ok(tl, id + ': 동작 표가 있다');
    assert.strictEqual(tl[tl.length - 1][2], sim.total(d), id + ': 그림의 길이가 동작의 길이와 같다');
    assert.ok(tl.every((v, i) => i === 0 || v[2] > tl[i - 1][2]), id + ': 프레임이 틱 순서대로다');
    for (const v of tl) assert.ok(T.states[v[0]] && v[1] < T.states[v[0]].frames, id + ': 있는 프레임이다');
    const at = tl.find(v => sim.fireTick(d) < v[2]);
    assert.deepStrictEqual([at[0], at[1]], T.fire[id], id + ': 판정 틱에 쏘는 · 치는 프레임이 나온다');
    if (d.fire) assert.ok(T.muzzle[id] && T.muzzle[id].length === 2, id + ': 총구 자리가 있다');
  }
  for (const k of ['idle', 'run', 'run_charge', 'jump', 'land', 'air_charge', 'charge', 'hurt', 'dead', 'learn']) {
    assert.ok(T.poses[k] && T.states[T.poses[k].state], k + ': 자세의 스트립이 있다');
  }
});

for (const [name, fn] of tests) {
  try { fn(); console.log('  ok   ' + name); }
  catch (err) { failed++; console.log('  FAIL ' + name + '\n       ' + String(err.message).split('\n')[0]); }
}
console.log('\n' + (tests.length - failed) + ' / ' + tests.length + ' 통과');
process.exit(failed ? 1 : 0);
