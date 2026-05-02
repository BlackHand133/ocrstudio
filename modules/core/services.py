"""
Services container.

A lightweight dataclass that bundles the three backend service objects so
handlers can receive them via dependency injection instead of fishing them
out of MainWindow.

Usage:
    from modules.core.services import Services
    from modules.core.ocr import TextDetector
    from modules.core.workspace.manager import WorkspaceManager
    from modules.core.undo_redo import UndoRedoManager

    services = Services(
        workspace_manager=WorkspaceManager(root_dir),
        detector=TextDetector(),
        undo_manager=UndoRedoManager.instance(),
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.core.ocr.detector import TextDetector
    from modules.core.workspace.manager import WorkspaceManager
    from modules.core.undo_redo import UndoRedoManager


@dataclass
class Services:
    """
    Container for the three application-level backend services.

    Attributes:
        workspace_manager: Manages workspace/version persistence.
        detector: PaddleOCR text-detection/recognition engine.
        undo_manager: Command-stack undo/redo manager.
    """

    workspace_manager: "WorkspaceManager"
    detector: "TextDetector"
    undo_manager: "UndoRedoManager"
