"""fal.ai 이미지 생성 도구 (SALVAGE 에셋 파이프라인).

.env.local 의 FAL_KEY 를 읽어 fal.ai 모델을 호출하고 결과 이미지를 저장한다.
키 값은 어디에도 출력하지 않는다.

지금 그림체로 뽑을 때 (캐릭터 시트, 설정화, 일러스트):
    python tools/fal_image.py --keep-style android \
        --prompt-file art/prompts/<내용>.txt \
        --prompt-file art/prompts/_sheet_layout_android.txt \
        --ref reference/<디자인 참조>.png \
        --out art/concept/<이름>.png

    --keep-style 은 화풍 기준 그림(art/style_anchor/)을 참조 이미지 맨 뒤에 붙이고,
    화풍 설명(_style_illustration.txt)과 화풍 고정 문구(_style_lock.txt)를 프롬프트 뒤에 붙이고,
    지금 그림체를 만든 모델과 크기를 쓴다. android / human / both 중에서 고른다.

그 밖의 그림 (픽셀 목업 등):
    python tools/fal_image.py --prompt-file art/prompts/concept_ingame_pixel.txt \
        --ref reference/캐릭터디자인2차.png --aspect 16:9 --resolution 2K \
        --out art/concept/concept_ingame_pixel.png

--dry-run 을 붙이면 fal.ai 를 호출하지 않고 보낼 내용만 보여 준다.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "fal-ai/nano-banana-pro/edit"

# 지금 그림체를 만든 조합. 바꾸면 그림체가 달라진다.
STYLE_MODEL = "openai/gpt-image-2.6/sunburst/edit"
STYLE_SIZE = {"width": 3072, "height": 2048}
STYLE_TEXT = ROOT / "art" / "prompts" / "_style_illustration.txt"
STYLE_LOCK = ROOT / "art" / "prompts" / "_style_lock.txt"
STYLE_ANCHORS = {
    "android": [ROOT / "art" / "style_anchor" / "android.png"],
    "human": [ROOT / "art" / "style_anchor" / "human.png"],
}
STYLE_ANCHORS["both"] = STYLE_ANCHORS["android"] + STYLE_ANCHORS["human"]


def load_fal_key() -> None:
    """.env.local 에서 FAL_KEY 만 골라 환경 변수로 올린다 (출력 금지)."""
    if os.environ.get("FAL_KEY"):
        return
    env_path = ROOT / ".env.local"
    if not env_path.exists():
        sys.exit(".env.local 을 찾을 수 없습니다.")
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("FAL_KEY="):
            os.environ["FAL_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
            return
    sys.exit(".env.local 에 FAL_KEY 가 없습니다.")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="fal.ai 이미지 생성")
    ap.add_argument("--model", default=None, help=f"기본값: {DEFAULT_MODEL} (--keep-style 이면 {STYLE_MODEL})")
    ap.add_argument("--prompt-file", action="append", required=True,
                    help="프롬프트 텍스트 파일 (여러 번 지정하면 순서대로 이어 붙인다. 예: 내용 + 시트 구성)")
    ap.add_argument("--ref", action="append", default=[], help="참조 이미지 (여러 번 지정 가능, 순서 = image 1, 2, ...)")
    ap.add_argument("--keep-style", choices=sorted(STYLE_ANCHORS),
                    help="지금 그림체로 고정한다. 화풍 기준 그림·화풍 설명·고정 문구·모델·크기를 자동으로 붙인다")
    ap.add_argument("--aspect", default=None, help="예: 16:9, 3:2, 1:1. 이 인자를 안 받는 모델이면 none")
    ap.add_argument("--resolution", default=None, help="1K / 2K / 4K. 이 인자를 안 받는 모델이면 none")
    ap.add_argument("--num", type=int, default=1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--arg", action="append", default=[], metavar="KEY=VALUE",
                    help="모델 전용 인자. 값은 JSON 으로 읽고, 안 되면 문자열로 쓴다 (여러 번 지정 가능)")
    ap.add_argument("--dry-run", action="store_true", help="fal.ai 를 호출하지 않고 보낼 내용만 출력한다")
    ap.add_argument("--out", required=True, help="저장 경로 (여러 장이면 _2, _3 … 접미사)")
    args = ap.parse_args()

    prompt_files = [Path(p) for p in args.prompt_file]
    refs = [Path(r) for r in args.ref]
    extra: dict[str, object] = {}
    for item in args.arg:
        k, _, v = item.partition("=")
        try:
            extra[k] = json.loads(v)
        except json.JSONDecodeError:
            extra[k] = v

    lock_text = ""
    if args.keep_style:
        model = args.model or STYLE_MODEL
        anchors = STYLE_ANCHORS[args.keep_style]
        missing = [str(a) for a in anchors if not a.exists()]
        if missing:
            sys.exit(f"화풍 기준 그림이 없습니다: {missing}")
        first = len(refs) + 1
        numbers = [str(first + i) for i in range(len(anchors))]
        which = f"image {numbers[0]} is" if len(numbers) == 1 else f"images {' and '.join(numbers)} are"
        refs += anchors
        if STYLE_TEXT.resolve() not in [p.resolve() for p in prompt_files]:
            prompt_files.append(STYLE_TEXT)
        lock_text = STYLE_LOCK.read_text(encoding="utf-8").strip().replace("{anchors}", which)
        aspect, resolution = args.aspect or "none", args.resolution or "none"
        extra.setdefault("image_size", STYLE_SIZE)
        extra.setdefault("quality", "high")
    else:
        model = args.model or DEFAULT_MODEL
        aspect, resolution = args.aspect or "auto", args.resolution or "2K"

    parts = [p.read_text(encoding="utf-8").strip() for p in prompt_files]
    if lock_text:
        parts.append(lock_text)
    prompt = "\n\n".join(parts)

    arguments: dict[str, object] = {"prompt": prompt, "num_images": args.num, "output_format": "png"}
    if aspect.lower() != "none":
        arguments["aspect_ratio"] = aspect
    if resolution.lower() != "none":
        arguments["resolution"] = resolution
    if args.seed is not None:
        arguments["seed"] = args.seed
    arguments.update(extra)

    if args.dry_run:
        print(f"[dry-run] model: {model}")
        print("[dry-run] prompt files: " + ", ".join(p.name for p in prompt_files) + (" + _style_lock.txt" if lock_text else ""))
        for i, r in enumerate(refs, 1):
            print(f"[dry-run] image {i}: {r}")
        shown = {k: v for k, v in arguments.items() if k != "prompt"}
        print(f"[dry-run] arguments: {json.dumps(shown, ensure_ascii=False)}")
        print(f"[dry-run] prompt ({len(prompt)} chars), last part:\n{parts[-1]}")
        return

    load_fal_key()
    import fal_client
    import requests

    image_urls = []
    for i, p in enumerate(refs, 1):
        ctype = mimetypes.guess_type(p.name)[0] or "image/png"
        # 파일 이름은 외부로 보내지 않고 ref1, ref2 … 로 올린다.
        url = fal_client.upload(p.read_bytes(), ctype, f"ref{i}{p.suffix.lower()}")
        image_urls.append(url)
        print(f"[upload] image {i}: {p.name}")
    if image_urls:
        arguments["image_urls"] = image_urls

    print(f"[run] {model} …")
    result = fal_client.subscribe(model, arguments=arguments)

    images = result.get("images") or []
    if not images:
        sys.exit(f"이미지가 반환되지 않았습니다: {str(result)[:500]}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for i, img in enumerate(images, 1):
        target = out if i == 1 else out.with_name(f"{out.stem}_{i}{out.suffix}")
        data = requests.get(img["url"], timeout=120).content
        target.write_bytes(data)
        print(f"[saved] {target} ({len(data) // 1024} KB)")


if __name__ == "__main__":
    main()
