from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import asyncio
from bleak import BleakScanner


class _ScanThread(QThread):
    found = pyqtSignal(str, str)
    done = pyqtSignal()

    def run(self):
        async def scan():
            devices = await BleakScanner.discover(timeout=5.0)
            for d in devices:
                self.found.emit(d.name or "Unknown", d.address)
        asyncio.run(scan())
        self.done.emit()


class BLEScanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BLE Scan")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        self._status = QLabel("Scanning for 5 seconds…")
        layout.addWidget(self._status)
        self._list = QListWidget()
        layout.addWidget(self._list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._thread = _ScanThread()
        self._thread.found.connect(self._add_device)
        self._thread.done.connect(lambda: self._status.setText("Scan complete."))
        self._thread.start()

    def _add_device(self, name: str, address: str) -> None:
        item = QListWidgetItem(f"{name}  [{address}]")
        item.setData(Qt.ItemDataRole.UserRole, address)
        self._list.addItem(item)

    def selected_address(self) -> str:
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return ""
