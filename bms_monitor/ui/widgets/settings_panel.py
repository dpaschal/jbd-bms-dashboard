from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QDoubleSpinBox, QCheckBox,
    QLineEdit, QDialogButtonBox,
)
from PyQt6.QtCore import pyqtSignal


class SettingsPanel(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setStyleSheet("""
            QDialog { background-color: #1a1a2e; color: #e2e2e2; }
            QLabel { color: #ffffff; }
            QDoubleSpinBox, QLineEdit {
                background-color: #16213e; color: #e2e2e2;
                border: 1px solid #0f3460; padding: 4px;
            }
            QCheckBox { color: #e2e2e2; }
            QPushButton {
                background-color: #16213e; color: #e2e2e2;
                border: 1px solid #0f3460; padding: 6px 16px;
            }
            QPushButton:hover { background-color: #0f3460; }
        """)
        self._settings = dict(settings)
        form = QFormLayout(self)
        self._cell_uv = QDoubleSpinBox(); self._cell_uv.setRange(2.0, 3.5); self._cell_uv.setSingleStep(0.01)
        self._cell_ov = QDoubleSpinBox(); self._cell_ov.setRange(3.0, 4.5); self._cell_ov.setSingleStep(0.01)
        self._pack_uv = QDoubleSpinBox(); self._pack_uv.setRange(10.0, 100.0); self._pack_uv.setSingleStep(0.1)
        self._temp_max = QDoubleSpinBox(); self._temp_max.setRange(20.0, 80.0)
        self._current_max = QDoubleSpinBox(); self._current_max.setRange(1.0, 500.0)
        self._log_enabled = QCheckBox()
        self._log_dir = QLineEdit()
        form.addRow("Cell undervolt (V):", self._cell_uv)
        form.addRow("Cell overvolt (V):", self._cell_ov)
        form.addRow("Pack undervolt (V):", self._pack_uv)
        form.addRow("Max temp (°C):", self._temp_max)
        form.addRow("Max current (A):", self._current_max)
        form.addRow("Enable logging:", self._log_enabled)
        form.addRow("Log directory:", self._log_dir)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self._load()

    def _load(self) -> None:
        s = self._settings
        self._cell_uv.setValue(s.get("cell_undervolt", 3.0))
        self._cell_ov.setValue(s.get("cell_overvolt", 3.65))
        self._pack_uv.setValue(s.get("pack_undervolt", 44.8))
        self._temp_max.setValue(s.get("temp_max", 45.0))
        self._current_max.setValue(s.get("current_max", 100.0))
        self._log_enabled.setChecked(s.get("log_enabled", True))
        self._log_dir.setText(s.get("log_dir", "~/.jbd-bms"))

    def _save(self) -> None:
        self._settings.update({
            "cell_undervolt": self._cell_uv.value(),
            "cell_overvolt": self._cell_ov.value(),
            "pack_undervolt": self._pack_uv.value(),
            "temp_max": self._temp_max.value(),
            "current_max": self._current_max.value(),
            "log_enabled": self._log_enabled.isChecked(),
            "log_dir": self._log_dir.text(),
        })
        self.settings_saved.emit(self._settings)
        self.accept()
