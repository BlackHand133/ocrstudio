"""Workspace CRUD endpoints."""

from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, HTTPException

from modules.utils import sanitize_filename
from server import schemas
from server.deps import get_workspace_context, get_workspace_manager
from server.services import image_service

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


def _unique_id(wm, name: str) -> str:
    base = sanitize_filename(name) or "workspace"
    candidate = base
    i = 2
    while wm.storage.workspace_exists(candidate):
        candidate = f"{base}_{i}"
        i += 1
    return candidate


@router.get("", response_model=List[schemas.WorkspaceSummary])
def list_workspaces() -> List[schemas.WorkspaceSummary]:
    wm = get_workspace_manager()
    return [
        schemas.WorkspaceSummary(
            id=w["id"],
            name=w.get("name", w["id"]),
            description=w.get("description", ""),
            source_folder=w.get("source_folder", ""),
            created_at=w.get("created_at", ""),
            modified_at=w.get("modified_at", ""),
            current_version=w.get("current_version", "v1"),
            available_versions=w.get("available_versions", []),
        )
        for w in wm.get_workspace_list()
    ]


@router.post("", response_model=schemas.CreateWorkspaceResponse, status_code=201)
def create_workspace(req: schemas.CreateWorkspaceRequest) -> schemas.CreateWorkspaceResponse:
    wm = get_workspace_manager()
    ws_id = _unique_id(wm, req.name)

    if req.source_folder:
        if not os.path.isdir(req.source_folder):
            raise HTTPException(400, f"source_folder not found: {req.source_folder}")
        source_folder = req.source_folder
    else:
        # Portable: images live inside the workspace dir.
        source_folder = os.path.join(wm.storage.get_workspace_path(ws_id), "images")

    if not wm.create_workspace(ws_id, req.name, source_folder, req.description):
        raise HTTPException(500, "Failed to create workspace")

    os.makedirs(source_folder, exist_ok=True)
    return schemas.CreateWorkspaceResponse(id=ws_id)


@router.get("/{workspace_id}", response_model=schemas.WorkspaceDetail)
def get_workspace(workspace_id: str) -> schemas.WorkspaceDetail:
    try:
        ctx = get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")

    images = image_service.scan_images(ctx.source_folder)
    version_data = ctx.wm.load_version(workspace_id, ctx.current_version) or {}
    annotations = version_data.get("annotations", {})
    annotated = sum(1 for v in annotations.values() if v)

    ws = ctx.data["workspace"]
    return schemas.WorkspaceDetail(
        id=workspace_id,
        name=ws.get("name", workspace_id),
        description=ws.get("description", ""),
        source_folder=ctx.source_folder,
        created_at=ws.get("created_at", ""),
        modified_at=ws.get("modified_at", ""),
        current_version=ctx.current_version,
        available_versions=ctx.data.get("versions", {}).get("available", []),
        image_count=len(images),
        annotated_count=annotated,
    )


@router.delete("/{workspace_id}", response_model=schemas.MessageResponse)
def delete_workspace(workspace_id: str) -> schemas.MessageResponse:
    wm = get_workspace_manager()
    if not wm.delete_workspace(workspace_id):
        raise HTTPException(404, "Workspace not found")
    return schemas.MessageResponse(message="deleted")
