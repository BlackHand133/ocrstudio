# modules/textline_orientation.py
"""
Textline Orientation Classifier
ใช้ PaddlePaddle model เพื่อตรวจจับว่าข้อความกลับหัว (180°) หรือไม่
"""

import os
import cv2
import numpy as np
import logging
from typing import Tuple, Optional

try:
    import paddle
    from paddle import inference
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logging.warning("PaddlePaddle not available. TextlineOrientationClassifier will not work.")


class TextlineOrientationClassifier:
    """
    Classifier สำหรับตรวจจับ orientation ของ text line
    
    โมเดล: PP-LCNet_x1_0_textline_ori
    Input: 80x160 (H x W)
    Output: 0_degree หรือ 180_degree
    """
    
    def __init__(self, model_dir: str = None):
        """
        Initialize classifier
        
        Args:
            model_dir: path ไปยัง folder ที่เก็บโมเดล (inference.pdiparams, inference.pdmodel)
                      ถ้าไม่ระบุ จะใช้ path เริ่มต้น
        """
        self.logger = logging.getLogger("TextDetGUI")
        
        if not PADDLE_AVAILABLE:
            self.logger.error("PaddlePaddle not installed. Cannot use orientation classifier.")
            self.predictor = None
            return
        
        # กำหนด path เริ่มต้น
        if model_dir is None:
            # ค้นหา model_dir จาก root project
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            model_dir = os.path.join(project_root, "models", "textline_orientation")
        
        self.model_dir = model_dir
        
        # ตรวจสอบไฟล์ - รองรับทั้ง .pdmodel และ .json (PIR format)
        self.model_file = os.path.join(model_dir, "inference.pdmodel")
        self.json_file = os.path.join(model_dir, "inference.json")
        self.params_file = os.path.join(model_dir, "inference.pdiparams")

        # เลือกใช้ไฟล์ที่มี: pdmodel > json
        if os.path.exists(self.model_file):
            self.using_format = "pdmodel"
            self.logger.info("Using inference.pdmodel (binary format)")
        elif os.path.exists(self.json_file):
            self.using_format = "json"
            self.logger.info("Using inference.json (PIR format)")
            self.model_file = self.json_file  # ใช้ JSON แทน
        else:
            self.logger.error(f"Model file not found: {self.model_file} or {self.json_file}")
            self.predictor = None
            return

        if not os.path.exists(self.params_file):
            self.logger.error(f"Params file not found: {self.params_file}")
            self.predictor = None
            return
        
        # กำหนดค่า preprocessing (จาก inference.yml)
        self.input_size = (160, 80)  # (W, H)
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape((3, 1, 1))
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape((3, 1, 1))
        self.scale = 1.0 / 255.0
        
        # Label mapping
        self.labels = ['0_degree', '180_degree']
        
        # สร้าง predictor
        self.predictor = self._create_predictor()
        
        if self.predictor:
            self.logger.info(f"TextlineOrientationClassifier loaded from {model_dir}")
    
    def _create_predictor(self):
        """สร้าง PaddlePaddle predictor"""
        try:
            # สร้าง config
            config = inference.Config(self.model_file, self.params_file)
            
            # ตั้งค่า CPU
            config.disable_gpu()
            config.set_cpu_math_library_num_threads(4)
            
            # ปิด optimization ที่อาจทำให้เกิดปัญหา
            config.switch_use_feed_fetch_ops(False)
            config.switch_ir_optim(True)
            
            # สร้าง predictor
            predictor = inference.create_predictor(config)
            
            self.logger.debug("PaddlePaddle predictor created successfully")
            return predictor
            
        except Exception as e:
            self.logger.error(f"Failed to create predictor: {e}", exc_info=True)
            return None
    
    def preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image ตาม inference.yml
        
        Args:
            img: numpy array (BGR format) ของรูปภาพ
            
        Returns:
            numpy array shape (1, 3, 80, 160) พร้อม normalize
        """
        # 1. Resize to 160x80 (W x H)
        img_resized = cv2.resize(img, self.input_size, interpolation=cv2.INTER_LINEAR)
        
        # 2. Convert BGR to RGB
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        
        # 3. Normalize: scale to [0, 1]
        img_float = img_rgb.astype(np.float32) * self.scale
        
        # 4. To CHW (Channel, Height, Width)
        img_chw = img_float.transpose((2, 0, 1))  # (H, W, C) -> (C, H, W)
        
        # 5. Normalize with mean and std
        img_normalized = (img_chw - self.mean) / self.std
        
        # 6. Add batch dimension
        img_batch = np.expand_dims(img_normalized, axis=0)  # (1, C, H, W)
        
        return img_batch.astype(np.float32)
    
    def predict(self, img: np.ndarray) -> Tuple[str, float]:
        """
        Predict orientation ของ text line
        
        Args:
            img: numpy array (BGR format) ของรูป crop text line
            
        Returns:
            tuple: (label, confidence)
                - label: '0_degree' หรือ '180_degree'
                - confidence: ค่าความมั่นใจ (0-1)
        """
        if self.predictor is None:
            self.logger.warning("Predictor not available, returning default")
            return '0_degree', 0.5
        
        try:
            # Preprocess
            input_data = self.preprocess(img)
            
            # Get input/output handles
            input_names = self.predictor.get_input_names()
            input_handle = self.predictor.get_input_handle(input_names[0])
            
            output_names = self.predictor.get_output_names()
            output_handle = self.predictor.get_output_handle(output_names[0])
            
            # Set input
            input_handle.copy_from_cpu(input_data)
            
            # Run inference
            self.predictor.run()
            
            # Get output
            output = output_handle.copy_to_cpu()
            
            # Process output (softmax + argmax)
            # output shape: (1, 2) หรือ (1, 1, 2)
            output = output.squeeze()  # remove batch dimension
            
            if len(output.shape) == 0:
                # scalar output
                pred_idx = 0
                confidence = 0.5
            else:
                # Softmax
                exp_scores = np.exp(output - np.max(output))
                probs = exp_scores / np.sum(exp_scores)
                
                # Argmax
                pred_idx = np.argmax(probs)
                confidence = float(probs[pred_idx])
            
            label = self.labels[pred_idx]
            
            self.logger.debug(f"Orientation prediction: {label} (confidence: {confidence:.3f})")
            
            return label, confidence
            
        except Exception as e:
            self.logger.error(f"Orientation prediction failed: {e}", exc_info=True)
            return '0_degree', 0.5
    
    def should_flip_180(self, img: np.ndarray, confidence_threshold: float = 0.6) -> bool:
        """
        ตรวจสอบว่าควรหมุน 180° หรือไม่
        
        Args:
            img: numpy array (BGR format) ของรูป crop text line
            confidence_threshold: threshold สำหรับตัดสินใจ (default: 0.6)
            
        Returns:
            bool: True ถ้าควรหมุน 180°
        """
        label, confidence = self.predict(img)
        
        # ถ้าความมั่นใจต่ำเกินไป ไม่หมุน
        if confidence < confidence_threshold:
            self.logger.debug(f"Confidence too low ({confidence:.3f}), not flipping")
            return False
        
        # ถ้า label เป็น 180_degree = ควรหมุน
        should_flip = (label == '180_degree')
        
        self.logger.debug(f"Should flip 180: {should_flip} (label: {label}, conf: {confidence:.3f})")
        
        return should_flip


# ===== Helper Function =====

def create_orientation_classifier(model_dir: Optional[str] = None) -> Optional[TextlineOrientationClassifier]:
    """
    สร้าง TextlineOrientationClassifier instance
    
    Args:
        model_dir: path ไปยัง model directory (optional)
        
    Returns:
        TextlineOrientationClassifier instance หรือ None ถ้าล้มเหลว
    """
    try:
        classifier = TextlineOrientationClassifier(model_dir=model_dir)
        if classifier.predictor is None:
            return None
        return classifier
    except Exception as e:
        logging.error(f"Failed to create orientation classifier: {e}")
        return None