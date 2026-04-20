import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    default_font = QFont()
    default_font.setPointSize(13)
    default_font.setWeight(QFont.DemiBold)
    app.setFont(default_font)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
