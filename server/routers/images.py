"""Image listing, file serving, and upload."""

from __future__ import annotations

import os
import shutil
from typing import List

import cv2
from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from modules.utils import imread_unicode, sanitize_filename
from server import schemas
from server.deps import get_workspace_context
from server.services import image_service

router = APIRouter(prefix="/api/workspaces/{workspace_id}/images", tags=["images"])

# Stored angle = total clockwise rotation applied to the original image.
_ROTATE_CODES = {
    90: cv2.ROTATE_90_CLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def _ctx(workspace_id: str):
    try:
        return get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")


@router.get("", response_model=List[schemas.ImageInfo])
def list_images(workspace_id: str) -> List[schemas.ImageInfo]:
    ctx = _ctx(workspace_id)
    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    annotations = version_data.get("annotations", {})
    out: List[schemas.ImageInfo] = []
    for key, _path in image_service.scan_images(ctx.source_folder):
        anns = annotations.get(key) or []
        out.append(
            schemas.ImageInfo(key=key, has_annotations=bool(anns), annotation_count=len(anns))
        )
    return out


@router.get("/missing")
def missing_images(workspace_id: str) -> dict:
    """Annotated image keys that have no matching file in the source folder."""
    ctx = _ctx(workspace_id)
    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    annotations = version_data.get("annotations", {})
    present = set(image_service.build_index(ctx.source_folder).keys())
    annotated = [k for k, a in annotations.items() if a]
    missing = sorted(k for k in annotated if k not in present)
    return {
        "missing": missing,
        "missing_count": len(missing),
        "annotated": len(annotated),
        "present": len(present),
    }


@router.get("/{key}/file")
def get_image_file(workspace_id: str, key: str):
    ctx = _ctx(workspace_id)
    path = image_service.build_index(ctx.source_folder).get(key)
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Image not found")

    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    angle = int(version_data.get("transforms", {}).get(key, 0) or 0) % 360
    if angle in _ROTATE_CODES:
        img = imread_unicode(path)
        if img is not None:
            rotated = cv2.rotate(img, _ROTATE_CODES[angle])
            ok, buf = cv2.imencode(".png", rotated)
            if ok:
                return Response(content=buf.tobytes(), media_type="image/png")
    return FileResponse(path)


@router.get("/{key}/thumb")
def get_thumbnail(workspace_id: str, key: str, size: int = 96):
    ctx = _ctx(workspace_id)
    path = image_service.build_index(ctx.source_folder).get(key)
    if not path or not os.path.exists(path):
        raise HTTPException(404, "Image not found")
    img = imread_unicode(path)
    if img is None:
        raise HTTPException(404, "Image not readable")
    size = max(16, min(int(size), 256))
    h, w = img.shape[:2]
    scale = size / max(h, w, 1)
    if scale < 1:
        img = cv2.resize(
            img, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA
        )
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if not ok:
        raise HTTPException(500, "Failed to encode thumbnail")
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.post("/upload", response_model=schemas.MessageResponse)
async def upload_images(
    workspace_id: str, files: List[UploadFile] = File(...)
) -> schemas.MessageResponse:
    ctx = _ctx(workspace_id)
    folder = ctx.source_folder
    os.makedirs(folder, exist_ok=True)

    saved = 0
    for f in files:
        raw = os.path.basename(f.filename or "")
        name = sanitize_filename(raw)
        if not name:
            continue
        dest = os.path.join(folder, name)
        # Stream to disk in chunks instead of loading the whole file into memory.
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out, length=1024 * 1024)
        saved += 1
    return schemas.MessageResponse(message=f"uploaded {saved} files")
