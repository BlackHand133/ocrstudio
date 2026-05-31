"""Augmentation engine for export.

Generates N randomized copies per image with per-type parameter ranges, a
reproducible seed, and bbox clamping — wrapping the Qt-free AugmentationPipeline
so every export format can reuse it.
"""

from __future__ import annotations

import base64
import random
from typing import List, Optional

import cv2
import numpy as np

from modules.utils import sanitize_filename


def _clip_box(pts, w: int, h: int) -> List[List[float]]:
    """Clamp every point to the image bounds (keeps box count stable)."""
    return [[min(max(float(x), 0.0), float(w)), min(max(float(y), 0.0), float(h))] for x, y in pts]


def _resolve_params(aug_type: str, params: dict, rng: random.Random, jitter: bool) -> dict:
    """Return concrete params; when ``jitter`` (copies > 1), sample within a range
    around the configured value so each copy differs."""
    p = dict(params)
    if not jitter:
        return p
    if aug_type == "rotation":
        a = abs(float(params.get("angle", 3)))
        p["angle"] = rng.uniform(-a, a)
    elif aug_type == "brightness_contrast":
        b = abs(float(params.get("brightness", 15)))
        c = float(params.get("contrast", 1.2)) or 1.0
        p["brightness"] = rng.uniform(-b, b)
        lo, hi = (1.0 / c, c) if c >= 1 else (c, 1.0 / c)
        p["contrast"] = rng.uniform(lo, hi)
    elif aug_type == "blur":
        k = max(3, int(params.get("kernel_size", 5)))
        odd = list(range(3, k + 1, 2)) or [3]
        p["kernel_size"] = rng.choice(odd)
    elif aug_type == "noise":
        inten = float(params.get("intensity", 20))
        p["intensity"] = rng.uniform(inten * 0.3, inten)
    elif aug_type == "perspective":
        s = float(params.get("strength", 0.08))
        p["strength"] = rng.uniform(s * 0.3, s)
    elif aug_type == "sharpen":
        s = float(params.get("strength", 1))
        p["strength"] = rng.uniform(max(0.2, s * 0.5), s * 1.5)
    # grayscale / random_erasing: nothing to jitter (erasing is random internally)
    return p


class _AugRunner:
    """Produces augmented variants of an image (and its boxes)."""

    def __init__(self, aug_config: dict, seed: Optional[int]):
        self.specs = aug_config.get("augmentations", [])
        self.mode = aug_config.get("mode", "combinatorial")
        self.copies = max(1, int(aug_config.get("copies", 1)))
        self.rng = random.Random(0 if seed is None else seed)
        if seed is not None:
            try:
                np.random.seed(int(seed) & 0xFFFFFFFF)
            except Exception:  # noqa: BLE001
                pass

    def _gen(self, img, bboxes):
        from modules.augmentation import AugmentationPipeline

        for c in range(self.copies):
            jitter = self.copies > 1
            tag = f"_{c}" if self.copies > 1 else ""
            if self.mode == "sequential":
                pipe = AugmentationPipeline(mode="sequential")
                for s in self.specs:
                    pipe.add_augmentation(
                        s["type"], _resolve_params(s["type"], s.get("params", {}), self.rng, jitter)
                    )
                for aug_img, aug_bb, name in pipe.apply(img, bboxes):
                    yield f"{sanitize_filename(name)}{tag}", aug_img, aug_bb
            else:
                for s in self.specs:
                    pipe = AugmentationPipeline(mode="combinatorial")
                    pipe.add_augmentation(
                        s["type"], _resolve_params(s["type"], s.get("params", {}), self.rng, jitter)
                    )
                    for aug_img, aug_bb, name in pipe.apply(img, bboxes):
                        yield f"{sanitize_filename(name)}{tag}", aug_img, aug_bb

    def detection(self, img, normal):
        """Yield (suffix, aug_image, boxes) — boxes are ann dicts with clamped points.

        Boxes that a geometric augment pushed (almost) entirely out of frame
        collapse to ~zero area after clamping; drop those so no degenerate box
        lands in the labels.
        """
        pts_list = [a["points"] for a in normal]
        for name, aug_img, aug_bb in self._gen(img, pts_list):
            if aug_img is None or not aug_bb:
                continue
            h, w = aug_img.shape[:2]
            boxes = []
            for orig, pts in zip(normal, aug_bb):
                clamped = _clip_box(pts, w, h)
                xs = [p[0] for p in clamped]
                ys = [p[1] for p in clamped]
                if max(xs) - min(xs) < 1 or max(ys) - min(ys) < 1:
                    continue
                boxes.append({**orig, "points": clamped})
            if boxes:
                yield name, aug_img, boxes

    def recognition(self, crop):
        """Yield (suffix, aug_crop)."""
        for name, aug_img, _bb in self._gen(crop, None):
            if aug_img is None or getattr(aug_img, "size", 0) == 0:
                continue
            yield name, aug_img


