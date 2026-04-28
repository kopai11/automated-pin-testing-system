import os


class ThemeMixin:
    """Mixin: Dark/Light theme stylesheet management."""

    def on_theme_changed(self, theme_name: str):
        self.apply_theme(theme_name)

    def apply_theme(self, theme_name: str):
        self.current_theme = "Dark" if str(theme_name).strip().lower() == "dark" else "Light"
        check_icon = os.path.join(os.path.dirname(os.path.dirname(__file__)), "check_mark_blue.svg")
        check_icon = check_icon.replace("\\", "/")

        if self.current_theme == "Dark":
            app_style = """
                QMainWindow, QWidget {
                    background-color: #1f232a;
                    color: #e6edf3;
                }
                QLabel {
                    color: #e6edf3;
                }
                QGroupBox {
                    border: 1px solid #3d444d;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 8px;
                    background-color: #24292f;
                    color: #e6edf3;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 4px;
                    color: #e6edf3;
                }
                QLineEdit, QPlainTextEdit, QComboBox, QListWidget {
                    background-color: #0d1117;
                    color: #e6edf3;
                    border: 1px solid #3d444d;
                    border-radius: 6px;
                    padding: 4px;
                    selection-background-color: #2f81f7;
                    selection-color: #ffffff;
                }
                QComboBox QAbstractItemView {
                    background-color: #0d1117;
                    color: #e6edf3;
                    border: 1px solid #3d444d;
                    outline: none;
                }
                QComboBox QAbstractItemView::item {
                    background-color: #0d1117;
                    color: #e6edf3;
                    padding: 4px 8px;
                    min-height: 22px;
                }
                QComboBox QAbstractItemView::item:hover {
                    background-color: #30363d;
                    color: #e6edf3;
                }
                QComboBox QAbstractItemView::item:selected {
                    background-color: #2f81f7;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 0px;
                    background: transparent;
                }
                QPushButton {
                    padding: 8px 16px;
                    border-radius: 6px;
                    border: 1px solid #4b5563;
                    background-color: #2f3742;
                    color: #e6edf3;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #39424f;
                    border-color: #7d8590;
                }
                QPushButton:pressed {
                    background-color: #222a33;
                    border-color: #8b949e;
                    padding-top: 9px;
                    padding-bottom: 7px;
                }
                QPushButton:checked {
                    background-color: #2f81f7;
                    border-color: #58a6ff;
                    color: #ffffff;
                }
                QPushButton:disabled {
                    background-color: #2a2f36;
                    color: #8b949e;
                    border-color: #3d444d;
                }
                QFrame#summaryCard {
                    background-color: #0d1117;
                    border: 1px solid #3d444d;
                    border-radius: 14px;
                }
                QLabel#summaryCardTitle {
                    color: #ffffff;
                    font-size: 24px;
                    font-weight: 700;
                }
                QLabel#summaryMetricLabel {
                    color: #c9d1d9;
                    font-size: 18px;
                    font-weight: 600;
                }
                QLabel#summaryMetricValue {
                    color: #f0f6fc;
                    font-size: 34px;
                    font-weight: 700;
                }
                QLabel#summaryMeta {
                    color: #8b949e;
                    font-size: 14px;
                }
                QCheckBox, QRadioButton {
                    color: #e6edf3;
                }
                QCheckBox:hover, QRadioButton:hover {
                    color: #f0f6fc;
                }
                QCheckBox {
                    spacing: 8px;
                }
                QRadioButton {
                    spacing: 8px;
                }
                QCheckBox::indicator, QGroupBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #8b949e;
                    border-radius: 4px;
                    background: #161b22;
                }
                QCheckBox::indicator:checked, QGroupBox::indicator:checked {
                    border: 1px solid #58a6ff;
                    background: #161b22;
                    image: url({CHECK_ICON});
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #8b949e;
                    border-radius: 8px;
                    background: #161b22;
                }
                QRadioButton::indicator:checked {
                    border: 2px solid #58a6ff;
                    border-radius: 8px;
                    background: #2f81f7;
                }
                QWidget#watermarked {
                    background: transparent;
                }
                QScrollArea {
                    background: transparent;
                    border: 0;
                }
            """
        else:
            app_style = """
                QMainWindow, QWidget {
                    background-color: #f6f8fa;
                    color: #1f2328;
                }
                QLabel {
                    color: #1f2328;
                }
                QGroupBox {
                    border: 1px solid #d0d7de;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 8px;
                    background-color: #ffffff;
                    color: #1f2328;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 4px;
                    color: #1f2328;
                }
                QLineEdit, QPlainTextEdit, QComboBox, QListWidget {
                    background-color: #ffffff;
                    color: #1f2328;
                    border: 1px solid #d0d7de;
                    border-radius: 6px;
                    padding: 4px;
                    selection-background-color: #0969da;
                    selection-color: #ffffff;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #1f2328;
                    border: 1px solid #d0d7de;
                    outline: none;
                }
                QComboBox QAbstractItemView::item {
                    background-color: #ffffff;
                    color: #1f2328;
                    padding: 4px 8px;
                    min-height: 22px;
                }
                QComboBox QAbstractItemView::item:hover {
                    background-color: #eaedf0;
                    color: #1f2328;
                }
                QComboBox QAbstractItemView::item:selected {
                    background-color: #0969da;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 0px;
                    background: transparent;
                }
                QPushButton {
                    padding: 8px 16px;
                    border-radius: 6px;
                    border: 1px solid #d0d7de;
                    background-color: #f3f4f6;
                    color: #1f2328;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #e8edf3;
                    border-color: #8c959f;
                }
                QPushButton:pressed {
                    background-color: #d0d7de;
                    border-color: #6e7781;
                    padding-top: 9px;
                    padding-bottom: 7px;
                }
                QPushButton:checked {
                    background-color: #0969da;
                    border-color: #218bff;
                    color: #ffffff;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #8c959f;
                    border-color: #dddddd;
                }
                QFrame#summaryCard {
                    background-color: #ffffff;
                    border: 1px solid #d0d7de;
                    border-radius: 14px;
                }
                QLabel#summaryCardTitle {
                    color: #1f2328;
                    font-size: 24px;
                    font-weight: 700;
                }
                QLabel#summaryMetricLabel {
                    color: #57606a;
                    font-size: 18px;
                    font-weight: 600;
                }
                QLabel#summaryMetricValue {
                    color: #1f2328;
                    font-size: 34px;
                    font-weight: 700;
                }
                QLabel#summaryMeta {
                    color: #6e7781;
                    font-size: 14px;
                }
                QCheckBox, QRadioButton {
                    color: #1f2328;
                }
                QCheckBox:hover, QRadioButton:hover {
                    color: #0f1720;
                }
                QCheckBox {
                    spacing: 8px;
                }
                QRadioButton {
                    spacing: 8px;
                }
                QCheckBox::indicator, QGroupBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid #6e7781;
                    border-radius: 4px;
                    background: #ffffff;
                }
                QCheckBox::indicator:checked, QGroupBox::indicator:checked {
                    border: 1px solid #218bff;
                    background: #ffffff;
                    image: url({CHECK_ICON});
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid #6e7781;
                    border-radius: 8px;
                    background: #ffffff;
                }
                QRadioButton::indicator:checked {
                    border: 2px solid #218bff;
                    border-radius: 8px;
                    background: #0969da;
                }
                QWidget#watermarked {
                    background: transparent;
                }
                QScrollArea {
                    background: transparent;
                    border: 0;
                }
            """

        app_style = app_style.replace("{CHECK_ICON}", check_icon)

        # Inject font-size override if user has set one
        font_sizes = {"Small": 12, "Medium": 14, "Large": 17}
        fs = font_sizes.get(getattr(self, "app_font_size", "Medium"), 14)
        if fs != 14:
            app_style += f"\n* {{ font-size: {fs}px; }}"

        self.setStyleSheet(app_style)

        # Re-apply theme toggle button styles after global stylesheet
        if hasattr(self, "_update_theme_toggle"):
            self._update_theme_toggle()
