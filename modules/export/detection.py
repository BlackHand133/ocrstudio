"""
Detection dataset exporter for text detection training.

This module exports datasets in PaddleOCR detection format:
- Images with bounding boxes
- Label files with annotations
- Train/test/valid splits
- Optional augmentation
"""

import os
import json
import logging
from typing import Dict, List, Optional
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from modules.export.base import BaseExporter
from modules.export.utils import ExportValidationError
from modules.export import utils as export_utils
from modules.utils import imread_unicode, imwrite_unicode, sanitize_annotations, sanitize_filename
from modules.augmentation import AugmentationPipeline

logger = logging.getLogger("TextDetGUI")
PLACEHOLDER_TEXT = "<no_label>"


class DetectionExporter(BaseExporter):
    """
    Exporter for text detection datasets.

    Exports:
    - Images with mask items applied
    - Bounding box annotations in JSON format
    - PaddleOCR label format
    - Train/test/valid splits
    """

    def export(self, folder_name: str, split_config: Dict,
               aug_config: Optional[Dict] = None, image_format: str = 'png') -> bool:
        """
        Export detection dataset.

        Args:
            folder_name: Output folder name
            split_config: Split configuration
            aug_config: Augmentation configuration (optional)
            image_format: Image format ('png' or 'jpg', default: 'png')

        Returns:
            bool: True if successful
        """
        try:
            # Get checked image keys
            keys = [
                k for k, ann in self.main_window.annotations.items()
                if ann and self.main_window.image_handler.is_item_checked(k)
            ]

            if not keys:
                raise ExportValidationError(
                    "No annotated images are selected for export.\n"
                    "Please annotate at least one image and ensure it is checked in the list."
                )

            # Create augmentation pipeline
            pipeline = None
            if aug_config:
                pipeline = AugmentationPipeline(mode=aug_config['mode'])
                for aug in aug_config['augmentations']:
                    pipeline.add_augmentation(aug['type'], aug['params'])

            # Split data
            split_result = self._split_data(keys, split_config)

            # Export dataset
            success = self._export_detection_dataset(
                folder_name, split_result, split_config, pipeline, aug_config, image_format
            )

            return success

        except Exception as e:
            logger.error(f"Detection export failed: {e}", exc_info=True)
            QtWidgets.QMessageBox.critical(
                self.main_window, "Export Error",
                f"Failed to export detection dataset:\n{str(e)}"
            )
            return False

    def _export_detection_dataset(self, folder_name: str, split_result: Dict,
                                  config: Dict, pipeline: Optional[AugmentationPipeline],
                                  aug_config: Optional[Dict], image_format: str = 'png') -> bool:
        """
        Export detection dataset with all files.

        Args:
            folder_name: Output folder name
            split_result: Dict of split_name -> list of keys
            config: Split configuration
            pipeline: Augmentation pipeline (optional)
            aug_config: Augmentation configuration (optional)
            image_format: Image format ('png' or 'jpg', default: 'png')

        Returns:
            bool: True if successful
        """
        # Create output directories
        dataset_dir = os.path.join(self.main_window.output_det_dir, folder_name)
        img_dir = os.path.join(dataset_dir, "img")

        split_dirs = {}
        for split_name in split_result.keys():
            split_dirs[split_name] = os.path.join(img_dir, split_name)
            self._ensure_dir(split_dirs[split_name])

        # Path mapping
        path_map = dict(self.main_window.image_items)
        all_labels = {split_name: [] for split_name in split_result.keys()}

        # Progress dialog
        total_keys = sum(len(v) for v in split_result.values())
        progress = QtWidgets.QProgressDialog(
            "Exporting Detection Dataset...", "Cancel", 0, total_keys, self.main_window
        )
        progress.setWindowTitle("Export Detection Dataset")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        processed = 0
        for split_name, split_keys in split_result.items():
            for key in split_keys:
                progress.setValue(processed)
                progress.setLabelText(f"Processing: {key}\n({processed+1}/{total_keys}) [{split_name}]")
                QtWidgets.QApplication.processEvents()

                if progress.wasCanceled():
                    logger.info("Detection export cancelled by user")
                    progress.close()
                    return False

                img_path = path_map[key]

                # Load image (Unicode-safe, with rotation support)
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
                    if export_utils.is_mask_item(ann)
                ]
                filtered_annotations = [
                    ann for ann in annotations
                    if not export_utils.is_mask_item(ann)
                ]

                # Skip if no annotations (only masks)
                if not filtered_annotations:
                    logger.info(f"Skipping {key}: only mask items, no annotations")
                    processed += 1
                    continue

                bboxes = [ann['points'] for ann in filtered_annotations]

                # Draw mask items on image
                if mask_items:
                    img = export_utils.draw_masks_on_image(img, mask_items)

                # Save image
                clean_key = sanitize_filename(
                    key.replace('.jpg', '').replace('.jpeg', '')
                       .replace('.png', '').replace('.bmp', '')
                       .replace('.jfif', '').replace('.tiff', '').replace('.tif', '')
                       .replace('.webp', '').replace('.gif', '').replace('.ico', '')
                )
                img_filename = f"{clean_key}.{image_format}"
                img_save_path = os.path.join(split_dirs[split_name], img_filename)
                success = imwrite_unicode(img_save_path, img, image_format=image_format)

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
                                # Sanitize augmentation name
                                clean_aug_name = sanitize_filename(aug_name.replace('.', '_'))
                                aug_filename = f"{clean_key}_{clean_aug_name}.{image_format}"
                                aug_save_path = os.path.join(split_dirs[split_name], aug_filename)

                                success = imwrite_unicode(aug_save_path, aug_img, image_format=image_format)

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

        # Show completion message
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

        # Show completion message with option to open folder
        msg_box = QtWidgets.QMessageBox(self.main_window)
        msg_box.setWindowTitle("Save Detection Dataset")
        msg_box.setText("✅ Detection Dataset saved successfully!")
        msg_box.setInformativeText(
            f"📁 Location:\n{dataset_dir}\n\n"
            f"📊 Statistics:\n{stats}\n  • Total: {total_images} images{aug_info}\n\n"
            f"ℹ️ Notes: Mask items are hidden in exported images"
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
                os.startfile(dataset_dir)
            elif sys.platform == 'darwin':
                subprocess.run(['open', dataset_dir])
            else:
                subprocess.run(['xdg-open', dataset_dir])

        logger.info(f"Exported detection dataset to {dataset_dir}")
        return True