def _make_runner(aug_config: Optional[dict], seed: Optional[int]):
    if aug_config and aug_config.get("augmentations"):
        return _AugRunner(aug_config, seed), set(aug_config.get("target_splits", ["train"]))
    return None, set()


def _det_samples(img, normal, runner, do_aug):
    """Yield (suffix, image, boxes): the original, then augmented variants."""
    yield "", img, normal
    if runner and do_aug:
        for suffix, aug_img, boxes in runner.detection(img, normal):
            yield suffix, aug_img, boxes


# ─────────────────────────────────────────────────────────────────────────────
# Preview helpers (count + visual gallery) — used by the export modal
# ─────────────────────────────────────────────────────────────────────────────


def variants_per_item(aug_config: Optional[dict]) -> int:
    """Augmented copies emitted per source item (excludes the original).

    combinatorial → one image per augmentation per copy; sequential → one
    chained image per copy.
    """
    if not aug_config:
        return 0
    specs = aug_config.get("augmentations", [])
    if not specs:
        return 0
    copies = max(1, int(aug_config.get("copies", 1)))
    if aug_config.get("mode", "combinatorial") == "sequential":
        return copies
    return copies * len(specs)


def _draw_boxes(img, boxes) -> np.ndarray:
    """Outline boxes (lists of [x, y]) on a copy so geometric augments are visible."""
    if not boxes:
        return img
    out = img.copy()
    for pts in boxes:
        try:
            arr = np.array([[int(round(x)), int(round(y))] for x, y in pts], dtype=np.int32)
        except (TypeError, ValueError):
            continue
        cv2.polylines(out, [arr], isClosed=True, color=(0, 200, 0), thickness=2)
    return out


def _encode_thumb(img, max_size: int = 360) -> str:
    """Downscale + JPEG-encode to a base64 data URI for inline display."""
    if img is None or getattr(img, "size", 0) == 0:
        return ""
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest > max_size:
        scale = max_size / longest
        img = cv2.resize(
            img, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA
        )
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def render_aug_samples(img, specs, mode, *, boxes=None, max_size: int = 360) -> List[dict]:
    """Demonstrate each selected augmentation on one sample image.

    Returns ``[{"label", "image"(data-uri)}]``: the original first, then each
    augmentation applied once with its configured params, plus the chained
    ``combined`` result when *mode* is sequential. Uses fixed params (no jitter)
    so the gallery is a clean one-per-effect comparison.
    """
    from modules.augmentation import AugmentationPipeline

    def _boxes_copy():
        return [list(b) for b in boxes] if boxes else None

    samples = [{"label": "original", "image": _encode_thumb(_draw_boxes(img, boxes), max_size)}]
    for s in specs:
        pipe = AugmentationPipeline(mode="combinatorial")
        pipe.add_augmentation(s["type"], dict(s.get("params", {})))
        try:
            results = pipe.apply(img, _boxes_copy())
        except Exception:  # noqa: BLE001 — one bad aug shouldn't kill the gallery
            continue
        if not results:
            continue
        aug_img, aug_bb, name = results[0]
        if aug_img is None:
            continue
        shown = _draw_boxes(aug_img, aug_bb) if aug_bb else aug_img
        samples.append({"label": str(name), "image": _encode_thumb(shown, max_size)})
    if mode == "sequential" and len(specs) > 1:
        pipe = AugmentationPipeline(mode="sequential")
        for s in specs:
            pipe.add_augmentation(s["type"], dict(s.get("params", {})))
        try:
            results = pipe.apply(img, _boxes_copy())
        except Exception:  # noqa: BLE001
            results = []
        if results and results[0][0] is not None:
            aug_img, aug_bb, _name = results[0]
            shown = _draw_boxes(aug_img, aug_bb) if aug_bb else aug_img
            samples.append({"label": "combined", "image": _encode_thumb(shown, max_size)})
    return samples
