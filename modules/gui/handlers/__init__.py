"""
GUI handlers package.

This package contains GUI-specific handlers that coordinate between
the GUI layer and business logic layer.

Handlers:
- AnnotationHandler: Annotation management
- ImageHandler: Image loading and display
- WorkspaceHandler: Workspace operations
- DetectionHandler: Text detection
- RotationHandler: Image rotation
- TableHandler: Table/list management
- UIHandler: UI state management
- CacheHandler: Image caching
- ExportHandler: Export operations (detection/recognition)

Usage:
    from modules.gui.handlers import (
        AnnotationHandler,
        ImageHandler,
        WorkspaceHandler,
        ExportHandler
    )
"""

# Import handlers for convenience (optional - can import directly)
# This allows: from modules.gui.handlers import AnnotationHandler
# Instead of: from modules.gui.handlers.annotation import AnnotationHandler

__all__ = [
    'annotation',
    'image',
    'workspace',
    'detection',
    'rotation',
    'table',
    'ui',
    'cache',
    'export',
]
