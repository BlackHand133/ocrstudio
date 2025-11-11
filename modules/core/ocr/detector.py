"""
Text Detector using PaddleOCR 3.0

This module provides text detection and recognition capabilities using PaddleOCR.
Supports both CPU and GPU modes with profile-based configuration.

Usage:
    from modules.core.ocr import TextDetector

    # Use default profile (from config)
    detector = TextDetector()

    # Use specific profile
    detector = TextDetector(profile="gpu")

    # Detect text
    results = detector.detect("path/to/image.jpg")
"""

import os
import logging
import numpy as np
from typing import Optional, Dict, Any, List
from PIL import Image

from modules.constants import DEFAULT_OCR_LANG

logger = logging.getLogger("TextDetGUI")


class TextDetector:
    """
    Text Detector using PaddleOCR 3.0

    Supports both detection and recognition with automatic image resizing
    for large images to improve performance and memory usage.
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        # Legacy parameters (for backward compatibility)
        lang: Optional[str] = None,
        use_gpu: Optional[bool] = None,
        ocr_version: Optional[str] = None,
        det_model_name: Optional[str] = None,
        rec_model_name: Optional[str] = None
    ) -> None:
        """
        Initialize PaddleOCR detector.

        Args:
            profile: Profile name (None = use default from config)
            lang: Language (legacy parameter)
            use_gpu: Use GPU or not (legacy parameter)
            ocr_version: PP-OCR version (legacy parameter)
            det_model_name: Detection model name (legacy parameter)
            rec_model_name: Recognition model name (legacy parameter)

        Examples:
            # Default (uses ConfigManager)
            detector = TextDetector()

            # Specific profile
            detector = TextDetector(profile="gpu")

            # Legacy parameters
            detector = TextDetector(lang='th', use_gpu=False)
        """

        self.logger = logger

        # ===== 1. Load Configuration =====
        self.config, self.profile_name = self._load_config(
            profile, lang, use_gpu, ocr_version, det_model_name, rec_model_name
        )

        # ===== 2. Setup Device =====
        device_type = self.config.get('device', 'cpu')
        self.use_gpu = (device_type == 'gpu')

        self._setup_device()

        # ===== 3. Setup Environment =====
        self._setup_environment()

        # ===== 4. Initialize PaddleOCR =====
        self._init_paddleocr()

        # Log summary
        self.logger.info(
            f"TextDetector initialized: profile={self.profile_name}, "
            f"device={self.config.get('device', 'cpu').upper()}"
        )

    def _load_config(
        self,
        profile: Optional[str],
        lang: Optional[str],
        use_gpu: Optional[bool],
        ocr_version: Optional[str],
        det_model_name: Optional[str],
        rec_model_name: Optional[str]
    ) -> tuple:
        """
        Load configuration from various sources (priority order).

        Returns:
            tuple: (config_dict, profile_name)
        """
        # Priority 1: Legacy parameters (for backward compatibility)
        if any(p is not None for p in [lang, use_gpu, ocr_version, det_model_name, rec_model_name]):
            self.logger.info("Using legacy parameters")
            params = {
                'lang': lang or DEFAULT_OCR_LANG,
                'device': 'gpu' if use_gpu else 'cpu',
                'use_doc_orientation_classify': False,
                'use_doc_unwarping': False,
                'use_textline_orientation': False,
            }

            if ocr_version:
                params['ocr_version'] = ocr_version
            if det_model_name:
                params['text_detection_model_name'] = det_model_name
            if rec_model_name:
                params['text_recognition_model_name'] = rec_model_name

            return params, 'legacy'

        # Priority 2: New ConfigManager
        try:
            from modules.config import ConfigManager

            config = ConfigManager.instance()

            # If no profile specified, use current profile
            if profile is None:
                profile = config.get_current_profile()
                self.logger.info(f"Using current profile: {profile}")
            else:
                self.logger.info(f"Using specified profile: {profile}")
                config.set_current_profile(profile)

            # Get PaddleOCR parameters from profile
            params = config.get_paddleocr_params(profile)

            self.logger.debug(f"Loaded params from ConfigManager: {params}")

            return params, profile

        except Exception as e:
            self.logger.warning(f"ConfigManager not available: {e}")

        # Priority 3: Fallback to old config_loader (for transition period)
        try:
            from modules.config_loader import get_paddleocr_params, get_loader

            loader = get_loader()

            if profile is None:
                profile = loader.get_default_profile_name()
                self.logger.info(f"Using default profile from old config: {profile}")
            else:
                self.logger.info(f"Using specified profile from old config: {profile}")

            params = get_paddleocr_params(profile)

            self.logger.debug(f"Loaded params from old config_loader: {params}")

            return params, profile

        except Exception as e:
            self.logger.warning(f"Failed to load from old config_loader: {e}")

        # Fallback: Hard-coded defaults
        self.logger.warning("Using fallback hard-coded config")
        return {
            'lang': DEFAULT_OCR_LANG,
            'device': 'cpu',
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
            'use_textline_orientation': False,
        }, 'fallback'

    def _setup_device(self):
        """Setup device (GPU/CPU)."""
        if self.use_gpu:
            import paddle
            gpu_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0

            if not gpu_available:
                self.logger.warning(
                    "GPU requested but not available. Falling back to CPU.\n"
                    "   To use CPU permanently, set default_profile to 'cpu' in config"
                )
                self.use_gpu = False
                self.config['device'] = 'cpu'

    def _setup_environment(self):
        """Setup environment variables for optimal performance."""
        import paddle

        # CUDA
        os.environ["CUDA_VISIBLE_DEVICES"] = "0" if self.use_gpu else ""

        # Set paddle device
        device_to_set = "gpu" if self.use_gpu else "cpu"
        paddle.set_device(device_to_set)

        # Threading optimization
        os.environ['OMP_NUM_THREADS'] = '4'
        os.environ['MKL_NUM_THREADS'] = '4'
        os.environ['KMP_BLOCKTIME'] = '30'
        os.environ['KMP_SETTINGS'] = '1'

    def _init_paddleocr(self):
        """Initialize PaddleOCR instance."""
        from paddleocr import PaddleOCR

        try:
            self.logger.debug(f"Initializing PaddleOCR with params: {self.config}")
            self.ocr = PaddleOCR(**self.config)

            device_used = self.config.get('device', 'cpu')
            self.logger.info(
                f"PaddleOCR initialized: lang={self.config.get('lang', DEFAULT_OCR_LANG)}, "
                f"device={device_used.upper()}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def detect(self, img_path: str) -> List[Dict[str, Any]]:
        """
        Detect and recognize text in an image.

        Supports Unicode paths (Thai, Chinese, etc.) and automatically
        resizes large images for better performance.

        Args:
            img_path: Path to image file

        Returns:
            List of detected text boxes:
            [
                {
                    'points': [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                    'transcription': str,
                    'difficult': False,
                    'score': float
                },
                ...
            ]

        Note:
            - Coordinates are in original image coordinate system
            - Original image is not modified
        """
        try:
            from modules.utils import imread_unicode

            # Read image with Unicode support
            img = imread_unicode(img_path)

            if img is None:
                self.logger.error(f"Failed to read image: {img_path}")
                return []

            # Auto-resize for large images
            h, w = img.shape[:2]
            original_size = (w, h)
            max_size = 2500  # Maximum recommended size
            scale_x, scale_y = 1.0, 1.0
            resized = False

            if max(h, w) > max_size:
                # Calculate new size (maintain aspect ratio)
                if w > h:
                    new_w = max_size
                    new_h = int(h * (max_size / w))
                else:
                    new_h = max_size
                    new_w = int(w * (max_size / h))

                # Resize with PIL (LANCZOS = best quality)
                pil_img = Image.fromarray(img)
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                img = np.array(pil_img)

                # Save scale factors for coordinate conversion
                scale_x = w / new_w
                scale_y = h / new_h
                resized = True

                self.logger.info(
                    f"Auto-resized image: {w}×{h} → {new_w}×{new_h} "
                    f"(scale: {scale_x:.3f}×{scale_y:.3f})"
                )

            # Run PaddleOCR predict
            results = self.ocr.predict(img)

            if not results or len(results) == 0:
                self.logger.warning(f"No results from OCR for {img_path}")
                return []

            # Parse results
            result = results[0]
            items = self._parse_paddleocr3_result(result)

            # Scale coordinates back to original size
            if resized and items:
                for item in items:
                    item['points'] = [
                        [x * scale_x, y * scale_y]
                        for x, y in item['points']
                    ]
                self.logger.debug(
                    f"Scaled {len(items)} boxes back to original size {original_size}"
                )

            self.logger.debug(f"Detected {len(items)} text regions in {img_path}")
            return items

        except Exception as e:
            self.logger.error(f"Detection failed for {img_path}: {e}", exc_info=True)
            return []

    def _parse_paddleocr3_result(self, result) -> List[Dict[str, Any]]:
        """
        Parse PaddleOCR 3.0 result to standard format.

        Args:
            result: PaddleOCR result object

        Returns:
            List of parsed items
        """
        items = []

        try:
            # Extract data from result (handles both dict and object)
            rec_polys = result.get('rec_polys', None) if isinstance(result, dict) else getattr(result, 'rec_polys', None)
            dt_polys = result.get('dt_polys', None) if isinstance(result, dict) else getattr(result, 'dt_polys', None)
            rec_texts = result.get('rec_texts', []) if isinstance(result, dict) else getattr(result, 'rec_texts', [])
            rec_scores = result.get('rec_scores', []) if isinstance(result, dict) else getattr(result, 'rec_scores', [])

            # Use rec_polys if available, otherwise use dt_polys
            polys = rec_polys if rec_polys is not None and len(rec_polys) > 0 else dt_polys

            if polys is None or len(polys) == 0:
                return []

            # Handle detection-only case (no recognition)
            if len(rec_texts) == 0 and len(polys) > 0:
                self.logger.warning(f"Found {len(polys)} polygons but no recognized texts")
                for poly in polys:
                    if isinstance(poly, np.ndarray):
                        points = poly.tolist()
                    else:
                        points = poly

                    if len(points) >= 4:
                        items.append({
                            'points': points,
                            'transcription': '',
                            'difficult': False,
                            'score': 0.0
                        })
                return items

            # Parse results with both polygons and texts
            n_boxes = len(polys)
            n_texts = len(rec_texts)
            n = min(n_boxes, n_texts) if n_texts > 0 else n_boxes

            for i in range(n):
                poly = polys[i]
                text = rec_texts[i] if i < len(rec_texts) else ""
                score = rec_scores[i] if i < len(rec_scores) else 0.0

                # Convert polygon to list
                if isinstance(poly, np.ndarray):
                    points = poly.tolist()
                else:
                    points = poly

                # Skip invalid polygons
                if len(points) < 4:
                    continue

                item = {
                    'points': points,
                    'transcription': text.strip(),
                    'difficult': False,
                    'score': float(score)
                }

                items.append(item)

            return items

        except Exception as e:
            self.logger.error(f"Failed to parse PaddleOCR 3.0 result: {e}", exc_info=True)
            return []

    def detect_batch(self, img_paths: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch inference (currently implemented as sequential processing).

        Args:
            img_paths: List of image paths

        Returns:
            Dict mapping image path to detected items
        """
        outs = {}
        for p in img_paths:
            try:
                outs[p] = self.detect(p)
            except Exception as e:
                self.logger.error(f"Batch detect failed for {p}: {e}")
                outs[p] = []
        return outs

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get current model information.

        Returns:
            Dict with model info
        """
        info = {
            'version': 'PaddleOCR 3.0',
            'profile': self.profile_name,
            'device': 'GPU' if self.use_gpu else 'CPU',
            'settings': {
                'lang': self.config.get('lang', DEFAULT_OCR_LANG),
                'use_doc_orientation_classify': self.config.get('use_doc_orientation_classify', False),
                'use_doc_unwarping': self.config.get('use_doc_unwarping', False),
                'use_textline_orientation': self.config.get('use_textline_orientation', False),
            }
        }
        return info


# ===== Backward Compatibility =====
class OCRDetector(TextDetector):
    """Alias for backward compatibility."""
    pass
