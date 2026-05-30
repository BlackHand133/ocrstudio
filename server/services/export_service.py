"""Headless dataset export (no Qt).

Produces PaddleOCR detection/recognition datasets plus ICDAR-2015, COCO, YOLO
and CSV/JSONL manifests, all from the same Qt-free helpers so output matches the
desktop app's PaddleOCR format.

Shared building blocks:
  * ``_split``        — percentage / fixed-count / stratified splitting (DataSplitter)
  * ``_AugRunner``    — augmentation with N randomized copies, param ranges, a
                        reproducible seed, and bbox clamping (works for every format)
  * ``_det_samples``  — yields (suffix, image, boxes): original first, then augmented
"""

from __future__ import annotations

import csv
import json
import os
import random
from typing import Callable, Dict, List, Optional

import cv2
import numpy as np

from modules.data.splitter import DataSplitter
from modules.export.utils import (
    ExportValidationError,
    crop_bounding_box,
    crop_rotated_box,
    is_mask_item,
    is_valid_box,
)
from modules.utils import imread_unicode, imwrite_unicode, sanitize_annotations, sanitize_filename

PLACEHOLDER_TEXT = "<no_label>"

ProgressFn = Optional[Callable[[int, int], None]]

# Stored angle = total clockwise rotation applied to the original image.
_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def _apply_rotation(img, angle: int):
    code = _ROTATE_CODES.get(int(angle) % 360)
    return cv2.rotate(img, code) if code is not None else img


