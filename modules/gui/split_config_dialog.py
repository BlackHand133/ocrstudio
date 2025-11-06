# modules/gui/split_config_dialog.py

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QLocale

class SplitConfigDialog(QtWidgets.QDialog):
    """
    Dialog สำหรับกำหนดค่าการแบ่งข้อมูล
    รองรับ train/test/valid แบบยืดหยุ่น
    """
    
    def __init__(self, parent=None, mode='detection', total_items=0):
        super().__init__(parent)
        self.mode = mode  # 'detection' or 'recognition'
        self.total_items = total_items
        self.result = None
        
        self.setWindowTitle(f"Split Configuration - {mode.title()}")
        self.setModal(True)
        self.resize(500, 600)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Info
        info_label = QtWidgets.QLabel(f"Total items: {self.total_items}")
        info_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(info_label)
        
        layout.addWidget(QtWidgets.QLabel("─" * 50))
        
        # === Split Method ===
        group_method = QtWidgets.QGroupBox("Split Method")
        method_layout = QtWidgets.QVBoxLayout()
        
        self.radio_percentage = QtWidgets.QRadioButton("By Percentage (%)")
        self.radio_percentage.setChecked(True)
        self.radio_count = QtWidgets.QRadioButton("By Count (Fixed)")
        
        method_layout.addWidget(self.radio_percentage)
        method_layout.addWidget(self.radio_count)
        group_method.setLayout(method_layout)
        layout.addWidget(group_method)
        
        # === Dataset Splits ===
        group_splits = QtWidgets.QGroupBox("Dataset Splits")
        splits_layout = QtWidgets.QFormLayout()
        
        # Train
        self.check_train = QtWidgets.QCheckBox("Train")
        self.check_train.setChecked(True)
        self.spin_train_pct = QtWidgets.QDoubleSpinBox()
        self.spin_train_pct.setRange(0, 100)
        self.spin_train_pct.setValue(80)
        self.spin_train_pct.setSuffix(" %")
        self.spin_train_pct.setLocale(QLocale(QLocale.C))
        
        self.spin_train_count = QtWidgets.QSpinBox()
        self.spin_train_count.setRange(0, 999999)
        self.spin_train_count.setValue(100)
        self.spin_train_count.setEnabled(False)
        self.spin_train_count.setLocale(QLocale(QLocale.C))
        
        train_layout = QtWidgets.QHBoxLayout()
        train_layout.addWidget(self.check_train)
        train_layout.addWidget(self.spin_train_pct)
        train_layout.addWidget(self.spin_train_count)
        splits_layout.addRow("", train_layout)
        
        # Test
        self.check_test = QtWidgets.QCheckBox("Test")
        self.spin_test_pct = QtWidgets.QDoubleSpinBox()
        self.spin_test_pct.setRange(0, 100)
        self.spin_test_pct.setValue(10)
        self.spin_test_pct.setSuffix(" %")
        self.spin_test_pct.setLocale(QLocale(QLocale.C))
        
        self.spin_test_count = QtWidgets.QSpinBox()
        self.spin_test_count.setRange(0, 999999)
        self.spin_test_count.setValue(10)
        self.spin_test_count.setEnabled(False)
        self.spin_test_count.setLocale(QLocale(QLocale.C))
        
        test_layout = QtWidgets.QHBoxLayout()
        test_layout.addWidget(self.check_test)
        test_layout.addWidget(self.spin_test_pct)
        test_layout.addWidget(self.spin_test_count)
        splits_layout.addRow("", test_layout)
        
        # Valid
        self.check_valid = QtWidgets.QCheckBox("Valid")
        self.spin_valid_pct = QtWidgets.QDoubleSpinBox()
        self.spin_valid_pct.setRange(0, 100)
        self.spin_valid_pct.setValue(10)
        self.spin_valid_pct.setSuffix(" %")
        self.spin_valid_pct.setLocale(QLocale(QLocale.C))
        
        self.spin_valid_count = QtWidgets.QSpinBox()
        self.spin_valid_count.setRange(0, 999999)
        self.spin_valid_count.setValue(10)
        self.spin_valid_count.setEnabled(False)
        self.spin_valid_count.setLocale(QLocale(QLocale.C))
        
        valid_layout = QtWidgets.QHBoxLayout()
        valid_layout.addWidget(self.check_valid)
        valid_layout.addWidget(self.spin_valid_pct)
        valid_layout.addWidget(self.spin_valid_count)
        splits_layout.addRow("", valid_layout)
        
        group_splits.setLayout(splits_layout)
        layout.addWidget(group_splits)
        
        # === Advanced Options ===
        group_advanced = QtWidgets.QGroupBox("Advanced Options")
        advanced_layout = QtWidgets.QVBoxLayout()
        
        # Random Seed
        seed_layout = QtWidgets.QHBoxLayout()
        self.check_seed = QtWidgets.QCheckBox("Random Seed:")
        self.spin_seed = QtWidgets.QSpinBox()
        self.spin_seed.setRange(0, 999999)
        self.spin_seed.setValue(42)
        self.spin_seed.setEnabled(False)
        self.spin_seed.setLocale(QLocale(QLocale.C))
        seed_layout.addWidget(self.check_seed)
        seed_layout.addWidget(self.spin_seed)
        seed_layout.addStretch()
        advanced_layout.addLayout(seed_layout)
        
        if self.mode == 'detection':
            # Density stratified
            self.check_density = QtWidgets.QCheckBox("Split by Text Density (Stratified)")
            self.combo_density = QtWidgets.QComboBox()
            self.combo_density.addItems(["Low → High", "High → Low", "Balanced"])
            self.combo_density.setEnabled(False)
            density_layout = QtWidgets.QHBoxLayout()
            density_layout.addWidget(self.check_density)
            density_layout.addWidget(self.combo_density)
            density_layout.addStretch()
            advanced_layout.addLayout(density_layout)
            
            # Curvature stratified
            self.check_curvature = QtWidgets.QCheckBox("Split by Curvature/Skew (Stratified)")
            self.combo_curvature = QtWidgets.QComboBox()
            self.combo_curvature.addItems(["Straight → Curved", "Curved → Straight", "Balanced"])
            self.combo_curvature.setEnabled(False)
            curvature_layout = QtWidgets.QHBoxLayout()
            curvature_layout.addWidget(self.check_curvature)
            curvature_layout.addWidget(self.combo_curvature)
            curvature_layout.addStretch()
            advanced_layout.addLayout(curvature_layout)
        
        elif self.mode == 'recognition':
            # Length stratified
            self.check_length = QtWidgets.QCheckBox("Split by Text Length (Stratified)")
            self.combo_length = QtWidgets.QComboBox()
            self.combo_length.addItems(["Short → Long", "Long → Short", "Balanced"])
            self.combo_length.setEnabled(False)
            length_layout = QtWidgets.QHBoxLayout()
            length_layout.addWidget(self.check_length)
            length_layout.addWidget(self.combo_length)
            length_layout.addStretch()
            advanced_layout.addLayout(length_layout)
        
        group_advanced.setLayout(advanced_layout)
        layout.addWidget(group_advanced)
        
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
        
        # === Connections ===
        self.radio_percentage.toggled.connect(self._on_method_changed)
        self.radio_count.toggled.connect(self._on_method_changed)
        self.check_seed.toggled.connect(self.spin_seed.setEnabled)
        
        if self.mode == 'detection':
            self.check_density.toggled.connect(self.combo_density.setEnabled)
            self.check_curvature.toggled.connect(self.combo_curvature.setEnabled)
        elif self.mode == 'recognition':
            self.check_length.toggled.connect(self.combo_length.setEnabled)
    
    def _on_method_changed(self):
        """สลับระหว่าง percentage และ count"""
        is_percentage = self.radio_percentage.isChecked()
        
        self.spin_train_pct.setEnabled(is_percentage)
        self.spin_test_pct.setEnabled(is_percentage)
        self.spin_valid_pct.setEnabled(is_percentage)
        
        self.spin_train_count.setEnabled(not is_percentage)
        self.spin_test_count.setEnabled(not is_percentage)
        self.spin_valid_count.setEnabled(not is_percentage)
    
    def get_config(self) -> dict:
        """รับค่า config ที่ผู้ใช้เลือก"""
        config = {
            'method': 'percentage' if self.radio_percentage.isChecked() else 'count',
            'splits': {},
            'seed': self.spin_seed.value() if self.check_seed.isChecked() else None,
            'advanced': {}
        }
        
        # Splits
        if self.check_train.isChecked():
            if config['method'] == 'percentage':
                config['splits']['train'] = self.spin_train_pct.value()
            else:
                config['splits']['train'] = self.spin_train_count.value()
        
        if self.check_test.isChecked():
            if config['method'] == 'percentage':
                config['splits']['test'] = self.spin_test_pct.value()
            else:
                config['splits']['test'] = self.spin_test_count.value()
        
        if self.check_valid.isChecked():
            if config['method'] == 'percentage':
                config['splits']['valid'] = self.spin_valid_pct.value()
            else:
                config['splits']['valid'] = self.spin_valid_count.value()
        
        # Validation
        if not config['splits']:
            return None  # ไม่มี split ใดถูกเลือก
        
        # Advanced options
        if self.mode == 'detection':
            if self.check_density.isChecked():
                config['advanced']['density'] = self.combo_density.currentText()
            if self.check_curvature.isChecked():
                config['advanced']['curvature'] = self.combo_curvature.currentText()
        elif self.mode == 'recognition':
            if self.check_length.isChecked():
                config['advanced']['length'] = self.combo_length.currentText()
        
        return config
    
    def accept(self):
        """Validate ก่อน accept"""
        config = self.get_config()
        
        if config is None:
            QtWidgets.QMessageBox.warning(
                self, "Warning",
                "กรุณาเลือกอย่างน้อย 1 dataset split (Train/Test/Valid)"
            )
            return
        
        # Validate percentage
        if config['method'] == 'percentage':
            total = sum(config['splits'].values())
            if total <= 0 or total > 100:
                QtWidgets.QMessageBox.warning(
                    self, "Warning",
                    f"Total percentage must be > 0 and <= 100\nCurrent: {total}%"
                )
                return
        
        # Validate count
        elif config['method'] == 'count':
            total = sum(config['splits'].values())
            if total > self.total_items:
                QtWidgets.QMessageBox.warning(
                    self, "Warning",
                    f"Not enough data!\nNeed: {total} items\nAvailable: {self.total_items} items"
                )
                return
        
        self.result = config
        super().accept()