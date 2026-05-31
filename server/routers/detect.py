"""OCR auto-detection — single image (sync) and batch (background job).

Detection runs on the image in its *displayed* orientation (the stored
rotation is applied first) so the returned boxes line up with what the user
sees and with the saved annotations. The detector is loaded lazily and run off
the event loop; missing model weights surface as 503 / job error.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading

import cv2
from fastapi import APIRouter, HTTPException

from modules.export.utils import crop_bounding_box, crop_rotated_box
from modules.utils import imread_unicode, imwrite_unicode
from server import schemas
from server.deps import get_detector, get_workspace_context, get_workspace_manager
from server.jobs import jobs
from server.services import image_service

router = APIRouter(prefix="/api/workspaces/{workspace_id}/detect", tags=["detect"])

_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def _shape_for(points: list) -> str:
    return "Quad" if len(points) == 4 else "Polygon"


def _results_to_dicts(results) -> list:
    """Map raw detector output to storage-format annotation dicts."""
    out = []
    for r in results or []:
        pts = r.get("points")
        if not isinstance(pts, list) or len(pts) < 4:
            continue
        out.append(
            {
                "points": [[float(x), float(y)] for x, y in pts],
                "transcription": r.get("transcription", ""),
                "difficult": False,
                "shape": _shape_for(pts),
                "score": float(r["score"]) if r.get("score") is not None else None,
            }
        )
    return out


def _detect_with_rotation(detector, path: str, angle: int) -> list:
    """Detect on the image rotated by *angle* (CW) so coords match the editor."""
    code = _ROTATE_CODES.get(int(angle) % 360)
    if code is None:
        return detector.detect(path)
    img = imread_unicode(path)
    if img is None:
        return []
    rotated = cv2.rotate(img, code)
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        if not imwrite_unicode(tmp, rotated, image_format="png"):
            return []
        return detector.detect(tmp)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _ocr_box(detector, path: str, angle: int, points: list, crop_method: str) -> tuple:
    """Recognize text inside a single box: rotate to the display frame, crop the
    region, then run the detector on just that crop. Returns (text, score)."""
    img = imread_unicode(path)
    if img is None:
        return "", None
    code = _ROTATE_CODES.get(int(angle) % 360)
    if code is not None:
        img = cv2.rotate(img, code)
    crop_fn = crop_rotated_box if crop_method == "rotated" else crop_bounding_box
    # auto_detect=False: the box is already in display orientation (stored rotation
    # applied above); don't let the crop helper re-rotate it heuristically.
    crop = crop_fn(img, points, auto_detect=False)
    if crop is None or getattr(crop, "size", 0) == 0 or crop.shape[0] < 2 or crop.shape[1] < 2:
        return "", None
    # The detector expects text as a region *inside* a larger image, so a tight
    # crop usually yields zero detections. Upscale small crops and add a replicate
    # margin so detection (then recognition) can find the line.
    h, w = crop.shape[:2]
    longest = max(h, w)
    if longest < 320:
        s = 320.0 / longest
        crop = cv2.resize(
            crop, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_CUBIC
        )
        h, w = crop.shape[:2]
    pad = max(24, int(0.4 * max(h, w)))
    crop = cv2.copyMakeBorder(crop, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        if not imwrite_unicode(tmp, crop, image_format="png"):
            return "", None
        results = detector.detect(tmp)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    # Join every recognized segment in reading order (top→bottom, left→right).
    parts = []
    best = None
    for r in results or []:
        text = (r.get("transcription") or "").strip()
        if not text:
            continue
        pts = r.get("points") or [[0, 0]]
        ys = [p[1] for p in pts]
        xs = [p[0] for p in pts]
        parts.append((min(ys), min(xs), text))
        score = r.get("score")
        if score is not None:
            best = float(score) if best is None else max(best, float(score))
    parts.sort(key=lambda z: (round(z[0] / 10.0), z[1]))
    return " ".join(p[2] for p in parts), best


@router.post("/{key}", response_model=schemas.DetectResponse)
async def detect_image(workspace_id: str, key: str) -> schemas.DetectResponse:
    try:
        ctx = get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")

    path = image_service.build_index(ctx.source_folder).get(key)
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Image not found")

    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    angle = int(version_data.get("transforms", {}).get(key, 0) or 0)

    try:
        detector = get_detector()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"OCR engine unavailable: {exc}")

    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, _detect_with_rotation, detector, path, angle)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Detection failed: {exc}")

    return schemas.DetectResponse(key=key, annotations=_results_to_dicts(results))


@router.post("/{key}/box", response_model=schemas.BoxDetectResponse)
async def detect_box(
    workspace_id: str, key: str, req: schemas.BoxDetectRequest
) -> schemas.BoxDetectResponse:
    """Re-run OCR on a single existing box (e.g. after switching models)."""
    try:
        ctx = get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")
    path = image_service.build_index(ctx.source_folder).get(key)
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Image not found")
    if not req.points or len(req.points) < 3:
        raise HTTPException(400, "Box needs at least 3 points")

    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    angle = int(version_data.get("transforms", {}).get(key, 0) or 0)

    try:
        detector = get_detector()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"OCR engine unavailable: {exc}")

    loop = asyncio.get_event_loop()
    try:
        text, score = await loop.run_in_executor(
            None, _ocr_box, detector, path, angle, req.points, req.crop_method
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Detection failed: {exc}")

    return schemas.BoxDetectResponse(transcription=text, score=score)


@router.post("", response_model=schemas.BatchDetectResponse)
def batch_detect(workspace_id: str, req: schemas.BatchDetectRequest) -> schemas.BatchDetectResponse:
    try:
        ctx = get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")

    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    annotations = version_data.get("annotations", {})
    index = image_service.build_index(ctx.source_folder)
    all_keys = list(index.keys())

    if req.scope == "selected":
        targets = [k for k in (req.keys or []) if k in index]
    elif req.scope == "all":
        targets = all_keys
    else:  # "empty"
        targets = [k for k in all_keys if not annotations.get(k)]

    if not req.overwrite:
        targets = [k for k in targets if not annotations.get(k)]

    job_id = jobs.create("detect", total=len(targets))
    if not targets:
        jobs.update(job_id, status="done", result={"processed": 0, "failed": 0})
        return schemas.BatchDetectResponse(job_id=job_id, total=0)

    threading.Thread(
        target=_run_batch,
        args=(job_id, workspace_id, ctx.current_version, targets, dict(index)),
        daemon=True,
    ).start()
    return schemas.BatchDetectResponse(job_id=job_id, total=len(targets))


def _run_batch(job_id: str, workspace_id: str, version: str, targets: list, index: dict) -> None:
    try:
        detector = get_detector()
    except RuntimeError as exc:
        jobs.update(job_id, status="error", error=f"OCR engine unavailable: {exc}")
        return

    wm = get_workspace_manager()
    vd = wm.load_version(workspace_id, version) or {}
    anns = vd.setdefault("annotations", {})
    transforms = vd.get("transforms", {})

    done = failed = 0
    for key in targets:
        try:
            angle = int(transforms.get(key, 0) or 0)
            anns[key] = _results_to_dicts(_detect_with_rotation(detector, index[key], angle))
        except Exception:  # noqa: BLE001
            failed += 1
        done += 1
        jobs.update(job_id, done=done, message=key)

    vd["metadata"] = {
        "total_images": len(index),
        "annotated_images": sum(1 for v in anns.values() if v),
        "total_annotations": sum(len(v) for v in anns.values()),
    }
    wm.save_version(workspace_id, version, vd)
    jobs.update(job_id, status="done", result={"processed": done, "failed": failed})
