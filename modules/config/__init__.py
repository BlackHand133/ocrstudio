"""
Configuration management package.

This package provides a unified configuration system that manages:
- OCR settings (profiles: CPU/GPU)
- Application settings
- Path configurations
- User preferences
"""

from modules.config.manager import ConfigManager

__all__ = ['ConfigManager']
