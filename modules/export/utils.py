"""
Image processing utilities for export operations.

This module provides reusable image processing functions:
- Mask handling
- Orientation detection
- Image cropping (rotated and bounding box)
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger("TextDetGUI")


def is_valid_box(pts) -> bool:
    """
    Check if points are valid for bounding box.

    Args:
        pts: List of points

    Returns:
        bool: True if valid
    """
    if not (isinstance(pts, list) and len(pts) >= 4):
        return False
    for p in pts:
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            return False
    return True


def is_mask_item(ann: Dict) -> bool:
    """
    Check if annotation is a mask item.

    Args:
        ann: Annotation dict

    Returns:
        bool: True if it's a mask item
    """
    shape = ann.get('shape', '')
    transcription = ann.get('transcription', '')

    # Check shape or transcription
    return 'Mask' in shape or transcription == '###'


def draw_masks_on_image(img: np.ndarray, mask_items: List[Dict]) -> np.ndarray:
    """
    Draw mask items on image to hide certain parts.

    Args:
        img: numpy array of image in BGR format
        mask_items: list of mask annotations

    Returns:
        numpy array of image with masks drawn
    """
    if not mask_items:
        return img

    img_copy = img.copy()

    for mask in mask_items:
        pts = mask.get('points', [])
        if not is_valid_box(pts):
            continue

        # Convert points to numpy array
        points = np.array(pts, dtype=np.int32)

        # Get mask_color (default black if not specified)
        mask_color_hex = mask.get('mask_color', '#000000')
        # Convert hex to RGB
        mask_color_hex = mask_color_hex.lstrip('#')
        r = int(mask_color_hex[0:2], 16)
        g = int(mask_color_hex[2:4], 16)
        b = int(mask_color_hex[4:6], 16)
        color_bgr = (b, g, r)  # OpenCV uses BGR

        # Draw filled polygon on image
        cv2.fillPoly(img_copy, [points], color_bgr)

    return img_copy


def detect_upside_down_with_model(img: np.ndarray, orientation_classifier=None) -> bool:
    """
    Detect upside-down using PaddlePaddle orientation model.

    Args:
        img: numpy array of image (BGR format)
        orientation_classifier: Orientation classifier instance

    Returns:
        bool: True if should rotate 180 degrees
    """
    if orientation_classifier is None:
        # Fallback to heuristic method
        return detect_upside_down_advanced(img)

    try:
        should_flip = orientation_classifier.should_flip_180(img, confidence_threshold=0.6)
        logger.debug(f"Model-based upside-down detection: flip={should_flip}")
        return should_flip
    except Exception as e:
        logger.error(f"Model-based detection failed: {e}, using fallback")
        return detect_upside_down_advanced(img)


def detect_upside_down_advanced(img: np.ndarray) -> bool:
    """
    Advanced heuristic for detecting upside-down images.

    Techniques:
    1. Edge distribution analysis (horizontal edges)
    2. Variance analysis (top vs bottom)
    3. Content distribution
    4. Text region centroid analysis

    Args:
        img: numpy array of image

    Returns:
        bool: True if should rotate 180 degrees
    """
    try:
        if img is None or img.size == 0:
            return False

        h, w = img.shape[:2]

        # Skip small images
        if h < 20 or w < 20:
            return False

        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        votes = 0  # Number of votes for rotating 180 degrees

        # Method 1: Edge Distribution (weight 2)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobelx_abs = np.abs(sobelx)

        mid = h // 2
        top_edge = np.mean(sobelx_abs[:mid, :])
        bottom_edge = np.mean(sobelx_abs[mid:, :])

        if top_edge > bottom_edge * 1.3:
            votes += 2
        elif bottom_edge > top_edge * 1.3:
            votes -= 2

        # Method 2: Variance Distribution (weight 1)
        top_var = np.var(gray[:mid, :])
        bottom_var = np.var(gray[mid:, :])

        if top_var > bottom_var * 1.2:
            votes += 1
        elif bottom_var > top_var * 1.2:
            votes -= 1

        # Method 3: Content Mass Distribution (weight 1)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Count pixels in top and bottom regions
        top_content = np.sum(binary[:mid, :] < 128)
        bottom_content = np.sum(binary[mid:, :] < 128)

        if top_content > bottom_content * 1.3:
            votes += 1
        elif bottom_content > top_content * 1.3:
            votes -= 1

        # Method 4: Text region centroid analysis (weight 2)
        _, text_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(text_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        y_centroids = []
        areas = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 5:  # ignore small noise
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cy = M["m01"] / M["m00"]
                    y_centroids.append(cy)
                    areas.append(area)
        if y_centroids:
            total_area = sum(areas)
            if total_area > 0:
                weighted_y = sum(y * a for y, a in zip(y_centroids, areas)) / total_area
                h_loc = gray.shape[0]
                if weighted_y < h_loc / 2 * 1.1:  # text centroids too high
                    votes += 2
                else:
                    votes -= 2

        # Decision rule: if votes >= 3 = should rotate 180
        should_rotate = votes >= 3

        logger.debug(f"Upside-down detection: votes={votes}, rotate={should_rotate}")

        return should_rotate

    except Exception as e:
        logger.error(f"Failed advanced upside-down detection: {e}")
        return False


def select_best_orientation(img: np.ndarray, auto_orient: bool = True,
                           orientation_classifier=None) -> Tuple[np.ndarray, int]:
    """
    Select best orientation for text with LTR assumption using ML-first approach.

    1. Check if portrait (H > W) → rotate to landscape (90° or 270°)
       - Try both 90° and 270°, use ML to pick the right one
    2. Use ML model to detect if upside-down, flip 180° if needed

    Args:
        img: numpy array of image (BGR format)
        auto_orient: if True, perform auto orientation
        orientation_classifier: Orientation classifier instance

    Returns:
        tuple: (oriented_img, final_angle)
    """
    if not auto_orient or img is None:
        return img, 0

    h, w = img.shape[:2]
    if min(h, w) < 20:
        return img, 0

    # Check if portrait
    is_portrait = h > w * 1.1  # 10% threshold

    best_img = img.copy()
    angle_applied = 0

    if is_portrait:
        # Portrait mode: need to rotate to landscape
        logger.debug(f"Image is portrait ({h}x{w}), converting to landscape")

        # Try 90° first (counterclockwise)
        img_90 = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        should_flip_90 = detect_upside_down_with_model(img_90, orientation_classifier)

        # Try 270° (clockwise)
        img_270 = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        should_flip_270 = detect_upside_down_with_model(img_270, orientation_classifier)

        # Choose the one that doesn't need flipping
        if should_flip_270 and not should_flip_90:
            best_img = img_90
            angle_applied = 90
        elif should_flip_90 and not should_flip_270:
            best_img = img_270
            angle_applied = 270
        else:
            # Both same, default to 90° and check if need flip
            best_img = img_90
            angle_applied = 90
            if should_flip_90:
                best_img = cv2.rotate(best_img, cv2.ROTATE_180)
                angle_applied = 270
    else:
        # Already landscape or square
        logger.debug(f"Image is landscape ({h}x{w}), checking orientation")

        # Just check if upside-down
        should_flip = detect_upside_down_with_model(img, orientation_classifier)
        if should_flip:
            best_img = cv2.rotate(img, cv2.ROTATE_180)
            angle_applied = 180
        else:
            best_img = img
            angle_applied = 0

    # Final check: ensure result is landscape
    final_h, final_w = best_img.shape[:2]
    if final_h > final_w * 1.1:
        logger.warning(f"Result still portrait ({final_h}x{final_w}), forcing 90° rotation")
        best_img = cv2.rotate(best_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        angle_applied = (angle_applied + 90) % 360

    logger.debug(f"ML-based orientation: {angle_applied}° applied")

    return best_img, angle_applied


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Arrange points into: top-left, top-right, bottom-right, bottom-left.

    Method:
    - Sort points by y-coordinate (top first)
    - Arrange top and bottom points by x (left to right)

    Args:
        pts: numpy array shape (4, 2)

    Returns:
        numpy array shape (4, 2) arranged as [TL, TR, BR, BL]
    """
    # Convert to list of tuples for sorting
    pts_list = [(pt[0], pt[1]) for pt in pts]

    # Sort points by y, then by x
    pts_list.sort(key=lambda p: (p[1], p[0]))

    # First 2 points are top row, last 2 are bottom row
    top_points = pts_list[:2]
    bottom_points = pts_list[2:]

    # Arrange by x (left to right)
    top_points.sort(key=lambda p: p[0])
    tl, tr = top_points

    bottom_points.sort(key=lambda p: p[0])
    bl, br = bottom_points

    # Create numpy array in order: TL, TR, BR, BL
    ordered = np.array([tl, tr, br, bl], dtype=np.float32)

    return ordered


