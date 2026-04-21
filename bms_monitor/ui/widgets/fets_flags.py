from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import BasicInfo


class FetsFlagsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QLabel("FET STATUS"))
        self._charge_lbl = QLabel("Charge: --")
        self._discharge_lbl = QLabel("Discharge: --")
        layout.addWidget(self._charge_lbl)
        layout.addWidget(self._discharge_lbl)
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

    def update(self, info: BasicInfo) -> None:
        c = "#4ecdc4" if info.charge_fet else "#e94560"
        d = "#4ecdc4" if info.discharge_fet else "#e94560"
        self._charge_lbl.setStyleSheet(f"color: {c};")
        self._charge_lbl.setText(f"Charge: {'ON' if info.charge_fet else 'OFF'}")
        self._discharge_lbl.setStyleSheet(f"color: {d};")
        self._discharge_lbl.setText(f"Discharge: {'ON' if info.discharge_fet else 'OFF'}")
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
