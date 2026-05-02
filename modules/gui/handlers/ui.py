# modules/gui/handlers/ui.py

import logging
from PyQt5 import QtWidgets

logger = logging.getLogger("TextDetGUI")


class UIHandler:
    """
    Manage UI interactions: draw mode, annotation type, mask mode.

    Mode flags are written to self.state (AppState).
    Qt widgets are accessed through self.main_window.
    """

    def __init__(self, state, services, main_window):
        self.state       = state
        self.services    = services
        self.main_window = main_window

    # ------------------------------------------------------------------ modes

    def toggle_draw_mode(self, checked: bool) -> None:
        """Enable or disable annotation-drawing mode."""
        self.state.draw_mode = checked

        drag_mode = (
            QtWidgets.QGraphicsView.NoDrag
            if checked
            else QtWidgets.QGraphicsView.RubberBandDrag
        )
        self.main_window.view.setDragMode(drag_mode)

        if checked:
            self.update_annotation_info()

        logger.debug(f"Draw mode: {checked}")

    def toggle_recog_mode(self, checked: bool) -> None:
        """Enable or disable recognition / table mode."""
        self.state.recog_mode = checked

        if checked:
            self.main_window.table_handler.populate_table()
        else:
            self.main_window.table.clearContents()
            self.main_window.table.setRowCount(0)

        if hasattr(self.main_window, "recog_toggle_btn"):
            self.main_window.recog_toggle_btn.setChecked(checked)

        logger.debug(f"Recognition mode: {checked}")

    def on_annotation_type_changed(self, new_type: str) -> None:
        """Switch between 'Quad' and 'Polygon' annotation types."""
        self.state.annotation_type = new_type
        self.update_annotation_info()

        # Exit draw mode when changing type
        if hasattr(self.main_window, "draw_action"):
            self.main_window.draw_action.setChecked(False)
            self.state.draw_mode = False

        logger.debug(f"Annotation type: {new_type}")

    # ------------------------------------------------------------------ UI helpers

    def update_annotation_info(self) -> None:
        """Update the instruction label for the current annotation type."""
        if not hasattr(self.main_window, "annotation_info_label"):
            return

        if self.state.annotation_type == "Quad":
            info = "(Drag to draw rectangle)"
        else:
            info = "(Click 4+ points, Right-click/Enter to finish, Esc to cancel)"

        self.main_window.annotation_info_label.setText(info)

    # ------------------------------------------------------------------ shape creation

    def add_box_from_rect(self, rect) -> None:
        """Add a Quad annotation from a drawn rectangle."""
        pts = [
            [rect.x(),               rect.y()],
            [rect.x() + rect.width(), rect.y()],
            [rect.x() + rect.width(), rect.y() + rect.height()],
            [rect.x(),               rect.y() + rect.height()],
        ]
        self.main_window.annotation_handler.add_box_item(pts, "", "Quad")

        if self.state.recog_mode:
            self.main_window.table_handler.populate_table()

        logger.debug("Added box from rectangle")

    def add_polygon_from_points(self, points: list) -> None:
        """Add a Polygon annotation from a list of points."""
        self.main_window.annotation_handler.add_box_item(points, "", "Polygon")

        if self.state.recog_mode:
            self.main_window.table_handler.populate_table()

        logger.debug(f"Added polygon with {len(points)} points")
