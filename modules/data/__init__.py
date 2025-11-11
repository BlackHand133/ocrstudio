"""
Data processing modules.

This package provides data processing and augmentation functionality:
- AugmentationPipeline: Image augmentation for training data
- DataSplitter: Split datasets into train/val/test
- Writer: Data output and serialization

Usage:
    from modules.data import AugmentationPipeline, DataSplitter

    # Augmentation
    pipeline = AugmentationPipeline()
    augmented = pipeline.apply(image, annotations)

    # Data splitting
    splitter = DataSplitter()
    splits = splitter.split_dataset(data, ratios=(0.7, 0.2, 0.1))
"""

# Note: Imports will be added as needed to avoid circular dependencies
# For now, users should import directly from sub-modules

__all__ = []
