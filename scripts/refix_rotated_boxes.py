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

    # check the changes by eye first — opens as one page in a browser
    python scripts/refix_rotated_boxes.py --all --review-queue review/

Use --review-queue before trusting a run. Confidence separates noise from text
but not a correct reading from a confident guess: in a 28-box sweep two got
through, one of them a correctly-oriented box holding nothing but the vowel
marks floating above a word, scored 0.97.

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


def review_crop(img, points, pad_ratio=0.9):
    """Crop with generous context and the box outlined, both ways up.

    Returns (upright, rotated). The pair is the point: a box that was never
    upside down looks wrong on the right-hand side, which is the one thing a
    confidence score cannot tell you. One accepted change in a 28-box run
    turned out to be a correctly-oriented crop containing only the vowel marks
    floating above a word — high confidence, no text in it at all.
    """
    pts = np.array(points, dtype=np.int32)
    x, y, w, h = cv2.boundingRect(pts)
    marked = img.copy()
    cv2.polylines(marked, [pts], True, (0, 0, 255), max(2, int(max(w, h) * 0.03)))
    pad = max(30, int(pad_ratio * max(w, h)))
    y0, y1 = max(0, y - pad), min(img.shape[0], y + h + pad)
    x0, x1 = max(0, x - pad), min(img.shape[1], x + w + pad)
    crop = marked[y0:y1, x0:x1]
    if crop.size == 0:
        return None, None
    scale = max(1, int(320 / max(crop.shape[:2])))
    if scale > 1:
        crop = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                          interpolation=cv2.INTER_CUBIC)
    return crop, cv2.rotate(crop, cv2.ROTATE_180)


REVIEW_CSS = """
body{font:14px system-ui,sans-serif;margin:0;padding:24px;background:#f6f6f4;color:#2c2c2a}
h1{font-size:18px;margin:0 0 4px}
.sub{color:#5f5e5a;margin-bottom:20px}
.card{background:#fff;border:1px solid #d3d1c7;border-radius:8px;padding:14px;margin-bottom:14px}
.card.rejected{border-color:#f7c1c1;background:#fffafa}
.hdr{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px}
.id{font-weight:600}
.tag{font-size:12px;padding:2px 8px;border-radius:10px;background:#eaf3de;color:#3b6d11}
.tag.no{background:#fcebeb;color:#a32d2d}
.pair{display:flex;gap:14px;flex-wrap:wrap}
figure{margin:0}
figcaption{font-size:12px;color:#5f5e5a;margin-top:4px}
img{max-width:100%;border:1px solid #d3d1c7;border-radius:4px;display:block}
table{border-collapse:collapse;margin-top:10px;font-size:13px}
td{padding:2px 10px 2px 0;vertical-align:top}
td.k{color:#5f5e5a;white-space:nowrap}
code{background:#f1efe8;padding:1px 5px;border-radius:3px}
"""


def write_review_queue(out_dir, entries, version, accepted, rejected):
    """Write the crops plus a single page that shows them all."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, e in enumerate(entries, 1):
        stem = f"{n:03d}_{e['key'].replace('.', '_')}_{e['index']}"
        cv2.imwrite(str(out_dir / f"{stem}_up.png"), e["upright"])
        cv2.imwrite(str(out_dir / f"{stem}_rot.png"), e["rotated"])
        cls = "card" if e["accepted"] else "card rejected"
        tag = ('<span class="tag">accepted</span>' if e["accepted"]
               else f'<span class="tag no">rejected: {esc(e["reason"])}</span>')
        rows.append(f"""<div class="{cls}">
  <div class="hdr"><span class="id">{esc(e['key'])} &middot; box #{e['index']}</span>{tag}</div>
  <div class="pair">
    <figure><img src="{stem}_up.png" alt=""><figcaption>as stored</figcaption></figure>
    <figure><img src="{stem}_rot.png" alt=""><figcaption>rotated 180&deg;</figcaption></figure>
  </div>
  <table>
    <tr><td class="k">current label</td><td><code>{esc(e['old'])}</code></td></tr>
    <tr><td class="k">upright read</td><td><code>{esc(e['up_text'])}</code> &nbsp;{e['up_score']:.2f}</td></tr>
    <tr><td class="k">rotated read</td><td><code>{esc(e['dn_text'])}</code> &nbsp;{e['dn_score']:.2f}</td></tr>
  </table>
</div>""")

    html = f"""<!doctype html><meta charset="utf-8">
<title>Rotation review &middot; {esc(version)}</title>
<style>{REVIEW_CSS}</style>
<h1>Rotation review &mdash; {esc(version)}</h1>
<div class="sub">{accepted} accepted, {rejected} rejected.
Check the right-hand image actually reads the right way up: a correctly
oriented box looks wrong there, and no confidence score catches that.</div>
{''.join(rows)}"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    return out_dir / "index.html"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


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
    ap.add_argument("--review-queue", metavar="DIR",
                    help="write every changed and rejected box to DIR as a "
                         "browsable page, both ways up, for checking by eye")
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
    rejected_total = 0
    review = [] if args.review_queue else None

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

            def queue(accepted, reason=""):
                """Record this box for the review page, if one was asked for."""
                if review is None:
                    return
                up_img, dn_img = review_crop(img, ann.get("points") or [])
                if up_img is None:
                    return
                review.append({
                    "key": key, "index": i, "old": old,
                    "up_text": up_text, "up_score": up_score,
                    "dn_text": dn_text, "dn_score": dn_score,
                    "upright": up_img, "rotated": dn_img,
                    "accepted": accepted, "reason": reason,
                })

            if not dn_text:
                continue
            if dn_score < args.min_score:
                continue
            if dn_score < up_score + args.min_gain:
                continue
            if not plausible_for_corpus(dn_text):
                rejected.append((i, old, dn_text, dn_score, "foreign script"))
                queue(False, "foreign script")
                continue
            # Never trade a Thai reading for one without Thai: on this corpus
            # that is the model transliterating rather than reading.
            if up_thai and not dn_thai:
                rejected.append((i, old, dn_text, dn_score, "would drop Thai"))
                queue(False, "would drop Thai")
                continue

            queue(True)
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
        rejected_total += len(rejected)

    print(f"\n{changed_total} box(es) would change across {len(targets)} image(s)")

    if review is not None:
        if review:
            page = write_review_queue(Path(args.review_queue), review,
                                      args.version, changed_total, rejected_total)
            print(f"Review queue: {page} ({len(review)} box(es)) — open it before "
                  f"trusting the result.")
        else:
            print("Review queue: nothing to review.")

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
