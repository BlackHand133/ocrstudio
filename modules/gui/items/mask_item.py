# modules/gui/mask_item.py
"""
Masking/Redaction Items for hiding sensitive information in images
Supports both Quad (rectangle) and Polygon (multi-sided) shapes
with automatic boundary clipping to prevent overflow
"""

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QRectF, QPointF
from typing import List, Union


class MaskQuadItem(QtWidgets.QGraphicsRectItem):
    """
    Quad Mask Item - solid rectangle for covering sensitive data
    Drawn with solid color (not transparent) to hide information
    with automatic boundary protection
    """
    
    handle_cursors = {
        'tl': Qt.SizeFDiagCursor, 'tr': Qt.SizeBDiagCursor,
        'bl': Qt.SizeBDiagCursor, 'br': Qt.SizeFDiagCursor,
        'l': Qt.SizeHorCursor,    'r': Qt.SizeHorCursor,
        't': Qt.SizeVerCursor,    'b': Qt.SizeVerCursor,
    }
    
    def __init__(self, pts: List[Union[List[float], tuple]], mask_color: QtGui.QColor = None):
        # Compute bounds
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        w, h = x2 - x1, y2 - y1
        
        super().__init__(0, 0, w, h)
        self.setPos(x1, y1)
        
        # Set color (default is solid black)
        if mask_color is None:
            mask_color = QtGui.QColor(0, 0, 0, 255)  # Solid black
        
        self.mask_color = mask_color
        
        # Set pen and brush - no border
        self.setPen(QtGui.QPen(Qt.NoPen))  # No border
        self.setBrush(QtGui.QBrush(self.mask_color))
        
        # Enable interactions
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        # Label showing this is a mask
        self.text_item = QtWidgets.QGraphicsTextItem("🔒 MASKED", self)
        self.text_item.setDefaultTextColor(Qt.white if self.mask_color.lightness() < 128 else Qt.black)
        font = self.text_item.font()
        font.setBold(True)
        font.setPointSize(10)
        self.text_item.setFont(font)
        
        # Handles
        self.handle_size = 8
        self.handles = {}
        self._active_handle = None
        
        # Image bounds (will be set by scene)
        self.image_bounds = None
        
        self._update_handles_pos()
        self.update_text_position()
    
    def set_image_bounds(self, width: int, height: int):
        """Set image boundaries for clipping"""
        self.image_bounds = QRectF(0, 0, width, height)
    
    def update_text_position(self):
        """Position label in the center of the box"""
        if self.text_item:
            tr = self.text_item.boundingRect()
            r = self.rect()
            self.text_item.setPos(
                (r.width() - tr.width()) / 2,
                (r.height() - tr.height()) / 2
            )
    
    def _update_handles_pos(self):
        """Calculate resize handle positions"""
        r = self.rect()
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        s = self.handle_size
        self.handles = {
            'tl': QRectF(x - s/2, y - s/2, s, s),
            'tr': QRectF(x + w - s/2, y - s/2, s, s),
            'bl': QRectF(x - s/2, y + h - s/2, s, s),
            'br': QRectF(x + w - s/2, y + h - s/2, s, s),
            'l':  QRectF(x - s/2, y + h/2 - s/2, s, s),
            'r':  QRectF(x + w - s/2, y + h/2 - s/2, s, s),
            't':  QRectF(x + w/2 - s/2, y - s/2, s, s),
            'b':  QRectF(x + w/2 - s/2, y + h - s/2, s, s),
        }
    
    def boundingRect(self):
        o = self.handle_size
        return super().boundingRect().adjusted(-o, -o, o, o)
    
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QtGui.QPen(Qt.yellow, 2, Qt.DashLine))
            painter.setBrush(QtGui.QBrush(Qt.white))
            for rect in self.handles.values():
                painter.drawRect(rect)
    
    def hoverMoveEvent(self, event):
        pos = event.pos()
        for name, rect in self.handles.items():
            if rect.contains(pos):
                self.setCursor(self.handle_cursors[name])
                break
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)
    
    def mousePressEvent(self, event):
        pos = event.pos()
        for name, rect in self.handles.items():
            if rect.contains(pos):
                self._active_handle = name
                break
        else:
            self._active_handle = None
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._active_handle:
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
            
            dx, dy = new_rect.x(), new_rect.y()
            w, h = new_rect.width(), new_rect.height()
            
            self.setRect(0, 0, w, h)
            scene_pos = self.pos()
            self.setPos(scene_pos.x() + dx, scene_pos.y() + dy)
            
            self._update_handles_pos()
            self.update_text_position()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
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
    
    def to_dict(self):
        """Export as dict format with clipped coordinates"""
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
            'transcription': '###',  # Use ### to indicate masked area
            'difficult': False,
            'shape': 'MaskQuad',
            'mask_color': self.mask_color.name()  # Save color as hex
        }
    
    def set_mask_color(self, color: QtGui.QColor):
        """Change mask color"""
        self.mask_color = color
        self.setBrush(QtGui.QBrush(color))
        # Update text color
        self.text_item.setDefaultTextColor(
            Qt.white if color.lightness() < 128 else Qt.black
        )


