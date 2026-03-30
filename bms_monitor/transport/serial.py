from __future__ import annotations
import serial
from PyQt6.QtCore import QThread, pyqtSignal
from bms_monitor.transport.base import Transport

START_BYTE = 0xDD
END_BYTE = 0x77
MAX_FRAME = 256


class _ReaderThread(QThread):
    raw_frame = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, port: serial.Serial):
        super().__init__()
        self._port = port
        self._running = True

    def run(self):
        buf = bytearray()
        while self._running:
            try:
                byte = self._port.read(1)
                if not byte:
                    continue
                b = byte[0]
                if b == START_BYTE and not buf:
                    buf.append(b)
                elif buf:
                    buf.append(b)
                    if b == END_BYTE and len(buf) >= 7:
                        self.raw_frame.emit(bytes(buf))
                        buf.clear()
                    elif len(buf) > MAX_FRAME:
                        buf.clear()
            except serial.SerialException as e:
                self.error.emit(str(e))
                break

    def stop(self):
        self._running = False


class SerialTransport(Transport):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._port: serial.Serial | None = None
        self._reader: _ReaderThread | None = None

    def connect_device(self, target: str) -> None:
        self._port = serial.Serial(target, baudrate=9600, timeout=1.0)
        self._reader = _ReaderThread(self._port)
        self._reader.raw_frame.connect(self.frame_received)
        self._reader.error.connect(self.error_occurred)
        self._reader.start()
        self.connection_changed.emit(True)

    def disconnect_device(self) -> None:
        if self._reader:
            self._reader.stop()
            self._reader.wait(2000)
        if self._port and self._port.is_open:
            self._port.close()
        self.connection_changed.emit(False)

    def send_frame(self, data: bytes) -> None:
        if self._port and self._port.is_open:
            self._port.write(data)
