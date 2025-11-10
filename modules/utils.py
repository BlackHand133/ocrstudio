# modules/utils.py

import logging
import cv2
import numpy as np
from PyQt5 import QtWidgets

def handle_exceptions(func):
    """
    decorator จับ exception ในเมธอด แล้ว log และโชว์ QMessageBox
    """
    logger = logging.getLogger("TextDetGUI")

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # log exception พร้อม traceback
            logger.exception("Exception in %s", func.__qualname__)
            # ถ้ามี QtWidgets ใน args[0], ใช้ parent ของหน้าต่างแสดง dialog
            parent = None
            if args and hasattr(args[0], 'parentWidget'):
                parent = args[0]
            QtWidgets.QMessageBox.critical(
                parent,
                "Error",
                f"เกิดข้อผิดพลาดในฟังก์ชัน {func.__name__}:\n{e}"
            )
    return wrapper


def imread_unicode(filepath: str) -> np.ndarray:
    """
    อ่านภาพโดยรองรับ Unicode path (ภาษาไทย, จีน, ฯลฯ)
    
    Args:
        filepath: path ของไฟล์รูป (รองรับ Unicode)
    
    Returns:
        numpy array ของภาพ หรือ None ถ้าอ่านไม่สำเร็จ
    """
    try:
        # อ่านไฟล์เป็น bytes
        with open(filepath, 'rb') as f:
            file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
        
        # Decode เป็นภาพ
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger = logging.getLogger("TextDetGUI")
        logger.error(f"Failed to read image {filepath}: {e}")
        return None




def clip_points_to_image(points: list, image_width: int, image_height: int) -> list:
    """
    ปรับ points ให้อยู่ภายในขอบเขตของรูปภาพ
    
    Args:
        points: list of [x, y] coordinates
        image_width: ความกว้างของรูปภาพ
        image_height: ความสูงของรูปภาพ
    
    Returns:
        list of clipped [x, y] coordinates
    """
    clipped_points = []
    for point in points:
        x, y = point[0], point[1]
        # Clip ให้อยู่ในช่วง [0, width] และ [0, height]
        x_clipped = max(0, min(x, image_width))
        y_clipped = max(0, min(y, image_height))
        clipped_points.append([x_clipped, y_clipped])
    
    return clipped_points


def imwrite_unicode(filepath: str, img: np.ndarray, params=None) -> bool:
    """
    เขียนภาพโดยรองรับ Unicode path
    
    Args:
        filepath: path ของไฟล์ที่จะบันทึก (รองรับ Unicode)
        img: numpy array ของภาพ
        params: พารามิเตอร์สำหรับ imencode (optional)
    
    Returns:
        True ถ้าสำเร็จ, False ถ้าล้มเหลว
    """
    try:
        # เลือก extension
        ext = filepath.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'bmp']:
            ext = 'jpg'
        
        # Encode ภาพ
        if params is None:
            params = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        
        success, encoded = cv2.imencode(f'.{ext}', img, params)
        
        if not success:
            return False
        
        # เขียนเป็นไฟล์
        with open(filepath, 'wb') as f:
            f.write(encoded.tobytes())
        
        return True
    except Exception as e:
        logger = logging.getLogger("TextDetGUI")
        logger.error(f"Failed to write image {filepath}: {e}")
        return False


def sanitize_annotation(annotation: dict) -> dict:
    """
    แปลง numpy types ใน annotation เป็น Python native types
    เพื่อให้ JSON serializable และจัดการกับ QtWidgets objects
    
    Args:
        annotation: dict ที่อาจมี numpy types หรือ Qt objects
    
    Returns:
        dict ที่มีเฉพาะ Python native types
    """
    def convert_value(val):
        """แปลงค่าเดียว"""
        # ตรวจสอบว่าเป็น QtWidgets object หรือไม่
        # ถ้าเป็น object ที่มี to_dict() method ให้เรียกใช้
        if hasattr(val, 'to_dict') and callable(getattr(val, 'to_dict')):
            return convert_value(val.to_dict())
        elif isinstance(val, (np.integer, np.int32, np.int64)):
            return int(val)
        elif isinstance(val, (np.floating, np.float32, np.float64)):
            return float(val)
        elif isinstance(val, np.ndarray):
            return val.tolist()
        elif isinstance(val, list):
            return [convert_value(v) for v in val]
        elif isinstance(val, dict):
            return {k: convert_value(v) for k, v in val.items()}
        else:
            return val
    
    return convert_value(annotation)


def sanitize_annotations(annotations: list) -> list:
    """
    แปลง numpy types ใน list ของ annotations

    Args:
        annotations: list of annotation dicts

    Returns:
        list of sanitized annotation dicts
    """
    return [sanitize_annotation(ann) for ann in annotations]


def sanitize_filename(filename: str, replacement: str = '_') -> str:
    """
    ทำความสะอาดชื่อไฟล์โดยแทนที่ space และ special characters ด้วย underscore
    เพื่อป้องกันปัญหาใน ML/DL training systems

    Args:
        filename: ชื่อไฟล์ที่ต้องการทำความสะอาด
        replacement: ตัวอักษรที่ใช้แทนที่ (default: '_')

    Returns:
        ชื่อไฟล์ที่ทำความสะอาดแล้ว

    Examples:
        >>> sanitize_filename("my file.jpg")
        "my_file.jpg"
        >>> sanitize_filename("image (1).png")
        "image_1_.png"
        >>> sanitize_filename("test + demo.jpg")
        "test_demo.jpg"
    """
    import re

    # แยกชื่อไฟล์และ extension
    parts = filename.rsplit('.', 1)
    name = parts[0]
    ext = parts[1] if len(parts) > 1 else ''

    # แทนที่ space และ special characters ด้วย replacement
    # รักษาไว้เฉพาะ: ตัวอักษร (a-z, A-Z, ภาษาต่างๆ), ตัวเลข (0-9), underscore (_), hyphen (-)
    # Pattern: แทนที่ทุกอักษรที่ไม่ใช่ word characters (รวมถึง Unicode), ไม่ใช่ hyphen, ไม่ใช่ dot
    name = re.sub(r'[^\w\-]+', replacement, name, flags=re.UNICODE)

    # ลบ underscore ที่ซ้ำกัน (ถ้ามี)
    name = re.sub(r'_+', '_', name)

    # ลบ underscore ที่ต้นและท้าย
    name = name.strip('_')

    # รวมกลับเป็นชื่อไฟล์
    if ext:
        return f"{name}.{ext}"
    else:
        return name