# modules/gui/ui_components.py (Workspace System + Button Controls + Masking)

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
from modules.gui.styles import (
    TOOLBAR_BUTTON_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE,
    SUCCESS_BUTTON_STYLE, FILTER_BUTTON_STYLE, INPUT_STYLE, COMBO_BOX_STYLE,
    LIST_WIDGET_STYLE, TABLE_WIDGET_STYLE, SECTION_HEADER_STYLE,
    WORKSPACE_INFO_STYLE, get_full_stylesheet
)


def create_toolbar(mainwin):
    """Create Toolbar with Workspace and Masking menus"""

    # ===== 1. WORKSPACE MENU =====
    workspace_menu = QtWidgets.QMenu("Workspace", mainwin)

    # Recent Workspaces submenu
    recent_menu = QtWidgets.QMenu("Recent Workspaces", mainwin)
    mainwin.recent_workspaces_menu = recent_menu  # Store reference for dynamic updates
    workspace_menu.addMenu(recent_menu)

    workspace_menu.addSeparator()

    act = QtWidgets.QAction("Switch Workspace...", mainwin)
    act.setShortcut("Ctrl+W")
    act.setToolTip("Switch to another workspace")
    act.triggered.connect(mainwin.switch_workspace)
    workspace_menu.addAction(act)

    act = QtWidgets.QAction("New Workspace...", mainwin)
    act.setShortcut("Ctrl+N")
    act.setToolTip("Create new workspace")
    act.triggered.connect(mainwin.create_new_workspace)
    workspace_menu.addAction(act)

    workspace_menu.addSeparator()

    act = QtWidgets.QAction("New Version", mainwin)
    act.setShortcut("Ctrl+Shift+N")
    act.setToolTip("Create new version")
    act.triggered.connect(mainwin.create_new_version)
    workspace_menu.addAction(act)

    act = QtWidgets.QAction("Switch Version", mainwin)
    act.setShortcut("Ctrl+Shift+V")
    act.setToolTip("Switch to another version")
    act.triggered.connect(mainwin.switch_version)
    workspace_menu.addAction(act)

    act = QtWidgets.QAction("Manage Versions...", mainwin)
    act.setShortcut("Ctrl+M")
    act.setToolTip("Manage all versions (view, delete)")
    act.triggered.connect(mainwin.manage_versions)
    workspace_menu.addAction(act)

    workspace_menu.addSeparator()

    # Quick Navigation shortcuts
    act = QtWidgets.QAction("Next Version", mainwin)
    act.setShortcut("Ctrl+Tab")
    act.setToolTip("Switch to next version")
    act.triggered.connect(mainwin.next_version)
    workspace_menu.addAction(act)

    act = QtWidgets.QAction("Previous Version", mainwin)
    act.setShortcut("Ctrl+Shift+Tab")
    act.setToolTip("Switch to previous version")
    act.triggered.connect(mainwin.previous_version)
    workspace_menu.addAction(act)

    workspace_menu.addSeparator()

    act = QtWidgets.QAction("Rename Workspace", mainwin)
    act.setToolTip("Rename current workspace")
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
    act.setToolTip("Check only images with Annotation")
    act.triggered.connect(mainwin.check_only_annotated)
    file_menu.addAction(act)

    act = QtWidgets.QAction("✗ Uncheck Unannotated", mainwin)
    act.setToolTip("Uncheck images without Annotation")
    act.triggered.connect(mainwin.uncheck_unannotated)
    file_menu.addAction(act)

    # ===== 3. AUTO ANNOTATE MENU =====
    auto_menu = QtWidgets.QMenu("Auto Annotate", mainwin)

    act = QtWidgets.QAction("Auto Current", mainwin)
    act.setShortcut("Ctrl+D")
    act.setToolTip("Run OCR only on current image")
    act.triggered.connect(mainwin.auto_label_current)
    auto_menu.addAction(act)

    act = QtWidgets.QAction("Auto All", mainwin)
    act.setShortcut("Ctrl+Shift+D")
    act.setToolTip("Run OCR on all images in folder")
    act.triggered.connect(mainwin.auto_label_all)
    auto_menu.addAction(act)

    act = QtWidgets.QAction("Auto Selected", mainwin)
    act.setShortcut("Ctrl+Alt+D")
    act.setToolTip("Run OCR only on checked (☑) images")
    act.triggered.connect(mainwin.auto_label_selected)
    auto_menu.addAction(act)

    # ===== 4. EDIT MENU =====
    edit_menu = QtWidgets.QMenu("Edit", mainwin)

    # Undo/Redo actions
    act = QtWidgets.QAction("Undo", mainwin)
    act.setShortcut("Ctrl+Z")
    act.setToolTip("Undo last action")
    act.setEnabled(False)  # Disabled initially
    act.triggered.connect(mainwin.undo_action)
    mainwin.undo_action_item = act
    edit_menu.addAction(act)

    act = QtWidgets.QAction("Redo", mainwin)
    act.setShortcut("Ctrl+Y")
    act.setToolTip("Redo last undone action")
    act.setEnabled(False)  # Disabled initially
    act.triggered.connect(mainwin.redo_action)
    mainwin.redo_action_item = act
    edit_menu.addAction(act)

    edit_menu.addSeparator()

    # Copy/Cut/Paste
    act = QtWidgets.QAction("Copy", mainwin)
    act.setShortcut("Ctrl+C")
    act.setToolTip("Copy selected annotations")
    act.triggered.connect(mainwin.copy_annotations)
    edit_menu.addAction(act)

    act = QtWidgets.QAction("Cut", mainwin)
    act.setShortcut("Ctrl+X")
    act.setToolTip("Cut selected annotations")
    act.triggered.connect(mainwin.cut_annotations)
    edit_menu.addAction(act)

    act = QtWidgets.QAction("Paste", mainwin)
    act.setShortcut("Ctrl+V")
    act.setToolTip("Paste annotations from clipboard")
    act.triggered.connect(mainwin.paste_annotations)
    edit_menu.addAction(act)

    edit_menu.addSeparator()

    act = QtWidgets.QAction("Select All", mainwin)
    act.setShortcut("Ctrl+A")
    act.setToolTip("Select all annotations on current image")
    act.triggered.connect(mainwin.select_all_annotations)
    edit_menu.addAction(act)

    act = QtWidgets.QAction("Delete Selected", mainwin)
    act.setShortcut("Del")
    act.setToolTip("Delete selected box")
    act.triggered.connect(mainwin.delete_selected)
    edit_menu.addAction(act)

    edit_menu.addSeparator()

    act = QtWidgets.QAction("Draw Box", mainwin, checkable=True)
    act.setShortcut("D")
    act.setToolTip("Toggle box drawing mode (or press Space)")
    act.triggered.connect(mainwin.toggle_draw_mode)
    mainwin.draw_action = act
    edit_menu.addAction(act)

    act = QtWidgets.QAction("Recognition Mode", mainwin, checkable=True)
    act.setShortcut("R")
    act.setToolTip("Toggle Transcription editing table")
    act.triggered.connect(mainwin.toggle_recog_mode)
    edit_menu.addAction(act)
    
    # ===== 5. MASKING MENU (NEW!) =====
    mask_menu = QtWidgets.QMenu("🔒 Masking", mainwin)

    act = QtWidgets.QAction("Draw Mask", mainwin, checkable=True)
    act.setShortcut("M")
    act.setToolTip("Toggle data masking area drawing mode")
    act.triggered.connect(mainwin.toggle_mask_mode)
    mainwin.mask_action = act
    mask_menu.addAction(act)

    mask_menu.addSeparator()

    act = QtWidgets.QAction("🎨 Choose Mask Color", mainwin)
    act.setShortcut("Ctrl+M")
    act.setToolTip("Select color for data masking")
    act.triggered.connect(mainwin.choose_mask_color)
    mask_menu.addAction(act)

    act = QtWidgets.QAction("🎨 Change Selected Mask Color", mainwin)
    act.setToolTip("Change color of selected mask")
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
    act.setToolTip("Rotate image left 90 degrees")
    act.triggered.connect(lambda: mainwin.rotate_image(-90))
    transform_menu.addAction(act)

    act = QtWidgets.QAction("🔄 Rotate Right 90°", mainwin)
    act.setShortcut("Ctrl+R")
    act.setToolTip("Rotate image right 90 degrees")
    act.triggered.connect(lambda: mainwin.rotate_image(90))
    transform_menu.addAction(act)

    act = QtWidgets.QAction("🔄 Rotate 180°", mainwin)
    act.setToolTip("Rotate image 180 degrees")
    act.triggered.connect(lambda: mainwin.rotate_image(180))
    transform_menu.addAction(act)

    transform_menu.addSeparator()

    act = QtWidgets.QAction("↺ Reset Rotation", mainwin)
    act.setToolTip("Reset image rotation")
    act.triggered.connect(mainwin.reset_rotation)
    transform_menu.addAction(act)

    # ===== 7. VIEW MENU (NEW!) =====
    view_menu = QtWidgets.QMenu("View", mainwin)

    act = QtWidgets.QAction("Zoom In", mainwin)
    act.setShortcut("+")
    act.setToolTip("Zoom in (or Ctrl+Scroll)")
    act.triggered.connect(mainwin.zoom_in)
    view_menu.addAction(act)

    act = QtWidgets.QAction("Zoom Out", mainwin)
    act.setShortcut("-")
    act.setToolTip("Zoom out (or Ctrl+Scroll)")
    act.triggered.connect(mainwin.zoom_out)
    view_menu.addAction(act)

    view_menu.addSeparator()

    act = QtWidgets.QAction("Fit to Window", mainwin)
    act.setShortcut("F")
    act.setToolTip("Fit image to window (or press 0)")
    act.triggered.connect(mainwin.zoom_fit)
    view_menu.addAction(act)

    act = QtWidgets.QAction("Reset Zoom (100%)", mainwin)
    act.setShortcut("1")
    act.setToolTip("Reset zoom to 100%")
    act.triggered.connect(mainwin.zoom_reset)
    view_menu.addAction(act)

    view_menu.addSeparator()

    act = QtWidgets.QAction("Next Image", mainwin)
    act.setShortcut("PgDown")
    act.setToolTip("Go to next image (or Down arrow)")
    act.triggered.connect(mainwin.navigate_next_image)
    view_menu.addAction(act)

    act = QtWidgets.QAction("Previous Image", mainwin)
    act.setShortcut("PgUp")
    act.setToolTip("Go to previous image (or Up arrow)")
    act.triggered.connect(mainwin.navigate_prev_image)
    view_menu.addAction(act)

    # ===== 8. EXPORT MENU =====
    export_menu = QtWidgets.QMenu("Export", mainwin)

    act = QtWidgets.QAction("Export Detection Dataset", mainwin)
    act.setShortcut("Ctrl+Shift+E")
    act.setToolTip("Export dataset for Text Detection training")
    act.triggered.connect(mainwin.save_labels)
    export_menu.addAction(act)

    act = QtWidgets.QAction("Export Recognition Dataset", mainwin)
    act.setShortcut("Ctrl+E")
    act.setToolTip("Export dataset for Text Recognition (crop images)")
    act.triggered.connect(mainwin.export_rec)
    export_menu.addAction(act)

    # ===== 9. SETTINGS MENU =====
    settings_menu = QtWidgets.QMenu("Settings", mainwin)

    act = QtWidgets.QAction("⚙️ Preferences", mainwin)
    act.setShortcut("Ctrl+,")
    act.setToolTip("Program settings (OCR, Application)")
    act.triggered.connect(mainwin.open_settings)
    settings_menu.addAction(act)

    act = QtWidgets.QAction("🔧 PaddleOCR Settings", mainwin)
    act.setShortcut("Ctrl+Shift+P")
    act.setToolTip("PaddleOCR settings (Version, Custom Models, Parameters)")
    act.triggered.connect(mainwin.open_paddleocr_settings)
    settings_menu.addAction(act)

    # ===== 10. HELP MENU =====
    help_menu = QtWidgets.QMenu("Help", mainwin)

    act = QtWidgets.QAction("⌨️ Keyboard Shortcuts", mainwin)
    act.setShortcut("F1")
    act.setToolTip("Show keyboard shortcuts and help")
    act.triggered.connect(mainwin.show_help)
    help_menu.addAction(act)

    act = QtWidgets.QAction("ℹ️ About", mainwin)
    act.setToolTip("About this application")
    act.triggered.connect(mainwin.show_about)
    help_menu.addAction(act)

    # ===== Create Toolbar and add Menus =====
    toolbar = mainwin.addToolBar("Main Toolbar")
    toolbar.setMovable(False)
    toolbar.setStyleSheet("""
        QToolBar {
            background-color: #FFFFFF;
            border-bottom: 1px solid #E0E0E0;
            spacing: 2px;
            padding: 4px 8px;
        }
        QToolBar::separator {
            width: 1px;
            background-color: #E0E0E0;
            margin: 4px 6px;
        }
    """)

    # Helper function to create styled menu buttons
    def create_menu_button(text, menu, icon=None):
        btn = QtWidgets.QToolButton()
        btn.setText(text)
        btn.setMenu(menu)
        btn.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        btn.setStyleSheet(TOOLBAR_BUTTON_STYLE)
        return btn

    # ===== GROUP 1: File Operations =====
    toolbar.addWidget(create_menu_button("File", file_menu))
    toolbar.addWidget(create_menu_button("Workspace", workspace_menu))

    toolbar.addSeparator()

    # ===== GROUP 2: Annotation Tools =====
    toolbar.addWidget(create_menu_button("Edit", edit_menu))
    toolbar.addWidget(create_menu_button("Auto", auto_menu))
    toolbar.addWidget(create_menu_button("Mask", mask_menu))

    toolbar.addSeparator()

    # ===== GROUP 3: View & Transform =====
    toolbar.addWidget(create_menu_button("View", view_menu))
    toolbar.addWidget(create_menu_button("Transform", transform_menu))

    toolbar.addSeparator()

    # ===== GROUP 4: Export =====
    toolbar.addWidget(create_menu_button("Export", export_menu))

    toolbar.addSeparator()

    # ===== QUICK ACTION BUTTONS =====
    # Mode selector with better styling
    mode_container = QtWidgets.QWidget()
    mode_layout = QtWidgets.QHBoxLayout(mode_container)
    mode_layout.setContentsMargins(4, 0, 4, 0)
    mode_layout.setSpacing(4)

    mode_label = QtWidgets.QLabel("Mode:")
    mode_label.setStyleSheet("color: #616161; font-size: 11px;")
    mode_layout.addWidget(mode_label)

    mode_combo = QtWidgets.QComboBox()
    mode_combo.addItems(["Annotation", "Masking"])
    mode_combo.setCurrentText("Annotation")
    mode_combo.setStyleSheet(COMBO_BOX_STYLE + "QComboBox { min-width: 90px; padding: 4px 8px; }")
    mode_combo.currentTextChanged.connect(mainwin.on_mode_changed)
    mainwin.mode_combo = mode_combo
    mode_layout.addWidget(mode_combo)

    toolbar.addWidget(mode_container)

    # Type selector
    type_container = QtWidgets.QWidget()
    type_layout = QtWidgets.QHBoxLayout(type_container)
    type_layout.setContentsMargins(4, 0, 4, 0)
    type_layout.setSpacing(4)

    type_label = QtWidgets.QLabel("Type:")
    type_label.setStyleSheet("color: #616161; font-size: 11px;")
    type_layout.addWidget(type_label)

    type_combo = QtWidgets.QComboBox()
    type_combo.addItems(["Quad", "Polygon"])
    type_combo.setCurrentText("Quad")
    type_combo.setStyleSheet(COMBO_BOX_STYLE + "QComboBox { min-width: 70px; padding: 4px 8px; }")
    type_combo.currentTextChanged.connect(mainwin.on_annotation_type_changed)
    mainwin.annotation_type_combo = type_combo
    type_layout.addWidget(type_combo)

    toolbar.addWidget(type_container)

    # Mask color button (hidden by default)
    mask_color_btn = QtWidgets.QPushButton("Color")
    mask_color_btn.setToolTip("Select mask color")
    mask_color_btn.clicked.connect(mainwin.choose_mask_color)
    mask_color_btn.setVisible(False)
    mask_color_btn.setStyleSheet(SECONDARY_BUTTON_STYLE + "QPushButton { padding: 4px 8px; }")
    mainwin.mask_color_btn = mask_color_btn
    toolbar.addWidget(mask_color_btn)

    toolbar.addSeparator()

    # ===== SAVE BUTTON =====
    save_btn = QtWidgets.QPushButton("Save")
    save_btn.setToolTip("Save annotations (Ctrl+S)")
    save_btn.setShortcut("Ctrl+S")
    save_btn.clicked.connect(mainwin.save_annotations_explicitly)
    save_btn.setStyleSheet(SUCCESS_BUTTON_STYLE + "QPushButton { padding: 6px 16px; }")
    mainwin.save_btn = save_btn
    toolbar.addWidget(save_btn)

    # Spacer to push remaining items to right
    spacer = QtWidgets.QWidget()
    spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    toolbar.addWidget(spacer)

    # ===== WORKSPACE INFO (right side) =====
    workspace_label = QtWidgets.QLabel("No workspace")
    workspace_label.setStyleSheet(WORKSPACE_INFO_STYLE)
    mainwin.workspace_label = workspace_label
    toolbar.addWidget(workspace_label)

    toolbar.addSeparator()

    # ===== HELP & SETTINGS (right side) =====
    toolbar.addWidget(create_menu_button("Settings", settings_menu))
    toolbar.addWidget(create_menu_button("Help", help_menu))

    # Info label (hidden - use status bar instead)
    info_label = QtWidgets.QLabel()
    info_label.setVisible(False)
    mainwin.annotation_info_label = info_label

    # Update info label
    mainwin.update_annotation_info()


