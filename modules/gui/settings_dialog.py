# modules/gui/settings_dialog.py

from PyQt5 import QtWidgets, QtCore, QtGui
from modules.config_loader import ConfigLoader
import logging
import copy

logger = logging.getLogger("TextDetGUI")


class SettingsDialog(QtWidgets.QDialog):
    """
    Dialog สำหรับตั้งค่าโปรแกรม
    - OCR Settings (Profile, PaddleOCR parameters)
    - Application Settings
    """

    # Signal เมื่อ settings เปลี่ยนแปลง
    settings_changed = QtCore.pyqtSignal()

    def __init__(self, config_loader: ConfigLoader, parent=None):
        super().__init__(parent)
        self.config_loader = config_loader

        # เก็บ config เดิมสำหรับ Cancel
        self.original_config = copy.deepcopy(self.config_loader._config)

        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        """สร้าง UI"""
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
        """สร้าง OCR Settings Tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # === Profile Selection ===
        profile_group = QtWidgets.QGroupBox("Profile Selection")
        profile_layout = QtWidgets.QVBoxLayout()

        # Radio buttons สำหรับ profile
        self.profile_cpu_radio = QtWidgets.QRadioButton("CPU (แนะนำสำหรับความเสถียร)")
        self.profile_gpu_radio = QtWidgets.QRadioButton("GPU (เร็วกว่า แต่ต้องมี CUDA)")

        profile_layout.addWidget(self.profile_cpu_radio)
        profile_layout.addWidget(self.profile_gpu_radio)

        # GPU Settings (แสดงเมื่อเลือก GPU)
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

        # เชื่อม signal
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

        # Checkboxes สำหรับ features
        self.use_doc_orientation_check = QtWidgets.QCheckBox("ตรวจจับการหมุนเอกสาร")
        ocr_layout.addRow("", self.use_doc_orientation_check)

        self.use_doc_unwarping_check = QtWidgets.QCheckBox("แก้การบิดเบี้ยวของเอกสาร")
        ocr_layout.addRow("", self.use_doc_unwarping_check)

        self.use_textline_orientation_check = QtWidgets.QCheckBox("ตรวจจับการกลับหัวของข้อความ (แนะนำสำหรับ GPU)")
        ocr_layout.addRow("", self.use_textline_orientation_check)

        ocr_group.setLayout(ocr_layout)
        layout.addWidget(ocr_group)

        # คำอธิบาย
        info_label = QtWidgets.QLabel(
            "<small><b>หมายเหตุ:</b><br>"
            "- Detection Threshold: ค่าสูง = ตรวจจับเข้มงวดขึ้น (0.5-0.9)<br>"
            "- Unclip Ratio: ค่าสูง = ขยาย bounding box มากขึ้น (1.0-2.5)<br>"
            "- การเปลี่ยน profile จะ reload OCR detector อัตโนมัติ</small>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        self.tab_widget.addTab(tab, "OCR Settings")

    def create_app_tab(self):
        """สร้าง Application Settings Tab"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)

        # === Application Settings ===
        app_group = QtWidgets.QGroupBox("Application Settings")
        app_layout = QtWidgets.QVBoxLayout()

        self.auto_save_check = QtWidgets.QCheckBox("Auto Save (บันทึกอัตโนมัติเมื่อมีการเปลี่ยนแปลง)")
        app_layout.addWidget(self.auto_save_check)

        self.cache_annotations_check = QtWidgets.QCheckBox("Cache Annotations (เก็บ cache เพื่อความเร็ว)")
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
        """โหลดค่า settings ปัจจุบัน"""
        try:
            # โหลด default profile
            default_profile = self.config_loader.get_default_profile_name()

            if default_profile == "cpu":
                self.profile_cpu_radio.setChecked(True)
            elif default_profile == "gpu":
                self.profile_gpu_radio.setChecked(True)

            # โหลด profile config
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
        """บันทึก settings ลง config"""
        try:
            # กำหนด profile ที่เลือก
            if self.profile_cpu_radio.isChecked():
                profile_name = "cpu"
            elif self.profile_gpu_radio.isChecked():
                profile_name = "gpu"
            else:
                profile_name = "cpu"

            # เปลี่ยน default profile
            old_profile = self.config_loader.get_default_profile_name()
            self.config_loader.set_default_profile(profile_name)

            # อัปเดต profile config
            profile_config = self.config_loader._config['profiles'][profile_name]

            # อัปเดต GPU settings (ถ้าเลือก GPU)
            if profile_name == "gpu":
                profile_config['device']['gpu_id'] = self.gpu_id_spin.value()
                profile_config['device']['gpu_mem'] = self.gpu_mem_spin.value()

            # อัปเดต PaddleOCR settings
            ocr_config = profile_config['paddleocr']
            ocr_config['lang'] = self.lang_combo.currentText()
            ocr_config['det_db_box_thresh'] = self.det_thresh_spin.value()
            ocr_config['det_db_unclip_ratio'] = self.unclip_ratio_spin.value()
            ocr_config['use_doc_orientation_classify'] = self.use_doc_orientation_check.isChecked()
            ocr_config['use_doc_unwarping'] = self.use_doc_unwarping_check.isChecked()
            ocr_config['use_textline_orientation'] = self.use_textline_orientation_check.isChecked()
            ocr_config['device'] = profile_name  # ต้องตรงกับ profile

            # อัปเดต App settings
            app_config = self.config_loader._config.get('app', {})
            app_config['auto_save'] = self.auto_save_check.isChecked()
            app_config['cache_annotations'] = self.cache_annotations_check.isChecked()
            self.config_loader._config['app'] = app_config

            # บันทึกลงไฟล์
            self.config_loader.save()

            # Emit signal ว่า settings เปลี่ยน
            self.settings_changed.emit()

            # แจ้งเตือนถ้าเปลี่ยน profile
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
        """OK button - บันทึกและปิด"""
        self.apply_settings()
        super().accept()

    def reject(self):
        """Cancel button - ยกเลิกและคืนค่าเดิม"""
        # Restore original config
        self.config_loader._config = self.original_config
        logger.info("Settings cancelled. Config restored.")
        super().reject()
