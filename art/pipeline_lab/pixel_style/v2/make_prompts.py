"""v2 2단계 프롬프트를 쓴다 (기획서 9.11.4). 밑그림의 칸 · 원점 · 키는 guides/guides.json 에서 읽는다.

    python art/pipeline_lab/pixel_style/v2/make_prompts.py
출력: art/prompts/pipeline/nx07_side_v2_s2_<안><키>.txt
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LAB = Path(__file__).resolve().parent

PLAN = {
    "A": "a near-black charcoal bodysuit and DARK olive armor that together make ONE big dark mass over most of the body; "
         "small light accents only: the pale face, a short olive highlight on the helmet top, the white ring at the back of the cannon, "
         "one small white shoulder accent, the pale antenna",
    "B": "a calm MIDDLE-bright olive armor shell (helmet, chest, cannon, shins and boots) that reads as one big connected olive shape, "
         "held together by a near-black charcoal bodysuit that shows only in the gaps; two small off-white plates (shoulder ball, knee)",
    "C": "a near-black charcoal bodysuit and DARK olive armor that together make ONE big dark mass, lit from BEHIND: a thin pale "
         "warm-grey lit edge, one art pixel wide, only on the back and top edges (back of the helmet, shoulder top, cannon top, back of "
         "the legs, heels), broken into a few strokes and never closed around the figure; plus the pale face and the cannon ring",
}
JOBS = ["A36", "C36", "C48", "B48"]

TEMPLATE = """Redraw image 2 as a CLEAN, FINISHED pixel-art game sprite. Image 2 is a rough block-out on the EXACT pixel grid of the output; image 1 is the drawing it was made from (our own earlier draft of the android NX-07).

THE GRID (most important):
- Image 2 has exactly the size of the output image. Every square block in it is ONE ART PIXEL of {c} x {c} image pixels. The grid starts at x={ox}, y={oy}. The figure is {t} art pixels tall.
- KEEP exactly: the grid, the size, the position on the canvas, the pose, the silhouette and the light/dark plan of image 2. Every art pixel of the output is one hard {c} x {c} square exactly on this grid. Never shift a block by half a square, never draw anything smaller than one art pixel.

WHAT TO CLEAN (image 2 is messy because it was squeezed onto the grid):
- Make every shape a clean, deliberate pixel-art shape: smooth stair-step curves on the helmet and the boots, straight runs, no ragged single blocks, no stray pixels, no noise.
- Keep the BIG CALM AREAS big. Do not break them into many small pieces. Do not add new parts, panel lines or small lights.
- The head: a big round olive helmet; a clear cyan INVERTED TRIANGLE emblem on its front ({emblem}); a dark visor band; under it a small PALE boyish face that is the brightest area of the head, with ONE dark-teal eye of {eye}; no mouth. The ear unit is a small round shape in a darker helmet tone (no white, no cyan in it). A thin antenna, one art pixel wide, rises up and back behind the helmet.
- The arms: the figure faces RIGHT. The cannon belongs to the FAR arm: the olive cannon tube with a white ring at its back end, one cyan light band and a cyan muzzle, held low in front of the body and pointing forward-down, exactly as in image 2. The NEAR arm hangs at the side and ends in a dark glove fist, no cannon on it.
- Light/dark plan to keep: {plan}.
- Cyan only on the emblem, the cannon light band and the muzzle (and the eye is dark teal). About 5% of the figure is saturated color, everything else is muted.
- NO OUTLINE: no black line around the figure and no dark ring around the parts. Dark parts are allowed on the edge because they are dark parts.
- 12 to 16 colors in total, each material 2 tones plus at most one small highlight. Use the colors of image 2; do not brighten the olive.

THE FIGURE: exactly one character, a sturdy BOY android soldier in pure side view facing right, the same relaxed standing pose as image 2 with both soles on the same ground line. Do not make it slimmer, taller, longer-legged or curvier.

BACKGROUND: completely flat solid magenta (#FF00FF) everywhere outside the figure. No ground, no shadow, no text, no border, no grid lines.
Hard square pixels on one even grid, no anti-aliasing, no blur, no gradients, no semi-transparent pixels.
"""


def main() -> None:
    g = json.loads((LAB / "guides/guides.json").read_text(encoding="utf-8"))
    for job in JOBS:
        gi = g[job]
        t = int(job[1:])
        txt = TEMPLATE.format(c=gi["cell"], ox=gi["origin"][0], oy=gi["origin"][1], t=t, plan=PLAN[job[0]],
                              emblem="3 art pixels wide on top, 1 below" if t <= 40 else "about 3 art pixels wide, 2 rows",
                              eye="1 x 1 art pixel" if t <= 40 else "1 x 2 art pixels (one wide, two tall)")
        p = ROOT / "art/prompts/pipeline" / f"nx07_side_v2_s2_{job}.txt"
        p.write_text(txt, encoding="utf-8")
        print(p)


if __name__ == "__main__":
    main()
