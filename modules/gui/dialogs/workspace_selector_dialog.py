# modules/gui/workspace_selector_dialog.py

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt


class WorkspaceSelectorDialog(QtWidgets.QDialog):
    """
    Dialog for selecting or creating a Workspace
    """
    
    def __init__(self, workspace_manager, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.selected_workspace = None
        
        self.setWindowTitle("Select Workspace")
        self.resize(600, 400)
        
        self._init_ui()
        self._load_workspaces()

    def _init_ui(self):
        """Create UI"""
        layout = QtWidgets.QVBoxLayout(self)

        # ===== Title =====
        title = QtWidgets.QLabel("Select a Workspace")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # ===== Workspace List =====
        self.workspace_list = QtWidgets.QListWidget()
        self.workspace_list.itemDoubleClicked.connect(self.on_workspace_double_clicked)
        layout.addWidget(self.workspace_list)
        
        # ===== Info Panel =====
        info_group = QtWidgets.QGroupBox("Workspace Info")
        info_layout = QtWidgets.QFormLayout()
        
        self.info_name = QtWidgets.QLabel("-")
        self.info_source = QtWidgets.QLabel("-")
        self.info_version = QtWidgets.QLabel("-")
        self.info_modified = QtWidgets.QLabel("-")
        
        info_layout.addRow("Name:", self.info_name)
        info_layout.addRow("Source Folder:", self.info_source)
        info_layout.addRow("Current Version:", self.info_version)
        info_layout.addRow("Last Modified:", self.info_modified)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # ===== Buttons =====
        button_layout = QtWidgets.QHBoxLayout()

        btn_new = QtWidgets.QPushButton("New Workspace")
        btn_new.clicked.connect(self.create_new_workspace)
        button_layout.addWidget(btn_new)

        self.btn_rename = QtWidgets.QPushButton("Rename")
        self.btn_rename.clicked.connect(self.rename_workspace)
        self.btn_rename.setEnabled(False)
        button_layout.addWidget(self.btn_rename)

        self.btn_delete = QtWidgets.QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_workspace)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("QPushButton { color: red; }")
        button_layout.addWidget(self.btn_delete)

        self.btn_repair = QtWidgets.QPushButton("🔧 Repair")
        self.btn_repair.clicked.connect(self.repair_workspace)
        self.btn_repair.setEnabled(False)
        self.btn_repair.setToolTip("Repair workspace with inconsistent data")
        button_layout.addWidget(self.btn_repair)

        button_layout.addStretch()

        btn_open = QtWidgets.QPushButton("Open")
        btn_open.clicked.connect(self.accept)
        button_layout.addWidget(btn_open)

        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)
        
        # Connect selection
        self.workspace_list.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _load_workspaces(self):
        """Load workspace list"""
        self.workspace_list.clear()

        workspaces = self.workspace_manager.get_workspace_list()

        if not workspaces:
            # No workspaces
            item = QtWidgets.QListWidgetItem("No workspaces found. Click 'New Workspace' to create one.")
            item.setFlags(Qt.NoItemFlags)
            self.workspace_list.addItem(item)
            return

        # Sort by modified_at
        workspaces.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        
        for ws in workspaces:
            item = QtWidgets.QListWidgetItem(f"📁 {ws['name']}")
            item.setData(Qt.UserRole, ws)
            self.workspace_list.addItem(item)
    
    def _on_selection_changed(self):
        """When workspace is selected"""
        items = self.workspace_list.selectedItems()
        if not items:
            self.btn_rename.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_repair.setEnabled(False)
            return

        ws_data = items[0].data(Qt.UserRole)
        if not ws_data:
            self.btn_rename.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_repair.setEnabled(False)
            return

        self.selected_workspace = ws_data["id"]

        # Enable rename, delete and repair buttons
        self.btn_rename.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_repair.setEnabled(True)

        # Show information
        self.info_name.setText(ws_data["name"])
        self.info_source.setText(ws_data["source_folder"])
        self.info_version.setText(ws_data["current_version"])
        self.info_modified.setText(ws_data["modified_at"][:19])
    
    def on_workspace_double_clicked(self, item):
        """Double click = open workspace"""
        if item.data(Qt.UserRole):
            self.accept()
    
    def create_new_workspace(self):
        """Create new workspace"""
        dialog = NewWorkspaceDialog(self.workspace_manager, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.selected_workspace = dialog.workspace_id
            self._load_workspaces()
            # Select newly created workspace
            for i in range(self.workspace_list.count()):
                item = self.workspace_list.item(i)
                ws_data = item.data(Qt.UserRole)
                if ws_data and ws_data["id"] == self.selected_workspace:
                    self.workspace_list.setCurrentItem(item)
                    break

    def rename_workspace(self):
        """Rename workspace"""
        if not self.selected_workspace:
            return

        # Get old name
        workspace_data = self.workspace_manager.load_workspace(self.selected_workspace)
        if not workspace_data:
            return

        old_name = workspace_data["workspace"]["name"]

        # Show dialog to enter new name
        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename Workspace",
            "Enter new workspace name:",
            QtWidgets.QLineEdit.Normal,
            old_name
        )

        if ok and new_name.strip():
            success, message = self.workspace_manager.rename_workspace(
                self.selected_workspace,
                new_name.strip()
            )

            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", message
                )
                # Refresh list
                self._load_workspaces()
                # Select the same workspace again
                for i in range(self.workspace_list.count()):
                    item = self.workspace_list.item(i)
                    ws_data = item.data(Qt.UserRole)
                    if ws_data and ws_data["id"] == self.selected_workspace:
                        self.workspace_list.setCurrentItem(item)
                        break
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", message
                )

    def delete_workspace(self):
        """Delete workspace"""
        if not self.selected_workspace:
            return

        # Get workspace data
        workspace_data = self.workspace_manager.load_workspace(self.selected_workspace)
        if not workspace_data:
            return

        name = workspace_data["workspace"]["name"]

        # Confirm deletion
        reply = QtWidgets.QMessageBox.question(
            self,
            "Delete Workspace",
            f"Are you sure you want to delete workspace '{name}'?\n\n"
            f"⚠️ This will permanently delete:\n"
            f"  • All versions\n"
            f"  • All annotations\n"
            f"  • All workspace data\n\n"
            f"This action cannot be undone!",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Delete workspace
            success = self.workspace_manager.delete_workspace(self.selected_workspace)

            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", f"Workspace '{name}' deleted successfully"
                )
                # Refresh list
                self.selected_workspace = None
                self._load_workspaces()
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", "Failed to delete workspace"
                )

    def repair_workspace(self):
        """Repair workspace"""
        if not self.selected_workspace:
            return

        # Get workspace data
        workspace_data = self.workspace_manager.load_workspace(self.selected_workspace)
        if not workspace_data:
            return

        name = workspace_data["workspace"]["name"]

        # Confirm repair
        reply = QtWidgets.QMessageBox.question(
            self,
            "Repair Workspace",
            f"Repair workspace '{name}'?\n\n"
            f"This will:\n"
            f"  • Check for missing version files\n"
            f"  • Remove invalid version entries\n"
            f"  • Fix current version reference\n\n"
            f"Do you want to continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Repair workspace
            success, message = self.workspace_manager.repair_workspace(self.selected_workspace)

            if success:
                QtWidgets.QMessageBox.information(
                    self, "Repair Complete", message
                )
                # Refresh list
                self._load_workspaces()
                # Select the same workspace again
                for i in range(self.workspace_list.count()):
                    item = self.workspace_list.item(i)
                    ws_data = item.data(Qt.UserRole)
                    if ws_data and ws_data["id"] == self.selected_workspace:
                        self.workspace_list.setCurrentItem(item)
                        break
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", message
                )


