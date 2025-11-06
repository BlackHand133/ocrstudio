# modules/gui/window_handler/export_handler.py

import os
import json
import logging
import cv2
import numpy as np
from PIL import Image
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from modules.utils import handle_exceptions, imread_unicode, imwrite_unicode, sanitize_annotations
from modules.data_splitter import DataSplitter
from modules.gui.split_config_dialog import SplitConfigDialog
from modules.augmentation import AugmentationPipeline
from modules.gui.augmentation_dialog import AugmentationDialog

# Import orientation classifier
try:
    import sys
    # Add path for importing textline_orientation
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from modules.textline_orientation import create_orientation_classifier
    ORIENTATION_MODEL_AVAILABLE = True
except ImportError as e:
    logging.warning(f"TextlineOrientationClassifier not available: {e}")
    ORIENTATION_MODEL_AVAILABLE = False
    create_orientation_classifier = None

logger = logging.getLogger("TextDetGUI")
PLACEHOLDER_TEXT = "<no_label>"


def is_valid_box(pts):
    """Check if points are valid"""
    if not (isinstance(pts, list) and len(pts) >= 4):
        return False
    for p in pts:
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            return False
    return True


class ExportHandler:
    """
    Export Dataset: Detection and Recognition
    Mask Items (for hiding certain parts)
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference to MainWindow instance
        """
        self.main_window = main_window
        self.orientation_stats = {
            '0': 0,
            '90': 0,
            '180': 0,
            '270': 0
        }
        
        # Create orientation classifier (if available)
        self.orientation_classifier = None
        if ORIENTATION_MODEL_AVAILABLE and create_orientation_classifier:
            try:
                self.orientation_classifier = create_orientation_classifier()
                if self.orientation_classifier:
                    logger.info("✅ Orientation classifier loaded successfully")
                else:
                    logger.warning("⚠️ Orientation classifier not available, using fallback")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load orientation classifier: {e}, using fallback")
    
    def _is_mask_item(self, ann):
        """
        Check if annotation is a mask item or not
        
        Args:
            ann: annotation dict
            
        Returns:
            bool: True if it's a mask item
        """
        shape = ann.get('shape', '')
        transcription = ann.get('transcription', '')
        
        # Check shape or transcription
        return 'Mask' in shape or transcription == '###'
    
    def _draw_masks_on_image(self, img, mask_items):
        """
        Draw mask items on image to hide certain parts in exported image
        
        Args:
            img: numpy array of image in original format
            mask_items: list of mask annotations
            
        Returns:
            numpy array of image with masks drawn
        """
        if not mask_items:
            return img
        
        img_copy = img.copy()
        
        for mask in mask_items:
            pts = mask.get('points', [])
            if not is_valid_box(pts):
                continue
            
            # Convert points to numpy array
            points = np.array(pts, dtype=np.int32)
            
            # Get mask_color (default black if not specified)
            mask_color_hex = mask.get('mask_color', '#000000')
            # Convert hex to RGB
            mask_color_hex = mask_color_hex.lstrip('#')
            r = int(mask_color_hex[0:2], 16)
            g = int(mask_color_hex[2:4], 16)
            b = int(mask_color_hex[4:6], 16)
            color_bgr = (b, g, r)  # OpenCV uses BGR
            
            # Draw filled polygon on image
            cv2.fillPoly(img_copy, [points], color_bgr)
        
        return img_copy
    
    
    def _detect_upside_down_with_model(self, img):
        """
        Detect upside-down using PaddlePaddle orientation model
        
        Args:
            img: numpy array of image (BGR format)
            
        Returns:
            bool: True if should rotate 180 degrees
        """
        if self.orientation_classifier is None:
            # Fallback to heuristic method
            return self._detect_upside_down_advanced(img)
        
        try:
            should_flip = self.orientation_classifier.should_flip_180(img, confidence_threshold=0.6)
            logger.debug(f"Model-based upside-down detection: flip={should_flip}")
            return should_flip
        except Exception as e:
            logger.error(f"Model-based detection failed: {e}, using fallback")
            return self._detect_upside_down_advanced(img)
    def _detect_upside_down_advanced(self, img):
        """
        Advanced heuristic for detecting upside-down images using techniques
        
        Techniques:
        1. Edge distribution analysis (horizontal edges)
        2. Variance analysis (top vs bottom)
        3. Content distribution
        4. Text region centroid analysis
        
        Args:
            img: numpy array of image
            
        Returns:
            bool: True if should rotate 180 degrees
        """
        try:
            if img is None or img.size == 0:
                return False
            
            h, w = img.shape[:2]
            
            # Skip small images
            if h < 20 or w < 20:
                return False
            
            # Convert to grayscale
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img.copy()
            
            votes = 0  # Number of votes for rotating 180 degrees
            
            # Method 1: Edge Distribution (weight 2)
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobelx_abs = np.abs(sobelx)
            
            mid = h // 2
            top_edge = np.mean(sobelx_abs[:mid, :])
            bottom_edge = np.mean(sobelx_abs[mid:, :])
            
            if top_edge > bottom_edge * 1.3:
                votes += 2
            elif bottom_edge > top_edge * 1.3:
                votes -= 2
            
            # Method 2: Variance Distribution (weight 1)
            # Compare variance between top and bottom
            top_var = np.var(gray[:mid, :])
            bottom_var = np.var(gray[mid:, :])
            
            if top_var > bottom_var * 1.2:
                votes += 1
            elif bottom_var > top_var * 1.2:
                votes -= 1
            
            # Method 3: Content Mass Distribution (weight 1)
            # Detect dark pixels as content mass
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Count pixels in top and bottom regions (dark pixels)
            top_content = np.sum(binary[:mid, :] < 128)
            bottom_content = np.sum(binary[mid:, :] < 128)
            
            if top_content > bottom_content * 1.3:
                votes += 1
            elif bottom_content > top_content * 1.3:
                votes -= 1
            
            # Method 4: Text region centroid analysis (weight 2)
            _, text_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(text_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            y_centroids = []
            areas = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 5:  # ignore small noise
                    M = cv2.moments(cnt)
                    if M["m00"] != 0:
                        cy = M["m01"] / M["m00"]
                        y_centroids.append(cy)
                        areas.append(area)
            if y_centroids:
                total_area = sum(areas)
                if total_area > 0:
                    weighted_y = sum(y * a for y, a in zip(y_centroids, areas)) / total_area
                    h_loc = gray.shape[0]
                    if weighted_y < h_loc / 2 * 1.1:  # text centroids too high
                        votes += 2
                    else:
                        votes -= 2
            
            # Decision rule: if votes >= 3 = should rotate 180
            should_rotate = votes >= 3
            
            logger.debug(f"Upside-down detection: votes={votes}, rotate={should_rotate} "
                        f"(edge: {top_edge:.1f}/{bottom_edge:.1f}, "
                        f"var: {top_var:.1f}/{bottom_var:.1f}, "
                        f"content: {top_content}/{bottom_content}, "
                        f"centroid_y: {np.mean(y_centroids) if y_centroids else 'N/A'})")
            
            return should_rotate
            
        except Exception as e:
            logger.error(f"Failed advanced upside-down detection: {e}")
            return False
    
    def _select_best_orientation(self, img, auto_orient=True):
        """
        Select best orientation for text with LTR assumption
        
        CRITICAL FIX: Force portrait → landscape conversion
        
        1. Check if portrait (H > W) → rotate to landscape
        2. Try all angles (0, 90, 180, 270) and calculate horizontal projection std
        3. Select angle with highest score
        4. Use ML model to detect upside-down and flip 180° if needed
        
        Args:
            img: numpy array of image (BGR format)
            auto_orient: if True, perform auto orientation
            
        Returns:
            tuple: (oriented_img, final_angle)
        """
        if not auto_orient or img is None:
            return img, 0
        
        h, w = img.shape[:2]
        if min(h, w) < 20:
            return img, 0
        
        rot_dict = {
            0: lambda x: x,
            90: lambda x: cv2.rotate(x, cv2.ROTATE_90_COUNTERCLOCKWISE),
            180: lambda x: cv2.rotate(x, cv2.ROTATE_180),
            270: lambda x: cv2.rotate(x, cv2.ROTATE_90_CLOCKWISE),
        }
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()
        
        # CRITICAL FIX: Force portrait to landscape
        # If portrait (height > width), only try 90° and 270° rotations
        is_portrait = h > w * 1.1  # 10% threshold to avoid false positives
        
        if is_portrait:
            # Portrait mode: only consider 90° and 270° (landscape orientations)
            angles_to_try = [90, 270]
            logger.debug(f"Image is portrait ({h}x{w}), forcing landscape orientation")
        else:
            # Already landscape or square: try all angles
            angles_to_try = [0, 90, 180, 270]
            logger.debug(f"Image is landscape ({h}x{w}), trying all orientations")
        
        scores = {}
        max_angle = 0
        max_score = -1
        best_rot_gray = gray
        
        for angle in angles_to_try:
            rot_gray = rot_dict[angle](gray)
            
            # Calculate horizontal projection score
            _, bin_img = cv2.threshold(rot_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            proj = np.sum(bin_img, axis=0).astype(float)
            score = np.std(proj)
            
            # Bonus score for landscape orientation
            rot_h, rot_w = rot_gray.shape[:2]
            if rot_w > rot_h:
                score *= 1.2  # 20% bonus for landscape
            
            scores[angle] = score
            if score > max_score:
                max_score = score
                max_angle = angle
                best_rot_gray = rot_gray
        
        best_img = rot_dict[max_angle](img)
        
        # Detect upside-down using ML model
        should_flip = self._detect_upside_down_with_model(best_rot_gray)
        if should_flip:
            best_img = cv2.rotate(best_img, cv2.ROTATE_180)
            final_angle = (max_angle + 180) % 360
        else:
            final_angle = max_angle
        
        # Final check: ensure result is landscape
        final_h, final_w = best_img.shape[:2]
        if final_h > final_w * 1.1:
            logger.warning(f"Result still portrait ({final_h}x{final_w}), forcing 90° rotation")
            best_img = cv2.rotate(best_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            final_angle = (final_angle + 90) % 360
        
        logger.debug(
            f"Best orientation: {final_angle}° "
            f"(initial: {max_angle}°, score: {max_score:.2f}, "
            f"flip: {should_flip}, scores: {scores})"
        )
        
        self.orientation_stats[str(final_angle)] += 1
        
        return best_img, final_angle
    
    def _crop_rotated_box(self, img, pts, auto_detect=True):
        """
        Crop image according to rotated rectangle and transform to straight
        
        Uses 2 methods:
        1. If points are exactly 4 corners -> use perspective transform directly
        2. If points more or less than 4 -> use minimum area rectangle then transform
        
        Args:
            img: numpy array of image (BGR format)
            pts: list of points [[x1,y1], [x2,y2], ...]
            auto_detect: use auto-detection for post-processing
            
        Returns:
            numpy array of cropped image straightened, or None if failed
        """
        try:
            # Validate input
            if img is None or not isinstance(pts, list) or len(pts) < 3:
                logger.error("Invalid input for rotated crop")
                return None
            
            # Convert points to numpy array
            points = np.array(pts, dtype=np.float32)
            
            # Method 1: If exactly 4 points provided -> use direct perspective transform
            if len(points) == 4:
                logger.debug("Using 4-point direct perspective transform")
                
                # Arrange points: top-left, top-right, bottom-right, bottom-left
                rect = self._order_points(points)
                
                # Calculate width and height of straight rectangle
                # Use distance along edges
                width_top = np.linalg.norm(rect[1] - rect[0])
                width_bottom = np.linalg.norm(rect[2] - rect[3])
                max_width = max(int(width_top), int(width_bottom))
                
                height_left = np.linalg.norm(rect[3] - rect[0])
                height_right = np.linalg.norm(rect[2] - rect[1])
                max_height = max(int(height_left), int(height_right))
                
                # Validate size
                if max_width < 1 or max_height < 1:
                    logger.error(f"Invalid calculated size: {max_width}x{max_height}")
                    return None
                
                # Create destination points (straight rectangle)
                dst_points = np.array([
                    [0, 0],
                    [max_width - 1, 0],
                    [max_width - 1, max_height - 1],
                    [0, max_height - 1]
                ], dtype=np.float32)
                
                # Calculate transformation matrix
                M = cv2.getPerspectiveTransform(rect, dst_points)
                
                # Perform perspective transform
                warped = cv2.warpPerspective(img, M, (max_width, max_height))
                
                # Post-process for horizontal and no upside-down
                warped, _ = self._select_best_orientation(warped, auto_orient=auto_detect)
                
                return warped
            
            # Method 2: If not exactly 4 points -> find minimum area rectangle
            else:
                logger.debug(f"Using minAreaRect for {len(points)} points")
                
                # Find minimum area rectangle
                rect = cv2.minAreaRect(points)
                
                # Returns (center, (width, height), angle)
                (cx, cy), (w, h), angle = rect
                
                # Validate size
                if w < 1 or h < 1:
                    logger.error(f"Invalid rectangle size: {w}x{h}")
                    return None
                
                # Get 4 corners of rotated rectangle
                box = cv2.boxPoints(rect)
                box = box.astype(np.float32)
                
                # Arrange points
                box_sorted = self._order_points(box)
                
                # Calculate size along edges (use minAreaRect dimensions)
                dst_w = int(w)
                dst_h = int(h)
                
                if dst_w < 1 or dst_h < 1:
                    logger.error(f"Invalid destination size: {dst_w}x{dst_h}")
                    return None
                
                # Create destination points
                dst_points = np.array([
                    [0, 0],
                    [dst_w - 1, 0],
                    [dst_w - 1, dst_h - 1],
                    [0, dst_h - 1]
                ], dtype=np.float32)
                
                # Calculate transformation matrix
                M = cv2.getPerspectiveTransform(box_sorted, dst_points)
                
                # Perform perspective transform
                warped = cv2.warpPerspective(img, M, (dst_w, dst_h))
                
                # Post-process for horizontal and no upside-down
                warped, _ = self._select_best_orientation(warped, auto_orient=auto_detect)
                
                return warped
            
        except Exception as e:
            logger.error(f"Failed to crop rotated box: {e}", exc_info=True)
            return None
    
    def _order_points(self, pts):
        """
        Arrange points into: top-left, top-right, bottom-right, bottom-left
        
        Method used:
        - Sort points by y-coordinate (top first, then by x for left-right)
        - Arrange top and bottom points by x (left to right)
        
        Args:
            pts: numpy array shape (4, 2)
            
        Returns:
            numpy array shape (4, 2) arranged correctly [TL, TR, BR, BL]
        """
        # Convert to list of tuples for sorting
        pts_list = [(pt[0], pt[1]) for pt in pts]
        
        # Sort points by y (ascending, then by x ascending for top row)
        pts_list.sort(key=lambda p: (p[1], p[0]))
        
        # First 2 points are top row, last 2 are bottom row
        top_points = pts_list[:2]
        bottom_points = pts_list[2:]
        
        # Arrange top row: sort by x (left to right)
        top_points.sort(key=lambda p: p[0])
        tl, tr = top_points
        
        # Arrange bottom row: sort by x (left to right)
        bottom_points.sort(key=lambda p: p[0])
        bl, br = bottom_points
        
        # Create numpy array in order: TL, TR, BR, BL
        ordered = np.array([tl, tr, br, bl], dtype=np.float32)
        
        return ordered
    
    def _crop_bounding_box(self, img, pts, auto_detect=True):
        """
        Crop image according to bounding box (axis-aligned, no rotation)
        
        Args:
            img: numpy array of image (BGR format)
            pts: list of points [[x1,y1], [x2,y2], ...]
            auto_detect: use auto-detection for post-processing
            
        Returns:
            numpy array of cropped image straightened, or None if failed
        """
        try:
            h, w = img.shape[:2]
            
            # Find bounding box
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x1, y1 = int(min(xs)), int(min(ys))
            x2, y2 = int(max(xs)), int(max(ys))
            
            # Clip to image bounds
            x1, y1 = max(0, min(x1, w)), max(0, min(y1, h))
            x2, y2 = max(0, min(x2, w)), max(0, min(y2, h))
            
            if x2 <= x1 or y2 <= y1:
                return None
            
            # Crop
            crop = img[y1:y2, x1:x2]
            
            # Post-process for horizontal and no upside-down
            crop, _ = self._select_best_orientation(crop, auto_orient=auto_detect)
            
            return crop
            
        except Exception as e:
            logger.error(f"Failed to crop bounding box: {e}")
            return None
    
    def _show_crop_method_dialog(self):
        """
        Show dialog to select crop method for Recognition export
        
        Returns:
            tuple: (crop_method, auto_detect_orientation)
                - crop_method: 'rotated' or 'bbox' or None
                - auto_detect_orientation: True/False
        """
        dialog = QtWidgets.QDialog(self.main_window)
        dialog.setWindowTitle("Recognition Export - Options")
        dialog.setMinimumWidth(500)
        
        layout = QtWidgets.QVBoxLayout()
        
        # Title
        title = QtWidgets.QLabel("<b>Select options for Recognition Export:</b>")
        title.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(title)
        
        # Crop Method Group
        crop_group = QtWidgets.QGroupBox("✅ Crop Method")
        crop_layout = QtWidgets.QVBoxLayout()
        
        radio_rotated = QtWidgets.QRadioButton("🔄 Auto-Straighten (Rotated Rectangle)")
        radio_rotated.setToolTip("Straighten rotated text lines and crop image automatically")
        radio_rotated.setChecked(True)
        
        radio_bbox = QtWidgets.QRadioButton("📦 Bounding Box (axis-aligned)")
        radio_bbox.setToolTip("Crop using bounding box without straightening image")
        
        crop_layout.addWidget(radio_rotated)
        crop_layout.addWidget(radio_bbox)
        crop_group.setLayout(crop_layout)
        layout.addWidget(crop_group)
        
        # Orientation Detection Group
        orient_group = QtWidgets.QGroupBox("🔍 Orientation Detection")
        orient_layout = QtWidgets.QVBoxLayout()
        
        check_auto_detect = QtWidgets.QCheckBox("🤖 Auto-Detect & Fix Orientation (recommended)")
        check_auto_detect.setChecked(True)
        check_auto_detect.setToolTip(
            "Detect and fix text orientation automatically (0/90/180/270°)\n"
            "Uses horizontal projection + baseline analysis\n"
            "Assumes horizontal text LTR (left to right)"
        )
        
        info_label = QtWidgets.QLabel(
            "<small>ℹ️ How it works:<br>"
            "&nbsp;&nbsp;• Horizontal alignment (projection)<br>"
            "&nbsp;&nbsp;• Baseline & centroid detection<br>"
            "&nbsp;&nbsp;• Edge & content distribution<br>"
            "<br>"
            "⚠️ Assumes horizontal text LTR</small>"
        )
        info_label.setStyleSheet("color: #666; padding: 5px;")
        
        orient_layout.addWidget(check_auto_detect)
        orient_layout.addWidget(info_label)
        orient_group.setLayout(orient_layout)
        layout.addWidget(orient_group)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        btn_ok = QtWidgets.QPushButton("✅ OK")
        btn_cancel = QtWidgets.QPushButton("❌ Cancel")
        
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Show dialog
        result = dialog.exec_()
        
        if result == QtWidgets.QDialog.Accepted:
            crop_method = 'rotated' if radio_rotated.isChecked() else 'bbox'
            auto_detect = check_auto_detect.isChecked()
            return crop_method, auto_detect
        else:
            return None, False
    
    @handle_exceptions
    def save_labels_detection(self):
        """Save Detection Dataset with Augmentation (Unicode-safe)"""
        # Save current annotation batch
        self.main_window.annotation_handler.save_current_annotation()
        
        # Get annotations that are checked
        keys = [
            k for k, ann in self.main_window.annotations.items() 
            if ann and self.main_window.image_handler.is_item_checked(k)
        ]
        
        if not keys:
            QtWidgets.QMessageBox.information(
                self.main_window, "No Annotations", 
                "No annotations selected for export"
            )
            return
        
        folder_name, ok = QtWidgets.QInputDialog.getText(
            self.main_window, "Save Detection Dataset", 
            "Choose Dataset:",
            QtWidgets.QLineEdit.Normal, "dataset_det"
        )
        if not ok or not folder_name.strip():
            return
        folder_name = folder_name.strip()
        
        # Dialog for Split Config
        dialog = SplitConfigDialog(self.main_window, mode='detection', total_items=len(keys))
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        config = dialog.result
        if not config:
            return
        
        # Request Augmentation
        aug_config = None
        reply = QtWidgets.QMessageBox.question(
            self.main_window, 'Augmentation', 
            'Apply Data Augmentation?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            aug_dialog = AugmentationDialog(self.main_window, mode='detection')
            if aug_dialog.exec_() == QtWidgets.QDialog.Accepted:
                aug_config = aug_dialog.result
        
        # Create Pipeline
        pipeline = None
        if aug_config:
            pipeline = AugmentationPipeline(mode=aug_config['mode'])
            for aug in aug_config['augmentations']:
                pipeline.add_augmentation(aug['type'], aug['params'])
        
        split_result = self._split_data(keys, config)
        
        # Export
        self._export_detection_dataset(
            folder_name, split_result, config, pipeline, aug_config
        )
    
    def _split_data(self, keys, config):
        """Split data according to config"""
        splitter = DataSplitter(seed=config.get('seed'))
        
        # Check if using advanced splitting
        use_density = 'density' in config.get('advanced', {})
        use_curvature = 'curvature' in config.get('advanced', {})
        
        if use_density or use_curvature:
            if use_density:
                density_scores = splitter.analyze_text_density(self.main_window.annotations)
                split_result = splitter.split_by_density_stratified(
                    keys, density_scores,
                    train_pct=config['splits'].get('train', 0),
                    test_pct=config['splits'].get('test', 0),
                    valid_pct=config['splits'].get('valid', 0)
                )
            elif use_curvature:
                curvature_scores = splitter.analyze_text_curvature(self.main_window.annotations)
                split_result = splitter.split_by_density_stratified(
                    keys, curvature_scores,
                    train_pct=config['splits'].get('train', 0),
                    test_pct=config['splits'].get('test', 0),
                    valid_pct=config['splits'].get('valid', 0)
                )
        else:
            if config['method'] == 'percentage':
                split_result = splitter.split_by_percentage(
                    keys,
                    train_pct=config['splits'].get('train', 0),
                    test_pct=config['splits'].get('test', 0),
                    valid_pct=config['splits'].get('valid', 0)
                )
            else:
                split_result = splitter.split_by_count(
                    keys,
                    train_count=config['splits'].get('train', 0),
                    test_count=config['splits'].get('test', 0),
                    valid_count=config['splits'].get('valid', 0)
                )
        
        return split_result
    
    def _export_detection_dataset(self, folder_name, split_result, config, pipeline, aug_config):
        """Export Detection Dataset"""
        dataset_dir = os.path.join(self.main_window.output_det_dir, folder_name)
        img_dir = os.path.join(dataset_dir, "img")
        
        split_dirs = {}
        for split_name in split_result.keys():
            split_dirs[split_name] = os.path.join(img_dir, split_name)
            os.makedirs(split_dirs[split_name], exist_ok=True)
        
        # Path mapping
        path_map = dict(self.main_window.image_items)
        all_labels = {split_name: [] for split_name in split_result.keys()}
        
        # Progress dialog
        total_keys = sum(len(v) for v in split_result.values())
        progress = QtWidgets.QProgressDialog(
            "Processing images...", "Cancel", 0, total_keys, self.main_window
        )
        progress.setWindowModality(Qt.WindowModal)
        
        processed = 0
        for split_name, split_keys in split_result.items():
            for key in split_keys:
                progress.setValue(processed)
                if progress.wasCanceled():
                    break
                
                img_path = path_map[key]
                
                # Load image (Unicode-safe)
                if hasattr(self.main_window, 'rotation_handler'):
                    img = self.main_window.rotation_handler.get_rotated_image(img_path, key)
                else:
                    img = imread_unicode(img_path)
                
                if img is None:
                    logger.error(f"Failed to read image: {img_path}")
                    processed += 1
                    continue
                
                # Get annotations
                annotations = self.main_window.annotations[key]
                
                # Separate mask items from normal annotations
                mask_items = [
                    ann for ann in annotations 
                    if self._is_mask_item(ann)
                ]
                filtered_annotations = [
                    ann for ann in annotations 
                    if not self._is_mask_item(ann)
                ]
                
                # Skip if no annotations (only masks)
                if not filtered_annotations:
                    logger.info(f"Skipping {key}: only mask items, no annotations")
                    processed += 1
                    continue
                
                bboxes = [ann['points'] for ann in filtered_annotations]
                
                # Draw mask items on image for export
                if mask_items:
                    img = self._draw_masks_on_image(img, mask_items)
                
                # Save image with masks applied
                img_filename = f"{key}.jpg"
                img_save_path = os.path.join(split_dirs[split_name], img_filename)
                success = imwrite_unicode(img_save_path, img)
                
                if not success:
                    logger.error(f"Failed to write image: {img_save_path}")
                    processed += 1
                    continue
                
                # Prepare labels
                rel_path = f"img/{split_name}/{img_filename}"
                all_labels[split_name].append((rel_path, filtered_annotations))
                
                # Augmentation (if enabled)
                if pipeline and aug_config:
                    target_splits = aug_config.get('target_splits', ['train'])
                    
                    if split_name in target_splits:
                        try:
                            aug_results = pipeline.apply(img, bboxes)
                            
                            for aug_img, aug_bboxes, aug_name in aug_results:
                                aug_filename = f"{key}_{aug_name}.jpg"
                                aug_save_path = os.path.join(split_dirs[split_name], aug_filename)
                                
                                success = imwrite_unicode(aug_save_path, aug_img)
                                
                                if not success:
                                    logger.error(f"Failed to write augmented image: {aug_save_path}")
                                    continue
                                
                                # Prepare annotations for augmented image
                                aug_annotations = []
                                for bbox, ann in zip(aug_bboxes, filtered_annotations):
                                    new_ann = ann.copy()
                                    new_ann['points'] = bbox
                                    aug_annotations.append(new_ann)
                                
                                aug_rel_path = f"img/{split_name}/{aug_filename}"
                                all_labels[split_name].append((aug_rel_path, aug_annotations))
                        
                        except Exception as e:
                            logger.error(f"Augmentation failed for {key}: {e}")
                
                processed += 1
        
        progress.setValue(total_keys)
        
        # Create label files
        label_files = {
            split_name: os.path.join(dataset_dir, f"labels_{split_name}.txt") 
            for split_name in split_result.keys()
        }
        all_lbl = os.path.join(dataset_dir, "labels_all.txt")
        
        with open(all_lbl, 'w', encoding='utf-8') as fa:
            for split_name, labels in all_labels.items():
                with open(label_files[split_name], 'w', encoding='utf-8') as f:
                    for rel_path, anns in labels:
                        # Sanitize annotations and serialize
                        clean = []
                        for ann in anns:
                            txt = ann.get("transcription", "").strip() or PLACEHOLDER_TEXT
                            clean.append({
                                "points": ann["points"],
                                "transcription": txt,
                                "difficult": ann.get("difficult", False)
                            })
                        clean = sanitize_annotations(clean)
                        line = f"{rel_path}\t{json.dumps(clean, ensure_ascii=False)}\n"
                        f.write(line)
                        fa.write(line)
        
        total_images = sum(len(labels) for labels in all_labels.values())
        stats = "\n".join([
            f"  • {name.title()}: {len(labels)} images" 
            for name, labels in all_labels.items()
        ])
        
        aug_info = ""
        if aug_config:
            aug_list = [aug['type'] for aug in aug_config['augmentations']]
            target_splits = aug_config.get('target_splits', ['train'])
            aug_info = f"\n\n🎨 Augmentations:\n  • " + "\n  • ".join(aug_list)
            aug_info += f"\n  • Mode: {aug_config['mode']}"
            aug_info += f"\n  • Applied to: {', '.join(target_splits)}"
        
        QtWidgets.QMessageBox.information(
            self.main_window, "Save Detection Dataset",
            f"✅ Detection Dataset saved successfully!\n\n"
            f"📁 Location: {dataset_dir}\n\n"
            f"📊 Statistics:\n{stats}\n  • Total: {total_images} images{aug_info}\n\n"
            f"ℹ️ Notes: Mask items are hidden in exported images"
        )
        
        logger.info(f"Exported detection dataset to {dataset_dir}")
    
    @handle_exceptions
    def export_recognition(self):
        """Save Recognition Dataset (Cropped Text Images) with Augmentation"""
        # Save current annotation batch
        self.main_window.annotation_handler.save_current_annotation()
        
        folder_name, ok = QtWidgets.QInputDialog.getText(
            self.main_window, "Export Recognition Dataset", 
            "Choose Dataset:",
            QtWidgets.QLineEdit.Normal, "dataset_rec"
        )
        if not ok or not folder_name.strip():
            return
        folder_name = folder_name.strip()
        
        # Collect crops
        crops = []
        for key, full in self.main_window.image_items:
            if not self.main_window.image_handler.is_item_checked(key):
                continue
            
            for idx, ann in enumerate(self.main_window.annotations.get(key, [])):
                # Skip mask items
                if self._is_mask_item(ann):
                    continue
                
                pts = ann.get("points", [])
                txt = ann.get("transcription", "").strip() or PLACEHOLDER_TEXT
                
                if not is_valid_box(pts):
                    continue
                
                crops.append((key, full, idx, pts, txt))
        
        if not crops:
            QtWidgets.QMessageBox.information(
                self.main_window, "Export Rec", 
                "No valid annotations for export\n(Mask items excluded)"
            )
            return
        
        # Show crop method and orientation dialog
        crop_result = self._show_crop_method_dialog()
        if crop_result[0] is None:
            return  # User cancelled
        
        crop_method, auto_detect = crop_result
        
        # Dialog for Split Config
        dialog = SplitConfigDialog(self.main_window, mode='recognition', total_items=len(crops))
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        config = dialog.result
        if not config:
            return
        
        # Request Augmentation
        aug_config = None
        reply = QtWidgets.QMessageBox.question(
            self.main_window, 'Augmentation', 
            'Apply Data Augmentation?',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
            QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            aug_dialog = AugmentationDialog(self.main_window, mode='recognition')
            if aug_dialog.exec_() == QtWidgets.QDialog.Accepted:
                aug_config = aug_dialog.result
        
        # Create Pipeline
        pipeline = None
        if aug_config:
            pipeline = AugmentationPipeline(mode=aug_config['mode'])
            for aug in aug_config['augmentations']:
                pipeline.add_augmentation(aug['type'], aug['params'])
        
        splitter = DataSplitter(seed=config.get('seed'))
        
        if config['method'] == 'percentage':
            split_result = splitter.split_by_percentage(
                crops,
                train_pct=config['splits'].get('train', 0),
                test_pct=config['splits'].get('test', 0),
                valid_pct=config['splits'].get('valid', 0)
            )
        else:
            split_result = splitter.split_by_count(
                crops,
                train_count=config['splits'].get('train', 0),
                test_count=config['splits'].get('test', 0),
                valid_count=config['splits'].get('valid', 0)
            )
        
        # Reset stats
        self.orientation_stats = {
            '0': 0,
            '90': 0,
            '180': 0,
            '270': 0
        }
        
        # Export
        self._export_recognition_dataset(
            folder_name, split_result, pipeline, aug_config, crop_method, auto_detect
        )
    
    def _export_recognition_dataset(self, folder_name, split_result, pipeline, aug_config, 
                                   crop_method='bbox', auto_detect=True):
        """Export Recognition Dataset"""
        rec_dir = os.path.join(self.main_window.output_rec_dir, folder_name)
        img_base = os.path.join(rec_dir, "images")
        
        split_dirs = {
            split_name: os.path.join(img_base, split_name) 
            for split_name in split_result.keys()
        }
        for d in split_dirs.values():
            os.makedirs(d, exist_ok=True)
        
        label_files = {
            split_name: os.path.join(rec_dir, f"{split_name}.txt") 
            for split_name in split_result.keys()
        }
        
        # Progress dialog
        total_crops = sum(len(v) for v in split_result.values())
        progress = QtWidgets.QProgressDialog(
            "Processing crops...", "Cancel", 0, total_crops, self.main_window
        )
        progress.setWindowModality(Qt.WindowModal)
        
        all_crops = {split_name: [] for split_name in split_result.keys()}
        
        # Process crops
        processed = 0
        failed_crops = 0
        horizontal_count = 0  # Count images that end up horizontal
        
        for split_name, split_items in split_result.items():
            for item in split_items:
                progress.setValue(processed)
                if progress.wasCanceled():
                    break
                
                key, full, idx, pts, txt = item
                
                try:
                    # Load image (considering rotation)
                    img_np = None
                    
                    if hasattr(self.main_window, 'rotation_handler'):
                        img_np = self.main_window.rotation_handler.get_rotated_image(full, key)
                    
                    if img_np is None:
                        img_np = imread_unicode(full)
                    
                    if img_np is None:
                        logger.error(f"Failed to load image: {key}")
                        failed_crops += 1
                        processed += 1
                        continue
                    
                    # Draw mask items on image before crop
                    mask_items = [
                        ann for ann in self.main_window.annotations.get(key, [])
                        if self._is_mask_item(ann)
                    ]
                    if mask_items:
                        logger.debug(f"Drawing {len(mask_items)} masks on {key}")
                        img_np = self._draw_masks_on_image(img_np, mask_items)
                    
                    # Crop according to selected method
                    logger.debug(f"Cropping {key}_{idx} using {crop_method} method")
                    
                    if crop_method == 'rotated':
                        crop_np = self._crop_rotated_box(img_np, pts, auto_detect=auto_detect)
                    else:  # 'bbox'
                        crop_np = self._crop_bounding_box(img_np, pts, auto_detect=auto_detect)
                    
                    if crop_np is None or crop_np.size == 0:
                        logger.error(f"Failed to crop: {key}_{idx} (method: {crop_method})")
                        failed_crops += 1
                        processed += 1
                        continue
                    
                    # Validate crop size
                    if crop_np.shape[0] < 5 or crop_np.shape[1] < 5:
                        logger.warning(f"Crop too small: {key}_{idx} ({crop_np.shape}), skipping")
                        failed_crops += 1
                        processed += 1
                        continue
                    
                    # Check if final crop is horizontal (not portrait)
                    h, w = crop_np.shape[:2]
                    if w >= h:  # Horizontal (or square)
                        horizontal_count += 1
                    
                    # Save crop
                    fn = f"{key}_{idx}.jpg"
                    path = os.path.join(split_dirs[split_name], fn)
                    
                    success = imwrite_unicode(path, crop_np)
                    
                    if not success:
                        logger.error(f"Failed to write crop: {path}")
                        failed_crops += 1
                        processed += 1
                        continue
                    
                    all_crops[split_name].append((f"images/{split_name}/{fn}", txt))
                    
                    # Augmentation (if enabled)
                    if pipeline and aug_config:
                        target_splits = aug_config.get('target_splits', ['train'])
                        
                        if split_name in target_splits:
                            try:
                                aug_results = pipeline.apply(crop_np, None)
                                
                                for aug_img, _, aug_name in aug_results:
                                    aug_fn = f"{key}_{idx}_{aug_name}.jpg"
                                    aug_path = os.path.join(split_dirs[split_name], aug_fn)
                                    
                                    success = imwrite_unicode(aug_path, aug_img)
                                    
                                    if not success:
                                        logger.error(f"Failed to write augmented crop: {aug_path}")
                                        continue
                                    
                                    all_crops[split_name].append((f"images/{split_name}/{aug_fn}", txt))
                            
                            except Exception as e:
                                logger.error(f"Augmentation failed for crop {fn}: {e}")
                
                except Exception as e:
                    logger.error(f"Crop failed for {key}_{idx}: {e}")
                    failed_crops += 1
                
                processed += 1
        
        progress.setValue(total_crops)
        
        # Create label files
        for split_name, crop_list in all_crops.items():
            with open(label_files[split_name], "w", encoding="utf-8") as f:
                for rel_path, text in crop_list:
                    f.write(f"{rel_path}\t{text}\n")
        
        total_crops_saved = sum(len(v) for v in all_crops.values())
        stats = "\n".join([
            f"  • {name.title()}: {len(items)} crops" 
            for name, items in all_crops.items()
        ])
        
        aug_info = ""
        if aug_config:
            aug_list = [aug['type'] for aug in aug_config['augmentations']]
            target_splits = aug_config.get('target_splits', ['train'])
            aug_info = f"\n\n🎨 Augmentations:\n  • " + "\n  • ".join(aug_list)
            aug_info += f"\n  • Mode: {aug_config['mode']}"
            aug_info += f"\n  • Applied to: {', '.join(target_splits)}"
        
        crop_method_name = "🔄 Auto-Straighten" if crop_method == 'rotated' else "📦 Bounding Box"
        
        # Calculate percentage
        horizontal_pct = (horizontal_count / total_crops_saved * 100) if total_crops_saved > 0 else 0
        
        # Orientation stats
        orient_info = ""
        if auto_detect:
            orient_lines = [f"  • {angle}°: {count}" for angle, count in self.orientation_stats.items()]
            orient_info = f"\n🔍 Orientation Correction:\n" + "\n".join(orient_lines)
        
        failed_msg = f"\n⚠️ Failed: {failed_crops} crops" if failed_crops > 0 else ""
        
        QtWidgets.QMessageBox.information(
            self.main_window, "Export Recognition Dataset",
            f"✅ Recognition Dataset saved successfully!\n\n"
            f"📁 Location: {rec_dir}\n\n"
            f"📊 Statistics:\n{stats}\n  • Total: {total_crops_saved} crops{aug_info}\n\n"
            f"✅ Crop Method: {crop_method_name}\n"
            f"📐 Final Orientation: {horizontal_count}/{total_crops_saved} horizontal ({horizontal_pct:.1f}%){orient_info}{failed_msg}\n\n"
            f"ℹ️ Notes:\n"
            f"  • Mask items are hidden in exported images\n"
            f"  • Crops are processed for horizontal LTR (left to right) text\n"
            f"  • {'Uses auto-orientation' if auto_detect else 'No auto-orientation'}"
        )
        
        logger.info(f"Exported recognition dataset to {rec_dir} using {crop_method} method")
        logger.info(f"Horizontal orientation: {horizontal_count}/{total_crops_saved} ({horizontal_pct:.1f}%)")
        if auto_detect:
            logger.info(f"Orientation stats: {self.orientation_stats}")