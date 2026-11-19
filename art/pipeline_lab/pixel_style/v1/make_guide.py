"""픽셀 마스터 v1 의 밑그림: 주포를 먼 쪽 팔(캐릭터의 왼팔)로 옮긴 56칸 블록 그림 (기획서 9.11.2).

    python art/pipeline_lab/pixel_style/v1/make_guide.py

재료는 우리 그림뿐이다: 견본 2 의 마스터(sample_dark2/nx07_side_dark2.png, 22×56).
- 머리(0~15줄)와 다리(36줄 아래)는 견본 2 그대로 쓰고, 슈트 색만 어두운 청회색으로 바꾼다.
- 몸통(16~35줄)은 지우고 칸 단위로 다시 깐다:
  뒤 → 앞 순서로 몸통 · 등짐 · 먼 쪽 팔의 주포(가슴 앞으로 내민다) · 가슴 장갑 · 앞쪽 팔(늘어뜨린 팔, 흰 · 올리브 건틀릿, 검은 주먹) · 앞쪽 어깨.
- 가로 23칸 (주포의 총구가 들어가게 1칸 넓혔다). 1024 캔버스에 칸 16px, 원점 (320, 64), 발바닥 960.
밑그림은 대충의 배치다. 모델이 깨끗한 모양으로 다시 그린다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
LAB = Path(__file__).resolve().parent
CELL, OX, OY = 16, 320, 64

HEX = {
    "S": "56607e",  # 슈트 (어두운 청회색)
    "s": "3f4762",  # 슈트 그늘
    "k": "262b3e",  # 슈트의 가장자리 · 장갑 낀 손
    "h": "4a5070",  # 손의 밝은 면
    "O": "8a8f58",  # 올리브
    "L": "a1ac6c",  # 올리브 밝은 면
    "o": "6c7242",  # 올리브 그늘
    "D": "353e19",  # 올리브 가장자리
    "W": "f0ebe4",  # 흰 판
    "g": "b6b0ab",  # 흰 판 그늘
    "G": "6a6a72",  # 흰 판 가장자리
    "C": "05fcfc",  # 시안 빛
    "c": "07bebd",  # 시안 그늘
}


def rgb(k: str) -> tuple[int, int, int, int]:
    h = HEX[k]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255


def main() -> None:
    src = np.array(Image.open(LAB.parent / "sample_dark2/nx07_side_dark2.png").convert("RGBA"))
    h, w = src.shape[:2]
    a = np.zeros((h, w + 1, 4), np.uint8)
    a[:, :w] = src
    # 슈트 색 바꾸기 (16줄 아래): #454356 → S, #1a1e2a → k, #292a2b → s
    swap = {(0x45, 0x43, 0x56): "S", (0x1A, 0x1E, 0x2A): "k", (0x29, 0x2A, 0x2B): "s"}
    for y in range(16, h):
        for x in range(w + 1):
            t = tuple(int(v) for v in a[y, x, :3])
            if a[y, x, 3] and t in swap:
                a[y, x] = rgb(swap[t])
    a[18:36] = 0  # 몸통을 지운다 (목 16~17줄은 남긴다)
    a[36:38, 14:] = 0  # 견본 2 의 주포 끝자락

    def rect(x0, y0, x1, y1, k):
        a[y0:y1 + 1, x0:x1 + 1] = rgb(k)

    def px(x, y, k):
        a[y, x] = rgb(k)

    # 몸통 (슈트)
    rect(6, 18, 13, 31, "k"); rect(7, 18, 12, 31, "S"); rect(7, 24, 8, 31, "s")
    rect(5, 32, 12, 35, "k"); rect(6, 32, 11, 35, "S"); rect(6, 34, 7, 35, "s")
    # 등짐
    rect(2, 18, 5, 25, "D"); rect(3, 19, 4, 24, "O"); px(3, 19, "L"); rect(3, 21, 3, 22, "W"); px(4, 22, "C")
    # 먼 쪽 팔 = 주포 (가슴 앞으로 내민다). 뒤쪽 끝은 앞쪽 팔에 가린다
    rect(11, 23, 22, 29, "D")
    rect(12, 24, 13, 28, "W"); rect(12, 28, 13, 28, "g")
    rect(14, 24, 19, 28, "O"); rect(14, 24, 19, 24, "L"); rect(14, 28, 19, 28, "o")
    rect(15, 26, 18, 26, "C")
    rect(20, 24, 21, 28, "c"); rect(20, 25, 21, 27, "C")
    # 가슴 장갑
    rect(10, 18, 15, 23, "D"); rect(11, 18, 14, 22, "O"); rect(12, 18, 13, 19, "L"); rect(11, 22, 14, 22, "o"); px(14, 20, "C")
    # 흰 골반 판
    rect(10, 31, 13, 33, "G"); rect(11, 31, 12, 32, "W")
    # 앞쪽 팔 (보통의 팔): 위팔 슈트 → 흰 고리 → 올리브 건틀릿 → 검은 주먹
    rect(7, 22, 11, 27, "k"); rect(8, 22, 10, 27, "S")
    rect(7, 27, 11, 28, "G"); rect(8, 27, 10, 27, "W"); rect(8, 28, 10, 28, "g")
    rect(7, 29, 11, 31, "D"); rect(8, 29, 10, 30, "O"); px(8, 29, "L")
    rect(7, 32, 11, 34, "k"); rect(8, 32, 10, 33, "h")
    # 앞쪽 어깨 (흰 공 모양)
    rect(7, 18, 11, 21, "G"); rect(8, 18, 10, 20, "W"); px(8, 18, "W"); rect(8, 21, 10, 21, "g")

    Image.fromarray(a, "RGBA").save(LAB / "guide56_cells.png")
    big = Image.fromarray(a, "RGBA").resize((a.shape[1] * CELL, a.shape[0] * CELL), Image.NEAREST)
    canvas = Image.new("RGBA", (1024, 1024), (255, 0, 255, 255))
    assert OX + big.width <= 1024 and OY + big.height == 960
    canvas.alpha_composite(big, (OX, OY))
    out = ROOT / "art/prompts/pipeline/nx07_side_v1_guide56.png"
    canvas.convert("RGB").save(out)
    Image.fromarray(a, "RGBA").resize((a.shape[1] * 8, a.shape[0] * 8), Image.NEAREST).save(LAB / "guide56_cells_x8.png")
    print(out, a.shape[1], "×", a.shape[0])


if __name__ == "__main__":
    main()
