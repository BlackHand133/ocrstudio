"""
GUI annotation items package.

This package contains graphic items for annotations:
- BaseAnnotationItem: Abstract base class
- BoxItem: Bounding box annotation
- PolygonItem: Polygon annotation
- MaskItem: Mask annotation

Usage:
    from modules.gui.items.box_item import BoxItem
    from modules.gui.items.polygon_item import PolygonItem
    from modules.gui.items.mask_item import MaskItem
"""

__all__ = [
    'base_annotation_item',
    'box_item',
    'polygon_item',
    'mask_item',
]
