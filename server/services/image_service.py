"""Image catalogue helpers — scan a source folder for images.

The image list is *not* persisted (same as the desktop app): it is derived by
walking the workspace's source folder and filtering by ``IMAGE_EXTENSIONS``.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from modules.constants import IMAGE_EXTENSIONS

_EXTS = {e.lower() for e in IMAGE_EXTENSIONS}


def resolve_source_folder(workspace_path: str, stored_folder: str) -> str:
    """Pick the folder to scan for a workspace.

    Prefers the workspace-internal ``images/`` dir (created for uploaded
    workspaces) so the workspace is portable across machines/containers; falls
    back to the stored (external or mounted) source folder otherwise.
    """
    internal = os.path.join(workspace_path, "images")
    if os.path.isdir(internal):
        return internal
    return stored_folder or ""


def scan_images(folder: str) -> List[Tuple[str, str]]:
    """Return a sorted list of ``(key, full_path)`` for images under *folder*.

    ``key`` is the filename (the annotation-dict key used everywhere else).
    """
    if not folder or not os.path.isdir(folder):
        return []
    items: List[Tuple[str, str]] = []
    for root_dir, _dirs, files in os.walk(folder):
        for fn in files:
            if os.path.splitext(fn.lower())[1] in _EXTS:
                items.append((fn, os.path.join(root_dir, fn)))
    items.sort(key=lambda pair: pair[0])
    return items


def build_index(folder: str) -> Dict[str, str]:
    """Map image key (filename) -> absolute path."""
    return {key: path for key, path in scan_images(folder)}