def crop_rotated_box(img: np.ndarray, pts: List, auto_detect: bool = True,
                     orientation_classifier=None) -> Optional[np.ndarray]:
    """
    Crop image according to rotated rectangle and transform to straight.

    Uses 2 methods:
    1. If exactly 4 corners -> use perspective transform directly
    2. If more/less than 4 points -> use minimum area rectangle

    Args:
        img: numpy array of image (BGR format)
        pts: list of points [[x1,y1], [x2,y2], ...]
        auto_detect: use auto-detection for post-processing
        orientation_classifier: Orientation classifier instance

    Returns:
        numpy array of cropped straightened image, or None if failed
    """
    try:
        # Validate input
        if img is None or not isinstance(pts, list) or len(pts) < 3:
            logger.error("Invalid input for rotated crop")
            return None

        # Convert points to numpy array
        points = np.array(pts, dtype=np.float32)

        # Method 1: If exactly 4 points -> direct perspective transform
        if len(points) == 4:
            logger.debug("Using 4-point direct perspective transform")

            # Arrange points
            rect = order_points(points)

            # Calculate width and height
            width_top = np.linalg.norm(rect[1] - rect[0])
            width_bottom = np.linalg.norm(rect[2] - rect[3])
            max_width = max(int(width_top), int(width_bottom))

            height_left = np.linalg.norm(rect[3] - rect[0])
            height_right = np.linalg.norm(rect[2] - rect[1])
            max_height = max(int(height_left), int(height_right))

            # Validate size
            if max_width < 1 or max_height < 1:
                logger.error(f"Invalid calculated size: {max_width}x{max_height}")
                return None

            # Create destination points (straight rectangle)
            dst_points = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype=np.float32)

            # Calculate transformation matrix
            M = cv2.getPerspectiveTransform(rect, dst_points)

            # Perform perspective transform
            warped = cv2.warpPerspective(img, M, (max_width, max_height))

            # Post-process for orientation
            warped, _ = select_best_orientation(warped, auto_orient=auto_detect,
                                               orientation_classifier=orientation_classifier)

            return warped

        # Method 2: Use minimum area rectangle
        else:
            logger.debug(f"Using minAreaRect for {len(points)} points")

            # Find minimum area rectangle
            rect = cv2.minAreaRect(points)

            # Returns (center, (width, height), angle)
            (cx, cy), (w, h), angle = rect

            # Validate size
            if w < 1 or h < 1:
                logger.error(f"Invalid rectangle size: {w}x{h}")
                return None

            # Get 4 corners
            box = cv2.boxPoints(rect)
            box = box.astype(np.float32)

            # Arrange points
            box_sorted = order_points(box)

            # Calculate size
            dst_w = int(w)
            dst_h = int(h)

            if dst_w < 1 or dst_h < 1:
                logger.error(f"Invalid destination size: {dst_w}x{dst_h}")
                return None

            # Create destination points
            dst_points = np.array([
                [0, 0],
                [dst_w - 1, 0],
                [dst_w - 1, dst_h - 1],
                [0, dst_h - 1]
            ], dtype=np.float32)

            # Calculate transformation matrix
            M = cv2.getPerspectiveTransform(box_sorted, dst_points)

            # Perform perspective transform
            warped = cv2.warpPerspective(img, M, (dst_w, dst_h))

            # Post-process for orientation
            warped, _ = select_best_orientation(warped, auto_orient=auto_detect,
                                               orientation_classifier=orientation_classifier)

            return warped

    except Exception as e:
        logger.error(f"Failed to crop rotated box: {e}", exc_info=True)
        return None


def crop_bounding_box(img: np.ndarray, pts: List, auto_detect: bool = True,
                     orientation_classifier=None) -> Optional[np.ndarray]:
    """
    Crop image according to bounding box (axis-aligned, no rotation).

    Args:
        img: numpy array of image (BGR format)
        pts: list of points [[x1,y1], [x2,y2], ...]
        auto_detect: use auto-detection for post-processing
        orientation_classifier: Orientation classifier instance

    Returns:
        numpy array of cropped image, or None if failed
    """
    try:
        h, w = img.shape[:2]

        # Find bounding box
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x1, y1 = int(min(xs)), int(min(ys))
        x2, y2 = int(max(xs)), int(max(ys))

        # Clip to image bounds
        x1, y1 = max(0, min(x1, w)), max(0, min(y1, h))
        x2, y2 = max(0, min(x2, w)), max(0, min(y2, h))

        if x2 <= x1 or y2 <= y1:
            return None

        # Crop
        crop = img[y1:y2, x1:x2]

        # Post-process for orientation
        crop, _ = select_best_orientation(crop, auto_orient=auto_detect,
                                         orientation_classifier=orientation_classifier)

        return crop

    except Exception as e:
        logger.error(f"Failed to crop bounding box: {e}")
        return None
