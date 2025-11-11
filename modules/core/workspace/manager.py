"""
Workspace Manager - Core workspace management.

This module provides high-level workspace operations by combining
storage and version management functionality.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from modules.constants import WORKSPACE_VERSION, DIR_WORKSPACES
from modules.core.workspace.storage import WorkspaceStorage
from modules.core.workspace.version import VersionManager

logger = logging.getLogger("TextDetGUI")


class WorkspaceManager:
    """
    Main workspace manager class.

    Combines storage and version management to provide high-level
    workspace operations.
    """

    def __init__(self, root_dir: str):
        """
        Initialize workspace manager.

        Args:
            root_dir: Project root directory
        """
        self.root_dir = root_dir
        self.workspaces_dir = os.path.join(root_dir, DIR_WORKSPACES)

        # Initialize sub-managers
        self.storage = WorkspaceStorage(self.workspaces_dir)
        self.version_manager = VersionManager(self.storage)

        logger.info(f"WorkspaceManager initialized with root: {root_dir}")

    # ===== Workspace Creation =====

    def create_workspace(self, workspace_id: str, name: str,
                        source_folder: str, description: str = "") -> bool:
        """
        Create new workspace.

        Args:
            workspace_id: Unique workspace identifier
            name: Workspace display name
            source_folder: Path to source image folder
            description: Workspace description

        Returns:
            True if successful
        """
        try:
            # Check if workspace already exists
            if self.storage.workspace_exists(workspace_id):
                logger.error(f"Workspace {workspace_id} already exists")
                return False

            # Create workspace directory
            success = self.storage.create_workspace_directory(workspace_id)
            if not success:
                return False

            # Create workspace.json
            workspace_data = {
                "version": WORKSPACE_VERSION,
                "workspace": {
                    "id": workspace_id,
                    "name": name,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "modified_at": datetime.now().isoformat()
                },
                "source": {
                    "folder": source_folder,
                    "total_images": 0,
                    "last_scan": None
                },
                "versions": {
                    "current": "v1",
                    "available": ["v1"]
                },
                "settings": {
                    "detector": {
                        "model": "paddleocr",
                        "lang": "th"
                    }
                }
            }

            success = self.storage.write_workspace_file(workspace_id, workspace_data)
            if not success:
                return False

            # Create initial version (v1)
            v1_data = {
                "version": WORKSPACE_VERSION,
                "workspace_id": workspace_id,
                "data_version": "v1",
                "created_at": datetime.now().isoformat(),
                "modified_at": datetime.now().isoformat(),
                "description": "Initial version",
                "annotations": {},
                "transforms": {},
                "metadata": {
                    "total_images": 0,
                    "annotated_images": 0,
                    "total_annotations": 0
                }
            }

            success = self.storage.write_version_file(workspace_id, "v1", v1_data)
            if not success:
                return False

            # Create empty exports.json
            exports_data = {
                "version": WORKSPACE_VERSION,
                "workspace_id": workspace_id,
                "exports": []
            }

            self.storage.write_exports_file(workspace_id, exports_data)

            logger.info(f"Created workspace: {workspace_id} ({name})")
            return True

        except Exception as e:
            logger.error(f"Failed to create workspace {workspace_id}: {e}")
            return False

    # ===== Workspace Loading =====

    def load_workspace(self, workspace_id: str) -> Optional[Dict]:
        """
        Load workspace data.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace data dict or None
        """
        if not self.storage.workspace_exists(workspace_id):
            logger.error(f"Workspace {workspace_id} not found")
            return None

        workspace_data = self.storage.read_workspace_file(workspace_id)

        if workspace_data is None:
            logger.error(f"Failed to load workspace {workspace_id}")
            return None

        # Validate and repair if needed
        workspace_data = self._validate_and_repair_workspace(workspace_id, workspace_data)

        logger.info(f"Loaded workspace: {workspace_id}")
        return workspace_data

    def _validate_and_repair_workspace(self, workspace_id: str, workspace_data: Dict) -> Dict:
        """
        Validate and repair workspace data.

        Args:
            workspace_id: Workspace ID
            workspace_data: Workspace data

        Returns:
            Validated/repaired workspace data
        """
        repaired = False

        # Ensure version field
        if 'version' not in workspace_data:
            workspace_data['version'] = WORKSPACE_VERSION
            repaired = True

        # Ensure versions structure
        if 'versions' not in workspace_data:
            workspace_data['versions'] = {
                "current": "v1",
                "available": ["v1"]
            }
            repaired = True
        else:
            versions = workspace_data['versions']

            # Ensure current version
            if 'current' not in versions or not versions['current']:
                versions['current'] = "v1"
                repaired = True

            # Ensure available list
            if 'available' not in versions:
                # Scan for version files
                available = self.storage.list_version_files(workspace_id)
                if not available:
                    available = ["v1"]
                versions['available'] = available
                repaired = True

        # Save if repaired
        if repaired:
            self.storage.write_workspace_file(workspace_id, workspace_data)
            logger.info(f"Repaired workspace data: {workspace_id}")

        return workspace_data

    # ===== Workspace Saving =====

    def save_workspace(self, workspace_id: str, data: Dict) -> bool:
        """
        Save workspace data.

        Args:
            workspace_id: Workspace ID
            data: Workspace data

        Returns:
            True if successful
        """
        return self.storage.write_workspace_file(workspace_id, data)

    # ===== Workspace Deletion =====

    def delete_workspace(self, workspace_id: str) -> bool:
        """
        Delete workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if successful
        """
        if not self.storage.workspace_exists(workspace_id):
            logger.error(f"Workspace {workspace_id} not found")
            return False

        return self.storage.delete_workspace_directory(workspace_id)

    # ===== Workspace Listing =====

    def get_workspace_list(self) -> List[Dict]:
        """
        Get list of all workspaces.

        Returns:
            List of workspace info dicts
        """
        workspace_ids = self.storage.list_workspace_ids()
        workspace_list = []

        for workspace_id in workspace_ids:
            workspace_data = self.storage.read_workspace_file(workspace_id)

            if workspace_data:
                workspace_info = workspace_data.get('workspace', {})
                versions_info = workspace_data.get('versions', {})

                item = {
                    'id': workspace_id,
                    'name': workspace_info.get('name', workspace_id),
                    'description': workspace_info.get('description', ''),
                    'created_at': workspace_info.get('created_at', ''),
                    'modified_at': workspace_info.get('modified_at', ''),
                    'current_version': versions_info.get('current', 'v1'),
                    'available_versions': versions_info.get('available', [])
                }

                workspace_list.append(item)

        # Sort by modified_at (newest first)
        workspace_list.sort(key=lambda x: x['modified_at'], reverse=True)

        return workspace_list

    # ===== Workspace Renaming =====

    def rename_workspace(self, workspace_id: str, new_name: str) -> Tuple[bool, str]:
        """
        Rename workspace.

        Args:
            workspace_id: Workspace ID
            new_name: New workspace name

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            workspace_data = self.storage.read_workspace_file(workspace_id)

            if not workspace_data:
                return False, "Workspace not found"

            # Update name
            workspace_data['workspace']['name'] = new_name
            workspace_data['workspace']['modified_at'] = datetime.now().isoformat()

            # Save
            success = self.storage.write_workspace_file(workspace_id, workspace_data)

            if success:
                logger.info(f"Renamed workspace {workspace_id} to '{new_name}'")
                return True, f"Workspace renamed to '{new_name}'"
            else:
                return False, "Failed to save workspace data"

        except Exception as e:
            logger.error(f"Failed to rename workspace: {e}")
            return False, str(e)

    # ===== Workspace Repair =====

    def repair_workspace(self, workspace_id: str) -> Tuple[bool, str]:
        """
        Repair workspace (validate and fix issues).

        Args:
            workspace_id: Workspace ID

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.storage.workspace_exists(workspace_id):
                return False, "Workspace not found"

            workspace_data = self.storage.read_workspace_file(workspace_id)

            if not workspace_data:
                return False, "Failed to load workspace data"

            # Validate and repair
            repaired_data = self._validate_and_repair_workspace(workspace_id, workspace_data)

            return True, "Workspace validated and repaired successfully"

        except Exception as e:
            logger.error(f"Failed to repair workspace: {e}")
            return False, str(e)

    # ===== Version Operations (Delegated to VersionManager) =====

    def load_version(self, workspace_id: str, version: str) -> Optional[Dict]:
        """Load version data."""
        return self.version_manager.load_version(workspace_id, version)

    def save_version(self, workspace_id: str, version: str, data: Dict) -> bool:
        """Save version data."""
        return self.version_manager.save_version(workspace_id, version, data)

    def create_version(self, workspace_id: str, new_version: str,
                      source_version: Optional[str] = None,
                      description: str = "") -> Tuple[bool, str]:
        """Create new version."""
        return self.version_manager.create_version(
            workspace_id, new_version, source_version, description
        )

    def switch_version(self, workspace_id: str, version: str) -> bool:
        """Switch to different version."""
        return self.version_manager.switch_version(workspace_id, version)

    def delete_version(self, workspace_id: str, version: str) -> Tuple[bool, str]:
        """Delete version."""
        return self.version_manager.delete_version(workspace_id, version)

    def get_version_list(self, workspace_id: str) -> List[Dict]:
        """Get list of all versions."""
        return self.version_manager.get_version_list(workspace_id)

    def get_current_version(self, workspace_id: str) -> Optional[str]:
        """Get current version name."""
        return self.version_manager.get_current_version(workspace_id)

    # ===== Exports Operations =====

    def get_exports(self, workspace_id: str) -> List[Dict]:
        """
        Get export history.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of export records
        """
        exports_data = self.storage.read_exports_file(workspace_id)

        if exports_data:
            return exports_data.get('exports', [])

        return []

    def add_export_record(self, workspace_id: str, export_info: Dict) -> bool:
        """
        Add export record.

        Args:
            workspace_id: Workspace ID
            export_info: Export information dict

        Returns:
            True if successful
        """
        try:
            exports_data = self.storage.read_exports_file(workspace_id)

            if not exports_data:
                exports_data = {
                    "version": WORKSPACE_VERSION,
                    "workspace_id": workspace_id,
                    "exports": []
                }

            # Add timestamp if not present
            if 'timestamp' not in export_info:
                export_info['timestamp'] = datetime.now().isoformat()

            # Add to exports list
            exports_data['exports'].append(export_info)

            # Save
            return self.storage.write_exports_file(workspace_id, exports_data)

        except Exception as e:
            logger.error(f"Failed to add export record: {e}")
            return False
