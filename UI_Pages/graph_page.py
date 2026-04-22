import os
import re
import time
import ctypes
import threading
from datetime import datetime
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QWidget, QTabWidget, QStackedLayout, QFileDialog,
)

from ..core.helpers import warn, make_scroll
from ..core.category_plot import CategoryPlotPage


class GraphPageMixin:
    """Mixin: Graph page UI + data monitoring engine, file parsing, graph rendering."""

    # -------------------------
    # Build Graph Page UI
    # -------------------------
    def build_graph_page(self):
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("📊 Live Graph Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        outer_layout.addWidget(title)

        top_row = QHBoxLayout()
        outer_layout.addLayout(top_row)

        self.btn_report = QPushButton("Save_Report")
        self.btn_view_summary = QPushButton("Show Summary")
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_manual_update = QPushButton("Manual Update Graph")
        self.btn_prev_cat = QPushButton("\u25c0 Prev")
        self.btn_next_cat = QPushButton("Next ▶")
        self.chk_show_all_data = QCheckBox("Show All Test Data")
        self.chk_show_all_data.setChecked(False)
        self.lbl_start_time = QLabel("")
        self.lbl_timer = QLabel("")
        self.lbl_operator = QLabel("")
        top_row.addWidget(self.btn_report)
        top_row.addWidget(self.btn_view_summary)
        top_row.addWidget(self.btn_stop)
        top_row.addWidget(self.btn_manual_update)
        top_row.addWidget(self.btn_prev_cat)
        top_row.addWidget(self.btn_next_cat)
        top_row.addWidget(self.chk_show_all_data)
        top_row.addStretch(1)
        top_row.addWidget(self.lbl_operator)
        top_row.addWidget(self.lbl_start_time)
        top_row.addWidget(self.lbl_timer)

        # Tabs container (one category per page)
        self.graph_tabs = QTabWidget()
        self.graph_data_page = QWidget()
        graph_data_layout = QVBoxLayout(self.graph_data_page)
        graph_data_layout.setContentsMargins(0, 0, 0, 0)
        graph_data_layout.addWidget(self.graph_tabs)

        self.graph_empty_page = QWidget()
        graph_empty_layout = QVBoxLayout(self.graph_empty_page)
        graph_empty_layout.setContentsMargins(20, 20, 20, 20)
        graph_empty_layout.addStretch(1)
        self.graph_empty_state_label = QLabel("No graph data available.\n👈 Go to the Operator tab, Load a recipe and start monitoring first.")
        self.graph_empty_state_label.setObjectName("summaryMeta")
        self.graph_empty_state_label.setStyleSheet("font-size: 22px;")
        self.graph_empty_state_label.setAlignment(Qt.AlignCenter)
        self.graph_empty_state_label.setWordWrap(True)
        graph_empty_layout.addWidget(self.graph_empty_state_label)
        graph_empty_layout.addStretch(1)

        graph_stack_host = QWidget()
        self.graph_content_stack = QStackedLayout(graph_stack_host)
        self.graph_content_stack.setContentsMargins(0, 0, 0, 0)
        self.graph_content_stack.addWidget(self.graph_empty_page)
        self.graph_content_stack.addWidget(self.graph_data_page)
        self.graph_content_stack.setCurrentWidget(self.graph_empty_page)
        outer_layout.addWidget(graph_stack_host, 1)

        scroll = make_scroll(outer)
        scroll.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self.page_graph)
        layout.addWidget(scroll)

        self.btn_stop.clicked.connect(self.stop_monitoring)
        self.btn_report.clicked.connect(self.report_summary)
        self.btn_view_summary.clicked.connect(self.open_summary_page)
        self.btn_prev_cat.clicked.connect(self.goto_prev_category_page)
        self.btn_next_cat.clicked.connect(self.goto_next_category_page)
        self.btn_manual_update.clicked.connect(self.reload_and_update_graph)
        self.chk_show_all_data.stateChanged.connect(self.on_show_all_data_changed)
        
        # Cache for full-history data (loaded on-demand when Show All Data is toggled)
        self._full_history_cache = None
        self._full_history_cache_valid = False

    def set_graph_empty_state(self, message: str):
        if hasattr(self, "graph_empty_state_label"):
            self.graph_empty_state_label.setText(message)
        if hasattr(self, "graph_content_stack"):
            self.graph_content_stack.setCurrentWidget(self.graph_empty_page)

    def set_graph_data_state(self):
        if hasattr(self, "graph_content_stack"):
            self.graph_content_stack.setCurrentWidget(self.graph_data_page)

    def goto_prev_category_page(self):
        if not hasattr(self, "graph_tabs"):
            return
        n = self.graph_tabs.count()
        if n <= 0:
            return
        i = self.graph_tabs.currentIndex()
        self.graph_tabs.setCurrentIndex((i - 1) % n)

    def goto_next_category_page(self):
        if not hasattr(self, "graph_tabs"):
            return
        n = self.graph_tabs.count()
        if n <= 0:
            return
        i = self.graph_tabs.currentIndex()
        self.graph_tabs.setCurrentIndex((i + 1) % n)

    def on_show_all_data_changed(self):
        """When Show All Data is toggled, load full history from file on-demand."""
        show_all = getattr(self, "chk_show_all_data", None) and self.chk_show_all_data.isChecked()
        if show_all and not self._full_history_cache_valid:
            # Load full history from file for Show All Data display
            QTimer.singleShot(0, self._load_full_history_cache)
        else:
            QTimer.singleShot(0, self.update_graph)

    # =========================================================
    # Monitoring Engine (data file parsing, graph rendering)
    # =========================================================

    def _new_grouped_store(self):
        return defaultdict(lambda: {
            "current_tm": [],
            "resistance_tm": [],
            "current_other": [],
            "resistance_other": [],
            "force": [],
            "has_other": False
        })

    def _downsample_data(self, data_list, max_points=5000):
        """Downsample large datasets for plotting performance."""
        if len(data_list) <= max_points:
            return data_list
        step = len(data_list) // max_points
        return data_list[::step]

    def setup_plot(self, selected_categories=None):
        if not hasattr(self, "graph_layout"):
            return

        if selected_categories is None:
            selected_categories = self._get_selected_categories_for_graph()

        if self.fig:
            plt.close(self.fig)

        if not selected_categories:
            self.fig, ax = plt.subplots(1, 1, figsize=(10, 3))
            ax.set_xlabel("Test Counts")
            ax.set_ylabel("Value")
            ax.grid(True)
            self.axes_pairs = []
        else:
            n = len(selected_categories)

            self.fig, axes = plt.subplots(
                2 * n, 1,
                figsize=(10, max(3, 5.2 * n))
            )
            axes = np.atleast_1d(axes)

            self.axes_pairs = []
            for i, category in enumerate(selected_categories):
                ax_cur = axes[2 * i]
                ax_res = axes[2 * i + 1]

                ax_cur.set_ylabel("Current (A)")
                ax_cur.grid(True, linestyle="--", alpha=0.7)
                ax_cur.text(
                    0.95, 0.90, f"{category} (Current)", transform=ax_cur.transAxes,
                    fontsize=9, va="top", ha="right",
                    bbox=dict(facecolor="white", alpha=0.5, edgecolor="black")
                )

                ax_res.set_ylabel("R-Value (mΩ)")
                ax_res.set_xlabel("Test Counts")
                ax_res.set_ylim(0, self.y_max)
                ax_res.grid(True, linestyle="--", alpha=0.7)
                ax_res.text(
                    0.95, 0.90, f"{category} (Resistance)", transform=ax_res.transAxes,
                    fontsize=9, va="top", ha="right",
                    bbox=dict(facecolor="white", alpha=0.5, edgecolor="black")
                )

                self.axes_pairs.append((ax_cur, ax_res))

        # clear old widgets
        for i in reversed(range(self.graph_layout.count())):
            w = self.graph_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.graph_layout.addWidget(self.toolbar)
        self.graph_layout.addWidget(self.canvas)

        self.fig.tight_layout(pad=1.0)
        self.canvas.draw_idle()

    def append_status(self, msg: str):
        try:
            self.serial_log.appendPlainText(msg)
        except Exception:
            pass

    def _get_active_config(self) -> dict:
        if getattr(self, "current_loaded_config_name", ""):
            return self.saved_configs.get(self.current_loaded_config_name, {}) or {}
        return {}

    def _get_selected_categories_for_graph(self):
        cfg = self._get_active_config()
        cats = cfg.get("categories", [])

        if isinstance(cats, dict):
            selected = [c for c, v in cats.items() if v]
        elif isinstance(cats, list):
            selected = list(cats)
        else:
            selected = []

        if selected:
            return selected

        if hasattr(self, "category_checks"):
            return [k for k, cb in self.category_checks.items() if cb.isChecked()]

        return []

    def _get_graph_params_from_recipe(self):
        cfg = self._get_active_config()

        self.window_size = int(cfg.get("window_size", self.window_size or 10))
        self.y_max = int(cfg.get("yAxis_max", cfg.get("y_axis_max", self.y_max or 20)))

        self.open_circuit = int(cfg.get("open_circuit", cfg.get("y_max", 3000)))
        self.close_circuit = int(cfg.get("close_circuit", cfg.get("y_min", 0)))

        self.display_mode = cfg.get("display_mode", "Display All_data")

    def start_monitoring(self):
        cfg = self._get_active_config()
        if not cfg:
            warn(self, "Warning", "Please load a recipe first (Operator page).")
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            os.path.join(self.default_save_folder, "Test data"),
            "CSV/Text Files (*.csv *.txt);;All Files (*)"
        )
        if path:
            self.ed_file_path.setText(path)

        self.file_path = path
        if not self.file_path or not os.path.exists(self.file_path):
            warn(self, "Warning", "No Data File is selected")
            return

        self._get_graph_params_from_recipe()

        sel_cats = self._get_selected_categories_for_graph()
        self.setup_plot(sel_cats)

        self.start_time = datetime.now().strftime("%Y-%m-%d / %H:%M:%S")
        self.lbl_start_time.setText(f"Start-Time:{self.start_time}")

        op = self.operator_name.text().strip()
        self.lbl_operator.setText(f"Operator Name: {op}")

        self.days = self.hours = self.minutes = self.seconds = 0
        self.running = True

        # Prevent PC from sleeping while test is running
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )

        self.btn_stop.setEnabled(True)
        self.btn_start.setEnabled(False)
        self.btn_stop_main.setEnabled(True)

        if not hasattr(self, "tmr") or self.tmr is None:
            self.tmr = QTimer(self)
            self.tmr.timeout.connect(self._tick_timer)
        self.tmr.start(1000)

        # ---- Initial full-file load ----
        try:
            self.grouped_data = self._new_grouped_store()
            self._last_step = None

            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parsed = self._parse_measure_line(line)
                    if not parsed:
                        continue

                    step = parsed['cat']

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

                self._file_pos = f.tell()
                self.last_file_size = self._file_pos

            QTimer.singleShot(0, self.update_graph)

        except Exception as e:
            self.append_status(f"Initial load failed: {e}")
            try:
                self.last_file_size = os.path.getsize(self.file_path)
                self._file_pos = self.last_file_size
            except Exception:
                self.last_file_size = 0
                self._file_pos = 0

        # ---- start tail thread ----
        self.monitor_thread = threading.Thread(target=self.monitor_data_file, daemon=True)
        self.monitor_thread.start()

        self.tabs.setCurrentWidget(self.page_graph)

        try:
            if not hasattr(self, "graph_update_timer") or self.graph_update_timer is None:
                self.graph_update_timer = QTimer(self)
                # Reduced frequency - only update display every 2s (no file reload)
                # Monitor thread handles incremental appends; full reload only on truncate/rotation
                self.graph_update_timer.timeout.connect(self.update_graph)
            self.graph_update_timer.start(2000)
        except Exception:
            pass

    def stop_monitoring(self):
        self.running = False

        # Allow PC to sleep again
        ES_CONTINUOUS = 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

        self.btn_stop.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.btn_stop_main.setEnabled(False)

        # Clear full-history cache on stop
        self._full_history_cache = None
        self._full_history_cache_valid = False

        try:
            if hasattr(self, "graph_update_timer"):
                self.graph_update_timer.stop()
        except Exception:
            pass

    def test_procedure(self):
        target_dir = os.path.join(self.default_save_folder, "Test Procedure")
        target_base_name = "Rhino_Shortcuts_CheatSheet"

        if not os.path.isdir(target_dir):
            warn(self, "Test Procedure", f"Folder not found:\n{target_dir}")
            return

        target_file = os.path.join(target_dir, target_base_name)
        matched_file = target_file if os.path.isfile(target_file) else None

        if matched_file is None:
            try:
                for entry in os.listdir(target_dir):
                    entry_base, _ = os.path.splitext(entry)
                    if entry_base.lower() == target_base_name.lower():
                        candidate = os.path.join(target_dir, entry)
                        if os.path.isfile(candidate):
                            matched_file = candidate
                            break
            except Exception as e:
                warn(self, "Test Procedure", f"Unable to access folder:\n{e}")
                return

        if matched_file:
            try:
                os.startfile(matched_file)
                return
            except Exception as e:
                warn(self, "Test Procedure", f"Unable to open file:\n{e}")
                return

        try:
            os.startfile(target_dir)
            warn(
                self,
                "Test Procedure",
                f"File '{target_base_name}' not found in:\n{target_dir}\n\nOpened folder instead."
            )
        except Exception as e:
            warn(self, "Test Procedure", f"Unable to open folder:\n{e}")

    def _tick_timer(self):
        if not self.running:
            self.tmr.stop()
            return
        self.seconds += 1
        if self.seconds >= 60:
            self.seconds = 0
            self.minutes += 1
            if self.minutes >= 60:
                self.minutes = 0
                self.hours += 1
                if self.hours >= 24:
                    self.hours = 0
                    self.days += 1
        self.lbl_timer.setText(f"Timer:{self.days:02d}:{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}")
    def _load_full_history_cache(self):
        """Load full history from file into cache for Show All Data display."""
        if not self.file_path or not os.path.exists(self.file_path):
            return
        try:
            temp_cache = self._new_grouped_store()
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    parsed = self._parse_measure_line(line)
                    if not parsed:
                        continue
                    step = parsed['cat']
                    if step is None or step < 1:
                        continue
                    self._append_step_point_to_store(step, parsed, temp_cache)
            self._full_history_cache = temp_cache
            self._full_history_cache_valid = True
            total_points = sum(len(v["resistance_tm"]) for v in temp_cache.values())
            self.append_status(f"✓ Full history loaded: {total_points:,} total points cached for display.")
        except Exception as e:
            self.append_status(f"Full history cache load failed: {e}")
        QTimer.singleShot(0, self.update_graph)
    def monitor_data_file(self):
        while self.running:
            try:
                try:
                    current_size = os.path.getsize(self.file_path)
                except OSError:
                    time.sleep(1)
                    continue

                if current_size < getattr(self, "last_file_size", 0) or getattr(self, "_file_pos", 0) > current_size:
                    try:
                        self._reload_full_file()
                        self.last_file_size = current_size
                    except Exception:
                        pass
                    time.sleep(0.2)
                    continue

                if current_size > getattr(self, "_file_pos", 0):
                    with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(self._file_pos)
                        new_data = f.read()
                        self._file_pos = f.tell()

                    if not new_data:
                        time.sleep(0.2)
                        continue

                    lines = new_data.splitlines()

                    for line in lines:
                        parsed = self._parse_measure_line(line)
                        if not parsed:
                            continue

                        step = parsed['cat']

                        if step == 1 and self._last_step is not None and self._last_step != 1:
                            pass  # cycle boundary detected

                        self._append_step_point(step, parsed)
                        self._last_step = step

                    try:
                        counts = {k: min(len(v["current_tm"]), len(v["resistance_tm"])) for k, v in self.grouped_data.items()}
                        QTimer.singleShot(0, lambda: self.append_status(f"Live counts per step: {counts}"))
                    except Exception:
                        pass

                    QTimer.singleShot(0, self.update_graph)

                self.last_file_size = current_size
                time.sleep(0.5)

            except Exception:
                time.sleep(2)

    def update_graph(self):
        try:
            selected_categories = self._get_selected_categories_for_graph()
            
            # Determine which data source to use
            show_all = getattr(self, "chk_show_all_data", None) and self.chk_show_all_data.isChecked()
            use_cache = show_all and self._full_history_cache_valid
            data_source = self._full_history_cache if use_cache else self.grouped_data
            
            if not selected_categories:
                inferred_steps = sorted(data_source.keys())
                if not inferred_steps:
                    self.set_graph_empty_state("No graph data available. Load a recipe and start monitoring first.")
                    return
                selected_categories = [self.reverse_category_map.get(s, str(s)) for s in inferred_steps]

            window_size = int(getattr(self, "window_size", 10) or 10)

            display_mode = getattr(self, "display_mode", "Display All_data")
            y_min_limit = float(getattr(self, "close_circuit", 0))
            y_max_limit = float(getattr(self, "open_circuit", 3000))

            current_step = None
            try:
                current_page = self.graph_tabs.currentWidget()
                for step_key, page_obj in self._category_pages.items():
                    if page_obj is current_page:
                        current_step = step_key
                        break
            except Exception:
                current_step = None

            rendered_any_page = False

            for label in selected_categories:
                if isinstance(label, int):
                    step = label
                    label_text = self.reverse_category_map.get(step, f"STEP {step}")
                else:
                    step = self.category_map.get(label)
                    if step is None and str(label).isdigit():
                        step = int(label)
                    label_text = str(label)

                if step is None:
                    continue

                data = data_source.get(step, {})
                cur_vals_tm = data.get("current_tm", [])
                res_vals_tm = data.get("resistance_tm", [])
                cur_vals_other = data.get("current_other", [])
                res_vals_other = data.get("resistance_other", [])
                force_vals = data.get("force", [])
                has_other = data.get("has_other", False)

                if not cur_vals_tm or not res_vals_tm:
                    continue
                
                # Apply downsampling for very large datasets (>5000 points) when showing all
                if show_all and len(cur_vals_tm) > 5000:
                    ds_factor = len(cur_vals_tm) // 5000
                    cur_vals_tm = cur_vals_tm[::ds_factor]
                    res_vals_tm = res_vals_tm[::ds_factor]
                    cur_vals_other = cur_vals_other[::ds_factor] if cur_vals_other else []
                    res_vals_other = res_vals_other[::ds_factor] if res_vals_other else []
                    force_vals = force_vals[::ds_factor] if force_vals else []

                rendered_any_page = True

                # clamp resistance TM
                processed_res_tm = []
                for y in res_vals_tm:
                    y = max(y, y_min_limit)
                    y = min(y, y_max_limit)
                    processed_res_tm.append(y)

                # clamp resistance Other if available
                processed_res_other = []
                if has_other and res_vals_other:
                    for y in res_vals_other:
                        y = max(y, y_min_limit)
                        y = min(y, y_max_limit)
                        processed_res_other.append(y)

                # cutoff mode
                if display_mode == "Cut_off beyond limit data":
                    if has_other and processed_res_other:
                        keep_idx = []
                        for k in range(min(len(processed_res_tm), len(processed_res_other))):
                            tm_valid = y_min_limit < processed_res_tm[k] < y_max_limit
                            other_valid = y_min_limit < processed_res_other[k] < y_max_limit
                            if tm_valid or other_valid:
                                keep_idx.append(k)

                        cur_vals_tm = [cur_vals_tm[k] for k in keep_idx] if len(cur_vals_tm) > 0 else []
                        processed_res_tm = [processed_res_tm[k] for k in keep_idx]
                        cur_vals_other = [cur_vals_other[k] for k in keep_idx] if len(cur_vals_other) > 0 else []
                        processed_res_other = [processed_res_other[k] for k in keep_idx]
                        force_vals = [force_vals[k] for k in keep_idx] if force_vals else []
                    else:
                        keep_idx = [k for k, y in enumerate(processed_res_tm) if (y_min_limit < y < y_max_limit)]
                        cur_vals_tm = [cur_vals_tm[k] for k in keep_idx]
                        processed_res_tm = [processed_res_tm[k] for k in keep_idx]
                        force_vals = [force_vals[k] for k in keep_idx] if force_vals else []

                # create/reuse the page for this step
                if step not in self._category_pages:
                    page = CategoryPlotPage()
                    self._category_pages[step] = page
                    self.graph_tabs.addTab(page, label_text)
                else:
                    page = self._category_pages[step]

                if current_step is None:
                    current_step = step
                    try:
                        if self.graph_tabs.currentIndex() < 0:
                            self.graph_tabs.setCurrentIndex(self.graph_tabs.count() - 1)
                    except Exception:
                        pass

                if step == current_step:
                    page.set_data(
                        label_text=f"{label_text}",
                        cur_vals=cur_vals_tm,
                        res_vals=processed_res_tm,
                        force_vals=force_vals,
                        y_max=float(getattr(self, "y_max", 3000)),
                        window_size=window_size,
                        color='blue',
                        cur_vals_other=cur_vals_other if has_other else None,
                        res_vals_other=processed_res_other if has_other else None,
                        color_other='red',
                        show_all_data=show_all,
                        line_width=self._get_line_width()
                    )

            if rendered_any_page:
                self.set_graph_data_state()
            else:
                self.set_graph_empty_state("No graph data available for the selected categories yet.")

            try:
                if self.graph_tabs.count() > 0 and self.graph_tabs.currentIndex() < 0:
                    self.graph_tabs.setCurrentIndex(0)
            except Exception:
                pass

        except Exception as e:
            try:
                self.serial_log.appendPlainText(f"Graph update error: {e}")
            except Exception:
                pass

    def _append_step_point(self, step: int, parsed_data: dict):
        if step is None or parsed_data is None:
            return
        if step < 1:
            return

        self.grouped_data[step]["current_tm"].append(parsed_data['cur_tm'])
        self.grouped_data[step]["resistance_tm"].append(parsed_data['res_tm'])
        self.grouped_data[step]["force"].append(parsed_data['force'])

        if parsed_data['has_other']:
            self.grouped_data[step]["current_other"].append(parsed_data['cur_other'])
            self.grouped_data[step]["resistance_other"].append(parsed_data['res_other'])
            self.grouped_data[step]["has_other"] = True
        
        # Invalidate full-history cache when new data arrives
        self._full_history_cache_valid = False

    def _append_step_point_to_store(self, step: int, parsed_data: dict, store: dict):
        """Helper to append a point to any store (live or cache)."""
        if step is None or parsed_data is None:
            return
        if step < 1:
            return

        store[step]["current_tm"].append(parsed_data['cur_tm'])
        store[step]["resistance_tm"].append(parsed_data['res_tm'])
        store[step]["force"].append(parsed_data['force'])

        if parsed_data['has_other']:
            store[step]["current_other"].append(parsed_data['cur_other'])
            store[step]["resistance_other"].append(parsed_data['res_other'])
            store[step]["has_other"] = True

    def _reload_full_file(self):
        self.grouped_data = self._new_grouped_store()
        self._last_step = None

        with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parsed = self._parse_measure_line(line)
                if not parsed:
                    continue
                step = parsed['cat']
                self._append_step_point(step, parsed)
                self._last_step = step

            self._file_pos = f.tell()
            self.last_file_size = self._file_pos

    def _parse_measure_line(self, line: str):
        # Both format: 1,Current: 0.1635 A | ResTM: 179.173 mOhm | ResOther: 49.592 mOhm | Force: 0 g
        BOTH_MEAS_RE = re.compile(
            r"^\s*(\d+)\s*,\s*Current\s*:\s*([0-9]*\.?[0-9]+)\s*A\s*\|\s*ResTM\s*:\s*([0-9]*\.?[0-9]+)\s*mOhm\s*\|\s*ResOther\s*:\s*([0-9]*\.?[0-9]+)\s*mOhm\s*\|\s*Force\s*:\s*([0-9]*\.?[0-9]+)\s*g\s*$",
            re.IGNORECASE
        )

        # TM only format: 1,Current: 0.1650 A | ResTM: 179.050 mOhm | Force: 0 g
        TM_MEAS_RE = re.compile(
            r"^\s*(\d+)\s*,\s*Current\s*:\s*([0-9]*\.?[0-9]+)\s*A\s*\|\s*ResTM\s*:\s*([0-9]*\.?[0-9]+)\s*mOhm(?:\s*\|\s*Force\s*:\s*([0-9]*\.?[0-9]+)\s*g)?\s*$",
            re.IGNORECASE
        )

        stripped_line = (line or "").strip()

        m = BOTH_MEAS_RE.match(stripped_line)
        if m:
            return {
                'cat': int(m.group(1)),
                'cur_tm': float(m.group(2)),
                'cur_other': float(m.group(2)),
                'res_tm': float(m.group(3)),
                'res_other': float(m.group(4)),
                'force': float(m.group(5)),
                'has_other': True
            }

        m = TM_MEAS_RE.match(stripped_line)
        if m:
            return {
                'cat': int(m.group(1)),
                'cur_tm': float(m.group(2)),
                'cur_other': None,
                'res_tm': float(m.group(3)),
                'res_other': None,
                'force': float(m.group(4)) if m.group(4) is not None else 0.0,
                'has_other': False
            }

        return None
