import numpy as np
from PIL import Image

_M1 = np.array([[0.4122214708,0.5363325363,0.0514459929],
                [0.2119034982,0.6806995451,0.1073969566],
                [0.0883024619,0.2817188376,0.6299787005]], np.float32)
_M2 = np.array([[0.2104542553,0.7936177850,-0.0040720468],
                [1.9779984951,-2.4285922050,0.4505937099],
                [0.0259040371,0.7827717662,-0.8086757660]], np.float32)

def to_oklab(rgb):
    c = np.asarray(rgb, np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return np.cbrt(c @ _M1.T) @ _M2.T

def _nearest(lab, plab, chunk=65536):
    out = np.empty(len(lab), np.int32)
    for i in range(0, len(lab), chunk):
        d = ((lab[i:i+chunk, None, :] - plab[None]) ** 2).sum(-1)
        out[i:i+chunk] = d.argmin(1)
    return out

def extract_palette(img, n=16, iters=20):
    """불투명 픽셀에서 n색 팔레트 추출 (OKLab 가중 k-means, 실제 존재하는 색으로 스냅)."""
    a = np.asarray(img.convert("RGBA"))
    px = a[a[..., 3] >= 128][:, :3]
    uniq, cnt = np.unique(px, axis=0, return_counts=True)
    lab = to_oklab(uniq); w = cnt.astype(np.float32)
    idx = [int(np.argmax(cnt))]
    for _ in range(1, min(n, len(uniq))):
        d = ((lab[:, None] - lab[idx][None]) ** 2).sum(-1).min(1) * w
        idx.append(int(np.argmax(d)))
    cent = lab[idx].copy()
    for _ in range(iters):
        lbl = _nearest(lab, cent)
        for k in range(len(cent)):
            m = lbl == k
            if m.any():
                cent[k] = (lab[m] * w[m, None]).sum(0) / w[m].sum()
    lbl = _nearest(lab, cent); pal = []
    for k in range(len(cent)):
        m = lbl == k
        if m.any():
            j = ((lab[m] - cent[k]) ** 2).sum(-1).argmin()
            pal.append(uniq[m][j])
    return np.unique(np.array(pal, np.uint8), axis=0)

def quantize(img, palette, alpha_cut=128):
    """팔레트로 재매핑 + 알파 이진화."""
    a = np.asarray(img.convert("RGBA")).copy()
    lbl = _nearest(to_oklab(a[..., :3].reshape(-1, 3)), to_oklab(palette))
    a[..., :3] = palette[lbl].reshape(a.shape[:2] + (3,))
    a[..., 3] = np.where(a[..., 3] >= alpha_cut, 255, 0)
    return Image.fromarray(a, "RGBA")

def majority_downscale(img_q, cell):
    """quantize된 이미지를 cell×cell 블록 다수결로 축소 (색 섞지 않음)."""
    a = np.asarray(img_q.convert("RGBA"))
    h, w = a.shape[0] // cell, a.shape[1] // cell
    out = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        for x in range(w):
            blk = a[y*cell:(y+1)*cell, x*cell:(x+1)*cell].reshape(-1, 4)
            op = blk[blk[:, 3] == 255]
            if len(op) * 2 < len(blk):
                continue
            cols, c = np.unique(op, axis=0, return_counts=True)
            out[y, x] = cols[c.argmax()]
    return Image.fromarray(out, "RGBA")

def add_outline(img, color=None, margin=1):
    """4방향 1px 외곽선. color 미지정 시 스프라이트에서 가장 어두운 색."""
    img = img.convert("RGBA")
    pad = Image.new("RGBA", (img.width + 2*margin, img.height + 2*margin))
    pad.paste(img, (margin, margin))
    a = np.asarray(pad).copy(); op = a[..., 3] == 255
    nb = np.zeros_like(op)
    nb[1:] |= op[:-1]; nb[:-1] |= op[1:]; nb[:, 1:] |= op[:, :-1]; nb[:, :-1] |= op[:, 1:]
    edge = nb & ~op
    if color is None:
        cols = np.unique(a[op][:, :3], axis=0)
        color = cols[to_oklab(cols)[:, 0].argmin()]
    a[edge, :3] = color; a[edge, 3] = 255
    return Image.fromarray(a, "RGBA")

def foot_anchor(img, rows=2):
    """하단 rows줄의 불투명 픽셀 중심 = 발 앵커 (x, y)."""
    a = np.asarray(img)[..., 3] == 255
    ys = np.where(a.any(1))[0]
    if len(ys) == 0:
        return None
    bottom = ys[-1]
    xs = np.where(a[max(0, bottom-rows+1):bottom+1].any(0))[0]
    return (int(xs.min() + xs.max()) // 2, int(bottom))

def align_frames(frames, cell_w, cell_h, baseline=1):
    """각 프레임을 셀에 넣고 발 앵커를 하단 중앙(baseline px 위)에 고정."""
    out = []
    for f in frames:
        cell = Image.new("RGBA", (cell_w, cell_h))
        anc = foot_anchor(f)
        if anc is not None:
            cell.paste(f, (cell_w // 2 - anc[0], cell_h - 1 - baseline - anc[1]), f)
        out.append(cell)
    return out

def reduce_flicker(frames, thresh=0.06):
    """이전 프레임과 지각적으로 거의 같은 색이면 이전 색 유지."""
    out = [frames[0]]; prev = np.asarray(frames[0])
    for f in frames[1:]:
        a = np.asarray(f).copy()
        both = (a[..., 3] == 255) & (prev[..., 3] == 255)
        d = np.linalg.norm(to_oklab(a[..., :3]) - to_oklab(prev[..., :3]), axis=-1)
        keep = both & (d > 0) & (d < thresh)
        a[keep] = prev[keep]
        out.append(Image.fromarray(a, "RGBA")); prev = a
    return out

def pack_sheet(anims, cell_w, cell_h, pad=1, fps=10):
    """anims = {"idle": [frames], "walk": [...]} → (sheet, meta). 행=동작."""
    ncol = max(len(v) for v in anims.values())
    W, H = ncol * (cell_w + pad), len(anims) * (cell_h + pad)
    sheet = Image.new("RGBA", (W, H))
    meta = {"cell": [cell_w, cell_h], "padding": pad, "animations": {}}
    for r, (name, frames) in enumerate(anims.items()):
        for c, f in enumerate(frames):
            sheet.paste(f, (c * (cell_w + pad), r * (cell_h + pad)))
        meta["animations"][name] = {"row": r, "frames": len(frames), "fps": fps}
    return sheet, meta

def qa(frames, palette, cell_w, cell_h):
    """크기·반투명·팔레트 이탈·앵커 흔들림 점검. 빈 리스트면 통과."""
    pal = {tuple(p) for p in palette.tolist()}; issues = []; bases = []
    for i, f in enumerate(frames):
        a = np.asarray(f.convert("RGBA"))
        if f.size != (cell_w, cell_h):
            issues.append(f"frame {i}: size {f.size}")
        if not np.isin(a[..., 3], [0, 255]).all():
            issues.append(f"frame {i}: semi-transparent pixels")
        extra = {tuple(c) for c in a[a[..., 3] == 255][:, :3].tolist()} - pal
        if extra:
            issues.append(f"frame {i}: {len(extra)} off-palette colors")
        anc = foot_anchor(f)
        if anc: bases.append(anc)
    if len(set(bases)) > 1:
        issues.append(f"anchor drift: {sorted(set(bases))}")
    return issues

def preview_gif(frames, path, scale=6, fps=10, bg=(40, 40, 48)):
    """nearest 확대 미리보기 GIF."""
    imgs = []
    for f in frames:
        b = Image.new("RGBA", f.size, bg + (255,)); b.alpha_composite(f)
        imgs.append(b.convert("RGB").resize((f.width*scale, f.height*scale), Image.NEAREST))
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=int(1000/fps), loop=0)
