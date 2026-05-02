"""
PaddleOCR Settings Dialog

Simple settings dialog for PaddleOCR with focus on:
- OCR Version selection
- Custom model paths (detection & recognition)
- Detection/Recognition parameters
- Basic features
"""

from PyQt5 import QtWidgets, QtCore, QtGui
from modules.config import ConfigManager
import os
import logging
import yaml

logger = logging.getLogger("TextDetGUI")


class PaddleOCRSettingsDialog(QtWidgets.QDialog):
    """
    PaddleOCR Settings Dialog with simple checkbox controls.

    Features:
    - Profile selection (CPU/GPU)
    - OCR version selection
    - Custom model paths with checkboxes
    - Detection/Recognition parameters
    - Basic features toggles
    """

    settings_changed = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager.instance()
        self.current_profile = self.config.get_current_profile()

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("PaddleOCR Settings")
        self.setModal(True)
        self.resize(700, 550)

        # Main layout
        layout = QtWidgets.QVBoxLayout(self)

        # Profile selection at top
        profile_group = self.create_profile_selection()
        layout.addWidget(profile_group)

        # Tab Widget
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_models_tab()
        self.create_parameters_tab()
        self.create_features_tab()

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok |
            QtWidgets.QDialogButtonBox.Cancel |
            QtWidgets.QDialogButtonBox.RestoreDefaults
        )
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        button_box.button(QtWidgets.QDialogButtonBox.RestoreDefaults).clicked.connect(
            self.restore_defaults
        )
        layout.addWidget(button_box)

    def create_profile_selection(self):
        """Create profile selection group"""
        group = QtWidgets.QGroupBox("Profile")
        layout = QtWidgets.QHBoxLayout()

        self.profile_combo = QtWidgets.QComboBox()
        self.profile_combo.addItems(["cpu", "gpu"])
        self.profile_combo.setCurrentText(self.current_profile)
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)

        layout.addWidget(QtWidgets.QLabel("Select Profile:"))
        layout.addWidget(self.profile_combo)
        layout.addStretch()

        group.setLayout(layout)
        return group

    def create_models_tab(self):
        """Create Models Tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(15)

        # Info label
        info = QtWidgets.QLabel(
            "Configure PaddleOCR version and custom model paths.\n"
            "Leave checkboxes unchecked to use default PaddleOCR models."
        )
        info.setWordWrap(True)
        info.setStyleSheet("QLabel { color: #555; margin: 5px; font-style: italic; }")
        layout.addWidget(info)

        # === OCR Version ===
        version_group = QtWidgets.QGroupBox("OCR Version")
        version_layout = QtWidgets.QVBoxLayout()

        self.use_custom_version_check = QtWidgets.QCheckBox(
            "Specify OCR version (leave unchecked for auto/latest)"
        )
        version_layout.addWidget(self.use_custom_version_check)

        self.version_widget = QtWidgets.QWidget()
        version_form = QtWidgets.QFormLayout()
        version_form.setContentsMargins(20, 5, 0, 5)

        self.ocr_version_combo = QtWidgets.QComboBox()
        self.ocr_version_combo.addItems([
            "PP-OCRv5",
            "PP-OCRv4",
            "PP-OCRv3"
        ])
        version_form.addRow("Version:", self.ocr_version_combo)

        self.version_widget.setLayout(version_form)
        self.version_widget.setEnabled(False)
        self.use_custom_version_check.toggled.connect(self.version_widget.setEnabled)
        version_layout.addWidget(self.version_widget)

        version_group.setLayout(version_layout)
        layout.addWidget(version_group)

        # === Detection Model ===
        det_group = QtWidgets.QGroupBox("Detection Model")
        det_layout = QtWidgets.QVBoxLayout()

        self.use_custom_det_check = QtWidgets.QCheckBox(
            "Use custom detection model"
        )
        det_layout.addWidget(self.use_custom_det_check)

        # Detection model path
        self.det_model_widget = QtWidgets.QWidget()
        det_form = QtWidgets.QVBoxLayout()
        det_form.setContentsMargins(20, 5, 0, 5)

        # Path input with browse button
        det_path_label = QtWidgets.QLabel("Model Directory:")
        det_path_label.setStyleSheet("QLabel { font-weight: bold; }")
        det_form.addWidget(det_path_label)

        det_path_layout = QtWidgets.QHBoxLayout()
        self.det_model_dir_edit = QtWidgets.QLineEdit()
        self.det_model_dir_edit.setPlaceholderText("Example: models/det/my_detection_model")
        det_browse_btn = QtWidgets.QPushButton("Browse...")
        det_browse_btn.setMaximumWidth(100)
        det_browse_btn.clicked.connect(
            lambda: self.browse_directory(self.det_model_dir_edit, "det")
        )
        det_path_layout.addWidget(self.det_model_dir_edit, 1)
        det_path_layout.addWidget(det_browse_btn, 0)
        det_form.addLayout(det_path_layout)

        # Helper text
        det_help = QtWidgets.QLabel(
            "💡 Tip: Place your detection model in models/det/ folder"
        )
        det_help.setStyleSheet("QLabel { color: #666; font-size: 9pt; margin-top: 3px; }")
        det_form.addWidget(det_help)

        self.det_model_widget.setLayout(det_form)
        self.det_model_widget.setEnabled(False)
        self.use_custom_det_check.toggled.connect(self.det_model_widget.setEnabled)
        det_layout.addWidget(self.det_model_widget)

        det_group.setLayout(det_layout)
        layout.addWidget(det_group)

        # === Recognition Model ===
        rec_group = QtWidgets.QGroupBox("Recognition Model")
        rec_layout = QtWidgets.QVBoxLayout()

        self.use_custom_rec_check = QtWidgets.QCheckBox(
            "Use custom recognition model"
        )
        rec_layout.addWidget(self.use_custom_rec_check)

        # Recognition model path
        self.rec_model_widget = QtWidgets.QWidget()
        rec_form = QtWidgets.QVBoxLayout()
        rec_form.setContentsMargins(20, 5, 0, 5)

        # Path input with browse button
        rec_path_label = QtWidgets.QLabel("Model Directory:")
        rec_path_label.setStyleSheet("QLabel { font-weight: bold; }")
        rec_form.addWidget(rec_path_label)

        rec_path_layout = QtWidgets.QHBoxLayout()
        self.rec_model_dir_edit = QtWidgets.QLineEdit()
        self.rec_model_dir_edit.setPlaceholderText("Example: models/rec/my_recognition_model")
        rec_browse_btn = QtWidgets.QPushButton("Browse...")
        rec_browse_btn.setMaximumWidth(100)
        rec_browse_btn.clicked.connect(
            lambda: self.browse_directory(self.rec_model_dir_edit, "rec")
        )
        rec_path_layout.addWidget(self.rec_model_dir_edit, 1)
        rec_path_layout.addWidget(rec_browse_btn, 0)
        rec_form.addLayout(rec_path_layout)

        # Helper text
        rec_help = QtWidgets.QLabel(
            "💡 Tip: Place your recognition model in models/rec/ folder"
        )
        rec_help.setStyleSheet("QLabel { color: #666; font-size: 9pt; margin-top: 3px; }")
        rec_form.addWidget(rec_help)

        self.rec_model_widget.setLayout(rec_form)
        self.rec_model_widget.setEnabled(False)
        self.use_custom_rec_check.toggled.connect(self.rec_model_widget.setEnabled)
        rec_layout.addWidget(self.rec_model_widget)

        rec_group.setLayout(rec_layout)
        layout.addWidget(rec_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Models")

    def create_parameters_tab(self):
        """Create Parameters Tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(15)

        # Scroll area for many parameters
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)

        # === Detection Parameters ===
        det_group = QtWidgets.QGroupBox("Detection Parameters")
        det_layout = QtWidgets.QVBoxLayout()

        # Box threshold with slider (always shown)
        thresh_form = QtWidgets.QFormLayout()
        self.det_box_thresh_spin = QtWidgets.QDoubleSpinBox()
        self.det_box_thresh_spin.setRange(0.1, 1.0)
        self.det_box_thresh_spin.setSingleStep(0.05)
        self.det_box_thresh_spin.setValue(0.7)
        self.det_box_thresh_spin.setDecimals(2)
        thresh_form.addRow(
            "Box Threshold:",
            self.create_slider_spinbox(self.det_box_thresh_spin, 0.1, 1.0, 0.05)
        )
        thresh_help = QtWidgets.QLabel("Higher = stricter detection (default: 0.6)")
        thresh_help.setStyleSheet("QLabel { color: #666; font-size: 9pt; }")
        thresh_form.addRow("", thresh_help)

        # Unclip ratio with slider (always shown)
        self.det_unclip_ratio_spin = QtWidgets.QDoubleSpinBox()
        self.det_unclip_ratio_spin.setRange(1.0, 3.0)
        self.det_unclip_ratio_spin.setSingleStep(0.1)
        self.det_unclip_ratio_spin.setValue(1.5)
        self.det_unclip_ratio_spin.setDecimals(1)
        thresh_form.addRow(
            "Unclip Ratio:",
            self.create_slider_spinbox(self.det_unclip_ratio_spin, 1.0, 3.0, 0.1)
        )
        unclip_help = QtWidgets.QLabel("Higher = larger boxes (default: 2.0)")
        unclip_help.setStyleSheet("QLabel { color: #666; font-size: 9pt; }")
        thresh_form.addRow("", unclip_help)

        det_layout.addLayout(thresh_form)

        # Advanced detection parameters (checkbox to enable)
        self.use_advanced_det_check = QtWidgets.QCheckBox(
            "Use advanced detection parameters"
        )
        det_layout.addWidget(self.use_advanced_det_check)

        self.advanced_det_widget = QtWidgets.QWidget()
        adv_det_form = QtWidgets.QFormLayout()
        adv_det_form.setContentsMargins(20, 5, 0, 5)

        # Pixel threshold
        self.det_thresh_spin = QtWidgets.QDoubleSpinBox()
        self.det_thresh_spin.setRange(0.1, 1.0)
        self.det_thresh_spin.setSingleStep(0.05)
        self.det_thresh_spin.setValue(0.3)
        self.det_thresh_spin.setDecimals(2)
        adv_det_form.addRow("Pixel Threshold:", self.det_thresh_spin)

        # Limit side length
        self.det_limit_side_spin = QtWidgets.QSpinBox()
        self.det_limit_side_spin.setRange(64, 4096)
        self.det_limit_side_spin.setSingleStep(32)
        self.det_limit_side_spin.setValue(960)
        adv_det_form.addRow("Max Side Length:", self.det_limit_side_spin)

        # Limit type
        self.det_limit_type_combo = QtWidgets.QComboBox()
        self.det_limit_type_combo.addItems(["max", "min"])
        adv_det_form.addRow("Limit Type:", self.det_limit_type_combo)

        # Detection batch size
        self.det_batch_spin = QtWidgets.QSpinBox()
        self.det_batch_spin.setRange(1, 32)
        self.det_batch_spin.setValue(1)
        adv_det_form.addRow("Detection Batch:", self.det_batch_spin)

        self.advanced_det_widget.setLayout(adv_det_form)
        self.advanced_det_widget.setEnabled(False)
        self.use_advanced_det_check.toggled.connect(self.advanced_det_widget.setEnabled)
        det_layout.addWidget(self.advanced_det_widget)

        det_group.setLayout(det_layout)
        scroll_layout.addWidget(det_group)

        # === Recognition Parameters ===
        rec_group = QtWidgets.QGroupBox("Recognition Parameters")
        rec_layout = QtWidgets.QVBoxLayout()

        rec_form = QtWidgets.QFormLayout()
        # Batch size (always shown)
        self.rec_batch_spin = QtWidgets.QSpinBox()
        self.rec_batch_spin.setRange(1, 32)
        self.rec_batch_spin.setValue(6)
        rec_form.addRow("Batch Size:", self.rec_batch_spin)

        rec_layout.addLayout(rec_form)

        # Advanced recognition parameters (checkbox to enable)
        self.use_advanced_rec_check = QtWidgets.QCheckBox(
            "Use advanced recognition parameters"
        )
        rec_layout.addWidget(self.use_advanced_rec_check)

        self.advanced_rec_widget = QtWidgets.QWidget()
        adv_rec_form = QtWidgets.QFormLayout()
        adv_rec_form.setContentsMargins(20, 5, 0, 5)

        # Recognition score threshold
        self.rec_score_thresh_spin = QtWidgets.QDoubleSpinBox()
        self.rec_score_thresh_spin.setRange(0.0, 1.0)
        self.rec_score_thresh_spin.setSingleStep(0.05)
        self.rec_score_thresh_spin.setValue(0.0)
        self.rec_score_thresh_spin.setDecimals(2)
        adv_rec_form.addRow("Score Threshold:", self.rec_score_thresh_spin)

        self.advanced_rec_widget.setLayout(adv_rec_form)
        self.advanced_rec_widget.setEnabled(False)
        self.use_advanced_rec_check.toggled.connect(self.advanced_rec_widget.setEnabled)
        rec_layout.addWidget(self.advanced_rec_widget)

        rec_group.setLayout(rec_layout)
        scroll_layout.addWidget(rec_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        self.tab_widget.addTab(tab, "Parameters")

    def create_features_tab(self):
        """Create Features Tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setSpacing(15)

        # === Advanced Features ===
        adv_group = QtWidgets.QGroupBox("Advanced Features")
        adv_layout = QtWidgets.QVBoxLayout()
        adv_layout.setSpacing(8)

        self.use_doc_orient_check = QtWidgets.QCheckBox(
            "Document Orientation (0°, 90°, 180°, 270°)"
        )
        adv_layout.addWidget(self.use_doc_orient_check)

        self.use_doc_unwarp_check = QtWidgets.QCheckBox(
            "Document Unwarping (curved text correction)"
        )
        adv_layout.addWidget(self.use_doc_unwarp_check)

        # Note: use_textline_orientation is always enabled (not shown in UI)
        # We keep it as a hidden checkbox for compatibility
        self.use_textline_orient_check = QtWidgets.QCheckBox()
        self.use_textline_orient_check.setChecked(True)
        self.use_textline_orient_check.setVisible(False)  # Hidden - always enabled

        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)

        # === Performance ===
        perf_group = QtWidgets.QGroupBox("Performance (CPU)")
        perf_layout = QtWidgets.QFormLayout()

        self.enable_mkldnn_check = QtWidgets.QCheckBox()
        self.enable_mkldnn_check.setChecked(True)
        perf_layout.addRow("Enable MKL-DNN:", self.enable_mkldnn_check)

        self.cpu_threads_spin = QtWidgets.QSpinBox()
        self.cpu_threads_spin.setRange(1, 32)
        self.cpu_threads_spin.setValue(8)
        perf_layout.addRow("CPU Threads:", self.cpu_threads_spin)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        layout.addStretch()
        self.tab_widget.addTab(tab, "Features")

    # === Helper Methods ===

    def create_slider_spinbox(self, spinbox, min_val, max_val, step):
        """Create a slider + spinbox combo widget"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setRange(int(min_val / step), int(max_val / step))
        slider.setValue(int(spinbox.value() / step))

        # Connect slider and spinbox
        slider.valueChanged.connect(
            lambda val: spinbox.setValue(val * step)
        )
        spinbox.valueChanged.connect(
            lambda val: slider.setValue(int(val / step))
        )

        layout.addWidget(spinbox, 0)
        layout.addWidget(slider, 1)

        widget.setLayout(layout)
        return widget

    def browse_directory(self, line_edit, model_type):
        """Browse for model directory"""
        # Start at models/{det or rec}
        start_dir = os.path.join(self.config.root_dir, "models", model_type)

        # Create dir if not exists
        os.makedirs(start_dir, exist_ok=True)

        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            f"Select {model_type.capitalize()} Model Directory",
            start_dir,
            QtWidgets.QFileDialog.ShowDirsOnly
        )

        if directory:
            # Make relative to project root
            try:
                rel_path = os.path.relpath(directory, self.config.root_dir)
                # Use forward slashes for cross-platform compatibility
                rel_path = rel_path.replace('\\', '/')
                line_edit.setText(rel_path)
            except ValueError:
                # If path is on different drive, use absolute path
                line_edit.setText(directory)

    def on_profile_changed(self, profile_name):
        """Handle profile change"""
        self.current_profile = profile_name
        self.load_settings()

    def load_settings(self):
        """Load current settings from config"""
        params = self.config.get_paddleocr_params(self.current_profile)

        # OCR Version
        ocr_version = params.get('ocr_version')
        if ocr_version:
            self.use_custom_version_check.setChecked(True)
            self.ocr_version_combo.setCurrentText(ocr_version)
        else:
            self.use_custom_version_check.setChecked(False)

        # Detection model
        det_dir = params.get('text_detection_model_dir')
        if det_dir:
            self.use_custom_det_check.setChecked(True)
            self.det_model_dir_edit.setText(det_dir)
        else:
            self.use_custom_det_check.setChecked(False)
            self.det_model_dir_edit.clear()

        # Recognition model (custom model = has path specified)
        rec_dir = params.get('text_recognition_model_dir')
        if rec_dir:
            self.use_custom_rec_check.setChecked(True)
            self.rec_model_dir_edit.setText(rec_dir)
        else:
            # No path = use official model via 'lang' parameter
            self.use_custom_rec_check.setChecked(False)
            self.rec_model_dir_edit.clear()

        # Detection params
        self.det_box_thresh_spin.setValue(
            params.get('det_db_box_thresh', 0.7)
        )
        self.det_unclip_ratio_spin.setValue(
            params.get('det_db_unclip_ratio', 1.5)
        )

        # Advanced detection params
        has_adv_det = any(key in params for key in [
            'text_det_thresh', 'text_det_limit_side_len',
            'text_det_limit_type', 'text_detection_batch_size'
        ])
        self.use_advanced_det_check.setChecked(has_adv_det)
        if has_adv_det:
            self.det_thresh_spin.setValue(params.get('text_det_thresh', 0.3))
            self.det_limit_side_spin.setValue(params.get('text_det_limit_side_len', 960))
            limit_type = params.get('text_det_limit_type', 'max')
            idx = self.det_limit_type_combo.findText(limit_type)
            if idx >= 0:
                self.det_limit_type_combo.setCurrentIndex(idx)
            self.det_batch_spin.setValue(params.get('text_detection_batch_size', 1))

        # Recognition params
        self.rec_batch_spin.setValue(
            params.get('rec_batch_num', 6)
        )

        # Advanced recognition params
        has_adv_rec = 'text_rec_score_thresh' in params
        self.use_advanced_rec_check.setChecked(has_adv_rec)
        if has_adv_rec:
            self.rec_score_thresh_spin.setValue(params.get('text_rec_score_thresh', 0.0))

        # Features
        self.use_doc_orient_check.setChecked(
            params.get('use_doc_orientation_classify', False)
        )
        self.use_doc_unwarp_check.setChecked(
            params.get('use_doc_unwarping', False)
        )
        # use_textline_orientation is always enabled
        self.use_textline_orient_check.setChecked(True)

        # Performance
        self.enable_mkldnn_check.setChecked(
            params.get('enable_mkldnn', True)
        )
        self.cpu_threads_spin.setValue(
            params.get('cpu_threads', 8)
        )

    def get_settings(self):
        """Get current settings from UI"""
        settings = {}

        # OCR Version
        if self.use_custom_version_check.isChecked():
            settings['ocr_version'] = self.ocr_version_combo.currentText()

        # Detection model
        if self.use_custom_det_check.isChecked() and self.det_model_dir_edit.text():
            settings['text_detection_model_dir'] = self.det_model_dir_edit.text()

        # Recognition model (only set if using custom model)
        if self.use_custom_rec_check.isChecked() and self.rec_model_dir_edit.text():
            settings['text_recognition_model_dir'] = self.rec_model_dir_edit.text()
        # else: use official model via 'lang' parameter (no path needed)

        # Detection parameters
        settings['det_db_box_thresh'] = self.det_box_thresh_spin.value()
        settings['det_db_unclip_ratio'] = self.det_unclip_ratio_spin.value()

        # Advanced detection parameters (only if checkbox is checked)
        if self.use_advanced_det_check.isChecked():
            settings['text_det_thresh'] = self.det_thresh_spin.value()
            settings['text_det_limit_side_len'] = self.det_limit_side_spin.value()
            settings['text_det_limit_type'] = self.det_limit_type_combo.currentText()
            settings['text_detection_batch_size'] = self.det_batch_spin.value()

        # Recognition parameters
        settings['rec_batch_num'] = self.rec_batch_spin.value()

        # Advanced recognition parameters (only if checkbox is checked)
        if self.use_advanced_rec_check.isChecked():
            settings['text_rec_score_thresh'] = self.rec_score_thresh_spin.value()

        # Features
        settings['use_doc_orientation_classify'] = self.use_doc_orient_check.isChecked()
        settings['use_doc_unwarping'] = self.use_doc_unwarp_check.isChecked()
        settings['use_textline_orientation'] = self.use_textline_orient_check.isChecked()

        # Performance
        settings['enable_mkldnn'] = self.enable_mkldnn_check.isChecked()
        settings['cpu_threads'] = self.cpu_threads_spin.value()

        return settings

    def accept_settings(self):
        """Accept and save settings"""
        try:
            settings = self.get_settings()

            # Update config
            profile_config = self.config.get_profile_config(self.current_profile)

            # Update paddleocr settings
            paddleocr_config = profile_config.get('paddleocr', {})
            paddleocr_config.update(settings)
            profile_config['paddleocr'] = paddleocr_config

            # Save to file
            self.save_profile_to_file(self.current_profile, profile_config)

            # Emit signal
            self.settings_changed.emit()

            # Show success message
            QtWidgets.QMessageBox.information(
                self,
                "Settings Saved",
                f"Settings for profile '{self.current_profile}' have been saved.\n\n"
                "⚠️ Important: Please restart OCR detection to apply changes."
            )

            self.accept()

        except Exception as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )

    def save_profile_to_file(self, profile_name, profile_config):
        """Save profile config to unified config.yaml"""
        config_file = os.path.join(self.config.config_dir, "config.yaml")

        # Load existing config
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f) or {}
        else:
            full_config = {'default_profile': 'cpu', 'profiles': {}}

        # Update the specific profile
        if 'profiles' not in full_config:
            full_config['profiles'] = {}

        full_config['profiles'][profile_name] = profile_config

        # Save back to config.yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(full_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved profile '{profile_name}' config to {config_file}")

    def restore_defaults(self):
        """Restore default settings"""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore default settings?\n"
            "This will reset all PaddleOCR parameters to defaults.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            # Reload from config
            self.load_settings()
            QtWidgets.QMessageBox.information(
                self,
                "Defaults Restored",
                "Default settings have been restored.\n"
                "Click OK to save, or Cancel to discard."
            )
