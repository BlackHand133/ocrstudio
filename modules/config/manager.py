"""
Unified Configuration Manager.

This module provides a centralized configuration system that combines:
1. Profile-based OCR config (CPU/GPU)
2. Application settings
3. Path configurations
4. User preferences

Usage:
    from modules.config import ConfigManager

    config = ConfigManager.instance()
    device = config.get('ocr.device')
    config.set('app.auto_save', True)
    config.save()
"""

import os
import yaml
import json
import logging
from typing import Any, Dict, Optional, List
from pathlib import Path

from modules.constants import (
    DIR_CONFIG, DIR_DATA, DIR_WORKSPACES, DIR_OUTPUT_DET, DIR_OUTPUT_REC,
    DIR_MODELS, DIR_LOGS, DIR_CACHE, WORKSPACE_VERSION,
    DEFAULT_OCR_LANG, DEFAULT_DET_DB_BOX_THRESH, DEFAULT_DET_DB_UNCLIP_RATIO
)

logger = logging.getLogger("TextDetGUI")


class ConfigManager:
    """
    Unified configuration manager using Singleton pattern.

    Manages all configuration data from multiple sources:
    - config/profiles/*.yaml (OCR profiles)
    - config/paths.yaml (Path configurations)
    - data/app_config.json (Application state)
    - data/recent_workspaces.json (Recent workspaces)
    """

    _instance: Optional['ConfigManager'] = None

    @classmethod
    def instance(cls, root_dir: Optional[str] = None) -> 'ConfigManager':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(root_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton (useful for testing)."""
        cls._instance = None

    def __init__(self, root_dir: Optional[str] = None):
        """
        Initialize ConfigManager.

        Args:
            root_dir: Project root directory (auto-detected if None)
        """
        if root_dir is None:
            # Auto-detect root directory
            this_file = os.path.abspath(__file__)
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(this_file)))

        self.root_dir = root_dir
        self.config_dir = os.path.join(root_dir, DIR_CONFIG)
        self.data_dir = os.path.join(root_dir, DIR_DATA)

        # Config storage
        self._profiles: Dict[str, Dict] = {}
        self._current_profile: str = "cpu"
        self._app_config: Dict = {}
        self._path_config: Dict = {}
        self._recent_workspaces: List[Dict] = []

        # Load all configurations
        self._load_all()

    def _load_all(self):
        """Load all configuration files."""
        self._load_profiles()
        self._load_path_config()
        self._load_app_config()
        self._load_recent_workspaces()

    def _load_profiles(self):
        """Load OCR profile configurations."""
        profiles_dir = os.path.join(self.config_dir, "profiles")

        # Fallback to old config.yaml if profiles don't exist
        old_config = os.path.join(self.config_dir, "config.yaml")
        if os.path.exists(old_config) and not os.path.exists(profiles_dir):
            logger.info("Loading old config.yaml format")
            with open(old_config, 'r', encoding='utf-8') as f:
                old_data = yaml.safe_load(f)
                self._profiles = old_data.get('profiles', {})
                self._current_profile = old_data.get('default_profile', 'cpu')
                return

        # Load new profile-based configs
        if os.path.exists(profiles_dir):
            for profile_file in os.listdir(profiles_dir):
                if profile_file.endswith('.yaml'):
                    profile_name = profile_file[:-5]  # Remove .yaml
                    profile_path = os.path.join(profiles_dir, profile_file)

                    with open(profile_path, 'r', encoding='utf-8') as f:
                        self._profiles[profile_name] = yaml.safe_load(f)

                    logger.debug(f"Loaded profile: {profile_name}")

        # Use fallback if no profiles loaded
        if not self._profiles:
            logger.warning("No profiles found, using fallback")
            self._profiles = self._get_fallback_profiles()

    def _load_path_config(self):
        """Load path configurations."""
        path_config_file = os.path.join(self.config_dir, "paths.yaml")

        if os.path.exists(path_config_file):
            with open(path_config_file, 'r', encoding='utf-8') as f:
                self._path_config = yaml.safe_load(f) or {}
        else:
            logger.warning("paths.yaml not found, using defaults")
            self._path_config = self._get_default_paths()

    def _load_app_config(self):
        """Load application configuration."""
        app_config_file = os.path.join(self.root_dir, "app_config.json")

        if os.path.exists(app_config_file):
            with open(app_config_file, 'r', encoding='utf-8') as f:
                self._app_config = json.load(f)
        else:
            logger.warning("app_config.json not found, using defaults")
            self._app_config = self._get_default_app_config()

    def _load_recent_workspaces(self):
        """Load recent workspaces."""
        recent_file = os.path.join(self.root_dir, "recent_workspaces.json")

        if os.path.exists(recent_file):
            with open(recent_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._recent_workspaces = data.get('workspaces', [])
        else:
            self._recent_workspaces = []

    def _get_fallback_profiles(self) -> Dict[str, Dict]:
        """Get fallback profiles if no config found."""
        return {
            'cpu': {
                'device': {'type': 'cpu'},
                'paddleocr': {
                    'lang': DEFAULT_OCR_LANG,
                    'use_doc_orientation_classify': False,
                    'use_doc_unwarping': False,
                    'use_textline_orientation': False,
                    'device': 'cpu',
                    'det_db_box_thresh': DEFAULT_DET_DB_BOX_THRESH,
                    'det_db_unclip_ratio': DEFAULT_DET_DB_UNCLIP_RATIO
                }
            },
            'gpu': {
                'device': {'type': 'gpu', 'gpu_id': 0, 'gpu_mem': 8000},
                'paddleocr': {
                    'lang': DEFAULT_OCR_LANG,
                    'use_doc_orientation_classify': False,
                    'use_doc_unwarping': False,
                    'use_textline_orientation': True,
                    'device': 'gpu',
                    'det_db_box_thresh': DEFAULT_DET_DB_BOX_THRESH,
                    'det_db_unclip_ratio': DEFAULT_DET_DB_UNCLIP_RATIO
                }
            }
        }

    def _get_default_paths(self) -> Dict[str, str]:
        """Get default path configurations."""
        return {
            'workspaces': os.path.join(self.data_dir, DIR_WORKSPACES),
            'models': os.path.join(self.data_dir, DIR_MODELS),
            'output': os.path.join(self.data_dir, 'output'),
            'output_det': os.path.join(self.data_dir, DIR_OUTPUT_DET),
            'output_rec': os.path.join(self.data_dir, DIR_OUTPUT_REC),
            'logs': os.path.join(self.data_dir, DIR_LOGS),
            'cache': os.path.join(self.data_dir, DIR_CACHE)
        }

    def _get_default_app_config(self) -> Dict:
        """Get default application configuration."""
        return {
            'version': WORKSPACE_VERSION,
            'current_workspace': None,
            'auto_save': True,
            'cache_annotations': True,
            'window': {
                'width': 1400,
                'height': 900
            }
        }

    # ===== Public API =====

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Examples:
            config.get('ocr.device')                  # From current profile
            config.get('app.auto_save')               # From app config
            config.get('paths.workspaces')            # From path config
            config.get('current_workspace')           # From app config root

        Args:
            key: Configuration key (dot-separated)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        parts = key.split('.')

        # Route to appropriate config source
        if parts[0] == 'ocr' or parts[0] == 'profile':
            # OCR/Profile config
            profile = self._profiles.get(self._current_profile, {})
            return self._get_nested(profile, parts[1:], default)

        elif parts[0] == 'app':
            # App config
            return self._get_nested(self._app_config, parts[1:], default)

        elif parts[0] == 'paths':
            # Path config
            return self._get_nested(self._path_config, parts[1:], default)

        else:
            # Try app config root level
            return self._get_nested(self._app_config, parts, default)

    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation.

        Examples:
            config.set('app.auto_save', False)
            config.set('current_workspace', 'my_workspace')

        Args:
            key: Configuration key (dot-separated)
            value: Value to set
        """
        parts = key.split('.')

        if parts[0] == 'app':
            self._set_nested(self._app_config, parts[1:], value)
        elif parts[0] == 'paths':
            self._set_nested(self._path_config, parts[1:], value)
        else:
            # Default to app config
            self._set_nested(self._app_config, parts, value)

    def _get_nested(self, data: Dict, keys: List[str], default: Any) -> Any:
        """Get nested value from dict using key path."""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _set_nested(self, data: Dict, keys: List[str], value: Any):
        """Set nested value in dict using key path."""
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    # ===== Profile Management =====

    def get_current_profile(self) -> str:
        """Get current profile name."""
        return self._current_profile

    def set_current_profile(self, profile_name: str):
        """Set current profile."""
        if profile_name not in self._profiles:
            raise ValueError(f"Profile '{profile_name}' not found")
        self._current_profile = profile_name
        logger.info(f"Switched to profile: {profile_name}")

    def list_profiles(self) -> List[str]:
        """Get list of available profiles."""
        return list(self._profiles.keys())

    def get_profile_config(self, profile_name: Optional[str] = None) -> Dict:
        """
        Get full profile configuration.

        Args:
            profile_name: Profile name (uses current if None)

        Returns:
            Profile configuration dict
        """
        if profile_name is None:
            profile_name = self._current_profile
        return self._profiles.get(profile_name, {})

    def get_paddleocr_params(self, profile_name: Optional[str] = None) -> Dict:
        """
        Get PaddleOCR parameters for specified profile.

        Args:
            profile_name: Profile name (uses current if None)

        Returns:
            Dict of PaddleOCR parameters
        """
        profile = self.get_profile_config(profile_name)
        return profile.get('paddleocr', {})

    # ===== Path Management =====

    def get_path(self, path_key: str) -> str:
        """
        Get configured path.

        Args:
            path_key: Path key (e.g., 'workspaces', 'output_det')

        Returns:
            Absolute path
        """
        return self._path_config.get(path_key, '')

    def ensure_directories(self):
        """Create all configured directories if they don't exist."""
        for path in self._path_config.values():
            os.makedirs(path, exist_ok=True)
        logger.info("Ensured all directories exist")

    # ===== Recent Workspaces =====

    def get_recent_workspaces(self) -> List[Dict]:
        """Get list of recent workspaces."""
        return self._recent_workspaces

    def add_recent_workspace(self, workspace_info: Dict):
        """Add workspace to recent list."""
        # Remove if already exists
        self._recent_workspaces = [
            w for w in self._recent_workspaces
            if w.get('id') != workspace_info.get('id')
        ]
        # Add to front
        self._recent_workspaces.insert(0, workspace_info)
        # Limit to 10 recent workspaces
        self._recent_workspaces = self._recent_workspaces[:10]

    # ===== Save Operations =====

    def save_app_config(self):
        """Save application configuration."""
        app_config_file = os.path.join(self.root_dir, "app_config.json")
        with open(app_config_file, 'w', encoding='utf-8') as f:
            json.dump(self._app_config, f, indent=2, ensure_ascii=False)
        logger.debug("Saved app_config.json")

    def save_recent_workspaces(self):
        """Save recent workspaces."""
        recent_file = os.path.join(self.root_dir, "recent_workspaces.json")
        data = {
            'version': WORKSPACE_VERSION,
            'workspaces': self._recent_workspaces
        }
        with open(recent_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug("Saved recent_workspaces.json")

    def save_all(self):
        """Save all configurations."""
        self.save_app_config()
        self.save_recent_workspaces()
        logger.info("Saved all configurations")


# ===== Convenience Functions =====

def get_config() -> ConfigManager:
    """Get ConfigManager singleton instance."""
    return ConfigManager.instance()
