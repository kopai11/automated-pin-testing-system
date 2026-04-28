import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QInputDialog, QDialogButtonBox,
)


class AuthMixin:
    """Mixin: Engineer authentication (password + name dialogs, 10-min session)."""

    def request_engineer_access(self):
        """Combined password + name dialog matching the modern UI design."""
        if getattr(self, '_engineer_authenticated', False):
            elapsed = time.time() - getattr(self, '_engineer_auth_time', 0)
            if elapsed < 600:
                self.tabs.setCurrentWidget(self.page_setting)
                return
            self._engineer_authenticated = False

        dlg = QDialog(self)
        dlg.setWindowTitle("Engineer Access")
        dlg.setModal(True)
        dlg.setMinimumWidth(500)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(14)
        lay.setContentsMargins(30, 24, 30, 24)

        title = QLabel("🔐 Engineer Access Required")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        lay.addWidget(title)

        lay.addWidget(QLabel("Password"))
        pw_row = QHBoxLayout()
        pw_edit = QLineEdit()
        pw_edit.setEchoMode(QLineEdit.Password)
        pw_edit.setMinimumHeight(38)
        pw_edit.setPlaceholderText("Enter password")
        pw_row.addWidget(pw_edit, 1)
        lay.addLayout(pw_row)

        lay.addWidget(QLabel("Your Name"))
        name_edit = QLineEdit()
        name_edit.setMinimumHeight(38)
        name_edit.setPlaceholderText("Enter your name")
        existing_name = getattr(self, 'Engineer_name', '')
        if existing_name:
            name_edit.setText(existing_name)
        lay.addWidget(name_edit)

        btn_unlock = QPushButton("Unlock Engineer Mode")
        btn_unlock.setMinimumHeight(42)
        lay.addWidget(btn_unlock)

        self._pw_attempts = 0
        self._pw_hint_shown = False

        def on_unlock():
            pw = pw_edit.text().strip()
            name = name_edit.text().strip()

            if pw != "88888888":
                self._pw_attempts += 1
                QMessageBox.warning(dlg, "Wrong Password",
                                    "Password is wrong. Please try again.")
                if self._pw_attempts >= 5 and not self._pw_hint_shown:
                    self._pw_hint_shown = True
                    QMessageBox.information(dlg, "Password Hint",
                                            "Hint: Password is Eight*8")
                pw_edit.clear()
                pw_edit.setFocus()
                return

            if not name:
                QMessageBox.warning(dlg, "Name Required",
                                    "Please enter your name.")
                name_edit.setFocus()
                return

            self.Engineer_name = name
            try:
                self.lbl_engineer.setText(f"Engineer: {self.Engineer_name}")
            except Exception:
                pass
            try:
                if hasattr(self, 'ed_engineer_name'):
                    self.ed_engineer_name.setText(name)
            except Exception:
                pass
            dlg.accept()

        btn_unlock.clicked.connect(on_unlock)
        name_edit.returnPressed.connect(on_unlock)
        pw_edit.returnPressed.connect(lambda: name_edit.setFocus())

        if dlg.exec() == QDialog.Accepted:
            self._engineer_authenticated = True
            self._engineer_auth_time = time.time()
            self.tabs.setCurrentWidget(self.page_setting)

    def ask_password(self) -> bool:
        """Show a password prompt. Returns True if password correct."""
        if getattr(self, '_engineer_authenticated', False):
            elapsed = time.time() - getattr(self, '_engineer_auth_time', 0)
            if elapsed < 600:
                return True
            self._engineer_authenticated = False
        try:
            attempts = 0
            hint_shown = False
            while True:
                text, ok = QInputDialog.getText(self, "🔐 Engineer Access Required", "Enter password:", QLineEdit.Password)
                if not ok:
                    return False

                pw = (text or "").strip()
                if pw == "88888888":
                    self._engineer_authenticated = True
                    self._engineer_auth_time = time.time()
                    return True

                attempts += 1
                QMessageBox.warning(self, "Wrong Password", "Password is wrong. Please try again or press Cancel to abort.")

                if attempts >= 5 and not hint_shown:
                    hint_shown = True
                    QMessageBox.information(self, "Password Hint", "Hint: Password is Eight*8")

        except Exception:
            return False

    def ask_engineer_name(self) -> str:
        """Prompt for engineer name. Returns the entered name or empty string if cancelled."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Engineer name")
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        lbl = QLabel("Please enter your name:")
        lbl.setStyleSheet("font-weight: 700; font-size: 25px;")
        layout.addWidget(lbl)
        edit = QLineEdit()
        edit.setPlaceholderText("Engineer name")
        edit.setMinimumWidth(300)
        layout.addWidget(edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        result = {'name': ''}

        def on_ok():
            value = edit.text().strip()
            if not value:
                QMessageBox.warning(self, "Input Required", "Please enter your name.")
                return
            result['name'] = value
            dlg.accept()

        def on_cancel():
            dlg.reject()

        buttons.accepted.connect(on_ok)
        buttons.rejected.connect(on_cancel)
        edit.returnPressed.connect(on_ok)

        if dlg.exec() == QDialog.Accepted:
            return result['name']
        return ""

    def change_engineer_name(self):
        """Update engineer name from the inline edit field on the Setting page."""
        from .helpers import info, warn
        name = self.ed_engineer_name.text().strip()
        if not name:
            warn(self, "Warning", "Please enter an engineer name.")
            return
        self.Engineer_name = name
        try:
            self.lbl_engineer.setText(f"Engineer: {self.Engineer_name}")
        except Exception:
            pass
        info(self, "Updated", f"Engineer name set to: {name}")
