"""기획자가 넣은 NX-07 새 디자인 시안(NOVA)의 스트립을 게임에 올린다 (기획서 9.10).

    python tools/nova_sheets.py art/sprites/nx07_nova/layout.json

하는 일
  1. 스트립(가로 한 줄, 칸 160x160)을 고치지 않고 게임 폴더로 복사한다. 줄이거나 다시 칠하지 않는다.
  2. 프레임마다 정수리 · 발바닥 · 발의 가로 범위 · 몸의 가로 중심을 잰다 (states.json).
  3. 표(프레임 수, 프레임 시간, 프레임별 가로 보정, 전투 동작의 프레임, 총구 자리, 자세)를 states.js 로 쓴다.
     게임은 file:// 로 열리므로 JSON 을 읽지 못한다. 그래서 스크립트 파일로 쓴다.
  4. 표가 맞는지 본다: 없는 스트립 · 프레임을 가리키는지, 틱이 순서대로인지, 판정 프레임이 동작 표에 들어 있는지.
     동작의 길이와 판정 틱은 game/src/sim.js 의 값이므로 node game/test/sim.test.js 가 확인한다.

가로 보정(dx): 그림 안에서 캐릭터가 미끄러져 간 스트립(3타의 반동, 피격)은 게임이 자리를 정하므로 그만큼 되돌린다.
  "dx": [...]            프레임마다 직접 적는다
  "anchor_body": 81.5    몸(스카프 · 빛을 뺀 부분)의 가로 중심이 이 자리에 오도록 프레임마다 계산한다
"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image


def measure(frame):
    """한 프레임(RGBA 배열)의 키 위치. 빈 프레임이면 None."""
    solid = frame[..., 3] > 100
    ys, xs = np.nonzero(solid)
    if len(ys) == 0:
        return None
    r, g, b = (frame[..., k].astype(int) for k in range(3))
    mint = solid & (g > 200) & (b > 150) & (r < 170) & (g - r > 60)       # 발광 · 섬광
    scarf = solid & (r > 180) & (g < 140) & (b < 90)                       # 스카프
    body = solid & ~mint & ~scarf
    bot = int(ys.max())
    feet = np.nonzero(solid[max(0, bot - 5):bot + 1].any(axis=0))[0]
    bxs = np.nonzero(body)[1]
    return {'top': int(ys.min()), 'bottom': bot, 'left': int(xs.min()), 'right': int(xs.max()),
            'feet': [int(feet.min()), int(feet.max())], 'body_x': round(float(bxs.mean()), 1) if len(bxs) else None}


def main(path):
    L = json.load(open(path, encoding='utf-8'))
    here = os.path.dirname(path)
    cw, ch = L['cell']
    base = L['base']
    out_dir = L['game']
    os.makedirs(out_dir, exist_ok=True)
    errors, table, report = [], {}, {}

    for st in L['states']:
        name = st['name']
        src = os.path.join(L['src'], st.get('file', name + '.png'))
        if not os.path.exists(src):
            errors.append(f'{name}: 스트립이 없다 ({src})')
            continue
        im = Image.open(src).convert('RGBA')
        if im.height != ch or im.width % cw:
            errors.append(f'{name}: 크기 {im.size} 가 칸 {cw}x{ch} 의 배수가 아니다')
            continue
        a = np.array(im)
        n = im.width // cw
        ms = [measure(a[:, i * cw:(i + 1) * cw]) for i in range(n)]
        if any(m is None for m in ms):
            errors.append(f'{name}: 빈 프레임이 있다')
            continue
        air = set(st.get('air', []))
        # 땅에 닿은 프레임은 발바닥이 기준 줄(또는 그 한 줄 위)에 있어야 한다
        off = [i for i, m in enumerate(ms) if i not in air and not (base - 2 <= m['bottom'] <= base)]
        if off:
            errors.append(f'{name}: 발바닥이 기준 줄({base})에서 벗어난 프레임 {off} (공중 프레임이면 "air" 에 적는다)')
        dx = st.get('dx')
        if dx is None and 'anchor_body' in st:
            dx = [int(round(st['anchor_body'] - m['body_x'])) for m in ms]
        if dx is not None and len(dx) != n:
            errors.append(f'{name}: dx 의 길이 {len(dx)} 가 프레임 수 {n} 와 다르다')
        shutil.copyfile(src, os.path.join(out_dir, name + '.png'))
        row = {'frames': n, 'ticks': st['ticks'], 'loop': bool(st.get('loop')), 'used': bool(st.get('used'))}
        if dx is not None and any(dx):
            row['dx'] = dx
        table[name] = row
        report[name] = {'frames': n, 'ticks': st['ticks'], 'used': bool(st.get('used')), 'dx': dx,
                        'height': [base - m['top'] + 1 for m in ms], 'key': ms}

    def frame_ok(where, name, i):
        if name not in table:
            errors.append(f'{where}: 없는 스트립 {name}')
        elif not (0 <= i < table[name]['frames']):
            errors.append(f'{where}: {name} 에 {i} 번 프레임이 없다 (0~{table[name]["frames"] - 1})')
        elif not table[name]['used']:
            errors.append(f'{where}: {name} 을 쓰는데 "used" 가 아니다')

    for act, tl in L['actions'].items():
        for k, (name, i, until) in enumerate(tl):
            frame_ok(f'actions.{act}', name, i)
            if k and until <= tl[k - 1][2]:
                errors.append(f'actions.{act}: 틱이 순서대로가 아니다 ({tl[k - 1][2]} → {until})')
        want = L['fire'].get(act)
        if not want:
            errors.append(f'fire.{act}: 판정 프레임이 적혀 있지 않다')
        elif not any([name, i] == want for name, i, _ in tl):
            errors.append(f'fire.{act}: {want} 이 동작 표에 없다')
    for pose, q in L['poses'].items():
        for i in q.get('frames', [0]):
            frame_ok(f'poses.{pose}', q['state'], i)

    # 서 있는 자세의 키 (대기의 첫 프레임)
    stand = report.get('idle', {}).get('height', [None])[0]
    js = {'id': L['id'], 'name': L['name'], 'cell': L['cell'], 'base': base, 'board': L.get('board'), 'glow': L.get('glow'), 'stand': stand,
          'states': table, 'actions': L['actions'], 'fire': L['fire'], 'muzzle': L['muzzle'], 'poses': L['poses']}
    with open(os.path.join(out_dir, 'states.js'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('/* tools/nova_sheets.py 가 만든 파일이다. 고치려면 art/sprites/nx07_nova/layout.json 을 고치고 도구를 다시 돌린다.\n'
                ' * frames = 프레임 수, ticks = 한 프레임을 보여 주는 틱(1/60초), dx = 프레임별 가로 보정, base = 칸 안에서 발바닥이 닿는 줄.\n'
                ' * actions = 전투 동작마다 [스트립, 프레임, 이 틱 전까지]. muzzle = 총구 [앞으로, 발바닥에서 위로]. */\n'
                '(function (root) {\n  var S = root.SALVAGE = root.SALVAGE || {};\n  S.stateSheets = S.stateSheets || {};\n'
                f'  S.stateSheets[{json.dumps(L["id"])}] = {json.dumps(js, ensure_ascii=False)};\n'
                "})(typeof window !== 'undefined' ? window : globalThis);\n")
    with open(os.path.join(here, 'states.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'cell': L['cell'], 'base': base, 'stand': stand, 'errors': errors, 'states': report}, f, ensure_ascii=False, indent=1)

    used = [n for n, r in table.items() if r['used']]
    print(f'[saved] {out_dir} — 스트립 {len(table)}장 (게임이 쓰는 것 {len(used)}장), states.js · 서 있는 키 {stand}px, 발바닥 줄 {base}')
    for n, r in report.items():
        if r['dx'] and any(r['dx']):
            print(f'  가로 보정 {n}: {r["dx"]}')
    if errors:
        print('검사 실패:')
        for e in errors:
            print('  -', e)
        return 1
    print('검사 통과')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'art/sprites/nx07_nova/layout.json'))
