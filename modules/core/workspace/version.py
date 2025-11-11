"""
Workspace Version Management.

This module handles version control for workspaces:
- Creating new versions
- Switching between versions
- Deleting versions
- Version listing and metadata
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from modules.constants import WORKSPACE_VERSION
from modules.core.workspace.storage import WorkspaceStorage

logger = logging.getLogger("TextDetGUI")


class VersionManager:
    """
    Manages versions for a workspace.

    Responsibilities:
    - Version CRUD operations
    - Version switching
    - Version metadata management
    """

    def __init__(self, storage: WorkspaceStorage):
        """
        Initialize version manager.

        Args:
            storage: WorkspaceStorage instance
        """
        self.storage = storage

    # ===== Version Loading/Saving =====

    def load_version(self, workspace_id: str, version: str) -> Optional[Dict]:
        """
        Load version data.

        Args:
            workspace_id: Workspace ID
            version: Version name

        Returns:
            Version data dict or None
        """
        if not self.storage.version_file_exists(workspace_id, version):
            logger.error(f"Version {version} not found in workspace {workspace_id}")
            return None

        data = self.storage.read_version_file(workspace_id, version)

        if data is None:
            logger.error(f"Failed to load version {version}")
            return None

        logger.info(f"Loaded version {version} from workspace {workspace_id}")
        return data

    def save_version(self, workspace_id: str, version: str, data: Dict) -> bool:
        """
        Save version data.

        Args:
            workspace_id: Workspace ID
            version: Version name
            data: Version data

        Returns:
            True if successful
        """
        # Ensure required fields
        if 'version' not in data:
            data['version'] = WORKSPACE_VERSION
        if 'workspace_id' not in data:
            data['workspace_id'] = workspace_id
        if 'data_version' not in data:
            data['data_version'] = version

        success = self.storage.write_version_file(workspace_id, version, data)

        if success:
            logger.info(f"Saved version {version} to workspace {workspace_id}")
        else:
            logger.error(f"Failed to save version {version}")

        return success

    # ===== Version Creation =====

    def create_version(self, workspace_id: str, new_version: str,
                      source_version: Optional[str] = None,
                      description: str = "") -> Tuple[bool, str]:
        """
        Create new version.

        Args:
            workspace_id: Workspace ID
            new_version: New version name
            source_version: Source version to copy from (None = create empty)
            description: Version description

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if version already exists
            if self.storage.version_file_exists(workspace_id, new_version):
                return False, f"Version {new_version} already exists"

            # Create new version data
            if source_version and self.storage.version_file_exists(workspace_id, source_version):
                # Copy from source version
                source_data = self.storage.read_version_file(workspace_id, source_version)

                if source_data is None:
                    return False, f"Failed to read source version {source_version}"

                # Create new version data based on source
                new_data = {
                    "version": WORKSPACE_VERSION,
                    "workspace_id": workspace_id,
                    "data_version": new_version,
                    "created_at": datetime.now().isoformat(),
                    "modified_at": datetime.now().isoformat(),
                    "description": description or f"Copied from {source_version}",
                    "annotations": source_data.get('annotations', {}),
                    "transforms": source_data.get('transforms', {}),
                    "metadata": source_data.get('metadata', {
                        "total_images": 0,
                        "annotated_images": 0,
                        "total_annotations": 0
                    })
                }

                logger.info(f"Creating version {new_version} from {source_version}")

            else:
                # Create empty version
                new_data = {
                    "version": WORKSPACE_VERSION,
                    "workspace_id": workspace_id,
                    "data_version": new_version,
                    "created_at": datetime.now().isoformat(),
                    "modified_at": datetime.now().isoformat(),
                    "description": description or "Empty version",
                    "annotations": {},
                    "transforms": {},
                    "metadata": {
                        "total_images": 0,
                        "annotated_images": 0,
                        "total_annotations": 0
                    }
                }

                logger.info(f"Creating empty version {new_version}")

            # Save new version
            success = self.storage.write_version_file(workspace_id, new_version, new_data)

            if not success:
                return False, "Failed to save new version file"

            # Update workspace.json to add new version
            workspace_data = self.storage.read_workspace_file(workspace_id)

            if workspace_data:
                versions = workspace_data.get('versions', {})
                available = versions.get('available', [])

                if new_version not in available:
                    available.append(new_version)
                    versions['available'] = sorted(available)  # Keep sorted

                workspace_data['versions'] = versions

                self.storage.write_workspace_file(workspace_id, workspace_data)

            return True, f"Version {new_version} created successfully"

        except Exception as e:
            logger.error(f"Failed to create version {new_version}: {e}")
            return False, str(e)

    # ===== Version Switching =====

    def switch_version(self, workspace_id: str, version: str) -> bool:
        """
        Switch to different version.

        Args:
            workspace_id: Workspace ID
            version: Target version name

        Returns:
            True if successful
        """
        try:
            # Check if version exists
            if not self.storage.version_file_exists(workspace_id, version):
                logger.error(f"Version {version} not found")
                return False

            # Update workspace.json
            workspace_data = self.storage.read_workspace_file(workspace_id)

            if not workspace_data:
                logger.error("Failed to load workspace data")
                return False

            # Update current version
            if 'versions' not in workspace_data:
                workspace_data['versions'] = {}

            workspace_data['versions']['current'] = version

            # Save workspace data
            success = self.storage.write_workspace_file(workspace_id, workspace_data)

            if success:
                logger.info(f"Switched to version {version} in workspace {workspace_id}")
            else:
                logger.error("Failed to save workspace after version switch")

            return success

        except Exception as e:
            logger.error(f"Failed to switch version: {e}")
            return False

    # ===== Version Deletion =====

    def delete_version(self, workspace_id: str, version: str) -> Tuple[bool, str]:
        """
        Delete version.

        Args:
            workspace_id: Workspace ID
            version: Version name to delete

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Load workspace data
            workspace_data = self.storage.read_workspace_file(workspace_id)

            if not workspace_data:
                return False, "Failed to load workspace data"

            versions_info = workspace_data.get('versions', {})
            current_version = versions_info.get('current')
            available_versions = versions_info.get('available', [])

            # Cannot delete current version
            if version == current_version:
                return False, f"Cannot delete current version ({version}). Switch to another version first."

            # Cannot delete if it's the only version
            if len(available_versions) <= 1:
                return False, "Cannot delete the only version in workspace"

            # Check if version exists
            if not self.storage.version_file_exists(workspace_id, version):
                return False, f"Version {version} not found"

            # Delete version file
            success = self.storage.delete_version_file(workspace_id, version)

            if not success:
                return False, "Failed to delete version file"

            # Update workspace.json
            if version in available_versions:
                available_versions.remove(version)
                versions_info['available'] = available_versions
                workspace_data['versions'] = versions_info

                self.storage.write_workspace_file(workspace_id, workspace_data)

            logger.info(f"Deleted version {version} from workspace {workspace_id}")
            return True, f"Version {version} deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete version {version}: {e}")
            return False, str(e)

    # ===== Version Listing =====

    def get_version_list(self, workspace_id: str) -> List[Dict]:
        """
        Get list of all versions with metadata.

        Args:
            workspace_id: Workspace ID

        Returns:
            List of version info dicts
        """
        try:
            # Get workspace data for current version
            workspace_data = self.storage.read_workspace_file(workspace_id)
            current_version = None

            if workspace_data:
                current_version = workspace_data.get('versions', {}).get('current')

            # Get all version files
            version_names = self.storage.list_version_files(workspace_id)

            version_list = []
            for version_name in version_names:
                version_data = self.storage.read_version_file(workspace_id, version_name)

                if version_data:
                    version_info = {
                        'name': version_name,
                        'is_current': (version_name == current_version),
                        'created_at': version_data.get('created_at', ''),
                        'modified_at': version_data.get('modified_at', ''),
                        'description': version_data.get('description', ''),
                        'metadata': version_data.get('metadata', {})
                    }

                    version_list.append(version_info)

            # Sort by name
            version_list.sort(key=lambda x: x['name'])

            return version_list

        except Exception as e:
            logger.error(f"Failed to get version list: {e}")
            return []

    # ===== Version Info =====

    def get_current_version(self, workspace_id: str) -> Optional[str]:
        """
        Get current version name.

        Args:
            workspace_id: Workspace ID

        Returns:
            Current version name or None
        """
        workspace_data = self.storage.read_workspace_file(workspace_id)

        if workspace_data:
            return workspace_data.get('versions', {}).get('current')

        return None

    def version_exists(self, workspace_id: str, version: str) -> bool:
        """
        Check if version exists.

        Args:
            workspace_id: Workspace ID
            version: Version name

        Returns:
            True if version exists
        """
        return self.storage.version_file_exists(workspace_id, version)