class NewWorkspaceDialog(QtWidgets.QDialog):
    """
    Dialog for creating a new Workspace
    """
    
    def __init__(self, workspace_manager, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.workspace_id = None
        
        self.setWindowTitle("Create New Workspace")
        self.resize(500, 300)
        
        self._init_ui()

    def _init_ui(self):
        """Create UI"""
        layout = QtWidgets.QVBoxLayout(self)

        # ===== Form =====
        form_layout = QtWidgets.QFormLayout()
        
        self.edit_name = QtWidgets.QLineEdit()
        self.edit_name.setPlaceholderText("e.g., Invoice Dataset")
        form_layout.addRow("Workspace Name:*", self.edit_name)
        
        folder_layout = QtWidgets.QHBoxLayout()
        self.edit_folder = QtWidgets.QLineEdit()
        self.edit_folder.setPlaceholderText("Select source image folder...")
        btn_browse = QtWidgets.QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_folder)
        folder_layout.addWidget(self.edit_folder)
        folder_layout.addWidget(btn_browse)
        form_layout.addRow("Source Folder:*", folder_layout)
        
        self.edit_description = QtWidgets.QTextEdit()
        self.edit_description.setPlaceholderText("Optional description...")
        self.edit_description.setMaximumHeight(80)
        form_layout.addRow("Description:", self.edit_description)
        
        layout.addLayout(form_layout)
        
        # ===== Info =====
        info_label = QtWidgets.QLabel(
            "💡 Tip: The workspace ID will be auto-generated from the name."
        )
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # ===== Buttons =====
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        
        btn_create = QtWidgets.QPushButton("Create")
        btn_create.clicked.connect(self.create_workspace)
        button_layout.addWidget(btn_create)
        
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
    
    def browse_folder(self):
        """Select folder"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Source Image Folder", ""
        )
        if folder:
            self.edit_folder.setText(folder)
    
    def create_workspace(self):
        """Create workspace"""
        name = self.edit_name.text().strip()
        folder = self.edit_folder.text().strip()
        description = self.edit_description.toPlainText().strip()

        # Validate
        if not name:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter workspace name")
            return

        if not folder:
            QtWidgets.QMessageBox.warning(self, "Error", "Please select source folder")
            return

        # Create workspace_id from name
        workspace_id = name.lower().replace(" ", "_").replace("-", "_")
        # Remove special characters
        workspace_id = "".join(c for c in workspace_id if c.isalnum() or c == "_")

        # Create workspace
        success = self.workspace_manager.create_workspace(
            workspace_id, name, folder, description
        )
        
        if success:
            self.workspace_id = workspace_id
            self.accept()
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error", 
                f"Failed to create workspace. Workspace '{workspace_id}' may already exist."
            )