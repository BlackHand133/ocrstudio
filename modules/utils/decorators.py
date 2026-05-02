"""
Decorator utilities.

This module provides useful decorators:
- Exception handling
- Logging
- Performance monitoring
"""

import logging


def handle_exceptions(func):
    """
    Decorator to catch exceptions and show error dialog.

    This decorator:
    1. Catches all exceptions
    2. Logs with full traceback
    3. Shows QMessageBox with error message (only when Qt is available)

    Qt is imported lazily inside the wrapper so that utility modules using
    this decorator can be imported in Qt-free test environments.

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
            # Log exception with full traceback
            logger.exception("Exception in %s", func.__qualname__)

            # Show error dialog only when Qt is available
            try:
                from PyQt5 import QtWidgets  # lazy import — Qt-free tests stay clean

                # Find parent widget for dialog
                parent = None
                if args and hasattr(args[0], 'parentWidget'):
                    parent = args[0]

                QtWidgets.QMessageBox.critical(
                    parent,
                    "Error",
                    f"เกิดข้อผิดพลาดในฟังก์ชัน {func.__name__}:\n{e}"
                )
            except ImportError:
                pass  # No Qt available (e.g., headless CI / unit tests)

    return wrapper
