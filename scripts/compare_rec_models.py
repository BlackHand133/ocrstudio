#!/usr/bin/env python3
"""
Compare PaddleOCR recognition models on your own images

Runs the same sample through two recognition models and scores both with
scripts/thai_quality.py, so you can tell whether a model change actually helps
before re-running OCR over a whole workspace. The saved annotations are scored
too, as a third reference point.

    # default: Thai model vs the general model
    python scripts/compare_rec_models.py --workspace dataset --sample 16

    # any two models
    python scripts/compare_rec_models.py \
        --model-a th_PP-OCRv5_mobile_rec \
        --model-b latin_PP-OCRv5_mobile_rec

Needs paddleocr installed. If it is not, run it inside the app image, which
already has it:

    docker run --rm -v "%cd%:/work" -w /work ocrstudio-web:latest \
        python scripts/compare_rec_models.py --workspace dataset

Two things this script does deliberately, both learned the hard way:

* enable_mkldnn=False — PaddleOCR 3.x crashes inside oneDNN+PIR on detection
  ("ConvertPirAttribute2RuntimeAttribute not support"). config/config.yaml
  disables it for the same reason.
* images are downscaled before predict(), matching max_image_size in the
  profile. Feeding a 4032x3024 phone photo straight to the server detector gets
  the process OOM-killed.

Reading the output: check the `thai` column before the rates. A model that
emits no Thai at all scores a perfect 0.00 on every rate while being useless.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# thai_quality calls force_utf8_output() on import, which covers this script too.
from thai_quality import HEADER, format_row, score, warn_if_no_thai  # noqa: E402

DEFAULT_A = "th_PP-OCRv5_mobile_rec"
DEFAULT_B = "PP-OCRv5_mobile_rec"


def build_engine(rec_model, det_model, det_side_len):
    from paddleocr import PaddleOCR

    return PaddleOCR(
        device="cpu",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,  # see module docstring
        text_detection_model_name=det_model,
        text_recognition_model_name=rec_model,
        text_det_limit_side_len=det_side_len,
        text_det_limit_type="max",
    )


def load_image(path, max_side):
    import numpy as np
    from PIL import Image

    im = Image.open(path).convert("RGB")
    if max_side and max(im.size) > max_side:
        s = max_side / max(im.size)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    return np.array(im)


def run_model(label, rec_model, keys, images_dir, args):
    print(f"\n--- {label}: {rec_model} ---", flush=True)
    t0 = time.time()
    try:
        ocr = build_engine(rec_model, args.det_model, args.det_side_len)
    except Exception as exc:  # noqa: BLE001 - report and keep the other run
        print(f"  could not build: {type(exc).__name__}: {exc}")
        return None, {}
    print(f"  ready in {time.time() - t0:.1f}s", flush=True)

    texts, per_image, failed = [], {}, 0
    for n, key in enumerate(keys, 1):
        try:
            result = ocr.predict(load_image(images_dir / key, args.max_image_size))
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  [{n}/{len(keys)}] {key}: ERROR {str(exc)[:90]}", flush=True)
            continue
        got = []
        if result:
            r = result[0]
            got = list(
                r.get("rec_texts", []) if isinstance(r, dict)
                else getattr(r, "rec_texts", [])
            )
        texts.extend(got)
        per_image[key] = got
        print(f"  [{n}/{len(keys)}] {key}: {len(got)} lines", flush=True)
    if failed:
        print(f"  {failed} image(s) failed")
    return score(texts), per_image


def pick_sample(version_file, images_dir, n, seed):
    data = json.loads(version_file.read_text(encoding="utf-8"))
    anns = data.get("annotations") or {}
    have = [k for k, v in anns.items() if v and (images_dir / k).exists()]
    if not have:
        return [], anns
    random.seed(seed)  # same images for both models
    return sorted(random.sample(have, min(n, len(have)))), anns


def main():
    ap = argparse.ArgumentParser(
        description="Compare two PaddleOCR recognition models on your images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--workspace", default="dataset")
    ap.add_argument("--version", default="v1", help="version file to sample from")
    ap.add_argument("--sample", type=int, default=16, help="images to run (default 16)")
    ap.add_argument("--seed", type=int, default=20260727)
    ap.add_argument("--model-a", default=DEFAULT_A)
    ap.add_argument("--model-b", default=DEFAULT_B)
    ap.add_argument("--det-model", default="PP-OCRv5_mobile_det",
                    help="server variants need far more RAM (default: mobile)")
    ap.add_argument("--det-side-len", type=int, default=1280)
    ap.add_argument("--max-image-size", type=int, default=2500,
                    help="downscale before OCR; 0 disables (default 2500)")
    ap.add_argument("--out", default="", help="write full results to this JSON file")
    args = ap.parse_args()

    ws = REPO_ROOT / "workspaces" / args.workspace
    images_dir = ws / "images"
    version_file = ws / f"{args.version}.json"
    for p in (ws, images_dir, version_file):
        if not p.exists():
            print(f"Missing: {p}")
            return 1

    keys, anns = pick_sample(version_file, images_dir, args.sample, args.seed)
    if not keys:
        print("No annotated images with files on disk.")
        return 1
    print(f"sample: {len(keys)} image(s) from {args.workspace}/{args.version}")

    saved = score([
        (a.get("transcription") or "")
        for k in keys for a in anns[k]
        if (a.get("transcription") or "").strip()
    ])

    a_stats, a_texts = run_model("A", args.model_a, keys, images_dir, args)
    b_stats, b_texts = run_model("B", args.model_b, keys, images_dir, args)

    print("\n" + "=" * len(HEADER))
    print("RESULTS")
    print("=" * len(HEADER))
    print(HEADER)
    print("-" * len(HEADER))
    rows = [("saved", saved), (f"A {args.model_a[:11]}", a_stats),
            (f"B {args.model_b[:11]}", b_stats)]
    for label, stats in rows:
        if stats is None:
            print(f"{label:<13}  (engine failed)")
        else:
            print(format_row(label, stats))

    print()
    broken = [warn_if_no_thai(label, s) for label, s in rows if s]
    if not any(broken):
        print("  All runs produced Thai, so the rates are comparable.")

    if a_texts and b_texts:
        print("\nsame line, both models (first 10 differences):")
        shown = 0
        for k in keys:
            for x, y in zip(a_texts.get(k, []), b_texts.get(k, [])):
                if x != y and shown < 10:
                    print(f"  A: {x!r}")
                    print(f"  B: {y!r}")
                    shown += 1

    if args.out:
        Path(args.out).write_text(
            json.dumps({"sample": keys, "saved": saved,
                        "a": {"model": args.model_a, "stats": a_stats, "texts": a_texts},
                        "b": {"model": args.model_b, "stats": b_stats, "texts": b_texts}},
                       ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
