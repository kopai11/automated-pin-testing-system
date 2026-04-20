from datetime import datetime

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QWidget, QFrame, QSizePolicy, QMessageBox, QFileDialog,
)

from ..helpers import make_scroll


class SummaryPageMixin:
    """Mixin: Summary dashboard page – cards, metrics, report export."""

    # -------------------------
    # Build Summary Page UI
    # -------------------------
    def build_summary_page(self):
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(12)

        header_row = QHBoxLayout()
        outer_layout.addLayout(header_row)

        title = QLabel("📋 Summary Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        header_row.addWidget(title)

        header_row.addStretch(1)

        self.btn_refresh_summary = QPushButton("Refresh Summary")
        self.btn_refresh_summary.clicked.connect(self.refresh_summary_page)
        header_row.addWidget(self.btn_refresh_summary)

        self.summary_context_label = QLabel("Load a recipe and collect data to view summary cards.")
        self.summary_context_label.setObjectName("summaryMeta")
        outer_layout.addWidget(self.summary_context_label)

        self.summary_cards_host = QWidget()
        self.summary_cards_layout = QGridLayout(self.summary_cards_host)
        self.summary_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_cards_layout.setHorizontalSpacing(18)
        self.summary_cards_layout.setVerticalSpacing(18)

        scroll = make_scroll(self.summary_cards_host)
        scroll.setStyleSheet("background: transparent;")
        outer_layout.addWidget(scroll, 1)

        layout = QVBoxLayout(self.page_summary)
        layout.addWidget(outer)

    # =========================================================
    # Summary Logic
    # =========================================================

    def _clear_layout_widgets(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout_widgets(child_layout)

    def _resolve_category_info(self, category):
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
        return cat_value, cat_label

    def _calc_summary_metrics(self, values, display_mode, y_min_limit, y_max_limit):
        if not values:
            return {
                "count": 0,
                "avg": 0.0,
                "max": 0.0,
                "min": 0.0,
                "std": 0.0,
                "upper": 0.0,
                "has_data": False,
            }

        processed_data = []
        for y in values:
            clamped_y = max(y, y_min_limit)
            clamped_y = min(clamped_y, y_max_limit)
            processed_data.append(clamped_y)

        if display_mode == "Cut_off beyond limit data":
            data_to_report = [y for y in processed_data if (y_min_limit < y < y_max_limit)]
        else:
            data_to_report = processed_data

        if not data_to_report:
            return {
                "count": 0,
                "avg": 0.0,
                "max": 0.0,
                "min": 0.0,
                "std": 0.0,
                "upper": 0.0,
                "has_data": False,
            }

        data_np = np.array(data_to_report, dtype=float)
        avg_rvalue = float(np.mean(data_np))
        return {
            "count": len(data_to_report),
            "avg": avg_rvalue,
            "max": float(np.max(data_np)),
            "min": float(np.min(data_np)),
            "std": float(np.std(data_np)),
            "upper": float(avg_rvalue + (avg_rvalue * 0.20)),
            "has_data": True,
        }

    def _build_summary_stats(self):
        selected_categories = self._get_selected_categories_for_graph()
        if not selected_categories:
            inferred_steps = sorted(self.grouped_data.keys())
            selected_categories = [self.reverse_category_map.get(step, str(step)) for step in inferred_steps]

        display_mode = getattr(self, "display_mode", "Display All_data")
        y_min_limit = float(getattr(self, "close_circuit", 0))
        y_max_limit = float(getattr(self, "open_circuit", 3000))

        summaries = []
        for category in selected_categories:
            cat_value, cat_label = self._resolve_category_info(category)
            data_dict = self.grouped_data.get(cat_value, {}) if cat_value is not None else {}
            tm_data = data_dict.get("resistance_tm", [])
            other_data = data_dict.get("resistance_other", []) if data_dict.get("has_other", False) else []

            tm_stats = self._calc_summary_metrics(tm_data, display_mode, y_min_limit, y_max_limit)
            other_stats = self._calc_summary_metrics(other_data, display_mode, y_min_limit, y_max_limit)

            summary = {
                "label": cat_label,
                "comparison_mode": bool(other_stats["has_data"]),
                "tm": tm_stats,
                "other": other_stats,
                "count": tm_stats["count"],
                "avg": tm_stats["avg"],
                "max": tm_stats["max"],
                "min": tm_stats["min"],
                "std": tm_stats["std"],
                "upper": tm_stats["upper"],
                "has_data": tm_stats["has_data"],
            }

            summaries.append(summary)

        return summaries

    def _create_summary_card(self, summary: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("summaryCard")
        card.setMinimumSize(250, 260)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel(summary["label"])
        title.setObjectName("summaryCardTitle")
        layout.addWidget(title)

        tm = summary.get("tm", {})
        other = summary.get("other", {})
        comparison_mode = bool(summary.get("comparison_mode", False))

        if comparison_mode:
            mode_label = QLabel("Comparison Mode: TestMax(TM) vs Other Pin")
            mode_label.setObjectName("summaryMeta")
            layout.addWidget(mode_label)

            count_label = QLabel("Test Count")
            count_label.setObjectName("summaryMetricLabel")
            count_value = QLabel(f"{tm.get('count', 0):,}")
            count_value.setObjectName("summaryMetricValue")
            layout.addWidget(count_label)
            layout.addWidget(count_value)

            for metric_label, tm_value, other_value in (
                ("Max Resistance (mΩ)", f"{tm.get('max', 0.0):.2f}", f"{other.get('max', 0.0):.2f}"),
                ("Min Resistance (mΩ)", f"{tm.get('min', 0.0):.2f}", f"{other.get('min', 0.0):.2f}"),
            ):
                label = QLabel(metric_label)
                label.setObjectName("summaryMetricLabel")
                value = QLabel(f"TM: {tm_value}    |    Other: {other_value}")
                value.setObjectName("summaryMetricValue")
                layout.addWidget(label)
                layout.addWidget(value)

            meta_text = (
                f"TM Avg: {tm.get('avg', 0.0):.2f} mΩ   |   Other Avg: {other.get('avg', 0.0):.2f} mΩ\n"
                f"TM Std: {tm.get('std', 0.0):.2f} mΩ   |   Other Std: {other.get('std', 0.0):.2f} mΩ\n"
                f"TM Upper Limit: {tm.get('upper', 0.0):.2f} mΩ   |   Other Upper Limit: {other.get('upper', 0.0):.2f} mΩ"
            )
        else:
            for metric_label, metric_value in (
                ("Test Count", f"{summary['count']:,}"),
                ("Max Resistance (mΩ)", f"{summary['max']:.2f}"),
                ("Min Resistance (mΩ)", f"{summary['min']:.2f}"),
            ):
                label = QLabel(metric_label)
                label.setObjectName("summaryMetricLabel")
                value = QLabel(metric_value)
                value.setObjectName("summaryMetricValue")
                layout.addWidget(label)
                layout.addWidget(value)

            meta_text = (
                f"Avg Resistance: {summary['avg']:.2f} mΩ    Std: {summary['std']:.2f} mΩ\n"
                f"Upper Limit: {summary['upper']:.2f} mΩ"
            ) if summary["has_data"] else "No test data available for this category yet."

        meta = QLabel(meta_text)
        meta.setObjectName("summaryMeta")
        meta.setWordWrap(True)
        layout.addWidget(meta)
        layout.addStretch(1)

        return card

    def refresh_summary_page(self):
        if not hasattr(self, "summary_cards_layout"):
            return

        self._clear_layout_widgets(self.summary_cards_layout)

        summaries = self._build_summary_stats()
        config_name = getattr(self, "current_loaded_config_name", "") or "No recipe loaded"
        operator_name = self.operator_name.text().strip() if hasattr(self, "operator_name") else ""
        operator_text = operator_name or "N/A"
        self.summary_context_label.setText(
            f"Recipe: {config_name}    |    Operator: {operator_text}    |    Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if not summaries:
            empty = QLabel("No summary data available.\n👈 Go to the Operator tab, Load a recipe and start monitoring first.")
            empty.setObjectName("summaryMeta")
            empty.setStyleSheet("font-size: 22px;")
            empty.setAlignment(Qt.AlignCenter)
            empty.setWordWrap(True)
            self.summary_cards_layout.addWidget(empty, 0, 0)
            return

        for index, summary in enumerate(summaries):
            row = index // 3
            col = index % 3
            self.summary_cards_layout.addWidget(self._create_summary_card(summary), row, col)

    def open_summary_page(self):
        self.refresh_summary_page()
        self.tabs.setCurrentWidget(self.page_summary)

    def report_summary(self):
        if not getattr(self, "current_loaded_config_name", ""):
            QMessageBox.warning(self, "Warning", "No configuration loaded in Operator mode.")
            return

        config_name = self.current_loaded_config_name
        operator_name = self.operator_name.text().strip() if hasattr(self, "operator_name") else ""

        summaries = self._build_summary_stats()

        if not summaries:
            QMessageBox.warning(self, "Warning", "No category is selected to generate report.")
            return

        report_content = f"Test Summary Report of {config_name}\n\n"

        for summary in summaries:
            report_content += f"Category : {summary['label']}\n"
            report_content += "=====================================\n"

            if summary["has_data"]:
                report_content += f"Test Count : {summary['count']}\n"
                report_content += f"Minimum R-Value: {summary['min']:.2f} mΩ\n"
                report_content += f"maximum R-value: {summary['max']:.2f} mΩ\n"
                report_content += f"Average R-value: {summary['avg']:.2f} mΩ\n"
                report_content += f"Upper_limit : {summary['upper']:.2f} mΩ\n"
                report_content += f"Standard Deviation: {summary['std']:.2f} mΩ\n"
            else:
                report_content += "No data available for the category.\n"

            report_content += "\n\n"

        report_content += f"Test is done by '{operator_name}'"
        report_content += f"\nStarted Time: {getattr(self, 'start_time', '')} "
        end_time = datetime.now().strftime("%Y-%m-%d / %H:%M:%S")
        report_content += f"\nFinished time: {end_time}"

        timer_string = f"{self.days:02d}Days-{self.hours:02d}Hr-{self.minutes:02d}Min-{self.seconds:02d}Sec"
        report_content += f"\nTotal time: {timer_string}"

        default_filename = f"{config_name}_summary_report.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Summary Report",
            default_filename,
            "Text files (*.txt);;All Files (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            QMessageBox.information(self, "Success", f"Summary_report saved to \n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to write report_summary file: {e}")
