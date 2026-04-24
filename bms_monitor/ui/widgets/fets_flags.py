from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from bms_monitor.protocol.frames import BasicInfo


class FetsFlagsWidget(QWidget):
    # Emits requested (charge_on, discharge_on) state for main window to write.
    fet_toggle_requested = pyqtSignal(bool, bool)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel("FET STATUS"))
        self._charge_lbl = QLabel("Charge: --")
        self._discharge_lbl = QLabel("Discharge: --")
        layout.addWidget(self._charge_lbl)
        layout.addWidget(self._discharge_lbl)

        btn_row = QHBoxLayout()
        self._charge_btn = QPushButton("Toggle Charge")
        self._discharge_btn = QPushButton("Toggle Discharge")
        self._charge_btn.setEnabled(False)
        self._discharge_btn.setEnabled(False)
        self._charge_btn.clicked.connect(self._toggle_charge)
        self._discharge_btn.clicked.connect(self._toggle_discharge)
        btn_row.addWidget(self._charge_btn)
        btn_row.addWidget(self._discharge_btn)
        layout.addLayout(btn_row)

        layout.addSpacing(8)
        layout.addWidget(QLabel("PROTECTION FLAGS"))
        self._flag_labels: dict[str, QLabel] = {}
        for name in ["cell_overvolt", "cell_undervolt", "pack_overvolt",
                     "pack_undervolt", "charge_overcurrent",
                     "discharge_overcurrent", "short_circuit", "ic_error",
                     "mos_lock"]:
            lbl = QLabel(f"  {name.replace('_', ' ')}")
            lbl.setStyleSheet("color: #555; font-size: 10px;")
            layout.addWidget(lbl)
            self._flag_labels[name] = lbl
        layout.addStretch()

        self._charge_on = True
        self._discharge_on = True

    def _toggle_charge(self) -> None:
        self.fet_toggle_requested.emit(not self._charge_on, self._discharge_on)

    def _toggle_discharge(self) -> None:
        self.fet_toggle_requested.emit(self._charge_on, not self._discharge_on)

    def update(self, info: BasicInfo) -> None:
        self._charge_on = info.charge_fet
        self._discharge_on = info.discharge_fet
        c = "#4ecdc4" if info.charge_fet else "#e94560"
        d = "#4ecdc4" if info.discharge_fet else "#e94560"
        self._charge_lbl.setStyleSheet(f"color: {c};")
        self._charge_lbl.setText(f"Charge: {'ON' if info.charge_fet else 'OFF'}")
        self._discharge_lbl.setStyleSheet(f"color: {d};")
        self._discharge_lbl.setText(f"Discharge: {'ON' if info.discharge_fet else 'OFF'}")
        self._charge_btn.setEnabled(True)
        self._discharge_btn.setEnabled(True)
        p = info.protection
        flag_map = {
            "cell_overvolt": p.cell_overvolt, "cell_undervolt": p.cell_undervolt,
            "pack_overvolt": p.pack_overvolt, "pack_undervolt": p.pack_undervolt,
            "charge_overcurrent": p.charge_overcurrent,
            "discharge_overcurrent": p.discharge_overcurrent,
            "short_circuit": p.short_circuit, "ic_error": p.ic_error,
            "mos_lock": p.mos_lock,
        }
        for name, active in flag_map.items():
            color = "#e94560" if active else "#555"
            prefix = "▶" if active else "  "
            self._flag_labels[name].setStyleSheet(f"color: {color}; font-size: 10px;")
            self._flag_labels[name].setText(f"{prefix} {name.replace('_', ' ')}")
