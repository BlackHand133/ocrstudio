"""
Recognition dataset exporter for OCR training.

This module exports cropped text images for recognition/OCR training:
- Cropped text regions (rotated or bounding box)
- Auto-orientation detection
- Label files with transcriptions
- Train/test/valid splits
- Optional augmentation
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from modules.export.base import BaseExporter
from modules.export import utils as export_utils
from modules.utils import imread_unicode, imwrite_unicode, sanitize_filename
from modules.augmentation import AugmentationPipeline
from modules.data.splitter import DataSplitter

logger = logging.getLogger("TextDetGUI")
PLACEHOLDER_TEXT = "<no_label>"


class RecognitionExporter(BaseExporter):
    """
    Exporter for text recognition datasets.

    Exports:
    - Cropped text images (straightened)
    - Auto-orientation detection and correction
    - Label files with transcriptions
    - Train/test/valid splits
    """

    def __init__(self, main_window):
        """
        Initialize recognition exporter.

        Args:
            main_window: Reference to MainWindow instance
        """
        super().__init__(main_window)

        # Orientation statistics
        self.orientation_stats = {
            '0': 0,
            '90': 0,
            '180': 0,
            '270': 0
        }

        # Try to get orientation classifier
        self.orientation_classifier = None
        if hasattr(main_window, 'orientation_classifier'):
            self.orientation_classifier = main_window.orientation_classifier

    def export(self, folder_name: str, split_config: Dict,
               crop_method: str = 'rotated', auto_detect: bool = True,
               aug_config: Optional[Dict] = None, image_format: str = 'png') -> bool:
        """
        Export recognition dataset.

        Args:
            folder_name: Output folder name
            split_config: Split configuration
            crop_method: 'rotated' or 'bbox'
            auto_detect: Auto-detect orientation
            aug_config: Augmentation configuration (optional)
            image_format: Image format ('png' or 'jpg', default: 'png')

        Returns:
            bool: True if successful
        """
        try:
            # Collect crops
            crops = self._collect_crops()

            if not crops:
                QtWidgets.QMessageBox.information(
                    self.main_window, "Export Rec",
                    "No valid annotations for export\n(Mask items excluded)"
                )
                return False

            # Create augmentation pipeline
            pipeline = None
            if aug_config:
                pipeline = AugmentationPipeline(mode=aug_config['mode'])
                for aug in aug_config['augmentations']:
                    pipeline.add_augmentation(aug['type'], aug['params'])

            # Split data
            splitter = DataSplitter(seed=split_config.get('seed'))

            if split_config['method'] == 'percentage':
                split_result = splitter.split_by_percentage(
                    crops,
                    train_pct=split_config['splits'].get('train', 0),
                    test_pct=split_config['splits'].get('test', 0),
                    valid_pct=split_config['splits'].get('valid', 0)
                )
            else:
                split_result = splitter.split_by_count(
                    crops,
                    train_count=split_config['splits'].get('train', 0),
                    test_count=split_config['splits'].get('test', 0),
                    valid_count=split_config['splits'].get('valid', 0)
                )

            # Reset orientation stats
            self.orientation_stats = {'0': 0, '90': 0, '180': 0, '270': 0}

            # Export dataset
            success = self._export_recognition_dataset(
                folder_name, split_result, pipeline, aug_config,
                crop_method, auto_detect, image_format
            )

            return success

        except Exception as e:
            logger.error(f"Recognition export failed: {e}", exc_info=True)
            QtWidgets.QMessageBox.critical(
                self.main_window, "Export Error",
                f"Failed to export recognition dataset:\n{str(e)}"
            )
            return False

    def _collect_crops(self) -> List[Tuple]:
        """
        Collect all crops from checked images.

        Returns:
            List of tuples: (key, full_path, idx, points, text)
        """
        crops = []

        for key, full in self.main_window.image_items:
            if not self.main_window.image_handler.is_item_checked(key):
                continue

            for idx, ann in enumerate(self.main_window.annotations.get(key, [])):
                # Skip mask items
                if export_utils.is_mask_item(ann):
                    continue

                pts = ann.get("points", [])
                txt = ann.get("transcription", "").strip() or PLACEHOLDER_TEXT

                if not export_utils.is_valid_box(pts):
                    continue

                crops.append((key, full, idx, pts, txt))

        return crops

    def _export_recognition_dataset(self, folder_name: str, split_result: Dict,
                                   pipeline: Optional[AugmentationPipeline],
                                   aug_config: Optional[Dict],
                                   crop_method: str = 'bbox',
                                   auto_detect: bool = True,
                                   image_format: str = 'png') -> bool:
        """
        Export recognition dataset with all files.

        Args:
            folder_name: Output folder name
            split_result: Dict of split_name -> list of crop tuples
            pipeline: Augmentation pipeline (optional)
            aug_config: Augmentation configuration (optional)
            crop_method: 'rotated' or 'bbox'
            auto_detect: Auto-detect orientation
            image_format: Image format ('png' or 'jpg', default: 'png')

        Returns:
            bool: True if successful
        """
        # Create output directories
        rec_dir = os.path.join(self.main_window.output_rec_dir, folder_name)
        img_base = os.path.join(rec_dir, "images")

        split_dirs = {
            split_name: os.path.join(img_base, split_name)
            for split_name in split_result.keys()
        }
        for d in split_dirs.values():
            self._ensure_dir(d)

        label_files = {
            split_name: os.path.join(rec_dir, f"{split_name}.txt")
            for split_name in split_result.keys()
        }

        # Progress dialog
        total_crops = sum(len(v) for v in split_result.values())
        progress = QtWidgets.QProgressDialog(
            "Exporting Recognition Dataset...", "Cancel", 0, total_crops, self.main_window
        )
        progress.setWindowTitle("Export Recognition Dataset")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        all_crops = {split_name: [] for split_name in split_result.keys()}

        # Process crops
        processed = 0
        failed_crops = 0
        horizontal_count = 0  # Count horizontal crops

        for split_name, split_items in split_result.items():
            for item in split_items:
                progress.setValue(processed)
                key, full, idx, pts, txt = item
                progress.setLabelText(f"Processing: {key} (crop {idx})\n({processed+1}/{total_crops}) [{split_name}]")
                QtWidgets.QApplication.processEvents()

                if progress.wasCanceled():
                    logger.info("Recognition export cancelled by user")
                    progress.close()
                    return False

                try:
                    # Load image (with rotation support)
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
                        if export_utils.is_mask_item(ann)
                    ]
                    if mask_items:
                        logger.debug(f"Drawing {len(mask_items)} masks on {key}")
                        img_np = export_utils.draw_masks_on_image(img_np, mask_items)

                    # Crop according to method
                    logger.debug(f"Cropping {key}_{idx} using {crop_method} method")

                    if crop_method == 'rotated':
                        crop_result = export_utils.crop_rotated_box(
                            img_np, pts, auto_detect=auto_detect,
                            orientation_classifier=self.orientation_classifier,
                            return_angle=True
                        )
                        if crop_result is None:
                            crop_np = None
                            angle_used = 0
                        elif isinstance(crop_result, tuple):
                            crop_np, angle_used = crop_result
                        else:
                            crop_np = crop_result
                            angle_used = 0
                    else:  # 'bbox'
                        crop_result = export_utils.crop_bounding_box(
                            img_np, pts, auto_detect=auto_detect,
                            orientation_classifier=self.orientation_classifier,
                            return_angle=True
                        )
                        if crop_result is None:
                            crop_np = None
                            angle_used = 0
                        elif isinstance(crop_result, tuple):
                            crop_np, angle_used = crop_result
                        else:
                            crop_np = crop_result
                            angle_used = 0

                    # Track orientation statistics
                    if auto_detect and crop_np is not None:
                        angle_key = str(angle_used)
                        if angle_key in self.orientation_stats:
                            self.orientation_stats[angle_key] += 1

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

                    # Check if horizontal
                    h, w = crop_np.shape[:2]
                    if w >= h:
                        horizontal_count += 1

                    # Save crop
                    clean_key = sanitize_filename(
                        key.replace('.jpg', '').replace('.jpeg', '')
                           .replace('.png', '').replace('.bmp', '')
                           .replace('.jfif', '').replace('.tiff', '').replace('.tif', '')
                           .replace('.webp', '').replace('.gif', '').replace('.ico', '')
                    )
                    fn = f"{clean_key}_{idx}.{image_format}"
                    path = os.path.join(split_dirs[split_name], fn)

                    success = imwrite_unicode(path, crop_np, image_format=image_format)

                    if not success:
                        logger.error(f"Failed to write crop: {path}")
                        failed_crops += 1
                        processed += 1
                        continue

                    all_crops[split_name].append((f"{folder_name}/images/{split_name}/{fn}", txt))

                    # Augmentation (if enabled)
                    if pipeline and aug_config:
                        target_splits = aug_config.get('target_splits', ['train'])

                        if split_name in target_splits:
                            try:
                                aug_results = pipeline.apply(crop_np, None)

                                for aug_img, _, aug_name in aug_results:
                                    # Sanitize augmentation name
                                    clean_aug_name = sanitize_filename(aug_name.replace('.', '_'))
                                    aug_fn = f"{clean_key}_{idx}_{clean_aug_name}.{image_format}"
                                    aug_path = os.path.join(split_dirs[split_name], aug_fn)

                                    success = imwrite_unicode(aug_path, aug_img, image_format=image_format)

                                    if not success:
                                        logger.error(f"Failed to write augmented crop: {aug_path}")
                                        continue

                                    all_crops[split_name].append(
                                        (f"{folder_name}/images/{split_name}/{aug_fn}", txt)
                                    )

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

        # Create orientation report if auto-detection was used
        if auto_detect:
            rotated_count = self.orientation_stats.get('90', 0) + self.orientation_stats.get('180', 0) + self.orientation_stats.get('270', 0)
            if rotated_count > 0:
                report_path = os.path.join(rec_dir, "orientation_report.txt")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write("=" * 60 + "\n")
                    f.write("ORIENTATION DETECTION REPORT\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"Total crops processed: {total_crops}\n")
                    f.write(f"Crops with orientation correction: {rotated_count}\n\n")
                    f.write("Orientation Statistics:\n")
                    for angle, count in sorted(self.orientation_stats.items()):
                        pct = (count / total_crops * 100) if total_crops > 0 else 0
                        f.write(f"  • {angle:3s}°: {count:4d} crops ({pct:5.1f}%)\n")
                    f.write("\n" + "-" * 60 + "\n")
                    f.write("IMPORTANT WARNING:\n")
                    f.write("-" * 60 + "\n")
                    f.write("ML-based orientation detection is NOT 100% accurate.\n")
                    f.write(f"{rotated_count} images were automatically rotated.\n\n")
                    f.write("RECOMMENDED ACTIONS:\n")
                    f.write("1. Manually inspect all exported crops\n")
                    f.write("2. Pay special attention to images with rotation (90°/180°/270°)\n")
                    f.write("3. Check if any images are upside-down or incorrectly rotated\n")
                    f.write("4. Correct any errors before training your model\n")
                    f.write("\nProblematic images may appear in any rotation category.\n")
                    f.write("Visual inspection is the most reliable verification method.\n")
                logger.info(f"Orientation report saved to: {report_path}")

        # Show completion message
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
        orientation_warning = ""
        if auto_detect:
            orient_lines = [f"  • {angle}°: {count}" for angle, count in self.orientation_stats.items()]
            orient_info = f"\n🔍 Orientation Correction:\n" + "\n".join(orient_lines)

            # Add warning if non-zero rotations detected
            rotated_count = self.orientation_stats.get('90', 0) + self.orientation_stats.get('180', 0) + self.orientation_stats.get('270', 0)
            if rotated_count > 0:
                orientation_warning = (
                    f"\n\n⚠️ IMPORTANT: Auto-orientation corrected {rotated_count} images.\n"
                    f"   ML models are NOT 100% accurate. Please verify your dataset:\n"
                    f"   • Check if any images are upside-down or incorrectly rotated\n"
                    f"   • Pay special attention to images with rotation (90°/180°/270°)\n"
                    f"   • Manual verification is recommended before training\n"
                    f"   • See 'orientation_report.txt' for detailed statistics"
                )

        failed_msg = f"\n⚠️ Failed: {failed_crops} crops" if failed_crops > 0 else ""

        # Show completion message with option to open folder
        msg_box = QtWidgets.QMessageBox(self.main_window)
        msg_box.setWindowTitle("Export Recognition Dataset")
        msg_box.setText("✅ Recognition Dataset saved successfully!")
        msg_box.setInformativeText(
            f"📁 Location:\n{rec_dir}\n\n"
            f"📊 Statistics:\n{stats}\n  • Total: {total_crops_saved} crops{aug_info}\n\n"
            f"✅ Crop Method: {crop_method_name}\n"
            f"📐 Final Orientation: {horizontal_count}/{total_crops_saved} horizontal ({horizontal_pct:.1f}%){orient_info}{failed_msg}{orientation_warning}\n\n"
            f"ℹ️ Notes:\n"
            f"  • Mask items are hidden in exported images\n"
            f"  • Crops are processed for horizontal LTR text\n"
            f"  • {'Uses auto-orientation' if auto_detect else 'No auto-orientation'}"
        )
        msg_box.setIcon(QtWidgets.QMessageBox.Information)

        # Add buttons
        btn_open = msg_box.addButton("Open Folder", QtWidgets.QMessageBox.ActionRole)
        msg_box.addButton(QtWidgets.QMessageBox.Ok)

        msg_box.exec_()

        # Check if user clicked Open Folder
        if msg_box.clickedButton() == btn_open:
            import subprocess
            import sys
            if sys.platform == 'win32':
                os.startfile(rec_dir)
            elif sys.platform == 'darwin':
                subprocess.run(['open', rec_dir])
            else:
                subprocess.run(['xdg-open', rec_dir])

        logger.info(f"Exported recognition dataset to {rec_dir} using {crop_method} method")
        logger.info(f"Horizontal orientation: {horizontal_count}/{total_crops_saved} ({horizontal_pct:.1f}%)")
        if auto_detect:
            logger.info(f"Orientation stats: {self.orientation_stats}")
            rotated_count = self.orientation_stats.get('90', 0) + self.orientation_stats.get('180', 0) + self.orientation_stats.get('270', 0)
            if rotated_count > 0:
                logger.warning(f"Auto-orientation corrected {rotated_count} images. Manual verification recommended!")
                logger.warning("ML-based orientation detection is not 100% accurate. Please verify exported crops.")

        return True
