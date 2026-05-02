# modules/gui/ui_coordinator.py
"""
UICoordinator — Subscribes to AppState signals and keeps Qt widgets in sync
with application state.  Also owns the larger UI-logic methods that were
previously on MainWindow, keeping MainWindow itself lean.
"""

import logging
from datetime import datetime

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QTimer

logger = logging.getLogger("TextDetGUI")


class UICoordinator:
    """
    Subscribes to AppState signals and keeps Qt widgets in sync with
    application state.  Also holds the larger UI-logic methods that were
    previously on MainWindow.

    All methods use ``self.mw`` to access MainWindow attributes (widgets,
    handlers, state, etc.) so that MainWindow itself only needs a thin
    set of 1-line delegates.
    """

    def __init__(self, main_window) -> None:
        self.mw = main_window
        self._connect_signals()

    # ------------------------------------------------------------------ signals

    def _connect_signals(self):
        """Connect AppState signals to update methods.

        Only signals whose argument signature matches the slot are connected
        here.  ``on_mode_changed(mode_text)`` is invoked directly by the mode
        combo box (which passes the new text) — it is *not* wired to the
        argument-less ``state.mode_changed`` signal.
        """
        state = self.mw._state
        # mode_changed (no args) → refresh status bar to reflect new mode
        state.mode_changed.connect(self._update_status_bar)
        # filter_changed / images_loaded (no args) → re-apply search filter
        state.filter_changed.connect(self._apply_search_filter)
        state.images_loaded.connect(self._apply_search_filter)
        # annotations_changed(str) → refresh status bar (slot ignores the arg)
        state.annotations_changed.connect(lambda _key: self._update_status_bar())

    # ================================================================ workspace UI

    def _update_workspace_ui(self):
        """Update UI after loading workspace."""
        mw = self.mw
        ws_info = mw.workspace_handler.get_workspace_info()

        if ws_info:
            title = f"TextDet GUI - {ws_info['name']} ({ws_info['current_version']})"
            mw.setWindowTitle(title)

            if hasattr(mw, 'workspace_label'):
                mw.workspace_label.setText(
                    f"  \U0001f4c1 {ws_info['name']} ({ws_info['current_version']})"
                )

            self._update_recent_workspaces_menu()
            self._update_status_bar()

            if hasattr(mw, 'image_handler') and ws_info.get('source_folder'):
                source_folder = ws_info['source_folder']
                mw.image_handler.load_images_from_folder(source_folder)
                image_count = mw.list_widget.count() if hasattr(mw, 'list_widget') else 0
                logger.info(f"Auto-loaded {image_count} images from: {source_folder}")

            logger.info(f"Workspace loaded: {ws_info['name']}")

    def _update_recent_workspaces_menu(self):
        """Update recent workspaces menu with latest data."""
        mw = self.mw
        if not hasattr(mw, 'recent_workspaces_menu'):
            return

        mw.recent_workspaces_menu.clear()
        recent = mw.workspace_manager.get_recent_workspaces()

        if not recent:
            action = QtWidgets.QAction("(No recent workspaces)", mw)
            action.setEnabled(False)
            mw.recent_workspaces_menu.addAction(action)
            return

        current_ws = mw.workspace_handler.current_workspace_id

        for ws_data in recent[:6]:
            ws_id   = ws_data.get('id')
            ws_name = ws_data.get('name', ws_id)
            last_opened = ws_data.get('last_opened', '')

            try:
                dt = datetime.fromisoformat(last_opened)
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception as e:
                logger.debug(f"Failed to parse date '{last_opened}': {e}")
                time_str = 'Unknown'

            if ws_id == current_ws:
                action = QtWidgets.QAction(f"✓ {ws_name}  ({time_str})", mw)
                action.setEnabled(False)
            else:
                action = QtWidgets.QAction(f"  {ws_name}  ({time_str})", mw)
                action.triggered.connect(lambda checked, wid=ws_id: self._switch_to_workspace(wid))

            mw.recent_workspaces_menu.addAction(action)

        if recent:
            mw.recent_workspaces_menu.addSeparator()
            action = QtWidgets.QAction("More Workspaces...", mw)
            action.triggered.connect(mw.switch_workspace)
            mw.recent_workspaces_menu.addAction(action)

    def _switch_to_workspace(self, workspace_id):
        """Switch to a specific workspace by ID."""
        mw = self.mw
        if workspace_id == mw.workspace_handler.current_workspace_id:
            return

        if mw.workspace_handler.current_workspace_id:
            mw.workspace_handler.save_workspace()

        success = mw.workspace_handler.load_workspace(workspace_id)

        if success:
            self._reload_workspace_ui()
        else:
            QtWidgets.QMessageBox.critical(
                mw, "Error", f"Failed to load workspace: {workspace_id}"
            )

    def _update_status_bar(self):
        """Update status bar with workspace statistics."""
        mw = self.mw
        if not hasattr(mw, 'statusBar'):
            return

        ws_info = mw.workspace_handler.get_workspace_info()

        if hasattr(mw, 'progress_label'):
            annotated_count = sum(1 for anns in mw.annotations.values() if anns)
            total_count = len(mw.image_items)
            mw.progress_label.setText(f"{annotated_count}/{total_count} labeled")

        if hasattr(mw, 'annotation_count_label'):
            count = len(mw.box_items)
            mw.annotation_count_label.setText(
                f"{count} annotation{'s' if count != 1 else ''}"
            )

        if hasattr(mw, 'mode_status_label'):
            if mw.draw_mode:
                mw.mode_status_label.setText("Draw")
                mw.mode_status_label.setStyleSheet(
                    "color: #2196F3; padding: 0 8px; font-weight: bold;"
                )
            elif mw.mask_mode:
                mw.mode_status_label.setText("Mask")
                mw.mode_status_label.setStyleSheet(
                    "color: #F44336; padding: 0 8px; font-weight: bold;"
                )
            elif mw.recog_mode:
                mw.mode_status_label.setText("Edit")
                mw.mode_status_label.setStyleSheet(
                    "color: #4CAF50; padding: 0 8px; font-weight: bold;"
                )
            else:
                mw.mode_status_label.setText("View")
                mw.mode_status_label.setStyleSheet("color: #616161; padding: 0 8px;")

        if not ws_info:
            mw.statusBar().showMessage("Ready")
            return

        if hasattr(mw.workspace_handler, 'is_saved') and not mw.workspace_handler.is_saved:
            mw.statusBar().showMessage(
                f"● {ws_info['name']} - {ws_info['current_version']} - Unsaved changes"
            )
        else:
            mw.statusBar().showMessage(
                f"{ws_info['name']} - {ws_info['current_version']}"
            )

    def _update_zoom_label(self):
        """Update zoom level in status bar."""
        mw = self.mw
        if hasattr(mw, 'zoom_label'):
            zoom_percent = int(mw.view._zoom * 100)
            mw.zoom_label.setText(f"{zoom_percent}%")

    def _reload_workspace_ui(self):
        """Reload entire UI after version/workspace switch — ensures clean state."""
        mw = self.mw
        try:
            mw.scene.clear()
            mw.box_items.clear()
            mw.modified_images.clear()
            mw.list_widget.clear()
            mw.img_key = None

            mw.undo_manager.clear()

            if hasattr(mw, 'pixmap_item'):
                mw.pixmap_item = None

            self._update_workspace_ui()

            if mw.list_widget.count() > 0:
                mw.list_widget.setCurrentRow(0)
                if hasattr(mw, 'image_handler'):
                    first_item = mw.list_widget.item(0)
                    if first_item:
                        mw.image_handler.on_image_selected(first_item)
                logger.info("Displayed first image after reload")

            logger.info("UI reloaded successfully after version switch")

        except Exception as e:
            logger.error(f"Error reloading UI after version switch: {e}", exc_info=True)
            QtWidgets.QMessageBox.critical(
                mw, "Error",
                f"Failed to reload UI after version switch:\n{str(e)}"
            )

    # ================================================================ version management

    def create_new_version(self):
        """Create a new version of the current workspace."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(mw, "Warning", "No workspace loaded")
            return

        ws_info = mw.workspace_handler.get_workspace_info()
        current_version    = ws_info.get("current_version", "v1")
        available_versions = ws_info.get("available_versions", [])

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
            mw, "New Version",
            f"Create new version: {new_version}\n\n"
            f"Will be based on: {current_version}\n\n"
            "Description:",
            QtWidgets.QLineEdit.Normal,
            f"Version {next_num}"
        )

        if ok:
            success = mw.workspace_handler.create_new_version(
                new_version, description=description
            )
            if success:
                self._update_workspace_ui()
                QtWidgets.QMessageBox.information(
                    mw, "Success",
                    f"Created version: {new_version}\n\nYou are now working on {new_version}"
                )

    def switch_version(self):
        """Switch to a different version via dialog."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(mw, "Warning", "No workspace loaded")
            return

        ws_info = mw.workspace_handler.get_workspace_info()
        available_versions = ws_info.get("available_versions", [])
        current_version    = ws_info.get("current_version", "")

        if not available_versions:
            return

        version, ok = QtWidgets.QInputDialog.getItem(
            mw, "Switch Version", "Select version:",
            available_versions,
            available_versions.index(current_version)
            if current_version in available_versions else 0,
            False
        )

        if ok and version and version != current_version:
            success = mw.workspace_handler.switch_version(version)
            if success:
                self._reload_workspace_ui()
                QtWidgets.QMessageBox.information(
                    mw, "Success", f"Switched to version: {version}"
                )
            else:
                QtWidgets.QMessageBox.critical(
                    mw, "Error", f"Failed to switch to version: {version}"
                )

    def manage_versions(self):
        """Open the Version Manager dialog."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(mw, "Warning", "No workspace loaded")
            return

        from modules.gui.dialogs.version_manager_dialog import VersionManagerDialog
        dialog = VersionManagerDialog(mw.workspace_handler, mw)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self._reload_workspace_ui()

    def next_version(self):
        """Switch to the next version (Ctrl+Tab)."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            return

        ws_info = mw.workspace_handler.get_workspace_info()
        available_versions = sorted(ws_info.get("available_versions", []))
        current_version    = ws_info.get("current_version", "")

        if len(available_versions) <= 1:
            mw.statusBar().showMessage("No other versions available", 2000)
            return

        try:
            current_index = available_versions.index(current_version)
        except ValueError:
            return

        next_ver = available_versions[(current_index + 1) % len(available_versions)]
        self._switch_to_version_quick(next_ver)

    def previous_version(self):
        """Switch to the previous version (Ctrl+Shift+Tab)."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            return

        ws_info = mw.workspace_handler.get_workspace_info()
        available_versions = sorted(ws_info.get("available_versions", []))
        current_version    = ws_info.get("current_version", "")

        if len(available_versions) <= 1:
            mw.statusBar().showMessage("No other versions available", 2000)
            return

        try:
            current_index = available_versions.index(current_version)
        except ValueError:
            return

        prev_ver = available_versions[(current_index - 1) % len(available_versions)]
        self._switch_to_version_quick(prev_ver)

    def _switch_to_version_quick(self, version: str):
        """Quick version switch without a confirmation dialog."""
        mw = self.mw
        success = mw.workspace_handler.switch_version(version)
        if success:
            self._reload_workspace_ui()
            mw.statusBar().showMessage(f"Switched to version: {version}", 3000)
        else:
            QtWidgets.QMessageBox.critical(
                mw, "Error", f"Failed to switch to version: {version}"
            )

    def rename_current_workspace(self):
        """Rename the currently loaded workspace."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(mw, "Warning", "No workspace loaded")
            return

        ws_info  = mw.workspace_handler.get_workspace_info()
        old_name = ws_info.get('name', '')

        new_name, ok = QtWidgets.QInputDialog.getText(
            mw, "Rename Workspace", "Enter new workspace name:",
            QtWidgets.QLineEdit.Normal, old_name
        )

        if ok and new_name.strip():
            success, message = mw.workspace_handler.rename_workspace(new_name.strip())
            if success:
                QtWidgets.QMessageBox.information(mw, "Success", message)
                self._update_workspace_ui()
            else:
                QtWidgets.QMessageBox.critical(mw, "Error", message)

    # ================================================================ PaddleOCR settings

    def _on_paddleocr_settings_changed(self):
        """Handle PaddleOCR settings change — prompt to reload detector."""
        mw = self.mw
        from modules.core.ocr import TextDetector

        reply = QtWidgets.QMessageBox.question(
            mw, "Reload OCR Detector",
            "PaddleOCR settings have been changed.\n"
            "Do you want to reload the OCR detector now?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            try:
                logger.info("Reloading OCR detector with new PaddleOCR settings...")
                mw.detector = TextDetector()
                QtWidgets.QMessageBox.information(
                    mw, "Detector Reloaded",
                    "OCR detector has been reloaded with new settings."
                )
                logger.info("OCR detector reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to reload detector: {e}", exc_info=True)
                QtWidgets.QMessageBox.critical(
                    mw, "Error", f"Failed to reload OCR detector:\n{str(e)}"
                )

    # ================================================================ save / auto-save

    def save_annotations_explicitly(self):
        """Explicitly save annotations with visual feedback (Ctrl+S / Save button)."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                mw, "No Workspace", "No workspace is currently loaded."
            )
            return

        original_text = None
        if hasattr(mw, 'save_btn'):
            original_text = mw.save_btn.text()
            mw.save_btn.setText("Saving...")
            mw.save_btn.setEnabled(False)
            QtWidgets.QApplication.processEvents()

        try:
            success = mw.workspace_handler.save_workspace()

            if success:
                mw.workspace_handler.is_saved = True
                self._update_status_bar()

                mw.modified_images.clear()
                if hasattr(mw, 'image_handler'):
                    mw.image_handler.refresh_all_items_appearance()

                if hasattr(mw, 'statusBar'):
                    mw.statusBar().showMessage("Annotations saved successfully", 3000)

                if hasattr(mw, 'save_btn'):
                    mw.save_btn.setText("Saved")
                    QTimer.singleShot(
                        2000,
                        lambda: self._reset_save_button(original_text)
                    )

                logger.info("Annotations saved")
            else:
                QtWidgets.QMessageBox.critical(mw, "Error", "Failed to save annotations")
                if hasattr(mw, 'save_btn') and original_text is not None:
                    mw.save_btn.setText(original_text)
                    mw.save_btn.setEnabled(True)

        except Exception as e:
            logger.error(f"Save error: {e}")
            QtWidgets.QMessageBox.critical(mw, "Error", f"Save error:\n{str(e)}")
            if hasattr(mw, 'save_btn') and original_text is not None:
                mw.save_btn.setText(original_text)
                mw.save_btn.setEnabled(True)

    def _reset_save_button(self, original_text="\U0001f4be Save"):
        """Reset save button to its original label."""
        mw = self.mw
        if hasattr(mw, 'save_btn'):
            mw.save_btn.setText(original_text)
            mw.save_btn.setEnabled(True)

    def mark_as_modified(self):
        """Mark the workspace as modified and track the current image."""
        mw = self.mw
        if hasattr(mw.workspace_handler, 'is_saved'):
            mw.workspace_handler.is_saved = False
            self._update_status_bar()

        if mw.img_key:
            mw.modified_images.add(mw.img_key)

            if hasattr(mw, 'image_handler'):
                for i in range(mw.list_widget.count()):
                    item = mw.list_widget.item(i)
                    item_key = item.data(Qt.UserRole)
                    if item_key == mw.img_key:
                        mw.image_handler.update_item_appearance(item, mw.img_key)
                        break

    def _auto_save(self):
        """Auto-save annotations periodically."""
        mw = self.mw
        if not mw.workspace_handler.current_workspace_id:
            return

        if hasattr(mw.workspace_handler, 'is_saved') and mw.workspace_handler.is_saved:
            return

        try:
            success = mw.workspace_handler.save_workspace()
            if success:
                mw.workspace_handler.is_saved = True
                mw.modified_images.clear()
                if hasattr(mw, 'image_handler'):
                    mw.image_handler.refresh_all_items_appearance()
                self._update_status_bar()

                if hasattr(mw, 'statusBar'):
                    time_str = datetime.now().strftime('%H:%M:%S')
                    mw.statusBar().showMessage(f"Auto-saved at {time_str}", 2000)

                logger.info("Auto-save completed")
        except Exception as e:
            logger.error(f"Auto-save failed: {e}")

    # ================================================================ search / filter

    def on_search_text_changed(self, text):
        """Handle search box text change."""
        self.mw.search_text = text.lower().strip()
        self._apply_search_filter()

    def apply_filter(self, filter_type):
        """Apply a named filter to the image list."""
        mw = self.mw
        mw.current_filter = filter_type

        if hasattr(mw, 'filter_all_btn'):
            mw.filter_all_btn.setChecked(filter_type == "all")
        if hasattr(mw, 'filter_annotated_btn'):
            mw.filter_annotated_btn.setChecked(filter_type == "annotated")
        if hasattr(mw, 'filter_empty_btn'):
            mw.filter_empty_btn.setChecked(filter_type == "empty")

        self._apply_search_filter()

    def _apply_search_filter(self):
        """Apply both search text and filter type to the image list."""
        mw = self.mw
        visible_count = 0
        total_count   = mw.list_widget.count()

        for i in range(total_count):
            item = mw.list_widget.item(i)
            key  = item.data(Qt.UserRole)

            has_annotations = bool(mw.annotations.get(key, []))

            filter_pass = True
            if mw.current_filter == "annotated":
                filter_pass = has_annotations
            elif mw.current_filter == "empty":
                filter_pass = not has_annotations

            search_pass = True
            if mw.search_text:
                if mw.search_text in key.lower():
                    search_pass = True
                else:
                    anns = mw.annotations.get(key, [])
                    search_pass = any(
                        mw.search_text in ann.get('transcription', '').lower()
                        for ann in anns
                    )

            should_show = filter_pass and search_pass
            item.setHidden(not should_show)

            if should_show:
                visible_count += 1

        if hasattr(mw, 'search_result_label'):
            if mw.search_text or mw.current_filter != "all":
                mw.search_result_label.setText(f"{visible_count}/{total_count}")
            else:
                mw.search_result_label.setText("")

    # ================================================================ mode toggles

    def toggle_draw_mode(self, checked):
        """Toggle box-drawing mode."""
        mw = self.mw
        mw.draw_mode = checked

        if checked and mw.mask_mode:
            mw.mask_mode = False
            if hasattr(mw, 'mask_action'):
                mw.mask_action.setChecked(False)

        if hasattr(mw, 'mode_combo'):
            mw.mode_combo.setCurrentText("Annotation")

        mw.ui_handler.toggle_draw_mode(checked)
        self._update_status_bar()

    def toggle_recog_mode(self, checked):
        """Toggle recognition/edit mode."""
        self.mw.ui_handler.toggle_recog_mode(checked)
        self._update_status_bar()

    def toggle_mask_mode(self, checked):
        """Toggle masking mode."""
        mw = self.mw
        mw.mask_mode = checked

        if checked and mw.draw_mode:
            mw.draw_mode = False
            if hasattr(mw, 'draw_action'):
                mw.draw_action.setChecked(False)

        if hasattr(mw, 'mask_color_btn'):
            mw.mask_color_btn.setVisible(checked)
            if checked:
                mw.mask_handler._update_color_button()

        if hasattr(mw, 'mode_combo'):
            mw.mode_combo.setCurrentText("Masking" if checked else "Annotation")

        self._update_status_bar()
        logger.info(f"Mask mode: {'ON' if checked else 'OFF'}")

    def on_mode_changed(self, mode_text):
        """Handle mode combo-box selection change."""
        mw = self.mw
        if mode_text == "Masking":
            if hasattr(mw, 'mask_action'):
                mw.mask_action.setChecked(True)
            mw.mask_mode = True
            mw.draw_mode = False
            if hasattr(mw, 'draw_action'):
                mw.draw_action.setChecked(False)
            if hasattr(mw, 'mask_color_btn'):
                mw.mask_color_btn.setVisible(True)
                mw.mask_handler._update_color_button()
        else:  # Annotation
            if hasattr(mw, 'mask_action'):
                mw.mask_action.setChecked(False)
            mw.mask_mode = False
            if hasattr(mw, 'mask_color_btn'):
                mw.mask_color_btn.setVisible(False)

    # ================================================================ image navigation

    def navigate_next_image(self):
        """Navigate to the next visible image in the list."""
        mw = self.mw
        if not mw.list_widget.count():
            return

        current_row = mw.list_widget.currentRow()

        for i in range(current_row + 1, mw.list_widget.count()):
            item = mw.list_widget.item(i)
            if not item.isHidden():
                mw.list_widget.setCurrentItem(item)
                mw.on_image_selected(item)
                return

        for i in range(0, current_row):
            item = mw.list_widget.item(i)
            if not item.isHidden():
                mw.list_widget.setCurrentItem(item)
                mw.on_image_selected(item)
                return

    def navigate_prev_image(self):
        """Navigate to the previous visible image in the list."""
        mw = self.mw
        if not mw.list_widget.count():
            return

        current_row = mw.list_widget.currentRow()

        for i in range(current_row - 1, -1, -1):
            item = mw.list_widget.item(i)
            if not item.isHidden():
                mw.list_widget.setCurrentItem(item)
                mw.on_image_selected(item)
                return

        for i in range(mw.list_widget.count() - 1, current_row, -1):
            item = mw.list_widget.item(i)
            if not item.isHidden():
                mw.list_widget.setCurrentItem(item)
                mw.on_image_selected(item)
                return

    # ================================================================ annotation selection

    def _select_next_annotation(self):
        """Select the next annotation in box_items (Tab key)."""
        mw = self.mw
        if not mw.box_items:
            return

        selected = mw.scene.selectedItems()
        current_idx = -1

        if selected:
            for i, item in enumerate(mw.box_items):
                if item in selected:
                    current_idx = i
                    break

        for item in mw.box_items:
            item.setSelected(False)

        next_idx = (current_idx + 1) % len(mw.box_items)
        mw.box_items[next_idx].setSelected(True)
        mw.view.centerOn(mw.box_items[next_idx])

    def _select_prev_annotation(self):
        """Select the previous annotation in box_items (Shift+Tab)."""
        mw = self.mw
        if not mw.box_items:
            return

        selected = mw.scene.selectedItems()
        current_idx = 0

        if selected:
            for i, item in enumerate(mw.box_items):
                if item in selected:
                    current_idx = i
                    break

        for item in mw.box_items:
            item.setSelected(False)

        prev_idx = (current_idx - 1) % len(mw.box_items)
        mw.box_items[prev_idx].setSelected(True)
        mw.view.centerOn(mw.box_items[prev_idx])
