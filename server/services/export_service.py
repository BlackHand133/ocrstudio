"""Headless dataset export (no Qt).

Re-implements the orchestration of the desktop DetectionExporter /
RecognitionExporter using the same Qt-free helpers in ``modules.export.utils``
and ``modules.data.splitter``, so output is byte-compatible with the PaddleOCR
format the desktop app produces.

Augmentation and ML auto-orientation are intentionally omitted here (Phase 4);
``crop_*`` is called with ``auto_detect=False`` so no model is required.
"""

from __future__ import annotations

import json
import os
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

    The effect is confined to each mask's polygon. Replaces the desktop's
    solid-only draw_masks_on_image so the web export supports redaction styles.
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


def _build_pipeline(aug_config: Optional[dict]):
    """Return (pipeline, target_splits) or (None, set()).

    AugmentationPipeline uses only cv2/PIL/numpy — no extra dependency.
    """
    if not aug_config or not aug_config.get("augmentations"):
        return None, set()
    from modules.augmentation import AugmentationPipeline

    pipeline = AugmentationPipeline(mode=aug_config.get("mode", "combinatorial"))
    for a in aug_config["augmentations"]:
        pipeline.add_augmentation(a["type"], a.get("params", {}))
    return pipeline, set(aug_config.get("target_splits", ["train"]))


def _split(items: List, splits: Dict[str, float], seed: Optional[int]) -> Dict[str, List]:
    splitter = DataSplitter(seed=seed)
    return splitter.split_by_percentage(
        items,
        train_pct=splits.get("train", 0),
        test_pct=splits.get("test", 0),
        valid_pct=splits.get("valid", 0),
    )


def export_detection(
    *,
    source_index: Dict[str, str],
    annotations: Dict[str, list],
    out_dir: str,
    folder_name: str,
    splits: Dict[str, float],
    seed: Optional[int] = None,
    image_format: str = "png",
    selected_keys: Optional[set] = None,
    rotations: Optional[Dict[str, int]] = None,
    aug_config: Optional[dict] = None,
    progress: ProgressFn = None,
) -> dict:
    """Export a PaddleOCR text-detection dataset.

    Layout: ``<folder>/img/<split>/*.png`` + ``labels_<split>.txt`` + ``labels_all.txt``.
    """
    pipeline, aug_targets = _build_pipeline(aug_config)
    keys = [
        k
        for k, anns in annotations.items()
        if anns
        and k in source_index
        and (selected_keys is None or k in selected_keys)
        and any(not is_mask_item(a) and is_valid_box(a.get("points", [])) for a in anns)
    ]
    if not keys:
        raise ExportValidationError("No annotated images to export for detection.")

    split_result = _split(keys, splits, seed)
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
            img = imread_unicode(source_index[key])
            if img is None:
                continue
            if rotations and rotations.get(key):
                img = _apply_rotation(img, rotations[key])
            anns = annotations[key]
            masks = [a for a in anns if is_mask_item(a)]
            normal = [a for a in anns if not is_mask_item(a) and is_valid_box(a.get("points", []))]
            if not normal:
                continue
            if masks:
                img = _apply_masks(img, masks)

            fn = f"{_stem(key)}.{image_format}"
            if not imwrite_unicode(os.path.join(sdir, fn), img, image_format=image_format):
                continue
            rel = f"img/{split_name}/{fn}"
            label = sanitize_annotations(
                [
                    {
                        "transcription": (a.get("transcription", "").strip() or PLACEHOLDER_TEXT),
                        "points": [[int(round(x)), int(round(y))] for x, y in a["points"]],
                        "difficult": bool(a.get("difficult", False)),
                    }
                    for a in normal
                ]
            )
            all_labels[split_name].append((rel, label))

            if pipeline and split_name in aug_targets:
                bboxes = [a["points"] for a in normal]
                for aug_img, aug_bboxes, aug_name in pipeline.apply(img, bboxes):
                    if aug_img is None or not aug_bboxes:
                        continue
                    aug_fn = f"{_stem(key)}_{sanitize_filename(aug_name)}.{image_format}"
                    if not imwrite_unicode(
                        os.path.join(sdir, aug_fn), aug_img, image_format=image_format
                    ):
                        continue
                    aug_label = sanitize_annotations(
                        [
                            {
                                "transcription": (
                                    a.get("transcription", "").strip() or PLACEHOLDER_TEXT
                                ),
                                "points": [[int(round(x)), int(round(y))] for x, y in bb],
                                "difficult": bool(a.get("difficult", False)),
                            }
                            for bb, a in zip(aug_bboxes, normal)
                        ]
                    )
                    all_labels[split_name].append((f"img/{split_name}/{aug_fn}", aug_label))

            if progress:
                progress(done, total)

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


