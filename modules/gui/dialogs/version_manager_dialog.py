# modules/gui/version_manager_dialog.py

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from datetime import datetime


class VersionManagerDialog(QtWidgets.QDialog):
    """
    Dialog for managing all Versions
    """

    def __init__(self, workspace_handler, parent=None):
        super().__init__(parent)
        self.workspace_handler = workspace_handler
        self.current_workspace_id = workspace_handler.current_workspace_id

        self.setWindowTitle("Manage Versions")
        self.resize(700, 500)

        self._init_ui()
        self._load_versions()

    def _init_ui(self):
        """Create UI"""
        layout = QtWidgets.QVBoxLayout(self)

        # ===== Title =====
        ws_info = self.workspace_handler.get_workspace_info()
        title = QtWidgets.QLabel(f"Manage Versions - {ws_info.get('name', 'Unknown')}")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # ===== Version List =====
        self.version_table = QtWidgets.QTableWidget()
        self.version_table.setColumnCount(6)
        self.version_table.setHorizontalHeaderLabels([
            'Version', 'Description', 'Created', 'Modified', 'Annotations', 'Status'
        ])
        self.version_table.horizontalHeader().setStretchLastSection(True)
        self.version_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.version_table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.version_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.version_table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.version_table)

        # ===== Info Panel =====
        info_group = QtWidgets.QGroupBox("Version Details")
        info_layout = QtWidgets.QFormLayout()

        self.info_version = QtWidgets.QLabel("-")
        self.info_description = QtWidgets.QLabel("-")
        self.info_images = QtWidgets.QLabel("-")
        self.info_annotations = QtWidgets.QLabel("-")
        self.info_created = QtWidgets.QLabel("-")
        self.info_modified = QtWidgets.QLabel("-")

        info_layout.addRow("Version:", self.info_version)
        info_layout.addRow("Description:", self.info_description)
        info_layout.addRow("Total Images:", self.info_images)
        info_layout.addRow("Total Annotations:", self.info_annotations)
        info_layout.addRow("Created:", self.info_created)
        info_layout.addRow("Last Modified:", self.info_modified)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # ===== Buttons =====
        button_layout = QtWidgets.QHBoxLayout()

        self.btn_switch = QtWidgets.QPushButton("Switch to Version")
        self.btn_switch.clicked.connect(self.switch_to_version)
        self.btn_switch.setEnabled(False)
        button_layout.addWidget(self.btn_switch)

        self.btn_delete = QtWidgets.QPushButton("Delete Version")
        self.btn_delete.clicked.connect(self.delete_version)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("QPushButton { color: red; }")
        button_layout.addWidget(self.btn_delete)

        button_layout.addStretch()

        btn_refresh = QtWidgets.QPushButton("Refresh")
        btn_refresh.clicked.connect(self._load_versions)
        button_layout.addWidget(btn_refresh)

        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        button_layout.addWidget(btn_close)

        layout.addLayout(button_layout)

    def _load_versions(self):
        """Load version list"""
        self.version_table.setRowCount(0)

        versions = self.workspace_handler.get_version_list()
        ws_info = self.workspace_handler.get_workspace_info()
        current_version = ws_info.get('current_version', '')

        if not versions:
            return

        # Sort by version
        versions.sort(key=lambda x: x.get('version', ''))

        for version_data in versions:
            row = self.version_table.rowCount()
            self.version_table.insertRow(row)

            version = version_data.get('version', '')
            description = version_data.get('description', '')
            created = version_data.get('created_at', '')
            modified = version_data.get('modified_at', '')
            is_current = version_data.get('is_current', False)
            metadata = version_data.get('metadata', {})

            # Format dates
            try:
                created_dt = datetime.fromisoformat(created)
                created = created_dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass

            try:
                modified_dt = datetime.fromisoformat(modified)
                modified = modified_dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass

            # Version
            item = QtWidgets.QTableWidgetItem(version)
            if is_current:
                item.setForeground(QtCore.Qt.blue)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.version_table.setItem(row, 0, item)

            # Description
            self.version_table.setItem(row, 1, QtWidgets.QTableWidgetItem(description))

            # Created
            self.version_table.setItem(row, 2, QtWidgets.QTableWidgetItem(created))

            # Modified
            self.version_table.setItem(row, 3, QtWidgets.QTableWidgetItem(modified))

            # Annotations count
            total_annotations = metadata.get('total_annotations', 0)
            self.version_table.setItem(row, 4, QtWidgets.QTableWidgetItem(str(total_annotations)))

            # Status
            status = "✓ Current" if is_current else ""
            status_item = QtWidgets.QTableWidgetItem(status)
            if is_current:
                status_item.setForeground(QtCore.Qt.blue)
                font = status_item.font()
                font.setBold(True)
                status_item.setFont(font)
            self.version_table.setItem(row, 5, status_item)

            # Store version data
            item.setData(Qt.UserRole, version_data)

        # Auto resize columns
        self.version_table.resizeColumnsToContents()

    def _on_selection_changed(self):
        """When version is selected"""
        selected_rows = self.version_table.selectedItems()

        if not selected_rows:
            self.btn_switch.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return

        # Get version data from first column
        row = selected_rows[0].row()
        version_item = self.version_table.item(row, 0)
        version_data = version_item.data(Qt.UserRole)

        if not version_data:
            return

        # Show information
        self.info_version.setText(version_data.get('version', '-'))
        self.info_description.setText(version_data.get('description', '-'))

        metadata = version_data.get('metadata', {})
        self.info_images.setText(str(metadata.get('total_images', 0)))
        self.info_annotations.setText(str(metadata.get('total_annotations', 0)))

        created = version_data.get('created_at', '-')
        modified = version_data.get('modified_at', '-')

        try:
            created_dt = datetime.fromisoformat(created)
            self.info_created.setText(created_dt.strftime("%Y-%m-%d %H:%M:%S"))
        except:
            self.info_created.setText(created)

        try:
            modified_dt = datetime.fromisoformat(modified)
            self.info_modified.setText(modified_dt.strftime("%Y-%m-%d %H:%M:%S"))
        except:
            self.info_modified.setText(modified)

        # Enable/disable buttons
        is_current = version_data.get('is_current', False)

        # Switch button: enable if not current version
        self.btn_switch.setEnabled(not is_current)

        # Delete button: enable if not current version
        self.btn_delete.setEnabled(not is_current)

    def switch_to_version(self):
        """Switch to selected version"""
        selected_rows = self.version_table.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        version_item = self.version_table.item(row, 0)
        version_data = version_item.data(Qt.UserRole)

        if not version_data:
            return

        version = version_data.get('version', '')

        # Confirm
        reply = QtWidgets.QMessageBox.question(
            self,
            "Switch Version",
            f"Switch to version '{version}'?\n\n"
            f"Current work will be saved automatically.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )

        if reply == QtWidgets.QMessageBox.Yes:
            success = self.workspace_handler.switch_version(version)

            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", f"Switched to version '{version}'"
                )
                self._load_versions()
                # Emit signal or close dialog to refresh main window
                self.accept()
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", "Failed to switch version"
                )

    def delete_version(self):
        """Delete selected version"""
        selected_rows = self.version_table.selectedItems()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        version_item = self.version_table.item(row, 0)
        version_data = version_item.data(Qt.UserRole)

        if not version_data:
            return

        version = version_data.get('version', '')
        description = version_data.get('description', '')
        metadata = version_data.get('metadata', {})
        total_annotations = metadata.get('total_annotations', 0)

        # Confirm deletion
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Version",
            f"Are you sure you want to delete version '{version}'?\n\n"
            f"Description: {description}\n"
            f"Total Annotations: {total_annotations}\n\n"
            f"⚠️ This will permanently delete all data in this version!\n"
            f"This action cannot be undone!",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            success, message = self.workspace_handler.delete_version(version)

            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", message
                )
                self._load_versions()
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", message
                )
