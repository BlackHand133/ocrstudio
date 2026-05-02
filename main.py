# main.py

import sys
import os
from PyQt5 import QtWidgets
from modules.logger import setup_logging
from modules.gui.main_window import MainWindow


def main():
    root = os.path.dirname(os.path.abspath(__file__))

    # Determine log level from config (falls back to INFO if config unavailable)
    try:
        from modules.config import ConfigManager
        _config = ConfigManager.instance(root)
        _log_level = _config.get("logging.level", "INFO")
        _log_format = _config.get("logging.format", None)
    except Exception:
        _log_level = "INFO"
        _log_format = None

    setup_logging(root, level=_log_level, log_format=_log_format)

    # Validate config and log any issues
    try:
        ConfigManager.instance().validate()
    except Exception:
        pass  # Never block startup on validation errors

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
