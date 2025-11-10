# modules/gui/main_window.py (Workspace System + Masking Feature)

import os
import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from modules.detector import TextDetector
from modules.workspace_manager import WorkspaceManager
from modules.gui.canvas_view import CanvasView
from modules.gui.ui_components import create_toolbar, create_left_dock, create_status_bar
from modules.gui.workspace_selector_dialog import WorkspaceSelectorDialog
from modules.gui.window_handler import (
    WorkspaceHandler,
    ImageHandler,
    AnnotationHandler,
    DetectionHandler,
    UIHandler,
    TableHandler,
    ExportHandler,
    RotationHandler
)

logger = logging.getLogger("TextDetGUI")


class MainWindow(QtWidgets.QMainWindow):
    """
    หน้าต่างหลักของแอปพลิเคชัน (Workspace System + Masking)
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize detector (ใช้ config จาก config/config.yaml)
        self.detector = TextDetector()  # ไม่ส่ง parameters = ใช้ config.yaml
        
        # Data attributes
        self.image_items = []      # List of (key, full_path)
        self.img_key = None         # Current image key
        self.img_path = None        # Current image path
        self.box_items = []         # List of BoxItem/PolygonItem/MaskItem
        self.annotations = {}       # Dict: key -> list of annotations
        self.draw_mode = False      # Drawing mode flag
        self.recog_mode = False     # Recognition mode flag
        self.annotation_type = 'Quad'  # 'Quad' or 'Polygon'
        self.mask_mode = False      # 🔒 Masking mode flag (NEW!)
        self.image_rotations = {}   # Dict: key -> rotation angle
        
        # Path setup
        this = os.path.abspath(__file__)
        root = os.path.dirname(os.path.dirname(os.path.dirname(this)))
        self.root_dir = root
        self.output_det_dir = os.path.join(root, "output_det")
        self.output_rec_dir = os.path.join(root, "output_rec")
        self.output_dir = os.path.join(root, "output")
        
        # Create output directories
        os.makedirs(self.output_det_dir, exist_ok=True)
        os.makedirs(self.output_rec_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize workspace manager
        self.workspace_manager = WorkspaceManager(root)
        
        # Initialize handlers
        self._init_handlers()
        
        # Initialize UI
        self._init_ui()
        
        # Select workspace
        self._select_initial_workspace()
    
    def _init_handlers(self):
        """สร้าง handler instances"""
        self.workspace_handler = WorkspaceHandler(self)
        self.image_handler = ImageHandler(self)
        self.annotation_handler = AnnotationHandler(self)
        self.detection_handler = DetectionHandler(self)
        self.ui_handler = UIHandler(self)
        self.table_handler = TableHandler(self)
        self.export_handler = ExportHandler(self)
        self.rotation_handler = RotationHandler(self)
        
        # 🔒 Mask Handler (NEW!)
        from modules.gui.mask_handler import MaskHandler
        self.mask_handler = MaskHandler(self)
    
    def _init_ui(self):
        """สร้าง UI"""
        self.setWindowTitle("TextDet GUI - Workspace System")
        self.resize(1400, 900)
        
        # Create scene and view
        self.scene = QtWidgets.QGraphicsScene()
        self.view = CanvasView(self)
        self.view.setScene(self.scene)
        self.setCentralWidget(self.view)
        
        # Create UI components
        create_toolbar(self)
        create_left_dock(self)
        create_status_bar(self)
        
        # Setup table
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self.table_handler.on_table_selection_changed)
        self.table.itemChanged.connect(self.table_handler.on_table_item_changed)
        
        # Icon for marked items
        self.icon_marked = self.style().standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
        
        logger.info("MainWindow initialized")
    
    def _select_initial_workspace(self):
        """เลือก workspace เมื่อเริ่มโปรแกรม"""
        # ตรวจสอบว่ามี workspace หรือไม่
        workspaces = self.workspace_manager.get_workspace_list()
        
        if not workspaces:
            # ไม่มี workspace -> แสดง dialog
            self._show_workspace_selector()
        else:
            # ลองโหลด workspace ล่าสุด
            current_ws = self.workspace_manager.app_config.get("current_workspace")
            
            if current_ws:
                success = self.workspace_handler.load_workspace(current_ws)
                if success:
                    # โหลดสำเร็จ -> อัปเดต UI
                    self._update_workspace_ui()
                    return
            
            # ถ้าโหลดไม่สำเร็จ -> แสดง selector
            self._show_workspace_selector()
    
    def _show_workspace_selector(self):
        """แสดง workspace selector dialog"""
        dialog = WorkspaceSelectorDialog(self.workspace_manager, self)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            workspace_id = dialog.selected_workspace
            if workspace_id:
                self.workspace_handler.load_workspace(workspace_id)
                self._update_workspace_ui()
        else:
            # User กด cancel -> ออกจากโปรแกรม
            logger.info("No workspace selected. Exiting...")
            QtWidgets.QApplication.quit()
    
    def _update_workspace_ui(self):
        """อัปเดต UI หลังโหลด workspace"""
        ws_info = self.workspace_handler.get_workspace_info()
        
        if ws_info:
            # อัปเดต window title
            title = f"TextDet GUI - {ws_info['name']} ({ws_info['current_version']})"
            self.setWindowTitle(title)
            
            # อัปเดต workspace label
            if hasattr(self, 'workspace_label'):
                self.workspace_label.setText(
                    f"  📁 {ws_info['name']} ({ws_info['current_version']})"
                )
            
            logger.info(f"Workspace loaded: {ws_info['name']}")
    
    # ===== Workspace Methods =====
    
    def switch_workspace(self):
        """สลับ workspace"""
        # บันทึก workspace ปัจจุบันก่อน
        if self.workspace_handler.current_workspace_id:
            self.workspace_handler.save_workspace()
        
        # แสดง selector
        self._show_workspace_selector()
    
    def create_new_workspace(self):
        """สร้าง workspace ใหม่"""
        from modules.gui.workspace_selector_dialog import NewWorkspaceDialog
        
        dialog = NewWorkspaceDialog(self.workspace_manager, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            workspace_id = dialog.workspace_id
            if workspace_id:
                self.workspace_handler.load_workspace(workspace_id)
                self._update_workspace_ui()
    
    def create_new_version(self):
        """สร้าง version ใหม่"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return
        
        # Dialog สำหรับสร้าง version
        ws_info = self.workspace_handler.get_workspace_info()
        current_version = ws_info.get("current_version", "v1")
        available_versions = ws_info.get("available_versions", [])
        
        # หาเบอร์ version ใหม่
        next_num = 1
        for v in available_versions:
            if v.startswith('v'):
                try:
                    num = int(v[1:])
                    next_num = max(next_num, num + 1)
                except:
                    pass
        
        new_version = f"v{next_num}"
        
        description, ok = QtWidgets.QInputDialog.getText(
            self, "New Version",
            f"Create new version: {new_version}\n\n"
            f"Will be based on: {current_version}\n\n"
            "Description:",
            QtWidgets.QLineEdit.Normal,
            f"Version {next_num}"
        )
        
        if ok:
            success = self.workspace_handler.create_new_version(
                new_version,
                description=description
            )
            
            if success:
                self._update_workspace_ui()
                QtWidgets.QMessageBox.information(
                    self, "Success",
                    f"Created version: {new_version}\n\n"
                    f"You are now working on {new_version}"
                )
    
    def switch_version(self):
        """สลับ version"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return

        ws_info = self.workspace_handler.get_workspace_info()
        available_versions = ws_info.get("available_versions", [])
        current_version = ws_info.get("current_version", "")

        if not available_versions:
            return

        version, ok = QtWidgets.QInputDialog.getItem(
            self, "Switch Version",
            "Select version:",
            available_versions,
            available_versions.index(current_version) if current_version in available_versions else 0,
            False
        )

        if ok and version and version != current_version:
            success = self.workspace_handler.switch_version(version)

            if success:
                # ล้างหน้าจอ
                self.scene.clear()
                self.box_items.clear()
                self.list_widget.clear()

                self._update_workspace_ui()

                QtWidgets.QMessageBox.information(
                    self, "Success",
                    f"Switched to version: {version}"
                )

    def manage_versions(self):
        """จัดการ version ทั้งหมด"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return

        from modules.gui.version_manager_dialog import VersionManagerDialog

        dialog = VersionManagerDialog(self.workspace_handler, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # รีเฟรช UI หลังจากมีการเปลี่ยนแปลง version
            self.scene.clear()
            self.box_items.clear()
            self.list_widget.clear()
            self._update_workspace_ui()

    def rename_current_workspace(self):
        """เปลี่ยนชื่อ workspace ปัจจุบัน"""
        if not self.workspace_handler.current_workspace_id:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No workspace loaded"
            )
            return

        ws_info = self.workspace_handler.get_workspace_info()
        old_name = ws_info.get('name', '')

        # แสดง dialog สำหรับกรอกชื่อใหม่
        new_name, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename Workspace",
            "Enter new workspace name:",
            QtWidgets.QLineEdit.Normal,
            old_name
        )

        if ok and new_name.strip():
            success, message = self.workspace_handler.rename_workspace(new_name.strip())

            if success:
                QtWidgets.QMessageBox.information(
                    self, "Success", message
                )
                # อัพเดต UI
                self._update_workspace_ui()
            else:
                QtWidgets.QMessageBox.critical(
                    self, "Error", message
                )

    def open_settings(self):
        """เปิด Settings Dialog"""
        from modules.gui.settings_dialog import SettingsDialog
        from modules.config_loader import get_loader

        dialog = SettingsDialog(get_loader(), self)

        # เชื่อม signal สำหรับ reload detector
        dialog.settings_changed.connect(self._reload_detector)

        dialog.exec_()

    def _reload_detector(self):
        """Reload OCR detector หลังจาก settings เปลี่ยน"""
        try:
            logger.info("Reloading OCR detector with new settings...")
            self.detector = TextDetector()  # สร้าง detector ใหม่ตาม config

            QtWidgets.QMessageBox.information(
                self,
                "Settings Applied",
                "Settings have been saved successfully.\nOCR detector has been reloaded."
            )

            logger.info("OCR detector reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload detector: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to reload OCR detector:\n{str(e)}"
            )

    # ===== Delegated Methods =====
    
    # Workspace Handler
    def _save_cache(self):
        """บันทึก workspace (แบบ cache)"""
        self.workspace_handler.save_workspace()
    
    # Image Handler
    def open_folder(self, *args):
        """เปิดโฟลเดอร์รูปภาพ"""
        self.image_handler.open_folder()
    
    def on_image_selected(self, item):
        """เมื่อเลือกรูปจาก list"""
        self.image_handler.on_image_selected(item)
    
    def check_only_annotated(self):
        """เช็คเฉพาะรูปที่มี annotation"""
        self.image_handler.check_only_annotated()
    
    def uncheck_unannotated(self):
        """ยกเลิกเช็ครูปที่ไม่มี annotation"""
        self.image_handler.uncheck_unannotated()
    
    def select_all_images(self):
        """เลือกทุกรูป (Select All)"""
        self.image_handler.select_all_images()
    
    def deselect_all_images(self):
        """ยกเลิกการเลือกทุกรูป (Deselect All)"""
        self.image_handler.deselect_all_images()
    
    def _is_item_checked(self, key):
        """ตรวจสอบว่ารูปถูกเช็คหรือไม่"""
        return self.image_handler.is_item_checked(key)
    
    # Annotation Handler
    def delete_selected(self, *args):
        """ลบ annotation ที่เลือก"""
        self.annotation_handler.delete_selected()
    
    # Detection Handler
    def auto_label_current(self, *args):
        """Auto-detect รูปปัจจุบัน"""
        self.detection_handler.auto_label_current()
    
    def auto_label_all(self, *args):
        """Auto-detect รูปทั้งหมด"""
        self.detection_handler.auto_label_all()
    
    def auto_label_selected(self, *args):
        """Auto-detect รูปที่เลือกไว้เท่านั้น"""
        self.detection_handler.auto_label_selected()
    
    # UI Handler
    def toggle_draw_mode(self, checked):
        """เปิด/ปิดโหมดวาดกล่อง"""
        self.draw_mode = checked
        
        # ปิด mask_mode ถ้าเปิด draw_mode
        if checked and self.mask_mode:
            self.mask_mode = False
            if hasattr(self, 'mask_action'):
                self.mask_action.setChecked(False)
        
        # อัปเดต mode combo
        if hasattr(self, 'mode_combo'):
            self.mode_combo.setCurrentText("Annotation")
        
        self.ui_handler.toggle_draw_mode(checked)
    
    def toggle_recog_mode(self, checked):
        """เปิด/ปิดโหมด Recognition"""
        self.ui_handler.toggle_recog_mode(checked)
    
    def on_annotation_type_changed(self, new_type):
        """เปลี่ยนประเภท annotation"""
        self.ui_handler.on_annotation_type_changed(new_type)
    
    def update_annotation_info(self):
        """อัปเดตข้อมูลสำนักงาน"""
        self.ui_handler.update_annotation_info()
    
    def add_box_from_rect(self, rect):
        """เพิ่มกล่อง Quad จาก rectangle"""
        self.ui_handler.add_box_from_rect(rect)
    
    def add_polygon_from_points(self, points):
        """เพิ่ม polygon จาก points"""
        self.ui_handler.add_polygon_from_points(points)
    
    # Table Handler
    def on_table_item_changed(self, item):
        """เมื่อแก้ไขข้อมูลในตาราง (deprecated - handler จัดการเอง)"""
        pass
    
    def on_table_selection_changed(self):
        """เมื่อเลือกแถวในตาราง (deprecated - handler จัดการเอง)"""
        pass
    
    # Export Handler
    def save_labels(self, *args):
        """Export Detection Dataset"""
        self.export_handler.save_labels_detection()
    
    def export_rec(self, *args):
        """Export Recognition Dataset"""
        self.export_handler.export_recognition()
    
    # Rotation Handler
    def rotate_image(self, angle):
        """หมุนรูปปัจจุบัน"""
        if hasattr(self, 'rotation_handler'):
            self.rotation_handler.rotate_current_image(angle)
    
    def reset_rotation(self):
        """รีเซ็ตการหมุนรูปปัจจุบัน"""
        if hasattr(self, 'rotation_handler'):
            self.rotation_handler.reset_rotation()
    
    # ===== 🔒 Mask Handler Methods (NEW!) =====
    
    def toggle_mask_mode(self, checked):
        """เปิด/ปิดโหมด Masking"""
        self.mask_mode = checked
        
        # ปิด draw_mode ถ้าเปิด mask_mode
        if checked and self.draw_mode:
            self.draw_mode = False
            if hasattr(self, 'draw_action'):
                self.draw_action.setChecked(False)
        
        # แสดง/ซ่อนปุ่มเลือกสี
        if hasattr(self, 'mask_color_btn'):
            self.mask_color_btn.setVisible(checked)
            # อัปเดตปุ่มแสดงสีปัจจุบัน
            if checked:
                self.mask_handler._update_color_button()
        
        # อัปเดต mode combo
        if hasattr(self, 'mode_combo'):
            if checked:
                self.mode_combo.setCurrentText("Masking")
            else:
                self.mode_combo.setCurrentText("Annotation")
        
        logger.info(f"Mask mode: {'ON' if checked else 'OFF'}")
    
    def on_mode_changed(self, mode_text):
        """เมื่อเปลี่ยน mode จาก combo box"""
        if mode_text == "Masking":
            # เปิด mask mode
            if hasattr(self, 'mask_action'):
                self.mask_action.setChecked(True)
            self.mask_mode = True
            self.draw_mode = False
            if hasattr(self, 'draw_action'):
                self.draw_action.setChecked(False)
            # แสดงปุ่มเลือกสี
            if hasattr(self, 'mask_color_btn'):
                self.mask_color_btn.setVisible(True)
                self.mask_handler._update_color_button()
        else:  # Annotation
            # ปิด mask mode
            if hasattr(self, 'mask_action'):
                self.mask_action.setChecked(False)
            self.mask_mode = False
            # ซ่อนปุ่มเลือกสี
            if hasattr(self, 'mask_color_btn'):
                self.mask_color_btn.setVisible(False)
    
    def add_mask_from_rect(self, rect):
        """เพิ่ม Quad Mask จาก rectangle"""
        self.mask_handler.add_mask_from_rect(rect)
    
    def add_mask_from_points(self, points):
        """เพิ่ม Polygon Mask จาก points"""
        self.mask_handler.add_mask_from_points(points)
    
    def choose_mask_color(self):
        """เปิด color picker เพื่อเลือกสี mask"""
        self.mask_handler.choose_mask_color()
    
    def change_selected_mask_color(self):
        """เปลี่ยนสีของ mask ที่เลือกอยู่"""
        self.mask_handler.change_selected_mask_color()
    
    def set_mask_color_preset(self, preset_name):
        """ตั้งค่าสีจาก preset"""
        self.mask_handler.set_mask_color_preset(preset_name)
    
    # ===== Event Handlers =====
    
    def closeEvent(self, event):
        """เมื่อปิดโปรแกรม"""
        QtWidgets.QApplication.processEvents()
        
        # บันทึก workspace
        if self.workspace_handler.current_workspace_id:
            self.workspace_handler.save_workspace()
        
        super().closeEvent(event)
        logger.info("Application closed")