from datetime import datetime

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QComboBox, QSpinBox, QCheckBox, QTabWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from ..core.helpers import make_scroll


class SPCChartPageMixin:
    """Mixin: SPC Chart page – two sub-tabs for Resistance and Current."""

    def build_spc_chart_page(self):
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(12)

        # ---- Header row ----
        header_row = QHBoxLayout()
        outer_layout.addLayout(header_row)

        title = QLabel("📈 SPC Chart")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        header_row.addWidget(title)

        header_row.addStretch(1)

        self.btn_refresh_spc = QPushButton("🔄 Refresh")
        self.btn_refresh_spc.clicked.connect(self.refresh_spc_chart)
        header_row.addWidget(self.btn_refresh_spc)

        # ---- Sub-tabs: Resistance / Current ----
        self.spc_sub_tabs = QTabWidget()
        self.spc_sub_tabs.setStyleSheet(
            "QTabBar::tab { min-width: 120px; padding: 6px 16px; font-weight: 600; }"
        )
        outer_layout.addWidget(self.spc_sub_tabs, 1)

        self._build_spc_resistance_tab()
        self._build_spc_current_tab()

        layout = QVBoxLayout(self.page_spc_chart)
        layout.addWidget(outer)

    # ---------------------------------------------------------
    # Resistance SPC Tab
    # ---------------------------------------------------------
    def _build_spc_resistance_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(tab)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(8)

        controls = QHBoxLayout()
        vl.addLayout(controls)

        controls.addWidget(QLabel("Category:"))
        self.spc_category_combo = QComboBox()
        self.spc_category_combo.setMinimumWidth(140)
        self.spc_category_combo.currentIndexChanged.connect(self._refresh_spc_resistance_chart)
        controls.addWidget(self.spc_category_combo)

        controls.addWidget(QLabel("Data Source:"))
        self.spc_source_combo = QComboBox()
        self.spc_source_combo.addItems(["TestMax Pin", "Other Pin"])
        self.spc_source_combo.currentIndexChanged.connect(self._refresh_spc_resistance_chart)
        controls.addWidget(self.spc_source_combo)

        controls.addWidget(QLabel("Sigma (σ):"))
        self.spc_sigma_spin = QSpinBox()
        self.spc_sigma_spin.setRange(1, 6)
        self.spc_sigma_spin.setValue(3)
        self.spc_sigma_spin.setToolTip("Number of standard deviations for control limits")
        self.spc_sigma_spin.valueChanged.connect(self._refresh_spc_resistance_chart)
        controls.addWidget(self.spc_sigma_spin)

        controls.addWidget(QLabel("Window:"))
        self.spc_window_spin = QSpinBox()
        self.spc_window_spin.setRange(10, 10000)
        self.spc_window_spin.setValue(150)
        self.spc_window_spin.setToolTip("Number of last data points to display")
        self.spc_window_spin.valueChanged.connect(self._refresh_spc_resistance_chart)
        controls.addWidget(self.spc_window_spin)

        self.spc_show_all_chk = QCheckBox("Show All Test Data")
        self.spc_show_all_chk.setChecked(False)
        self.spc_show_all_chk.stateChanged.connect(self._refresh_spc_resistance_chart)
        controls.addWidget(self.spc_show_all_chk)

        controls.addStretch(1)

        self.spc_context_label = QLabel("Load a recipe and collect data to view SPC chart.")
        self.spc_context_label.setObjectName("summaryMeta")
        vl.addWidget(self.spc_context_label)

        self.spc_figure = Figure(figsize=(10, 5), dpi=100)
        self.spc_figure.patch.set_facecolor("none")
        self.spc_canvas = FigureCanvas(self.spc_figure)
        self.spc_canvas.setStyleSheet("background: transparent;")
        self.spc_canvas.setMinimumHeight(380)

        self.spc_toolbar = NavigationToolbar(self.spc_canvas, None)

        self._spc_annot = None
        self._spc_scatter = None
        self._spc_data = None
        self._spc_ucl = None
        self._spc_lcl = None
        self._spc_mean = None
        self._spc_hover_cid = None

        vl.addWidget(self.spc_toolbar)
        vl.addWidget(self.spc_canvas, 1)

        self.spc_stats_label = QLabel("")
        self.spc_stats_label.setObjectName("summaryMeta")
        self.spc_stats_label.setWordWrap(True)
        vl.addWidget(self.spc_stats_label)

        self.spc_sub_tabs.addTab(tab, "⚡ Resistance")

    # ---------------------------------------------------------
    # Current SPC Tab (no Data Source — current is shared)
    # ---------------------------------------------------------
    def _build_spc_current_tab(self):
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(tab)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(8)

        controls = QHBoxLayout()
        vl.addLayout(controls)

        controls.addWidget(QLabel("Category:"))
        self.spc_cur_category_combo = QComboBox()
        self.spc_cur_category_combo.setMinimumWidth(140)
        self.spc_cur_category_combo.currentIndexChanged.connect(self._refresh_spc_current_chart)
        controls.addWidget(self.spc_cur_category_combo)

        controls.addWidget(QLabel("Sigma (σ):"))
        self.spc_cur_sigma_spin = QSpinBox()
        self.spc_cur_sigma_spin.setRange(1, 6)
        self.spc_cur_sigma_spin.setValue(3)
        self.spc_cur_sigma_spin.valueChanged.connect(self._refresh_spc_current_chart)
        controls.addWidget(self.spc_cur_sigma_spin)

        controls.addWidget(QLabel("Window:"))
        self.spc_cur_window_spin = QSpinBox()
        self.spc_cur_window_spin.setRange(10, 10000)
        self.spc_cur_window_spin.setValue(150)
        self.spc_cur_window_spin.valueChanged.connect(self._refresh_spc_current_chart)
        controls.addWidget(self.spc_cur_window_spin)

        self.spc_cur_show_all_chk = QCheckBox("Show All Test Data")
        self.spc_cur_show_all_chk.setChecked(False)
        self.spc_cur_show_all_chk.stateChanged.connect(self._refresh_spc_current_chart)
        controls.addWidget(self.spc_cur_show_all_chk)

        controls.addStretch(1)

        self.spc_cur_context_label = QLabel("Load a recipe and collect data to view Current SPC chart.")
        self.spc_cur_context_label.setObjectName("summaryMeta")
        vl.addWidget(self.spc_cur_context_label)

        self.spc_cur_figure = Figure(figsize=(10, 5), dpi=100)
        self.spc_cur_figure.patch.set_facecolor("none")
        self.spc_cur_canvas = FigureCanvas(self.spc_cur_figure)
        self.spc_cur_canvas.setStyleSheet("background: transparent;")
        self.spc_cur_canvas.setMinimumHeight(380)

        self.spc_cur_toolbar = NavigationToolbar(self.spc_cur_canvas, None)

        self._spc_cur_annot = None
        self._spc_cur_scatter = None
        self._spc_cur_data = None
        self._spc_cur_ucl = None
        self._spc_cur_lcl = None
        self._spc_cur_mean = None
        self._spc_cur_hover_cid = None

        vl.addWidget(self.spc_cur_toolbar)
        vl.addWidget(self.spc_cur_canvas, 1)

        self.spc_cur_stats_label = QLabel("")
        self.spc_cur_stats_label.setObjectName("summaryMeta")
        self.spc_cur_stats_label.setWordWrap(True)
        vl.addWidget(self.spc_cur_stats_label)

        self.spc_sub_tabs.addTab(tab, "🔌 Current")

    # =========================================================
    # SPC Chart Logic
    # =========================================================

    def _populate_spc_categories(self):
        """Populate both category combos from current grouped_data."""
        steps = sorted(self.grouped_data.keys())

        for combo in (self.spc_category_combo, self.spc_cur_category_combo):
            combo.blockSignals(True)
            prev = combo.currentText()
            combo.clear()
            for step in steps:
                label = self.reverse_category_map.get(step, f"Step {step}")
                combo.addItem(label, step)
            idx = combo.findText(prev)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

    def refresh_spc_chart(self):
        """Redraw both Resistance and Current SPC charts."""
        self._populate_spc_categories()
        self._refresh_spc_resistance_chart()
        self._refresh_spc_current_chart()

    def _refresh_spc_resistance_chart(self):
        """Redraw the Resistance SPC chart."""
        self._populate_spc_categories()

        step = self.spc_category_combo.currentData()
        if step is None:
            self._draw_empty_spc("No category data available.")
            return

        source = self.spc_source_combo.currentText()
        r_key = "resistance_tm" if source == "TestMax Pin" else "resistance_other"
        data_dict = self.grouped_data.get(step, {})
        r_values = data_dict.get(r_key, [])

        sigma_k = self.spc_sigma_spin.value()

        if r_values:
            self._draw_spc_chart(r_values, sigma_k)
        else:
            self._draw_empty_spc(f"No resistance data for {self.spc_category_combo.currentText()}.")

        config_name = getattr(self, "current_loaded_config_name", "") or "N/A"
        cat_label = self.spc_category_combo.currentText()
        self.spc_context_label.setText(
            f"Recipe: {config_name}    |    Category: {cat_label}    |    "
            f"Source: {source}    |    Points: {len(r_values)}    |    "
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )

    def _draw_spc_chart(self, values, sigma_k):
        """Draw the SPC (X-bar) chart with UCL, LCL, and center line."""
        all_data = np.array(values, dtype=float)
        # Stats are always computed on ALL data
        mean = float(np.mean(all_data))
        std = float(np.std(all_data))
        ucl = mean + sigma_k * std
        lcl = mean - sigma_k * std

        # Window the display data
        show_all = self.spc_show_all_chk.isChecked()
        window = self.spc_window_spin.value()
        if not show_all and len(all_data) > window:
            display_data = all_data[-window:]
            start_idx = len(all_data) - window + 1
        else:
            display_data = all_data
            start_idx = 1
        x = np.arange(start_idx, start_idx + len(display_data))

        # Theme-aware colors
        is_dark = getattr(self, 'current_theme', 'Light') == 'Dark'
        text_color = '#e6edf3' if is_dark else '#1f2328'
        bg_color = '#0d1117' if is_dark else '#ffffff'

        fig = self.spc_figure
        fig.clear()
        ax = fig.add_subplot(111)
        fig.patch.set_facecolor('none')
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        for spine in ax.spines.values():
            spine.set_edgecolor(text_color)

        # Determine point colors: red if outside limits, blue if within
        colors = ["#e74c3c" if (v > ucl or v < lcl) else "#3498db" for v in display_data]
        self._spc_scatter = ax.scatter(x, display_data, c=colors, s=18, zorder=5, picker=True)
        ax.plot(x, display_data, color="#3498db", linewidth=0.8, alpha=0.6, zorder=4)

        # Store data for hover lookup
        self._spc_data = display_data
        self._spc_x_offset = start_idx
        self._spc_ucl = ucl
        self._spc_lcl = lcl
        self._spc_mean = mean

        # Control lines
        ax.axhline(mean, color="#2ecc71", linewidth=1.5, linestyle="-", label=f"Mean: {mean:.2f} mΩ")
        ax.axhline(ucl, color="#e74c3c", linewidth=1.2, linestyle="--", label=f"UCL ({sigma_k}σ): {ucl:.2f} mΩ")
        ax.axhline(lcl, color="#e74c3c", linewidth=1.2, linestyle="--", label=f"LCL ({sigma_k}σ): {lcl:.2f} mΩ")

        # Fill out-of-control zones
        ax.fill_between(x, ucl, max(display_data.max(), ucl) * 1.05, alpha=0.07, color="#e74c3c")
        ax.fill_between(x, lcl, min(display_data.min(), lcl) * 0.95 if lcl > 0 else lcl - abs(lcl) * 0.05, alpha=0.07, color="#e74c3c")

        ax.set_xlabel("Test Count")
        ax.set_ylabel("Resistance (mΩ)")
        ax.set_title("SPC Control Chart — Resistance over Time")
        ax.legend(loc="upper right", fontsize=8, facecolor=bg_color, edgecolor=text_color, labelcolor=text_color)
        ax.grid(True, alpha=0.3)

        # Setup hover annotation
        self._spc_annot = ax.annotate(
            "", xy=(0, 0), xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#ffffcc", ec="#333333", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#333333"),
            fontsize=9, color="#1f2328", zorder=10,
        )
        self._spc_annot.set_visible(False)

        # Connect hover event (disconnect previous if any)
        if self._spc_hover_cid is not None:
            self.spc_canvas.mpl_disconnect(self._spc_hover_cid)
        self._spc_hover_cid = self.spc_canvas.mpl_connect("motion_notify_event", self._on_spc_hover)

        fig.tight_layout()
        self.spc_canvas.draw()

        # Stats bar (always based on ALL data)
        ooc_all = int(np.sum((all_data > ucl) | (all_data < lcl)))
        showing = f"Showing last {len(display_data)} of {len(all_data)}" if len(display_data) < len(all_data) else f"Showing all {len(all_data)}"
        self.spc_stats_label.setText(
            f"{showing}    |    "
            f"Mean(Avg): {mean:.3f} mΩ    |    Standard Deviation(Std): {std:.3f} mΩ    |    "
            f"Upper Control Limit(UCL): {ucl:.3f} mΩ    |    Lower Control Limit(LCL): {lcl:.3f} mΩ    |    "
            f"Out-of-Control: {ooc_all}/{len(all_data)} ({ooc_all/len(all_data)*100:.1f}%)"
        )

    def _on_spc_hover(self, event):
        """Show annotation tooltip when cursor is near a data point."""
        if self._spc_annot is None or self._spc_scatter is None or self._spc_data is None:
            return
        if event.inaxes is None:
            if self._spc_annot.get_visible():
                self._spc_annot.set_visible(False)
                self.spc_canvas.draw_idle()
            return

        cont, ind = self._spc_scatter.contains(event)
        if cont:
            idx = ind["ind"][0]
            val = float(self._spc_data[idx])
            sample_num = idx + getattr(self, '_spc_x_offset', 1)

            # Determine status
            if val > self._spc_ucl:
                status = "⚠ ABOVE UCL"
            elif val < self._spc_lcl:
                status = "⚠ BELOW LCL"
            else:
                status = "✅ In Control"

            cat_label = self.spc_category_combo.currentText()
            source = self.spc_source_combo.currentText()

            self._spc_annot.xy = (sample_num, val)
            self._spc_annot.set_text(
                f"Test Count #{sample_num}\n"
                f"Resistance: {val:.3f} mΩ\n"
                f"Category: {cat_label}\n"
                f"Source: {source}\n"
                f"Status: {status}"
            )
            self._spc_annot.set_visible(True)
            self.spc_canvas.draw_idle()
        else:
            if self._spc_annot.get_visible():
                self._spc_annot.set_visible(False)
                self.spc_canvas.draw_idle()

    def _draw_empty_spc(self, message):
        """Show an empty chart with a centered message."""
        fig = self.spc_figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=14,
                transform=ax.transAxes, color="gray")
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout()
        self.spc_canvas.draw()
        self.spc_stats_label.setText("")

    # =========================================================
    # Current SPC Chart Logic (single value — series connection)
    # =========================================================

    def _refresh_spc_current_chart(self):
        """Redraw the Current SPC chart."""
        self._populate_spc_categories()

        step = self.spc_cur_category_combo.currentData()
        if step is None:
            self._draw_empty_spc_cur("No category data available.")
            return

        data_dict = self.grouped_data.get(step, {})
        # Current is the same for both pins (series connection) — always use current_tm
        c_values = data_dict.get("current_tm", [])

        sigma_k = self.spc_cur_sigma_spin.value()

        if c_values:
            self._draw_spc_cur_chart(c_values, sigma_k)
        else:
            self._draw_empty_spc_cur(f"No current data for {self.spc_cur_category_combo.currentText()}.")

        config_name = getattr(self, "current_loaded_config_name", "") or "N/A"
        cat_label = self.spc_cur_category_combo.currentText()
        self.spc_cur_context_label.setText(
            f"Recipe: {config_name}    |    Category: {cat_label}    |    "
            f"Points: {len(c_values)}    |    "
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )

    def _draw_spc_cur_chart(self, values, sigma_k):
        """Draw the SPC chart for Current over Time."""
        all_data = np.array(values, dtype=float)
        mean = float(np.mean(all_data))
        std = float(np.std(all_data))
        ucl = mean + sigma_k * std
        lcl = mean - sigma_k * std

        show_all = self.spc_cur_show_all_chk.isChecked()
        window = self.spc_cur_window_spin.value()
        if not show_all and len(all_data) > window:
            display_data = all_data[-window:]
            start_idx = len(all_data) - window + 1
        else:
            display_data = all_data
            start_idx = 1
        x = np.arange(start_idx, start_idx + len(display_data))

        is_dark = getattr(self, 'current_theme', 'Light') == 'Dark'
        text_color = '#e6edf3' if is_dark else '#1f2328'
        bg_color = '#0d1117' if is_dark else '#ffffff'

        fig = self.spc_cur_figure
        fig.clear()
        ax = fig.add_subplot(111)
        fig.patch.set_facecolor('none')
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        for spine in ax.spines.values():
            spine.set_edgecolor(text_color)

        colors = ["#e74c3c" if (v > ucl or v < lcl) else "#e67e22" for v in display_data]
        self._spc_cur_scatter = ax.scatter(x, display_data, c=colors, s=18, zorder=5, picker=True)
        ax.plot(x, display_data, color="#e67e22", linewidth=0.8, alpha=0.6, zorder=4)

        self._spc_cur_data = display_data
        self._spc_cur_x_offset = start_idx
        self._spc_cur_ucl = ucl
        self._spc_cur_lcl = lcl
        self._spc_cur_mean = mean

        ax.axhline(mean, color="#2ecc71", linewidth=1.5, linestyle="-", label=f"Mean: {mean:.2f} mA")
        ax.axhline(ucl, color="#e74c3c", linewidth=1.2, linestyle="--", label=f"UCL ({sigma_k}σ): {ucl:.2f} mA")
        ax.axhline(lcl, color="#e74c3c", linewidth=1.2, linestyle="--", label=f"LCL ({sigma_k}σ): {lcl:.2f} mA")

        ax.fill_between(x, ucl, max(display_data.max(), ucl) * 1.05, alpha=0.07, color="#e74c3c")
        ax.fill_between(x, lcl, min(display_data.min(), lcl) * 0.95 if lcl > 0 else lcl - abs(lcl) * 0.05, alpha=0.07, color="#e74c3c")

        ax.set_xlabel("Test Count")
        ax.set_ylabel("Current (mA)")
        ax.set_title("SPC Control Chart — Current over Time")
        ax.legend(loc="upper right", fontsize=8, facecolor=bg_color, edgecolor=text_color, labelcolor=text_color)
        ax.grid(True, alpha=0.3)

        self._spc_cur_annot = ax.annotate(
            "", xy=(0, 0), xytext=(15, 15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#ffffcc", ec="#333333", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#333333"),
            fontsize=9, color="#1f2328", zorder=10,
        )
        self._spc_cur_annot.set_visible(False)

        if self._spc_cur_hover_cid is not None:
            self.spc_cur_canvas.mpl_disconnect(self._spc_cur_hover_cid)
        self._spc_cur_hover_cid = self.spc_cur_canvas.mpl_connect("motion_notify_event", self._on_spc_cur_hover)

        fig.tight_layout()
        self.spc_cur_canvas.draw()

        ooc_all = int(np.sum((all_data > ucl) | (all_data < lcl)))
        showing = f"Showing last {len(display_data)} of {len(all_data)}" if len(display_data) < len(all_data) else f"Showing all {len(all_data)}"
        self.spc_cur_stats_label.setText(
            f"{showing}    |    "
            f"Mean(Avg): {mean:.3f} mA    |    Std: {std:.3f} mA    |    "
            f"UCL: {ucl:.3f} mA    |    LCL: {lcl:.3f} mA    |    "
            f"Out-of-Control: {ooc_all}/{len(all_data)} ({ooc_all/len(all_data)*100:.1f}%)"
        )

    def _on_spc_cur_hover(self, event):
        """Show annotation tooltip for current chart."""
        if self._spc_cur_annot is None or self._spc_cur_scatter is None or self._spc_cur_data is None:
            return
        if event.inaxes is None:
            if self._spc_cur_annot.get_visible():
                self._spc_cur_annot.set_visible(False)
                self.spc_cur_canvas.draw_idle()
            return

        cont, ind = self._spc_cur_scatter.contains(event)
        if cont:
            idx = ind["ind"][0]
            val = float(self._spc_cur_data[idx])
            sample_num = idx + getattr(self, '_spc_cur_x_offset', 1)

            if val > self._spc_cur_ucl:
                status = "⚠ ABOVE UCL"
            elif val < self._spc_cur_lcl:
                status = "⚠ BELOW LCL"
            else:
                status = "✅ In Control"

            cat_label = self.spc_cur_category_combo.currentText()

            self._spc_cur_annot.xy = (sample_num, val)
            self._spc_cur_annot.set_text(
                f"Test Count #{sample_num}\n"
                f"Current: {val:.3f} mA\n"
                f"Category: {cat_label}\n"
                f"Status: {status}"
            )
            self._spc_cur_annot.set_visible(True)
            self.spc_cur_canvas.draw_idle()
        else:
            if self._spc_cur_annot.get_visible():
                self._spc_cur_annot.set_visible(False)
                self.spc_cur_canvas.draw_idle()

    def _draw_empty_spc_cur(self, message):
        """Show an empty current chart with a centered message."""
        fig = self.spc_cur_figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=14,
                transform=ax.transAxes, color="gray")
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout()
        self.spc_cur_canvas.draw()
        self.spc_cur_stats_label.setText("")

    def open_spc_chart_page(self):
        self.refresh_spc_chart()
        self.tabs.setCurrentWidget(self.page_spc_chart)
