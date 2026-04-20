from PySide6.QtCore import Signal, QObject, QTimer

import serial


class SerialReader(QObject):
    """Low-level serial port reader running on a QThread."""

    line_received = Signal(str)
    disconnected = Signal(str)

    def __init__(self):
        super().__init__()
        self.ser = None
        self._running = False
        self._buffer = ""

    def connect_port(self, port: str, baud: int):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = serial.Serial(port, baud, timeout=0.1)

    def start(self):
        self._running = True
        self._buffer = ""
        self._loop()

    def stop(self):
        self._running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass

    def write(self, data: bytes):
        if self.ser and self.ser.is_open:
            self.ser.write(data)

    def _loop(self):
        if not self._running:
            return

        try:
            waiting = self.ser.in_waiting if (self.ser and self.ser.is_open) else 0
            if waiting > 0:
                data = self.ser.read(waiting).decode("utf-8", errors="ignore")
                if data:
                    self._buffer += data
                    lines = self._buffer.splitlines(keepends=True)

                    if lines and not lines[-1].endswith("\n"):
                        complete = lines[:-1]
                        self._buffer = lines[-1]
                    else:
                        complete = lines
                        self._buffer = ""

                    for line in complete:
                        self.line_received.emit(line.rstrip("\n"))

        except Exception as e:
            self.disconnected.emit(f"Serial error: {e}")
            self.stop()
            return

        QTimer.singleShot(10, self._loop)
