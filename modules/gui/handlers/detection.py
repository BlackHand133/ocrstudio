# modules/gui/handlers/detection.py

import logging

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from modules.utils import handle_exceptions, sanitize_annotations

logger = logging.getLogger("TextDetGUI")


def is_valid_box(pts) -> bool:
    if not (isinstance(pts, list) and len(pts) >= 4):
        return False
    return all(isinstance(p, (list, tuple)) and len(p) == 2 for p in pts)


class DetectionHandler:
    """
    Manage auto-detection with PaddleOCR.

    detector lives in self.services (Services).
    img_path / img_key / annotations / image_items are read from self.state (AppState).
    Qt widgets are accessed through self.main_window.
    """

    def __init__(self, state, services, main_window):
        self.state       = state
        self.services    = services
        self.main_window = main_window

    # ------------------------------------------------------------------ current image

    @handle_exceptions
    def auto_label_current(self) -> None:
        """Run auto-detection on the currently displayed image."""
        if not self.state.img_path:
            QtWidgets.QMessageBox.warning(
                self.main_window, "Warning", "Please select an image first"
            )
            return

        existing = len(self.main_window.box_items)
        if existing > 0:
            reply = QtWidgets.QMessageBox.question(
                self.main_window,
                "Existing Annotations",
                f"This image has {existing} existing annotations.\n\n"
                f"Do you want to replace them with auto-detection results?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if reply != QtWidgets.QMessageBox.Yes:
                return

        self.main_window.annotation_handler.clear_boxes()
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            items = self.services.detector.detect(self.state.img_path)
            self.main_window.annotation_handler.apply_detections(items)

            key = self.state.img_key
            self.state.annotations[key] = sanitize_annotations(
                [b.to_dict() for b in self.main_window.box_items]
            )
            self.main_window.annotation_handler.update_list_icon(key)
            self.main_window.workspace_handler.save_workspace()

            if self.state.recog_mode:
                self.main_window.table_handler.populate_table()

            logger.info(f"Auto-labeled current: {len(items)} regions")
            self.main_window.statusBar().showMessage(
                f"Auto-detection complete: {len(items)} text regions found", 5000
            )
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    # ------------------------------------------------------------------ all images

    @handle_exceptions
    def auto_label_all(self) -> None:
        """Run auto-detection on every image in the catalogue."""
        if not self.state.image_items:
            QtWidgets.QMessageBox.warning(
                self.main_window, "Warning", "Please open a folder first"
            )
            return

        total = len(self.state.image_items)
        reply = QtWidgets.QMessageBox.question(
            self.main_window,
            "Auto Detection — All Images",
            f"Run auto-detection on all {total} images?\n\n"
            f"This will replace existing annotations.\n"
            f"This operation may take a while.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        self._run_batch_detection(self.state.image_items, "Auto Detection")

    # ------------------------------------------------------------------ selected images

    @handle_exceptions
    def auto_label_selected(self) -> None:
        """Run auto-detection on checked images only."""
        lw = self.main_window.list_widget
        checked = []
        for i in range(lw.count()):
            item = lw.item(i)
            if item.checkState() == Qt.Checked:
                key = item.data(Qt.UserRole)
                for k, full in self.state.image_items:
                    if k == key:
                        checked.append((key, full))
                        break

        if not checked:
            QtWidgets.QMessageBox.warning(
                self.main_window,
                "Warning",
                "Please check (☑) images for Auto Detection",
            )
            return

        reply = QtWidgets.QMessageBox.question(
            self.main_window,
            "Auto Detection — Selected Images",
            f"Run auto-detection on {len(checked)} selected images?\n\n"
            f"This will replace existing annotations.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes,
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return

        self._run_batch_detection(checked, "Auto Detection — Selected")

    # ------------------------------------------------------------------ batch helper

    def _run_batch_detection(self, image_list: list, title: str) -> None:
        total    = len(image_list)
        progress = QtWidgets.QProgressDialog(
            "Running Auto Detection...", "Cancel", 0, total, self.main_window
        )
        progress.setWindowTitle(title)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        success_count = fail_count = 0

        try:
            for i, (key, full) in enumerate(image_list):
                if progress.wasCanceled():
                    logger.info(f"{title} cancelled by user")
                    break

                progress.setValue(i)
                progress.setLabelText(f"Processing: {key}\n({i + 1}/{total})")
                QtWidgets.QApplication.processEvents()

                try:
                    items = self.services.detector.detect(full)
                    valid = [
                        {**it, "shape": "Polygon"}
                        for it in items
                        if is_valid_box(it["points"])
                    ]
                    self.state.annotations[key] = sanitize_annotations(valid)
                    self.main_window.annotation_handler.update_list_icon(key)
                    success_count += 1
                    logger.debug(f"Auto-labeled {key}: {len(valid)} regions")
                except Exception as e:
                    logger.error(f"Auto-label failed on {key}: {e}")
                    fail_count += 1

            progress.setValue(total)
            self.main_window.workspace_handler.save_workspace()

            # Refresh display if current image was processed
            if self.state.img_key:
                self.main_window.image_handler.on_image_selected(
                    self._find_list_item(self.state.img_key)
                )

            logger.info(f"{title} done: {success_count} ok, {fail_count} failed")
            QtWidgets.QMessageBox.information(
                self.main_window,
                "Done",
                f"{title} finished\n\nSuccess: {success_count}\nFailed: {fail_count}",
            )
        finally:
            progress.close()

    # ------------------------------------------------------------------ helpers

    def _find_list_item(self, key: str):
        """Return the QListWidgetItem for *key*, or None."""
        lw = self.main_window.list_widget
        from PyQt5.QtCore import Qt
        for i in range(lw.count()):
            item = lw.item(i)
            if item.data(Qt.UserRole) == key:
                return item
        return None
