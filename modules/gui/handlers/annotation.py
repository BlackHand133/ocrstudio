# modules/gui/window_handler/annotation_handler.py

import logging
from PyQt5 import QtWidgets, QtGui
from modules.gui.items.box_item import BoxItem
from modules.gui.items.polygon_item import PolygonItem
from modules.gui.items.mask_item import MaskQuadItem, MaskPolygonItem
from modules.utils import sanitize_annotations

logger = logging.getLogger("TextDetGUI")


def is_valid_box(pts):
    """Check if points are valid"""
    if not (isinstance(pts, list) and len(pts) >= 4):
        return False
    for p in pts:
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            return False
    return True


class AnnotationHandler:
    """
    Manage annotations: add, delete, load, save
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference to MainWindow instance
        """
        self.main_window = main_window
    
    def add_box_item(self, pts, text, item_type=None, mask_color=None):
        """
        Add new annotation box (including mask items)
        
        Args:
            pts: list of points [[x1,y1], [x2,y2], ...]
            text: text in annotation
            item_type: 'Quad', 'Polygon', 'MaskQuad', 'MaskPolygon' (None = use value from annotation_type)
            mask_color: mask color (for mask items only)
        """
        if item_type is None:
            item_type = self.main_window.annotation_type
        
        # Check if it's a Mask Item
        is_mask = 'Mask' in item_type or text == '###'
        
        # Create item based on type
        if is_mask:
            # Create MaskItem
            if 'Quad' in item_type or (len(pts) == 4 and 'Polygon' not in item_type):
                from PyQt5.QtGui import QColor
                color = None
                if mask_color:
                    color = QColor(mask_color)
                box = MaskQuadItem(pts, color)
            else:
                from PyQt5.QtGui import QColor
                color = None
                if mask_color:
                    color = QColor(mask_color)
                box = MaskPolygonItem(pts, color)
        else:
            # Create normal BoxItem or PolygonItem
            if item_type == 'Quad' and len(pts) == 4:
                box = BoxItem(pts, text)
            else:
                box = PolygonItem(pts, text)
        
        box.setZValue(1)
        self.main_window.scene.addItem(box)
        self.main_window.box_items.append(box)
        
        logger.debug(f"Added {item_type} annotation: {text[:20]}")
    
    def clear_boxes(self):
        """Clear all annotation boxes"""
        for b in self.main_window.box_items:
            self.main_window.scene.removeItem(b)
        self.main_window.box_items.clear()
    
    def save_current_annotation(self):
        """Save annotation of current image"""
        if self.main_window.img_key:
            annotations = [b.to_dict() for b in self.main_window.box_items]
            self.main_window.annotations[self.main_window.img_key] = sanitize_annotations(annotations)
            self.update_list_icon(self.main_window.img_key)
    
    def load_annotation(self, key):
        """
        Load annotation of image (including mask items)
        
        Args:
            key: image key
        """
        ann = self.main_window.annotations.get(key, [])
        self.clear_boxes()
        
        for it in ann:
            if is_valid_box(it['points']):
                pts = it['points']
                text = it.get('transcription', '')
                
                # Use 'shape' field if available, otherwise use point count (backward compatibility)
                item_type = it.get('shape', 'Quad' if len(pts) == 4 else 'Polygon')
                
                # Get mask_color if available (for mask items)
                mask_color = it.get('mask_color', None)
                
                self.add_box_item(pts, text, item_type, mask_color)
        
        self.main_window.view.update()
        logger.debug(f"Loaded {len(ann)} annotations for {key}")
    
    def update_list_icon(self, key):
        """
        Update checkmark icon and color in list widget
        
        Args:
            key: image key
        """
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            if item.text() == key:
                # Update item appearance
                if hasattr(self.main_window.image_handler, 'update_item_appearance'):
                    self.main_window.image_handler.update_item_appearance(item, key)
                else:
                    # Fallback if new method doesn't exist
                    if self.main_window.annotations.get(key):
                        item.setIcon(self.main_window.icon_marked)
                    else:
                        item.setIcon(QtGui.QIcon())
                break
    
    def delete_selected(self):
        """Delete selected annotations (including mask items)"""
        sel = self.main_window.scene.selectedItems()
        removed = False
        
        for it in sel:
            # Check for BoxItem, PolygonItem and MaskItems
            if isinstance(it, (BoxItem, PolygonItem, MaskQuadItem, MaskPolygonItem)):
                self.main_window.scene.removeItem(it)
                self.main_window.box_items.remove(it)
                removed = True
        
        if removed:
            # Save changes
            annotations = [b.to_dict() for b in self.main_window.box_items]
            self.main_window.annotations[self.main_window.img_key] = sanitize_annotations(annotations)
            self.update_list_icon(self.main_window.img_key)
            self.main_window.workspace_handler.save_workspace()
            
            # Update table if in recog mode
            if self.main_window.recog_mode:
                self.main_window.table_handler.populate_table()
            
            logger.info(f"Deleted {len(sel)} annotations")
        else:
            QtWidgets.QMessageBox.information(
                self.main_window, "Delete", "No box selected"
            )
    
    def apply_detections(self, items):
        """
        Apply detection results
        
        Args:
            items: list of detection results
        """
        self.clear_boxes()
        
        for it in items:
            if not is_valid_box(it['points']):
                continue
            
            pts = it['points']
            # PaddleOCR detection results should always be Polygon to preserve original shape
            item_type = 'Polygon'  # Always use Polygon for detection
            self.add_box_item(pts, it['transcription'], item_type, mask_color=None)
        
        self.main_window.view.update()
        logger.info(f"Applied {len(items)} detections")