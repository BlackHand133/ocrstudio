"""
Application State Model.

Single source of truth for all mutable business data. This class is intentionally
free of any heavy business logic — it holds data and emits Qt signals when that
data changes so UI components can react.

Design rules:
  - No Qt *widgets* here (QGraphicsItem, QListWidget, etc.) — only plain data.
  - Use the setter helpers (set_current_image, set_annotations, …) when a change
    should notify observers via a signal.
  - Direct attribute mutation is fine for internal batch updates that will be
    followed by an explicit notify() call.
  - Handlers should import AppState and use self.state.xxx instead of
    self.main_window.xxx for all business data.

Usage:
    from modules.core.app_state import AppState

    state = AppState()
    state.current_image_changed.connect(my_slot)
    state.set_current_image("img001.jpg", "/path/to/img001.jpg")
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger("TextDetGUI")


class AppState(QObject):
    """
    Centralised mutable application state.

    Signals:
        current_image_changed(key, path): Emitted when the active image changes.
        annotations_changed(key): Emitted when annotations for *key* are updated.
        images_loaded(): Emitted when the full image list is replaced.
        mode_changed(): Emitted when any draw/recog/mask mode flag changes.
        filter_changed(): Emitted when the filter or search text changes.
    """

    # ------------------------------------------------------------------ signals
    current_image_changed = pyqtSignal(str, str)   # (key, path)
    annotations_changed   = pyqtSignal(str)         # image key
    images_loaded         = pyqtSignal()
    mode_changed          = pyqtSignal()
    filter_changed        = pyqtSignal()

    # ------------------------------------------------------------------ init
    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # --- current image context ---
        self.img_key:  Optional[str] = None
        self.img_path: Optional[str] = None

        # --- image catalogue ---
        # List of (key, full_path) tuples; key is the stable filename used
        # as the annotation dict key.
        self.image_items: List[Tuple[str, str]] = []

        # --- annotation data ---
        # key → list of annotation dicts
        # {"points": [[x,y],...], "transcription": str, "difficult": bool,
        #  "shape": str, "score": float, "mask_color": str|None}
        self.annotations: Dict[str, List] = {}

        # key → rotation angle (0 / 90 / 180 / 270)
        self.image_rotations: Dict[str, int] = {}

        # Keys that have been modified since the last explicit save
        self.modified_images: Set[str] = set()

        # --- mode flags ---
        self.draw_mode:       bool = False
        self.recog_mode:      bool = False
        self.mask_mode:       bool = False
        self.annotation_type: str  = "Quad"   # "Quad" | "Polygon"

        # --- filter / search ---
        self.current_filter: str = "all"   # "all" | "annotated" | "empty"
        self.search_text:    str = ""

    # ------------------------------------------------------------------ setters
    # Use these helpers to mutate state AND fire the corresponding signal.
    # For silent / batch updates, assign the attribute directly and call the
    # notify_* method at the end.

    def set_current_image(self, key: Optional[str], path: Optional[str]) -> None:
        """Change the active image and notify observers."""
        self.img_key  = key
        self.img_path = path
        self.current_image_changed.emit(key or "", path or "")

    def set_annotations(self, key: str, annotations: List) -> None:
        """Replace annotations for *key* and notify observers."""
        self.annotations[key] = annotations
        self.annotations_changed.emit(key)

    def set_image_items(self, items: List[Tuple[str, str]]) -> None:
        """Replace the entire image catalogue and notify observers."""
        self.image_items = items
        self.images_loaded.emit()

    def set_draw_mode(self, value: bool) -> None:
        """Enable or disable bounding-box draw mode and notify observers."""
        self.draw_mode = value
        self.mode_changed.emit()

    def set_recog_mode(self, value: bool) -> None:
        """Enable or disable text-recognition mode and notify observers."""
        self.recog_mode = value
        self.mode_changed.emit()

    def set_mask_mode(self, value: bool) -> None:
        """Enable or disable mask-paint mode and notify observers."""
        self.mask_mode = value
        self.mode_changed.emit()

    def set_annotation_type(self, value: str) -> None:
        """Set the active annotation shape type (``'Quad'`` or ``'Polygon'``) and notify observers."""
        self.annotation_type = value
        self.mode_changed.emit()

    def set_filter(self, filter_type: str, search_text: str = "") -> None:
        """Update the image-list filter and optional search text, then notify observers.

        Args:
            filter_type: One of ``'all'``, ``'annotated'``, or ``'empty'``.
            search_text: Substring to match against image filenames.
        """
        self.current_filter = filter_type
        self.search_text    = search_text
        self.filter_changed.emit()

    # ------------------------------------------------------------------ helpers

    def mark_modified(self, key: str) -> None:
        """Mark image *key* as having unsaved changes."""
        self.modified_images.add(key)

    def clear_modified(self, key: Optional[str] = None) -> None:
        """Clear the modified flag for *key*, or all keys if None."""
        if key is None:
            self.modified_images.clear()
        else:
            self.modified_images.discard(key)

    def get_image_path(self, key: str) -> Optional[str]:
        """Return the full path for *key*, or None if not found."""
        for k, path in self.image_items:
            if k == key:
                return path
        return None

    def reset(self) -> None:
        """
        Reset all state to initial values (used when switching workspaces).
        Does NOT emit signals — callers should do a full UI refresh.
        """
        self.img_key           = None
        self.img_path          = None
        self.image_items       = []
        self.annotations       = {}
        self.image_rotations   = {}
        self.modified_images   = set()
        self.draw_mode         = False
        self.recog_mode        = False
        self.mask_mode         = False
        self.annotation_type   = "Quad"
        self.current_filter    = "all"
        self.search_text       = ""

    # ------------------------------------------------------------------ repr
    def __repr__(self) -> str:
        return (
            f"<AppState img={self.img_key!r} "
            f"images={len(self.image_items)} "
            f"annotated={len([k for k, v in self.annotations.items() if v])}>"
        )
