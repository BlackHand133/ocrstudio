# modules/gui/polygon_item.py

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QPointF, QRectF
from typing import List, Union
from modules.gui.items.base_annotation_item import BaseAnnotationItem

class PolygonItem(BaseAnnotationItem, QtWidgets.QGraphicsPolygonItem):
    """
    Polygon annotation (4+ จุด) - รูปหลายเหลี่ยมที่ปรับจุดยอดได้
    รองรับการลากจุดยอดแต่ละจุด และมี text label
    with automatic boundary protection
    """
    
    def __init__(self, pts: List[Union[List[float], tuple]], text: str) -> None:
        # สร้าง QPolygonF จากจุด
        poly = QtGui.QPolygonF([QPointF(float(p[0]), float(p[1])) for p in pts])
        
        # Initialize both parent classes
        BaseAnnotationItem.__init__(self)
        QtWidgets.QGraphicsPolygonItem.__init__(self, poly)
        
        # Set visual style (เหมือน BoxItem)
        self.setPen(QtGui.QPen(Qt.red, 2))
        self.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0, 50)))
        
        # Enable interactions
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        # Create text label
        self.create_text_item(text, self)
        
        # Vertex handles
        self._active_vertex = None
        
        # Image bounds (will be set by scene)
        self.image_bounds = None
        
        # Initial layout
        self.update_text_position()
    
    def set_image_bounds(self, width: int, height: int):
        """Set image boundaries for clipping"""
        self.image_bounds = QRectF(0, 0, width, height)
    
    def update_text_position(self) -> None:
        """วาง label ไว้เหนือจุดแรก"""
        if self.text_item and not self.polygon().isEmpty():
            first_pt = self.polygon().at(0)
            tr = self.text_item.boundingRect()
            self.text_item.setPos(first_pt.x(), first_pt.y() - tr.height() - 5)
    
    def boundingRect(self) -> QRectF:
        """ขยาย bounds เพื่อให้วาด handles ได้"""
        o = self.handle_size
        return super().boundingRect().adjusted(-o, -o, o, o)
    
    def paint(self, painter: QtGui.QPainter, option, widget) -> None:
        super().paint(painter, option, widget)
        
        # วาด vertex handles ถ้าถูกเลือก (เหมือนกับ BoxItem วาด handles)
        if self.isSelected():
            painter.setPen(QtGui.QPen(Qt.blue, 1))
            painter.setBrush(QtGui.QBrush(Qt.white))
            for i in range(self.polygon().size()):
                pt = self.polygon().at(i)
                r = self.handle_size / 2
                painter.drawEllipse(pt, r, r)
    
    def _get_vertex_at(self, pos: QPointF) -> int:
        """หาว่าตำแหน่ง pos อยู่ใกล้จุดไหน (return index หรือ -1)"""
        threshold = self.handle_size
        for i in range(self.polygon().size()):
            pt = self.polygon().at(i)
            if (pt - pos).manhattanLength() < threshold:
                return i
        return -1
    
    def hoverMoveEvent(self, event) -> None:
        if self._get_vertex_at(event.pos()) >= 0:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)
    
    def mousePressEvent(self, event) -> None:
        self._active_vertex = self._get_vertex_at(event.pos())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        if self._active_vertex is not None and self._active_vertex >= 0:
            # ลากจุดยอดพร้อม clipping
            new_pos = event.pos()
            
            # Clip to image bounds if available
            if self.image_bounds:
                scene_pos = self.mapToScene(new_pos)
                clipped_x = max(0, min(scene_pos.x(), self.image_bounds.width()))
                clipped_y = max(0, min(scene_pos.y(), self.image_bounds.height()))
                new_pos = self.mapFromScene(QPointF(clipped_x, clipped_y))
            
            new_poly = QtGui.QPolygonF(self.polygon())
            new_poly.replace(self._active_vertex, new_pos)
            self.setPolygon(new_poly)
            self.update_text_position()
        else:
            # ลากทั้ง polygon
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        self._active_vertex = None
        # Ensure vertices are within bounds after release
        self._clip_polygon_to_bounds()
        super().mouseReleaseEvent(event)
    
    def itemChange(self, change, value):
        """Override to prevent moving outside image bounds"""
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and self.image_bounds:
            new_pos = value
            poly = self.polygon()
            
            if not poly.isEmpty():
                bounds = poly.boundingRect()
                
                # Calculate limits
                min_x = -bounds.x()
                min_y = -bounds.y()
                max_x = self.image_bounds.width() - (bounds.x() + bounds.width())
                max_y = self.image_bounds.height() - (bounds.y() + bounds.height())
                
                # Clip position
                new_x = max(min_x, min(new_pos.x(), max_x))
                new_y = max(min_y, min(new_pos.y(), max_y))
                
                return QPointF(new_x, new_y)
        
        return super().itemChange(change, value)
    
    def _clip_polygon_to_bounds(self):
        """Clip polygon vertices to image bounds"""
        if not self.image_bounds:
            return
        
        new_poly = QtGui.QPolygonF()
        for i in range(self.polygon().size()):
            pt = self.polygon().at(i)
            scene_pt = self.mapToScene(pt)
            
            # Clip coordinates
            clipped_x = max(0, min(scene_pt.x(), self.image_bounds.width()))
            clipped_y = max(0, min(scene_pt.y(), self.image_bounds.height()))
            
            # Convert back to item coordinates
            item_pt = self.mapFromScene(QPointF(clipped_x, clipped_y))
            new_poly.append(item_pt)
        
        if not new_poly.isEmpty():
            self.setPolygon(new_poly)
            self.update_text_position()
    
    def get_center(self) -> QPointF:
        """Return center point in scene coordinates"""
        poly = self.polygon()
        if poly.isEmpty():
            return self.pos()
        
        # หาจุดกลางจาก bounding rect
        local_rect = poly.boundingRect()
        local_center = local_rect.center()
        return self.mapToScene(local_center)
    
    def to_dict(self) -> dict:
        """Export เป็น dict (scene coordinates) with clipped coordinates"""
        points = []
        poly_scene = self.mapToScene(self.polygon())
        for i in range(poly_scene.size()):
            pt = poly_scene.at(i)
            x, y = pt.x(), pt.y()
            
            # Clip to image bounds if available
            if self.image_bounds:
                x = max(0, min(x, self.image_bounds.width()))
                y = max(0, min(y, self.image_bounds.height()))
            
            points.append([x, y])
        
        return {
            'points': points,
            'transcription': self.get_transcription(),
            'difficult': False,
            'shape': 'Polygon'  # บันทึกประเภทเพื่อไม่ให้สับสนกับ Quad
        }