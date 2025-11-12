"""
GUI Export Handler - Thin coordinator between GUI and export modules.

This module provides GUI-level coordination for export operations:
- Shows dialogs for user input
- Delegates to business logic exporters
- Handles UI-specific operations only
"""

import logging
from PyQt5 import QtWidgets

from modules.export.detection import DetectionExporter
from modules.export.recognition import RecognitionExporter
from modules.gui.dialogs.split_config_dialog import SplitConfigDialog
from modules.gui.dialogs.augmentation_dialog import AugmentationDialog
from modules.utils import handle_exceptions
from modules.constants import DEFAULT_EXPORT_IMAGE_FORMAT

logger = logging.getLogger("TextDetGUI")


class ExportHandler:
    """
    GUI coordinator for export operations.

    This is a thin wrapper that:
    1. Shows dialogs to get user configuration
    2. Delegates to DetectionExporter or RecognitionExporter
    3. Handles only GUI-specific logic
    """

    def __init__(self, main_window):
        """
        Initialize export handler.

        Args:
            main_window: Reference to MainWindow instance
        """
        self.main_window = main_window

        # Create exporters
        self.detection_exporter = DetectionExporter(main_window)
        self.recognition_exporter = RecognitionExporter(main_window)

        logger.info("ExportHandler initialized with new modular exporters")

    @handle_exceptions
    def save_labels_detection(self):
        """
        Export detection dataset.

        Shows dialogs for configuration, then delegates to DetectionExporter.
        """
        # Save current annotations
        self.main_window.annotation_handler.save_current_annotation()

        # Check if any annotations are selected
        keys = [
            k for k, ann in self.main_window.annotations.items()
            if ann and self.main_window.image_handler.is_item_checked(k)
        ]

        if not keys:
            QtWidgets.QMessageBox.information(
                self.main_window, "No Annotations",
                "No annotations selected for export"
            )
            return

        # Get folder name
        folder_name, ok = QtWidgets.QInputDialog.getText(
            self.main_window, "Save Detection Dataset",
            "Choose Dataset:",
            QtWidgets.QLineEdit.Normal, "dataset_det"
        )
        if not ok or not folder_name.strip():
            return
        folder_name = folder_name.strip()

        # Get split configuration
        dialog = SplitConfigDialog(self.main_window, mode='detection', total_items=len(keys))
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        config = dialog.result
        if not config:
            return

        # Get image format selection
        image_format = self._show_format_selection_dialog()
        if image_format is None:
            return  # User cancelled

        # Get augmentation configuration
        aug_config = None
        reply = QtWidgets.QMessageBox.question(
            self.main_window, 'Augmentation',
            'Apply Data Augmentation?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            aug_dialog = AugmentationDialog(self.main_window, mode='detection')
            if aug_dialog.exec_() == QtWidgets.QDialog.Accepted:
                aug_config = aug_dialog.result

        # Delegate to DetectionExporter
        self.detection_exporter.export(folder_name, config, aug_config, image_format)

    @handle_exceptions
    def export_recognition(self):
        """
        Export recognition dataset.

        Shows dialogs for configuration, then delegates to RecognitionExporter.
        """
        # Save current annotations
        self.main_window.annotation_handler.save_current_annotation()

        # Get folder name
        folder_name, ok = QtWidgets.QInputDialog.getText(
            self.main_window, "Export Recognition Dataset",
            "Choose Dataset:",
            QtWidgets.QLineEdit.Normal, "dataset_rec"
        )
        if not ok or not folder_name.strip():
            return
        folder_name = folder_name.strip()

        # Count crops
        crops_count = 0
        for key, full in self.main_window.image_items:
            if not self.main_window.image_handler.is_item_checked(key):
                continue
            for ann in self.main_window.annotations.get(key, []):
                # Skip mask items
                from modules.export import utils as export_utils
                if not export_utils.is_mask_item(ann):
                    crops_count += 1

        if crops_count == 0:
            QtWidgets.QMessageBox.information(
                self.main_window, "Export Rec",
                "No valid annotations for export\n(Mask items excluded)"
            )
            return

        # Get crop method and orientation options
        crop_result = self._show_crop_method_dialog()
        if crop_result[0] is None:
            return  # User cancelled

        crop_method, auto_detect = crop_result

        # Get split configuration
        dialog = SplitConfigDialog(self.main_window, mode='recognition', total_items=crops_count)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        config = dialog.result
        if not config:
            return

        # Get image format selection
        image_format = self._show_format_selection_dialog()
        if image_format is None:
            return  # User cancelled

        # Get augmentation configuration
        aug_config = None
        reply = QtWidgets.QMessageBox.question(
            self.main_window, 'Augmentation',
            'Apply Data Augmentation?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            aug_dialog = AugmentationDialog(self.main_window, mode='recognition')
            if aug_dialog.exec_() == QtWidgets.QDialog.Accepted:
                aug_config = aug_dialog.result

        # Delegate to RecognitionExporter
        self.recognition_exporter.export(
            folder_name, config, crop_method, auto_detect, aug_config, image_format
        )

    def _show_crop_method_dialog(self):
        """
        Show dialog to select crop method for Recognition export.

        Returns:
            tuple: (crop_method, auto_detect_orientation)
                - crop_method: 'rotated' or 'bbox' or None
                - auto_detect_orientation: True/False
        """
        dialog = QtWidgets.QDialog(self.main_window)
        dialog.setWindowTitle("Recognition Export - Options")
        dialog.setMinimumWidth(500)

        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("<b>Select options for Recognition Export:</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)

        # Crop Method Group
        crop_group = QtWidgets.QGroupBox("✅ Crop Method")
        crop_layout = QtWidgets.QVBoxLayout()

        radio_rotated = QtWidgets.QRadioButton("🔄 Auto-Straighten (Rotated Rectangle)")
        radio_rotated.setToolTip("Straighten rotated text lines and crop image automatically")
        radio_rotated.setChecked(True)

        radio_bbox = QtWidgets.QRadioButton("📦 Bounding Box (axis-aligned)")
        radio_bbox.setToolTip("Crop using bounding box without straightening image")

        crop_layout.addWidget(radio_rotated)
        crop_layout.addWidget(radio_bbox)
        crop_group.setLayout(crop_layout)
        layout.addWidget(crop_group)

        # Orientation Detection Group
        orient_group = QtWidgets.QGroupBox("🔍 Orientation Detection")
        orient_layout = QtWidgets.QVBoxLayout()

        check_auto_detect = QtWidgets.QCheckBox("🤖 Auto-Detect & Fix Orientation (recommended)")
        check_auto_detect.setChecked(True)
        check_auto_detect.setToolTip(
            "Detect and fix text orientation automatically (0/90/180/270°)\n"
            "Uses ML model + heuristics for best results\n"
            "Assumes horizontal text LTR (left to right)"
        )

        info_label = QtWidgets.QLabel(
            "<small>ℹ️ How it works:<br>"
            "&nbsp;&nbsp;• ML-based orientation detection<br>"
            "&nbsp;&nbsp;• Horizontal alignment (projection)<br>"
            "&nbsp;&nbsp;• Baseline & centroid detection<br>"
            "<br>"
            "⚠️ Assumes horizontal text LTR</small>"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")

        orient_layout.addWidget(check_auto_detect)
        orient_layout.addWidget(info_label)
        orient_group.setLayout(orient_layout)
        layout.addWidget(orient_group)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("✅ OK")
        btn_cancel = QtWidgets.QPushButton("❌ Cancel")

        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Show dialog
        result = dialog.exec_()

        if result == QtWidgets.QDialog.Accepted:
            crop_method = 'rotated' if radio_rotated.isChecked() else 'bbox'
            auto_detect = check_auto_detect.isChecked()
            return crop_method, auto_detect
        else:
            return None, False

    def _show_format_selection_dialog(self):
        """
        Show dialog to select image format for export.

        Returns:
            str: 'png' or 'jpg', or None if cancelled
        """
        dialog = QtWidgets.QDialog(self.main_window)
        dialog.setWindowTitle("Image Format Selection")
        dialog.setMinimumWidth(400)

        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("<b>Select Export Image Format</b>")
        layout.addWidget(title)

        # Description
        desc = QtWidgets.QLabel(
            "Choose the image format for exported images:"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # Format selection group
        format_group = QtWidgets.QGroupBox("Image Format")
        format_layout = QtWidgets.QVBoxLayout()

        # PNG option (default)
        radio_png = QtWidgets.QRadioButton("PNG - Lossless (Recommended)")
        radio_png.setChecked(True)  # Default to PNG
        png_details = QtWidgets.QLabel(
            "   • No quality loss\n"
            "   • Larger file size\n"
            "   • Best for training"
        )
        png_details.setStyleSheet("color: #666; margin-left: 20px;")

        # JPG option
        radio_jpg = QtWidgets.QRadioButton("JPG - Lossy (Smaller files)")
        jpg_details = QtWidgets.QLabel(
            "   • Some quality loss\n"
            "   • Smaller file size\n"
            "   • Quality: 95%"
        )
        jpg_details.setStyleSheet("color: #666; margin-left: 20px;")

        format_layout.addWidget(radio_png)
        format_layout.addWidget(png_details)
        format_layout.addSpacing(10)
        format_layout.addWidget(radio_jpg)
        format_layout.addWidget(jpg_details)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        layout.addSpacing(20)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("✅ OK")
        btn_cancel = QtWidgets.QPushButton("❌ Cancel")

        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)

        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Show dialog
        result = dialog.exec_()

        if result == QtWidgets.QDialog.Accepted:
            return 'png' if radio_png.isChecked() else 'jpg'
        else:
            return None  # User cancelled
