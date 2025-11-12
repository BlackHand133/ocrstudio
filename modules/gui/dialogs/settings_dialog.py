# modules/gui/settings_dialog.py

from PyQt5 import QtWidgets, QtCore, QtGui
from modules.config_loader import ConfigLoader
import logging
import copy

logger = logging.getLogger("TextDetGUI")


class SettingsDialog(QtWidgets.QDialog):
    """
    Dialog for application settings
    - OCR Settings (Profile, PaddleOCR parameters)
    - Application Settings
    """

    # Signal when settings change
    settings_changed = QtCore.pyqtSignal()

    def __init__(self, config_loader: ConfigLoader, parent=None):
        super().__init__(parent)
        self.config_loader = config_loader

        # Store original config for Cancel
        self.original_config = copy.deepcopy(self.config_loader._config)

        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        """Create UI"""
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(600, 500)

        # Main layout
        layout = QtWidgets.QVBoxLayout(self)

        # Tab Widget
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        # Tabs
        self.create_ocr_tab()
        self.create_app_tab()

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok |
            QtWidgets.QDialogButtonBox.Cancel |
            QtWidgets.QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        layout.addWidget(button_box)

    def create_ocr_tab(self):
        """Create OCR Settings Tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # === Profile Selection ===
        profile_group = QtWidgets.QGroupBox("Profile Selection")
        profile_layout = QtWidgets.QVBoxLayout()

        # Radio buttons for profile
        self.profile_cpu_radio = QtWidgets.QRadioButton("CPU (recommended for stability)")
        self.profile_gpu_radio = QtWidgets.QRadioButton("GPU (faster, requires CUDA)")

        profile_layout.addWidget(self.profile_cpu_radio)
        profile_layout.addWidget(self.profile_gpu_radio)

        # GPU Settings (shown when GPU is selected)
        self.gpu_settings_widget = QtWidgets.QWidget()
        gpu_layout = QtWidgets.QFormLayout()

        self.gpu_id_spin = QtWidgets.QSpinBox()
        self.gpu_id_spin.setMinimum(0)
        self.gpu_id_spin.setMaximum(7)
        self.gpu_id_spin.setValue(0)
        gpu_layout.addRow("GPU ID:", self.gpu_id_spin)

        self.gpu_mem_spin = QtWidgets.QSpinBox()
        self.gpu_mem_spin.setMinimum(1000)
        self.gpu_mem_spin.setMaximum(32000)
        self.gpu_mem_spin.setSingleStep(1000)
        self.gpu_mem_spin.setValue(8000)
        self.gpu_mem_spin.setSuffix(" MB")
        gpu_layout.addRow("GPU Memory:", self.gpu_mem_spin)

        self.gpu_settings_widget.setLayout(gpu_layout)
        self.gpu_settings_widget.setEnabled(False)
        profile_layout.addWidget(self.gpu_settings_widget)

        # Connect signal
        self.profile_gpu_radio.toggled.connect(self.gpu_settings_widget.setEnabled)

        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)

        # === PaddleOCR Parameters ===
        ocr_group = QtWidgets.QGroupBox("PaddleOCR Parameters")
        ocr_layout = QtWidgets.QFormLayout()

        # Language
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItems(["th", "en", "ch", "japan", "korean"])
        self.lang_combo.setCurrentText("th")
        ocr_layout.addRow("Language:", self.lang_combo)

        # Detection threshold
        self.det_thresh_spin = QtWidgets.QDoubleSpinBox()
        self.det_thresh_spin.setMinimum(0.0)
        self.det_thresh_spin.setMaximum(1.0)
        self.det_thresh_spin.setSingleStep(0.05)
        self.det_thresh_spin.setValue(0.7)
        self.det_thresh_spin.setDecimals(2)
        ocr_layout.addRow("Detection Threshold:", self.det_thresh_spin)

        # Unclip ratio
        self.unclip_ratio_spin = QtWidgets.QDoubleSpinBox()
        self.unclip_ratio_spin.setMinimum(1.0)
        self.unclip_ratio_spin.setMaximum(3.0)
        self.unclip_ratio_spin.setSingleStep(0.1)
        self.unclip_ratio_spin.setValue(1.5)
        self.unclip_ratio_spin.setDecimals(1)
        ocr_layout.addRow("Unclip Ratio:", self.unclip_ratio_spin)

        # Checkboxes for features
        self.use_doc_orientation_check = QtWidgets.QCheckBox("Detect document rotation")
        ocr_layout.addRow("", self.use_doc_orientation_check)

        self.use_doc_unwarping_check = QtWidgets.QCheckBox("Fix document distortion")
        ocr_layout.addRow("", self.use_doc_unwarping_check)

        self.use_textline_orientation_check = QtWidgets.QCheckBox("Detect text line orientation (recommended for GPU)")
        ocr_layout.addRow("", self.use_textline_orientation_check)

        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)

        # Description
        info_label = QtWidgets.QLabel(
            "<small><b>Note:</b><br>"
            "- Detection Threshold: Higher value = stricter detection (0.5-0.9)<br>"
            "- Unclip Ratio: Higher value = expand bounding box more (1.0-2.5)<br>"
            "- Changing profile will reload OCR detector automatically</small>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        self.tab_widget.addTab(tab, "OCR Settings")

    def create_app_tab(self):
        """Create Application Settings Tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # === Application Settings ===
        app_group = QtWidgets.QGroupBox("Application Settings")
        app_layout = QtWidgets.QVBoxLayout()

        self.auto_save_check = QtWidgets.QCheckBox("Auto Save (automatically save when changes occur)")
        app_layout.addWidget(self.auto_save_check)

        self.cache_annotations_check = QtWidgets.QCheckBox("Cache Annotations (store cache for speed)")
        app_layout.addWidget(self.cache_annotations_check)

        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        # === Info ===
        info_group = QtWidgets.QGroupBox("About")
        info_layout = QtWidgets.QVBoxLayout()

        config_path_label = QtWidgets.QLabel(f"<b>Config File:</b> {self.config_loader.config_file}")
        config_path_label.setWordWrap(True)
        info_layout.addWidget(config_path_label)

        available_profiles = self.config_loader.list_profiles()
        profiles_label = QtWidgets.QLabel(f"<b>Available Profiles:</b> {', '.join(available_profiles)}")
        info_layout.addWidget(profiles_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()

        self.tab_widget.addTab(tab, "Application")

    def load_current_settings(self):
        """Load current settings"""
        try:
            # Load default profile
            default_profile = self.config_loader.get_default_profile_name()

            if default_profile == "cpu":
                self.profile_cpu_radio.setChecked(True)
            elif default_profile == "gpu":
                self.profile_gpu_radio.setChecked(True)

            # Load profile config
            profile_config = self.config_loader.get_profile(default_profile)

            # GPU Settings
            if default_profile == "gpu":
                device_config = profile_config.get('device', {})
                self.gpu_id_spin.setValue(device_config.get('gpu_id', 0))
                self.gpu_mem_spin.setValue(device_config.get('gpu_mem', 8000))

            # PaddleOCR Settings
            ocr_config = profile_config.get('paddleocr', {})

            self.lang_combo.setCurrentText(ocr_config.get('lang', 'th'))
            self.det_thresh_spin.setValue(ocr_config.get('det_db_box_thresh', 0.7))
            self.unclip_ratio_spin.setValue(ocr_config.get('det_db_unclip_ratio', 1.5))

            self.use_doc_orientation_check.setChecked(ocr_config.get('use_doc_orientation_classify', False))
            self.use_doc_unwarping_check.setChecked(ocr_config.get('use_doc_unwarping', False))
            self.use_textline_orientation_check.setChecked(ocr_config.get('use_textline_orientation', False))

            # App Settings
            app_config = self.config_loader.get_app_settings()
            self.auto_save_check.setChecked(app_config.get('auto_save', True))
            self.cache_annotations_check.setChecked(app_config.get('cache_annotations', True))

            logger.info("Loaded current settings into dialog")

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                f"Failed to load settings:\n{str(e)}"
            )

    def apply_settings(self):
        """Save settings to config"""
        try:
            # Determine selected profile
            if self.profile_cpu_radio.isChecked():
                profile_name = "cpu"
            elif self.profile_gpu_radio.isChecked():
                profile_name = "gpu"
            else:
                profile_name = "cpu"

            # Change default profile
            old_profile = self.config_loader.get_default_profile_name()
            self.config_loader.set_default_profile(profile_name)

            # Update profile config
            profile_config = self.config_loader._config['profiles'][profile_name]

            # Update GPU settings (if GPU is selected)
            if profile_name == "gpu":
                profile_config['device']['gpu_id'] = self.gpu_id_spin.value()
                profile_config['device']['gpu_mem'] = self.gpu_mem_spin.value()

            # Update PaddleOCR settings
            ocr_config = profile_config['paddleocr']
            ocr_config['lang'] = self.lang_combo.currentText()
            ocr_config['det_db_box_thresh'] = self.det_thresh_spin.value()
            ocr_config['det_db_unclip_ratio'] = self.unclip_ratio_spin.value()
            ocr_config['use_doc_orientation_classify'] = self.use_doc_orientation_check.isChecked()
            ocr_config['use_doc_unwarping'] = self.use_doc_unwarping_check.isChecked()
            ocr_config['use_textline_orientation'] = self.use_textline_orientation_check.isChecked()
            ocr_config['device'] = profile_name  # Must match profile

            # Update App settings
            app_config = self.config_loader._config.get('app', {})
            app_config['auto_save'] = self.auto_save_check.isChecked()
            app_config['cache_annotations'] = self.cache_annotations_check.isChecked()
            self.config_loader._config['app'] = app_config

            # Save to file
            self.config_loader.save()

            # Emit signal that settings changed
            self.settings_changed.emit()

            # Notify if profile changed
            if old_profile != profile_name:
                QtWidgets.QMessageBox.information(
                    self,
                    "Profile Changed",
                    f"Profile changed from '{old_profile}' to '{profile_name}'.\n"
                    "OCR detector will be reloaded."
                )

            logger.info(f"Settings saved successfully. Profile: {profile_name}")

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )

    def accept(self):
        """OK button - save and close"""
        self.apply_settings()
        super().accept()

    def reject(self):
        """Cancel button - cancel and restore original values"""
        # Restore original config
        self.config_loader._config = self.original_config
        logger.info("Settings cancelled. Config restored.")
        super().reject()
