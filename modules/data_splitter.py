# modules/data_splitter.py

import random
import math
from typing import List, Dict, Tuple, Optional
import numpy as np

class DataSplitter:
    """
    ระบบแบ่งข้อมูลอัจฉริยะ
    รองรับ train/test/valid แบบยืดหยุ่น
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    
    # ===== Detection Analysis =====
    
    @staticmethod
    def analyze_text_density(annotations: Dict) -> Dict[str, float]:
        """
        วิเคราะห์ความหนาแน่นของข้อความ (จำนวน bbox ต่อรูป)
        Returns: {image_key: bbox_count}
        """
        density = {}
        for key, anns in annotations.items():
            if anns:
                density[key] = len(anns)
        return density
    
    @staticmethod
    def analyze_text_curvature(annotations: Dict) -> Dict[str, float]:
        """
        วิเคราะห์ความโค้ง/เอียงของข้อความ
        คำนวณจาก deviation ของจุดจากเส้นตรง
        Returns: {image_key: avg_curvature_score}
        """
        curvature = {}
        
        for key, anns in annotations.items():
            if not anns:
                continue
            
            scores = []
            for ann in anns:
                pts = ann.get('points', [])
                if len(pts) < 4:
                    continue
                
                # คำนวณ deviation จากเส้นตรงระหว่างจุดแรกและจุดสุดท้าย
                if len(pts) == 4:
                    # Quad: คำนวณมุม
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    width = max(x_coords) - min(x_coords)
                    height = max(y_coords) - min(y_coords)
                    
                    # Aspect ratio และ skew
                    if width > 0:
                        angle = math.atan2(height, width)
                        scores.append(abs(angle))
                else:
                    # Polygon: คำนวณ curvature จาก deviation
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    
                    # Fit เส้นตรง
                    if len(x_coords) >= 2:
                        coeffs = np.polyfit(x_coords, y_coords, 1)
                        fitted = np.polyval(coeffs, x_coords)
                        deviation = np.std(np.array(y_coords) - fitted)
                        scores.append(deviation)
            
            curvature[key] = np.mean(scores) if scores else 0.0
        
        return curvature
    
    # ===== Recognition Analysis =====
    
    @staticmethod
    def analyze_text_length(annotations: Dict) -> Dict[str, List[int]]:
        """
        วิเคราะห์ความยาวของข้อความ
        Returns: {image_key: [lengths...]}
        """
        lengths = {}
        
        for key, anns in annotations.items():
            if not anns:
                continue
            
            key_lengths = []
            for ann in anns:
                text = ann.get('transcription', '').strip()
                if text and text != '<no_label>':
                    key_lengths.append(len(text))
            
            if key_lengths:
                lengths[key] = key_lengths
        
        return lengths
    
    # ===== Splitting Methods =====
    
    def split_by_percentage(
        self,
        items: List,
        train_pct: float = 0.0,
        test_pct: float = 0.0,
        valid_pct: float = 0.0
    ) -> Dict[str, List]:
        """
        แบ่งข้อมูลตามเปอร์เซ็นต์
        """
        total = train_pct + test_pct + valid_pct
        if total <= 0 or total > 100:
            raise ValueError("Total percentage must be > 0 and <= 100")
        
        # Shuffle
        shuffled = items.copy()
        random.shuffle(shuffled)
        
        n = len(shuffled)
        
        # คำนวณจำนวน
        n_train = round(n * train_pct / 100)
        n_test = round(n * test_pct / 100)
        n_valid = n - n_train - n_test  # ที่เหลือไป valid
        
        result = {}
        idx = 0
        
        if train_pct > 0:
            result['train'] = shuffled[idx:idx+n_train]
            idx += n_train
        
        if test_pct > 0:
            result['test'] = shuffled[idx:idx+n_test]
            idx += n_test
        
        if valid_pct > 0:
            result['valid'] = shuffled[idx:]
        
        return result
    
    def split_by_count(
        self,
        items: List,
        train_count: int = 0,
        test_count: int = 0,
        valid_count: int = 0
    ) -> Dict[str, List]:
        """
        แบ่งข้อมูลตามจำนวนตายตัว
        """
        total_needed = train_count + test_count + valid_count
        
        if total_needed <= 0:
            raise ValueError("Total count must be > 0")
        
        if total_needed > len(items):
            raise ValueError(
                f"Not enough data! Need {total_needed} items but only have {len(items)}"
            )
        
        # Shuffle
        shuffled = items.copy()
        random.shuffle(shuffled)
        
        result = {}
        idx = 0
        
        if train_count > 0:
            result['train'] = shuffled[idx:idx+train_count]
            idx += train_count
        
        if test_count > 0:
            result['test'] = shuffled[idx:idx+test_count]
            idx += test_count
        
        if valid_count > 0:
            result['valid'] = shuffled[idx:idx+valid_count]
        
        return result
    
    def split_by_density_stratified(
        self,
        items: List,
        density_scores: Dict,
        train_pct: float = 0.0,
        test_pct: float = 0.0,
        valid_pct: float = 0.0,
        n_bins: int = 3
    ) -> Dict[str, List]:
        """
        แบ่งข้อมูลตามความหนาแน่น (stratified)
        แต่ละ bin จะถูกแบ่งตามสัดส่วนเดียวกัน
        """
        # แบ่ง items เป็น bins ตาม density
        densities = [density_scores.get(item, 0) for item in items]
        percentiles = np.percentile(densities, np.linspace(0, 100, n_bins + 1))
        
        bins = [[] for _ in range(n_bins)]
        for item in items:
            d = density_scores.get(item, 0)
            for i in range(n_bins):
                if percentiles[i] <= d < percentiles[i + 1] or (i == n_bins - 1 and d == percentiles[-1]):
                    bins[i].append(item)
                    break
        
        # แบ่งแต่ละ bin ตามสัดส่วน
        result = {'train': [], 'test': [], 'valid': []}
        
        for bin_items in bins:
            split = self.split_by_percentage(bin_items, train_pct, test_pct, valid_pct)
            for key, values in split.items():
                result[key].extend(values)
        
        # ลบ key ที่ว่าง
        return {k: v for k, v in result.items() if v}
    
    def split_by_length_stratified(
        self,
        items: List,
        length_data: Dict[str, List[int]],
        train_pct: float = 0.0,
        test_pct: float = 0.0,
        valid_pct: float = 0.0,
        n_bins: int = 3
    ) -> Dict[str, List]:
        """
        แบ่งข้อมูลตามความยาวข้อความ (stratified)
        ใช้ความยาวเฉลี่ยของแต่ละรูป
        """
        # คำนวณความยาวเฉลี่ย
        avg_lengths = {}
        for item in items:
            if item in length_data and length_data[item]:
                avg_lengths[item] = np.mean(length_data[item])
            else:
                avg_lengths[item] = 0
        
        # แบ่งเป็น bins
        lengths = [avg_lengths[item] for item in items]
        percentiles = np.percentile(lengths, np.linspace(0, 100, n_bins + 1))
        
        bins = [[] for _ in range(n_bins)]
        for item in items:
            length = avg_lengths[item]
            for i in range(n_bins):
                if percentiles[i] <= length < percentiles[i + 1] or (i == n_bins - 1 and length == percentiles[-1]):
                    bins[i].append(item)
                    break
        
        # แบ่งแต่ละ bin
        result = {'train': [], 'test': [], 'valid': []}
        
        for bin_items in bins:
            split = self.split_by_percentage(bin_items, train_pct, test_pct, valid_pct)
            for key, values in split.items():
                result[key].extend(values)
        
        return {k: v for k, v in result.items() if v}