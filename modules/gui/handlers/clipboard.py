# modules/gui/handlers/clipboard.py
"""
Clipboard handler for copy/paste/cut of annotations.
"""

import logging
from copy import deepcopy

from PyQt5 import QtWidgets

from modules.gui.box_item import BoxItem
from modules.gui.polygon_item import PolygonItem
from modules.gui.mask_item import MaskQuadItem, MaskPolygonItem
from modules.core.undo_redo import UndoRedoManager, AddAnnotationCommand

logger = logging.getLogger("TextDetGUI")

_ANNOTATION_TYPES = (BoxItem, PolygonItem, MaskQuadItem, MaskPolygonItem)


class ClipboardHandler:
    """
    Handle copy / paste / cut of annotations.

    Data access goes through self.state (AppState).
    """

    def __init__(self, state, services, main_window):
        """
        Args:
            state:       AppState instance.
            services:    Services container.
            main_window: MainWindow reference (Qt widget access only).
        """
        self.state       = state
        self.services    = services
        self.main_window = main_window
        self.clipboard:  list = []

    # ------------------------------------------------------------------ public

    def copy_selected(self) -> None:
        """Copy selected annotations to the internal clipboard."""
        selected = self.main_window.scene.selectedItems()
        if not selected:
            self.main_window.statusBar().showMessage("No annotations selected to copy", 2000)
            return

        self.clipboard.clear()
        for item in selected:
            if isinstance(item, _ANNOTATION_TYPES):
                self.clipboard.append(deepcopy(item.to_dict()))

        if self.clipboard:
            self.main_window.statusBar().showMessage(
                f"Copied {len(self.clipboard)} annotation(s)", 2000
            )
            logger.info(f"Copied {len(self.clipboard)} annotations to clipboard")
        else:
            self.main_window.statusBar().showMessage("No valid annotations to copy", 2000)

    def paste(self) -> None:
        """Paste annotations from clipboard with a small position offset."""
        if not self.clipboard:
            self.main_window.statusBar().showMessage("Clipboard is empty", 2000)
            return

        if not self.state.img_key:
            self.main_window.statusBar().showMessage("No image selected", 2000)
            return

        offset       = 20
        pasted_count = 0
        undo_manager = UndoRedoManager.instance()

        for ann in self.clipboard:
            new_ann = deepcopy(ann)
            if "points" in new_ann:
                new_ann["points"] = [
                    [p[0] + offset, p[1] + offset] for p in new_ann["points"]
                ]

            cmd = AddAnnotationCommand(self.main_window, self.state.img_key, new_ann)
            if undo_manager.execute(cmd):
                pasted_count += 1

        if pasted_count:
            self.main_window.annotation_handler.load_annotation(self.state.img_key)
            if self.state.recog_mode:
                self.main_window.table_handler.populate_table()
            self.main_window.statusBar().showMessage(
                f"Pasted {pasted_count} annotation(s)", 2000
            )
            logger.info(f"Pasted {pasted_count} annotations")
        else:
            self.main_window.statusBar().showMessage("Failed to paste annotations", 2000)

    def cut_selected(self) -> None:
        """Cut selected annotations (copy then delete)."""
        selected = self.main_window.scene.selectedItems()
        if not selected:
            self.main_window.statusBar().showMessage("No annotations selected to cut", 2000)
            return

        self.copy_selected()
        if self.clipboard:
            self.main_window.annotation_handler.delete_selected()
            self.main_window.statusBar().showMessage(
                f"Cut {len(self.clipboard)} annotation(s)", 2000
            )

    def has_clipboard_content(self) -> bool:
        return bool(self.clipboard)

    def clear_clipboard(self) -> None:
        self.clipboard.clear()
        logger.debug("Clipboard cleared")
