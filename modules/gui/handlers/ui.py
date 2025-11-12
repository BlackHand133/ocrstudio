# modules/gui/window_handler/ui_handler.py

import logging
from PyQt5 import QtWidgets

logger = logging.getLogger("TextDetGUI")


class UIHandler:
    """
    Manage UI interactions: draw mode, annotation type, etc.
    """

    def __init__(self, main_window):
        """
        Args:
            main_window: reference to MainWindow instance
        """
        self.main_window = main_window
    
    def toggle_draw_mode(self, checked):
        """
        Toggle draw box mode

        Args:
            checked: True = enable, False = disable
        """
        self.main_window.draw_mode = checked

        # Change drag mode
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
        Toggle Recognition mode (show table)

        Args:
            checked: True = enable, False = disable
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
        Change annotation type

        Args:
            new_type: 'Quad' or 'Polygon'
        """
        self.main_window.annotation_type = new_type
        self.update_annotation_info()

        # Disable draw mode when changing type
        if hasattr(self.main_window, 'draw_action'):
            self.main_window.draw_action.setChecked(False)
            self.main_window.draw_mode = False
        
        logger.debug(f"Annotation type changed to: {new_type}")
    
    def update_annotation_info(self):
        """Update instruction information"""
        if not hasattr(self.main_window, 'annotation_info_label'):
            return
        
        if self.main_window.annotation_type == 'Quad':
            info = "(Drag to draw rectangle)"
        else:
            info = "(Click 4+ points, Right-click/Enter to finish, Esc to cancel)"
        
        self.main_window.annotation_info_label.setText(info)
    
    def add_box_from_rect(self, rect):
        """
        Add Quad box from rectangle

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

        # Update table if in recog mode
        if self.main_window.recog_mode:
            self.main_window.table_handler.populate_table()
        
        logger.debug("Added box from rectangle")
    
    def add_polygon_from_points(self, points):
        """
        Add polygon from points

        Args:
            points: list of points [[x1,y1], [x2,y2], ...]
        """
        self.main_window.annotation_handler.add_box_item(points, "", 'Polygon')

        # Update table if in recog mode
        if self.main_window.recog_mode:
            self.main_window.table_handler.populate_table()
        
        logger.debug(f"Added polygon with {len(points)} points")