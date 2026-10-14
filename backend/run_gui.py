#!/usr/bin/env python3
"""Launch Conway's Game of Life — PyQt5 desktop edition."""
import os
import sys

# Suppress noisy font enumeration warnings from custom/third-party Windows fonts
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.warning=false;qt.qpa.fonts=false")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from app.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
