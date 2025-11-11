# modules/gui/augmentation_dialog.py

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QLocale

class AugmentationDialog(QtWidgets.QDialog):
    """
    Dialog สำหรับเลือก augmentation options
    รองรับทั้ง Detection และ Recognition
    """
    
    def __init__(self, parent=None, mode='detection'):
        super().__init__(parent)
        self.mode = mode  # 'detection' or 'recognition'
        self.result = None
        
        self.setWindowTitle(f"Augmentation Config - {mode.title()}")
        self.setModal(True)
        self.resize(600, 750)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # === Target Splits Selection ===
        split_group = QtWidgets.QGroupBox("Apply Augmentation To")
        split_layout = QtWidgets.QHBoxLayout()
        
        self.check_aug_train = QtWidgets.QCheckBox("Train")
        self.check_aug_train.setChecked(True)  # Default: augment train only
        self.check_aug_test = QtWidgets.QCheckBox("Test")
        self.check_aug_valid = QtWidgets.QCheckBox("Valid")
        
        split_layout.addWidget(self.check_aug_train)
        split_layout.addWidget(self.check_aug_test)
        split_layout.addWidget(self.check_aug_valid)
        split_layout.addStretch()
        
        info_label = QtWidgets.QLabel("💡 Tip: Usually augment training set only")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        split_layout.addWidget(info_label)
        
        split_group.setLayout(split_layout)
        layout.addWidget(split_group)
        
        # === Mode Selection ===
        mode_group = QtWidgets.QGroupBox("Augmentation Mode")
        mode_layout = QtWidgets.QVBoxLayout()
        
        self.radio_combinatorial = QtWidgets.QRadioButton(
            "Combinatorial (สร้างแยกแต่ละ augmentation)"
        )
        self.radio_combinatorial.setChecked(True)
        self.radio_sequential = QtWidgets.QRadioButton(
            "Sequential (ใช้ augmentation พร้อมกันในภาพเดียว)"
        )
        
        mode_layout.addWidget(self.radio_combinatorial)
        mode_layout.addWidget(self.radio_sequential)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # === Scrollable Augmentation Options ===
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        
        # 1. Geometric Transformations
        self._add_geometric_section(scroll_layout)
        
        # 2. Color and Intensity
        self._add_color_section(scroll_layout)
        
        # 3. Noise and Effects
        self._add_noise_section(scroll_layout)
        
        if self.mode == 'recognition':
            # 4. Text-specific (สำหรับ recognition)
            self._add_text_specific_section(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # === Buttons ===
        button_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("OK")
        btn_cancel = QtWidgets.QPushButton("Cancel")
        
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
    
    def _add_geometric_section(self, layout):
        """Geometric Transformations"""
        group = QtWidgets.QGroupBox("🔄 Geometric Transformations")
        group_layout = QtWidgets.QVBoxLayout()
        
        # Rotation
        self.check_rotation = QtWidgets.QCheckBox("Rotation")
        rotation_layout = QtWidgets.QHBoxLayout()
        rotation_layout.addWidget(QtWidgets.QLabel("Angle (°):"))
        self.spin_rotation = QtWidgets.QDoubleSpinBox()
        self.spin_rotation.setRange(-45, 45)
        self.spin_rotation.setValue(10)
        self.spin_rotation.setLocale(QLocale(QLocale.C))
        self.slider_rotation = QtWidgets.QSlider(Qt.Horizontal)
        self.slider_rotation.setRange(-45, 45)
        self.slider_rotation.setValue(10)
        self._sync_spin_slider(self.spin_rotation, self.slider_rotation)
        rotation_layout.addWidget(self.spin_rotation)
        rotation_layout.addWidget(self.slider_rotation)
        group_layout.addWidget(self.check_rotation)
        group_layout.addLayout(rotation_layout)
        
        # Shear
        self.check_shear = QtWidgets.QCheckBox("Shear/Skew")
        shear_layout = QtWidgets.QHBoxLayout()
        shear_layout.addWidget(QtWidgets.QLabel("Shear X:"))
        self.spin_shear_x = QtWidgets.QDoubleSpinBox()
        self.spin_shear_x.setRange(-0.5, 0.5)
        self.spin_shear_x.setValue(0.1)
        self.spin_shear_x.setSingleStep(0.05)
        self.spin_shear_x.setLocale(QLocale(QLocale.C))
        shear_layout.addWidget(self.spin_shear_x)
        shear_layout.addWidget(QtWidgets.QLabel("Shear Y:"))
        self.spin_shear_y = QtWidgets.QDoubleSpinBox()
        self.spin_shear_y.setRange(-0.5, 0.5)
        self.spin_shear_y.setValue(0.05)
        self.spin_shear_y.setSingleStep(0.05)
        self.spin_shear_y.setLocale(QLocale(QLocale.C))
        shear_layout.addWidget(self.spin_shear_y)
        group_layout.addWidget(self.check_shear)
        group_layout.addLayout(shear_layout)
        
        # Scale
        self.check_scale = QtWidgets.QCheckBox("Scale/Resize")
        scale_layout = QtWidgets.QHBoxLayout()
        scale_layout.addWidget(QtWidgets.QLabel("Scale X:"))
        self.spin_scale_x = QtWidgets.QDoubleSpinBox()
        self.spin_scale_x.setRange(0.5, 2.0)
        self.spin_scale_x.setValue(1.1)
        self.spin_scale_x.setSingleStep(0.1)
        self.spin_scale_x.setLocale(QLocale(QLocale.C))
        scale_layout.addWidget(self.spin_scale_x)
        scale_layout.addWidget(QtWidgets.QLabel("Scale Y:"))
        self.spin_scale_y = QtWidgets.QDoubleSpinBox()
        self.spin_scale_y.setRange(0.5, 2.0)
        self.spin_scale_y.setValue(1.1)
        self.spin_scale_y.setSingleStep(0.1)
        self.spin_scale_y.setLocale(QLocale(QLocale.C))
        scale_layout.addWidget(self.spin_scale_y)
        group_layout.addWidget(self.check_scale)
        group_layout.addLayout(scale_layout)
        
        # Perspective (สำหรับ detection)
        if self.mode == 'detection':
            self.check_perspective = QtWidgets.QCheckBox("Perspective Transform")
            persp_layout = QtWidgets.QHBoxLayout()
            persp_layout.addWidget(QtWidgets.QLabel("Strength:"))
            self.spin_perspective = QtWidgets.QDoubleSpinBox()
            self.spin_perspective.setRange(0.0, 0.5)
            self.spin_perspective.setValue(0.2)
            self.spin_perspective.setSingleStep(0.05)
            self.spin_perspective.setLocale(QLocale(QLocale.C))
            persp_layout.addWidget(self.spin_perspective)
            group_layout.addWidget(self.check_perspective)
            group_layout.addLayout(persp_layout)
        
        # Crop (สำหรับ recognition)
        if self.mode == 'recognition':
            self.check_crop = QtWidgets.QCheckBox("Random Crop")
            crop_layout = QtWidgets.QHBoxLayout()
            crop_layout.addWidget(QtWidgets.QLabel("Crop Ratio:"))
            self.spin_crop = QtWidgets.QDoubleSpinBox()
            self.spin_crop.setRange(0.7, 1.0)
            self.spin_crop.setValue(0.9)
            self.spin_crop.setSingleStep(0.05)
            self.spin_crop.setLocale(QLocale(QLocale.C))
            crop_layout.addWidget(self.spin_crop)
            group_layout.addWidget(self.check_crop)
            group_layout.addLayout(crop_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _add_color_section(self, layout):
        """Color and Intensity Transformations"""
        group = QtWidgets.QGroupBox("🎨 Color and Intensity")
        group_layout = QtWidgets.QVBoxLayout()
        
        # Brightness/Contrast
        self.check_brightness = QtWidgets.QCheckBox("Brightness/Contrast")
        bright_layout = QtWidgets.QHBoxLayout()
        bright_layout.addWidget(QtWidgets.QLabel("Brightness:"))
        self.spin_brightness = QtWidgets.QDoubleSpinBox()
        self.spin_brightness.setRange(-50, 50)
        self.spin_brightness.setValue(20)
        self.spin_brightness.setLocale(QLocale(QLocale.C))
        bright_layout.addWidget(self.spin_brightness)
        bright_layout.addWidget(QtWidgets.QLabel("Contrast:"))
        self.spin_contrast = QtWidgets.QDoubleSpinBox()
        self.spin_contrast.setRange(0.5, 2.0)
        self.spin_contrast.setValue(1.2)
        self.spin_contrast.setSingleStep(0.1)
        self.spin_contrast.setLocale(QLocale(QLocale.C))
        bright_layout.addWidget(self.spin_contrast)
        group_layout.addWidget(self.check_brightness)
        group_layout.addLayout(bright_layout)
        
        # Color Jitter
        self.check_color_jitter = QtWidgets.QCheckBox("Color Jitter")
        jitter_layout = QtWidgets.QHBoxLayout()
        jitter_layout.addWidget(QtWidgets.QLabel("Hue:"))
        self.spin_hue = QtWidgets.QDoubleSpinBox()
        self.spin_hue.setRange(-0.5, 0.5)
        self.spin_hue.setValue(0.05)
        self.spin_hue.setSingleStep(0.05)
        self.spin_hue.setLocale(QLocale(QLocale.C))
        jitter_layout.addWidget(self.spin_hue)
        jitter_layout.addWidget(QtWidgets.QLabel("Saturation:"))
        self.spin_saturation = QtWidgets.QDoubleSpinBox()
        self.spin_saturation.setRange(0.5, 2.0)
        self.spin_saturation.setValue(1.1)
        self.spin_saturation.setSingleStep(0.1)
        self.spin_saturation.setLocale(QLocale(QLocale.C))
        jitter_layout.addWidget(self.spin_saturation)
        group_layout.addWidget(self.check_color_jitter)
        group_layout.addLayout(jitter_layout)
        
        # Grayscale
        self.check_grayscale = QtWidgets.QCheckBox("Grayscale (Convert to B&W)")
        group_layout.addWidget(self.check_grayscale)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _add_noise_section(self, layout):
        """Noise and Effects"""
        group = QtWidgets.QGroupBox("🔊 Noise and Effects")
        group_layout = QtWidgets.QVBoxLayout()
        
        # Gaussian Blur
        self.check_blur = QtWidgets.QCheckBox("Gaussian Blur")
        blur_layout = QtWidgets.QHBoxLayout()
        blur_layout.addWidget(QtWidgets.QLabel("Kernel Size:"))
        self.spin_blur = QtWidgets.QSpinBox()
        self.spin_blur.setRange(3, 15)
        self.spin_blur.setValue(5)
        self.spin_blur.setSingleStep(2)
        self.spin_blur.setLocale(QLocale(QLocale.C))
        blur_layout.addWidget(self.spin_blur)
        group_layout.addWidget(self.check_blur)
        group_layout.addLayout(blur_layout)
        
        # Noise Addition
        self.check_noise = QtWidgets.QCheckBox("Add Noise")
        noise_layout = QtWidgets.QHBoxLayout()
        noise_layout.addWidget(QtWidgets.QLabel("Type:"))
        self.combo_noise_type = QtWidgets.QComboBox()
        self.combo_noise_type.addItems(["Gaussian", "Salt & Pepper"])
        noise_layout.addWidget(self.combo_noise_type)
        noise_layout.addWidget(QtWidgets.QLabel("Intensity:"))
        self.spin_noise = QtWidgets.QDoubleSpinBox()
        self.spin_noise.setRange(0, 50)
        self.spin_noise.setValue(25)
        self.spin_noise.setLocale(QLocale(QLocale.C))
        noise_layout.addWidget(self.spin_noise)
        group_layout.addWidget(self.check_noise)
        group_layout.addLayout(noise_layout)
        
        # Random Erasing
        self.check_erasing = QtWidgets.QCheckBox("Random Erasing")
        erasing_layout = QtWidgets.QHBoxLayout()
        erasing_layout.addWidget(QtWidgets.QLabel("Probability:"))
        self.spin_erasing_prob = QtWidgets.QDoubleSpinBox()
        self.spin_erasing_prob.setRange(0, 1)
        self.spin_erasing_prob.setValue(0.5)
        self.spin_erasing_prob.setSingleStep(0.1)
        self.spin_erasing_prob.setLocale(QLocale(QLocale.C))
        erasing_layout.addWidget(self.spin_erasing_prob)
        erasing_layout.addWidget(QtWidgets.QLabel("Area Ratio:"))
        self.spin_erasing_area = QtWidgets.QDoubleSpinBox()
        self.spin_erasing_area.setRange(0, 0.3)
        self.spin_erasing_area.setValue(0.1)
        self.spin_erasing_area.setSingleStep(0.05)
        self.spin_erasing_area.setLocale(QLocale(QLocale.C))
        erasing_layout.addWidget(self.spin_erasing_area)
        group_layout.addWidget(self.check_erasing)
        group_layout.addLayout(erasing_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _add_text_specific_section(self, layout):
        """Text-specific Adjustments (สำหรับ Recognition)"""
        group = QtWidgets.QGroupBox("📝 Text-specific")
        group_layout = QtWidgets.QVBoxLayout()
        
        # Sharpening
        self.check_sharpen = QtWidgets.QCheckBox("Sharpening")
        sharpen_layout = QtWidgets.QHBoxLayout()
        sharpen_layout.addWidget(QtWidgets.QLabel("Strength:"))
        self.spin_sharpen = QtWidgets.QDoubleSpinBox()
        self.spin_sharpen.setRange(0, 2)
        self.spin_sharpen.setValue(1.0)
        self.spin_sharpen.setSingleStep(0.1)
        self.spin_sharpen.setLocale(QLocale(QLocale.C))
        sharpen_layout.addWidget(self.spin_sharpen)
        group_layout.addWidget(self.check_sharpen)
        group_layout.addLayout(sharpen_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _sync_spin_slider(self, spinbox, slider):
        """Sync spinbox กับ slider"""
        spinbox.valueChanged.connect(lambda v: slider.setValue(int(v)))
        slider.valueChanged.connect(lambda v: spinbox.setValue(float(v)))
    
    def get_config(self) -> dict:
        """รับค่า config ที่ผู้ใช้เลือก"""
        config = {
            'mode': 'combinatorial' if self.radio_combinatorial.isChecked() else 'sequential',
            'augmentations': [],
            'target_splits': []  # เพิ่ม: splits ที่จะทำ augmentation
        }
        
        # เก็บ splits ที่เลือก
        if self.check_aug_train.isChecked():
            config['target_splits'].append('train')
        if self.check_aug_test.isChecked():
            config['target_splits'].append('test')
        if self.check_aug_valid.isChecked():
            config['target_splits'].append('valid')
        
        # Geometric
        if self.check_rotation.isChecked():
            config['augmentations'].append({
                'type': 'rotation',
                'params': {'angle': self.spin_rotation.value()}
            })
        
        if self.check_shear.isChecked():
            config['augmentations'].append({
                'type': 'shear',
                'params': {
                    'shear_x': self.spin_shear_x.value(),
                    'shear_y': self.spin_shear_y.value()
                }
            })
        
        if self.check_scale.isChecked():
            config['augmentations'].append({
                'type': 'scale',
                'params': {
                    'scale_x': self.spin_scale_x.value(),
                    'scale_y': self.spin_scale_y.value()
                }
            })
        
        if self.mode == 'detection' and self.check_perspective.isChecked():
            config['augmentations'].append({
                'type': 'perspective',
                'params': {'strength': self.spin_perspective.value()}
            })
        
        if self.mode == 'recognition' and self.check_crop.isChecked():
            config['augmentations'].append({
                'type': 'crop',
                'params': {'crop_ratio': self.spin_crop.value()}
            })
        
        # Color/Intensity
        if self.check_brightness.isChecked():
            config['augmentations'].append({
                'type': 'brightness_contrast',
                'params': {
                    'brightness': self.spin_brightness.value(),
                    'contrast': self.spin_contrast.value()
                }
            })
        
        if self.check_color_jitter.isChecked():
            config['augmentations'].append({
                'type': 'color_jitter',
                'params': {
                    'hue': self.spin_hue.value(),
                    'saturation': self.spin_saturation.value()
                }
            })
        
        if self.check_grayscale.isChecked():
            config['augmentations'].append({'type': 'grayscale', 'params': {}})
        
        # Noise
        if self.check_blur.isChecked():
            config['augmentations'].append({
                'type': 'blur',
                'params': {'kernel_size': self.spin_blur.value()}
            })
        
        if self.check_noise.isChecked():
            noise_type = 'gaussian' if self.combo_noise_type.currentText() == 'Gaussian' else 'salt_pepper'
            config['augmentations'].append({
                'type': 'noise',
                'params': {
                    'noise_type': noise_type,
                    'intensity': self.spin_noise.value()
                }
            })
        
        if self.check_erasing.isChecked():
            config['augmentations'].append({
                'type': 'random_erasing',
                'params': {
                    'prob': self.spin_erasing_prob.value(),
                    'area_ratio': self.spin_erasing_area.value()
                }
            })
        
        # Text-specific (recognition)
        if self.mode == 'recognition' and self.check_sharpen.isChecked():
            config['augmentations'].append({
                'type': 'sharpen',
                'params': {'strength': self.spin_sharpen.value()}
            })
        
        return config
    
    def accept(self):
        """Validate ก่อน accept"""
        config = self.get_config()
        
        if not config['augmentations']:
            QtWidgets.QMessageBox.warning(
                self, "Warning",
                "กรุณาเลือกอย่างน้อย 1 augmentation"
            )
            return
        
        if not config['target_splits']:
            QtWidgets.QMessageBox.warning(
                self, "Warning",
                "กรุณาเลือกอย่างน้อย 1 dataset split (Train/Test/Valid)"
            )
            return
        
        self.result = config
        super().accept()