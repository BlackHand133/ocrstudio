# modules/gui/main_window.py (Workspace System + Masking Feature)

import os
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from modules.gui.styles import get_full_stylesheet
from modules.detector import TextDetector
from modules.core.workspace.manager import WorkspaceManager
from modules.gui.canvas_view import CanvasView
from modules.gui.ui_components import create_toolbar, create_left_dock, create_status_bar
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
from modules.core.undo_redo import UndoRedoManager

logger = logging.getLogger("TextDetGUI")


class MainWindow(QtWidgets.QMainWindow):
    """
    Main window of the application (Workspace System + Masking)
    """

    def __init__(self):
        super().__init__()

        # Initialize detector (use config from config/config.yaml)
        self.detector = TextDetector()  # Don't pass parameters = use config.yaml
        
        # Data attributes
        self.image_items = []      # List of (key, full_path)
        self.img_key = None         # Current image key
        self.img_path = None        # Current image path
        self.box_items = []         # List of BoxItem/PolygonItem/MaskItem
        self.annotations = {}       # Dict: key -> list of annotations
        self.draw_mode = False      # Drawing mode flag
        self.recog_mode = False     # Recognition mode flag
        self.annotation_type = 'Quad'  # 'Quad' or 'Polygon'
        self.mask_mode = False      # 🔒 Masking mode flag (NEW!)
        self.image_rotations = {}   # Dict: key -> rotation angle
        self.modified_images = set()  # Track modified images since last save
        self.current_filter = "all"  # Current filter: "all", "annotated", "empty"
        self.search_text = ""  # Current search text

        # Path setup
        this = os.path.abspath(__file__)
        root = os.path.dirname(os.path.dirname(os.path.dirname(this)))
        self.root_dir = root
        self.output_det_dir = os.path.join(root, "output_det")
        self.output_rec_dir = os.path.join(root, "output_rec")
        self.output_dir = os.path.join(root, "output")
        
        # Create output directories
        os.makedirs(self.output_det_dir, exist_ok=True)
        os.makedirs(self.output_rec_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize workspace manager
        self.workspace_manager = WorkspaceManager(root)
        
        # Initialize handlers
        self._init_handlers()

        # Initialize Undo/Redo system
        self._init_undo_redo()

        # Initialize UI
        self._init_ui()

        # Select workspace
        self._select_initial_workspace()
    
    def _init_handlers(self):
        """Create handler instances"""
        self.workspace_handler = WorkspaceHandler(self)
        self.image_handler = ImageHandler(self)
        self.annotation_handler = AnnotationHandler(self)
        self.detection_handler = DetectionHandler(self)
        self.ui_handler = UIHandler(self)
        self.table_handler = TableHandler(self)
        self.export_handler = ExportHandler(self)
        self.rotation_handler = RotationHandler(self)

        # 🔒 Mask Handler (NEW!)
        from modules.gui.mask_handler import MaskHandler
        self.mask_handler = MaskHandler(self)

        # Clipboard Handler
        self.clipboard_handler = ClipboardHandler(self)

    def _init_undo_redo(self):
        """Initialize Undo/Redo system"""
        self.undo_manager = UndoRedoManager.instance()
        # Add callback to update UI when undo/redo state changes
        self.undo_manager.add_change_callback(self._update_undo_redo_ui)

    def _update_undo_redo_ui(self):
        """Update Undo/Redo menu items based on availability"""
        if hasattr(self, 'undo_action_item'):
            can_undo = self.undo_manager.can_undo()
            self.undo_action_item.setEnabled(can_undo)
            if can_undo:
                desc = self.undo_manager.get_undo_description()
                self.undo_action_item.setText(f"Undo {desc}" if desc else "Undo")
            else:
                self.undo_action_item.setText("Undo")

        if hasattr(self, 'redo_action_item'):
            can_redo = self.undo_manager.can_redo()
            self.redo_action_item.setEnabled(can_redo)
            if can_redo:
                desc = self.undo_manager.get_redo_description()
                self.redo_action_item.setText(f"Redo {desc}" if desc else "Redo")
            else:
                self.redo_action_item.setText("Redo")

    def get_annotations(self, image_key: str):
        """Get annotations for an image (for undo/redo system)"""
        from copy import deepcopy
        # Return a copy to prevent direct modification of internal state
        return deepcopy(self.annotations.get(image_key, []))

    def set_annotations(self, image_key: str, annotations: list):
        """Set annotations for an image and refresh UI (for undo/redo system)"""
        from modules.utils import sanitize_annotations
        self.annotations[image_key] = sanitize_annotations(annotations)

        # Refresh display if this is current image
        if image_key == self.img_key:
            self.annotation_handler.load_annotation(image_key)

        # Update list icon
        self.annotation_handler.update_list_icon(image_key)

        # Mark as modified
        self.mark_as_modified()

    def _init_ui(self):
        """Create UI"""
        self.setWindowTitle("OCR Tools Studio")
        self.resize(1400, 900)

        # Apply global stylesheet
        self.setStyleSheet(get_full_stylesheet())

        # Create scene and view
        self.scene = QtWidgets.QGraphicsScene()
        self.view = CanvasView(self)
        self.view.setScene(self.scene)
        self.view.setStyleSheet("background-color: #F0F0F0; border: none;")
        self.setCentralWidget(self.view)

        # Create UI components
        create_toolbar(self)
        create_left_dock(self)
        create_status_bar(self)

        # Setup table
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self.table_handler.on_table_selection_changed)
        self.table.itemChanged.connect(self.table_handler.on_table_item_changed)

        # Icon for marked items
        self.icon_marked = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)

        # Auto-save timer (every 5 minutes)
        from PyQt5.QtCore import QTimer
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(300000)  # 5 minutes = 300000 ms

        logger.info("MainWindow initialized")
    
    def _select_initial_workspace(self):
        """Select workspace when starting program"""
        # Check if workspace exists
        workspaces = self.workspace_manager.get_workspace_list()

        if not workspaces:
            # No workspace -> show dialog
            self._show_workspace_selector()
        else:
            # Try to load last workspace
            current_ws = self.workspace_manager.app_config.get("current_workspace")

            if current_ws:
                success = self.workspace_handler.load_workspace(current_ws)
                if success:
                    # Load successful -> update UI
                    self._update_workspace_ui()
                    return

            # If load failed -> show selector
            self._show_workspace_selector()

    def _show_workspace_selector(self):
        """Show workspace selector dialog"""
        dialog = WorkspaceSelectorDialog(self.workspace_manager, self)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            workspace_id = dialog.selected_workspace
            if workspace_id:
                self.workspace_handler.load_workspace(workspace_id)
                self._update_workspace_ui()
        else:
            # User pressed cancel -> exit program
            logger.info("No workspace selected. Exiting...")
            QtWidgets.QApplication.quit()

    def _update_workspace_ui(self):
        """Update UI after loading workspace"""
        ws_info = self.workspace_handler.get_workspace_info()

        if ws_info:
            # Update window title
            title = f"TextDet GUI - {ws_info['name']} ({ws_info['current_version']})"
            self.setWindowTitle(title)

            # Update workspace label
            if hasattr(self, 'workspace_label'):
                self.workspace_label.setText(
                    f"  📁 {ws_info['name']} ({ws_info['current_version']})"
                )

            # Update recent workspaces menu
            self._update_recent_workspaces_menu()

            # Update status bar
            self._update_status_bar()

            # Auto-load images from workspace source folder
            if hasattr(self, 'image_handler') and ws_info.get('source_folder'):
                source_folder = ws_info['source_folder']
                self.image_handler.load_images_from_folder(source_folder)
                image_count = self.list_widget.count() if hasattr(self, 'list_widget') else 0
                logger.info(f"Auto-loaded {image_count} images from: {source_folder}")

            logger.info(f"Workspace loaded: {ws_info['name']}")

    def _update_recent_workspaces_menu(self):
        """Update recent workspaces menu with latest data"""
        if not hasattr(self, 'recent_workspaces_menu'):
            return

        # Clear existing actions
        self.recent_workspaces_menu.clear()

        # Get recent workspaces
        recent = self.workspace_manager.get_recent_workspaces()

        if not recent:
            # No recent workspaces
            action = QtWidgets.QAction("(No recent workspaces)", self)
            action.setEnabled(False)
            self.recent_workspaces_menu.addAction(action)
            return

        # Add recent workspaces (max 6)
        current_ws = self.workspace_handler.current_workspace_id

        for ws_data in recent[:6]:
            ws_id = ws_data.get('id')
            ws_name = ws_data.get('name', ws_id)
            last_opened = ws_data.get('last_opened', '')

            # Format last opened time
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(last_opened)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception as e:
                logger.debug(f"Failed to parse date '{last_opened}': {e}")
                time_str = 'Unknown'

            # Create action
            if ws_id == current_ws:
                action = QtWidgets.QAction(f"✓ {ws_name}  ({time_str})", self)
                action.setEnabled(False)  # Current workspace is disabled
            else:
                action = QtWidgets.QAction(f"  {ws_name}  ({time_str})", self)
                action.triggered.connect(lambda checked, wid=ws_id: self._switch_to_workspace(wid))

            self.recent_workspaces_menu.addAction(action)

        # Add separator and "More..." option
        if len(recent) > 0:
            self.recent_workspaces_menu.addSeparator()
            action = QtWidgets.QAction("More Workspaces...", self)
            action.triggered.connect(self.switch_workspace)
            self.recent_workspaces_menu.addAction(action)

    def _switch_to_workspace(self, workspace_id):
        """Switch to specific workspace by ID"""
        if workspace_id == self.workspace_handler.current_workspace_id:
            return

        # Save current workspace
        if self.workspace_handler.current_workspace_id:
            self.workspace_handler.save_workspace()

        # Load new workspace
        success = self.workspace_handler.load_workspace(workspace_id)

        if success:
            # Reload UI
            self._reload_workspace_ui()
        else:
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to load workspace: {workspace_id}"
            )

    def _update_status_bar(self):
        """Update status bar with workspace statistics"""
        if not hasattr(self, 'statusBar'):
            return

        ws_info = self.workspace_handler.get_workspace_info()

        # Update progress label
        if hasattr(self, 'progress_label'):
            annotated_count = sum(1 for anns in self.annotations.values() if anns)
            total_count = len(self.image_items)
            self.progress_label.setText(f"{annotated_count}/{total_count} labeled")

        # Update annotation count for current image
        if hasattr(self, 'annotation_count_label'):
            count = len(self.box_items)
            self.annotation_count_label.setText(f"{count} annotation{'s' if count != 1 else ''}")

        # Update mode indicator
        if hasattr(self, 'mode_status_label'):
            if self.draw_mode:
                self.mode_status_label.setText("Draw")
                self.mode_status_label.setStyleSheet("color: #2196F3; padding: 0 8px; font-weight: bold;")
            elif self.mask_mode:
                self.mode_status_label.setText("Mask")
                self.mode_status_label.setStyleSheet("color: #F44336; padding: 0 8px; font-weight: bold;")
            elif self.recog_mode:
                self.mode_status_label.setText("Edit")
                self.mode_status_label.setStyleSheet("color: #4CAF50; padding: 0 8px; font-weight: bold;")
            else:
                self.mode_status_label.setText("View")
                self.mode_status_label.setStyleSheet("color: #616161; padding: 0 8px;")

        # Update main message
        if not ws_info:
            self.statusBar().showMessage("Ready")
            return

        # Build status message
        if hasattr(self.workspace_handler, 'is_saved') and not self.workspace_handler.is_saved:
            self.statusBar().showMessage(f"● {ws_info['name']} - {ws_info['current_version']} - Unsaved changes")
        else:
            self.statusBar().showMessage(f"{ws_info['name']} - {ws_info['current_version']}")

    def _update_zoom_label(self):
        """Update zoom level in status bar"""
        if hasattr(self, 'zoom_label'):
            zoom_percent = int(self.view._zoom * 100)
            self.zoom_label.setText(f"{zoom_percent}%")

    def _reload_workspace_ui(self):
        """Reload entire UI after version switch - ensures clean state"""
        try:
            # Clear current UI state
            self.scene.clear()
            self.box_items.clear()
            self.modified_images.clear()  # Clear change tracking
            self.list_widget.clear()
            self.img_key = None

            # Clear undo/redo history on workspace reload
            self.undo_manager.clear()

            # Clear current image display
            if hasattr(self, 'pixmap_item'):
                self.pixmap_item = None

            # Update workspace info (title, labels) - this also loads images now
            self._update_workspace_ui()

            # Select and display first image if available
            if self.list_widget.count() > 0:
                self.list_widget.setCurrentRow(0)
                # Trigger image display
                if hasattr(self, 'image_handler'):
                    first_item = self.list_widget.item(0)
                    if first_item:
                        self.image_handler.on_image_selected(first_item)
                logger.info(f"Displayed first image after reload")

            logger.info("UI reloaded successfully after version switch")

        except Exception as e:
            logger.error(f"Error reloading UI after version switch: {e}", exc_info=True)
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to reload UI after version switch:\n{str(e)}"
            )
    
    # ===== Workspace Methods =====

    def switch_workspace(self):
        """Switch workspace"""
        # Save current workspace first
        if self.workspace_handler.current_workspace_id:
            self.workspace_handler.save_workspace()

        # Show selector
        self._show_workspace_selector()

    def create_new_workspace(self):
        """Create new workspace"""
        from modules.gui.dialogs.workspace_selector_dialog import NewWorkspaceDialog

        dialog = NewWorkspaceDialog(self.workspace_manager, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            workspace_id = dialog.workspace_id
            if workspace_id:
                self.workspace_handler.load_workspace(workspace_id)
                self._update_workspace_ui()

    def create_new_version(self):
        """Create new version"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return

        # Dialog for creating version
        ws_info = self.workspace_handler.get_workspace_info()
        current_version = ws_info.get("current_version", "v1")
        available_versions = ws_info.get("available_versions", [])

        # Find new version number
        next_num = 1
        for v in available_versions:
            if v.startswith('v'):
                try:
                    num = int(v[1:])
                    next_num = max(next_num, num + 1)
                except ValueError:
                    pass

        new_version = f"v{next_num}"
        
        description, ok = QtWidgets.QInputDialog.getText(
            self, "New Version",
            f"Create new version: {new_version}\n\n"
            f"Will be based on: {current_version}\n\n"
            "Description:",
            QtWidgets.QLineEdit.Normal,
            f"Version {next_num}"
        )
        
        if ok:
            success = self.workspace_handler.create_new_version(
                new_version,
                description=description
            )
            
            if success:
                self._update_workspace_ui()
                QtWidgets.QMessageBox.information(
                    self, "Success",
                    f"Created version: {new_version}\n\n"
                    f"You are now working on {new_version}"
                )
    
    def switch_version(self):
        """Switch version"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return

        ws_info = self.workspace_handler.get_workspace_info()
        available_versions = ws_info.get("available_versions", [])
        current_version = ws_info.get("current_version", "")

        if not available_versions:
            return

        version, ok = QtWidgets.QInputDialog.getItem(
            self, "Switch Version",
            "Select version:",
            available_versions,
            available_versions.index(current_version) if current_version in available_versions else 0,
            False
        )

        if ok and version and version != current_version:
            success = self.workspace_handler.switch_version(version)

            if success:
                # Reload entire UI with clean state and display first image
                self._reload_workspace_ui()

                QtWidgets.QMessageBox.information(
                    self, "Success",
                    f"Switched to version: {version}"
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error",
                    f"Failed to switch to version: {version}"
                )

    def manage_versions(self):
        """Manage all versions"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return

        from modules.gui.dialogs.version_manager_dialog import VersionManagerDialog

        dialog = VersionManagerDialog(self.workspace_handler, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Refresh UI after version changes
            self._reload_workspace_ui()

    def next_version(self):
        """Switch to next version (Ctrl+Tab)"""
        if not self.workspace_handler.current_workspace_id:
            return

        ws_info = self.workspace_handler.get_workspace_info()
        available_versions = ws_info.get("available_versions", [])
        current_version = ws_info.get("current_version", "")

        if len(available_versions) <= 1:
            self.statusBar().showMessage("No other versions available", 2000)
            return

        # Sort versions
        available_versions.sort()

        # Find current index
        try:
            current_index = available_versions.index(current_version)
        except ValueError:
            return

        # Get next version (wrap around)
        next_index = (current_index + 1) % len(available_versions)
        next_ver = available_versions[next_index]

        # Switch to next version
        self._switch_to_version_quick(next_ver)

    def previous_version(self):
        """Switch to previous version (Ctrl+Shift+Tab)"""
        if not self.workspace_handler.current_workspace_id:
            return

        ws_info = self.workspace_handler.get_workspace_info()
        available_versions = ws_info.get("available_versions", [])
        current_version = ws_info.get("current_version", "")

        if len(available_versions) <= 1:
            self.statusBar().showMessage("No other versions available", 2000)
            return

        # Sort versions
        available_versions.sort()

        # Find current index
        try:
            current_index = available_versions.index(current_version)
        except ValueError:
            return

        # Get previous version (wrap around)
        prev_index = (current_index - 1) % len(available_versions)
        prev_ver = available_versions[prev_index]

        # Switch to previous version
        self._switch_to_version_quick(prev_ver)

    def _switch_to_version_quick(self, version: str):
        """Quick version switch without confirmation dialog"""
        success = self.workspace_handler.switch_version(version)

        if success:
            # Reload entire UI with clean state and display first image
            self._reload_workspace_ui()

            # Show notification
            self.statusBar().showMessage(f"Switched to version: {version}", 3000)
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error",
                f"Failed to switch to version: {version}"
            )

    def rename_current_workspace(self):
        """Rename current workspace"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return

        ws_info = self.workspace_handler.get_workspace_info()
        old_name = ws_info.get('name', '')

        # Show dialog to enter new name
        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename Workspace",
            "Enter new workspace name:",
            QtWidgets.QLineEdit.Normal,
            old_name
        )

        if ok and new_name.strip():
            success, message = self.workspace_handler.rename_workspace(new_name.strip())

            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", message
                )
                # Update UI
                self._update_workspace_ui()
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", message
                )

    def open_settings(self):
        """Open Settings Dialog"""
        from modules.gui.dialogs.settings_dialog import SettingsDialog
        from modules.config_loader import get_loader

        dialog = SettingsDialog(get_loader(), self)

        # Connect signal for reload detector
        dialog.settings_changed.connect(self._reload_detector)

        dialog.exec_()

    def _reload_detector(self):
        """Reload OCR detector after settings change"""
        try:
            logger.info("Reloading OCR detector with new settings...")
            self.detector = TextDetector()  # Create new detector according to config

            QtWidgets.QMessageBox.information(
                self,
                "Settings Applied",
                "Settings have been saved successfully.\nOCR detector has been reloaded."
            )

            logger.info("OCR detector reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload detector: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to reload OCR detector:\n{str(e)}"
            )

    def open_paddleocr_settings(self):
        """Open PaddleOCR Advanced Settings Dialog"""
        from modules.gui.dialogs.paddleocr_settings_dialog import PaddleOCRSettingsDialog

        dialog = PaddleOCRSettingsDialog(self)

        # Connect signal for reload detector
        dialog.settings_changed.connect(self._on_paddleocr_settings_changed)

        dialog.exec_()

    def show_help(self):
        """Show help dialog with keyboard shortcuts"""
        from modules.gui.dialogs.help_dialog import HelpDialog

        dialog = HelpDialog(self)
        dialog.exec_()

    def show_about(self):
        """Show about dialog"""
        from modules.__version__ import __version__

        about_text = f"""
        <h2>OCR Tools Studio</h2>
        <p>Version: {__version__}</p>
        <p>A professional annotation tool for OCR dataset creation.</p>
        <br>
        <p><b>Features:</b></p>
        <ul>
            <li>Text detection and recognition annotation</li>
            <li>PaddleOCR integration for auto-detection</li>
            <li>Data masking for sensitive information</li>
            <li>Export to PaddleOCR training format</li>
            <li>Workspace and version management</li>
        </ul>
        <br>
        <p>Press <b>F1</b> for keyboard shortcuts.</p>
        """

        QtWidgets.QMessageBox.about(self, "About OCR Tools Studio", about_text)

    def _on_paddleocr_settings_changed(self):
        """Handle PaddleOCR settings change"""
        # Show confirmation dialog
        reply = QtWidgets.QMessageBox.question(
            self,
            "Reload OCR Detector",
            "PaddleOCR settings have been changed.\n"
            "Do you want to reload the OCR detector now?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                logger.info("Reloading OCR detector with new PaddleOCR settings...")
                self.detector = TextDetector()  # Create new detector

                QtWidgets.QMessageBox.information(
                    self,
                    "Detector Reloaded",
                    "OCR detector has been reloaded with new settings."
                )

                logger.info("OCR detector reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to reload detector: {e}", exc_info=True)
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to reload OCR detector:\n{str(e)}"
                )

    # ===== Delegated Methods =====

    # Workspace Handler
    def _save_cache(self):
        """Save workspace (cache style)"""
        self.workspace_handler.save_workspace()

    def save_annotations_explicitly(self):
        """
        Explicitly save annotations with visual feedback
        Triggered by Save button or Ctrl+S
        """
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self,
                "No Workspace",
                "No workspace is currently loaded."
            )
            return

        # Visual feedback: change button
        if hasattr(self, 'save_btn'):
            original_text = self.save_btn.text()
            self.save_btn.setText("Saving...")
            self.save_btn.setEnabled(False)
            QtWidgets.QApplication.processEvents()

        try:
            success = self.workspace_handler.save_workspace()

            if success:
                self.workspace_handler.is_saved = True
                self._update_status_bar()

                # Clear modified images set and refresh all items
                self.modified_images.clear()
                if hasattr(self, 'image_handler'):
                    self.image_handler.refresh_all_items_appearance()

                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage("Annotations saved successfully", 3000)

                # Reset button with checkmark
                if hasattr(self, 'save_btn'):
                    self.save_btn.setText("Saved")
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(2000, lambda: self._reset_save_button(original_text))

                logger.info("Annotations saved")
            else:
                QtWidgets.QMessageBox.critical(self, "Error", "Failed to save annotations")
                if hasattr(self, 'save_btn'):
                    self.save_btn.setText(original_text)
                    self.save_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"Save error: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Save error:\n{str(e)}")
            if hasattr(self, 'save_btn'):
                self.save_btn.setText(original_text)
                self.save_btn.setEnabled(True)

    def _reset_save_button(self, original_text="💾 Save"):
        """Reset save button"""
        if hasattr(self, 'save_btn'):
            self.save_btn.setText(original_text)
            self.save_btn.setEnabled(True)

    def mark_as_modified(self):
        """Mark workspace as modified and track current image"""
        # Mark workspace as unsaved
        if hasattr(self.workspace_handler, 'is_saved'):
            self.workspace_handler.is_saved = False
            self._update_status_bar()

        # Track current image as modified
        if self.img_key:
            self.modified_images.add(self.img_key)

            # Update list item appearance to show modified status
            if hasattr(self, 'image_handler'):
                from PyQt5.QtCore import Qt
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    item_key = item.data(Qt.UserRole)
                    if item_key == self.img_key:
                        self.image_handler.update_item_appearance(item, self.img_key)
                        break

    def _auto_save(self):
        """Auto-save annotations periodically"""
        if not self.workspace_handler.current_workspace_id:
            return

        # Only save if there are unsaved changes
        if hasattr(self.workspace_handler, 'is_saved') and self.workspace_handler.is_saved:
            return

        try:
            success = self.workspace_handler.save_workspace()
            if success:
                self.workspace_handler.is_saved = True

                # Clear modified images set and refresh all items
                self.modified_images.clear()
                if hasattr(self, 'image_handler'):
                    self.image_handler.refresh_all_items_appearance()
                self._update_status_bar()

                # Show subtle notification
                if hasattr(self, 'statusBar'):
                    from datetime import datetime
                    time_str = datetime.now().strftime('%H:%M:%S')
                    self.statusBar().showMessage(f"Auto-saved at {time_str}", 2000)

                logger.info("Auto-save completed")
        except Exception as e:
            logger.error(f"Auto-save failed: {e}")

    # Image Handler
    def open_folder(self, *args):
        """Open image folder"""
        self.image_handler.open_folder()

    def on_image_selected(self, item):
        """When selecting image from list"""
        self.image_handler.on_image_selected(item)

    def check_only_annotated(self):
        """Check only images with annotations"""
        self.image_handler.check_only_annotated()

    def uncheck_unannotated(self):
        """Uncheck images without annotations"""
        self.image_handler.uncheck_unannotated()

    def select_all_images(self):
        """Select all images (Select All)"""
        self.image_handler.select_all_images()

    def deselect_all_images(self):
        """Deselect all images (Deselect All)"""
        self.image_handler.deselect_all_images()

    def _is_item_checked(self, key):
        """Check if image is checked"""
        return self.image_handler.is_item_checked(key)

    # ===== Search & Filter =====

    def on_search_text_changed(self, text):
        """Handle search text change"""
        self.search_text = text.lower().strip()
        self._apply_search_filter()

    def apply_filter(self, filter_type):
        """Apply filter to image list"""
        self.current_filter = filter_type

        # Update button states
        if hasattr(self, 'filter_all_btn'):
            self.filter_all_btn.setChecked(filter_type == "all")
        if hasattr(self, 'filter_annotated_btn'):
            self.filter_annotated_btn.setChecked(filter_type == "annotated")
        if hasattr(self, 'filter_empty_btn'):
            self.filter_empty_btn.setChecked(filter_type == "empty")

        self._apply_search_filter()

    def _apply_search_filter(self):
        """Apply both search and filter to the image list"""
        visible_count = 0
        total_count = self.list_widget.count()

        for i in range(total_count):
            item = self.list_widget.item(i)
            key = item.data(Qt.UserRole)

            # Apply filter
            has_annotations = bool(self.annotations.get(key, []))

            filter_pass = True
            if self.current_filter == "annotated":
                filter_pass = has_annotations
            elif self.current_filter == "empty":
                filter_pass = not has_annotations

            # Apply search
            search_pass = True
            if self.search_text:
                # Search in image name
                if self.search_text in key.lower():
                    search_pass = True
                else:
                    # Search in annotations
                    anns = self.annotations.get(key, [])
                    search_pass = any(
                        self.search_text in ann.get('transcription', '').lower()
                        for ann in anns
                    )

            # Show/hide item
            should_show = filter_pass and search_pass
            item.setHidden(not should_show)

            if should_show:
                visible_count += 1

        # Update result label
        if hasattr(self, 'search_result_label'):
            if self.search_text or self.current_filter != "all":
                self.search_result_label.setText(f"{visible_count}/{total_count}")
            else:
                self.search_result_label.setText("")

    # Annotation Handler
    def delete_selected(self, *args):
        """Delete selected annotation"""
        self.annotation_handler.delete_selected()

    # ===== Undo/Redo Actions =====

    def undo_action(self):
        """Undo the last action"""
        if self.undo_manager.undo():
            self.statusBar().showMessage("Undo successful", 2000)
            logger.info(f"Undo performed, {self.undo_manager.get_undo_count()} actions remaining")
        else:
            self.statusBar().showMessage("Nothing to undo", 2000)

    def redo_action(self):
        """Redo the last undone action"""
        if self.undo_manager.redo():
            self.statusBar().showMessage("Redo successful", 2000)
            logger.info(f"Redo performed, {self.undo_manager.get_redo_count()} actions remaining")
        else:
            self.statusBar().showMessage("Nothing to redo", 2000)

    # Detection Handler
    def auto_label_current(self, *args):
        """Auto-detect current image"""
        self.detection_handler.auto_label_current()

    def auto_label_all(self, *args):
        """Auto-detect all images"""
        self.detection_handler.auto_label_all()

    def auto_label_selected(self, *args):
        """Auto-detect only selected images"""
        self.detection_handler.auto_label_selected()

    # UI Handler
    def toggle_draw_mode(self, checked):
        """Toggle box drawing mode"""
        self.draw_mode = checked

        # Close mask_mode if opening draw_mode
        if checked and self.mask_mode:
            self.mask_mode = False
            if hasattr(self, 'mask_action'):
                self.mask_action.setChecked(False)

        # Update mode combo
        if hasattr(self, 'mode_combo'):
            self.mode_combo.setCurrentText("Annotation")

        self.ui_handler.toggle_draw_mode(checked)
        self._update_status_bar()

    def toggle_recog_mode(self, checked):
        """Toggle Recognition mode"""
        self.ui_handler.toggle_recog_mode(checked)
        self._update_status_bar()

    def on_annotation_type_changed(self, new_type):
        """Change annotation type"""
        self.ui_handler.on_annotation_type_changed(new_type)

    def update_annotation_info(self):
        """Update annotation information"""
        self.ui_handler.update_annotation_info()

    def add_box_from_rect(self, rect):
        """Add Quad box from rectangle"""
        self.ui_handler.add_box_from_rect(rect)

    def add_polygon_from_points(self, points):
        """Add polygon from points"""
        self.ui_handler.add_polygon_from_points(points)

    # Table Handler
    def on_table_item_changed(self, item):
        """When editing data in table (deprecated - handler manages itself)"""
        pass

    def on_table_selection_changed(self):
        """When selecting row in table (deprecated - handler manages itself)"""
        pass

    # Export Handler
    def save_labels(self, *args):
        """Export Detection Dataset"""
        self.export_handler.save_labels_detection()

    def export_rec(self, *args):
        """Export Recognition Dataset"""
        self.export_handler.export_recognition()

    # Rotation Handler
    def rotate_image(self, angle):
        """Rotate current image"""
        if hasattr(self, 'rotation_handler'):
            self.rotation_handler.rotate_current_image(angle)

    def reset_rotation(self):
        """Reset rotation of current image"""
        if hasattr(self, 'rotation_handler'):
            self.rotation_handler.reset_rotation()
    
    # ===== 🔒 Mask Handler Methods (NEW!) =====

    def toggle_mask_mode(self, checked):
        """Toggle Masking mode"""
        self.mask_mode = checked

        # Close draw_mode if opening mask_mode
        if checked and self.draw_mode:
            self.draw_mode = False
            if hasattr(self, 'draw_action'):
                self.draw_action.setChecked(False)

        # Show/hide color selection button
        if hasattr(self, 'mask_color_btn'):
            self.mask_color_btn.setVisible(checked)
            # Update button showing current color
            if checked:
                self.mask_handler._update_color_button()

        # Update mode combo
        if hasattr(self, 'mode_combo'):
            if checked:
                self.mode_combo.setCurrentText("Masking")
            else:
                self.mode_combo.setCurrentText("Annotation")

        self._update_status_bar()
        logger.info(f"Mask mode: {'ON' if checked else 'OFF'}")

    def on_mode_changed(self, mode_text):
        """When changing mode from combo box"""
        if mode_text == "Masking":
            # Open mask mode
            if hasattr(self, 'mask_action'):
                self.mask_action.setChecked(True)
            self.mask_mode = True
            self.draw_mode = False
            if hasattr(self, 'draw_action'):
                self.draw_action.setChecked(False)
            # Show color selection button
            if hasattr(self, 'mask_color_btn'):
                self.mask_color_btn.setVisible(True)
                self.mask_handler._update_color_button()
        else:  # Annotation
            # Close mask mode
            if hasattr(self, 'mask_action'):
                self.mask_action.setChecked(False)
            self.mask_mode = False
            # Hide color selection button
            if hasattr(self, 'mask_color_btn'):
                self.mask_color_btn.setVisible(False)

    def add_mask_from_rect(self, rect):
        """Add Quad Mask from rectangle"""
        self.mask_handler.add_mask_from_rect(rect)

    def add_mask_from_points(self, points):
        """Add Polygon Mask from points"""
        self.mask_handler.add_mask_from_points(points)

    def choose_mask_color(self):
        """Open color picker to select mask color"""
        self.mask_handler.choose_mask_color()

    def change_selected_mask_color(self):
        """Change color of selected mask"""
        self.mask_handler.change_selected_mask_color()

    def set_mask_color_preset(self, preset_name):
        """Set color from preset"""
        self.mask_handler.set_mask_color_preset(preset_name)

    # ===== Clipboard Methods =====

    def copy_annotations(self):
        """Copy selected annotations"""
        self.clipboard_handler.copy_selected()

    def paste_annotations(self):
        """Paste annotations from clipboard"""
        self.clipboard_handler.paste()

    def cut_annotations(self):
        """Cut selected annotations"""
        self.clipboard_handler.cut_selected()

    # ===== Navigation Methods =====

    def navigate_next_image(self):
        """Navigate to next image in list"""
        if not self.list_widget.count():
            return

        current_row = self.list_widget.currentRow()

        # Find next visible item
        for i in range(current_row + 1, self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.list_widget.setCurrentItem(item)
                self.on_image_selected(item)
                return

        # Wrap around to beginning
        for i in range(0, current_row):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.list_widget.setCurrentItem(item)
                self.on_image_selected(item)
                return

    def navigate_prev_image(self):
        """Navigate to previous image in list"""
        if not self.list_widget.count():
            return

        current_row = self.list_widget.currentRow()

        # Find previous visible item
        for i in range(current_row - 1, -1, -1):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.list_widget.setCurrentItem(item)
                self.on_image_selected(item)
                return

        # Wrap around to end
        for i in range(self.list_widget.count() - 1, current_row, -1):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.list_widget.setCurrentItem(item)
                self.on_image_selected(item)
                return

    def select_all_annotations(self):
        """Select all annotations on current image"""
        for item in self.box_items:
            item.setSelected(True)
        self.statusBar().showMessage(f"Selected {len(self.box_items)} annotations", 2000)

    def deselect_all_annotations(self):
        """Deselect all annotations"""
        for item in self.box_items:
            item.setSelected(False)

    # ===== Zoom Methods =====

    def zoom_in(self):
        """Zoom in canvas"""
        self.view.scale(1.25, 1.25)
        self.view._zoom *= 1.25
        self._update_zoom_label()

    def zoom_out(self):
        """Zoom out canvas"""
        self.view.scale(0.8, 0.8)
        self.view._zoom *= 0.8
        self._update_zoom_label()

    def zoom_fit(self):
        """Fit image to view"""
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.view._zoom = 1.0
        self._update_zoom_label()

    def zoom_reset(self):
        """Reset zoom to 100%"""
        current_zoom = self.view._zoom
        if current_zoom != 0:
            factor = 1.0 / current_zoom
            self.view.scale(factor, factor)
            self.view._zoom = 1.0
        self._update_zoom_label()

    # ===== Event Handlers =====

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        key = event.key()
        modifiers = event.modifiers()

        # Ctrl+C: Copy
        if key == Qt.Key_C and modifiers == Qt.ControlModifier:
            self.copy_annotations()
            return

        # Ctrl+V: Paste
        if key == Qt.Key_V and modifiers == Qt.ControlModifier:
            self.paste_annotations()
            return

        # Ctrl+X: Cut
        if key == Qt.Key_X and modifiers == Qt.ControlModifier:
            self.cut_annotations()
            return

        # Page Down / Down Arrow: Next image
        if key in (Qt.Key_PageDown, Qt.Key_Down) and modifiers == Qt.NoModifier:
            self.navigate_next_image()
            return

        # Page Up / Up Arrow: Previous image
        if key in (Qt.Key_PageUp, Qt.Key_Up) and modifiers == Qt.NoModifier:
            self.navigate_prev_image()
            return

        # Delete / Backspace: Delete selected
        if key in (Qt.Key_Delete, Qt.Key_Backspace) and modifiers == Qt.NoModifier:
            self.delete_selected()
            return

        # Escape: Deselect all / Cancel operation
        if key == Qt.Key_Escape:
            self.deselect_all_annotations()
            # Also cancel polygon drawing if active
            if hasattr(self.view, 'polygon_points') and self.view.polygon_points:
                self.view._cancel_polygon()
            return

        # Ctrl+A: Select all annotations (not images)
        if key == Qt.Key_A and modifiers == Qt.ControlModifier:
            self.select_all_annotations()
            return

        # +/=: Zoom in
        if key in (Qt.Key_Plus, Qt.Key_Equal) and modifiers == Qt.NoModifier:
            self.zoom_in()
            return

        # -: Zoom out
        if key == Qt.Key_Minus and modifiers == Qt.NoModifier:
            self.zoom_out()
            return

        # 0: Fit to view
        if key == Qt.Key_0 and modifiers == Qt.NoModifier:
            self.zoom_fit()
            return

        # 1: Reset zoom to 100%
        if key == Qt.Key_1 and modifiers == Qt.NoModifier:
            self.zoom_reset()
            return

        # F: Fit to view (alternative)
        if key == Qt.Key_F and modifiers == Qt.NoModifier:
            self.zoom_fit()
            return

        # Space: Toggle draw mode
        if key == Qt.Key_Space and modifiers == Qt.NoModifier:
            if hasattr(self, 'draw_action'):
                self.draw_action.toggle()
                self.toggle_draw_mode(self.draw_action.isChecked())
            return

        # Tab: Select next annotation
        if key == Qt.Key_Tab and modifiers == Qt.NoModifier:
            self._select_next_annotation()
            return

        # Shift+Tab: Select previous annotation
        if key == Qt.Key_Backtab or (key == Qt.Key_Tab and modifiers == Qt.ShiftModifier):
            self._select_prev_annotation()
            return

        super().keyPressEvent(event)

    def _select_next_annotation(self):
        """Select next annotation in the list"""
        if not self.box_items:
            return

        selected = self.scene.selectedItems()
        current_idx = -1

        if selected:
            for i, item in enumerate(self.box_items):
                if item in selected:
                    current_idx = i
                    break

        # Deselect all
        for item in self.box_items:
            item.setSelected(False)

        # Select next
        next_idx = (current_idx + 1) % len(self.box_items)
        self.box_items[next_idx].setSelected(True)

        # Center view on selected item
        self.view.centerOn(self.box_items[next_idx])

    def _select_prev_annotation(self):
        """Select previous annotation in the list"""
        if not self.box_items:
            return

        selected = self.scene.selectedItems()
        current_idx = 0

        if selected:
            for i, item in enumerate(self.box_items):
                if item in selected:
                    current_idx = i
                    break

        # Deselect all
        for item in self.box_items:
            item.setSelected(False)

        # Select previous
        prev_idx = (current_idx - 1) % len(self.box_items)
        self.box_items[prev_idx].setSelected(True)

        # Center view on selected item
        self.view.centerOn(self.box_items[prev_idx])

    def closeEvent(self, event):
        """When closing program"""
        QtWidgets.QApplication.processEvents()

        # Save workspace
        if self.workspace_handler.current_workspace_id:
            self.workspace_handler.save_workspace()

        super().closeEvent(event)
        logger.info("Application closed")