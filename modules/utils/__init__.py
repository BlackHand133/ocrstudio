"""
Utility functions package.

This package provides various utility functions:
- Decorators: Exception handling, logging
- File I/O: Unicode-safe image reading/writing
- Image: Point clipping, transformations
- Validation: Data sanitization, filename cleaning

Usage:
    from modules.utils import handle_exceptions, imread_unicode, sanitize_filename

    @handle_exceptions
    def my_function():
        img = imread_unicode("path/to/ภาพ.jpg")
        filename = sanitize_filename("my file (1).jpg")
"""

# Decorators (Qt imported lazily inside the decorator itself)
from modules.utils.decorators import handle_exceptions

# Validation utilities (pure Python + numpy — always available)
from modules.utils.validation import (
    sanitize_annotation,
    sanitize_annotations,
    sanitize_filename,
)

# File I/O and image utilities require cv2 — import conditionally so that
# Qt-free / headless test environments don't fail on collection.
try:
    from modules.utils.file_io import imread_unicode, imwrite_unicode
    from modules.utils.image import clip_points_to_image
except ImportError:
    imread_unicode    = None  # type: ignore[assignment]
    imwrite_unicode   = None  # type: ignore[assignment]
    clip_points_to_image = None  # type: ignore[assignment]

__all__ = [
    # Decorators
    'handle_exceptions',

    # File I/O
    'imread_unicode',
    'imwrite_unicode',

    # Image utilities
    'clip_points_to_image',

    # Validation
    'sanitize_annotation',
    'sanitize_annotations',
    'sanitize_filename',
]
