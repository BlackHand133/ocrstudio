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


def imwrite_unicode(filepath: str, img: np.ndarray, params=None, image_format: str = None) -> bool:
    """
    Write image with Unicode path support.

    This function writes images to paths containing Unicode characters,
    which cv2.imwrite() cannot handle directly.

    Args:
        filepath: Output file path (supports Unicode)
        img: numpy array of image
        params: Encoding parameters (optional)
                Default: JPEG quality 95 for JPG, PNG compression 3 for PNG
        image_format: Image format override ('jpg' or 'png')
                     If None, will detect from filepath extension

    Returns:
        True if successful, False otherwise

    Example:
        >>> img = np.zeros((100, 100, 3), dtype=np.uint8)
        >>> success = imwrite_unicode("D:/รูปภาพ/output.jpg", img)
        >>> print(success)
        True

        >>> # Force PNG format
        >>> success = imwrite_unicode("D:/รูปภาพ/output.png", img, image_format='png')
        >>> print(success)
        True
    """
    try:
        # Get file extension
        if image_format:
            ext = image_format.lower()
        else:
            ext = filepath.split('.')[-1].lower()

        # Validate extension
        if ext not in ['jpg', 'jpeg', 'png', 'bmp', 'jfif', 'tiff', 'tif', 'webp']:
            ext = 'jpg'

        # Set default encoding params based on format
        if params is None:
            if ext in ['jpg', 'jpeg', 'jfif']:
                # JPEG: Quality 95 (0-100, higher = better quality)
                params = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            elif ext == 'png':
                # PNG: Compression 3 (0-9, higher = smaller file but slower)
                params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]
            elif ext == 'webp':
                # WebP: Quality 95
                params = [int(cv2.IMWRITE_WEBP_QUALITY), 95]
            else:
                # Default for other formats
                params = []

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
