# modules/gui/handlers/image.py

import os
import logging

import cv2
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QRectF

from modules.utils import sanitize_filename
from modules.constants import IMAGE_EXTENSIONS

logger = logging.getLogger("TextDetGUI")


class ImageHandler:
    """
    Manage image loading, display, and list appearance.

    Image catalogue and current-image state are stored in self.state (AppState).
    Qt widgets are accessed through self.main_window.
    """

    # Background colours for different annotation / selection states
    COLOR_NORMAL    = QtGui.QColor(255, 255, 255)
    COLOR_ANNOTATED = QtGui.QColor(200, 255, 200)
    COLOR_CHECKED   = QtGui.QColor(200, 230, 255)
    COLOR_BOTH      = QtGui.QColor(180, 255, 200)

    def __init__(self, state, services, main_window):
        self.state       = state
        self.services    = services
        self.main_window = main_window

    # ------------------------------------------------------------------ folder

    def open_folder(self) -> None:
        """Show a folder picker and load images from the selected path."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, "Select Image Folder", ""
        )
        if folder:
            self.load_images_from_folder(folder)

    # Threshold above which the list is populated in chunks via a QTimer
    # to keep the UI responsive while loading huge workspaces.
    _LAZY_LOAD_THRESHOLD = 1000
    _LAZY_LOAD_CHUNK     = 200  # items loaded per timer tick

    def load_images_from_folder(self, folder: str) -> None:
        """
        Scan *folder* recursively and populate the image list.

        For workspaces with more than ``_LAZY_LOAD_THRESHOLD`` images, items
        are added in chunks via a QTimer so the GUI stays responsive and the
        first images appear immediately.  Smaller workspaces load synchronously.

        Args:
            folder: Absolute path to the folder containing images.
        """
        if not folder or not os.path.exists(folder):
            logger.warning(f"Invalid folder path: {folder}")
            return

        exts = set(IMAGE_EXTENSIONS)

        # Phase 1 — scan filesystem (fast: just stat() + ext check)
        scanned: list = []
        for root_dir, _, files in os.walk(folder):
            for fn in sorted(files):
                if os.path.splitext(fn.lower())[1] in exts:
                    scanned.append((fn, os.path.join(root_dir, fn)))

        self.state.image_items = scanned
        lw = self.main_window.list_widget
        lw.clear()
        # Uniform sizes lets QListWidget skip per-row size hints — huge perf win
        lw.setUniformItemSizes(True)

        total = len(scanned)
        if total <= self._LAZY_LOAD_THRESHOLD:
            # Small workspace — populate synchronously, but still batch repaints
            self._populate_chunk(scanned, lw, batched=True)
            logger.info(f"Loaded {total} images from {folder}")
            return

        # Large workspace — chunked loading via QTimer
        logger.info(
            f"Lazy-loading {total} images from {folder} "
            f"({self._LAZY_LOAD_CHUNK} per tick)"
        )

        # Cancel any in-flight lazy load
        self._cancel_lazy_load()

        # Track progress on a status bar message
        self._lazy_pending = scanned[:]
        self._lazy_total   = total
        self._lazy_loaded  = 0

        from PyQt5.QtCore import QTimer
        self._lazy_timer = QTimer(self.main_window)
        self._lazy_timer.setInterval(0)  # fire on next event-loop tick
        self._lazy_timer.timeout.connect(self._lazy_load_tick)
        self._lazy_timer.start()

    # ------------------------------------------------------------------ lazy-load helpers

    def _populate_chunk(self, items, lw, batched: bool = False) -> None:
        """Add *items* (list of (key, full_path) tuples) to the list widget."""
        if batched:
            lw.setUpdatesEnabled(False)
            lw.blockSignals(True)
        try:
            for key, _full in items:
                item = QtWidgets.QListWidgetItem(key)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setData(Qt.UserRole, key)
                self.update_item_appearance(item, key)
                lw.addItem(item)
        finally:
            if batched:
                lw.blockSignals(False)
                lw.setUpdatesEnabled(True)

    def _lazy_load_tick(self) -> None:
        """Timer callback — populate the next chunk of pending items."""
        chunk = self._lazy_pending[: self._LAZY_LOAD_CHUNK]
        self._lazy_pending = self._lazy_pending[self._LAZY_LOAD_CHUNK :]

        if not chunk:
            self._cancel_lazy_load()
            logger.info(f"Lazy-load complete: {self._lazy_total} images")
            if hasattr(self.main_window, "statusBar"):
                self.main_window.statusBar().showMessage(
                    f"Loaded {self._lazy_total} images", 3000
                )
            return

        self._populate_chunk(chunk, self.main_window.list_widget, batched=True)
        self._lazy_loaded += len(chunk)

        if hasattr(self.main_window, "statusBar"):
            self.main_window.statusBar().showMessage(
                f"Loading images... {self._lazy_loaded}/{self._lazy_total}"
            )

    def _cancel_lazy_load(self) -> None:
        """Stop any in-flight lazy-load timer (e.g. when switching workspaces)."""
        timer = getattr(self, "_lazy_timer", None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()
            self._lazy_timer = None
        self._lazy_pending = []

    # ------------------------------------------------------------------ appearance

    def update_item_appearance(self, item, key: str) -> None:
        """
        Refresh background colour, icon, and text decoration for *item*.

        Args:
            item: QListWidgetItem to update.
            key:  Image key used to look up annotation / modified state.
        """
        has_annotation = bool(self.state.annotations.get(key))
        is_checked     = item.checkState() == Qt.Checked
        is_modified    = key in self.state.modified_images

        display_text = f"* {key}" if is_modified else key
        item.setText(display_text)

        item.setIcon(
            self.main_window.icon_marked if has_annotation else QtGui.QIcon()
        )

        font = item.font()
        if is_modified:
            item.setBackground(QtGui.QColor(255, 200, 100))
            font.setItalic(True)
        elif has_annotation and is_checked:
            item.setBackground(self.COLOR_BOTH)
            font.setBold(True)
            font.setItalic(False)
        elif has_annotation:
            item.setBackground(self.COLOR_ANNOTATED)
            font.setBold(False)
            font.setItalic(False)
        elif is_checked:
            item.setBackground(self.COLOR_CHECKED)
            font.setBold(False)
            font.setItalic(False)
        else:
            item.setBackground(self.COLOR_NORMAL)
            font.setBold(False)
            font.setItalic(False)
        item.setFont(font)

    def refresh_all_items_appearance(self) -> None:
        """Redraw all list items to reflect current annotation state."""
        lw = self.main_window.list_widget
        for i in range(lw.count()):
            item = lw.item(i)
            self.update_item_appearance(item, item.data(Qt.UserRole))

    # ------------------------------------------------------------------ selection

    def on_image_selected(self, item) -> None:
        """Handle user clicking an image in the list widget."""
        QtWidgets.QApplication.processEvents()

        self.main_window.annotation_handler.save_current_annotation()

        key = item.data(Qt.UserRole)
        for k, full in self.state.image_items:
            if k == key:
                self.load_image(k, full)
                break

        self.main_window.annotation_handler.load_annotation(key)

        if self.state.recog_mode:
            self.main_window.table_handler.populate_table()

        self.refresh_all_items_appearance()

    # ------------------------------------------------------------------ load

    def load_image(self, key: str, full_path: str) -> None:
        """
        Load and display an image on the canvas.

        Applies any stored rotation via RotationHandler before display.

        Args:
            key:       Image key (filename).
            full_path: Absolute path to the image file.
        """
        self.state.img_key  = key
        self.state.img_path = full_path

        self.main_window.scene.clear()
        self.main_window.box_items.clear()

        if hasattr(self.main_window, "rotation_handler"):
            img = self.main_window.rotation_handler.get_rotated_image(full_path, key)
            if img is not None:
                img_rgb       = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                h, w, c       = img_rgb.shape
                bytes_per_line = c * w
                q_img = QtGui.QImage(
                    img_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888
                )
                pix = QtGui.QPixmap.fromImage(q_img)
            else:
                pix = QtGui.QPixmap(full_path)
        else:
            pix = QtGui.QPixmap(full_path)

        self.main_window.scene.addPixmap(pix).setZValue(0)
        self.main_window.scene.setSceneRect(QRectF(pix.rect()))
        self.main_window.view.fitInView(
            self.main_window.scene.sceneRect(), Qt.KeepAspectRatio
        )

        logger.debug(f"Loaded image: {key}")

    # ------------------------------------------------------------------ checkbox helpers

    def is_item_checked(self, key: str) -> bool:
        lw = self.main_window.list_widget
        for i in range(lw.count()):
            item = lw.item(i)
            if item.data(Qt.UserRole) == key:
                return item.checkState() == Qt.Checked
        return False

    def check_only_annotated(self) -> None:
        lw = self.main_window.list_widget
        for i in range(lw.count()):
            item = lw.item(i)
            key  = item.data(Qt.UserRole)
            state = Qt.Checked if self.state.annotations.get(key) else Qt.Unchecked
            item.setCheckState(state)
            self.update_item_appearance(item, key)
        logger.info("Checked only annotated images")

    def uncheck_unannotated(self) -> None:
        lw = self.main_window.list_widget
        for i in range(lw.count()):
            item = lw.item(i)
            key  = item.data(Qt.UserRole)
            if not self.state.annotations.get(key):
                item.setCheckState(Qt.Unchecked)
                self.update_item_appearance(item, key)
        logger.info("Unchecked unannotated images")

    def select_all_images(self) -> None:
        lw = self.main_window.list_widget
        for i in range(lw.count()):
            item = lw.item(i)
            item.setCheckState(Qt.Checked)
            self.update_item_appearance(item, item.data(Qt.UserRole))
        logger.info("Selected all images")

    def deselect_all_images(self) -> None:
        lw = self.main_window.list_widget
        for i in range(lw.count()):
            item = lw.item(i)
            item.setCheckState(Qt.Unchecked)
            self.update_item_appearance(item, item.data(Qt.UserRole))
        logger.info("Deselected all images")
