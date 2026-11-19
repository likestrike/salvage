"""NX-07 대기 키 그림의 파츠 지도(parts/idle_parts.png)를 만든다.

파츠 지도는 칸(112x96)과 같은 크기의 그림이고, 파츠마다 한 색으로 칠해져 있다. tools/state_sheets.py 의 rig 이 이 지도대로
키 그림(대기 첫 프레임)을 파츠로 나눠서 파츠별로 움직인다. 지도는 그림판에서 직접 고쳐도 된다 (색만 지키면 된다).

  머리      #ff4d4d   목 줄(27)까지
  뒤쪽 팔   #ffd24d   등 뒤로 늘어뜨린 왼팔 (흰 건틀릿과 주먹)
  주포      #4de3ff   오른팔의 전완 고리와 포신
  다리      #6f7dff   허리 줄(53) 아래: 골반 · 허벅지 · 무릎 · 부츠
  몸통      #7dff6f   나머지: 가슴 · 백팩 · 배

좌표는 칸 안의 px 이다. 대기 키 그림의 자리가 바뀌면(layout 의 기준 위치를 바꾸면) 이 지도도 다시 맞춰야 한다.

  python art/sprites/nx07_states/parts/idle_parts_make.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

CW, CH = 112, 96
COLORS = {'head': (255, 77, 77), 'arm_back': (255, 210, 77), 'cannon': (77, 227, 255), 'legs': (111, 125, 255), 'torso': (125, 255, 111)}
NECK, WAIST = 27, 53


def part_of(x: int, y: int) -> str:
    if y <= NECK:
        return 'head'
    # 뒤쪽 팔: 흰 건틀릿(34~44, 40~49)과 주먹(33~44, 49~58). 백팩의 아랫부분(41~, ~41)은 몸통이다
    if y <= 58 and ((y >= 40 and x <= 40) or (42 <= y <= 49 and x <= 45) or (y >= 50 and x <= 44)):
        return 'arm_back'
    # 주포: 전완의 고리(58~66, 41~51)와 포신(67~, 41~57)
    if (41 <= y <= 57 and x >= 67) or (41 <= y <= 51 and 58 <= x <= 66):
        return 'cannon'
    if y >= WAIST:
        return 'legs'
    return 'torso'


img = np.zeros((CH, CW, 3), dtype=np.uint8)
for y in range(CH):
    for x in range(CW):
        img[y, x] = COLORS[part_of(x, y)]
out = Path(__file__).with_name('idle_parts.png')
Image.fromarray(img).save(out)
print('[saved]', out)