def create_left_dock(mainwin):
    """Create Left Dock with improved organization and styling"""
    container = QtWidgets.QWidget()
    container.setStyleSheet("background-color: #FAFAFA;")
    layout = QtWidgets.QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # ===== IMAGES SECTION =====
    images_section = QtWidgets.QWidget()
    images_section.setStyleSheet("background-color: #FFFFFF;")
    images_layout = QtWidgets.QVBoxLayout(images_section)
    images_layout.setContentsMargins(8, 8, 8, 8)
    images_layout.setSpacing(8)

    # Section header
    images_header = QtWidgets.QLabel("IMAGES")
    images_header.setStyleSheet(SECTION_HEADER_STYLE)
    images_layout.addWidget(images_header)

    # Search box
    search_input = QtWidgets.QLineEdit()
    search_input.setPlaceholderText("Search images or text...")
    search_input.setClearButtonEnabled(True)
    search_input.setStyleSheet(INPUT_STYLE)
    search_input.textChanged.connect(mainwin.on_search_text_changed)
    mainwin.search_input = search_input
    images_layout.addWidget(search_input)

    # Filter buttons row
    filter_container = QtWidgets.QWidget()
    filter_layout = QtWidgets.QHBoxLayout(filter_container)
    filter_layout.setContentsMargins(0, 0, 0, 0)
    filter_layout.setSpacing(4)

    filter_all = QtWidgets.QToolButton()
    filter_all.setText("All")
    filter_all.setCheckable(True)
    filter_all.setChecked(True)
    filter_all.setToolTip("Show all images")
    filter_all.setStyleSheet(FILTER_BUTTON_STYLE)
    filter_all.clicked.connect(lambda: mainwin.apply_filter("all"))
    mainwin.filter_all_btn = filter_all

    filter_annotated = QtWidgets.QToolButton()
    filter_annotated.setText("Labeled")
    filter_annotated.setCheckable(True)
    filter_annotated.setToolTip("Show only labeled images")
    filter_annotated.setStyleSheet(FILTER_BUTTON_STYLE)
    filter_annotated.clicked.connect(lambda: mainwin.apply_filter("annotated"))
    mainwin.filter_annotated_btn = filter_annotated

    filter_empty = QtWidgets.QToolButton()
    filter_empty.setText("Empty")
    filter_empty.setCheckable(True)
    filter_empty.setToolTip("Show only unlabeled images")
    filter_empty.setStyleSheet(FILTER_BUTTON_STYLE)
    filter_empty.clicked.connect(lambda: mainwin.apply_filter("empty"))
    mainwin.filter_empty_btn = filter_empty

    filter_layout.addWidget(filter_all)
    filter_layout.addWidget(filter_annotated)
    filter_layout.addWidget(filter_empty)
    filter_layout.addStretch()

    # Search result label
    search_result_label = QtWidgets.QLabel("")
    search_result_label.setStyleSheet("color: #9E9E9E; font-size: 11px;")
    mainwin.search_result_label = search_result_label
    filter_layout.addWidget(search_result_label)

    images_layout.addWidget(filter_container)

    # Image List
    lw = QtWidgets.QListWidget()
    lw.setStyleSheet(LIST_WIDGET_STYLE)
    lw.itemClicked.connect(mainwin.on_image_selected)
    mainwin.list_widget = lw
    images_layout.addWidget(lw, 1)

    # Selection buttons
    selection_container = QtWidgets.QWidget()
    selection_layout = QtWidgets.QHBoxLayout(selection_container)
    selection_layout.setContentsMargins(0, 4, 0, 0)
    selection_layout.setSpacing(4)

    btn_select_all = QtWidgets.QPushButton("Select All")
    btn_select_all.setToolTip("Select all images for export")
    btn_select_all.clicked.connect(mainwin.select_all_images)
    btn_select_all.setStyleSheet(SECONDARY_BUTTON_STYLE + "QPushButton { padding: 4px 8px; font-size: 11px; }")

    btn_deselect_all = QtWidgets.QPushButton("Deselect All")
    btn_deselect_all.setToolTip("Deselect all images")
    btn_deselect_all.clicked.connect(mainwin.deselect_all_images)
    btn_deselect_all.setStyleSheet(SECONDARY_BUTTON_STYLE + "QPushButton { padding: 4px 8px; font-size: 11px; }")

    selection_layout.addWidget(btn_select_all)
    selection_layout.addWidget(btn_deselect_all)
    selection_layout.addStretch()

    images_layout.addWidget(selection_container)

    layout.addWidget(images_section, 1)

    # Divider
    divider = QtWidgets.QFrame()
    divider.setFrameShape(QtWidgets.QFrame.HLine)
    divider.setStyleSheet("background-color: #E0E0E0;")
    divider.setFixedHeight(1)
    layout.addWidget(divider)

    # ===== TRANSCRIPTION SECTION =====
    transcription_section = QtWidgets.QWidget()
    transcription_section.setStyleSheet("background-color: #FFFFFF;")
    transcription_layout = QtWidgets.QVBoxLayout(transcription_section)
    transcription_layout.setContentsMargins(8, 8, 8, 8)
    transcription_layout.setSpacing(8)

    # Section header with toggle
    trans_header_container = QtWidgets.QWidget()
    trans_header_layout = QtWidgets.QHBoxLayout(trans_header_container)
    trans_header_layout.setContentsMargins(0, 0, 0, 0)

    trans_header = QtWidgets.QLabel("TRANSCRIPTIONS")
    trans_header.setStyleSheet(SECTION_HEADER_STYLE)
    trans_header_layout.addWidget(trans_header)

    trans_header_layout.addStretch()

    # Recognition mode toggle
    recog_toggle = QtWidgets.QPushButton("Edit Mode")
    recog_toggle.setCheckable(True)
    recog_toggle.setToolTip("Toggle transcription editing (R)")
    recog_toggle.setStyleSheet("""
        QPushButton {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #F5F5F5;
        }
        QPushButton:checked {
            background-color: #E3F2FD;
            border-color: #2196F3;
            color: #1976D2;
        }
    """)
    recog_toggle.clicked.connect(mainwin.toggle_recog_mode)
    mainwin.recog_toggle_btn = recog_toggle
    trans_header_layout.addWidget(recog_toggle)

    transcription_layout.addWidget(trans_header_container)

    # Transcription Table
    tbl = QtWidgets.QTableWidget(0, 2)
    tbl.setHorizontalHeaderLabels(['#', 'Transcription'])
    tbl.horizontalHeader().setStretchLastSection(True)
    tbl.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
    tbl.setColumnWidth(0, 40)
    tbl.verticalHeader().hide()
    tbl.verticalHeader().setDefaultSectionSize(40)  # Set default row height
    tbl.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
    tbl.setStyleSheet(TABLE_WIDGET_STYLE)
    tbl.itemChanged.connect(mainwin.on_table_item_changed)
    tbl.setMinimumHeight(150)
    mainwin.table = tbl
    transcription_layout.addWidget(tbl, 1)

    # Help text
    help_label = QtWidgets.QLabel("Double-click to edit transcription")
    help_label.setStyleSheet("color: #9E9E9E; font-size: 10px; font-style: italic;")
    help_label.setAlignment(Qt.AlignCenter)
    transcription_layout.addWidget(help_label)

    layout.addWidget(transcription_section, 1)

    # Create dock
    dock = QtWidgets.QDockWidget("", mainwin)
    dock.setWidget(container)
    dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable | QtWidgets.QDockWidget.DockWidgetFloatable)
    dock.setTitleBarWidget(QtWidgets.QWidget())  # Hide title bar
    dock.setMinimumWidth(280)
    mainwin.addDockWidget(Qt.LeftDockWidgetArea, dock)
    mainwin.left_dock = dock


