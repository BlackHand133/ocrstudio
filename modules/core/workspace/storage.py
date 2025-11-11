"""
Workspace Storage Operations.

This module handles all file I/O operations for workspaces:
- Reading/writing JSON files
- File path management
- Directory operations
"""

import os
import json
import shutil
import logging
from typing import Dict, Optional
from datetime import datetime

from modules.constants import WORKSPACE_VERSION, WORKSPACE_FILE

logger = logging.getLogger("TextDetGUI")


class WorkspaceStorage:
    """
    Handles storage operations for workspaces.

    Responsibilities:
    - File I/O operations
    - JSON serialization/deserialization
    - Path management
    - Directory operations
    """

    def __init__(self, workspaces_dir: str):
        """
        Initialize storage handler.

        Args:
            workspaces_dir: Base directory for all workspaces
        """
        self.workspaces_dir = workspaces_dir
        os.makedirs(workspaces_dir, exist_ok=True)

    # ===== Path Operations =====

    def get_workspace_path(self, workspace_id: str) -> str:
        """Get workspace directory path."""
        return os.path.join(self.workspaces_dir, workspace_id)

    def get_workspace_file_path(self, workspace_id: str) -> str:
        """Get workspace.json file path."""
        return os.path.join(self.get_workspace_path(workspace_id), WORKSPACE_FILE)

    def get_version_file_path(self, workspace_id: str, version: str) -> str:
        """Get version file path (e.g., v1.json)."""
        return os.path.join(self.get_workspace_path(workspace_id), f"{version}.json")

    def get_exports_file_path(self, workspace_id: str) -> str:
        """Get exports.json file path."""
        return os.path.join(self.get_workspace_path(workspace_id), "exports.json")

    def workspace_exists(self, workspace_id: str) -> bool:
        """Check if workspace exists."""
        return os.path.exists(self.get_workspace_path(workspace_id))

    def version_file_exists(self, workspace_id: str, version: str) -> bool:
        """Check if version file exists."""
        return os.path.exists(self.get_version_file_path(workspace_id, version))

    # ===== JSON Operations =====

    def read_json(self, file_path: str) -> Optional[Dict]:
        """
        Read JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            Dict if successful, None if failed
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"JSON file not found: {file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return None

    def write_json(self, file_path: str, data: Dict) -> bool:
        """
        Write JSON file.

        Args:
            file_path: Path to JSON file
            data: Data to write

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write with pretty formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Wrote JSON to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write {file_path}: {e}")
            return False

    # ===== Workspace File Operations =====

    def read_workspace_file(self, workspace_id: str) -> Optional[Dict]:
        """
        Read workspace.json file.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace data dict or None
        """
        file_path = self.get_workspace_file_path(workspace_id)
        return self.read_json(file_path)

    def write_workspace_file(self, workspace_id: str, data: Dict) -> bool:
        """
        Write workspace.json file.

        Args:
            workspace_id: Workspace ID
            data: Workspace data

        Returns:
            True if successful
        """
        file_path = self.get_workspace_file_path(workspace_id)

        # Update modified timestamp
        if 'workspace' in data and 'modified_at' in data['workspace']:
            data['workspace']['modified_at'] = datetime.now().isoformat()

        return self.write_json(file_path, data)

    # ===== Version File Operations =====

    def read_version_file(self, workspace_id: str, version: str) -> Optional[Dict]:
        """
        Read version file (e.g., v1.json).

        Args:
            workspace_id: Workspace ID
            version: Version name

        Returns:
            Version data dict or None
        """
        file_path = self.get_version_file_path(workspace_id, version)
        return self.read_json(file_path)

    def write_version_file(self, workspace_id: str, version: str, data: Dict) -> bool:
        """
        Write version file.

        Args:
            workspace_id: Workspace ID
            version: Version name
            data: Version data

        Returns:
            True if successful
        """
        file_path = self.get_version_file_path(workspace_id, version)

        # Update modified timestamp
        if 'modified_at' in data:
            data['modified_at'] = datetime.now().isoformat()

        return self.write_json(file_path, data)

    # ===== Exports File Operations =====

    def read_exports_file(self, workspace_id: str) -> Optional[Dict]:
        """Read exports.json file."""
        file_path = self.get_exports_file_path(workspace_id)
        data = self.read_json(file_path)

        # Return empty exports structure if not found
        if data is None:
            return {
                "version": WORKSPACE_VERSION,
                "workspace_id": workspace_id,
                "exports": []
            }

        return data

    def write_exports_file(self, workspace_id: str, data: Dict) -> bool:
        """Write exports.json file."""
        file_path = self.get_exports_file_path(workspace_id)
        return self.write_json(file_path, data)

    # ===== Directory Operations =====

    def create_workspace_directory(self, workspace_id: str) -> bool:
        """
        Create workspace directory.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if successful
        """
        try:
            workspace_path = self.get_workspace_path(workspace_id)

            if os.path.exists(workspace_path):
                logger.warning(f"Workspace directory already exists: {workspace_id}")
                return False

            os.makedirs(workspace_path, exist_ok=True)
            logger.info(f"Created workspace directory: {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create workspace directory {workspace_id}: {e}")
            return False

    def delete_workspace_directory(self, workspace_id: str) -> bool:
        """
        Delete workspace directory and all contents.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if successful
        """
        try:
            workspace_path = self.get_workspace_path(workspace_id)

            if not os.path.exists(workspace_path):
                logger.warning(f"Workspace directory not found: {workspace_id}")
                return False

            shutil.rmtree(workspace_path)
            logger.info(f"Deleted workspace directory: {workspace_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete workspace directory {workspace_id}: {e}")
            return False

    def delete_version_file(self, workspace_id: str, version: str) -> bool:
        """
        Delete version file.

        Args:
            workspace_id: Workspace ID
            version: Version name

        Returns:
            True if successful
        """
        try:
            file_path = self.get_version_file_path(workspace_id, version)

            if not os.path.exists(file_path):
                logger.warning(f"Version file not found: {version}")
                return False

            os.remove(file_path)
            logger.info(f"Deleted version file: {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete version file {version}: {e}")
            return False

    def copy_version_file(self, workspace_id: str, source_version: str,
                         target_version: str) -> bool:
        """
        Copy version file.

        Args:
            workspace_id: Workspace ID
            source_version: Source version name
            target_version: Target version name

        Returns:
            True if successful
        """
        try:
            source_path = self.get_version_file_path(workspace_id, source_version)
            target_path = self.get_version_file_path(workspace_id, target_version)

            if not os.path.exists(source_path):
                logger.error(f"Source version not found: {source_version}")
                return False

            if os.path.exists(target_path):
                logger.warning(f"Target version already exists: {target_version}")
                return False

            shutil.copy2(source_path, target_path)
            logger.info(f"Copied version {source_version} to {target_version}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy version file: {e}")
            return False

    # ===== List Operations =====

    def list_workspace_ids(self) -> list:
        """
        List all workspace IDs.

        Returns:
            List of workspace IDs
        """
        try:
            if not os.path.exists(self.workspaces_dir):
                return []

            # Get directories that contain workspace.json
            workspace_ids = []
            for item in os.listdir(self.workspaces_dir):
                item_path = os.path.join(self.workspaces_dir, item)
                if os.path.isdir(item_path):
                    workspace_file = os.path.join(item_path, WORKSPACE_FILE)
                    if os.path.exists(workspace_file):
                        workspace_ids.append(item)

            return workspace_ids

        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            return []

    def list_version_files(self, workspace_id: str) -> list:
        """
        List all version files in workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of version names (e.g., ['v1', 'v2', 'v3'])
        """
        try:
            workspace_path = self.get_workspace_path(workspace_id)

            if not os.path.exists(workspace_path):
                return []

            # Find all v*.json files
            versions = []
            for item in os.listdir(workspace_path):
                if item.startswith('v') and item.endswith('.json'):
                    version_name = item[:-5]  # Remove .json
                    versions.append(version_name)

            # Sort versions
            versions.sort()

            return versions

        except Exception as e:
            logger.error(f"Failed to list versions: {e}")
            return []
