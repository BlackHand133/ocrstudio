# modules/gui/handlers/annotation.py

import logging

from PyQt5 import QtWidgets, QtGui

from modules.gui.box_item import BoxItem
from modules.gui.polygon_item import PolygonItem
from modules.gui.mask_item import MaskQuadItem, MaskPolygonItem
from modules.utils import sanitize_annotations
from modules.core.undo_redo import (
    UndoRedoManager,
    AddAnnotationCommand,
    DeleteAnnotationCommand,
    BatchDeleteCommand,
    ClearAnnotationsCommand,
)

logger = logging.getLogger("TextDetGUI")


def is_valid_box(pts) -> bool:
    """Return True if *pts* is a list of at least 4 valid [x, y] pairs."""
    if not (isinstance(pts, list) and len(pts) >= 4):
        return False
    return all(isinstance(p, (list, tuple)) and len(p) == 2 for p in pts)


class AnnotationHandler:
    """
    Manage annotations: add, delete, load, save.

    img_key and annotations data come from self.state (AppState).
    Qt scene / box_items are accessed through self.main_window.
    """

    def __init__(self, state, services, main_window):
        self.state       = state
        self.services    = services
        self.main_window = main_window

    # ------------------------------------------------------------------ add

    def add_box_item(
        self,
        pts: list,
        text: str,
        item_type: str = None,
        mask_color=None,
        use_undo: bool = True,
    ) -> None:
        """
        Add an annotation box/polygon/mask to the scene.

        Args:
            pts:        List of [x, y] coordinate pairs.
            text:       Transcription text.
            item_type:  'Quad' | 'Polygon' | 'MaskQuad' | 'MaskPolygon'.
                        Defaults to state.annotation_type.
            mask_color: QColor-compatible value for mask items.
            use_undo:   If True, add the operation to the undo stack.
        """
        if item_type is None:
            item_type = self.state.annotation_type

        is_mask = "Mask" in item_type or text == "###"

        if is_mask:
            from PyQt5.QtGui import QColor
            color = QColor(mask_color) if mask_color else None
            if "Quad" in item_type or (len(pts) == 4 and "Polygon" not in item_type):
                box = MaskQuadItem(pts, color)
            else:
                box = MaskPolygonItem(pts, color)
        else:
            if item_type == "Quad" and len(pts) == 4:
                box = BoxItem(pts, text)
            else:
                box = PolygonItem(pts, text)

        box.setZValue(1)
        self.main_window.scene.addItem(box)
        self.main_window.box_items.append(box)

        img_key = self.state.img_key
        if use_undo and img_key:
            ann_data = {
                "points":        pts,
                "transcription": text,
                "difficult":     False,
                "shape":         item_type,
            }
            if mask_color:
                ann_data["mask_color"] = mask_color

            undo_manager = UndoRedoManager.instance()
            cmd = AddAnnotationCommand(self.main_window, img_key, ann_data)
            undo_manager.execute(cmd)
        else:
            self.save_current_annotation()

        logger.debug(
            f"Added {item_type} annotation: {repr(text[:20]) if text else '(empty)'}"
        )

    # ------------------------------------------------------------------ clear / save / load

    def clear_boxes(self) -> None:
        """Remove all annotation items from the scene and clear box_items."""
        for b in self.main_window.box_items:
            self.main_window.scene.removeItem(b)
        self.main_window.box_items.clear()

    def save_current_annotation(self) -> None:
        """Serialize box_items to the annotation dict for the current image."""
        key = self.state.img_key
        if key:
            annotations = [b.to_dict() for b in self.main_window.box_items]
            self.state.annotations[key] = sanitize_annotations(annotations)
            self.update_list_icon(key)

    def load_annotation(self, key: str) -> None:
        """
        Clear the canvas and load annotations for *key*.

        Args:
            key: Image key whose annotations should be displayed.
        """
        ann = self.state.annotations.get(key, [])
        self.clear_boxes()

        for it in ann:
            if is_valid_box(it["points"]):
                pts       = it["points"]
                text      = it.get("transcription", "")
                item_type = it.get("shape", "Quad" if len(pts) == 4 else "Polygon")
                mask_color = it.get("mask_color", None)
                self.add_box_item(pts, text, item_type, mask_color, use_undo=False)

        self.main_window.view.update()
        logger.debug(f"Loaded {len(ann)} annotations for {key}")

    # ------------------------------------------------------------------ list icon

    def update_list_icon(self, key: str) -> None:
        """Refresh the icon / appearance of the list item for *key*."""
        from PyQt5.QtCore import Qt
        lw = self.main_window.list_widget
        for i in range(lw.count()):
            item = lw.item(i)
            if item.data(Qt.UserRole) == key:
                if hasattr(self.main_window, "image_handler"):
                    self.main_window.image_handler.update_item_appearance(item, key)
                else:
                    icon = (
                        self.main_window.icon_marked
                        if self.state.annotations.get(key)
                        else QtGui.QIcon()
                    )
                    item.setIcon(icon)
                break

    # ------------------------------------------------------------------ delete

    def delete_selected(self) -> None:
        """Delete the selected annotations with undo/redo support."""
        sel = self.main_window.scene.selectedItems()
        ann_types = (BoxItem, PolygonItem, MaskQuadItem, MaskPolygonItem)

        indices = []
        for it in sel:
            if isinstance(it, ann_types):
                try:
                    indices.append(self.main_window.box_items.index(it))
                except ValueError:
                    continue

        if not indices:
            QtWidgets.QMessageBox.information(
                self.main_window, "Delete", "No box selected"
            )
            return

        img_key = self.state.img_key
        if not img_key:
            return

        undo_manager = UndoRedoManager.instance()
        cmd = (
            DeleteAnnotationCommand(self.main_window, img_key, indices[0])
            if len(indices) == 1
            else BatchDeleteCommand(self.main_window, img_key, indices)
        )

        if undo_manager.execute(cmd):
            if self.state.recog_mode:
                self.main_window.table_handler.populate_table()
            logger.info(f"Deleted {len(indices)} annotations")
        else:
            QtWidgets.QMessageBox.critical(
                self.main_window, "Error", "Failed to delete annotations"
            )

    # ------------------------------------------------------------------ apply detections

    def apply_detections(self, items: list) -> None:
        """
        Apply auto-detection results to the canvas.

        Args:
            items: List of detection dicts from TextDetector.detect().
        """
        self.clear_boxes()
        for it in items:
            if is_valid_box(it["points"]):
                self.add_box_item(
                    it["points"], it["transcription"], "Polygon",
                    mask_color=None, use_undo=False,
                )
        self.main_window.view.update()
        logger.info(f"Applied {len(items)} detections")
