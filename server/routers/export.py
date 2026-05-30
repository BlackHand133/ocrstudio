"""Dataset export endpoints (PaddleOCR detection / recognition).

Export runs as a background job (reuses the in-process job registry) so large
datasets don't block the request or hit timeouts; the client polls
``GET /api/jobs/{id}`` for progress and the final result.
"""

from __future__ import annotations

from datetime import datetime
import os
import shutil
import tempfile
import threading

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from modules.export.utils import ExportValidationError
from server import schemas
from server.deps import get_workspace_context, get_workspace_manager
from server.jobs import jobs
from server.services import export_service, image_service

router = APIRouter(prefix="/api/workspaces/{workspace_id}/export", tags=["export"])


def _out_root(kind: str) -> str:
    root = get_workspace_manager().root_dir
    sub = "output_det" if kind == "detection" else "output_rec"
    path = os.path.join(root, sub)
    os.makedirs(path, exist_ok=True)
    return path


def _safe_folder(folder: str) -> str:
    if "/" in folder or "\\" in folder or ".." in folder:
        raise HTTPException(400, "Invalid folder name")
    return folder


@router.post("", response_model=schemas.ExportJobResponse)
def run_export(workspace_id: str, req: schemas.ExportRequest) -> schemas.ExportJobResponse:
    if req.kind not in ("detection", "recognition"):
        raise HTTPException(400, "kind must be 'detection' or 'recognition'")
    allowed_formats = {"paddleocr", "icdar", "coco", "yolo", "csv", "jsonl"}
    if req.dataset_format not in allowed_formats:
        raise HTTPException(400, f"dataset_format must be one of {sorted(allowed_formats)}")
    if req.dataset_format in {"icdar", "coco", "yolo"} and req.kind != "detection":
        raise HTTPException(400, f"{req.dataset_format} format supports detection only")
    if not 0 < (req.train + req.valid + req.test) <= 100:
        raise HTTPException(400, "Split percentages must sum to between 1 and 100")
    try:
        ctx = get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")

    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    annotations = version_data.get("annotations", {})
    rotations = version_data.get("transforms", {})
    source_index = image_service.build_index(ctx.source_folder)
    selected = set(req.selected_keys) if req.selected_keys is not None else None

    # Fast emptiness check so the user gets immediate feedback instead of a job
    # that fails a moment later.
    candidates = [
        k
        for k, anns in annotations.items()
        if anns and k in source_index and (selected is None or k in selected)
    ]
    if not candidates:
        raise HTTPException(400, "No annotated images to export.")

    out_root = _out_root(req.kind)
    folder = (
        f"{workspace_id}_{ctx.current_version}_{req.dataset_format}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    splits = {"train": req.train, "test": req.test, "valid": req.valid}

    aug_config = None
    if req.augment and req.augmentations:
        aug_config = {
            "mode": req.aug_mode,
            "augmentations": [a.model_dump() for a in req.augmentations],
            "target_splits": req.aug_targets or ["train"],
        }

    job_id = jobs.create("export")

    def work() -> None:
        def progress(done: int, total: int) -> None:
            jobs.update(job_id, done=done, total=total)

        fmt = req.dataset_format
        common = dict(
            source_index=source_index,
            annotations=annotations,
            out_dir=out_root,
            folder_name=folder,
            splits=splits,
            seed=req.seed,
            image_format=req.image_format,
            selected_keys=selected,
            rotations=rotations,
            progress=progress,
        )
        try:
            if req.kind == "detection":
                if fmt == "paddleocr":
                    result = export_service.export_detection(aug_config=aug_config, **common)
                elif fmt == "icdar":
                    result = export_service.export_icdar(**common)
                elif fmt == "coco":
                    result = export_service.export_coco(**common)
                elif fmt == "yolo":
                    result = export_service.export_yolo(**common)
                else:  # csv | jsonl
                    result = export_service.export_manifest_detection(fmt=fmt, **common)
            else:  # recognition
                if fmt == "paddleocr":
                    result = export_service.export_recognition(
                        crop_method=req.crop_method,
                        aug_config=aug_config,
                        auto_orient=req.auto_orient,
                        **common,
                    )
                else:  # csv | jsonl
                    result = export_service.export_manifest_recognition(
                        fmt=fmt,
                        crop_method=req.crop_method,
                        auto_orient=req.auto_orient,
                        **common,
                    )
            jobs.update(
                job_id,
                status="done",
                result={
                    **result,
                    "download_url": (
                        f"/api/workspaces/{workspace_id}/export/"
                        f"{result['folder']}/download?kind={req.kind}"
                    ),
                },
            )
        except ExportValidationError as exc:
            jobs.update(job_id, status="error", error=str(exc))
        except Exception as exc:  # noqa: BLE001
            jobs.update(job_id, status="error", error=f"Export failed: {exc}")

    threading.Thread(target=work, daemon=True).start()
    return schemas.ExportJobResponse(job_id=job_id)


@router.get("/{folder}/download")
def download_export(workspace_id: str, folder: str, kind: str = Query("detection")):
    folder = _safe_folder(folder)
    dataset_dir = os.path.join(_out_root(kind), folder)
    if not os.path.isdir(dataset_dir):
        raise HTTPException(404, "Export not found")

    tmp = tempfile.mkdtemp()
    zip_path = shutil.make_archive(os.path.join(tmp, folder), "zip", dataset_dir)
    return FileResponse(
        zip_path,
        filename=f"{folder}.zip",
        media_type="application/zip",
        background=BackgroundTask(shutil.rmtree, tmp, True),
    )
