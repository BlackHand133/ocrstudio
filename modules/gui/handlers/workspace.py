# modules/gui/handlers/workspace.py

import logging
from copy import deepcopy
from typing import Optional, Dict

from modules.utils import sanitize_annotations

logger = logging.getLogger("TextDetGUI")


class WorkspaceHandler:
    """
    Manage Workspace and Version for MainWindow.

    Data access goes through self.state (AppState).
    Backend operations go through self.services.workspace_manager.
    """

    def __init__(self, state, services, main_window):
        """
        Args:
            state:       AppState instance — source of truth for business data.
            services:    Services container (workspace_manager, detector, undo_manager).
            main_window: MainWindow reference — used only for Qt widget access.
        """
        self.state       = state
        self.services    = services
        self.main_window = main_window

        self.current_workspace_id: Optional[str] = None
        self.current_version:      Optional[str] = None
        self.version_data:         Optional[Dict] = None
        self.is_saved:             bool = True

    # ---------------------------------------------------------------------- load

    def load_workspace(self, workspace_id: str, version: Optional[str] = None) -> bool:
        """
        Load workspace and version data into AppState.

        Args:
            workspace_id: Workspace identifier.
            version:      Version name (None = use current version).

        Returns:
            True on success, False on failure.
        """
        try:
            workspace_data = self.services.workspace_manager.load_workspace(workspace_id)
            if not workspace_data:
                logger.error(f"Failed to load workspace: {workspace_id}")
                return False

            if version is None:
                version = workspace_data["versions"]["current"]

            version_data = self.services.workspace_manager.load_version(workspace_id, version)
            if not version_data:
                logger.error(f"Failed to load version: {version}")
                return False

            self.current_workspace_id = workspace_id
            self.current_version      = version
            self.version_data         = version_data

            # Push data into AppState (the single source of truth)
            self.state.annotations     = version_data.get("annotations", {})
            self.state.image_rotations = version_data.get("transforms", {})

            # Persist recently-used workspace
            self.services.workspace_manager.app_config["current_workspace"] = workspace_id
            self.services.workspace_manager.save_app_config()
            self.services.workspace_manager.add_recent_workspace(workspace_id)

            logger.info(f"Loaded workspace: {workspace_id}, version: {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to load workspace: {e}")
            return False

    # ---------------------------------------------------------------------- save

    def save_workspace(self) -> bool:
        """Save current workspace state from AppState to disk."""
        if not self.current_workspace_id or not self.current_version:
            logger.warning("No workspace loaded — nothing to save")
            return False

        try:
            if self.version_data is None:
                logger.error("No version data loaded — cannot save workspace")
                return False

            sanitized = {
                key: sanitize_annotations(anns)
                for key, anns in self.state.annotations.items()
            }

            self.version_data["annotations"] = sanitized
            self.version_data["transforms"]  = deepcopy(self.state.image_rotations)

            success = self.services.workspace_manager.save_version(
                self.current_workspace_id,
                self.current_version,
                self.version_data,
            )
            if success:
                logger.debug(f"Saved workspace: {self.current_workspace_id}")
            return success

        except Exception as e:
            logger.error(f"Failed to save workspace: {e}")
            return False

    # ---------------------------------------------------------------------- versions

    def create_new_version(
        self,
        new_version: str,
        base_version: Optional[str] = None,
        description: str = "",
    ) -> bool:
        if not self.current_workspace_id:
            logger.error("No workspace loaded")
            return False

        self.save_workspace()

        if base_version is None:
            base_version = self.current_version

        success = self.services.workspace_manager.create_version(
            self.current_workspace_id,
            new_version,
            base_version,
            description,
        )
        if success:
            self.switch_version(new_version)
        return success

    def switch_version(self, version: str) -> bool:
        if not self.current_workspace_id:
            logger.error("No workspace loaded")
            return False

        if version == self.current_version:
            logger.info(f"Already on version {version}")
            return True

        # Stash current state for rollback
        old_version     = self.current_version
        old_annotations = deepcopy(self.state.annotations)
        old_rotations   = deepcopy(self.state.image_rotations)

        try:
            if not self.save_workspace():
                logger.error("Failed to save current version before switch")
                return False

            if self.load_workspace(self.current_workspace_id, version):
                logger.info(f"Switched '{old_version}' → '{version}'")
                return True

            # Rollback
            logger.error(f"Failed to load version '{version}', rolling back")
            self.current_version       = old_version
            self.state.annotations     = old_annotations
            self.state.image_rotations = old_rotations
            return False

        except Exception as e:
            logger.error(f"Exception during version switch: {e}", exc_info=True)
            self.current_version       = old_version
            self.state.annotations     = old_annotations
            self.state.image_rotations = old_rotations
            return False

    def delete_version(self, version: str):
        if not self.current_workspace_id:
            return False, "No workspace loaded"
        return self.services.workspace_manager.delete_version(
            self.current_workspace_id, version
        )

    def get_version_list(self):
        if not self.current_workspace_id:
            return []
        return self.services.workspace_manager.get_version_list(
            self.current_workspace_id
        )

    # ---------------------------------------------------------------------- workspace ops

    def get_workspace_info(self) -> Dict:
        if not self.current_workspace_id:
            return {}
        workspace_data = self.services.workspace_manager.load_workspace(
            self.current_workspace_id
        )
        if not workspace_data:
            return {}
        return {
            "id":                self.current_workspace_id,
            "name":              workspace_data["workspace"]["name"],
            "description":       workspace_data["workspace"].get("description", ""),
            "source_folder":     workspace_data["source"]["folder"],
            "current_version":   self.current_version,
            "available_versions": workspace_data["versions"]["available"],
        }

    def get_version_stats(self) -> Dict:
        if not self.version_data:
            return {}
        return self.version_data.get("metadata", {})

    def rename_workspace(self, new_name: str):
        if not self.current_workspace_id:
            return False, "No workspace loaded"
        return self.services.workspace_manager.rename_workspace(
            self.current_workspace_id, new_name
        )

    def delete_workspace(self, workspace_id: Optional[str] = None) -> bool:
        if workspace_id is None:
            workspace_id = self.current_workspace_id
        if not workspace_id:
            logger.error("No workspace specified")
            return False

        if workspace_id == self.current_workspace_id:
            self.current_workspace_id  = None
            self.current_version       = None
            self.version_data          = None
            self.state.annotations     = {}
            self.state.image_rotations = {}

        return self.services.workspace_manager.delete_workspace(workspace_id)
