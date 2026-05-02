# modules/detector.py
#
# COMPATIBILITY SHIM — DO NOT ADD CODE HERE.
# The canonical implementation lives at modules/core/ocr/detector.py
#
# This file exists only for backward compatibility.
# All new code should import from the canonical path:
#
#   from modules.core.ocr import TextDetector
#   from modules.core.ocr.detector import TextDetector, OCRDetector

from modules.core.ocr.detector import TextDetector, OCRDetector  # noqa: F401
