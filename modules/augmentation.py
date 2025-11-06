# modules/augmentation.py

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from PIL import Image, ImageEnhance, ImageFilter
import random

class ImageAugmentor:
    """
    ระบบ Augmentation สำหรับ Text Detection และ Recognition
    รองรับการปรับ bounding box ตาม geometric transformations
    """
    
    @staticmethod
    def rotate_image(img: np.ndarray, angle: float, 
                     bboxes: Optional[List[List[List[float]]]] = None) -> Tuple[np.ndarray, List]:
        """
        หมุนภาพและปรับ bounding boxes
        """
        h, w = img.shape[:2]
        center = (w / 2, h / 2)
        
        # สร้าง rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # คำนวณขนาดใหม่
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # ปรับ translation
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        # หมุนภาพ
        rotated = cv2.warpAffine(img, M, (new_w, new_h), 
                                 borderMode=cv2.BORDER_REPLICATE)
        
        # ปรับ bboxes
        new_bboxes = []
        if bboxes:
            for bbox in bboxes:
                new_pts = []
                for pt in bbox:
                    # แปลง point ด้วย transformation matrix
                    x, y = pt[0], pt[1]
                    new_x = M[0, 0] * x + M[0, 1] * y + M[0, 2]
                    new_y = M[1, 0] * x + M[1, 1] * y + M[1, 2]
                    new_pts.append([new_x, new_y])
                new_bboxes.append(new_pts)
        
        return rotated, new_bboxes
    
    @staticmethod
    def shear_image(img: np.ndarray, shear_x: float, shear_y: float,
                   bboxes: Optional[List[List[List[float]]]] = None) -> Tuple[np.ndarray, List]:
        """
        Shear/Skew ภาพและปรับ bounding boxes
        """
        h, w = img.shape[:2]
        
        # สร้าง shear matrix
        M = np.float32([
            [1, shear_x, 0],
            [shear_y, 1, 0]
        ])
        
        # คำนวณขนาดใหม่
        new_w = int(w + abs(shear_x * h))
        new_h = int(h + abs(shear_y * w))
        
        # Adjust translation
        if shear_x < 0:
            M[0, 2] = abs(shear_x * h)
        if shear_y < 0:
            M[1, 2] = abs(shear_y * w)
        
        # Shear ภาพ
        sheared = cv2.warpAffine(img, M, (new_w, new_h),
                                borderMode=cv2.BORDER_REPLICATE)
        
        # ปรับ bboxes
        new_bboxes = []
        if bboxes:
            for bbox in bboxes:
                new_pts = []
                for pt in bbox:
                    x, y = pt[0], pt[1]
                    new_x = M[0, 0] * x + M[0, 1] * y + M[0, 2]
                    new_y = M[1, 0] * x + M[1, 1] * y + M[1, 2]
                    new_pts.append([new_x, new_y])
                new_bboxes.append(new_pts)
        
        return sheared, new_bboxes
    
    @staticmethod
    def scale_image(img: np.ndarray, scale_x: float, scale_y: float,
                   bboxes: Optional[List[List[List[float]]]] = None) -> Tuple[np.ndarray, List]:
        """
        ปรับขนาดภาพและ bounding boxes
        """
        h, w = img.shape[:2]
        new_w = int(w * scale_x)
        new_h = int(h * scale_y)
        
        scaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # ปรับ bboxes
        new_bboxes = []
        if bboxes:
            for bbox in bboxes:
                new_pts = [[pt[0] * scale_x, pt[1] * scale_y] for pt in bbox]
                new_bboxes.append(new_pts)
        
        return scaled, new_bboxes
    
    @staticmethod
    def perspective_transform(img: np.ndarray, strength: float = 0.2,
                            bboxes: Optional[List[List[List[float]]]] = None) -> Tuple[np.ndarray, List]:
        """
        Perspective transformation
        """
        h, w = img.shape[:2]
        
        # สร้าง random perspective points
        offset = strength * min(w, h)
        src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst_pts = np.float32([
            [random.uniform(0, offset), random.uniform(0, offset)],
            [w - random.uniform(0, offset), random.uniform(0, offset)],
            [w - random.uniform(0, offset), h - random.uniform(0, offset)],
            [random.uniform(0, offset), h - random.uniform(0, offset)]
        ])
        
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        transformed = cv2.warpPerspective(img, M, (w, h),
                                         borderMode=cv2.BORDER_REPLICATE)
        
        # ปรับ bboxes
        new_bboxes = []
        if bboxes:
            for bbox in bboxes:
                new_pts = []
                for pt in bbox:
                    # Transform point
                    x, y = pt[0], pt[1]
                    pt_homo = np.array([x, y, 1])
                    new_pt = M @ pt_homo
                    new_x = new_pt[0] / new_pt[2]
                    new_y = new_pt[1] / new_pt[2]
                    new_pts.append([new_x, new_y])
                new_bboxes.append(new_pts)
        
        return transformed, new_bboxes
    
    @staticmethod
    def adjust_brightness_contrast(img: np.ndarray, brightness: float = 0.0, 
                                   contrast: float = 1.0) -> np.ndarray:
        """
        ปรับ brightness และ contrast
        brightness: -100 to 100
        contrast: 0.5 to 2.0
        """
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # Brightness
        if brightness != 0:
            factor = 1 + brightness / 100
            enhancer = ImageEnhance.Brightness(img_pil)
            img_pil = enhancer.enhance(factor)
        
        # Contrast
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img_pil)
            img_pil = enhancer.enhance(contrast)
        
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def color_jitter(img: np.ndarray, hue: float = 0.0, 
                    saturation: float = 1.0) -> np.ndarray:
        """
        Color jittering
        hue: -0.5 to 0.5
        saturation: 0.5 to 2.0
        """
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # Saturation
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(img_pil)
            img_pil = enhancer.enhance(saturation)
        
        # Hue (convert to HSV)
        if hue != 0.0:
            img_hsv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2HSV).astype(np.float32)
            img_hsv[:, :, 0] = (img_hsv[:, :, 0] + hue * 180) % 180
            img_pil = Image.fromarray(cv2.cvtColor(img_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB))
        
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def to_grayscale(img: np.ndarray) -> np.ndarray:
        """แปลงเป็นขาวดำ"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    
    @staticmethod
    def gaussian_blur(img: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """Gaussian blur"""
        if kernel_size % 2 == 0:
            kernel_size += 1
        return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
    
    @staticmethod
    def add_noise(img: np.ndarray, noise_type: str = 'gaussian', 
                 intensity: float = 25) -> np.ndarray:
        """
        เพิ่ม noise
        noise_type: 'gaussian' or 'salt_pepper'
        intensity: 0-100
        """
        if noise_type == 'gaussian':
            noise = np.random.randn(*img.shape) * intensity
            noisy = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        elif noise_type == 'salt_pepper':
            noisy = img.copy()
            prob = intensity / 1000
            # Salt
            salt = np.random.random(img.shape[:2]) < prob
            noisy[salt] = 255
            # Pepper
            pepper = np.random.random(img.shape[:2]) < prob
            noisy[pepper] = 0
        else:
            noisy = img
        
        return noisy
    
    @staticmethod
    def random_erasing(img: np.ndarray, prob: float = 0.5, 
                      area_ratio: float = 0.1) -> np.ndarray:
        """
        Random erasing
        prob: ความน่าจะเป็นที่จะ erase
        area_ratio: สัดส่วนพื้นที่ที่จะ erase (0-1)
        """
        if random.random() > prob:
            return img
        
        h, w = img.shape[:2]
        area = h * w * area_ratio
        
        # Random size
        erase_h = int(np.sqrt(area * random.uniform(0.5, 2)))
        erase_w = int(area / erase_h)
        
        if erase_h >= h or erase_w >= w:
            return img
        
        # Random position
        x = random.randint(0, w - erase_w)
        y = random.randint(0, h - erase_h)
        
        # Erase (fill with random color or mean)
        erased = img.copy()
        erased[y:y+erase_h, x:x+erase_w] = np.random.randint(0, 256, 3)
        
        return erased
    
    @staticmethod
    def sharpen(img: np.ndarray, strength: float = 1.0) -> np.ndarray:
        """
        Sharpening
        strength: 0-2
        """
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Sharpness(img_pil)
        sharpened = enhancer.enhance(1 + strength)
        return cv2.cvtColor(np.array(sharpened), cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def random_crop(img: np.ndarray, crop_ratio: float = 0.9) -> np.ndarray:
        """
        Random crop (สำหรับ recognition)
        crop_ratio: สัดส่วนที่เหลือ (0.8-1.0)
        """
        h, w = img.shape[:2]
        new_h = int(h * crop_ratio)
        new_w = int(w * crop_ratio)
        
        if new_h >= h or new_w >= w:
            return img
        
        y = random.randint(0, h - new_h)
        x = random.randint(0, w - new_w)
        
        return img[y:y+new_h, x:x+new_w]


class AugmentationPipeline:
    """
    Pipeline สำหรับจัดการ augmentation หลายตัว
    รองรับ combinatorial และ sequential modes
    """
    
    def __init__(self, mode: str = 'combinatorial'):
        """
        mode: 'combinatorial' (สร้างทุกชุด) หรือ 'sequential' (ใช้พร้อมกัน)
        """
        self.mode = mode
        self.augmentor = ImageAugmentor()
        self.augmentations = []
    
    def add_augmentation(self, aug_type: str, params: dict):
        """เพิ่ม augmentation"""
        self.augmentations.append({'type': aug_type, 'params': params})
    
    def apply(self, img: np.ndarray, bboxes: Optional[List] = None) -> List[Tuple[np.ndarray, List]]:
        """
        Apply augmentations
        Returns: [(aug_img, aug_bboxes), ...]
        """
        if self.mode == 'combinatorial':
            return self._apply_combinatorial(img, bboxes)
        else:
            return self._apply_sequential(img, bboxes)
    
    def _apply_combinatorial(self, img: np.ndarray, bboxes: Optional[List] = None) -> List[Tuple]:
        """สร้างภาพแยกสำหรับแต่ละ augmentation"""
        results = []
        
        for aug in self.augmentations:
            aug_img, aug_bboxes = self._apply_single(img, bboxes, aug['type'], aug['params'])
            results.append((aug_img, aug_bboxes, aug['type']))
        
        return results
    
    def _apply_sequential(self, img: np.ndarray, bboxes: Optional[List] = None) -> List[Tuple]:
        """ใช้ augmentation ทั้งหมดต่อเนื่องบนภาพเดียว"""
        current_img = img.copy()
        current_bboxes = bboxes.copy() if bboxes else None
        aug_names = []
        
        for aug in self.augmentations:
            current_img, current_bboxes = self._apply_single(
                current_img, current_bboxes, aug['type'], aug['params']
            )
            aug_names.append(aug['type'])
        
        combined_name = '+'.join(aug_names)
        return [(current_img, current_bboxes, combined_name)]
    
    def _apply_single(self, img: np.ndarray, bboxes: Optional[List], 
                     aug_type: str, params: dict) -> Tuple[np.ndarray, List]:
        """Apply single augmentation"""
        
        # Geometric (ต้องปรับ bboxes)
        if aug_type == 'rotation':
            return self.augmentor.rotate_image(img, params['angle'], bboxes)
        
        elif aug_type == 'shear':
            return self.augmentor.shear_image(
                img, params.get('shear_x', 0), params.get('shear_y', 0), bboxes
            )
        
        elif aug_type == 'scale':
            return self.augmentor.scale_image(
                img, params.get('scale_x', 1), params.get('scale_y', 1), bboxes
            )
        
        elif aug_type == 'perspective':
            return self.augmentor.perspective_transform(
                img, params.get('strength', 0.2), bboxes
            )
        
        # Color/Intensity (ไม่ต้องปรับ bboxes)
        elif aug_type == 'brightness_contrast':
            aug_img = self.augmentor.adjust_brightness_contrast(
                img, params.get('brightness', 0), params.get('contrast', 1)
            )
            return aug_img, bboxes
        
        elif aug_type == 'color_jitter':
            aug_img = self.augmentor.color_jitter(
                img, params.get('hue', 0), params.get('saturation', 1)
            )
            return aug_img, bboxes
        
        elif aug_type == 'grayscale':
            return self.augmentor.to_grayscale(img), bboxes
        
        elif aug_type == 'blur':
            aug_img = self.augmentor.gaussian_blur(img, params.get('kernel_size', 5))
            return aug_img, bboxes
        
        elif aug_type == 'noise':
            aug_img = self.augmentor.add_noise(
                img, params.get('noise_type', 'gaussian'), params.get('intensity', 25)
            )
            return aug_img, bboxes
        
        elif aug_type == 'random_erasing':
            aug_img = self.augmentor.random_erasing(
                img, params.get('prob', 0.5), params.get('area_ratio', 0.1)
            )
            return aug_img, bboxes
        
        elif aug_type == 'sharpen':
            aug_img = self.augmentor.sharpen(img, params.get('strength', 1))
            return aug_img, bboxes
        
        elif aug_type == 'crop':
            aug_img = self.augmentor.random_crop(img, params.get('crop_ratio', 0.9))
            return aug_img, bboxes  # Note: bboxes ไม่ valid หลัง crop
        
        else:
            return img, bboxes