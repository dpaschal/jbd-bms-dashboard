from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import CellVoltages


class CellsWidget(QWidget):
    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.addWidget(QLabel("CELLS"))
        header.addStretch()
        self._delta_lbl = QLabel("Δ --")
        self._delta_lbl.setStyleSheet("font-weight: bold;")
        header.addWidget(self._delta_lbl)
        self._max_lbl = QLabel("max --")
        self._min_lbl = QLabel("min --")
        self._max_lbl.setStyleSheet("color: #888; font-size: 10px;")
        self._min_lbl.setStyleSheet("color: #888; font-size: 10px;")
        header.addSpacing(8)
        header.addWidget(self._max_lbl)
        header.addWidget(self._min_lbl)
        outer.addLayout(header)

        grid_host = QWidget()
        self._layout = QGridLayout(grid_host)
        self._layout.setSpacing(2)
        self._layout.setContentsMargins(0, 0, 0, 0)
        # Wrap in row that left-justifies the grid so it doesn't stretch.
        grid_row = QHBoxLayout()
        grid_row.setContentsMargins(0, 0, 0, 0)
        grid_row.addWidget(grid_host)
        grid_row.addStretch()
        outer.addLayout(grid_row)

        self._bars: list[tuple[QProgressBar, QLabel, QLabel]] = []
        self._balance_mask: int = 0

    def update_balance(self, mask: int) -> None:
        self._balance_mask = mask
        self._repaint_balance()

    def _repaint_balance(self) -> None:
        for i, (_bar, _lbl, bal_lbl) in enumerate(self._bars):
            active = bool(self._balance_mask & (1 << i))
            if active:
                bal_lbl.setText("BAL")
                bal_lbl.setStyleSheet("color: #ffeaa7; font-size: 8px; font-weight: bold;")
            else:
                bal_lbl.setText("")

    def update(self, cells: CellVoltages) -> None:
        count = len(cells.voltages)
        if len(self._bars) != count:
            for i in reversed(range(self._layout.count())):
                self._layout.itemAt(i).widget().deleteLater()
            self._bars = []
            cols = 8
            for i in range(count):
                bar = QProgressBar()
                bar.setOrientation(Qt.Orientation.Vertical)
                bar.setRange(2800, 3700)
                bar.setTextVisible(False)
                bar.setFixedWidth(22)
                bar.setFixedHeight(80)
                lbl = QLabel("--")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("font-size: 9px;")
                bal_lbl = QLabel("")
                bal_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                col = i % cols
                row_bar = (i // cols) * 3
                self._layout.addWidget(bar, row_bar, col)
                self._layout.addWidget(lbl, row_bar + 1, col)
                self._layout.addWidget(bal_lbl, row_bar + 2, col)
                self._bars.append((bar, lbl, bal_lbl))

        min_v = cells.min_voltage
        max_v = cells.max_voltage
        for i, (bar, lbl, _bal) in enumerate(self._bars):
            v = cells.voltages[i]
            bar.setValue(int(v * 1000))
            lbl.setText(f"{v:.3f}")
            is_low = (cells.delta > 0.020 and abs(v - min_v) < 0.001)
            is_high = (cells.delta > 0.020 and abs(v - max_v) < 0.001)
            if is_low:
                color = "#e94560"
            elif is_high:
                color = "#f5a623"
            else:
                color = "#4ecdc4"
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
            lbl.setStyleSheet(f"font-size: 9px; color: {color};")

        delta_mv = cells.delta * 1000
        if delta_mv > 20:
            dc = "#e94560"
        elif delta_mv > 10:
            dc = "#ffeaa7"
        else:
            dc = "#4ecdc4"
        self._delta_lbl.setText(f"Δ {delta_mv:.0f}mV")
        self._delta_lbl.setStyleSheet(f"font-weight: bold; color: {dc};")
        self._max_lbl.setText(f"max {max_v:.3f}V")
        self._min_lbl.setText(f"min {min_v:.3f}V")
        self._repaint_balance()
        self.setToolTip(f"Δ max: {delta_mv:.0f} mV")
