from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel, QProgressBar, QVBoxLayout
from PyQt6.QtCore import Qt
from bms_monitor.protocol.frames import CellVoltages


class CellsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QGridLayout(self)
        self._layout.setSpacing(4)
        self._bars: list[tuple[QProgressBar, QLabel]] = []

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
                bar.setFixedWidth(28)
                lbl = QLabel("--")
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("font-size: 9px;")
                col = i % cols
                row_bar = (i // cols) * 2
                self._layout.addWidget(bar, row_bar, col)
                self._layout.addWidget(lbl, row_bar + 1, col)
                self._bars.append((bar, lbl))

        min_v = cells.min_voltage
        for i, (bar, lbl) in enumerate(self._bars):
            v = cells.voltages[i]
            bar.setValue(int(v * 1000))
            lbl.setText(f"{v:.3f}")
            is_low = (cells.delta > 0.020 and abs(v - min_v) < 0.001)
            color = "#e94560" if is_low else "#4ecdc4"
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
            lbl.setStyleSheet(f"font-size: 9px; color: {color};")
        self.setToolTip(f"Δ max: {cells.delta * 1000:.0f} mV")
