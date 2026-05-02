# modules/gui/handlers/table.py

import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from modules.utils import handle_exceptions, sanitize_annotations
from modules.core.undo_redo import UndoRedoManager, UpdateTranscriptionCommand

logger = logging.getLogger("TextDetGUI")
PLACEHOLDER_TEXT = "<no_label>"


class TableHandler:
    """
    Manage the Recognition table: display and edit transcriptions.

    box_items (Qt graphics objects) remain in main_window.
    img_key is read from self.state (AppState).
    """

    def __init__(self, state, services, main_window):
        self.state       = state
        self.services    = services
        self.main_window = main_window

    # ------------------------------------------------------------------ helpers

    def _get_annotation_items_with_transcription(self):
        """Return [(original_idx, box_item), ...] for items that have a transcription."""
        result = []
        for idx, box in enumerate(self.main_window.box_items):
            if hasattr(box, "get_transcription") and callable(box.get_transcription):
                result.append((idx, box))
        return result

    # ------------------------------------------------------------------ public

    def populate_table(self) -> None:
        """Fill the table with transcriptions of the current image's annotations."""
        table = self.main_window.table
        table.blockSignals(True)
        table.clearContents()

        items = self._get_annotation_items_with_transcription()
        table.setRowCount(len(items))

        for table_row, (original_idx, box) in enumerate(items):
            # Column 0: ID (read-only)
            id_cell = QtWidgets.QTableWidgetItem(str(original_idx))
            id_cell.setFlags(id_cell.flags() & ~Qt.ItemIsEditable)
            id_cell.setData(Qt.UserRole, original_idx)
            table.setItem(table_row, 0, id_cell)

            # Column 1: Transcription (editable)
            txt  = box.get_transcription() or PLACEHOLDER_TEXT
            cell = QtWidgets.QTableWidgetItem(txt)
            cell.setData(Qt.UserRole, original_idx)
            table.setItem(table_row, 1, cell)

            table.setRowHeight(table_row, 40)

        table.blockSignals(False)
        logger.debug(
            f"Populated table: {len(items)} items "
            f"(of {len(self.main_window.box_items)} total)"
        )

    @handle_exceptions
    def on_table_item_changed(self, item) -> None:
        """Handle in-place transcription edits with undo/redo support."""
        if item.column() != 1:
            return

        original_idx = item.data(Qt.UserRole)
        if original_idx is None or original_idx >= len(self.main_window.box_items):
            return

        box = self.main_window.box_items[original_idx]
        if not (hasattr(box, "set_transcription") and callable(box.set_transcription)):
            logger.warning(f"Box {original_idx} has no set_transcription method")
            return

        new_txt = item.text().strip() or PLACEHOLDER_TEXT
        old_txt = box.get_transcription() or PLACEHOLDER_TEXT
        if new_txt == old_txt:
            return

        img_key = self.state.img_key
        if img_key:
            undo_manager = UndoRedoManager.instance()
            cmd = UpdateTranscriptionCommand(
                self.main_window, img_key, original_idx, new_txt
            )
            undo_manager.execute(cmd)
            box.set_transcription(new_txt)
        else:
            # Fallback: direct update without undo
            box.set_transcription(new_txt)
            anns = [b.to_dict() for b in self.main_window.box_items]
            self.state.annotations[img_key] = sanitize_annotations(anns)
            self.main_window.workspace_handler.save_workspace()

        logger.debug(f"Updated transcription for box {original_idx}: {new_txt[:20]}")

    def on_table_selection_changed(self) -> None:
        """Highlight the annotation corresponding to the selected table row."""
        for box in self.main_window.box_items:
            box.setSelected(False)

        sel = self.main_window.table.selectedIndexes()
        if not sel:
            return

        id_cell = self.main_window.table.item(sel[0].row(), 0)
        if not id_cell:
            return

        original_idx = id_cell.data(Qt.UserRole)
        if original_idx is not None and original_idx < len(self.main_window.box_items):
            box = self.main_window.box_items[original_idx]
            box.setSelected(True)
            self.main_window.view.centerOn(box)
            logger.debug(f"Selected box {original_idx} from table")
