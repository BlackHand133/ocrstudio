# modules/detector.py
# 
# ⚠️ สำคัญ! ไฟล์นี้แก้ไขแล้วให้ใช้งานกับ config.yaml
# 
# การใช้งาน:
#   detector = TextDetector()  # ← ไม่ส่ง parameters = ใช้ config.yaml
#

import os
import logging
import numpy as np
from typing import Optional, Dict, Any

class TextDetector:
    """
    Text Detector using PaddleOCR 3.0
    รองรับทั้ง Detection และ Recognition
    
    ✅ ใช้งานง่าย - แค่ปรับ config ในไฟล์ config/config.yaml
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
        Initialize PaddleOCR 3.0
        
        วิธีการใช้งาน:
        
        1. ใช้ default (แนะนำ - ง่ายที่สุด):
           detector = TextDetector()
           → ใช้ profile ที่ตั้งไว้ใน config/config.yaml
        
        2. เลือก profile:
           detector = TextDetector(profile="gpu")
           → ใช้ profile "gpu" จาก config
        
        3. ใช้ parameters แบบเดิม (backward compatible):
           detector = TextDetector(lang='th', use_gpu=False)
        
        Args:
            profile: ชื่อ profile (None = ใช้ default จาก config)
            lang: ภาษา (legacy)
            use_gpu: ใช้ GPU หรือไม่ (legacy)
            ocr_version: เวอร์ชัน PP-OCR (legacy)
            det_model_name: ชื่อโมเดล detection (legacy)
            rec_model_name: ชื่อโมเดล recognition (legacy)
        """
        
        # Logger
        self.logger = logging.getLogger("TextDetGUI")
        
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
            f"TextDetector initialized with profile: {self.profile_name} "
            f"(device: {self.config.get('device', 'cpu').upper()})"
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
        โหลด config จากหลายแหล่ง (priority order)
        Returns: (config_dict, profile_name)
        """
        # Priority 1: Legacy parameters
        if any(p is not None for p in [lang, use_gpu, ocr_version, det_model_name, rec_model_name]):
            self.logger.info("Using legacy parameters")
            params = {
                'lang': lang or 'th',
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
        
        # Priority 2: Profile from unified config
        try:
            from modules.config_loader import get_paddleocr_params, get_loader
            
            loader = get_loader()
            
            # ถ้าไม่ระบุ profile ใช้ default จาก config
            if profile is None:
                profile = loader.get_default_profile_name()
                self.logger.info(f"Using default profile from config: {profile}")
            else:
                self.logger.info(f"Using specified profile: {profile}")
            
            # ดึง params จาก config (มี parameters ครบแล้ว)
            params = get_paddleocr_params(profile)
            
            self.logger.debug(f"Loaded params: {params}")
            
            return params, profile
            
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}. Using fallback.")
        
        # Fallback: Hard-coded defaults
        self.logger.warning("Using fallback hard-coded config")
        return {
            'lang': 'th',
            'device': 'cpu',
            'use_doc_orientation_classify': False,
            'use_doc_unwarping': False,
            'use_textline_orientation': False,
        }, 'fallback'
    
    def _setup_device(self):
        """ตั้งค่า device (GPU/CPU)"""
        if self.use_gpu:
            import paddle
            gpu_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
            
            if not gpu_available:
                self.logger.warning(
                    "GPU requested but not available. Falling back to CPU.\n"
                    "   To use CPU permanently, change default_profile to 'cpu' in config/config.yaml"
                )
                self.use_gpu = False
                self.config['device'] = 'cpu'
    
    def _setup_environment(self):
        """ตั้งค่า environment variables"""
        import paddle
        
        # CUDA
        os.environ["CUDA_VISIBLE_DEVICES"] = "0" if self.use_gpu else ""
        
        # Set paddle device
        device_to_set = "gpu" if self.use_gpu else "cpu"
        paddle.set_device(device_to_set)
        
        # Threading
        os.environ['OMP_NUM_THREADS'] = '4'
        os.environ['MKL_NUM_THREADS'] = '4'
        os.environ['KMP_BLOCKTIME'] = '30'
        os.environ['KMP_SETTINGS'] = '1'
    
    def _init_paddleocr(self):
        """สร้าง PaddleOCR instance"""
        from paddleocr import PaddleOCR
        
        try:
            # ส่ง parameters ทั้งหมดให้ PaddleOCR
            self.logger.debug(f"Initializing PaddleOCR with params: {self.config}")
            self.ocr = PaddleOCR(**self.config)
            
            device_used = self.config.get('device', 'cpu')
            self.logger.info(
                f"PaddleOCR initialized: lang={self.config.get('lang', 'th')}, "
                f"device={device_used.upper()}"
            )
            
            if device_used == 'cpu':
                self.logger.info(
                    "Using CPU mode. To use GPU, change default_profile to 'gpu' in config/config.yaml"
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise
    
    def detect(self, img_path: str):
        """
        Single-image inference using PaddleOCR 3.0
        รองรับ Unicode path (ภาษาไทย, จีน, ฯลฯ)
        🆕 Auto-resize รูปขนาดใหญ่เพื่อประหยัด memory และเพิ่มความเร็ว
        
        Args:
            img_path: path ของรูปภาพ
        
        Returns:
            list of dict:
              {
                'points': [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                'transcription': str,
                'difficult': False
              }
              
        Note:
            - Coordinates ที่ return จะอยู่ในระบบของรูปต้นฉบับ (auto-scaled back)
            - รูปต้นฉบับจะไม่ถูกแก้ไข
        """
        try:
            from modules.utils import imread_unicode
            
            # อ่านรูปด้วย imread_unicode (รองรับ Unicode path)
            img = imread_unicode(img_path)
            
            if img is None:
                self.logger.error("Failed to read image: %s", img_path)
                return []
            
            # 🆕 Auto-resize สำหรับรูปขนาดใหญ่
            h, w = img.shape[:2]
            original_size = (w, h)
            max_size = 2500  # ขนาดสูงสุดที่แนะนำ (ปรับได้)
            scale_x, scale_y = 1.0, 1.0
            resized = False
            
            if max(h, w) > max_size:
                # คำนวณขนาดใหม่ (maintain aspect ratio)
                if w > h:
                    new_w = max_size
                    new_h = int(h * (max_size / w))
                else:
                    new_h = max_size
                    new_w = int(w * (max_size / h))
                
                # Resize ด้วย PIL (LANCZOS = คุณภาพดีที่สุด)
                from PIL import Image
                import numpy as np
                
                pil_img = Image.fromarray(img)
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
                img = np.array(pil_img)
                
                # เก็บ scale factors สำหรับแปลง coordinates กลับ
                scale_x = w / new_w
                scale_y = h / new_h
                resized = True
                
                self.logger.info(
                    f"Auto-resized image: {w}×{h} → {new_w}×{new_h} "
                    f"(scale: {scale_x:.3f}×{scale_y:.3f})"
                )
            
            # เรียก PaddleOCR 3.0 predict
            results = self.ocr.predict(img)
            
            if not results or len(results) == 0:
                self.logger.warning("No results from OCR for %s", img_path)
                return []
            
            # แปลง result เป็น format เดิม
            result = results[0]
            items = self._parse_paddleocr3_result(result)
            
            # 🆕 แปลง coordinates กลับเป็นขนาดต้นฉบับ
            if resized and items:
                for item in items:
                    item['points'] = [
                        [x * scale_x, y * scale_y] 
                        for x, y in item['points']
                    ]
                self.logger.debug(
                    f"Scaled {len(items)} boxes back to original size {original_size}"
                )
            
            self.logger.debug("Detected %d text regions in %s", len(items), img_path)
            return items
            
        except Exception as e:
            self.logger.error("Detection failed for %s: %s", img_path, e, exc_info=True)
            return []
    
    def _parse_paddleocr3_result(self, result):
        """แปลง PaddleOCR 3.0 result เป็น format เดิม"""
        items = []
        
        try:
            rec_polys = result.get('rec_polys', None) if isinstance(result, dict) else getattr(result, 'rec_polys', None)
            dt_polys = result.get('dt_polys', None) if isinstance(result, dict) else getattr(result, 'dt_polys', None)
            rec_texts = result.get('rec_texts', []) if isinstance(result, dict) else getattr(result, 'rec_texts', [])
            rec_scores = result.get('rec_scores', []) if isinstance(result, dict) else getattr(result, 'rec_scores', [])
            
            polys = rec_polys if rec_polys is not None and len(rec_polys) > 0 else dt_polys
            
            if polys is None or len(polys) == 0:
                return []
            
            if len(rec_texts) == 0 and len(polys) > 0:
                self.logger.warning(f"Found {len(polys)} polygons but no recognized texts.")
                for i, poly in enumerate(polys):
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
            
            n_boxes = len(polys)
            n_texts = len(rec_texts)
            n = min(n_boxes, n_texts) if n_texts > 0 else n_boxes
            
            for i in range(n):
                poly = polys[i]
                text = rec_texts[i] if i < len(rec_texts) else ""
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                
                if isinstance(poly, np.ndarray):
                    points = poly.tolist()
                else:
                    points = poly
                
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
    
    def detect_batch(self, img_paths: list):
        """
        Batch inference (fallback to single-image)
        
        Args:
            img_paths: list ของ image paths
        
        Returns:
            dict: {img_path: [items], ...}
        """
        outs = {}
        for p in img_paths:
            try:
                outs[p] = self.detect(p)
            except Exception as e:
                self.logger.error(f"Batch detect failed for {p}: {e}")
                outs[p] = []
        return outs
    
    def get_model_info(self):
        """
        ดึงข้อมูลโมเดลที่ใช้
        
        Returns:
            dict: ข้อมูลโมเดล
        """
        info = {
            'version': 'PaddleOCR 3.0',
            'profile': self.profile_name,
            'device': 'GPU' if self.use_gpu else 'CPU',
            'settings': {
                'lang': self.config.get('lang', 'th'),
                'use_doc_orientation_classify': self.config.get('use_doc_orientation_classify', False),
                'use_doc_unwarping': self.config.get('use_doc_unwarping', False),
                'use_textline_orientation': self.config.get('use_textline_orientation', True),
            }
        }
        return info


# ===== Backward Compatibility =====
class OCRDetector(TextDetector):
    """Alias สำหรับ backward compatibility"""
    pass