class MaskPolygonItem(QtWidgets.QGraphicsPolygonItem):
    """
    Polygon Mask Item - solid polygon for covering sensitive data
    Drawn with solid color (not transparent) to hide information
    with automatic boundary protection
    """
    
    def __init__(self, pts: List[Union[List[float], tuple]], mask_color: QtGui.QColor = None):
        poly = QtGui.QPolygonF([QPointF(float(p[0]), float(p[1])) for p in pts])
        super().__init__(poly)
        
        # Set color (default is solid black)
        if mask_color is None:
            mask_color = QtGui.QColor(0, 0, 0, 255)
        
        self.mask_color = mask_color
        
        # Set pen and brush - no border
        self.setPen(QtGui.QPen(Qt.NoPen))  # No border
        self.setBrush(QtGui.QBrush(self.mask_color))
        
        # Enable interactions
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        
        # Label showing this is a mask
        self.text_item = QtWidgets.QGraphicsTextItem("🔒 MASKED", self)
        self.text_item.setDefaultTextColor(Qt.white if self.mask_color.lightness() < 128 else Qt.black)
        font = self.text_item.font()
        font.setBold(True)
        font.setPointSize(10)
        self.text_item.setFont(font)
        
        # Vertex handles
        self.handle_size = 8
        self._active_vertex = None
        
        # Image bounds (will be set by scene)
        self.image_bounds = None
        
        self.update_text_position()
    
    def set_image_bounds(self, width: int, height: int):
        """Set image boundaries for clipping"""
        self.image_bounds = QRectF(0, 0, width, height)
    
    def update_text_position(self):
        """Position label in the center of polygon"""
        if self.text_item and not self.polygon().isEmpty():
            rect = self.polygon().boundingRect()
            tr = self.text_item.boundingRect()
            self.text_item.setPos(
                rect.center().x() - tr.width() / 2,
                rect.center().y() - tr.height() / 2
            )
    
    def boundingRect(self):
        o = self.handle_size
        return super().boundingRect().adjusted(-o, -o, o, o)
    
    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QtGui.QPen(Qt.yellow, 2, Qt.DashLine))
            painter.setBrush(QtGui.QBrush(Qt.white))
            for i in range(self.polygon().size()):
                pt = self.polygon().at(i)
                r = self.handle_size / 2
                painter.drawEllipse(pt, r, r)
    
    def _get_vertex_at(self, pos: QPointF):
        threshold = self.handle_size
        for i in range(self.polygon().size()):
            pt = self.polygon().at(i)
            if (pt - pos).manhattanLength() < threshold:
                return i
        return -1
    
    def hoverMoveEvent(self, event):
        if self._get_vertex_at(event.pos()) >= 0:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)
    
    def mousePressEvent(self, event):
        self._active_vertex = self._get_vertex_at(event.pos())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._active_vertex is not None and self._active_vertex >= 0:
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
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
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
    
    def to_dict(self):
        """Export as dict format with clipped coordinates"""
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
            'transcription': '###',  # Use ### to indicate masked area
            'difficult': False,
            'shape': 'MaskPolygon',
            'mask_color': self.mask_color.name()
        }
    
    def set_mask_color(self, color: QtGui.QColor):
        """Change mask color"""
        self.mask_color = color
        self.setBrush(QtGui.QBrush(color))
        # Update text color
        self.text_item.setDefaultTextColor(
            Qt.white if color.lightness() < 128 else Qt.black
        )