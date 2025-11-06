# modules/gui/window_handler/ui_handler.py

import logging
from PyQt5 import QtWidgets

logger = logging.getLogger("TextDetGUI")


class UIHandler:
    """
    จัดการ UI interactions: draw mode, annotation type, etc.
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference ไปยัง MainWindow instance
        """
        self.main_window = main_window
    
    def toggle_draw_mode(self, checked):
        """
        เปิด/ปิดโหมดวาดกล่อง
        
        Args:
            checked: True = เปิด, False = ปิด
        """
        self.main_window.draw_mode = checked
        
        # เปลี่ยน drag mode
        if checked:
            mode = QtWidgets.QGraphicsView.NoDrag
        else:
            mode = QtWidgets.QGraphicsView.RubberBandDrag
        
        self.main_window.view.setDragMode(mode)
        
        if checked:
            self.update_annotation_info()
        
        logger.debug(f"Draw mode: {checked}")
    
    def toggle_recog_mode(self, checked):
        """
        เปิด/ปิดโหมด Recognition (แสดงตาราง)
        
        Args:
            checked: True = เปิด, False = ปิด
        """
        self.main_window.recog_mode = checked
        self.main_window.table.setVisible(checked)
        
        if checked:
            self.main_window.table_handler.populate_table()
        else:
            self.main_window.table.clearContents()
            self.main_window.table.setRowCount(0)
        
        logger.debug(f"Recognition mode: {checked}")
    
    def on_annotation_type_changed(self, new_type):
        """
        เปลี่ยนประเภท annotation
        
        Args:
            new_type: 'Quad' หรือ 'Polygon'
        """
        self.main_window.annotation_type = new_type
        self.update_annotation_info()
        
        # ปิด draw mode เมื่อเปลี่ยนประเภท
        if hasattr(self.main_window, 'draw_action'):
            self.main_window.draw_action.setChecked(False)
            self.main_window.draw_mode = False
        
        logger.debug(f"Annotation type changed to: {new_type}")
    
    def update_annotation_info(self):
        """อัปเดตข้อมูลคำแนะนำการใช้งาน"""
        if not hasattr(self.main_window, 'annotation_info_label'):
            return
        
        if self.main_window.annotation_type == 'Quad':
            info = "(Drag to draw rectangle)"
        else:
            info = "(Click 4+ points, Right-click/Enter to finish, Esc to cancel)"
        
        self.main_window.annotation_info_label.setText(info)
    
    def add_box_from_rect(self, rect):
        """
        เพิ่มกล่อง Quad จาก rectangle
        
        Args:
            rect: QRectF object
        """
        pts = [
            [rect.x(), rect.y()],
            [rect.x() + rect.width(), rect.y()],
            [rect.x() + rect.width(), rect.y() + rect.height()],
            [rect.x(), rect.y() + rect.height()],
        ]
        
        self.main_window.annotation_handler.add_box_item(pts, "", 'Quad')
        
        # อัปเดตตารางถ้าอยู่ใน recog mode
        if self.main_window.recog_mode:
            self.main_window.table_handler.populate_table()
        
        logger.debug("Added box from rectangle")
    
    def add_polygon_from_points(self, points):
        """
        เพิ่ม polygon จาก points
        
        Args:
            points: list of points [[x1,y1], [x2,y2], ...]
        """
        self.main_window.annotation_handler.add_box_item(points, "", 'Polygon')
        
        # อัปเดตตารางถ้าอยู่ใน recog mode
        if self.main_window.recog_mode:
            self.main_window.table_handler.populate_table()
        
        logger.debug(f"Added polygon with {len(points)} points")