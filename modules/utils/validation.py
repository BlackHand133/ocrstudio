"""
Data validation and sanitization utilities.

This module provides functions for:
- Type conversion (numpy → Python native)
- Data sanitization
- Filename cleaning
"""

import re
import logging
import numpy as np

logger = logging.getLogger("TextDetGUI")


def sanitize_annotation(annotation: dict) -> dict:
    """
    Convert numpy types to Python native types for JSON serialization.

    This function recursively converts:
    - numpy integers → int
    - numpy floats → float
    - numpy arrays → list
    - Qt objects with to_dict() → dict

    Args:
        annotation: Dict that may contain numpy types or Qt objects

    Returns:
        Dict with only Python native types

    Example:
        >>> import numpy as np
        >>> ann = {"points": np.array([[1, 2], [3, 4]]), "score": np.float32(0.95)}
        >>> clean = sanitize_annotation(ann)
        >>> print(type(clean["points"]))
        <class 'list'>
    """
    def convert_value(val):
        """Convert single value"""
        # Check if Qt object with to_dict() method
        if hasattr(val, 'to_dict') and callable(getattr(val, 'to_dict')):
            return convert_value(val.to_dict())
        elif isinstance(val, (np.integer, np.int32, np.int64)):
            return int(val)
        elif isinstance(val, (np.floating, np.float32, np.float64)):
            return float(val)
        elif isinstance(val, np.ndarray):
            return val.tolist()
        elif isinstance(val, list):
            return [convert_value(v) for v in val]
        elif isinstance(val, dict):
            return {k: convert_value(v) for k, v in val.items()}
        else:
            return val

    return convert_value(annotation)


def sanitize_annotations(annotations: list) -> list:
    """
    Sanitize list of annotations.

    Applies sanitize_annotation() to each annotation in the list.

    Args:
        annotations: List of annotation dicts

    Returns:
        List of sanitized annotation dicts

    Example:
        >>> anns = [{"id": np.int32(1)}, {"id": np.int32(2)}]
        >>> clean = sanitize_annotations(anns)
        >>> print(type(clean[0]["id"]))
        <class 'int'>
    """
    return [sanitize_annotation(ann) for ann in annotations]


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    Clean filename by replacing spaces and special characters.

    This prevents issues in ML/DL training systems that don't handle
    special characters well.

    Rules:
    - Replace spaces and special chars with replacement character
    - Keep only: letters (Unicode), digits, underscore, hyphen
    - Remove duplicate underscores
    - Strip leading/trailing underscores

    Args:
        filename: Filename to clean
        replacement: Replacement character (default: '_')

    Returns:
        Cleaned filename

    Examples:
        >>> sanitize_filename("my file.jpg")
        'my_file.jpg'
        >>> sanitize_filename("image (1).png")
        'image_1_.png'
        >>> sanitize_filename("test + demo.jpg")
        'test_demo.jpg'
        >>> sanitize_filename("ภาพที่ 1.jpg")
        'ภาพที่_1.jpg'
    """
    # Split name and extension
    parts = filename.rsplit('.', 1)
    name = parts[0]
    ext = parts[1] if len(parts) > 1 else ''

    # Replace spaces and special characters
    # Keep only: word characters (including Unicode), hyphen
    name = re.sub(r'[^\w\-]+', replacement, name, flags=re.UNICODE)

    # Remove duplicate underscores
    name = re.sub(r'_+', '_', name)

    # Strip leading/trailing underscores
    name = name.strip('_')

    # Reconstruct filename
    if ext:
        return f"{name}.{ext}"
    else:
        return name
