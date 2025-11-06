# modules/config_loader.py

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("TextDetGUI")


class ConfigLoader:
    """
    โหลดและจัดการ unified configuration
    ใช้ profile-based config ในไฟล์เดียว
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Args:
            config_file: path ไปยัง config.yaml (default: project_root/config/config.yaml)
        """
        if config_file is None:
            # Auto-detect config file
            this_file = os.path.abspath(__file__)
            # config_loader.py อยู่ใน modules/ ดังนั้นต้อง dirname 2 ครั้ง
            project_root = os.path.dirname(os.path.dirname(this_file))
            config_file = os.path.join(project_root, "config", "config.yaml")
        
        self.config_file = config_file
        self._config = None  # Cache
        self._load_config()
    
    def _load_config(self):
        """โหลด config file"""
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file not found: {self.config_file}")
            self._config = self._get_fallback_config()
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            logger.info(f"Loaded config from: {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._config = self._get_fallback_config()
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Fallback config ถ้าไฟล์หาย"""
        logger.warning("Using fallback config")
        return {
            'default_profile': 'cpu',
            'profiles': {
                'cpu': {
                    'device': {'type': 'cpu'},
                    'paddleocr': {
                        'lang': 'th',
                        'use_doc_orientation_classify': False,
                        'use_doc_unwarping': False,
                        'use_textline_orientation': False,
                        'device': 'cpu'
                    }
                }
            }
        }
    
    def get_profile(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        ดึง profile config
        
        Args:
            profile_name: ชื่อ profile (None = ใช้ default)
        
        Returns:
            dict ของ profile config
        """
        if profile_name is None:
            profile_name = self._config.get('default_profile', 'cpu')
        
        profiles = self._config.get('profiles', {})
        
        if profile_name not in profiles:
            logger.warning(f"Profile '{profile_name}' not found. Using default.")
            profile_name = self._config.get('default_profile', 'cpu')
        
        if profile_name not in profiles:
            logger.error(f"Default profile '{profile_name}' also not found!")
            return self._get_fallback_config()['profiles']['cpu']
        
        return profiles[profile_name]
    
    def list_profiles(self) -> list:
        """แสดงรายการ profiles ทั้งหมด"""
        profiles = self._config.get('profiles', {})
        return list(profiles.keys())
    
    def get_default_profile_name(self) -> str:
        """ดึงชื่อ default profile"""
        return self._config.get('default_profile', 'cpu')
    
    def set_default_profile(self, profile_name: str):
        """เปลี่ยน default profile"""
        profiles = self._config.get('profiles', {})
        
        if profile_name not in profiles:
            raise ValueError(f"Profile '{profile_name}' not found. Available: {list(profiles.keys())}")
        
        self._config['default_profile'] = profile_name
        logger.info(f"Default profile changed to: {profile_name}")
    
    def save(self):
        """บันทึก config กลับไปยังไฟล์"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._config, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"Config saved to: {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def get_paddleocr_params(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        แปลง profile config เป็น parameters สำหรับ PaddleOCR()
        
        Args:
            profile_name: ชื่อ profile (None = ใช้ default)
        
        Returns:
            dict ของ parameters พร้อมใช้กับ PaddleOCR(**params)
        
        Examples:
            >>> loader = ConfigLoader()
            >>> params = loader.get_paddleocr_params()
            >>> ocr = PaddleOCR(**params)
        """
        profile = self.get_profile(profile_name)
        
        # ดึง paddleocr config โดยตรง (มี parameters ครบแล้ว)
        paddleocr_config = profile.get('paddleocr', {})
        
        # คัดลอก parameters ทั้งหมด
        params = paddleocr_config.copy()
        
        logger.debug(f"Generated PaddleOCR params for profile '{profile_name or 'default'}': {params}")
        return params
    
    def get_app_settings(self) -> Dict[str, Any]:
        """ดึง application settings"""
        return self._config.get('app', {})


# ===== Convenience Functions =====

_default_loader = None


def get_loader() -> ConfigLoader:
    """Get default ConfigLoader instance (singleton)"""
    global _default_loader
    if _default_loader is None:
        _default_loader = ConfigLoader()
    return _default_loader


def get_profile(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick access to get profile
    
    Examples:
        >>> config = get_profile()  # default profile
        >>> config = get_profile("gpu")
    """
    return get_loader().get_profile(profile_name)


def get_paddleocr_params(profile_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick access to get PaddleOCR params
    
    Examples:
        >>> params = get_paddleocr_params()  # default profile
        >>> params = get_paddleocr_params("gpu")
        >>> ocr = PaddleOCR(**params)
    """
    return get_loader().get_paddleocr_params(profile_name)


def list_profiles() -> list:
    """
    Quick access to list profiles
    
    Examples:
        >>> profiles = list_profiles()
        >>> print(profiles)  # ['cpu', 'gpu']
    """
    return get_loader().list_profiles()


def get_default_profile() -> str:
    """
    Quick access to get default profile name
    
    Examples:
        >>> default = get_default_profile()
        >>> print(default)  # 'cpu'
    """
    return get_loader().get_default_profile_name()


def set_default_profile(profile_name: str):
    """
    Quick access to set default profile
    
    Examples:
        >>> set_default_profile("gpu")
        >>> get_loader().save()  # บันทึกการเปลี่ยนแปลง
    """
    loader = get_loader()
    loader.set_default_profile(profile_name)
    # Note: ต้องเรียก loader.save() เพื่อบันทึกถาวร