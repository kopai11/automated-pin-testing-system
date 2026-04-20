class ThemeMixin:
    """Mixin: Dark/Light theme stylesheet management."""

    def on_theme_changed(self, theme_name: str):
        self.apply_theme(theme_name)

    def apply_theme(self, theme_name: str):
        self.current_theme = "Dark" if str(theme_name).strip().lower() == "dark" else "Light"

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
                    border: 1px solid #3d444d;
                    background-color: #30363d;
                    color: #e6edf3;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3d444d;
                    border-color: #6e7681;
                }
                QPushButton:pressed {
                    background-color: #24292f;
                    border-color: #8b949e;
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
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #eaedf0;
                    border-color: #8c959f;
                }
                QPushButton:pressed {
                    background-color: #d8dee4;
                    border-color: #6e7781;
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
                QWidget#watermarked {
                    background: transparent;
                }
                QScrollArea {
                    background: transparent;
                    border: 0;
                }
            """

        # Inject font-size override if user has set one
        font_sizes = {"Small": 12, "Medium": 14, "Large": 17}
        fs = font_sizes.get(getattr(self, "app_font_size", "Medium"), 14)
        if fs != 14:
            app_style += f"\n* {{ font-size: {fs}px; }}"

        self.setStyleSheet(app_style)

        # Re-apply theme toggle button styles after global stylesheet
        if hasattr(self, "_update_theme_toggle"):
            self._update_theme_toggle()
