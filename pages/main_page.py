from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QPushButton


class MainPageMixin:
    """Mixin: Main landing page with Engineer / Operator buttons."""

    def build_main_page(self):
        layout = QVBoxLayout(self.main_page)
        layout.setAlignment(Qt.AlignCenter)

        btn_row = QVBoxLayout()
        btn_row.setSpacing(12)

        btn_engineer = QPushButton("⚙️ Engineer Section")
        btn_operator = QPushButton("👤 Operating Section")

        for b in (btn_engineer, btn_operator):
            b.setMinimumHeight(150)
            b.setStyleSheet("font-size: 50px; padding: 10px;")
            btn_row.addWidget(b)

        layout.addLayout(btn_row)

        btn_operator.clicked.connect(lambda: self.tabs.setCurrentWidget(self.page_operator))
        btn_engineer.clicked.connect(self.request_engineer_access)
