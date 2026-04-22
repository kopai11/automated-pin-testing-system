import json
import os
from datetime import datetime

from PySide6.QtWidgets import QMessageBox, QFileDialog

from .helpers import info, warn


class ConfigMixin:
    """Mixin: Recipe/configuration save, load, delete, and operator-page loader."""

    def load_saved_configs(self):
        try:
            if os.path.exists(self.configs_file):
                with open(self.configs_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}

    def update_config_combobox(self):
        names = sorted(self.saved_configs.keys())
        self.config_combo.clear()
        self.config_combo.addItems(names)

    def load_config_operator(self):
        name = self.config_combo.currentText().strip()
        if not name:
            warn(self, "Warning", "Please select a Test_Program!")
            return

        self.current_loaded_config_name = name
        config = self.saved_configs.get(name, {})

        cats_raw = config.get("categories", [])
        if isinstance(cats_raw, dict):
            selected_categories = [cat for cat, enabled in cats_raw.items() if enabled]
        elif isinstance(cats_raw, list):
            selected_categories = list(cats_raw)
        else:
            selected_categories = []

        types_raw = config.get("measure_cat", config.get("test_type", []))
        if isinstance(types_raw, dict):
            selected_types = [t for t, enabled in types_raw.items() if enabled]
        elif isinstance(types_raw, list):
            selected_types = list(types_raw)
        else:
            selected_types = []

        y_max = config.get("yAxis_max", config.get("y_axis_max", "N/A"))
        open_circuit = config.get("open_circuit", config.get("y_max", "N/A"))
        close_circuit = config.get("close_circuit", config.get("y_min", "N/A"))

        details = [f"Recipe/TestProgram name: {name}"]
        details.append(f"\nPart number/Project number: {config.get('project_name','') or 'N/A'}")
        details.append(f"Pin_fixture: {config.get('pin_fixture','') or 'N/A'}")
        details.append(f"\nData File: {config.get('file_path','N/A')}")

        details.append("\nGraph Settings:")
        details.append(f"  • Max R-Value: {y_max} mΩ (Y-axis)")
        details.append(f"  • Open-Circuit: {open_circuit} mΩ")
        details.append(f"  • Close-Circuit: {close_circuit} mΩ")

        details.append("\nSelected Categories:")
        if selected_categories:
            for c in selected_categories:
                details.append(f"  • {c}")
        else:
            details.append("  • None (default will be used)")

        details.append("\nTest type:")
        if selected_types:
            for t in selected_types:
                details.append(f"  • {t}")
        else:
            details.append("  • None (default will be used)")

        details.append(f"\nDisplay Mode: {config.get('display_mode', 'Display All_data')}")
        details.append(f"\nRecipe was Created by Engineer: {config.get('Engineer','Unknown')}")
        details.append(f"Created_time : {config.get('Created_time','N/A')}")

        self.details_text.setPlainText("\n".join(details))

        self.file_path = config.get("file_path", None)
        self.btn_start.setEnabled(True)

    def update_configs_list_widget(self):
        self.list_configs.clear()
        for name in sorted(self.saved_configs.keys()):
            self.list_configs.addItem(name)

    def save_configuration_qt(self):
        name = self.ed_config_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter Recipe/Test-program Name.")
            return

        cfg = {
            "project_name": self.ed_project_name.text().strip(),
            "file_path": self.ed_file_path.text().strip(),
            "pin_fixture": self.ed_pin_fixture.text().strip(),
            "measure_cat": self._get_selected_test_types(),
            "display_mode": self._get_display_mode_text(),
            "yAxis_max": int(self.ed_yaxis_max.text() or "20"),
            "open_circuit": int(self.ed_open_circuit.text() or "3000"),
            "close_circuit": int(self.ed_close_circuit.text() or "0"),
            "categories": self._get_selected_categories(),
            "Engineer": self.Engineer_name,
            "Created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        self.saved_configs[name] = cfg

        try:
            with open(self.configs_file, "w", encoding="utf-8") as f:
                json.dump(self.saved_configs, f, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configs JSON: {e}")
            return

        self.update_configs_list_widget()
        self.update_config_combobox()
        QMessageBox.information(self, "Saved", f"Saved config: {name}")

    def save_config_details_from_setting_qt(self):
        """Get selected config from the list, format details, and save to a .txt file."""
        config_name = self._selected_config_name_from_list()
        if not config_name:
            QMessageBox.warning(self, "Warning", "Please select a Test_Program from the list to save details for.")
            return

        if config_name not in self.saved_configs:
            QMessageBox.warning(self, "Error", f"Configuration '{config_name}' not found.")
            return

        config = self.saved_configs[config_name]

        cats_raw = config.get("categories", [])
        if isinstance(cats_raw, dict):
            selected_cats = [cat for cat, val in cats_raw.items() if val]
        elif isinstance(cats_raw, list):
            selected_cats = list(cats_raw)
        else:
            selected_cats = []

        types_raw = config.get("measure_cat", config.get("test_type", []))
        if isinstance(types_raw, dict):
            selected_types = [t for t, val in types_raw.items() if val]
        elif isinstance(types_raw, list):
            selected_types = list(types_raw)
        else:
            selected_types = []

        y_axis_max  = config.get("yAxis_max", config.get("y_axis_max", "N/A"))
        open_circ   = config.get("open_circuit", config.get("y_max", "N/A"))
        close_circ  = config.get("close_circuit", config.get("y_min", "N/A"))

        project_num = config.get("project_name", "") or "N/A"
        pin_fixture = config.get("pin_fixture", "") or "N/A"
        display_mode = config.get("display_mode", "Display All_data")
        engineer    = config.get("Engineer", "Unknown")
        created     = config.get("Created_time", "N/A")

        details = ""
        details += f"Recipe/TestProgram name: {config_name}\n"
        details += f"\nPart number/Project number: {project_num}\n"
        details += f"Pin_fixture: {pin_fixture}\n"

        details += "\nGraph Settings:\n"
        details += f"  • R-value Maximum: {y_axis_max} mΩ (Y-axis)\n"
        details += f"  • Open-Circuit: {open_circ} mΩ\n"
        details += f"  • Close-Circuit: {close_circ} mΩ\n"

        details += "\nSelected Categories:\n"
        if selected_cats:
            for cat in selected_cats:
                details += f"  • {cat}\n"
        else:
            details += "  • None (default will be used)\n"

        details += "\nTest type:\n"
        if selected_types:
            for t in selected_types:
                details += f"  • {t}\n"
        else:
            details += "  • None (default will be used)\n"

        details += f"\nDisplay Mode: {display_mode}\n"
        details += f"\nRecipe was Created by Engineer: {engineer}\n"
        details += f"Created_time : {created}\n"

        default_filename = f"{config_name}_Test_Config_details.txt"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Test Config Details",
            default_filename,
            "Text files (*.txt);;All Files (*)"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(details)
            QMessageBox.information(self, "Saved", f"Details saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save details:\n{e}")

    def _selected_config_name_from_list(self):
        return self.list_configs.currentText().strip()

    def load_configuration_qt(self):
        name = self._selected_config_name_from_list()
        if not name:
            QMessageBox.warning(self, "Warning", "Please select a config to load.")
            return

        cfg = self.saved_configs.get(name, {})
        self.ed_config_name.setText(name)
        self.ed_project_name.setText(cfg.get("project_name", ""))
        self.ed_pin_fixture.setText(cfg.get("pin_fixture", ""))

        selected = set(cfg.get("measure_cat", []))
        for k, cb in self.measure_cat_checks.items():
            cb.setChecked(k in selected)

        mode = cfg.get("display_mode", "Display All_data")
        self.rb_all_data.setChecked(mode == "Display All_data")
        self.rb_cutoff.setChecked(mode != "Display All_data")

        self.ed_yaxis_max.setText(str(cfg.get("yAxis_max", 20)))
        self.ed_open_circuit.setText(str(cfg.get("open_circuit", 3000)))
        self.ed_close_circuit.setText(str(cfg.get("close_circuit", 0)))

        selected_cat = set(cfg.get("categories", []))
        for k, cb in self.category_checks.items():
            cb.setChecked(k in selected_cat)

        QMessageBox.information(self, "Loaded", f"Loaded config: {name}")

    def delete_configuration_qt(self):
        name = self._selected_config_name_from_list()
        if not name:
            QMessageBox.warning(self, "Warning", "Select a recipe to delete.")
            return

        reply = QMessageBox.question(
            self, "Delete Recipe",
            f"Delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.saved_configs.pop(name, None)
        try:
            with open(self.configs_file, "w", encoding="utf-8") as f:
                json.dump(self.saved_configs, f, indent=2)
        except Exception:
            pass
        self.update_configs_list_widget()
        self.update_config_combobox()
        QMessageBox.information(self, "Deleted", f"Recipe '{name}' deleted.")