def export_recognition(
    *,
    source_index: Dict[str, str],
    annotations: Dict[str, list],
    out_dir: str,
    folder_name: str,
    splits: Dict[str, float],
    seed: Optional[int] = None,
    image_format: str = "png",
    crop_method: str = "bbox",
    selected_keys: Optional[set] = None,
    rotations: Optional[Dict[str, int]] = None,
    aug_config: Optional[dict] = None,
    auto_orient: bool = False,
    progress: ProgressFn = None,
) -> dict:
    """Export a PaddleOCR text-recognition dataset (cropped lines + label files).

    Layout: ``<folder>/images/<split>/*.png`` + ``<split>.txt`` (``relpath\\ttext``).
    ``auto_orient`` rotates each crop upright (ML PP-LCNet classifier if its model
    is available, else a heuristic).
    """
    pipeline, aug_targets = _build_pipeline(aug_config)

    classifier = None
    if auto_orient:
        try:
            from modules.core.ocr.orientation import create_orientation_classifier

            classifier = create_orientation_classifier()
        except Exception:  # noqa: BLE001 - heuristic fallback if model/paddle missing
            classifier = None
    # (key, idx, points, text) for every non-mask, valid box
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
            text = a.get("transcription", "").strip() or PLACEHOLDER_TEXT
            crops.append((key, idx, pts, text))

    if not crops:
        raise ExportValidationError("No valid annotations to export for recognition.")

    split_result = _split(crops, splits, seed)
    rec_dir = os.path.join(out_dir, folder_name)
    img_base = os.path.join(rec_dir, "images")
    all_lines: Dict[str, list] = {s: [] for s in split_result}

    img_cache: Dict[str, object] = {}
    crop_fn = crop_rotated_box if crop_method == "rotated" else crop_bounding_box

    total = sum(len(v) for v in split_result.values())
    done = 0
    for split_name, items in split_result.items():
        sdir = os.path.join(img_base, split_name)
        os.makedirs(sdir, exist_ok=True)
        for key, idx, pts, text in items:
            done += 1
            if key not in img_cache:
                img = imread_unicode(source_index[key])
                if img is not None and rotations and rotations.get(key):
                    img = _apply_rotation(img, rotations[key])
                if img is not None and masks_by_key.get(key):
                    img = _apply_masks(img, masks_by_key[key])
                img_cache[key] = img
            img = img_cache[key]
            if img is None:
                continue

            crop = crop_fn(img, pts, auto_detect=auto_orient, orientation_classifier=classifier)
            if crop is None or getattr(crop, "size", 0) == 0:
                continue
            if crop.shape[0] < 3 or crop.shape[1] < 3:
                continue

            fn = f"{_stem(key)}_{idx}.{image_format}"
            if not imwrite_unicode(os.path.join(sdir, fn), crop, image_format=image_format):
                continue
            all_lines[split_name].append((f"images/{split_name}/{fn}", text))

            if pipeline and split_name in aug_targets:
                for aug_img, _bb, aug_name in pipeline.apply(crop, None):
                    if aug_img is None or aug_img.size == 0:
                        continue
                    aug_fn = f"{_stem(key)}_{idx}_{sanitize_filename(aug_name)}.{image_format}"
                    if not imwrite_unicode(
                        os.path.join(sdir, aug_fn), aug_img, image_format=image_format
                    ):
                        continue
                    all_lines[split_name].append((f"images/{split_name}/{aug_fn}", text))

            if progress:
                progress(done, total)

    os.makedirs(rec_dir, exist_ok=True)
    for split_name, lines in all_lines.items():
        with open(os.path.join(rec_dir, f"{split_name}.txt"), "w", encoding="utf-8") as f:
            for rel, text in lines:
                f.write(f"{rel}\t{text}\n")

    stats = {s: len(v) for s, v in all_lines.items()}
    return {
        "kind": "recognition",
        "folder": folder_name,
        "splits": stats,
        "total": sum(stats.values()),
    }
