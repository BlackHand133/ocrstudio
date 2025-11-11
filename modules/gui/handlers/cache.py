# modules/gui/window_handler/cache_handler.py

import os
import json
import logging
from modules.utils import sanitize_annotations

logger = logging.getLogger("TextDetGUI")


class CacheHandler:
    """
    จัดการการโหลดและบันทึก cache
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference ไปยัง MainWindow instance
        """
        self.main_window = main_window
    
    def load_cache(self):
        """โหลด cache จากไฟล์"""
        cache_path = self.main_window.cache_path
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # โหลด annotations
                self.main_window.annotations = data.get('annotations', {})
                
                # โหลด rotations
                self.main_window.image_rotations = data.get('rotations', {})
                
                logger.info(f"Loaded cache from {cache_path}")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
                self.main_window.annotations = {}
                self.main_window.image_rotations = {}
        else:
            self.main_window.annotations = {}
            self.main_window.image_rotations = {}
    
    def save_cache(self):
        """บันทึก cache ลงไฟล์"""
        cache_path = self.main_window.cache_path
        
        try:
            # Sanitize annotations ก่อน serialize
            sanitized_annotations = {}
            for key, anns in self.main_window.annotations.items():
                sanitized_annotations[key] = sanitize_annotations(anns)
            
            # รวม annotations และ rotations
            cache_data = {
                'annotations': sanitized_annotations,
                'rotations': getattr(self.main_window, 'image_rotations', {})
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved cache to {cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")