# modules/gui/main_window.py — coordinator only (no business logic)

import os
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from modules.gui.styles import get_full_stylesheet
from modules.core.ocr import TextDetector
from modules.core.workspace.manager import WorkspaceManager
from modules.core.app_state import AppState
from modules.core.services import Services
from modules.core.undo_redo import UndoRedoManager
from modules.gui.canvas_view import CanvasView
from modules.gui.ui_components import create_toolbar, create_left_dock, create_status_bar
from modules.gui.ui_coordinator import UICoordinator
from modules.gui.dialogs.workspace_selector_dialog import WorkspaceSelectorDialog
from modules.gui.handlers.workspace import WorkspaceHandler
from modules.gui.handlers.image import ImageHandler
from modules.gui.handlers.annotation import AnnotationHandler
from modules.gui.handlers.detection import DetectionHandler
from modules.gui.handlers.ui import UIHandler
from modules.gui.handlers.table import TableHandler
from modules.gui.handlers.export import ExportHandler
from modules.gui.handlers.rotation import RotationHandler
from modules.gui.handlers.clipboard import ClipboardHandler

logger = logging.getLogger("TextDetGUI")


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window — pure coordinator.

    Responsibilities (only):
        - Create AppState, Services, handlers, and UICoordinator.
        - Build Qt widgets via ui_components helpers.
        - Route Qt events (keyPress, close) to handlers and the coordinator.

    All business logic lives in handlers (`modules/gui/handlers/*.py`) or in
    the UICoordinator (`modules/gui/ui_coordinator.py`).  The
    backward-compatibility properties below forward attribute access to
    AppState so legacy handler code that says ``self.main_window.annotations``
    keeps working.
    """

    # ================================================================ init

    def __init__(self):
        super().__init__()

        # 1. AppState first — properties below depend on it
        self._state = AppState()

        # 2. Qt-side canvas list (QGraphicsItem objects, not in AppState)
        self.box_items = []

        # 3. Path setup
        _this = os.path.abspath(__file__)
        root = os.path.dirname(os.path.dirname(os.path.dirname(_this)))
        self.root_dir = root
        self.output_det_dir = os.path.join(root, "output_det")
        self.output_rec_dir = os.path.join(root, "output_rec")
        self.output_dir     = os.path.join(root, "output")
        os.makedirs(self.output_det_dir, exist_ok=True)
        os.makedirs(self.output_rec_dir, exist_ok=True)
        os.makedirs(self.output_dir,     exist_ok=True)

        # 4. Backend services
        self.workspace_manager = WorkspaceManager(root)
        self._services = Services(
            workspace_manager=self.workspace_manager,
            detector=TextDetector(),
            undo_manager=UndoRedoManager.instance(),
        )

        # 5. Handlers, undo/redo, UI, coordinator, initial workspace
        self._init_handlers()
        self._init_undo_redo()
        self._init_ui()
        self.ui_coordinator = UICoordinator(self)
        self._select_initial_workspace()

    # ================================================================ backward-compat properties

    @property
    def img_key(self):              return self._state.img_key
    @img_key.setter
    def img_key(self, v):           self._state.img_key = v

    @property
    def img_path(self):             return self._state.img_path
    @img_path.setter
    def img_path(self, v):          self._state.img_path = v

    @property
    def image_items(self):          return self._state.image_items
    @image_items.setter
    def image_items(self, v):       self._state.image_items = v

    @property
    def annotations(self):          return self._state.annotations
    @annotations.setter
    def annotations(self, v):       self._state.annotations = v

    @property
    def image_rotations(self):      return self._state.image_rotations
    @image_rotations.setter
    def image_rotations(self, v):   self._state.image_rotations = v

    @property
    def modified_images(self):      return self._state.modified_images
    @modified_images.setter
    def modified_images(self, v):   self._state.modified_images = v

    @property
    def draw_mode(self):            return self._state.draw_mode
    @draw_mode.setter
    def draw_mode(self, v):         self._state.draw_mode = v

    @property
    def recog_mode(self):           return self._state.recog_mode
    @recog_mode.setter
    def recog_mode(self, v):        self._state.recog_mode = v

    @property
    def mask_mode(self):            return self._state.mask_mode
    @mask_mode.setter
    def mask_mode(self, v):         self._state.mask_mode = v

    @property
    def annotation_type(self):      return self._state.annotation_type
    @annotation_type.setter
    def annotation_type(self, v):   self._state.annotation_type = v

    @property
    def current_filter(self):       return self._state.current_filter
    @current_filter.setter
    def current_filter(self, v):    self._state.current_filter = v

    @property
    def search_text(self):          return self._state.search_text
    @search_text.setter
    def search_text(self, v):       self._state.search_text = v

    @property
    def detector(self):             return self._services.detector
    @detector.setter
    def detector(self, v):          self._services.detector = v

    # ================================================================ init helpers

    def _init_handlers(self):
        """Create all handler instances, injecting state and services."""
        s, sv = self._state, self._services

        self.workspace_handler  = WorkspaceHandler(s, sv, self)
        self.image_handler      = ImageHandler(s, sv, self)
        self.annotation_handler = AnnotationHandler(s, sv, self)
        self.detection_handler  = DetectionHandler(s, sv, self)
        self.ui_handler         = UIHandler(s, sv, self)
        self.table_handler      = TableHandler(s, sv, self)
        self.export_handler     = ExportHandler(s, sv, self)
        self.rotation_handler   = RotationHandler(s, sv, self)
        self.clipboard_handler  = ClipboardHandler(s, sv, self)

        from modules.gui.mask_handler import MaskHandler
        self.mask_handler = MaskHandler(self)

    def _init_undo_redo(self):
        """Initialize Undo/Redo system."""
        self.undo_manager = UndoRedoManager.instance()
        self.undo_manager.add_change_callback(self._update_undo_redo_ui)

    def _update_undo_redo_ui(self):
        """Update Undo/Redo menu items based on availability."""
        if hasattr(self, 'undo_action_item'):
            can = self.undo_manager.can_undo()
            self.undo_action_item.setEnabled(can)
            desc = self.undo_manager.get_undo_description() if can else ""
            self.undo_action_item.setText(f"Undo {desc}" if desc else "Undo")
        if hasattr(self, 'redo_action_item'):
            can = self.undo_manager.can_redo()
            self.redo_action_item.setEnabled(can)
            desc = self.undo_manager.get_redo_description() if can else ""
            self.redo_action_item.setText(f"Redo {desc}" if desc else "Redo")

    def get_annotations(self, image_key: str):
        """Return a deep copy of annotations for *image_key* (used by undo/redo)."""
        from copy import deepcopy
        return deepcopy(self.annotations.get(image_key, []))

    def set_annotations(self, image_key: str, annotations: list):
        """Set annotations for *image_key* and refresh UI (used by undo/redo)."""
        from modules.utils import sanitize_annotations
        self.annotations[image_key] = sanitize_annotations(annotations)
        if image_key == self.img_key:
            self.annotation_handler.load_annotation(image_key)
        self.annotation_handler.update_list_icon(image_key)
        self.mark_as_modified()

    def _init_ui(self):
        """Create all Qt widgets and the auto-save timer."""
        self.setWindowTitle("OCR Tools Studio")
        self.resize(1400, 900)
        self.setStyleSheet(get_full_stylesheet())

        self.scene = QtWidgets.QGraphicsScene()
        self.view = CanvasView(self)
        self.view.setScene(self.scene)
        self.view.setStyleSheet("background-color: #F0F0F0; border: none;")
        self.setCentralWidget(self.view)

        create_toolbar(self)
        create_left_dock(self)
        create_status_bar(self)

        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self.table_handler.on_table_selection_changed)
        self.table.itemChanged.connect(self.table_handler.on_table_item_changed)
        self.icon_marked = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)

        from PyQt5.QtCore import QTimer
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(300000)  # 5 minutes

        self._restore_window_state()
        logger.info("MainWindow initialized")

    def _select_initial_workspace(self):
        """Pick a workspace at startup — last-used, fallback to selector."""
        if not self.workspace_manager.get_workspace_list():
            self._show_workspace_selector()
            return

        current_ws = self.workspace_manager.app_config.get("current_workspace")
        if current_ws and self.workspace_handler.load_workspace(current_ws):
            self._update_workspace_ui()
            return

        self._show_workspace_selector()

    def _show_workspace_selector(self):
        """Show the workspace selector dialog (or quit if cancelled)."""
        dialog = WorkspaceSelectorDialog(self.workspace_manager, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            workspace_id = dialog.selected_workspace
            if workspace_id:
                self.workspace_handler.load_workspace(workspace_id)
                self._update_workspace_ui()
        else:
            logger.info("No workspace selected. Exiting...")
            QtWidgets.QApplication.quit()

    # ================================================================ delegates → UICoordinator

    def _update_workspace_ui(self):              self.ui_coordinator._update_workspace_ui()
    def _update_recent_workspaces_menu(self):    self.ui_coordinator._update_recent_workspaces_menu()
    def _switch_to_workspace(self, ws_id):       self.ui_coordinator._switch_to_workspace(ws_id)
    def _update_status_bar(self):                self.ui_coordinator._update_status_bar()
    def _update_zoom_label(self):                self.ui_coordinator._update_zoom_label()
    def _reload_workspace_ui(self):              self.ui_coordinator._reload_workspace_ui()

    def create_new_version(self):                self.ui_coordinator.create_new_version()
    def switch_version(self):                    self.ui_coordinator.switch_version()
    def manage_versions(self):                   self.ui_coordinator.manage_versions()
    def next_version(self):                      self.ui_coordinator.next_version()
    def previous_version(self):                  self.ui_coordinator.previous_version()
    def rename_current_workspace(self):          self.ui_coordinator.rename_current_workspace()

    def save_annotations_explicitly(self):       self.ui_coordinator.save_annotations_explicitly()
    def mark_as_modified(self):                  self.ui_coordinator.mark_as_modified()
    def _auto_save(self):                        self.ui_coordinator._auto_save()
    def _save_cache(self):                       self.workspace_handler.save_workspace()

    def on_search_text_changed(self, text):      self.ui_coordinator.on_search_text_changed(text)
    def apply_filter(self, filter_type):         self.ui_coordinator.apply_filter(filter_type)
    def _apply_search_filter(self):              self.ui_coordinator._apply_search_filter()

    def toggle_draw_mode(self, checked):         self.ui_coordinator.toggle_draw_mode(checked)
    def toggle_recog_mode(self, checked):        self.ui_coordinator.toggle_recog_mode(checked)
    def toggle_mask_mode(self, checked):         self.ui_coordinator.toggle_mask_mode(checked)
    def on_mode_changed(self, mode_text):        self.ui_coordinator.on_mode_changed(mode_text)

    def navigate_next_image(self):               self.ui_coordinator.navigate_next_image()
    def navigate_prev_image(self):               self.ui_coordinator.navigate_prev_image()
    def _select_next_annotation(self):           self.ui_coordinator._select_next_annotation()
    def _select_prev_annotation(self):           self.ui_coordinator._select_prev_annotation()

    # ================================================================ workspace dialog launchers

    def switch_workspace(self):
        """Save current then show the workspace selector."""
        if self.workspace_handler.current_workspace_id:
            self.workspace_handler.save_workspace()
        self._show_workspace_selector()

    def create_new_workspace(self):
        """Open the New-Workspace dialog and load the result."""
        from modules.gui.dialogs.workspace_selector_dialog import NewWorkspaceDialog
        dialog = NewWorkspaceDialog(self.workspace_manager, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted and dialog.workspace_id:
            self.workspace_handler.load_workspace(dialog.workspace_id)
            self._update_workspace_ui()

    # ================================================================ settings / help

    def open_settings(self):
        """Open the unified Settings dialog."""
        from modules.gui.dialogs.settings_dialog import SettingsDialog
        from modules.config import ConfigManager
        dialog = SettingsDialog(ConfigManager.instance(), self)
        dialog.settings_changed.connect(self._reload_detector)
        dialog.exec_()

    def _reload_detector(self):
        """Reload OCR detector after settings change."""
        try:
            logger.info("Reloading OCR detector with new settings...")
            self.detector = TextDetector()
            QtWidgets.QMessageBox.information(
                self, "Settings Applied",
                "Settings have been saved successfully.\nOCR detector has been reloaded.",
            )
            logger.info("OCR detector reloaded successfully")
        except (RuntimeError, OSError, ValueError) as e:
            logger.exception("Failed to reload detector")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Failed to reload OCR detector:\n{e}"
            )

    def open_paddleocr_settings(self):
        """Open the advanced PaddleOCR settings dialog."""
        from modules.gui.dialogs.paddleocr_settings_dialog import PaddleOCRSettingsDialog
        dialog = PaddleOCRSettingsDialog(self)
        dialog.settings_changed.connect(self.ui_coordinator._on_paddleocr_settings_changed)
        dialog.exec_()

    def show_help(self):
        """Show the keyboard-shortcut help dialog."""
        from modules.gui.dialogs.help_dialog import HelpDialog
        HelpDialog(self).exec_()

    def show_about(self):
        """Show the About dialog."""
        from modules.__version__ import __version__
        about_text = (
            f"<h2>OCR Tools Studio</h2>"
            f"<p>Version: {__version__}</p>"
            "<p>A professional annotation tool for OCR dataset creation.</p>"
            "<p>Press <b>F1</b> for keyboard shortcuts.</p>"
        )
        QtWidgets.QMessageBox.about(self, "About OCR Tools Studio", about_text)

    # ================================================================ tiny handler delegates

    # Image handler
    def open_folder(self, *args):                self.image_handler.open_folder()
    def on_image_selected(self, item):           self.image_handler.on_image_selected(item)
    def check_only_annotated(self):              self.image_handler.check_only_annotated()
    def uncheck_unannotated(self):               self.image_handler.uncheck_unannotated()
    def select_all_images(self):                 self.image_handler.select_all_images()
    def deselect_all_images(self):               self.image_handler.deselect_all_images()
    def _is_item_checked(self, key):             return self.image_handler.is_item_checked(key)

    # Annotation / detection
    def delete_selected(self, *args):            self.annotation_handler.delete_selected()
    def auto_label_current(self, *args):         self.detection_handler.auto_label_current()
    def auto_label_all(self, *args):             self.detection_handler.auto_label_all()
    def auto_label_selected(self, *args):        self.detection_handler.auto_label_selected()

    # UI handler
    def on_annotation_type_changed(self, t):     self.ui_handler.on_annotation_type_changed(t)
    def update_annotation_info(self):            self.ui_handler.update_annotation_info()
    def add_box_from_rect(self, rect):           self.ui_handler.add_box_from_rect(rect)
    def add_polygon_from_points(self, points):   self.ui_handler.add_polygon_from_points(points)

    # Table (no-op stubs — handler manages itself)
    def on_table_item_changed(self, item):       pass
    def on_table_selection_changed(self):        pass

    # Export / rotation
    def save_labels(self, *args):                self.export_handler.save_labels_detection()
    def export_rec(self, *args):                 self.export_handler.export_recognition()

    def rotate_image(self, angle):
        if hasattr(self, 'rotation_handler'):
            self.rotation_handler.rotate_current_image(angle)

    def reset_rotation(self):
        if hasattr(self, 'rotation_handler'):
            self.rotation_handler.reset_rotation()

    # Mask
    def add_mask_from_rect(self, rect):          self.mask_handler.add_mask_from_rect(rect)
    def add_mask_from_points(self, points):      self.mask_handler.add_mask_from_points(points)
    def choose_mask_color(self):                 self.mask_handler.choose_mask_color()
    def change_selected_mask_color(self):        self.mask_handler.change_selected_mask_color()
    def set_mask_color_preset(self, name):       self.mask_handler.set_mask_color_preset(name)

    # Clipboard
    def copy_annotations(self):                  self.clipboard_handler.copy_selected()
    def paste_annotations(self):                 self.clipboard_handler.paste()
    def cut_annotations(self):                   self.clipboard_handler.cut_selected()

    # Annotation selection (single-image scope)
    def select_all_annotations(self):
        for item in self.box_items:
            item.setSelected(True)
        self.statusBar().showMessage(f"Selected {len(self.box_items)} annotations", 2000)

    def deselect_all_annotations(self):
        for item in self.box_items:
            item.setSelected(False)

    # ================================================================ undo/redo

    def undo_action(self):
        if self.undo_manager.undo():
            self.statusBar().showMessage("Undo successful", 2000)
        else:
            self.statusBar().showMessage("Nothing to undo", 2000)

    def redo_action(self):
        if self.undo_manager.redo():
            self.statusBar().showMessage("Redo successful", 2000)
        else:
            self.statusBar().showMessage("Nothing to redo", 2000)

    # ================================================================ zoom

    def zoom_in(self):
        self.view.scale(1.25, 1.25)
        self.view._zoom *= 1.25
        self._update_zoom_label()

    def zoom_out(self):
        self.view.scale(0.8, 0.8)
        self.view._zoom *= 0.8
        self._update_zoom_label()

    def zoom_fit(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.view._zoom = 1.0
        self._update_zoom_label()

    def zoom_reset(self):
        if self.view._zoom != 0:
            factor = 1.0 / self.view._zoom
            self.view.scale(factor, factor)
            self.view._zoom = 1.0
        self._update_zoom_label()

    # ================================================================ keyPressEvent

    # Maps (key, modifier) → method name on `self`.  Looked up before falling
    # back to the default Qt handler.  Tab/Shift+Tab need special handling
    # because Shift+Tab has its own Qt key code.
    _SHORTCUTS = {
        (Qt.Key_C,        Qt.ControlModifier): "copy_annotations",
        (Qt.Key_V,        Qt.ControlModifier): "paste_annotations",
        (Qt.Key_X,        Qt.ControlModifier): "cut_annotations",
        (Qt.Key_PageDown, Qt.NoModifier):      "navigate_next_image",
        (Qt.Key_Down,     Qt.NoModifier):      "navigate_next_image",
        (Qt.Key_PageUp,   Qt.NoModifier):      "navigate_prev_image",
        (Qt.Key_Up,       Qt.NoModifier):      "navigate_prev_image",
        (Qt.Key_Delete,    Qt.NoModifier):     "delete_selected",
        (Qt.Key_Backspace, Qt.NoModifier):     "delete_selected",
        (Qt.Key_A,        Qt.ControlModifier): "select_all_annotations",
        (Qt.Key_Plus,     Qt.NoModifier):      "zoom_in",
        (Qt.Key_Equal,    Qt.NoModifier):      "zoom_in",
        (Qt.Key_Minus,    Qt.NoModifier):      "zoom_out",
        (Qt.Key_0,        Qt.NoModifier):      "zoom_fit",
        (Qt.Key_F,        Qt.NoModifier):      "zoom_fit",
        (Qt.Key_1,        Qt.NoModifier):      "zoom_reset",
        (Qt.Key_Tab,      Qt.NoModifier):      "_select_next_annotation",
    }

    def keyPressEvent(self, event):
        """Route keyboard shortcuts to handlers; fall through to Qt default."""
        key, mods = event.key(), event.modifiers()

        if key == Qt.Key_Escape:
            self.deselect_all_annotations()
            if hasattr(self.view, 'polygon_points') and self.view.polygon_points:
                self.view._cancel_polygon()
            return

        if key == Qt.Key_Space and mods == Qt.NoModifier:
            if hasattr(self, 'draw_action'):
                self.draw_action.toggle()
                self.toggle_draw_mode(self.draw_action.isChecked())
            return

        # Shift+Tab — special-case (Qt.Key_Backtab OR Tab+Shift)
        if key == Qt.Key_Backtab or (key == Qt.Key_Tab and mods == Qt.ShiftModifier):
            self._select_prev_annotation()
            return

        method_name = self._SHORTCUTS.get((key, mods))
        if method_name:
            getattr(self, method_name)()
            return

        super().keyPressEvent(event)

    # ================================================================ closeEvent + window state

    def closeEvent(self, event):
        """Save workspace and window state before closing."""
        QtWidgets.QApplication.processEvents()
        if self.workspace_handler.current_workspace_id:
            self.workspace_handler.save_workspace()
        self._save_window_state()
        super().closeEvent(event)
        logger.info("Application closed")

    def _save_window_state(self) -> None:
        """Save window geometry and dock/toolbar state to ``data/app_config.json``."""
        try:
            import base64
            ui_state = self.workspace_manager.app_config.setdefault("ui_state", {})
            ui_state["geometry"]     = base64.b64encode(bytes(self.saveGeometry())).decode()
            ui_state["window_state"] = base64.b64encode(bytes(self.saveState())).decode()
            self.workspace_manager.save_app_config()
            logger.debug("Window state saved")
        except Exception:
            logger.exception("Failed to save window state")

    def _restore_window_state(self) -> None:
        """Restore window geometry and dock/toolbar state from ``data/app_config.json``."""
        try:
            import base64
            from PyQt5.QtCore import QByteArray
            ui_state = self.workspace_manager.app_config.get("ui_state", {})
            geom_b64 = ui_state.get("geometry")
            if geom_b64:
                self.restoreGeometry(QByteArray(base64.b64decode(geom_b64)))
            state_b64 = ui_state.get("window_state")
            if state_b64:
                self.restoreState(QByteArray(base64.b64decode(state_b64)))
        except Exception:
            logger.exception("Failed to restore window state — using defaults")