def create_status_bar(mainwin):
    """Create Status Bar with enhanced information display"""
    sb = mainwin.statusBar()
    sb.setStyleSheet("""
        QStatusBar {
            background-color: #FFFFFF;
            border-top: 1px solid #E0E0E0;
            padding: 4px;
        }
        QStatusBar::item {
            border: none;
        }
    """)

    # Left side: Main message
    mainwin.status = sb

    # Right side: Permanent widgets
    # Annotation count
    annotation_count_label = QtWidgets.QLabel("0 annotations")
    annotation_count_label.setStyleSheet("color: #616161; padding: 0 8px;")
    mainwin.annotation_count_label = annotation_count_label
    sb.addPermanentWidget(annotation_count_label)

    # Separator
    sep1 = QtWidgets.QLabel("|")
    sep1.setStyleSheet("color: #E0E0E0;")
    sb.addPermanentWidget(sep1)

    # Image progress
    progress_label = QtWidgets.QLabel("0/0 images")
    progress_label.setStyleSheet("color: #616161; padding: 0 8px;")
    mainwin.progress_label = progress_label
    sb.addPermanentWidget(progress_label)

    # Separator
    sep2 = QtWidgets.QLabel("|")
    sep2.setStyleSheet("color: #E0E0E0;")
    sb.addPermanentWidget(sep2)

    # Zoom level
    zoom_label = QtWidgets.QLabel("100%")
    zoom_label.setStyleSheet("color: #616161; padding: 0 8px;")
    mainwin.zoom_label = zoom_label
    sb.addPermanentWidget(zoom_label)

    # Separator
    sep3 = QtWidgets.QLabel("|")
    sep3.setStyleSheet("color: #E0E0E0;")
    sb.addPermanentWidget(sep3)

    # Mode indicator
    mode_status_label = QtWidgets.QLabel("View")
    mode_status_label.setStyleSheet("color: #616161; padding: 0 8px;")
    mainwin.mode_status_label = mode_status_label
    sb.addPermanentWidget(mode_status_label)

    sb.showMessage("Ready")