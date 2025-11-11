"""
Base exporter class for all dataset exporters.

This module provides the abstract base class that all exporters should inherit from.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any

from modules.data.splitter import DataSplitter

logger = logging.getLogger("TextDetGUI")


class BaseExporter(ABC):
    """
    Abstract base class for all exporters.

    Provides common functionality for:
    - Data splitting
    - Progress tracking
    - Error handling
    - Metadata management
    """

    def __init__(self, main_window):
        """
        Initialize base exporter.

        Args:
            main_window: Reference to MainWindow instance
        """
        self.main_window = main_window
        self.workspace_handler = getattr(main_window, 'workspace_handler', None)
        self.logger = logger

    @abstractmethod
    def export(self, **kwargs) -> bool:
        """
        Export dataset. Must be implemented by subclasses.

        Returns:
            bool: True if successful
        """
        pass

    def _split_data(self, keys: List, config: Dict) -> Dict[str, List]:
        """
        Split data according to configuration.

        Args:
            keys: List of items to split (image keys or crops)
            config: Split configuration dict

        Returns:
            Dict mapping split_name -> list of items
        """
        splitter = DataSplitter(seed=config.get('seed'))

        # Check if using advanced splitting
        use_density = 'density' in config.get('advanced', {})
        use_curvature = 'curvature' in config.get('advanced', {})

        if use_density or use_curvature:
            # Advanced splitting with stratification
            if use_density:
                density_scores = splitter.analyze_text_density(self.main_window.annotations)
                split_result = splitter.split_by_density_stratified(
                    keys, density_scores,
                    train_pct=config['splits'].get('train', 0),
                    test_pct=config['splits'].get('test', 0),
                    valid_pct=config['splits'].get('valid', 0)
                )
            elif use_curvature:
                curvature_scores = splitter.analyze_text_curvature(self.main_window.annotations)
                split_result = splitter.split_by_density_stratified(
                    keys, curvature_scores,
                    train_pct=config['splits'].get('train', 0),
                    test_pct=config['splits'].get('test', 0),
                    valid_pct=config['splits'].get('valid', 0)
                )
        else:
            # Simple splitting
            if config['method'] == 'percentage':
                split_result = splitter.split_by_percentage(
                    keys,
                    train_pct=config['splits'].get('train', 0),
                    test_pct=config['splits'].get('test', 0),
                    valid_pct=config['splits'].get('valid', 0)
                )
            else:
                split_result = splitter.split_by_count(
                    keys,
                    train_count=config['splits'].get('train', 0),
                    test_count=config['splits'].get('test', 0),
                    valid_count=config['splits'].get('valid', 0)
                )

        return split_result

    def _get_annotations(self, key: str) -> List[Dict]:
        """
        Get annotations for a given image key.

        Args:
            key: Image key

        Returns:
            List of annotation dicts
        """
        return self.main_window.annotations.get(key, [])

    def _ensure_dir(self, path: str) -> bool:
        """
        Ensure directory exists.

        Args:
            path: Directory path

        Returns:
            bool: True if successful
        """
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            return False

    def _log_export_stats(self, export_type: str, stats: Dict[str, Any]):
        """
        Log export statistics.

        Args:
            export_type: Type of export ('detection' or 'recognition')
            stats: Statistics dict
        """
        self.logger.info(f"=== {export_type.title()} Export Stats ===")
        for key, value in stats.items():
            self.logger.info(f"  {key}: {value}")
