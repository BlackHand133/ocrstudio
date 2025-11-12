# modules/gui/window_handler/image_handler.py

import os
import logging
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QRectF
from modules.utils import sanitize_filename

logger = logging.getLogger("TextDetGUI")


class ImageHandler:
    """
    Manage image operations: load, select, display (with clear status indication)
    """

    # Colors for different statuses
    COLOR_NORMAL = QtGui.QColor(255, 255, 255)           # White - normal
    COLOR_ANNOTATED = QtGui.QColor(200, 255, 200)        # Light green - has annotation
    COLOR_CHECKED = QtGui.QColor(200, 230, 255)          # Light blue - checked
    COLOR_BOTH = QtGui.QColor(180, 255, 200)             # Green-blue - has annotation + checked

    def __init__(self, main_window):
        """
        Args:
            main_window: reference to MainWindow instance
        """
        self.main_window = main_window
    
    def open_folder(self):
        """Open folder and scan images recursively"""
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.main_window, "Select Image Folder", ""
        )
        if not folder:
            return

        # Supported image extensions
        exts = {'.jpg', '.jpeg', '.png', '.bmp'}
        
        self.main_window.image_items.clear()
        self.main_window.list_widget.clear()
        
        idx = 1
        for root_dir, _, files in os.walk(folder):
            for fn in sorted(files):
                if os.path.splitext(fn.lower())[1] in exts:
                    # Sanitize filename to remove space and special characters
                    clean_fn = sanitize_filename(fn)
                    key = f"{idx:04d}_{clean_fn}"
                    full = os.path.join(root_dir, fn)
                    self.main_window.image_items.append((key, full))
                    
                    item = QtWidgets.QListWidgetItem(key)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked)

                    # Show status with color and icon
                    self.update_item_appearance(item, key)
                    
                    self.main_window.list_widget.addItem(item)
                    idx += 1
        
        logger.info(f"Loaded {len(self.main_window.image_items)} images from {folder}")
    
    def update_item_appearance(self, item, key):
        """
        Update item appearance based on status

        Args:
            item: QListWidgetItem
            key: image key
        """
        has_annotation = bool(self.main_window.annotations.get(key))
        is_checked = item.checkState() == Qt.Checked

        # Set icon
        if has_annotation:
            item.setIcon(self.main_window.icon_marked)
        else:
            item.setIcon(QtGui.QIcon())

        # Set background color
        if has_annotation and is_checked:
            # Has annotation + checked
            item.setBackground(self.COLOR_BOTH)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        elif has_annotation:
            # Has annotation only
            item.setBackground(self.COLOR_ANNOTATED)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
        elif is_checked:
            # Checked only
            item.setBackground(self.COLOR_CHECKED)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
        else:
            # Normal
            item.setBackground(self.COLOR_NORMAL)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
    
    def refresh_all_items_appearance(self):
        """Refresh appearance of all items"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            key = item.text()
            self.update_item_appearance(item, key)
    
    def on_image_selected(self, item):
        """When user selects image from list"""
        QtWidgets.QApplication.processEvents()

        # Save annotation of current image first
        self.main_window.annotation_handler.save_current_annotation()
        
        key = item.text()

        # Find image path
        for k, full in self.main_window.image_items:
            if k == key:
                self.load_image(k, full)
                break

        # Load annotation
        self.main_window.annotation_handler.load_annotation(key)

        # Update table if in recog mode
        if self.main_window.recog_mode:
            self.main_window.table_handler.populate_table()

        # Update appearance of all items (in case checkbox was clicked)
        self.refresh_all_items_appearance()
    
    def load_image(self, key, full_path):
        """Load and display image on canvas (supports rotation)"""
        self.main_window.img_key = key
        self.main_window.img_path = full_path

        # Clear scene
        self.main_window.scene.clear()
        self.main_window.box_items.clear()

        # Check if there is rotation
        if hasattr(self.main_window, 'rotation_handler'):
            from modules.utils import imread_unicode
            import cv2
            
            img = self.main_window.rotation_handler.get_rotated_image(full_path, key)

            if img is not None:
                # Convert numpy array to QPixmap
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                h, w, c = img_rgb.shape
                bytes_per_line = c * w
                q_img = QtGui.QImage(img_rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
                pix = QtGui.QPixmap.fromImage(q_img)
            else:
                pix = QtGui.QPixmap(full_path)
        else:
            # If no rotation_handler, load normally
            pix = QtGui.QPixmap(full_path)
        
        self.main_window.scene.addPixmap(pix).setZValue(0)
        self.main_window.scene.setSceneRect(QRectF(pix.rect()))
        self.main_window.view.fitInView(
            self.main_window.scene.sceneRect(), 
            Qt.KeepAspectRatio
        )
        
        logger.debug(f"Loaded image: {key}")
    
    def is_item_checked(self, key):
        """Check if image is checked"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            if item.text() == key:
                return item.checkState() == Qt.Checked
        return False
    
    def check_only_annotated(self):
        """Check only images with annotations"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            key = item.text()
            has_annotation = bool(self.main_window.annotations.get(key))
            item.setCheckState(Qt.Checked if has_annotation else Qt.Unchecked)
            self.update_item_appearance(item, key)
        
        logger.info("Checked only annotated images")
    
    def uncheck_unannotated(self):
        """Uncheck images without annotations"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            key = item.text()
            if not self.main_window.annotations.get(key):
                item.setCheckState(Qt.Unchecked)
                self.update_item_appearance(item, key)
        
        logger.info("Unchecked unannotated images")
    
    def select_all_images(self):
        """Select all images (Check All)"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            item.setCheckState(Qt.Checked)
            key = item.text()
            self.update_item_appearance(item, key)
        
        logger.info("Selected all images")
    
    def deselect_all_images(self):
        """Deselect all images (Uncheck All)"""
        for i in range(self.main_window.list_widget.count()):
            item = self.main_window.list_widget.item(i)
            item.setCheckState(Qt.Unchecked)
            key = item.text()
            self.update_item_appearance(item, key)
        
        logger.info("Deselected all images")