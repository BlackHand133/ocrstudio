"""
PaddleOCR format handlers.

This module provides utilities for PaddleOCR format:
- Detection label format
- Recognition label format
- Label file writing
"""

import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger("TextDetGUI")
PLACEHOLDER_TEXT = "<no_label>"


def format_detection_label(annotation: Dict) -> Dict:
    """
    Format annotation for PaddleOCR detection.

    Args:
        annotation: Annotation dict with points and transcription

    Returns:
        Formatted dict for detection
    """
    txt = annotation.get("transcription", "").strip() or PLACEHOLDER_TEXT

    return {
        "points": annotation["points"],
        "transcription": txt,
        "difficult": annotation.get("difficult", False)
    }


def format_recognition_label(text: str) -> str:
    """
    Format text for PaddleOCR recognition.

    Args:
        text: Transcription text

    Returns:
        Formatted text
    """
    return text.strip() or PLACEHOLDER_TEXT


def write_detection_label_file(file_path: str, labels: List[tuple]) -> bool:
    """
    Write detection label file in PaddleOCR format.

    Format: image_path\t[{"points": [[x1,y1],...], "transcription": "text", "difficult": false}]

    Args:
        file_path: Output file path
        labels: List of (rel_path, annotations) tuples

    Returns:
        bool: True if successful
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for rel_path, anns in labels:
                # Format annotations
                formatted = [format_detection_label(ann) for ann in anns]

                # Write line
                line = f"{rel_path}\t{json.dumps(formatted, ensure_ascii=False)}\n"
                f.write(line)

        logger.info(f"Wrote detection labels to {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to write detection labels to {file_path}: {e}")
        return False


def write_recognition_label_file(file_path: str, labels: List[tuple]) -> bool:
    """
    Write recognition label file in PaddleOCR format.

    Format: image_path\ttext

    Args:
        file_path: Output file path
        labels: List of (rel_path, text) tuples

    Returns:
        bool: True if successful
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for rel_path, text in labels:
                # Format text
                formatted_text = format_recognition_label(text)

                # Write line
                f.write(f"{rel_path}\t{formatted_text}\n")

        logger.info(f"Wrote recognition labels to {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to write recognition labels to {file_path}: {e}")
        return False


def validate_detection_annotation(annotation: Dict) -> bool:
    """
    Validate detection annotation format.

    Args:
        annotation: Annotation dict

    Returns:
        bool: True if valid
    """
    if not isinstance(annotation, dict):
        return False

    # Check required fields
    if 'points' not in annotation:
        return False

    points = annotation['points']
    if not isinstance(points, list) or len(points) < 4:
        return False

    # Check each point
    for pt in points:
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            return False

    return True
