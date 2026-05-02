#!/usr/bin/env python
"""
Setup script for Ajan OCR Annotation Tool
Provides backward compatibility with older pip/setuptools versions
"""

from setuptools import setup, find_packages
import os
import re

# Read version from modules/__version__.py (safe regex — avoids exec())
with open(os.path.join("modules", "__version__.py"), encoding="utf-8") as f:
    _version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
version = {"__version__": _version_match.group(1) if _version_match else "0.0.0"}

# Read README for long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="ocrstudio",
    version=version["__version__"],
    description="OCR Annotation Tool with PaddleOCR integration for Thai and multilingual text",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/BlackHand133/ocrstudio",
    packages=find_packages(exclude=["tests", "docs", "back-up", "workspaces"]),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "gpu": [
            "paddlepaddle-gpu>=2.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ajan-ocr=main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Image Recognition",
    ],
    keywords="ocr annotation paddleocr computer-vision thai-ocr dataset-annotation",
    project_urls={
        "Documentation": "https://github.com/BlackHand133/ocrstudio#readme",
        "Bug Tracker": "https://github.com/BlackHand133/ocrstudio/issues",
        "Source Code": "https://github.com/BlackHand133/ocrstudio",
    },
)
