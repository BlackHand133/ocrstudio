#!/usr/bin/env python3
"""
Re-read annotation boxes whose text is printed upside down

Photographs of drug bags often include the blister pack lying the other way up.
The bag reads fine; the pack comes back as noise — 'Simethicone 80 mg.' becomes
'ธw 08 อน0วนอพเs'. Rotating the whole image is not the fix: it would invert the
boxes that are already correct.

So this works per box. Each one is cropped, read as-is and again rotated 180,
and the better reading wins. Nothing about the *content* of the existing text is
used to decide which boxes to look at — text-based heuristics miss the boxes
that come back as plain Latin noise, which is most of them.

    # look, change nothing (default)
    python scripts/refix_rotated_boxes.py --images A117.jpg A118.jpg

    # write the result to a new version, leaving the original untouched
    python scripts/refix_rotated_boxes.py --images A117.jpg --write

Needs paddleocr. Without it locally, run in the app image:

    docker run --rm -v "%cd%:/work" -w /work ocrstudio-web:latest \
        python scripts/refix_rotated_boxes.py --images A117.jpg

The original version file is never modified. --write creates the next free
vN.json beside it and leaves the workspace pointing wherever it already points,
so you can compare the two in the app before switching.
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from thai_quality import force_utf8_output, is_thai  # noqa: E402
from workspace_versions import next_version_path, stamp_version  # noqa: E402

force_utf8_output()

# Confidence alone is not enough to accept a replacement. A dry run over
# A117.jpg returned '店' at 0.58 and '1-2は' at 0.85 for crops that are neither
# Chinese nor Japanese — the model is happy to be confidently wrong on an
# ambiguous crop. The genuine finds scored 0.96 and 0.98.
#
# So a rotated reading has to clear three bars, not one: be confident in
# absolute terms, beat the upright reading by a wide margin, and be spelled out
# of characters that belong on a Thai drug bag.
MIN_SCORE_GAIN = 0.25
MIN_ABSOLUTE_SCORE = 0.90

# Thai, ASCII letters/digits, and the punctuation that shows up on these labels.
_ALLOWED_PUNCT = set(" .,:;/()[]{}%-+#&'\"!?*=@\\|_<>")


def plausible_for_corpus(text):
    """Reject readings containing scripts this corpus cannot contain.

    The Thai recognition dictionary still carries CJK and kana, so a rotated
    crop can come back as '店'. Nothing on a Thai pharmacy label is written in
    those, and letting one through would corrupt curated data.
    """
    for ch in text:
        if is_thai(ch) or ch.isascii() and (ch.isalnum() or ch in _ALLOWED_PUNCT):
            continue
        return False
    return True


def imread_unicode(path):
    """cv2.imread cannot open Thai filenames on Windows."""
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def build_engine():
    from paddleocr import PaddleOCR

    return PaddleOCR(
        device="cpu",
        lang="th",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        # PaddleOCR 3.x crashes in oneDNN+PIR on detection; config.yaml disables
        # it for the same reason.
        enable_mkldnn=False,
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_det_limit_side_len=1280,
        text_det_limit_type="max",
    )


def crop_box(img, points, pad_ratio=0.25):
    pts = np.array(points, dtype=np.float32)
    x, y, w, h = cv2.boundingRect(pts.astype(np.int32))
    pad = max(8, int(pad_ratio * max(w, h)))
    y0, y1 = max(0, y - pad), min(img.shape[0], y + h + pad)
    x0, x1 = max(0, x - pad), min(img.shape[1], x + w + pad)
    crop = img[y0:y1, x0:x1]
    if crop.size == 0 or min(crop.shape[:2]) < 4:
        return None
    longest = max(crop.shape[:2])
    if longest < 320:  # recognition does poorly on tiny crops
        s = 320.0 / longest
        crop = cv2.resize(
            crop, (int(crop.shape[1] * s), int(crop.shape[0] * s)),
            interpolation=cv2.INTER_CUBIC,
        )
    return crop


def read(ocr, image):
    """Return (text, mean_confidence, thai_char_count)."""
    try:
        result = ocr.predict(image)
    except Exception:  # noqa: BLE001 - a single unreadable crop must not stop the run
        return "", 0.0, 0
    if not result:
        return "", 0.0, 0
    r = result[0]
    texts = list(r.get("rec_texts", []) if isinstance(r, dict)
                 else getattr(r, "rec_texts", []))
    scores = list(r.get("rec_scores", []) if isinstance(r, dict)
                  else getattr(r, "rec_scores", []))
    text = " ".join(t for t in texts if t).strip()
    mean = float(np.mean(scores)) if scores else 0.0
    return text, mean, sum(1 for c in text if is_thai(c))




def main():
    ap = argparse.ArgumentParser(
        description="Re-read boxes that are printed upside down",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--workspace", default="dataset")
    ap.add_argument("--version", default="v4", help="version file to read")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--images", nargs="+",
                       help="image keys to process, e.g. A117.jpg A118.jpg")
    group.add_argument("--all", action="store_true",
                       help="sweep every image in the version (slow: two OCR "
                            "passes per box)")
    ap.add_argument("--write", action="store_true",
                    help="save to a new version file (default: report only)")
    ap.add_argument("--min-gain", type=float, default=MIN_SCORE_GAIN,
                    help=f"confidence the rotated read must win by (default {MIN_SCORE_GAIN})")
    ap.add_argument("--min-score", type=float, default=MIN_ABSOLUTE_SCORE,
                    help=f"absolute confidence floor (default {MIN_ABSOLUTE_SCORE})")
    args = ap.parse_args()

    ws = REPO_ROOT / "workspaces" / args.workspace
    images_dir = ws / "images"
    version_file = ws / f"{args.version}.json"
    if not version_file.exists():
        print(f"No such version: {version_file}")
        return 1

    data = json.loads(version_file.read_text(encoding="utf-8"))
    annotations = data.get("annotations") or {}

    if args.all:
        targets = sorted(annotations)
        print(f"sweeping all {len(targets)} image(s) in {args.version}")
    else:
        missing = [k for k in args.images if k not in annotations]
        if missing:
            print(f"Not in {args.version}: {', '.join(missing)}")
        targets = [k for k in args.images if k in annotations]
    if not targets:
        return 1

    ocr = build_engine()
    changed_total = 0

    for key in targets:
        path = images_dir / key
        if not path.exists():
            print(f"\n=== {key} — image not on disk, skipped ===")
            continue
        img = imread_unicode(path)
        if img is None:
            print(f"\n=== {key} — unreadable, skipped ===")
            continue

        boxes = annotations[key] or []
        print(f"\n=== {key} ({len(boxes)} boxes) ===")
        changed_here = 0
        rejected = []

        for i, ann in enumerate(boxes):
            old = (ann.get("transcription") or "").strip()
            if old == "###":  # curator marked it ignore; leave it alone
                continue
            crop = crop_box(img, ann.get("points") or [])
            if crop is None:
                continue

            up_text, up_score, up_thai = read(ocr, crop)
            dn_text, dn_score, dn_thai = read(ocr, cv2.rotate(crop, cv2.ROTATE_180))

            if not dn_text:
                continue
            if dn_score < args.min_score:
                continue
            if dn_score < up_score + args.min_gain:
                continue
            if not plausible_for_corpus(dn_text):
                rejected.append((i, old, dn_text, dn_score, "foreign script"))
                continue
            # Never trade a Thai reading for one without Thai: on this corpus
            # that is the model transliterating rather than reading.
            if up_thai and not dn_thai:
                rejected.append((i, old, dn_text, dn_score, "would drop Thai"))
                continue

            print(f"  #{i:2}  {up_score:.2f} -> {dn_score:.2f}   thai {up_thai} -> {dn_thai}")
            print(f"       was: {old!r}")
            print(f"       now: {dn_text!r}")
            ann["transcription"] = dn_text
            # The pixels did not move, only the reading; record why the text
            # changed so a reviewer is not left guessing.
            ann["rotated_180"] = True
            changed_here += 1

        for i, old, new, score, why in rejected:
            print(f"  #{i:2}  rejected ({why}, {score:.2f}): {old!r} -> {new!r}")
        print(f"  {changed_here} accepted, {len(rejected)} rejected")
        changed_total += changed_here

    print(f"\n{changed_total} box(es) would change across {len(targets)} image(s)")

    if not args.write:
        print("\nReport only. Re-run with --write to save to a new version.")
        return 0
    if not changed_total:
        print("Nothing to write.")
        return 0

    out = next_version_path(ws)
    stamp_version(
        data, args.version,
        f"{args.version} with {changed_total} upside-down box(es) re-read "
        f"(scripts/refix_rotated_boxes.py)",
        rotated_boxes_fixed=changed_total,
    )
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWrote {out.name}. {version_file.name} is unchanged — open both in the "
          f"app and compare before switching the workspace over.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
