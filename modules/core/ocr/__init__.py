"""
OCR (Optical Character Recognition) module.

This package provides text detection and recognition capabilities using PaddleOCR.

Main classes:
    - TextDetector: Main OCR detector for text detection and recognition
    - OCRDetector: Alias for backward compatibility
    - TextlineOrientationClassifier: Textline orientation classifier (0° vs 180°)

The classes above are resolved lazily (PEP 562): importing them pulls in cv2 and
paddle, which costs seconds. Config loading only needs the pure-Python
compatibility helpers in :mod:`modules.core.ocr.compat`, so those are exported
eagerly and everything heavy is deferred until first use.
"""

import importlib
from typing import Any

from modules.core.ocr.compat import (
    OCR_VERSIONS,
    PARAM_ALIASES,
    engine_version,
    explain_unsupported,
    normalize_params,
    supported_langs,
    version_supports_lang,
    versions_for_lang,
)

_LAZY_ATTRS = {
    'TextDetector': ('modules.core.ocr.detector', 'TextDetector'),
    'OCRDetector': ('modules.core.ocr.detector', 'OCRDetector'),
    'TextlineOrientationClassifier': (
        'modules.core.ocr.orientation',
        'TextlineOrientationClassifier',
    ),
}


def __getattr__(name: str) -> Any:
    """Import the heavy OCR classes on first access."""
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = target
    value = getattr(importlib.import_module(module_name), attr_name)
    globals()[name] = value  # cache so __getattr__ only runs once
    return value


def __dir__() -> list:
    return sorted(list(globals()) + list(_LAZY_ATTRS))


__all__ = [
    'TextDetector',
    'OCRDetector',
    'TextlineOrientationClassifier',
    'OCR_VERSIONS',
    'PARAM_ALIASES',
    'engine_version',
    'explain_unsupported',
    'normalize_params',
    'supported_langs',
    'version_supports_lang',
    'versions_for_lang',
]
