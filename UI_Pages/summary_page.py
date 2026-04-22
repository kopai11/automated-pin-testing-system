import csv
import os
from datetime import datetime

import numpy as np

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.helpers import make_scroll


class SummaryPageMixin:
    """Mixin: Summary dashboard page - cards, metrics, report export."""

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
        for value in values:
            clamped_value = max(value, y_min_limit)
            clamped_value = min(clamped_value, y_max_limit)
            processed_data.append(clamped_value)

        if display_mode == "Cut_off beyond limit data":
            data_to_report = [value for value in processed_data if (y_min_limit < value < y_max_limit)]
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

            summaries.append({
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
            })

        return summaries

    def _calc_basic_metrics(self, values):
        if not values:
            return {
                "count": 0,
                "avg": 0.0,
                "max": 0.0,
                "min": 0.0,
                "std": 0.0,
                "has_data": False,
            }

        data_np = np.array(values, dtype=float)
        return {
            "count": len(values),
            "avg": float(np.mean(data_np)),
            "max": float(np.max(data_np)),
            "min": float(np.min(data_np)),
            "std": float(np.std(data_np)),
            "has_data": True,
        }

    def _build_metric_summary_stats(self, tm_key: str, other_key: str):
        selected_categories = self._get_selected_categories_for_graph()
        if not selected_categories:
            inferred_steps = sorted(self.grouped_data.keys())
            selected_categories = [self.reverse_category_map.get(step, str(step)) for step in inferred_steps]

        summaries = []
        for category in selected_categories:
            cat_value, cat_label = self._resolve_category_info(category)
            data_dict = self.grouped_data.get(cat_value, {}) if cat_value is not None else {}
            tm_data = data_dict.get(tm_key, [])

            tm_stats = self._calc_basic_metrics(tm_data)

            summaries.append({
                "label": cat_label,
                "comparison_mode": False,
                "tm": tm_stats,
                "other": self._calc_basic_metrics([]),
                "count": tm_stats["count"],
                "avg": tm_stats["avg"],
                "max": tm_stats["max"],
                "min": tm_stats["min"],
                "std": tm_stats["std"],
                "has_data": tm_stats["has_data"],
            })

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

    def _sanitize_report_name(self, value: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (value or "").strip())
        safe = safe.strip("_")
        return safe or "report"

    def _get_report_metadata(self):
        cfg = self._get_active_config() if hasattr(self, "_get_active_config") else {}

        categories = cfg.get("categories", [])
        if isinstance(categories, dict):
            selected_categories = [cat for cat, enabled in categories.items() if enabled]
        elif isinstance(categories, list):
            selected_categories = list(categories)
        else:
            selected_categories = self._get_selected_categories_for_graph()

        test_types = cfg.get("measure_cat", cfg.get("test_type", []))
        if isinstance(test_types, dict):
            selected_test_types = [name for name, enabled in test_types.items() if enabled]
        elif isinstance(test_types, list):
            selected_test_types = list(test_types)
        else:
            selected_test_types = []

        return {
            "recipe_name": getattr(self, "current_loaded_config_name", "") or "N/A",
            "project_name": cfg.get("project_name", "") or "N/A",
            "pin_fixture": cfg.get("pin_fixture", "") or "N/A",
            "engineer": cfg.get("Engineer", "Unknown"),
            "created_time": cfg.get("Created_time", "N/A"),
            "data_file": getattr(self, "file_path", None) or cfg.get("file_path", "N/A"),
            "display_mode": getattr(self, "display_mode", cfg.get("display_mode", "Display All_data")),
            "y_axis_max": getattr(self, "y_max", cfg.get("yAxis_max", cfg.get("y_axis_max", "N/A"))),
            "open_circuit": float(getattr(self, "open_circuit", cfg.get("open_circuit", cfg.get("y_max", 3000))) or 0),
            "close_circuit": float(getattr(self, "close_circuit", cfg.get("close_circuit", cfg.get("y_min", 0))) or 0),
            "categories": selected_categories,
            "test_types": selected_test_types,
        }

    def _build_report_yield_snapshot(self, key: str, y_min_limit: float, y_max_limit: float):
        results = []
        total_all = 0
        pass_all = 0
        fail_all = 0

        selected_categories = self._get_selected_categories_for_graph()
        if not selected_categories:
            inferred_steps = sorted(self.grouped_data.keys())
            selected_categories = [self.reverse_category_map.get(step, str(step)) for step in inferred_steps]

        for category in selected_categories:
            cat_value, cat_label = self._resolve_category_info(category)
            data_dict = self.grouped_data.get(cat_value, {}) if cat_value is not None else {}
            values = data_dict.get(key, [])
            yield_info = self._calc_yield_for_category(values, y_min_limit, y_max_limit)
            yield_info["label"] = cat_label
            results.append(yield_info)
            total_all += yield_info["total"]
            pass_all += yield_info["pass"]
            fail_all += yield_info["fail"]

        overall_pct = (pass_all / total_all * 100.0) if total_all > 0 else 0.0
        return results, {
            "total": total_all,
            "pass": pass_all,
            "fail": fail_all,
            "yield_pct": overall_pct,
            "has_data": total_all > 0,
        }

    def _build_report_export_data(self):
        metadata = self._get_report_metadata()
        config_name = metadata["recipe_name"]
        operator_name = self.operator_name.text().strip() if hasattr(self, "operator_name") else ""
        summaries = self._build_summary_stats()
        current_summaries = self._build_metric_summary_stats("current_tm", "current_other")
        if not summaries:
            return None

        end_time = datetime.now().strftime("%Y-%m-%d / %H:%M:%S")
        timer_string = f"{self.days:02d}Days-{self.hours:02d}Hr-{self.minutes:02d}Min-{self.seconds:02d}Sec"
        tm_yield_rows, tm_overall_yield = self._build_report_yield_snapshot(
            "resistance_tm",
            metadata["close_circuit"],
            metadata["open_circuit"],
        )

        has_other = any(summary.get("comparison_mode", False) for summary in summaries)
        other_yield_rows = []
        other_overall_yield = None
        if has_other:
            other_yield_rows, other_overall_yield = self._build_report_yield_snapshot(
                "resistance_other",
                metadata["close_circuit"],
                metadata["open_circuit"],
            )

        return {
            "metadata": metadata,
            "config_name": config_name,
            "operator_name": operator_name,
            "summaries": summaries,
            "current_summaries": current_summaries,
            "end_time": end_time,
            "timer_string": timer_string,
            "tm_yield_rows": tm_yield_rows,
            "tm_overall_yield": tm_overall_yield,
            "other_yield_rows": other_yield_rows,
            "other_overall_yield": other_overall_yield,
        }

    def _build_report_text(self, report_data: dict) -> str:
        metadata = report_data["metadata"]
        config_name = report_data["config_name"]
        summaries = report_data["summaries"]
        current_summaries = report_data["current_summaries"]
        tm_yield_rows = report_data["tm_yield_rows"]
        tm_overall_yield = report_data["tm_overall_yield"]
        other_yield_rows = report_data["other_yield_rows"]
        other_overall_yield = report_data["other_overall_yield"]

        def kv(label: str, value: str) -> str:
            return f"{label:<14} : {value}"

        report_lines = [
            "=" * 70,
            "█  POGO PIN DURABILITY TEST: EXECUTIVE SUMMARY REPORT  █",
            "=" * 70,
            "",
            "█ TEST INFORMATION",
            "-" * 70,
            kv("Recipe Name", config_name),
            kv("Project Number", str(metadata["project_name"])),
            kv("Pin Fixture", str(metadata["pin_fixture"])),
            kv("Operator", report_data["operator_name"] or "N/A"),
            kv("Engineer", str(metadata["engineer"])),
            kv("Source Data File", str(metadata["data_file"])),
            kv("Categories", ", ".join(metadata["categories"]) if metadata["categories"] else "N/A"),
            kv("Test Types", ", ".join(metadata["test_types"]) if metadata["test_types"] else "N/A"),
            kv("Started Time", getattr(self, "start_time", "") or "N/A"),
            kv("Finished Time", report_data["end_time"]),
            kv("Total Duration", report_data["timer_string"]),
            "",
            "█ RESISTANCE DATA",
            "-" * 70,
            "",
        ]

        for summary in summaries:
            count_text = f"{summary.get('count', 0):,}"
            report_lines.append(f"Category: {summary['label']} (Test Count : {count_text})")
            report_lines.append("| Pin Source    | Min (mΩ) | Max (mΩ) | Avg (mΩ) | Std Dev (mΩ) |")
            report_lines.append("|---------------|----------|----------|----------|---------------|")

            if summary.get("comparison_mode", False):
                tm = summary.get("tm", {})
                other = summary.get("other", {})
                report_lines.append(
                    f"| TestMax Pin   | {tm.get('min', 0.0):>8.2f} | {tm.get('max', 0.0):>8.2f} | {tm.get('avg', 0.0):>8.2f} | {tm.get('std', 0.0):>13.2f} |"
                )
                report_lines.append(
                    f"| Other Pin     | {other.get('min', 0.0):>8.2f} | {other.get('max', 0.0):>8.2f} | {other.get('avg', 0.0):>8.2f} | {other.get('std', 0.0):>13.2f} |"
                )
            elif summary.get("has_data", False):
                report_lines.append(
                    f"| TestMax Pin   | {summary['min']:>8.2f} | {summary['max']:>8.2f} | {summary['avg']:>8.2f} | {summary['std']:>13.2f} |"
                )
            else:
                report_lines.append("| TestMax Pin   |      N/A |      N/A |      N/A |           N/A |")

            report_lines.append("")

        report_lines.append("")
        report_lines.append("█ CURRENT DATA")
        report_lines.append("-" * 70)
        report_lines.append("")

        for summary in current_summaries:
            count_text = f"{summary.get('count', 0):,}"
            report_lines.append(f"Category: {summary['label']} (Test Count : {count_text})")
            report_lines.append("| Pin Source    | Min (A)  | Max (A)  | Avg (A)  | Std Dev (A)   |")
            report_lines.append("|---------------|----------|----------|----------|---------------|")

            if summary.get("has_data", False):
                report_lines.append(
                    f"| Current       | {summary['min']:>8.4f} | {summary['max']:>8.4f} | {summary['avg']:>8.4f} | {summary['std']:>13.4f} |"
                )
            else:
                report_lines.append("| Current       |      N/A |      N/A |      N/A |           N/A |")

            report_lines.append("")

        report_lines.append("")
        report_lines.append("█ OVERALL YIELD SUMMARY")
        report_lines.append("-" * 70)
        report_lines.append(
            f"TestMax Pin      : {tm_overall_yield['yield_pct']:.1f}%  |  Total={tm_overall_yield['total']:,}  Pass={tm_overall_yield['pass']:,}  Fail={tm_overall_yield['fail']:,}"
        )

        if other_overall_yield is not None:
            report_lines.append("")
            report_lines.append(
                f"Other Pin        : {other_overall_yield['yield_pct']:.1f}%  |  Total={other_overall_yield['total']:,}  Pass={other_overall_yield['pass']:,}  Fail={other_overall_yield['fail']:,}"
            )

        report_lines.append("")
        report_lines.append("")

        other_by_label = {row["label"]: row for row in other_yield_rows}
        for tm_row in tm_yield_rows:
            label = tm_row["label"]
            other_row = other_by_label.get(label, {"pass": 0, "fail": 0, "total": 0}) if other_overall_yield is not None else None
            count_text = f"{tm_row['total']:,}"
            report_lines.append(f"Category: {label} (Test Count : {count_text})")
            report_lines.append("| Pin Source     | Pass     | Fail     | Total     |")
            report_lines.append("|----------------|----------|----------|-----------|")
            report_lines.append(
                f"| TestMax Pin    | {tm_row['pass']:>8} | {tm_row['fail']:>8} | {tm_row['total']:>9} |"
            )

            if other_row is not None:
                report_lines.append(
                    f"| Other Pin      | {other_row['pass']:>8} | {other_row['fail']:>8} | {other_row['total']:>9} |"
                )

            report_lines.append("")

        report_lines.append("")

        report_lines.append("_End of Executive Report. See Raw_Data.csv for full analysis._")
        return "\n".join(report_lines) + "\n"

    def _build_report_csv_rows(self, report_data: dict):
        summaries = report_data["summaries"]
        current_summaries = report_data["current_summaries"]
        tm_yield_rows = report_data["tm_yield_rows"]
        tm_overall_yield = report_data["tm_overall_yield"]
        other_yield_rows = report_data["other_yield_rows"]
        other_overall_yield = report_data["other_overall_yield"]

        rows = [
            ["Category", "Mode", "Count", "Minimum (mΩ)", "Maximum (mΩ)", "Average (mΩ)", "Std Dev (mΩ)", "Upper Limit (mΩ)", "Pin Source"],
        ]

        for summary in summaries:
            if summary.get("comparison_mode", False):
                tm = summary.get("tm", {})
                other = summary.get("other", {})
                rows.append([summary["label"], "Comparison", tm.get("count", 0), f"{tm.get('min', 0.0):.2f}", f"{tm.get('max', 0.0):.2f}", f"{tm.get('avg', 0.0):.2f}", f"{tm.get('std', 0.0):.2f}", f"{tm.get('upper', 0.0):.2f}", "TestMax Pin"])
                rows.append([summary["label"], "Comparison", other.get("count", 0), f"{other.get('min', 0.0):.2f}", f"{other.get('max', 0.0):.2f}", f"{other.get('avg', 0.0):.2f}", f"{other.get('std', 0.0):.2f}", f"{other.get('upper', 0.0):.2f}", "Other Pin"])
            elif summary["has_data"]:
                rows.append([summary["label"], "TestMax only", summary["count"], f"{summary['min']:.2f}", f"{summary['max']:.2f}", f"{summary['avg']:.2f}", f"{summary['std']:.2f}", f"{summary['upper']:.2f}", "TestMax Pin"])
            else:
                rows.append([summary["label"], "No data", 0, "", "", "", "", "", "TestMax Pin"])

        rows.extend([
            [],
            ["Current Category", "Mode", "Count", "Minimum (A)", "Maximum (A)", "Average (A)", "Std Dev (A)", "Pin Source"],
        ])

        for summary in current_summaries:
            if summary["has_data"]:
                rows.append([summary["label"], "Current", summary["count"], f"{summary['min']:.4f}", f"{summary['max']:.4f}", f"{summary['avg']:.4f}", f"{summary['std']:.4f}", "Current"])
            else:
                rows.append([summary["label"], "No data", 0, "", "", "", "", "Current"])

        rows.extend([
            [],
            ["Yield", "Scope", "Yield %", "Total", "Pass", "Fail"],
            ["Yield", "TestMax Pin Overall", f"{tm_overall_yield['yield_pct']:.1f}", tm_overall_yield["total"], tm_overall_yield["pass"], tm_overall_yield["fail"]],
        ])
        for row in tm_yield_rows:
            rows.append(["Yield", row["label"], f"{row['yield_pct']:.1f}", row["total"], row["pass"], row["fail"]])

        if other_overall_yield is not None:
            rows.append(["Yield", "Other Pin Overall", f"{other_overall_yield['yield_pct']:.1f}", other_overall_yield["total"], other_overall_yield["pass"], other_overall_yield["fail"]])
            for row in other_yield_rows:
                rows.append(["Yield", row["label"] + " (Other Pin)", f"{row['yield_pct']:.1f}", row["total"], row["pass"], row["fail"]])

        return rows

    def report_summary(self):
        if not getattr(self, "current_loaded_config_name", ""):
            QMessageBox.warning(self, "Warning", "No configuration loaded in Operator mode.")
            return

        report_data = self._build_report_export_data()
        if not report_data:
            QMessageBox.warning(self, "Warning", "No category is selected to generate report.")
            return

        txt_content = self._build_report_text(report_data)
        csv_rows = self._build_report_csv_rows(report_data)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_recipe_name = self._sanitize_report_name(report_data["config_name"])
        safe_operator_name = self._sanitize_report_name(report_data["operator_name"] or "operator")

        format_dialog = QMessageBox(self)
        format_dialog.setWindowTitle("Choose Report Format")
        format_dialog.setText("Choose (.txt) for Docs or (.csv) for Excel:")

        btn_txt = format_dialog.addButton(".txt", QMessageBox.AcceptRole)
        btn_csv = format_dialog.addButton(".csv", QMessageBox.AcceptRole)
        btn_cancel = format_dialog.addButton(QMessageBox.Cancel)
        format_dialog.setDefaultButton(btn_txt)
        format_dialog.exec()

        clicked = format_dialog.clickedButton()
        if clicked == btn_cancel or clicked is None:
            return

        is_csv = clicked == btn_csv
        report_dir = getattr(
            self,
            "report_save_folder",
            r"C:\Users\HDD 205\Desktop\Pogo_Pin Quality_Test_ Data\Report",
        )
        os.makedirs(report_dir, exist_ok=True)

        ext = "csv" if is_csv else "txt"
        default_filename = f"{safe_recipe_name}_{safe_operator_name}_{timestamp}_summary_report.{ext}"
        default_path = os.path.join(report_dir, default_filename)
        file_filter = "CSV files (*.csv)" if is_csv else "Text files (*.txt)"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Summary Report",
            default_path,
            file_filter,
        )

        if not file_path:
            return

        if is_csv and not file_path.lower().endswith(".csv"):
            file_path += ".csv"
        if not is_csv and not file_path.lower().endswith(".txt"):
            file_path += ".txt"

        try:
            if is_csv:
                with open(file_path, "w", encoding="utf-8-sig", newline="") as file_obj:
                    writer = csv.writer(file_obj)
                    writer.writerows(csv_rows)
                QMessageBox.information(self, "Success", f"Summary CSV exported to\n{file_path}")
            else:
                with open(file_path, "w", encoding="utf-8") as file_obj:
                    file_obj.write(txt_content)
                QMessageBox.information(self, "Success", f"Summary report saved to\n{file_path}")
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Failed to save summary report: {error}")