def _apply_masks(img, mask_items):
    """Censor mask regions on the image: solid fill, blur, or pixelate.

    The effect is confined to each mask's polygon.
    """
    if not mask_items:
        return img
    out = img.copy()
    h_img, w_img = out.shape[:2]
    for m in mask_items:
        pts = m.get("points", [])
        if not is_valid_box(pts):
            continue
        poly = np.array(pts, dtype=np.int32)
        mode = (m.get("mask_mode") or "solid").lower()
        x, y, w, h = cv2.boundingRect(poly)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(w_img, x + w), min(h_img, y + h)
        if x1 <= x0 or y1 <= y0:
            continue

        if mode == "solid":
            hexc = (m.get("mask_color") or "#000000").lstrip("#")
            if len(hexc) >= 6:
                r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
            else:
                r = g = b = 0
            cv2.fillPoly(out, [poly], (b, g, r))
            continue

        roi = out[y0:y1, x0:x1].copy()
        rh, rw = roi.shape[:2]
        if mode == "blur":
            k = max(3, (min(rw, rh) // 3) | 1)
            proc = cv2.GaussianBlur(roi, (k, k), 0)
        elif mode == "pixelate":
            pw, ph = max(1, rw // 12), max(1, rh // 12)
            proc = cv2.resize(
                cv2.resize(roi, (pw, ph), interpolation=cv2.INTER_LINEAR),
                (rw, rh),
                interpolation=cv2.INTER_NEAREST,
            )
        else:
            proc = roi

        region_mask = np.zeros((rh, rw), dtype=np.uint8)
        cv2.fillPoly(region_mask, [poly - [x0, y0]], 255)
        region = out[y0:y1, x0:x1]
        region[region_mask == 255] = proc[region_mask == 255]
        out[y0:y1, x0:x1] = region
    return out


def _stem(key: str) -> str:
    return sanitize_filename(os.path.splitext(key)[0]) or "img"


def _text_of(a) -> str:
    return a.get("transcription", "").strip()


def _quad4(points) -> List[List[int]]:
    """ICDAR-2015 is strictly 4-point; reduce polygons to their bounding quad."""
    if len(points) == 4:
        return [[int(round(x)), int(round(y))] for x, y in points]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, y0 = int(round(min(xs))), int(round(min(ys)))
    x1, y1 = int(round(max(xs))), int(round(max(ys)))
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _clip_box(pts, w: int, h: int) -> List[List[float]]:
    """Clamp every point to the image bounds (keeps box count stable)."""
    return [[min(max(float(x), 0.0), float(w)), min(max(float(y), 0.0), float(h))] for x, y in pts]


def _eligible_det_keys(source_index, annotations, selected_keys) -> List[str]:
    return [
        k
        for k, anns in annotations.items()
        if anns
        and k in source_index
        and (selected_keys is None or k in selected_keys)
        and any(not is_mask_item(a) and is_valid_box(a.get("points", [])) for a in anns)
    ]


def _prep_det_image(source_index, key, annotations, rotations):
    """Load an image, apply stored rotation + burn in censor masks.

    Returns ``(image, normal_boxes)`` where ``normal_boxes`` excludes mask items.
    """
    img = imread_unicode(source_index[key])
    if img is None:
        return None, []
    if rotations and rotations.get(key):
        img = _apply_rotation(img, rotations[key])
    anns = annotations[key]
    masks = [a for a in anns if is_mask_item(a)]
    normal = [a for a in anns if not is_mask_item(a) and is_valid_box(a.get("points", []))]
    if masks:
        img = _apply_masks(img, masks)
    return img, normal


def _density(keys, annotations) -> Dict[str, int]:
    return {
        k: sum(
            1
            for a in annotations.get(k, [])
            if not is_mask_item(a) and is_valid_box(a.get("points", []))
        )
        for k in keys
    }


# ─────────────────────────────────────────────────────────────────────────────
# Splitting — percentage (default), fixed count, or stratified by a score.
# ─────────────────────────────────────────────────────────────────────────────


def _split(
    items: List,
    splits: Dict[str, float],
    seed: Optional[int],
    *,
    mode: str = "percentage",
    counts: Optional[Dict[str, int]] = None,
    stratify_scores: Optional[Dict] = None,
    n_bins: int = 3,
) -> Dict[str, List]:
    sp = DataSplitter(seed=seed)
    if mode == "count" and counts:
        return sp.split_by_count(
            items,
            int(counts.get("train", 0)),
            int(counts.get("test", 0)),
            int(counts.get("valid", 0)),
        )
    if mode == "stratified" and stratify_scores:
        return sp.split_by_density_stratified(
            items,
            stratify_scores,
            splits.get("train", 0),
            splits.get("test", 0),
            splits.get("valid", 0),
            n_bins=n_bins,
        )
    return sp.split_by_percentage(
        items,
        train_pct=splits.get("train", 0),
        test_pct=splits.get("test", 0),
        valid_pct=splits.get("valid", 0),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Augmentation — N randomized copies, per-type parameter ranges, reproducible
# seed, and bbox clamping. Wraps the Qt-free AugmentationPipeline.
# ─────────────────────────────────────────────────────────────────────────────


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
        """Yield (suffix, aug_image, boxes) — boxes are ann dicts with clamped points."""
        pts_list = [a["points"] for a in normal]
        for name, aug_img, aug_bb in self._gen(img, pts_list):
            if aug_img is None or not aug_bb:
                continue
            h, w = aug_img.shape[:2]
            boxes = [{**orig, "points": _clip_box(pts, w, h)} for orig, pts in zip(normal, aug_bb)]
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


def _fname(stem: str, suffix: str, fmt: str) -> str:
    return f"{stem}_{suffix}.{fmt}" if suffix else f"{stem}.{fmt}"


# ─────────────────────────────────────────────────────────────────────────────
# Detection exporters
# ─────────────────────────────────────────────────────────────────────────────


def _det_split(keys, annotations, splits, seed, split_mode, counts, n_bins):
    strat = _density(keys, annotations) if split_mode == "stratified" else None
    return _split(
        keys, splits, seed, mode=split_mode, counts=counts, stratify_scores=strat, n_bins=n_bins
    )


def export_detection(
    *,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed=None,
    image_format="png",
    selected_keys=None,
    rotations=None,
    aug_config=None,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    progress: ProgressFn = None,
) -> dict:
    """PaddleOCR detection: ``img/<split>/*`` + ``labels_<split>.txt`` + ``labels_all.txt``."""
    keys = _eligible_det_keys(source_index, annotations, selected_keys)
    if not keys:
        raise ExportValidationError("No annotated images to export for detection.")
    split_result = _det_split(keys, annotations, splits, seed, split_mode, counts, n_bins)
    runner, aug_targets = _make_runner(aug_config, seed)
    dataset_dir = os.path.join(out_dir, folder_name)
    img_dir = os.path.join(dataset_dir, "img")
    all_labels: Dict[str, list] = {s: [] for s in split_result}
    total = sum(len(v) for v in split_result.values())
    done = 0
    for split_name, split_keys in split_result.items():
        sdir = os.path.join(img_dir, split_name)
        os.makedirs(sdir, exist_ok=True)
        for key in split_keys:
            done += 1
            img, normal = _prep_det_image(source_index, key, annotations, rotations)
            if progress:
                progress(done, total)
            if img is None or not normal:
                continue
            for suffix, im, boxes in _det_samples(img, normal, runner, split_name in aug_targets):
                fn = _fname(_stem(key), suffix, image_format)
                if not imwrite_unicode(os.path.join(sdir, fn), im, image_format=image_format):
                    continue
                label = sanitize_annotations(
                    [
                        {
                            "transcription": (_text_of(a) or PLACEHOLDER_TEXT),
                            "points": [[int(round(x)), int(round(y))] for x, y in a["points"]],
                            "difficult": bool(a.get("difficult", False)),
                        }
                        for a in boxes
                    ]
                )
                all_labels[split_name].append((f"img/{split_name}/{fn}", label))
    os.makedirs(dataset_dir, exist_ok=True)
    with open(os.path.join(dataset_dir, "labels_all.txt"), "w", encoding="utf-8") as fa:
        for split_name, labels in all_labels.items():
            with open(
                os.path.join(dataset_dir, f"labels_{split_name}.txt"), "w", encoding="utf-8"
            ) as f:
                for rel, label in labels:
                    line = f"{rel}\t{json.dumps(label, ensure_ascii=False)}\n"
                    f.write(line)
                    fa.write(line)
    stats = {s: len(v) for s, v in all_labels.items()}
    return {
        "kind": "detection",
        "folder": folder_name,
        "splits": stats,
        "total": sum(stats.values()),
    }


def export_icdar(
    *,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed=None,
    image_format="png",
    selected_keys=None,
    rotations=None,
    aug_config=None,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    progress: ProgressFn = None,
) -> dict:
    """ICDAR-2015: ``<split>/images/*`` + ``<split>/gt/gt_<stem>.txt``
    (``x1,y1,...,x4,y4,transcription``; ``###`` = ignore)."""
    keys = _eligible_det_keys(source_index, annotations, selected_keys)
    if not keys:
        raise ExportValidationError("No annotated images to export for detection.")
    split_result = _det_split(keys, annotations, splits, seed, split_mode, counts, n_bins)
    runner, aug_targets = _make_runner(aug_config, seed)
    dataset_dir = os.path.join(out_dir, folder_name)
    total = sum(len(v) for v in split_result.values())
    done = 0
    counts_out: Dict[str, int] = {}
    for split_name, split_keys in split_result.items():
        img_dir = os.path.join(dataset_dir, split_name, "images")
        gt_dir = os.path.join(dataset_dir, split_name, "gt")
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(gt_dir, exist_ok=True)
        n = 0
        for key in split_keys:
            done += 1
            img, normal = _prep_det_image(source_index, key, annotations, rotations)
            if progress:
                progress(done, total)
            if img is None or not normal:
                continue
            for suffix, im, boxes in _det_samples(img, normal, runner, split_name in aug_targets):
                stem = f"{_stem(key)}_{suffix}" if suffix else _stem(key)
                if not imwrite_unicode(
                    os.path.join(img_dir, f"{stem}.{image_format}"), im, image_format=image_format
                ):
                    continue
                lines = []
                for a in boxes:
                    quad = _quad4(a["points"])
                    coords = ",".join(str(c) for p in quad for c in p)
                    text = _text_of(a)
                    if not text or a.get("difficult"):
                        text = "###"
                    lines.append(f"{coords},{text}")
                with open(os.path.join(gt_dir, f"gt_{stem}.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + ("\n" if lines else ""))
                n += 1
        counts_out[split_name] = n
    return {
        "kind": "detection",
        "folder": folder_name,
        "splits": counts_out,
        "total": sum(counts_out.values()),
    }


def export_coco(
    *,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed=None,
    image_format="png",
    selected_keys=None,
    rotations=None,
    aug_config=None,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    progress: ProgressFn = None,
) -> dict:
    """COCO detection: ``<split>/images/*`` + ``<split>/instances.json``."""
    keys = _eligible_det_keys(source_index, annotations, selected_keys)
    if not keys:
        raise ExportValidationError("No annotated images to export for detection.")
    split_result = _det_split(keys, annotations, splits, seed, split_mode, counts, n_bins)
    runner, aug_targets = _make_runner(aug_config, seed)
    dataset_dir = os.path.join(out_dir, folder_name)
    total = sum(len(v) for v in split_result.values())
    done = 0
    counts_out: Dict[str, int] = {}
    for split_name, split_keys in split_result.items():
        img_dir = os.path.join(dataset_dir, split_name, "images")
        os.makedirs(img_dir, exist_ok=True)
        coco: dict = {
            "images": [],
            "annotations": [],
            "categories": [{"id": 1, "name": "text", "supercategory": "text"}],
        }
        ann_id = 1
        img_id = 0
        for key in split_keys:
            done += 1
            img, normal = _prep_det_image(source_index, key, annotations, rotations)
            if progress:
                progress(done, total)
            if img is None or not normal:
                continue
            for suffix, im, boxes in _det_samples(img, normal, runner, split_name in aug_targets):
                stem = f"{_stem(key)}_{suffix}" if suffix else _stem(key)
                fn = f"{stem}.{image_format}"
                if not imwrite_unicode(os.path.join(img_dir, fn), im, image_format=image_format):
                    continue
                img_id += 1
                h, w = im.shape[:2]
                coco["images"].append(
                    {"id": img_id, "file_name": fn, "width": int(w), "height": int(h)}
                )
                for a in boxes:
                    pts = [[float(x), float(y)] for x, y in a["points"]]
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    x0, y0 = min(xs), min(ys)
                    bw, bh = max(xs) - x0, max(ys) - y0
                    coco["annotations"].append(
                        {
                            "id": ann_id,
                            "image_id": img_id,
                            "category_id": 1,
                            "bbox": [round(x0, 2), round(y0, 2), round(bw, 2), round(bh, 2)],
                            "area": round(bw * bh, 2),
                            "segmentation": [[round(c, 2) for p in pts for c in p]],
                            "iscrowd": 0,
                            "text": _text_of(a),
                            "ignore": 1 if a.get("difficult") else 0,
                        }
                    )
                    ann_id += 1
        with open(
            os.path.join(dataset_dir, split_name, "instances.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(coco, f, ensure_ascii=False)
        counts_out[split_name] = len(coco["images"])
    return {
        "kind": "detection",
        "folder": folder_name,
        "splits": counts_out,
        "total": sum(counts_out.values()),
    }


def export_yolo(
    *,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed=None,
    image_format="png",
    selected_keys=None,
    rotations=None,
    aug_config=None,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    progress: ProgressFn = None,
) -> dict:
    """Ultralytics YOLO: ``images/<split>/*`` + ``labels/<split>/*.txt`` + ``data.yaml``."""
    keys = _eligible_det_keys(source_index, annotations, selected_keys)
    if not keys:
        raise ExportValidationError("No annotated images to export for detection.")
    split_result = _det_split(keys, annotations, splits, seed, split_mode, counts, n_bins)
    runner, aug_targets = _make_runner(aug_config, seed)
    dataset_dir = os.path.join(out_dir, folder_name)
    total = sum(len(v) for v in split_result.values())
    done = 0
    counts_out: Dict[str, int] = {}
    for split_name, split_keys in split_result.items():
        img_dir = os.path.join(dataset_dir, "images", split_name)
        lbl_dir = os.path.join(dataset_dir, "labels", split_name)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)
        n = 0
        for key in split_keys:
            done += 1
            img, normal = _prep_det_image(source_index, key, annotations, rotations)
            if progress:
                progress(done, total)
            if img is None or not normal:
                continue
            for suffix, im, boxes in _det_samples(img, normal, runner, split_name in aug_targets):
                h, w = im.shape[:2]
                if w <= 0 or h <= 0:
                    continue
                stem = f"{_stem(key)}_{suffix}" if suffix else _stem(key)
                if not imwrite_unicode(
                    os.path.join(img_dir, f"{stem}.{image_format}"), im, image_format=image_format
                ):
                    continue
                lines = []
                for a in boxes:
                    xs = [p[0] for p in a["points"]]
                    ys = [p[1] for p in a["points"]]
                    x0, x1 = max(0.0, min(xs)), min(float(w), max(xs))
                    y0, y1 = max(0.0, min(ys)), min(float(h), max(ys))
                    bw, bh = (x1 - x0) / w, (y1 - y0) / h
                    if bw <= 0 or bh <= 0:
                        continue
                    cx, cy = ((x0 + x1) / 2) / w, ((y0 + y1) / 2) / h
                    lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                with open(os.path.join(lbl_dir, f"{stem}.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + ("\n" if lines else ""))
                n += 1
        counts_out[split_name] = n

    yaml_key = {"train": "train", "valid": "val", "test": "test"}
    ydata = ["path: ."]
    for split_name, c in counts_out.items():
        if c:
            ydata.append(f"{yaml_key.get(split_name, split_name)}: images/{split_name}")
    ydata += ["nc: 1", "names: ['text']"]
    with open(os.path.join(dataset_dir, "data.yaml"), "w", encoding="utf-8") as f:
        f.write("\n".join(ydata) + "\n")
    return {
        "kind": "detection",
        "folder": folder_name,
        "splits": counts_out,
        "total": sum(counts_out.values()),
    }


def export_manifest_detection(
    *,
    fmt,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed=None,
    image_format="png",
    selected_keys=None,
    rotations=None,
    aug_config=None,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    progress: ProgressFn = None,
) -> dict:
    """CSV / JSONL detection manifest under ``img/<split>/``."""
    keys = _eligible_det_keys(source_index, annotations, selected_keys)
    if not keys:
        raise ExportValidationError("No annotated images to export for detection.")
    split_result = _det_split(keys, annotations, splits, seed, split_mode, counts, n_bins)
    runner, aug_targets = _make_runner(aug_config, seed)
    dataset_dir = os.path.join(out_dir, folder_name)
    os.makedirs(dataset_dir, exist_ok=True)
    total = sum(len(v) for v in split_result.values())
    done = 0
    counts_out: Dict[str, int] = {}
    for split_name, split_keys in split_result.items():
        img_dir = os.path.join(dataset_dir, "img", split_name)
        os.makedirs(img_dir, exist_ok=True)
        rows: List[list] = []
        records: List[dict] = []
        for key in split_keys:
            done += 1
            img, normal = _prep_det_image(source_index, key, annotations, rotations)
            if progress:
                progress(done, total)
            if img is None or not normal:
                continue
            for suffix, im, boxes in _det_samples(img, normal, runner, split_name in aug_targets):
                h, w = im.shape[:2]
                fn = _fname(_stem(key), suffix, image_format)
                if not imwrite_unicode(os.path.join(img_dir, fn), im, image_format=image_format):
                    continue
                rel = f"img/{split_name}/{fn}"
                jboxes = []
                for a in boxes:
                    pts = [[int(round(x)), int(round(y))] for x, y in a["points"]]
                    jboxes.append(
                        {
                            "transcription": _text_of(a),
                            "points": pts,
                            "difficult": bool(a.get("difficult")),
                        }
                    )
                    rows.append(
                        [
                            rel,
                            json.dumps(pts, ensure_ascii=False),
                            _text_of(a),
                            int(bool(a.get("difficult"))),
                        ]
                    )
                records.append({"image": rel, "width": int(w), "height": int(h), "boxes": jboxes})
        if fmt == "csv":
            with open(
                os.path.join(dataset_dir, f"{split_name}.csv"), "w", encoding="utf-8", newline=""
            ) as f:
                writer = csv.writer(f)
                writer.writerow(["image", "points", "transcription", "difficult"])
                writer.writerows(rows)
        else:
            with open(os.path.join(dataset_dir, f"{split_name}.jsonl"), "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        counts_out[split_name] = len(records)
    return {
        "kind": "detection",
        "folder": folder_name,
        "splits": counts_out,
        "total": sum(counts_out.values()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Recognition exporters
# ─────────────────────────────────────────────────────────────────────────────


def _collect_crops(annotations, source_index, selected_keys):
    crops: List[tuple] = []
    masks_by_key: Dict[str, list] = {}
    for key, anns in annotations.items():
        if key not in source_index:
            continue
        if selected_keys is not None and key not in selected_keys:
            continue
        masks_by_key[key] = [a for a in anns if is_mask_item(a)]
        for idx, a in enumerate(anns):
            if is_mask_item(a):
                continue
            pts = a.get("points", [])
            if not is_valid_box(pts):
                continue
            crops.append((key, idx, pts, a.get("transcription", "").strip() or PLACEHOLDER_TEXT))
    return crops, masks_by_key


def _split_rec(crops, splits, seed, *, group_by_image, mode, counts, n_bins):
    """Split crops. When ``group_by_image`` all crops of one image stay in the
    same split (prevents train/valid leakage); stratified uses avg text length."""
    if group_by_image:
        keys = list(dict.fromkeys(c[0] for c in crops))
        strat = None
        if mode == "stratified":
            lens: Dict[str, list] = {}
            for k, _idx, _pts, text in crops:
                if text != PLACEHOLDER_TEXT:
                    lens.setdefault(k, []).append(len(text))
            strat = {k: (sum(lens[k]) / len(lens[k]) if lens.get(k) else 0.0) for k in keys}
        key_split = _split(
            keys, splits, seed, mode=mode, counts=counts, stratify_scores=strat, n_bins=n_bins
        )
        k2s = {k: s for s, ks in key_split.items() for k in ks}
        result: Dict[str, list] = {s: [] for s in key_split}
        for c in crops:
            s = k2s.get(c[0])
            if s is not None:
                result[s].append(c)
        return result
    return _split(crops, splits, seed, mode=mode, counts=counts, n_bins=n_bins)


def _rec_crop_image(im, pts, crop_method, auto_orient, classifier):
    crop_fn = crop_rotated_box if crop_method == "rotated" else crop_bounding_box
    crop = crop_fn(im, pts, auto_detect=auto_orient, orientation_classifier=classifier)
    if crop is None or getattr(crop, "size", 0) == 0:
        return None
    if crop.shape[0] < 3 or crop.shape[1] < 3:
        return None
    return crop


def _write_recognition(
    *,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed,
    image_format,
    crop_method,
    selected_keys,
    rotations,
    aug_config,
    auto_orient,
    split_mode,
    counts,
    n_bins,
    group_by_image,
    progress,
    finalize,
):
    """Shared recognition driver. ``finalize(dataset_dir, lines_by_split)`` writes
    the label files for the concrete format."""
    classifier = None
    if auto_orient:
        try:
            from modules.core.ocr.orientation import create_orientation_classifier

            classifier = create_orientation_classifier()
        except Exception:  # noqa: BLE001
            classifier = None

    crops, masks_by_key = _collect_crops(annotations, source_index, selected_keys)
    if not crops:
        raise ExportValidationError("No valid annotations to export for recognition.")
    split_result = _split_rec(
        crops,
        splits,
        seed,
        group_by_image=group_by_image,
        mode=split_mode,
        counts=counts,
        n_bins=n_bins,
    )
    runner, aug_targets = _make_runner(aug_config, seed)
    dataset_dir = os.path.join(out_dir, folder_name)
    img_base = os.path.join(dataset_dir, "images")
    os.makedirs(dataset_dir, exist_ok=True)
    img_cache: Dict[str, object] = {}
    lines_by_split: Dict[str, List[tuple]] = {s: [] for s in split_result}
    total = sum(len(v) for v in split_result.values())
    done = 0
    for split_name, items in split_result.items():
        sdir = os.path.join(img_base, split_name)
        os.makedirs(sdir, exist_ok=True)
        for key, idx, pts, text in items:
            done += 1
            if progress:
                progress(done, total)
            if key not in img_cache:
                im = imread_unicode(source_index[key])
                if im is not None and rotations and rotations.get(key):
                    im = _apply_rotation(im, rotations[key])
                if im is not None and masks_by_key.get(key):
                    im = _apply_masks(im, masks_by_key[key])
                img_cache[key] = im
            im = img_cache[key]
            if im is None:
                continue
            crop = _rec_crop_image(im, pts, crop_method, auto_orient, classifier)
            if crop is None:
                continue
            fn = f"{_stem(key)}_{idx}.{image_format}"
            if imwrite_unicode(os.path.join(sdir, fn), crop, image_format=image_format):
                lines_by_split[split_name].append((f"images/{split_name}/{fn}", text))
            if runner and split_name in aug_targets:
                for suffix, aug_crop in runner.recognition(crop):
                    afn = f"{_stem(key)}_{idx}_{suffix}.{image_format}"
                    if imwrite_unicode(
                        os.path.join(sdir, afn), aug_crop, image_format=image_format
                    ):
                        lines_by_split[split_name].append((f"images/{split_name}/{afn}", text))
    finalize(dataset_dir, lines_by_split)
    stats = {s: len(v) for s, v in lines_by_split.items()}
    return {
        "kind": "recognition",
        "folder": folder_name,
        "splits": stats,
        "total": sum(stats.values()),
    }


def export_recognition(
    *,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed=None,
    image_format="png",
    crop_method="bbox",
    selected_keys=None,
    rotations=None,
    aug_config=None,
    auto_orient=False,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    group_by_image=True,
    progress: ProgressFn = None,
) -> dict:
    """PaddleOCR recognition: ``images/<split>/*`` + ``<split>.txt`` (``relpath\\ttext``)."""

    def finalize(dataset_dir, lines_by_split):
        for split_name, lines in lines_by_split.items():
            with open(os.path.join(dataset_dir, f"{split_name}.txt"), "w", encoding="utf-8") as f:
                for rel, text in lines:
                    f.write(f"{rel}\t{text}\n")

    return _write_recognition(
        source_index=source_index,
        annotations=annotations,
        out_dir=out_dir,
        folder_name=folder_name,
        splits=splits,
        seed=seed,
        image_format=image_format,
        crop_method=crop_method,
        selected_keys=selected_keys,
        rotations=rotations,
        aug_config=aug_config,
        auto_orient=auto_orient,
        split_mode=split_mode,
        counts=counts,
        n_bins=n_bins,
        group_by_image=group_by_image,
        progress=progress,
        finalize=finalize,
    )


def export_manifest_recognition(
    *,
    fmt,
    source_index,
    annotations,
    out_dir,
    folder_name,
    splits,
    seed=None,
    image_format="png",
    crop_method="bbox",
    selected_keys=None,
    rotations=None,
    aug_config=None,
    auto_orient=False,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    group_by_image=True,
    progress: ProgressFn = None,
) -> dict:
    """CSV / JSONL recognition manifest (``image,text`` / ``{image,text}``)."""

    def finalize(dataset_dir, lines_by_split):
        for split_name, lines in lines_by_split.items():
            if fmt == "csv":
                with open(
                    os.path.join(dataset_dir, f"{split_name}.csv"),
                    "w",
                    encoding="utf-8",
                    newline="",
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow(["image", "text"])
                    writer.writerows([[rel, text] for rel, text in lines])
            else:
                with open(
                    os.path.join(dataset_dir, f"{split_name}.jsonl"), "w", encoding="utf-8"
                ) as f:
                    for rel, text in lines:
                        f.write(json.dumps({"image": rel, "text": text}, ensure_ascii=False) + "\n")

    return _write_recognition(
        source_index=source_index,
        annotations=annotations,
        out_dir=out_dir,
        folder_name=folder_name,
        splits=splits,
        seed=seed,
        image_format=image_format,
        crop_method=crop_method,
        selected_keys=selected_keys,
        rotations=rotations,
        aug_config=aug_config,
        auto_orient=auto_orient,
        split_mode=split_mode,
        counts=counts,
        n_bins=n_bins,
        group_by_image=group_by_image,
        progress=progress,
        finalize=finalize,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Split preview — counts only, no file I/O (for the Export dialog).
# ─────────────────────────────────────────────────────────────────────────────


def preview_split(
    *,
    kind,
    source_index,
    annotations,
    splits,
    seed=None,
    selected_keys=None,
    split_mode="percentage",
    counts=None,
    n_bins=3,
    group_by_image=True,
) -> dict:
    """Return ``{"unit": "...", "total": N, "splits": {...}}`` without writing files."""
    if kind == "detection":
        keys = _eligible_det_keys(source_index, annotations, selected_keys)
        if not keys:
            return {"unit": "images", "total": 0, "splits": {}}
        sr = _det_split(keys, annotations, splits, seed, split_mode, counts, n_bins)
        return {"unit": "images", "total": len(keys), "splits": {s: len(v) for s, v in sr.items()}}
    crops, _ = _collect_crops(annotations, source_index, selected_keys)
    if not crops:
        return {"unit": "crops", "total": 0, "splits": {}}
    sr = _split_rec(
        crops,
        splits,
        seed,
        group_by_image=group_by_image,
        mode=split_mode,
        counts=counts,
        n_bins=n_bins,
    )
    return {"unit": "crops", "total": len(crops), "splits": {s: len(v) for s, v in sr.items()}}
