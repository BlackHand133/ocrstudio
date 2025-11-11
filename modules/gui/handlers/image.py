# modules/gui/window_handler/image_handler.py

import os
import logging
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QRectF
from modules.utils import sanitize_filename

logger = logging.getLogger("TextDetGUI")


class ImageHandler:
    """
    จัดการเรื่องรูปภาพ: โหลด, เลือก, แสดงผล (พร้อมการแสดงสถานะที่ชัดเจน)
    """
    
    # สีสำหรับสถานะต่างๆ
    COLOR_NORMAL = QtGui.QColor(255, 255, 255)           # สีขาว - ปกติ
    COLOR_ANNOTATED = QtGui.QColor(200, 255, 200)        # เขียวอ่อน - มี annotation
    COLOR_CHECKED = QtGui.QColor(200, 230, 255)          # ฟ้าอ่อน - ถูกเลือก
    COLOR_BOTH = QtGui.QColor(180, 255, 200)             # เขียว-ฟ้า - มี annotation + ถูกเลือก
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference ไปยัง MainWindow instance
        """
        self.main_window = main_window
    
    def open_folder(self):
        """เปิดโฟลเดอร์และสแกนรูปภาพแบบ recursive"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, "Select Image Folder", ""
        )
        if not folder:
            return
        
        # นามสกุลรูปที่รองรับ
        exts = {'.jpg', '.jpeg', '.png', '.bmp'}
        
        self.main_window.image_items.clear()
        self.main_window.list_widget.clear()
        
        idx = 1
        for root_dir, _, files in os.walk(folder):
            for fn in sorted(files):
                if os.path.splitext(fn.lower())[1] in exts:
                    # Sanitize filename เพื่อลบ space และ special characters
                    clean_fn = sanitize_filename(fn)
                    key = f"{idx:04d}_{clean_fn}"
                    full = os.path.join(root_dir, fn)
                    self.main_window.image_items.append((key, full))
                    
                    item = QtWidgets.QListWidgetItem(key)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked)
                    
                    # แสดงสถานะด้วยสีและไอคอน
                    self.update_item_appearance(item, key)
                    
                    self.main_window.list_widget.addItem(item)
                    idx += 1
        
        logger.info(f"Loaded {len(self.main_window.image_items)} images from {folder}")
    
    def update_item_appearance(self, item, key):
        """
        อัปเดตรูปลักษณ์ของ item ตามสถานะ
        
        Args:
            item: QListWidgetItem
            key: image key
        """
        has_annotation = bool(self.main_window.annotations.get(key))
        is_checked = item.checkState() == Qt.Checked
        
        # ตั้งค่าไอคอน
        if has_annotation:
            item.setIcon(self.main_window.icon_marked)
        else:
            item.setIcon(QtGui.QIcon())
        
        # ตั้งค่าสีพื้นหลัง
        if has_annotation and is_checked:
            # มี annotation + ถูกเลือก
            item.setBackground(self.COLOR_BOTH)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        elif has_annotation:
            # มี annotation อย่างเดียว
            item.setBackground(self.COLOR_ANNOTATED)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
        elif is_checked:
            # ถูกเลือกอย่างเดียว
            item.setBackground(self.COLOR_CHECKED)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
        else:
            # ปกติ
            item.setBackground(self.COLOR_NORMAL)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
    
    def refresh_all_items_appearance(self):
        """รีเฟรชรูปลักษณ์ของทุก items"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            key = item.text()
            self.update_item_appearance(item, key)
    
    def on_image_selected(self, item):
        """เมื่อผู้ใช้เลือกรูปจาก list"""
        QtWidgets.QApplication.processEvents()
        
        # บันทึก annotation รูปปัจจุบันก่อน
        self.main_window.annotation_handler.save_current_annotation()
        
        key = item.text()
        
        # หา path ของรูป
        for k, full in self.main_window.image_items:
            if k == key:
                self.load_image(k, full)
                break
        
        # โหลด annotation
        self.main_window.annotation_handler.load_annotation(key)
        
        # อัปเดตตารางถ้าอยู่ใน recog mode
        if self.main_window.recog_mode:
            self.main_window.table_handler.populate_table()
        
        # อัปเดตรูปลักษณ์ทุก items (กรณี checkbox ถูกคลิก)
        self.refresh_all_items_appearance()
    
    def load_image(self, key, full_path):
        """โหลดและแสดงรูปบน canvas (รองรับการหมุน)"""
        self.main_window.img_key = key
        self.main_window.img_path = full_path
        
        # ล้าง scene
        self.main_window.scene.clear()
        self.main_window.box_items.clear()
        
        # ตรวจสอบว่ามีการหมุนหรือไม่
        if hasattr(self.main_window, 'rotation_handler'):
            from modules.utils import imread_unicode
            import cv2
            
            img = self.main_window.rotation_handler.get_rotated_image(full_path, key)
            
            if img is not None:
                # แปลง numpy array เป็น QPixmap
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                h, w, c = img_rgb.shape
                bytes_per_line = c * w
                q_img = QtGui.QImage(img_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
                pix = QtGui.QPixmap.fromImage(q_img)
            else:
                pix = QtGui.QPixmap(full_path)
        else:
            # ถ้ายังไม่มี rotation_handler ให้โหลดปกติ
            pix = QtGui.QPixmap(full_path)
        
        self.main_window.scene.addPixmap(pix).setZValue(0)
        self.main_window.scene.setSceneRect(QRectF(pix.rect()))
        self.main_window.view.fitInView(
            self.main_window.scene.sceneRect(), 
            Qt.KeepAspectRatio
        )
        
        logger.debug(f"Loaded image: {key}")
    
    def is_item_checked(self, key):
        """ตรวจสอบว่ารูปถูกเช็คไว้หรือไม่"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            if item.text() == key:
                return item.checkState() == Qt.Checked
        return False
    
    def check_only_annotated(self):
        """เช็คเฉพาะรูปที่มี annotation"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            key = item.text()
            has_annotation = bool(self.main_window.annotations.get(key))
            item.setCheckState(Qt.Checked if has_annotation else Qt.Unchecked)
            self.update_item_appearance(item, key)
        
        logger.info("Checked only annotated images")
    
    def uncheck_unannotated(self):
        """ยกเลิกการเช็ครูปที่ไม่มี annotation"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            key = item.text()
            if not self.main_window.annotations.get(key):
                item.setCheckState(Qt.Unchecked)
                self.update_item_appearance(item, key)
        
        logger.info("Unchecked unannotated images")
    
    def select_all_images(self):
        """เลือกทุกรูป (Check All)"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            item.setCheckState(Qt.Checked)
            key = item.text()
            self.update_item_appearance(item, key)
        
        logger.info("Selected all images")
    
    def deselect_all_images(self):
        """ยกเลิกการเลือกทุกรูป (Uncheck All)"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
            key = item.text()
            self.update_item_appearance(item, key)
        
        logger.info("Deselected all images")