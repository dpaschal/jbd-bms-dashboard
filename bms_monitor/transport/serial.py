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
                chunk = self._port.read(64)
                if not chunk:
                    continue
                buf.extend(chunk)
                while True:
                    start = buf.find(START_BYTE)
                    if start == -1:
                        buf.clear()
                        break
                    if start > 0:
                        del buf[:start]
                    if len(buf) < 7:
                        break
                    payload_len = buf[3]
                    frame_len = 4 + payload_len + 2 + 1
                    if frame_len > MAX_FRAME:
                        # bogus length — drop the start byte and resync
                        del buf[:1]
                        continue
                    if len(buf) < frame_len:
                        break
                    frame = bytes(buf[:frame_len])
                    del buf[:frame_len]
                    if frame[-1] == END_BYTE:
                        self.raw_frame.emit(frame)
                    # else: corrupt frame silently dropped, loop resyncs
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
