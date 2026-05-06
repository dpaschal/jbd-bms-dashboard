from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from bms_monitor.protocol.frames import BasicInfo


class _FetButton(QPushButton):
    """Toggle button that shows current FET state in its own label."""
    def __init__(self, name: str):
        super().__init__(f"{name}: --")
        self._name = name
        self._on: bool | None = None
        self.setMinimumHeight(28)
        self.setEnabled(False)

    def set_state(self, on: bool) -> None:
        self._on = on
        text = f"{self._name}: {'ON' if on else 'OFF'}"
        self.setText(text)
        bg = "#1f3d2f" if on else "#3d1f1f"
        fg = "#4ecdc4" if on else "#e94560"
        self.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"font-weight: bold; border: 1px solid {fg}; padding: 4px 8px; }}"
            f"QPushButton:hover {{ background-color: #2a4a3a; }}"
        )
        self.setEnabled(True)

    def is_on(self) -> bool:
        return bool(self._on)


class FetsFlagsWidget(QWidget):
    fet_toggle_requested = pyqtSignal(bool, bool)

    def __init__(self):
        super().__init__()
        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(10)

        # Left column: FET status / toggle buttons.
        fet_col = QVBoxLayout()
        fet_col.setSpacing(4)
        fet_col.addWidget(QLabel("FET STATUS"))
        self._charge_btn = _FetButton("Charge")
        self._discharge_btn = _FetButton("Discharge")
        self._charge_btn.clicked.connect(self._toggle_charge)
        self._discharge_btn.clicked.connect(self._toggle_discharge)
        fet_col.addWidget(self._charge_btn)
        fet_col.addWidget(self._discharge_btn)
        fet_col.addStretch()
        outer.addLayout(fet_col, stretch=1)

        # Right column: protection flags grid (2 cols).
        flags_col = QVBoxLayout()
        flags_col.setSpacing(2)
        flags_col.addWidget(QLabel("PROTECTION FLAGS"))
        flags_host = QWidget()
        self._flags_grid = QGridLayout(flags_host)
        self._flags_grid.setHorizontalSpacing(8)
        self._flags_grid.setVerticalSpacing(1)
        self._flags_grid.setContentsMargins(0, 0, 0, 0)
        flags_col.addWidget(flags_host)
        flags_col.addStretch()
        outer.addLayout(flags_col, stretch=1)

        self._flag_labels: dict[str, QLabel] = {}
        names = ["cell_overvolt", "cell_undervolt", "pack_overvolt",
                 "pack_undervolt", "charge_overcurrent",
                 "discharge_overcurrent", "short_circuit", "ic_error",
                 "mos_lock"]
        for i, name in enumerate(names):
            lbl = QLabel(name.replace("_", " "))
            lbl.setStyleSheet("color: #555; font-size: 10px;")
            self._flags_grid.addWidget(lbl, i // 2, i % 2)
            self._flag_labels[name] = lbl

    def _toggle_charge(self) -> None:
        self.fet_toggle_requested.emit(
            not self._charge_btn.is_on(), self._discharge_btn.is_on()
        )

    def _toggle_discharge(self) -> None:
        self.fet_toggle_requested.emit(
            self._charge_btn.is_on(), not self._discharge_btn.is_on()
        )

    def update(self, info: BasicInfo) -> None:
        self._charge_btn.set_state(info.charge_fet)
        self._discharge_btn.set_state(info.discharge_fet)
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
            prefix = "▶ " if active else "  "
            self._flag_labels[name].setStyleSheet(
                f"color: {color}; font-size: 10px;"
            )
            self._flag_labels[name].setText(f"{prefix}{name.replace('_', ' ')}")
