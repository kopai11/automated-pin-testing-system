import os
from datetime import datetime

import serial
import serial.tools.list_ports

from PySide6.QtCore import QTimer, QThread
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QPlainTextEdit, QCheckBox, QGroupBox, QFileDialog,
    QMessageBox, QSizePolicy, QWidget, QRadioButton, QButtonGroup,
)

from ..helpers import info, warn, err, make_scroll
from ..serial_reader import SerialReader


class OperatorPageMixin:
    """Mixin: Operator dashboard page – recipe selection, start/stop, serial monitor."""

    # -------------------------
    # Build Operator Page UI
    # -------------------------
    def build_operator_page(self):
        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("👤 Operator Dashboard")
        title.setStyleSheet("font-size: 30px; font-weight: 800;")
        outer_layout.addWidget(title)

        cols = QHBoxLayout()
        outer_layout.addLayout(cols, 1)

        left = QWidget()
        right = QWidget()
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cols.addWidget(left, 2)
        cols.addWidget(right, 2)

        left_l = QVBoxLayout(left)
        right_l = QVBoxLayout(right)

        box_name = QGroupBox("Operator")
        gl = QGridLayout(box_name)
        gl.addWidget(QLabel("Operator ID/Name:"), 0, 0)
        self.operator_name = QLineEdit()
        gl.addWidget(self.operator_name, 0, 1)
        left_l.addWidget(box_name)

        box_recipe = QGroupBox("Select Recipe")
        gl2 = QGridLayout(box_recipe)
        gl2.addWidget(QLabel("Test Recipe/Test Program:"), 0, 0)
        self.config_combo = QComboBox()
        gl2.addWidget(self.config_combo, 0, 1)
        btn_load = QPushButton("Load Recipe")
        gl2.addWidget(btn_load, 0, 2)
        left_l.addWidget(box_recipe)

        box_details = QGroupBox("Recipe Details")
        v = QVBoxLayout(box_details)
        self.details_text = QPlainTextEdit()
        self.details_text.setReadOnly(True)
        v.addWidget(self.details_text)
        left_l.addWidget(box_details, 1)

        # Start / Stop buttons
        self.btn_start = QPushButton("▶  Start Monitoring")
        self.btn_start.setEnabled(False)
        self.btn_start.setMinimumHeight(50)

        self.btn_stop_main = QPushButton("⏹  Stop")
        self.btn_stop_main.setObjectName("btn_stop_main")
        self.btn_stop_main.setEnabled(False)
        self.btn_stop_main.setMinimumHeight(50)

        self.btn_test_procedure = QPushButton("📋 Test Procedure")
        self.btn_test_procedure.setMinimumHeight(50)

        start_stop_row = QHBoxLayout()
        start_stop_row.setSpacing(8)
        start_stop_row.addWidget(self.btn_start, 3)
        start_stop_row.addWidget(self.btn_stop_main, 2)
        start_stop_row.addWidget(self.btn_test_procedure, 1)
        left_l.addLayout(start_stop_row)

        # Serial Monitor
        serial_box = QGroupBox("📡Communication Section (Serial Monitor)")
        right_l.addWidget(serial_box, 1)
        self.build_serial_monitor_ui(serial_box)

        # Wire up
        btn_load.clicked.connect(self.load_config_operator)
        self.update_config_combobox()
        self.btn_start.clicked.connect(self.start_monitoring)
        self.btn_stop_main.clicked.connect(self.stop_monitoring)
        self.btn_test_procedure.clicked.connect(self.test_procedure)

        scroll = make_scroll(outer)
        layout = QVBoxLayout(self.page_operator)
        layout.addWidget(scroll)

    # =========================================================
    # Serial Monitor UI + Commands + Auto-save
    # =========================================================

    def build_serial_monitor_ui(self, parent_group: QGroupBox):
        lay = QVBoxLayout(parent_group)

        # Row: Port + Baud + buttons
        row = QHBoxLayout()
        lay.addLayout(row)

        row.addWidget(QLabel("COM Port:"))
        self.cmb_port = QComboBox()
        row.addWidget(self.cmb_port, 1)

        row.addWidget(QLabel("Baud:"))
        self.cmb_baud = QComboBox()
        self.cmb_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.cmb_baud.setCurrentText("38400")
        row.addWidget(self.cmb_baud)

        self.btn_connect = QPushButton("🔌Connect")
        self.btn_disconnect = QPushButton("⛔ Disconnect")
        self.btn_refresh = QPushButton("🔄 Refresh")
        row.addWidget(self.btn_connect)
        row.addWidget(self.btn_disconnect)
        row.addWidget(self.btn_refresh)

        # Pin Name Apply / Set button
        row2 = QHBoxLayout()
        lay.addLayout(row2)

        row2.addWidget(QLabel("TestProgram:"))
        self.ed_testprogram = QLineEdit()
        self.ed_testprogram.setPlaceholderText("Folder name for SD card save & auto-save file name")
        row2.addWidget(self.ed_testprogram, 1)
        self.btn_send_file = QPushButton("Return")
        row2.addWidget(self.btn_send_file)
        row2.addWidget(QLabel("Set TestProgram as Pin_fixture + RecipeName + Timestamp according to Recipe."))
        row2.addStretch(1)

        # Auto-save + pin id
        row2_1 = QHBoxLayout()
        lay.addLayout(row2_1)

        self.chk_autosave = QCheckBox("Data Auto-save")
        self.lbl_autosave = QLabel("Disable")
        self.lbl_autosave.setStyleSheet("color: red; font-weight: 600;")
        row2_1.addWidget(self.chk_autosave)
        row2_1.addWidget(self.lbl_autosave)
        row2_1.addStretch(1)

        # Monitor screen
        self.serial_log = QPlainTextEdit()
        self.serial_log.setReadOnly(True)
        self.serial_log.setMinimumHeight(250)
        lay.addWidget(self.serial_log, 1)

        # Manual save / clear
        row3 = QHBoxLayout()
        lay.addLayout(row3)
        self.btn_manual_save = QPushButton("💾 Manual Save Data")
        self.btn_clear = QPushButton("🧹 Clear Monitor")
        row3.addWidget(self.btn_manual_save)
        row3.addWidget(self.btn_clear)
        row3.addStretch(1)

        # RadioButtons for Send Command
        cmd_box = QGroupBox("🎛️ Testing Mode Selection")
        cmd_box.setStyleSheet("""
            QGroupBox::title {
            font-weight: bold;
            }
        """)
        cmd_l = QHBoxLayout(cmd_box)
        self.rb_TMonly = QRadioButton("TestMax Pin")
        self.rb_Both = QRadioButton("Both Pins")
        self.cmd_group = QButtonGroup(cmd_box)
        self.cmd_group.setExclusive(True)
        self.cmd_group.addButton(self.rb_TMonly)
        self.cmd_group.addButton(self.rb_Both)
        cmd_l.addWidget(self.rb_TMonly)
        cmd_l.addWidget(self.rb_Both)
        lay.addWidget(cmd_box)

        # ---- Resistance Zero Adj group containing TM and Other Pin boxes ----
        self.zero_adj_group = QGroupBox("Perform Resistance Zero Adj")
        self.zero_adj_group.setCheckable(True)
        self.zero_adj_group.setChecked(False)
        self.zero_adj_group.setStyleSheet("""
            QGroupBox::title {
            font-weight: bold;
            }
        """)
        zero_adj_layout = QHBoxLayout(self.zero_adj_group)

        # Resistance Zero Offset - TM
        self.zero_offset_tm_box = QGroupBox("TestMax Pin")
        self.zero_offset_tm_box.setStyleSheet("""
            QGroupBox::title {
            font-weight: bold;
            }
        """)
        zero_offset_tm_layout = QHBoxLayout(self.zero_offset_tm_box)
        self.rb_zero_offset_tm_on = QRadioButton("Hioki ON")
        self.rb_zero_offset_tm_off = QRadioButton("Hioki OFF")
        self.pb_zero_offset_tm = QPushButton("Set TM Pin Zero Offset")
        self.zero_offset_tm_group = QButtonGroup(self.zero_offset_tm_box)
        self.zero_offset_tm_group.setExclusive(True)
        self.zero_offset_tm_group.addButton(self.rb_zero_offset_tm_on)
        self.zero_offset_tm_group.addButton(self.rb_zero_offset_tm_off)
        self.rb_zero_offset_tm_off.setChecked(True)
        zero_offset_tm_layout.addWidget(self.rb_zero_offset_tm_on)
        zero_offset_tm_layout.addWidget(self.rb_zero_offset_tm_off)
        zero_offset_tm_layout.addWidget(self.pb_zero_offset_tm)
        zero_adj_layout.addWidget(self.zero_offset_tm_box)

        # Resistance Zero Offset - Other
        self.zero_offset_other_box = QGroupBox("OtherPin")
        self.zero_offset_other_box.setStyleSheet("""
            QGroupBox::title {
            font-weight: bold;
            }
        """)
        zero_offset_other_layout = QHBoxLayout(self.zero_offset_other_box)
        self.rb_zero_offset_other_on = QRadioButton("Hioki ON")
        self.rb_zero_offset_other_off = QRadioButton("Hioki OFF")
        self.pb_zero_offset_other = QPushButton("Set OtherPin Zero Offset")
        self.zero_offset_other_group = QButtonGroup(self.zero_offset_other_box)
        self.zero_offset_other_group.setExclusive(True)
        self.zero_offset_other_group.addButton(self.rb_zero_offset_other_on)
        self.zero_offset_other_group.addButton(self.rb_zero_offset_other_off)
        self.rb_zero_offset_other_off.setChecked(True)
        zero_offset_other_layout.addWidget(self.rb_zero_offset_other_on)
        zero_offset_other_layout.addWidget(self.rb_zero_offset_other_off)
        zero_offset_other_layout.addWidget(self.pb_zero_offset_other)
        zero_adj_layout.addWidget(self.zero_offset_other_box)

        # ---- Same row: Zero R Adj box + Current Source box ----
        row_adj_current = QHBoxLayout()
        lay.addLayout(row_adj_current)

        row_adj_current.addWidget(self.zero_adj_group)

        current_box = QGroupBox("Current Path Control")
        current_box.setStyleSheet("""
            QGroupBox::title {
            font-weight: bold;
            }
        """)
        current_layout = QHBoxLayout(current_box)
        self.btn_current_on = QPushButton("On")
        self.btn_current_on.setStyleSheet("font-weight: 700;")
        self.btn_current_off = QPushButton("Off")
        self.btn_current_off.setStyleSheet("font-weight: 700;")
        current_layout.addWidget(self.btn_current_on)
        current_layout.addWidget(self.btn_current_off)
        row_adj_current.addWidget(current_box)

        # ---- Row 5: Start / Stop / Servo On / Servo Off ----
        row5 = QHBoxLayout()
        lay.addLayout(row5)
        self.btn_read = QPushButton("▶️ Start")
        self.btn_read.setStyleSheet("font-weight: 800;")
        self.btn_end = QPushButton("⏹️ Stop")
        self.btn_end.setStyleSheet("font-weight: 800;")
        self.btn_ServoOn = QPushButton("⚡ Servo On")
        self.btn_ServoOn.setStyleSheet("font-weight: 700;")
        self.btn_ServoOff = QPushButton("⛔ Servo Off")
        self.btn_ServoOff.setStyleSheet("color: red;font-weight: 700;")
        row5.addWidget(self.btn_read)
        row5.addWidget(self.btn_end)
        row5.addWidget(self.btn_ServoOn)
        row5.addWidget(self.btn_ServoOff)
        row5.addStretch(1)

        # Threaded serial
        self.serial_thread = QThread(self)
        self.serial_worker = SerialReader()
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.start()
        self._serial_line_buffer = ""

        # signals
        self.btn_refresh.clicked.connect(self.update_serial_ports)
        self.btn_connect.clicked.connect(self.connect_serial_monitor)
        self.btn_disconnect.clicked.connect(self.disconnect_serial_monitor)
        self.btn_clear.clicked.connect(self.clear_serial_monitor)
        self.btn_manual_save.clicked.connect(self.manual_save_serial_monitor_data)

        self.chk_autosave.stateChanged.connect(self.toggle_serial_monitor_auto_save)
        self.rb_TMonly.clicked.connect(self.send_serial_combination)
        self.rb_Both.clicked.connect(self.send_serial_combination)
        self.btn_read.clicked.connect(self.send_serial_read_command)
        self.btn_end.clicked.connect(self.send_serial_end_command)
        self.btn_send_file.clicked.connect(self.send_serial_file_command)
        self.btn_ServoOn.clicked.connect(self.sent_servoOn_command)
        self.btn_ServoOff.clicked.connect(self.btn_ServoOff_command)
        self.rb_zero_offset_tm_on.toggled.connect(self.send_zero_offset_tm_onoff_command)
        self.pb_zero_offset_tm.clicked.connect(self.send_zero_offset_tm_command)
        self.rb_zero_offset_other_on.toggled.connect(self.send_zero_offset_other_onoff_command)
        self.pb_zero_offset_other.clicked.connect(self.send_zero_offset_other_command)
        self.zero_adj_group.toggled.connect(self.toggle_zero_adj_function)
        self.btn_current_on.clicked.connect(self.send_current_on_command)
        self.btn_current_off.clicked.connect(self.send_current_off_command)

        self.serial_worker.line_received.connect(self.append_serial_line)
        self.serial_worker.disconnected.connect(self.on_serial_disconnected)

        # initial ports
        self.update_serial_ports()

    # ---- Serial port commands ----

    def update_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        self.cmb_port.clear()
        for idx, p in enumerate(ports):
            if p.description and p.description != p.device:
                display_text = f"{p.device} - {p.description}"
            else:
                display_text = p.device
            self.cmb_port.addItem(display_text, p.device)

    def append_serial_line(self, line: str):
        stripped = line.strip()
        # Continuation parts: starts with | or Current right after a number+comma
        if stripped.startswith("|") or stripped.startswith("Current"):
            if self._serial_line_buffer:
                self._serial_line_buffer += stripped
            else:
                self._serial_line_buffer = stripped
        else:
            # Flush any buffered line first
            if self._serial_line_buffer:
                self.serial_log.appendPlainText(self._serial_line_buffer)
                self._serial_line_buffer = ""
            # Check if this line starts a new data record (e.g. "1,")
            if stripped.endswith(",") and stripped[:-1].isdigit():
                self._serial_line_buffer = stripped
            else:
                self.serial_log.appendPlainText(line)

    def _flush_serial_buffer(self):
        if self._serial_line_buffer:
            self.serial_log.appendPlainText(self._serial_line_buffer)
            self._serial_line_buffer = ""

    def on_serial_disconnected(self, msg: str):
        self._flush_serial_buffer()
        self.append_serial_line(msg)
        info(self, "Status", msg)
        self.btn_connect.setStyleSheet("")

    def connect_serial_monitor(self):
        port = self.cmb_port.currentData()
        if not port:
            port = self.cmb_port.currentText().strip().split(' - ')[0]

        baud = int(self.cmb_baud.currentText())

        if not port:
            warn(self, "Connection Error", "Please select a COM port.")
            return

        self.serial_log.clear()
        self.last_serial_data_len = 0
        self.auto_save_session_header_written = False

        try:
            self.serial_worker.connect_port(port, baud)
            info(self, "Connection Successful", f"Connected to {port} at {baud}")
            self.btn_connect.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            QTimer.singleShot(0, self.serial_worker.start)

            if self.chk_autosave.isChecked():
                self.serial_monitor_data_auto_save()

        except Exception as e:
            err(self, "Connection Error", f"Could not connect to {port}: {e}")

    def disconnect_serial_monitor(self):
        self.auto_save_enabled = False
        self.chk_autosave.setChecked(False)
        self._flush_serial_buffer()
        QTimer.singleShot(0, self.serial_worker.stop)
        self.write_serial_monitor_auto_save_end_marker()
        self.btn_connect.setStyleSheet("")

    def clear_serial_monitor(self):
        self.serial_log.clear()
        self._serial_line_buffer = ""
        self.last_serial_data_len = 0
        self.auto_save_session_header_written = False

    def send_serial_read_command(self):
        try:
            self.serial_worker.write(b"start\n")
            # Disable current, resistance, and test mode controls
            self.zero_adj_group.setEnabled(False)
            self.btn_current_on.setEnabled(False)
            self.btn_current_off.setEnabled(False)
            self.rb_TMonly.setEnabled(False)
            self.rb_Both.setEnabled(False)
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_serial_end_command(self):
        try:
            self.serial_worker.write(b"stop\n")
            if hasattr(self, 'cmd_group'):
                self.cmd_group.setExclusive(False)
                self.rb_TMonly.setChecked(False)
                self.rb_Both.setChecked(False)
                self.cmd_group.setExclusive(True)
            # Re-enable current, resistance, and test mode controls
            self.zero_adj_group.setEnabled(True)
            self.btn_current_on.setEnabled(True)
            self.btn_current_off.setEnabled(True)
            self.rb_TMonly.setEnabled(True)
            self.rb_Both.setEnabled(True)

        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_serial_file_command(self):
        try:
            pin = self.ed_testprogram.text().strip()

            if not pin:
                warn(self, "Missing", "Please fill TestProgram.")
                return

            cmd = f"FOLDER:{pin}\n"
            self.serial_worker.write(cmd.encode("utf-8"))
            self.serial_log.appendPlainText(f"SENT: {cmd.strip()}")

        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def sent_servoOn_command(self):
        try:
            self.serial_worker.write(b"servoon\n")
            self.btn_ServoOn.setEnabled(False)
            self.btn_ServoOn.setStyleSheet("color: green; font-weight: 700;")
            self.btn_ServoOff.setStyleSheet("font-weight: 700;")
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def btn_ServoOff_command(self):
        try:
            self.serial_worker.write(b"servooff\n")
            self.btn_ServoOn.setEnabled(True)
            self.btn_ServoOff.setStyleSheet("color: red;font-weight: 700;")
            self.btn_ServoOn.setStyleSheet("font-weight: 700;")
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def toggle_zero_adj_function(self, checked):
        if not checked:
            # Prevent unchecking if either Hioki is still ON
            if not self.rb_zero_offset_tm_off.isChecked() or not self.rb_zero_offset_other_off.isChecked():
                self.zero_adj_group.setChecked(True)
                return
            # Reset radio buttons to OFF when unchecking
            self.rb_zero_offset_tm_off.setChecked(True)
            self.rb_zero_offset_other_off.setChecked(True)
        # Disable Start/Stop/ServoOn/ServoOff/CurrentOn when zero adj is active
        self.btn_read.setEnabled(not checked)
        self.btn_end.setEnabled(not checked)
        self.btn_ServoOn.setEnabled(not checked)
        self.btn_ServoOff.setEnabled(not checked)
        self.btn_current_on.setEnabled(not checked)
        self.btn_current_off.setEnabled(not checked)

    def send_zero_offset_tm_onoff_command(self):
        try:
            if self.rb_zero_offset_tm_on.isChecked():
                self.serial_worker.write(b"HiokiOnTM\n")
                # Disable Other pin Hioki ON while TM is ON
                self.rb_zero_offset_other_on.setEnabled(False)
            elif self.rb_zero_offset_tm_off.isChecked():
                self.serial_worker.write(b"HiokiOffTM\n")
                # Re-enable Other pin Hioki ON
                self.rb_zero_offset_other_on.setEnabled(True)
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_zero_offset_tm_command(self):
        try:
            self.serial_worker.write(b"0ADJTM\n")
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_zero_offset_other_onoff_command(self):
        try:
            if self.rb_zero_offset_other_on.isChecked():
                self.serial_worker.write(b"HiokiOnOther\n")
                # Disable TM pin Hioki ON while Other is ON
                self.rb_zero_offset_tm_on.setEnabled(False)
            elif self.rb_zero_offset_other_off.isChecked():
                self.serial_worker.write(b"HiokiOffOther\n")
                # Re-enable TM pin Hioki ON
                self.rb_zero_offset_tm_on.setEnabled(True)
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_zero_offset_other_command(self):
        try:
            self.serial_worker.write(b"0ADJOther\n")
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_current_on_command(self):
        """Send CurrentOn command and disable resistance buttons."""
        try:
            self.serial_worker.write(b"CurrentOn\n")
            self.serial_log.appendPlainText("SENT: CurrentOn")
            self.btn_current_on.setEnabled(False)
            self.btn_current_on.setStyleSheet("color: green; font-weight: 700;")
            self.btn_current_off.setEnabled(True)
            self.btn_current_off.setStyleSheet("font-weight: 700;")
            # Disable resistance buttons
            self.btn_read.setEnabled(False)
            self.btn_end.setEnabled(False)
            self.btn_ServoOn.setEnabled(False)
            self.btn_ServoOff.setEnabled(False)
            self.zero_adj_group.setEnabled(False)
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_current_off_command(self):
        """Send CurrentOff command and re-enable resistance buttons."""
        try:
            self.serial_worker.write(b"CurrentOff\n")
            self.serial_log.appendPlainText("SENT: CurrentOff")
            self.btn_current_off.setEnabled(False)
            self.btn_current_off.setStyleSheet("color: red; font-weight: 700;")
            self.btn_current_on.setEnabled(True)
            self.btn_current_on.setStyleSheet("font-weight: 700;")
            # Re-enable resistance buttons
            self.btn_read.setEnabled(True)
            self.btn_end.setEnabled(True)
            self.btn_ServoOn.setEnabled(True)
            self.btn_ServoOff.setEnabled(True)
            self.zero_adj_group.setEnabled(True)
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    def send_serial_combination(self):
        if self.rb_TMonly.isChecked():
            cmd = "1\n"
        elif self.rb_Both.isChecked():
            cmd = "2\n"
        else:
            return
        try:
            self.serial_worker.write(cmd.encode("utf-8"))
            self.serial_log.appendPlainText(f"SENT: {cmd.strip()}")
        except Exception as e:
            warn(self, "Error", f"Couldn't send command: {e}")

    # ---- Auto-save ----

    def toggle_serial_monitor_auto_save(self):
        enabled = self.chk_autosave.isChecked()

        if enabled:
            pin_name = self.ed_testprogram.text().strip()
            if not pin_name:
                QMessageBox.warning(
                    self,
                    "TestProgram Required",
                    "Please enter TestProgram before enabling Auto-save."
                )
                try:
                    self.chk_autosave.setChecked(False)
                except Exception:
                    pass
                self.auto_save_enabled = False
                self.lbl_autosave.setText("Disable")
                self.lbl_autosave.setStyleSheet("color: red; font-weight: 600;")
                return

            log_dir = os.path.join(self.default_save_folder, "Test data")
            os.makedirs(log_dir, exist_ok=True)

            safe_name = "".join(c for c in pin_name if c not in r'\/:*?"<>|').strip()
            if not safe_name:
                safe_name = "AutoSave"

            self.auto_save_file_path = os.path.join(log_dir, f"{safe_name}.txt")

            self.auto_save_enabled = True
            self.lbl_autosave.setText("Active")
            self.lbl_autosave.setStyleSheet("color: green; font-weight: 600;")
            self.auto_save_session_header_written = False

            self.serial_monitor_data_auto_save()

        else:
            self.auto_save_enabled = False
            self.lbl_autosave.setText("Disable")
            self.lbl_autosave.setStyleSheet("color: red; font-weight: 600;")
            try:
                self.write_serial_monitor_auto_save_end_marker()
            except Exception:
                pass

    def serial_monitor_data_auto_save(self):
        if not self.auto_save_enabled:
            return

        file_path = getattr(self, "auto_save_file_path", None)
        if not file_path:
            self.auto_save_enabled = False
            self.lbl_autosave.setText("Disable")
            self.lbl_autosave.setStyleSheet("color: red; font-weight: 600;")
            return

        if not getattr(self, "auto_save_session_header_written", False):
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n--- NEW SERIAL SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                self.auto_save_session_header_written = True
            except Exception:
                self.auto_save_enabled = False
                self.lbl_autosave.setText("Disable")
                self.lbl_autosave.setStyleSheet("color: red; font-weight: 600;")
                return

        current_full = self.serial_log.toPlainText()
        last_len = getattr(self, "last_serial_data_len", 0)
        new_content = current_full[last_len:].strip()

        if new_content:
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(new_content + "\n")
                self.last_serial_data_len = len(current_full)
            except Exception:
                pass

        QTimer.singleShot(5000, self.serial_monitor_data_auto_save)

    def write_serial_monitor_auto_save_end_marker(self):
        file_path = getattr(self, "auto_save_file_path", None)
        if not file_path:
            return

        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- END OF AUTO-SAVE SESSION: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        except Exception:
            pass

    def manual_save_serial_monitor_data(self):
        content = self.serial_log.toPlainText().strip()
        if not content:
            info(self, "Save Data", "No data to save in the serial monitor.")
            return

        default_name = (self.ed_testprogram.text().strip() or f"ManualSave_{datetime.now().strftime('%Y%m%d_%H%M%S')}") + ".txt"
        path, _ = QFileDialog.getSaveFileName(self, "Save Serial Data", default_name, "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            info(self, "Save Data", f"Serial data saved to:\n{path}")
        except Exception as e:
            err(self, "Save Error", f"Failed to save serial data: {e}")
