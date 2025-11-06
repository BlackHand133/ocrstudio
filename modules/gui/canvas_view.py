# modules/gui/canvas_view.py

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QRectF, QPoint, QPointF, Qt

class CanvasView(QtWidgets.QGraphicsView):
    """รองรับการวาด Quad/Polygon สำหรับ Annotation และ Masking + ซูม Ctrl+Scroll"""
    
    def __init__(self, parent=None):
        super().__init__(parent.scene)
        self.parent = parent
        
        # สำหรับ Quad mode (ลากวาดสี่เหลี่ยม)
        self.rubberBand = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self.origin = QPoint()
        self.drawing_quad = False
        
        # สำหรับ Polygon mode (คลิกหลายจุด)
        self.polygon_points = []  # เก็บจุดที่คลิก
        self.temp_line = None     # เส้นชั่วคราวจากจุดล่าสุดไปเมาส์
        self.polygon_preview = None  # แสดง polygon preview
        
        self._zoom = 1.0
    
    def mousePressEvent(self, event):
        # ตรวจสอบว่าอยู่ในโหมดวาดหรือไม่
        draw_mode = getattr(self.parent, 'draw_mode', False)
        mask_mode = getattr(self.parent, 'mask_mode', False)
        
        if not (draw_mode or mask_mode):
            super().mousePressEvent(event)
            return
        
        annotation_type = getattr(self.parent, 'annotation_type', 'Quad')
        
        if annotation_type == 'Quad':
            # โหมด Quad: ลากวาดสี่เหลี่ยม
            if event.button() == Qt.LeftButton:
                self.origin = event.pos()
                self.rubberBand.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
                self.rubberBand.show()
                self.drawing_quad = True
            else:
                super().mousePressEvent(event)
        
        elif annotation_type == 'Polygon':
            # โหมด Polygon: คลิกเพื่อเพิ่มจุด
            if event.button() == Qt.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                self.polygon_points.append(scene_pos)
                self._update_polygon_preview()
            
            elif event.button() == Qt.RightButton:
                # คลิกขวา = ปิด polygon (ต้องมีอย่างน้อย 4 จุด)
                if len(self.polygon_points) >= 4:
                    self._finish_polygon()
                else:
                    self._cancel_polygon()
    
    def mouseMoveEvent(self, event):
        if self.drawing_quad:
            # อัปเดต rubber band
            rect = QtCore.QRect(self.origin, event.pos()).normalized()
            self.rubberBand.setGeometry(rect)
        
        elif self.polygon_points:
            # อัปเดตเส้นชั่วคราว
            self._update_polygon_preview(self.mapToScene(event.pos()))
        
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.drawing_quad and event.button() == Qt.LeftButton:
            self.rubberBand.hide()
            self.drawing_quad = False
            
            rect_vp = QtCore.QRect(self.origin, event.pos()).normalized()
            
            # ตรวจสอบขนาดขั้นต่ำ
            if rect_vp.width() < 5 or rect_vp.height() < 5:
                return
            
            tl = self.mapToScene(rect_vp.topLeft())
            br = self.mapToScene(rect_vp.bottomRight())
            scene_rect = QRectF(tl, br)
            
            # ตรวจสอบว่าเป็น mask mode หรือ annotation mode
            if getattr(self.parent, 'mask_mode', False):
                self.parent.add_mask_from_rect(scene_rect)
            else:
                self.parent.add_box_from_rect(scene_rect)
        
        else:
            super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """กด Enter หรือ Escape เพื่อปิด/ยกเลิก polygon"""
        if self.polygon_points:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if len(self.polygon_points) >= 4:
                    self._finish_polygon()
            elif event.key() == Qt.Key_Escape:
                self._cancel_polygon()
        else:
            super().keyPressEvent(event)
    
    def wheelEvent(self, event):
        """Ctrl+Scroll เพื่อซูม"""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.25 if delta > 0 else 0.8
            self._zoom *= factor
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)
    
    def _update_polygon_preview(self, mouse_pos=None):
        """อัปเดตการแสดงผล polygon preview"""
        # ลบ preview เก่า
        if self.temp_line:
            self.scene().removeItem(self.temp_line)
            self.temp_line = None
        if self.polygon_preview:
            self.scene().removeItem(self.polygon_preview)
            self.polygon_preview = None
        
        if not self.polygon_points:
            return
        
        # วาดจุดที่คลิกแล้ว
        pen = QtGui.QPen(Qt.blue, 2)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 255, 30))
        
        if len(self.polygon_points) >= 2:
            poly = QtGui.QPolygonF(self.polygon_points)
            self.polygon_preview = self.scene().addPolygon(poly, pen, brush)
            self.polygon_preview.setZValue(10)
        
        # วาดเส้นชั่วคราวไปตำแหน่งเมาส์
        if mouse_pos and self.polygon_points:
            pen_temp = QtGui.QPen(Qt.gray, 1, Qt.DashLine)
            self.temp_line = self.scene().addLine(
                self.polygon_points[-1].x(), self.polygon_points[-1].y(),
                mouse_pos.x(), mouse_pos.y(),
                pen_temp
            )
            self.temp_line.setZValue(10)
    
    def _finish_polygon(self):
        """ยืนยันสร้าง polygon (ต้องมีอย่างน้อย 4 จุด)"""
        if len(self.polygon_points) >= 4:
            # แปลงเป็น list of [x, y]
            points = [[p.x(), p.y()] for p in self.polygon_points]
            
            # ตรวจสอบว่าเป็น mask mode หรือ annotation mode
            if getattr(self.parent, 'mask_mode', False):
                self.parent.add_mask_from_points(points)
            else:
                self.parent.add_polygon_from_points(points)
        
        self._cancel_polygon()
    
    def _cancel_polygon(self):
        """ยกเลิกการวาด polygon"""
        self.polygon_points.clear()
        if self.temp_line:
            self.scene().removeItem(self.temp_line)
            self.temp_line = None
        if self.polygon_preview:
            self.scene().removeItem(self.polygon_preview)
            self.polygon_preview = None