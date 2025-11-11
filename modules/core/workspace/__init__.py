"""
Workspace management package.

This package provides workspace and version control functionality:
- WorkspaceManager: High-level workspace operations
- VersionManager: Version control operations
- WorkspaceStorage: Low-level storage operations

Usage:
    from modules.core.workspace import WorkspaceManager

    # Create manager
    manager = WorkspaceManager(root_dir)

    # Create workspace
    manager.create_workspace("my_workspace", "My Workspace", "/path/to/images")

    # Load workspace
    data = manager.load_workspace("my_workspace")

    # Version operations
    manager.create_version("my_workspace", "v2", source_version="v1")
    manager.switch_version("my_workspace", "v2")
    versions = manager.get_version_list("my_workspace")
"""

from modules.core.workspace.manager import WorkspaceManager
from modules.core.workspace.version import VersionManager
from modules.core.workspace.storage import WorkspaceStorage

__all__ = ['WorkspaceManager', 'VersionManager', 'WorkspaceStorage']
