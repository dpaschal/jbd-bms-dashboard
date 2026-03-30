from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
from bms_monitor.protocol.frames import BasicInfo
from collections import deque
import time

HISTORY = 300


class LiveChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._plot = pg.PlotWidget(background="#16213e")
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setLabel("left", "Voltage (V)")
        self._plot.setLabel("bottom", "Time (s)")
        self._v_curve = self._plot.plot(pen=pg.mkPen("#4ecdc4", width=2), name="Voltage")
        self._i_curve = self._plot.plot(pen=pg.mkPen("#f5a623", width=2), name="Current")
        layout.addWidget(self._plot)
        self._times: deque[float] = deque(maxlen=HISTORY)
        self._voltages: deque[float] = deque(maxlen=HISTORY)
        self._currents: deque[float] = deque(maxlen=HISTORY)
        self._t0 = time.monotonic()

    def push_basic(self, info: BasicInfo) -> None:
        t = time.monotonic() - self._t0
        self._times.append(t)
        self._voltages.append(info.pack_voltage)
        self._currents.append(info.current)
        ts = list(self._times)
        self._v_curve.setData(ts, list(self._voltages))
        self._i_curve.setData(ts, list(self._currents))
