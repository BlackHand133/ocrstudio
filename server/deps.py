"""Shared dependencies / singletons for the API.

Everything here is process-wide and lazily constructed so the server starts
fast (PaddleOCR is heavy and is only loaded on the first detect call).
"""

from __future__ import annotations

import logging
from pathlib import Path
import threading

from server.services.image_service import resolve_source_folder

# Repo root = parent of the ``server`` package. ``modules/`` and ``workspaces/``
# live here. Stays correct both locally and inside the container (/app).
ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger("ocrstudio.server")

_workspace_manager = None
_detector = None
_detector_lock = threading.Lock()


def get_root() -> Path:
    return ROOT


def get_workspace_manager():
    """WorkspaceManager singleton rooted at the repo root."""
    global _workspace_manager
    if _workspace_manager is None:
        from modules.core.workspace.manager import WorkspaceManager

        _workspace_manager = WorkspaceManager(str(ROOT))
    return _workspace_manager


def get_config():
    """ConfigManager singleton (profiles cpu/gpu)."""
    from modules.config import ConfigManager

    return ConfigManager.instance(str(ROOT))


def get_detector():
    """Lazily build the PaddleOCR detector.

    Heavy + may fail if model weights are absent. Raises ``RuntimeError`` so the
    caller can return HTTP 503 while the rest of the app keeps working.
    """
    global _detector
    if _detector is not None:
        return _detector
    with _detector_lock:
        if _detector is None:
            try:
                import os

                from modules.core.ocr.detector import TextDetector

                # GPU image sets OCR_PROFILE=gpu so the detector loads on CUDA.
                profile = os.environ.get("OCR_PROFILE")
                if profile:
                    try:
                        from modules.config import ConfigManager

                        ConfigManager.instance(str(ROOT)).set_current_profile(profile)
                    except Exception:  # noqa: BLE001 - fall back to default profile
                        logger.warning("Could not set OCR profile %r; using default", profile)

                _detector = TextDetector()
            except Exception as exc:  # noqa: BLE001 - surface any init failure
                logger.exception("Failed to initialise OCR detector")
                raise RuntimeError(str(exc)) from exc
    return _detector


def reset_detector() -> None:
    """Drop the cached detector so the next detect reloads with fresh config."""
    global _detector
    with _detector_lock:
        _detector = None


class WorkspaceContext:
    """Resolved view of a workspace used by the routers."""

    def __init__(self, wm, workspace_id: str, data: dict) -> None:
        self.wm = wm
        self.workspace_id = workspace_id
        self.data = data
        self.workspace_path = wm.storage.get_workspace_path(workspace_id)
        self.source_folder = resolve_source_folder(
            self.workspace_path, data.get("source", {}).get("folder", "")
        )
        self.current_version: str = data.get("versions", {}).get("current", "v1")


def get_workspace_context(workspace_id: str) -> WorkspaceContext:
    """Load a workspace or raise ``KeyError`` if it does not exist."""
    wm = get_workspace_manager()
    data = wm.load_workspace(workspace_id)
    if not data:
        raise KeyError(workspace_id)
    return WorkspaceContext(wm, workspace_id, data)
