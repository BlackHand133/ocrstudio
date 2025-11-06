# main.py

import sys
import os
from PyQt5 import QtWidgets
from modules.logger import setup_logging
from modules.gui.main_window import MainWindow

def main():
    # คำนวณ root project
    root = os.path.dirname(os.path.abspath(__file__))
    # ตั้งค่า logging
    setup_logging(root)

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
