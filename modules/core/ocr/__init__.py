"""
OCR (Optical Character Recognition) module.

This package provides text detection and recognition capabilities using PaddleOCR.

Main classes:
    - TextDetector: Main OCR detector for text detection and recognition
    - OCRDetector: Alias for backward compatibility
    - TextlineOrientationClassifier: Textline orientation classifier (0° vs 180°)
"""

from modules.core.ocr.detector import TextDetector, OCRDetector
from modules.core.ocr.orientation import TextlineOrientationClassifier

__all__ = ['TextDetector', 'OCRDetector', 'TextlineOrientationClassifier']
