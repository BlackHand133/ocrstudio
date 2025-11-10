# modules/gui/ui_components.py (Workspace System + Button Controls + Masking)

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


def create_toolbar(mainwin):
    """สร้าง Toolbar พร้อมเมนู Workspace และ Masking"""
    
    # ===== 1. WORKSPACE MENU =====
    workspace_menu = QtWidgets.QMenu("Workspace", mainwin)
    
    act = QtWidgets.QAction("Switch Workspace", mainwin)
    act.setShortcut("Ctrl+W")
    act.setToolTip("สลับไปยัง workspace อื่น")
    act.triggered.connect(mainwin.switch_workspace)
    workspace_menu.addAction(act)
    
    act = QtWidgets.QAction("New Workspace", mainwin)
    act.setToolTip("สร้าง workspace ใหม่")
    act.triggered.connect(mainwin.create_new_workspace)
    workspace_menu.addAction(act)
    
    workspace_menu.addSeparator()
    
    act = QtWidgets.QAction("New Version", mainwin)
    act.setShortcut("Ctrl+Shift+N")
    act.setToolTip("สร้าง version ใหม่")
    act.triggered.connect(mainwin.create_new_version)
    workspace_menu.addAction(act)
    
    act = QtWidgets.QAction("Switch Version", mainwin)
    act.setShortcut("Ctrl+Shift+V")
    act.setToolTip("สลับไป version อื่น")
    act.triggered.connect(mainwin.switch_version)
    workspace_menu.addAction(act)

    act = QtWidgets.QAction("Manage Versions", mainwin)
    act.setToolTip("จัดการ version ทั้งหมด (ดู, ลบ)")
    act.triggered.connect(mainwin.manage_versions)
    workspace_menu.addAction(act)

    workspace_menu.addSeparator()

    act = QtWidgets.QAction("Rename Workspace", mainwin)
    act.setToolTip("เปลี่ยนชื่อ workspace ปัจจุบัน")
    act.triggered.connect(mainwin.rename_current_workspace)
    workspace_menu.addAction(act)
    
    # ===== 2. FILE MENU =====
    file_menu = QtWidgets.QMenu("File", mainwin)
    
    act = QtWidgets.QAction("Open Folder", mainwin)
    act.setShortcut("Ctrl+O")
    act.triggered.connect(mainwin.open_folder)
    file_menu.addAction(act)
    
    file_menu.addSeparator()
    
    act = QtWidgets.QAction("✓ Check Annotated", mainwin)
    act.setToolTip("เช็คเฉพาะรูปที่มี Annotation")
    act.triggered.connect(mainwin.check_only_annotated)
    file_menu.addAction(act)
    
    act = QtWidgets.QAction("✗ Uncheck Unannotated", mainwin)
    act.setToolTip("ยกเลิกเช็ครูปที่ไม่มี Annotation")
    act.triggered.connect(mainwin.uncheck_unannotated)
    file_menu.addAction(act)
    
    # ===== 3. AUTO ANNOTATE MENU =====
    auto_menu = QtWidgets.QMenu("Auto Annotate", mainwin)
    
    act = QtWidgets.QAction("Auto Current", mainwin)
    act.setShortcut("Ctrl+C")
    act.setToolTip("รัน OCR เฉพาะรูปปัจจุบัน")
    act.triggered.connect(mainwin.auto_label_current)
    auto_menu.addAction(act)
    
    act = QtWidgets.QAction("Auto All", mainwin)
    act.setShortcut("Ctrl+A")
    act.setToolTip("รัน OCR ทุกรูปในโฟลเดอร์")
    act.triggered.connect(mainwin.auto_label_all)
    auto_menu.addAction(act)
    
    act = QtWidgets.QAction("Auto Selected", mainwin)
    act.setShortcut("Ctrl+Shift+A")
    act.setToolTip("รัน OCR เฉพาะรูปที่ Check (☑) ไว้")
    act.triggered.connect(mainwin.auto_label_selected)
    auto_menu.addAction(act)
    
    # ===== 4. EDIT MENU =====
    edit_menu = QtWidgets.QMenu("Edit", mainwin)
    
    act = QtWidgets.QAction("Draw Box", mainwin, checkable=True)
    act.setShortcut("D")
    act.setToolTip("เปิด/ปิดโหมดวาดกล่อง")
    act.triggered.connect(mainwin.toggle_draw_mode)
    mainwin.draw_action = act
    edit_menu.addAction(act)
    
    act = QtWidgets.QAction("Recognition Mode", mainwin, checkable=True)
    act.setShortcut("R")
    act.setToolTip("เปิด/ปิดตารางแก้ไข Transcription")
    act.triggered.connect(mainwin.toggle_recog_mode)
    edit_menu.addAction(act)
    
    edit_menu.addSeparator()
    
    act = QtWidgets.QAction("Delete Selected", mainwin)
    act.setShortcut("Del")
    act.setToolTip("ลบกล่องที่เลือก")
    act.triggered.connect(mainwin.delete_selected)
    edit_menu.addAction(act)
    
    # ===== 5. MASKING MENU (ใหม่!) =====
    mask_menu = QtWidgets.QMenu("🔒 Masking", mainwin)
    
    act = QtWidgets.QAction("Draw Mask", mainwin, checkable=True)
    act.setShortcut("M")
    act.setToolTip("เปิด/ปิดโหมดวาดพื้นที่ปกปิดข้อมูล")
    act.triggered.connect(mainwin.toggle_mask_mode)
    mainwin.mask_action = act
    mask_menu.addAction(act)
    
    mask_menu.addSeparator()
    
    act = QtWidgets.QAction("🎨 Choose Mask Color", mainwin)
    act.setShortcut("Ctrl+M")
    act.setToolTip("เลือกสีสำหรับปกปิดข้อมูล")
    act.triggered.connect(mainwin.choose_mask_color)
    mask_menu.addAction(act)
    
    act = QtWidgets.QAction("🎨 Change Selected Mask Color", mainwin)
    act.setToolTip("เปลี่ยนสีของ mask ที่เลือกอยู่")
    act.triggered.connect(mainwin.change_selected_mask_color)
    mask_menu.addAction(act)
    
    mask_menu.addSeparator()
    
    # Preset colors
    preset_menu = QtWidgets.QMenu("Quick Colors", mask_menu)
    
    for color_name in ['Black', 'White', 'Gray', 'Red', 'Blur']:
        act = QtWidgets.QAction(f"⬛ {color_name}", mainwin)
        act.triggered.connect(lambda checked, c=color_name: mainwin.set_mask_color_preset(c))
        preset_menu.addAction(act)
    
    mask_menu.addMenu(preset_menu)
    
    # ===== 6. TRANSFORM MENU =====
    transform_menu = QtWidgets.QMenu("Transform", mainwin)
    
    act = QtWidgets.QAction("🔄 Rotate Left 90°", mainwin)
    act.setShortcut("Ctrl+L")
    act.setToolTip("หมุนรูปซ้าย 90 องศา")
    act.triggered.connect(lambda: mainwin.rotate_image(-90))
    transform_menu.addAction(act)
    
    act = QtWidgets.QAction("🔄 Rotate Right 90°", mainwin)
    act.setShortcut("Ctrl+R")
    act.setToolTip("หมุนรูปขวา 90 องศา")
    act.triggered.connect(lambda: mainwin.rotate_image(90))
    transform_menu.addAction(act)
    
    act = QtWidgets.QAction("🔄 Rotate 180°", mainwin)
    act.setToolTip("หมุนรูป 180 องศา")
    act.triggered.connect(lambda: mainwin.rotate_image(180))
    transform_menu.addAction(act)
    
    transform_menu.addSeparator()
    
    act = QtWidgets.QAction("↺ Reset Rotation", mainwin)
    act.setToolTip("รีเซ็ตการหมุนรูป")
    act.triggered.connect(mainwin.reset_rotation)
    transform_menu.addAction(act)
    
    # ===== 7. EXPORT MENU =====
    export_menu = QtWidgets.QMenu("Export", mainwin)

    act = QtWidgets.QAction("Save Labels (Detection)", mainwin)
    act.setShortcut("Ctrl+S")
    act.setToolTip("บันทึก dataset สำหรับ Text Detection")
    act.triggered.connect(mainwin.save_labels)
    export_menu.addAction(act)

    act = QtWidgets.QAction("Export Recognition", mainwin)
    act.setShortcut("Ctrl+E")
    act.setToolTip("บันทึก dataset สำหรับ Text Recognition (crop รูป)")
    act.triggered.connect(mainwin.export_rec)
    export_menu.addAction(act)

    # ===== 8. SETTINGS MENU =====
    settings_menu = QtWidgets.QMenu("Settings", mainwin)

    act = QtWidgets.QAction("⚙️ Preferences", mainwin)
    act.setShortcut("Ctrl+,")
    act.setToolTip("ตั้งค่าโปรแกรม (OCR, Application)")
    act.triggered.connect(mainwin.open_settings)
    settings_menu.addAction(act)
    
    # ===== สร้าง Toolbar และเพิ่ม Menus =====
    toolbar = mainwin.addToolBar("Main Toolbar")
    toolbar.setMovable(False)
    
    # เพิ่ม Menu Buttons
    workspace_btn = QtWidgets.QToolButton()
    workspace_btn.setText("Workspace")
    workspace_btn.setMenu(workspace_menu)
    workspace_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(workspace_btn)
    
    file_btn = QtWidgets.QToolButton()
    file_btn.setText("File")
    file_btn.setMenu(file_menu)
    file_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(file_btn)
    
    auto_btn = QtWidgets.QToolButton()
    auto_btn.setText("Auto Annotate")
    auto_btn.setMenu(auto_menu)
    auto_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(auto_btn)
    
    edit_btn = QtWidgets.QToolButton()
    edit_btn.setText("Edit")
    edit_btn.setMenu(edit_menu)
    edit_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(edit_btn)
    
    # ปุ่ม Masking (ใหม่!)
    mask_btn = QtWidgets.QToolButton()
    mask_btn.setText("🔒 Masking")
    mask_btn.setMenu(mask_menu)
    mask_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(mask_btn)
    
    transform_btn = QtWidgets.QToolButton()
    transform_btn.setText("Transform")
    transform_btn.setMenu(transform_menu)
    transform_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(transform_btn)
    
    export_btn = QtWidgets.QToolButton()
    export_btn.setText("Export")
    export_btn.setMenu(export_menu)
    export_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(export_btn)

    settings_btn = QtWidgets.QToolButton()
    settings_btn.setText("⚙️ Settings")
    settings_btn.setMenu(settings_menu)
    settings_btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
    toolbar.addWidget(settings_btn)

    toolbar.addSeparator()
    
    # ===== WORKSPACE INFO =====
    workspace_label = QtWidgets.QLabel("  📁 No workspace loaded")
    workspace_label.setStyleSheet("color: #555; padding: 5px;")
    mainwin.workspace_label = workspace_label
    toolbar.addWidget(workspace_label)
    
    toolbar.addSeparator()
    
    # ===== MODE INDICATOR =====
    mode_label = QtWidgets.QLabel("  Mode: ")
    toolbar.addWidget(mode_label)
    
    mode_combo = QtWidgets.QComboBox()
    mode_combo.addItems(["Annotation", "Masking"])
    mode_combo.setCurrentText("Annotation")
    mode_combo.currentTextChanged.connect(mainwin.on_mode_changed)
    mainwin.mode_combo = mode_combo
    toolbar.addWidget(mode_combo)
    
    toolbar.addSeparator()
    
    # ===== ANNOTATION/MASK TYPE SELECTOR =====
    toolbar.addWidget(QtWidgets.QLabel("  Type: "))
    
    type_combo = QtWidgets.QComboBox()
    type_combo.addItems(["Quad", "Polygon"])
    type_combo.setCurrentText("Quad")
    type_combo.currentTextChanged.connect(mainwin.on_annotation_type_changed)
    mainwin.annotation_type_combo = type_combo
    toolbar.addWidget(type_combo)
    
    # ===== MASK COLOR BUTTON (ใหม่!) =====
    mask_color_btn = QtWidgets.QPushButton("🎨 Color")
    mask_color_btn.setToolTip("เลือกสีสำหรับ Mask")
    mask_color_btn.clicked.connect(mainwin.choose_mask_color)
    mask_color_btn.setVisible(False)  # ซ่อนไว้ก่อน จะแสดงเมื่อเปลี่ยนเป็น Masking mode
    mainwin.mask_color_btn = mask_color_btn
    toolbar.addWidget(mask_color_btn)
    
    # Info label
    info_label = QtWidgets.QLabel()
    info_label.setStyleSheet("color: gray; margin-left: 10px;")
    mainwin.annotation_info_label = info_label
    toolbar.addWidget(info_label)
    
    # อัปเดต info label
    mainwin.update_annotation_info()


