"""
Image processing utilities.

This module provides image manipulation functions:
- Point clipping
- Coordinate validation
- Image transformations
"""

import logging

logger = logging.getLogger("TextDetGUI")


def clip_points_to_image(points: list, image_width: int, image_height: int) -> list:
    """
    Clip points to image boundaries.

    Ensures all points are within valid image coordinates.

    Args:
        points: List of [x, y] coordinates
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        List of clipped [x, y] coordinates

    Example:
        >>> points = [[10, 20], [1000, 500], [-5, 30]]
        >>> clipped = clip_points_to_image(points, 800, 600)
        >>> print(clipped)
        [[10, 20], [800, 500], [0, 30]]
    """
    clipped_points = []

    for point in points:
        x, y = point[0], point[1]

        # Clip to valid range [0, width] and [0, height]
        x_clipped = max(0, min(x, image_width))
        y_clipped = max(0, min(y, image_height))

        clipped_points.append([x_clipped, y_clipped])

    return clipped_points
