from datetime import datetime

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QWidget, QFrame, QSizePolicy, QComboBox, QDoubleSpinBox,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ..helpers import make_scroll


class YieldPageMixin:
    """Mixin: Yield % page – pass/fail rates per category and overall."""

    def build_yield_page(self):
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(12)

        # ---- Header row ----
        header_row = QHBoxLayout()
        outer_layout.addLayout(header_row)

        title = QLabel("✅ Yield %")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        header_row.addWidget(title)

        header_row.addStretch(1)

        header_row.addWidget(QLabel("Data Source:"))
        self.yield_source_combo = QComboBox()
        self.yield_source_combo.addItems(["TestMax Pin", "Other Pin"])
        self.yield_source_combo.setMinimumWidth(140)
        self.yield_source_combo.currentIndexChanged.connect(self.refresh_yield_page)
        header_row.addWidget(self.yield_source_combo)

        self.btn_refresh_yield = QPushButton("🔄 Refresh")
        self.btn_refresh_yield.clicked.connect(self.refresh_yield_page)
        header_row.addWidget(self.btn_refresh_yield)

        # ---- Limit inputs row ----
        limits_row = QHBoxLayout()
        outer_layout.addLayout(limits_row)

        limits_row.addWidget(QLabel("LSL (Lower Spec Limit mΩ):"))
        self.yield_lsl_spin = QDoubleSpinBox()
        self.yield_lsl_spin.setRange(0, 99999)
        self.yield_lsl_spin.setDecimals(2)
        self.yield_lsl_spin.setValue(float(getattr(self, "close_circuit", 0) or 0))
        self.yield_lsl_spin.setMinimumWidth(120)
        self.yield_lsl_spin.valueChanged.connect(self.refresh_yield_page)
        limits_row.addWidget(self.yield_lsl_spin)

        limits_row.addWidget(QLabel("USL (Upper Spec Limit mΩ):"))
        self.yield_usl_spin = QDoubleSpinBox()
        self.yield_usl_spin.setRange(0, 99999)
        self.yield_usl_spin.setDecimals(2)
        self.yield_usl_spin.setValue(float(getattr(self, "open_circuit", 3000) or 3000))
        self.yield_usl_spin.setMinimumWidth(120)
        self.yield_usl_spin.valueChanged.connect(self.refresh_yield_page)
        limits_row.addWidget(self.yield_usl_spin)

        self.btn_yield_load_recipe_limits = QPushButton("Load Recipe Limits")
        self.btn_yield_load_recipe_limits.clicked.connect(self._yield_load_recipe_limits)
        limits_row.addWidget(self.btn_yield_load_recipe_limits)

        limits_row.addStretch(1)

        # ---- Context label ----
        self.yield_context_label = QLabel("Load a recipe and collect data to view yield metrics.")
        self.yield_context_label.setObjectName("summaryMeta")
        outer_layout.addWidget(self.yield_context_label)

        # ---- Overall yield card ----
        self.yield_overall_card = QFrame()
        self.yield_overall_card.setObjectName("summaryCard")
        self.yield_overall_card.setMinimumHeight(100)
        self.yield_overall_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.yield_overall_layout = QVBoxLayout(self.yield_overall_card)
        self.yield_overall_layout.setContentsMargins(18, 14, 18, 14)
        self.yield_overall_layout.setSpacing(6)
        outer_layout.addWidget(self.yield_overall_card)

        # ---- Yield bar chart ----
        self.yield_figure = Figure(figsize=(10, 3.5), dpi=100)
        self.yield_figure.patch.set_facecolor("none")
        self.yield_canvas = FigureCanvas(self.yield_figure)
        self.yield_canvas.setStyleSheet("background: transparent;")
        self.yield_canvas.setMinimumHeight(280)
        outer_layout.addWidget(self.yield_canvas)

        # ---- Per-category cards grid ----
        self.yield_cards_host = QWidget()
        self.yield_cards_layout = QGridLayout(self.yield_cards_host)
        self.yield_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.yield_cards_layout.setHorizontalSpacing(18)
        self.yield_cards_layout.setVerticalSpacing(18)

        scroll = make_scroll(self.yield_cards_host)
        scroll.setStyleSheet("background: transparent;")
        outer_layout.addWidget(scroll, 1)

        layout = QVBoxLayout(self.page_yield)
        layout.addWidget(outer)

    # =========================================================
    # Yield Logic
    # =========================================================

    def _yield_load_recipe_limits(self):
        """Reset LSL/USL spin boxes to the current recipe limits."""
        lsl = float(getattr(self, "close_circuit", 0) or 0)
        usl = float(getattr(self, "open_circuit", 3000) or 3000)
        self.yield_lsl_spin.blockSignals(True)
        self.yield_usl_spin.blockSignals(True)
        self.yield_lsl_spin.setValue(lsl)
        self.yield_usl_spin.setValue(usl)
        self.yield_lsl_spin.blockSignals(False)
        self.yield_usl_spin.blockSignals(False)
        self.refresh_yield_page()

    def _calc_yield_for_category(self, values, y_min_limit, y_max_limit):
        """Calculate pass/fail/yield for a list of resistance values."""
        if not values:
            return {"total": 0, "pass": 0, "fail": 0, "yield_pct": 0.0, "has_data": False}

        passed = sum(1 for v in values if y_min_limit <= v <= y_max_limit)
        failed = len(values) - passed
        yield_pct = (passed / len(values)) * 100.0 if values else 0.0

        return {
            "total": len(values),
            "pass": passed,
            "fail": failed,
            "yield_pct": yield_pct,
            "has_data": True,
        }

    def _build_yield_data(self):
        """Build yield stats for all active categories."""
        selected_categories = self._get_selected_categories_for_graph()
        if not selected_categories:
            inferred_steps = sorted(self.grouped_data.keys())
            selected_categories = [self.reverse_category_map.get(step, str(step)) for step in inferred_steps]

        y_min_limit = self.yield_lsl_spin.value()
        y_max_limit = self.yield_usl_spin.value()

        results = []
        for category in selected_categories:
            cat_value = None
            cat_label = str(category)

            if isinstance(category, int):
                cat_value = category
                cat_label = self.reverse_category_map.get(cat_value, f"CH{cat_value}")
            else:
                cat_value = self.category_map.get(str(category))
                if cat_value is None and str(category).isdigit():
                    cat_value = int(category)
                cat_label = str(category)

            cat_label = f"{cat_label} Contact"
            data_dict = self.grouped_data.get(cat_value, {}) if cat_value is not None else {}
            source = self.yield_source_combo.currentText()
            key = "resistance_tm" if source == "TestMax Pin" else "resistance_other"
            values = data_dict.get(key, [])
            yield_info = self._calc_yield_for_category(values, y_min_limit, y_max_limit)
            yield_info["label"] = cat_label
            results.append(yield_info)

        return results

    def _create_yield_card(self, info: dict) -> QFrame:
        """Create a card widget showing yield stats for one category."""
        card = QFrame()
        card.setObjectName("summaryCard")
        card.setMinimumSize(220, 180)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        title = QLabel(info["label"])
        title.setObjectName("summaryCardTitle")
        layout.addWidget(title)

        if not info["has_data"]:
            no_data = QLabel("No data")
            no_data.setObjectName("summaryMeta")
            layout.addWidget(no_data)
            layout.addStretch(1)
            return card

        # Yield % in large font with color
        pct = info["yield_pct"]
        color = "#2ecc71" if pct >= 95 else "#f39c12" if pct >= 80 else "#e74c3c"
        yield_lbl = QLabel(f"{pct:.1f}%")
        yield_lbl.setStyleSheet(f"font-size: 34px; font-weight: 700; color: {color};")
        yield_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(yield_lbl)

        details = QLabel(
            f"Total: {info['total']}    Pass: {info['pass']}    Fail: {info['fail']}"
        )
        details.setObjectName("summaryMeta")
        details.setAlignment(Qt.AlignCenter)
        layout.addWidget(details)

        layout.addStretch(1)
        return card

    def _clear_yield_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            cl = item.layout()
            if w is not None:
                w.deleteLater()
            elif cl is not None:
                self._clear_yield_layout(cl)

    def refresh_yield_page(self):
        """Refresh yield cards, overall banner, and bar chart."""
        yield_data = self._build_yield_data()

        # Update context
        config_name = getattr(self, "current_loaded_config_name", "") or "N/A"
        y_min = self.yield_lsl_spin.value()
        y_max = self.yield_usl_spin.value()
        self.yield_context_label.setText(
            f"Recipe: {config_name}    |    LSL: {y_min:.2f} mΩ    |    USL: {y_max:.2f} mΩ    |    "
            f"Updated: {datetime.now().strftime('%H:%M:%S')}"
        )

        # ---- Overall yield banner ----
        self._clear_yield_layout(self.yield_overall_layout)

        total_all = sum(d["total"] for d in yield_data)
        pass_all = sum(d["pass"] for d in yield_data)
        fail_all = sum(d["fail"] for d in yield_data)
        overall_pct = (pass_all / total_all * 100.0) if total_all > 0 else 0.0

        color = "#2ecc71" if overall_pct >= 95 else "#f39c12" if overall_pct >= 80 else "#e74c3c"

        overall_title = QLabel("Overall Yield")
        overall_title.setObjectName("summaryCardTitle")
        self.yield_overall_layout.addWidget(overall_title)

        row_layout = QHBoxLayout()
        pct_label = QLabel(f"{overall_pct:.1f}%")
        pct_label.setStyleSheet(f"font-size: 40px; font-weight: 800; color: {color};")
        row_layout.addWidget(pct_label)

        detail_label = QLabel(
            f"Total: {total_all:,}    |    Pass: {pass_all:,}    |    Fail: {fail_all:,}"
        )
        detail_label.setObjectName("summaryMeta")
        detail_label.setStyleSheet("font-size: 16px;")
        detail_label.setAlignment(Qt.AlignVCenter)
        row_layout.addWidget(detail_label)
        row_layout.addStretch(1)
        self.yield_overall_layout.addLayout(row_layout)

        # ---- Bar chart ----
        self._draw_yield_bar_chart(yield_data)

        # ---- Per-category cards ----
        self._clear_yield_layout(self.yield_cards_layout)
        for index, info in enumerate(yield_data):
            row = index // 3
            col = index % 3
            self.yield_cards_layout.addWidget(self._create_yield_card(info), row, col)

    def _draw_yield_bar_chart(self, yield_data):
        """Draw a horizontal bar chart of yield % per category."""
        fig = self.yield_figure
        fig.clear()

        categories_with_data = [d for d in yield_data if d["has_data"]]
        if not categories_with_data:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No yield data to display", ha="center", va="center",
                    fontsize=14, color="gray", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            fig.tight_layout()
            self.yield_canvas.draw()
            return

        ax = fig.add_subplot(111)

        # Theme-aware colors
        is_dark = getattr(self, 'current_theme', 'Light') == 'Dark'
        text_color = '#e6edf3' if is_dark else '#1f2328'
        bg_color = '#0d1117' if is_dark else '#ffffff'
        fig.patch.set_facecolor('none')
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=text_color)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.title.set_color(text_color)
        for spine in ax.spines.values():
            spine.set_edgecolor(text_color)

        labels = [d["label"] for d in categories_with_data]
        pcts = [d["yield_pct"] for d in categories_with_data]
        colors = ["#2ecc71" if p >= 95 else "#f39c12" if p >= 80 else "#e74c3c" for p in pcts]

        y_pos = np.arange(len(labels))
        bars = ax.barh(y_pos, pcts, color=colors, height=0.55, edgecolor="none")

        # Value labels on bars
        for bar, pct in zip(bars, pcts):
            ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                    f"{pct:.1f}%", va="center", fontsize=9, color=text_color)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9, color=text_color)
        ax.set_xlim(0, 105)
        ax.set_xlabel("Yield %")
        ax.set_title("Yield % by Category")
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        self.yield_canvas.draw()

    def open_yield_page(self):
        self.refresh_yield_page()
        self.tabs.setCurrentWidget(self.page_yield)
