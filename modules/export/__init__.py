"""
Export system for text detection and recognition datasets.

This package provides export functionality for:
- Detection datasets (text detection with bounding boxes)
- Recognition datasets (cropped text images for OCR)
- Various format handlers (PaddleOCR, YOLO, etc.)

Usage:
    from modules.export import DetectionExporter, RecognitionExporter

    # Detection export
    det_exporter = DetectionExporter(main_window)
    det_exporter.export(output_dir, split_config, aug_config)

    # Recognition export
    rec_exporter = RecognitionExporter(main_window)
    rec_exporter.export(output_dir, split_config, aug_config, crop_method)
"""

# ExportValidationError and the image utils are Qt-free and safe to import eagerly.
from modules.export.utils import ExportValidationError

# DetectionExporter / RecognitionExporter import PyQt5, so they are loaded lazily
# via PEP 562 __getattr__. This lets the headless web backend import
# ``modules.export.utils`` (cropping, masks, splitting helpers) without pulling
# in Qt, while ``from modules.export import DetectionExporter`` still works in the
# desktop app.
_LAZY = {
    "BaseExporter": "base",
    "DetectionExporter": "detection",
    "RecognitionExporter": "recognition",
}


def __getattr__(name):
    if name in _LAZY:
        from importlib import import_module

        module = import_module(f"modules.export.{_LAZY[name]}")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'BaseExporter',
    'DetectionExporter',
    'RecognitionExporter',
    'ExportValidationError',
]
