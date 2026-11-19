"""NX-07 의 머리 키 그림(parts/head.png)과 눈을 감은 머리(parts/head_blink.png)를 만든다.

AI 가 그린 머리(head_ai.png, 대기 첫 프레임에서 잘라 낸 것)의 실루엣은 그대로 두고 안쪽만 정리했다.
  - 헬멧: 얼룩진 음영을 밝은 면 · 중간 면 · 그늘 세 톤으로 정리 (밝은 면은 왼쪽 위)
  - 이마 엠블럼: 뭉개진 덩어리를 5 · 3 · 1 px 의 역삼각형으로
  - 눈: 속눈썹 한 줄 아래에 2x2 눈동자 (오른쪽 위가 동공)
  - 얼굴: 흰색과 아이보리가 섞여 있던 것을 아이보리 한 색과 턱 그늘로

글자 하나가 픽셀 하나다. 고치려면 아래 그림을 고치고 다시 돌린 뒤, tools/state_sheets.py 를 돌린다.

  python art/sprites/nx07_states/parts/head_refine.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

PALETTE = {
    '.': (0, 0, 0, 0),
    'K': (3, 3, 3, 255),          # 외곽선
    'L': (150, 151, 118, 255),    # 헬멧 밝은 면
    'M': (135, 136, 104, 255),    # 헬멧 중간 면
    'S': (118, 120, 91, 255),     # 헬멧 그늘
    'D': (52, 52, 46, 255),       # 바이저 띠, 보디슈트
    'W': (249, 250, 249, 255),    # 귀 장치와 깃
    'G': (160, 157, 150, 255),    # 귀 장치의 그늘
    'F': (247, 244, 232, 255),    # 얼굴
    'f': (226, 221, 205, 255),    # 턱 그늘
    'P': (201, 179, 171, 255),    # 바이저 아래의 살색 그늘
    'c': (40, 218, 240, 255),     # 시안
    'C': (150, 238, 248, 255),    # 밝은 시안
}

HEAD = """
..............KKKKKKKK.......
............KKLLLLLLMMKK.....
...........KMLLLLLLMMMMKK....
..........KMLLLLLMMMMMMMMK...
.........KMLLLLMMMMMMMMMMMK..
........KMMMMMMMMMMMMMMMMMMK.
........KMMMMMMMMMMMMMMMMMMK.
........KMMKKKMMMMMMMMSDDDDDK
KK.....KDSSSSSSMMMMMMMScCWCcK
KWW....KDSSSSSSSMMMMMMMScWcSK
KKWK...KDSWWSSSSKMMMMMMMScSSK
.KWWK..KWWWWWKSSDDDDMMMMMSSSK
..KSWWKKWKMKWWKDDDDDDDMMMMMSK
..KKMWWWKMMMWWKKKDDDDDDDMMSSK
...KKSSWWWWMKWWDSKKKKDDDDDDK.
....KKGWSCCcKWKDPKPKKKKDDDDK.
.....KKGKSSSWGKDPKFKKKKKDDDK.
......KGGKGGGKMMPKFFcKFPKDK..
.......KKGGGKKSMMKFFccFFKK...
........KKKKDDSMMMFFFFFFfK...
..........KKDDDMMMMFFFfffK...
"""

# 눈을 감은 머리 (대기에서 깜빡일 때): 눈동자 두 줄을 감은 눈 한 줄로 바꾼다
BLINK = {17: '......KGGKGGGKMMPKFFKKFPKDK..', 18: '.......KKGGGKKSMMKFFFFFFKK...'}

rows = HEAD.strip().split()
assert len(rows) == 21 and all(len(r) == 29 for r in rows), [len(r) for r in rows]
for name, grid in (('head.png', rows), ('head_blink.png', [BLINK.get(i, r) for i, r in enumerate(rows)])):
    assert all(len(r) == 29 for r in grid), name
    img = np.array([[PALETTE[ch] for ch in r] for r in grid], dtype=np.uint8)
    out = Path(__file__).with_name(name)
    Image.fromarray(img).save(out)
    print('[saved]', out, img.shape[1], 'x', img.shape[0])
