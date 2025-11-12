# modules/gui/window_handler/workspace_handler.py

import logging
from typing import Optional, Dict
from modules.utils import sanitize_annotations

logger = logging.getLogger("TextDetGUI")


class WorkspaceHandler:
    """
    Manage Workspace and Version for MainWindow
    Replaces the old CacheHandler
    """

    def __init__(self, main_window):
        """
        Args:
            main_window: reference to MainWindow instance
        """
        self.main_window = main_window
        self.current_workspace_id = None
        self.current_version = None
        self.version_data = None
    
    def load_workspace(self, workspace_id: str, version: Optional[str] = None):
        """
        Load workspace and version

        Args:
            workspace_id: workspace id
            version: version name (None = use current version)
        """
        try:
            # Load workspace
            workspace_data = self.main_window.workspace_manager.load_workspace(workspace_id)
            if not workspace_data:
                logger.error(f"Failed to load workspace: {workspace_id}")
                return False

            # Use current version if not specified
            if version is None:
                version = workspace_data["versions"]["current"]

            # Load version data
            version_data = self.main_window.workspace_manager.load_version(workspace_id, version)
            if not version_data:
                logger.error(f"Failed to load version: {version}")
                return False

            # Store data
            self.current_workspace_id = workspace_id
            self.current_version = version
            self.version_data = version_data

            # Load data into MainWindow
            self.main_window.annotations = version_data.get("annotations", {})
            self.main_window.image_rotations = version_data.get("transforms", {})

            # Update app config
            self.main_window.workspace_manager.app_config["current_workspace"] = workspace_id
            self.main_window.workspace_manager.save_app_config()

            # Add to recent list
            self.main_window.workspace_manager.add_recent_workspace(workspace_id)
            
            logger.info(f"Loaded workspace: {workspace_id}, version: {version}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load workspace: {e}")
            return False
    
    def save_workspace(self):
        """Save current workspace"""
        if not self.current_workspace_id or not self.current_version:
            logger.warning("No workspace loaded")
            return False
        
        try:
            # Sanitize annotations
            sanitized_annotations = {}
            for key, anns in self.main_window.annotations.items():
                sanitized_annotations[key] = sanitize_annotations(anns)

            # Update version data
            self.version_data["annotations"] = sanitized_annotations
            self.version_data["transforms"] = self.main_window.image_rotations

            # Save
            success = self.main_window.workspace_manager.save_version(
                self.current_workspace_id,
                self.current_version,
                self.version_data
            )
            
            if success:
                logger.debug(f"Saved workspace: {self.current_workspace_id}")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to save workspace: {e}")
            return False
    
    def create_new_version(self, new_version: str, base_version: Optional[str] = None,
                          description: str = "") -> bool:
        """
        Create new version

        Args:
            new_version: new version name e.g. "v2"
            base_version: version to copy from (None = copy from current)
            description: description
        """
        if not self.current_workspace_id:
            logger.error("No workspace loaded")
            return False

        # Save current version first
        self.save_workspace()

        # Use current version as base if not specified
        if base_version is None:
            base_version = self.current_version

        # Create new version
        success = self.main_window.workspace_manager.create_version(
            self.current_workspace_id,
            new_version,
            base_version,
            description
        )
        
        if success:
            # Switch to new version
            self.switch_version(new_version)
        
        return success
    
    def switch_version(self, version: str) -> bool:
        """Switch to another version"""
        if not self.current_workspace_id:
            logger.error("No workspace loaded")
            return False

        # Save current version first
        self.save_workspace()

        # Load new version
        return self.load_workspace(self.current_workspace_id, version)
    
    def get_workspace_info(self) -> Dict:
        """Get current workspace information"""
        if not self.current_workspace_id:
            return {}
        
        workspace_data = self.main_window.workspace_manager.load_workspace(
            self.current_workspace_id
        )
        
        if not workspace_data:
            return {}
        
        return {
            "id": self.current_workspace_id,
            "name": workspace_data["workspace"]["name"],
            "description": workspace_data["workspace"].get("description", ""),
            "source_folder": workspace_data["source"]["folder"],
            "current_version": self.current_version,
            "available_versions": workspace_data["versions"]["available"]
        }
    
    def get_version_stats(self) -> Dict:
        """Get statistics of current version"""
        if not self.version_data:
            return {}

        return self.version_data.get("metadata", {})

    def delete_version(self, version: str) -> tuple:
        """
        Delete version

        Args:
            version: version to delete

        Returns:
            (success: bool, message: str)
        """
        if not self.current_workspace_id:
            return False, "No workspace loaded"

        # Call delete_version from workspace_manager
        success, message = self.main_window.workspace_manager.delete_version(
            self.current_workspace_id,
            version
        )

        return success, message

    def get_version_list(self):
        """
        Get list of all versions in current workspace

        Returns:
            List of version info dicts
        """
        if not self.current_workspace_id:
            return []

        return self.main_window.workspace_manager.get_version_list(
            self.current_workspace_id
        )

    def rename_workspace(self, new_name: str) -> tuple:
        """
        Rename current workspace

        Args:
            new_name: new name

        Returns:
            (success: bool, message: str)
        """
        if not self.current_workspace_id:
            return False, "No workspace loaded"

        # Call rename_workspace from workspace_manager
        success, message = self.main_window.workspace_manager.rename_workspace(
            self.current_workspace_id,
            new_name
        )

        return success, message

    def delete_workspace(self, workspace_id: str = None) -> bool:
        """
        Delete workspace

        Args:
            workspace_id: workspace id to delete (None = delete current workspace)

        Returns:
            success: bool
        """
        if workspace_id is None:
            workspace_id = self.current_workspace_id

        if not workspace_id:
            logger.error("No workspace specified")
            return False

        # If deleting currently open workspace, clear state
        if workspace_id == self.current_workspace_id:
            self.current_workspace_id = None
            self.current_version = None
            self.version_data = None
            self.main_window.annotations = {}
            self.main_window.image_rotations = {}

        # Call delete_workspace from workspace_manager
        return self.main_window.workspace_manager.delete_workspace(workspace_id)