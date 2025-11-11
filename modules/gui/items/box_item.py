# modules/gui/box_item.py

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QRectF, QPointF
from typing import List, Union
from modules.gui.items.base_annotation_item import BaseAnnotationItem

class BoxItem(BaseAnnotationItem, QtWidgets.QGraphicsRectItem):
    """
    Quad annotation (4 จุด) - กล่องสี่เหลี่ยมที่ปรับขนาดได้
    รองรับ resize handles 8 จุด และมี text label
    with automatic boundary protection
    """

    handle_cursors = {
        'tl': Qt.SizeFDiagCursor, 'tr': Qt.SizeBDiagCursor,
        'bl': Qt.SizeBDiagCursor, 'br': Qt.SizeFDiagCursor,
        'l': Qt.SizeHorCursor,    'r': Qt.SizeHorCursor,
        't': Qt.SizeVerCursor,    'b': Qt.SizeVerCursor,
    }

    def __init__(self, pts: List[Union[List[float], tuple]], text: str) -> None:
        # Compute bounds in scene coords
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        w, h = x2 - x1, y2 - y1

        # Initialize both parent classes
        BaseAnnotationItem.__init__(self)
        QtWidgets.QGraphicsRectItem.__init__(self, 0, 0, w, h)
        
        self.setPos(x1, y1)  # place item in scene

        # Enable moving/resizing
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        # Set visual style
        self.setPen(QtGui.QPen(Qt.red, 2))
        self.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0, 50)))

        # Create text label
        self.create_text_item(text, self)

        # Tracks which handle is active
        self.handles = {}
        self._active_handle = None
        
        # Image bounds (will be set by scene)
        self.image_bounds = None

        # Initial layout
        self._update_handles_pos()
        self.update_text_position()
    
    def set_image_bounds(self, width: int, height: int):
        """Set image boundaries for clipping"""
        self.image_bounds = QRectF(0, 0, width, height)

    def update_text_position(self) -> None:
        """Place label just above the top-left of the rect."""
        if self.text_item:
            tr = self.text_item.boundingRect()
            self.text_item.setPos(0, -tr.height() - 2)

    def _update_handles_pos(self) -> None:
        """Compute the positions of the eight resize handles."""
        r = self.rect()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        s = self.handle_size
        self.handles = {
            'tl': QRectF(x - s/2,   y - s/2,   s, s),
            'tr': QRectF(x + w - s/2, y - s/2,   s, s),
            'bl': QRectF(x - s/2,   y + h - s/2, s, s),
            'br': QRectF(x + w - s/2, y + h - s/2, s, s),
            'l':  QRectF(x - s/2,   y + h/2 - s/2, s, s),
            'r':  QRectF(x + w - s/2, y + h/2 - s/2, s, s),
            't':  QRectF(x + w/2 - s/2, y - s/2,   s, s),
            'b':  QRectF(x + w/2 - s/2, y + h - s/2, s, s),
        }

    def boundingRect(self) -> QRectF:
        """Expand bounds so handles can be painted."""
        o = self.handle_size
        return super().boundingRect().adjusted(-o, -o, o, o)

    def paint(self, painter: QtGui.QPainter, option, widget) -> None:
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QtGui.QPen(Qt.blue, 1))
            painter.setBrush(QtGui.QBrush(Qt.white))
            for rect in self.handles.values():
                painter.drawRect(rect)

    def hoverMoveEvent(self, event) -> None:
        pos = event.pos()
        for name, rect in self.handles.items():
            if rect.contains(pos):
                self.setCursor(self.handle_cursors[name])
                break
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        pos = event.pos()
        for name, rect in self.handles.items():
            if rect.contains(pos):
                self._active_handle = name
                break
        else:
            self._active_handle = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._active_handle:
            # Compute new local rect coordinates
            r = self.rect()
            p = event.pos()
            x0, y0 = r.x(), r.y()
            x1, y1 = x0 + r.width(), y0 + r.height()
            if 'l' in self._active_handle: x0 = p.x()
            if 'r' in self._active_handle: x1 = p.x()
            if 't' in self._active_handle: y0 = p.y()
            if 'b' in self._active_handle: y1 = p.y()
            new_rect = QRectF(QPointF(x0, y0), QPointF(x1, y1)).normalized()
            
            # Clip to image bounds if available
            if self.image_bounds:
                scene_pos = self.pos()
                tl = self.mapToScene(QPointF(new_rect.x(), new_rect.y()))
                br = self.mapToScene(QPointF(new_rect.x() + new_rect.width(), 
                                            new_rect.y() + new_rect.height()))
                
                # Clip coordinates
                tl_x = max(0, min(tl.x(), self.image_bounds.width()))
                tl_y = max(0, min(tl.y(), self.image_bounds.height()))
                br_x = max(0, min(br.x(), self.image_bounds.width()))
                br_y = max(0, min(br.y(), self.image_bounds.height()))
                
                # Convert back to item coordinates
                tl_clipped = self.mapFromScene(QPointF(tl_x, tl_y))
                br_clipped = self.mapFromScene(QPointF(br_x, br_y))
                new_rect = QRectF(tl_clipped, br_clipped).normalized()

            # Offset item in scene if top/left moved
            dx, dy = new_rect.x(), new_rect.y()
            w, h = new_rect.width(), new_rect.height()

            # Apply: reset local rect to (0,0,w,h), shift item pos
            self.setRect(0, 0, w, h)
            scene_pos = self.pos()
            self.setPos(scene_pos.x() + dx, scene_pos.y() + dy)

            # Update handles and label
            self._update_handles_pos()
            self.update_text_position()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._active_handle = None
        # Ensure item is within bounds after release
        self._clip_to_bounds()
        super().mouseReleaseEvent(event)
    
    def itemChange(self, change, value):
        """Override to prevent moving outside image bounds"""
        if change == QtWidgets.QGraphicsItem.ItemPositionChange and self.image_bounds:
            new_pos = value
            rect = self.rect()
            
            # Calculate new scene coordinates
            tl = new_pos
            br = new_pos + QPointF(rect.width(), rect.height())
            
            # Clip to bounds
            new_x = max(0, min(tl.x(), self.image_bounds.width() - rect.width()))
            new_y = max(0, min(tl.y(), self.image_bounds.height() - rect.height()))
            
            return QPointF(new_x, new_y)
        
        return super().itemChange(change, value)
    
    def _clip_to_bounds(self):
        """Clip item to image bounds"""
        if not self.image_bounds:
            return
        
        tl = self.mapToScene(QPointF(0, 0))
        br = self.mapToScene(QPointF(self.rect().width(), self.rect().height()))
        
        # Clip coordinates
        x1 = max(0, min(tl.x(), self.image_bounds.width()))
        y1 = max(0, min(tl.y(), self.image_bounds.height()))
        x2 = max(0, min(br.x(), self.image_bounds.width()))
        y2 = max(0, min(br.y(), self.image_bounds.height()))
        
        # Update position and size
        w = x2 - x1
        h = y2 - y1
        if w > 0 and h > 0:
            self.setRect(0, 0, w, h)
            self.setPos(x1, y1)
            self._update_handles_pos()
            self.update_text_position()

    def get_center(self) -> QPointF:
        """Return center point in scene coordinates"""
        rect = self.rect()
        local_center = QPointF(rect.width()/2, rect.height()/2)
        return self.mapToScene(local_center)

    def to_dict(self) -> dict:
        """Export points in scene coordinates (4 จุด) with clipped coordinates"""
        tl = self.mapToScene(QPointF(0, 0))
        br = self.mapToScene(QPointF(self.rect().width(), self.rect().height()))
        x1, y1 = tl.x(), tl.y()
        x2, y2 = br.x(), br.y()
        
        # Clip to image bounds if available
        if self.image_bounds:
            x1 = max(0, min(x1, self.image_bounds.width()))
            y1 = max(0, min(y1, self.image_bounds.height()))
            x2 = max(0, min(x2, self.image_bounds.width()))
            y2 = max(0, min(y2, self.image_bounds.height()))
        
        return {
            'points': [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
            'transcription': self.get_transcription(),
            'difficult': False,
            'shape': 'Quad'  # บันทึกประเภทเพื่อไม่ให้สับสนกับ Polygon
        }