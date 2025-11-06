# modules/gui/window_handler/detection_handler.py

import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from modules.utils import handle_exceptions, sanitize_annotations

logger = logging.getLogger("TextDetGUI")


def is_valid_box(pts):
    """ตรวจสอบว่า points ถูกต้องหรือไม่"""
    if not (isinstance(pts, list) and len(pts) >= 4):
        return False
    for p in pts:
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            return False
    return True


class DetectionHandler:
    """
    จัดการ Auto Detection ด้วย PaddleOCR
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference ไปยัง MainWindow instance
        """
        self.main_window = main_window
    
    @handle_exceptions
    def auto_label_current(self):
        """รัน auto detection สำหรับรูปปัจจุบัน"""
        if not self.main_window.img_path:
            QtWidgets.QMessageBox.warning(
                self.main_window, "Warning", "เลือกรูปก่อน"
            )
            return
        
        # ล้าง annotations เดิม
        self.main_window.annotation_handler.clear_boxes()
        
        # แสดง cursor รอ
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            # รัน detection
            items = self.main_window.detector.detect(self.main_window.img_path)
            
            # แสดงผลลัพธ์
            self.main_window.annotation_handler.apply_detections(items)
            
            # บันทึก
            self.main_window.annotations[self.main_window.img_key] = sanitize_annotations(
                [b.to_dict() for b in self.main_window.box_items]
            )
            self.main_window.annotation_handler.update_list_icon(self.main_window.img_key)
            self.main_window.workspace_handler.save_workspace()
            
            # อัปเดตตารางถ้าอยู่ใน recog mode
            if self.main_window.recog_mode:
                self.main_window.table_handler.populate_table()
            
            logger.info(f"Auto-labeled current image: {len(items)} regions detected")
        
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
    
    @handle_exceptions
    def auto_label_all(self):
        """รัน auto detection สำหรับรูปทั้งหมด"""
        if not self.main_window.image_items:
            QtWidgets.QMessageBox.warning(
                self.main_window, "Warning", "Open Folder ก่อน"
            )
            return
        
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            success_count = 0
            fail_count = 0
            
            for key, full in self.main_window.image_items:
                try:
                    # รัน detection
                    items = self.main_window.detector.detect(full)
                    
                    # Sanitize และเพิ่ม shape เป็น Polygon (เพื่อรักษาความสอดคล้องกับ auto_label_current)
                    valid_items = []
                    for it in items:
                        if is_valid_box(it['points']):
                            # เพิ่ม 'shape': 'Polygon' เพื่อให้ตรงกับ apply_detections()
                            it['shape'] = 'Polygon'
                            valid_items.append(it)
                    
                    self.main_window.annotations[key] = sanitize_annotations(valid_items)
                    self.main_window.annotation_handler.update_list_icon(key)
                    
                    success_count += 1
                    logger.debug(f"Auto-labeled {key}: {len(valid_items)} regions")
                
                except Exception as e:
                    logger.error(f"Auto-label failed on {key}: {e}")
                    fail_count += 1
            
            # บันทึก workspace
            self.main_window.workspace_handler.save_workspace()
            
            logger.info(f"Auto-label all completed: {success_count} success, {fail_count} failed")
            
            QtWidgets.QMessageBox.information(
                self.main_window, 
                "Done", 
                f"Auto-label all finished\n\nSuccess: {success_count}\nFailed: {fail_count}"
            )
        
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
    
    @handle_exceptions
    def auto_label_selected(self):
        """รัน auto detection สำหรับรูปที่ check (checkbox) ไว้เท่านั้น"""
        # ดึงรายการรูปที่ถูก check ไว้
        checked_keys = []
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                checked_keys.append(item.text())
        
        if not checked_keys:
            QtWidgets.QMessageBox.warning(
                self.main_window, 
                "Warning", 
                "กรุณา Check (☑) รูปที่ต้องการทำ Auto Detection\n\n"
                "หมายเหตุ: คลิก checkbox หน้ารูปเพื่อเลือก"
            )
            return
        
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            success_count = 0
            fail_count = 0
            
            # วนลูปเฉพาะรูปที่ check ไว้
            for key, full in self.main_window.image_items:
                if key not in checked_keys:
                    continue  # ข้ามรูปที่ไม่ได้ check
                
                try:
                    # รัน detection
                    items = self.main_window.detector.detect(full)
                    
                    # Sanitize และเพิ่ม shape เป็น Polygon (เพื่อรักษาความสอดคล้องกับ auto_label_current)
                    valid_items = []
                    for it in items:
                        if is_valid_box(it['points']):
                            # เพิ่ม 'shape': 'Polygon' เพื่อให้ตรงกับ apply_detections()
                            it['shape'] = 'Polygon'
                            valid_items.append(it)
                    
                    self.main_window.annotations[key] = sanitize_annotations(valid_items)
                    self.main_window.annotation_handler.update_list_icon(key)
                    
                    success_count += 1
                    logger.debug(f"Auto-labeled {key}: {len(valid_items)} regions")
                
                except Exception as e:
                    logger.error(f"Auto-label failed on {key}: {e}")
                    fail_count += 1
            
            # บันทึก workspace
            self.main_window.workspace_handler.save_workspace()
            
            logger.info(f"Auto-label selected completed: {success_count} success, {fail_count} failed")
            
            QtWidgets.QMessageBox.information(
                self.main_window, 
                "Done", 
                f"Auto-label selected finished\n\n"
                f"Checked: {len(checked_keys)} images\n"
                f"Success: {success_count}\n"
                f"Failed: {fail_count}"
            )
        
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()