def create_left_dock(mainwin):
    """สร้าง Left Dock พร้อมปุ่ม Select All / Deselect All"""
    container = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(0,0,0,0)
    
    # ===== ปุ่ม Select/Deselect Controls =====
    button_container = QtWidgets.QWidget()
    button_layout = QtWidgets.QHBoxLayout(button_container)
    button_layout.setContentsMargins(5, 5, 5, 5)
    button_layout.setSpacing(5)
    
    # ปุ่ม Select All
    btn_select_all = QtWidgets.QPushButton("☑ Select All")
    btn_select_all.setToolTip("เลือกทุกไฟล์ (Ctrl+Shift+A)")
    btn_select_all.setShortcut("Ctrl+Shift+A")
    btn_select_all.clicked.connect(mainwin.select_all_images)
    btn_select_all.setStyleSheet("""
        QPushButton {
            background-color: #e3f2fd;
            border: 1px solid #90caf9;
            padding: 5px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #bbdefb;
        }
        QPushButton:pressed {
            background-color: #90caf9;
        }
    """)
    
    # ปุ่ม Deselect All
    btn_deselect_all = QtWidgets.QPushButton("☐ Deselect All")
    btn_deselect_all.setToolTip("ยกเลิกการเลือกทุกไฟล์ (Ctrl+Shift+D)")
    btn_deselect_all.setShortcut("Ctrl+Shift+D")
    btn_deselect_all.clicked.connect(mainwin.deselect_all_images)
    btn_deselect_all.setStyleSheet("""
        QPushButton {
            background-color: #fff3e0;
            border: 1px solid #ffb74d;
            padding: 5px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #ffe0b2;
        }
        QPushButton:pressed {
            background-color: #ffb74d;
        }
    """)
    
    button_layout.addWidget(btn_select_all)
    button_layout.addWidget(btn_deselect_all)
    
    layout.addWidget(button_container)

    # ===== Image List =====
    lw = QtWidgets.QListWidget()
    lw.itemClicked.connect(mainwin.on_image_selected)
    mainwin.list_widget = lw
    layout.addWidget(lw, 1)

    # ===== Transcription Table =====
    tbl = QtWidgets.QTableWidget(0,2)
    tbl.setHorizontalHeaderLabels(['ID','Transcription'])
    tbl.horizontalHeader().setStretchLastSection(True)
    tbl.verticalHeader().hide()
    tbl.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
    tbl.itemChanged.connect(mainwin.on_table_item_changed)
    tbl.hide()
    mainwin.table = tbl
    layout.addWidget(tbl,1)

    dock = QtWidgets.QDockWidget("Images / Annotations", mainwin)
    dock.setWidget(container)
    dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable|
                     QtWidgets.QDockWidget.DockWidgetFloatable)
    mainwin.addDockWidget(Qt.LeftDockWidgetArea, dock)


def create_status_bar(mainwin):
    """สร้าง Status Bar"""
    sb = mainwin.statusBar()
    sb.showMessage("Ready")
    mainwin.status = sb