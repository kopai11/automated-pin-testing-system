import json
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QCheckBox, QGroupBox, QFileDialog, QInputDialog,
    QMessageBox, QSizePolicy, QWidget, QScrollArea,
)

# Settings file lives next to the package root (one level up from pages/)
_APP_SETTINGS_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "app_settings.json")
)

_DEFAULTS = {
    "current_theme": "Dark",
    "app_font_size": "Medium",
    "graph_refresh_interval": 5,
    "graph_line_thickness": "Medium",
    "serial_auto_scroll": True,
    "serial_timestamp_lines": False,
    "test_data_filepath": r"C:\Users\HDD 205\Desktop\Pogo_Pin Quality_Test_ Data",
    "report_data_filepath": r"C:\Users\HDD 205\Desktop\Pogo_Pin Quality_Test_ Data\Report",
    "procedure_filepath": r"C:\Users\HDD 205\Desktop\Pogo_Pin Quality_Test_ Data\Test Procedure",
    "export_format": "CSV",
}


class AppSettingsPageMixin:
    """Mixin: App Settings page – theme, font, display, graph, serial, data & export."""

    # ---- Persistence helpers ----
    @staticmethod
    def _load_app_settings_from_disk() -> dict:
        try:
            if os.path.isfile(_APP_SETTINGS_FILE):
                with open(_APP_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_app_settings_to_disk(self):
        data = {
            "current_theme": self.current_theme,
            "app_font_size": self.app_font_size,
            "graph_refresh_interval": self.graph_refresh_interval,
            "graph_line_thickness": self.graph_line_thickness,
            "serial_auto_scroll": self.serial_auto_scroll,
            "serial_timestamp_lines": self.serial_timestamp_lines,
            "test_data_filepath": self.test_data_filepath,
            "report_data_filepath": self.report_data_filepath,
            "procedure_filepath": self.procedure_filepath,
            "export_format": self.export_format,
        }
        try:
            with open(_APP_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ---- Init: load from disk, then fill gaps with defaults ----
    def _init_app_settings(self):
        saved = self._load_app_settings_from_disk()

        # Backward compatibility: migrate old key names if present.
        if "test_data_filepath" not in saved and "default_save_folder" in saved:
            saved["test_data_filepath"] = saved.get("default_save_folder")
        if "report_data_filepath" not in saved and "report_save_folder" in saved:
            saved["report_data_filepath"] = saved.get("report_save_folder")
        if "procedure_filepath" not in saved:
            base = saved.get("test_data_filepath") or _DEFAULTS["test_data_filepath"]
            saved["procedure_filepath"] = os.path.join(base, "Test Procedure")

        for key, default_val in _DEFAULTS.items():
            setattr(self, key, saved.get(key, default_val))

        # Runtime aliases for existing code that may still reference old names.
        self.default_save_folder = self.test_data_filepath
        self.report_save_folder = self.report_data_filepath

    # ---- Theme ----
    def _set_theme(self, theme_name: str):
        self.on_theme_changed(theme_name)
        self._update_theme_toggle()
        self._save_app_settings_to_disk()

    def _update_theme_toggle(self):
        if not hasattr(self, "_btn_theme_light"):
            return
        is_dark = self.current_theme == "Dark"
        self._btn_theme_light.setChecked(not is_dark)
        self._btn_theme_dark.setChecked(is_dark)

        active = (
            "background-color: #0969da; color: #ffffff; font-weight: 700; "
            "border: 1px solid #0969da; border-radius: 8px; font-size: 14px; "
            "padding: 6px 18px;"
        )
        if is_dark:
            inactive = (
                "background-color: #30363d; color: #8b949e; font-weight: 600; "
                "border: 1px solid #3d444d; border-radius: 8px; font-size: 14px; "
                "padding: 6px 18px;"
            )
        else:
            inactive = (
                "background-color: #f3f4f6; color: #57606a; font-weight: 600; "
                "border: 1px solid #d0d7de; border-radius: 8px; font-size: 14px; "
                "padding: 6px 18px;"
            )

        self._btn_theme_light.setStyleSheet(active if not is_dark else inactive)
        self._btn_theme_dark.setStyleSheet(active if is_dark else inactive)

    # ---- Font size ----
    def _apply_font_size(self, size_name: str):
        self.app_font_size = size_name
        self.apply_theme(self.current_theme)

    def _on_font_size_changed(self, text: str):
        self._apply_font_size(text)
        self._save_app_settings_to_disk()

    # ---- Full screen ----
    def _toggle_fullscreen(self, checked: bool):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    # ---- Graph auto-refresh interval ----
    def _on_refresh_interval_changed(self, text: str):
        mapping = {"1 sec": 1, "3 sec": 3, "5 sec": 5, "10 sec": 10}
        self.graph_refresh_interval = mapping.get(text, 5)
        if hasattr(self, "graph_update_timer") and self.graph_update_timer is not None:
            self.graph_update_timer.setInterval(self.graph_refresh_interval * 1000)
        self._save_app_settings_to_disk()

    # ---- Graph line thickness ----
    def _on_line_thickness_changed(self, text: str):
        self.graph_line_thickness = text
        self._save_app_settings_to_disk()

    def _get_line_width(self) -> float:
        return {"Thin": 1.8, "Medium": 2.2, "Thick": 4}.get(
            self.graph_line_thickness, 1.8
        )

    # ---- Serial auto-scroll ----
    def _on_auto_scroll_changed(self, checked: bool):
        self.serial_auto_scroll = checked
        self._save_app_settings_to_disk()

    # ---- Serial timestamp ----
    def _on_timestamp_lines_changed(self, checked: bool):
        self.serial_timestamp_lines = checked
        self._save_app_settings_to_disk()

    # ---- Send step command to controller ----
    def _send_step_command(self):
        step = self.ed_step.text().strip()
        if not step.isdigit():
            QMessageBox.warning(self, "Invalid", "Please enter a valid step number.")
            return
        try:
            cmd = f"STEP:{step}\n"
            self.serial_worker.write(cmd.encode("utf-8"))
            self.serial_log.appendPlainText(f"SENT: STEP:{step}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Couldn't send command: {e}")

    # ---- Default save folder (password-protected) ----
    def _check_settings_password(self) -> bool:
        if getattr(self, '_settings_authenticated', False):
            elapsed = time.time() - getattr(self, '_settings_auth_time', 0)
            if elapsed < 60:
                return True
            self._settings_authenticated = False
        attempts = 0
        while True:
            text, ok = QInputDialog.getText(
                self, "Engineer Access",
                "🔐 Password Access Required",
                QLineEdit.Password
            )
            if not ok:
                return False
            if (text or "").strip() == "88888888":
                self._settings_authenticated = True
                self._settings_auth_time = time.time()
                return True
            attempts += 1
            QMessageBox.warning(self, "Wrong Password", "Password is wrong. Please try again or press Cancel.")
            if attempts >= 5:
                QMessageBox.information(self, "Password Hint", "Hint: Password is Eight*8")

    def _secure_browse_test_data_folder(self):
        if not self._check_settings_password():
            return
        self._unlock_data_controls()
        self._browse_test_data_folder()

    def _secure_browse_report_folder(self):
        if not self._check_settings_password():
            return
        self._unlock_data_controls()
        self._browse_report_folder()

    def _unlock_data_controls(self):
        if hasattr(self, "ed_save_folder"):
            self.ed_save_folder.setEnabled(True)
        if hasattr(self, "ed_procedure_folder"):
            self.ed_procedure_folder.setEnabled(True)
        if hasattr(self, "cmb_export_format"):
            self.cmb_export_format.setEnabled(True)
            try:
                self.cmb_export_format.currentTextChanged.disconnect(self._on_export_format_changed)
            except Exception:
                pass
            self.cmb_export_format.currentTextChanged.connect(self._on_export_format_changed)
        if hasattr(self, "ed_report_folder"):
            self.ed_report_folder.setEnabled(True)
        if hasattr(self, "btn_browse_folder"):
            self.btn_browse_folder.setText("📂 Browse")
        if hasattr(self, "btn_browse_report_folder"):
            self.btn_browse_report_folder.setText("📂 Browse")
        if hasattr(self, "btn_browse_procedure_folder"):
            self.btn_browse_procedure_folder.setText("📂 Browse")
        QTimer.singleShot(60000, self._lock_data_controls)

    def _lock_data_controls(self):
        self._settings_authenticated = False
        if hasattr(self, "ed_save_folder"):
            self.ed_save_folder.setEnabled(False)
        if hasattr(self, "ed_procedure_folder"):
            self.ed_procedure_folder.setEnabled(False)
        if hasattr(self, "cmb_export_format"):
            try:
                self.cmb_export_format.currentTextChanged.disconnect(self._on_export_format_changed)
            except Exception:
                pass
            self.cmb_export_format.setEnabled(False)
        if hasattr(self, "ed_report_folder"):
            self.ed_report_folder.setEnabled(False)
        if hasattr(self, "btn_browse_folder"):
            self.btn_browse_folder.setText("🔒 Browse")
        if hasattr(self, "btn_browse_report_folder"):
            self.btn_browse_report_folder.setText("🔒 Browse")
        if hasattr(self, "btn_browse_procedure_folder"):
            self.btn_browse_procedure_folder.setText("🔒 Browse")

    def _browse_test_data_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Test Data Filepath", self.test_data_filepath
        )
        if folder:
            self.test_data_filepath = folder
            self.default_save_folder = folder
            if hasattr(self, "ed_save_folder"):
                self.ed_save_folder.setText(folder)
            self._save_app_settings_to_disk()

    def _secure_browse_procedure_folder(self):
        if not self._check_settings_password():
            return
        self._unlock_data_controls()
        self._browse_procedure_folder()

    def _browse_procedure_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Procedure Filepath", self.procedure_filepath
        )
        if folder:
            self.procedure_filepath = folder
            if hasattr(self, "ed_procedure_folder"):
                self.ed_procedure_folder.setText(folder)
            self._save_app_settings_to_disk()

    def _browse_report_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Report Data Filepath", self.report_data_filepath
        )
        if folder:
            self.report_data_filepath = folder
            self.report_save_folder = folder
            if hasattr(self, "ed_report_folder"):
                self.ed_report_folder.setText(folder)
            self._save_app_settings_to_disk()

    # ---- Export format ----
    def _on_export_format_changed(self, text: str):
        self.export_format = text
        self._save_app_settings_to_disk()

    # ---- Always on top ----
    def _toggle_always_on_top(self, checked: bool):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    # ---- Reset window size ----
    def _reset_window_size(self):
        self.showNormal()
        self.resize(1200, 800)
        if hasattr(self, "chk_fullscreen"):
            self.chk_fullscreen.setChecked(False)

    # -------------------------
    # Build App Settings Page UI
    # -------------------------
    def build_app_settings_page(self):
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(20, 20, 20, 20)
        outer_layout.setSpacing(16)

        title = QLabel("⚙️ App Settings")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        outer_layout.addWidget(title)

        cols = QHBoxLayout()
        cols.setSpacing(24)
        outer_layout.addLayout(cols)

        left = QWidget()
        right = QWidget()
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        cols.addWidget(left, 1)
        cols.addWidget(right, 1)

        left_l = QVBoxLayout(left)
        left_l.setSpacing(12)
        right_l = QVBoxLayout(right)
        right_l.setSpacing(12)

        # ===================== LEFT: Display & UI =====================

        gb_theme = QGroupBox("🎨 Theme")
        theme_lay = QHBoxLayout(gb_theme)
        theme_lay.setContentsMargins(12, 12, 12, 12)
        self._btn_theme_light = QPushButton("☀️ Light")
        self._btn_theme_dark = QPushButton("🌙 Dark")
        for btn in (self._btn_theme_light, self._btn_theme_dark):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(100)
        self._btn_theme_light.clicked.connect(lambda: self._set_theme("Light"))
        self._btn_theme_dark.clicked.connect(lambda: self._set_theme("Dark"))
        theme_lay.addWidget(self._btn_theme_light)
        theme_lay.addWidget(self._btn_theme_dark)
        theme_lay.addStretch(1)
        left_l.addWidget(gb_theme)

        gb_font = QGroupBox("🔤 Font Size")
        font_lay = QHBoxLayout(gb_font)
        font_lay.setContentsMargins(12, 12, 12, 12)
        self.cmb_font_size = QComboBox()
        self.cmb_font_size.addItems(["Small", "Medium", "Large"])
        self.cmb_font_size.setCurrentText(self.app_font_size)
        self.cmb_font_size.currentTextChanged.connect(self._on_font_size_changed)
        font_lay.addWidget(QLabel("Size:"))
        font_lay.addWidget(self.cmb_font_size)
        font_lay.addStretch(1)
        left_l.addWidget(gb_font)

        gb_fullscreen = QGroupBox("🖥️ Display")
        fs_lay = QVBoxLayout(gb_fullscreen)
        fs_lay.setContentsMargins(12, 12, 12, 12)
        self.chk_fullscreen = QCheckBox("Full Screen")
        self.chk_fullscreen.setChecked(self.isFullScreen())
        self.chk_fullscreen.toggled.connect(self._toggle_fullscreen)
        fs_lay.addWidget(self.chk_fullscreen)
        self.chk_always_on_top = QCheckBox("Always on Top")
        self.chk_always_on_top.setChecked(
            bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
        )
        self.chk_always_on_top.toggled.connect(self._toggle_always_on_top)
        fs_lay.addWidget(self.chk_always_on_top)
        self.btn_reset_window = QPushButton("🔄 Reset Window Size")
        self.btn_reset_window.clicked.connect(self._reset_window_size)
        fs_lay.addWidget(self.btn_reset_window)
        left_l.addWidget(gb_fullscreen)

        # ===================== RIGHT: Graph & Serial & Data =====================

        gb_graph_s = QGroupBox("📊 Graph Settings")
        gs_lay = QGridLayout(gb_graph_s)
        gs_lay.setContentsMargins(12, 12, 12, 12)

        gs_lay.addWidget(QLabel("Auto-refresh Interval:"), 0, 0)
        self.cmb_refresh_interval = QComboBox()
        self.cmb_refresh_interval.addItems(["1 sec", "3 sec", "5 sec", "10 sec"])
        self.cmb_refresh_interval.setCurrentText(f"{self.graph_refresh_interval} sec")
        self.cmb_refresh_interval.currentTextChanged.connect(self._on_refresh_interval_changed)
        gs_lay.addWidget(self.cmb_refresh_interval, 0, 1)

        gs_lay.addWidget(QLabel("Line Thickness:"), 1, 0)
        self.cmb_line_thickness = QComboBox()
        self.cmb_line_thickness.addItems(["Thin", "Medium", "Thick"])
        self.cmb_line_thickness.setCurrentText(self.graph_line_thickness)
        self.cmb_line_thickness.currentTextChanged.connect(self._on_line_thickness_changed)
        gs_lay.addWidget(self.cmb_line_thickness, 1, 1)
        right_l.addWidget(gb_graph_s)

        gb_serial = QGroupBox("📡 Serial Monitor")
        ser_lay = QVBoxLayout(gb_serial)
        ser_lay.setContentsMargins(12, 12, 12, 12)
        self.chk_serial_auto_scroll = QCheckBox("Auto-scroll")
        self.chk_serial_auto_scroll.setChecked(self.serial_auto_scroll)
        self.chk_serial_auto_scroll.toggled.connect(self._on_auto_scroll_changed)
        ser_lay.addWidget(self.chk_serial_auto_scroll)
        self.chk_timestamp_lines = QCheckBox("Timestamp each line")
        self.chk_timestamp_lines.setChecked(self.serial_timestamp_lines)
        self.chk_timestamp_lines.toggled.connect(self._on_timestamp_lines_changed)
        ser_lay.addWidget(self.chk_timestamp_lines)

        # Step command to controller
        step_row = QHBoxLayout()
        step_row.addWidget(QLabel("Step:"))
        self.ed_step = QLineEdit()
        self.ed_step.setPlaceholderText("e.g. 3")
        step_row.addWidget(self.ed_step, 1)
        self.btn_send_step = QPushButton("Set Step")
        step_row.addWidget(self.btn_send_step)
        ser_lay.addLayout(step_row)

        self.btn_send_step.clicked.connect(self._send_step_command)
        self.ed_step.returnPressed.connect(self._send_step_command)

        right_l.addWidget(gb_serial)

        gb_data = QGroupBox("💾 Data & Export")
        data_lay = QGridLayout(gb_data)
        data_lay.setContentsMargins(12, 12, 12, 12)

        data_lay.addWidget(QLabel("Test_data_filepath:"), 0, 0)
        self.ed_save_folder = QLineEdit(self.test_data_filepath)
        self.ed_save_folder.setReadOnly(True)
        self.ed_save_folder.setEnabled(False)
        data_lay.addWidget(self.ed_save_folder, 0, 1)
        self.btn_browse_folder = QPushButton("🔒 Browse")
        self.btn_browse_folder.clicked.connect(self._secure_browse_test_data_folder)
        data_lay.addWidget(self.btn_browse_folder, 0, 2)

        data_lay.addWidget(QLabel("Report_data_filepath:"), 1, 0)
        self.ed_report_folder = QLineEdit(self.report_data_filepath)
        self.ed_report_folder.setReadOnly(True)
        self.ed_report_folder.setEnabled(False)
        data_lay.addWidget(self.ed_report_folder, 1, 1)
        self.btn_browse_report_folder = QPushButton("🔒 Browse")
        self.btn_browse_report_folder.clicked.connect(self._secure_browse_report_folder)
        data_lay.addWidget(self.btn_browse_report_folder, 1, 2)

        data_lay.addWidget(QLabel("Procedure_filepath:"), 2, 0)
        self.ed_procedure_folder = QLineEdit(self.procedure_filepath)
        self.ed_procedure_folder.setReadOnly(True)
        self.ed_procedure_folder.setEnabled(False)
        data_lay.addWidget(self.ed_procedure_folder, 2, 1)
        self.btn_browse_procedure_folder = QPushButton("🔒 Browse")
        self.btn_browse_procedure_folder.clicked.connect(self._secure_browse_procedure_folder)
        data_lay.addWidget(self.btn_browse_procedure_folder, 2, 2)

        data_lay.addWidget(QLabel("Export Format:"), 3, 0)
        self.cmb_export_format = QComboBox()
        self.cmb_export_format.addItems(["CSV", "TXT"])
        self.cmb_export_format.setCurrentText(self.export_format)
        self.cmb_export_format.setEnabled(False)
        data_lay.addWidget(self.cmb_export_format, 3, 1)
        right_l.addWidget(gb_data)

        left_l.addStretch(1)
        right_l.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(outer)
        scroll.setStyleSheet("background: transparent;")

        page_layout = QVBoxLayout(self.page_app_settings)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        # Sync theme buttons after build
        self._update_theme_toggle()
