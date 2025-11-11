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

from modules.export.base import BaseExporter
from modules.export.detection import DetectionExporter
from modules.export.recognition import RecognitionExporter

__all__ = [
    'BaseExporter',
    'DetectionExporter',
    'RecognitionExporter'
]
