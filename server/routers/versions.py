"""Workspace version control (list / create / switch / delete)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from server import schemas
from server.deps import get_workspace_context, get_workspace_manager

router = APIRouter(prefix="/api/workspaces/{workspace_id}/versions", tags=["versions"])


@router.get("", response_model=List[schemas.VersionInfo])
def list_versions(workspace_id: str) -> List[schemas.VersionInfo]:
    wm = get_workspace_manager()
    if not wm.storage.workspace_exists(workspace_id):
        raise HTTPException(404, "Workspace not found")
    return [schemas.VersionInfo(**v) for v in wm.get_version_list(workspace_id)]


@router.post("", response_model=schemas.MessageResponse, status_code=201)
def create_version(workspace_id: str, req: schemas.CreateVersionRequest) -> schemas.MessageResponse:
    try:
        ctx = get_workspace_context(workspace_id)
    except KeyError:
        raise HTTPException(404, "Workspace not found")

    base = req.base or ctx.current_version
    ok, message = ctx.wm.create_version(workspace_id, req.name, base, req.description)
    if not ok:
        raise HTTPException(400, message)
    # Switch to the freshly created version so the editor lands on it.
    ctx.wm.switch_version(workspace_id, req.name)
    return schemas.MessageResponse(message=message)


@router.post("/{name}/switch", response_model=schemas.MessageResponse)
def switch_version(workspace_id: str, name: str) -> schemas.MessageResponse:
    wm = get_workspace_manager()
    if not wm.switch_version(workspace_id, name):
        raise HTTPException(400, f"Cannot switch to version '{name}'")
    return schemas.MessageResponse(message=f"Switched to {name}")


@router.delete("/{name}", response_model=schemas.MessageResponse)
def delete_version(workspace_id: str, name: str) -> schemas.MessageResponse:
    wm = get_workspace_manager()
    ok, message = wm.delete_version(workspace_id, name)
    if not ok:
        raise HTTPException(400, message)
    return schemas.MessageResponse(message=message)
