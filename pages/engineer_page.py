import os

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QCheckBox, QGroupBox, QFileDialog, QMessageBox,
    QSizePolicy, QWidget, QRadioButton, QButtonGroup, QScrollArea,
)

from ..helpers import make_scroll


class EngineerPageMixin:
    """Mixin: Engineer settings page – recipe builder, graph config, categories."""

    def build_setting_page(self):
        root = QWidget()
        root.setStyleSheet("background: transparent;")
        root_l = QVBoxLayout(root)
        root_l.setContentsMargins(15, 15, 15, 15)
        root_l.setSpacing(12)

        title = QLabel("⚙️ Engineer Dashboard")
        title.setStyleSheet("font-size: 30px; font-weight: 800;")
        root_l.addWidget(title)

        cols = QHBoxLayout()
        cols.setSpacing(20)
        root_l.addLayout(cols)

        left = QWidget()
        right = QWidget()
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        cols.addWidget(left, 1)
        cols.addWidget(right, 2.5)

        left_l = QVBoxLayout(left)
        left_l.setSpacing(10)
        right_l = QVBoxLayout(right)
        right_l.setSpacing(10)

        # ===================== LEFT COLUMN =====================

        # Project
        gb_project = QGroupBox("Project")
        gl = QGridLayout(gb_project)
        gl.addWidget(QLabel("Part_number/Project_number:"), 0, 0)
        self.ed_project_name = QLineEdit()
        self.ed_project_name.setMinimumWidth(180)
        gl.addWidget(self.ed_project_name, 0, 1)
        left_l.addWidget(gb_project)

        # Pin Fixture
        gb_fixture = QGroupBox("Pin Fixture")
        glx = QGridLayout(gb_fixture)
        glx.addWidget(QLabel("Pin Fixture:"), 0, 0)
        self.ed_pin_fixture = QLineEdit()
        self.ed_pin_fixture.setMinimumWidth(180)
        glx.addWidget(self.ed_pin_fixture, 0, 1)
        left_l.addWidget(gb_fixture)

        # Test Types
        gb_test_types = QGroupBox("Select Test Types")
        gtt = QGridLayout(gb_test_types)
        self.measure_cat_checks = {}
        measure_cat = ["Frequency", "Temperature", "Humanity", "Force", "Current", "Life_Spend", "Resistance"]
        for i, item in enumerate(measure_cat):
            cb = QCheckBox(item)
            cb.setChecked(False)
            cb.setStyleSheet("font-size: 14px;")
            self.measure_cat_checks[item] = cb
            r, c = divmod(i, 3)
            gtt.addWidget(cb, r, c)
        left_l.addWidget(gb_test_types)

        # Display Mode
        gb_display_mode = QGroupBox("Display Mode")
        vtm = QVBoxLayout(gb_display_mode)
        self.rb_all_data = QRadioButton("Display All_data")
        self.rb_cutoff = QRadioButton("Cut_off beyond limit data")
        self.rb_all_data.setChecked(True)
        self.display_mode_group = QButtonGroup(self)
        self.display_mode_group.addButton(self.rb_all_data)
        self.display_mode_group.addButton(self.rb_cutoff)
        vtm.addWidget(self.rb_all_data)
        vtm.addWidget(self.rb_cutoff)
        left_l.addWidget(gb_display_mode)

        # Engineer Name
        gb_engineer = QGroupBox("Engineer Name")
        gb_engineer.setStyleSheet("QGroupBox { font-size: 18px; font-weight: 800; }")
        eng_layout = QVBoxLayout(gb_engineer)
        eng_layout.setSpacing(8)
        eng_layout.addWidget(QLabel("Change Engineer Name"))
        self.ed_engineer_name = QLineEdit()
        self.ed_engineer_name.setPlaceholderText("Enter engineer name")
        self.ed_engineer_name.setText(getattr(self, 'Engineer_name', ''))
        self.ed_engineer_name.setMinimumHeight(36)
        eng_layout.addWidget(self.ed_engineer_name)
        self.btn_change_engineer = QPushButton("Update Name")
        self.btn_change_engineer.clicked.connect(self.change_engineer_name)
        eng_layout.addWidget(self.btn_change_engineer)
        left_l.addWidget(gb_engineer)

        left_l.addStretch(1)

        # ===================== RIGHT COLUMN =====================

        # Graph Setting
        gb_graph = QGroupBox("Graph Setting")
        gg = QGridLayout(gb_graph)

        gg.addWidget(QLabel("Full Scale:"), 0, 0)
        self.ed_window_size = QLineEdit("10")
        self.ed_window_size.setMaximumWidth(90)
        gg.addWidget(self.ed_window_size, 0, 1)
        gg.addWidget(QLabel("(X-axis)"), 0, 2)

        gg.addWidget(QLabel("Max R-Value(mΩ):"), 1, 0)
        self.ed_yaxis_max = QLineEdit("20")
        self.ed_yaxis_max.setMaximumWidth(90)
        gg.addWidget(self.ed_yaxis_max, 1, 1)
        gg.addWidget(QLabel("(Y-axis)"), 1, 2)

        gg.addWidget(QLabel("Open-Circuit(mΩ):"), 2, 0)
        self.ed_open_circuit = QLineEdit("3000")
        self.ed_open_circuit.setMaximumWidth(90)
        gg.addWidget(self.ed_open_circuit, 2, 1)

        gg.addWidget(QLabel("Close-Circuit(mΩ):"), 3, 0)
        self.ed_close_circuit = QLineEdit("0")
        self.ed_close_circuit.setMaximumWidth(90)
        gg.addWidget(self.ed_close_circuit, 3, 1)

        # Categories
        gb_cat = QGroupBox("Categories")
        gc = QGridLayout(gb_cat)
        self.category_checks = {}
        categories = ["0%", "25%", "50%", "75%", "100%", "-75%", "-50%", "-25%", "-0%"]
        for i, cat in enumerate(categories):
            cb = QCheckBox(cat)
            cb.setChecked(False)
            cb.setStyleSheet("font-size: 14px;")
            self.category_checks[cat] = cb
            r, c = divmod(i, 3)
            gc.addWidget(cb, r, c)

        gg.addWidget(gb_cat, 4, 0, 1, 3)
        right_l.addWidget(gb_graph)

        # Save Test-config
        gb_save = QGroupBox("Save Test-config Setting")
        gs = QGridLayout(gb_save)
        gs.addWidget(QLabel("Recipe/Test-program:"), 0, 0)
        self.ed_config_name = QLineEdit()
        self.ed_config_name.setMinimumWidth(260)
        gs.addWidget(self.ed_config_name, 0, 1)
        self.btn_save_cfg = QPushButton("Save")
        self.btn_save_to_file = QPushButton("Save into File")
        gs.addWidget(self.btn_save_cfg, 0, 2)
        gs.addWidget(self.btn_save_to_file, 0, 3)
        right_l.addWidget(gb_save)

        # Saved Test Recipes
        gb_saved = QGroupBox("Saved Test Recipes")
        gb_saved.setStyleSheet("QGroupBox { font-size: 18px; font-weight: 800; }")
        saved_layout = QVBoxLayout(gb_saved)
        saved_layout.setSpacing(10)
        saved_layout.addWidget(QLabel("Select Recipe"))
        self.list_configs = QComboBox()
        self.list_configs.setMinimumHeight(36)
        saved_layout.addWidget(self.list_configs)

        btn_row_saved = QHBoxLayout()
        btn_row_saved.setSpacing(10)
        self.btn_load_cfg = QPushButton("\U0001f4c2 Load to Recipe")
        self.btn_delete_cfg = QPushButton("\U0001f5d1 Delete Recipe")
        self.btn_reset_defaults = QPushButton("\U0001f504 Reset Recipe")
        for b in (self.btn_load_cfg, self.btn_delete_cfg, self.btn_reset_defaults):
            b.setMinimumHeight(38)
        btn_row_saved.addWidget(self.btn_load_cfg)
        btn_row_saved.addWidget(self.btn_delete_cfg)
        btn_row_saved.addWidget(self.btn_reset_defaults)
        saved_layout.addLayout(btn_row_saved)

        right_l.addWidget(gb_saved)
        right_l.addStretch(1)

        # Apply to page
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(root)
        scroll.setStyleSheet("background: transparent;")

        page_layout = QVBoxLayout(self.page_setting)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        # Hook signals
        self.btn_save_cfg.clicked.connect(self.save_configuration_qt)
        self.btn_save_to_file.clicked.connect(self.save_config_details_from_setting_qt)
        self.btn_load_cfg.clicked.connect(self.load_configuration_qt)
        self.btn_delete_cfg.clicked.connect(self.delete_configuration_qt)
        self.btn_reset_defaults.clicked.connect(self.reset_setting_defaults_qt)

        self.update_configs_list_widget()

    # ---- Setting page helpers ----

    def create_file_qt(self):
        path, _ = QFileDialog.getSaveFileName(self, "Create New Data File", "", "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)")
        if path:
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, 'w') as f:
                    f.write("")
                self.ed_file_path.setText(path)
                QMessageBox.information(self, "File Created", f"Data file created successfully at:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create file: {str(e)}")

    def _get_display_mode_text(self) -> str:
        return "Display All_data" if self.rb_all_data.isChecked() else "Cut_off beyond limit data"

    def _get_selected_test_types(self):
        return [k for k, cb in self.measure_cat_checks.items() if cb.isChecked()]

    def _get_selected_categories(self):
        return [k for k, cb in self.category_checks.items() if cb.isChecked()]

    def reset_setting_defaults_qt(self):
        self.ed_project_name.setText("")
        self.ed_file_path.setText("")
        self.ed_pin_fixture.setText("")

        for cb in self.measure_cat_checks.values():
            cb.setChecked(False)

        self.rb_all_data.setChecked(True)

        self.ed_window_size.setText("10")
        self.ed_yaxis_max.setText("20")
        self.ed_open_circuit.setText("3000")
        self.ed_close_circuit.setText("0")

        for cb in self.category_checks.values():
            cb.setChecked(False)
