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

# Decorators
from modules.utils.decorators import handle_exceptions

# File I/O
from modules.utils.file_io import imread_unicode, imwrite_unicode

# Image utilities
from modules.utils.image import clip_points_to_image

# Validation utilities
from modules.utils.validation import (
    sanitize_annotation,
    sanitize_annotations,
    sanitize_filename
)

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
