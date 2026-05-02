# modules/gui/base_annotation_item.py

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QPointF
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtCore import QRectF

class BaseAnnotationItem:
    """
    Mixin class สำหรับ Annotation Items ทั้งหมด
    ให้ shared implementation ของ methods ที่ใช้ร่วมกัน
    """
    
    handle_size = 8
    
    def __init__(self):
        """Initialize common attributes"""
        # Text label (จะต้องสร้างใน subclass)
        self.text_item = None
    
    def to_dict(self) -> dict:
        """
        Export annotation เป็น dict format
        Subclass ต้อง override method นี้
        Returns:
            {
                'points': [[x1,y1], [x2,y2], ...],
                'transcription': str,
                'difficult': bool
            }
        """
        raise NotImplementedError("Subclass must implement to_dict()")
    
    def get_center(self) -> QPointF:
        """
        Return center point ของ annotation (สำหรับ centerOn)
        Subclass ต้อง override method นี้
        """
        raise NotImplementedError("Subclass must implement get_center()")
    
    def update_text_position(self):
        """
        อัปเดตตำแหน่ง text label
        Subclass ต้อง override method นี้
        """
        raise NotImplementedError("Subclass must implement update_text_position()")
    
    def create_text_item(self, text: str, parent):
        """สร้าง text label แบบมาตรฐาน"""
        self.text_item = QtWidgets.QGraphicsTextItem(text, parent)
        self.text_item.setDefaultTextColor(QtGui.QColor(255, 0, 0))
        self.text_item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.text_item.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.text_item.setAcceptedMouseButtons(QtCore.Qt.NoButton)
        self.text_item.setAcceptHoverEvents(False)
        
        # ทำให้ text อ่านง่ายขึ้นด้วย background
        font = self.text_item.font()
        font.setPointSize(10)
        font.setBold(True)
        self.text_item.setFont(font)
    
    def get_transcription(self) -> str:
        """Get text จาก label"""
        if self.text_item:
            return self.text_item.toPlainText()
        return ""
    
    def set_transcription(self, text: str):
        """Set text ใน label"""
        if self.text_item:
            self.text_item.setPlainText(text)
            self.update_text_position()

    def _save_to_parent(self):
        """Save annotation changes to parent main_window"""
        try:
            # Get scene from the item (self is the QGraphicsItem)
            scene = self.scene()
            if not scene:
                return

            # Get main_window from scene's views
            views = scene.views()
            if not views:
                return

            view = views[0]
            if hasattr(view, 'parent') and view.parent:
                main_window = view.parent
                if hasattr(main_window, 'annotation_handler'):
                    main_window.annotation_handler.save_current_annotation()
                    main_window.mark_as_modified()
        except Exception as e:
            # Silent fail - don't crash the app
            import logging
            logger = logging.getLogger("TextDetGUI")
            logger.debug(f"Failed to save annotation: {e}")