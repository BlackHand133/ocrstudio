# modules/gui/handlers/rotation.py

import logging
import cv2
import numpy as np
from typing import List, Optional

from PyQt5 import QtWidgets

from modules.utils import imread_unicode

logger = logging.getLogger("TextDetGUI")


class RotationHandler:
    """
    Manage image rotation and coordinate transform of annotations.

    Data access goes through self.state (AppState).
    """

    def __init__(self, state, services, main_window):
        """
        Args:
            state:       AppState instance.
            services:    Services container.
            main_window: MainWindow reference (Qt widget access only).
        """
        self.state       = state
        self.services    = services
        self.main_window = main_window

    # ------------------------------------------------------------------ public

    def rotate_current_image(self, angle: int) -> None:
        """
        Rotate the current image and its annotations by *angle* degrees.

        Args:
            angle: Degrees to rotate (90, -90, or 180).
        """
        if not self.state.img_key or not self.state.img_path:
            QtWidgets.QMessageBox.warning(
                self.main_window, "Warning", "Please select an image first"
            )
            return

        key = self.state.img_key

        # Save current annotations before rotating
        self.main_window.annotation_handler.save_current_annotation()

        current_rotation = self.state.image_rotations.get(key, 0)
        new_rotation     = (current_rotation + angle) % 360

        self.state.image_rotations[key] = new_rotation

        # Rotate annotation coordinates
        self._rotate_annotations(key, angle)

        # Reload image and annotations
        self.main_window.image_handler.load_image(key, self.state.img_path)
        self.main_window.annotation_handler.load_annotation(key)
        self.main_window.workspace_handler.save_workspace()

        logger.info(f"Rotated image {key} by {angle}° (total: {new_rotation}°)")

    def reset_rotation(self) -> None:
        """Reset rotation for the current image."""
        if not self.state.img_key:
            return

        key = self.state.img_key
        if key in self.state.image_rotations:
            del self.state.image_rotations[key]

            self.main_window.image_handler.load_image(key, self.state.img_path)
            self.main_window.annotation_handler.load_annotation(key)
            self.main_window.workspace_handler.save_workspace()

            logger.info(f"Reset rotation for {key}")

    def get_rotated_image(self, img_path: str, key: str) -> Optional[np.ndarray]:
        """
        Load image and apply stored rotation.

        Args:
            img_path: Path to image file.
            key:      Image key used to look up the stored rotation.

        Returns:
            Rotated numpy array, or None on read failure.
        """
        img = imread_unicode(img_path)
        if img is None:
            return None

        rotation = self.state.image_rotations.get(key, 0)
        if rotation == 0:
            return img

        return self.rotate_image_cv2(img, rotation)

    # ------------------------------------------------------------------ static helpers

    @staticmethod
    def rotate_image_cv2(img: np.ndarray, angle: int) -> np.ndarray:
        """Rotate *img* by *angle* degrees using OpenCV."""
        if angle == 0:
            return img
        elif angle == 90:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(img, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            h, w    = img.shape[:2]
            center  = (w / 2, h / 2)
            M       = cv2.getRotationMatrix2D(center, angle, 1.0)
            cos     = np.abs(M[0, 0])
            sin     = np.abs(M[0, 1])
            new_w   = int((h * sin) + (w * cos))
            new_h   = int((h * cos) + (w * sin))
            M[0, 2] += (new_w / 2) - center[0]
            M[1, 2] += (new_h / 2) - center[1]
            return cv2.warpAffine(img, M, (new_w, new_h), borderMode=cv2.BORDER_REPLICATE)

    # ------------------------------------------------------------------ private

    def _rotate_annotations(self, key: str, angle: int) -> None:
        annotations = self.state.annotations.get(key, [])
        if not annotations:
            return

        img_path = self.state.get_image_path(key)
        if not img_path:
            return

        img = imread_unicode(img_path)
        if img is None:
            return

        h, w = img.shape[:2]

        rotated = []
        for ann in annotations:
            new_ann          = ann.copy()
            new_ann["points"] = self._rotate_points(ann.get("points", []), angle, w, h)
            rotated.append(new_ann)

        self.state.annotations[key] = rotated

    def _rotate_points(
        self,
        points: List[List[float]],
        angle: int,
        w: int,
        h: int,
    ) -> List[List[float]]:
        rotated = []
        for pt in points:
            x, y = pt[0], pt[1]
            if angle == 90:
                new_x, new_y = h - y, x
            elif angle == -90:
                new_x, new_y = y, w - x
            elif angle == 180:
                new_x, new_y = w - x, h - y
            else:
                new_x, new_y = x, y
            rotated.append([new_x, new_y])
        return rotated
