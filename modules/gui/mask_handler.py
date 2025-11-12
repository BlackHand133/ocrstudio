# modules/gui/mask_handler.py
"""
Mask Handler for managing data masking/redaction
Supports adding both Quad and Polygon mask items
"""

import logging
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt

logger = logging.getLogger("TextDetGUI")


class MaskHandler:
    """Manage Mask Operations"""

    def __init__(self, mainwin):
        self.mainwin = mainwin
        # Selected color for mask (default is black)
        self.current_mask_color = QtGui.QColor(0, 0, 0, 255)
    
    def add_mask_from_rect(self, rect):
        """Add Quad Mask from rectangle"""
        if not self.mainwin.img_key:
            return

        from modules.gui.items.mask_item import MaskQuadItem

        # Convert rect to 4 points
        x1, y1 = rect.left(), rect.top()
        x2, y2 = rect.right(), rect.bottom()
        pts = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

        # Create mask item
        mask = MaskQuadItem(pts, self.current_mask_color)
        self.mainwin.scene.addItem(mask)
        self.mainwin.box_items.append(mask)

        # Add to annotations
        key = self.mainwin.img_key
        if key not in self.mainwin.annotations:
            self.mainwin.annotations[key] = []
        self.mainwin.annotations[key].append(mask)
        
        # Update UI
        self._update_ui()
        
        logger.info(f"Added quad mask with color {self.current_mask_color.name()}")
    
    def add_mask_from_points(self, points):
        """Add Polygon Mask from points"""
        if not self.mainwin.img_key:
            return

        from modules.gui.items.mask_item import MaskPolygonItem

        # Create mask item
        mask = MaskPolygonItem(points, self.current_mask_color)
        self.mainwin.scene.addItem(mask)
        self.mainwin.box_items.append(mask)

        # Add to annotations
        key = self.mainwin.img_key
        if key not in self.mainwin.annotations:
            self.mainwin.annotations[key] = []
        self.mainwin.annotations[key].append(mask)

        # Update UI
        self._update_ui()
        
        logger.info(f"Added polygon mask with color {self.current_mask_color.name()}")
    
    def choose_mask_color(self):
        """Open color picker to select mask color"""
        color = QtWidgets.QColorDialog.getColor(
            self.current_mask_color,
            self.mainwin,
            "Choose Mask Color",
            QtWidgets.QColorDialog.ShowAlphaChannel
        )
        
        if color.isValid():
            self.current_mask_color = color
            logger.info(f"Mask color changed to {color.name()}")

            # Update color button
            if hasattr(self.mainwin, 'mask_color_btn'):
                self._update_color_button()
    
    def _update_color_button(self):
        """Update button showing current color"""
        if hasattr(self.mainwin, 'mask_color_btn'):
            color = self.current_mask_color
            # Create style showing background color
            text_color = "white" if color.lightness() < 128 else "black"
            self.mainwin.mask_color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: {text_color};
                    border: 2px solid #555;
                    padding: 5px 15px;
                    border-radius: 3px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 2px solid #888;
                }}
            """)
            self.mainwin.mask_color_btn.setText(f"🎨 Color: {color.name()}")
    
    def _update_ui(self):
        """Update UI after adding mask"""
        # Update annotation info
        if hasattr(self.mainwin, 'update_annotation_info'):
            self.mainwin.update_annotation_info()

        # Mark as having annotation
        if hasattr(self.mainwin, 'icon_marked') and hasattr(self.mainwin, 'list_widget'):
            key = self.mainwin.img_key
            for i in range(self.mainwin.list_widget.count()):
                item = self.mainwin.list_widget.item(i)
                item_key = item.data(Qt.UserRole)
                if item_key == key:
                    item.setIcon(self.mainwin.icon_marked)
                    break
    
    def change_selected_mask_color(self):
        """Change color of selected mask"""
        # Find selected mask items
        selected_items = self.mainwin.scene.selectedItems()
        mask_items = []
        
        for item in selected_items:
            if hasattr(item, 'set_mask_color'):  # Check if it's a mask item
                mask_items.append(item)
        
        if not mask_items:
            QtWidgets.QMessageBox.information(
                self.mainwin,
                "No Mask Selected",
                "Please select one or more mask items to change their color."
            )
            return

        # Select new color
        color = QtWidgets.QColorDialog.getColor(
            self.current_mask_color,
            self.mainwin,
            "Choose New Color for Selected Masks",
            QtWidgets.QColorDialog.ShowAlphaChannel
        )
        
        if color.isValid():
            # Change color of selected masks
            for mask in mask_items:
                mask.set_mask_color(color)
            
            logger.info(f"Changed color of {len(mask_items)} mask(s) to {color.name()}")
            
            QtWidgets.QMessageBox.information(
                self.mainwin,
                "Success",
                f"Changed color of {len(mask_items)} mask item(s)"
            )
    
    def get_mask_presets(self):
        """Return commonly used colors"""
        return {
            'Black': QtGui.QColor(0, 0, 0, 255),
            'White': QtGui.QColor(255, 255, 255, 255),
            'Gray': QtGui.QColor(128, 128, 128, 255),
            'Red': QtGui.QColor(255, 0, 0, 255),
            'Blur': QtGui.QColor(200, 200, 200, 200),  # Semi-transparent gray
        }
    
    def set_mask_color_preset(self, preset_name):
        """Set color from preset"""
        presets = self.get_mask_presets()
        if preset_name in presets:
            self.current_mask_color = presets[preset_name]
            self._update_color_button()
            logger.info(f"Set mask color to preset: {preset_name}")