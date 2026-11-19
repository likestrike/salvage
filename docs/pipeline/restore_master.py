"""AI 도트풍 원화 → 그리드 복원 마스터 스프라이트.

사용법:
  python restore_master.py <input.png> <out_dir> --pixel-width 8 --colors 24

처리 순서:
  1) proper-pixel-art로 숨은 그리드를 찾아 셀마다 한 색으로 스냅 (손으로 다시 그리지 않음)
  2) 알파 0/255 이진화, 캐릭터 바운딩박스로 크롭
  3) OKLab k-means로 팔레트 N색 추출 → 팔레트로 재매핑(색 잠금)
  4) QA(크기·반투명·팔레트 이탈) 후 마스터 PNG, 팔레트(.hex/.gpl), 4배 미리보기 저장
"""
import argparse, os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from pxl import extract_palette, quantize, qa, to_oklab
from proper_pixel_art import pixelate
from proper_pixel_art.config import PixelateConfig

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--pixel-width", type=int, default=None,
                    help="원화에서 도트 1칸의 픽셀 크기. 미지정 시 자동 검출(오검출 잦음, 반드시 확인)")
    ap.add_argument("--colors", type=int, default=24)
    ap.add_argument("--name", default="master")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    src = Image.open(a.src).convert("RGBA")
    cfg = PixelateConfig(pixel_width=a.pixel_width, transparent_background=True)
    res = pixelate(src, cfg)
    img = res.image.convert("RGBA")

    arr = np.array(img); arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0)
    img = Image.fromarray(arr)
    ys, xs = np.where(arr[..., 3] == 255)
    img = img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

    pal = extract_palette(img, n=a.colors)
    pal = pal[np.argsort(to_oklab(pal)[:, 0])]
    master = quantize(img, pal)

    issues = qa([master], pal, master.width, master.height)
    m = os.path.join(a.out, a.name)
    master.save(m + ".png")
    master.resize((master.width * 4, master.height * 4), Image.NEAREST).save(m + "_x4.png")
    open(m + "_palette.hex", "w").write("\n".join("%02x%02x%02x" % tuple(p) for p in pal) + "\n")
    with open(m + "_palette.gpl", "w") as f:
        f.write(f"GIMP Palette\nName: {a.name}\nColumns: 8\n#\n")
        for p in pal: f.write(f"{p[0]:3d} {p[1]:3d} {p[2]:3d}\t#{'%02X%02X%02X' % tuple(p)}\n")
    info = {"size": master.size, "pixel_width_used": a.pixel_width or "auto",
            "detected_pixel_width_upscaled": res.pixel_width, "colors": len(pal), "qa": issues}
    json.dump(info, open(m + "_info.json", "w"), ensure_ascii=False, indent=2, default=str)
    print(json.dumps(info, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
