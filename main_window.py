import os
from datetime import datetime
from collections import defaultdict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit,
)

from .core.helpers import WatermarkedWidget
from .core.theme import ThemeMixin
from .core.navigation import NavigationMixin
from .core.auth import AuthMixin
from .core.config_manager import ConfigMixin

from .UI_Pages.main_page import MainPageMixin
from .UI_Pages.operator_page import OperatorPageMixin
from .UI_Pages.engineer_page import EngineerPageMixin
from .UI_Pages.graph_page import GraphPageMixin
from .UI_Pages.summary_page import SummaryPageMixin
from .UI_Pages.spc_chart_page import SPCChartPageMixin
from .UI_Pages.yield_page import YieldPageMixin
from .UI_Pages.app_settings_page import AppSettingsPageMixin


class MainWindow(
    QMainWindow,
    ThemeMixin,
    NavigationMixin,
    AuthMixin,
    MainPageMixin,
    OperatorPageMixin,
    EngineerPageMixin,
    GraphPageMixin,
    SummaryPageMixin,
    SPCChartPageMixin,
    YieldPageMixin,
    AppSettingsPageMixin,
    ConfigMixin,
):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pogo Pin Analysis App")
        icon_path = os.path.join(os.path.dirname(__file__), "pogo_pin_icon.svg")
        self.setWindowIcon(QIcon(icon_path))
        self.resize(1200, 800)

        # Theme state (default light mode)
        self.current_theme = "Light"

        # Initialize app settings defaults
        self._init_app_settings()

        self.file_path = None
        self.ed_file_path = QLineEdit()  # hidden backing field for file path references
        self.ed_file_path.setVisible(False)
        self.window_size = 10
        self.y_max = 20
        self.last_file_size = 0
        self.running = False

        self.category_map = {
            "0%": 1, "25%": 2, "50%": 3, "75%": 4, "100%": 5,
            "-75%": 6, "-50%": 7, "-25%": 8, "-0%": 9, "Home": 10
        }
        self.reverse_category_map = {v: k for k, v in self.category_map.items()}

        # grouped_data: key = step number (1..10), value lists grow with cycle count
        self.grouped_data = self._new_grouped_store()

        # tracking for cycle detection
        self._last_step = None

        self.configs_file = "graph_configs.json"
        self.saved_configs = self.load_saved_configs()
        self.current_loaded_config_name = ""

        # Timer state
        self.start_time = ""
        self.days = self.hours = self.minutes = self.seconds = 0
        self.tmr = None
        self.graph_update_timer = None

        # Serial autosave state
        self.auto_save_enabled = False
        self.auto_save_session_header_written = False
        self.last_serial_data_len = 0

        # ---- Top bar ----
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(8, 8, 8, 8)

        self.btn_back = QPushButton("←")
        self.btn_back.clicked.connect(self.go_backward)
        self.btn_back.setEnabled(True)
        self.btn_back.setStyleSheet('font-weight: 300; font-size: 20px;')

        self.btn_forward = QPushButton("→")
        self.btn_forward.setEnabled(True)
        self.btn_forward.clicked.connect(self.go_forward)
        self.btn_forward.setStyleSheet('font-weight: 300; font-size: 20px;')

        self.btn_switch_mode = QPushButton("🏠 Main Page")
        self.btn_switch_mode.clicked.connect(lambda: self.tabs.setCurrentWidget(self.main_page))
        self.btn_switch_mode.setStyleSheet('font-weight: 500; font-size: 20px;')

        self.btn_operator_mode = QPushButton("👤 Operator Mode")
        self.btn_operator_mode.clicked.connect(lambda: self.tabs.setCurrentWidget(self.page_operator))
        self.btn_operator_mode.setStyleSheet("font-weight: 500; font-size: 20px;")

        self.btn_graph_show = QPushButton("📊 Graph Data")
        self.btn_graph_show.clicked.connect(lambda: self.tabs.setCurrentWidget(self.page_graph))
        self.btn_graph_show.setStyleSheet("font-weight: 500; font-size: 20px;")

        self.btn_summary_show = QPushButton("📋 Summary")
        self.btn_summary_show.clicked.connect(self.open_summary_page)
        self.btn_summary_show.setStyleSheet("font-weight: 500; font-size: 20px;")

        self.btn_spc_chart_show = QPushButton("📈 SPC Chart")
        self.btn_spc_chart_show.clicked.connect(self.open_spc_chart_page)
        self.btn_spc_chart_show.setStyleSheet("font-weight: 500; font-size: 20px;")

        self.btn_yield_show = QPushButton("✅ Yield %")
        self.btn_yield_show.clicked.connect(self.open_yield_page)
        self.btn_yield_show.setStyleSheet("font-weight: 500; font-size: 20px;")

        # Three-dot settings button -> navigates to App Settings page
        self.btn_settings_menu = QPushButton("⋮")
        self.btn_settings_menu.setFixedSize(40, 36)
        self.btn_settings_menu.setCursor(Qt.PointingHandCursor)
        self.btn_settings_menu.setStyleSheet(
            "font-size: 22px; font-weight: 900; border: none; padding: 0;"
        )
        self.btn_settings_menu.clicked.connect(
            lambda: self.tabs.setCurrentWidget(self.page_app_settings)
        )

        self.lbl_engineer = QLabel("")
        self.lbl_engineer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_engineer.setStyleSheet("font-weight: 700; font-size: 20px;")
        self.lbl_engineer.setVisible(False)

        self.lbl_datetime = QLabel("📅 Date/Time")
        self.lbl_datetime.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_datetime.setStyleSheet("font-weight: 700; font-size: 20px;")

        top_layout.addWidget(self.btn_back)
        top_layout.addWidget(self.btn_forward)
        top_layout.addWidget(self.btn_switch_mode)
        top_layout.addWidget(self.btn_operator_mode)
        top_layout.addWidget(self.btn_graph_show)
        top_layout.addWidget(self.btn_summary_show)
        top_layout.addWidget(self.btn_spc_chart_show)
        top_layout.addWidget(self.btn_yield_show)
        top_layout.addWidget(self.lbl_engineer)
        top_layout.addStretch(1)
        top_layout.addWidget(self.lbl_datetime)
        top_layout.addWidget(self.btn_settings_menu)

        # ---- Tabs ----
        self.tabs = QTabWidget()
        self.main_page = WatermarkedWidget()
        self.page_operator = WatermarkedWidget()
        self.page_setting = WatermarkedWidget()
        self.page_graph = WatermarkedWidget()
        self.page_summary = WatermarkedWidget()
        self.page_spc_chart = WatermarkedWidget()
        self.page_yield = WatermarkedWidget()
        self.page_app_settings = WatermarkedWidget()
        self.main_page.setObjectName("watermarked")
        self.page_operator.setObjectName("watermarked")
        self.page_setting.setObjectName("watermarked")
        self.page_graph.setObjectName("watermarked")
        self.page_summary.setObjectName("watermarked")
        self.page_spc_chart.setObjectName("watermarked")
        self.page_yield.setObjectName("watermarked")
        self.page_app_settings.setObjectName("watermarked")

        self.tabs.addTab(self.main_page, "Main Page")
        self.tabs.addTab(self.page_operator, "Operator")
        self.tabs.addTab(self.page_setting, "Setting")
        self.tabs.addTab(self.page_graph, "Graph Visualization")
        self.tabs.addTab(self.page_summary, "Summary")
        self.tabs.addTab(self.page_spc_chart, "SPC Chart")
        self.tabs.addTab(self.page_yield, "Yield")
        self.tabs.addTab(self.page_app_settings, "App Settings")
        self.apply_theme(self.current_theme)
        # Hide the visible tab bar so navigation is done only via top buttons
        try:
            self.tabs.tabBar().hide()
        except Exception:
            pass

        # setup history stacks and connect tab-change handler
        self.backward = []
        self.forward = []
        self.is_navigating_history = False
        try:
            self.tabs.currentChanged.connect(self.on_tab_change)
            try:
                self.backward = [self.tabs.widget(self.tabs.currentIndex())]
            except Exception:
                self.backward = []
            try:
                self._last_selected_widget = self.tabs.widget(self.tabs.currentIndex())
            except Exception:
                self._last_selected_widget = None
            self._skip_next_password_prompt = False
            self._suppress_on_tab_change = False
        except Exception:
            pass
        finally:
            try:
                self.update_tab_navigation_buttons()
            except Exception:
                pass

        # ---- Root layout ----
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addWidget(top)
        root_layout.addWidget(self.tabs)
        self.setCentralWidget(root)

        # ---- Build pages ----
        self.build_main_page()
        self.build_operator_page()
        self.build_setting_page()
        self.build_graph_page()
        self.build_summary_page()
        self.build_spc_chart_page()
        self.build_yield_page()
        self.build_app_settings_page()

        # ---- Matplotlib init ----
        self.fig = None
        self.axes = None
        self.canvas = None
        self.toolbar = None
        self._cursor_cids = []
        self._cursor_lines = {}
        self._current_category = 0
        self._last_step = None
        self._category_pages = {}

        # ---- Date/time ticker ----
        self.dt_timer = QTimer(self)
        self.dt_timer.timeout.connect(self.update_datetime)
        self.dt_timer.start(1000)
        self.update_datetime()

    def reload_and_update_graph(self):
        """Lightweight re-sync: append missing tail data; full reload only on reset/truncate."""
        if not getattr(self, "file_path", None) or not os.path.exists(self.file_path):
            self.append_status("No data file to re-sync.")
            return

        try:
            current_size = os.path.getsize(self.file_path)

            # File reset/truncate detected -> full rebuild for consistency.
            if current_size < getattr(self, "last_file_size", 0) or getattr(self, "_file_pos", 0) > current_size:
                self._reload_full_file()
                self.last_file_size = current_size
                self.update_graph()
                return

            old_pos = getattr(self, "_file_pos", 0)
            if current_size > old_pos:
                new_points = 0
                with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(old_pos)
                    new_data = f.read()
                    self._file_pos = f.tell()

                for line in new_data.splitlines():
                    parsed = self._parse_measure_line(line)
                    if not parsed:
                        continue
                    step = parsed.get("cat")
                    if step is None:
                        continue
                    try:
                        step = int(step)
                    except Exception:
                        continue
                    if step < 1:
                        continue

                    self._append_step_point(step, parsed)
                    self._last_step = step
                    new_points += 1

                self.last_file_size = current_size
                self.append_status(f"Re-sync: appended {new_points} new points.")
            else:
                self.last_file_size = current_size
                self.append_status("Re-sync: no new data found.")

            self.update_graph()
        except Exception as e:
            self.append_status(f"Re-sync failed: {e}")

    # -------------------------
    # Date/time
    # -------------------------
    def update_datetime(self):
        self.lbl_datetime.setText(datetime.now().strftime("📅 Date:%Y-%m-%d / 🕐 Time:%H:%M:%S"))

    # -------------------------
    # Close cleanup
    # -------------------------
    def closeEvent(self, event):
        self.running = False

        # Allow PC to sleep again when app closes
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

        try:
            self.serial_worker.stop()
        except Exception:
            pass
        try:
            self.serial_thread.quit()
            self.serial_thread.wait(500)
        except Exception:
            pass
        event.accept()
