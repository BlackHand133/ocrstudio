"""
Decorator utilities.

This module provides useful decorators:
- Exception handling
- Logging
- Performance monitoring
"""

import logging
from PyQt5 import QtWidgets


def handle_exceptions(func):
    """
    Decorator to catch exceptions and show error dialog.

    This decorator:
    1. Catches all exceptions
    2. Logs with full traceback
    3. Shows QMessageBox with error message

    Args:
        func: Function to wrap

    Returns:
        Wrapped function

    Usage:
        @handle_exceptions
        def my_function(self):
            # Your code here
            pass
    """
    logger = logging.getLogger("TextDetGUI")

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log exception with traceback
            logger.exception("Exception in %s", func.__qualname__)

            # Find parent widget for dialog
            parent = None
            if args and hasattr(args[0], 'parentWidget'):
                parent = args[0]

            # Show error dialog
            QtWidgets.QMessageBox.critical(
                parent,
                "Error",
                f"เกิดข้อผิดพลาดในฟังก์ชัน {func.__name__}:\n{e}"
            )

    return wrapper
