# modules/gui/window_handler/rotation_handler.py

import logging
import cv2
import numpy as np
from typing import List, Tuple
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QRectF
from modules.utils import imread_unicode

logger = logging.getLogger("TextDetGUI")


class RotationHandler:
    """
    จัดการการหมุนรูปภาพและ annotations
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference ไปยัง MainWindow instance
        """
        self.main_window = main_window
    
    def rotate_current_image(self, angle):
        """
        หมุนรูปปัจจุบันและ annotations
        
        Args:
            angle: มุมที่ต้องการหมุน (90, -90, 180)
        """
        if not self.main_window.img_key or not self.main_window.img_path:
            QtWidgets.QMessageBox.warning(
                self.main_window, "Warning", "กรุณาเลือกรูปก่อน"
            )
            return
        
        key = self.main_window.img_key
        
        # บันทึก annotation ปัจจุบันก่อน
        self.main_window.annotation_handler.save_current_annotation()
        
        # ดึงข้อมูลการหมุนปัจจุบัน
        if not hasattr(self.main_window, 'image_rotations'):
            self.main_window.image_rotations = {}
        
        current_rotation = self.main_window.image_rotations.get(key, 0)
        new_rotation = (current_rotation + angle) % 360
        
        # บันทึกค่าการหมุนใหม่
        self.main_window.image_rotations[key] = new_rotation
        
        # หมุน annotations
        self._rotate_annotations(key, angle)
        
        # โหลดรูปใหม่
        self.main_window.image_handler.load_image(key, self.main_window.img_path)
        
        # โหลด annotations ที่หมุนแล้ว
        self.main_window.annotation_handler.load_annotation(key)
        
        # บันทึก workspace
        self.main_window.workspace_handler.save_workspace()
        
        logger.info(f"Rotated image {key} by {angle}° (total: {new_rotation}°)")
    
    def _rotate_annotations(self, key, angle):
        """
        หมุน annotations ตามมุมที่กำหนด
        
        Args:
            key: image key
            angle: มุมที่หมุน (90, -90, 180)
        """
        annotations = self.main_window.annotations.get(key, [])
        if not annotations:
            return
        
        # อ่านรูปเพื่อหาขนาด
        img_path = None
        for k, path in self.main_window.image_items:
            if k == key:
                img_path = path
                break
        
        if not img_path:
            return
        
        img = imread_unicode(img_path)
        if img is None:
            return
        
        h, w = img.shape[:2]
        
        # หมุน points ตามมุม
        rotated_annotations = []
        for ann in annotations:
            points = ann.get('points', [])
            rotated_points = self._rotate_points(points, angle, w, h)
            
            new_ann = ann.copy()
            new_ann['points'] = rotated_points
            rotated_annotations.append(new_ann)
        
        self.main_window.annotations[key] = rotated_annotations
    
    def _rotate_points(self, points, angle, w, h):
        """
        หมุน points ตามมุมที่กำหนด
        
        Args:
            points: list of [x, y]
            angle: มุมที่หมุน (90, -90, 180)
            w: ความกว้างรูปเดิม
            h: ความสูงรูปเดิม
        
        Returns:
            list of rotated [x, y]
        """
        rotated = []
        
        for pt in points:
            x, y = pt[0], pt[1]
            
            if angle == 90:  # หมุนขวา 90°
                new_x = h - y
                new_y = x
            elif angle == -90:  # หมุนซ้าย 90°
                new_x = y
                new_y = w - x
            elif angle == 180:  # หมุน 180°
                new_x = w - x
                new_y = h - y
            else:
                new_x, new_y = x, y
            
            rotated.append([new_x, new_y])
        
        return rotated
    
    def get_rotated_image(self, img_path, key):
        """
        โหลดรูปและหมุนตามค่าที่บันทึกไว้
        
        Args:
            img_path: path ของรูป
            key: image key
        
        Returns:
            numpy array ของรูปที่หมุนแล้ว (หรือ None ถ้าไม่สำเร็จ)
        """
        img = imread_unicode(img_path)
        if img is None:
            return None
        
        # ตรวจสอบว่ามีการหมุนหรือไม่
        if not hasattr(self.main_window, 'image_rotations'):
            return img
        
        rotation = self.main_window.image_rotations.get(key, 0)
        if rotation == 0:
            return img
        
        # หมุนรูป
        return self.rotate_image_cv2(img, rotation)
    
    @staticmethod
    def rotate_image_cv2(img, angle):
        """
        หมุนรูปด้วย OpenCV
        
        Args:
            img: numpy array
            angle: มุมที่หมุน (90, 180, 270)
        
        Returns:
            numpy array ของรูปที่หมุนแล้ว
        """
        if angle == 0:
            return img
        elif angle == 90:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(img, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            # สำหรับมุมอื่นๆ ใช้ warpAffine
            h, w = img.shape[:2]
            center = (w / 2, h / 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            cos = np.abs(M[0, 0])
            sin = np.abs(M[0, 1])
            new_w = int((h * sin) + (w * cos))
            new_h = int((h * cos) + (w * sin))
            M[0, 2] += (new_w / 2) - center[0]
            M[1, 2] += (new_h / 2) - center[1]
            return cv2.warpAffine(img, M, (new_w, new_h), borderMode=cv2.BORDER_REPLICATE)
    
    def reset_rotation(self):
        """รีเซ็ตการหมุนของรูปปัจจุบัน"""
        if not self.main_window.img_key:
            return
        
        key = self.main_window.img_key
        
        if not hasattr(self.main_window, 'image_rotations'):
            return
        
        if key in self.main_window.image_rotations:
            del self.main_window.image_rotations[key]
            
            # โหลดรูปใหม่
            self.main_window.image_handler.load_image(key, self.main_window.img_path)
            self.main_window.annotation_handler.load_annotation(key)
            self.main_window.workspace_handler.save_workspace()
            
            logger.info(f"Reset rotation for {key}")