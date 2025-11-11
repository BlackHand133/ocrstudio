#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive Test Script for Project Restructure
Tests all new imports and module structure

Run this to verify the restructure is working correctly:
    python test_restructure.py
"""

import sys
import traceback
from typing import List, Tuple

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}[PASS] {text}{Colors.RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}[FAIL] {text}{Colors.RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")

# Test results storage
test_results: List[Tuple[str, bool, str]] = []

def test_import(module_path: str, item_name: str = None, description: str = "") -> bool:
    """
    Test importing a module or item from a module

    Args:
        module_path: Full module path (e.g., "modules.gui.handlers.workspace")
        item_name: Specific item to import (e.g., "WorkspaceHandler")
        description: Human-readable description

    Returns:
        bool: True if import successful, False otherwise
    """
    try:
        if item_name:
            exec(f"from {module_path} import {item_name}")
            test_name = f"{module_path}.{item_name}"
        else:
            exec(f"import {module_path}")
            test_name = module_path

        print_success(f"{description or test_name}")
        test_results.append((test_name, True, ""))
        return True
    except Exception as e:
        error_msg = str(e)
        print_error(f"{description or test_name}")
        print(f"   Error: {error_msg}")
        test_results.append((test_name, False, error_msg))
        return False

def test_handlers():
    """Test all handler imports"""
    print_header("Testing Handler Imports")

    handlers = [
        ("modules.gui.handlers.workspace", "WorkspaceHandler", "Workspace Handler"),
        ("modules.gui.handlers.image", "ImageHandler", "Image Handler"),
        ("modules.gui.handlers.annotation", "AnnotationHandler", "Annotation Handler"),
        ("modules.gui.handlers.detection", "DetectionHandler", "Detection Handler"),
        ("modules.gui.handlers.ui", "UIHandler", "UI Handler"),
        ("modules.gui.handlers.table", "TableHandler", "Table Handler"),
        ("modules.gui.handlers.export", "ExportHandler", "Export Handler"),
        ("modules.gui.handlers.rotation", "RotationHandler", "Rotation Handler"),
    ]

    success_count = 0
    for module_path, class_name, description in handlers:
        if test_import(module_path, class_name, description):
            success_count += 1

    result = "PASSED" if success_count == len(handlers) else "FAILED"
    print(f"\n{Colors.BOLD}Handlers: {success_count}/{len(handlers)} passed [{result}]{Colors.RESET}")
    return success_count == len(handlers)

def test_dialogs():
    """Test all dialog imports"""
    print_header("Testing Dialog Imports")

    dialogs = [
        ("modules.gui.dialogs.workspace_selector_dialog", "WorkspaceSelectorDialog", "Workspace Selector Dialog"),
        ("modules.gui.dialogs.split_config_dialog", "SplitConfigDialog", "Split Config Dialog"),
        ("modules.gui.dialogs.augmentation_dialog", "AugmentationDialog", "Augmentation Dialog"),
        ("modules.gui.dialogs.settings_dialog", "SettingsDialog", "Settings Dialog"),
        ("modules.gui.dialogs.version_manager_dialog", "VersionManagerDialog", "Version Manager Dialog"),
    ]

    success_count = 0
    for module_path, class_name, description in dialogs:
        if test_import(module_path, class_name, description):
            success_count += 1

    result = "PASSED" if success_count == len(dialogs) else "FAILED"
    print(f"\n{Colors.BOLD}Dialogs: {success_count}/{len(dialogs)} passed [{result}]{Colors.RESET}")
    return success_count == len(dialogs)

def test_items():
    """Test all item imports"""
    print_header("Testing Item Imports")

    items = [
        ("modules.gui.items.base_annotation_item", "BaseAnnotationItem", "Base Annotation Item"),
        ("modules.gui.items.box_item", "BoxItem", "Box Item"),
        ("modules.gui.items.polygon_item", "PolygonItem", "Polygon Item"),
        ("modules.gui.items.mask_item", "MaskQuadItem", "Mask Quad Item"),
        ("modules.gui.items.mask_item", "MaskPolygonItem", "Mask Polygon Item"),
    ]

    success_count = 0
    for module_path, class_name, description in items:
        if test_import(module_path, class_name, description):
            success_count += 1

    result = "PASSED" if success_count == len(items) else "FAILED"
    print(f"\n{Colors.BOLD}Items: {success_count}/{len(items)} passed [{result}]{Colors.RESET}")
    return success_count == len(items)

def test_export_modules():
    """Test export module imports"""
    print_header("Testing Export Modules")

    exports = [
        ("modules.export.base", "BaseExporter", "Base Exporter"),
        ("modules.export.detection", "DetectionExporter", "Detection Exporter"),
        ("modules.export.recognition", "RecognitionExporter", "Recognition Exporter"),
        ("modules.export.utils", None, "Export Utils Module"),
        ("modules.export.formats.ppocr", None, "PaddleOCR Format Module"),
    ]

    success_count = 0
    for module_path, class_name, description in exports:
        if test_import(module_path, class_name, description):
            success_count += 1

    result = "PASSED" if success_count == len(exports) else "FAILED"
    print(f"\n{Colors.BOLD}Export Modules: {success_count}/{len(exports)} passed [{result}]{Colors.RESET}")
    return success_count == len(exports)

def test_utils():
    """Test utils package imports"""
    print_header("Testing Utils Package")

    utils = [
        ("modules.utils", "handle_exceptions", "Exception Handler Decorator"),
        ("modules.utils", "imread_unicode", "Unicode Image Read"),
        ("modules.utils", "imwrite_unicode", "Unicode Image Write"),
        ("modules.utils", "sanitize_annotation", "Annotation Sanitizer"),
        ("modules.utils", "sanitize_filename", "Filename Sanitizer"),
        ("modules.utils.decorators", "handle_exceptions", "Decorators Module"),
        ("modules.utils.file_io", "imread_unicode", "File I/O Module"),
        ("modules.utils.image", "clip_points_to_image", "Image Utils Module"),
        ("modules.utils.validation", "sanitize_annotation", "Validation Module"),
    ]

    success_count = 0
    for module_path, func_name, description in utils:
        if test_import(module_path, func_name, description):
            success_count += 1

    result = "PASSED" if success_count == len(utils) else "FAILED"
    print(f"\n{Colors.BOLD}Utils: {success_count}/{len(utils)} passed [{result}]{Colors.RESET}")
    return success_count == len(utils)

def test_core_modules():
    """Test core module imports"""
    print_header("Testing Core Modules")

    core = [
        ("modules.config.manager", "ConfigManager", "Config Manager"),
        ("modules.constants", None, "Constants Module"),
        ("modules.core.ocr.detector", "TextDetector", "Text Detector"),
        ("modules.core.workspace.manager", "WorkspaceManager", "Workspace Manager"),
        ("modules.data.augmentation", "AugmentationPipeline", "Augmentation Pipeline"),
    ]

    success_count = 0
    for module_path, class_name, description in core:
        if test_import(module_path, class_name, description):
            success_count += 1

    result = "PASSED" if success_count == len(core) else "FAILED"
    print(f"\n{Colors.BOLD}Core Modules: {success_count}/{len(core)} passed [{result}]{Colors.RESET}")
    return success_count == len(core)

def test_main_window():
    """Test main window import"""
    print_header("Testing Main Window")

    result = test_import("modules.gui.main_window", "MainWindow", "Main Window Class")

    status = "PASSED" if result else "FAILED"
    print(f"\n{Colors.BOLD}Main Window: [{status}]{Colors.RESET}")
    return result

def test_backward_compatibility():
    """Test that old backward-compatible imports still work"""
    print_header("Testing Backward Compatibility")

    print_info("These old imports should still work for compatibility:")

    compat_tests = [
        ("modules.utils", "handle_exceptions", "Utils backward compatibility"),
        ("modules.utils", "imread_unicode", "File I/O backward compatibility"),
        ("modules.export", "DetectionExporter", "Export backward compatibility"),
    ]

    success_count = 0
    for module_path, item_name, description in compat_tests:
        if test_import(module_path, item_name, description):
            success_count += 1

    result = "PASSED" if success_count == len(compat_tests) else "FAILED"
    print(f"\n{Colors.BOLD}Backward Compatibility: {success_count}/{len(compat_tests)} passed [{result}]{Colors.RESET}")
    return success_count == len(compat_tests)

def print_summary():
    """Print test summary"""
    print_header("Test Summary")

    total_tests = len(test_results)
    passed_tests = sum(1 for _, passed, _ in test_results if passed)
    failed_tests = total_tests - passed_tests

    print(f"{Colors.BOLD}Total Tests: {total_tests}{Colors.RESET}")
    print(f"{Colors.GREEN}Passed: {passed_tests}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed_tests}{Colors.RESET}")

    if failed_tests > 0:
        print(f"\n{Colors.RED}{Colors.BOLD}Failed Tests:{Colors.RESET}")
        for test_name, passed, error in test_results:
            if not passed:
                print(f"{Colors.RED}  [X] {test_name}{Colors.RESET}")
                if error:
                    print(f"     {error}")

    percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"\n{Colors.BOLD}Success Rate: {percentage:.1f}%{Colors.RESET}")

    if percentage == 100:
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD} ALL TESTS PASSED! RESTRUCTURE SUCCESSFUL! {Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}  SOME TESTS FAILED - REVIEW REQUIRED  {Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        return False

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{'Project Restructure - Comprehensive Test Suite':^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{'Version 2.2.0 - Phase 6 & 7 Verification':^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

    # Run all test suites
    all_passed = True

    all_passed &= test_handlers()
    all_passed &= test_dialogs()
    all_passed &= test_items()
    all_passed &= test_export_modules()
    all_passed &= test_utils()
    all_passed &= test_core_modules()
    all_passed &= test_main_window()
    all_passed &= test_backward_compatibility()

    # Print summary
    success = print_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
