"""
File I/O utilities with Unicode support.

This module provides file operations that support Unicode paths:
- Image reading (imread_unicode)
- Image writing (imwrite_unicode)
- Unicode-safe operations for Thai, Chinese, etc.
"""

import logging
import cv2
import numpy as np

logger = logging.getLogger("TextDetGUI")


def imread_unicode(filepath: str) -> np.ndarray:
    """
    Read image with Unicode path support (Thai, Chinese, etc.).

    This function reads images from paths containing Unicode characters,
    which cv2.imread() cannot handle directly.

    Args:
        filepath: Image file path (supports Unicode)

    Returns:
        numpy array of image (BGR format), or None if failed

    Example:
        >>> img = imread_unicode("D:/รูปภาพ/test.jpg")
        >>> print(img.shape)
        (480, 640, 3)
    """
    try:
        # Read file as bytes
        with open(filepath, 'rb') as f:
            file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)

        # Decode to image
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        return img

    except Exception as e:
        logger.error(f"Failed to read image {filepath}: {e}")
        return None


def imwrite_unicode(filepath: str, img: np.ndarray, params=None) -> bool:
    """
    Write image with Unicode path support.

    This function writes images to paths containing Unicode characters,
    which cv2.imwrite() cannot handle directly.

    Args:
        filepath: Output file path (supports Unicode)
        img: numpy array of image
        params: Encoding parameters (optional)
                Default: JPEG quality 95

    Returns:
        True if successful, False otherwise

    Example:
        >>> img = np.zeros((100, 100, 3), dtype=np.uint8)
        >>> success = imwrite_unicode("D:/รูปภาพ/output.jpg", img)
        >>> print(success)
        True
    """
    try:
        # Get file extension
        ext = filepath.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'bmp']:
            ext = 'jpg'

        # Set default encoding params
        if params is None:
            params = [int(cv2.IMWRITE_JPEG_QUALITY), 95]

        # Encode image
        success, encoded = cv2.imencode(f'.{ext}', img, params)

        if not success:
            return False

        # Write to file
        with open(filepath, 'wb') as f:
            f.write(encoded.tobytes())

        return True

    except Exception as e:
        logger.error(f"Failed to write image {filepath}: {e}")
        return False
