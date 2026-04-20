from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QMessageBox, QScrollArea, QWidget


def info(parent, title, text):
    QMessageBox.information(parent, title, text)

def warn(parent, title, text):
    QMessageBox.warning(parent, title, text)

def err(parent, title, text):
    QMessageBox.critical(parent, title, text)

def make_scroll(widget: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    return scroll


class WatermarkedWidget(QWidget):
    """Custom widget with 'TEST MAX MANUFACTURING PTE LTD' watermark background."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        """Draw multiple company name watermarks scattered in the background."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        x_spacing = 650
        y_spacing = 450

        x_offset = -150
        y_offset = 0

        y_pos = y_offset
        while y_pos < height + 250:
            x_pos = x_offset
            if ((y_pos - y_offset) // y_spacing) % 2 == 6:
                x_pos += x_spacing // 4

            while x_pos < width + 250:
                painter.save()
                painter.translate(x_pos, y_pos)
                painter.rotate(-45)

                font_testmax = QFont("Arial Black", 75, QFont.Black)
                font_testmax.setLetterSpacing(QFont.AbsoluteSpacing, 3)
                painter.setFont(font_testmax)
                painter.setPen(QColor(237, 85, 69, 12))
                painter.drawText(-200, 0, "TEST MAX")

                font_company = QFont("Arial", 26, QFont.Bold)
                font_company.setLetterSpacing(QFont.AbsoluteSpacing, 2)
                painter.setFont(font_company)
                painter.setPen(QColor(45, 100, 174, 15))
                painter.drawText(-200, 38, "MANUFACTURING PTE LTD")

                painter.restore()

                x_pos += x_spacing

            y_pos += y_spacing
