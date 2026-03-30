from PyQt6.QtCore import QObject, pyqtSignal


class Transport(QObject):
    frame_received = pyqtSignal(bytes)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def connect_device(self, target: str) -> None:
        raise NotImplementedError

    def disconnect_device(self) -> None:
        raise NotImplementedError

    def send_frame(self, data: bytes) -> None:
        raise NotImplementedError
