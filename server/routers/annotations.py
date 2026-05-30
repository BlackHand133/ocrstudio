"""Per-image annotation read/write.

Saves straight back into the workspace version JSON via WorkspaceManager, in
the exact format the desktop app uses, and refreshes ``metadata`` counts.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from modules.utils import sanitize_annotations
from server import schemas
from server.deps import get_workspace_context
from server.services import image_service

router = APIRouter(prefix="/api/workspaces/{workspace_id}/annotations", tags=["annotations"])


def _ctx_and_version(workspace_id: str):
    try:
        ctx = get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")
    version_data = ctx.wm.load_version(workspace_id, ctx.current_version)
    if version_data is None:
        raise HTTPException(404, "Version not found")
    return ctx, version_data


@router.get("/{key}", response_model=schemas.AnnotationsResponse)
def get_annotations(workspace_id: str, key: str) -> schemas.AnnotationsResponse:
    ctx, vd = _ctx_and_version(workspace_id)
    anns = vd.get("annotations", {}).get(key, [])
    rotation = int(vd.get("transforms", {}).get(key, 0) or 0)
    return schemas.AnnotationsResponse(key=key, rotation=rotation, annotations=anns)


@router.put("/{key}", response_model=schemas.AnnotationsResponse)
def save_annotations(
    workspace_id: str, key: str, req: schemas.SaveAnnotationsRequest
) -> schemas.AnnotationsResponse:
    ctx, vd = _ctx_and_version(workspace_id)

    anns = [a.model_dump() for a in req.annotations]
    vd.setdefault("annotations", {})[key] = sanitize_annotations(anns)

    transforms = vd.setdefault("transforms", {})
    if req.rotation:
        transforms[key] = req.rotation
    else:
        transforms.pop(key, None)

    annotations = vd["annotations"]
    total_images = len(image_service.scan_images(ctx.source_folder))
    vd["metadata"] = {
        "total_images": total_images,
        "annotated_images": sum(1 for v in annotations.values() if v),
        "total_annotations": sum(len(v) for v in annotations.values()),
    }

    if not ctx.wm.save_version(workspace_id, ctx.current_version, vd):
        raise HTTPException(500, "Failed to save annotations")

    rotation = int(transforms.get(key, 0) or 0)
    return schemas.AnnotationsResponse(key=key, rotation=rotation, annotations=annotations[key])
